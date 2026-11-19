"""
Main scanner module for running search probes against ecommerce sites.

This scanner is designed to run locally on macOS with headed browser support
for bot-protected sites. It reuses the fetcher and discovery modules from
src/audit for robust page fetching and result extraction.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus, urlparse

from dotenv import load_dotenv

# Add src/audit to path for reusing discovery and fetcher modules
_audit_path = str(Path(__file__).parent.parent / "audit")
if _audit_path not in sys.path:
    sys.path.insert(0, _audit_path)

from .models import (
    ProbeType,
    ProbeResult,
    ProbeStatus,
    ProbeScore,
    ScoredProbe,
    SearchResult,
    SiteInfo,
    ScanResult,
)
from .probes import ProbeGenerator
from .scorer import score_probe_result, score_scan

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


class Scanner:
    """
    Search scanner that runs deterministic probes against ecommerce sites.
    
    Reuses the audit module's fetcher for robust page fetching with:
    - Bot protection bypass (headed Chromium)
    - Site-specific extractors for many retailers
    - Proper zero-result detection
    
    Usage:
        scanner = Scanner()
        result = scanner.scan("https://example.com")
        print(json.dumps(result.model_dump(), indent=2))
    """
    
    def __init__(
        self,
        output_dir: str = "scanner_output",
        take_screenshots: bool = True,
        headed: bool = True,
        max_results_per_query: int = 10,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.take_screenshots = take_screenshots
        self.headed = headed
        self.max_results = max_results_per_query
        self._fetcher = None
        self._playwright = None
        self._browser = None
    
    def _get_fetcher(self):
        """Get the audit fetcher module."""
        if self._fetcher is None:
            try:
                from src import fetcher
                self._fetcher = fetcher
            except ImportError as e:
                logger.warning("Could not import audit fetcher: %s", e)
                self._fetcher = None
        return self._fetcher
    
    def _get_browser(self):
        """Lazy-initialize Playwright browser."""
        if self._browser is not None:
            return self._browser
        
        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            # Use Chromium in headed mode for best bot-protection bypass
            self._browser = self._playwright.chromium.launch(
                headless=not self.headed,
                args=["--disable-blink-features=AutomationControlled"],
            )
            return self._browser
        except Exception as e:
            logger.error("Failed to initialize Playwright: %s", e)
            raise RuntimeError(
                "Playwright not available. Run: pip install playwright && playwright install chromium"
            ) from e
    
    def _close_browser(self):
        """Close browser if open."""
        if self._browser:
            try:
                self._browser.close()
            except:
                pass
            self._browser = None
        if self._playwright:
            try:
                self._playwright.stop()
            except:
                pass
            self._playwright = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self._close_browser()
    
    def _discover_site(self, url: str) -> tuple[SiteInfo, list[str], list[str], list[str]]:
        """Discover site info using the audit module's discovery."""
        try:
            from src.discovery import discover_from_search_url, discover_site
            
            # Try to discover from the URL
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            
            # If URL looks like a search URL, use that
            if "search" in url.lower() or "q=" in url.lower():
                ctx = discover_from_search_url(url)
            else:
                # Otherwise discover from homepage
                ctx = discover_site(url)
            
            site_info = SiteInfo(
                domain=domain,
                site_name=ctx.site_name,
                search_url_template=ctx.search_url_template,
                primary_language=ctx.primary_language,
            )
            
            return site_info, ctx.nav_categories, ctx.featured_items, ctx.brands
            
        except Exception as e:
            logger.warning("Discovery failed, using basic info: %s", e)
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return SiteInfo(domain=domain), [], [], []
    
    def _discover_search_url(self, base_url: str) -> Optional[str]:
        """Try to discover the search URL template for a site."""
        try:
            # First try to find search form on homepage
            resp = requests.get(base_url, headers={"User-Agent": _USER_AGENT}, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Look for search forms
            for form in soup.find_all("form"):
                action = form.get("action", "")
                if "search" in action.lower():
                    # Find the query parameter name
                    for inp in form.find_all("input"):
                        name = inp.get("name", "").lower()
                        if name in ("q", "query", "search", "keyword", "k", "term", "s"):
                            full_action = action if action.startswith("http") else f"{base_url.rstrip('/')}{action}"
                            return f"{full_action}?{inp.get('name')}={{}}"
            
            # Try common search URL patterns
            for pattern in ["/search?q={}", "/search?query={}", "/catalogsearch/result/?q={}"]:
                test_url = f"{base_url.rstrip('/')}{pattern.format('test')}"
                try:
                    r = requests.head(test_url, headers={"User-Agent": _USER_AGENT}, timeout=5, allow_redirects=True)
                    if r.status_code < 400:
                        return f"{base_url.rstrip('/')}{pattern}"
                except:
                    pass
            
            return None
            
        except Exception as e:
            logger.warning("Search URL discovery failed: %s", e)
            return None
    
    def _fetch_search_results(
        self,
        search_url: str,
        query: str,
        screenshot_name: Optional[str] = None,
    ) -> tuple[list[SearchResult], int, ProbeStatus, Optional[str], Optional[str]]:
        """
        Fetch search results for a query.
        
        Uses the audit module's fetcher when available for robust extraction.
        Falls back to basic Playwright fetching otherwise.
        
        Returns: (results, count, status, error_message, screenshot_path)
        """
        url = search_url.format(quote_plus(query))
        screenshot_path = None
        
        # Try using the audit fetcher first (has site-specific extractors)
        fetcher = self._get_fetcher()
        if fetcher:
            try:
                outcome = fetcher.fetch_search_results(
                    search_url_template=search_url,
                    query=query,
                    max_results=self.max_results,
                    headed=self.headed,
                )
                
                # Convert FetchOutcome to our format
                results = [
                    SearchResult(
                        rank=r.rank,
                        title=r.title,
                        price=r.price,
                        url=r.url,
                    )
                    for r in outcome.results
                ]
                
                # Map FetchStatus to ProbeStatus
                from src.models import FetchStatus
                status_map = {
                    FetchStatus.OK: ProbeStatus.SUCCESS,
                    FetchStatus.ZERO_CONFIRMED: ProbeStatus.SUCCESS,
                    FetchStatus.PARTIAL: ProbeStatus.PARTIAL,
                    FetchStatus.REDIRECT: ProbeStatus.REDIRECT,
                    FetchStatus.BLOCKED: ProbeStatus.BLOCKED,
                    FetchStatus.TIMEOUT: ProbeStatus.TIMEOUT,
                    FetchStatus.ERROR: ProbeStatus.ERROR,
                }
                probe_status = status_map.get(outcome.status, ProbeStatus.ERROR)
                
                count = outcome.total_hits if outcome.total_hits else len(results)
                
                # Take screenshot if requested
                if self.take_screenshots and screenshot_name:
                    screenshot_path = self._take_screenshot(url, screenshot_name)
                
                return results, count, probe_status, outcome.evidence if probe_status != ProbeStatus.SUCCESS else None, screenshot_path
                
            except Exception as e:
                logger.warning("Audit fetcher failed, falling back to basic fetch: %s", e)
        
        # Fallback: Use basic Playwright fetch
        try:
            from bs4 import BeautifulSoup
            html, screenshot_path = self._fetch_with_playwright(url, screenshot_name)
            if not html:
                return [], 0, ProbeStatus.BLOCKED, "Failed to fetch page", screenshot_path
            
            # Basic block detection
            sample = html[:5000].lower()
            if any(sig in sample for sig in ("just a moment", "checking your browser", "ray id")):
                return [], 0, ProbeStatus.BLOCKED, "Cloudflare protection", screenshot_path
            if any(sig in sample for sig in ("incapsula incident", "pardon our interruption")):
                return [], 0, ProbeStatus.BLOCKED, "Imperva protection", screenshot_path
            
            soup = BeautifulSoup(html, "html.parser")
            results, count = self._extract_results(soup, url)
            return results, count, ProbeStatus.SUCCESS, None, screenshot_path
            
        except Exception as e:
            return [], 0, ProbeStatus.ERROR, str(e), None
    
    def _fetch_with_playwright(
        self,
        url: str,
        screenshot_name: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        """Fetch page with Playwright. Returns (html, screenshot_path)."""
        screenshot_path = None
        try:
            browser = self._get_browser()
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=_USER_AGENT,
            )
            page = context.new_page()
            
            # Navigate and wait for content
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait a bit for any JS to settle
            page.wait_for_timeout(2000)
            
            # Take screenshot if requested
            if self.take_screenshots and screenshot_name:
                screenshot_path = str(self.output_dir / f"{screenshot_name}.png")
                page.screenshot(path=screenshot_path, full_page=False)
            
            html = page.content()
            context.close()
            
            return html, screenshot_path
            
        except Exception as e:
            logger.error("Playwright fetch failed: %s", e)
            return None, screenshot_path
    
    def _take_screenshot(self, url: str, name: str) -> Optional[str]:
        """Take a screenshot of a URL."""
        try:
            browser = self._get_browser()
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=_USER_AGENT,
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)
            
            path = str(self.output_dir / f"{name}.png")
            page.screenshot(path=path, full_page=False)
            context.close()
            return path
        except Exception as e:
            logger.warning("Screenshot failed: %s", e)
            return None
    
    def _extract_results(self, soup: BeautifulSoup, url: str) -> tuple[list[SearchResult], int]:
        """Extract search results from a page. Returns (results, count)."""
        results = []
        
        # Try to extract result count from page text
        count = self._extract_result_count(soup)
        
        # Look for product cards using common patterns
        card_selectors = [
            # Common e-commerce patterns
            "[class*='product']",
            "[class*='item']",
            "[class*='result']",
            "[class*='card']",
            "[data-product]",
            "[data-item]",
            # Specific platform patterns
            ".product-item",
            ".search-result",
            ".product-card",
            ".plp-product",
        ]
        
        cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if len(cards) >= 3:  # Found enough cards
                break
        
        # Extract info from each card
        for i, card in enumerate(cards[:self.max_results]):
            # Find title
            title = None
            for tag in card.find_all(["h1", "h2", "h3", "h4", "a"]):
                text = tag.get_text(strip=True)
                if text and len(text) > 5 and len(text) < 200:
                    title = text
                    break
            
            if not title:
                continue
            
            # Find price
            price = None
            price_patterns = [
                r"(?:[$€£¥])\s?\d[\d.,]*",
                r"\d[\d.,]*\s?(?:[$€£¥]|kr|Kč)",
            ]
            card_text = card.get_text()
            for pattern in price_patterns:
                match = re.search(pattern, card_text)
                if match:
                    price = match.group().strip()
                    break
            
            # Find URL
            link = card.find("a", href=True)
            item_url = link["href"] if link else None
            if item_url and not item_url.startswith("http"):
                parsed = urlparse(url)
                item_url = f"{parsed.scheme}://{parsed.netloc}{item_url}"
            
            results.append(SearchResult(
                rank=len(results) + 1,
                title=title[:200],
                price=price,
                url=item_url,
            ))
        
        # If no count was found, use results length
        if count == 0 and results:
            count = len(results)
        
        return results, count
    
    def _extract_result_count(self, soup: BeautifulSoup) -> int:
        """Try to extract the total result count from page text."""
        # Look for common count patterns
        patterns = [
            r"(\d+)\s*(?:results?|products?|items?)",
            r"(?:showing|found)\s*(\d+)",
            r"(\d+)\s*(?:träffar|produkter)",  # Swedish
            r"(\d+)\s*(?:Ergebnisse|Produkte)",  # German
        ]
        
        text = soup.get_text()[:5000]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except:
                    pass
        
        return 0
    
    def scan(
        self,
        url: str,
        vertical: Optional[str] = None,
        country: Optional[str] = None,
    ) -> ScanResult:
        """
        Run all probes against a site and return scored results.
        
        Args:
            url: The site URL (homepage or search URL)
            vertical: Optional vertical/industry label
            country: Optional country label
        
        Returns:
            ScanResult with all probe results and scores
        """
        start_time = time.time()
        
        # Discover site info
        logger.info("Discovering site: %s", url)
        site_info, nav_categories, featured_items, brands = self._discover_site(url)
        site_info.vertical = vertical
        site_info.country = country
        
        # Set up result
        result = ScanResult(site=site_info)
        
        # Find search URL if not discovered
        if not site_info.search_url_template:
            search_template = self._discover_search_url(url)
            if search_template:
                site_info.search_url_template = search_template
            else:
                result.error_message = "Could not discover search URL"
                result.overall_score = ProbeScore.ERROR
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                return result
        
        # Initialize probe generator
        generator = ProbeGenerator(
            site_info=site_info,
            nav_categories=nav_categories,
            featured_items=featured_items,
            brands=brands,
        )
        
        # Run probes
        probes: list[ScoredProbe] = []
        
        # 1. Control query (must pass for other probes to be meaningful)
        control_query, control_rationale = generator.generate_control_query()
        if control_query:
            probe = self._run_probe(
                ProbeType.CONTROL_QUERY,
                site_info.search_url_template,
                control_query,
                rationale=control_rationale,
            )
            scored = score_probe_result(probe)
            probes.append(scored)
            
            if scored.score in (ProbeScore.BLOCKED, ProbeScore.ERROR):
                result.blocked = scored.score == ProbeScore.BLOCKED
                result.error_message = probe.error_message
                result.probes = probes
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                result.llm_cost_usd = generator.llm_cost_usd
                return score_scan(result)
        
        # 2. Exact product name
        product_query, product_rationale = generator.generate_exact_product_name()
        if product_query:
            probe = self._run_probe(
                ProbeType.EXACT_PRODUCT_NAME,
                site_info.search_url_template,
                product_query,
                rationale=product_rationale,
            )
            probes.append(score_probe_result(probe))
        
        # 3. Category term
        category_query, category_rationale = generator.generate_category_term()
        if category_query:
            probe = self._run_probe(
                ProbeType.CATEGORY_TERM,
                site_info.search_url_template,
                category_query,
                rationale=category_rationale,
            )
            probes.append(score_probe_result(probe))
            
            # Use category for other probes
            base_query = category_query
        else:
            base_query = control_query
        
        # 4. Typo tolerance (F002)
        typo_query, typo_control, typo_rationale = generator.generate_typo_query(base_query)
        if typo_query and typo_query != typo_control:
            # Get control count
            _, control_count, _, _, _ = self._fetch_search_results(
                site_info.search_url_template, typo_control
            )
            probe = self._run_probe(
                ProbeType.TYPO,
                site_info.search_url_template,
                typo_query,
                control_query=typo_control,
                control_count=control_count,
                rationale=typo_rationale,
            )
            probes.append(score_probe_result(probe))
        
        # 5. Synonym
        syn_query, syn_control, syn_rationale = generator.generate_synonym_query()
        if syn_query and syn_control:
            _, control_count, _, _, _ = self._fetch_search_results(
                site_info.search_url_template, syn_control
            )
            probe = self._run_probe(
                ProbeType.SYNONYM,
                site_info.search_url_template,
                syn_query,
                control_query=syn_control,
                control_count=control_count,
                rationale=syn_rationale,
            )
            probes.append(score_probe_result(probe))
        
        # 6. Plural/singular
        ps_query, ps_control, ps_rationale = generator.generate_plural_singular(base_query)
        if ps_query and ps_query != ps_control:
            _, control_count, _, _, _ = self._fetch_search_results(
                site_info.search_url_template, ps_control
            )
            probe = self._run_probe(
                ProbeType.PLURAL_SINGULAR,
                site_info.search_url_template,
                ps_query,
                control_query=ps_control,
                control_count=control_count,
                rationale=ps_rationale,
            )
            probes.append(score_probe_result(probe))
        
        # 7. Diacritics
        dia_query, dia_control, dia_rationale = generator.generate_diacritics_query()
        if dia_query and dia_control and dia_query != dia_control:
            _, control_count, _, _, _ = self._fetch_search_results(
                site_info.search_url_template, dia_control
            )
            probe = self._run_probe(
                ProbeType.DIACRITICS,
                site_info.search_url_template,
                dia_query,
                control_query=dia_control,
                control_count=control_count,
                rationale=dia_rationale,
            )
            probes.append(score_probe_result(probe))
        
        # 8. Compound split
        split_query, split_control, split_rationale = generator.generate_compound_split()
        if split_query and split_control:
            _, control_count, _, _, _ = self._fetch_search_results(
                site_info.search_url_template, split_control
            )
            probe = self._run_probe(
                ProbeType.COMPOUND_SPLIT,
                site_info.search_url_template,
                split_query,
                control_query=split_control,
                control_count=control_count,
                rationale=split_rationale,
            )
            probes.append(score_probe_result(probe))
        
        # 9. Merged words
        merged_query, merged_control, merged_rationale = generator.generate_merged_words(base_query)
        if merged_query and merged_control and merged_query != merged_control:
            _, control_count, _, _, _ = self._fetch_search_results(
                site_info.search_url_template, merged_control
            )
            probe = self._run_probe(
                ProbeType.MERGED_WORDS,
                site_info.search_url_template,
                merged_query,
                control_query=merged_control,
                control_count=control_count,
                rationale=merged_rationale,
            )
            probes.append(score_probe_result(probe))
        
        # 10. Constraint query
        const_query, const_base, const_rationale = generator.generate_constraint_query()
        if const_query:
            _, control_count, _, _, _ = self._fetch_search_results(
                site_info.search_url_template, const_base
            )
            probe = self._run_probe(
                ProbeType.CONSTRAINT_QUERY,
                site_info.search_url_template,
                const_query,
                control_query=const_base,
                control_count=control_count,
                rationale=const_rationale,
            )
            probes.append(score_probe_result(probe))
        
        # 11. SKU search
        sku_query, sku_rationale = generator.generate_sku_search()
        if sku_query:
            probe = self._run_probe(
                ProbeType.SKU_SEARCH,
                site_info.search_url_template,
                sku_query,
                rationale=sku_rationale,
            )
            probes.append(score_probe_result(probe))
        
        # 12. Zero-result check
        zero_query, zero_rationale = generator.generate_zero_result_check()
        probe = self._run_probe(
            ProbeType.ZERO_RESULT_CHECK,
            site_info.search_url_template,
            zero_query,
            rationale=zero_rationale,
        )
        probes.append(score_probe_result(probe))
        
        # Compile results
        result.probes = probes
        result.execution_time_ms = int((time.time() - start_time) * 1000)
        result.llm_cost_usd = generator.llm_cost_usd
        
        return score_scan(result)
    
    def _run_probe(
        self,
        probe_type: ProbeType,
        search_url_template: str,
        query: str,
        control_query: Optional[str] = None,
        control_count: Optional[int] = None,
        rationale: str = "",
    ) -> ProbeResult:
        """Run a single probe and return the result."""
        start = time.time()
        
        screenshot_name = f"{probe_type.value}_{query[:20].replace(' ', '_')}"
        results, count, status, error, screenshot = self._fetch_search_results(
            search_url_template, query, screenshot_name
        )
        
        return ProbeResult(
            probe_type=probe_type,
            query=query,
            control_query=control_query,
            status=status,
            result_count=count,
            results=results[:self.max_results],
            control_count=control_count,
            screenshot_path=screenshot,
            error_message=error,
            execution_time_ms=int((time.time() - start) * 1000),
            rationale=rationale,
        )
    
    def save_result(self, result: ScanResult, filename: Optional[str] = None) -> str:
        """Save scan result to JSON file. Returns the file path."""
        if filename is None:
            safe_domain = result.site.domain.replace(".", "_").replace("/", "_")
            filename = f"{safe_domain}_{result.scanned_at[:10]}.json"
        
        path = self.output_dir / filename
        with open(path, "w") as f:
            json.dump(result.model_dump(), f, indent=2, default=str)
        
        return str(path)


def main():
    """CLI entry point for single-site scanning."""
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Scan a site's search capability")
    parser.add_argument("url", help="Site URL to scan")
    parser.add_argument("--vertical", help="Industry vertical (e.g., fashion, outdoor)")
    parser.add_argument("--country", help="Country code (e.g., US, UK, DE)")
    parser.add_argument("--output-dir", default="scanner_output", help="Output directory")
    parser.add_argument("--no-screenshots", action="store_true", help="Disable screenshots")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    
    args = parser.parse_args()
    
    with Scanner(
        output_dir=args.output_dir,
        take_screenshots=not args.no_screenshots,
        headed=not args.headless,
    ) as scanner:
        result = scanner.scan(
            args.url,
            vertical=args.vertical,
            country=args.country,
        )
        
        path = scanner.save_result(result)
        
        print(f"\n{'='*60}")
        print(f"Scan Results for {result.site.domain}")
        print(f"{'='*60}")
        print(f"Overall Score: {result.overall_score.value}")
        print(f"LLM Cost: ${result.llm_cost_usd:.4f}")
        print(f"Execution Time: {result.execution_time_ms}ms")
        print(f"\nCapabilities:")
        for cap in result.capabilities:
            print(f"  {cap.capability}: {cap.score.value} ({cap.summary})")
        print(f"\nResults saved to: {path}")


if __name__ == "__main__":
    main()

"""
Main scanner module for running search probes against ecommerce sites.

This scanner is designed to run locally on macOS with headed browser support
for bot-protected sites. It reuses the fetcher and discovery modules from
src/audit for robust page fetching and result extraction.
"""

from __future__ import annotations

import json
import logging
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

load_dotenv(override=False)

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
        self._output_root = Path(output_dir)
        self.output_dir = self._output_root
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.take_screenshots = take_screenshots
        self.headed = headed
        self.max_results = max_results_per_query
        self._playwright = None
        self._browser = None
        self._query_cache = {}
    
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
            self._close_browser()
            raise RuntimeError(f"Could not launch Chromium: {e}") from e
    
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
    
    def _load_page(self, url: str, name: str):
        """Capture rendered HTML, API evidence and screenshot in one headed visit."""
        import gzip
        from src import fetcher
        browser = self._get_browser()
        context = browser.new_context(viewport={"width": 1280, "height": 900}, user_agent=_USER_AGENT)
        page = context.new_page()
        page.set_default_timeout(3000)
        captured = []
        fetcher._apply_stealth(page)
        page.on("response", lambda response: fetcher._capture_search_api(response, captured))
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            fetcher._dismiss_consent_banners(page)
            ready = fetcher._wait_for_host_ready(page, url) if "?" in url else None
            page.wait_for_timeout(1500)
            if "bergzeit.de" in urlparse(url).netloc:
                decline = page.get_by_role("button", name="Nicht einverstanden", exact=True)
                if decline.count() and decline.first.is_visible():
                    decline.first.click(timeout=2000)
                    page.wait_for_timeout(300)
            if "allbirds.com" in urlparse(url).netloc:
                close = page.get_by_role("button", name="Close", exact=True)
                for button in close.all():
                    if button.is_visible():
                        button.click(timeout=2000)
                        page.wait_for_timeout(300)
                        break
            html = page.content()
            safe_name = re.sub(r"[^\w.-]+", "_", name)[:100]
            path = self.output_dir / safe_name
            with gzip.open(str(path) + ".html.gz", "wt") as evidence:
                evidence.write(html)
            shot = None
            if self.take_screenshots:
                shot = str(path) + ".png"
                page.screenshot(path=shot, full_page=False)
            return dict(html=html, final_url=page.url,
                        http_status=response.status if response else None,
                        visible_text=page.locator("body").inner_text(timeout=5000), ready=ready,
                        search_api=fetcher._read_captured_search_api(captured)), shot
        finally:
            context.close()

    def _discover_site(self, url: str) -> tuple[SiteInfo, list[str], list[str], list[str]]:
        from bs4 import BeautifulSoup
        from src import discovery
        page, _ = self._load_page(url, "homepage")
        soup = BeautifulSoup(page["html"], "html.parser")
        template = ""
        if "?" in url:
            try:
                template, _ = discovery.parse_search_url(url)
            except ValueError:
                pass
        template = template or discovery._extract_search_url_template(soup, page["final_url"])
        if not template:
            link = soup.select_one('a[href$="/search"]')
            if link:
                from urllib.parse import urljoin
                search_page, _ = self._load_page(urljoin(url, link["href"]), "search_discovery")
                template = discovery._extract_search_url_template(BeautifulSoup(search_page["html"], "html.parser"), search_page["final_url"])
        info = SiteInfo(domain=urlparse(url).netloc.removeprefix("www."),
                        site_name=discovery._extract_site_name(soup, url),
                        search_url_template=template,
                        primary_language="German" if soup.html and str(soup.html.get("lang", "")).startswith("de") else "English")
        categories = discovery._extract_nav_categories(soup)
        excluded = discovery._NON_SEED_NAV | {"b2b", "image link", "advice & inspiration", "shopping cart", "black friday", "men", "women", "herren", "damen", "services", "stores", "login", "holiday sale", "mens holiday sale", "bestsellers", "leather alternatives"}
        categories = [c for c in categories if c.lower() not in excluded][:15]
        return info, categories, discovery._extract_featured_items(soup), discovery._extract_brands(soup)

    def _discover_search_url(self, base_url: str) -> Optional[str]:
        # Never accept an arbitrary HTTP 200 as proof that a search endpoint works.
        return None

    def _fetch_search_results(self, search_url: str, query: str, screenshot_name: Optional[str] = None):
        from src import fetcher
        from src.models import FetchStatus
        key = (search_url, query)
        if key in self._query_cache:
            return self._query_cache[key]
        try:
            url = search_url.format(quote_plus(query))
            page, shot = self._load_page(url, screenshot_name or query)
            outcome = fetcher._analyse_page(url=url, query=query, max_results=self.max_results,
                                            allow_llm=False, **page)
            status = {
                FetchStatus.OK: ProbeStatus.SUCCESS,
                FetchStatus.ZERO_CONFIRMED: ProbeStatus.SUCCESS,
                FetchStatus.ZERO_UNVERIFIED: ProbeStatus.ERROR,
                FetchStatus.PARTIAL: ProbeStatus.PARTIAL,
                FetchStatus.REDIRECT: ProbeStatus.REDIRECT,
                FetchStatus.BLOCKED: ProbeStatus.BLOCKED,
                FetchStatus.TIMEOUT: ProbeStatus.TIMEOUT,
                FetchStatus.ERROR: ProbeStatus.ERROR,
            }[FetchStatus(outcome.status)]
            count = outcome.total_hits if outcome.total_hits is not None else len(outcome.results)
            results = [SearchResult(rank=r.rank, title=r.title, price=r.price, url=r.url) for r in outcome.results]
            value = (results, count, status, outcome.evidence or None, shot)
            logger.info("%r -> %s: %s hits (%s)", query, status.value, count, outcome.evidence)
            self._query_cache[key] = value
            return value
        except Exception as exc:
            logger.exception("Search fetch failed for %r", query)
            return [], 0, ProbeStatus.ERROR, str(exc), None

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
        self._query_cache.clear()
        self.output_dir = self._output_root / urlparse(url).netloc
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Discover site info
        logger.info("Discovering site: %s", url)
        try:
            site_info, nav_categories, featured_items, brands = self._discover_site(url)
        except Exception as exc:
            logger.error("Discovery failed: %s", exc)
            return ScanResult(site=SiteInfo(domain=urlparse(url).netloc.removeprefix("www."),
                              vertical=vertical, country=country), error_message=str(exc),
                              execution_time_ms=int((time.time() - start_time) * 1000))
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
        if not control_query:
            result.error_message = "No catalog category available for a positive control"
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result
        if control_query:
            probe = self._run_probe(
                ProbeType.CONTROL_QUERY,
                site_info.search_url_template,
                control_query,
                rationale=control_rationale,
            )
            scored = score_probe_result(probe)
            probes.append(scored)
            
            if scored.score != ProbeScore.PASS:
                result.blocked = scored.score == ProbeScore.BLOCKED
                result.error_message = probe.error_message
                result.probes = probes
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                result.llm_cost_usd = generator.llm_cost_usd
                return score_scan(result)
        
        if control_query and probe.results:
            generator.featured_items = [r.title for r in probe.results]

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
        
        if control_query:
            control = self._query_cache.get((search_url_template, control_query))
            if control and control[2] not in (ProbeStatus.SUCCESS, ProbeStatus.REDIRECT):
                status = ProbeStatus.ERROR
                error = f"Control fetch was {control[2].value}; comparison is inconclusive"
                control_count = None
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
    """Backward-compatible module entry point."""
    from .cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()

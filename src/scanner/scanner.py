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
from datetime import datetime, timezone
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
        max_results_per_query: int = 5,
        viewport_height: int = 900,
    ):
        self._output_root = Path(output_dir)
        self.output_dir = self._output_root
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.take_screenshots = take_screenshots
        self.headed = headed
        self.max_results = max_results_per_query
        self.viewport_height = viewport_height
        self._playwright = None
        self._browser = None
        self._query_cache = {}
        self._count_exact = {}
        self._retrying = set()
    
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
        context = browser.new_context(viewport={"width": 1280, "height": self.viewport_height}, user_agent=_USER_AGENT)
        page = context.new_page()
        page.set_default_timeout(3000)
        captured = []
        fetcher._apply_stealth(page)
        page.on("response", lambda response: fetcher._capture_search_api(response, captured))
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            if "just a moment" in page.title().lower():
                fetcher._wait_for_cloudflare_clear(page, timeout_ms=15000)
            fetcher._dismiss_consent_banners(page)
            ready = fetcher._wait_for_host_ready(page, url) if "?" in url else None
            page.wait_for_timeout(1500)
            if "passenger-clothing.com" in urlparse(url).netloc and "?" in url:
                try:
                    page.wait_for_function("""() => document.querySelector('#ProductGridContainer product-card') ||
                        /no results|no products found/i.test(document.querySelector('main')?.innerText || '')""", timeout=12000)
                except Exception:
                    pass
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
            if "watery.dk" in urlparse(url).netloc:
                decline = page.get_by_role("button", name="Afvis alle", exact=True)
                if decline.count() and decline.first.is_visible():
                    decline.first.click(timeout=2000)
                    page.wait_for_timeout(500)
            if "finisterre.com" in urlparse(url).netloc:
                for frame in page.frames:
                    for button in frame.locator("button.close-btn, [aria-label='Close'], [title='Close'], .om-popup-close").all():
                        if button.is_visible():
                            try:
                                button.click(timeout=1500)
                            except Exception:
                                logger.debug("Overlay close did not settle; retained screenshot evidence")
                            break
            for consent_label in ("Ablehnen", "Einverstanden", "Alle Cookies zulassen"):
                button = page.get_by_role('button',name=consent_label,exact=True)
                if button.count() and button.first.is_visible():
                    try:
                        button.first.click(timeout=1500)
                        page.wait_for_timeout(300)
                    except Exception:
                        logger.debug("Consent dismissal did not settle")
                    break
            if "connox.de" in urlparse(url).netloc:
                close = page.locator('autodetect-root').get_by_role('button',name='Close',exact=True)
                if close.count() and close.first.is_visible():
                    try:
                        close.first.click(timeout=1500)
                        page.wait_for_timeout(300)
                    except Exception:
                        logger.debug("Country modal close did not settle")
            if "connox.de" in urlparse(url).netloc:
                for frame in page.frames:
                    minimize = frame.get_by_text('Fenster minimieren',exact=True)
                    if minimize.count() and minimize.first.is_visible():
                        try:
                            minimize.first.click(timeout=1500)
                            page.wait_for_timeout(700)
                        except Exception:
                            logger.debug("Promotional panel minimization did not settle")
            html = page.content()
            analysis_html = html
            if name not in ("homepage", "search_discovery"):
                # CSS-hidden empty-state templates are not rendered zero evidence.
                page.evaluate("""() => {
                    for (const el of document.querySelectorAll('*')) {
                        if (['SCRIPT','STYLE','LINK','META'].includes(el.tagName)) continue;
                        const style = getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0' || el.hidden)
                            el.setAttribute('data-scanner-hidden', 'true');
                    }
                }""")
                from bs4 import BeautifulSoup
                rendered = BeautifulSoup(page.content(), "html.parser")
                for hidden in rendered.select('[data-scanner-hidden]'):
                    hidden.decompose()
                analysis_html = str(rendered)
            shadows = page.evaluate("""() => [...document.querySelectorAll('br-product-card')]
                .map(el => el.shadowRoot ? el.shadowRoot.innerHTML : '').join('')""")
            if shadows:
                analysis_html += '<section data-scanner-shadow-evidence>' + shadows + '</section>'
            import hashlib
            safe_name = re.sub(r"[^\w.-]+", "_", name)[:80] + "_" + hashlib.sha256(name.encode()).hexdigest()[:10]
            path = self.output_dir / safe_name
            with gzip.open(str(path) + ".html.gz", "wt") as evidence:
                evidence.write(html)
            shot = None
            if self.take_screenshots:
                shot = str(path) + ".png"
                page.screenshot(path=shot, full_page=False)
            if analysis_html != html:
                with gzip.open(str(path) + ".rendered.html.gz", "wt") as evidence:
                    evidence.write(analysis_html)
            api_evidence = fetcher._read_captured_search_api(captured)
            from urllib.parse import parse_qs
            params = parse_qs(urlparse(url).query)
            query = next((params[k][0] for k in ('q','search','keywords') if params.get(k)), '')
            summary = fetcher._search_api_summary(api_evidence, query) if query else None
            from dataclasses import asdict
            from bs4 import BeautifulSoup
            text_soup = BeautifulSoup(analysis_html, 'html.parser')
            for noise in text_soup.select('script, style'):
                noise.decompose()
            rendered_text = text_soup.get_text(' ', strip=True)
            metadata = {"captured_at":datetime.now(timezone.utc).isoformat(), "requested_url":url, "final_url":page.url,
                        "http_status":response.status if response else None,
                        "visible_text":rendered_text,
                        "search_api_summary":asdict(summary) if summary else None}
            Path(str(path) + '.page.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
            return dict(html=analysis_html, final_url=page.url,
                        http_status=response.status if response else None,
                        visible_text=rendered_text, ready=ready,
                        search_api=api_evidence), shot
        finally:
            context.close()

    def _discover_site(self, url: str) -> tuple[SiteInfo, list[str], list[str], list[str]]:
        from bs4 import BeautifulSoup
        from src import discovery
        page, _ = self._load_page(url, "homepage")
        soup = BeautifulSoup(page["html"], "html.parser")
        from src import fetcher
        blocked = fetcher._detect_block(page['html'], page.get('http_status'), page['final_url'])
        if blocked and blocked != "tiny_page":
            raise RuntimeError(f"Bot protection during discovery: {blocked}")
        template = ""
        if "?" in url:
            try:
                template, _ = discovery.parse_search_url(url)
            except ValueError:
                pass
        template = template or discovery._extract_search_url_template(soup, page["final_url"])
        # JS forms without action otherwise become homepage?q=... and
        # homepage recommendation cards masquerade as search results.
        query_links = [a.get('href') for a in soup.select('a[href]')
                       if '/search?' in str(a.get('href', '')) and 'q=' in str(a.get('href', ''))]
        if query_links:
            from urllib.parse import urljoin
            template, _ = discovery.parse_search_url(urljoin(page['final_url'], query_links[0]))
        if not template:
            link = soup.select_one('a[href$="/search"]')
            if link:
                from urllib.parse import urljoin
                search_page, _ = self._load_page(urljoin(url, link["href"]), "search_discovery")
                template = discovery._extract_search_url_template(BeautifulSoup(search_page["html"], "html.parser"), search_page["final_url"])
        info = SiteInfo(domain=urlparse(url).netloc.removeprefix("www."),
                        site_name=discovery._extract_site_name(soup, url),
                        search_url_template=template,
                        primary_language={"de":"German", "cs":"Czech", "sk":"Slovak", "pl":"Polish", "da":"Danish", "sv":"Swedish", "no":"Norwegian"}.get(str(soup.html.get("lang", "en"))[:2] if soup.html else "en", "English"))
        self._platform = "Shopify" if "cdn.shopify.com" in page["html"] or "Shopify.shop" in page["html"] else "unknown"
        categories = discovery._extract_nav_categories(soup)
        # Headless menu components often lack semantic <nav>; collection and
        # query links still expose literal catalog vocabulary.
        from urllib.parse import parse_qs
        for anchor in soup.select('a[href]'):
            href = str(anchor.get('href', ''))
            label = anchor.get_text(' ', strip=True)
            if '/collections/' in href or parse_qs(urlparse(href).query).get('q'):
                if label and 3 <= len(label) <= 55 and label not in categories:
                    categories.append(label)

        excluded = discovery._NON_SEED_NAV | discovery._GENERIC_NAV_ITEMS | {"b2b", "image link", "advice & inspiration", "shopping cart", "black friday", "men", "women", "herren", "damen", "services", "stores", "login", "holiday sale", "mens holiday sale", "bestsellers", "leather alternatives"}
        from .catalog import catalog_categories
        categories = catalog_categories(soup, page["final_url"], categories)
        categories = [c for c in categories if c.lower() not in excluded and not re.search(r"%|offers|continue shopping|featured|last chance|gifting|view |shop |sale|up to", c, re.I)][:30]
        return info, categories, discovery._extract_featured_items(soup), discovery._extract_brands(soup)

    def _discover_search_url(self, base_url: str, seed: str = "") -> Optional[str]:
        """Submit an observed JS search input; never guess endpoints from HTTP 200."""
        if not seed:
            return None
        from src import discovery, fetcher
        context = self._get_browser().new_context(viewport={"width":1280,"height":900},user_agent=_USER_AGENT)
        page = context.new_page()
        try:
            page.goto(base_url,wait_until="domcontentloaded",timeout=30000)
            page.wait_for_timeout(2500)
            fetcher._dismiss_consent_banners(page)
            inputs = page.locator('input[type="search"], input[name="keywords"], input[name="q"]')
            for field in inputs.all():
                if field.is_visible():
                    field.fill(seed)
                    field.press('Enter')
                    page.wait_for_timeout(2500)
                    template, observed = discovery.parse_search_url(page.url)
                    if observed.casefold() == seed.casefold():
                        return template
            return None
        except Exception as exc:
            logger.info("Interactive search discovery inconclusive: %s", type(exc).__name__)
            return None
        finally:
            context.close()

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
            from .storefronts import scoped_products, scoped_count, scoped_brands
            scoped = scoped_products(page['html'], page['final_url'], self.max_results)
            visible_count = scoped_count(page['html'], page['final_url'])
            if visible_count == 0 and not scoped:
                outcome = outcome.model_copy(update={"status":FetchStatus.ZERO_CONFIRMED,
                    "results":[],"total_hits":0,"evidence":"Visible scoped product count is zero"})
            if scoped and outcome.status != FetchStatus.ZERO_CONFIRMED:
                from src.models import FetchStatus as FS
                outcome = outcome.model_copy(update={"status": FS.OK, "results": scoped,
                    "total_hits": scoped_count(page["html"], page["final_url"]) or outcome.total_hits,
                    "evidence": "Products read from verified store search-result container"})
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
            self._count_exact[key] = outcome.total_hits is not None
            count = outcome.total_hits if outcome.total_hits is not None else len(outcome.results)
            observed_brands = scoped_brands(page["html"], page["final_url"])
            results = [SearchResult(rank=r.rank, title=r.title, price=r.price, url=r.url, brand=observed_brands.get(r.url)) for r in outcome.results]
            value = (results, count, status, outcome.evidence or None, shot)
            logger.info("%r -> %s: %s hits (%s)", query, status.value, count, outcome.evidence)
            self._query_cache[key] = value
            return value
        except Exception as exc:
            if key not in self._retrying and any(token in str(exc) for token in ('ERR_CONNECTION_REFUSED','Timeout','timeout')):
                self._retrying.add(key)
                try:
                    logger.info("Retrying one transient browser failure for %r",query)
                    time.sleep(1)
                    return self._fetch_search_results(search_url,query,screenshot_name)
                finally:
                    self._retrying.discard(key)
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
        self._count_exact.clear()
        self.output_dir = self._output_root / urlparse(url).netloc
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Discover site info
        logger.info("Discovering site: %s", url)
        try:
            site_info, nav_categories, featured_items, brands = self._discover_site(url)
        except Exception as exc:
            logger.error("Discovery failed: %s", exc)
            return score_scan(ScanResult(site=SiteInfo(domain=urlparse(url).netloc.removeprefix("www."),
                              vertical=vertical, country=country), error_message=str(exc),
                              blocked="Bot protection" in str(exc),
                              overall_score=ProbeScore.BLOCKED if "Bot protection" in str(exc) else ProbeScore.ERROR,
                              execution_time_ms=int((time.time() - start_time) * 1000)))
        site_info.vertical = vertical
        site_info.country = country
        
        # Set up result
        result = ScanResult(site=site_info, platform=getattr(self, "_platform", "unknown"))
        
        # Find search URL if not discovered
        if not site_info.search_url_template:
            search_template = self._discover_search_url(url, (nav_categories + featured_items + [site_info.site_name])[0])
            if search_template:
                site_info.search_url_template = search_template
            else:
                result.error_message = "Could not discover search URL"
                result.overall_score = ProbeScore.ERROR
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                return score_scan(result)
        
        # Initialize probe generator
        generator = ProbeGenerator(
            site_info=site_info,
            nav_categories=nav_categories,
            featured_items=featured_items,
            brands=brands,
        )
        
        # Run probes
        probes: list[ScoredProbe] = []
        
        # Try several real catalog seeds; a promotional nav label is not a
        # trustworthy positive control. Keep attempts as technical evidence.
        probe = None
        for control_query in (nav_categories + featured_items)[:6]:
            candidate = self._run_probe(ProbeType.CONTROL_QUERY,
                site_info.search_url_template, control_query, rationale="Catalog seed control")
            if candidate.status in (ProbeStatus.SUCCESS, ProbeStatus.REDIRECT) and candidate.results:
                probe = candidate
                probes.append(score_probe_result(candidate))
                break
            result.discovery_attempts.append(candidate)
            if candidate.status == ProbeStatus.BLOCKED:
                break
        if probe is None:
            result.probes = [score_probe_result(p) for p in result.discovery_attempts]
            result.blocked = any(p.status == ProbeStatus.BLOCKED for p in result.discovery_attempts)
            result.error_message = "No readable positive catalog control" if result.discovery_attempts else "No catalog categories/products discovered"
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return score_scan(result)
        catalog_sample = list(probe.results)
        for seed in [c for c in nav_categories[:3] if c != control_query]:
            sampled = self._fetch_search_results(site_info.search_url_template, seed)
            if sampled[2] in (ProbeStatus.SUCCESS, ProbeStatus.REDIRECT):
                catalog_sample.extend(sampled[0])
        catalog_sample = list({(r.url or r.title):r for r in catalog_sample}.values())
        generator.featured_items = [r.title for r in catalog_sample]
        result.inapplicable = {}
        from .battery import build_battery
        pairs = build_battery(generator, catalog_sample)
        tested = {ProbeType.CONTROL_QUERY}
        for pair in pairs:
            control = self._fetch_search_results(site_info.search_url_template, pair.control)
            observation = self._run_probe(pair.kind, site_info.search_url_template,
                pair.query, control_query=pair.control, control_count=control[1],
                rationale=f"Catalog-grounded {pair.kind.value}: {pair.evidence or pair.control}")
            observation.control_results = control[0]
            observation.control_screenshot_path = control[4]
            observation.expected_title = pair.expected_title or None
            observation.expected_url = pair.expected_url or None
            observation.constraints = pair.constraints
            observation.catalog_evidence = pair.evidence
            observation.grounded = pair.grounded
            scored = score_probe_result(observation)
            # Repeat prospective failures in a fresh browser context, preserving first evidence.
            if scored.score == ProbeScore.FAIL:
                self._query_cache.pop((site_info.search_url_template, pair.query), None)
                repeated = self._fetch_search_results(site_info.search_url_template, pair.query,
                    f"repeat_{pair.kind.value}_{len(probes)}")
                observation.repeated = (repeated[1] == observation.result_count and
                    repeated[2] == observation.status and
                    [r.title for r in repeated[0]] == [r.title for r in observation.results])
                scored = score_probe_result(observation)
            probes.append(scored)
            tested.add(pair.kind)
        zero_query, rationale = generator.generate_zero_result_check()
        zero = self._run_probe(ProbeType.ZERO_RESULT_CHECK, site_info.search_url_template,
            zero_query, control_query=control_query, control_count=probe.result_count,
            rationale=rationale)
        probes.append(score_probe_result(zero))
        tested.add(ProbeType.ZERO_RESULT_CHECK)
        result.inapplicable = {kind.value: "No qualifying catalog-grounded pair in sampled navigation/products"
                               for kind in ProbeType if kind not in tested}
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
        
        screenshot_name = f"{probe_type.value}_{query}"
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
            result_count_exact=self._count_exact.get((search_url_template, query), False),
            control_count_exact=self._count_exact.get((search_url_template, control_query), False),
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

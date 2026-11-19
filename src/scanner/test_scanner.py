from scanner.models import ProbeResult, ProbeType, ProbeStatus, ProbeScore, ScanResult, SiteInfo
from scanner.scorer import score_probe_result, score_scan


def test_partial_zero_is_not_a_search_failure():
    probe = ProbeResult(probe_type=ProbeType.ZERO_RESULT_CHECK, query='nonsense',
                        status=ProbeStatus.PARTIAL)
    assert score_probe_result(probe).score == ProbeScore.ERROR


def test_error_scan_does_not_pass():
    probe = ProbeResult(probe_type=ProbeType.CONTROL_QUERY, query='boots', status=ProbeStatus.ERROR)
    result = ScanResult(site=SiteInfo(domain='example.com'), probes=[score_probe_result(probe)])
    assert score_scan(result).overall_score == ProbeScore.ERROR


def test_zero_control_cannot_support_comparison():
    probe = ProbeResult(probe_type=ProbeType.TYPO, query='bots', control_query='boots',
                        control_count=0, status=ProbeStatus.SUCCESS)
    assert score_probe_result(probe).score == ProbeScore.ERROR


def test_fetch_preserves_explicit_zero_and_uses_same_screenshot(tmp_path, monkeypatch):
    from scanner.scanner import Scanner
    from src.models import FetchOutcome, FetchStatus, SearchResult
    from src import fetcher
    scanner = Scanner(str(tmp_path))
    visits = []
    def load(url, name):
        visits.append(url)
        return dict(html='<main>No results</main>', final_url=url), 'same-visit.png'
    monkeypatch.setattr(scanner, '_load_page', load)
    monkeypatch.setattr(fetcher, '_analyse_page', lambda **kw: FetchOutcome(
        query=kw['query'], status=FetchStatus.ZERO_CONFIRMED, total_hits=0,
        results=[SearchResult(rank=1, title='Recommendation')]))
    results, count, status, error, shot = scanner._fetch_search_results('https://example.com/search?q={}', 'a & b')
    assert count == 0
    assert status == ProbeStatus.SUCCESS
    assert shot == 'same-visit.png'
    scanner._fetch_search_results('https://example.com/search?q={}', 'a & b')
    assert visits == ['https://example.com/search?q=a+%26+b']


def test_unverified_zero_is_error(tmp_path, monkeypatch):
    from scanner.scanner import Scanner
    from src.models import FetchOutcome, FetchStatus
    from src import fetcher
    scanner = Scanner(str(tmp_path))
    monkeypatch.setattr(scanner, '_load_page', lambda *args: (dict(html='empty', final_url='https://example.com'), None))
    monkeypatch.setattr(fetcher, '_analyse_page', lambda **kw: FetchOutcome(
        query=kw['query'], status=FetchStatus.ZERO_UNVERIFIED, evidence='No marker'))
    assert scanner._fetch_search_results('https://example.com?q={}', 'test')[2] == ProbeStatus.ERROR


def test_current_cotswold_tiles():
    from bs4 import BeautifulSoup
    from src.fetcher import _try_cotswoldoutdoor
    soup = BeautifulSoup('''<div data-testid="product-tile">
    <a href="/p/rab-jacket-123.html"><header data-testid="product-tile-title-header">
    <div data-testid="product-tile-brand">Rab</div><div data-testid="product-tile-title">Down Jacket</div>
    </header></a><span data-testid="product-tile-price-actual-price">£120.00</span></div>''', 'html.parser')
    results = _try_cotswoldoutdoor(soup, 10)
    assert len(results) == 1
    assert results[0].title == 'Rab Down Jacket'
    assert results[0].price == '£120.00'


def test_discovery_filters_utility_links(tmp_path, monkeypatch):
    from scanner.scanner import Scanner
    scanner = Scanner(str(tmp_path))
    html = '''<html lang="en"><nav><a>B2B</a><a>Men</a><a>Jackets</a><a>Waterproof Jackets</a></nav>
    <form action="/lister.html"><input name="q" type="search"></form></html>'''
    monkeypatch.setattr(scanner, '_load_page', lambda *args: (dict(html=html, final_url='https://example.com'), None))
    info, categories, _, _ = scanner._discover_site('https://example.com')
    assert categories == ['Jackets', 'Waterproof Jackets']
    assert info.search_url_template == 'https://example.com/lister.html?q={}'


def test_cli_batch_is_local(monkeypatch, tmp_path):
    import sys
    from types import SimpleNamespace
    from scanner import cli, batch
    seen = []
    monkeypatch.setattr(batch, 'run_batch', lambda config: seen.append(config) or SimpleNamespace(completed=1, blocked=0, failed=0))
    monkeypatch.setattr(sys, 'argv', ['scanner', '--batch', 'stores.csv', '--headed'])
    cli.main()
    assert seen[0].input_csv == 'stores.csv'
    assert seen[0].headed is True


def test_allbirds_visible_count_and_clean_title():
    from src.fetcher import _analyse_page
    html = '''<html><title>Search</title><main><p data-search-results-count>We found 71 results for "shoes"</p>
    <div data-testid="product-card-123"><a href="/products/mens-cruiser" data-analytics-main-search-card-name="Men's Cruiser">FINAL SALE Quick add</a><span>$105</span></div>
    </main></html>'''
    outcome = _analyse_page(html=html, url='https://www.allbirds.com/search?q=shoes',
                            final_url='https://www.allbirds.com/search?q=shoes', query='shoes',
                            max_results=1, allow_llm=False)
    assert outcome.total_hits == 71
    assert outcome.results[0].title == "Men's Cruiser"


def test_newsletter_captcha_does_not_block_shopify_results():
    from src.fetcher import _detect_block
    html = '''<html><title>Search</title><script src="https://google.com/recaptcha/api.js"></script>
    <main><p data-search-results-count>We found 1 result</p><div data-testid="product-card-123">
    <a href="/products/shoe" data-analytics-main-search-card-name="Shoe">Shoe</a></div></main></html>'''
    assert _detect_block(html, 200, 'https://www.allbirds.com/search?q=shoe') is None


def test_llm_call_uses_supported_arguments_and_current_cost(monkeypatch):
    from types import SimpleNamespace
    from scanner.probes import ProbeGenerator
    generator = ProbeGenerator(SiteInfo(domain='example.com'), ['Jackets'], [], [])
    def create(*, model, max_tokens, messages):
        return SimpleNamespace(usage=SimpleNamespace(input_tokens=100, output_tokens=20),
                               content=[SimpleNamespace(type='text', text='coat')])
    generator._client = SimpleNamespace(messages=SimpleNamespace(create=create))
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key-never-sent')
    assert generator._llm_pick_terms('synonym') == ['coat']
    assert abs(generator.llm_cost_usd - 0.0002) < 1e-10


def test_allbirds_confirmed_zero_ignores_newsletter_captcha():
    from src.fetcher import _analyse_page
    html = '''<html><title>Search</title><script src="https://google.com/recaptcha/api.js"></script>
    <main><p data-search-results-count>We found 0 results for "nonsense"</p></main></html>'''
    outcome = _analyse_page(html=html, url='https://www.allbirds.com/search?q=nonsense',
                            final_url='https://www.allbirds.com/search?q=nonsense', query='nonsense',
                            max_results=10, allow_llm=False)
    assert outcome.status == 'zero_confirmed'
    assert outcome.total_hits == 0


def test_narrower_counts_do_not_prove_color_or_price_constraints():
    probe = ProbeResult(probe_type=ProbeType.CONSTRAINT_QUERY, query='black shoes under 50',
                        control_query='shoes', control_count=71, result_count=61,
                        status=ProbeStatus.SUCCESS)
    assert score_probe_result(probe).score == ProbeScore.PARTIAL


def test_bergzeit_titles_exclude_promotions_and_sizes():
    from bs4 import BeautifulSoup
    from src.fetcher import _try_bergzeit
    soup = BeautifulSoup('''<a class="products-list__product-box" href="/p/rab-jacket/1234567/">
    <span>Experten Tipp -5 % on top +2</span><div class="product-box-content__brand">Rab | Wanderjacken</div>
    <div class="product-box-content__name">Herren Jacke</div><div>XXS XS S M L</div></a>''', 'html.parser')
    assert _try_bergzeit(soup, 10)[0].title == 'Rab Herren Jacke'

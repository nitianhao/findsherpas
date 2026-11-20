from types import SimpleNamespace
from scanner.battery import build_battery, numeric_price
from scanner.models import ProbeResult, ProbeType as P, ProbeStatus, ProbeScore as S, SearchResult
from scanner.scorer import score_probe_result


def product(title='Women waterproof leather boots 39', rank=1, price='€80'):
    return SearchResult(rank=rank,title=title,url='/products/boots',price=price)


def observation(**kwargs):
    values = dict(probe_type=P.MERGED_WORDS, query='LeatherBoots', control_query='Leather Boots',
        result_count=0, control_count=10, control_results=[product()], status=ProbeStatus.SUCCESS,
        screenshot_path='query.png',control_screenshot_path='control.png',grounded=True)
    values.update(kwargs)
    return ProbeResult(**values)


def test_zero_needs_repeat_for_high_confidence_and_review_for_proof():
    assert score_probe_result(observation()).confidence == 'medium'
    scored = score_probe_result(observation(repeated=True))
    assert scored.confidence == 'high'
    assert not scored.proof_eligible
    scored.verified = True
    assert scored.proof_eligible


def test_disjoint_nonzero_counts_do_not_pass_or_fail():
    scored = score_probe_result(observation(result_count=10,
        results=[SearchResult(rank=1,title='Irrelevant')]))
    assert scored.score == S.PARTIAL


def test_constraint_zero_without_qualifying_product_is_inconclusive():
    assert score_probe_result(observation(probe_type=P.CONSTRAINT_QUERY)).score == S.PARTIAL


def test_missing_colour_is_unknown_not_contradiction():
    assert score_probe_result(observation(probe_type=P.CONSTRAINT_QUERY, result_count=1,
        results=[product()], constraints={'colour':'black'})).score == S.PARTIAL


def test_price_violation_and_locale_parsing():
    assert numeric_price('1.299,95 €') == 1299.95
    assert numeric_price('1 299,95 Kč') == 1299.95
    assert numeric_price('from £20') is None
    scored = score_probe_result(observation(probe_type=P.PRICE_CONSTRAINT, result_count=1,
        results=[product(price='€120')], constraints={'price_max':'100'}, repeated=True))
    assert scored.score == S.FAIL
    assert scored.confidence == 'high'


def test_reference_must_be_in_control():
    assert score_probe_result(observation(expected_title='Invented boot', repeated=True)).score == S.PARTIAL


def test_exact_rank_four_is_failure_rank_three_passes():
    for rank, expected in [(3,S.PASS),(4,S.FAIL)]:
        scored = score_probe_result(observation(probe_type=P.RANKING_CHECK,
            result_count=10,results=[product(rank=rank)],expected_title=product().title))
        assert scored.score == expected


def test_generated_controls_and_attributes_are_validated():
    import json
    generator = SimpleNamespace(nav_categories=['Leather Boots','Rain Jackets','Walking Shoes'],
        brands=[],site=SimpleNamespace(primary_language='English'),
        _llm_pick_terms=lambda *args,**kwargs:[json.dumps([
            {'kind':'constraint_query','query':'black boots','control':product().title,
             'constraints':{'colour':'black'}},
            {'kind':'abbreviation','query':'TV','control':'television'},
            {'kind':'plural_singular','query':'Leather Boot','control':'Leather Boots'}])])
    pairs = build_battery(generator,[product()])
    assert sum(p.kind == P.MERGED_WORDS for p in pairs) == 3
    assert not any(p.query == 'black boots' for p in pairs)
    assert not any(p.control == 'television' for p in pairs)
    assert any(p.kind == P.PLURAL_SINGULAR for p in pairs)


def test_javascript_form_uses_observed_search_link(tmp_path, monkeypatch):
    from scanner.scanner import Scanner
    s = Scanner(str(tmp_path))
    html = '<html><form><input name="q"></form><a href="/search?q=Socks">Socks</a><a href="/collections/jackets">Jackets</a></html>'
    monkeypatch.setattr(s,'_load_page', lambda *args: (dict(html=html,final_url='https://example.com'),None))
    info,categories,_,_ = s._discover_site('https://example.com')
    assert info.search_url_template == 'https://example.com/search?q={}'
    assert 'Socks' in categories and 'Jackets' in categories


def test_unreviewed_failures_are_never_exported(tmp_path):
    import json
    from scanner.batch import export_for_benchmark
    from scanner.models import ScanResult, SiteInfo
    scored = score_probe_result(observation(repeated=True))
    scan = ScanResult(site=SiteInfo(domain='example.com'),overall_score=S.FAIL,probes=[scored])
    path = tmp_path/'batch.json'
    path.write_text(json.dumps({'results':[scan.model_dump(mode='json')]}))
    exported = export_for_benchmark(str(path))
    assert json.loads(open(exported).read())['proof_cards'] == []
    scored.verified = True
    scan.probes = [scored]
    path.write_text(json.dumps({'results':[scan.model_dump(mode='json')]}))
    assert len(json.loads(open(export_for_benchmark(str(path))).read())['proof_cards']) == 1


def test_catalog_vocabulary_excludes_country_and_utility_menus():
    from scanner.catalog import catalog_categories
    from bs4 import BeautifulSoup
    soup = BeautifulSoup('''<nav><a href="https://other.com">Belgium</a><a href="/reklamace">Reklamace</a></nav>
    <header><a href="/obleceni/">Oblečení</a><a href="/collections/waterproof">Waterproof Jackets</a></header>
    <footer><a href="/collections/utility">Bad footer</a></footer>''','html.parser')
    assert catalog_categories(soup,'https://example.com',[]) == ['Waterproof Jackets','Oblečení']


def test_store_scoped_adapter_ignores_menu_recommendations():
    from scanner.storefronts import scoped_products
    html = '''<nav><a href="/products/unrelated"><div class="ellipsis-2-line">Noise</div></a></nav>
    <div id="klevu-search-results"><a href="/products/jacket"><div class="ellipsis-2-line">Rain Jacket</div>
    <span class="text-purpleNavy">€120</span></a></div>'''
    products = scoped_products(html,'https://finisterre.com/search?q=Jacket',5)
    assert [p.title for p in products] == ['Rain Jacket']
    assert products[0].price == '€120'


def test_connox_shadow_card_keeps_brand_and_sale_price():
    from scanner.storefronts import scoped_products
    html = '''<section data-scanner-shadow-evidence><div class="br-product-card">
    <a class="br-product-card__link" href="https://www.connox.de/products/chair"><div class="br-product-card__brand">Carl Hansen</div>
    <h3 class="br-product-card__title">CH24 Wishbone Chair</h3><span class="br-product-card__price-sale">814,00 €</span></a></div></section>'''
    results = scoped_products(html,'https://www.connox.de/search?q=Stuhl',5)
    assert results[0].title == 'Carl Hansen CH24 Wishbone Chair'
    assert results[0].price == '814,00 €'


def test_llm_cannot_invent_constraint_words_or_call_rewrites_compound_splits():
    import json
    generator = SimpleNamespace(nav_categories=['Gloves'],brands=[],site=SimpleNamespace(primary_language='English'),
        _llm_pick_terms=lambda *a,**kw:[json.dumps([
            {'kind':'constraint_query','query':'3mm neoprene gloves','control':'3mm Yulex Gloves','constraints':{'size':'3mm'}},
            {'kind':'compound_split','query':'water gloves','control':'3mm Yulex Gloves'}])])
    pairs = build_battery(generator,[product('3mm Yulex Gloves')])
    assert not any(p.kind in (P.CONSTRAINT_QUERY,P.COMPOUND_SPLIT) for p in pairs)


def test_brand_model_query_cannot_append_invented_product_type():
    import json
    generator = SimpleNamespace(nav_categories=['Oblečení'],brands=['RAFIKI'],site=SimpleNamespace(primary_language='Czech'),
        _llm_pick_terms=lambda *a,**kw:[json.dumps([
            {'kind':'brand_search','query':'RAFIKI CRIMP alpinistická bunda','control':'RAFIKI CRIMP'}])])
    assert not any(p.query == 'RAFIKI CRIMP alpinistická bunda' for p in build_battery(generator,[product('RAFIKI CRIMP')]))


def test_semantic_zero_is_a_review_candidate_not_a_failure():
    assert score_probe_result(observation(probe_type=P.NATURAL_LANGUAGE,grounded=False,repeated=True)).score == S.PARTIAL


def test_model_code_outside_first_exact_name_targets_is_tested():
    generator = SimpleNamespace(nav_categories=['Furniture'],brands=[],site=SimpleNamespace(primary_language='English'),
        _llm_pick_terms=lambda *a,**kw:[])
    items = [product('Chair'), product('Table'), product('Lamp'), product('Carl Hansen CH24 Wishbone Chair')]
    assert any(p.kind == P.SKU_SEARCH and p.query == 'CH24' for p in build_battery(generator,items))


def test_scoped_recommendations_never_override_authoritative_zero(tmp_path, monkeypatch):
    from scanner.scanner import Scanner
    from scanner import storefronts
    from src import fetcher
    from src.models import FetchOutcome, FetchStatus
    s = Scanner(str(tmp_path))
    monkeypatch.setattr(s,'_load_page',lambda *a:(dict(html='zero',final_url='https://finisterre.com/search?q=no'), 'zero.png'))
    monkeypatch.setattr(fetcher,'_analyse_page',lambda **kw:FetchOutcome(query='no',status=FetchStatus.ZERO_CONFIRMED,total_hits=0))
    monkeypatch.setattr(storefronts,'scoped_products',lambda *a:[product()])
    results,count,status,_,_ = s._fetch_search_results('https://finisterre.com/search?q={}','no')
    assert count == 0 and results == [] and status == ProbeStatus.SUCCESS


def test_capture_names_survive_consent_loop_and_differ_per_query(tmp_path,monkeypatch):
    from scanner.scanner import Scanner
    from src import fetcher
    from pathlib import Path
    class Empty:
        def count(self): return 0
    class Page:
        frames=[]
        def set_default_timeout(self,*a): pass
        def on(self,*a): pass
        def goto(self,url,**kw): self.url=url;return SimpleNamespace(status=200)
        def wait_for_timeout(self,*a): pass
        def title(self): return 'Search'
        def get_by_role(self,*a,**kw): return Empty()
        def content(self): return '<html><body><main>Search products</main></body></html>'
        def evaluate(self,script): return ''
        def screenshot(self,path,**kw): Path(path).write_bytes(b'fixture')
    class Context:
        def new_page(self): return Page()
        def close(self): pass
    s=Scanner(str(tmp_path))
    monkeypatch.setattr(s,'_get_browser',lambda:SimpleNamespace(new_context=lambda **kw:Context()))
    for helper in ['_apply_stealth','_dismiss_consent_banners','_wait_for_host_ready']:
        monkeypatch.setattr(fetcher,helper,lambda *a:None)
    _,first=s._load_page('https://example.com/search?q=a','probe_a')
    _,second=s._load_page('https://example.com/search?q=b','probe_b')
    assert first != second and 'probe_a' in first and 'probe_b' in second


def test_database_payload_also_requires_review_without_network(monkeypatch):
    import json
    from scanner.db import InstantDBClient
    from scanner.models import ScanResult, SiteInfo
    client=InstantDBClient.__new__(InstantDBClient)
    operations=[]
    monkeypatch.setattr(client,'_transact',lambda ops:operations.extend(ops))
    scored=score_probe_result(observation(repeated=True))
    scan=ScanResult(site=SiteInfo(domain='example.com'),probes=[scored])
    client.push_benchmark_scan(scan)
    assert json.loads(operations[0][3]['proof_cards']) == []


def test_recommendation_fallback_for_gibberish_is_not_automatically_a_failure():
    p=observation(probe_type=P.ZERO_RESULT_CHECK,result_count=4,results=[product()])
    assert score_probe_result(p).score == S.PARTIAL


def test_unknown_positive_seed_is_a_technical_error_not_search_failure():
    p=ProbeResult(probe_type=P.CONTROL_QUERY,query='NAKUPOVAŤ',status=ProbeStatus.SUCCESS,result_count=0)
    assert score_probe_result(p).score == S.ERROR


def test_visible_store_totals_are_distinct_from_samples_including_zero():
    from scanner.storefronts import scoped_count
    assert scoped_count('<main>Produkty (10000)</main>','https://rockpoint.cz/search') == 10000
    assert scoped_count('<main>Sökningen på "x" matchade 0 produkter</main>','https://designtorget.se/search') == 0


def test_promotional_collection_ctas_are_not_catalog_queries():
    from scanner.catalog import catalog_categories
    from bs4 import BeautifulSoup
    html='<header><a href="/collections/womens">Explore Women\'s</a><a href="/collections/socks">NAKUPOVAŤ</a><a href="/collections/fleece">Fleece</a></header>'
    assert catalog_categories(BeautifulSoup(html,'html.parser'),'https://example.com',[]) == ['Fleece']


def test_catalog_brand_and_abbreviation_generate_grounded_pairs():
    generator=SimpleNamespace(nav_categories=['Furniture'],brands=[],site=SimpleNamespace(primary_language='German'),
        _llm_pick_terms=lambda *a,**kw:[])
    item=product('Onix TV-Möbel');item.brand='Kave Home'
    pairs=build_battery(generator,[item])
    assert any(p.kind == P.BRAND_SEARCH and p.query == 'Kave Home Onix TV-Möbel' for p in pairs)
    assert any(p.kind == P.TYPO and p.control == item.title and p.query != item.title for p in pairs)
    assert any(p.kind == P.ABBREVIATION and p.query == 'Onix Fernsehmöbel' for p in pairs)


def test_identical_screenshot_files_cannot_be_proof():
    scored=score_probe_result(observation(repeated=True,control_screenshot_path='query.png'))
    scored.verified=True
    assert scored.confidence != 'high' and not scored.proof_eligible


def test_navigation_accents_and_observed_units_are_not_missed():
    generator=SimpleNamespace(nav_categories=['Oblečení'],brands=[],site=SimpleNamespace(primary_language='Czech'),
        _llm_pick_terms=lambda *a,**kw:[])
    pairs=build_battery(generator,[product('MiiR 12oz Flip Traveller')])
    assert any(p.kind == P.DIACRITICS and p.query == 'Obleceni' for p in pairs)
    assert any(p.kind == P.FORMAT_VARIANT and p.query == 'MiiR 12 oz Flip Traveller' for p in pairs)
    assert any(p.kind == P.ABBREVIATION and p.query == 'MiiR 12 ounce Flip Traveller' for p in pairs)


def test_explicit_faux_material_and_opposing_gender_do_not_pass():
    from scanner.evidence import attribute_check
    assert attribute_check('material','leather','Faux leather boots') is False
    assert attribute_check('material','Leder','Kunstleder Jacke') is False
    assert attribute_check('gender',"men's","Women's cotton shirt") is False
    assert attribute_check('gender','Damen','Herren Jacke') is False
    assert attribute_check('colour','black','Blue boots') is None
    assert attribute_check('material','wool','Warm jumper') is None


def test_brand_typo_really_changes_the_observed_brand():
    from scanner.probes import generate_typo
    assert generate_typo('Craghoppers') == 'craghopers'
    generator=SimpleNamespace(nav_categories=['Clothing'],brands=[],site=SimpleNamespace(primary_language='English'),
        _llm_pick_terms=lambda *a,**kw:[])
    item=product('Alma Shirt');item.brand='Gucci'
    pairs=build_battery(generator,[item])
    assert not any(p.kind==P.TYPO and p.query=='Gucci Alma Shirt' for p in pairs)

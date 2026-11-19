"""Offline tests for the candidate pilot's evidence and execution boundaries."""
import unittest
from src.candidates.contracts import Fact, Product, Candidate
from src.candidates.validation import ground_fact, validate_candidate


def product(pid='p'):
    return Product(id=pid, name='Cup', url='https://example.com/cup?id='+pid,
                   text='Krus uden hank. Kapacitet 1,5 L. Antal 6. Højde 20 cm. Diameter 15,5 cm.')


class EvidenceTests(unittest.TestCase):
    def test_missing_quote_or_foreign_source_rejected(self):
        for pid, quote in [('p', 'Invented specification'), ('other', 'Krus uden hank.')]:
            f=Fact(id='f', product_id=pid, attribute='handle', value='none', quote=quote)
            self.assertIsNotNone(ground_fact(f, product()))

    def test_capacity_normalization_and_distinct_dimension_axes(self):
        f=Fact(id='f', product_id='p', attribute='capacity', value='1,5', unit='L', quote='Kapacitet 1,5 L.')
        self.assertIsNone(ground_fact(f, product()))
        self.assertEqual(f.normalized_value, '1500')
        self.assertEqual(f.normalized_unit, 'ml')
        f=Fact(id='h', product_id='p', attribute='height', value='20', unit='cm', quote='Højde 20 cm.')
        self.assertIsNone(ground_fact(f, product()))
        self.assertEqual(f.attribute,'height')
        self.assertEqual(f.normalized_unit,'mm')

    def test_invented_numeric_value_or_unit_rejected(self):
        for value, unit in [('9','L'),('1,5','kg'),('NaN','L')]:
            f=Fact(id='f',product_id='p',attribute='capacity',value=value,unit=unit,quote='Kapacitet 1,5 L.')
            self.assertIsNotNone(ground_fact(f, product()))

    def test_missing_coverage_evidence_rejected(self):
        c=Candidate(mode='negation',positive_ids=['p'],fact_ids=['unknown'],rationale='looks good')
        self.assertTrue(validate_candidate(c, {'p':product()}, {}))

    def test_material_mention_does_not_prove_no_coating(self):
        fs=[Fact(id='t',product_id='p',attribute='product_type',value='pan',quote='Cup'),
            Fact(id='m',product_id='p',attribute='material',value='stainless_steel',quote='Cup')]
        c=Candidate(mode='combined_exclusions',positive_ids=['p'],fact_ids=['t','m'],rationale='steel')
        self.assertTrue(validate_candidate(c,{'p':product()},{f.id:f for f in fs}))

    def test_quote_must_be_specific_not_entire_page(self):
        with self.assertRaises(ValueError):
            Fact(id='f',product_id='p',attribute='handle',value='none',quote='x'*601)


class CollectionTests(unittest.TestCase):
    def test_search_offsite_and_unobserved_links_rejected(self):
        from src.candidates.collection import allowed_url, select_observed
        from src.candidates.contracts import Link, Selection
        for url in ['https://other.example/product','https://www.imerco.dk/search?query=pan',
                    'https://www.imerco.dk/foo?q=pan','https://www.imerco.dk.evil.test/foo',
                    'http://www.imerco.dk/foo']:
            self.assertFalse(allowed_url(url),url)
        self.assertTrue(allowed_url('https://www.imerco.dk/borddaekning/glas'))
        with self.assertRaises(ValueError):
            select_observed(Selection(ids=['invented'],reason=''),[Link(id='known',url='https://www.imerco.dk/x',text='x')],7)

    def test_detail_page_must_confirm_product_identity(self):
        from src.candidates.collection import detail_product
        from src.candidates.contracts import Link
        link=Link(id='123',url='https://www.imerco.dk/x?id=123',text='Cup')
        metadata={'final_url':link.url,'snapshot':'x.html','sha256':'hash','captured_at':'now'}
        with self.assertRaises(ValueError):
            detail_product(link,'<h1>Cup</h1><p>Vare nr. 999</p>',metadata,'category')
        self.assertEqual(detail_product(link,'<h1>Cup</h1><p>Vare nr. 123</p>',metadata,'category').id,'123')


class CallsTests(unittest.TestCase):
    def test_caps_failed_calls_and_cached_resume(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        from src.candidates.runner import Calls, BudgetStop
        from src.candidates.contracts import Selection
        with TemporaryDirectory() as tmp:
            calls=Calls(Path(tmp),max_calls=1,max_usd=1,client=object())
            response=Selection(ids=['x'],reason='observed')
            with patch('src.candidates.runner.structured_call',return_value=response) as api:
                self.assertEqual(calls.call('a',{},Selection,'choose').ids,['x'])
                self.assertEqual(calls.call('a',{},Selection,'choose').ids,['x'])
                self.assertEqual(api.call_count,1)
                with self.assertRaises(BudgetStop):calls.call('b',{},Selection,'choose')
        with TemporaryDirectory() as tmp:
            calls=Calls(Path(tmp),max_usd=.000001,client=object())
            with patch('src.candidates.runner.structured_call') as api:
                with self.assertRaises(BudgetStop):calls.call('a',{},Selection,'choose')
                api.assert_not_called()
        with TemporaryDirectory() as tmp:
            calls=Calls(Path(tmp),client=object())
            with patch('src.candidates.runner.structured_call',side_effect=RuntimeError('unavailable')) as api:
                with self.assertRaises(RuntimeError):calls.call('a',{},Selection,'choose')
                with self.assertRaises(BudgetStop):calls.call('a',{},Selection,'choose')
                self.assertEqual(api.call_count,1)
                self.assertEqual(calls.summary()['requests'],1)
                self.assertGreater(calls.summary()['estimated_usd'],0)

    def test_input_or_prompt_change_is_not_cached(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        from src.candidates.runner import Calls
        from src.candidates.contracts import Selection
        with TemporaryDirectory() as tmp:
            calls=Calls(Path(tmp),client=object())
            with patch('src.candidates.runner.structured_call',return_value=Selection(ids=['x'],reason='')) as api:
                calls.call('a',{'input':1},Selection,'choose')
                calls.call('a',{'input':2},Selection,'choose')
                calls.call('a',{'input':2},Selection,'changed prompt')
                self.assertEqual(api.call_count,3)


class PipelineTests(unittest.TestCase):
    def test_review_rejection_and_fabricated_fact_never_count_as_coverage(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from src.candidates.contracts import FactBatch, CandidateBatch, ReviewBatch, ReviewDecision
        from src.candidates.runner import build_candidates
        p=product()
        class Stub:
            def call(self,stage,payload,schema,instruction):
                if stage.startswith('extract') or stage.startswith('repair_quotes'):
                    return FactBatch(facts=[
                        Fact(product_id='p',attribute='product_type',value='cup',quote='Krus uden hank.'),
                        Fact(product_id='p',attribute='handle',value='none',quote='Krus uden hank.'),
                        Fact(product_id='p',attribute='material',value='solid_oak',quote='Invented oak.')])
                if stage=='match':
                    return CandidateBatch(candidates=[Candidate(mode='negation',positive_ids=['p'],fact_ids=['0:0','0:1'],rationale='')])
                return ReviewBatch(decisions=[ReviewDecision(mode='negation',approved=False,rejected_fact_ids=['0:1'],reason='contradiction')])
            def summary(self):return {'requests':3}
        with TemporaryDirectory() as tmp:
            report=build_candidates([p],Stub(),Path(tmp))
            self.assertEqual(report['covered_modes'],0)
            self.assertEqual(report['coverage']['negation']['status'],'rejected')
            self.assertGreaterEqual(len(report['rejected_facts']),1)

    def test_budget_exhaustion_leaves_checkpoint_and_uncovered_modes(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from src.candidates.runner import build_candidates, BudgetStop
        class Stub:
            def call(self,*a,**kw):raise BudgetStop('budget exhausted')
            def summary(self):return {'requests':0}
        with TemporaryDirectory() as tmp:
            report=build_candidates([product()],Stub(),Path(tmp))
            self.assertEqual(report['status'],'incomplete')
            self.assertEqual(report['covered_modes'],0)
            self.assertTrue((Path(tmp)/'report.json').exists())


class RegressionTests(unittest.TestCase):
    def test_existing_but_irrelevant_quote_cannot_prove_uncoated(self):
        p=Product(id='p',name='Pan',url='https://example.com/p',text='Rustfrit stål Jævn varmefordeling Til alle komfurer. Stegepanden har ingen belægning.')
        wrong=Fact(product_id='p',attribute='coating',value='none',quote='Rustfrit stål Jævn varmefordeling Til alle komfurer')
        right=Fact(product_id='p',attribute='coating',value='none',quote='Stegepanden har ingen belægning.')
        self.assertIsNotNone(ground_fact(wrong,p))
        self.assertIsNone(ground_fact(right,p))


class NavigationRegressionTests(unittest.TestCase):
    def test_late_furniture_category_is_not_silently_dropped(self):
        from src.candidates.collection import nav_links
        html=''.join(f'<a href="/borddaekning/cat{i}">Category {i}</a>' for i in range(235))
        html+='<a href="/bolig/moebler/borde">Borde</a>'
        links=nav_links(html)
        self.assertEqual(links[-1].text,'Borde')
        self.assertEqual(len(links),236)


class ResumeIntegrityTests(unittest.TestCase):
    def test_cli_rejects_edited_product_checkpoint(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from src.candidates.__main__ import main
        with TemporaryDirectory() as tmp:
            path=Path(tmp); fixture=path/'input.json'; out=path/'run'
            fixture.write_text(json.dumps([{'id':'p','url':'https://www.imerco.dk/p?id=p','text':'Cup Sammenlign Porcelain'}]))
            args=['candidates','--replay',str(fixture),'--out',str(out)]
            with patch('src.candidates.__main__.load_dotenv'),patch('sys.argv',args),patch('src.candidates.__main__.build_candidates',return_value={'status':'complete','covered_modes':0,'cost':{}}):
                main()
            (out/'products.json').write_text('[]')
            with patch('src.candidates.__main__.load_dotenv'),patch('sys.argv',args+['--resume']),patch('src.candidates.__main__.build_candidates') as build:
                with self.assertRaises(SystemExit):main()
                build.assert_not_called()


class RepairAndCurrencyTests(unittest.TestCase):
    def test_danish_currency_alias_preserves_original_and_normalizes(self):
        p=Product(id='p',name='Pan',url='https://www.imerco.dk/p',text='499,95 Medlemspris')
        f=Fact(product_id='p',attribute='price_member',value='499,95',unit='kr',quote='499,95 Medlemspris')
        self.assertIsNone(ground_fact(f,p))
        self.assertEqual(f.unit,'kr')
        self.assertEqual(f.normalized_unit,'DKK')
        self.assertEqual(f.normalized_value,'499.95')

    def test_bounded_quote_repair_uses_source_and_cannot_promote_invented_quote(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from src.candidates.contracts import FactBatch, CandidateBatch
        from src.candidates.runner import build_candidates
        class Stub:
            stages=[]
            def call(self,stage,payload,schema,instruction):
                self.stages.append(stage)
                if stage.startswith('extract') or stage.startswith('repair_quotes'):
                    return FactBatch(facts=[Fact(product_id='p',attribute='material',value='solid_oak',quote='Absent oak quote')])
                return CandidateBatch(candidates=[])
            def summary(self):return {}
        stub=Stub()
        with TemporaryDirectory() as tmp:
            result=build_candidates([product()],stub,Path(tmp))
            self.assertEqual(stub.stages,['extract_0','repair_quotes_0','match'])
            self.assertEqual(result['facts'],[])
            self.assertEqual(result['covered_modes'],0)
            self.assertEqual(len(result['rejected_facts']),2)

    def test_replay_retains_live_capture_provenance(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from src.candidates.runner import replay_products
        p=product().model_dump();p.update(captured_at='2026-11-03T12:00:00Z',source_hash='htmlhash',category_urls=['https://www.imerco.dk/bolig/moebler'])
        with TemporaryDirectory() as tmp:
            f=Path(tmp)/'products.json';f.write_text(json.dumps([p]))
            got=replay_products(f)[0]
            self.assertEqual(got.captured_at,p['captured_at'])
            self.assertEqual(got.source_hash,'htmlhash')
            self.assertEqual(got.category_urls,p['category_urls'])


if __name__ == '__main__':
    unittest.main()

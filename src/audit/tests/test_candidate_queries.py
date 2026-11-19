"""Grounded query suites: no storefront or model network calls."""
import unittest
from src.candidates.contracts import Candidate, Fact, Product
from src.candidates.query_cases import Draft, compile_brief, compile_case, validate_draft


def facts(pid='p'):
    return {
        't':Fact(id='t',product_id=pid,attribute='product_type',value='jug',quote='Kande'),
        'c':Fact(id='c',product_id=pid,attribute='capacity',value='0,70',unit='L',quote='Kapacitet 0,70 L',normalized_value='700',normalized_unit='ml'),
        'm':Fact(id='m',product_id=pid,attribute='material',value='porcelain',quote='Materiale Porcelæn'),
    }


class QueryContractTests(unittest.TestCase):
    def test_unit_conversion_uses_equivalent_capacity_not_new_size(self):
        c=Candidate(mode='unit_conversion',positive_ids=['p'],fact_ids=['t','c'],rationale='')
        brief=compile_brief(c,facts())
        d=Draft(mode='unit_conversion',anchor_product_id='p',baseline_query='kande 0,70 liter',test_queries=['kande 700 ml'])
        self.assertEqual(validate_draft(d,brief),[])
        case=compile_case(d,brief)
        self.assertEqual(case['steps'][0]['requirements'],case['steps'][1]['requirements'])
        self.assertEqual(case['steps'][1]['requirements'][-1]['value'],'700')
        self.assertEqual(case['steps'][1]['requirements'][-1]['unit'],'ml')
        self.assertIn('equivalent',case['success_rule'])

    def test_unverified_anchor_or_invented_number_is_rejected(self):
        brief=compile_brief(Candidate(mode='unit_conversion',positive_ids=['p'],fact_ids=['t','c'],rationale=''),facts())
        for anchor,query in [('invented','kande 700 ml'),('p','kande 900 ml')]:
            d=Draft(mode='unit_conversion',anchor_product_id=anchor,baseline_query='kande 0,70 liter',test_queries=[query])
            self.assertTrue(validate_draft(d,brief))

    def test_specificity_has_exactly_two_controlled_additions(self):
        brief=compile_brief(Candidate(mode='specificity',positive_ids=['p'],fact_ids=['t','c','m'],rationale=''),facts())
        d=Draft(mode='specificity',anchor_product_id='p',baseline_query='kande',test_queries=['kande i porcelæn','kande i porcelæn 0,70 liter'])
        self.assertEqual(validate_draft(d,brief),[])
        case=compile_case(d,brief)
        self.assertEqual([len(s['requirements']) for s in case['steps']],[1,2,3])
        d.test_queries=['kande i porcelæn']
        self.assertTrue(validate_draft(d,brief))

    def test_nonmember_budget_uses_public_contrast_as_eligible_anchor(self):
        fs={}
        for fid,pid,attr,value in [('a','member','product_type','pan'),('b','member','price_member','499,95'),
            ('c','member','price_regular','1499,95'),('d','public','product_type','pan'),('e','public','price_public','299,95')]:
            fs[fid]=Fact(id=fid,product_id=pid,attribute=attr,value=value,unit='DKK' if attr.startswith('price') else '',quote='fixture',normalized_value=value.replace(',','.') if attr.startswith('price') else '',normalized_unit='DKK' if attr.startswith('price') else '')
        c=Candidate(mode='conditional_price',positive_ids=['member'],contrast_ids=['public'],fact_ids=list(fs),rationale='')
        b=compile_brief(c,fs)
        self.assertEqual([a['product_id'] for a in b['anchors']],['public'])
        d=Draft(mode='conditional_price',anchor_product_id='public',baseline_query='stegepande',test_queries=['stegepande under 500 kr'])
        case=compile_case(d,b)
        self.assertEqual(case['context']['membership'],'nonmember')
        self.assertEqual(case['steps'][1]['requirements'][-1]['operator'],'lt')
        self.assertEqual(case['known_ineligible_product_ids'],['member'])
        d.anchor_product_id='member'
        self.assertTrue(validate_draft(d,b))


class InputAndReviewTests(unittest.TestCase):
    def fixture(self,path):
        import json
        ps=[Product(id='p',name='Jug',url='https://www.imerco.dk/jug?id=p',text='Kande. Kapacitet 0,70 L. Materiale Porcelæn.').model_dump()]
        fs=facts()
        c=Candidate(mode='unit_conversion',positive_ids=['p'],fact_ids=['t','c'],rationale='')
        report={'status':'complete','facts':[f.model_dump() for f in fs.values()],
                'candidates':[c.model_dump()],'coverage':{'unit_conversion':{'status':'verified_candidate'},'either_or':{'status':'rejected'}}}
        (path/'products.json').write_text(json.dumps(ps))
        (path/'report.json').write_text(json.dumps(report))
        return report

    def test_rejected_or_tampered_source_cannot_seed_queries(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from src.candidates.query_cases import load_input
        with TemporaryDirectory() as tmp:
            path=Path(tmp);r=self.fixture(path)
            load_input(path)
            r['coverage']['unit_conversion']['status']='rejected'
            (path/'report.json').write_text(json.dumps(r))
            with self.assertRaises(ValueError):load_input(path)
            r['coverage']['unit_conversion']['status']='verified_candidate'
            r['facts'][1]['quote']='Invented capacity quote'
            (path/'report.json').write_text(json.dumps(r))
            with self.assertRaises(ValueError):load_input(path)

    def test_wording_review_rejection_keeps_case_out_of_accepted_export(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from src.candidates.query_cases import generate, DraftBatch
        from src.candidates.contracts import ReviewBatch, ReviewDecision
        class Stub:
            def call(self,stage,payload,schema,instruction):
                if stage=='draft_queries':
                    return DraftBatch(drafts=[Draft(mode='unit_conversion',anchor_product_id='p',baseline_query='kande 0,70 liter',test_queries=['kande 700 ml'])])
                return ReviewBatch(decisions=[ReviewDecision(mode='unit_conversion',reason='Meaning changed',approved=False)])
            def summary(self):return {}
        with TemporaryDirectory() as tmp:
            path=Path(tmp);self.fixture(path)
            report=generate(path,path/'out',Stub())
            self.assertEqual(report['cases'],[])
            self.assertEqual(report['unaccepted_modes'],['unit_conversion'])
            self.assertEqual(report['source_modes_excluded'],['either_or'])
            self.assertFalse(report['searches_executed'])

    def test_dimensions_keep_height_axis_and_value(self):
        fs={'t':Fact(id='t',product_id='p',attribute='product_type',value='vase',quote='Vase'),
            'h':Fact(id='h',product_id='p',attribute='height',value='20',unit='cm',quote='Højde 20 cm',normalized_value='200',normalized_unit='mm'),
            'd':Fact(id='d',product_id='p',attribute='diameter',value='15,5',unit='cm',quote='Diameter 15,5 cm',normalized_value='155',normalized_unit='mm')}
        b=compile_brief(Candidate(mode='dimension',positive_ids=['p'],fact_ids=list(fs),rationale=''),fs)
        d=Draft(mode='dimension',anchor_product_id='p',baseline_query='vase',test_queries=['vase 20 cm høj'])
        case=compile_case(d,b)
        self.assertEqual(case['steps'][1]['requirements'][-1]['attribute'],'height')
        self.assertEqual(case['steps'][1]['requirements'][-1]['value'],'200')
        d.test_queries=['vase 15,5 cm høj']
        self.assertTrue(validate_draft(d,b))

    def test_different_stage_system_prompts_have_separate_cached_calls(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from src.candidates.runner import Calls
        from src.candidates.contracts import Selection
        with TemporaryDirectory() as tmp:
            with patch('src.candidates.runner.structured_call',return_value=Selection(ids=['x'],reason='')) as api:
                Calls(Path(tmp),client=object(),system='Candidate system').call('a',{},Selection,'choose')
                Calls(Path(tmp),client=object(),system='Query system').call('a',{},Selection,'choose')
                self.assertEqual(api.call_count,2)
                self.assertEqual(api.call_args.kwargs['system'],'Query system')


if __name__=='__main__':unittest.main()

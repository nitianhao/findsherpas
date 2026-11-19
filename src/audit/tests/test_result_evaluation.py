import unittest
from src.candidates.contracts import Fact
from src.candidates.evaluate_results import compare_requirement, summarize_step, summarize_suite


def f(attribute,value,normalized='',unit=''):
    return Fact(id='f',product_id='p',attribute=attribute,value=value,quote='evidence',normalized_value=normalized,normalized_unit=unit)


class EvaluationTests(unittest.TestCase):
    def test_volume_uses_normalized_units(self):
        req={'attribute':'capacity','operator':'eq','value':'1600','unit':'ml'}
        self.assertEqual(compare_requirement(req,[f('capacity','1,6','1600','ml')])['status'],'satisfies')
        self.assertEqual(compare_requirement(req,[f('capacity','1500','1500','ml')])['status'],'violates')

    def test_unknown_is_not_a_negative(self):
        req={'attribute':'coating','operator':'eq','value':'none','unit':''}
        self.assertEqual(compare_requirement(req,[])['status'],'unknown')

    def test_stainless_surface_may_have_aluminium_core(self):
        req={'attribute':'material','operator':'eq','value':'stainless_steel_aluminium','unit':''}
        self.assertEqual(compare_requirement(req,[f('material','stainless_steel')])['status'],'satisfies')
        self.assertEqual(compare_requirement(req,[f('material','aluminium')])['status'],'violates')

    def test_decisive_violation_is_not_hidden_by_another_unknown(self):
        entries=[{'rank':1,'status':'violates'},{'rank':2,'status':'violates'}]
        result=summarize_step({'status':'ok'},entries,True)
        self.assertEqual(result['findability'],'fail')
        entries.append({'rank':3,'status':'unknown'})
        self.assertEqual(summarize_step({'status':'ok'},entries,True)['findability'],'inconclusive')

    def test_alternative_can_pass_without_anchor(self):
        entries=[{'rank':3,'status':'satisfies'},{'rank':1,'status':'violates'}]
        r=summarize_step({'status':'ok'},entries,False)
        self.assertEqual(r['findability'],'pass')
        self.assertEqual(r['first_satisfying_rank'],3)
        self.assertEqual(r['violating_count'],1)

    def test_empty_requires_trusted_fetch_and_current_execution_proof(self):
        self.assertEqual(summarize_step({'status':'zero_confirmed'},[],True)['findability'],'fail')
        self.assertEqual(summarize_step({'status':'zero_confirmed'},[],False)['findability'],'inconclusive')
        self.assertEqual(summarize_step({'status':'error'},[],True)['findability'],'inconclusive')

    def test_failed_baseline_cannot_prove_added_constraint_failure(self):
        self.assertEqual(summarize_suite([{'findability':'fail'},{'findability':'fail'}]),'inconclusive_baseline')
        self.assertEqual(summarize_suite([{'findability':'pass'},{'findability':'fail'}]),'failure')


if __name__=='__main__':unittest.main()

class UnitAliasTests(unittest.TestCase):
    def test_litre_alias_can_quote_symbol_without_inventing_units(self):
        from src.candidates.contracts import Product
        from src.candidates.validation import ground_fact
        p=Product(id='p',name='Jug',url='https://example.com/jug',text='Kapacitet 1,6 L')
        fact=Fact(id='f',product_id='p',attribute='capacity',value='1,6',unit='liter',quote='Kapacitet 1,6 L')
        self.assertIsNone(ground_fact(fact,p))
        self.assertEqual(fact.normalized_value,'1600')
        wrong=Fact(id='x',product_id='p',attribute='capacity',value='1,6',unit='ml',quote='Kapacitet 1,6 L')
        self.assertIsNotNone(ground_fact(wrong,p))

class PriceEligibilityTests(unittest.TestCase):
    def test_member_bargain_does_not_satisfy_nonmember_budget(self):
        req={'attribute':'nonmember_price','operator':'lt','value':'500','unit':'DKK'}
        facts=[f('price_member','499,95','499.95','DKK'),f('price_regular','1499,95','1499.95','DKK')]
        self.assertEqual(compare_requirement(req,facts)['status'],'violates')
        self.assertEqual(compare_requirement(req,facts[:1])['status'],'unknown')
        self.assertEqual(compare_requirement(req,[f('price_public','299,95','299.95','DKK')])['status'],'satisfies')

class CategoricalAndPurityTests(unittest.TestCase):
    def test_danish_material_labels_are_not_false_violations(self):
        req={'attribute':'material','operator':'eq','value':'porcelain','unit':''}
        self.assertEqual(compare_requirement(req,[f('material','Porcelæn')])['status'],'satisfies')
        self.assertEqual(compare_requirement(req,[f('material','Keramik')])['status'],'unknown')

    def test_generic_other_cannot_establish_wrong_product_type(self):
        req={'attribute':'product_type','operator':'eq','value':'jug','unit':''}
        self.assertEqual(compare_requirement(req,[f('product_type','other')])['status'],'unknown')
        self.assertEqual(compare_requirement(req,[f('product_type','vase')])['status'],'violates')

    def test_some_good_results_do_not_hide_known_pollution(self):
        self.assertEqual(summarize_suite([{'findability':'pass'},{'findability':'pass','violating_count':1}]),'mixed_results')

class FactAuditTests(unittest.TestCase):
    def test_rejected_fact_cannot_be_used_for_a_pass(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from src.candidates.contracts import FactBatch,Product
        from src.candidates.evaluate_results import collect_facts,FactAudit,FactDecision
        class Stub:
            def call(self,stage,payload,schema,instruction):
                if stage.startswith('eval_extract'):
                    return FactBatch(facts=[Fact(product_id='p',attribute='product_type',value='cup',quote='Ramakiner til airfryer')])
                return FactAudit(decisions=[FactDecision(fact_id='e0:0',reason='Not evidence for a drinking cup',approved=False)])
        with TemporaryDirectory() as tmp:
            sources={'p':{'status':'ok','product':Product(id='p',name='Ramekins',url='https://www.imerco.dk/p',text='Ramakiner til airfryer').model_dump()}}
            approved,rejected=collect_facts(sources,{'p':['product_type']},Stub(),Path(tmp))
            self.assertEqual(approved,{})
            self.assertEqual(compare_requirement({'attribute':'product_type','operator':'eq','value':'cup','unit':''},list(approved.values()))['status'],'unknown')

import unittest
from src.candidates.ordinary_search import metrics,validate_plan,ShoppingCase,Plan,SHAPES

class OrdinarySearchTests(unittest.TestCase):
    def test_family_specific_query_is_not_penalized_for_variants(self):
        rows=[{'rank':i+1,'label':'exact','family_id':'one','online_stock':'available_online'} for i in range(10)]
        self.assertTrue(metrics({'shape':'category'},rows)['variant_concentration_flag'])
        self.assertFalse(metrics({'shape':'family'},rows)['variant_concentration_flag'])

    def test_stock_flag_requires_a_relevant_available_alternative(self):
        rows=[{'rank':1,'label':'exact','family_id':'one','online_stock':'not_available_online'},
              {'rank':2,'label':'irrelevant','family_id':'two','online_stock':'available_online'}]
        self.assertFalse(metrics({'shape':'category'},rows)['stock_ordering_flag'])
        rows[1]['label']='exact'
        self.assertTrue(metrics({'shape':'category'},rows)['stock_ordering_flag'])

    def test_unknown_relevance_does_not_become_a_wrong_result(self):
        rows=[{'rank':1,'label':'unknown','family_id':'one','online_stock':'unknown'},
              {'rank':2,'label':'exact','family_id':'two','online_stock':'available_online'}]
        m=metrics({'shape':'category'},rows)
        self.assertEqual(m['first_exact_rank'],2)
        self.assertEqual(m['unknown_count'],1)
        self.assertEqual(m['nonexact_above_first_exact'],0)

    def test_query_set_requires_all_thirty_and_independent_inventory_anchors(self):
        sources={c:{'cards':[{'id':c,'brand':'Brand'}]} for c in ['pans','cups','glasses','jugs','vases']}
        cases=[ShoppingCase(id=c+'_'+s,category=c,shape=s,query=c+' '+s,goal='goal',anchor_ids=[c]) for c in sources for s in SHAPES]
        self.assertEqual(validate_plan(Plan(cases=cases),sources),[])
        cases[0].anchor_ids=['invented']
        self.assertTrue(validate_plan(Plan(cases=cases),sources))
        cases[0].anchor_ids=['pans'];cases[1].query=cases[0].query
        self.assertTrue(validate_plan(Plan(cases=cases),sources))

    def test_separate_quoted_field_lines_must_each_exist_in_source(self):
        from src.candidates.ordinary_search import evidence_matches
        context='name: Termokrus\nbrand: S well\nprimary_category_id: To go kopper\ncust_material: ["Rustfrit stål"]'
        self.assertTrue(evidence_matches(context,'name: Termokrus\nprimary_category_id: To go kopper'))
        self.assertFalse(evidence_matches(context,'name: Termokrus\nbrand: Invented'))
        self.assertFalse(evidence_matches(context,'Termokrus ... Invented'))

if __name__=='__main__':unittest.main()

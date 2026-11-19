import unittest
from decimal import Decimal
from src.candidates.unit_investigation import parse_volume,plan_variants,extract_public_search

class UnitInvestigationTests(unittest.TestCase):
    def test_equivalent_volume_spellings_normalize_without_float_error(self):
        for value in ['1,6 L','1.6 liter','160 cl','1600ml','16 dl','1600 milliliter']:
            self.assertEqual(parse_volume(value),Decimal('1600'),value)
        self.assertEqual(parse_volume('0,1 L'),Decimal('100'))

    def test_rejects_ambiguous_ranges_and_nonvolume_tokens(self):
        for value in ['1600 mAh','Model1600ml','1 L / 2 L','1,5–1,6 L','1,600.2 L','0,7/1,6 L','kande over 1,6 L','kande mindst 1600 ml']:
            self.assertIsNone(parse_volume(value),value)

    def test_plan_changes_one_representation_and_preserves_volume(self):
        rows=plan_variants('kande',Decimal('1600'),'Eva Trio Legio Nova Kande')
        self.assertIn('kande 160 cl',[r['query'] for r in rows])
        self.assertIn('kande 1.6 L',[r['query'] for r in rows])
        self.assertEqual(len({r['query'] for r in rows}),len(rows))
        for row in rows:
            if row['family']=='equivalent_volume':self.assertEqual(parse_volume(row['query']),Decimal('1600'))

    def test_only_sanitized_search_data_is_returned(self):
        import json
        record={'query':'kande 1600 ml','parsedQuery':'kande 1600 ml','nbHits':1,'hits':[
            {'objectID':'p','name':'Jug','cust_capacity':'600 ml','cust_spec_capacity':'600',
             '_rankingInfo':{'nbTypos':2},'_highlightResult':{'cust_synopsis':{'value':'<em>600</em> ml','matchedWords':['1600','ml']}}}]}
        d={'runtimeConfig':{'NEXT_PUBLIC_ALGOLIA_TOKEN':'DO_NOT_COPY'},'props':{'pageProps':{'page':{'data':{'plpResult':{'serverState':{'initialResults':{'product-list':{'state':{'numericRefinements':{}},'results':[record]}}}}}}}}}
        html='<script id="__NEXT_DATA__" type="application/json">'+json.dumps(d)+'</script>'
        result=extract_public_search(html)
        self.assertNotIn('DO_NOT_COPY',json.dumps(result))
        self.assertEqual(result['records'][0]['capacity_ml'],'600')
        self.assertEqual(result['records'][0]['nb_typos'],2)

    def test_recommendation_index_is_not_the_query_result_feed(self):
        import json
        d={'props':{'pageProps':{'page':{'data':{'plpResult':{'serverState':{'initialResults':{
            'recommendations':{'results':[{'query':'','nbHits':99,'hits':[{'objectID':'wrong'}]}]},
            'product-list':{'state':{},'results':[{'query':'kande 1600 ml','nbHits':0,'hits':[]}]}}}}}}}}}
        html='<script id="__NEXT_DATA__">'+json.dumps(d)+'</script>'
        result=extract_public_search(html,expected_query='kande 1600 ml')
        self.assertEqual(result['total_hits'],0)
        self.assertEqual(result['records'],[])
        self.assertFalse(extract_public_search(html,expected_query='different')['available'])

    def test_expansion_preserves_centiliter_only_candidates(self):
        from src.candidates.unit_investigation import replay_fix
        rows=[]
        for key,records in [('milliliters',[{'product_id':'wrong','capacity_ml':'1500'}]),('comma_word',[{'product_id':'l','capacity_ml':'1600'}]),('centiliters',[{'product_id':'cl','capacity_ml':'1600'}])]:
            rows.append({'id':key,'observations':[{'public_search':{'query':key,'records':records}}]})
        r=replay_fix(rows,Decimal('1600'),'milliliters','comma_word',('centiliters',))
        self.assertEqual({x['product_id'] for x in r['eligible_records']},{'l','cl'})
        self.assertEqual(r['rejected_wrong_capacity'],1)

if __name__=='__main__':unittest.main()

import unittest
from src.candidates.stock_experiment import rerank,purchase_stock


def row(pid,label='exact',stock='available_online',accepted=True):
    return {'product_id':pid,'label':label,'online_stock':stock,'review_accepted':accepted}

class StockRerankTests(unittest.TestCase):
    def test_available_exact_moves_ahead_without_reordering_peers(self):
        rows=[row('u1',stock='not_available_online'),row('a1'),row('u2',stock='not_available_online'),row('a2')]
        result=rerank({'shape':'category'},rows)
        self.assertEqual([r['product_id'] for r in result],['a1','a2','u1','u2'])
        self.assertEqual({r['product_id'] for r in result},{r['product_id'] for r in rows})
        self.assertEqual(rows[0]['product_id'],'u1')

    def test_wrong_brand_accessory_and_unknown_cannot_cross_exact_unavailable(self):
        for label in ['substitute','complement','irrelevant','unknown']:
            with self.subTest(label=label):
                rows=[row('exact-unavailable',stock='not_available_online'),row('weak',label),row('exact-available')]
                self.assertEqual(rerank({'shape':'brand'},rows),rows)

    def test_unknown_stock_and_rejected_review_are_barriers(self):
        for blocker in [row('unknown-stock',stock='unknown'),row('not-reviewed',accepted=False)]:
            with self.subTest(blocker=blocker):
                rows=[row('unavailable',stock='not_available_online'),blocker,row('available')]
                self.assertEqual(rerank({'shape':'category'},rows),rows)

    def test_named_unavailable_lookup_is_pinned(self):
        rows=[row('named-original',stock='not_available_online'),row('available-variant')]
        self.assertEqual(rerank({'shape':'named_product'},rows),rows)

    def test_multiple_blocks_can_change_without_crossing_relevance_boundaries(self):
        rows=[row('u1',stock='not_available_online'),row('a1'),row('sub','substitute'),row('u2',stock='not_available_online'),row('a2')]
        result=rerank({'shape':'family'},rows)
        self.assertEqual([r['product_id'] for r in result],['a1','u1','sub','a2','u2'])
        self.assertEqual([r['label'] for r in result],[r['label'] for r in rows])
        self.assertEqual(rerank({'shape':'family'},result),result)

    def test_empty_search_is_recorded_without_manufacturing_a_stock_issue(self):
        import tempfile,json
        from pathlib import Path
        from src.candidates.stock_experiment import simulate
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            (out/'evaluation.json').write_text(json.dumps({'cases':[{'case':{'shape':'category'},'fetch_status':'zero_confirmed','rows':[]}],'cost':{}}))
            simulate(out)
            result=json.loads((out/'simulation.json').read_text())
            self.assertEqual(result['summary']['stock_ordering_before'],0)
            self.assertEqual(result['summary']['raw_top1_unavailable'],0)
            self.assertFalse(result['cases'][0]['changed'])

    def test_explicit_online_sold_out_beats_store_availability(self):
        text='Giv mig besked Midlertidligt udsolgt online Klik & hent i butik På lager i 86 butikker'
        self.assertEqual(purchase_stock(text),'not_available_online')

    def test_store_stock_alone_does_not_establish_online_fulfillment(self):
        self.assertEqual(purchase_stock('Klik & hent På lager i 86 butikker'),'unknown')

    def test_online_purchase_with_dispatch_is_available(self):
        self.assertEqual(purchase_stock('Læg i kurv Afsendes 1-4 hverdage'),'available_online')

if __name__=='__main__':unittest.main()

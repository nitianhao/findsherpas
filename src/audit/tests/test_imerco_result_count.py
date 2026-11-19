"""Imerco facet counts must not become reported search-result counts."""
import unittest
from src.fetcher import page_state

class ImercoCountTests(unittest.TestCase):
    def test_results_header_overrides_earlier_offer_facet_count(self):
        html='<h1>Søgeresultater</h1><span class="FilterSelectionHeader_selectionHeaderCount__abc">3 varer</span><span class="HitsHeader_count__xyz">28 varer</span>'
        state=page_state(html,'https://www.imerco.dk/search?query=kande')
        self.assertEqual(state.total_hits,28)
        self.assertTrue(state.hits_strong)

    def test_zero_header_confirms_zero_without_recommendation_counts(self):
        html='<span class="FilterSelectionHeader_selectionHeaderCount__abc">5 varer</span><span class="HitsHeader_count__xyz">0 varer</span>'
        state=page_state(html,'https://www.imerco.dk/search?query=xx')
        self.assertEqual(state.total_hits,0)
        self.assertIsNotNone(state.no_results_marker)

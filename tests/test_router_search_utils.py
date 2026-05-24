import unittest

from core.router_search_utils import cleanup_marketplace_query, cleanup_site_query


class RouterSearchUtilsTests(unittest.TestCase):
    def test_cleanup_marketplace_query(self):
        self.assertEqual(cleanup_marketplace_query("nutbook"), "notebook")

    def test_cleanup_site_query(self):
        self.assertEqual(cleanup_site_query("pesquise aulas de python no youtube"), "aulas python youtube")


if __name__ == "__main__":
    unittest.main()

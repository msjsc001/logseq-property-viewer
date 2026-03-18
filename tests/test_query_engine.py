import unittest

from backend.query_engine import QuerySyntaxError, search_blocks


class QueryEngineTests(unittest.TestCase):
    def setUp(self):
        self.blocks = [
            {"page": "Alpha", "block_content": "- done", "properties": {"status": "done"}},
            {"page": "Alpha", "block_content": "- undone", "properties": {"status": "undone"}},
            {"page": "Beta", "block_content": "- urgent", "properties": {"priority": "A"}},
            {"page": "Gamma", "block_content": "- Mixed", "properties": {"State": "Done"}},
        ]

    def test_exact_match_does_not_match_partial_values(self):
        result = search_blocks(self.blocks, "status:done")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["properties"]["status"], "done")

    def test_fuzzy_match_supports_substrings(self):
        result = search_blocks(self.blocks, "status~done")
        self.assertEqual(len(result), 2)

    def test_and_or_logic_and_text_search_work(self):
        and_result = search_blocks(self.blocks, "has:status AND done")
        or_result = search_blocks(self.blocks, "priority:A OR status:done")
        self.assertEqual(len(and_result), 2)
        self.assertEqual(len(or_result), 2)

    def test_invalid_query_raises_structured_error(self):
        with self.assertRaises(QuerySyntaxError):
            search_blocks(self.blocks, "has:")

    def test_case_sensitive_search_affects_all_query_modes(self):
        exact_insensitive = search_blocks(self.blocks, "state:done")
        exact_sensitive = search_blocks(self.blocks, "State:Done", case_sensitive=True)
        exact_sensitive_miss = search_blocks(self.blocks, "state:done", case_sensitive=True)
        has_sensitive = search_blocks(self.blocks, "has:State", case_sensitive=True)
        fuzzy_sensitive = search_blocks(self.blocks, "State~Do", case_sensitive=True)
        text_sensitive = search_blocks(self.blocks, "Mixed", case_sensitive=True)

        self.assertEqual(len(exact_insensitive), 1)
        self.assertEqual(len(exact_sensitive), 1)
        self.assertEqual(exact_sensitive[0]["page"], "Gamma")
        self.assertEqual(len(exact_sensitive_miss), 0)
        self.assertEqual(len(has_sensitive), 1)
        self.assertEqual(has_sensitive[0]["page"], "Gamma")
        self.assertEqual(len(fuzzy_sensitive), 1)
        self.assertEqual(fuzzy_sensitive[0]["page"], "Gamma")
        self.assertEqual(len(text_sensitive), 1)
        self.assertEqual(text_sensitive[0]["page"], "Gamma")


if __name__ == "__main__":
    unittest.main()

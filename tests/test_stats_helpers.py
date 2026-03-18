import unittest

from backend.main import (
    _build_global_value_stats,
    _build_key_stats,
    _build_key_value_distribution,
    _build_value_key_distribution,
    _collect_property_aggregates,
)


class StatsHelperTests(unittest.TestCase):
    def setUp(self):
        self.blocks = [
            {
                "properties": {
                    "status": "done",
                    "review": "done",
                    "empty": "",
                }
            },
            {
                "properties": {
                    "status": "done",
                    "result": "done",
                }
            },
            {
                "properties": {
                    "status": "Done",
                }
            },
            {
                "properties": {
                    "status": "DONE",
                }
            },
        ]
        self.aggregates = _collect_property_aggregates(self.blocks)

    def test_global_values_aggregate_same_value_across_multiple_keys(self):
        result = _build_global_value_stats(self.aggregates)
        done_row = next(item for item in result["values"] if item["value"] == "done")

        self.assertEqual(done_row["count"], 4)
        self.assertEqual(done_row["keyCount"], 3)
        self.assertEqual(
            done_row["topKeys"],
            [
                {"key": "status", "count": 2},
                {"key": "review", "count": 1},
                {"key": "result", "count": 1},
            ],
        )

    def test_value_stats_keep_case_variants_separate(self):
        result = _build_global_value_stats(self.aggregates)
        counts = {item["value"]: item["count"] for item in result["values"]}

        self.assertEqual(counts["done"], 4)
        self.assertEqual(counts["Done"], 1)
        self.assertEqual(counts["DONE"], 1)

    def test_empty_string_value_is_included_in_stats(self):
        result = _build_global_value_stats(self.aggregates)
        empty_row = next(item for item in result["values"] if item["value"] == "")

        self.assertEqual(empty_row["count"], 1)
        self.assertEqual(empty_row["keyCount"], 1)

    def test_value_key_distribution_returns_sorted_key_counts(self):
        result = _build_value_key_distribution(self.aggregates, "done")

        self.assertEqual(
            result["keys"],
            [
                {"key": "status", "count": 2},
                {"key": "review", "count": 1},
                {"key": "result", "count": 1},
            ],
        )
        self.assertEqual(result["total"], 3)

    def test_existing_key_stats_and_value_distribution_do_not_regress(self):
        key_stats = _build_key_stats(self.aggregates)
        status_row = next(item for item in key_stats if item["key"] == "status")
        key_distribution = _build_key_value_distribution(self.aggregates, "status")

        self.assertEqual(status_row["count"], 4)
        self.assertEqual(status_row["uniqueValues"], 3)
        self.assertEqual(
            key_distribution["values"],
            [
                {"value": "done", "count": 2},
                {"value": "Done", "count": 1},
                {"value": "DONE", "count": 1},
            ],
        )


if __name__ == "__main__":
    unittest.main()

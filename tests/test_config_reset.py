import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config


class ConfigResetTests(unittest.TestCase):
    def test_reset_config_can_preserve_history_and_path_independently(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            with patch.object(config, "CONFIG_FILE", config_file):
                config.save_config(
                    {
                        "graph_path": "D:/Graph",
                        "language": "en",
                        "query_case_sensitive": True,
                        "query_history": ["a", "b"],
                        "global_hidden_columns": ["status"],
                        "column_configs": {"q": {"visibleColumns": ["page"]}},
                        "sidebar_collapsed": True,
                        "auto_update_enabled": True,
                    }
                )
                result = config.reset_config(
                    clear_graph_path=False,
                    clear_preferences=True,
                    clear_history=False,
                )

                self.assertEqual(result["graph_path"], "D:/Graph")
                self.assertEqual(result["query_history"], ["a", "b"])
                self.assertEqual(result["language"], "zh")
                self.assertFalse(result["query_case_sensitive"])
                self.assertEqual(result["global_hidden_columns"], [])
                self.assertFalse(result["sidebar_collapsed"])


if __name__ == "__main__":
    unittest.main()

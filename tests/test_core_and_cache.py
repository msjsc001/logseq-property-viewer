import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cache
import core


class CoreAndCacheTests(unittest.TestCase):
    def test_page_level_properties_are_indexed_and_separator_keys_are_filtered(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "note.md"
            file_path.write_text(
                "  alias:: 书籍AI提示词，AI总结书籍\n"
                "  ai-提示词:: [[提示词-书籍总结]]\n"
                "  提示词-经典程度:: [[经典程度-⭐⭐⭐⭐]]\n"
                "  关联强度-btc::\n"
                "  --:: --\n"
                "  --2:: --\n"
                "- 正文块\n"
                "  status:: done\n",
                encoding="utf-8",
            )

            blocks = core.parse_file_for_properties(str(file_path))

            self.assertEqual(len(blocks), 2)
            self.assertEqual(
                blocks[0]["properties"],
                {
                    "alias": "书籍AI提示词，AI总结书籍",
                    "ai-提示词": "[[提示词-书籍总结]]",
                    "提示词-经典程度": "[[经典程度-⭐⭐⭐⭐]]",
                    "关联强度-btc": "",
                },
            )
            self.assertEqual(blocks[0]["block_path"], "note")
            self.assertNotIn("--", blocks[0]["properties"])
            self.assertNotIn("--2", blocks[0]["properties"])
            self.assertEqual(blocks[1]["properties"], {"status": "done"})

    def test_nested_blocks_keep_properties_on_the_correct_block(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "note.md"
            file_path.write_text(
                "- parent\n"
                "  status:: open\n"
                "  - child\n"
                "    status:: done\n",
                encoding="utf-8",
            )

            blocks = core.parse_file_for_properties(str(file_path))

            self.assertEqual(len(blocks), 2)
            self.assertEqual(blocks[0]["properties"], {"status": "open"})
            self.assertEqual(blocks[0]["block_path"], "parent")
            self.assertEqual(blocks[1]["properties"], {"status": "done"})
            self.assertEqual(blocks[1]["block_path"], "parent > child")

    def test_non_standard_roots_are_scanned_recursively(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_root = Path(temp_dir)
            nested = graph_root / "nested" / "folder"
            nested.mkdir(parents=True)
            (nested / "task.md").write_text("- todo\n  priority:: A\n", encoding="utf-8")

            files = list(core.iter_markdown_files(str(graph_root)))

            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].name, "task.md")

    def test_old_cache_schema_is_marked_stale(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            graph_path = "D:/Graph"
            with patch.object(cache, "get_cache_dir", return_value=cache_dir):
                legacy_file = cache_dir / f"{cache._get_cache_filepath_for_graph(graph_path).name}"
                legacy_file.write_text(json.dumps({"legacy": True}), encoding="utf-8")

                payload = cache.load_cache(graph_path)

                self.assertTrue(payload["_stale"])


if __name__ == "__main__":
    unittest.main()

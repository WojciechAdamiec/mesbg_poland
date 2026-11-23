import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import store


class StoreCacheTests(unittest.TestCase):
    def tearDown(self):
        store._read_json.cache_clear()

    def test_json_is_shared_until_file_changes_then_reloaded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ranking.json"
            path.write_text(json.dumps([{"place": 1}]), encoding="utf-8")
            with (
                patch.object(store, "DATA_DIRECTORY", directory),
                patch.object(store, "MAIN_RANKING_FILE", path.name),
            ):
                first = store.load_main_ranking()
                second = store.load_main_ranking()
                self.assertIs(first, second)

                path.write_text(json.dumps([{"place": 2, "player_id": "p"}]), encoding="utf-8")
                updated = store.load_main_ranking()

            self.assertEqual(updated, [{"place": 2, "player_id": "p"}])
            self.assertIsNot(updated, first)


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

import articles


class ArticleArmyRecordTests(unittest.TestCase):
    def test_records_are_aggregated_once_and_refresh_with_new_battle_data(self):
        battles = [
            {"army_1_name": "Army A", "army_2_name": "Army B", "result": [2, 0]},
            {"army_1_name": "Army A", "army_2_name": "Army C", "result": [1, 1]},
            {"army_1_name": "Army D", "result": [1]},
        ]
        with (
            patch.object(articles, "_cached_battles", None),
            patch.object(articles, "_cached_army_records", None),
            patch.object(articles, "load_battles", return_value=battles),
        ):
            self.assertEqual(articles.army_record("Army A"), (2, 1.5, 4))
            self.assertEqual(articles.army_record("Army B"), (1, 0, 4))
            self.assertEqual(articles.army_record("Unknown"), (0, 0, 0))

            refreshed = [{"army_1_name": "Army A", "result": [0, 1]}]
            with patch.object(articles, "load_battles", return_value=refreshed):
                self.assertEqual(articles.army_record("Army A"), (1, 0, 1))


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch


ARMIES = [
    {"army_id": 1, "name": "Army A", "faction": "GOOD"},
    {"army_id": 2, "name": "Army B", "faction": "EVIL"},
]

with (
    patch("dash.register_page"),
    patch("store.load_battles", return_value=[]),
    patch("store.load_armies", return_value=ARMIES),
    patch("store.load_main_ranking", return_value=[]),
):
    from pages import stats_army_list_winrates, stats_pickrate_vs_winrate


class StatsChartAggregationTests(unittest.TestCase):
    def setUp(self):
        self.battles = [
            {
                "army_1_id": 1,
                "army_2_id": 2,
                "result": [2, 1],
                "format": "INDIVIDUAL",
                "tournament_type": "LOCAL",
                "patch": "BALROG",
                "season": 2026,
            },
            {
                "army_1_id": 2,
                "army_2_id": 1,
                "result": [1, 1],
                "format": "INDIVIDUAL",
                "tournament_type": "LOCAL",
                "patch": "BALROG",
                "season": 2026,
            },
            {
                "army_1_id": 1,
                "army_2_id": 2,
                "result": [1],
                "format": "INDIVIDUAL",
                "tournament_type": "LOCAL",
                "patch": "BALROG",
                "season": 2026,
            },
        ]

    def test_pickrate_chart_and_data_size_share_valid_filtered_battle_count(self):
        series, count = stats_pickrate_vs_winrate._compute_chart_data_and_count(
            self.battles,
            ARMIES,
            [0, 1000],
            stats_pickrate_vs_winrate.GAME_TYPES,
            stats_pickrate_vs_winrate.PATCHES,
            stats_pickrate_vs_winrate.FACTIONS,
            ["Individual"],
            0,
            seasons=["2026"],
        )

        self.assertEqual(count, 2)
        values = {item["army"]: item for group in series for item in group["data"]}
        self.assertEqual(values["Army A"]["games"], 2)
        self.assertEqual(values["Army A"]["winrate"], 75.0)
        self.assertEqual(values["Army B"]["games"], 2)
        self.assertEqual(values["Army B"]["winrate"], 25.0)

    def test_opponent_chart_and_data_size_share_selected_army_matches(self):
        with (
            patch.object(stats_army_list_winrates, "army_by_id", {army["army_id"]: army for army in ARMIES}),
            patch.object(stats_army_list_winrates, "armies_data", ARMIES),
        ):
            chart, count = stats_army_list_winrates._compute_chart_data_and_count(
                self.battles,
                "1",
                [0, 1000],
                stats_army_list_winrates.GAME_TYPES,
                stats_army_list_winrates.PATCHES,
                stats_army_list_winrates.FACTIONS,
                ["Individual"],
                0,
                seasons=["2026"],
            )

        self.assertEqual(count, 2)
        self.assertEqual(chart, [{"army": "Army B", "winrate": 75.0, "games": 2}])


if __name__ == "__main__":
    unittest.main()

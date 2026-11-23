import unittest
from unittest.mock import patch


with (
    patch("dash.register_page"),
    patch("store.load_armies", return_value=[]),
    patch("store.load_battles", return_value=[]),
    patch("store.load_main_ranking", return_value=[]),
):
    from pages.stats_armies_best_players import compute_best_players, make_table_rows


class BestPlayersTests(unittest.TestCase):
    def test_adjusted_winrate_with_actual_draws(self):
        battles = [
            {
                "army_1_id": 1,
                "player_1_id": "a",
                "player_1_name": "A",
                "result": [1, 0],
            },
            {
                "army_2_id": 1,
                "player_2_id": "a",
                "player_2_name": "A",
                "result": [1, 1],
            },
        ]
        rows = compute_best_players(battles, "1", [])
        self.assertEqual(rows[0]["games"], 2)
        self.assertEqual(rows[0]["winrate"], 75.0)
        self.assertEqual(rows[0]["adjusted_winrate"], 53.12)

    def test_adjusted_winrate_at_and_around_minimum_games(self):
        for games, expected in ((1, 53.12), (15, 96.88), (16, 100.0), (17, 100.0)):
            with self.subTest(games=games):
                battles = [
                    {"army_1_id": 1, "player_1_id": "a", "result": [1, 0]}
                    for _ in range(games)
                ]
                row = compute_best_players(battles, 1, [])[0]
                self.assertEqual(row["games"], games)
                self.assertEqual(row["winrate"], 100.0)
                self.assertEqual(row["adjusted_winrate"], expected)

    def test_adjusted_winrate_matches_winrate_at_and_above_minimum(self):
        for games in (16, 17):
            with self.subTest(games=games):
                battles = [
                    {"army_1_id": 1, "player_1_id": "a", "result": result}
                    for result in [[1, 0]] * 6 + [[0, 1]] * (games - 6)
                ]
                row = compute_best_players(battles, 1, [])[0]
                self.assertEqual(row["adjusted_winrate"], row["winrate"])

    def test_adjusted_winrate_drives_order(self):
        battles = [
            {"army_1_id": 1, "player_1_id": "one-win", "result": [1, 0]},
            *[
                {"army_1_id": 1, "player_1_id": "established", "result": result}
                for result in [[1, 0]] * 10 + [[0, 1]] * 6
            ],
        ]
        rows = compute_best_players(battles, 1, [])
        self.assertEqual([row["player_id"] for row in rows], ["established", "one-win"])
        self.assertEqual([row["adjusted_winrate"] for row in rows], [62.5, 53.12])

    def test_tied_displayed_rates_share_competition_rank(self):
        rates = [60.0, 60.0, 55.0, 50.0, 50.0, 40.0]
        rows = [
            {
                "player_name": str(index),
                "main_ranking_place": None,
                "games": 1,
                "winrate": 50.0,
                "adjusted_winrate": rate,
            }
            for index, rate in enumerate(rates)
        ]
        table_rows = make_table_rows(rows)
        self.assertEqual(
            [row.children[0].children for row in table_rows],
            [1, 1, 3, 4, 4, 6],
        )

    def test_empty_table_spans_all_columns(self):
        self.assertEqual(make_table_rows([])[0].children.attributes["colSpan"], 6)


if __name__ == "__main__":
    unittest.main()

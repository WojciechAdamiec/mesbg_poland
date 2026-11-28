import json
import tempfile
import unittest
from pathlib import Path

import app
import dash
from center_stats import build_center_stats, center_for_city, hosted_event_counts, load_center_mapping, load_placements
from center_profile_components import (
    center_ranking_table, center_sections, center_stat_card, centers, distribution_chart, ranking_distribution,
    trophy_row,
)
from army_stats_table import army_stats_table


class CenterStatsTests(unittest.TestCase):
    def test_ranking_distribution_has_nonoverlapping_bands_and_includes_all_ranked_players(self):
        ranking = [{"place": place} for place in (
            1, 10, 11, 30, 31, 50, 51, 70, 71, 100, 101, 150,
            151, 200, 201, 300, 301, 1001, None, 0,
        )]
        self.assertEqual(ranking_distribution(ranking), [
            ("1–10", 2), ("11–30", 2), ("31–50", 2),
            ("51–70", 2), ("71–100", 2), ("101–150", 2),
            ("151–200", 2), ("201–300", 2), ("301+", 2),
        ])
        chart = distribution_chart({"ranking": ranking}, "A", 2026)
        self.assertEqual(list(chart.figure.data[0].customdata), [2] * 9)
        self.assertEqual(list(chart.figure.data[0].text), ["2 (11.1%)"] * 9)
        empty = distribution_chart({"ranking_2027": []}, "A", 2027)
        self.assertEqual(empty.children, "No ranking data available for this center.")

    def test_stat_card_ranks_centers_with_ties(self):
        card = center_stat_card("Events", 4, [7, 4, 4, 1])
        self.assertEqual(card.children.children[1].children, "4 (2/4)")
        card = center_stat_card("Events", 0, [0, 0, 0])
        self.assertEqual(card.children.children[1].children, "0 (1/3)")
        card = center_stat_card("Trophies", 4, [7, 4, 4, 1])
        self.assertEqual(card.children.children[1].children, "4 (2/4)")

    def test_event_counts_use_league_season_boundaries(self):
        events = [{"date": date} for date in (
            "2025-12-04", "2025-12-05", "2026-11-23", "2026-11-24", "2027-01-01",
        )]
        self.assertEqual(hosted_event_counts(events), {2026: 2, 2027: 2})

    def test_hosted_events_show_a_season_divider(self):
        data = {
            "events": [
                {"date": "2026-11-24", "name": "New", "city": {"name": "Town"}},
                {"date": "2026-11-23", "name": "Old", "city": {"name": "Town"}},
            ],
            "ranking": [], "ranking_2027": [],
            "trophies": [
                {"date": "2026-11-23", "event": "Old", "type": "MASTER", "place": 1,
                 "players": [{"player_id": "p1", "name": "One"}, {"player_id": "p2", "name": "Two"}]},
                {"date": "2026-11-24", "event": "New", "type": "CHALLENGER", "place": 3,
                 "players": [{"player_id": "p1", "name": "One"}]},
            ],
            "armies": [],
            "distribution": {limit: 0 for limit in (10, 30, 50, 100, 200, 1000)},
            "distribution_2027": {limit: 0 for limit in (10, 30, 50, 100, 200, 1000)},
        }
        section = center_sections("A", data)
        cards = section.children[0].children[1].children
        trophy_cards = [card for card in cards if card.children.children[0].children.startswith("Trophies")]
        self.assertEqual([card.children.children[0].children for card in trophy_cards],
                         ["Trophies (2026)", "Trophies (2027)"])
        self.assertTrue(all(card.children.children[1].children.startswith("1 (")
                            and card.children.children[1].children.endswith("/13)")
                            for card in trophy_cards))
        events_section = next(block for block in section.children
                              if getattr(block.children[0], "children", None) == "Hosted Events")
        rows = events_section.children[1].children.children[1].children
        self.assertIsNone(rows[0].style)
        self.assertEqual(rows[1].style, {"borderTop": "3px solid #00ffff"})

    def test_mapping_and_aggregation(self):
        centers = ["A", "B"]
        mapping = {"town": "A", "nearby": "A", "other": "B", "unknown": None}
        cities = {
            "p1": {"name": " Town ", "country": "PL"},
            "p2": {"name": "nearby", "country": "PL"},
            "p3": {"name": "Other", "country": "PL"},
            "foreign": {"name": "Town", "country": "US"},
        }
        ranking = [
            {"player_id": "p1", "place": 10},
            {"player_id": "p2", "place": 31},
            {"player_id": "p3", "place": 1001},
            {"player_id": "foreign", "place": 1},
        ]
        events = [
            {"tournament_id": "e1", "city": {"name": "nearby", "country": "PL"}, "date": "2026-01-01"},
            {"tournament_id": "e2", "city": {"name": "other", "country": "PL"}, "tournament_type": "ONLINE"},
        ]
        battle = {
            "tournament_id": "e1", "format": "INDIVIDUAL", "result": [2, 2],
            "army_1_id": 1, "army_1_name": "Army", "army_2_id": 1, "army_2_name": "Army",
        }
        battles = [
            battle,
            {**battle, "army_2_id": 2, "army_2_name": "Other army", "result": [1, 0]},
            {**battle, "format": "DOUBLES"},
            {**battle, "tournament_id": "e2"},
        ]
        trophies = [{
            "players": [{"player_id": "p2", "name": "Two"}, {"player_id": "p1", "name": "One"},
                        {"player_id": "p3", "name": "Three"}],
            "date": "2026-02-01", "type": "MASTER", "place": 3, "event": "Team event",
        }]
        result = build_center_stats(
            centers, mapping, cities, ranking, events, battles, trophies,
            [{"army_id": 1, "faction": "GOOD"}],
            [
                {"player_id": "p1", "place": 5, "score": 40},
                {"player_id": "p2", "place": 5, "score": 40},
                {"player_id": "new", "place": 9, "score": 20, "city_name": "Town", "city_country": "PL"},
            ],
        )
        a = result["A"]
        self.assertEqual([r["player_id"] for r in a["ranking"]], ["p1", "p2"])
        self.assertEqual(list(a["distribution"].values()), [1, 1, 2, 2, 2, 2])
        self.assertEqual(list(a["distribution_2027"].values()), [3, 3, 3, 3, 3, 3])
        self.assertEqual([r["player_id"] for r in a["ranking_2027"]], ["p1", "p2", "new"])
        rendered = center_ranking_table(a["ranking_2027"]).children
        self.assertEqual([cell.children for cell in rendered.children[0].children.children],
                         ["#", "Score", "Player", "City"])
        self.assertEqual([[cell.children for cell in row.children[:2]]
                          for row in rendered.children[1].children],
                         [[1, "40 (#5)"], [1, "40 (#5)"], [3, "20 (#9)"]])
        self.assertEqual(len(a["events"]), 1)
        self.assertEqual(a["trophies"], trophies)
        self.assertEqual(result["B"]["trophies"], trophies)
        self.assertEqual(a["armies"][0]["games"], 3)
        self.assertEqual(a["armies"][0]["winrate"], 66.67)
        self.assertEqual(a["armies"][0]["pickrate"], 75.0)
        self.assertEqual(a["armies"][0]["faction"], "Good")
        self.assertEqual(a["armies"][1]["pickrate"], 25.0)
        self.assertIsNone(a["armies"][1]["faction"])
        self.assertFalse(result["B"]["events"])
        self.assertIsNone(center_for_city(cities["foreign"], mapping))

    def test_individual_and_team_podiums_and_missing_results(self):
        events = [
            {"tournament_id": event_id, "name": event_id, "date": "2026-01-01", "tournament_type": kind}
            for event_id, kind in (("master", "MASTER"), ("challenger", "CHALLENGER"),
                                   ("team", "DMP"), ("missing", "MASTER"))
        ]
        people = [
            {"user": {"id": str(place), "displayName": str(place)}, "finalResult": {"place": place}}
            for place in range(1, 5)
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for event_id in ("master", "challenger", "team"):
                folder = root / event_id
                folder.mkdir()
                submission = {"tournament_id": event_id, "people": people}
                if event_id == "team":
                    submission["teams"] = [
                        {"id": "team", "name": "Team", "finalResult": {"place": 2}},
                        {"id": "fourth", "finalResult": {"place": 4}},
                    ]
                    submission["people"] = [
                        {**people[0], "teamId": "team"},
                        {**people[1], "teamId": "team"},
                        {**people[2], "teamId": "fourth"},
                    ]
                (folder / "submission_data.json").write_text(json.dumps(submission), encoding="utf-8")
            placements, missing = load_placements(events, root)
        self.assertEqual(missing, 1)
        self.assertCountEqual([(t["type"], t["place"]) for t in placements],
                              [("MASTER", 1), ("MASTER", 2), ("MASTER", 3),
                               ("CHALLENGER", 1), ("CHALLENGER", 2), ("CHALLENGER", 3),
                               ("MASTER", 2)])
        team = next(t for t in placements if t.get("team_name") == "Team")
        self.assertEqual([p["player_id"] for p in team["players"]], ["1", "2"])
        rendered = trophy_row([team], "MASTER", "Masters:")
        self.assertEqual(rendered.children[0].children, "Masters:")
        self.assertEqual(trophy_row([team], "CHALLENGER", "Challengers:").children[0].children, "Challengers:")
        card = rendered.children[1].children[0].children
        self.assertEqual([text.children for text in card.children.children[1].children], ["1", "2"])
        self.assertEqual((card.style["width"], card.style["height"]), ("210px", "100px"))

    def test_mapping_rejects_duplicate_cities(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mapping.json"
            path.write_text('{"A": ["Town"], "B": [" town "]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_center_mapping(path)

    def test_shared_army_table_renders_sortable_faction_rows(self):
        armies = [
            {"army": "Good army", "winrate": 50, "pickrate": 75, "games": 3, "faction": "Good"},
            {"army": "Evil army", "winrate": 75, "pickrate": 25, "games": 1, "faction": "Evil"},
            {"army": "Unknown", "winrate": 0, "pickrate": 0, "games": 1, "faction": None},
        ]
        table = army_stats_table(armies).children
        self.assertEqual(table.className, "pp-sortable")
        self.assertEqual([cell.children for cell in table.children[0].children.children],
                         ["#", "Army list", "Winrate", "Pickrate", "Games"])
        rows = table.children[1].children
        self.assertEqual([row.children[1].children for row in rows],
                         ["Evil army", "Good army", "Unknown"])
        self.assertEqual(rows[1].children[3].children, "75.00%")
        self.assertEqual(rows[0].style["borderLeft"], "4px solid #e03131")
        self.assertEqual(rows[1].style["borderLeft"], "4px solid #2f9e44")
        self.assertEqual(rows[2].style["borderLeft"], "4px solid #868e96")
        center_table = army_stats_table(armies, sort_by="games", margin_left=0)
        self.assertEqual(center_table.style["marginLeft"], 0)
        center_rows = center_table.children.children[1].children
        self.assertEqual([row.children[1].children for row in center_rows],
                         ["Good army", "Evil army", "Unknown"])

    def test_pages_registered_and_render_selected_centers(self):
        links = next(link for link in app.nav.children if link.label == "Stats").children
        self.assertEqual([link.href for link in links[-2:]],
                         ["/stats/center_profiles", "/stats/centers_comparison"])
        paths = {page["path"] for page in dash.page_registry.values()}
        self.assertTrue({links[-2].href, links[-1].href} <= paths)
        names = list(centers)
        self.assertEqual(len(names), 13)
        dependencies = app.app.server.test_client().get("/_dash-dependencies").get_json()
        outputs = [entry["output"] for entry in dependencies]
        self.assertEqual(outputs.count("center-profile-output.children"), 1)
        self.assertEqual(outputs.count("..center-profile-location.search...center-profile-select.value.."), 1)
        profile = app.app.callback_map["center-profile-output.children"]["callback"].__wrapped__
        comparison = app.app.callback_map["centers-comparison-output.children"]["callback"].__wrapped__
        self.assertEqual(type(profile(names[0])).__name__, "Stack")
        result = comparison(names[0], names[1])
        self.assertEqual(type(result).__name__, "Stack")
        self.assertTrue(all(type(row).__name__ == "Grid" for row in result.children))
        for row in result.children[1:]:
            left, right = (column.children.children[0].children for column in row.children)
            self.assertEqual(left, right)
        self.assertEqual(type(comparison(names[0], names[0])).__name__, "Text")


if __name__ == "__main__":
    unittest.main()

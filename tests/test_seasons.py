import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from battle import Battle
from battle_parser import parse_battles
from db import BattleDB
from pages.stats_filters import (
    DEFAULT_FORMATS,
    FACTIONS,
    GAME_TYPES,
    PATCHES,
    SEASONS,
    battle_in_seasons,
    count_filtered_battles,
    create_filter_controls,
    filter_ids,
)


class SeasonTests(unittest.TestCase):
    def test_battle_round_trip_and_existing_battle_default(self):
        battle = Battle(result=(1, 0), player_1_id="a", player_2_id="b",
                        player_1_name="A", player_2_name="B", season=2027)
        self.assertEqual(Battle.from_dict(battle.to_dict()).season, 2027)
        legacy = battle.to_dict()
        del legacy["season"]
        self.assertEqual(Battle.from_dict(legacy).season, 2026)

    def test_duplicate_import_updates_season(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "battles.json"
            db = BattleDB(path)
            battle = Battle(result=(1, 0), player_1_id="a", player_2_id="b",
                            player_1_name="A", player_2_name="B", tournament_id="event")
            db.battles = [battle, Battle.from_dict({**battle.to_dict(), "season": 2027})]
            db.save()
            self.assertEqual(len(db.battles), 1)
            self.assertEqual(BattleDB(path).battles[0].season, 2027)

    def test_individual_and_manual_battles_inherit_season(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            submission = {
                "season": 2027, "points": "500", "tournament_type": "LOKAL",
                "people": [
                    {"status": "APPROVED", "user": {"id": player, "displayName": player},
                     "army": {"id": number, "name": player}}
                    for number, player in enumerate(("a", "b"), 1)
                ],
            }
            submission_path = path / "submission_data.json"
            submission_path.write_text(json.dumps(submission), encoding="utf-8")
            csv_path = path / "pairings_history.csv"
            row = {
                "Tournament ID": "event", "Tournament Name": "Event", "Round ID": "round",
                "Round Status": "FINISHED", "Table ID": "table",
                "P1 User ID": "a", "P2 User ID": "b",
                "P1 Secondary Points (VP)": "1", "P2 Secondary Points (VP)": "0",
            }
            with csv_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=row.keys())
                writer.writeheader()
                writer.writerow(row)
            for overrides in ({}, {"event": {"battles": [{"table_id": "table"}]}}):
                with self.subTest(overrides=overrides):
                    battles = parse_battles(str(csv_path), str(submission_path), "event", str(path), overrides)
                    self.assertEqual([battle.season for battle in battles], [2027])

    def test_doubles_battles_inherit_season(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            submission = {
                "season": 2027, "points": "2x500", "tournament_type": "LOKAL",
                "people": [
                    {"status": "APPROVED", "user": {"id": player, "displayName": player},
                     "teamId": team, "army": {"id": army, "name": team}}
                    for player, team, army in (("a1", "a", 1), ("a2", "a", 1),
                                                ("b1", "b", 2), ("b2", "b", 2))
                ],
            }
            submission_path = path / "submission_data.json"
            submission_path.write_text(json.dumps(submission), encoding="utf-8")
            csv_path = path / "pairings_history.csv"
            rows = [{
                "Tournament ID": "event", "Tournament Name": "Event", "Round ID": "round",
                "Round Status": "FINISHED", "Table ID": f"table-{number}",
                "P1 User ID": f"a{number}", "P2 User ID": f"b{number}",
                "P1 Primary Points (TP)": "1", "P2 Primary Points (TP)": "0",
                "P1 Secondary Points (VP)": "1", "P2 Secondary Points (VP)": "0",
            } for number in (1, 2)]
            with csv_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            battles = parse_battles(str(csv_path), str(submission_path), "event", str(path), {})
            self.assertEqual(len(battles), 4)
            self.assertTrue(all(battle.season == 2027 for battle in battles))

    def test_season_controls_default_to_both_and_follow_patch(self):
        controls = create_filter_controls("test").children
        ids = filter_ids("test")
        patch_index = next(i for i, component in enumerate(controls) if getattr(component, "id", None) == ids["patches"])
        season_group = controls[patch_index + 2]
        self.assertEqual(season_group.id, ids["seasons"])
        self.assertEqual(season_group.value, ["2026", "2027"])

    def test_season_filter_and_data_size(self):
        base = {"format": "INDIVIDUAL", "tournament_type": "LOCAL", "patch": "BALROG",
                "points": {"value": 500, "doubled": False}, "result": [1, 0]}
        battles = [{**base, "season": 2026}, {**base, "season": 2027}, dict(base)]
        args = (battles, [0, 1000], GAME_TYPES, PATCHES, DEFAULT_FORMATS)
        self.assertEqual(count_filtered_battles(*args), 3)
        self.assertEqual(count_filtered_battles(*args, seasons=["2026"]), 2)
        self.assertEqual(count_filtered_battles(*args, seasons=["2027"]), 1)
        self.assertEqual(count_filtered_battles(*args, seasons=[]), 0)
        self.assertTrue(battle_in_seasons(battles[2], SEASONS))

    def test_both_stats_charts_and_counts_filter_seasons(self):
        armies = [
            {"army_id": 1, "name": "Good army", "faction": "GOOD"},
            {"army_id": 2, "name": "Evil army", "faction": "EVIL"},
        ]
        with (patch("dash.register_page"), patch("store.load_armies", return_value=armies),
              patch("store.load_battles", return_value=[])):
            from pages import stats_army_list_winrates as alw
            from pages import stats_pickrate_vs_winrate as pvw
        battles = [
            {"season": year, "format": "INDIVIDUAL", "tournament_type": "LOCAL", "patch": "BALROG",
             "points": {"value": 500, "doubled": False}, "result": [1, 0],
             "army_1_id": 1, "army_2_id": 2}
            for year in (2026, 2027)
        ]
        with (patch.object(alw, "armies_data", armies), patch.object(alw, "battles_data", battles),
              patch.object(alw, "army_by_id", {a["army_id"]: a for a in armies})):
            chart = alw.compute_chart_data(battles, 1, [0, 1000], GAME_TYPES, PATCHES,
                                           FACTIONS, DEFAULT_FORMATS, 0, seasons=["2027"])
            self.assertEqual(chart[0]["games"], 1)
            self.assertEqual(alw.count_army_battles(battles, 1, [0, 1000], GAME_TYPES, PATCHES,
                                                    DEFAULT_FORMATS, seasons=["2027"]), 1)
            callback_chart, label = alw.update_chart(1, [0, 1000], GAME_TYPES, PATCHES, FACTIONS,
                                                     DEFAULT_FORMATS, 0, False, 50, ["2027"])
            self.assertEqual(callback_chart[0]["games"], 1)
            self.assertEqual(label, "Data Size: 1 battles")
        chart = pvw.compute_chart_data(battles, armies, [0, 1000], GAME_TYPES, PATCHES,
                                       FACTIONS, DEFAULT_FORMATS, 0, seasons=["2027"])
        self.assertEqual(chart[0]["data"][0]["games"], 1)
        with patch.object(pvw, "armies_data", armies), patch.object(pvw, "battles_data", battles):
            output = pvw.update_chart([0, 1000], GAME_TYPES, PATCHES, FACTIONS, DEFAULT_FORMATS,
                                      0, False, 50, ["2027"])
            self.assertEqual(output[0][0]["data"][0]["games"], 1)
            self.assertEqual(output[3], "Data Size: 1 battles")


if __name__ == "__main__":
    unittest.main()

import csv
import datetime
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from download_data import (
    build_player_cities,
    build_tournament_records,
    download_master_tournaments_data,
    download_tournament_battles_data,
    extract_armies_data,
    get_polish_events,
    build_2027_rankings,
    load_cached_tournament,
    parse_user_tournament_data,
    transform_master_ranking_data,
)


class TournamentCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = datetime.datetime.now(datetime.timezone.utc)
        self.event = {
            "id": "event-1",
            "name": "Example tournament",
            "date": datetime.date(2026, 3, 1),
            "ends_at": (self.now - datetime.timedelta(days=10)).isoformat(),
            "points": 600,
            "tournament_type": "MASTER",
            "city": {"id": 1, "name": "Town", "country": "PL"},
        }
        self.directory = Path(self.tmp.name) / "Exampletournament"
        self.directory.mkdir()
        self.submission = {
            "people": [
                {"user": {"id": "player", "city": {"id": 1, "name": "Town", "country": "PL"}},
                 "finalResult": {"place": 1}}
            ],
            "points": 600,
            "tournament_type": "MASTER",
        }
        (self.directory / "submission_data.json").write_text(json.dumps(self.submission), encoding="utf-8")
        with (self.directory / "pairings_history.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Tournament ID"])
            writer.writeheader()
            writer.writerow({"Tournament ID": self.event["id"]})

    def test_old_cache_is_used_for_battles_master_and_location_data(self):
        with patch("download_data.INPUT_DIRECTORY", self.tmp.name), patch("download_data.requests.get") as get:
            submissions = download_tournament_battles_data([self.event])
            masters = download_master_tournaments_data([self.event], submissions)
        get.assert_not_called()
        self.assertEqual(masters[0]["people"][0]["result"], 1)
        records = build_tournament_records([self.event], submissions)
        self.assertEqual(records[0]["player_ids"], ["player"])
        self.assertEqual(build_player_cities([], [], records, submissions)["player"]["name"], "Town")

    def test_event_list_retains_end_date(self):
        raw = {
            "id": "event-1", "name": "Example", "startsAt": "2026-03-01T10:00:00Z",
            "endsAt": "2026-03-03T10:00:00Z", "city": {"country": "PL"},
            "rankingEventType": {"name": "lokal"},
        }
        self.assertEqual(get_polish_events([raw])[0]["ends_at"], raw["endsAt"])

    def test_event_date_uses_polish_time_at_season_boundary(self):
        events = get_polish_events([
            {"id": "before", "name": "Before", "startsAt": "2026-11-23T22:30:00Z",
             "city": {"country": "PL"}, "rankingEventType": {"name": "lokal"}},
            {"id": "after", "name": "After", "startsAt": "2026-11-23T23:00:00Z",
             "city": {"country": "PL"}, "rankingEventType": {"name": "lokal"}},
        ])
        self.assertEqual([event["date"] for event in events],
                         [datetime.date(2026, 11, 23), datetime.date(2026, 11, 24)])

    def test_unranked_events_are_excluded_and_dmp_is_a_master_record(self):
        base = {"name": "Event", "startsAt": "2026-03-01T10:00:00Z", "city": {"country": "PL"}}
        events = get_polish_events([
            {**base, "id": "revoked", "rankingEventType": None},
            {**base, "id": "dmp", "rankingEventType": {"name": "DMP"}},
        ])
        self.assertEqual([event["id"] for event in events], ["dmp"])
        self.assertEqual(build_tournament_records(events, {})[0]["tournament_type"], "MASTER")

    def test_dmp_is_flat_30_in_master_category(self):
        results = parse_user_tournament_data([
            {"rankingEventType": {"name": "dmp"}, "rankingResult": 10},
            {"rankingEventType": {"name": "master"}, "rankingResult": 50},
            {"rankingEventType": {"name": "lokal"}, "rankingResult": 15},
        ])
        self.assertEqual((results["master_1"], results["master_2"], results["master_total"]), (50, 30, 80))
        self.assertEqual(results["local_total"], 15)

    def test_2027_rankings_apply_new_rules_and_exclude_other_seasons(self):
        events = []
        submissions = {}

        def add_event(event_id, date, tournament_type, people, teams=None):
            events.append({
                "id": event_id,
                "date": datetime.date.fromisoformat(date),
                "tournament_type": tournament_type,
            })
            submissions[event_id] = {"people": people, "teams": teams or []}

        user = {"id": "p", "displayName": "Player",
                "city": {"id": 7, "name": "Town", "country": "PL"}}
        add_event("old", "2026-11-23", "MASTER", [
            {"user": user, "finalResult": {"place": 1}},
        ])
        for index, (tournament_type, place) in enumerate([
            ("MASTER", 1), ("MASTER", 2), ("MASTER", 3), ("MASTER", 4),
            ("MASTER", 5), ("MASTER", 6), ("CHALLENGER", 1),
        ]):
            add_event(f"main-{index}", "2026-11-24", tournament_type, [
                {"user": user, "finalResult": {"place": place}},
            ])
        for index, place in enumerate((1, 2, 3, 4, 5, 6, 7)):
            add_event(f"local-{index}", "2027-01-01", "LOKAL", [
                {"user": user, "finalResult": {"place": place}},
            ])
        add_event("dmp", "2027-01-01", "DMP", [
            {"user": {"id": "dmp-only", "displayName": "DMP"}, "finalResult": {}},
        ])
        add_event("pairs", "2027-01-01", "MASTER", [
            {"user": {"id": "pairs", "displayName": "Pairs"}, "teamId": "team",
             "finalResult": {}},
        ], teams=[{"id": "team", "finalResult": {"place": 2}}])
        add_event("online", "2027-01-01", "ONLINE", [
            {"user": user, "finalResult": {"place": 17}},
        ])
        add_event("online-team", "2027-01-01", "ONLINE", [
            {"user": {"id": "online-team", "displayName": "Online Team"},
             "teamId": "team", "finalResult": {}},
        ], teams=[{"id": "team", "finalResult": {"place": 2}}])

        rankings = build_2027_rankings(events, submissions)
        main = {entry["player_id"]: entry for entry in rankings["main"]}
        master = {entry["player_id"]: entry for entry in rankings["master"]}
        online = {entry["player_id"]: entry for entry in rankings["online"]}

        self.assertEqual(
            [main["p"][f"master_challenger_{i}"] for i in range(1, 7)],
            [60, 55, 50, 48, 46, 44],
        )
        self.assertEqual(main["p"]["master_challenger_total"], 303)
        self.assertEqual([main["p"][f"local_{i}"] for i in range(1, 7)], [20, 18, 16, 15, 14, 13])
        self.assertEqual(main["p"]["local_total"], 96)
        self.assertEqual(main["p"]["score"], 399)
        self.assertEqual((master["p"]["master_1"], master["p"]["master_2"],
                          master["p"]["master_3"], master["p"]["score"]), (60, 55, 50, 165))
        self.assertNotIn("dmp-only", master)
        self.assertEqual(main["dmp-only"]["master_challenger_1"], 30)
        self.assertEqual(main["pairs"]["master_challenger_1"], 50)
        self.assertEqual(online["p"]["online_1"], 10)
        self.assertEqual(online["online-team"]["online_1"], 31)

    def test_army_metadata_excludes_unranked_snapshots(self):
        root = Path(self.tmp.name)
        battles_path = root / "battles.json"
        battles_path.write_text(json.dumps([{"army_1_id": 1, "army_1_name": "Army"}]), encoding="utf-8")
        for name, event_id, faction in (("ranked", "ranked", "GOOD"), ("revoked", "revoked", "EVIL")):
            path = root / name
            path.mkdir()
            (path / "submission_data.json").write_text(json.dumps({
                "tournament_id": event_id,
                "people": [{"army": {"id": 1, "metadata": {"mesbgType": faction}}}],
            }), encoding="utf-8")
        with patch("download_data.requests.get") as get:
            armies = extract_armies_data(str(battles_path), str(root), {"ranked"})
        get.assert_not_called()
        self.assertEqual(armies[0]["faction"], "GOOD")

    def test_master_ranking_ignores_dmp_and_recalculates_eligibility_and_places(self):
        raw = [
            {"user": {"id": "a", "displayName": "A"}, "place": 1, "score": 1},
            {"user": {"id": "b", "displayName": "B"}, "place": 2, "score": 2},
            {"user": {"id": "dmp-only"}, "place": 3, "score": 3},
        ]
        masters = [
            {"master_date": "2026-03-01", "people": [
                {"user": {"id": "a"}, "result": a},
                {"user": {"id": "b"}, "result": b},
                {"user": {"id": "dmp-only"}, "result": 1},
            ]}
            for a, b in ((5, 1), (6, 2), (7, 3))
        ]
        masters[2]["people"].pop()
        ranking = transform_master_ranking_data(raw, masters, [])
        self.assertEqual([(entry["displayName"], entry["score"], entry["place"]) for entry in ranking],
                         [("B", 6, 1), ("A", 18, 2)])

    def test_master_ranking_only_counts_2026_season_results(self):
        raw = [
            {"user": {"id": "a", "displayName": "A"}},
            {"user": {"id": "b", "displayName": "B"}},
        ]
        masters = [
            {"master_date": date, "people": [
                {"user": {"id": "a"}, "result": result},
                *([{"user": {"id": "b"}, "result": 1}] if date != "2026-11-23" else []),
            ]}
            for date, result in (
                ("2025-12-04", 1),
                ("2025-12-05", 10),
                ("2026-06-01", 11),
                ("2026-11-23", 12),
                ("2026-11-24", 1),
                ("2027-01-01", 1),
            )
        ]
        ranking = transform_master_ranking_data(raw, masters, [])
        self.assertEqual([(entry["displayName"], entry["score"], entry["place"]) for entry in ranking],
                         [("A", 33, 1)])

    def test_cached_tournament_season_uses_tournament_date(self):
        for date, expected in ((datetime.date(2026, 11, 23), 2026),
                               (datetime.date(2026, 11, 24), 2027),
                               (datetime.date(2026, 11, 25), 2027)):
            with self.subTest(date=date):
                event = {**self.event, "date": date}
                with patch("download_data.INPUT_DIRECTORY", self.tmp.name), patch("download_data.requests.get") as get:
                    submissions = download_tournament_battles_data([event])
                get.assert_not_called()
                self.assertEqual(submissions[event["id"]]["season"], expected)
                saved = json.loads((self.directory / "submission_data.json").read_text(encoding="utf-8"))
                self.assertEqual(saved["season"], expected)

    def test_recent_missing_invalid_or_future_end_dates_are_not_cached(self):
        for end in (
            (self.now - datetime.timedelta(days=6)).isoformat(),
            (self.now + datetime.timedelta(days=2)).isoformat(),
            None,
            "not a date",
            "2026-01-01",
            123,
        ):
            with self.subTest(end=end):
                self.assertIsNone(load_cached_tournament({**self.event, "ends_at": end}, self.directory))

    def test_missing_corrupt_wrong_event_or_pre_end_files_are_not_cached(self):
        path = self.directory / "submission_data.json"
        csv_path = self.directory / "pairings_history.csv"
        path.unlink()
        self.assertIsNone(load_cached_tournament(self.event, self.directory))
        path.write_text("invalid json", encoding="utf-8")
        self.assertIsNone(load_cached_tournament(self.event, self.directory))
        path.write_text(json.dumps(self.submission), encoding="utf-8")
        csv_path.write_text("Tournament ID\nanother-event\n", encoding="utf-8")
        self.assertIsNone(load_cached_tournament(self.event, self.directory))
        csv_path.write_text("Tournament ID\nevent-1\n", encoding="utf-8")
        before_end = (self.now - datetime.timedelta(days=11)).timestamp()
        os.utime(csv_path, (before_end, before_end))
        self.assertIsNone(load_cached_tournament(self.event, self.directory))

    def test_downloaded_empty_tournament_is_cached_on_next_run(self):
        (self.directory / "submission_data.json").unlink()
        (self.directory / "pairings_history.csv").unlink()
        rounds = Mock(status_code=200)
        rounds.json.return_value = {"rounds": []}
        submission = Mock(status_code=200)
        submission.json.return_value = self.submission.copy()
        with patch("download_data.INPUT_DIRECTORY", self.tmp.name), \
             patch("download_data.requests.get", side_effect=[rounds, submission]) as get:
            first = download_tournament_battles_data([self.event])
            self.assertEqual(get.call_count, 2)
        with patch("download_data.INPUT_DIRECTORY", self.tmp.name), patch("download_data.requests.get") as get:
            second = download_tournament_battles_data([self.event])
            get.assert_not_called()
        self.assertEqual(first, second)

    def test_new_tournament_saves_2027_season(self):
        (self.directory / "submission_data.json").unlink()
        (self.directory / "pairings_history.csv").unlink()
        rounds = Mock(status_code=200)
        rounds.json.return_value = {"rounds": []}
        submission = Mock(status_code=200)
        submission.json.return_value = self.submission.copy()
        event = {**self.event, "date": datetime.date(2026, 11, 24)}
        with patch("download_data.INPUT_DIRECTORY", self.tmp.name), \
             patch("download_data.requests.get", side_effect=[rounds, submission]):
            submissions = download_tournament_battles_data([event])
        self.assertEqual(submissions[event["id"]]["season"], 2027)
        saved = json.loads((self.directory / "submission_data.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["season"], 2027)

    def test_recent_tournament_downloads_both_rounds_and_submission(self):
        recent = {**self.event, "ends_at": (self.now - datetime.timedelta(days=1)).isoformat()}
        rounds = Mock(status_code=200)
        rounds.json.return_value = {"rounds": [{"id": "round-1", "title": "Round 1"}]}
        details = Mock(status_code=200)
        details.json.return_value = {"pairings": [{"id": "table-1"}]}
        submission = Mock(status_code=200)
        submission.json.return_value = self.submission.copy()
        with patch("download_data.INPUT_DIRECTORY", self.tmp.name), \
             patch("download_data.requests.get", side_effect=[rounds, details, submission]) as get:
            results = download_tournament_battles_data([recent])
        self.assertEqual(get.call_count, 3)
        self.assertEqual(results["event-1"]["people"], self.submission["people"])
        with (self.directory / "pairings_history.csv").open(encoding="utf-8", newline="") as f:
            self.assertEqual(next(csv.DictReader(f))["Table ID"], "table-1")

    def test_failed_round_download_does_not_replace_saved_data(self):
        before_csv = (self.directory / "pairings_history.csv").read_bytes()
        before_submission = (self.directory / "submission_data.json").read_bytes()
        recent = {**self.event, "ends_at": (self.now - datetime.timedelta(days=1)).isoformat()}
        failed_rounds = Mock(status_code=503)
        submission = Mock(status_code=200)
        submission.json.return_value = self.submission.copy()
        with patch("download_data.INPUT_DIRECTORY", self.tmp.name), \
             patch("download_data.requests.get", side_effect=[failed_rounds, submission]):
            download_tournament_battles_data([recent])
        self.assertEqual((self.directory / "pairings_history.csv").read_bytes(), before_csv)
        self.assertEqual((self.directory / "submission_data.json").read_bytes(), before_submission)


if __name__ == "__main__":
    unittest.main()

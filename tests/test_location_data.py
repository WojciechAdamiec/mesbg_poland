import unittest
from unittest.mock import patch

from achievements import calculate_achievements, player_locations_by_id
from download_data import (
    build_player_cities,
    build_player_profiles,
    build_tournament_records,
    get_polish_events,
    transform_online_ranking_data,
    transform_ranking_data,
)


class LocationDataTests(unittest.TestCase):
    def test_locations_deduplicate_cities_and_include_online(self):
        tournaments = [
            {"tournament_id": "one", "city": {"id": 1, "name": "Town", "country": "PL"},
             "player_ids": ["one", "two"]},
            {"tournament_id": "repeat", "city": {"id": 1, "name": "Town", "country": "PL"},
             "player_ids": ["one"]},
            {"tournament_id": "online", "city": {"id": 3040, "name": "ONLINE", "country": "PL"},
             "player_ids": ["one"]},
            {"tournament_id": "other", "city": {"id": 2, "name": "Other", "country": "PL"},
             "player_ids": ["two"]},
        ]
        self.assertEqual(player_locations_by_id(tournaments),
                         {"one": ["Town", "ONLINE"], "two": ["Other", "Town"]})
        for field in ("city", "player_ids"):
            broken = {**tournaments[0], field: None}
            with self.assertRaisesRegex(ValueError, "incomplete"):
                player_locations_by_id([broken])

    def test_strider_unlocks_at_five_distinct_locations(self):
        profiles = [{"player_id": "one", "displayName": "One", "draws": 0, "opponents": [], "army_lists": []}]
        tournaments = [
            {"tournament_id": str(i), "city": {"id": i, "name": f"Town {i}"}, "player_ids": ["one"]}
            for i in range(7)
        ]
        four = calculate_achievements(profiles, {}, tournaments[:4])[0]
        five = calculate_achievements(profiles, {}, tournaments[:5])[0]
        self.assertEqual(four["locations_count"], 4)
        self.assertNotIn("Strider", four["achievements"])
        self.assertEqual(five["locations_count"], 5)
        self.assertEqual(five["achievement_progress"]["Strider"], {"current": 5, "target": 10, "stage": 1})

    def test_event_city_and_participants_are_preserved(self):
        events = get_polish_events([
            {"id": "event", "name": "Example", "startsAt": "2026-03-01T10:00:00Z",
             "city": {"id": 42, "name": "Town", "country": "PL"},
             "rankingEventType": {"name": "challenger"}, "pointsLimit": 600},
            {"id": "foreign", "startsAt": "2026-03-01T10:00:00Z", "city": {"country": "GB"}},
        ])
        submissions = {"event": {"people": [
            {"user": {"id": "one"}, "finalResult": {"place": 1}},
            {"user": {"id": "one"}, "finalResult": {"place": 1}},
            {"user": {"id": "two"}, "finalResult": {"place": 2}},
            {"user": {"id": "declined"}, "finalResult": None},
        ]}}
        records = build_tournament_records(events, submissions)
        self.assertEqual(records, [{
            "tournament_id": "event", "name": "Example", "date": "2026-03-01",
            "tournament_type": "CHALLENGER", "city": {"id": 42, "name": "Town", "country": "PL"},
            "player_ids": ["one", "two"],
        }])
        self.assertIsNone(build_tournament_records(events, {})[0]["player_ids"])

    def test_player_city_prefers_rankings_and_latest_submission(self):
        tournaments = [
            {"tournament_id": "new", "date": "2026-05-01"},
            {"tournament_id": "old", "date": "2026-01-01"},
        ]
        submissions = {
            "old": {"people": [{"user": {"id": "fallback", "city": {"id": 1, "name": "Old"}}}]},
            "new": {"people": [
                {"user": {"id": "fallback", "city": {"id": 2, "name": "New", "country": "PL"}}},
                {"user": {"id": "ranked", "city": {"id": 3, "name": "Outdated"}}},
                {"user": {"id": "unknown", "city": {"id": 3, "name": "Outdated"}}},
                {"user": {"id": "same", "city": {"id": 5, "name": "Same", "country": "PL"}}},
            ]},
        }
        main = [{"player_id": "ranked", "city_id": 4, "city_name": "Current", "city_country": "PL"},
                {"player_id": "unknown", "city_name": None},
                {"player_id": "same", "city_name": "Same"}]
        online = [{"player_id": "ranked", "city_name": "Online city"},
                  {"player_id": "online", "city_name": "Online only"}]
        cities = build_player_cities(main, online, tournaments, submissions)
        self.assertEqual(cities["fallback"], {"id": 2, "name": "New", "country": "PL"})
        self.assertEqual(cities["ranked"], {"id": 4, "name": "Current", "country": "PL"})
        self.assertIsNone(cities["unknown"])
        self.assertEqual(cities["online"]["name"], "Online only")
        self.assertEqual(cities["same"], {"id": 5, "name": "Same", "country": "PL"})

    def test_ranking_transform_retains_city_identity(self):
        raw = [{"id": "ranking-entry", "user": {
            "id": "player", "city": {"id": 12, "name": "Town", "country": "PL"},
            "discordUsername": "linked-account",
        }}, {"id": "unlinked-entry", "user": {
            "id": "unlinked-player", "discordUsername": None,
        }}]
        with (patch("download_data.get_user_tournaments", return_value=[]),
              patch("download_data.get_user_online_tournaments", return_value=[])):
            main = transform_ranking_data(raw)
            online = transform_online_ranking_data(raw)
        for ranking in (main, online):
            self.assertEqual(
                (ranking[0]["city_id"], ranking[0]["city_name"], ranking[0]["city_country"]),
                (12, "Town", "PL"),
            )
            self.assertTrue(ranking[0]["discord_linked"])
            self.assertFalse(ranking[1]["discord_linked"])
            self.assertNotIn("discordUsername", ranking[0])

    def test_player_profiles_store_discord_link_status_from_both_rankings(self):
        battles = [{
            "format": "SINGLES", "result": [1, 0],
            "player_1_id": "main-player", "player_1_name": "Main player",
            "player_2_id": "online-player", "player_2_name": "Online player",
        }]
        profiles = build_player_profiles(
            battles,
            [{"player_id": "main-player", "discord_linked": True}],
            [{"player_id": "online-player", "discord_linked": True}],
        )
        self.assertEqual(
            {profile["player_id"]: profile["discord_linked"] for profile in profiles},
            {"main-player": True, "online-player": True},
        )


if __name__ == "__main__":
    unittest.main()

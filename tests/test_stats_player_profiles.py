import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from battle import TournamentType
from battle_parser import INDIVIDUAL, TEAM
from player_profile_stats import ArmyExpertise, seasonal_trophies, unique_trophy_players
from store import PlayerTournamentResults, TournamentWin, load_tournament_results
import achievements
import download_data


with (
    patch("dash.register_page"),
    patch("store.load_player_profiles", return_value=[]),
    patch("store.load_main_ranking", return_value=[]),
    patch("store.load_main_ranking_2027", return_value=[]),
    patch("store.load_master_ranking", return_value=[]),
    patch("store.load_online_ranking", return_value=[]),
    patch("store.load_armies", return_value=[]),
    patch("store.load_battles", return_value=[]),
    patch("store.load_tournament_results", return_value={}),
):
    import pages.stats_player_profiles as profile_page
    import pages.stats_player_comparison as comparison_page
    from pages.stats_player_profiles import (
        _achievements_section,
        _expertise_section,
        _table,
        _trophies,
        build_profile_sections,
    )


class PlayerProfileTests(unittest.TestCase):
    def test_player_rank_boundaries_and_mithril_requires_full_completion(self):
        self.assertEqual([(name, threshold) for name, threshold, _ in achievements.PLAYER_RANKS], [
            ("Leaf", 0), ("Wooden", 10), ("Stone", 20), ("Copper", 30), ("Bronze", 40),
            ("Iron", 50), ("Silver", 60), ("Gold", 70), ("Emerald", 80), ("Diamond", 90),
            ("Mithril", 100),
        ])
        definitions = tuple(
            achievements.Achievement(f"Achievement {index}", "", "achievement.png",
                                     lambda player, results: False)
            for index in range(100)
        )
        names = [definition.name for definition in definitions]
        with patch.object(profile_page, "ACHIEVEMENTS", definitions):
            for index, (_, threshold, _) in enumerate(profile_page.PLAYER_RANKS):
                with self.subTest(threshold=threshold):
                    self.assertEqual(profile_page._rank_progress(names[:threshold])[2], index)
                    if threshold:
                        self.assertEqual(profile_page._rank_progress(names[:threshold - 1])[2], index - 1)
            self.assertEqual(profile_page._rank_progress(names[:89])[2], 8)
            self.assertEqual(profile_page._rank_progress(names[:90])[2], 9)
            self.assertEqual(profile_page._rank_progress(names[:99])[2], 9)
            self.assertEqual(profile_page._rank_progress(names + names[:1] + ["unknown"]), (100, 100, 10))
            self.assertIsNone(profile_page._rank_progress(None))
        total = achievements.total_achievement_stages(achievements.ACHIEVEMENTS)
        for index, (_, threshold, _) in enumerate(achievements.PLAYER_RANKS[1:], start=1):
            required = (threshold * total + 99) // 100
            with self.subTest(threshold=threshold, total=total):
                self.assertEqual(achievements.rank_index_for_count(required - 1, total), index - 1)
                self.assertEqual(achievements.rank_index_for_count(required, total), index)

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_rank_section_and_distribution_exclude_missing_profiles(self, _asset_url):
        definitions = tuple(
            achievements.Achievement(f"Achievement {index}", "", "achievement.png",
                                     lambda player, results: False)
            for index in range(100)
        )
        names = [definition.name for definition in definitions]
        players = [{"achievements": []}, {"achievements": names[:4]},
                   {"achievements": names[:10]}, {"achievements": names}, {}]
        with patch.object(profile_page, "ACHIEVEMENTS", definitions):
            counts, unavailable = profile_page._rank_distribution(players)
            self.assertEqual((counts[0], counts[1], counts[-1], sum(counts), unavailable),
                             (2, 1, 1, 4, 1))
            section = profile_page._player_rank_section(players[1], players)
            rank_card = section.children[0].children.children
            self.assertEqual(rank_card[1].children, "Leaf (4/100 4.0%)")
            self.assertFalse(any(isinstance(child, profile_page.dmc.Progress) for child in section.children))
            track = section.children[1].children
            self.assertEqual(len(track.children), 11)
            self.assertEqual(track.gap, 4)
            self.assertTrue(all(tooltip.children.style["minWidth"] == "80px" for tooltip in track.children))
            self.assertEqual([text.children for text in track.children[0].label.children],
                             ["Leaf: 0%", "0/100 achievements needed", "You already have this"])
            self.assertEqual([text.children for text in track.children[1].label.children],
                             ["Wooden: 10%", "10/100 achievements needed", "You need 6 more to get this"])
            self.assertEqual(track.children[1].children.attributes["tabIndex"], 0)
            chart = section.children[2]
            self.assertIn("exclude players without calculated achievements", chart.children[1].children)
            graph = chart.children[2].children
            self.assertEqual(list(graph.figure.data[0].y), [count * 25 for count in counts])
            self.assertEqual(graph.figure.data[0].x[0], "Leaf (0%)")
            self.assertNotEqual(graph.figure.data[0].orientation, "h")
            self.assertIn("%{y:.1f}%", graph.figure.data[0].hovertemplate)
            complete = profile_page._player_rank_section(players[3], players)
            self.assertEqual(complete.children[0].children.children[1].children, "Mithril (100/100 100.0%)")
            self.assertEqual(complete.children[1].children.children[-1].label.children[-1].children,
                             "You already have this")
            missing = profile_page._player_rank_section({}, players)
            self.assertIn("unavailable", missing.children[0].children)
            empty_chart = profile_page._rank_distribution_chart([{}], None)
            self.assertIn("unavailable", empty_chart.children[1].children)

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_rank_tooltip_rounds_required_achievements_up(self, _asset_url):
        definitions = tuple(
            achievements.Achievement(f"Achievement {index}", "", "achievement.png",
                                     lambda player, results: False)
            for index in range(56)
        )
        profile = {"achievements": [a.name for a in definitions[:2]]}
        with patch.object(profile_page, "ACHIEVEMENTS", definitions):
            section = profile_page._player_rank_section(profile, [profile])
        tooltip = section.children[1].children.children[1]
        self.assertEqual([text.children for text in tooltip.label.children],
                         ["Wooden: 10%", "6/56 achievements needed", "You need 4 more to get this"])

    def test_table_only_limits_height_when_more_than_ten_rows(self):
        columns = [("Name", "name")]
        rows = [{"name": str(index)} for index in range(11)]

        short_table = _table("Players", rows[:10], columns).children[1]
        long_table = _table("Players", rows, columns).children[1]

        self.assertIsNone(short_table.h)
        self.assertEqual(long_table.h, 442)
        self.assertEqual(long_table.scrollbars, "xy")

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_trophies_show_all_top_50_wins_with_ranking_boundaries(self, _asset_url):
        ranking = [{"player_id": str(place), "place": place} for place in (1, 10, 11, 30, 31, 50, 51)]
        ranking.append({"player_id": "lost", "place": 2})
        battles = [
            {"player_1_id": "winner", "player_2_id": str(place),
             "player_2_name": f"Player {place}", "result": [1, 0]}
            for place in (50, 51, 31, 30, 11, 10, 1) for _ in range(2)
        ]
        battles.extend([
            {"player_1_id": "winner", "player_2_id": "unranked", "result": [1, 0]},
            {"player_1_id": "winner", "player_2_id": "lost", "result": [0, 1]},
        ])
        rankings = {2026: ranking}
        trophy_results = seasonal_trophies(battles, rankings)
        self.assertIs(seasonal_trophies(battles, {2026: ranking}), trophy_results)
        players = trophy_results["winner"][2026]
        self.assertEqual([p["main_ranking_place"] for p in players], [1, 10, 11, 30, 31, 50])

        trophy_section = _trophies(players)
        cards = trophy_section.children[1].children
        self.assertEqual(len(cards), 6)
        self.assertEqual(
            [card.children.children[0].children[1].style["backgroundColor"] for card in cards],
            ["#facc15", "#facc15", "#cbd5e1", "#cbd5e1", "#cd7f32", "#cd7f32"],
        )
        first = cards[0].children.children
        self.assertEqual(first[1].children, "Player 1")
        self.assertEqual(first[0].children[0].children, "#1")
        self.assertIn("shooting-target-icon.png", first[0].children[1].style["maskImage"])
        self.assertIn("crossed-swords-icon.png", first[0].children[2].children[0].style["maskImage"])
        self.assertEqual(first[0].children[2].children[1].children, "2")
        self.assertEqual(first[0].children[2].attributes["aria-label"], "Times defeated: 2")
        self.assertEqual(cards[0].style["width"], "180px")

    def test_trophies_are_season_specific_and_count_unique_opponents(self):
        rankings = {
            2026: [{"player_id": "shared", "place": 5}, {"player_id": "only-2026", "place": 40}],
            2027: [{"player_id": "shared", "place": 8}, {"player_id": "only-2027", "place": 20}],
        }
        def battle(loser, season, result=(5, 0), **kwargs):
            return {"player_1_id": "winner", "player_2_id": loser, "player_2_name": loser,
                    "season": season, "result": result, **kwargs}
        battles = [
            battle("shared", 2026), battle("shared", 2026), battle("shared", 2027),
            battle("only-2026", 2027), battle("only-2027", 2027),
            battle("only-2026", 2026, result=(0, 5)), battle("only-2026", 2026, format="DOUBLES"),
        ]
        trophies = seasonal_trophies(battles, rankings)["winner"]
        self.assertEqual([(t["player_id"], t["times_defeated"]) for t in trophies[2026]], [("shared", 2)])
        self.assertEqual([t["player_id"] for t in trophies[2027]], ["shared", "only-2027"])
        self.assertEqual(unique_trophy_players(trophies), {"shared", "only-2027"})
        self.assertEqual(unique_trophy_players(trophies, 10), {"shared"})

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_profile_displays_both_trophy_seasons(self, _asset_url):
        profile = {"army_lists": [], "opponent_army_lists": [], "opponents": []}
        with (patch.object(profile_page, "profile_by_id", {"winner": profile}),
              patch.object(profile_page, "trophies_by_player", {}),
              patch.object(profile_page.army_expertise, "for_player", return_value=[])):
            section = profile_page.build_profile_sections("winner")[4]
        self.assertEqual([item.children[0].children for item in section.children],
                         ["Top Player Trophies 2026", "Top Player Trophies 2027"])

    def test_multiseason_achievements_use_unique_trophies_and_any_frontman_season(self):
        rankings = {
            2026: [{"player_id": "winner", "place": 5, "city_name": "Poznań"},
                   {"player_id": "rival", "place": 1, "city_name": "Poznań"},
                   *[{"player_id": f"top-{i}", "place": i} for i in range(1, 11)]],
            2027: [{"player_id": "winner", "place": 1, "city_name": "Poznań"},
                   {"player_id": "rival", "place": 5, "city_name": "Poznań"},
                   *[{"player_id": f"top-{i}", "place": i} for i in range(1, 11)]],
        }
        battles = [
            {"season": year, "player_1_id": "winner", "player_2_id": f"top-{i}", "result": [1, 0]}
            for year in (2026, 2027) for i in range(1, 11)
        ]
        profile = {"player_id": "winner", "draws": 0, "opponents": [], "army_lists": []}
        result = achievements.calculate_achievements(
            [profile], {}, [], main_ranking=rankings[2026],
            rankings_by_season=rankings, battles=battles,
        )[0]
        self.assertEqual(result["achievement_progress"]["Headhunter"]["current"], 10)
        self.assertEqual(result["achievement_progress"]["Beat the Unbeatable"]["current"], 10)
        self.assertIn("Center's Frontman", result["achievements"])

    def test_center_frontman_uses_mapped_cities_across_seasons_and_preserves_ties(self):
        rankings = {
            2026: [
                {"player_id": "first", "place": 5, "city_name": "Kraków"},
                {"player_id": "tied", "place": 5, "city_name": "Wieliczka"},
                {"player_id": "second", "place": 10, "city_name": "Wieliczka"},
                {"player_id": "unknown", "place": 1, "city_name": "Unknown"},
                {"player_id": "no_city", "place": 2, "city_name": "Kraków"},
            ],
            2027: [
                {"player_id": "second", "place": 1, "city_name": "Wieliczka"},
                {"player_id": "first", "place": 2, "city_name": "Kraków"},
            ],
        }
        cities = {"no_city": None}
        profiles = [
            {"player_id": player, "draws": 0, "opponents": [], "army_lists": []}
            for player in ("first", "tied", "second", "unknown", "no_city")
        ]
        result = achievements.calculate_achievements(
            profiles, {}, [], rankings_by_season=rankings, player_cities=cities, nations_cup_player_ids=set(),
        )
        self.assertEqual(
            {profile["player_id"] for profile in result if "Center's Frontman" in profile["achievements"]},
            {"first", "tied", "second"},
        )
        _, mapping = achievements.load_center_mapping()
        self.assertEqual(achievements._center_frontmen({2026: rankings[2026]}, cities, mapping),
                         {"first", "tied"})
        modified_mapping = {**mapping, "wieliczka": "Other"}
        self.assertEqual(achievements._center_frontmen({2026: rankings[2026]}, cities, modified_mapping),
                         {"first", "tied"})
        modified_mapping = {**mapping, "wieliczka": None}
        self.assertEqual(achievements._center_frontmen({2026: rankings[2026]}, cities, modified_mapping),
                         {"first"})

    def test_expertise_uses_shared_competition_ranking_by_player_id(self):
        battles = []
        for index in range(10):
            for _ in range(2):
                battles.append({
                    "army_1_id": 1,
                    "player_1_id": f"winner-{index}",
                    "player_1_name": "Same name",
                    "result": [1, 0],
                })
        battles.extend([
            {"army_1_id": 1, "player_1_id": "selected", "player_1_name": "Same name", "result": [0, 1]},
            {"army_1_id": 2, "player_1_id": "selected", "player_1_name": "Same name", "result": [1, 0]},
            {"army_2_id": 2, "player_2_id": "other", "player_2_name": "Other", "result": [0, 1]},
        ])
        for index in range(9):
            for _ in range(2):
                battles.append({
                    "army_1_id": 3,
                    "player_1_id": f"winner-{index}",
                    "player_1_name": "Same name",
                    "result": [1, 0],
                })
        battles.extend([
            {"army_1_id": 3, "player_1_id": "selected", "player_1_name": "Same name", "result": [0, 1]},
            {"army_1_id": 3, "player_1_id": "tied", "player_1_name": "Same name", "result": [0, 1]},
        ])
        expertise = ArmyExpertise(battles, [], [
            {"army_id": 1, "name": "First"}, {"army_id": 2, "name": "Second"}, {"army_id": 3, "name": "Third"},
        ])
        result = expertise.for_player("selected", [{"army_id": 1}, {"army_id": 2}, {"army_id": 3}, {"army_id": None}])
        no_top_ten = expertise.for_player("selected", [{"army_id": 1}])
        self.assertEqual([(row["army_name"], row["place"]) for row in result], [("Second", 1), ("Third", 10)])
        self.assertEqual(no_top_ten, [])
        self.assertEqual(_expertise_section(no_top_ten).children[1].children, "No army lists ranked in the top 10.")

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_expertise_tier_colors(self, _asset_url):
        armies = [
            {"army_name": str(place), "place": place, "adjusted_winrate": 50.0}
            for place in (1, 2, 5, 6, 10)
        ]
        cards = _expertise_section(armies).children[1].children
        self.assertEqual(
            [card.children.children[0].children[1].style["backgroundColor"] for card in cards],
            ["#facc15", "#cbd5e1", "#cbd5e1", "#cd7f32", "#cd7f32"],
        )

    def test_no_selected_player_has_no_profile_sections(self):
        self.assertEqual(build_profile_sections(None), (None, None, None, None, None, None))
        self.assertEqual(profile_page.update_achievements(None, "default"), (None, {"display": "none"}))

    def test_player_url_sync_and_other_query_parameters(self):
        with patch.object(profile_page, "profile_by_id", {"one": {}, "two": {}}):
            sync = profile_page._sync_player_url
            no_update = profile_page.no_update
            self.assertEqual(sync("?player=one", None, None), (no_update, "one"))
            self.assertEqual(sync("?player=two", "one", "pp-location"), (no_update, "two"))
            self.assertEqual(sync("?player=unknown", "one", "pp-location"), (no_update, None))
            self.assertEqual(sync("?view=full&player=one", "two", "pp-selected-player"),
                             ("?view=full&player=two", no_update))
            self.assertEqual(sync("?view=full&player=one", None, "pp-selected-player"),
                             ("?view=full", no_update))
            self.assertEqual(sync("?player=one", "one", "pp-selected-player"), (no_update, no_update))

    def test_comparison_url_sync_for_both_players(self):
        with patch.object(comparison_page, "profile_by_id", {"one": {}, "two": {}}):
            sync = comparison_page._sync_players_url
            no_update = comparison_page.no_update
            self.assertEqual(sync("?player_a=one&player_b=two", None, None, None),
                             (no_update, "one", "two"))
            self.assertEqual(sync("?player_a=two&player_b=unknown", "one", "two", "pc-location"),
                             (no_update, "two", None))
            self.assertEqual(sync("?view=full&player_a=one", "one", "two", "pc-player-b"),
                             ("?view=full&player_a=one&player_b=two", no_update, no_update))
            self.assertEqual(sync("?view=full&player_a=one&player_b=two", None, "two", "pc-player-a"),
                             ("?view=full&player_b=two", no_update, no_update))
            self.assertEqual(sync("?player_a=one&player_b=two", "one", "two", "pc-player-b"),
                             (no_update, no_update, no_update))

    def test_tournament_wins_use_first_place_and_player_ids(self):
        def person(player_id, place):
            return {"user": {"id": player_id}, "finalResult": {"place": place}}

        with tempfile.TemporaryDirectory() as directory:
            for index, tournament_type in enumerate(("LOKAL", "CHALLENGER", "MASTER", "ONLINE", None)):
                tournament = Path(directory) / str(index)
                tournament.mkdir()
                (tournament / "submission_data.json").write_text(json.dumps({
                    "tournament_type": tournament_type,
                    "people": [person("winner", 1), person("teammate", 1), person("runner-up", 2),
                               {"user": {"id": "missing-result"}, "finalResult": None}],
                }), encoding="utf-8")
            results = load_tournament_results(directory)
        expected = {TournamentWin(tournament_type, INDIVIDUAL) for tournament_type in (
            TournamentType.LOCAL, TournamentType.CHALLENGER, TournamentType.MASTER, TournamentType.ONLINE,
        )}
        self.assertEqual({player: result.wins for player, result in results.items() if result.wins},
                         {"winner": expected, "teammate": expected})

    def test_team_win_requires_winning_team_standings(self):
        with tempfile.TemporaryDirectory() as directory:
            tournament = Path(directory) / "team-event"
            tournament.mkdir()
            (tournament / "submission_data.json").write_text(json.dumps({
                "tournament_type": "LOKAL",
                "teams": [{"id": "winning-team", "finalResult": {"place": 1}},
                          {"id": "other-team", "finalResult": {"place": 2}}],
                "people": [
                    {"user": {"id": "one"}, "teamId": "winning-team", "finalResult": {"place": 1}},
                    {"user": {"id": "two"}, "teamId": "winning-team", "finalResult": {"place": 1}},
                    {"user": {"id": "other"}, "teamId": "other-team", "finalResult": {"place": 1}},
                ],
            }), encoding="utf-8")
            results = load_tournament_results(directory)
        expected = {TournamentWin(TournamentType.LOCAL, TEAM)}
        self.assertEqual({player: result.wins for player, result in results.items() if result.wins},
                         {"one": expected, "two": expected})

    def test_veggie_alpha_excludes_the_winner_when_checking_top_50(self):
        def person(player_id, place):
            return {"user": {"id": player_id}, "finalResult": {"place": place}}

        with tempfile.TemporaryDirectory() as directory:
            for name, winner, opponent in (
                ("no-top-50", "winner", "rank-51"),
                ("top-50-opponent", "winner-with-top-opponent", "rank-50"),
            ):
                tournament = Path(directory) / name
                tournament.mkdir()
                (tournament / "submission_data.json").write_text(json.dumps({
                    "tournament_type": "LOKAL",
                    "people": [person(winner, 1), person(opponent, 2)],
                }), encoding="utf-8")
            ranking = [
                {"player_id": "winner", "place": 1},
                {"player_id": "rank-50", "place": 50},
                {"player_id": "rank-51", "place": 51},
            ]
            results = load_tournament_results(directory, ranking)
        self.assertTrue(results["winner"].veggie_alpha)
        self.assertFalse(results["winner-with-top-opponent"].veggie_alpha)
        veggie_alpha = next(a for a in achievements.ACHIEVEMENTS if a.name == "Eggplant Among Veggies")
        self.assertTrue(veggie_alpha.condition({}, results["winner"]))
        self.assertFalse(veggie_alpha.condition({}, results["winner-with-top-opponent"]))

    def test_veggie_alpha_uses_ranking_of_tournament_season(self):
        with tempfile.TemporaryDirectory() as directory:
            for season in (2026, 2027):
                folder = Path(directory) / str(season)
                folder.mkdir()
                (folder / "submission_data.json").write_text(json.dumps({
                    "season": season, "tournament_type": "LOKAL",
                    "people": [
                        {"user": {"id": f"winner-{season}"}, "finalResult": {"place": 1}},
                        {"user": {"id": "opponent"}, "finalResult": {"place": 2}},
                    ],
                }), encoding="utf-8")
            rankings = {
                2026: [{"player_id": "opponent", "place": 51}],
                2027: [{"player_id": "opponent", "place": 50}],
            }
            results = load_tournament_results(directory, rankings_by_season=rankings)
            self.assertTrue(results["winner-2026"].veggie_alpha)
            self.assertFalse(results["winner-2027"].veggie_alpha)
            results = load_tournament_results(directory, rankings_by_season={2026: rankings[2026]})
            self.assertFalse(results["winner-2027"].veggie_alpha)

    def test_tournament_participation_uses_standings_not_battles(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, tournament_type in enumerate(("CHALLENGER", "LOKAL")):
                event = Path(directory) / str(index)
                event.mkdir()
                (event / "submission_data.json").write_text(json.dumps({
                    "tournament_type": tournament_type,
                    "people": [
                        {"user": {"id": "played"}, "finalResult": {"place": 2}},
                        {"user": {"id": "played"}, "finalResult": {"place": 2}},
                        {"user": {"id": "declined"}, "finalResult": {"stageId": 1}},
                    ],
                }), encoding="utf-8")
            results = load_tournament_results(directory)
        self.assertEqual(results["played"].events, {TournamentType.CHALLENGER: 1, TournamentType.LOCAL: 1})
        self.assertNotIn("declined", results)
        with patch.object(comparison_page, "tournament_results_by_player", results):
            self.assertEqual(comparison_page._events_of_type("played", "CHALLENGER"), 1)
            self.assertEqual(comparison_page._events_of_type("played", "LOCAL"), 1)
            self.assertEqual(comparison_page._events_of_type("played", "MASTER"), 0)

    def test_all_loss_achievement_requires_at_least_one_loss_and_no_draws_or_wins(self):
        people = [
            {"user": {"id": player}, "finalResult": result}
            for player, result in [
                ("loser", {"wins": 0, "draws": 0, "loss": 3}),
                ("draw", {"wins": 0, "draws": 1, "loss": 2}),
                ("win", {"wins": 1, "draws": 0, "loss": 2}),
                ("no-games", {"wins": 0, "draws": 0, "loss": 0}),
                ("missing", {"loss": 3}),
            ]
        ]
        with tempfile.TemporaryDirectory() as directory:
            tournament = Path(directory) / "event"
            tournament.mkdir()
            (tournament / "submission_data.json").write_text(json.dumps({
                "tournament_type": "LOKAL", "people": people,
            }), encoding="utf-8")
            results = load_tournament_results(directory)
        self.assertEqual(set(results), {"loser"})
        loser = next(a for a in achievements.ACHIEVEMENTS if a.name == "Consolation Prize")
        self.assertTrue(loser.condition({}, results["loser"]))

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_achievements_show_all_with_unlocked_and_locked_states(self, _asset_url):
        progress = {
            achievement.name: {
                "stage": 1 if achievement.name in {"Challenge Accepted", "Power of Friendship"} else 0,
                "current": achievement.stages[0] if achievement.name in {"Challenge Accepted", "Power of Friendship"} else 0,
                "target": achievement.stages[1] if achievement.name in {"Challenge Accepted", "Power of Friendship"} else achievement.stages[0],
            }
            for achievement in achievements.ACHIEVEMENTS if achievement.stage_count > 1
        }
        grid = _achievements_section(
            ["Challenge Accepted", "Power of Friendship", "Vox populi, vox Dei"], progress_by_name=progress,
        ).children[-1]
        cards = grid.children
        self.assertEqual(grid.cols, {"base": 1, "sm": 2, "lg": 4})
        self.assertEqual(grid.style, {"maxWidth": "1356px", "width": "100%", "gridAutoRows": "1fr"})
        self.assertEqual([card.children.children[1].children for card in cards[:10]], [
            "King of the Neighbourhood 0/3", "Challenge Accepted 1/3", "The Big Fish 0/3",
            "Virtually Unstoppable 0/3", "Ultimate Champion", "One-Man Army 0/3",
            "Power of Friendship 1/3", "Eggplant Among Veggies", "Consolation Prize 0/3", "War Veteran 0/5",
        ])
        self.assertEqual(cards[-1].children.children[1].children, "Hoarding Instincts 0/10")
        self.assertEqual(cards[1].children.children[0].style["backgroundColor"], "#cd7f32")
        self.assertEqual(cards[6].children.children[0].style["backgroundColor"], "#cd7f32")
        self.assertEqual([card.children.children[4].children for card in cards],
                         [str(number) for number in range(1, len(cards) + 1)])
        self.assertTrue(all(len(card.children.children) in (5, 6) for card in cards))
        self.assertEqual(cards[0].children.children[3].style["right"], "12px")
        self.assertEqual(cards[0].children.children[4].style["left"], "12px")
        self.assertEqual(cards[0].children.children[3].style["fontSize"], "1.5rem")
        self.assertEqual(cards[0].children.children[4].style["fontSize"], "1.5rem")
        self.assertIn("locked", cards[0].to_plotly_json()["props"]["aria-label"])
        self.assertIn("partially unlocked", cards[1].to_plotly_json()["props"]["aria-label"])
        self.assertTrue(all("achievement.png" in card.children.children[0].style["maskImage"] for card in cards))
        self.assertEqual(cards[1].children.children[2].children, "Win 3 Challenger tournaments.")
        self.assertEqual(cards[1].children.children[2].style["minHeight"], "3.75rem")
        self.assertTrue(all(card.style["minHeight"] == "257px" for card in cards))

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_locked_achievement_progress_is_displayed_only_when_available(self, _asset_url):
        achievement_name = "Ah, Yes. The Negotiator"
        progress = {achievement_name: {"current": 4, "target": 5, "stage": 0}}
        cards = _achievements_section([], progress_by_name=progress).children[-1].children
        card = next(card for card in cards if card.children.children[1].children == achievement_name + " 0/3")
        bar, label = card.children.children[-1].children
        self.assertEqual(bar.value, 80)
        self.assertEqual(label.children, "4 / 5")
        self.assertEqual(label.style["fontSize"], card.children.children[3].style["fontSize"])
        self.assertEqual(card.children.children[-1].style["marginTop"], "auto")
        self.assertIn("4 / 5", bar.attributes["aria-label"])
        unlocked = _achievements_section([achievement_name], progress_by_name={
            achievement_name: {"current": 15, "target": 15, "stage": 3},
        }).children[-1].children
        card = next(card for card in unlocked if card.children.children[1].children == achievement_name + " 3/3")
        self.assertEqual(len(card.children.children), 5)
        unavailable = _achievements_section(None, progress_by_name=progress).children[-1].children
        card = next(card for card in unavailable if card.children.children[1].children == achievement_name + " ?/3")
        self.assertEqual(len(card.children.children), 5)
        with patch.object(profile_page, "profile_by_id", {
            "one": {"achievements": [], "achievement_progress": progress},
        }):
            section, _ = profile_page.update_achievements("one", "default")
        card = next(card for card in section.children[-1].children
                    if card.children.children[1].children == achievement_name + " 0/3")
        self.assertEqual(card.children.children[-1].children[1].children, "4 / 5")

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_achievement_percentages_use_all_profiles_and_deduplicate_unlocks(self, _asset_url):
        players = [{"achievements": ["Discorded", "Discorded"]},
                   {"achievements": ["Discorded"]},
                   {"achievements": []}]
        percentages = profile_page._achievement_percentages(players)
        with patch.object(profile_page, "achievement_percentages", percentages):
            cards = _achievements_section([]).children[-1].children
        card = next(card for card in cards if card.children.children[1].children == "Discorded")
        self.assertEqual(card.children.children[3].children.children.children, "66.7%")
        self.assertEqual(card.children.children[3].style["position"], "absolute")
        self.assertEqual(card.children.children[3].style["right"], "12px")
        self.assertIn("66.7% of players", card.to_plotly_json()["props"]["aria-label"])
        self.assertIsNone(profile_page._achievement_percentages([]))
        self.assertIsNone(profile_page._achievement_percentages([{"achievements": []}, {}]))

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_achievement_rarity_sort_groups_unlocks_and_sorts_descending(self, _asset_url):
        definitions = tuple(
            achievements.Achievement(name, name, "achievement.png", lambda player, results: False)
            for name in ("A", "B", "C", "D", "E")
        )
        percentages = {"A": 10, "B": 70, "C": 90, "D": 70, "E": 5}
        unlocked = ["A", "B", "D"]
        with (patch.object(profile_page, "ACHIEVEMENTS", definitions),
              patch.object(profile_page, "achievement_percentages", percentages)):
            default = _achievements_section(unlocked, "default").children[-1].children
            rarity = _achievements_section(unlocked, "rarity").children[-1].children
            locked = _achievements_section([], "rarity").children[-1].children
        names = lambda cards: [card.children.children[1].children for card in cards]
        self.assertEqual(names(default), ["A", "B", "C", "D", "E"])
        self.assertEqual(names(rarity), ["B", "D", "A", "C", "E"])
        self.assertEqual(names(locked), ["C", "B", "D", "A", "E"])
        numbers = lambda cards: [card.children.children[4].children for card in cards]
        self.assertEqual(numbers(default), ["1", "2", "3", "4", "5"])
        self.assertEqual(numbers(rarity), ["2", "4", "1", "3", "5"])
        self.assertEqual(numbers(locked), ["3", "2", "4", "1", "5"])

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_custom_achievement_uses_profile_condition_and_icon(self, _asset_url):
        achievement = achievements.Achievement(
            "Veteran", "Play ten games.", "custom.png", lambda player, wins: player["games_played"] >= 10,
        )
        with patch.object(profile_page, "ACHIEVEMENTS", (achievement,)):
            card = _achievements_section(["Veteran"]).children[-1].children[0]
        self.assertEqual(card.children.children[0].style["backgroundColor"], "#facc15")
        self.assertIn("custom.png", card.children.children[0].style["maskImage"])

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_requested_achievement_icons_render(self, _asset_url):
        icons = {
            "Ultimate Champion": "champion.png",
            "Consolation Prize": "prize.png",
            "Jack of All Trades": "jack.png",
            "Shapeshifter": "shapeshifter.png",
            "Headhunter": "sniper.png",
            "Discorded": "discord.png",
            "Rat Catcher": "rat.png",
            "The Gingerbread Must Flow": "cookie.png",
            "War Veteran": "war_veteran.png",
            "Hold my Beer": "beer.png",
            "Staff Meeting": "broom.png",
        }
        selected = tuple(a for a in achievements.ACHIEVEMENTS if a.name in icons)
        self.assertEqual({a.name for a in selected}, set(icons))
        with patch.object(profile_page, "ACHIEVEMENTS", selected):
            cards = _achievements_section([]).children[-1].children
        icon_dir = Path(__file__).resolve().parents[1] / "assets" / "icons"
        for achievement, card in zip(selected, cards):
            with self.subTest(achievement=achievement.name):
                icon = icons[achievement.name]
                self.assertTrue((icon_dir / icon).is_file())
                self.assertIn(f"/assets/icons/{icon}", card.children.children[0].style["maskImage"])

    def test_orku_slayer_requires_being_or_defeating_orku(self):
        qualifies = achievements._is_orku_slayer
        self.assertTrue(qualifies({"displayName": "OrkuOrku", "opponents": []}))
        self.assertTrue(qualifies({"displayName": "Other", "opponents": [
            {"displayName": " OrkuOrku ", "wins": 1},
        ]}))
        self.assertFalse(qualifies({"displayName": "Other", "opponents": [
            {"displayName": "OrkuOrku", "wins": 0},
            {"displayName": "Someone else", "wins": 1},
        ]}))

    def test_coordinators_achievement_requires_membership_or_a_win_against_a_member(self):
        achievement = next(a for a in achievements.ACHIEVEMENTS if a.name == "If you can't beat Them, join Them")
        member_ids = achievements.get_tag("players", "coordinators").items
        results = PlayerTournamentResults()
        for member_id in member_ids:
            with self.subTest(member_id=member_id):
                self.assertTrue(achievement.condition({"player_id": member_id, "opponents": []}, results))
                self.assertTrue(achievement.condition({
                    "player_id": "other", "opponents": [{"player_id": member_id, "wins": 1}],
                }, results))
                self.assertFalse(achievement.condition({
                    "player_id": "other", "opponents": [{"player_id": member_id, "wins": 0}],
                }, results))
        self.assertFalse(achievement.condition({
            "player_id": "other", "opponents": [{"player_id": "other", "displayName": "Shogun", "wins": 1}],
        }, results))

    def test_representatives_achievement_requires_membership_or_a_win_against_a_member(self):
        achievement = next(a for a in achievements.ACHIEVEMENTS if a.name == "Vox populi, vox Dei")
        results = PlayerTournamentResults()
        for member_id in achievements.get_tag("players", "representatives").items:
            with self.subTest(member_id=member_id):
                self.assertTrue(achievement.condition({"player_id": member_id, "opponents": []}, results))
                self.assertTrue(achievement.condition({
                    "player_id": "other", "opponents": [{"player_id": member_id, "wins": 1}],
                }, results))
                self.assertFalse(achievement.condition({
                    "player_id": "other", "opponents": [{"player_id": member_id, "wins": 0}],
                }, results))
        self.assertFalse(achievement.condition({
            "player_id": "other", "opponents": [{"player_id": "other", "wins": 1}],
        }, results))

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_representatives_achievement_text_renders_tag_tooltip(self, _asset_url):
        cards = _achievements_section([]).children[-1].children
        card = next(card for card in cards if card.children.children[1].children == "Vox populi, vox Dei")
        description = card.children.children[2].children
        self.assertEqual(description.children[0], "Be or beat one of the ")
        self.assertEqual(description.children[1].children.children, "Representatives")
        self.assertIn("Representatives: Kajoj\nKarolczi\nKrell", card.to_plotly_json()["props"]["aria-label"])

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_coordinators_achievement_text_renders_tag_tooltip(self, _asset_url):
        cards = _achievements_section([]).children[-1].children
        card = next(card for card in cards if card.children.children[1].children == "If you can't beat Them, join Them")
        description = card.children.children[2].children
        self.assertEqual(description.children[0], "Be or beat one of the ")
        self.assertEqual(description.children[1].children.children, "Coordinators")
        self.assertIn("Coordinators: Bakson\nFishPriest\nGadii\nKacik\nShogun\n", card.to_plotly_json()["props"]["aria-label"])

    def test_individual_and_team_achievements_are_independent(self):
        individual = next(a for a in achievements.ACHIEVEMENTS if a.name == "One-Man Army")
        team = next(a for a in achievements.ACHIEVEMENTS if a.name == "Power of Friendship")
        individual_results = PlayerTournamentResults(win_format_counts={INDIVIDUAL: 1})
        team_results = PlayerTournamentResults(win_format_counts={TEAM: 1})
        self.assertTrue(individual.condition({}, individual_results))
        self.assertFalse(team.condition({}, individual_results))
        self.assertTrue(team.condition({}, team_results))
        self.assertFalse(individual.condition({}, team_results))

    def test_discorded_requires_a_linked_discord_account(self):
        discorded = next(a for a in achievements.ACHIEVEMENTS if a.name == "Discorded")
        results = PlayerTournamentResults()
        self.assertTrue(discorded.condition({"discord_linked": True}, results))
        self.assertFalse(discorded.condition({"discord_linked": False}, results))
        self.assertFalse(discorded.condition({}, results))

    def test_army_tag_achievements_count_wins_across_tagged_armies(self):
        monsters = next(a for a in achievements.ACHIEVEMENTS if a.name == "Big Game Hunter")
        self.assertEqual(monsters.text, "Win at least 5 games against [[tag:army_lists:monsters]].")

        profile = {
            "player_id": "one",
            "draws": 0,
            "army_lists": [],
            "opponent_army_lists": [
                {"army_id": 315, "wins": 3},
                {"army_id": 324, "wins": 2},
                {"army_id": 468, "wins": 10},
            ],
        }
        name = "Burn the Westfold"
        reached = achievements.calculate_achievements([profile], {}, [])[0]
        self.assertIn(name, reached["achievements"])
        self.assertEqual(reached["achievement_progress"][name], {"current": 5, "target": 10, "stage": 1})

        profile["opponent_army_lists"][1]["wins"] = 1
        below = achievements.calculate_achievements([profile], {}, [])[0]
        self.assertNotIn(name, below["achievements"])
        self.assertEqual(below["achievement_progress"][name], {"current": 4, "target": 5, "stage": 0})

    def test_selected_army_tag_achievements_count_wins_with_armies(self):
        for tag_id, name, first_army, second_army in (
            ("wizards", "Staff Meeting", 381, 367),
            ("hobbits", "Small Victories", 435, 458),
            ("hero-armies", "Plot Armour Supplier", 314, 319),
        ):
            with self.subTest(tag_id=tag_id):
                achievement = next(a for a in achievements.ACHIEVEMENTS if a.name == name)
                self.assertEqual(
                    achievement.text, f"Win at least 5 games with [[tag:army_lists:{tag_id}]]."
                )
                profile = {
                    "player_id": "one",
                    "draws": 0,
                    "army_lists": [
                        {"army_id": first_army, "games": 4, "wins": 3},
                        {"army_id": second_army, "games": 3, "wins": 2},
                        {"army_id": 999, "games": 10, "wins": 10},
                    ],
                    "opponent_army_lists": [{"army_id": first_army, "wins": 20}],
                }
                reached = achievements.calculate_achievements([profile], {}, [])[0]
                self.assertIn(name, reached["achievements"])
                self.assertEqual(reached["achievement_progress"][name], {"current": 5, "target": 10, "stage": 1})
                profile["army_lists"][1]["wins"] = 1
                below = achievements.calculate_achievements([profile], {}, [])[0]
                self.assertNotIn(name, below["achievements"])
                self.assertEqual(below["achievement_progress"][name], {"current": 4, "target": 5, "stage": 0})

    def test_radagasts_alliance_counts_for_both_monster_achievements(self):
        profile = {
            "player_id": "one", "draws": 0, "opponents": [],
            "army_lists": [{"army_id": 343, "games": 12, "wins": 10}],
            "opponent_army_lists": [{"army_id": 343, "wins": 5}],
        }
        result = achievements.calculate_achievements([profile], {}, [])[0]
        self.assertEqual(result["achievement_progress"]["Big Game Hunter"],
                         {"current": 5, "target": 10, "stage": 1})
        self.assertEqual(result["achievement_progress"]["I kill when I wish"],
                         {"current": 10, "target": 15, "stage": 2})

    def test_army_achievement_pairs_have_requested_names_and_order(self):
        expected = (
            ("rohan", "Muster the Rohirrim!", "Burn the Westfold"),
            ("gondor", "Gondor Needs no King", "King needed after all"),
            ("isengard", "Leave none alive!", "Unhanded"),
            ("mordor", "Do you not know Death?", "Eye Sore"),
            ("moria", "Light Not Included", "Mine Your Own Business"),
            ("evil-north", "Relentless March South", "Cold Reception"),
            ("evil-men", "No Glory in Pointless Defeat", "It's Treason Then"),
            ("elves", "Chosen by Valars", "Not Really Immortal"),
            ("dwarves", "Hold my Beer", "Beard Trimmer"),
            ("hobbits", "Small Victories", "Shoes Required"),
            ("monsters", "I kill when I wish", "Big Game Hunter"),
            ("wizards", "Staff Meeting", "There is no Light"),
            ("hero-armies", "Plot Armour Supplier", "We've been made Equal"),
            ("good-men", "Oath Fulfilled", "Moral Superiority"),
        )
        definitions = achievements.BASE_ACHIEVEMENTS
        for tag_id, with_name, against_name in expected:
            with self.subTest(tag=tag_id):
                index = next(i for i, achievement in enumerate(definitions) if achievement.name == with_name)
                self.assertEqual(definitions[index + 1].name, against_name)
                self.assertEqual(definitions[index].text,
                                 f"Win at least 5 games with [[tag:army_lists:{tag_id}]].")
                self.assertEqual(definitions[index + 1].text,
                                 f"Win at least 5 games against [[tag:army_lists:{tag_id}]].")

    def test_every_army_tag_has_independent_win_with_and_against_stages(self):
        definitions = achievements.ACHIEVEMENTS
        self.assertEqual(len({achievement.name for achievement in definitions}), len(definitions))
        for tag in achievements.load_tags("army_lists"):
            with self.subTest(tag=tag.id):
                against_name = achievements._army_tag_achievement(tag, False).name
                with_name = achievements._army_tag_achievement(tag, True).name
                against = next(a for a in definitions if a.name == against_name)
                with_army = next(a for a in definitions if a.name == with_name)
                self.assertNotEqual(against.name, with_army.name)
                for count in (0, 4, 5, 9, 10, 14, 15):
                    profile = {
                        "player_id": "one", "draws": 0, "opponents": [],
                        "army_lists": [{"army_id": tag.items[0], "games": 20, "wins": count}],
                        "opponent_army_lists": [{"army_id": tag.items[0], "wins": 15 - count}],
                    }
                    result = achievements.calculate_achievements([profile], {}, [])[0]
                    for achievement, wins in ((with_army, count), (against, 15 - count)):
                        stage = sum(wins >= target for target in (5, 10, 15))
                        self.assertEqual(result["achievement_progress"][achievement.name], {
                            "current": wins, "target": (5, 10, 15)[min(stage, 2)], "stage": stage,
                        })

    def test_draw_army_and_location_stage_boundaries(self):
        base = {"player_id": "one", "opponents": [], "army_lists": []}
        tournaments = [
            {"tournament_id": str(i), "city": {"id": i, "name": f"Town {i}"}, "player_ids": ["one"]}
            for i in range(31)
        ]
        for name, targets in (
            ("Ah, Yes. The Negotiator", (5, 10, 15)),
            ("Shapeshifter", (10, 20, 30)),
            ("Strider", (5, 10, 15)),
        ):
            for count in sorted({0, *(value for target in targets for value in (target - 1, target))}):
                with self.subTest(achievement=name, count=count):
                    profile = {
                        **base, "draws": count,
                        "army_lists": [{"army_id": i, "games": 1} for i in range(count)],
                    }
                    result = achievements.calculate_achievements([profile], {}, tournaments[:count])[0]
                    stage = sum(count >= target for target in targets)
                    self.assertEqual(result["achievement_progress"][name], {
                        "current": count, "target": targets[min(stage, 2)], "stage": stage,
                    })

    def test_game_milestones_at_boundaries(self):
        profile = {"player_id": "one", "draws": 0, "army_lists": [], "opponents": []}
        targets = (30, 50, 80, 120, 200)
        for games in (0, 29, 30, 49, 50, 79, 80, 119, 120, 199, 200, 201):
            with self.subTest(games=games):
                result = achievements.calculate_achievements([{**profile, "games_played": games}], {}, [])[0]
                stage = sum(games >= target for target in targets)
                self.assertEqual("War Veteran" in result["achievements"], stage > 0)
                self.assertNotIn("No Longer Fresh", result["achievements"])
                self.assertNotIn("Field Tested", result["achievements"])
                self.assertEqual(result["achievement_progress"]["War Veteran"], {
                    "current": games, "target": targets[min(stage, 4)], "stage": stage,
                })
                self.assertEqual(result["achievements_count"],
                                 len(result["achievements"]) + max(stage - 1, 0))

    def test_season_ranking_achievement_uses_best_place_across_seasons(self):
        places = (None, 0, 51, 50, 31, 30, 11, 10, 1)
        profiles = [
            {"player_id": str(index), "draws": 0, "army_lists": [], "opponents": []}
            for index in range(len(places))
        ]
        rankings = {
            2026: [{"player_id": str(index), "place": place} for index, place in enumerate(places)],
            2027: [{"player_id": "3", "place": 10}, {"player_id": "5", "place": 51}],
        }
        results = achievements.calculate_achievements(
            profiles, {}, [], rankings_by_season=rankings, nations_cup_player_ids=set(),
        )
        self.assertEqual(
            [result["achievement_progress"]["Primus Inter Pares"]["stage"] for result in results],
            [0, 0, 0, 3, 1, 2, 2, 3, 3],
        )
        for result, stage in zip(results, (0, 0, 0, 3, 1, 2, 2, 3, 3)):
            self.assertEqual("Primus Inter Pares" in result["achievements"], stage > 0)
            self.assertEqual(result["achievements_count"],
                             len(result["achievements"]) + max(stage - 1, 0))

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_season_ranking_card_has_stage_labels_without_progress_bar(self, _asset_url):
        achievement = next(a for a in achievements.ACHIEVEMENTS if a.name == "Primus Inter Pares")
        with (patch.object(profile_page, "ACHIEVEMENTS", (achievement,)),
              patch.object(profile_page, "achievement_percentages", {achievement.name: [50, 30, 10]})):
            card = _achievements_section(
                [achievement.name],
                progress_by_name={achievement.name: {"stage": 2, "current": 2, "target": 3}},
            ).children[-1].children[0]
        self.assertEqual(card.children.children[1].children, "Primus Inter Pares 2/3")
        self.assertIn("top 10", card.children.children[2].children)
        self.assertEqual(len(card.children.children), 5)
        tooltip = card.children.children[3].children.label.children[1].children
        self.assertEqual([line.children for line in tooltip], [
            "Stage 1 (Top 50): 50.0%", "Stage 2 (Top 30): 30.0%", "Stage 3 (Top 10): 10.0%",
        ])

    def test_nations_cup_teams_are_ordered_by_master_ranking(self):
        path = Path(__file__).resolve().parents[1] / "data" / "hall_of_fame_nations_cup_2027.json"
        teams = json.loads(path.read_text(encoding="utf-8"))["teams"]
        self.assertEqual(
            [[player["player_id"] for player in team["players"]] for team in teams],
            [
                [
                    "93cda88b-c976-4e61-8f65-9a5a5f1ecf7b",
                    "6a2a00f2-2511-49bb-abf4-034ba4382126",
                    "9e5a191c-e93a-436d-b7b0-95d223dd6e2e",
                    "d96af431-77bb-4909-bb15-61df62e81b15",
                    "76870d30-055b-4a89-a141-78ef032269f2",
                    "c451779b-6172-4e1a-acbd-1b387949849d",
                ],
                [
                    "5f6a7ffa-1a94-4176-a2f0-42f18d04a39e",
                    "beec30f8-4a47-431b-b7ed-e7f37e95bbbc",
                    "e0392558-e263-4874-b380-e33152fcecbe",
                    "97c5e5bc-7502-4f16-9c1b-53ead4fab5b2",
                    "9d5bc521-d1ac-416e-952c-926b6aef9e60",
                    "224b8d3d-7e1f-4095-853a-088883879195",
                ],
            ],
        )
        self.assertEqual(
            [[player["placement"] for player in team["players"]] for team in teams],
            [[1, 2, 4, 5, 6, 15], [3, 7, 8, 9, 10, 12]],
        )

    def test_poland_strong_uses_nations_cup_player_ids(self):
        from store import load_nations_cup_2027_player_ids

        members = load_nations_cup_2027_player_ids()
        self.assertEqual(len(members), 12)
        self.assertIn("93cda88b-c976-4e61-8f65-9a5a5f1ecf7b", members)
        profiles = [
            {"player_id": player_id, "draws": 0, "army_lists": [], "opponents": []}
            for player_id in (*members, "not-a-member")
        ]
        results = achievements.calculate_achievements(profiles, {}, [], rankings_by_season={})
        self.assertTrue(all("Poland Strong" in profile["achievements"] for profile in results[:-1]))
        self.assertNotIn("Poland Strong", results[-1]["achievements"])
        self.assertEqual([a.name for a in achievements.ACHIEVEMENTS[-3:]],
                         ["Primus Inter Pares", "Poland Strong", "Hoarding Instincts"])

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_multistage_cards_show_next_progress_colors_and_stage_percentages(self, _asset_url):
        veteran = next(a for a in achievements.ACHIEVEMENTS if a.name == "War Veteran")
        profiles = [
            {"achievements": ["War Veteran"] if stage else [],
             "achievement_progress": {"War Veteran": {"stage": stage, "current": games, "target": target}}}
            for stage, games, target in (
                (0, 0, 30), (1, 30, 50), (2, 60, 80),
                (3, 80, 120), (4, 120, 200), (5, 200, 200),
            )
        ]
        with patch.object(profile_page, "ACHIEVEMENTS", (veteran,)):
            percentages = profile_page._achievement_percentages(profiles)
            self.assertEqual(percentages["War Veteran"], [500 / 6, 400 / 6, 50, 200 / 6, 100 / 6])
            with patch.object(profile_page, "achievement_percentages", percentages):
                cards = [
                    _achievements_section(profile["achievements"],
                                          progress_by_name=profile["achievement_progress"]).children[-1].children[0]
                    for profile in profiles
                ]
            self.assertEqual([card.children.children[1].children for card in cards],
                             [f"War Veteran {stage}/5" for stage in range(6)])
            self.assertEqual([card.children.children[0].style["backgroundColor"] for card in cards],
                             ["#6b7280", "#a07855", "#a8a29e", "#cd7f32", "#cbd5e1", "#facc15"])
            self.assertEqual([card.children.children[3].children.children.children for card in cards],
                             ["83.3%", "83.3%", "66.7%", "50.0%", "33.3%", "83.3%"])
            self.assertEqual([card.children.children[2].children for card in cards], [
                "Play 30 games.", "Play 50 games.", "Play 80 games.",
                "Play 120 games.", "Play 200 games.", "Play 200 games.",
            ])
            for card in cards:
                self.assertIn(card.children.children[2].children, card.to_plotly_json()["props"]["aria-label"])
            tooltip = cards[2].children.children[3].children
            self.assertEqual(tooltip.classNames, {"tooltip": "tag-tooltip-popup"})
            self.assertEqual(tooltip.label.children[0].children, "War Veteran")
            self.assertEqual([text.children for text in tooltip.label.children[1].children], [
                "Stage 1 (30): 83.3%", "Stage 2 (50): 66.7%", "Stage 3 (80): 50.0%",
                "Stage 4 (120): 33.3%", "Stage 5 (200): 16.7%",
            ])
            bar, label = cards[2].children.children[-1].children
            self.assertAlmostEqual(bar.value, 100 / 3)
            self.assertEqual(label.children, "60 / 80")
            self.assertEqual(len(cards[-1].children.children), 5)
            self.assertEqual(profile_page._rank_progress(
                profiles[2]["achievements"], profiles[2]["achievement_progress"])[:2], (2, 5))

    def test_stage_gradations_and_completion_count_use_stages(self):
        self.assertEqual([profile_page._stage_color(i, 3) for i in range(1, 4)],
                         ["#cd7f32", "#cbd5e1", "#facc15"])
        self.assertEqual([profile_page._stage_color(i, 5) for i in range(1, 6)],
                         ["#a07855", "#a8a29e", "#cd7f32", "#cbd5e1", "#facc15"])
        veteran = next(a for a in achievements.BASE_ACHIEVEMENTS if a.name == "War Veteran")
        base = (veteran,) + tuple(
            achievements.Achievement(f"Base {i}", "", "achievement.png", lambda player, results: False)
            for i in range(49)
        )
        profile = {"player_id": "one", "draws": 0, "games_played": 200, "army_lists": [], "opponents": []}
        with patch.object(achievements, "BASE_ACHIEVEMENTS", base):
            calculated = achievements.calculate_achievements([profile], {}, [])[0]
        self.assertEqual(calculated["achievement_progress"]["Hoarding Instincts"]["current"], 5 * 100 // 54)

    def test_local_win_milestones_count_distinct_events_including_team_wins(self):
        profile = {"player_id": "one", "draws": 0, "army_lists": [], "opponents": []}
        with tempfile.TemporaryDirectory() as directory:
            for index in range(6):
                tournament = Path(directory) / str(index)
                tournament.mkdir()
                winning_person = {"user": {"id": "one"}, "teamId": "first", "finalResult": {"place": 1}}
                event = {
                    "tournament_type": "LOKAL",
                    "people": [winning_person, winning_person,
                               {"user": {"id": "other"}, "teamId": "second", "finalResult": {"place": 1}}],
                }
                if index == 2:
                    event["teams"] = [{"id": "first", "finalResult": {"place": 1}},
                                      {"id": "second", "finalResult": {"place": 2}}]
                (tournament / "submission_data.json").write_text(json.dumps(event), encoding="utf-8")
                results = load_tournament_results(directory)
                count = index + 1
                self.assertEqual(results["one"].win_counts[TournamentType.LOCAL], count)
                if index == 2:
                    self.assertEqual(results["other"].win_counts[TournamentType.LOCAL], 2)
                calculated = achievements.calculate_achievements([profile], results, [])[0]
                stage = sum(count >= target for target in (1, 3, 5))
                self.assertEqual(calculated["achievement_progress"]["King of the Neighbourhood"], {
                    "current": count, "target": (1, 3, 5)[min(stage, 2)], "stage": stage,
                })

    def test_tournament_stages_count_distinct_wins_formats_and_all_loss_events(self):
        profile = {"player_id": "winner", "draws": 0, "army_lists": [], "opponents": []}
        types = (
            ("LOKAL", TournamentType.LOCAL, "King of the Neighbourhood"),
            ("CHALLENGER", TournamentType.CHALLENGER, "Challenge Accepted"),
            ("MASTER", TournamentType.MASTER, "The Big Fish"),
            ("ONLINE", TournamentType.ONLINE, "Virtually Unstoppable"),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index in range(5):
                for raw_type, tournament_type, name in types:
                    folder = Path(directory) / f"{raw_type}-{index}"
                    folder.mkdir()
                    winner = {"user": {"id": "winner"}, "finalResult": {"place": 1}}
                    if index % 2:
                        winner["teamId"] = "team"
                    loser = {"user": {"id": "loser"}, "finalResult": {
                        "place": 2, "wins": 0, "draws": 0, "loss": 3,
                    }}
                    event = {
                        "tournament_type": raw_type,
                        "people": [winner, winner, *([loser, loser] if raw_type == "LOKAL" else [])],
                        "teams": [{"id": "team", "finalResult": {"place": 1}}] if index % 2 else [],
                    }
                    (folder / "submission_data.json").write_text(json.dumps(event), encoding="utf-8")
                results = load_tournament_results(directory)
                count = index + 1
                self.assertEqual(results["loser"].lost_all_count, count)
                self.assertEqual(results["winner"].win_format_counts, {
                    INDIVIDUAL: (index // 2 + 1) * 4,
                    **({TEAM: ((index + 1) // 2) * 4} if index else {}),
                })
                calculated = achievements.calculate_achievements([profile], results, [])[0]
                stage = sum(count >= target for target in (1, 3, 5))
                for _, tournament_type, name in types:
                    self.assertEqual(results["winner"].win_counts[tournament_type], count)
                    self.assertEqual(calculated["achievement_progress"][name]["stage"], stage)
                for name, kind in (("One-Man Army", INDIVIDUAL), ("Power of Friendship", TEAM)):
                    wins = results["winner"].win_format_counts.get(kind, 0)
                    self.assertEqual(calculated["achievement_progress"][name]["stage"],
                                     sum(wins >= target for target in (1, 3, 5)))
                lost = achievements.calculate_achievements([{**profile, "player_id": "loser"}], results, [])[0]
                self.assertEqual(lost["achievement_progress"]["Consolation Prize"]["stage"],
                                 sum(count >= target for target in (1, 3, 5)))

    def test_ultimate_champion_requires_all_four_types(self):
        hattrick = next(a for a in achievements.ACHIEVEMENTS if a.name == "Ultimate Champion")
        wins = {TournamentWin(kind, INDIVIDUAL) for kind in (
            TournamentType.LOCAL, TournamentType.CHALLENGER, TournamentType.MASTER, TournamentType.ONLINE,
        )}
        self.assertTrue(hattrick.condition({}, PlayerTournamentResults(wins)))
        for win in wins:
            self.assertFalse(hattrick.condition({}, PlayerTournamentResults(wins - {win})))

    def test_completion_milestones_use_only_base_achievements(self):
        base = tuple(
            achievements.Achievement(f"Base {index}", "", "achievement.png",
                                     lambda player, results, index=index: index < player["earned"])
            for index in range(53)
        )
        profile = {"player_id": "one", "draws": 0, "army_lists": [], "opponents": [],
                   "achievements": [a.name for a in achievements.COMPLETION_ACHIEVEMENTS]}
        with patch.object(achievements, "BASE_ACHIEVEMENTS", base):
            for threshold in range(10, 101, 10):
                target = (threshold * len(base) + 99) // 100
                for count in (target - 1, target):
                    with self.subTest(threshold=threshold, count=count):
                        result = achievements.calculate_achievements([{**profile, "earned": count}], {}, [])[0]
                        current = count * 100 // len(base)
                        stage = current // 10
                        self.assertEqual(result["achievement_progress"]["Hoarding Instincts"], {
                            "current": current, "target": min((stage + 1) * 10, 100), "stage": stage,
                        })
                        self.assertEqual("Hoarding Instincts" in result["achievements"], stage > 0)

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_completion_card_displays_percentage_progress(self, _asset_url):
        completion = achievements.COMPLETION_ACHIEVEMENTS[0]
        with (patch.object(profile_page, "ACHIEVEMENTS", (completion,)),
              patch.object(profile_page, "achievement_percentages", {completion.name: [0] * 10})):
            card = _achievements_section(
                [completion.name],
                progress_by_name={completion.name: {"stage": 2, "current": 27, "target": 30}},
            ).children[-1].children[0]
        self.assertEqual(card.children.children[1].children, "Hoarding Instincts 2/10")
        self.assertEqual(card.children.children[2].children, "Unlock at least 30% of non-completion achievements.")
        self.assertEqual(card.children.children[-1].children[1].children, "27% / 30%")
        self.assertIn("Stage 10 (100%): 0.0%",
                      [line.children for line in card.children.children[3].children.label.children[1].children])

    def test_army_variety_and_city_achievements(self):
        city_names = [
            *[("poznan-" + str(i), "Poznań") for i in range(5)],
            *[("wroclaw-" + str(i), "Wrocław") for i in range(5)],
            ("katowice-1", "Katowice"), ("katowice-2", "Katowice"),
            ("gliwice-1", "Gliwice"), ("rybnik-1", "Rybnik"), ("zabrze-1", "Zabrze"),
            *[("warszawa-" + str(i), "Warszawa") for i in range(5)],
        ]
        opponents = [
            {"player_id": player_id, "wins": 1}
            for player_id, _city in city_names
        ]
        opponents.append({"player_id": "lost-in-poznan", "wins": 0})
        silesia_city_ids = {
            "Katowice": 227, "Gliwice": 3142, "Rybnik": 2864, "Zabrze": 3189,
        }
        player_cities = {
            player_id: {"name": city, **({"id": silesia_city_ids[city]} if city in silesia_city_ids else {})}
            for player_id, city in city_names
        }
        player_cities["lost-in-poznan"] = {"name": "Poznań"}
        main_ranking = [
            {"player_id": "selected", "place": 20, "city_id": 1, "city_name": "Poznań"},
            {"player_id": "same-city-second", "place": 21, "city_id": 1, "city_name": "Poznań"},
            {"player_id": "other-city-first", "place": 1, "city_id": 2, "city_name": "Other"},
            {"player_id": "cityless", "place": 2},
        ]
        profiles = [
            {"player_id": "selected", "draws": 0, "opponents": opponents,
             "army_lists": [{"army_id": army_id, "games": 1} for army_id in range(10)]
             + [{"army_id": 0, "games": 2}]},
            {"player_id": "same-city-second", "draws": 0, "opponents": [], "army_lists": []},
            {"player_id": "cityless", "draws": 0, "opponents": [], "army_lists": []},
            {"player_id": "nine-armies", "draws": 0, "opponents": [],
             "army_lists": [{"army_id": army_id, "games": 1} for army_id in range(9)]},
        ]
        updated = achievements.calculate_achievements(
            profiles, {}, [], main_ranking=main_ranking, player_cities=player_cities
        )
        selected_achievements = set(updated[0]["achievements"])
        self.assertTrue({
            "Shapeshifter", "Potato Peeler", "Rat Catcher", "Age of Coal is Over",
            "Capital Punishment", "Center's Frontman",
        }.issubset(selected_achievements))
        self.assertNotIn("Center's Frontman", updated[1]["achievements"])
        self.assertNotIn("Center's Frontman", updated[2]["achievements"])
        self.assertNotIn("Shapeshifter", updated[3]["achievements"])

    def test_city_achievement_progress_counts_distinct_defeated_players(self):
        cities = {
            "Capital Punishment": ("Warszawa",), "Rat Catcher": ("Wrocław",),
            "Potato Peeler": ("Poznań",),
            "Dragon Slayer": ("Kraków",),
            "Go back to Bałuty": ("Łódź",),
            "The Gingerbread Must Flow": ("Bydgoszcz", "Toruń"),
            "Adults Only": ("Bielsko-Biała",), "Mayonnaise Enjoyer": ("Kielce",),
        }
        for name, locations in cities.items():
            with self.subTest(achievement=name):
                opponents = [{"player_id": str(i), "wins": 1} for i in range(5)]
                player_cities = {str(i): {"name": locations[i % len(locations)]} for i in range(5)}
                base = {"player_id": "one", "draws": 4, "army_lists": []}
                below = achievements.calculate_achievements(
                    [{**base, "opponents": opponents[:4] + [opponents[0], {**opponents[4], "wins": 0}]}],
                    {}, [], player_cities=player_cities,
                )[0]
                self.assertNotIn(name, below["achievements"])
                self.assertEqual(below["achievement_progress"][name], {"current": 4, "target": 5})
                self.assertEqual(below["achievement_progress"]["Ah, Yes. The Negotiator"],
                                 {"current": 4, "target": 5, "stage": 0})
                unlocked = achievements.calculate_achievements(
                    [{**base, "opponents": opponents}], {}, [], player_cities=player_cities,
                )[0]
                self.assertIn(name, unlocked["achievements"])
                self.assertEqual(unlocked["achievement_progress"][name], {"current": 5, "target": 5})

    def test_silesia_achievement_uses_place_tag_and_counts_distinct_defeats(self):
        name = "Age of Coal is Over"
        opponents = [{"player_id": str(i), "wins": 1} for i in range(5)]
        player_cities = {
            str(i): {"id": city_id}
            for i, city_id in enumerate((227, 3142, 2864, 3189, 3160))
        }
        base = {"player_id": "one", "draws": 0, "army_lists": []}
        below = achievements.calculate_achievements(
            [{**base, "opponents": opponents[:4] + [opponents[0], {**opponents[4], "wins": 0}]}],
            {}, [], player_cities=player_cities,
        )[0]
        self.assertNotIn(name, below["achievements"])
        self.assertEqual(below["achievement_progress"][name], {"current": 4, "target": 5})

        unlocked = achievements.calculate_achievements(
            [{**base, "opponents": opponents}], {}, [], player_cities=player_cities,
        )[0]
        self.assertIn(name, unlocked["achievements"])
        self.assertEqual(unlocked["achievement_progress"][name], {"current": 5, "target": 5})

    def test_tricity_achievement_uses_tag_and_counts_distinct_defeats(self):
        name = "Drunken Sailor"
        opponents = [{"player_id": str(i), "wins": 1} for i in range(5)]
        player_cities = {
            str(i): {"id": city_id}
            for i, city_id in enumerate((234, 3117, 3118, 234, 3117))
        }
        player_cities.update({"other": {"id": 235}, "unknown": None})
        base = {"player_id": "one", "draws": 0, "army_lists": []}
        below = achievements.calculate_achievements(
            [{**base, "opponents": opponents[:4] + [
                opponents[0], {**opponents[4], "wins": 0},
                {"player_id": "other", "wins": 1}, {"player_id": "unknown", "wins": 1},
            ]}],
            {}, [], player_cities=player_cities,
        )[0]
        self.assertNotIn(name, below["achievements"])
        self.assertEqual(below["achievement_progress"][name], {"current": 4, "target": 5})
        unlocked = achievements.calculate_achievements(
            [{**base, "opponents": opponents}], {}, [], player_cities=player_cities,
        )[0]
        self.assertIn(name, unlocked["achievements"])
        self.assertEqual(unlocked["achievement_progress"][name], {"current": 5, "target": 5})

    def test_galicia_achievement_uses_place_tag_and_excludes_krakow(self):
        name = "Can Opener"
        opponents = [{"player_id": str(i), "wins": 1} for i in range(6)]
        player_cities = {
            str(i): {"id": city_id}
            for i, city_id in enumerate((3138, 3175, 252, 3137, 3143, 3184))
        }
        player_cities["krakow"] = {"id": 228}
        base = {"player_id": "one", "draws": 0, "army_lists": []}
        below = achievements.calculate_achievements(
            [{**base, "opponents": opponents[:4] + [
                opponents[0], {**opponents[4], "wins": 0}, {**opponents[5], "wins": 0},
                {"player_id": "krakow", "wins": 1},
            ]}],
            {}, [], player_cities=player_cities,
        )[0]
        self.assertNotIn(name, below["achievements"])
        self.assertEqual(below["achievement_progress"][name], {"current": 4, "target": 5})

        unlocked = achievements.calculate_achievements(
            [{**base, "opponents": opponents}], {}, [], player_cities=player_cities,
        )[0]
        self.assertIn(name, unlocked["achievements"])
        self.assertEqual(unlocked["achievement_progress"][name], {"current": 6, "target": 5})

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_silesia_achievement_text_renders_tag_tooltip(self, _asset_url):
        cards = _achievements_section([]).children[-1].children
        card = next(card for card in cards if card.children.children[1].children == "Age of Coal is Over")
        description = card.children.children[2].children
        self.assertEqual(description.children[1].children.children, "Silesia")
        self.assertEqual(description.children[1].children.className,
                         "tag-keyword achievement-tag-keyword")
        self.assertEqual(description.children[2], ".")
        self.assertIn("Silesia: Chorzów\nGliwice", card.to_plotly_json()["props"]["aria-label"])

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_can_opener_achievement_text_renders_galicia_tag(self, _asset_url):
        cards = _achievements_section([]).children[-1].children
        card = next(card for card in cards if card.children.children[1].children == "Can Opener")
        description = card.children.children[2].children
        self.assertEqual(description.children[1].children.children, "Galicia")
        self.assertIn(
            "Galicia: Dębica\nNowy Sącz\nRzeszów\nTarnów\nWieliczka\nŻywiec",
            card.to_plotly_json()["props"]["aria-label"],
        )

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_tricity_achievement_text_renders_tag_tooltip(self, _asset_url):
        cards = _achievements_section([]).children[-1].children
        card = next(card for card in cards if card.children.children[1].children == "Drunken Sailor")
        description = card.children.children[2].children
        self.assertEqual(description.children[1].children.children, "Trójmiasto")
        self.assertEqual(description.children[1].label.children[1].children[0].children, "Gdańsk")
        self.assertIn("Trójmiasto: Gdańsk\nGdynia", card.to_plotly_json()["props"]["aria-label"])

    def test_negotiator_requires_at_least_five_draws(self):
        negotiator = next(a for a in achievements.ACHIEVEMENTS if a.name == "Ah, Yes. The Negotiator")
        self.assertFalse(negotiator.condition({"draws": 4}, PlayerTournamentResults()))
        self.assertTrue(negotiator.condition({"draws": 5}, PlayerTournamentResults()))

    def test_trophy_and_army_specialty_achievement_thresholds(self):
        class Expertise:
            def for_player(self, player_id, _armies):
                places = {
                    "qualified": [1, *range(2, 11)],
                    "below_counts": range(2, 11),
                    "below_top_ten": [1] * 10,
                    "no_number_one": [2] * 10,
                }[player_id]
                return [{"place": place} for place in places]

        rankings = [
            {"player_id": f"top-{place}", "place": place}
            for place in range(1, 52)
        ]
        qualified = {
            "player_id": "qualified",
            "draws": 0,
            "opponents": [
                {"player_id": f"top-{place}", "wins": 1}
                for place in (1, 2, 3, *range(11, 19))
            ],
            "army_lists": [],
        }
        below_counts = {
            "player_id": "below_counts",
            "draws": 0,
            "opponents": [
                {"player_id": f"top-{place}", "wins": 1}
                for place in range(11, 20)
            ],
            "army_lists": [],
        }
        below_top_ten = {
            "player_id": "below_top_ten",
            "draws": 0,
            "opponents": [
                {"player_id": f"top-{place}", "wins": 1}
                for place in (1, 2, *range(11, 19))
            ],
            "army_lists": [],
        }
        no_number_one = {
            **qualified,
            "player_id": "no_number_one",
        }
        battles = [
            {"player_1_id": profile["player_id"], "player_2_id": opponent["player_id"],
             "result": [1, 0], "season": 2026}
            for profile in (qualified, below_counts, below_top_ten, no_number_one)
            for opponent in profile["opponents"]
        ]
        with patch.object(achievements, "ArmyExpertise", return_value=Expertise()):
            profiles = achievements.calculate_achievements(
                [qualified, below_counts, below_top_ten, no_number_one],
                {},
                [],
                main_ranking=rankings,
                battles=battles,
            )

        qualified_achievements = set(profiles[0]["achievements"])
        self.assertTrue({
            "Headhunter",
            "Beat the Unbeatable",
            "Jack of All Trades",
            "Master Tactician",
        }.issubset(qualified_achievements))
        below_count_achievements = set(profiles[1]["achievements"])
        self.assertNotIn("Headhunter", below_count_achievements)
        self.assertNotIn("Jack of All Trades", below_count_achievements)
        below_top_ten_achievements = set(profiles[2]["achievements"])
        self.assertIn("Headhunter", below_top_ten_achievements)
        self.assertNotIn("Beat the Unbeatable", below_top_ten_achievements)
        no_number_one_achievements = set(profiles[3]["achievements"])
        self.assertIn("Jack of All Trades", no_number_one_achievements)
        self.assertNotIn("Master Tactician", no_number_one_achievements)

    def test_recalculate_persists_counts_and_replaces_outdated_achievements(self):
        profile = {"player_id": "one", "displayName": "One", "draws": 10, "army_lists": [],
                   "opponents": [],
                   "achievements": ["outdated", "Man of Culture", "Białystok Challenger", "Lublin Challenger", "Border Control",
                                    "Meta Chaser", "No Fun Allowed"],
                   "achievement_progress": {
                       "Białystok Challenger": {"current": 5, "target": 5},
                       "Lublin Challenger": {"current": 5, "target": 5},
                       "Border Control": {"current": 5, "target": 5},
                       "Meta Chaser": {"current": 5, "target": 5},
                       "No Fun Allowed": {"current": 5, "target": 5},
                   },
                   "achievements_count": 99,
                   "other_data": "preserved"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "player_profiles.json"
            path.write_text(json.dumps([profile]), encoding="utf-8")
            with (patch.object(achievements, "DATA_DIRECTORY", directory),
                  patch("download_data.DATA_DIRECTORY", directory),
                  patch.object(achievements, "load_tournament_results", return_value={}),
                  patch.object(achievements, "load_tournaments", return_value=[]),
                  patch.object(achievements, "load_main_ranking", return_value=[]),
                  patch.object(achievements, "load_main_ranking_2027", return_value=[]),
                  patch.object(achievements, "load_battles", return_value=[]),
                  patch.object(achievements, "load_armies", return_value=[]),
                  patch.object(achievements, "load_player_cities", return_value={})):
                calculated = achievements.recalculate_achievements()
                saved = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(saved, calculated)
                self.assertEqual(achievements.recalculate_achievements(), saved)
        self.assertEqual(saved[0]["achievements"], ["Ah, Yes. The Negotiator"])
        self.assertEqual(saved[0]["achievements_count"], 2)
        self.assertNotIn("Białystok Challenger", saved[0]["achievement_progress"])
        self.assertNotIn("Lublin Challenger", saved[0]["achievement_progress"])
        self.assertNotIn("Border Control", saved[0]["achievement_progress"])
        self.assertNotIn("Meta Chaser", saved[0]["achievement_progress"])
        self.assertNotIn("No Fun Allowed", saved[0]["achievement_progress"])
        self.assertEqual(saved[0]["achievement_progress"]["Ah, Yes. The Negotiator"],
                         {"current": 10, "target": 15, "stage": 2})
        self.assertEqual(saved[0]["other_data"], "preserved")

    @patch("dash.get_asset_url", side_effect=lambda path: "/assets/" + path)
    def test_missing_achievements_are_shown_as_unavailable(self, _asset_url):
        section = _achievements_section(None)
        self.assertIn("not been calculated", section.children[0].children)
        self.assertIn("unavailable", section.children[1].children[0].to_plotly_json()["props"]["aria-label"])

    def test_views_display_stored_achievement_counts(self):
        first = {"player_id": "one", "displayName": "One", "games_played": 5, "wins": 2,
                 "draws": 0, "losses": 3, "winrate": 40, "army_lists": [], "achievements_count": 3,
                 "opponents": [{"player_id": "top", "wins": 1}], "locations_count": 5}
        second = {**first, "player_id": "two", "displayName": "Two", "achievements_count": 1, "locations_count": 2}
        profiles = {"one": first, "two": second}
        trophy_data = {"one": {2026: [{"player_id": "top", "main_ranking_place": 4}]}}
        with (patch.object(profile_page, "profile_by_id", profiles),
              patch.object(profile_page, "main_place_by_id", {"top": 4}),
              patch.object(profile_page, "trophies_by_player", trophy_data),
              patch.object(profile_page, "master_place_by_name", {"One": 7}),
              patch.object(profile_page, "online_place_by_id", {"one": 2}),
              patch.object(profile_page.army_expertise, "for_player", return_value=[{}, {}])):
            scroll_area = profile_page.build_top("one").children[1]
            grid = scroll_area.children
            self.assertEqual(grid.cols, 6)
            self.assertEqual(scroll_area.scrollbars, "x")
            self.assertEqual(len(grid.children), 12)
            self.assertTrue(all(text.ta == "center" for card in grid.children for text in card.children.children))
            self.assertTrue(all(card.children.children[0].size == "md" and
                                card.children.children[1].size == "1.75rem" for card in grid.children))
            self.assertEqual([card.children.children[1].children for card in grid.children[:3]], ["-", "7", "2"])
            unranked = profile_page.build_top("two").children[1].children.children
            self.assertEqual([card.children.children[1].children for card in unranked[:3]], ["-", "-", "-"])
            self.assertEqual(
                [(card.children.children[0].children, card.children.children[1].children)
                 for card in grid.children],
                [("Main ranking place", "-"), ("Master ranking place", "7"), ("Online ranking place", "2"),
                 ("Tournament locations", "5"), ("Games played", "5"), ("Winrate", "40%"),
                 ("Wins", "2"), ("Draws", "0"), ("Losses", "3"), ("Player trophies", "1"),
                 ("Army specialties", "2"), ("Achievements unlocked", achievements.format_achievement_count(3))],
            )
        second["opponents"] = []
        with (patch.object(comparison_page, "profile_by_id", profiles),
              patch.object(comparison_page, "main_place_by_id", {"top": 4}),
              patch.object(comparison_page, "trophies_by_player", trophy_data),
              patch.object(comparison_page.army_expertise, "for_player", side_effect=[[{}, {}], []]),
              patch.object(comparison_page, "_history", return_value=None)):
            comparison = comparison_page.update_comparison("one", "two")
        rows = comparison.children[0].children.children[1].children
        self.assertEqual([[cell.children for cell in row.children[:3]] for row in rows[-4:]],
                         [["Tournament locations", "5", "2"], ["Player trophies", "1", "0"], ["Army specialties", "2", "0"],
                          ["Achievements unlocked", achievements.format_achievement_count(3),
                           achievements.format_achievement_count(1)]])
        self.assertTrue(all(row.children[1].style == comparison_page.HIGHLIGHT for row in rows[-4:]))
        total = achievements.total_achievement_stages(achievements.ACHIEVEMENTS)
        self.assertEqual(achievements.format_achievement_count(0), f"Leaf (0/{total} 0.0%)")
        self.assertEqual(achievements.format_achievement_count(total), f"Mithril ({total}/{total} 100.0%)")
        self.assertEqual(achievements.format_achievement_count(None), "-")
        del second["achievements_count"]
        with (patch.object(profile_page, "profile_by_id", profiles),
              patch.object(profile_page.army_expertise, "for_player", return_value=[])):
            self.assertEqual(profile_page.build_top("two").children[1].children.children[-1]
                             .children.children[1].children, "-")
        with (patch.object(comparison_page, "profile_by_id", profiles),
              patch.object(comparison_page.army_expertise, "for_player", return_value=[]),
              patch.object(comparison_page, "_history", return_value=None)):
            row = comparison_page.update_comparison("one", "two").children[0].children.children[1].children[-1]
        self.assertEqual([cell.children for cell in row.children[:3]],
                         ["Achievements unlocked", achievements.format_achievement_count(3), "-"])
        self.assertEqual(row.children[1].style, comparison_page.HIGHLIGHT)

    def test_download_refresh_saves_calculated_achievements(self):
        profile = {"player_id": "one", "displayName": "One", "draws": 10, "army_lists": [], "opponents": []}
        event = {"id": "event", "name": "Event", "date": "2026-01-01", "tournament_type": "LOKAL",
                 "city": {"id": 1, "name": "Town", "country": "PL"}}
        submissions = {"event": {"people": [{
            "user": {"id": "one", "city": {"id": 2, "name": "Home", "country": "PL"}},
            "finalResult": {"place": 2},
        }]}}
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "battles.json").write_text("[]", encoding="utf-8")
            with (patch.object(download_data, "DATA_DIRECTORY", directory),
                  patch.object(download_data, "load_metadata", return_value={"time": None}),
                  patch.object(download_data, "save_metadata"),
                  patch.object(download_data, "get_main_ranking_data", return_value=[]),
                  patch.object(download_data, "build_2027_rankings", return_value={
                      "main": [], "master": [], "online": [],
                  }),
                  patch.object(download_data, "get_online_ranking_data", return_value=[]),
                  patch.object(download_data, "get_finished_events", return_value=[]),
                  patch.object(download_data, "get_polish_events", return_value=[event]),
                  patch.object(download_data, "download_master_tournaments_data", return_value=[]),
                  patch.object(download_data, "get_master_ranking_data", return_value=[]),
                  patch.object(download_data, "download_tournament_battles_data", return_value=submissions),
                  patch.object(download_data, "parse_and_store_battles"),
                  patch.object(download_data, "extract_armies_data", return_value=[]),
                  patch.object(download_data, "build_player_profiles", return_value=[profile]),
                  patch("store.load_tournament_results", return_value={})):
                download_data.download_data(force=True)
            saved = json.loads((Path(directory) / "player_profiles.json").read_text(encoding="utf-8"))
            tournaments = json.loads((Path(directory) / "tournaments.json").read_text(encoding="utf-8"))
            cities = json.loads((Path(directory) / "player_cities.json").read_text(encoding="utf-8"))
            self.assertEqual(tournaments[0]["city"]["name"], "Town")
            self.assertEqual(tournaments[0]["player_ids"], ["one"])
            self.assertEqual(cities["one"], {"id": 2, "name": "Home", "country": "PL"})
        self.assertEqual(saved[0]["achievements"], ["Ah, Yes. The Negotiator"])
        self.assertEqual(saved[0]["achievements_count"], 2)


if __name__ == "__main__":
    unittest.main()

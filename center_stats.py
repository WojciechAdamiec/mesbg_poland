import json
from datetime import date
from functools import lru_cache
from pathlib import Path

from battle_parser import CSV_FILE, JSON_FILE, tournament_input_id
from center_mapping import center_for_city, center_for_ranked_player, load_center_mapping
from download_data import SEASON_2027_START, START_DATE, _winrate
from store import (
    load_armies, load_battles, load_main_ranking, load_main_ranking_2027,
    load_player_cities, load_tournaments,
)


ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "input"
TOP_LIMITS = (10, 30, 50, 100, 200, 1000)


def event_season(event):
    event_date = date.fromisoformat(event["date"])
    if event_date >= SEASON_2027_START:
        return 2027
    if event_date >= START_DATE:
        return 2026
    return None


def hosted_event_counts(events):
    counts = {2026: 0, 2027: 0}
    for event in events:
        season = event_season(event)
        if season is not None:
            counts[season] += 1
    return counts


def load_placements(tournaments, input_path=INPUT_PATH):
    """Load individual and team podium placements for Master and Challenger events."""
    events = {
        event["tournament_id"]: event for event in tournaments
        if event.get("tournament_type") in ("MASTER", "DMP", "CHALLENGER")
    }
    submissions = {}
    if input_path.is_dir():
        for path in input_path.glob(f"*/{JSON_FILE}"):
            tournament_id = tournament_input_id(str(path), str(path.parent / CSV_FILE))
            if tournament_id in events:
                with path.open(encoding="utf-8") as file:
                    submissions[tournament_id] = json.load(file)
    placements = []
    incomplete = 0
    for tournament_id, submission in submissions.items():
        event = events[tournament_id]
        people = submission.get("people")
        teams = submission.get("teams") or []
        if not isinstance(people, list):
            incomplete += 1
            continue

        def player_details(person):
            player = person.get("user") or {}
            if player.get("id"):
                return {
                    "player_id": player["id"],
                    "name": player.get("displayName") or player["id"],
                }
            return None

        def add_placement(place, players, team_name=None):
            placements.append({
                "players": players, "place": place, "event": event["name"],
                "date": event["date"],
                "type": "MASTER" if event["tournament_type"] == "DMP" else event["tournament_type"],
                "team_name": team_name,
            })

        if teams:
            if not any((team.get("finalResult") or {}).get("place") for team in teams):
                incomplete += 1
                continue
            missing_members = False
            for team in teams:
                place = (team.get("finalResult") or {}).get("place")
                if not isinstance(place, int) or not 1 <= place <= 3:
                    continue
                players = []
                seen = set()
                for person in people:
                    if person.get("teamId") != team.get("id"):
                        continue
                    player = player_details(person)
                    if player and player["player_id"] not in seen:
                        players.append(player)
                        seen.add(player["player_id"])
                if players:
                    add_placement(place, players, team.get("name"))
                else:
                    missing_members = True
            if missing_members:
                incomplete += 1
        else:
            if any(person.get("teamId") for person in people) or not any(
                (person.get("finalResult") or {}).get("place") for person in people
            ):
                incomplete += 1
                continue
            for person in people:
                place = (person.get("finalResult") or {}).get("place")
                player = player_details(person)
                if player and isinstance(place, int) and 1 <= place <= 3:
                    add_placement(place, [player])
    return placements, len(events) - len(submissions) + incomplete


def build_center_stats(centers, city_to_center, player_cities, ranking, tournaments, battles, placements, armies,
                       ranking_2027):
    stats = {
        center: {"ranking": [], "ranking_2027": [], "events": [], "trophies": [], "armies": {},
                 "distribution": {limit: 0 for limit in TOP_LIMITS},
                 "distribution_2027": {limit: 0 for limit in TOP_LIMITS}}
        for center in centers
    }
    player_centers = {
        player_id: center_for_city(city, city_to_center)
        for player_id, city in player_cities.items()
    }
    for ranking_key, rows in (("ranking", ranking), ("ranking_2027", ranking_2027)):
        for row in rows:
            player_id = row.get("player_id")
            center = center_for_ranked_player(row, player_cities, city_to_center)
            if center not in stats:
                continue
            stats[center][ranking_key].append(row)
            place = row.get("place")
            if isinstance(place, int) and place > 0:
                distribution_key = "distribution" if ranking_key == "ranking" else "distribution_2027"
                for limit in TOP_LIMITS:
                    if place <= limit:
                        stats[center][distribution_key][limit] += 1
    for data in stats.values():
        for ranking_key in ("ranking", "ranking_2027"):
            data[ranking_key].sort(key=lambda row: (row.get("place") is None, row.get("place") or 0))

    event_centers = {}
    for event in tournaments:
        if event.get("tournament_type") == "ONLINE":
            continue
        center = center_for_city(event.get("city"), city_to_center)
        if center in stats:
            stats[center]["events"].append(event)
            event_centers[event["tournament_id"]] = center
    for data in stats.values():
        data["events"].sort(key=lambda event: event.get("date") or "", reverse=True)

    for trophy in placements:
        represented_centers = {
            player_centers.get(player["player_id"]) for player in trophy["players"]
        }
        for center in represented_centers:
            if center in stats:
                stats[center]["trophies"].append(trophy)
    for data in stats.values():
        data["trophies"].sort(key=lambda item: item.get("date") or "", reverse=True)

    faction_by_army = {army["army_id"]: army.get("faction") for army in armies}
    for battle in battles:
        center = event_centers.get(battle.get("tournament_id"))
        result = battle.get("result")
        if center is None or battle.get("format") == "DOUBLES" or not result or len(result) != 2:
            continue
        for index in (0, 1):
            army_id = battle.get(f"army_{index + 1}_id")
            if army_id is None:
                continue
            army = stats[center]["armies"].setdefault(army_id, {
                "name": battle.get(f"army_{index + 1}_name") or "Unknown",
                "faction": {"GOOD": "Good", "EVIL": "Evil"}.get(faction_by_army.get(army_id)),
                "games": 0, "wins": 0, "draws": 0,
            })
            army["games"] += 1
            if result[index] > result[1 - index]:
                army["wins"] += 1
            elif result[index] == result[1 - index]:
                army["draws"] += 1
    for data in stats.values():
        armies = data["armies"].values()
        total_picks = sum(army["games"] for army in armies)
        for army in armies:
            army["winrate"] = _winrate(army["wins"], army["games"], army["draws"])
            army["pickrate"] = round(army["games"] * 100 / total_picks, 2)
        data["armies"] = sorted(armies, key=lambda army: (-army["games"], army["name"].casefold()))
    return stats


@lru_cache(maxsize=1)
def load_center_stats():
    centers, city_to_center = load_center_mapping()
    tournaments = load_tournaments()
    placements, missing_results = load_placements(tournaments)
    return build_center_stats(
        centers, city_to_center, load_player_cities(), load_main_ranking(),
        tournaments, load_battles(), placements, load_armies(), load_main_ranking_2027(),
    ), missing_results

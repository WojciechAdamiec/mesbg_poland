import pandas as pd
import requests
import copy
import csv
import datetime
import json
import os
from rich import print

from patches import select_patch
from battle_parser import (
    CSV_FILE,
    JSON_FILE,
    SCENARIOS_FILE,
    import_battles,
    tournament_input_id,
)
from db import BattleDB
from ranking_rules.scoring import (
    CHALLENGER,
    LOCAL,
    MASTER_INDIVIDUAL,
    MASTER_PAIRS_2027,
    ONLINE_INDIVIDUAL_2027,
    ONLINE_TEAM_2027,
)


START_DATE = datetime.datetime.strptime("05-12-2025", "%d-%m-%Y").date()
END_DATE = datetime.datetime.strptime("30-11-2050", "%d-%m-%Y").date()
SEASON_2027_START = datetime.date(2026, 11, 24)
TOURNAMENT_REFRESH_WINDOW = datetime.timedelta(days=7)


DATA_DIRECTORY = "data"
METADATA_FILE = "metadata.json"
MAIN_RANKING_FILE = "main_ranking.json"
MAIN_RANKING_2027_FILE = "main_ranking_2027.json"
ONLINE_RANKING_FILE = "online_ranking.json"
MASTER_RANKING_FILE = "master_ranking.json"
MASTER_RANKING_2027_FILE = "master_ranking_2027.json"
MASTER_TOURNAMENTS_FILE = "master_tournaments.json"
ONLINE_RANKING_2027_FILE = "online_ranking_2027.json"
BATTLES_FILE = "battles.json"
ARMIES_FILE = "armies.json"
PLAYER_PROFILES_FILE = "player_profiles.json"
TOURNAMENTS_FILE = "tournaments.json"
PLAYER_CITIES_FILE = "player_cities.json"
ACCESS_TOKEN = "PASTER_TOKEN_HERE"
INPUT_DIRECTORY = "input"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "game-system": "mesbg",
}
cookies = {"access_token": ACCESS_TOKEN}


def transform_ranking_data(raw_data):
    transformed = []
    
    for user in raw_data:
        user_data = get_user_tournaments(user.get("id"))
        user_tournament_data = parse_user_tournament_data(user_data)
        player = user.get("user") or {}

        simplified_entry = {
            "place": user.get("place"),
            "score": user.get("score"),
            "player_id": player.get("id"),
            "displayName": player.get("displayName"),
            "city_name": (player.get("city") or {}).get("name"),
            "city_id": (player.get("city") or {}).get("id"),
            "city_country": (player.get("city") or {}).get("country"),
            "discord_linked": bool(player.get("discordUsername")),
        }
        data_to_display = copy.copy(simplified_entry)
        data_to_display.update(user_tournament_data)
        transformed.append(data_to_display)
    
    return transformed


def transform_master_ranking_data(raw_data, master_tournaments_data, main_ranking_json):
    user_master_results = {}
    user_main_score = {user.get("player_id"): user.get("score") for user in main_ranking_json}

    for user in raw_data:
        user_master_results[(user.get("user") or {}).get("id")] = []

    for tournament in master_tournaments_data:
        tournament_date = datetime.date.fromisoformat(tournament["master_date"])
        if not START_DATE <= tournament_date < SEASON_2027_START:
            continue
        for person in tournament.get("people", []):
            user_id = (person.get("user") or {}).get("id")
            result = person.get("result")
            if user_id in user_master_results:
                user_master_results[user_id].append(result)

    for user, results in user_master_results.items():
        results.sort()

    transformed = []

    for user in raw_data:
        user_id = (user.get("user") or {}).get("id")
        results = user_master_results[user_id]
        if len(results) < 3:
            continue
        score = sum(results[:3])
        tie_breaker = user_main_score.get(user_id, 0)
        simplified_entry = {
            "place": None,
            "score": score,
            "tie_breaker": tie_breaker,
            "displayName": (user.get("user") or {}).get("displayName"),
            "city_name": ((user.get("user") or {}).get("city") or {}).get("name"),
            "top_2": sum(results[:2]),
            "master_1": results[0],
            "master_2": results[1],
            "master_3": results[2],
        }
        data_to_display = copy.copy(simplified_entry)
        transformed.append(data_to_display)

    transformed.sort(key=lambda entry: (entry["score"], -entry["tie_breaker"]))

    prev_entry = None
    for index, entry in enumerate(transformed):
        if prev_entry is not None and entry["score"] == prev_entry["score"] and entry["tie_breaker"] == prev_entry["tie_breaker"]:
            entry["place"] = prev_entry["place"]
        else:
            entry["place"] = index + 1
        prev_entry = entry

    return transformed


def transform_online_ranking_data(raw_data):
    transformed = []
    
    for user in raw_data:
        user_data = get_user_online_tournaments(user.get("id"))
        user_tournament_data = parse_user_online_tournament_data(user_data)
        player = user.get("user") or {}

        simplified_entry = {
            "place": user.get("place"),
            "score": user.get("score"),
            "player_id": player.get("id"),
            "displayName": player.get("displayName"),
            "city_name": (player.get("city") or {}).get("name"),
            "city_id": (player.get("city") or {}).get("id"),
            "city_country": (player.get("city") or {}).get("country"),
            "discord_linked": bool(player.get("discordUsername")),
        }
        data_to_display = copy.copy(simplified_entry)
        data_to_display.update(user_tournament_data)
        transformed.append(data_to_display)

    return transformed


def get_user_tournaments(user_id):
    url_user_tournaments = f"https://api.championshub.app/api/ranking/user/mesbg-pl/{user_id}?season=28"
    res_user_tournaments = requests.get(url_user_tournaments, headers=headers, cookies=cookies, timeout=15)
    return res_user_tournaments.json()

def get_user_online_tournaments(user_id):
    url_user_tournaments = f"https://api.championshub.app/api/ranking/user/mesbg-pl-online/{user_id}?season=30"
    res_user_tournaments = requests.get(url_user_tournaments, headers=headers, cookies=cookies, timeout=15)
    return res_user_tournaments.json()


def get_main_ranking_data():
    print("Downloading main ranking data from Champions Hub API...")
    url_details = f"https://api.championshub.app/api/ranking/results/mesbg-pl?season=28&cityId=PL/"
    res_details = requests.get(url_details, headers=headers, cookies=cookies, timeout=15)
    res_json = res_details.json()
    res_json = transform_ranking_data(res_json)
    return res_json


def _place_value(raw_place):
    if raw_place is None or isinstance(raw_place, bool):
        return None
    try:
        place = int(raw_place)
    except (TypeError, ValueError):
        return None
    return place if place > 0 else None


def _points_for_place(scoring, place):
    if place is None:
        return None
    points = scoring[1]
    return points[min(place - 1, len(points) - 1)]


def _rank_by_score(entries, tie_breaker=False):
    entries.sort(key=lambda entry: (
        -entry["score"],
        -entry.get("tie_breaker", 0) if tie_breaker else 0,
        (entry.get("displayName") or "").casefold(),
        str(entry["player_id"]),
    ))
    previous_key = None
    previous_place = None
    for index, entry in enumerate(entries):
        rank_key = (entry["score"], entry.get("tie_breaker", 0) if tie_breaker else None)
        if rank_key != previous_key:
            previous_place = index + 1
            previous_key = rank_key
        entry["place"] = previous_place
    return entries


def build_2027_rankings(polish_events, submissions_by_id):
    """Build 2027 rankings from season-scoped tournament placements and published rules."""
    players = {}

    def event_date(event):
        value = event["date"]
        return datetime.date.fromisoformat(value) if isinstance(value, str) else value

    def get_player(user):
        user_id = user.get("id")
        if not user_id:
            return None
        player = players.setdefault(user_id, {
            "player_id": user_id,
            "displayName": user.get("displayName"),
            "city_id": None,
            "city_name": None,
            "city_country": None,
            "discord_linked": False,
            "main_results": [],
            "master_results": [],
            "local_results": [],
            "online_results": [],
        })
        city = user.get("city") or {}
        if city:
            player.update({
                "city_id": city.get("id"),
                "city_name": city.get("name"),
                "city_country": city.get("country"),
            })
        player["displayName"] = user.get("displayName") or player["displayName"]
        player["discord_linked"] = player["discord_linked"] or bool(user.get("discordUsername"))
        return player

    for event in sorted(polish_events, key=event_date):
        if event_date(event) < SEASON_2027_START:
            continue

        submission = submissions_by_id.get(event["id"])
        if not submission:
            continue
        tournament_type = (event.get("tournament_type") or "").upper()
        people = submission.get("people", [])
        teams = submission.get("teams") or []
        is_team_event = bool(teams) or any(person.get("teamId") for person in people)
        team_places = {
            team.get("id"): _place_value((team.get("finalResult") or {}).get("place"))
            for team in teams
            if team.get("id")
        }

        for person in people:
            user = person.get("user") or {}
            player = get_player(user)
            if player is None:
                continue

            if tournament_type == "DMP":
                player["main_results"].append(30)
                continue

            place = team_places.get(person.get("teamId")) or _place_value(
                (person.get("finalResult") or {}).get("place")
            )
            if place is None:
                continue

            if tournament_type == "LOKAL":
                points = _points_for_place(LOCAL, place)
                player["local_results"].append(points)
            elif tournament_type == "CHALLENGER":
                points = _points_for_place(CHALLENGER, place)
                player["main_results"].append(points)
                player["master_results"].append(points)
            elif tournament_type == "MASTER":
                scoring = MASTER_PAIRS_2027 if is_team_event else MASTER_INDIVIDUAL
                points = _points_for_place(scoring, place)
                player["main_results"].append(points)
                player["master_results"].append(points)
            elif tournament_type == "ONLINE":
                scoring = ONLINE_TEAM_2027 if is_team_event else ONLINE_INDIVIDUAL_2027
                player["online_results"].append(_points_for_place(scoring, place))

    main_ranking = []
    master_ranking = []
    online_ranking = []

    for player in players.values():
        main_results = sorted(player["main_results"], reverse=True)[:6]
        local_results = sorted(player["local_results"], reverse=True)[:6]
        main_results.extend([0] * (6 - len(main_results)))
        local_results.extend([0] * (6 - len(local_results)))
        if any(main_results) or any(local_results):
            master_total = sum(main_results)
            local_total = sum(local_results)
            main_ranking.append({
                **{key: player[key] for key in ("player_id", "displayName", "city_id", "city_name",
                                                  "city_country", "discord_linked")},
                "master_challenger_total": master_total,
                **{f"master_challenger_{i}": score for i, score in enumerate(main_results, 1)},
                "local_total": local_total,
                **{f"local_{i}": score for i, score in enumerate(local_results, 1)},
                "score": master_total + local_total,
            })

        master_results = sorted(player["master_results"], reverse=True)[:3]
        master_results.extend([0] * (3 - len(master_results)))
        if any(master_results):
            master_ranking.append({
                **{key: player[key] for key in ("player_id", "displayName", "city_id", "city_name",
                                                  "city_country", "discord_linked")},
                "score": sum(master_results),
                "tie_breaker": 0,
                "top_2": sum(master_results[:2]),
                **{f"master_{i}": score for i, score in enumerate(master_results, 1)},
            })

        online_results = sorted(player["online_results"], reverse=True)[:5]
        online_results.extend([0] * (5 - len(online_results)))
        if any(online_results):
            online_ranking.append({
                **{key: player[key] for key in ("player_id", "displayName", "city_id", "city_name",
                                                  "city_country", "discord_linked")},
                "score": sum(online_results),
                **{f"online_{i}": score for i, score in enumerate(online_results, 1)},
            })

    main_ranking = _rank_by_score(main_ranking)
    main_scores = {player["player_id"]: player["score"] for player in main_ranking}
    for player in master_ranking:
        player["tie_breaker"] = main_scores.get(player["player_id"], 0)
    return {
        "main": main_ranking,
        "master": _rank_by_score(master_ranking, tie_breaker=True),
        "online": _rank_by_score(online_ranking),
    }


def get_online_ranking_data():
    print("Downloading online ranking data from Champions Hub API...")
    url_details = f"https://api.championshub.app/api/ranking/results/mesbg-pl-online?season=30&cityId=PL/"
    res_details = requests.get(url_details, headers=headers, cookies=cookies, timeout=15)
    res_json = res_details.json()
    res_json = transform_online_ranking_data(res_json)
    return res_json


def get_master_ranking_data(master_tournaments_data, main_ranking_json):
    print("Downloading master ranking data from Champions Hub API...")
    url_details = f"https://api.championshub.app/api/ranking/results/mesbg-pl/variant/kadra?season=28&cityId=PL/"
    res_details = requests.get(url_details, headers=headers, cookies=cookies, timeout=15)
    res_json = res_details.json()
    res_json = transform_master_ranking_data(res_json, master_tournaments_data, main_ranking_json)
    return res_json


def parse_user_tournament_data(user_tournaments):
    master_values = []
    local_values = []
    challenger_values = []

    for tournament in user_tournaments:
        tournament_type = (tournament.get("rankingEventType") or {}).get("name", "").upper()
        score = tournament.get("rankingResult")
        if tournament_type == "MASTER":
            master_values.append(score)
        elif tournament_type == "DMP":
            master_values.append(30)
        elif tournament_type == "LOKAL":
            local_values.append(score)
        elif tournament_type == "CHALLENGER":
            challenger_values.append(score)

    challenger_values.sort(reverse=True)
    if challenger_values:
        highest = challenger_values[0]
        local_values.append(highest)

    master_values.sort(reverse=True)
    local_values.sort(reverse=True)

    master_tournaments = [0, 0, 0, 0, 0]
    for i in range(5):
        if i < len(master_values):
            master_tournaments[i] = master_values[i]
        else:
            break

    local_tournaments = [0, 0, 0, 0, 0]
    for i in range(5):
        if i < len(local_values):
            local_tournaments[i] = local_values[i]
        else:
            break

    return {
        "master_total": sum(master_tournaments),
        "master_1": master_tournaments[0],
        "master_2": master_tournaments[1],
        "master_3": master_tournaments[2],
        "master_4": master_tournaments[3],
        "master_5": master_tournaments[4],
        "local_total": sum(local_tournaments),
        "local_1": local_tournaments[0],
        "local_2": local_tournaments[1],
        "local_3": local_tournaments[2],
        "local_4": local_tournaments[3],
        "local_5": local_tournaments[4],
    }


def parse_user_online_tournament_data(user_tournaments):
    online_values = []

    for tournament in user_tournaments:
        tournament_type = tournament.get("rankingEventType", {}).get("name", "")
        if tournament_type == "ONLINE":
            score = tournament.get("rankingResult")
            online_values.append(score)

    online_values.sort(reverse=True)

    online_tournaments = [0, 0, 0, 0, 0]
    for i in range(5):
        if i < len(online_values):
            online_tournaments[i] = online_values[i]
        else:
            break

    return {
        "online_total": sum(online_tournaments),
        "online_1": online_tournaments[0],
        "online_2": online_tournaments[1],
        "online_3": online_tournaments[2],
        "online_4": online_tournaments[3],
        "online_5": online_tournaments[4],
    }


def get_finished_events():
    print("Downloading finished events list from Champions Hub API...")
    all_events_raw = []
    skip = 0
    while True:
        payload = {"ranking": None, "statuses": ["FINISHED"], "take": 100, "skip": skip}
        r = requests.post(
            "https://api.championshub.app/api/event-management/list",
            headers=headers,
            cookies=cookies,
            json=payload,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()["data"]
        if not data:
            break
        all_events_raw.extend(data)
        if len(data) < 100:
            break
        skip += 100
    return all_events_raw


def get_polish_events(all_events_raw):
    target_events = []
    for ev in all_events_raw:
        city_data = ev.get("city") or {}
        raw_start = ev.get("startsAt")
        t_points = ev.get("pointsLimit")
        if raw_start and city_data.get("country") == "PL":
            corrected_date = pd.to_datetime(raw_start, utc=True).tz_convert("Europe/Warsaw").date()
            if START_DATE <= corrected_date <= END_DATE:
                t_id = ev.get("id")
                t_name = ev.get("name")
                ranking_event_type = ev.get("rankingEventType")
                tournament_type = ranking_event_type.get("name").upper() if ranking_event_type else None
                if tournament_type not in {"LOKAL", "CHALLENGER", "MASTER", "DMP", "ONLINE"}:
                    continue
                target_events.append({
                    "id": t_id,
                    "name": t_name,
                    "date": corrected_date,
                    "ends_at": ev.get("endsAt"),
                    "points": t_points,
                    "tournament_type": tournament_type,
                    "city": {"id": city_data.get("id"), "name": city_data.get("name"),
                             "country": city_data.get("country")},
                })
    return target_events


def download_master_tournaments_data(polish_events=None, submissions_by_id=None):
    print("Downloading masters data from Champions Hub API...")
    if polish_events is None:
        all_events = get_finished_events()
        polish_events = get_polish_events(all_events)

    master_events = [ev for ev in polish_events if ev.get("tournament_type") == "MASTER"]
    master_tournaments_data = []

    for master in master_events:
        master_id = master["id"]
        master_name = master["name"]
        master_date = master["date"]
        master_points = master["points"]
        url_details = f"https://api.championshub.app/api/submission/{master_id}"
        try:
            res_json = (submissions_by_id or {}).get(master_id)
            if res_json is None:
                res_details = requests.get(url_details, headers=headers, cookies=cookies, timeout=15)
                if res_details.status_code != 200:
                    print(f"Error downloading master tournament {master_name} ({master_id}): HTTP {res_details.status_code}")
                    continue
                res_json = res_details.json()
            people = res_json.get("people", [])
            people_data = []
            for person in people:
                user = person.get("user", {})
                result = (person.get("finalResult") or {}).get("place")
                if result:
                    people_data.append({
                        "user": user,
                        "result": result
                    })

            master_tournaments_data.append({
                "master_id": master_id,
                "master_name": master_name,
                "master_date": str(master_date),
                "master_points": master_points,
                "people": people_data
            })
        except Exception as e:
            print(f"Error downloading master tournament {master_name} ({master_id}): {e}")

    return master_tournaments_data


def load_cached_tournament(ev, directory):
    raw_end = ev.get("ends_at")
    if not raw_end:
        return None
    try:
        if not isinstance(raw_end, str):
            raise ValueError("expected an ISO date string")
        end = datetime.datetime.fromisoformat(raw_end.replace("Z", "+00:00"))
        if end.tzinfo is None:
            raise ValueError("missing timezone")
    except (TypeError, ValueError) as e:
        print(f"Invalid end date for {ev['name']} ({ev['id']}): {e}; downloading again")
        return None
    if datetime.datetime.now(datetime.timezone.utc) - end <= TOURNAMENT_REFRESH_WINDOW:
        return None

    submission_path = os.path.join(directory, JSON_FILE)
    csv_path = os.path.join(directory, CSV_FILE)
    if not os.path.isfile(submission_path) or not os.path.isfile(csv_path):
        return None
    if any(os.path.getmtime(path) < end.timestamp() for path in (submission_path, csv_path)):
        return None
    try:
        with open(submission_path, encoding="utf-8") as f:
            submission = json.load(f)
        if not isinstance(submission, dict) or not isinstance(submission.get("people"), list):
            raise ValueError("invalid submission data")
        with open(csv_path, encoding="utf-8", newline="") as f:
            rows = csv.DictReader(f)
            if not rows.fieldnames and submission.get("tournament_id") == ev["id"]:
                return submission
            if not rows.fieldnames or "Tournament ID" not in rows.fieldnames:
                raise ValueError("missing tournament ID column")
            ids = {row["Tournament ID"] for row in rows}
        if ids != {str(ev["id"])}:
            raise ValueError("missing or mismatched tournament ID")
        return submission
    except (OSError, UnicodeError, json.JSONDecodeError, csv.Error, ValueError) as e:
        print(f"Cannot use cached data for {ev['name']} ({ev['id']}): {e}; downloading again")
        return None


def download_tournament_battles_data(polish_events=None):
    print("Downloading tournament battles data from Champions Hub API...")
    if polish_events is None:
        all_events = get_finished_events()
        polish_events = get_polish_events(all_events)

    submissions_by_id = {}
    for ev in polish_events:
        t_id = ev["id"]
        t_name = ev["name"]
        t_date = ev["date"]
        t_points = ev["points"]
        tournament_type = ev["tournament_type"]
        season = 2027 if t_date >= SEASON_2027_START else 2026

        folder_name = "".join(x for x in t_name if x.isalnum())
        t_directory = os.path.join(INPUT_DIRECTORY, folder_name)
        cached_submission = load_cached_tournament(ev, t_directory)
        if cached_submission is not None:
            patch_obj = select_patch(t_date)
            metadata = {
                "points": t_points,
                "patch": patch_obj.name if patch_obj else None,
                "tournament_type": tournament_type,
                "season": season,
            }
            if any(cached_submission.get(key) != value for key, value in metadata.items()):
                cached_submission.update(metadata)
                with open(os.path.join(t_directory, JSON_FILE), "w", encoding="utf-8") as f:
                    json.dump(cached_submission, f, indent=4)
            submissions_by_id[t_id] = cached_submission
            print(f"Using cached data for event: {t_name}")
            continue

        print(f"Downloading battles for event: {t_name}")
        os.makedirs(t_directory, exist_ok=True)

        url_rounds_list = f"https://api.championshub.app/api/round/{t_id}"
        all_pairings_flat = []
        rounds_complete = False
        try:
            res_rounds = requests.get(url_rounds_list, headers=headers, cookies=cookies, timeout=15)
            if res_rounds.status_code == 200:
                rounds_list = res_rounds.json().get("rounds", [])
                rounds_complete = True
                for rd in rounds_list:
                    r_id = rd.get("id")
                    r_title = rd.get("title") or rd.get("name")
                    url_details = f"https://api.championshub.app/api/round/{t_id}/{r_id}"
                    res_details = requests.get(url_details, headers=headers, cookies=cookies, timeout=15)
                    if res_details.status_code != 200:
                        print(f"Error fetching round {r_id} for {t_name} ({t_id}): HTTP {res_details.status_code}")
                        rounds_complete = False
                        continue
                    round_data = res_details.json()
                    pairings = round_data.get("pairings", [])
                    for p in pairings:
                        u1 = p.get("pairingUser1") or {}
                        u2 = p.get("pairingUser2") or {}
                        row = {
                            "Tournament Name": t_name,
                            "Tournament ID": t_id,
                            "Round Title": r_title,
                            "Round ID": r_id,
                            "Round Status": round_data.get("status"),
                            "Table ID": p.get("id"),
                            "Table Number (Order)": p.get("order"),
                            "Created At": p.get("createdAt"),
                            "P1 ID": u1.get("id"),
                            "P1 User ID": u1.get("userId"),
                            "P1 Primary Points (TP)": u1.get("primaryPoints"),
                            "P1 Secondary Points (VP)": u1.get("secondaryPoints"),
                            "P1 Tertiary Points": u1.get("tertiaryPoints"),
                            "P1 Use Secondary List": u1.get("useSecondaryList"),
                            "P2 ID": u2.get("id"),
                            "P2 User ID": u2.get("userId"),
                            "P2 Primary Points (TP)": u2.get("primaryPoints"),
                            "P2 Secondary Points (VP)": u2.get("secondaryPoints"),
                            "P2 Tertiary Points": u2.get("tertiaryPoints"),
                            "P2 Use Secondary List": u2.get("useSecondaryList"),
                            "Approved by P1": p.get("approvedByUser1"),
                            "Approved by P2": p.get("approvedByUser2"),
                            "Added by User ID": p.get("addedByUserId"),
                        }
                        all_pairings_flat.append(row)
            else:
                print(f"Error fetching rounds for {t_name} ({t_id}): HTTP {res_rounds.status_code}")
        except Exception as e:
            rounds_complete = False
            print(f"Error fetching rounds for {t_name} ({t_id}): {e}")

        url_submission = f"https://api.championshub.app/api/submission/{t_id}"
        try:
            res_sub = requests.get(url_submission, headers=headers, cookies=cookies, timeout=15)
            if res_sub.status_code == 200:
                res_json = res_sub.json()
                submissions_by_id[t_id] = res_json
                res_json["points"] = t_points
                patch_obj = select_patch(t_date)
                res_json["patch"] = patch_obj.name if patch_obj else None
                res_json["tournament_type"] = tournament_type
                res_json["season"] = season
                res_json["tournament_id"] = t_id

                if not rounds_complete:
                    continue

                final_pairings_history = pd.DataFrame(all_pairings_flat)
                csv_path = os.path.join(t_directory, CSV_FILE)
                final_pairings_history.to_csv(csv_path, index=False)

                rounds_path = os.path.join(t_directory, SCENARIOS_FILE)
                if not os.path.exists(rounds_path):
                    with open(rounds_path, "w", encoding="utf-8") as f:
                        json.dump({}, f, indent=4)

                submission_path = os.path.join(t_directory, JSON_FILE)
                with open(submission_path, "w", encoding="utf-8") as f:
                    json.dump(res_json, f, indent=4)
            else:
                print(f"Error fetching submissions for {t_name} ({t_id}): HTTP {res_sub.status_code}")
        except Exception as e:
            print(f"Error fetching submissions for {t_name} ({t_id}): {e}")
    return submissions_by_id


def build_tournament_records(events, submissions_by_id):
    """Keep tournament towns and ranked participant IDs; missing submissions remain unknown."""
    records = []
    for event in events:
        submission = submissions_by_id.get(event["id"])
        participant_ids = None
        if submission is not None:
            participant_ids = sorted({
                person["user"]["id"]
                for person in submission.get("people", [])
                if (person.get("user") or {}).get("id") and (person.get("finalResult") or {}).get("place")
            })
        records.append({
            "tournament_id": event["id"],
            "name": event["name"],
            "date": str(event["date"]),
            "tournament_type": "MASTER" if event["tournament_type"] == "DMP" else event["tournament_type"],
            "city": event["city"],
            "player_ids": participant_ids,
        })
    return records


def build_player_cities(main_ranking, online_ranking, tournaments, submissions_by_id):
    """Use ranking cities when available, otherwise the most recent submission snapshot."""
    cities = {}
    for tournament in sorted(tournaments, key=lambda event: event["date"]):
        submission = submissions_by_id.get(tournament["tournament_id"])
        if submission is None:
            continue
        for person in submission.get("people", []):
            user = person.get("user") or {}
            if user.get("id"):
                city = user.get("city")
                cities[user["id"]] = ({key: city.get(key) for key in ("id", "name", "country")}
                                      if city else None)
    for ranking in (online_ranking, main_ranking):
        for player in ranking:
            if player.get("player_id"):
                player_id = player["player_id"]
                name = player.get("city_name")
                previous = cities.get(player_id) or {}
                same_city = name and previous.get("name") == name
                cities[player_id] = (
                    {"id": player.get("city_id") or (previous.get("id") if same_city else None),
                     "name": name,
                     "country": player.get("city_country") or (previous.get("country") if same_city else None)}
                    if name else None
                )
    return cities


def parse_and_store_battles(input_directory=INPUT_DIRECTORY, db_file=None, eligible_ids=None):
    if db_file is None:
        db_file = os.path.join(DATA_DIRECTORY, BATTLES_FILE)
    print(f"Parsing and storing battles from {input_directory} to {db_file}...")
    import_battles(input_directory=input_directory, db_file=db_file, eligible_ids=eligible_ids)


def extract_armies_data(battles_file=None, input_directory=INPUT_DIRECTORY, eligible_ids=None):
    if battles_file is None:
        battles_file = os.path.join(DATA_DIRECTORY, BATTLES_FILE)

    if not os.path.exists(battles_file):
        print(f"Battles file {battles_file} not found.")
        return []

    with open(battles_file, "r", encoding="utf-8") as f:
        battles = json.load(f)

    armies_dict = {}
    for b in battles:
        a1_id, a1_name = b.get("army_1_id"), b.get("army_1_name")
        if a1_id is not None and a1_name:
            armies_dict[a1_id] = a1_name
        a2_id, a2_name = b.get("army_2_id"), b.get("army_2_name")
        if a2_id is not None and a2_name:
            armies_dict[a2_id] = a2_name

    factions = {}
    if os.path.exists(input_directory):
        for tournament_dir in os.listdir(input_directory):
            sub_path = os.path.join(input_directory, tournament_dir, JSON_FILE)
            if os.path.exists(sub_path):
                csv_path = os.path.join(input_directory, tournament_dir, CSV_FILE)
                if eligible_ids is not None and tournament_input_id(sub_path, csv_path) not in eligible_ids:
                    continue
                try:
                    with open(sub_path, "r", encoding="utf-8") as f:
                        sub_data = json.load(f)
                    for person in sub_data.get("people", []):
                        for k in ["army", "secondaryArmy"]:
                            arm = person.get(k)
                            if arm and arm.get("id"):
                                meta = arm.get("metadata") or {}
                                mesbg_type = meta.get("mesbgType")
                                if mesbg_type:
                                    factions[arm["id"]] = mesbg_type.upper()
                except Exception:
                    pass

    missing_factions = [aid for aid in armies_dict if aid not in factions]
    if missing_factions:
        try:
            r = requests.get(
                "https://api.championshub.app/api/army/list",
                headers=headers,
                cookies=cookies,
                timeout=15,
            )
            if r.status_code == 200:
                for a in r.json():
                    meta = a.get("metadata") or {}
                    mtype = meta.get("mesbgType")
                    if mtype:
                        factions[a["id"]] = mtype.upper()
        except Exception as e:
            print(f"Error fetching army metadata from API: {e}")

    armies_list = []
    for army_id in sorted(armies_dict.keys()):
        armies_list.append({
            "army_id": army_id,
            "faction": factions.get(army_id, "UNKNOWN"),
            "name": armies_dict[army_id],
        })

    return armies_list


def _winrate(wins, games, draws=0):
    return round((wins + 0.5 * draws) / games * 100, 2) if games else 0.0


def _bump(table, key, won, lost, **extra):
    entry = table.setdefault(key, {**extra, "games": 0, "wins": 0, "draws": 0, "losses": 0})
    entry["games"] += 1
    if won:
        entry["wins"] += 1
    elif lost:
        entry["losses"] += 1
    else:
        entry["draws"] += 1


def _finalize(table, sort_key=None):
    rows = []
    for entry in table.values():
        entry["winrate"] = _winrate(entry["wins"], entry["games"], entry["draws"])
        rows.append(entry)
    rows.sort(key=sort_key or (lambda r: (-r["games"], -r["winrate"])))
    return rows


def build_player_profiles(battles, main_ranking, online_ranking=None):
    """Per-player stats; winrates count each draw as half a win."""
    place_by_id = {u.get("player_id"): u.get("place") for u in main_ranking}
    discord_linked_by_id = {}
    for ranking_player in [*main_ranking, *(online_ranking or [])]:
        player_id = ranking_player.get("player_id")
        if player_id:
            discord_linked_by_id[player_id] = (
                discord_linked_by_id.get(player_id, False) or bool(ranking_player.get("discord_linked"))
            )
    names = {}
    players = {}

    for battle in battles:
        if battle.get("format") == "DOUBLES":
            continue
        result = battle.get("result")
        if not result or len(result) != 2:
            continue
        for me, opp in (("1", "2"), ("2", "1")):
            player_id = battle.get(f"player_{me}_id")
            opponent_id = battle.get(f"player_{opp}_id")
            if not player_id:
                continue
            names[player_id] = battle.get(f"player_{me}_name")
            my_score = result[int(me) - 1]
            opp_score = result[int(opp) - 1]
            won, lost = my_score > opp_score, my_score < opp_score
            my_army = battle.get(f"army_{me}_id")
            opp_army = battle.get(f"army_{opp}_id")

            profile = players.setdefault(
                player_id,
                {"total": {"games": 0, "wins": 0, "draws": 0, "losses": 0},
                 "armies": {}, "opponents": {}, "opponent_armies": {}, "defeated": {}},
            )
            total = profile["total"]
            total["games"] += 1
            total["wins" if won else "losses" if lost else "draws"] += 1

            _bump(profile["armies"], my_army, won, lost,
                  army_id=my_army, army_name=battle.get(f"army_{me}_name"))
            _bump(profile["opponent_armies"], opp_army, won, lost,
                  army_id=opp_army, army_name=battle.get(f"army_{opp}_name"))
            if opponent_id:
                names[opponent_id] = battle.get(f"player_{opp}_name")
                _bump(profile["opponents"], opponent_id, won, lost,
                      player_id=opponent_id, displayName=battle.get(f"player_{opp}_name"))
                if won:
                    _bump(profile["defeated"], opponent_id, True, False,
                          player_id=opponent_id, displayName=battle.get(f"player_{opp}_name"))

    profiles = []
    for player_id, p in players.items():
        total = p["total"]
        total["winrate"] = _winrate(total["wins"], total["games"], total["draws"])
        defeated = [
            {"player_id": d["player_id"], "displayName": d["displayName"],
             "main_ranking_place": place_by_id[d["player_id"]], "times_defeated": d["wins"]}
            for d in p["defeated"].values()
            if place_by_id.get(d["player_id"]) is not None
        ]
        defeated.sort(key=lambda d: d["main_ranking_place"])
        profiles.append({
            "player_id": player_id,
            "displayName": names.get(player_id),
            "main_ranking_place": place_by_id.get(player_id),
            "discord_linked": discord_linked_by_id.get(player_id, False),
            "games_played": total["games"],
            "wins": total["wins"],
            "draws": total["draws"],
            "losses": total["losses"],
            "winrate": total["winrate"],
            "army_lists": _finalize(p["armies"]),
            "opponents": _finalize(p["opponents"]),
            "opponent_army_lists": _finalize(p["opponent_armies"]),
            "top5_defeated_players": defeated[:5],
        })
    profiles.sort(key=lambda r: (-r["games_played"], r["displayName"] or ""))
    return profiles


def load_metadata():
    metadata_path = os.path.join(DATA_DIRECTORY, METADATA_FILE)
    if not os.path.exists(metadata_path):
        return {"time": None}
    with open(metadata_path, "r") as f:
        return json.load(f)


def save_metadata(metadata):
    metadata_path = os.path.join(DATA_DIRECTORY, METADATA_FILE)
    os.makedirs(DATA_DIRECTORY, exist_ok=True)
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)


def save_data(data, filename):
    data_path = os.path.join(DATA_DIRECTORY, filename)
    os.makedirs(DATA_DIRECTORY, exist_ok=True)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def download_data(force=False):
    metadata = load_metadata()
    raw_time = metadata.get("time")
    load_time = datetime.datetime.fromisoformat(raw_time) if raw_time else None

    is_stale = force or load_time is None or (
        datetime.datetime.now(datetime.timezone.utc) - load_time > datetime.timedelta(hours=24)
    )

    if is_stale:
        print(f"Data is missing or older than 24 hours, refreshing data...")

        main_ranking_json = get_main_ranking_data()
        save_data(main_ranking_json, MAIN_RANKING_FILE)

        online_ranking_json = get_online_ranking_data()
        save_data(online_ranking_json, ONLINE_RANKING_FILE)

        all_events_raw = get_finished_events()
        polish_events = get_polish_events(all_events_raw)

        submissions_by_id = download_tournament_battles_data(polish_events)
        rankings_2027 = build_2027_rankings(polish_events, submissions_by_id)
        save_data(rankings_2027["main"], MAIN_RANKING_2027_FILE)
        save_data(rankings_2027["master"], MASTER_RANKING_2027_FILE)
        save_data(rankings_2027["online"], ONLINE_RANKING_2027_FILE)
        rankings_by_season = {2026: main_ranking_json, 2027: rankings_2027["main"]}

        master_tournaments_data = download_master_tournaments_data(polish_events, submissions_by_id)
        save_data(master_tournaments_data, MASTER_TOURNAMENTS_FILE)

        master_ranking_json = get_master_ranking_data(master_tournaments_data, main_ranking_json)
        save_data(master_ranking_json, MASTER_RANKING_FILE)

        tournaments = build_tournament_records(polish_events, submissions_by_id)
        save_data(tournaments, TOURNAMENTS_FILE)
        player_cities = build_player_cities(main_ranking_json, online_ranking_json, tournaments, submissions_by_id)
        save_data(player_cities, PLAYER_CITIES_FILE)
        eligible_ids = {event["id"] for event in polish_events}
        parse_and_store_battles(INPUT_DIRECTORY, os.path.join(DATA_DIRECTORY, BATTLES_FILE), eligible_ids)

        armies_data = extract_armies_data(
            battles_file=os.path.join(DATA_DIRECTORY, BATTLES_FILE),
            input_directory=INPUT_DIRECTORY,
            eligible_ids=eligible_ids,
        )
        save_data(armies_data, ARMIES_FILE)

        with open(os.path.join(DATA_DIRECTORY, BATTLES_FILE), "r", encoding="utf-8") as f:
            battles_data = json.load(f)
        from achievements import calculate_achievements
        from store import load_tournament_results

        profiles = build_player_profiles(battles_data, main_ranking_json, online_ranking_json)
        save_data(calculate_achievements(
            profiles,
            load_tournament_results(INPUT_DIRECTORY, main_ranking_json, eligible_ids, rankings_by_season),
            tournaments,
            main_ranking=main_ranking_json,
            rankings_by_season=rankings_by_season,
            battles=battles_data,
            armies=armies_data,
            player_cities=player_cities,
        ),
                  PLAYER_PROFILES_FILE)

        metadata["time"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_metadata(metadata)

        print(f"Data refreshed and saved to {DATA_DIRECTORY} directory.")
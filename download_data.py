import pandas as pd
import requests
import copy
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
)
from db import BattleDB


START_DATE = datetime.datetime.strptime("05-12-2025", "%d-%m-%Y").date()
END_DATE = datetime.datetime.strptime("30-11-2050", "%d-%m-%Y").date()


DATA_DIRECTORY = "data"
METADATA_FILE = "metadata.json"
MAIN_RANKING_FILE = "main_ranking.json"
ONLINE_RANKING_FILE = "online_ranking.json"
MASTER_RANKING_FILE = "master_ranking.json"
MASTER_TOURNAMENTS_FILE = "master_tournaments.json"
BATTLES_FILE = "battles.json"
ARMIES_FILE = "armies.json"
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

        simplified_entry = {
            "place": user.get("place"),
            "score": user.get("score"),
            "player_id": (user.get("user") or {}).get("id"),
            "displayName": (user.get("user") or {}).get("displayName"),
            "city_name": ((user.get("user") or {}).get("city") or {}).get("name"),
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
        place = user.get("place")
        score = user.get("score")
        tie_breaker = user_main_score.get(user_id, 0)
        simplified_entry = {
            "place": place,
            "score": score,
            "tie_breaker": tie_breaker,
            "displayName": (user.get("user") or {}).get("displayName"),
            "city_name": ((user.get("user") or {}).get("city") or {}).get("name"),
            "top_2": user_master_results.get(user_id, [0, 0, 0])[0] + user_master_results.get(user_id, [0, 0, 0])[1],
            "master_1": user_master_results.get(user_id, [0, 0, 0])[0],
            "master_2": user_master_results.get(user_id, [0, 0, 0])[1],
            "master_3": user_master_results.get(user_id, [0, 0, 0])[2],
        }
        data_to_display = copy.copy(simplified_entry)
        transformed.append(data_to_display)

    transformed.sort(key=lambda entry: (entry["place"], -entry["tie_breaker"]))

    prev_entry = None
    for index, entry in enumerate(transformed):
        if prev_entry is not None and entry["place"] == prev_entry["place"] and entry["tie_breaker"] == prev_entry["tie_breaker"]:
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

        simplified_entry = {
            "place": user.get("place"),
            "score": user.get("score"),
            "player_id": (user.get("user") or {}).get("id"),
            "displayName": (user.get("user") or {}).get("displayName"),
            "city_name": ((user.get("user") or {}).get("city") or {}).get("name"),
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
        tournament_type = tournament.get("rankingEventType", {}).get("name", "")
        score = tournament.get("rankingResult")
        if tournament_type == "master":
            master_values.append(score)
        elif tournament_type == "DMP":
            master_values.append(score)
        elif tournament_type == "lokal":
            local_values.append(score)
        elif tournament_type == "challenger":
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
        try:
            r = requests.post(
                "https://api.championshub.app/api/event-management/list",
                headers=headers,
                cookies=cookies,
                json=payload,
                timeout=15,
            )
            data = r.json().get("data", [])
            if not data:
                break
            all_events_raw.extend(data)
            if len(data) < 100:
                break
            skip += 100
        except Exception as e:
            print(f"Error fetching event list: {e}")
            break
    return all_events_raw


def get_polish_events(all_events_raw):
    target_events = []
    for ev in all_events_raw:
        city_data = ev.get("city") or {}
        raw_start = ev.get("startsAt")
        t_points = ev.get("pointsLimit")
        if raw_start and city_data.get("country") == "PL":
            corrected_date = (pd.to_datetime(raw_start) + pd.Timedelta(hours=2)).date()
            if START_DATE <= corrected_date <= END_DATE:
                t_id = ev.get("id")
                t_name = ev.get("name")
                ranking_event_type = ev.get("rankingEventType")
                tournament_type = ranking_event_type.get("name").upper() if ranking_event_type else None
                target_events.append({
                    "id": t_id,
                    "name": t_name,
                    "date": corrected_date,
                    "points": t_points,
                    "tournament_type": tournament_type,
                })
    return target_events


def download_master_tournaments_data(polish_events=None):
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
            res_details = requests.get(url_details, headers=headers, cookies=cookies, timeout=15)
            if res_details.status_code == 200:
                res_json = res_details.json()
                people = res_json.get("people", [])
                people_data = []
                for person in people:
                    user = person.get("user", {})
                    result = person.get("finalResult", {}).get("place", None)
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


def download_tournament_battles_data(polish_events=None):
    print("Downloading tournament battles data from Champions Hub API...")
    if polish_events is None:
        all_events = get_finished_events()
        polish_events = get_polish_events(all_events)

    for ev in polish_events:
        t_id = ev["id"]
        t_name = ev["name"]
        t_date = ev["date"]
        t_points = ev["points"]
        tournament_type = ev["tournament_type"]

        print(f"Downloading battles for event: {t_name}")
        folder_name = "".join(x for x in t_name if x.isalnum())
        t_directory = os.path.join(INPUT_DIRECTORY, folder_name)
        os.makedirs(t_directory, exist_ok=True)

        url_rounds_list = f"https://api.championshub.app/api/round/{t_id}"
        all_pairings_flat = []
        try:
            res_rounds = requests.get(url_rounds_list, headers=headers, cookies=cookies, timeout=15)
            if res_rounds.status_code == 200:
                rounds_list = res_rounds.json().get("rounds", [])
                for rd in rounds_list:
                    r_id = rd.get("id")
                    r_title = rd.get("title") or rd.get("name")
                    url_details = f"https://api.championshub.app/api/round/{t_id}/{r_id}"
                    res_details = requests.get(url_details, headers=headers, cookies=cookies, timeout=15)
                    if res_details.status_code != 200:
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
        except Exception as e:
            print(f"Error fetching rounds for {t_name} ({t_id}): {e}")

        final_pairings_history = pd.DataFrame(all_pairings_flat)
        csv_path = os.path.join(t_directory, CSV_FILE)
        final_pairings_history.to_csv(csv_path, index=False)

        url_submission = f"https://api.championshub.app/api/submission/{t_id}"
        try:
            res_sub = requests.get(url_submission, headers=headers, cookies=cookies, timeout=15)
            if res_sub.status_code == 200:
                res_json = res_sub.json()
                res_json["points"] = t_points
                patch_obj = select_patch(t_date)
                res_json["patch"] = patch_obj.name if patch_obj else None
                res_json["tournament_type"] = tournament_type

                rounds_path = os.path.join(t_directory, SCENARIOS_FILE)
                if not os.path.exists(rounds_path):
                    with open(rounds_path, "w", encoding="utf-8") as f:
                        json.dump({}, f, indent=4)

                submission_path = os.path.join(t_directory, JSON_FILE)
                with open(submission_path, "w", encoding="utf-8") as f:
                    json.dump(res_json, f, indent=4)
        except Exception as e:
            print(f"Error fetching submissions for {t_name} ({t_id}): {e}")


def parse_and_store_battles(input_directory=INPUT_DIRECTORY, db_file=None):
    if db_file is None:
        db_file = os.path.join(DATA_DIRECTORY, BATTLES_FILE)
    print(f"Parsing and storing battles from {input_directory} to {db_file}...")
    import_battles(input_directory=input_directory, db_file=db_file)


def extract_armies_data(battles_file=None, input_directory=INPUT_DIRECTORY):
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
        datetime.datetime.now(datetime.timezone.utc) - load_time > datetime.timedelta(hours=12)
    )

    if is_stale:
        print(f"Data is missing or older than 3 days, refreshing data...")

        main_ranking_json = get_main_ranking_data()
        save_data(main_ranking_json, MAIN_RANKING_FILE)

        online_ranking_json = get_online_ranking_data()
        save_data(online_ranking_json, ONLINE_RANKING_FILE)

        all_events_raw = get_finished_events()
        polish_events = get_polish_events(all_events_raw)

        master_tournaments_data = download_master_tournaments_data(polish_events)
        save_data(master_tournaments_data, MASTER_TOURNAMENTS_FILE)

        master_ranking_json = get_master_ranking_data(master_tournaments_data, main_ranking_json)
        save_data(master_ranking_json, MASTER_RANKING_FILE)

        download_tournament_battles_data(polish_events)
        parse_and_store_battles(INPUT_DIRECTORY, os.path.join(DATA_DIRECTORY, BATTLES_FILE))

        armies_data = extract_armies_data(
            battles_file=os.path.join(DATA_DIRECTORY, BATTLES_FILE),
            input_directory=INPUT_DIRECTORY,
        )
        save_data(armies_data, ARMIES_FILE)

        metadata["time"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_metadata(metadata)

        print(f"Data refreshed and saved to {DATA_DIRECTORY} directory.")
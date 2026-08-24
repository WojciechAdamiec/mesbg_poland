import pandas as pd
import requests
import copy
import datetime
import json
import os
from rich import print


START_DATE = datetime.datetime.strptime("05-12-2025", "%d-%m-%Y").date()
END_DATE = datetime.datetime.strptime("30-11-2050", "%d-%m-%Y").date()


DATA_DIRECTORY = "data"
METADATA_FILE = "metadata.json"
MAIN_RANKING_FILE = "main_ranking.json"
ONLINE_RANKING_FILE = "online_ranking.json"
MASTER_RANKING_FILE = "master_ranking.json"
MASTER_TOURNAMENTS_FILE = "master_tournaments.json"
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


def download_master_tournaments_data():
    print("Downloading masters data from Champions Hub API...")
    all_events_raw = []
    skip = 0
    while True:
        payload = {"ranking": None, "statuses": ["FINISHED"], "take": 100, "skip": skip}
        try:
            r = requests.post("https://api.championshub.app/api/event-management/list", headers=headers, cookies=cookies, json=payload, timeout=15)
            data = r.json().get("data", [])
            if not data: break
            all_events_raw.extend(data)
            if len(data) < 100: break
            skip += 100
        except: break

    target_event_ids = []
    for ev in all_events_raw:
        city_data = ev.get("city") or {}
        raw_start = ev.get("startsAt")
        t_points = ev.get("pointsLimit")
        if raw_start and city_data.get("country") == "PL":
            corrected_date = (pd.to_datetime(raw_start) + pd.Timedelta(hours=2)).date()
            if START_DATE <= corrected_date <= END_DATE:
                t_id, t_name = ev.get("id"), ev.get("name")
                tournament_type = ev.get("rankingEventType").get("name").upper() if ev.get("rankingEventType") else None
                if tournament_type == "MASTER":
                    target_event_ids.append((t_id, t_name, corrected_date, t_points, tournament_type))
    master_tournaments_data = []
    for master_id, master_name, master_date, master_points, master_type in target_event_ids:
        url_details = f"https://api.championshub.app/api/submission/{master_id}"
        res_details = requests.get(url_details, headers=headers, cookies=cookies, timeout=15)
        res_json = res_details.json()
        people = res_json.get("people", [])
        people_data = []
        if people:
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

    return master_tournaments_data



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
    with open(data_path, "w") as f:
        json.dump(data, f, indent=4)


def download_data():
    metadata = load_metadata()
    raw_time = metadata.get("time")
    load_time = datetime.datetime.fromisoformat(raw_time) if raw_time else None

    is_stale = load_time is None or (
        datetime.datetime.now(datetime.timezone.utc) - load_time > datetime.timedelta(hours=1)
    )

    if is_stale:
        print(f"Data is missing or older than 1 hour, refreshing data...")

        main_ranking_json = get_main_ranking_data()
        save_data(main_ranking_json, MAIN_RANKING_FILE)

        online_ranking_json = get_online_ranking_data()
        save_data(online_ranking_json, ONLINE_RANKING_FILE)

        master_tournaments_data = download_master_tournaments_data()
        save_data(master_tournaments_data, MASTER_TOURNAMENTS_FILE)

        master_ranking_json = get_master_ranking_data(master_tournaments_data, main_ranking_json)
        save_data(master_ranking_json, MASTER_RANKING_FILE)

        metadata["time"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_metadata(metadata)
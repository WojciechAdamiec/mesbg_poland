import requests
import copy
import datetime
import json
import os


DATA_DIRECTORY = "data"
METADATA_FILE = "metadata.json"
MAIN_RANKING_FILE = "main_ranking.json"
ONLINE_RANKING_FILE = "online_ranking.json"
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
            "displayName": (user.get("user") or {}).get("displayName"),
            "city_name": ((user.get("user") or {}).get("city") or {}).get("name"),
        }
        data_to_display = copy.copy(simplified_entry)
        data_to_display.update(user_tournament_data)
        transformed.append(data_to_display)
    
    return transformed


def transform_online_ranking_data(raw_data):
    transformed = []
    
    for user in raw_data:
        user_data = get_user_online_tournaments(user.get("id"))
        user_tournament_data = parse_user_online_tournament_data(user_data)

        simplified_entry = {
            "place": user.get("place"),
            "score": user.get("score"),
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
    res_json = transform_ranking_data(res_json)  # Transform the data to only include Place, displayName, city_name, and score
    return res_json


def get_online_ranking_data():
    print("Downloading online ranking data from Champions Hub API...")
    url_details = f"https://api.championshub.app/api/ranking/results/mesbg-pl-online?season=30&cityId=PL/"
    res_details = requests.get(url_details, headers=headers, cookies=cookies, timeout=15)
    res_json = res_details.json()
    res_json = transform_online_ranking_data(res_json)  # Transform the data to only include Place, displayName, city_name, and score
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

        ranking_path = os.path.join(DATA_DIRECTORY, MAIN_RANKING_FILE)
        os.makedirs(DATA_DIRECTORY, exist_ok=True)
        with open(ranking_path, "w") as f:
            json.dump(main_ranking_json, f, indent=4)

        online_ranking_json = get_online_ranking_data()
        
        online_ranking_path = os.path.join(DATA_DIRECTORY, ONLINE_RANKING_FILE)
        with open(online_ranking_path, "w") as f:
            json.dump(online_ranking_json, f, indent=4)

        metadata["time"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_metadata(metadata)
import requests
from rich import print


ACCESS_TOKEN = "PASTER_TOKEN_HERE"
INPUT_DIRECTORY = "input"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "game-system": "mesbg",
}
cookies = {"access_token": ACCESS_TOKEN}


def get_main_ranking_data():
    url_details = f"https://api.championshub.app/api/ranking/results/mesbg-pl?season=28&cityId=PL/"
    res_details = requests.get(url_details, headers=headers, cookies=cookies, timeout=15)
    res_json = res_details.json()
    res_json = transform_ranking_data(res_json)  # Transform the data to only include Place, displayName, city_name, and score
    return res_json


def transform_ranking_data(raw_data):
    """Transform raw ranking data to simplified format with only Place, displayName, city_name, and score"""
    transformed = []
    
    for entry in raw_data:
        simplified_entry = {
            "place": entry.get("place"),
            "displayName": (entry.get("user") or {}).get("displayName"),
            "city_name": ((entry.get("user") or {}).get("city") or {}).get("name"),
            "score": entry.get("score")
        }
        transformed.append(simplified_entry)
    
    return transformed
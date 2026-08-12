import json
import os
import requests
import pandas as pd
from datetime import datetime
from rich import print
from patches import select_patch


START_DATE = "05-12-2025"
END_DATE = "30-11-2050"
ACCESS_TOKEN = "PASTER_TOKEN_HERE"
INPUT_DIRECTORY = "input"

start_date = datetime.strptime(START_DATE, "%d-%m-%Y").date()
end_date = datetime.strptime(END_DATE, "%d-%m-%Y").date()

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "game-system": "mesbg",
}
cookies = {"access_token": ACCESS_TOKEN}


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
        if start_date <= corrected_date <= end_date:
            t_id, t_name = ev.get("id"), ev.get("name")
            tournament_type = ev.get("rankingEventType").get("name").upper() if ev.get("rankingEventType") else None
            target_event_ids.append((t_id, t_name, corrected_date, t_points, tournament_type))



all_pairings_flat = []


for t_id, t_name, t_date, t_points, tournament_type in target_event_ids:
    print(f"Event: {t_name}")
    t_directory = f"{INPUT_DIRECTORY}/{''.join(x for x in t_name if (x.isalpha() or x.isdigit()))}"
    os.makedirs(t_directory, exist_ok=True)
    url_rounds_list = f"https://api.championshub.app/api/round/{t_id}"
    
    try:
        res_rounds = requests.get(url_rounds_list, headers=headers, cookies=cookies, timeout=15)
        if res_rounds.status_code != 200: continue
        
        rounds_list = res_rounds.json().get("rounds", [])
        
        for rd in rounds_list:
            r_id = rd.get("id")
            r_title = rd.get("title") or rd.get("name")
            
            url_details = f"https://api.championshub.app/api/round/{t_id}/{r_id}"
            res_details = requests.get(url_details, headers=headers, cookies=cookies, timeout=15)
            if res_details.status_code != 200: continue
            
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
                    "Added by User ID": p.get("addedByUserId")
                }
                all_pairings_flat.append(row)
                
    except Exception as e:
        print(f"Error with a round: {t_id}: {e}")

    final_pairings_history = pd.DataFrame(all_pairings_flat)
    final_pairings_history.to_csv(f"{t_directory}/pairings_history.csv", index=False)
    all_pairings_flat = []

    url_details = f"https://api.championshub.app/api/submission/{t_id}"
    res_details = requests.get(url_details, headers=headers, cookies=cookies, timeout=15)
    res_json = res_details.json()
    res_json["points"] = t_points
    res_json["patch"] = select_patch(t_date).name
    res_json["tournament_type"] = tournament_type

    if not os.path.exists(f"{t_directory}/rounds.json"):
        with open(f"{t_directory}/rounds.json", "w") as f:
            json.dump({}, f, indent=4)

    with open(f"{t_directory}/submission_data.json", "w") as f:
        json.dump(res_json, f, indent=4)

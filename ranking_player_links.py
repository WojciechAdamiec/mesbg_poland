from collections import defaultdict
from urllib.parse import urlencode

from dash import dcc

from store import load_main_ranking, load_player_profiles


profiles = load_player_profiles()
profile_ids = {profile["player_id"] for profile in profiles if profile.get("player_id")}
ids_by_name = defaultdict(set)
for profile in profiles:
    if profile.get("player_id") and profile.get("displayName"):
        ids_by_name[profile["displayName"].strip()].add(profile["player_id"])

ids_by_name_city = defaultdict(set)
for row in load_main_ranking():
    if row.get("player_id") in profile_ids and row.get("displayName") and row.get("city_name"):
        ids_by_name_city[(row["displayName"].strip(), row["city_name"].strip())].add(row["player_id"])


def player_name_cell(row):
    name = row["displayName"]
    player_id = row.get("player_id")
    if not player_id and name:
        candidates = ids_by_name[name.strip()]
        if len(candidates) != 1 and row.get("city_name"):
            candidates = ids_by_name_city[(name.strip(), row["city_name"].strip())]
        if len(candidates) == 1:
            player_id = next(iter(candidates))
    if player_id not in profile_ids:
        return name
    return dcc.Link(name, href="/stats/player_profiles?" + urlencode({"player": player_id}),
                    style={"color": "#00ffff"})

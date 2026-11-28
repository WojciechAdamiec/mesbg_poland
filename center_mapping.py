import json
from pathlib import Path


MAPPING_PATH = Path(__file__).resolve().parent / "data" / "center_cities.json"


def load_center_mapping(path=MAPPING_PATH):
    with path.open(encoding="utf-8") as file:
        mapping = json.load(file)
    city_to_center = {}
    for center, cities in mapping.items():
        if not isinstance(cities, list):
            raise ValueError(f"Expected a list of cities for {center} in {path}")
        for city in cities:
            key = city.strip().casefold()
            if not key or key in city_to_center:
                raise ValueError(f"Duplicate or empty city {city!r} in {path}")
            city_to_center[key] = None if center == "unassigned" else center
    return [center for center in mapping if center != "unassigned"], city_to_center


def center_for_city(city, city_to_center):
    if not city or city.get("country") not in (None, "PL"):
        return None
    return city_to_center.get((city.get("name") or "").strip().casefold())


def center_for_ranked_player(row, player_cities, city_to_center):
    player_id = row.get("player_id")
    if player_id in player_cities:
        city = player_cities[player_id]
    else:
        city = {"name": row.get("city_name"), "country": row.get("city_country")}
    return center_for_city(city, city_to_center)

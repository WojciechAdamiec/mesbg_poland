import json
import csv
import os
from battle import Battle, Points, Patch, TournamentType, Scenario
from db import BattleDB


INPUT_DIRECTORY = "input"
CSV_FILE = "pairings_history.csv"
JSON_FILE = "submission_data.json"
SCENARIOS_FILE = "rounds.json"
DB_FILE = "battles.json"


def parse_scenario(raw_scenario: str, tournament_dir: str) -> Scenario | None:

    if not raw_scenario:
        return None

    with open(os.path.join(INPUT_DIRECTORY, tournament_dir, SCENARIOS_FILE), "r", encoding="utf-8") as f:
        SCENARIO_MAP = json.load(f)

    scenario = SCENARIO_MAP.get(raw_scenario.strip())

    return Scenario[scenario] if scenario else None


def parse_patch(raw_patch: str) -> Patch | None:
    if not raw_patch:
        return None

    return Patch[raw_patch]


def parse_points(raw_points: str) -> Points:
    if not raw_points:
        return None

    if "+" in raw_points or "/" in raw_points:
        return None

    doubled = "x" in raw_points.lower()
    value = int(raw_points) if not doubled else int(raw_points[2:])

    return Points(value=value, doubled=doubled)


def parse_tournament_type(raw_type: str) -> TournamentType | None:
    if not raw_type:
        return None

    TOURNAMENT_TYPE_MAP = {
        "LOKAL": TournamentType.LOCAL,
        "CHALLENGER": TournamentType.CHALLENGER,
        "MASTER": TournamentType.MASTER,
        "ONLINE": TournamentType.ONLINE,
    }

    try:
        return TOURNAMENT_TYPE_MAP[raw_type.upper()]
    except KeyError:
        print(f"WARNING: Unknown tournament type: {raw_type}")
        return None


def load_submissions(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    submissions = {}

    for submission in data["people"]:
        army = submission.get("army")
        secondary_army = submission.get("secondaryArmy")
        user = submission.get("user")

        # No army/player information -> cannot create Battle
        if not army or not user:
            continue

        # Only actual participants
        if submission.get("status") not in {"APPROVED", "WAITING"}:
            continue

        submissions[user["id"]] = {
            "submission_id": submission["id"],
            "player_id": user["id"],
            "player_name": user["displayName"],
            "army_id": army["id"],
            "army_name": army["name"],
            "second_army_id": secondary_army.get("id") if secondary_army else None,
            "second_army_name": secondary_army.get("name") if secondary_army else None,
        }


    submissions["points"] = data.get("points", None)
    submissions["patch"] = data.get("patch", None)
    submissions["tournament_type"] = data.get("tournament_type", None)
    return submissions


def parse_result(row: dict) -> tuple[int, int] | None:
    p1_vp = row["P1 Secondary Points (VP)"]
    p2_vp = row["P2 Secondary Points (VP)"]

    if p1_vp == "" or p2_vp == "":
        return None

    try:
        return int(float(p1_vp)), int(float(p2_vp))
    except (ValueError, TypeError):
        return None


def parse_battles(csv_path: str, json_path: str, tournament_dir: str) -> list[Battle]:

    submissions = load_submissions(json_path)

    battles = []

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:

            # Only finished rounds
            if row["Round Status"] != "FINISHED":
                continue

            tournament_id = row["Tournament ID"]

            p1_user_id = row["P1 User ID"]
            p2_user_id = row["P2 User ID"]

            p1_use_secondary_list=True if row["P1 Use Secondary List"] == "True" else False if row["P1 Use Secondary List"] == "False" else None
            p2_use_secondary_list=True if row["P2 Use Secondary List"] == "True" else False if row["P2 Use Secondary List"] == "False" else None

            p1 = submissions.get(p1_user_id)
            p2 = submissions.get(p2_user_id)

            if p1 is None:
                print(
                    f"WARNING: P1 user not found: "
                    f"{p1_user_id}"
                )
                continue

            if p2 is None:
                print(
                    f"WARNING: P2 user not found: "
                    f"{p2_user_id}"
                )
                continue

            result = parse_result(row)

            if result is None:
                print(
                    f"WARNING: Invalid result in table "
                    f"{row['Table ID']}"
                )
                continue

            p1_first_army_id=p1["army_id"]
            p1_second_army_id=p1.get("second_army_id")

            p2_first_army_id=p2["army_id"]
            p2_second_army_id=p2.get("second_army_id")

            if p1_second_army_id is not None and p1_use_secondary_list == True:
                p1_army_id = p1_second_army_id
                p1_army_name = p1["second_army_name"]
            elif p1_second_army_id is not None and p1_use_secondary_list == False:
                p1_army_id = p1_first_army_id
                p1_army_name = p1["army_name"]
            elif p1_second_army_id is not None and p1_use_secondary_list == None:
                p1_army_id = None
                p1_army_name = None
            else:
                p1_army_id = p1_first_army_id
                p1_army_name = p1["army_name"]

            if p2_second_army_id is not None and p2_use_secondary_list == True:
                p2_army_id = p2_second_army_id
                p2_army_name = p2["second_army_name"]
            elif p2_second_army_id is not None and p2_use_secondary_list == False:
                p2_army_id = p2_first_army_id
                p2_army_name = p2["army_name"]
            elif p2_second_army_id is not None and p2_use_secondary_list == None:
                p2_army_id = None
                p2_army_name = None
            else:
                p2_army_id = p2_first_army_id
                p2_army_name = p2["army_name"]

            battle = Battle(
                points=parse_points(submissions["points"]),
                

                army_1_id=p1_army_id,
                army_2_id=p2_army_id,
                army_1_name=p1_army_name,
                army_2_name=p2_army_name,

                result=result,

                patch=parse_patch(submissions["patch"]),

                player_1_id=p1["player_id"],
                player_2_id=p2["player_id"],

                player_1_name=p1["player_name"],
                player_2_name=p2["player_name"],

                scenario=parse_scenario(row["Round Title"], tournament_dir),

                tournament_id=tournament_id,
                tournament_name=row["Tournament Name"],

                tournament_type=parse_tournament_type(submissions["tournament_type"]),
            )
            battles.append(battle)

    return battles

def import_battles():
    for tournament_dir in os.listdir(INPUT_DIRECTORY):
        tournament_path = os.path.join(INPUT_DIRECTORY, tournament_dir)
        if os.path.isdir(tournament_path):
            csv_file = os.path.join(tournament_path, CSV_FILE)
            json_file = os.path.join(tournament_path, JSON_FILE)

            if os.path.exists(csv_file) and os.path.exists(json_file):
                battles = parse_battles(csv_file, json_file, tournament_dir)
                print(f"Parsed {len(battles)} battles from {tournament_dir}.")
                db = BattleDB(DB_FILE)
                db.battles.extend(battles)
                db.save()
                print(f"Database now contains {len(db.battles)} battles.")
            else:
                print(f"Missing CSV or JSON file in {tournament_dir}. Skipping.")


if __name__ == "__main__":
    import_battles()
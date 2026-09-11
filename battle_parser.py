import json
import csv
import os
from battle import Battle, Points, Patch, TournamentType, Scenario
from db import BattleDB, DB_FILE


INPUT_DIRECTORY = "input"
CSV_FILE = "pairings_history.csv"
JSON_FILE = "submission_data.json"
SCENARIOS_FILE = "rounds.json"


def parse_scenario(raw_scenario: str | None, tournament_dir: str, input_directory: str = INPUT_DIRECTORY) -> Scenario | None:
    if not raw_scenario:
        return None

    rounds_path = os.path.join(input_directory, tournament_dir, SCENARIOS_FILE)
    if not os.path.exists(rounds_path):
        return None

    try:
        with open(rounds_path, "r", encoding="utf-8") as f:
            scenario_map = json.load(f)
        scenario = scenario_map.get(raw_scenario.strip())
        return Scenario[scenario] if scenario else None
    except Exception:
        return None


def parse_patch(raw_patch: str | None) -> Patch | None:
    if not raw_patch:
        return None
    try:
        return Patch[raw_patch]
    except KeyError:
        return None


def parse_points(raw_points: str | int | None) -> Points | None:
    if raw_points is None:
        return None

    raw_points_str = str(raw_points).strip()
    if not raw_points_str or "+" in raw_points_str or "/" in raw_points_str:
        return None

    doubled = "x" in raw_points_str.lower()
    try:
        if doubled:
            val_str = raw_points_str.lower().split("x")[-1].strip()
            value = int(val_str)
        else:
            value = int(raw_points_str)
        return Points(value=value, doubled=doubled)
    except (ValueError, TypeError):
        return None


def parse_tournament_type(raw_type: str | None) -> TournamentType | None:
    if not raw_type:
        return None

    tournament_type_map = {
        "LOKAL": TournamentType.LOCAL,
        "CHALLENGER": TournamentType.CHALLENGER,
        "MASTER": TournamentType.MASTER,
        "DMP": TournamentType.DMP,
        "ONLINE": TournamentType.ONLINE,
    }

    try:
        return tournament_type_map[raw_type.upper()]
    except KeyError:
        print(f"WARNING: Unknown tournament type: {raw_type}")
        return None


def load_submissions(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    submissions = {}

    for submission in data.get("people", []):
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
            "submission_id": submission.get("id"),
            "player_id": user["id"],
            "player_name": user.get("displayName"),
            "army_id": army.get("id"),
            "army_name": army.get("name"),
            "second_army_id": secondary_army.get("id") if secondary_army else None,
            "second_army_name": secondary_army.get("name") if secondary_army else None,
        }

    submissions["points"] = data.get("points", None)
    submissions["patch"] = data.get("patch", None)
    submissions["tournament_type"] = data.get("tournament_type", None)
    return submissions


def parse_result(row: dict) -> tuple[int, int] | None:
    p1_vp = row.get("P1 Secondary Points (VP)")
    p2_vp = row.get("P2 Secondary Points (VP)")

    if p1_vp == "" or p1_vp is None:
        p1_vp = "0"
    if p2_vp == "" or p2_vp is None:
        p2_vp = "0"

    try:
        return int(float(p1_vp)), int(float(p2_vp))
    except (ValueError, TypeError):
        return None


def parse_battles(csv_path: str, json_path: str, tournament_dir: str, input_directory: str = INPUT_DIRECTORY) -> list[Battle]:
    submissions = load_submissions(json_path)
    battles = []

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Only finished rounds
            if row.get("Round Status") != "FINISHED":
                continue

            tournament_id = row.get("Tournament ID")
            p1_user_id = row.get("P1 User ID")
            p2_user_id = row.get("P2 User ID")

            p1_use_sec_raw = row.get("P1 Use Secondary List")
            p2_use_sec_raw = row.get("P2 Use Secondary List")

            p1_use_secondary_list = True if p1_use_sec_raw == "True" else False if p1_use_sec_raw == "False" else None
            p2_use_secondary_list = True if p2_use_sec_raw == "True" else False if p2_use_sec_raw == "False" else None

            p1 = submissions.get(p1_user_id)
            p2 = submissions.get(p2_user_id)

            if p1 is None:
                print(f"WARNING: P1 user not found: {p1_user_id}")
                continue

            if p2 is None:
                print(f"WARNING: P2 user not found: {p2_user_id}")
                continue

            result = parse_result(row)
            if result is None:
                print(f"WARNING: Invalid result in table {row.get('Table ID')}")
                continue

            p1_first_army_id = p1["army_id"]
            p1_second_army_id = p1.get("second_army_id")

            p2_first_army_id = p2["army_id"]
            p2_second_army_id = p2.get("second_army_id")

            if p1_second_army_id is not None and p1_use_secondary_list is True:
                p1_army_id = p1_second_army_id
                p1_army_name = p1["second_army_name"]
            elif p1_second_army_id is not None and p1_use_secondary_list is False:
                p1_army_id = p1_first_army_id
                p1_army_name = p1["army_name"]
            elif p1_second_army_id is not None and p1_use_secondary_list is None:
                p1_army_id = None
                p1_army_name = None
            else:
                p1_army_id = p1_first_army_id
                p1_army_name = p1["army_name"]

            if p2_second_army_id is not None and p2_use_secondary_list is True:
                p2_army_id = p2_second_army_id
                p2_army_name = p2["second_army_name"]
            elif p2_second_army_id is not None and p2_use_secondary_list is False:
                p2_army_id = p2_first_army_id
                p2_army_name = p2["army_name"]
            elif p2_second_army_id is not None and p2_use_secondary_list is None:
                p2_army_id = None
                p2_army_name = None
            else:
                p2_army_id = p2_first_army_id
                p2_army_name = p2["army_name"]

            battle = Battle(
                points=parse_points(submissions.get("points")),
                army_1_id=p1_army_id,
                army_2_id=p2_army_id,
                army_1_name=p1_army_name,
                army_2_name=p2_army_name,
                result=result,
                patch=parse_patch(submissions.get("patch")),
                player_1_id=p1["player_id"],
                player_2_id=p2["player_id"],
                player_1_name=p1["player_name"],
                player_2_name=p2["player_name"],
                scenario=parse_scenario(row.get("Round Title"), tournament_dir, input_directory),
                tournament_id=tournament_id,
                tournament_name=row.get("Tournament Name"),
                tournament_type=parse_tournament_type(submissions.get("tournament_type")),
            )
            battles.append(battle)

    return battles


def import_battles(input_directory: str = INPUT_DIRECTORY, db_file: str = DB_FILE) -> list[Battle]:
    db = BattleDB(db_file)
    if not os.path.exists(input_directory):
        print(f"Directory {input_directory} does not exist.")
        return []

    for tournament_dir in os.listdir(input_directory):
        tournament_path = os.path.join(input_directory, tournament_dir)
        if os.path.isdir(tournament_path):
            csv_file = os.path.join(tournament_path, CSV_FILE)
            json_file = os.path.join(tournament_path, JSON_FILE)

            if os.path.exists(csv_file) and os.path.exists(json_file):
                battles = parse_battles(csv_file, json_file, tournament_dir, input_directory)
                print(f"Parsed {len(battles)} battles from {tournament_dir}.")
                db.battles.extend(battles)
            else:
                print(f"Missing CSV or JSON file in {tournament_dir}. Skipping.")

    db.save()
    print(f"Import finished. Database at {db_file} now contains {len(db.battles)} battles.")
    return db.battles


if __name__ == "__main__":
    import_battles()
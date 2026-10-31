import json
import csv
import os
import re
from battle import Battle, Points, Patch, TournamentType, Scenario
from db import BattleDB, DB_FILE


INPUT_DIRECTORY = "input"
CSV_FILE = "pairings_history.csv"
JSON_FILE = "submission_data.json"
SCENARIOS_FILE = "rounds.json"

INDIVIDUAL = "INDIVIDUAL"
DOUBLES = "DOUBLES"
TEAM = "TEAM"
# Team events where only the team result was recorded; no per-player battles can be derived.
TEAM_AGGREGATE = "TEAM_AGGREGATE"


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


def resolve_army(player: dict, use_secondary_list: bool | None) -> tuple[int | None, str | None]:
    second_army_id = player.get("second_army_id")
    if second_army_id is not None and use_secondary_list is True:
        return second_army_id, player["second_army_name"]
    if second_army_id is not None and use_secondary_list is None:
        return None, None
    return player["army_id"], player["army_name"]


def load_user_teams(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        (p.get("user") or {}).get("id"): p.get("teamId")
        for p in data.get("people") or []
        if p.get("user") and p.get("teamId")
    }


def _read_finished_rows(csv_path: str) -> list[dict]:
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.DictReader(f) if row.get("Round Status") == "FINISHED"]


def _team_groups(rows: list[dict], user_teams: dict) -> dict:
    """Group pairing rows of two different teams meeting in the same round."""
    groups = {}
    for row in rows:
        team_1 = user_teams.get(row.get("P1 User ID"))
        team_2 = user_teams.get(row.get("P2 User ID"))
        if not team_1 or not team_2 or team_1 == team_2:
            continue
        key = (row.get("Round ID"), frozenset((team_1, team_2)))
        groups.setdefault(key, []).append(row)
    return groups


def _oriented_scores(row: dict, user_teams: dict, first_team: str) -> tuple:
    scores_1 = (row.get("P1 Primary Points (TP)"), row.get("P1 Secondary Points (VP)"))
    scores_2 = (row.get("P2 Primary Points (TP)"), row.get("P2 Secondary Points (VP)"))
    if user_teams.get(row.get("P1 User ID")) == first_team:
        return scores_1 + scores_2
    return scores_2 + scores_1


DOUBLES_NAME_PATTERN = re.compile(r"\d+\s*x\s*\d+|doubles?|dubel", re.IGNORECASE)

# Temporary override: these tournaments always count as doubles, on top of automatic detection.
FORCED_DOUBLES_TOURNAMENTS = {
    "Middle-Earth SBG Turniej Master 'Zadyma na Południu' Parowy 2x500 pkt [STREFA]",
    "Dubelek w Matisofcie 2x350pkt",
    "Middle-Earth SBG Turniej Doubles - Parowy 2x500 pkt [STREFA]",
    "Turniej Middle-earth SBG - Kraków - Grudzień - Vanaheim - parowy",
    "MirkŁódź Turniej Lokalny DOUBLES Middle-Earth SBG - Grudzień 2025",
    "Turniej Middle Earth SBG Kielce- Grudzień  (Parówka)",
}


def _normalize_name(name: str | None) -> str:
    return " ".join((name or "").split()).casefold()


_FORCED_DOUBLES_NORMALIZED = {_normalize_name(n) for n in FORCED_DOUBLES_TOURNAMENTS}


def is_forced_doubles(tournament_name: str | None) -> bool:
    return _normalize_name(tournament_name) in _FORCED_DOUBLES_NORMALIZED


def classify_tournament(rows: list[dict], user_teams: dict, raw_points, tournament_name: str = "") -> str:
    """Returns INDIVIDUAL, DOUBLES, TEAM or TEAM_AGGREGATE (team event without per-player results)."""
    groups = _team_groups(rows, user_teams)
    if not groups:
        return INDIVIDUAL

    points = parse_points(raw_points)
    if (
        (points is not None and points.doubled)
        or is_forced_doubles(tournament_name)
        or DOUBLES_NAME_PATTERN.search(tournament_name or "")
    ):
        return DOUBLES

    # Teammates sharing exactly the same score against the same team means only the team result was recorded
    mirrored = 0
    total = 0
    for (_, teams), group_rows in groups.items():
        first_team = sorted(teams)[0]
        total += len(group_rows)
        if len(group_rows) >= 2 and len({_oriented_scores(r, user_teams, first_team) for r in group_rows}) == 1:
            mirrored += len(group_rows)
    return TEAM_AGGREGATE if mirrored / total >= 0.5 else TEAM


def _row_player_flags(row: dict) -> dict:
    flags = {}
    for side in ("P1", "P2"):
        raw = row.get(f"{side} Use Secondary List")
        flags[row.get(f"{side} User ID")] = True if raw == "True" else False if raw == "False" else None
    return flags


def doubles_points(raw_points, tournament_name: str) -> Points | None:
    points = parse_points(raw_points)
    if points is not None and points.doubled:
        return points
    match = re.search(r"(\d+)\s*x\s*(\d+)", tournament_name or "", re.IGNORECASE)
    if match and match.group(1) == "2":
        return Points(value=int(match.group(2)), doubled=True)
    return points


def _team_army(submissions: dict, user_ids: list[str]) -> tuple[int, str] | None:
    """Partners play one shared list, but the site does not record which one.
    The army is known only if all lists of the team are the same army."""
    armies = set()
    for uid in user_ids:
        player = submissions[uid]
        armies.add((player["army_id"], player["army_name"]))
        if player.get("second_army_id") is not None:
            armies.add((player["second_army_id"], player["second_army_name"]))
    return armies.pop() if len(armies) == 1 else None


def parse_doubles_battles(rows: list[dict], submissions: dict, user_teams: dict, tournament_dir: str, input_directory: str) -> list[Battle]:
    """Every player of one team gets a battle against every player of the opposing team."""
    battles = []
    for (_, teams), group_rows in _team_groups(rows, user_teams).items():
        first_team, second_team = sorted(teams)
        scores = {_oriented_scores(r, user_teams, first_team) for r in group_rows}
        if len(scores) != 1:
            print(f"WARNING: inconsistent doubles result in {tournament_dir}")
            continue
        _, vp_1, _, vp_2 = scores.pop()
        result = parse_result({"P1 Secondary Points (VP)": vp_1, "P2 Secondary Points (VP)": vp_2})
        if result is None:
            continue

        flags = {}
        for r in group_rows:
            flags.update(_row_player_flags(r))
        team_players = {
            team: sorted(uid for uid in flags if user_teams.get(uid) == team and uid in submissions)
            for team in (first_team, second_team)
        }

        team_armies = {team: _team_army(submissions, team_players[team]) for team in team_players}
        if any(army is None for army in team_armies.values()):
            continue

        first_row = group_rows[0]
        for uid_1 in team_players[first_team]:
            for uid_2 in team_players[second_team]:
                p1, p2 = submissions[uid_1], submissions[uid_2]
                army_1_id, army_1_name = team_armies[first_team]
                army_2_id, army_2_name = team_armies[second_team]
                battles.append(Battle(
                    points=doubles_points(submissions.get("points"), first_row.get("Tournament Name")),
                    army_1_id=army_1_id,
                    army_2_id=army_2_id,
                    army_1_name=army_1_name,
                    army_2_name=army_2_name,
                    result=result,
                    patch=parse_patch(submissions.get("patch")),
                    player_1_id=p1["player_id"],
                    player_2_id=p2["player_id"],
                    player_1_name=p1["player_name"],
                    player_2_name=p2["player_name"],
                    scenario=parse_scenario(first_row.get("Round Title"), tournament_dir, input_directory),
                    tournament_id=first_row.get("Tournament ID"),
                    tournament_name=first_row.get("Tournament Name"),
                    tournament_type=parse_tournament_type(submissions.get("tournament_type")),
                    format=DOUBLES,
                ))
    return battles


def get_tournament_kind(csv_path: str, json_path: str) -> str:
    rows = _read_finished_rows(csv_path)
    return classify_tournament(
        rows,
        load_user_teams(json_path),
        load_submissions(json_path).get("points"),
        rows[0].get("Tournament Name") if rows else "",
    )


def parse_battles(csv_path: str, json_path: str, tournament_dir: str, input_directory: str = INPUT_DIRECTORY) -> list[Battle]:
    submissions = load_submissions(json_path)
    battles = []

    if parse_tournament_type(submissions.get("tournament_type")) is None:
        return []

    rows = _read_finished_rows(csv_path)
    user_teams = load_user_teams(json_path)
    kind = classify_tournament(
        rows, user_teams, submissions.get("points"), rows[0].get("Tournament Name") if rows else ""
    )
    if kind == TEAM_AGGREGATE:
        return []
    if kind == DOUBLES:
        return parse_doubles_battles(rows, submissions, user_teams, tournament_dir, input_directory)

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

            p1_army_id, p1_army_name = resolve_army(p1, p1_use_secondary_list)
            p2_army_id, p2_army_name = resolve_army(p2, p2_use_secondary_list)

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
                format=kind,
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
                kind = "NO_TOURNAMENT_TYPE" if parse_tournament_type(load_submissions(json_file).get("tournament_type")) is None else get_tournament_kind(csv_file, json_file)
                battles = parse_battles(csv_file, json_file, tournament_dir, input_directory)
                print(f"Parsed {len(battles)} battles from {tournament_dir} [{kind}].")
                db.battles.extend(battles)
            else:
                print(f"Missing CSV or JSON file in {tournament_dir}. Skipping.")

    db.save()
    print(f"Import finished. Database at {db_file} now contains {len(db.battles)} battles.")
    return db.battles


if __name__ == "__main__":
    import_battles()
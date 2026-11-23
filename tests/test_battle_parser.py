import csv
import json

from battle import TournamentType
from battle_parser import TEAM, TEAM_AGGREGATE, classify_tournament, get_tournament_kind, import_battles, parse_battles
from pages.stats_filters import battle_matches_filters
from store import load_tournament_results


def _write_tournament_files(tmp_path, overrides):
    tournament_id = "tournament-1"
    submissions = {
        "tournament_type": "LOKAL",
        "points": "500",
        "people": [
            {
                "status": "APPROVED",
                "user": {"id": player_id, "displayName": player_id},
                "teamId": team_id,
                "army": {"id": army_id, "name": army_name},
            }
            for player_id, team_id, army_id, army_name in (
                ("a1", "team-a", 1, "Army A1"),
                ("a2", "team-a", 2, "Army A2"),
                ("b1", "team-b", 3, "Army B1"),
                ("b2", "team-b", 4, "Army B2"),
            )
        ],
    }
    (tmp_path / "submission_data.json").write_text(json.dumps(submissions), encoding="utf-8")
    (tmp_path / "manual_battle_overrides.json").write_text(
        json.dumps({"tournaments": overrides}), encoding="utf-8"
    )

    rows = []
    for table_id, p1, p2 in (("table-1", "a1", "b1"), ("table-2", "a2", "b2")):
        rows.append({
            "Tournament ID": tournament_id,
            "Round ID": "round-1",
            "Round Title": "Round 1",
            "Round Status": "FINISHED",
            "Table ID": table_id,
            "P1 User ID": p1,
            "P2 User ID": p2,
            "P1 Primary Points (TP)": "1",
            "P2 Primary Points (TP)": "0",
            "P1 Secondary Points (VP)": "2",
            "P2 Secondary Points (VP)": "0",
            "P1 Use Secondary List": "False",
            "P2 Use Secondary List": "False",
        })
    csv_path = tmp_path / "pairings_history.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return csv_path, tmp_path / "submission_data.json", tournament_id, rows


def test_manual_tournament_battles_override_aggregate_classification(tmp_path):
    tournament_id = "tournament-1"
    overrides = {
        tournament_id: {
            "battles": [{
                "table_id": "table-1",
                "result": [7, 3],
                "army_1_id": 31,
                "army_1_name": "Corrected Army 1",
                "army_2_id": 32,
                "army_2_name": "Corrected Army 2",
            }]
        }
    }
    csv_path, submissions_path, _, rows = _write_tournament_files(tmp_path, overrides)
    submissions = json.loads(submissions_path.read_text(encoding="utf-8"))
    teams = {person["user"]["id"]: person["teamId"] for person in submissions["people"]}
    assert classify_tournament(rows, teams, "500", "Team event") == TEAM_AGGREGATE

    battles = parse_battles(
        str(csv_path),
        str(submissions_path),
        str(tmp_path.name),
        str(tmp_path),
    )

    assert len(battles) == 1
    assert battles[0].format == "INDIVIDUAL"
    assert battles[0].result == (7, 3)
    assert battles[0].army_1_name == "Corrected Army 1"
    assert battles[0].army_2_name == "Corrected Army 2"


def test_reimport_replaces_corrected_and_removed_battles(tmp_path):
    tournament_dir = tmp_path / "event"
    tournament_dir.mkdir()
    overrides = {"tournament-1": {"battles": [
        {"table_id": "table-1", "result": [7, 3]},
        {"table_id": "table-2", "result": [5, 1]},
    ]}}
    _write_tournament_files(tournament_dir, overrides)
    config_path = tmp_path / "manual_battle_overrides.json"
    config_path.write_text(json.dumps({"tournaments": overrides}), encoding="utf-8")
    db_path = tmp_path / "battles.json"

    import_battles(str(tmp_path), str(db_path))
    overrides["tournament-1"]["battles"] = [{"table_id": "table-1", "result": [2, 4]}]
    config_path.write_text(json.dumps({"tournaments": overrides}), encoding="utf-8")
    import_battles(str(tmp_path), str(db_path))

    saved = json.loads(db_path.read_text(encoding="utf-8"))
    assert len(saved) == 1
    assert saved[0]["result"] == [2, 4]


def test_dmp_uses_individual_tertiary_scores_even_for_mirrored_team_results(tmp_path):
    csv_path, submissions_path, _, rows = _write_tournament_files(tmp_path, {})
    submissions = json.loads(submissions_path.read_text(encoding="utf-8"))
    submissions["tournament_type"] = "DMP"
    submissions_path.write_text(json.dumps(submissions), encoding="utf-8")
    rows[0].update({"P1 Tertiary Points": "2", "P2 Tertiary Points": "9"})
    rows[1].update({"P1 Tertiary Points": "3", "P2 Tertiary Points": "3"})
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    battles = parse_battles(str(csv_path), str(submissions_path), "event", str(tmp_path), {})
    assert [b.result for b in battles] == [(2, 9), (3, 3)]
    assert get_tournament_kind(str(csv_path), str(submissions_path)) == TEAM
    assert all(b.tournament_type == TournamentType.MASTER and b.format == "TEAM" for b in battles)
    battle = battles[0].to_dict()
    battle["patch"] = "BALROG"
    assert battle_matches_filters(battle, [0, 1000], ["Masters"], ["Balrog Age"], ["Team"])
    assert not battle_matches_filters(battle, [0, 1000], ["Locals"], ["Balrog Age"], ["Team"])
    manual = {"tournament-1": {"battles": [{"table_id": "table-1"}]}}
    assert parse_battles(str(csv_path), str(submissions_path), "event", str(tmp_path), manual)[0].result == (2, 9)

    rows[0]["P1 Tertiary Points"] = ""
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    battles = parse_battles(str(csv_path), str(submissions_path), "event", str(tmp_path), {})
    assert [b.result for b in battles] == [(3, 3)]


def test_ineligible_events_removed_from_existing_battles_and_tournament_results(tmp_path):
    event = tmp_path / "event"
    event.mkdir()
    _write_tournament_files(event, {})
    submission_path = event / "submission_data.json"
    submission = json.loads(submission_path.read_text(encoding="utf-8"))
    for person in submission["people"]:
        person.pop("teamId")
    submission["people"][0]["finalResult"] = {"place": 1, "wins": 1}
    submission_path.write_text(json.dumps(submission), encoding="utf-8")
    db_path = tmp_path / "battles.json"
    import_battles(str(tmp_path), str(db_path), {"tournament-1"})
    assert json.loads(db_path.read_text(encoding="utf-8"))
    assert load_tournament_results(str(tmp_path), eligible_ids={"tournament-1"})

    import_battles(str(tmp_path), str(db_path), set())
    assert json.loads(db_path.read_text(encoding="utf-8")) == []
    assert load_tournament_results(str(tmp_path), eligible_ids=set()) == {}
    assert submission_path.exists()

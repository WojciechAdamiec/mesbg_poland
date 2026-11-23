import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from download_data import (
    DATA_DIRECTORY,
    MAIN_RANKING_FILE,
    MAIN_RANKING_2027_FILE,
    ONLINE_RANKING_FILE,
    ONLINE_RANKING_2027_FILE,
    MASTER_RANKING_FILE,
    MASTER_RANKING_2027_FILE,
    MASTER_TOURNAMENTS_FILE,
    BATTLES_FILE,
    ARMIES_FILE,
    PLAYER_PROFILES_FILE,
    TOURNAMENTS_FILE,
    PLAYER_CITIES_FILE,
    INPUT_DIRECTORY,
    JSON_FILE,
)
from battle import TournamentType
from battle_parser import (
    CSV_FILE, INDIVIDUAL, TEAM, parse_tournament_type,
    saved_eligible_tournament_ids, tournament_input_id,
)


@lru_cache(maxsize=32)
def _read_json(path, modified_ns, size):
    stat = os.stat(path)
    if stat.st_mtime_ns != modified_ns or stat.st_size != size:
        return _load_json(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_json(path):
    stat = os.stat(path)
    return _read_json(os.fspath(path), stat.st_mtime_ns, stat.st_size)


def load_main_ranking():
    main_ranking_path = os.path.join(DATA_DIRECTORY, MAIN_RANKING_FILE)
    if not os.path.exists(main_ranking_path):
        return []
    return _load_json(main_ranking_path)


def load_main_ranking_2027():
    path = os.path.join(DATA_DIRECTORY, MAIN_RANKING_2027_FILE)
    if not os.path.exists(path):
        return []
    return _load_json(path)


def load_online_ranking():
    online_ranking_path = os.path.join(DATA_DIRECTORY, ONLINE_RANKING_FILE)
    if not os.path.exists(online_ranking_path):
        return []
    return _load_json(online_ranking_path)


def load_master_ranking():
    master_ranking_path = os.path.join(DATA_DIRECTORY, MASTER_RANKING_FILE)
    if not os.path.exists(master_ranking_path):
        return []
    return _load_json(master_ranking_path)


def load_master_ranking_2027():
    path = os.path.join(DATA_DIRECTORY, MASTER_RANKING_2027_FILE)
    if not os.path.exists(path):
        return []
    return _load_json(path)


def load_online_ranking_2027():
    path = os.path.join(DATA_DIRECTORY, ONLINE_RANKING_2027_FILE)
    if not os.path.exists(path):
        return []
    return _load_json(path)


def load_master_tournaments():
    master_tournaments_path = os.path.join(DATA_DIRECTORY, MASTER_TOURNAMENTS_FILE)
    if not os.path.exists(master_tournaments_path):
        return []
    return _load_json(master_tournaments_path)


def load_battles():
    battles_path = os.path.join(DATA_DIRECTORY, BATTLES_FILE)
    if not os.path.exists(battles_path):
        return []
    return _load_json(battles_path)


def load_armies():
    armies_path = os.path.join(DATA_DIRECTORY, ARMIES_FILE)
    if not os.path.exists(armies_path):
        return []
    return _load_json(armies_path)

def load_player_profiles():
    path = os.path.join(DATA_DIRECTORY, PLAYER_PROFILES_FILE)
    if not os.path.exists(path):
        return []
    return _load_json(path)


def load_tournaments():
    """Load tournament towns and ranked participant IDs, or raise if not downloaded."""
    path = os.path.join(DATA_DIRECTORY, TOURNAMENTS_FILE)
    return _load_json(path)


def load_player_cities():
    """Load last known player towns keyed by player ID, or raise if not downloaded."""
    path = os.path.join(DATA_DIRECTORY, PLAYER_CITIES_FILE)
    return _load_json(path)


def load_nations_cup_2027_player_ids():
    path = Path(DATA_DIRECTORY) / "hall_of_fame_nations_cup_2027.json"
    with path.open(encoding="utf-8") as file:
        teams = json.load(file)["teams"]
    player_ids = set()
    for team in teams:
        for player in team["players"]:
            player_id = player["player_id"]
            if player_id is not None:
                if not isinstance(player_id, str) or not player_id:
                    raise ValueError(f"Invalid Nations Cup player_id in {path}: {player_id!r}")
                player_ids.add(player_id)
    return player_ids


@dataclass(frozen=True)
class TournamentWin:
    tournament_type: TournamentType | None
    format: str


@dataclass
class PlayerTournamentResults:
    wins: set[TournamentWin] = field(default_factory=set)
    lost_all: bool = False
    events: dict[TournamentType, int] = field(default_factory=dict)
    veggie_alpha: bool = False
    win_counts: dict[TournamentType, int] = field(default_factory=dict)
    win_format_counts: dict[str, int] = field(default_factory=dict)
    lost_all_count: int = 0


def load_tournament_results(input_directory=INPUT_DIRECTORY, main_ranking=None, eligible_ids=None,
                            rankings_by_season=None):
    """Index tournament participation, wins, all-loss results, and qualifying Veggie Alpha wins."""
    players = {}
    check_veggie = rankings_by_season is not None or main_ranking is not None
    if rankings_by_season is None:
        rankings_by_season = {2026: main_ranking} if main_ranking is not None else {}
    top_50_by_season = {
        season: {
            player["player_id"]
            for player in ranking
            if player.get("player_id") and player.get("place") is not None and 1 <= player["place"] <= 50
        }
        for season, ranking in rankings_by_season.items() if ranking
    }
    warned_seasons = set()
    directory = Path(input_directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"Tournament input directory not found: {directory}")
    if eligible_ids is None and input_directory == INPUT_DIRECTORY:
        eligible_ids = saved_eligible_tournament_ids()
    for path in directory.glob(f"*/{JSON_FILE}"):
        if eligible_ids is not None and tournament_input_id(str(path), str(path.parent / CSV_FILE)) not in eligible_ids:
            continue
        with path.open(encoding="utf-8") as f:
            submission = json.load(f)
        tournament_type = parse_tournament_type(submission.get("tournament_type"))
        if tournament_type is None:
            continue
        season = submission.get("season", 2026)
        top_50_players = top_50_by_season.get(season)
        if check_veggie and top_50_players is None and season not in warned_seasons:
            print(f"WARNING: No {season} ranking available; Veggie Alpha cannot be evaluated for that season.")
            warned_seasons.add(season)
        teams = submission.get("teams") or []
        winning_teams = {
            team["id"] for team in teams
            if (team.get("finalResult") or {}).get("place") == 1
        }
        participants = set()
        tournament_players = set()
        winners = {}
        all_loss_players = set()
        for person in submission.get("people", []):
            player_id = (person.get("user") or {}).get("id")
            result = person.get("finalResult") or {}
            if not player_id:
                continue
            if result.get("place"):
                tournament_players.add(player_id)
            if result.get("place") and tournament_type is not None and player_id not in participants:
                player_results = players.setdefault(player_id, PlayerTournamentResults())
                player_results.events[tournament_type] = player_results.events.get(tournament_type, 0) + 1
                participants.add(player_id)
            if result.get("wins") == 0 and result.get("draws") == 0 and (result.get("loss") or 0) > 0:
                all_loss_players.add(player_id)
            if result.get("place") == 1:
                if teams:
                    if person.get("teamId") not in winning_teams:
                        continue
                    tournament_format = TEAM
                else:
                    tournament_format = INDIVIDUAL
                winners[player_id] = tournament_format
                players.setdefault(player_id, PlayerTournamentResults()).wins.add(TournamentWin(
                    tournament_type, tournament_format
                ))
        for player_id in all_loss_players:
            player_results = players.setdefault(player_id, PlayerTournamentResults())
            player_results.lost_all = True
            player_results.lost_all_count += 1
        for winner, tournament_format in winners.items():
            player_results = players.setdefault(winner, PlayerTournamentResults())
            if tournament_type is not None:
                player_results.win_counts[tournament_type] = player_results.win_counts.get(tournament_type, 0) + 1
            player_results.win_format_counts[tournament_format] = (
                player_results.win_format_counts.get(tournament_format, 0) + 1
            )
            if top_50_players is not None and not (tournament_players - {winner}) & top_50_players:
                player_results.veggie_alpha = True
    return players

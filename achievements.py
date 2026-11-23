"""Recalculate stored achievements with ``python achievements.py``."""

import json
import os
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from battle import TournamentType
from battle_parser import INDIVIDUAL, TEAM
from download_data import DATA_DIRECTORY, PLAYER_PROFILES_FILE, save_data
from player_profile_stats import ArmyExpertise, seasonal_trophies, unique_trophy_players
from store import (
    PlayerTournamentResults,
    load_armies,
    load_battles,
    load_main_ranking,
    load_main_ranking_2027,
    load_nations_cup_2027_player_ids,
    load_player_cities,
    load_tournament_results,
    load_tournaments,
)
from tags import get_tag, load_tags


@dataclass(frozen=True)
class Achievement:
    name: str
    text: str
    icon: str
    condition: Callable[[dict, PlayerTournamentResults], bool]
    progress: Callable[[dict], int] | None = None
    target: int | None = None
    stages: tuple[int, ...] = ()
    stage_texts: tuple[str, ...] = ()
    progress_unit: str = ""
    stage_labels: tuple[str, ...] = ()
    show_progress: bool = True

    def __post_init__(self):
        if self.stages and (
            self.progress is None or any(target <= 0 for target in self.stages)
            or any(first >= second for first, second in zip(self.stages, self.stages[1:]))
        ):
            raise ValueError(f"Achievement {self.name} requires progress and increasing positive stage targets")
        if self.stage_texts and (not self.stages or len(self.stage_texts) != len(self.stages)):
            raise ValueError(f"Achievement {self.name} requires one description per stage")
        if self.stage_labels and (not self.stages or len(self.stage_labels) != len(self.stages)):
            raise ValueError(f"Achievement {self.name} requires one label per stage")

    @property
    def stage_count(self):
        return len(self.stages) if self.stages else 1

    def text_for_stage(self, stage):
        if not self.stage_texts:
            return self.text
        return self.stage_texts[min(stage or 0, len(self.stage_texts) - 1)]


def _threshold_achievement(name, text, target, progress):
    return Achievement(
        name, text, "achievement.png",
        lambda player, results: progress(player) >= target,
        progress, target,
    )


def _staged_achievement(
    name, text, stages, progress, *, stage_texts=(), progress_unit="", stage_labels=(), show_progress=True,
):
    if not stages:
        raise ValueError(f"Achievement {name} requires at least one stage")
    return Achievement(
        name, text, "achievement.png",
        lambda player, results: progress({**player, "_tournament_results": results}) >= stages[0],
        progress, stages[-1], tuple(stages), tuple(stage_texts), progress_unit, tuple(stage_labels), show_progress,
    )


def _milestone_achievement(name, stages, description, progress, *, progress_unit=""):
    stage_texts = tuple(description(target) for target in stages)
    return _staged_achievement(
        name, stage_texts[0], stages, progress,
        stage_texts=stage_texts, progress_unit=progress_unit,
    )


def total_achievement_stages(definitions):
    return sum(achievement.stage_count for achievement in definitions)


def achievement_stage(achievement, unlocked, progress_by_name):
    if achievement.stage_count == 1:
        return int(achievement.name in unlocked)
    progress = (progress_by_name or {}).get(achievement.name)
    if progress is None or "stage" not in progress:
        return None
    stage = progress["stage"]
    if type(stage) is not int or not 0 <= stage <= achievement.stage_count:
        raise ValueError(f"Invalid stage for achievement {achievement.name}: {stage}")
    return stage


def unlocked_stage_count(definitions, unlocked, progress_by_name):
    stages = [achievement_stage(achievement, unlocked, progress_by_name) for achievement in definitions]
    return None if any(stage is None for stage in stages) else sum(stages)


def _city_achievement(name, text, *cities):
    return _threshold_achievement(
        name, text, 5,
        lambda player: _defeated_players_in_cities(player, player["_player_cities"], cities),
    )


def _place_tag_achievement(name, text, tag_id):
    place_ids = set(get_tag("places", tag_id).items)
    return _threshold_achievement(
        name, text, 5,
        lambda player: _defeated_players_in_places(player, player["_player_cities"], place_ids),
    )


ARMY_ACHIEVEMENT_NAMES = {
    "rohan": ("Muster the Rohirrim!", "Burn the Westfold"),
    "gondor": ("Gondor Needs no King", "King needed after all"),
    "isengard": ("Leave none alive!", "Unhanded"),
    "mordor": ("Do you not know Death?", "Eye Sore"),
    "moria": ("Light Not Included", "Mine Your Own Business"),
    "evil-north": ("Relentless March South", "Cold Reception"),
    "evil-men": ("No Glory in Pointless Defeat", "It's Treason Then"),
    "elves": ("Chosen by Valars", "Not Really Immortal"),
    "dwarves": ("Hold my Beer", "Beard Trimmer"),
    "hobbits": ("Small Victories", "Shoes Required"),
    "monsters": ("I kill when I wish", "Big Game Hunter"),
    "wizards": ("Staff Meeting", "There is no Light"),
    "hero-armies": ("Plot Armour Supplier", "We've been made Equal"),
    "good-men": ("Oath Fulfilled", "Moral Superiority"),
}


def _army_tag_achievement(tag, wins_with):
    army_ids = set(tag.items)
    army_field = "army_lists" if wins_with else "opponent_army_lists"
    preposition = "with" if wins_with else "against"
    name = ARMY_ACHIEVEMENT_NAMES[tag.id][0 if wins_with else 1]
    return _milestone_achievement(
        name, (5, 10, 15),
        lambda target: f"Win at least {target} games {preposition} [[tag:army_lists:{tag.id}]].",
        lambda player: sum(
            army.get("wins", 0)
            for army in player.get(army_field, [])
            if army.get("army_id") in army_ids
        ),
    )


def _player_tag_achievement(name, text, tag_id):
    player_ids = set(get_tag("players", tag_id).items)
    return Achievement(
        name, text, "achievement.png",
        lambda player, results: player.get("player_id") in player_ids or any(
            opponent.get("player_id") in player_ids and opponent.get("wins", 0) > 0
            for opponent in player.get("opponents", [])
        ),
    )


def _is_orku_slayer(player):
    def is_orku(name):
        return (name or "").strip().casefold() == "orkuorku"

    return is_orku(player.get("displayName")) or any(
        is_orku(opponent.get("displayName")) and opponent["wins"] > 0
        for opponent in player.get("opponents", [])
    )


def _normalize_city_name(name):
    normalized = unicodedata.normalize("NFKD", (name or "").strip().casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _defeated_players_in_cities(player, player_cities, target_cities):
    target_names = {_normalize_city_name(city) for city in target_cities}
    defeated = set()
    for opponent in player.get("opponents", []):
        opponent_id = opponent.get("player_id")
        if not opponent_id or opponent.get("wins", 0) <= 0:
            continue
        city = player_cities.get(opponent_id) or {}
        city_name = _normalize_city_name(city.get("name"))
        if city_name in target_names:
            defeated.add(opponent_id)
    return len(defeated)


def _defeated_players_in_places(player, player_cities, place_ids):
    defeated = set()
    for opponent in player.get("opponents", []):
        opponent_id = opponent.get("player_id")
        if not opponent_id or opponent.get("wins", 0) <= 0:
            continue
        city = player_cities.get(opponent_id) or {}
        if city.get("id") in place_ids:
            defeated.add(opponent_id)
    return len(defeated)


def _same_city(first, second):
    first_id, second_id = first.get("city_id"), second.get("city_id")
    if first_id is not None and second_id is not None:
        return first_id == second_id
    return (
        _normalize_city_name(first.get("city_name")) != ""
        and _normalize_city_name(first.get("city_name")) == _normalize_city_name(second.get("city_name"))
        and _normalize_city_name(first.get("city_country")) == _normalize_city_name(second.get("city_country"))
    )


def _is_best_player_in_city(player_id, main_ranking):
    ranking_by_id = {player.get("player_id"): player for player in main_ranking if player.get("player_id")}
    player = ranking_by_id.get(player_id)
    if not player or player.get("place") is None or (
        player.get("city_id") is None and not player.get("city_name")
    ):
        return False
    same_city_places = [
        rival["place"]
        for rival in main_ranking
        if rival.get("place") is not None and _same_city(player, rival)
    ]
    return bool(same_city_places) and player["place"] == min(same_city_places)


def _different_armies_played(player):
    return len({
        army.get("army_id")
        for army in player.get("army_lists", [])
        if army.get("army_id") is not None and army.get("games", 0) > 0
    })


# Add achievements here; conditions receive the player profile and tournament results.
BASE_ACHIEVEMENTS = (
    *(
        _milestone_achievement(
            name, (1, 3, 5),
            lambda target, label=label: f"Win {target} {label} tournament{'s' if target != 1 else ''}.",
            lambda player, kind=kind: player["_tournament_results"].win_counts.get(kind, 0),
        )
        for name, label, kind in (
            ("King of the Neighbourhood", "Local", TournamentType.LOCAL),
            ("Challenge Accepted", "Challenger", TournamentType.CHALLENGER),
            ("The Big Fish", "Master", TournamentType.MASTER),
            ("Virtually Unstoppable", "Online", TournamentType.ONLINE),
        )
    ),
    Achievement("Ultimate Champion", "Win a Local, a Challenger, a Master and an Online tournament.", "achievement.png",
                lambda player, results: {
                    TournamentType.LOCAL, TournamentType.CHALLENGER, TournamentType.MASTER, TournamentType.ONLINE
                }.issubset({win.tournament_type for win in results.wins})),
    *(
        _milestone_achievement(
            name, (1, 3, 5),
            lambda target, label=label: f"Win {target} {label} tournament{'s' if target != 1 else ''}.",
            lambda player, kind=kind: player["_tournament_results"].win_format_counts.get(kind, 0),
        )
        for name, label, kind in (
            ("One-Man Army", "individual", INDIVIDUAL),
            ("Power of Friendship", "pair or team", TEAM),
        )
    ),
    Achievement("Eggplant Among Veggies", "Win a tournament with no good players.", "achievement.png",
                lambda player, results: results.veggie_alpha),
    _milestone_achievement(
        "Consolation Prize", (1, 3, 5),
        lambda target: f"Lose all games in {target} tournament{'s' if target != 1 else ''}.",
        lambda player: player["_tournament_results"].lost_all_count,
    ),
    _staged_achievement(
        "War Veteran", "Play 30 games.", (30, 50, 80, 120, 200),
        lambda player: player.get("games_played", 0),
        stage_texts=("Play 30 games.", "Play 50 games.", "Play 80 games.",
                     "Play 120 games.", "Play 200 games."),
    ),
    _milestone_achievement("Ah, Yes. The Negotiator", (5, 10, 15),
                           lambda target: f"Draw at least {target} games.",
                           lambda player: player["draws"]),
    _threshold_achievement("Jack of All Trades", "Earn at least 10 army specialties.", 10,
                           lambda player: player.get("_army_specialty_count", 0)),
    _threshold_achievement("Master Tactician", "Be the best player of an army list.", 1,
                           lambda player: player.get("_number_one_specialty_count", 0)),
    _milestone_achievement("Shapeshifter", (10, 20, 30),
                           lambda target: f"Play battles with at least {target} different armies.",
                           lambda player: player.get("_different_armies_played", 0)),
    _threshold_achievement("Headhunter", "Collect at least 10 top player trophies.", 10,
                           lambda player: player.get("_player_trophy_count", 0)),
    _threshold_achievement("Beat the Unbeatable", "Defeat at least 3 players ranked in the top 10.", 3,
                           lambda player: player.get("_top_ten_trophy_count", 0)),
    Achievement("Orku Slayer", "Defeat OrkuOrku or be OrkuOrku.", "achievement.png",
                lambda player, results: _is_orku_slayer(player)),
    Achievement("Discorded", "Link a Discord account to your ChampionsHub account.", "achievement.png",
                lambda player, results: player.get("discord_linked", False)),
    _milestone_achievement("Strider", (5, 10, 15),
                           lambda target: f"Play tournaments in at least {target} different locations.",
                           lambda player: player["locations_count"]),
    Achievement("Center's Frontman", "Be the best player in your city at the end of a season.", "achievement.png",
                lambda player, results: player.get("_is_best_player_in_city", False)),
    _player_tag_achievement(
        "Vox populi, vox Dei",
        "Be or beat one of the [[tag:players:representatives]].",
        "representatives",
    ),
    _player_tag_achievement(
        "If you can't beat Them, join Them",
        "Be or beat one of the [[tag:players:coordinators]].",
        "coordinators",
    ),
    _city_achievement("Potato Peeler", "Defeat at least 5 different players from Poznań.", "Poznań"),
    _city_achievement("Rat Catcher", "Defeat at least 5 different players from Wrocław.", "Wrocław"),
    _place_tag_achievement(
        "Age of Coal is Over",
        "Defeat at least 5 different players from [[tag:places:silesia]].",
        "silesia",
    ),
    _city_achievement("Capital Punishment", "Defeat at least 5 different players from Warszawa.", "Warszawa"),
    _place_tag_achievement(
        "Can Opener",
        "Defeat at least 5 different players from [[tag:places:galicia]].",
        "galicia",
    ),
    _city_achievement("Dragon Slayer", "Defeat at least 5 different players from Kraków.", "Kraków"),
    _city_achievement("Go back to Bałuty", "Defeat at least 5 different players from Łódź.", "Łódź"),
    _place_tag_achievement(
        "Drunken Sailor",
        "Defeat at least 5 different players from [[tag:places:tricity]].",
        "tricity",
    ),
    _city_achievement(
        "The Gingerbread Must Flow",
        "Defeat at least 5 different players from either Bydgoszcz or Toruń.",
        "Bydgoszcz", "Toruń",
    ),
    _city_achievement("Adults Only", "Defeat at least 5 different players from Bielsko-Biała.", "Bielsko-Biała"),
    _city_achievement("Mayonnaise Enjoyer", "Defeat at least 5 different players from Kielce.", "Kielce"),
    *(_army_tag_achievement(tag, wins_with)
      for tag in load_tags("army_lists") for wins_with in (True, False)),
    _staged_achievement(
        "Primus Inter Pares", "Finish a season in the top 50 of the main ranking.", (1, 2, 3),
        lambda player: player["_season_ranking_stage"],
        stage_texts=(
            "Finish a season in the top 50 of the main ranking.",
            "Finish a season in the top 30 of the main ranking.",
            "Finish a season in the top 10 of the main ranking.",
        ),
        stage_labels=("Top 50", "Top 30", "Top 10"),
        show_progress=False,
    ),
    Achievement(
        "Poland Strong", "Be a member of an official Polish team at an international event.", "achievement.png",
        lambda player, results: player["player_id"] in player["_nations_cup_player_ids"],
    ),
)

COMPLETION_ACHIEVEMENTS = (
    _milestone_achievement(
        "Hoarding Instincts", tuple(range(10, 101, 10)),
        lambda target: f"Unlock at least {target}% of non-completion achievements.",
        lambda player: player["_base_achievement_count"] * 100 // player["_base_achievement_total"],
        progress_unit="%",
    ),
)
ACHIEVEMENTS = BASE_ACHIEVEMENTS + COMPLETION_ACHIEVEMENTS

PLAYER_RANKS = (
    ("Leaf", 0, "#84cc16"),
    ("Wooden", 10, "#a07855"),
    ("Stone", 20, "#a8a29e"),
    ("Copper", 30, "#c77c52"),
    ("Bronze", 40, "#cd7f32"),
    ("Iron", 50, "#94a3b8"),
    ("Silver", 60, "#e2e8f0"),
    ("Gold", 70, "#eab308"),
    ("Emerald", 80, "#34d399"),
    ("Mithril", 100, "#e0f2fe"),
)


def rank_index_for_count(count, total):
    return max(
        index for index, (_, threshold, _) in enumerate(PLAYER_RANKS)
        if count * 100 >= threshold * total
    )


def format_achievement_count(count):
    if count is None:
        return "-"
    total = total_achievement_stages(ACHIEVEMENTS)
    name = PLAYER_RANKS[rank_index_for_count(count, total)][0]
    return f"{name} ({count}/{total} {count * 100 / total:.1f}%)"


def player_locations_by_id(tournaments):
    """Index distinct tournament locations by player, including the ONLINE location."""
    locations = {}
    for tournament in tournaments:
        city = tournament.get("city") or {}
        name = (city.get("name") or "").strip()
        participants = tournament.get("player_ids")
        if not name or participants is None:
            raise ValueError(f"Tournament {tournament['tournament_id']} has incomplete location or participant data")
        city_id = city.get("id")
        key = ("id", city_id) if city_id is not None else ("name", name.casefold(), city.get("country"))
        for player_id in participants:
            locations.setdefault(player_id, {})[key] = name
    return {
        player_id: sorted(names.values(), key=lambda name: (name.casefold() == "online", name.casefold()))
        for player_id, names in locations.items()
    }


def calculate_achievements(
    profiles, tournament_results, tournaments, *, main_ranking=None, battles=None, armies=None, player_cities=None,
    rankings_by_season=None, nations_cup_player_ids=None,
):
    """Return profiles with fresh locations, achievement names, counts, and threshold progress."""
    main_ranking = main_ranking or []
    player_cities = player_cities or {}
    if rankings_by_season is None:
        rankings_by_season = {2026: main_ranking}
    if nations_cup_player_ids is None:
        nations_cup_player_ids = load_nations_cup_2027_player_ids()
    best_ranking_places = {}
    for ranking in rankings_by_season.values():
        for player in ranking:
            player_id, place = player.get("player_id"), player.get("place")
            if player_id and type(place) is int and place > 0:
                best_ranking_places[player_id] = min(place, best_ranking_places.get(player_id, place))
    trophies_by_player = seasonal_trophies(battles or [], rankings_by_season)
    expertise = ArmyExpertise(battles or [], main_ranking, armies or [])
    locations_by_player = player_locations_by_id(tournaments)
    updated = []
    for profile in profiles:
        locations = locations_by_player.get(profile["player_id"], [])
        profile = {**profile, "tournament_locations": locations, "locations_count": len(locations)}
        results = tournament_results.get(profile["player_id"], PlayerTournamentResults())
        trophies = trophies_by_player.get(profile["player_id"], {})
        specialties = expertise.for_player(profile["player_id"], profile.get("army_lists", []))
        achievement_profile = {
            **profile,
            "_tournament_results": results,
            "_nations_cup_player_ids": nations_cup_player_ids,
            "_season_ranking_stage": sum(
                best_ranking_places.get(profile["player_id"], 51) <= threshold for threshold in (50, 30, 10)
            ),
            "_player_trophy_count": len(unique_trophy_players(trophies)),
            "_top_ten_trophy_count": len(unique_trophy_players(trophies, max_place=10)),
            "_army_specialty_count": len(specialties),
            "_number_one_specialty_count": sum(specialty["place"] == 1 for specialty in specialties),
            "_different_armies_played": _different_armies_played(profile),
            "_base_achievement_total": total_achievement_stages(BASE_ACHIEVEMENTS),
            "_player_cities": player_cities,
            "_is_best_player_in_city": any(
                _is_best_player_in_city(profile["player_id"], ranking)
                for ranking in rankings_by_season.values()
            ),
        }
        unlocked = []
        progress = {}
        unlocked_count = 0
        for group in (BASE_ACHIEVEMENTS, COMPLETION_ACHIEVEMENTS):
            for achievement in group:
                if achievement.stages:
                    current = achievement.progress(achievement_profile)
                    stage = sum(current >= target for target in achievement.stages)
                    target = achievement.stages[min(stage, achievement.stage_count - 1)]
                    progress[achievement.name] = {"current": current, "target": target, "stage": stage}
                    if stage:
                        unlocked.append(achievement.name)
                    unlocked_count += stage
                elif achievement.progress is not None and achievement.target is not None:
                    current = achievement.progress(achievement_profile)
                    progress[achievement.name] = {"current": current, "target": achievement.target}
                    if current >= achievement.target:
                        unlocked.append(achievement.name)
                        unlocked_count += 1
                elif achievement.condition(achievement_profile, results):
                    unlocked.append(achievement.name)
                    unlocked_count += 1
            achievement_profile["_base_achievement_count"] = unlocked_count
        updated.append({
            **profile, "achievements": unlocked, "achievements_count": unlocked_count,
            "achievement_progress": progress,
        })
    return updated


def recalculate_achievements():
    """Recalculate and save achievements using the currently downloaded data."""
    path = os.path.join(DATA_DIRECTORY, PLAYER_PROFILES_FILE)
    with open(path, encoding="utf-8") as f:
        profiles = json.load(f)
    main_ranking = load_main_ranking()
    rankings_by_season = {2026: main_ranking, 2027: load_main_ranking_2027()}
    updated = calculate_achievements(
        profiles,
        load_tournament_results(rankings_by_season=rankings_by_season),
        load_tournaments(),
        main_ranking=main_ranking,
        rankings_by_season=rankings_by_season,
        battles=load_battles(),
        armies=load_armies(),
        player_cities=load_player_cities(),
    )
    save_data(updated, PLAYER_PROFILES_FILE)
    return updated


if __name__ == "__main__":
    updated_profiles = recalculate_achievements()
    print(f"Recalculated achievements for {len(updated_profiles)} players.")

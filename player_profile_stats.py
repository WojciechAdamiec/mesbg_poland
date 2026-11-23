from functools import lru_cache

from army_players import compute_best_players, index_battles_by_army, ranked_players

_trophy_cache_battles = None
_trophy_cache_rankings = None
_trophy_cache_result = None


def seasonal_trophies(battles, rankings_by_season):
    global _trophy_cache_battles, _trophy_cache_rankings, _trophy_cache_result
    ranking_items = tuple(sorted(rankings_by_season.items()))
    if (
        battles is _trophy_cache_battles
        and _trophy_cache_rankings is not None
        and len(ranking_items) == len(_trophy_cache_rankings)
        and all(
            season == cached_season and ranking is cached_ranking
            for (season, ranking), (cached_season, cached_ranking) in zip(
                ranking_items, _trophy_cache_rankings
            )
        )
    ):
        return _trophy_cache_result

    places = {
        season: {player["player_id"]: player.get("place") for player in ranking if player.get("player_id")}
        for season, ranking in rankings_by_season.items()
    }
    trophies = {}
    for battle in battles:
        if battle.get("format") == "DOUBLES":
            continue
        result = battle.get("result")
        if not result or len(result) != 2 or result[0] == result[1]:
            continue
        season = battle.get("season", 2026)
        winner, loser = (1, 2) if result[0] > result[1] else (2, 1)
        winner_id = battle.get(f"player_{winner}_id")
        loser_id = battle.get(f"player_{loser}_id")
        place = places.get(season, {}).get(loser_id)
        if not winner_id or not loser_id or place is None or not 1 <= place <= 50:
            continue
        entries = trophies.setdefault(winner_id, {}).setdefault(season, {})
        entry = entries.setdefault(loser_id, {
            "player_id": loser_id,
            "displayName": battle.get(f"player_{loser}_name"),
            "main_ranking_place": place,
            "times_defeated": 0,
        })
        entry["times_defeated"] += 1
    result = {
        player_id: {
            season: sorted(entries.values(), key=lambda entry: entry["main_ranking_place"])
            for season, entries in seasons.items()
        }
        for player_id, seasons in trophies.items()
    }
    _trophy_cache_battles = battles
    _trophy_cache_rankings = ranking_items
    _trophy_cache_result = result
    return result


def unique_trophy_players(trophies_by_season, max_place=50):
    return {
        trophy["player_id"]
        for trophies in trophies_by_season.values()
        for trophy in trophies
        if trophy["main_ranking_place"] <= max_place
    }


class ArmyExpertise:
    def __init__(self, battles, ranking, armies):
        self.ranking = ranking
        self.army_by_id = {army["army_id"]: army for army in armies}
        self.battles_by_army = index_battles_by_army(battles)

    @lru_cache(maxsize=None)
    def leaderboard(self, army_id):
        return list(ranked_players(compute_best_players(
            self.battles_by_army.get(army_id, []), army_id, self.ranking
        )))

    def for_player(self, player_id, armies):
        expertise = []
        for army in armies:
            army_id = army.get("army_id")
            if army_id not in self.army_by_id:
                continue
            for position, row in self.leaderboard(army_id):
                if position > 10:
                    break
                if row["player_id"] == player_id:
                    expertise.append({
                        "army_name": self.army_by_id[army_id]["name"],
                        "place": position,
                        "adjusted_winrate": row["adjusted_winrate"],
                    })
                    break
        return sorted(expertise, key=lambda item: (item["place"], item["army_name"].casefold()))

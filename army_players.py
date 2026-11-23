MINIMUM_GAMES = 16


def compute_best_players(battles, selected_army_id, ranking):
    try:
        selected_army_id = int(selected_army_id)
    except (TypeError, ValueError):
        return []

    rank_by_id = {player.get("player_id"): player.get("place") for player in ranking}
    name_by_id = {
        player.get("player_id"): player.get("displayName")
        for player in ranking
        if player.get("player_id") and player.get("displayName")
    }
    stats_by_player = {}

    for battle in battles:
        if battle.get("format") == "DOUBLES":
            continue
        result = battle.get("result")
        if not result or len(result) != 2:
            continue

        for side, opponent in (("1", "2"), ("2", "1")):
            if battle.get(f"army_{side}_id") != selected_army_id:
                continue
            player_id = battle.get(f"player_{side}_id")
            if not player_id:
                continue

            name_by_id.setdefault(
                player_id,
                battle.get(f"player_{side}_name") or str(player_id),
            )
            player_stats = stats_by_player.setdefault(
                player_id, {"games": 0, "wins": 0, "draws": 0}
            )
            player_stats["games"] += 1
            player_score = result[int(side) - 1]
            opponent_score = result[int(opponent) - 1]
            if player_score > opponent_score:
                player_stats["wins"] += 1
            elif player_score == opponent_score:
                player_stats["draws"] += 1

    rows = []
    for player_id, stats in stats_by_player.items():
        effective_wins = stats["wins"] + 0.5 * stats["draws"]
        added_draws = max(0, MINIMUM_GAMES - stats["games"])
        rows.append(
            {
                "player_id": player_id,
                "player_name": name_by_id.get(player_id) or str(player_id),
                "main_ranking_place": rank_by_id.get(player_id),
                "games": stats["games"],
                "winrate": round(effective_wins / stats["games"] * 100, 2),
                "adjusted_winrate": round(
                    (effective_wins + 0.5 * added_draws)
                    / (stats["games"] + added_draws) * 100, 2
                ),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            -row["adjusted_winrate"],
            -row["games"],
            row["main_ranking_place"] if row["main_ranking_place"] is not None else float("inf"),
            row["player_name"].casefold(),
        ),
    )


def ranked_players(rows):
    previous_rate = None
    for index, row in enumerate(rows, start=1):
        if row["adjusted_winrate"] != previous_rate:
            position = index
            previous_rate = row["adjusted_winrate"]
        yield position, row

import math

import dash
import dash_mantine_components as dmc
from dash import callback, Input, Output
from store import load_armies, load_battles
from pages.stats_filters import (
    FACTIONS,
    FACTION_COLORS,
    GAME_TYPES,
    DEFAULT_FORMATS,
    GAME_TYPE_MAP,
    MAX_GAMES,
    MAX_POINTS,
    MIN_POINTS,
    PATCHES,
    PATCH_MAP,
    count_filtered_battles,
    create_filter_controls,
    data_size_label,
    battle_in_ranking,
    battle_in_formats,
    register_ranking_toggle,
    top_player_ids,
    filter_ids,
    filter_inputs,
)


dash.register_page(__name__, path='/stats/pickrate_vs_winrate', name="Pickrate vs Winrate")

battles_data = load_battles()
armies_data = load_armies()


def compute_chart_data(battles, armies, points_range, game_types, patches, factions, formats, min_games, ranking_enabled=False, ranking_top=50):
    allowed_types = {GAME_TYPE_MAP[gt] for gt in (game_types or []) if gt in GAME_TYPE_MAP}
    allowed_patches = {PATCH_MAP[p] for p in (patches or []) if p in PATCH_MAP}
    top_players = top_player_ids(ranking_enabled, ranking_top)
    low, high = points_range if points_range else (MIN_POINTS, MAX_POINTS)

    stats = {
        a["army_id"]: {
            "army": a["name"],
            "faction": "Good" if a.get("faction") == "GOOD" else "Evil",
            "faction_code": a.get("faction"),
            "games": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
        }
        for a in armies
    }

    total_picks = 0

    for b in battles:
        if not battle_in_formats(b, formats):
            continue
        if not battle_in_ranking(b, top_players):
            continue

        t_type = b.get("tournament_type")
        if t_type not in allowed_types:
            continue

        patch = b.get("patch")
        if patch not in allowed_patches:
            continue

        battle_points = b.get("points")
        pts = battle_points["value"] * (2 if battle_points.get("doubled") else 1) if battle_points else None
        if pts is not None:
            if not (low <= pts <= high):
                continue
        else:
            if not (low <= MIN_POINTS and high >= MAX_POINTS):
                continue

        result = b.get("result")
        if not result or len(result) != 2:
            continue
        p1_score, p2_score = result

        a1_id = b.get("army_1_id")
        a2_id = b.get("army_2_id")

        if a1_id and a1_id in stats:
            stats[a1_id]["games"] += 1
            total_picks += 1
            if p1_score > p2_score:
                stats[a1_id]["wins"] += 1
            elif p1_score == p2_score:
                stats[a1_id]["draws"] += 1
            else:
                stats[a1_id]["losses"] += 1

        if a2_id and a2_id in stats:
            stats[a2_id]["games"] += 1
            total_picks += 1
            if p2_score > p1_score:
                stats[a2_id]["wins"] += 1
            elif p2_score == p1_score:
                stats[a2_id]["draws"] += 1
            else:
                stats[a2_id]["losses"] += 1

    good_data = []
    evil_data = []

    for aid, st in stats.items():
        if st["games"] < (min_games or 0) or st["games"] == 0:
            continue

        pickrate = round((st["games"] / total_picks) * 100, 2) if total_picks > 0 else 0.0
        winrate = round((st["wins"] / st["games"]) * 100, 2) if st["games"] > 0 else 0.0

        item = {
            "army": st["army"],
            "pickrate": pickrate,
            "winrate": winrate,
            "games": st["games"],
            "faction": st["faction"],
        }

        if st["faction_code"] == "GOOD":
            good_data.append(item)
        elif st["faction_code"] == "EVIL":
            evil_data.append(item)

    series = []
    series.append({
        "name": "Good",
        "color": FACTION_COLORS["Good"],
        "data": good_data if "Good" in (factions or []) else [],
    })
    series.append({
        "name": "Evil",
        "color": FACTION_COLORS["Evil"],
        "data": evil_data if "Evil" in (factions or []) else [],
    })

    return series


initial_chart_data = compute_chart_data(
    battles_data,
    armies_data,
    points_range=[MIN_POINTS, MAX_POINTS],
    game_types=GAME_TYPES,
    patches=PATCHES,
    factions=FACTIONS,
    formats=DEFAULT_FORMATS,
    min_games=40,
)

initial_data_size = count_filtered_battles(
    battles_data, [MIN_POINTS, MAX_POINTS], GAME_TYPES, PATCHES, DEFAULT_FORMATS
)


def compute_axes(series):
    points = [p for s in series for p in s["data"]]

    max_pick = max((p["pickrate"] for p in points), default=0)
    x_max = 5.0 if max_pick <= 5 else math.ceil((max_pick + 0.25) / 0.25) * 0.25
    x_ticks = [round(i * 0.25, 2) for i in range(int(round(x_max / 0.25)) + 1)]

    if points:
        wins = [p["winrate"] for p in points]
        y_min = math.floor((min(wins) - 5) / 2) * 2
        y_max = math.ceil((max(wins) + 5) / 2) * 2
    else:
        y_min, y_max = 40, 60
    y_min = min(y_min, 50)
    y_max = max(y_max, 50)
    y_ticks = list(range(y_min, y_max + 1, 2))

    x_props = {"domain": [0, x_max], "ticks": x_ticks, "type": "number", "interval": 0}
    y_props = {"domain": [y_min, y_max], "ticks": y_ticks, "type": "number", "interval": 0}
    return x_props, y_props


REFERENCE_LINES = [{"y": 50, "color": "red.7", "lineWidth": 2}]
initial_x_props, initial_y_props = compute_axes(initial_chart_data)

controls = create_filter_controls("pvw", max_games=60, default_min_games=40)
ids = filter_ids("pvw")
register_ranking_toggle("pvw")

layout = dmc.Box(
    [
        dmc.Title("Pickrate vs Winrate", order=2, mb="md"),
        dmc.Grid(
            [
                dmc.GridCol(controls, span=3),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            dmc.Text(data_size_label(initial_data_size), id="pvw-data-size", fw=600, ta="center"),
                            dmc.ScatterChart(
                                id="pvw-chart",
                                h=500,
                                data=initial_chart_data,
                                dataKey={"x": "pickrate", "y": "winrate"},
                                xAxisLabel="Pickrate (%)",
                                yAxisLabel="Winrate (%)",
                                xAxisProps=initial_x_props,
                                yAxisProps=initial_y_props,
                                referenceLines=REFERENCE_LINES,
                                gridAxis="xy",
                                withTooltip=True,
                                tooltipProps={"content": {"function": "pickrateTooltip"}},
                            ),
                        ],
                        gap="lg",
                    ),
                    span=9,
                ),
            ]
        ),
    ],
    style={"padding": "40px"},
)


@callback(
    Output("pvw-chart", "data"),
    Output("pvw-chart", "xAxisProps"),
    Output("pvw-chart", "yAxisProps"),
    Output("pvw-data-size", "children"),
    Input(ids["points_range"], "value"),
    Input(ids["game_types"], "value"),
    Input(ids["patches"], "value"),
    Input(ids["factions"], "value"),
    Input(ids["formats"], "value"),
    Input(ids["min_games"], "value"),
    Input(ids["ranking_enabled"], "checked"),
    Input(ids["ranking_top"], "value"),
)
def update_chart(points_range, game_types, patches, factions, formats, min_games, ranking_enabled, ranking_top):
    series = compute_chart_data(
        battles_data,
        armies_data,
        points_range=points_range,
        game_types=game_types,
        patches=patches,
        factions=factions,
        formats=formats,
        min_games=min_games,
        ranking_enabled=ranking_enabled,
        ranking_top=ranking_top,
    )
    x_props, y_props = compute_axes(series)
    data_size = count_filtered_battles(
        battles_data, points_range, game_types, patches, formats, ranking_enabled, ranking_top
    )
    return series, x_props, y_props, data_size_label(data_size)

import dash
import dash_mantine_components as dmc
from dash import Input, Output, callback
from store import load_armies, load_battles
from pages.stats_filters import (
    FACTIONS,
    GAME_TYPE_MAP,
    MAX_POINTS,
    MIN_POINTS,
    PATCH_MAP,
    PATCHES,
    GAME_TYPES,
    create_filter_controls,
    filter_ids,
)


dash.register_page(__name__, path="/stats/army_list_winrates", name="Army List Winrates")

battles_data = load_battles()
armies_data = load_armies()
army_by_id = {army["army_id"]: army for army in armies_data}
army_options = [
    {"label": army["name"], "value": str(army["army_id"])}
    for army in sorted(armies_data, key=lambda item: item["name"])
]
default_army = army_options[0]["value"] if army_options else None


def _battle_matches_filters(battle, points_range, game_types, patches):
    allowed_types = {GAME_TYPE_MAP[item] for item in (game_types or []) if item in GAME_TYPE_MAP}
    allowed_patches = {PATCH_MAP[item] for item in (patches or []) if item in PATCH_MAP}
    if battle.get("tournament_type") not in allowed_types:
        return False
    if battle.get("patch") not in allowed_patches:
        return False

    low, high = points_range if points_range else (MIN_POINTS, MAX_POINTS)
    points = battle.get("points", {}).get("value") if battle.get("points") else None
    if points is not None:
        return low <= points <= high
    return low <= MIN_POINTS and high >= MAX_POINTS


def compute_chart_data(
    battles,
    selected_army_id,
    points_range,
    game_types,
    patches,
    factions,
    exclude_vegetables,
    min_games,
):
    try:
        selected_army_id = int(selected_army_id)
    except (TypeError, ValueError):
        return []

    if selected_army_id not in army_by_id:
        return []

    allowed_factions = {"GOOD" if item == "Good" else "EVIL" for item in (factions or [])}
    opponents = {
        army["army_id"]: {"army": army["name"], "games": 0, "wins": 0}
        for army in armies_data
        if army.get("faction") in allowed_factions
    }

    for battle in battles:
        if not _battle_matches_filters(battle, points_range, game_types, patches):
            continue
        result = battle.get("result")
        if not result or len(result) != 2:
            continue

        army_1_id = battle.get("army_1_id")
        army_2_id = battle.get("army_2_id")
        if army_1_id == selected_army_id and army_2_id in opponents:
            opponent_id, selected_score, opponent_score = army_2_id, result[0], result[1]
        elif army_2_id == selected_army_id and army_1_id in opponents:
            opponent_id, selected_score, opponent_score = army_1_id, result[1], result[0]
        else:
            continue

        opponents[opponent_id]["games"] += 1
        if selected_score > opponent_score:
            opponents[opponent_id]["wins"] += 1

    data = []
    for opponent_id, stats in opponents.items():
        if opponent_id == selected_army_id or stats["games"] < (min_games or 0) or stats["games"] == 0:
            continue
        data.append(
            {
                "army": stats["army"],
                "winrate": round(stats["wins"] / stats["games"] * 100, 2),
                "games": stats["games"],
            }
        )
    return sorted(data, key=lambda item: (-item["winrate"], item["army"]))


filter_control_ids = filter_ids("alw")
initial_chart_data = compute_chart_data(
    battles_data,
    default_army,
    [MIN_POINTS, MAX_POINTS],
    GAME_TYPES,
    PATCHES,
    FACTIONS,
    False,
    5,
)

layout = dmc.Box(
    [
        dmc.Title("Army List Winrates", order=2, mb="md"),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Stack(
                        [
                            dmc.Text("Army list", fw=600),
                            dmc.Select(
                                id="alw-selected-army",
                                data=army_options,
                                value=default_army,
                                searchable=True,
                                clearable=False,
                                styles={
                                    "input": {
                                        "color": "#111827",
                                        "backgroundColor": "#ffffff",
                                    },
                                    "dropdown": {"backgroundColor": "#ffffff"},
                                    "option": {"color": "#111827"},
                                },
                            ),
                            create_filter_controls("alw", max_games=40, default_min_games=5),
                        ]
                    ),
                    span=3,
                ),
                dmc.GridCol(
                    dmc.BarChart(
                        id="alw-chart",
                        h=500,
                        data=initial_chart_data,
                        dataKey="army",
                        series=[{"name": "winrate", "color": "cyan.5", "label": "Winrate (%)"}],
                        yAxisLabel="Winrate (%)",
                        xAxisProps={
                            "angle": -45,
                            "textAnchor": "end",
                            "height": 130,
                            "tickMargin": 12,
                            "interval": 0,
                        },
                        yAxisProps={"domain": [0, 100]},
                        withTooltip=True,
                        tooltipProps={"content": {"function": "armyListWinrateTooltip"}},
                        withLegend=False,
                    ),
                    span=9,
                ),
            ]
        ),
    ],
    style={"padding": "40px"},
)


@callback(
    Output("alw-chart", "data"),
    Input("alw-selected-army", "value"),
    Input(filter_control_ids["points_range"], "value"),
    Input(filter_control_ids["game_types"], "value"),
    Input(filter_control_ids["patches"], "value"),
    Input(filter_control_ids["factions"], "value"),
    Input(filter_control_ids["exclude_vegetables"], "checked"),
    Input(filter_control_ids["min_games"], "value"),
)
def update_chart(selected_army_id, points_range, game_types, patches, factions, exclude_vegetables, min_games):
    return compute_chart_data(
        battles_data,
        selected_army_id,
        points_range,
        game_types,
        patches,
        factions,
        exclude_vegetables,
        min_games,
    )

import dash
import dash_mantine_components as dmc
from dash import Input, Output, callback
from store import load_armies, load_battles
from pages.stats_filters import (
    FACTIONS,
    MAX_POINTS,
    MIN_POINTS,
    PATCHES,
    GAME_TYPES,
    DEFAULT_FORMATS,
    battle_matches_filters,
    create_filter_controls,
    data_size_label,
    filter_ids,
    register_ranking_toggle,
    top_player_ids,
)


dash.register_page(__name__, path="/stats/army_list_winrates", name="Armies Winrates")

battles_data = load_battles()
armies_data = load_armies()
army_by_id = {army["army_id"]: army for army in armies_data}
army_options = [
    {"label": army["name"], "value": str(army["army_id"])}
    for army in sorted(armies_data, key=lambda item: item["name"])
]
default_army = army_options[0]["value"] if army_options else None


def count_army_battles(battles, selected_army_id, points_range, game_types, patches, formats, ranking_enabled=False, ranking_top=50, seasons=None):
    try:
        selected_army_id = int(selected_army_id)
    except (TypeError, ValueError):
        return 0
    top_players = top_player_ids(ranking_enabled, ranking_top)
    return sum(
        1
        for battle in battles
        if selected_army_id in (battle.get("army_1_id"), battle.get("army_2_id"))
        and len(battle.get("result") or ()) == 2
        and battle_matches_filters(battle, points_range, game_types, patches, formats, top_players, seasons)
    )


def _compute_chart_data_and_count(
    battles,
    selected_army_id,
    points_range,
    game_types,
    patches,
    factions,
    formats,
    min_games,
    ranking_enabled=False,
    ranking_top=50,
    seasons=None,
):
    try:
        selected_army_id = int(selected_army_id)
    except (TypeError, ValueError):
        return [], 0

    if selected_army_id not in army_by_id:
        return [], 0

    top_players = top_player_ids(ranking_enabled, ranking_top)
    allowed_factions = {"GOOD" if item == "Good" else "EVIL" for item in (factions or [])}
    opponents = {
        army["army_id"]: {"army": army["name"], "games": 0, "wins": 0}
        for army in armies_data
        if army.get("faction") in allowed_factions
    }
    data_size = 0

    for battle in battles:
        result = battle.get("result")
        if (
            selected_army_id not in (battle.get("army_1_id"), battle.get("army_2_id"))
            or not result
            or len(result) != 2
        ):
            continue
        if not battle_matches_filters(battle, points_range, game_types, patches, formats, top_players, seasons):
            continue
        data_size += 1

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
        elif selected_score == opponent_score:
            opponents[opponent_id]["wins"] += 0.5

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
    return sorted(data, key=lambda item: (-item["winrate"], item["army"])), data_size


def compute_chart_data(
    battles,
    selected_army_id,
    points_range,
    game_types,
    patches,
    factions,
    formats,
    min_games,
    ranking_enabled=False,
    ranking_top=50,
    seasons=None,
):
    return _compute_chart_data_and_count(
        battles,
        selected_army_id,
        points_range,
        game_types,
        patches,
        factions,
        formats,
        min_games,
        ranking_enabled,
        ranking_top,
        seasons,
    )[0]


filter_control_ids = filter_ids("alw")
register_ranking_toggle("alw")
initial_chart_data, initial_data_size = _compute_chart_data_and_count(
    battles_data,
    default_army,
    [MIN_POINTS, MAX_POINTS],
    GAME_TYPES,
    PATCHES,
    FACTIONS,
    DEFAULT_FORMATS,
    5,
)

layout = dmc.Box(
    [
        dmc.Title("Armies Winrates", order=2, mb="md"),
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
                    span={"base": 12, "lg": 3},
                ),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            dmc.Text(data_size_label(initial_data_size), id="alw-data-size", fw=600, ta="center"),
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
                        ],
                        gap="lg",
                    ),
                    span={"base": 12, "lg": 9},
                ),
            ]
        ),
    ],
    style={"padding": "40px"},
)


@callback(
    Output("alw-chart", "data"),
    Output("alw-data-size", "children"),
    Input("alw-selected-army", "value"),
    Input(filter_control_ids["points_range"], "value"),
    Input(filter_control_ids["game_types"], "value"),
    Input(filter_control_ids["patches"], "value"),
    Input(filter_control_ids["factions"], "value"),
    Input(filter_control_ids["formats"], "value"),
    Input(filter_control_ids["min_games"], "value"),
    Input(filter_control_ids["ranking_enabled"], "checked"),
    Input(filter_control_ids["ranking_top"], "value"),
    Input(filter_control_ids["seasons"], "value"),
)
def update_chart(selected_army_id, points_range, game_types, patches, factions, formats, min_games, ranking_enabled, ranking_top, seasons):
    chart, data_size = _compute_chart_data_and_count(
        battles_data,
        selected_army_id,
        points_range,
        game_types,
        patches,
        factions,
        formats,
        min_games,
        ranking_enabled,
        ranking_top,
        seasons,
    )
    return chart, data_size_label(data_size)

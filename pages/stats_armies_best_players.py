import dash
import dash_mantine_components as dmc
from dash import Input, Output, callback
from army_players import MINIMUM_GAMES, compute_best_players, index_battles_by_army, ranked_players
from store import load_armies, load_battles, load_main_ranking


dash.register_page(__name__, path="/stats/armies_best_players", name="Armies Best Players")

battles_data = load_battles()
main_ranking = load_main_ranking()
armies_data = load_armies()
battles_by_army = index_battles_by_army(battles_data)
army_options = [
    {"label": army["name"], "value": str(army["army_id"])}
    for army in sorted(armies_data, key=lambda item: item["name"])
]
default_army = army_options[0]["value"] if army_options else None


def make_table_rows(rows):
    if not rows:
        return [
            dmc.TableTr(
                dmc.TableTd(
                    "No player data for this army.",
                    attributes={"colSpan": 6},
                    style={"textAlign": "center"},
                )
            )
        ]

    table_rows = []
    for position, row in ranked_players(rows):
        table_rows.append(
            dmc.TableTr(
                [
                    dmc.TableTd(position, style={"textAlign": "center"}),
                    dmc.TableTd(row["player_name"], style={"textAlign": "left"}),
                    dmc.TableTd(
                        row["main_ranking_place"]
                        if row["main_ranking_place"] is not None
                        else "-",
                        style={"textAlign": "center"},
                    ),
                    dmc.TableTd(row["games"], style={"textAlign": "center"}),
                    dmc.TableTd(f'{row["winrate"]}%', style={"textAlign": "center"}),
                    dmc.TableTd(
                        f'{row["adjusted_winrate"]}%',
                        style={"textAlign": "center"},
                    ),
                ]
            )
        )
    return table_rows


initial_rows = make_table_rows(
    compute_best_players(
        battles_by_army.get(int(default_army), []) if default_army is not None else [],
        default_army,
        main_ranking,
    )
)

layout = dmc.Box(
    [
        dmc.Title("Armies Best Players", order=2, mb="md"),
        dmc.Stack(
            [
                dmc.Paper(
                    [
                        dmc.Text(
                            "Adjusted Win Ratio adds draws for players with fewer than "
                            f"{MINIMUM_GAMES} games, up to {MINIMUM_GAMES} games total.",
                            mb="xs",
                        ),
                        dmc.Text(
                            f"AWR = ((W + D / 2) / (G + D)) × 100%, "
                            f"where D = max(0, {MINIMUM_GAMES} − G)",
                            ta="center",
                            fw=700,
                            size="lg",
                            mb="xs",
                        ),
                        dmc.Text(
                            "W = wins (actual draws count as half a win); "
                            "G = games played; D = added draws.",
                            size="sm",
                        ),
                        dmc.Text(
                            f"At {MINIMUM_GAMES} or more games, AWR equals WR.",
                            size="sm",
                        ),
                    ],
                    withBorder=True,
                    radius="md",
                    p="md",
                    style={"backgroundColor": "#1a1b2e", "color": "white"},
                ),
                dmc.Text("Army list", fw=600),
                dmc.Select(
                    id="abp-selected-army",
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
                    style={"width": "100%"},
                ),
                dmc.ScrollArea(
                    dmc.Table(
                        [
                            dmc.TableThead(
                                dmc.TableTr(
                                    [
                                        dmc.TableTh("#", style={"textAlign": "center"}),
                                        dmc.TableTh(
                                            "Player Name",
                                            style={"textAlign": "left"},
                                        ),
                                        dmc.TableTh(
                                            "Main Ranking Place",
                                            style={"textAlign": "center"},
                                        ),
                                        dmc.TableTh(
                                            "Games Played",
                                            style={"textAlign": "center"},
                                        ),
                                        dmc.TableTh("WR", style={"textAlign": "center"}),
                                        dmc.TableTh("AWR", style={"textAlign": "center"}),
                                    ]
                                )
                            ),
                            dmc.TableTbody(initial_rows, id="abp-table-body"),
                        ],
                        withTableBorder=True,
                        withRowBorders=True,
                        striped=True,
                        id="abp-table",
                    ),
                    type="auto",
                    scrollbars="x",
                    offsetScrollbars=True,
                    style={"width": "100%"},
                ),
            ],
            gap="lg",
            style={"width": "100%", "maxWidth": "710px"},
        ),
    ],
    style={"padding": "40px"},
)


@callback(
    Output("abp-table-body", "children"),
    Input("abp-selected-army", "value"),
)
def update_table(selected_army_id):
    try:
        selected_army_id_int = int(selected_army_id)
    except (TypeError, ValueError):
        selected_battles = []
    else:
        selected_battles = battles_by_army.get(selected_army_id_int, [])
    return make_table_rows(
        compute_best_players(selected_battles, selected_army_id, main_ranking)
    )

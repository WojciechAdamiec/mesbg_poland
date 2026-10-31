import dash
import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc
from store import load_player_profiles


dash.register_page(__name__, path="/stats/player_profiles", name="Player Profiles")

profiles = load_player_profiles()
profile_by_id = {p["player_id"]: p for p in profiles}
player_options = [
    {"label": (p["displayName"] or p["player_id"]).strip(), "value": p["player_id"]}
    for p in sorted(profiles, key=lambda item: (item["displayName"] or "").strip().lower())
]
default_player = None


def _stat_card(label, value):
    return dmc.Paper(
        dmc.Stack([dmc.Text(label, size="sm", c="dimmed"), dmc.Text(str(value), fw=700, size="xl")], gap=0),
        withBorder=True,
        p="md",
        bg="dark.7",
        c="white",
    )


def _table(title, rows, columns):
    """columns: list of (header, key)."""
    header = dmc.TableThead(dmc.TableTr([dmc.TableTh(h) for h, _ in columns]))
    body = dmc.TableTbody(
        [
            dmc.TableTr([dmc.TableTd(_fmt(row.get(key))) for _, key in columns])
            for row in rows
        ]
    )
    return dmc.Stack(
        [
            dmc.Title(title, order=4),
            dmc.ScrollArea(
                dmc.Table(
                    [header, body],
                    className="pp-sortable",
                    highlightOnHover=True,
                    withTableBorder=True,
                    withRowBorders=True,
                    style={"backgroundColor": "#1a1b2e", "color": "white"},
                ),
                h=min(60 + 38 * len(rows), 420),
            ) if rows else dmc.Text("No data", c="dimmed"),
        ]
    )


def _fmt(value):
    return "-" if value is None else str(value)


def _winrate_rows(rows):
    return [{**row, "winrate": f"{row['winrate']}%"} for row in rows]


SORT_OPTIONS = [
    {"label": "Sort by winrate", "value": "winrate"},
    {"label": "Sort by games played", "value": "games"},
]


def _winrate_chart(rows, key, sort_by="winrate"):
    rows = sorted(rows, key=lambda r: (-r[sort_by], -r["games"], r[key] or ""))
    figure = go.Figure(
        go.Bar(
            x=[row[key] for row in rows],
            y=[row["winrate"] for row in rows],
            customdata=[row["games"] for row in rows],
            text=[row["games"] for row in rows],
            textposition="outside",
            cliponaxis=False,
            marker_color="#22b8cf",
            hovertemplate="<b>%{x}</b><br>Winrate: %{y:.1f}%<br>Games: %{customdata}<extra></extra>",
        )
    )
    figure.update_layout(
        height=380,
        margin={"l": 50, "r": 20, "t": 30, "b": 130},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#ffffff"},
        xaxis={"tickangle": -45, "type": "category"},
        yaxis={"range": [0, 110], "title": "Winrate (%)", "gridcolor": "rgba(255,255,255,0.2)"},
        hoverlabel={"bgcolor": "#1a1b2e", "font": {"color": "#ffffff"}},
    )
    graph = dcc.Graph(
        figure=figure,
        config={"displayModeBar": False},
        style={"width": f"{max(600, 60 * len(rows))}px"},
    )
    return dmc.ScrollArea(graph, type="always", offsetScrollbars=True)


def _chart_section(title, control_id, box_id, player_id, rows_key, sort_by="winrate"):
    p = profile_by_id.get(player_id)
    return dmc.Stack(
        [
            dmc.Title(title, order=4),
            dmc.SegmentedControl(
                id=control_id,
                data=SORT_OPTIONS,
                value=sort_by,
                styles={
                    "root": {"backgroundColor": "#1a1b2e"},
                    "label": {"color": "#d1d5db"},
                    "indicator": {"backgroundColor": "#0e7490"},
                },
                color="cyan",
            ),
            dmc.Box(_winrate_chart(p[rows_key], "army_name", sort_by) if p else None, id=box_id),
        ]
    )


ARMY_COLS = [("Army list", "army_name"), ("Games", "games"), ("Wins", "wins"),
             ("Draws", "draws"), ("Losses", "losses"), ("Winrate", "winrate")]
PLAYER_COLS = [("Player", "displayName")] + ARMY_COLS[1:]


def build_top(player_id):
    p = profile_by_id.get(player_id)
    if not p:
        return dmc.Text("Select a player to see their profile.", c="dimmed")
    return dmc.Stack(
        [
            dmc.Title(p["displayName"], order=3),
            dmc.SimpleGrid(
                [
                    _stat_card("Main ranking place", p.get("main_ranking_place") or "-"),
                    _stat_card("Games played", p["games_played"]),
                    _stat_card("Wins", p["wins"]),
                    _stat_card("Draws", p["draws"]),
                    _stat_card("Losses", p["losses"]),
                    _stat_card("Winrate", f"{p['winrate']}%"),
                ],
                cols=6,
            ),
        ]
    )


def build_tables_a(player_id):
    p = profile_by_id.get(player_id)
    if not p:
        return None
    return dmc.Stack(
        [
            _table("Army lists used", _winrate_rows(p["army_lists"]), ARMY_COLS),
            _table(
                "Top 5 defeated players (by main ranking)",
                p["top5_defeated_players"],
                [("Main ranking place", "main_ranking_place"), ("Player", "displayName"),
                 ("Times defeated", "times_defeated")],
            ),
            _table("Opponents played against", _winrate_rows(p["opponents"]), PLAYER_COLS),
        ],
        gap="lg",
    )


def build_tables_b(player_id):
    p = profile_by_id.get(player_id)
    if not p:
        return None
    return _table("Army lists played against", _winrate_rows(p["opponent_army_lists"]), ARMY_COLS)


layout = dmc.Box(
    [
        dmc.Title("Player Profiles", order=2, mb="md"),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Stack(
                        [
                            dmc.Text("Player", fw=600),
                            dmc.Select(
                                id="pp-selected-player",
                                data=player_options,
                                value=default_player,
                                searchable=True,
                                clearable=True,
                                placeholder="Select a player",
                                styles={
                                    "input": {"color": "#111827", "backgroundColor": "#ffffff"},
                                    "dropdown": {"backgroundColor": "#ffffff"},
                                    "option": {"color": "#111827"},
                                },
                            ),
                        ]
                    ),
                    span=3,
                ),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            dmc.Box(build_top(default_player), id="pp-top"),
                            _chart_section(
                                "Winrate by army list used", "pp-sort-armies", "pp-chart-armies",
                                default_player, "army_lists",
                            ),
                            dmc.Box(build_tables_a(default_player), id="pp-tables-a"),
                            _chart_section(
                                "Winrate against army lists", "pp-sort-opponent-armies",
                                "pp-chart-opponent-armies", default_player, "opponent_army_lists",
                            ),
                            dmc.Box(build_tables_b(default_player), id="pp-tables-b"),
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
    Output("pp-top", "children"),
    Output("pp-tables-a", "children"),
    Output("pp-tables-b", "children"),
    Input("pp-selected-player", "value"),
)
def update_profile(player_id):
    return build_top(player_id), build_tables_a(player_id), build_tables_b(player_id)


@callback(
    Output("pp-chart-armies", "children"),
    Input("pp-selected-player", "value"),
    Input("pp-sort-armies", "value"),
)
def update_army_chart(player_id, sort_by):
    if player_id not in profile_by_id:
        return None
    return _winrate_chart(profile_by_id[player_id]["army_lists"], "army_name", sort_by)


@callback(
    Output("pp-chart-opponent-armies", "children"),
    Input("pp-selected-player", "value"),
    Input("pp-sort-opponent-armies", "value"),
)
def update_opponent_army_chart(player_id, sort_by):
    if player_id not in profile_by_id:
        return None
    return _winrate_chart(profile_by_id[player_id]["opponent_army_lists"], "army_name", sort_by)

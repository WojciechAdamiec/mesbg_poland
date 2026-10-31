import json
from pathlib import Path

import dash
import dash_mantine_components as dmc


dash.register_page(__name__, path="/hall_of_fame/nations_cup_2027")

with (Path(__file__).resolve().parents[1] / "data" / "hall_of_fame_nations_cup_2027.json").open(
    encoding="utf-8"
) as data_file:
    nations_cup_data = json.load(data_file)

teams = nations_cup_data["teams"]


def metric(label, value):
    return dmc.Stack(
        [
            dmc.Text(label, size="xs", c="#b8c7d9", fw=600),
            dmc.Text(str(value), size="sm", fw=700, c="#00ffff"),
        ],
        gap=2,
    )


def player_card(player):
    nickname = f' "{player["nickname"]}"' if player.get("nickname") else ""
    full_name = f'{player["first_name"]}{nickname} {player["surname"]}'
    photo = (
        dmc.Image(
            src=player["photo"],
            alt=full_name,
            w=150,
            h=150,
            fit="cover",
            radius="sm",
            style={"flex": "0 0 150px"},
        )
        if player["photo"]
        else dmc.Center(
            dmc.Text("Photo", size="sm", c="cyan"),
            style={
                "width": "150px",
                "height": "150px",
                "flex": "0 0 150px",
                "backgroundColor": "rgba(0, 158, 224, 0.12)",
                "borderRadius": "var(--mantine-radius-sm)",
            },
        )
    )
    return dmc.Card(
        dmc.Group(
            [
                dmc.Stack(
                    [
                        photo,
                        dmc.Text(f'Age: {player["age"]}', size="md", c="#b8c7d9"),
                        dmc.Text(
                            player["center"],
                            size="md",
                            c="#b8c7d9",
                            style={"overflowWrap": "anywhere"},
                        ),
                        dmc.Text(
                            player["club"],
                            size="md",
                            c="cyan",
                            style={"overflowWrap": "anywhere"},
                        ),
                    ],
                    gap="xs",
                    style={"flex": "0 0 150px", "minWidth": 0},
                ),
                dmc.Stack(
                    [
                        dmc.Group(
                            [
                                dmc.Text(
                                    full_name,
                                    size="xl",
                                    fw=700,
                                    c="#f7efe2",
                                    style={"flex": "1", "minWidth": 0},
                                ),
                                dmc.Badge(
                                    f'#{player["placement"]}',
                                    size="xl",
                                    color="yellow" if player["placement"] == 1 else "cyan",
                                    variant="light",
                                ),
                            ],
                            justify="space-between",
                            align="flex-start",
                            wrap="wrap",
                        ),
                        dmc.Divider(color="dark.4"),
                        dmc.SimpleGrid(
                            [
                                dmc.Stack(
                                    [
                                        metric("PLACEMENTS", player["placements"]),
                                        metric("WIN RATIO", player["winratio"]),
                                    ],
                                    gap="xs",
                                ),
                                dmc.Stack(
                                    [
                                        dmc.Text("TOP 5 ARMIES", size="xs", c="#b8c7d9", fw=600),
                                        *[
                                            dmc.Group(
                                                [
                                                    dmc.Text(
                                                        str(army["games"]),
                                                        size="sm",
                                                        fw=700,
                                                        c="#00ffff",
                                                        style={
                                                            "width": "2ch",
                                                            "textAlign": "right",
                                                            "flexShrink": 0,
                                                        },
                                                    ),
                                                    dmc.Text(
                                                        f': {army["name"]}',
                                                        size="sm",
                                                        c="#f7efe2",
                                                    ),
                                                ],
                                                gap=4,
                                                wrap="nowrap",
                                            )
                                            for army in player["top_armylists"]
                                        ],
                                    ],
                                    gap="xs",
                                ),
                            ],
                            cols=2,
                            spacing="xs",
                        ),
                        dmc.Divider(color="dark.4"),
                        dmc.Text(
                            f'"{player["quote"]}"' if player["quote"] else "",
                            size="sm",
                            c="#f7efe2",
                            fs="italic",
                            style={"overflowWrap": "anywhere"},
                        ),
                    ],
                    gap="xs",
                    style={"flex": "1", "minWidth": 0},
                ),
            ],
            align="flex-start",
            gap="sm",
            wrap="nowrap",
        ),
        withBorder=True,
        radius="md",
        padding="sm",
        shadow="md",
        style={
            "backgroundColor": "var(--metro-card)",
            "color": "#f7efe2",
            "borderColor": "rgba(0, 158, 224, 0.35)",
        },
    )


def team_section(team):
    return dmc.Box(
        [
            dmc.Text(
                team["name"],
                style={"fontSize": "28px", "marginBottom": "16px", "color": "#00ffff"},
            ),
            dmc.SimpleGrid(
                [player_card(player) for player in team["players"]],
                cols={"base": 1, "sm": 2, "lg": 3},
                spacing="lg",
            ),
        ],
        style={"marginBottom": "40px"},
    )


layout = dmc.Box(
    [
        dmc.Text(
            "2027 Nations Cup",
            style={"fontSize": "40px", "marginBottom": "20px"},
        ),
        dmc.Text(
            nations_cup_data["subtitle"],
            style={"fontSize": "16px", "marginBottom": "20px"},
        ),
        *[team_section(team) for team in teams],
    ],
    style={"padding": "40px"},
)

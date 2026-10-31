import json
from pathlib import Path

import dash
import dash_mantine_components as dmc


dash.register_page(__name__, path="/hall_of_fame/2026_online_winners")

with (Path(__file__).resolve().parents[1] / "data" / "hall_of_fame_2026_online_winners.json").open(
    encoding="utf-8"
) as data_file:
    winners_data = json.load(data_file)

players = winners_data["players"]


def metric(label, value):
    return dmc.Stack(
        [
            dmc.Text(label, size="xs", c="#b8c7d9", fw=600),
            dmc.Text(str(value), size="sm", fw=700, c="#00ffff"),
        ],
        gap=2,
    )


def player_card(player):
    placement = player["placement"]
    photo = (
        dmc.Image(
            src=player["photo"],
            alt=f'{player["first_name"]} "{player["nickname"]}" {player["surname"]}',
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
                        dmc.Text(
                            f'Age: {player["age"]}',
                            size="md",
                            c="#b8c7d9",
                        ),
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
                                    f'{player["first_name"]} "{player["nickname"]}" {player["surname"]}',
                                    size="xl",
                                    fw=700,
                                    c="#f7efe2",
                                    style={"flex": "1", "minWidth": 0},
                                ),
                                dmc.Badge(
                                    f"#{placement}",
                                    size="xl",
                                    color="yellow" if placement == 1 else "cyan",
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
                                        metric("POINTS", player["points"]),
                                        metric("WIN RATIO", player["winratio"]),
                                    ],
                                    gap="xs",
                                ),
                                dmc.Stack(
                                    [
                                        dmc.Text(
                                            "TOP 5 ARMIES",
                                            size="xs",
                                            c="#b8c7d9",
                                            fw=600,
                                        ),
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
            "borderColor": "#d6b34a" if placement == 1 else "rgba(0, 158, 224, 0.35)",
        },
    )


layout = dmc.Box(
    [
        dmc.Text(
            "2026 Online Winners",
            style={"fontSize": "40px", "marginBottom": "20px"},
        ),
        dmc.Text(
            winners_data["subtitle"],
            style={"fontSize": "16px", "marginBottom": "20px"},
        ),
        dmc.SimpleGrid(
            [player_card(player) for player in players],
            cols={"base": 1, "sm": 2, "lg": 3},
            spacing="lg",
        ),
    ],
    style={"padding": "40px"},
)

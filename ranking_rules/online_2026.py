import dash_mantine_components as dmc
from dash import html


RULES = [
    dmc.Text(""),
    dmc.Text("Score is the sum of points from top5 Online tournaments."),
    dmc.Title("Tournaments", order=3),
    dmc.Text("League points for individual tournaments are awarded as follows:"),
    html.Ol([
        html.Li(["Count the number of people who participated in the tournament*. Call this number ", html.Strong("N"), "."]),
        html.Li([
            "Award points for tournament placing according to these rules:",
            html.Ul([
                html.Li(["First place receives ", html.Strong("N"), " points."]),
                html.Li("Each subsequent place receives one point fewer than the previous place."),
                html.Li("Every player receives at least 5 points, regardless of placing."),
            ]),
        ]),
    ]),
    dmc.Text(["Example for ", html.Strong("N"), " = 13:"]),
    dmc.Table(
        data={
            "head": ["Place", 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
            "body": [["Points", 13, 12, 11, 10, 9, 8, 7, 6, 5, 5, 5, 5, 5]],
        },
        withTableBorder=True,
        withColumnBorders=True,
    ),
    dmc.Text(["Example for ", html.Strong("N"), " = 8:"]),
    dmc.Table(
        data={
            "head": ["Place", 1, 2, 3, 4, 5, 6, 7, 8],
            "body": [["Points", 8, 7, 6, 5, 5, 5, 5, 5]],
        },
        withTableBorder=True,
        withColumnBorders=True,
    ),
    dmc.Text("*Only people who played at least one round normally are counted."),
]

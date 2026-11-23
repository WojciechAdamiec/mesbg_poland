import dash_mantine_components as dmc

from ranking_rules.scoring import scoring_table


RULES = [
    dmc.Text("The ranking score is top5 Online tournament results."),
    dmc.Text("Individual tournaments", fw=700),
    scoring_table(
        [*range(1, 17), "17+"],
        [40, 35, 31, 28, 26, 24, 22, 20, 18, 17, 16, 15, 14, 13, 12, 11, 10],
    ),
    dmc.Text("Team tournaments", fw=700),
    scoring_table(
        [*range(1, 9), "9+"],
        [40, 31, 26, 22, 18, 16, 14, 12, 10],
    ),
]

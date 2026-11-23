import dash_mantine_components as dmc

from ranking_rules.scoring import CHALLENGER, LOCAL, MASTER_INDIVIDUAL, scoring_table


RULES = [
    dmc.Text(
        "The ranking counts top5 Master results and top5 Local or Challenger results. "
        "At most one Challenger per season can count."
    ),
    dmc.Text(
        "Each DMP participant receives 30 points, counted as a Master result."
    ),
    dmc.Text("Local tournaments", fw=700),
    scoring_table(*LOCAL),
    dmc.Text("Challenger tournaments", fw=700),
    scoring_table(*CHALLENGER),
    dmc.Text("Master tournaments - Individual", fw=700),
    scoring_table(*MASTER_INDIVIDUAL),
    dmc.Text("Master tournaments - Pairs", fw=700),
    scoring_table(
        [*range(1, 20), "20+"],
        [60, 55, 50, 47, 44, 41, 38, 35, 32, 29, 27, 25, 23, 21, 19, 17, 15, 13, 11, 10],
    ),
]

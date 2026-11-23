import dash_mantine_components as dmc

from ranking_rules.scoring import CHALLENGER, LOCAL, MASTER_INDIVIDUAL, MASTER_PAIRS_2027, scoring_table


RULES = [
    dmc.Text(
        "The ranking counts top6 Master or Challenger results and top6 Local results."
    ),
    dmc.Text("Each DMP participant receives 30 points, counted as a Master result."),
    dmc.Text("Local tournaments", fw=700),
    scoring_table(*LOCAL),
    dmc.Text("Challenger tournaments", fw=700),
    scoring_table(*CHALLENGER),
    dmc.Text("Master tournaments - Individual", fw=700),
    scoring_table(*MASTER_INDIVIDUAL),
    dmc.Text("Master tournaments - Pairs", fw=700),
    scoring_table(*MASTER_PAIRS_2027),
]

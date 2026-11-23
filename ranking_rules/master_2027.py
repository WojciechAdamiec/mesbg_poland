import dash_mantine_components as dmc

from ranking_rules.scoring import CHALLENGER, MASTER_INDIVIDUAL, MASTER_PAIRS_2027, scoring_table


RULES = [
    dmc.Text("The ranking counts top3 Master or Challenger results. DMP does not count."),
    dmc.Text("Challenger tournaments", fw=700),
    scoring_table(*CHALLENGER),
    dmc.Text("Master tournaments - Individual", fw=700),
    scoring_table(*MASTER_INDIVIDUAL),
    dmc.Text("Master tournaments - Pairs", fw=700),
    scoring_table(*MASTER_PAIRS_2027),
]

import dash_mantine_components as dmc

from ranking_rules.scoring import ONLINE_INDIVIDUAL_2027, ONLINE_TEAM_2027, scoring_table


RULES = [
    dmc.Text("The ranking score is top5 Online tournament results."),
    dmc.Text("Individual tournaments", fw=700),
    scoring_table(*ONLINE_INDIVIDUAL_2027),
    dmc.Text("Team tournaments", fw=700),
    scoring_table(*ONLINE_TEAM_2027),
]

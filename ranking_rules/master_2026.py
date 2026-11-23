import dash_mantine_components as dmc


RULES = [
    dmc.Text("Only players who played at least 3 Master tournaments are eligible for the ranking."),
    dmc.Text("Score is the sum of placements in top3 Master tournaments."),
    dmc.Text("The lower the score the better."),
    dmc.Text("DMP is not counted towards the ranking."),
]

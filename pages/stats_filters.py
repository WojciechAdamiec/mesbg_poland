import dash_mantine_components as dmc


GAME_TYPES = ["Locals", "Challengers", "Masters", "Online"]
PATCHES = ["Balrog Age", "Gwaihir Age", "Nightlings Age"]
FACTIONS = ["Good", "Evil"]
FACTION_COLORS = {"Good": "green.6", "Evil": "red.6"}

GAME_TYPE_MAP = {
    "Locals": "LOCAL",
    "Challengers": "CHALLENGER",
    "Masters": "MASTER",
    "Online": "ONLINE",
}

PATCH_MAP = {
    "Balrog Age": "BALROG",
    "Gwaihir Age": "GWAIHIR",
    "Nightlings Age": "NIGHTLINGS",
}

FACTION_MAP = {
    "Good": "GOOD",
    "Evil": "EVIL",
}

MIN_POINTS = 0
MAX_POINTS = 1000
MAX_GAMES = 100


def filter_ids(prefix):
    return {
        "points_range": f"{prefix}-points-range",
        "game_types": f"{prefix}-game-types",
        "patches": f"{prefix}-patches",
        "factions": f"{prefix}-factions",
        "exclude_vegetables": f"{prefix}-exclude-vegetables",
        "min_games": f"{prefix}-min-games",
    }


def filter_inputs(prefix):
    ids = filter_ids(prefix)
    return [
        ids["points_range"],
        ids["game_types"],
        ids["patches"],
        ids["factions"],
        ids["exclude_vegetables"],
        ids["min_games"],
    ]


def create_filter_controls(prefix, max_games=MAX_GAMES, default_min_games=0):
    ids = filter_ids(prefix)
    return dmc.Stack(
        [
            dmc.Text("Points range", fw=600),
            dmc.RangeSlider(
                id=ids["points_range"],
                min=MIN_POINTS,
                max=MAX_POINTS,
                step=10,
                value=[MIN_POINTS, MAX_POINTS],
                marks=[{"value": p, "label": str(p)} for p in range(0, 1001, 100)],
                labelAlwaysOn=False,
                mb=30,
            ),
            dmc.Text("Game type", fw=600),
            dmc.CheckboxGroup(
                id=ids["game_types"],
                value=GAME_TYPES,
                children=dmc.Group([dmc.Checkbox(label=gt, value=gt) for gt in GAME_TYPES]),
            ),
            dmc.Text("Patch", fw=600, mt="md"),
            dmc.CheckboxGroup(
                id=ids["patches"],
                value=PATCHES,
                children=dmc.Group([dmc.Checkbox(label=p, value=p) for p in PATCHES]),
            ),
            dmc.Text("Factions", fw=600, mt="md"),
            dmc.CheckboxGroup(
                id=ids["factions"],
                value=FACTIONS,
                children=dmc.Group([dmc.Checkbox(label=f, value=f) for f in FACTIONS]),
            ),
            dmc.Text("Ranking", fw=600, mt="md"),
            dmc.Checkbox(id=ids["exclude_vegetables"], label="Exclude Vegetables"),
            dmc.Text("Minimum games played", fw=600, mt="md"),
            dmc.Slider(
                id=ids["min_games"],
                min=0,
                max=max_games,
                step=1,
                value=default_min_games,
                marks=[
                    {"value": p, "label": str(p)}
                    for p in range(0, max_games + 1, max(1, max_games // 5))
                ],
                labelAlwaysOn=False,
                mb=30,
            ),
        ]
    )
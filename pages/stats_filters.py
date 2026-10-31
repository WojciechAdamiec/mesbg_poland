import dash_mantine_components as dmc
from dash import Input, Output, callback
from store import load_main_ranking


GAME_TYPES = ["Locals", "Challengers", "Masters", "Online"]
PATCHES = ["Balrog Age", "Gwaihir Age", "Nightlings Age"]
FORMATS = ["Individual", "Team", "Doubles"]
DEFAULT_FORMATS = ["Individual", "Team"]
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

FORMAT_MAP = {
    "Individual": "INDIVIDUAL",
    "Team": "TEAM",
    "Doubles": "DOUBLES",
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
        "formats": f"{prefix}-formats",
        "min_games": f"{prefix}-min-games",
        "ranking_enabled": f"{prefix}-ranking-enabled",
        "ranking_top": f"{prefix}-ranking-top",
    }


def top_player_ids(ranking_enabled, top_x):
    """Returns a set of player ids in the top X of the main ranking, or None when the filter is off."""
    if not ranking_enabled:
        return None
    limit = top_x or 50
    return {r["player_id"] for r in load_main_ranking() if r.get("place", 0) <= limit}


def battle_in_formats(battle, formats):
    allowed = {FORMAT_MAP[item] for item in (formats or []) if item in FORMAT_MAP}
    return (battle.get("format") or "INDIVIDUAL") in allowed


def battle_in_ranking(battle, top_players):
    if top_players is None:
        return True
    return battle.get("player_1_id") in top_players and battle.get("player_2_id") in top_players


def battle_matches_filters(battle, points_range, game_types, patches, formats, top_players=None):
    if not battle_in_formats(battle, formats) or not battle_in_ranking(battle, top_players):
        return False
    allowed_types = {GAME_TYPE_MAP[item] for item in (game_types or []) if item in GAME_TYPE_MAP}
    allowed_patches = {PATCH_MAP[item] for item in (patches or []) if item in PATCH_MAP}
    if battle.get("tournament_type") not in allowed_types or battle.get("patch") not in allowed_patches:
        return False

    low, high = points_range if points_range else (MIN_POINTS, MAX_POINTS)
    battle_points = battle.get("points")
    if battle_points:
        return low <= battle_points["value"] * (2 if battle_points.get("doubled") else 1) <= high
    return low <= MIN_POINTS and high >= MAX_POINTS


def count_filtered_battles(battles, points_range, game_types, patches, formats, ranking_enabled=False, ranking_top=50):
    top_players = top_player_ids(ranking_enabled, ranking_top)
    return sum(
        1
        for battle in battles
        if battle_matches_filters(battle, points_range, game_types, patches, formats, top_players)
        and len(battle.get("result") or ()) == 2
    )


def data_size_label(count):
    return f"Data Size: {count:,} battles".replace(",", " ")


def register_ranking_toggle(prefix):
    ids = filter_ids(prefix)

    @callback(
        Output(ids["ranking_top"], "disabled"),
        Input(ids["ranking_enabled"], "checked"),
    )
    def _toggle_slider(enabled):
        return not enabled


def filter_inputs(prefix):
    ids = filter_ids(prefix)
    return [
        ids["points_range"],
        ids["game_types"],
        ids["patches"],
        ids["factions"],
        ids["formats"],
        ids["min_games"],
        ids["ranking_enabled"],
        ids["ranking_top"],
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
            dmc.Text("Tournament rank", fw=600),
            dmc.CheckboxGroup(
                id=ids["game_types"],
                value=GAME_TYPES,
                children=dmc.Group([dmc.Checkbox(label=gt, value=gt) for gt in GAME_TYPES]),
            ),
            dmc.Text("Game format", fw=600, mt="md"),
            dmc.CheckboxGroup(
                id=ids["formats"],
                value=DEFAULT_FORMATS,
                children=dmc.Group([dmc.Checkbox(label=f, value=f) for f in FORMATS]),
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
            dmc.Switch(id=ids["ranking_enabled"], label="Enable Ranking Filter", checked=False),
            dmc.Text("Battles fought only by players in TopX:", size="sm"),
            dmc.Slider(
                id=ids["ranking_top"],
                min=10,
                max=200,
                step=1,
                value=50,
                disabled=True,
                marks=[{"value": p, "label": str(p)} for p in (10, 25, 50, 75, 100, 125, 150, 175, 200)],
                labelAlwaysOn=False,
                mb=30,
            ),
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

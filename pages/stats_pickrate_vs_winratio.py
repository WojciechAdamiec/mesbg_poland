import dash
import dash_mantine_components as dmc
from dash import callback, Input, Output
from store import load_armies, load_battles


dash.register_page(__name__, path='/stats/pickrate_vs_winratio', name="Pickrate vs Winratio")

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

battles_data = load_battles()
armies_data = load_armies()

MIN_POINTS = 0
MAX_POINTS = 1000
MAX_GAMES = 100


def compute_chart_data(battles, armies, points_range, game_types, patches, factions, exclude_vegetables, min_games):
    allowed_types = {GAME_TYPE_MAP[gt] for gt in (game_types or []) if gt in GAME_TYPE_MAP}
    allowed_patches = {PATCH_MAP[p] for p in (patches or []) if p in PATCH_MAP}
    low, high = points_range if points_range else (MIN_POINTS, MAX_POINTS)

    stats = {
        a["army_id"]: {
            "army": a["name"],
            "faction": "Good" if a.get("faction") == "GOOD" else "Evil",
            "faction_code": a.get("faction"),
            "games": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
        }
        for a in armies
    }

    total_picks = 0

    for b in battles:
        t_type = b.get("tournament_type")
        if t_type not in allowed_types:
            continue

        patch = b.get("patch")
        if patch not in allowed_patches:
            continue

        pts = b.get("points", {}).get("value") if b.get("points") else None
        if pts is not None:
            if not (low <= pts <= high):
                continue
        else:
            if not (low <= MIN_POINTS and high >= MAX_POINTS):
                continue

        result = b.get("result")
        if not result or len(result) != 2:
            continue
        p1_score, p2_score = result

        a1_id = b.get("army_1_id")
        a2_id = b.get("army_2_id")

        if a1_id and a1_id in stats:
            stats[a1_id]["games"] += 1
            total_picks += 1
            if p1_score > p2_score:
                stats[a1_id]["wins"] += 1
            elif p1_score == p2_score:
                stats[a1_id]["draws"] += 1
            else:
                stats[a1_id]["losses"] += 1

        if a2_id and a2_id in stats:
            stats[a2_id]["games"] += 1
            total_picks += 1
            if p2_score > p1_score:
                stats[a2_id]["wins"] += 1
            elif p2_score == p1_score:
                stats[a2_id]["draws"] += 1
            else:
                stats[a2_id]["losses"] += 1

    good_data = []
    evil_data = []

    for aid, st in stats.items():
        if st["games"] < (min_games or 0) or st["games"] == 0:
            continue

        pickrate = round((st["games"] / total_picks) * 100, 2) if total_picks > 0 else 0.0
        winrate = round((st["wins"] / st["games"]) * 100, 2) if st["games"] > 0 else 0.0

        item = {
            "army": st["army"],
            "pickrate": pickrate,
            "winrate": winrate,
            "games": st["games"],
            "faction": st["faction"],
        }

        if st["faction_code"] == "GOOD":
            good_data.append(item)
        elif st["faction_code"] == "EVIL":
            evil_data.append(item)

    series = []
    series.append({
        "name": "Good",
        "color": FACTION_COLORS["Good"],
        "data": good_data if "Good" in (factions or []) else [],
    })
    series.append({
        "name": "Evil",
        "color": FACTION_COLORS["Evil"],
        "data": evil_data if "Evil" in (factions or []) else [],
    })

    return series


initial_chart_data = compute_chart_data(
    battles_data,
    armies_data,
    points_range=[MIN_POINTS, MAX_POINTS],
    game_types=GAME_TYPES,
    patches=PATCHES,
    factions=FACTIONS,
    exclude_vegetables=False,
    min_games=0,
)

controls = dmc.Stack(
    [
        dmc.Text("Points range", fw=600),
        dmc.RangeSlider(
            id="pvw-points-range",
            min=MIN_POINTS,
            max=MAX_POINTS,
            step=10,
            value=[MIN_POINTS, MAX_POINTS],
            marks=[{"value": p, "label": str(p)} for p in range(0, 1001, 100)],
            labelAlwaysOn=True,
            mb=30,
        ),
        dmc.Text("Game type", fw=600),
        dmc.CheckboxGroup(
            id="pvw-game-types",
            value=GAME_TYPES,
            children=dmc.Group([dmc.Checkbox(label=gt, value=gt) for gt in GAME_TYPES]),
        ),
        dmc.Text("Patch", fw=600, mt="md"),
        dmc.CheckboxGroup(
            id="pvw-patches",
            value=PATCHES,
            children=dmc.Group([dmc.Checkbox(label=p, value=p) for p in PATCHES]),
        ),
        dmc.Text("Factions", fw=600, mt="md"),
        dmc.CheckboxGroup(
            id="pvw-factions",
            value=FACTIONS,
            children=dmc.Group([dmc.Checkbox(label=f, value=f) for f in FACTIONS]),
        ),
        dmc.Text("Ranking", fw=600, mt="md"),
        dmc.Checkbox(id="pvw-exclude-vegetables", label="Exclude Vegetables"),
        dmc.Text("Minimum games played", fw=600, mt="md"),
        dmc.Slider(
            id="pvw-min-games",
            min=0,
            max=MAX_GAMES,
            step=1,
            value=0,
            marks=[{"value": p, "label": str(p)} for p in range(0, 101, 20)],
            labelAlwaysOn=False,
            mb=30,
        ),
    ]
)

layout = dmc.Box(
    [
        dmc.Title("Pickrate vs Winrate", order=2, mb="md"),
        dmc.Grid(
            [
                dmc.GridCol(controls, span=3),
                dmc.GridCol(
                    dmc.ScatterChart(
                        id="pvw-chart",
                        h=500,
                        data=initial_chart_data,
                        dataKey={"x": "pickrate", "y": "winrate"},
                        xAxisLabel="Pickrate (%)",
                        yAxisLabel="Winrate (%)",
                        xAxisProps={"tickCount": 20},
                        yAxisProps={"tickCount": 20},
                        gridAxis="xy",
                        withTooltip=True,
                        tooltipProps={"content": {"function": "pickrateTooltip"}},
                    ),
                    span=9,
                ),
            ]
        ),
    ],
    style={"padding": "40px"},
)


@callback(
    Output("pvw-chart", "data"),
    Input("pvw-points-range", "value"),
    Input("pvw-game-types", "value"),
    Input("pvw-patches", "value"),
    Input("pvw-factions", "value"),
    Input("pvw-exclude-vegetables", "checked"),
    Input("pvw-min-games", "value"),
)
def update_chart(points_range, game_types, patches, factions, exclude_vegetables, min_games):
    return compute_chart_data(
        battles_data,
        armies_data,
        points_range=points_range,
        game_types=game_types,
        patches=patches,
        factions=factions,
        exclude_vegetables=exclude_vegetables,
        min_games=min_games,
    )

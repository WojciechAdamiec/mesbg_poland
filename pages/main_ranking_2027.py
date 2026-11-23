import dash

from pages.main_ranking_2026 import HIGHLIGHT_FULL, HIGHLIGHT_ZERO, make_layout
from ranking_rules.main_2027 import RULES
from store import load_main_ranking_2027


dash.register_page(__name__, path="/ranking_main_2027")

data = load_main_ranking_2027()

MASTER_CHALLENGER_KEYS = [f"master_challenger_{i}" for i in range(1, 7)]
LOCAL_KEYS = [f"local_{i}" for i in range(1, 7)]
COLUMNS = [
    ("place", "Place", "center"),
    ("score", "Score", "center"),
    ("displayName", "Display Name", "right"),
    ("city_name", "City Name", "left"),
    ("master_challenger_total", "Master Total", "center"),
    *[(key, f"Master {i}", "center") for i, key in enumerate(MASTER_CHALLENGER_KEYS, 1)],
    ("local_total", "Local Total", "center"),
    *[(key, f"Local {i}", "center") for i, key in enumerate(LOCAL_KEYS, 1)],
]
HIGHLIGHT_HALF = {"backgroundColor": "#369bef80", "fontWeight": 700}


def cell_style(key, value, align):
    style = {"textAlign": align}
    if value == 0:
        style.update(HIGHLIGHT_ZERO)
    elif isinstance(value, (int, float)):
        if (
            (key == "score" and value >= 480)
            or (key == "master_challenger_total" and value >= 360)
            or (key == "local_total" and value >= 120)
            or (key in MASTER_CHALLENGER_KEYS and value >= 60)
            or (key in LOCAL_KEYS and value >= 20)
        ):
            style.update(HIGHLIGHT_FULL)
        elif key in MASTER_CHALLENGER_KEYS and 40 <= value < 60:
            style.update(HIGHLIGHT_HALF)
    return style


layout = make_layout(data, year=2027, rules=RULES, columns=COLUMNS, style_for_cell=cell_style)

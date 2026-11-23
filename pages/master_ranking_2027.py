import dash

from pages.main_ranking_2026 import HIGHLIGHT_FULL, HIGHLIGHT_ZERO
from pages.main_ranking_2027 import HIGHLIGHT_HALF
from pages.master_ranking_2026 import COLUMNS as COLUMNS_2026, make_layout
from ranking_rules.master_2027 import RULES


dash.register_page(__name__, path="/ranking_master_2027")

MASTER_KEYS = [f"master_{i}" for i in range(1, 4)]
COLUMNS = [
    *COLUMNS_2026[:5],
    *[(key, f"Master {i}", "center") for i, key in enumerate(MASTER_KEYS, 1)],
]


def cell_style(key, value, align):
    style = {"textAlign": align}
    if value == 0:
        style.update(HIGHLIGHT_ZERO)
    elif isinstance(value, (int, float)):
        if (key == "score" and value >= 180) or (key in MASTER_KEYS and value >= 60):
            style.update(HIGHLIGHT_FULL)
        elif key in MASTER_KEYS and 40 <= value < 60:
            style.update(HIGHLIGHT_HALF)
    return style


SAMPLE_RESULTS = [
    ("Sample: maximum", [60, 60, 60]),
    ("Sample: just below maximum", [60, 60, 59]),
    ("Sample: thresholds", [59, 40, 39]),
    ("Sample: no scores", [0, 0, 0]),
]
sample_data = [
    {
        "place": place,
        "score": sum(scores),
        "tie_breaker": 0,
        "displayName": name,
        "city_name": "Sample",
        **dict(zip(MASTER_KEYS, scores)),
    }
    for place, (name, scores) in enumerate(SAMPLE_RESULTS, 1)
]

layout = make_layout(sample_data, year=2027, rules=RULES, columns=COLUMNS, style_for_cell=cell_style)

import dash

from pages.main_ranking_2026 import HIGHLIGHT_FULL
from pages.online_ranking_2026 import COLUMNS as COLUMNS_2026, HIGHLIGHT_ZERO, make_layout
from ranking_rules.online_2027 import RULES


dash.register_page(__name__, path="/ranking_online_2027")

ONLINE_KEYS = [f"online_{i}" for i in range(1, 6)]
COLUMNS = [
    *COLUMNS_2026[:4],
    *[(key, f"Online {i}", "center") for i, key in enumerate(ONLINE_KEYS, 1)],
]


def cell_style(key, value, align):
    style = {"textAlign": align}
    if value == 0:
        style.update(HIGHLIGHT_ZERO)
    elif isinstance(value, (int, float)) and (
        (key == "score" and value >= 200) or (key in ONLINE_KEYS and value >= 40)
    ):
        style.update(HIGHLIGHT_FULL)
    return style


SAMPLE_RESULTS = [
    ("Sample: maximum", [40, 40, 40, 40, 40]),
    ("Sample: just below maximum", [40, 40, 40, 40, 39]),
    ("Sample: thresholds", [40, 39, 10, 0, 0]),
    ("Sample: no scores", [0, 0, 0, 0, 0]),
]
sample_data = [
    {
        "place": place,
        "score": sum(scores),
        "displayName": name,
        "city_name": "Sample",
        **dict(zip(ONLINE_KEYS, scores)),
    }
    for place, (name, scores) in enumerate(SAMPLE_RESULTS, 1)
]

layout = make_layout(sample_data, year=2027, rules=RULES, columns=COLUMNS, style_for_cell=cell_style)

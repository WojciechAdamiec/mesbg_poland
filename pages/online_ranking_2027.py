import dash

from pages.main_ranking_2026 import HIGHLIGHT_FULL
from pages.online_ranking_2026 import COLUMNS as COLUMNS_2026, HIGHLIGHT_ZERO, make_layout
from ranking_rules.online_2027 import RULES
from store import load_online_ranking_2027


dash.register_page(__name__, path="/ranking_online_2027")

data = load_online_ranking_2027()

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


layout = make_layout(data, year=2027, rules=RULES, columns=COLUMNS, style_for_cell=cell_style)

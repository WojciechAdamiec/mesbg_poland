import dash
from dash import dcc
import dash_mantine_components as dmc
from ranking_rules import rules_box
from ranking_rules.main_2026 import RULES
from store import load_main_ranking


dash.register_page(__name__, path='/ranking_main_2026')

data = load_main_ranking()

# key, header label, text-align for both the header and its column cells
COLUMNS = [
    ("place", "Place", "center"),
    ("score", "Score", "center"),
    ("displayName", "Display Name", "right"),
    ("city_name", "City Name", "left"),
    ("master_total", "Master Total", "center"),
    ("master_1", "Master 1", "center"),
    ("master_2", "Master 2", "center"),
    ("master_3", "Master 3", "center"),
    ("master_4", "Master 4", "center"),
    ("master_5", "Master 5", "center"),
    ("local_total", "Local Total", "center"),
    ("local_1", "Local 1", "center"),
    ("local_2", "Local 2", "center"),
    ("local_3", "Local 3", "center"),
    ("local_4", "Local 4", "center"),
    ("local_5", "Local 5", "center"),
]

# minimum value for a cell to be highlighted; adjust per column as needed
HIGHLIGHT_THRESHOLDS = {
    "master_total": 300,
    "master_1": 60,
    "master_2": 60,
    "master_3": 60,
    "master_4": 60,
    "master_5": 60,
    "local_total": 120,
    "local_1": 40,
    "local_2": 20,
    "local_3": 20,
    "local_4": 20,
    "local_5": 20,
}
HIGHLIGHT_FULL = {"backgroundColor": "#3ac87880", "fontWeight": 700}
HIGHLIGHT_ZERO = {"backgroundColor": "#ea616c3c", "fontWeight": 700}


def cell_style(key, value, align):
    style = {"textAlign": align}
    threshold = HIGHLIGHT_THRESHOLDS.get(key)
    if threshold is not None and isinstance(value, (int, float)) and value >= threshold:
        style.update(HIGHLIGHT_FULL)
    elif value == 0:
        style.update(HIGHLIGHT_ZERO)
    return style


def make_layout(ranking_data, year, rules, columns=COLUMNS, style_for_cell=cell_style):
    head = dmc.TableThead(
        dmc.TableTr([
            dmc.TableTh(label, style={"textAlign": align})
            for _, label, align in columns
        ])
    )
    rows = [
        dmc.TableTr([
            dmc.TableTd(row[key], style=style_for_cell(key, row[key], align))
            for key, _, align in columns
        ])
        for row in ranking_data
    ]
    title = f"{year} Main Ranking"
    return dmc.Box([
        dmc.Text(title, className="ranking-title", style={"fontSize": "40px", "marginBottom": "20px"}),
        rules_box(rules),
        dcc.Link("Go to Champions Hub Ranking", href="https://championshub.app/mesbg/ranking/mesbg-pl", target="_blank", style={"color": "#00ffff", "text-decoration": "none", "font-size": "16px"}),
        dmc.ScrollArea(
            dmc.Table([head, dmc.TableTbody(rows)], highlightOnHover=True, withTableBorder=True, withColumnBorders=True, style={"marginTop": "20px", "width": "60%"}),
            type="auto",
            scrollbars="x",
            offsetScrollbars=True,
            className="table-scroll-area",
        ),
    ], style={"paddingLeft": "40px"})


layout = make_layout(data, year=2026, rules=RULES)

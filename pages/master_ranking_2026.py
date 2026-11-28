import dash
from dash import dcc
import dash_mantine_components as dmc
from ranking_rules import rules_box
from ranking_rules.master_2026 import RULES
from ranking_player_links import player_name_cell
from store import load_master_ranking


dash.register_page(__name__, path='/ranking_master_2026')


data = load_master_ranking()


COLUMNS = [
    ("place", "Place", "center"),
    ("score", "Score", "center"),
    ("tie_breaker", "Tie Breaker", "center"),
    ("displayName", "Display Name", "right"),
    ("city_name", "City Name", "left"),
    ("top_2", "Top2", "center"),
    ("master_1", "Master 1", "center"),
    ("master_2", "Master 2", "center"),
    ("master_3", "Master 3", "center"),
]

HIGHLIGHT_THRESHOLDS = {
    "top_2": 2,
    "master_1": 1,
    "master_2": 1,
    "master_3": 1,
}
HIGHLIGHT_FULL = {"backgroundColor": "#3ac87880", "fontWeight": 700}


def cell_style(key, value, align):
    style = {"textAlign": align}
    threshold = HIGHLIGHT_THRESHOLDS.get(key)
    if threshold is not None and isinstance(value, (int, float)) and value == threshold:
        style.update(HIGHLIGHT_FULL)
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
            dmc.TableTd(player_name_cell(row) if key == "displayName" else row[key],
                        style=style_for_cell(key, row[key], align))
            for key, _, align in columns
        ])
        for row in ranking_data
    ]
    title = f"{year} Master Ranking"
    return dmc.Box([
        dmc.Text(title, className="ranking-title", style={"fontSize": "40px", "marginBottom": "20px"}),
        rules_box(rules),
        dcc.Link("Go to Champions Hub Ranking", href="https://championshub.app/mesbg/ranking/mesbg-pl?variant=kadra", target="_blank", style={"color": "#00ffff", "text-decoration": "none", "font-size": "16px"}),
        dmc.ScrollArea(
            dmc.Table([head, dmc.TableTbody(rows)], highlightOnHover=True, withTableBorder=True, withColumnBorders=True, style={"marginTop": "20px", "width": "35%"}),
            type="auto",
            scrollbars="x",
            offsetScrollbars=True,
            className="table-scroll-area",
        ),
    ], style={"paddingLeft": "40px"})


layout = make_layout(data, year=2026, rules=RULES)

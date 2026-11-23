import dash
from dash import dcc
import dash_mantine_components as dmc
from ranking_rules import rules_box
from ranking_rules.online_2026 import RULES
from store import load_online_ranking


dash.register_page(__name__, path='/ranking_online_2026')


data = load_online_ranking()

COLUMNS = [
    ("place", "Place", "center"),
    ("score", "Score", "center"),
    ("displayName", "Display Name", "right"),
    ("city_name", "City Name", "left"),
    ("online_1", "Online 1", "center"),
    ("online_2", "Online 2", "center"),
    ("online_3", "Online 3", "center"),
    ("online_4", "Online 4", "center"),
    ("online_5", "Online 5", "center"),
]


HIGHLIGHT_ZERO = {"backgroundColor": "#ea616c3c", "fontWeight": 700}


def cell_style(key, value, align):
    style = {"textAlign": align}
    if value == 0:
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
    title = f"{year} Online Ranking"
    return dmc.Box([
        dmc.Text(title, className="ranking-title", style={"fontSize": "40px", "marginBottom": "20px"}),
        rules_box(rules),
        dcc.Link("Go to Champions Hub Ranking", href="https://championshub.app/mesbg/ranking/mesbg-pl-online", target="_blank", style={"color": "#00ffff", "text-decoration": "none", "font-size": "16px"}),
        dmc.ScrollArea(
            dmc.Table([head, dmc.TableTbody(rows)], highlightOnHover=True, withTableBorder=True, withColumnBorders=True, style={"marginTop": "20px", "width": "40%"}),
            type="auto",
            scrollbars="x",
            offsetScrollbars=True,
            className="table-scroll-area",
        ),
    ], style={"paddingLeft": "40px"})


layout = make_layout(data, year=2026, rules=RULES)

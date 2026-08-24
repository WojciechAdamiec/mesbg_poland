import dash
from dash import dcc
import dash_mantine_components as dmc
from store import load_master_ranking


dash.register_page(__name__, path='/ranking_master')


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
HIGHLIGHT_FULL = {"backgroundColor": "#4adfce3d", "fontWeight": 700}


def cell_style(key, value, align):
    style = {"textAlign": align}
    threshold = HIGHLIGHT_THRESHOLDS.get(key)
    if threshold is not None and isinstance(value, (int, float)) and value == threshold:
        style.update(HIGHLIGHT_FULL)
    return style


rows = [
    dmc.TableTr(
        [
            dmc.TableTd(row[key], style=cell_style(key, row[key], align))
            for key, _, align in COLUMNS
        ]
    )
    for row in data
]

head = dmc.TableThead(
    dmc.TableTr(
        [
            dmc.TableTh(label, style={"textAlign": align})
            for _, label, align in COLUMNS
        ]
    )
)
body = dmc.TableTbody(rows)

layout = dmc.Box([
    dmc.Text("Polish MESBG Master League Ranking", style={"fontSize": "40px", "marginBottom": "20px"}),
    dcc.Link("Go to Champions Hub Ranking", href="https://championshub.app/mesbg/ranking/mesbg-pl?variant=kadra", target="_blank", style={"color": "#00ffff", "text-decoration": "none", "font-size": "16px"}),
    dmc.Table([head, body], highlightOnHover=True, withTableBorder=True, withColumnBorders=True, style={"marginTop": "20px", "width": "35%"}),
], style={"paddingLeft": "40px"})

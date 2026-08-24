import dash
from dash import dcc
import dash_mantine_components as dmc
from store import load_main_ranking


dash.register_page(__name__, path='/ranking_main')



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
HIGHLIGHT_FULL = {"backgroundColor": "#4adfce3d", "fontWeight": 700}
HIGHLIGHT_ZERO = {"backgroundColor": "#ea616c3c", "fontWeight": 700}


def cell_style(key, value, align):
    style = {"textAlign": align}
    threshold = HIGHLIGHT_THRESHOLDS.get(key)
    if threshold is not None and isinstance(value, (int, float)) and value >= threshold:
        style.update(HIGHLIGHT_FULL)
    elif value == 0:
        style.update(HIGHLIGHT_ZERO)
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
    dmc.Text("Polish MESBG League Main Ranking", style={"fontSize": "40px", "marginBottom": "20px"}),
    dcc.Link("Go to Champions Hub Ranking", href="https://championshub.app/mesbg/ranking/mesbg-pl", target="_blank", style={"color": "#00ffff", "text-decoration": "none", "font-size": "16px"}),
    dmc.Table([head, body], highlightOnHover=True, withTableBorder=True, withColumnBorders=True, style={"marginTop": "20px", "width": "60%"}),
], style={"paddingLeft": "40px"})

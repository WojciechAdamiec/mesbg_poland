import dash
from dash import dcc
import dash_mantine_components as dmc
from store import load_online_ranking


dash.register_page(__name__, path='/ranking_online')


data = load_online_ranking()

# key, header label, text-align for both the header and its column cells
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


rows = [
    dmc.TableTr(
        [
            dmc.TableTd(row[key], style={"textAlign": align})
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
    dmc.Text("Polish MESBG Online League Ranking", style={"fontSize": "40px", "marginBottom": "20px"}),
    dcc.Link("Go to Champions Hub Ranking", href="https://championshub.app/mesbg/ranking/mesbg-pl-online", target="_blank", style={"color": "#00ffff", "text-decoration": "none", "font-size": "16px"}),
    dmc.Table([head, body], highlightOnHover=True, withTableBorder=True, withColumnBorders=True, style={"marginTop": "20px", "width": "40%"}),
], style={"paddingLeft": "40px"})

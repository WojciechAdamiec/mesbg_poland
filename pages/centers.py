import dash
import json
import dash_mantine_components as dmc
import plotly.express as px
import pandas as pd
import math
from dash import Input, Output, dcc, no_update


dash.register_page(__name__, path='/centers')


with open('data/powiaty-min.geojson', 'r', encoding='utf-8') as f:
    poland_map = json.load(f)

features = poland_map.get("features", [])
powiat_ids = [feature.get("id") for feature in features]
powiat_names = [feature.get("properties", {}).get("nazwa", "").strip().title() for feature in features]

df = pd.DataFrame(
    {
        "powiat_id": powiat_ids,
        "powiat_name": powiat_names,
        "value": 0,
    }
)

fig = px.choropleth(
    df,
    geojson=poland_map,
    locations="powiat_id",
    featureidkey="id",
    color="value",
    hover_name="powiat_name",
    color_continuous_scale=[(0.0, "#dfe7ef"), (1.0, "#dfe7ef")],
    range_color=(0, 1),
)
fig.update_traces(marker_line_color="#5f7288", marker_line_width=0.6)
fig.update_traces(
    hovertemplate="<b>%{hovertext}</b><extra></extra>",
    selector={"type": "choropleth"},
)


def get_size(raw_size):
    return int(math.sqrt(float(raw_size)) * 3)


CENTER_COLOR = "#1e8b5f"
CITY_COORDS = {
    "Kraków": (50.0614, 19.9366),
    "Bydgoszcz": (53.1235, 18.0084),
    "Katowice": (50.2649, 19.0238),
    "Poznań": (52.4064, 16.9252),
    "Bielsko-Biała": (49.8224, 19.0584),
    "Wrocław": (51.1079, 17.0385),
    "Trójmiasto": (54.3520, 18.6466),
    "Warszawa": (52.2297, 21.0122),
    "Łódź": (51.7592, 19.4560),
    "Rzeszów": (50.0414, 21.9991),
    "Kielce": (50.8661, 20.6286),
    "Białystok": (53.1325, 23.1688),
    "ONLINE": (49.8, 16.9),
    "Rybnik": (50.0971, 18.5416),
    "Toruń": (53.0138, 18.5981),
    "Kozy": (50.9141, 21.0842),
    "Szczecin": (53.4285, 14.5528),
    "Lublin": (51.2465, 22.5684),
    "Złotów": (53.3466, 17.0536),
    "Chorzów": (50.3032, 18.9480),
    "Dębica": (50.0514, 21.4114),
    "Nowy Sącz": (49.6216, 20.6977),
}

with open('data/centers.json', 'r', encoding='utf-8') as f:
    centers_data = json.load(f)

centers = pd.DataFrame(
    [
        {
            "name": name,
            "lat": CITY_COORDS.get(name, (49.0, 14.5))[0],
            "lon": CITY_COORDS.get(name, (49.0, 14.5))[1],
            "size": size,
            "desc": "",
            "url": "",
            "color": CENTER_COLOR,
        }
        for name, size in centers_data.items()
    ]
)

centers["size"] = centers["size"].apply(get_size)

fig.add_scattergeo(
    lat=centers["lat"],
    lon=centers["lon"],
    mode="markers",
    marker={
        "size": centers["size"],
        "color": centers["color"],
        "line": {"color": "#f7efe2", "width": 1.5},
        "symbol": "circle",
    },
    customdata=centers[["name", "desc", "url"]],
    hovertemplate="<b>%{customdata[0]}</b><br>DESC<extra></extra>",
    name="Centers",
)

fig.update_coloraxes(showscale=False)
fig.update_geos(
    visible=False,
    bgcolor="rgba(0,0,0,0)",
    projection_type="mercator",
    lataxis_range=[48.8, 55.1],
    lonaxis_range=[14.1, 24.2],
)
fig.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)


layout = dmc.Box([
    dcc.Location(id="centers-redirect", refresh=True),
    dmc.Text("MESBG Centers Map", style={"fontSize": "40px", "marginBottom": "20px"}),
    dcc.Graph(id="centers-map", figure=fig, style={"height": "80vh", "width": "100%"}, responsive=True),
])


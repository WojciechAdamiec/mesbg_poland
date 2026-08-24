import dash
import json
import math
import dash_mantine_components as dmc
import plotly.express as px
import pandas as pd
from dash import Input, Output, dcc, no_update


dash.register_page(__name__, path='/masters')


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


INDIVIDUAL_COLOR = "#8b1e1e"
PAIR_COLOR = "#1e8b5f"
DOUBLES_COLOR = "#1e5f8b"
DMP_COLOR = "#8b5f1e"


def get_size(players):
    return int(math.sqrt(players) * 8)


master_tournaments = pd.DataFrame(
    [
        {
            "name": "Macki Wojny 2026",
            "description": "Turniej Parowy. 700pkt.",
            "url": "https://championshub.app/mesbg/events/1a1d8ae7-1be8-46d3-afde-ab479c8cc5a3",
            "lat": 51.7592,
            "lon": 19.4560,
            "color": PAIR_COLOR,
            "size": 100,
        },
        {
            "name": "IMW: Khazad Wrocław 2026",
            "description": "Turniej Indywidualny. 613pkt.",
            "url": "https://championshub.app/mesbg/events/78daa7ea-5cff-4b08-8232-62ceba122249",
            "lat": 51.1079,
            "lon": 17.0385,
            "color": INDIVIDUAL_COLOR,
            "size": 88,
        },
        {
            "name": "Indywidualne Mistrzostwa Polski 2026",
            "description": "Turniej Indywidualny. 745pkt.",
            "url": "https://championshub.app/mesbg/events/4acc2947-7325-4fd3-b6c5-26d158dcfc50",
            "lat": 50.3249,
            "lon": 18.7857,
            "color": INDIVIDUAL_COLOR,
            "size": 131,
        },
        {
            "name": "Bitwa o Białe Miasto 2026",
            "description": "Turniej Indywidualny. 500pkt.",
            "url": "https://championshub.app/mesbg/events/d98e7403-869d-45b1-b913-0f93d880a59c",
            "lat": 53.1325,
            "lon": 23.1688,
            "color": INDIVIDUAL_COLOR,
            "size": 48,
        },
        {
            "name": "Magmaster 2026",
            "description": "Turniej Parowy. 600+200pkt.",
            "url": "https://championshub.app/mesbg/events/1690b39b-6f35-4f03-b112-95e242cc7f7c",
            "lat": 53.1235,
            "lon": 18.0084,
            "color": PAIR_COLOR,
            "size": 70,
        },
        {
            "name": "Bój o Czerwoną Strzałę 2026",
            "description": "Turniej Indywidualny. 915pkt.",
            "url": "https://championshub.app/mesbg/events/bc514681-647d-4397-83ad-a29f10c6406d",
            "lat": 52.4064,
            "lon": 16.9252,
            "color": INDIVIDUAL_COLOR,
            "size": 65,
        },
        {
            "name": "Krakowskie Manewry 2026",
            "description": "Turniej Indywidualny. 670pkt.",
            "url": "https://championshub.app/mesbg/events/73886888-aec6-40b2-a2cd-a6353423fd49",
            "lat": 50.0647,
            "lon": 19.9450,
            "color": INDIVIDUAL_COLOR,
            "size": 101,
        },
        {
            "name": "Parowe Mistrzostwa Polski 2026",
            "description": "Turniej Parowy. 777pkt.",
            "url": "https://championshub.app/mesbg/events/77bcee3e-0ab8-48e0-a5dd-3f15749fb492",
            "lat": 54.3520,
            "lon": 18.6466,
            "color": PAIR_COLOR,
            "size": 66,
        },
        {
            "name": "Zadyma na Południu 2026",
            "description": "Turniej Doubles. 2x500pkt.",
            "url": "https://championshub.app/mesbg/events/4ff143c6-50f2-4e4d-905e-355cf001dd7b",
            "lat": 49.8224,
            "lon": 19.0584,
            "color": DOUBLES_COLOR,
            "size": 80,
        },
        {
            "name": "Cień Wschodu - Fajkowy Szlem 2026",
            "description": "Turniej Indywidualny. 600pkt.",
            "url": "https://championshub.app/mesbg/events/2b307bec-26d6-447f-b2da-b6fafd2b9d4b",
            "lat": 51.2465,
            "lon": 22.5684,
            "color": INDIVIDUAL_COLOR,
            "size": 50,
        },
        {
            "name": "Drużynowe Mistrzostwa Polski 2026",
            "description": "Turniej Drużynowy. 800pkt.",
            "url": "https://championshub.app/mesbg/events/05c040d4-265e-48c7-8af7-66ba309d88d9",
            "lat": 52.2297,
            "lon": 21.0122,
            "color": DMP_COLOR,
            "size": 240,
        },
    ]
)
master_tournaments["size"] = master_tournaments["size"].apply(get_size)

fig.add_scattergeo(
    lat=master_tournaments["lat"],
    lon=master_tournaments["lon"],
    mode="markers",
    marker={
        "size": master_tournaments["size"],
        "color": master_tournaments["color"],
        "line": {"color": "#f7efe2", "width": 1.5},
        "symbol": "circle",
    },
    customdata=master_tournaments[["name", "description", "url"]],
    hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
    name="Tournaments",
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
    dcc.Location(id="masters-redirect", refresh=True),
    dmc.Text("This is the Masters page", style={"fontSize": "40px", "marginBottom": "20px"}),
    dcc.Graph(id="masters-map", figure=fig, style={"height": "80vh", "width": "100%"}, responsive=True),
])


@dash.callback(Output("masters-redirect", "href"), Input("masters-map", "clickData"))
def redirect_to_tournament(click_data):
    if not click_data or not click_data.get("points"):
        return no_update

    point = click_data["points"][0]
    customdata = point.get("customdata")

    if not customdata or len(customdata) < 3:
        return no_update

    return customdata[2]
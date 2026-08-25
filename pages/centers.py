import dash
import json
import dash_mantine_components as dmc
import plotly.express as px
import pandas as pd
import math
from dash_iconify import DashIconify
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


accordion = dmc.Accordion(
    disableChevronRotation=False,
    multiple=True,
    children=[
        dmc.AccordionItem(
            [
                dmc.AccordionControl(
                    dmc.Text(
                        "Social Groups",
                        fz="xl",
                        lh="md",
                    ),
                    icon=DashIconify(
                        icon="tabler:user",
                        color="var(--mantine-color-blue-6)",
                        width=20,
                    ),
                    className="accordion-control",
                ),
                dmc.AccordionPanel(
                    dmc.Box([
                        dmc.Text(
                            [
                                "Facebook: ",
                                dmc.Anchor(
                                    "Middle Earth SBG Górny Śląsk i okolice",
                                    href="https://www.facebook.com/groups/115716008622897",
                                    target="_blank",
                                    c="var(--neon-cyan)",
                                ),
                            ],
                            fz="md",
                            lh="md",
                            c="var(--mantine-color-white)",
                        ),
                        dmc.Text(
                            [
                                "Discord: ",
                                dmc.Anchor(
                                    "Śluńskie Hobbity",
                                    href="https://discord.gg/P8h3pnSHTS",
                                    target="_blank",
                                    c="var(--neon-cyan)",
                                ),
                            ],
                            fz="md",
                            lh="md",
                            c="var(--mantine-color-white)",
                        ),
                    ])
                ),
            ],
            value="socials",
        ),
        dmc.AccordionItem(
            [
                dmc.AccordionControl(
                    dmc.Text(
                        "Clubs",
                        fz="xl",
                        lh="md",
                    ),
                    icon=DashIconify(
                        icon="tabler:beer",
                        color= "var(--mantine-color-red-6)",
                        width=20,
                    ),
                    className="accordion-control",
                ),
                dmc.AccordionPanel([
                    dmc.Group(
                        [
                            dmc.Text("Legion Śląska", fw=800, fz="40px", c="var(--mantine-color-white)"),
                            dmc.Badge("Z Members", size="xl", color="violet", c="var(--mantine-color-white)"),
                        ],
                        justify="space-between",
                        mt="md",
                        mb="xs",
                    ),
                    dmc.Grid(
                        [
                            dmc.GridCol(
                                dmc.Box(
                                    dmc.Image(
                                        radius="md",
                                        h=200,
                                        w="auto",
                                        fit="contain",
                                        src="assets/legion_slaska.jpg",
                                    ),
                                    style={
                                        "overflow": "hidden",
                                        "borderRadius": "var(--mantine-radius-md)",
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center",
                                    },
                                ),
                                span="content",
                            ),
                            dmc.GridCol(
                                dmc.Box([
                                    dmc.Text("Śląskie Stowarzyszenie Graczy Gier Bitewnych Legion Śląska", fz="md", lh="md", c="var(--mantine-color-white)", mb="sm"),
                                    dmc.Text(
                                        [
                                            "Facebook: ",
                                            dmc.Anchor(
                                                "Middle-Earth SBG Legion Śląska",
                                                href="https://www.facebook.com/LegionSlaska",
                                                target="_blank",
                                                c="var(--neon-cyan)",
                                            ),
                                        ],
                                        fz="sm",
                                        lh="md",
                                        c="var(--mantine-color-white)",
                                    ),
                                    dmc.Text(
                                        [
                                            "Website: ",
                                            dmc.Anchor(
                                                "Legion Śląska",
                                                href="https://legion-slaska.pl/",
                                                target="_blank",
                                                c="var(--neon-cyan)",
                                            ),
                                        ],
                                        fz="sm",
                                        lh="md",
                                        c="var(--mantine-color-white)",
                                    ),
                                    dmc.Text(
                                        [
                                            "Contact Person: ",
                                            dmc.Anchor(
                                                "Piotr \"Zichu\" Zich",
                                                href="https://www.facebook.com/piotr.zich",
                                                target="_blank",
                                                c="var(--neon-cyan)",
                                            ),
                                        ],
                                        fz="sm",
                                        lh="md",
                                        c="var(--mantine-color-white)",
                                    ),
                                ]),
                                span="auto",
                            ),
                        ],
                        gutter="sm",
                    ),
                ]),
            ],
            value="clubs",
        ),
        dmc.AccordionItem(
            [
                dmc.AccordionControl(
                    dmc.Text(
                        "Gaming Places",
                        fz="xl",
                        lh="md",
                    ),
                    icon=DashIconify(
                        icon="tabler:current-location",
                        color= "var(--mantine-color-green-6)",
                        width=20,
                    ),
                    className="accordion-control",
                ),
                dmc.AccordionPanel(
                    dmc.Text(
                        [
                            "Place: ",
                            dmc.Anchor(
                                "Miejski Dom Kultury Os. Paderewskiego w Katowicach",
                                href="https://www.google.com/maps/search/?api=1&query=Miejski+Dom+Kultury+Os.+Paderewskiego+w+Katowicach",
                                target="_blank",
                                c="var(--neon-cyan)",
                            ),
                        ],
                        fz="md",
                        lh="md",
                        c="var(--mantine-color-white)",
                    ),
                ),
            ],
            value="places",
        ),
        dmc.AccordionItem(
            [
                dmc.AccordionControl(
                    dmc.Text(
                        "Tutors",
                        fz="xl",
                        lh="md",
                    ),
                    icon=DashIconify(
                        icon="tabler:chalkboard-teacher",
                        color= "var(--mantine-color-violet-5)",
                        width=20,
                    ),
                    className="accordion-control",
                ),
                dmc.AccordionPanel(
                    dmc.Text(
                        [
                            "Facebook: ",
                            dmc.Anchor(
                                'Łukasz Stoch',
                                href="https://www.facebook.com/profile.php?id=100001723950937",
                                target="_blank",
                                c="var(--neon-cyan)",
                            ),
                        ],
                        fz="md",
                        lh="md",
                        c="var(--mantine-color-white)",
                    ),
                ),
            ],
            value="tutors",
        ),
    ],
)


card = dmc.Card(
    children=[
        dmc.CardSection(
            dmc.Image(
                src="assets/katowice.jpg",
                h=160,
            )
        ),
        dmc.Group(
            [
                dmc.Text("Katowice", fw=800, fz="40px", c="var(--mantine-color-white)"),
                dmc.Badge("X players", size="xl", color="blue", c="var(--mantine-color-white)"),
                dmc.Badge("Y events", size="xl", color="green", c="var(--mantine-color-white)"),
                dmc.Badge("Large Center", size="xl", color="red", c="var(--mantine-color-white)"),
            ],
            justify="space-between",
            mt="md",
            mb="xs",
        ),
        accordion,
    ],
    withBorder=True,
    shadow="sm",
    radius="md",
    w=350,
    style={
        "background": "transparent",
        "borderColor": "var(--mantine-color-gray-6)",
    },
)


layout = dmc.Box([
    dcc.Location(id="centers-redirect", refresh=True),
    dmc.Text("MESBG Centers Map", style={"fontSize": "40px", "marginBottom": "20px"}),
    dmc.Group(
        children = [
            dcc.Graph(id="centers-map", figure=fig, style={"height": "80vh", "width": "100%"}, responsive=True),
            card,
        ],
        justify="center",
        gap="xl",
        grow=True,
    )
])


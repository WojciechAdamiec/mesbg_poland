import dash
import json
import dash_mantine_components as dmc
import plotly.express as px
import pandas as pd
import math
from dash_iconify import DashIconify
from dash import Input, Output, State, dcc, no_update


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


def get_size(raw_size):
    return int(math.sqrt(float(raw_size)) * 3)


def get_center_size_category(name):
    details = centers_details.get(name, {})
    size_val = details.get("size")
    if size_val in ["Large", "Medium", "Small"]:
        return size_val
    raw_size = centers_data.get(name, 0)
    if raw_size >= 500:
        return "Large"
    elif raw_size >= 100:
        return "Medium"
    else:
        return "Small"


SIZE_COLORS = {
    "Large": "#e03131",   # Red
    "Medium": "#2f9e44",  # Green
    "Small": "#1971c2",   # Blue
}
SELECTED_CENTER_COLOR = "#ffd43b"  # Bright Gold / Yellow highlight
SELECTED_LINE_COLOR = "#ffffff"

# Global tooltip texts for all center cards
TOOLTIP_PLAYERS = "Number of unique players who played here in last 12 months."
TOOLTIP_EVENTS = "Number of events held here in last 12 months."
TOOLTIP_SIZE = "Community size tier of this center."
TOOLTIP_CLUB_MEMBERS = "Total registered club members."
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
    "ONLINE": (49.8, 15.5),
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

with open('data/centers_details.json', 'r', encoding='utf-8') as f:
    centers_details = json.load(f)

centers = pd.DataFrame(
    [
        {
            "name": name,
            "lat": CITY_COORDS.get(name, (49.0, 14.5))[0],
            "lon": CITY_COORDS.get(name, (49.0, 14.5))[1],
            "size": size,
            "desc": "",
            "url": "",
        }
        for name, size in centers_data.items()
    ]
)

centers["size"] = centers["size"].apply(get_size)


def create_map_figure(selected_center=None):
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

    marker_colors = [
        SELECTED_CENTER_COLOR if name == selected_center else SIZE_COLORS.get(get_center_size_category(name), "#1971c2")
        for name in centers["name"]
    ]
    line_colors = [
        SELECTED_LINE_COLOR if name == selected_center else "#f7efe2"
        for name in centers["name"]
    ]
    line_widths = [
        3.0 if name == selected_center else 1.5
        for name in centers["name"]
    ]
    marker_sizes = [
        size + 5 if name == selected_center else size
        for name, size in zip(centers["name"], centers["size"])
    ]

    fig.add_scattergeo(
        lat=centers["lat"],
        lon=centers["lon"],
        mode="markers",
        marker={
            "size": marker_sizes,
            "color": marker_colors,
            "line": {"color": line_colors, "width": line_widths},
            "symbol": "circle",
        },
        customdata=centers["name"],
        hovertemplate="<b>%{customdata}</b><extra></extra>",
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
        uirevision="constant",
    )
    return fig


def create_welcome_card():
    return dmc.Card(
        children=[
            dmc.Stack(
                [
                    DashIconify(
                        icon="tabler:map-pin",
                        width=60,
                        color="var(--neon-cyan)",
                    ),
                    dmc.Text(
                        "MESBG Poland Centers",
                        fw=800,
                        fz="32px",
                        c="var(--mantine-color-white)",
                        ta="center",
                    ),
                    dmc.Text(
                        "Select any town marker on the map to explore its local MESBG community, social groups, clubs, gaming venues, and tutors.",
                        fz="md",
                        c="var(--mantine-color-gray-4)",
                        ta="center",
                        lh="md",
                    ),
                    dmc.Badge(
                        "Click a town on the map",
                        size="xl",
                        variant="light",
                        color="blue",
                        mt="sm",
                    ),
                ],
                align="center",
                justify="center",
                gap="md",
                p="xl",
            )
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        w=700,
        style={
            "background": "transparent",
            "borderColor": "var(--mantine-color-gray-6)",
        },
    )


def create_center_card(town_name):
    if not town_name:
        return create_welcome_card()

    details = centers_details.get(town_name, {})
    raw_size = centers_data.get(town_name, 0)

    card_sections = []

    # 1. Header Image
    image_src = details.get("image")
    if image_src:
        card_sections.append(
            dmc.CardSection(
                dmc.Image(
                    src=image_src,
                    h=160,
                )
            )
        )

    players = details.get("players", "X")
    events = details.get("events", "Y")

    size_val = details.get("size")
    if not size_val:
        if raw_size >= 500:
            size_val = "Large"
        elif raw_size >= 100:
            size_val = "Medium"
        else:
            size_val = "Small"

    players_label = f"{players} players" if not str(players).lower().endswith("players") else str(players)
    events_label = f"{events} events" if not str(events).lower().endswith("events") else str(events)
    size_label = size_val if "Center" in str(size_val) else f"{size_val} Center"

    badge_elements = [
        dmc.Tooltip(
            label=TOOLTIP_PLAYERS,
            withArrow=True,
            children=dmc.Badge(players_label, size="xl", color="blue", c="var(--mantine-color-white)"),
        ),
        dmc.Tooltip(
            label=TOOLTIP_EVENTS,
            withArrow=True,
            children=dmc.Badge(events_label, size="xl", color="green", c="var(--mantine-color-white)"),
        ),
        dmc.Tooltip(
            label=TOOLTIP_SIZE,
            withArrow=True,
            children=dmc.Badge(size_label, size="xl", color="red", c="var(--mantine-color-white)"),
        ),
    ]

    card_sections.append(
        dmc.Group(
            [
                dmc.Text(town_name, fw=800, fz="40px", c="var(--mantine-color-white)"),
                *badge_elements,
            ],
            justify="space-between",
            mt="md",
            mb="xs",
        )
    )

    socials_list = details.get("socials", [])
    if socials_list:
        social_children = []
        for s in socials_list:
            platform = s.get("platform", "Link")
            name = s.get("name", platform)
            url = s.get("url", "#")
            social_children.append(
                dmc.Text(
                    [
                        f"{platform}: ",
                        dmc.Anchor(
                            name,
                            href=url,
                            target="_blank",
                            c="var(--neon-cyan)",
                        ),
                    ],
                    fz="md",
                    lh="md",
                    c="var(--mantine-color-white)",
                )
            )
        social_content = dmc.Box(social_children)
    else:
        social_content = dmc.Text("No groups listed", c="var(--mantine-color-dimmed)", fz="sm")

    clubs_list = details.get("clubs", [])
    if clubs_list:
        club_items = []
        for c in clubs_list:
            club_name = c.get("name", "Club")
            members = c.get("members", "Z")
            members_label = members if str(members).lower().endswith("members") else f"{members} Members"
            club_img = c.get("image")
            description = c.get("description", "")
            links = c.get("links", [])

            header_items = [
                dmc.Text(club_name, fw=800, fz="28px", c="var(--mantine-color-white)"),
                dmc.Tooltip(
                    label=TOOLTIP_CLUB_MEMBERS,
                    withArrow=True,
                    children=dmc.Badge(members_label, size="xl", color="violet", c="var(--mantine-color-white)"),
                ),
            ]

            col_children = []
            if club_img:
                col_children.append(
                    dmc.GridCol(
                        dmc.Box(
                            dmc.Image(
                                radius="md",
                                h=160,
                                w="auto",
                                fit="contain",
                                src=club_img,
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
                    )
                )

            info_lines = []
            if description:
                info_lines.append(
                    dmc.Text(description, fz="md", lh="md", c="var(--mantine-color-white)", mb="sm")
                )
            for l in links:
                label = l.get("label", "Link")
                link_name = l.get("name", label)
                link_url = l.get("url", "#")
                info_lines.append(
                    dmc.Text(
                        [
                            f"{label}: ",
                            dmc.Anchor(
                                link_name,
                                href=link_url,
                                target="_blank",
                                c="var(--neon-cyan)",
                            ),
                        ],
                        fz="sm",
                        lh="md",
                        c="var(--mantine-color-white)",
                    )
                )
            col_children.append(dmc.GridCol(dmc.Box(info_lines), span="auto"))

            club_items.append(
                dmc.Box(
                    [
                        dmc.Group(header_items, justify="space-between", mt="xs", mb="xs"),
                        dmc.Grid(col_children, gutter="sm"),
                    ],
                    mb="md",
                )
            )
        clubs_content = dmc.Box(club_items)
    else:
        clubs_content = dmc.Text("No clubs listed", c="var(--mantine-color-dimmed)", fz="sm")

    places_list = details.get("places", [])
    if places_list:
        place_lines = []
        for p in places_list:
            place_name = p.get("name", "Place")
            place_url = p.get("url", f"https://www.google.com/maps/search/?api=1&query={place_name}")
            place_lines.append(
                dmc.Text(
                    [
                        "Place: ",
                        dmc.Anchor(
                            place_name,
                            href=place_url,
                            target="_blank",
                            c="var(--neon-cyan)",
                        ),
                    ],
                    fz="md",
                    lh="md",
                    c="var(--mantine-color-white)",
                )
            )
        places_content = dmc.Box(place_lines)
    else:
        places_content = dmc.Text("No places listed", c="var(--mantine-color-dimmed)", fz="sm")

    tutors_list = details.get("tutors", [])
    if tutors_list:
        tutor_blocks = []
        for t in tutors_list:
            tutor_name = t.get("name", "Tutor")
            contact_elements = []

            contacts = t.get("contacts")
            if contacts and isinstance(contacts, list):
                for c in contacts:
                    platform = c.get("platform", "Contact")
                    value = c.get("value") or c.get("name") or platform
                    url = c.get("url")

                    if url:
                        contact_elements.append(
                            dmc.Text(
                                [
                                    f"{platform}: ",
                                    dmc.Anchor(
                                        value,
                                        href=url,
                                        target="_blank",
                                        c="var(--neon-cyan)",
                                    ),
                                ],
                                fz="sm",
                                lh="md",
                                c="var(--mantine-color-white)",
                            )
                        )
                    else:
                        contact_elements.append(
                            dmc.Text(
                                f"{platform}: {value}" if value != platform else platform,
                                fz="sm",
                                lh="md",
                                c="var(--mantine-color-white)",
                            )
                        )
            else:
                platform = t.get("platform", "Facebook")
                tutor_url = t.get("url")
                if tutor_url:
                    contact_elements.append(
                        dmc.Text(
                            [
                                f"{platform}: ",
                                dmc.Anchor(
                                    tutor_name,
                                    href=tutor_url,
                                    target="_blank",
                                    c="var(--neon-cyan)",
                                ),
                            ],
                            fz="sm",
                            lh="md",
                            c="var(--mantine-color-white)",
                        )
                    )
                else:
                    contact_elements.append(
                        dmc.Text(
                            platform,
                            fz="sm",
                            lh="md",
                            c="var(--mantine-color-white)",
                        )
                    )

            tutor_blocks.append(
                dmc.Box(
                    [
                        dmc.Text(tutor_name, fw=700, fz="md", c="var(--mantine-color-white)", mb="xs"),
                        dmc.Box(contact_elements, pl="sm"),
                    ],
                    mb="sm",
                )
            )
        tutors_content = dmc.Box(tutor_blocks)
    else:
        tutors_content = dmc.Text("No tutors listed", c="var(--mantine-color-dimmed)", fz="sm")

    accordion = dmc.Accordion(
        disableChevronRotation=False,
        multiple=True,
        value=["socials", "clubs", "places", "tutors"],
        children=[
            dmc.AccordionItem(
                [
                    dmc.AccordionControl(
                        dmc.Text("Social Groups", fz="xl", lh="md"),
                        icon=DashIconify(
                            icon="tabler:user",
                            color="var(--mantine-color-blue-6)",
                            width=20,
                        ),
                        className="accordion-control",
                    ),
                    dmc.AccordionPanel(social_content),
                ],
                value="socials",
            ),
            dmc.AccordionItem(
                [
                    dmc.AccordionControl(
                        dmc.Text("Clubs", fz="xl", lh="md"),
                        icon=DashIconify(
                            icon="tabler:beer",
                            color="var(--mantine-color-red-6)",
                            width=20,
                        ),
                        className="accordion-control",
                    ),
                    dmc.AccordionPanel(clubs_content),
                ],
                value="clubs",
            ),
            dmc.AccordionItem(
                [
                    dmc.AccordionControl(
                        dmc.Text("Gaming Places", fz="xl", lh="md"),
                        icon=DashIconify(
                            icon="tabler:current-location",
                            color="var(--mantine-color-green-6)",
                            width=20,
                        ),
                        className="accordion-control",
                    ),
                    dmc.AccordionPanel(places_content),
                ],
                value="places",
            ),
            dmc.AccordionItem(
                [
                    dmc.AccordionControl(
                        dmc.Text("Tutors", fz="xl", lh="md"),
                        icon=DashIconify(
                            icon="tabler:chalkboard-teacher",
                            color="var(--mantine-color-violet-5)",
                            width=20,
                        ),
                        className="accordion-control",
                    ),
                    dmc.AccordionPanel(tutors_content),
                ],
                value="tutors",
            ),
        ],
    )

    card_sections.append(accordion)

    return dmc.Card(
        children=card_sections,
        withBorder=True,
        shadow="sm",
        radius="md",
        w=700,
        style={
            "background": "transparent",
            "borderColor": "var(--mantine-color-gray-6)",
        },
    )


layout = dmc.Box([
    dcc.Location(id="centers-redirect", refresh=True),
    dcc.Store(id="selected-center-store", data=None),
    dmc.Text("MESBG Centers Map", style={"fontSize": "40px", "marginBottom": "20px"}),
    dmc.Group(
        children=[
            dcc.Graph(
                id="centers-map",
                figure=create_map_figure(None),
                style={"height": "80vh", "width": "100%"},
                responsive=True,
            ),
            dmc.Box(
                id="center-card-container",
                children=create_welcome_card(),
            ),
        ],
        justify="center",
        align="flex-start",
        gap="xl",
        grow=True,
    ),
])


@dash.callback(
    Output("centers-map", "figure"),
    Output("center-card-container", "children"),
    Output("selected-center-store", "data"),
    Input("centers-map", "clickData"),
    State("selected-center-store", "data"),
)
def update_center(click_data, current_selection):
    selected = current_selection
    if click_data and "points" in click_data and len(click_data["points"]) > 0:
        point = click_data["points"][0]
        custom = point.get("customdata")
        candidate = None
        if isinstance(custom, list) and len(custom) > 0:
            candidate = custom[0]
        elif isinstance(custom, str):
            candidate = custom
        elif point.get("hovertext") in centers_data:
            candidate = point.get("hovertext")

        if candidate and (candidate in centers_data or candidate in CITY_COORDS or candidate in centers_details):
            selected = candidate

    return create_map_figure(selected), create_center_card(selected), selected



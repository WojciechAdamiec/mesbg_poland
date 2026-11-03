import json
from datetime import datetime
from zoneinfo import ZoneInfo

import dash
import dash_mantine_components as dmc
from dash import Dash
import download_data

# Dash Mantine Components v3 requires React 19.
dash._dash_renderer._set_react_version("19.2.4")


APP_TITLE = "MESBG Poland"
APP_DESCRIPTION = "Data collector and visualiser for Polish MESBG League tournaments"
APP_URL = "https://mesbg-poland.plotly.app"

# Link previews need absolute image URLs; Dash's auto-generated page tags are disabled as they would be empty.
app = Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    include_pages_meta=False,
    meta_tags=[
        {"name": "description", "content": APP_DESCRIPTION},
        {"property": "og:type", "content": "website"},
        {"property": "og:site_name", "content": APP_TITLE},
        {"property": "og:title", "content": APP_TITLE},
        {"property": "og:description", "content": APP_DESCRIPTION},
        {"property": "og:image", "content": f"{APP_URL}/assets/banner.png"},
        {"name": "twitter:card", "content": "summary_large_image"},
    ],
)


def get_last_update_text():
    try:
        with open("data/metadata.json", "r", encoding="utf-8") as f:
            metadata = json.load(f)
        dt = datetime.fromisoformat(metadata["time"]).astimezone(ZoneInfo("Europe/Warsaw"))
        return f"Last update: {dt.strftime('%Y-%m-%d %H:%M')}"
    except (FileNotFoundError, KeyError, ValueError):
        return "Last update: unknown"


nav = dmc.Box([
    dmc.NavLink(label="Home", href="/", active="exact"),
    dmc.NavLink(
        label="Rankings",
        active="children",
        childrenOffset=28,
        children=[
            dmc.NavLink(
                label="Main Ranking",
                href="/ranking_main",
                active="exact-with-search",
            ),
            dmc.NavLink(
                label="Master Ranking",
                href="/ranking_master",
                active="exact-with-search",
            ),
            dmc.NavLink(
                label="Online Ranking",
                href="/ranking_online",
                active="exact-with-search",
            ),
        ],
    ),
    dmc.NavLink(
        label="Stats",
        active="children",
        childrenOffset=28,
        children=[
            dmc.NavLink(
                label="Pickrate vs Winrate",
                href="/stats/pickrate_vs_winrate",
                active="exact-with-search",
            ),
            dmc.NavLink(
                label="Army List Winrates",
                href="/stats/army_list_winrates",
                active="exact-with-search",
            ),
            dmc.NavLink(
                label="Player Profiles",
                href="/stats/player_profiles",
                active="exact-with-search",
            ),
            dmc.NavLink(
                label="Player Comparison",
                href="/stats/player_comparison",
                active="exact-with-search",
            ),
        ],
    ),
    dmc.NavLink(
        label="Hall of Fame",
        active="children",
        childrenOffset=28,
        children=[
            dmc.NavLink(
                label="2026 Winners",
                href="/hall_of_fame/2026_winners",
                active="exact-with-search",
            ),
            dmc.NavLink(
                label="2026 Online Winners",
                href="/hall_of_fame/2026_online_winners",
                active="exact-with-search",
            ),
            dmc.NavLink(
                label="2027 Nations Cup",
                href="/hall_of_fame/nations_cup_2027",
                active="exact-with-search",
            ),
        ],
    ),
    dmc.NavLink(label="Masters", href="/masters", active="exact"),
    dmc.NavLink(label="Centers", href="/centers", active="exact"),
    dmc.NavLink(label="Articles", href="/articles", active="partial"),
])

top_bar = dmc.Box(
    dmc.Group(
        [
            dmc.Text(
                "MESBG Poland", 
                size="xl", 
                style={
                    "color": "#00ffff",
                    "fontFamily": "Orbitron, monospace",
                    "fontWeight": "900",
                    "fontSize": "28px",
                    "letterSpacing": "3px",
                    "textTransform": "uppercase",
                    "textShadow": "0 0 2px #00ffff, 0 0 2px #00ffff, 0 0 3px #00ffff",
                    "margin": "2px",
                }
            ),
            dmc.Text(
                get_last_update_text(),
                size="lg",
                style={
                    "color": "#00ffff",
                    "fontFamily": "Orbitron, monospace",
                    "opacity": 0.8,
                },
            ),
        ],
        justify="space-between",
        align="center",
        style={"width": "100%", "height": "100%"},
    ),
    className="metro-header",
    style={"padding": "15px 25px"},
)

app.layout = dmc.MantineProvider(
    dmc.AppShell(
        [
            dmc.AppShellHeader(top_bar),
            dmc.AppShellNavbar(nav),
            dmc.AppShellMain(dash.page_container),
        ],
        padding="xl",
        header={"height": 70},
        navbar={"width": 220},
    )
)

if __name__ == "__main__":
    download_data.download_data()
    app.run(debug=True)
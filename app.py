import dash
import dash_mantine_components as dmc
from dash import Dash


app = Dash(__name__, use_pages=True)


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
    dmc.NavLink(label="Stats", href="/stats", active="exact"),
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
    app.run(debug=True)
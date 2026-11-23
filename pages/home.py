import dash
import dash_mantine_components as dmc
from dash_iconify import DashIconify


dash.register_page(__name__, path="/", name="Home")


FEATURES = [
    {
        "title": "Rankings",
        "description": "Follow the main, master, and online league standings.",
        "href": "/ranking_main_2026",
        "icon": "tabler:trophy",
    },
    {
        "title": "Statistics",
        "description": "Explore army performance, player profiles, and comparisons.",
        "href": "/stats/pickrate_vs_winrate",
        "icon": "tabler:chart-bar",
    },
    {
        "title": "Hall of Fame",
        "description": "Meet the players and teams who made their mark.",
        "href": "/hall_of_fame/2026_winners",
        "icon": "tabler:medal",
    },
    {
        "title": "Masters",
        "description": "See Poland's major MESBG tournaments on the map.",
        "href": "/masters",
        "icon": "tabler:flag",
    },
    {
        "title": "Community centers",
        "description": "Find local clubs, players, and places to play.",
        "href": "/centers",
        "icon": "tabler:map-pin",
    },
    {
        "title": "Articles",
        "description": "Read guides and army-list features from the community.",
        "href": "/articles",
        "icon": "tabler:book",
    },
]

CHANGELOG = [
    (
        "0.10",
        "Optimization and Season 2027",
        "Optimized various pages and views. Added support for Season 2027.",
    ),
    (
        "0.9",
        "Achievements",
        "Added achievements and ranks visible in player profiles and players comparison page.",
    ),
    (
        "0.8",
        "Armies Best Players",
        "Added page allowing to search for best players for each army list. Overhauled player profiles.",
    ),
    (
        "0.7",
        "Homepage Update",
        "Added homepage update with new features and layout.",
    ),
    (
        "0.6",
        "More ways to explore",
        "Player profiles and comparisons, expanded army-list statistics, and the start of the article library.",
    ),
    (
        "0.5",
        "Statistics and champions",
        "Army-list win-rate analysis and the Hall of Fame bring tournament results and winners into focus.",
    ),
    (
        "0.4",
        "The community map",
        "Explore MESBG centers around Poland, with richer profiles for local communities and clubs.",
    ),
    (
        "0.3",
        "More tournament rankings",
        "Master and online rankings, plus a map of major tournaments.",
    ),
    (
        "0.2",
        "The league takes shape",
        "A main league ranking and site navigation make tournament standings easier to explore.",
    ),
    (
        "0.1",
        "The beginning",
        "The first version of the MESBG Poland tournament-data project.",
    ),
]


def feature_card(feature):
    return dmc.Anchor(
        dmc.Card(
            [
                dmc.Group(
                    [
                        DashIconify(icon=feature["icon"], width=26, color="#00ffff"),
                        dmc.Text(feature["title"], fw=700, size="lg", c="#f7efe2"),
                    ],
                    gap="sm",
                ),
                dmc.Text(feature["description"], size="sm", c="#b8c7d9", mt="sm"),
            ],
            withBorder=True,
            shadow="sm",
            radius="md",
            h="100%",
            style={"backgroundColor": "rgba(13, 20, 33, 0.85)"},
        ),
        href=feature["href"],
        underline="never",
        style={"height": "100%"},
    )


def changelog_card(release):
    version, title, description = release
    return dmc.Card(
        [
            dmc.Group(
                [
                    dmc.Badge(f"v{version}", color="cyan", variant="light", size="lg"),
                    dmc.Text(title, fw=700, size="lg", c="#f7efe2"),
                ],
                gap="sm",
            ),
            dmc.Text(description, size="sm", c="#b8c7d9", mt="sm"),
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        style={"backgroundColor": "rgba(13, 20, 33, 0.85)"},
    )


layout = dmc.Container(
    [
        dmc.Stack(
            [
                dmc.Group(
                    [
                        dmc.Title("MESBG Poland", order=1),
                        dmc.Badge("Current version · v0.8", color="cyan", variant="light", size="lg"),
                    ],
                    gap="md",
                    wrap="wrap",
                ),
                dmc.Text(
                    "Your home for Polish Middle-earth Strategy Battle Game tournaments: "
                    "rankings, results, stats, and the community behind them.",
                    size="lg",
                    c="#b8c7d9",
                    maw=760,
                ),
                dmc.Anchor(
                    dmc.Button(
                        "Explore the main ranking",
                        rightSection=DashIconify(icon="tabler:arrow-right", width=18),
                        color="cyan",
                        variant="light",
                    ),
                    href="/ranking_main_2026",
                    underline="never",
                ),
            ],
            gap="md",
            mb=48,
            mt="xl",
        ),
        dmc.Title("Explore the site", order=2, mb="md"),
        dmc.SimpleGrid(
            [feature_card(feature) for feature in FEATURES],
            cols={"base": 1, "sm": 2, "lg": 3},
            spacing="md",
            mb=48,
        ),
        dmc.Group(
            [
                dmc.Title("Changelog", order=2),
            ],
            align="baseline",
            gap="md",
            mb="md",
        ),
        dmc.SimpleGrid(
            [changelog_card(release) for release in CHANGELOG],
            cols={"base": 1, "md": 2},
            spacing="md",
        ),
    ],
    size="lg",
    py="xl",
)

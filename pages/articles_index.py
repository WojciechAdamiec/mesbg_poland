import dash
import dash_mantine_components as dmc

from articles import article_header, load_articles

dash.register_page(__name__, path="/articles", name="Articles")


def _card(article):
    badges, meta_line = article_header(article)
    children = []
    if article["cover"]:
        children.append(dmc.CardSection(dmc.Image(src=article["cover"], h=160, fit="cover")))
    children += [
        dmc.Group(badges, gap="xs", mt="md"),
        dmc.Text(article["title"], fw=700, size="lg", mt="xs"),
        dmc.Text(article["summary"], size="sm", c="dimmed", mt="xs"),
        dmc.Text(meta_line, size="xs", c="dimmed", mt="sm"),
    ]
    return dmc.Anchor(
        dmc.Card(children, withBorder=True, shadow="sm", radius="md", h="100%", className="article-card"),
        href=f"/articles/{article['slug']}",
        underline="never",
    )


def layout(**_):
    articles = load_articles().values()
    return dmc.Container(
        [
            dmc.Title("Articles", order=1, mb="lg"),
            dmc.SimpleGrid(
                [_card(a) for a in articles] or [dmc.Text("No articles yet.")],
                cols={"base": 1, "sm": 2, "lg": 3},
            ),
        ],
        size="lg",
        py="xl",
    )

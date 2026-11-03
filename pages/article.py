import dash
import dash_mantine_components as dmc

from dash import html

from articles import article_header, article_tracker, load_articles, render_body

dash.register_page(__name__, path_template="/articles/<slug>")


def layout(slug=None, **_):
    article = load_articles().get(slug)
    if article is None:
        return dmc.Container(
            [
                dmc.Title("Article not found", order=2),
                dmc.Anchor("Back to articles", href="/articles"),
            ],
            size="md",
            py="xl",
        )

    badges, meta_line = article_header(article)
    header = [
        dmc.Anchor("← All articles", href="/articles", size="sm"),
        dmc.Group(badges, gap="xs", mt="sm"),
        dmc.Title(article["title"], order=1),
    ]
    if meta_line:
        header.append(dmc.Text(meta_line, c="dimmed", size="sm"))
    if article["cover"]:
        header.append(dmc.Image(src=article["cover"], radius="md", className="article-cover"))

    body, toc = render_body(article["body"])
    return dmc.Container(
        html.Div(
            [article_tracker(toc), html.Div([*header, *body], className="article-main")],
            className="article-layout" if toc else "article-layout article-layout-single",
        ),
        size="xl",
        py="xl",
        className="article-page",
    )

import dash_mantine_components as dmc
from dash import html


def rules_box(content):
    return html.Details(
        [
            html.Summary(html.Span("Rules", className="model-name"), className="model-summary"),
            dmc.Stack(content, gap="md", className="ranking-rules-content"),
        ],
        className="model-card ranking-rules",
    )

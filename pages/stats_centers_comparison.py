from urllib.parse import parse_qsl, urlencode

import dash
import dash_mantine_components as dmc
from dash import Input, Output, callback, ctx, dcc, no_update

from center_profile_components import center_section_blocks, centers, select_center


dash.register_page(__name__, path="/stats/centers_comparison", name="Centers Comparison")

layout = dmc.Box([
    dcc.Location(id="centers-comparison-location", refresh=False),
    dmc.Title("Centers Comparison", order=2, mb="md"),
    dmc.Grid([
        dmc.GridCol(select_center("center-a", "Center A"), span={"base": 12, "md": 6}),
        dmc.GridCol(select_center("center-b", "Center B"), span={"base": 12, "md": 6}),
    ], style={"maxWidth": "900px"}),
    dmc.Box(id="centers-comparison-output", mt="lg"),
], style={"padding": "40px"})


@callback(
    Output("centers-comparison-location", "search"),
    Output("center-a", "value"), Output("center-b", "value"),
    Input("centers-comparison-location", "search"),
    Input("center-a", "value"), Input("center-b", "value"),
)
def sync_centers_url(search, center_a, center_b):
    params = parse_qsl((search or "").lstrip("?"), keep_blank_values=True)
    if ctx.triggered_id in ("center-a", "center-b"):
        params = [(key, value) for key, value in params if key not in ("center_a", "center_b")]
        for key, center in (("center_a", center_a), ("center_b", center_b)):
            if center in centers:
                params.append((key, center))
        query = urlencode(params)
        new_search = f"?{query}" if query else ""
        return (new_search if new_search != (search or "") else no_update), no_update, no_update
    selected_a = next((value for key, value in params if key == "center_a" and value in centers), None)
    selected_b = next((value for key, value in params if key == "center_b" and value in centers), None)
    return (no_update, selected_a if selected_a != center_a else no_update,
            selected_b if selected_b != center_b else no_update)


@callback(
    Output("centers-comparison-output", "children"),
    Input("center-a", "value"), Input("center-b", "value"),
)
def update_comparison(center_a, center_b):
    if center_a not in centers or center_b not in centers:
        return dmc.Text("Select two centers to compare them.", c="dimmed")
    if center_a == center_b:
        return dmc.Text("Select two different centers.", c="dimmed")
    sections_a = center_section_blocks(center_a, centers[center_a])
    sections_b = center_section_blocks(center_b, centers[center_b])
    return dmc.Stack([
        dmc.Grid([
            dmc.GridCol(section_a, span={"base": 12, "lg": 6}),
            dmc.GridCol(section_b, span={"base": 12, "lg": 6}),
        ])
        for section_a, section_b in zip(sections_a, sections_b)
    ], gap="lg")

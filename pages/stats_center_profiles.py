from urllib.parse import parse_qsl, urlencode

import dash
import dash_mantine_components as dmc
from dash import Input, Output, callback, ctx, dcc, no_update

from center_profile_components import center_sections, centers, select_center


dash.register_page(__name__, path="/stats/center_profiles", name="Center Profiles")

layout = dmc.Box([
    dcc.Location(id="center-profile-location", refresh=False),
    dmc.Title("Center Profiles", order=2, mb="md"),
    dmc.Box(select_center("center-profile-select", "Center"), style={"maxWidth": "400px"}),
    dmc.Box(id="center-profile-output", mt="lg"),
], style={"padding": "40px"})


@callback(
    Output("center-profile-location", "search"),
    Output("center-profile-select", "value"),
    Input("center-profile-location", "search"),
    Input("center-profile-select", "value"),
)
def sync_center_url(search, center):
    params = parse_qsl((search or "").lstrip("?"), keep_blank_values=True)
    if ctx.triggered_id == "center-profile-select":
        params = [(key, value) for key, value in params if key != "center"]
        if center in centers:
            params.append(("center", center))
        query = urlencode(params)
        new_search = f"?{query}" if query else ""
        return (new_search if new_search != (search or "") else no_update), no_update
    selected = next((value for key, value in params if key == "center" and value in centers), None)
    return no_update, selected if selected != center else no_update


@callback(Output("center-profile-output", "children"), Input("center-profile-select", "value"))
def update_center_profile(center):
    if center not in centers:
        return dmc.Text("Select a center to see its profile.", c="dimmed")
    return center_sections(center, centers[center])

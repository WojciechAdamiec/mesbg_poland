import dash
import dash_mantine_components as dmc


dash.register_page(__name__, path='/ranking_master')

layout = dmc.Box(
    dmc.Text("This is the Master Ranking page")
)
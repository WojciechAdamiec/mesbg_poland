import dash
import dash_mantine_components as dmc


dash.register_page(__name__, path='/')

layout = dmc.Box("This is the Home page")
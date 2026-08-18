import dash
from dash import dcc
import dash_mantine_components as dmc
from get_main_ranking import get_main_ranking_data


dash.register_page(__name__, path='/ranking_main')


def serve_layout():
    data = get_main_ranking_data()

    rows = [
        dmc.TableTr(
            [
                dmc.TableTd(row["place"]),
                dmc.TableTd(row["displayName"]),
                dmc.TableTd(row["city_name"]),
                dmc.TableTd(row["score"]),
            ]
        )
        for row in data
    ]

    head = dmc.TableThead(
        dmc.TableTr(
            [
                dmc.TableTh("Place"),
                dmc.TableTh("Display Name"),
                dmc.TableTh("City Name"),
                dmc.TableTh("Score"),
            ]
        )
    )
    body = dmc.TableTbody(rows)

    return dmc.Box([
        dmc.Text("This is the Main Ranking page", style={"fontSize": "40px", "marginBottom": "20px"}),
        dcc.Link("Go to Champions Hub Ranking", href="https://championshub.app/mesbg/ranking/mesbg-pl", target="_blank", style={"color": "#00ffff", "text-decoration": "none", "font-size": "16px"}),
        dmc.Table([head, body], highlightOnHover=True, withTableBorder=True, withColumnBorders=True, style={"marginTop": "20px", "width": "30%"}),
    ], style={"paddingLeft": "40px"})


layout = serve_layout


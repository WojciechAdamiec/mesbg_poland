import dash_mantine_components as dmc


def army_stats_table(armies, sort_by="winrate", margin_left="30px"):
    rows = []
    for index, army in enumerate(sorted(armies, key=lambda item: item[sort_by], reverse=True), 1):
        faction = army.get("faction")
        if faction == "Good":
            row_color, text_color = "rgba(47, 158, 68, 0.1)", "#2f9e44"
        elif faction == "Evil":
            row_color, text_color = "rgba(224, 49, 49, 0.1)", "#e03131"
        else:
            row_color, text_color = "transparent", "#868e96"
        rows.append(dmc.TableTr(
            [
                dmc.TableTd(str(index), style={"textAlign": "center"}),
                dmc.TableTd(army["army"]),
                dmc.TableTd(f"{army['winrate']:.1f}%", style={"textAlign": "center"}),
                dmc.TableTd(f"{army['pickrate']:.2f}%", style={"textAlign": "center"}),
                dmc.TableTd(str(army["games"]), style={"textAlign": "center"}),
            ],
            style={"backgroundColor": row_color, "borderLeft": f"4px solid {text_color}"},
        ))

    return dmc.ScrollArea(
        dmc.Table(
            [
                dmc.TableThead(dmc.TableTr([
                    dmc.TableTh("#", style={"textAlign": "center"}),
                    dmc.TableTh("Army list"),
                    dmc.TableTh("Winrate", style={"textAlign": "center"}),
                    dmc.TableTh("Pickrate", style={"textAlign": "center"}),
                    dmc.TableTh("Games", style={"textAlign": "center"}),
                ])),
                dmc.TableTbody(rows),
            ],
            striped=True,
            highlightOnHover=True,
            className="pp-sortable",
            style={"backgroundColor": "#1a1b2e", "color": "white"},
        ),
        type="auto",
        offsetScrollbars=True,
        style={"marginLeft": margin_left},
    )

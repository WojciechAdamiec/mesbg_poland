from urllib.parse import urlencode

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import dcc
from dash_iconify import DashIconify

from army_stats_table import army_stats_table
from center_stats import event_season, hosted_event_counts, load_center_stats


centers, missing_results = load_center_stats()
center_options = [{"label": center, "value": center} for center in centers]
SELECT_STYLES = {
    "input": {"color": "#111827", "backgroundColor": "#ffffff"},
    "dropdown": {"backgroundColor": "#ffffff"},
    "option": {"color": "#111827"},
}
TABLE_STYLE = {"backgroundColor": "#1a1b2e", "color": "white"}


def select_center(select_id, label):
    return dmc.Stack([
        dmc.Text(label, fw=600),
        dmc.Select(
            id=select_id, data=center_options, searchable=True, clearable=True,
            placeholder="Select a center", styles=SELECT_STYLES,
        ),
    ])


def table(headers, rows, empty, separators=()):
    if not rows:
        return dmc.Text(empty, c="dimmed")
    return dmc.ScrollArea(
        dmc.Table([
            dmc.TableThead(dmc.TableTr([dmc.TableTh(header) for header in headers])),
            dmc.TableTbody([
                dmc.TableTr([dmc.TableTd(value) for value in row],
                            style={"borderTop": "3px solid #00ffff"} if index in separators else None)
                for index, row in enumerate(rows)
            ]),
        ], withTableBorder=True, withRowBorders=True, style=TABLE_STYLE),
        type="auto", scrollbars="x", offsetScrollbars=True, className="table-scroll-area",
    )


def ranking_distribution(ranking):
    bands = [
        ("1–10", 10), ("11–30", 30), ("31–50", 50), ("51–70", 70),
        ("71–100", 100), ("101–150", 150), ("151–200", 200),
        ("201–300", 300), ("301+", None),
    ]
    counts = [0] * len(bands)
    for row in ranking:
        place = row.get("place")
        if not isinstance(place, int) or place < 1:
            continue
        for index, (_, upper) in enumerate(bands):
            if upper is None or place <= upper:
                counts[index] += 1
                break
    return [(label, count) for (label, _), count in zip(bands, counts)]


def distribution_chart(data, name, season):
    ranking = data["ranking" if season == 2026 else "ranking_2027"]
    bands = ranking_distribution(ranking)
    total = sum(count for _, count in bands)
    if not total:
        return dmc.Text("No ranking data available for this center.", c="dimmed")
    percentages = [count * 100 / total for _, count in bands]
    figure = go.Figure(go.Bar(
        x=percentages,
        y=[label for label, _ in bands],
        orientation="h",
        marker_color="#00bcd4",
        customdata=[count for _, count in bands],
        text=[f"{count} ({percentage:.1f}%)" for (_, count), percentage in zip(bands, percentages)],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="Rank %{y}<br>%{customdata} players (%{x:.1f}%)<extra></extra>",
    ))
    figure.update_layout(
        height=400, margin={"l": 85, "r": 100, "t": 15, "b": 50},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        xaxis={"title": "Share of ranked players", "rangemode": "tozero", "ticksuffix": "%"},
        yaxis={"type": "category", "autorange": "reversed"}, showlegend=False,
    )
    return dcc.Graph(figure=figure, config={"displayModeBar": False},
                     id={"type": "center-distribution", "center": name, "season": season})


def trophy_row(trophies, kind, label):
    colors = {1: "#ffd700", 2: "#c0c0c0", 3: "#cd7f32"}
    def card(trophy):
        names = ", ".join(player["name"] for player in trophy["players"])
        details = f'{trophy["date"]} · {trophy["event"]} · #{trophy["place"]}'
        if trophy.get("team_name"):
            details += f' · {trophy["team_name"]}'
        return dmc.Tooltip(
            label=f"{details} · {names}",
            withArrow=True, events={"hover": True, "focus": True, "touch": True},
            children=dmc.Paper(
                dmc.Group([
                    DashIconify(icon="tabler:trophy-filled", color=colors[trophy["place"]], width=40),
                    dmc.Stack([
                        dmc.Text(player["name"], size="sm", ta="center",
                                 style={"whiteSpace": "nowrap", "overflow": "hidden", "textOverflow": "ellipsis"})
                        for player in trophy["players"]
                    ], gap=0, justify="center",
                        style={"minWidth": 0, "flex": 1, "maxHeight": "76px", "overflowY": "auto"}),
                ], gap="xs", wrap="nowrap", align="center", style={"height": "100%"}),
                p="xs", withBorder=True, bg="dark.7", radius="md",
                style={"width": "210px", "height": "100px", "boxSizing": "border-box", "paddingLeft": "16px"},
                attributes={"tabIndex": 0, "aria-label": f"{details} · {names}"},
            ),
        )

    return dmc.Group([
        dmc.Text(label, fw=600, style={"flex": "0 0 110px"}),
        dmc.Box(
            [card(trophy) for trophy in trophies if trophy["type"] == kind]
            or [dmc.Text("—", c="dimmed")],
            style={
                "display": "grid", "gridTemplateColumns": "repeat(auto-fill, 210px)",
                "gap": "8px", "flex": 1, "minWidth": 0, "overflowX": "auto",
            },
        ),
    ], gap="sm", align="center", wrap="nowrap")


def center_ranking_table(ranking):
    rows = []
    previous_place = None
    center_place = None
    for index, row in enumerate(ranking, 1):
        national_place = row.get("place")
        if national_place is not None and (index == 1 or national_place != previous_place):
            center_place = index
        score = row.get("score")
        score_label = str(score) if score is not None else "-"
        if national_place is not None:
            score_label += f" (#{national_place})"
        rows.append([
            center_place if national_place is not None else "-", score_label,
            dcc.Link(
                row.get("displayName") or row["player_id"],
                href="/stats/player_profiles?" + urlencode({"player": row["player_id"]}),
                style={"color": "#00ffff"},
            ), row.get("city_name") or "-",
        ])
        previous_place = national_place
    return table(["#", "Score", "Player", "City"], rows, "No ranked players.")


def center_stat_card(label, value, values):
    place = 1 + sum(other > value for other in values)
    return dmc.Paper(
        dmc.Stack([
            dmc.Text(label, c="dimmed"),
            dmc.Text(f"{value} ({place}/{len(values)})", fw=700, size="xl"),
        ], gap=0),
        withBorder=True, p="md", bg="dark.7",
    )


def center_section_blocks(name, data):
    event_counts = hosted_event_counts(data["events"])
    trophy_counts = {year: sum(event_season(trophy) == year for trophy in data["trophies"])
                     for year in (2026, 2027)}
    all_event_counts = [hosted_event_counts(center["events"]) for center in centers.values()]
    all_trophy_counts = [
        {year: sum(event_season(trophy) == year for trophy in center["trophies"])
         for year in (2026, 2027)}
        for center in centers.values()
    ]
    event_rows = [
        [event.get("date") or "-", event.get("name") or "-", event.get("tournament_type") or "-",
         (event.get("city") or {}).get("name") or "-"]
        for event in data["events"]
    ]
    event_separators = {
        index for index in range(1, len(data["events"]))
        if event_season(data["events"][index - 1]) == 2027
        and event_season(data["events"][index]) == 2026
    }
    army_rows = [{**army, "army": army["name"]} for army in data["armies"]]
    return [
        dmc.Stack([
            dmc.Title(name, order=3),
            dmc.Group([
                center_stat_card("Hosted Events (2026)", event_counts[2026],
                                 [counts[2026] for counts in all_event_counts]),
                center_stat_card("Active Players (2026)", len(data["ranking"]),
                                 [len(center["ranking"]) for center in centers.values()]),
                center_stat_card("Trophies (2026)", trophy_counts[2026],
                                 [counts[2026] for counts in all_trophy_counts]),
                center_stat_card("Hosted Events (2027)", event_counts[2027],
                                 [counts[2027] for counts in all_event_counts]),
                center_stat_card("Active Players (2027)", len(data["ranking_2027"]),
                                 [len(center["ranking_2027"]) for center in centers.values()]),
                center_stat_card("Trophies (2027)", trophy_counts[2027],
                                 [counts[2027] for counts in all_trophy_counts]),
            ]),
        ], gap="sm"),
        dmc.Stack([dmc.Title("Ranking Distribution 2026", order=4),
                   distribution_chart(data, name, 2026)], gap="sm"),
        dmc.Stack([dmc.Title("Ranking Distribution 2027", order=4),
                   distribution_chart(data, name, 2027)], gap="sm"),
        dmc.Stack([
            dmc.Title("Tournament Trophies 2026", order=4),
            dmc.Alert(f"Results are unavailable for {missing_results} qualifying events.", color="yellow")
            if missing_results else None,
        ], gap="sm"),
        trophy_row([t for t in data["trophies"] if event_season(t) == 2026], "MASTER", "Masters:"),
        trophy_row([t for t in data["trophies"] if event_season(t) == 2026], "CHALLENGER", "Challengers:"),
        dmc.Stack([dmc.Title("Tournament Trophies 2027", order=4)], gap="sm"),
        trophy_row([t for t in data["trophies"] if event_season(t) == 2027], "MASTER", "Masters:"),
        trophy_row([t for t in data["trophies"] if event_season(t) == 2027], "CHALLENGER", "Challengers:"),
        dmc.Stack([dmc.Title("2026 Center Ranking", order=4), center_ranking_table(data["ranking"])], gap="sm"),
        dmc.Stack([dmc.Title("2027 Center Ranking", order=4), center_ranking_table(data["ranking_2027"])], gap="sm"),
        dmc.Stack([dmc.Title("Hosted Events", order=4),
                   table(["Date", "Event", "Type", "City"], event_rows, "No mapped events.", event_separators)],
                  gap="sm"),
        dmc.Stack([
            dmc.Title("Local Meta Snapshot", order=4),
            army_stats_table(army_rows, sort_by="games", margin_left=0)
            if army_rows else dmc.Text("No recorded battles.", c="dimmed"),
        ], gap="sm"),
    ]


def center_sections(name, data):
    return dmc.Stack(center_section_blocks(name, data), gap="sm")



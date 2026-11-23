from collections import Counter
from urllib.parse import parse_qsl, urlencode

import dash
import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import Input, Output, callback, ctx, dcc, no_update
from achievements import (
    ACHIEVEMENTS, PLAYER_RANKS, achievement_stage, format_achievement_count,
    rank_index_for_count, total_achievement_stages, unlocked_stage_count,
)
from player_profile_stats import ArmyExpertise, seasonal_trophies, unique_trophy_players
from store import load_armies, load_battles, load_main_ranking, load_main_ranking_2027, load_master_ranking, load_online_ranking, load_player_profiles
from tags import render_tagged_text, styled_tooltip, text_with_tag_descriptions


dash.register_page(__name__, path="/stats/player_profiles", name="Player Profiles")


def _achievement_percentages(player_profiles):
    if not player_profiles or any(not isinstance(p.get("achievements"), list) for p in player_profiles):
        return None
    counts = Counter(name for player in player_profiles for name in set(player["achievements"]))
    percentages = {name: count * 100 / len(player_profiles) for name, count in counts.items()}
    for achievement in ACHIEVEMENTS:
        if achievement.stage_count <= 1:
            continue
        stages = [
            achievement_stage(achievement, player["achievements"], player.get("achievement_progress"))
            for player in player_profiles
        ]
        percentages[achievement.name] = (
            None if any(stage is None for stage in stages) else [
                sum(stage >= target for stage in stages) * 100 / len(player_profiles)
                for target in range(1, achievement.stage_count + 1)
            ]
        )
    return percentages


profiles = load_player_profiles()
profile_by_id = {p["player_id"]: p for p in profiles}
achievement_percentages = _achievement_percentages(profiles)
main_ranking = load_main_ranking()
main_place_by_id = {p["player_id"]: p.get("place") for p in main_ranking}
rankings_by_season = {2026: main_ranking, 2027: load_main_ranking_2027()}
online_place_by_id = {p.get("player_id"): p.get("place") for p in load_online_ranking()}
master_place_by_name = {(p.get("displayName") or "").strip(): p.get("place") for p in load_master_ranking()}
battles = load_battles()
trophies_by_player = seasonal_trophies(battles, rankings_by_season)
army_expertise = ArmyExpertise(battles, main_ranking, load_armies())
player_options = [
    {"label": (p["displayName"] or p["player_id"]).strip(), "value": p["player_id"]}
    for p in sorted(profiles, key=lambda item: (item["displayName"] or "").strip().lower())
]
default_player = None


def _rank_progress(unlocked_achievements, progress_by_name=None):
    if not isinstance(unlocked_achievements, list):
        return None
    total = total_achievement_stages(ACHIEVEMENTS)
    if not total:
        return None
    count = unlocked_stage_count(ACHIEVEMENTS, set(unlocked_achievements), progress_by_name)
    if count is None:
        return None
    rank_index = rank_index_for_count(count, total)
    return count, total, rank_index


def _rank_distribution(player_profiles):
    counts = [0] * len(PLAYER_RANKS)
    unavailable = 0
    for profile in player_profiles:
        progress = _rank_progress(profile.get("achievements"), profile.get("achievement_progress"))
        if progress is None:
            unavailable += 1
        else:
            counts[progress[2]] += 1
    return counts, unavailable


def _rank_distribution_chart(player_profiles, selected_rank):
    counts, _ = _rank_distribution(player_profiles)
    total = sum(counts)
    if not total:
        return dmc.Stack([
            dmc.Title("Rank Distribution", order=5),
            dmc.Text("Rank distribution is unavailable until player achievements are calculated.", c="dimmed"),
        ], gap="xs")
    percentages = [count * 100 / total for count in counts]
    figure = go.Figure(go.Bar(
        x=[f"{name} ({threshold}%)" for name, threshold, _ in PLAYER_RANKS],
        y=percentages,
        marker={
            "color": [color for _, _, color in PLAYER_RANKS],
            "line": {
                "color": ["white" if index == selected_rank else "rgba(0,0,0,0)"
                          for index in range(len(PLAYER_RANKS))],
                "width": [2 if index == selected_rank else 0 for index in range(len(PLAYER_RANKS))],
            },
        },
        hovertemplate="%{x}<br>Players: %{y:.1f}%<extra></extra>",
    ))
    figure.update_layout(
        height=400,
        margin={"l": 60, "r": 30, "t": 15, "b": 130},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#ffffff"},
        xaxis={"tickangle": -45, "type": "category"},
        yaxis={"title": "Players (%)", "rangemode": "tozero", "ticksuffix": "%",
               "gridcolor": "rgba(255,255,255,0.2)"},
        hoverlabel={"bgcolor": "#1a1b2e", "font": {"color": "#ffffff"}},
    )
    return dmc.Stack([
        dmc.Title("Rank Distribution", order=5),
        dmc.Text("Percentages exclude players without calculated achievements.", size="sm", c="dimmed"),
        dmc.ScrollArea(
            dcc.Graph(figure=figure, config={"displayModeBar": False}, style={"minWidth": "1100px"}),
            type="auto", scrollbars="x",
        ),
    ], gap="xs")


def _player_rank_section(profile, player_profiles):
    progress = _rank_progress(profile.get("achievements"), profile.get("achievement_progress"))
    if progress is None:
        return dmc.Stack([
            dmc.Text("Player rank is unavailable until achievements are calculated.", c="dimmed"),
            _rank_distribution_chart(player_profiles, None),
        ])

    count, total, rank_index = progress
    name, _, color = PLAYER_RANKS[rank_index]
    percent = count * 100 / total
    track = []
    for index, (rank_name, rank_threshold, rank_color) in enumerate(PLAYER_RANKS):
        required = (rank_threshold * total + 99) // 100
        status = "You already have this" if count >= required else f"You need {required - count} more to get this"
        detail = f"{rank_name}: {rank_threshold}%, {required}/{total} achievements needed. {status}."
        track.append(dmc.Tooltip(
            label=dmc.Stack([
                dmc.Text(f"{rank_name}: {rank_threshold}%", fw=700),
                dmc.Text(f"{required}/{total} achievements needed"),
                dmc.Text(status),
            ], gap=2),
            children=dmc.Paper(
                dmc.Stack([
                    _asset_icon("achievement.png", rank_color, 32),
                    dmc.Text(rank_name, fw=700, size="sm", ta="center"),
                    dmc.Text(f"{rank_threshold}%", size="sm", c="dimmed"),
                ], align="center", gap=4),
                withBorder=True, radius="md", p=4,
                style={
                    "backgroundColor": "#1a1b2e",
                    "borderColor": rank_color if index == rank_index else "#373a40",
                    "borderWidth": "2px" if index == rank_index else "1px",
                    "minWidth": "80px",
                },
                attributes={
                    "aria-label": detail + (" Current rank." if index == rank_index else ""),
                    "tabIndex": 0,
                },
            ),
            withArrow=True,
            events={"hover": True, "focus": True, "touch": True},
        ))

    return dmc.Stack([
        dmc.Paper(
            dmc.Group([
                _asset_icon("achievement.png", color, 42),
                dmc.Text(f"{name} ({count}/{total} {percent:.1f}%)", fw=700, size="xl"),
            ], gap="md"),
            withBorder=True, radius="md", p="sm",
            style={"backgroundColor": "#1a1b2e", "width": "fit-content", "maxWidth": "100%"},
        ),
        dmc.ScrollArea(
            dmc.Group(track, wrap="nowrap", gap=4, align="stretch"),
            type="auto", scrollbars="x", offsetScrollbars=True,
        ),
        _rank_distribution_chart(player_profiles, rank_index),
    ], gap="sm", style={"maxWidth": "1356px", "width": "100%"})


def _stat_card(label, value):
    return dmc.Paper(
        dmc.Stack([dmc.Text(label, size="md", c="dimmed", ta="center"),
                   dmc.Text(str(value), fw=700, size="1.75rem", ta="center")], gap=0),
        withBorder=True,
        p="md",
        bg="dark.7",
        c="white",
    )


def _table(title, rows, columns):
    """columns: list of (header, key)."""
    header = dmc.TableThead(dmc.TableTr([dmc.TableTh(h) for h, _ in columns]))
    body = dmc.TableTbody(
        [
            dmc.TableTr([dmc.TableTd(_fmt(row.get(key))) for _, key in columns])
            for row in rows
        ]
    )
    return dmc.Stack(
        [
            dmc.Title(title, order=4),
            dmc.ScrollArea(
                dmc.Table(
                    [header, body],
                    className="pp-sortable",
                    highlightOnHover=True,
                    withTableBorder=True,
                    withRowBorders=True,
                    style={"backgroundColor": "#1a1b2e", "color": "white"},
                ),
                h=442 if len(rows) > 10 else None,
                type="auto",
                scrollbars="xy",
                offsetScrollbars=True,
                className="table-scroll-area pp-profile-table-scroll",
                style={"width": "fit-content", "maxWidth": "100%"},
            ) if rows else dmc.Text("No data", c="dimmed"),
        ]
    )


def _fmt(value):
    return "-" if value is None else str(value)


def _winrate_rows(rows):
    return [{**row, "winrate": f"{row['winrate']}%"} for row in rows]


SORT_OPTIONS = [
    {"label": "Sort by winrate", "value": "winrate"},
    {"label": "Sort by games played", "value": "games"},
]


def _winrate_chart(rows, key, sort_by="winrate"):
    rows = sorted(rows, key=lambda r: (-r[sort_by], -r["games"], r[key] or ""))
    figure = go.Figure(
        go.Bar(
            x=[row[key] for row in rows],
            y=[row["winrate"] for row in rows],
            customdata=[row["games"] for row in rows],
            text=[row["games"] for row in rows],
            textposition="outside",
            cliponaxis=False,
            marker_color="#22b8cf",
            hovertemplate="<b>%{x}</b><br>Winrate: %{y:.1f}%<br>Games: %{customdata}<extra></extra>",
        )
    )
    figure.update_layout(
        height=380,
        margin={"l": 50, "r": 20, "t": 30, "b": 130},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#ffffff"},
        xaxis={"tickangle": -45, "type": "category"},
        yaxis={"range": [0, 110], "title": "Winrate (%)", "gridcolor": "rgba(255,255,255,0.2)"},
        hoverlabel={"bgcolor": "#1a1b2e", "font": {"color": "#ffffff"}},
    )
    graph = dcc.Graph(
        figure=figure,
        config={"displayModeBar": False},
        style={"width": f"{max(600, 60 * len(rows))}px"},
    )
    return dmc.ScrollArea(graph, type="always", offsetScrollbars=True)


def _chart_section(title, control_id, box_id, player_id, rows_key, sort_by="winrate"):
    p = profile_by_id.get(player_id)
    return dmc.Stack(
        [
            dmc.Title(title, order=4),
            dmc.SegmentedControl(
                id=control_id,
                data=SORT_OPTIONS,
                value=sort_by,
                styles={
                    "root": {"backgroundColor": "#1a1b2e"},
                    "label": {"color": "#d1d5db"},
                    "indicator": {"backgroundColor": "#0e7490"},
                },
                color="cyan",
            ),
            dmc.Box(_winrate_chart(p[rows_key], "army_name", sort_by) if p else None, id=box_id),
        ]
    )


ARMY_COLS = [("Army list", "army_name"), ("Games", "games"), ("Wins", "wins"),
             ("Draws", "draws"), ("Losses", "losses"), ("Winrate", "winrate")]
PLAYER_COLS = [("Player", "displayName")] + ARMY_COLS[1:]


def build_top(player_id):
    p = profile_by_id.get(player_id)
    if not p:
        return dmc.Text("Select a player to see their profile.", c="dimmed")
    return dmc.Stack(
        [
            dmc.Title(p["displayName"], order=3),
            dmc.ScrollArea(
                dmc.SimpleGrid(
                    [
                        _stat_card("Main ranking place", p.get("main_ranking_place") or "-"),
                        _stat_card("Master ranking place", _fmt(master_place_by_name.get((p.get("displayName") or "").strip()))),
                        _stat_card("Online ranking place", _fmt(online_place_by_id.get(player_id))),
                        _stat_card("Tournament locations", p.get("locations_count", "-")),
                        _stat_card("Games played", p["games_played"]),
                        _stat_card("Winrate", f"{p['winrate']}%"),
                        _stat_card("Wins", p["wins"]),
                        _stat_card("Draws", p["draws"]),
                        _stat_card("Losses", p["losses"]),
                        _stat_card("Player trophies", len(unique_trophy_players(trophies_by_player.get(player_id, {})))),
                        _stat_card("Army specialties", len(army_expertise.for_player(player_id, p["army_lists"]))),
                        _stat_card("Achievements unlocked", format_achievement_count(p.get("achievements_count"))),
                    ],
                    cols=6,
                    style={"minWidth": "960px"},
                ),
                type="auto",
                scrollbars="x",
            ),
        ]
    )


def build_profile_sections(player_id):
    p = profile_by_id.get(player_id)
    if not p:
        return None, None, None, None, None, None
    return (
        _table("Army lists used", _winrate_rows(p["army_lists"]), ARMY_COLS),
        _table("Army lists played against", _winrate_rows(p["opponent_army_lists"]), ARMY_COLS),
        _table("Opponents played against", _winrate_rows(p["opponents"]), PLAYER_COLS),
        _locations_section(p.get("tournament_locations")),
        dmc.Stack([
            _trophies(trophies_by_player.get(player_id, {}).get(season, []), season)
            for season in (2026, 2027)
        ], gap="lg"),
        _expertise_section(army_expertise.for_player(player_id, p["army_lists"])),
    )


def _locations_section(locations):
    if locations is None:
        content = dmc.Text("Tournament locations have not been calculated yet.", c="dimmed")
    elif not locations:
        content = dmc.Text("No tournament locations recorded.", c="dimmed")
    else:
        content = dmc.Group(
            [
                dmc.Paper(
                    dmc.Text(name, fw=700, size="lg", ta="center", style={"overflowWrap": "anywhere"}),
                    withBorder=True, radius="md", p="md",
                    style={"backgroundColor": "#1a1b2e", "width": "180px", "flex": "0 0 180px"},
                )
                for name in locations
            ],
            wrap="wrap", align="stretch", gap=16, style={"maxWidth": "1356px"},
        )
    return dmc.Stack([dmc.Title("Tournament Locations", order=4), content])


def _asset_icon(filename, color, size):
    image = f'url("{dash.get_asset_url(f"icons/{filename}")}")'
    return dmc.Box(
        style={
            "width": f"{size}px",
            "height": f"{size}px",
            "backgroundColor": color,
            "maskImage": image,
            "maskSize": "contain",
            "maskRepeat": "no-repeat",
            "maskPosition": "center",
            "WebkitMaskImage": image,
            "WebkitMaskSize": "contain",
            "WebkitMaskRepeat": "no-repeat",
            "WebkitMaskPosition": "center",
            "flexShrink": 0,
        },
        **{"aria-hidden": "true"},
    )


def _expertise_section(armies):
    cards = []
    for army in armies:
        place = army["place"]
        color = (
            "#facc15" if place == 1
            else "#cbd5e1" if place <= 5
            else "#cd7f32"
        )
        cards.append(
            dmc.Paper(
                dmc.Stack(
                    [
                        dmc.Box(
                            [
                                dmc.Text(f"#{place}", size="lg", fw=700, ta="center"),
                                _asset_icon("inspiration-icon.png", color, 42),
                                dmc.Text(
                                    f'{army["adjusted_winrate"]}%',
                                    size="sm",
                                    fw=700,
                                    ta="center",
                                    attributes={"aria-label": f'Adjusted win ratio: {army["adjusted_winrate"]}%'},
                                ),
                            ],
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "1fr 42px 1fr",
                                "alignItems": "center",
                                "width": "100%",
                            },
                        ),
                        dmc.Text(
                            army["army_name"], fw=700, size="lg", ta="center",
                            style={"overflowWrap": "anywhere"},
                        ),
                    ],
                    align="center",
                    gap="xs",
                ),
                withBorder=True,
                radius="md",
                p="md",
                style={"backgroundColor": "#1a1b2e", "width": "180px", "flex": "0 0 180px"},
            )
        )
    return dmc.Stack(
        [
            dmc.Title("Army Specialties", order=4),
            dmc.Group(cards, wrap="wrap", align="stretch", gap=16, style={"maxWidth": "1356px"})
            if cards else dmc.Text("No army lists ranked in the top 10.", c="dimmed"),
        ]
    )


TROPHY_BRONZE = "#cd7f32"
TROPHY_SILVER = "#cbd5e1"
TROPHY_GOLD = "#facc15"
STAGE_COLORS = ("#a07855", "#a8a29e", TROPHY_BRONZE, TROPHY_SILVER, TROPHY_GOLD)
TEN_STAGE_COLORS = (
    "#a07855", "#c48a69", "#a8a29e", "#e7dfc7", "#c77c52",
    "#d4b04c", TROPHY_BRONZE, "#94a3b8", TROPHY_SILVER, TROPHY_GOLD,
)


def _stage_color(stage, total):
    if not stage:
        return "#6b7280"
    if total == len(TEN_STAGE_COLORS):
        return TEN_STAGE_COLORS[stage - 1]
    if total <= len(STAGE_COLORS):
        return STAGE_COLORS[len(STAGE_COLORS) - total + stage - 1]
    return STAGE_COLORS[round((stage - 1) * (len(STAGE_COLORS) - 1) / (total - 1))]


def _achievements_section(unlocked_achievements, sort_by="default", progress_by_name=None):
    cards = []
    achievements = list(enumerate(ACHIEVEMENTS, start=1))
    unlocked_names = set(unlocked_achievements or [])

    def stage_for(achievement):
        if unlocked_achievements is None:
            return None
        return achievement_stage(achievement, unlocked_names, progress_by_name)

    def percentages_for(achievement):
        if achievement_percentages is None:
            return None
        value = achievement_percentages.get(
            achievement.name, [0] * achievement.stage_count if achievement.stage_count > 1 else 0
        )
        if value is None:
            return None
        return value if isinstance(value, list) else [value]

    def displayed_percentage(achievement):
        values = percentages_for(achievement)
        if values is None:
            return None
        stage = stage_for(achievement)
        index = 0 if stage is None or stage == achievement.stage_count else max(0, stage - 1)
        return values[index]

    if sort_by == "rarity":
        achievements = sorted(
            achievements,
            key=lambda numbered: (
                not bool(stage_for(numbered[1])),
                -(displayed_percentage(numbered[1]) or 0),
            ),
        )
    for number, achievement in achievements:
        stage = stage_for(achievement)
        unlocked = bool(stage)
        status = ("unavailable" if stage is None else "locked" if stage == 0 else
                  "unlocked" if stage == achievement.stage_count else "partially unlocked")
        color = _stage_color(stage, achievement.stage_count)
        percentage_value = displayed_percentage(achievement)
        percentage = f"{percentage_value:.1f}%" if percentage_value is not None else "-"
        percentage_label = (f"{percentage} of players unlocked this achievement"
                            if percentage_value is not None else "Unlock percentage unavailable")
        progress = ((progress_by_name or {}).get(achievement.name)
                    if achievement.show_progress and stage is not None and stage < achievement.stage_count else None)
        progress_label = (
            f"{progress['current']}{achievement.progress_unit} / {progress['target']}{achievement.progress_unit}"
            if progress else None
        )
        previous_target = achievement.stages[stage - 1] if achievement.stages and stage else 0
        progress_value = (
            min(100, max(0, 100 * (progress["current"] - previous_target)
                         / (progress["target"] - previous_target)))
            if progress else 0
        )
        values = percentages_for(achievement)
        tooltip = [
            f"Stage {index}" + (
                f" ({achievement.stage_labels[index - 1]})" if achievement.stage_labels else
                f" ({achievement.stages[index - 1]}{achievement.progress_unit})" if achievement.stages else ""
            )
            + f": {values[index - 1]:.1f}%"
            for index in range(1, achievement.stage_count + 1)
        ] if values is not None else ["Unlock percentages unavailable"]
        title = achievement.name
        if achievement.stage_count > 1:
            title += f" {stage if stage is not None else '?'}/{achievement.stage_count}"
        description = achievement.text_for_stage(stage)
        achievement_text = render_tagged_text(
            description,
            keyword_class="tag-keyword achievement-tag-keyword",
        )
        accessible_achievement_text = text_with_tag_descriptions(description)
        cards.append(
            dmc.Paper(
                dmc.Stack(
                    [
                        _asset_icon(achievement.icon, color, 42),
                        dmc.Text(title, fw=700, size="lg", ta="center"),
                        dmc.Text(
                            achievement_text, size="sm", ta="center",
                            style={"minHeight": "3.75rem", "lineHeight": "1.25rem"},
                        ),
                        dmc.Box(
                            styled_tooltip(
                                achievement.name, tooltip,
                                dmc.Text(
                                    percentage, size="md", fw=700, c="#9ca3af",
                                    tabIndex=0, style={"fontSize": "1.5rem"},
                                    **{"aria-label": percentage_label},
                                ),
                            ),
                            style={
                                "position": "absolute",
                                "top": "8px",
                                "right": "12px",
                                "fontSize": "1.5rem",
                            },
                        ),
                        dmc.Text(
                            str(number), size="md", fw=700, c="#9ca3af",
                            style={
                                "position": "absolute",
                                "top": "8px",
                                "left": "12px",
                                "fontSize": "1.5rem",
                            },
                        ),
                        *([dmc.Stack([
                            dmc.Progress(
                                value=progress_value,
                                color="cyan", size="sm",
                                attributes={"aria-label": f"{achievement.name} progress: {progress_label}"},
                            ),
                            dmc.Text(
                                progress_label, fw=700, c="#9ca3af", ta="center",
                                style={"fontSize": "1.5rem"},
                            ),
                        ], gap=4, style={"width": "100%", "marginTop": "auto"})] if progress else []),
                    ],
                    align="center",
                    gap="xs",
                    style={"flex": 1},
                ),
                withBorder=True,
                radius="md",
                p="md",
                pt="32px",
                style={
                    "backgroundColor": "#1a1b2e",
                    "borderColor": color,
                    "color": "white" if unlocked else "#9ca3af",
                    "position": "relative",
                    "display": "flex",
                    "minHeight": "257px",
                },
                **{"aria-label": (
                    f"{achievement.name}: {status}. {accessible_achievement_text} {percentage_label}"
                )},
            )
        )
    return dmc.Stack([
        *([dmc.Text("Achievements have not been calculated yet.", c="dimmed")]
          if unlocked_achievements is None else []),
        dmc.SimpleGrid(
            cards,
            cols={"base": 1, "sm": 2, "lg": 4},
            spacing=16,
            style={"maxWidth": "1356px", "width": "100%", "gridAutoRows": "1fr"},
        ),
    ])


def _trophies(players, season=None):
    cards = [
        dmc.Paper(
            dmc.Stack(
                [
                    dmc.Box(
                        [
                            dmc.Text(
                                f'#{player["main_ranking_place"]}',
                                size="lg",
                                fw=700,
                                ta="center",
                            ),
                            _asset_icon(
                                "shooting-target-icon.png",
                                (
                                    TROPHY_GOLD if player["main_ranking_place"] <= 10
                                    else TROPHY_SILVER if player["main_ranking_place"] <= 30
                                    else TROPHY_BRONZE
                                ),
                                42,
                            ),
                            dmc.Group(
                                [
                                    _asset_icon("crossed-swords-icon.png", "currentColor", 18),
                                    dmc.Text(str(player["times_defeated"]), size="lg", fw=700),
                                ],
                                gap=4,
                                justify="center",
                                wrap="nowrap",
                                attributes={"aria-label": f'Times defeated: {player["times_defeated"]}'},
                            ),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "1fr 42px 1fr",
                            "alignItems": "center",
                            "width": "100%",
                        },
                    ),
                    dmc.Text(
                        _fmt(player.get("displayName")),
                        fw=700,
                        size="lg",
                        ta="center",
                        style={"overflowWrap": "anywhere"},
                    ),
                ],
                align="center",
                gap="xs",
            ),
            withBorder=True,
            radius="md",
            p="md",
            style={"backgroundColor": "#1a1b2e", "width": "180px", "flex": "0 0 180px"},
        )
        for player in players
    ]
    return dmc.Stack(
        [
            dmc.Title(f"Top Player Trophies {season}" if season else "Top Player Trophies", order=4),
            dmc.Group(
                cards,
                wrap="wrap",
                align="stretch",
                gap=16,
                style={"maxWidth": "1356px"},
            ) if cards else dmc.Text("No defeated players in the main ranking top 50.", c="dimmed"),
        ]
    )


layout = dmc.Box(
    [
        dcc.Location(id="pp-location", refresh=False),
        dmc.Title("Player Profiles", order=2, mb="md"),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Stack(
                        [
                            dmc.Text("Player", fw=600),
                            dmc.Select(
                                id="pp-selected-player",
                                data=player_options,
                                value=default_player,
                                searchable=True,
                                clearable=True,
                                placeholder="Select a player",
                                styles={
                                    "input": {"color": "#111827", "backgroundColor": "#ffffff"},
                                    "dropdown": {"backgroundColor": "#ffffff"},
                                    "option": {"color": "#111827"},
                                },
                            ),
                        ]
                    ),
                    span={"base": 12, "lg": 3},
                ),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            dmc.Box(build_top(default_player), id="pp-top"),
                            dmc.Box(id="pp-armies-table"),
                            _chart_section(
                                "Winrate by army list used", "pp-sort-armies", "pp-chart-armies",
                                default_player, "army_lists",
                            ),
                            dmc.Box(id="pp-opponent-armies-table"),
                            _chart_section(
                                "Winrate against army lists", "pp-sort-opponent-armies",
                                "pp-chart-opponent-armies", default_player, "opponent_army_lists",
                            ),
                            dmc.Box(id="pp-opponents-table"),
                            dmc.Box(id="pp-locations"),
                            dmc.Box(id="pp-trophies"),
                            dmc.Box(id="pp-expertise"),
                            dmc.Box(
                                dmc.Stack([
                                    dmc.Title("Player Achievements", order=4),
                                    dmc.Box(id="pp-player-rank"),
                                    dmc.SegmentedControl(
                                        id="pp-achievement-sort",
                                        data=[
                                            {"label": "Default Order", "value": "default"},
                                            {"label": "Rarity", "value": "rarity"},
                                        ],
                                        value="default",
                                        styles={
                                            "root": {"backgroundColor": "#1a1b2e"},
                                            "label": {"color": "#d1d5db"},
                                            "indicator": {"backgroundColor": "#0e7490"},
                                        },
                                        color="cyan",
                                    ),
                                    dmc.Box(id="pp-achievements-content"),
                                ]),
                                id="pp-achievements",
                                style={"display": "none"},
                            ),
                        ],
                        gap="lg",
                    ),
                    span=12,
                ),
            ]
        ),
    ],
    style={"padding": "40px"},
)


def _sync_player_url(search, player_id, triggered_id):
    params = parse_qsl((search or "").lstrip("?"), keep_blank_values=True)
    if triggered_id == "pp-selected-player":
        params = [(key, value) for key, value in params if key != "player"]
        if player_id:
            params.append(("player", player_id))
        query = urlencode(params)
        new_search = f"?{query}" if query else ""
        return (new_search if new_search != (search or "") else no_update), no_update

    url_player = next((value for key, value in params if key == "player"), None)
    selected = url_player if url_player in profile_by_id else None
    return no_update, selected if selected != player_id else no_update


@callback(
    Output("pp-location", "search"),
    Output("pp-selected-player", "value"),
    Input("pp-location", "search"),
    Input("pp-selected-player", "value"),
)
def sync_player_url(search, player_id):
    return _sync_player_url(search, player_id, ctx.triggered_id)


@callback(
    Output("pp-top", "children"),
    Output("pp-armies-table", "children"),
    Output("pp-opponent-armies-table", "children"),
    Output("pp-opponents-table", "children"),
    Output("pp-locations", "children"),
    Output("pp-trophies", "children"),
    Output("pp-expertise", "children"),
    Input("pp-selected-player", "value"),
)
def update_profile(player_id):
    return (build_top(player_id), *build_profile_sections(player_id))


@callback(
    Output("pp-achievements-content", "children"),
    Output("pp-achievements", "style"),
    Input("pp-selected-player", "value"),
    Input("pp-achievement-sort", "value"),
)
def update_achievements(player_id, sort_by):
    profile = profile_by_id.get(player_id)
    if not profile:
        return None, {"display": "none"}
    return _achievements_section(
        profile.get("achievements"), sort_by, profile.get("achievement_progress")
    ), {}


@callback(
    Output("pp-player-rank", "children"),
    Input("pp-selected-player", "value"),
)
def update_player_rank(player_id):
    profile = profile_by_id.get(player_id)
    return _player_rank_section(profile, profiles) if profile else None


@callback(
    Output("pp-chart-armies", "children"),
    Input("pp-selected-player", "value"),
    Input("pp-sort-armies", "value"),
)
def update_army_chart(player_id, sort_by):
    if player_id not in profile_by_id:
        return None
    return _winrate_chart(profile_by_id[player_id]["army_lists"], "army_name", sort_by)


@callback(
    Output("pp-chart-opponent-armies", "children"),
    Input("pp-selected-player", "value"),
    Input("pp-sort-opponent-armies", "value"),
)
def update_opponent_army_chart(player_id, sort_by):
    if player_id not in profile_by_id:
        return None
    return _winrate_chart(profile_by_id[player_id]["opponent_army_lists"], "army_name", sort_by)

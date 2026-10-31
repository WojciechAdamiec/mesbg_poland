import dash
import dash_mantine_components as dmc
from dash import Input, Output, callback
from download_data import _winrate
from store import (
    load_battles,
    load_main_ranking,
    load_master_ranking,
    load_online_ranking,
    load_player_profiles,
)


dash.register_page(__name__, path="/stats/player_comparison", name="Player Comparison")

profiles = [p for p in load_player_profiles() if p.get("player_id")]
profile_by_id = {p["player_id"]: p for p in profiles}
player_options = [
    {"label": (p["displayName"] or p["player_id"]).strip(), "value": p["player_id"]}
    for p in sorted(profiles, key=lambda item: (item["displayName"] or "").strip().lower())
]

main_place_by_id = {r.get("player_id"): r.get("place") for r in load_main_ranking()}
online_place_by_id = {r.get("player_id"): r.get("place") for r in load_online_ranking()}
# The master ranking has no player ids, so it is matched by display name.
master_place_by_name = {(r.get("displayName") or "").strip(): r.get("place") for r in load_master_ranking()}

# Doubles are excluded, consistently with player profiles.
battles = [b for b in load_battles() if b.get("format") != "DOUBLES" and b.get("result") and len(b["result"]) == 2]
events_by_player = {}
for _battle in battles:
    for _side in ("1", "2"):
        _pid = _battle.get(f"player_{_side}_id")
        if _pid:
            events_by_player.setdefault(_pid, {})[_battle.get("tournament_id")] = _battle.get("tournament_type")


master_record_by_player = {}
for _battle in battles:
    if _battle.get("tournament_type") != "MASTER":
        continue
    for _me, _opp in ((0, 1), (1, 0)):
        _pid = _battle.get(f"player_{_me + 1}_id")
        if not _pid:
            continue
        _record = master_record_by_player.setdefault(_pid, {"games": 0, "wins": 0, "draws": 0})
        _record["games"] += 1
        if _battle["result"][_me] > _battle["result"][_opp]:
            _record["wins"] += 1
        elif _battle["result"][_me] == _battle["result"][_opp]:
            _record["draws"] += 1


def _master_winrate(player_id):
    record = master_record_by_player.get(player_id)
    return _winrate(record["wins"], record["games"], record["draws"]) if record else None


def _events_of_type(player_id, tournament_type):
    return sum(1 for t in events_by_player.get(player_id, {}).values() if t == tournament_type)

HIGHLIGHT = {"backgroundColor": "#14532d", "fontWeight": 700}
TABLE_STYLE = {"backgroundColor": "#1a1b2e", "color": "white"}


def _fmt(value):
    return "-" if value is None else str(value)


def _compare(value_a, value_b, higher_is_better, names):
    """Returns (winner 'A'/'B'/None, comment)."""
    name_a, name_b = names
    if value_a is None and value_b is None:
        return None, "No data"
    if value_b is None:
        return "A", f"{name_a} (only one with data)"
    if value_a is None:
        return "B", f"{name_b} (only one with data)"
    if value_a == value_b:
        return None, "Equal"
    diff = abs(value_a - value_b)
    diff = round(diff, 2) if isinstance(diff, float) else diff
    a_wins = (value_a > value_b) == higher_is_better
    winner = "A" if a_wins else "B"
    name = name_a if a_wins else name_b
    return winner, f"{name} (+{diff})" if higher_is_better else f"{name} ({diff} places higher)"


def _row(label, value_a, value_b, winner, comment):
    return dmc.TableTr(
        [
            dmc.TableTd(label, fw=600),
            dmc.TableTd(_fmt(value_a), style=HIGHLIGHT if winner == "A" else None),
            dmc.TableTd(_fmt(value_b), style=HIGHLIGHT if winner == "B" else None),
            dmc.TableTd(comment),
        ]
    )


def _metric_row(label, value_a, value_b, higher_is_better, names, display=None):
    winner, comment = _compare(value_a, value_b, higher_is_better, names)
    shown_a, shown_b = (display(value_a), display(value_b)) if display else (value_a, value_b)
    return _row(label, shown_a, shown_b, winner, comment)


def _comparison_table(first_header, names, rows):
    return dmc.Table(
        [
            dmc.TableThead(
                dmc.TableTr(
                    [dmc.TableTh(first_header, style={"width": "170px"}),
                     dmc.TableTh(names[0], style={"width": "190px"}),
                     dmc.TableTh(names[1], style={"width": "190px"}),
                     dmc.TableTh("Who is better")]
                )
            ),
            dmc.TableTbody(rows),
        ],
        withTableBorder=True,
        withRowBorders=True,
        style={**TABLE_STYLE, "tableLayout": "fixed", "maxWidth": "900px"},
    )


def _army_label(army):
    if not army:
        return None
    return f"{army['army_name'] or 'Unknown'} - {army['games']} games, {army['winrate']}%"


def _top_armies(profile):
    armies = [a for a in profile["army_lists"] if a.get("army_id") is not None]
    return sorted(armies, key=lambda a: (-a["games"], -a["winrate"]))[:5]


def _army_table(profile_a, profile_b, names):
    top_a, top_b = _top_armies(profile_a), _top_armies(profile_b)
    rows = []
    for i in range(5):
        army_a = top_a[i] if i < len(top_a) else None
        army_b = top_b[i] if i < len(top_b) else None
        rows.append(
            dmc.TableTr(
                [dmc.TableTd(f"#{i + 1}", fw=600), dmc.TableTd(_fmt(_army_label(army_a))),
                 dmc.TableTd(_fmt(_army_label(army_b)))]
            )
        )
    return dmc.Table(
        [
            dmc.TableThead(
                dmc.TableTr(
                    [dmc.TableTh("Rank", style={"width": "170px"}),
                     dmc.TableTh(names[0], style={"width": "300px"}),
                     dmc.TableTh(names[1], style={"width": "300px"})]
                )
            ),
            dmc.TableTbody(rows),
        ],
        withTableBorder=True,
        withRowBorders=True,
        style={**TABLE_STYLE, "tableLayout": "fixed", "maxWidth": "900px"},
    )

def _history(id_a, id_b, name_a, name_b):
    games = [
        b for b in battles
        if {b.get("player_1_id"), b.get("player_2_id")} == {id_a, id_b}
    ]
    wins_a = wins_b = draws = 0
    rows = []
    for b in games:
        flipped = b["player_1_id"] == id_b
        score_a, score_b = (b["result"][1], b["result"][0]) if flipped else (b["result"][0], b["result"][1])
        if score_a > score_b:
            wins_a += 1
            outcome = name_a
        elif score_b > score_a:
            wins_b += 1
            outcome = name_b
        else:
            draws += 1
            outcome = "Draw"
        army_a = b["army_2_name"] if flipped else b["army_1_name"]
        army_b = b["army_1_name"] if flipped else b["army_2_name"]
        scenario = b.get("scenario")
        rows.append({
            "event": b.get("tournament_name"),
            "type": b.get("tournament_type"),
            "scenario": scenario if isinstance(scenario, str) else (scenario.get("name") if isinstance(scenario, dict) else None),
            "army_a": army_a,
            "army_b": army_b,
            "score": f"{score_a} : {score_b}",
            "winner": outcome,
        })
    rows.sort(key=lambda r: r["event"] or "")

    summary = f"{name_a} {wins_a} - {wins_b} {name_b}, draws: {draws} ({len(games)} games)"
    if not rows:
        return dmc.Text("These players have never played each other.", c="dimmed")

    def entry(r):
        return dmc.Paper(
            dmc.Stack(
                [
                    dmc.Group(
                        [dmc.Text(_fmt(r["event"]), fw=700), dmc.Text(f"Type: {_fmt(r['type'])}", c="dimmed"),
                         dmc.Text(f"Scenario: {_fmt(r['scenario'])}", c="dimmed")],
                        gap="lg",
                    ),
                    dmc.Group(
                        [dmc.Text(f"{name_a}: {_fmt(r['army_a'])}"), dmc.Text(f"{name_b}: {_fmt(r['army_b'])}"),
                         dmc.Text(f"Score: {r['score']}", fw=600), dmc.Text(f"Winner: {r['winner']}", fw=600)],
                        gap="lg",
                    ),
                ],
                gap=4,
            ),
            withBorder=True,
            p="sm",
            style=TABLE_STYLE,
        )

    return dmc.Stack(
        [dmc.Text(summary, fw=600), *[entry(r) for r in rows]],
        gap="xs",
        style={"maxWidth": "900px"},
    )

def _name(profile):
    return (profile["displayName"] or profile["player_id"]).strip()


def _select(select_id, label):
    return dmc.GridCol(
        dmc.Stack(
            [
                dmc.Text(label, fw=600),
                dmc.Select(
                    id=select_id,
                    data=player_options,
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
        span={"base": 12, "md": 6},
    )


layout = dmc.Box(
    [
        dmc.Title("Player Comparison", order=2, mb="md"),
        dmc.Box(
            dmc.Grid([_select("pc-player-a", "Player A"), _select("pc-player-b", "Player B")]),
            style={"maxWidth": "900px"},
        ),
        dmc.Space(h="md"),
        dmc.Box(id="pc-output"),
    ]
)


@callback(
    Output("pc-output", "children"),
    Input("pc-player-a", "value"),
    Input("pc-player-b", "value"),
)
def update_comparison(id_a, id_b):
    profile_a, profile_b = profile_by_id.get(id_a), profile_by_id.get(id_b)
    if not profile_a or not profile_b:
        return dmc.Text("Select two players to compare them.", c="dimmed")
    if id_a == id_b:
        return dmc.Text("Select two different players.", c="dimmed")

    name_a, name_b = _name(profile_a), _name(profile_b)
    names = (name_a, name_b)

    def events(tournament_type):
        return _events_of_type(id_a, tournament_type), _events_of_type(id_b, tournament_type)

    rows = [
        _metric_row("Games played", profile_a["games_played"], profile_b["games_played"], True, names),
        _metric_row("Masters played", *events("MASTER"), True, names),
        _metric_row("Challengers played", *events("CHALLENGER"), True, names),
        _metric_row("Locals played", *events("LOCAL"), True, names),
        _metric_row("Online events played", *events("ONLINE"), True, names),
        _metric_row("Winrate", profile_a["winrate"], profile_b["winrate"], True, names,
                    display=lambda v: None if v is None else f"{v}%"),
        _metric_row("Master winrate", _master_winrate(id_a), _master_winrate(id_b), True, names,
                    display=lambda v: None if v is None else f"{v}%"),
        _metric_row("Main ranking place", main_place_by_id.get(id_a), main_place_by_id.get(id_b), False, names),
        _metric_row("Master ranking place", master_place_by_name.get(name_a), master_place_by_name.get(name_b), False, names),
        _metric_row("Online ranking place", online_place_by_id.get(id_a), online_place_by_id.get(id_b), False, names),
    ]
    return dmc.Stack(
        [
            _comparison_table("", names, rows),
            dmc.Title("Top 5 most played armies", order=3, mt="md"),
            _army_table(profile_a, profile_b, names),
            dmc.Title("Head-to-head history", order=3, mt="md"),
            _history(id_a, id_b, name_a, name_b),
        ]
    )
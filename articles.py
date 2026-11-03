"""Loads Markdown articles from ./content/articles and renders them as Dash components.

Article file format:

    ---
    title: Some title
    category: army-list
    expert: Expert name
    redactor: Redactor name
    ---
    Markdown body...

Extra syntax inside the body (each on its own line):

    {{ army_stats: Army of Gundabad | 5 | Medium }}   live stats with optional difficulty rating and label
    :::details Section title             collapsible section, closed by a line with ':::'
    ...markdown...
    :::
    {{ army_list: /assets/x/400.png | Sample list – 400 points }}   army list image in a collapsible section, closed by default; the title after '|' is optional
    :::model Model name                  model profile, closed by a line with ':::'
    points: 100                          optional lines, all of them can be left out
    role: Hero of Valour
    stats: Mv 6" | Fv 6/4 | Sv 4+ | S 5 | D 7 | A 3 | W 3 | C 6+ | I 4+ | Might 3 | Will 3 | Fate 3
    wargear: Sword, Armour               more optional lines, shown below the stats
    heroic actions: Heroic Strike
    keywords: Goblin, Hero
    base size: 40mm
    **Special rule**: How it works.      special rules, one per line, shown below the stats; the description is optional
    ...markdown comment...               shown under the profile card
    :::
    :::scenarios                         scenarios in three groups; list names after the group label
    Dobre: Domination, Hold Ground       unlisted scenarios end up in Niezłe
    Niezłe: ...
    Kiepskie: ...
    :::
    :::points                            points timeline arrow from 400 to 1000+, colored ranges
    Dobre: 400-700                       ranges as 'from-to' or 'from+', comma separated
    Niezłe: 700-900
    Kiepskie: 900+
    :::
"""
import os
import re

import dash_mantine_components as dmc
from dash import dcc, html

from battle import Scenario
from store import load_battles

ARTICLES_DIRECTORY = os.path.join("content", "articles")
CATEGORY_LABELS = {"army-list": "Army list", "guide": "Guide"}

_DIRECTIVE_RE = re.compile(r"^\{\{\s*(\w+)\s*:\s*(.*?)\s*\}\}\s*$")
_DETAILS_RE = re.compile(r"^:::details\s+(.*?)\s*$")
_MODEL_RE = re.compile(r"^:::model\s+(.*?)\s*$")
_SCENARIOS_RE = re.compile(r"^:::scenarios\s*$")
_POINTS_RE = re.compile(r"^:::points\s*$")
_RANGE_RE = re.compile(r"^(\d+)\s*(?:-|–)\s*(\d+)$|^(\d+)\s*\+$")
_POINTS_MIN, _POINTS_TICK_MIN, _POINTS_TICK_MAX, _POINTS_MAX = 300, 400, 1000, 1100
_SCENARIO_GROUPS = (("dobre", "Dobre", "good"), ("niezłe", "Niezłe", "ok"), ("kiepskie", "Kiepskie", "bad"))
_MODEL_FIELD_RE = re.compile(r"^(points|role|stats|wargear|heroic actions|keywords|base size)\s*:\s*(.*?)\s*$", re.IGNORECASE)
_MODEL_RULE_RE = re.compile(r"^\*\*([^*]+?)\*\*(?:\s*:\s*(.*?))?\s*$")
# Suffixes added to stat values when missing; Might / Will / Fate are shown on the right side of the stat row.
_STAT_SUFFIXES = {"mv": '"', "sv": "+", "c": "+", "i": "+"}
_RIGHT_STATS = {"might", "will", "fate"}
_SECTION_RE = re.compile(r"^(#{1,2})\s+(.*?)\s*#*\s*$")


def _parse_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().lstrip("\ufeff")
    meta = {}
    body = text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if match:
        for line in match.group(1).splitlines():
            if ":" in line and not line.lstrip().startswith("#"):
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
        body = match.group(2)
    return meta, body


def load_articles():
    """Returns {slug: article dict}, newest first. Re-read on every call so edits show up on reload."""
    articles = {}
    for root, _, files in os.walk(ARTICLES_DIRECTORY):
        for file_name in files:
            if not file_name.endswith(".md"):
                continue
            slug = file_name[:-3]
            meta, body = _parse_file(os.path.join(root, file_name))
            if meta.get("draft", "").lower() == "true":
                continue
            articles[slug] = {
                "slug": slug,
                "title": meta.get("title", slug),
                "category": meta.get("category", "guide"),
                "army": meta.get("army"),
                "author": meta.get("author"),
                "expert": meta.get("expert"),
                "redactor": meta.get("redactor"),
                "date": meta.get("date", ""),
                "cover": meta.get("cover"),
                "summary": meta.get("summary", ""),
                "body": body,
            }
    return dict(sorted(articles.items(), key=lambda item: item[1]["date"], reverse=True))


def army_record(army_name):
    games = wins = total_picks = 0
    for battle in load_battles():
        result = battle.get("result")
        if not isinstance(result, list) or len(result) != 2:
            continue
        for side in (1, 2):
            picked_army = battle.get(f"army_{side}_name")
            if not picked_army:
                continue
            total_picks += 1
            if picked_army != army_name:
                continue
            games += 1
            mine, theirs = result[side - 1], result[2 - side]
            if mine > theirs:
                wins += 1
            elif mine == theirs:
                wins += 0.5
    return games, wins, total_picks


def _army_stats_card(value):
    parts = [part.strip() for part in value.split("|")]
    army_name = parts[0]
    difficulty = None
    if len(parts) > 1:
        if len(parts) != 3:
            raise ValueError("Army stats difficulty must be provided as a rating and label")
        try:
            difficulty = int(parts[1])
        except ValueError as exc:
            raise ValueError(f"Army difficulty must be an integer from 1 to 10, got {parts[1]!r}") from exc
        if not 1 <= difficulty <= 10:
            raise ValueError(f"Army difficulty must be from 1 to 10, got {difficulty}")
        if not parts[2]:
            raise ValueError("Army difficulty label must not be empty")

    games, wins, total_picks = army_record(army_name)
    pickrate = f"{games / total_picks:.1%}" if total_picks else "-"
    winrate = f"{wins / games:.1%}" if games else "-"
    cells = [("Games", games), ("Pickrate", pickrate), ("Winrate", winrate)]
    stat_cells = [
        dmc.Stack(
            [dmc.Text(value, fw=700, size="xl"), dmc.Text(label, size="sm", c="dimmed")],
            gap=0,
            align="center",
        )
        for label, value in cells
    ]
    if difficulty is not None:
        stat_cells.append(
            dmc.Stack(
                [
                    dmc.Group(
                        [
                            dmc.Text(f"{difficulty}/10", fw=700, size="xl", c="cyan"),
                            dmc.Text(parts[2], fw=700),
                        ],
                        gap="xs",
                        align="baseline",
                    ),
                    dmc.Text("Difficulty", size="sm", c="dimmed"),
                ],
                gap=0,
                align="center",
            )
        )
    return dmc.Paper(
        dmc.Stack(
            [
                dmc.Text(army_name, fw=700, size="lg", ta="center"),
                dmc.SimpleGrid(
                    stat_cells,
                    cols=len(stat_cells),
                ),
            ],
            gap="sm",
        ),
        withBorder=True,
        shadow="sm",
        radius="md",
        p="md",
        my="md",
        className="article-card",
    )


def _markdown(lines):
    text = "\n".join(lines).strip()
    return dcc.Markdown(text, className="article-body") if text else None


def _points_timeline(lines):
    span = _POINTS_MAX - _POINTS_MIN

    def pct(value):
        return (min(max(value, _POINTS_MIN), _POINTS_MAX) - _POINTS_MIN) / span * 100

    segments = []
    for line in lines:
        key, _, rest = line.partition(":")
        css = {group_key: group_css for group_key, _, group_css in _SCENARIO_GROUPS}.get(key.strip().lower())
        if not css:
            continue
        for item in rest.split(","):
            match = _RANGE_RE.match(item.strip())
            if not match:
                continue
            if match.group(3):
                start, end = int(match.group(3)), _POINTS_MAX
            else:
                start, end = int(match.group(1)), int(match.group(2))
            if end > start:
                left, right = pct(start), pct(end)
                segments.append(
                    html.Div(
                        className=f"points-segment scenario-{css}",
                        style={"left": f"{left}%", "width": f"{right - left}%"},
                    )
                )

    ticks = [
        html.Div(
            str(value),
            className="points-tick",
            style={"left": f"{pct(value)}%"},
        )
        for value in range(_POINTS_TICK_MIN, _POINTS_TICK_MAX + 1, 100)
    ]
    axis = html.Div(html.Div(segments, className="points-bar"), className="points-axis")
    legend = html.Div(
        [
            html.Span(label, className=f"points-legend-item scenario-{css}")
            for _, label, css in _SCENARIO_GROUPS
        ],
        className="points-legend",
    )
    return html.Div([axis, html.Div(ticks, className="points-ticks"), legend], className="points-timeline")


def _scenarios_card(lines):
    names = {scenario.value.lower(): scenario.value for scenario in Scenario}
    assigned = {key: [] for key, _, _ in _SCENARIO_GROUPS}
    seen = set()
    for line in lines:
        key, _, rest = line.partition(":")
        key = key.strip().lower()
        if key not in assigned:
            continue
        for item in rest.split(","):
            name = names.get(item.strip().lower())
            if name and name not in seen:
                seen.add(name)
                assigned[key].append(name)
    # Scenarios not mentioned anywhere fall into the middle group.
    assigned["niezłe"].extend(name for name in names.values() if name not in seen)

    columns = [
        html.Div(
            [
                html.Div(f"{label} ({len(assigned[key])})", className="scenario-group-title"),
                html.Ul([html.Li(name) for name in assigned[key]], className="scenario-list"),
            ],
            className=f"scenario-group scenario-{css}",
        )
        for key, label, css in _SCENARIO_GROUPS
    ]
    return html.Div(columns, className="scenario-groups")


def _model_card(name, lines):
    fields = {}
    rules = []
    start = 0
    # Field and rule lines are only read from the top of the block; everything after them is the comment.
    while start < len(lines):
        stripped = lines[start].strip()
        field = _MODEL_FIELD_RE.match(stripped)
        rule = _MODEL_RULE_RE.match(stripped)
        if field:
            fields[field.group(1).lower()] = field.group(2)
        elif rule:
            rules.append((rule.group(1), rule.group(2) or ""))
        elif stripped:
            break
        start += 1
    comment = _markdown(lines[start:])

    header = [html.Span(name, className="model-name")]
    if "points" in fields:
        header.append(html.Span(f"{fields['points'] or '–'} pts", className="model-points"))
    title = html.Div(header, className="model-title")

    info = [title]
    if fields.get("role"):
        info.append(html.Div(fields["role"], className="model-role"))
    if fields.get("stats"):
        main_cells, right_cells = [], []
        for part in fields["stats"].split("|"):
            label, _, value = part.strip().partition(" ")
            if not label:
                continue
            value = value.strip() or "-"
            suffix = _STAT_SUFFIXES.get(label.lower())
            if suffix and value != "-" and not value.endswith(suffix):
                value += suffix
            cell = html.Div(
                [html.Div(label, className="model-stat-label"), html.Div(value, className="model-stat-value")],
                className="model-stat",
            )
            (right_cells if label.lower() in _RIGHT_STATS else main_cells).append(cell)
        groups = [html.Div(main_cells, className="model-stats-group")]
        if right_cells:
            groups.append(html.Div(right_cells, className="model-stats-group model-stats-right"))
        info.append(html.Div(groups, className="model-stats"))
    details = [
        html.Div([html.Strong(label), f": {fields[key] or '–'}"], className="model-rule")
        for key, label in (
            ("wargear", "Wargear"),
            ("heroic actions", "Heroic Actions"),
            ("keywords", "Keywords"),
            ("base size", "Base Size"),
        )
        if key in fields
    ]
    if details:
        info.append(html.Div(details, className="model-rules"))
    if rules:
        info.append(
            html.Div(
                [
                    html.Div(
                        [html.Strong(rule_name), f": {rule_text}" if rule_text else ""],
                        className="model-rule",
                    )
                    for rule_name, rule_text in rules
                ],
                className="model-rules",
            )
        )

    card = html.Details(
        [html.Summary(info[0], className="model-summary"), html.Div(info[1:], className="model-details")],
        className="model-card",
    )
    if comment is None:
        return card
    return html.Div([card, html.Div(comment, className="model-comment")], className="model-profile")


def _army_list_image(value):
    src, _, title = value.partition("|")
    src, title = src.strip(), title.strip() or "Army list"
    image = html.A(
        html.Img(src=src, alt=title, className="army-list-image"),
        href=src,
        target="_blank",
        title="Otwórz w pełnym rozmiarze",
    )
    return dmc.Accordion(
        dmc.AccordionItem(
            [dmc.AccordionControl(title), dmc.AccordionPanel(html.Div(image, className="army-list"))],
            value=title,
        ),
        my="sm",
        className="article-accordion",
    )


def _slugify(text, used):
    slug = re.sub(r"[\W_]+", "-", text.lower()).strip("-") or "section"
    candidate, n = slug, 2
    while candidate in used:
        candidate, n = f"{slug}-{n}", n + 1
    used.add(candidate)
    return candidate


def _section(level, title, anchor, content):
    return html.Section(
        [
            html.Div(
                [
                    dmc.Title(title, order=level + 1, className="article-section-title"),
                    html.Button(
                        type="button",
                        className="article-toggle",
                        title="Zwiń / rozwiń sekcję",
                        **{"aria-label": "Zwiń / rozwiń sekcję", "aria-expanded": "true"},
                    ),
                ],
                className="article-section-header",
            ),
            html.Div(content, className="article-section-content"),
        ],
        id=anchor,
        className=f"article-section article-section-level-{level}",
    )


def render_body(body):
    """Returns (components, toc).

    '# ' starts a top-level collapsible section and '## ' a collapsible subsection nested in it.
    toc lists (level, title, anchor) for the sidebar tracker.
    """
    components = []
    toc = []
    used_ids = set()
    buffer = []
    stack = []
    in_code = False

    def target():
        return stack[-1]["content"] if stack else components

    def flush():
        block = _markdown(buffer)
        if block is not None:
            target().append(block)
        buffer.clear()

    def close_section():
        done = stack.pop()
        target().append(_section(done["level"], done["title"], done["anchor"], done["content"]))

    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        directive = _DIRECTIVE_RE.match(line.strip())
        details = _DETAILS_RE.match(line.strip())
        model = _MODEL_RE.match(line.strip())
        heading = None if in_code else _SECTION_RE.match(line)
        if line.lstrip().startswith("```"):
            in_code = not in_code
            buffer.append(line)
        elif in_code:
            buffer.append(line)
        elif heading:
            flush()
            level = len(heading.group(1))
            while stack and stack[-1]["level"] >= level:
                close_section()
            title = re.sub(r"[*_`]", "", heading.group(2))
            anchor = _slugify(title, used_ids)
            stack.append({"level": level, "title": title, "anchor": anchor, "content": []})
            toc.append((level, title, anchor))
        elif directive and directive.group(1) == "army_stats":
            flush()
            target().append(_army_stats_card(directive.group(2)))
        elif directive and directive.group(1) == "army_list":
            flush()
            target().append(_army_list_image(directive.group(2)))
        elif model:
            flush()
            inner = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                inner.append(lines[i])
                i += 1
            target().append(_model_card(model.group(1), inner))
        elif _POINTS_RE.match(line.strip()):
            flush()
            inner = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                inner.append(lines[i])
                i += 1
            target().append(_points_timeline(inner))
        elif _SCENARIOS_RE.match(line.strip()):
            flush()
            inner = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                inner.append(lines[i])
                i += 1
            target().append(_scenarios_card(inner))
        elif details:
            flush()
            inner = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                inner.append(lines[i])
                i += 1
            title = details.group(1)
            target().append(
                dmc.Accordion(
                    dmc.AccordionItem(
                        [dmc.AccordionControl(title), dmc.AccordionPanel(_markdown(inner))],
                        value=title,
                    ),
                    my="sm",
                    className="article-accordion",
                )
            )
        else:
            buffer.append(line)
        i += 1
    flush()
    while stack:
        close_section()
    return components, toc


def article_tracker(toc):
    if not toc:
        return None
    return html.Nav(
        [
            html.Div("Nawigacja", className="article-tracker-title"),
            *[
                html.A(
                    title,
                    href=f"#{anchor}",
                    className=f"article-tracker-link article-tracker-level-{level}",
                    **{"data-target": anchor},
                )
                for level, title, anchor in toc
            ],
        ],
        className="article-tracker",
    )


def article_header(article, link=False):
    category = CATEGORY_LABELS.get(article["category"], article["category"])
    badges = [dmc.Badge(category, variant="light")]
    if article["army"]:
        badges.append(dmc.Badge(article["army"], variant="outline"))
    contributors = [
        f"{label}: {article[key]}"
        for key, label in (("expert", "Expert"), ("redactor", "Redactor"))
        if article.get(key)
    ]
    if not contributors and article.get("author"):
        contributors.append(article["author"])
    meta_line = " · ".join((*contributors, article["date"]))
    return badges, meta_line

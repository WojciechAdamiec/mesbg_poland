"""Loads Markdown articles from ./content/articles and renders them as Dash components.

Article file format:

    ---
    title: Some title
    category: army-list
    ---
    Markdown body...

Extra syntax inside the body (each on its own line):

    {{ army_stats: Army of Gundabad }}   live games / winrate card from battles data
    :::details Section title             collapsible section, closed by a line with ':::'
    ...markdown...
    :::
"""
import os
import re

import dash_mantine_components as dmc
from dash import dcc

from store import load_battles

ARTICLES_DIRECTORY = os.path.join("content", "articles")
CATEGORY_LABELS = {"army-list": "Army list", "guide": "Guide"}

_DIRECTIVE_RE = re.compile(r"^\{\{\s*(\w+)\s*:\s*(.*?)\s*\}\}\s*$")
_DETAILS_RE = re.compile(r"^:::details\s+(.*?)\s*$")


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
                "date": meta.get("date", ""),
                "cover": meta.get("cover"),
                "summary": meta.get("summary", ""),
                "body": body,
            }
    return dict(sorted(articles.items(), key=lambda item: item[1]["date"], reverse=True))


def army_record(army_name):
    games = wins = draws = 0
    for battle in load_battles():
        for side in (1, 2):
            if battle.get(f"army_{side}_name") != army_name:
                continue
            result = battle.get("result")
            if not isinstance(result, list) or len(result) != 2:
                continue
            games += 1
            mine, theirs = result[side - 1], result[2 - side]
            if mine > theirs:
                wins += 1
            elif mine == theirs:
                draws += 1
    return games, wins, draws


def _army_stats_card(army_name):
    games, wins, draws = army_record(army_name)
    winrate = f"{wins / games:.1%}" if games else "-"
    cells = [("Games", games), ("Wins", wins), ("Draws", draws), ("Winrate", winrate)]
    return dmc.Paper(
        dmc.Stack(
            [
                dmc.Text(army_name, fw=700, size="lg"),
                dmc.SimpleGrid(
                    [
                        dmc.Stack(
                            [dmc.Text(value, fw=700, size="xl"), dmc.Text(label, size="sm", c="dimmed")],
                            gap=0,
                            align="center",
                        )
                        for label, value in cells
                    ],
                    cols=4,
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


def render_body(body):
    components = []
    buffer = []

    def flush():
        block = _markdown(buffer)
        if block is not None:
            components.append(block)
        buffer.clear()

    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        directive = _DIRECTIVE_RE.match(line.strip())
        details = _DETAILS_RE.match(line.strip())
        if directive and directive.group(1) == "army_stats":
            flush()
            components.append(_army_stats_card(directive.group(2)))
        elif details:
            flush()
            inner = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                inner.append(lines[i])
                i += 1
            title = details.group(1)
            components.append(
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
    return components


def article_header(article, link=False):
    category = CATEGORY_LABELS.get(article["category"], article["category"])
    badges = [dmc.Badge(category, variant="light")]
    if article["army"]:
        badges.append(dmc.Badge(article["army"], variant="outline"))
    meta_line = " · ".join(part for part in (article["author"], article["date"]) if part)
    return badges, meta_line

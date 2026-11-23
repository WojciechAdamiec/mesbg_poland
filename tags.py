"""Load typed tags and render inline references to them.

Article text can reference a tag with ``[[tag:TYPE:ID]]``, for example
``[[tag:army_lists:rohan]]``.
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import dash_mantine_components as dmc
from dash import html


TAG_TYPES = ("army_lists", "players", "places", "tournaments")
TAG_DIRECTORY = Path(__file__).parent / "tags"
_TAG_FILES = {tag_type: f"{tag_type}.json" for tag_type in TAG_TYPES}
_TAG_REFERENCE_RE = re.compile(r"\[\[tag:([a-z_]+):([a-z0-9_-]+)\]\]")


@dataclass(frozen=True)
class Tag:
    id: str
    name: str
    desc: str
    items: tuple[str | int, ...]


def load_tags(tag_type):
    """Load and validate tags from one type-specific JSON file."""
    if tag_type not in _TAG_FILES:
        raise ValueError(f"Unknown tag type {tag_type!r}; expected one of {', '.join(TAG_TYPES)}")

    path = TAG_DIRECTORY / _TAG_FILES[tag_type]
    with path.open(encoding="utf-8") as file:
        records = json.load(file)
    if not isinstance(records, list):
        raise ValueError(f"Tag file {path} must contain a JSON list")

    tags = []
    seen_ids = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Tag entry {index} in {path} must be an object")
        tag_id = record.get("id")
        name = record.get("name")
        desc = record.get("desc")
        items = record.get("items")
        if not isinstance(tag_id, str) or not tag_id:
            raise ValueError(f"Tag entry {index} in {path} must have a non-empty string id")
        if tag_id in seen_ids:
            raise ValueError(f"Duplicate tag id {tag_id!r} in {path}")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Tag {tag_id!r} in {path} must have a non-empty name")
        if not isinstance(desc, str) or not desc:
            raise ValueError(f"Tag {tag_id!r} in {path} must have a non-empty desc")
        if not isinstance(items, list) or any(
            not isinstance(item, (str, int)) or isinstance(item, bool) for item in items
        ):
            raise ValueError(f"Tag {tag_id!r} in {path} must have a list of string or integer items")
        if len(set(items)) != len(items):
            raise ValueError(f"Tag {tag_id!r} in {path} contains duplicate items")
        tags.append(Tag(tag_id, name, desc, tuple(items)))
        seen_ids.add(tag_id)
    return tuple(tags)


def get_tag(tag_type, tag_id):
    """Return a tag by type and id, raising ``KeyError`` if it does not exist."""
    for tag in load_tags(tag_type):
        if tag.id == tag_id:
            return tag
    raise KeyError(f"Unknown {tag_type} tag {tag_id!r}")


def has_tag(tag_type, tag_id, item_id):
    """Return whether an item identifier belongs to the specified tag."""
    return item_id in get_tag(tag_type, tag_id).items


def tags_for_item(tag_type, item_id):
    """Return all tags of a type containing the given item identifier."""
    return tuple(tag for tag in load_tags(tag_type) if item_id in tag.items)


def text_with_tag_descriptions(text):
    """Return readable plain text with each tag reference expanded to its name and description."""
    return _TAG_REFERENCE_RE.sub(
        lambda match: _format_tag_description(*match.groups()),
        text,
    )


def _format_tag_description(tag_type, tag_id):
    tag = get_tag(tag_type, tag_id)
    return f"{tag.name}: {tag.desc}"


def styled_tooltip(title, lines, children):
    return dmc.Tooltip(
        label=html.Div(
            [
                html.Div(title, className="tag-tooltip-title"),
                html.Div(
                    [html.Div(line, className="tag-tooltip-line") for line in lines],
                    className="tag-tooltip-description",
                ),
            ],
        ),
        children=children,
        classNames={"tooltip": "tag-tooltip-popup"},
        boxWrapperProps={"style": {"display": "inline"}},
        inline=True,
        position="top",
        withArrow=True,
        multiline=True,
        w=360,
        maw="80vw",
        fz=21,
        events={"hover": True, "focus": True, "touch": True},
    )


def _tag_keyword(tag, keyword_class):
    return styled_tooltip(
        tag.name, tag.desc.split("\n"),
        html.Span(
            tag.name,
            className=keyword_class,
            tabIndex=0,
            **{"aria-label": f"{tag.name}: {tag.desc}"},
        ),
    )


def render_tagged_text(
    text, *, render_text: Callable[[str], object] | None = None, keyword_class="tag-keyword"
):
    """Replace ``[[tag:TYPE:ID]]`` references with accessible keyword tooltips.

    ``render_text`` can be supplied by callers that need formatting for ordinary
    text segments, such as the article Markdown renderer.
    """
    matches = list(_TAG_REFERENCE_RE.finditer(text))
    if not matches:
        return text

    tags_by_type = {}
    for match in matches:
        tag_type = match.group(1)
        if tag_type not in tags_by_type:
            tags_by_type[tag_type] = {tag.id: tag for tag in load_tags(tag_type)}

    parts = []

    def append_text(value):
        if not value:
            return
        if render_text is None:
            parts.append(value)
            return
        leading = len(value) - len(value.lstrip())
        trailing = len(value) - len(value.rstrip())
        if leading + trailing >= len(value):
            parts.append(value)
            return
        if leading:
            parts.append(value[:leading])
        content_end = len(value) - trailing if trailing else len(value)
        parts.append(render_text(value[leading:content_end]))
        if trailing:
            parts.append(value[content_end:])

    start = 0
    for match in matches:
        append_text(text[start:match.start()])
        tag_type, tag_id = match.groups()
        try:
            tag = tags_by_type[tag_type][tag_id]
        except KeyError as exc:
            raise KeyError(f"Unknown {tag_type} tag {tag_id!r} in text reference") from exc
        parts.append(_tag_keyword(tag, keyword_class))
        start = match.end()
    append_text(text[start:])
    return html.Span(parts, className="tagged-text")

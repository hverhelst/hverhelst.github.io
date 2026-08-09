"""Insert an object into a JSON array file without reformatting the rest of it.

The ``data/*.json`` files are hand-maintained and inconsistent on purpose:
most use tab indentation with the separating comma on its own line, while
``education.json`` uses four spaces with a trailing comma. Round-tripping a
whole file through ``json.dumps`` would rewrite every line and bury the one
entry that actually changed, so this module splices the rendered entry into
the raw text and copies the surrounding layout.
"""

import json


def top_level_spans(text):
    """Return the ``(start, end)`` offsets of each object in the outer array."""
    spans = []
    depth = 0
    start = None
    in_string = False
    escaped = False
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        elif ch == "{":
            if depth == 1:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 1 and start is not None:
                spans.append((start, i + 1))
                start = None
    return spans


def _line_indent(text, offset):
    """Whitespace between the start of ``offset``'s line and ``offset``."""
    line_start = text.rfind("\n", 0, offset) + 1
    prefix = text[line_start:offset]
    return prefix if prefix.strip() == "" else ""


def detect_style(text, spans):
    """Work out the indentation and element separator used by the file.

    Returns ``(outer_indent, inner_unit, separator)``. ``separator`` is the
    literal text between two consecutive entries, so it already ends with the
    outer indentation of the entry that follows it.
    """
    outer = "\t"
    inner = "\t"
    separator = "\n" + outer + ",\n" + outer

    if spans:
        outer = _line_indent(text, spans[0][0]) or "\t"
        block = text[spans[0][0] : spans[0][1]]
        for line in block.split("\n")[1:]:
            if line.strip():
                indent = line[: len(line) - len(line.lstrip())]
                if indent.startswith(outer):
                    inner = indent[len(outer) :] or "\t"
                break
        separator = "\n" + outer + ",\n" + outer
    if len(spans) > 1:
        separator = text[spans[0][1] : spans[1][0]]
    return outer, inner, separator


def render(obj, outer_indent, inner_unit):
    """Serialise ``obj`` at the nesting level of an existing array element."""
    body = json.dumps(obj, indent=inner_unit, ensure_ascii=False)
    lines = body.split("\n")
    return "\n".join([lines[0]] + [outer_indent + line for line in lines[1:]])


def insert(text, obj, index):
    """Return ``text`` with ``obj`` spliced in as element number ``index``."""
    spans = top_level_spans(text)
    outer, inner, separator = detect_style(text, spans)
    block = render(obj, outer, inner)

    if not spans:
        open_bracket = text.index("[")
        close_bracket = text.rindex("]")
        return (
            text[: open_bracket + 1]
            + "\n"
            + outer
            + block
            + "\n"
            + text[close_bracket:]
        )

    index = max(0, min(index, len(spans)))
    if index == len(spans):
        at = spans[-1][1]
        return text[:at] + separator + block + text[at:]
    at = spans[index][0]
    return text[:at] + block + separator + text[at:]

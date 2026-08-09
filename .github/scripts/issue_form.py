"""Read the values a GitHub issue form collected, keyed by field ``id``.

GitHub renders a submitted issue form as markdown: one ``### <label>`` heading
per field, followed by the value (or the literal ``_No response_``). The field
``id`` is not in the rendered body, so the ids are recovered by reading the
template YAML back out of ``.github/ISSUE_TEMPLATE/`` and matching on label.

That also gives a template-detection mechanism that does not depend on issue
labels existing in the repository: the template whose labels line up with the
headings in the body is the one that was used.
"""

import os
import re

import yaml

NO_RESPONSE = "_No response_"
TEMPLATE_DIR = os.path.join(".github", "ISSUE_TEMPLATE")
VALUE_TYPES = ("input", "textarea", "dropdown", "checkboxes")


def load_templates(directory=TEMPLATE_DIR):
    """Return ``{stem: template}`` for every issue form in ``directory``."""
    templates = {}
    for name in sorted(os.listdir(directory)):
        stem, ext = os.path.splitext(name)
        if ext not in (".yml", ".yaml") or stem == "config":
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        if isinstance(data, dict) and "body" in data:
            templates[stem] = data
    return templates


def fields(template):
    """The value-carrying elements of a template, in order."""
    return [
        element
        for element in template.get("body", [])
        if element.get("type") in VALUE_TYPES
        and element.get("attributes", {}).get("label")
    ]


def parse_body(body):
    """Split a rendered issue body into ``{heading: raw text}``."""
    sections = {}
    heading = None
    lines = []
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        match = re.match(r"^###\s+(.*?)\s*$", line)
        if match:
            if heading is not None:
                sections[heading] = "\n".join(lines).strip()
            heading = match.group(1)
            lines = []
        elif heading is not None:
            lines.append(line)
    if heading is not None:
        sections[heading] = "\n".join(lines).strip()
    return sections


def match_template(body, templates):
    """Pick the template that best explains ``body``, or ``None``.

    A template only qualifies when every one of its required fields shows up
    as a heading; among those, the one matching the most headings wins.
    """
    headings = set(parse_body(body))
    if not headings:
        return None, None

    best = (0, None, None)
    for stem, template in sorted(templates.items()):
        labels = [f["attributes"]["label"] for f in fields(template)]
        required = [
            f["attributes"]["label"]
            for f in fields(template)
            if f.get("validations", {}).get("required")
        ]
        if not all(label in headings for label in required):
            continue
        score = sum(1 for label in labels if label in headings)
        if score > best[0]:
            best = (score, stem, template)
    return best[1], best[2]


def _checked(text):
    """Labels of the ticked options in a rendered ``checkboxes`` field."""
    return [
        line.split("]", 1)[1].strip()
        for line in text.split("\n")
        if re.match(r"^\s*- \[[xX]\]", line)
    ]


def values(template, body):
    """Return ``{field id: value}`` for one submitted form.

    Text fields come back as strings (empty when unanswered), single-option
    checkboxes as booleans, multi-option checkboxes as a list of labels.
    """
    sections = parse_body(body)
    result = {}
    for field in fields(template):
        attributes = field["attributes"]
        key = field.get("id") or attributes["label"]
        raw = sections.get(attributes["label"], "")
        if field["type"] == "checkboxes":
            options = attributes.get("options", [])
            ticked = _checked(raw)
            result[key] = bool(ticked) if len(options) == 1 else ticked
        else:
            result[key] = "" if raw == NO_RESPONSE else raw
    return result

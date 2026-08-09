#!/usr/bin/env python3
"""Turn a submitted issue form into a new record in ``data/*.json``.

Reads the issue body (from ``--body-file`` or ``$ISSUE_BODY``), works out which
issue form produced it, builds the record, downloads any attached figure into
``static/media/``, and splices the record into the right data file.

Writes a small JSON report to ``$GITHUB_OUTPUT`` (or ``--report``) so the
workflow knows what happened:

    status=added|skipped   file=data/news.json   summary=...   branch=...

Exit status is 0 for both "added" and "skipped"; a malformed submission exits
non-zero so the workflow can report it back on the issue.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bibtex  # noqa: E402
import issue_form  # noqa: E402
import json_splice  # noqa: E402
import sections  # noqa: E402
import validate_data  # noqa: E402

MEDIA_DIR = os.path.join("static", "media")
USER_AGENT = "hverhelst.github.io data-entry bot"
IMAGE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
}


class SubmissionError(Exception):
    """The form was filled in in a way that cannot be turned into a record."""


# --------------------------------------------------------------------------
# text helpers


def one_line(value):
    """Collapse a textarea answer to the single line the JSON files use."""
    return re.sub(r"\s+", " ", (value or "").replace("\r\n", "\n")).strip()


def paragraphs(value):
    """Keep blank-line paragraph breaks, join hard-wrapped lines."""
    text = (value or "").replace("\r\n", "\n").strip()
    return "\n\n".join(
        re.sub(r"\s+", " ", block).strip()
        for block in re.split(r"\n\s*\n", text)
        if block.strip()
    )


def check(data_file, record):
    """Hold the record to the same schema a hand-written one is held to."""
    found = validate_data.validate_record(data_file, record)
    if found:
        problems = "; ".join(problem.split(": ", 1)[-1] for problem in found)
        raise SubmissionError(
            f"the entry does not fit {os.path.basename(data_file)}: {problems}"
        )


def fetch(url, accept=None):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    if accept:
        request.add_header("Accept", accept)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(), response.headers.get("Content-Type", "")


# --------------------------------------------------------------------------
# figures


def first_attachment(value):
    """The first image URL in a textarea a figure was dropped into."""
    if not value:
        return ""
    match = re.search(r"!\[[^\]]*\]\((https?://[^)\s]+)\)", value)
    if match:
        return match.group(1)
    match = re.search(r'<img[^>]+src="(https?://[^"]+)"', value)
    if match:
        return match.group(1)
    match = re.search(r"https?://\S+", value)
    return match.group(0).rstrip(">)") if match else ""


def download_figure(url, basename):
    """Save an attached figure under ``static/media`` and return its path."""
    try:
        data, content_type = fetch(url)
    except (urllib.error.URLError, ValueError) as error:
        raise SubmissionError(f"could not download the figure from {url}: {error}")

    extension = IMAGE_EXTENSIONS.get(content_type.split(";")[0].strip())
    if extension is None:
        extension = os.path.splitext(url.split("?")[0])[1].lower()
        if extension not in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"):
            raise SubmissionError(
                f"the attached figure is a {content_type or 'unknown'} file; "
                "attach a PNG, JPEG, GIF, SVG or WebP image."
            )

    os.makedirs(MEDIA_DIR, exist_ok=True)
    path = os.path.join(MEDIA_DIR, basename + extension)
    with open(path, "wb") as handle:
        handle.write(data)
    return "media/" + basename + extension


# --------------------------------------------------------------------------
# publications


def unfence(text):
    """Drop the ``` fence a pasted block is often wrapped in."""
    lines = [line for line in (text or "").strip().split("\n")]
    while lines and lines[0].lstrip().startswith("```"):
        lines.pop(0)
    while lines and lines[-1].strip().startswith("```"):
        lines.pop()
    return "\n".join(lines).strip()


def resolve_bibtex(source):
    """Accept BibTeX, a DOI, or a link to a .bib file; return BibTeX text."""
    source = unfence(source)
    if not source:
        raise SubmissionError("no BibTeX, DOI or .bib link was given.")
    if "@" in source and "{" in source:
        return source

    reference = source.splitlines()[0].strip()
    if re.match(r"^https?://", reference) and not re.search(
        r"(doi\.org|/doi/)", reference
    ):
        data, _ = fetch(reference)
        return data.decode("utf-8", "replace")

    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", reference, flags=re.I)
    try:
        data, _ = fetch("https://doi.org/" + doi, accept="application/x-bibtex")
    except urllib.error.HTTPError as error:
        raise SubmissionError(
            f"doi.org returned {error.code} for {doi!r}. Paste the BibTeX "
            "instead, or check the DOI."
        )
    except urllib.error.URLError as error:
        raise SubmissionError(f"could not reach doi.org: {error.reason}")
    return data.decode("utf-8", "replace")


def display_surname(author):
    """First author's family name from a rendered list, ``H. M. Verhelst, …``."""
    first = author.split(",")[0].strip()
    words = first.split()
    return re.sub(r"[^A-Za-z]", "", words[-1]) if words else ""


def unique_cite_key(preferred, base, existing):
    """``Verhelst2024`` / ``Verhelst2024a`` / ``Verhelst2024b``, never a clash."""
    taken = {entry.get("cite-key", "") for entry in existing}
    candidate = re.sub(r"[^A-Za-z0-9]", "", preferred or "") or base
    if candidate not in taken:
        return candidate
    for suffix in "abcdefghijklmnopqrstuvwxyz":
        if candidate + suffix not in taken:
            return candidate + suffix
    raise SubmissionError(f"cannot find a free cite key based on {candidate!r}.")


def description_from_bibtex(entry_type, fields):
    """Map BibTeX fields onto the ``description`` object the site renders."""
    year = fields.get("year", "") or fields.get("date", "")[:4]
    doi = fields.get("doi", "").replace("https://doi.org/", "")
    url = fields.get("url", "")
    if doi:
        url = "https://doi.org/" + doi

    eprint = fields.get("eprint", "")
    if eprint:
        archive = fields.get("archiveprefix") or fields.get("eprinttype") or "arXiv"
        if not eprint.lower().startswith(archive.lower()):
            eprint = f"{archive}:{eprint}"

    description = {
        "author": bibtex.format_authors(fields.get("author", "")),
        "title": fields.get("title", "").rstrip("."),
        "journal": fields.get("journal") or fields.get("journaltitle", ""),
        "booktitle": fields.get("booktitle", ""),
        "editor": bibtex.format_authors(fields.get("editor", "")),
        "series": fields.get("series", ""),
        "school": fields.get("school") or fields.get("institution", ""),
        "publisher": fields.get("publisher", ""),
        "volume": fields.get("volume", ""),
        "issue": fields.get("number", ""),
        "pages": fields.get("pages", "").replace("--", "-"),
        "year": year,
        "eprint": eprint,
        "url": url,
        "abstract": one_line(fields.get("abstract", "")),
    }

    if entry_type == "thesis":
        # Only the year of this is ever rendered, so a year-only BibTeX entry
        # can safely stand in the first of January.
        description["date"] = fields.get("date") or (year + "-01-01" if year else "")
        description["degree"] = {
            "phdthesis": "Doctor of Philosophy",
            "mastersthesis": "Master of Science",
        }.get(fields.get("_bibtex_type", ""), fields.get("degree", ""))
    return description


def build_publication(stem, answers, existing):
    """Build a publications.json record from either publication form."""
    figure_field = answers.get("figure", "")
    caption = one_line(answers.get("imageCaption", ""))

    if stem == "publication-bibtex":
        raw = resolve_bibtex(answers.get("bibtex", ""))
        bib_type, bib_key, fields = bibtex.parse(raw)
        fields["_bibtex_type"] = bib_type
        entry_type = answers.get("entry-type", "").strip() or ""
        if entry_type in ("", "auto-detect from the BibTeX entry type"):
            entry_type = sections.BIBTEX_ENTRY_TYPES.get(bib_type)
            if entry_type is None:
                raise SubmissionError(
                    f"BibTeX entry type @{bib_type} has no matching section; "
                    "pick one explicitly in the form."
                )
        if entry_type == "unpublished" and not fields.get("eprint"):
            # arXiv DOIs carry the identifier but no eprint field.
            match = re.search(r"arXiv\.(\d{4}\.\d{4,5})", fields.get("doi", ""), re.I)
            if match:
                fields["eprint"] = "arXiv:" + match.group(1)
        description = description_from_bibtex(entry_type, fields)
        preferred_key = answers.get("cite-key", "").strip() or bib_key
        fallback_key = bibtex.surname(fields.get("author", ""))
    else:
        entry_type = answers.get("entry-type", "").strip()
        description = {
            key: one_line(answers.get(key, ""))
            for key in sections.PUBLICATION["description_order"]
            if key in answers
        }
        description["abstract"] = one_line(answers.get("abstract", ""))
        preferred_key = answers.get("cite-key", "").strip()
        fallback_key = display_surname(description.get("author", ""))

    cite_key = unique_cite_key(
        preferred_key,
        (fallback_key or "Entry") + description.get("year", ""),
        existing,
    )

    attachment = first_attachment(figure_field)
    if attachment:
        description["image"] = download_figure(attachment, cite_key)
        description["imageCaption"] = caption or description.get("title", "")
    elif caption:
        raise SubmissionError(
            "a figure caption was given but no figure was attached."
        )

    ordered = {
        key: description[key]
        for key in sections.PUBLICATION["description_order"]
        if description.get(key)
    }
    record = {
        "cite-key": cite_key,
        "entry-type": entry_type,
        "description": ordered,
        "featured": bool(answers.get("featured")),
    }
    check(sections.PUBLICATION["file"], record)
    return record


# --------------------------------------------------------------------------
# generic sections


def build_record(stem, answers):
    """Build a record for one of the flat ``data/*.json`` sections."""
    config = sections.SECTIONS[stem]
    constant = config.get("constant", {})
    booleans = set(config.get("booleans", []))
    keep_empty = set(config.get("keep_empty", []))
    multiline = {"text", "details", "description"}

    record = {}
    for key in config["order"]:
        if key in constant:
            record[key] = constant[key]
            continue
        if key in booleans:
            record[key] = bool(answers.get(key))
            continue
        value = answers.get(key, "")
        if not isinstance(value, str):
            continue
        value = paragraphs(value) if key in multiline else one_line(value)
        if value or key in keep_empty:
            record[key] = value
    check(config["file"], record)
    return record


def placement(entries, record, config):
    """Index at which the record keeps the file's existing ordering."""
    candidates = list(range(len(entries)))
    group = config.get("group_by")
    if group:
        candidates = [
            i for i, entry in enumerate(entries) if entry.get(group) == record.get(group)
        ]
        if not candidates:
            return len(entries)

    order = config.get("sort")
    if not order:
        return candidates[-1] + 1 if candidates else len(entries)

    key, reverse = order
    new = record.get(key, "")
    for index in candidates:
        current = entries[index].get(key, "")
        if (new > current) if reverse else (new < current):
            return index
    return candidates[-1] + 1 if candidates else len(entries)


# --------------------------------------------------------------------------


def report(destination, values):
    # GITHUB_OUTPUT is line-oriented, so every value has to stay on one line.
    lines = [f"{key}={one_line(str(value))}" for key, value in values.items()]
    text = "\n".join(lines) + "\n"
    if destination:
        with open(destination, "a", encoding="utf-8") as handle:
            handle.write(text)
    sys.stderr.write(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", help="file holding the issue body")
    parser.add_argument("--issue", default="0", help="issue number, for the branch name")
    parser.add_argument("--report", help="defaults to $GITHUB_OUTPUT")
    parser.add_argument(
        "--print", action="store_true", help="show the record instead of writing it"
    )
    args = parser.parse_args()

    if args.body_file:
        with open(args.body_file, encoding="utf-8") as handle:
            body = handle.read()
    else:
        body = os.environ.get("ISSUE_BODY", "")

    destination = args.report or os.environ.get("GITHUB_OUTPUT")

    templates = issue_form.load_templates()
    stem, template = issue_form.match_template(body, templates)
    if stem is None:
        report(destination, {"status": "skipped", "reason": "no matching issue form"})
        return 0

    answers = issue_form.values(template, body)
    config = sections.config(stem)

    with open(config["file"], encoding="utf-8") as handle:
        text = handle.read()
    entries = json.loads(text)

    if stem in sections.PUBLICATION_TEMPLATES:
        record = build_publication(stem, answers, entries)
        summary = record["description"]["title"]
        index = len(entries)
    else:
        record = build_record(stem, answers)
        summary = config["summary"].format(**{**{k: "" for k in config["order"]}, **record})
        index = placement(entries, record, config)

    if args.print:
        print(json.dumps(record, indent="\t", ensure_ascii=False))
        return 0

    # Never leave behind a data file the site cannot read.
    updated = json_splice.insert(text, record, index)
    spliced = json.loads(updated)
    problems = validate_data.problems(
        spliced, validate_data.load_schema(config["file"])
    )
    if problems:
        raise SubmissionError("; ".join(problems))
    with open(config["file"], "w", encoding="utf-8") as handle:
        handle.write(updated)

    report(
        destination,
        {
            "status": "added",
            "file": config["file"],
            "kind": config["label"],
            "summary": summary.replace("\n", " ")[:120],
            "branch": f"data-entry/issue-{args.issue}",
        },
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SubmissionError as error:
        sys.stderr.write("error: " + str(error) + "\n")
        report(os.environ.get("GITHUB_OUTPUT"), {"status": "error", "message": error})
        sys.exit(1)

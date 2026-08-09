#!/usr/bin/env python3
"""Run every issue form through add_entry.py against a copy of ``data/``.

Nothing else exercises this pipeline until a real issue is filed, so this
renders a filled-in submission the way GitHub renders one, feeds it through
the real code path, and checks that what lands in the data file is the shape
the Hugo partials and the LaTeX CV expect.

    python .github/scripts/selftest.py

Run from the repository root. Only network-free cases are covered; the
BibTeX form is tested with pasted BibTeX rather than a DOI lookup.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bibtex  # noqa: E402
import issue_form  # noqa: E402
import sections  # noqa: E402

SCRIPT = os.path.join(".github", "scripts", "add_entry.py")

# One filled-in submission per issue form, keyed by field id.
CASES = {
    "news": {
        "date": "2026-08-01",
        "title": "A new paper",
        "text": "It is about splines.",
        "url": "https://doi.org/10.0000/test",
        "featured": True,
    },
    "conference": {
        "name": "A Conference",
        "title": "A Talk",
        "location": "Delft, The Netherlands",
        "start": "2026-05-01",
        "end": "",
        "invited": True,
        "featured": False,
    },
    "software": {
        "name": "gsTest",
        "role": "Developer",
        "description": "A module.",
        "url": "https://github.com/gismo/gsTest",
        "doi": "10.5281/zenodo.1",
        "featured": True,
    },
    "award": {
        "title": "Best Poster",
        "location": "Some Society",
        "year": "2026",
        "featured": True,
    },
    "membership": {
        "organization": "Some Society",
        "member": "Member",
        "start": "2026-01-01",
        "url": "https://example.org/",
        "featured": False,
    },
    "experience": {
        "type": "visit",
        "role": "Visiting Researcher",
        "location": "Pavia, Italy",
        "start": "2026-02-01",
        "end": "2026-03-01",
        "institute": "Università di Pavia",
        "visiting": "prof. A. Reali",
        "duration": "4 weeks",
        "featured": False,
    },
    "teaching": {
        "course": "Numerical Methods (AB1234)",
        "role": "Lecturer",
        "university": "Technische Universiteit Eindhoven",
        "degree": "Mechanical Engineering",
        "level": "MSc",
        "start": "2026-01-01",
        "end": "2026-06-01",
        "duration": "1 quarter",
        "featured": True,
    },
    "supervision": {
        "name": "A Student",
        "title": "A Thesis",
        "level": "MSc",
        "degree": "Applied Mathematics",
        "university": "Technische Universiteit Delft",
        "role": "Daily supervisor",
        "graduation": "2026-07-01",
        "cosupervisors": "dr. M. Möller",
        "featured": False,
    },
    "education": {
        "school": "Technische Universiteit Delft",
        "degree": "Master of Science",
        "start": "2016-09-01",
        "end": "2019-07-22",
        "major": "Maritime Technology",
        "notes": "Cum Laude",
        "schoollink": "https://tudelft.nl",
        "featured": True,
    },
    "publication": {
        "entry-type": "article",
        "title": "A Manual Paper",
        "author": "H. M. Verhelst, M. Möller",
        "year": "2026",
        "url": "https://doi.org/10.0000/manual",
        "journal": "Journal of Tests",
        "volume": "1",
        "pages": "1-10",
        "abstract": "An abstract.",
        "featured": True,
    },
    "publication-bibtex": {
        "bibtex": (
            "@article{Verhelst2026x,\n"
            "  author  = {Verhelst, Hugo M. and M{\\\"o}ller, Matthias and "
            "Den Besten, Henk},\n"
            "  title   = {Adaptive {THB}-spline analysis},\n"
            "  journal = {Computer Methods in Applied Mechanics and Engineering},\n"
            "  volume  = {440},\n"
            "  pages   = {118855--118870},\n"
            "  year    = {2026},\n"
            "  doi     = {10.1016/j.cma.2026.118855},\n"
            "  abstract = {A short abstract.}\n"
            "}"
        ),
        "entry-type": "auto-detect from the BibTeX entry type",
        "cite-key": "",
        "featured": True,
    },
}

# What each case must produce in the data file.
EXPECTED = {
    "news": {"date": "2026-08-01", "featured": True},
    "conference": {"end": "", "invited": True, "featured": False},
    "software": {"doi": "10.5281/zenodo.1"},
    "award": {"type": "award"},
    "membership": {"type": "membership", "end": ""},
    "experience": {"type": "visit", "duration": "4 weeks"},
    "teaching": {"level": "MSc"},
    "supervision": {"graduation": "2026-07-01"},
    "education": {"major": "Maritime Technology"},
}

failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def render(template, answers):
    """Render a submission the way GitHub renders a completed issue form."""
    lines = []
    for field in issue_form.fields(template):
        attributes = field["attributes"]
        value = answers.get(field.get("id"))
        lines.append("### " + attributes["label"])
        lines.append("")
        if field["type"] == "checkboxes":
            for option in attributes["options"]:
                mark = "X" if value else " "
                lines.append(f"- [{mark}] {option['label']}")
        elif value in (None, ""):
            lines.append(issue_form.NO_RESPONSE)
        else:
            lines.append(str(value))
        lines.append("")
    return "\n".join(lines)


def run_case(stem, template, answers, workdir):
    body = render(template, answers)

    matched, _ = issue_form.match_template(body, issue_form.load_templates())
    check(matched == stem, f"{stem}: body matched template {matched!r}")

    body_file = os.path.join(workdir, "body.md")
    with open(body_file, "w", encoding="utf-8") as handle:
        handle.write(body)
    report_file = os.path.join(workdir, "report.txt")

    config = sections.config(stem)
    before = json.load(open(config["file"], encoding="utf-8"))

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--body-file",
            body_file,
            "--issue",
            "1",
            "--report",
            report_file,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        failures.append(f"{stem}: add_entry.py failed: {result.stderr.strip()}")
        return

    report = dict(
        line.split("=", 1)
        for line in open(report_file, encoding="utf-8").read().splitlines()
        if "=" in line
    )
    check(report.get("status") == "added", f"{stem}: status={report.get('status')}")

    after = json.load(open(config["file"], encoding="utf-8"))
    check(len(after) == len(before) + 1, f"{stem}: entry count did not grow by one")
    added = [entry for entry in after if entry not in before]
    check(len(added) == 1, f"{stem}: {len(added)} new entries instead of one")
    if not added:
        return
    entry = added[0]

    for key, value in EXPECTED.get(stem, {}).items():
        check(
            entry.get(key) == value,
            f"{stem}: {key} is {entry.get(key)!r}, expected {value!r}",
        )
    check(
        all(key in config["order"] for key in entry),
        f"{stem}: unexpected keys {set(entry) - set(config['order'])}",
    )
    return entry


def main():
    if not os.path.isdir(".github/ISSUE_TEMPLATE"):
        sys.exit("run from the repository root")

    templates = issue_form.load_templates()
    check(
        set(templates) == set(CASES),
        f"untested templates: {sorted(set(templates) ^ set(CASES))}",
    )

    workdir = tempfile.mkdtemp(prefix="data-entry-selftest-")
    backup = os.path.join(workdir, "data")
    shutil.copytree("data", backup)
    entries = {}
    try:
        for stem in sorted(CASES):
            if stem not in templates:
                continue
            entries[stem] = run_case(stem, templates[stem], CASES[stem], workdir)
    finally:
        shutil.rmtree("data")
        shutil.copytree(backup, "data")
        shutil.rmtree(workdir)

    manual = entries.get("publication")
    if manual:
        check(
            manual["cite-key"] == "Verhelst2026",
            f"publication: cite key {manual['cite-key']!r} does not avoid clashes",
        )
        check("issue" not in manual["description"], "publication: empty issue emitted")

    parsed = entries.get("publication-bibtex")
    if parsed:
        description = parsed["description"]
        check(
            description["author"] == "H. M. Verhelst, M. Möller, H. Den Besten",
            f"bibtex: authors came out as {description['author']!r}",
        )
        check(
            description["title"] == "Adaptive THB-spline analysis",
            f"bibtex: title came out as {description['title']!r}",
        )
        check(
            description["url"] == "https://doi.org/10.1016/j.cma.2026.118855",
            f"bibtex: url came out as {description['url']!r}",
        )
        check(description["pages"] == "118855-118870", "bibtex: page range not tidied")
        check(parsed["entry-type"] == "article", "bibtex: entry type not detected")

    # A pasted BibTeX block usually arrives wrapped in a code fence, and a
    # pasted DOI sometimes does too.
    add_entry = __import__("add_entry")
    check(
        add_entry.unfence("```bibtex\n@misc{a, title={T}}\n```").startswith("@misc"),
        "unfence: fenced BibTeX not unwrapped",
    )
    check(
        add_entry.unfence("```\n10.0000/x\n```") == "10.0000/x",
        "unfence: fenced DOI not unwrapped",
    )

    # A few author-formatting shapes that publisher exports actually emit.
    for source, expected in [
        ("Verhelst, Hugo M. and Möller, M.", "H. M. Verhelst, M. Möller"),
        ("Hugo M. Verhelst and Matthias Möller", "H. M. Verhelst, M. Möller"),
        ("den Besten, Johan Henk", "J. H. den Besten"),
        ("Jean-Pierre Dupont", "J.-P. Dupont"),
    ]:
        got = bibtex.format_authors(source)
        check(got == expected, f"authors: {source!r} -> {got!r}, wanted {expected!r}")

    if failures:
        for failure in failures:
            print("FAIL " + failure)
        sys.exit(1)
    print(f"ok — {len(CASES)} issue forms round-trip into data/")


if __name__ == "__main__":
    main()

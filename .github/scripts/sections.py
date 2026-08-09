"""Where each issue form lands in ``data/`` and in what shape.

One entry per issue-form template. The form field ids are deliberately the
same strings as the JSON keys, so there is no separate field mapping to keep
in sync — this table only records the things a form cannot express: key order,
fixed values, which keys survive being empty, and where in the file a new
record belongs.
"""

# ``order``      key order in the emitted object; keys not listed are dropped.
# ``constant``   values fixed by the template rather than answered by a human.
# ``booleans``   always emitted, even when false.
# ``keep_empty`` optional keys that existing entries carry as "" — emitted so
#                the record matches its neighbours.
# ``group_by``   insert next to the entries sharing this key's value.
# ``sort``       ``(key, reverse)`` to place the entry, or None to append.
# ``label``      human summary used for the branch name, commit and PR title.

SECTIONS = {
    "news": {
        "file": "data/news.json",
        "order": ["date", "title", "text", "url", "details", "featured"],
        "booleans": ["featured"],
        "sort": ("date", True),
        "label": "news item",
        "summary": "{title}",
    },
    "conference": {
        "file": "data/conferences.json",
        "order": [
            "name",
            "location",
            "title",
            "start",
            "end",
            "url",
            "details",
            "featured",
            "invited",
        ],
        "booleans": ["featured", "invited"],
        "keep_empty": ["end"],
        "sort": ("start", False),
        "label": "conference contribution",
        "summary": "{title} ({name})",
    },
    "software": {
        "file": "data/software.json",
        "order": ["name", "role", "description", "url", "doi", "details", "featured"],
        "booleans": ["featured"],
        "label": "software entry",
        "summary": "{name}",
    },
    "award": {
        "file": "data/awards.json",
        "constant": {"type": "award"},
        "order": ["type", "title", "location", "year", "featured"],
        "booleans": ["featured"],
        "group_by": "type",
        "label": "award",
        "summary": "{title}",
    },
    "membership": {
        "file": "data/awards.json",
        "constant": {"type": "membership"},
        "order": ["type", "organization", "member", "url", "start", "end", "featured"],
        "booleans": ["featured"],
        "keep_empty": ["end"],
        "group_by": "type",
        "label": "membership",
        "summary": "{organization}",
    },
    "experience": {
        "file": "data/experience.json",
        "order": [
            "type",
            "role",
            "institute",
            "organization",
            "department",
            "location",
            "visiting",
            "duration",
            "url",
            "start",
            "end",
            "featured",
        ],
        "booleans": ["featured"],
        "group_by": "type",
        "label": "experience entry",
        "summary": "{role}",
    },
    "teaching": {
        "file": "data/teaching.json",
        "order": [
            "degree",
            "level",
            "course",
            "university",
            "start",
            "end",
            "duration",
            "url",
            "role",
            "featured",
        ],
        "booleans": ["featured"],
        "label": "teaching entry",
        "summary": "{course}",
    },
    "supervision": {
        "file": "data/supervision.json",
        "order": [
            "name",
            "university",
            "degree",
            "title",
            "level",
            "graduation",
            "cosupervisors",
            "role",
            "url",
            "featured",
        ],
        "booleans": ["featured"],
        "label": "supervision entry",
        "summary": "{name} ({level})",
    },
    "education": {
        "file": "data/education.json",
        "order": [
            "school",
            "schoollink",
            "degree",
            "major",
            "notes",
            "start",
            "end",
            "thesis",
            "thesislink",
            "supervisors",
            "featured",
        ],
        "booleans": ["featured"],
        "label": "education entry",
        "summary": "{degree}, {school}",
    },
}

# Publications are nested (``description``) and have two front doors: a form
# with one field per BibTeX field, and a form that takes the BibTeX itself.
PUBLICATION = {
    "file": "data/publications.json",
    "order": ["cite-key", "entry-type", "description", "featured"],
    "description_order": [
        "author",
        "title",
        "journal",
        "booktitle",
        "editor",
        "series",
        "school",
        "degree",
        "publisher",
        "volume",
        "issue",
        "pages",
        "year",
        "date",
        "eprint",
        "url",
        "image",
        "imageCaption",
        "abstract",
    ],
    "booleans": ["featured"],
    "label": "publication",
    "summary": "{title}",
}

# BibTeX entry type -> the site's entry-type. Which values are legal, and
# which fields each of them needs, lives in .github/schemas/.
BIBTEX_ENTRY_TYPES = {
    "article": "article",
    "inproceedings": "inproceeding",
    "conference": "inproceeding",
    "proceedings": "inproceeding",
    "incollection": "incollection",
    "inbook": "incollection",
    "bookchapter": "incollection",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
    "thesis": "thesis",
    "unpublished": "unpublished",
    "misc": "unpublished",
    "techreport": "unpublished",
    "preprint": "unpublished",
}

PUBLICATION_TEMPLATES = ("publication", "publication-bibtex")


def config(stem):
    """The section configuration behind an issue-form file stem."""
    if stem in PUBLICATION_TEMPLATES:
        return PUBLICATION
    return SECTIONS[stem]

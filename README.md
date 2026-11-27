[![Website](https://img.shields.io/website?url=https%3A%2F%2Fwww.hugoverhelst.nl&label=hugoverhelst.nl)](https://hugoverhelst.nl)
[![Website](https://img.shields.io/website?url=https%3A%2F%2Fhverhelst.github.io&label=hverhelst.github.io)](https://hverhelst.github.io)

Personal academic website, built with [Hugo](https://gohugo.io/). The layouts, the CV
writer and the data-entry machinery live in
[data-based-academic-website](https://github.com/hverhelst/data-based-academic-website),
carried here as a submodule at `themes/dbaw`. **This repository is data.**

```sh
git clone --recurse-submodules https://github.com/hverhelst/hverhelst.github.io
# or, in an existing clone:
git submodule update --init
```

Dependabot opens a pull request when the theme moves; `.github/workflows/data-checks.yml`
fails on that pull request if the vendored issue forms have fallen behind it.

## Content model

Every section of the site is generated from a JSON file in `data/`: `news`, `education`,
`experience`, `awards`, `publications`, `conferences`, `software`, `teaching`, `supervision`.

`data/sections.json` is the registry: it lists the sections, in order, and how each is
rendered. It lives in `data/` rather than in `hugo.toml` because the LaTeX CV reads the
same file, which is what stops the website and the PDF from drifting apart. Entries flagged
`"featured": true` also appear on the homepage.

To add a section, two things are needed:

1. `data/<name>.json` — an array of flat records;
2. an entry in `data/sections.json` naming which fields to show.

```json
{
  "id": "grants",
  "style": "generic",
  "label": "Grants & Funding",
  "cvLabel": "Grants & Funding",
  "titleField": "title",
  "subtitleField": "funder",
  "dateField": "year",
  "linkField": "url"
}
```

That is enough for it to appear on the homepage and in the CV. Everything else is optional:
a `content/<name>/_index.md` stub gives it a page of its own and turns the heading into a
link; a `.github/schemas/<name>.schema.json` gets it validated in CI; an issue form gets it
into the pull-request pipeline; and a `layouts/partials/sections/<name>.html` in *this*
repository overrides the theme's generic renderer if the default shape is not good enough.

## Schemas

Each data file has a JSON Schema in `.github/schemas/`, checked in CI by
`.github/workflows/data-checks.yml` and reused by the issue-form pipeline, so a hand-written
record and a form-built one are held to the same standard:

```sh
python themes/dbaw/scripts/validate_data.py
```

They live outside `data/` on purpose — anything under `data/` is ingested by Hugo as site
data. `.vscode/settings.json` wires them up for autocomplete and inline errors while editing.

They exist for one failure the build cannot see. Every section preset dispatches on an
enum-valued field with **no fallback branch** — `entry-type` in publications, `type` in
experience and awards, `level` in teaching and supervision, `invited` in conferences. Write
`"inproceedings"` for `"inproceeding"`, or leave out `"invited"`, and the entry silently
disappears from both the website and the CV while `hugo` and `compile_CV.sh` still exit 0.
The schemas also pin ISO dates, four-digit years, URL schemes, per-`type` required fields,
and reject unknown keys; `validate_data.py` additionally rejects duplicate cite keys.

## Adding entries through issues

New records do not have to be hand-edited into `data/`. [Opening an
issue](../../issues/new/choose) offers a form per section — publication, news item,
conference contribution, software, award, membership, experience, teaching, supervision,
education. Submitting one triggers `.github/workflows/add-entry.yml`, which builds the
record, checks that the site still compiles, and opens a pull request against `master` for
review. Merging it publishes; closing the issue or the pull request throws it away.

Publications have two forms. One asks for each field, the other takes **BibTeX or a DOI** —
a bare DOI is resolved to BibTeX through doi.org, LaTeX accents are decoded (`M{\"o}ller` →
Möller), authors are reformatted to the site's `H. M. Verhelst, M. Möller` style, and the
cite key is taken from the BibTeX or derived as `Surname` + year with a suffix if it is
already taken. A figure dropped into the form is committed to `static/media/<cite-key>.png`
and wired up as the record's `image`.

Notes:

- GitHub does not accept `.bib` as an attachment file type. Paste the BibTeX into the form,
  or rename the file to `.txt`, drag it in, and paste the resulting link.
- Only issues opened by the repository owner are acted on.
- Editing the issue rebuilds the branch and updates the pull request, so mistakes are fixed
  by editing rather than by opening a new issue.
- The forms apply labels (`data-entry` and the section name). Those are cosmetic — the
  workflow identifies the form by matching the submitted headings against
  `.github/ISSUE_TEMPLATE/*.yml`, so nothing breaks if a label does not exist.
- Pull requests opened with `GITHUB_TOKEN` do not trigger other workflows, which is why
  `add-entry.yml` runs `hugo` itself before opening one.

How it fits together, all under `themes/dbaw/scripts/`:

| File | Role |
| --- | --- |
| `add_entry.py` | Entry point: match form, build record, write the data file |
| `issue_form.py` | Recovers field ids by reading the templates back out of `ISSUE_TEMPLATE/` |
| `paths.py` | Resolves site-owned paths against `--site-root`, theme-owned ones against itself |
| `enable_issue_forms.py` | Copies the forms, schemas and workflows in — and reports drift |
| `sections.py` | Key order, fixed values and insertion position per section |
| `bibtex.py` | Dependency-free BibTeX reader and LaTeX-to-Unicode decoding |
| `json_splice.py` | Inserts the record without reformatting the rest of the file |
| `validate_data.py` | Checks records against the schemas, site copy before theme preset |
| `selftest.py` | Runs every form through the pipeline; also a CI workflow |

Form field ids are deliberately the same strings as the JSON keys, so adding a field to a
section means adding it to the template, to that section's `order` in `sections.py`, and to
the schema — `sections.py` says where a record goes, the schema says what a valid one looks
like, and neither restates the other. Run `python themes/dbaw/scripts/selftest.py` from the
repository root after changing any of it.

The forms themselves have to be copied into this repository, because GitHub reads issue
templates only from the repository they belong to. One command both installs and refreshes
them:

```sh
python themes/dbaw/scripts/enable_issue_forms.py
```

## Foldable record details

Any record may carry an optional collapsible region — an abstract, a longer write-up, a
graphical abstract, or any combination:

```json
{
  "abstract": "Markdown is supported here.",
  "image": "media/my-figure.png",
  "imageCaption": "Used as alt text and figure caption"
}
```

- Publications use `abstract` (inside `description`); every other section uses `details`.
- `image` is a path under `static/` (`media/…`) or an absolute URL to a publisher-hosted
  figure. Local files live in `static/media/`.
- The toggle appears only when at least one of the two fields is present, so records
  without them render exactly as before. Its label is "Abstract" for publications,
  "Read more" for news, "Details" elsewhere — and "Figure" when a record has an image but
  no text.
- Clicking a figure opens a lightbox with a button pointing at the record's `url` (or DOI).

Implemented by the theme's `layouts/partials/recordDetails.html` using Bootstrap's collapse
component (no extra dependency).

## Automatic CV

`themes/dbaw/compile_CV.sh` builds `static/doc/CV.pdf` from the same `data/*.json` files
using LuaLaTeX (`autoCV.tex` parses the JSON at compile time via `lualibs`). It must run
from the repository root, and runs LuaLaTeX twice so `\pageref{LastPage}` resolves. GitHub
Actions runs it on every deploy, so the PDF never drifts from the website. The PDF is a
build artifact and is not committed.

The CV walks `data/sections.json`, so a section added to the site reaches the PDF too. Two
keys steer it: `inCV: false` leaves a section out (`news` uses this), and `cvLabel` supplies
the heading, because the CV's wording is usually longer than the site's — "Conference and
seminar presentations" against "Conferences".

Note: the CV always includes *all* entries — the `featured` flag only affects the website
homepage. To use a modified CV layout, put a `latex/autoCV.tex` in this repository and it
wins over the theme's.

## Local development

```sh
git submodule update --init          # first time, or after cloning without --recurse-submodules
hugo server                          # http://localhost:1313
bash themes/dbaw/compile_CV.sh       # rebuild the PDF CV
```

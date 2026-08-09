[![Website](https://img.shields.io/website?url=https%3A%2F%2Fwww.hugoverhelst.nl&label=hugoverhelst.nl)](https://hugoverhelst.nl)
[![Website](https://img.shields.io/website?url=https%3A%2F%2Fhverhelst.github.io&label=hverhelst.github.io)](https://hverhelst.github.io)

Personal academic website, built with [Hugo](https://gohugo.io/) from the
[hugo-resume](https://github.com/eddiewebb/hugo-resume) template (vendored into this repo —
there is no `themes/` directory, the layouts *are* the theme).

## Content model

Every section of the site is generated from a JSON file in `data/`: `news`, `education`,
`experience`, `awards`, `publications`, `conferences`, `software`, `teaching`, `supervision`.
`config.toml` lists the active sections in `params.sections`; each has a matching
`layouts/partials/<section>Summary.html` renderer and a stub `content/<section>/_index.md`.
Entries flagged `"featured": true` also appear on the homepage.

To add a section: create `data/<name>.json`, a `<name>Summary.html` partial, a content stub,
an `i18n/en.json` label, and add the name to `params.sections`.

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

How it fits together, all under `.github/scripts/`:

| File | Role |
| --- | --- |
| `add_entry.py` | Entry point: match form, build record, write the data file |
| `issue_form.py` | Recovers field ids by reading the templates back out of `ISSUE_TEMPLATE/` |
| `sections.py` | Key order, fixed values and insertion position per section |
| `bibtex.py` | Dependency-free BibTeX reader and LaTeX-to-Unicode decoding |
| `json_splice.py` | Inserts the record without reformatting the rest of the file |
| `selftest.py` | Runs every form through the pipeline; also a CI workflow |

Form field ids are deliberately the same strings as the JSON keys, so adding a field to a
section means adding it to the template and to that section's `order` in `sections.py` —
there is no third mapping to keep in sync. Run `python .github/scripts/selftest.py` from the
repository root after changing any of it.

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

Implemented by `layouts/partials/recordDetails.html` using Bootstrap's collapse component
(no extra dependency).

## Automatic CV

`./compile_CV.sh` builds `static/doc/CV.pdf` from the same `data/*.json` files using
LuaLaTeX (`latex/autoCV.tex` parses the JSON at compile time via `lualibs`). The script must
run from the repository root, and runs LuaLaTeX twice so `\pageref{LastPage}` resolves.
GitHub Actions runs it on every deploy, so the PDF never drifts from the website. The PDF is
a build artifact and is not committed.

Note: the CV always includes *all* entries — the `featured` flag only affects the website
homepage.

## Local development

```sh
./compile.sh        # hugo server at http://localhost:1313
./compile_CV.sh     # rebuild the PDF CV
```

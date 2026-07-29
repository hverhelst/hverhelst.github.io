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

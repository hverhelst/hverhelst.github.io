#!/bin/bash
# Builds the CV PDF from latex/autoCV.tex + data/*.json.
# MUST run from the repository root: the Lua code opens data/*.json with
# CWD-relative paths. -output-directory only affects TeX outputs, not io.open.
set -euo pipefail
cd "$(dirname "$0")"

BUILDDIR=build/CV
mkdir -p "$BUILDDIR" static/doc

# Two passes: lastpage + hyperref need a second run for \pageref{LastPage}.
for pass in 1 2; do
    lualatex --interaction=nonstopmode --halt-on-error \
             --output-directory="$BUILDDIR" latex/autoCV.tex
done

cp "$BUILDDIR/autoCV.pdf" static/doc/CV.pdf
echo "CV written to static/doc/CV.pdf"

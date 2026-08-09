"""A small, dependency-free BibTeX reader, good enough for publisher exports.

Only what this repository needs: one entry at a time, brace- or quote-
delimited values, ``@string`` and comments skipped, and enough LaTeX decoding
that "M{\\\"o}ller" comes out of the other end as "Möller".
"""

import re
import unicodedata

# LaTeX accent commands, mapped to the combining mark they apply to.
_COMBINING = {
    "`": "\u0300",
    "'": "\u0301",
    "^": "\u0302",
    "~": "\u0303",
    "=": "\u0304",
    "u": "\u0306",
    ".": "\u0307",
    '"': "\u0308",
    "r": "\u030a",
    "H": "\u030b",
    "v": "\u030c",
    "c": "\u0327",
    "k": "\u0328",
    "d": "\u0323",
    "b": "\u0331",
}

# Standalone LaTeX commands that stand for a single character.
_LITERAL = {
    "ss": "ß",
    "o": "ø",
    "O": "Ø",
    "l": "ł",
    "L": "Ł",
    "aa": "å",
    "AA": "Å",
    "ae": "æ",
    "AE": "Æ",
    "oe": "œ",
    "OE": "Œ",
    "i": "ı",
    "j": "ȷ",
    "&": "&",
    "%": "%",
    "$": "$",
    "#": "#",
    "_": "_",
    "{": "{",
    "}": "}",
    "textendash": "–",
    "textemdash": "—",
    "ldots": "…",
    "dots": "…",
    "'": "'",
    "`": "`",
}


def _apply_accent(command, letter):
    letter = letter or " "
    return unicodedata.normalize("NFC", letter + _COMBINING[command])


def latex_to_text(value):
    """Best-effort conversion of a LaTeX fragment to plain Unicode."""
    if not value:
        return ""
    text = value

    # \"{o} / \"o / \c{c} / \v s
    accents = "".join(re.escape(key) for key in _COMBINING)
    text = re.sub(
        r"\\([%s])\s*\{\\?([A-Za-z]?)\}" % accents,
        lambda m: _apply_accent(m.group(1), m.group(2)),
        text,
    )
    text = re.sub(
        r"\\([%s])\s*([A-Za-z])" % accents,
        lambda m: _apply_accent(m.group(1), m.group(2)),
        text,
    )
    # {\ss} / \ss{} / \&
    text = re.sub(
        r"\\([A-Za-z]+|[&%$#_{}'`])\s*\{\}|\\([A-Za-z]+|[&%$#_{}'`])",
        lambda m: _LITERAL.get(m.group(1) or m.group(2), m.group(0)),
        text,
    )
    # Math mode and remaining grouping braces carry no meaning here.
    text = text.replace("$", "")
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"~", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _split_fields(body):
    """Split an entry body on the commas that separate top-level fields."""
    parts = []
    depth = 0
    quoted = False
    current = []
    for ch in body:
        if ch == "{" and not quoted:
            depth += 1
        elif ch == "}" and not quoted:
            depth -= 1
        elif ch == '"' and depth == 0:
            quoted = not quoted
        if ch == "," and depth == 0 and not quoted:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return [part for part in parts if part.strip()]


def _strip_delimiters(value):
    value = value.strip()
    while len(value) >= 2 and (
        (value[0] == "{" and value[-1] == "}") or (value[0] == '"' and value[-1] == '"')
    ):
        value = value[1:-1].strip()
    return value


def parse(source):
    """Parse the first real entry in ``source`` into ``(type, key, fields)``.

    ``fields`` keys are lower-cased; values are LaTeX-decoded.
    """
    for match in re.finditer(r"@(\w+)\s*[{(]", source):
        entry_type = match.group(1).lower()
        if entry_type in ("comment", "string", "preamble"):
            continue

        opening = match.end() - 1
        depth = 0
        end = None
        for i in range(opening, len(source)):
            if source[i] in "{(":
                depth += 1
            elif source[i] in "})":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            raise ValueError("unbalanced braces in BibTeX entry")

        parts = _split_fields(source[opening + 1 : end])
        if not parts:
            raise ValueError("BibTeX entry has no body")

        cite_key = parts[0].strip()
        fields = {}
        for part in parts[1:]:
            if "=" not in part:
                continue
            name, _, value = part.partition("=")
            fields[name.strip().lower()] = latex_to_text(_strip_delimiters(value))
        return entry_type, cite_key, fields

    raise ValueError("no BibTeX entry found")


def _split_names(author):
    """Split a BibTeX author list on top-level ``and``."""
    names = []
    depth = 0
    current = []
    tokens = re.split(r"(\s+and\s+)", author)
    for token in tokens:
        if re.fullmatch(r"\s+and\s+", token) and depth == 0:
            names.append("".join(current))
            current = []
            continue
        depth += token.count("{") - token.count("}")
        current.append(token)
    names.append("".join(current))
    return [name.strip() for name in names if name.strip()]


def _initials(given):
    out = []
    for part in re.split(r"[\s.]+", given):
        if not part:
            continue
        if "-" in part:
            out.append("-".join(p[0].upper() + "." for p in part.split("-") if p))
        else:
            out.append(part[0].upper() + ".")
    return " ".join(out)


def format_authors(author):
    """Render a BibTeX author list the way ``publications.json`` writes them.

    ``Verhelst, Hugo M. and Möller, Matthias`` becomes
    ``H. M. Verhelst, M. Möller``.
    """
    people = []
    for name in _split_names(author):
        if name.lower() in ("others", "et al."):
            people.append("et al.")
            continue
        if "," in name:
            family, _, given = name.partition(",")
            # Drop a "Jr."-style suffix in a second comma-separated group.
            given = given.split(",")[0]
        else:
            words = name.split()
            particle = 0
            for i, word in enumerate(words[:-1]):
                if word[:1].islower():
                    particle = i
                    break
                particle = i + 1
            family = " ".join(words[particle:])
            given = " ".join(words[:particle])
        family = family.strip()
        given = _initials(given.strip())
        people.append(" ".join(part for part in (given, family) if part))
    return ", ".join(people)


def surname(author):
    """The family name of the first author, stripped to ASCII letters."""
    names = _split_names(author)
    if not names:
        return ""
    first = names[0]
    family = first.partition(",")[0] if "," in first else first.split()[-1]
    ascii_family = unicodedata.normalize("NFKD", family)
    return re.sub(r"[^A-Za-z]", "", ascii_family)

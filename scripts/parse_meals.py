#!/usr/bin/env python3
"""
Parse ``meals-struct.md`` (the prepared K.FIT meal catalog) into a structured
JSON seed used by the Alembic data migration.

Source quirks handled:
  - Protein in the source is expressed in CALORIES ("חלבון: 140 קלורי").
    Stored verbatim as ``protein_calories`` (no conversion — source data is
    never transformed).
  - Some items have no protein ("לא צוין בקובץ") -> protein_calories = null.
  - Category is "רגיל" for every item -> meal_type "generic".

Output: JSON array on stdout. Run from anywhere; pass the md path as argv[1].
"""
import json
import re
import sys

SEED_TAG = "meals-struct-v1"

HEADER_RE = re.compile(r"^### פריט\s+(\d+)\s+-\s+(.+?)\s+-\s+עמוד\s+(\d+)\s*$")
CAL_RE = re.compile(r"^- קלוריות:\s*(\d+)")
PROT_RE = re.compile(r"^- חלבון:\s*(.+?)\s*$")
CAT_RE = re.compile(r"^- קטיגוריה:\s*(.+?)\s*$")
INT_RE = re.compile(r"(\d+)")

CATEGORY_MAP = {"רגיל": "generic"}


def parse(md_path: str) -> list[dict]:
    lines = open(md_path, encoding="utf-8").read().splitlines()

    # Only parse the detail section, never the index table.
    try:
        start = next(
            i for i, ln in enumerate(lines) if ln.startswith("## פירוט מלא")
        )
    except StopIteration:
        sys.exit("could not find '## פירוט מלא' detail section")
    lines = lines[start:]

    # Split into per-item blocks on the '### פריט' headers.
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for ln in lines:
        if HEADER_RE.match(ln):
            if current is not None:
                blocks.append(current)
            current = [ln]
        elif current is not None:
            current.append(ln)
    if current is not None:
        blocks.append(current)

    meals: list[dict] = []
    for block in blocks:
        meals.append(parse_block(block))
    return meals


def parse_block(block: list[str]) -> dict:
    m = HEADER_RE.match(block[0])
    item_no, name, page = int(m.group(1)), m.group(2).strip(), int(m.group(3))

    calories: int | None = None
    protein_calories: int | None = None
    category = "רגיל"
    content: list[str] = []
    in_content = False

    for ln in block[1:]:
        if CAL_RE.match(ln):
            calories = int(CAL_RE.match(ln).group(1))
            in_content = False
            continue
        pm = PROT_RE.match(ln)
        if pm:
            digits = INT_RE.search(pm.group(1))
            protein_calories = int(digits.group(1)) if digits else None
            in_content = False
            continue
        if ln.strip() == "- תוכן:":
            in_content = True
            continue
        cm = CAT_RE.match(ln)
        if cm:
            category = cm.group(1).strip()
            in_content = False
            continue
        if in_content:
            stripped = re.sub(r"^\s*-\s?", "", ln)
            if stripped.strip():
                content.append(stripped.rstrip())

    if calories is None:
        sys.exit(f"item {item_no}: missing calories")

    meal_type = CATEGORY_MAP.get(category, "generic")

    return {
        "name": name,
        "calories": calories,
        "protein_calories": protein_calories,  # verbatim from source, may be None
        "meal_type": meal_type,
        "payload": {
            "_seed": SEED_TAG,
            "item_no": item_no,
            "source_page": page,
            "name_he": name,
            "protein_calories": protein_calories,
            "content": content,
        },
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "meals-struct.md"
    data = parse(path)
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    print(file=sys.stderr)
    print(f"parsed {len(data)} meals", file=sys.stderr)

#!/usr/bin/env python3
"""Check every skill's SKILL.md frontmatter and the relative links in the repo's markdown.

  scripts/check_skills.py

Each skills/<dir>/SKILL.md must open with a frontmatter block whose `name` equals <dir> and
whose `description` is non-empty. Every relative markdown link in a tracked .md file outside
archive/ must point at a file or directory that exists. Stdlib only.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True,
                                    cwd=Path(__file__).parent).strip())
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"^(```|~~~).*?^\1", re.DOTALL | re.MULTILINE)


def frontmatter(text):
    """Return the top-level `key: value` pairs of a leading --- block (folded values joined)."""
    m = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None
    fields, key = {}, None
    for line in m.group(1).splitlines():
        top = re.match(r"([A-Za-z_-]+):\s*(.*)", line)
        if top:
            key = top.group(1)
            value = top.group(2)
            fields[key] = "" if value in (">", ">-", "|", "|-") else value
        elif key and line.startswith(" "):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def check_skills():
    errors = []
    for skill_md in sorted(ROOT.glob("skills/*/SKILL.md")):
        name = skill_md.parent.name
        fields = frontmatter(skill_md.read_text(encoding="utf-8"))
        rel = skill_md.relative_to(ROOT)
        if fields is None:
            errors.append(f"{rel}: no frontmatter block")
            continue
        if fields.get("name") != name:
            errors.append(f"{rel}: name is {fields.get('name')!r}, expected {name!r}")
        if not fields.get("description"):
            errors.append(f"{rel}: description is missing or empty")
    return errors


def check_links():
    errors = []
    tracked = subprocess.check_output(["git", "ls-files", "*.md"], text=True, cwd=ROOT).split()
    for rel in tracked:
        if rel.startswith("archive/"):
            continue
        path = ROOT / rel
        if not path.is_file():
            continue
        text = FENCE.sub("", path.read_text(encoding="utf-8"))
        for target in LINK.findall(text):
            if re.match(r"[a-z]+:", target) or target.startswith("#"):
                continue  # external URL, mailto, or in-page anchor
            if "<" in target:
                continue  # placeholder such as <skill-dir>/...
            file_part = target.split("#", 1)[0]
            if not (path.parent / file_part).exists():
                errors.append(f"{rel}: broken link {target}")
    return errors


def main():
    errors = check_skills() + check_links()
    for e in errors:
        print(e)
    if not errors:
        print("skills and links ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

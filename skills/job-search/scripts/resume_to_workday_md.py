#!/usr/bin/env python3
"""
resume_to_workday_md.py — transform the house-style résumé markdown (as used by
make_resume_pdf.sh) into a plain, single-column markdown intended for Workday's
"Autofill with Resume" parser, which chokes on the styled PDF.

This is a line-oriented, template-aware transform, not a general markdown rewriter. It
assumes the résumé follows the structure used across jobs/applications/*/resume.md and
the resume repo's role/* archetypes:

    # <Name>
    ## <Headline / subtitle>
    **Located in <City, ST>**<br>
    Phone: ...<br>
    Email: <...><br>
    GitHub: [...](...)<br>
    LinkedIn: [...](...)

    ## <Section>              (e.g. Summary, Industry Experience, Skills, Education)

    ### <Job Title>
    #### <Company> | <Mon YYYY - Mon YYYY or Present> | <Location>

    *Scope: ...*

    - bullet
    - bullet

Transform rules (see make_resume_workday.sh / job-search skill docs for the brief):
  - Name, headline, and each contact item become their own plain paragraph (no <br>, no
    header/footer), in source order.
  - Section headers are renamed to standard words (Summary, Experience, Education, Skills,
    Certifications; anything else is title-cased as given) and emitted as a real Heading 1 so
    pandoc produces a real Word Heading style.
  - Each job/education entry is split into separate plain-text lines: Job Title, Company (or
    Institution), Location (if present), then the date range with full month names ("April
    2017", not "Apr 2017"). A source line with only a year (no month) is left as-is — there is
    nothing to expand — and reported by the wrapper script as a heads-up.
  - A "*Scope: ...*" sub-line is de-italicized, has its leading "Scope:" label dropped (the
    sentence itself is kept so the description starts with real text, not a label), and is kept
    as its own plain descriptive paragraph, placed right after the date line and before the
    bullets. It is not merged into the first bullet (that would alter the bullet's wording);
    keeping it as a separate, un-styled line satisfies "fold into the description" without
    touching bullet content.
  - One company with multiple roles is only split into separate job entries when the source
    gives each role its own date range. The jobs repo's Kantata entry packs both roles
    ("Internal Infrastructure Platform" / "M-Bridge Integration Platform") as bullets under one
    shared Apr 2017 - Dec 2023 range with no per-role dates, so this script keeps it as one job
    entry (the wrapper script notes this explicitly rather than inventing split dates).
  - All bold/italic/link markdown is stripped to plain text. A markdown link's visible text is
    kept (e.g. "[github.com/x](https://...)" -> "github.com/x"); the destination URL is dropped
    since the visible text already reads as a URL. Em dashes and en dashes become plain hyphens.
  - Bullets become plain "- " list items (rendered as real Word bullets by pandoc). No tables,
    columns, or text boxes are introduced.

Rules learned from a live Workday "Autofill with Resume" test against the docx this script
produces (2026-10-05), since the parser only has four fields to assign per entry (Title,
Company, Location, Dates) and no concept of a non-job section:
  - A location line that reads "Remote" (any case, e.g. "Remote (US)", "Remote (part-time)") is
    OMITTED rather than emitted. Workday's parser mis-reads a bare "Remote" location line as the
    Job Title of a *new* entry, which shifts that entry's real company/dates/description down one
    row and appends the real title onto the *previous* entry's description. A real place name
    ("San Francisco, CA") parses into the Location field correctly, so those are kept.
  - A job title's " · <subtitle>" suffix (e.g. "Independent Consultant · AI-Native Software
    Delivery") is stripped before emitting. Workday otherwise splits on the separator and reads
    "Consultant" as the title and "AI-Native Software Delivery" as the company.
  - Narrow rule: when the (pre-strip) title contains "Independent" or "Consultant" (case
    insensitive), the Company field is forced to "Self-employed" regardless of what the source's
    "#### Company | Dates | Location" line says. This exists specifically for the
    "Independent Consultant" entry, whose source company text ("Client engagements") is a
    descriptive phrase, not an org name, and Workday parsed it as a second title/company pair.
    Keep this narrow: it only fires on consultant/independent titles, not on every entry.
  - Sections with no per-entry Company/Dates structure are dropped entirely from this render:
    "Open Source Projects", "Recommendations", and any Experience entry with no parseable
    "#### Company | Dates | Location" line (e.g. "Earlier Career (2001 - 2014)", which is a prose
    paragraph, not a job). Workday has no non-job section concept and was parsing these as blank
    or bled-together job entries. Output section order is fixed: contact block, Summary,
    Experience, Education, Skills; any other section is silently dropped.
  - This dropping is safe for the end recruiter: the Workday docx this script produces is used
    only to drive the platform's autofill step. The agent replaces the uploaded attachment with
    the full styled PDF (make_resume_pdf.sh output) immediately after, so nothing here is
    actually lost to the reader — see make_resume_workday.sh's header and the job-search skill's
    step 6a for the replace-the-attachment step this depends on.

Usage:
    resume_to_workday_md.py <input.md> <output.workday.md>
"""

import re
import sys

MONTHS = {
    "Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April",
    "May": "May", "Jun": "June", "Jul": "July", "Aug": "August",
    "Sep": "September", "Sept": "September", "Oct": "October",
    "Nov": "November", "Dec": "December",
}
MONTH_RE = re.compile(r"\b(" + "|".join(MONTHS.keys()) + r")\b")


def plain(text):
    """Strip markdown formatting to plain text, keeping link/autolink visible text."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)      # [text](url) -> text
    text = re.sub(r"<([^<>\s]+)>", r"\1", text)                # <email> / <url> -> bare text
    text = re.sub(r"<br\s*/?>", "", text)                      # stray <br>
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)             # **bold**
    text = re.sub(r"__([^_]+)__", r"\1", text)                 # __bold__
    text = re.sub(r"\*([^*]+)\*", r"\1", text)                 # *italic*
    text = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", text)      # _italic_
    text = text.replace("—", "-").replace("–", "-")  # em/en dash -> hyphen
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_date(s):
    s = plain(s)
    return MONTH_RE.sub(lambda m: MONTHS[m.group(1)], s)


def map_section_name(raw):
    low = raw.lower()
    if "summary" in low:
        return "Summary"
    if "experience" in low:
        return "Experience"
    if "education" in low:
        return "Education"
    if "skill" in low:
        return "Skills"
    if "certif" in low:
        return "Certifications"
    return raw.strip()


# Sections kept in the Workday render, and the fixed order they're emitted in. Anything else
# (e.g. "Open Source Projects", "Recommendations") has no per-entry Company/Dates structure
# Workday can parse and is dropped. See module docstring.
KEPT_SECTIONS = ("Summary", "Experience", "Education", "Skills")

TITLE_SUBTITLE_RE = re.compile(r"\s*·\s*.*$")
SELF_EMPLOYED_TITLE_RE = re.compile(r"\bindependent\b|\bconsultant\b", re.IGNORECASE)
SCOPE_LABEL_RE = re.compile(r"^Scope:\s*", re.IGNORECASE)


def strip_title_subtitle(title):
    """Drop a ' · <subtitle>' suffix from a job title (see module docstring)."""
    return TITLE_SUBTITLE_RE.sub("", title).strip()


def is_remote_location(location):
    return location.strip().lower().startswith("remote")


class Builder:
    def __init__(self):
        self.blocks = []
        self.notes = []

    def emit(self, text):
        text = text.strip()
        if text:
            self.blocks.append(text)

    def emit_bullets(self, items):
        items = [i for i in items if i.strip()]
        if items:
            self.blocks.append("\n".join(f"- {i}" for i in items))

    def note(self, msg):
        self.notes.append(msg)

    def render(self):
        return "\n\n".join(self.blocks) + "\n"


def flush_block_lines(b, lines):
    """Process a run of generic body lines: group into paragraphs and bullet lists."""
    para_buf = []
    bullets = []

    def flush():
        if para_buf:
            b.emit(" ".join(para_buf))
            para_buf.clear()
        if bullets:
            b.emit_bullets(bullets)
            bullets.clear()

    for raw in lines:
        s = raw.strip()
        if s == "":
            flush()
            continue
        if s.startswith("#"):
            continue  # stray heading inside a body block; not expected, skip defensively
        m = re.match(r"^[-*]\s+(.*)$", s)
        if m:
            if para_buf:
                b.emit(" ".join(para_buf))
                para_buf.clear()
            bullets.append(plain(m.group(1)))
        else:
            if bullets:
                b.emit_bullets(bullets)
                bullets.clear()
            para_buf.append(plain(s))
    flush()


def process_job_entries(b, lines, is_education):
    entries = []
    current = None
    for ln in lines:
        if ln.startswith("### "):
            if current is not None:
                entries.append(current)
            current = [ln]
        elif current is not None:
            current.append(ln)
        # content before the first "### " in an experience/education section is unexpected;
        # drop silently (none observed in the house-style templates this targets).
    if current is not None:
        entries.append(current)

    for entry in entries:
        raw_title = plain(entry[0][4:].strip())
        title = strip_title_subtitle(raw_title)
        rest = entry[1:]
        while rest and rest[0].strip() == "":
            rest.pop(0)

        has_h4 = bool(rest) and rest[0].strip().startswith("#### ")
        if not has_h4:
            # No parseable "#### Company | Dates | Location" line (e.g. "Earlier Career
            # (2001 - 2014)", a prose paragraph, not a job). Workday has no way to represent
            # this as anything but a blank job entry, so drop it. See module docstring.
            b.note(f"Entry '{title}' has no '#### Company | Dates | Location' line; "
                   f"dropped from the Workday render (not a parseable job).")
            continue

        h4 = rest[0].strip()[5:].strip()
        rest.pop(0)
        parts = [p.strip() for p in h4.split("|")]
        b.emit(title)
        if is_education:
            if len(parts) >= 1 and parts[0]:
                b.emit(plain(parts[0]))
            if len(parts) >= 2 and parts[1]:
                date = normalize_date(parts[1])
                if re.fullmatch(r"\d{4}(\s*-\s*\d{4})?", date.strip()):
                    b.note(f"Education date '{date}' has no month in the source; left as-is.")
                b.emit(date)
        else:
            company = plain(parts[0]) if len(parts) >= 1 else ""
            date = normalize_date(parts[1]) if len(parts) >= 2 else ""
            location = plain(parts[2]) if len(parts) >= 3 else ""
            if SELF_EMPLOYED_TITLE_RE.search(raw_title):
                # Narrow rule: an "Independent"/"Consultant" title's source company text is a
                # descriptive phrase (e.g. "Client engagements"), not an org name, and Workday
                # parsed it as a second title/company pair. See module docstring.
                company = "Self-employed"
            if company:
                b.emit(company)
            if location and not is_remote_location(location):
                b.emit(location)
            if date:
                if re.fullmatch(r"\d{4}\s*-\s*\d{4}", date.strip()):
                    b.note(
                        f"Job '{title}' at '{company}' has a year-only date range "
                        f"('{date}') in the source; left as-is (no month to expand)."
                    )
                b.emit(date)

        while rest and rest[0].strip() == "":
            rest.pop(0)

        if rest and re.match(r"^\*\s*Scope\b", rest[0].strip(), re.IGNORECASE):
            scope_line = rest.pop(0)
            scope_text = plain(scope_line.strip())
            scope_text = SCOPE_LABEL_RE.sub("", scope_text)
            b.emit(scope_text)
            while rest and rest[0].strip() == "":
                rest.pop(0)

        flush_block_lines(b, rest)


def convert(text):
    b = Builder()
    lines = text.split("\n")
    n = len(lines)
    i = 0

    if not (i < n and lines[i].startswith("# ")):
        raise ValueError("Expected résumé to start with a top-level '# Name' heading.")
    name = plain(lines[i][2:].strip())
    contact = [name]
    i += 1
    while i < n and lines[i].strip() == "":
        i += 1

    if i < n and lines[i].startswith("## "):
        contact.append(plain(lines[i][3:].strip()))
        i += 1
        while i < n and lines[i].strip() == "":
            i += 1

    while i < n and lines[i].strip() != "" and not lines[i].startswith("#"):
        for part in re.split(r"<br\s*/?>", lines[i]):
            part = part.strip()
            if part:
                contact.append(plain(part))
        i += 1

    for c in contact:
        b.emit(c)

    # Sections are rendered into per-section builders, then stitched onto the main builder in
    # the fixed KEPT_SECTIONS order below (the source order of sections in resume.md, e.g.
    # Education after Skills, doesn't match the Workday output order the brief specifies).
    rendered_sections = {}

    while i < n:
        if lines[i].strip() == "":
            i += 1
            continue
        m = re.match(r"^##\s+(.*)$", lines[i])
        if not m:
            i += 1
            continue
        section_name = map_section_name(m.group(1))
        i += 1

        section_lines = []
        while i < n and not re.match(r"^##\s+", lines[i]):
            section_lines.append(lines[i])
            i += 1

        if section_name not in KEPT_SECTIONS:
            # Not a job/education/skills section (e.g. "Open Source Projects",
            # "Recommendations"): no per-entry Company/Dates structure Workday can parse.
            # Dropped from this render. See module docstring.
            b.note(f"Section '{section_name}' has no job/dates structure Workday can parse; "
                   f"dropped from the Workday render.")
            continue

        sb = Builder()
        sb.emit(f"# {section_name}")
        if section_name in ("Experience", "Education"):
            process_job_entries(sb, section_lines, is_education=(section_name == "Education"))
        else:
            flush_block_lines(sb, section_lines)
        rendered_sections[section_name] = sb.blocks
        b.notes.extend(sb.notes)

    for section_name in KEPT_SECTIONS:
        b.blocks.extend(rendered_sections.get(section_name, []))

    return b.render(), b.notes


def main():
    if len(sys.argv) != 3:
        print("Usage: resume_to_workday_md.py <input.md> <output.workday.md>", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        text = f.read()
    out, notes = convert(text)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(out)
    for note in notes:
        print(f"NOTE: {note}", file=sys.stderr)


if __name__ == "__main__":
    main()

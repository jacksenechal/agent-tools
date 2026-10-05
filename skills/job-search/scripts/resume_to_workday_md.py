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

Rules learned from a second live Workday "Autofill with Resume" test (2026-10-05):
  - Workday's Education "Degree" dropdown only matches full degree names ("Bachelor of Arts"),
    not house-style abbreviations ("BA"). An Education entry's degree title (e.g. "BA in
    Mathematics, minor in Computer Science") is now split into separate lines: the expanded
    degree name, the field of study, and "Minor in <X>" if present, each its own line, followed
    by the school line and the year line. Abbreviations expanded: BA, BS, MA, MS, MBA, PhD. An
    unrecognized abbreviation falls back to emitting the original title line unchanged (see
    expand_degree_lines).
  - Workday's structured Skills field wants individual skills, not the house-style categorized
    bullets ("Languages & Frameworks: Python, TypeScript, ..."). The Skills section is now
    flattened into one comma-separated paragraph of the individual skills with the category
    labels dropped and duplicates removed (case-insensitive), in source order (see
    process_skills_section).

Rules learned from a third live Workday "Autofill with Resume" test (2026-10-05). This docx
exists only to drive the parser (see the "safe for the end recruiter" note below), so wording
chosen purely for parser behavior is fine even if it wouldn't be on the real résumé:
  - The Independent Consultant entry's forced Company (see the "Self-employed" rule further
    below) is now "Senechal Consulting" instead of "Self-employed": Jack's direction is that this
    reads as an actual org name to the parser rather than a status word. The title stays
    "Independent Consultant". Updated again 2026-10-05: forced Company changed to "Freelance"
    (Jack's preferred value; falls back to "Senechal Consulting" if Workday drops or mis-parses
    "Freelance").
  - The Education entry's school name "University of North Carolina at Asheville" is rendered as
    "University of North Carolina Asheville" (no "at"): Workday's School field didn't match the
    "at Asheville" form against its lookup. See SCHOOL_NAME_OVERRIDES — narrow, exact-match
    substitution, not a general "at" stripper.

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
    insensitive), the Company field is forced to a fixed value (see the third-test note above for
    its current text, "Senechal Consulting") regardless of what the source's
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
SELF_EMPLOYED_COMPANY = "Freelance"
SCOPE_LABEL_RE = re.compile(r"^Scope:\s*", re.IGNORECASE)

# Narrow, exact-match school-name overrides learned from a live Workday parser test (see module
# docstring): Workday's School field didn't match "University of North Carolina at Asheville"
# against its lookup, so it's rendered without "at". Not a general "at"-stripping rule.
SCHOOL_NAME_OVERRIDES = {
    "University of North Carolina at Asheville": "University of North Carolina Asheville",
}

DEGREE_EXPANSIONS = {
    "BA": "Bachelor of Arts",
    "BS": "Bachelor of Science",
    "MA": "Master of Arts",
    "MS": "Master of Science",
    "MBA": "Master of Business Administration",
    "PHD": "Doctor of Philosophy",
}
DEGREE_TITLE_RE = re.compile(
    r"^\s*([A-Za-z.]+)\s*(?:in\s+(.+?))?\s*(?:,\s*minor\s+in\s+(.+?))?\s*$",
    re.IGNORECASE,
)


def expand_degree_lines(raw_title):
    """Parse a degree title like 'BA in Mathematics, minor in Computer Science' into
    separate lines: the full degree name, the field of study, and 'Minor in <X>' (each
    omitted if absent). Returns None if the leading token isn't a recognized abbreviation,
    so the caller falls back to emitting the original title unchanged."""
    m = DEGREE_TITLE_RE.match(raw_title)
    if not m:
        return None
    abbr_key = m.group(1).replace(".", "").upper()
    full = DEGREE_EXPANSIONS.get(abbr_key)
    if not full:
        return None
    lines = [full]
    field, minor = m.group(2), m.group(3)
    if field:
        lines.append(plain(field))
    if minor:
        lines.append(f"Minor in {plain(minor)}")
    return lines


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


SKILLS_LABEL_RE = re.compile(r"^\*\*([^*]+)\*\*:\s*")


def process_skills_section(b, lines, style="flat"):
    """Render the Skills section either as one flattened comma-separated paragraph (style
    "flat", the default: house-style categorized skill bullets '- **Label**: a, b, c.' with
    category labels dropped, duplicates removed case-insensitively, in source order — this is
    what Workday's structured Skills field wants, see module docstring), or, for style
    "categorized", as the source's own categorized lines rendered as plain "Label: a, b, c"
    paragraphs (no Word list, no bold) — kept distinct per category rather than merged into one
    paragraph, for cases where the categorization itself should remain visible/parseable."""
    if style == "categorized":
        for raw in lines:
            s = raw.strip()
            m = re.match(r"^[-*]\s+(.*)$", s)
            if not m:
                continue
            item_text = m.group(1)
            label_m = SKILLS_LABEL_RE.match(item_text)
            if label_m:
                label = plain(label_m.group(1))
                rest = plain(SKILLS_LABEL_RE.sub("", item_text)).rstrip(".")
                b.emit(f"{label}: {rest}")
            else:
                b.emit(plain(item_text).rstrip("."))
        return

    items = []
    seen = set()
    for raw in lines:
        s = raw.strip()
        m = re.match(r"^[-*]\s+(.*)$", s)
        if not m:
            continue
        text = SKILLS_LABEL_RE.sub("", m.group(1))
        text = plain(text).rstrip(".")
        for item in text.split(","):
            item = item.strip()
            if not item:
                continue
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
    if items:
        b.emit(", ".join(items))


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
        if is_education:
            degree_lines = expand_degree_lines(title)
            if degree_lines:
                for dl in degree_lines:
                    b.emit(dl)
            else:
                b.emit(title)
        else:
            b.emit(title)
        if is_education:
            if len(parts) >= 1 and parts[0]:
                school = plain(parts[0])
                school = SCHOOL_NAME_OVERRIDES.get(school, school)
                b.emit(school)
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
                company = SELF_EMPLOYED_COMPANY
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


def convert(text, skills_style="flat"):
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
        elif section_name == "Skills":
            process_skills_section(sb, section_lines, style=skills_style)
        else:
            flush_block_lines(sb, section_lines)
        rendered_sections[section_name] = sb.blocks
        b.notes.extend(sb.notes)

    for section_name in KEPT_SECTIONS:
        b.blocks.extend(rendered_sections.get(section_name, []))

    return b.render(), b.notes


def main():
    args = sys.argv[1:]
    skills_style = "flat"
    if "--skills-style" in args:
        idx = args.index("--skills-style")
        try:
            skills_style = args[idx + 1]
        except IndexError:
            print("Error: --skills-style requires a value (flat|categorized)", file=sys.stderr)
            sys.exit(1)
        del args[idx:idx + 2]
    if skills_style not in ("flat", "categorized"):
        print(f"Error: --skills-style must be 'flat' or 'categorized', got '{skills_style}'",
              file=sys.stderr)
        sys.exit(1)
    if len(args) != 2:
        print("Usage: resume_to_workday_md.py <input.md> <output.workday.md> "
              "[--skills-style flat|categorized]", file=sys.stderr)
        sys.exit(1)
    with open(args[0], encoding="utf-8") as f:
        text = f.read()
    out, notes = convert(text, skills_style=skills_style)
    with open(args[1], "w", encoding="utf-8") as f:
        f.write(out)
    for note in notes:
        print(f"NOTE: {note}", file=sys.stderr)


if __name__ == "__main__":
    main()

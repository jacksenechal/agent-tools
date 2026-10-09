# Workday Application Playbook

Validated end-to-end 2026-10-05 against one Workday tenant (test posting,
stopped at Review, never submitted). Packed runbook, not a session log — see `make_resume_workday.sh`'s
module docstring for the full parser-quirk history.

## Stop-at-Review rule

**NEVER click Submit.** Every run — test or real — stops at the Review step. Fill everything,
leave the draft, tell the user it's ready. The user clicks Submit. This is absolute; it is not
conditional on "looks done" or "test mode."

## Setup

- Golden `playwright-golden` MCP session, signed in to the target tenant. Confirm with a
  `browser_snapshot` before starting — if signed out, stop and tell the user (they sign in via
  `http://localhost:6080/vnc.html`; never enter credentials yourself).
- File uploads: see `playwright-docker` skill's "File uploads" section for the current allowed
  path. As of 2026-10-05 the jobs and resume repos are bind-mounted at their identical host
  paths, so `browser_file_upload` works directly from `$JOBS_DIR/...` and
  `$RESUME_DIR/...` paths. If a path gets rejected as "outside allowed roots" or comes
  back `ENOENT`, re-read that section before improvising — it explains which of the two layers
  (harness allowlist vs. container filesystem) is actually failing, and the first fallback is
  `/tmp/.playwright-mcp-golden/` (always allowed; `docker cp` a file there, upload from there).

## Starting a fresh application

1. Go to Candidate Home. If a draft already exists for the target req, delete it first
   (`Related Actions` → `Delete Application` → confirm) **unless the user asked to continue an
   existing draft**. A reopened draft ("Continue Application") skips the Autofill step entirely —
   see "Recovery" below.
2. Navigate to the job posting, click **Apply**, then **Autofill with Resume** (not "Apply
   Manually" or "Use My Last Application" — those skip the parse this playbook depends on).
3. Render the parser-shaped `.docx`, passing the cell phone, education start year, and website
   link from `profile.md` so the docx doesn't need manual fixing after upload:
   ```bash
   <skill-dir>/scripts/make_resume_workday.sh <resume.md> \
     --name "<Your Name>" \
     --phone "<cell from profile.md>" \
     --edu-start <year from profile.md> \
     --link <website from profile.md>
   ```
4. Upload it on the Autofill screen, click **Continue**. Autofill only runs once per fresh
   application — see "Recovery" for how to redo it within the same session.

## Per-page checklist

**My Information**
- Legal name parses to the *preferred* name in both Legal and Preferred fields (e.g. both show
  the preferred name). Fix the Legal First Name back to the legal name — tick stays on "I have a preferred name."
- Phone defaults to whatever's in the docx. As of 2026-10-05 the standard render invocation
  (step 3) passes `--phone` with the cell already, so this should come in correct; if it still
  shows the public Google Voice number (e.g. the docx was rendered without `--phone`), overwrite
  with the cell per `profile.md`'s phone policy.
- Address Line 1 and Postal Code are often left blank by autofill; fill from `profile.md`.
- "How Did You Hear About Us": the employer's own corporate-site option, unless the tracker row
  has a confirmed referral (then "Referral"/"Employee Referral").

**My Experience**
- Confirms 6 jobs + education parse correctly from a current `resume.md`.
- **Fixed 2026-10-05**: Workday has no Summary field, and autofill was dumping the résumé's
  Summary text into the first job's (consulting entry's) Role Description. `resume_to_workday_md.py`
  now drops the Summary section from the Workday render entirely by default (`--keep-summary` to
  restore it for a tenant retest). If Role Description ever starts with Summary-sounding prose
  instead of the job's own scope/bullets, re-render with a current script version.
- Known residue: the consulting entry's Job Title parses as "Consultant" — fix to "Independent
  Consultant." Its Company renders correctly when `profile.md` has a "Consulting company" row
  with an org-style name such as "<Surname> Consulting" (read by `self_employed_company()` in
  `resume_to_workday_md.py`). "Freelance" was tried 2026-10-05 and came
  back with Company **blank** on this tenant (confirming an earlier plain-PDF test); reverted. If
  it comes up again, test it fresh — don't assume it's fixed without a live check.
- **New finding (2026-10-05): Workday's free-text fields (confirmed on Role Description) reject
  straight `" \ < > [ ] { }` characters outright** ("Contains illegal characters...") and block
  Save and Continue with a field-level error until fixed. `resume_to_workday_md.py`'s `plain()`
  now strips these automatically, so a fresh render is clean — but if you ever hand-edit text
  into one of these fields (or paste from elsewhere), re-check for straight quotes before saving.
- Skills: autofill **never** populates this field, and behavior is **tenant-dependent**.
  - Tenant A (wd5): the type-ahead picker returned "No Items." for every query tried,
    including common terms (Python, Kubernetes, Leadership, Java) and even a bare single letter
    ("a") — broken on this tenant, not the terms.
  - Tenant B (wd12): a "Skills and Strengths (Optional)" chip field shows ~15 "(Suggested)"
    skills inferred from the uploaded résumé (seen with the styled PDF), but the field caps at
    10. Prune to the 10 most relevant to the posting — keep the job's core stack and leadership
    terms, drop generic ones ("Mobile Applications," "Computer Programming") when off-target.
  - General procedure: if suggestions appear, prune to 10. If none appear and the picker works,
    type up to 10 terms from the résumé's Skills section that match the posting. If the picker
    is dead (tenant A-style), leave it blank and move on — don't burn turns on variations.
  - **Untested**: whether the parser-shaped `.docx` also triggers tenant B-style suggestions
    (likely, since they're inferred from text). Never re-upload the styled PDF after the docx —
    it re-runs autofill and overwrites the docx-parsed work history. The reverse order (PDF
    first for suggestions, then Back and docx) is also untested, and whether skill chips survive
    a re-parse is unknown. Verify both on the next real application on a suggestion-capable
    tenant.
- Swap the attachment: delete the autofill `.docx`, upload the styled, named PDF
  (`applications/<id>/Resume - <Name> - <Role>.pdf`) in its place. The docx only existed to
  drive the parse; the recruiter should see the real résumé.
- Minor field: there isn't one. A "minor in X" from the résumé has nowhere to go; drop it
  silently (it's already folded into the Field of Study handling upstream).
- School name: a formal "University of X at Y" may need the Workday form without "at" — a parser
  quirk, not a factual claim change; set it in `profile.md`'s "Workday school names" row (see
  `school_name_overrides` in the script).
- **Websites** and **Education "From" year**: as of 2026-10-05 the standard render invocation
  (step 3) emits contact URLs as real docx hyperlinks and prepends the education start year, so
  both fields should autofill. If either is still blank after autofill, the docx was likely
  rendered without `--link`/`--edu-start` — fill them manually from `profile.md` (website,
  and 1998 as the education start year) rather than leaving them empty.

**Application Questions**
- Answer everything `profile.md` covers directly (work authorization, prior-employer check →
  No, age 18+ → Yes, relatives-at-company → No, employment type → check "Full time").
- State-of-residence question: match the address state.
- Desired start date, "does the posted salary range align," and willing to relocate without
  assistance: answer from `profile.md`'s standing answers (one to two weeks out or the first of
  next month; Yes; No). For anything else Workday **requires** to proceed past this page that
  `profile.md` doesn't cover, stop and ask rather than guessing. On a *test* run whose only
  purpose is validating the flow, a clearly-labeled placeholder is fine to get to Review — call
  it out plainly in the report, don't let it read as a real answer.
- Optional fields (languages spoken, licenses/certifications, willing to travel): leave blank
  unless `profile.md` has an answer; these are rarely load-bearing.

**Voluntary Disclosures**
- EEO block maps directly from `profile.md`: gender, ethnicity (answer the "Hispanic or Latino?"
  sub-question consistently with the ethnicity answer), veteran status.
- Check the terms-and-conditions consent box; it's required to proceed.

**Self Identify**
- Form CC-305 (disability self-ID). Use the standing answer in `profile.md`; don't default to "I
  do not want to answer" unless that is what `profile.md` says.
- Name and Date fields on this form are required despite no visible asterisk until the
  validation error fires — fill Name (legal name) and today's date.
- The two disability-answer checkboxes besides the one you want are `disabled` while another is
  checked; click the currently-checked one to uncheck it, which re-enables the others, then
  click the one you want.

**Review**
- Read every section back. Confirm the Company fix, the attachment swap, and the My Experience
  text sanitization landed (illegal-character errors surface retroactively on Save and Continue,
  not live as you type).
- Stop. Do not click Submit.

## Recovery

- **Within the same session, before saving My Experience**: the in-form **Back** button returns
  to the Autofill screen; re-uploading a `.docx` there replaces the previous parse cleanly. Used
  this 2026-10-05 to fix a wrong disability answer discovered after reaching Review — Back
  through each step to Self Identify, no "Discard Application?" prompt as long as you're backing
  up within the still-unsaved draft.
- **Reopening a saved draft** ("Continue Application" from Candidate Home) skips Autofill
  entirely — you land straight on My Information with whatever was last saved. Hitting Back from
  there raises "Discard Application?" — a real confirm dialog, not a no-op.
- **Starting over**: delete the draft from Candidate Home (`Related Actions` → `Delete
  Application` → confirm) and begin again from Apply.

## Gotchas index (quick reference)

| Symptom | Cause | Fix |
|---|---|---|
| Legal first name shows preferred name | Autofill doesn't distinguish legal/preferred | Manually correct Legal First Name |
| Phone shows public number | docx carries whatever `resume.md` lists | Overwrite with cell from `profile.md` |
| Company blank for consulting entry | "Freelance" doesn't survive Workday's parse on this tenant | Add a "Consulting company" row to `profile.md` with an org-style name ("<Surname> Consulting") |
| Job title "Consultant" | Parser drops "Independent" | Manually fix to "Independent Consultant" |
| Save and Continue blocked, "illegal characters" error | Straight `" \ < > [ ] { }` in a free-text field | `resume_to_workday_md.py`'s `plain()` strips these now; re-render if editing by hand |
| Skills type-ahead returns "No Items." for everything | Tenant's skill-cloud lookup may be non-functional (seen on tenant A) | Try 2-3 terms, then leave blank — don't loop |
| Skills chip field shows ~15 "(Suggested)" skills, caps at 10 | Tenant infers skills from uploaded résumé text (seen on tenant B) | Prune to the 10 most relevant to the posting |
| Required field has no visible `*` until you try to save | Asterisk sometimes only renders after a validation pass | Expect this on Self Identify's Name/Date |
| `browser_file_upload` says "outside allowed roots" or `ENOENT` | Harness-allowlist vs. container-filesystem path mismatch | See `playwright-docker` skill's "File uploads" section |
| Websites field empty after autofill | docx had no hyperlinks (markdown links were stripped to plain text) or LinkedIn URL lacked "www." | Render with `--link`/profile.md's website; LinkedIn is auto-normalized to `www.linkedin.com` by `resume_to_workday_md.py` |
| Education "From" year blank | No start year in the source date line (e.g. "May 2003" alone) | Render with `--edu-start <year>` |

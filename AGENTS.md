# AGENTS.md — agent-tools

Guidance for agents working anywhere in this repo.

## This is a public, general-purpose repo — no personal data

`agent-tools` (skills, scripts, assets, docs) is meant to be general-purpose and shareable. It
must contain **no personally identifiable information (PII)** and no user-specific details:

- No names, emails, phone numbers, addresses, LinkedIn/GitHub handles, employer names, or other
  personal facts — not in SKILL.md files, not in scripts, not in assets, not in comments or
  example commands.
- Scripts must take personal values at runtime: a flag (e.g. `--name`), an environment variable
  (e.g. `$JOB_SEARCH_APPLICANT_NAME`), or by reading a file in the user's **private** repo. Do
  not hardcode a default that embeds a real person.
- In docs and examples, use placeholders (`<Your Name>`, `<Company>`, `<Role>`) rather than real
  values.
- Refer to the person a skill works for as **"the user"** (pronouns they/them), never by name.
  Strings the code writes or parses (tracker note markers, brief headings) are generic too
  (e.g. `LIVENESS: needs user <date>`, `## Needs you`).

**Where personal details live:** the user's private repos (for the job-search skill, that's the
jobs repo, `$JOBS_DIR`, including `profile.md`). Read from there at runtime; never copy into
this repo.

If you catch existing PII in this repo, treat it as a bug and remove/genericize it.

## No hard-coded paths

Skills here run on other people's machines, in cloud sessions, and in containers, where nothing
lives where it does on the author's machine. **Never hard-code a machine-specific path**: no
fixed workspace layout under the home directory, no specific user's home directory, no assumed
location for this repo, a skill, or a user's repos. This applies to scripts, assets (systemd
units, compose files), SKILL.md files, references, examples, and comments alike. Hard-coded
paths have crept back in before; do not reintroduce them.

Resolve locations at run time instead:

- **A skill's own files**: from the script's location (`$(dirname "${BASH_SOURCE[0]}")`,
  `os.path.dirname(__file__)`). In docs, write `<skill-dir>/...` and say it means the skill's
  base directory.
- **The user's repos and data**: an environment variable, then a config file under
  `${XDG_CONFIG_HOME:-~/.config}/<skill>/`, then discovery from the current directory. For
  job-search that is `skills/job-search/scripts/paths.sh` (`jobsearch_paths.py` for Python),
  documented in its SKILL.md under "Project Locations"; extend it rather than adding a path
  inline. In docs, write `$JOBS_DIR`, `$RESUME_DIR`, `$SITE_DIR`.
- **Installed artifacts** (systemd units and the like): templates with placeholders the
  installer fills in, e.g. `@SKILL_DIR@`.

Container-internal paths (`/home/pwuser`, `/home/node`, `/home/arcadedb`) are fine: they are
fixed by the image, not by a user's machine.

`scripts/check_no_hardcoded_paths.sh` enforces this. Run it before committing; enable it as a
pre-commit hook with `git config core.hooksPath .githooks`. Fix a finding at its source; never
add an allowlist entry to make it pass. `archive/` is exempt (retired, unmaintained).

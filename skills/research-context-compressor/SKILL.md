---
name: research-context-compressor
description: Inspect a research repository and write a compact `.research/` workspace manifest (project_manifest.yml, experiment_matrix.yml, data_dictionary.yml) so future AI sessions can orient themselves without rescanning the whole repo. Use when the user asks to "compress this project context", "create a research manifest", or "save the project context for future agents".
---

# research-context-compressor

Build a compact, machine-readable workspace memory at the **project root**
under `.research/`. Other research-hub skills (project-orienter,
literature-triage-matrix, paper-memory-builder) read these files instead of
rescanning the repo every session, which is where the token savings come from.

This is the **foundation** skill. Run it once per project and refresh when
the project's research question, datasets, or experiment set changes.

## When to use

Trigger phrases:

- "Compress this project context for future agents."
- "Create a research manifest so future sessions don't reread everything."
- "Save the key project context before we continue."
- "Build a `.research/` folder for this repo."

Not for:

- Compressing source code or generating doc strings — that's a code task.
- Running experiments or analyzing results — those write to `outputs/`,
  not `.research/`.
- Writing the manuscript itself.

## Inputs you should read (whichever exist — priority order)

The compressor reads whatever your project has. **None of these are
required.** If a file is missing, that field of the manifest stays
empty (see "What NOT to do").

**For any project**:

1. `README.md` at the repo root — project overview.

**For code-based research projects** (Python / JS / R / Julia / etc.):

2. `pyproject.toml` / `package.json` / `requirements.txt` /
   `renv.lock` / `Project.toml` — primary tools.
3. `scripts/` and `notebooks/` — main entrypoints.
4. `data/` and `outputs/` — datasets and artifacts.

**For qualitative / archival / interpretive projects**:

2. `notes/`, `drafts/`, `sources/` — manuscript-track work.
3. `.obsidian/` — Obsidian vault settings, if present.
4. Any plain-text bibliography file (`bibliography.md`, `sources.bib`,
   `references.json`).

**For both**:

5. `docs/` — long-form descriptions.
6. `.git/HEAD` and `git log --oneline -20` — current branch + recent
   activity, if a git repo.
7. `.research/` (if it already exists) — for refresh, not first-time
   create.

**An empty manifest field is better than an invented one.**

## Outputs you must produce

Write these to `<project-root>/.research/`:

- `project_manifest.yml` — top-level orientation. **Required.**
- `experiment_matrix.yml` — per-experiment status. **Required if `scripts/` or `notebooks/` exist.**
- `data_dictionary.yml` — datasets and schemas. **Required if `data/` exists.**
- `run_log.md` — append a single entry recording this run.
- `decisions.md` — leave empty if no ADRs yet; do not invent decisions.
- `open_questions.md` — list any obvious unknowns you spotted.

If a file already exists, **update don't replace**: keep human-edited
fields, fill in only the empty ones unless the user said "regenerate from
scratch".

## Schema reference

Quick reminder of `project_manifest.yml` required fields:

- `project_name`
- `research_area`
- `research_question`
- `current_stage` (one of `discovery / exploration / experiments / writing / rebuttal / submission`)
- `last_updated` (today's date in ISO format)

If you don't know a field, leave it empty (`""` or `[]`). Do **not** guess
research questions, hypotheses, or claims.

## What NOT to do

- Don't write to `.paper/` — that's `paper-memory-builder`'s job.
- Don't write `.research/literature_matrix.md` — that's
  `literature-triage-matrix`'s job.
- Don't invent fields not in the schema. Add a line to
  `.research/open_questions.md` instead.
- Don't overclaim: if the project has no clear research question yet, leave
  `research_question` empty and add a question to `open_questions.md`.
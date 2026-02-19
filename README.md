# Crossref Citation Check Example Repo

This repository demonstrates how to use the `$crossref-citation-check` skill to validate academic references against Crossref metadata.

Skill file:
- `C:\Users\KMK\.codex\skills\crossref-citation-check\SKILL.md`

## What This Skill Does

The skill checks reference fields against Crossref and reports:
- citation-level status: `match_found`, `no_likely_match`, `no_match`
- field-level comparisons for title, authors, journal, volume, issue, pages, year, DOI, URL
- corrected metadata values when mismatches are found

## Supported Input Formats

You can pass references in:
- JSON (`.json`)
- CSV (`.csv`)
- free text (`.txt`, `.md`)
- LaTeX bibliography files (`.tex`, `.bib`, including `\bibitem{...}`)

## Prerequisites

- Python 3 installed
- Internet access (Crossref REST API lookup)

## Core Command

Run the helper script from the skill directory:

```powershell
python C:\Users\KMK\.codex\skills\crossref-citation-check\crossref_checker.py -i <input-file> -o <output-file>
```

Optional flags:
- `-e you@example.com` adds a polite contact email in User-Agent
- `--title-threshold 0.90` increases strictness for title-based matching

## Example Commands (Using This Repo)

```powershell
# JSON input
python C:\Users\KMK\.codex\skills\crossref-citation-check\crossref_checker.py -i citations.json -o refs_results.json -e you@example.com

# CSV input
python C:\Users\KMK\.codex\skills\crossref-citation-check\crossref_checker.py -i citations.csv -o refs_results.json -e you@example.com

# Free-text input
python C:\Users\KMK\.codex\skills\crossref-citation-check\crossref_checker.py -i refs.txt -o refs_results.json -e you@example.com

# LaTeX bibliography input
python C:\Users\KMK\.codex\skills\crossref-citation-check\crossref_checker.py -i bib.tex -o refs_results.json -e you@example.com
```

## How to Read Results

Output is a JSON array. Each item includes:
- `article`: parsed/provided citation
- `status`: overall match result
- `matched_by`: `doi` or `title` (when matched)
- `title_score`: confidence for title-based matching
- `comparison`: field-by-field validation for matched records
- `error`: reason when no reliable match is found

Interpretation:
- `match_found`: Crossref match accepted; inspect `comparison` for field corrections
- `no_likely_match`: nearest result is below confidence threshold; treat as unresolved
- `no_match`: no usable candidate returned

## Recommended Workflow for Academic Reference Checks

1. Prepare references in one of the supported formats.
2. Run `crossref_checker.py` with `-o` to save a report.
3. For `match_found`, update bibliography fields to Crossref values (especially DOI, year, volume/pages/article number).
4. For `no_likely_match` / `no_match`, manually verify using DOI, full title, and full author list.
5. Re-run until unresolved items are minimized.

## Notes

- DOI-based matching is most reliable; include DOI when possible.
- Free-text input works, but structured JSON/CSV usually gives cleaner parsing.
- If Crossref has no reliable record, keep the reference and annotate it as unresolved until manually confirmed.

## Download and Install (GitHub, VS Code Copilot Agent, ChatGPT Codex)

### 1. Download from GitHub

```powershell
git clone <YOUR_REPO_URL>
cd crossref-citation-check
```

Or use GitHub UI:
- Click `Code` -> `Download ZIP`
- Extract the ZIP and open the folder

### 2. Use with ChatGPT Codex Skills

Codex loads skills from your local skills directory:
- Windows: `C:\Users\<your-user>\.codex\skills\`

Copy this skill folder into that location:
- Source: `.github/skills/crossref-citation-check`
- Target: `C:\Users\<your-user>\.codex\skills\crossref-citation-check`

Required files in the target folder:
- `SKILL.md`
- `crossref_checker.py`

Then invoke in Codex by naming the skill in your prompt, for example:
- `Use $crossref-citation-check on bib.tex and report mismatches.`

### 3. Use with VS Code GitHub Copilot Agent

This repo already includes:
- `.github/skills/crossref-citation-check/`

Steps:
1. Open the repository in VS Code.
2. Sign in to GitHub Copilot.
3. Open Copilot Chat and switch to Agent mode.
4. Ask explicitly for skill usage, for example:
   - `Use the crossref-citation-check skill to validate refs.txt and produce corrected fields.`

### 4. Run Script Directly (Any Environment)

```powershell
python .github/skills/crossref-citation-check/crossref_checker.py -i bib.tex -o refs_results.json -e you@example.com
```

Replace `bib.tex` with any supported input:
- `refs.txt`
- `refs.md`
- `citations.csv`
- `citations.json`

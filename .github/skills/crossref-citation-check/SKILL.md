---
name: crossref-citation-check
description: >-
  Validate citations against Crossref with strict field-level misinformation
  detection and correction-ready output.
argument-hint: >-
  Path to citations input (JSON, CSV, TXT/MD free text, or LaTeX .tex/.bib)
  or a structured list of citation objects.
user-invokable: true
---
# Crossref Citation Check Skill (v2)

## Purpose

Assume any reference field can be incorrect or missing, validate against
Crossref, and return correction-ready output.

## Supported Inputs

- JSON citation arrays
- CSV with citation columns
- Free-text citation blocks (`.txt`, `.md`)
- LaTeX bibliography files (`.tex`, `.bib`, including `\bibitem{...}`)

## Required Invocation Behavior

When this skill is selected:

1. Must use local helper script in this folder:
   - `crossref_checker.py`
2. Script-first policy:
   - Always run script first.
   - Only use manual API fallback if script execution fails.
3. For text/LaTeX inputs, pass the file directly to the script.
4. Final response must include execution evidence:
   - exact command used
   - output file path
   - short summary/preview from output

## Script Usage

- `python crossref_checker.py -i citations.json`
- `python crossref_checker.py -i citations.csv -o results.json`
- `python crossref_checker.py -i refs.tex -o results.json`
- `python crossref_checker.py -i refs.txt -o results.json`
- `python crossref_checker.py -i refs.md --title-threshold 0.90`
- `python crossref_checker.py -i refs.txt --critical-fields title,doi,authors,journal,year`
- `python crossref_checker.py -i refs.txt --emit-corrected-reference true`

## Output Contract (v2)

Each citation result must include:

- `citation_id`
- `source_format` (`json` | `csv` | `txt` | `md` | `tex` | `bib`)
- `status` (`match_found` | `corrected` | `critical_mismatch` | `unresolved`)
- `matched_by` (`doi` | `title` | `none`)
- `confidence` (`title_score`, optional `candidate_rank`)
- `field_assessment` (per-field assessment object)
- `correction_patch` (`set`, `unset`)
- `corrected_reference` (`format`, `text`)
- `required_user_inputs` (for unresolved entries)
- `error` (when applicable)

### Field Assessment States

- `correct`
- `missing`
- `incorrect`
- `conflict`

### Critical Field Policy

Default critical fields:

- `title`
- `doi`
- `authors`
- `journal`
- `year`

If any critical field state is `conflict`, status must be `critical_mismatch`.

## Matching and Resolution Rules

- DOI lookup first when DOI exists.
- If DOI lookup fails and title exists, use title search with threshold.
- If no reliable match, return `unresolved` and required disambiguation inputs.
- Missing/incorrect fields in resolvable matches must produce `correction_patch`.

## Notes

- Use `-e` email when possible for polite API usage.
- Respect rate limits.
- Crossref remains authority for suggested corrected values.

## Reusable Enforcement Prompt Block

```text
Use $crossref-citation-check on <INPUT_FILE>.

Hard constraints:
1) You MUST run:
   python <SKILL_DIR>/crossref_checker.py -i <INPUT_FILE> -o <OUTPUT_FILE>
2) You MUST NOT call Crossref API directly unless this command fails.
3) If command fails, stop and report:
   - exact command attempted
   - exact error message
4) Before final answer, provide execution evidence:
   - exact command run
   - output file path
   - short preview/summary from <OUTPUT_FILE>
5) Return field-level corrections for incorrect/missing values.
```

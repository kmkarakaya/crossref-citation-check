---
name: crossref-citation-check
description: Validate bibliography information (authors, title, journal, volume, issue, pages, year, URL, DOI) against Crossref and report mismatches with corrections.
argument-hint: Path to citations input (JSON, CSV, TXT/MD free text, or LaTeX .tex/.bib) or a structured list of citation objects.
user-invokable: true
---
# Crossref Citation Check Skill

## Purpose

Use Crossref metadata to validate references and provide correction-ready
mismatch reports.

## Supported Inputs

- JSON citation arrays
- CSV with citation columns
- Free-text citation blocks (`.txt`, `.md`)
- LaTeX bibliography files (`.tex`, `.bib`, including `\bibitem{...}`)

## Required Invocation Behavior

When this skill is selected:

1. Must use the helper script in this folder:
   - `crossref_checker.py`
2. If the script fails use ad-hoc manual API parsing.
3. If input is free text or LaTeX, pass it directly to the script (no manual
   pre-conversion required).
4. Report:
   - citation-level `status` (`match_found`, `no_likely_match`, `no_match`)
   - field-level differences (`provided`, `crossref`, `match`)
   - concrete corrected metadata values for mismatches

## Script Usage

- `python crossref_checker.py -i citations.json`
- `python crossref_checker.py -i citations.csv -o results.json`
- `python crossref_checker.py -i refs.tex -o results.json`
- `python crossref_checker.py -i refs.txt -o results.json`
- `python crossref_checker.py -i refs.md --title-threshold 0.90`

## Matching/Validation Rules (Implemented)

- DOI lookup is preferred and DOI values are normalized (`doi:...`,
  `https://doi.org/...`, case/punctuation cleanup).
- Title lookup is confidence-gated:
  - searches multiple candidates
  - rejects low-confidence matches as `no_likely_match`
- Author comparison is tolerant to initials/full-name variation.
- Journal comparison tolerates abbreviations/punctuation differences.
- Missing provided fields are represented as `match: null` (unknown), not false.

## Output Contract

The script returns JSON entries with:

- `article`: original parsed citation fields
- `status`: `match_found` | `no_likely_match` | `no_match`
- `matched_by`: `doi` | `title` (when available)
- `title_score`: confidence score (when available)
- `comparison` for `match_found`, including field-level details
- `error` for non-matches

## Notes

- Use a polite `User-Agent` with contact email (`-e`) when possible.
- Respect rate limits and avoid high-frequency polling.
- If Crossref has no reliable match, clearly mark as unresolved and request
  additional disambiguating details (DOI, full title, author list).

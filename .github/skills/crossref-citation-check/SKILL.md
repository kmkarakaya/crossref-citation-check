---
name: crossref-citation-check
description: >-
  Validate citations against Crossref with strict field-level misinformation
  detection, multi-candidate DOI recovery, and correction-ready output.
argument-hint: >-
  Path to references input in plain text (`.txt`) or LaTeX bibliography
  (`.tex`/`.bib`).
user-invokable: true
---
# Crossref Citation Check Skill (v2.1)

## Purpose

Validate references assuming any field can be incorrect or missing.
If DOI is missing or suspect, recover candidate DOIs via ranked multi-candidate
search, and support user-guided final selection.

## Supported Inputs

- Plain-text references (`.txt`)
- LaTeX bibliography files (`.tex`, `.bib`, including `\bibitem{...}`)

## Required Invocation Behavior

When this skill is selected:

1. Must use local helper script in this folder:
   - `crossref_checker.py`
2. Script-first policy:
   - Always run script first.
   - Only use manual API fallback if script execution fails.
3. If any result has `selection_required=true`:
   - present top candidates (rank/title/authors/journal/year/DOI/composite score)
   - ask user to pick rank per `citation_id` (or confirm recommendation)
   - rerun script with `--selection-map`
4. Final response must include execution evidence:
   - exact command used
   - output file path
   - short summary/preview from output

## Script Usage

- First pass:
  - `python crossref_checker.py -i refs.txt -o refs_results.json`
  - `python crossref_checker.py -i bib.tex -o bib_results.json`
- Advanced v2.1 controls:
  - `python crossref_checker.py -i refs.txt --candidate-rows 6`
  - `python crossref_checker.py -i refs.txt --auto-accept-threshold 0.88 --ambiguity-gap-threshold 0.06`
  - `python crossref_checker.py -i refs.txt --shortlist-trigger missing_or_conflict`
- Apply user selections:
  - `python crossref_checker.py -i refs.txt --selection-map selection_map.json -o refs_results_final.json`
  - `selection_map.json` example: `{"paper:4": 2, "paper:7": 1}`

## Output Contract (v2.1, v2-compatible extension)

Each citation result includes existing v2 fields plus shortlist/selection
fields:

- `citation_id`
- `source_format`
- `status` (`match_found` | `corrected` | `critical_mismatch` | `unresolved`)
- `matched_by` (`doi` | `title` | `none`)
- `confidence`
- `field_assessment`
- `correction_patch` (`set`, `unset`)
- `corrected_reference`
- `required_user_inputs`
- `error` (when applicable)

Additional v2.1 fields:

- `candidate_matches` (0..N):
  - `rank`
  - `composite_score`
  - `component_scores` (`title`, `authors`, `journal`, `year`)
  - `doi`, `title`, `authors`, `journal`, `year`, `volume`, `issue`, `pages`, `url`
  - `matched_by_query` (`bibliographic`, `title`, `author_title`)
- `recommended_candidate_rank`
- `selection_required`
- `selection_reason` (`ambiguous_top2`, `low_confidence`, `doi_conflict_review`, `none`)
- `selected_candidate_rank`
- `doi_conflict`

## Matching and Resolution Rules

- DOI lookup first when DOI exists.
- Shortlist trigger defaults to `missing_or_conflict`.
- Candidate retrieval uses up to 3 query types:
  - `query.bibliographic` (title + first 2 authors + journal + year)
  - `query.title`
  - `query.author` + `query.title`
- Deduplicate candidates by DOI (fallback: normalized title+year).
- Composite rank uses weighted score:
  - title `0.55`
  - authors `0.30`
  - journal `0.10`
  - year `0.05`
- Auto-accept top candidate only if:
  - `top_score >= auto_accept_threshold`
  - `top_minus_second >= ambiguity_gap_threshold`
  - no DOI-conflict review requirement
- Otherwise require user selection.

## Notes

- Use `-e` email when possible for polite API usage.
- Respect rate limits.
- Crossref remains authority for suggested corrected values.

## Reusable Enforcement Prompt Block

```text
Use $crossref-citation-check on <INPUT_FILE>.

Hard constraints:
1) MUST run:
   python <SKILL_DIR>/crossref_checker.py -i <INPUT_FILE> -o <OUTPUT_FILE>
2) MUST NOT call Crossref API directly unless this command fails.
3) If output contains selection_required=true:
   - ask user for candidate rank by citation_id
   - rerun with --selection-map
4) Before final answer, provide execution evidence:
   - exact command run
   - output path
   - short summary from output
```

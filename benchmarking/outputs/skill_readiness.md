# Skill Readiness Report

- Overall ready: `False`
- Cases file: `C:\Codes\crossref-citation-check\benchmarking\readiness_cases.csv`
- Runs directory: `C:\Codes\crossref-citation-check\benchmarking\outputs\readiness_runs`
- Correction score source: `C:\Codes\crossref-citation-check\benchmarking\outputs\benchmark_score.json`

## Metrics

- Correction rate: `0.891892` (min `0.85`)
- Trigger precision: `1.0` (required `1.0`)
- Trigger recall: `0.0` (min `0.9`)
- Workflow compliance: `0.333333` (min `0.9`)
- Case count: `8`

## Hard Fails

- selection_required_tex: missing_required_selection_flow
- selection_required_txt: missing_required_selection_flow

## Per-Case Summary

| Case | Should Trigger | Did Trigger | Selection Flow Expected | Workflow Score | Failed Checks | Hard Fails |
|---|---:|---:|---:|---:|---|---|
| `positive_explicit_tex` | `True` | `False` | `False` | `0.25` | `['trigger_check', 'evidence_check', 'output_contract_check']` | `[]` |
| `positive_implicit_txt` | `True` | `False` | `False` | `0.25` | `['trigger_check', 'evidence_check', 'output_contract_check']` | `[]` |
| `positive_contextual_tex` | `True` | `False` | `False` | `0.25` | `['trigger_check', 'evidence_check', 'output_contract_check']` | `[]` |
| `negative_translate` | `False` | `False` | `False` | `1.0` | `[]` | `[]` |
| `negative_summarize` | `False` | `False` | `False` | `1.0` | `[]` | `[]` |
| `selection_required_tex` | `True` | `False` | `True` | `0.2` | `['trigger_check', 'selection_flow_check', 'evidence_check', 'output_contract_check']` | `['missing_required_selection_flow']` |
| `selection_required_txt` | `True` | `False` | `True` | `0.2` | `['trigger_check', 'selection_flow_check', 'evidence_check', 'output_contract_check']` | `['missing_required_selection_flow']` |
| `noisy_malformed_txt` | `True` | `False` | `False` | `0.25` | `['trigger_check', 'evidence_check', 'output_contract_check']` | `[]` |

## Failed Check Details

### `positive_explicit_tex`
- Failed checks: `['trigger_check', 'evidence_check', 'output_contract_check']`
- Hard fails: `[]`
- Contract errors: `['no_result_json_files']`

### `positive_implicit_txt`
- Failed checks: `['trigger_check', 'evidence_check', 'output_contract_check']`
- Hard fails: `[]`
- Contract errors: `['no_result_json_files']`

### `positive_contextual_tex`
- Failed checks: `['trigger_check', 'evidence_check', 'output_contract_check']`
- Hard fails: `[]`
- Contract errors: `['no_result_json_files']`

### `selection_required_tex`
- Failed checks: `['trigger_check', 'selection_flow_check', 'evidence_check', 'output_contract_check']`
- Hard fails: `['missing_required_selection_flow']`
- Contract errors: `['no_result_json_files']`
- Selection errors: `['missing_before_apply']`

### `selection_required_txt`
- Failed checks: `['trigger_check', 'selection_flow_check', 'evidence_check', 'output_contract_check']`
- Hard fails: `['missing_required_selection_flow']`
- Contract errors: `['no_result_json_files']`
- Selection errors: `['missing_before_apply']`

### `noisy_malformed_txt`
- Failed checks: `['trigger_check', 'evidence_check', 'output_contract_check']`
- Hard fails: `[]`
- Contract errors: `['no_result_json_files']`

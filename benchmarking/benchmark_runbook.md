# Benchmark Runbook

## Fast Path (One Command)

Run everything end-to-end (generate, first pass, selection maps, second pass, score):

```powershell
python benchmarking/run_benchmark.py --min-overall 0.80
```

Run with skill-readiness grading after score/report:

```powershell
python benchmarking/run_benchmark.py --min-overall 0.80 --readiness
```

Run with real chat-agent in the middle (script pauses for your manual prompt runs and resumes):

```powershell
python benchmarking/run_benchmark.py --mode agent-in-loop --min-overall 0.80
```

In `agent-in-loop` mode the script always pauses before first-pass and second-pass stages.
It waits for your Enter confirmation, then checks required output files exist.

Score-only mode (reuse existing `*_after_apply.json`):

```powershell
python benchmarking/run_benchmark.py --score-only --min-overall 0.80
```

## 1) Generate benchmark files from ground truth

Ground-truth files are now stored at:
- `benchmarking/outputs/inputs/groundtruth_bib.tex`
- `benchmarking/outputs/inputs/groundtruth_bib.txt`

```powershell
python benchmarking/benchmark_generate.py `
  --groundtruth-tex benchmarking/outputs/inputs/groundtruth_bib.tex `
  --groundtruth-txt benchmarking/outputs/inputs/groundtruth_bib.txt `
  --out-tex benchmarking/outputs/benchmark_bib.tex `
  --out-txt benchmarking/outputs/benchmark_bib.txt `
  --manifest benchmarking/outputs/benchmark_manifest.json
```

Expected outputs:
- `benchmarking/outputs/benchmark_bib.tex`
- `benchmarking/outputs/benchmark_bib.txt`
- `benchmarking/outputs/benchmark_manifest.json`

## 2) First-pass validation with skill

Use prompts from `benchmarking/benchmark_agent_prompts.md` to produce:
- `benchmarking/outputs/bib_results_before_apply.json`
- `benchmarking/outputs/refs_results_before_apply.json`

Each agent answer must include:
- exact command run
- output path
- short summary

## 3) Build deterministic selection maps

```powershell
python benchmarking/benchmark_make_selection_map.py -i benchmarking/outputs/bib_results_before_apply.json -o benchmarking/outputs/bib_selection_map.json
python benchmarking/benchmark_make_selection_map.py -i benchmarking/outputs/refs_results_before_apply.json -o benchmarking/outputs/refs_selection_map.json
```

Expected outputs:
- `benchmarking/outputs/bib_selection_map.json`
- `benchmarking/outputs/refs_selection_map.json`

## 4) Second-pass validation with selection maps

Use prompts from `benchmarking/benchmark_agent_prompts.md` to produce:
- `benchmarking/outputs/bib_results_after_apply.json`
- `benchmarking/outputs/refs_results_after_apply.json`

## 5) Score against ground truth

```powershell
python benchmarking/benchmark_score.py `
  --groundtruth-tex benchmarking/outputs/inputs/groundtruth_bib.tex `
  --groundtruth-txt benchmarking/outputs/inputs/groundtruth_bib.txt `
  --benchmark-tex benchmarking/outputs/benchmark_bib.tex `
  --benchmark-txt benchmarking/outputs/benchmark_bib.txt `
  --result-tex benchmarking/outputs/bib_results_after_apply.json `
  --result-txt benchmarking/outputs/refs_results_after_apply.json `
  --manifest benchmarking/outputs/benchmark_manifest.json `
  --output benchmarking/outputs/benchmark_score.json `
  --min-overall 0.80
```

Exit codes:
- `0`: pass
- `2`: below threshold
- `1`: invalid input/error

Expected output:
- `benchmarking/outputs/benchmark_score.json`
- Primary metric in score JSON: `overall.overall_correction_rate`
- Primary pass condition: `overall.overall_correction_rate >= threshold`
- Field-level correction counts:
  - `overall.total_targeted_wrong_fields`
  - `overall.total_fixed_fields`

## 6) Generate per-reference report

```powershell
python benchmarking/benchmark_report.py `
  --groundtruth-tex benchmarking/outputs/inputs/groundtruth_bib.tex `
  --groundtruth-txt benchmarking/outputs/inputs/groundtruth_bib.txt `
  --benchmark-tex benchmarking/outputs/benchmark_bib.tex `
  --benchmark-txt benchmarking/outputs/benchmark_bib.txt `
  --result-tex benchmarking/outputs/bib_results_after_apply.json `
  --result-txt benchmarking/outputs/refs_results_after_apply.json `
  --score-json benchmarking/outputs/benchmark_score.json `
  --output benchmarking/outputs/report.md
```

Expected output:
- `benchmarking/outputs/report.md`

## 7) Acceptance checks

```powershell
python -m unittest
```

## 8) Skill readiness grading (optional but recommended for shipping)

Create per-case run artifacts under:
- `benchmarking/outputs/readiness_runs/<case_id>/`

Each case folder should include:
- `response.md` (agent final response text)
- `commands.txt` (exact commands run, one per line)
- optional checker files:
  - `*_before_apply.json`
  - `*_selection_map.json`
  - `*_after_apply.json`

Case definitions:
- `benchmarking/readiness_cases.csv`

Run readiness grader:

```powershell
python benchmarking/benchmark_skill_readiness.py `
  --cases benchmarking/readiness_cases.csv `
  --runs-dir benchmarking/outputs/readiness_runs `
  --correction-score benchmarking/outputs/benchmark_score.json `
  --output benchmarking/outputs/skill_readiness.json `
  --report benchmarking/outputs/skill_readiness.md
```

Expected readiness outputs:
- `benchmarking/outputs/skill_readiness.json`
- `benchmarking/outputs/skill_readiness.md`

End-to-end run is complete when all of these exist:
- `benchmarking/outputs/inputs/groundtruth_bib.tex`
- `benchmarking/outputs/inputs/groundtruth_bib.txt`
- `benchmarking/outputs/benchmark_bib.tex`
- `benchmarking/outputs/benchmark_bib.txt`
- `benchmarking/outputs/bib_results_before_apply.json`
- `benchmarking/outputs/refs_results_before_apply.json`
- `benchmarking/outputs/bib_results_after_apply.json`
- `benchmarking/outputs/refs_results_after_apply.json`
- `benchmarking/outputs/benchmark_score.json`
- `benchmarking/outputs/report.md`
- `benchmarking/outputs/skill_readiness.json` (if readiness enabled)
- `benchmarking/outputs/skill_readiness.md` (if readiness enabled)

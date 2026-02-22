# Benchmark Runbook

## Fast Path (One Command)

Run everything end-to-end (generate, first pass, selection maps, second pass, score):

```powershell
python benchmarking/run_benchmark.py --min-overall 0.80
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
  --result-tex benchmarking/outputs/bib_results_after_apply.json `
  --result-txt benchmarking/outputs/refs_results_after_apply.json `
  --output benchmarking/outputs/benchmark_score.json `
  --min-overall 0.80
```

Exit codes:
- `0`: pass
- `2`: below threshold
- `1`: invalid input/error

Expected output:
- `benchmarking/outputs/benchmark_score.json`

## 6) Acceptance checks

```powershell
python -m unittest
```

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

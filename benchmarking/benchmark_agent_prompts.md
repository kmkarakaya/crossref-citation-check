# Benchmark Agent Prompts

Use these prompts exactly in agent chat for the benchmark workflow.

## First Pass (`.tex`)

```text
Use $crossref-citation-check on benchmarking/outputs/benchmark_bib.tex.

Hard constraints:
1) MUST run:
   python .github/skills/crossref-citation-check/crossref_checker.py -i benchmarking/outputs/benchmark_bib.tex -o benchmarking/outputs/bib_results_before_apply.json
2) MUST NOT call Crossref API directly unless this command fails.
3) If output contains selection_required=true:
   - list top candidates per citation_id (rank, title, authors, journal, year, DOI, composite_score)
   - do not guess silently
4) Before final answer, provide execution evidence:
   - exact command run
   - output path
   - short summary from output
```

## First Pass (`.txt`)

```text
Use $crossref-citation-check on benchmarking/outputs/benchmark_bib.txt.

Hard constraints:
1) MUST run:
   python .github/skills/crossref-citation-check/crossref_checker.py -i benchmarking/outputs/benchmark_bib.txt -o benchmarking/outputs/refs_results_before_apply.json
2) MUST NOT call Crossref API directly unless this command fails.
3) If output contains selection_required=true:
   - list top candidates per citation_id (rank, title, authors, journal, year, DOI, composite_score)
   - do not guess silently
4) Before final answer, provide execution evidence:
   - exact command run
   - output path
   - short summary from output
```

## Second Pass (`--selection-map`)

Generate selection maps first:

```powershell
python benchmarking/benchmark_make_selection_map.py -i benchmarking/outputs/bib_results_before_apply.json -o benchmarking/outputs/bib_selection_map.json
python benchmarking/benchmark_make_selection_map.py -i benchmarking/outputs/refs_results_before_apply.json -o benchmarking/outputs/refs_selection_map.json
```

Then use these prompts:

```text
Use $crossref-citation-check on benchmarking/outputs/benchmark_bib.tex and apply user selections from benchmarking/outputs/bib_selection_map.json.

Hard constraints:
1) MUST run:
   python .github/skills/crossref-citation-check/crossref_checker.py -i benchmarking/outputs/benchmark_bib.tex --selection-map benchmarking/outputs/bib_selection_map.json -o benchmarking/outputs/bib_results_after_apply.json
2) MUST NOT call Crossref API directly unless this command fails.
3) Before final answer, provide execution evidence:
   - exact command run
   - output path
   - short summary from output
```

```text
Use $crossref-citation-check on benchmarking/outputs/benchmark_bib.txt and apply user selections from benchmarking/outputs/refs_selection_map.json.

Hard constraints:
1) MUST run:
   python .github/skills/crossref-citation-check/crossref_checker.py -i benchmarking/outputs/benchmark_bib.txt --selection-map benchmarking/outputs/refs_selection_map.json -o benchmarking/outputs/refs_results_after_apply.json
2) MUST NOT call Crossref API directly unless this command fails.
3) Before final answer, provide execution evidence:
   - exact command run
   - output path
   - short summary from output
```

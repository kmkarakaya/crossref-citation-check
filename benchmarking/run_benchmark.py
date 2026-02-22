from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List


def _run(cmd: List[str], cwd: Path) -> int:
    print(f"[run-benchmark] RUN: {shlex.join(cmd)}", flush=True)
    completed = subprocess.run(cmd, cwd=str(cwd))
    return completed.returncode


def _checker_command(
    python_exe: str,
    checker_path: Path,
    input_path: Path,
    output_path: Path,
    email: str | None,
    candidate_rows: int,
    auto_accept_threshold: float,
    ambiguity_gap_threshold: float,
    shortlist_trigger: str,
    selection_map: Path | None = None,
) -> List[str]:
    cmd = [
        python_exe,
        str(checker_path),
        "-i",
        str(input_path),
        "-o",
        str(output_path),
        "--candidate-rows",
        str(candidate_rows),
        "--auto-accept-threshold",
        str(auto_accept_threshold),
        "--ambiguity-gap-threshold",
        str(ambiguity_gap_threshold),
        "--shortlist-trigger",
        shortlist_trigger,
    ]
    if email:
        cmd.extend(["-e", email])
    if selection_map:
        cmd.extend(["--selection-map", str(selection_map)])
    return cmd


def _missing(paths: List[Path]) -> List[Path]:
    return [p for p in paths if not p.exists()]


def _pause_for_agent(stage: str) -> bool:
    try:
        input(f"[run-benchmark] PAUSE: {stage}. Run the agent prompts now, then press Enter...")
    except EOFError:
        print("[run-benchmark] ERROR: agent-in-loop mode requires an interactive terminal.")
        return False
    return True


def _wait_for_files(paths: List[Path], stage: str) -> bool:
    while True:
        missing = _missing(paths)
        if not missing:
            return True

        print(f"[run-benchmark] WAITING: {stage}")
        for p in missing:
            print(f"[run-benchmark] Missing: {p}")
        try:
            input("[run-benchmark] After generating missing files, press Enter to re-check...")
        except EOFError:
            print("[run-benchmark] ERROR: agent-in-loop mode requires an interactive terminal.")
            return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-command benchmark runner for crossref-citation-check.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used for all sub-commands. Default: current interpreter.",
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root path. Default: auto-detected.",
    )
    parser.add_argument(
        "--outputs-dir",
        default="benchmarking/outputs",
        help="Output directory for generated benchmark artifacts (relative to --root or absolute).",
    )
    parser.add_argument(
        "--min-overall",
        type=float,
        default=0.80,
        help="Passing threshold for final benchmark score.",
    )
    parser.add_argument("--email", default=None, help="Optional contact email passed to crossref_checker.py.")
    parser.add_argument("--candidate-rows", type=int, default=6, help="crossref_checker --candidate-rows")
    parser.add_argument(
        "--auto-accept-threshold",
        type=float,
        default=0.88,
        help="crossref_checker --auto-accept-threshold",
    )
    parser.add_argument(
        "--ambiguity-gap-threshold",
        type=float,
        default=0.06,
        help="crossref_checker --ambiguity-gap-threshold",
    )
    parser.add_argument(
        "--shortlist-trigger",
        default="missing_or_conflict",
        choices=["missing_or_conflict", "missing_only", "all"],
        help="crossref_checker --shortlist-trigger",
    )
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        help="Skip benchmark input generation and reuse existing benchmark_bib.* files.",
    )
    parser.add_argument(
        "--score-only",
        action="store_true",
        help="Only run benchmark_score.py (expects after-apply result files to already exist).",
    )
    parser.add_argument(
        "--mode",
        default="script",
        choices=["script", "agent-in-loop"],
        help="script: run all steps locally; agent-in-loop: pause for manual agent prompt steps.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    bench_dir = root / "benchmarking"
    outputs_dir_raw = Path(args.outputs_dir)
    outputs_dir = outputs_dir_raw if outputs_dir_raw.is_absolute() else (root / outputs_dir_raw)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    checker_path = root / ".github" / "skills" / "crossref-citation-check" / "crossref_checker.py"
    if not checker_path.exists():
        print(f"[run-benchmark] ERROR: checker script not found: {checker_path}")
        return 1

    groundtruth_tex = outputs_dir / "inputs" / "groundtruth_bib.tex"
    groundtruth_txt = outputs_dir / "inputs" / "groundtruth_bib.txt"
    if not groundtruth_tex.exists() or not groundtruth_txt.exists():
        print("[run-benchmark] ERROR: groundtruth files not found in outputs inputs folder.")
        print(f"[run-benchmark] Expected: {groundtruth_tex}")
        print(f"[run-benchmark] Expected: {groundtruth_txt}")
        return 1
    benchmark_tex = outputs_dir / "benchmark_bib.tex"
    benchmark_txt = outputs_dir / "benchmark_bib.txt"
    benchmark_manifest = outputs_dir / "benchmark_manifest.json"
    bib_before = outputs_dir / "bib_results_before_apply.json"
    refs_before = outputs_dir / "refs_results_before_apply.json"
    bib_map = outputs_dir / "bib_selection_map.json"
    refs_map = outputs_dir / "refs_selection_map.json"
    bib_after = outputs_dir / "bib_results_after_apply.json"
    refs_after = outputs_dir / "refs_results_after_apply.json"
    score_out = outputs_dir / "benchmark_score.json"

    commands: List[List[str]] = []

    generate_cmd = [
        args.python,
        str(bench_dir / "benchmark_generate.py"),
        "--groundtruth-tex",
        str(groundtruth_tex),
        "--groundtruth-txt",
        str(groundtruth_txt),
        "--out-tex",
        str(benchmark_tex),
        "--out-txt",
        str(benchmark_txt),
        "--manifest",
        str(benchmark_manifest),
    ]

    map_bib_cmd = [
        args.python,
        str(bench_dir / "benchmark_make_selection_map.py"),
        "-i",
        str(bib_before),
        "-o",
        str(bib_map),
    ]
    map_refs_cmd = [
        args.python,
        str(bench_dir / "benchmark_make_selection_map.py"),
        "-i",
        str(refs_before),
        "-o",
        str(refs_map),
    ]

    score_cmd = [
        args.python,
        str(bench_dir / "benchmark_score.py"),
        "--groundtruth-tex",
        str(groundtruth_tex),
        "--groundtruth-txt",
        str(groundtruth_txt),
        "--result-tex",
        str(bib_after),
        "--result-txt",
        str(refs_after),
        "--output",
        str(score_out),
        "--min-overall",
        str(args.min_overall),
    ]

    if args.mode == "script":
        if not args.score_only:
            if not args.skip_generate:
                commands.append(generate_cmd)

            commands.append(
                _checker_command(
                    python_exe=args.python,
                    checker_path=checker_path,
                    input_path=benchmark_tex,
                    output_path=bib_before,
                    email=args.email,
                    candidate_rows=args.candidate_rows,
                    auto_accept_threshold=args.auto_accept_threshold,
                    ambiguity_gap_threshold=args.ambiguity_gap_threshold,
                    shortlist_trigger=args.shortlist_trigger,
                )
            )
            commands.append(
                _checker_command(
                    python_exe=args.python,
                    checker_path=checker_path,
                    input_path=benchmark_txt,
                    output_path=refs_before,
                    email=args.email,
                    candidate_rows=args.candidate_rows,
                    auto_accept_threshold=args.auto_accept_threshold,
                    ambiguity_gap_threshold=args.ambiguity_gap_threshold,
                    shortlist_trigger=args.shortlist_trigger,
                )
            )
            commands.extend([map_bib_cmd, map_refs_cmd])
            commands.append(
                _checker_command(
                    python_exe=args.python,
                    checker_path=checker_path,
                    input_path=benchmark_tex,
                    output_path=bib_after,
                    email=args.email,
                    candidate_rows=args.candidate_rows,
                    auto_accept_threshold=args.auto_accept_threshold,
                    ambiguity_gap_threshold=args.ambiguity_gap_threshold,
                    shortlist_trigger=args.shortlist_trigger,
                    selection_map=bib_map,
                )
            )
            commands.append(
                _checker_command(
                    python_exe=args.python,
                    checker_path=checker_path,
                    input_path=benchmark_txt,
                    output_path=refs_after,
                    email=args.email,
                    candidate_rows=args.candidate_rows,
                    auto_accept_threshold=args.auto_accept_threshold,
                    ambiguity_gap_threshold=args.ambiguity_gap_threshold,
                    shortlist_trigger=args.shortlist_trigger,
                    selection_map=refs_map,
                )
            )

        commands.append(score_cmd)
    else:
        if not args.score_only:
            if not args.skip_generate:
                commands.append(generate_cmd)
            for cmd in commands:
                code = _run(cmd, cwd=root)
                if code != 0:
                    print(f"[run-benchmark] STOP: command failed with exit code {code}")
                    return code
            commands = []

            print("[run-benchmark] Agent-in-loop mode.")
            print("[run-benchmark] Step 1: run first-pass prompts from benchmarking/benchmark_agent_prompts.md")
            print(f"[run-benchmark] Expected outputs: {bib_before} and {refs_before}")
            if not _pause_for_agent("Step 1 (first-pass agent prompts)"):
                return 1
            if not _wait_for_files([bib_before, refs_before], "first-pass agent outputs"):
                return 1

            for cmd in [map_bib_cmd, map_refs_cmd]:
                code = _run(cmd, cwd=root)
                if code != 0:
                    print(f"[run-benchmark] STOP: command failed with exit code {code}")
                    return code

            print("[run-benchmark] Step 2: run second-pass prompts with selection maps from benchmarking/benchmark_agent_prompts.md")
            print(f"[run-benchmark] Expected outputs: {bib_after} and {refs_after}")
            if not _pause_for_agent("Step 2 (second-pass agent prompts with selection maps)"):
                return 1
            if not _wait_for_files([bib_after, refs_after], "second-pass agent outputs"):
                return 1

        commands.append(score_cmd)

    for cmd in commands:
        code = _run(cmd, cwd=root)
        if code != 0:
            print(f"[run-benchmark] STOP: command failed with exit code {code}")
            return code

    print("[run-benchmark] Done.")
    print(f"[run-benchmark] Score report: {score_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

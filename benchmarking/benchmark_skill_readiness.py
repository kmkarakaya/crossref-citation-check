from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


REQUIRED_CASE_COLUMNS = {
    "case_id",
    "prompt",
    "should_trigger",
    "expects_selection_flow",
    "input_file",
}

REQUIRED_RESULT_KEYS = {
    "citation_id",
    "status",
    "correction_patch",
    "selection_required",
}


@dataclass
class ReadinessCase:
    case_id: str
    prompt: str
    should_trigger: bool
    expects_selection_flow: bool
    input_file: str



def _parse_bool(value: str) -> bool:
    text = (value or "").strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n", ""}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")



def _is_checker_command(line: str) -> bool:
    return "crossref_checker.py" in line.lower()



def _is_direct_crossref_api_command(line: str) -> bool:
    lower = line.lower()
    patterns = [
        "api.crossref.org/works",
        "https://api.crossref.org/",
        "http://api.crossref.org/",
        "crossref.org/works?",
    ]
    return any(p in lower for p in patterns)



def _read_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]



def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))



def _load_json_list(path: Path) -> List[Dict[str, Any]]:
    data = _load_json(path)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list in {path}")
    return [item for item in data if isinstance(item, dict)]



def load_cases(cases_path: Path) -> List[ReadinessCase]:
    with cases_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_CASE_COLUMNS - columns
        if missing:
            raise ValueError(f"readiness cases CSV missing required columns: {sorted(missing)}")

        cases: List[ReadinessCase] = []
        seen: set[str] = set()
        for row in reader:
            case_id = (row.get("case_id") or "").strip()
            if not case_id:
                raise ValueError("readiness cases CSV contains empty case_id")
            if case_id in seen:
                raise ValueError(f"duplicate case_id in readiness cases CSV: {case_id}")
            seen.add(case_id)

            cases.append(
                ReadinessCase(
                    case_id=case_id,
                    prompt=(row.get("prompt") or "").strip(),
                    should_trigger=_parse_bool(row.get("should_trigger") or "false"),
                    expects_selection_flow=_parse_bool(row.get("expects_selection_flow") or "false"),
                    input_file=(row.get("input_file") or "").strip(),
                )
            )

    if not cases:
        raise ValueError("readiness cases CSV is empty")
    return cases



def _validate_result_contract(result_files: List[Path]) -> tuple[bool, List[str]]:
    errors: List[str] = []
    if not result_files:
        return False, ["no_result_json_files"]

    valid_any = False
    for path in result_files:
        try:
            items = _load_json_list(path)
        except Exception:
            errors.append(f"invalid_json_list:{path.name}")
            continue

        valid_any = True
        for idx, item in enumerate(items):
            missing = [k for k in REQUIRED_RESULT_KEYS if k not in item]
            if missing:
                errors.append(f"missing_keys:{path.name}[{idx}]={missing}")

    if not valid_any:
        return False, errors or ["no_valid_result_json"]
    return len(errors) == 0, errors



def _extract_selection_required_ids(before_paths: List[Path]) -> tuple[set[str], List[str]]:
    required: set[str] = set()
    errors: List[str] = []
    for path in before_paths:
        try:
            items = _load_json_list(path)
        except Exception:
            errors.append(f"invalid_before_json:{path.name}")
            continue
        for item in items:
            if bool(item.get("selection_required")):
                cid = item.get("citation_id")
                if cid is not None:
                    required.add(str(cid))
    return required, errors



def _load_selection_maps(map_paths: List[Path]) -> tuple[Dict[str, Any], List[str]]:
    merged: Dict[str, Any] = {}
    errors: List[str] = []
    for path in map_paths:
        try:
            payload = _load_json(path)
        except Exception:
            errors.append(f"invalid_selection_map:{path.name}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"selection_map_not_object:{path.name}")
            continue
        for k, v in payload.items():
            merged[str(k)] = v
    return merged, errors



def _extract_after_selection_flags(after_paths: List[Path]) -> tuple[Dict[str, bool], List[str]]:
    flags: Dict[str, bool] = {}
    errors: List[str] = []
    for path in after_paths:
        try:
            items = _load_json_list(path)
        except Exception:
            errors.append(f"invalid_after_json:{path.name}")
            continue
        for item in items:
            cid = item.get("citation_id")
            if cid is None:
                continue
            flags[str(cid)] = bool(item.get("selection_required"))
    return flags, errors



def evaluate_case(case: ReadinessCase, runs_dir: Path) -> Dict[str, Any]:
    case_dir = runs_dir / case.case_id
    response_path = case_dir / "response.md"
    commands_path = case_dir / "commands.txt"

    response_text = response_path.read_text(encoding="utf-8-sig") if response_path.exists() else ""
    commands = _read_lines(commands_path)

    checker_indices = [idx for idx, line in enumerate(commands) if _is_checker_command(line)]
    direct_api_indices = [idx for idx, line in enumerate(commands) if _is_direct_crossref_api_command(line)]

    did_trigger = len(checker_indices) > 0
    trigger_check = did_trigger if case.should_trigger else (not did_trigger)

    if checker_indices:
        first_checker = min(checker_indices)
        direct_before_checker = any(idx < first_checker for idx in direct_api_indices)
        script_first_check = not direct_before_checker
        direct_api_violation = direct_before_checker
    else:
        script_first_check = len(direct_api_indices) == 0
        direct_api_violation = len(direct_api_indices) > 0

    should_validate_evidence = case.should_trigger or did_trigger
    if should_validate_evidence:
        response_lower = response_text.lower()
        has_command_evidence = ("crossref_checker.py" in response_lower) or any(_is_checker_command(c) for c in commands)
        has_output_path = (".json" in response_lower) and any(
            keyword in response_lower for keyword in ["output", "path", "written", "saved"]
        )
        has_summary_signal = any(
            keyword in response_lower
            for keyword in [
                "summary",
                "status",
                "selection_required",
                "result",
                "corrected",
                "unresolved",
                "critical_mismatch",
                "match_found",
            ]
        )
        evidence_check = has_command_evidence and has_output_path and has_summary_signal
    else:
        evidence_check = True

    result_json_files = sorted(case_dir.glob("*_before_apply.json")) + sorted(case_dir.glob("*_after_apply.json"))
    if case.should_trigger or did_trigger:
        output_contract_check, contract_errors = _validate_result_contract(result_json_files)
    else:
        output_contract_check, contract_errors = True, []

    selection_errors: List[str] = []
    if case.expects_selection_flow:
        before_paths = sorted(case_dir.glob("*_before_apply.json"))
        after_paths = sorted(case_dir.glob("*_after_apply.json"))
        map_paths = sorted(case_dir.glob("*_selection_map.json"))

        if not before_paths:
            selection_flow_check = False
            selection_errors.append("missing_before_apply")
            required_ids: set[str] = set()
        else:
            required_ids, err = _extract_selection_required_ids(before_paths)
            selection_errors.extend(err)
            if not required_ids:
                selection_flow_check = False
                selection_errors.append("no_selection_required_in_before_apply")
            else:
                selection_map, err = _load_selection_maps(map_paths)
                selection_errors.extend(err)
                if not map_paths:
                    selection_flow_check = False
                    selection_errors.append("missing_selection_map")
                elif not all(cid in selection_map for cid in required_ids):
                    selection_flow_check = False
                    selection_errors.append("selection_map_missing_required_citations")
                elif not after_paths:
                    selection_flow_check = False
                    selection_errors.append("missing_after_apply")
                else:
                    after_flags, err = _extract_after_selection_flags(after_paths)
                    selection_errors.extend(err)
                    unresolved = [cid for cid in required_ids if after_flags.get(cid, True)]
                    selection_flow_check = len(unresolved) == 0
                    if unresolved:
                        selection_errors.append(f"selection_still_required_after_apply:{sorted(unresolved)}")
    else:
        selection_flow_check = True

    checks = {
        "trigger_check": trigger_check,
        "script_first_check": script_first_check,
        "selection_flow_check": selection_flow_check,
        "evidence_check": evidence_check,
        "output_contract_check": output_contract_check,
    }

    applicable_checks = ["trigger_check", "script_first_check"]
    if case.should_trigger:
        applicable_checks.extend(["evidence_check", "output_contract_check"])
    if case.expects_selection_flow:
        applicable_checks.append("selection_flow_check")

    passed_applicable = sum(1 for key in applicable_checks if checks.get(key))
    workflow_score = (passed_applicable / len(applicable_checks)) if applicable_checks else 1.0

    hard_fail_reasons: List[str] = []
    if (not case.should_trigger) and did_trigger:
        hard_fail_reasons.append("negative_control_false_positive")
    if case.expects_selection_flow and (not selection_flow_check):
        hard_fail_reasons.append("missing_required_selection_flow")
    if direct_api_violation:
        hard_fail_reasons.append("direct_crossref_api_policy_violation")

    failed_checks = [key for key in checks.keys() if not checks[key]]

    return {
        "case_id": case.case_id,
        "prompt": case.prompt,
        "should_trigger": case.should_trigger,
        "did_trigger": did_trigger,
        "expects_selection_flow": case.expects_selection_flow,
        "checks": checks,
        "applicable_checks": applicable_checks,
        "workflow_score": round(workflow_score, 6),
        "failed_checks": failed_checks,
        "direct_api_violation": direct_api_violation,
        "hard_fail_reasons": hard_fail_reasons,
        "case_dir": str(case_dir),
        "contract_errors": contract_errors,
        "selection_errors": selection_errors,
        "files_found": {
            "response_md": response_path.exists(),
            "commands_txt": commands_path.exists(),
            "result_json_count": len(result_json_files),
        },
    }



def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return numerator / denominator



def _load_correction_rate(correction_score_path: Path) -> float:
    payload = _load_json(correction_score_path)
    if not isinstance(payload, dict):
        raise ValueError("correction score JSON must be an object")
    overall = payload.get("overall")
    if not isinstance(overall, dict):
        raise ValueError("correction score JSON missing overall object")
    rate = overall.get("overall_correction_rate")
    if rate is None:
        raise ValueError("correction score JSON missing overall.overall_correction_rate")
    return float(rate)



def evaluate_readiness(
    cases_path: Path,
    runs_dir: Path,
    correction_score_path: Path,
    min_correction_rate: float = 0.85,
    min_trigger_recall: float = 0.90,
    min_workflow_compliance: float = 0.90,
) -> Dict[str, Any]:
    cases = load_cases(cases_path)
    correction_rate = _load_correction_rate(correction_score_path)

    per_case = [evaluate_case(case, runs_dir) for case in cases]

    positives = [c for c in per_case if c["should_trigger"]]
    negatives = [c for c in per_case if not c["should_trigger"]]

    tp = sum(1 for c in per_case if c["should_trigger"] and c["did_trigger"])
    fp = sum(1 for c in per_case if (not c["should_trigger"]) and c["did_trigger"])
    fn = sum(1 for c in per_case if c["should_trigger"] and (not c["did_trigger"]))

    trigger_precision = _safe_ratio(tp, tp + fp)
    trigger_recall = _safe_ratio(tp, tp + fn)

    total_applicable = sum(len(c["applicable_checks"]) for c in per_case)
    total_passed = sum(
        sum(1 for key in c["applicable_checks"] if c["checks"].get(key)) for c in per_case
    )
    workflow_compliance_rate = _safe_ratio(total_passed, total_applicable)

    hard_fail_reasons: List[str] = []
    for case in per_case:
        for reason in case["hard_fail_reasons"]:
            hard_fail_reasons.append(f"{case['case_id']}: {reason}")

    thresholds = {
        "min_correction_rate": min_correction_rate,
        "required_trigger_precision": 1.0,
        "min_trigger_recall": min_trigger_recall,
        "min_workflow_compliance": min_workflow_compliance,
    }

    overall_ready = (
        correction_rate >= min_correction_rate
        and abs(trigger_precision - 1.0) <= 1e-12
        and trigger_recall >= min_trigger_recall
        and workflow_compliance_rate >= min_workflow_compliance
        and len(hard_fail_reasons) == 0
    )

    return {
        "overall_ready": overall_ready,
        "hard_fail_reasons": hard_fail_reasons,
        "thresholds": thresholds,
        "metrics": {
            "correction_rate": round(correction_rate, 6),
            "trigger_precision": round(trigger_precision, 6),
            "trigger_recall": round(trigger_recall, 6),
            "workflow_compliance_rate": round(workflow_compliance_rate, 6),
            "case_count": len(per_case),
            "positive_case_count": len(positives),
            "negative_case_count": len(negatives),
        },
        "per_case": per_case,
    }



def build_report_markdown(payload: Dict[str, Any], cases_path: Path, runs_dir: Path, correction_score_path: Path) -> str:
    overall_ready = bool(payload.get("overall_ready"))
    metrics = payload.get("metrics") or {}
    thresholds = payload.get("thresholds") or {}
    hard_fails = payload.get("hard_fail_reasons") or []
    per_case = payload.get("per_case") or []

    lines: List[str] = []
    lines.append("# Skill Readiness Report")
    lines.append("")
    lines.append(f"- Overall ready: `{overall_ready}`")
    lines.append(f"- Cases file: `{cases_path}`")
    lines.append(f"- Runs directory: `{runs_dir}`")
    lines.append(f"- Correction score source: `{correction_score_path}`")
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append(f"- Correction rate: `{metrics.get('correction_rate')}` (min `{thresholds.get('min_correction_rate')}`)")
    lines.append(
        f"- Trigger precision: `{metrics.get('trigger_precision')}` (required `{thresholds.get('required_trigger_precision')}`)"
    )
    lines.append(f"- Trigger recall: `{metrics.get('trigger_recall')}` (min `{thresholds.get('min_trigger_recall')}`)")
    lines.append(
        f"- Workflow compliance: `{metrics.get('workflow_compliance_rate')}` (min `{thresholds.get('min_workflow_compliance')}`)"
    )
    lines.append(f"- Case count: `{metrics.get('case_count')}`")
    lines.append("")

    lines.append("## Hard Fails")
    lines.append("")
    if hard_fails:
        for reason in hard_fails:
            lines.append(f"- {reason}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Per-Case Summary")
    lines.append("")
    lines.append(
        "| Case | Should Trigger | Did Trigger | Selection Flow Expected | Workflow Score | Failed Checks | Hard Fails |"
    )
    lines.append("|---|---:|---:|---:|---:|---|---|")
    for case in per_case:
        lines.append(
            "| "
            f"`{case.get('case_id')}` | "
            f"`{case.get('should_trigger')}` | "
            f"`{case.get('did_trigger')}` | "
            f"`{case.get('expects_selection_flow')}` | "
            f"`{case.get('workflow_score')}` | "
            f"`{case.get('failed_checks')}` | "
            f"`{case.get('hard_fail_reasons')}` |"
        )

    lines.append("")
    lines.append("## Failed Check Details")
    lines.append("")
    failed_cases = [c for c in per_case if c.get("failed_checks") or c.get("hard_fail_reasons")]
    if not failed_cases:
        lines.append("- none")
    else:
        for case in failed_cases:
            lines.append(f"### `{case.get('case_id')}`")
            lines.append(f"- Failed checks: `{case.get('failed_checks')}`")
            lines.append(f"- Hard fails: `{case.get('hard_fail_reasons')}`")
            contract_errors = case.get("contract_errors") or []
            selection_errors = case.get("selection_errors") or []
            if contract_errors:
                lines.append(f"- Contract errors: `{contract_errors}`")
            if selection_errors:
                lines.append(f"- Selection errors: `{selection_errors}`")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"



def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate skill readiness using deterministic checks over captured agent runs.")
    parser.add_argument("--cases", required=True, help="Path to readiness_cases.csv")
    parser.add_argument("--runs-dir", required=True, help="Directory containing per-case run artifacts")
    parser.add_argument("--correction-score", required=True, help="Path to benchmark_score.json")
    parser.add_argument("--output", required=True, help="Path to output skill_readiness.json")
    parser.add_argument("--report", required=True, help="Path to output skill_readiness.md")
    parser.add_argument("--min-correction-rate", type=float, default=0.85)
    parser.add_argument("--min-trigger-recall", type=float, default=0.90)
    parser.add_argument("--min-workflow-compliance", type=float, default=0.90)
    args = parser.parse_args()

    try:
        payload = evaluate_readiness(
            cases_path=Path(args.cases),
            runs_dir=Path(args.runs_dir),
            correction_score_path=Path(args.correction_score),
            min_correction_rate=args.min_correction_rate,
            min_trigger_recall=args.min_trigger_recall,
            min_workflow_compliance=args.min_workflow_compliance,
        )
        output_path = Path(args.output)
        report_path = Path(args.report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        report_md = build_report_markdown(
            payload=payload,
            cases_path=Path(args.cases),
            runs_dir=Path(args.runs_dir),
            correction_score_path=Path(args.correction_score),
        )
        report_path.write_text(report_md, encoding="utf-8")
    except Exception as exc:
        print(f"[skill-readiness] ERROR: {exc}")
        return 1

    print(f"[skill-readiness] Output written: {args.output}")
    print(f"[skill-readiness] Report written: {args.report}")
    print(f"[skill-readiness] Overall ready: {payload.get('overall_ready')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

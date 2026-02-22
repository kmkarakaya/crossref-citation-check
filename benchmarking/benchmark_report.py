from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from benchmark_score import apply_correction_patch
from benchmark_utils import ALL_FIELDS, CORE_FIELDS, article_to_fields, field_match_score, load_crossref_checker


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_json_list(path: Path) -> List[Dict[str, Any]]:
    data = _load_json(path)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list: {path}")
    return data


def _article_to_fields_obj(article: Any) -> Dict[str, Any]:
    return {
        "authors": list(getattr(article, "authors", []) or []),
        "title": getattr(article, "title", None),
        "journal": getattr(article, "journal", None),
        "volume": getattr(article, "volume", None),
        "issue": getattr(article, "issue", None),
        "pages": getattr(article, "pages", None),
        "year": getattr(article, "year", None),
        "doi": getattr(article, "doi", None),
        "url": getattr(article, "url", None),
    }


def _fmt_value(value: Any) -> str:
    if value is None:
        return "`<null>`"
    if value == []:
        return "`[]`"
    if isinstance(value, list):
        return "<br>".join(str(v) for v in value) if value else "`[]`"
    text = str(value)
    if text == "":
        return "`<empty>`"
    return text.replace("\n", "<br>")


def _fmt_float(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def _fmt_bool(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "n/a"


def _fmt_fixed(targeted_wrong: Any, fixed: Any) -> str:
    if targeted_wrong is False:
        return "Not Needed"
    if fixed is True:
        return "yes"
    if fixed is False:
        return "no"
    return "n/a"


def _safe_get_score_row(score_by_id: Dict[str, Dict[str, Any]], citation_id: str, section: str) -> Dict[str, Any]:
    row = score_by_id.get(citation_id)
    if row is None:
        raise ValueError(f"Missing score mapping for {section} citation_id '{citation_id}'")
    return row


def _validate_mapping(
    section: str,
    benchmark_ids: List[str],
    groundtruth_ids: List[str],
    result_ids: List[str],
    score_ids: List[str],
) -> None:
    missing_gt = [cid for cid in benchmark_ids if cid not in set(groundtruth_ids)]
    missing_res = [cid for cid in benchmark_ids if cid not in set(result_ids)]
    missing_score = [cid for cid in benchmark_ids if cid not in set(score_ids)]
    extra_res = [cid for cid in result_ids if cid not in set(benchmark_ids)]
    extra_score = [cid for cid in score_ids if cid not in set(benchmark_ids)]

    errors: List[str] = []
    if missing_gt:
        errors.append(f"{section}: missing groundtruth citations: {missing_gt}")
    if missing_res:
        errors.append(f"{section}: missing result citations: {missing_res}")
    if missing_score:
        errors.append(f"{section}: missing score citations: {missing_score}")
    if extra_res:
        errors.append(f"{section}: unexpected result citations: {extra_res}")
    if extra_score:
        errors.append(f"{section}: unexpected score citations: {extra_score}")
    if errors:
        raise ValueError("; ".join(errors))


def _field_outcome_row(
    field: str,
    score_row: Dict[str, Any],
    gt_fields: Dict[str, Any],
    benchmark_fields: Dict[str, Any],
    corrected_fields: Dict[str, Any],
) -> Dict[str, Any]:
    outcomes = score_row.get("field_outcomes")
    if isinstance(outcomes, dict) and isinstance(outcomes.get(field), dict):
        row = outcomes[field]
        return {
            "targeted_wrong": row.get("targeted_wrong"),
            "benchmark_match": row.get("benchmark_match"),
            "corrected_match": row.get("corrected_match"),
            "fixed": row.get("fixed"),
        }

    # Backward-compat fallback for old score schema.
    benchmark_match = field_match_score(field, gt_fields.get(field), benchmark_fields.get(field)) if field in CORE_FIELDS else None
    corrected_match = field_match_score(field, gt_fields.get(field), corrected_fields.get(field)) if field in CORE_FIELDS else None
    return {
        "targeted_wrong": None,
        "benchmark_match": benchmark_match,
        "corrected_match": corrected_match,
        "fixed": None,
    }


def _build_citation_section(
    section: str,
    citation_id: str,
    benchmark_fields: Dict[str, Any],
    corrected_fields: Dict[str, Any],
    groundtruth_fields: Dict[str, Any],
    result_item: Dict[str, Any],
    score_row: Dict[str, Any],
) -> str:
    status = result_item.get("status")
    matched_by = result_item.get("matched_by")
    selection_required = result_item.get("selection_required")
    selection_reason = result_item.get("selection_reason")
    selected_candidate_rank = result_item.get("selected_candidate_rank")
    recommended_candidate_rank = result_item.get("recommended_candidate_rank")

    lines: List[str] = []
    lines.append(f"### {section.upper()} `{citation_id}`")
    lines.append("")
    lines.append(
        "Status: "
        f"`status={status}` | "
        f"`selection_required={selection_required}` | "
        f"`matched_by={matched_by}` | "
        f"`selection_reason={selection_reason}` | "
        f"`selected_candidate_rank={selected_candidate_rank}` | "
        f"`recommended_candidate_rank={recommended_candidate_rank}`"
    )
    lines.append("")
    lines.append(
        "Correction Summary: "
        f"`targeted={score_row.get('targeted_wrong_count')}` | "
        f"`fixed={score_row.get('fixed_count')}` | "
        f"`correction_rate={score_row.get('correction_rate')}` | "
        f"`targeted_source={score_row.get('targeted_source')}` | "
        f"`status_score={score_row.get('status_score')}`"
    )
    lines.append("")
    lines.append(
        "| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | "
        "Benchmark vs GT | Corrected vs GT | Fixed? |"
    )
    lines.append("|---|---:|---|---|---|---:|---:|---:|")

    for field in ALL_FIELDS:
        outcome = _field_outcome_row(field, score_row, groundtruth_fields, benchmark_fields, corrected_fields)
        lines.append(
            f"| `{field}` | {_fmt_bool(outcome.get('targeted_wrong'))} | {_fmt_value(benchmark_fields.get(field))} | "
            f"{_fmt_value(corrected_fields.get(field))} | {_fmt_value(groundtruth_fields.get(field))} | "
            f"{_fmt_float(outcome.get('benchmark_match'))} | {_fmt_float(outcome.get('corrected_match'))} | "
            f"{_fmt_fixed(outcome.get('targeted_wrong'), outcome.get('fixed'))} |"
        )

    warnings = score_row.get("warnings") or []
    if warnings:
        lines.append("")
        lines.append(f"Warnings: `{warnings}`")

    lines.append("")
    return "\n".join(lines)


def generate_report(
    groundtruth_tex: Path,
    groundtruth_txt: Path,
    benchmark_tex: Path,
    benchmark_txt: Path,
    result_tex: Path,
    result_txt: Path,
    score_json: Path,
    output: Path,
) -> Path:
    cc, _ = load_crossref_checker()

    gt_tex_articles = cc.load_articles_from_text(str(groundtruth_tex))
    gt_txt_articles = cc.load_articles_from_text(str(groundtruth_txt))
    bm_tex_articles = cc.load_articles_from_text(str(benchmark_tex))
    bm_txt_articles = cc.load_articles_from_text(str(benchmark_txt))
    tex_results = _load_json_list(result_tex)
    txt_results = _load_json_list(result_txt)
    score_payload = _load_json(score_json)
    if not isinstance(score_payload, dict):
        raise ValueError("score_json must be a JSON object")

    files_obj = score_payload.get("files")
    if not isinstance(files_obj, dict):
        raise ValueError("score_json missing 'files' object")
    tex_score = files_obj.get("tex")
    txt_score = files_obj.get("txt")
    if not isinstance(tex_score, dict) or not isinstance(txt_score, dict):
        raise ValueError("score_json missing files.tex/files.txt objects")
    tex_score_rows = tex_score.get("citations")
    txt_score_rows = txt_score.get("citations")
    if not isinstance(tex_score_rows, list) or not isinstance(txt_score_rows, list):
        raise ValueError("score_json files.tex/files.txt missing citations list")

    gt_tex = {a.citation_id: a for a in gt_tex_articles}
    gt_txt = {a.citation_id: a for a in gt_txt_articles}
    bm_tex = {a.citation_id: a for a in bm_tex_articles}
    bm_txt = {a.citation_id: a for a in bm_txt_articles}
    res_tex = {str(r.get("citation_id")): r for r in tex_results}
    res_txt = {str(r.get("citation_id")): r for r in txt_results}
    score_tex = {str(r.get("citation_id")): r for r in tex_score_rows if isinstance(r, dict)}
    score_txt = {str(r.get("citation_id")): r for r in txt_score_rows if isinstance(r, dict)}

    tex_ids = [a.citation_id for a in bm_tex_articles]
    txt_ids = [a.citation_id for a in bm_txt_articles]
    _validate_mapping("tex", tex_ids, list(gt_tex.keys()), list(res_tex.keys()), list(score_tex.keys()))
    _validate_mapping("txt", txt_ids, list(gt_txt.keys()), list(res_txt.keys()), list(score_txt.keys()))

    now = datetime.now(timezone.utc).isoformat()
    policy = score_payload.get("scoring_policy") or {}
    overall = score_payload.get("overall") or {}

    lines: List[str] = []
    lines.append("# Benchmark Per-Reference Report")
    lines.append("")
    lines.append(f"Generated at (UTC): `{now}`")
    lines.append("")
    lines.append("## Scoring Policy")
    lines.append("")
    lines.append(f"- Primary: `{policy.get('primary_score_mode', 'n/a')}`")
    lines.append(f"- Targeted Fields Source: `{policy.get('targeted_field_source', 'n/a')}`")
    lines.append(f"- Core Fields: `{policy.get('core_fields', [])}`")
    lines.append("")
    lines.append("## Overall Summary")
    lines.append("")
    lines.append(f"- Threshold: `{score_payload.get('threshold')}`")
    lines.append(
        f"- Correction: `{overall.get('total_fixed_fields')}` / `{overall.get('total_targeted_wrong_fields')}` = "
        f"`{overall.get('overall_correction_rate')}`"
    )
    lines.append(f"- Average status score: `{overall.get('average_status_score')}`")
    lines.append(f"- Total citations: `{overall.get('total_citations')}`")
    lines.append(f"- Passed: `{overall.get('passed')}`")
    lines.append("")
    lines.append("## File Summaries")
    lines.append("")

    for section_key, section_title in (("tex", "TEX"), ("txt", "TXT")):
        section = files_obj.get(section_key) or {}
        lines.append(
            f"- {section_title}: fixed `{section.get('total_fixed_fields')}` / "
            f"`{section.get('total_targeted_wrong_fields')}` = `{section.get('correction_rate')}` | "
            f"avg_status=`{section.get('average_status_score')}`"
        )
    lines.append("")
    lines.append("## TEX Citations")
    lines.append("")

    for cid in tex_ids:
        bm_article = bm_tex[cid]
        gt_article = gt_tex[cid]
        result_item = res_tex[cid]
        score_row = _safe_get_score_row(score_tex, cid, "tex")
        article_payload = result_item.get("article")
        if not isinstance(article_payload, dict):
            raise ValueError(f"Result item for {cid} missing article object")
        patch = result_item.get("correction_patch") or {"set": {}, "unset": []}
        if not isinstance(patch, dict):
            raise ValueError(f"Result item for {cid} has invalid correction_patch")
        corrected_fields = apply_correction_patch(article_to_fields(article_payload), patch)
        lines.append(
            _build_citation_section(
                section="tex",
                citation_id=cid,
                benchmark_fields=_article_to_fields_obj(bm_article),
                corrected_fields=corrected_fields,
                groundtruth_fields=_article_to_fields_obj(gt_article),
                result_item=result_item,
                score_row=score_row,
            )
        )

    lines.append("## TXT Citations")
    lines.append("")
    for cid in txt_ids:
        bm_article = bm_txt[cid]
        gt_article = gt_txt[cid]
        result_item = res_txt[cid]
        score_row = _safe_get_score_row(score_txt, cid, "txt")
        article_payload = result_item.get("article")
        if not isinstance(article_payload, dict):
            raise ValueError(f"Result item for {cid} missing article object")
        patch = result_item.get("correction_patch") or {"set": {}, "unset": []}
        if not isinstance(patch, dict):
            raise ValueError(f"Result item for {cid} has invalid correction_patch")
        corrected_fields = apply_correction_patch(article_to_fields(article_payload), patch)
        lines.append(
            _build_citation_section(
                section="txt",
                citation_id=cid,
                benchmark_fields=_article_to_fields_obj(bm_article),
                corrected_fields=corrected_fields,
                groundtruth_fields=_article_to_fields_obj(gt_article),
                result_item=result_item,
                score_row=score_row,
            )
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate per-reference benchmark markdown report.")
    parser.add_argument("--groundtruth-tex", required=True, help="Path to groundtruth tex file")
    parser.add_argument("--groundtruth-txt", required=True, help="Path to groundtruth txt file")
    parser.add_argument("--benchmark-tex", required=True, help="Path to benchmark tex file")
    parser.add_argument("--benchmark-txt", required=True, help="Path to benchmark txt file")
    parser.add_argument("--result-tex", required=True, help="Path to after-apply results for benchmark tex")
    parser.add_argument("--result-txt", required=True, help="Path to after-apply results for benchmark txt")
    parser.add_argument("--score-json", required=True, help="Path to benchmark_score.json")
    parser.add_argument("--output", required=True, help="Path to report.md output")
    args = parser.parse_args()

    try:
        out = generate_report(
            groundtruth_tex=Path(args.groundtruth_tex),
            groundtruth_txt=Path(args.groundtruth_txt),
            benchmark_tex=Path(args.benchmark_tex),
            benchmark_txt=Path(args.benchmark_txt),
            result_tex=Path(args.result_tex),
            result_txt=Path(args.result_txt),
            score_json=Path(args.score_json),
            output=Path(args.output),
        )
    except Exception as exc:
        print(f"[benchmark-report] ERROR: {exc}")
        return 1

    print(f"[benchmark-report] Output written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

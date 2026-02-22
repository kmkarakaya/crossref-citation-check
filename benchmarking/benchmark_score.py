from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from benchmark_utils import (
    CORE_FIELDS,
    article_to_fields,
    field_match_score,
    is_missing,
    load_crossref_checker,
    normalise_doi,
)


def apply_correction_patch(base_fields: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    fields = {
        "authors": list(base_fields.get("authors") or []),
        "title": base_fields.get("title"),
        "journal": base_fields.get("journal"),
        "volume": base_fields.get("volume"),
        "issue": base_fields.get("issue"),
        "pages": base_fields.get("pages"),
        "year": base_fields.get("year"),
        "doi": base_fields.get("doi"),
        "url": base_fields.get("url"),
    }
    for field in patch.get("unset", []):
        fields[field] = [] if field == "authors" else None
    for field, value in patch.get("set", {}).items():
        fields[field] = value
    if fields.get("doi") and not fields.get("url"):
        doi = normalise_doi(fields.get("doi"))
        if doi:
            fields["url"] = f"https://doi.org/{doi}"
    return fields


def compute_status_score(result_item: Dict[str, Any]) -> float:
    status = result_item.get("status")
    selection_required = bool(result_item.get("selection_required"))
    error = result_item.get("error")
    required_user_inputs = result_item.get("required_user_inputs") or []

    if status in {"match_found", "corrected"} and not selection_required:
        return 1.0
    if status in {"unresolved", "critical_mismatch"} and bool(error) and bool(required_user_inputs):
        return 0.6
    if selection_required:
        return 0.2
    return 0.0


def _groundtruth_fields_from_article(article: Any) -> Dict[str, Any]:
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


def _article_fields(article: Any) -> Dict[str, Any]:
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


def _parse_manifest_section(manifest_payload: Dict[str, Any], section: str) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    mutations = manifest_payload.get("mutations")
    if not isinstance(mutations, dict):
        return result
    rows = mutations.get(section)
    if not isinstance(rows, list):
        return result

    for row in rows:
        if not isinstance(row, dict):
            continue
        citation_id = row.get("citation_id")
        if not isinstance(citation_id, str):
            continue
        fields = row.get("mutated_fields_core")
        if not isinstance(fields, list):
            continue
        filtered = [f for f in fields if isinstance(f, str) and f in CORE_FIELDS]
        if filtered:
            result[citation_id] = filtered
    return result


def load_manifest_mutated_fields(manifest_path: Optional[Path]) -> Dict[str, Dict[str, List[str]]]:
    if manifest_path is None:
        return {"tex": {}, "txt": {}}
    payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Manifest must be a JSON object")
    return {
        "tex": _parse_manifest_section(payload, "tex"),
        "txt": _parse_manifest_section(payload, "txt"),
    }


def _resolve_targeted_wrong_fields(
    citation_id: str,
    gt_fields: Dict[str, Any],
    benchmark_fields: Dict[str, Any],
    manifest_fields: Optional[List[str]],
) -> Tuple[List[str], str, List[str], List[str]]:
    active_core_fields = [field for field in CORE_FIELDS if not is_missing(gt_fields.get(field))]
    auto_diff = [
        field
        for field in active_core_fields
        if field_match_score(field, gt_fields.get(field), benchmark_fields.get(field)) < 1.0
    ]

    warnings: List[str] = []
    if manifest_fields is None:
        return auto_diff, "auto_diff", auto_diff, warnings

    manifest_active = [field for field in manifest_fields if field in active_core_fields]
    targeted = [
        field
        for field in manifest_active
        if field_match_score(field, gt_fields.get(field), benchmark_fields.get(field)) < 1.0
    ]
    auto_only = [field for field in auto_diff if field not in manifest_active]
    if auto_only:
        warnings.append(f"auto_diff_only_fields={auto_only}")
    return targeted, "manifest", auto_diff, warnings


def _missing_citation_row(citation_id: str, targeted_wrong_fields: List[str], targeted_source: str, warnings: List[str]) -> Dict[str, Any]:
    field_outcomes = {
        field: {
            "targeted_wrong": field in targeted_wrong_fields,
            "benchmark_match": None,
            "corrected_match": None,
            "fixed": False,
        }
        for field in CORE_FIELDS
    }
    targeted_wrong_count = len(targeted_wrong_fields)
    correction_rate = 1.0 if targeted_wrong_count == 0 else 0.0
    return {
        "citation_id": citation_id,
        "missing_result": True,
        "targeted_source": targeted_source,
        "targeted_wrong_fields": targeted_wrong_fields,
        "targeted_wrong_count": targeted_wrong_count,
        "fixed_fields": [],
        "fixed_count": 0,
        "correction_rate": round(correction_rate, 6),
        "warning_no_targeted_fields": targeted_wrong_count == 0,
        "warnings": warnings,
        "field_outcomes": field_outcomes,
        "status": None,
        "selection_required": False,
        "status_score": 0.0,
    }


def score_results_against_groundtruth(
    groundtruth_articles: List[Any],
    benchmark_articles: List[Any],
    results: List[Dict[str, Any]],
    label: str,
    manifest_fields_lookup: Dict[str, List[str]],
) -> Dict[str, Any]:
    benchmark_by_id = {str(getattr(item, "citation_id")): item for item in benchmark_articles}
    result_by_id = {str(item.get("citation_id")): item for item in results}

    citation_reports: List[Dict[str, Any]] = []
    total_targeted_wrong_fields = 0
    total_fixed_fields = 0
    cumulative_status_score = 0.0

    for article in groundtruth_articles:
        citation_id = str(getattr(article, "citation_id"))
        gt_fields = _groundtruth_fields_from_article(article)

        benchmark_article = benchmark_by_id.get(citation_id)
        if benchmark_article is None:
            raise ValueError(f"Missing benchmark citation for {label}:{citation_id}")
        benchmark_fields = _article_fields(benchmark_article)

        manifest_fields = manifest_fields_lookup.get(citation_id)
        targeted_wrong_fields, targeted_source, _, warnings = _resolve_targeted_wrong_fields(
            citation_id,
            gt_fields,
            benchmark_fields,
            manifest_fields,
        )

        result_item = result_by_id.get(citation_id)
        if not result_item:
            row = _missing_citation_row(citation_id, targeted_wrong_fields, targeted_source, warnings)
            citation_reports.append(row)
            total_targeted_wrong_fields += row["targeted_wrong_count"]
            continue

        article_payload = result_item.get("article")
        if not isinstance(article_payload, dict):
            raise ValueError(f"Result item for {citation_id} is missing object field 'article'")
        patch = result_item.get("correction_patch") or {"set": {}, "unset": []}
        if not isinstance(patch, dict):
            raise ValueError(f"Result item for {citation_id} has invalid correction_patch")

        predicted_base = article_to_fields(article_payload)
        predicted_fields = apply_correction_patch(predicted_base, patch)

        status = result_item.get("status")
        selection_required = bool(result_item.get("selection_required"))
        status_score = compute_status_score(result_item)
        cumulative_status_score += status_score

        field_outcomes: Dict[str, Dict[str, Any]] = {}
        for field in CORE_FIELDS:
            benchmark_match = field_match_score(field, gt_fields.get(field), benchmark_fields.get(field))
            corrected_match = field_match_score(field, gt_fields.get(field), predicted_fields.get(field))
            is_targeted = field in targeted_wrong_fields
            fixed = is_targeted and corrected_match >= 1.0
            field_outcomes[field] = {
                "targeted_wrong": is_targeted,
                "benchmark_match": round(benchmark_match, 6),
                "corrected_match": round(corrected_match, 6),
                "fixed": fixed,
            }

        fixed_fields = [
            field
            for field in targeted_wrong_fields
            if field_match_score(field, gt_fields.get(field), predicted_fields.get(field)) >= 1.0
        ]
        targeted_wrong_count = len(targeted_wrong_fields)
        fixed_count = len(fixed_fields)
        correction_rate = 1.0 if targeted_wrong_count == 0 else (fixed_count / targeted_wrong_count)

        total_targeted_wrong_fields += targeted_wrong_count
        total_fixed_fields += fixed_count

        citation_reports.append(
            {
                "citation_id": citation_id,
                "missing_result": False,
                "targeted_source": targeted_source,
                "targeted_wrong_fields": targeted_wrong_fields,
                "targeted_wrong_count": targeted_wrong_count,
                "fixed_fields": fixed_fields,
                "fixed_count": fixed_count,
                "correction_rate": round(correction_rate, 6),
                "warning_no_targeted_fields": targeted_wrong_count == 0,
                "warnings": warnings,
                "field_outcomes": field_outcomes,
                "status": status,
                "selection_required": selection_required,
                "status_score": round(status_score, 6),
            }
        )

    count = len(groundtruth_articles)
    correction_rate = 1.0 if total_targeted_wrong_fields == 0 else (total_fixed_fields / total_targeted_wrong_fields)
    avg_status_score = cumulative_status_score / count if count else 0.0

    return {
        "label": label,
        "groundtruth_count": len(groundtruth_articles),
        "benchmark_count": len(benchmark_articles),
        "result_count": len(results),
        "total_targeted_wrong_fields": total_targeted_wrong_fields,
        "total_fixed_fields": total_fixed_fields,
        "correction_rate": round(correction_rate, 6),
        "average_status_score": round(avg_status_score, 6),
        "citations": citation_reports,
    }


def load_json_list(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError(f"JSON file must contain a list: {path}")
    return data


def score_benchmark(
    groundtruth_tex: Path,
    groundtruth_txt: Path,
    benchmark_tex: Path,
    benchmark_txt: Path,
    result_tex: Path,
    result_txt: Path,
    manifest: Optional[Path],
    min_overall: float,
) -> Dict[str, Any]:
    cc, _ = load_crossref_checker()
    gt_tex_articles = cc.load_articles_from_text(str(groundtruth_tex))
    gt_txt_articles = cc.load_articles_from_text(str(groundtruth_txt))
    bm_tex_articles = cc.load_articles_from_text(str(benchmark_tex))
    bm_txt_articles = cc.load_articles_from_text(str(benchmark_txt))

    if len(gt_tex_articles) != 7 or len(gt_txt_articles) != 7:
        raise ValueError("Groundtruth files must each parse into exactly 7 citations")
    if len(bm_tex_articles) != 7 or len(bm_txt_articles) != 7:
        raise ValueError("Benchmark files must each parse into exactly 7 citations")

    tex_results = load_json_list(result_tex)
    txt_results = load_json_list(result_txt)

    manifest_lookup = load_manifest_mutated_fields(manifest)

    tex_summary = score_results_against_groundtruth(
        groundtruth_articles=gt_tex_articles,
        benchmark_articles=bm_tex_articles,
        results=tex_results,
        label="tex",
        manifest_fields_lookup=manifest_lookup.get("tex", {}),
    )
    txt_summary = score_results_against_groundtruth(
        groundtruth_articles=gt_txt_articles,
        benchmark_articles=bm_txt_articles,
        results=txt_results,
        label="txt",
        manifest_fields_lookup=manifest_lookup.get("txt", {}),
    )

    total_targeted_wrong_fields = tex_summary["total_targeted_wrong_fields"] + txt_summary["total_targeted_wrong_fields"]
    total_fixed_fields = tex_summary["total_fixed_fields"] + txt_summary["total_fixed_fields"]
    overall_correction_rate = 1.0 if total_targeted_wrong_fields == 0 else (total_fixed_fields / total_targeted_wrong_fields)

    all_status_scores = [item["status_score"] for item in tex_summary["citations"]]
    all_status_scores.extend(item["status_score"] for item in txt_summary["citations"])
    average_status_score = sum(all_status_scores) / len(all_status_scores) if all_status_scores else 0.0

    passed = overall_correction_rate >= min_overall

    return {
        "scoring_policy": {
            "primary_score_mode": "mutation-correction rate (targeted wrong fields fixed / targeted wrong fields)",
            "targeted_field_source": "manifest.mutated_fields_core with auto-diff fallback",
            "core_fields": list(CORE_FIELDS),
        },
        "threshold": min_overall,
        "files": {
            "tex": tex_summary,
            "txt": txt_summary,
        },
        "overall": {
            "total_citations": len(all_status_scores),
            "total_targeted_wrong_fields": total_targeted_wrong_fields,
            "total_fixed_fields": total_fixed_fields,
            "overall_correction_rate": round(overall_correction_rate, 6),
            "average_status_score": round(average_status_score, 6),
            "passed": passed,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score checker benchmark results against ground truth.")
    parser.add_argument("--groundtruth-tex", required=True, help="Path to groundtruth tex file")
    parser.add_argument("--groundtruth-txt", required=True, help="Path to groundtruth txt file")
    parser.add_argument("--benchmark-tex", required=True, help="Path to benchmark tex file")
    parser.add_argument("--benchmark-txt", required=True, help="Path to benchmark txt file")
    parser.add_argument("--result-tex", required=True, help="Path to after-apply checker results for tex benchmark")
    parser.add_argument("--result-txt", required=True, help="Path to after-apply checker results for txt benchmark")
    parser.add_argument("--manifest", default=None, help="Optional benchmark_manifest.json path")
    parser.add_argument("--output", required=True, help="Path to score report JSON")
    parser.add_argument("--min-overall", type=float, default=0.80, help="Passing threshold for overall correction rate")
    args = parser.parse_args()

    try:
        manifest_path = Path(args.manifest) if args.manifest else None
        report = score_benchmark(
            groundtruth_tex=Path(args.groundtruth_tex),
            groundtruth_txt=Path(args.groundtruth_txt),
            benchmark_tex=Path(args.benchmark_tex),
            benchmark_txt=Path(args.benchmark_txt),
            result_tex=Path(args.result_tex),
            result_txt=Path(args.result_txt),
            manifest=manifest_path,
            min_overall=args.min_overall,
        )
        Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        print(f"[benchmark-score] ERROR: {exc}")
        return 1

    overall = report["overall"]["overall_correction_rate"]
    passed = report["overall"]["passed"]
    print(f"[benchmark-score] Output written: {args.output}")
    print(f"[benchmark-score] Overall correction rate: {overall:.6f}")
    print(f"[benchmark-score] Pass threshold: {args.min_overall:.6f}")
    print(f"[benchmark-score] Result: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

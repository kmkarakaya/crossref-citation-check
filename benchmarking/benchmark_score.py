from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Tuple

from benchmark_utils import (
    ALL_FIELDS,
    article_to_fields,
    author_overlap_score,
    is_missing,
    load_crossref_checker,
    normalise_doi,
    normalise_text,
    normalise_url,
)


FIELD_WEIGHTS = {
    "title": 0.30,
    "authors": 0.25,
    "journal": 0.20,
    "doi": 0.15,
    "year": 0.05,
    "url": 0.05,
}


def _title_similarity(left: Any, right: Any) -> float:
    l = normalise_text(str(left) if left is not None else "") or ""
    r = normalise_text(str(right) if right is not None else "") or ""
    if not l or not r:
        return 0.0
    return SequenceMatcher(None, l, r).ratio()


def _journal_match(left: Any, right: Any) -> bool:
    left_raw = str(left) if left is not None else ""
    right_raw = str(right) if right is not None else ""
    l_norm = normalise_text(left_raw) or ""
    r_norm = normalise_text(right_raw) or ""
    if not l_norm or not r_norm:
        return False
    if l_norm == r_norm:
        return True
    if l_norm in r_norm or r_norm in l_norm:
        return True
    return _title_similarity(left_raw, right_raw) >= 0.78


def _expand_authors_for_scoring(authors: List[str]) -> List[str]:
    expanded: List[str] = []
    for raw_name in (authors or []):
        if not raw_name:
            continue
        text = str(raw_name).strip()
        if not text:
            continue

        if ";" in text:
            expanded.extend([p.strip() for p in text.split(";") if p.strip()])
            continue

        and_parts = [p.strip() for p in re.split(r"\s+and\s+", text, flags=re.IGNORECASE) if p.strip()]
        if len(and_parts) > 1:
            expanded.extend(and_parts)
            continue

        comma_parts = [p.strip() for p in text.split(",") if p.strip()]
        if len(comma_parts) >= 2 and all(len(p.split()) >= 2 for p in comma_parts):
            expanded.extend(comma_parts)
            continue

        # Family,given pairs: e.g. "Sengul, Gokhan, Karakaya, Murat"
        if len(comma_parts) >= 4 and len(comma_parts) % 2 == 0:
            paired = [f"{comma_parts[i]}, {comma_parts[i + 1]}" for i in range(0, len(comma_parts), 2)]
            expanded.extend(paired)
            continue

        expanded.append(text)

    # Deduplicate while preserving order.
    deduped: List[str] = []
    seen = set()
    for name in expanded:
        key = name.strip().lower()
        if key and key not in seen:
            deduped.append(name)
            seen.add(key)
    return deduped


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


def _field_value_match(field: str, groundtruth: Any, predicted: Any) -> float:
    if field == "authors":
        gt_authors = _expand_authors_for_scoring(groundtruth or [])
        pred_authors = _expand_authors_for_scoring(predicted or [])
        return author_overlap_score(gt_authors, pred_authors)
    if field == "title":
        return 1.0 if normalise_text(groundtruth) == normalise_text(predicted) else 0.0
    if field == "journal":
        return 1.0 if _journal_match(groundtruth, predicted) else 0.0
    if field == "doi":
        return 1.0 if normalise_doi(groundtruth) == normalise_doi(predicted) else 0.0
    if field == "year":
        return 1.0 if str(groundtruth).strip() == str(predicted).strip() else 0.0
    if field == "url":
        return 1.0 if normalise_url(groundtruth) == normalise_url(predicted) else 0.0
    if field in ALL_FIELDS:
        return 1.0 if groundtruth == predicted else 0.0
    return 0.0


def compute_field_score(groundtruth_fields: Dict[str, Any], predicted_fields: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
    weighted = 0.0
    active_weight = 0.0
    field_scores: Dict[str, float] = {}

    for field, weight in FIELD_WEIGHTS.items():
        gt_value = groundtruth_fields.get(field)
        if is_missing(gt_value):
            continue
        score = _field_value_match(field, gt_value, predicted_fields.get(field))
        field_scores[field] = score
        weighted += weight * score
        active_weight += weight

    if active_weight == 0:
        return 0.0, field_scores
    return weighted / active_weight, field_scores


def compute_status_score(result_item: Dict[str, Any]) -> float:
    status = result_item.get("status")
    selection_required = bool(result_item.get("selection_required"))
    error = result_item.get("error")
    required_user_inputs = result_item.get("required_user_inputs") or []
    patch = result_item.get("correction_patch") or {}
    has_patch_update = bool((patch.get("set") or {})) or bool((patch.get("unset") or []))

    if status in {"match_found", "corrected"} and not selection_required:
        return 1.0
    if status == "critical_mismatch" and not selection_required:
        # Critical mismatch can still mean useful correction output was produced.
        return 0.8 if has_patch_update else 0.6
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


def score_results_against_groundtruth(groundtruth_articles: List[Any], results: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    result_by_id = {str(item.get("citation_id")): item for item in results}
    citation_reports: List[Dict[str, Any]] = []
    cumulative_score = 0.0

    for article in groundtruth_articles:
        citation_id = str(getattr(article, "citation_id"))
        gt_fields = _groundtruth_fields_from_article(article)
        result_item = result_by_id.get(citation_id)

        if not result_item:
            citation_reports.append(
                {
                    "citation_id": citation_id,
                    "missing_result": True,
                    "field_score": 0.0,
                    "status_score": 0.0,
                    "citation_score": 0.0,
                }
            )
            continue

        article_payload = result_item.get("article")
        if not isinstance(article_payload, dict):
            raise ValueError(f"Result item for {citation_id} is missing object field 'article'")
        patch = result_item.get("correction_patch") or {"set": {}, "unset": []}
        if not isinstance(patch, dict):
            raise ValueError(f"Result item for {citation_id} has invalid correction_patch")

        predicted_base = article_to_fields(article_payload)
        predicted_fields = apply_correction_patch(predicted_base, patch)

        field_score, field_details = compute_field_score(gt_fields, predicted_fields)
        status_score = compute_status_score(result_item)
        citation_score = 0.85 * field_score + 0.15 * status_score
        cumulative_score += citation_score

        citation_reports.append(
            {
                "citation_id": citation_id,
                "missing_result": False,
                "field_score": round(field_score, 6),
                "status_score": round(status_score, 6),
                "citation_score": round(citation_score, 6),
                "field_details": {k: round(v, 6) for k, v in field_details.items()},
                "status": result_item.get("status"),
                "selection_required": bool(result_item.get("selection_required")),
            }
        )

    avg_score = cumulative_score / len(groundtruth_articles) if groundtruth_articles else 0.0
    return {
        "label": label,
        "groundtruth_count": len(groundtruth_articles),
        "result_count": len(results),
        "average_score": round(avg_score, 6),
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
    result_tex: Path,
    result_txt: Path,
    min_overall: float,
) -> Dict[str, Any]:
    cc, _ = load_crossref_checker()
    gt_tex_articles = cc.load_articles_from_text(str(groundtruth_tex))
    gt_txt_articles = cc.load_articles_from_text(str(groundtruth_txt))
    if len(gt_tex_articles) != 7 or len(gt_txt_articles) != 7:
        raise ValueError("Groundtruth files must each parse into exactly 7 citations")

    tex_results = load_json_list(result_tex)
    txt_results = load_json_list(result_txt)

    tex_summary = score_results_against_groundtruth(gt_tex_articles, tex_results, "tex")
    txt_summary = score_results_against_groundtruth(gt_txt_articles, txt_results, "txt")

    all_scores = [item["citation_score"] for item in tex_summary["citations"]]
    all_scores.extend(item["citation_score"] for item in txt_summary["citations"])
    overall_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
    passed = overall_score >= min_overall

    return {
        "threshold": min_overall,
        "files": {
            "tex": tex_summary,
            "txt": txt_summary,
        },
        "overall": {
            "average_score": round(overall_score, 6),
            "total_citations": len(all_scores),
            "passed": passed,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score checker benchmark results against ground truth.")
    parser.add_argument("--groundtruth-tex", required=True, help="Path to groundtruth tex file")
    parser.add_argument("--groundtruth-txt", required=True, help="Path to groundtruth txt file")
    parser.add_argument("--result-tex", required=True, help="Path to after-apply checker results for tex benchmark")
    parser.add_argument("--result-txt", required=True, help="Path to after-apply checker results for txt benchmark")
    parser.add_argument("--output", required=True, help="Path to score report JSON")
    parser.add_argument("--min-overall", type=float, default=0.80, help="Passing threshold for overall average score")
    args = parser.parse_args()

    try:
        report = score_benchmark(
            groundtruth_tex=Path(args.groundtruth_tex),
            groundtruth_txt=Path(args.groundtruth_txt),
            result_tex=Path(args.result_tex),
            result_txt=Path(args.result_txt),
            min_overall=args.min_overall,
        )
        Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        print(f"[benchmark-score] ERROR: {exc}")
        return 1

    overall = report["overall"]["average_score"]
    passed = report["overall"]["passed"]
    print(f"[benchmark-score] Output written: {args.output}")
    print(f"[benchmark-score] Overall score: {overall:.6f}")
    print(f"[benchmark-score] Pass threshold: {args.min_overall:.6f}")
    print(f"[benchmark-score] Result: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

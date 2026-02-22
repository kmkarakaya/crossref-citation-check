from __future__ import annotations

import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ALL_FIELDS = ("authors", "title", "journal", "volume", "issue", "pages", "year", "doi", "url")
CORE_FIELDS = ("title", "authors", "journal", "doi", "year", "url")


def load_crossref_checker() -> Tuple[Any, Path]:
    root = Path(__file__).resolve().parents[1]
    skill_dir = root / ".github" / "skills" / "crossref-citation-check"
    if not skill_dir.exists():
        raise FileNotFoundError(f"Skill directory not found: {skill_dir}")
    if str(skill_dir) not in sys.path:
        sys.path.insert(0, str(skill_dir))
    import crossref_checker as cc  # type: ignore

    return cc, skill_dir


def is_missing(value: Any) -> bool:
    return value is None or value == "" or value == []


def normalise_doi(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    doi = value.strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    doi = doi.strip().rstrip(".,;")
    return doi.lower() if doi else None


def normalise_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def normalise_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return value.strip().rstrip(".,;").lower()


def author_key(name: str) -> Optional[str]:
    if not name:
        return None
    cleaned = re.sub(r"[^\w,\s-]+", "", name).strip().lower()
    if not cleaned:
        return None
    if "," in cleaned:
        parts = [p.strip() for p in cleaned.split(",", 1)]
        family = parts[0]
        given_part = parts[1] if len(parts) > 1 else ""
    else:
        tokens = cleaned.split()
        if not tokens:
            return None
        family = tokens[-1]
        given_part = " ".join(tokens[:-1])
    given_initial = given_part[:1] if given_part else ""
    if not family:
        return None
    return f"{family}:{given_initial}"


def f1_overlap(left: set, right: set) -> float:
    if not left or not right:
        return 0.0
    inter = len(left.intersection(right))
    if inter == 0:
        return 0.0
    precision = inter / len(right)
    recall = inter / len(left)
    if precision + recall == 0:
        return 0.0
    return (2.0 * precision * recall) / (precision + recall)


def author_overlap_score(left_authors: List[str], right_authors: List[str]) -> float:
    left = {k for k in (author_key(a) for a in (left_authors or [])) if k}
    right = {k for k in (author_key(a) for a in (right_authors or [])) if k}
    return f1_overlap(left, right)


def _title_similarity(left: Any, right: Any) -> float:
    l = normalise_text(str(left) if left is not None else "") or ""
    r = normalise_text(str(right) if right is not None else "") or ""
    if not l or not r:
        return 0.0
    return SequenceMatcher(None, l, r).ratio()


def _journal_numeric_tokens(value: Any) -> List[str]:
    text = str(value) if value is not None else ""
    return re.findall(r"\d+[a-zA-Z]*", text)


def journal_match(left: Any, right: Any) -> bool:
    left_raw = str(left) if left is not None else ""
    right_raw = str(right) if right is not None else ""
    l_norm = normalise_text(left_raw) or ""
    r_norm = normalise_text(right_raw) or ""
    if not l_norm or not r_norm:
        return False
    if l_norm == r_norm:
        return True
    if l_norm in r_norm or r_norm in l_norm:
        text_ok = True
    else:
        text_ok = _title_similarity(left_raw, right_raw) >= 0.78
    if not text_ok:
        return False

    left_nums = _journal_numeric_tokens(left_raw)
    right_nums = _journal_numeric_tokens(right_raw)
    if left_nums and right_nums:
        return left_nums == right_nums
    return True


def expand_authors_for_scoring(authors: List[str]) -> List[str]:
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

        if len(comma_parts) >= 4 and len(comma_parts) % 2 == 0:
            paired = [f"{comma_parts[i]}, {comma_parts[i + 1]}" for i in range(0, len(comma_parts), 2)]
            expanded.extend(paired)
            continue

        expanded.append(text)

    deduped: List[str] = []
    seen = set()
    for name in expanded:
        key = name.strip().lower()
        if key and key not in seen:
            deduped.append(name)
            seen.add(key)
    return deduped


def field_match_score(field: str, groundtruth: Any, predicted: Any) -> float:
    if field == "authors":
        gt_authors = expand_authors_for_scoring(groundtruth or [])
        pred_authors = expand_authors_for_scoring(predicted or [])
        return author_overlap_score(gt_authors, pred_authors)
    if field == "title":
        return 1.0 if normalise_text(groundtruth) == normalise_text(predicted) else 0.0
    if field == "journal":
        return 1.0 if journal_match(groundtruth, predicted) else 0.0
    if field == "doi":
        return 1.0 if normalise_doi(groundtruth) == normalise_doi(predicted) else 0.0
    if field == "year":
        return 1.0 if str(groundtruth).strip() == str(predicted).strip() else 0.0
    if field == "url":
        return 1.0 if normalise_url(groundtruth) == normalise_url(predicted) else 0.0
    if field in ALL_FIELDS:
        return 1.0 if groundtruth == predicted else 0.0
    return 0.0


def article_to_fields(article: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "authors": article.get("authors") or [],
        "title": article.get("title"),
        "journal": article.get("journal"),
        "volume": article.get("volume"),
        "issue": article.get("issue"),
        "pages": article.get("pages"),
        "year": article.get("year"),
        "doi": article.get("doi"),
        "url": article.get("url"),
    }

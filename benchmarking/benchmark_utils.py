from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ALL_FIELDS = ("authors", "title", "journal", "volume", "issue", "pages", "year", "doi", "url")


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

"""
crossref_checker.py
====================

Crossref-backed citation validation with strict mismatch detection and
correction-ready output (v2 schema).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


ALL_FIELDS = ("authors", "title", "journal", "volume", "issue", "pages", "year", "doi", "url")
DEFAULT_CRITICAL_FIELDS = ("title", "doi", "authors", "journal", "year")
SUPPORTED_SOURCE_FORMATS = {"json", "csv", "txt", "md", "tex", "bib"}


@dataclass
class Article:
    citation_id: str
    source_format: str
    raw_record: Optional[str] = None
    bibitem_key: Optional[str] = None
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    year: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None

    def provided_fields(self) -> Dict[str, Any]:
        return {
            "authors": self.authors,
            "title": self.title,
            "journal": self.journal,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "year": self.year,
            "doi": self.doi,
            "url": self.url,
        }


class CrossrefChecker:
    BASE_URL = "https://api.crossref.org/works"
    SEARCH_ROWS = 5
    DEFAULT_TITLE_MATCH_THRESHOLD = 0.85

    def __init__(
        self,
        email: Optional[str] = None,
        title_match_threshold: float = DEFAULT_TITLE_MATCH_THRESHOLD,
        critical_fields: Optional[List[str]] = None,
        emit_corrected_reference: bool = True,
        schema_version: str = "v2",
    ) -> None:
        user_agent = "CrossrefCitationChecker/2.0"
        if email:
            user_agent = f"{user_agent} (mailto:{email})"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.title_match_threshold = title_match_threshold
        self.critical_fields = set(critical_fields or list(DEFAULT_CRITICAL_FIELDS))
        self.emit_corrected_reference = emit_corrected_reference
        self.schema_version = schema_version

    @staticmethod
    def _is_missing(value: Any) -> bool:
        return value is None or value == "" or value == []

    @staticmethod
    def _normalise_doi(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        doi = value.strip()
        doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
        doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
        doi = doi.strip().rstrip(".,;")
        return doi.lower() if doi else None

    @staticmethod
    def _normalise_text(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return re.sub(r"[^a-z0-9]+", "", value.strip().lower())

    @staticmethod
    def _normalise_str(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip().lower()

    @staticmethod
    def _normalise_pages(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        page = value.replace("\u2013", "-").replace("\u2014", "-")
        page = re.sub(r"\s+", "", page)
        return page

    @classmethod
    def _title_similarity(cls, left: Optional[str], right: Optional[str]) -> float:
        l = cls._normalise_text(left) or ""
        r = cls._normalise_text(right) or ""
        if not l or not r:
            return 0.0
        return SequenceMatcher(None, l, r).ratio()

    @classmethod
    def _journal_match(cls, provided_journal: Optional[str], crossref_journal: Optional[str]) -> Optional[bool]:
        if not provided_journal:
            return None
        if not crossref_journal:
            return False
        p_norm = cls._normalise_text(provided_journal) or ""
        c_norm = cls._normalise_text(crossref_journal) or ""
        if p_norm == c_norm:
            return True
        if p_norm and c_norm and (p_norm in c_norm or c_norm in p_norm):
            return True
        return cls._title_similarity(provided_journal, crossref_journal) >= 0.78

    @staticmethod
    def _author_key(name: str) -> Optional[str]:
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

    def _request_with_retry(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[requests.Response]:
        delay = 1.0
        for attempt in range(4):
            try:
                response = self.session.get(url, params=params, timeout=30)
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt < 3:
                        time.sleep(delay)
                        delay *= 2
                        continue
                response.raise_for_status()
                return response
            except requests.RequestException:
                if attempt < 3:
                    time.sleep(delay)
                    delay *= 2
                    continue
                return None
        return None

    def _search_by_title(self, title: str) -> Dict[str, Any]:
        params = {"query.bibliographic": title, "rows": self.SEARCH_ROWS}
        response = self._request_with_retry(self.BASE_URL, params=params)
        if not response:
            return {"metadata": None, "score": 0.0, "candidate_rank": None, "candidate_title": None}

        data = response.json()
        items = data.get("message", {}).get("items", [])
        if not items:
            return {"metadata": None, "score": 0.0, "candidate_rank": None, "candidate_title": None}

        best_item: Optional[Dict[str, Any]] = None
        best_score = 0.0
        best_rank: Optional[int] = None
        best_title: Optional[str] = None
        for idx, item in enumerate(items, start=1):
            item_titles = item.get("title")
            item_title = item_titles[0] if isinstance(item_titles, list) and item_titles else (item_titles or "")
            score = self._title_similarity(title, item_title)
            if score > best_score:
                best_item = item
                best_score = score
                best_rank = idx
                best_title = item_title

        return {
            "metadata": best_item,
            "score": best_score,
            "candidate_rank": best_rank,
            "candidate_title": best_title,
        }

    def get_metadata(self, doi: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
        if doi:
            normalised_doi = self._normalise_doi(doi)
            if normalised_doi:
                response = self._request_with_retry(f"{self.BASE_URL}/{normalised_doi}")
                if response:
                    return {
                        "metadata": response.json().get("message"),
                        "matched_by": "doi",
                        "score": 1.0,
                        "candidate_rank": None,
                        "candidate_title": None,
                    }

        if title:
            title_result = self._search_by_title(title)
            metadata = title_result["metadata"]
            score = title_result["score"]
            if metadata and score >= self.title_match_threshold:
                return {
                    "metadata": metadata,
                    "matched_by": "title",
                    "score": score,
                    "candidate_rank": title_result.get("candidate_rank"),
                    "candidate_title": title_result.get("candidate_title"),
                }
            return {
                "metadata": None,
                "matched_by": "title",
                "score": score,
                "candidate_rank": title_result.get("candidate_rank"),
                "candidate_title": title_result.get("candidate_title"),
            }

        return {
            "metadata": None,
            "matched_by": "none",
            "score": 0.0,
            "candidate_rank": None,
            "candidate_title": None,
        }

    def _crossref_to_fields(self, crossref: Dict[str, Any]) -> Dict[str, Any]:
        title = None
        title_raw = crossref.get("title")
        if isinstance(title_raw, list) and title_raw:
            title = title_raw[0]
        elif isinstance(title_raw, str):
            title = title_raw

        journal = None
        container = crossref.get("container-title")
        if isinstance(container, list) and container:
            journal = container[0]
        elif isinstance(container, str):
            journal = container

        authors: List[str] = []
        for author in crossref.get("author") or []:
            given = (author.get("given") or "").strip()
            family = (author.get("family") or "").strip()
            full_name = f"{given} {family}".strip()
            if full_name:
                authors.append(full_name)

        year: Optional[str] = None
        for date_field in ("published-print", "published-online", "published", "issued"):
            if date_field in crossref:
                date_parts = crossref[date_field].get("date-parts")
                if isinstance(date_parts, list) and date_parts and date_parts[0]:
                    year = str(date_parts[0][0])
                    break

        return {
            "authors": authors,
            "title": title,
            "journal": journal,
            "volume": crossref.get("volume"),
            "issue": crossref.get("issue"),
            "pages": crossref.get("page"),
            "year": year,
            "doi": crossref.get("DOI"),
            "url": crossref.get("URL"),
        }

    def _compare_authors(self, provided: List[str], crossref_authors: List[str]) -> Dict[str, Any]:
        provided = provided or []
        crossref_authors = crossref_authors or []

        provided_set = {k for k in (self._author_key(a) for a in provided) if k}
        crossref_set = {k for k in (self._author_key(a) for a in crossref_authors) if k}

        provided_by_key: Dict[str, str] = {}
        for name in provided:
            key = self._author_key(name)
            if key and key not in provided_by_key:
                provided_by_key[key] = name

        crossref_by_key: Dict[str, str] = {}
        for name in crossref_authors:
            key = self._author_key(name)
            if key and key not in crossref_by_key:
                crossref_by_key[key] = name

        missing_keys = sorted(crossref_set - provided_set)
        extra_keys = sorted(provided_set - crossref_set)
        missing_names = [crossref_by_key[k] for k in missing_keys if k in crossref_by_key]
        extra_names = [provided_by_key[k] for k in extra_keys if k in provided_by_key]

        if self._is_missing(provided):
            state = "missing" if not self._is_missing(crossref_authors) else "correct"
            match = None
        elif self._is_missing(crossref_authors):
            state = "correct"
            match = None
        elif provided_set == crossref_set and provided_set:
            state = "correct"
            match = True
        elif provided_set.issubset(crossref_set):
            state = "missing"
            match = False
        else:
            state = "conflict" if "authors" in self.critical_fields else "incorrect"
            match = False

        return {
            "state": state,
            "provided": provided,
            "crossref": crossref_authors,
            "critical": "authors" in self.critical_fields,
            "match": match,
            "missing_from_provided": missing_names,
            "extra_in_provided": extra_names,
        }

    def _compare_scalar_field(self, field: str, provided: Any, crossref: Any) -> Dict[str, Any]:
        critical = field in self.critical_fields

        if self._is_missing(provided):
            state = "missing" if not self._is_missing(crossref) else "correct"
            return {
                "state": state,
                "provided": provided,
                "crossref": crossref,
                "critical": critical,
                "match": None,
            }

        if self._is_missing(crossref):
            return {
                "state": "correct",
                "provided": provided,
                "crossref": crossref,
                "critical": critical,
                "match": None,
            }

        if field == "doi":
            match = self._normalise_doi(provided) == self._normalise_doi(crossref)
        elif field == "title":
            match = self._normalise_text(provided) == self._normalise_text(crossref)
        elif field == "journal":
            match = self._journal_match(provided, crossref) is True
        elif field == "pages":
            match = self._normalise_pages(provided) == self._normalise_pages(crossref)
        elif field == "url":
            match = self._normalise_str(provided) == self._normalise_str(crossref)
        elif field in {"volume", "issue", "year"}:
            match = str(provided).strip() == str(crossref).strip()
        else:
            match = str(provided).strip() == str(crossref).strip()

        if match:
            state = "correct"
        else:
            state = "conflict" if critical else "incorrect"

        return {
            "state": state,
            "provided": provided,
            "crossref": crossref,
            "critical": critical,
            "match": match,
        }

    def assess_fields(self, article: Article, crossref_fields: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        assessment: Dict[str, Dict[str, Any]] = {}
        provided = article.provided_fields()
        for field in ALL_FIELDS:
            if field == "authors":
                assessment[field] = self._compare_authors(provided.get(field) or [], crossref_fields.get(field) or [])
            else:
                assessment[field] = self._compare_scalar_field(field, provided.get(field), crossref_fields.get(field))
        return assessment

    @staticmethod
    def _build_required_inputs(article: Article) -> List[str]:
        required: List[str] = []
        if not article.doi:
            required.append("DOI")
        if not article.title:
            required.append("full exact title")
        if not article.authors:
            required.append("full author list")
        if not article.journal:
            required.append("venue/journal name")
        if not article.year:
            required.append("publication year")
        if not required:
            required = ["DOI", "full exact title", "full author list", "venue/journal name", "publication year"]
        return required

    @staticmethod
    def _build_correction_patch(field_assessment: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        set_fields: Dict[str, Any] = {}
        unset_fields: List[str] = []

        for field, details in field_assessment.items():
            state = details.get("state")
            provided = details.get("provided")
            crossref = details.get("crossref")

            if state in {"missing", "incorrect", "conflict"} and crossref not in (None, "", []):
                set_fields[field] = crossref
            elif state in {"incorrect", "conflict"} and provided not in (None, "", []):
                unset_fields.append(field)

        return {"set": set_fields, "unset": sorted(set(unset_fields))}

    @staticmethod
    def _apply_patch_to_fields(article: Article, correction_patch: Dict[str, Any]) -> Dict[str, Any]:
        fields = article.provided_fields()
        for field in correction_patch.get("unset", []):
            fields[field] = [] if field == "authors" else None
        for field, value in correction_patch.get("set", {}).items():
            fields[field] = value

        if fields.get("doi") and not fields.get("url"):
            norm_doi = CrossrefChecker._normalise_doi(fields["doi"])
            if norm_doi:
                fields["url"] = f"https://doi.org/{norm_doi}"

        return fields

    @staticmethod
    def _render_canonical_text(fields: Dict[str, Any]) -> str:
        authors = fields.get("authors") or []
        authors_part = ", ".join(authors) if authors else "[missing authors]"
        title = fields.get("title") or "[missing title]"
        journal = fields.get("journal") or "[missing journal]"
        volume = fields.get("volume")
        issue = fields.get("issue")
        pages = fields.get("pages")
        year = fields.get("year")
        doi = fields.get("doi")
        url = fields.get("url")

        venue_parts: List[str] = [journal]
        if volume and issue:
            venue_parts.append(f"{volume}({issue})")
        elif volume:
            venue_parts.append(str(volume))
        elif issue:
            venue_parts.append(f"({issue})")
        if pages:
            venue_parts.append(str(pages))
        venue = ", ".join([p for p in venue_parts if p])
        if year:
            venue = f"{venue} ({year})"

        segments = [f'{authors_part}: "{title}."', venue]
        if doi:
            segments.append(f"doi:{CrossrefChecker._normalise_doi(doi) or doi}")
        if url:
            segments.append(str(url))

        return ". ".join([s for s in segments if s]).strip() + "."

    @classmethod
    def _render_tex_reference(cls, article: Article, fields: Dict[str, Any]) -> str:
        citation_key = article.bibitem_key or article.citation_id.replace(":", "_")
        lines: List[str] = [f"\\bibitem{{{citation_key}}}"]

        authors = fields.get("authors") or []
        title = fields.get("title")
        if authors and title:
            lines.append(f"{', '.join(authors)}: ``{title}.''")
        elif title:
            lines.append(f"``{title}.''")
        elif authors:
            lines.append(f"{', '.join(authors)}")

        journal = fields.get("journal")
        volume = fields.get("volume")
        issue = fields.get("issue")
        pages = fields.get("pages")
        year = fields.get("year")

        venue = ""
        if journal:
            venue = str(journal)
        if volume and issue:
            venue = f"{venue} {volume}({issue})".strip()
        elif volume:
            venue = f"{venue} {volume}".strip()
        elif issue:
            venue = f"{venue} ({issue})".strip()
        if pages:
            pages_tex = str(pages).replace("-", "--")
            venue = f"{venue}, {pages_tex}".strip(", ")
        if year:
            venue = f"{venue} ({year})".strip()
        if venue:
            lines.append(f"{venue}.")

        url = fields.get("url")
        doi = fields.get("doi")
        if not url and doi:
            norm_doi = cls._normalise_doi(doi)
            if norm_doi:
                url = f"https://doi.org/{norm_doi}"
        if url:
            lines.append(f"\\url{{{url}}}")

        return "\n".join(lines)

    @classmethod
    def _build_corrected_reference(cls, article: Article, fields: Dict[str, Any], emit: bool) -> Dict[str, Any]:
        fmt = article.source_format
        if not emit:
            return {"format": fmt, "text": ""}

        if fmt in {"tex", "bib"}:
            text = cls._render_tex_reference(article, fields)
        else:
            text = cls._render_canonical_text(fields)

        return {"format": fmt, "text": text}

    def _determine_status(self, field_assessment: Dict[str, Dict[str, Any]]) -> str:
        if any(details.get("critical") and details.get("state") == "conflict" for details in field_assessment.values()):
            return "critical_mismatch"
        if any(details.get("state") in {"missing", "incorrect"} for details in field_assessment.values()):
            return "corrected"
        return "match_found"

    def _build_result(
        self,
        article: Article,
        lookup: Dict[str, Any],
        status: str,
        field_assessment: Dict[str, Dict[str, Any]],
        correction_patch: Dict[str, Any],
        corrected_reference: Dict[str, Any],
        error: Optional[str] = None,
        required_user_inputs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        confidence: Dict[str, Any] = {}
        if lookup.get("score") is not None:
            confidence["title_score"] = lookup.get("score")
        if lookup.get("candidate_rank") is not None:
            confidence["candidate_rank"] = lookup.get("candidate_rank")

        result: Dict[str, Any] = {
            "citation_id": article.citation_id,
            "source_format": article.source_format,
            "status": status,
            "matched_by": lookup.get("matched_by") or "none",
            "confidence": confidence,
            "field_assessment": field_assessment,
            "correction_patch": correction_patch,
            "corrected_reference": corrected_reference,
            "required_user_inputs": required_user_inputs or [],
        }

        if error:
            result["error"] = error
        if lookup.get("candidate_title"):
            result["candidate_title"] = lookup.get("candidate_title")

        result["article"] = asdict(article)
        return result

    def check_articles(self, articles: List[Article]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        for article in articles:
            lookup = self.get_metadata(doi=article.doi, title=article.title)
            matched_by = lookup.get("matched_by") or "none"
            meta = lookup.get("metadata")

            if meta:
                crossref_fields = self._crossref_to_fields(meta)
                field_assessment = self.assess_fields(article, crossref_fields)
                correction_patch = self._build_correction_patch(field_assessment)
                corrected_fields = self._apply_patch_to_fields(article, correction_patch)
                corrected_reference = self._build_corrected_reference(article, corrected_fields, self.emit_corrected_reference)
                status = self._determine_status(field_assessment)

                results.append(
                    self._build_result(
                        article=article,
                        lookup={**lookup, "matched_by": matched_by},
                        status=status,
                        field_assessment=field_assessment,
                        correction_patch=correction_patch,
                        corrected_reference=corrected_reference,
                        error=(
                            "Critical mismatch in one or more required fields"
                            if status == "critical_mismatch"
                            else None
                        ),
                    )
                )
            else:
                fallback_assessment: Dict[str, Dict[str, Any]] = {}
                for field in ALL_FIELDS:
                    provided_value = article.provided_fields().get(field)
                    fallback_assessment[field] = {
                        "state": "missing" if self._is_missing(provided_value) else "correct",
                        "provided": provided_value,
                        "crossref": None,
                        "critical": field in self.critical_fields,
                        "match": None,
                    }

                unresolved_error = "No reliable Crossref match found"
                if matched_by == "title" and lookup.get("score", 0.0) < self.title_match_threshold:
                    unresolved_error = "Top title candidate is below confidence threshold"
                elif matched_by == "none":
                    unresolved_error = "Insufficient metadata for lookup"

                results.append(
                    self._build_result(
                        article=article,
                        lookup={**lookup, "matched_by": matched_by},
                        status="unresolved",
                        field_assessment=fallback_assessment,
                        correction_patch={"set": {}, "unset": []},
                        corrected_reference=self._build_corrected_reference(
                            article,
                            article.provided_fields(),
                            self.emit_corrected_reference,
                        ),
                        error=unresolved_error,
                        required_user_inputs=self._build_required_inputs(article),
                    )
                )

            time.sleep(1)

        return results


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def _split_authors_text(value: str) -> List[str]:
    raw = value.strip()
    if not raw:
        return []

    if ";" in raw:
        return [p.strip() for p in raw.split(";") if p.strip()]

    and_parts = [p.strip() for p in re.split(r"\s+and\s+", raw, flags=re.IGNORECASE) if p.strip()]
    if len(and_parts) > 1:
        return and_parts

    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) >= 2 and len(parts) % 2 == 0:
        family_like = parts[0::2]
        given_like = parts[1::2]
        can_pair = any("." in g or len(g.split()) <= 2 for g in given_like) and all(len(f.split()) <= 2 for f in family_like)
        if can_pair:
            return [f"{parts[i]}, {parts[i + 1]}" for i in range(0, len(parts), 2)]

    return [raw]


def load_articles_from_json(path: str) -> List[Article]:
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    if isinstance(data, dict) and isinstance(data.get("citations"), list):
        data = data["citations"]

    if not isinstance(data, list):
        raise ValueError("JSON input must be an array of citation objects.")

    articles: List[Article] = []
    for idx, entry in enumerate(data, start=1):
        if not isinstance(entry, dict):
            continue

        authors_raw = entry.get("authors")
        if isinstance(authors_raw, list):
            authors = [str(a).strip() for a in authors_raw if str(a).strip()]
        elif isinstance(authors_raw, str):
            authors = _split_authors_text(authors_raw)
        else:
            authors = []

        citation_id = str(entry.get("citation_id") or f"json:{idx}")
        articles.append(
            Article(
                citation_id=citation_id,
                source_format="json",
                raw_record=json.dumps(entry, ensure_ascii=False),
                title=entry.get("title"),
                authors=authors,
                journal=entry.get("journal"),
                volume=entry.get("volume"),
                issue=entry.get("issue"),
                pages=entry.get("pages"),
                year=str(entry.get("year")) if entry.get("year") is not None else None,
                doi=entry.get("doi"),
                url=entry.get("url"),
            )
        )

    return articles


def load_articles_from_csv(path: str) -> List[Article]:
    articles: List[Article] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            authors = _split_authors_text(row.get("authors") or "")
            citation_id = str(row.get("citation_id") or f"csv:{idx}")
            articles.append(
                Article(
                    citation_id=citation_id,
                    source_format="csv",
                    raw_record=json.dumps(row, ensure_ascii=False),
                    title=row.get("title"),
                    authors=authors,
                    journal=row.get("journal"),
                    volume=row.get("volume"),
                    issue=row.get("issue"),
                    pages=row.get("pages"),
                    year=row.get("year"),
                    doi=row.get("doi"),
                    url=row.get("url"),
                )
            )
    return articles


def _extract_title(text: str) -> Optional[str]:
    patterns = [
        r"``([^`]+)''",
        r"\"([^\"]+)\"",
        r"'([^']+)'",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip(" \n\t.,;:")

    colon_match = re.search(r":\s*([^.\n]+)\.", text)
    if colon_match:
        return colon_match.group(1).strip(" \n\t.,;:")

    sentence_match = re.search(r"([A-Za-z][^.\n]{10,})\.", text)
    if sentence_match:
        return sentence_match.group(1).strip(" \n\t.,;:")

    return None


def _extract_doi(text: str) -> Optional[str]:
    match = re.search(
        r"(?:doi:\s*|https?://(?:dx\.)?doi\.org/)(10\.\d{4,9}/[^\s\}\],;]+)",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip().rstrip(".,;")
    return None


def _extract_url(text: str) -> Optional[str]:
    url_match = re.search(r"\\url\{([^}]+)\}", text)
    if url_match:
        return url_match.group(1).strip()

    plain = re.search(r"https?://[^\s\}]+", text)
    if plain:
        return plain.group(0).strip().rstrip(".,;")

    return None


def _extract_year(text: str) -> Optional[str]:
    text_wo_urls = re.sub(r"\\url\{[^}]+\}", " ", text)
    text_wo_urls = re.sub(r"https?://[^\s\}]+", " ", text_wo_urls)
    text_wo_dois = re.sub(
        r"(?:doi:\s*)?10\.\d{4,9}/[^\s\}\],;]+",
        " ",
        text_wo_urls,
        flags=re.IGNORECASE,
    )

    years_in_parentheses = re.findall(r"\((19\d{2}|20\d{2})\)", text_wo_dois)
    if years_in_parentheses:
        return years_in_parentheses[-1]

    years = re.findall(r"\b(19\d{2}|20\d{2})\b", text_wo_dois)
    return years[-1] if years else None


def _extract_bibitem_key(text: str) -> Optional[str]:
    match = re.search(r"\\bibitem\s*\{([^}]+)\}", text)
    if not match:
        return None
    return match.group(1).strip()


def _extract_authors(text: str, title: Optional[str]) -> List[str]:
    prefix = text
    if title:
        title_pos = text.find(title)
        if title_pos > 0:
            prefix = text[:title_pos]

    if ":" in prefix:
        prefix = prefix.rsplit(":", 1)[0]

    prefix = re.sub(r"\\bibitem\s*\{[^}]+\}", "", prefix).strip(" \n\t,.;")
    if not prefix:
        return []

    prefix = prefix.replace(" and ", "; ")
    return _split_authors_text(prefix)


def _extract_journal(text: str, title: Optional[str]) -> Optional[str]:
    if not title:
        return None

    pos = text.find(title)
    if pos < 0:
        return None

    tail = text[pos + len(title) :]
    tail = re.sub(r"\\url\{[^}]+\}", "", tail)
    tail = re.sub(r"https?://[^\s\}]+", "", tail)
    tail = re.sub(r"\s+", " ", tail).strip(" \n\t,.;:-")
    if not tail:
        return None

    stop_tokens = [" doi:", " arxiv:", " arxiv preprint", " accessed:"]
    tail_lower = tail.lower()
    stop_positions = [tail_lower.find(tok) for tok in stop_tokens if tail_lower.find(tok) >= 0]
    if stop_positions:
        tail = tail[: min(stop_positions)].strip(" \n\t,.;:-")

    return tail or None


def _text_to_article(record: str, citation_id: str, source_format: str, bibitem_key: Optional[str]) -> Optional[Article]:
    rec = record.strip()
    if not rec:
        return None

    title = _extract_title(rec)
    doi = _extract_doi(rec)
    url = _extract_url(rec)
    year = _extract_year(rec)
    authors = _extract_authors(rec, title)
    journal = _extract_journal(rec, title)

    if not title and not doi:
        return None

    return Article(
        citation_id=citation_id,
        source_format=source_format,
        raw_record=record,
        bibitem_key=bibitem_key,
        title=title,
        authors=authors,
        journal=journal,
        year=year,
        doi=doi,
        url=url,
    )


def load_articles_from_text(path: str) -> List[Article]:
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()

    source_format = Path(path).suffix.lower().lstrip(".") or "txt"
    if source_format not in SUPPORTED_SOURCE_FORMATS:
        source_format = "txt"

    records: List[Tuple[str, str, Optional[str]]] = []
    bibitem_matches = list(re.finditer(r"\\bibitem\s*\{([^}]+)\}", text))
    if bibitem_matches:
        for idx, match in enumerate(bibitem_matches):
            start = match.start()
            end = bibitem_matches[idx + 1].start() if idx + 1 < len(bibitem_matches) else len(text)
            record = text[start:end].strip()
            key = match.group(1).strip()
            citation_id = key or f"{source_format}:{idx + 1}"
            records.append((citation_id, record, key))
    else:
        chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n+", text) if chunk.strip()]
        if len(chunks) == 1 and "\n" in chunks[0]:
            chunks = [line.strip() for line in text.splitlines() if line.strip()]
        for idx, rec in enumerate(chunks, start=1):
            records.append((f"{source_format}:{idx}", rec, None))

    articles: List[Article] = []
    for citation_id, rec, key in records:
        article = _text_to_article(rec, citation_id=citation_id, source_format=source_format, bibitem_key=key)
        if article:
            articles.append(article)

    return articles


def _parse_critical_fields(raw: str) -> List[str]:
    fields = [f.strip() for f in raw.split(",") if f.strip()]
    invalid = [f for f in fields if f not in ALL_FIELDS]
    if invalid:
        raise ValueError(f"Invalid critical fields: {', '.join(invalid)}")
    return fields


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate citations using Crossref and emit strict correction-ready results.")
    parser.add_argument("-i", "--input", required=True, help="Path to JSON, CSV, TXT, MD, TEX, or BIB file containing citation records")
    parser.add_argument("-o", "--output", help="Path to write the results JSON report")
    parser.add_argument("-e", "--email", help="Contact email to include in User-Agent")
    parser.add_argument(
        "--title-threshold",
        type=float,
        default=CrossrefChecker.DEFAULT_TITLE_MATCH_THRESHOLD,
        help="Minimum title similarity (0-1) required for title-search matches.",
    )
    parser.add_argument(
        "--schema-version",
        default="v2",
        choices=["v2"],
        help="Output schema version (v2).",
    )
    parser.add_argument(
        "--critical-fields",
        default=",".join(DEFAULT_CRITICAL_FIELDS),
        help="Comma-separated critical fields. Default: title,doi,authors,journal,year",
    )
    parser.add_argument(
        "--emit-corrected-reference",
        default="true",
        help="Whether to include corrected_reference text (true/false). Default: true",
    )
    args = parser.parse_args()

    ext = Path(args.input).suffix.lower().lstrip(".")
    if ext == "json":
        articles = load_articles_from_json(args.input)
    elif ext == "csv":
        articles = load_articles_from_csv(args.input)
    else:
        articles = load_articles_from_text(args.input)

    if not articles:
        raise ValueError("No parseable citations found in input.")

    critical_fields = _parse_critical_fields(args.critical_fields)
    emit_corrected_reference = _parse_bool(args.emit_corrected_reference)

    print(f"[crossref-checker] Input: {args.input}")
    print(f"[crossref-checker] Parsed citations: {len(articles)}")

    checker = CrossrefChecker(
        email=args.email,
        title_match_threshold=args.title_threshold,
        critical_fields=critical_fields,
        emit_corrected_reference=emit_corrected_reference,
        schema_version=args.schema_version,
    )
    results = checker.check_articles(articles)

    status_counts = {"match_found": 0, "corrected": 0, "critical_mismatch": 0, "unresolved": 0}
    for item in results:
        status = item.get("status")
        if status in status_counts:
            status_counts[status] += 1

    print(
        "[crossref-checker] Summary: "
        f"match_found={status_counts['match_found']}, "
        f"corrected={status_counts['corrected']}, "
        f"critical_mismatch={status_counts['critical_mismatch']}, "
        f"unresolved={status_counts['unresolved']}"
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as out:
            json.dump(results, out, indent=2, ensure_ascii=False)
        print(f"[crossref-checker] Output written: {args.output}")
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

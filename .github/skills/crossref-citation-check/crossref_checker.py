"""
crossref_checker.py
====================

This module provides a simple command-line tool and Python API for validating
bibliographic information about scholarly articles using Crossref's free
REST API. It is designed to help authors, librarians and developers verify
that a given citation is complete and accurate by comparing the supplied
metadata against authoritative data returned by Crossref.

Key features:

* Query Crossref by DOI (preferred) or by title when a DOI is unavailable.
* Retrieve essential metadata fields such as title, authors, journal name,
  volume, issue, pages, publication year, DOI and URL.
* Compare supplied values to Crossref's response and flag discrepancies.
* Accept input in JSON, CSV, plain text, and LaTeX bibliography snippets.
  CSV files should have column headers matching metadata keys (e.g.
  ``title``, ``authors``, ``journal``, ``volume``); multiple authors
  should be separated by semicolons.
* Optional polite ``User-Agent`` header via a ``--email`` flag to comply
  with Crossref's etiquette recommendations.

Example usage:

.. code-block:: bash

   # Validate citations stored in citations.json and print the report
   python crossref_checker.py --input citations.json

   # Validate citations from a CSV file and save the report to results.json
   python crossref_checker.py -i citations.csv -o results.json -e you@example.com

   # Validate free-text or LaTeX bibliography entries
   python crossref_checker.py -i references.tex -o results.json

In both cases, the script outputs a list of results with a top-level
``status`` field (``match_found``, ``no_likely_match``, or ``no_match``).
For ``match_found`` results, a ``comparison`` dictionary is included. For
unsuccessful lookups, an ``error`` message is included.

Note: The Crossref API enforces rate limits. This script includes a
small delay between requests to avoid hitting those limits. For large
datasets, consider caching results or requesting a polite rate limit
increase from Crossref.

"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

import requests


@dataclass
class Article:
    """Representation of a bibliographic record provided by the user.

    The ``authors`` attribute should be a list of strings (e.g. ``["John Doe", "Jane Smith"]``).
    Other attributes are optional and may be ``None`` if unknown.
    """

    title: Optional[str] = None
    authors: Optional[List[str]] = field(default_factory=list)
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    year: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None


class CrossrefChecker:
    """A client for validating article metadata against the Crossref REST API."""

    BASE_URL = "https://api.crossref.org/works"
    SEARCH_ROWS = 5
    DEFAULT_TITLE_MATCH_THRESHOLD = 0.85

    def __init__(self, email: Optional[str] = None, title_match_threshold: float = DEFAULT_TITLE_MATCH_THRESHOLD) -> None:
        """Initialise the Crossref checker.

        Parameters
        ----------
        email : str, optional
            Contact email to include in the User-Agent header. Supplying
            a contact address is considered good practice and may improve
            the reliability of requests.
        """
        user_agent = "CrossrefCitationChecker/1.0"
        if email:
            user_agent = f"{user_agent} (mailto:{email})"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.title_match_threshold = title_match_threshold

    @staticmethod
    def _normalise_doi(value: Optional[str]) -> Optional[str]:
        """Normalise DOI values from formats like doi:... or https://doi.org/..."""
        if not value:
            return None
        doi = value.strip()
        doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
        doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
        doi = doi.strip().rstrip(".,;")
        return doi.lower() if doi else None

    @staticmethod
    def _normalise_text(value: Optional[str]) -> Optional[str]:
        """Normalise text for tolerant title/journal matching."""
        if value is None:
            return None
        return re.sub(r"[^a-z0-9]+", "", value.strip().lower())

    @staticmethod
    def _normalise_pages(value: Optional[str]) -> Optional[str]:
        """Normalise page ranges, unifying dash styles and whitespace."""
        if value is None:
            return None
        page = value.replace("\u2013", "-").replace("\u2014", "-")
        page = re.sub(r"\s+", "", page)
        return page

    @classmethod
    def _journal_match(cls, provided_journal: Optional[str], crossref_journal: Optional[str]) -> Optional[bool]:
        """Match journals with tolerance for abbreviations and punctuation."""
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
        p_tokens = re.findall(r"[a-z0-9]+", provided_journal.lower())
        c_tokens = re.findall(r"[a-z0-9]+", crossref_journal.lower())
        c_tokens_filtered = [t for t in c_tokens if t not in {"the", "of", "and", "for", "in", "on"}]
        if p_tokens and c_tokens_filtered:
            # Abbreviation-friendly rule: every provided token should match a crossref token by
            # exact equality or prefix relation in either direction.
            token_hits = [
                any(ct == pt or ct.startswith(pt) or pt.startswith(ct) for ct in c_tokens_filtered)
                for pt in p_tokens
            ]
            if all(token_hits):
                return True
        return cls._title_similarity(provided_journal, crossref_journal) >= 0.78

    @classmethod
    def _title_similarity(cls, left: Optional[str], right: Optional[str]) -> float:
        """Compute normalised similarity score between two titles."""
        l = cls._normalise_text(left) or ""
        r = cls._normalise_text(right) or ""
        if not l or not r:
            return 0.0
        return SequenceMatcher(None, l, r).ratio()

    def _request_with_retry(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[requests.Response]:
        """Request Crossref with basic retries/backoff for transient failures."""
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
        """Search Crossref by title and return best candidate with similarity score."""
        params = {"query.bibliographic": title, "rows": self.SEARCH_ROWS}
        response = self._request_with_retry(self.BASE_URL, params=params)
        if not response:
            return {"metadata": None, "score": 0.0}
        data = response.json()
        items = data.get("message", {}).get("items", [])
        if not items:
            return {"metadata": None, "score": 0.0}

        best_item = None
        best_score = 0.0
        for item in items:
            item_titles = item.get("title")
            item_title = item_titles[0] if isinstance(item_titles, list) and item_titles else (item_titles or "")
            score = self._title_similarity(title, item_title)
            if score > best_score:
                best_item = item
                best_score = score
        return {"metadata": best_item, "score": best_score}

    def get_metadata(self, doi: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve bibliographic metadata from Crossref by DOI or title.

        When a DOI is supplied, the API is queried directly via ``/works/{doi}``.
        Otherwise, a title search is performed using the ``query.bibliographic``
        parameter, returning the first match.

        Parameters
        ----------
        doi : str, optional
            Digital Object Identifier for the article.
        title : str, optional
            The article title to search for. Only used when ``doi`` is ``None``.

        Returns
        -------
        dict
            A lookup result dictionary with keys:
            - ``metadata``: Crossref ``message`` object or ``None``
            - ``matched_by``: ``"doi"``, ``"title"``, or ``None``
            - ``score``: confidence score (1.0 for DOI matches)
            - ``candidate_title``: optional low-confidence title candidate
        """
        if doi:
            normalised_doi = self._normalise_doi(doi)
            if normalised_doi:
                url = f"{self.BASE_URL}/{normalised_doi}"
                response = self._request_with_retry(url)
                if response:
                    data = response.json()
                    return {"metadata": data.get("message"), "matched_by": "doi", "score": 1.0}
        if title:
            title_result = self._search_by_title(title)
            metadata = title_result["metadata"]
            score = title_result["score"]
            if metadata and score >= self.title_match_threshold:
                return {"metadata": metadata, "matched_by": "title", "score": score}
            if metadata:
                return {"metadata": None, "matched_by": "title", "score": score, "candidate_title": (metadata.get("title") or [""])[0]}
        return {"metadata": None, "matched_by": None, "score": 0.0}

    @staticmethod
    def _normalise_str(value: Optional[str]) -> Optional[str]:
        """Normalise a string for comparison by stripping whitespace and lowering case."""
        if value is None:
            return None
        return value.strip().lower()

    @staticmethod
    def _author_key(name: str) -> Optional[str]:
        """Build a tolerant author key using family name + first given initial."""
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

    def compare(self, provided: Article, crossref: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Compare user-provided article metadata against Crossref's record.

        The comparison attempts to match various fields (title, authors, journal,
        volume, issue, pages, year, DOI, and URL). Each entry in the returned
        dictionary contains the provided value, the Crossref value, and a
        boolean ``match`` flag indicating whether they are equal (case-insensitive
        for strings).

        Parameters
        ----------
        provided : Article
            The citation supplied by the user.
        crossref : dict
            The metadata retrieved from Crossref for the article.

        Returns
        -------
        dict
            A nested dictionary keyed by field name. Each value includes
            ``provided``, ``crossref``, and ``match`` (``true``/``false``/
            ``null`` when the field is missing in the provided citation).
            The ``authors`` field also includes ``missing_from_provided`` and
            ``extra_in_provided`` diagnostics.
        """
        result: Dict[str, Dict[str, Any]] = {}

        def record(field: str, provided_value: Any, crossref_value: Any, normalise: bool = True) -> None:
            """Helper to populate the result dictionary for a single field."""
            if provided_value is None or provided_value == "" or provided_value == []:
                match = None
            elif normalise and isinstance(provided_value, str) and isinstance(crossref_value, str):
                pv = self._normalise_text(provided_value)
                cv = self._normalise_text(crossref_value)
                match = (pv == cv) if pv is not None and cv is not None else False
            else:
                match = provided_value == crossref_value
            result[field] = {
                "provided": provided_value,
                "crossref": crossref_value,
                "match": match,
            }

        # Title comparison (Crossref returns a list of titles)
        crossref_title = None
        crossref_titles = crossref.get("title")
        if isinstance(crossref_titles, list) and crossref_titles:
            crossref_title = crossref_titles[0]
        elif isinstance(crossref_titles, str):
            crossref_title = crossref_titles
        record("title", provided.title, crossref_title)

        # Journal name (container-title may be a list)
        crossref_journal = None
        ctitle = crossref.get("container-title")
        if isinstance(ctitle, list) and ctitle:
            crossref_journal = ctitle[0]
        elif isinstance(ctitle, str):
            crossref_journal = ctitle
        result["journal"] = {
            "provided": provided.journal,
            "crossref": crossref_journal,
            "match": self._journal_match(provided.journal, crossref_journal),
        }

        # Authors: compare as normalized keys for order-independent matching
        provided_authors = provided.authors or []
        provided_set = {k for a in provided_authors if a for k in [self._author_key(a)] if k}
        crossref_authors_data = crossref.get("author") or []
        crossref_names: List[str] = []
        for author in crossref_authors_data:
            given = (author.get("given") or "").strip()
            family = (author.get("family") or "").strip()
            full_name = f"{given} {family}".strip()
            if full_name:
                crossref_names.append(full_name)
        crossref_set = {k for n in crossref_names if n for k in [self._author_key(n)] if k}
        # Determine match (treat provided list as a valid subset when present)
        authors_match = None if not provided_set else provided_set.issubset(crossref_set)
        crossref_by_key: Dict[str, List[str]] = {}
        for n in crossref_names:
            k = self._author_key(n)
            if not k:
                continue
            crossref_by_key.setdefault(k, []).append(n)
        provided_by_key: Dict[str, List[str]] = {}
        for n in provided_authors:
            k = self._author_key(n)
            if not k:
                continue
            provided_by_key.setdefault(k, []).append(n)
        missing_keys = sorted(crossref_set - provided_set) if provided_set else []
        extra_keys = sorted(provided_set - crossref_set) if provided_set else []
        missing_names = [crossref_by_key[k][0] for k in missing_keys if k in crossref_by_key]
        extra_names = [provided_by_key[k][0] for k in extra_keys if k in provided_by_key]
        result["authors"] = {
            "provided": provided_authors,
            "crossref": crossref_names,
            "match": authors_match,
            "missing_from_provided": missing_names,
            "extra_in_provided": extra_names,
        }

        # Volume, issue, pages
        record("volume", provided.volume, crossref.get("volume"), normalise=False)
        record("issue", provided.issue, crossref.get("issue"), normalise=False)
        # Crossref uses 'page' for pages
        provided_pages = self._normalise_pages(provided.pages)
        crossref_pages = self._normalise_pages(crossref.get("page"))
        result["pages"] = {
            "provided": provided.pages,
            "crossref": crossref.get("page"),
            "match": None if not provided_pages else bool(crossref_pages and provided_pages == crossref_pages),
        }

        # Publication year: attempt to extract from 'published-print' or 'published-online'
        crossref_year: Optional[str] = None
        for date_field in ("published-print", "published-online", "published", "issued"):
            if date_field in crossref:
                date_parts = crossref[date_field].get("date-parts")
                if isinstance(date_parts, list) and date_parts and date_parts[0]:
                    # date-parts is a list of lists: [[year, month, day]]
                    crossref_year = str(date_parts[0][0])
                    break
        record("year", provided.year, crossref_year, normalise=False)

        # DOI and URL (case-insensitive for DOI; URL will also be compared case-insensitively as a string)
        provided_doi = self._normalise_doi(provided.doi)
        crossref_doi = self._normalise_doi(crossref.get("DOI"))
        result["doi"] = {
            "provided": provided.doi,
            "crossref": crossref.get("DOI"),
            "match": None if not provided_doi else bool(crossref_doi and provided_doi == crossref_doi),
        }
        provided_url = self._normalise_str(provided.url)
        crossref_url = self._normalise_str(crossref.get("URL"))
        result["url"] = {
            "provided": provided.url,
            "crossref": crossref.get("URL"),
            "match": None if not provided_url else bool(crossref_url and provided_url == crossref_url),
        }

        return result

    def check_articles(self, articles: List[Article]) -> List[Dict[str, Any]]:
        """Validate a list of articles against Crossref and return comparison results.

        Parameters
        ----------
        articles : list of Article
            Articles to be validated. At least ``title`` or ``doi`` should be provided for each article.

        Returns
        -------
        list of dict
            Each entry contains the original article data plus a ``status`` key.
            ``match_found`` entries include ``comparison``; non-matches include
            an ``error`` message and optional match diagnostics.
        """
        results: List[Dict[str, Any]] = []
        for article in articles:
            lookup = self.get_metadata(doi=article.doi, title=article.title)
            meta = lookup.get("metadata")
            if meta:
                comparison = self.compare(article, meta)
                results.append(
                    {
                        "article": article.__dict__,
                        "comparison": comparison,
                        "status": "match_found",
                        "matched_by": lookup.get("matched_by"),
                        "title_score": lookup.get("score"),
                    }
                )
            elif lookup.get("matched_by") == "title":
                results.append(
                    {
                        "article": article.__dict__,
                        "status": "no_likely_match",
                        "title_score": lookup.get("score"),
                        "candidate_title": lookup.get("candidate_title"),
                        "error": "Top title candidate is below confidence threshold",
                    }
                )
            else:
                results.append({"article": article.__dict__, "status": "no_match", "error": "No match found"})
            # Respect Crossref rate limits: a short delay between requests
            time.sleep(1)
        return results


def load_articles_from_json(path: str) -> List[Article]:
    """Load a list of articles from a JSON file.

    The file should contain a JSON array where each element is an object with
    keys corresponding to the Article fields (e.g. ``"title"``, ``"authors"``, ``"journal"``, etc.).

    Parameters
    ----------
    path : str
        Path to the JSON file.

    Returns
    -------
    list of Article
        A list of ``Article`` instances.
    """
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    articles: List[Article] = []
    for entry in data:
        # Ensure authors is a list
        authors = entry.get("authors")
        if isinstance(authors, str):
            # Split comma or semicolon separated strings
            authors_list = [a.strip() for a in authors.replace(";", ",").split(",") if a.strip()]
        elif isinstance(authors, list):
            authors_list = authors
        else:
            authors_list = []
        articles.append(
            Article(
                title=entry.get("title"),
                authors=authors_list,
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
    """Load a list of articles from a CSV file.

    The CSV must contain a header row with field names matching the Article
    attributes. Authors should be separated by semicolons (``;``) or commas.

    Parameters
    ----------
    path : str
        Path to the CSV file.

    Returns
    -------
    list of Article
        A list of ``Article`` instances.
    """
    import csv
    articles: List[Article] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            authors_raw = row.get("authors") or ""
            # Replace semicolons with commas to unify splitting, then split
            authors_list = [a.strip() for a in authors_raw.replace(";", ",").split(",") if a.strip()]
            articles.append(
                Article(
                    title=row.get("title"),
                    authors=authors_list,
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
    """Extract a title from common citation quote styles."""
    patterns = [
        r"``([^`]+)''",
        r"\"([^\"]+)\"",
        r"'([^']+)'",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip(" \n\t.,;:")
    # Fallback for unquoted titles, e.g. "Author, A.: Title of Work."
    colon_match = re.search(r":\s*([^.\n]+)\.", text)
    if colon_match:
        return colon_match.group(1).strip(" \n\t.,;:")
    # Last-resort fallback: first sentence with enough lexical content.
    sentence_match = re.search(r"([A-Za-z][^.\n]{10,})\.", text)
    if sentence_match:
        return sentence_match.group(1).strip(" \n\t.,;:")
    return None


def _extract_doi(text: str) -> Optional[str]:
    """Extract a DOI from url/doi formats."""
    match = re.search(
        r"(?:doi:\s*|https?://(?:dx\.)?doi\.org/)(10\.\d{4,9}/[^\s\}\],;]+)",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip().rstrip(".,;")
    return None


def _extract_url(text: str) -> Optional[str]:
    """Extract URL from \\url{...} or plain URLs."""
    url_match = re.search(r"\\url\{([^}]+)\}", text)
    if url_match:
        return url_match.group(1).strip()
    plain = re.search(r"https?://[^\s\}]+", text)
    if plain:
        return plain.group(0).strip().rstrip(".,;")
    return None


def _extract_year(text: str) -> Optional[str]:
    """Extract publication year from citation text."""
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
    return years[-1] if years else None


def _extract_authors(text: str, title: Optional[str]) -> List[str]:
    """Extract likely author list from citation text."""
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
    prefix = prefix.replace(" and ", ", ")
    return [a.strip() for a in prefix.split(",") if a.strip()]


def _extract_journal(text: str, title: Optional[str]) -> Optional[str]:
    """Extract a likely venue/journal fragment after title."""
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


def _text_to_article(record: str) -> Optional[Article]:
    """Parse one free-text citation record into an Article."""
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
        title=title,
        authors=authors,
        journal=journal,
        year=year,
        doi=doi,
        url=url,
    )


def load_articles_from_text(path: str) -> List[Article]:
    """Load citations from plain text or LaTeX bibliography files."""
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    records: List[str] = []

    bibitem_matches = list(re.finditer(r"\\bibitem\s*\{[^}]+\}", text))
    if bibitem_matches:
        for idx, match in enumerate(bibitem_matches):
            start = match.start()
            end = bibitem_matches[idx + 1].start() if idx + 1 < len(bibitem_matches) else len(text)
            records.append(text[start:end].strip())
    else:
        records = [chunk.strip() for chunk in re.split(r"\n\s*\n+", text) if chunk.strip()]
        if len(records) == 1 and "\n" in records[0]:
            # Fallback: one citation per line if no blank-line separation.
            line_records = [line.strip() for line in text.splitlines() if line.strip()]
            if len(line_records) > 1:
                records = line_records

    articles: List[Article] = []
    for rec in records:
        article = _text_to_article(rec)
        if article:
            articles.append(article)
    return articles


def main() -> None:
    """Entry point for the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Validate a list of scholarly citations using Crossref's REST API."
    )
    parser.add_argument(
        "-i", "--input", required=True, help="Path to JSON, CSV, TXT, MD, TEX, or BIB file containing citation records"
    )
    parser.add_argument(
        "-o", "--output", help="Path to write the results JSON report"
    )
    parser.add_argument(
        "-e",
        "--email",
        help=(
            "Contact email to include in the User-Agent header. "
            "Providing an email is recommended for polite API usage."
        ),
    )
    parser.add_argument(
        "--title-threshold",
        type=float,
        default=CrossrefChecker.DEFAULT_TITLE_MATCH_THRESHOLD,
        help="Minimum title similarity (0-1) required for title-search matches.",
    )
    args = parser.parse_args()

    # Load articles from the specified input file
    ext = args.input.split(".")[-1].lower()
    if ext == "json":
        articles = load_articles_from_json(args.input)
    elif ext == "csv":
        articles = load_articles_from_csv(args.input)
    elif ext in {"txt", "md", "tex", "bib"}:
        articles = load_articles_from_text(args.input)
    else:
        # Best-effort fallback: try plain-text parsing for unknown extensions.
        articles = load_articles_from_text(args.input)

    if not articles:
        raise ValueError("No parseable citations found in input.")

    checker = CrossrefChecker(email=args.email, title_match_threshold=args.title_threshold)
    results = checker.check_articles(articles)

    # Write or print the results
    if args.output:
        with open(args.output, "w", encoding="utf-8") as out:
            json.dump(results, out, indent=2, ensure_ascii=False)
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()


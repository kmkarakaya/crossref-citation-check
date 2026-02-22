import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_DIR = Path(__file__).resolve().parents[1] / ".github" / "skills" / "crossref-citation-check"
sys.path.insert(0, str(SKILL_DIR))

import crossref_checker as cc


def _candidate(fields, composite, title=1.0, authors=1.0, journal=1.0, year=1.0, query="bibliographic", query_score=100.0):
    return {
        "metadata": {"DOI": fields.get("doi"), "title": [fields.get("title") or ""], "score": query_score},
        "matched_by_query": query,
        "query_score": query_score,
        "fields": fields,
        "component_scores": {"title": title, "authors": authors, "journal": journal, "year": year},
        "composite_score": composite,
    }


class CrossrefCheckerV21Tests(unittest.TestCase):
    def test_extract_year_ignores_year_like_doi_digits(self):
        text = (
            "Savuran, H., Karakaya, M.: ``Efficient Route Planning for an Unmanned Air Vehicle "
            "Deployed on a Moving Carrier.'' Soft Computing 20(7), 2905--2920 (2016). "
            "\\url{https://doi.org/10.1007/s00500-015-1970-4}"
        )
        self.assertEqual(cc._extract_year(text), "2016")

    def test_extract_authors_groups_family_given_pairs(self):
        text = (
            "\\bibitem{paper:2}\n"
            "Sengul, Gokhan, Karakaya, Murat, Misra, Sanjay, Abayomi-Alli, Olusola O., Damasevicius, Robertas:\n"
            "``Deep learning based fall detection using smartwatches for healthcare applications.''"
        )
        title = "Deep learning based fall detection using smartwatches for healthcare applications"
        self.assertEqual(
            cc._extract_authors(text, title),
            [
                "Sengul, Gokhan",
                "Karakaya, Murat",
                "Misra, Sanjay",
                "Abayomi-Alli, Olusola O.",
                "Damasevicius, Robertas",
            ],
        )

    def test_missing_doi_correct_title_authors_autofills(self):
        class DummyChecker(cc.CrossrefChecker):
            def get_metadata(self, doi=None, title=None):
                return {
                    "metadata": {
                        "title": [title],
                        "container-title": ["Biomedical Signal Processing and Control"],
                        "author": [{"given": "Gokhan", "family": "Sengul"}, {"given": "Murat", "family": "Karakaya"}],
                        "issued": {"date-parts": [[2022]]},
                        "DOI": "10.1016/j.bspc.2021.103242",
                        "URL": "https://doi.org/10.1016/j.bspc.2021.103242",
                    },
                    "matched_by": "title",
                    "score": 0.95,
                    "candidate_rank": 1,
                    "candidate_title": title,
                }

        article = cc.Article(
            citation_id="x1",
            source_format="txt",
            title="Deep learning based fall detection using smartwatches for healthcare applications",
            authors=["Sengul, Gokhan", "Karakaya, Murat"],
            journal="Biomedical Signal Processing and Control",
            year="2022",
            doi=None,
        )
        checker = DummyChecker()
        fields = {
            "title": article.title,
            "authors": ["Gokhan Sengul", "Murat Karakaya"],
            "journal": article.journal,
            "year": "2022",
            "doi": "10.1016/j.bspc.2021.103242",
            "url": "https://doi.org/10.1016/j.bspc.2021.103242",
            "volume": "71",
            "issue": None,
            "pages": "103242",
        }
        with patch("crossref_checker.time.sleep", return_value=None), patch.object(
            DummyChecker, "_collect_ranked_candidates", return_value=[_candidate(fields, 0.96)]
        ):
            result = checker.check_articles([article])[0]
        self.assertEqual(result["status"], "corrected")
        self.assertIn("doi", result["correction_patch"]["set"])
        self.assertFalse(result["selection_required"])

    def test_noisy_title_but_strong_authors_journal_year_can_rank_high(self):
        checker = cc.CrossrefChecker()
        article = cc.Article(
            citation_id="n1",
            source_format="txt",
            title="Analyzing students Academic Success in Prerequisite Chains",
            authors=["Murat Karakaya", "M. Eryilmaz", "U. O. Ceyhan"],
            journal="International Journal of Engineering Education",
            year="2018",
        )
        fields = {
            "title": "Analyzing students' Academic Success in Prerequisite Course Chains",
            "authors": ["Murat Karakaya", "M. Eryilmaz", "U. O. Ceyhan"],
            "journal": "International Journal of Engineering Education",
            "year": "2018",
            "doi": "10.1234/example",
            "url": "https://doi.org/10.1234/example",
            "volume": None,
            "issue": None,
            "pages": None,
        }
        scores = checker._candidate_component_scores(article, fields)
        composite = checker._candidate_composite_score(article, scores)
        self.assertGreater(scores["authors"], 0.9)
        self.assertGreater(scores["journal"], 0.9)
        self.assertEqual(scores["year"], 1.0)
        self.assertGreater(composite, 0.85)

    def test_ambiguous_top_two_requires_selection(self):
        article = cc.Article(
            citation_id="x2",
            source_format="txt",
            title="Some noisy title",
            authors=["Karakaya, M."],
        )
        checker = cc.CrossrefChecker()
        c1 = _candidate(
            {"title": "Candidate One", "authors": ["Murat Karakaya"], "journal": "J1", "year": "2018", "doi": "10.1/one", "url": "https://doi.org/10.1/one", "volume": None, "issue": None, "pages": None},
            0.90,
            title=0.9,
        )
        c2 = _candidate(
            {"title": "Candidate Two", "authors": ["Murat Karakaya"], "journal": "J2", "year": "2018", "doi": "10.1/two", "url": "https://doi.org/10.1/two", "volume": None, "issue": None, "pages": None},
            0.86,
            title=0.88,
        )
        with patch("crossref_checker.time.sleep", return_value=None), patch.object(
            cc.CrossrefChecker, "get_metadata", return_value={"metadata": None, "matched_by": "title", "score": 0.5, "candidate_rank": 1, "candidate_title": "x"}
        ), patch.object(cc.CrossrefChecker, "_collect_ranked_candidates", return_value=[c1, c2]):
            result = checker.check_articles([article])[0]
        self.assertEqual(result["status"], "unresolved")
        self.assertTrue(result["selection_required"])
        self.assertEqual(result["selection_reason"], "ambiguous_top2")
        self.assertEqual(len(result["candidate_matches"]), 2)

    def test_doi_conflict_requires_selection_and_is_critical(self):
        article = cc.Article(
            citation_id="x3",
            source_format="txt",
            title="Wrong title",
            authors=["Savuran, Halil"],
            doi="10.1016/j.engappai.2024.109337",
        )
        checker = cc.CrossrefChecker()
        top_fields = {
            "title": "Another article",
            "authors": ["Gokhan Sengul", "Murat Karakaya"],
            "journal": "Biomedical Signal Processing and Control",
            "year": "2022",
            "doi": "10.1016/j.bspc.2021.103242",
            "url": "https://doi.org/10.1016/j.bspc.2021.103242",
            "volume": "71",
            "issue": None,
            "pages": "103242",
        }
        with patch("crossref_checker.time.sleep", return_value=None), patch.object(
            cc.CrossrefChecker,
            "get_metadata",
            return_value={
                "metadata": {
                    "title": ["Different DOI title"],
                    "container-title": ["Engineering Applications of Artificial Intelligence"],
                    "author": [{"given": "Halil", "family": "Savuran"}],
                    "issued": {"date-parts": [[2024]]},
                    "DOI": "10.1016/j.engappai.2024.109337",
                    "URL": "https://doi.org/10.1016/j.engappai.2024.109337",
                },
                "matched_by": "doi",
                "score": 1.0,
                "candidate_rank": None,
                "candidate_title": None,
            },
        ), patch.object(cc.CrossrefChecker, "_collect_ranked_candidates", return_value=[_candidate(top_fields, 0.94)]):
            result = checker.check_articles([article])[0]
        self.assertEqual(result["status"], "critical_mismatch")
        self.assertTrue(result["selection_required"])
        self.assertEqual(result["selection_reason"], "doi_conflict_review")
        self.assertTrue(result["doi_conflict"])

    def test_selection_map_rank_is_applied(self):
        article = cc.Article(
            citation_id="paper:4",
            source_format="txt",
            title="Analyzing students' Academic Success in Prerequisite Course Chains",
            authors=["Murat Karakaya", "M. Eryilmaz", "U. O. Ceyhan"],
            year="2018",
        )
        checker = cc.CrossrefChecker(selection_map={"paper:4": 2})
        c1 = _candidate(
            {"title": "Less suitable", "authors": ["A B"], "journal": "J1", "year": "2018", "doi": "10.1/less", "url": "https://doi.org/10.1/less", "volume": None, "issue": None, "pages": None},
            0.79,
        )
        c2 = _candidate(
            {"title": "Analyzing students' Academic Success in Prerequisite Course Chains", "authors": ["Murat Karakaya", "M. Eryilmaz", "U. O. Ceyhan"], "journal": "International Journal of Engineering Education", "year": "2018", "doi": "10.9999/real", "url": "https://doi.org/10.9999/real", "volume": "34", "issue": "2A", "pages": "364-370"},
            0.91,
        )
        with patch("crossref_checker.time.sleep", return_value=None), patch.object(
            cc.CrossrefChecker, "get_metadata", return_value={"metadata": None, "matched_by": "title", "score": 0.3, "candidate_rank": 1, "candidate_title": "x"}
        ), patch.object(cc.CrossrefChecker, "_collect_ranked_candidates", return_value=[c1, c2]):
            result = checker.check_articles([article])[0]
        self.assertEqual(result["selected_candidate_rank"], 2)
        self.assertIn("doi", result["correction_patch"]["set"])
        self.assertIn("journal", result["correction_patch"]["set"])
        self.assertIn(result["status"], {"corrected", "match_found"})

    def test_candidate_dedup_by_doi(self):
        article = cc.Article(citation_id="d1", source_format="txt", title="x")
        checker = cc.CrossrefChecker(candidate_rows=6)
        dmeta = {"DOI": "10.1/dup", "title": ["Same"]}
        with patch.object(
            cc.CrossrefChecker,
            "_query_candidates",
            side_effect=[
                [{"metadata": dmeta, "matched_by_query": "bibliographic", "query_score": 100.0}],
                [{"metadata": {"DOI": "10.1/dup", "title": ["Same"]}, "matched_by_query": "title", "query_score": 120.0}],
                [],
            ],
        ):
            ranked = checker._collect_ranked_candidates(article)
        self.assertEqual(len(ranked), 1)

    def test_integration_tex_and_txt_parsing(self):
        tex_content = (
            "\\begin{thebibliography}{1}\n"
            "\\bibitem{paper:4}\n"
            "Murat Karakaya, M. Eryilmaz, and U. O. Ceyhan: ``Analyzing students' Academic Success in Prerequisite Course Chains.''\n"
            "International Journal of Engineering Education 34(2A), 364--370 (2018).\n"
            "\\end{thebibliography}\n"
        )
        txt_content = (
            "Murat Karakaya, M. Eryilmaz, and U. O. Ceyhan:\n"
            "\"Analyzing students' Academic Success in Prerequisite Course Chains.\"\n"
            "International Journal of Engineering Education 34(2A), 364--370 (2018).\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".tex", delete=False, encoding="utf-8") as t:
            t.write(tex_content)
            tex_path = t.name
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as t:
            t.write(txt_content)
            txt_path = t.name
        tex_articles = cc.load_articles_from_text(tex_path)
        txt_articles = cc.load_articles_from_text(txt_path)
        self.assertEqual(tex_articles[0].source_format, "tex")
        self.assertEqual(txt_articles[0].source_format, "txt")


if __name__ == "__main__":
    unittest.main()

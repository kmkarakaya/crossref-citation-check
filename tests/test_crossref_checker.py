import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_DIR = Path(__file__).resolve().parents[1] / ".github" / "skills" / "crossref-citation-check"
sys.path.insert(0, str(SKILL_DIR))

import crossref_checker as cc


class CrossrefCheckerV2Tests(unittest.TestCase):
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

    def test_doi_title_conflict_becomes_critical_mismatch(self):
        class DummyChecker(cc.CrossrefChecker):
            def get_metadata(self, doi=None, title=None):
                return {
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
                }

        article = cc.Article(
            citation_id="x1",
            source_format="txt",
            title="A novel solution for routing a swarm of drones operated on a mobile host",
            authors=["Savuran, Halil"],
            doi="10.1016/j.engappai.2024.109337",
        )
        checker = DummyChecker()
        with patch("crossref_checker.time.sleep", return_value=None):
            result = checker.check_articles([article])[0]
        self.assertEqual(result["status"], "critical_mismatch")
        self.assertEqual(result["field_assessment"]["title"]["state"], "conflict")
        self.assertEqual(result["error"], "Critical mismatch in one or more required fields")

    def test_missing_doi_with_high_conf_title_becomes_corrected(self):
        class DummyChecker(cc.CrossrefChecker):
            def get_metadata(self, doi=None, title=None):
                return {
                    "metadata": {
                        "title": [title],
                        "container-title": ["Biomedical Signal Processing and Control"],
                        "author": [
                            {"given": "Gokhan", "family": "Sengul"},
                            {"given": "Murat", "family": "Karakaya"},
                        ],
                        "issued": {"date-parts": [[2022]]},
                        "DOI": "10.1016/j.bspc.2021.103242",
                        "URL": "https://doi.org/10.1016/j.bspc.2021.103242",
                        "volume": "71",
                        "page": "103242",
                    },
                    "matched_by": "title",
                    "score": 0.97,
                    "candidate_rank": 1,
                    "candidate_title": title,
                }

        article = cc.Article(
            citation_id="x2",
            source_format="txt",
            title="Deep learning based fall detection using smartwatches for healthcare applications",
            authors=["Sengul, Gokhan", "Karakaya, Murat"],
            journal="Biomedical Signal Processing and Control",
            year="2022",
        )
        checker = DummyChecker()
        with patch("crossref_checker.time.sleep", return_value=None):
            result = checker.check_articles([article])[0]
        self.assertEqual(result["status"], "corrected")
        self.assertIn("doi", result["correction_patch"]["set"])
        self.assertIn("url", result["correction_patch"]["set"])

    def test_low_confidence_title_becomes_unresolved_with_required_inputs(self):
        class DummyChecker(cc.CrossrefChecker):
            def get_metadata(self, doi=None, title=None):
                return {
                    "metadata": None,
                    "matched_by": "title",
                    "score": 0.42,
                    "candidate_rank": 1,
                    "candidate_title": "Nearby but incorrect title",
                }

        article = cc.Article(
            citation_id="x3",
            source_format="txt",
            title="Unknown citation",
            authors=["Someone, A."],
        )
        checker = DummyChecker()
        with patch("crossref_checker.time.sleep", return_value=None):
            result = checker.check_articles([article])[0]
        self.assertEqual(result["status"], "unresolved")
        self.assertIn("DOI", result["required_user_inputs"])
        self.assertEqual(result["matched_by"], "title")

    def test_integration_tex_fixture_preserves_tex_format(self):
        tex_content = (
            "\\begin{thebibliography}{1}\n"
            "\\bibitem{paper:1}\n"
            "Savuran, Halil, Karakaya, Murat: ``Wrong title here.''\n"
            "Engineering Applications of Artificial Intelligence 138, 109337 (2020).\n"
            "\\url{https://doi.org/10.1016/j.engappai.2024.109337}\n"
            "\\end{thebibliography}\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".tex", delete=False, encoding="utf-8") as tmp:
            tmp.write(tex_content)
            temp_path = tmp.name

        articles = cc.load_articles_from_text(temp_path)

        class DummyChecker(cc.CrossrefChecker):
            def get_metadata(self, doi=None, title=None):
                return {
                    "metadata": {
                        "title": ["A novel solution for routing a swarm of drones operated on a mobile host"],
                        "container-title": ["Engineering Applications of Artificial Intelligence"],
                        "author": [
                            {"given": "Halil", "family": "Savuran"},
                            {"given": "Murat", "family": "Karakaya"},
                        ],
                        "issued": {"date-parts": [[2024]]},
                        "DOI": "10.1016/j.engappai.2024.109337",
                        "URL": "https://doi.org/10.1016/j.engappai.2024.109337",
                        "volume": "138",
                        "page": "109337",
                    },
                    "matched_by": "doi",
                    "score": 1.0,
                    "candidate_rank": None,
                    "candidate_title": None,
                }

        checker = DummyChecker()
        with patch("crossref_checker.time.sleep", return_value=None):
            result = checker.check_articles(articles)[0]
        self.assertEqual(result["source_format"], "tex")
        self.assertEqual(result["corrected_reference"]["format"], "tex")
        self.assertIn("\\bibitem{paper:1}", result["corrected_reference"]["text"])

    def test_integration_txt_fixture_preserves_txt_format(self):
        txt_content = (
            "Murat Karakaya, M. Eryilmaz, and U. O. Ceyhan:\n"
            "\"Analyzing students' Academic Success in Prerequisite Course Chains: A Case Study in Turkey.\"\n"
            "International Journal of Engineering Education 34(2A), 364--370 (2018).\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
            tmp.write(txt_content)
            temp_path = tmp.name

        articles = cc.load_articles_from_text(temp_path)

        class DummyChecker(cc.CrossrefChecker):
            def get_metadata(self, doi=None, title=None):
                return {
                    "metadata": None,
                    "matched_by": "title",
                    "score": 0.3,
                    "candidate_rank": 1,
                    "candidate_title": "Analyzing Academic Achievement ...",
                }

        checker = DummyChecker()
        with patch("crossref_checker.time.sleep", return_value=None):
            result = checker.check_articles(articles)[0]
        self.assertEqual(result["source_format"], "txt")
        self.assertEqual(result["corrected_reference"]["format"], "txt")
        self.assertEqual(result["status"], "unresolved")

    def test_integration_json_fixture_preserves_json_format(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(
                [
                    {
                        "title": "Deep learning based fall detection using smartwatches for healthcare applications",
                        "authors": ["Sengul, Gokhan", "Karakaya, Murat"],
                        "journal": "Biomedical Signal Processing and Control",
                        "year": "2022",
                    }
                ],
                tmp,
            )
            temp_path = tmp.name

        articles = cc.load_articles_from_json(temp_path)

        class DummyChecker(cc.CrossrefChecker):
            def get_metadata(self, doi=None, title=None):
                return {
                    "metadata": {
                        "title": [title],
                        "container-title": ["Biomedical Signal Processing and Control"],
                        "author": [
                            {"given": "Gokhan", "family": "Sengul"},
                            {"given": "Murat", "family": "Karakaya"},
                        ],
                        "issued": {"date-parts": [[2022]]},
                        "DOI": "10.1016/j.bspc.2021.103242",
                        "URL": "https://doi.org/10.1016/j.bspc.2021.103242",
                    },
                    "matched_by": "title",
                    "score": 0.95,
                    "candidate_rank": 1,
                    "candidate_title": title,
                }

        checker = DummyChecker()
        with patch("crossref_checker.time.sleep", return_value=None):
            result = checker.check_articles(articles)[0]
        self.assertEqual(result["source_format"], "json")
        self.assertEqual(result["corrected_reference"]["format"], "json")
        self.assertEqual(result["status"], "corrected")


if __name__ == "__main__":
    unittest.main()

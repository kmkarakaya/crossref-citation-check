import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_DIR = Path(__file__).resolve().parents[1] / ".github" / "skills" / "crossref-citation-check"
sys.path.insert(0, str(SKILL_DIR))

import crossref_checker as cc


class CrossrefCheckerRegressionTests(unittest.TestCase):
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

    def test_doi_mismatch_is_reported_as_doi_conflict(self):
        class DummyChecker(cc.CrossrefChecker):
            def get_metadata(self, doi=None, title=None):
                return {
                    "metadata": {
                        "title": ["Different title from DOI record"],
                        "container-title": ["Engineering Applications of Artificial Intelligence"],
                        "author": [{"given": "Halil", "family": "Savuran"}],
                        "issued": {"date-parts": [[2024]]},
                        "DOI": "10.1016/j.engappai.2024.109337",
                        "URL": "https://doi.org/10.1016/j.engappai.2024.109337",
                    },
                    "matched_by": "doi",
                    "score": 1.0,
                }

        article = cc.Article(
            title="A novel solution for routing a swarm of drones operated on a mobile host",
            authors=["Savuran, Halil"],
            doi="10.1016/j.engappai.2024.109337",
        )
        checker = DummyChecker()
        with patch("crossref_checker.time.sleep", return_value=None):
            results = checker.check_articles([article])
        self.assertEqual(results[0]["status"], "doi_conflict")
        self.assertEqual(
            results[0]["error"],
            "DOI resolved but title does not match DOI record",
        )


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarking"))
GROUNDTRUTH_DIR = ROOT / "benchmarking" / "outputs" / "inputs"

import benchmark_score as bs
from benchmark_utils import load_crossref_checker


def _article_dict(article):
    return {
        "citation_id": article.citation_id,
        "source_format": article.source_format,
        "raw_record": article.raw_record,
        "bibitem_key": article.bibitem_key,
        "title": article.title,
        "authors": article.authors,
        "journal": article.journal,
        "volume": article.volume,
        "issue": article.issue,
        "pages": article.pages,
        "year": article.year,
        "doi": article.doi,
        "url": article.url,
    }


class BenchmarkScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cc, _ = load_crossref_checker()
        cls.gt_tex = cc.load_articles_from_text(str(GROUNDTRUTH_DIR / "groundtruth_bib.tex"))
        cls.gt_txt = cc.load_articles_from_text(str(GROUNDTRUTH_DIR / "groundtruth_bib.txt"))

    def test_perfect_synthetic_results_score_one(self):
        tex_results = []
        txt_results = []

        for article in self.gt_tex:
            tex_results.append(
                {
                    "citation_id": article.citation_id,
                    "status": "corrected",
                    "selection_required": False,
                    "error": "",
                    "required_user_inputs": [],
                    "article": _article_dict(article),
                    "correction_patch": {"set": {}, "unset": []},
                }
            )
        for article in self.gt_txt:
            txt_results.append(
                {
                    "citation_id": article.citation_id,
                    "status": "corrected",
                    "selection_required": False,
                    "error": "",
                    "required_user_inputs": [],
                    "article": _article_dict(article),
                    "correction_patch": {"set": {}, "unset": []},
                }
            )

        tex_summary = bs.score_results_against_groundtruth(self.gt_tex, tex_results, "tex")
        txt_summary = bs.score_results_against_groundtruth(self.gt_txt, txt_results, "txt")
        self.assertEqual(tex_summary["average_score"], 1.0)
        self.assertEqual(txt_summary["average_score"], 1.0)

    def test_uncorrected_results_score_below_half(self):
        bad_tex = []
        for article in self.gt_tex:
            bad_tex.append(
                {
                    "citation_id": article.citation_id,
                    "status": "unresolved",
                    "selection_required": True,
                    "error": "",
                    "required_user_inputs": [],
                    "article": {
                        "title": "totally wrong title",
                        "authors": [],
                        "journal": "wrong journal",
                        "volume": None,
                        "issue": None,
                        "pages": None,
                        "year": "1900",
                        "doi": "10.9999/fake",
                        "url": "https://example.com/fake",
                    },
                    "correction_patch": {"set": {}, "unset": []},
                }
            )

        summary = bs.score_results_against_groundtruth(self.gt_tex, bad_tex, "tex")
        self.assertLess(summary["average_score"], 0.5)

    def test_unresolved_with_rationale_gets_partial_credit(self):
        article = self.gt_tex[0]
        unresolved = [
            {
                "citation_id": article.citation_id,
                "status": "unresolved",
                "selection_required": False,
                "error": "No reliable Crossref match found",
                "required_user_inputs": ["DOI", "full exact title"],
                "article": {
                    "title": "wrong title",
                    "authors": [],
                    "journal": "wrong journal",
                    "volume": None,
                    "issue": None,
                    "pages": None,
                    "year": None,
                    "doi": None,
                    "url": None,
                },
                "correction_patch": {"set": {}, "unset": []},
            }
        ]
        resolved = [
            {
                "citation_id": article.citation_id,
                "status": "corrected",
                "selection_required": False,
                "error": "",
                "required_user_inputs": [],
                "article": _article_dict(article),
                "correction_patch": {"set": {}, "unset": []},
            }
        ]

        unresolved_summary = bs.score_results_against_groundtruth([article], unresolved, "tex")
        resolved_summary = bs.score_results_against_groundtruth([article], resolved, "tex")
        unresolved_score = unresolved_summary["citations"][0]["citation_score"]
        resolved_score = resolved_summary["citations"][0]["citation_score"]
        self.assertGreater(unresolved_score, 0.0)
        self.assertLess(unresolved_score, resolved_score)


if __name__ == "__main__":
    unittest.main()

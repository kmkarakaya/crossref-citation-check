import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarking"))

import benchmark_generate as bg
import benchmark_score as bs
from benchmark_utils import load_crossref_checker


GROUNDTRUTH_DIR = ROOT / "benchmarking" / "outputs" / "inputs"


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
        cls.cc = cc
        cls.gt_tex = cc.load_articles_from_text(str(GROUNDTRUTH_DIR / "groundtruth_bib.tex"))
        cls.gt_txt = cc.load_articles_from_text(str(GROUNDTRUTH_DIR / "groundtruth_bib.txt"))

    def _generate_benchmark_files(self, tmp: Path):
        bm_tex = tmp / "benchmark_bib.tex"
        bm_txt = tmp / "benchmark_bib.txt"
        manifest = tmp / "benchmark_manifest.json"
        bg.generate_benchmarks(
            groundtruth_tex=GROUNDTRUTH_DIR / "groundtruth_bib.tex",
            groundtruth_txt=GROUNDTRUTH_DIR / "groundtruth_bib.txt",
            out_tex=bm_tex,
            out_txt=bm_txt,
            manifest_path=manifest,
        )
        return bm_tex, bm_txt, manifest

    def test_perfect_synthetic_results_score_one(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bm_tex, bm_txt, manifest = self._generate_benchmark_files(tmp)
            tex_result = tmp / "bib_results_after_apply.json"
            txt_result = tmp / "refs_results_after_apply.json"

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

            tex_result.write_text(json.dumps(tex_results, ensure_ascii=False), encoding="utf-8")
            txt_result.write_text(json.dumps(txt_results, ensure_ascii=False), encoding="utf-8")

            report = bs.score_benchmark(
                groundtruth_tex=GROUNDTRUTH_DIR / "groundtruth_bib.tex",
                groundtruth_txt=GROUNDTRUTH_DIR / "groundtruth_bib.txt",
                benchmark_tex=bm_tex,
                benchmark_txt=bm_txt,
                result_tex=tex_result,
                result_txt=txt_result,
                manifest=manifest,
                min_overall=0.80,
            )
            self.assertEqual(report["overall"]["overall_correction_rate"], 1.0)
            self.assertNotIn("legacy_scores", report)
            self.assertNotIn("legacy_scores", report["files"]["tex"])
            self.assertNotIn("legacy_scores", report["files"]["txt"])
            for row in report["files"]["tex"]["citations"]:
                self.assertNotIn("legacy_scores", row)
            for row in report["files"]["txt"]["citations"]:
                self.assertNotIn("legacy_scores", row)

    def test_uncorrected_results_score_below_half(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bm_tex, bm_txt, manifest = self._generate_benchmark_files(tmp)
            tex_result = tmp / "bib_results_after_apply.json"
            txt_result = tmp / "refs_results_after_apply.json"

            bm_tex_articles = self.cc.load_articles_from_text(str(bm_tex))
            bm_txt_articles = self.cc.load_articles_from_text(str(bm_txt))

            bad_tex = []
            bad_txt = []
            for article in bm_tex_articles:
                bad_tex.append(
                    {
                        "citation_id": article.citation_id,
                        "status": "unresolved",
                        "selection_required": True,
                        "error": "",
                        "required_user_inputs": [],
                        "article": _article_dict(article),
                        "correction_patch": {"set": {}, "unset": []},
                    }
                )
            for article in bm_txt_articles:
                bad_txt.append(
                    {
                        "citation_id": article.citation_id,
                        "status": "unresolved",
                        "selection_required": True,
                        "error": "",
                        "required_user_inputs": [],
                        "article": _article_dict(article),
                        "correction_patch": {"set": {}, "unset": []},
                    }
                )

            tex_result.write_text(json.dumps(bad_tex, ensure_ascii=False), encoding="utf-8")
            txt_result.write_text(json.dumps(bad_txt, ensure_ascii=False), encoding="utf-8")

            report = bs.score_benchmark(
                groundtruth_tex=GROUNDTRUTH_DIR / "groundtruth_bib.tex",
                groundtruth_txt=GROUNDTRUTH_DIR / "groundtruth_bib.txt",
                benchmark_tex=bm_tex,
                benchmark_txt=bm_txt,
                result_tex=tex_result,
                result_txt=txt_result,
                manifest=manifest,
                min_overall=0.80,
            )
            self.assertLess(report["overall"]["overall_correction_rate"], 0.5)

    def test_unresolved_with_rationale_gets_partial_status_credit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bm_tex, bm_txt, manifest = self._generate_benchmark_files(tmp)
            tex_result = tmp / "bib_results_after_apply.json"
            txt_result = tmp / "refs_results_after_apply.json"

            bm_tex_articles = self.cc.load_articles_from_text(str(bm_tex))
            bm_txt_articles = self.cc.load_articles_from_text(str(bm_txt))

            unresolved_tex = []
            unresolved_txt = []
            for article in bm_tex_articles:
                unresolved_tex.append(
                    {
                        "citation_id": article.citation_id,
                        "status": "unresolved",
                        "selection_required": False,
                        "error": "No reliable Crossref match found",
                        "required_user_inputs": ["DOI", "full exact title"],
                        "article": _article_dict(article),
                        "correction_patch": {"set": {}, "unset": []},
                    }
                )
            for article in bm_txt_articles:
                unresolved_txt.append(
                    {
                        "citation_id": article.citation_id,
                        "status": "unresolved",
                        "selection_required": False,
                        "error": "No reliable Crossref match found",
                        "required_user_inputs": ["DOI", "full exact title"],
                        "article": _article_dict(article),
                        "correction_patch": {"set": {}, "unset": []},
                    }
                )

            tex_result.write_text(json.dumps(unresolved_tex, ensure_ascii=False), encoding="utf-8")
            txt_result.write_text(json.dumps(unresolved_txt, ensure_ascii=False), encoding="utf-8")

            report = bs.score_benchmark(
                groundtruth_tex=GROUNDTRUTH_DIR / "groundtruth_bib.tex",
                groundtruth_txt=GROUNDTRUTH_DIR / "groundtruth_bib.txt",
                benchmark_tex=bm_tex,
                benchmark_txt=bm_txt,
                result_tex=tex_result,
                result_txt=txt_result,
                manifest=manifest,
                min_overall=0.80,
            )
            self.assertGreater(report["overall"]["average_status_score"], 0.0)
            self.assertLess(report["overall"]["average_status_score"], 1.0)

    def test_critical_mismatch_patch_still_gets_fix_credit(self):
        gt_article = self.gt_tex[0]
        benchmark_article_obj = SimpleNamespace(
            citation_id=gt_article.citation_id,
            source_format="tex",
            raw_record="",
            bibitem_key=gt_article.citation_id,
            title="A novel solution for routeing a swarm of drones operated on a mobile host",
            authors=list(gt_article.authors),
            journal="Engineering Applications of Artificial Intelligence 139, 109337 (2025)",
            volume=None,
            issue=None,
            pages=None,
            year="2025",
            doi=None,
            url=None,
        )

        benchmark_like_article = {
            "citation_id": benchmark_article_obj.citation_id,
            "source_format": benchmark_article_obj.source_format,
            "raw_record": benchmark_article_obj.raw_record,
            "bibitem_key": benchmark_article_obj.bibitem_key,
            "title": benchmark_article_obj.title,
            "authors": benchmark_article_obj.authors,
            "journal": benchmark_article_obj.journal,
            "volume": benchmark_article_obj.volume,
            "issue": benchmark_article_obj.issue,
            "pages": benchmark_article_obj.pages,
            "year": benchmark_article_obj.year,
            "doi": benchmark_article_obj.doi,
            "url": benchmark_article_obj.url,
        }

        results = [
            {
                "citation_id": gt_article.citation_id,
                "status": "critical_mismatch",
                "selection_required": False,
                "error": "Critical mismatch",
                "required_user_inputs": [],
                "article": benchmark_like_article,
                "correction_patch": {
                    "set": {
                        "title": gt_article.title,
                        "year": gt_article.year,
                        "doi": gt_article.doi,
                        "url": gt_article.url,
                    },
                    "unset": [],
                },
            }
        ]

        summary = bs.score_results_against_groundtruth(
            groundtruth_articles=[gt_article],
            benchmark_articles=[benchmark_article_obj],
            results=results,
            label="tex",
            manifest_fields_lookup={gt_article.citation_id: ["title", "year", "doi", "url"]},
        )
        row = summary["citations"][0]
        self.assertGreater(row["fixed_count"], 0)
        self.assertIn("year", row["fixed_fields"])
        self.assertIn("doi", row["fixed_fields"])
        self.assertIn("url", row["fixed_fields"])

    def test_missing_manifest_uses_auto_diff_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bm_tex, bm_txt, _ = self._generate_benchmark_files(tmp)
            tex_result = tmp / "bib_results_after_apply.json"
            txt_result = tmp / "refs_results_after_apply.json"

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

            tex_result.write_text(json.dumps(tex_results, ensure_ascii=False), encoding="utf-8")
            txt_result.write_text(json.dumps(txt_results, ensure_ascii=False), encoding="utf-8")

            report = bs.score_benchmark(
                groundtruth_tex=GROUNDTRUTH_DIR / "groundtruth_bib.tex",
                groundtruth_txt=GROUNDTRUTH_DIR / "groundtruth_bib.txt",
                benchmark_tex=bm_tex,
                benchmark_txt=bm_txt,
                result_tex=tex_result,
                result_txt=txt_result,
                manifest=None,
                min_overall=0.80,
            )
            self.assertEqual(report["overall"]["overall_correction_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()

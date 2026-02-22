import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarking"
sys.path.insert(0, str(BENCH))

import benchmark_generate as bg
import benchmark_report as br
import benchmark_score as bs
from benchmark_utils import load_crossref_checker


class BenchmarkReportTests(unittest.TestCase):
    def test_report_generation_and_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            gt_tex = ROOT / "benchmarking" / "outputs" / "inputs" / "groundtruth_bib.tex"
            gt_txt = ROOT / "benchmarking" / "outputs" / "inputs" / "groundtruth_bib.txt"
            bm_tex = tmp / "benchmark_bib.tex"
            bm_txt = tmp / "benchmark_bib.txt"
            manifest = tmp / "benchmark_manifest.json"
            score_json = tmp / "benchmark_score.json"
            report_md = tmp / "report.md"
            tex_result = tmp / "bib_results_after_apply.json"
            txt_result = tmp / "refs_results_after_apply.json"

            bg.generate_benchmarks(
                groundtruth_tex=gt_tex,
                groundtruth_txt=gt_txt,
                out_tex=bm_tex,
                out_txt=bm_txt,
                manifest_path=manifest,
            )

            cc, _ = load_crossref_checker()
            tex_articles = cc.load_articles_from_text(str(gt_tex))
            txt_articles = cc.load_articles_from_text(str(gt_txt))

            def article_dict(a):
                return {
                    "citation_id": a.citation_id,
                    "source_format": a.source_format,
                    "raw_record": a.raw_record,
                    "bibitem_key": a.bibitem_key,
                    "title": a.title,
                    "authors": a.authors,
                    "journal": a.journal,
                    "volume": a.volume,
                    "issue": a.issue,
                    "pages": a.pages,
                    "year": a.year,
                    "doi": a.doi,
                    "url": a.url,
                }

            tex_results = []
            txt_results = []
            for a in tex_articles:
                tex_results.append(
                    {
                        "citation_id": a.citation_id,
                        "status": "corrected",
                        "selection_required": False,
                        "matched_by": "title",
                        "selection_reason": "none",
                        "selected_candidate_rank": 1,
                        "recommended_candidate_rank": 1,
                        "article": article_dict(a),
                        "correction_patch": {"set": {}, "unset": []},
                    }
                )
            for a in txt_articles:
                txt_results.append(
                    {
                        "citation_id": a.citation_id,
                        "status": "corrected",
                        "selection_required": False,
                        "matched_by": "title",
                        "selection_reason": "none",
                        "selected_candidate_rank": 1,
                        "recommended_candidate_rank": 1,
                        "article": article_dict(a),
                        "correction_patch": {"set": {}, "unset": []},
                    }
                )

            tex_result.write_text(json.dumps(tex_results, indent=2, ensure_ascii=False), encoding="utf-8")
            txt_result.write_text(json.dumps(txt_results, indent=2, ensure_ascii=False), encoding="utf-8")

            score_payload = bs.score_benchmark(
                groundtruth_tex=gt_tex,
                groundtruth_txt=gt_txt,
                benchmark_tex=bm_tex,
                benchmark_txt=bm_txt,
                result_tex=tex_result,
                result_txt=txt_result,
                manifest=manifest,
                min_overall=0.80,
            )
            score_json.write_text(json.dumps(score_payload, indent=2, ensure_ascii=False), encoding="utf-8")

            out = br.generate_report(
                groundtruth_tex=gt_tex,
                groundtruth_txt=gt_txt,
                benchmark_tex=bm_tex,
                benchmark_txt=bm_txt,
                result_tex=tex_result,
                result_txt=txt_result,
                score_json=score_json,
                output=report_md,
            )
            self.assertEqual(out, report_md)
            self.assertTrue(report_md.exists())

            text = report_md.read_text(encoding="utf-8")
            self.assertIn("## TEX Citations", text)
            self.assertIn("## TXT Citations", text)
            self.assertIn("### TEX `paper:1`", text)
            self.assertIn("### TXT `txt:1`", text)
            self.assertIn("Correction Summary", text)
            self.assertNotIn("Legacy Scores", text)
            self.assertNotIn("legacy strict", text)
            self.assertNotIn("field_relaxed", text)
            self.assertNotIn("citation_relaxed", text)
            self.assertIn("Not Needed", text)
            self.assertIn(
                "| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |",
                text,
            )

    def test_missing_score_mapping_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            gt_tex = ROOT / "benchmarking" / "outputs" / "inputs" / "groundtruth_bib.tex"
            gt_txt = ROOT / "benchmarking" / "outputs" / "inputs" / "groundtruth_bib.txt"
            bm_tex = tmp / "benchmark_bib.tex"
            bm_txt = tmp / "benchmark_bib.txt"
            manifest = tmp / "benchmark_manifest.json"
            score_json = tmp / "benchmark_score.json"
            report_md = tmp / "report.md"
            tex_result = tmp / "bib_results_after_apply.json"
            txt_result = tmp / "refs_results_after_apply.json"

            bg.generate_benchmarks(
                groundtruth_tex=gt_tex,
                groundtruth_txt=gt_txt,
                out_tex=bm_tex,
                out_txt=bm_txt,
                manifest_path=manifest,
            )

            cc, _ = load_crossref_checker()
            tex_articles = cc.load_articles_from_text(str(gt_tex))
            txt_articles = cc.load_articles_from_text(str(gt_txt))

            tex_results = []
            txt_results = []
            for a in tex_articles:
                tex_results.append(
                    {
                        "citation_id": a.citation_id,
                        "status": "corrected",
                        "selection_required": False,
                        "matched_by": "title",
                        "article": {
                            "title": a.title,
                            "authors": a.authors,
                            "journal": a.journal,
                            "volume": a.volume,
                            "issue": a.issue,
                            "pages": a.pages,
                            "year": a.year,
                            "doi": a.doi,
                            "url": a.url,
                        },
                        "correction_patch": {"set": {}, "unset": []},
                    }
                )
            for a in txt_articles:
                txt_results.append(
                    {
                        "citation_id": a.citation_id,
                        "status": "corrected",
                        "selection_required": False,
                        "matched_by": "title",
                        "article": {
                            "title": a.title,
                            "authors": a.authors,
                            "journal": a.journal,
                            "volume": a.volume,
                            "issue": a.issue,
                            "pages": a.pages,
                            "year": a.year,
                            "doi": a.doi,
                            "url": a.url,
                        },
                        "correction_patch": {"set": {}, "unset": []},
                    }
                )

            tex_result.write_text(json.dumps(tex_results, indent=2, ensure_ascii=False), encoding="utf-8")
            txt_result.write_text(json.dumps(txt_results, indent=2, ensure_ascii=False), encoding="utf-8")

            score_payload = bs.score_benchmark(
                groundtruth_tex=gt_tex,
                groundtruth_txt=gt_txt,
                benchmark_tex=bm_tex,
                benchmark_txt=bm_txt,
                result_tex=tex_result,
                result_txt=txt_result,
                manifest=manifest,
                min_overall=0.80,
            )
            score_payload["files"]["tex"]["citations"] = score_payload["files"]["tex"]["citations"][:-1]
            score_json.write_text(json.dumps(score_payload, indent=2, ensure_ascii=False), encoding="utf-8")

            with self.assertRaises(ValueError):
                br.generate_report(
                    groundtruth_tex=gt_tex,
                    groundtruth_txt=gt_txt,
                    benchmark_tex=bm_tex,
                    benchmark_txt=bm_txt,
                    result_tex=tex_result,
                    result_txt=txt_result,
                    score_json=score_json,
                    output=report_md,
                )

    def test_cli_returns_nonzero_on_missing_mapping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            gt_tex = ROOT / "benchmarking" / "outputs" / "inputs" / "groundtruth_bib.tex"
            gt_txt = ROOT / "benchmarking" / "outputs" / "inputs" / "groundtruth_bib.txt"
            bm_tex = tmp / "benchmark_bib.tex"
            bm_txt = tmp / "benchmark_bib.txt"
            manifest = tmp / "benchmark_manifest.json"
            score_json = tmp / "benchmark_score.json"
            report_md = tmp / "report.md"
            tex_result = tmp / "bib_results_after_apply.json"
            txt_result = tmp / "refs_results_after_apply.json"

            bg.generate_benchmarks(
                groundtruth_tex=gt_tex,
                groundtruth_txt=gt_txt,
                out_tex=bm_tex,
                out_txt=bm_txt,
                manifest_path=manifest,
            )

            tex_result.write_text("[]", encoding="utf-8")
            txt_result.write_text("[]", encoding="utf-8")
            score_json.write_text(
                json.dumps({"files": {"tex": {"citations": []}, "txt": {"citations": []}}}, ensure_ascii=False),
                encoding="utf-8",
            )

            cmd = [
                sys.executable,
                str(BENCH / "benchmark_report.py"),
                "--groundtruth-tex",
                str(gt_tex),
                "--groundtruth-txt",
                str(gt_txt),
                "--benchmark-tex",
                str(bm_tex),
                "--benchmark-txt",
                str(bm_txt),
                "--result-tex",
                str(tex_result),
                "--result-txt",
                str(txt_result),
                "--score-json",
                str(score_json),
                "--output",
                str(report_md),
            ]
            completed = subprocess.run(cmd, cwd=str(ROOT))
            self.assertNotEqual(completed.returncode, 0)


if __name__ == "__main__":
    unittest.main()

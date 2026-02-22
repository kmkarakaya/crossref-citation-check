import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarking"))

import benchmark_skill_readiness as bsr


CSV_HEADER = "case_id,prompt,should_trigger,expects_selection_flow,input_file\n"


class SkillReadinessTests(unittest.TestCase):
    def _write_correction_score(self, path: Path, rate: float = 0.9) -> None:
        payload = {"overall": {"overall_correction_rate": rate}}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _write_case_csv(self, path: Path, rows: list[str]) -> None:
        path.write_text(CSV_HEADER + "\n".join(rows) + "\n", encoding="utf-8")

    def _write_case_files(
        self,
        case_dir: Path,
        response: str,
        commands: list[str],
        before_items=None,
        after_items=None,
        selection_map=None,
    ) -> None:
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "response.md").write_text(response, encoding="utf-8")
        (case_dir / "commands.txt").write_text("\n".join(commands) + "\n", encoding="utf-8")
        if before_items is not None:
            (case_dir / "run_before_apply.json").write_text(
                json.dumps(before_items, ensure_ascii=False), encoding="utf-8"
            )
        if after_items is not None:
            (case_dir / "run_after_apply.json").write_text(
                json.dumps(after_items, ensure_ascii=False), encoding="utf-8"
            )
        if selection_map is not None:
            (case_dir / "run_selection_map.json").write_text(
                json.dumps(selection_map, ensure_ascii=False), encoding="utf-8"
            )

    def _minimal_result_item(self, cid: str, selection_required: bool = False) -> dict:
        return {
            "citation_id": cid,
            "status": "corrected",
            "correction_patch": {"set": {}, "unset": []},
            "selection_required": selection_required,
        }

    def test_trigger_positive_passes_when_checker_command_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            runs = tmp / "runs"
            cases_csv = tmp / "cases.csv"
            score_json = tmp / "benchmark_score.json"
            self._write_correction_score(score_json, rate=0.9)

            self._write_case_csv(
                cases_csv,
                [
                    "case1,Use skill,true,false,benchmarking/outputs/benchmark_bib.tex",
                ],
            )

            case_dir = runs / "case1"
            self._write_case_files(
                case_dir,
                response=(
                    "Command: python .github/skills/crossref-citation-check/crossref_checker.py -i a -o b.json\n"
                    "Output path: b.json\n"
                    "Summary: status corrected"
                ),
                commands=[
                    "python .github/skills/crossref-citation-check/crossref_checker.py -i a -o b.json"
                ],
                after_items=[self._minimal_result_item("paper:1", selection_required=False)],
            )

            payload = bsr.evaluate_readiness(cases_csv, runs, score_json)
            case = payload["per_case"][0]
            self.assertTrue(case["checks"]["trigger_check"])

    def test_trigger_negative_fails_when_checker_command_appears(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            runs = tmp / "runs"
            cases_csv = tmp / "cases.csv"
            score_json = tmp / "benchmark_score.json"
            self._write_correction_score(score_json, rate=0.9)

            self._write_case_csv(
                cases_csv,
                [
                    "case2,Translate this,false,false,",
                ],
            )

            case_dir = runs / "case2"
            self._write_case_files(
                case_dir,
                response="No-op",
                commands=[
                    "python .github/skills/crossref-citation-check/crossref_checker.py -i a -o b.json"
                ],
                after_items=[self._minimal_result_item("txt:1", selection_required=False)],
            )

            payload = bsr.evaluate_readiness(cases_csv, runs, score_json)
            case = payload["per_case"][0]
            self.assertFalse(case["checks"]["trigger_check"])
            self.assertIn("negative_control_false_positive", case["hard_fail_reasons"])

    def test_selection_required_flow_fails_without_map_and_passes_with_map(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            runs = tmp / "runs"
            cases_csv = tmp / "cases.csv"
            score_json = tmp / "benchmark_score.json"
            self._write_correction_score(score_json, rate=0.9)
            self._write_case_csv(
                cases_csv,
                [
                    "case3,Use skill,true,true,benchmarking/outputs/benchmark_bib.tex",
                ],
            )

            # Failing selection flow
            fail_dir = runs / "case3"
            self._write_case_files(
                fail_dir,
                response=(
                    "Command: python .github/skills/crossref-citation-check/crossref_checker.py -i a -o before.json\n"
                    "Output path: before.json\n"
                    "Summary: selection_required true"
                ),
                commands=[
                    "python .github/skills/crossref-citation-check/crossref_checker.py -i a -o before.json"
                ],
                before_items=[self._minimal_result_item("paper:4", selection_required=True)],
                after_items=[self._minimal_result_item("paper:4", selection_required=True)],
            )
            payload_fail = bsr.evaluate_readiness(cases_csv, runs, score_json)
            case_fail = payload_fail["per_case"][0]
            self.assertFalse(case_fail["checks"]["selection_flow_check"])

            # Passing selection flow (overwrite with map + resolved after)
            self._write_case_files(
                fail_dir,
                response=(
                    "Command: python .github/skills/crossref-citation-check/crossref_checker.py -i a -o before.json\n"
                    "Output path: after.json\n"
                    "Summary: selection handled and corrected"
                ),
                commands=[
                    "python .github/skills/crossref-citation-check/crossref_checker.py -i a -o before.json",
                    "python .github/skills/crossref-citation-check/crossref_checker.py -i a --selection-map map.json -o after.json",
                ],
                before_items=[self._minimal_result_item("paper:4", selection_required=True)],
                after_items=[self._minimal_result_item("paper:4", selection_required=False)],
                selection_map={"paper:4": 1},
            )
            payload_pass = bsr.evaluate_readiness(cases_csv, runs, score_json)
            case_pass = payload_pass["per_case"][0]
            self.assertTrue(case_pass["checks"]["selection_flow_check"])

    def test_hard_fail_on_direct_crossref_api_usage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            runs = tmp / "runs"
            cases_csv = tmp / "cases.csv"
            score_json = tmp / "benchmark_score.json"
            self._write_correction_score(score_json, rate=0.9)
            self._write_case_csv(
                cases_csv,
                [
                    "case4,Use skill,true,false,benchmarking/outputs/benchmark_bib.txt",
                ],
            )

            case_dir = runs / "case4"
            self._write_case_files(
                case_dir,
                response=(
                    "Command: python .github/skills/crossref-citation-check/crossref_checker.py -i a -o out.json\n"
                    "Output path: out.json\n"
                    "Summary: corrected"
                ),
                commands=[
                    "curl https://api.crossref.org/works?query.title=test",
                    "python .github/skills/crossref-citation-check/crossref_checker.py -i a -o out.json",
                ],
                after_items=[self._minimal_result_item("txt:2", selection_required=False)],
            )

            payload = bsr.evaluate_readiness(cases_csv, runs, score_json)
            case = payload["per_case"][0]
            self.assertIn("direct_crossref_api_policy_violation", case["hard_fail_reasons"])
            self.assertIn("case4: direct_crossref_api_policy_violation", payload["hard_fail_reasons"])

    def test_overall_ready_true_when_thresholds_satisfied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            runs = tmp / "runs"
            cases_csv = tmp / "cases.csv"
            score_json = tmp / "benchmark_score.json"
            self._write_correction_score(score_json, rate=0.91)
            self._write_case_csv(
                cases_csv,
                [
                    "case_pos,Use skill,true,false,benchmarking/outputs/benchmark_bib.txt",
                    "case_neg,Translate this,false,false,",
                ],
            )

            pos_dir = runs / "case_pos"
            self._write_case_files(
                pos_dir,
                response=(
                    "Command: python .github/skills/crossref-citation-check/crossref_checker.py -i a -o out.json\n"
                    "Output path: out.json\n"
                    "Summary: corrected"
                ),
                commands=[
                    "python .github/skills/crossref-citation-check/crossref_checker.py -i a -o out.json"
                ],
                after_items=[self._minimal_result_item("txt:1", selection_required=False)],
            )

            neg_dir = runs / "case_neg"
            self._write_case_files(
                neg_dir,
                response="No skill run needed.",
                commands=["echo summary only"],
            )

            payload = bsr.evaluate_readiness(cases_csv, runs, score_json)
            self.assertTrue(payload["overall_ready"])
            self.assertEqual(payload["metrics"]["trigger_precision"], 1.0)


if __name__ == "__main__":
    unittest.main()

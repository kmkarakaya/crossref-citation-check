import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarking"))
GROUNDTRUTH_DIR = ROOT / "benchmarking" / "outputs" / "inputs"

import benchmark_generate as bg
from benchmark_utils import load_crossref_checker


class BenchmarkGenerationTests(unittest.TestCase):
    def test_generate_outputs_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            out_tex = tmp / "benchmark_bib.tex"
            out_txt = tmp / "benchmark_bib.txt"
            manifest = tmp / "benchmark_manifest.json"

            bg.generate_benchmarks(
                groundtruth_tex=GROUNDTRUTH_DIR / "groundtruth_bib.tex",
                groundtruth_txt=GROUNDTRUTH_DIR / "groundtruth_bib.txt",
                out_tex=out_tex,
                out_txt=out_txt,
                manifest_path=manifest,
            )

            self.assertTrue(out_tex.exists())
            self.assertTrue(out_txt.exists())
            self.assertTrue(manifest.exists())

            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(len(data["mutations"]["tex"]), 7)
            self.assertEqual(len(data["mutations"]["txt"]), 7)
            for item in data["mutations"]["tex"]:
                self.assertGreaterEqual(item["mutation_count"], 2)
                self.assertIn("mutated_fields_core", item)
                self.assertIn("mutated_fields_all", item)
                self.assertIsInstance(item["mutated_fields_core"], list)
                self.assertIsInstance(item["mutated_fields_all"], list)
                self.assertGreaterEqual(len(item["mutated_fields_core"]), 1)
            for item in data["mutations"]["txt"]:
                self.assertGreaterEqual(item["mutation_count"], 2)
                self.assertIn("mutated_fields_core", item)
                self.assertIn("mutated_fields_all", item)
                self.assertIsInstance(item["mutated_fields_core"], list)
                self.assertIsInstance(item["mutated_fields_all"], list)
                self.assertGreaterEqual(len(item["mutated_fields_core"]), 1)

            cc, _ = load_crossref_checker()
            tex_articles = cc.load_articles_from_text(str(out_tex))
            txt_articles = cc.load_articles_from_text(str(out_txt))
            self.assertEqual(len(tex_articles), 7)
            self.assertEqual(len(txt_articles), 7)
            self.assertEqual([a.citation_id for a in tex_articles], [f"paper:{i}" for i in range(1, 8)])
            self.assertEqual([a.citation_id for a in txt_articles], [f"txt:{i}" for i in range(1, 8)])


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarking"))

import benchmark_make_selection_map as bms


class BenchmarkSelectionMapTests(unittest.TestCase):
    def test_build_selection_map_success(self):
        results = [
            {"citation_id": "paper:1", "selection_required": False},
            {"citation_id": "paper:2", "selection_required": True, "recommended_candidate_rank": 2},
            {"citation_id": "paper:3", "selection_required": True, "recommended_candidate_rank": 1},
        ]
        self.assertEqual(bms.build_selection_map(results), {"paper:2": 2, "paper:3": 1})

    def test_build_selection_map_missing_rank_fails(self):
        results = [
            {"citation_id": "paper:4", "selection_required": True},
        ]
        with self.assertRaises(ValueError):
            bms.build_selection_map(results)


if __name__ == "__main__":
    unittest.main()

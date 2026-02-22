from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


def build_selection_map(results: List[dict]) -> Dict[str, int]:
    selection_map: Dict[str, int] = {}

    for item in results:
        if not item.get("selection_required"):
            continue
        citation_id = str(item.get("citation_id") or "").strip()
        if not citation_id:
            raise ValueError("Result item with selection_required=true is missing citation_id")
        rank = item.get("recommended_candidate_rank")
        if rank is None:
            raise ValueError(f"Missing recommended_candidate_rank for citation_id '{citation_id}'")
        try:
            rank_int = int(rank)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid recommended_candidate_rank for citation_id '{citation_id}': {rank}") from exc
        if rank_int < 1:
            raise ValueError(f"recommended_candidate_rank must be >= 1 for citation_id '{citation_id}'")
        selection_map[citation_id] = rank_int

    return selection_map


def main() -> int:
    parser = argparse.ArgumentParser(description="Create selection-map JSON from first-pass checker results.")
    parser.add_argument("-i", "--input", required=True, help="First-pass result JSON path")
    parser.add_argument("-o", "--output", required=True, help="Selection map JSON output path")
    args = parser.parse_args()

    try:
        data = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
        if not isinstance(data, list):
            raise ValueError("Input JSON must be a list of result objects")
        selection_map = build_selection_map(data)
        Path(args.output).write_text(json.dumps(selection_map, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        print(f"[benchmark-selection-map] ERROR: {exc}")
        return 1

    print(f"[benchmark-selection-map] Wrote: {args.output}")
    print(f"[benchmark-selection-map] Entries: {len(selection_map)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

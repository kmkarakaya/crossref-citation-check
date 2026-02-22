from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from benchmark_utils import CORE_FIELDS, load_crossref_checker


EXPECTED_TEX_IDS = [f"paper:{i}" for i in range(1, 8)]
EXPECTED_TXT_IDS = [f"txt:{i}" for i in range(1, 8)]

# Structured mutation targets are used by benchmark_score.py as primary source.
MUTATED_FIELDS_ALL_BY_INDEX = {
    1: ["title", "journal", "year", "doi", "url"],
    2: ["authors", "year", "doi", "url"],
    3: ["title", "journal"],
    4: ["title", "pages", "doi", "url"],
    5: ["title", "year", "doi", "url"],
    6: ["title", "journal", "doi", "url"],
    7: ["pages", "doi", "url"],
}


def _citation_index(citation_id: str) -> int:
    _, idx = citation_id.split(":", 1)
    return int(idx)


def _mutated_fields(citation_id: str) -> Tuple[List[str], List[str]]:
    idx = _citation_index(citation_id)
    all_fields = MUTATED_FIELDS_ALL_BY_INDEX.get(idx)
    if not all_fields:
        raise ValueError(f"No structured mutation fields configured for {citation_id}")
    core_fields = [field for field in all_fields if field in CORE_FIELDS]
    return core_fields, all_fields


def _replace_once(text: str, old: str, new: str, note: str, notes: List[str]) -> str:
    if old not in text:
        raise ValueError(f"Could not apply mutation '{note}': missing fragment '{old}'")
    notes.append(note)
    return text.replace(old, new, 1)


def _replace_all(text: str, old: str, new: str, note: str, notes: List[str]) -> str:
    if old not in text:
        raise ValueError(f"Could not apply mutation '{note}': missing fragment '{old}'")
    notes.append(note)
    return text.replace(old, new)


def _mutate_tex_record(citation_id: str, record: str) -> Tuple[str, List[str]]:
    notes: List[str] = []
    out = record

    if citation_id == "paper:1":
        out = _replace_once(out, "routing", "routeing", "title typo: routing -> routeing", notes)
        out = _replace_once(
            out,
            "Engineering Applications of Artificial Intelligence 138, 109337 (2024).",
            "Engineering Applications of Artificial Intelligence 139, 109337 (2025).",
            "venue/year drift: 138->139 and 2024->2025",
            notes,
        )
        out = _replace_once(
            out,
            "\\url{https://doi.org/10.1016/j.engappai.2024.109337}\n",
            "",
            "deleted DOI URL line",
            notes,
        )
    elif citation_id == "paper:2":
        out = _replace_once(out, "Sanjay Misra, ", "", "removed one middle author token", notes)
        out = _replace_once(out, "(2022).", "(2023).", "year drift: 2022->2023", notes)
        out = _replace_once(
            out,
            "\\url{https://doi.org/10.1016/j.bspc.2021.103242}",
            "\\url{https://doi.org/10.9999/fake.fall.2023}",
            "injected fake DOI URL",
            notes,
        )
    elif citation_id == "paper:3":
        out = _replace_once(
            out,
            "SS-MLA: a semisupervised method for multi-label annotation of remotely sensed images.",
            "SS-MLA: a semisupervised method for multi-label annotation.",
            "truncated title after multi-label annotation",
            notes,
        )
        out = _replace_once(
            out,
            "Journal of Applied Remote Sensing 15(03), 036509 (2021).",
            "Journal of Advanced Remote Sensing 15(03), 036509, 99(9), 999--1001 (2021).",
            "journal drift + fake issue/pages fragment",
            notes,
        )
    elif citation_id == "paper:4":
        out = _replace_once(out, "students' Academic", "students Academic", "title apostrophe removed", notes)
        out = _replace_once(out, "364--370 (2018).", "364--376 (2018).", "page range drift: 364--370->364--376", notes)
        out = _replace_once(
            out,
            "International Journal of Engineering Education 34(2A), 364--376 (2018).",
            "International Journal of Engineering Education 34(2A), 364--376 (2018).\n\\url{https://doi.org/10.4242/fake.chain.2018}",
            "added fake DOI URL",
            notes,
        )
    elif citation_id == "paper:5":
        out = _replace_once(out, "moving carrier", "stationary carrier", "title semantic drift: moving->stationary", notes)
        out = _replace_once(out, "(2016).", "(2017).", "year drift: 2016->2017", notes)
        out = _replace_once(out, "10.1007/s00500-015-1970-4", "10.1007/s00500-015-1970-9", "DOI drift suffix 4->9", notes)
    elif citation_id == "paper:6":
        out = _replace_once(out, "``MSCT: An Efficient", "``An Efficient", "removed MSCT prefix from title", notes)
        out = _replace_once(out, "9(9), 3396--3411 (2015).", "9(4), 3396--3411 (2015).", "venue drift: 9(9)->9(4)", notes)
        out = _replace_once(
            out,
            "\\url{https://doi.org/10.3837/tiis.2015.09.007}",
            "\\url{https://example.com/fake/msct}",
            "replaced URL with fake non-DOI URL",
            notes,
        )
    elif citation_id == "paper:7":
        out = _replace_once(out, "65--82 (2015).", "65--92 (2015).", "page range drift: 65--82->65--92", notes)
        out = _replace_once(
            out,
            "Ad Hoc \\& Sensor Wireless Networks 28(1--2), 65--92 (2015).",
            "Ad Hoc \\& Sensor Wireless Networks 28(1--2), 65--92 (2015).\n\\url{https://doi.org/10.5555/ahsn.2015.028}",
            "added fake DOI URL",
            notes,
        )
        out = _replace_once(
            out,
            "No reliable Crossref match found; DOI unavailable.\n",
            "",
            "removed no-match note from tex variant",
            notes,
        )
    else:
        raise ValueError(f"Unexpected citation key in tex file: {citation_id}")

    return out, notes


def _mutate_txt_line(citation_id: str, line: str) -> Tuple[str, List[str]]:
    notes: List[str] = []
    out = line

    if citation_id == "txt:1":
        out = _replace_once(out, "routing", "routeing", "title typo: routing -> routeing", notes)
        out = _replace_all(out, " 138, ", " 139, ", "venue drift: 138->139", notes)
        out = _replace_all(out, "(2024)", "(2025)", "year drift: 2024->2025", notes)
        out = _replace_once(out, "doi:10.1016/j.engappai.2024.109337. ", "", "deleted DOI token", notes)
        out = _replace_once(out, "https://doi.org/10.1016/j.engappai.2024.109337", "", "deleted DOI URL token", notes)
    elif citation_id == "txt:2":
        out = _replace_once(out, "Sanjay Misra, ", "", "removed one middle author token", notes)
        out = _replace_all(out, "(2022)", "(2023)", "year drift: 2022->2023", notes)
        out = _replace_all(out, "10.1016/j.bspc.2021.103242", "10.9999/fake.fall.2023", "injected fake DOI", notes)
    elif citation_id == "txt:3":
        out = _replace_once(
            out,
            "multi-label annotation of remotely sensed images",
            "multi-label annotation",
            "truncated title after multi-label annotation",
            notes,
        )
        out = _replace_once(
            out,
            "Journal of Applied Remote Sensing",
            "Journal of Advanced Remote Sensing",
            "journal drift: Applied->Advanced",
            notes,
        )
        out = _replace_once(out, ". doi:", "; 99(9), 999--1001. doi:", "added fake issue/pages fragment", notes)
    elif citation_id == "txt:4":
        out = _replace_once(out, "students' Academic", "students Academic", "title apostrophe removed", notes)
        out = _replace_once(out, "364--370", "364--376", "page range drift: 364--370->364--376", notes)
        out = out.rstrip(".")
        notes.append("added fake DOI and DOI URL")
        out = f"{out}. doi:10.4242/fake.chain.2018. https://doi.org/10.4242/fake.chain.2018"
    elif citation_id == "txt:5":
        out = _replace_once(out, "moving carrier", "stationary carrier", "title semantic drift: moving->stationary", notes)
        out = _replace_all(out, "(2016)", "(2017)", "year drift: 2016->2017", notes)
        out = _replace_all(out, "10.1007/s00500-015-1970-4", "10.1007/s00500-015-1970-9", "DOI drift suffix 4->9", notes)
    elif citation_id == "txt:6":
        out = _replace_once(out, "\"MSCT: An Efficient", "\"An Efficient", "removed MSCT prefix from title", notes)
        out = _replace_once(out, "9(9) (2015)", "9(4) (2015)", "venue drift: 9(9)->9(4)", notes)
        out = _replace_once(
            out,
            "https://doi.org/10.3837/tiis.2015.09.007",
            "https://example.com/fake/msct",
            "replaced URL with fake non-DOI URL",
            notes,
        )
    elif citation_id == "txt:7":
        out = _replace_once(out, "65--82", "65--92", "page range drift: 65--82->65--92", notes)
        out = out.rstrip(".")
        notes.append("added fake DOI and DOI URL")
        out = f"{out}. doi:10.5555/ahsn.2015.028. https://doi.org/10.5555/ahsn.2015.028"
    else:
        raise ValueError(f"Unexpected citation id in txt file: {citation_id}")

    return out, notes


def mutate_tex_content(text: str) -> Tuple[str, List[Dict[str, object]]]:
    bibitem_matches = list(re.finditer(r"\\bibitem\s*\{([^}]+)\}", text))
    if len(bibitem_matches) != 7:
        raise ValueError(f"Expected 7 bibitems in tex groundtruth, found {len(bibitem_matches)}")

    manifest_items: List[Dict[str, object]] = []
    pieces: List[str] = []
    cursor = 0
    seen_ids: List[str] = []

    for idx, match in enumerate(bibitem_matches):
        start = match.start()
        end = bibitem_matches[idx + 1].start() if idx + 1 < len(bibitem_matches) else len(text)
        citation_id = match.group(1).strip()
        seen_ids.append(citation_id)
        original_record = text[start:end]
        mutated_record, notes = _mutate_tex_record(citation_id, original_record)
        pieces.append(text[cursor:start])
        pieces.append(mutated_record)
        cursor = end
        manifest_items.append(
            {
                "citation_id": citation_id,
                "mutation_count": len(notes),
                "mutations": notes,
                "mutated_fields_core": _mutated_fields(citation_id)[0],
                "mutated_fields_all": _mutated_fields(citation_id)[1],
                "before_excerpt": original_record.strip()[:220],
                "after_excerpt": mutated_record.strip()[:220],
            }
        )

    pieces.append(text[cursor:])
    if sorted(seen_ids) != sorted(EXPECTED_TEX_IDS):
        raise ValueError(f"Unexpected citation keys in tex file: {seen_ids}")

    return "".join(pieces), manifest_items


def mutate_txt_content(text: str) -> Tuple[str, List[Dict[str, object]]]:
    lines = text.splitlines()
    non_empty_indices = [idx for idx, line in enumerate(lines) if line.strip()]
    if len(non_empty_indices) != 7:
        raise ValueError(f"Expected 7 citations in txt groundtruth, found {len(non_empty_indices)}")

    manifest_items: List[Dict[str, object]] = []
    for order, line_idx in enumerate(non_empty_indices, start=1):
        citation_id = f"txt:{order}"
        original_line = lines[line_idx]
        mutated_line, notes = _mutate_txt_line(citation_id, original_line)
        lines[line_idx] = mutated_line
        manifest_items.append(
            {
                "citation_id": citation_id,
                "mutation_count": len(notes),
                "mutations": notes,
                "mutated_fields_core": _mutated_fields(citation_id)[0],
                "mutated_fields_all": _mutated_fields(citation_id)[1],
                "before_excerpt": original_line[:220],
                "after_excerpt": mutated_line[:220],
            }
        )

    return "\n".join(lines) + "\n", manifest_items


def _validate_generated_files(tex_path: Path, txt_path: Path) -> None:
    cc, _ = load_crossref_checker()
    tex_articles = cc.load_articles_from_text(str(tex_path))
    txt_articles = cc.load_articles_from_text(str(txt_path))

    tex_ids = [a.citation_id for a in tex_articles]
    txt_ids = [a.citation_id for a in txt_articles]
    if tex_ids != EXPECTED_TEX_IDS:
        raise ValueError(f"Generated tex parse check failed. Expected {EXPECTED_TEX_IDS}, got {tex_ids}")
    if txt_ids != EXPECTED_TXT_IDS:
        raise ValueError(f"Generated txt parse check failed. Expected {EXPECTED_TXT_IDS}, got {txt_ids}")


def generate_benchmarks(
    groundtruth_tex: Path,
    groundtruth_txt: Path,
    out_tex: Path,
    out_txt: Path,
    manifest_path: Path,
) -> Dict[str, object]:
    tex_in = groundtruth_tex.read_text(encoding="utf-8-sig")
    txt_in = groundtruth_txt.read_text(encoding="utf-8-sig")

    tex_out, tex_manifest = mutate_tex_content(tex_in)
    txt_out, txt_manifest = mutate_txt_content(txt_in)

    out_tex.write_text(tex_out, encoding="utf-8")
    out_txt.write_text(txt_out, encoding="utf-8")
    _validate_generated_files(out_tex, out_txt)

    manifest: Dict[str, object] = {
        "generator_version": "1.0",
        "groundtruth": {"tex": str(groundtruth_tex), "txt": str(groundtruth_txt)},
        "outputs": {"tex": str(out_tex), "txt": str(out_txt)},
        "mutations": {"tex": tex_manifest, "txt": txt_manifest},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic benchmark bibliography files from ground truth.")
    parser.add_argument("--groundtruth-tex", required=True, help="Path to groundtruth tex file")
    parser.add_argument("--groundtruth-txt", required=True, help="Path to groundtruth txt file")
    parser.add_argument("--out-tex", required=True, help="Path to output benchmark tex file")
    parser.add_argument("--out-txt", required=True, help="Path to output benchmark txt file")
    parser.add_argument("--manifest", required=True, help="Path to output manifest json")
    args = parser.parse_args()

    try:
        manifest = generate_benchmarks(
            groundtruth_tex=Path(args.groundtruth_tex),
            groundtruth_txt=Path(args.groundtruth_txt),
            out_tex=Path(args.out_tex),
            out_txt=Path(args.out_txt),
            manifest_path=Path(args.manifest),
        )
    except Exception as exc:
        print(f"[benchmark-generate] ERROR: {exc}")
        return 1

    tex_count = len((manifest["mutations"])["tex"])  # type: ignore[index]
    txt_count = len((manifest["mutations"])["txt"])  # type: ignore[index]
    print(f"[benchmark-generate] Wrote benchmark files and manifest.")
    print(f"[benchmark-generate] tex citations mutated: {tex_count}")
    print(f"[benchmark-generate] txt citations mutated: {txt_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build the current calibrated board as twelve A4 tiles and one full-size page."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dnd_board_game.physical_cards.handout_files import (
    HANDOUTS_ROOT, HANDOUT_BUILD_ROOT, pdf_pages, publish_pdf,
)
from dnd_board_game.physical_cards.handout_maps import (
    map_specification, render_a4_html, render_full_html,
)
from dnd_board_game.physical_cards.mana_print_files import render_pdf


def write_map_sources(work: Path) -> dict[str, Path]:
    """Keep generated HTML and the physical specification outside handouts."""
    work.mkdir(parents=True, exist_ok=True)
    paths = {"map_a4": work / "map_a4.html", "map_full": work / "map_full.html"}
    paths["map_a4"].write_text(render_a4_html(), encoding="utf-8")
    paths["map_full"].write_text(render_full_html(), encoding="utf-8")
    (work / "map_specification.json").write_text(
        json.dumps(map_specification(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return paths


def build_maps(output: Path = HANDOUTS_ROOT,
               work: Path = HANDOUT_BUILD_ROOT / "maps") -> dict[str, Path]:
    sources = write_map_sources(work)
    staged = {key: work / f"{key}.pdf" for key in sources}
    # Rendering is sequential, and both source PDFs exist before publication.
    for key, source in sources.items():
        render_pdf(source, staged[key])
    for key, source in staged.items():
        expected = 12 if key == "map_a4" else 1
        actual = pdf_pages(source)
        if actual != expected:
            raise RuntimeError(f"{key}: oczekiwano {expected} stron, otrzymano {actual}.")
    return {key: publish_pdf(source, output / f"{key}.pdf") for key, source in staged.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HANDOUTS_ROOT)
    parser.add_argument("--work", type=Path, default=HANDOUT_BUILD_ROOT / "maps")
    parser.add_argument("--html-only", action="store_true")
    args = parser.parse_args()
    paths = write_map_sources(args.work) if args.html_only else build_maps(args.output, args.work)
    for key, path in paths.items():
        print(f"{key}: {path}", flush=True)


if __name__ == "__main__":
    main()

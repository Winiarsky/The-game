from __future__ import annotations

import argparse
from pathlib import Path

from dnd_board_game.physical_cards.hero_card_sheet import generate_hero_card_sheet


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wygeneruj 12 dwustronnych kart bohaterów na arkuszach A4."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--preview-dir", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = generate_hero_card_sheet(
        args.output,
        manifest_path=args.manifest,
        preview_dir=args.preview_dir,
        overwrite=args.overwrite,
    )
    print(f"PDF: {result.pdf_path}")
    print(f"Manifest: {result.manifest_path}")
    print(f"Karty: {result.card_count}; strony: {result.page_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

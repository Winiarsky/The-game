from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from dnd_board_game.physical_cards.character_card_sets import (
    CHARACTER_DECKS,
    generate_character_sheet_bw_pdf,
    generate_combined_character_sheets_bw_pdf,
    generate_character_card_set_bw_test,
    generate_character_card_set,
)
from dnd_board_game.character_creation import PLAYABLE_HERO_IDS


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wygeneruj osobne zestawy kart dla siedmiu grywalnych archetypów."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("assets/physical_cards/character_sets"),
    )
    parser.add_argument(
        "--actor",
        action="append",
        choices=tuple(CHARACTER_DECKS),
        help="Bohater do wygenerowania; bez parametru generuje wszystkie zestawy.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--bw-test-only",
        action="store_true",
        help="Generuj czarno-białe awersy bez rewersów oraz tonerowe dossier i statystyki.",
    )
    args = parser.parse_args()
    actor_ids = tuple(args.actor or PLAYABLE_HERO_IDS)
    if args.bw_test_only:
        bw_dir = args.output_dir / "bw_test"
        generated_paths: list[Path] = []
        for actor_id in actor_ids:
            output_path = bw_dir / f"card_set_{actor_id}_bw_test.pdf"
            result = generate_character_card_set_bw_test(
                actor_id,
                output_path,
                preview_dir=bw_dir / "previews" / actor_id,
                overwrite=args.overwrite,
            )
            generated_paths.append(result.pdf_path)
            print(
                f"{actor_id}: {result.pdf_path} "
                f"({result.card_count} kart, {result.page_count} stron, bez rewersów)"
            )
        pdfunite = shutil.which("pdfunite")
        if pdfunite:
            combined = bw_dir / "card_sets_bw_test.pdf"
            temporary = bw_dir / ".card_sets_bw_test.tmp.pdf"
            if temporary.exists():
                temporary.unlink()
            subprocess.run(
                [pdfunite, *(str(path) for path in generated_paths), str(temporary)],
                check=True,
            )
            temporary.replace(combined)
            print(f"zbiorczy: {combined}")
        return 0
    for actor_id in actor_ids:
        output_path = args.output_dir / f"card_set_{actor_id}.pdf"
        result = generate_character_card_set(
            actor_id,
            output_path,
            preview_dir=args.output_dir / "previews" / actor_id,
            overwrite=args.overwrite,
        )
        print(
            f"{actor_id}: {result.pdf_path} "
            f"({result.card_count} kart, {result.page_count} stron)"
        )
        sheet_path = generate_character_sheet_bw_pdf(
            actor_id,
            args.output_dir / "character_sheets_bw" / f"character_sheet_{actor_id}_bw.pdf",
            overwrite=args.overwrite,
        )
        print(f"{actor_id}: {sheet_path} (1 strona A4, czarny toner)")
    combined_path = generate_combined_character_sheets_bw_pdf(
        actor_ids,
        args.output_dir / "character_sheets_bw" / "character_sheets_bw.pdf",
        overwrite=args.overwrite,
    )
    print(f"zbiorczy: {combined_path} ({len(actor_ids)} stron A4)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

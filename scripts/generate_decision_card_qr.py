from __future__ import annotations

import argparse
from pathlib import Path

from dnd_board_game.physical_cards import (
    DECISION_CARD_QR_VERSION,
    DecisionCardActionKind,
    build_decision_card_qr_payload,
    generate_decision_card_qr,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wygeneruj wersjonowany kod QR dla fizycznej karty decyzji."
    )
    parser.add_argument(
        "--kind",
        required=True,
        choices=[kind.value for kind in DecisionCardActionKind],
        help="Rodzaj źródła działania.",
    )
    parser.add_argument(
        "--source-id",
        required=True,
        help="Stabilne source_id w formacie snake_case.",
    )
    parser.add_argument(
        "--label",
        required=True,
        help="Czytelny kod karty zapisywany w metadanych, np. EB-01.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Docelowy plik .png albo .svg.",
    )
    parser.add_argument(
        "--version",
        type=int,
        default=DECISION_CARD_QR_VERSION,
        help=f"Wersja payloadu (obecnie: {DECISION_CARD_QR_VERSION}).",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=6,
        help="Liczba pikseli/jednostek na moduł QR (domyślnie: 6).",
    )
    parser.add_argument(
        "--quiet-zone",
        type=int,
        default=4,
        help="Biały margines w modułach, minimum 4 (domyślnie: 4).",
    )
    parser.add_argument(
        "--error-correction",
        choices=("L", "M", "Q", "H"),
        default="H",
        help="Poziom korekcji błędów (domyślnie: H).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Pozwól zastąpić istniejący obraz i metadane.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = build_decision_card_qr_payload(
        args.kind,
        args.source_id,
        version=args.version,
    )
    asset = generate_decision_card_qr(
        payload,
        args.output,
        label=args.label,
        scale=args.scale,
        quiet_zone_modules=args.quiet_zone,
        error_correction=args.error_correction,
        overwrite=args.overwrite,
    )
    print(f"QR: {asset.image_path}")
    print(f"Metadane: {asset.metadata_path}")
    print(f"Payload: {asset.payload}")
    print(
        "Symbol: "
        f"{asset.module_count} modułów + "
        f"{asset.quiet_zone_modules} moduły marginesu z każdej strony"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

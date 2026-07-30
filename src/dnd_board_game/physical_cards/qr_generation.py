from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import segno

from .qr_payload import parse_decision_card_qr_payload


SUPPORTED_QR_OUTPUT_SUFFIXES = frozenset({".png", ".svg"})
SUPPORTED_ERROR_CORRECTION_LEVELS = frozenset({"L", "M", "Q", "H"})


@dataclass(frozen=True, slots=True)
class GeneratedQrAsset:
    image_path: Path
    metadata_path: Path
    payload: str
    module_count: int
    total_module_count: int
    scale: int
    quiet_zone_modules: int
    error_correction: str


def generate_decision_card_qr(
    payload: str,
    output_path: str | Path,
    *,
    label: str,
    scale: int = 6,
    quiet_zone_modules: int = 4,
    error_correction: str = "H",
    overwrite: bool = False,
) -> GeneratedQrAsset:
    parsed = parse_decision_card_qr_payload(payload)
    path = Path(output_path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_QR_OUTPUT_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_QR_OUTPUT_SUFFIXES))
        raise ValueError(f"QR output must use one of these suffixes: {supported}.")
    if not label.strip():
        raise ValueError("Decision-card label cannot be empty.")
    if not isinstance(scale, int) or isinstance(scale, bool) or scale < 1:
        raise ValueError("QR scale must be a positive integer.")
    if (
        not isinstance(quiet_zone_modules, int)
        or isinstance(quiet_zone_modules, bool)
        or quiet_zone_modules < 4
    ):
        raise ValueError("QR quiet zone must be at least 4 modules.")
    normalized_error = error_correction.upper()
    if normalized_error not in SUPPORTED_ERROR_CORRECTION_LEVELS:
        raise ValueError("QR error correction must be one of L, M, Q or H.")

    metadata_path = Path(f"{path}.json")
    if not overwrite:
        existing = [candidate for candidate in (path, metadata_path) if candidate.exists()]
        if existing:
            raise FileExistsError(f"Refusing to overwrite existing file: {existing[0]}")

    path.parent.mkdir(parents=True, exist_ok=True)
    qr = segno.make(
        payload,
        error=normalized_error,
        micro=False,
        boost_error=False,
    )
    module_count = qr.symbol_size(scale=1, border=0)[0]
    total_module_count = qr.symbol_size(
        scale=1,
        border=quiet_zone_modules,
    )[0]
    qr.save(
        path,
        scale=scale,
        border=quiet_zone_modules,
        dark="#000000",
        light="#ffffff",
    )

    asset = GeneratedQrAsset(
        image_path=path,
        metadata_path=metadata_path,
        payload=payload,
        module_count=module_count,
        total_module_count=total_module_count,
        scale=scale,
        quiet_zone_modules=quiet_zone_modules,
        error_correction=normalized_error,
    )
    metadata = {
        "schema": "dnd_board_game.decision_card_qr",
        "schema_version": 1,
        "label": label.strip(),
        "action_kind": parsed.action_kind.value,
        "source_id": parsed.source_id,
        **{
            key: str(value) if isinstance(value, Path) else value
            for key, value in asdict(asset).items()
        },
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return asset

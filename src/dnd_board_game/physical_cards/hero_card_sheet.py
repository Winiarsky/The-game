"""Printable duplex poker-size cards for selecting the curated heroes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from dnd_board_game.character_creation import HERO_ARCHETYPES_BY_ID

from .qr_payload import build_actor_card_qr_payload
from .universal_card_sheet import (
    A4_SIZE_PX,
    BLEED_PX,
    CARD_ART_SIZE_PX,
    CARD_HEIGHT_MM,
    CARD_SIZE_PX,
    CARD_WIDTH_MM,
    DPI,
    PROJECT_ROOT,
    _draw_crop_marks,
    _font,
    _mm,
    _qr_image,
    render_universal_card_back,
)


HERO_PORTRAIT_ROOT = (
    PROJECT_ROOT / "assets" / "character_portraits" / "default_roster_v2"
)
PORTRAIT_CROP_CENTER = (0.5, 0.0)
PORTRAIT_VERTICAL_OFFSET_PX = BLEED_PX


@dataclass(frozen=True, slots=True)
class HeroCardPrintSpec:
    actor_id: str
    name: str
    class_name: str
    accent: tuple[int, int, int]

    @property
    def profile(self):
        return HERO_ARCHETYPES_BY_ID[self.actor_id]

    @property
    def payload(self) -> str:
        return build_actor_card_qr_payload(self.actor_id)


@dataclass(frozen=True, slots=True)
class HeroCardSheetResult:
    pdf_path: Path
    manifest_path: Path
    card_count: int
    page_count: int


HERO_CARD_SPECS = (
    HeroCardPrintSpec("brakka", "Brakka", "Barbarzyńca", (166, 67, 46)),
    HeroCardPrintSpec("lorian", "Lorian", "Bard", (154, 81, 140)),
    HeroCardPrintSpec("dagna", "Dagna", "Kleryczka", (211, 164, 73)),
    HeroCardPrintSpec("sylwen", "Sylwen", "Druidka", (75, 132, 82)),
    HeroCardPrintSpec("garran", "Garran", "Wojownik", (85, 118, 148)),
    HeroCardPrintSpec("pim", "Pim", "Mnich", (196, 130, 49)),
    HeroCardPrintSpec("rhogar", "Rhogar", "Paladyn", (192, 93, 53)),
    HeroCardPrintSpec("erynd", "Erynd", "Łowca", (75, 126, 91)),
    HeroCardPrintSpec("mira", "Mira", "Łotrzyca", (111, 81, 139)),
    HeroCardPrintSpec("veyra", "Veyra", "Czarownica", (156, 63, 112)),
    HeroCardPrintSpec("kael", "Kael", "Czarnoksiężnik", (105, 76, 145)),
    HeroCardPrintSpec("nimra", "Nimra", "Czarodziejka", (61, 112, 175)),
)


def render_hero_card_front(spec: HeroCardPrintSpec) -> Image.Image:
    width, height = CARD_ART_SIZE_PX
    trim_left = BLEED_PX
    trim_top = BLEED_PX
    trim_right = trim_left + CARD_SIZE_PX[0] - 1
    trim_bottom = trim_top + CARD_SIZE_PX[1] - 1
    portrait_bottom = trim_top + _mm(54)
    image = Image.new("RGB", CARD_ART_SIZE_PX, (8, 10, 12))
    portrait_path = HERO_PORTRAIT_ROOT / f"{spec.actor_id}.png"
    with Image.open(portrait_path) as source:
        portrait = ImageOps.fit(
            source.convert("RGB"),
            (width, portrait_bottom + BLEED_PX),
            method=Image.Resampling.LANCZOS,
            centering=PORTRAIT_CROP_CENTER,
        )
    top_bleed = portrait.crop((0, 0, width, 1)).resize(
        (width, PORTRAIT_VERTICAL_OFFSET_PX)
    )
    image.paste(top_bleed, (0, 0))
    image.paste(portrait, (0, PORTRAIT_VERTICAL_OFFSET_PX))
    top_bleed.close()
    portrait.close()
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, width, height), fill=(3, 5, 7, 18))
    draw.rectangle(
        (trim_left, portrait_bottom - _mm(12), trim_right, trim_bottom),
        fill=(5, 7, 10, 235),
    )
    draw.rectangle(
        (trim_left, trim_top, trim_right, trim_bottom),
        outline=(*spec.accent, 255),
        width=_mm(0.7),
    )
    draw.rectangle(
        (trim_left + _mm(2), trim_top + _mm(2), trim_right - _mm(2), trim_bottom - _mm(2)),
        outline=(211, 184, 137, 120),
        width=max(1, _mm(0.25)),
    )
    draw.text(
        (trim_left + _mm(4), portrait_bottom - _mm(9)),
        spec.name.upper(),
        font=_font(_mm(5.0), serif=True, bold=True),
        fill=(245, 235, 216),
    )
    draw.text(
        (trim_left + _mm(4), portrait_bottom - _mm(2)),
        f"{spec.class_name} · poziom 1",
        font=_font(_mm(2.7), bold=True),
        fill=spec.accent,
    )
    role_width = CARD_SIZE_PX[0] - _mm(31)
    role = spec.profile.role
    role_font = _font(_mm(2.35))
    words = role.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=role_font)[2] > role_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    draw.multiline_text(
        (trim_left + _mm(4), portrait_bottom + _mm(4)),
        "\n".join(lines),
        font=role_font,
        fill=(204, 202, 195),
        spacing=_mm(0.5),
    )
    draw.text(
        (trim_left + _mm(4), trim_bottom - _mm(8)),
        spec.profile.helper_code,
        font=_font(_mm(2.6), bold=True),
        fill=(231, 218, 197),
    )
    qr = _qr_image(spec.payload, _mm(23))
    qr_left = trim_right - _mm(4) - qr.width
    qr_top = trim_bottom - _mm(4) - qr.height
    image.paste(qr, (qr_left, qr_top))
    return image


def render_hero_card_back() -> Image.Image:
    image = render_universal_card_back()
    draw = ImageDraw.Draw(image, "RGBA")
    center_x = CARD_ART_SIZE_PX[0] // 2
    trim_top = BLEED_PX
    trim_bottom = trim_top + CARD_SIZE_PX[1] - 1
    draw.rounded_rectangle(
        (
            BLEED_PX + _mm(4),
            trim_top + _mm(6),
            BLEED_PX + CARD_SIZE_PX[0] - _mm(4),
            trim_top + _mm(18),
        ),
        radius=_mm(2),
        fill=(5, 7, 9, 255),
        outline=(153, 116, 72, 180),
        width=_mm(0.3),
    )
    draw.rounded_rectangle(
        (
            BLEED_PX + _mm(4),
            trim_bottom - _mm(16),
            BLEED_PX + CARD_SIZE_PX[0] - _mm(4),
            trim_bottom - _mm(5),
        ),
        radius=_mm(2),
        fill=(5, 7, 9, 255),
        outline=(114, 85, 137, 190),
        width=_mm(0.3),
    )
    draw.text(
        (center_x, trim_top + _mm(10)),
        "KARTA BOHATERA",
        font=_font(_mm(4.0), serif=True, bold=True),
        fill=(235, 224, 207),
        anchor="ma",
    )
    draw.text(
        (center_x, trim_bottom - _mm(13)),
        "TOŻSAMOŚĆ",
        font=_font(_mm(3.0), bold=True),
        fill=(155, 117, 177),
        anchor="ma",
    )
    return image


def _positions() -> tuple[tuple[int, int], ...]:
    horizontal_gap = _mm(10)
    vertical_gap = _mm(12)
    total_width = 2 * CARD_ART_SIZE_PX[0] + horizontal_gap
    total_height = 2 * CARD_ART_SIZE_PX[1] + vertical_gap
    start_x = (A4_SIZE_PX[0] - total_width) // 2
    start_y = (A4_SIZE_PX[1] - total_height) // 2
    return (
        (start_x, start_y),
        (start_x + CARD_ART_SIZE_PX[0] + horizontal_gap, start_y),
        (start_x, start_y + CARD_ART_SIZE_PX[1] + vertical_gap),
        (
            start_x + CARD_ART_SIZE_PX[0] + horizontal_gap,
            start_y + CARD_ART_SIZE_PX[1] + vertical_gap,
        ),
    )


def _sheet(
    cards: tuple[Image.Image, ...],
    *,
    backs: bool,
    sheet_number: int,
) -> Image.Image:
    sheet = Image.new("RGB", A4_SIZE_PX, "white")
    draw = ImageDraw.Draw(sheet)
    positions = _positions()
    if backs:
        positions = tuple(
            (A4_SIZE_PX[0] - left - CARD_ART_SIZE_PX[0], top)
            for left, top in positions
        )
    for card, (left, top) in zip(cards, positions, strict=True):
        sheet.paste(card, (left, top))
        _draw_crop_marks(draw, left, top)
    label = (
        f"ARKUSZ {sheet_number} · REWERSY · odwróć po długiej krawędzi"
        if backs
        else f"ARKUSZ {sheet_number} · PRZODY"
    )
    draw.text((_mm(10), _mm(7)), label, font=_font(_mm(3), bold=True), fill=(25, 25, 25))
    draw.text(
        (_mm(10), A4_SIZE_PX[1] - _mm(10)),
        "Druk 100% · bez dopasowania · po cięciu 63 × 88 mm · spad 3 mm",
        font=_font(_mm(2.2)),
        fill=(45, 45, 45),
    )
    return sheet


def generate_hero_card_sheet(
    output_path: str | Path,
    *,
    manifest_path: str | Path | None = None,
    preview_dir: str | Path | None = None,
    overwrite: bool = False,
) -> HeroCardSheetResult:
    pdf_path = Path(output_path)
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Arkusz kart bohaterów musi mieć rozszerzenie .pdf.")
    resolved_manifest = Path(manifest_path) if manifest_path else Path(f"{pdf_path}.json")
    if not overwrite:
        for candidate in (pdf_path, resolved_manifest):
            if candidate.exists():
                raise FileExistsError(f"Refusing to overwrite existing file: {candidate}")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_manifest.parent.mkdir(parents=True, exist_ok=True)
    pages: list[Image.Image] = []
    previews = Path(preview_dir) if preview_dir else None
    if previews:
        previews.mkdir(parents=True, exist_ok=True)
    for offset in range(0, len(HERO_CARD_SPECS), 4):
        group = HERO_CARD_SPECS[offset : offset + 4]
        fronts = tuple(render_hero_card_front(spec) for spec in group)
        back = render_hero_card_back()
        backs = tuple(back.copy() for _ in group)
        sheet_no = offset // 4 + 1
        front_sheet = _sheet(fronts, backs=False, sheet_number=sheet_no)
        back_sheet = _sheet(backs, backs=True, sheet_number=sheet_no)
        pages.extend((front_sheet, back_sheet))
        if previews:
            front_sheet.save(previews / f"sheet_{sheet_no}_fronts.png", dpi=(DPI, DPI))
            back_sheet.save(previews / f"sheet_{sheet_no}_backs.png", dpi=(DPI, DPI))
        for image in (*fronts, *backs, back):
            image.close()
    pages[0].save(
        pdf_path,
        "PDF",
        resolution=DPI,
        save_all=True,
        append_images=pages[1:],
        quality=95,
    )
    manifest = {
        "schema": "dnd_board_game.hero_card_sheet",
        "schema_version": 1,
        "dpi": DPI,
        "page": {"format": "A4", "cards_per_sheet": 4},
        "card": {
            "trim_width_mm": CARD_WIDTH_MM,
            "trim_height_mm": CARD_HEIGHT_MM,
            "bleed_mm": 3,
            "qr_payload_schema": "dndbg:v1:actor:<actor_id>",
        },
        "duplex": {"sheets": 3, "pages": 6, "flip": "long_edge"},
        "cards": [
            {
                "actor_id": spec.actor_id,
                "name": spec.name,
                "class_name": spec.class_name,
                "role": spec.profile.role,
                "human_code": spec.profile.helper_code,
                "payload": spec.payload,
                "portrait": str(HERO_PORTRAIT_ROOT / f"{spec.actor_id}.png"),
            }
            for spec in HERO_CARD_SPECS
        ],
    }
    resolved_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for page in pages:
        page.close()
    return HeroCardSheetResult(pdf_path, resolved_manifest, len(HERO_CARD_SPECS), 6)


__all__ = [
    "HERO_CARD_SPECS",
    "HeroCardPrintSpec",
    "HeroCardSheetResult",
    "generate_hero_card_sheet",
    "render_hero_card_front",
    "render_hero_card_back",
]

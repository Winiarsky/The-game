from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path

import segno
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .qr_payload import build_decision_card_qr_payload


DPI = 300
MM_PER_INCH = 25.4
A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297
CARD_WIDTH_MM = 63
CARD_HEIGHT_MM = 88
BLEED_MM = 3
SAFE_MARGIN_MM = 4
QR_TARGET_MM = 20
PROJECT_ROOT = Path(__file__).resolve().parents[3]
UNIVERSAL_CARD_ART_ROOT = (
    PROJECT_ROOT / "assets" / "physical_cards" / "universal_controls" / "art"
)
UNIVERSAL_CARD_BACK_ASSET = "universal_card_back_background.png"


def _mm(value: float) -> int:
    return round(value / MM_PER_INCH * DPI)


A4_SIZE_PX = (_mm(A4_WIDTH_MM), _mm(A4_HEIGHT_MM))
CARD_SIZE_PX = (_mm(CARD_WIDTH_MM), _mm(CARD_HEIGHT_MM))
BLEED_PX = _mm(BLEED_MM)
CARD_ART_SIZE_PX = (
    CARD_SIZE_PX[0] + 2 * BLEED_PX,
    CARD_SIZE_PX[1] + 2 * BLEED_PX,
)


@dataclass(frozen=True, slots=True)
class UniversalCardPrintSpec:
    source_id: str
    title: str
    polish_title: str
    purpose: str
    instruction: str
    human_code: str
    accent: tuple[int, int, int]
    symbol: str
    background_asset: str

    @property
    def payload(self) -> str:
        return build_decision_card_qr_payload("universal", self.source_id)


@dataclass(frozen=True, slots=True)
class UniversalCardSheetResult:
    pdf_path: Path
    manifest_path: Path
    card_count: int
    page_count: int


UNIVERSAL_CARD_SPECS = (
    UniversalCardPrintSpec(
        source_id="accept",
        title="ACCEPT",
        polish_title="AKCEPTUJ",
        purpose="POTWIERDŹ • DALEJ",
        instruction=(
            "Zatwierdza aktualnie widoczną decyzję. "
            "Nie omija kosztów ani walidacji."
        ),
        human_code="AC-01",
        accent=(42, 148, 113),
        symbol="check",
        background_asset="accept_gate_background.png",
    ),
    UniversalCardPrintSpec(
        source_id="decline",
        title="DECLINE",
        polish_title="ODRZUĆ",
        purpose="ODRZUĆ • WRÓĆ",
        instruction=(
            "Odrzuca lub anuluje aktualny krok. "
            "Nie cofa rozstrzygniętej akcji."
        ),
        human_code="DC-01",
        accent=(169, 65, 67),
        symbol="cross",
        background_asset="decline_sealed_portal_background.png",
    ),
)


def _font(size: int, *, serif: bool = False, bold: bool = False) -> ImageFont.FreeTypeFont:
    family = "dejavu"
    if serif:
        filename = "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf"
    else:
        filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    candidates = (
        Path("/usr/share/fonts/truetype") / family / filename,
        Path("/usr/share/fonts/truetype/liberation2")
        / (
            "LiberationSerif-Bold.ttf"
            if serif and bold
            else "LiberationSerif-Regular.ttf"
            if serif
            else "LiberationSans-Bold.ttf"
            if bold
            else "LiberationSans-Regular.ttf"
        ),
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size)
        except OSError:
            continue
    raise RuntimeError("Nie znaleziono fontu potrzebnego do wygenerowania kart.")


def _centered_text(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    top: int,
    text: str,
    *,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0]
    draw.text((center_x - width // 2, top), text, font=font, fill=fill)


def _wrapped_centered_text(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    top: int,
    max_width: int,
    text: str,
    *,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    spacing: int,
) -> None:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        width = draw.textbbox((0, 0), candidate, font=font)[2]
        if current and width > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    draw.multiline_text(
        (center_x, top),
        "\n".join(lines),
        font=font,
        fill=fill,
        anchor="ma",
        align="center",
        spacing=spacing,
    )


def _qr_image(payload: str, target_size_px: int) -> Image.Image:
    qr = segno.make(payload, error="H", micro=False, boost_error=False)
    total_modules = qr.symbol_size(scale=1, border=4)[0]
    scale = max(1, target_size_px // total_modules)
    stream = io.BytesIO()
    qr.save(
        stream,
        kind="png",
        scale=scale,
        border=4,
        dark="#000000",
        light="#ffffff",
    )
    stream.seek(0)
    with Image.open(stream) as image:
        return image.convert("RGB")


def _card_background(asset_name: str) -> Image.Image:
    path = UNIVERSAL_CARD_ART_ROOT / asset_name
    with Image.open(path) as source:
        return ImageOps.fit(
            source.convert("RGB"),
            CARD_ART_SIZE_PX,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )


def _draw_symbol(
    draw: ImageDraw.ImageDraw,
    spec: UniversalCardPrintSpec,
    center_x: int,
    center_y: int,
    radius: int,
) -> None:
    accent = spec.accent
    draw.ellipse(
        (
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
        ),
        fill=(7, 10, 12, 205),
        outline=accent,
        width=_mm(1.2),
    )
    line_width = _mm(1.7)
    if spec.symbol == "check":
        draw.line(
            (
                center_x - radius // 2,
                center_y,
                center_x - radius // 8,
                center_y + radius // 3,
                center_x + radius // 2,
                center_y - radius // 3,
            ),
            fill=accent,
            width=line_width,
            joint="curve",
        )
    else:
        offset = radius // 2
        draw.line(
            (
                center_x - offset,
                center_y - offset,
                center_x + offset,
                center_y + offset,
            ),
            fill=accent,
            width=line_width,
        )
        draw.line(
            (
                center_x + offset,
                center_y - offset,
                center_x - offset,
                center_y + offset,
            ),
            fill=accent,
            width=line_width,
        )


def render_universal_card_front(spec: UniversalCardPrintSpec) -> Image.Image:
    width, height = CARD_ART_SIZE_PX
    trim_left = BLEED_PX
    trim_top = BLEED_PX
    trim_right = trim_left + CARD_SIZE_PX[0] - 1
    trim_bottom = trim_top + CARD_SIZE_PX[1] - 1
    safe = _mm(SAFE_MARGIN_MM)
    image = _card_background(spec.background_asset)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, width - 1, height - 1), fill=(4, 6, 8, 42))
    draw.rectangle(
        (trim_left, trim_top, trim_right, trim_bottom),
        outline=(153, 116, 72),
        width=_mm(0.7),
    )
    draw.rectangle(
        (
            trim_left + safe // 2,
            trim_top + safe // 2,
            trim_right - safe // 2,
            trim_bottom - safe // 2,
        ),
        outline=(74, 63, 55),
        width=_mm(0.25),
    )
    draw.rectangle(
        (
            trim_left + safe,
            trim_top + safe,
            trim_right - safe,
            trim_top + _mm(16),
        ),
        fill=(5, 8, 10, 205),
        outline=(*spec.accent, 210),
        width=_mm(0.35),
    )
    draw.rounded_rectangle(
        (
            trim_left + safe,
            trim_top + _mm(43),
            trim_right - safe,
            trim_bottom - safe,
        ),
        radius=_mm(2),
        fill=(5, 7, 9, 210),
        outline=(153, 116, 72, 150),
        width=_mm(0.25),
    )
    center_x = width // 2
    _centered_text(
        draw,
        center_x,
        trim_top + _mm(5.2),
        spec.title,
        font=_font(_mm(4.8), serif=True, bold=True),
        fill=(241, 231, 213),
    )
    _centered_text(
        draw,
        center_x,
        trim_top + _mm(12.0),
        spec.polish_title,
        font=_font(_mm(2.6), bold=True),
        fill=spec.accent,
    )
    _draw_symbol(
        draw,
        spec,
        center_x,
        trim_top + _mm(32),
        _mm(10),
    )
    _centered_text(
        draw,
        center_x,
        trim_top + _mm(44.5),
        spec.purpose,
        font=_font(_mm(2.8), bold=True),
        fill=(225, 213, 193),
    )
    _wrapped_centered_text(
        draw,
        center_x,
        trim_top + _mm(50),
        CARD_SIZE_PX[0] - 2 * (safe + _mm(2)),
        spec.instruction,
        font=_font(_mm(2.25)),
        fill=(190, 187, 181),
        spacing=_mm(0.7),
    )
    qr = _qr_image(spec.payload, _mm(QR_TARGET_MM))
    qr_left = center_x - qr.width // 2
    qr_top = trim_bottom - safe - qr.height - _mm(4)
    image.paste(qr, (qr_left, qr_top))
    _centered_text(
        draw,
        center_x,
        qr_top + qr.height + _mm(1),
        spec.human_code,
        font=_font(_mm(2.5), bold=True),
        fill=(225, 213, 193),
    )
    return image


def render_universal_card_back() -> Image.Image:
    width, height = CARD_ART_SIZE_PX
    trim_left = BLEED_PX
    trim_top = BLEED_PX
    trim_right = trim_left + CARD_SIZE_PX[0] - 1
    trim_bottom = trim_top + CARD_SIZE_PX[1] - 1
    safe = _mm(SAFE_MARGIN_MM)
    image = _card_background(UNIVERSAL_CARD_BACK_ASSET)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, width - 1, height - 1), fill=(4, 5, 7, 28))
    draw.rectangle(
        (trim_left, trim_top, trim_right, trim_bottom),
        outline=(153, 116, 72),
        width=_mm(0.7),
    )
    draw.rectangle(
        (
            trim_left + safe // 2,
            trim_top + safe // 2,
            trim_right - safe // 2,
            trim_bottom - safe // 2,
        ),
        outline=(74, 63, 55),
        width=_mm(0.25),
    )
    center_x = width // 2
    center_y = height // 2
    draw.rounded_rectangle(
        (
            trim_left + safe,
            trim_top + _mm(6),
            trim_right - safe,
            trim_top + _mm(18),
        ),
        radius=_mm(2),
        fill=(5, 7, 9, 195),
        outline=(153, 116, 72, 145),
        width=_mm(0.3),
    )
    draw.rounded_rectangle(
        (
            trim_left + safe,
            trim_bottom - _mm(16),
            trim_right - safe,
            trim_bottom - _mm(5),
        ),
        radius=_mm(2),
        fill=(5, 7, 9, 195),
        outline=(114, 85, 137, 170),
        width=_mm(0.3),
    )
    draw.polygon(
        (
            (center_x, center_y - _mm(6)),
            (center_x + _mm(5), center_y),
            (center_x, center_y + _mm(6)),
            (center_x - _mm(5), center_y),
        ),
        outline=(211, 184, 137, 210),
    )
    _centered_text(
        draw,
        center_x,
        trim_top + _mm(10),
        "KARTA DECYZJI",
        font=_font(_mm(4.3), serif=True, bold=True),
        fill=(235, 224, 207),
    )
    _centered_text(
        draw,
        center_x,
        trim_bottom - _mm(13),
        "UNIWERSALNA",
        font=_font(_mm(3.0), bold=True),
        fill=(155, 117, 177),
    )
    return image


def _sheet_positions(card_count: int) -> tuple[tuple[int, int], ...]:
    gap = _mm(12)
    total_width = card_count * CARD_ART_SIZE_PX[0] + (card_count - 1) * gap
    start_x = (A4_SIZE_PX[0] - total_width) // 2
    top = _mm(28)
    return tuple(
        (start_x + index * (CARD_ART_SIZE_PX[0] + gap), top)
        for index in range(card_count)
    )


def _draw_crop_marks(draw: ImageDraw.ImageDraw, left: int, top: int) -> None:
    trim_left = left + BLEED_PX
    trim_top = top + BLEED_PX
    trim_right = trim_left + CARD_SIZE_PX[0]
    trim_bottom = trim_top + CARD_SIZE_PX[1]
    gap = _mm(1)
    length = _mm(4)
    color = (40, 40, 40)
    width = max(1, _mm(0.2))
    for x in (trim_left, trim_right):
        draw.line((x, trim_top - gap - length, x, trim_top - gap), fill=color, width=width)
        draw.line((x, trim_bottom + gap, x, trim_bottom + gap + length), fill=color, width=width)
    for y in (trim_top, trim_bottom):
        draw.line((trim_left - gap - length, y, trim_left - gap, y), fill=color, width=width)
        draw.line((trim_right + gap, y, trim_right + gap + length, y), fill=color, width=width)


def _render_sheet(
    cards: tuple[Image.Image, ...],
    *,
    reverse_positions: bool,
    page_label: str,
) -> Image.Image:
    sheet = Image.new("RGB", A4_SIZE_PX, "white")
    draw = ImageDraw.Draw(sheet)
    positions = _sheet_positions(len(cards))
    if reverse_positions:
        positions = tuple(reversed(positions))
    for card, (left, top) in zip(cards, positions, strict=True):
        sheet.paste(card, (left, top))
        _draw_crop_marks(draw, left, top)
    draw.text(
        (_mm(12), _mm(10)),
        page_label,
        font=_font(_mm(3.1), bold=True),
        fill=(25, 25, 25),
    )
    draw.text(
        (_mm(12), A4_SIZE_PX[1] - _mm(16)),
        "Druk 100% · bez dopasowania strony · format karty po cięciu 63 × 88 mm · spad 3 mm",
        font=_font(_mm(2.3)),
        fill=(45, 45, 45),
    )
    return sheet


def generate_universal_card_sheet(
    output_path: str | Path,
    *,
    manifest_path: str | Path | None = None,
    preview_dir: str | Path | None = None,
    overwrite: bool = False,
) -> UniversalCardSheetResult:
    pdf_path = Path(output_path)
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Arkusz kart musi mieć rozszerzenie .pdf.")
    resolved_manifest_path = (
        Path(manifest_path)
        if manifest_path is not None
        else Path(f"{pdf_path}.json")
    )
    if not overwrite:
        for candidate in (pdf_path, resolved_manifest_path):
            if candidate.exists():
                raise FileExistsError(f"Refusing to overwrite existing file: {candidate}")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_manifest_path.parent.mkdir(parents=True, exist_ok=True)

    fronts = tuple(render_universal_card_front(spec) for spec in UNIVERSAL_CARD_SPECS)
    back = render_universal_card_back()
    backs = tuple(back.copy() for _ in UNIVERSAL_CARD_SPECS)
    front_sheet = _render_sheet(
        fronts,
        reverse_positions=False,
        page_label="STRONA 1 · PRZODY",
    )
    back_sheet = _render_sheet(
        backs,
        reverse_positions=True,
        page_label="STRONA 2 · REWERSY · odwróć po długiej krawędzi",
    )
    front_sheet.save(
        pdf_path,
        "PDF",
        resolution=DPI,
        save_all=True,
        append_images=[back_sheet],
        quality=95,
    )
    if preview_dir is not None:
        preview_root = Path(preview_dir)
        preview_root.mkdir(parents=True, exist_ok=True)
        front_sheet.save(preview_root / "page_1_fronts.png", dpi=(DPI, DPI))
        back_sheet.save(preview_root / "page_2_backs.png", dpi=(DPI, DPI))

    manifest = {
        "schema": "dnd_board_game.universal_decision_card_sheet",
        "schema_version": 1,
        "dpi": DPI,
        "page": {"format": "A4", "width_mm": A4_WIDTH_MM, "height_mm": A4_HEIGHT_MM},
        "card": {
            "trim_width_mm": CARD_WIDTH_MM,
            "trim_height_mm": CARD_HEIGHT_MM,
            "bleed_mm": BLEED_MM,
            "safe_margin_mm": SAFE_MARGIN_MM,
            "qr_target_mm": QR_TARGET_MM,
        },
        "duplex": {"pages": 2, "flip": "long_edge"},
        "back_background_asset": UNIVERSAL_CARD_BACK_ASSET,
        "cards": [
            {
                "source_id": spec.source_id,
                "title": spec.title,
                "polish_title": spec.polish_title,
                "human_code": spec.human_code,
                "payload": spec.payload,
                "background_asset": spec.background_asset,
            }
            for spec in UNIVERSAL_CARD_SPECS
        ],
    }
    resolved_manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for image in (*fronts, *backs, back, front_sheet, back_sheet):
        image.close()
    return UniversalCardSheetResult(
        pdf_path=pdf_path,
        manifest_path=resolved_manifest_path,
        card_count=len(UNIVERSAL_CARD_SPECS),
        page_count=2,
    )

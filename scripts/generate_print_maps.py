from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
MAP_ROOT = ROOT / "assets" / "print_maps" / "village_watchtower"
SOURCE_ROOT = MAP_ROOT / "source"
PNG_ROOT = MAP_ROOT / "png"
A4_ROOT = MAP_ROOT / "pdf" / "a4"
FULL_SIZE_ROOT = MAP_ROOT / "pdf" / "full_size"

DPI = 300
BOARD_COLUMNS = 20
BOARD_ROWS = 30
FIELD_CM = 2.5
BOARD_WIDTH_CM = BOARD_COLUMNS * FIELD_CM
BOARD_HEIGHT_CM = BOARD_ROWS * FIELD_CM
MAP_SIZE_PX = (
    round(DPI * BOARD_WIDTH_CM / 2.54),
    round(DPI * BOARD_HEIGHT_CM / 2.54),
)
A4_LANDSCAPE_PX = (
    round(DPI * 29.7 / 2.54),
    round(DPI * 21.0 / 2.54),
)
PAGE_MARGIN_PX = round(DPI * 0.5 / 2.54)
TILE_OVERLAP_PX = round(DPI * 0.3 / 2.54)


@dataclass(frozen=True, slots=True)
class PrintMapSpec:
    id: str
    title: str


MAPS = (
    PrintMapSpec("village_market", "Rynek"),
    PrintMapSpec("village_tavern", "Karczma"),
    PrintMapSpec("village_elder_house", "Dom sołtysa"),
    PrintMapSpec("village_forest_road", "Droga do lasu"),
    PrintMapSpec("watchtower_gate", "Brama strażnicy"),
    PrintMapSpec("watchtower_courtyard", "Dziedziniec strażnicy"),
    PrintMapSpec("watchtower_barracks", "Koszary strażnicy"),
    PrintMapSpec("watchtower_tower", "Wieża obserwacyjna"),
)


def _font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _prepare_map(spec: PrintMapSpec) -> Image.Image:
    source = Image.open(SOURCE_ROOT / f"{spec.id}.png").convert("L")
    source = ImageOps.fit(
        source,
        MAP_SIZE_PX,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    source = ImageEnhance.Contrast(source).enhance(1.08)
    source = source.filter(ImageFilter.UnsharpMask(radius=1.4, percent=115, threshold=3))
    image = source.convert("RGB")
    _draw_orientation_marks(image)
    return image


def _draw_orientation_marks(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    inset = round(DPI * 0.35 / 2.54)
    size = round(DPI * 0.35 / 2.54)
    width = max(4, round(DPI * 0.04 / 2.54))
    marks = (
        (inset, inset, 1),
        (image.width - inset - size, inset, 2),
        (inset, image.height - inset - size, 3),
    )
    for left, top, count in marks:
        for index in range(count):
            offset = index * (size // 3)
            draw.rectangle(
                (
                    left + offset,
                    top + offset,
                    left + size,
                    top + size,
                ),
                outline="black",
                width=width,
            )


def _tile_pages(image: Image.Image, spec: PrintMapSpec) -> list[Image.Image]:
    page_width, page_height = A4_LANDSCAPE_PX
    usable_width = page_width - 2 * PAGE_MARGIN_PX
    usable_height = page_height - 2 * PAGE_MARGIN_PX
    step_x = usable_width - TILE_OVERLAP_PX
    step_y = usable_height - TILE_OVERLAP_PX
    columns = math.ceil((image.width - TILE_OVERLAP_PX) / step_x)
    rows = math.ceil((image.height - TILE_OVERLAP_PX) / step_y)
    pages: list[Image.Image] = []
    label_font = _font(23)

    for row in range(rows):
        for column in range(columns):
            left = min(column * step_x, image.width - usable_width)
            top = min(row * step_y, image.height - usable_height)
            crop = image.crop(
                (
                    left,
                    top,
                    min(left + usable_width, image.width),
                    min(top + usable_height, image.height),
                )
            )
            page = Image.new("RGB", (page_width, page_height), "white")
            page.paste(crop, (PAGE_MARGIN_PX, PAGE_MARGIN_PX))
            draw = ImageDraw.Draw(page)
            draw.rectangle(
                (
                    PAGE_MARGIN_PX,
                    PAGE_MARGIN_PX,
                    PAGE_MARGIN_PX + crop.width,
                    PAGE_MARGIN_PX + crop.height,
                ),
                outline="black",
                width=2,
            )
            draw.text(
                (PAGE_MARGIN_PX, page_height - PAGE_MARGIN_PX + 8),
                (
                    f"{spec.title} | część {row + 1}.{column + 1}/{rows}.{columns} "
                    "| druk 100% | zakładka 3 mm"
                ),
                fill="black",
                font=label_font,
            )
            pages.append(page)
    return pages


def _save_pdf(path: Path, pages: list[Image.Image]) -> None:
    pages[0].save(
        path,
        "PDF",
        resolution=DPI,
        save_all=True,
        append_images=pages[1:],
    )


def main() -> None:
    PNG_ROOT.mkdir(parents=True, exist_ok=True)
    A4_ROOT.mkdir(parents=True, exist_ok=True)
    FULL_SIZE_ROOT.mkdir(parents=True, exist_ok=True)

    for spec in MAPS:
        image = _prepare_map(spec)
        image.save(PNG_ROOT / f"{spec.id}.png", dpi=(DPI, DPI))
        _save_pdf(FULL_SIZE_ROOT / f"{spec.id}.pdf", [image])
        pages = _tile_pages(image, spec)
        _save_pdf(A4_ROOT / f"{spec.id}.pdf", pages)
        for page in pages:
            page.close()
        image.close()


if __name__ == "__main__":
    main()

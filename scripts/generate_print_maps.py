from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP_ROOT = ROOT / "assets" / "print_maps" / "village_watchtower"

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
    source_path: Path


MAPS = (
    PrintMapSpec(
        "village_overview",
        "Wioska",
        DEFAULT_MAP_ROOT / "source" / "village_overview.png",
    ),
    PrintMapSpec(
        "watchtower_overview",
        "Strażnica",
        DEFAULT_MAP_ROOT / "source" / "watchtower_overview.png",
    ),
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
    source = Image.open(spec.source_path).convert("L")
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


def generate_print_maps(
    specs: tuple[PrintMapSpec, ...],
    output_root: str | Path,
) -> tuple[Path, ...]:
    map_root = Path(output_root)
    png_root = map_root / "png"
    a4_root = map_root / "pdf" / "a4"
    full_size_root = map_root / "pdf" / "full_size"
    png_root.mkdir(parents=True, exist_ok=True)
    a4_root.mkdir(parents=True, exist_ok=True)
    full_size_root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for spec in specs:
        image = _prepare_map(spec)
        png_path = png_root / f"{spec.id}.png"
        full_size_path = full_size_root / f"{spec.id}.pdf"
        a4_path = a4_root / f"{spec.id}.pdf"
        image.save(png_path, dpi=(DPI, DPI))
        _save_pdf(full_size_path, [image])
        pages = _tile_pages(image, spec)
        _save_pdf(a4_path, pages)
        for page in pages:
            page.close()
        image.close()
        written.extend((png_path, a4_path, full_size_path))
    return tuple(written)


def load_manifest(path: str | Path) -> tuple[tuple[PrintMapSpec, ...], Path]:
    manifest_path = Path(path).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("schema") != "dnd_board_game.print_map_manifest":
        raise ValueError("Nieobsługiwany schemat manifestu map.")
    if int(data.get("schema_version", 0)) != 1:
        raise ValueError("Nieobsługiwana wersja manifestu map.")
    output_value = Path(str(data["output_root"]))
    output_root = output_value if output_value.is_absolute() else ROOT / output_value
    specs = tuple(
        PrintMapSpec(
            id=str(entry["id"]),
            title=str(entry["title"]),
            source_path=(
                Path(str(entry["source"]))
                if Path(str(entry["source"])).is_absolute()
                else manifest_path.parent / str(entry["source"])
            ),
        )
        for entry in data.get("maps", [])
    )
    return specs, output_root


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Przygotuj czarno-białe mapy 50 × 75 cm oraz PDF-y A4."
    )
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    specs, output_root = (
        load_manifest(args.manifest)
        if args.manifest
        else (MAPS, DEFAULT_MAP_ROOT)
    )
    if not specs:
        parser.error("Manifest nie zawiera żadnej mapy.")
    for path in generate_print_maps(specs, output_root):
        print(path)


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets/ui_v2/ashen_oath/print_maps"
SCENARIOS_DIR = ROOT / "scenarios"
DPI = 300
CELL_CM = 2.5
CELL_PX = round(DPI * CELL_CM / 2.54)
BOARD_COLS = 20
BOARD_ROWS = 30
BOARD_BOUNDS = (0, 0, BOARD_COLS - 1, BOARD_ROWS - 1)
A4_LANDSCAPE_PX = (round(DPI * 29.7 / 2.54), round(DPI * 21.0 / 2.54))
MARGIN_PX = round(DPI * 0.5 / 2.54)
OVERLAP_PX = round(DPI * 0.3 / 2.54)
ORIENTATION_MARKERS = (
    ("blue", (0, 0), (0, 90, 255, 235), "top_left"),
    ("yellow", (BOARD_COLS - 1, 0), (255, 210, 0, 235), "top_right"),
    ("red", (0, BOARD_ROWS - 1), (255, 30, 30, 235), "bottom_left"),
)


@dataclass(frozen=True)
class MapSpec:
    map_id: str
    scenario_file: str
    background_file: str
    title: str


MAPS = (
    MapSpec("brindleford_square", "ashen_oath_brindleford_square.json", "brindleford_square_bg.png", "Brindleford Square"),
    MapSpec("burned_chapel", "ashen_oath_burned_chapel.json", "burned_chapel_bg.png", "Burned Chapel"),
    MapSpec("old_mill", "ashen_oath_old_mill.json", "old_mill_bg.png", "Old Mill"),
    MapSpec("hill_ruins", "ashen_oath_hill_ruins.json", "hill_ruins_bg.png", "Hill Ruins"),
    MapSpec("oath_crypt", "ashen_oath_oath_crypt.json", "oath_crypt_bg.png", "Oath Crypt"),
)


def _font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _scenario_bounds(payload: dict) -> tuple[int, int, int, int]:
    coords: list[tuple[int, int]] = []
    for room in payload.get("rooms", []) or []:
        coords.extend(tuple(map(int, pos)) for pos in room.get("positions", []) or [])
    for obj in payload.get("objects", []) or []:
        coords.extend(tuple(map(int, pos)) for pos in obj.get("positions", []) or [] if isinstance(pos, list) and len(pos) == 2)
        for inst in obj.get("instances", []) or []:
            pos = inst.get("position")
            if isinstance(pos, list) and len(pos) == 2:
                coords.append(tuple(map(int, pos)))
    if not coords:
        raise ValueError("Scenario has no coordinates")
    xs = [pos[0] for pos in coords]
    ys = [pos[1] for pos in coords]
    return min(xs), min(ys), max(xs), max(ys)


def _load_background(path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    image = ImageEnhance.Color(image).enhance(0.92)
    image = ImageEnhance.Contrast(image).enhance(1.04)
    return image


def _cell_rect(pos: tuple[int, int], bounds: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    min_x, min_y, _max_x, _max_y = bounds
    x = (int(pos[0]) - min_x) * CELL_PX
    y = (int(pos[1]) - min_y) * CELL_PX
    return x, y, x + CELL_PX, y + CELL_PX


def _overlay_scenario_markers(image: Image.Image, payload: dict, bounds: tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    for obj in payload.get("objects", []) or []:
        category = str(obj.get("category") or "")
        object_id = str(obj.get("object_id") or "")
        if category in {"Enemies", "NPC"}:
            continue
        if object_id == "hidden_cache":
            continue
        positions = list(obj.get("positions") or [])
        if object_id == "simple_obstacle":
            fill = (55, 40, 30, 95)
            outline = (33, 24, 18, 145)
        elif object_id == "rumble_field":
            fill = (120, 110, 95, 80)
            outline = (70, 64, 55, 120)
        elif object_id == "trap_tile":
            fill = (120, 72, 20, 45)
            outline = (120, 72, 20, 105)
            positions.extend(inst.get("position") for inst in obj.get("instances", []) or [])
        else:
            continue
        for pos in positions:
            if not isinstance(pos, list) or len(pos) != 2:
                continue
            rect = _cell_rect(tuple(pos), bounds)
            draw.rectangle(rect, fill=fill, outline=outline, width=max(2, CELL_PX // 70))


def _draw_grid(image: Image.Image, cells_w: int, cells_h: int) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    major = (42, 36, 30, 165)
    minor = (42, 36, 30, 118)
    for x in range(cells_w + 1):
        px = x * CELL_PX
        draw.line((px, 0, px, cells_h * CELL_PX), fill=major if x in {0, cells_w} else minor, width=4 if x in {0, cells_w} else 2)
    for y in range(cells_h + 1):
        py = y * CELL_PX
        draw.line((0, py, cells_w * CELL_PX, py), fill=major if y in {0, cells_h} else minor, width=4 if y in {0, cells_h} else 2)


def _draw_orientation_markers(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    size = max(20, int(CELL_PX * 0.26))
    inset = max(12, int(CELL_PX * 0.10))
    outline = max(3, int(CELL_PX * 0.035))
    for _name, (col, row), fill, anchor in ORIENTATION_MARKERS:
        cell_left = col * CELL_PX
        cell_top = row * CELL_PX
        cell_right = cell_left + CELL_PX
        cell_bottom = cell_top + CELL_PX
        if anchor == "top_right":
            x1 = cell_right - inset - size
            y1 = cell_top + inset
        elif anchor == "bottom_left":
            x1 = cell_left + inset
            y1 = cell_bottom - inset - size
        else:
            x1 = cell_left + inset
            y1 = cell_top + inset
        x2 = x1 + size
        y2 = y1 + size
        draw.rectangle((x1, y1, x2, y2), fill=(255, 255, 255, 210), outline=(20, 20, 20, 230), width=outline + 2)
        draw.rectangle((x1 + outline, y1 + outline, x2 - outline, y2 - outline), fill=fill, outline=(255, 255, 255, 230), width=max(2, outline // 2))


def _render_map(spec: MapSpec, *, grid: bool) -> Image.Image:
    payload = json.loads((SCENARIOS_DIR / spec.scenario_file).read_text(encoding="utf-8"))
    _scenario_bounds(payload)
    bounds = BOARD_BOUNDS
    cells_w = BOARD_COLS
    cells_h = BOARD_ROWS
    image = _load_background(OUT_DIR / "images" / spec.background_file, (cells_w * CELL_PX, cells_h * CELL_PX))
    _overlay_scenario_markers(image, payload, bounds)
    if grid:
        _draw_grid(image, cells_w, cells_h)
    _draw_orientation_markers(image)
    return image


def _tile_pages(image: Image.Image, title: str, *, grid: bool) -> list[Image.Image]:
    page_w, page_h = A4_LANDSCAPE_PX
    usable_w = page_w - 2 * MARGIN_PX
    usable_h = page_h - 2 * MARGIN_PX
    step_x = usable_w - OVERLAP_PX
    step_y = usable_h - OVERLAP_PX
    cols = max(1, math.ceil(max(0, image.width - OVERLAP_PX) / step_x))
    rows = max(1, math.ceil(max(0, image.height - OVERLAP_PX) / step_y))
    pages: list[Image.Image] = []
    label_font = _font(34)
    note_font = _font(24)
    for row in range(rows):
        for col in range(cols):
            left = min(col * step_x, max(0, image.width - usable_w))
            top = min(row * step_y, max(0, image.height - usable_h))
            crop = image.crop((left, top, min(left + usable_w, image.width), min(top + usable_h, image.height)))
            page = Image.new("RGB", (page_w, page_h), (246, 242, 232))
            page.paste(crop, (MARGIN_PX, MARGIN_PX))
            draw = ImageDraw.Draw(page, "RGBA")
            label = f"{title} - {'grid' if grid else 'no grid'} - tile {row + 1}.{col + 1}/{rows}.{cols}"
            draw.text((MARGIN_PX, page_h - MARGIN_PX + 10), label, fill=(60, 52, 45, 220), font=note_font)
            draw.text((page_w - MARGIN_PX - 560, 18), "Print at 100%. 1 field = 2.5 cm.", fill=(60, 52, 45, 210), font=label_font)
            if cols > 1 or rows > 1:
                draw.rectangle((MARGIN_PX, MARGIN_PX, MARGIN_PX + crop.width, MARGIN_PX + crop.height), outline=(95, 70, 45, 120), width=2)
            pages.append(page)
    return pages


def _save_pdf(path: Path, pages: list[Image.Image]) -> None:
    if not pages:
        raise ValueError("No pages to save")
    pages[0].save(path, "PDF", resolution=DPI, save_all=True, append_images=pages[1:])


def _save_full_size_pdf(path: Path, images: list[Image.Image]) -> None:
    if not images:
        raise ValueError("No images to save")
    images[0].save(path, "PDF", resolution=DPI, save_all=True, append_images=images[1:])


def main() -> None:
    (OUT_DIR / "png/grid").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "png/no_grid").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "pdf").mkdir(parents=True, exist_ok=True)
    grid_pages: list[Image.Image] = []
    no_grid_pages: list[Image.Image] = []
    grid_full_size: list[Image.Image] = []
    no_grid_full_size: list[Image.Image] = []
    for spec in MAPS:
        for grid, collection, subdir in ((True, grid_pages, "grid"), (False, no_grid_pages, "no_grid")):
            image = _render_map(spec, grid=grid)
            image.save(OUT_DIR / "png" / subdir / f"{spec.map_id}.png", dpi=(DPI, DPI))
            collection.extend(_tile_pages(image, spec.title, grid=grid))
            if grid:
                grid_full_size.append(image)
            else:
                no_grid_full_size.append(image)
    _save_pdf(OUT_DIR / "pdf/ashen_oath_print_maps_grid_a4_tiled.pdf", grid_pages)
    _save_pdf(OUT_DIR / "pdf/ashen_oath_print_maps_no_grid_a4_tiled.pdf", no_grid_pages)
    _save_full_size_pdf(OUT_DIR / "pdf/ashen_oath_print_maps_grid_full_20x30_fields.pdf", grid_full_size)
    _save_full_size_pdf(OUT_DIR / "pdf/ashen_oath_print_maps_no_grid_full_20x30_fields.pdf", no_grid_full_size)


if __name__ == "__main__":
    main()

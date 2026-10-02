"""Canonical print destinations and publication helpers, separate from game rules."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[3]
HANDOUTS_ROOT = ROOT / "handouts"
HANDOUT_BUILD_ROOT = ROOT / ".cache/handouts"


@dataclass(frozen=True, slots=True)
class HandoutSpec:
    filename: str
    title: str
    label_key: str = ""


HANDOUT_FILES = (
    HandoutSpec("characters.pdf", "Karty siedmiu postaci", "materials_heroes"),
    HandoutSpec("map_a4.pdf", "Plansza do złożenia — 12 arkuszy A4", "materials_map_a4"),
    HandoutSpec("map_full.pdf", "Pełna plansza — jedna strona dla drukarni", "materials_map_full"),
    HandoutSpec("mission_0/tiles.pdf", "Misja 0 — kafle i rozmieszczenie", "materials_tiles"),
    HandoutSpec("mission_0/items.pdf", "Misja 0 — przedmioty do wycięcia", "materials_items"),
    HandoutSpec("mission_0/order.pdf", "Misja 0 — rozkaz Nessy", "materials_order"),
    HandoutSpec("mission_0/receipts.pdf", "Misja 0 — pokwitowania Boruta", "materials_receipts"),
    HandoutSpec("reference/rules.pdf", "Ściąga graczy", "materials_rules"),
    HandoutSpec("reference/markers.pdf", "Znaczniki pomocnicze", "materials_tokens"),
)


def handout_path(filename: str, *, root: Path = HANDOUTS_ROOT) -> Path:
    """Downloads expose only canonical files, never arbitrary local paths."""
    if filename not in {item.filename for item in HANDOUT_FILES}:
        raise ValueError("Nieznany materiał do druku.")
    destination = root / filename
    if not destination.resolve().is_relative_to(root.resolve()):
        raise ValueError("Materiał do druku jest poza katalogiem handouts.")
    return destination


def handout_url(filename: str) -> str:
    handout_path(filename)
    return "/session-materials/" + filename


def pdf_pages(path: Path) -> int:
    info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True,
                          check=True, timeout=15).stdout
    count = re.search(r"Pages:\s+(\d+)", info)
    if count is None:
        raise RuntimeError(f"Brak liczby stron PDF: {path.name}")
    return int(count.group(1))


def compact_pdf(path: Path) -> None:
    """Optimize ink art at 300 dpi while retaining vector text and page geometry."""
    gs = shutil.which("gs")
    if not gs:
        return
    target = path.with_suffix(".compact.pdf")
    try:
        subprocess.run([gs, "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4", "-dAutoRotatePages=/None", "-dDetectDuplicateImages=true",
            "-dDownsampleColorImages=true", "-dColorImageResolution=300", "-dColorImageDownsampleType=/Bicubic",
            "-dDownsampleGrayImages=true", "-dGrayImageResolution=300", "-dGrayImageDownsampleType=/Bicubic",
            "-dDownsampleMonoImages=false", f"-sOutputFile={target}", str(path)],
            capture_output=True, check=True, timeout=60)
        if pdf_pages(target) != pdf_pages(path):
            raise RuntimeError("Optymalizacja zmieniła liczbę stron.")
        if target.stat().st_size < path.stat().st_size:
            target.replace(path)
    finally:
        target.unlink(missing_ok=True)


def publish_pdf(source: Path, destination: Path, *, expected_pages: int | None = None) -> Path:
    """Replace a published file only after the complete source PDF exists."""
    with source.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise ValueError(f"Nieprawidłowy PDF: {source.name}")
    if expected_pages is not None and pdf_pages(source) != expected_pages:
        raise ValueError(f"Nieprawidłowa liczba stron PDF: {source.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destination.parent, prefix=".publish-", suffix=".pdf", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copyfile(source, temporary)
        shutil.copymode(source, temporary)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination

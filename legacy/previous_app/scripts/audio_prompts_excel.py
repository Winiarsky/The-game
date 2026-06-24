from __future__ import annotations

import argparse
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPTS = (
    ROOT / "assets/ui_v2/ashen_oath/AUDIO_PROMPTS.md",
    ROOT / "assets/ui_v2/bandit_cave/AUDIO_PROMPTS.md",
)
DEFAULT_OUTPUT = ROOT / "assets/ui_v2/audio_prompts.xlsx"

HEADING_RE = re.compile(r"^(#{2,6})\s+(.+?)\s*$", re.MULTILINE)
TARGET_RE = re.compile(
    r"-\s+(?:Docelowy plik|Proponowany plik):\s+`([^`]+)`", re.IGNORECASE
)
TYPE_RE = re.compile(r"-\s+Typ:\s+(.+)", re.IGNORECASE)
SOURCE_RE = re.compile(r"-\s+Zrodlo(?: tekstu| grafiki)?|-\s+Zródło(?: tekstu| grafiki)?", re.IGNORECASE)
PERFORMANCE_RE = re.compile(r"-\s+Wykonanie:\s+(.+)", re.IGNORECASE)
FENCE_RE = re.compile(r"```(?:text)?\n(.*?)\n```", re.DOTALL)


@dataclass(frozen=True)
class AudioPrompt:
    scenario_id: str
    section: str
    target_path: str
    kind: str
    source_file: str
    source_ref: str
    performance: str
    text: str
    sfx_prompt: str
    status: str = "todo"
    notes: str = ""


def _scenario_id(path: Path) -> str:
    try:
        return path.parent.name
    except IndexError:
        return path.stem


def _clean_heading(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`"):
        value = value[1:-1]
    return re.sub(r"^\d+(?:\.\d+)?\s+", "", value).strip()


def _kind_from_path(target_path: str, explicit: str = "") -> str:
    explicit = explicit.strip()
    if explicit:
        return explicit
    parts = target_path.split("/")
    if "voiceover" in parts:
        return "voiceover"
    if "sfx" in parts:
        return "sfx"
    if "music" in parts:
        return "music"
    if "ambience" in parts:
        return "ambience"
    return "audio"


def _line_after_label(chunk: str, pattern: re.Pattern[str]) -> str:
    match = pattern.search(chunk)
    return match.group(1).strip() if match and match.groups() else ""


def _source_ref(chunk: str) -> str:
    for line in chunk.splitlines():
        if SOURCE_RE.match(line):
            return line.split(":", 1)[1].strip() if ":" in line else line.strip("- ")
    return ""


def _paragraph_text(chunk: str) -> str:
    lines: list[str] = []
    for line in chunk.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("- "):
            continue
        if stripped.startswith("<!--"):
            continue
        lines.append(stripped)
    return "\n".join(lines).strip()


def _classified_fences(chunk: str) -> tuple[str, str]:
    text_blocks: list[str] = []
    sfx_blocks: list[str] = []
    for match in FENCE_RE.finditer(chunk):
        before = chunk[: match.start()]
        label = before.rsplit("\n", 3)[-3:]
        label_text = "\n".join(label).lower()
        content = match.group(1).strip()
        if "sfx" in label_text and "tekst do tts" not in label_text:
            sfx_blocks.append(content)
        elif "prompt do elevenlabs" in label_text and "tekst do tts" not in label_text:
            text_blocks.append(content)
        elif "tekst do tts" in label_text:
            text_blocks.append(content)
        else:
            text_blocks.append(content)
    return "\n\n".join(text_blocks).strip(), "\n\n".join(sfx_blocks).strip()


def parse_audio_prompts(path: Path) -> list[AudioPrompt]:
    body = path.read_text(encoding="utf-8")
    scenario_id = _scenario_id(path)
    headings = list(HEADING_RE.finditer(body))
    rows: list[AudioPrompt] = []
    for index, heading in enumerate(headings):
        level = len(heading.group(1))
        if level not in {3, 4}:
            continue
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        chunk = body[start:end].strip()
        title = _clean_heading(heading.group(2))

        inline_target = re.fullmatch(r"`([^`]+)`", heading.group(2).strip())
        target = inline_target.group(1) if inline_target else _line_after_label(chunk, TARGET_RE)
        if not target or not target.startswith("audio/"):
            continue

        explicit_kind = _line_after_label(chunk, TYPE_RE)
        prompt_text, sfx_prompt = _classified_fences(chunk)
        if not prompt_text:
            prompt_text = _paragraph_text(chunk)

        rows.append(
            AudioPrompt(
                scenario_id=scenario_id,
                section=title,
                target_path=target,
                kind=_kind_from_path(target, explicit_kind),
                source_file=str(path.relative_to(ROOT)),
                source_ref=_source_ref(chunk),
                performance=_line_after_label(chunk, PERFORMANCE_RE),
                text=prompt_text,
                sfx_prompt=sfx_prompt,
            )
        )
    return rows


def _col_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _xml_text(value: str) -> ET.Element:
    node = ET.Element("t")
    if value != value.strip():
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    node.text = value
    return node


def write_xlsx(rows: Iterable[AudioPrompt], output: Path) -> None:
    headers = [
        "scenario_id",
        "section",
        "target_path",
        "kind",
        "source_file",
        "source_ref",
        "performance",
        "text",
        "sfx_prompt",
        "status",
        "notes",
    ]
    table = [headers] + [[str(getattr(row, header)) for header in headers] for row in rows]

    def sheet_xml() -> str:
        root = ET.Element(
            "worksheet",
            {
                "xmlns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
                "xmlns:r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
            },
        )
        sheet_data = ET.SubElement(root, "sheetData")
        for row_index, row in enumerate(table, 1):
            row_node = ET.SubElement(sheet_data, "row", {"r": str(row_index)})
            for col_index, value in enumerate(row, 1):
                cell_ref = f"{_col_name(col_index)}{row_index}"
                cell = ET.SubElement(row_node, "c", {"r": cell_ref, "t": "inlineStr"})
                inline = ET.SubElement(cell, "is")
                inline.append(_xml_text(value))
        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="audio_prompts" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml())
        archive.writestr(
            "docProps/core.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Audio prompts</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>""",
        )
        archive.writestr(
            "docProps/app.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex</Application>
</Properties>""",
        )


def read_xlsx(path: Path) -> list[dict[str, str]]:
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    rows: list[list[str]] = []
    for row_node in sheet.findall(".//main:sheetData/main:row", ns):
        values: list[str] = []
        for cell in row_node.findall("main:c", ns):
            text = "".join(node.text or "" for node in cell.findall(".//main:t", ns))
            values.append(text)
        rows.append(values)
    if not rows:
        return []
    headers = rows[0]
    return [dict(zip(headers, row)) for row in rows[1:]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export AUDIO_PROMPTS.md files to an Excel workbook.")
    parser.add_argument("inputs", nargs="*", type=Path, default=list(DEFAULT_PROMPTS))
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    rows: list[AudioPrompt] = []
    for raw_path in args.inputs:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        rows.extend(parse_audio_prompts(path))
    output = args.output if args.output.is_absolute() else ROOT / args.output
    write_xlsx(rows, output)
    print(f"Wrote {len(rows)} rows to {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

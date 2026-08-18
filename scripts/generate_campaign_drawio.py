"""Generate an editable multi-page draw.io document from Mermaid blocks.

The converter intentionally supports only the small Mermaid subset used by the
campaign design document: nodes, subgraphs, class assignments and directed
edges.  Every generated vertex remains an individually movable/editable draw.io
cell; subgraphs become collapsible swimlanes.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from html import unescape
from pathlib import Path
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    ROOT / "content/scenarios/campaign/ostatni_transport_graf.md"
)
DEFAULT_OUTPUT = (
    ROOT / "content/scenarios/campaign/ostatni_transport_graf.drawio"
)

_NODE_RE = re.compile(
    r"^([A-Za-z][A-Za-z0-9_]*)\s*"
    r"(\[\[.*\]\]|\[\(.*\)\]|\(\[.*\]\)|\{\{.*\}\}|\{.*\}|\[.*\])$"
)
_SUBGRAPH_RE = re.compile(
    r'^subgraph\s+([A-Za-z][A-Za-z0-9_]*)\["(.*)"\]$'
)
_CLASS_RE = re.compile(r"^class\s+([^ ]+)\s+([A-Za-z_][A-Za-z0-9_]*);$")
_EDGE_START_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)\s+")
_EDGE_STEP_RE = re.compile(
    r"\s*(-->|-\.->|==>)(?:\|([^|]+)\|)?\s*"
    r"([A-Za-z][A-Za-z0-9_]*)"
)


@dataclass(frozen=True, slots=True)
class DiagramNode:
    id: str
    label: str
    group_id: str
    class_name: str = "interaction"


@dataclass(frozen=True, slots=True)
class DiagramEdge:
    source: str
    target: str
    arrow: str
    label: str = ""


@dataclass(frozen=True, slots=True)
class DiagramGroup:
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class DiagramPage:
    name: str
    direction: str
    nodes: tuple[DiagramNode, ...]
    edges: tuple[DiagramEdge, ...]
    groups: tuple[DiagramGroup, ...]


@dataclass(frozen=True, slots=True)
class _MermaidBlock:
    h1: str
    h2: str
    source: str


_STYLE_BY_CLASS = {
    "map": (
        "rounded=0;whiteSpace=wrap;html=1;fillColor=#172554;"
        "fontColor=#ffffff;strokeColor=#60a5fa;strokeWidth=3;"
    ),
    "tile": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#d9f99d;"
        "fontColor=#1a2e05;strokeColor=#4d7c0f;strokeWidth=3;"
    ),
    "npc": (
        "ellipse;whiteSpace=wrap;html=1;fillColor=#dbeafe;"
        "fontColor=#172554;strokeColor=#2563eb;strokeWidth=2;"
    ),
    "instance": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#fef3c7;"
        "fontColor=#451a03;strokeColor=#d97706;strokeWidth=2;"
    ),
    "interaction": (
        "rounded=0;whiteSpace=wrap;html=1;fillColor=#ccfbf1;"
        "fontColor=#134e4a;strokeColor=#0f766e;strokeWidth=2;"
    ),
    "combat": (
        "shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;"
        "fillColor=#fee2e2;fontColor=#450a0a;strokeColor=#dc2626;"
        "strokeWidth=3;"
    ),
    "hero": (
        "shape=process;whiteSpace=wrap;html=1;fillColor=#f3e8ff;"
        "fontColor=#3b0764;strokeColor=#9333ea;strokeWidth=2;"
    ),
    "decision": (
        "rhombus;whiteSpace=wrap;html=1;fillColor=#ffedd5;"
        "fontColor=#431407;strokeColor=#ea580c;strokeWidth=2;"
    ),
    "transition": (
        "rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor=#dcfce7;"
        "fontColor=#052e16;strokeColor=#16a34a;strokeWidth=3;"
    ),
    "clue": (
        "shape=note;whiteSpace=wrap;html=1;fillColor=#ecfeff;"
        "fontColor=#164e63;strokeColor=#0891b2;strokeWidth=2;"
    ),
    "resource": (
        "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;"
        "backgroundOutline=1;fillColor=#f1f5f9;fontColor=#0f172a;"
        "strokeColor=#475569;strokeWidth=2;"
    ),
    "exit": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#fee2e2;"
        "fontColor=#450a0a;strokeColor=#dc2626;strokeWidth=3;"
    ),
    "inactive": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#e5e7eb;"
        "fontColor=#4b5563;strokeColor=#9ca3af;strokeWidth=2;"
        "dashed=1;dashPattern=5 5;"
    ),
}


def _plain_heading(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip("#").strip())


def _extract_blocks(markdown: str) -> tuple[_MermaidBlock, ...]:
    blocks: list[_MermaidBlock] = []
    h1 = "Graf kampanii"
    h2 = ""
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("# "):
            h1 = _plain_heading(line[2:])
            h2 = ""
        elif line.startswith("## "):
            h2 = _plain_heading(line[3:])
        elif line.strip() == "```mermaid":
            content: list[str] = []
            index += 1
            while index < len(lines) and lines[index].strip() != "```":
                content.append(lines[index])
                index += 1
            blocks.append(_MermaidBlock(h1, h2, "\n".join(content)))
        index += 1
    return tuple(blocks)


def _page_name(block: _MermaidBlock, index: int) -> str:
    if block.h2 and block.h2 not in block.h1:
        name = f"{block.h1} · {block.h2}"
    else:
        name = block.h1 or f"Diagram {index}"
    return name[:120]


def _node_label(shape_source: str) -> str:
    quoted = re.search(r'"(.*)"', shape_source)
    if quoted:
        return unescape(quoted.group(1))
    return shape_source.strip("[](){} ")


def _parse_edge(line: str) -> tuple[DiagramEdge, ...]:
    start = _EDGE_START_RE.match(line)
    if start is None:
        return ()
    current = start.group(1)
    position = start.end(1)
    edges: list[DiagramEdge] = []
    while True:
        step = _EDGE_STEP_RE.match(line, position)
        if step is None:
            break
        arrow, label, target = step.groups()
        edges.append(DiagramEdge(current, target, arrow, label or ""))
        current = target
        position = step.end()
    return tuple(edges)


def parse_mermaid_page(block: _MermaidBlock, index: int) -> DiagramPage:
    direction = "LR"
    nodes_in_order: list[tuple[str, str, str]] = []
    groups: list[DiagramGroup] = []
    group_stack: list[str] = []
    class_by_node: dict[str, str] = {}
    edges: list[DiagramEdge] = []

    for raw_line in block.source.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("%%"):
            continue
        if line.startswith("flowchart "):
            direction = line.split(maxsplit=1)[1].strip()
            continue
        subgraph = _SUBGRAPH_RE.fullmatch(line)
        if subgraph is not None:
            group_id, label = subgraph.groups()
            groups.append(DiagramGroup(group_id, label))
            group_stack.append(group_id)
            continue
        if line == "end":
            if group_stack:
                group_stack.pop()
            continue
        class_match = _CLASS_RE.fullmatch(line)
        if class_match is not None:
            ids, class_name = class_match.groups()
            for node_id in ids.split(","):
                class_by_node[node_id] = class_name
            continue
        if line.startswith("classDef ") or line.startswith("style "):
            continue
        node_match = _NODE_RE.fullmatch(line)
        if node_match is not None:
            node_id, shape_source = node_match.groups()
            group_id = group_stack[-1] if group_stack else "__root__"
            nodes_in_order.append((node_id, _node_label(shape_source), group_id))
            continue
        if any(arrow in line for arrow in ("-->", "-.->", "==>")):
            edges.extend(_parse_edge(line))

    if any(group_id == "__root__" for _, _, group_id in nodes_in_order):
        groups.insert(0, DiagramGroup("__root__", "GŁÓWNY PRZEPŁYW"))

    nodes = tuple(
        DiagramNode(
            node_id,
            label,
            group_id,
            class_by_node.get(node_id, "interaction"),
        )
        for node_id, label, group_id in nodes_in_order
    )
    known_ids = {node.id for node in nodes}
    filtered_edges = tuple(
        edge
        for edge in edges
        if edge.source in known_ids and edge.target in known_ids
    )
    return DiagramPage(
        _page_name(block, index),
        direction,
        nodes,
        filtered_edges,
        tuple(groups),
    )


def parse_campaign_markdown(source: str) -> tuple[DiagramPage, ...]:
    return tuple(
        parse_mermaid_page(block, index)
        for index, block in enumerate(_extract_blocks(source), start=1)
    )


def _add_geometry(
    cell: ET.Element,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    relative: bool = False,
) -> None:
    attributes = {
        "x": str(round(x, 2)),
        "y": str(round(y, 2)),
        "width": str(round(width, 2)),
        "height": str(round(height, 2)),
        "as": "geometry",
    }
    if relative:
        attributes["relative"] = "1"
    ET.SubElement(cell, "mxGeometry", attributes)


def _group_layout(
    nodes: tuple[DiagramNode, ...],
) -> tuple[int, int, float, float]:
    columns = 4 if len(nodes) >= 13 else 3 if len(nodes) >= 7 else 2
    rows = max(1, (len(nodes) + columns - 1) // columns)
    width = 30 + columns * 285
    height = 70 + rows * 105
    return columns, rows, float(width), float(height)


def _drawio_page(page: DiagramPage, page_index: int) -> ET.Element:
    diagram = ET.Element(
        "diagram",
        {"id": f"campaign-page-{page_index}", "name": page.name},
    )
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        {
            "dx": "1800",
            "dy": "1000",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "1",
            "pageScale": "1",
            "pageWidth": "2600",
            "pageHeight": "3600",
            "math": "0",
            "shadow": "0",
        },
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    nodes_by_group: dict[str, list[DiagramNode]] = defaultdict(list)
    for node in page.nodes:
        nodes_by_group[node.group_id].append(node)

    group_cells: dict[str, str] = {}
    node_cells: dict[str, str] = {}
    row_y = 30.0
    group_index = 0
    group_items = [
        group for group in page.groups if nodes_by_group.get(group.id)
    ]
    group_layouts = {
        group.id: _group_layout(tuple(nodes_by_group[group.id]))
        for group in group_items
    }

    for pair_start in range(0, len(group_items), 2):
        pair = group_items[pair_start : pair_start + 2]
        pair_height = max(group_layouts[group.id][3] for group in pair)
        for column, group in enumerate(pair):
            _, _, width, height = group_layouts[group.id]
            group_cell_id = f"p{page_index}_g{group_index}"
            group_index += 1
            group_cells[group.id] = group_cell_id
            group_cell = ET.SubElement(
                root,
                "mxCell",
                {
                    "id": group_cell_id,
                    "value": group.label,
                    "style": (
                        "swimlane;html=1;rounded=1;startSize=34;horizontal=1;"
                        "fillColor=#f8fafc;swimlaneFillColor=#ffffff;"
                        "strokeColor=#64748b;fontColor=#0f172a;"
                        "fontStyle=1;collapsible=1;"
                    ),
                    "vertex": "1",
                    "parent": "1",
                },
            )
            group_x = 30.0 + column * 1300.0
            _add_geometry(
                group_cell,
                x=group_x,
                y=row_y,
                width=width,
                height=height,
            )
            columns, _, _, _ = group_layouts[group.id]
            for node_index, node in enumerate(nodes_by_group[group.id]):
                node_cell_id = f"p{page_index}_n_{node.id}"
                node_cells[node.id] = node_cell_id
                node_cell = ET.SubElement(
                    root,
                    "mxCell",
                    {
                        "id": node_cell_id,
                        "value": node.label,
                        "style": _STYLE_BY_CLASS.get(
                            node.class_name,
                            _STYLE_BY_CLASS["interaction"],
                        ),
                        "vertex": "1",
                        "parent": group_cell_id,
                    },
                )
                node_column = node_index % columns
                node_row = node_index // columns
                _add_geometry(
                    node_cell,
                    x=20.0 + node_column * 285.0,
                    y=50.0 + node_row * 105.0,
                    width=250.0,
                    height=70.0,
                )
        row_y += pair_height + 50.0

    for edge_index, edge in enumerate(page.edges):
        source = node_cells.get(edge.source)
        target = node_cells.get(edge.target)
        if source is None or target is None:
            continue
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
            "jettySize=auto;html=1;endArrow=block;endFill=1;"
            "strokeColor=#64748b;strokeWidth=2;"
        )
        if edge.arrow == "-.->":
            style += "dashed=1;dashPattern=8 8;"
        elif edge.arrow == "==>":
            style += "strokeColor=#16a34a;strokeWidth=4;"
        edge_cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": f"p{page_index}_e{edge_index}",
                "value": edge.label,
                "style": style,
                "edge": "1",
                "parent": "1",
                "source": source,
                "target": target,
            },
        )
        _add_geometry(
            edge_cell,
            x=0,
            y=0,
            width=0,
            height=0,
            relative=True,
        )
    return diagram


def build_drawio_document(pages: tuple[DiagramPage, ...]) -> ET.Element:
    mxfile = ET.Element(
        "mxfile",
        {
            "host": "app.diagrams.net",
            "modified": "2026-08-06T00:00:00.000Z",
            "agent": "Codex campaign Mermaid converter",
            "version": "26.0.16",
            "type": "device",
            "compressed": "false",
            "pages": str(len(pages)),
        },
    )
    for index, page in enumerate(pages, start=1):
        mxfile.append(_drawio_page(page, index))
    return mxfile


def generate_drawio(source_path: Path, output_path: Path) -> tuple[int, int, int]:
    pages = parse_campaign_markdown(source_path.read_text(encoding="utf-8"))
    document = build_drawio_document(pages)
    ET.indent(document, space="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(document).write(
        output_path,
        encoding="utf-8",
        xml_declaration=True,
    )
    node_count = sum(len(page.nodes) for page in pages)
    edge_count = sum(len(page.edges) for page in pages)
    return len(pages), node_count, edge_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate editable draw.io pages from the campaign Mermaid file."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    pages, nodes, edges = generate_drawio(args.source, args.output)
    print(
        f"generated {args.output}: pages={pages} nodes={nodes} edges={edges}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

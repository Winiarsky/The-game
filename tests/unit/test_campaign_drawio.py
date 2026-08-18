from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from scripts.generate_campaign_drawio import generate_drawio


SOURCE = Path("content/scenarios/campaign/ostatni_transport_graf.md")


def test_campaign_mermaid_generates_editable_multi_page_drawio(tmp_path) -> None:
    output = tmp_path / "campaign.drawio"

    page_count, node_count, edge_count = generate_drawio(SOURCE, output)

    assert page_count == 14
    assert node_count >= 420
    assert edge_count >= 340
    root = ET.parse(output).getroot()
    assert root.tag == "mxfile"
    assert root.attrib["compressed"] == "false"
    diagrams = root.findall("diagram")
    assert len(diagrams) == page_count

    vertices = root.findall(".//mxCell[@vertex='1']")
    edges = root.findall(".//mxCell[@edge='1']")
    assert len(vertices) >= node_count
    assert len(edges) == edge_count
    assert all(vertex.find("mxGeometry") is not None for vertex in vertices)
    assert all(edge.get("source") and edge.get("target") for edge in edges)


def test_campaign_drawio_contains_player_tile_and_map_pages(tmp_path) -> None:
    output = tmp_path / "campaign.drawio"
    generate_drawio(SOURCE, output)
    root = ET.parse(output).getroot()

    page_names = [diagram.attrib["name"] for diagram in root.findall("diagram")]
    assert any("Graf całej przygody" in name for name in page_names)
    assert any(
        "Mapa 0" in name and "Główny przepływ" in name
        for name in page_names
    )
    assert any(
        "Mapa 0" in name and "kafelki gracza" in name.lower()
        for name in page_names
    )
    assert any(
        "Mapa 1" in name and "kafelki gracza" in name.lower()
        for name in page_names
    )
    assert any(
        "Mapa 2" in name and "kafelki gracza" in name.lower()
        for name in page_names
    )
    assert any(
        "Mapa 3" in name and "kafelki gracza" in name.lower()
        for name in page_names
    )

    tile_cells = [
        cell
        for cell in root.findall(".//mxCell[@vertex='1']")
        if "fillColor=#d9f99d" in cell.attrib.get("style", "")
    ]
    assert len(tile_cells) >= 100
    assert any("Co wiadomo o zaginięciu?" in cell.attrib.get("value", "") for cell in tile_cells)
    assert any("Zakończ odprawę" in cell.attrib.get("value", "") for cell in tile_cells)
    assert not any("Przyjmij zlecenie" in cell.attrib.get("value", "") for cell in tile_cells)
    assert any("Poznaj wersję Marka" in cell.attrib.get("value", "") for cell in tile_cells)
    assert any("Zamknij pęknięcie" in cell.attrib.get("value", "") for cell in tile_cells)

    assert any(
        "Erynd: Przejrzyj papiery przewozowe"
        in cell.attrib.get("value", "")
        for cell in root.findall(".//mxCell[@vertex='1']")
    )

    inactive_cells = [
        cell
        for cell in root.findall(".//mxCell[@vertex='1']")
        if "fillColor=#e5e7eb" in cell.attrib.get("style", "")
    ]
    assert len(inactive_cells) >= 8
    assert any("Archiwum" in cell.attrib.get("value", "") for cell in inactive_cells)

"""Mission-local editable sources and separate player-ready print packages."""
from __future__ import annotations

from copy import deepcopy
import importlib
import json
from pathlib import Path

import pytest

from dnd_board_game.scenarios import character_text

ROOT = Path(__file__).resolve().parents[2]
MISSION = ROOT / 'content/scenarios/misja_0_dzwon'


def split_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    data = deepcopy(character_text.load_text())
    aid = {'version': 1, 'pages': data.pop('player_aid')}
    data['player_aid_file'] = 'sciaga_graczy.json'
    source = tmp_path / 'karty_postaci.json'
    source.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    aid_path = tmp_path / data['player_aid_file']
    aid_path.write_text(json.dumps(aid, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(character_text, 'SOURCE_PATH', source)
    return source, aid_path


def test_canonical_sources_are_in_mission_without_duplicate_rules() -> None:
    assert character_text.SOURCE_PATH == MISSION / 'text/karty_postaci.json'
    source = json.loads(character_text.SOURCE_PATH.read_text())
    assert 'player_aid' not in source
    assert source['player_aid_file'] == 'sciaga_graczy.json'
    assert not (ROOT / 'content/characters/karty_postaci.json').exists()
    assert len(character_text.load_text()['player_aid']) == 4


def test_editing_only_rules_reloads_aid_without_touching_character_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, aid_path = split_source(tmp_path, monkeypatch)
    original = source.read_bytes()
    character_text.load_text()  # Cache both files before editing only the aid.
    aid = json.loads(aid_path.read_text())
    aid['pages'][0]['lead'] = 'Moje zasady dla graczy po zapisaniu pliku.'
    aid_path.write_text(json.dumps(aid, ensure_ascii=False), encoding='utf-8')
    assert character_text.load_text()['player_aid'][0]['lead'] == aid['pages'][0]['lead']
    assert source.read_bytes() == original
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    mats = importlib.import_module('build_hero_mats')
    assert aid['pages'][0]['lead'] in mats.player_aid_page(character_text.load_text()['player_aid'][0])


@pytest.mark.parametrize('reference', ['../outside.json', '/tmp/outside.json'])
def test_aid_reference_is_a_sibling_file(
    reference: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, _ = split_source(tmp_path, monkeypatch)
    data = json.loads(source.read_text())
    data['player_aid_file'] = reference
    source.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='obok karty_postaci'):
        character_text.load_text()


def test_invalid_aid_fails_before_rendering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, aid_path = split_source(tmp_path, monkeypatch)
    aid_path.write_text('{"version": 1, "pages": []}', encoding='utf-8')
    with pytest.raises(ValueError, match='niepustej listy'):
        character_text.load_text()


def test_current_generator_publishes_35_character_pages_and_separate_reference_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    generator = importlib.import_module('build_rune_relations')
    work = tmp_path / 'work'
    public = tmp_path / 'handouts'
    page_counts: dict[Path, int] = {}
    merged: dict[Path, tuple[Path, ...]] = {}
    published: dict[Path, tuple[Path, int | None]] = {}
    written: list[Path] = []
    original_mkdir = Path.mkdir
    original_text = Path.write_text
    original_bytes = Path.write_bytes

    def writable(path: Path) -> None:
        assert path.resolve().is_relative_to(tmp_path.resolve()), f'Generator wrote outside tmp: {path}'
        written.append(path)

    def mkdir(path: Path, *args: object, **kwargs: object) -> None:
        writable(path)
        original_mkdir(path, *args, **kwargs)

    def write_text(path: Path, text: str, *args: object, **kwargs: object) -> int:
        writable(path)
        return original_text(path, text, *args, **kwargs)

    def write_bytes(path: Path, data: bytes) -> int:
        writable(path)
        return original_bytes(path, data)

    monkeypatch.setattr(Path, 'mkdir', mkdir)
    monkeypatch.setattr(Path, 'write_text', write_text)
    monkeypatch.setattr(Path, 'write_bytes', write_bytes)

    def render(html: Path, pdf: Path) -> None:
        pages = html.read_text(encoding='utf-8').count('<article class="page')
        assert pages > 0
        page_counts[pdf] = pages
        pdf.write_bytes(b'%PDF-1.4\nrendered placeholder\n%%EOF\n')

    def merge(parts: list[Path], destination: Path) -> None:
        assert parts and all(path.is_file() for path in parts)
        merged[destination] = tuple(parts)
        page_counts[destination] = sum(page_counts[path] for path in parts)
        destination.write_bytes(b'%PDF-1.4\nmerged placeholder\n%%EOF\n')

    def validate(path: Path, *, script: str) -> list[object]:
        assert path.read_text(encoding='utf-8').count('<article class="page') == 5
        return []

    def reference_sheet(folder: Path, name: str, html: str, *, html_only: bool) -> tuple[Path, list[object]]:
        assert not html_only
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'{name}.html'
        path.write_text(html, encoding='utf-8')
        pdf = path.with_suffix('.pdf')
        render(path, pdf)
        assert page_counts[pdf] == 1
        return pdf, []

    def compact(path: Path) -> None:
        assert path.is_file() and page_counts[path] > 0

    def publish(source: Path, destination: Path, *, expected_pages: int | None = None) -> Path:
        assert source.is_file() and page_counts[source] == expected_pages
        published[destination.relative_to(public)] = (source, expected_pages)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        return destination

    def external_process(*args: object, **kwargs: object) -> None:
        raise AssertionError('The pipeline test must not launch Chrome or PDF tools')

    monkeypatch.setattr(generator, 'render_pdf', render)
    monkeypatch.setattr(generator, 'merge_pdfs', merge)
    monkeypatch.setattr(generator, 'pdf_pages', lambda path: page_counts[path])
    monkeypatch.setattr(generator, 'compact_pdf', compact)
    monkeypatch.setattr(generator.baskets, 'validate', validate)
    monkeypatch.setattr(generator, '_reference_sheet', reference_sheet)
    monkeypatch.setattr(generator, 'publish_pdf', publish)
    monkeypatch.setattr(generator.subprocess, 'run', external_process)

    manifest = generator.build(output=work, publish_root=public)
    assert manifest['profile'] == 'rune_relations_v03' and manifest['pages'] == 35
    assert manifest['action_mm'] == [60, 54] and manifest['equipment_mm'] == [60, 42]
    assert len(manifest['sections']) == 7
    assert [section['first_page'] for section in manifest['sections']] == [1, 6, 11, 16, 21, 26, 31]
    assert all(section['pages'] == 5 for section in manifest['sections'])
    assert len(merged[work / 'characters.pdf']) == 7
    assert len(merged[work / 'reference/rules.pdf']) == 3
    assert published == {
        Path('characters.pdf'): (work / 'characters.pdf', 35),
        Path('reference/rules.pdf'): (work / 'reference/rules.pdf', 3),
        Path('reference/markers.pdf'): (work / 'reference/markers.pdf', 1),
    }
    assert {path.relative_to(public) for path in public.rglob('*.pdf')} == set(published)
    reference = json.loads((work / 'reference/reference_manifest.json').read_text(encoding='utf-8'))
    assert reference['rules']['file'] == 'rules.pdf' and reference['rules']['pages'] == 3
    assert reference['markers']['file'] == 'markers.pdf' and reference['markers']['pages'] == 1
    assert written and all(path.resolve().is_relative_to(tmp_path.resolve()) for path in written)

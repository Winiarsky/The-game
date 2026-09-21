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


def test_generator_publishes_cards_aid_and_markers_as_separate_pdfs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    mats = importlib.import_module('build_hero_mats')
    monkeypatch.setattr(mats, 'OUTPUT', tmp_path / 'characters')
    published: dict[str, tuple[list[Path], list[dict], dict]] = {}

    def write_page(folder: Path, name: str, html: str, **kwargs: object) -> tuple[Path, list]:
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f'{name}.pdf', []

    def publish(destination: Path, parts: list[Path], sections: list[dict], **metadata: object) -> None:
        published[destination.name] = (parts, sections, metadata)

    monkeypatch.setattr(mats, 'write_page', write_page)
    monkeypatch.setattr(mats, 'publish_pdf', publish)
    assert mats.build_pack() == MISSION / 'print/karty_postaci_A4.pdf'
    assert set(published) == {'karty_postaci_A4.pdf', 'sciaga_graczy_A4.pdf', 'znaczniki_A4.pdf'}
    cards, sections, dimensions = published['karty_postaci_A4.pdf']
    assert len(cards) == 36 and len(sections) == 7
    assert all(path.parent.name != 'wspolne' for path in cards)
    assert sections[0]['first_page'] == 2 and sections[-1]['last_page'] == 36
    assert dimensions['mana_mm'] == [63, 88]
    assert dimensions['equipment_mm'] == [60, 42]
    assert dimensions['action_mm'] == [62, 76]
    assert dimensions['nimra_action_mm'] == [68, 53]
    assert len(published['sciaga_graczy_A4.pdf'][0]) == 4
    assert published['znaczniki_A4.pdf'][0][0].name == '05_znaczniki.pdf'

"""Editable character and tutorial copy; mechanical definitions stay in rules.

The cache follows file revisions, so saving the JSON is enough for the next UI
request or print build to see edits. Returned source data is read-only by contract.
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
import json
from pathlib import Path
from typing import Any, TYPE_CHECKING, TypeVar

from dnd_board_game.rules.shared_mana_catalog import SharedAbility
from dnd_board_game.rules.physical_mana import ManaAbility

if TYPE_CHECKING:
    from dnd_board_game.application.training_walkthrough import TrainingStep

AbilityText = TypeVar("AbilityText", SharedAbility, ManaAbility)

SOURCE_PATH = (Path(__file__).resolve().parents[3]
               / 'content/scenarios/misja_0_dzwon/text/karty_postaci.json')
HERO_IDS = frozenset(('garran', 'brakka', 'mira', 'dagna', 'lorian', 'nimra', 'erynd'))
COLORS = frozenset('CBZFN')


def revision(path: Path | None = None) -> tuple[str, int, int]:
    file = path if path is not None else SOURCE_PATH
    stat = file.stat()
    return str(file), stat.st_mtime_ns, stat.st_size


@lru_cache(maxsize=8)
def _read(stamp: tuple[str, int, int]) -> dict[str, Any]:
    data = json.loads(Path(stamp[0]).read_text(encoding='utf-8'))
    if data.get('version') != 1 or set(data.get('heroes', {})) != HERO_IDS:
        raise ValueError('karty_postaci.json: wymagana wersja 1 i siedmiu bohaterów.')
    for hid, hero in data['heroes'].items():
        for key in ('role', 'history', 'motivation', 'personal_goal', 'character_line'):
            if not isinstance(hero.get(key), str) or not hero[key].strip():
                raise ValueError(f'karty_postaci.json: brak tekstu {hid}.{key}.')
        for mode in ('combat', 'exploration'):
            if set(hero['passives'][mode]) != COLORS:
                raise ValueError(f'karty_postaci.json: {hid}.{mode} wymaga pięciu kolorów.')
            for color, passive in hero['passives'][mode].items():
                for key in ('name', 'when', 'effect', 'short', 'stacking'):
                    if not isinstance(passive.get(key), str) or not passive[key].strip():
                        raise ValueError(f'karty_postaci.json: brak {hid}.{mode}.{color}.{key}.')
        for aid, action in hero['actions'].items():
            if not all(isinstance(action.get(k), str) and action[k].strip() for k in ('name', 'description')):
                raise ValueError(f'karty_postaci.json: niepełny opis akcji {hid}.{aid}.')
    for key in ('equipment', 'keywords', 'tutorial'):
        if key not in data:
            raise ValueError(f'karty_postaci.json: brak sekcji {key}.')
    if 'player_aid' not in data and not isinstance(data.get('player_aid_file'), str):
        raise ValueError('karty_postaci.json: brak player_aid_file lub sekcji player_aid.')
    return data


@lru_cache(maxsize=8)
def _read_player_aid(stamp: tuple[str, int, int]) -> list[dict[str, Any]]:
    data = json.loads(Path(stamp[0]).read_text(encoding='utf-8'))
    pages = data.get('pages')
    if data.get('version') != 1 or not isinstance(pages, list) or not pages:
        raise ValueError('Ściąga graczy wymaga wersji 1 i niepustej listy pages.')
    ids: set[str] = set()
    for page in pages:
        if not isinstance(page, dict) or not all(
            isinstance(page.get(key), str) and page[key].strip()
            for key in ('id', 'title', 'subtitle', 'lead')
        ) or not isinstance(page.get('sections'), list) or not page['sections']:
            raise ValueError('Ściąga graczy: niepełna strona.')
        if page['id'] in ids:
            raise ValueError('Ściąga graczy: powtórzony identyfikator strony.')
        ids.add(page['id'])
    return pages


def load_text() -> dict[str, Any]:
    data = _read(revision())
    # Complete in-memory/legacy sources retain the previous public contract.
    if 'player_aid' in data:
        return data
    reference = Path(data['player_aid_file'])
    if reference.name != str(reference) or reference.is_absolute():
        raise ValueError('player_aid_file musi wskazywać plik obok karty_postaci.json.')
    pages = _read_player_aid(revision(SOURCE_PATH.parent / reference))
    return {**data, 'player_aid': pages}


def hero_text(hero_id: str) -> dict[str, Any]:
    return load_text()['heroes'][hero_id]


def action_text(hero_id: str, action_id: str) -> dict[str, Any]:
    return hero_text(hero_id)['actions'][action_id]


def passive_label(display: dict[str, str]) -> str:
    return f"{display['name']}: {display['when']}: {display['effect']} {display['stacking']}"


def present_ability(ability: AbilityText) -> AbilityText:
    """Overlay prose without changing IDs, cost, timing, or other mechanics."""
    if ability.category == 'tutorial':
        text = load_text()['tutorial']['foundations'][ability.id]
        return replace(ability, name=text['name'], description=text['instruction'])
    text = action_text(ability.hero_id, ability.id)
    return replace(ability, name=text['name'], description=text['description'],
                   boosts=tuple(replace(b, label=text['boosts'][b.id]) for b in ability.boosts))


def print_copy() -> dict[str, Any]:
    """Adapter for the print layout, not a second editable copy."""
    source = load_text()
    return dict(equipment=source['equipment'], heroes={hid: {
        'character_line': h['character_line'], 'flaw': h['flaw']['description'],
        'actions': {aid: a['description'] for aid, a in h['actions'].items()},
        'boosts': {aid: a['boost_summary'] for aid, a in h['actions'].items()},
    } for hid, h in source['heroes'].items()})


def tutorial_steps(hero_id: str) -> tuple[TrainingStep, ...]:
    from dnd_board_game.application.training_walkthrough import steps
    return tuple(replace(step, ability=present_ability(step.ability)) for step in steps(hero_id))


def feature_copy(hero_id: str, feature_id: str) -> tuple[str, str] | None:
    """Refresh prose in saved character records without rewriting their mechanics."""
    if hero_id not in HERO_IDS:
        return None
    from dnd_board_game.rules.physical_mana import FLAWS
    hero = hero_text(hero_id)
    if feature_id == FLAWS[hero_id][0]:
        return hero['flaw']['name'], hero['flaw']['description']
    if feature_id in hero['actions']:
        from .pooled_mana_catalog import requirement_text, ability_description
        action = hero['actions'][feature_id]
        if feature_id == 'spiritual_weapon_activation':
            return action['name'], action['description']
        return action['name'], requirement_text(feature_id, hero_id) + ' ' + ability_description(hero_id, feature_id)
    return None

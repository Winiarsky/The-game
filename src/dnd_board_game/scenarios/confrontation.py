"""Validated confrontation catalogue shared by UI, print and simulations."""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import json
from dnd_board_game.rules.exploration_mana_catalog import HEROES
from dnd_board_game.rules.confrontation import PASSIVE_KINDS
from dnd_board_game.rules.confrontation_passives import STACKING
from dnd_board_game.rules.pooled_mana import COLORS
from dnd_board_game.core.player_labels_pl import ABILITY_LABELS_PL
from .character_text import load_text, hero_text, passive_label, revision


def reminder() -> str:
    return load_text()['tutorial']['exploration_reminder']


def condition_help() -> tuple[tuple[str, str], ...]:
    return tuple(tuple(item) for item in load_text()['tutorial']['conditions'])


@dataclass(frozen=True, slots=True)
class Lesson:
    id: str
    name: str
    scene: str
    kind: str
    focus: str
    instruction: str


def validate_approaches(approaches: list[dict]) -> None:
    """Authored options need not cover all abilities or use unique abilities."""
    if not isinstance(approaches, list) or not 1 <= len(approaches) <= 12:
        raise ValueError('Scena wymaga od 1 do 12 podejść.')
    ids = set()
    for option in approaches:
        if (not isinstance(option, dict) or not isinstance(option.get('id'), str)
                or not option['id'] or option['id'] in ids
                or not isinstance(option.get('name'), str) or not option['name'].strip()
                or not isinstance(option.get('description'), str) or not option['description'].strip()
                or option.get('ability') not in ABILITY_LABELS_PL
                or type(option.get('repeatable', False)) is not bool
                or type(option.get('dc')) is not int or option['dc'] < 1
                or type(option.get('die')) is not int or option['die'] not in (4, 6, 8, 10, 12)):
            raise ValueError('Nieprawidłowe podejście sceny: id, nazwa, opis, cecha, ST i kość.')
        ids.add(option['id'])
    for option in approaches:
        links = option.get('supports')
        if (not isinstance(links, list) or any(not isinstance(x, str) for x in links)
                or len(set(links)) != len(links) or any(x not in ids and x != '*' for x in links)
                or ('*' in links and len(links) != 1)):
            raise ValueError('Powiązania pomocy muszą wskazywać podejścia tej sceny lub samo *.')

def catalog() -> dict:
    path = Path(__file__).resolve().parents[3] / 'content/balance/confrontation.json'
    return _catalog(revision(path), revision())


@lru_cache(maxsize=8)
def _catalog(balance_revision: tuple, text_revision: tuple) -> dict:
    data = json.loads(Path(balance_revision[0]).read_text())
    for hid, profile in data['passives'].items():
        for color, passive in profile.items():
            passive['display'] = dict(hero_text(hid)['passives']['exploration'][color])
            passive['label'] = passive_label(passive['display'])
    for lesson in data['lessons']:
        lesson.update(load_text()['tutorial']['exploration_lessons'][lesson['id']])
    if data['version'] != 2 or set(data['passives']) != set(HEROES):
        raise ValueError('Nieprawidłowy katalog konfrontacji.')
    for profile in data['passives'].values():
        if set(profile) != set(COLORS) or any(p['kind'] not in PASSIVE_KINDS or not p['label'] for p in profile.values()):
            raise ValueError('Nieprawidłowe pasywy konfrontacji.')
        if any(p.get('stackable') is not (p['kind'] in ({'test','impact'} | STACKING)) for p in profile.values()):
            raise ValueError('Obwódka kumulacji musi odpowiadać działaniu pasywu konfrontacji.')
    ids = {s['id'] for s in data['scenes']}
    if len(ids) != len(data['scenes']):
        raise ValueError('Powtórzona scena konfrontacji.')
    for scene in data['scenes']:
        if scene['kind'] not in {'npc', 'object'} or scene['resistance_per_hero'] < 1:
            raise ValueError('Nieprawidłowy rodzaj lub opór sceny.')
        validate_approaches(scene.get('approaches'))
        if scene['minimum_pressure'] < 1 or scene['pressure_per_hero'] < 1:
            raise ValueError('Scena wymaga presji na talię.')
        if not scene['reactions'] or any(r['kind'] not in {'burn', 'strip', 'heal'} for r in scene['reactions']):
            raise ValueError('Nieprawidłowa reakcja.')
    lessons = tuple(Lesson(**l) for l in data['lessons'])
    if len({l.id for l in lessons}) != len(lessons) or any(l.scene not in ids for l in lessons):
        raise ValueError('Nieprawidłowe lekcje konfrontacji.')
    return data


def scene_by_id(key: str) -> dict:
    for scene in catalog()['scenes']:
        if scene['id'] == key:
            return scene
    raise ValueError('Nieznana scena konfrontacji.')


def lessons_for(hero: str) -> tuple[Lesson, ...]:
    if hero not in HEROES:
        raise ValueError('Nieznany bohater.')
    return tuple(Lesson(**l) for l in catalog()['lessons'])


def lesson_by_id(hero: str, key: str) -> Lesson:
    for lesson in lessons_for(hero):
        if lesson.id == key:
            return lesson
    raise ValueError('Nieznane ćwiczenie konfrontacji.')


def passives(hero: str) -> dict[str, dict[str, str]]:
    return catalog()['passives'][hero]

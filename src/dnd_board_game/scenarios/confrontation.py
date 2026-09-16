"""Validated confrontation catalogue shared by UI, print and simulations."""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import json
from dnd_board_game.rules.exploration_mana_catalog import HEROES
from dnd_board_game.rules.confrontation import PASSIVE_KINDS
from dnd_board_game.rules.pooled_mana import COLORS

REMINDER = ('Konfrontacja drużynowa: każdy ma własną pulę i turę. Poniżej 21 pkt obowiązkowo wybierz jedną z dwóch odkrytych kart; druga zostaje. '
            'Przy 21+ nie dobierasz, bez kary za przekroczenie. Po doborze: własny test albo pomoc +2 do następnego testu sojusznika, bez kumulacji i bez spalania. '
            'Premia many +0/+2/+4/+6 wymaga 0/6/12/21 pkt i spala 1/1/2/3 karty. Możesz wybrać słabszą próbę. '
            'Test: k20 + cecha + naładowanie + pozostałe premie. Sukces: kość wpływu zależna od podatności + modyfikator cechy + premie wpływu. '
            'Pula pozostaje. Spalanie z wierzchu po efekcie, także przy niepowodzeniu. Po rundzie sytuacja reaguje. '
            'Opór 0 = sukces. Brak kart do wymaganej operacji kończy konfrontację; najpierw rozstrzygnij rozpoczęte działanie. Bez ostatniej darmowej kolejki. '
            'Na nową konfrontację zbierz cały komplet i przetasuj. Runy wybierają działania; rzuty przez fokus, −/+, podsumowanie i ✓.')
CONDITION_HELP = (
    ('Częściowe porozumienie', 'Po zbiciu połowy oporu możesz przyjąć jawny kompromis zamiast walczyć o pełny sukces.'),
    ('Drażliwy temat', 'Dobranie wskazanego koloru zmienia cenę i korzyść sukcesu całej drużyny.'),
    ('Dodatkowy cel', 'Dwie niebieskie karty w pulach drużyny przy sukcesie dają dodatkową informację.'),
    ('Przysługa za przysługę', 'Raz: odzyskaj najstarszą spaloną kartę na spód za zobowiązanie, które pozostaje także po porażce.'),
)

@dataclass(frozen=True, slots=True)
class Lesson:
    id: str
    name: str
    scene: str
    kind: str
    focus: str
    instruction: str

@lru_cache(maxsize=1)
def catalog() -> dict:
    data = json.loads((Path(__file__).resolve().parents[3] / 'content/balance/confrontation.json').read_text())
    if data['version'] != 1 or set(data['passives']) != set(HEROES):
        raise ValueError('Nieprawidłowy katalog konfrontacji.')
    for profile in data['passives'].values():
        if set(profile) != set(COLORS) or any(p['kind'] not in PASSIVE_KINDS or not p['label'] for p in profile.values()):
            raise ValueError('Nieprawidłowe pasywy konfrontacji.')
    ids = {s['id'] for s in data['scenes']}
    if len(ids) != len(data['scenes']):
        raise ValueError('Powtórzona scena konfrontacji.')
    for scene in data['scenes']:
        if scene['kind'] not in {'npc', 'object'} or set(scene['methods']) != set(HEROES) or scene['resistance_per_hero'] < 1:
            raise ValueError('Scena wymaga profilu wszystkich siedmiu metod.')
        for method in scene['methods'].values():
            if method['dc'] < 1 or method['die'] not in (4, 6, 8, 10, 12):
                raise ValueError('Nieprawidłowa podatność metody.')
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

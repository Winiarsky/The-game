"""Validated file-backed content for the shared exploration resolver and lessons."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

from dnd_board_game.rules.exploration_mana_conditions import ManaCondition
from dnd_board_game.rules.exploration_mana_catalog import COLORS, method_by_id, obstacle_description, profile_values


@dataclass(frozen=True, slots=True)
class ManaFollowup:
    id: str
    label: str
    message: str
    flag: str


@dataclass(frozen=True, slots=True)
class ManaVariant:
    kind: str
    message: str
    cost: str
    flags: tuple[str, ...]
    followups: tuple[ManaFollowup, ...] = ()


@dataclass(frozen=True, slots=True)
class ManaOption:
    method_id: str
    profile: str
    obstacle: str
    description: str
    cost: str
    success: str
    failure: str
    success_flag: str
    failure_flag: str
    variants: tuple[ManaVariant, ...] = ()


@dataclass(frozen=True, slots=True)
class ManaScene:
    id: str
    kind: str
    name: str
    description: str
    dc: int
    position: tuple[int, int]
    options: tuple[ManaOption, ...]
    condition: ManaCondition = ManaCondition()
    condition_title: str = ''
    condition_text: str = ''
    obligation: str = ''


@dataclass(frozen=True, slots=True)
class ManaLesson:
    id: str
    name: str
    kind: str
    narration: str
    objective: str
    hero_id: str = ""
    profile: str = ""
    obstacle: str = ""
    dc: int = 0
    offers: tuple[tuple[str, ...], ...] = ()
    choices: tuple[str, ...] = ()
    finish: str = ""
    practice: bool = False
    scene_id: str = ''
    open_after_preparation: bool = False


def scene_from_data(data: dict) -> ManaScene:
    options = []
    for option in data['options']:
        variants = tuple(ManaVariant(**{**v, 'flags': tuple(v['flags']),
                         'followups': tuple(ManaFollowup(**f) for f in v.get('followups', ()))})
                         for v in option.get('variants', ()))
        options.append(ManaOption(**{**option, 'variants': variants}))
    return ManaScene(**{**data, 'position': tuple(data['position']), 'options': tuple(options),
                        'condition': ManaCondition(**data.get('condition', {}))})


@lru_cache(maxsize=1)
def content() -> tuple[tuple[ManaScene, ...], tuple[ManaLesson, ...]]:
    path = Path(__file__).resolve().parents[3] / "content/tutorials/exploration_mana.json"
    data = json.loads(path.read_text())
    if data.get("version") not in (1, 2):
        raise ValueError("Nieobsługiwana wersja lekcji eksploracji.")
    scenes = tuple(scene_from_data(s) for s in data['scenes'])
    lessons = tuple(ManaLesson(**{**s, "offers": tuple(tuple(o) for o in s.get("offers", ())),
                                  "choices": tuple(s.get("choices", ()))}) for s in data["lessons"])
    if len({s.id for s in scenes}) != len(scenes) or len({s.id for s in lessons}) != len(lessons):
        raise ValueError("Id scen i lekcji muszą być unikalne.")
    for scene in scenes:
        if len(scene.options) < 3 or len({o.method_id for o in scene.options}) != len(scene.options):
            raise ValueError("Scena wymaga minimum trzech różnych metod.")
        if scene.dc < 1 or not (0 <= scene.position[0] < 20 and 0 <= scene.position[1] < 30):
            raise ValueError("Nieprawidłowy ST lub pozycja sceny.")
        for option in scene.options:
            if method_by_id(option.method_id).kind != scene.kind:
                raise ValueError("Metoda nie pasuje do celu.")
            profile_values(option.profile)
            obstacle_description(option.obstacle)
            if scene.condition.kind != 'none':
                required = {'success', 'failure'} | {
                    'compromise': {'compromise'}, 'sensitive_topic': {'sensitive_success'},
                    'color_goal': {'goal_success'}, 'favor': set(),
                }[scene.condition.kind]
                if {v.kind for v in option.variants} != required or len(option.variants) != len(required):
                    raise ValueError('Niekompletne warianty wyniku warunku.')
                if option.obstacle != 'none' or not scene.condition_text:
                    raise ValueError('Nowa rozmowa wymaga jednej jawnej zasady.')
                if scene.condition.kind == 'favor' and not scene.obligation:
                    raise ValueError('Ustępstwo wymaga jawnego zobowiązania.')
                for variant in option.variants:
                    if not variant.flags or len({f.id for f in variant.followups}) != len(variant.followups) or len(variant.followups) > 2:
                        raise ValueError('Nieprawidłowe konsekwencje sceny.')
    for lesson in lessons:
        if lesson.scene_id and not any(s.id == lesson.scene_id and s.kind == lesson.kind for s in scenes):
            raise ValueError('Lekcja wskazuje nieistniejącą scenę.')
        if lesson.kind not in {s.kind for s in scenes} or len(lesson.offers) != len(lesson.choices):
            raise ValueError("Niekompletna lekcja.")
        if lesson.profile:
            profile_values(lesson.profile)
        if lesson.obstacle:
            obstacle_description(lesson.obstacle)
        counts = {c: 0 for c in COLORS}
        for offer, choice in zip(lesson.offers, lesson.choices):
            if choice not in offer or len(offer) < 2 or any(c not in COLORS for c in offer):
                raise ValueError("Nieprawidłowa oferta ćwiczebna.")
            if len(offer) > 2 and (len(set(offer[:-1])) != 1 or offer[-1] == offer[0]):
                raise ValueError("Dociąganie kończy się na pierwszej innej barwie.")
            for color in offer:
                counts[color] += 1
        if max(counts.values()) > 5:
            raise ValueError("Ćwiczebna kolejność przekracza fizyczną talię.")
    return scenes, lessons


def scene_by_id(scene_id: str) -> ManaScene:
    for scene in content()[0]:
        if scene.id == scene_id:
            return scene
    raise ValueError('Nieznana scena rozmowy.')


def scene_for(kind: str) -> ManaScene:
    return next(s for s in content()[0] if s.kind == kind)


def lessons_for(hero: str) -> tuple[ManaLesson, ...]:
    return tuple(lesson for lesson in content()[1] if not lesson.hero_id or lesson.hero_id == hero)


def lesson_by_id(hero: str, lesson_id: str) -> ManaLesson:
    for lesson in lessons_for(hero):
        if lesson.id == lesson_id:
            return lesson
    raise ValueError("Ta lekcja nie jest dostępna dla wybranej postaci.")

"""Deterministic lesson sequence and figurine setups for guided training."""
from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.actors import Faction
from dnd_board_game.combat.targets import actor_as_combat_target
from dnd_board_game.rules import DiceExpression
from dnd_board_game.rules.shared_mana_catalog import CATALOG, HOLY_SYMBOL, SharedAbility
from dnd_board_game.scenarios.loader import LoadedEncounter
from dnd_board_game.world import Coordinate


@dataclass(frozen=True)
class TrainingStep:
    ability: SharedAbility
    boost_id: str = ''

    @property
    def id(self) -> str:
        return self.ability.id + (':' + self.boost_id if self.boost_id else '')

    @property
    def boosts(self) -> dict[str, int]:
        return {self.boost_id: 1} if self.boost_id else {}

    @property
    def name(self) -> str:
        boost = next((b for b in self.ability.boosts if b.id == self.boost_id), None)
        return self.ability.name + (f' · {boost.label}' if boost else '')


def steps(hero_id: str) -> tuple[TrainingStep, ...]:
    abilities = [a for a in (*CATALOG, HOLY_SYMBOL) if a.hero_id == hero_id]
    # Learn recovery first, then the shield and its extra damage before protection.
    if hero_id == 'garran':
        order = ('second_wind', 'shield_bash', 'defensive_stance', 'garran_command_halt',
                 'garran_shield_wall', 'garran_guard_companion', 'garran_rally',
                 'iron_bastion', 'counterattack_command')
        abilities.sort(key=lambda a: order.index(a.id))
    if hero_id == 'dagna':
        order = ('healing_word', 'caring_gesture', 'lesser_restoration', 'bless',
                 'sacred_flame', 'divine_care_aura', 'guiding_bolt', 'preserve_life',
                 'spiritual_weapon', 'turn_undead')
        abilities.sort(key=lambda a: order.index(a.id))
    from .pooled_mana_training import FOUNDATIONS
    foundation = tuple(TrainingStep(SharedAbility(hero_id, key, name, "A", "tutorial", "", text))
                       for key, name, text in FOUNDATIONS)
    return (*foundation, *(step for a in abilities for step in (TrainingStep(a), *(TrainingStep(a, b.id) for b in a.boosts))))


def configure_walkthrough(encounter: LoadedEncounter, hero_id: str, index: int) -> LoadedEncounter:
    """Use the existing terrain; each lesson gets fresh, suitable recipients."""
    course = steps(hero_id)
    if not 0 <= index <= len(course):
        raise ValueError('Nieprawidłowy krok samouczka.')
    final = index == len(course)
    ability_id = '' if final else course[index].ability.id
    hero = next(a for a in encounter.actors if str(a.id) == hero_id)
    dummy = next(a for a in encounter.actors if str(a.id) == 'recruitment_dummy')
    helper = next(a for a in encounter.actors if str(a.id) == 'recruitment_helper')
    hero_position = Coordinate(9, 18)
    positions = [Coordinate(10, 18)]
    helpers = []
    support = {'garran_shield_wall', 'garran_guard_companion', 'garran_rally', 'iron_bastion',
               'counterattack_command', 'bless', 'lesser_restoration', 'caring_gesture',
               'healing_word', 'preserve_life', 'mana_inspiration', 'victory_hymn'}
    if ability_id in support:
        helpers = [replace(helper, position=Coordinate(9, 17), name='Pomocnik do ćwiczeń', hp=5, max_hp=40)]
    if ability_id == 'garran_guard_companion':
        positions = [Coordinate(10, 16)]
    if ability_id == 'counterattack_command':
        positions = [Coordinate(10, 17)]
    if ability_id in {'hamstring_cut', 'blade_mistress', 'shadow_verdict'}:
        helpers = [replace(helper, position=Coordinate(11, 18), name='Partner do flanki')]
    if ability_id == 'hide':
        hero_position, positions = Coordinate(5, 15), [Coordinate(7, 15)]
    if hero_id in {'erynd', 'lorian', 'nimra'} and (final or (not final and course[index].ability.timing != 'R')):
        positions = [Coordinate(10, 17)] if hero_id == 'nimra' else [Coordinate(10, 12)]
    groups = {'sacred_flame', 'deafening_roar', 'reaper', 'unstoppable', 'blade_dance',
              'entangling_shot', 'anchoring_arrow', 'double_shot', 'arrow_rain',
              'nimra_flame_fan', 'nimra_force_wave', 'nimra_web', 'nimra_mind_break',
              'nimra_lightning_path', 'shatter', 'nimra_sticky_matrix'}
    if ability_id in groups:
        first = positions[0]
        positions += [Coordinate(first.col + 1, first.row), Coordinate(first.col + 1, first.row - 1)]
    if ability_id == 'nimra_force_wave':
        positions = [Coordinate(10, 18), Coordinate(11, 18), Coordinate(12, 18)]
    if not final and course[index].boost_id == 'exclude':
        helpers = [replace(helper, position=Coordinate(10, 16), name='Pomocnik do ochrony przed obszarem')]
    hero = replace(hero, position=hero_position,
                   hp=max(1, hero.max_hp - (12 if ability_id in {'second_wind', 'preserve_life'} else 0)))
    enemies = tuple(replace(dummy, id='recruitment_dummy' if i == 0 else f'recruitment_dummy_{i+1}',
                            name='Kukła pojedynkowa' if final else f'Kukła do ćwiczeń {i+1}',
                            position=p, ac=13 if final else 10, hp=30 if final else 180,
                            max_hp=30 if final else 180, speed_feet=30 if final else 0,
                            features=tuple(f for f in dummy.features if not final or f.feature_id != 'training_fixed_damage'))
                    for i, p in enumerate(positions))
    actors = (hero, *helpers, *enemies)
    ids = {a.id for a in actors}
    sources = {key: value for key, value in encounter.attack_sources_by_actor.items() if key in ids}
    options = {key: value for key, value in encounter.attack_source_options_by_actor.items() if key in ids}
    teaching_ac = actor_as_combat_target(hero, actors=actors).ac
    for enemy in enemies:
        source = encounter.attack_sources_by_actor[dummy.id]
        source = replace(source, damage_fixed=None if final else 6, damage_die_sides=6 if final else None,
                         damage_modifier=0, damage_hint='1k6' if final else '6',
                         attack_roll_request=replace(source.attack_roll_request, modifiers=(replace(source.attack_roll_request.modifiers[0], label='Kukła', value=3 if final else teaching_ac - 8 if course[index].ability.timing == 'R' else 5),)),
                         damage_components=tuple(replace(c, dice=DiceExpression(1, 6) if final else None,
                                                         fixed=None if final else 6, modifier=0) for c in source.damage_components))
        sources[enemy.id], options[enemy.id] = source, (source,)
    if final:
        from dnd_board_game.actors import FeatureGrant, FeatureSourceKind
        enemies = tuple(replace(e, features=(*e.features,
            FeatureGrant("mana_burn_deck", "Żar w talii", FeatureSourceKind.MONSTER, "pooled_mana_v01",
                         "Co drugą rundę pierwsze trafienie spala dwie karty talii; niedobór powoduje drain."))) for e in enemies)
        actors = (hero, *helpers, *enemies)
    board = replace(encounter.board, terrain_by_tile={p: t for p, t in encounter.board.terrain_by_tile.items() if p != Coordinate(3, 18)})
    return replace(encounter, board=board, actors=actors, attack_sources_by_actor=sources, attack_source_options_by_actor=options,
                   environment=tuple(e for e in encounter.environment if e.id != 'recruitment_nessa'),
                   scene_objects=tuple(o for o in encounter.scene_objects if o.id != 'recruitment_nessa'), objectives=())

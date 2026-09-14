"""One bow roll compared with each enemy's own AC and cover."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
from dnd_board_game.actors import Actor
from dnd_board_game.rules import ActiveEffect, D20RollInput, resolve_d20_roll
from .attack_flow import AttackSource
from .targets import combat_armor_class
from .session import CombatState
from .damage import DamageComponentSpec


@dataclass(frozen=True, slots=True)
class VolleyHit:
    actor_id: str
    armor_class: int
    cover: int
    hit: bool
    critical: bool


def volley_source(actor: Actor, source: AttackSource, effects: tuple[ActiveEffect, ...]) -> AttackSource:
    from .scene_interactions import attack_source_with_combat_effects
    return attack_source_with_combat_effects(actor, source, effects)


def resolve_volley(source: AttackSource, targets: Sequence[Actor], covers: dict[str, int],
                   effects: tuple[ActiveEffect, ...], *, natural_roll: int, natural_roll_2: int | None = None) -> tuple[int, tuple[VolleyHit, ...]]:
    if type(natural_roll) is not int or not 1 <= natural_roll <= 20:
        raise ValueError('Podaj naturalny wynik wspólnego k20.')
    result = resolve_d20_roll(D20RollInput(source.attack_roll_request, natural_roll, natural_roll_2))
    hits = []
    for target in targets:
        cover = covers.get(str(target.id), 0)
        ac = combat_armor_class(target, effects) + cover
        hits.append(VolleyHit(str(target.id), ac, cover,
            result.natural_roll == 20 or (result.natural_roll != 1 and result.total >= ac), result.natural_roll == 20))
    return result.total, tuple(hits)


def volley_bonuses(state: CombatState, source: AttackSource, hits: Sequence[VolleyHit], effects: tuple[ActiveEffect, ...]) -> tuple[tuple[DamageComponentSpec, str], ...]:
    """Assign each once-per-turn damage rider to at most one qualifying hit."""
    from .session import current_actor
    from .scene_interactions import attack_source_with_target_combat_effects
    from .erynd_features import first_blood_damage
    actor = current_actor(state)
    bonuses = []
    assigned = set()
    for hit in hits:
        if not hit.hit:
            continue
        target = next(a for a in state.actors if str(a.id) == hit.actor_id)
        contextual = attack_source_with_target_combat_effects(actor, target, source, effects)
        mark = next((c for c in contextual.damage_components if c.id == 'hunters_mark'), None)
        blood = first_blood_damage(actor, target, source.damage_components[0].damage_type) if not any(e.actor_id == str(actor.id) and e.kind == 'first_blood_used' for e in effects) else None
        for component in (mark, blood):
            if component is not None and component.id not in assigned:
                assigned.add(component.id)
                bonuses.append((component, hit.actor_id))
    return tuple(bonuses)

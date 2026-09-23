"""Board-game combat rules unique to Nimra.

The helpers in this module intentionally do not know about Flask, scanners or
LEDs.  They are shared by the UI and tests so target selection, Metamagic
costs and Arcane Echo cannot diverge between input transports.
"""

from __future__ import annotations

from dnd_board_game.actors.resources import uses_physical_mana

from dataclasses import dataclass, replace
from typing import Sequence

from dnd_board_game.actors import Actor, Faction, actor_has_feature, can_spend_actor_resource
from dnd_board_game.core.damage_types import DamageType
from dnd_board_game.rules import ActiveEffect, DiceExpression, EffectDuration, EffectSource, EffectSourceType

from .attack_flow import AttackSource, AttackSourceType
from .spells import grid_distance_feet


NIMRA_METAMAGIC_RESOURCE_ID = "metamagic_points"
NIMRA_LIGHTNING_PATH_ID = "nimra_lightning_path"
NIMRA_LIGHTNING_JUMP_RANGE_FEET = 15
NIMRA_METAMAGIC_IDS: tuple[str, ...] = (
    "nimra_sculpt_field",
    "nimra_distant_spell",
    "nimra_overcharged_spell",
    "nimra_forced_weave",
    "nimra_energy_transmutation",
)
NIMRA_METAMAGIC_COSTS = {
    "nimra_sculpt_field": 1,
    "nimra_distant_spell": 1,
    "nimra_overcharged_spell": 1,
    "nimra_forced_weave": 2,
    "nimra_energy_transmutation": 1,
}
NIMRA_METAMAGIC_NAMES = {
    "nimra_sculpt_field": "Rzeźbienie pola",
    "nimra_distant_spell": "Odległy czar",
    "nimra_overcharged_spell": "Przeciążony czar",
    "nimra_forced_weave": "Wymuszony splot",
    "nimra_energy_transmutation": "Transmutacja energii",
}
TRANSMUTABLE_DAMAGE_TYPES = frozenset(
    {DamageType.ACID, DamageType.COLD, DamageType.FIRE, DamageType.LIGHTNING, DamageType.THUNDER}
)


@dataclass(frozen=True, slots=True)
class LightningJump:
    target_id: str
    distance_feet: int
    is_enemy: bool


def select_lightning_jump_target(
    caster: Actor,
    primary_target: Actor,
    actors: Sequence[Actor],
    *,
    maximum_range_feet: int = NIMRA_LIGHTNING_JUMP_RANGE_FEET,
) -> LightningJump | None:
    """Choose one automatic jump after Piorunowy szlak's primary target.

    Distance wins first.  On an equal distance an enemy is preferred, then
    actor id provides stable replay behaviour.  The caster and the already-hit
    primary target are never candidates.  An ally is therefore hit when it is
    the sole/nearest legal candidate, exactly as the card warns.
    """

    candidates: list[tuple[int, int, str, Actor]] = []
    for candidate in actors:
        if candidate.id in {caster.id, primary_target.id} or candidate.is_defeated():
            continue
        distance = grid_distance_feet(primary_target.position, candidate.position)
        if distance > maximum_range_feet:
            continue
        is_enemy = candidate.faction not in {caster.faction, Faction.NEUTRAL}
        candidates.append((distance, 0 if is_enemy else 1, str(candidate.id), candidate))
    if not candidates:
        return None
    distance, enemy_rank, _actor_id, target = min(candidates)
    return LightningJump(str(target.id), distance, enemy_rank == 0)


def nimra_metamagic_compatibility(
    actor: Actor,
    source: AttackSource,
    metamagic_id: str,
) -> tuple[bool, str]:
    if str(actor.id) != "nimra" or not actor_has_feature(actor, metamagic_id):
        return False, "Nimra nie zna tej Metamagii."
    if source.source_type is not AttackSourceType.SPELL:
        return False, "Metamagia działa wyłącznie na czary."
    if metamagic_id == "nimra_sculpt_field":
        return (source.area is not None, "Czar nie tworzy obszaru.")
    if metamagic_id == "nimra_distant_spell":
        allowed = source.range_feet > 0 and source.id not in {"shield", "misty_step"}
        return allowed, "Tego czaru nie można wydłużyć."
    if metamagic_id == "nimra_overcharged_spell":
        allowed = any(component.dice is not None for component in source.damage_components)
        return allowed, "Czar nie zadaje obrażeń kośćmi."
    if metamagic_id == "nimra_forced_weave":
        return (bool(source.save_ability), "Czar nie wymaga rzutu obronnego.")
    if metamagic_id == "nimra_energy_transmutation":
        allowed = any(
            component.damage_type in TRANSMUTABLE_DAMAGE_TYPES
            for component in source.damage_components
        )
        return allowed, "Typu obrażeń tego czaru nie można transmutować."
    return False, "Nieznana Metamagia Nimry."


def apply_nimra_metamagic(
    actor: Actor,
    source: AttackSource,
    metamagic_id: str,
    *,
    transmuted_damage_type: DamageType | None = None,
    validate_resources: bool = True,
) -> AttackSource:
    if source.metamagic_ids:
        raise ValueError("Do jednego czaru Nimra może dołączyć tylko jedną Metamagię.")
    allowed, reason = nimra_metamagic_compatibility(actor, source, metamagic_id)
    if not allowed:
        raise ValueError(reason)
    cost = NIMRA_METAMAGIC_COSTS[metamagic_id]
    if validate_resources and not can_spend_actor_resource(actor, NIMRA_METAMAGIC_RESOURCE_ID, cost):
        raise ValueError(f"Brak {cost} pkt Metamagii.")
    range_feet = source.range_feet
    components = source.damage_components
    if metamagic_id == "nimra_distant_spell":
        range_feet = min(75, range_feet + 15)
    elif metamagic_id == "nimra_overcharged_spell":
        changed = False
        transformed = []
        for component in components:
            if not changed and component.dice is not None:
                component = replace(
                    component,
                    dice=DiceExpression(component.dice.count + 1, component.dice.sides),
                )
                changed = True
            transformed.append(component)
        components = tuple(transformed)
    elif metamagic_id == "nimra_energy_transmutation":
        if transmuted_damage_type not in TRANSMUTABLE_DAMAGE_TYPES:
            raise ValueError("Wybierz kwas, zimno, ogień, błyskawice albo grzmot.")
        components = tuple(
            replace(component, damage_type=transmuted_damage_type)
            if component.damage_type in TRANSMUTABLE_DAMAGE_TYPES
            else component
            for component in components
        )

    return replace(
        source,
        range_feet=range_feet,
        damage_components=components,
        damage_type=(
            components[0].damage_type.value if components else source.damage_type
        ),
        damage_die_sides=(
            components[0].dice.sides
            if components and components[0].dice is not None
            else source.damage_die_sides
        ),
        damage_hint=" + ".join(component.hint() for component in components),
        metamagic_ids=(metamagic_id,),
        resource_pool_id=NIMRA_METAMAGIC_RESOURCE_ID,
        resource_cost=cost,
    )


def nimra_metamagic_compatibility_for_action(
    actor: Actor,
    action: object,
    metamagic_id: str,
) -> tuple[bool, str]:
    if str(actor.id) != "nimra" or not actor_has_feature(actor, metamagic_id):
        return False, "Nimra nie zna tej Metamagii."
    if metamagic_id == "nimra_sculpt_field":
        return (getattr(action, "area", None) is not None, "Czar nie tworzy obszaru.")
    if metamagic_id == "nimra_distant_spell":
        allowed = int(getattr(action, "range_feet", 0)) > 0 and getattr(action, "id", "") not in {"shield", "misty_step"}
        return allowed, "Tego czaru nie można wydłużyć."
    if metamagic_id == "nimra_overcharged_spell":
        deals_dice_damage = (
            bool(str(getattr(action, "damage_type", "")).strip())
            and int(getattr(action, "damage_die_sides", 0)) > 0
            and (
                int(getattr(action, "projectile_damage_dice_count", 0)) > 0
                or int(getattr(action, "ongoing_damage_dice_count", 0)) > 0
                or bool(getattr(action, "damage_on_cast", False))
            )
        )
        return deals_dice_damage, "Czar nie zadaje obrażeń kośćmi."
    if metamagic_id == "nimra_forced_weave":
        allowed = (
            bool(getattr(action, "save_ability", None))
            and getattr(action, "area", None) is None
            and int(getattr(action, "target_count", 1)) == 1
        )
        return allowed, "Ten przepływ nie wskazuje pojedynczego celu rzutu obronnego."
    if metamagic_id == "nimra_energy_transmutation":
        try:
            current = DamageType(str(getattr(action, "damage_type", "")))
        except ValueError:
            current = None
        return (current in TRANSMUTABLE_DAMAGE_TYPES, "Typu obrażeń tego czaru nie można transmutować.")
    return False, "Nieznana Metamagia Nimry."


def apply_nimra_metamagic_to_action(
    actor: Actor,
    action: object,
    metamagic_token: str,
) -> object:
    metamagic_id, separator, damage_type_id = metamagic_token.partition("@")
    allowed, reason = nimra_metamagic_compatibility_for_action(actor, action, metamagic_id)
    if not allowed:
        raise ValueError(reason)
    cost = NIMRA_METAMAGIC_COSTS[metamagic_id]
    if not can_spend_actor_resource(actor, NIMRA_METAMAGIC_RESOURCE_ID, cost):
        raise ValueError(f"Brak {cost} pkt Metamagii.")
    changes: dict[str, object] = {
        "metamagic_ids": (metamagic_id,),
        "resource_pool_id": NIMRA_METAMAGIC_RESOURCE_ID,
        "resource_cost": cost,
    }
    if metamagic_id == "nimra_distant_spell":
        changes["range_feet"] = min(75, int(getattr(action, "range_feet", 0)) + 15)
    elif metamagic_id == "nimra_overcharged_spell":
        changes["projectile_damage_dice_count"] = int(
            getattr(action, "projectile_damage_dice_count", 0)
        ) + 1
    elif metamagic_id == "nimra_energy_transmutation":
        if not separator or DamageType(damage_type_id) not in TRANSMUTABLE_DAMAGE_TYPES:
            raise ValueError("Wybierz kwas, zimno, ogień, błyskawice albo grzmot.")
        changes["damage_type"] = damage_type_id
    return replace(action, **changes)


def arcane_echo_effects(
    actor: Actor,
    *,
    spell_id: str,
    metamagic_ids: Sequence[str],
    round_number: int,
) -> tuple[ActiveEffect, ...]:
    """Record a committed cast for the next Nimra turn; previews record nothing."""

    from .runes import uses_runes
    if uses_runes(actor) or not actor_has_feature(actor, "flaw_arcane_echo"):
        return ()
    source = EffectSource(EffectSourceType.SYSTEM, "flaw_arcane_echo", "Skaza: Echo magicznego wycieku")
    actor_id = str(actor.id)
    effects = [
        ActiveEffect(
            id=f"nimra_echo_spell:{actor_id}:{round_number}",
            actor_id=actor_id,
            kind="nimra_echo_spell",
            label="Echo czaru",
            object_id=f"spell:{spell_id}",
            value=round_number,
            source=source,
            duration=EffectDuration.UNTIL_ENCOUNTER_END,
            stacking_key=f"nimra_echo_spell:{actor_id}:{spell_id}",
        )
    ]
    if metamagic_ids:
        metamagic_id = tuple(metamagic_ids)[0].partition("@")[0]
        effects.append(
            ActiveEffect(
                id=f"nimra_echo_metamagic:{actor_id}:{round_number}",
                actor_id=actor_id,
                kind="nimra_echo_metamagic",
                label="Echo Metamagii",
                object_id=f"metamagic:{metamagic_id}",
                value=round_number,
                source=source,
                duration=EffectDuration.UNTIL_ENCOUNTER_END,
                stacking_key=f"nimra_echo_metamagic:{actor_id}:{metamagic_id}",
            )
        )
    return tuple(effects)


def arcane_echo_block_reason(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
    *,
    round_number: int,
    spell_id: str | None = None,
    metamagic_id: str | None = None,
) -> str:
    """Return a player-facing reason when last round's spell/meta is repeated."""

    if uses_physical_mana(actor) or not actor_has_feature(actor, "flaw_arcane_echo"):
        return ""
    for effect in active_effects:
        if effect.actor_id != str(actor.id) or effect.value + 1 != round_number:
            continue
        if spell_id and effect.kind == "nimra_echo_spell" and effect.object_id == f"spell:{spell_id}":
            return "Echo magicznego wycieku: tego samego czaru nie można rzucić runda po rundzie."
        if metamagic_id and effect.kind == "nimra_echo_metamagic" and effect.object_id == f"metamagic:{metamagic_id}":
            return "Echo magicznego wycieku: tej samej Metamagii nie można użyć runda po rundzie."
    return ""

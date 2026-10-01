"""Content boundary for the charge engine; existing encounters remain reusable."""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from typing import Any, Mapping

from dnd_board_game.actors import Actor, Faction, FeatureGrant, FeatureSourceKind
from dnd_board_game.combat.charge_encounter import ChargeEncounter
from dnd_board_game.combat.session import CombatState
from dnd_board_game.inventory.magic_items import effective_ability_modifier
from dnd_board_game.rules.resonance import PROFILE, ChargeActorState, ChargeState, ChargeWeapon
from dnd_board_game.scenarios.loader import LoadedEncounter, compile_actor_combat_content
from dnd_board_game.scenarios.rune_charge_catalog import load_rune_charge_catalog
from dnd_board_game.world.charge_movement import distance


def apply_charge_profile(actor: Actor) -> Actor:
    catalog = load_rune_charge_catalog()
    hero = catalog["heroes"].get(str(actor.id))
    if not hero or any(f.feature_id == PROFILE for f in actor.features):
        return actor
    old_prefixes = ("physical_mana:", "shared_mana:", "pooled_mana:", "mana_saturation:", "runes:")
    card_ids = {c["id"] for c in hero["cards"]}
    retired = {"action_surge", "savage_attacks", "sneak_attack", "first_blood", "fighting_style_archery", "scouts_vigilance", "mana_passives_v1"}
    features = tuple(f for f in actor.features if f.feature_id not in retired|card_ids
                     and not f.source_ref.startswith(old_prefixes) and not f.feature_id.startswith("flaw_"))
    for key in ("passive", "flaw"):
        entry = hero[key]
        features += (FeatureGrant(f"{PROFILE}_{key}", entry["name"], FeatureSourceKind.SCENARIO, PROFILE, entry["description"]),)
    features += tuple(FeatureGrant(c["id"], c["name"], FeatureSourceKind.SCENARIO, PROFILE, c["effect"]) for c in hero["cards"])
    features += (FeatureGrant(PROFILE, "Ładunki i Rezonans", FeatureSourceKind.SCENARIO, PROFILE),)
    return replace(actor, features=features, attacks_per_action=1, spell_slots=(), spells=(), spell_ids=(), spell_access=())


def charge_weapon(actor: Actor, source: Any) -> ChargeWeapon:
    """Use authored damage and equipment bonuses, not retired proficiency/passives."""
    ability = source.ability or "strength"
    hero = actor.faction == Faction.ALLY
    modifiers = source.attack_roll_request.modifiers
    attack_bonus = sum(m.value for m in modifiers if not hero or str(m.modifier_type) not in {"ability", "proficiency"})
    ability_damage = effective_ability_modifier(actor, ability)-source.ability_damage_modifier_applied if hero and source.adds_ability_modifier_to_damage else 0
    parts = tuple(dict(count=p.dice.count if p.dice else 0, sides=p.dice.sides if p.dice else 0,
                       value=(p.fixed or 0)+p.modifier, modifier=p.modifier+(ability_damage if p.id == "base" else 0),
                       damage_type=str(p.damage_type), label=p.label or source.name) for p in source.damage_components)
    if not parts:
        parts = (dict(count=1 if source.damage_die_sides else 0, sides=source.damage_die_sides or 0,
                      value=source.damage_fixed or 0, modifier=source.damage_modifier+ability_damage,
                      damage_type=str(source.damage_type), label=source.name),)
    return ChargeWeapon(source.id, source.name, ability, str(source.attack_kind),
                        max(1, (source.reach_feet or source.range_feet)//5), parts, attack_bonus,
                        str(source.source_type), source.ammunition_type or "", source.ammunition_cost if source.ammunition_type else 0,
                        source.on_hit_condition or source.conditional_on_hit_save_condition or "",
                        source.conditional_on_hit_save_ability or "", source.conditional_on_hit_save_dc,
                        minimum_movement=source.conditional_on_hit_minimum_movement_feet//5,
                        requires_adjacent_ally=source.conditional_on_hit_requires_adjacent_ally,
                        spell_save_ability=source.save_ability or "", spell_save_dc=source.save_dc,
                        spell_save_half=source.save_damage_on_success == "half", proficiency_id=source.proficiency_id or "")


@lru_cache(maxsize=64)
def _compiled_sources(actor: Actor) -> tuple[Any, ...]:
    """Bounded cache of immutable content compilation, never mutable rules state."""
    return compile_actor_combat_content(actor).attack_sources


def weapons_for(combat: CombatState, encounter: LoadedEncounter, effects: tuple[Any, ...] = ()) -> dict[str, ChargeWeapon]:
    result = {}
    for actor in combat.actors:
        if actor.faction == Faction.ALLY:
            equipped = {i.id for i in actor.inventory if i.kind == "weapon" and i.equipped and i.available}
            sources = _compiled_sources(actor)
            source = next((s for s in sources if s.source_item_id in equipped), None)
        else:
            source = encounter.attack_sources_by_actor.get(actor.id)
        if source is None:
            result[str(actor.id)] = ChargeWeapon("unarmed", "Bez broni", "strength", "melee", 1,
                (dict(count=0, sides=0, value=max(0, 1+effective_ability_modifier(actor, "strength")), damage_type="bludgeoning", label="Bez broni"),),
                0 if actor.faction == Faction.ALLY else effective_ability_modifier(actor, "strength"), source_type="unarmed")
        else:
            if effects:
                from dnd_board_game.combat.scene_interactions import attack_source_with_combat_effects
                source = attack_source_with_combat_effects(actor, source, effects)
            result[str(actor.id)] = charge_weapon(actor, source)
    return result


def encounter_engine(combat: CombatState, encounter: LoadedEncounter, *, catalog: Mapping[str, Any] | None = None, effects: tuple[Any, ...] = ()) -> ChargeEncounter:
    cover = {a.position: max((obj.stealth_bonus for obj in encounter.scene_objects
                            if any(distance(a.position, p) <= 1 for p in obj.positions)), default=0) for a in combat.actors}
    return ChargeEncounter(combat, encounter.board, catalog or load_rune_charge_catalog(), weapons_for(combat, encounter, effects), cover_bonuses=cover)


def start_charge_combat(combat: CombatState, encounter: LoadedEncounter) -> CombatState:
    actors = tuple(apply_charge_profile(a) if a.faction == Faction.ALLY else a for a in combat.actors)
    order = [str(e.actor.id) for e in combat.initiative_order.entries]
    state = ChargeState(order=order, index=combat.initiative_order.current_index, round=combat.initiative_order.round_number,
                        fighters={str(a.id): ChargeActorState() for a in actors})
    for hidden in combat.hidden_states:
        state.fighters[hidden.actor_id].hidden = list(hidden.hidden_from_actor_ids)
        state.fighters[hidden.actor_id].hide_total = hidden.stealth_total
    combat = replace(combat, actors=actors, shared_mana=None, resonance=state)
    engine = encounter_engine(combat, encounter)
    engine.begin_turn()
    return engine.combat_state()

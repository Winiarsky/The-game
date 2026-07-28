"""Pure single-class level-up transaction for saved characters."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.actors import Actor, ActorResourcePool, HitDicePool
from dnd_board_game.combat import SpellSlotState
from dnd_board_game.rules import experience_progress

from .builder import build_character
from .models import (
    CharacterBuildResources,
    CharacterCatalog,
    CharacterDraft,
    CreatedCharacter,
)


@dataclass(frozen=True, slots=True)
class LevelUpChoices:
    selected_cantrip_ids: tuple[str, ...] | None = None
    selected_spell_ids: tuple[str, ...] | None = None
    selected_prepared_spell_ids: tuple[str, ...] | None = None
    selected_subclass_id: str | None = None
    selected_expertise_ids: tuple[str, ...] | None = None
    selected_fighting_style_id: str | None = None
    selected_class_option_ids: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class CharacterLevelUpResult:
    character_before: CreatedCharacter
    character_after: CreatedCharacter
    level_before: int
    level_after: int
    hit_points_gained: int


def level_up_character(
    character: CreatedCharacter,
    catalog: CharacterCatalog,
    resources: CharacterBuildResources,
    *,
    choices: LevelUpChoices = LevelUpChoices(),
    level_cap: int = 3,
) -> CharacterLevelUpResult:
    """Advance exactly one level after validating XP and all newly required choices."""
    actor = character.actor
    if actor.level >= level_cap:
        raise ValueError(f"Postać osiągnęła limit poziomu {level_cap}.")
    progress = experience_progress(actor, level_cap=level_cap)
    target_level = actor.level + 1
    if progress.eligible_level < target_level:
        required = progress.next_level_experience or 0
        raise ValueError(
            f"Za mało XP na poziom {target_level}: "
            f"{actor.experience_points}/{required}."
        )
    draft = CharacterDraft(
        id=str(actor.id),
        name=actor.name,
        species_id=character.species_id,
        class_id=character.class_id,
        background_id=character.background_id,
        base_ability_scores=character.base_ability_scores,
        selected_skill_ids=character.selected_skill_ids,
        selected_expertise_ids=_choice(
            choices.selected_expertise_ids,
            character.selected_expertise_ids,
        ),
        selected_fighting_style_id=(
            character.selected_fighting_style_id
            if choices.selected_fighting_style_id is None
            else choices.selected_fighting_style_id
        ),
        equipment_package_id=character.equipment_package_id,
        selected_cantrip_ids=_choice(
            choices.selected_cantrip_ids,
            character.selected_cantrip_ids,
        ),
        selected_spell_ids=_choice(
            choices.selected_spell_ids,
            character.selected_spell_ids,
        ),
        selected_prepared_spell_ids=_choice(
            choices.selected_prepared_spell_ids,
            character.selected_prepared_spell_ids,
        ),
        selected_subclass_id=(
            character.selected_subclass_id
            if choices.selected_subclass_id is None
            else choices.selected_subclass_id
        ),
        portrait=actor.portrait,
        level=target_level,
        selected_species_bonus_ability_ids=(
            character.selected_species_bonus_ability_ids
        ),
        selected_species_skill_ids=character.selected_species_skill_ids,
        selected_species_tool_ids=character.selected_species_tool_ids,
        selected_species_language_ids=character.selected_species_language_ids,
        selected_species_variant_id=character.selected_species_variant_id,
        selected_species_cantrip_ids=character.selected_species_cantrip_ids,
        selected_class_option_ids=_choice(
            choices.selected_class_option_ids,
            character.selected_class_option_ids,
        ),
        selected_background_tool_ids=character.selected_background_tool_ids,
        selected_background_language_ids=(
            character.selected_background_language_ids
        ),
    )
    rebuilt = build_character(draft, catalog, resources)
    hp_gain = rebuilt.actor.max_hp - actor.max_hp
    advanced_actor = _merge_progression_actor(actor, rebuilt.actor, hp_gain)
    advanced = replace(rebuilt, actor=advanced_actor)
    return CharacterLevelUpResult(
        character_before=character,
        character_after=advanced,
        level_before=actor.level,
        level_after=target_level,
        hit_points_gained=hp_gain,
    )


def _merge_progression_actor(
    current: Actor,
    rebuilt: Actor,
    hp_gain: int,
) -> Actor:
    return replace(
        current,
        hp=current.hp + hp_gain if current.hp > 0 else current.hp,
        max_hp=rebuilt.max_hp,
        speed_feet=rebuilt.speed_feet,
        ability_scores=rebuilt.ability_scores,
        spell_slots=_merge_spell_slots(current.spell_slots, rebuilt.spell_slots),
        spell_save_dc=rebuilt.spell_save_dc,
        senses=rebuilt.senses,
        spell_ids=rebuilt.spell_ids,
        spell_preparation=rebuilt.spell_preparation,
        spells=rebuilt.spells,
        spell_access=rebuilt.spell_access,
        hit_dice=_merge_hit_dice(current.hit_dice, rebuilt.hit_dice),
        resource_pools=_merge_resource_pools(
            current.resource_pools,
            rebuilt.resource_pools,
        ),
        level=rebuilt.level,
        proficiency_bonus=rebuilt.proficiency_bonus,
        proficiencies=rebuilt.proficiencies,
        size=rebuilt.size,
        damage_affinities=rebuilt.damage_affinities,
        features=rebuilt.features,
    )


def _merge_spell_slots(
    current: tuple[SpellSlotState, ...],
    rebuilt: tuple[SpellSlotState, ...],
) -> tuple[SpellSlotState, ...]:
    old = {slot.level: slot for slot in current}
    merged: list[SpellSlotState] = []
    for slot in rebuilt:
        previous = old.get(slot.level)
        previous_remaining = previous.remaining if previous is not None else 0
        previous_maximum = previous.maximum if previous is not None else 0
        merged.append(
            replace(
                slot,
                remaining=min(
                    slot.maximum,
                    previous_remaining
                    + max(0, slot.maximum - previous_maximum),
                ),
            )
        )
    return tuple(merged)


def _merge_hit_dice(
    current: tuple[HitDicePool, ...],
    rebuilt: tuple[HitDicePool, ...],
) -> tuple[HitDicePool, ...]:
    old = {pool.die_sides: pool for pool in current}
    merged: list[HitDicePool] = []
    for pool in rebuilt:
        previous = old.get(pool.die_sides)
        previous_remaining = previous.remaining if previous is not None else 0
        previous_maximum = previous.maximum if previous is not None else 0
        merged.append(
            replace(
                pool,
                remaining=min(
                    pool.maximum,
                    previous_remaining
                    + max(0, pool.maximum - previous_maximum),
                ),
            )
        )
    return tuple(merged)


def _merge_resource_pools(
    current: tuple[ActorResourcePool, ...],
    rebuilt: tuple[ActorResourcePool, ...],
) -> tuple[ActorResourcePool, ...]:
    old = {pool.id: pool for pool in current}
    return tuple(
        replace(
            pool,
            current=(
                min(pool.maximum, old[pool.id].current)
                if pool.id in old
                else pool.current
            ),
        )
        for pool in rebuilt
    )


def _choice(
    selected: tuple[str, ...] | None,
    existing: tuple[str, ...],
) -> tuple[str, ...]:
    return existing if selected is None else selected

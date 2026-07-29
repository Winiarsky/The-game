from dataclasses import replace

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.inventory import InventoryItem, SpellcastingFocusKind
from dnd_board_game.rules import (
    SpellAccessKind,
    SpellAccessProfile,
    SpellCastingTime,
    SpellComponents,
    SpellDefinition,
    SpellDuration,
    SpellDurationKind,
    SpellMaterial,
    SpellRange,
    SpellRangeKind,
    SpellSchool,
    available_spell_slot_levels,
    spell_is_accessible,
    spell_duration_minutes,
    spell_target_count,
    spell_save_dc_for_spell,
    spellcasting_ability_for_spell,
    validate_spell_cast,
)
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    SpellSlotState,
    attack_source_for_actor,
    consume_spell_resource,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import Coordinate


def _spell(
    *,
    level: int = 1,
    components: SpellComponents = SpellComponents(verbal=True),
) -> SpellDefinition:
    return SpellDefinition(
        id="test_spell",
        name="Test spell",
        level=level,
        school=SpellSchool.EVOCATION,
        casting_time=SpellCastingTime.ACTION,
        range=SpellRange(SpellRangeKind.DISTANCE, 30),
        components=components,
        duration=SpellDuration(SpellDurationKind.INSTANTANEOUS),
        effect_kind="attack",
    )


def test_available_spell_slot_levels_supports_upcasting() -> None:
    slots = (
        SpellSlotState(1, 0, 2),
        SpellSlotState(2, 1, 1),
        SpellSlotState(3, 1, 1),
    )

    assert available_spell_slot_levels(slots, 1) == (2, 3)
    assert validate_spell_cast(_spell(), slots=slots).cast_level == 2
    assert validate_spell_cast(_spell(), slots=slots).valid is True
    assert validate_spell_cast(_spell(), slots=slots, cast_level=2).valid is True


def test_silence_blocks_verbal_spell_but_subtle_spell_ignores_components() -> None:
    slots = (SpellSlotState(1, 1, 1),)
    spell = _spell(
        components=SpellComponents(verbal=True, somatic=True),
    )

    blocked = validate_spell_cast(
        spell,
        slots=slots,
        verbal_components_blocked=True,
        has_free_hand=False,
    )
    subtle = validate_spell_cast(
        spell,
        slots=slots,
        verbal_components_blocked=True,
        has_free_hand=False,
        ignore_verbal_somatic=True,
    )

    assert blocked.valid is False
    assert "obszarze Ciszy" in blocked.errors[0]
    assert subtle.valid is True


def test_spell_duration_converts_to_exploration_minutes() -> None:
    assert spell_duration_minutes(
        SpellDuration(SpellDurationKind.MINUTE, 3)
    ) == 3
    assert spell_duration_minutes(
        SpellDuration(SpellDurationKind.HOUR, 2)
    ) == 120
    assert spell_duration_minutes(
        SpellDuration(SpellDurationKind.TEN_DAYS)
    ) == 10 * 24 * 60
    assert spell_duration_minutes(
        SpellDuration(SpellDurationKind.UNTIL_DISPELLED)
    ) is None
    assert spell_duration_minutes(
        SpellDuration(SpellDurationKind.INSTANTANEOUS)
    ) == 0


def test_spell_target_count_scales_from_selected_slot_level() -> None:
    assert spell_target_count(
        base_targets=3,
        spell_level=1,
        cast_level=1,
        targets_per_slot_level=1,
    ) == 3
    assert spell_target_count(
        base_targets=3,
        spell_level=1,
        cast_level=4,
        targets_per_slot_level=1,
    ) == 6


def test_known_prepared_and_spellbook_access_have_distinct_semantics() -> None:
    spell = _spell()
    known = SpellAccessProfile(SpellAccessKind.KNOWN, (spell.id,))
    prepared = SpellAccessProfile(SpellAccessKind.PREPARED, (spell.id,))
    spellbook = SpellAccessProfile(SpellAccessKind.SPELLBOOK, (spell.id,))

    assert spell_is_accessible(spell, (known,))
    assert not spell_is_accessible(spell, (prepared,))
    assert not spell_is_accessible(spell, (spellbook,))
    assert spell_is_accessible(spell, (prepared,), prepared_spell_ids=(spell.id,))
    assert spell_is_accessible(spell, (spellbook,), prepared_spell_ids=(spell.id,))
    assert spell_is_accessible(replace(spell, level=0), (prepared,))


def test_spell_access_keeps_source_specific_casting_ability() -> None:
    spell = _spell()
    actor = Actor(
        id=ActorId("high_elf_sorcerer"),
        name="High Elf Sorcerer",
        ac=10,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        ability_scores=AbilityScores(intelligence=16, charisma=14),
        proficiency_bonus=2,
        spell_save_dc=13,
        spell_access=(
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                ("fire_bolt",),
                casting_ability="intelligence",
            ),
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                ("chill_touch",),
                casting_ability="charisma",
            ),
        ),
    )

    assert spellcasting_ability_for_spell(actor, "fire_bolt") == "intelligence"
    assert spellcasting_ability_for_spell(actor, "chill_touch") == "charisma"
    assert spell_save_dc_for_spell(actor, "fire_bolt") == 13
    assert spell_save_dc_for_spell(actor, "chill_touch") == 12

    fire_bolt = attack_source_for_actor(
        AttackSource(
            id="fire_bolt",
            name="Fire Bolt",
            source_type=AttackSourceType.SPELL,
            range_feet=120,
            attack_roll_request=D20RollRequest(),
            ability="charisma",
        ),
        actor,
    )

    assert fire_bolt.ability == "intelligence"
    assert resolve_d20_roll(
        D20RollInput(fire_bolt.attack_roll_request, 10)
    ).total == 15


def test_focus_replaces_only_costless_unconsumed_material() -> None:
    focus = InventoryItem(
        id="holy_symbol",
        name="Holy symbol",
        kind="focus",
        spellcasting_focus_kind=SpellcastingFocusKind.HOLY_SYMBOL,
    )
    slots = (SpellSlotState(1, 1, 1),)
    costless = _spell(
        components=SpellComponents(
            somatic=True,
            materials=(SpellMaterial("incense", "incense"),),
        )
    )
    costly = replace(
        costless,
        components=SpellComponents(
            somatic=True,
            materials=(SpellMaterial("diamond", "diamond", minimum_value_cp=5000),),
        ),
    )
    consumed = replace(
        costless,
        components=SpellComponents(
            somatic=True,
            materials=(SpellMaterial("chalk", "chalk", consumed=True),),
        ),
    )

    assert validate_spell_cast(
        costless,
        slots=slots,
        inventory=(focus,),
        allowed_focus_kinds=("holy_symbol",),
    ).valid
    assert not validate_spell_cast(
        costly,
        slots=slots,
        inventory=(focus,),
        allowed_focus_kinds=("holy_symbol",),
    ).valid
    assert not validate_spell_cast(
        consumed,
        slots=slots,
        inventory=(focus,),
        allowed_focus_kinds=("holy_symbol",),
    ).valid


def test_costly_consumed_material_is_selected_for_consumption() -> None:
    diamond = InventoryItem(
        id="diamond",
        name="Diamond",
        kind="treasure",
        quantity=2,
        value_cp=5000,
    )
    spell = _spell(
        components=SpellComponents(
            verbal=True,
            materials=(
                SpellMaterial(
                    "diamond",
                    "diamond worth 50 gp",
                    minimum_value_cp=5000,
                    consumed=True,
                    quantity=2,
                ),
            ),
        )
    )

    result = validate_spell_cast(
        spell,
        slots=(SpellSlotState(1, 1, 1),),
        inventory=(diamond,),
    )

    assert result.valid
    assert result.material_uses[0].item_id == "diamond"
    assert result.material_uses[0].quantity == 2
    assert result.material_uses[0].consumed


def test_cast_consumes_selected_material_and_lowest_legal_slot() -> None:
    spell = _spell(
        components=SpellComponents(
            verbal=True,
            materials=(SpellMaterial("diamond", "diamond", consumed=True),),
        )
    )
    actor = Actor(
        id=ActorId("caster"),
        name="Caster",
        ac=10,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        spell_slots=(SpellSlotState(1, 0, 1), SpellSlotState(2, 1, 1)),
        inventory=(InventoryItem("diamond", "Diamond", "treasure", quantity=2),),
        spells=(spell,),
        spell_access=(SpellAccessProfile(SpellAccessKind.KNOWN, (spell.id,)),),
    )

    result = consume_spell_resource(actor, spell.level, spell_id=spell.id)

    assert result.spell_level == 2
    assert result.actor_after.spell_slots[1].remaining == 0
    assert result.actor_after.inventory[0].quantity == 1


def test_ritual_consumes_material_but_not_spell_slot() -> None:
    spell = replace(
        _spell(
            components=SpellComponents(
                verbal=True,
                materials=(SpellMaterial("chalk", "chalk", consumed=True),),
            )
        ),
        ritual=True,
    )
    actor = Actor(
        id=ActorId("ritualist"),
        name="Ritualist",
        ac=10,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        spell_slots=(SpellSlotState(1, 1, 1),),
        inventory=(InventoryItem("chalk", "Chalk", "gear", quantity=2),),
        spells=(spell,),
        spell_access=(SpellAccessProfile(SpellAccessKind.SPELLBOOK, (spell.id,)),),
    )

    result = consume_spell_resource(
        actor,
        spell.level,
        spell_id=spell.id,
        ritual=True,
    )

    assert result.consumed is False
    assert result.actor_after.spell_slots[0].remaining == 1
    assert result.actor_after.inventory[0].quantity == 1


def test_somatic_only_spell_requires_a_free_hand() -> None:
    spell = _spell(components=SpellComponents(somatic=True))

    result = validate_spell_cast(
        spell,
        slots=(SpellSlotState(1, 1, 1),),
        has_free_hand=False,
    )

    assert not result.valid
    assert "wolnej dłoni" in result.errors[0]

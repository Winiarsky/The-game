import pytest

from dataclasses import replace

from dnd_board_game.actors import (
    AbilityScores,
    FeatureGrant,
    FeatureSourceKind,
)
from dnd_board_game.character_creation import (
    CharacterDraft,
    build_character,
    load_character_catalog,
    load_character_resources,
)
from dnd_board_game.rules import (
    D20RollContextTag,
    D20RollInput,
    D20RollKind,
    D20RollRequest,
    SavingThrowEffectTag,
    actor_background_permission_ids,
    actor_is_immune_to_effect,
    apply_actor_d20_traits,
    long_rest_required_minutes,
    resolve_background_permission,
    resolve_d20_roll,
)
from dnd_board_game.combat import (
    DamageComponentInput,
    DamageType,
    apply_damage_result,
    build_player_initiative_prompts,
    resolve_damage,
)


@pytest.fixture
def content():
    catalog = load_character_catalog("content/character_creation/catalog.json")
    return catalog, load_character_resources(catalog, "content")


def _fighter(content, *, actor_id: str, species_id: str, background_id: str):
    catalog, resources = content
    species = catalog.species_by_id(species_id)
    background = catalog.background_by_id(background_id)
    fighter = catalog.class_by_id("fighter")
    assert species is not None
    assert background is not None
    assert fighter is not None
    species_language_ids = (
        ("dwarvish",)
        if species_id in {"human", "elf"}
        else ()
    )
    granted_skill_ids = {
        *species.skill_proficiencies,
        *background.skill_proficiencies,
    }
    selected_skill_ids = tuple(
        skill_id
        for skill_id in fighter.skill_choices
        if skill_id not in granted_skill_ids
    )[: fighter.skill_choice_count]
    known_languages = {*species.languages, *species_language_ids}
    selected_background_language_ids = tuple(
        language
        for language in ("elvish", "dwarvish", "gnomish", "orc", "draconic")
        if language not in known_languages
    )[: background.language_choice_count]
    return build_character(
        CharacterDraft(
            id=actor_id,
            name=actor_id.title(),
            species_id=species_id,
            class_id="fighter",
            background_id=background_id,
            base_ability_scores=AbilityScores(15, 14, 13, 12, 10, 8),
            selected_skill_ids=selected_skill_ids,
            selected_fighting_style_id="defense",
            equipment_package_id="fighter_sword_and_board",
            selected_species_language_ids=species_language_ids,
            selected_species_cantrip_ids=(
                ("mage_hand",) if species_id == "elf" else ()
            ),
            selected_species_tool_ids=(
                ("smiths_tools",) if species_id == "dwarf" else ()
            ),
            selected_background_tool_ids=background.tool_choices[
                : background.tool_choice_count
            ],
            selected_background_language_ids=selected_background_language_ids,
        ),
        catalog,
        resources,
    ).actor


def test_trance_shortens_individual_long_rest_requirement(content):
    elf = _fighter(
        content,
        actor_id="elf_soldier",
        species_id="elf",
        background_id="soldier",
    )
    human = _fighter(
        content,
        actor_id="human_soldier",
        species_id="human",
        background_id="soldier",
    )

    assert long_rest_required_minutes(elf) == 240
    assert long_rest_required_minutes(human) == 480


def test_character_catalog_builds_halfling_as_small(content):
    halfling = _fighter(
        content,
        actor_id="small_halfling",
        species_id="halfling",
        background_id="soldier",
    )

    assert halfling.size.value == "small"


def test_stonecunning_grants_double_proficiency_only_for_tagged_check(content):
    dwarf = _fighter(
        content,
        actor_id="dwarf_soldier",
        species_id="dwarf",
        background_id="soldier",
    )

    ordinary = apply_actor_d20_traits(
        dwarf,
        D20RollRequest(),
        D20RollKind.ABILITY_CHECK,
    )
    stonework = apply_actor_d20_traits(
        dwarf,
        D20RollRequest(),
        D20RollKind.ABILITY_CHECK,
        effect_tags=(D20RollContextTag.STONEWORK.value,),
    )

    assert resolve_d20_roll(D20RollInput(ordinary, 10)).total == 10
    assert resolve_d20_roll(D20RollInput(stonework, 10)).total == 14
    assert stonework.modifiers[-1].stacking_key == "proficiency"


def test_artificers_lore_grants_double_proficiency_only_for_tagged_check(content):
    gnome = _fighter(
        content,
        actor_id="gnome_sage",
        species_id="gnome",
        background_id="sage",
    )

    ordinary = apply_actor_d20_traits(
        gnome,
        D20RollRequest(),
        D20RollKind.ABILITY_CHECK,
    )
    lore = apply_actor_d20_traits(
        gnome,
        D20RollRequest(),
        D20RollKind.ABILITY_CHECK,
        effect_tags=(D20RollContextTag.ARTIFICERS_LORE.value,),
    )

    assert resolve_d20_roll(D20RollInput(ordinary, 10)).total == 10
    assert resolve_d20_roll(D20RollInput(lore, 10)).total == 14
    assert lore.modifiers[-1].stacking_key == "proficiency"


def test_jack_of_all_trades_applies_only_without_proficiency(content):
    bard = replace(
        _fighter(
            content,
            actor_id="bard_test",
            species_id="human",
            background_id="soldier",
        ),
        features=(
            FeatureGrant(
                "jack_of_all_trades",
                "Jack of All Trades",
                FeatureSourceKind.CLASS,
                "bard",
            ),
        ),
    )
    untrained = apply_actor_d20_traits(
        bard,
        D20RollRequest(),
        D20RollKind.ABILITY_CHECK,
    )
    trained = apply_actor_d20_traits(
        bard,
        D20RollRequest(
            modifiers=untrained.modifiers[:-1] + (
                replace(untrained.modifiers[-1], value=2),
            ),
        ),
        D20RollKind.ABILITY_CHECK,
    )

    assert untrained.modifiers[-1].value == 1
    assert len(trained.modifiers) == 1
    initiative = build_player_initiative_prompts((bard,))[0]
    jack_modifier = next(
        modifier
        for modifier in initiative.request.modifiers
        if modifier.stacking_key == "proficiency"
    )
    assert jack_modifier.value == bard.proficiency_bonus // 2


def test_divine_health_grants_disease_immunity(content):
    paladin = replace(
        _fighter(
            content,
            actor_id="paladin_test",
            species_id="human",
            background_id="soldier",
        ),
        features=(
            FeatureGrant(
                "divine_health",
                "Divine Health",
                FeatureSourceKind.CLASS,
                "paladin",
            ),
        ),
    )

    assert actor_is_immune_to_effect(
        paladin,
        SavingThrowEffectTag.DISEASE.value,
    )


def test_half_orc_relentless_endurance_prevents_first_non_instant_defeat(content):
    half_orc = _fighter(
        content,
        actor_id="half_orc_soldier",
        species_id="half_orc",
        background_id="soldier",
    )
    damage = resolve_damage(
        (DamageComponentInput(half_orc.hp, DamageType.SLASHING),),
    )

    first = apply_damage_result(half_orc, damage)
    second = apply_damage_result(first.actor_after, damage)
    instant = apply_damage_result(
        half_orc,
        resolve_damage(
            (
                DamageComponentInput(
                    half_orc.hp + half_orc.max_hp,
                    DamageType.SLASHING,
                ),
            )
        ),
    )

    assert half_orc.senses.darkvision_feet == 60
    assert first.actor_after.hp == 1
    assert first.actor_after.resource_pools[-1].id == "relentless_endurance_uses"
    assert first.actor_after.resource_pools[-1].current == 0
    assert first.defeated is False
    assert second.actor_after.hp == 0
    assert second.actor_after.needs_death_save() is True
    assert instant.instant_death is True
    assert instant.actor_after.hp == 0
    assert instant.actor_after.resource_pools[-1].current == 1


@pytest.mark.parametrize(
    ("background_id", "permissions"),
    (
        (
            "acolyte",
            ("request_faithful_shelter", "request_faithful_care"),
        ),
        ("charlatan", ("maintain_false_identity",)),
        ("criminal", ("contact_criminal_network",)),
        ("entertainer", ("secure_performance_lodging",)),
        ("folk_hero", ("request_commoner_shelter",)),
        ("guild_artisan", ("request_guild_support",)),
        ("hermit", ("recall_personal_discovery",)),
        ("noble", ("request_noble_audience",)),
        ("outlander", ("forage_and_recall_geography",)),
        ("sage", ("locate_lore_source",)),
        ("sailor", ("secure_ship_passage",)),
        ("soldier", ("invoke_military_rank", "request_military_aid")),
        ("urchin", ("navigate_city_shortcut",)),
    ),
)
def test_background_permissions_are_data_driven_actor_grants(
    content,
    background_id,
    permissions,
):
    actor = _fighter(
        content,
        actor_id=f"{background_id}_hero",
        species_id="human",
        background_id=background_id,
    )

    assert actor_background_permission_ids(actor) == permissions
    for permission_id in permissions:
        resolution = resolve_background_permission(
            actor,
            permission_id,
            scene_permission_ids=permissions,
        )
        assert resolution.allowed is True
        assert resolution.feature_id is not None


def test_background_permission_requires_actor_grant_and_scene_opportunity(content):
    soldier = _fighter(
        content,
        actor_id="ranked_soldier",
        species_id="human",
        background_id="soldier",
    )

    available = resolve_background_permission(
        soldier,
        "request_military_aid",
        scene_permission_ids=("request_military_aid",),
    )
    unavailable_scene = resolve_background_permission(
        soldier,
        "request_military_aid",
        scene_permission_ids=(),
    )
    unknown_actor_permission = resolve_background_permission(
        soldier,
        "locate_lore_source",
        scene_permission_ids=("locate_lore_source",),
    )

    assert available.allowed is True
    assert available.feature_id == "military_rank"
    assert unavailable_scene.allowed is False
    assert unknown_actor_permission.allowed is False

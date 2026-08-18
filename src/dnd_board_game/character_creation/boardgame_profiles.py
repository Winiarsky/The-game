"""Role-first additions applied only to the seven curated starter heroes."""

from __future__ import annotations

from dataclasses import replace

from dnd_board_game.actors import (
    Actor,
    ActorResourcePool,
    FeatureGrant,
    FeatureSourceKind,
    RecoveryPeriod,
)
from dnd_board_game.rules import (
    SpellAccessKind,
    SpellAccessProfile,
    SpellComponents,
    SpellDefinition,
)


_ACTIVE_FEATURES: dict[str, tuple[tuple[str, str], ...]] = {
    "garran": (
        ("guard_duty", "Warta"),
        ("iron_line", "Żelazna linia"),
        ("action_surge", "Zryw akcji"),
        ("lay_on_hands", "Ratunek polowy"),
        ("defensive_stance", "Pozycja obronna"),
    ),
    "brakka": (
        ("intimidation", "Zastraszanie siłą"),
        ("reckless_attack", "Lekkomyślny atak"),
        ("frenzy", "Szał bojowy"),
        ("action_surge", "Niepowstrzymany impet"),
        ("cunning_action", "Drapieżny pęd"),
    ),
    "mira": (
        ("break_in", "Włamanie"),
        ("cunning_action", "Przebiegła akcja"),
        ("instinctive_dodge", "Unik instynktowny"),
        ("exploit_weakness", "Wykorzystanie słabości"),
    ),
    "dagna": (("diagnosis", "Diagnoza"),),
    "erynd": (
        ("tracking", "Tropienie"),
        ("fighting_style_archery", "Styl walki: Łucznictwo"),
        ("cunning_action", "Zwiadowcza mobilność"),
        ("patient_shot", "Strzelecka cierpliwość"),
    ),
}

_FEATURE_MIN_LEVEL: dict[tuple[str, str], int] = {
    ("brakka", "action_surge"): 2,
    ("brakka", "cunning_action"): 2,
}

_FIXED_DECK_SPELLS: dict[str, tuple[tuple[int, str, str | None], ...]] = {
    "garran": (
        (2, "command", "tactics_uses"),
        (2, "shield_of_faith", "tactics_uses"),
        (3, "heroism", "tactics_uses"),
        (3, "warding_bond", "tactics_uses"),
    ),
    "brakka": (
        (3, "false_life", "ferocity_uses"),
        (3, "thunderwave", "ferocity_uses"),
    ),
    "mira": (
        (1, "invisibility", "trick_uses"),
        (1, "find_traps", "trick_uses"),
        (2, "vicious_mockery", "trick_uses"),
        (3, "mirror_image", "trick_uses"),
    ),
    "dagna": (
        (1, "sacred_flame", None),
        (1, "healing_word", None),
        (1, "bless", None),
        (1, "sanctuary", None),
        (2, "guiding_bolt", None),
        (3, "aid", None),
        (3, "lesser_restoration", None),
        (3, "warding_bond", None),
    ),
    "lorian": (
        (1, "vicious_mockery", None),
        (1, "thunderwave", None),
        (1, "healing_word", None),
        (2, "faerie_fire", None),
        (2, "heroism", None),
        (3, "hideous_laughter", None),
    ),
    "nimra": (
        (1, "ray_of_frost", None),
        (1, "grease", None),
        (1, "shield", None),
        (1, "sleep", None),
        (2, "fog_cloud", None),
        (3, "web", None),
        (3, "hold_person", None),
        (3, "misty_step", None),
        (3, "shatter", None),
    ),
    "erynd": (
        (1, "hunters_mark", "instinct"),
        (1, "goodberry", "instinct"),
        (1, "find_traps", "instinct"),
        (2, "misty_step", "instinct"),
        (3, "spike_growth", "instinct"),
        (3, "see_invisibility", "instinct"),
    ),
}

_DECK_CASTING_ABILITIES = {
    "garran": "strength",
    "brakka": "constitution",
    "mira": "dexterity",
    "dagna": "wisdom",
    "lorian": "charisma",
    "nimra": "intelligence",
    "erynd": "wisdom",
}

_ACTION_IDS_BY_FEATURE: dict[str, tuple[str, ...]] = {
    "action_surge": ("action_surge",),
    "lay_on_hands": ("lay_on_hands",),
    "defensive_stance": ("defensive_stance",),
    "reckless_attack": ("reckless_attack",),
    "frenzy": ("frenzy",),
    "cunning_action": ("cunning_action",),
    "instinctive_dodge": ("instinctive_dodge",),
    "exploit_weakness": ("exploit_weakness",),
    "patient_shot": ("patient_shot",),
    "guard_duty": ("guard_duty",),
    "intimidation": ("intimidation",),
    "break_in": ("break_in",),
    "diagnosis": ("diagnosis",),
    "tracking": ("tracking",),
}

_RESOURCE_IDS_BY_FEATURE: dict[str, tuple[str, ...]] = {
    "exploit_weakness": ("trick_uses",),
    "patient_shot": ("instinct",),
}

_PRIMARY_ABILITY_BOOSTS = {
    "garran": "strength",
    "brakka": "strength",
    "mira": "dexterity",
    "dagna": "wisdom",
    "lorian": "charisma",
    "nimra": "intelligence",
    "erynd": "dexterity",
}
_ABILITY_BOOST_FEATURE_ID = "boardgame_level_3_ability_boost"
_ABILITY_LABELS_PL = {
    "strength": "Siła",
    "dexterity": "Zręczność",
    "constitution": "Kondycja",
    "intelligence": "Inteligencja",
    "wisdom": "Mądrość",
    "charisma": "Charyzma",
}

_FLAW_FEATURES: dict[str, tuple[str, str]] = {
    "garran": ("flaw_command_guilt", "Skaza: Wina dowódcy"),
    "brakka": ("flaw_chains", "Skaza: Bitewny amok"),
    "mira": ("flaw_interrogation", "Skaza: Lęk przed przesłuchaniem"),
    "dagna": ("flaw_leave_no_one", "Skaza: Nikogo nie zostawiam"),
    "lorian": ("flaw_approval", "Skaza: Głód aprobaty"),
    "nimra": ("flaw_arcane_echo", "Skaza: Echo magicznego wycieku"),
    "erynd": ("flaw_ambush_survivor", "Skaza: Ocalały z zasadzki"),
}


def apply_boardgame_archetype(
    actor: Actor,
    *,
    spell_definitions: tuple[SpellDefinition, ...] = (),
) -> Actor:
    actor_id = str(actor.id)
    features = list(actor.features)
    existing_feature_ids = {feature.feature_id for feature in features}
    boost_ability = _PRIMARY_ABILITY_BOOSTS.get(actor_id)
    if (
        actor.level >= 3
        and boost_ability is not None
        and _ABILITY_BOOST_FEATURE_ID not in existing_feature_ids
    ):
        actor = replace(
            actor,
            ability_scores=replace(
                actor.ability_scores,
                **{
                    boost_ability: min(
                        20,
                        getattr(actor.ability_scores, boost_ability) + 2,
                    )
                },
            ),
        )
        features.append(
            FeatureGrant(
                feature_id=_ABILITY_BOOST_FEATURE_ID,
                label=f"Premia archetypu: +2 {_ABILITY_LABELS_PL[boost_ability]}",
                source_kind=FeatureSourceKind.SCENARIO,
                source_ref=f"boardgame_archetype:{actor_id}",
            )
        )
        existing_feature_ids.add(_ABILITY_BOOST_FEATURE_ID)
    for feature_id, label in _ACTIVE_FEATURES.get(actor_id, ()):
        if actor.level < _FEATURE_MIN_LEVEL.get((actor_id, feature_id), 1):
            continue
        if feature_id in existing_feature_ids:
            continue
        features.append(
            FeatureGrant(
                feature_id=feature_id,
                label=label,
                source_kind=FeatureSourceKind.SCENARIO,
                source_ref=f"boardgame_archetype:{actor_id}",
                action_ids=_ACTION_IDS_BY_FEATURE.get(feature_id, ()),
                resource_ids=_RESOURCE_IDS_BY_FEATURE.get(feature_id, ()),
            )
        )

    flaw = _FLAW_FEATURES.get(actor_id)
    if flaw is not None and flaw[0] not in existing_feature_ids:
        features.append(
            FeatureGrant(
                feature_id=flaw[0],
                label=flaw[1],
                source_kind=FeatureSourceKind.SCENARIO,
                source_ref=f"boardgame_archetype:{actor_id}",
            )
        )

    pools = list(actor.resource_pools)
    existing_pool_ids = {pool.id for pool in pools}
    if actor_id == "garran" and "guard_duty_uses" not in existing_pool_ids:
        maximum = 3 if actor.level >= 3 else 2
        pools.append(
            ActorResourcePool(
                "guard_duty_uses",
                "Warta",
                maximum,
                maximum,
                RecoveryPeriod.LONG_REST,
            )
        )
    if actor_id == "garran" and "action_surge_uses" not in existing_pool_ids:
        pools.append(
            ActorResourcePool(
                "action_surge_uses",
                "Zryw akcji",
                1,
                1,
                RecoveryPeriod.SHORT_REST,
            )
        )
    if actor_id == "garran" and "lay_on_hands_points" not in existing_pool_ids:
        pools.append(
            ActorResourcePool(
                "lay_on_hands_points",
                "Ratunek polowy",
                actor.level * 5,
                actor.level * 5,
                RecoveryPeriod.LONG_REST,
            )
        )
    if actor_id == "garran" and "defensive_stance_uses" not in existing_pool_ids:
        pools.append(
            ActorResourcePool(
                "defensive_stance_uses",
                "Pozycja obronna",
                1,
                1,
                RecoveryPeriod.SHORT_REST,
            )
        )
    if actor_id == "mira" and "instinctive_dodge_uses" not in existing_pool_ids:
        pools.append(
            ActorResourcePool(
                "instinctive_dodge_uses",
                "Unik instynktowny",
                1,
                1,
                RecoveryPeriod.SHORT_REST,
            )
        )
    if actor_id == "mira" and "trick_uses" not in existing_pool_ids:
        maximum = 3 if actor.level >= 3 else 2
        pools.append(
            ActorResourcePool(
                "trick_uses",
                "Fortele",
                maximum,
                maximum,
                RecoveryPeriod.LONG_REST,
            )
        )
    if actor_id == "garran" and actor.level >= 2 and "tactics_uses" not in existing_pool_ids:
        maximum = 3 if actor.level >= 3 else 2
        pools.append(
            ActorResourcePool(
                "tactics_uses",
                "Taktyka",
                maximum,
                maximum,
                RecoveryPeriod.LONG_REST,
            )
        )
    if actor_id == "brakka" and actor.level >= 2 and "action_surge_uses" not in existing_pool_ids:
        pools.append(
            ActorResourcePool(
                "action_surge_uses",
                "Niepowstrzymany impet",
                1,
                1,
                RecoveryPeriod.SHORT_REST,
            )
        )
    if actor_id == "brakka" and actor.level >= 3 and "ferocity_uses" not in existing_pool_ids:
        pools.append(
            ActorResourcePool(
                "ferocity_uses",
                "Dzikość",
                2,
                2,
                RecoveryPeriod.LONG_REST,
            )
        )
    if actor_id == "erynd" and "instinct" not in existing_pool_ids:
        maximum = 3 if actor.level >= 3 else 2
        pools.append(
            ActorResourcePool(
                "instinct",
                "Instynkt",
                maximum,
                maximum,
                RecoveryPeriod.LONG_REST,
            )
        )
    if actor_id == "lorian":
        inspiration_maximum = max(
            1,
            (actor.ability_scores.charisma - 10) // 2,
        )
        pools = [
            replace(
                pool,
                current=max(
                    0,
                    inspiration_maximum - (pool.maximum - pool.current),
                ),
                maximum=inspiration_maximum,
            )
            if pool.id == "bardic_inspiration_uses"
            else pool
            for pool in pools
        ]
    spells = list(actor.spells)
    spell_ids = list(actor.spell_ids)
    spell_access = list(actor.spell_access)
    spell_save_dc = actor.spell_save_dc
    casting_ability = _DECK_CASTING_ABILITIES.get(actor_id)
    if casting_ability is not None and spell_save_dc is not None:
        ability_score = getattr(actor.ability_scores, casting_ability)
        spell_save_dc = 8 + actor.proficiency_bonus + (ability_score - 10) // 2
    deck_spell_specs = tuple(
        (spell_id, resource_id)
        for minimum_level, spell_id, resource_id in _FIXED_DECK_SPELLS.get(actor_id, ())
        if actor.level >= minimum_level
    )
    if deck_spell_specs:
        # The physical deck is the complete decision interface for a curated
        # hero.  Keep spells on the actor for descriptive/narrative use, but do
        # not leave additional class-preparation profiles mechanically castable.
        spell_access = []
        added_spell_ids: list[str] = []
        resource_mappings: list[tuple[str, str]] = []
        for spell_id, resource_id in deck_spell_specs:
            spell = next(
                (item for item in spell_definitions if item.id == spell_id),
                None,
            )
            if spell is None:
                continue
            if resource_id is not None:
                spell = replace(
                    spell,
                    components=SpellComponents(verbal=True),
                )
            if spell.id in spell_ids:
                spell_index = next(
                    index
                    for index, existing_spell in enumerate(spells)
                    if existing_spell.id == spell.id
                )
                spells[spell_index] = spell
            else:
                spells.append(spell)
                spell_ids.append(spell.id)
            added_spell_ids.append(spell.id)
            if resource_id is not None:
                resource_mappings.append((spell.id, resource_id))
        if added_spell_ids:
            casting_ability = _DECK_CASTING_ABILITIES[actor_id]
            spell_access.append(
                SpellAccessProfile(
                    kind=(
                        SpellAccessKind.INNATE
                        if resource_mappings
                        else SpellAccessKind.KNOWN
                    ),
                    spell_ids=tuple(added_spell_ids),
                    allowed_focus_kinds=tuple(
                        dict.fromkeys(
                            focus_kind
                            for profile in actor.spell_access
                            for focus_kind in profile.allowed_focus_kinds
                        )
                    ),
                    casting_ability=casting_ability,
                    resource_ids_by_spell=tuple(resource_mappings),
                )
            )
            if resource_mappings:
                ability_score = getattr(actor.ability_scores, casting_ability)
                spell_save_dc = (
                    8 + actor.proficiency_bonus + (ability_score - 10) // 2
                )
    proficiencies = actor.proficiencies
    if actor_id == "erynd":
        proficiencies = replace(
            proficiencies,
            expertise=tuple(
                dict.fromkeys((*proficiencies.expertise, "stealth", "survival"))
            ),
        )
    return replace(
        actor,
        features=tuple(features),
        resource_pools=tuple(pools),
        spells=tuple(spells),
        spell_ids=tuple(spell_ids),
        spell_access=tuple(spell_access),
        spell_preparation=(None if deck_spell_specs else actor.spell_preparation),
        # Erynd's spell-shaped techniques spend Instinct, never ranger slots.
        spell_slots=() if actor_id == "erynd" else actor.spell_slots,
        spell_save_dc=spell_save_dc,
        proficiencies=proficiencies,
    )


__all__ = ["apply_boardgame_archetype"]

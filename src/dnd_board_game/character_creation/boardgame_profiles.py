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
    ability_modifier,
)


_ACTIVE_FEATURES: dict[str, tuple[tuple[str, str], ...]] = {
    "garran": (
        ("iron_line", "Żelazna linia"),
        ("action_surge", "Zryw akcji"),
        ("shield_bash", "Uderzenie tarczą"),
        ("defensive_stance", "Pozycja obronna"),
        ("garran_command_halt", "Rozkaz: Stać"),
        ("garran_shield_wall", "Osłona tarczą"),
        ("garran_rally", "Mowa dowódcy"),
        ("garran_guard_companion", "Osłona towarzysza"),
    ),
    "brakka": (
        ("intimidation", "Zastraszanie siłą"),
        ("reckless_attack", "Lekkomyślny atak"),
        ("powerful_strike", "Potężne uderzenie"),
        ("shoulder_check", "Z bara"),
        ("brakka_grapple", "Chwyt"),
        ("hard_as_rock", "Twarda jak skała"),
        ("acceleration", "Przyspieszenie"),
        ("deafening_roar", "Ogłuszający ryk"),
    ),
    "mira": (
        ("mira_shadow_stealth", "Mistrzyni ukrycia"),
        ("mira_shadow_killer", "Atak z cienia"),
        ("mira_ranged_evasion", "Ruchomy cel"),
        ("instinctive_dodge", "Unik instynktowny"),
        ("smoke_screen", "Zasłona dymna"),
        ("hamstring_cut", "Cięcie ścięgna"),
        ("piercing_attack", "Przeszywający atak"),
        ("guard_vault", "Przeskok przez gardę"),
        ("blade_mistress", "Mistrzyni ostrzy"),
        ("combat_trap_detection", "Wykrycie pułapek"),
    ),
    "dagna": (
        ("field_medic_step", "Krok ratowniczki"),
    ),
    "lorian": (
        ("crossbowman", "Kusznik"),
        ("optical_scope", "Luneta optyczna"),
        ("mocking_shot", "Ostrzał destabilizujący"),
        ("provoking_shot", "Prowokujący ostrzał"),
        ("entangling_shot", "Oplatający ostrzał"),
        ("counterpoint", "Kontrapunkt"),
        ("distracting_shout", "Rozpraszający okrzyk"),
        ("social_grace_bargaining", "Obycie i targowanie"),
        ("improvisation", "Improwizacja"),
    ),
    "erynd": (
        ("fighting_style_archery", "Styl walki: Łucznictwo"),
        ("first_blood", "Pierwsza krew"),
        ("scouts_vigilance", "Czujność zwiadowcy"),
        ("cunning_action", "Zwiadowcza mobilność"),
        ("aim", "Celowanie"),
        ("anchoring_arrow", "Strzała kotwicząca"),
        ("exposing_arrow", "Strzała odsłaniająca"),
        ("disrupting_arrow", "Strzała zakłócająca"),
        ("double_shot", "Podwójny strzał"),
    ),
    "nimra": (
        ("nimra_catalogue", "Katalog niemożliwego"),
        ("nimra_sculpt_field", "Rzeźbienie pola"),
        ("nimra_distant_spell", "Odległy czar"),
        ("nimra_overcharged_spell", "Przeciążony czar"),
        ("nimra_forced_weave", "Wymuszony splot"),
        ("nimra_energy_transmutation", "Transmutacja energii"),
    ),
}

_FEATURE_MIN_LEVEL: dict[tuple[str, str], int] = {}

_FIXED_DECK_SPELLS: dict[str, tuple[tuple[int, str, str | None], ...]] = {
    "garran": (),
    "brakka": (),
    "mira": (),
    "dagna": (
        (1, "sacred_flame", None),
        (1, "healing_word", None),
        (1, "bless", None),
        (1, "divine_care_aura", None),
        (2, "guiding_bolt", None),
        (3, "healing_grace_aura", None),
        (3, "lesser_restoration", None),
        (3, "spiritual_weapon", None),
    ),
    "lorian": (
        (1, "thunderwave", None),
        (1, "faerie_fire", None),
        (1, "panic_whisper", None),
        (3, "hideous_laughter", None),
        (3, "stage_command", None),
        (3, "accelerated_refrain", None),
    ),
    "nimra": (
        (1, "nimra_frost_pulse", None),
        (1, "nimra_acid_splash", None),
        (1, "nimra_mind_spike", None),
        (1, "nimra_flame_fan", None),
        (1, "nimra_force_wave", None),
        (1, "nimra_sticky_matrix", None),
        (1, "shield", None),
        (1, "nimra_sleep", None),
        (2, "nimra_fog", None),
        (3, "nimra_web", None),
        (3, "nimra_lightning_path", None),
        (3, "nimra_mind_break", None),
        (3, "nimra_stasis", None),
        (3, "misty_step", None),
        (3, "shatter", None),
    ),
    "erynd": (
        (1, "hunters_mark", "instinct"),
        (2, "misty_step", "instinct"),
        (3, "spike_growth", "instinct"),
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
    "shield_bash": ("shield_bash",),
    "defensive_stance": ("defensive_stance",),
    "garran_command_halt": ("garran_command_halt",),
    "garran_shield_wall": ("garran_shield_wall",),
    "garran_rally": ("garran_rally",),
    "garran_guard_companion": ("garran_guard_companion",),
    "reckless_attack": ("reckless_attack",),
    "powerful_strike": ("powerful_strike",),
    "shoulder_check": ("shoulder_check",),
    "hard_as_rock": ("hard_as_rock",),
    "acceleration": ("acceleration",),
    "deafening_roar": ("deafening_roar",),
    "cunning_action": ("cunning_action",),
    "instinctive_dodge": ("instinctive_dodge",),
    "smoke_screen": ("smoke_screen",),
    "hamstring_cut": ("hamstring_cut",),
    "piercing_attack": ("piercing_attack",),
    "guard_vault": ("guard_vault",),
    "blade_mistress": ("blade_mistress",),
    "combat_trap_detection": ("combat_trap_detection",),
    "aim": ("aim",),
    "anchoring_arrow": ("anchoring_arrow",),
    "exposing_arrow": ("exposing_arrow",),
    "disrupting_arrow": ("disrupting_arrow",),
    "double_shot": ("double_shot",),
    "mocking_shot": ("mocking_shot",),
    "provoking_shot": ("provoking_shot",),
    "optical_scope": ("optical_scope",),
    "entangling_shot": ("entangling_shot",),
    "counterpoint": ("counterpoint",),
    "distracting_shout": ("distracting_shout",),
    "improvisation": ("improvisation",),
    "guard_duty": ("guard_duty",),
    "intimidation": ("intimidation",),
    "tracking": ("tracking",),
    "nimra_sculpt_field": ("nimra_sculpt_field",),
    "nimra_distant_spell": ("nimra_distant_spell",),
    "nimra_overcharged_spell": ("nimra_overcharged_spell",),
    "nimra_forced_weave": ("nimra_forced_weave",),
    "nimra_energy_transmutation": ("nimra_energy_transmutation",),
}

_RESOURCE_IDS_BY_FEATURE: dict[str, tuple[str, ...]] = {
    "garran_command_halt": ("tactics_uses",),
    "garran_shield_wall": ("tactics_uses",),
    "garran_rally": ("tactics_uses",),
    "garran_guard_companion": ("tactics_uses",),
    "powerful_strike": ("ferocity_uses",),
    "hard_as_rock": ("ferocity_uses",),
    "acceleration": ("ferocity_uses",),
    "deafening_roar": ("ferocity_uses",),
    "instinctive_dodge": ("trick_uses",),
    "smoke_screen": ("trick_uses",),
    "hamstring_cut": ("trick_uses",),
    "piercing_attack": ("trick_uses",),
    "blade_mistress": ("trick_uses",),
    "anchoring_arrow": ("instinct",),
    "exposing_arrow": ("instinct",),
    "disrupting_arrow": ("instinct",),
    "double_shot": ("instinct",),
    "nimra_sculpt_field": ("metamagic_points",),
    "nimra_distant_spell": ("metamagic_points",),
    "nimra_overcharged_spell": ("metamagic_points",),
    "nimra_forced_weave": ("metamagic_points",),
    "nimra_energy_transmutation": ("metamagic_points",),
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
    "garran": ("flaw_remorse", "Skaza: Wyrzuty sumienia"),
    "brakka": ("flaw_chains", "Skaza: Bitewny amok"),
    "mira": ("flaw_exposed_panic", "Skaza: Panika po zdemaskowaniu"),
    "dagna": ("flaw_leave_no_one", "Skaza: Nikogo nie zostawiam"),
    "lorian": ("flaw_needs_audience", "Skaza: Potrzeba publiczności"),
    "nimra": ("flaw_arcane_echo", "Skaza: Echo magicznego wycieku"),
    "erynd": ("flaw_friendly_fire_trauma", "Skaza: Trauma bratobójczego strzału"),
}

_REMOVED_FEATURE_IDS: dict[str, frozenset[str]] = {
    "garran": frozenset(
        {
            "guard_duty",
            "lay_on_hands",
            "military_rank",
            "flaw_command_guilt",
        }
    ),
    "brakka": frozenset(
        {"frenzy", "action_surge", "cunning_action", "danger_sense"}
    ),
    "mira": frozenset(
        {
            "brave",
            "cunning_action",
            "halfling_nimbleness",
            "naturally_stealthy",
            "flaw_interrogation",
            "mira_opportunity_evasion",
            "break_in",
            "exploit_weakness",
            "criminal_contact",
            "thieves_cant",
            "fast_hands",
            "second_story_work",
            "sneak_attack",
            "sneak_attack_2d6",
            "roguish_archetype",
        }
    ),
    "dagna": frozenset({"stonecunning", "shelter_of_the_faithful"}),
    "lorian": frozenset(
        {
            "skill_versatility",
            "by_popular_demand",
            "jack_of_all_trades",
            "song_of_rest",
            "bard_college",
            "bonus_proficiencies",
            "flaw_approval",
        }
    ),
    "erynd": frozenset(
        {
            "favored_enemy_beast",
            "favored_enemy",
            "natural_explorer_forest",
            "natural_explorer",
            "colossus_slayer",
            "hunters_prey",
            "primeval_awareness",
            "tracking",
            "patient_shot",
            "high_elf_cantrip",
            "flaw_ambush_survivor",
        }
    ),
    "nimra": frozenset(
        {
            "artificers_lore",
            "tinker",
            "researcher",
            "evocation_savant",
            "sculpt_spells",
        }
    ),
}


def apply_boardgame_archetype(
    actor: Actor,
    *,
    spell_definitions: tuple[SpellDefinition, ...] = (),
) -> Actor:
    actor = reconcile_boardgame_feature_removals(actor)
    actor_id = str(actor.id)
    # Curated knives were added after the class catalogue expanded simple-weapon
    # proficiencies into individual ids. Give their intended wielders proficiency.
    weapon_id = {"mira": "throwing_knife", "erynd": "hunting_knife"}.get(actor_id)
    if weapon_id and not actor.proficiencies.is_weapon_proficient(weapon_id):
        actor = replace(actor, proficiencies=replace(
            actor.proficiencies, weapons=(*actor.proficiencies.weapons, weapon_id),
        ))
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
    if actor_id == "mira":
        maximum = max(1, ability_modifier(actor.ability_scores.dexterity))
        existing = next((pool for pool in pools if pool.id == "trick_uses"), None)
        pools = [
            pool
            for pool in pools
            if pool.id != "instinctive_dodge_uses"
        ]
        if existing is None:
            pools.append(
                ActorResourcePool(
                    "trick_uses",
                    "Fortele",
                    maximum,
                    maximum,
                    RecoveryPeriod.LONG_REST,
                )
            )
        else:
            pools = [
                replace(
                    pool,
                    current=max(0, maximum - (pool.maximum - pool.current)),
                    maximum=maximum,
                    recovery=RecoveryPeriod.LONG_REST,
                )
                if pool.id == "trick_uses"
                else pool
                for pool in pools
            ]
    if actor_id == "garran" and actor.level >= 2:
        maximum = max(1, ability_modifier(actor.ability_scores.strength))
        existing = next((pool for pool in pools if pool.id == "tactics_uses"), None)
        if existing is None:
            pools.append(
                ActorResourcePool(
                    "tactics_uses",
                    "Taktyka",
                    maximum,
                    maximum,
                    RecoveryPeriod.LONG_REST,
                )
            )
        else:
            pools = [
                replace(
                    pool,
                    current=max(0, maximum - (pool.maximum - pool.current)),
                    maximum=maximum,
                )
                if pool.id == "tactics_uses"
                else pool
                for pool in pools
            ]
    if actor_id == "brakka" and actor.level >= 3 and "ferocity_uses" not in existing_pool_ids:
        maximum = max(1, ability_modifier(actor.ability_scores.constitution))
        pools.append(
            ActorResourcePool(
                "ferocity_uses",
                "Dzikość",
                0,
                maximum,
                RecoveryPeriod.NEVER,
            )
        )
    if actor_id == "erynd":
        maximum = max(1, ability_modifier(actor.ability_scores.dexterity))
        existing = next((pool for pool in pools if pool.id == "instinct"), None)
        if existing is None:
            pools.append(
                ActorResourcePool(
                    "instinct",
                    "Instynkt",
                    maximum,
                    maximum,
                    RecoveryPeriod.LONG_REST,
                )
            )
        else:
            pools = [
                replace(
                    pool,
                    current=max(0, maximum - (pool.maximum - pool.current)),
                    maximum=maximum,
                )
                if pool.id == "instinct"
                else pool
                for pool in pools
            ]
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
                recovery=RecoveryPeriod.SHORT_REST,
            )
            if pool.id == "bardic_inspiration_uses"
            else pool
            for pool in pools
        ]
    if actor_id == "nimra":
        maximum = max(1, ability_modifier(actor.ability_scores.intelligence))
        existing = next(
            (pool for pool in pools if pool.id == "metamagic_points"),
            None,
        )
        if existing is None:
            pools.append(
                ActorResourcePool(
                    "metamagic_points",
                    "Punkty Metamagii",
                    maximum,
                    maximum,
                    RecoveryPeriod.LONG_REST,
                )
            )
        else:
            pools = [
                replace(
                    pool,
                    current=max(0, maximum - (pool.maximum - pool.current)),
                    maximum=maximum,
                    recovery=RecoveryPeriod.LONG_REST,
                )
                if pool.id == "metamagic_points"
                else pool
                for pool in pools
            ]
    spells = list(actor.spells)
    spell_ids = list(actor.spell_ids)
    spell_access = list(actor.spell_access)
    if actor_id == "garran":
        retired_spell_ids = {"command", "shield_of_faith", "heroism", "warding_bond"}
        spells = [spell for spell in spells if spell.id not in retired_spell_ids]
        spell_ids = [spell_id for spell_id in spell_ids if spell_id not in retired_spell_ids]
    if actor_id == "lorian":
        retired_spell_ids = {
            "vicious_mockery",
            "mage_hand",
            "healing_word",
            "charm_person",
            "heroism",
        }
        spells = [spell for spell in spells if spell.id not in retired_spell_ids]
        spell_ids = [spell_id for spell_id in spell_ids if spell_id not in retired_spell_ids]
        spell_access = []
    if actor_id == "mira":
        retired_spell_ids = {
            "invisibility",
            "find_traps",
            "vicious_mockery",
            "mirror_image",
        }
        spells = [spell for spell in spells if spell.id not in retired_spell_ids]
        spell_ids = [spell_id for spell_id in spell_ids if spell_id not in retired_spell_ids]
        spell_access = []
    if actor_id == "erynd":
        retired_spell_ids = {"goodberry", "find_traps", "see_invisibility", "cure_wounds", "light"}
        spells = [spell for spell in spells if spell.id not in retired_spell_ids]
        spell_ids = [spell_id for spell_id in spell_ids if spell_id not in retired_spell_ids]
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
    inventory = actor.inventory
    if actor_id == "lorian":
        allowed_items = {"rapier", "hand_crossbow", "leather_armor", "lute"}
        inventory = tuple(
            item
            for item in actor.inventory
            if (item.source_ref or item.id) in allowed_items
        )
        # Obycie i targowanie owns the social specialization. Keeping an
        # additional Expertise multiplier here would apply the same concept
        # twice and make the scenario DCs effectively meaningless.
        proficiencies = replace(
            proficiencies,
            expertise=tuple(
                skill
                for skill in proficiencies.expertise
                if skill not in {"persuasion", "stealth"}
            ),
        )
    return replace(
        actor,
        features=tuple(features),
        resource_pools=tuple(pools),
        spells=tuple(spells),
        spell_ids=tuple(spell_ids),
        spell_access=tuple(spell_access),
        spell_preparation=(
            None if deck_spell_specs or actor_id in {"mira", "erynd"}
            else actor.spell_preparation
        ),
        # Erynd's spell-shaped techniques spend Instinct, never ranger slots.
        spell_slots=() if actor_id in {"erynd", "mira"} else actor.spell_slots,
        spell_save_dc=spell_save_dc,
        proficiencies=proficiencies,
        inventory=inventory,
    )


def reconcile_boardgame_feature_removals(actor: Actor) -> Actor:
    """Migrate retired curated features in restored actors without resetting state."""

    actor_id = str(actor.id)
    removed_feature_ids = _REMOVED_FEATURE_IDS.get(actor_id, frozenset())
    retired_resource_ids = (
        {"guard_duty_uses", "lay_on_hands_points", "defensive_stance_uses"}
        if actor_id == "garran"
        else {"primeval_awareness_uses"} if actor_id == "erynd"
        else {"instinctive_dodge_uses"} if actor_id == "mira"
        else set()
    )
    features = [
        feature
        for feature in actor.features
        if feature.feature_id not in removed_feature_ids
    ]
    current_flaw = _FLAW_FEATURES.get(actor_id)
    if current_flaw is not None and current_flaw[0] not in {
        feature.feature_id for feature in features
    }:
        features.append(
            FeatureGrant(
                feature_id=current_flaw[0],
                label=current_flaw[1],
                source_kind=FeatureSourceKind.SCENARIO,
                source_ref=f"boardgame_archetype:{actor_id}",
            )
        )
    migrated_features = tuple(features)
    resource_pools = tuple(
        pool for pool in actor.resource_pools if pool.id not in retired_resource_ids
    )
    return (
        actor
        if migrated_features == actor.features
        and resource_pools == actor.resource_pools
        else replace(
            actor,
            features=migrated_features,
            resource_pools=resource_pools,
        )
    )


__all__ = ["apply_boardgame_archetype", "reconcile_boardgame_feature_removals"]

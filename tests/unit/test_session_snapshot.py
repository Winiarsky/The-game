import json
from dataclasses import replace

import pytest

from dnd_board_game.actors import (
    ActorId,
    ActorSenseProfile,
    ActorTrigger,
    CreatureSize,
    DamageAffinityProfile,
    DeathSaveState,
    FeatureGrant,
    FeatureSourceKind,
    ProficiencyProfile,
    ActorResourcePool,
    RecoveryPeriod,
    TriggerEffectKind,
    TriggerEventType,
)
from dnd_board_game.combat import (
    AmmunitionExpenditure,
    BattlefieldLoot,
    CombatCondition,
    ConditionSaveTiming,
    ConditionState,
    HiddenState,
    EnemyAiRuntimeState,
    EnemyOutcome,
    LongCastState,
    SummonedCreatureState,
    add_summoned_creature,
    summon_actor,
    DamageType,
    replace_actor,
    transform_into_wild_shape,
    set_scene_flag,
)
from dnd_board_game.exploration import (
    CraftingComponentSelection,
    CraftingDraft,
    EncounterEdge,
    EncounterEdgeType,
    PrecombatStealthAttempt,
    build_crafting_source_registry,
    craft_temporary_item,
    discover_scene_source,
    FixtureOperation,
    apply_fixture_action,
    plan_fixture_action,
    add_exploration_condition,
    ExplorationTrapStatus,
    NpcAttitude,
    NpcAttemptPolicy,
    NpcStateUpdate,
    npc_runtime_state_for,
    plan_npc_attempt,
    plan_npc_transition,
    resolve_npc_runtime_interaction,
    set_trap_status,
)
from dnd_board_game.inventory import (
    ArmorCategory,
    BundleEntry,
    CheckModifier,
    CheckModifierMode,
    GearCategory,
    HandSlot,
    InventoryItem,
    ItemChargeRecovery,
    LootBundle,
    LightSource,
    SpellcastingFocusKind,
)
from dnd_board_game.save import (
    SNAPSHOT_SCHEMA_VERSION,
    SessionSnapshot,
    SnapshotValidationError,
    read_snapshot,
)
from dnd_board_game.rules import (
    ActiveEffect,
    EffectDuration,
    EffectSource,
    EffectSourceType,
)
from dnd_board_game.scenarios import build_encounter_from_scenario, load_scenario
from dnd_board_game.ui.exploration_app import ExplorationUiSession, UiFlowStage, create_app
from dnd_board_game.world import Coordinate


def _session(tmp_path) -> ExplorationUiSession:
    return ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="snapshot_test",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
        automatic_checkpoints=True,
    )


def _start_scout_combat(session: ExplorationUiSession) -> None:
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(session.state, flags=set_scene_flag(session.state.flags, "scout_panicked", True))
    session.state_payload()
    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            session.assign_encounter_player_start_position(
                session.encounter_setup_flow.remaining_player_start_positions()[0]
            )
        else:
            session.confirm_encounter_setup_step()
    session.start_encounter_initiative()
    for roll in (20, 19, 18):
        if session.combat_state is None:
            session.submit_encounter_initiative_roll(roll)


def test_snapshot_json_round_trip_is_deterministic(tmp_path):
    session = _session(tmp_path)
    snapshot = session.create_snapshot()

    restored = SessionSnapshot.from_dict(snapshot.as_dict(), base_state=session.state)

    assert restored.as_dict() == snapshot.as_dict()
    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    cleric = next(actor for actor in restored.actors if str(actor.id) == "cleric")
    assert cleric.level == 1
    assert cleric.portrait == "portraits/abandoned_watchtower/cleric.webp"
    shield = next(item for item in cleric.inventory if item.id == "shield")
    assert shield.armor_class_bonus == 2
    assert shield.armor_proficiency == "shield"
    assert len(shield.held_in) == 1
    amulet = next(item for item in cleric.inventory if item.id == "guardian_amulet")
    assert [effect.kind.value for effect in amulet.magic_effects] == [
        "armor_class_bonus",
        "saving_throw_bonus",
    ]
    assert cleric.auras[0].id == "protective_reliquary"
    assert {spell.id for spell in cleric.spells} == {
        "sacred_flame",
        "radiant_line",
        "healing_word",
        "cure_wounds",
        "inflict_wounds",
        "bless_attack_bonus",
        "comprehend_languages",
        "shield",
        "counterspell",
        "warding_rite",
        "call_guardian_spirit",
        "veil_step",
        "repelling_pulse",
        "grasping_current",
        "weakening_miasma",
        "binding_frost",
        "unravel_magic",
    }
    assert cleric.spell_access[0].kind.value == "prepared"
    radiant_line = next(spell for spell in cleric.spells if spell.id == "radiant_line")
    assert radiant_line.scaling is not None
    assert radiant_line.scaling.damage_dice_per_slot_level == 1
    sacred_flame = next(
        spell for spell in cleric.spells if spell.id == "sacred_flame"
    )
    assert sacred_flame.scaling is not None
    assert sacred_flame.scaling.cantrip_damage_dice_per_tier == 1
    bless = next(
        spell for spell in cleric.spells if spell.id == "bless_attack_bonus"
    )
    assert bless.scaling is not None
    assert bless.scaling.targets_per_slot_level == 1
    ritual = next(
        spell for spell in cleric.spells if spell.id == "comprehend_languages"
    )
    assert ritual.exploration_effect is not None
    assert ritual.exploration_effect.flag_key == "comprehend_languages_active"


def test_stable_checkpoint_writes_reloadable_snapshot_and_records_reason(tmp_path):
    session = _session(tmp_path)
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    assert session._write_stable_checkpoint(reason="test_resolution") is True

    restored = read_snapshot(session.snapshot_path, base_state=session.state)
    assert restored.scenario_id == session.exploration.scenario_id
    assert restored.ui_stage == UiFlowStage.LOCATION_ACTIVE.value
    events = [
        json.loads(line)
        for line in session.observer.path.read_text(encoding="utf-8").splitlines()
    ]
    assert any(
        event["event_type"] == "ui_automatic_checkpoint_saved"
        and event["payload"]["reason"] == "test_resolution"
        for event in events
    )


def test_snapshot_round_trip_preserves_active_wild_shape_and_normal_form_hp(tmp_path):
    session = _session(tmp_path)
    actor = session.exploration.actors[0]
    actor = replace(
        actor,
        features=(
            *actor.features,
            FeatureGrant(
                "wild_shape",
                "Wild Shape",
                FeatureSourceKind.CLASS,
                "druid",
            ),
        ),
        resource_pools=(
            *actor.resource_pools,
            ActorResourcePool(
                "wild_shape_uses",
                "Wild Shape",
                2,
                2,
                RecoveryPeriod.SHORT_REST,
            ),
        ),
    )
    shaped = transform_into_wild_shape(actor, "wolf")
    session.exploration = replace(
        session.exploration,
        actors=(
            shaped,
            *session.exploration.actors[1:],
        ),
    )

    snapshot = session.create_snapshot()
    restored = SessionSnapshot.from_dict(snapshot.as_dict(), base_state=session.state)
    restored_actor = restored.actors[0]

    assert restored_actor.wild_shape is not None
    assert restored_actor.wild_shape.form_id == "wolf"
    assert restored_actor.wild_shape.original_hp == actor.hp
    assert restored_actor.hp == 11
    assert restored.as_dict() == snapshot.as_dict()


def test_snapshot_round_trip_preserves_timed_exploration_magic(tmp_path):
    session = _session(tmp_path)
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.cast_exploration_ritual("cleric", "comprehend_languages")
    snapshot = session.create_snapshot()
    fresh_state = _session(tmp_path).state

    restored = SessionSnapshot.from_dict(
        snapshot.as_dict(),
        base_state=fresh_state,
    )

    assert len(restored.exploration_state.magic_effects) == 1
    effect = restored.exploration_state.magic_effects[0]
    assert effect.spell_id == "comprehend_languages"
    assert effect.expires_at_minute == session.state.elapsed_minutes + 60
    assert restored.exploration_state.flags == session.state.flags


def test_snapshot_v14_migrates_with_no_timed_exploration_magic(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 14
    raw["exploration"].pop("magic_effects")

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert restored.exploration_state.magic_effects == ()


def test_snapshot_v15_migrates_with_no_long_casts(tmp_path):
    session = _session(tmp_path)
    _start_scout_combat(session)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 15
    raw["combat"].pop("long_casts")

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert restored.combat_state is not None
    assert restored.combat_state.long_casts == ()


def test_snapshot_v16_migrates_with_no_summoned_creatures(tmp_path):
    session = _session(tmp_path)
    _start_scout_combat(session)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 16
    raw["combat"].pop("summoned_creatures")

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert restored.combat_state is not None
    assert restored.combat_state.summoned_creatures == ()


def test_snapshot_v17_migrates_spell_origin_metadata_defaults(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 17
    raw["exploration"]["condition_states"] = [
        {
            "actor_id": "hero",
            "condition": "poisoned",
            "source_actor_id": None,
            "source_label": "Stary efekt",
            "duration": "permanent",
            "expiration_actor_id": "hero",
            "save_ability": None,
            "save_dc": None,
            "save_timing": None,
        }
    ]
    for effect in raw["active_effects"]:
        effect.pop("spell_level", None)

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    condition = restored.exploration_state.condition_states[0]
    assert condition.source_spell_id is None
    assert condition.source_spell_level is None
    assert all(effect.spell_level is None for effect in restored.active_effects)


def test_snapshot_v18_round_trip_preserves_dispellable_spell_level(tmp_path):
    session = _session(tmp_path)
    effect = ActiveEffect(
        id="spell-effect:test",
        actor_id="hero",
        kind="spell_ac_bonus",
        label="Magiczna osłona",
        object_id="spell:test_ward",
        value=2,
        source_actor_id="hero",
        target_actor_id="hero",
        source=EffectSource(
            EffectSourceType.SPELL,
            "test_ward",
            "Magiczna osłona",
        ),
        duration=EffectDuration.CONCENTRATION,
        spell_level=3,
    )
    session.active_combat_effects = (effect,)

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )

    assert restored.active_effects == (effect,)
    assert restored.active_effects[0].spell_level == 3


def test_snapshot_v19_migrates_actor_senses_and_v20_round_trip_preserves_them(
    tmp_path,
):
    session = _session(tmp_path)
    hero = next(
        actor for actor in session.exploration.actors if str(actor.id) == "hero"
    )
    session.exploration = session._replace_exploration_actor(
        replace(hero, senses=ActorSenseProfile(darkvision_feet=60))
    )

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )
    restored_hero = next(
        actor for actor in restored.actors if str(actor.id) == "hero"
    )
    assert restored_hero.senses.darkvision_feet == 60

    old = session.create_snapshot().as_dict()
    old["schema_version"] = 19
    for actor in old["actors"]:
        actor.pop("senses")
    migrated = SessionSnapshot.from_dict(old, base_state=session.state)
    migrated_hero = next(
        actor for actor in migrated.actors if str(actor.id) == "hero"
    )
    assert migrated_hero.senses == ActorSenseProfile()


def test_snapshot_v20_migrates_empty_exploration_hiding_state(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 20
    raw["exploration"].pop("hidden_actor_states")

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert restored.exploration_state.hidden_actor_states == ()


def test_snapshot_v21_round_trip_preserves_exploration_hiding_state(tmp_path):
    session = _session(tmp_path)
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.start_exploration_hide("rogue")
    session.resolve_rolls({"rogue": 15})

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )

    assert len(restored.exploration_state.hidden_actor_states) == 1
    hidden = restored.exploration_state.hidden_actor_states[0]
    assert hidden.actor_id == "rogue"
    assert hidden.zone_id == "gate"
    assert hidden.natural_roll == 15
    assert hidden.stealth_total == 22


def test_snapshot_v21_migrates_typed_fixture_runtime_fields(tmp_path):
    session = _session(tmp_path)
    plan = plan_fixture_action(
        session.state,
        source_id="zone:gate:fixture:gate_corroded_hinges",
        operation=FixtureOperation.DETACH,
    )
    session.state = apply_fixture_action(
        session.state,
        plan,
        success=True,
    ).state
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 21
    fixture_state = raw["exploration"]["fixture_states"][0]
    fixture_state.pop("opened")
    fixture_state.pop("locked")
    fixture_state.pop("looted")
    fixture_state.pop("current_hit_points")

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    migrated = restored.exploration_state.fixture_states[0]
    assert migrated.opened is False
    assert migrated.locked is False
    assert migrated.looted is False
    assert migrated.current_hit_points is None


def test_snapshot_v22_round_trip_preserves_door_and_container_state(tmp_path):
    session = _session(tmp_path)
    gate_source = "zone:gate:fixture:watchtower_gate"
    unlocked = apply_fixture_action(
        session.state,
        plan_fixture_action(
            session.state,
            source_id=gate_source,
            operation=FixtureOperation.UNLOCK,
        ),
        success=True,
    )
    opened = apply_fixture_action(
        unlocked.state,
        plan_fixture_action(
            unlocked.state,
            source_id=gate_source,
            operation=FixtureOperation.OPEN,
        ),
        success=True,
    )
    session.state = opened.state

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )

    gate = next(
        item
        for item in restored.exploration_state.fixture_states
        if item.fixture_id == "watchtower_gate"
    )
    assert gate.opened is True
    assert gate.locked is False
    assert gate.current_hit_points == 27


def test_snapshot_v22_migrates_actor_exhaustion_to_zero(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 22
    for actor in raw["actors"]:
        actor.pop("exhaustion_level")

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert all(actor.exhaustion_level == 0 for actor in restored.actors)


def test_snapshot_v23_round_trip_preserves_actor_exhaustion(tmp_path):
    session = _session(tmp_path)
    actors = tuple(
        replace(actor, exhaustion_level=3)
        if str(actor.id) == "hero"
        else actor
        for actor in session.exploration.actors
    )
    session.exploration = replace(session.exploration, actors=actors)

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )

    hero = next(actor for actor in restored.actors if str(actor.id) == "hero")
    assert hero.exhaustion_level == 3


def test_snapshot_v24_round_trip_preserves_actor_experience(tmp_path):
    session = _session(tmp_path)
    actors = tuple(
        replace(actor, experience_points=325)
        if str(actor.id) == "hero"
        else actor
        for actor in session.exploration.actors
    )
    session.exploration = replace(session.exploration, actors=actors)

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )

    hero = next(actor for actor in restored.actors if str(actor.id) == "hero")
    assert hero.experience_points == 325


def test_snapshot_v23_migrates_actor_experience_to_zero(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 23
    for actor in raw["actors"]:
        actor.pop("experience_points")
    if raw["combat"] is not None:
        for actor in raw["combat"]["actors"]:
            actor.pop("experience_points")

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert all(actor.experience_points == 0 for actor in restored.actors)


def test_snapshot_save_and_load_restores_dynamic_summoned_actor(tmp_path):
    session = _session(tmp_path)
    _start_scout_combat(session)
    assert session.combat_state is not None
    owner = session.combat_state.actors[0]
    gate = build_encounter_from_scenario(
        load_scenario("content/scenarios/gate_skirmish.json")
    )
    cleric = next(actor for actor in gate.actors if str(actor.id) == "cleric")
    action = next(
        action
        for action in gate.combat_actions_by_actor[cleric.id]
        if action.id == "call_guardian_spirit"
    )
    assert action.summon is not None
    summoned_actor_id = ActorId("summon:test_owner:guardian:1")
    effect_id = "concentration_summon:test"
    summoned = SummonedCreatureState(
        actor_id=summoned_actor_id,
        owner_actor_id=owner.id,
        spell_id=action.id,
        definition=action.summon,
        concentration_effect_id=effect_id,
    )
    actor = summon_actor(
        action.summon,
        actor_id=summoned_actor_id,
        owner=owner,
        position=Coordinate(19, 29),
    )
    session.combat_state = add_summoned_creature(
        session.combat_state,
        summoned,
        actor,
    )

    session.save_snapshot()
    session.combat_state = None
    loaded = session.load_snapshot()

    assert session.combat_state is not None
    assert session.combat_state.summoned_creatures[0].actor_id == summoned_actor_id
    assert any(
        str(actor.id) == summoned_actor_id
        for actor in session.combat_state.actors
    )
    assert loaded["combat"]["summoned_creatures"][0]["actor_id"] == summoned_actor_id


def test_snapshot_round_trip_preserves_long_cast_progress(tmp_path):
    session = _session(tmp_path)
    _start_scout_combat(session)
    assert session.combat_state is not None
    caster = session.combat_state.actors[0]
    cast = LongCastState(
        caster_id=caster.id,
        spell_id="warding_rite",
        label="Rytuał ochronny",
        cast_level=1,
        required_actions=10,
        completed_actions=4,
        started_round=1,
        last_progress_round=4,
    )
    session.combat_state = replace(
        session.combat_state,
        long_casts=(cast,),
    )

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )

    assert restored.combat_state is not None
    assert restored.combat_state.long_casts == (cast,)


def test_snapshot_v1_migrates_through_current_content_contract(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 1
    raw.pop("content")

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    migrated = restored.as_dict()
    assert migrated["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert migrated["content"] == {
        "scenario_schema": "dnd_board_game.scenario",
        "scenario_schema_version": 1,
        "ruleset_id": "dnd_5e_2014",
        "source_pack_ids": ["project_original"],
    }


def test_snapshot_v2_migrates_currency_value_and_weight_defaults(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 2
    for actor in raw["actors"]:
        actor.pop("currency", None)
        for item in actor["inventory"]:
            item.pop("value_cp", None)
            item.pop("weight_lb", None)

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert all(actor.currency.total_coins == 0 for actor in restored.actors)
    assert all(
        item.value_cp == 0 and item.weight_lb == 0
        for actor in restored.actors
        for item in actor.inventory
    )


def test_snapshot_v3_migrates_ammunition_type_default(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 3
    for actor in raw["actors"]:
        for item in actor["inventory"]:
            item.pop("ammunition_type", None)

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert all(
        item.ammunition_type is None
        for actor in restored.actors
        for item in actor.inventory
    )


def test_snapshot_v4_migrates_empty_ammunition_recovery_state(tmp_path):
    session = _session(tmp_path)
    _start_scout_combat(session)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 4
    raw["combat"].pop("ammunition_expenditures")
    raw["combat"].pop("battlefield_loot")

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert restored.combat_state is not None
    assert restored.combat_state.ammunition_expenditures == ()
    assert restored.combat_state.battlefield_loot == ()


def test_snapshot_round_trip_preserves_ammunition_ledger_and_battlefield_loot(tmp_path):
    session = _session(tmp_path)
    _start_scout_combat(session)
    assert session.combat_state is not None
    shooter = session.combat_state.actors[0]
    bolt = InventoryItem(
        "crossbow_bolt",
        "Bełt do kuszy",
        "ammunition",
        quantity=1,
        equipped=False,
        ammunition_type="bolt",
        value_cp=5,
        weight_lb=0.075,
    )
    session.combat_state = replace(
        session.combat_state,
        ammunition_expenditures=(
            AmmunitionExpenditure(
                shooter_actor_id=shooter.id,
                shooter_faction=shooter.faction,
                ammunition_type="bolt",
                item=bolt,
                quantity=5,
            ),
        ),
        battlefield_loot=(
            BattlefieldLoot(
                id="recovered_ammunition",
                position=Coordinate(3, 4),
                bundle=LootBundle(
                    id="battlefield:recovered_ammunition",
                    label="Odzyskana amunicja",
                    items=(replace(bolt, quantity=2),),
                ),
            ),
        ),
    )

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )

    assert restored.combat_state is not None
    assert restored.combat_state.ammunition_expenditures == (
        AmmunitionExpenditure(
            shooter_actor_id=shooter.id,
            shooter_faction=shooter.faction,
            ammunition_type="bolt",
            item=bolt,
            quantity=5,
        ),
    )
    assert restored.combat_state.battlefield_loot[0].position == Coordinate(3, 4)
    assert restored.combat_state.battlefield_loot[0].bundle.items[0].quantity == 2


def test_snapshot_v5_initializes_merchants_from_current_content(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        session_id="merchant_migration",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 5
    raw["exploration"].pop("merchants")

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert restored.exploration_state.merchants[0].id == "mira_market_stall"
    assert restored.exploration_state.merchants[0].inventory[0].quantity == 40


def test_snapshot_v6_migrates_to_current_armor_schema(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 6

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION


def test_snapshot_v7_migrates_to_current_item_charge_schema(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 7
    for actor in raw["actors"]:
        for item in actor["inventory"]:
            item.pop("charges_maximum", None)
            item.pop("charges_current", None)
            item.pop("charges_recovery", None)
            item.pop("charges_recovery_dice", None)
            item.pop("charges_recovery_modifier", None)

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    ordinary_item = restored.actors[0].inventory[0]
    assert ordinary_item.charges_maximum is None
    assert ordinary_item.charges_recovery == ItemChargeRecovery.NEVER


def test_snapshot_v8_migrates_to_current_attunement_schema(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 8
    for actor in raw["actors"]:
        for item in actor["inventory"]:
            item.pop("requires_attunement", None)
            item.pop("attuned", None)

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert all(
        not item.requires_attunement and not item.attuned
        for actor in restored.actors
        for item in actor.inventory
    )


def test_snapshot_v9_migrates_to_current_magic_effect_schema(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 9
    for actor in raw["actors"]:
        for item in actor["inventory"]:
            item.pop("magic_effects", None)

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert all(
        not item.magic_effects
        for actor in restored.actors
        for item in actor.inventory
    )


def test_snapshot_v10_migrates_to_current_weapon_schema(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["schema_version"] = 10
    for actor in raw["actors"]:
        for item in actor["inventory"]:
            item.pop("weapon_category", None)
            item.pop("weapon_properties", None)

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert all(
        item.weapon_category is None and not item.weapon_properties
        for actor in restored.actors
        for item in actor.inventory
    )


def test_snapshot_v11_migrates_and_round_trip_preserves_mundane_gear(tmp_path):
    session = _session(tmp_path)
    actor = session.exploration.actors[0]
    pack = InventoryItem(
        "test_pack",
        "Pakiet testowy",
        "equipment_pack",
        equipped=False,
        gear_category=GearCategory.EQUIPMENT_PACK,
        stackable=False,
        spellcasting_focus_kind=SpellcastingFocusKind.COMPONENT_POUCH,
        container_capacity=None,
        light_source=LightSource(20, 20, 60),
        check_modifiers=(
            CheckModifier(
                "test_advantage",
                "Próba",
                "test_context",
                CheckModifierMode.ADVANTAGE,
            ),
        ),
        bundle_contents=(BundleEntry("torch", 10),),
    )
    actor = replace(actor, inventory=(*actor.inventory, pack))
    from dnd_board_game.inventory import ActiveLight, LightShape
    actor = replace(
        actor,
        active_light=ActiveLight(
            "torch",
            "Pochodnia",
            20,
            20,
            42,
            LightShape.RADIUS,
        ),
    )
    session.exploration = session._replace_exploration_actor(actor)

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )
    restored_pack = next(
        item for item in restored.actors[0].inventory if item.id == "test_pack"
    )

    assert restored_pack.gear_category == GearCategory.EQUIPMENT_PACK
    assert restored_pack.light_source == pack.light_source
    assert restored_pack.check_modifiers == pack.check_modifiers
    assert restored_pack.bundle_contents == pack.bundle_contents
    assert restored.actors[0].active_light == actor.active_light

    old = session.create_snapshot().as_dict()
    old["schema_version"] = 11
    for raw_actor in old["actors"]:
        raw_actor.pop("active_light", None)
        for raw_item in raw_actor["inventory"]:
            for field in (
                "gear_category",
                "stackable",
                "tool_proficiency_id",
                "spellcasting_focus_kind",
                "container_capacity",
                "light_source",
                "check_modifiers",
                "durability",
                "bundle_contents",
            ):
                raw_item.pop(field, None)
    migrated = SessionSnapshot.from_dict(old, base_state=session.state)
    assert migrated.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION


def test_snapshot_round_trip_preserves_item_charge_state(tmp_path):
    session = _session(tmp_path)
    cleric = next(actor for actor in session.exploration.actors if str(actor.id) == "cleric")
    wand = next(item for item in cleric.inventory if item.id == "binding_wand")
    cleric = replace(
        cleric,
        inventory=tuple(
            replace(item, charges_current=3, attuned=True)
            if item.id == wand.id
            else item
            for item in cleric.inventory
        ),
    )
    session.exploration = session._replace_exploration_actor(cleric)

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )
    restored_cleric = next(actor for actor in restored.actors if str(actor.id) == "cleric")
    restored_wand = next(
        item for item in restored_cleric.inventory if item.id == "binding_wand"
    )

    assert restored_wand.quantity == 1
    assert restored_wand.charges_current == 3
    assert restored_wand.charges_maximum == 7
    assert restored_wand.charges_recovery == ItemChargeRecovery.LONG_REST
    assert restored_wand.charges_recovery_dice == "1d6"
    assert restored_wand.charges_recovery_modifier == 1
    assert restored_wand.requires_attunement is True
    assert restored_wand.attuned is True


def test_snapshot_round_trip_preserves_body_armor_rules(tmp_path):
    session = _session(tmp_path)
    actor = session.exploration.actors[0]
    armor = InventoryItem(
        "chain_mail",
        "Kolczuga",
        "armor",
        equipped=True,
        armor_category=ArmorCategory.HEAVY,
        armor_base_ac=16,
        armor_dexterity_cap=0,
        armor_strength_requirement=13,
        stealth_disadvantage=True,
        armor_proficiency="heavy",
        value_cp=7500,
        weight_lb=55,
    )
    actor = replace(actor, inventory=(*actor.inventory, armor))
    session.exploration = session._replace_exploration_actor(actor)

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )
    restored_armor = next(
        item
        for item in restored.actors[0].inventory
        if item.id == "chain_mail"
    )

    assert restored_armor.armor_category == ArmorCategory.HEAVY
    assert restored_armor.armor_base_ac == 16
    assert restored_armor.armor_dexterity_cap == 0
    assert restored_armor.armor_strength_requirement == 13
    assert restored_armor.stealth_disadvantage is True


def test_snapshot_round_trip_preserves_merchant_trade_state(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        session_id="merchant_round_trip",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.select_point("merchant_stall")
    session.buy_merchant_item(
        merchant_id="mira_market_stall",
        actor_id="hero",
        item_id="crossbow_bolt",
        quantity=7,
    )
    base = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        session_id="merchant_base",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=base.state,
    )

    merchant = restored.exploration_state.merchants[0]
    hero = next(actor for actor in restored.actors if str(actor.id) == "hero")
    assert next(item for item in merchant.inventory if item.id == "crossbow_bolt").quantity == 33
    assert merchant.currency.total_cp == 10_035
    assert next(item for item in hero.inventory if item.id == "crossbow_bolt").quantity == 7
    assert hero.currency.total_cp == 965


def test_snapshot_round_trip_preserves_completed_downtime_crafting(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        session_id="downtime_round_trip",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.complete_downtime_crafting(
        actor_id="hero",
        recipe_id="forge_dagger",
    )
    base = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        session_id="downtime_base",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=base.state,
    )

    hero = next(actor for actor in restored.actors if str(actor.id) == "hero")
    assert hero.currency.total_cp == 900
    assert next(item for item in hero.inventory if item.id == "dagger").quantity == 1
    assert restored.exploration_state.elapsed_minutes == 480
    flags = dict(restored.exploration_state.flags.values)
    assert flags.get("watchtower_dusk_arrival") is True
    assert flags.get("watchtower_alerted") is True


def test_snapshot_round_trip_preserves_pending_npc_scene_transition(tmp_path):
    session = _session(tmp_path)
    session.pending_npc_transition = plan_npc_transition(
        session.exploration.npc_transitions,
        transition_id="scout_knife_escalation",
        state=session.state,
        resolved_encounter_trigger_ids=session.resolved_encounter_trigger_ids,
    )

    restored = SessionSnapshot.from_dict(session.create_snapshot().as_dict(), base_state=session.state)

    assert restored.pending_npc_transition is not None
    assert restored.pending_npc_transition.transition_id == "scout_knife_escalation"
    assert restored.pending_npc_transition.variant_id == "danger_nearby"


def test_snapshot_round_trip_preserves_npc_runtime_state(tmp_path):
    session = _session(tmp_path)
    resolution = resolve_npc_runtime_interaction(
        session.state,
        npc_id="wounded_scout",
        intent="medical",
        success=True,
        summary="Zwiadowca został opatrzony.",
        update=NpcStateUpdate(
            attitude=NpcAttitude.FRIENDLY,
            physical_state="Ustabilizowany",
            emotional_state="Wdzięczny",
        ),
        revealed_information_ids=("tower_hint",),
        attempt_id="medical",
    )
    session.state = resolution.state

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=ExplorationUiSession(
            "content/scenarios/abandoned_watchtower.json",
            session_id="snapshot_base",
            observation_dir=tmp_path / "base_observations",
            save_dir=tmp_path / "base_saves",
        ).state,
    )

    npc = npc_runtime_state_for(restored.exploration_state, "wounded_scout")
    assert npc is not None
    assert npc.attitude == NpcAttitude.FRIENDLY
    assert npc.revealed_information_ids == ("tower_hint",)
    assert npc.used_attempt_ids == ("medical",)
    assert npc.relationship_events[0].summary == "Zwiadowca został opatrzony."
    assert npc.relationship_events[0].attempt_id == "medical"


def test_older_snapshot_without_npc_states_uses_content_defaults(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    raw["exploration"].pop("npc_states")

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    npc = npc_runtime_state_for(restored.exploration_state, "wounded_scout")
    assert npc is not None
    assert npc.attitude == NpcAttitude.INDIFFERENT
    assert "przygnieciony" in npc.physical_state


def test_older_npc_event_without_attempt_id_uses_unique_attempt_fallback(tmp_path):
    session = _session(tmp_path)
    resolution = resolve_npc_runtime_interaction(
        session.state,
        npc_id="wounded_scout",
        intent="social",
        success=False,
        summary="Nieudana próba.",
        attempt_id="scout_build_trust",
    )
    session.state = resolution.state
    raw = session.create_snapshot().as_dict()
    raw["exploration"]["npc_states"][0]["relationship_events"][0].pop("attempt_id")

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)
    plan = plan_npc_attempt(
        restored.exploration_state,
        npc_id="wounded_scout",
        policy=NpcAttemptPolicy(attempt_id="scout_build_trust", max_attempts=2),
    )

    assert plan.attempts_used == 1


def test_snapshot_round_trip_preserves_exploration_condition(tmp_path):
    session = _session(tmp_path)
    session.state = add_exploration_condition(
        session.state,
        "hero",
        CombatCondition.PRONE,
    )

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )

    assert restored.exploration_state.condition_states == (
        ConditionState("hero", CombatCondition.PRONE),
    )


def test_snapshot_round_trip_preserves_exploration_trap_state(tmp_path):
    session = _session(tmp_path)
    session.state = set_trap_status(
        session.state,
        "gate_alarm_wire",
        ExplorationTrapStatus.REVEALED,
    )

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )

    assert restored.exploration_state.trap_states == session.state.trap_states


def test_older_snapshot_without_actor_size_defaults_to_medium(tmp_path):
    session = _session(tmp_path)
    raw = session.create_snapshot().as_dict()
    for actor in raw["actors"]:
        actor.pop("size", None)
        actor.pop("damage_affinities", None)
        actor.pop("auras", None)
        actor.pop("triggers", None)

    restored = SessionSnapshot.from_dict(raw, base_state=session.state)

    assert all(actor.size == CreatureSize.MEDIUM for actor in restored.actors)
    assert all(actor.damage_affinities == DamageAffinityProfile() for actor in restored.actors)
    assert all(actor.auras == () for actor in restored.actors)
    assert all(actor.triggers == () for actor in restored.actors)


def test_snapshot_round_trip_preserves_skill_profile_and_combat_hidden_state(tmp_path):
    session = _session(tmp_path)
    _start_scout_combat(session)
    assert session.combat_state is not None
    hero = next(actor for actor in session.combat_state.actors if str(actor.id) == "hero")
    session.combat_state = replace_actor(
        session.combat_state,
        replace(
            hero,
            size=CreatureSize.LARGE,
            damage_affinities=DamageAffinityProfile(
                resistances=(DamageType.FIRE,),
                immunities=(DamageType.POISON,),
                vulnerabilities=(DamageType.COLD,),
            ),
            attacks_per_action=2,
            condition_immunities=("poisoned",),
            triggers=(
                ActorTrigger(
                    "snapshot_trigger",
                    "Osłona snapshotu",
                    TriggerEventType.TURN_START,
                    TriggerEffectKind.GRANT_TEMP_HP,
                    2,
                ),
            ),
            proficiency_bonus=3,
            proficiencies=ProficiencyProfile(
                saving_throws=("dexterity",),
                skills=("stealth",),
                expertise=("stealth",),
                weapons=("longsword",),
                tools=("thieves_tools",),
            ),
        ),
    )
    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            two_weapon_trigger_item_id="longsword",
            attack_action_active=True,
            attacks_used=1,
            attacks_maximum=2,
        ),
        hidden_states=(HiddenState("hero", 21, ("goblin_a", "goblin_b")),),
        condition_states=(
            ConditionState(
                "hero",
                CombatCondition.POISONED,
                source_actor_id="goblin_a",
                source_label="Trucizna testowa",
                save_ability="constitution",
                save_dc=12,
                save_timing=ConditionSaveTiming.TURN_END,
                source_spell_id="enemy_miasma",
                source_spell_level=3,
            ),
            ConditionState("goblin_a", CombatCondition.GRAPPLED, "hero"),
        ),
    )

    restored = SessionSnapshot.from_dict(session.create_snapshot().as_dict(), base_state=session.state)

    assert restored.combat_state is not None
    restored_hero = next(actor for actor in restored.combat_state.actors if str(actor.id) == "hero")
    assert restored_hero.proficiency_bonus == 3
    assert restored_hero.attacks_per_action == 2
    assert restored_hero.condition_immunities == ("poisoned",)
    assert restored_hero.triggers[0].id == "snapshot_trigger"
    restored_goblin = next(
        actor for actor in restored.combat_state.actors if str(actor.id) == "goblin_a"
    )
    assert restored_goblin.resource_pools[0].recharge is not None
    assert restored_goblin.resource_pools[0].recharge.minimum_roll == 5
    assert restored_goblin.features[0].feature_id == "goblin_frenzied_lunge"
    assert restored_goblin.features[0].resource_ids == ("frenzied_lunge_charge",)
    assert restored_goblin.currency.sp == 5
    assert next(item for item in restored_goblin.inventory if item.id == "poison_vial").weight_lb == 0.5
    assert restored_hero.size == CreatureSize.LARGE
    assert restored_hero.damage_affinities == DamageAffinityProfile(
        resistances=(DamageType.FIRE,),
        immunities=(DamageType.POISON,),
        vulnerabilities=(DamageType.COLD,),
    )
    assert restored_hero.skill_expertise == ("stealth",)
    assert restored_hero.proficiencies.saving_throws == ("dexterity",)
    assert restored_hero.proficiencies.weapons == ("longsword",)
    assert restored_hero.proficiencies.tools == ("thieves_tools",)
    restored_longsword = next(item for item in restored_hero.inventory if item.id == "longsword")
    assert restored_longsword.hands_required == 1
    assert restored_longsword.held_in == (HandSlot.MAIN_HAND,)
    restored_rogue = next(
        actor for actor in restored.combat_state.actors if str(actor.id) == "rogue"
    )
    restored_bolts = next(
        item for item in restored_rogue.inventory if item.id == "crossbow_bolt"
    )
    assert restored_bolts.ammunition_type == "bolt"
    assert restored_bolts.quantity == 20
    assert restored.combat_state.turn_action.two_weapon_trigger_item_id == "longsword"
    assert restored.combat_state.turn_action.attack_action_active is True
    assert restored.combat_state.turn_action.attacks_used == 1
    assert restored.combat_state.turn_action.attacks_maximum == 2
    assert restored.combat_state.hidden_states == (
        HiddenState("hero", 21, ("goblin_a", "goblin_b")),
    )
    assert restored.combat_state.condition_states == (
        ConditionState(
            "hero",
            CombatCondition.POISONED,
            source_actor_id="goblin_a",
            source_label="Trucizna testowa",
            save_ability="constitution",
            save_dc=12,
            save_timing=ConditionSaveTiming.TURN_END,
            source_spell_id="enemy_miasma",
            source_spell_level=3,
        ),
        ConditionState("goblin_a", CombatCondition.GRAPPLED, "hero"),
    )


def test_snapshot_round_trip_preserves_temporary_scene_item(tmp_path):
    session = _session(tmp_path)
    draft = CraftingDraft(
        label="Prowizoryczny taran",
        description="Długa deska obciążona kamieniem.",
        purpose_id="heavy_force",
        components=(
            CraftingComponentSelection("zone:gate:item:gate_rotten_planks"),
            CraftingComponentSelection("zone:gate:item:gate_loose_stones"),
        ),
    )
    session.state, created = craft_temporary_item(
        session.state,
        draft,
        build_crafting_source_registry(session.state, session.exploration.actors),
        session.exploration.crafting_policy,
    )

    restored = SessionSnapshot.from_dict(session.create_snapshot().as_dict(), base_state=session.state)

    assert restored.exploration_state.temporary_items == (created,)


def test_snapshot_round_trip_preserves_unconsumed_encounter_edge(tmp_path):
    session = _session(tmp_path)
    edge = EncounterEdge(
        id="observation:gate:fact:positions:actor:hero",
        edge_type=EncounterEdgeType.INITIATIVE_ADVANTAGE,
        label="Rozpoznane pozycje goblinów",
        beneficiary_actor_id="hero",
        encounter_trigger_id="gate_open_skirmish",
        source_observation_id="gate",
        source_fact_id="positions",
    )
    session.state = replace(session.state, encounter_edges=(edge,))

    restored = SessionSnapshot.from_dict(session.create_snapshot().as_dict(), base_state=session.state)

    assert restored.exploration_state.encounter_edges == (edge,)


def test_snapshot_round_trip_preserves_encounter_opening_resolution(tmp_path):
    session = _session(tmp_path)
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    flags = set_scene_flag(session.state.flags, "gate_passed", True)
    flags = set_scene_flag(flags, "gate_lock_critical", True)
    flags = set_scene_flag(flags, "gate_bolt_critical", True)
    session.state = replace(session.state, flags=flags)
    session.state_payload()
    session.resolve_encounter_opening()
    assert session.pending_encounter is not None
    session.pending_encounter = replace(
        session.pending_encounter,
        precombat_stealth_completed=True,
        precombat_stealth_attempts=(
            PrecombatStealthAttempt(
                "rogue",
                15,
                20,
                ("goblin_a", "goblin_b"),
                (),
            ),
        ),
    )

    restored = SessionSnapshot.from_dict(session.create_snapshot().as_dict(), base_state=session.state)

    assert restored.pending_encounter is not None
    assert restored.pending_encounter.opening_resolution is not None
    assert restored.pending_encounter.opening_resolution.outcome.value == "party_can_hide"
    assert restored.pending_encounter.precombat_stealth_completed is True
    assert restored.pending_encounter.precombat_stealth_attempts[0].total == 20


def test_snapshot_round_trip_preserves_found_scene_source_without_inventory_transfer(tmp_path):
    session = _session(tmp_path)
    source = build_crafting_source_registry(session.state, session.exploration.actors).source_by_id(
        "zone:gate:item:gate_rotten_planks"
    )
    assert source is not None
    session.state = discover_scene_source(
        session.state,
        source,
        requested_as="kij",
        purpose="dosięgnięcie rygla",
        matched_properties=("long", "rigid"),
        semantic_substitution=True,
    )
    inventory_before = session.state.inventory_resource_ids

    restored = SessionSnapshot.from_dict(session.create_snapshot().as_dict(), base_state=session.state)

    assert restored.exploration_state.source_discoveries == session.state.source_discoveries
    assert restored.exploration_state.inventory_resource_ids == inventory_before


def test_snapshot_round_trip_preserves_collected_scene_quantity_and_owner_inventory(tmp_path):
    session = _session(tmp_path)
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("/wez drewnianą deskę")
    session.decide("accept", lead_actor_id="hero", quantity=2)

    restored = SessionSnapshot.from_dict(session.create_snapshot().as_dict(), base_state=session.state)

    assert restored.exploration_state.source_collections == session.state.source_collections
    hero = next(actor for actor in restored.actors if str(actor.id) == "hero")
    assert next(item for item in hero.inventory if item.name == "Drewniana deska").quantity == 2
    remaining = build_crafting_source_registry(restored.exploration_state, restored.actors).source_by_id(
        "zone:gate:item:gate_rotten_planks"
    )
    assert remaining is not None and remaining.quantity == 2


def test_snapshot_round_trip_preserves_fixture_state_and_released_items(tmp_path):
    session = _session(tmp_path)
    plan = plan_fixture_action(
        session.state,
        source_id="zone:gate:fixture:gate_corroded_hinges",
        operation=FixtureOperation.DETACH,
    )
    session.state = apply_fixture_action(session.state, plan, success=True).state

    restored = SessionSnapshot.from_dict(session.create_snapshot().as_dict(), base_state=session.state)

    assert restored.exploration_state.fixture_states == session.state.fixture_states
    registry = build_crafting_source_registry(restored.exploration_state, restored.actors)
    assert registry.source_by_id("zone:gate:fixture:gate_corroded_hinges").usable is False
    assert registry.source_by_id("zone:gate:item:detached_gate_metal").usable is True


def test_snapshot_round_trip_preserves_dynamic_crafting_allocations(tmp_path):
    session = _session(tmp_path)
    draft = CraftingDraft(
        label="Prowizoryczna drabina",
        description="Dwie deski związane liną.",
        purpose_id="climbing_aid",
        components=(
            CraftingComponentSelection("zone:gate:item:gate_rotten_planks", quantity=2),
            CraftingComponentSelection("resource:rope"),
        ),
    )
    session.state, created = craft_temporary_item(
        session.state,
        draft,
        build_crafting_source_registry(session.state, session.exploration.actors),
        session.exploration.crafting_policy,
    )

    restored = SessionSnapshot.from_dict(session.create_snapshot().as_dict(), base_state=session.state)

    assert restored.exploration_state.temporary_items == (created,)


def test_session_save_and_load_restores_exploration_state(tmp_path):
    session = _session(tmp_path)
    actor_before = session.exploration.actors[0]
    changed_actor = replace(actor_before, hp=actor_before.hp - 3, temp_hp=2)
    session.exploration = replace(session.exploration, actors=(changed_actor, *session.exploration.actors[1:]))
    session.state = replace(
        session.state,
        flags=set_scene_flag(session.state.flags, "snapshot_flag", True),
        elapsed_minutes=75,
    )
    expected = session.create_snapshot().as_dict()
    session.save_snapshot()

    session.exploration = replace(
        session.exploration,
        actors=(replace(changed_actor, hp=1, temp_hp=0), *session.exploration.actors[1:]),
    )
    session.state = replace(session.state, elapsed_minutes=999)
    session.load_snapshot()

    assert session.create_snapshot().as_dict() == expected
    assert session.exploration.actors[0].hp == changed_actor.hp
    assert session.state.elapsed_minutes == 75
    assert session.snapshot_path.exists()


def test_snapshot_round_trip_preserves_selected_exploration_point_position(tmp_path):
    session = _session(tmp_path)
    session.state = replace(
        session.state,
        points=tuple(
            replace(point, positions=(Coordinate(9, 9),))
            if point.id == "wounded_scout"
            else point
            for point in session.state.points
        ),
        flags=set_scene_flag(
            session.state.flags,
            "exploration_point_placed_wounded_scout",
            True,
        ),
    )

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=replace(session.state, points=session.exploration.points),
    )

    scout = next(
        point
        for point in restored.exploration_state.points
        if point.id == "wounded_scout"
    )
    assert scout.positions == (Coordinate(9, 9),)


def test_session_save_and_load_restores_active_combat(tmp_path):
    session = _session(tmp_path)
    _start_scout_combat(session)
    assert session.combat_state is not None
    active = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(session.combat_state, replace(active, hp=active.hp - 1))
    expected = session.create_snapshot().as_dict()
    session.save_snapshot()

    session.combat_state = None
    session.encounter_initiative_flow = None
    session.load_snapshot()

    assert session.combat_state is not None
    assert session.encounter_initiative_flow is not None
    assert session._active_encounter() is not None
    assert session.create_snapshot().as_dict() == expected


def test_snapshot_round_trip_preserves_death_save_state(tmp_path):
    session = _session(tmp_path)
    _start_scout_combat(session)
    assert session.combat_state is not None
    active = session.combat_state.initiative_order.current_actor
    dying = replace(
        active,
        hp=0,
        uses_death_saves=True,
        death_saves=DeathSaveState(successes=1, failures=2),
    )
    session.combat_state = replace_actor(session.combat_state, dying)

    restored = SessionSnapshot.from_dict(session.create_snapshot().as_dict(), base_state=session.state)
    restored_actor = next(actor for actor in restored.combat_state.actors if actor.id == active.id)

    assert restored_actor.uses_death_saves is True
    assert restored_actor.death_saves == DeathSaveState(successes=1, failures=2)


def test_snapshot_round_trip_preserves_dropped_weapon(tmp_path):
    session = _session(tmp_path)
    _start_scout_combat(session)
    assert session.combat_state is not None
    armed = next(actor for actor in session.combat_state.actors if actor.inventory)
    session.combat_state = replace_actor(session.combat_state, replace(armed, hp=0, uses_death_saves=True))

    restored = SessionSnapshot.from_dict(session.create_snapshot().as_dict(), base_state=session.state)

    assert restored.combat_state is not None
    assert len(restored.combat_state.dropped_weapons) == 1
    dropped = restored.combat_state.dropped_weapons[0]
    assert dropped.source_actor_id == armed.id
    assert dropped.weapon.equipped is False
    assert dropped.position == armed.position


def test_snapshot_round_trip_preserves_enemy_ai_morale_memory_and_outcomes(tmp_path):
    session = _session(tmp_path)
    _start_scout_combat(session)
    assert session.combat_state is not None
    session.combat_state = replace(
        session.combat_state,
        enemy_ai=EnemyAiRuntimeState(
            profile_id="hungry_shadow_pack",
            encounter_seed=13,
            starting_morale=3,
            morale=1,
            used_morale_events=("leader_bloodied",),
            previous_targets=(("shadow_1", "hero"),),
            decision_counts=(("shadow_1", 2),),
            outcomes=(EnemyOutcome("shadow_2", "Głodny cień", "escaped", 2),),
        ),
    )

    restored = SessionSnapshot.from_dict(
        session.create_snapshot().as_dict(),
        base_state=session.state,
    )

    assert restored.combat_state is not None
    assert restored.combat_state.enemy_ai == session.combat_state.enemy_ai


def test_snapshot_rejects_unknown_version(tmp_path):
    session = _session(tmp_path)
    session.save_snapshot()
    payload = json.loads(session.snapshot_path.read_text(encoding="utf-8"))
    payload["schema_version"] = SNAPSHOT_SCHEMA_VERSION + 1
    session.snapshot_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SnapshotValidationError, match="Nieobsługiwana wersja"):
        read_snapshot(session.snapshot_path, base_state=session.state)


def test_snapshot_is_blocked_during_transient_player_choice(tmp_path):
    session = _session(tmp_path)
    session.pending_state.player_attack = object()

    with pytest.raises(ValueError, match="dokończ albo anuluj"):
        session.create_snapshot()

    assert session.state_payload()["snapshot"]["can_save"] is False


def test_snapshot_routes_save_and_restore_state(tmp_path):
    session = _session(tmp_path)
    client = create_app(session).test_client()

    saved = client.post("/api/snapshot/save", json={})
    session.state = replace(session.state, elapsed_minutes=120)
    loaded = client.post("/api/snapshot/load", json={})

    assert saved.status_code == 200
    assert saved.get_json()["snapshot"]["exists"] is True
    assert loaded.status_code == 200
    assert session.state.elapsed_minutes == 0


def test_load_rejects_pending_encounter_path_not_owned_by_scenario(tmp_path):
    session = _session(tmp_path)
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(session.state, flags=set_scene_flag(session.state.flags, "scout_panicked", True))
    session.state_payload()
    session.save_snapshot()
    before = session.create_snapshot().as_dict()
    payload = json.loads(session.snapshot_path.read_text(encoding="utf-8"))
    payload["pending_encounter"]["encounter_scenario"] = "../../outside.json"
    session.snapshot_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="nie odpowiada"):
        session.load_snapshot()

    assert session.create_snapshot().as_dict() == before

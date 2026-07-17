import json
from dataclasses import replace

import pytest

from dnd_board_game.actors import (
    ActorTrigger,
    CreatureSize,
    DamageAffinityProfile,
    DeathSaveState,
    ProficiencyProfile,
    TriggerEffectKind,
    TriggerEventType,
)
from dnd_board_game.combat import (
    CombatCondition,
    ConditionSaveTiming,
    ConditionState,
    HiddenState,
    DamageType,
    replace_actor,
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
from dnd_board_game.inventory import HandSlot
from dnd_board_game.save import (
    SNAPSHOT_SCHEMA_VERSION,
    SessionSnapshot,
    SnapshotValidationError,
    read_snapshot,
)
from dnd_board_game.ui.exploration_app import ExplorationUiSession, UiFlowStage, create_app


def _session(tmp_path) -> ExplorationUiSession:
    return ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="snapshot_test",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
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
    shield = next(item for item in cleric.inventory if item.id == "shield")
    assert shield.armor_class_bonus == 2
    assert shield.armor_proficiency == "shield"
    assert len(shield.held_in) == 1
    assert cleric.auras[0].id == "protective_reliquary"


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
                source_label="Trucizna testowa",
                save_ability="constitution",
                save_dc=12,
                save_timing=ConditionSaveTiming.TURN_END,
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
            source_label="Trucizna testowa",
            save_ability="constitution",
            save_dc=12,
            save_timing=ConditionSaveTiming.TURN_END,
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
    session.state = replace(
        session.state,
        flags=set_scene_flag(session.state.flags, "gate_passed", True),
    )
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
    assert restored.pending_encounter.opening_resolution.outcome.value == "party_surprises_enemies"
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

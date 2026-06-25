from __future__ import annotations

import argparse
import random
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.combat import (
    ActionUse,
    AttackSource,
    AttackSourceType,
    CombatState,
    CombatStatus,
    DamageComponentInput,
    DamageType,
    InitiativeEntry,
    InitiativeOrder,
    active_actor_led_feedback,
    apply_damage,
    attack_declaration_from_state,
    attack_result_led_feedback,
    attack_targets_led_feedback,
    current_actor,
    finish_turn,
    replace_actor,
    resolve_attack,
    resolve_damage,
    resolve_enemy_auto_attack,
    select_attack_target,
    selected_attack_target_led_feedback,
    start_attack_action,
    start_combat,
    stop_combat,
    use_turn_action,
)
from dnd_board_game.hardware import BoardLedAdapter
from dnd_board_game.rules import D20RollInput, D20RollRequest, RollModifier, RollModifierType, resolve_d20_roll, roll_instruction

from .demo_mini_combat import (
    ConnectionFactory,
    _attack_result_message,
    _create_adapter,
    _pause_for_led_step,
    _read_int_or_default,
    _select_target,
    build_demo_combatants,
)
from .session_observer import SessionObserver


@dataclass(frozen=True, slots=True)
class DemoMiniCombatLoopResult:
    messages: tuple[str, ...]
    final_state: CombatState
    observation_path: Path
    feedback_events: int


def run_demo(
    args: argparse.Namespace,
    *,
    connection_factory: ConnectionFactory | None = None,
) -> DemoMiniCombatLoopResult:
    observer = SessionObserver(args.session_id, Path(args.observation_dir))
    observer.record("session_started", {"runtime": "demo_mini_combat_loop"})
    observer.record(
        "board_backend_selected",
        {"backend": args.board_backend, "board_url": args.board_url, "show_leds": args.show_leds},
    )
    adapter = _create_adapter(args, connection_factory) if args.show_leds and args.board_backend != "none" else None
    board, hero, goblin, hero_source = build_demo_combatants()
    enemy_source = _enemy_attack_source()
    state = start_combat((hero, goblin), _fixed_demo_initiative(hero, goblin))
    rng = random.Random(args.enemy_seed)
    messages: list[str] = []
    feedback_events = 0

    while state.status == CombatStatus.ACTIVE:
        if state.round_number > args.max_rounds:
            state = stop_combat(state)
            message = f"Demo zatrzymane po limicie rund: {args.max_rounds}."
            print(message)
            messages.append(message)
            observer.record("combat_stopped", {"reason": "max_rounds", "max_rounds": args.max_rounds})
            break

        actor = current_actor(state)
        turn_message = f"Runda {state.round_number}. Tura: {actor.name}."
        print(turn_message)
        messages.append(turn_message)
        observer.record("turn_started", {"actor_id": str(actor.id), "round_number": state.round_number})
        if adapter is not None:
            adapter.show_feedback(active_actor_led_feedback(state.initiative_order))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "active_actor", "actor_id": str(actor.id)})
            _pause_for_led_step(
                args,
                "To tylko wskazanie aktywnego aktora. Nie klikaj planszy; naciśnij Enter w terminalu.",
            )
            adapter.clear()

        if actor.faction == Faction.ALLY:
            state, turn_messages, sent = _run_hero_turn(args, board, state, actor, hero_source, adapter, observer)
        else:
            state, turn_messages, sent = _run_enemy_turn(board, state, actor, enemy_source, rng, adapter, observer, args)
        messages.extend(turn_messages)
        feedback_events += sent

        if state.status == CombatStatus.FINISHED:
            break

        observer.record("turn_finished", {"actor_id": str(actor.id), "round_number": state.round_number})
        state = finish_turn(state)

    if state.status == CombatStatus.FINISHED:
        message = _combat_finished_message(state)
        print(message)
        messages.append(message)
        observer.record("combat_finished", {"winner": state.winner.value if state.winner else None})

    observer.record("session_finished", {"observation_path": str(observer.path)})
    return DemoMiniCombatLoopResult(tuple(messages), state, observer.path, feedback_events)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run debug mini combat loop.")
    parser.add_argument("--board-backend", choices=("none", "simulator", "hardware"), default="none")
    parser.add_argument("--board-url", default="http://127.0.0.1:5000")
    parser.add_argument("--board-serial-port", default=None)
    parser.add_argument("--wled-url", default=None)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--observation-dir", default="data/session_observations")
    parser.add_argument("--show-leds", dest="show_leds", action="store_true", default=False)
    parser.add_argument("--no-show-leds", dest="show_leds", action="store_false")
    parser.add_argument("--wait-for-enter", action="store_true", default=False)
    parser.add_argument("--step-delay", type=float, default=1.5)
    parser.add_argument("--target-id", default="goblin")
    parser.add_argument("--target-position", default=None)
    parser.add_argument("--scan-timeout", type=float, default=30.0)
    parser.add_argument("--hero-attack-roll", type=int, default=14)
    parser.add_argument("--hero-damage", type=int, default=6)
    parser.add_argument("--hero-damage-type", choices=[item.value for item in DamageType], default=DamageType.SLASHING.value)
    parser.add_argument("--enemy-seed", type=int, default=7)
    parser.add_argument("--max-rounds", type=int, default=3)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.session_id is None:
        args.session_id = f"demo_mini_combat_loop_{uuid.uuid4().hex[:8]}"
    try:
        run_demo(args)
    except Exception as exc:
        print(f"demo_mini_combat_loop failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _run_hero_turn(
    args: argparse.Namespace,
    board,
    state: CombatState,
    actor: Actor,
    source: AttackSource,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
) -> tuple[CombatState, tuple[str, ...], int]:
    messages: list[str] = []
    feedback_events = 0
    action_message = f"{actor.name} wybiera akcję: Atak."
    print(action_message)
    messages.append(action_message)
    attack_state = start_attack_action(board, actor, state.actors, source)
    if not attack_state.legal_targets:
        message = "Brak legalnych celów ataku. Tura kończy się bez ataku."
        print(message)
        messages.append(message)
        observer.record("attack_rejected", {"reason": "no_legal_targets", "attacker_id": str(actor.id)})
        return use_turn_action(state).state, tuple(messages), feedback_events

    target_message = "Wybierz cel ataku. Legalne cele: " + ", ".join(target.name for target in attack_state.legal_targets) + "."
    print(target_message)
    messages.append(target_message)
    if adapter is not None:
        adapter.show_feedback(attack_targets_led_feedback(attack_state.legal_targets))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "legal_attack_targets"})

    attack_state = _select_target(args, attack_state, adapter, observer)
    if adapter is not None:
        adapter.clear()
    declaration = attack_declaration_from_state(attack_state)
    observer.record(
        "attack_declared",
        {"attacker_id": str(actor.id), "target_id": declaration.target.id, "source": declaration.source.name},
    )

    instruction = roll_instruction(source.attack_roll_request)
    roll_message = f"Atakujesz {declaration.target.name} za pomocą {source.name}. {instruction.message}"
    print(roll_message)
    messages.append(roll_message)
    if adapter is not None:
        adapter.show_feedback(selected_attack_target_led_feedback(declaration.target))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "selected_attack_target", "target_id": declaration.target.id})
    natural_attack_roll = _read_int_or_default(
        args,
        f"Wpisz naturalny wynik ataku d20 albo naciśnij Enter dla wartości z CLI ({args.hero_attack_roll}): ",
        args.hero_attack_roll,
    )
    if adapter is not None:
        adapter.clear()

    attack_roll = resolve_d20_roll(D20RollInput(source.attack_roll_request, natural_attack_roll))
    resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
    action_result = use_turn_action(state)
    state = action_result.state
    observer.record("action_used", {"actor_id": str(actor.id), "action": "attack", "accepted": action_result.accepted})
    result_message = _attack_result_message(resolution.outcome.value, declaration.target.name, attack_roll.total)
    print(result_message)
    messages.append(result_message)
    observer.record(
        "attack_resolved",
        {
            "attacker_id": str(actor.id),
            "target_id": declaration.target.id,
            "natural_roll": attack_roll.natural_roll,
            "modifier_total": attack_roll.breakdown.modifier_total,
            "total": attack_roll.total,
            "outcome": resolution.outcome.value,
            "hit": resolution.hit,
        },
    )
    if adapter is not None:
        adapter.show_feedback(attack_result_led_feedback(declaration.target, resolution.outcome))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "attack_result", "outcome": resolution.outcome.value})
        _pause_for_led_step(args, "Naciśnij Enter po wyniku ataku.")
        adapter.clear()

    if resolution.hit:
        damage = resolve_damage((DamageComponentInput(args.hero_damage, DamageType(args.hero_damage_type), source.name),))
        target_actor = _actor_by_string_id(state, declaration.target.id)
        updated_target = apply_damage(target_actor, damage)
        state = replace_actor(state, updated_target)
        damage_message = (
            f"Obrażenia: {damage.total_applied} {args.hero_damage_type}. "
            f"{target_actor.name}: HP {target_actor.hp} -> {updated_target.hp}."
        )
        print(damage_message)
        messages.append(damage_message)
        _record_damage(observer, target_actor, updated_target, damage)

    return state, tuple(messages), feedback_events


def _run_enemy_turn(
    board,
    state: CombatState,
    actor: Actor,
    source: AttackSource,
    rng: random.Random,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    args: argparse.Namespace,
) -> tuple[CombatState, tuple[str, ...], int]:
    result = resolve_enemy_auto_attack(board, state, actor, source, rng)
    observer.record("enemy_action_selected", {"actor_id": str(actor.id), "action": "attack", "target_id": result.target.id if result.target else None})
    observer.record("action_used", {"actor_id": str(actor.id), "action": "attack", "accepted": result.action_used})
    messages: list[str] = []
    feedback_events = 0

    if result.target is not None:
        target_message = f"{actor.name} wybiera cel: {result.target.name}."
        print(target_message)
        messages.append(target_message)
        if adapter is not None:
            adapter.show_feedback(selected_attack_target_led_feedback(result.target))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "enemy_selected_attack_target", "target_id": result.target.id})
            _pause_for_led_step(args, "Naciśnij Enter po celu przeciwnika.")
            adapter.clear()

    print(result.message)
    messages.append(result.message)

    if result.attack_roll is not None and result.attack_resolution is not None:
        observer.record(
            "attack_resolved",
            {
                "attacker_id": str(actor.id),
                "target_id": result.target.id if result.target else None,
                "natural_roll": result.attack_roll.natural_roll,
                "modifier_total": result.attack_roll.breakdown.modifier_total,
                "total": result.attack_roll.total,
                "outcome": result.attack_resolution.outcome.value,
                "hit": result.attack_resolution.hit,
            },
        )
        if adapter is not None and result.target is not None:
            adapter.show_feedback(attack_result_led_feedback(result.target, result.attack_resolution.outcome))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "enemy_attack_result", "outcome": result.attack_resolution.outcome.value})
            _pause_for_led_step(args, "Naciśnij Enter po wyniku ataku przeciwnika.")
            adapter.clear()

    if result.damage is not None and result.updated_target is not None:
        previous_target = _actor_by_string_id(state, result.target.id)
        _record_damage(observer, previous_target, result.updated_target, result.damage)

    return result.state, tuple(messages), feedback_events


def _fixed_demo_initiative(hero: Actor, goblin: Actor) -> InitiativeOrder:
    empty_request = D20RollRequest()
    hero_roll = resolve_d20_roll(D20RollInput(empty_request, 20))
    goblin_roll = resolve_d20_roll(D20RollInput(empty_request, 10))
    return InitiativeOrder(
        (
            InitiativeEntry(hero, hero_roll, 2, 0),
            InitiativeEntry(goblin, goblin_roll, 2, 1),
        )
    )


def _enemy_attack_source() -> AttackSource:
    return AttackSource(
        name="Szabla",
        source_type=AttackSourceType.WEAPON,
        range_feet=5,
        attack_roll_request=D20RollRequest(
            modifiers=(RollModifier("Premia ataku goblina", 4, RollModifierType.CUSTOM, stacking_key="goblin_attack"),)
        ),
        damage_hint="1d6 + 2 slashing",
    )


def _actor_by_string_id(state: CombatState, actor_id: str) -> Actor:
    for actor in state.actors:
        if str(actor.id) == actor_id:
            return actor
    raise ValueError(f"Unknown actor: {actor_id}.")


def _record_damage(observer: SessionObserver, before: Actor, after: Actor, damage) -> None:
    observer.record(
        "damage_applied",
        {
            "target_id": str(before.id),
            "components": [
                {"amount": component.amount, "damage_type": component.damage_type.value, "label": component.label}
                for component in damage.components
            ],
            "total_applied": damage.total_applied,
            "hp_before": before.hp,
            "hp_after": after.hp,
            "temp_hp_before": before.temp_hp,
            "temp_hp_after": after.temp_hp,
        },
    )


def _combat_finished_message(state: CombatState) -> str:
    if state.winner == Faction.ALLY:
        return "Walka zakończona. Zwyciężają bohaterowie."
    if state.winner == Faction.ENEMY:
        return "Walka zakończona. Zwyciężają przeciwnicy."
    return "Walka zakończona."


if __name__ == "__main__":
    raise SystemExit(main())

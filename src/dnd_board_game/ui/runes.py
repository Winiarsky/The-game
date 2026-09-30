"""Board-facing opening allocation and rune-card presentation."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING

from dnd_board_game.rules.runes import RESOURCE_RUNES, take_rune, undo_rune, confirm_allocation
from dnd_board_game.rules.shared_mana import sync_runes
from dnd_board_game.scenarios.rune_catalog import rune_card
from .board_panel_symbols import rune_slot

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession, BoardScanTarget
    from .shared_mana import ManaDeclaration
    from dnd_board_game.rules.shared_mana import SharedMana
    from dnd_board_game.world import Coordinate

RUNE_SLOTS = {rune: rune_slot(rune) for rune in RESOURCE_RUNES}


def view(session: ExplorationUiSession) -> dict[str, object] | None:
    state = session.combat_state
    if state is None or state.shared_mana is None or state.shared_mana.runes is None:
        return None
    from .rune_baskets import active
    if active(session):
        from .rune_baskets import view as basket_view
        return basket_view(session)
    from .board_panel_symbols import panel_icon
    pool = state.shared_mana.runes
    actors = {str(a.id): a for a in state.actors}
    choices = []
    if pool.phase == "allocation":
        choices = [dict(slot=RUNE_SLOTS[r], rune=r, label=f"{r} ×{n}", command="rune_take", count=n)
                   for r, n in Counter(pool.offer).items() if len(pool.hand(pool.actor)) < 7]
        if pool.picks:
            choices.append(dict(slot=29, command="rune_undo", label="Cofnij ostatnią runę"))
        choices.append(dict(slot=28, command="rune_confirm", label="Zatwierdź przydział"))
    upkeep = state.shared_mana.rune_upkeep_actor
    upkeep_rune = state.shared_mana.rune_upkeep_selected if upkeep else ""
    if upkeep:
        choices = [dict(slot=RUNE_SLOTS[r], rune=r, count=n, command="rune_upkeep_take", label=f"{r} ×{n}")
                   for r,n in Counter(pool.hand(upkeep)).items() if not upkeep_rune]
        choices.append(dict(slot=29, command="rune_upkeep_undo" if upkeep_rune else "rune_upkeep_end",
                            label="Cofnij wybór runy" if upkeep_rune else "Zakończ aurę"))
        if upkeep_rune:
            choices.insert(0, dict(slot=28, command="rune_upkeep_pay", label=f"Podtrzymaj: {upkeep_rune}"))
    result = dict(phase="upkeep" if upkeep else pool.phase, actor=upkeep or pool.actor,
                actor_name=actors[upkeep or pool.actor].name, upkeep=bool(upkeep), upkeep_rune=upkeep_rune,
                special_used=state.turn_action.rune_special_used,
                offer=[dict(rune=r, count=n, slot=RUNE_SLOTS[r], icon=panel_icon(RUNE_SLOTS[r])) for r, n in Counter(pool.offer).items()],
                deck_count=len(pool.deck), discard_count=len(pool.discard), opening_count=len(pool.heroes)+2,
                hands=[dict(hero=h, name=actors[h].name, cards=list(pool.hand(h)), count=len(pool.hand(h)), limit=7,
                    counts=[dict(rune=r, name=r, count=n, icon=panel_icon(RUNE_SLOTS[r]), slot=RUNE_SLOTS[r]) for r,n in Counter(pool.hand(h)).items()]) for h in pool.heroes],
                choices=[dict(c, icon=panel_icon(c["slot"])) for c in choices],
                selected_slots=[RUNE_SLOTS[upkeep_rune]] if upkeep_rune else [],
                instruction=(f"Żelazny bastion: ✓ wyda runę {upkeep_rune} i podtrzyma podstawową aurę: +1 KP, promień 2 pól. ↩ cofa wybór runy."
                             if upkeep_rune else "Wybierz dowolną runę na podtrzymanie. ↩ kończy aurę bez płatności." if pool.hand(upkeep)
                             else "Brak run na podtrzymanie. Zakończ aurę przyciskiem ↩.") if upkeep else f"{actors[pool.actor].name}: kliknij runę, aby wziąć jedną sztukę. ↩ cofa ostatni wybór; ✓ zatwierdza i przechodzi dalej." if pool.phase == "allocation" else "Niewydane runy zostają do końca walki. Nie ma kolejnego doboru.")
    from .rune_payment import view as payment_view
    selection = payment_view(session)
    if selection is not None:
        result.update(selection)
    return result


def command(session: ExplorationUiSession, data: dict[str, object]) -> dict[str, object]:
    state = session.combat_state
    mana = state.shared_mana
    if mana.runes is None or type(data.get("revision")) is not int or data["revision"] != mana.revision:
        raise ValueError("Nieaktualny wybór run.")
    action = data.get("command")
    if str(action).startswith("rune_choice_"):
        from .rune_payment import command as payment_command
        return payment_command(session, data)
    if action in {"rune_upkeep_take", "rune_upkeep_undo"}:
        if not mana.rune_upkeep_actor:
            raise ValueError("Żadna aura nie czeka na podtrzymanie.")
        rune = str(data.get("rune", "")) if action == "rune_upkeep_take" else ""
        if action == "rune_upkeep_take" and (mana.rune_upkeep_selected or rune not in mana.runes.hand(mana.rune_upkeep_actor)):
            raise ValueError("Wybierz dostępną runę do podtrzymania aury.")
        session.combat_state = replace(state, shared_mana=replace(mana, rune_upkeep_selected=rune, revision=mana.revision+1))
        session.board_panel_context = None
        session._sync_board_leds()
        return session.state_payload()
    if action in {"rune_upkeep_pay", "rune_upkeep_end"}:
        if not mana.rune_upkeep_actor:
            raise ValueError("Żadna aura nie czeka na podtrzymanie.")
        pool = mana.runes
        if action == "rune_upkeep_pay":
            from dnd_board_game.rules.runes import spend_runes
            from dnd_board_game.combat.shared_mana_features import synchronize_bastion
            if not mana.rune_upkeep_selected:
                raise ValueError("Najpierw wybierz runę na podtrzymanie.")
            pool = spend_runes(pool, mana.rune_upkeep_actor, (mana.rune_upkeep_selected,))
            session.active_combat_effects = synchronize_bastion(state.actors, tuple(
                replace(effect, value=1, radius_feet=10)
                if effect.kind == "iron_bastion" and effect.source_actor_id == mana.rune_upkeep_actor
                else effect for effect in session.active_combat_effects))
        else:
            session.active_combat_effects = tuple(e for e in session.active_combat_effects if not (
                e.kind in {"iron_bastion", "iron_bastion_member"} and e.source_actor_id == mana.rune_upkeep_actor))
        mana = replace(mana, rune_upkeep_actor="", rune_upkeep_selected="")
    elif action == "rune_take":
        pool = take_rune(mana.runes, str(data.get("rune", "")))
    elif action == "rune_undo":
        pool = undo_rune(mana.runes)
    elif action == "rune_confirm":
        pool = confirm_allocation(mana.runes)
    else:
        raise ValueError("Nieznana operacja run.")
    session.combat_state = replace(state, shared_mana=sync_runes(mana, pool))
    session.board_panel_context = None
    session._record("combat_rune_allocation", dict(command=action, actor=mana.runes.actor, rune=data.get("rune"), phase=pool.phase))
    session._sync_board_leds()
    return session.state_payload()


def scan_target(session: ExplorationUiSession) -> BoardScanTarget | None:
    from .rune_baskets import active
    if active(session):
        from .rune_baskets import scan_target as basket_target
        return basket_target(session)
    from .exploration_app import BoardScanTarget
    from dnd_board_game.hardware.board_panel import panel_feedback, panel_position
    payload = view(session)
    if payload is None or not payload["choices"]:
        return None
    slots = (*tuple(c["slot"] for c in payload["choices"]), 26, 27)
    from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole
    from dnd_board_game.hardware.led_palette import LedColor
    feedback = panel_feedback(tuple(s for s in slots if s < 26), control_slots=tuple(s for s in slots if s >= 26))
    selected = tuple(LedFrame((panel_position(slot),), LedColor.SELECTED_ABILITY_TARGET, LedRole.MARKER)
                     for slot in payload.get("selected_slots", ()))
    return BoardScanTarget(positions=tuple(panel_position(s) for s in slots),
                           feedback=LedFeedback((*feedback.frames, *selected)),
                           empty_message=payload["instruction"])


def select_position(session: ExplorationUiSession, position: Coordinate) -> dict[str, object]:
    from .rune_baskets import active
    if active(session):
        from .rune_baskets import select_position as basket_select
        return basket_select(session, position)
    from dnd_board_game.hardware.board_panel import panel_position
    payload = view(session)
    if payload and payload["choices"] and position in (panel_position(26), panel_position(27)):
        session.board_selection_revision += 1
        return dict(panel_event=dict(slot=29-position.row, context=f"rune-scroll:{session.combat_state.shared_mana.revision}"),
                    board_selection=session._board_selection_payload())
    choice = next((c for c in payload["choices"] if panel_position(c["slot"]) == position), None)
    if choice is None:
        raise ValueError("Wybierz podświetloną runę lub zatwierdzenie.")
    return command(session, {**choice, "revision": session.combat_state.shared_mana.revision})


def boost_options(session: ExplorationUiSession, declaration: ManaDeclaration) -> list[dict[str, object]]:
    from dnd_board_game.combat.runes import quote_runes
    from .board_panel_symbols import panel_icon, SYMBOLS
    from .rune_payment import declaration_targets
    from .rune_baskets import active
    if declaration.rune_flaw_only or active(session):
        return []
    card = rune_card(declaration.actor_id, declaration.ability_id)
    actor = next(a for a in session.combat_state.actors if str(a.id) == declaration.actor_id)
    choices = []
    for i, boost in enumerate(card.boosts):
        selected = bool(declaration.boosts.get(boost.id))
        reason = ""
        try:
            quote_runes(session.combat_state, actor, card.id, {} if selected else {boost.id: 1},
                        targets=declaration_targets(session, declaration))
        except ValueError as exc:
            reason = str(exc)
        slot = 5 + i
        choices.append(dict(slot=slot, rune_name=SYMBOLS[slot][0], icon=panel_icon(slot), boost_id=boost.id,
                            amount=1, count=0 if selected else 1, selected=selected, color=boost.color,
                            cost=[boost.color] if boost.color else [], budget=card.budget_for({boost.id: 1}),
                            effect=boost.label, enabled=not reason, unavailable_reason=reason))
    return choices


def option_metadata(session: ExplorationUiSession, option: dict[str, object]) -> dict[str, object]:
    from dnd_board_game.combat.session import current_actor
    actor = current_actor(session.combat_state)
    key = str(option.get("action_id") or option.get("source_id") or option.get("id") or "")
    card = rune_card(str(actor.id), key, pool=session.combat_state.shared_mana.runes)
    if card is None:
        return {}
    if card.category:
        from dnd_board_game.rules.rune_baskets import NAMES
        return dict(label=card.name, description=card.description, rune_cost=[NAMES[card.category]],
                    rune_cost_label="1 własny żeton: " + NAMES[card.category], rune_budget=card.budget,
                    action_cost="reaction" if card.budget=="R" else "special", timing=card.budget,
                    rune_slot=card.slot, mana_cost=None, mana_boosts=[])
    first_free = card.free_first and (str(actor.id), card.id + ":free") not in session.combat_state.shared_mana.runes.used_once
    return dict(label=card.name, description=card.description, rune_cost=[] if first_free else [card.rune], rune_budget=card.budget,
                rune_cost_label=f"Pierwsze użycie bez run; następne: 1 × {card.rune}" if card.free_first else "",
                action_cost="reaction" if card.budget == "R" else "special", timing=card.budget,
                rune_slot=card.slot, mana_cost=None, mana_boosts=[])


def option_unavailable(session: ExplorationUiSession, option: dict[str, object]) -> str | None:
    from dnd_board_game.combat.session import current_actor
    from dnd_board_game.combat.runes import quote_runes
    actor = current_actor(session.combat_state)
    key = str(option.get("action_id") or option.get("source_id") or option.get("id") or "")
    if rune_card(str(actor.id), key) is None:
        return None
    try:
        quote_runes(session.combat_state, actor, key, {})
    except ValueError as exc:
        return str(exc)
    return None


def finish_effects(session: ExplorationUiSession, paid: SharedMana) -> None:
    """Close the special attack series while preserving the ordinary action."""
    card = rune_card(paid.pending_actor, paid.pending_ability)
    if card is None or card.budget == "R":
        return
    state = session.combat_state
    session.combat_state = replace(state, turn_action=replace(state.turn_action,
        attack_action_active=False, attacks_used=0, attacks_maximum=0))


def apply_attack_push(session: ExplorationUiSession, transition: object) -> None:
    """Resolve the paid counterattack rider through the ordinary board topology."""
    state = session.combat_state
    mana = state.shared_mana
    applied = getattr(transition, "applied_damage", None)
    if not (mana and mana.runes and mana.pending_ability == "counterattack_command"
            and mana.command_step == 1 and dict(mana.pending_boosts).get("push") and applied):
        return
    from dnd_board_game.combat import current_actor, replace_actor
    from dnd_board_game.combat.shared_mana_features import blocks_forced_movement
    from dnd_board_game.application.combat_shove_flow import forced_push_destination
    from dnd_board_game.world import PathResult
    from dnd_board_game.rules import EffectEvent, EffectEventType
    actor = current_actor(state)
    target = next(a for a in state.actors if a.id == applied.actor_after.id)
    if actor.id != "garran" or target.is_defeated() or blocks_forced_movement(target, session.active_combat_effects):
        return
    encounter = session._active_encounter()
    destination = forced_push_destination(board=encounter.board, state=state, attacker=actor,
        target=target, distance_feet=5, scene_objects=encounter.scene_objects)
    if destination == target.position:
        return
    session.combat_state = replace_actor(state, replace(target, position=destination))
    path = PathResult(target.position, destination, (target.position, destination), 5, True)
    session._apply_spike_growth_movement_damage(str(target.id), path)
    session._apply_moonbeam_entry_damage(str(target.id), path)
    session._apply_web_entry_save(str(target.id), path)
    session._apply_zone_of_truth_entry_save(str(target.id), path)
    session._apply_combat_trigger_events((EffectEvent(EffectEventType.ACTOR_MOVED, actor_id=str(target.id), position=destination),))
    session._add_message("Rozkaz: Kontratak!", f"{target.name}: odepchnięcie na pole {destination.as_tuple()}.")

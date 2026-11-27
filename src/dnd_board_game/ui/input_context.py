"""Keyboard decisions reuse existing session commands and pure combat previews."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from typing import Any, TYPE_CHECKING

from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.world import Coordinate
from .input_commands import cursor_position, cursor_step

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession


MULTIPLE = frozenset({"bless", "passage_song", "double_shot", "force_darts"})


def charge_engine(session: ExplorationUiSession) -> Any | None:
    from . import resonance
    from .presentation_board import active as presentation_active
    if (session.launcher_navigation is not None or presentation_active(session)
            or (session.board_panel_context and session.board_panel_context[2])):
        return None
    if resonance.active(session) and session._board_selection_mode() == "combat_field":
        return resonance.engine(session)
    return None


def _signature(session: ExplorationUiSession, selection: dict[str, Any], e: Any) -> str:
    # Cursor navigation has its own revision; it must not change its own context.
    signature = [session.ui_flow_stage.value, selection["mode"],
                 session.board_selection_revision, selection.get("panel_context"),
                 selection.get("legal_positions"), selection.get("prompt")]
    if e is not None:
        p, task = e.s.preview or {}, e.s.task or {}
        signature += [e.s.round, str(e.active.id), e.s.phase, e.s.inspected,
                      p.get("id"), task.get("type"), task.get("actor"),
                      len(task.get("dice_results", []))]
    return hashlib.sha256(json.dumps(signature, sort_keys=True, default=str).encode()).hexdigest()[:20]


def _bounds(session: ExplorationUiSession) -> tuple[int, int]:
    encounter = session._active_encounter()
    dimensions = encounter.board.dimensions if encounter else None
    return (dimensions.cols, dimensions.rows) if dimensions else (20, 30)


def _candidate(session: ExplorationUiSession, e: Any) -> tuple[Any, bool, str]:
    """The engine owns a private copy; selecting it cannot change the session."""
    position = session.keyboard_cursor.position
    if position is None:
        return e, False, ""
    if e.s.inspected:
        return e, position in [a.position for a in e.board_actors()], ""
    if e.select(position):
        if e.s.preview:
            e.s.preview.pop("rejected_target", None)
        return e, True, ""
    if e.s.preview:
        from .resonance import _rejection_text
        for actor_id in e.target_candidates():
            if e.actor(actor_id).position == position:
                reason = e.target_rejection(actor_id)
                if reason:
                    e.s.preview["rejected_target"] = dict(target=actor_id, reason=reason)
                    return e, False, _rejection_text(session, e, actor_id, reason)
    return e, False, "To pole nie jest dostępne dla bieżącego wyboru."


def payload(session: ExplorationUiSession, selection: dict[str, Any] | None = None) -> dict[str, Any]:
    selection = selection if selection is not None else session._board_selection_payload()
    if session.input_mode != "keyboard":
        return dict(mode="board", context="", revision=selection["revision"], kind="menu",
                    controls=[], fields=[], cursor=None, origin=None)
    from . import resonance
    e = charge_engine(session)
    fields = [p for p in selection.get("legal_positions", []) if p[0] != 19]
    context = _signature(session, selection, e)
    cursor = session.keyboard_cursor
    origin = e.active.position if e else Coordinate(*fields[0]) if fields else None
    setup = session.encounter_setup_flow
    if e is None and selection["mode"] == "encounter_setup" and setup and setup.pending_start_position:
        origin = setup.pending_start_position
    if e and e.s.task and e.s.task["type"] == "relocate":
        origin = e.actor(e.s.task["target"]).position
    if cursor.context != context:
        cursor.context, cursor.position, cursor.touched = context, origin, False
    kind = "map" if fields else "menu"
    initiative = session.encounter_initiative_flow
    if (selection["mode"] == "initiative_roll" and initiative and initiative.roll_panel
            and not initiative.roll_panel.review):
        kind = "dice"
    controls: list[dict[str, Any]] = []
    preview: dict[str, Any] | None = None
    valid = list(cursor.position) in fields if cursor.position else False
    notice = ""
    multiple = False
    positions = {tuple(p) for p in selection.get("legal_positions", [])}
    can_accept = panel_position(28).as_tuple() in positions
    can_back = panel_position(29).as_tuple() in positions
    can_adjust = any(panel_position(slot).as_tuple() in positions for slot in (26, 27))
    if e is not None:
        if e.s.inspected:
            kind = "menu"
        real_controls = resonance.controls(e)
        for slot, control in real_controls.items():
            controls.append(dict(control, id=str(control.get("id", f"control:{slot}"))))
        # Disabled choices remain readable in the action menu.
        if e.s.phase == "idle" and not e.s.inspected:
            view = resonance.presentation(e)[0]
            existing = {c["id"] for c in controls}
            for choice in (*view["basic_actions"], *view["powers"]):
                if choice["id"] not in existing:
                    controls.append(dict(id=choice["id"], label=choice.get("label", choice.get("name", "")),
                                         disabled=choice.get("disabled", ""), slot=choice["slot"], command="choose"))
        multiple = bool(e.s.preview and e.s.preview["id"] in MULTIPLE)
        task = e.s.task
        if task and task["type"] == "roll" and e.actor(task["actor"]).faction.value == "ally":
            kind = "dice"
        can_accept, can_back = 28 in real_controls, 29 in real_controls
        if kind == "map" and cursor.touched:
            candidate, valid, notice = _candidate(session, e)
            v, board = resonance.presentation(candidate)
            preview = dict(decision=v["decision"], path=[list(p) for p in board.path],
                           cost=sum(((candidate.s.preview or {}).get("path") or {}).get("costs", [])))
            can_accept = valid or (multiple and can_accept)
        if multiple:
            notice = notice or "Kropka (.) wybiera/dodaje cel. Enter zatwierdza wybrane cele; bez gotowego zestawu wskazuje cel."
    elif kind == "map":
        can_accept = valid
    if kind == "map" and cursor.touched and not valid:
        can_accept = False
        notice = notice or "To pole nie jest teraz dostępne. Wskaż podświetlone pole."
    cols, rows = _bounds(session)
    return dict(mode="keyboard", context=context, revision=selection["revision"], kind=kind,
                bounds=dict(cols=cols, rows=rows),
                cursor=list(cursor.position) if cursor.position else None,
                origin=list(origin) if origin else None, fields=fields, controls=controls,
                selected_id=None, selection_mode="multiple" if multiple else "single",
                prompt=selection.get("prompt", ""), notice=notice, valid=valid,
                can_accept=can_accept, can_back=can_back, can_adjust=can_adjust, preview=preview)


def decorate(session: ExplorationUiSession, state: dict[str, Any]) -> None:
    view = payload(session, state["board_selection"])
    state["input"] = view
    # The authoritative controls and target sets stay unchanged. Only the read-only
    # decision card reflects the candidate under the keyboard cursor.
    combat = (state.get("combat") or {}).get("resonance")
    if combat and view.get("preview") and view.get("selection_mode") != "multiple":
        decision = view["preview"]["decision"]
        if view["valid"]:
            combat["decision"].pop("rejected_target", None)
            combat["decision"].pop("warning", None)
        combat["decision"] = dict(combat["decision"], **{
            key: value for key, value in decision.items()
            if key in {"target_ids", "targets", "warning", "rejected_target", "cost", "resonance"}
        })


def _map_feedback(base: LedFeedback) -> LedFeedback:
    """Keyboard decisions use the screen; the physical control strip stays dark."""
    return LedFeedback(tuple(
        LedFrame(positions, frame.color, frame.role)
        for frame in base.frames
        if (positions := tuple(position for position in frame.positions if position.col != 19))
    ))


def feedback(session: ExplorationUiSession, base: LedFeedback) -> LedFeedback:
    if session.input_mode != "keyboard":
        return base
    base = _map_feedback(base)
    view = payload(session)
    cursor = session.keyboard_cursor
    if view["kind"] != "map" or not cursor.touched or cursor.position is None:
        return base
    e = charge_engine(session)
    valid = view["valid"]
    if e is not None:
        from .resonance import presentation
        from dnd_board_game.hardware.resonance_feedback import resonance_feedback
        candidate, valid, _ = _candidate(session, e)
        board = presentation(candidate)[1]
        if not valid:
            board = replace(board, path=(), destination=None, selected=())
        base = _map_feedback(resonance_feedback(board))
    retained = tuple(LedFrame(positions, frame.color, frame.role) for frame in base.frames
                     if (positions := tuple(p for p in frame.positions if p != cursor.position)))
    color = LedColor.MOVEMENT_DESTINATION if valid else LedColor.ATTACK_MISS
    return LedFeedback((*retained, LedFrame((cursor.position,), color, LedRole.MARKER)))


def _resonance_send(session: ExplorationUiSession, command: str, **extra: Any) -> dict[str, Any]:
    from .resonance import command as send
    return send(session, dict(command=command, revision=session.combat_state.resonance.revision, **extra))


def command(session: ExplorationUiSession, data: dict[str, Any]) -> dict[str, Any]:
    current = payload(session)
    if session.input_mode != "keyboard":
        raise ValueError("Najpierw włącz sterowanie klawiaturą.")
    if data.get("context") != current["context"] or data.get("revision") != current["revision"]:
        raise ValueError("Ten wybór jest już nieaktualny. Użyj bieżącego ekranu.")
    action = data.get("command")
    cursor = session.keyboard_cursor
    e = charge_engine(session)
    if action in {"navigate", "cursor"}:
        if current["kind"] != "map" or cursor.position is None:
            raise ValueError("Ten ekran nie oczekuje wskazania pola mapy.")
        cols, rows = _bounds(session)
        position = (cursor_step(cursor.position, data.get("dx", 0), data.get("dy", 0), cols=cols, rows=rows)
                    if action == "navigate" else cursor_position(data.get("position"), cols=cols, rows=rows))
        cursor.position, cursor.touched = position, True
        cursor.revision += 1
        session._sync_board_leds()
        return session.state_payload()
    if e is not None:
        from .resonance import controls
        available = controls(e)
        if action == "shortcut":
            choice = str(data.get("id", ""))
            if choice == "end":
                action, data = "activate", dict(id="control:3")
            elif choice == "info":
                action, data = "activate", dict(id="control:25")
            else:
                action, data = "activate", dict(id=choice)
        if action == "activate":
            key = str(data.get("id", ""))
            choice = next((control for slot, control in available.items()
                           if str(control.get("id", f"control:{slot}")) == key), None)
            if not choice:
                raise ValueError("To działanie nie jest teraz dostępne.")
            cursor.revision += 1
            return _resonance_send(session, **{k: v for k, v in choice.items() if k not in {"label", "slot"}})
        if action == "adjust":
            delta = data.get("delta")
            if type(delta) is not int or delta not in {-1, 1}:
                raise ValueError("Zmiana wartości musi wynosić +1 albo −1.")
            choice = available.get(26 if delta > 0 else 27)
            if not choice:
                raise ValueError("Nie można teraz zmienić wartości.")
            cursor.revision += 1
            return _resonance_send(session, **{k: v for k, v in choice.items() if k not in {"label", "slot"}})
        if action in {"accept", "select"} and current["kind"] == "map":
            if cursor.touched and not current["valid"]:
                raise ValueError(current["notice"])
            multiple = current["selection_mode"] == "multiple"
            ready_before = bool(available.get(28, {}).get("command") == "accept")
            if action == "accept" and multiple and ready_before:
                cursor.revision += 1
                return _resonance_send(session, "accept")
            if cursor.position is None or list(cursor.position) not in current["fields"]:
                if action == "accept" and ready_before:
                    cursor.revision += 1
                    return _resonance_send(session, "accept")
                raise ValueError("Najpierw wskaż dostępne pole.")
            cursor.revision += 1
            result = _resonance_send(session, "select", position=list(cursor.position))
            updated = charge_engine(session)
            if (action == "accept" and not multiple and updated is not None
                    and controls(updated).get(28, {}).get("command") == "accept"):
                # Relocation and self actions use the same existing confirmation.
                return _resonance_send(session, "accept")
            return result
        if action in {"accept", "back"}:
            slot = 28 if action == "accept" else 29
            choice = available.get(slot)
            if not choice:
                raise ValueError("Nie można teraz zatwierdzić ani cofnąć tego kroku.")
            cursor.revision += 1
            return _resonance_send(session, **{k: v for k, v in choice.items() if k not in {"label", "slot"}})
    # Existing generic panel handlers already validate the current flow and may
    # return browser-owned panel events. Merely moving the cursor never calls them.
    target = session._current_board_scan_target()
    if action in {"accept", "select"} and current["kind"] == "map":
        setup = session.encounter_setup_flow
        if (action == "accept" and current["context"] == cursor.context and not cursor.touched
                and session._board_selection_mode() == "encounter_setup" and setup
                and setup.pending_start_position is not None and setup.can_confirm):
            selected = panel_position(28)
        else:
            selected = cursor.position
    elif action in {"accept", "back", "adjust"}:
        if action == "adjust":
            if type(data.get("delta")) is not int or data["delta"] not in {-1, 1}:
                raise ValueError("Zmiana wartości musi wynosić +1 albo −1.")
            slot = 26 if data["delta"] > 0 else 27
        else:
            slot = 28 if action == "accept" else 29
        selected = panel_position(slot)
    else:
        raise ValueError("Wybierz działanie w bieżącym menu.")
    if selected is None or selected not in target.positions:
        raise ValueError("Ten wybór nie jest teraz dostępny.")
    cursor.revision += 1
    cursor.touched = False
    result = session.select_board_position(selected)
    if "panel_event" in result:
        result["input"] = payload(session, result["board_selection"])
    return result

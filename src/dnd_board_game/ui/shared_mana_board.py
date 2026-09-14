"""Board selection for targets shown by a shared-mana declaration."""
from __future__ import annotations

from typing import TYPE_CHECKING

from dnd_board_game.hardware.board_panel import panel_feedback, panel_position
from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.world import Coordinate

if TYPE_CHECKING:
    from .exploration_app import BoardScanTarget, ExplorationUiSession
    from .shared_mana import ManaDeclaration


def has_targets(declaration: ManaDeclaration | None) -> bool:
    return declaration is not None and (declaration.stage == "bonus" or
        declaration.ability_id in {"counterattack_command", "feint", "caring_gesture", "mana_inspiration"})


def target_selection(session: ExplorationUiSession, declaration: ManaDeclaration,
                     targets: list[dict[str, str]]) -> dict[str, object]:
    multiple = declaration.stage == "bonus" and declaration.ability_id == "garran_shield_wall"
    maximum = int(declaration.resume_arguments["remaining"]) if multiple else 1
    selected = declaration.selected_target_ids if multiple else tuple(
        key for key in (declaration.resume_arguments.get("target_id"),) if key)
    actors = {str(actor.id): actor for actor in session.combat_state.actors}
    choices = [dict(target, position=list(actors[target["id"]].position.as_tuple()),
                    selected=target["id"] in selected) for target in targets]
    legal = {target["id"] for target in choices}
    applied = [dict(id=key, name=actors[key].name, position=list(actors[key].position.as_tuple()))
               for key in declaration.resume_arguments.get("used_targets", ())
               if multiple and key in actors]
    instruction = (f"Wybierz do {maximum} sojuszników, naciskając ich podświetlone pola."
                   if multiple and maximum > 1 else
                   "Wybierz cel, naciskając jego podświetlone pole na planszy.")
    instruction += " Wybrane figurki świecą mocniej. Ponowne naciśnięcie cofa wybór."
    if declaration.stage == "bonus" and declaration.ability_id == "garran_shield_wall":
        instruction += " ✓ nadaje wybranym po 5 tymczasowych PW."
    return dict(targets=choices, applied_targets=applied, selected_ids=list(selected), multiple=multiple,
                maximum=maximum, can_confirm=bool(selected) and len(selected) <= maximum
                and len(set(selected)) == len(selected) and set(selected) <= legal,
                instruction=instruction)


def scan_target(session: ExplorationUiSession) -> BoardScanTarget | None:
    from .exploration_app import BoardScanTarget
    from .shared_mana import payload
    from .aura_preview import context_feedback

    if not has_targets(session.shared_mana_declaration):
        return None
    view = payload(session)["declaration"]
    selection = view.get("target_selection")
    if selection is None:
        return None
    positions = tuple(Coordinate(*target["position"]) for target in selection["targets"])
    frames = tuple(LedFrame((Coordinate(*target["position"]),),
        LedColor.SELECTED_ABILITY_TARGET if target["selected"] else LedColor.LEGAL_ABILITY_TARGET,
        LedRole.MARKER) for target in selection["targets"])
    frames += tuple(LedFrame((Coordinate(*target["position"]),),
        LedColor.SELECTED_ABILITY_TARGET, LedRole.MARKER) for target in selection["applied_targets"])
    controls = [28] if selection["can_confirm"] and not view.get("error") else []
    if view["stage"] == "payment" or selection["selected_ids"]:
        controls.append(29)
    if view["stage"] != "payment" and view.get("roll_sides"):
        roll = view.get("roll") or 1
        if roll > 1:
            controls.append(26)
        if roll < view["roll_sides"]:
            controls.append(27)
    choices = [choice for choice in view.get("boost_options", ()) if choice["enabled"]]
    colors = {"C": (255, 45, 45), "N": (30, 110, 255), "Z": (30, 220, 70),
              "B": (255, 255, 255), "F": (150, 150, 150), "*": (190, 190, 190)}
    marked = {p for frame in frames for p in frame.positions}
    aura_frames = tuple(LedFrame(tuple(p for p in frame.positions if p not in marked), frame.color, frame.role)
                        for frame in context_feedback(session).frames)
    feedback = panel_feedback(tuple(choice["slot"] for choice in choices),
        control_slots=tuple(controls), base=LedFeedback((*aura_frames, *frames)),
        action_colors={choice["slot"]: colors[choice["color"]] for choice in choices})
    selected_boosts = tuple(LedFrame((panel_position(choice["slot"]),),
        colors[choice["color"]], LedRole.MARKER) for choice in choices if choice["selected"])
    return BoardScanTarget(
        positions=(*positions, *(panel_position(slot) for slot in controls),
                   *(panel_position(choice["slot"]) for choice in choices)),
        feedback=LedFeedback((*feedback.frames, *selected_boosts)),
        empty_message=selection["instruction"])


def select_position(session: ExplorationUiSession, position: Coordinate) -> dict[str, object]:
    from .shared_mana import command, payload

    target = scan_target(session)
    if target is None or position not in target.positions:
        raise ValueError("Wybierz podświetlone pole lub przycisk planszy.")
    # Native scans bypass the HTTP game-command hook which clears old dice panels.
    session.board_panel_context = None
    view = payload(session)["declaration"]
    data = {"revision": session.combat_state.shared_mana.revision}
    actor = next((item for item in view["target_selection"]["targets"]
                  if list(position.as_tuple()) == item["position"]), None)
    if actor:
        data.update(command="target", target_id=actor["id"])
    else:
        slot = 29 - position.row
        if slot == 28:
            data["command"] = {"payment": "pay", "bonus": "bonus", "effect_roll": "effect"}[view["stage"]]
        elif slot == 29:
            data["command"] = "cancel" if view["stage"] == "payment" else "clear_targets"
        elif slot in (26, 27):
            data.update(command="parameters", natural_roll=(view.get("roll") or 1) + (1 if slot == 27 else -1))
        else:
            data.update(command="boost_option", slot=slot)
    return command(session, data)

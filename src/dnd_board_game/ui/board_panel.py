"""Stable printed controls projected onto the authoritative combat menu."""

from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

from dnd_board_game.hardware.led_palette import LedColor, RGBColor
from dnd_board_game.hardware.board_panel import PANEL_MOVE, PANEL_ATTACK, PANEL_ITEM, PANEL_END_TURN
from dnd_board_game.scenarios.rune_catalog import rune_card
from dnd_board_game.ui.board_panel_symbols import HERO_PANEL_ABILITIES, ability_panel_slot, panel_icon

if TYPE_CHECKING:
    from .exploration_app import BoardScanTarget, ExplorationUiSession
    from dnd_board_game.world import Coordinate


def browser_dice_target(session: ExplorationUiSession) -> BoardScanTarget:
    """One browser die owns the controls, including correction and final review."""
    from .exploration_app import BoardScanTarget
    from dnd_board_game.hardware.board_panel import panel_feedback, panel_position
    context = session.board_panel_context
    slots = context[1] if context and context[0].startswith('dice:') and context[2] else (28,)
    return BoardScanTarget(positions=tuple(panel_position(slot) for slot in slots),
        feedback=panel_feedback(control_slots=slots),
        empty_message='Ustaw wynik bieżącej kości przez − / +. ✓ przechodzi dalej; na końcu zatwierdź podsumowanie. ↩ poprawia poprzednią kość.')


def select_browser_die(session: ExplorationUiSession, position: Coordinate) -> dict[str, object]:
    if position not in browser_dice_target(session).positions:
        raise ValueError('Dokończ bieżącą kość lub podsumowanie rzutu na panelu − / + / ✓ / ↩.')
    context = session.board_panel_context
    session.board_selection_revision += 1
    return dict(panel_event=dict(slot=29-position.row, context=context[0] if context else None),
                board_selection=session._board_selection_payload())


def action_economy_panel_color(economy: str) -> RGBColor:
    """Color the panel using the same economy group as its screen tile."""
    return {
        "action": LedColor.PANEL_ACTION,
        "bonus_action": LedColor.PANEL_BONUS_ACTION,
        "movement": LedColor.PANEL_MOVEMENT,
        "control": LedColor.PANEL_TURN_CONTROL,
    }.get(economy, LedColor.PANEL_FREE_ACTION)


class PanelOption(Protocol):
    id: str
    action_id: str | None
    source_id: str | None


def option_panel_payload(
    hero_id: str, option: PanelOption, *, basic_attack: bool = False
) -> dict[str, object]:
    fixed = {"turn:move": PANEL_MOVE, "menu:items": PANEL_ITEM, "turn:end": PANEL_END_TURN}
    ability = {
        "basic:hide": "hide", "basic:end-hide": "hide", "turn:grapple": "grapple",
    }.get(option.id, option.action_id or option.source_id)
    abilities = HERO_PANEL_ABILITIES.get(hero_id, ())
    slot = fixed.get(option.id)
    card = rune_card(hero_id, ability or "")
    if card is not None:
        slot = card.slot
    elif ability == 'counterattack_command':
        slot = ability_panel_slot('garran', ability)
    elif ability in abilities:
        slot = ability_panel_slot(hero_id, ability)
    elif basic_attack:
        slot = PANEL_ATTACK
    return {"panel_slot": slot, "panel_icon": panel_icon(slot) if slot is not None else panel_icon(PANEL_ATTACK) if option.source_id else ""}

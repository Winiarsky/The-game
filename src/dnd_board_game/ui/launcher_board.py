"""Page-scoped rune navigation, sharing the game's single board connection."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING
from uuid import uuid4

from dnd_board_game.hardware.board_panel import PANEL_RUNE_START, PANEL_RUNE_STOP, panel_feedback, panel_position
from dnd_board_game.hardware.led_palette import LedColor

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession, BoardScanTarget
    from dnd_board_game.world import Coordinate


@dataclass(frozen=True)
class LauncherNavigation:
    token: str
    slots: tuple[int, ...] = ()
    selected: tuple[int, ...] = ()
    controls: tuple[int, ...] = ()
    focused: int | None = None
    back: bool = False
    generation: int = 0
    consumed: bool = False

    @property
    def active_slots(self) -> tuple[int, ...]:
        return () if self.consumed else (*self.slots, *self.controls, *((29,) if self.back else ()))


def begin(s: ExplorationUiSession) -> str:
    s.launcher_navigation = LauncherNavigation(uuid4().hex)
    s.board_panel_context = None
    s._cancel_obsolete_board_input()
    s._sync_board_leds()
    return s.launcher_navigation.token


def leave(s: ExplorationUiSession) -> None:
    s.launcher_navigation = None
    s._cancel_obsolete_board_input()
    s._sync_board_leds()


def configure(s: ExplorationUiSession, data: dict[str, object]) -> dict[str, object]:
    nav = s.launcher_navigation
    if nav is None or data.get('token') != nav.token:
        raise ValueError('To menu nie jest już aktywne. Odśwież stronę.')
    slots, selected = data.get('slots', []), data.get('selected', [])
    for values in (slots, selected):
        if not isinstance(values, list) or len(values) > 20 or any(type(v) is not int or not PANEL_RUNE_START <= v < PANEL_RUNE_STOP for v in values):
            raise ValueError('Nieprawidłowe runy menu.')
        if len(set(values)) != len(values):
            raise ValueError('Każdy kafelek menu musi mieć osobną runę.')
    if not set(selected) <= set(slots) or type(data.get('back', False)) is not bool:
        raise ValueError('Nieprawidłowy wybór menu.')
    controls = data.get('controls', [])
    focused = data.get('focused')
    if (not isinstance(controls, list) or len(controls) > 3
            or any(type(slot) is not int or slot not in (26, 27, 28) for slot in controls)
            or len(controls) != len(set(controls))
            or (focused is not None and (type(focused) is not int or focused not in slots))):
        raise ValueError('Nieprawidłowe przyciski nawigacji menu.')
    s.launcher_navigation = replace(nav, slots=tuple(slots), selected=tuple(selected),
                                    controls=tuple(controls) if slots else (), focused=focused,
                                    back=data.get('back') is True, generation=nav.generation + 1, consumed=False)
    if s.board_adapter is not None and not s.board_adapter.connected:
        s.shutdown_board()
    if s.board_adapter is None:
        backend = s.board_backend if s.board_backend in {'hardware', 'simulator'} else s.configured_board_backend
        s.configure_board(backend=backend, board_url=s.board_url,
                          board_serial_port=s.board_serial_port, wled_url=s.wled_url)
    s._cancel_obsolete_board_input()
    s._sync_board_leds()
    return {'board_selection': selection(s), 'board': s._board_payload()}


def release(s: ExplorationUiSession, token: str) -> None:
    nav = s.launcher_navigation
    # Delayed pagehide from a previous document must not stop the new screen.
    if nav is not None and nav.token == token:
        s.launcher_navigation = replace(nav, consumed=True, generation=nav.generation + 1)
        s._cancel_obsolete_board_input()
        s._sync_board_leds()


def target(s: ExplorationUiSession) -> BoardScanTarget:
    from .exploration_app import BoardScanTarget
    nav = s.launcher_navigation
    slots = nav.active_slots
    colors = {slot: LedColor.MOVEMENT_DESTINATION if slot in nav.selected else LedColor.PANEL_RUNE
              for slot in slots if slot < 26}
    return BoardScanTarget(positions=tuple(panel_position(slot) for slot in slots),
        feedback=panel_feedback(tuple(colors), selected_slot=nav.focused, action_colors=colors,
                                control_slots=tuple(slot for slot in slots if slot >= 26)),
        empty_message=('Naciśnij podświetloną runę kafelka.'
                       + (' −/+ przegląda, ✓ wybiera.' if nav.controls else '')
                       + (' ↩ wraca.' if nav.back else '')))


def selection(s: ExplorationUiSession) -> dict[str, object]:
    nav = s.launcher_navigation
    connected = s.board_adapter is not None and s.board_adapter.connected
    positions = [list(panel_position(slot).as_tuple()) for slot in nav.active_slots]
    return dict(revision=f'launcher:{nav.token}:{nav.generation}', navigation_token=nav.token,
                mode='launcher', input_mode='single', panel_enabled=False, panel_context=None,
                legal_positions=positions, legal_position_count=len(positions), connected=connected,
                auto_arm=connected and bool(positions), allow_retry=connected,
                confirmation_policy='immediate', prompt=target(s).empty_message)


def select(s: ExplorationUiSession, position: Coordinate) -> dict[str, object]:
    nav = s.launcher_navigation
    slot = 29 - position.row
    if position.col != 19 or slot not in nav.active_slots:
        raise ValueError('Ta runa nie jest teraz dostępna.')
    s.launcher_navigation = replace(nav, consumed=True, generation=nav.generation + 1)
    s._sync_board_leds()
    return {'navigation_event': {'token': nav.token, 'slot': slot}, 'board_selection': selection(s)}

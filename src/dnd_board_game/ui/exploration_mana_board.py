"""Printed runes for exploration decisions; the same choices drive UI and scans."""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from dnd_board_game.hardware.board_panel import panel_feedback, panel_position
from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.rules.exploration_mana_catalog import COLORS, HEROES
from dnd_board_game.world import Coordinate
from .board_panel_symbols import SYMBOLS, panel_icon

if TYPE_CHECKING:
    from .exploration_app import BoardScanTarget, ExplorationUiSession


def choice(slot: int, action: str, label: str, **extra: Any) -> dict[str, Any]:
    return dict(slot=slot, action=action, label=label, extra=extra,
                name=SYMBOLS[slot][0], icon=panel_icon(slot))


def choices(p: dict[str, Any]) -> list[dict[str, Any]]:
    """Only legal choices receive a lit rune. Slot assignments never compact."""
    if p.get('model') == 'party_confrontation':
        return p['board_choices']
    result = []
    a = p.get('attempt')
    if p['phase'] in {'introduction', 'setup'}:
        result.append(choice(28, 'acknowledge', 'Gotowe'))
    elif not a:
        result.extend(choice(6 + HEROES.index(o['hero']), 'start', o['name'], method=o['id'])
                      for o in p['options'] if o['enabled'])
    elif a['needs_resume']:
        result.append(choice(28, 'resume', 'Potwierdzam zachowane stosy', stacks_preserved=True))
        if a['phase'] == 'bargain':
            result.append(choice(24, 'accept_bargain', 'Przyjmij podpisane świadectwo'))
    elif a['phase'] == 'bargain':
        result.extend((choice(24, 'accept_bargain', 'Przyjmij podpisane świadectwo'),
                       choice(25, 'decline_bargain', 'Odrzuć propozycję · wróć do pas/dobór')))
    elif a['phase'] == 'offer':
        if p['condition']['kind'] == 'favor' and a['favor_status'] != 'used':
            result.append(choice(25, 'cancel_favor', 'Wybierz normalną wartość') if a['favor_status'] == 'armed'
                          else choice(24, 'arm_favor', 'Ustępstwo: karta za 1 w zamian za list'))
        result.extend(choice(13 + COLORS.index(v['color']), 'choose', v['name'], color=v['color'])
                      for v in a['values'] if (not a['expected_color'] or a['expected_color'] == v['color'])
                      and sum(c['color'] == v['color'] for c in a['cards']) < 5)
        if a['cards'] and not a['expected_color']:
            result.append(choice(22, 'empty', 'Talia wyczerpana'))
    elif a['phase'] == 'decision':
        if not a['must_stand']:
            result.append(choice(18, 'draw', 'Dobierz kolejną ofertę'))
        if not a['must_draw']:
            result.append(choice(19, 'stand', 'Pas · przejdź do testu'))
    elif a['phase'] == 'roll':
        result.append(choice(28, 'roll', 'Zatwierdź wpisane wyniki kości'))
    elif a['phase'] == 'reroll_choice':
        result.append(choice(20, 'reroll', 'Improwizacja · przerzuć test'))
        if p['lesson']['finish'] != 'reroll':
            result.append(choice(21, 'accept', 'Przyjmij porażkę'))
    elif a['phase'] == 'result':
        result.append(choice(28, 'next', p.get('next_label', 'Następne ćwiczenie')))
        result.extend(choice(24+i, 'debrief', f['label'], id=f['id']) for i,f in enumerate(p.get('followups', [])) if not f['completed'])
    if not a or a['phase'] in {'offer', 'decision', 'bargain', 'result'}:
        result.append(choice(23, 'retry', 'Powtórz lekcję · przygotuj talię od nowa'))
    result.append(choice(29, 'leave', p.get('leave_label', 'Wybór postaci · zachowaj postęp')))
    return result


MANA_LED_COLORS: dict[str, tuple[int, int, int]] = {
    'C': (255, 0, 0), 'B': (255, 255, 255), 'Z': (0, 255, 0),
    'F': (180, 0, 255), 'N': (0, 70, 255),
}


def mana_choice_colors(p: dict[str, Any]) -> dict[int, tuple[int, int, int]]:
    """Color reporting and taking a revealed card share the same LED identity."""
    colors: dict[int, tuple[int, int, int]] = {}
    for control in p['board_choices']:
        color = control['extra'].get('color')
        if control['action'] == 'take':
            color = p['mana']['offer'][control['extra']['index']]
        if color in MANA_LED_COLORS:
            colors[control['slot']] = MANA_LED_COLORS[color]
    return colors


def scan_target(s: ExplorationUiSession) -> BoardScanTarget:
    from .exploration_app import BoardScanTarget
    from .exploration_mana import payload
    p = payload(s)
    if p.get('attempt', {}).get('phase') == 'roll':
        from .board_panel import browser_dice_target
        return browser_dice_target(s)
    controls = p['board_choices']
    base = LedFeedback()
    if p['phase'] == 'setup' and p['setup']['position']:
        base = LedFeedback((LedFrame((Coordinate(*p['setup']['position']),),
                                    LedColor.PLAYER_START_ZONE, LedRole.MARKER),))
    elif p['phase'] == 'scene':
        base = LedFeedback((LedFrame((Coordinate(*p['scene']['position']),),
                                    LedColor.INTERACTIVE_OBJECT, LedRole.MARKER),))
    return BoardScanTarget(
        positions=tuple(panel_position(c['slot']) for c in controls),
        feedback=panel_feedback(tuple(c['slot'] for c in controls if c['slot'] < 26),
                                control_slots=tuple(c['slot'] for c in controls if c['slot'] >= 26), base=base,
                                action_colors=mana_choice_colors(p)),
        empty_message='Wybierz podświetloną runę na planszy. Jej znaczenie widzisz przy opcji na ekranie.')


def select_position(s: ExplorationUiSession, position: Coordinate) -> dict[str, object]:
    from .exploration_mana import command, payload
    p = payload(s)
    if p.get('attempt', {}).get('phase') == 'roll':
        from .board_panel import select_browser_die
        return select_browser_die(s, position)
    selected = next((c for c in p['board_choices'] if panel_position(c['slot']) == position), None)
    if selected is None:
        raise ValueError('Ta runa nie jest aktywna w bieżącym kroku eksploracji.')
    if selected['action'] in ('scroll', 'inspect'):
        s.board_selection_revision += 1
        return dict(panel_event=dict(slot=selected['slot'], context=f"confrontation-{selected['action']}:{p['revision']}"),
                    board_selection=s._board_selection_payload())
    return command(s, dict(action=selected['action'], revision=p['revision'], **selected['extra']))

"""A real combat lesson for detection and disarming; no mana-card minigame."""
from __future__ import annotations

from dataclasses import replace
import json
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from dnd_board_game.application.recruitment_arena import ARENA_ID
from dnd_board_game.combat.scene import scene_flag, set_scene_flag
from dnd_board_game.combat.session import current_actor
from dnd_board_game.combat.simple_traps import SimpleTrap, trap_request, validate_trap_action, resolve_trap_check
from dnd_board_game.world import Coordinate

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession

KEY = 'simple_trap_training'
POSITION = Coordinate(8, 18)


def enabled(s: ExplorationUiSession) -> bool:
    return s.exploration.scenario_id == ARENA_ID and scene_flag(s.state.flags, 'training_mode', '') == 'traps'


def read(s: ExplorationUiSession) -> dict[str, Any]:
    raw = scene_flag(s.state.flags, KEY, '')
    return json.loads(str(raw)) if raw else dict(revision=0, status='hidden', pending=None, result='', completed=False,
                                                phase='introduction', token=uuid4().hex)


def write(s: ExplorationUiSession, data: dict[str, Any]) -> None:
    data['revision'] += 1
    s.state = replace(s.state, flags=set_scene_flag(s.state.flags, KEY, json.dumps(data, ensure_ascii=False)))
    s.board_panel_context = None
    s.board_selection_revision += 1
    s._sync_board_leds()


def initialize(s: ExplorationUiSession) -> None:
    data = dict(revision=0, status='hidden', pending=None, result='', completed=False, phase='introduction', token=uuid4().hex)
    s.state = replace(s.state, flags=set_scene_flag(s.state.flags, KEY, json.dumps(data)))


def notice(s: ExplorationUiSession) -> dict[str, object] | None:
    if not enabled(s):
        return None
    data = read(s)
    if data['phase'] != 'introduction':
        return None
    return dict(id='trap:'+data['token'], phase='introduction', name='Pułapka podczas walki',
                narration='Nessa: wykryj pułapkę zwykłym testem Mądrości, a potem dezaktywuj testem Zręczności. Każda próba zużywa akcję, więc pomiędzy nimi normalnie przejdzie tura przeciwnika.',
                explanation='Na polu (8,18) znajduje się ćwiczebny mechanizm z atramentem. Znacznik połóż dopiero po wykryciu. Narzędzia są przygotowane obok; biegłość otrzymuje tylko posiadający ją bohater. Ten test nie korzysta z doboru many.',
                instruction='Przeczytaj zasady, przygotuj planszę i rozpocznij walkę. W swojej turze wybierz wykrywanie pułapki.', button='✓ Przygotuj ćwiczenie')


def acknowledge(s: ExplorationUiSession, notice_id: str) -> dict[str, object]:
    expected = notice(s)
    if not expected or expected['id'] != notice_id:
        raise ValueError('To objaśnienie nie jest już aktualne.')
    data = read(s)
    data['phase'] = 'exercise'
    write(s, data)
    return s.state_payload()


def command(s: ExplorationUiSession, data: dict[str, Any]) -> dict[str, object]:
    if not enabled(s):
        raise ValueError('Nie trwa lekcja pułapki.')
    stored = read(s)
    if data.get('revision') != stored['revision']:
        raise ValueError('Nieaktualne polecenie pułapki.')
    if data.get('action') in {'leave', 'retry'}:
        from .training_arena import training_hero
        hero = str(scene_flag(s.state.flags, 'training_hero', 'garran'))
        saved = [(k, v) for k, v in s.state.flags.values if k.startswith(('walkthrough_', 'training_completed_', 'training_tutorial_done_', 'exploration_mana_', 'trap_lesson_done_'))]
        s.configure_custom_party((training_hero(hero),))
        flags = s.state.flags
        for key, value in saved:
            flags = set_scene_flag(flags, key, value)
        s.state = replace(s.state, flags=flags)
        if data.get('action') == 'retry':
            from .training_arena import start_training_trial
            return start_training_trial(s, hero, 'traps', 'humanoid')
        from .training_menu import show_cases
        from dnd_board_game.scenarios.character_text import tutorial_steps as steps
        show_cases(s, hero, len(steps(hero)) + 1)
        s._sync_board_leds()
        return s.state_payload()
    if s.combat_state is None or stored['phase'] != 'exercise':
        raise ValueError('Najpierw przygotuj planszę i rozpocznij walkę.')
    trap = SimpleTrap('training_ink', 'Pułapka z atramentem', POSITION, status=stored['status'])
    action = str(data.get('action', ''))
    if action in {'detect', 'disarm'}:
        if stored['pending'] or s._combat_has_pending_resolution() or s.shared_mana_declaration:
            raise ValueError('Najpierw rozstrzygnij poprzednie działanie.')
        actor = validate_trap_action(s.combat_state, trap, action, tools_available=True)
        stored['pending'] = dict(action=action, actor=str(actor.id), round=s.combat_state.round_number)
    elif action == 'roll':
        pending = stored['pending']
        if not pending or str(current_actor(s.combat_state).id) != pending['actor'] or s.combat_state.round_number != pending['round']:
            raise ValueError('Oczekujący test należy do innej tury.')
        outcome = resolve_trap_check(s.combat_state, trap, pending['action'], data.get('roll'), tools_available=True)
        s.combat_state = outcome.state
        stored['pending'] = None
        stored['status'] = outcome.trap.status
        if pending['action'] == 'detect':
            stored['result'] = f'Wynik {outcome.total}. ' + ('Pułapka wykryta — połóż znacznik na polu (8,18). W kolejnej turze możesz ją dezaktywować.' if outcome.success else 'Nie udało się wykryć pułapki. Akcja została zużyta; możesz spróbować w kolejnej turze.')
        else:
            stored['result'] = f'Wynik {outcome.total}. ' + ('Pułapka rozbrojona.' if outcome.success else 'Pułapka uruchomiona: atrament oznacza twoją figurkę. Mechanizm został zużyty; w tej lekcji nie zadaje obrażeń.')
            stored['completed'] = True
            flags = set_scene_flag(s.state.flags, 'trap_lesson_done_'+pending['actor'], True)
            if outcome.triggered:
                flags = set_scene_flag(flags, 'training_ink_mark_'+pending['actor'], True)
            s.state = replace(s.state, flags=flags)
        s._record('simple_combat_trap_resolved', dict(action=pending['action'], total=outcome.total,
                                                    status=outcome.trap.status, actor=pending['actor']))
    else:
        raise ValueError('Nieznane działanie przy pułapce.')
    write(s, stored)
    return s.state_payload()


def payload(s: ExplorationUiSession) -> dict[str, Any] | None:
    if not enabled(s):
        return None
    data = read(s)
    data['options'] = []
    data['position'] = list(POSITION.as_tuple())
    if s.combat_state is None or s.combat_state.status.value != 'active' or data['phase'] == 'introduction':
        return data
    trap = SimpleTrap('training_ink', 'Pułapka z atramentem', POSITION, status=data['status'])
    actor = current_actor(s.combat_state)
    for action, name in (('detect','Wykryj pułapkę · akcja'), ('disarm','Dezaktywuj pułapkę · akcja')):
        reason = ''
        try:
            validate_trap_action(s.combat_state, trap, action, tools_available=True)
            if s._combat_has_pending_resolution() or s.shared_mana_declaration:
                reason = 'Najpierw zakończ bieżące działanie.'
        except ValueError as error:
            reason = str(error)
        data['options'].append(dict(action=action, name=name, enabled=not reason and not data['pending'], reason=reason))
    if data['pending']:
        request = trap_request(actor, trap, data['pending']['action'], state=s.combat_state)
        data['modifiers'] = [dict(label=m.label, value=m.value) for m in request.modifiers]
    return data

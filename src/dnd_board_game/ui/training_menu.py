"""Board and screen navigation for sequential courses and isolated cases."""
from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from dnd_board_game.application.recruitment_arena import HERO_ORDER
from dnd_board_game.scenarios.character_text import tutorial_steps as steps
from dnd_board_game.combat.scene import scene_flag, set_scene_flag
from dnd_board_game.hardware.board_panel import panel_feedback, panel_position
from .board_panel_symbols import panel_icon

if TYPE_CHECKING:
    from .exploration_app import BoardScanTarget, ExplorationUiSession
    from dnd_board_game.world import Coordinate

PAGE_SIZE = 8


def _read(s: ExplorationUiSession, key: str, default: object = '') -> object:
    return scene_flag(s.state.flags, 'training_menu_' + key, default)


def _write(s: ExplorationUiSession, *, hero: str = '', view: str = 'heroes', page: int = 0, subject: str = 'combat') -> None:
    flags = s.state.flags
    for key, value in dict(hero=hero, view=view, page=page, subject=subject).items():
        flags = set_scene_flag(flags, 'training_menu_' + key, value)
    s.state = replace(s.state, flags=flags)
    s.board_panel_context = None
    s.board_selection_revision += 1


def show_cases(s: ExplorationUiSession, hero: str, index: int, subject: str = 'combat') -> None:
    _write(s, hero=hero, view='cases', page=index // PAGE_SIZE, subject=subject)


def show_modes(s: ExplorationUiSession, hero: str, subject: str = 'combat') -> None:
    _write(s, hero=hero, view='modes', subject=subject)


def payload(s: ExplorationUiSession) -> dict[str, object]:
    from .training_arena import training_hero
    hero = str(_read(s, 'hero'))
    view = str(_read(s, 'view', 'heroes')) if hero in HERO_ORDER else 'heroes'
    subject = str(_read(s, 'subject', 'combat'))
    exploring = subject == 'exploration'
    subject_name = 'Eksploracja' if exploring else 'Walka'
    page, pages = 0, 1
    options: list[dict[str, object]] = []

    def option(slot: int, action: str, label: str, **data: object) -> None:
        options.append(dict(slot=slot, icon=panel_icon(slot), action=action, label=label, **data))

    if view == 'heroes':
        for index, h in enumerate(HERO_ORDER):
            option(5 + index, 'hero:' + h, training_hero(h).name)
        title = 'Wybierz postać'
    elif view == 'subjects':
        title = training_hero(hero).name + ' · wybierz dział'
        option(5, 'subject:combat', 'Walka', detail='Mana, zdolności, podbicia, pojedynek i pułapka.')
        option(6, 'subject:exploration', 'Eksploracja', detail='Rozmowy z NPC, obiekty i warunki interakcji.')
    elif view == 'modes':
        title = training_hero(hero).name + ' · ' + subject_name
        if exploring:
            from .confrontation import read_store
            from dnd_board_game.scenarios.confrontation import lessons_for
            total = len(lessons_for(hero))
            progress = int(read_store(s).get('sequence_progress', {}).get(hero, 0))
            completed = progress >= total
        else:
            total = len(steps(hero))
            progress = int(scene_flag(s.state.flags, f'walkthrough_charge_progress_{hero}', 0))
            completed = bool(scene_flag(s.state.flags, f'walkthrough_charge_completed_{hero}', False))
        option(5, 'sequence', 'Po kolei · od początku' if completed or not progress else 'Po kolei · kontynuuj',
               detail=f'{total} ćwiczeń' + (' rozmów i obiektów.' if exploring else ' i końcowy pojedynek.')
               if completed or not progress else f'Zachowany postęp: {progress}/{total} ćwiczeń.')
        option(6, 'cases', 'Wybierz ćwiczenie', detail='Dowolny przypadek. Bez zmiany postępu kursu po kolei.')
        if exploring:
            from .confrontation import selected_party
            members = selected_party(s, hero)
            option(8, 'party', 'Skład drużyny', detail=', '.join(training_hero(h).name for h in members))
        if progress and not completed:
            option(7, 'restart', 'Po kolei · od początku', detail='Rozpocznij nowy przebieg kursu.')
    elif view == 'party':
        from .confrontation import selected_party
        members = selected_party(s, hero)
        title = training_hero(hero).name + f' · skład drużyny {len(members)}/5'
        for index, h in enumerate(HERO_ORDER):
            if h != hero and (h in members or len(members) < 5):
                option(5 + index, 'member:' + h, training_hero(h).name, completed=h in members,
                       detail='Usuń z drużyny' if h in members else 'Dodaj do drużyny')
    else:
        view = 'cases'
        title = training_hero(hero).name + ' · ' + subject_name + ' · ćwiczenia'
        if exploring:
            from dnd_board_game.scenarios.confrontation import lessons_for
            from .confrontation import read_store, lesson_completed
            store = read_store(s)
            course = [(lesson.id, lesson.name, 'Rozmowa z NPC' if lesson.kind == 'npc' else 'Obiekt')
                      for lesson in lessons_for(hero)]
        else:
            course = [(step.id, step.name, 'Podstawy many' if step.ability.category == 'tutorial' else 'Podbicie' if step.boost_id else 'Zdolność') for step in steps(hero)]
            course.extend((('duel', 'Samodzielny pojedynek', 'Walka'), ('trap', 'Pułapka w walce', 'Wykrywanie i dezaktywacja')))
        pages = (len(course) + PAGE_SIZE - 1) // PAGE_SIZE
        page = max(0, min(int(_read(s, 'page', 0)), pages - 1))
        for index, (case_id, name, category) in enumerate(course[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]):
            completed = (lesson_completed(store, hero, case_id) if exploring else
                         bool(scene_flag(s.state.flags, 'trap_lesson_done_' + hero if case_id == 'trap' else f'walkthrough_charge_case_{hero}_{case_id}', False)))
            option(5 + index, 'case:' + case_id, name, detail=category, completed=completed)
        if page:
            option(27, 'previous', 'Poprzednia strona')
        if page + 1 < pages:
            option(26, 'next', 'Następna strona')
    option(29, 'back', 'Menu główne' if view == 'heroes' else 'Wybór postaci' if view == 'subjects' else 'Wybór działu' if view == 'modes' else 'Wybór trybu')
    return dict(view=view, subject=subject, hero_id=hero, title=title, page=page, pages=pages, options=options,
                revision=s.board_selection_revision)


def board_target(s: ExplorationUiSession) -> BoardScanTarget:
    from .exploration_app import BoardScanTarget
    options = payload(s)['options']
    slots = tuple(o['slot'] for o in options)
    return BoardScanTarget(positions=tuple(panel_position(slot) for slot in slots),
        feedback=panel_feedback(tuple(slot for slot in slots if slot < 26),
                                control_slots=tuple(slot for slot in slots if slot >= 26)),
        empty_message='Wybierz podświetloną runę. −/+ zmienia stronę listy; ↩ wraca.')


def select_position(s: ExplorationUiSession, position: Coordinate) -> dict[str, object]:
    menu = payload(s)
    option = next((o for o in menu['options'] if panel_position(o['slot']) == position), None)
    if option is None:
        raise ValueError('Wybierz podświetloną opcję samouczka.')
    return command(s, dict(action=option['action'], revision=menu['revision']))


def command(s: ExplorationUiSession, data: dict[str, object]) -> dict[str, object]:
    from .training_arena import roster_active
    from .training_walkthrough import start
    if not roster_active(s):
        raise ValueError('Najpierw wróć do wyboru ćwiczenia.')
    menu = payload(s)
    if data.get('revision') != menu['revision']:
        raise ValueError('Ten wybór samouczka nie jest już aktualny.')
    action = str(data.get('action', ''))
    if action not in {o['action'] for o in menu['options']}:
        raise ValueError('Ta opcja nie jest dostępna w bieżącym menu.')
    hero = str(menu['hero_id'])
    subject = str(menu['subject'])
    if action.startswith('hero:'):
        _write(s, hero=action.removeprefix('hero:'), view='subjects')
    elif action.startswith('subject:'):
        show_modes(s, hero, action.removeprefix('subject:'))
    elif action == 'party':
        _write(s, hero=hero, view='party', subject=subject)
    elif action.startswith('member:'):
        from .confrontation import selected_party, set_party
        members = selected_party(s, hero)
        member = action.removeprefix('member:')
        set_party(s, hero, tuple(h for h in members if h != member) if member in members else (*members, member))
        _write(s, hero=hero, view='party', subject=subject)
    elif action in {'sequence', 'restart'}:
        if subject == 'exploration':
            from .exploration_mana import start_course
            return start_course(s, hero, reset_progress=action == 'restart')
        return start(s, hero, reset_progress=action == 'restart')
    elif action.startswith('case:'):
        case_id = action.removeprefix('case:')
        if subject == 'exploration':
            from .exploration_mana import start_course
            return start_course(s, hero, case_id=case_id)
        if case_id == 'trap':
            from .training_arena import start_training_trial
            return start_training_trial(s, hero, 'traps', 'humanoid')
        return start(s, hero, case_id=case_id)
    elif action == 'cases':
        _write(s, hero=hero, view='cases', subject=subject)
    elif action in {'previous', 'next'}:
        _write(s, hero=hero, view='cases', page=int(menu['page']) + (1 if action == 'next' else -1), subject=subject)
    elif menu['view'] == 'heroes':
        from .launcher_board import begin
        begin(s)
        return {'navigate': '/'}
    else:
        parent = {'cases': 'modes', 'party': 'modes', 'modes': 'subjects', 'subjects': 'heroes'}[menu['view']]
        _write(s, hero=hero if parent != 'heroes' else '', view=parent, subject=subject)
    s._sync_board_leds()
    return s.state_payload()

"""Party-confrontation transport, training and physical-board presentation."""
from __future__ import annotations
from dataclasses import replace
import json
from typing import TYPE_CHECKING, Any
from uuid import uuid4
from types import SimpleNamespace
from dnd_board_game.rules import confrontation as rules
from dnd_board_game.rules.pooled_mana import COLORS
from dnd_board_game.rules.exploration_mana_catalog import HEROES, COLOR_NAMES
from dnd_board_game.scenarios.confrontation import lessons_for, lesson_by_id, scene_by_id, passives, REMINDER
from dnd_board_game.combat.scene import scene_flag, set_scene_flag
from dnd_board_game.world import Coordinate

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession

KEY = 'exploration_mana_party_v1'


def read_store(s: ExplorationUiSession) -> dict[str, Any]:
    raw = scene_flag(s.state.flags, KEY, '')
    data = json.loads(str(raw)) if raw else dict(version=1, revision=0, active=False, current=None, completed=[], sequence_progress={})
    if data.get('version') != 1:
        raise ValueError('Nieobsługiwana wersja konfrontacji drużynowej.')
    current = data.get('current')
    if current and current.get('roll_rules_version', 1) < 2:
        from dnd_board_game.application.confrontation import build
        actors = {str(a.id): a for a in s.exploration.actors}
        state = current['state']
        fresh = build(tuple(actors[p['id']] for p in state['participants']), current['scene'])
        for index, participant in enumerate(fresh.participants):
            previous = state['participants'][index]
            delta = participant.test_modifier - previous['test_modifier']
            if index == state['turn'] and state['stage'] == 'check':
                state['check_modifier'] += delta
            previous['test_modifier'] = participant.test_modifier
            previous['test_components'] = list(participant.test_components)
        current['roll_rules_version'] = 2
    return data


def active(s: ExplorationUiSession) -> bool:
    return bool(read_store(s)['active'])


def write(s: ExplorationUiSession, store: dict[str, Any]) -> None:
    store['revision'] += 1
    s.state = replace(s.state, flags=set_scene_flag(s.state.flags, KEY, json.dumps(store, ensure_ascii=False)))
    s.board_panel_context = None
    s.board_selection_revision += 1
    s._sync_board_leds()


def selected_party(s: ExplorationUiSession, hero: str) -> tuple[str, ...]:
    saved = scene_flag(s.state.flags, 'training_menu_party_' + hero, '')
    if saved:
        chosen = tuple(json.loads(str(saved)))
        if hero in chosen and 1 <= len(chosen) <= 5 and len(set(chosen)) == len(chosen) and all(h in HEROES for h in chosen):
            return (hero, *(h for h in chosen if h != hero))
    index = HEROES.index(hero)
    return (hero, HEROES[(index + 1) % 7], HEROES[(index + 2) % 7])


def set_party(s: ExplorationUiSession, hero: str, members: tuple[str, ...]) -> None:
    if hero not in members or not 1 <= len(members) <= 5 or len(set(members)) != len(members) or any(h not in HEROES for h in members):
        raise ValueError('Wybierz 1–5 bohaterów, w tym wybranego prowadzącego.')
    s.state = replace(s.state, flags=set_scene_flag(s.state.flags, 'training_menu_party_' + hero, json.dumps(members)))


def lesson_completed(store: dict[str, Any], hero: str, lesson: str) -> bool:
    return hero + ':' + lesson in store['completed']


def _launch(s: ExplorationUiSession, store: dict[str, Any], hero: str, lesson_id: str, mode: str,
            members: tuple[str, ...]) -> None:
    from .training_arena import training_hero
    from dnd_board_game.application.confrontation import build
    from dnd_board_game.application.exploration_flow import ExplorationFlowStage
    lesson = lesson_by_id(hero, lesson_id)
    if lesson.id == 'support' and len(members) < 2:
        raise ValueError('Ćwiczenie pomocy wymaga co najmniej dwóch bohaterów.')
    scene = scene_by_id(lesson.scene)
    saved = [(k, v) for k, v in s.state.flags.values if k.startswith(('walkthrough_', 'training_completed_', 'training_tutorial_done_', 'exploration_mana_', 'trap_lesson_done_', 'training_menu_party_'))]
    actors = tuple(replace(training_hero(h), position=Coordinate(9, 18)) for h in members)
    fixed = s._fixed_session_id
    s._fixed_session_id = s.observer.session_id
    try:
        s.configure_custom_party(actors)
    finally:
        s._fixed_session_id = fixed
    flags = s.state.flags
    for key, value in (*saved, ('training_mode', 'exploration'), ('training_requested', True), ('training_hero', hero)):
        flags = set_scene_flag(flags, key, value)
    s.state = replace(s.state, flags=flags, party_position=replace(s.state.party_position, marker_position=Coordinate(9, 18)))
    s.pending_encounter = None
    s.ui_flow_stage = ExplorationFlowStage.LOCATION_ACTIVE
    store['active'] = True
    store['current'] = dict(hero=hero, lesson=lesson_id, mode=mode, members=list(members), token=uuid4().hex,
                            scene=scene, state=build(actors, scene).to_data(), committed=False, roll_rules_version=2)
    s._exploration_mana_confirmed = store['current']['token']


def start_course(s: ExplorationUiSession, hero: str, *, case_id: str | None = None, reset_progress: bool = False) -> dict[str, object]:
    from .training_arena import roster_active
    from .exploration_mana import read_store as legacy_store
    if not roster_active(s) or active(s) or legacy_store(s)['active'] or hero not in HEROES:
        raise ValueError('Wróć do wyboru ćwiczeń eksploracji.')
    store = read_store(s)
    course = lessons_for(hero)
    mode = 'single' if case_id is not None else 'sequence'
    if case_id is None:
        index = int(store['sequence_progress'].get(hero, 0))
        if reset_progress or index >= len(course):
            index = 0
            store['sequence_progress'][hero] = 0
        case_id = course[index].id
    if case_id == 'support' and len(selected_party(s, hero)) < 2:
        raise ValueError('Ćwiczenie pomocy wymaga towarzysza. Dodaj go w wyborze składu drużyny.')
    _launch(s, store, hero, case_id, mode, selected_party(s, hero))
    write(s, store)
    return s.state_payload()


def _leave(s: ExplorationUiSession, store: dict[str, Any]) -> None:
    from .training_arena import training_hero
    from .training_menu import show_cases, show_modes
    current = store['current']
    saved = [(k, v) for k, v in s.state.flags.values if k.startswith(('walkthrough_', 'training_completed_', 'training_tutorial_done_', 'exploration_mana_', 'trap_lesson_done_', 'training_menu_party_'))]
    s.configure_custom_party((training_hero(current['hero']),))
    flags = s.state.flags
    for key, value in saved:
        flags = set_scene_flag(flags, key, value)
    s.state = replace(s.state, flags=flags)
    store['active'] = False
    if current['mode'] == 'single':
        index = next(i for i, l in enumerate(lessons_for(current['hero'])) if l.id == current['lesson'])
        show_cases(s, current['hero'], index, 'exploration')
    else:
        show_modes(s, current['hero'], 'exploration')


def _complete(store: dict[str, Any], state: rules.Confrontation) -> None:
    current = store['current']
    if state.stage != 'result' or current['committed']:
        return
    lesson = lesson_by_id(current['hero'], current['lesson'])
    fulfilled = {'support': state.used_support, 'charge': state.reached_charge, 'reaction': state.reacted,
                 'drain': state.mana.phase == 'drain', 'compromise': state.outcome in {'compromise', 'success'},
                 'favor': state.obligation, 'color_goal': state.goal and state.outcome == 'success'}.get(lesson.focus, state.outcome in {'success', 'compromise'})
    current['committed'] = True
    current['completed'] = fulfilled
    if fulfilled:
        key = current['hero'] + ':' + lesson.id
        if key not in store['completed']:
            store['completed'].append(key)
        if current['mode'] == 'sequence':
            store['sequence_progress'][current['hero']] = next(i for i, l in enumerate(lessons_for(current['hero'])) if l.id == lesson.id) + 1


def command(s: ExplorationUiSession, data: dict[str, Any]) -> dict[str, object]:
    store = read_store(s)
    if type(data.get('revision')) is not int or data['revision'] != store['revision']:
        raise ValueError('To polecenie jest nieaktualne.')
    action = data.get('action')
    if (store.get('current') or {}).get('mode') == 'mission' and action in {'next','leave'}:
        from .mission_zero import finish_confrontation
        current = store['current']
        if not store['active']:
            raise ValueError('Konfrontacja jest już zamknięta.')
        if action == 'next':
            if current['state']['stage'] != 'result':
                raise ValueError('Najpierw zakończ konfrontację.')
            store['active'] = False
            write(s, store)
            finish_confrontation(s, current)
        else:
            store['active'] = False
            write(s, store)
        return s.state_payload()
    if action == 'open':
        return start_course(s, str(data.get('hero', '')), case_id=str(data.get('lesson', 'npc')))
    if not store['active'] or not store['current']:
        raise ValueError('Nie trwa konfrontacja.')
    current = store['current']
    state = rules.Confrontation.from_data(current['state'])
    confirmed = getattr(s, '_exploration_mana_confirmed', '') == current['token']
    if action == 'leave':
        _leave(s, store)
    elif action == 'retry':
        _launch(s, store, current['hero'], current['lesson'], current['mode'], tuple(current['members']))
    elif action == 'resume':
        if confirmed or state.stage in {'introduction', 'setup', 'result'} or data.get('stacks_preserved') is not True:
            raise ValueError('Potwierdź zachowanie fizycznych stosów, aby wznowić.')
        s._exploration_mana_confirmed = current['token']
    elif not confirmed and state.stage not in {'introduction', 'setup', 'result'}:
        raise ValueError('Najpierw potwierdź zachowane stosy lub powtórz próbę.')
    elif action == 'next':
        if state.stage != 'result':
            raise ValueError('Najpierw zakończ konfrontację.')
        course = lessons_for(current['hero'])
        index = next(i for i, l in enumerate(course) if l.id == current['lesson'])
        if current['mode'] == 'single' or (current.get('completed') and index + 1 == len(course)):
            _leave(s, store)
        else:
            target = course[index + 1].id if current.get('completed') else current['lesson']
            _launch(s, store, current['hero'], target, current['mode'], tuple(current['members']))
    else:
        if action == 'acknowledge' and state.stage == 'introduction':
            state = replace(state, stage='setup')
        elif action == 'acknowledge' and state.stage == 'setup':
            from dnd_board_game.application.confrontation import prepare_lesson
            state = prepare_lesson(rules.shuffle(state), current['lesson'])
            s._exploration_mana_confirmed = current['token']
        elif action == 'color':
            state = rules.report_color(state, str(data.get('color', '')))
        elif action == 'take':
            state = rules.take(state, data.get('index'))
        elif action == 'test':
            state = rules.declare(state, data.get('bonus'))
        elif action == 'support':
            state = rules.support(state, str(data.get('target', '')))
        elif action == 'roll':
            rolls = data.get('rolls', [])
            if not isinstance(rolls, list) or len(rolls) != 1:
                raise ValueError('Podaj jeden naturalny wynik kości.')
            state = rules.roll_check(state, rolls[0]) if state.stage == 'check' else rules.roll_impact(state, rolls[0])
        elif action == 'advance':
            state = rules.advance(state)
        elif action == 'react':
            # NPC's die is rolled once on the server; persisted result cannot reroll on refresh.
            state = rules.react(state, s.encounter_rng.randint(1, 4))
        elif action == 'compromise':
            if current.get('compromise_declined'):
                raise ValueError('Oferta kompromisu została już odrzucona.')
            state = rules.compromise(state)
        elif action == 'favor':
            state = rules.favor(state)
        else:
            raise ValueError('Nieznane działanie konfrontacji.')
        old=rules.Confrontation.from_data(current['state'])
        if current['mode']=='mission' and action in {'test','support'} and old.stage=='turn' and old.condition=='compromise' and old.resistance*2<=old.maximum:
            current['compromise_declined']=True
        current['state'] = state.to_data()
        if state.obligation:
            store.setdefault('obligations', {})[current['token']] = dict(hero=current['hero'], scene=current['scene']['id'], text='Dostarcz list Nessy.', fulfilled=False)
        if state.outcome:
            store.setdefault('outcomes', {})[current['token']] = dict(scene=current['scene']['id'], outcome=state.outcome, goal=state.goal, sensitive=state.sensitive, obligation=state.obligation)
        if current['mode'] != 'mission':
            _complete(store, state)
        s._record('party_confrontation_action', dict(action=action, hero=state.actor.id, round=state.round,
                  resistance=state.resistance, stage=state.stage, outcome=state.outcome))
    write(s, store)
    return s.state_payload()


def payload(s: ExplorationUiSession) -> dict[str, Any]:
    from .exploration_mana_board import choice
    store = read_store(s)
    if not store['active']:
        return dict(model='party_confrontation', active=False, revision=store['revision'])
    current = store['current']
    scene = current['scene']
    if current['mode'] == 'mission':
        from .mission_zero import scene as mission_scene
        scene = mission_scene(s, current['mission_scene'])
        lesson = SimpleNamespace(id=current['lesson'], name=scene['name'], instruction=scene['goal'])
    else:
        lesson = lesson_by_id(current['hero'], current['lesson'])
    state = rules.Confrontation.from_data(current['state'])
    pool = state.mana
    needs_resume = getattr(s, '_exploration_mana_confirmed', '') != current['token'] and state.stage not in {'introduction', 'setup', 'result'}
    options = []
    if needs_resume:
        options.append(choice(28, 'resume', 'Potwierdzam zachowane stosy', stacks_preserved=True))
    elif state.stage in {'introduction', 'setup'}:
        options.append(choice(28, 'acknowledge', 'Przygotuj planszę' if state.stage == 'introduction' else 'Potwierdź figurkę i przetasowaną talię'))
    elif state.stage == 'result':
        options.append(choice(28, 'next', 'Wróć do misji' if current['mode'] == 'mission' else 'Wybór ćwiczenia' if current['mode'] == 'single' else 'Następne ćwiczenie' if current.get('completed') else 'Powtórz ćwiczenie'))
    elif pool.phase in {'reveal', 'burn'}:
        for i, color in enumerate(COLORS):
            # Full physical conservation validation also happens in the pure engine.
            known = (*pool.deck, *pool.offer, *pool.burned, *pool.expired, *(c for _, h in (*pool.pools, *pool.prisons) for c in h))
            if pool.deck[0] == color or (pool.deck[0] is None and known.count(color) < pool.copies):
                options.append(choice(13 + i, 'color', COLOR_NAMES[i], color=color))
    elif pool.phase == 'choose':
        options.extend(choice(6+i, 'take', f'Weź {COLOR_NAMES[COLORS.index(c)]} · {pool.point_values(state.actor.id)[c]} pkt', index=i) for i,c in enumerate(pool.offer))
    elif state.stage == 'turn':
        options.extend(choice(18 + i, 'test', f'Test: mana +{bonus}, spal {cost}', bonus=bonus) for i, (_, bonus, cost) in enumerate(rules.TIERS) if any(t[1] == bonus for t in rules.available_tiers(state)))
        options.extend(choice(6+HEROES.index(p.id), 'support', f'Pomóż: {p.name} (+{max(2+state.passive(state.actor.id,"support"),dict(state.aids).get(p.id,0))})', target=p.id) for p in state.participants if p.id != state.actor.id)
        if state.condition == 'compromise' and state.resistance * 2 <= state.maximum and not current.get('compromise_declined'):
            options.append(choice(24, 'compromise', 'Przyjmij kompromis'))
        if state.condition == 'favor' and not state.obligation and pool.burned:
            options.append(choice(25, 'favor', 'Przyjmij zobowiązanie · odzyskaj kartę'))
    elif state.stage in {'after_action', 'after_reaction'}:
        options.append(choice(28, 'advance', 'Przejdź dalej'))
    elif state.stage == 'reaction':
        options.append(choice(28, 'react', 'Rozstrzygnij reakcję sytuacji'))
    from dnd_board_game.scenarios.mission_pack import read_json
    mission_ui=read_json(s._scenario_asset_root(),'text/ui.json') if current['mode']=='mission' else None
    options.append(choice(29,'leave',mission_ui['leave_confrontation'] if mission_ui else 'Wróć do wyboru'))
    rolling = state.stage in {'check', 'impact'} and not needs_resume
    modifier = state.check_modifier if state.stage == 'check' else state.impact_modifier
    die = 20 if state.stage == 'check' else state.actor.die
    result = scene.get(state.outcome, '') if state.outcome else ''
    if state.outcome == 'success' and state.condition == 'color_goal' and state.goal:
        result += ' Nessa ujawnia dodatkową informację o trasie.'
    if state.outcome == 'success' and state.condition == 'sensitive' and state.sensitive:
        result += ' Poznaliście nazwiska; Nessa wycofuje prywatną pomoc.'
    preparation = []
    if lesson.id in {'charge', 'reaction'}:
        values = pool.point_values(state.actor.id)
        high, low = max(values, key=values.get), min(values, key=values.get)
        count = 2 if lesson.id == 'charge' else 3
        preparation = [f'Ćwiczenie zaczyna się z przygotowanym ładunkiem: połóż {count} karty koloru {COLOR_NAMES[COLORS.index(high)]} w puli {state.actor.name}.']
        if lesson.id == 'charge':
            preparation.append(f'Wyłóż ofertę: {COLOR_NAMES[COLORS.index(high)]}, {COLOR_NAMES[COLORS.index(low)]}. Pozostałe karty przetasuj jako talię.')
        else:
            preparation.append('Pozostałe karty przetasuj jako talię. Zaczynamy od reakcji sytuacji w rundzie 2.')
    elif lesson.id == 'drain':
        preparation = ['Zostaw w talii tylko 3 karty: od góry czerwona, biała, niebieska. Wszystkie pozostałe połóż w spalonych. To końcówka konfrontacji.']
    return dict(model='party_confrontation', active=True, revision=store['revision'], phase=state.stage,
        scene={**scene, 'position':scene.get('position',[9,17])}, setup=dict(position=scene.get('party_position',[9,18]),preparation=preparation), lesson=dict(id=lesson.id,name=lesson.name,objective=lesson.instruction),
        mission_ui=mission_ui,
        run_mode=current['mode'], hero=current['hero'], round=state.round, actor=state.actor.id, actor_name=state.actor.name,
        method=state.actor.method, dc=state.actor.dc, impact_die=state.actor.die,
        color_passives={c: info['label'] for c, info in passives(state.actor.id).items()},
        resistance=state.resistance, maximum=state.maximum, outcome=state.outcome, result=result,
        last=state.last, last_total=state.last_total, last_impact=state.last_impact,
        mana=dict(phase=pool.phase, reason=pool.reason, deck=len(pool.deck), burned=len(pool.burned), copies=pool.copies,
                  offer=list(pool.offer), pending=pool.pending_count, points=pool.points(state.actor.id)),
        party=[dict(id=p.id,name=p.name,method=p.method,dc=p.dc,die=p.die,points=pool.points(p.id),
                    ability=p.ability,test_modifier=p.test_modifier,influence_modifier=p.impact_modifier,
                    cards=list(pool.hand(p.id)),values=pool.point_values(p.id),aid=dict(state.aids).get(p.id,0),
                    passives=[dict(color=c,label=info['label'],count=pool.hand(p.id).count(c)) for c,info in passives(p.id).items() if c in pool.hand(p.id)]) for p in state.participants],
        reaction=scene['reactions'][(state.round-1)%len(scene['reactions'])]['name'], pressure=state.pressure,
        needs_resume=needs_resume, obligation=state.obligation, completed=current.get('completed',False),
        board_choices=options, reminder=REMINDER, die_kind='test' if state.stage == 'check' else 'influence',
        attempt=dict(phase='roll',actor=state.actor.name,method=state.actor.method,busted=False,dice_count=1,die=die,
                     modifier_total=modifier,modifiers=([dict(label=label,value=value) for label,value in state.actor.test_components] +
                        [dict(label='Mana, pasywy i pomoc',value=modifier-state.actor.test_modifier)] if state.stage=='check' else
                        [dict(label=state.actor.ability,value=state.actor.impact_modifier),dict(label='Pasywy wpływu',value=modifier-state.actor.impact_modifier)])) if rolling else {})

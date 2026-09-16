"""Exploration lesson transport. All card and check decisions use the shared engine."""
from __future__ import annotations

from dataclasses import asdict, replace
import json
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from dnd_board_game.actors import Actor
from dnd_board_game.application.exploration_mana_outcomes import resolve_outcome
from dnd_board_game.application.exploration_mana_flow import check_request, method_modifiers, resolve_attempt
from dnd_board_game.application.recruitment_arena import ARENA_ID
from dnd_board_game.combat.scene import scene_flag, set_scene_flag
from dnd_board_game.core.player_labels_pl import ABILITY_LABELS_PL
from dnd_board_game.rules.exploration_mana import (
    ManaAttempt, answer_bargain, set_favor, accept_failure, choose_color, declare_draw, next_value, request_reroll, stand,
)
from dnd_board_game.rules.exploration_mana_catalog import (
    COLORS, COLOR_NAMES, HEROES, REMINDER, hero_methods, method_by_id, obstacle_description, profile_values,
)
from dnd_board_game.scenarios.exploration_mana import lesson_by_id, lessons_for, scene_for, scene_by_id, scene_from_data, ManaScene
from dnd_board_game.world import Coordinate

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession, BoardScanTarget

STORE_KEY = "exploration_mana_store"
HERO_POSITION = Coordinate(9, 18)
COMMON_LESSONS = frozenset({'stand', 'exact', 'bust', 'repeat', 'after_red', 'four', 'condition_compromise', 'condition_sensitive_topic', 'condition_color_goal', 'condition_favor'})


def lesson_completed(store: dict[str, Any], hero: str, lesson_id: str) -> bool:
    return (f'{hero}:{lesson_id}' in store['completed'] or
            (lesson_id in COMMON_LESSONS and f'common:{lesson_id}' in store['completed']))


def read_store(s: ExplorationUiSession) -> dict[str, Any]:
    raw = scene_flag(s.state.flags, STORE_KEY, "")
    if not raw:
        return {"version": 2, "revision": 0, "active": False, "current": None, "completed": [], "outcomes": {}, "obligations": {}}
    data = json.loads(str(raw))
    if type(data.get("version")) is not int or data["version"] not in (1, 2):
        raise ValueError("Nieobsługiwana wersja kursu eksploracji.")
    if data['version'] == 1:
        data['version'] = 2
        current = data.get('current')
        if current:
            current['scene_data'] = asdict(scene_by_id(current['scene']))
            current['scene_data']['condition'] = {'kind': 'none'}
            if current.get('attempt'):
                current['attempt'] = ManaAttempt.from_data(current['attempt']).to_data()
        for outcome in data['outcomes'].values():
            outcome.setdefault('kind', 'success' if outcome['success'] else 'failure')
            outcome.setdefault('flags', [outcome['flag']])
            outcome.setdefault('followups', [])
    data.setdefault('obligations', {})
    return data


def _scene(current: dict[str, Any]) -> ManaScene:
    return scene_from_data(current['scene_data']) if current.get('scene_data') else scene_by_id(current['scene'])


def active(s: ExplorationUiSession) -> bool:
    from .confrontation import active as party_active
    if party_active(s):
        return True
    return s.exploration.scenario_id == ARENA_ID and read_store(s)["active"]


def rolling(s: ExplorationUiSession) -> bool:
    from .confrontation import active as party_active, payload as party_payload
    if party_active(s):
        return party_payload(s).get('attempt', {}).get('phase') == 'roll'
    if not active(s):
        return False
    current = read_store(s).get('current') or {}
    return (current.get('attempt') or {}).get('phase') == 'roll'


def write_store(s: ExplorationUiSession, store: dict[str, Any]) -> None:
    store["revision"] += 1
    flags = set_scene_flag(s.state.flags, STORE_KEY, json.dumps(store, ensure_ascii=False))
    s.state = replace(s.state, flags=flags)
    s.board_panel_context = None
    s.board_selection_revision += 1
    s._sync_board_leds()


def _actor(s: ExplorationUiSession, method_id: str) -> Actor:
    hero = method_by_id(method_id).hero_id
    for actor in s._party_actors():
        if str(actor.id) == hero:
            return actor
    raise ValueError("Bohater przypisany do tej metody nie uczestniczy w próbie.")


def _launch(s: ExplorationUiSession, store: dict[str, Any], hero: str, lesson_id: str, *, run_mode: str = "legacy") -> None:
    from .training_arena import training_hero
    from dnd_board_game.application.exploration_flow import ExplorationFlowStage
    if s.exploration.scenario_id != ARENA_ID or hero not in HEROES:
        raise ValueError("Wybierz bohatera na arenie Nessy.")
    if s.combat_state is not None and s.combat_state.status.value != "finished":
        raise ValueError("Najpierw zakończ ćwiczenie walki albo wróć do wyboru postaci.")
    if s.pending_encounter is not None:
        raise ValueError("Najpierw zakończ przygotowanie bieżącej walki.")
    lesson = lesson_by_id(hero, lesson_id)
    scene = scene_by_id(lesson.scene_id) if lesson.scene_id else scene_for(lesson.kind)
    saved = [(k, v) for k, v in s.state.flags.values
             if k.startswith(("training_completed_", "training_tutorial_done_", "walkthrough_", "exploration_mana_", "trap_lesson_done_"))]
    members = (hero, *(h for h in HEROES if h != hero))[:3] if lesson.practice else (hero,)
    fixed = s._fixed_session_id
    s._fixed_session_id = s.observer.session_id
    try:
        s.configure_custom_party(tuple(replace(training_hero(h), position=Coordinate(9, 18 + i))
                                       for i, h in enumerate(members)))
    finally:
        s._fixed_session_id = fixed
    flags = s.state.flags
    for key, value in (*saved, ("training_mode", "exploration"), ("training_requested", True), ("training_hero", hero)):
        flags = set_scene_flag(flags, key, value)
    s.state = replace(s.state, flags=flags)
    s.pending_encounter = None
    s.ui_flow_stage = ExplorationFlowStage.LOCATION_ACTIVE
    store["active"] = True
    store["current"] = dict(hero=hero, lesson=lesson_id, run_mode=run_mode, scene=scene.id, phase="introduction",
                            attempt=None, token=uuid4().hex, setup_index=0, committed=False, scene_data=asdict(scene), check_dc=lesson.dc or scene.dc, debrief_done=[], debrief_message="")


def start_legacy_course(s: ExplorationUiSession, hero: str, *, case_id: str | None = None,
                 reset_progress: bool = False) -> dict[str, object]:
    from .training_arena import roster_active
    if not roster_active(s) or active(s) or hero not in HEROES:
        raise ValueError('Wróć do wyboru ćwiczeń eksploracji.')
    store = read_store(s)
    course = lessons_for(hero)
    run_mode = 'sequence' if case_id is None else 'single'
    if case_id is None:
        progress = store.setdefault('sequence_progress', {})
        index = int(progress.get(hero, 0))
        if reset_progress or index >= len(course):
            index = 0
            progress[hero] = 0
        case_id = course[index].id
    _launch(s, store, hero, case_id, run_mode=run_mode)
    write_store(s, store)
    return s.state_payload()


def start_course(s: ExplorationUiSession, hero: str, *, case_id: str | None = None,
                 reset_progress: bool = False) -> dict[str, object]:
    from .confrontation import start_course as start_party
    return start_party(s, hero, case_id=case_id, reset_progress=reset_progress)


def _return_to_menu(s: ExplorationUiSession, store: dict[str, Any]) -> None:
    from .training_arena import training_hero
    from .training_menu import show_cases, show_modes
    current = store['current']
    hero, mode = current['hero'], current.get('run_mode', 'legacy')
    saved = [(k, v) for k, v in s.state.flags.values
             if k.startswith(('walkthrough_', 'training_completed_', 'training_tutorial_done_',
                              'exploration_mana_', 'trap_lesson_done_'))]
    s.configure_custom_party((training_hero(hero),))
    flags = s.state.flags
    for key, value in saved:
        flags = set_scene_flag(flags, key, value)
    s.state = replace(s.state, flags=flags)
    store['active'] = False
    if mode == 'single':
        index = next(i for i, lesson in enumerate(lessons_for(hero)) if lesson.id == current['lesson'])
        show_cases(s, hero, index, 'exploration')
    elif mode == 'sequence':
        show_modes(s, hero, 'exploration')


def _commit(s: ExplorationUiSession, store: dict[str, Any], attempt: ManaAttempt) -> None:
    current = store["current"]
    if attempt.phase != "result" or current["committed"]:
        return
    lesson = lesson_by_id(current["hero"], current["lesson"])
    scene = _scene(current)
    option = next(o for o in scene.options if o.method_id == attempt.method_id)
    current["committed"] = True
    # Training is a sandbox: consequences are persistent within this exercise, not campaign rewards.
    store["outcomes"][current["token"]] = resolve_outcome(attempt, option)
    fulfilled = ((lesson.finish != "exact" or attempt.end_reason == "exact")
                 and (lesson.finish != "bust" or attempt.busted)
                 and (lesson.finish != "limit" or attempt.end_reason == "limit")
                 and (lesson.finish != "reroll" or attempt.reroll_used)
                 and (lesson.finish != "proposal" or attempt.proposal_status in {"accepted", "declined"}))
    if fulfilled:
        key = f"{current['hero']}:{lesson.id}"
        if key not in store["completed"]:
            store["completed"].append(key)
        if lesson.id in COMMON_LESSONS and f'common:{lesson.id}' not in store['completed']:
            store['completed'].append(f'common:{lesson.id}')
        # The own-method lesson can also be satisfied through a guided basics exercise.
        method = method_by_id(attempt.method_id)
        if method.hero_id == current["hero"]:
            own_key = f"{current['hero']}:{method.kind}"
            if own_key not in store["completed"]:
                store["completed"].append(own_key)
    if fulfilled and current.get('run_mode') == 'sequence':
        index = next(i for i, item in enumerate(lessons_for(current['hero'])) if item.id == lesson.id)
        store.setdefault('sequence_progress', {})[current['hero']] = index + 1
    current["lesson_completed"] = fulfilled
    s._record("exploration_mana_resolved", dict(attempt_id=attempt.id, method=attempt.method_id,
              target=scene.id, success=attempt.success, total=attempt.total, busted=attempt.busted))


def command(s: ExplorationUiSession, data: dict[str, Any]) -> dict[str, object]:
    from .confrontation import active as party_active, command as party_command
    if party_active(s) or data.get('model') == 'party_confrontation':
        return party_command(s, data)
    store = read_store(s)
    if type(data.get("revision")) is not int or data["revision"] != store["revision"]:
        raise ValueError("To polecenie jest nieaktualne. Użyj bieżącego widoku próby.")
    action = data.get("action")
    if action == "open":
        if store["active"]:
            raise ValueError("Najpierw zakończ lub opuść bieżącą lekcję.")
        current = store.get("current")
        hero, lesson_id = str(data.get("hero", "")), str(data.get("lesson", "npc"))
        if current and current["hero"] == hero and current["lesson"] == lesson_id and not current["committed"]:
            if s.combat_state is not None or s.pending_encounter is not None:
                raise ValueError("Najpierw zakończ ćwiczenie walki.")
            _launch(s, store, hero, lesson_id)
            store["current"] = current
            s._exploration_mana_confirmed = ""
        else:
            _launch(s, store, hero, lesson_id)
        write_store(s, store)
        return s.state_payload()
    if not active(s) or not store.get("current"):
        raise ValueError("Nie trwa lekcja eksploracji.")
    current = store["current"]
    lesson = lesson_by_id(current["hero"], current["lesson"])
    scene = _scene(current)
    attempt = ManaAttempt.from_data(current["attempt"]) if current["attempt"] else None
    if action == "leave":
        _return_to_menu(s, store)
    elif action in {"retry", "next"}:
        mode = current.get('run_mode', 'legacy')
        target = lesson.id
        if action == "next":
            if not current['committed']:
                raise ValueError('Najpierw rozstrzygnij ćwiczenie.')
            course = lessons_for(current['hero'])
            index = next(i for i, item in enumerate(course) if item.id == lesson.id)
            if mode == 'single' or (mode == 'sequence' and current.get('lesson_completed') and index + 1 == len(course)):
                _return_to_menu(s, store)
                write_store(s, store)
                return s.state_payload()
            if mode == 'sequence':
                target = course[index + 1].id if current.get('lesson_completed') else lesson.id
            else:
                target = next((l.id for l in course if not lesson_completed(store, current['hero'], l.id)), 'practice_npc')
        _launch(s, store, current['hero'], target, run_mode=mode)
    elif action == "acknowledge":
        if current["phase"] == "introduction":
            current["phase"] = "setup"
        elif current["phase"] == "setup":
            current["setup_index"] += 1
            if current["setup_index"] >= len(s._party_actors()) + 2:
                current["phase"] = "scene"
        else:
            raise ValueError("To objaśnienie już się zakończyło.")
    elif action == "start":
        if current["phase"] != "scene" or attempt is not None:
            raise ValueError("Nie można ponownie rozpocząć tej próby.")
        method_id = str(data.get("method", ""))
        actor = _actor(s, method_id)
        if not lesson.practice and str(actor.id) != current["hero"]:
            raise ValueError("Ta lekcja ćwiczy metodę wybranej postaci.")
        option = next((o for o in scene.options if o.method_id == method_id), None)
        if option is None:
            raise ValueError("Ten cel nie obsługuje wybranej metody.")
        attempt = ManaAttempt(current["token"], scene.id, method_id,
                              profile_values(lesson.profile or option.profile), lesson.obstacle or option.obstacle, condition=scene.condition)
        current["phase"] = "attempt"
        current["attempt"] = attempt.to_data()
        s._exploration_mana_confirmed = attempt.id
    elif action == "resume":
        if attempt is None or data.get("stacks_preserved") is not True:
            raise ValueError("Potwierdź zachowanie fizycznej talii, puli i odrzuconych. Pomieszane stosy wymagają jawnego powtórzenia lekcji.")
        s._exploration_mana_confirmed = attempt.id
    elif action == 'debrief':
        if attempt is None or attempt.phase != 'result':
            raise ValueError('Najpierw zakończ rozmowę.')
        followup = next((f for f in _followups(store, current) if f['id'] == data.get('id')), None)
        if followup is None or followup['id'] in current.get('debrief_done', []):
            raise ValueError('Ta możliwość nie jest dostępna.')
        current.setdefault('debrief_done', []).append(followup['id'])
        current['debrief_message'] = followup['message']
        outcome = store['outcomes'][current['token']]
        outcome.setdefault('effects', list(outcome.get('flags', []))).append(followup['flag'])
        if followup['id'] == 'deliver_letter':
            store['obligations'][current['token']]['fulfilled'] = True
    else:
        if attempt is None:
            raise ValueError("Najpierw rozpocznij próbę.")
        if attempt.phase in {"offer", "decision"} and getattr(s, "_exploration_mana_confirmed", "") != attempt.id:
            raise ValueError("Potwierdź stan fizycznych stosów przed wznowieniem doboru.")
        if action == 'accept_bargain':
            attempt = answer_bargain(attempt, accept=True)
        elif action == 'decline_bargain':
            if getattr(s, '_exploration_mana_confirmed', '') != attempt.id:
                raise ValueError('Potwierdź zachowane stosy przed powrotem do doboru.')
            attempt = answer_bargain(attempt, accept=False)
        elif action in {'arm_favor', 'cancel_favor'}:
            attempt = set_favor(attempt, armed=action == 'arm_favor')
        elif action == "choose":
            color = str(data.get("color", ""))
            if lesson.choices and ((len(attempt.colors) >= len(lesson.choices) and not lesson.open_after_preparation) or (len(attempt.colors) < len(lesson.choices) and color != lesson.choices[len(attempt.colors)])):
                raise ValueError("W tej przygotowanej lekcji wybierz wskazany kolor.")
            attempt = choose_color(attempt, color)
        elif action == "draw":
            if lesson.choices and not lesson.open_after_preparation and len(attempt.colors) == len(lesson.choices):
                raise ValueError("W tym ćwiczeniu teraz spasuj.")
            attempt = declare_draw(attempt)
        elif action in {"stand", "empty"}:
            if lesson.choices and (len(attempt.colors) < len(lesson.choices) or (not lesson.open_after_preparation and len(attempt.colors) != len(lesson.choices))):
                raise ValueError("Najpierw wykonaj przygotowane wybory tej lekcji.")
            attempt = stand(attempt, empty_deck=action == "empty")
        elif action == "roll":
            rolls = data.get("rolls", [])
            if not isinstance(rolls, list):
                raise ValueError("Wpisz wyniki kości.")
            attempt = resolve_attempt(_actor(s, attempt.method_id), attempt, current.get("check_dc", lesson.dc or scene.dc),
                                      tuple(rolls), improvisation_available=not attempt.reroll_used)
        elif action == "reroll":
            attempt = request_reroll(attempt)
        elif action == "accept":
            if lesson.finish == "reroll":
                raise ValueError("W tej lekcji użyj Improwizacji; drugi wynik będzie ostateczny.")
            attempt = accept_failure(attempt)
        else:
            raise ValueError("Nieznane polecenie eksploracji.")
        current["attempt"] = attempt.to_data()
        if attempt.favor_status == 'used':
            store['obligations'].setdefault(attempt.id, dict(text=scene.obligation, fulfilled=False))
        _commit(s, store, attempt)
    write_store(s, store)
    return s.state_payload()


def _followups(store: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    result = list(store['outcomes'].get(current['token'], {}).get('followups', []))
    obligation = store['obligations'].get(current['token'])
    if obligation:
        result.append(dict(id='deliver_letter', label='Przejdź do zadania z listem',
            message='Nessa zapisuje dodatkową drogę do obozu uchodźców. W ćwiczeniu przechodzicie tę odnogę i dostarczacie list. Zobowiązanie wykonane.', flag='letter_delivered'))
    return result


def payload(s: ExplorationUiSession) -> dict[str, Any] | None:
    from .confrontation import active as party_active, payload as party_payload
    if party_active(s):
        return party_payload(s)
    if s.exploration.scenario_id != ARENA_ID:
        return None
    store = read_store(s)
    result: dict[str, Any] = dict(active=store["active"], revision=store["revision"], completed=store["completed"],
                                 reminder=REMINDER, heroes=[dict(id=h, trap_completed=bool(scene_flag(s.state.flags, 'trap_lesson_done_'+h, False)), lessons=[dict(id=l.id, name=l.name,
                                 completed=lesson_completed(store, h, l.id)) for l in lessons_for(h)]) for h in HEROES])
    if not store["active"]:
        return result
    current = store["current"]
    lesson = lesson_by_id(current["hero"], current["lesson"])
    scene = _scene(current)
    mode = current.get('run_mode', 'legacy')
    course = lessons_for(current['hero'])
    index = next(i for i, item in enumerate(course) if item.id == lesson.id)
    next_label = ('Wybór ćwiczenia' if mode == 'single' else
                  'Powtórz ćwiczenie' if mode == 'sequence' and current.get('committed') and not current.get('lesson_completed') else
                  'Kurs ukończony · wybór trybu' if mode == 'sequence' and index + 1 == len(course) else 'Następne ćwiczenie')
    result.update(run_mode=mode, course_index=index, course_total=len(course), next_label=next_label,
                  leave_label='Wybór ćwiczenia' if mode == 'single' else 'Wybór trybu' if mode == 'sequence' else 'Wybór postaci · zachowaj postęp')
    result.update(hero=current["hero"], lesson=dict(id=lesson.id, name=lesson.name, finish=lesson.finish,
                  narration=lesson.narration, objective=lesson.objective), phase=current["phase"],
                  condition=dict(**asdict(scene.condition), title=scene.condition_title, description=scene.condition_text),
                  scene=dict(name=scene.name, description=scene.description, position=list(scene.position), kind=scene.kind))
    members = s._party_actors()
    setup_steps = [dict(text=f"Ustaw figurkę {a.name} na polu {a.position.as_tuple()}.", position=list(a.position.as_tuple())) for a in members]
    setup_steps += [dict(text=f"Ustaw {'figurkę Ireny' if scene.kind == 'npc' else 'znacznik skrzyni'} na polu {scene.position}.", position=list(scene.position)),
                    dict(text="Zbierz wszystkie 25 kart many (po 5 każdego koloru). Usuń rynek walki. " +
                         ("Ułóż poniższe oferty w podanej kolejności od góry talii; reszta kart pod spodem. To jawnie przygotowane ćwiczenie." if lesson.offers else "Przetasuj talię. Obok zostaw miejsce na pulę wybraną i odrzucone."), position=[])]
    result["setup"] = setup_steps[min(current["setup_index"], len(setup_steps) - 1)]
    result["prepared_offers"] = [list(o) for o in lesson.offers]
    result["options"] = []
    for option in scene.options:
        method = method_by_id(option.method_id)
        actor = next((a for a in members if str(a.id) == method.hero_id), None)
        allowed = actor is not None and (lesson.practice or method.hero_id == current["hero"])
        result["options"].append(dict(id=method.id, name=method.name, hero=method.hero_id,
            ability=ABILITY_LABELS_PL[method.ability], enabled=allowed, description=option.description, cost=option.cost,
            obstacle=obstacle_description(lesson.obstacle or option.obstacle)[1],
            modifiers=[dict(label=m.label, value=m.value) for m in method_modifiers(actor, method)] if allowed else []))
    from .exploration_mana_board import choices
    if not current["attempt"]:
        result["board_choices"] = choices(result)
        return result
    attempt = ManaAttempt.from_data(current["attempt"])
    request = check_request(_actor(s, attempt.method_id), attempt)
    option = next(o for o in scene.options if o.method_id == attempt.method_id)
    outcome = store['outcomes'].get(current['token'], {})
    result['followups'] = [dict(**f, completed=f['id'] in current.get('debrief_done', [])) for f in _followups(store, current)]
    result['debrief_message'] = current.get('debrief_message', '')
    result['obligation'] = store['obligations'].get(current['token'])
    result["attempt"] = dict(phase=attempt.phase, total=attempt.total, bonus=attempt.bonus, busted=attempt.busted,
        method=method_by_id(attempt.method_id).name, actor=_actor(s, attempt.method_id).name,
        cards=[dict(color=c, value=v) for c, v in zip(attempt.colors, attempt.amounts)],
        values=[dict(color=c, name=n, base=v, value=next_value(attempt, c)) for c, n, v in zip(COLORS, COLOR_NAMES, attempt.values)],
        obstacle=dict(zip(("name", "description"), obstacle_description(attempt.obstacle))),
        modifiers=[dict(label=m.label, value=m.value) for m in request.modifiers],
        modifier_total=sum(m.value for m in request.modifiers), dice_count=2 if attempt.busted else 1,
        needs_resume=attempt.phase in {"offer", "decision", "bargain"} and getattr(s, "_exploration_mana_confirmed", "") != attempt.id,
        end_reason=attempt.end_reason, rolls=list(attempt.rolls), roll_total=attempt.roll_total,
        success=attempt.success, outcome_kind=attempt.outcome_kind, proposal_status=attempt.proposal_status,
        sensitive_used=attempt.sensitive_used, favor_status=attempt.favor_status, goal_met=attempt.goal_met,
        goal_progress=attempt.colors.count(attempt.condition.color), dc=current.get("check_dc", lesson.dc or scene.dc),
        outcome=(outcome.get('message', '') + ' ' + outcome.get('cost', '')).strip(),
        outcome_flags=outcome.get('effects', outcome.get('flags', [])),
        lesson_completed=current.get("lesson_completed", False),
        offer=list(lesson.offers[len(attempt.colors)]) if attempt.phase == "offer" and len(attempt.colors) < len(lesson.offers) else [],
        expected_color=lesson.choices[len(attempt.colors)] if attempt.phase == "offer" and len(attempt.colors) < len(lesson.choices) else "",
        must_draw=bool(lesson.choices and len(attempt.colors) < len(lesson.choices)),
        must_stand=bool(lesson.choices and not lesson.open_after_preparation and len(attempt.colors) >= len(lesson.choices)))
    result["board_choices"] = choices(result)
    return result


def scan_target(s: ExplorationUiSession) -> BoardScanTarget:
    from .exploration_mana_board import scan_target as target
    return target(s)


def select_position(s: ExplorationUiSession, position: Coordinate) -> dict[str, object]:
    from .exploration_mana_board import select_position as select
    return select(s, position)

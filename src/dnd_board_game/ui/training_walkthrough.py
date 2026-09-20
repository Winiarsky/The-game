"""Guided arena transitions. Lessons use real actions and isolated fresh encounters."""
from __future__ import annotations

from dataclasses import replace
import random
from typing import TYPE_CHECKING
from uuid import uuid4

from dnd_board_game.application.recruitment_arena import ARENA_ID, HERO_ORDER
from dnd_board_game.application.training_walkthrough import TrainingStep
from dnd_board_game.scenarios.character_text import load_text, tutorial_steps as steps
from dnd_board_game.actors import Faction
from dnd_board_game.combat.context_menu import CombatMenuAction
from dnd_board_game.combat.scene import scene_flag, set_scene_flag
from dnd_board_game.combat.session import current_actor, combat_winner
from .board_panel_symbols import ability_panel_slot, panel_icon

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession
    from dnd_board_game.combat.context_menu import CombatMenuOption




def enabled(s: ExplorationUiSession) -> bool:
    return s.exploration.scenario_id == ARENA_ID and scene_flag(s.state.flags, 'training_mode', '') == 'walkthrough'


def flag(s: ExplorationUiSession, key: str, default: object = '') -> object:
    return scene_flag(s.state.flags, 'walkthrough_' + key, default)


def put(s: ExplorationUiSession, **values: object) -> None:
    flags = s.state.flags
    for key, value in values.items():
        flags = set_scene_flag(flags, 'walkthrough_' + key, value)
    s.state = replace(s.state, flags=flags)


def hero_id(s: ExplorationUiSession) -> str:
    return str(scene_flag(s.state.flags, 'training_hero', 'garran'))


def current_step(s: ExplorationUiSession) -> TrainingStep | None:
    course = steps(hero_id(s))
    index = int(flag(s, 'index', 0))
    return course[index] if 0 <= index < len(course) else None


def exercising(s: ExplorationUiSession) -> bool:
    return enabled(s) and flag(s, 'phase') == 'exercise' and current_step(s) is not None


def single_case(s: ExplorationUiSession) -> bool:
    return flag(s, 'run_mode', 'sequence') == 'single'


def complete_step(s: ExplorationUiSession) -> None:
    step = current_step(s)
    if step is None:
        return
    flags = set_scene_flag(s.state.flags, f'walkthrough_charge_case_{hero_id(s)}_{step.id}', True)
    if not single_case(s):
        flags = set_scene_flag(flags, f'walkthrough_charge_progress_{hero_id(s)}', int(flag(s, 'index', 0)) + 1)
    s.state = replace(s.state, flags=flags)


def start(s: ExplorationUiSession, hero: str, *, reset_progress: bool = False, case_id: str | None = None) -> dict[str, object]:
    if s.exploration.scenario_id != ARENA_ID or hero not in HERO_ORDER:
        raise ValueError('Wybierz bohatera samouczka na arenie.')
    if s.combat_state is not None and s.combat_state.status.value != 'finished':
        raise ValueError('Najpierw zakończ bieżące ćwiczenie albo wróć do wyboru postaci.')
    if s.pending_encounter is not None and s.combat_state is None:
        raise ValueError('Najpierw zakończ przygotowanie bieżącej próby.')
    if case_id is not None:
        course = steps(hero)
        ids = [step.id for step in course] + ['duel']
        if case_id not in ids:
            raise ValueError('Nie ma takiego ćwiczenia dla wybranej postaci.')
        return launch(s, hero, ids.index(case_id), single=True)
    index = 0 if reset_progress else int(scene_flag(s.state.flags, f'walkthrough_charge_progress_{hero}', 0))
    if scene_flag(s.state.flags, f'walkthrough_charge_completed_{hero}', False):
        index = 0
    return launch(s, hero, min(index, len(steps(hero))))


def launch(s: ExplorationUiSession, hero: str, index: int, *, show_introduction: bool = True, single: bool = False) -> dict[str, object]:
    from .training_arena import training_hero
    from dnd_board_game.application.exploration_flow import ExplorationFlowStage
    saved = [(k, v) for k, v in s.state.flags.values if k.startswith(('training_completed_', 'training_tutorial_done_', 'walkthrough_progress_', 'walkthrough_completed_', 'walkthrough_pool_', 'walkthrough_charge_', 'walkthrough_terrain_ready', 'walkthrough_intro_seen', 'exploration_mana_', 'trap_lesson_done_'))]
    # Reset also cancels the old board reader and drops all pending action flows.
    fixed_id = s._fixed_session_id
    s._fixed_session_id = s.observer.session_id
    try:
        s.configure_custom_party((training_hero(hero),))
    finally:
        s._fixed_session_id = fixed_id
    flags = s.state.flags
    for key, value in (*saved, ('training_mode', 'walkthrough'), ('training_hero', hero),
                       ('training_creature_type', 'humanoid'), ('training_requested', True)):
        flags = set_scene_flag(flags, key, value)
    s.state = replace(s.state, flags=flags)
    put(s, run_mode='single' if single else 'sequence', index=index, phase='introduction' if show_introduction else 'setup', token=uuid4().hex, paid=False, charge_pending_ability='')
    s.ui_flow_stage = ExplorationFlowStage.LOCATION_ACTIVE
    s._refresh_pending_encounter()
    s.pending_encounter = replace(s.pending_encounter, precombat_stealth_completed=True)
    s._add_message('Nessa · samouczek', load_text()['tutorial']['intro'] if index == 0 else 'Kolejne ćwiczenie: usuń poprzednie kukły i pomocników. Ustaw figurki zgodnie z podświetleniem; teren pozostaje bez zmian.')
    s.start_encounter_setup()
    from dnd_board_game.combat import SetupStep, SetupStepKind
    from dnd_board_game.hardware.led_palette import LedColor
    flow = s.encounter_setup_flow
    figurines = tuple(step for step in flow.steps if step.kind in {SetupStepKind.ACTORS, SetupStepKind.ENEMIES})
    if flag(s, 'terrain_ready', False):
        flow.steps = (SetupStep(kind=SetupStepKind.ENVIRONMENT, label='Przygotowanie nowej sytuacji', positions=(),
                               color=LedColor.PLAYER_START_ZONE,
                               message='Zdejmij poprzednie kukły, pomocników i przywołane istoty. Teren zostaje. ✓ rozpoczyna ustawianie nowej sytuacji.'), *figurines)
    else:
        # The introduction replaces the generic "start combat" setup message.
        terrain = tuple(step for step in flow.steps[1:] if step.kind == SetupStepKind.ENVIRONMENT)
        flow.steps = (*terrain, *figurines)
    flow.current_index = 0
    s._sync_board_leds()
    return s.state_payload()


def after_setup(s: ExplorationUiSession) -> None:
    if not enabled(s) or flag(s, 'phase') != 'setup':
        return
    put(s, phase='briefing', terrain_ready=True)
    if current_step(s) is not None:
        # Exercises have a controlled turn order; the final duel rolls initiative normally.
        s.start_encounter_initiative()
        s.submit_encounter_initiative_roll(20)
    s.board_panel_context = None
    s.board_selection_revision += 1


def initialize_combat(s: ExplorationUiSession) -> None:
    if not enabled(s) or current_step(s) is None:
        return
    from dnd_board_game.combat.class_features import resolve_rage
    from dnd_board_game.combat.stealth import HiddenState
    from dnd_board_game.combat.conditions import ConditionState, CombatCondition
    step = current_step(s)
    state = s.combat_state
    order = state.initiative_order
    index = next(i for i, e in enumerate(order.entries) if str(e.actor.id) == hero_id(s))
    state = replace(state, initiative_order=replace(order, current_index=index))
    if state.shared_mana:
        state = replace(state, shared_mana=replace(state.shared_mana, turn_actor=hero_id(s)))
    s.combat_state = state
    if hero_id(s) == 'brakka' and not step.ability.id.startswith('pool_') and step.ability.id not in {'rage', 'reckless_attack', 'shoulder_check'}:
        result = resolve_rage(state, s.active_combat_effects)
        s.active_combat_effects = result.active_effects
        # Prerequisite is supplied by the lesson, leaving the real action budget intact.
    if step.ability.id == 'shadow_verdict':
        s.combat_state = replace(state, hidden_states=(HiddenState(hero_id(s), 30,
            tuple(str(a.id) for a in state.actors if a.faction == Faction.ENEMY)),))
    if step.ability.id == 'lesser_restoration':
        s.combat_state = replace(s.combat_state, condition_states=(ConditionState(
            actor_id='recruitment_helper', condition=CombatCondition.POISONED,
            source_label='Zatrucie przygotowane do ćwiczenia'),))
    if step.ability.id == 'mana_recovery' and s.combat_state.shared_mana.pooled is None:
        mana = s.combat_state.shared_mana
        s.combat_state = replace(s.combat_state, shared_mana=replace(mana, deck=17, discard=3))


def notice_id(s: ExplorationUiSession) -> str:
    if not enabled(s) or flag(s, 'phase') not in {'introduction', 'briefing', 'success', 'retry', 'final_result'}:
        return ''
    if flag(s, 'phase') == 'introduction':
        return f"walkthrough:{flag(s, 'token')}:{flag(s, 'index')}:introduction"
    mana = s.combat_state.shared_mana if s.combat_state else None
    pool_setup = mana is not None and mana.pooled is not None and mana.phase.value == 'pooled'
    if (s._combat_has_pending_resolution() and not pool_setup) or s.shared_mana_declaration is not None:
        return ''
    if s.combat_targeting_attack_source_id or s.combat_targeting_class_feature_action_id:
        return ''
    return f"walkthrough:{flag(s, 'token')}:{flag(s, 'index')}:{flag(s, 'phase')}"


def acknowledge(s: ExplorationUiSession, token: str) -> dict[str, object]:
    if not token or token != notice_id(s):
        raise ValueError('To objaśnienie nie jest już aktualne.')
    phase, step = flag(s, 'phase'), current_step(s)
    if phase == 'introduction':
        put(s, phase='setup', intro_seen=True)
        s.board_panel_context = None
        s.board_selection_revision += 1
        s._sync_board_leds()
        return s.state_payload()
    if phase == 'final_result':
        return leave(s)
    if phase == 'success':
        if single_case(s):
            return leave(s)
        return launch(s, hero_id(s), int(flag(s, 'index', 0)) + 1)
    if phase == 'retry':
        return launch(s, hero_id(s), int(flag(s, 'index', 0)), single=single_case(s))
    put(s, phase='exercise' if step else 'final')
    s.board_panel_context = None
    s.board_selection_revision += 1
    if step is None:
        return s.start_encounter_initiative()
    if step.ability.timing == 'R' and (s.combat_state.shared_mana.pooled is None or s.combat_state.shared_mana.pooled.phase == 'ready'):
        order = s.combat_state.initiative_order
        index = next(i for i, e in enumerate(order.entries) if e.actor.faction == Faction.ENEMY)
        s.combat_state = replace(s.combat_state, initiative_order=replace(order, current_index=index))
        return s.resolve_enemy_turn()
    s._sync_board_leds()
    return s.state_payload()


def payment_error(s: ExplorationUiSession, ability_id: str, boosts: dict[str, int]) -> str:
    if not exercising(s):
        return ''
    step = current_step(s)
    # Multi-action resolutions can legitimately dispatch internal sources.
    if s.combat_state.shared_mana.phase.value == 'resolving':
        return ''
    if ability_id != step.ability.id:
        return f'Teraz ćwiczymy: {step.ability.name}. Wybierz wskazaną umiejętność.'
    if {k: v for k, v in boosts.items() if v} != step.boosts:
        return ('Wybierz wskazaną runę podbicia (dwie dodatkowo spalone karty).' if step.boost_id
                else 'W tym ćwiczeniu użyj zdolności bez podbicia.')
    return ''


def paid(s: ExplorationUiSession, ability_id: str, boosts: dict[str, int]) -> None:
    if exercising(s) and ability_id == current_step(s).ability.id:
        put(s, paid=True, paid_boosts=boosts,
            before=[{'id': str(a.id), 'hp': a.hp, 'position': list(a.position.as_tuple())} for a in s.combat_state.actors])


def record_ability(s: ExplorationUiSession, ability_id: str, actor: str) -> None:
    if not exercising(s) or actor != hero_id(s) or ability_id != current_step(s).ability.id or not flag(s, 'paid', False):
        return
    if s.combat_state.shared_mana.pooled.phase != 'ready':
        put(s, charge_pending_ability=ability_id)
        return
    step = current_step(s)
    if flag(s, 'paid_boosts', {}) != step.boosts:
        return
    success = True
    if ability_id in {'shield_bash', 'shoulder_check'}:
        before = {a['id']: a for a in flag(s, 'before', [])}
        success = any(a.faction == Faction.ENEMY and str(a.id) in before
                      and list(a.position.as_tuple()) != before[str(a.id)]['position'] for a in s.combat_state.actors)
    if ability_id == 'hide':
        success = any(h.actor_id == actor for h in s.combat_state.hidden_states)
    if ability_id == 'counterattack_command':
        success = not s.combat_state.shared_mana.command_skipped
    put(s, phase='success' if success else 'retry', paid=False)
    if success:
        complete_step(s)
    s._record('walkthrough_step_resolved', {'hero_id': actor, 'step_id': step.id, 'success': success})
    s.board_selection_revision += 1


def filter_options(s: ExplorationUiSession, options: tuple[CombatMenuOption, ...]) -> tuple[CombatMenuOption, ...]:
    if not enabled(s) or current_step(s) is None:
        return options
    if flag(s, 'phase') != 'exercise':
        return ()
    from dnd_board_game.combat.context_menu import CombatMenuAction as A
    step = current_step(s)
    if step.ability.id == 'pool_hold':
        from dnd_board_game.rules.shared_mana_catalog import CATALOG
        paid_ids = {a.id for a in CATALOG}
        return tuple(o for o in options if o.action in {A.SELECT_ATTACK_SOURCE, A.MOVE, A.ATTACK, A.EQUIP_AND_ATTACK}
                     and (o.source_id or '') not in paid_ids)
    mana = s.combat_state.shared_mana
    if mana and mana.phase.value == 'resolving':
        return tuple(o for o in options if not mana.command_step or o.action != A.END_TURN)
    return tuple(o for o in options if o.source_id == step.ability.id or o.action_id == step.ability.id
                 or (step.ability.id == 'hide' and o.action == A.HIDE)
                 or (step.ability.category == 'item' and o.action in {A.OPEN_ITEM_MENU, A.SELECT_ITEM_ACTION})
                 or (step.ability.timing == 'R' and o.action == A.END_TURN))


def leave(s: ExplorationUiSession, *, retry: bool = False, choose_case: bool = False) -> dict[str, object]:
    if not enabled(s):
        raise ValueError('Nie trwa prowadzony samouczek.')
    # These are isolated training encounters: an explicit restart/exit also
    # cancels unfinished dice, payment and board input via configure_custom_party.
    if retry:
        return launch(s, hero_id(s), int(flag(s, 'index', 0)), single=single_case(s))
    won = bool(current_step(s) is None and s.combat_state and s.combat_state.status.value == 'finished'
               and combat_winner(s.combat_state) == Faction.ALLY)
    was_single, selected_hero, selected_index = single_case(s), hero_id(s), int(flag(s, 'index', 0))
    if won and was_single:
        s.state = replace(s.state, flags=set_scene_flag(s.state.flags, f'walkthrough_charge_case_{selected_hero}_duel', True))
    if won and not was_single:
        s.state = replace(s.state, flags=set_scene_flag(s.state.flags, f'walkthrough_charge_completed_{hero_id(s)}', True))
    saved = [(k, v) for k, v in s.state.flags.values if k.startswith(('walkthrough_progress_', 'walkthrough_completed_', 'walkthrough_pool_', 'walkthrough_charge_', 'walkthrough_terrain_ready', 'walkthrough_intro_seen', 'exploration_mana_', 'trap_lesson_done_'))]
    from .training_arena import training_hero
    s.configure_custom_party((training_hero(hero_id(s)),))
    flags = s.state.flags
    for key, value in saved:
        flags = set_scene_flag(flags, key, value)
    s.state = replace(s.state, flags=flags)
    if was_single or choose_case:
        from .training_menu import show_cases
        show_cases(s, selected_hero, selected_index)
    else:
        from .training_menu import show_modes
        show_modes(s, selected_hero)
    s._sync_board_leds()
    return s.state_payload()


def exercise_instruction(s: ExplorationUiSession, step: TrainingStep, fallback: str) -> str:
    """Guide the next input without changing selection or payment semantics."""
    if not exercising(s):
        return fallback
    declaration = s.shared_mana_declaration
    if declaration is not None and declaration.stage == 'payment':
        error = payment_error(s, declaration.ability_id, declaration.boosts)
        if s.combat_state.shared_mana.pooled is not None:
            from dnd_board_game.scenarios.pooled_mana_catalog import pool_ability
            payment = ('Potwierdź niebieskim ✓; ta zdolność nie zużywa many.'
                       if pool_ability(declaration.ability_id, declaration.actor_id).free else
                       'Zachowaj ładunek. Zatwierdź użycie przez ✓; po efekcie zgłoś kolory spalonych kart.')
            return (error + ' ' if error else '') + payment
        if error:
            return error + ' Następnie odłóż pokazany koszt i naciśnij niebieskie ✓.'
        return 'Odłóż pokazany koszt many na stos odrzuconych. Naciśnij niebieskie ✓, aby wykonać zdolność.'
    if s._combat_has_pending_resolution():
        return fallback
    option = next((o for o in s._combat_turn_action_options()
                   if o.id == s.combat_turn_preview_option_id), None)
    if option is not None and option.action == CombatMenuAction.CLASS_FEATURE and option.action_id == step.ability.id:
        return (f'Wybrano „{step.ability.name}”. Naciśnij niebieskie ✓, aby przejść do kosztu many. '
                'Runa wybiera zdolność; ✓ zatwierdza wybór.')
    return fallback


def payload(s: ExplorationUiSession) -> dict[str, object]:
    hero = hero_id(s)
    step = current_step(s)
    phase = str(flag(s, 'phase'))
    index, total = int(flag(s, 'index', 0)), len(steps(hero))
    lesson = None
    if step:
        boost = next((b for b in step.ability.boosts if b.id == step.boost_id), None)
        instruction = f'Użyj zdolności „{step.ability.name}”' + (f' i wybierz podbicie: {boost.label} (+2 spalone karty).' if boost else ' bez podbicia.')
        if step.ability.timing == 'R':
            instruction = 'W tej lekcji wynik ataku kukły jest przygotowany, aby uruchomić reakcję. Po ✓ kukła rozpocznie atak. W oknie reakcji wybierz „' + step.ability.name + '”. Reakcja nie zużywa many; potwierdź ją i rozstrzygnij atak.'
        if step.ability.id == 'garran_guard_companion':
            instruction = 'Po ✓ kukła zaatakuje pomocnika. W oknie Osłony towarzysza naciśnij ✓; reakcja nie zużywa many. Garran przejmie trafienie i 6 obrażeń; pomocnik pozostanie bezpieczny.'
        preparation = ''
        if hero == 'brakka' and step.ability.id not in {'rage', 'reckless_attack', 'shoulder_check'}:
            preparation = 'Na potrzeby tej sytuacji Brakka już jest w Szale. '
        if step.ability.id == 'shadow_verdict':
            preparation = 'Mira zaczyna ukryta przed kukłą, a pomocnik zapewnia jej własną flankę. '
        lesson = dict(id=step.id, narration_id=f'{hero}:{step.id}', name=step.name, cost=list(step.ability.payment(step.boosts)),
                      icon=panel_icon(24 if step.ability.category == 'tutorial' else 3 if step.ability.category == 'item' else ability_panel_slot(hero, step.ability.id)),
                      explanation=step.ability.full_description,
                      instruction=exercise_instruction(s, step, instruction),
                      narration=preparation + narration_content()[hero][step.ability.id] + (f' Teraz powtórz zdolność z dodatkową maną: {boost.label}. Wybierz odpowiadającą jej runę w oknie kosztu.' if boost else ''),
                      boost_cost=["*", "*"] if boost else [])
    if lesson and step:
        from .pooled_mana_training import preparation as pool_preparation
        from dnd_board_game.scenarios.pooled_mana_catalog import requirement_text, ability_description
        if step.ability.category == 'tutorial':
            lesson.update(cost=[], instruction=step.ability.description)
        else:
            lesson.update(cost=[], explanation=requirement_text(step.ability.id, hero) + " " + ability_description(hero, step.ability.id),
                          narration=pool_preparation(s) + " " + lesson["narration"],
                          instruction=exercise_instruction(s, step, instruction))
    notice = None
    token = notice_id(s)
    if token:
        notice = dict(lesson or dict(name='Samodzielny pojedynek', cost=[], icon='',
            explanation='Kukła: 30 PW, KP 13, ruch 30 ft, jeden atak wręcz +3, obrażenia 1k6. Pokonaj ją, używając poznanych zdolności.',
            instruction='Odzyskujesz pełne PW. Zbierz komplet podany w panelu many i przetasuj. Pule są puste; dobór poniżej 6 kart na początku twojej tury. Kukła co drugą rundę spala dwie karty po trafieniu.',
            narration='Teraz wybory należą do ciebie. Potwierdź przygotowanie kart; następnie rzucimy na inicjatywę.'))
        notice.update(id=token, phase=phase, button='✓ Wykonaj ćwiczenie' if phase == 'briefing' and step else '✓ Rozpocznij pojedynek' if phase == 'briefing' else '✓ Następna sytuacja' if phase == 'success' else '✓ Przygotuj ponowną próbę')
        if phase == 'introduction':
            notice.update(intro=load_text()['tutorial']['intro'] if not flag(s, 'intro_seen', False) else '',
                instruction='Naciśnij ✓, aby przejść do ustawiania figurek. Teren pozostaje na miejscu.'
                    if flag(s, 'terrain_ready', False) else 'Naciśnij ✓, aby rozpocząć przygotowanie planszy. Każdy element ustawimy osobno.',
                button='✓ Przejdź do ustawiania')
        elif phase == 'briefing':
            notice.update(narration='Plansza jest przygotowana. Teraz wykonaj ćwiczenie.' if step else
                'Plansza jest przygotowana. Potwierdź gotowość do rzutu na inicjatywę.', explanation='')
            if step and step.ability.id in {'garran_shield_wall', 'iron_bastion'}:
                notice['narration'] += ' Przygaszone pola pokazują zasięg aury, turkusowe figurki — jej odbiorców, a biała figurka — Garrana. Podgląd nie nadaje jeszcze efektu.'
            if step and step.ability.id in {'bless', 'divine_care_aura', 'victory_hymn'}:
                recipients = 'złote figurki — wrogów objętych karą' if step.ability.id == 'divine_care_aura' else 'turkusowe figurki — sojuszników objętych premią'
                notice['narration'] += f' Przygaszone pola pokazują zasięg aury, {recipients}. Biała figurka to źródło aury. Podgląd nie nadaje jeszcze efektu.'
        if phase == 'final_result':
            won = combat_winner(s.combat_state) == Faction.ALLY
            notice.update(name='Samouczek ukończony' if won else 'Spróbuj ponownie',
                narration='Kukła pokonana. Znasz już zdolności tej postaci i użyłeś ich w samodzielnej walce.' if won else 'To była próba. Ćwiczenia pozostają zaliczone; po wybraniu tej postaci wrócisz do pojedynku.',
                instruction='Wróć do wyboru trybu. Możesz powtórzyć kurs lub wybrać pojedyncze ćwiczenie.',
                explanation='', button='✓ Wybór trybu')
        if phase == 'success':
            notice['narration'] = 'Ćwiczenie zaliczone. Przygotujemy teraz kolejną sytuację.'
            notice['explanation'] = ''
            notice['instruction'] = 'Ćwiczenie zakończone. ✓ przygotuje następną sytuację.'
            if step.ability.id in {'garran_shield_wall', 'iron_bastion'}:
                notice['narration'] = ('Aura działa. Przygaszone pola wskazują jej zasięg, turkusowe figurki — odbiorców. '
                    + ('Sąsiedni sojusznicy mają +2 KP; Garran nie otrzymuje tej premii.' if step.ability.id == 'garran_shield_wall'
                       else 'Garran i sojusznicy w 10 ft mają premię KP równą modyfikatorowi jego Siły i ochronę przed przymusowym przesunięciem.'))
                if step.ability.id == 'iron_bastion':
                    bonus = next((e.value for e in s.active_combat_effects if e.kind == 'iron_bastion' and e.source_actor_id == 'garran'), None)
                    if bonus is not None:
                        notice['narration'] += f' Premia z tej aury: {bonus:+d} KP.'
            if step.ability.id == 'garran_guard_companion':
                notice['narration'] = 'Garran przejął atak wymierzony w pomocnika. Sprawdź wynik: obrażenia trafiły do Garrana, a PW pomocnika się nie zmieniły. Koszt i reakcja zostały zużyte.'
            if step.ability.id in {'bless', 'divine_care_aura', 'victory_hymn'}:
                recipients = 'Złote figurki to wrogowie objęci karą.' if step.ability.id == 'divine_care_aura' else 'Turkusowe figurki to sojusznicy objęci premią; źródło aury także korzysta z efektu.'
                notice['narration'] = f'Aura działa. Przygaszone pola pokazują jej aktualny zasięg. {recipients} Biała figurka wskazuje źródło. Po przestawieniu figurek zasięg i odbiorcy są aktualizowani. Utrata koncentracji kończy aurę.'
        elif phase == 'retry':
            notice['explanation'] = ''
            notice['narration'] = 'Próba nie przyniosła ćwiczonego efektu. To się zdarza przy rzutach. Odnowimy zasoby i odtworzymy ustawienie, aby spróbować ponownie.'
            notice['instruction'] = '✓ odnowi PW, manę i ustawienie tego ćwiczenia.'
            if step and step.ability.id == 'counterattack_command':
                notice['narration'] = 'Nie obie figurki wykonały atak. W Kontrataku zakończ ruch w zasięgu kukły albo zostań na polu startowym. Pudło zalicza atak; brak legalnego celu oznacza ponowienie próby.'
    if notice and single_case(s):
        if phase == 'introduction':
            notice['intro'] = 'Pojedyncze ćwiczenie. Przygotujemy potrzebne zasoby i warunki. Postęp kursu po kolei pozostaje zachowany.'
        if phase in {'success', 'final_result'}:
            notice['button'] = '✓ Wybór ćwiczenia'
            notice['instruction'] = '✓ wraca do listy. Możesz powtórzyć ten przypadek albo wybrać inny.'
            if phase == 'success':
                notice['narration'] = notice['narration'].replace('Przygotujemy teraz kolejną sytuację.', 'Możesz teraz wybrać kolejne ćwiczenie.')
            else:
                notice['name'] = 'Pojedynek wygrany' if combat_winner(s.combat_state) == Faction.ALLY else 'Koniec próby'
                notice['narration'] = 'Samodzielna próba zakończona. Postęp kursu po kolei pozostaje zachowany.'
    return dict(guided=True, run_mode='single' if single_case(s) else 'sequence', intro=load_text()['tutorial']['intro'], current=lesson, index=index, total=total,
                completed_count=index, complete=False, phase=phase, notice=notice,
                can_retry=True)


def synchronize(s: ExplorationUiSession) -> None:
    if enabled(s) and exercising(s) and s.combat_state is not None:
        from .pooled_mana_training import synchronize as synchronize_pool_lesson
        synchronize_pool_lesson(s)
    if not enabled(s) or flag(s, 'phase') != 'final' or s.combat_state is None:
        return
    defeated = any(str(a.id) == hero_id(s) and a.hp <= 0 for a in s.combat_state.actors)
    mana = s.combat_state.shared_mana
    if (defeated or s.combat_state.status.value == 'finished') and mana and mana.phase.value in {'end_turn', 'discard', 'refresh'}:
        from dnd_board_game.rules.shared_mana import ManaPhase
        # The duel is over; there is no next turn to refill or refresh cards for.
        s.combat_state = replace(s.combat_state, shared_mana=replace(mana, phase=ManaPhase.READY, end_turn_pending=False))
    if not s._combat_has_pending_resolution() and defeated:
        from dnd_board_game.combat.session import CombatStatus
        s.combat_state = replace(s.combat_state, status=CombatStatus.FINISHED)
    if s.combat_state.status.value == 'finished' and not s._combat_has_pending_resolution() and (not mana or not mana.pooled or mana.pooled.phase == 'ready'):
        put(s, phase='final_result')
        s.board_panel_context = None
        s.board_selection_revision += 1


def narration_content() -> dict[str, dict[str, str]]:
    data = {hid: h['tutorial'] for hid, h in load_text()['heroes'].items()}
    if set(data) != set(HERO_ORDER):
        raise ValueError('Narracja wymaga siedmiu bohaterów.')
    for hero in HERO_ORDER:
        if set(data[hero]) != {step.ability.id for step in steps(hero)}:
            raise ValueError(f'Niepełna narracja samouczka: {hero}.')
    return data


def enemy_rng(s: ExplorationUiSession) -> random.Random:
    # Explicit scripted teaching attack: first d20 is 10, matching the lesson's
    # attack modifier just above the hero's base AC. The final duel uses the normal RNG.
    if exercising(s) and current_step(s).ability.timing == 'R':
        return random.Random(23)
    return s.encounter_rng


def restore_setup(s: ExplorationUiSession) -> dict[str, object] | None:
    if enabled(s) and s.combat_state is None and flag(s, 'phase') in {'introduction', 'setup', 'briefing'}:
        return launch(s, hero_id(s), int(flag(s, 'index', 0)), show_introduction=flag(s, 'phase') == 'introduction', single=single_case(s))
    return None


def require_lesson_action(s: ExplorationUiSession, ability_id: str) -> None:
    if not enabled(s) or current_step(s) is None:
        return
    if flag(s, 'phase') != 'exercise':
        raise ValueError('Najpierw potwierdź objaśnienie Nessy przyciskiem ✓.')
    if s.combat_state.shared_mana.phase.value == 'resolving':
        return
    if current_step(s).ability.id == 'pool_hold' and ability_id.startswith('basic_attack:'):
        return
    if ability_id != current_step(s).ability.id:
        raise ValueError(f'Teraz ćwiczymy: {current_step(s).ability.name}.')

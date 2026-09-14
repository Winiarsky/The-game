"""Physical Athletics roll, automatic opponent, destination and boosted damage."""
from __future__ import annotations
from typing import TYPE_CHECKING
from dnd_board_game.combat.session import current_actor, replace_actor
from dnd_board_game.combat.class_features import resolve_shoulder_check, legal_shoulder_check_destinations
from dnd_board_game.actors import skill_modifier
from dnd_board_game.world import Coordinate

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession


def begin_shoulder(session: ExplorationUiSession) -> dict[str, object]:
    from .shared_mana import ManaDeclaration
    session.shared_mana_declaration = ManaDeclaration('shoulder_check', 'brakka', '',
        {'target_id': session.combat_selected_class_feature_target_id, 'shoulder_stage': 'contest'},
        boosts=dict(session.combat_state.shared_mana.pending_boosts), stage='effect_roll')
    session._sync_board_leds()
    return session.state_payload()


def resolve_shoulder_step(session: ExplorationUiSession, roll: int) -> dict[str, object]:
    declaration = session.shared_mana_declaration
    stage = declaration.resume_arguments['shoulder_stage']
    target = session._actor_by_string_id(declaration.resume_arguments['target_id'])
    actor = current_actor(session.combat_state)
    if stage == 'damage':
        from dnd_board_game.combat.damage import DamageComponentInput, DamageType, apply_damage_result, resolve_damage
        count = declaration.boosts.get('damage', 0)
        if type(roll) is not int or not count <= roll <= 6*count:
            raise ValueError(f'Wpisz sumę {count}k6 obrażeń podbicia.')
        applied = apply_damage_result(target, resolve_damage((DamageComponentInput(roll, DamageType.BLUDGEONING, 'Z bara: podbicie'),), target.damage_affinities))
        session.combat_state = replace_actor(session.combat_state, applied.actor_after)
        session.shared_mana_declaration = None
        session._maybe_prompt_concentration_check(applied)
        session._add_message('Z bara', f'{target.name}: {applied.damage.total_applied} obrażeń podbicia.')
    else:
        if type(roll) is not int or not 1 <= roll <= 20:
            raise ValueError('Podaj naturalny k20 testu Atletyki.')
        defender = session.encounter_rng.randint(1, 20)
        won = roll + skill_modifier(actor, 'athletics') > defender + skill_modifier(target, 'athletics')
        distance = 5 * (1 + declaration.boosts.get('push', 0)) if won else 0
        session.shared_mana_declaration = None
        session.brakka_shoulder_check_rolls = (roll, defender, distance)
        legal = legal_shoulder_check_destinations(session._active_encounter().board, session.combat_state, actor, target, distance_feet=distance)
        session.board_message = f'Z bara: {roll + skill_modifier(actor, "athletics")} przeciw {defender + skill_modifier(target, "athletics")}. ' + ('Wybierz pole odepchnięcia i zatwierdź.' if legal else 'Brak przesunięcia.')
        session._add_message('Sporny test Atletyki', session.board_message)
        if not legal:
            return finish_shoulder(session, None)
    session._sync_board_leds()
    return session.state_payload()


def finish_shoulder(session: ExplorationUiSession, destination: Coordinate | None) -> dict[str, object]:
    from .shared_mana import ManaDeclaration
    attacker, defender, _ = session.brakka_shoulder_check_rolls
    target_id = session.combat_selected_class_feature_target_id
    result = resolve_shoulder_check(session.combat_state, board=session._active_encounter().board,
        target_id=target_id, attacker_roll=attacker, defender_roll=defender, destination=destination)
    session.combat_state = result.state
    if result.push_distance_feet:
        from .shared_movement import apply_extra_movement
        apply_extra_movement(session, str(result.target_after.id), result.target_before.position, result.target_after.position)
    session.combat_targeting_class_feature_action_id = None
    session.combat_selected_class_feature_target_id = None
    session.brakka_shoulder_check_rolls = ()
    session.brakka_shoulder_check_destination = None
    boosts = dict(session.combat_state.shared_mana.pending_boosts)
    if result.attacker_total > result.defender_total and boosts.get('damage', 0):
        session.shared_mana_declaration = ManaDeclaration('shoulder_check', 'brakka', '', {'target_id': target_id, 'shoulder_stage': 'damage'}, boosts=boosts, stage='effect_roll')
    session._add_message('Z bara', f'Test {result.attacker_total} przeciw {result.defender_total}; przesunięcie {result.push_distance_feet} ft.')
    session._sync_board_leds()
    return session.state_payload()

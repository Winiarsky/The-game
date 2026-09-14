"""Aura footprints and recipients, projected from the real membership rules."""
from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import replace

from dnd_board_game.combat.shared_mana_features import AURA_ABILITIES, support_aura_preview
from dnd_board_game.combat.session import current_actor
from dnd_board_game.combat.spells import grid_distance_feet
from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.world import Coordinate

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession


def aura_feedback(session: ExplorationUiSession, ability_id: str | None, source_id: str = 'garran', *,
                  active_only: bool = False, boosts: dict[str, int] | None = None) -> LedFeedback:
    # Movement/control options have no ability id. Do not build a hypothetical
    # mana declaration for them, especially while a paid technique is resolving.
    if not ability_id or ability_id not in dict(AURA_ABILITIES):
        return LedFeedback()
    state = session.combat_state
    encounter = session._active_encounter()
    if state is None or encounter is None:
        return LedFeedback()
    action = next((a for a in encounter.combat_actions_by_actor.get(source_id, ()) if a.id == ability_id), None)
    mana = state.shared_mana
    if boosts is not None and mana is not None:
        mana = replace(mana, pending_ability=ability_id, pending_boosts=tuple(boosts.items()))
    preview = support_aura_preview(state.actors, session.active_combat_effects, ability_id, source_id,
        active_only=active_only, action=action, mana=mana)
    if preview is None:
        return LedFeedback()
    owner = preview.source
    members = set(preview.affected_actor_ids)
    member_positions = tuple(a.position for a in state.actors if str(a.id) in members and a.id != owner.id)
    area = tuple(Coordinate(col, row)
        for col in range(min(19, encounter.board.dimensions.cols))
        for row in range(encounter.board.dimensions.rows)
        if (max(abs(owner.position.col-col), abs(owner.position.row-row))*5 if preview.square_range
            else grid_distance_feet(owner.position, Coordinate(col, row))) <= preview.radius_feet
        and Coordinate(col, row) not in (*member_positions, owner.position))
    hostile = preview.source_kind == 'divine_care_aura_source'
    return LedFeedback((
        LedFrame(area, LedColor.AURA_DIVINE_CARE_DIM if hostile else LedColor.AURA_HEALING_DIM, LedRole.AREA_EFFECT),
        LedFrame(member_positions, LedColor.AURA_DIVINE_CARE_ACTIVE if hostile else LedColor.SELECTED_ABILITY_TARGET, LedRole.ENEMY if hostile else LedRole.ALLY),
        LedFrame((owner.position,), LedColor.ACTIVE_ACTOR, LedRole.ACTIVE_ACTOR),
    ))


def context_feedback(session: ExplorationUiSession) -> LedFeedback:
    from . import training_walkthrough as guided
    state = session.combat_state
    if state is None:
        return LedFeedback()
    if guided.enabled(session) and guided.notice_id(session):
        step = guided.current_step(session)
        return aura_feedback(session, step.ability.id, guided.hero_id(session),
            active_only=guided.flag(session, 'phase') == 'success', boosts=step.boosts
        ) if step and guided.flag(session, 'phase') in {'briefing', 'success'} else LedFeedback()
    declaration = session.shared_mana_declaration
    if declaration:
        return aura_feedback(session, declaration.ability_id, declaration.actor_id,
            active_only=declaration.stage != 'payment', boosts=declaration.boosts)
    if session.combat_turn_preview_option_id:
        option = next((o for o in session._combat_turn_action_options()
                       if o.id == session.combat_turn_preview_option_id), None)
        return aura_feedback(session, option.action_id or option.source_id, str(current_actor(state).id), boosts={}) if option else LedFeedback()
    if session._combat_has_pending_resolution() or session.selected_combat_aura_preview_id:
        return LedFeedback()
    frames = []
    for ability, kind in AURA_ABILITIES:
        owners = {e.source_actor_id or e.actor_id for e in session.active_combat_effects if e.kind == kind}
        for owner in sorted(owners):
            frames.extend(aura_feedback(session, ability, owner, active_only=True).frames)
    # The active figure belongs to the current board decision, even inside an aura.
    active_position = current_actor(state).position
    return LedFeedback(tuple(replace(frame, positions=tuple(p for p in frame.positions if p != active_position))
                             for frame in frames))

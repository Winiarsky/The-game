"""Arena-only teaching progress, persisted in the existing scene flags."""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
import json
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

from dnd_board_game.application.recruitment_arena import ARENA_ID, HERO_ORDER
from dnd_board_game.combat.scene import scene_flag, set_scene_flag
from dnd_board_game.rules.shared_mana_catalog import CATALOG, HOLY_SYMBOL, SharedAbility
from .board_panel_symbols import ability_panel_slot, panel_icon

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession


def abilities(hero_id: str) -> tuple[SharedAbility, ...]:
    return tuple(a for a in (*CATALOG, HOLY_SYMBOL) if a.hero_id == hero_id)


class TutorialContent(TypedDict):
    intro: str
    lessons: dict[str, str]


@lru_cache(maxsize=1)
def tutorial_content() -> dict[str, TutorialContent]:
    path = Path(__file__).resolve().parents[3] / 'content/tutorials/recruitment_arena.json'
    data = json.loads(path.read_text())['heroes']
    if set(data) != set(HERO_ORDER):
        raise ValueError('Samouczek wymaga siedmiu bohaterów.')
    for hero_id in HERO_ORDER:
        if set(data[hero_id]['lessons']) != {a.id for a in abilities(hero_id)}:
            raise ValueError(f'Niepełny katalog lekcji: {hero_id}.')
    return data


def enabled(session: ExplorationUiSession) -> bool:
    return (session.exploration.scenario_id == ARENA_ID
            and scene_flag(session.state.flags, 'training_mode', '') == 'tutorial')


def skill_key(hero_id: str, ability_id: str) -> str:
    return f'training_tutorial_done_{hero_id}_{ability_id}'


def completed(session: ExplorationUiSession, hero_id: str) -> tuple[str, ...]:
    return tuple(a.id for a in abilities(hero_id)
                 if scene_flag(session.state.flags, skill_key(hero_id, a.id), False))


def record_ability(session: ExplorationUiSession, ability_id: str, actor_id: str) -> None:
    """Called only at committed completion boundaries, never on a payment/preview."""
    from . import training_walkthrough as guided
    if guided.enabled(session):
        guided.record_ability(session, ability_id, actor_id)
        return
    if not enabled(session) or not session.custom_party or actor_id != str(session.custom_party[0].id):
        return
    if ability_id not in {a.id for a in abilities(actor_id)} or ability_id in completed(session, actor_id):
        return
    flags = set_scene_flag(session.state.flags, skill_key(actor_id, ability_id), True)
    flags = set_scene_flag(flags, 'training_tutorial_notice', ability_id)
    session.state = replace(session.state, flags=flags)
    session._record('training_ability_completed', {'hero_id': actor_id, 'ability_id': ability_id})
    session.board_selection_revision += 1


def notice_id(session: ExplorationUiSession) -> str:
    from .simple_traps import notice as trap_notice
    if (notice := trap_notice(session)) is not None:
        return str(notice['id'])
    from . import training_walkthrough as guided
    if guided.enabled(session):
        return guided.notice_id(session)
    if not enabled(session) or session.combat_state is None:
        return ''
    if (session._combat_has_pending_resolution() or session.shared_mana_declaration is not None
            or session.combat_targeting_attack_source_id or session.combat_targeting_class_feature_action_id
            or (session.encounter_setup_flow and session.encounter_setup_flow.current_step)):
        return ''
    return str(scene_flag(session.state.flags, 'training_tutorial_notice', ''))


def acknowledge(session: ExplorationUiSession, ability_id: str) -> dict[str, object]:
    from .simple_traps import notice as trap_notice, acknowledge as trap_acknowledge
    if trap_notice(session) is not None:
        return trap_acknowledge(session, ability_id)
    from . import training_walkthrough as guided
    if guided.enabled(session):
        return guided.acknowledge(session, ability_id)
    if not ability_id or ability_id != notice_id(session):
        raise ValueError('To objaśnienie nie jest już aktualne.')
    session.state = replace(session.state, flags=set_scene_flag(session.state.flags, 'training_tutorial_notice', ''))
    session.board_panel_context = None
    session.board_selection_revision += 1
    session._sync_board_leds()
    return session.state_payload()


def payload(session: ExplorationUiSession, hero_id: str) -> dict[str, object]:
    content = tutorial_content()[hero_id]
    done = completed(session, hero_id)
    lessons = [dict(id=a.id, name=a.name, cost=list(a.cost), timing=a.timing,
                    icon=panel_icon(2 if a.category == 'item' else ability_panel_slot(hero_id, a.id)),
                    instruction=content['lessons'][a.id], explanation=a.full_description,
                    completed=a.id in done) for a in abilities(hero_id)]
    notice = next((lesson for lesson in lessons if lesson['id'] == notice_id(session)), None)
    return dict(intro=content['intro'], lessons=lessons, completed_count=len(done), total=len(lessons),
                complete=len(done) == len(lessons), notice=notice)

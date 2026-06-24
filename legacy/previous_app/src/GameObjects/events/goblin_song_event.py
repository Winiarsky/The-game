from __future__ import annotations

import logging
import random
from typing import Iterable

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect
from actions.move_utils import find_path
from GameObjects.events.magic.magic_utils import grid_distance_feet
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources

from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


def _has_status(actor, status_id: str) -> bool:
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            return bool(has_status(status_id))
        except Exception:
            return False
    statuses = getattr(actor, "statuses", None)
    if isinstance(statuses, list):
        return any(getattr(s, "id", s) == status_id for s in statuses)
    return False


def _has_tag(actor, tag: str) -> bool:
    tags = getattr(actor, "tags", None)
    if isinstance(tags, (list, set, tuple)) and tag in tags:
        return True
    statuses = getattr(actor, "statuses", None) or []
    for status in statuses:
        data = getattr(status, "data", None) or {}
        effect_tags = set(data.get("effect_tags", []) or [])
        if tag in effect_tags:
            return True
    return False


def _is_hidden_or_unseen(actor) -> bool:
    if getattr(actor, "hidden", False) and not getattr(actor, "revealed", True):
        return True
    if _has_status(actor, "concealed"):
        return True
    if _has_status(actor, "stealth"):
        return True
    if _has_status(actor, "hidden"):
        return True
    return False


def _status_int(actor, status_id: str, key: str, default: int) -> int:
    getter = getattr(actor, "get_status_data", None)
    if callable(getter):
        try:
            raw = getter(status_id, key, default)
        except Exception:
            raw = default
        try:
            return int(raw)
        except Exception:
            return int(default)
    return int(default)


def _skill_rank(actor, skill_id: str) -> str:
    raw_skill = str(skill_id or "").strip().lower()
    if actor is None or not raw_skill:
        return "untrained"
    if raw_skill == Skill.PERCEPTION.value:
        return str(getattr(actor, "perception_rank", "untrained") or "untrained").strip().lower()
    if raw_skill in (Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value):
        save_ranks = getattr(actor, "save_ranks", None)
        if isinstance(save_ranks, dict):
            return str(save_ranks.get(raw_skill, "untrained") or "untrained").strip().lower()
    skill_ranks = getattr(actor, "skill_ranks", None)
    if isinstance(skill_ranks, dict):
        return str(skill_ranks.get(raw_skill, "untrained") or "untrained").strip().lower()
    return "untrained"


def _goblin_song_max_targets(actor) -> int:
    getter = getattr(actor, "get_status_data", None)
    rank_map = {}
    if callable(getter):
        try:
            rank_map = dict(getter("goblin_song", "goblin_song_max_targets_by_rank", {}) or {})
        except Exception:
            rank_map = {}
        base = _status_int(actor, "goblin_song", "max_targets", 1)
    else:
        base = 1
    rank = _skill_rank(actor, Skill.PERFORMANCE.value)
    if isinstance(rank_map, dict) and rank:
        raw = rank_map.get(rank)
        if raw is not None:
            try:
                return max(1, int(raw))
            except Exception:
                pass
    return max(1, int(base))


def GoblinSongDebuffStatus(*, duration: int) -> Status:
    return Status(
        id="goblin_song_debuff",
        label="Goblin Song",
        duration=duration,
        stacks=True,
        data={"ui_description": "-1 status do Perception i Will (Goblin Song)."},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value, Skill.WILL.value],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag=Skill.PERCEPTION.value,
                        source="status:goblin_song",
                        label="goblin song -1",
                        is_penalty=True,
                    ),
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag=Skill.WILL.value,
                        source="status:goblin_song",
                        label="goblin song -1",
                        is_penalty=True,
                    ),
                ],
            )
        ],
    )


def GoblinSongImmunityStatus(*, duration: int = 600) -> Status:
    return Status(
        id="goblin_song_immunity",
        label="Goblin Song Immunity",
        duration=duration,
        data={"ui_description": "Tymczasowa odporność na Goblin Song."},
    )


def _iter_candidates(
    game,
    source_pos: tuple[int, int],
    *,
    range_feet: int = 30,
) -> Iterable[tuple[object, tuple[int, int]]]:
    board = game.board
    max_range = max(5, int(range_feet or 30))
    for enemy in getattr(game, "enemies", []) or []:
        pos = getattr(enemy, "position", None)
        if pos is None:
            continue
        if _is_hidden_or_unseen(enemy):
            continue
        if _has_tag(enemy, "deaf") or _has_tag(enemy, "deafened"):
            continue
        if _has_status(enemy, "goblin_song_immunity"):
            continue
        if grid_distance_feet(source_pos, pos) > max_range:
            continue
        path = find_path(board, source_pos, pos, allow_diagonal=True, allow_occupied=True, mover=None)
        if not path:
            continue
        yield enemy, pos


@register_event
class GoblinSongEvent(GameEvent):
    name = "goblin_song"
    default_tags = ["performance", "sonic"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Goblin Song dostępne tylko w walce.")

        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do Goblin Song.")
        source_pos = getattr(actor, "position", None)
        if source_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        # Performance check -> DC
        resolution = resolve_skill_check_with_sources(
            skill_id=Skill.PERFORMANCE.value,
            dc=0,
            actor=actor,
            tags=[Skill.PERFORMANCE.value, "performance", "goblin_song"],
            game=ctx.game,
            apply_modifiers=True,
        )
        dc = int(resolution.total)
        try:
            ctx.game.ui_log(f"Goblin Song: DC z Performance = {dc}.")
        except Exception:
            pass

        max_targets = _goblin_song_max_targets(actor)
        range_feet = _status_int(actor, "goblin_song", "goblin_song_range_feet", 30)
        success_rounds = _status_int(actor, "goblin_song", "goblin_song_success_duration_rounds", 1)
        crit_success_rounds = _status_int(actor, "goblin_song", "goblin_song_critical_success_duration_rounds", 10)
        immunity_rounds = _status_int(actor, "goblin_song", "goblin_song_critical_failure_immunity_rounds", 600)
        perf_rank = _skill_rank(actor, Skill.PERFORMANCE.value)

        try:
            ui = getattr(ctx.game, "ui", None)
            if ui is not None and hasattr(ui, "prompt_info"):
                ui.prompt_info(
                    "Goblin Song",
                    prompt_long=(
                        f"Wybierz do {max_targets} celów w {range_feet} stóp. "
                        f"Skalowanie po Performance ({perf_rank}): "
                        "trained=1, expert=2, master=4, legendary=8."
                    ),
                    source="goblin_song",
                )
        except Exception:
            pass

        candidates = list(_iter_candidates(ctx.game, source_pos, range_feet=range_feet))
        if not candidates:
            return EventResult.cancelled(message="Brak celów w zasięgu Goblin Song.")

        positions = [pos for _enemy, pos in candidates]
        selected: list[object] = []
        selected_positions: set[tuple[int, int]] = set()

        base_color = [0, 80, 180]
        selected_color = [60, 160, 255]

        def _render_leds():
            colors = [selected_color if pos in selected_positions else base_color for pos in positions]
            ctx.game.conn.set_leds(positions, colors)

        def _prompt_more() -> bool:
            ui = getattr(ctx.game, "ui", None)
            if ui is not None and hasattr(ui, "prompt_choice"):
                try:
                    choice = ui.prompt_choice(
                        "Wskazać kolejny cel?",
                        choices=["tak", "nie"],
                        source="goblin_song",
                    )
                    return str(choice or "").strip().lower().startswith("t")
                except Exception:
                    pass
                if not getattr(ui, "allow_cli_fallback", False):
                    return False
            try:
                resp = input("Wskazać kolejny cel? [t/N]: ")
                return resp.strip().lower().startswith("t")
            except Exception:
                return False

        try:
            while True:
                _render_leds()
                choice = ctx.game.conn.scan_board(positions)
                if choice not in positions:
                    break
                if choice in selected_positions:
                    selected_positions.remove(choice)
                    selected = [e for e in selected if getattr(e, "position", None) != choice]
                else:
                    if len(selected) >= max_targets:
                        try:
                            ctx.game.ui_log("Osiągnięto limit celów.")
                        except Exception:
                            pass
                    else:
                        for enemy, pos in candidates:
                            if pos == choice:
                                selected.append(enemy)
                                selected_positions.add(pos)
                                break
                if len(selected) >= max_targets:
                    break
                if not _prompt_more():
                    break
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass

        if not selected:
            return EventResult.cancelled(message="Nie wybrano celów Goblin Song.")

        results = []
        for enemy in selected:
            will_bonus = getattr(enemy, "will_bonus", 0)
            try:
                will_bonus = int(will_bonus)
            except Exception:
                will_bonus = 0
            roll = random.randint(1, 20)
            total = roll + will_bonus
            diff = total - dc
            if diff >= 10:
                outcome = "critical_success"
            elif diff >= 0:
                outcome = "success"
            elif diff <= -10:
                outcome = "critical_failure"
            else:
                outcome = "failure"

            if outcome == "critical_success":
                try:
                    enemy.add_status(GoblinSongDebuffStatus(duration=crit_success_rounds))
                except Exception:
                    pass
                results.append(
                    f"{getattr(enemy, 'name', 'wróg')}: krytyczny sukces ({crit_success_rounds} rund)."
                )
            elif outcome == "success":
                try:
                    enemy.add_status(GoblinSongDebuffStatus(duration=success_rounds))
                except Exception:
                    pass
                results.append(f"{getattr(enemy, 'name', 'wróg')}: sukces ({success_rounds} runda/rund).")
            elif outcome == "critical_failure":
                try:
                    enemy.add_status(GoblinSongImmunityStatus(duration=immunity_rounds))
                except Exception:
                    pass
                results.append(
                    f"{getattr(enemy, 'name', 'wróg')}: krytyczna porażka (odporność {immunity_rounds} rund)."
                )
            else:
                results.append(f"{getattr(enemy, 'name', 'wróg')}: porażka.")

        if results:
            try:
                ctx.game.ui_log("Goblin Song: " + " ".join(results))
            except Exception:
                pass

        return EventResult(success=True, consumed_action=self.consumes_action, message="Goblin Song wykonany.")

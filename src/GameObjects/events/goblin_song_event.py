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


def _iter_candidates(game, source_pos: tuple[int, int]) -> Iterable[tuple[object, tuple[int, int]]]:
    board = game.board
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
        if grid_distance_feet(source_pos, pos) > 30:
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

        getter = getattr(actor, "get_status_data", None)
        if callable(getter):
            max_targets = getter("goblin_song", "max_targets", 1)
        else:
            max_targets = 1
        try:
            max_targets = int(max_targets)
        except Exception:
            max_targets = 1
        max_targets = max(1, max_targets)

        try:
            ui = getattr(ctx.game, "ui", None)
            if ui is not None and hasattr(ui, "prompt_info"):
                ui.prompt_info(
                    "Goblin Song",
                    prompt_long=(
                        f"Wybierz do {max_targets} celów w 30 stóp. "
                        "(Expert 2 / Master 4 / Legendary 8)"
                    ),
                    source="goblin_song",
                )
        except Exception:
            pass

        candidates = list(_iter_candidates(ctx.game, source_pos))
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
                    enemy.add_status(GoblinSongDebuffStatus(duration=5))
                except Exception:
                    pass
                results.append(f"{getattr(enemy, 'name', 'wróg')}: krytyczny sukces (5 rund).")
            elif outcome == "success":
                try:
                    enemy.add_status(GoblinSongDebuffStatus(duration=1))
                except Exception:
                    pass
                results.append(f"{getattr(enemy, 'name', 'wróg')}: sukces (1 runda).")
            elif outcome == "critical_failure":
                try:
                    enemy.add_status(GoblinSongImmunityStatus())
                except Exception:
                    pass
                results.append(f"{getattr(enemy, 'name', 'wróg')}: krytyczna porażka (odporność).")
            else:
                results.append(f"{getattr(enemy, 'name', 'wróg')}: porażka.")

        if results:
            try:
                ctx.game.ui_log("Goblin Song: " + " ".join(results))
            except Exception:
                pass

        return EventResult(success=True, consumed_action=self.consumes_action, message="Goblin Song wykonany.")

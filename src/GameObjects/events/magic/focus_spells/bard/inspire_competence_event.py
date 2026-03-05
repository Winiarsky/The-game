from __future__ import annotations

from board import consts
from skills import Skill
from statuses import AidedStatus

from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources

from ....base import EventContext, EventResult
from ....registry import register_event
from ...magic_event import MagicEvent
from ...magic_utils import grid_distance_feet
from ...spell_types import SpellTradition


def _is_bard(actor) -> bool:
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            return bool(has_status("bard"))
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) == "bard":
            return True
    class_name = str(getattr(actor, "class_name", "") or "").strip().lower()
    return class_name == "bard"


@register_event
class InspireCompetenceEvent(MagicEvent):
    name = "inspire_competence"
    actions_cost = 1
    default_tags = ["magic", "spell", "focus", "cantrip", "performance", "auditory"]
    spell_tags = ["cantrip", "focus", "occult", "bard"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["focus", "cantrip"]
    range_feet = 30
    prompt = (
        "Inspire Competence (Focus Cantrip): wybierz sojusznika i skill. "
        "Rzucasz Performance vs DC 15 jak przy Aid dla skilla. "
        "W walce: 1 akcja. Poza walka: bez kosztu akcji."
    )

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        if not _is_bard(actor):
            return EventResult.cancelled(message="Inspire Competence: tylko bard moze rzucic ten cantrip.")

        ui = getattr(ctx.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_info"):
            try:
                ui.prompt_info(
                    "Inspire Competence",
                    prompt_long=(
                        "Wybierasz sojusznika i skill. Wykonujesz test Performance (DC 15), "
                        "a wynik dziala jak Aid dla wybranego testu skilla."
                    ),
                    source="inspire_competence",
                )
            except Exception:
                pass

        target, _target_pos = self._pick_target(ctx, actor)
        if target is None:
            return EventResult.cancelled(message="Brak sojusznika w zasiegu Inspire Competence.")

        skill_id = self._pick_skill(ctx)
        if not skill_id:
            return EventResult.cancelled(message="Nie wybrano skilla do wsparcia.")

        result = resolve_skill_check_with_sources(
            skill_id=Skill.PERFORMANCE.value,
            dc=15,
            actor=actor,
            tags=["aid", "performance", "inspire_competence"],
            game=ctx.game,
            apply_modifiers=True,
        )
        outcome = str(getattr(result, "outcome", "failure") or "failure")

        if outcome == "failure":
            return EventResult(
                success=True,
                consumed_action=ctx.in_combat,
                actions_spent=1 if ctx.in_combat else None,
                message="Inspire Competence: nieudane (brak bonusu).",
            )

        if outcome == "critical_failure":
            bonus = -1
        elif outcome == "success":
            bonus = 1
        else:  # critical_success
            bonus = 2

        remover = getattr(target, "remove_status", None)
        if callable(remover):
            try:
                remover("aided")
            except Exception:
                pass
        adder = getattr(target, "add_status", None)
        if not callable(adder):
            return EventResult.cancelled(message="Sojusznik nie obsluguje statusow.")
        try:
            adder(AidedStatus(bonus=bonus, skill_id=skill_id))
        except Exception:
            return EventResult.cancelled(message="Nie udalo sie nalozyc efektu Inspire Competence.")

        return EventResult(
            success=True,
            consumed_action=ctx.in_combat,
            actions_spent=1 if ctx.in_combat else None,
            message=f"Inspire Competence: {outcome}, {target.name if hasattr(target, 'name') else 'cel'} dostaje {bonus:+d} do {skill_id}.",
        )

    def _pick_target(self, ctx: EventContext, actor):
        source_pos = getattr(actor, "position", None)
        candidates = []
        for hero in getattr(ctx.game, "heroes", []) or []:
            if hero is actor:
                continue
            pos = getattr(hero, "position", None)
            if pos is None:
                continue
            if grid_distance_feet(source_pos, pos) > self.range_feet:
                continue
            candidates.append((hero, pos))
        if not candidates:
            return None, None
        if len(candidates) == 1:
            return candidates[0]

        ui = getattr(ctx.game, "ui", None)
        names = [getattr(hero, "name", f"Hero {idx + 1}") for idx, (hero, _pos) in enumerate(candidates)]
        if ui is not None and hasattr(ui, "prompt_choice"):
            try:
                answer = ui.prompt_choice(
                    "Inspire Competence: wybierz sojusznika.",
                    choices=names,
                    source="inspire_competence",
                )
                if answer is not None:
                    raw = str(answer).strip()
                    if raw in names:
                        idx = names.index(raw)
                        return candidates[idx]
            except Exception:
                pass

        positions = [pos for _, pos in candidates]
        try:
            ctx.game.conn.set_leds(positions, consts.INTERACT_FIELD_RGB)
            choice = ctx.game.conn.scan_board(positions)
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass
        for hero, pos in candidates:
            if pos == choice:
                return hero, pos
        return None, None

    def _pick_skill(self, ctx: EventContext) -> str | None:
        choices = [skill.value for skill in Skill]
        ui = getattr(ctx.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_choice"):
            try:
                answer = ui.prompt_choice(
                    "Inspire Competence: wybierz skill do wsparcia.",
                    choices=choices,
                    source="inspire_competence",
                )
                if answer is not None:
                    raw = str(answer).strip().lower()
                    if raw in choices:
                        return raw
            except Exception:
                pass
            if not getattr(ui, "allow_cli_fallback", False):
                return None
        try:
            answer = input("Wybierz skill do wsparcia: ").strip().lower()
        except Exception:
            return None
        if answer in choices:
            return answer
        return None

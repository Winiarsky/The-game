from __future__ import annotations

import logging

from board import consts
from bonuses import BonusEffect, BonusType, build_modifiers_grid, compute_total_modifier, select_best_effects
from skills import Skill
from statuses import AidedStatus
from statuses.race.human.feats.cooperative_nature import COOPERATIVE_NATURE_STATUS

from .base import ActionCostEvent, EventContext, EventResult
from .registry import register_event
from GameObjects.interactions_mixin import prompt_for_roll, resolve_skill_check
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources

logger = logging.getLogger(__name__)


@register_event
class AidEvent(ActionCostEvent):
    """Aid: przyznaj jednorazowy bonus do następnego testu sojusznika."""

    name = "aid"
    default_tags = ["aid", "manipulate"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True
    actions_cost = 1

    @staticmethod
    def _has_status(obj, status) -> bool:
        if obj is None:
            return False
        has_status = getattr(obj, "has_status", None)
        if callable(has_status):
            return bool(has_status(status))
        for item in getattr(obj, "statuses", []) or []:
            item_id = getattr(item, "id", None)
            if item_id == status.id or item == status.id:
                return True
        return False

    @staticmethod
    def _adjacent_allies(game, pos, actor):
        board = game.board
        neighbors = board.get_neighbors(pos, include_position=False, diagonal=True)
        result = []
        for p in neighbors:
            occ = board.occupant_at(p)
            if occ is None or occ is actor:
                continue
            if occ in getattr(game, "heroes", []):
                result.append((occ, p))
        return result

    @staticmethod
    def _pick_target(ctx: EventContext, candidates):
        if not candidates:
            return None, None
        if len(candidates) == 1:
            return candidates[0]
        ui = getattr(ctx.game, "ui", None)
        names = [getattr(hero, "name", f"Hero {idx + 1}") for idx, (hero, _pos) in enumerate(candidates)]
        if ui is not None and hasattr(ui, "prompt_choice"):
            choice_meta = [
                {"raw": str(idx), "label": name, "desc": "Sojusznik w zasięgu 5 stóp."}
                for idx, name in enumerate(names)
            ]
            try:
                answer = ui.prompt_choice(
                    "Wybierz sojusznika do wsparcia.",
                    title="Aid",
                    subtitle="Wybór celu",
                    choices=[c["label"] for c in choice_meta],
                    choice_meta=choice_meta,
                    source="aid",
                )
                if answer is not None:
                    raw = str(answer).strip()
                    if raw.isdigit():
                        idx = int(raw)
                        if 0 <= idx < len(candidates):
                            return candidates[idx]
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

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Aid dostępne tylko w walce.")
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do Aid.")
        actor_pos = getattr(actor, "position", None)
        if actor_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        candidates = self._adjacent_allies(ctx.game, actor_pos, actor)
        target, target_pos = self._pick_target(ctx, candidates)
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak sojusznika do wsparcia.")

        coop = self._has_status(actor, COOPERATIVE_NATURE_STATUS)
        selection = self._pick_aid_test(ctx)
        if selection is None:
            return EventResult.cancelled(message="Nie wybrano testu do wsparcia.")

        outcome = self._resolve_aid_check(ctx, selection, actor)
        if outcome == "failure":
            try:
                ctx.game.ui_log("Aid nieudane: test przeciwko DC 15 nie powiódł się.")
            except Exception:
                pass
            return EventResult(success=True, consumed_action=self.consumes_action, message="Aid nieudane.")

        bonus = 0
        if outcome == "critical_failure":
            bonus = -1
        elif outcome == "success":
            bonus = 2 if coop else 1
        elif outcome == "critical_success":
            bonus = 4 if coop else 2
        try:
            ui = getattr(ctx.game, "ui", None)
            if ui is not None and hasattr(ui, "prompt_info"):
                ui.prompt_info(
                    "Aid",
                    prompt_long=f"Wynik testu Aid: {outcome.replace('_', ' ')}.",
                    source="aid",
                )
        except Exception:
            pass

        if selection.startswith("attack:"):
            tag = "attack_melee" if selection.endswith("melee") else "attack_ranged"
            adder = getattr(target, "add_bonus", None)
            if not callable(adder):
                return EventResult.cancelled(message="Sojusznik nie obsługuje bonusów.")
            try:
                remover = getattr(target, "remove_bonuses_by_source", None)
                if callable(remover):
                    remover("aid:attack")
            except Exception:
                pass
            try:
                adder(
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=abs(bonus),
                        tag=tag,
                        source="aid:attack",
                        label=f"aid {bonus:+d}",
                        is_penalty=bonus < 0,
                    )
                )
            except Exception as exc:
                logger.error("Nie udało się dodać bonusu Aid: %s", exc)
                return EventResult.cancelled(message="Nie udało się wesprzeć sojusznika.")
        else:
            adder = getattr(target, "add_status", None)
            if not callable(adder):
                return EventResult.cancelled(message="Sojusznik nie obsługuje statusów.")
            skill_id = selection.split("skill:", 1)[-1].strip()
            try:
                remover = getattr(target, "remove_status", None)
                if callable(remover):
                    remover("aided")
            except Exception:
                pass
            try:
                adder(AidedStatus(bonus=bonus, skill_id=skill_id))
            except Exception as exc:
                logger.error("Nie udało się dodać statusu Aided: %s", exc)
                return EventResult.cancelled(message="Nie udało się wesprzeć sojusznika.")

        try:
            if bonus < 0:
                ctx.game.ui_log("Aid: krytyczna porażka, sojusznik otrzymuje -1 do wybranego testu.")
            else:
                ctx.game.ui_log(f"Aid: sojusznik otrzymuje +{bonus} do wybranego testu (jednorazowo).")
        except Exception:
            pass

        return EventResult(success=True, consumed_action=self.consumes_action, message="Aid wykonane.")

    def _resolve_aid_check(self, ctx: EventContext, selection: str, actor) -> str:
        dc = 15
        if selection.startswith("attack:"):
            tag = "attack_melee" if selection.endswith("melee") else "attack_ranged"
            effects = list(getattr(actor, "bonuses", [])) if hasattr(actor, "bonuses") else []
            modifier = compute_total_modifier(effects, tag) if effects else 0
            best_effects = select_best_effects(effects, tag)
            roll = prompt_for_roll(
                f"Aid: test ataku ({'wręcz' if tag == 'attack_melee' else 'dystansowy'}) vs DC {dc}.",
                layout="test",
                prompt_long=f"Modyfikator łączny: {modifier:+d} (doliczany automatycznie).",
                modifiers=build_modifiers_grid(best_effects),
                answer_placeholder="Wynik k20",
            )
            total = roll + modifier
            return resolve_skill_check(dc, total)

        skill_id = selection.split("skill:", 1)[-1].strip()
        result = resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=dc,
            actor=actor,
            tags=["aid"],
            game=ctx.game,
            apply_modifiers=True,
        )
        return result.outcome

    def _pick_aid_test(self, ctx: EventContext) -> str | None:
        ui = getattr(ctx.game, "ui", None)
        skill_choices = []
        for skill in Skill:
            label = skill.value.replace("_", " ").title()
            skill_choices.append(
                {
                    "raw": f"skill:{skill.value}",
                    "label": label,
                    "desc": "Test umiejętności",
                }
            )
        attack_choices = [
            {"raw": "attack:melee", "label": "Melee Attack", "desc": "Test ataku wręcz"},
            {"raw": "attack:ranged", "label": "Ranged Attack", "desc": "Test ataku dystansowego"},
        ]
        choice_meta = skill_choices + attack_choices
        choices = [c["label"] for c in choice_meta]
        if ui is not None and hasattr(ui, "prompt_choice"):
            try:
                answer = ui.prompt_choice(
                    "Wybierz test do wsparcia.",
                    title="Aid",
                    subtitle="Wybór testu",
                    prompt_long="Bonus z Aid działa tylko na najbliższy rzut wybranego testu.",
                    choices=choices,
                    choice_meta=choice_meta,
                    source="aid",
                )
                if answer is not None:
                    return self._resolve_choice(str(answer).strip(), choice_meta)
            except Exception:
                pass
        try:
            answer = input("Wybierz test do wsparcia (np. Athletics / Melee Attack): ").strip()
        except Exception:
            return None
        return self._resolve_choice(answer, choice_meta)

    @staticmethod
    def _resolve_choice(raw: str, choice_meta: list[dict]) -> str | None:
        if not raw:
            return None
        for item in choice_meta:
            if raw == str(item.get("raw", "")):
                return item["raw"]
        for item in choice_meta:
            if raw.lower() == str(item.get("label", "")).lower():
                return item["raw"]
        return None

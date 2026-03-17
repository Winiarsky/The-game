from __future__ import annotations

import logging

from board import consts
from actions.move_utils import find_path, follow_path, trim_path_to_feet
from combat import effective_ac, refresh_flanking_statuses
from combat.degree_of_success import is_critical_success, is_hit, natural_shift_from_roll, resolve_outcome
from GameObjects.interactions_mixin import prompt_for_roll
from statuses import Status
from statuses.classes.ranger.ranger_utils import target_allows_precision_damage

from .base import ActionCostEvent, EventContext, EventResult
from .registry import register_event

logger = logging.getLogger(__name__)


def _actor_id(actor) -> str:
    return str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or id(actor))


def _has_status(actor, status_id: str) -> bool:
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            return bool(checker(status_id))
        except Exception:
            return False
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", status) == status_id:
            return True
    return False


def _remove_status(actor, status_id: str) -> None:
    remover = getattr(actor, "remove_status", None)
    if callable(remover):
        try:
            remover(status_id)
        except Exception:
            pass


def _prompt_choice(ctx: EventContext, prompt: str, choices: list[str], *, source: str) -> str | None:
    ui = getattr(ctx.game, "ui", None)
    answer = None
    if ui is not None and hasattr(ui, "prompt_choice"):
        try:
            answer = ui.prompt_choice(prompt, choices=choices, source=source)
        except Exception:
            answer = None
    if answer is None:
        try:
            answer = ctx.game.conn.read_card(prompt, choices)
        except Exception:
            answer = None
    if answer is None:
        return None
    raw = str(answer).strip().lower().replace(" ", "_")
    if not raw:
        return None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(choices):
            return choices[idx]
    for entry in choices:
        if raw == entry:
            return entry
    return None


@register_event
class CommandAnimalCompanionEvent(ActionCostEvent):
    name = "command_animal_companion"
    default_tags = ["companion", "command", "animal", "minion"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True
    actions_cost = 1

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Animal Companion dziala tylko w walce.")
        owner = ctx.actor
        if owner is None:
            return EventResult.cancelled(message="Brak ownera do komendy companiona.")
        if not _has_status(owner, "animal_companion"):
            return EventResult.cancelled(message="Bohater nie ma Animal Companion.")

        combat_state = getattr(ctx.game, "state", None)
        getter = getattr(combat_state, "get_animal_companion", None)
        if not callable(getter):
            return EventResult.cancelled(message="Brak runtime Animal Companion w stanie walki.")
        companion = getter(owner)
        if companion is None:
            return EventResult.cancelled(message="Animal Companion nie jest ustawiony na planszy.")

        if _has_status(owner, "animal_companion_commanded"):
            return EventResult.cancelled(message="Animal Companion byl juz komenderowany w tej turze.")

        actions_left = 2
        support_used = False
        action_logs: list[str] = []
        spent_any = False
        strike_count = 0
        while actions_left > 0:
            choices = ["stride", "strike", "support", "end"]
            if support_used:
                choices = ["stride", "end"]
            choice = _prompt_choice(
                ctx,
                f"Animal Companion ({getattr(companion, 'name', 'companion')}): wybierz akcje ({actions_left} left)",
                choices,
                source=self.name,
            )
            if choice is None:
                break
            if choice == "end":
                break
            if choice == "stride":
                consumed, msg = self._companion_stride(ctx, owner, companion)
            elif choice == "strike":
                consumed, msg = self._companion_strike(ctx, owner, companion, strike_count=strike_count)
            elif choice == "support":
                consumed, msg = self._companion_support(ctx, owner, companion)
                support_used = True if consumed else support_used
            else:
                consumed, msg = (False, "Nieznana akcja companiona.")

            if msg:
                action_logs.append(msg)
            if consumed:
                actions_left -= 1
                spent_any = True
                if choice == "strike":
                    strike_count += 1

        if not spent_any:
            return EventResult.cancelled(message="Komenda anulowana - companion nie wykonal zadnej akcji.")

        _remove_status(owner, "animal_companion_commanded")
        adder = getattr(owner, "add_status", None)
        if callable(adder):
            try:
                adder(
                    Status(
                        id="animal_companion_commanded",
                        label="Animal Companion Commanded",
                        duration=1,
                        source=self.name,
                        data={"source_id": _actor_id(owner), "source_turns_left": 1},
                    )
                )
            except Exception:
                pass

        summary = "; ".join(action_logs) if action_logs else "Animal Companion wykonuje komende."
        return EventResult(success=True, consumed_action=True, message=summary)

    def _companion_stride(self, ctx: EventContext, owner, companion) -> tuple[bool, str]:
        board = getattr(ctx.game, "board", None)
        start = getattr(companion, "position", None)
        if board is None or start is None:
            return False, "Stride: companion nie jest na planszy."

        try:
            ctx.game.conn.set_leds([start], consts.HERO_HIGHLIGHT_RGB)
        except Exception:
            pass
        try:
            target = ctx.game.conn.scan_board(None)
        except Exception:
            target = None
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass
        if target is None or not board.in_bounds(target):
            return False, "Stride: nie wybrano poprawnego celu ruchu."

        path = find_path(board, start, target, allow_diagonal=True, allow_occupied=False, mover=companion)
        if not path:
            # Fallback: w części testów helpery ruchu mogą być podmieniane; spróbuj
            # dynamicznie pobrać aktualną implementację find_path.
            try:
                from actions.move_utils import find_path as runtime_find_path

                path = runtime_find_path(board, start, target, allow_diagonal=True, allow_occupied=False, mover=companion)
            except Exception:
                path = []
        if not path:
            return False, "Stride: brak sciezki do wybranego pola."

        move_budget = max(5, int(getattr(companion, "land_speed_feet", 25) or 25))
        trimmed = trim_path_to_feet(path, move_budget, board, mover=companion)
        if len(trimmed) < 2:
            return False, "Stride: cel poza zasiegiem ruchu."

        dest = trimmed[-1]
        try:
            leds = [start] + trimmed[1:]
            colors = [consts.MOVE_START_RGB] + [consts.MOVE_FIELD_RGB] * (len(trimmed) - 1)
            ctx.game.conn.set_leds(leds, colors)
        except Exception:
            pass
        try:
            completed, _stop_pos, reason = follow_path(
                ctx,
                companion,
                trimmed,
                allow_occupied=False,
                step_delay=0.0,
            )
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass
        if not completed:
            return False, f"Stride: ruch przerwany ({reason or 'unknown'})."

        events_bus = getattr(ctx.game, "events", None)
        if events_bus is not None and hasattr(events_bus, "safe_emit_action"):
            try:
                events_bus.safe_emit_action(
                    actor=companion,
                    action_id="animal_companion_stride",
                    action_tags=["move", "animal_companion"],
                    owner_id=_actor_id(owner),
                    from_pos=start,
                    to_pos=dest,
                )
            except Exception:
                pass
        try:
            refresh_flanking_statuses(ctx.game)
        except Exception:
            pass
        return True, f"Stride: companion przemiescil sie na {dest}."

    @staticmethod
    def _combat_round_index(ctx: EventContext) -> int | None:
        try:
            if not ctx.in_combat:
                return None
            state = getattr(ctx.game, "state", None)
            return int(getattr(state, "round_index", 0) or 0)
        except Exception:
            return None

    @staticmethod
    def _companion_hunter_edge(companion) -> str:
        return str(getattr(companion, "ranger_hunter_edge", "") or "").strip().lower()

    @staticmethod
    def _companion_hunted_target_id(companion) -> str:
        return str(getattr(companion, "ranger_hunted_prey_target_id", "") or "").strip()

    def _companion_precision_ready(self, ctx: EventContext, companion, target) -> bool:
        if self._companion_hunter_edge(companion) != "precision":
            return False
        target_id = _actor_id(target)
        if not target_id or target_id != self._companion_hunted_target_id(companion):
            return False
        if not target_allows_precision_damage(target):
            return False
        round_index = self._combat_round_index(ctx)
        if round_index is None:
            return True
        applied_round = getattr(companion, "ranger_precision_applied_round", None)
        applied_target = str(getattr(companion, "ranger_precision_applied_target_id", "") or "").strip()
        try:
            if int(applied_round) == int(round_index) and applied_target == target_id:
                return False
        except Exception:
            pass
        return True

    def _mark_companion_precision(self, ctx: EventContext, companion, target) -> None:
        round_index = self._combat_round_index(ctx)
        target_id = _actor_id(target)
        try:
            setattr(companion, "ranger_precision_applied_round", round_index)
        except Exception:
            pass
        try:
            setattr(companion, "ranger_precision_applied_target_id", target_id)
        except Exception:
            pass

    def _companion_strike(self, ctx: EventContext, owner, companion, *, strike_count: int = 0) -> tuple[bool, str]:
        board = getattr(ctx.game, "board", None)
        source_pos = getattr(companion, "position", None)
        if board is None or source_pos is None:
            return False, "Strike: companion nie jest na planszy."

        reach = max(1, int(getattr(companion, "reach_cells", 1) or 1))
        candidates = []
        for enemy in getattr(ctx.game, "enemies", []) or []:
            pos = getattr(enemy, "position", None)
            if pos is None:
                continue
            if int(getattr(enemy, "hp", 1) or 1) <= 0:
                continue
            if max(abs(pos[0] - source_pos[0]), abs(pos[1] - source_pos[1])) > reach:
                continue
            candidates.append(enemy)
        if not candidates:
            return False, "Strike: brak wroga w zasiegu companiona."

        target = None
        if len(candidates) == 1:
            target = candidates[0]
        else:
            positions = [getattr(enemy, "position", None) for enemy in candidates if getattr(enemy, "position", None) is not None]
            try:
                ctx.game.conn.set_leds(positions, consts.INTERACT_FIELD_RGB)
                selected = ctx.game.conn.scan_board(positions)
            finally:
                try:
                    ctx.game.conn.leds_off()
                except Exception:
                    pass
            for enemy in candidates:
                if getattr(enemy, "position", None) == selected:
                    target = enemy
                    break
            if target is None:
                target = candidates[0]

        attacks = list(getattr(companion, "attack_profiles", []) or [])
        if not attacks:
            return False, "Strike: companion nie ma atakow."
        if len(attacks) == 1:
            profile = attacks[0]
        else:
            labels = [str(a.get("label", a.get("id", "attack")) or "attack").strip().lower().replace(" ", "_") for a in attacks]
            choice = _prompt_choice(
                ctx,
                "Animal Companion: wybierz atak",
                labels,
                source=self.name,
            )
            profile = attacks[0]
            if choice:
                for cand, label in zip(attacks, labels):
                    if choice == label:
                        profile = cand
                        break

        attack_label = str(profile.get("label", profile.get("id", "attack")) or "attack")
        damage_formula = str(profile.get("damage", "1d6") or "1d6")
        damage_type = str(profile.get("damage_type", "normal") or "normal")
        target_ac = int(effective_ac(target) or 10)
        traits = {str(item or "").strip().lower() for item in (profile.get("traits") or [])}
        hunted_target = self._companion_hunted_target_id(companion) == _actor_id(target)
        flurry_note = ""
        if self._companion_hunter_edge(companion) == "flurry" and hunted_target:
            if strike_count == 1:
                flurry_note = "Hunter's Edge (Flurry): MAP dla 2. ataku: -2 agile / -3 standard."
            elif strike_count >= 2:
                flurry_note = "Hunter's Edge (Flurry): MAP dla 3+ ataku: -4 agile / -6 standard."
            else:
                flurry_note = "Hunter's Edge (Flurry): pierwszy atak bez MAP."
        agile_note = "Atak ma trait agile." if "agile" in traits else "Atak bez traitu agile."
        prompt_notes = [f"AC celu: {target_ac}", agile_note]
        if flurry_note:
            prompt_notes.append(flurry_note)

        attack_roll_data = prompt_for_roll(
            f"Animal Companion Strike ({attack_label}) - podaj wynik ataku lacznie z modyfikatorem:",
            layout="test",
            answer_placeholder="Attack total",
            prompt_long="\n".join(prompt_notes),
            return_details=True,
            infer_natural_from_roll=False,
        )
        if isinstance(attack_roll_data, dict):
            attack_roll = int(attack_roll_data.get("roll", 0) or 0)
            natural_shift = int(attack_roll_data.get("natural_shift", 0) or 0)
        else:
            attack_roll = int(attack_roll_data or 0)
            natural_shift = natural_shift_from_roll(attack_roll)
        outcome = resolve_outcome(attack_roll, target_ac, natural_shift=natural_shift)
        critical = is_critical_success(outcome)
        hit = is_hit(outcome)
        if not hit:
            return True, f"Strike ({attack_label}): pudlo vs AC {target_ac}."

        dmg_base = int(
            prompt_for_roll(
                f"Animal Companion Strike ({attack_label}) - podaj obrazenia ({damage_formula}):",
                layout="damage",
                answer_placeholder="Damage",
                prompt_long="Na critical obrazenia sa podwajane automatycznie.",
            )
            or 0
        )
        precision_bonus = 0
        if self._companion_precision_ready(ctx, companion, target):
            precision_roll = prompt_for_roll(
                "Hunter's Edge (Precision) - dodatkowe obrażenia 1k8:",
                layout="damage",
                answer_placeholder="Precision damage",
            )
            try:
                precision_bonus = max(0, int(precision_roll or 0))
            except Exception:
                precision_bonus = 0
            self._mark_companion_precision(ctx, companion, target)

        damage = max(0, dmg_base * (2 if critical else 1)) + precision_bonus
        apply = getattr(target, "apply_damage", None)
        defeated = False
        if callable(apply):
            try:
                _hp, defeated = apply(damage, damage_type)
            except Exception:
                defeated = False
        if defeated and getattr(target, "position", None) is not None and board is not None:
            try:
                board.remove(getattr(target, "position"))
            except Exception:
                pass
        try:
            refresh_flanking_statuses(ctx.game)
        except Exception:
            pass
        events_bus = getattr(ctx.game, "events", None)
        if events_bus is not None and hasattr(events_bus, "safe_emit_action"):
            try:
                events_bus.safe_emit_action(
                    actor=companion,
                    target=target,
                    action_id="animal_companion_strike",
                    action_tags=["attack", "animal_companion"],
                    owner_id=_actor_id(owner),
                    attack_name=attack_label,
                    critical=bool(critical),
                    damage=damage,
                    damage_type=damage_type,
                )
            except Exception:
                pass
        target_name = getattr(target, "name", "target")
        msg = f"Strike ({attack_label}) trafia {target_name} za {damage} {damage_type}."
        if precision_bonus > 0:
            msg += f" Precision +{precision_bonus}."
        if critical:
            msg += " Critical."
        if defeated:
            msg += " Cel pokonany."
        return True, msg

    def _companion_support(self, _ctx: EventContext, owner, companion) -> tuple[bool, str]:
        _remove_status(owner, "animal_companion_support")
        support_note = str(getattr(companion, "support_benefit", "") or "").strip()
        adder = getattr(owner, "add_status", None)
        if callable(adder):
            try:
                adder(
                    Status(
                        id="animal_companion_support",
                        label=f"Animal Companion Support ({getattr(companion, 'companion_type', 'companion')})",
                        duration=1,
                        source=self.name,
                        data={
                            "companion_type": str(getattr(companion, "companion_type", "wolf")),
                            "support_benefit": support_note,
                            "manual_resolution": False,
                            "owner_move_feet_this_turn": 0,
                        },
                    )
                )
            except Exception:
                pass
        if not support_note:
            support_note = "Companion wspiera ownera do startu nastepnej tury."
        return True, f"Support: {support_note}"


__all__ = [
    "CommandAnimalCompanionEvent",
]

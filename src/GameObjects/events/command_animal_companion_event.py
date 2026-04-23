from __future__ import annotations

import logging
import time

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


def _is_enemy_target(game, target) -> bool:
    if target is None:
        return False
    if target in getattr(game, "enemies", []):
        return True
    module_name = str(getattr(getattr(target, "__class__", None), "__module__", "") or "")
    if module_name.startswith("GameObjects.Enemies.") or module_name == "GameObjects.Enemies.basic_enemy":
        if getattr(target, "position", None) is None:
            return False
        try:
            return int(getattr(target, "hp", 1) or 0) > 0
        except Exception:
            return True
    if getattr(target, "behavior_id", None) is not None and getattr(target, "position", None) is not None:
        try:
            return int(getattr(target, "hp", 1) or 0) > 0
        except Exception:
            return True
    if getattr(target, "position", None) is not None and hasattr(target, "hp") and hasattr(target, "ac"):
        try:
            return int(getattr(target, "hp", 1) or 0) > 0
        except Exception:
            return True
    return False


def _prompt_choice(
    ctx: EventContext,
    prompt: str,
    choices: list[str],
    *,
    source: str,
    choice_meta: list[dict] | None = None,
) -> str | None:
    ui = getattr(ctx.game, "ui", None)
    answer = None
    if ui is not None and hasattr(ui, "prompt_choice"):
        try:
            answer = ui.prompt_choice(
                prompt,
                choices=choices,
                source=source,
                choice_meta=choice_meta,
                layout="menu_numpad",
            )
        except Exception:
            answer = None
    if answer is None:
        conn = getattr(ctx.game, "conn", None)
        reader = getattr(conn, "read_card", None)
        if callable(reader):
            try:
                answer = reader(f"{prompt}: {', '.join(choices)}", source=source)
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


def _prompt_info(ctx: EventContext, title: str, text: str, *, source: str) -> None:
    ui = getattr(ctx.game, "ui", None)
    if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_info"):
        try:
            ui.prompt_info(title, prompt_long=text, source=source)
            return
        except Exception:
            pass
    logger.info("%s: %s", title, text)


def _highlight_companion_and_positions(ctx: EventContext, companion, positions: list[tuple[int, int]]) -> None:
    conn = getattr(ctx.game, "conn", None)
    if conn is None or not hasattr(conn, "set_leds"):
        return
    source_pos = getattr(companion, "position", None)
    led_positions: list[tuple[int, int]] = []
    led_colors: list[list[int]] = []
    if source_pos is not None:
        led_positions.append(tuple(source_pos))
        led_colors.append(list(consts.HERO_HIGHLIGHT_RGB))
    for pos in positions:
        led_positions.append(tuple(pos))
        led_colors.append(list(consts.INTERACT_FIELD_RGB))
    if not led_positions:
        return
    try:
        conn.set_leds(led_positions, led_colors)
    except Exception:
        pass


def _recover_companion_from_board(ctx: EventContext, owner):
    state = getattr(ctx.game, "state", None)
    owner_id = _actor_id(owner)
    board = getattr(ctx.game, "board", None)
    iterator = getattr(board, "_iter_occupants", None)
    if not callable(iterator):
        return None
    for candidate in iterator():
        if str(getattr(candidate, "owner_id", "") or "") != owner_id:
            continue
        if getattr(candidate, "companion_type", None) is None:
            continue
        if getattr(candidate, "position", None) is None:
            continue
        mapping = getattr(state, "animal_companions", None)
        if isinstance(mapping, dict):
            mapping[owner_id] = candidate
        return candidate
    return None


def _iter_enemy_like_targets(ctx: EventContext):
    seen: set[str] = set()
    for enemy in list(getattr(ctx.game, "enemies", []) or []):
        enemy_id = _actor_id(enemy)
        if enemy_id in seen:
            continue
        seen.add(enemy_id)
        yield enemy
    board = getattr(ctx.game, "board", None)
    iterator = getattr(board, "_iter_occupants", None)
    if not callable(iterator):
        return
    for candidate in iterator():
        candidate_id = _actor_id(candidate)
        if candidate_id in seen:
            continue
        if not _is_enemy_target(ctx.game, candidate):
            continue
        seen.add(candidate_id)
        yield candidate


def _damage_formula_average(damage_formula: str) -> int:
    raw = str(damage_formula or "").strip().lower().replace(" ", "")
    if "d" not in raw:
        try:
            return max(0, int(raw or 0))
        except Exception:
            return 0
    count_part, rest = raw.split("d", 1)
    bonus = 0
    sides_part = rest
    if "+" in rest:
        sides_part, bonus_part = rest.split("+", 1)
        try:
            bonus = int(bonus_part or 0)
        except Exception:
            bonus = 0
    count = int(count_part or 1)
    sides = int(sides_part or 0)
    if count <= 0 or sides <= 0:
        return max(0, bonus)
    return max(0, int(round(count * ((sides + 1) / 2.0) + bonus)))


def _companion_attack_bonus(companion, profile: dict[str, object], *, strike_count: int = 0) -> int:
    traits = {str(item or "").strip().lower() for item in (profile.get("traits") or [])}
    level = max(1, int(getattr(companion, "level", 1) or 1))
    ability_mods = dict(getattr(companion, "ability_mods", {}) or {})
    str_mod = int(ability_mods.get("str", 0) or 0)
    dex_mod = int(ability_mods.get("dex", 0) or 0)
    prof_bonus = level + 2
    is_finesse = "finesse" in traits
    ability_bonus = dex_mod if is_finesse and dex_mod > str_mod else str_mod
    agile = "agile" in traits
    if strike_count <= 0:
        map_penalty = 0
    elif strike_count == 1:
        map_penalty = -4 if agile else -5
    else:
        map_penalty = -8 if agile else -10
    return int(prof_bonus + ability_bonus + map_penalty)


def _companion_action_choice_meta(companion) -> list[dict[str, str]]:
    speed = max(5, int(getattr(companion, "land_speed_feet", 25) or 25))
    support_note = str(getattr(companion, "support_benefit", "") or "").strip()
    attacks = list(getattr(companion, "attack_profiles", []) or [])
    strike_lines: list[str] = []
    for attack in attacks:
        label = str(attack.get("label", attack.get("id", "Atak")) or "Atak")
        damage = str(attack.get("damage", "1d6") or "1d6")
        damage_type = str(attack.get("damage_type", "normal") or "normal")
        bonus = _companion_attack_bonus(companion, attack, strike_count=0)
        avg = _damage_formula_average(damage) + max(0, int(dict(getattr(companion, "ability_mods", {}) or {}).get("str", 0) or 0))
        strike_lines.append(f"{label}: atak {bonus:+d}, obrażenia {damage}+STR ({damage_type}, średnio ok. {avg}).")
    strike_desc = " ".join(strike_lines) if strike_lines else "Wykonuje podstawowy atak w zasięgu 5 ft."
    return [
        {
            "raw": "stride",
            "label": "Ruch",
            "desc": f"Ruch towarzysza do {speed} ft zgodnie z podświetloną ścieżką.",
            "category": "movement",
        },
        {
            "raw": "strike",
            "label": "Atak",
            "desc": strike_desc,
            "category": "combat",
        },
        {
            "raw": "support",
            "label": "Wsparcie",
            "desc": support_note or "Towarzysz wspiera właściciela do początku jego następnej tury.",
            "category": "class",
        },
        {
            "raw": "end",
            "label": "Koniec",
            "desc": "Zakończ komendę i zachowaj niewydane akcje towarzysza.",
            "category": "turn",
        },
    ]


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
            return EventResult.cancelled(message="Zwierzecy towarzysz dziala tylko w walce.")
        owner = ctx.actor
        if owner is None:
            return EventResult.cancelled(message="Brak wlasciciela do komendy towarzysza.")
        if not _has_status(owner, "animal_companion"):
            return EventResult.cancelled(message="Bohater nie ma zwierzecego towarzysza.")

        combat_state = getattr(ctx.game, "state", None)
        getter = getattr(combat_state, "get_animal_companion", None)
        if not callable(getter):
            return EventResult.cancelled(message="Brak runtime zwierzecego towarzysza w stanie walki.")
        companion = getter(owner)
        if companion is None:
            companion = _recover_companion_from_board(ctx, owner)
        if companion is None:
            return EventResult.cancelled(message="Zwierzecy towarzysz nie jest ustawiony na planszy.")

        if _has_status(owner, "animal_companion_commanded"):
            return EventResult.cancelled(message="Zwierzecy towarzysz byl juz komenderowany w tej turze.")

        actions_left = 2
        support_used = False
        action_logs: list[str] = []
        spent_any = False
        strike_count = 0
        while actions_left > 0:
            choices = ["stride", "strike", "support", "end"]
            if support_used:
                choices = ["stride", "end"]
            choice_meta = [row for row in _companion_action_choice_meta(companion) if row.get("raw") in choices]
            choice = _prompt_choice(
                ctx,
                f"Zwierzecy towarzysz ({getattr(companion, 'name', 'towarzysz')}): wybierz akcje ({actions_left} pozostalo)",
                choices,
                source=self.name,
                choice_meta=choice_meta,
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
                consumed, msg = (False, "Nieznana akcja towarzysza.")

            if msg:
                action_logs.append(msg)
                if not consumed:
                    _prompt_info(
                        ctx,
                        "Zwierzęcy towarzysz: akcja niemożliwa",
                        str(msg),
                        source=self.name,
                    )
            if consumed:
                actions_left -= 1
                spent_any = True
                if choice == "strike":
                    strike_count += 1

        if not spent_any:
            return EventResult.cancelled(message="Komenda anulowana - towarzysz nie wykonal zadnej akcji.")

        _remove_status(owner, "animal_companion_commanded")
        adder = getattr(owner, "add_status", None)
        if callable(adder):
            try:
                adder(
                    Status(
                        id="animal_companion_commanded",
                        label="Zwierzecy towarzysz skomenderowany",
                        duration=1,
                        source=self.name,
                        data={"source_id": _actor_id(owner), "source_turns_left": 1},
                    )
                )
            except Exception:
                pass

        summary = "; ".join(action_logs) if action_logs else "Zwierzecy towarzysz wykonuje komende."
        try:
            ctx.game.events.safe_emit_action(
                actor=owner,
                action_id=self.name,
                action_tags=self._effective_tags(ctx),
                summary=summary,
                companion_id=_actor_id(companion),
                companion_name=getattr(companion, "name", "Towarzysz"),
            )
        except Exception:
            pass
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
        path_leds = [start] + trimmed[1:]
        path_colors = [consts.MOVE_START_RGB] + [consts.MOVE_FIELD_RGB] * (len(trimmed) - 2) + [consts.MOVE_TARGET_RGB]
        try:
            ctx.game.conn.set_leds(path_leds, path_colors)
        except Exception:
            pass
        try:
            confirm = ctx.game.conn.scan_board(None)
        except Exception:
            confirm = None
        if confirm != dest:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass
            return False, "Stride: ruch anulowany (kliknij podświetlone pole docelowe, aby potwierdzić)."
        try:
            completed, _stop_pos, reason = follow_path(
                ctx,
                companion,
                trimmed,
                allow_occupied=False,
                step_delay=0.1,
            )
        finally:
            try:
                fading = [list(map(int, c)) for c in path_colors]
                for idx in range(len(path_leds)):
                    fading[idx] = [0, 0, 0]
                    ctx.game.conn.set_leds(path_leds, fading)
                    time.sleep(0.05)
                ctx.game.conn.leds_off()
            except Exception:
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
        for enemy in _iter_enemy_like_targets(ctx):
            pos = getattr(enemy, "position", None)
            if pos is None:
                continue
            if int(getattr(enemy, "hp", 1) or 1) <= 0:
                continue
            if max(abs(pos[0] - source_pos[0]), abs(pos[1] - source_pos[1])) > reach:
                continue
            candidates.append(enemy)
        if not candidates and board is not None:
            for pos in board.get_neighbors(source_pos, include_position=False, diagonal=True):
                target = board.occupant_at(pos)
                if not _is_enemy_target(ctx.game, target):
                    continue
                if max(abs(pos[0] - source_pos[0]), abs(pos[1] - source_pos[1])) > reach:
                    continue
                candidates.append(target)
        if not candidates:
            return False, "Strike: brak wroga w zasiegu companiona."

        target = None
        if len(candidates) == 1:
            target = candidates[0]
        else:
            positions = [getattr(enemy, "position", None) for enemy in candidates if getattr(enemy, "position", None) is not None]
            _prompt_info(
                ctx,
                "Zwierzęcy towarzysz: wybór celu",
                (
                    f"Wybierz figurkę przeciwnika, którego zaatakuje {getattr(companion, 'name', 'towarzysz')}.\n"
                    "Podświetlona figurka to twój towarzysz, a pola celu są oznaczone osobnym kolorem."
                ),
                source=self.name,
            )
            try:
                _highlight_companion_and_positions(ctx, companion, positions)
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
            choice_meta = []
            for attack, label in zip(attacks, labels):
                damage = str(attack.get("damage", "1d6") or "1d6")
                damage_type = str(attack.get("damage_type", "normal") or "normal")
                attack_bonus = _companion_attack_bonus(companion, attack, strike_count=strike_count)
                choice_meta.append(
                    {
                        "raw": label,
                        "label": str(attack.get("label", label) or label),
                        "desc": f"Atak {attack_bonus:+d}; obrażenia {damage}+STR ({damage_type}).",
                        "category": "combat",
                    }
                )
            choice = _prompt_choice(
                ctx,
                "Zwierzecy towarzysz: wybierz atak",
                labels,
                source=self.name,
                choice_meta=choice_meta,
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
        target_name = getattr(target, "name", "target")
        target_pos = getattr(target, "position", None)
        traits = {str(item or "").strip().lower() for item in (profile.get("traits") or [])}
        hunted_target = self._companion_hunted_target_id(companion) == _actor_id(target)
        agile = "agile" in traits
        is_finesse = "finesse" in traits
        flurry = self._companion_hunter_edge(companion) == "flurry" and hunted_target

        # --- Oblicz modyfikator ataku (PF2e: proficiency + ability + MAP) ---
        companion_level = max(1, int(getattr(companion, "level", 1) or 1))
        ability_mods = dict(getattr(companion, "ability_mods", {}) or {})
        str_mod = int(ability_mods.get("str", 0) or 0)
        dex_mod = int(ability_mods.get("dex", 0) or 0)
        prof_bonus = companion_level + 2  # wytrenowany (trained)
        if is_finesse and dex_mod > str_mod:
            ability_bonus = dex_mod
            ability_label = "Zręczność"
        else:
            ability_bonus = str_mod
            ability_label = "Siła"

        if strike_count == 0:
            map_penalty = 0
        elif strike_count == 1:
            map_penalty = (-2 if agile else -3) if flurry else (-4 if agile else -5)
        else:
            map_penalty = (-4 if agile else -6) if flurry else (-8 if agile else -10)

        atk_components: list[dict] = [
            {
                "id": "proficiency",
                "label": "Biegłość",
                "value": prof_bonus,
                "description": f"Wytrenowany: poziom {companion_level} + 2.",
                "editable": True,
            },
            {
                "id": "ability",
                "label": ability_label,
                "value": ability_bonus,
                "description": f"Modyfikator {ability_label}{' (finesse)' if is_finesse and dex_mod > str_mod else ''}.",
                "editable": True,
            },
            {
                "id": "item",
                "label": "Przedmiot",
                "value": 0,
                "description": "Premie z wyposażenia (brak).",
                "editable": True,
            },
        ]
        if map_penalty != 0:
            map_label = "MAP (Flurry)" if flurry else "MAP"
            atk_components.append({
                "id": "situational",
                "label": map_label,
                "value": map_penalty,
                "description": f"Multiple Attack Penalty ({'agile' if agile else 'standard'}).",
                "editable": True,
            })
        atk_auto_total = sum(int(c["value"]) for c in atk_components)
        atk_roll_stack = {"components": atk_components, "auto_total_modifier": atk_auto_total}

        flurry_note = ""
        if flurry:
            if strike_count == 1:
                flurry_note = "Hunter's Edge (Flurry): MAP dla 2. ataku: -2 agile / -3 standard."
            elif strike_count >= 2:
                flurry_note = "Hunter's Edge (Flurry): MAP dla 3+ ataku: -4 agile / -6 standard."
            else:
                flurry_note = "Hunter's Edge (Flurry): pierwszy atak bez MAP."
        agile_note = "Atak ma trait agile." if agile else "Atak bez traitu agile."
        prompt_notes = [f"AC celu: {target_ac}", agile_note]
        if flurry_note:
            prompt_notes.append(flurry_note)

        if target_pos is not None:
            try:
                _highlight_companion_and_positions(ctx, companion, [tuple(target_pos)])
            except Exception:
                pass
        _prompt_info(
            ctx,
            "Zwierzęcy towarzysz: Strike",
            (
                f"{getattr(companion, 'name', 'Towarzysz')} wykonuje {attack_label} przeciw {target_name}"
                f"{f' na polu {target_pos}' if target_pos is not None else ''}.\n"
                f"Teraz wykonaj rzut ataku przeciw AC {target_ac} i potwierdź w UI."
            ),
            source=self.name,
        )

        attack_roll_data = prompt_for_roll(
            f"Atak zwierzecego towarzysza ({attack_label}):",
            layout="test",
            answer_placeholder="Wynik k20",
            prompt_long="\n".join(prompt_notes),
            roll_stack=atk_roll_stack,
            auto_total_modifier=atk_auto_total,
            return_details=True,
            infer_natural_from_roll=False,
        )
        if isinstance(attack_roll_data, dict):
            attack_roll = int(attack_roll_data.get("computed_total", attack_roll_data.get("roll", 0)) or 0)
            natural_shift = int(attack_roll_data.get("natural_shift", 0) or 0)
        else:
            attack_roll = int(attack_roll_data or 0)
            natural_shift = natural_shift_from_roll(attack_roll)
        outcome = resolve_outcome(attack_roll, target_ac, natural_shift=natural_shift)
        critical = is_critical_success(outcome)
        hit = is_hit(outcome)
        if not hit:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass
            return True, f"Strike ({attack_label}): pudło vs AC {target_ac} (wynik: {attack_roll})."

        # --- Roll obrażeń z modyfikatorem STR ---
        dmg_str_mod = str_mod  # PF2e: obrażenia używają STR, nie DEX (nawet finesse)
        dmg_components: list[dict] = [
            {
                "id": "ability",
                "label": "Siła",
                "value": dmg_str_mod,
                "description": "Modyfikator Siły do obrażeń.",
                "editable": True,
            },
        ]
        dmg_auto_total = dmg_str_mod
        dmg_roll_stack = {"components": dmg_components, "auto_total_modifier": dmg_auto_total}
        _prompt_info(
            ctx,
            "Zwierzęcy towarzysz: obrażenia",
            (
                f"Atak {attack_label} trafia {target_name}.\n"
                f"Rzuć teraz obrażenia ({damage_formula})"
                f"{' x2 dla krytyka' if critical else ''} i potwierdź w UI."
            ),
            source=self.name,
        )
        dmg_base = int(
            prompt_for_roll(
                f"Atak zwierzecego towarzysza ({attack_label}) - obrazenia ({damage_formula}):",
                layout="damage",
                answer_placeholder="Suma obrażeń",
                prompt_long="Przy trafeniu krytycznym obrażenia są podwajane automatycznie.",
                roll_stack=dmg_roll_stack,
                auto_total_modifier=dmg_auto_total,
            )
            or 0
        )
        precision_bonus = 0
        if self._companion_precision_ready(ctx, companion, target):
            _prompt_info(
                ctx,
                "Zwierzęcy towarzysz: Precision",
                "Hunter's Edge (Precision) jest aktywne. Rzuć dodatkowe obrażenia i potwierdź w UI.",
                source=self.name,
            )
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
        try:
            ctx.game.conn.leds_off()
        except Exception:
            pass
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
                        label=f"Wsparcie zwierzecego towarzysza ({getattr(companion, 'companion_type', 'towarzysz')})",
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

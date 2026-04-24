from __future__ import annotations

import heapq
import logging

from board import consts
import GameObjects.interactions_mixin.skill_check_resolver as check_resolver
from prompt_text_catalog import render_prompt_text
from ui_client import get_ui_client
from skills import Skill
from GameObjects.events.magic.magic_utils import grid_distance_feet

from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


def _color_tuple(value) -> tuple[int, int, int]:
    try:
        rgb = list(value or [])
        return (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    except Exception:
        base = list(consts.SEEK_OBJECT_RGB)
        return (int(base[0]), int(base[1]), int(base[2]))


def _scaled_rgb(value, factor: float) -> list[int]:
    base = _color_tuple(value)
    return [max(0, min(255, int(round(channel * factor)))) for channel in base]


@register_event
class SeekEvent(GameEvent):
    name = "seek"
    default_tags = ["seek", Skill.PERCEPTION.value]
    consumes_action = True

    @staticmethod
    def _seek_area_preview_rgb() -> list[int]:
        factor = float(getattr(consts, "SEEK_AREA_PREVIEW_BRIGHTNESS", 0.45) or 0.45)
        return _scaled_rgb(consts.SEEK_AREA_RGB, factor)

    @staticmethod
    def _seek_object_preview_rgb(color) -> list[int]:
        factor = float(getattr(consts, "SEEK_OBJECT_PREVIEW_BRIGHTNESS", 1.35) or 1.35)
        return _scaled_rgb(color or consts.SEEK_OBJECT_RGB, factor)

    @staticmethod
    def _seek_radius_feet(actor) -> int:
        base_radius = 30
        if actor is None:
            return base_radius
        has_status = getattr(actor, "has_status", None)
        if callable(has_status):
            try:
                if has_status("deafened"):
                    return base_radius
            except Exception:
                pass
        best = base_radius
        for status in getattr(actor, "statuses", []) or []:
            data = getattr(status, "data", None) or {}
            try:
                radius = int(data.get("seek_sense_radius_feet", 0) or 0)
            except Exception:
                radius = 0
            if radius > best:
                best = radius
        return max(base_radius, best)

    @staticmethod
    def _seek_audio_within_feet(actor) -> int:
        default = 30
        if actor is None:
            return default
        best = default
        for status in getattr(actor, "statuses", []) or []:
            data = getattr(status, "data", None) or {}
            try:
                distance = int(data.get("seek_audio_locate_bonus_within_feet", 0) or 0)
            except Exception:
                distance = 0
            if distance > best:
                best = distance
        return max(default, best)

    @staticmethod
    def _seek_scent_within_feet(actor) -> int:
        default = 0
        if actor is None:
            return default
        best = default
        for status in getattr(actor, "statuses", []) or []:
            data = getattr(status, "data", None) or {}
            try:
                distance = int(data.get("seek_scent_locate_bonus_within_feet", 0) or 0)
            except Exception:
                distance = 0
            if distance > best:
                best = distance
        return max(default, best)

    @staticmethod
    def _seek_step_cost(current: tuple[int, int], nxt: tuple[int, int], diag_parity: int) -> tuple[int, int]:
        is_diag = abs(int(current[0]) - int(nxt[0])) == 1 and abs(int(current[1]) - int(nxt[1])) == 1
        step_cost = 10 if (is_diag and diag_parity == 1) else 5
        next_parity = diag_parity ^ 1 if is_diag else diag_parity
        return step_cost, next_parity

    @staticmethod
    def _seek_step_direct(board, current: tuple[int, int], nxt: tuple[int, int]) -> bool:
        in_bounds = getattr(board, "in_bounds", None)
        is_blocked = getattr(board, "is_blocked", None)
        edge_between = getattr(board, "edge_interactables_between", None)
        if not callable(in_bounds) or not callable(is_blocked):
            return False
        if not in_bounds(current) or not in_bounds(nxt):
            return False
        if is_blocked(current, nxt):
            return False
        if callable(edge_between):
            for edge_obj in edge_between(current, nxt):
                blocks_passage = getattr(edge_obj, "blocks_passage", None)
                if callable(blocks_passage) and blocks_passage(current, nxt):
                    return False
        return True

    @classmethod
    def _can_seek_step(cls, board, current: tuple[int, int], nxt: tuple[int, int]) -> bool:
        if abs(int(current[0]) - int(nxt[0])) == 1 and abs(int(current[1]) - int(nxt[1])) == 1:
            mid_a = (int(nxt[0]), int(current[1]))
            mid_b = (int(current[0]), int(nxt[1]))
            route_a = cls._seek_step_direct(board, current, mid_a) and cls._seek_step_direct(board, mid_a, nxt)
            route_b = cls._seek_step_direct(board, current, mid_b) and cls._seek_step_direct(board, mid_b, nxt)
            return bool(route_a or route_b)
        return cls._seek_step_direct(board, current, nxt)

    @staticmethod
    def _can_seek_expand(board, pos: tuple[int, int]) -> bool:
        can_enter = getattr(board, "can_enter", None)
        if not callable(can_enter):
            return True
        try:
            return bool(can_enter(pos, allow_occupied=True))
        except TypeError:
            return bool(can_enter(pos))
        except Exception:
            return False

    @classmethod
    def _reachable_seek_positions(cls, board, origin: tuple[int, int] | None, max_feet: int) -> set[tuple[int, int]]:
        if origin is None:
            return set()
        if max_feet <= 0:
            return {origin}
        in_bounds = getattr(board, "in_bounds", None)
        get_neighbors = getattr(board, "get_neighbors", None)
        if not callable(in_bounds) or not callable(get_neighbors):
            return {origin}

        best_cost_by_state: dict[tuple[tuple[int, int], int], int] = {(origin, 0): 0}
        best_cost_by_pos: dict[tuple[int, int], int] = {origin: 0}
        frontier: list[tuple[int, int, tuple[int, int]]] = [(0, 0, origin)]

        while frontier:
            cost, diag_parity, current = heapq.heappop(frontier)
            if cost != best_cost_by_state.get((current, diag_parity)):
                continue
            for nxt in get_neighbors(current, include_position=False, diagonal=True):
                if not in_bounds(nxt):
                    continue
                if not cls._can_seek_step(board, current, nxt):
                    continue
                step_cost, next_parity = cls._seek_step_cost(current, nxt, diag_parity)
                new_cost = cost + step_cost
                if new_cost > max_feet:
                    continue
                if new_cost < best_cost_by_pos.get(nxt, float("inf")):
                    best_cost_by_pos[nxt] = new_cost
                if not cls._can_seek_expand(board, nxt):
                    continue
                state = (nxt, next_parity)
                if new_cost < best_cost_by_state.get(state, float("inf")):
                    best_cost_by_state[state] = new_cost
                    heapq.heappush(frontier, (new_cost, next_parity, nxt))

        return set(best_cost_by_pos)

    @classmethod
    def _build_seek_positions(
        cls,
        board,
        hero_pos: tuple[int, int],
        allowed_rooms: list[str],
        seek_radius: int,
    ) -> set[tuple[int, int]]:
        reachable = cls._reachable_seek_positions(board, hero_pos, seek_radius)
        if not allowed_rooms:
            return set(reachable or {hero_pos})
        room_positions_fn = getattr(board, "positions_in_rooms", None)
        if not callable(room_positions_fn):
            return {hero_pos}
        room_positions = set(room_positions_fn(set(allowed_rooms)) or set())
        search_positions = reachable.intersection(room_positions) if reachable else set()
        if hero_pos in room_positions or not search_positions:
            search_positions.add(hero_pos)
        return search_positions

    @staticmethod
    def _is_trap_like(obj) -> bool:
        return bool(
            hasattr(obj, "trap_armed")
            and callable(getattr(obj, "detect_trap", None))
            and callable(getattr(obj, "disable_trap", None))
        )

    @classmethod
    def _is_seek_preview_visible(cls, obj) -> bool:
        if bool(getattr(obj, "hide_from_seek_preview", False)):
            return False
        hidden = bool(getattr(obj, "hidden", False))
        revealed = bool(getattr(obj, "revealed", False))
        trap_detected = bool(getattr(obj, "trap_detected", False))
        if hidden and not (revealed or trap_detected):
            return False
        if cls._is_trap_like(obj) and not bool(getattr(obj, "trap_armed", False)):
            return False
        return True

    @staticmethod
    def _seek_preview_descriptor(obj) -> dict[str, object]:
        if bool(
            hasattr(obj, "trap_armed")
            and callable(getattr(obj, "detect_trap", None))
            and callable(getattr(obj, "disable_trap", None))
        ):
            trap_name = str(getattr(obj, "trap_name", "") or "").strip() or "Pułapka"
            return {
                "label": trap_name,
                "legend": "pułapka",
                "color": list(consts.SEEK_TRAP_RGB),
                "color_name": "czerwone",
                "priority": 100,
            }
        label = str(getattr(obj, "seek_label", "") or "").strip()
        if not label:
            label = str(getattr(obj, "name", "") or getattr(obj, "exit_label", "") or obj.__class__.__name__).strip()
        color = getattr(obj, "seek_color", None)
        if not isinstance(color, (list, tuple)) or len(color) < 3:
            color = list(consts.SEEK_OBJECT_RGB)
        color_name = str(getattr(obj, "seek_color_name", "") or "").strip() or "szare"
        return {
            "label": label,
            "legend": label.lower(),
            "color": [int(color[0]), int(color[1]), int(color[2])],
            "color_name": color_name,
            "priority": 10,
        }

    @classmethod
    def _preview_interactables(
        cls,
        board,
        actor,
        game,
        search_positions: set[tuple[int, int]],
    ) -> tuple[dict[tuple[int, int], dict[str, object]], list[dict[str, object]]]:
        preview_by_pos: dict[tuple[int, int], dict[str, object]] = {}
        preview_items: list[dict[str, object]] = []
        seen_labels: set[tuple[str, tuple[int, int, int]]] = set()

        for pos in sorted(set(search_positions or set()), key=lambda item: (int(item[1]), int(item[0]))):
            for obj in list(board.interactables_at(pos) or []):
                if not cls._is_seek_preview_visible(obj):
                    continue
                can_interact = getattr(obj, "can_interact", None)
                if callable(can_interact):
                    try:
                        if not bool(can_interact(actor, game)):
                            continue
                    except Exception:
                        pass
                descriptor = cls._seek_preview_descriptor(obj)
                descriptor["position"] = pos
                preview_items.append(descriptor)
                current = preview_by_pos.get(pos)
                if current is None or int(descriptor.get("priority", 0) or 0) >= int(current.get("priority", 0) or 0):
                    preview_by_pos[pos] = descriptor
                legend_key = (str(descriptor.get("legend", "")).strip().lower(), _color_tuple(descriptor.get("color")))
                seen_labels.add(legend_key)

        legend_entries: list[dict[str, object]] = []
        for legend, color in sorted(seen_labels, key=lambda item: (item[0], item[1])):
            match = next(
                (
                    item for item in preview_items
                    if str(item.get("legend", "")).strip().lower() == legend
                    and _color_tuple(item.get("color")) == color
                ),
                None,
            )
            if match is None:
                continue
            legend_entries.append(
                {
                    "legend": str(match.get("legend") or "").strip(),
                    "color_name": str(match.get("color_name") or "").strip() or "szare",
                    "color": list(match.get("color") or consts.SEEK_OBJECT_RGB),
                }
            )
        legend_entries.sort(key=lambda item: (str(item.get("color_name") or ""), str(item.get("legend") or "")))
        return preview_by_pos, legend_entries

    @staticmethod
    def _seek_preview_legend_markdown(legend_entries: list[dict[str, object]]) -> str:
        if not legend_entries:
            return "- Brak jawnych obiektów interaktywnych w zasięgu."
        lines = []
        for entry in legend_entries:
            color_name = str(entry.get("color_name") or "").strip() or "szare"
            legend = str(entry.get("legend") or "").strip() or "obiekt"
            lines.append(f"- **{color_name.capitalize()}**: {legend}")
        return "\n".join(lines)

    @classmethod
    def _confirm_seek_preview(cls, game, legend_entries: list[dict[str, object]]) -> bool:
        prompt_text = render_prompt_text(
            "interaction.seek_preview",
            legend_block=cls._seek_preview_legend_markdown(legend_entries),
        )
        title = str(prompt_text.get("title") or "Seek")
        summary = str(prompt_text.get("summary") or "Rozejrzyj się po zasięgu akcji.")
        body_markdown = str(prompt_text.get("body_markdown") or "")
        details_markdown = str(prompt_text.get("details_markdown") or "")
        choice_meta = [
            {
                "raw": "confirm",
                "label": "Wykonaj Seek",
                "desc": "Rzuć Perception, aby wykryć ukryte obiekty i pułapki w zasięgu.",
                "key": "Enter",
                "category": "combat",
                "icon": "S",
            },
            {
                "raw": "cancel",
                "label": "Anuluj",
                "desc": "Wycofaj się z akcji Seek bez wykonywania rzutu.",
                "key": "Esc",
                "category": "utility",
                "icon": "X",
            },
        ]
        player_prompt = getattr(game, "player_prompt", None)
        if player_prompt is not None and hasattr(player_prompt, "choice"):
            try:
                answer = player_prompt.choice(
                    title,
                    choices=["confirm", "cancel"],
                    source="seek_preview",
                    subtitle=summary,
                    body_markdown=body_markdown,
                    details_markdown=details_markdown,
                    choice_meta=choice_meta,
                    scope_key="hero_turn:resolution",
                    dedupe_key="interaction.seek_preview",
                    layout="dialog",
                    prompt_id="interaction.seek_preview",
                )
                if answer is not None:
                    return str(answer or "").strip().lower() == "confirm"
            except Exception:
                pass

        ui = getattr(game, "ui", None)
        if ui is None or not getattr(ui, "enabled", False) or not hasattr(ui, "prompt_choice"):
            return True
        answer = ui.prompt_choice(
            title,
            choices=["confirm", "cancel"],
            source="seek_preview",
            prompt_id="interaction.seek_preview",
            prompt_long=body_markdown,
            details_markdown=details_markdown,
            communication={
                "channel": "prompt",
                "priority": "action",
                "semantic_type": "required_action",
                "title": title,
                "summary": summary,
                "body_markdown": body_markdown,
                "details_markdown": details_markdown,
                "blocking": True,
                "context": {"prompt_key": "interaction.seek_preview"},
            },
            choice_meta=choice_meta,
        )
        return str(answer or "").strip().lower() == "confirm"

    @staticmethod
    def _show_seek_area(
        game,
        hero_pos: tuple[int, int],
        search_positions: set[tuple[int, int]],
        preview_by_pos: dict[tuple[int, int], dict[str, object]] | None = None,
    ) -> bool:
        positions = sorted(set(search_positions or {hero_pos}), key=lambda pos: (int(pos[1]), int(pos[0])))
        preview_by_pos = dict(preview_by_pos or {})
        colors = []
        for pos in positions:
            if pos == hero_pos:
                colors.append(list(consts.HERO_HIGHLIGHT_RGB))
                continue
            preview = preview_by_pos.get(pos)
            if preview is not None:
                colors.append(SeekEvent._seek_object_preview_rgb(preview.get("color") or consts.SEEK_OBJECT_RGB))
                continue
            colors.append(SeekEvent._seek_area_preview_rgb())
        try:
            game.conn.set_leds(positions, colors)
            return True
        except Exception:
            return False

    def execute(self, ctx: EventContext) -> EventResult:
        game = ctx.game
        actor = ctx.actor
        if actor not in getattr(game, "heroes", []) or getattr(actor, "position", None) is None:
            heroes_positions = [hero.position for hero in getattr(game, "heroes", []) if hero.position is not None]
            if not heroes_positions:
                logger.warning("Brak bohaterów na planszy.")
                return EventResult.cancelled(message="Brak bohaterów na planszy.")
            game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
            source = game.conn.scan_board(heroes_positions)
            game.conn.leds_off()
            actor = game.board.occupant_at(source)

        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Nie wybrano bohatera do przeszukania.")

        hero_pos = actor.position
        game.events.safe_emit_action(
            actor=actor,
            action_id="seek_start",
            action_tags=self._effective_tags(ctx),
            pos=hero_pos,
        )

        board = game.board
        rooms_here = board.rooms_at(hero_pos)

        allowed_rooms: list[str] = []
        for room_id in rooms_here:
            if board.is_room_seek_locked(room_id):
                logger.info("Pokój %s jest zablokowany po krytycznej porażce.", room_id)
                continue
            if board.room_seek_failures(room_id) >= consts.SEEK_FAIL_MAX_ATTEMPTS:
                logger.info("W pokoju %s wyczerpano próby przeszukania.", room_id)
                continue
            allowed_rooms.append(room_id)

        if rooms_here and not allowed_rooms:
            logger.info("Nie możesz już przeszukiwać żadnego z tych pokoi.")
            return EventResult.noop(message="Brak dostępnych pokoi do przeszukania.")

        seek_radius = self._seek_radius_feet(actor)
        search_positions = self._build_seek_positions(board, hero_pos, allowed_rooms, seek_radius)
        preview_by_pos, legend_entries = self._preview_interactables(board, actor, game, search_positions)
        seek_area_lit = self._show_seek_area(game, hero_pos, search_positions, preview_by_pos)
        if not self._confirm_seek_preview(game, legend_entries):
            if seek_area_lit:
                try:
                    game.conn.leds_off()
                except Exception:
                    pass
            return EventResult.cancelled(message="Przerwano akcję Seek.")

        base_tags = ["seek", Skill.PERCEPTION.value]
        base_resolution = check_resolver.resolve_skill_check_with_sources(
            skill_id=Skill.PERCEPTION.value,
            dc=consts.SEEK_FAIL,
            actor=actor,
            target=None,
            tags=base_tags,
            game=game,
            apply_modifiers=True,
            consume_statuses=False,
        )
        roll = base_resolution.roll
        roll_total = base_resolution.total

        if rooms_here and roll_total < consts.SEEK_CRITICAL_FAIL:
            for room_id in rooms_here:
                board.lock_room_seek(room_id)
            logger.info("Krytyczna porażka – dalsze przeszukiwanie tych pokoi zablokowane.")
            if seek_area_lit:
                try:
                    game.conn.leds_off()
                except Exception:
                    pass
            return EventResult.noop(message="Krytyczna porażka – pokoje zablokowane.")

        newly_revealed_positions: set[tuple[int, int]] = set()
        detected_trap_positions: set[tuple[int, int]] = set()
        reveal_notes: list[str] = []
        trap_notes: list[str] = []
        hidden_candidates = 0
        trap_candidates = 0
        revealed_count = 0
        trap_detected_count = 0

        for pos in search_positions:
            for obj in board.interactables_at(pos):
                is_trap_like = bool(
                    hasattr(obj, "trap_armed")
                    and callable(getattr(obj, "detect_trap", None))
                    and callable(getattr(obj, "disable_trap", None))
                )
                if is_trap_like and bool(getattr(obj, "trap_armed", False)) and not bool(getattr(obj, "trap_detected", False)):
                    trap_candidates += 1
                    trap_tags = base_tags + ["trap", "seek", "search"]
                    trap_resolution = check_resolver.resolve_skill_check_with_sources_from_roll(
                        skill_id=Skill.PERCEPTION.value,
                        dc=int(getattr(obj, "trap_detection_dc", 18) or 18),
                        actor=actor,
                        target=obj,
                        tags=trap_tags,
                        roll=roll,
                        game=game,
                        apply_modifiers=True,
                    )
                    outcome, trap_msg = obj.detect_trap(int(trap_resolution.total or 0))
                    if outcome in ("success", "critical_success"):
                        detected_trap_positions.add(pos)
                        trap_detected_count += 1
                        trap_name = str(getattr(obj, "trap_name", "") or "").strip() or "Pułapka"
                        trap_notes.append(f"{trap_name}: {trap_msg}")
                        logger.info("Wykryto pułapkę %s na polu %s.", trap_name, pos)
                if not getattr(obj, "hidden", False) or getattr(obj, "revealed", False):
                    continue
                if not getattr(obj, "seekable", True):
                    continue
                hidden_candidates += 1
                was_revealed = getattr(obj, "revealed", False)
                obj_tags = list(getattr(obj, "reveal_tags", ()) or ())
                tags = base_tags + [t for t in obj_tags if t not in base_tags]
                if "undetected" not in tags:
                    tags.append("undetected")
                target_distance = grid_distance_feet(hero_pos, pos)
                if target_distance <= 30 and "within_30_feet" not in tags:
                    tags.append("within_30_feet")
                audible = bool(getattr(obj, "audible", False)) or ("auditory" in obj_tags)
                if audible and target_distance <= self._seek_audio_within_feet(actor):
                    if "auditory" not in tags:
                        tags.append("auditory")
                scentable = bool(getattr(obj, "smelly", False)) or bool(getattr(obj, "scentable", False))
                if not scentable:
                    scentable = "scent" in obj_tags or "smelly" in obj_tags
                if scentable and target_distance <= self._seek_scent_within_feet(actor):
                    if "scent" not in tags:
                        tags.append("scent")
                resolution = check_resolver.resolve_skill_check_with_sources_from_roll(
                    skill_id=Skill.PERCEPTION.value,
                    dc=getattr(obj, "reveal_dc", 18),
                    actor=actor,
                    target=obj,
                    tags=tags,
                    roll=roll,
                    game=game,
                    apply_modifiers=True,
                )
                total = resolution.total
                if hasattr(obj, "try_reveal"):
                    obj.try_reveal(total)
                elif total >= getattr(obj, "reveal_dc", 18):
                    obj.revealed = True
                if not was_revealed and getattr(obj, "revealed", False):
                    newly_revealed_positions.add(pos)
                    revealed_count += 1
                    desc = (
                        getattr(obj, "description_on_reveal", None)
                        or getattr(obj, "reveal_description", None)
                        or getattr(obj, "description", None)
                    )
                    if desc:
                        reveal_notes.append(str(desc))
                    on_reveal = getattr(obj, "on_reveal", None)
                    if callable(on_reveal):
                        try:
                            extra = on_reveal(game, source_actor=actor)
                        except TypeError:
                            extra = on_reveal(game)
                        except Exception:
                            extra = None
                        if extra:
                            reveal_notes.append(str(extra))
                    logger.info("Odkrywasz %s na polu %s.", obj.__class__.__name__, pos)

        if hidden_candidates == 0 and trap_candidates == 0:
            logger.info("W wybranych pokojach nie ma ukrytych elementów ani pułapek do przeszukania.")
            if seek_area_lit:
                try:
                    game.conn.leds_off()
                except Exception:
                    pass
            return EventResult.noop(message="Brak ukrytych elementów ani pułapek.")
        if not newly_revealed_positions and not detected_trap_positions:
            logger.info("Przeszukiwanie niczego nie ujawnia.")
            if rooms_here and roll_total < consts.SEEK_FAIL:
                for room_id in allowed_rooms:
                    board.increment_room_seek_fail(room_id)
                logger.info(
                    "Nieudana próba – pozostałe próby: %s",
                    {room: max(0, consts.SEEK_FAIL_MAX_ATTEMPTS - board.room_seek_failures(room)) for room in allowed_rooms},
                )
            if seek_area_lit:
                try:
                    game.conn.leds_off()
                except Exception:
                    pass
            return EventResult.noop(message="Nic nie znaleziono.")

        logger.info(
            "Ujawniono %s ukrytych obiektów i wykryto %s pułapek.",
            revealed_count,
            trap_detected_count,
        )
        game.events.safe_emit_action(
            actor=actor,
            action_id="seek_reveal",
            action_tags=["seek", "reveal"],
            revealed=list(newly_revealed_positions),
            count=revealed_count,
            detected_traps=list(detected_trap_positions),
            traps_count=trap_detected_count,
        )
        reveal_positions = list(newly_revealed_positions.union(detected_trap_positions))
        if seek_area_lit:
            try:
                game.conn.leds_off()
            except Exception:
                pass
        game.conn.set_leds(reveal_positions, consts.HIDDEN_REVEAL_RGB)
        info_text = "Odkryto ukryte obiekty i/lub pułapki."
        if reveal_notes:
            info_text = "Odkryto:\n" + "\n".join(reveal_notes)
        if trap_notes:
            trap_text = "Wykryte pułapki:\n" + "\n".join(trap_notes)
            info_text = f"{info_text}\n{trap_text}" if info_text else trap_text
        ui = get_ui_client()
        if ui.enabled:
            ui.prompt_info("Odkryto coś!", prompt_long=info_text, source="seek")
        else:
            time_to_show = getattr(consts, "SEEK_REVEAL_SECONDS", 3)
            try:
                import time

                time.sleep(time_to_show)
            finally:
                pass
        game.conn.leds_off()

        return EventResult(success=True, consumed_action=self.consumes_action, message="Przeszukiwanie wykonane.")

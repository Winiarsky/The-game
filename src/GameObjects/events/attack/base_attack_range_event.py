from __future__ import annotations

import logging
import math
from typing import Sequence

from bonuses import BonusEffect, BonusType
from GameObjects.interactions_mixin import RangeAttackAffectMixin
from ui_client import get_ui_client
from statuses import Status
from damage_types import DamageType

from .attack_base import AttackEventBase
from ..targeting import is_target_blocked_by_tags
from ..base import EventContext, EventResult

logger = logging.getLogger(__name__)


CoverType = str


class BaseRangeAttackEvent(AttackEventBase):
    """Wspólna logika dla ataków dystansowych (łuki, kusze itd.)."""

    weapon_label: str = "bronią dystansową"
    damage_prompt: str | Sequence[str] = "1k6 + DEX"
    action_id_base: str = "attack_ranged"
    damage_type: str | Sequence[str] = DamageType.PIERCING.value
    range_increment_ft: int = 60
    max_range_increments: int = 6
    feet_per_cell: int = 5
    default_tags = ["attack_ranged", "ranged_attack"]
    consumes_action = True

    COVER_RANK = {"none": 0, "minor": 1, "standard": 2, "greater": 3, "block": 4}
    COVER_AC = {"minor": 1, "standard": 2, "greater": 4}
    COVER_LED = {
        "minor": [30, 120, 0],
        "standard": [90, 90, 0],
        "greater": [150, 60, 0],
        "block": [180, 0, 0],
    }
    TARGET_LED = [0, 40, 140]

    # --- main flow ---
    def execute(self, ctx: EventContext) -> EventResult:  # noqa: C901
        game = ctx.game
        hero = ctx.actor
        if hero is None:
            return EventResult.cancelled(message="Brak bohatera do ataku dystansowego.")
        hero_pos = getattr(hero, "position", None)
        if hero_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        candidates = [(e, getattr(e, "position", None)) for e in getattr(game, "enemies", [])]
        candidates = [(e, pos) for e, pos in candidates if pos is not None]
        tags = self._effective_tags(ctx)
        candidates = [(e, pos) for e, pos in candidates if not is_target_blocked_by_tags(e, tags)]
        if not candidates:
            return EventResult.cancelled(message="Brak wrogów na planszy.")

        analyses = []
        for enemy, pos in candidates:
            analysis = self._analyze_shot(game, hero_pos, pos, target=enemy)
            analysis["enemy"] = enemy
            analyses.append(analysis)

        # LED: przeszkody + potencjalne cele
        led_positions: list[tuple[int, int]] = []
        led_colors: list[list[int]] = []
        obstacle_led: dict[tuple[int, int], CoverType] = {}
        for analysis in analyses:
            for obs in analysis.get("obstacles", []):
                for p in obs["positions"]:
                    current = obstacle_led.get(p, "none")
                    if self.COVER_RANK[obs["cover_type"]] > self.COVER_RANK[current]:
                        obstacle_led[p] = obs["cover_type"]
        for pos, ctype in obstacle_led.items():
            led_positions.append(pos)
            led_colors.append(self.COVER_LED.get(ctype, self.COVER_LED["standard"]))

        hittable = [a for a in analyses if not a["blocked"]]
        for analysis in hittable:
            led_positions.append(analysis["target_pos"])
            led_colors.append(self.TARGET_LED)

        if led_positions:
            try:
                game.conn.set_leds(led_positions, led_colors)
            except Exception as exc:
                logger.warning("Nie udało się ustawić LEDów: %s", exc)

        try:
            if not hittable:
                return EventResult.cancelled(message="Brak wrogów w zasięgu lub linia strzału zablokowana.")

            target_pos_list = [a["target_pos"] for a in hittable]
            try:
                choice = game.conn.scan_board(target_pos_list)
            except Exception:
                choice = None
            target_analysis = None
            for a in hittable:
                if a["target_pos"] == choice:
                    target_analysis = a
                    break
            if target_analysis is None:
                return EventResult.cancelled(message="Nie wybrano poprawnego celu.")

            enemy = target_analysis["enemy"]
            target_pos = target_analysis["target_pos"]
            cover_type = target_analysis["cover_type"]
            cover_bonus = self.COVER_AC.get(cover_type, 0)
            distance_ft = target_analysis["distance_ft"]
            range_penalty = target_analysis["range_penalty"]
            increments = target_analysis["increments"]

            cover_bonus_effect = None
            if cover_bonus:
                cover_bonus_effect = BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=cover_bonus,
                    tag="ac",
                    source=f"cover:{cover_type}",
                    target_id=getattr(hero, "object_id", None),
                    label=f"osłona ({cover_type})",
                )

            target_ac, base_ac, modifier = self._ac_with_bonuses(
                enemy,
                attacker=hero,
                extra_bonuses=[cover_bonus_effect] if cover_bonus_effect else None,
            )

            game.events.safe_emit_action(
                actor=hero,
                action_id=f"{self.action_id_base}_pre",
                action_tags=self._effective_tags(ctx),
                target=enemy,
                target_pos=target_pos,
            )

            mods: list[str] = []
            if cover_bonus:
                mods.append(f"+{cover_bonus} osłona ({cover_type})")
            if range_penalty:
                mods.append(f"-{range_penalty} zasięg ({increments}x{self.range_increment_ft} stóp)")
            mods_note = "; ".join(mods) if mods else "brak"

            action_tag = (self._effective_tags(ctx) or ["attack_ranged"])[0]
            bonus_info = self._format_bonus_info(hero, action_tag, target=enemy)

            from ui_client import get_ui_client

            roll = get_ui_client().prompt_roll(
                f"Atak {self.weapon_label} na AC {target_ac}",
                source="game",
                layout="test",
                subtitle=f"bazowe {base_ac}, modyfikatory: {mods_note}",
                prompt_long=bonus_info.strip(),
                answer_placeholder="Wynik k20 + DEX",
            )
            critical = roll >= target_ac + 10
            hit = roll >= target_ac
            if not hit:
                game.events.safe_emit_action(
                    actor=hero,
                    action_id=f"{self.action_id_base}_miss",
                    action_tags=self._effective_tags(ctx),
                    target=enemy,
                    target_pos=target_pos,
                    roll=roll,
                    target_ac=target_ac,
                    cover=cover_type,
                    range_penalty=range_penalty,
                )
                self._apply_range_attacker_status(hero)
                return EventResult(success=True, consumed_action=self.consumes_action, message="Strzał chybia.")

            prompt_prefix = "Trafienie krytyczne! " if critical else "Trafienie! "
            damage_components = self._collect_damage_components(prompt_prefix=prompt_prefix)
            defeated = False
            try:
                defeated = self._apply_damage_components(enemy, damage_components)
            except Exception as exc:
                logger.error("Błąd przy zadawaniu obrażeń: %s", exc)
                return EventResult(success=False, consumed_action=False, message=str(exc))

            game.events.safe_emit_action(
                actor=hero,
                action_id=self.action_id_base,
                action_tags=self._effective_tags(ctx),
                target=enemy,
                target_pos=target_pos,
                damage=sum(d for _, d in damage_components),
                damage_components=damage_components,
                defeated=defeated,
                cover=cover_type,
                range_penalty=range_penalty,
                critical=critical,
            )

            if defeated:
                try:
                    game.board.remove(target_pos)
                    try:
                        game.enemies.remove(enemy)
                    except ValueError:
                        pass
                except Exception as exc:
                    logger.error("Nie udało się usunąć wroga: %s", exc)
                enemy.position = None

            self._apply_range_attacker_status(hero)
            msg = "Przeciwnik pokonany." if defeated else ("Trafienie krytyczne!" if critical else f"Atak {self.weapon_label} trafia.")
            return EventResult(success=True, consumed_action=self.consumes_action, message=msg, data={"critical": critical})
        finally:
            try:
                game.conn.leds_off()
            except Exception:
                pass

    # --- helpers ---
    def _apply_range_attacker_status(self, hero) -> None:
        try:
            if hasattr(hero, "add_status"):
                hero.add_status(Status(id="range_attacker", label="Range attacker"))
        except Exception:
            logger.debug("Nie udało się nadać statusu range_attacker.", exc_info=True)

    def _cover_rank(self, cover_type: CoverType) -> int:
        return self.COVER_RANK.get(cover_type, 0)

    # --- damage helpers ---
    def _collect_damage_components(self, *, prompt_prefix: str = "") -> list[tuple[str, int]]:
        """Pozyskaj wartości obrażeń dla 1+ typów."""
        if isinstance(self.damage_type, str):
            dmg = get_ui_client().prompt_roll(
                f"{prompt_prefix}Obrażenia {self.damage_prompt}: ",
                source="game",
                layout="damage",
                answer_placeholder="Suma obrażeń",
            )
            return [(self.damage_type, dmg)]

        damage_types = list(self.damage_type)
        components: list[tuple[str, int]] = []
        for idx, dtype in enumerate(damage_types):
            prompt = self.damage_prompt
            if isinstance(prompt, (list, tuple)):
                prompt_text = prompt[idx] if idx < len(prompt) else prompt[-1]
            else:
                prompt_text = prompt
            roll = get_ui_client().prompt_roll(
                f"{prompt_prefix}Obrażenia {prompt_text} ({dtype}): ",
                source="game",
                layout="damage",
                answer_placeholder=f"Obrażenia {dtype}",
            )
            components.append((dtype, roll))
        return components

    @staticmethod
    def _apply_damage_components(target, comps):
        defeated = False
        for dmg_type, amount in comps:
            _, defeated = target.apply_damage(amount, dmg_type)
        return defeated

    def _line_cells(self, start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
        """Prosty Bresenham na siatce."""
        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        cells: list[tuple[int, int]] = []
        while True:
            cells.append((x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
        return cells

    def _analyze_shot(self, game, start: tuple[int, int], end: tuple[int, int], *, target) -> dict:
        board = game.board
        line = self._line_cells(start, end)
        obstacles: list[dict] = []
        cover_type: CoverType = "none"
        blocked = False
        seen_ids: set[int] = set()

        # dystans / zakres
        dx, dy = abs(start[0] - end[0]), abs(start[1] - end[1])
        distance_ft = math.sqrt(dx * dx + dy * dy) * self.feet_per_cell
        increments = max(1, math.ceil(distance_ft / self.range_increment_ft))
        range_penalty = max(0, increments - 1) * 2
        if increments > self.max_range_increments:
            blocked = True
            cover_type = "block"

        # pola pomiędzy
        for idx, pos in enumerate(line[1:]):  # pomijamy start
            if pos == end:
                break
            occupant = board.occupant_at(pos)
            if occupant is target:
                continue
            ctype = None
            if occupant:
                if occupant in getattr(game, "heroes", []):
                    ctype = None  # sojusznik nie daje osłony
                elif occupant in getattr(game, "enemies", []):
                    ctype = "minor"
                elif isinstance(occupant, RangeAttackAffectMixin):
                    ctype = occupant.range_cover_type()
            if ctype:
                obstacles.append({"positions": [pos], "cover_type": ctype, "source": occupant})
                if self._cover_rank(ctype) > self._cover_rank(cover_type):
                    cover_type = ctype
                if ctype == "block":
                    blocked = True

            for obj in board.interactables_at(pos):
                if id(obj) in seen_ids:
                    continue
                if isinstance(obj, RangeAttackAffectMixin):
                    seen_ids.add(id(obj))
                    ctype = obj.range_cover_type()
                    obstacles.append({"positions": [pos], "cover_type": ctype, "source": obj})
                    if self._cover_rank(ctype) > self._cover_rank(cover_type):
                        cover_type = ctype
                    if ctype == "block":
                        blocked = True

        # krawędzie między kolejnymi polami
        for a, b in zip(line, line[1:]):
            if board.is_blocked(a, b):
                ctype = "block"
                obstacles.append({"positions": [a, b], "cover_type": ctype, "source": board.get_wall(a, b)})
                cover_type = "block"
                blocked = True
            for obj in board.edge_interactables_between(a, b):
                if id(obj) in seen_ids:
                    continue
                if isinstance(obj, RangeAttackAffectMixin):
                    seen_ids.add(id(obj))
                    ctype = obj.range_cover_type()
                    obstacles.append({"positions": [a, b], "cover_type": ctype, "source": obj})
                    if self._cover_rank(ctype) > self._cover_rank(cover_type):
                        cover_type = ctype
                    if ctype == "block":
                        blocked = True

        if getattr(target, "has_status", lambda _s: False)("prone"):
            if self._cover_rank("greater") > self._cover_rank(cover_type):
                cover_type = "greater"

        return {
            "target_pos": end,
            "cover_type": cover_type,
            "blocked": blocked,
            "obstacles": obstacles,
            "distance_ft": distance_ft,
            "increments": increments,
            "range_penalty": range_penalty,
        }

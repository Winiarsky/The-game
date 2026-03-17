from __future__ import annotations

import logging
import re

from bonuses import BonusEffect, BonusType
from damage_types import DamageType
from GameObjects.interactions_mixin import prompt_for_roll
from GameObjects.items.inventory import (
    consume_ready_event_item,
    ensure_actor_inventory,
    get_equipped_weapons,
    has_ready_event_item,
    item_label,
    missing_event_item_reason,
    ready_event_items,
)
from economy import refresh_actor_bulk_state
from localization import localized_hint_pl, localize_term_pl
from statuses import Status

from ...base import ActionCostEvent, EventContext, EventResult
from ...bombs.base_alchemical_bomb_event import BaseAlchemicalBombEvent
from ...registry import dispatch_event, list_events, register_event

logger = logging.getLogger(__name__)


def _normalize(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _first_line(text: object) -> str:
    for raw_line in str(text or "").splitlines():
        line = str(raw_line or "").strip()
        if line:
            return line
    return ""


def _spell_tier_label(tags: set[str]) -> str:
    if "cantrip" in tags:
        return "Cantrip"
    if "focus" in tags:
        return "Focus"
    for tag in sorted(tags):
        if not tag.startswith("rank"):
            continue
        digits = "".join(ch for ch in tag if ch.isdigit())
        if digits:
            return f"Ranga {max(1, int(digits))}"
    return "Czar"


def _spell_actions_label(event_cls) -> str:
    try:
        cost = max(1, int(getattr(event_cls, "actions_cost", 1) or 1))
    except Exception:
        cost = 1
    return f"Koszt: {cost} akcja" if cost == 1 else f"Koszt: {cost} akcje"


def _spell_range_label(event_cls, tags: set[str]) -> str:
    range_raw = getattr(event_cls, "range_feet", None)
    if isinstance(range_raw, int):
        return f"Zasieg: {max(0, int(range_raw))} ft"
    if "touch" in tags:
        return "Zasieg: dotyk"
    return "Zasieg: wlasny"


def _spell_traditions_label(tags: set[str]) -> str:
    traditions = [item for item in ("arcane", "divine", "occult", "primal") if item in tags]
    if not traditions:
        return "Tradycja: -"
    return "Tradycja: " + ", ".join(localize_term_pl(item) for item in traditions)


def _spell_detail_lines(spell_id: str) -> tuple[str, list[str], list[str]]:
    normalized = _normalize(spell_id)
    if not normalized:
        return "", [], []
    event_cls = dict(list_events() or {}).get(normalized)
    if event_cls is None:
        label = localize_term_pl(normalized)
        hint = str(localized_hint_pl(normalized) or "").strip()
        detail_lines = [hint] if hint else [f"Jednorazowo rzucasz czar: {label}."]
        return label, detail_lines, []

    tags: set[str] = set()
    for tag in list(getattr(event_cls, "spell_tags", []) or []):
        value = _normalize(tag)
        if value:
            tags.add(value)
    for tag in list(getattr(event_cls, "default_tags", []) or []):
        value = _normalize(tag)
        if value:
            tags.add(value)
    for tradition in list(getattr(event_cls, "magic_traditions", []) or []):
        value = _normalize(getattr(tradition, "value", tradition))
        if value == "arcana":
            value = "arcane"
        if value:
            tags.add(value)

    label = localize_term_pl(normalized)
    meta_lines = [
        _spell_tier_label(tags),
        _spell_actions_label(event_cls),
        _spell_range_label(event_cls, tags),
        _spell_traditions_label(tags),
    ]

    raw_desc = str(getattr(event_cls, "prompt_description", "") or "").strip()
    if not raw_desc:
        raw_desc = str(localized_hint_pl(normalized) or "").strip()
    if not raw_desc:
        raw_desc = str(getattr(event_cls, "prompt", "") or "").strip()

    detail_lines: list[str] = []
    for piece in re.split(r"(?:\n+|(?<=[\.\!\?])\s+)", raw_desc):
        line = str(piece or "").strip().lstrip("-•").strip()
        if not line:
            continue
        if line not in detail_lines:
            detail_lines.append(line)
    if not detail_lines:
        detail_lines.append(f"Jednorazowo rzucasz czar: {label}.")
    return label, detail_lines, meta_lines


def _scroll_spell_choice_desc(spell_id: str) -> str:
    label, detail_lines, meta_lines = _spell_detail_lines(spell_id)
    lines = [
        f"Fluff: Jednorazowy zwoj z czarem: {label}.",
        "Mechanika:",
        "- Kiedy: Po wybraniu tej opcji.",
        "- Efekt:",
    ]
    for item in meta_lines + detail_lines:
        text = str(item or "").strip()
        if text:
            lines.append(f"  - {text}")
    return "\n".join(lines)


def _scroll_spell_item_description(spell_id: str) -> str:
    label, detail_lines, meta_lines = _spell_detail_lines(spell_id)
    parts = [f"Jednorazowo rzuca czar: {label}."]
    if meta_lines:
        meta_text = ". ".join(str(item or "").strip().rstrip(".") for item in meta_lines if str(item or "").strip())
        if meta_text:
            parts.append(meta_text + ".")
    if detail_lines:
        parts.append(" ".join(detail_lines))
    return " ".join(str(part or "").strip() for part in parts if str(part or "").strip()).strip()


def _target_has_any_tag(target, tags: tuple[str, ...]) -> bool:
    if target is None:
        return False
    has_tag = getattr(target, "has_tag", None)
    if callable(has_tag):
        for tag in tags:
            try:
                if bool(has_tag(tag)):
                    return True
            except Exception:
                continue
    target_tags = {str(t).strip().lower() for t in (getattr(target, "tags", None) or [])}
    enemy_type = getattr(target, "enemy_type", None)
    if enemy_type is not None:
        target_tags.add(str(getattr(enemy_type, "value", enemy_type)).strip().lower())
    for tag in tags:
        if str(tag).strip().lower() in target_tags:
            return True
    return False


def _status_weakness(target, key: str) -> int:
    if target is None:
        return 0
    highest = 0
    for status in list(getattr(target, "statuses", []) or []):
        data = getattr(status, "data", None) or {}
        try:
            value = int(data.get(key, 0) or 0)
        except Exception:
            value = 0
        highest = max(highest, value)
    return max(0, highest)


class _MagicalWaterBombEvent(BaseAlchemicalBombEvent):
    actions_cost = 1
    range_feet = 20
    default_tags = ["attack_ranged", "ranged_attack", "bomb", "magic", "consumable"]
    tier_choices = ("standard",)
    tiers = {"standard": {"item_bonus": 0, "damage_dice": "1d6", "splash": 0}}

    def _prompt_level(self) -> str | None:
        return "standard"

    def _prompt_damage(self, tier: str, dice: str) -> int:
        return int(
            prompt_for_roll(
                f"{self._event_label()} ({tier}) – podaj obrażenia ({dice}):",
                source=self.name,
                layout="damage",
                subtitle="Wynik = kosc + modyfikatory.",
                answer_placeholder="Wynik kosci",
                roll_stack={
                    "components": [
                        {
                            "id": "damage_die",
                            "label": "Rzut kosci",
                            "value": 0,
                            "description": f"Wynik rzutu {dice}.",
                            "editable": True,
                        },
                        {
                            "id": "ability",
                            "label": "Cecha",
                            "value": 0,
                            "description": "Modyfikator cechy (jesli dotyczy).",
                            "editable": True,
                        },
                        {
                            "id": "item",
                            "label": "Przedmiot",
                            "value": 0,
                            "description": "Premia/kara z przedmiotu.",
                            "editable": True,
                        },
                        {
                            "id": "status",
                            "label": "Status",
                            "value": 0,
                            "description": "Premia/kara status.",
                            "editable": True,
                        },
                        {
                            "id": "circumstance",
                            "label": "Okolicznosci",
                            "value": 0,
                            "description": "Premia/kara circumstance.",
                            "editable": True,
                        },
                    ],
                    "auto_total_modifier": 0,
                },
                auto_total_modifier=0,
            )
            or 0
        )


@register_event
class HolyWaterEvent(_MagicalWaterBombEvent):
    name = "holy_water"
    required_inventory_event_name = "holy_water"
    damage_type = DamageType.GOOD.value
    prompt_description = (
        "Woda swiecona (consumable magic item, 3 gp).\n"
        "Rzucasz jak bomba (20 ft).\n"
        "Trafienie: 1k6 obrazen good fiendom/nieumarlym lub innym celom z weakness to good."
    )

    def _apply_on_hit(self, ctx, target, target_pos, tier, tier_data, *, critical: bool = False) -> None:
        valid_target = _target_has_any_tag(target, ("fiend", "demon", "devil", "undead"))
        valid_target = valid_target or _status_weakness(target, "weakness_good") > 0
        if not valid_target:
            try:
                ctx.game.ui_log("Woda swiecona trafia, ale cel nie jest podatny na obrazenia good.")
            except Exception:
                pass
            return
        damage = self._prompt_damage(tier, str(tier_data.get("damage_dice", "1d6")))
        if critical:
            damage *= 2
        self._apply_damage(target, damage, self.damage_type)


@register_event
class UnholyWaterEvent(_MagicalWaterBombEvent):
    name = "unholy_water"
    required_inventory_event_name = "unholy_water"
    damage_type = DamageType.EVIL.value
    prompt_description = (
        "Woda plugawa (consumable magic item, 3 gp).\n"
        "Rzucasz jak bomba (20 ft).\n"
        "Trafienie: 1k6 obrazen evil celestials lub innym celom z weakness to evil."
    )

    def _apply_on_hit(self, ctx, target, target_pos, tier, tier_data, *, critical: bool = False) -> None:
        valid_target = _target_has_any_tag(target, ("celestial", "angel", "azata", "archon"))
        valid_target = valid_target or _status_weakness(target, "weakness_evil") > 0
        if not valid_target:
            try:
                ctx.game.ui_log("Woda plugawa trafia, ale cel nie jest podatny na obrazenia evil.")
            except Exception:
                pass
            return
        damage = self._prompt_damage(tier, str(tier_data.get("damage_dice", "1d6")))
        if critical:
            damage *= 2
        self._apply_damage(target, damage, self.damage_type)


@register_event
class MinorHealingPotionEvent(ActionCostEvent):
    name = "minor_healing_potion"
    actions_cost = 1
    consumes_action = True
    default_tags = ["magic", "consumable", "healing", "manipulate"]
    required_inventory_event_name = "minor_healing_potion"
    prompt_description = "Mikstura leczenia (slaba): po wypiciu odzyskujesz 1k8 HP."

    def pre(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do wypicia mikstury.")
        if not has_ready_event_item(actor, self.required_inventory_event_name):
            return EventResult.cancelled(message=missing_event_item_reason(actor, self.required_inventory_event_name))
        return super().pre(ctx)

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do wypicia mikstury.")
        heal = int(
            prompt_for_roll(
                "Mikstura leczenia (slaba) – podaj leczenie (1d8):",
                layout="damage",
                subtitle="Wynik = kosc + modyfikatory.",
                source=self.name,
                answer_placeholder="Wynik kosci",
                roll_stack={
                    "components": [
                        {
                            "id": "heal_die",
                            "label": "Rzut kosci",
                            "value": 0,
                            "description": "Wynik rzutu 1d8.",
                            "editable": True,
                        },
                        {
                            "id": "item",
                            "label": "Przedmiot",
                            "value": 0,
                            "description": "Premia/kara item do leczenia.",
                            "editable": True,
                        },
                        {
                            "id": "status",
                            "label": "Status",
                            "value": 0,
                            "description": "Premia/kara status do leczenia.",
                            "editable": True,
                        },
                        {
                            "id": "circumstance",
                            "label": "Okolicznosci",
                            "value": 0,
                            "description": "Premia/kara circumstance do leczenia.",
                            "editable": True,
                        },
                    ],
                    "auto_total_modifier": 0,
                },
                auto_total_modifier=0,
            )
            or 0
        )
        if not consume_ready_event_item(actor, self.required_inventory_event_name):
            return EventResult.cancelled(message=missing_event_item_reason(actor, self.required_inventory_event_name))

        healer = getattr(actor, "heal", None)
        if callable(healer):
            try:
                healer(max(0, int(heal)))
            except Exception:
                pass

        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            actions_spent=self.actions_cost,
            message=f"Wypito miksture leczenia: +{max(0, int(heal))} HP.",
            data={"healed": max(0, int(heal))},
        )


def _scroll_rank1_spell_choices() -> list[str]:
    preferred = [
        "magic_missile",
        "magic_weapon",
        "mage_armor",
        "heal",
        "harm",
        "fear",
        "burning_hands",
        "shocking_grasp",
        "command",
        "grease",
        "true_strike",
        "soothe",
    ]
    available = set(list_events().keys())
    choices = [name for name in preferred if _normalize(name) in available]
    if choices:
        return choices
    return sorted(
        name
        for name, cls in list_events().items()
        if "rank1" in {str(tag).strip().lower() for tag in list(getattr(cls, "spell_tags", []) or [])}
    )


def choose_common_rank1_scroll_spell(
    game,
    *,
    source: str,
    choices: list[str] | None = None,
    title: str = "Zwoj czaru 1. rangi",
    subtitle: str = "8/2 nawigacja, Enter potwierdzenie.",
    prompt_long: str = "Wybierz czar wspólny 1. rangi dla tego zwoju.",
) -> str | None:
    choices = list(choices or _scroll_rank1_spell_choices())
    if not choices:
        return None
    ui = getattr(game, "ui", None)
    if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_choice"):
        choice_meta = []
        labels = []
        for name in choices:
            label = localize_term_pl(name)
            labels.append(label)
            choice_meta.append(
                {
                    "raw": name,
                    "label": label,
                    "desc": _scroll_spell_choice_desc(name),
                    "key": "",
                }
            )
        answer = ui.prompt_choice(
            "Zwoj: wybierz czar 1. rangi",
            choices=labels,
            source=source,
            layout="menu_numpad",
            title=title,
            subtitle=subtitle,
            prompt_long=prompt_long,
            choice_meta=choice_meta,
        )
        raw = _normalize(answer)
        if raw in {_normalize(name) for name in choices}:
            return raw
        if str(answer or "").strip().isdigit():
            idx = int(str(answer).strip()) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        for name, label in zip(choices, labels):
            if _normalize(answer) == _normalize(label):
                return name
        return None
    # fallback bez UI
    return choices[0]


def _prompt_scroll_spell(ctx: EventContext, choices: list[str]) -> str | None:
    return choose_common_rank1_scroll_spell(
        ctx.game,
        source="scroll_common_rank1",
        choices=choices,
        title="Zwoj czaru 1. rangi",
        subtitle="8/2 nawigacja, Enter potwierdzenie.",
        prompt_long="Rzucasz wybrany czar bez zuzycia slotu postaci (zuzywa zwoj).",
    )


def configure_common_rank1_scroll(item, spell_id: str):
    normalized_spell = _normalize(spell_id)
    if not normalized_spell:
        return item
    label = localize_term_pl(normalized_spell)
    try:
        setattr(item, "scroll_spell_id", normalized_spell)
    except Exception:
        pass
    try:
        setattr(item, "name", f"Zwoj: {label}")
    except Exception:
        pass
    description = _scroll_spell_item_description(normalized_spell)
    try:
        setattr(item, "description", description)
    except Exception:
        pass
    return item


def prepare_common_rank1_scroll_purchase(
    game,
    item,
    *,
    source: str,
    title: str,
    subtitle: str,
    prompt_long: str,
) -> bool:
    spell_id = choose_common_rank1_scroll_spell(
        game,
        source=source,
        title=title,
        subtitle=subtitle,
        prompt_long=prompt_long,
    )
    if not spell_id:
        return False
    configure_common_rank1_scroll(item, spell_id)
    return True


def configured_common_rank1_scroll_spell(item) -> str:
    return _normalize(getattr(item, "scroll_spell_id", ""))


def _consume_inventory_item(actor, item) -> bool:
    inventory = ensure_actor_inventory(actor)
    target_iid = str(getattr(item, "instance_id", "") or "").strip()
    for existing in list(inventory):
        existing_iid = str(getattr(existing, "instance_id", "") or "").strip()
        if target_iid and existing_iid != target_iid:
            continue
        if target_iid or existing is item:
            inventory.remove(existing)
            try:
                setattr(actor, "inventory", inventory)
            except Exception:
                pass
            refresh_actor_bulk_state(actor, inventory=inventory)
            return True
    return False


def _select_scroll_item(ctx: EventContext, items: list[object]) -> object | None:
    ready_items = list(items or [])
    if not ready_items:
        return None
    if len(ready_items) == 1:
        return ready_items[0]

    ui = getattr(ctx.game, "ui", None)
    if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_choice"):
        labels: list[str] = []
        choice_meta: list[dict[str, str]] = []
        for idx, item in enumerate(ready_items, start=1):
            spell_id = configured_common_rank1_scroll_spell(item)
            if spell_id:
                label = item_label(item)
                desc = str(getattr(item, "description", "") or "").strip() or f"Czar ze zwoju: {localize_term_pl(spell_id)}."
            else:
                label = f"{item_label(item)} (bez wybranego czaru)"
                desc = "Legacy/generyczny zwoj. Przy aktywacji wybierzesz czar."
            labels.append(label)
            choice_meta.append(
                {
                    "raw": str(idx),
                    "label": label,
                    "desc": desc,
                    "key": str(idx),
                }
            )
        answer = ui.prompt_choice(
            "Zwoj: wybierz konkretny egzemplarz",
            choices=labels,
            source="scroll_common_rank1_item",
            layout="menu_numpad",
            title="Ktorego zwoju chcesz uzyc?",
            subtitle="8/2 nawigacja, Enter potwierdzenie.",
            prompt_long="Jesli masz kilka zwojow 1. rangi, najpierw wybierasz konkretny egzemplarz.",
            choice_meta=choice_meta,
        )
        raw = str(answer or "").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(ready_items):
                return ready_items[idx]
        lowered = _normalize(raw)
        for item, label in zip(ready_items, labels):
            if lowered == _normalize(label):
                return item
    return ready_items[0]


@register_event
class ScrollCommonRank1Event(ActionCostEvent):
    name = "scroll_common_rank1"
    actions_cost = 1
    consumes_action = True
    default_tags = ["magic", "consumable", "scroll", "manipulate"]
    required_inventory_event_name = "scroll_common_rank1"
    prompt_description = (
        "Zwoj wspolnego czaru 1. rangi (4 gp).\n"
        "Wybierasz czar z listy i rzucasz go jak normalna akcje magiczna.\n"
        "Zwoj jest zuzywany po udanym rzuceniu."
    )

    def pre(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do aktywacji zwoju.")
        if not has_ready_event_item(actor, self.required_inventory_event_name):
            return EventResult.cancelled(message=missing_event_item_reason(actor, self.required_inventory_event_name))
        return super().pre(ctx)

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do aktywacji zwoju.")
        scroll_item = _select_scroll_item(ctx, ready_event_items(actor, self.required_inventory_event_name))
        if scroll_item is None:
            return EventResult.cancelled(message=missing_event_item_reason(actor, self.required_inventory_event_name))

        selected_spell = configured_common_rank1_scroll_spell(scroll_item)
        if not selected_spell:
            choices = _scroll_rank1_spell_choices()
            if not choices:
                return EventResult.cancelled(message="Brak dostępnych czarów 1. rangi do użycia ze zwoju.")
            selected_spell = _prompt_scroll_spell(ctx, choices)
            if not selected_spell:
                return EventResult.cancelled(message="Nie wybrano czaru ze zwoju.")

        if _normalize(selected_spell) not in set(_scroll_rank1_spell_choices()) and _normalize(selected_spell) not in set(list_events().keys()):
            return EventResult.cancelled(message="Ten zwoj ma nieznany lub nieobslugiwany czar.")

        spell_state = getattr(actor, "spell_state", None)
        restore_enforce = None
        if isinstance(spell_state, dict):
            restore_enforce = bool(spell_state.get("enforce", False))
            try:
                spell_state["enforce"] = False
                setattr(actor, "spell_state", spell_state)
            except Exception:
                pass

        try:
            spell_result = dispatch_event(
                selected_spell,
                EventContext(
                    game=ctx.game,
                    actor=actor,
                    tags=list(ctx.tags or []) + ["scroll_cast"],
                    metadata=dict(ctx.metadata or {}),
                ),
            )
        finally:
            if isinstance(spell_state, dict) and restore_enforce is not None:
                try:
                    spell_state["enforce"] = bool(restore_enforce)
                    setattr(actor, "spell_state", spell_state)
                except Exception:
                    pass

        if not spell_result.success:
            return EventResult(
                success=False,
                consumed_action=bool(spell_result.consumed_action),
                actions_spent=spell_result.actions_spent,
                message=spell_result.message or "Czar ze zwoju nie powiodl sie.",
                data=dict(spell_result.data or {}),
            )

        if not _consume_inventory_item(actor, scroll_item):
            return EventResult.cancelled(message=missing_event_item_reason(actor, self.required_inventory_event_name))

        message = spell_result.message or f"Rzucono czar: {localize_term_pl(selected_spell)}."
        return EventResult(
            success=True,
            consumed_action=bool(spell_result.consumed_action),
            actions_spent=spell_result.actions_spent,
            message=f"Zuzyto zwoj. {message}",
            data={**dict(spell_result.data or {}), "scroll_spell": selected_spell},
        )


def _select_weapon_for_potency(ctx: EventContext, actor):
    weapons = [item for item in list(get_equipped_weapons(actor) or []) if _normalize(getattr(item, "item_id", "")) != "unarmed"]
    if not weapons:
        return None
    if len(weapons) == 1:
        return weapons[0]
    ui = getattr(ctx.game, "ui", None)
    if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_choice"):
        labels = [item_label(item) for item in weapons]
        answer = ui.prompt_choice(
            "Potency Crystal: wybierz bron",
            choices=labels,
            source="potency_crystal",
            layout="menu_numpad",
            title="Potency Crystal",
            subtitle="8/2 nawigacja, Enter potwierdzenie.",
            prompt_long="Premia +1 item do ataku bronia do konca biezacej tury.",
        )
        raw = str(answer or "").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(weapons):
                return weapons[idx]
        low = _normalize(raw)
        for item in weapons:
            if low == _normalize(item_label(item)):
                return item
    return weapons[0]


@register_event
class PotencyCrystalEvent(ActionCostEvent):
    name = "potency_crystal"
    actions_cost = 1
    consumes_action = True
    default_tags = ["magic", "consumable", "manipulate"]
    required_inventory_event_name = "potency_crystal"
    prompt_description = (
        "Krysztal potencji (4 gp).\n"
        "Aktywujesz przy trzymanej broni.\n"
        "Do konca tury: +1 item do atakow bronia."
    )

    def pre(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do aktywacji talizmanu.")
        if not has_ready_event_item(actor, self.required_inventory_event_name):
            return EventResult.cancelled(message=missing_event_item_reason(actor, self.required_inventory_event_name))
        return super().pre(ctx)

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do aktywacji talizmanu.")
        weapon = _select_weapon_for_potency(ctx, actor)
        if weapon is None:
            return EventResult.cancelled(message="Potency Crystal wymaga aktywnej broni (nie unarmed).")

        remove_prefix = getattr(actor, "remove_bonuses_with_prefix", None)
        if callable(remove_prefix):
            try:
                remove_prefix("potency_crystal:")
            except Exception:
                pass
        for tag in ("attack_melee", "attack_ranged"):
            try:
                actor.add_bonus(
                    BonusEffect(
                        type=BonusType.ITEM,
                        value=1,
                        tag=tag,
                        source="potency_crystal:attack",
                        label="potency crystal",
                        duration_turns=1,
                    )
                )
            except Exception:
                pass
        try:
            actor.remove_status("potency_crystal_active")
        except Exception:
            pass
        try:
            actor.add_status(
                Status(
                    id="potency_crystal_active",
                    label="Potency Crystal",
                    duration=1,
                    data={"ui_description": "+1 item do ataku bronia do konca tury."},
                )
            )
        except Exception:
            pass

        if not consume_ready_event_item(actor, self.required_inventory_event_name):
            return EventResult.cancelled(message=missing_event_item_reason(actor, self.required_inventory_event_name))

        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            actions_spent=self.actions_cost,
            message=f"Aktywowano Potency Crystal na broni: {item_label(weapon)} (+1 item do ataku do konca tury).",
        )

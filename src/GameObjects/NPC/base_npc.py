import json
import logging
import math
from pathlib import Path
from typing import Optional, Callable, Iterable

from GameObjects.base import GameObjectMeta
from GameObjects.items.alchemical_item import (
    AlchemicalItem,
    alchemical_item_defaults,
    alchemical_item_name_from_event,
    normalize_alchemical_event_id,
)
from GameObjects.items.armor import create_armor
from GameObjects.items.equipment import create_equipment
from GameObjects.items.inventory import add_item, item_description, item_label
from GameObjects.items.shield import create_shield
from GameObjects.items.weapon import create_weapon
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin import (
    SocialMixin,
    TradeMixin,
    TradeItem,
    PickpocketMixin,
    resolve_skill_check,
    attitude_label,
    prompt_for_roll,
)
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event
from economy import add_actor_cp, can_actor_afford_cp, format_actor_money, format_cp_value, spend_actor_cp
from services import (
    add_service_spell_to_actor,
    apply_service_effect,
    choose_spell_for_service,
    create_service,
    merchant_spell_capacity,
    merchant_spell_count,
    parse_service_rank,
)
from skills import Skill

logger = logging.getLogger(__name__)

DIALOGS_DIR = Path(__file__).resolve().parents[1] / "dialogs"
_MERCHANT_TIER_ORDER: tuple[str, ...] = ("novice", "adept", "master")
_MERCHANT_TIER_SPELL_MAX_RANK: dict[str, int] = {
    "novice": 1,
    "adept": 3,
    "master": 9,
}


class BaseNPC(SocialMixin, TradeMixin, PickpocketMixin, InteractableMixin):
    """Bazowy NPC z dialogiem, handlem i próbą kradzieży."""

    meta: Optional[GameObjectMeta] = None  # do ustawiania w klasach pochodnych

    def __init__(
        self,
        *,
        name: str = "NPC",
        dialog: Optional[dict | str] = None,
        dialog_path: Optional[str] = None,
        allow_same_cell_interact: bool = True,
        require_same_cell_interact: bool = False,
        blocks_movement: bool = True,
        attitude: int = 0,
        inventory: Optional[list[TradeItem]] = None,
        base_price_modifier: float = 1.0,
        pickpocket_dc: int = 16,
        pickpocket_loot: Optional[list[str]] = None,
        enable_diplomacy: bool = True,
        is_noble: bool = False,
        enable_talk: bool = True,
        enable_trade: bool = True,
        enable_pickpocket: bool = True,
        on_pickpocket_fail: Optional[Callable[[object, object], Optional[str]]] = None,
        on_trade: Optional[Callable[[object, object], Optional[str]]] = None,
        trade_tier: str = "novice",
        spell_service_traditions: Optional[list[str]] = None,
        spell_service_max_rank: int = 1,
        spell_service_allow_cantrips: bool = True,
        spell_service_catalog: Optional[list[str]] = None,
        spell_service_catalog_by_tier: Optional[dict[str, list[str]]] = None,
    ):
        InteractableMixin.__init__(
            self,
            position=None,
            blocks_movement=blocks_movement,
            allow_same_cell_interact=allow_same_cell_interact,
            require_same_cell_interact=require_same_cell_interact,
        )

        self.attitude = attitude
        raw_inventory = inventory or []
        self.inventory = [
            item if isinstance(item, TradeItem) else TradeItem(**item) for item in raw_inventory
        ]
        self.base_price_modifier = base_price_modifier
        self.pickpocket_dc = pickpocket_dc
        self.pickpocket_loot = pickpocket_loot or ["kilka monet"]
        self._dialog_used: set[str] = set()
        self.enable_diplomacy = enable_diplomacy
        self.is_noble = is_noble
        self.enable_talk = enable_talk
        self.enable_trade = enable_trade
        self.enable_pickpocket = enable_pickpocket
        self._on_pickpocket_fail = on_pickpocket_fail
        self._on_trade = on_trade
        self.trade_tier = self._normalize_tier(trade_tier)
        self.spell_service_traditions = [
            str(item).strip().lower().replace("-", "_").replace(" ", "_")
            for item in list(spell_service_traditions or [])
            if str(item).strip()
        ]
        try:
            self.spell_service_max_rank = max(0, int(spell_service_max_rank or 0))
        except Exception:
            self.spell_service_max_rank = 1
        self.spell_service_allow_cantrips = bool(spell_service_allow_cantrips)
        self.spell_service_catalog = [
            str(item).strip().lower().replace("-", "_").replace(" ", "_")
            for item in list(spell_service_catalog or [])
            if str(item).strip()
        ]
        parsed_catalog_by_tier: dict[str, list[str]] = {}
        if isinstance(spell_service_catalog_by_tier, dict):
            for raw_tier, values in spell_service_catalog_by_tier.items():
                tier_id = self._normalize_tier(raw_tier)
                if not isinstance(values, (list, tuple, set)):
                    continue
                parsed_catalog_by_tier[tier_id] = [
                    str(item).strip().lower().replace("-", "_").replace(" ", "_")
                    for item in list(values)
                    if str(item).strip()
                ]
        self.spell_service_catalog_by_tier = parsed_catalog_by_tier

        self.name = name
        self.dialog = self._load_dialog(dialog, dialog_path) or self._default_dialog()
        self.register_default_actions()

    def _load_dialog(self, dialog: Optional[dict | str], dialog_path: Optional[str]) -> Optional[dict]:
        """Normalizuj dialog, próbując wczytać z pliku jeśli podano dialog_path."""
        normalized = self._normalize_dialog(dialog)
        if normalized:
            return normalized
        if dialog_path:
            loaded = self._load_dialog_from_path(dialog_path)
            if loaded:
                return loaded
        # fallback: bazowy plik domyślny, jeśli istnieje
        fallback = self._load_dialog_from_path("default_npc_dialog.json")
        return fallback

    def _load_dialog_from_path(self, dialog_path: str) -> Optional[dict]:
        path = Path(dialog_path)
        if not path.is_absolute():
            path = DIALOGS_DIR / path
        try:
            if not path.exists():
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception as exc:
            logger.warning("Nie udało się wczytać dialogu z %s: %s", path, exc)
        return None

    # --- Dialog ---
    def _normalize_dialog(self, dialog: Optional[dict | str]) -> Optional[dict]:
        if dialog is None:
            return None
        if isinstance(dialog, dict):
            return dialog
        if isinstance(dialog, str):
            return {"start": {"text": dialog, "options": []}}
        return None

    def _default_dialog(self) -> dict:
        """Minimalny dialog, podmieniany w klasach pochodnych."""
        return {"start": {"text": f"{self.name} nie ma nic do powiedzenia.", "options": []}}

    def _run_dialog(self) -> str:
        """Przykładowa implementacja – klasy potomne mogą ją rozszerzyć."""
        node = self.dialog.get("start", {})
        return node.get("text", "...")

    def action_talk(self, _actor, _game, _payload=None) -> str:
        return self._run_dialog()

    # --- Handel ---
    @staticmethod
    def _normalize_trade_kind(raw_kind: object) -> str:
        return str(raw_kind or "auto").strip().lower()

    @staticmethod
    def _normalize_tier(raw_tier: object) -> str:
        tier = str(raw_tier or "").strip().lower().replace("-", "_").replace(" ", "_")
        if tier in _MERCHANT_TIER_ORDER:
            return tier
        return "novice"

    @staticmethod
    def _tier_index(raw_tier: object) -> int:
        tier = BaseNPC._normalize_tier(raw_tier)
        try:
            return _MERCHANT_TIER_ORDER.index(tier)
        except ValueError:
            return 0

    def _trade_tier_label(self) -> str:
        labels = {"novice": "Nowicjusz", "adept": "Adept", "master": "Mistrz"}
        return labels.get(self.trade_tier, self.trade_tier.title())

    def _is_trade_item_available_for_tier(self, trade_item: TradeItem) -> bool:
        required = self._normalize_tier(getattr(trade_item, "min_tier", "novice"))
        return self._tier_index(self.trade_tier) >= self._tier_index(required)

    @staticmethod
    def _normalize_item_id(raw_item_id: object) -> str:
        return str(raw_item_id or "").strip().lower().replace(" ", "_").replace("-", "_")

    def _trade_price_cp(self, trade_item: TradeItem) -> int:
        base = max(0, int(getattr(trade_item, "price", 0) or 0))
        mult = float(self.price_multiplier(self.attitude))
        return max(0, int(math.ceil(float(base) * float(mult))))

    def _trade_item_to_game_item(self, trade_item: TradeItem):
        item_id = self._normalize_item_id(getattr(trade_item, "item_id", ""))
        kind = self._normalize_trade_kind(getattr(trade_item, "kind", "auto"))
        if not item_id:
            return None

        if kind in {"auto", "weapon"}:
            item = create_weapon(item_id)
            if item is not None:
                return item
        if kind in {"auto", "armor"}:
            item = create_armor(item_id)
            if item is not None:
                return item
        if kind in {"auto", "shield"}:
            item = create_shield(item_id)
            if item is not None:
                return item
        if kind in {"auto", "equipment", "gear", "ammo", "potion", "magic"}:
            item = create_equipment(item_id)
            if item is not None:
                return item
        if kind in {"auto", "service"}:
            service = create_service(item_id)
            if service is not None:
                return service

        if kind in {"auto", "alchemical"}:
            event_name = item_id
            if event_name.startswith("alchemical:"):
                event_name = event_name.split(":", 1)[1].strip()
            if event_name:
                normalized_event = normalize_alchemical_event_id(event_name)
                defaults = alchemical_item_defaults(normalized_event)
                return AlchemicalItem(
                    item_id=f"alchemical:{normalized_event}",
                    name=alchemical_item_name_from_event(normalized_event),
                    event_name=normalized_event,
                    description=str(getattr(trade_item, "description", "") or "Przedmiot alchemiczny."),
                    bulk=defaults.get("bulk", "L"),
                    price_cp=max(0, int(defaults.get("price_cp", getattr(trade_item, "price", 0)) or 0)),
                )
        return None

    def _spell_service_profile(self) -> tuple[set[str], int, bool, set[str] | None]:
        explicit_traditions = {
            str(item).strip().lower().replace("-", "_").replace(" ", "_")
            for item in list(getattr(self, "spell_service_traditions", []) or [])
            if str(item).strip()
        }
        object_id = str(getattr(getattr(self, "meta", None), "object_id", "") or "").strip().lower()
        if explicit_traditions:
            traditions = explicit_traditions
        elif "mage" in object_id:
            traditions = {"arcana", "primal"}
        elif "priest" in object_id:
            traditions = {"divine", "occult"}
        else:
            traditions = {"arcana", "primal", "divine", "occult"}

        tier_cap = int(_MERCHANT_TIER_SPELL_MAX_RANK.get(self.trade_tier, 1) or 1)
        try:
            configured_max_rank = int(getattr(self, "spell_service_max_rank", 0) or 0)
        except Exception:
            configured_max_rank = 0
        if configured_max_rank > 0:
            max_rank = max(0, min(configured_max_rank, tier_cap))
        else:
            max_rank = max(0, int(tier_cap))
        allow_cantrips = bool(getattr(self, "spell_service_allow_cantrips", True))
        raw_catalog = list(getattr(self, "spell_service_catalog", []) or [])
        catalog_values: set[str] = set()
        if raw_catalog:
            catalog_values.update(
                str(item).strip().lower().replace("-", "_").replace(" ", "_")
                for item in raw_catalog
                if str(item).strip()
            )
        raw_catalog_by_tier = dict(getattr(self, "spell_service_catalog_by_tier", {}) or {})
        if raw_catalog_by_tier:
            current_idx = self._tier_index(self.trade_tier)
            for tier_id, values in raw_catalog_by_tier.items():
                if self._tier_index(tier_id) > current_idx:
                    continue
                if not isinstance(values, (list, tuple, set)):
                    continue
                catalog_values.update(
                    str(item).strip().lower().replace("-", "_").replace(" ", "_")
                    for item in values
                    if str(item).strip()
                )
        catalog: set[str] | None = catalog_values or None
        return traditions, max_rank, allow_cantrips, catalog

    def _record_service_purchase(self, actor, *, service_obj, price_cp: int, extra: dict[str, object] | None = None) -> None:
        history = list(getattr(actor, "service_history", []) or [])
        row = {
            "service_id": str(getattr(service_obj, "item_id", "") or "").strip().lower(),
            "service_name": str(getattr(service_obj, "name", "") or "").strip(),
            "price_cp": max(0, int(price_cp or 0)),
        }
        if isinstance(extra, dict):
            for key, value in extra.items():
                row[str(key)] = value
        history.append(row)
        try:
            setattr(actor, "service_history", history)
        except Exception:
            pass

    def _parse_trade_choice(self, answer: object, *, choices: list[dict[str, object]]) -> str | None:
        if answer is None:
            return None
        if isinstance(answer, dict):
            for key in ("selected", "value", "id", "choice", "answer"):
                value = answer.get(key) if isinstance(answer, dict) else None
                if value is None:
                    continue
                parsed = self._parse_trade_choice(value, choices=choices)
                if parsed:
                    return parsed
            return None
        raw = str(answer).strip()
        if not raw:
            return None
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return str(choices[idx]["id"])
        lowered = raw.lower()
        for row in choices:
            if lowered == str(row["id"]).lower():
                return str(row["id"])
            if lowered == str(row.get("label", "")).lower():
                return str(row["id"])
            if lowered == str(row.get("raw", "")).lower():
                return str(row["id"])
        if ":" in lowered:
            prefix = lowered.split(":", 1)[0].strip()
            if prefix.isdigit():
                idx = int(prefix) - 1
                if 0 <= idx < len(choices):
                    return str(choices[idx]["id"])
        return None

    def _trade_loop_ui(self, actor, game) -> str:
        ui = getattr(game, "ui", None)
        if ui is None or not getattr(ui, "enabled", False) or not hasattr(ui, "prompt_choice"):
            return self._trade_offer_text()

        purchases: list[str] = []
        while True:
            options: list[dict[str, object]] = []
            for idx, trade_item in enumerate(list(self.inventory or []), start=1):
                if not self._is_trade_item_available_for_tier(trade_item):
                    continue
                stock = int(getattr(trade_item, "stock", -1) or -1)
                if stock == 0:
                    continue
                item_obj = self._trade_item_to_game_item(trade_item)
                if item_obj is None:
                    continue
                price_cp = self._trade_price_cp(trade_item)
                stock_txt = "bez limitu" if stock < 0 else str(stock)
                desc_lines = [
                    f"Cena: {format_cp_value(price_cp)}",
                    f"Stan: {stock_txt}",
                    item_description(item_obj),
                ]
                extra_desc = str(getattr(trade_item, "description", "") or "").strip()
                if extra_desc:
                    desc_lines.insert(0, extra_desc)
                options.append(
                    {
                        "id": f"trade:{idx - 1}",
                        "raw": str(idx),
                        "label": item_label(item_obj),
                        "desc": "\n".join(line for line in desc_lines if line),
                        "trade_index": idx - 1,
                        "price_cp": price_cp,
                    }
                )

            options.append(
                {
                    "id": "__exit_trade__",
                    "raw": "0",
                    "label": "Zakoncz handel",
                    "desc": "Wroc do menu interakcji.",
                }
            )

            answer = ui.prompt_choice(
                "Handel",
                choices=[str(row["label"]) for row in options],
                source="interaction",
                layout="dialog",
                title=f"Handel: {self.name}",
                subtitle=(
                    f"Tier: {self._trade_tier_label()}\n"
                    f"Monety: {format_actor_money(actor)}"
                ),
                prompt_long="Wybierz towar i potwierdz Enter.",
                choice_meta=[
                    {
                        "raw": str(row.get("raw", row["id"])),
                        "label": str(row["label"]),
                        "desc": str(row.get("desc", "")),
                        "key": str(pos + 1),
                    }
                    for pos, row in enumerate(options)
                ],
            )
            choice_id = self._parse_trade_choice(answer, choices=options)
            if not choice_id or choice_id == "__exit_trade__":
                break

            selected = next((row for row in options if str(row["id"]) == choice_id), None)
            if selected is None:
                continue
            try:
                trade_index = int(selected.get("trade_index", -1))
            except Exception:
                trade_index = -1
            if trade_index < 0 or trade_index >= len(self.inventory):
                continue
            trade_item = self.inventory[trade_index]
            current_stock = int(getattr(trade_item, "stock", -1) or -1)
            if current_stock == 0:
                continue
            price_cp = int(selected.get("price_cp", 0) or 0)
            if not can_actor_afford_cp(actor, price_cp):
                try:
                    if hasattr(ui, "prompt_info"):
                        ui.prompt_info(
                            "Brak srodkow",
                            prompt_long=(
                                f"Potrzeba: {format_cp_value(price_cp)}\n"
                                f"Masz: {format_actor_money(actor)}"
                            ),
                            source="interaction",
                        )
                except Exception:
                    pass
                continue
            item_obj = self._trade_item_to_game_item(trade_item)
            if item_obj is None:
                continue
            category = str(getattr(item_obj, "category", "") or "").strip().lower()

            selected_spell = None
            if category == "service":
                service_id = str(getattr(item_obj, "item_id", "") or "").strip().lower()
                service_rank = parse_service_rank(service_id)
                if service_rank is not None:
                    active_spells = merchant_spell_count(actor)
                    spell_limit = merchant_spell_capacity(actor)
                    if active_spells >= spell_limit:
                        try:
                            if hasattr(ui, "prompt_info"):
                                ui.prompt_info(
                                    "Limit czarow uslugowych",
                                    prompt_long=(
                                        "Nie mozesz kupic kolejnego czaru uslugowego.\n"
                                        f"Aktywne: {active_spells}/{spell_limit} "
                                        "(limit = modyfikator INT, minimum 1)."
                                    ),
                                    source="interaction",
                                )
                        except Exception:
                            pass
                        continue

                    traditions, max_rank, allow_cantrips, catalog = self._spell_service_profile()
                    selected_spell = choose_spell_for_service(
                        game=game,
                        actor=actor,
                        provider_name=str(getattr(self, "name", "") or "Kupiec"),
                        service_id=service_id,
                        traditions=traditions,
                        max_rank=max_rank,
                        allow_cantrips=allow_cantrips,
                        catalog=catalog,
                    )
                    if selected_spell is None:
                        try:
                            if hasattr(ui, "prompt_info"):
                                ui.prompt_info(
                                    "Brak dostepnych czarow",
                                    prompt_long=(
                                        "Ten handlarz nie ma teraz czarow pasujacych do tej uslugi.\n"
                                        "Sprawdz tradycje, range uslugi lub konfiguracje katalogu."
                                    ),
                                    source="interaction",
                                )
                        except Exception:
                            pass
                        continue
            if not spend_actor_cp(actor, price_cp):
                continue
            if category == "service":
                if selected_spell is not None:
                    granted, grant_msg = add_service_spell_to_actor(
                        actor=actor,
                        spell_id=str(getattr(selected_spell, "spell_id", "") or ""),
                        tier=str(getattr(selected_spell, "tier", "") or ""),
                        provider_name=str(getattr(self, "name", "") or ""),
                        game=game,
                    )
                    if not granted:
                        add_actor_cp(actor, price_cp)
                        try:
                            if hasattr(ui, "prompt_info"):
                                ui.prompt_info(
                                    "Zakup anulowany",
                                    prompt_long=str(grant_msg or "Nie udalo sie dodac czaru uslugowego."),
                                    source="interaction",
                                )
                        except Exception:
                            pass
                        continue
                    self._record_service_purchase(
                        actor,
                        service_obj=item_obj,
                        price_cp=price_cp,
                        extra={
                            "spell_id": str(getattr(selected_spell, "spell_id", "") or ""),
                            "spell_tier": str(getattr(selected_spell, "tier", "") or ""),
                        },
                    )
                    effect_notes = [str(grant_msg or "").strip()]
                else:
                    self._record_service_purchase(actor, service_obj=item_obj, price_cp=price_cp)
                    effect_notes = apply_service_effect(
                        str(getattr(item_obj, "item_id", "") or ""),
                        actor=actor,
                        game=game,
                        provider_name=str(getattr(self, "name", "") or ""),
                    )
            else:
                add_item(actor, item_obj)
                effect_notes = []
            if current_stock > 0:
                trade_item.stock = max(0, current_stock - 1)
            purchase_label = item_label(item_obj)
            if category == "service":
                purchase_label = f"{purchase_label} [usluga]"
            purchases.append(f"{purchase_label} ({format_cp_value(price_cp)})")
            try:
                if hasattr(ui, "prompt_info"):
                    service_note = ""
                    if category == "service":
                        extra = "\n".join(str(line).strip() for line in list(effect_notes or []) if str(line).strip())
                        service_note = "\nTyp: usluga natychmiastowa (nie trafia do ekwipunku)."
                        if extra:
                            service_note += f"\nEfekt:\n{extra}"
                    ui.prompt_info(
                        "Zakup udany",
                        prompt_long=(
                            f"Kupiono: {item_label(item_obj)}\n"
                            f"Zaplacono: {format_cp_value(price_cp)}\n"
                            f"Pozostalo: {format_actor_money(actor)}"
                            f"{service_note}"
                        ),
                        source="interaction",
                    )
            except Exception:
                pass

        if not purchases:
            return f"Koniec handlu. Monety: {format_actor_money(actor)}."
        return (
            "Zakupy zakonczone.\n"
            f"Kupiono: {', '.join(purchases)}\n"
            f"Monety po zakupach: {format_actor_money(actor)}"
        )

    def _trade_offer_text(self) -> str:
        if not self.inventory:
            return "Nie mam nic na sprzedaż."
        mult = self.price_multiplier(self.attitude)
        lines = [f"Oferta ({attitude_label(self.attitude)}, mnożnik {mult:.2f}, tier: {self._trade_tier_label()}):"]
        for row in self.inventory:
            if not self._is_trade_item_available_for_tier(row):
                continue
            price_cp = self._trade_price_cp(row)
            stock = int(getattr(row, "stock", -1) or -1)
            stock_txt = "bez limitu" if stock < 0 else str(stock)
            lines.append(f"- {row.name}: {format_cp_value(price_cp)} (stan: {stock_txt})")
        return "\n".join(lines)

    def action_trade(self, _actor, _game, _payload=None) -> str:
        if _game is not None and _actor is not None:
            msg = self._trade_loop_ui(_actor, _game)
        else:
            msg = self._trade_offer_text()
        if callable(self._on_trade):
            extra = self._on_trade(self, _actor)
            if extra:
                msg = f"{msg}\n{extra}"
        return msg

    # --- Kradzież ---
    def action_pickpocket(self, actor, _game, _payload=None) -> str:
        has_status = getattr(actor, "has_status", None)
        is_stealthed = has_status(Skill.STEALTH.value) if callable(has_status) else Skill.STEALTH.value in getattr(actor, "statuses", [])
        if not is_stealthed:
            return "Musisz być w ukryciu, aby spróbować podkraść."
        outcome = None
        if _game is None:
            roll = prompt_for_roll("Pickpocket: podaj wynik rzutu (d20 + modyfikatory): ")
            outcome = resolve_skill_check(self.pickpocket_dc, roll)
        else:
            result = dispatch_event(
                "skill_check",
                EventContext(
                    game=_game,
                    actor=actor,
                    tags=[Skill.THIEVERY.value, "pickpocket"],
                    metadata={
                        "dc": self.pickpocket_dc,
                        "skill_id": Skill.THIEVERY.value,
                        "skill_label": "Thievery",
                        "apply_modifiers": True,
                    },
                ),
            )
            outcome = result.data.get("outcome") if result.data else resolve_skill_check(self.pickpocket_dc, 0)
        if outcome in ("success", "critical_success"):
            loot = (self.pickpocket_loot or ["drobne"])[0]
            return f"Udało się podkraść: {loot} (wynik: {outcome})."
        # porażka obniża nastawienie
        new_att, label = self.adjust_attitude(self.pickpocket_fail_attitude_delta)
        msg = (
            f"Przyłapany! Nastawienie spada do: {label} ({new_att}). "
            f"Wynik testu: {outcome}."
        )
        if callable(self._on_pickpocket_fail):
            extra = self._on_pickpocket_fail(self, actor)
            if extra:
                msg = f"{msg} {extra}"
        return msg

    # --- Diplomacy check (tagowy SkillCheckEvent) ---
    def _diplomacy_dc(self) -> int:
        """DC zależne od nastawienia (-2..2): wrogi trudniej, przyjacielski łatwiej."""
        base_dc = 15
        # niższe DC dla pozytywnego nastawienia, wyższe dla negatywnego
        return base_dc - 2 * self.attitude

    def action_diplomacy(self, actor, game, _payload=None) -> str:
        dc = self._diplomacy_dc()
        tags = [Skill.DIPLOMACY.value, "convince"]
        if self.is_noble:
            tags.append("noble")

        ctx = EventContext(
            game=game,
            actor=actor,
            tags=tags,
            metadata={"dc": dc, "skill_id": Skill.DIPLOMACY.value, "skill_label": "Diplomacy"},
        )
        result = dispatch_event("skill_check", ctx)

        outcome = result.data.get("outcome") if result.data else None
        if outcome in ("success", "critical_success"):
            delta = 2 if outcome == "critical_success" else 1
            new_att, label = self.adjust_attitude(delta)
            return (
                f"Udana perswazja ({outcome}). Nastawienie rośnie do: {label} ({new_att}). "
                f"{result.message or ''}"
            ).strip()

        if outcome in ("failure", "critical_failure"):
            delta = -2 if outcome == "critical_failure" else -1
            new_att, label = self.adjust_attitude(delta)
            return (
                f"Nie udało się przekonać ({outcome}). Nastawienie spada do: {label} ({new_att}). "
                f"{result.message or ''}"
            ).strip()

        return result.message or "Test dyplomacji nie został przeprowadzony."

    def register_default_actions(self) -> None:
        """Tworzy standardowe akcje (dialog, handel, kradzież, wyjście) wg flag."""
        if self.enable_talk:
            self.register_action(
                Interaction(
                    id="talk",
                    label="Porozmawiaj",
                    description="Rozmowa.",
                    handler=type(self).action_talk,
                    end_interaction=False,
                )
            )
        if self.enable_diplomacy:
            self.register_action(
                Interaction(
                    id="diplomacy",
                    label="Przekonaj (Diplomacy)",
                    description="Próba perswazji zależna od nastawienia.",
                    handler=type(self).action_diplomacy,
                    end_interaction=False,
                    tags=["diplomacy", "convince"],
                )
            )
        if self.enable_trade:
            self.register_action(
                Interaction(
                    id="trade",
                    label="Handluj",
                    description="Zobacz, co oferuje.",
                    handler=type(self).action_trade,
                    end_interaction=False,
                )
            )
        if self.enable_pickpocket:
            self.register_action(
                Interaction(
                    id="pickpocket",
                    label="Podkradnij",
                    description="Próba kradzieży (Thievery).",
                    handler=type(self).action_pickpocket,
                    end_interaction=False,
                )
            )
        self.register_action(
            Interaction(
                id="leave",
                label="Zakończ",
                description="Zakończ rozmowę.",
                handler=lambda _self, _actor, _game, _payload=None: "Kończysz rozmowę.",
            )
        )
        for extra in self.extra_actions():
            self.register_action(extra)

    def extra_actions(self) -> Iterable[Interaction]:
        """Hook na dodatkowe akcje w klasach potomnych."""
        return []

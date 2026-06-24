from __future__ import annotations

from dataclasses import dataclass

from GameObjects.interactions_mixin import prompt_for_roll
from spell_management import (
    can_cast_managed_spell,
    classify_spell_tier,
    consume_managed_spell_resources,
    ensure_actor_spell_state,
)

from .base import Reaction


def _has_status(actor, status_id: str) -> bool:
    if actor is None:
        return False
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


def _spell_name_from_event(event: dict[str, object]) -> str:
    explicit = str(event.get("spell_name", "") or "").strip()
    if explicit:
        return explicit
    action_id = str(event.get("action_id", "") or "").strip()
    if action_id.endswith("_pre"):
        action_id = action_id[:-4]
    return action_id or "unknown_spell"


def _prompt_choice(game, prompt: str, choices: list[str], *, source: str) -> str | None:
    ui = getattr(game, "ui", None)
    chooser = getattr(ui, "prompt_choice", None)
    if callable(chooser):
        try:
            value = chooser(prompt, choices=choices, source=source)
            if value is not None:
                raw = str(value).strip()
                if raw:
                    return raw
        except Exception:
            pass
    if ui is not None and not getattr(ui, "allow_cli_fallback", False):
        return None
    try:
        raw = input(f"{prompt} {choices}: ").strip()
    except Exception:
        return None
    return raw or None


def _is_yes(value: str | None) -> bool:
    raw = str(value or "").strip().lower()
    return raw in {"t", "tak", "y", "yes", "1"}


def _normalize_spell_id(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _focus_points(actor) -> int:
    try:
        return max(0, int(getattr(actor, "focus_point", 0) or 0))
    except Exception:
        return 0


def _set_focus_points(actor, value: int) -> None:
    try:
        setattr(actor, "focus_point", max(0, int(value)))
    except Exception:
        pass


def _spell_tier_from_event(event: dict[str, object]) -> str | None:
    tags = list(event.get("spell_tags") or [])
    if not tags:
        tags = list(event.get("action_tags") or [])
    raw = classify_spell_tier(tags)
    normalized = str(raw or "").strip().lower()
    return normalized or None


def _counterspell_ready(actor, event: dict[str, object], game) -> tuple[bool, str | None, str, str | None]:
    spell_name = _spell_name_from_event(event)
    spell_id = _normalize_spell_id(spell_name)
    spell_tier = _spell_tier_from_event(event)
    if not spell_id:
        return False, "Counterspell: nie udalo sie rozpoznac czaru przeciwnika.", "", spell_tier
    if not spell_tier:
        return (
            False,
            f"Counterspell: brak danych o randze/typie czaru {spell_name}.",
            spell_id,
            None,
        )

    state = ensure_actor_spell_state(actor, game=game, enforce=True)
    if spell_tier == "focus":
        known_focus = {
            _normalize_spell_id(item)
            for item in list((state.get("known", {}) or {}).get("focus", []) or [])
            if _normalize_spell_id(item)
        }
        if spell_id not in known_focus:
            return (
                False,
                f"Counterspell: {spell_name} nie jest znanym focus spellem tej postaci.",
                spell_id,
                spell_tier,
            )
        if _focus_points(actor) <= 0:
            return False, "Counterspell: brak Focus Point na skontrowanie focus spella.", spell_id, spell_tier
        return True, None, spell_id, spell_tier

    can_cast, reason = can_cast_managed_spell(actor, spell_id=spell_id, tier=spell_tier)
    if not can_cast:
        return False, f"Counterspell: {reason or 'brak dostepu do tego samego czaru.'}", spell_id, spell_tier
    return True, None, spell_id, spell_tier


def _spend_counterspell_resource(actor, *, spell_id: str, spell_tier: str | None) -> None:
    if spell_tier == "focus":
        _set_focus_points(actor, _focus_points(actor) - 1)
        return
    consume_managed_spell_resources(actor, spell_id=spell_id, tier=spell_tier)


@dataclass
class CounterspellReaction(Reaction):
    id: str = "counterspell_reaction"
    label: str = "Counterspell"
    priority: int = 80
    action_cost: int = 1
    requires_reach: bool = False
    blocks_range_attacker: bool = False

    def triggers(self, actor, event: dict[str, object]) -> bool:
        if actor is None:
            return False
        if not _has_status(actor, "counterspell"):
            return False
        action_id = str(event.get("action_id", "") or "")
        if not action_id.endswith("_pre"):
            return False
        tags = {str(tag or "").strip().lower() for tag in (event.get("action_tags") or [])}
        return "magic" in tags and "spell" in tags

    def reason(self, actor, event: dict[str, object]) -> str:
        _ = actor
        spell_name = _spell_name_from_event(event)
        return f"przeciwnik rzuca czar {spell_name}"

    def prompt_text(self, actor, event: dict[str, object]) -> str:
        _ = actor
        spell_name = _spell_name_from_event(event)
        return (
            "Counterspell: czy chcesz uzyc reakcji dla czaru "
            f"{spell_name}? (wymagany ten sam czar i odpowiedni zasob czarowania)"
        )

    def execute(self, actor, event: dict[str, object], ctx) -> bool:
        spell_name = _spell_name_from_event(event)
        game = ctx.game
        ready, reason, spell_id, spell_tier = _counterspell_ready(actor, event, game)
        if not ready:
            try:
                game.ui_log(str(reason or "Counterspell: brak odpowiedniego czaru."))
            except Exception:
                pass
            return False

        confirm = _prompt_choice(
            game,
            f"Counterspell: zuzyc odpowiedni zasob, aby skontrowac czar {spell_name}?",
            choices=["tak", "nie"],
            source="counterspell",
        )
        if not _is_yes(confirm):
            return False

        _spend_counterspell_resource(actor, spell_id=spell_id, spell_tier=spell_tier)

        counteract_total = int(
            prompt_for_roll(
                "Counterspell: podaj wynik counteract check (d20 + spellcasting modifier):",
                layout="test",
                answer_placeholder="Counteract check",
            )
            or 0
        )
        spell_dc = int(
            prompt_for_roll(
                "Counterspell: podaj DC czaru przeciwnika:",
                layout="test",
                answer_placeholder="Spell DC",
            )
            or 0
        )

        delta = int(counteract_total) - int(spell_dc)
        if delta >= 10:
            outcome = "critical_success"
        elif delta >= 0:
            outcome = "success"
        elif delta <= -10:
            outcome = "critical_failure"
        else:
            outcome = "failure"

        disrupted = outcome in {"success", "critical_success"}
        if disrupted:
            event["disrupted"] = True
            event["disruption_reason"] = "counterspell"
        event["counterspell_outcome"] = outcome
        event["counterspell_spell_name"] = spell_name
        if spell_tier:
            event["counterspell_spell_tier"] = spell_tier

        try:
            if disrupted:
                game.ui_log(f"Counterspell: {spell_name} zostaje anulowany ({outcome}).")
            else:
                game.ui_log(
                    f"Counterspell: nie udalo sie anulowac {spell_name} ({outcome}); "
                    "zasob zostaje zuzyty."
                )
        except Exception:
            pass
        return True

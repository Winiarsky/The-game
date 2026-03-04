from __future__ import annotations

from dataclasses import dataclass

from GameObjects.interactions_mixin import prompt_for_roll

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
            f"{spell_name}? (wymagany ten sam czar i zuzycie slotu)"
        )

    def execute(self, actor, event: dict[str, object], ctx) -> bool:
        spell_name = _spell_name_from_event(event)
        game = ctx.game
        confirm = _prompt_choice(
            game,
            (
                "Counterspell: potwierdz, ze masz DOKLADNIE ten sam czar "
                f"({spell_name}) i zuzywasz odpowiedni slot."
            ),
            choices=["tak", "nie"],
            source="counterspell",
        )
        if not _is_yes(confirm):
            return False

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

        try:
            if disrupted:
                game.ui_log(f"Counterspell: {spell_name} zostaje anulowany ({outcome}).")
            else:
                game.ui_log(
                    f"Counterspell: nie udalo sie anulowac {spell_name} ({outcome}); "
                    "slot zostaje zuzyty."
                )
        except Exception:
            pass
        return True

from __future__ import annotations

from .base import EventContext, EventResult, GameEvent
from .registry import dispatch_event, register_event


def _normalize(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _is_wizard(actor) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            if bool(checker("wizard")):
                return True
        except Exception:
            pass
    return _normalize(getattr(actor, "class_name", "")) == "wizard"


def _wizard_setup(actor) -> dict:
    if actor is None:
        return {}
    getter = getattr(actor, "get_status_data", None)
    if callable(getter):
        try:
            setup = getter("wizard", "wizard_setup", {})
            if isinstance(setup, dict):
                return dict(setup)
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) != "wizard":
            continue
        data = getattr(status, "data", None) or {}
        setup = data.get("wizard_setup")
        if isinstance(setup, dict):
            return dict(setup)
    return {}


def _wizard_arcane_study(actor) -> str | None:
    setup = _wizard_setup(actor)
    raw = setup.get("arcane_study")
    if raw is None:
        raw = getattr(actor, "wizard_arcane_study", None)
    normalized = _normalize(raw)
    return normalized or None


def _wizard_drain_action(actor) -> str:
    setup = _wizard_setup(actor)
    raw = setup.get("drain_action")
    if raw is None:
        raw = getattr(actor, "wizard_drain_action", None)
    normalized = _normalize(raw)
    return normalized or "drain_bonded_item"


def _wizard_cast_registry(actor) -> list[dict]:
    raw = getattr(actor, "wizard_cast_spells_registry", None)
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(dict(item))
    return out


def _wizard_drain_usage(actor) -> dict[str, int]:
    raw = getattr(actor, "wizard_drain_usage", None)
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for key, value in raw.items():
        try:
            out[str(key)] = int(value or 0)
        except Exception:
            continue
    return out


def _set_wizard_drain_usage(actor, usage: dict[str, int]) -> None:
    payload: dict[str, int] = {}
    for key, value in usage.items():
        try:
            payload[str(key)] = max(0, int(value or 0))
        except Exception:
            continue
    try:
        setattr(actor, "wizard_drain_usage", payload)
    except Exception:
        pass


def _entry_rank(entry: dict) -> int:
    try:
        return max(1, int(entry.get("rank", 1) or 1))
    except Exception:
        return 1


def _drain_bucket(actor, entry: dict) -> str:
    study = _wizard_arcane_study(actor)
    if study == "universalist":
        return f"rank:{_entry_rank(entry)}"
    return "all"


def _prompt_choice(ctx: EventContext, prompt: str, choices: list[str], *, source: str) -> str | None:
    ui = getattr(ctx.game, "ui", None)
    if ui is None:
        return None
    chooser = getattr(ui, "prompt_choice", None)
    if callable(chooser):
        try:
            answer = chooser(prompt, choices=choices, source=source)
            if answer is not None:
                raw = str(answer).strip()
                if raw:
                    return raw
        except Exception:
            pass
    if not getattr(ui, "allow_cli_fallback", False):
        return None
    try:
        raw = input(f"{prompt} {choices}: ").strip()
    except Exception:
        return None
    return raw or None


def _labelize_spell(spell_id: str, rank: int) -> str:
    base = str(spell_id or "").strip().replace("_", " ").title()
    return f"{base} (rank {max(1, int(rank or 1))})"


def _read_card(ctx: EventContext, prompt: str, acceptable: list[str]) -> str | None:
    conn = getattr(ctx.game, "conn", None)
    reader = getattr(conn, "read_card", None)
    if not callable(reader):
        return None
    try:
        return str(reader(prompt, acceptable_responses=acceptable) or "").strip().lower() or None
    except Exception:
        try:
            return str(reader(prompt, acceptable) or "").strip().lower() or None
        except Exception:
            return None


class _DrainWizardBondBase(GameEvent):
    consumes_action = False
    available_in_combat = True
    available_in_exploration = True
    expected_drain_action: str = "drain_bonded_item"

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message=f"{self.name}: missing actor.")
        if not _is_wizard(actor):
            return EventResult.cancelled(message=f"{self.name}: only Wizard can use this action.")

        configured = _wizard_drain_action(actor)
        if configured != self.expected_drain_action:
            return EventResult.cancelled(
                message=f"{self.name}: your current Arcane Bond uses action '{configured}'."
            )

        usage = _wizard_drain_usage(actor)
        registry = _wizard_cast_registry(actor)

        eligible: list[dict] = []
        seen_pairs: set[tuple[str, int]] = set()
        for entry in reversed(registry):
            spell_id = _normalize(entry.get("spell_id"))
            if not spell_id:
                continue
            if bool(entry.get("is_focus", False)) or bool(entry.get("is_cantrip", False)):
                continue
            rank = _entry_rank(entry)
            key = (spell_id, rank)
            if key in seen_pairs:
                continue
            bucket = _drain_bucket(actor, entry)
            if int(usage.get(bucket, 0) or 0) >= 1:
                continue
            seen_pairs.add(key)
            eligible.append({"spell_id": spell_id, "rank": rank, "bucket": bucket})

        if not eligible:
            return EventResult.cancelled(
                message=f"{self.name}: no eligible already-cast non-focus non-cantrip wizard spells in registry."
            )

        label_to_entry: dict[str, dict] = {}
        labels: list[str] = []
        for entry in eligible:
            label = _labelize_spell(entry["spell_id"], entry["rank"])
            labels.append(label)
            label_to_entry[label] = entry
        labels.append("cancel")

        selected_label = _prompt_choice(
            ctx,
            "Drain Bonded Item/Familiar: choose a previously cast spell",
            labels,
            source=self.name,
        )
        if selected_label is None:
            return EventResult.cancelled(message=f"{self.name}: cancelled.")
        selected_raw = str(selected_label).strip()
        if _normalize(selected_raw) == "cancel":
            return EventResult.cancelled(message=f"{self.name}: cancelled.")
        selected = label_to_entry.get(selected_raw)
        if selected is None:
            return EventResult.cancelled(message=f"{self.name}: invalid selection.")

        spell_id = str(selected["spell_id"])
        scanned = _read_card(
            ctx,
            f"{self.name}: scan the selected spell card ({spell_id})",
            acceptable=[spell_id, "cancel"],
        )
        if scanned is None or _normalize(scanned) == "cancel":
            return EventResult.cancelled(message=f"{self.name}: cancelled before casting.")
        if _normalize(scanned) != spell_id:
            return EventResult.cancelled(message=f"{self.name}: scanned card does not match chosen spell.")

        cast_result = dispatch_event(
            spell_id,
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata=dict(ctx.metadata or {}),
            ),
        )
        if not cast_result.success:
            return cast_result

        usage[selected["bucket"]] = int(usage.get(selected["bucket"], 0) or 0) + 1
        _set_wizard_drain_usage(actor, usage)

        base = str(cast_result.message or f"{spell_id}: cast.")
        cast_result.message = f"{self.name}: {base}"
        return cast_result


@register_event
class DrainBondedItemEvent(_DrainWizardBondBase):
    name = "drain_bonded_item"
    expected_drain_action = "drain_bonded_item"


@register_event
class DrainFamiliarEvent(_DrainWizardBondBase):
    name = "drain_familiar"
    expected_drain_action = "drain_familiar"


@register_event
class RefocusEvent(GameEvent):
    name = "refocus"
    consumes_action = False
    available_in_combat = False
    available_in_exploration = True

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="refocus: missing actor.")
        if not _is_wizard(actor):
            return EventResult.cancelled(message="refocus: only Wizard refocus is implemented.")

        try:
            current = max(0, int(getattr(actor, "focus_point", 0) or 0))
        except Exception:
            current = 0

        max_pool = 1
        for attr_name in ("wizard_focus_pool_max", "focus_pool_max", "focus_pool_size"):
            try:
                raw = int(getattr(actor, attr_name, 0) or 0)
            except Exception:
                raw = 0
            if raw > max_pool:
                max_pool = raw
        max_pool = max(max_pool, current, 1)

        if current >= max_pool:
            return EventResult.cancelled(message=f"refocus: focus pool already full ({current}/{max_pool}).")

        new_value = min(max_pool, current + 1)
        try:
            setattr(actor, "focus_point", int(new_value))
        except Exception:
            return EventResult.cancelled(message="refocus: failed to update focus pool.")

        return EventResult(
            success=True,
            consumed_action=False,
            message=(
                f"Refocus (Wizard): study your spellbook/research for 10 minutes. "
                f"Focus Point {current} -> {new_value}/{max_pool}."
            ),
        )


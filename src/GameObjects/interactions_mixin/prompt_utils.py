from __future__ import annotations

import logging

from ui_client import get_ui_client
from combat.degree_of_success import (
    clamp_natural_shift,
    natural_mode_from_shift,
    natural_shift_from_mode,
    natural_shift_from_roll,
)

logger = logging.getLogger(__name__)

_MAGIC_PROMPT_CONTEXT: dict | None = None


def get_magic_prompt_context() -> dict | None:
    return _MAGIC_PROMPT_CONTEXT


def set_magic_prompt_context(payload: dict | None) -> None:
    global _MAGIC_PROMPT_CONTEXT
    _MAGIC_PROMPT_CONTEXT = payload if isinstance(payload, dict) else None


def _parse_roll_details(answer, *, infer_natural_from_roll: bool = False) -> dict[str, object]:
    roll = 0
    raw_roll = 0
    shift = 0
    modifier_delta = 0
    computed_total = None

    if isinstance(answer, dict):
        roll_val = answer.get("roll", answer.get("value", answer.get("result", 0)))
        raw_roll_val = answer.get("raw_roll", roll_val)
        try:
            roll = int(roll_val or 0)
        except Exception:
            roll = 0
        try:
            raw_roll = int(raw_roll_val or 0)
        except Exception:
            raw_roll = roll
        mode = answer.get("natural_mode", answer.get("natural", answer.get("nat", None)))
        shift = natural_shift_from_mode(mode)
        if shift == 0:
            shift = clamp_natural_shift(answer.get("natural_shift"))
        if shift == 0 and infer_natural_from_roll:
            shift = natural_shift_from_roll(raw_roll)
        try:
            modifier_delta = int(answer.get("modifier_delta", 0) or 0)
        except Exception:
            modifier_delta = 0
        if "computed_total" in answer:
            try:
                computed_total = int(answer.get("computed_total", 0) or 0)
            except Exception:
                computed_total = None
    else:
        try:
            roll = int(answer or 0)
        except Exception:
            roll = 0
        raw_roll = roll
        if infer_natural_from_roll:
            shift = natural_shift_from_roll(raw_roll)

    out = {
        "roll": int(roll),
        "raw_roll": int(raw_roll),
        "natural_shift": int(shift),
        "natural_mode": natural_mode_from_shift(shift),
        "modifier_delta": int(modifier_delta),
    }
    if computed_total is not None:
        out["computed_total"] = int(computed_total)
    return out


def _int_or_default(value, default: int = 0) -> int:
    try:
        return int(value or 0)
    except Exception:
        return int(default)


def _sum_modifier_bucket(modifiers: dict, key: str, *, is_penalty: bool = False) -> int:
    total = 0
    for row in list(modifiers.get(key, []) or []):
        value = _int_or_default(row.get("value", 0), 0) if isinstance(row, dict) else 0
        total += -abs(value) if is_penalty else abs(value)
    return int(total)


def _prepare_roll_stack_payload(
    *,
    roll_stack: dict | None,
    modifiers: dict | None,
    auto_total_modifier: int | None,
) -> dict | None:
    base_payload: dict = dict(roll_stack or {})
    raw_components = list(base_payload.get("components") or [])
    components: list[dict[str, object]] = []

    if raw_components:
        for idx, row in enumerate(raw_components):
            if not isinstance(row, dict):
                continue
            components.append(
                {
                    "id": str(row.get("id") or f"component_{idx + 1}"),
                    "label": str(row.get("label") or f"Składnik {idx + 1}"),
                    "value": _int_or_default(row.get("value", 0), 0),
                    "description": str(row.get("description") or row.get("desc") or ""),
                    "editable": bool(row.get("editable", True)),
                }
            )
    elif isinstance(modifiers, dict):
        circumstance_total = _sum_modifier_bucket(modifiers, "bonCirc") + _sum_modifier_bucket(
            modifiers, "penCirc", is_penalty=True
        )
        status_total = _sum_modifier_bucket(modifiers, "bonStat") + _sum_modifier_bucket(
            modifiers, "penStat", is_penalty=True
        )
        item_total = _sum_modifier_bucket(modifiers, "bonItem") + _sum_modifier_bucket(
            modifiers, "penItem", is_penalty=True
        )
        for cid, label, value, description in (
            ("circumstance", "Okoliczności", circumstance_total, "Premie i kary circumstance."),
            ("status", "Status", status_total, "Premie i kary status."),
            ("item", "Przedmiot", item_total, "Premie i kary item."),
        ):
            if int(value) == 0:
                continue
            components.append(
                {
                    "id": cid,
                    "label": label,
                    "value": int(value),
                    "description": description,
                    "editable": True,
                }
            )

    components_total = sum(_int_or_default(item.get("value", 0), 0) for item in components)
    auto_total = auto_total_modifier
    if auto_total is None and "auto_total_modifier" in base_payload:
        auto_total = _int_or_default(base_payload.get("auto_total_modifier", 0), 0)
    if auto_total is None:
        auto_total = int(components_total)

    if int(auto_total) != int(components_total):
        diff = int(auto_total) - int(components_total)
        components.append(
            {
                "id": "other_auto",
                "label": "Pozostałe",
                "value": int(diff),
                "description": "Pozostały automatyczny modyfikator.",
                "editable": True,
            }
        )

    if not components and int(auto_total) == 0:
        return None

    base_payload["components"] = components
    base_payload["auto_total_modifier"] = int(auto_total)
    return base_payload


def _default_damage_roll_stack_payload() -> dict[str, object]:
    components = [
        {
            "id": "ability",
            "label": "Cecha",
            "value": 0,
            "description": "Modyfikator cechy do obrażeń (jeśli dotyczy).",
            "editable": True,
        },
        {
            "id": "item",
            "label": "Przedmiot",
            "value": 0,
            "description": "Premie/kary z wyposażenia.",
            "editable": True,
        },
        {
            "id": "status",
            "label": "Status",
            "value": 0,
            "description": "Premie/kary status do obrażeń.",
            "editable": True,
        },
        {
            "id": "circumstance",
            "label": "Okoliczności",
            "value": 0,
            "description": "Premie/kary circumstance do obrażeń.",
            "editable": True,
        },
        {
            "id": "other",
            "label": "Inne",
            "value": 0,
            "description": "Pozostałe modyfikatory.",
            "editable": True,
        },
    ]
    return {
        "components": components,
        "auto_total_modifier": 0,
    }


def _has_status_id(actor, status_id: str) -> bool:
    if actor is None:
        return False
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            return bool(has_status(status_id))
        except Exception:
            return False
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", status) == status_id:
            return True
    return False


def _dangerous_sorcery_bonus_per_level(actor) -> int:
    if actor is None:
        return 1
    getter = getattr(actor, "get_status_data", None)
    if callable(getter):
        try:
            value = int(getter("dangerous_sorcery", "dangerous_sorcery_damage_bonus_per_spell_level", 1) or 1)
            return max(1, value)
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) != "dangerous_sorcery":
            continue
        data = getattr(status, "data", None) or {}
        try:
            value = int(data.get("dangerous_sorcery_damage_bonus_per_spell_level", 1) or 1)
            return max(1, value)
        except Exception:
            return 1
    return 1


def _prompt_choice(ui_client, prompt: str, choices: list[str], *, source: str) -> str | None:
    if getattr(ui_client, "enabled", False):
        try:
            answer = ui_client.prompt_choice(prompt, choices=choices, source=source)
            if answer is not None:
                raw = str(answer).strip()
                if raw:
                    return raw
        except Exception:
            pass
    if not getattr(ui_client, "allow_cli_fallback", False):
        return None
    try:
        raw = input(f"{prompt} {choices}: ").strip()
    except Exception:
        return None
    return raw or None


def _prompt_spell_level(ui_client, *, source: str) -> int | None:
    choices = [str(idx) for idx in range(1, 11)]
    selected = _prompt_choice(
        ui_client,
        "Dangerous Sorcery: podaj poziom czaru (slot spell level)",
        choices=choices,
        source=source,
    )
    if selected is not None:
        try:
            value = int(str(selected).strip())
            return max(1, value)
        except Exception:
            pass

    if getattr(ui_client, "enabled", False):
        try:
            answer = ui_client.prompt_roll(
                "Dangerous Sorcery: wpisz poziom czaru",
                source=source,
                layout="test",
                answer_placeholder="Poziom czaru",
            )
            details = _parse_roll_details(answer)
            value = int(details.get("roll", 0) or 0)
            if value > 0:
                return value
        except Exception:
            return None
    if not getattr(ui_client, "allow_cli_fallback", False):
        return None
    try:
        raw = input("Dangerous Sorcery - poziom czaru: ").strip()
        value = int(raw or 0)
    except Exception:
        return None
    return value if value > 0 else None


def _apply_dangerous_sorcery_if_needed(
    rolled_value: int,
    *,
    ui_client,
    layout: str,
) -> int:
    context = get_magic_prompt_context()
    if not isinstance(context, dict):
        return int(rolled_value)
    if str(layout or "").strip().lower() != "damage":
        return int(rolled_value)
    if bool(context.get("dangerous_sorcery_resolved", False)):
        return int(rolled_value)

    actor = context.get("actor")
    if not _has_status_id(actor, "dangerous_sorcery"):
        context["dangerous_sorcery_resolved"] = True
        return int(rolled_value)
    if bool(context.get("is_focus_spell", False)) or bool(context.get("is_cantrip_spell", False)):
        context["dangerous_sorcery_resolved"] = True
        return int(rolled_value)

    apply_answer = _prompt_choice(
        ui_client,
        (
            "Dangerous Sorcery: ten bonus dziala tylko dla czarow ze slotu, "
            "ktore zadaja obrazenia i nie maja duration. Zastosowac teraz?"
        ),
        choices=["tak", "nie"],
        source="dangerous_sorcery",
    )
    normalized = str(apply_answer or "").strip().lower()
    if normalized not in {"t", "tak", "y", "yes", "1"}:
        context["dangerous_sorcery_resolved"] = True
        return int(rolled_value)

    spell_level = _prompt_spell_level(ui_client, source="dangerous_sorcery")
    if spell_level is None:
        context["dangerous_sorcery_resolved"] = True
        return int(rolled_value)

    per_level = _dangerous_sorcery_bonus_per_level(actor)
    bonus = max(0, int(spell_level) * int(per_level))
    context["dangerous_sorcery_resolved"] = True
    context["dangerous_sorcery_applied"] = True

    game = context.get("game")
    logger_fn = getattr(game, "ui_log", None)
    if callable(logger_fn):
        try:
            spell_name = str(context.get("spell_name", "spell") or "spell")
            logger_fn(f"Dangerous Sorcery: +{bonus} obrazen do czaru '{spell_name}' (poziom {spell_level}).")
        except Exception:
            pass
    return int(rolled_value) + int(bonus)


def prompt_for_roll(prompt: str, *, return_details: bool = False, infer_natural_from_roll: bool = False, **ui_kwargs):
    """Poproś o rzut i zwróć liczbę całkowitą (UI; CLI tylko gdy ALLOW_CLI_FALLBACK=1).

    Domyślnie wysyła do UI jako layout \"test\" (check), żeby zachować spójny wygląd
    wszystkich promptów na rzuty. Można nadpisać layout/placeholder via **ui_kwargs.
    """
    ui_client = get_ui_client()
    layout = str(ui_kwargs.get("layout", "test") or "test")
    roll_stack_arg = ui_kwargs.pop("roll_stack", None)
    auto_total_modifier = ui_kwargs.pop("auto_total_modifier", None)
    roll_stack_payload = _prepare_roll_stack_payload(
        roll_stack=roll_stack_arg if isinstance(roll_stack_arg, dict) else None,
        modifiers=ui_kwargs.get("modifiers") if isinstance(ui_kwargs.get("modifiers"), dict) else None,
        auto_total_modifier=_int_or_default(auto_total_modifier, 0) if auto_total_modifier is not None else None,
    )
    if roll_stack_payload is None and str(layout).strip().lower() == "damage":
        roll_stack_payload = _default_damage_roll_stack_payload()
    if roll_stack_payload is not None and str(layout).strip().lower() in {"test", "damage"}:
        ui_kwargs["roll_stack"] = roll_stack_payload
    if ui_client.enabled:
        if "layout" not in ui_kwargs:
            ui_kwargs["layout"] = "test"
            layout = "test"
        ui_kwargs.setdefault("answer_placeholder", "Podaj wynik rzutu")
        ui_answer = ui_client.prompt_roll(
            prompt,
            source="game",
            return_meta=bool(return_details),
            **ui_kwargs,
        )
        if return_details:
            details = _parse_roll_details(ui_answer, infer_natural_from_roll=infer_natural_from_roll)
            if str(layout).strip().lower() == "damage":
                details["roll"] = _apply_dangerous_sorcery_if_needed(
                    int(details.get("roll", 0) or 0),
                    ui_client=ui_client,
                    layout=layout,
                )
            return details
        details = _parse_roll_details(ui_answer, infer_natural_from_roll=infer_natural_from_roll)
        value = int(details.get("roll", 0) or 0)
        if str(layout).strip().lower() == "damage":
            value = _apply_dangerous_sorcery_if_needed(
                value,
                ui_client=ui_client,
                layout=layout,
            )
        return value

    if not getattr(ui_client, "allow_cli_fallback", False):
        raise RuntimeError("UI-only mode: prompt_for_roll wymaga aktywnego UI.")

    while True:
        raw = input(prompt).strip()
        if not raw:
            continue
        try:
            value = int(raw)
            if return_details:
                details = _parse_roll_details(value, infer_natural_from_roll=infer_natural_from_roll)
                if str(layout).strip().lower() == "damage":
                    details["roll"] = _apply_dangerous_sorcery_if_needed(
                        int(details.get("roll", 0) or 0),
                        ui_client=ui_client,
                        layout=layout,
                    )
                return details
            if str(layout).strip().lower() == "damage":
                value = _apply_dangerous_sorcery_if_needed(
                    value,
                    ui_client=ui_client,
                    layout=layout,
                )
            return value
        except ValueError:
            continue

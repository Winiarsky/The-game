from __future__ import annotations

from localization import localize_term_pl
from focus_pool import ensure_focus_pool, set_focus_points
from spell_management import ensure_actor_spell_state

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


def _wizard_thesis(actor) -> str:
    setup = _wizard_setup(actor)
    raw = setup.get("thesis")
    if raw is None:
        raw = getattr(actor, "wizard_thesis", None)
    return _normalize(raw)


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


def _spell_state(actor) -> dict:
    state = getattr(actor, "spell_state", None)
    if isinstance(state, dict):
        return state
    return {}


def _actor_scenario_key(actor) -> str:
    raw_id = str(getattr(actor, "object_id", "") or "").strip()
    if raw_id:
        return f"actor:{raw_id}"
    raw_name = str(getattr(actor, "name", "") or "").strip()
    if raw_name:
        return f"name:{raw_name.lower()}"
    return f"pyid:{id(actor)}"


def _scenario_substitution_usage(game) -> set[str]:
    raw = getattr(game, "_wizard_spell_substitution_used", None)
    if isinstance(raw, set):
        return raw
    try:
        payload: set[str] = set()
        setattr(game, "_wizard_spell_substitution_used", payload)
        return payload
    except Exception:
        return set()


def _is_spell_substitution_used(game, actor) -> bool:
    if game is None or actor is None:
        return False
    usage = _scenario_substitution_usage(game)
    return _actor_scenario_key(actor) in usage


def _mark_spell_substitution_used(game, actor) -> None:
    if game is None or actor is None:
        return
    usage = _scenario_substitution_usage(game)
    usage.add(_actor_scenario_key(actor))


def _rank_from_tier(tier: str) -> int | None:
    raw = _normalize(tier)
    if not raw.startswith("rank_"):
        return None
    try:
        rank = int(raw.split("_", 1)[1])
    except Exception:
        return None
    if rank < 1:
        return None
    return rank


def _build_substitution_options(state: dict) -> list[dict]:
    prepared_counts = dict(state.get("prepared_counts", {}) or {})
    consumed_counts = dict(state.get("consumed_counts", {}) or {})
    known = dict(state.get("known", {}) or {})

    options: list[dict] = []
    for tier, prepared_map_raw in prepared_counts.items():
        rank = _rank_from_tier(tier)
        if rank is None:
            continue
        prepared_map = dict(prepared_map_raw or {})
        consumed_map = dict(consumed_counts.get(tier, {}) or {})
        known_spells = [
            _normalize(spell_id)
            for spell_id in list(known.get(tier, []) or [])
            if _normalize(spell_id)
        ]
        if not known_spells:
            continue
        for spell_id, prepared_total_raw in prepared_map.items():
            spell = _normalize(spell_id)
            if not spell:
                continue
            try:
                prepared_total = int(prepared_total_raw or 0)
            except Exception:
                prepared_total = 0
            try:
                consumed_total = int(consumed_map.get(spell, 0) or 0)
            except Exception:
                consumed_total = 0
            available_total = max(0, prepared_total - consumed_total)
            if available_total <= 0:
                continue
            replacements = [candidate for candidate in known_spells if candidate and candidate != spell]
            if not replacements:
                continue
            options.append(
                {
                    "tier": tier,
                    "rank": rank,
                    "from_spell": spell,
                    "available": available_total,
                    "replacements": replacements,
                }
            )
    return options


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
    base = localize_term_pl(str(spell_id or "").strip())
    return f"{base} (ranga {max(1, int(rank or 1))})"


def _decode_menu_selection(answer: str | None, labels: list[str]) -> str | None:
    raw = str(answer or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(labels):
            return labels[idx]
        return None
    low = _normalize(raw)
    for label in labels:
        if low == _normalize(label):
            return label
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
            if _normalize(entry.get("cast_source")) == "staff_nexus":
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
        cast_result = dispatch_event(
            spell_id,
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata={
                    **dict(ctx.metadata or {}),
                    "wizard_drain_recast": True,
                    "wizard_drain_bucket": str(selected.get("bucket") or ""),
                    "wizard_drain_rank": int(selected.get("rank", 1) or 1),
                },
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
class WizardSpellSubstitutionEvent(GameEvent):
    name = "wizard_spell_substitution"
    consumes_action = False
    available_in_combat = False
    available_in_exploration = True

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message=f"{self.name}: missing actor.")
        if not _is_wizard(actor):
            return EventResult.cancelled(message=f"{self.name}: only Wizard can use this action.")
        if ctx.in_combat:
            return EventResult.cancelled(message=f"{self.name}: available only in exploration (10 minutes).")
        if _wizard_thesis(actor) != "spell_substitution":
            return EventResult.cancelled(message=f"{self.name}: requires thesis Spell Substitution.")
        if _is_spell_substitution_used(ctx.game, actor):
            return EventResult.cancelled(message=f"{self.name}: already used once per scenario.")

        try:
            state = ensure_actor_spell_state(actor, game=ctx.game, enforce=True)
        except Exception:
            state = _spell_state(actor)
        if not isinstance(state, dict) or not state:
            return EventResult.cancelled(message=f"{self.name}: missing spell state.")

        options = _build_substitution_options(state)
        if not options:
            return EventResult.cancelled(
                message=f"{self.name}: no prepared uncast spell copy can be substituted right now."
            )

        header_labels: list[str] = []
        header_map: dict[str, dict] = {}
        for entry in options:
            label = (
                f"Ranga {int(entry.get('rank', 1) or 1)}: "
                f"{localize_term_pl(str(entry.get('from_spell') or ''))} "
                f"(wolne kopie: {int(entry.get('available', 0) or 0)})"
            )
            header_labels.append(label)
            header_map[label] = entry
        header_labels.append("cancel")
        picked_header = _prompt_choice(
            ctx,
            "Spell Substitution (10 minut): wybierz przygotowany czar do podmiany",
            header_labels,
            source=self.name,
        )
        selected_header = _decode_menu_selection(picked_header, header_labels)
        if selected_header is None:
            return EventResult.cancelled(message=f"{self.name}: cancelled.")
        if _normalize(selected_header) == "cancel":
            return EventResult.cancelled(message=f"{self.name}: cancelled.")
        selected = header_map.get(selected_header)
        if selected is None:
            return EventResult.cancelled(message=f"{self.name}: invalid first selection.")

        replacements = list(selected.get("replacements", []) or [])
        if not replacements:
            return EventResult.cancelled(message=f"{self.name}: no replacement spells available.")
        replacement_labels = [localize_term_pl(spell_id) for spell_id in replacements]
        replacement_labels.append("cancel")
        replacement_map = {label: spell_id for label, spell_id in zip(replacement_labels, replacements)}

        picked_replacement = _prompt_choice(
            ctx,
            "Spell Substitution: wybierz nowy czar z tej samej rangi",
            replacement_labels,
            source=self.name,
        )
        selected_replacement = _decode_menu_selection(picked_replacement, replacement_labels)
        if selected_replacement is None:
            return EventResult.cancelled(message=f"{self.name}: cancelled.")
        if _normalize(selected_replacement) == "cancel":
            return EventResult.cancelled(message=f"{self.name}: cancelled.")
        replacement_spell = _normalize(replacement_map.get(selected_replacement))
        if not replacement_spell:
            return EventResult.cancelled(message=f"{self.name}: invalid replacement selection.")

        tier = str(selected.get("tier") or "")
        from_spell = _normalize(selected.get("from_spell"))
        if not tier or not from_spell:
            return EventResult.cancelled(message=f"{self.name}: invalid substitution payload.")
        if replacement_spell == from_spell:
            return EventResult.cancelled(message=f"{self.name}: replacement must be different spell.")

        prepared_today = dict(state.get("prepared_today", {}) or {})
        prepared_list = list(prepared_today.get(tier, []) or [])
        replaced = False
        for idx, spell_id in enumerate(prepared_list):
            if _normalize(spell_id) != from_spell:
                continue
            prepared_list[idx] = replacement_spell
            replaced = True
            break
        if not replaced:
            return EventResult.cancelled(message=f"{self.name}: prepared list is out of sync.")
        prepared_today[tier] = prepared_list
        state["prepared_today"] = prepared_today

        prepared_counts_all = dict(state.get("prepared_counts", {}) or {})
        prepared_counts_tier = dict(prepared_counts_all.get(tier, {}) or {})
        try:
            from_count = int(prepared_counts_tier.get(from_spell, 0) or 0)
        except Exception:
            from_count = 0
        if from_count <= 0:
            return EventResult.cancelled(message=f"{self.name}: prepared counts are out of sync.")
        prepared_counts_tier[from_spell] = max(0, from_count - 1)
        if int(prepared_counts_tier.get(from_spell, 0) or 0) <= 0:
            prepared_counts_tier.pop(from_spell, None)
        prepared_counts_tier[replacement_spell] = int(prepared_counts_tier.get(replacement_spell, 0) or 0) + 1
        prepared_counts_all[tier] = prepared_counts_tier
        state["prepared_counts"] = prepared_counts_all

        try:
            setattr(actor, "spell_state", state)
        except Exception:
            pass
        _mark_spell_substitution_used(ctx.game, actor)

        rank = int(selected.get("rank", 1) or 1)
        return EventResult(
            success=True,
            consumed_action=False,
            message=(
                "Spell Substitution (10 minut): "
                f"Ranga {rank}, {localize_term_pl(from_spell)} -> {localize_term_pl(replacement_spell)}."
            ),
        )


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

        current, max_pool = ensure_focus_pool(actor)
        if max_pool <= 0:
            return EventResult.cancelled(message="refocus: actor has no Focus Pool.")

        if current >= max_pool:
            return EventResult.cancelled(message=f"refocus: focus pool already full ({current}/{max_pool}).")

        new_value = set_focus_points(actor, current + 1, clamp_to_pool=True)

        class_label = localize_term_pl(_normalize(getattr(actor, "class_name", "")))
        class_hint = f" ({class_label})" if class_label else ""
        return EventResult(
            success=True,
            consumed_action=False,
            message=(
                f"Refocus{class_hint}: 10 minut skupienia/modlitwy/medytacji zależnie od źródła mocy. "
                f"Focus Point {current} -> {new_value}/{max_pool}."
            ),
        )

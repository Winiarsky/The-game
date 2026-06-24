from __future__ import annotations

from localization import localize_term_pl
from spell_management import (
    _collect_spells_for_tier_and_tradition,
    _normalize_spell_id,
    _normalize_tier,
    _rank_tiers,
    _sorcerer_setup_data,
    ensure_actor_spell_state,
    swap_sorcerer_repertoire_spell,
)

from .base import EventContext, EventResult, GameEvent
from .registry import register_event


def _normalize(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _labelize_spell(spell_id: str) -> str:
    return localize_term_pl(str(spell_id or "").strip())


def _tier_label(tier: str) -> str:
    normalized = _normalize_tier(tier)
    if normalized == "cantrip":
        return "Cantrip"
    if normalized.startswith("rank_"):
        try:
            return f"Ranga {int(normalized.split('_', 1)[1])}"
        except Exception:
            return normalized
    return normalized or str(tier or "")


def _is_sorcerer(actor) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            if bool(checker("sorcerer")):
                return True
        except Exception:
            pass
    return _normalize(getattr(actor, "class_name", "")) == "sorcerer"


def build_sorcerer_retrain_options(actor, *, game=None) -> list[dict]:
    if not _is_sorcerer(actor):
        return []

    try:
        state = ensure_actor_spell_state(actor, game=game, enforce=True)
    except Exception:
        state = dict(getattr(actor, "spell_state", {}) or {})
    if not isinstance(state, dict) or not state:
        return []

    known = dict(state.get("known", {}) or {})
    setup = _sorcerer_setup_data(actor)
    tradition = _normalize(setup.get("spell_tradition") or getattr(actor, "sorcerer_spell_tradition", ""))
    bloodline_granted = dict(
        setup.get("bloodline_granted_spells")
        or getattr(actor, "sorcerer_bloodline_granted_spells", {})
        or {}
    )
    signatures = {
        _normalize_spell_id(item)
        for item in list(state.get("sorcerer_signature_spells", []) or [])
        if _normalize_spell_id(item)
    }

    options: list[dict] = []
    for tier in ("cantrip", *_rank_tiers()):
        tier_known = []
        for item in list(known.get(tier, []) or []):
            spell_id = _normalize_spell_id(item)
            if spell_id and spell_id not in tier_known:
                tier_known.append(spell_id)
        if not tier_known:
            continue

        bloodline_spell = _normalize_spell_id(bloodline_granted.get(tier))
        tier_pool = [
            _normalize_spell_id(item)
            for item in _collect_spells_for_tier_and_tradition(
                tier=tier,
                traditions={tradition} if tradition else set(),
            )
            if _normalize_spell_id(item)
        ]
        if not tier_pool:
            continue

        tier_known_set = set(tier_known)
        for source_spell in tier_known:
            if bloodline_spell and source_spell == bloodline_spell:
                continue
            replacements = [
                spell_id
                for spell_id in tier_pool
                if spell_id != source_spell and spell_id not in tier_known_set
            ]
            if not replacements:
                continue
            options.append(
                {
                    "tier": tier,
                    "source_spell": source_spell,
                    "replacements": replacements,
                    "is_signature": source_spell in signatures,
                }
            )
    return options


def has_retrainable_sorcerer_spell(actor, *, game=None) -> bool:
    return bool(build_sorcerer_retrain_options(actor, game=game))


def _decode_choice(answer: object, entries: list[dict[str, str]]) -> str | None:
    raw = str(answer or "").strip()
    if not raw:
        return None
    low = raw.lower()
    for entry in entries:
        raw_id = str(entry.get("raw", "")).strip().lower()
        label = str(entry.get("label", "")).strip().lower()
        if low == raw_id or (label and low == label):
            return raw_id or None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(entries):
            mapped = str(entries[idx].get("raw", "")).strip().lower()
            if mapped:
                return mapped
    return low or None


def _prompt_choice(ctx: EventContext, prompt: str, entries: list[dict[str, str]]) -> str | None:
    ui = getattr(ctx.game, "ui", None)
    if ui is None:
        return None
    chooser = getattr(ui, "prompt_choice", None)
    if not callable(chooser):
        return None
    try:
        answer = chooser(
            prompt,
            choices=[entry["label"] for entry in entries],
            source="retrain_sorcerer_spell",
            choice_meta=entries,
        )
    except Exception:
        return None
    return _decode_choice(answer, entries)


@register_event
class RetrainSorcererSpellEvent(GameEvent):
    name = "retrain_sorcerer_spell"
    default_tags = ["sorcerer"]
    consumes_action = False
    actions_cost = 0
    available_in_combat = False
    available_in_exploration = True

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message=f"{self.name}: missing actor.")
        if not _is_sorcerer(actor):
            return EventResult.cancelled(message=f"{self.name}: only Sorcerer can use this action.")

        options = build_sorcerer_retrain_options(actor, game=ctx.game)
        if not options:
            return EventResult.cancelled(
                message=f"{self.name}: no eligible repertoire spell can be retrained right now."
            )

        source_entries: list[dict[str, str]] = []
        source_map: dict[str, dict] = {}
        for idx, option in enumerate(options, start=1):
            source_key = f"{option['tier']}::{option['source_spell']}"
            desc_parts = [_tier_label(str(option.get("tier") or ""))]
            if option.get("is_signature"):
                desc_parts.append("Signature spell przeniesie sie na nowy czar.")
            source_entries.append(
                {
                    "raw": source_key,
                    "label": f"{_labelize_spell(str(option.get('source_spell') or ''))} ({_tier_label(str(option.get('tier') or ''))})",
                    "desc": " ".join(desc_parts),
                    "key": str(idx),
                }
            )
            source_map[source_key] = option

        picked_source = _prompt_choice(
            ctx,
            "Retrain Sorcerer Spell: wybierz czar z repertuaru do podmiany",
            source_entries,
        )
        if not picked_source:
            return EventResult.cancelled(message=f"{self.name}: cancelled.")

        selected = source_map.get(picked_source)
        if selected is None:
            return EventResult.cancelled(message=f"{self.name}: invalid source selection.")

        replacements = list(selected.get("replacements", []) or [])
        if not replacements:
            return EventResult.cancelled(message=f"{self.name}: no replacement spells available.")

        replacement_entries: list[dict[str, str]] = []
        replacement_map: dict[str, str] = {}
        for idx, spell_id in enumerate(replacements, start=1):
            normalized = _normalize_spell_id(spell_id)
            replacement_entries.append(
                {
                    "raw": normalized,
                    "label": _labelize_spell(normalized),
                    "desc": _tier_label(str(selected.get("tier") or "")),
                    "key": str(idx),
                }
            )
            replacement_map[normalized] = normalized

        picked_replacement = _prompt_choice(
            ctx,
            "Retrain Sorcerer Spell: wybierz nowy czar tej samej rangi",
            replacement_entries,
        )
        replacement_spell = replacement_map.get(str(picked_replacement or "").strip().lower())
        if not replacement_spell:
            return EventResult.cancelled(message=f"{self.name}: invalid replacement selection.")

        ok, message = swap_sorcerer_repertoire_spell(
            actor,
            from_spell=str(selected.get("source_spell") or ""),
            to_spell=replacement_spell,
            tier=str(selected.get("tier") or ""),
            game=ctx.game,
        )
        if not ok:
            return EventResult.cancelled(message=f"{self.name}: {message}")

        return EventResult(
            success=True,
            consumed_action=False,
            message=f"Retrain Sorcerer Spell: {message}",
        )

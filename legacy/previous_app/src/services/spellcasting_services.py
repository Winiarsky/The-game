from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from localization import localize_term_pl, localized_hint_pl
from spell_management import (
    classify_spell_tier,
    grant_merchant_one_shot_spell,
    merchant_spell_capacity,
    merchant_spell_count,
)

_SUPPORTED_TRADITIONS = ("arcana", "primal", "divine", "occult")


@dataclass(frozen=True)
class SpellServiceChoice:
    spell_id: str
    tier: str
    label: str
    traditions: tuple[str, ...]
    desc: str


def _normalize(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def parse_service_rank(service_id: object) -> int | None:
    raw = _normalize(service_id)
    if raw == "spellcasting_service_cantrip":
        return 0
    prefix = "spellcasting_service_rank_"
    if not raw.startswith(prefix):
        return None
    suffix = raw[len(prefix) :]
    try:
        return max(1, int(suffix))
    except Exception:
        return None


def _allowed_tiers_for_service(rank: int, *, allow_cantrips: bool) -> set[str]:
    allowed: set[str] = set()
    if rank <= 0:
        if allow_cantrips:
            allowed.add("cantrip")
        return allowed
    allowed.add(f"rank_{rank}")
    return allowed


def _event_tags(event_cls: type | None) -> set[str]:
    tags: set[str] = set()
    if event_cls is None:
        return tags
    for tag in list(getattr(event_cls, "spell_tags", []) or []):
        normalized = _normalize(tag)
        if normalized:
            tags.add(normalized)
    for tag in list(getattr(event_cls, "default_tags", []) or []):
        normalized = _normalize(tag)
        if normalized:
            tags.add(normalized)
    return tags


def _event_traditions(event_cls: type | None, tags: set[str]) -> set[str]:
    traditions = {tag for tag in tags if tag in _SUPPORTED_TRADITIONS}
    if event_cls is None:
        return traditions
    for tradition in list(getattr(event_cls, "magic_traditions", []) or []):
        value = _normalize(getattr(tradition, "value", tradition))
        if value in _SUPPORTED_TRADITIONS:
            traditions.add(value)
    return traditions


def _tier_label_pl(tier: str) -> str:
    if tier == "cantrip":
        return "Cantrip"
    if tier.startswith("rank_"):
        try:
            return f"Ranga {max(1, int(tier.split('_', 1)[1]))}"
        except Exception:
            return "Ranga"
    return localize_term_pl(tier)


def list_spell_choices_for_service(
    *,
    service_id: str,
    traditions: set[str],
    max_rank: int,
    allow_cantrips: bool,
    catalog: set[str] | None = None,
) -> list[SpellServiceChoice]:
    rank = parse_service_rank(service_id)
    if rank is None:
        return []
    if rank > max_rank:
        return []

    try:
        import GameObjects.events.all_events  # noqa: F401
        from GameObjects.events.registry import list_events
    except Exception:
        return []

    allowed_tiers = _allowed_tiers_for_service(rank, allow_cantrips=allow_cantrips)
    wanted_traditions = {item for item in traditions if item in _SUPPORTED_TRADITIONS}
    allowed_catalog = {_normalize(item) for item in list(catalog or set()) if _normalize(item)}

    entries: list[SpellServiceChoice] = []
    for event_name, event_cls in dict(list_events() or {}).items():
        spell_id = _normalize(event_name)
        if not spell_id:
            continue
        if allowed_catalog and spell_id not in allowed_catalog:
            continue
        tags = _event_tags(event_cls)
        tier = classify_spell_tier(list(tags))
        if not tier:
            continue
        if tier == "focus":
            continue
        if tier not in allowed_tiers:
            continue

        event_traditions = _event_traditions(event_cls, tags)
        if wanted_traditions and not event_traditions.intersection(wanted_traditions):
            continue

        label = localize_term_pl(spell_id)
        hint = localized_hint_pl(spell_id)
        desc_parts = [
            f"Typ: {_tier_label_pl(tier)}",
            "Tradycja: " + ", ".join(localize_term_pl(item) for item in sorted(event_traditions))
            if event_traditions
            else "Tradycja: ogolna",
        ]
        if hint:
            desc_parts.insert(0, hint)
        entries.append(
            SpellServiceChoice(
                spell_id=spell_id,
                tier=tier,
                label=label,
                traditions=tuple(sorted(event_traditions)),
                desc="\n".join(part for part in desc_parts if part),
            )
        )

    entries.sort(key=lambda item: (item.tier, item.label.lower(), item.spell_id))
    return entries


def choose_spell_for_service(
    *,
    game,
    actor,
    provider_name: str,
    service_id: str,
    traditions: set[str],
    max_rank: int,
    allow_cantrips: bool,
    catalog: set[str] | None = None,
) -> SpellServiceChoice | None:
    choices = list_spell_choices_for_service(
        service_id=service_id,
        traditions=traditions,
        max_rank=max_rank,
        allow_cantrips=allow_cantrips,
        catalog=catalog,
    )
    if not choices:
        return None

    ui = getattr(game, "ui", None)
    labels = [item.label for item in choices]
    cap = merchant_spell_capacity(actor)
    used = merchant_spell_count(actor)

    if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_choice"):
        choice_meta = [
            {
                "raw": item.spell_id,
                "label": item.label,
                "desc": item.desc,
                "key": "",
            }
            for item in choices
        ]
        answer = ui.prompt_choice(
            "Usluga rzucenia czaru: wybierz czar",
            choices=labels,
            source="service_spellcasting",
            layout="menu_numpad",
            title=f"Usluga magiczna: {provider_name}",
            subtitle="8/2 nawigacja, Enter potwierdzenie.",
            prompt_long=(
                "Kupujesz jednorazowy czar do rzucenia z akcji Magia.\n"
                f"Limit aktywnych czarow uslugowych: {used}/{cap}."
            ),
            choice_meta=choice_meta,
        )
        raw = _normalize(answer)
        if not raw:
            return None
        for item in choices:
            if raw == _normalize(item.spell_id) or raw == _normalize(item.label):
                return item
        if str(answer or "").strip().isdigit():
            idx = int(str(answer).strip()) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        return None

    return choices[0]


def add_service_spell_to_actor(
    *,
    actor,
    spell_id: str,
    tier: str,
    provider_name: str,
    game=None,
) -> tuple[bool, str]:
    return grant_merchant_one_shot_spell(
        actor,
        spell_id=spell_id,
        tier=tier,
        provider_name=provider_name,
        game=game,
    )


__all__ = [
    "SpellServiceChoice",
    "add_service_spell_to_actor",
    "choose_spell_for_service",
    "list_spell_choices_for_service",
    "merchant_spell_capacity",
    "merchant_spell_count",
    "parse_service_rank",
]

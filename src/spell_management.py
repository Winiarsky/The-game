from __future__ import annotations

from typing import Any


_CASTER_CLASSES = {"wizard", "sorcerer", "cleric", "druid", "bard", "magus"}
_KNOWN_TIERS = (
    "cantrip",
    "focus",
    "rank_1",
    "rank_2",
    "rank_3",
    "rank_4",
    "rank_5",
    "rank_6",
    "rank_7",
    "rank_8",
    "rank_9",
    "rank_10",
    "innate",
)
_SPELL_ID_ALIASES = {
    "shield": "shield_cantrip",
    "detectmagic": "detect_magic",
    "acidsplash": "acid_splash",
}
_BARD_DEFAULT_TRADITION = "occult"
_BARD_DEFAULT_CANTRIP_COUNT_L1 = 5
_BARD_DEFAULT_RANK1_COUNT_L1 = 2
_BARD_DEFAULT_RANK1_SLOTS_L1 = 2
_BARD_BONUS_CANTRIPS = ("inspire_courage", "counter_performance")
_BARD_BONUS_FOCUS = ("counter_performance",)
_SORCERER_DEFAULT_CANTRIP_COUNT_L1 = 5
_SORCERER_DEFAULT_RANK1_COUNT_L1 = 2
_SORCERER_DEFAULT_RANK1_SLOTS_L1 = 3
_CLERIC_DEFAULT_TRADITION = "divine"
_CLERIC_DEFAULT_CANTRIP_PREPARED_L1 = 5
_CLERIC_DEFAULT_RANK1_SLOTS_L1 = 2
_DRUID_DEFAULT_TRADITION = "primal"
_DRUID_DEFAULT_CANTRIP_PREPARED_L1 = 5
_DRUID_DEFAULT_RANK1_SLOTS_L1 = 2


def _actor_level(actor) -> int:
    try:
        level = int(getattr(actor, "level", 1) or 1)
    except Exception:
        level = 1
    return max(1, min(20, level))


def _normalize(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _normalize_spell_id(value: object) -> str:
    raw = _normalize(value)
    if not raw:
        return ""
    return _SPELL_ID_ALIASES.get(raw, raw)


def _labelize(value: str) -> str:
    return str(value or "").strip().replace("_", " ").title()


def _iter_status_data(actor) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for status in list(getattr(actor, "statuses", []) or []):
        data = getattr(status, "data", None)
        if isinstance(data, dict):
            out.append(data)
    return out


def _removed_cantrip_ids(actor) -> set[str]:
    removed: set[str] = set()
    for data in _iter_status_data(actor):
        values = data.get("removed_cantrips")
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, (list, tuple, set)):
            continue
        for item in values:
            spell_id = _normalize_spell_id(item)
            if spell_id:
                removed.add(spell_id)
    return removed


def _apply_removed_cantrip_overrides(actor, known: dict[str, list[str]]) -> None:
    removed = _removed_cantrip_ids(actor)
    if not removed:
        return
    cantrips = [
        _normalize_spell_id(item)
        for item in list(known.get("cantrip", []) or [])
        if _normalize_spell_id(item) and _normalize_spell_id(item) not in removed
    ]
    known["cantrip"] = list(dict.fromkeys(cantrips))


def _append_unique(container: list[str], value: str) -> None:
    item = _normalize_spell_id(value)
    if not item:
        return
    if item not in container:
        container.append(item)


def _append_many(container: list[str], values: object) -> None:
    if isinstance(values, str):
        _append_unique(container, values)
        return
    if not isinstance(values, (list, tuple, set)):
        return
    for value in values:
        _append_unique(container, str(value))


def _normalize_tier(value: object) -> str:
    raw = _normalize(value).replace("-", "_").replace(" ", "_")
    if raw in {"cantrip", "cantrips"}:
        return "cantrip"
    if raw in {"focus", "innate"}:
        return raw
    if raw.endswith(("st", "nd", "rd", "th")):
        raw = raw[:-2]
    if raw.isdigit():
        try:
            rank = int(raw)
        except Exception:
            rank = 0
        if rank >= 1:
            return f"rank_{rank}"
    if raw in {"rank1", "rank_1"}:
        return "rank_1"
    if raw in {"rank2", "rank_2"}:
        return "rank_2"
    if raw in {"rank3", "rank_3"}:
        return "rank_3"
    if raw in {"rank4", "rank_4"}:
        return "rank_4"
    if raw in {"rank5", "rank_5"}:
        return "rank_5"
    if raw in {"rank6", "rank_6"}:
        return "rank_6"
    if raw in {"rank7", "rank_7"}:
        return "rank_7"
    if raw in {"rank8", "rank_8"}:
        return "rank_8"
    if raw in {"rank9", "rank_9"}:
        return "rank_9"
    if raw in {"rank10", "rank_10"}:
        return "rank_10"
    return ""


def _tier_for_rank(rank: int) -> str:
    return f"rank_{max(1, int(rank))}"


def _rank_for_tier(tier: str) -> int | None:
    normalized = _normalize_tier(tier)
    if not normalized.startswith("rank_"):
        return None
    try:
        value = int(normalized.split("_", 1)[1])
    except Exception:
        return None
    if value < 1:
        return None
    return value


def _is_rank_tier(tier: str | None) -> bool:
    return bool(_rank_for_tier(str(tier or "")))


def _normalize_merchant_one_shot(raw: object) -> dict[str, dict[str, int]]:
    normalized: dict[str, dict[str, int]] = {}
    if not isinstance(raw, dict):
        return normalized
    for tier, spells in raw.items():
        tier_id = _normalize_tier(tier)
        if not tier_id:
            continue
        if not isinstance(spells, dict):
            continue
        bucket: dict[str, int] = {}
        for spell_id, count in spells.items():
            sid = _normalize_spell_id(spell_id)
            if not sid:
                continue
            try:
                value = int(count or 0)
            except Exception:
                value = 0
            if value <= 0:
                continue
            bucket[sid] = max(0, value)
        if bucket:
            normalized[tier_id] = bucket
    return normalized


def _normalize_merchant_known(raw: object) -> dict[str, set[str]]:
    normalized: dict[str, set[str]] = {}
    if not isinstance(raw, dict):
        return normalized
    for tier, spells in raw.items():
        tier_id = _normalize_tier(tier)
        if not tier_id:
            continue
        bucket: set[str] = set()
        if isinstance(spells, dict):
            for spell_id, enabled in spells.items():
                if not bool(enabled):
                    continue
                sid = _normalize_spell_id(spell_id)
                if sid:
                    bucket.add(sid)
        elif isinstance(spells, (list, tuple, set)):
            for spell_id in spells:
                sid = _normalize_spell_id(spell_id)
                if sid:
                    bucket.add(sid)
        if bucket:
            normalized[tier_id] = bucket
    return normalized


def _merchant_one_shot_total(one_shot: dict[str, dict[str, int]]) -> int:
    total = 0
    for spells in one_shot.values():
        if not isinstance(spells, dict):
            continue
        for count in spells.values():
            try:
                total += max(0, int(count or 0))
            except Exception:
                continue
    return max(0, total)


def merchant_spell_capacity(actor) -> int:
    ability_mods = dict(getattr(actor, "ability_modifiers", {}) or {})
    if "intelligence" in ability_mods:
        try:
            return max(1, int(ability_mods.get("intelligence", 0) or 0))
        except Exception:
            return 1
    try:
        return max(1, int(getattr(actor, "int_mod", 0) or 0))
    except Exception:
        return 1


def merchant_spell_count(actor) -> int:
    state = dict(getattr(actor, "spell_state", {}) or {})
    one_shot = _normalize_merchant_one_shot(state.get("merchant_one_shot"))
    return _merchant_one_shot_total(one_shot)


def _event_tier(spell_id: str) -> str | None:
    try:
        import GameObjects.events.all_events  # noqa: F401
        from GameObjects.events.registry import list_events
    except Exception:
        return None
    events = list_events()
    event_cls = events.get(_normalize(spell_id))
    if event_cls is None:
        return None
    tags: list[str] = []
    for tag in list(getattr(event_cls, "spell_tags", []) or []):
        tags.append(_normalize(tag))
    for tag in list(getattr(event_cls, "default_tags", []) or []):
        tags.append(_normalize(tag))
    if "focus" in tags:
        return "focus"
    if "cantrip" in tags:
        return "cantrip"
    for tag in tags:
        if tag.startswith("rank"):
            suffix = tag[4:]
            try:
                rank = max(1, int(suffix))
            except Exception:
                continue
            return f"rank_{rank}"
    return None


def _event_cls_for_spell(spell_id: str):
    try:
        import GameObjects.events.all_events  # noqa: F401
        from GameObjects.events.registry import list_events
    except Exception:
        return None
    return list_events().get(_normalize(spell_id))


def _auto_spell_desc(event_cls) -> str:
    """Build a brief Polish mechanical description from event class attributes."""
    if event_cls is None:
        return ""
    _SAVE_LABELS = {"fortitude": "Wytrzymałość", "reflex": "Refleks", "will": "Wola"}
    parts: list[str] = []
    try:
        cost = max(1, min(3, int(getattr(event_cls, "actions_cost", 1) or 1)))
    except Exception:
        cost = 1
    parts.append("1 akcja" if cost == 1 else f"{cost} akcje")

    raw_range = getattr(event_cls, "range_feet", None)
    if isinstance(raw_range, int) and raw_range > 0:
        parts.append(f"zasięg {raw_range} ft")

    area_feet = getattr(event_cls, "area_feet", None)
    area_type = str(getattr(event_cls, "area_type", "") or "").strip()
    if isinstance(area_feet, int) and area_feet > 0:
        area_suffix = f" ({area_type})" if area_type else ""
        parts.append(f"obszar {area_feet} ft{area_suffix}")

    damage_prompt = str(getattr(event_cls, "damage_prompt", "") or "").strip()
    if damage_prompt:
        parts.append(f"obrażenia {damage_prompt}")

    save_type = str(getattr(event_cls, "save_type", "") or "").strip().lower()
    if save_type in _SAVE_LABELS:
        is_basic = bool(getattr(event_cls, "basic_save", False))
        parts.append(f"rzut obronny: {_SAVE_LABELS[save_type]}{' (basic)' if is_basic else ''}")

    duration = str(getattr(event_cls, "duration", "") or "").strip()
    if duration:
        parts.append(f"czas trwania: {duration}")

    return ", ".join(parts)


def _event_tags(spell_id: str) -> set[str]:
    try:
        import GameObjects.events.all_events  # noqa: F401
        from GameObjects.events.registry import list_events
    except Exception:
        return set()
    events = list_events()
    event_cls = events.get(_normalize(spell_id))
    if event_cls is None:
        return set()
    tags: set[str] = set()
    for tag in list(getattr(event_cls, "spell_tags", []) or []):
        normalized = _normalize(tag)
        if normalized:
            tags.add(normalized)
    for tag in list(getattr(event_cls, "default_tags", []) or []):
        normalized = _normalize(tag)
        if normalized:
            tags.add(normalized)
    for tradition in list(getattr(event_cls, "magic_traditions", []) or []):
        normalized = _normalize(getattr(tradition, "value", tradition))
        if normalized:
            tags.add(normalized)
    if "arcane" in tags:
        tags.add("arcana")
    if "arcana" in tags:
        tags.add("arcane")
    return tags


def _collect_spells_for_tier_and_tradition(*, tier: str, traditions: set[str]) -> list[str]:
    try:
        import GameObjects.events.all_events  # noqa: F401
        from GameObjects.events.registry import list_events
    except Exception:
        return []
    normalized_tier = _normalize_tier(tier)
    if not normalized_tier:
        return []
    wanted = {_normalize(item) for item in set(traditions or set()) if _normalize(item)}
    if "arcane" in wanted:
        wanted.add("arcana")
    if "arcana" in wanted:
        wanted.add("arcane")

    out: list[str] = []
    for event_name in dict(list_events() or {}):
        spell_id = _normalize_spell_id(event_name)
        if not spell_id:
            continue
        tags = _event_tags(spell_id)
        if normalize_tier := _normalize_tier(classify_spell_tier(list(tags))):
            if normalize_tier != normalized_tier:
                continue
        else:
            continue
        if wanted and not tags.intersection(wanted):
            continue
        if spell_id not in out:
            out.append(spell_id)
    out.sort()
    return out


def classify_spell_tier(tags: list[str] | None) -> str | None:
    normalized = [_normalize(tag) for tag in list(tags or [])]
    if "focus" in normalized:
        return "focus"
    if "cantrip" in normalized:
        return "cantrip"
    for tag in normalized:
        if tag.startswith("rank"):
            suffix = tag[4:]
            try:
                rank = max(1, int(suffix))
            except Exception:
                continue
            return f"rank_{rank}"
    return None


def _base_known_spell_lists(actor) -> dict[str, list[str]]:
    known: dict[str, list[str]] = {
        "cantrip": [],
        "focus": [],
        "rank_1": [],
        "rank_2": [],
        "rank_3": [],
        "rank_4": [],
        "rank_5": [],
        "rank_6": [],
        "rank_7": [],
        "rank_8": [],
        "rank_9": [],
        "rank_10": [],
        "innate": [],
    }

    attr_tier_map: dict[str, str] = {
        "sorcerer_known_cantrips": "cantrip",
        "sorcerer_known_rank_1_spells": "rank_1",
        "sorcerer_known_rank_2_spells": "rank_2",
        "sorcerer_known_rank_3_spells": "rank_3",
        "sorcerer_known_rank_4_spells": "rank_4",
        "sorcerer_known_rank_5_spells": "rank_5",
        "sorcerer_known_rank_6_spells": "rank_6",
        "sorcerer_known_rank_7_spells": "rank_7",
        "sorcerer_known_rank_8_spells": "rank_8",
        "sorcerer_known_rank_9_spells": "rank_9",
        "sorcerer_known_rank_10_spells": "rank_10",
        "sorcerer_focus_spells": "focus",
        "bard_known_cantrips": "cantrip",
        "bard_known_rank_1_spells": "rank_1",
        "bard_focus_spells": "focus",
        "wizard_focus_spells": "focus",
        "wizard_school_spells": "rank_1",
        "druid_order_spells": "focus",
        "cleric_domain_spells": "focus",
    }
    for attr_name, tier in attr_tier_map.items():
        _append_many(known[tier], getattr(actor, attr_name, None))

    raw_spellbook = getattr(actor, "wizard_spellbook", None)
    if isinstance(raw_spellbook, dict):
        for tier in ("cantrip", "rank_1", "rank_2", "rank_3", "rank_4", "rank_5", "rank_6", "rank_7", "rank_8", "rank_9", "rank_10"):
            source = raw_spellbook.get(tier)
            if tier == "rank_1" and source is None:
                source = raw_spellbook.get("rank1")
            if tier == "cantrip" and source is None:
                source = raw_spellbook.get("cantrips")
            _append_many(known[tier], source)

    _append_unique(known["rank_1"], getattr(actor, "wizard_school_bonus_spell", ""))
    _append_unique(known["focus"], getattr(actor, "wizard_school_focus_spell", ""))
    _append_unique(known["focus"], getattr(actor, "sorcerer_bloodline_initial_focus_spell", ""))
    _append_unique(known["focus"], getattr(actor, "druid_order_spell", ""))

    pending: list[str] = []

    def _pending_from_dict(raw: object) -> None:
        if not isinstance(raw, dict):
            return
        for value in raw.values():
            _append_unique(pending, str(value))

    for data in _iter_status_data(actor):
        _append_many(known["innate"], data.get("granted_cantrips"))
        _append_many(known["cantrip"], data.get("bard_known_cantrips"))
        _append_many(known["rank_1"], data.get("bard_known_rank_1_spells"))
        _append_many(known["focus"], data.get("bard_focus_spells"))
        _append_unique(pending, data.get("known_spell"))
        _append_unique(pending, data.get("domain_spell"))
        _append_unique(pending, data.get("order_spell"))
        _append_unique(known["focus"], data.get("wizard_focus_spell"))
        bard_setup = data.get("bard_setup")
        if isinstance(bard_setup, dict):
            _append_many(known["cantrip"], bard_setup.get("known_cantrips"))
            _append_many(known["rank_1"], bard_setup.get("known_rank_1_spells"))
            _append_many(known["focus"], bard_setup.get("known_focus_spells"))
            _append_unique(pending, bard_setup.get("muse_granted_rank_1_spell"))
        muse = data.get("bard_muse_choice")
        if isinstance(muse, dict):
            _append_unique(pending, muse.get("known_spell"))
        sorc_setup = data.get("sorcerer_setup")
        if isinstance(sorc_setup, dict):
            _append_many(known["cantrip"], sorc_setup.get("known_cantrips"))
            _append_many(known["rank_1"], sorc_setup.get("known_rank_1_spells"))
            _append_unique(known["focus"], sorc_setup.get("bloodline_initial_focus_spell"))
            _pending_from_dict(sorc_setup.get("bloodline_granted_spells"))
        wiz_setup = data.get("wizard_setup")
        if isinstance(wiz_setup, dict):
            _append_unique(pending, wiz_setup.get("school_bonus_spell"))
            _append_unique(known["focus"], wiz_setup.get("school_focus_spell"))
            setup_spellbook = wiz_setup.get("spellbook")
            if isinstance(setup_spellbook, dict):
                for tier in ("cantrip", "rank_1", "rank_2", "rank_3", "rank_4", "rank_5", "rank_6", "rank_7", "rank_8", "rank_9", "rank_10"):
                    raw = setup_spellbook.get(tier)
                    if tier == "rank_1" and raw is None:
                        raw = setup_spellbook.get("rank1")
                    if tier == "cantrip" and raw is None:
                        raw = setup_spellbook.get("cantrips")
                    _append_many(known[tier], raw)
        druid_setup = data.get("druid_setup")
        if isinstance(druid_setup, dict):
            _append_unique(known["focus"], druid_setup.get("order_spell"))
        _pending_from_dict(data.get("sorcerer_bloodline_granted_spells"))

    for spell_id in list(known["innate"]):
        _append_unique(known["cantrip"], spell_id)

    for spell_id in pending:
        tier = _event_tier(spell_id)
        if tier == "focus":
            _append_unique(known["focus"], spell_id)
        elif tier == "cantrip":
            _append_unique(known["cantrip"], spell_id)
        elif tier == "rank_1":
            _append_unique(known["rank_1"], spell_id)
        elif tier is None:
            _append_unique(known["rank_1"], spell_id)

    champion_setup: dict[str, Any] = {}
    getter = getattr(actor, "get_status_data", None)
    if callable(getter):
        try:
            raw_setup = getter("champion", "champion_setup", {})
            if isinstance(raw_setup, dict):
                champion_setup = dict(raw_setup)
        except Exception:
            champion_setup = {}
    champion_cause = _normalize(
        champion_setup.get("cause")
        or getattr(actor, "champion_cause", "")
        or ""
    )
    class_name = _normalize(getattr(actor, "class_name", ""))
    is_champion = class_name == "champion"
    if not is_champion:
        try:
            is_champion = bool(actor.has_status("champion"))
        except Exception:
            is_champion = False
    if is_champion and champion_cause in {"paladin", "redeemer", "liberator"}:
        _append_unique(known["focus"], "lay_on_hands")

    return known


def _bard_rank1_slots_per_day(actor) -> int:
    try:
        raw = getattr(actor, "bard_rank_1_slots_per_day", None)
        if raw is None:
            raw = getattr(actor, "bard_rank1_slots_per_day", None)
        if raw is not None:
            return max(0, int(raw or 0))
    except Exception:
        pass
    for data in _iter_status_data(actor):
        bard_setup = data.get("bard_setup")
        if isinstance(bard_setup, dict):
            try:
                return max(0, int(bard_setup.get("rank_1_slots_per_day", _BARD_DEFAULT_RANK1_SLOTS_L1) or 0))
            except Exception:
                continue
        try:
            raw = data.get("bard_rank_1_slots_per_day")
            if raw is not None:
                return max(0, int(raw or 0))
        except Exception:
            continue
    return int(_BARD_DEFAULT_RANK1_SLOTS_L1)


def _bard_muse_spell(actor) -> str:
    for data in _iter_status_data(actor):
        muse = data.get("bard_muse_choice")
        if not isinstance(muse, dict):
            continue
        spell_id = _normalize_spell_id(muse.get("known_spell"))
        if spell_id:
            return spell_id
    return ""


def _status_setup_data(actor, *, status_id: str, key: str) -> dict[str, Any]:
    getter = getattr(actor, "get_status_data", None)
    if callable(getter):
        try:
            raw = getter(status_id, key, {})
            if isinstance(raw, dict):
                return dict(raw)
        except Exception:
            pass
    for status in list(getattr(actor, "statuses", []) or []):
        if getattr(status, "id", None) != status_id:
            continue
        data = getattr(status, "data", None) or {}
        setup = data.get(key)
        if isinstance(setup, dict):
            return dict(setup)
    return {}


def _sorcerer_setup_data(actor) -> dict[str, Any]:
    return _status_setup_data(actor, status_id="sorcerer", key="sorcerer_setup")


def _cleric_setup_data(actor) -> dict[str, Any]:
    return _status_setup_data(actor, status_id="cleric", key="cleric_setup")


def _druid_setup_data(actor) -> dict[str, Any]:
    return _status_setup_data(actor, status_id="druid", key="druid_setup")


def _ability_modifier(actor, ability: str) -> int:
    ability_mods = dict(getattr(actor, "ability_modifiers", {}) or {})
    normalized = _normalize(ability)
    if normalized in ability_mods:
        try:
            return int(ability_mods.get(normalized, 0) or 0)
        except Exception:
            return 0
    fallback_attrs = {
        "strength": "str_mod",
        "dexterity": "dex_mod",
        "constitution": "con_mod",
        "intelligence": "int_mod",
        "wisdom": "wis_mod",
        "charisma": "cha_mod",
    }
    attr_name = fallback_attrs.get(normalized)
    if attr_name:
        try:
            return int(getattr(actor, attr_name, 0) or 0)
        except Exception:
            return 0
    return 0


def _sorcerer_rank1_slots_per_day(actor) -> int:
    try:
        raw = getattr(actor, "sorcerer_rank_1_slots_per_day", None)
        if raw is not None:
            return max(0, int(raw or 0))
    except Exception:
        pass
    setup = _sorcerer_setup_data(actor)
    try:
        raw = setup.get("rank_1_slots_per_day")
        if raw is not None:
            return max(0, int(raw or 0))
    except Exception:
        pass
    for data in _iter_status_data(actor):
        try:
            raw = data.get("sorcerer_rank_1_slots_per_day")
            if raw is not None:
                return max(0, int(raw or 0))
        except Exception:
            continue
    return int(_SORCERER_DEFAULT_RANK1_SLOTS_L1)


def _default_sorcerer_slots_for_level(level: int) -> dict[str, int]:
    lvl = max(1, min(20, int(level or 1)))
    slots: dict[str, int] = {"cantrip": 5}
    if lvl >= 19:
        max_rank = 10
    else:
        max_rank = max(1, (lvl + 1) // 2)

    for rank in range(1, max_rank):
        slots[_tier_for_rank(rank)] = 4

    highest_tier = _tier_for_rank(max_rank)
    if max_rank == 1:
        slots[highest_tier] = 3 if lvl == 1 else 4
    elif max_rank == 10 and lvl >= 19:
        slots[highest_tier] = 1
    else:
        slots[highest_tier] = 3 if (lvl % 2 == 1) else 4
    return slots


def _sorcerer_slot_budget_by_tier(actor) -> dict[str, int]:
    level = _actor_level(actor)
    base_slots: dict[str, int] | None = None
    for data in _iter_status_data(actor):
        table = data.get("sorcerer_spells_per_day")
        if not isinstance(table, dict):
            continue
        row = table.get(level)
        if row is None:
            row = table.get(str(level))
        slots = _normalize_slot_budget(row)
        if slots:
            base_slots = slots
            break
    if base_slots is None:
        base_slots = _default_sorcerer_slots_for_level(level)

    # Keep table defaults, but allow explicit slot overrides from setup/runtime attrs.
    slot_budget = dict(base_slots)

    setup = _sorcerer_setup_data(actor)
    for rank in range(1, 11):
        key = f"rank_{rank}_slots_per_day"
        try:
            raw = setup.get(key)
            if raw is not None:
                slot_budget[_tier_for_rank(rank)] = max(0, int(raw or 0))
        except Exception:
            continue

    for data in _iter_status_data(actor):
        for rank in range(1, 11):
            key = f"sorcerer_rank_{rank}_slots_per_day"
            try:
                raw = data.get(key)
                if raw is not None:
                    slot_budget[_tier_for_rank(rank)] = max(0, int(raw or 0))
            except Exception:
                continue

    for rank in range(1, 11):
        key = f"sorcerer_rank_{rank}_slots_per_day"
        try:
            raw = getattr(actor, key, None)
            if raw is not None:
                slot_budget[_tier_for_rank(rank)] = max(0, int(raw or 0))
        except Exception:
            continue
    return slot_budget


def _rank_tiers() -> list[str]:
    return [_tier_for_rank(rank) for rank in range(1, 11)]


def _sorcerer_signature_spells_for_state(actor, state: dict[str, Any]) -> list[str]:
    class_name = _normalize(state.get("class_name") or getattr(actor, "class_name", ""))
    if class_name != "sorcerer":
        return []

    level = _actor_level(actor)
    known = dict(state.get("known", {}) or {})
    slot_budget = _sorcerer_slot_budget_by_tier(actor)
    setup = _sorcerer_setup_data(actor)
    declared: list[str] = []

    def _append_declared(raw_values: object) -> None:
        if isinstance(raw_values, str):
            _append_unique(declared, raw_values)
            return
        if isinstance(raw_values, (list, tuple, set)):
            for raw in raw_values:
                _append_unique(declared, str(raw))

    _append_declared(state.get("sorcerer_signature_spells"))
    _append_declared(getattr(actor, "sorcerer_signature_spells", None))
    _append_declared(setup.get("signature_spells"))
    for data in _iter_status_data(actor):
        _append_declared(data.get("sorcerer_signature_spells"))

    known_any_rank: set[str] = set()
    for tier in _rank_tiers():
        for spell_id in list(known.get(tier, []) or []):
            normalized = _normalize_spell_id(spell_id)
            if normalized:
                known_any_rank.add(normalized)

    # Signature spell must belong to repertoire (any rank).
    filtered_declared: list[str] = []
    for spell_id in declared:
        if spell_id in known_any_rank and spell_id not in filtered_declared:
            filtered_declared.append(spell_id)

    # CRB: signature spells start at level 3+. At level 1-2 keep only explicit choices.
    if level < 3:
        return filtered_declared

    # Ensure at least one signature spell for each rank with slots.
    signatures = list(filtered_declared)
    for tier in _rank_tiers():
        if int(slot_budget.get(tier, 0) or 0) <= 0:
            continue
        tier_known = [
            _normalize_spell_id(spell_id)
            for spell_id in list(known.get(tier, []) or [])
            if _normalize_spell_id(spell_id)
        ]
        if not tier_known:
            continue
        if any(spell_id in signatures for spell_id in tier_known):
            continue
        signatures.append(tier_known[0])
    return signatures


def _sync_sorcerer_signature_spells(actor, state: dict[str, Any]) -> None:
    signatures = _sorcerer_signature_spells_for_state(actor, state)
    state["sorcerer_signature_spells"] = list(signatures)
    try:
        setattr(actor, "sorcerer_signature_spells", list(signatures))
    except Exception:
        pass


def _sorcerer_knows_spell_any_rank(known: dict[str, Any], spell_id: str) -> bool:
    normalized = _normalize_spell_id(spell_id)
    if not normalized:
        return False
    for tier in _rank_tiers():
        tier_known = {
            _normalize_spell_id(item)
            for item in list(known.get(tier, []) or [])
            if _normalize_spell_id(item)
        }
        if normalized in tier_known:
            return True
    return False


def _cleric_tradition(actor) -> str:
    setup = _cleric_setup_data(actor)
    from_setup = _normalize(setup.get("spell_tradition"))
    if from_setup:
        return from_setup
    for data in _iter_status_data(actor):
        maybe = _normalize(data.get("cleric_spell_tradition"))
        if maybe:
            return maybe
    return _CLERIC_DEFAULT_TRADITION


def _druid_tradition(actor) -> str:
    setup = _druid_setup_data(actor)
    from_setup = _normalize(setup.get("spell_tradition"))
    if from_setup:
        return from_setup
    for data in _iter_status_data(actor):
        maybe = _normalize(data.get("druid_spell_tradition"))
        if maybe:
            return maybe
    return _DRUID_DEFAULT_TRADITION


def _cleric_font_spell(actor) -> str:
    setup = _cleric_setup_data(actor)
    font = _normalize(
        setup.get("font")
        or getattr(actor, "cleric_font", "")
    )
    if font == "harm":
        return "harm"
    return "heal"


def _cleric_font_slots(actor) -> int:
    cha_mod = _ability_modifier(actor, "charisma")
    return max(0, 1 + int(cha_mod))


def _default_cleric_slots_for_level(level: int) -> dict[str, int]:
    lvl = max(1, min(20, int(level or 1)))
    slots: dict[str, int] = {"cantrip": 5}
    if lvl >= 19:
        max_rank = 10
    else:
        max_rank = max(1, (lvl + 1) // 2)

    for rank in range(1, max_rank):
        slots[_tier_for_rank(rank)] = 3

    highest_tier = _tier_for_rank(max_rank)
    if max_rank == 1:
        slots[highest_tier] = 2 if lvl == 1 else 3
    elif max_rank == 10 and lvl >= 19:
        slots[highest_tier] = 1
    else:
        slots[highest_tier] = 2 if (lvl % 2 == 1) else 3
    return slots


def _normalize_slot_budget(raw: object) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for key, value in raw.items():
        normalized_key = _normalize_tier(key)
        if not normalized_key:
            if _normalize(key) == "cantrip":
                normalized_key = "cantrip"
            else:
                continue
        try:
            out[normalized_key] = max(0, int(value or 0))
        except Exception:
            continue
    return out


def _cleric_slot_budget_by_tier(actor) -> dict[str, int]:
    level = _actor_level(actor)
    for data in _iter_status_data(actor):
        table = data.get("cleric_spells_per_day")
        if not isinstance(table, dict):
            continue
        row = table.get(level)
        if row is None:
            row = table.get(str(level))
        slots = _normalize_slot_budget(row)
        if slots:
            return slots
    return _default_cleric_slots_for_level(level)


def _highest_rank_tier_with_slots(slot_budget: dict[str, int]) -> str:
    highest = "rank_1"
    for rank in range(1, 11):
        tier = _tier_for_rank(rank)
        if int(slot_budget.get(tier, 0) or 0) > 0:
            highest = tier
    return highest


def _druid_slot_budget_by_tier(actor) -> dict[str, int]:
    level = _actor_level(actor)
    for data in _iter_status_data(actor):
        table = data.get("druid_spells_per_day")
        if not isinstance(table, dict):
            continue
        row = table.get(level)
        if row is None:
            row = table.get(str(level))
        slots = _normalize_slot_budget(row)
        if slots:
            return slots
    return _default_cleric_slots_for_level(level)


def _default_wizard_slots_for_level(level: int) -> dict[str, int]:
    return _default_cleric_slots_for_level(level)


def _wizard_slot_budget_by_tier(actor) -> dict[str, int]:
    level = _actor_level(actor)
    for data in _iter_status_data(actor):
        table = data.get("wizard_spells_per_day")
        if not isinstance(table, dict):
            continue
        row = table.get(level)
        if row is None:
            row = table.get(str(level))
        slots = _normalize_slot_budget(row)
        if slots:
            return slots
    return _default_wizard_slots_for_level(level)


def _cleric_cantrip_prepared_count(actor) -> int:
    try:
        raw = getattr(actor, "cleric_prepared_cantrips", None)
        if raw is not None:
            return max(0, int(raw or 0))
    except Exception:
        pass
    for data in _iter_status_data(actor):
        try:
            raw = data.get("cleric_prepared_cantrips_at_level1")
            if raw is not None:
                return max(0, int(raw or 0))
        except Exception:
            continue
    slots = _cleric_slot_budget_by_tier(actor)
    return int(slots.get("cantrip", _CLERIC_DEFAULT_CANTRIP_PREPARED_L1) or _CLERIC_DEFAULT_CANTRIP_PREPARED_L1)


def _cleric_rank1_slots(actor) -> int:
    try:
        raw = getattr(actor, "cleric_prepared_rank_1_slots", None)
        if raw is not None:
            return max(0, int(raw or 0))
    except Exception:
        pass
    for data in _iter_status_data(actor):
        try:
            raw = data.get("cleric_prepared_rank_1_slots_at_level1")
            if raw is not None:
                return max(0, int(raw or 0))
        except Exception:
            continue
    slots = _cleric_slot_budget_by_tier(actor)
    return int(slots.get("rank_1", _CLERIC_DEFAULT_RANK1_SLOTS_L1) or _CLERIC_DEFAULT_RANK1_SLOTS_L1)


def _druid_cantrip_prepared_count(actor) -> int:
    try:
        raw = getattr(actor, "druid_prepared_cantrips", None)
        if raw is not None:
            return max(0, int(raw or 0))
    except Exception:
        pass
    for data in _iter_status_data(actor):
        try:
            raw = data.get("druid_prepared_cantrips_at_level1")
            if raw is not None:
                return max(0, int(raw or 0))
        except Exception:
            continue
    slots = _druid_slot_budget_by_tier(actor)
    return int(slots.get("cantrip", _DRUID_DEFAULT_CANTRIP_PREPARED_L1) or _DRUID_DEFAULT_CANTRIP_PREPARED_L1)


def _druid_rank1_slots(actor) -> int:
    try:
        raw = getattr(actor, "druid_prepared_rank_1_slots", None)
        if raw is not None:
            return max(0, int(raw or 0))
    except Exception:
        pass
    for data in _iter_status_data(actor):
        try:
            raw = data.get("druid_prepared_rank_1_slots_at_level1")
            if raw is not None:
                return max(0, int(raw or 0))
        except Exception:
            continue
    slots = _druid_slot_budget_by_tier(actor)
    return int(slots.get("rank_1", _DRUID_DEFAULT_RANK1_SLOTS_L1) or _DRUID_DEFAULT_RANK1_SLOTS_L1)


def _ensure_bard_baseline_known(actor, known: dict[str, list[str]]) -> None:
    cantrips = list(known.get("cantrip", []) or [])
    rank1 = list(known.get("rank_1", []) or [])
    focus = list(known.get("focus", []) or [])

    tradition = _BARD_DEFAULT_TRADITION
    for data in _iter_status_data(actor):
        bard_setup = data.get("bard_setup")
        if isinstance(bard_setup, dict):
            maybe_tradition = _normalize(bard_setup.get("spell_tradition"))
            if maybe_tradition:
                tradition = maybe_tradition
                break
        maybe_tradition = _normalize(data.get("bard_spell_tradition"))
        if maybe_tradition:
            tradition = maybe_tradition
            break

    cantrip_pool = _collect_spells_for_tier_and_tradition(tier="cantrip", traditions={tradition})
    rank1_pool = _collect_spells_for_tier_and_tradition(tier="rank_1", traditions={tradition})

    for spell_id in cantrip_pool:
        if len(cantrips) >= int(_BARD_DEFAULT_CANTRIP_COUNT_L1):
            break
        _append_unique(cantrips, spell_id)
    for spell_id in rank1_pool:
        if len(rank1) >= int(_BARD_DEFAULT_RANK1_COUNT_L1):
            break
        _append_unique(rank1, spell_id)

    muse_spell = _bard_muse_spell(actor)
    if muse_spell and muse_spell in rank1_pool:
        if muse_spell not in rank1:
            if len(rank1) >= int(_BARD_DEFAULT_RANK1_COUNT_L1) and rank1:
                rank1[-1] = muse_spell
            else:
                rank1.append(muse_spell)

    for spell_id in _BARD_BONUS_CANTRIPS:
        _append_unique(cantrips, spell_id)
    for spell_id in _BARD_BONUS_FOCUS:
        _append_unique(focus, spell_id)

    known["cantrip"] = list(cantrips)
    known["rank_1"] = list(rank1)
    known["focus"] = list(focus)


def _ensure_sorcerer_baseline_known(actor, known: dict[str, list[str]]) -> None:
    cantrips = list(known.get("cantrip", []) or [])

    setup = _sorcerer_setup_data(actor)
    tradition = _normalize(setup.get("spell_tradition") or getattr(actor, "sorcerer_spell_tradition", ""))
    if not tradition:
        tradition = "arcane"
    slot_budget = _sorcerer_slot_budget_by_tier(actor)
    cantrip_pool = _collect_spells_for_tier_and_tradition(tier="cantrip", traditions={tradition})
    cantrip_target = max(
        0,
        int(slot_budget.get("cantrip", _SORCERER_DEFAULT_CANTRIP_COUNT_L1) or _SORCERER_DEFAULT_CANTRIP_COUNT_L1),
    )
    for spell_id in cantrip_pool:
        if len(cantrips) >= cantrip_target:
            break
        _append_unique(cantrips, spell_id)
    bloodline_cantrip = _normalize_spell_id(
        setup.get("bloodline_cantrip") or getattr(actor, "sorcerer_bloodline_cantrip", "")
    )
    bloodline_spells = dict(
        setup.get("bloodline_granted_spells")
        or getattr(actor, "sorcerer_bloodline_granted_spells", {})
        or {}
    )
    if bloodline_cantrip:
        _append_unique(cantrips, bloodline_cantrip)
    known["cantrip"] = list(cantrips)

    for rank in range(1, 11):
        tier = _tier_for_rank(rank)
        target_known = max(0, int(slot_budget.get(tier, 0) or 0))
        tier_known = list(known.get(tier, []) or [])
        granted_spell = _normalize_spell_id(bloodline_spells.get(tier))
        if granted_spell:
            _append_unique(tier_known, granted_spell)
        tier_pool = _collect_spells_for_tier_and_tradition(tier=tier, traditions={tradition})
        for spell_id in tier_pool:
            if len(tier_known) >= target_known:
                break
            _append_unique(tier_known, spell_id)
        known[tier] = list(tier_known)


def _ensure_cleric_baseline_known(actor, known: dict[str, list[str]]) -> None:
    tradition = _cleric_tradition(actor)
    cantrip_pool = _collect_spells_for_tier_and_tradition(tier="cantrip", traditions={tradition})
    cantrips = list(known.get("cantrip", []) or [])
    for spell_id in cantrip_pool:
        _append_unique(cantrips, spell_id)
    known["cantrip"] = list(cantrips)
    for rank in range(1, 11):
        tier = _tier_for_rank(rank)
        pool = _collect_spells_for_tier_and_tradition(tier=tier, traditions={tradition})
        tier_known = list(known.get(tier, []) or [])
        for spell_id in pool:
            _append_unique(tier_known, spell_id)
        known[tier] = list(tier_known)


def _ensure_druid_baseline_known(actor, known: dict[str, list[str]]) -> None:
    tradition = _druid_tradition(actor)
    cantrip_pool = _collect_spells_for_tier_and_tradition(tier="cantrip", traditions={tradition})
    cantrips = list(known.get("cantrip", []) or [])
    for spell_id in cantrip_pool:
        _append_unique(cantrips, spell_id)
    known["cantrip"] = list(cantrips)
    for rank in range(1, 11):
        tier = _tier_for_rank(rank)
        pool = _collect_spells_for_tier_and_tradition(tier=tier, traditions={tradition})
        tier_known = list(known.get(tier, []) or [])
        for spell_id in pool:
            _append_unique(tier_known, spell_id)
        known[tier] = list(tier_known)


def _ui_enabled(game) -> bool:
    ui = getattr(game, "ui", None)
    return bool(ui is not None and getattr(ui, "enabled", False))


def _decode_selection(answer: str | None, options: list[str]) -> str | None:
    raw = str(answer or "").strip()
    if not raw:
        return None
    low = _normalize(raw)
    if low in {"done", "end", "cancel"}:
        return "done"
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            return options[idx]
    for option in options:
        if low == _normalize(option):
            return option
    for option in options:
        if low == _normalize(_labelize(option)):
            return option
    return None


def _auto_pick(choices: list[str], count: int, *, allow_duplicates: bool) -> list[str]:
    if count <= 0 or not choices:
        return []
    if allow_duplicates:
        return [choices[idx % len(choices)] for idx in range(count)]
    return list(choices[: min(count, len(choices))])


def _build_spell_choice_meta(spell_ids: list[str]) -> list[dict[str, str]]:
    """Build choice_meta entries with localized labels and structured descriptions for spell selection UI."""
    try:
        from localization import localize_term_pl, localized_hint_pl
    except Exception:
        return []
    out: list[dict[str, str]] = []
    for spell_id in spell_ids:
        label = str(localize_term_pl(spell_id) or _labelize(spell_id)).strip()
        hint = str(localized_hint_pl(spell_id) or "").strip()
        event_cls = _event_cls_for_spell(spell_id)
        tags = _event_tags(spell_id)
        if "cantrip" in tags:
            tier_label = "Cantrip"
        elif "focus" in tags:
            tier_label = "Focus"
        else:
            tier_label = ""
            for tag in sorted(tags):
                if tag.startswith("rank_"):
                    try:
                        num = int(tag[len("rank_"):])
                        tier_label = f"Ranga {num}"
                        break
                    except ValueError:
                        pass
        fluff_suffix = f" ({tier_label})" if tier_label else ""
        # Use hint from localization; if missing, auto-generate from event class attributes.
        efekt = hint or _auto_spell_desc(event_cls) or "brak opisu mechaniki"
        desc = f"Fluff: {label}{fluff_suffix}\nMechanika:\n- Kiedy: Wybierz do przygotowania.\n- Efekt: {efekt}"
        out.append({"raw": spell_id, "label": label, "desc": desc})
    return out


def _pick_spells(
    game,
    *,
    title: str,
    source: str,
    choices: list[str],
    count: int,
    allow_duplicates: bool,
    prompt: bool,
) -> list[str]:
    normalized_choices = [item for item in (_normalize(choice) for choice in choices) if item]
    if count <= 0 or not normalized_choices:
        return []
    if not prompt or not _ui_enabled(game):
        return _auto_pick(normalized_choices, count, allow_duplicates=allow_duplicates)

    ui = getattr(game, "ui", None)
    chooser = getattr(ui, "prompt_choice", None)
    if not callable(chooser):
        return _auto_pick(normalized_choices, count, allow_duplicates=allow_duplicates)

    selected: list[str] = []
    while len(selected) < count:
        selectable = list(normalized_choices) if allow_duplicates else [item for item in normalized_choices if item not in selected]
        if not selectable:
            break
        spell_meta = _build_spell_choice_meta(selectable)
        if spell_meta:
            done_entry: dict[str, str] = {"raw": "Done", "label": "Gotowe ✓", "desc": ""}
            choice_meta = spell_meta + [done_entry]
            display_choices = [entry["label"] for entry in spell_meta] + ["Done"]
            answer = chooser(
                f"{title} ({len(selected) + 1}/{count})",
                choices=display_choices,
                source=source,
                choice_meta=choice_meta,
            )
        else:
            display_choices = [_labelize(item) for item in selectable] + ["Done"]
            answer = chooser(
                f"{title} ({len(selected) + 1}/{count})",
                choices=display_choices,
                source=source,
            )
        decoded = _decode_selection(str(answer or ""), selectable)
        if decoded == "done":
            break
        if decoded is None:
            break
        selected.append(decoded)

    if not selected:
        return _auto_pick(normalized_choices, count, allow_duplicates=allow_duplicates)
    if allow_duplicates and len(selected) < count:
        selected.extend(_auto_pick(selected or normalized_choices, count - len(selected), allow_duplicates=True))
    return selected


def _menu_pick(
    game,
    *,
    title: str,
    source: str,
    choices: list[dict[str, str]],
    prompt: bool,
) -> str | None:
    if not prompt or not _ui_enabled(game) or not choices:
        return None
    ui = getattr(game, "ui", None)
    chooser = getattr(ui, "prompt_choice", None)
    if not callable(chooser):
        return None
    display_labels = [str(item.get("label") or "").strip() for item in choices]
    display_labels.append("Done")
    try:
        answer = chooser(title, choices=display_labels, source=source)
    except Exception:
        return None
    raw = str(answer or "").strip()
    if not raw:
        return None
    low = _normalize(raw)
    if low in {"done", "end", "cancel"}:
        return None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(choices):
            return str(choices[idx].get("id") or "").strip() or None
        return None
    for item in choices:
        item_id = str(item.get("id") or "").strip()
        label = str(item.get("label") or "").strip()
        if low == _normalize(item_id) or low == _normalize(label):
            return item_id or None
    return None


def _wizard_apply_spell_blending(
    actor,
    game,
    *,
    setup: dict[str, Any],
    slot_budget: dict[str, int],
    prompt: bool,
) -> tuple[dict[str, int], int, dict[str, Any]]:
    thesis = _normalize(setup.get("thesis") or getattr(actor, "wizard_thesis", ""))
    if thesis != "spell_blending":
        return dict(slot_budget), 0, {"enabled": False}

    mutable_slots: dict[int, int] = {
        rank: max(0, int(slot_budget.get(_tier_for_rank(rank), 0) or 0))
        for rank in range(1, 11)
    }
    max_castable_rank = max((rank for rank, value in mutable_slots.items() if int(value or 0) > 0), default=1)
    bonus_levels_used: set[int] = set()
    blend_ops: list[dict[str, int]] = []
    cantrip_trade_ranks: list[int] = []
    extra_cantrips = 0

    while True:
        options: list[dict[str, str]] = []
        for source_rank in range(1, max_castable_rank + 1):
            if int(mutable_slots.get(source_rank, 0) or 0) < 2:
                continue
            for target_rank in (source_rank + 1, source_rank + 2):
                if target_rank > max_castable_rank:
                    continue
                if target_rank in bonus_levels_used:
                    continue
                opt_id = f"blend:{source_rank}:{target_rank}"
                options.append(
                    {
                        "id": opt_id,
                        "label": (
                            f"2x ranga {source_rank} -> +1 slot ranga {target_rank} "
                            "(Spell Blending)"
                        ),
                    }
                )
        for source_rank in range(1, max_castable_rank + 1):
            if int(mutable_slots.get(source_rank, 0) or 0) < 1:
                continue
            opt_id = f"cantrip:{source_rank}"
            options.append(
                {
                    "id": opt_id,
                    "label": f"1x ranga {source_rank} -> +2 cantripy",
                }
            )

        if not options:
            break

        selected = _menu_pick(
            game,
            title="Wizard (Spell Blending): wybierz wymiane slotow",
            source="spell_prepare",
            choices=options,
            prompt=prompt,
        )
        if not selected:
            break
        parts = str(selected).split(":")
        if len(parts) < 2:
            break
        kind = _normalize(parts[0])
        if kind == "blend" and len(parts) == 3:
            try:
                source_rank = max(1, int(parts[1]))
                target_rank = max(1, int(parts[2]))
            except Exception:
                continue
            if int(mutable_slots.get(source_rank, 0) or 0) < 2:
                continue
            if target_rank > max_castable_rank:
                continue
            if target_rank in bonus_levels_used:
                continue
            mutable_slots[source_rank] = max(0, int(mutable_slots.get(source_rank, 0) or 0) - 2)
            mutable_slots[target_rank] = max(0, int(mutable_slots.get(target_rank, 0) or 0) + 1)
            bonus_levels_used.add(target_rank)
            blend_ops.append({"source_rank": source_rank, "target_rank": target_rank})
            continue
        if kind == "cantrip" and len(parts) == 2:
            try:
                source_rank = max(1, int(parts[1]))
            except Exception:
                continue
            if int(mutable_slots.get(source_rank, 0) or 0) < 1:
                continue
            mutable_slots[source_rank] = max(0, int(mutable_slots.get(source_rank, 0) or 0) - 1)
            extra_cantrips += 2
            cantrip_trade_ranks.append(source_rank)
            continue

    out_budget = dict(slot_budget)
    for rank in range(1, 11):
        out_budget[_tier_for_rank(rank)] = max(0, int(mutable_slots.get(rank, 0) or 0))

    payload = {
        "enabled": True,
        "blends": list(blend_ops),
        "cantrip_trades": list(cantrip_trade_ranks),
        "extra_cantrips": int(max(0, extra_cantrips)),
    }
    if hasattr(game, "ui_log") and (blend_ops or cantrip_trade_ranks):
        blend_desc = ", ".join(
            [f"2xR{int(item.get('source_rank', 0) or 0)}->R{int(item.get('target_rank', 0) or 0)}" for item in blend_ops]
        ) or "-"
        cantrip_desc = ", ".join([f"R{rank}" for rank in cantrip_trade_ranks]) or "-"
        try:
            game.ui_log(
                "Wizard Spell Blending: "
                f"blendy={blend_desc}; cantrip-trade={cantrip_desc}; bonus cantripy=+{int(max(0, extra_cantrips))}."
            )
        except Exception:
            pass
    return out_budget, int(max(0, extra_cantrips)), payload


def _wizard_setup_data(actor) -> dict[str, Any]:
    getter = getattr(actor, "get_status_data", None)
    if callable(getter):
        try:
            setup = getter("wizard", "wizard_setup", {})
            if isinstance(setup, dict):
                return dict(setup)
        except Exception:
            pass
    for status in list(getattr(actor, "statuses", []) or []):
        if getattr(status, "id", None) != "wizard":
            continue
        data = getattr(status, "data", None) or {}
        setup = data.get("wizard_setup")
        if isinstance(setup, dict):
            return dict(setup)
    return {}


def _normalize_staff_nexus_state(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"enabled": False}
    cantrip_spell = _normalize_spell_id(raw.get("cantrip_spell"))
    rank1_spell = _normalize_spell_id(raw.get("rank_1_spell"))
    try:
        charges_total = max(0, int(raw.get("charges_total", 0) or 0))
    except Exception:
        charges_total = 0
    try:
        charges_remaining = max(0, int(raw.get("charges_remaining", charges_total) or 0))
    except Exception:
        charges_remaining = charges_total
    try:
        base_charges = max(0, int(raw.get("base_charges", 0) or 0))
    except Exception:
        base_charges = 0
    extra_charge_ranks: list[int] = []
    for value in list(raw.get("extra_charge_ranks", []) or []):
        try:
            rank = max(1, int(value or 0))
        except Exception:
            continue
        extra_charge_ranks.append(rank)
    try:
        max_extra_spells = max(0, int(raw.get("max_extra_spells", 0) or 0))
    except Exception:
        max_extra_spells = 0
    enabled = bool(raw.get("enabled")) and bool(cantrip_spell or rank1_spell)
    return {
        "enabled": enabled,
        "cantrip_spell": cantrip_spell,
        "rank_1_spell": rank1_spell,
        "charges_total": charges_total,
        "charges_remaining": min(charges_total, charges_remaining),
        "base_charges": base_charges,
        "extra_charge_ranks": list(extra_charge_ranks),
        "max_extra_spells": max_extra_spells,
    }


def _staff_nexus_extra_spell_limit(actor) -> int:
    level = _actor_level(actor)
    if level >= 16:
        return 3
    if level >= 8:
        return 2
    return 1


def _wizard_staff_nexus_options(actor, *, spell_id: str, tier: str | None) -> dict[str, Any]:
    state = dict(getattr(actor, "spell_state", {}) or {})
    class_name = _normalize(state.get("class_name") or getattr(actor, "class_name", ""))
    if class_name != "wizard":
        return {"available": False}
    setup = _wizard_setup_data(actor)
    thesis = _normalize(setup.get("thesis") or getattr(actor, "wizard_thesis", ""))
    if thesis != "staff_nexus":
        return {"available": False}

    payload = _normalize_staff_nexus_state(state.get("wizard_staff_nexus"))
    if not bool(payload.get("enabled")):
        return {"available": False}

    normalized_spell = _normalize_spell_id(spell_id)
    normalized_tier = _normalize_tier(tier)
    if not normalized_spell or not normalized_tier:
        return {"available": False}

    cantrip_spell = str(payload.get("cantrip_spell") or "")
    rank1_spell = str(payload.get("rank_1_spell") or "")
    charges_remaining = int(payload.get("charges_remaining", 0) or 0)

    if normalized_tier == "cantrip" and normalized_spell == cantrip_spell:
        return {
            "available": True,
            "source": "staff_nexus",
            "requires_charge": False,
            "charges_remaining": charges_remaining,
            "spell_id": cantrip_spell,
            "tier": "cantrip",
        }
    if normalized_tier == "rank_1" and normalized_spell == rank1_spell and charges_remaining > 0:
        return {
            "available": True,
            "source": "staff_nexus",
            "requires_charge": True,
            "charges_remaining": charges_remaining,
            "spell_id": rank1_spell,
            "tier": "rank_1",
        }
    return {"available": False}


def consume_wizard_staff_nexus_resources(actor, *, spell_id: str, tier: str | None) -> None:
    state = dict(getattr(actor, "spell_state", {}) or {})
    payload = _normalize_staff_nexus_state(state.get("wizard_staff_nexus"))
    if not bool(payload.get("enabled")):
        return

    options = _wizard_staff_nexus_options(actor, spell_id=spell_id, tier=tier)
    if not bool(options.get("available")):
        return
    if not bool(options.get("requires_charge")):
        return

    current_remaining = int(payload.get("charges_remaining", 0) or 0)
    payload["charges_remaining"] = max(0, current_remaining - 1)
    state["wizard_staff_nexus"] = dict(payload)
    try:
        setattr(actor, "spell_state", state)
    except Exception:
        pass
    try:
        setattr(actor, "wizard_staff_nexus", dict(payload))
        setattr(actor, "wizard_staff_nexus_charges_remaining", int(payload.get("charges_remaining", 0) or 0))
        setattr(actor, "wizard_staff_nexus_charges_total", int(payload.get("charges_total", 0) or 0))
    except Exception:
        pass


def _wizard_apply_staff_nexus(
    actor,
    game,
    *,
    setup: dict[str, Any],
    slot_budget: dict[str, int],
    prompt: bool,
) -> tuple[dict[str, int], dict[str, Any]]:
    thesis = _normalize(setup.get("thesis") or getattr(actor, "wizard_thesis", ""))
    if thesis != "staff_nexus":
        return dict(slot_budget), {"enabled": False}

    cantrip_spell = _normalize_spell_id(
        setup.get("staff_nexus_cantrip")
        or setup.get("wizard_staff_nexus_cantrip")
        or getattr(actor, "wizard_staff_nexus_cantrip", "")
    )
    rank1_spell = _normalize_spell_id(
        setup.get("staff_nexus_rank_1_spell")
        or setup.get("wizard_staff_nexus_rank_1_spell")
        or getattr(actor, "wizard_staff_nexus_rank_1_spell", "")
    )
    if not cantrip_spell and not rank1_spell:
        return dict(slot_budget), {"enabled": False}

    mutable_budget = dict(slot_budget)
    highest_rank = max(
        (rank for rank in range(1, 11) if int(mutable_budget.get(_tier_for_rank(rank), 0) or 0) > 0),
        default=0,
    )
    max_extra_spells = _staff_nexus_extra_spell_limit(actor)
    extra_charge_ranks: list[int] = []

    for _ in range(max_extra_spells):
        options: list[dict[str, str]] = []
        for rank in range(1, 11):
            tier = _tier_for_rank(rank)
            if int(mutable_budget.get(tier, 0) or 0) <= 0:
                continue
            options.append(
                {
                    "id": f"staff_charge:{rank}",
                    "label": f"Ranga {rank} -> +{rank} ladunkow Staff Nexus",
                }
            )
        if not options:
            break

        selected = _menu_pick(
            game,
            title="Wizard (Staff Nexus): poświęć slot na dodatkowe ładunki kostura",
            source="spell_prepare",
            choices=options,
            prompt=prompt,
        )
        if not selected:
            break
        parts = str(selected).split(":")
        if len(parts) != 2 or _normalize(parts[0]) != "staff_charge":
            break
        try:
            rank = max(1, int(parts[1]))
        except Exception:
            continue
        tier = _tier_for_rank(rank)
        if int(mutable_budget.get(tier, 0) or 0) <= 0:
            continue
        mutable_budget[tier] = max(0, int(mutable_budget.get(tier, 0) or 0) - 1)
        extra_charge_ranks.append(rank)

    charges_total = max(0, int(highest_rank)) + sum(int(rank) for rank in extra_charge_ranks)
    payload = {
        "enabled": True,
        "cantrip_spell": cantrip_spell,
        "rank_1_spell": rank1_spell,
        "base_charges": max(0, int(highest_rank)),
        "charges_total": max(0, int(charges_total)),
        "charges_remaining": max(0, int(charges_total)),
        "extra_charge_ranks": list(extra_charge_ranks),
        "max_extra_spells": max_extra_spells,
    }

    if hasattr(game, "ui_log"):
        try:
            extra_desc = ", ".join([f"R{rank}" for rank in extra_charge_ranks]) or "-"
            game.ui_log(
                "Wizard Staff Nexus: "
                f"cantrip={_labelize(cantrip_spell)}, rank1={_labelize(rank1_spell)}, "
                f"ladunki={int(payload['charges_total'])} (bazowe {int(payload['base_charges'])}, dodatkowe: {extra_desc})."
            )
        except Exception:
            pass
    return mutable_budget, payload


def _wizard_prepare_today(state: dict[str, Any], actor, game, *, prompt: bool) -> None:
    setup = _wizard_setup_data(actor)
    slot_budget = _wizard_slot_budget_by_tier(actor)
    chosen_school = _normalize(
        setup.get("school")
        or setup.get("wizard_school")
        or getattr(actor, "wizard_school", "")
        or ""
    )
    is_specialist = bool(chosen_school and chosen_school != "universalist")
    raw_specialist_slot_flag = (
        setup.get("specialist_bonus_slot_per_rank")
        if setup.get("specialist_bonus_slot_per_rank") is not None
        else setup.get("specialist_bonus_rank1_slot")
    )
    specialist_slot_enabled = bool(raw_specialist_slot_flag) if raw_specialist_slot_flag is not None else True
    try:
        specialist_bonus_cantrip = int(
            setup.get("specialist_bonus_cantrip")
            if setup.get("specialist_bonus_cantrip") is not None
            else 1
        )
    except Exception:
        specialist_bonus_cantrip = 1

    blended_budget, blend_extra_cantrips, blend_payload = _wizard_apply_spell_blending(
        actor,
        game,
        setup=setup,
        slot_budget=slot_budget,
        prompt=prompt,
    )
    slot_budget = dict(blended_budget)
    state["wizard_spell_blending"] = dict(blend_payload)
    try:
        setattr(actor, "wizard_spell_blending", dict(blend_payload))
    except Exception:
        pass

    staff_budget, staff_payload = _wizard_apply_staff_nexus(
        actor,
        game,
        setup=setup,
        slot_budget=slot_budget,
        prompt=prompt,
    )
    slot_budget = dict(staff_budget)
    state["wizard_staff_nexus"] = dict(staff_payload)
    try:
        setattr(actor, "wizard_staff_nexus", dict(staff_payload))
        setattr(actor, "wizard_staff_nexus_charges_total", int(staff_payload.get("charges_total", 0) or 0))
        setattr(actor, "wizard_staff_nexus_charges_remaining", int(staff_payload.get("charges_remaining", 0) or 0))
    except Exception:
        pass

    cantrip_budget = int(slot_budget.get("cantrip", 0) or 0) + int(max(0, blend_extra_cantrips))
    if is_specialist:
        cantrip_budget += max(0, int(specialist_bonus_cantrip))

    known = state.get("known", {})
    known_cantrips = list(known.get("cantrip", []) or [])
    prepared_cantrips = _pick_spells(
        game,
        title="Czarodziej — Przygotuj cantrip (slot)",
        source="spell_prepare",
        choices=known_cantrips,
        count=max(0, int(cantrip_budget)),
        allow_duplicates=False,
        prompt=prompt,
    )

    prepared_today = state.setdefault("prepared_today", {})
    prepared_today["cantrip"] = list(prepared_cantrips)
    slot_total = state.setdefault("slot_total", {})
    slot_total["cantrip"] = max(0, int(cantrip_budget))
    slot_remaining = state.setdefault("slot_remaining", {})
    slot_remaining["cantrip"] = max(0, int(cantrip_budget))
    prepared_counts = state.setdefault("prepared_counts", {})
    prepared_counts["cantrip"] = {spell_id: 1 for spell_id in prepared_cantrips}
    consumed_counts = state.setdefault("consumed_counts", {})
    consumed_counts["cantrip"] = {}

    for rank in range(1, 11):
        tier = _tier_for_rank(rank)
        known_rank_spells = list(known.get(tier, []) or [])
        base_slots = max(0, int(slot_budget.get(tier, 0) or 0))
        bonus_slots = 1 if (is_specialist and specialist_slot_enabled and base_slots > 0) else 0

        _tier_display = tier.replace("rank_", "Ranga ").replace("_", " ").title()
        prepared_base = _pick_spells(
            game,
            title=f"Czarodziej — Przygotuj czar ({_tier_display}, slot)",
            source="spell_prepare",
            choices=known_rank_spells,
            count=base_slots,
            allow_duplicates=True,
            prompt=prompt,
        )

        prepared_bonus: list[str] = []
        if bonus_slots > 0:
            school_choices = [
                spell_id
                for spell_id in known_rank_spells
                if chosen_school in _event_tags(spell_id)
            ]
            prepared_bonus = _pick_spells(
                game,
                title=(
                    f"Czarodziej (Specjalista) — Przygotuj czar ({_tier_display}, {chosen_school}, slot)"
                ),
                source="spell_prepare",
                choices=school_choices,
                count=bonus_slots,
                allow_duplicates=True,
                prompt=prompt,
            )

        prepared_rank_spells = list(prepared_base) + list(prepared_bonus)
        prepared_today[tier] = list(prepared_rank_spells)
        slot_total[tier] = max(0, int(base_slots + bonus_slots))
        slot_remaining[tier] = max(0, int(base_slots + bonus_slots))
        tier_counts: dict[str, int] = {}
        for spell_id in prepared_rank_spells:
            sid = _normalize_spell_id(spell_id)
            if not sid:
                continue
            tier_counts[sid] = int(tier_counts.get(sid, 0) or 0) + 1
        prepared_counts[tier] = tier_counts
        consumed_counts[tier] = {}

    try:
        setattr(actor, "wizard_prepared_today_cantrips", list(prepared_cantrips))
        setattr(actor, "wizard_prepared_today_rank1_spells", list(prepared_today.get("rank_1", []) or []))
        setattr(actor, "wizard_prepared_rank1_slots_remaining", int(slot_remaining.get("rank_1", 0) or 0))
        for rank in range(2, 11):
            tier = _tier_for_rank(rank)
            setattr(actor, f"wizard_prepared_{tier}_slots_remaining", int(slot_remaining.get(tier, 0) or 0))
    except Exception:
        pass


def _bard_prepare_today(state: dict[str, Any], actor) -> None:
    known = state.get("known", {})
    cantrips = list(known.get("cantrip", []) or [])
    rank1 = list(known.get("rank_1", []) or [])
    slots = max(0, int(_bard_rank1_slots_per_day(actor)))

    prepared_today = state.setdefault("prepared_today", {})
    prepared_today["cantrip"] = list(cantrips)
    prepared_today["rank_1"] = list(rank1)

    slot_total = state.setdefault("slot_total", {})
    slot_total["rank_1"] = slots
    slot_remaining = state.setdefault("slot_remaining", {})
    slot_remaining["rank_1"] = slots

    try:
        setattr(actor, "bard_rank_1_slots_remaining", int(slots))
    except Exception:
        pass


def _sorcerer_prepare_today(state: dict[str, Any], actor) -> None:
    known = state.get("known", {})
    cantrips = list(known.get("cantrip", []) or [])
    slot_budget = _sorcerer_slot_budget_by_tier(actor)

    prepared_today = state.setdefault("prepared_today", {})
    prepared_today["cantrip"] = list(cantrips)
    slot_total = state.setdefault("slot_total", {})
    slot_remaining = state.setdefault("slot_remaining", {})
    slot_total["cantrip"] = max(
        0,
        int(slot_budget.get("cantrip", _SORCERER_DEFAULT_CANTRIP_COUNT_L1) or _SORCERER_DEFAULT_CANTRIP_COUNT_L1),
    )
    slot_remaining["cantrip"] = int(slot_total.get("cantrip", 0) or 0)

    for rank in range(1, 11):
        tier = _tier_for_rank(rank)
        known_tier = list(known.get(tier, []) or [])
        prepared_today[tier] = list(known_tier)
        tier_slots = max(0, int(slot_budget.get(tier, 0) or 0))
        slot_total[tier] = tier_slots
        slot_remaining[tier] = tier_slots

    try:
        setattr(actor, "sorcerer_rank_1_slots_remaining", int(slot_remaining.get("rank_1", 0) or 0))
        for rank in range(2, 11):
            tier = _tier_for_rank(rank)
            setattr(actor, f"sorcerer_{tier}_slots_remaining", int(slot_remaining.get(tier, 0) or 0))
    except Exception:
        pass


def _cleric_prepare_today(state: dict[str, Any], actor, game, *, prompt: bool) -> None:
    known = state.get("known", {})
    known_cantrips = list(known.get("cantrip", []) or [])
    slot_budget = _cleric_slot_budget_by_tier(actor)
    cantrip_budget = int(_cleric_cantrip_prepared_count(actor))
    font_slots = int(_cleric_font_slots(actor))
    font_spell = _cleric_font_spell(actor)
    font_tier = _highest_rank_tier_with_slots(slot_budget)

    prepared_cantrips = _pick_spells(
        game,
        title="Kleryk — Przygotuj cantrip (slot)",
        source="spell_prepare",
        choices=known_cantrips,
        count=cantrip_budget,
        allow_duplicates=False,
        prompt=prompt,
    )

    prepared_today = state.setdefault("prepared_today", {})
    prepared_today["cantrip"] = list(prepared_cantrips)
    slot_total = state.setdefault("slot_total", {})
    slot_remaining = state.setdefault("slot_remaining", {})
    prepared_counts = state.setdefault("prepared_counts", {})
    consumed_counts = state.setdefault("consumed_counts", {})

    for rank in range(1, 11):
        tier = _tier_for_rank(rank)
        tier_slots = int(slot_budget.get(tier, 0) or 0)
        tier_known = list(known.get(tier, []) or [])
        _tier_display = tier.replace("rank_", "Ranga ").replace("_", " ").title()
        prepared_spells = _pick_spells(
            game,
            title=f"Kleryk — Przygotuj czar ({_tier_display}, slot)",
            source="spell_prepare",
            choices=tier_known,
            count=tier_slots,
            allow_duplicates=True,
            prompt=prompt,
        )
        prepared_today[tier] = list(prepared_spells)
        slot_total[tier] = max(0, int(tier_slots))
        slot_remaining[tier] = max(0, int(tier_slots))

        counts: dict[str, int] = {}
        for spell_id in prepared_spells:
            sid = _normalize_spell_id(spell_id)
            if not sid:
                continue
            counts[sid] = int(counts.get(sid, 0) or 0) + 1
        prepared_counts[tier] = counts
        consumed_counts[tier] = {}

    if font_spell and font_slots > 0:
        font_prepared = list(prepared_today.get(font_tier, []) or [])
        font_prepared.extend([font_spell for _ in range(font_slots)])
        prepared_today[font_tier] = font_prepared
        slot_total[font_tier] = max(0, int(slot_total.get(font_tier, 0) or 0) + int(font_slots))
        slot_remaining[font_tier] = max(0, int(slot_remaining.get(font_tier, 0) or 0) + int(font_slots))

        counts = dict(prepared_counts.get(font_tier, {}) or {})
        counts[font_spell] = int(counts.get(font_spell, 0) or 0) + int(font_slots)
        prepared_counts[font_tier] = counts
        consumed_counts[font_tier] = {}

    state["cleric_font"] = font_spell
    state["cleric_font_slots"] = int(max(0, font_slots))
    state["cleric_font_tier"] = font_tier

    try:
        setattr(actor, "cleric_prepared_rank_1_slots_remaining", int(slot_remaining.get("rank_1", 0) or 0))
        for rank in range(2, 11):
            tier = _tier_for_rank(rank)
            setattr(actor, f"cleric_prepared_{tier}_slots_remaining", int(slot_remaining.get(tier, 0) or 0))
    except Exception:
        pass


def _druid_prepare_today(state: dict[str, Any], actor, game, *, prompt: bool) -> None:
    known = state.get("known", {})
    known_cantrips = list(known.get("cantrip", []) or [])
    slot_budget = _druid_slot_budget_by_tier(actor)
    cantrip_budget = int(_druid_cantrip_prepared_count(actor))

    prepared_cantrips = _pick_spells(
        game,
        title="Druid — Przygotuj cantrip (slot)",
        source="spell_prepare",
        choices=known_cantrips,
        count=cantrip_budget,
        allow_duplicates=False,
        prompt=prompt,
    )

    prepared_today = state.setdefault("prepared_today", {})
    prepared_today["cantrip"] = list(prepared_cantrips)
    slot_total = state.setdefault("slot_total", {})
    slot_remaining = state.setdefault("slot_remaining", {})
    prepared_counts = state.setdefault("prepared_counts", {})
    consumed_counts = state.setdefault("consumed_counts", {})

    for rank in range(1, 11):
        tier = _tier_for_rank(rank)
        tier_slots = int(slot_budget.get(tier, 0) or 0)
        tier_known = list(known.get(tier, []) or [])
        _tier_display = tier.replace("rank_", "Ranga ").replace("_", " ").title()
        prepared_spells = _pick_spells(
            game,
            title=f"Druid — Przygotuj czar ({_tier_display}, slot)",
            source="spell_prepare",
            choices=tier_known,
            count=tier_slots,
            allow_duplicates=True,
            prompt=prompt,
        )
        prepared_today[tier] = list(prepared_spells)
        slot_total[tier] = max(0, int(tier_slots))
        slot_remaining[tier] = max(0, int(tier_slots))

        counts: dict[str, int] = {}
        for spell_id in prepared_spells:
            sid = _normalize_spell_id(spell_id)
            if not sid:
                continue
            counts[sid] = int(counts.get(sid, 0) or 0) + 1
        prepared_counts[tier] = counts
        consumed_counts[tier] = {}

    try:
        setattr(actor, "druid_prepared_rank_1_slots_remaining", int(slot_remaining.get("rank_1", 0) or 0))
        for rank in range(2, 11):
            tier = _tier_for_rank(rank)
            setattr(actor, f"druid_prepared_{tier}_slots_remaining", int(slot_remaining.get(tier, 0) or 0))
    except Exception:
        pass


def initialize_actor_spell_management(
    game,
    actor,
    *,
    prompt: bool = True,
    enforce: bool = True,
) -> dict[str, Any]:
    known = _base_known_spell_lists(actor)
    # Zachowaj jednorazowe czary zakupione jako usluga (np. od NPC maga/kaplana).
    current_state = dict(getattr(actor, "spell_state", {}) or {})
    one_shot = _normalize_merchant_one_shot(current_state.get("merchant_one_shot"))
    merchant_known = _normalize_merchant_known(current_state.get("merchant_known"))
    for tier_id, spells in one_shot.items():
        tier_bucket = known.setdefault(tier_id, [])
        for spell_id, count in spells.items():
            if int(count or 0) <= 0:
                continue
            _append_unique(tier_bucket, spell_id)

    class_name = _normalize(getattr(actor, "class_name", ""))
    if class_name == "bard":
        _ensure_bard_baseline_known(actor, known)
    if class_name == "sorcerer":
        _ensure_sorcerer_baseline_known(actor, known)
    if class_name == "cleric":
        _ensure_cleric_baseline_known(actor, known)
    if class_name == "druid":
        _ensure_druid_baseline_known(actor, known)
    _apply_removed_cantrip_overrides(actor, known)
    has_spell_content = any(bool(values) for values in known.values()) or _merchant_one_shot_total(one_shot) > 0
    enabled = has_spell_content or class_name in _CASTER_CLASSES

    state = dict(getattr(actor, "spell_state", {}) or {})
    state["enabled"] = bool(enabled)
    state["enforce"] = bool(enforce and enabled)
    state["class_name"] = class_name
    state["known"] = {key: list(value) for key, value in known.items()}
    state["merchant_one_shot"] = one_shot
    state["merchant_known"] = {tier: sorted(values) for tier, values in merchant_known.items()}
    state.setdefault("prepared_today", {})
    state.setdefault("slot_total", {})
    state.setdefault("slot_remaining", {})
    state.setdefault("prepared_counts", {})
    state.setdefault("consumed_counts", {})

    if class_name == "wizard":
        _wizard_prepare_today(state, actor, game, prompt=prompt)
        if prompt:
            try:
                setattr(actor, "wizard_drain_usage", {})
            except Exception:
                pass
    if class_name == "bard":
        _bard_prepare_today(state, actor)
    if class_name == "sorcerer":
        _sorcerer_prepare_today(state, actor)
        _sync_sorcerer_signature_spells(actor, state)
    if class_name == "cleric":
        _cleric_prepare_today(state, actor, game, prompt=prompt)
    if class_name == "druid":
        _druid_prepare_today(state, actor, game, prompt=prompt)

    try:
        setattr(actor, "spell_state", state)
    except Exception:
        pass

    if bool(enabled) and hasattr(game, "ui_log"):
        known_counts = ", ".join(
            [
                f"cantrip={len(state['known'].get('cantrip', []))}",
                f"rank1={len(state['known'].get('rank_1', []))}",
                f"focus={len(state['known'].get('focus', []))}",
                f"innate={len(state['known'].get('innate', []))}",
            ]
        )
        try:
            game.ui_log(
                f"{getattr(actor, 'name', 'Aktor')}: spell state -> {known_counts}."
            )
        except Exception:
            pass
    return state


def ensure_actor_spell_state(actor, *, game=None, enforce: bool | None = None) -> dict[str, Any]:
    raw = getattr(actor, "spell_state", None)
    if isinstance(raw, dict):
        class_name = _normalize(raw.get("class_name") or getattr(actor, "class_name", ""))
        fresh_known = _base_known_spell_lists(actor)
        one_shot = _normalize_merchant_one_shot(raw.get("merchant_one_shot"))
        merchant_known = _normalize_merchant_known(raw.get("merchant_known"))
        merged_known: dict[str, list[str]] = {}
        current_known = raw.get("known", {}) or {}
        for tier in _KNOWN_TIERS:
            merged: list[str] = []
            _append_many(merged, current_known.get(tier))
            _append_many(merged, fresh_known.get(tier))
            if tier in one_shot:
                for spell_id, count in one_shot.get(tier, {}).items():
                    if int(count or 0) > 0:
                        _append_unique(merged, spell_id)
            merged_known[tier] = merged
        raw["class_name"] = class_name
        raw["known"] = merged_known
        _apply_removed_cantrip_overrides(actor, raw["known"])
        raw["merchant_one_shot"] = one_shot
        raw["merchant_known"] = {tier: sorted(values) for tier, values in merchant_known.items()}
        raw["enabled"] = bool(
            any(bool(items) for items in merged_known.values())
            or class_name in _CASTER_CLASSES
            or _merchant_one_shot_total(one_shot) > 0
        )
        if class_name == "bard":
            slots_default = max(0, int(_bard_rank1_slots_per_day(actor)))
            slot_total = raw.setdefault("slot_total", {})
            slot_remaining = raw.setdefault("slot_remaining", {})
            if "rank_1" not in slot_total:
                slot_total["rank_1"] = slots_default
            if "rank_1" not in slot_remaining:
                slot_remaining["rank_1"] = int(slot_total.get("rank_1", slots_default) or 0)
            try:
                setattr(actor, "bard_rank_1_slots_remaining", int(slot_remaining.get("rank_1", 0) or 0))
            except Exception:
                pass
        if class_name == "sorcerer":
            slot_budget = _sorcerer_slot_budget_by_tier(actor)
            slot_total = raw.setdefault("slot_total", {})
            slot_remaining = raw.setdefault("slot_remaining", {})
            for rank in range(1, 11):
                tier = _tier_for_rank(rank)
                default_slots = max(0, int(slot_budget.get(tier, 0) or 0))
                if tier not in slot_total:
                    slot_total[tier] = default_slots
                if tier not in slot_remaining:
                    slot_remaining[tier] = int(slot_total.get(tier, default_slots) or 0)
            try:
                setattr(actor, "sorcerer_rank_1_slots_remaining", int(slot_remaining.get("rank_1", 0) or 0))
                for rank in range(2, 11):
                    tier = _tier_for_rank(rank)
                    setattr(actor, f"sorcerer_{tier}_slots_remaining", int(slot_remaining.get(tier, 0) or 0))
            except Exception:
                pass
            _sync_sorcerer_signature_spells(actor, raw)
        if enforce is not None:
            raw["enforce"] = bool(enforce and raw.get("enabled", False))
        try:
            setattr(actor, "spell_state", raw)
        except Exception:
            pass
        return raw
    if game is None:
        # Szybki sync bez promptów i bez egzekwowania.
        class _NoGame:
            def ui_log(self, _msg):
                return None

            ui = None

        game = _NoGame()
    return initialize_actor_spell_management(
        game,
        actor,
        prompt=False,
        enforce=bool(enforce) if enforce is not None else False,
    )


def swap_sorcerer_repertoire_spell(
    actor,
    *,
    from_spell: str,
    to_spell: str,
    tier: str | None = None,
    game=None,
) -> tuple[bool, str]:
    state = ensure_actor_spell_state(actor, game=game, enforce=True)
    class_name = _normalize(state.get("class_name") or getattr(actor, "class_name", ""))
    if class_name != "sorcerer":
        return False, "Tylko Sorcerer moze wymieniac czary repertuaru."

    source_spell = _normalize_spell_id(from_spell)
    target_spell = _normalize_spell_id(to_spell)
    if not source_spell or not target_spell:
        return False, "Nieprawidlowy identyfikator czaru."
    if source_spell == target_spell:
        return False, "Nowy czar musi byc inny niz aktualny."

    known = dict(state.get("known", {}) or {})
    chosen_tier = _normalize_tier(tier) if tier else ""
    if chosen_tier not in {"cantrip", *_rank_tiers()}:
        chosen_tier = ""
    if not chosen_tier:
        for candidate_tier in ("cantrip", *_rank_tiers()):
            tier_known = {
                _normalize_spell_id(item)
                for item in list(known.get(candidate_tier, []) or [])
                if _normalize_spell_id(item)
            }
            if source_spell in tier_known:
                chosen_tier = candidate_tier
                break
    if not chosen_tier:
        return False, f"{_labelize(source_spell)} nie figuruje w repertuarze Sorcerera."

    tier_known_list = [
        _normalize_spell_id(item)
        for item in list(known.get(chosen_tier, []) or [])
        if _normalize_spell_id(item)
    ]
    if source_spell not in tier_known_list:
        return False, f"{_labelize(source_spell)} nie figuruje w {chosen_tier.replace('_', ' ')}."
    if target_spell in tier_known_list:
        return False, f"{_labelize(target_spell)} jest juz znany na tym poziomie."

    setup = _sorcerer_setup_data(actor)
    bloodline_granted = dict(
        setup.get("bloodline_granted_spells")
        or getattr(actor, "sorcerer_bloodline_granted_spells", {})
        or {}
    )
    bloodline_spell = _normalize_spell_id(bloodline_granted.get(chosen_tier))
    if bloodline_spell and source_spell == bloodline_spell:
        return False, "Nie mozna wymienic bloodline granted spell."

    tradition = _normalize(setup.get("spell_tradition") or getattr(actor, "sorcerer_spell_tradition", ""))
    if tradition:
        tier_pool = {
            _normalize_spell_id(item)
            for item in _collect_spells_for_tier_and_tradition(tier=chosen_tier, traditions={tradition})
            if _normalize_spell_id(item)
        }
        if tier_pool and target_spell not in tier_pool:
            return False, f"{_labelize(target_spell)} nie nalezy do tradycji {tradition} dla {chosen_tier.replace('_', ' ')}."

    replaced = False
    for idx, spell_id in enumerate(tier_known_list):
        if spell_id != source_spell:
            continue
        tier_known_list[idx] = target_spell
        replaced = True
        break
    if not replaced:
        return False, f"Nie udalo sie podmienic { _labelize(source_spell) }."
    tier_known_list = list(dict.fromkeys([spell_id for spell_id in tier_known_list if spell_id]))
    known[chosen_tier] = list(tier_known_list)
    state["known"] = known

    signatures = [
        _normalize_spell_id(item)
        for item in list(state.get("sorcerer_signature_spells", []) or [])
        if _normalize_spell_id(item)
    ]
    if source_spell in signatures and target_spell not in signatures:
        signatures = [target_spell if spell_id == source_spell else spell_id for spell_id in signatures]
    state["sorcerer_signature_spells"] = list(dict.fromkeys(signatures))

    attr_name = {
        "cantrip": "sorcerer_known_cantrips",
        "rank_1": "sorcerer_known_rank_1_spells",
        "rank_2": "sorcerer_known_rank_2_spells",
        "rank_3": "sorcerer_known_rank_3_spells",
        "rank_4": "sorcerer_known_rank_4_spells",
        "rank_5": "sorcerer_known_rank_5_spells",
        "rank_6": "sorcerer_known_rank_6_spells",
        "rank_7": "sorcerer_known_rank_7_spells",
        "rank_8": "sorcerer_known_rank_8_spells",
        "rank_9": "sorcerer_known_rank_9_spells",
        "rank_10": "sorcerer_known_rank_10_spells",
    }.get(chosen_tier)
    if attr_name:
        try:
            setattr(actor, attr_name, list(tier_known_list))
        except Exception:
            pass

    statuses = list(getattr(actor, "statuses", []) or [])
    for idx, status in enumerate(statuses):
        if getattr(status, "id", None) != "sorcerer":
            continue
        data = dict(getattr(status, "data", None) or {})
        setup_payload = dict(data.get("sorcerer_setup") or {})
        if chosen_tier == "cantrip":
            setup_payload["known_cantrips"] = list(tier_known_list)
            data["sorcerer_known_cantrips"] = list(tier_known_list)
        elif chosen_tier == "rank_1":
            setup_payload["known_rank_1_spells"] = list(tier_known_list)
            data["sorcerer_known_rank_1_spells"] = list(tier_known_list)
        data["sorcerer_setup"] = setup_payload
        data["sorcerer_signature_spells"] = list(state.get("sorcerer_signature_spells", []) or [])
        try:
            from dataclasses import replace

            statuses[idx] = replace(status, data=data)
            setattr(actor, "statuses", statuses)
        except Exception:
            pass
        break

    _sync_sorcerer_signature_spells(actor, state)
    try:
        setattr(actor, "spell_state", state)
    except Exception:
        pass
    return (
        True,
        f"Sorcerer repertoire: { _labelize(source_spell) } -> { _labelize(target_spell) } ({chosen_tier.replace('_', ' ')}).",
    )


def grant_merchant_one_shot_spell(
    actor,
    *,
    spell_id: str,
    tier: str,
    provider_name: str = "",
    game=None,
) -> tuple[bool, str]:
    normalized_spell = _normalize_spell_id(spell_id)
    normalized_tier = _normalize_tier(tier)
    if not normalized_spell:
        return False, "Nieprawidlowy czar uslugowy."
    if normalized_tier not in _KNOWN_TIERS:
        return False, f"Nieobslugiwany poziom czaru: {tier}."

    state = ensure_actor_spell_state(actor, game=game, enforce=True)
    one_shot = _normalize_merchant_one_shot(state.get("merchant_one_shot"))
    current_total = _merchant_one_shot_total(one_shot)
    capacity = merchant_spell_capacity(actor)
    if current_total >= capacity:
        return (
            False,
            f"Limit aktywnych czarow uslugowych osiagniety ({current_total}/{capacity}). "
            "Wydaj najpierw jeden z zapisanych czarow.",
        )

    bucket = dict(one_shot.get(normalized_tier, {}) or {})
    bucket[normalized_spell] = int(bucket.get(normalized_spell, 0) or 0) + 1
    one_shot[normalized_tier] = bucket
    state["merchant_one_shot"] = one_shot
    merchant_known = _normalize_merchant_known(state.get("merchant_known"))
    known_bucket = set(merchant_known.get(normalized_tier, set()) or set())
    known_bucket.add(normalized_spell)
    merchant_known[normalized_tier] = known_bucket
    state["merchant_known"] = {tier_id: sorted(values) for tier_id, values in merchant_known.items()}

    known = dict(state.get("known", {}) or {})
    tier_known = list(known.get(normalized_tier, []) or [])
    _append_unique(tier_known, normalized_spell)
    known[normalized_tier] = tier_known
    state["known"] = known
    state["enabled"] = True
    state["enforce"] = True
    try:
        setattr(actor, "spell_state", state)
    except Exception:
        pass

    provider = str(provider_name or "").strip()
    provider_note = f" od: {provider}" if provider else ""
    updated_total = _merchant_one_shot_total(one_shot)
    return (
        True,
        f"Dodano jednorazowy czar{provider_note}: {_labelize(normalized_spell)} "
        f"({normalized_tier.replace('_', ' ')}, {updated_total}/{capacity}).",
    )


def can_cast_managed_spell(actor, *, spell_id: str, tier: str | None) -> tuple[bool, str | None]:
    state = dict(getattr(actor, "spell_state", {}) or {})
    if not state or not bool(state.get("enabled", False)) or not bool(state.get("enforce", False)):
        return True, None

    spell = _normalize_spell_id(spell_id)
    if not spell:
        return True, None
    normalized_tier = _normalize_tier(tier) if tier is not None else ""
    one_shot = _normalize_merchant_one_shot(state.get("merchant_one_shot"))
    merchant_known = _normalize_merchant_known(state.get("merchant_known"))
    has_one_shot_charge = bool(
        normalized_tier
        and int(one_shot.get(normalized_tier, {}).get(spell, 0) or 0) > 0
    )
    is_merchant_spell = bool(
        normalized_tier and spell in set(merchant_known.get(normalized_tier, set()) or set())
    )
    known = state.get("known", {}) or {}
    known_innate = set(_normalize_spell_id(item) for item in list(known.get("innate", []) or []))
    class_name = _normalize(state.get("class_name") or getattr(actor, "class_name", ""))
    sorcerer_signatures = {
        _normalize_spell_id(item)
        for item in list(state.get("sorcerer_signature_spells", []) or [])
        if _normalize_spell_id(item)
    }

    if normalized_tier:
        tier_known = set(_normalize_spell_id(item) for item in list(known.get(normalized_tier, []) or []))
        if spell not in known_innate and not has_one_shot_charge:
            require_tier_known = bool(tier_known) or class_name == "sorcerer"
            if require_tier_known and spell not in tier_known:
                signature_heighten_ok = (
                    class_name == "sorcerer"
                    and _is_rank_tier(normalized_tier)
                    and spell in sorcerer_signatures
                    and _sorcerer_knows_spell_any_rank(known, spell)
                )
                if not signature_heighten_ok:
                    return False, f"{_labelize(spell)}: czar nie jest znany dla tej postaci."
        if is_merchant_spell and not has_one_shot_charge:
            return False, f"{_labelize(spell)}: brak jednorazowego ladunku od handlarza."
    if spell in known_innate and not has_one_shot_charge:
        return True, None

    if class_name == "wizard" and not has_one_shot_charge:
        prepared_today = state.get("prepared_today", {}) or {}
        if normalized_tier == "cantrip":
            prepared_cantrips = set(_normalize_spell_id(item) for item in list(prepared_today.get("cantrip", []) or []))
            if not prepared_cantrips:
                return False, f"{_labelize(spell)}: brak przygotowanych cantripow."
            if spell not in prepared_cantrips:
                return False, f"{_labelize(spell)}: cantrip nie jest dziś przygotowany."
        if _is_rank_tier(normalized_tier):
            prepared_list = list(prepared_today.get(normalized_tier, []) or [])
            if not prepared_list:
                return False, f"{_labelize(spell)}: brak przygotowanych czarow {normalized_tier.replace('_', ' ')}."
            prepared_counts = dict(state.get("prepared_counts", {}).get(normalized_tier, {}) or {})
            consumed_counts = dict(state.get("consumed_counts", {}).get(normalized_tier, {}) or {})
            prepared_total = int(prepared_counts.get(spell, 0) or 0)
            consumed_total = int(consumed_counts.get(spell, 0) or 0)
            if prepared_total - consumed_total <= 0:
                return False, f"{_labelize(spell)}: brak przygotowanej kopii tego czaru."
            try:
                remaining = int((state.get("slot_remaining", {}) or {}).get(normalized_tier, 0) or 0)
            except Exception:
                remaining = 0
            if remaining <= 0:
                return False, f"{_labelize(spell)}: brak slotów {normalized_tier.replace('_', ' ')}."
    if class_name == "bard" and not has_one_shot_charge:
        if normalized_tier == "rank_1":
            try:
                remaining = int((state.get("slot_remaining", {}) or {}).get("rank_1", 0) or 0)
            except Exception:
                remaining = 0
            if remaining <= 0:
                return False, f"{_labelize(spell)}: brak slotów rank 1."
    if class_name == "sorcerer" and not has_one_shot_charge:
        if _is_rank_tier(normalized_tier):
            try:
                remaining = int((state.get("slot_remaining", {}) or {}).get(normalized_tier, 0) or 0)
            except Exception:
                remaining = 0
            if remaining <= 0:
                return False, f"{_labelize(spell)}: brak slotów {normalized_tier.replace('_', ' ')}."
    if class_name in {"cleric", "druid"} and not has_one_shot_charge:
        prepared_today = state.get("prepared_today", {}) or {}
        if normalized_tier == "cantrip":
            prepared_cantrips = set(_normalize_spell_id(item) for item in list(prepared_today.get("cantrip", []) or []))
            if prepared_cantrips and spell not in prepared_cantrips:
                return False, f"{_labelize(spell)}: cantrip nie jest dziś przygotowany."
        if _is_rank_tier(normalized_tier):
            prepared_counts = dict(state.get("prepared_counts", {}).get(normalized_tier, {}) or {})
            consumed_counts = dict(state.get("consumed_counts", {}).get(normalized_tier, {}) or {})
            if prepared_counts:
                prepared_total = int(prepared_counts.get(spell, 0) or 0)
                consumed_total = int(consumed_counts.get(spell, 0) or 0)
                if prepared_total - consumed_total <= 0:
                    return False, f"{_labelize(spell)}: brak przygotowanej kopii tego czaru."
            try:
                remaining = int((state.get("slot_remaining", {}) or {}).get(normalized_tier, 0) or 0)
            except Exception:
                remaining = 0
            if remaining <= 0:
                return False, f"{_labelize(spell)}: brak slotów {normalized_tier.replace('_', ' ')}."
    return True, None


def consume_managed_spell_resources(actor, *, spell_id: str, tier: str | None) -> None:
    state = dict(getattr(actor, "spell_state", {}) or {})
    if not state or not bool(state.get("enabled", False)) or not bool(state.get("enforce", False)):
        return
    spell = _normalize_spell_id(spell_id)
    normalized_tier = _normalize_tier(tier) if tier is not None else ""

    # 1) Najpierw rozlicz jednorazowe czary zakupione jako usluga.
    if normalized_tier:
        one_shot = _normalize_merchant_one_shot(state.get("merchant_one_shot"))
        tier_bucket = dict(one_shot.get(normalized_tier, {}) or {})
        current_charges = int(tier_bucket.get(spell, 0) or 0)
        if current_charges > 0:
            remaining_charges = max(0, current_charges - 1)
            if remaining_charges > 0:
                tier_bucket[spell] = remaining_charges
            else:
                tier_bucket.pop(spell, None)
            if tier_bucket:
                one_shot[normalized_tier] = tier_bucket
            else:
                one_shot.pop(normalized_tier, None)
            state["merchant_one_shot"] = one_shot
            try:
                setattr(actor, "spell_state", state)
            except Exception:
                pass
            return

    # 2) Standardowe zuzycie slotow klasowych.
    class_name = _normalize(state.get("class_name") or getattr(actor, "class_name", ""))
    if class_name == "bard":
        if normalized_tier != "rank_1":
            return
        slot_remaining = state.setdefault("slot_remaining", {})
        try:
            current_remaining = int(slot_remaining.get("rank_1", 0) or 0)
        except Exception:
            current_remaining = 0
        slot_remaining["rank_1"] = max(0, current_remaining - 1)
        try:
            if class_name == "bard":
                setattr(actor, "bard_rank_1_slots_remaining", int(slot_remaining.get("rank_1", 0) or 0))
            else:
                setattr(actor, "sorcerer_rank_1_slots_remaining", int(slot_remaining.get("rank_1", 0) or 0))
        except Exception:
            pass
        try:
            setattr(actor, "spell_state", state)
        except Exception:
            pass
        return
    if class_name == "sorcerer":
        if not _is_rank_tier(normalized_tier):
            return
        slot_remaining = state.setdefault("slot_remaining", {})
        try:
            current_remaining = int(slot_remaining.get(normalized_tier, 0) or 0)
        except Exception:
            current_remaining = 0
        slot_remaining[normalized_tier] = max(0, current_remaining - 1)
        try:
            if normalized_tier == "rank_1":
                setattr(actor, "sorcerer_rank_1_slots_remaining", int(slot_remaining.get("rank_1", 0) or 0))
            setattr(
                actor,
                f"sorcerer_{normalized_tier}_slots_remaining",
                int(slot_remaining.get(normalized_tier, 0) or 0),
            )
        except Exception:
            pass
        try:
            setattr(actor, "spell_state", state)
        except Exception:
            pass
        return
    if class_name in {"cleric", "druid"}:
        if not _is_rank_tier(normalized_tier):
            return
        slot_remaining = state.setdefault("slot_remaining", {})
        try:
            current_remaining = int(slot_remaining.get(normalized_tier, 0) or 0)
        except Exception:
            current_remaining = 0
        slot_remaining[normalized_tier] = max(0, current_remaining - 1)

        consumed_counts = state.setdefault("consumed_counts", {})
        tier_consumed = dict(consumed_counts.get(normalized_tier, {}) or {})
        tier_consumed[spell] = int(tier_consumed.get(spell, 0) or 0) + 1
        consumed_counts[normalized_tier] = tier_consumed

        try:
            if class_name == "cleric":
                if normalized_tier == "rank_1":
                    setattr(actor, "cleric_prepared_rank_1_slots_remaining", int(slot_remaining.get("rank_1", 0) or 0))
                setattr(
                    actor,
                    f"cleric_prepared_{normalized_tier}_slots_remaining",
                    int(slot_remaining.get(normalized_tier, 0) or 0),
                )
            else:
                if normalized_tier == "rank_1":
                    setattr(actor, "druid_prepared_rank_1_slots_remaining", int(slot_remaining.get("rank_1", 0) or 0))
                setattr(
                    actor,
                    f"druid_prepared_{normalized_tier}_slots_remaining",
                    int(slot_remaining.get(normalized_tier, 0) or 0),
                )
        except Exception:
            pass
        try:
            setattr(actor, "spell_state", state)
        except Exception:
            pass
        return
    if class_name != "wizard":
        return
    if not _is_rank_tier(normalized_tier):
        return
    slot_remaining = state.setdefault("slot_remaining", {})
    try:
        current_remaining = int(slot_remaining.get(normalized_tier, 0) or 0)
    except Exception:
        current_remaining = 0
    slot_remaining[normalized_tier] = max(0, current_remaining - 1)

    consumed_counts = state.setdefault("consumed_counts", {})
    tier_consumed = dict(consumed_counts.get(normalized_tier, {}) or {})
    tier_consumed[spell] = int(tier_consumed.get(spell, 0) or 0) + 1
    consumed_counts[normalized_tier] = tier_consumed

    try:
        if normalized_tier == "rank_1":
            setattr(actor, "wizard_prepared_rank1_slots_remaining", int(slot_remaining.get("rank_1", 0) or 0))
        setattr(
            actor,
            f"wizard_prepared_{normalized_tier}_slots_remaining",
            int(slot_remaining.get(normalized_tier, 0) or 0),
        )
    except Exception:
        pass
    try:
        setattr(actor, "spell_state", state)
    except Exception:
        pass

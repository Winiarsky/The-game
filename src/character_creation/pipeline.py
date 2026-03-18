from __future__ import annotations

import base64
import binascii
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Callable
from uuid import uuid4

from GameObjects.items.armor import BaseArmor, create_armor, list_armor_ids, normalize_armor_id
from GameObjects.items.armor.specialization import (
    armor_group_label_pl,
    armor_specialization_description_pl,
)
from GameObjects.items.alchemical_item import (
    AlchemicalItem,
    alchemical_item_defaults,
    alchemical_item_name_from_event,
    list_alchemical_item_ids,
    normalize_alchemical_event_id,
)
from GameObjects.items.base_item import BaseItem
from GameObjects.items.equipment import create_equipment, list_equipment_ids, normalize_equipment_id
from GameObjects.items.inventory import add_item, ensure_actor_inventory, get_equipped_weapons, item_label, set_equipped_weapons
from GameObjects.items.shield import BaseShield, create_shield, list_shield_ids, normalize_shield_id
from GameObjects.items.weapon import create_weapon, list_weapon_ids, normalize_weapon_id
from economy import (
    add_actor_cp,
    actor_bulk_summary,
    can_actor_afford_cp,
    coin_pouch_from_cp,
    ensure_actor_coin_pouch,
    format_bulk_units,
    format_actor_money,
    format_cp_value,
    item_cost_cp,
    item_bulk_units,
    normalize_coin_pouch,
    refresh_actor_bulk_state,
    set_actor_starting_money_gp,
    spend_actor_cp,
)
from localization import localize_term_pl, localized_hint_pl
from statuses.base import Status
from ui_payloads import _speed_snapshot_values

from .catalog import (
    ABILITY_IDS,
    ANCESTRY_FEAT_IDS_BY_ANCESTRY,
    ANCESTRY_IDS,
    CLASS_DEFENSE_PROFICIENCY,
    CLASS_FEAT_CHOICES_MANUAL,
    CLASS_IDS,
    CLASS_KEY_ABILITY_DEFAULT,
    CLASS_PERCEPTION_RANK,
    CLASS_SAVE_RANKS,
    CLASS_SKILL_RULES,
    CLASS_WEAPON_PROFICIENCY,
    CORE_SKILL_IDS,
    HERITAGE_IDS_BY_ANCESTRY,
    background_boost_options,
    background_training,
    list_background_status_ids,
    resolve_status,
)
from .mechanics import (
    SKILL_TO_ABILITY,
    apply_ability_boost,
    apply_character_creation_ability_boost,
    apply_ability_flaw,
    apply_math_to_hero,
    base_ability_scores,
    compress_rank_map,
    compute_math,
    higher_rank,
    merge_rank_maps,
    proficiency_bonus,
    refresh_actor_ac,
    rank_priority,
)
from .repository import CharacterRepository


_ANCESTRY_FALLBACK = {
    "human": {"boosts": ["free", "free"], "flaw": None},
    "elf": {"boosts": ["dexterity", "intelligence", "free"], "flaw": "constitution"},
    "dwarf": {"boosts": ["constitution", "wisdom", "free"], "flaw": "charisma"},
    "gnome": {"boosts": ["constitution", "charisma", "free"], "flaw": "strength"},
    "goblin": {"boosts": ["dexterity", "charisma", "free"], "flaw": "wisdom"},
    "halfling": {"boosts": ["dexterity", "wisdom", "free"], "flaw": "strength"},
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PORTRAIT_DIR = PROJECT_ROOT / "player_ui" / "static" / "portraits"
_PORTRAIT_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
_STARTING_GOLD_GP = 15
_BACK_OPTION_ID = "__back__"
_BACK_TEXT_TOKENS = {
    _BACK_OPTION_ID,
    "cofnij",
    "wstecz",
    "back",
    "/back",
    "/cofnij",
    "<<",
    "<",
}
_SHOP_SECTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "weapons",
        "label": "Bronie",
        "desc": "Pelny katalog zaimplementowanych broni. Filtry: typ, biegłość, ręce, rzadkość.",
    },
    {
        "id": "armors",
        "label": "Pancerze",
        "desc": "Lekkie/srednie/ciężkie pancerze z aktualnego katalogu gry.",
    },
    {
        "id": "shields",
        "label": "Tarcze",
        "desc": "Buckler oraz tarcze bojowe. Filtruj po rodzaju.",
    },
    {
        "id": "ammunition",
        "label": "Amunicja",
        "desc": "Strzaly, bełty i pociski.",
    },
    {
        "id": "alchemy",
        "label": "Alchemia",
        "desc": "Bomby, eliksiry i narzędzia alchemiczne.",
    },
    {
        "id": "gear",
        "label": "Sprzęt i narzędzia",
        "desc": "Narzędzia, ekwipunek podróżny i wyposażenie użytkowe.",
    },
    {
        "id": "magic",
        "label": "Magiczne i konsumpcyjne",
        "desc": "Mikstury, święta/nieświęta woda, talizmany i zwoje.",
    },
)

_WEAPON_INTERNAL_IDS = {"unarmed", "razortooth_jaws", "shield_bash", "sword", "standard_shield"}
_WEAPON_RARITY_TRAITS = {"dwarf", "elf", "goblin", "gnome", "halfling", "orc", "uncommon"}

_HUMAN_HERITAGE_FEATS_GENERIC: set[str] = {
    "adapted_cantrip",
    "cooperative_nature",
    "general_training",
    "natural_ambition",
    "natural_skill",
    "unconventional_weaponry",
}
_HUMAN_HERITAGE_FEATS_HALF_ELF: set[str] = {
    "elf_atavism",
    "haughty_obstinacy",
}
_HUMAN_HERITAGE_FEATS_HALF_ORC: set[str] = {
    "monstrous_peacemaker",
    "orc_ferocity",
    "orc_sight",
    "orc_superstition",
    "orc_weapon_familiarity",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _labelize(value: str) -> str:
    return localize_term_pl(value)


def _normalize(value: str | None) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _first_line(raw: object) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    for line in text.splitlines():
        line = str(line).strip()
        if line:
            return line
    return ""


def _trim_text(raw: object, *, max_len: int = 320) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _looks_like_spell_hint(text: str) -> bool:
    low = str(text or "").strip().lower()
    if not low:
        return False
    return low.startswith("cantrip:") or low.startswith("czar") or low.startswith("focus spell")


def _spell_hint_has_concrete_mechanics(text: str) -> bool:
    low = str(text or "").strip().lower()
    if not low:
        return False
    mechanic_tokens = (
        "save",
        "rzut",
        "dc",
        "obra",
        "kryty",
        "stunned",
        "enfeebled",
        "immobilized",
        "ac",
        "speed",
        "predkos",
        "zasieg",
        "akcj",
        "tura",
        "+1",
        "-1",
    )
    return any(token in low for token in mechanic_tokens)


def _choice_id_fallback_hint(choice_id: object) -> str:
    raw = _normalize(str(choice_id or ""))
    if not raw:
        return ""
    localized_hint = str(localized_hint_pl(raw) or "").strip()
    if localized_hint and not _looks_like_spell_hint(localized_hint):
        return localized_hint

    aliases = {
        "shield": "shield_cantrip",
        "detectmagic": "detect_magic",
        "acidsplash": "acid_splash",
    }
    normalized = aliases.get(raw, raw)
    try:
        import GameObjects.events.all_events  # noqa: F401
        from GameObjects.events.registry import list_events
        from spell_management import classify_spell_tier
    except Exception:
        return localized_hint

    event_cls = dict(list_events() or {}).get(normalized)
    if event_cls is None:
        return localized_hint

    tags: set[str] = set()
    for tag in list(getattr(event_cls, "spell_tags", []) or []):
        value = _normalize(str(tag or "")).replace("-", "_").replace(" ", "_")
        if value:
            tags.add(value)
    for tag in list(getattr(event_cls, "default_tags", []) or []):
        value = _normalize(str(tag or "")).replace("-", "_").replace(" ", "_")
        if value:
            tags.add(value)
    for tradition in list(getattr(event_cls, "magic_traditions", []) or []):
        value = _normalize(str(getattr(tradition, "value", tradition) or "")).replace("-", "_").replace(" ", "_")
        if value:
            tags.add(value)

    tier = str(classify_spell_tier(list(tags)) or "").strip().lower()
    if tier == "cantrip":
        tier_label = "Cantrip"
    elif tier == "focus":
        tier_label = "Focus"
    elif tier.startswith("rank_"):
        try:
            tier_label = f"Ranga {max(1, int(tier.split('_', 1)[1]))}"
        except Exception:
            tier_label = "Czar"
    else:
        tier_label = "Akcja"

    try:
        actions_cost = max(1, int(getattr(event_cls, "actions_cost", 1) or 1))
    except Exception:
        actions_cost = 1
    cost_label = f"Koszt: {actions_cost} akcja" if actions_cost == 1 else f"Koszt: {actions_cost} akcje"

    range_raw = getattr(event_cls, "range_feet", None)
    if isinstance(range_raw, int):
        range_label = f"Zasieg: {max(0, int(range_raw))} ft"
    elif "touch" in tags:
        range_label = "Zasieg: dotyk"
    else:
        range_label = "Zasieg: wg efektu"

    traditions = [item for item in ("arcane", "divine", "occult", "primal") if item in tags]
    traditions_label = (
        "Tradycja: " + ", ".join(localize_term_pl(item) for item in traditions)
        if traditions
        else "Tradycja: -"
    )

    prompt = _first_line(getattr(event_cls, "prompt", "") or "")
    meta_lines = [tier_label, cost_label, range_label, traditions_label]
    if prompt:
        event_hint = "\n".join([prompt] + [f"- {line}" for line in meta_lines]).strip()
    else:
        event_hint = "\n".join(f"- {line}" for line in meta_lines).strip()

    if localized_hint:
        if _looks_like_spell_hint(localized_hint) and not _spell_hint_has_concrete_mechanics(localized_hint):
            return event_hint or localized_hint
        return localized_hint
    return event_hint


def _structured_choice_desc(
    *,
    name: str,
    fluff: str,
    mechanics: str,
    when: str | None = None,
) -> str:
    import re

    mechanics_raw = str(mechanics or "").strip()
    when_raw = str(when or "").strip()
    effect_raw = mechanics_raw

    if mechanics_raw:
        match_when = re.search(
            r"Kiedy:\s*(.*?)(?:\s*(?:\||;)\s*Efekt:|[\s\.,:-]+Efekt:|$)",
            mechanics_raw,
            flags=re.IGNORECASE | re.DOTALL,
        )
        match_effect = re.search(r"Efekt:\s*(.*)$", mechanics_raw, flags=re.IGNORECASE | re.DOTALL)
        mechanics_starts_with_meta = mechanics_raw.lstrip().lower().startswith("kiedy:") or mechanics_raw.lstrip().lower().startswith("efekt:")
        if mechanics_starts_with_meta:
            if match_when and not when_raw:
                when_raw = str(match_when.group(1) or "").strip(" .;|")
            if match_effect:
                effect_raw = str(match_effect.group(1) or "").strip()
            elif match_when:
                effect_raw = str(mechanics_raw).strip()
    if not when_raw:
        when_raw = "Po wybraniu tej opcji."
    if not effect_raw:
        effect_raw = "Brak dodatkowych informacji mechanicznych."
    when_lines = [line for line in re.split(r"\s*(?:\||\n)\s*", when_raw) if str(line or "").strip()]
    effect_lines = [line for line in re.split(r"\s*(?:\||\n)\s*", effect_raw) if str(line or "").strip()]
    if not when_lines:
        when_lines = ["Po wybraniu tej opcji."]
    if not effect_lines:
        effect_lines = ["Brak dodatkowych informacji mechanicznych."]

    cleaned_when: list[str] = []
    cleaned_effect: list[str] = []
    for item in when_lines:
        text = str(item or "").strip().lstrip("-•").strip(" .;")
        if text:
            cleaned_when.append(text)
    for item in effect_lines:
        text = str(item or "").strip().lstrip("-•").strip()
        if text.lower().startswith("efekt:"):
            text = text.split(":", 1)[1].strip()
        if text:
            cleaned_effect.append(text)
    if not cleaned_when:
        cleaned_when = ["Po wybraniu tej opcji."]
    if not cleaned_effect:
        cleaned_effect = ["Brak dodatkowych informacji mechanicznych."]

    lines = [
        f"Fluff: {str(fluff or '').strip() or '-'}",
        "Mechanika:",
        f"- Kiedy: {cleaned_when[0]}",
    ]
    for extra in cleaned_when[1:]:
        lines.append(f"  - {extra}")

    if len(cleaned_effect) == 1:
        lines.append(f"- Efekt: {cleaned_effect[0]}")
    else:
        lines.append("- Efekt:")
        for item in cleaned_effect:
            lines.append(f"  - {item}")
    return "\n".join(lines)


def _ensure_structured_choice_desc(*, label: str, desc: str, choice_id: str | None = None) -> str:
    text = str(desc or "").strip()
    already_structured = (
        "|" not in text
        and bool(re.search(r"(?mi)^\s*fluff\s*:", text))
        and bool(re.search(r"(?mi)^\s*mechanika\s*:\s*$", text))
        and bool(re.search(r"(?mi)^\s*-\s*kiedy\s*:", text))
        and bool(re.search(r"(?mi)^\s*-\s*efekt\s*:", text))
    )
    if already_structured:
        return text
    fallback_hint = _choice_id_fallback_hint(choice_id or label)
    if not text and fallback_hint:
        text = str(fallback_hint).strip()
    if not text:
        return _structured_choice_desc(
            name=label,
            fluff=f"Wybierasz: {label}.",
            mechanics=f"Efekt zalezy od opcji: {label}.",
        )
    if re.match(r"^\s*(NAZWA:|Fluff:|Mechanika:|Kiedy:|Efekt:)", text, flags=re.IGNORECASE):
        name = label
        fluff = "Opcja wyboru."
        mechanics = ""
        when = ""
        effect = ""
        for raw_line in text.splitlines():
            line = str(raw_line or "").strip()
            if not line:
                continue
            normalized_line = line.lstrip("-• ").strip()
            low = normalized_line.lower()
            if low.startswith("nazwa:"):
                name = normalized_line.split(":", 1)[1].strip() or name
            elif low.startswith("fluff:"):
                fluff = normalized_line.split(":", 1)[1].strip() or fluff
            elif low.startswith("mechanika:"):
                mechanics = normalized_line.split(":", 1)[1].strip() or mechanics
            elif low.startswith("kiedy:"):
                when = normalized_line.split(":", 1)[1].strip() or when
            elif low.startswith("efekt:"):
                effect = normalized_line.split(":", 1)[1].strip() or effect
        if effect:
            mechanics = f"{mechanics}\nEfekt: {effect}".strip()
        return _structured_choice_desc(
            name=name,
            fluff=fluff,
            mechanics=mechanics or "Brak dodatkowych informacji mechanicznych.",
            when=when or None,
        )
    fluff = _first_line(text) or _first_line(fallback_hint) or f"Wybierasz: {label}."
    mechanics = _trim_text(text or fallback_hint, max_len=520) or f"Efekt zalezy od opcji: {label}."
    return _structured_choice_desc(
        name=label,
        fluff=fluff,
        mechanics=mechanics,
    )


def _is_back_choice(value: object) -> bool:
    normalized = _normalize(str(value or ""))
    return normalized in _BACK_TEXT_TOKENS


def _portrait_desc(stem: str) -> str:
    key = _normalize(stem)
    if "warrior" in key or "fighter" in key:
        return "Portret wojownika. Styl frontowy i ofensywny."
    if "rogue" in key or "thief" in key:
        return "Portret łotrzyka. Mobilność, skradanie i precyzja."
    if "mage" in key or "wizard" in key or "sorcerer" in key:
        return "Portret maga. Kontrola pola walki i czary."
    if "cleric" in key or "priest" in key:
        return "Portret kapłana. Wsparcie i magia boska."
    return "Portret bohatera."


def _portrait_label(stem: str) -> str:
    key = _normalize(stem)
    if "warrior" in key or "fighter" in key:
        return "Wojownik"
    if "rogue" in key or "thief" in key:
        return "Lotrzyk"
    if "mage" in key or "wizard" in key or "sorcerer" in key:
        return "Mag"
    if "cleric" in key or "priest" in key:
        return "Kaplan"
    clean_stem = stem[9:] if stem.lower().startswith("portrait_") else stem
    return _labelize(clean_stem)


def _portrait_options() -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    if _PORTRAIT_DIR.exists():
        for path in sorted(_PORTRAIT_DIR.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower() not in _PORTRAIT_EXTS:
                continue
            stem = str(path.stem or "portret")
            options.append(
                {
                    "id": f"/static/portraits/{path.name}",
                    "label": _portrait_label(stem),
                    "desc": _portrait_desc(stem),
                }
            )
    if options:
        return options
    return [
        {
            "id": "/static/placeholder.png",
            "label": "Domyślny Portret",
            "desc": "Portret domyślny (brak dodatkowych grafik).",
        }
    ]


def _store_portrait_bytes(blob: bytes, *, ext: str, suggested_name: str) -> str | None:
    if not blob:
        return None
    if len(blob) > 5 * 1024 * 1024:
        return None
    ext_norm = str(ext or "").strip().lower()
    if ext_norm not in _PORTRAIT_EXTS:
        return None
    target_dir = _PORTRAIT_DIR / "custom"
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = _normalize(suggested_name) or "hero"
    filename = f"{stem}_{uuid4().hex[:8]}{ext_norm}"
    target = target_dir / filename
    try:
        target.write_bytes(blob)
    except Exception:
        return None
    return f"/static/portraits/custom/{filename}"


def _persist_uploaded_portrait(answer: Any, *, suggested_name: str) -> str | None:
    if answer is None:
        return None
    if isinstance(answer, str):
        text = answer.strip()
        if not text:
            return None
        if text.startswith("/static/"):
            return text
        path = Path(text).expanduser()
        if path.exists() and path.is_file():
            ext = path.suffix.lower()
            if ext in _PORTRAIT_EXTS:
                try:
                    blob = path.read_bytes()
                except Exception:
                    return None
                return _store_portrait_bytes(blob, ext=ext, suggested_name=suggested_name)
        return None
    if not isinstance(answer, dict):
        return None
    data_url = str(answer.get("data_url") or "").strip()
    filename = str(answer.get("filename") or "").strip()
    if not data_url.startswith("data:") or ";base64," not in data_url:
        return None
    header, b64 = data_url.split(",", 1)
    mime = header[5:].split(";")[0].strip().lower()
    ext_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
    }
    ext = ext_map.get(mime) or Path(filename).suffix.lower() or ".jpg"
    try:
        blob = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        return None
    return _store_portrait_bytes(blob, ext=ext, suggested_name=suggested_name)


def _pick_portrait_image(game, *, allow_back: bool = False) -> str:
    ui = getattr(game, "ui", None)
    if ui is not None and hasattr(ui, "prompt_file_image"):
        try:
            answer = ui.prompt_file_image(
                title="KROK 0: Wybór portretu postaci",
                subtitle="Wybierz plik obrazu z dysku (jpg/png/webp/svg).",
                prompt_long=(
                    "Otwórz eksplorator plików, wskaż portret, potem Enter aby potwierdzić."
                    + (" Aby cofnąć, wpisz '/back' i potwierdź." if allow_back else "")
                ),
                source="character_creation",
            )
        except Exception:
            answer = None
        if allow_back and _is_back_choice(answer):
            return _BACK_OPTION_ID
        saved = _persist_uploaded_portrait(answer, suggested_name="hero")
        if saved:
            return saved
        return "/static/placeholder.png"
    chosen = _pick_one(
        game,
        title="KROK 0: Wybór portretu postaci",
        subtitle="Wybierz portret bohatera.",
        source="character_creation",
        options=_portrait_options(),
        layout="menu_numpad",
        allow_back=allow_back,
    )
    return str(chosen or "/static/placeholder.png")


def _with_numpad_hint(subtitle: str) -> str:
    hint = "8/2 nawigacja, Enter potwierdzenie."
    base = str(subtitle or "").strip()
    if not base:
        return hint
    if "8/2" in base and "Enter" in base:
        return base
    return f"{base} {hint}"


def _ui_prompt_choice(
    game,
    *,
    title: str,
    subtitle: str,
    source: str,
    options: list[dict[str, str]],
    layout: str = "dialog",
    image: str | None = None,
    allow_back: bool = False,
) -> str | None:
    if not options:
        return None
    ui = getattr(game, "ui", None)
    options_runtime = list(options)
    if allow_back and not any(_normalize(str(item.get("id") or "")) == _BACK_OPTION_ID for item in options_runtime):
        options_runtime.append(
            {
                "id": _BACK_OPTION_ID,
                "label": "Cofnij",
                "desc": "Wróć do poprzedniego kroku tworzenia postaci.",
                "key": "/",
            }
        )

    choice_meta = []
    for idx, option in enumerate(options_runtime, start=1):
        label = str(option.get("label") or option.get("id") or f"Opcja {idx}")
        choice_meta.append(
            {
                "raw": option["id"],
                "label": label,
                "desc": _ensure_structured_choice_desc(
                    label=label,
                    desc=str(option.get("desc") or ""),
                    choice_id=str(option.get("id") or ""),
                ),
                "key": option.get("key") or str(idx),
            }
        )
    if ui is not None and hasattr(ui, "prompt_choice"):
        try:
            answer = ui.prompt_choice(
                title,
                choices=[entry["label"] for entry in choice_meta],
                source=source,
                layout=layout,
                title=title,
                subtitle=_with_numpad_hint(
                    subtitle + (" Wybierz 'Cofnij', aby wrócić." if allow_back else "")
                ),
                choice_meta=choice_meta,
                image=image,
            )
            if answer:
                return str(answer)
        except Exception:
            pass
    try:
        raw = input(f"{title} ").strip()
    except Exception:
        return None
    return raw or None


def _decode_option(raw: str | None, options: list[dict[str, str]], *, allow_back: bool = False) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if allow_back and _is_back_choice(text):
        return _BACK_OPTION_ID
    by_id = {str(item["id"]).strip().lower(): str(item["id"]).strip().lower() for item in options}
    by_label = {str(item["label"]).strip().lower(): str(item["id"]).strip().lower() for item in options}
    by_key = {str(item.get("key") or "").strip().lower(): str(item["id"]).strip().lower() for item in options}
    low = text.lower()
    if low in by_id:
        return by_id[low]
    if low in by_label:
        return by_label[low]
    if low in by_key:
        return by_key[low]
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(options):
            return str(options[idx]["id"]).strip().lower()
    return None


def _pick_one(
    game,
    *,
    title: str,
    subtitle: str,
    source: str,
    options: list[dict[str, str]],
    layout: str = "menu_numpad",
    image: str | None = None,
    allow_back: bool = False,
) -> str | None:
    answer = _ui_prompt_choice(
        game,
        title=title,
        subtitle=subtitle,
        source=source,
        options=options,
        layout=layout,
        image=image,
        allow_back=allow_back,
    )
    return _decode_option(answer, options, allow_back=allow_back)


def _prompt_text(
    game,
    *,
    title: str,
    source: str,
    default: str = "",
    image: str | None = None,
    allow_back: bool = False,
) -> str:
    ui = getattr(game, "ui", None)
    if ui is not None and hasattr(ui, "prompt_choice"):
        try:
            answer = ui.prompt_choice(
                title,
                choices=None,
                source=source,
                layout="dialog",
                title=title,
                subtitle=(
                    "Wpisz tekst i potwierdź Enter."
                    + (" Aby cofnąć: wpisz /back i Enter." if allow_back else "")
                ),
                image=image,
            )
            if allow_back and _is_back_choice(answer):
                return _BACK_OPTION_ID
            if str(answer or "").strip():
                return str(answer).strip()
        except Exception:
            pass
    try:
        raw = input(f"{title} ").strip()
    except Exception:
        raw = ""
    if allow_back and _is_back_choice(raw):
        return _BACK_OPTION_ID
    return raw or default


def _prompt_info(game, *, title: str, text: str, image: str | None = None) -> None:
    # W kreatorze postaci nie blokujemy flow dodatkowymi promptami info.
    try:
        game.ui_log(f"{title}\n{text}")
    except Exception:
        pass


def _notify_creation_progress(
    game,
    hero: Hero,
    *,
    stage: str,
    expected: str | None = None,
    mechanics: str | None = None,
) -> None:
    note_parts = [str(stage or "").strip()]
    if expected:
        note_parts.append(f"Co wybierasz: {str(expected).strip()}")
    if mechanics:
        note_parts.append(f"Mechanika: {str(mechanics).strip()}")
    note = "\n".join(part for part in note_parts if part)
    try:
        sender = getattr(game, "ui_hero", None)
        if callable(sender):
            sender(hero, note=note)
    except Exception:
        pass
    try:
        active_sender = getattr(game, "ui_active_actor", None)
        if callable(active_sender):
            active_sender(hero)
    except Exception:
        pass


def _sync_creation_preview_from_selected(hero: Hero, selected: dict[str, Any]) -> None:
    """Uzupełnij podgląd tworzonej postaci po lewej stronie UI."""
    if hero is None:
        return
    hero.character_creation_in_progress = True
    hero.image = str(selected.get("portrait_image") or getattr(hero, "image", None) or "/static/placeholder.png")
    hero.name = str(selected.get("name") or getattr(hero, "name", None) or "Bohater").strip() or "Bohater"
    hero.character_concept = str(selected.get("concept") or getattr(hero, "character_concept", "") or "")
    hero.ancestry_id = str(selected.get("ancestry_id") or "")
    hero.heritage_id = str(selected.get("heritage_id") or "")
    hero.ancestry_feat_id = str(selected.get("ancestry_feat_id") or "")
    hero.background_id = str(selected.get("background_id") or "")
    hero.class_id = str(selected.get("class_id") or "")
    hero.class_name = hero.class_id or str(getattr(hero, "class_name", "") or "")
    preview_instinct_id = str(selected.get("barbarian_instinct_id") or "")
    if preview_instinct_id:
        setattr(hero, "preview_barbarian_instinct_id", preview_instinct_id)
    else:
        try:
            delattr(hero, "preview_barbarian_instinct_id")
        except Exception:
            pass
    _refresh_creation_preview_bonuses(hero, selected)


def _preview_status_ids_from_selected(selected: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for key in (
        "ancestry_id",
        "heritage_id",
        "ancestry_feat_id",
        "background_id",
        "class_id",
        "barbarian_instinct_id",
        "manual_class_feat_id",
    ):
        normalized = _normalize(selected.get(key))
        if normalized and normalized not in out:
            out.append(normalized)

    # Background często gwarantuje dodatkowy feat/status - pokaż go od razu w live preview.
    background_id = _normalize(selected.get("background_id"))
    if background_id:
        try:
            background_status = resolve_status(background_id)
        except Exception:
            background_status = None
        background_data = getattr(background_status, "data", None) or {}
        background_feat_id = _normalize(background_data.get("background_feat_id"))
        if background_feat_id and background_feat_id not in out:
            out.append(background_feat_id)
    return out


def _clone_status_for_preview(status: Status) -> Status:
    return Status(
        id=str(getattr(status, "id", "") or ""),
        label=str(getattr(status, "label", "") or ""),
        duration=getattr(status, "duration", None),
        source=getattr(status, "source", None),
        stacks=int(getattr(status, "stacks", 1) or 1),
        data=dict(getattr(status, "data", None) or {}),
        check_effects=list(getattr(status, "check_effects", None) or []),
    )


def _refresh_creation_preview_bonuses(hero: Hero, selected: dict[str, Any]) -> None:
    """Przelicz szybki live preview postaci po każdym etapie kreatora."""
    if hero is None:
        return

    preview_statuses: list[Status] = []
    for status_id in _preview_status_ids_from_selected(selected):
        resolved = resolve_status(status_id)
        if resolved is None:
            resolved = Status(id=status_id, label=_labelize(status_id))
        preview_statuses.append(_clone_status_for_preview(resolved))
    hero.statuses = preview_statuses

    ancestry_id = _normalize(selected.get("ancestry_id"))
    background_id = _normalize(selected.get("background_id"))
    class_id = _normalize(selected.get("class_id"))

    ancestry_status = next(
        (item for item in preview_statuses if _normalize(getattr(item, "id", "")) == ancestry_id),
        None,
    )
    class_status = next(
        (item for item in preview_statuses if _normalize(getattr(item, "id", "")) == class_id),
        None,
    )

    if ancestry_status is not None:
        languages, traits, base_speed, ancestry_hp = _extract_languages_traits_speed(ancestry_status)
    else:
        languages, traits, base_speed, ancestry_hp = [], [], 25, 6
    hero.languages = list(dict.fromkeys(languages))
    hero.traits = list(dict.fromkeys(traits))

    ability_scores = base_ability_scores()
    # Etapowanie preview:
    # - zawsze start od 10 we wszystkich cechach,
    # - boosty/flaw ancestry nakładamy dopiero po wyborze heritage,
    # - boosty background/class są nakładane później, w dedykowanych krokach wyboru cech.
    if ancestry_status is not None and _normalize(selected.get("heritage_id")):
        ancestry_boosts, ancestry_flaw = _ancestry_boosts_and_flaw(ancestry_status)
        for boost in ancestry_boosts:
            if boost == "free":
                continue
            apply_character_creation_ability_boost(ability_scores, boost)
        if ancestry_flaw:
            apply_ability_flaw(ability_scores, ancestry_flaw)

    class_skill_rule = dict(CLASS_SKILL_RULES.get(class_id, {"fixed": [], "additional": 0}) or {})
    trained_core: set[str] = {
        _normalize(item)
        for item in list(class_skill_rule.get("fixed") or [])
        if _normalize(item) in CORE_SKILL_IDS
    }
    trained_core.update(_trained_skills_from_statuses(hero))
    skill_ranks = {skill_id: "trained" for skill_id in trained_core if skill_id in CORE_SKILL_IDS}

    if class_id:
        perception_rank = str(CLASS_PERCEPTION_RANK.get(class_id, "trained") or "trained")
        save_ranks = dict(
            CLASS_SAVE_RANKS.get(
                class_id,
                {"fortitude": "trained", "reflex": "trained", "will": "trained"},
            )
        )
    else:
        perception_rank = "untrained"
        save_ranks = {"fortitude": "untrained", "reflex": "untrained", "will": "untrained"}
    status_skill_updates, status_save_updates, status_perception_rank = _status_rank_overrides(hero, level=1)
    skill_ranks = merge_rank_maps(
        skill_ranks,
        status_skill_updates,
        allowed_keys=CORE_SKILL_IDS,
        sparse=True,
    )
    save_ranks = merge_rank_maps(
        save_ranks,
        status_save_updates,
        allowed_keys=("fortitude", "reflex", "will"),
        sparse=True,
    )
    if status_perception_rank and rank_priority(status_perception_rank) > rank_priority(perception_rank):
        perception_rank = status_perception_rank

    class_hp = int((getattr(class_status, "data", None) or {}).get("class_hp") or 8) if class_status is not None else 0
    weapon_ranks = dict(CLASS_WEAPON_PROFICIENCY.get(class_id, {})) if class_id else {}
    defense_ranks = dict(CLASS_DEFENSE_PROFICIENCY.get(class_id, {})) if class_id else {}
    unarmored_rank = str(defense_ranks.get("unarmored", "untrained"))
    lore_skills = _lore_skills_from_statuses(hero)

    math = compute_math(
        level=1,
        ability_scores=ability_scores,
        skill_ranks=skill_ranks,
        perception_rank=perception_rank,
        save_ranks=save_ranks,
        ancestry_hp=ancestry_hp,
        class_hp=class_hp,
        speed_feet=base_speed,
        unarmored_rank=unarmored_rank,
    )
    apply_math_to_hero(
        hero,
        math,
        weapon_proficiency_ranks=weapon_ranks,
        defense_proficiency_ranks=defense_ranks,
        trained_skills=sorted(set(trained_core) | set(skill_ranks.keys())),
        lore_skills=lore_skills,
    )


def _status_description(status: Status) -> str:
    data = getattr(status, "data", None) or {}
    return str(
        data.get("ui_prompt_long")
        or data.get("ui_description")
        or data.get("ui_prompt")
        or "Brak dodatkowego opisu."
    )


def _status_mechanics_short(status: Status | None) -> str:
    max_preview_len = 420
    if status is None:
        return ""
    check_effects = list(getattr(status, "check_effects", None) or [])
    if check_effects:
        def _bonus_type_label(value: object) -> str:
            raw = str(getattr(value, "value", value) or "").strip().lower()
            mapping = {
                "status": "status",
                "circumstance": "circumstance",
                "item": "item",
            }
            return mapping.get(raw, raw or "bonus")

        rows: list[str] = []
        for effect in check_effects:
            skills = [str(item).strip().lower() for item in list(getattr(effect, "skills", None) or []) if str(item).strip()]
            tags = [str(item).strip().lower() for item in list(getattr(effect, "tags_required", None) or []) if str(item).strip()]
            tags = [item for item in tags if item != "roll"]
            when_parts: list[str] = []
            if skills:
                when_parts.append(f"przy testach: {', '.join(_labelize(item) for item in skills)}")
            if tags:
                when_parts.append(f"gdy tagi: {', '.join(_labelize(item) for item in tags)}")
            when_txt = "; ".join(when_parts) if when_parts else "w pasujących testach"

            seen_mods: set[tuple[str, int, bool, str]] = set()
            mod_parts: list[str] = []
            has_multiple_skills = len(set(skills)) > 1
            for bonus in list(getattr(effect, "bonus_effects", None) or []):
                raw_value = int(getattr(bonus, "value", 0) or 0)
                if raw_value == 0:
                    continue
                is_penalty = bool(getattr(bonus, "is_penalty", False) or raw_value < 0)
                abs_value = abs(raw_value)
                btype = _bonus_type_label(getattr(bonus, "type", "status"))
                target_tag = str(getattr(bonus, "tag", "") or "").strip().lower()
                token = (btype, abs_value, is_penalty, target_tag)
                if token in seen_mods:
                    continue
                seen_mods.add(token)
                sign = "-" if is_penalty else "+"
                part = f"{sign}{abs_value} {btype}"
                if target_tag:
                    part += f" do {_labelize(target_tag)}"
                mod_parts.append(part)

            if getattr(effect, "promote", 0):
                mod_parts.append(f"podniesienie stopnia sukcesu o {int(getattr(effect, 'promote', 0))}")
            if getattr(effect, "demote", 0):
                mod_parts.append(f"obniżenie stopnia sukcesu o {int(getattr(effect, 'demote', 0))}")

            if not mod_parts:
                continue
            rows.append(f"Kiedy: {when_txt}. Efekt: {', '.join(mod_parts)}.")

        if rows:
            text = " ; ".join(rows)
            if len(text) > max_preview_len:
                text = text[: max_preview_len - 3].rstrip() + "..."
            return text

    data = getattr(status, "data", None) or {}
    raw = str(data.get("ui_description") or data.get("ui_prompt_long") or data.get("ui_prompt") or "").strip()
    if not raw:
        return ""
    # Prefer explicit "Kiedy/Efekt" blocks when present in descriptions.
    match_when = re.search(
        r"Kiedy:\s*(.*?)(?:\s*(?:\||;)\s*Efekt:|[\s\.,:-]+Efekt:|$)",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )
    match_effect = re.search(r"Efekt:\s*(.*)$", raw, flags=re.IGNORECASE | re.DOTALL)
    if match_when or match_effect:
        when_txt = str((match_when.group(1) if match_when else "") or "").strip(" .;|")
        effect_txt = str((match_effect.group(1) if match_effect else "") or "").strip(" .;|")
        combined_parts: list[str] = []
        if when_txt:
            combined_parts.append(f"Kiedy: {when_txt}")
        if effect_txt:
            combined_parts.append(f"Efekt: {effect_txt}")
        if combined_parts:
            preferred_structured = " ; ".join(combined_parts)
            if len(preferred_structured) > max_preview_len:
                preferred_structured = preferred_structured[: max_preview_len - 3].rstrip() + "..."
            return preferred_structured
    lines = [str(line).strip() for line in raw.splitlines() if str(line).strip()]
    if not lines:
        return ""
    mechanics_keywords = (
        "mechanika",
        "podczas",
        "rage",
        "szal",
        "zyskujesz",
        "otrzymujesz",
        "bonus",
        "kara",
        "trigger",
        "frequency",
        "wymaga",
        "critical",
        "trained",
        "hp",
        "ac",
        "rzut",
        "save",
        "specjalne",
        "dostep",
        "raz dziennie",
    )
    def _line_has_keyword(line_low: str, token: str) -> bool:
        tok = str(token or "").strip().lower()
        if not tok:
            return False
        if len(tok) <= 3:
            words = re.findall(r"[a-z0-9_ąćęłńóśźż]+", line_low)
            return tok in words
        return tok in line_low
    preferred = ""
    for line in lines:
        low = line.lower()
        if any(_line_has_keyword(low, token) for token in mechanics_keywords) or "+" in line or "->" in line:
            preferred = line
            break
    if not preferred:
        for line in lines:
            low = line.lower()
            if low.startswith("fabu") or low.startswith("twoj ") or low.startswith("twoja "):
                continue
            preferred = line
            break
    if not preferred:
        preferred = lines[0]
    if len(preferred) > max_preview_len:
        preferred = preferred[: max_preview_len - 3].rstrip() + "..."
    return preferred


def _filter_ancestry_feat_ids_for_selection(
    ancestry_id: str,
    heritage_id: str,
    feat_ids: list[str],
) -> list[str]:
    ancestry = _normalize(ancestry_id)
    heritage = _normalize(heritage_id)
    normalized = [str(item or "").strip().lower() for item in list(feat_ids or []) if str(item or "").strip()]
    if ancestry != "human":
        return normalized

    allowed: set[str]
    if heritage == "half_elf":
        allowed = set(_HUMAN_HERITAGE_FEATS_GENERIC) | set(_HUMAN_HERITAGE_FEATS_HALF_ELF)
    elif heritage == "half_orc":
        allowed = set(_HUMAN_HERITAGE_FEATS_GENERIC) | set(_HUMAN_HERITAGE_FEATS_HALF_ORC)
    else:
        # Skilled/Versatile i inne czysto ludzkie heritage: tylko ludzkie featy bazowe.
        allowed = set(_HUMAN_HERITAGE_FEATS_GENERIC)
    return [item for item in normalized if item in allowed]


def _create_shop_item(offer: dict[str, Any]):
    kind = str(offer.get("kind") or "").strip().lower()
    item_id = str(offer.get("id") or "").strip().lower()
    if not kind or not item_id:
        return None
    if kind == "weapon":
        return create_weapon(item_id)
    if kind == "armor":
        return create_armor(item_id)
    if kind == "shield":
        return create_shield(item_id)
    if kind in {"ammo", "equipment", "gear"}:
        resolved = normalize_equipment_id(item_id)
        if not resolved:
            return None
        item = create_equipment(resolved)
        if item is None:
            return None
        custom_desc = str(offer.get("desc") or "").strip()
        if custom_desc:
            item.description = custom_desc
        return item
    if kind == "alchemical":
        normalized_event = normalize_alchemical_event_id(item_id)
        defaults = alchemical_item_defaults(normalized_event)
        return AlchemicalItem(
            item_id=f"alchemical:{normalized_event}",
            name=alchemical_item_name_from_event(normalized_event),
            event_name=normalized_event,
            description=str(offer.get("desc") or "Przedmiot alchemiczny."),
            bulk=defaults.get("bulk", "L"),
            price_cp=max(
                item_cost_cp(normalized_event),
                int(defaults.get("price_cp", 0) or 0),
            ),
        )
    return None


def _serialize_inventory_item(item: Any) -> dict[str, Any] | None:
    item_id = str(getattr(item, "item_id", "") or "").strip().lower()
    if not item_id:
        return None
    payload: dict[str, Any] = {
        "item_id": item_id,
        "category": str(getattr(item, "category", "") or "").strip().lower(),
        "name": str(getattr(item, "name", "") or "").strip(),
        "description": str(getattr(item, "description", "") or "").strip(),
        "traits": list(getattr(item, "traits", ()) or ()),
        "price_cp": int(getattr(item, "price_cp", 0) or 0),
        "bulk": getattr(item, "bulk", "-"),
        "instance_id": str(getattr(item, "instance_id", "") or "").strip(),
    }
    event_name = str(getattr(item, "event_name", "") or "").strip()
    if event_name:
        payload["event_name"] = event_name
        payload["preparation_counter"] = int(getattr(item, "preparation_counter", 0) or 0)
        payload["prepared_by_quick_alchemy"] = bool(getattr(item, "prepared_by_quick_alchemy", False))
        payload["prepared_by_advanced_alchemy"] = bool(getattr(item, "prepared_by_advanced_alchemy", False))
    if payload["category"] == "shield":
        payload["current_hp"] = int(getattr(item, "current_hp", 0) or 0)
        payload["raised"] = bool(getattr(item, "raised", False))
    if payload["category"] in {"ammo", "ammunition"} or "ammunition" in set(payload["traits"]):
        payload["ammo_count"] = int(getattr(item, "ammo_count", 0) or 0)
    scroll_spell_id = str(getattr(item, "scroll_spell_id", "") or "").strip().lower().replace("-", "_").replace(" ", "_")
    if scroll_spell_id:
        payload["scroll_spell_id"] = scroll_spell_id
    return payload


def _serialize_inventory(hero: Hero) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for item in list(getattr(hero, "inventory", []) or []):
        payload = _serialize_inventory_item(item)
        if payload is not None:
            serialized.append(payload)
    return serialized


def _item_from_snapshot_payload(payload: dict[str, Any]):
    item_id = str(payload.get("item_id") or "").strip().lower()
    if not item_id:
        return None
    event_name = str(payload.get("event_name") or "").strip().lower()
    category = str(payload.get("category") or "").strip().lower()

    item = create_weapon(item_id)
    if item is None:
        item = create_armor(item_id)
    if item is None:
        item = create_shield(item_id)
    if item is None:
        item = create_equipment(item_id)
    if item is None and (event_name or item_id.startswith("alchemical:") or category == "potion"):
        resolved_event = normalize_alchemical_event_id(event_name or item_id.split(":", 1)[-1])
        defaults = alchemical_item_defaults(resolved_event)
        item = AlchemicalItem(
            item_id=f"alchemical:{resolved_event}",
            name=alchemical_item_name_from_event(resolved_event),
            event_name=resolved_event,
            bulk=defaults.get("bulk", "L"),
            price_cp=max(0, int(defaults.get("price_cp", 0) or 0)),
        )
    if item is None:
        item = BaseItem(
            item_id=item_id,
            name=str(payload.get("name") or _labelize(item_id) or item_id),
            category=category or "gear",
        )

    try:
        item.name = str(payload.get("name") or getattr(item, "name", "") or "")
    except Exception:
        pass
    try:
        item.description = str(payload.get("description") or getattr(item, "description", "") or "")
    except Exception:
        pass
    try:
        item.traits = tuple(payload.get("traits") or getattr(item, "traits", ()) or ())
    except Exception:
        pass
    try:
        item.price_cp = int(payload.get("price_cp", getattr(item, "price_cp", 0)) or 0)
    except Exception:
        pass
    if "bulk" in payload:
        try:
            item.bulk = payload.get("bulk", getattr(item, "bulk", "-"))
        except Exception:
            pass
    instance_id = str(payload.get("instance_id") or "").strip()
    if instance_id:
        try:
            item.instance_id = instance_id
        except Exception:
            pass

    if isinstance(item, AlchemicalItem):
        try:
            resolved_event = event_name or item_id.split(":", 1)[-1]
            item.event_name = resolved_event
            item.preparation_counter = max(0, int(payload.get("preparation_counter", 0) or 0))
            item.prepared_by_quick_alchemy = bool(payload.get("prepared_by_quick_alchemy", False))
            item.prepared_by_advanced_alchemy = bool(payload.get("prepared_by_advanced_alchemy", False))
        except Exception:
            pass
    if str(getattr(item, "category", "") or "").strip().lower() == "shield":
        if "current_hp" in payload:
            try:
                item.current_hp = max(0, int(payload.get("current_hp", getattr(item, "current_hp", 0)) or 0))
            except Exception:
                pass
        if "raised" in payload:
            try:
                item.raised = bool(payload.get("raised"))
            except Exception:
                pass
    if "ammo_count" in payload:
        try:
            item.ammo_count = max(0, int(payload.get("ammo_count", 0) or 0))
        except Exception:
            pass
    scroll_spell_id = str(payload.get("scroll_spell_id") or "").strip().lower().replace("-", "_").replace(" ", "_")
    if scroll_spell_id:
        try:
            setattr(item, "scroll_spell_id", scroll_spell_id)
        except Exception:
            pass
    return item


def _restore_inventory_from_snapshot(snapshot: dict[str, Any]) -> list[object]:
    out: list[object] = []
    raw = snapshot.get("inventory_items")
    if not isinstance(raw, list):
        return out
    for row in raw:
        if not isinstance(row, dict):
            continue
        item = _item_from_snapshot_payload(row)
        if item is not None:
            out.append(item)
    return out


def _loadouts_from_inventory(hero: Hero) -> tuple[list[str], list[str], list[str]]:
    weapons: list[str] = []
    armors: list[str] = []
    shields: list[str] = []
    for item in list(getattr(hero, "inventory", []) or []):
        item_id = str(getattr(item, "item_id", "") or "").strip().lower()
        if not item_id:
            continue
        weapon_id = normalize_weapon_id(item_id)
        if weapon_id and weapon_id not in weapons and weapon_id != "unarmed":
            weapons.append(weapon_id)
            continue
        armor_id = normalize_armor_id(item_id)
        if armor_id and armor_id not in armors:
            armors.append(armor_id)
            continue
        shield_id = normalize_shield_id(item_id)
        if shield_id and shield_id not in shields:
            shields.append(shield_id)
            continue
    if not weapons:
        weapons = ["unarmed"]
    return weapons, armors, shields


_DAMAGE_TYPE_LABELS_PL: dict[str, str] = {
    "slashing": "sieczne",
    "piercing": "klute",
    "bludgeoning": "obuchowe",
    "fire": "ogien",
    "cold": "zimno",
    "electricity": "elektryczne",
    "acid": "kwas",
    "sonic": "dzwiekowe",
    "mental": "mentalne",
    "positive": "pozytywne",
    "negative": "negatywne",
    "good": "good",
    "evil": "evil",
}

_WEAPON_TRAIT_HINTS_PL: dict[str, str] = {
    "agile": "MAP jest mniejszy: drugi atak -4, trzeci -8.",
    "finesse": "Do ataku melee mozesz uzyc DEX zamiast STR.",
    "sweep": "Po ataku innego celu w tej turze zyskujesz +1 circumstance do trafienia.",
    "shove": "Bron wspiera manewr Shove (odepchniecie).",
    "trip": "Bron wspiera manewr Trip (podciecie).",
    "disarm": "Bron wspiera manewr Disarm (rozbrojenie).",
    "parry": "Mozesz wykonac Parry, aby zyskac bonus do AC do poczatku nastepnej tury.",
    "forceful": "Kolejne trafienia ta bronia w tej turze zyskuja bonus do obrazen.",
    "backswing": "Po pudle zyskujesz +1 circumstance do nastepnego ataku ta bronia w turze.",
    "nonlethal": "Domyslnie zadaje obrazenia nieletalne.",
    "free_hand": "Reka pozostaje wolna do Interact/manewrow mimo trzymania broni.",
    "crossbow": "Bron kuszowa, zwykle wymaga przeladowania po strzale.",
    "propulsive": "Do obrazen dystansowych dodajesz polowe modyfikatora STR.",
}

_ARMOR_TRAIT_HINTS_PL: dict[str, str] = {
    "comfort": "Wygodny pancerz, brak dodatkowych utrudnien podczas noszenia.",
    "flexible": "Nie stosujesz kary pancerza do testow Acrobatics i Athletics.",
    "noisy": "Kara pancerza do Stealth zawsze obowiazuje (nawet przy spelnionym STR).",
    "bulwark": "W testach Reflex vs efekty obszarowe/obrazenia ustawia min. +3 z DEX.",
}

_SHIELD_TRAIT_HINTS_PL: dict[str, str] = {
    "shield_block": "Umozliwia reakcje Blok tarcza (redukcja obrazen do Twardosci, koszt reakcji).",
    "tower_shield": "Podniesiona tarcza wiezowa daje oslonowe premie; z Take Cover zapewnia greater cover (+4 AC).",
    "light_shield": "Lekka tarcza o mniejszej wytrzymalosci i bonusie do AC.",
}


def _parse_trait_token(trait: str) -> tuple[str, str]:
    text = str(trait or "").strip().lower()
    if ":" in text:
        key, value = text.split(":", 1)
        return key.strip(), value.strip()
    return text, ""


def _trait_effect_line_pl(trait: str) -> str:
    key, value = _parse_trait_token(trait)
    if key == "thrown":
        return f"Thrown {value} ft: mozesz rzucic bronia na dystans {value} stop."
    if key == "versatile":
        dtype = _DAMAGE_TYPE_LABELS_PL.get(value, value.upper() if value else value)
        return f"Versatile {value.upper()}: mozesz zmienic typ obrazen na {dtype}."
    if key == "deadly":
        return f"Deadly {value}: przy trafieniu krytycznym dodajesz dodatkowa kosc {value}."
    if key == "fatal":
        return f"Fatal {value}: kryt podnosi kosc obrazen do {value} i dodaje dodatkowa kosc {value}."
    if key == "reach":
        reach_ft = value or "10"
        return f"Reach {reach_ft} ft: zwieksza zasieg atakow melee."
    if key == "reload":
        return f"Reload {value}: po strzale musisz przeladowac ({value} akcja/akcje)."
    if key == "volley":
        return f"Volley {value} ft: -2 do ataku przeciw celom blizej niz {value} stop."
    if key == "two_hand":
        return f"Two-hand {value}: trzymajac oburacz obrazenia zmieniaja sie na {value}."
    hint = _WEAPON_TRAIT_HINTS_PL.get(key) or localized_hint_pl(key)
    trait_label = _labelize(key)
    if hint:
        return f"{trait_label}: {hint}"
    return f"{trait_label}: cecha specjalna broni."


def _weapon_shop_mechanics_desc(item: BaseItem) -> str:
    damage_prompt = str(getattr(item, "damage_prompt", "") or "-")
    damage_type_raw = str(getattr(item, "damage_type", "") or "").strip().lower()
    damage_type = _DAMAGE_TYPE_LABELS_PL.get(damage_type_raw, _labelize(damage_type_raw) if damage_type_raw else "-")
    ranged = bool(getattr(item, "ranged", False))
    range_increment = int(getattr(item, "range_increment_ft", 0) or 0)
    reload = int(getattr(item, "reload", 0) or 0)
    prof = _labelize(str(getattr(item, "proficiency_category", "") or "simple"))
    group = _labelize(str(getattr(item, "weapon_group", "") or ""))
    hands_required = int(getattr(item, "hands_required", 1) or 1)
    traits = [str(value).strip() for value in list(getattr(item, "traits", ()) or ()) if str(value).strip()]
    trait_labels = ", ".join(_labelize(_parse_trait_token(value)[0]) for value in traits) if traits else "brak"
    trait_effects = "; ".join(_trait_effect_line_pl(value) for value in traits) if traits else "Brak dodatkowych efektow cech."
    parts = [
        f"Atak: {damage_prompt} ({damage_type})",
        f"Typ: {'dystansowa' if ranged else 'wrecz'}",
        f"Rece: {hands_required}",
        f"Bieglosc: {prof}",
    ]
    if group:
        parts.append(f"Grupa: {group}")
    if ranged and range_increment > 0:
        parts.append(f"Zasieg: {range_increment} ft")
    if reload > 0:
        parts.append(f"Przeladowanie: {reload}")
    parts.append(f"Cechy: {trait_labels}")
    parts.append(f"Dzialanie cech: {trait_effects}")
    return "\n".join(f"- {part}" for part in parts)


def _armor_trait_effect_line_pl(trait: str) -> str:
    key, _value = _parse_trait_token(trait)
    hint = _ARMOR_TRAIT_HINTS_PL.get(key) or localized_hint_pl(key)
    trait_label = _labelize(key)
    if hint:
        return f"{trait_label}: {hint}"
    return f"{trait_label}: cecha specjalna pancerza."


def _armor_shop_mechanics_desc(item: BaseArmor) -> str:
    armor_category = _labelize(str(getattr(item, "armor_category", "") or "light"))
    armor_group = str(getattr(item, "armor_group", "cloth") or "cloth")
    ac_bonus = int(getattr(item, "ac_bonus", 0) or 0)
    dex_cap = int(getattr(item, "dex_cap", 0) or 0)
    strength_requirement = int(getattr(item, "strength_requirement", 10) or 10)
    check_penalty = max(0, int(getattr(item, "check_penalty", 0) or 0))
    speed_penalty = max(0, int(getattr(item, "speed_penalty_feet", 0) or 0))
    bulwark_floor_raw = getattr(item, "bulwark_reflex_floor", None)
    bulwark_floor = None if bulwark_floor_raw is None else int(bulwark_floor_raw)
    specialization_effect = armor_specialization_description_pl(
        armor_group=armor_group,
        armor_category=getattr(item, "armor_category", "light"),
    )
    traits = [str(value).strip() for value in list(getattr(item, "traits", ()) or ()) if str(value).strip()]
    trait_labels = ", ".join(_labelize(_parse_trait_token(value)[0]) for value in traits) if traits else "brak"
    trait_effects = [_armor_trait_effect_line_pl(value) for value in traits]
    parts = [
        f"Kategoria: {armor_category}",
        f"Grupa pancerza: {armor_group_label_pl(armor_group)}",
        f"Bonus AC: +{ac_bonus}",
        f"Max DEX: +{dex_cap}",
        f"Wymaganie STR: {strength_requirement}",
        f"Kara do testow (STR/DEX, m.in. Stealth): -{check_penalty}",
        f"Kara do predkosci: -{speed_penalty} ft",
        f"Specjalizacja pancerza: {specialization_effect}",
    ]
    if bulwark_floor is not None:
        parts.append(f"Bulwark (minimum Refleks): +{bulwark_floor}")
    parts.append(f"Cechy: {trait_labels}")
    if trait_effects:
        parts.append("Dzialanie cech:")
        parts.extend(f"Dzialanie cechy: {effect}" for effect in trait_effects)
    else:
        parts.append("Dzialanie cech: Brak dodatkowych efektow cech.")
    return "\n".join(f"- {part}" for part in parts)


def _shield_trait_effect_line_pl(trait: str) -> str:
    key, _value = _parse_trait_token(trait)
    hint = _SHIELD_TRAIT_HINTS_PL.get(key) or localized_hint_pl(key)
    trait_label = _labelize(key)
    if hint:
        return f"{trait_label}: {hint}"
    return f"{trait_label}: cecha specjalna tarczy."


def _shield_shop_mechanics_desc(item: BaseShield) -> str:
    ac_bonus = int(getattr(item, "ac_bonus", 0) or 0)
    take_cover_ac = int(getattr(item, "take_cover_ac_bonus", ac_bonus) or ac_bonus)
    hardness = int(getattr(item, "hardness", 0) or 0)
    max_hp = int(getattr(item, "max_hp", 0) or 0)
    bt = int(getattr(item, "broken_threshold", 0) or 0)
    speed_penalty = max(0, int(getattr(item, "speed_penalty_feet", 0) or 0))
    traits = [str(value).strip() for value in list(getattr(item, "traits", ()) or ()) if str(value).strip()]
    trait_labels = ", ".join(_labelize(_parse_trait_token(value)[0]) for value in traits) if traits else "brak"
    trait_effects = "; ".join(_shield_trait_effect_line_pl(value) for value in traits) if traits else "Brak dodatkowych efektow cech."
    trait_keys = {str(_parse_trait_token(value)[0] or "").strip().lower() for value in traits}

    parts = [
        f"Bonus AC: +{ac_bonus} (dziala przy akcji Raise Shield)",
        f"Twardosc: {hardness}",
        f"HP tarczy: {max_hp}",
        f"Prog zniszczenia (BT): {bt}",
    ]
    if take_cover_ac > ac_bonus:
        parts.append(f"Oslona: do +{take_cover_ac} AC")
    if speed_penalty > 0:
        parts.append(f"Kara do predkosci po Raise Shield: -{speed_penalty} ft")
    if "tower_shield" in trait_keys:
        parts.append("Tarcza wiezowa: podniesiona tarcza tworzy oslone dla strzalow; z Oslona daje wieksza oslone (+4 AC).")
    parts.append(f"Cechy: {trait_labels}")
    parts.append(f"Dzialanie cech: {trait_effects}")
    return "\n".join(f"- {part}" for part in parts)


def _item_choice_desc(offer: dict[str, Any], item: BaseItem, *, owned: int) -> str:
    item_id = str(offer.get("id") or "").strip().lower()
    kind = str(offer.get("kind") or "").strip().lower()
    fluff = _first_line(offer.get("desc")) or "Przedmiot przydatny w przygodzie."
    cost_cp = item_cost_cp(item_id)
    bulk_units = item_bulk_units(item)
    name = _labelize(item_id)

    if kind == "weapon":
        mechanics = (
            f"{_weapon_shop_mechanics_desc(item)}\n"
            f"- Cena: {format_cp_value(cost_cp)}\n"
            f"- Bulk: {format_bulk_units(bulk_units)}\n"
            f"- Posiadane: {owned}."
        )
        return _structured_choice_desc(
            name=name,
            fluff=fluff,
            mechanics=mechanics,
            when="Podczas zakupu w etapie ekwipunku startowego.",
        )

    if kind == "armor" and isinstance(item, BaseArmor):
        mechanics = (
            f"{_armor_shop_mechanics_desc(item)}\n"
            f"- Cena: {format_cp_value(cost_cp)}\n"
            f"- Bulk: {format_bulk_units(bulk_units)}\n"
            f"- Posiadane: {owned}."
        )
        return _structured_choice_desc(
            name=name,
            fluff=fluff,
            mechanics=mechanics,
            when="Podczas zakupu w etapie ekwipunku startowego.",
        )

    if kind == "shield" and isinstance(item, BaseShield):
        mechanics = (
            f"{_shield_shop_mechanics_desc(item)}\n"
            f"- Cena: {format_cp_value(cost_cp)}\n"
            f"- Bulk: {format_bulk_units(bulk_units)}\n"
            f"- Posiadane: {owned}."
        )
        return _structured_choice_desc(
            name=name,
            fluff=fluff,
            mechanics=mechanics,
            when="Podczas zakupu w etapie ekwipunku startowego.",
        )

    mechanics = (
        "\n".join(
            [
                f"- Cena: {format_cp_value(cost_cp)}",
                f"- Bulk: {format_bulk_units(bulk_units)}",
                f"- Posiadane: {owned}.",
                str(getattr(item, "description", "") or "").strip(),
            ]
        ).strip()
    )
    return _structured_choice_desc(
        name=name,
        fluff=fluff,
        mechanics=mechanics,
        when="Podczas zakupu w etapie ekwipunku startowego.",
    )


def _equip_from_inventory_defaults(hero: Hero) -> None:
    inventory = ensure_actor_inventory(hero)
    first_weapon = None
    first_shield = None
    first_armor = None
    for item in inventory:
        item_id = str(getattr(item, "item_id", "") or "").strip().lower()
        if first_weapon is None and normalize_weapon_id(item_id) not in {None, "unarmed"}:
            first_weapon = item
        if first_shield is None and normalize_shield_id(item_id):
            first_shield = item
        if first_armor is None and normalize_armor_id(item_id):
            first_armor = item
    if first_weapon is not None:
        set_equipped_weapons(hero, [first_weapon])
    if first_shield is not None:
        try:
            setattr(hero, "equipped_shield", first_shield)
        except Exception:
            pass
    if first_armor is not None:
        try:
            setattr(hero, "equipped_armor_item_id", str(getattr(first_armor, "instance_id", "") or ""))
        except Exception:
            pass
    refresh_actor_ac(hero)


def _offer_key(offer: dict[str, Any]) -> str:
    return f"{str(offer.get('kind') or '').strip().lower()}:{str(offer.get('id') or '').strip().lower()}"


def _weapon_rarity(item: BaseItem) -> str:
    traits = {str(value or "").strip().lower() for value in list(getattr(item, "traits", ()) or ())}
    return "uncommon" if traits & _WEAPON_RARITY_TRAITS else "common"


def _item_trait_keys(item: BaseItem) -> tuple[str, ...]:
    keys: list[str] = []
    for raw in list(getattr(item, "traits", ()) or ()):
        key, _value = _parse_trait_token(str(raw or ""))
        normalized = _normalize(key)
        if normalized and normalized not in keys:
            keys.append(normalized)
    return tuple(keys)


def _weapon_damage_die_key(item: BaseItem) -> str:
    prompt = str(getattr(item, "damage_prompt", "") or "").strip().lower()
    match = re.search(r"\b\d+\s*[kd]\s*(\d+)\b", prompt)
    if not match:
        return "other"
    sides = str(match.group(1) or "").strip()
    if not sides.isdigit():
        return "other"
    return f"k{int(sides)}"


def _alchemical_kind(item_id: str) -> str:
    key = str(item_id or "").strip().lower()
    bombs = {"acidflask", "alchemists_fire", "bottled_lightning", "frost_vial", "tanglefoot_bag", "thunderstone"}
    elixirs = {"antidote", "antiplague", "elixir_of_life"}
    if key in bombs:
        return "bomb"
    if key in elixirs:
        return "elixir"
    return "tool"


def _equipment_offer_section(item: BaseItem) -> tuple[str, str]:
    category = str(getattr(item, "category", "") or "").strip().lower()
    item_id = str(getattr(item, "item_id", "") or "").strip().lower()
    traits = {str(value or "").strip().lower() for value in list(getattr(item, "traits", ()) or ())}
    if category == "ammo" or "ammunition" in traits:
        kind = {
            "arrows": "arrows",
            "bolts": "bolts",
            "sling_bullets": "sling",
        }.get(item_id, "other")
        return "ammunition", kind
    if category == "potion" or "magic" in traits:
        if "scroll" in traits:
            return "magic", "scroll"
        if "talisman" in traits:
            return "magic", "talisman"
        if item_id in {"holy_water", "unholy_water"}:
            return "magic", "water"
        if "healing" in traits:
            return "magic", "potion"
        return "magic", "other"
    if "tools" in traits or "tool" in traits:
        return "gear", "tools"
    if "container" in traits:
        return "gear", "container"
    if "light_source" in traits:
        return "gear", "light"
    if "camp" in traits:
        return "gear", "camp"
    return "gear", "adventuring"


def _build_full_shop_offers() -> list[dict[str, Any]]:
    offers: list[dict[str, Any]] = []

    for weapon_id in list_weapon_ids():
        if weapon_id in _WEAPON_INTERNAL_IDS:
            continue
        item = create_weapon(weapon_id)
        if item is None:
            continue
        offers.append(
            {
                "id": weapon_id,
                "kind": "weapon",
                "section": "weapons",
                "desc": str(getattr(item, "description", "") or "").strip(),
                "weapon_type": "ranged" if bool(getattr(item, "ranged", False)) else "melee",
                "proficiency": str(getattr(item, "proficiency_category", "simple") or "simple").strip().lower(),
                "hands": str(max(1, int(getattr(item, "hands_required", 1) or 1))),
                "rarity": _weapon_rarity(item),
                "traits": list(_item_trait_keys(item)),
                "damage_die": _weapon_damage_die_key(item),
            }
        )

    for armor_id in list_armor_ids():
        item = create_armor(armor_id)
        if item is None:
            continue
        offers.append(
            {
                "id": armor_id,
                "kind": "armor",
                "section": "armors",
                "desc": str(getattr(item, "description", "") or "").strip(),
                "armor_category": str(getattr(item, "armor_category", "light") or "light").strip().lower(),
            }
        )

    for shield_id in list_shield_ids():
        if shield_id == "standard_shield":
            continue
        item = create_shield(shield_id)
        if item is None:
            continue
        traits = {str(value or "").strip().lower() for value in list(getattr(item, "traits", ()) or ())}
        if shield_id == "buckler":
            shield_type = "buckler"
        elif "tower_shield" in traits:
            shield_type = "tower"
        else:
            shield_type = "standard"
        offers.append(
            {
                "id": shield_id,
                "kind": "shield",
                "section": "shields",
                "desc": str(getattr(item, "description", "") or "").strip(),
                "shield_type": shield_type,
            }
        )

    for equipment_id in list_equipment_ids():
        item = create_equipment(equipment_id)
        if item is None:
            continue
        section, section_kind = _equipment_offer_section(item)
        offers.append(
            {
                "id": equipment_id,
                "kind": "equipment",
                "section": section,
                "desc": str(getattr(item, "description", "") or "").strip(),
                f"{section}_kind": section_kind,
            }
        )

    for alchemical_id in list_alchemical_item_ids():
        item = _create_shop_item({"id": alchemical_id, "kind": "alchemical"})
        if item is None:
            continue
        offers.append(
            {
                "id": alchemical_id,
                "kind": "alchemical",
                "section": "alchemy",
                "desc": str(getattr(item, "description", "") or "").strip(),
                "alchemy_kind": _alchemical_kind(alchemical_id),
            }
        )

    order_map = {str(section.get("id") or ""): idx for idx, section in enumerate(_SHOP_SECTIONS)}
    offers.sort(key=lambda row: (order_map.get(str(row.get("section") or ""), 999), _labelize(str(row.get("id") or ""))))
    return offers


# Backward-compatible alias used by tests and helper utilities.
_STARTER_SHOP_OFFERS: tuple[dict[str, Any], ...] = tuple(_build_full_shop_offers())


def _section_trait_filter_values(section_id: str) -> list[tuple[str, str]]:
    sid = str(section_id or "").strip().lower()
    values: list[str] = []
    for row in _STARTER_SHOP_OFFERS:
        if str(row.get("section") or "").strip().lower() != sid:
            continue
        for raw in list(row.get("traits") or ()):
            normalized = _normalize(str(raw or ""))
            if normalized and normalized not in values:
                values.append(normalized)
    values.sort(key=lambda item: _labelize(item))
    return [(item, _labelize(item)) for item in values]


def _section_weapon_damage_die_values() -> list[tuple[str, str]]:
    values: list[str] = []
    for row in _STARTER_SHOP_OFFERS:
        if str(row.get("section") or "").strip().lower() != "weapons":
            continue
        key = _normalize(str(row.get("damage_die") or ""))
        if key and key not in values:
            values.append(key)

    def _sort_key(value: str) -> tuple[int, int]:
        low = str(value or "").strip().lower()
        if low.startswith("k") and low[1:].isdigit():
            return (0, int(low[1:]))
        return (1, 0)

    values.sort(key=_sort_key)
    labels = {"other": "Inne"}
    return [(item, labels.get(item, item.upper())) for item in values]


def _section_filter_state_defaults(section_id: str) -> dict[str, str]:
    sid = str(section_id or "").strip().lower()
    if sid == "weapons":
        return {
            "weapon_type": "all",
            "proficiency": "all",
            "hands": "all",
            "rarity": "all",
            "trait": "all",
            "damage_die": "all",
        }
    if sid == "armors":
        return {"armor_category": "all"}
    if sid == "shields":
        return {"shield_type": "all"}
    if sid == "ammunition":
        return {"ammunition_kind": "all"}
    if sid == "alchemy":
        return {"alchemy_kind": "all"}
    if sid == "gear":
        return {"gear_kind": "all"}
    if sid == "magic":
        return {"magic_kind": "all"}
    return {}


def _section_filter_specs(section_id: str) -> list[tuple[str, str, list[tuple[str, str]]]]:
    sid = str(section_id or "").strip().lower()
    if sid == "weapons":
        trait_values = [("all", "Wszystkie")] + _section_trait_filter_values("weapons")
        damage_die_values = [("all", "Wszystkie")] + _section_weapon_damage_die_values()
        return [
            ("weapon_type", "Typ", [("all", "Wszystkie"), ("melee", "Wrecz"), ("ranged", "Dystansowe")]),
            ("proficiency", "Bieglosc", [("all", "Wszystkie"), ("simple", "Simple"), ("martial", "Martial"), ("advanced", "Advanced")]),
            ("hands", "Rece", [("all", "Wszystkie"), ("1", "1 reka"), ("2", "2 rece")]),
            ("rarity", "Rzadkosc", [("all", "Wszystkie"), ("common", "Common"), ("uncommon", "Uncommon")]),
            ("trait", "Trait", trait_values),
            ("damage_die", "Kosc obrazen", damage_die_values),
        ]
    if sid == "armors":
        return [("armor_category", "Kategoria", [("all", "Wszystkie"), ("light", "Lekkie"), ("medium", "Srednie"), ("heavy", "Ciezkie")])]
    if sid == "shields":
        return [("shield_type", "Typ", [("all", "Wszystkie"), ("buckler", "Buckler"), ("standard", "Standard"), ("tower", "Tower")])]
    if sid == "ammunition":
        return [("ammunition_kind", "Typ", [("all", "Wszystkie"), ("arrows", "Strzaly"), ("bolts", "Belty"), ("sling", "Pociski do procy"), ("other", "Inne")])]
    if sid == "alchemy":
        return [("alchemy_kind", "Typ", [("all", "Wszystkie"), ("bomb", "Bomby"), ("elixir", "Eliksiry"), ("tool", "Narzedzia")])]
    if sid == "gear":
        return [
            ("gear_kind", "Typ", [("all", "Wszystkie"), ("tools", "Narzedzia"), ("container", "Pojemniki"), ("light", "Swiatlo"), ("camp", "Obozowe"), ("adventuring", "Podroznicze")])
        ]
    if sid == "magic":
        return [("magic_kind", "Typ", [("all", "Wszystkie"), ("potion", "Mikstury"), ("scroll", "Zwoje"), ("talisman", "Talizmany"), ("water", "Holy/Unholy Water"), ("other", "Inne")])]
    return []


def _filter_offers_for_section(offers: list[dict[str, Any]], section_id: str, filters: dict[str, str]) -> list[dict[str, Any]]:
    sid = str(section_id or "").strip().lower()
    out = [dict(row) for row in offers if str(row.get("section") or "").strip().lower() == sid]
    for key, value in dict(filters or {}).items():
        selected = str(value or "").strip().lower()
        if not selected or selected == "all":
            continue
        if key == "trait":
            out = [
                row
                for row in out
                if selected
                in {
                    _normalize(str(raw or ""))
                    for raw in list(row.get("traits") or ())
                    if str(raw or "").strip()
                }
            ]
            continue
        out = [row for row in out if str(row.get(key) or "").strip().lower() == selected]
    return out


def _cycle_filter_value(filters: dict[str, str], key: str, allowed_values: list[str]) -> None:
    values = [str(item or "").strip().lower() for item in list(allowed_values or []) if str(item or "").strip()]
    if not values:
        return
    current = str(filters.get(key, values[0]) or values[0]).strip().lower()
    try:
        idx = values.index(current)
    except ValueError:
        idx = 0
    filters[key] = values[(idx + 1) % len(values)]


def _build_filter_options(section_id: str, filters: dict[str, str]) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    for key, label, values in _section_filter_specs(section_id):
        allowed = [item[0] for item in values]
        selected = str(filters.get(key, allowed[0] if allowed else "all") or "all").strip().lower()
        label_map = {item[0]: item[1] for item in values}
        current_label = label_map.get(selected, selected)
        options.append(
            {
                "id": f"__filter:{key}",
                "label": f"Filtr {label}: {current_label}",
                "desc": _structured_choice_desc(
                    name=f"Filtr {label}",
                    fluff="Przelacza wartosc filtra dla tej sekcji.",
                    mechanics=(
                        "Po potwierdzeniu Enter filtr przechodzi do kolejnej wartosci. "
                        "Lista ponizej odswieza sie automatycznie."
                    ),
                ),
            }
        )
    return options


def _run_starting_equipment_step(
    game,
    hero: Hero,
    *,
    class_id: str,
    image: str | None = None,
    on_refresh: Callable[[str, str], None] | None = None,
) -> None:
    def _emit_refresh(expected: str, mechanics: str) -> None:
        if not callable(on_refresh):
            return
        try:
            on_refresh(str(expected or "").strip(), str(mechanics or "").strip())
        except Exception:
            return

    set_actor_starting_money_gp(hero, _STARTING_GOLD_GP)
    hero.inventory = []
    hero.weapon_loadout = ["unarmed"]
    hero.armor_loadout = []
    hero.shield_loadout = []

    all_offers = [dict(row) for row in _STARTER_SHOP_OFFERS]
    section_filters = {
        str(section.get("id") or "").strip().lower(): _section_filter_state_defaults(str(section.get("id") or ""))
        for section in _SHOP_SECTIONS
    }
    purchases: dict[str, int] = {}
    purchase_history: list[tuple[str, str, int]] = []
    while True:
        money_text = format_actor_money(hero)
        bulk_summary = actor_bulk_summary(hero)
        options: list[dict[str, str]] = []
        for section in _SHOP_SECTIONS:
            section_id = str(section.get("id") or "").strip().lower()
            section_base = [row for row in all_offers if str(row.get("section") or "").strip().lower() == section_id]
            active = _filter_offers_for_section(section_base, section_id, section_filters.get(section_id, {}))
            options.append(
                {
                    "id": f"__section:{section_id}",
                    "label": f"{section.get('label')} ({len(active)}/{len(section_base)})",
                    "desc": _structured_choice_desc(
                        name=str(section.get("label") or section_id),
                        fluff=str(section.get("desc") or "Sekcja sklepu startowego."),
                        mechanics=(
                            f"Dostepne po filtrach: {len(active)} z {len(section_base)}. "
                            "Wejdz Enter, aby przegladac i kupowac przedmioty."
                        ),
                    ),
                }
            )
        options.append(
            {
                "id": "__finish_equipment__",
                "label": "Zakończ zakupy",
                "desc": _structured_choice_desc(
                    name="Zakoncz zakupy",
                    fluff="Konczy etap wyposazenia startowego.",
                    mechanics="Przechodzisz do kolejnych krokow tworzenia postaci i zamykasz liste zakupow.",
                    when="Gdy skonczysz kompletowac ekwipunek i chcesz przejsc dalej.",
                ),
            }
        )
        chosen = _pick_one(
            game,
            title="KROK 12: Ekwipunek startowy",
            subtitle=(
                f"Budżet: {money_text}. "
                f"Bulk: {bulk_summary['total_display']} / "
                f"{bulk_summary['encumbered_limit_display']} (encumbered)."
            ),
            source="character_creation",
            options=options,
            layout="menu_numpad",
            image=image,
            allow_back=True,
        )
        if _is_back_choice(chosen):
            if not purchase_history:
                _prompt_info(
                    game,
                    title="Ekwipunek",
                    text="Brak zakupów do cofnięcia.",
                    image=image,
                )
                continue
            last_offer_key, last_instance_id, last_cost_cp = purchase_history.pop()
            inventory = list(getattr(hero, "inventory", []) or [])
            removed_name = _labelize(last_offer_key.split(":", 1)[-1])
            removed = False
            for idx, row in enumerate(inventory):
                if str(getattr(row, "instance_id", "") or "") == last_instance_id:
                    removed_name = str(getattr(row, "name", "") or removed_name)
                    del inventory[idx]
                    removed = True
                    break
            if not removed and inventory:
                row = inventory.pop()
                removed_name = str(getattr(row, "name", "") or removed_name)
            hero.inventory = inventory
            purchases[last_offer_key] = max(0, int(purchases.get(last_offer_key, 0)) - 1)
            add_actor_cp(hero, int(last_cost_cp or 0))
            weapons, armors, shields = _loadouts_from_inventory(hero)
            hero.weapon_loadout = list(weapons)
            hero.armor_loadout = list(armors)
            hero.shield_loadout = list(shields)
            _equip_from_inventory_defaults(hero)
            refresh_actor_bulk_state(hero, inventory=inventory)
            _prompt_info(
                game,
                title="Cofnięto zakup",
                text=(
                    f"Usunięto: {removed_name}\n"
                    f"Zwrócono: {format_cp_value(last_cost_cp)}\n"
                    f"Środki: {format_actor_money(hero)}"
                ),
                image=image,
            )
            _emit_refresh(
                f"Cofnięto zakup: {removed_name}",
                "Ekwipunek i sakiewka zostały odświeżone po cofnięciu zakupu.",
            )
            continue
        if not chosen or chosen == "__finish_equipment__":
            break
        chosen_text = str(chosen or "").strip().lower()
        if not chosen_text.startswith("__section:"):
            continue
        section_id = chosen_text.split(":", 1)[1].strip().lower()
        section_meta = next((row for row in _SHOP_SECTIONS if str(row.get("id") or "").strip().lower() == section_id), None)
        if section_meta is None:
            continue
        section_base = [row for row in all_offers if str(row.get("section") or "").strip().lower() == section_id]
        active_filters = section_filters.setdefault(section_id, _section_filter_state_defaults(section_id))
        while True:
            filtered = _filter_offers_for_section(section_base, section_id, active_filters)
            section_options = _build_filter_options(section_id, active_filters)
            for offer in filtered:
                item = _create_shop_item(offer)
                if item is None:
                    continue
                cost_cp = item_cost_cp(str(offer.get("id") or ""))
                offer_key = _offer_key(offer)
                owned = int(purchases.get(offer_key, 0))
                section_options.append(
                    {
                        "id": f"__buy:{offer_key}",
                        "label": f"{_labelize(str(offer.get('id') or ''))} ({format_cp_value(cost_cp)})",
                        "desc": _item_choice_desc(offer, item, owned=owned),
                    }
                )
            if not filtered:
                section_options.append(
                    {
                        "id": "__no_items__",
                        "label": "Brak pozycji dla aktywnych filtrow",
                        "desc": _structured_choice_desc(
                            name="Brak pozycji",
                            fluff="Aktualne filtry ukrywaja wszystkie przedmioty w tej sekcji.",
                            mechanics="Zmien filtry (pierwsze opcje listy), aby pokazac pozycje.",
                        ),
                    }
                )
            section_options.append(
                {
                    "id": "__back_section__",
                    "label": "Wroc do sekcji",
                    "desc": _structured_choice_desc(
                        name="Powrot",
                        fluff="Powrot do glownych sekcji sklepu.",
                        mechanics="Nie zmienia stanu zakupow.",
                    ),
                }
            )
            chosen_item = _pick_one(
                game,
                title=f"KROK 12: {section_meta.get('label')}",
                subtitle=(
                    f"Budżet: {format_actor_money(hero)}. "
                    f"Bulk: {actor_bulk_summary(hero)['total_display']} / {actor_bulk_summary(hero)['encumbered_limit_display']} (encumbered). "
                    f"Pozycje: {len(filtered)}. "
                    "8/2: nawigacja w aktywnym panelu, 4/6: przełącz Filtry <-> Lista."
                ),
                source="character_creation",
                options=section_options,
                layout="menu_numpad",
                image=image,
                allow_back=True,
            )
            if _is_back_choice(chosen_item) or chosen_item == "__back_section__":
                break
            if not chosen_item:
                continue
            chosen_item_text = str(chosen_item).strip().lower()
            if chosen_item_text.startswith("__filter:"):
                filter_key = chosen_item_text.split(":", 1)[1].strip()
                specs = {key: values for key, _label, values in _section_filter_specs(section_id)}
                values = [value[0] for value in list(specs.get(filter_key, []))]
                _cycle_filter_value(active_filters, filter_key, values)
                continue
            if chosen_item_text == "__no_items__":
                continue
            if not chosen_item_text.startswith("__buy:"):
                continue
            buy_key = chosen_item_text.split(":", 1)[1].strip()
            offer = next((row for row in filtered if _offer_key(row) == buy_key), None)
            if offer is None:
                continue
            item = _create_shop_item(offer)
            if item is None:
                continue
            if str(getattr(item, "item_id", "") or "").strip().lower() == "scroll_common_rank1":
                from GameObjects.events.magic.consumables.events import prepare_common_rank1_scroll_purchase

                configured = prepare_common_rank1_scroll_purchase(
                    game,
                    item,
                    source="character_creation_scroll_common_rank1",
                    title="Kupujesz zwoj czaru 1. rangi",
                    subtitle="Najpierw wybierz czar zapisany na zwoju.",
                    prompt_long="Ten zakup tworzy konkretny zwoj z przypisanym czarem. Później używasz już gotowego zwoju, bez ponownego wyboru przy zakupie.",
                )
                if not configured:
                    continue
            cost_cp = item_cost_cp(str(offer.get("id") or ""))
            if not can_actor_afford_cp(hero, cost_cp):
                _prompt_info(
                    game,
                    title="Ekwipunek",
                    text=(
                        f"Brak srodkow na {_labelize(str(offer.get('id') or ''))}. "
                        f"Potrzeba {format_cp_value(cost_cp)}."
                    ),
                    image=image,
                )
                continue
            if not spend_actor_cp(hero, cost_cp):
                continue
            try:
                setattr(item, "price_cp", int(cost_cp))
            except Exception:
                pass
            add_item(hero, item)
            weapons, armors, shields = _loadouts_from_inventory(hero)
            hero.weapon_loadout = list(weapons)
            hero.armor_loadout = list(armors)
            hero.shield_loadout = list(shields)
            _equip_from_inventory_defaults(hero)
            purchases[buy_key] = int(purchases.get(buy_key, 0) + 1)
            purchase_history.append((buy_key, str(getattr(item, "instance_id", "") or ""), int(cost_cp or 0)))
            bulk = actor_bulk_summary(hero)
            _prompt_info(
                game,
                title="Zakupiono przedmiot",
                text=(
                    f"Dodano: {item_label(item)}\n"
                    f"Pozostale srodki: {format_actor_money(hero)}\n"
                    f"Bulk: {bulk['total_display']} / {bulk['encumbered_limit_display']} (encumbered)"
                ),
                image=image,
            )
            _emit_refresh(
                f"Dodano: {item_label(item)}",
                "Lista ekwipunku, stan rąk, Bulk i sakiewka zostały zaktualizowane.",
            )

    weapons, armors, shields = _loadouts_from_inventory(hero)
    hero.weapon_loadout = list(weapons)
    hero.armor_loadout = list(armors)
    hero.shield_loadout = list(shields)
    _equip_from_inventory_defaults(hero)
    refresh_actor_bulk_state(hero, inventory=list(getattr(hero, "inventory", []) or []))

    class_hint = {
        "fighter": "Wojownik zwykle chce: broń 1R + tarcza lub broń 2R i pancerz.",
        "rogue": "Łotrzyk zwykle chce: lekką zbroję i lekką broń (finesse).",
        "ranger": "Łowca zwykle chce: broń dystansową albo dwa lekkie ostrza.",
        "wizard": "Mag zwykle chce: lekki ekwipunek i zachowany budżet na przyszłe zakupy.",
        "cleric": "Kapłan zwykle chce: broń prostą, tarczę i pancerz zgodny z biegłością.",
    }.get(str(class_id or "").strip().lower(), "Dobierz ekwipunek pod styl gry i biegłości klasy.")
    _prompt_info(
        game,
        title="Podsumowanie ekwipunku",
        text=(
            f"Środki po zakupach: {format_actor_money(hero)}\n"
            f"Bulk całkowity: {actor_bulk_summary(hero)['total_display']}\n"
            f"Broń loadout: {', '.join(_labelize(item) for item in hero.weapon_loadout)}\n"
            f"Pancerze: {', '.join(_labelize(item) for item in hero.armor_loadout) or '-'}\n"
            f"Tarcze: {', '.join(_labelize(item) for item in hero.shield_loadout) or '-'}\n"
            f"Wskazówka: {class_hint}"
        ),
        image=image,
    )
    _emit_refresh(
        "Zakończono zakupy startowe.",
        "Sekcja ekwipunku pokazuje finalny stan przed przejściem dalej.",
    )


def _status_choice_desc(status: Status | None, fallback: str) -> str:
    if status is None:
        return _structured_choice_desc(
            name=_labelize("wybor"),
            fluff=fallback,
            mechanics="Brak danych statusu.",
        )
    data = getattr(status, "data", None) or {}
    status_name = _labelize(getattr(status, "id", "") or getattr(status, "label", "") or "wybor")
    fluff_default = _first_line(data.get("ui_description")) or _first_line(data.get("ui_prompt_long")) or fallback
    when_default = "Po wybraniu tej opcji."
    if bool(data.get("is_background")):
        ability_ui = _trim_text(data.get("background_ability_boosts_ui"), max_len=280)
        skill_ui = _trim_text(data.get("background_skill_training_ui"), max_len=280)

        feat_id = str(data.get("background_feat_id") or "").strip().lower()
        feat_status = resolve_status(feat_id) if feat_id else None
        if feat_status is None:
            grants = list(data.get("grants_statuses") or [])
            if grants:
                first = grants[0]
                if isinstance(first, Status):
                    feat_status = first
        feat_label = _labelize(feat_id) if feat_id else (_labelize(getattr(feat_status, "id", "")) if feat_status is not None else "")
        feat_effect = _trim_text(_status_mechanics_short(feat_status), max_len=260)

        mechanics_parts: list[str] = []
        if ability_ui:
            mechanics_parts.append(f"Boosty cech: {ability_ui}")
        if skill_ui:
            mechanics_parts.append(f"Skill/Lore: {skill_ui}")
        if feat_label:
            mechanics_parts.append(f"Gwarantowany feat: {feat_label}")
        if feat_effect:
            mechanics_parts.append(f"Efekt featu: {feat_effect}")
        mechanics_text = "\n".join(f"- {part}" for part in mechanics_parts if part) or "Background dodaje boosty, skill/Lore i feat."
        return _structured_choice_desc(
            name=status_name,
            fluff=fluff_default,
            mechanics=mechanics_text,
            when=when_default,
        )

    short = _status_mechanics_short(status)
    desc = str(_status_description(status) or "").strip()
    if not desc or desc == "Brak dodatkowego opisu.":
        desc = fallback
    mechanics_text = _trim_text(short or desc, max_len=460) or fallback
    return _structured_choice_desc(
        name=status_name,
        fluff=fluff_default,
        mechanics=mechanics_text,
        when=None,
    )


def _rank_label_pl(rank: str | None) -> str:
    raw = _normalize(rank)
    mapping = {
        "untrained": "niewyszkolony",
        "trained": "wyszkolony",
        "expert": "ekspert",
        "master": "mistrz",
        "legendary": "legendarny",
    }
    return mapping.get(raw, _labelize(raw))


def _class_key_ability_choices(class_id: str, status: Status | None) -> list[str]:
    if status is None:
        fallback = _normalize(CLASS_KEY_ABILITY_DEFAULT.get(class_id, "strength"))
        return [fallback] if fallback else []
    data = getattr(status, "data", None) or {}
    choices: list[str] = []
    for key in (f"{class_id}_key_ability_choices", "key_ability_choices"):
        raw = list(data.get(key) or [])
        for item in raw:
            ability = _normalize(item)
            if ability in ABILITY_IDS and ability not in choices:
                choices.append(ability)
    if not choices:
        fallback = _normalize(CLASS_KEY_ABILITY_DEFAULT.get(class_id, "strength"))
        if fallback:
            choices.append(fallback)
    return choices


def _format_prof_line_pl(mapping: dict[str, str], order: list[str], labels: dict[str, str]) -> str:
    parts: list[str] = []
    for key in order:
        if key in mapping:
            parts.append(f"{labels.get(key, _labelize(key))}: {_rank_label_pl(mapping.get(key))}")
    for key in mapping:
        if key not in order:
            parts.append(f"{labels.get(key, _labelize(key))}: {_rank_label_pl(mapping.get(key))}")
    return ", ".join(parts) if parts else "brak"


def _class_mechanics_desc_pl(class_id: str, status: Status | None) -> str:
    data = getattr(status, "data", None) if status is not None else {}
    data = data or {}

    class_hp = int(data.get("class_hp") or 0)
    key_choices = _class_key_ability_choices(class_id, status)
    key_txt = ", ".join(_labelize(item) for item in key_choices) if key_choices else "brak"

    perception_rank = _rank_label_pl(CLASS_PERCEPTION_RANK.get(class_id, "trained"))
    save_map = dict(CLASS_SAVE_RANKS.get(class_id, {}))
    weapon_map = dict(CLASS_WEAPON_PROFICIENCY.get(class_id, {}))
    defense_map = dict(CLASS_DEFENSE_PROFICIENCY.get(class_id, {}))
    skill_rule = dict(CLASS_SKILL_RULES.get(class_id, {"fixed": [], "additional": 0}) or {})
    fixed_skills = [_normalize(item) for item in list(skill_rule.get("fixed") or []) if _normalize(item)]
    additional = max(0, int(skill_rule.get("additional") or 0))
    feat_choices = list(CLASS_FEAT_CHOICES_MANUAL.get(class_id, []) or [])

    save_line = _format_prof_line_pl(
        save_map,
        ["fortitude", "reflex", "will"],
        {"fortitude": "Fortitude", "reflex": "Reflex", "will": "Will"},
    )
    weapon_line = _format_prof_line_pl(
        weapon_map,
        ["simple", "martial", "advanced", "unarmed"],
        {
            "simple": "bronie proste",
            "martial": "bronie wojenne",
            "advanced": "bronie zaawansowane",
            "unarmed": "ataki bez broni",
        },
    )
    defense_line = _format_prof_line_pl(
        defense_map,
        ["unarmored", "light", "medium", "heavy"],
        {
            "unarmored": "bez pancerza",
            "light": "pancerz lekki",
            "medium": "pancerz sredni",
            "heavy": "pancerz ciezki",
        },
    )
    fixed_skills_txt = ", ".join(_labelize(item) for item in fixed_skills) if fixed_skills else "brak"

    setup_hints = {
        "fighter": "Dalsze wybory: key ability i feat klasowy poziomu 1.",
        "rogue": "Dalsze wybory: racket, key ability i feat klasowy poziomu 1.",
        "wizard": "Dalsze wybory: szkola/uniwersalista, teza, bond oraz feat klasowy poziomu 1.",
        "cleric": "Dalsze wybory: bóstwo, doktryna, domena, font i bron ulubiona.",
        "barbarian": "Dalsze wybory: instinct i feat klasowy poziomu 1.",
        "ranger": "Dalsze wybory: key ability, hunter's edge i feat klasowy poziomu 1.",
        "bard": "Dalsze wybory: Muse i feat klasowy poziomu 1.",
        "alchemist": "Dalsze wybory: research field i feat klasowy poziomu 1.",
        "champion": "Dalsze wybory: key ability, cause, bóstwo, bron ulubiona i font.",
        "druid": "Dalsze wybory: order, key ability i feat klasowy poziomu 1.",
        "monk": "Dalsze wybory: key ability i feat klasowy poziomu 1.",
        "sorcerer": "Dalsze wybory: bloodline i feat klasowy poziomu 1.",
    }
    feat_txt = (
        ", ".join(_labelize(item) for item in feat_choices)
        if feat_choices
        else "wg setupu klasy"
    )

    return "\n".join(
        [
            f"- HP klasy: {class_hp}",
            f"- Key Ability: {key_txt}",
            f"- Percepcja: {perception_rank}",
            f"- Rzuty obronne: {save_line}",
            f"- Bieglosc broni: {weapon_line}",
            f"- Bieglosc obrony/pancerzy: {defense_line}",
            f"- Skille stale: {fixed_skills_txt}",
            f"- Dodatkowe skille: {additional} (+ modyfikator INT, minimum 0)",
            f"- Featy klasowe poziomu 1: {feat_txt}",
            f"- Dalsze wybory: {setup_hints.get(class_id, 'Pojawia sie w kolejnych krokach.')}",
        ]
    )


def _ancestry_mechanics_desc_pl(status: Status | None) -> str:
    if status is None:
        return "Brak danych ancestry."
    data = getattr(status, "data", None) or {}
    hp = int(data.get("ancestry_hp") or 0)
    speed = int(data.get("base_speed_feet") or 0)
    boosts_raw, flaw_raw = _ancestry_boosts_and_flaw(status)
    langs_raw = [str(item).strip() for item in list(data.get("ancestry_languages") or []) if str(item).strip()]
    bonus_langs_raw = [str(item).strip() for item in list(data.get("ancestry_bonus_languages") or []) if str(item).strip()]
    traits_raw = [str(item).strip() for item in list(data.get("ancestry_traits") or []) if str(item).strip()]
    grants_raw = list(data.get("grants_statuses") or [])
    ability_pl = {
        "strength": "Siła",
        "dexterity": "Zręczność",
        "constitution": "Kondycja",
        "intelligence": "Inteligencja",
        "wisdom": "Mądrość",
        "charisma": "Charyzma",
        "free": "Dowolna",
    }
    boosts = [ability_pl.get(item, _labelize(item)) for item in boosts_raw] or ["Brak"]
    flaw = ability_pl.get(flaw_raw, _labelize(flaw_raw)) if flaw_raw else "Brak"
    langs = ", ".join(_labelize(item) for item in langs_raw) if langs_raw else "Brak"
    bonus_langs = ", ".join(_labelize(item) for item in bonus_langs_raw) if bonus_langs_raw else ""
    traits = ", ".join(_labelize(item) for item in traits_raw) if traits_raw else "Brak"
    grants: list[str] = []
    for item in grants_raw:
        sid = ""
        if isinstance(item, Status):
            sid = str(item.id or "").strip()
        elif hasattr(item, "id"):
            sid = str(getattr(item, "id", "") or "").strip()
        elif isinstance(item, str):
            sid = str(item).strip()
        if sid:
            grants.append(_labelize(sid))
    grants_txt = ", ".join(dict.fromkeys(grants)) if grants else ""
    lines = [
        f"- HP ancestry: {hp}",
        f"- Predkosc bazowa: {speed} stop",
        f"- Boosty atrybutow: {', '.join(boosts)}",
        f"- Wada atrybutu: {flaw}",
        f"- Jezyki startowe: {langs}",
        f"- Cechy: {traits}",
    ]
    if bonus_langs:
        lines.append(f"- Dodatkowe jezyki (przy dodatnim INT): {bonus_langs}")
    if grants_txt:
        lines.append(f"- Nadawane statusy/cechy: {grants_txt}")
    return "\n".join(lines)


def _ancestry_fluff_sentence(ancestry_id: str, status: Status | None = None) -> str:
    mapping = {
        "human": "Ludzie sa wszechstronni i szybko dostosowuja sie do nowych wyzwan.",
        "elf": "Elfy lacza dlugowiecznosc, zmyslowosc i talent do subtelnej magii oraz sztuki.",
        "dwarf": "Krasnoludy sa twarde, wytrwale i wychowane w tradycji klanowej.",
        "gnome": "Gnomy sa ciekawe swiata, zywiolowe i napedzane nieustanna potrzeba nowych wrazen.",
        "goblin": "Gobliny sa impulsywne, zadziorne i niezwykle pomyslowe w walce o przetrwanie.",
        "halfling": "Niziolki sa zreczne, pogodne i zaskakujaco odporne w trudnych warunkach.",
    }
    aid = _normalize(ancestry_id)
    if aid in mapping:
        return mapping[aid]
    if status is not None:
        data = getattr(status, "data", None) or {}
        raw = _first_line(data.get("ui_prompt_long")) or _first_line(data.get("ui_description"))
        if raw and "punkty zycia" not in raw.lower():
            return raw
    return "Twoje pochodzenie definiuje kulture, cechy rasowe i tempo rozwoju postaci."


def _collect_status_ids(hero: Hero) -> list[str]:
    out: list[str] = []
    for status in list(getattr(hero, "statuses", []) or []):
        sid = str(getattr(status, "id", "") or "").strip().lower()
        if sid and sid not in out:
            out.append(sid)
    return out


def _collect_status_data(hero: Hero) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for status in list(getattr(hero, "statuses", []) or []):
        sid = str(getattr(status, "id", "") or "").strip().lower()
        data = getattr(status, "data", None)
        if sid and isinstance(data, dict):
            out[sid] = dict(data)
    return out


def _trained_skills_from_statuses(hero: Hero) -> set[str]:
    getter = getattr(hero, "_trained_skill_ids", None)
    if callable(getter):
        try:
            return {
                skill_id
                for skill_id in set(getter() or set())
                if skill_id in CORE_SKILL_IDS
            }
        except Exception:
            return set()
    return set()


def _normalize_lore_name(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if "_" in raw:
        raw = raw.replace("_", " ")
    label = _labelize(raw)
    return str(label or raw).strip() or None


def _lore_skills_from_statuses(hero: Hero) -> list[str]:
    out: list[str] = []
    for status in list(getattr(hero, "statuses", []) or []):
        data = getattr(status, "data", None) or {}
        for key in ("trained_lore_skills", "trained_lore", "lore_skills"):
            for item in list(data.get(key) or []):
                normalized = _normalize_lore_name(item)
                if normalized and normalized not in out:
                    out.append(normalized)
    return out


def _status_rank_overrides(hero: Hero, *, level: int) -> tuple[dict[str, str], dict[str, str], str | None]:
    skill_updates: dict[str, str] = {}
    save_updates: dict[str, str] = {}
    perception_rank: str | None = None

    def _merge_skill(skill_id: object, rank: object) -> None:
        sid = _normalize(str(skill_id))
        if sid not in CORE_SKILL_IDS:
            return
        current = skill_updates.get(sid, "untrained")
        skill_updates[sid] = higher_rank(current, str(rank or "untrained"))

    def _merge_save(save_id: object, rank: object) -> None:
        sid = _normalize(str(save_id))
        if sid not in {"fortitude", "reflex", "will"}:
            return
        current = save_updates.get(sid, "untrained")
        save_updates[sid] = higher_rank(current, str(rank or "untrained"))

    def _rank_from_progression(
        progression: dict[object, object] | None,
        *,
        level_value: int,
        default_rank: str = "trained",
    ) -> str:
        selected = str(default_rank or "trained")
        for level_key, rank in dict(progression or {}).items():
            try:
                threshold = int(str(level_key).strip())
            except Exception:
                continue
            if int(level_value) >= threshold:
                selected = higher_rank(selected, str(rank or selected))
        return selected

    for status in list(getattr(hero, "statuses", []) or []):
        data = getattr(status, "data", None) or {}
        for skill_id, rank in dict(data.get("skill_ranks") or {}).items():
            _merge_skill(skill_id, rank)
        for save_id, rank in dict(data.get("save_ranks") or {}).items():
            _merge_save(save_id, rank)

        status_perception = str(data.get("perception_rank") or "").strip().lower()
        if status_perception:
            if perception_rank is None or rank_priority(status_perception) > rank_priority(perception_rank):
                perception_rank = status_perception

        for key in ("trained_skills", "skills_trained"):
            for skill_id in list(data.get(key) or []):
                _merge_skill(skill_id, "trained")

        if str(getattr(status, "id", "") or "").strip().lower() == "canny_acumen":
            chosen = _normalize(str(data.get("canny_acumen_choice") or ""))
            if not chosen:
                continue
            rank = str(data.get("canny_acumen_rank") or "expert")
            rank_at_17 = str(data.get("canny_acumen_rank_at_17") or rank)
            selected_rank = rank_at_17 if int(level or 1) >= 17 else rank
            if chosen == "perception":
                if perception_rank is None or rank_priority(selected_rank) > rank_priority(perception_rank):
                    perception_rank = selected_rank
            else:
                _merge_save(chosen, selected_rank)

        if str(getattr(status, "id", "") or "").strip().lower() == "skilled_heritage":
            chosen_skill = _normalize(str(data.get("skilled_heritage_skill") or ""))
            if chosen_skill in CORE_SKILL_IDS:
                selected_rank = _rank_from_progression(
                    dict(data.get("skilled_heritage_progression") or {}),
                    level_value=int(level or 1),
                    default_rank="trained",
                )
                _merge_skill(chosen_skill, selected_rank)

    return skill_updates, save_updates, perception_rank


def _ancestry_boosts_and_flaw(ancestry_status: Status) -> tuple[list[str], str | None]:
    data = ancestry_status.data or {}
    boosts = list(data.get("ability_boosts") or [])
    flaw = str(data.get("ability_flaw") or "").strip().lower() or None
    if boosts:
        return [str(item).strip().lower() for item in boosts if str(item).strip()], flaw
    fallback = _ANCESTRY_FALLBACK.get(str(ancestry_status.id).strip().lower(), {})
    return list(fallback.get("boosts") or []), str(fallback.get("flaw") or "") or None


def _pick_ability(
    game,
    *,
    title: str,
    subtitle: str,
    allowed: list[str],
    source: str,
    image: str | None = None,
    allow_back: bool = False,
) -> str | None:
    options = []
    for ability_id in allowed:
        options.append(
            {
                "id": ability_id,
                "label": _labelize(ability_id),
                "desc": localized_hint_pl(ability_id) or "Wybierz te ceche.",
            }
        )
    return _pick_one(
        game,
        title=title,
        subtitle=subtitle,
        source=source,
        options=options,
        image=image,
        allow_back=allow_back,
    )


def _selected_class_key_ability(hero: Hero, class_id: str) -> str:
    direct_attr = getattr(hero, f"{class_id}_key_ability", None)
    normalized = _normalize(direct_attr)
    if normalized in ABILITY_IDS:
        return normalized
    status_obj = next(
        (item for item in list(getattr(hero, "statuses", []) or []) if getattr(item, "id", None) == class_id),
        None,
    )
    data = getattr(status_obj, "data", None) or {}
    setup = data.get(f"{class_id}_setup")
    if isinstance(setup, dict):
        normalized = _normalize(setup.get("key_ability"))
        if normalized in ABILITY_IDS:
            return normalized
    fallback = _normalize(data.get(f"{class_id}_key_ability"))
    if fallback in ABILITY_IDS:
        return fallback
    return CLASS_KEY_ABILITY_DEFAULT.get(class_id, "strength")


def _pick_additional_skills(
    game,
    *,
    amount: int,
    exclude: set[str],
    source: str,
    image: str | None = None,
    on_change: Callable[[list[str]], None] | None = None,
) -> list[str]:
    amount = max(0, int(amount))
    if amount <= 0:
        return []
    picked: list[str] = []
    while len(picked) < amount:
        idx = len(picked)
        pool = [skill for skill in CORE_SKILL_IDS if skill not in exclude and skill not in picked]
        if not pool:
            break
        options = [{"id": item, "label": _labelize(item), "desc": "Dodatkowy trained skill."} for item in pool]
        chosen = _pick_one(
            game,
            title=f"KROK 9: Dodatkowy skill {idx + 1}/{amount}",
            subtitle="Co wybierasz: dodatkowy trained skill z klasy. Mechanika: podnosi poziom skilla do trained.",
            source=source,
            options=options,
            image=image,
            allow_back=True,
        )
        if _is_back_choice(chosen):
            if picked:
                picked.pop()
                if callable(on_change):
                    on_change(list(picked))
            continue
        if not chosen:
            chosen = pool[0]
        picked.append(chosen)
        if callable(on_change):
            on_change(list(picked))
    return picked


def _resolve_background_training_choice(
    game,
    *,
    background_status_id: str,
    already_trained: set[str],
    image: str | None = None,
) -> tuple[str | None, str | None]:
    training = background_training(background_status_id)
    if training is None:
        return None, None

    skill_id: str | None
    if len(training.skill_choices) == 1:
        skill_id = training.skill_choices[0]
    else:
        options = [{"id": item, "label": _labelize(item), "desc": "Wybór skilla z backgroundu."} for item in training.skill_choices]
        skill_id = _pick_one(
            game,
            title="KROK 9: Skill z Backgroundu",
            subtitle="Co wybierasz: skill z backgroundu. Mechanika: skill staje sie trained.",
            source="character_creation",
            options=options,
            image=image,
            allow_back=True,
        )
        if _is_back_choice(skill_id):
            skill_id = None
        if not skill_id and training.skill_choices:
            skill_id = training.skill_choices[0]

    if skill_id in already_trained:
        replacement_pool = [item for item in CORE_SKILL_IDS if item not in already_trained]
        if replacement_pool:
            options = [{"id": item, "label": _labelize(item), "desc": "Skill zastępczy za duplikat z klasy."} for item in replacement_pool]
            replacement = _pick_one(
                game,
                title="KROK 9: Duplikat trained skilla",
                subtitle="Duplikat skilla z klasy. Wybierz zamiennik; mechanika: zamiast duplikatu dostajesz inny trained skill.",
                source="character_creation",
                options=options,
                image=image,
                allow_back=True,
            )
            if replacement and not _is_back_choice(replacement):
                skill_id = replacement

    lore_name: str | None = training.lore_template
    if training.requires_lore_input:
        template = str(training.lore_template)
        if template == "{legal_or_warfare}":
            chosen = _pick_one(
                game,
                title="KROK 9: Lore z Backgroundu",
                subtitle="Co wybierasz: specjalizacje Lore z backgroundu. Mechanika: dodaje trained w wybranym Lore.",
                source="character_creation",
                options=[
                    {"id": "Legal Lore", "label": "Legal Lore", "desc": "Prawo i procedury."},
                    {"id": "Warfare Lore", "label": "Warfare Lore", "desc": "Wiedza o wojnie."},
                ],
                image=image,
                allow_back=True,
            )
            lore_name = "Legal Lore" if _is_back_choice(chosen) else (chosen or "Legal Lore")
        elif template == "{genealogy_or_heraldry}":
            chosen = _pick_one(
                game,
                title="KROK 9: Lore z Backgroundu",
                subtitle="Co wybierasz: specjalizacje Lore z backgroundu. Mechanika: dodaje trained w wybranym Lore.",
                source="character_creation",
                options=[
                    {"id": "Genealogy Lore", "label": "Genealogy Lore", "desc": "Rodowody i linie rodowe."},
                    {"id": "Heraldry Lore", "label": "Heraldry Lore", "desc": "Herby i symbole rodowe."},
                ],
                image=image,
                allow_back=True,
            )
            lore_name = "Genealogy Lore" if _is_back_choice(chosen) else (chosen or "Genealogy Lore")
        else:
            fill = _prompt_text(
                game,
                title="Podaj temat Lore (np. Forest, Absalom, Desert):",
                source="character_creation",
                default="General",
                image=image,
                allow_back=True,
            )
            if _is_back_choice(fill):
                fill = "General"
            lore_name = template.format(terrain=fill, city=fill)
    return skill_id, lore_name


def _extract_languages_traits_speed(ancestry_status: Status) -> tuple[list[str], list[str], int, int]:
    data = ancestry_status.data or {}
    langs = [str(item).strip().lower() for item in list(data.get("ancestry_languages") or []) if str(item).strip()]
    traits = [str(item).strip().lower() for item in list(data.get("ancestry_traits") or []) if str(item).strip()]
    speed = int(data.get("base_speed_feet") or 25)
    ancestry_hp = int(data.get("ancestry_hp") or 6)
    return langs, traits, speed, ancestry_hp


def _update_live_creation_sheet(
    game,
    hero: Hero,
    *,
    ancestry_status: Status,
    class_status: Status,
    class_id: str,
    ability_scores: dict[str, int],
    trained_core: set[str],
    lore_skills: list[str],
    stage: str,
    expected: str,
    mechanics: str,
) -> None:
    """Przelicz i wyślij live podgląd arkusza postaci do lewego panelu."""
    languages, traits, base_speed, ancestry_hp = _extract_languages_traits_speed(ancestry_status)
    class_hp = int((class_status.data or {}).get("class_hp") or 8)

    skill_ranks = {skill_id: "trained" for skill_id in set(trained_core) if skill_id in CORE_SKILL_IDS}
    perception_rank = str(CLASS_PERCEPTION_RANK.get(class_id, "trained") or "trained")
    save_ranks = dict(
        CLASS_SAVE_RANKS.get(
            class_id,
            {"fortitude": "trained", "reflex": "trained", "will": "trained"},
        )
    )
    status_skill_updates, status_save_updates, status_perception_rank = _status_rank_overrides(hero, level=1)
    skill_ranks = merge_rank_maps(
        skill_ranks,
        status_skill_updates,
        allowed_keys=CORE_SKILL_IDS,
        sparse=True,
    )
    save_ranks = merge_rank_maps(
        save_ranks,
        status_save_updates,
        allowed_keys=("fortitude", "reflex", "will"),
        sparse=True,
    )
    if status_perception_rank and rank_priority(status_perception_rank) > rank_priority(perception_rank):
        perception_rank = status_perception_rank

    weapon_ranks = dict(CLASS_WEAPON_PROFICIENCY.get(class_id, {}))
    defense_ranks = dict(CLASS_DEFENSE_PROFICIENCY.get(class_id, {}))
    unarmored_rank = str(defense_ranks.get("unarmored", "trained"))

    math = compute_math(
        level=1,
        ability_scores=dict(ability_scores),
        skill_ranks=skill_ranks,
        perception_rank=perception_rank,
        save_ranks=save_ranks,
        ancestry_hp=ancestry_hp,
        class_hp=class_hp,
        speed_feet=base_speed,
        unarmored_rank=unarmored_rank,
    )
    apply_math_to_hero(
        hero,
        math,
        weapon_proficiency_ranks=weapon_ranks,
        defense_proficiency_ranks=defense_ranks,
        trained_skills=sorted(set(trained_core) | set(skill_ranks.keys())),
        lore_skills=list(lore_skills),
    )
    hero.languages = list(dict.fromkeys(languages))
    hero.traits = list(dict.fromkeys(traits))
    _notify_creation_progress(
        game,
        hero,
        stage=stage,
        expected=expected,
        mechanics=mechanics,
    )


def _build_snapshot(
    *,
    hero: Hero,
    character_id: str,
    name: str,
    concept: str,
    ancestry_id: str,
    heritage_id: str,
    ancestry_feat_id: str,
    background_id: str,
    class_id: str,
    class_feat_ids: list[str],
) -> dict[str, Any]:
    raw_base_speed_feet, display_speed_feet = _speed_snapshot_values(hero)
    coin_pouch = normalize_coin_pouch(getattr(hero, "coin_pouch", None))
    equipped_weapon_ids = []
    for weapon in list(get_equipped_weapons(hero) or []):
        wid = normalize_weapon_id(getattr(weapon, "item_id", None))
        if wid and wid not in equipped_weapon_ids:
            equipped_weapon_ids.append(wid)
    equipped_armor_id = ""
    equipped_armor_instance = str(getattr(hero, "equipped_armor_item_id", "") or "")
    for item in list(getattr(hero, "inventory", []) or []):
        if str(getattr(item, "instance_id", "") or "") == equipped_armor_instance:
            aid = normalize_armor_id(getattr(item, "item_id", None))
            if aid:
                equipped_armor_id = aid
            break
    equipped_shield = getattr(hero, "equipped_shield", None)
    equipped_shield_id = normalize_shield_id(getattr(equipped_shield, "item_id", None)) if equipped_shield is not None else ""
    stored_skill_ranks = compress_rank_map(getattr(hero, "skill_ranks", {}) or {}, allowed_keys=CORE_SKILL_IDS)
    stored_trained_skills = sorted(
        {
            _normalize(item)
            for item in list(getattr(hero, "trained_skills", []) or [])
            if _normalize(item) in CORE_SKILL_IDS
        }
        | set(stored_skill_ranks.keys())
        | _trained_skills_from_statuses(hero)
    )
    stored_lore_skills: list[str] = []
    for item in list(getattr(hero, "lore_skills", []) or []):
        normalized = _normalize_lore_name(item)
        if normalized and normalized not in stored_lore_skills:
            stored_lore_skills.append(normalized)
    for item in _lore_skills_from_statuses(hero):
        if item not in stored_lore_skills:
            stored_lore_skills.append(item)

    return {
        "character_id": character_id,
        "name": name,
        "concept": concept,
        "level": int(getattr(hero, "level", 1) or 1),
        "ancestry_id": ancestry_id,
        "heritage_id": heritage_id,
        "ancestry_feat_id": ancestry_feat_id,
        "background_id": background_id,
        "class_id": class_id,
        "class_feat_ids": list(class_feat_ids),
        "portrait_image": str(getattr(hero, "image", "") or ""),
        "status_ids": _collect_status_ids(hero),
        "status_data": _collect_status_data(hero),
        "ability_scores": dict(getattr(hero, "ability_scores", {}) or {}),
        "ability_modifiers": dict(getattr(hero, "ability_modifiers", {}) or {}),
        "skill_ranks": stored_skill_ranks,
        "skill_modifiers": dict(getattr(hero, "skill_modifiers", {}) or {}),
        "trained_skills": stored_trained_skills,
        "lore_skills": stored_lore_skills,
        "languages": list(getattr(hero, "languages", []) or []),
        "traits": list(getattr(hero, "traits", []) or []),
        "perception_rank": str(getattr(hero, "perception_rank", "untrained") or "untrained"),
        "perception_bonus": int(getattr(hero, "perception_bonus", 0) or 0),
        "focus_point": int(getattr(hero, "focus_point", 0) or 0),
        "focus_pool_max": int(getattr(hero, "focus_pool_max", 0) or 0),
        "save_ranks": compress_rank_map(
            getattr(hero, "save_ranks", {}) or {},
            allowed_keys=("fortitude", "reflex", "will"),
        ),
        "fortitude_bonus": int(getattr(hero, "fortitude_bonus", 0) or 0),
        "reflex_bonus": int(getattr(hero, "reflex_bonus", 0) or 0),
        "will_bonus": int(getattr(hero, "will_bonus", 0) or 0),
        "weapon_proficiency_ranks": compress_rank_map(getattr(hero, "weapon_proficiency_ranks", {}) or {}),
        "defense_proficiency_ranks": compress_rank_map(getattr(hero, "defense_proficiency_ranks", {}) or {}),
        "max_hp": int(getattr(hero, "max_hp", 1) or 1),
        "base_speed_feet": int(raw_base_speed_feet or 25),
        "speed_feet": int(display_speed_feet),
        "ac": int(getattr(hero, "ac", 10) or 10),
        "starting_gold_gp": int(getattr(hero, "starting_gold_gp", _STARTING_GOLD_GP) or _STARTING_GOLD_GP),
        "coin_pouch": dict(coin_pouch),
        "track_ammo": bool(getattr(hero, "track_ammo", False)),
        "inventory_items": _serialize_inventory(hero),
        "weapon_loadout": list(getattr(hero, "weapon_loadout", []) or []),
        "armor_loadout": list(getattr(hero, "armor_loadout", []) or []),
        "shield_loadout": list(getattr(hero, "shield_loadout", []) or []),
        "equipped_weapon_ids": list(equipped_weapon_ids),
        "equipped_armor_id": str(equipped_armor_id or ""),
        "equipped_shield_id": str(equipped_shield_id or ""),
        "equipped_armor_item_id": str(getattr(hero, "equipped_armor_item_id", "") or ""),
        "equipped_shield_hand": str(getattr(hero, "equipped_shield_hand", "") or ""),
        "created_at": _now_iso(),
    }


@dataclass
class CharacterCreationResult:
    hero: Hero
    snapshot: dict[str, Any]


def create_character(game, repository: CharacterRepository) -> CharacterCreationResult | None:
    from hero import Hero
    hero = Hero()
    hero.level = 1
    hero.wounds = 0
    hero.temp_hp = 0
    hero.track_ammo = True
    hero.character_creation_in_progress = True
    set_actor_starting_money_gp(hero, _STARTING_GOLD_GP)
    selected: dict[str, Any] = {
        "portrait_image": "/static/placeholder.png",
        "name": "Bohater",
        "concept": "",
        "ancestry_id": "",
        "heritage_id": "",
        "ancestry_feat_id": "",
        "background_id": "",
        "class_id": "",
        "barbarian_instinct_id": "",
        "manual_class_feat_id": "",
    }

    wizard_steps = [
        "portrait",
        "name",
        "ancestry",
        "heritage",
        "ancestry_feat",
        "background",
        "class",
        "barbarian_instinct",
        "class_feat",
    ]
    _sync_creation_preview_from_selected(hero, selected)
    _notify_creation_progress(
        game,
        hero,
        stage="Kreator postaci",
        expected="Wybieraj kolejne kroki tworzenia bohatera.",
        mechanics="Lewy panel pokazuje bieżący podgląd tworzonej postaci.",
    )
    step_index = 0
    while step_index < len(wizard_steps):
        step = wizard_steps[step_index]
        allow_back = step_index > 0

        if step == "portrait":
            portrait = _pick_portrait_image(game, allow_back=allow_back)
            if _is_back_choice(portrait):
                step_index = max(0, step_index - 1)
                continue
            selected["portrait_image"] = str(portrait or "/static/placeholder.png")
            _sync_creation_preview_from_selected(hero, selected)
            _notify_creation_progress(
                game,
                hero,
                stage="KROK 0: Portret",
                expected="Wybierz obraz postaci.",
                mechanics="Portret jest zapisywany i pokazywany w UI gry.",
            )
            step_index += 1
            continue

        if step == "name":
            hero.image = str(selected.get("portrait_image") or hero.image or "/static/placeholder.png")
            raw_name = _prompt_text(
                game,
                title="Podaj imię postaci:",
                source="character_creation",
                default=str(selected.get("name") or "Bohater"),
                image=hero.image,
                allow_back=allow_back,
            )
            if _is_back_choice(raw_name):
                step_index = max(0, step_index - 1)
                continue
            selected["name"] = str(raw_name).strip() or "Bohater"
            _sync_creation_preview_from_selected(hero, selected)
            _notify_creation_progress(
                game,
                hero,
                stage="KROK 0B: Imie",
                expected="Podaj nazwe bohatera.",
                mechanics="Imie bedzie uzywane w logach, turach i zapisach postaci.",
            )
            step_index += 1
            continue

        if step == "ancestry":
            hero.image = str(selected.get("portrait_image") or hero.image or "/static/placeholder.png")
            ancestry_options = []
            for ancestry_id in ANCESTRY_IDS:
                status = resolve_status(ancestry_id)
                if status is None:
                    continue
                ancestry_options.append(
                    {
                        "id": ancestry_id,
                        "label": _labelize(ancestry_id),
                        "desc": _structured_choice_desc(
                            name=_labelize(ancestry_id),
                            fluff=_ancestry_fluff_sentence(ancestry_id, status),
                            mechanics=_ancestry_mechanics_desc_pl(status),
                            when="Natychmiast po potwierdzeniu wyboru ancestry.",
                        ),
                    }
                )
            ancestry_id = _pick_one(
                game,
                title="KROK 2: Wybór Ancestry",
                subtitle="Co wybierasz: pochodzenie postaci. Mechanika: HP ancestry, speed, boosty/flaw i cechy rasowe.",
                source="character_creation",
                options=ancestry_options,
                layout="menu_numpad",
                image=hero.image,
                allow_back=allow_back,
            )
            if _is_back_choice(ancestry_id):
                step_index = max(0, step_index - 1)
                continue
            if not ancestry_id:
                continue
            selected["ancestry_id"] = str(ancestry_id)
            selected["heritage_id"] = ""
            selected["ancestry_feat_id"] = ""
            _sync_creation_preview_from_selected(hero, selected)
            _notify_creation_progress(
                game,
                hero,
                stage="KROK 2: Ancestry",
                expected=f"Wybrane: {_labelize(selected['ancestry_id'])}",
                mechanics="Dodaje cechy ancestry i otwiera kolejne wybory (heritage, feat).",
            )
            step_index += 1
            continue

        if step == "heritage":
            ancestry_id = str(selected.get("ancestry_id") or "")
            if not ancestry_id:
                step_index = max(0, step_index - 1)
                continue
            hero.image = str(selected.get("portrait_image") or hero.image or "/static/placeholder.png")
            heritage_ids = list(HERITAGE_IDS_BY_ANCESTRY.get(ancestry_id, []) or [])
            heritage_options = []
            for heritage_id in heritage_ids:
                status = resolve_status(heritage_id)
                if status is None:
                    continue
                heritage_options.append(
                    {
                        "id": heritage_id,
                        "label": _labelize(heritage_id),
                        "desc": _status_choice_desc(status, "Dziedzictwo ancestry."),
                    }
                )
            heritage_id = _pick_one(
                game,
                title="KROK 3: Wybór Heritage",
                subtitle="Co wybierasz: dziedzictwo (heritage). Mechanika: specjalna cecha ancestry.",
                source="character_creation",
                options=heritage_options,
                layout="menu_numpad",
                image=hero.image,
                allow_back=allow_back,
            )
            if _is_back_choice(heritage_id):
                step_index = max(0, step_index - 1)
                continue
            if not heritage_id:
                continue
            selected["heritage_id"] = str(heritage_id)
            _sync_creation_preview_from_selected(hero, selected)
            _notify_creation_progress(
                game,
                hero,
                stage="KROK 3: Heritage",
                expected=f"Wybrane: {_labelize(selected['heritage_id'])}",
                mechanics="Dodaje ceche heritage jako status na bohaterze.",
            )
            step_index += 1
            continue

        if step == "ancestry_feat":
            ancestry_id = str(selected.get("ancestry_id") or "")
            if not ancestry_id:
                step_index = max(0, step_index - 1)
                continue
            heritage_id = str(selected.get("heritage_id") or "")
            hero.image = str(selected.get("portrait_image") or hero.image or "/static/placeholder.png")
            ancestry_feat_ids = list(ANCESTRY_FEAT_IDS_BY_ANCESTRY.get(ancestry_id, []) or [])
            ancestry_feat_ids = _filter_ancestry_feat_ids_for_selection(ancestry_id, heritage_id, ancestry_feat_ids)
            ancestry_feat_options = []
            for feat_id in ancestry_feat_ids:
                status = resolve_status(feat_id)
                if status is None:
                    continue
                ancestry_feat_options.append(
                    {
                        "id": feat_id,
                        "label": _labelize(feat_id),
                        "desc": _status_choice_desc(status, "Feat ancestry (poziom 1)."),
                    }
                )
            ancestry_feat_id = _pick_one(
                game,
                title="KROK 4: Ancestry Feat",
                subtitle="Co wybierasz: feat ancestry (poziom 1). Mechanika: nowy status z efektem pasywnym/aktywnym.",
                source="character_creation",
                options=ancestry_feat_options,
                layout="menu_numpad",
                image=hero.image,
                allow_back=allow_back,
            )
            if _is_back_choice(ancestry_feat_id):
                step_index = max(0, step_index - 1)
                continue
            if not ancestry_feat_id:
                continue
            selected["ancestry_feat_id"] = str(ancestry_feat_id)
            _sync_creation_preview_from_selected(hero, selected)
            _notify_creation_progress(
                game,
                hero,
                stage="KROK 4: Ancestry Feat",
                expected=f"Wybrane: {_labelize(selected['ancestry_feat_id'])}",
                mechanics="Feat ancestry zostaje dopiety do statusow bohatera.",
            )
            step_index += 1
            continue

        if step == "background":
            hero.image = str(selected.get("portrait_image") or hero.image or "/static/placeholder.png")
            background_options = []
            for background_status_id in list_background_status_ids():
                status = resolve_status(background_status_id)
                if status is None:
                    continue
                background_options.append(
                    {
                        "id": background_status_id,
                        "label": _labelize(background_status_id),
                        "desc": _status_choice_desc(status, "Tło postaci."),
                    }
                )
            background_id = _pick_one(
                game,
                title="KROK 5: Background",
                subtitle="Co wybierasz: tlo postaci (decyzja stala). Mechanika: boost cechy, skill/Lore, skill feat.",
                source="character_creation",
                options=background_options,
                layout="menu_numpad",
                image=hero.image,
                allow_back=allow_back,
            )
            if _is_back_choice(background_id):
                step_index = max(0, step_index - 1)
                continue
            if not background_id:
                continue
            selected["background_id"] = str(background_id)
            _sync_creation_preview_from_selected(hero, selected)
            _notify_creation_progress(
                game,
                hero,
                stage="KROK 5: Background",
                expected=f"Wybrane: {_labelize(selected['background_id'])}",
                mechanics="Dodaje background i przypisany feat do statusow bohatera.",
            )
            step_index += 1
            continue

        if step == "class":
            hero.image = str(selected.get("portrait_image") or hero.image or "/static/placeholder.png")
            class_options = []
            for class_id in CLASS_IDS:
                status = resolve_status(class_id)
                if status is None:
                    continue
                class_options.append(
                    {
                        "id": class_id,
                        "label": _labelize(class_id),
                        "desc": _structured_choice_desc(
                            name=_labelize(class_id),
                            fluff=_first_line((getattr(status, "data", None) or {}).get("ui_description")) or "Wybierasz klase postaci.",
                            mechanics=_class_mechanics_desc_pl(class_id, status),
                            when="Natychmiast po potwierdzeniu wyboru klasy.",
                        ),
                    }
                )
            class_id = _pick_one(
                game,
                title="KROK 6: Wybór Klasy",
                subtitle="Co wybierasz: klase. Mechanika: HP klasy, bieglosci, setup klasowy i featy.",
                source="character_creation",
                options=class_options,
                layout="menu_numpad",
                image=hero.image,
                allow_back=allow_back,
            )
            if _is_back_choice(class_id):
                step_index = max(0, step_index - 1)
                continue
            if not class_id:
                continue
            selected["class_id"] = str(class_id)
            if str(class_id).strip().lower() != "barbarian":
                selected["barbarian_instinct_id"] = ""
            selected["manual_class_feat_id"] = ""
            _sync_creation_preview_from_selected(hero, selected)
            _notify_creation_progress(
                game,
                hero,
                stage="KROK 6: Klasa",
                expected=f"Wybrane: {_labelize(selected['class_id'])}",
                mechanics="Zapisane wybory klasowe (np. key ability) i statusy klasy.",
            )
            step_index += 1
            continue

        if step == "barbarian_instinct":
            class_id = str(selected.get("class_id") or "").strip().lower()
            if not class_id:
                step_index = max(0, step_index - 1)
                continue
            if class_id != "barbarian":
                selected["barbarian_instinct_id"] = ""
                step_index += 1
                continue
            hero.image = str(selected.get("portrait_image") or hero.image or "/static/placeholder.png")
            instinct_ids = [
                "animal_instinct",
                "dragon_instinct",
                "fury_instinct",
                "giant_instinct",
                "spirit_instinct",
            ]
            instinct_options = []
            for instinct_id in instinct_ids:
                status = resolve_status(instinct_id)
                if status is None:
                    continue
                instinct_options.append(
                    {
                        "id": instinct_id,
                        "label": _labelize(instinct_id),
                        "desc": _status_choice_desc(status, "Instynkt barbarzyńcy."),
                    }
                )
            chosen_instinct = _pick_one(
                game,
                title="KROK 6B: Instynkt Barbarzyńcy",
                subtitle="Co wybierasz: instynkt barbarzyńcy. Mechanika: definiuje bonusy i zachowanie podczas Rage.",
                source="character_creation",
                options=instinct_options,
                layout="menu_numpad",
                image=hero.image,
                allow_back=allow_back,
            )
            if _is_back_choice(chosen_instinct):
                step_index = max(0, step_index - 1)
                continue
            if not chosen_instinct:
                continue
            selected["barbarian_instinct_id"] = str(chosen_instinct)
            _sync_creation_preview_from_selected(hero, selected)
            _notify_creation_progress(
                game,
                hero,
                stage="KROK 6B: Instynkt Barbarzyńcy",
                expected=f"Wybrane: {_labelize(selected['barbarian_instinct_id'])}",
                mechanics="Dodaje status instynktu i jego efekty powiązane z Rage.",
            )
            step_index += 1
            continue

        if step == "class_feat":
            class_id = str(selected.get("class_id") or "")
            if not class_id:
                step_index = max(0, step_index - 1)
                continue
            hero.image = str(selected.get("portrait_image") or hero.image or "/static/placeholder.png")
            manual_class_feats = list(CLASS_FEAT_CHOICES_MANUAL.get(class_id, []) or [])
            if not manual_class_feats:
                selected["manual_class_feat_id"] = ""
                step_index += 1
                continue
            feat_options = []
            for feat_id in manual_class_feats:
                status = resolve_status(feat_id)
                if status is None:
                    continue
                feat_options.append(
                    {
                        "id": feat_id,
                        "label": _labelize(feat_id),
                        "desc": _status_choice_desc(status, "Feat klasowy poziomu 1."),
                    }
                )
            chosen_feat = _pick_one(
                game,
                title="KROK 11: Class Feat",
                subtitle="Co wybierasz: feat klasy na 1. poziomie. Mechanika: dodaje nowa zdolnosc jako status.",
                source="character_creation",
                options=feat_options,
                layout="menu_numpad",
                image=hero.image,
                allow_back=allow_back,
            )
            if _is_back_choice(chosen_feat):
                step_index = max(0, step_index - 1)
                continue
            selected["manual_class_feat_id"] = str(chosen_feat or "")
            _sync_creation_preview_from_selected(hero, selected)
            _notify_creation_progress(
                game,
                hero,
                stage="KROK 11: Class Feat",
                expected=(
                    f"Wybrane: {_labelize(selected['manual_class_feat_id'])}"
                    if str(selected.get("manual_class_feat_id") or "").strip()
                    else "Pominięto wybór featu klasy."
                ),
                mechanics="Feat klasy trafia do statusów bohatera i odblokowuje odpowiednie akcje.",
            )
            step_index += 1
            continue

        step_index += 1

    hero.image = str(selected.get("portrait_image") or "/static/placeholder.png")
    name = str(selected.get("name") or "Bohater").strip() or "Bohater"
    hero.name = name
    concept = str(selected.get("concept") or "").strip()
    ancestry_id = str(selected.get("ancestry_id") or "").strip().lower()
    heritage_id = str(selected.get("heritage_id") or "").strip().lower()
    ancestry_feat_id = str(selected.get("ancestry_feat_id") or "").strip().lower()
    background_id = str(selected.get("background_id") or "").strip().lower()
    class_id = str(selected.get("class_id") or "").strip().lower()
    barbarian_instinct_id = str(selected.get("barbarian_instinct_id") or "").strip().lower()
    preselected_class_feat_id = str(selected.get("manual_class_feat_id") or "").strip().lower()

    ancestry_status = resolve_status(ancestry_id)
    heritage_status = resolve_status(heritage_id)
    ancestry_feat_status = resolve_status(ancestry_feat_id)
    background_status = resolve_status(background_id)
    class_status = resolve_status(class_id)
    if not all([ancestry_status, heritage_status, ancestry_feat_status, background_status, class_status]):
        return None

    # Wyczyść dane live-preview i odtwórz finalny stan z rzeczywistymi wyborami.
    hero.statuses = []

    hero.add_status(ancestry_status)
    _prompt_info(game, title=f"Wybrane Ancestry: {_labelize(ancestry_id)}", text=_ancestry_mechanics_desc_pl(ancestry_status), image=hero.image)
    hero.add_status(heritage_status)
    _prompt_info(
        game,
        title=f"Wybrane Heritage: {_labelize(heritage_id)}",
        text=_status_description(heritage_status),
        image=hero.image,
    )
    deferred_ancestry_feat_status: Status | None = None
    deferred_ancestry_feat_id = ""
    ancestry_feat_choice_kind = str(
        ((getattr(ancestry_feat_status, "data", None) or {}).get("ui_choice_kind") or "")
    ).strip().lower()
    if ancestry_feat_choice_kind == "natural_ambition":
        deferred_ancestry_feat_status = ancestry_feat_status
        deferred_ancestry_feat_id = ancestry_feat_id
    else:
        hero.add_status(ancestry_feat_status)
        _prompt_info(
            game,
            title=f"Wybrany Ancestry Feat: {_labelize(ancestry_feat_id)}",
            text=_status_description(ancestry_feat_status),
            image=hero.image,
        )
    hero.add_status(background_status)
    _prompt_info(
        game,
        title=f"Wybrane Tlo: {_labelize(background_id)}",
        text=_status_description(background_status),
        image=hero.image,
    )

    def _refresh_pre_class_boost_preview(*, expected: str, mechanics: str, ability_scores_current: dict[str, int]) -> None:
        _update_live_creation_sheet(
            game,
            hero,
            ancestry_status=ancestry_status,
            class_status=class_status,
            class_id=class_id,
            ability_scores=dict(ability_scores_current),
            trained_core=set(_trained_skills_from_statuses(hero)),
            lore_skills=list(_lore_skills_from_statuses(hero)),
            stage="KROK 5A: Boosty ancestry/background",
            expected=expected,
            mechanics=mechanics,
        )

    def _creation_boost_pool(
        scores_current: dict[str, int],
        allowed_values: list[str] | tuple[str, ...],
        *,
        exclude: list[str] | tuple[str, ...] | None = None,
    ) -> list[str]:
        excluded = {
            _normalize(item)
            for item in list(exclude or [])
            if _normalize(item) in ABILITY_IDS
        }
        pool: list[str] = []
        for item in list(allowed_values or []):
            ability_id = _normalize(item)
            if ability_id not in ABILITY_IDS or ability_id in excluded:
                continue
            try:
                score = int(scores_current.get(ability_id, 10) or 10)
            except Exception:
                score = 10
            if score >= 18:
                continue
            if ability_id not in pool:
                pool.append(ability_id)
        return pool

    # Najpierw ancestry/background boosty, potem setup klasy (KROK 6A).
    pre_class_scores = base_ability_scores()
    ancestry_boosts_base, ancestry_flaw_base = _ancestry_boosts_and_flaw(ancestry_status)
    for boost in ancestry_boosts_base:
        if boost == "free":
            continue
        apply_character_creation_ability_boost(pre_class_scores, boost)
        _refresh_pre_class_boost_preview(
            expected=f"Ancestry boost: {_labelize(boost)}",
            mechanics="Atrybuty aktualizowane na żywo po wyborach ancestry/background.",
            ability_scores_current=pre_class_scores,
        )

    ancestry_free_count = sum(1 for item in ancestry_boosts_base if str(item).strip().lower() == "free")
    ancestry_free_picks: list[str] = []
    ancestry_free_base = dict(pre_class_scores)
    while len(ancestry_free_picks) < ancestry_free_count:
        pool = _creation_boost_pool(pre_class_scores, list(ABILITY_IDS), exclude=ancestry_free_picks)
        chosen = _pick_ability(
            game,
            title=f"KROK 5A: Ancestry free boost {len(ancestry_free_picks) + 1}/{ancestry_free_count}",
            subtitle="Co wybierasz: dowolna cecha z ancestry. Mechanika: +2 do wybranej cechy.",
            allowed=pool or list(ABILITY_IDS),
            source="character_creation",
            image=hero.image,
            allow_back=True,
        )
        if _is_back_choice(chosen):
            if ancestry_free_picks:
                ancestry_free_picks.pop()
                pre_class_scores = dict(ancestry_free_base)
                for picked in ancestry_free_picks:
                    apply_character_creation_ability_boost(pre_class_scores, picked)
                _refresh_pre_class_boost_preview(
                    expected="Cofnięto ostatni ancestry free boost.",
                    mechanics="Atrybuty aktualizowane na żywo po cofnięciu wyboru.",
                    ability_scores_current=pre_class_scores,
                )
            continue
        if not chosen and pool:
            chosen = pool[0]
        if not chosen:
            break
        ancestry_free_picks.append(chosen)
        pre_class_scores = dict(ancestry_free_base)
        for picked in ancestry_free_picks:
            apply_character_creation_ability_boost(pre_class_scores, picked)
        _refresh_pre_class_boost_preview(
            expected=f"Ancestry free boost {len(ancestry_free_picks)}/{ancestry_free_count}: {_labelize(chosen)}",
            mechanics="Atrybuty aktualizowane na żywo po wyborach ancestry/background.",
            ability_scores_current=pre_class_scores,
        )

    if ancestry_flaw_base:
        apply_ability_flaw(pre_class_scores, ancestry_flaw_base)
        _refresh_pre_class_boost_preview(
            expected=f"Ancestry flaw: {_labelize(ancestry_flaw_base)}",
            mechanics="Atrybuty aktualizowane na żywo po wyborach ancestry/background.",
            ability_scores_current=pre_class_scores,
        )

    bg_restricted, bg_free_count = background_boost_options(background_id)
    if bg_restricted:
        restricted_pool = _creation_boost_pool(pre_class_scores, list(bg_restricted)) or [
            _normalize(item)
            for item in list(bg_restricted)
            if _normalize(item) in ABILITY_IDS
        ]
        while True:
            chosen = _pick_ability(
                game,
                title="KROK 5A: Background boost (ograniczony)",
                subtitle=f"Wybierz: {', '.join(_labelize(item) for item in restricted_pool)}",
                allowed=restricted_pool,
                source="character_creation",
                image=hero.image,
                allow_back=True,
            )
            if _is_back_choice(chosen):
                continue
            if not chosen and restricted_pool:
                chosen = str(restricted_pool[0])
            if chosen:
                apply_character_creation_ability_boost(pre_class_scores, chosen)
                _refresh_pre_class_boost_preview(
                    expected=f"Background boost: {_labelize(chosen)}",
                    mechanics="Atrybuty aktualizowane na żywo po wyborach ancestry/background.",
                    ability_scores_current=pre_class_scores,
                )
            break

    bg_free_picks: list[str] = []
    bg_free_base = dict(pre_class_scores)
    while len(bg_free_picks) < int(bg_free_count):
        pool = _creation_boost_pool(pre_class_scores, list(ABILITY_IDS), exclude=bg_free_picks)
        chosen = _pick_ability(
            game,
            title=f"KROK 5A: Background free boost {len(bg_free_picks) + 1}/{int(bg_free_count)}",
            subtitle="Co wybierasz: dowolna cecha z backgroundu. Mechanika: +2 do wybranej cechy.",
            allowed=pool or list(ABILITY_IDS),
            source="character_creation",
            image=hero.image,
            allow_back=True,
        )
        if _is_back_choice(chosen):
            if bg_free_picks:
                bg_free_picks.pop()
                pre_class_scores = dict(bg_free_base)
                for picked in bg_free_picks:
                    apply_character_creation_ability_boost(pre_class_scores, picked)
                _refresh_pre_class_boost_preview(
                    expected="Cofnięto ostatni background free boost.",
                    mechanics="Atrybuty aktualizowane na żywo po cofnięciu wyboru.",
                    ability_scores_current=pre_class_scores,
                )
            continue
        if not chosen and pool:
            chosen = pool[0]
        if not chosen:
            break
        bg_free_picks.append(chosen)
        pre_class_scores = dict(bg_free_base)
        for picked in bg_free_picks:
            apply_character_creation_ability_boost(pre_class_scores, picked)
        _refresh_pre_class_boost_preview(
            expected=f"Background free boost {len(bg_free_picks)}/{int(bg_free_count)}: {_labelize(chosen)}",
            mechanics="Atrybuty aktualizowane na żywo po wyborach ancestry/background.",
            ability_scores_current=pre_class_scores,
        )

    _prompt_info(
        game,
        title=f"KROK 6A: Setup klasy ({_labelize(class_id)})",
        text=(
            "Za chwile pojawia sie wybory klasowe (np. Key Ability, racket, bloodline, cause).\n"
            "Co wybierasz: parametry tozsamosci i stylu klasy.\n"
            "Mechanika: te wybory trafiaja do statusu klasy i sa uzywane w dalszych obliczeniach postaci."
        ),
        image=hero.image,
    )
    previous_creation_flag = bool(getattr(hero, "character_creation_in_progress", False))
    try:
        setattr(hero, "character_creation_in_progress", True)
    except Exception:
        pass
    try:
        hero.add_status(class_status)
    finally:
        try:
            setattr(hero, "character_creation_in_progress", previous_creation_flag)
        except Exception:
            pass
    class_key_ability_preview = _selected_class_key_ability(hero, class_id)
    class_setup_preview_scores = dict(pre_class_scores)
    if _normalize(class_key_ability_preview) in ABILITY_IDS:
        apply_character_creation_ability_boost(class_setup_preview_scores, class_key_ability_preview)
    _update_live_creation_sheet(
        game,
        hero,
        ancestry_status=ancestry_status,
        class_status=class_status,
        class_id=class_id,
        ability_scores=class_setup_preview_scores,
        trained_core=set(_trained_skills_from_statuses(hero)),
        lore_skills=list(_lore_skills_from_statuses(hero)),
        stage=f"KROK 6A: Setup klasy ({_labelize(class_id)})",
        expected=f"Key Ability: {_labelize(class_key_ability_preview)}",
        mechanics="Wybrana key ability klasy jest od razu dodawana do podgladu (+2).",
    )
    _prompt_info(
        game,
        title=f"Wybrana Klasa: {_labelize(class_id)}",
        text=_class_mechanics_desc_pl(class_id, class_status),
        image=hero.image,
    )

    if class_id == "barbarian" and barbarian_instinct_id:
        instinct_status = resolve_status(barbarian_instinct_id)
        if instinct_status is not None:
            hero.add_status(instinct_status)
            _prompt_info(
                game,
                title=f"Wybrany Instynkt: {_labelize(barbarian_instinct_id)}",
                text=_status_description(instinct_status),
                image=hero.image,
            )

    class_feat_ids: list[str] = []
    def _champion_cause_after_setup() -> str:
        if class_id != "champion":
            return ""
        getter = getattr(hero, "get_status_data", None)
        if callable(getter):
            try:
                setup = getter("champion", "champion_setup", {})
                if isinstance(setup, dict):
                    value = str(setup.get("cause", "") or "").strip().lower()
                    if value:
                        return value
            except Exception:
                pass
        value = str(getattr(hero, "champion_cause", "") or "").strip().lower()
        return value

    def _apply_corrected_champion_class_feat(*, skipped_feat_id: str) -> bool:
        if class_id != "champion":
            return False
        cause_id = _champion_cause_after_setup()
        allowed_by_cause = {
            "paladin": {"deitys_domain", "ranged_reprisal"},
            "redeemer": {"deitys_domain", "weight_of_guilt"},
            "liberator": {"deitys_domain", "unimpeded_step"},
        }
        allowed = allowed_by_cause.get(cause_id, set(CLASS_FEAT_CHOICES_MANUAL.get("champion") or []))
        fallback_feat_ids: list[str] = []
        for feat_id in list(CLASS_FEAT_CHOICES_MANUAL.get("champion") or []):
            fid = str(feat_id or "").strip().lower()
            if not fid or fid == skipped_feat_id:
                continue
            if fid not in allowed:
                continue
            try:
                if bool(hero.has_status(fid)):
                    continue
            except Exception:
                pass
            if resolve_status(fid) is None:
                continue
            fallback_feat_ids.append(fid)
        if not fallback_feat_ids:
            return False

        fallback_options = []
        for feat_id in fallback_feat_ids:
            status = resolve_status(feat_id)
            if status is None:
                continue
            fallback_options.append(
                {
                    "id": feat_id,
                    "label": _labelize(feat_id),
                    "desc": _status_choice_desc(status, "Feat klasowy poziomu 1."),
                }
            )
        if not fallback_options:
            return False

        corrected_feat = _pick_one(
            game,
            title="KROK 11A: Class Feat (korekta po setupie)",
            subtitle=(
                "Wczesniejszy wybor class feata jest niezgodny z aktualnym setupem klasy. "
                "Wybierz poprawny feat."
            ),
            source="character_creation",
            options=fallback_options,
            layout="menu_numpad",
            image=hero.image,
            allow_back=False,
        )
        if not corrected_feat:
            return False
        corrected_feat = str(corrected_feat).strip().lower()
        corrected_status = resolve_status(corrected_feat)
        if corrected_status is None:
            return False
        if not bool(hero.add_status(corrected_status)):
            return False
        class_feat_ids.append(corrected_feat)
        _prompt_info(
            game,
            title=f"Wybrany Class Feat (korekta): {_labelize(corrected_feat)}",
            text=_status_description(corrected_status),
            image=hero.image,
        )
        return True

    if preselected_class_feat_id:
        feat_status = resolve_status(preselected_class_feat_id)
        if feat_status is not None:
            added = bool(hero.add_status(feat_status))
            if added:
                class_feat_ids.append(preselected_class_feat_id)
                _prompt_info(
                    game,
                    title=f"Wybrany Class Feat: {_labelize(preselected_class_feat_id)}",
                    text=_status_description(feat_status),
                    image=hero.image,
                )
            else:
                _prompt_info(
                    game,
                    title=f"Class Feat pominięty: {_labelize(preselected_class_feat_id)}",
                    text="Wybrany feat nie spelnia warunkow dla tej postaci i nie zostal dodany.",
                    image=hero.image,
                )
                _apply_corrected_champion_class_feat(skipped_feat_id=preselected_class_feat_id)

    if deferred_ancestry_feat_status is not None:
        hero.add_status(deferred_ancestry_feat_status)
        _prompt_info(
            game,
            title=f"Wybrany Ancestry Feat: {_labelize(deferred_ancestry_feat_id)}",
            text=_status_description(deferred_ancestry_feat_status),
            image=hero.image,
        )

    # KROK 7 i 8: ability scores i modyfikatory
    def _refresh_live_preview(
        *,
        stage: str,
        expected: str,
        mechanics: str,
        ability_scores_current: dict[str, int],
        trained_core_current: set[str] | None = None,
        lore_skills_current: list[str] | None = None,
    ) -> None:
        _update_live_creation_sheet(
            game,
            hero,
            ancestry_status=ancestry_status,
            class_status=class_status,
            class_id=class_id,
            ability_scores=dict(ability_scores_current),
            trained_core=set(trained_core_current or set()),
            lore_skills=list(lore_skills_current or []),
            stage=stage,
            expected=expected,
            mechanics=mechanics,
        )

    ability_scores = dict(pre_class_scores)
    key_ability = _selected_class_key_ability(hero, class_id)
    if _normalize(key_ability) in ABILITY_IDS:
        apply_character_creation_ability_boost(ability_scores, key_ability)
    preview_trained_core = set(_trained_skills_from_statuses(hero))
    preview_lore_skills = list(_lore_skills_from_statuses(hero))

    _refresh_live_preview(
        stage="KROK 7: Ability Boosts",
        expected=f"Key Ability klasy: {_labelize(key_ability)}",
        mechanics="Atrybuty i modyfikatory zaktualizowane na żywo po wyborze.",
        ability_scores_current=ability_scores,
        trained_core_current=preview_trained_core,
        lore_skills_current=preview_lore_skills,
    )

    free_boost_picks: list[str] = []
    free_boost_base = dict(ability_scores)
    while len(free_boost_picks) < 4:
        pool = _creation_boost_pool(ability_scores, list(ABILITY_IDS), exclude=free_boost_picks)
        chosen = _pick_ability(
            game,
            title=f"KROK 7: Free boost {len(free_boost_picks) + 1}/4",
            subtitle="Co wybierasz: jeden z 4 wolnych boostow. Mechanika: +2 do cechy; kazdy wybor musi byc inny.",
            allowed=pool,
            source="character_creation",
            image=hero.image,
            allow_back=True,
        )
        if _is_back_choice(chosen):
            if free_boost_picks:
                free_boost_picks.pop()
                ability_scores = dict(free_boost_base)
                for picked in free_boost_picks:
                    apply_character_creation_ability_boost(ability_scores, picked)
                _refresh_live_preview(
                    stage="KROK 7: Ability Boosts",
                    expected="Cofnięto ostatni free boost.",
                    mechanics="Atrybuty i modyfikatory zaktualizowane na żywo po cofnięciu.",
                    ability_scores_current=ability_scores,
                    trained_core_current=preview_trained_core,
                    lore_skills_current=preview_lore_skills,
                )
            continue
        if not chosen and pool:
            chosen = pool[0]
        if not chosen:
            break
        free_boost_picks.append(chosen)
        ability_scores = dict(free_boost_base)
        for picked in free_boost_picks:
            apply_character_creation_ability_boost(ability_scores, picked)
        _refresh_live_preview(
            stage="KROK 7: Ability Boosts",
            expected=f"Free boost {len(free_boost_picks)}/4: {_labelize(chosen)}",
            mechanics="Atrybuty i modyfikatory zaktualizowane na żywo po wyborze.",
            ability_scores_current=ability_scores,
            trained_core_current=preview_trained_core,
            lore_skills_current=preview_lore_skills,
        )
    _refresh_live_preview(
        stage="KROK 7: Ability Boosts",
        expected="Zamknięto wybory atrybutów.",
        mechanics=f"Zastosowano wszystkie boosty; klasowy key ability: {_labelize(key_ability)}.",
        ability_scores_current=ability_scores,
        trained_core_current=preview_trained_core,
        lore_skills_current=preview_lore_skills,
    )

    # KROK 9: Skille
    int_mod_preview = (int(ability_scores.get("intelligence", 10)) - 10) // 2
    class_skill_rule = dict(CLASS_SKILL_RULES.get(class_id, {"fixed": [], "additional": 0}) or {})
    trained_core: set[str] = set(str(item).strip().lower() for item in list(class_skill_rule.get("fixed") or []))
    additional_count = max(0, int(class_skill_rule.get("additional") or 0) + int(int_mod_preview))

    class_setup_status = next(
        (item for item in list(getattr(hero, "statuses", []) or []) if getattr(item, "id", None) == class_id),
        None,
    )
    class_setup_data = getattr(class_setup_status, "data", None) or {}
    setup_payload = class_setup_data.get(f"{class_id}_setup")
    if isinstance(setup_payload, dict):
        trained_core.update(_normalize(item) for item in list(setup_payload.get("trained_skills") or []) if _normalize(item))
        one_skill = _normalize(setup_payload.get("trained_skill"))
        if one_skill:
            trained_core.add(one_skill)
    preview_trained_core = set(trained_core) | set(_trained_skills_from_statuses(hero))
    _refresh_live_preview(
        stage="KROK 9: Skille",
        expected="Start wyboru skilli.",
        mechanics="Sekcja skilli pokazuje stan bazowy klasy przed dodatkowymi wyborami.",
        ability_scores_current=ability_scores,
        trained_core_current=preview_trained_core,
        lore_skills_current=preview_lore_skills,
    )

    for skill in _pick_additional_skills(
        game,
        amount=additional_count,
        exclude=set(trained_core),
        source="character_creation",
        image=hero.image,
        on_change=lambda picks: _refresh_live_preview(
            stage="KROK 9: Skille",
            expected=(
                f"Dodatkowe skille: {', '.join(_labelize(item) for item in picks)}"
                if picks
                else "Wybierz dodatkowe skille klasy."
            ),
            mechanics="Sekcja skilli aktualizuje się po każdym wyborze i cofnięciu.",
            ability_scores_current=ability_scores,
            trained_core_current=(set(trained_core) | set(picks) | set(_trained_skills_from_statuses(hero))),
            lore_skills_current=preview_lore_skills,
        ),
    ):
        trained_core.add(skill)

    bg_skill, bg_lore = _resolve_background_training_choice(
        game,
        background_status_id=background_id,
        already_trained=set(trained_core),
        image=hero.image,
    )
    if bg_skill:
        trained_core.add(bg_skill)
    trained_core.update(_trained_skills_from_statuses(hero))

    lore_skills: list[str] = []
    if bg_lore:
        normalized_lore = _normalize_lore_name(bg_lore)
        if normalized_lore:
            lore_skills.append(normalized_lore)
    for lore in _lore_skills_from_statuses(hero):
        if lore not in lore_skills:
            lore_skills.append(lore)
    preview_trained_core = set(trained_core)
    preview_lore_skills = list(lore_skills)
    _refresh_live_preview(
        stage="KROK 9: Skille",
        expected="Wybierz trained skille i Lore.",
        mechanics="Skille trafiaja do skill_ranks bohatera; brakujace sa traktowane jako untrained.",
        ability_scores_current=ability_scores,
        trained_core_current=preview_trained_core,
        lore_skills_current=preview_lore_skills,
    )

    # KROK 10: Skill feat (z backgroundu)
    bg_feat_id = str((background_status.data or {}).get("background_feat_id") or "").strip().lower()
    if bg_feat_id:
        feat_status = resolve_status(bg_feat_id)
        mechanics_short = _status_mechanics_short(feat_status)
        info_text = f"Otrzymujesz skill feat z backgroundu: {_labelize(bg_feat_id)}."
        if mechanics_short:
            info_text += f"\nMechanika (krotko): {mechanics_short}"
        _prompt_info(
            game,
            title="KROK 10: Skill Feat",
            text=info_text,
            image=hero.image,
        )
        _notify_creation_progress(
            game,
            hero,
            stage="KROK 10: Skill Feat",
            expected=f"Otrzymany feat: {_labelize(bg_feat_id)}",
            mechanics="Feat jest dodawany jako status i moze modyfikowac akcje/testy.",
        )

    # KROK 11: Class feat (część klas wybiera feat podczas setupu statusu)
    for attr_name in ("rogue_class_feat", "ranger_class_feat", "wizard_class_feat", "sorcerer_class_feat", "monk_class_feat"):
        value = _normalize(getattr(hero, attr_name, None))
        if value and value not in class_feat_ids:
            class_feat_ids.append(value)

    if class_feat_ids:
        _prompt_info(
            game,
            title="KROK 11: Class Feat",
            text="Wybrane featy klasowe: " + ", ".join(_labelize(item) for item in class_feat_ids),
            image=hero.image,
        )
        _notify_creation_progress(
            game,
            hero,
            stage="KROK 11: Class Feat",
            expected="Featy klasowe zapisane.",
            mechanics="Wybrane featy klasowe zostaly dodane do statusow bohatera.",
        )

    # KROK 12-17: wyliczenia i finalizacja
    languages, traits, base_speed, ancestry_hp = _extract_languages_traits_speed(ancestry_status)
    class_hp = int((class_status.data or {}).get("class_hp") or 8)

    skill_ranks = {skill_id: "trained" for skill_id in trained_core if skill_id in CORE_SKILL_IDS}
    perception_rank = str(CLASS_PERCEPTION_RANK.get(class_id, "trained") or "trained")
    save_ranks = dict(CLASS_SAVE_RANKS.get(class_id, {"fortitude": "trained", "reflex": "trained", "will": "trained"}))

    status_skill_updates, status_save_updates, status_perception_rank = _status_rank_overrides(hero, level=1)
    skill_ranks = merge_rank_maps(
        skill_ranks,
        status_skill_updates,
        allowed_keys=CORE_SKILL_IDS,
        sparse=True,
    )
    save_ranks = merge_rank_maps(
        save_ranks,
        status_save_updates,
        allowed_keys=("fortitude", "reflex", "will"),
        sparse=True,
    )
    if status_perception_rank and rank_priority(status_perception_rank) > rank_priority(perception_rank):
        perception_rank = status_perception_rank
    weapon_ranks = dict(CLASS_WEAPON_PROFICIENCY.get(class_id, {}))
    defense_ranks = dict(CLASS_DEFENSE_PROFICIENCY.get(class_id, {}))
    unarmored_rank = str(defense_ranks.get("unarmored", "trained"))

    math = compute_math(
        level=1,
        ability_scores=ability_scores,
        skill_ranks=skill_ranks,
        perception_rank=perception_rank,
        save_ranks=save_ranks,
        ancestry_hp=ancestry_hp,
        class_hp=class_hp,
        speed_feet=base_speed,
        unarmored_rank=unarmored_rank,
    )
    apply_math_to_hero(
        hero,
        math,
        weapon_proficiency_ranks=weapon_ranks,
        defense_proficiency_ranks=defense_ranks,
        trained_skills=sorted(set(trained_core) | set(skill_ranks.keys())),
        lore_skills=lore_skills,
    )
    _notify_creation_progress(
        game,
        hero,
        stage="KROK 12-17: Wyliczenia",
        expected="Automatyczne podsumowanie statystyk.",
        mechanics="Przeliczono HP, AC, modyfikatory, skille i rzuty obronne.",
    )
    _run_starting_equipment_step(
        game,
        hero,
        class_id=class_id,
        image=hero.image,
        on_refresh=lambda expected, mechanics: _update_live_creation_sheet(
            game,
            hero,
            ancestry_status=ancestry_status,
            class_status=class_status,
            class_id=class_id,
            ability_scores=dict(ability_scores),
            trained_core=set(trained_core),
            lore_skills=list(lore_skills),
            stage="KROK 12: Ekwipunek",
            expected=expected,
            mechanics=mechanics,
        ),
    )
    hero.name = str(name).strip() or "Bohater"
    hero.character_concept = concept
    hero.class_id = class_id
    hero.ancestry_id = ancestry_id
    hero.heritage_id = heritage_id
    hero.ancestry_feat_id = ancestry_feat_id
    hero.background_id = background_id
    hero.languages = list(dict.fromkeys(languages))
    hero.traits = list(dict.fromkeys(traits))
    hero.starting_gold_gp = _STARTING_GOLD_GP
    _notify_creation_progress(
        game,
        hero,
        stage="KROK 12: Ekwipunek",
        expected="Zestaw startowy i stan rąk.",
        mechanics="Ekwipunek i sakiewka sa zapisane do postaci.",
    )

    character_id = _normalize(name) or f"hero_{uuid4().hex[:8]}"
    snapshot = _build_snapshot(
        hero=hero,
        character_id=character_id,
        name=hero.name,
        concept=concept,
        ancestry_id=ancestry_id,
        heritage_id=heritage_id,
        ancestry_feat_id=ancestry_feat_id,
        background_id=background_id,
        class_id=class_id,
        class_feat_ids=class_feat_ids,
    )
    repository.save_character(snapshot)
    try:
        setattr(hero, "character_creation_in_progress", False)
    except Exception:
        pass
    _, display_speed_feet = _speed_snapshot_values(hero)
    _notify_creation_progress(
        game,
        hero,
        stage="FINAL: Postac gotowa",
        expected=f"Imie: {hero.name}",
        mechanics="Snapshot zapisany; bohater gotowy do wyboru w menu startowym.",
    )

    _prompt_info(
        game,
        title="Postać utworzona",
        text=(
            f"Imię: {hero.name}\n"
            f"Ancestry/Heritage: {_labelize(ancestry_id)} / {_labelize(heritage_id)}\n"
            f"Klasa: {_labelize(class_id)}\n"
            f"HP: {hero.max_hp}, AC: {hero.ac}, Speed: {display_speed_feet} ft\n"
            f"Sakiewka: {format_actor_money(hero)}\n"
            f"Bulk: {actor_bulk_summary(hero)['total_display']} / {actor_bulk_summary(hero)['encumbered_limit_display']} (encumbered)\n"
            f"Skille trained: {', '.join(_labelize(item) for item in sorted(trained_core)) or '-'}\n"
            f"Lore: {', '.join(lore_skills) or '-'}\n"
            "Wpisz te dane na fizycznej karcie postaci."
        ),
        image=hero.image,
    )
    return CharacterCreationResult(hero=hero, snapshot=snapshot)


def hero_from_snapshot(snapshot: dict[str, Any]) -> Hero:
    from hero import Hero
    hero = Hero()
    hero.level = int(snapshot.get("level") or 1)
    hero.wounds = 0
    hero.temp_hp = 0
    hero.name = str(snapshot.get("name") or "Bohater")
    hero.character_id = str(snapshot.get("character_id") or "")
    hero.character_concept = str(snapshot.get("concept") or "")
    hero.class_id = str(snapshot.get("class_id") or "")
    hero.class_name = hero.class_id
    hero.ancestry_id = str(snapshot.get("ancestry_id") or "")
    hero.heritage_id = str(snapshot.get("heritage_id") or "")
    hero.ancestry_feat_id = str(snapshot.get("ancestry_feat_id") or "")
    hero.background_id = str(snapshot.get("background_id") or "")
    hero.image = str(snapshot.get("portrait_image") or snapshot.get("image") or "/static/placeholder.png")
    hero.track_ammo = bool(snapshot.get("track_ammo", True))
    hero.starting_gold_gp = int(snapshot.get("starting_gold_gp") or _STARTING_GOLD_GP)
    raw_coin_pouch = snapshot.get("coin_pouch")
    if isinstance(raw_coin_pouch, dict):
        hero.coin_pouch = normalize_coin_pouch(raw_coin_pouch)
    else:
        hero.coin_pouch = coin_pouch_from_cp(max(0, int(hero.starting_gold_gp or 0)) * 100)
    ensure_actor_coin_pouch(hero, default_gp=0)

    weapon_loadout: list[str] = []
    for item in list(snapshot.get("weapon_loadout") or []):
        normalized = normalize_weapon_id(item)
        if normalized and normalized not in weapon_loadout:
            weapon_loadout.append(normalized)
    armor_loadout: list[str] = []
    for item in list(snapshot.get("armor_loadout") or []):
        normalized = normalize_armor_id(item)
        if normalized and normalized not in armor_loadout:
            armor_loadout.append(normalized)
    shield_loadout: list[str] = []
    for item in list(snapshot.get("shield_loadout") or []):
        normalized = normalize_shield_id(item)
        if normalized and normalized not in shield_loadout:
            shield_loadout.append(normalized)
    hero.weapon_loadout = weapon_loadout or ["unarmed"]
    hero.armor_loadout = armor_loadout
    hero.shield_loadout = shield_loadout
    restored_inventory = _restore_inventory_from_snapshot(snapshot)
    if restored_inventory:
        hero.inventory = list(restored_inventory)

    status_ids = [str(item).strip().lower() for item in list(snapshot.get("status_ids") or []) if str(item).strip()]
    for item in list(snapshot.get("class_feat_ids") or []):
        feat_id = _normalize(item)
        if feat_id and feat_id not in status_ids:
            status_ids.append(feat_id)
    status_data = snapshot.get("status_data") if isinstance(snapshot.get("status_data"), dict) else {}
    statuses: list[Status] = []
    for status_id in status_ids:
        resolved = resolve_status(status_id)
        if resolved is None:
            resolved = Status(id=status_id, label=_labelize(status_id))
        data = dict(getattr(resolved, "data", None) or {})
        override = status_data.get(status_id)
        if isinstance(override, dict):
            data.update(override)
        statuses.append(Status(id=resolved.id, label=resolved.label, duration=resolved.duration, source=resolved.source, stacks=resolved.stacks, data=data, check_effects=resolved.check_effects))
    hero.statuses = statuses

    inferred_focus_point = 0
    inferred_focus_pool_max = 0
    for status in hero.statuses:
        data = dict(getattr(status, "data", {}) or {})
        set_attrs = dict(data.get("set_actor_attrs") or {})
        add_attrs = dict(data.get("add_actor_attrs") or {})
        if "focus_point" in set_attrs:
            try:
                inferred_focus_point = max(inferred_focus_point, int(set_attrs.get("focus_point") or 0))
            except Exception:
                pass
        if "focus_pool_max" in set_attrs:
            try:
                inferred_focus_pool_max = max(inferred_focus_pool_max, int(set_attrs.get("focus_pool_max") or 0))
            except Exception:
                pass
        if "focus_point" in add_attrs:
            try:
                inferred_focus_point += int(add_attrs.get("focus_point") or 0)
            except Exception:
                pass
        if "focus_pool_max" in add_attrs:
            try:
                inferred_focus_pool_max += int(add_attrs.get("focus_pool_max") or 0)
            except Exception:
                pass
    inferred_focus_point = max(0, int(inferred_focus_point))
    inferred_focus_pool_max = max(0, int(inferred_focus_pool_max), int(inferred_focus_point))

    hero.ability_scores = dict(snapshot.get("ability_scores") or {})
    hero.ability_modifiers = dict(snapshot.get("ability_modifiers") or {})
    hero.skill_ranks = compress_rank_map(snapshot.get("skill_ranks") or {}, allowed_keys=CORE_SKILL_IDS)
    hero.skill_modifiers = dict(snapshot.get("skill_modifiers") or {})
    snapshot_trained = {
        _normalize(item)
        for item in list(snapshot.get("trained_skills") or [])
        if _normalize(item) in CORE_SKILL_IDS
    }
    rank_trained = set(hero.skill_ranks.keys())
    status_trained = _trained_skills_from_statuses(hero)
    hero.trained_skills = sorted(snapshot_trained | rank_trained | status_trained)
    lore_skills: list[str] = []
    for item in list(snapshot.get("lore_skills") or []):
        normalized = _normalize_lore_name(item)
        if normalized and normalized not in lore_skills:
            lore_skills.append(normalized)
    for item in _lore_skills_from_statuses(hero):
        if item not in lore_skills:
            lore_skills.append(item)
    hero.lore_skills = lore_skills
    hero.languages = list(snapshot.get("languages") or [])
    hero.traits = list(snapshot.get("traits") or [])
    hero.perception_rank = str(snapshot.get("perception_rank") or "untrained")
    hero.focus_point = int(snapshot.get("focus_point") if "focus_point" in snapshot else inferred_focus_point)
    hero.focus_pool_max = int(snapshot.get("focus_pool_max") if "focus_pool_max" in snapshot else inferred_focus_pool_max)
    hero.save_ranks = compress_rank_map(snapshot.get("save_ranks") or {}, allowed_keys=("fortitude", "reflex", "will"))
    hero.weapon_proficiency_ranks = compress_rank_map(snapshot.get("weapon_proficiency_ranks") or {})
    hero.defense_proficiency_ranks = compress_rank_map(snapshot.get("defense_proficiency_ranks") or {})
    hero.max_hp = int(snapshot.get("max_hp") or 1)
    hero.base_speed_feet = int(snapshot.get("base_speed_feet") or 25)
    hero.ac = int(snapshot.get("ac") or 10)

    for key, value in dict(hero.ability_modifiers).items():
        if key == "strength":
            hero.str_mod = int(value)
        elif key == "dexterity":
            hero.dex_mod = int(value)
        elif key == "constitution":
            hero.con_mod = int(value)
        elif key == "intelligence":
            hero.int_mod = int(value)
        elif key == "wisdom":
            hero.wis_mod = int(value)
        elif key == "charisma":
            hero.cha_mod = int(value)

    status_skill_updates, status_save_updates, status_perception_rank = _status_rank_overrides(hero, level=int(hero.level or 1))
    hero.skill_ranks = merge_rank_maps(
        hero.skill_ranks,
        status_skill_updates,
        allowed_keys=CORE_SKILL_IDS,
        sparse=True,
    )
    hero.save_ranks = merge_rank_maps(
        hero.save_ranks,
        status_save_updates,
        allowed_keys=("fortitude", "reflex", "will"),
        sparse=True,
    )
    if status_perception_rank and rank_priority(status_perception_rank) > rank_priority(hero.perception_rank):
        hero.perception_rank = status_perception_rank
    hero.trained_skills = sorted(set(hero.trained_skills) | set(hero.skill_ranks.keys()))

    level = int(hero.level or 1)
    recomputed_skill_mods: dict[str, int] = {}
    for skill_id in CORE_SKILL_IDS:
        ability_key = SKILL_TO_ABILITY.get(skill_id, "intelligence")
        ability_mod = int(dict(hero.ability_modifiers).get(ability_key, 0) or 0)
        rank = str(dict(hero.skill_ranks).get(skill_id, "untrained") or "untrained")
        total = ability_mod + int(proficiency_bonus(level, rank))
        recomputed_skill_mods[skill_id] = total
    hero.skill_modifiers = recomputed_skill_mods
    for skill_id, bonus in recomputed_skill_mods.items():
        setattr(hero, f"{skill_id}_bonus", int(bonus))
    for skill_id in CORE_SKILL_IDS:
        setattr(hero, f"{skill_id}_trained", skill_id in set(hero.trained_skills) or skill_id in set(hero.skill_ranks.keys()))

    wis_mod = int(dict(hero.ability_modifiers).get("wisdom", 0) or 0)
    con_mod = int(dict(hero.ability_modifiers).get("constitution", 0) or 0)
    dex_mod = int(dict(hero.ability_modifiers).get("dexterity", 0) or 0)

    hero.perception_bonus = wis_mod + int(proficiency_bonus(level, hero.perception_rank))
    hero.fortitude_bonus = con_mod + int(proficiency_bonus(level, dict(hero.save_ranks).get("fortitude", "untrained")))
    hero.reflex_bonus = dex_mod + int(proficiency_bonus(level, dict(hero.save_ranks).get("reflex", "untrained")))
    hero.will_bonus = wis_mod + int(proficiency_bonus(level, dict(hero.save_ranks).get("will", "untrained")))
    try:
        from focus_pool import ensure_focus_pool

        ensure_focus_pool(hero)
    except Exception:
        pass

    ensure_actor_inventory(hero)
    equipped_weapon_ids: list[str] = []
    for item in list(snapshot.get("equipped_weapon_ids") or []):
        normalized = normalize_weapon_id(item)
        if normalized and normalized not in equipped_weapon_ids:
            equipped_weapon_ids.append(normalized)
    if equipped_weapon_ids:
        equipped_weapons = []
        for item in list(getattr(hero, "inventory", []) or []):
            wid = normalize_weapon_id(getattr(item, "item_id", None))
            if wid in equipped_weapon_ids:
                equipped_weapons.append(item)
        if equipped_weapons:
            set_equipped_weapons(hero, equipped_weapons)

    equipped_armor_instance = str(snapshot.get("equipped_armor_item_id") or "").strip()
    if equipped_armor_instance:
        for item in list(getattr(hero, "inventory", []) or []):
            if str(getattr(item, "instance_id", "") or "").strip() != equipped_armor_instance:
                continue
            try:
                setattr(hero, "equipped_armor_item_id", equipped_armor_instance)
            except Exception:
                pass
            break
    if not str(getattr(hero, "equipped_armor_item_id", "") or "").strip():
        equipped_armor_id = normalize_armor_id(snapshot.get("equipped_armor_id"))
        if equipped_armor_id:
            for item in list(getattr(hero, "inventory", []) or []):
                if normalize_armor_id(getattr(item, "item_id", None)) != equipped_armor_id:
                    continue
                try:
                    setattr(hero, "equipped_armor_item_id", str(getattr(item, "instance_id", "") or ""))
                except Exception:
                    pass
                break
    equipped_shield_id = normalize_shield_id(snapshot.get("equipped_shield_id"))
    if equipped_shield_id:
        for item in list(getattr(hero, "inventory", []) or []):
            if normalize_shield_id(getattr(item, "item_id", None)) != equipped_shield_id:
                continue
            try:
                setattr(hero, "equipped_shield", item)
            except Exception:
                pass
            break
    shield_hand = str(snapshot.get("equipped_shield_hand") or "").strip().lower()
    if shield_hand:
        try:
            setattr(hero, "equipped_shield_hand", shield_hand)
        except Exception:
            pass

    refresh_actor_bulk_state(hero, inventory=list(getattr(hero, "inventory", []) or []))
    refresh_actor_ac(hero)
    return hero


def list_character_menu_options(repository: CharacterRepository, *, exclude_ids: set[str] | None = None) -> list[dict[str, str]]:
    excluded = {str(item).strip().lower() for item in (exclude_ids or set()) if str(item).strip()}
    options: list[dict[str, str]] = []
    for record in repository.list_characters():
        cid = str(record.get("character_id") or "").strip().lower()
        if not cid or cid in excluded:
            continue
        label = str(record.get("name") or cid)
        ancestry = _labelize(str(record.get("ancestry_id") or ""))
        class_id = _labelize(str(record.get("class_id") or ""))
        desc = f"{ancestry} · {class_id}".strip(" ·")
        options.append({"id": cid, "label": label, "desc": desc})
    return options


__all__ = [
    "CharacterCreationResult",
    "create_character",
    "hero_from_snapshot",
    "list_character_menu_options",
]

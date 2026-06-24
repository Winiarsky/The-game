from __future__ import annotations

import re


RUNTIME_PROMPT_AUDIO_DIR = "audio/voiceover/runtime_prompts"


SKILL_AUDIO_KEYS = {
    "acrobatics": "acrobatics",
    "akrobatyki": "acrobatics",
    "arcana": "arcana",
    "wiedzy tajemnej": "arcana",
    "athletics": "athletics",
    "atletyki": "athletics",
    "crafting": "crafting",
    "rzemiosla": "crafting",
    "rzemiosła": "crafting",
    "deception": "deception",
    "oszustwa": "deception",
    "diplomacy": "diplomacy",
    "dyplomacji": "diplomacy",
    "intimidation": "intimidation",
    "zastraszania": "intimidation",
    "lore": "lore",
    "wiedzy": "lore",
    "medicine": "medicine",
    "medycyny": "medicine",
    "nature": "nature",
    "natury": "nature",
    "occultism": "occultism",
    "okultyzmu": "occultism",
    "performance": "performance",
    "wystepu": "performance",
    "występu": "performance",
    "religion": "religion",
    "religii": "religion",
    "society": "society",
    "spoleczenstwa": "society",
    "społeczeństwa": "society",
    "stealth": "stealth",
    "skradania": "stealth",
    "survival": "survival",
    "przetrwania": "survival",
    "thievery": "thievery",
    "zlodziejstwa": "thievery",
    "złodziejstwa": "thievery",
    "perception": "perception",
    "percepcji": "perception",
    "fortitude": "fortitude",
    "reflex": "reflex",
    "will": "will",
}


def runtime_prompt_audio_path(key: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", str(key or "").strip().lower()).strip("_")
    return f"{RUNTIME_PROMPT_AUDIO_DIR}/roll_{normalized}_prompt_001.mp3"


def _skill_audio_from_text(text: str) -> str | None:
    raw = str(text or "").strip().lower()
    if not raw:
        return None
    patterns = (
        r"\btest\s+([a-ząćęłńóśźż_ ]+?)(?:\s*\(|\s+dc\b|[.:,]|$)",
        r"\bwykonaj\s+test\s+([a-ząćęłńóśźż_ ]+?)(?:\s+i\b|\s*\(|\s+dc\b|[.:,]|$)",
        r"\brzut\s+(?:na|obronny:?)\s+([a-ząćęłńóśźż_ ]+?)(?:\s+save\b|\s*\(|\s+dc\b|[.:,]|$)",
        r"\b([a-ząćęłńóśźż_]+)\s+save\b",
    )
    for pattern in patterns:
        match = re.search(pattern, raw)
        if not match:
            continue
        candidate = match.group(1).strip(" .:-_")
        if candidate in SKILL_AUDIO_KEYS:
            return runtime_prompt_audio_path(SKILL_AUDIO_KEYS[candidate])
        first_word = candidate.split(" ", 1)[0]
        if first_word in SKILL_AUDIO_KEYS:
            return runtime_prompt_audio_path(SKILL_AUDIO_KEYS[first_word])
    return None


def default_roll_audio(prompt: object, *, layout: object | None = None, prompt_id: object | None = None) -> str | None:
    """Return a deterministic voiceover path for generic roll/test prompts."""
    raw = str(prompt or "").strip()
    text = raw.lower()
    normalized_layout = str(layout or "").strip().lower()
    normalized_id = str(prompt_id or "").strip().lower()

    if "damage" in {normalized_layout, normalized_id}:
        return runtime_prompt_audio_path("damage")

    skill_audio = _skill_audio_from_text(raw)
    if skill_audio:
        return skill_audio

    if "spell attack" in text or "atak zakleciem" in text or "atak zaklęciem" in text:
        return runtime_prompt_audio_path("spell_attack")
    if "attack_ranged" in text or "atak dystans" in text:
        return runtime_prompt_audio_path("ranged_attack")
    if "attack_melee" in text or "atak wręcz" in text or "atak wrecz" in text:
        return runtime_prompt_audio_path("melee_attack")
    if re.search(r"\batak\b|\battack\b|\brzut ataku\b", text):
        return runtime_prompt_audio_path("attack")
    if "flat check" in text or "concealed" in text or "hidden" in text:
        return runtime_prompt_audio_path("flat_check")
    if "recovery check" in text:
        return runtime_prompt_audio_path("recovery_check")
    if "counteract" in text or "counterspell" in text:
        return runtime_prompt_audio_path("counteract")

    if normalized_layout == "test":
        return runtime_prompt_audio_path("check")
    return None

#!/usr/bin/env python3
"""Generate missing SRD 5.1 level 0-2 spell headers from the official PDF text.

This is a maintainer tool, not a runtime dependency.  It deliberately refuses
to overwrite hand-authored executable spell definitions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import unicodedata

from dnd_board_game.character_creation.srd_manifest import SRD_SPELL_IDS_BY_LEVEL


NAME_OVERRIDES = {
    "arcanists_magic_aura": "Arcanist’s Magic Aura",
    "blindness_deafness": "Blindness/Deafness",
    "enlarge_reduce": "Enlarge/Reduce",
    "hunters_mark": "Hunter’s Mark",
}
CASTING_TIME_IDS = {
    "1 action": "action",
    "1 bonus action": "bonus_action",
    "1 reaction": "reaction",
    "1 minute": "minute",
    "10 minutes": "ten_minutes",
    "1 hour": "hour",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("text", type=Path, help="Text extracted from the official SRD 5.1 PDF")
    parser.add_argument("--output", type=Path, default=Path("content/spells"))
    args = parser.parse_args()
    source = _normalized(args.text.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    generated = 0
    for expected_level, spell_ids in SRD_SPELL_IDS_BY_LEVEL.items():
        for spell_id in spell_ids:
            destination = args.output / f"{spell_id}.json"
            if destination.exists():
                continue
            name = NAME_OVERRIDES.get(spell_id, spell_id.replace("_", " ").title())
            payload = _spell_payload(source, spell_id, name, expected_level)
            destination.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            generated += 1
    print(f"Generated {generated} missing SRD spell definitions.")


def _normalized(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    for dash in ("‐", "‑", "–", "—"):
        value = value.replace(dash, "-")
    return re.sub(r"\s+", " ", value)


def _spell_payload(
    source: str,
    spell_id: str,
    name: str,
    expected_level: int,
) -> dict[str, object]:
    heading = re.compile(
        re.escape(name)
        + r"\s+(?:(cantrip)|((?:1st|2nd))-+level)\s+"
        + r"(abjuration|conjuration|divination|enchantment|evocation|illusion|necromancy|transmutation)"
        + r"(\s+\(ritual\))?\s+Casting Time:\s*(.*?)\s+Range:\s*(.*?)\s+"
        + r"Components:\s*(.*?)\s+Duration:\s*"
        + r"((?:Concentration,\s*(?:up to\s*)?)?(?:Instantaneous|Until dispelled(?: or triggered)?|\d+\s+(?:rounds?|minutes?|hours?)))",
        re.IGNORECASE,
    )
    matches = tuple(heading.finditer(source))
    if not matches:
        raise ValueError(f"Cannot find spell header for {name}.")
    match = matches[-1]
    level = 0 if match.group(1) else {"1st": 1, "2nd": 2}[match.group(2).lower()]
    if level != expected_level:
        raise ValueError(f"{name}: parsed level {level}, expected {expected_level}.")
    casting_text = match.group(5).strip().lower()
    casting_id = next(
        (
            value
            for prefix, value in CASTING_TIME_IDS.items()
            if casting_text == prefix or casting_text.startswith(prefix)
        ),
        None,
    )
    if casting_id is None:
        raise ValueError(f"{name}: unsupported casting time {casting_text!r}.")
    range_payload = _range_payload(match.group(6))
    components = _components_payload(spell_id, match.group(7))
    duration, concentration = _duration_payload(match.group(8))
    return {
        "schema": "dnd_board_game.spell",
        "schema_version": 1,
        "ruleset_id": "dnd_5e_2014",
        "source_pack_ids": ["srd_5_1_cc_by_4_0"],
        "id": spell_id,
        "name": name,
        "level": level,
        "school": match.group(3).lower(),
        "casting_time": casting_id,
        "range": range_payload,
        "components": components,
        "duration": duration,
        "concentration": concentration,
        "ritual": bool(match.group(4)),
        "effect": {
            "kind": "manual",
            "rules_resolution": "pending_typed_implementation",
        },
    }


def _range_payload(raw: str) -> dict[str, object]:
    text = raw.strip()
    lowered = text.lower()
    if lowered.startswith("self"):
        return {"kind": "self"}
    if lowered == "touch":
        return {"kind": "touch"}
    if lowered == "sight":
        return {"kind": "sight"}
    if lowered == "unlimited":
        return {"kind": "unlimited"}
    match = re.match(r"(\d+)\s+feet", lowered)
    if match:
        return {"kind": "distance", "feet": int(match.group(1))}
    raise ValueError(f"Unsupported spell range {text!r}.")


def _components_payload(spell_id: str, raw: str) -> dict[str, object]:
    text = raw.strip()
    letters = text.split("(", 1)[0]
    material_match = re.search(r"\((.*)\)", text)
    materials: list[dict[str, object]] = []
    if "M" in letters:
        label = material_match.group(1).strip() if material_match else "komponent materialny"
        value_match = re.search(
            r"(?:(\d+)\s*gp\s+worth|(?:worth|value of)\s+(?:at least\s+)?(\d+)\s*gp)",
            label,
            re.I,
        )
        value_gp = next(
            (int(group) for group in value_match.groups() if group is not None),
            None,
        ) if value_match else None
        materials.append(
            {
                "item_id": f"spell_component_{spell_id}",
                "label": label,
                **(
                    {"minimum_value_cp": value_gp * 100}
                    if value_gp is not None
                    else {}
                ),
                **(
                    {"consumed": True}
                    if re.search(r"consum", label, re.I)
                    else {}
                ),
            }
        )
    return {
        "verbal": "V" in letters,
        "somatic": "S" in letters,
        "materials": materials,
    }


def _duration_payload(raw: str) -> tuple[dict[str, object], bool]:
    text = raw.strip().lower()
    concentration = text.startswith("concentration")
    text = re.sub(r"^concentration,\s*(?:up to\s*)?", "", text)
    if text.startswith("instantaneous"):
        return {"kind": "instantaneous"}, concentration
    if text.startswith("until dispelled"):
        return {"kind": "until_dispelled"}, concentration
    match = re.match(r"(\d+)\s+(round|minute|minutes|hour|hours)", text)
    if not match:
        raise ValueError(f"Unsupported spell duration {raw!r}.")
    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "round":
        kind = "round"
    elif unit.startswith("minute"):
        kind = "ten_minutes" if amount == 10 else "minute"
        if kind == "ten_minutes":
            amount = 1
    elif amount == 8:
        kind, amount = "eight_hours", 1
    elif amount == 24:
        kind, amount = "twenty_four_hours", 1
    else:
        kind = "hour"
    return {"kind": kind, "amount": amount}, concentration


if __name__ == "__main__":
    main()

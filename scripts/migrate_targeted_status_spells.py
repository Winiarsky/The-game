"""One-shot migration of SRD buffs to typed targeted combat statuses."""

from __future__ import annotations

import json
from pathlib import Path


SPELLS: dict[str, dict[str, object]] = {
    "barkskin": {
        "effect_kind": "minimum_armor_class",
        "value": 16,
        "target_faction": "ally",
    },
    "blur": {
        "effect_kind": "attacks_against_disadvantage",
        "value": 0,
        "target_faction": "self",
    },
    "darkvision": {
        "effect_kind": "darkvision",
        "value": 60,
        "target_faction": "ally",
    },
    "expeditious_retreat": {
        "effect_kind": "bonus_action_dash",
        "value": 1,
        "target_faction": "self",
    },
    "invisibility": {
        "effect_kind": "invisibility",
        "value": 0,
        "target_faction": "ally",
    },
    "jump": {
        "effect_kind": "jump_multiplier",
        "value": 3,
        "target_faction": "ally",
    },
    "longstrider": {
        "effect_kind": "speed_bonus",
        "value": 10,
        "target_faction": "ally",
    },
    "mage_armor": {
        "effect_kind": "mage_armor_base",
        "value": 13,
        "target_faction": "ally",
    },
    "pass_without_trace": {
        "effect_kind": "stealth_bonus_aura",
        "value": 10,
        "target_faction": "ally",
        "target_count": 5,
    },
    "protection_from_evil_and_good": {
        "effect_kind": "protection_from_evil_and_good",
        "value": 0,
        "target_faction": "ally",
    },
    "protection_from_poison": {
        "effect_kind": "protection_from_poison",
        "value": 0,
        "target_faction": "ally",
    },
    "sanctuary": {
        "effect_kind": "sanctuary",
        "value": 0,
        "target_faction": "ally",
    },
    "see_invisibility": {
        "effect_kind": "see_invisibility",
        "value": 0,
        "target_faction": "self",
    },
    "spider_climb": {
        "effect_kind": "spider_climb",
        "value": 0,
        "target_faction": "ally",
    },
    "true_strike": {
        "effect_kind": "next_attack_advantage",
        "value": 0,
        "target_faction": "self",
        "duration": "next_attack",
    },
    "warding_bond": {
        "effect_kind": "warding_bond",
        "value": 1,
        "target_faction": "ally",
    },
}


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "content" / "spells"
    for spell_id, contract in SPELLS.items():
        path = root / f"{spell_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        previous = data["effect"]
        if previous.get("kind") not in {"assisted", "combat_action"}:
            raise ValueError(f"{spell_id}: unexpected effect {previous.get('kind')}")
        migrated = {
            "kind": "combat_action",
            "action_type": "targeted_status",
            "label": data["name"],
            "target_count": 1,
            "cast_flag": f"cast_{spell_id}",
            "instructions": previous.get("instructions", ""),
            **contract,
        }
        data["effect"] = migrated
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()

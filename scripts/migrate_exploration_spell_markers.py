"""One-shot, reproducible migration of authored-scene spells from assisted casts."""

from __future__ import annotations

import json
from pathlib import Path


SPELL_IDS = (
    "alarm",
    "animal_messenger",
    "arcane_lock",
    "arcanists_magic_aura",
    "augury",
    "continual_flame",
    "create_or_destroy_water",
    "detect_evil_and_good",
    "detect_magic",
    "detect_poison_and_disease",
    "detect_thoughts",
    "disguise_self",
    "find_traps",
    "gentle_repose",
    "goodberry",
    "identify",
    "illusory_script",
    "knock",
    "locate_animals_or_plants",
    "locate_object",
    "magic_mouth",
    "prayer_of_healing",
    "purify_food_and_drink",
    "rope_trick",
    "silent_image",
    "speak_with_animals",
    "alter_self",
    "calm_emotions",
    "charm_person",
    "enthrall",
    "suggestion",
    "zone_of_truth",
    "find_familiar",
    "find_steed",
    "floating_disk",
    "unseen_servant",
)


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "content" / "spells"
    for spell_id in SPELL_IDS:
        path = root / f"{spell_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        previous = data["effect"]
        if previous.get("kind") not in {"assisted", "exploration"}:
            raise ValueError(f"{spell_id}: unexpected effect {previous.get('kind')}")
        data["effect"] = {
            "kind": "exploration",
            "effect_type": "set_flag",
            "flag_key": f"cast_{spell_id}",
            "flag_value": True,
            "instructions": previous.get(
                "instructions",
                "Scena i narrator rozstrzygają użycie na podstawie znacznika czaru.",
            ),
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()

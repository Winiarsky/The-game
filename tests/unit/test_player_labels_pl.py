import json
from pathlib import Path

from dnd_board_game.character_creation import (
    load_character_catalog,
    load_character_resources,
)
from dnd_board_game.core.player_labels_pl import (
    PLAYER_LABELS_PL,
    SPELL_NAMES_PL,
)


def test_every_spell_content_id_has_one_polish_player_name() -> None:
    spell_ids = {
        str(json.loads(path.read_text(encoding="utf-8"))["id"])
        for path in Path("content/spells").glob("*.json")
    }

    assert set(SPELL_NAMES_PL) == spell_ids
    assert all(name.strip() for name in SPELL_NAMES_PL.values())


def test_every_creator_skill_language_tool_and_spell_has_a_polish_label() -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    creator_ids: set[str] = set()
    for species in catalog.species:
        creator_ids.update(species.skill_proficiencies)
        creator_ids.update(species.skill_choices)
        creator_ids.update(species.tool_proficiencies)
        creator_ids.update(species.tool_choices)
        creator_ids.update(species.languages)
        creator_ids.update(species.cantrip_choices)
        creator_ids.update(species.fixed_cantrip_ids)
        creator_ids.update(spell.spell_id for spell in species.innate_spells)
    for background in catalog.backgrounds:
        creator_ids.update(background.skill_proficiencies)
        creator_ids.update(background.tool_proficiencies)
        creator_ids.update(background.tool_choices)
        creator_ids.update(background.languages)
    for character_class in catalog.classes:
        creator_ids.update(character_class.skill_choices)
        creator_ids.update(character_class.tool_proficiencies)
        creator_ids.update(character_class.cantrip_choices)
        creator_ids.update(character_class.spell_choices)
        creator_ids.update(character_class.fighting_style_choices)

    assert sorted(creator_ids - PLAYER_LABELS_PL.keys()) == []


def test_loaded_spell_and_creator_item_names_are_polish_player_labels() -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")

    assert resources.spell("magic_missile").name == "Magiczny pocisk"
    assert resources.spell("find_familiar").name == "Przywołanie chowańca"
    assert resources.inventory_item("playing_card_set").name == "Talia kart"
    assert all(item.name.strip() for _, item in resources.inventory_items)

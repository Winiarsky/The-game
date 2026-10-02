"""Cross-check the player-facing material against the actual starter builds."""

from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.character_creation import (
    PLAYABLE_HERO_IDS, apply_boardgame_archetype, build_character,
    default_character_drafts, load_character_catalog, load_character_resources,
)
from dnd_board_game.character_creation.boardgame_help import HERO_FLAWS, HERO_FLAW_IDS
from dnd_board_game.combat import AttackKind, attack_source_for_actor
from dnd_board_game.inventory import effective_armor_class
from dnd_board_game.actors import Actor
from dnd_board_game.core.player_labels_pl import PLAYER_LABELS_PL
from dnd_board_game.ui.combat_keyboard import HERO_SHORTCUTS, shortcut_for_option
from dnd_board_game.ui.exploration_app import (
    ExplorationUiSession, _exploration_actor_payload, _feature_help_text,
)
from dnd_board_game.ui.hero_selection import HERO_SELECTION_GUIDES
from dnd_board_game.ui.routes import _character_sheet_feature_entries


@pytest.fixture(scope="module")
def heroes() -> dict[str, Actor]:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    return {
        draft.id: apply_boardgame_archetype(
            build_character(draft, catalog, resources).actor,
            spell_definitions=tuple(spell for _, spell in resources.spells),
        )
        for draft in default_character_drafts() if draft.id in PLAYABLE_HERO_IDS
    }


@pytest.mark.parametrize("actor_id", PLAYABLE_HERO_IDS)
def test_current_print_model_matches_v03_starter_stats_equipment_and_features(
    heroes: dict[str, Actor], actor_id: str,
) -> None:
    from dnd_board_game.application.resonance_combat import apply_charge_profile
    from dnd_board_game.character_creation.runes import apply_rune_profile
    from dnd_board_game.core.player_labels_pl import ABILITY_LABELS_PL
    from dnd_board_game.inventory.armor import effective_speed_feet
    from dnd_board_game.physical_cards.mana_print import build_print_hero
    from dnd_board_game.rules import ability_modifier
    from dnd_board_game.rules.resonance import PROFILE, cards_for
    from dnd_board_game.scenarios.rune_relation_catalog import load_rune_relation_catalog

    actor = apply_charge_profile(apply_rune_profile(heroes[actor_id]))
    printed = build_print_hero(actor_id, rune_profile=True)
    assert (printed.id, printed.name, printed.level, printed.hp, printed.ac, printed.speed) == (
        str(actor.id), actor.name, actor.level, actor.max_hp,
        effective_armor_class(actor), effective_speed_feet(actor),
    )
    assert printed.abilities == tuple(
        (label, score, ability_modifier(score))
        for ability, label in ABILITY_LABELS_PL.items()
        for score in (getattr(actor.ability_scores, ability),)
    )
    assert printed.equipment == tuple(f"{item.name} ×{item.quantity}" for item in actor.inventory)

    catalog = load_rune_relation_catalog()
    row = catalog["heroes"][actor_id]
    powers = cards_for(catalog, actor_id)
    grants = {feature.feature_id: feature for feature in actor.features if feature.source_ref == PROFILE}
    assert set(grants) == {PROFILE, f"{PROFILE}_passive", f"{PROFILE}_flaw", *(card.id for card in powers)}
    for card in powers:
        assert (grants[card.id].label, grants[card.id].description) == (card.name, card.effect)
    for kind in ("passive", "flaw"):
        assert (grants[f"{PROFILE}_{kind}"].label, grants[f"{PROFILE}_{kind}"].description) == (
            row[kind]["name"], row[kind]["description"],
        )


def test_custom_knives_and_archery_survive_live_source_rebinding(heroes: dict[str, Actor], tmp_path: Path) -> None:
    from tests.unit.test_exploration_ui_session import _start_gate_skirmish

    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json",
                                   save_dir=tmp_path / "saves", observation_dir=tmp_path / "observations")
    session.configure_custom_party((heroes["erynd"], heroes["mira"]))
    _start_gate_skirmish(session)
    for actor_id, item_id, kind, expected in (
        ("erynd", "longbow", AttackKind.RANGED, 8),
        ("erynd", "hunting_knife", AttackKind.MELEE, 3),
        ("mira", "throwing_knife", AttackKind.RANGED, 6),
    ):
        actor = heroes[actor_id]
        source = next(s for s in session._attack_sources_for_actor(actor)
                      if s.proficiency_id == item_id and s.attack_kind == kind
                      and s.ability == ("strength" if item_id == "hunting_knife" else "dexterity"))
        for _ in range(3):
            source = attack_source_for_actor(source, actor)
            assert sum(m.value for m in source.attack_roll_request.modifiers) == expected
        assert apply_boardgame_archetype(actor).proficiencies == actor.proficiencies
        if item_id == "longbow":
            no_style = replace(actor, features=tuple(f for f in actor.features if f.feature_id != "fighting_style_archery"))
            assert sum(m.value for m in attack_source_for_actor(source, no_style).attack_roll_request.modifiers) == 6


@pytest.mark.parametrize("actor_id,item_id,ability,expected", (
    ("garran", "longsword", "strength", 6),
    ("brakka", "greataxe", "strength", 6),
    ("mira", "rapier", "dexterity", 6),
    ("dagna", "mace", "strength", 3),
    ("lorian", "hand_crossbow", "dexterity", 4),
    ("nimra", "dagger", "dexterity", 4),
    ("erynd", "longbow", "dexterity", 8),
))
def test_every_hero_has_the_documented_primary_weapon_bonus(
    heroes: dict[str, Actor], tmp_path: Path,
    actor_id: str, item_id: str, ability: str, expected: int,
) -> None:
    from tests.unit.test_exploration_ui_session import _start_gate_skirmish

    actor = heroes[actor_id]
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        save_dir=tmp_path / "saves", observation_dir=tmp_path / "observations",
    )
    session.configure_custom_party((actor,))
    _start_gate_skirmish(session)
    source = next(source for source in session._attack_sources_for_actor(actor)
                  if source.proficiency_id == item_id and source.ability == ability)
    assert sum(modifier.value for modifier in source.attack_roll_request.modifiers) == expected


def test_previously_unlabelled_hero_actions_have_keyboard_access() -> None:
    from dnd_board_game.combat.context_menu import CombatMenuAction, CombatMenuCategory, CombatMenuOption

    for actor_id, option_id, action, action_id, key in (
        ("mira", "basic:hide", CombatMenuAction.HIDE, None, "D"),
        ("mira", "basic:end-hide", CombatMenuAction.END_HIDE, None, "D"),
        ("brakka", "turn:grapple", CombatMenuAction.GRAPPLE, None, "D"),
        ("dagna", "class-feature:turn_undead", CombatMenuAction.CLASS_FEATURE, "turn_undead", "T"),
    ):
        option = CombatMenuOption(option_id, "Test", "", CombatMenuCategory.SUPPORT, action, action_id=action_id)
        assert shortcut_for_option(actor_id, option) == key

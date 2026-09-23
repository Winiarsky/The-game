"""One equipped weapon is shared by new-game and printable rune profiles."""
import pytest

from dnd_board_game.character_creation.runes import apply_rune_profile
from dnd_board_game.inventory import effective_armor_class
from dnd_board_game.physical_cards.mana_print import build_print_hero
from dnd_board_game.ui.training_arena import training_hero


@pytest.mark.parametrize('hero,weapon', [('garran','longsword'), ('brakka','greataxe'),
    ('mira','rapier'), ('dagna','mace'), ('lorian','hand_crossbow'), ('nimra','quarterstaff'), ('erynd','longbow')])
def test_single_weapon_keeps_starter_protection_and_matches_print(hero: str, weapon: str) -> None:
    old = training_hero(hero)
    actor = apply_rune_profile(old)
    weapons = [i for i in actor.inventory if i.kind == 'weapon']
    assert len(weapons) == 1 and weapons[0].id == weapon and weapons[0].equipped
    assert weapons[0].quantity == 1
    assert sum(i.kind == 'armor' for i in actor.inventory) <= 1
    assert effective_armor_class(actor) == effective_armor_class(old)
    assert {i.id for i in actor.inventory if i.kind == 'shield'} == ({'shield'} if hero in {'garran','dagna'} else set())
    assert {i.id for i in actor.inventory if i.kind == 'ammunition'} == ({'arrow'} if hero == 'erynd' else set())
    printed = build_print_hero(hero, rune_profile=True)
    assert printed.ac == effective_armor_class(actor)
    assert all(f'{i.name} ×{i.quantity}' in printed.equipment for i in actor.inventory)
    spare_names = {i.name for i in old.inventory if i.kind == 'weapon' and i.id != weapon}
    assert not any(name in line for name in spare_names for line in printed.equipment)
    assert apply_rune_profile(actor) == actor

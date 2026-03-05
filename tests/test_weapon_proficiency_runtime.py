from hero import Hero
from combat.weapon_proficiency import compute_weapon_attack_roll_bonus
from statuses import Status
from statuses.race.dwarf.feats.dwarven_weapon_familiarity import DWARVEN_WEAPON_FAMILIARITY_STATUS


def test_proficiency_bonus_formula_level_plus_rank_step():
    hero = Hero()
    hero.level = 5
    hero.str_mod = 4
    hero.add_status(
        Status(
            id="weapon_prof_test",
            data={
                "weapon_proficiency_ranks": {
                    "simple": "trained",
                    "martial": "expert",
                    "advanced": "untrained",
                    "unarmed": "trained",
                }
            },
        )
    )

    result = compute_weapon_attack_roll_bonus(hero, weapon_tags=["attack_melee", "sword"], is_ranged=False, finesse=False)
    # martial expert: 5 + 4 = 9, STR +4
    assert int(result["proficiency_bonus"]) == 9
    assert int(result["ability_bonus"]) == 4
    assert int(result["total"]) == 13


def test_dwarven_weapon_familiarity_reclassifies_dwarf_weapons():
    hero = Hero()
    hero.level = 1
    hero.str_mod = 2
    hero.add_status(
        Status(
            id="weapon_prof_test",
            data={"weapon_proficiency_ranks": {"simple": "trained", "martial": "untrained", "advanced": "untrained"}},
        )
    )
    hero.add_status(DWARVEN_WEAPON_FAMILIARITY_STATUS)

    result = compute_weapon_attack_roll_bonus(
        hero,
        weapon_tags=["attack_melee", "advanced", "dwarf", "dwarven_war_axe"],
        is_ranged=False,
        finesse=False,
    )
    # advanced dwarf -> martial (feat), potem martial dwarf -> simple (feat), simple trained: 1 + 2
    assert result["category"] == "simple"
    assert result["rank"] == "trained"
    assert int(result["proficiency_bonus"]) == 3
    assert int(result["total"]) == 5

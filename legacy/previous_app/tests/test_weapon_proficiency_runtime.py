from hero import Hero
from combat.weapon_proficiency import compute_weapon_attack_roll_bonus
from statuses import Status
from statuses.race.dwarf.feats.dwarven_weapon_familiarity import DWARVEN_WEAPON_FAMILIARITY_STATUS
from statuses.classes.monk.feats.monastic_weaponry import MONASTIC_WEAPONRY_STATUS


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


def test_brutal_uses_strength_for_ranged_attack_bonus():
    hero = Hero()
    hero.level = 1
    hero.str_mod = 4
    hero.dex_mod = 1
    hero.add_status(
        Status(
            id="weapon_prof_test",
            data={
                "weapon_proficiency_ranks": {
                    "simple": "trained",
                    "martial": "trained",
                    "advanced": "untrained",
                    "unarmed": "trained",
                }
            },
        )
    )

    normal = compute_weapon_attack_roll_bonus(
        hero,
        weapon_tags=["attack_ranged", "weapon_test"],
        is_ranged=True,
        finesse=False,
        brutal=False,
    )
    brutal = compute_weapon_attack_roll_bonus(
        hero,
        weapon_tags=["attack_ranged", "weapon_test", "brutal"],
        is_ranged=True,
        finesse=False,
        brutal=True,
    )

    assert int(normal["ability_bonus"]) == 1
    assert int(brutal["ability_bonus"]) == 4


def test_melee_attack_formula_with_item_bonus_matches_pf2_example_shape():
    hero = Hero()
    hero.level = 5
    hero.str_mod = 4
    hero.weapon_attack_item_bonus = {"default": 1}
    hero.add_status(
        Status(
            id="weapon_prof_test",
            data={
                "weapon_proficiency_ranks": {
                    "simple": "trained",
                    "martial": "trained",
                    "advanced": "untrained",
                    "unarmed": "trained",
                }
            },
        )
    )

    result = compute_weapon_attack_roll_bonus(
        hero,
        weapon_tags=["attack_melee", "longsword"],
        is_ranged=False,
        finesse=False,
    )
    # level 5 + trained 2 + STR 4 + item 1 = 12
    assert int(result["proficiency_bonus"]) == 7
    assert int(result["ability_bonus"]) == 4
    assert int(result["item_bonus"]) == 1
    assert int(result["total"]) == 12


def test_ranged_attack_formula_with_dex_and_expert_matches_pf2_example_shape():
    hero = Hero()
    hero.level = 4
    hero.dex_mod = 4
    hero.str_mod = 1
    hero.weapon_attack_item_bonus = {"default": 1}
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

    result = compute_weapon_attack_roll_bonus(
        hero,
        weapon_tags=["attack_ranged", "longbow"],
        is_ranged=True,
        finesse=False,
    )
    # level 4 + expert 4 + DEX 4 + item 1 = 13
    assert int(result["proficiency_bonus"]) == 8
    assert int(result["ability_bonus"]) == 4
    assert str(result["ability_key"]) == "dexterity"
    assert int(result["item_bonus"]) == 1
    assert int(result["total"]) == 13


def test_monastic_weaponry_reclassifies_monk_weapons_to_simple_for_proficiency():
    hero = Hero()
    hero.level = 1
    hero.str_mod = 3
    hero.add_status(Status(id="monk"))
    hero.add_status(
        Status(
            id="weapon_prof_test",
            data={
                "weapon_proficiency_ranks": {
                    "simple": "trained",
                    "martial": "untrained",
                    "advanced": "untrained",
                    "unarmed": "trained",
                }
            },
        )
    )

    without_feat = compute_weapon_attack_roll_bonus(
        hero,
        weapon_tags=["attack_melee", "bo_staff", "martial", "monk"],
        is_ranged=False,
        finesse=False,
    )
    hero.add_status(MONASTIC_WEAPONRY_STATUS)
    with_feat = compute_weapon_attack_roll_bonus(
        hero,
        weapon_tags=["attack_melee", "bo_staff", "martial", "monk"],
        is_ranged=False,
        finesse=False,
    )

    assert without_feat["category"] == "martial"
    assert without_feat["rank"] == "untrained"
    assert with_feat["category"] == "simple"
    assert with_feat["rank"] == "trained"
    assert int(with_feat["proficiency_bonus"]) == 3
    assert int(with_feat["total"]) == 6

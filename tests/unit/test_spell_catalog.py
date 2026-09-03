import json
from pathlib import Path

from dnd_board_game.character_creation.srd_manifest import SRD_SPELL_IDS_BY_LEVEL
from dnd_board_game.combat import (
    ActionEconomyCost,
    MagicMovementKind,
    SpellAreaShape,
)
from dnd_board_game.core.player_labels_pl import player_label
from dnd_board_game.rules import (
    EffectDuration,
    SpellDurationKind,
    SpellRangeKind,
    SpellSchool,
)
from dnd_board_game.scenarios.loader import (
    _parse_attack,
    _parse_combat_action,
    _parse_healing_source,
    _parse_spell_definition,
    _spell_effect_payload,
)


SPELL_ROOT = Path("content/spells")
SRD_SPELL_IDS = {
    "sacred_flame",
    "healing_word",
    "fire_bolt",
    "burning_hands",
    "cure_wounds",
    "inflict_wounds",
}


def _spell_data(spell_id: str) -> dict[str, object]:
    return json.loads((SPELL_ROOT / f"{spell_id}.json").read_text(encoding="utf-8"))


def test_exploration_use_metadata_distinguishes_objects_from_creatures():
    fire_bolt = _spell_data("fire_bolt")["exploration_use"]
    magic_missile = _spell_data("magic_missile")["exploration_use"]
    knock = _spell_data("knock")["exploration_use"]

    assert {"damage_object", "ignite"} <= set(fire_bolt["tags"])
    assert "object" in fire_bolt["targets"]
    assert "damage_creature" in magic_missile["tags"]
    assert "damage_object" not in magic_missile["tags"]
    assert {"open", "unlock"} <= set(knock["tags"])
    assert "very_loud" in knock["consequences"]


def test_first_srd_spell_tranche_has_open_source_metadata() -> None:
    for spell_id in SRD_SPELL_IDS:
        data = _spell_data(spell_id)
        assert data["ruleset_id"] == "dnd_5e_2014"
        assert data["source_pack_ids"] == ["srd_5_1_cc_by_4_0"]


def test_all_cantrip_names_are_presented_in_polish() -> None:
    expected = {
        "acid_splash": "Kwasowy rozprysk",
        "chill_touch": "Dotyk chłodu",
        "dancing_lights": "Tańczące światła",
        "druidcraft": "Druidztwo",
        "eldritch_blast": "Niesamowity podmuch",
        "fire_bolt": "Ognisty pocisk",
        "guidance": "Wskazówki",
        "light": "Światło",
        "mage_hand": "Dłoń maga",
        "mending": "Naprawa",
        "message": "Wiadomość",
        "minor_illusion": "Pomniejsza iluzja",
        "poison_spray": "Trujący rozprysk",
        "prestidigitation": "Kuglarstwo",
        "produce_flame": "Stworzenie płomienia",
        "ray_of_frost": "Promień mrozu",
        "resistance": "Odporność",
        "sacred_flame": "Święty płomień",
        "shillelagh": "Kostur",
        "shocking_grasp": "Porażający dotyk",
        "spare_the_dying": "Oszczędź umierającego",
        "thaumaturgy": "Taumaturgia",
        "true_strike": "Prawdziwe uderzenie",
        "vicious_mockery": "Zjadliwa kpina",
    }

    assert {
        spell_id: _spell_data(spell_id)["name"]
        for spell_id in expected
    } == expected


def test_all_first_level_srd_spell_names_are_presented_in_polish() -> None:
    expected = {
        "alarm": "Alarm",
        "animal_friendship": "Przyjaźń ze zwierzętami",
        "bane": "Zguba",
        "bless": "Błogosławieństwo",
        "burning_hands": "Płonące dłonie",
        "charm_person": "Zauroczenie osoby",
        "color_spray": "Barwna zasłona",
        "command": "Rozkaz",
        "comprehend_languages": "Rozumienie języków",
        "create_or_destroy_water": "Stworzenie lub zniszczenie wody",
        "cure_wounds": "Leczenie ran",
        "detect_evil_and_good": "Wykrycie dobra i zła",
        "detect_magic": "Wykrycie magii",
        "detect_poison_and_disease": "Wykrycie trucizny i choroby",
        "disguise_self": "Zmiana wyglądu",
        "divine_favor": "Boska przychylność",
        "entangle": "Oplątanie",
        "expeditious_retreat": "Szybki odwrót",
        "faerie_fire": "Baśniowy ogień",
        "false_life": "Fałszywe życie",
        "feather_fall": "Powolne opadanie",
        "find_familiar": "Znalezienie chowańca",
        "floating_disk": "Lewitujący dysk",
        "fog_cloud": "Chmura mgły",
        "goodberry": "Dobre jagody",
        "grease": "Śliskość",
        "guiding_bolt": "Pocisk przewodni",
        "healing_word": "Słowo leczenia",
        "hellish_rebuke": "Piekielna reprymenda",
        "heroism": "Heroizm",
        "hideous_laughter": "Ohydny śmiech",
        "hunters_mark": "Znak łowcy",
        "identify": "Identyfikacja",
        "illusory_script": "Iluzoryczne pismo",
        "inflict_wounds": "Zadawanie ran",
        "jump": "Skok",
        "longstrider": "Długie kroki",
        "mage_armor": "Magiczny pancerz",
        "magic_missile": "Magiczny pocisk",
        "protection_from_evil_and_good": "Ochrona przed dobrem i złem",
        "purify_food_and_drink": "Oczyszczenie jadła i napoju",
        "sanctuary": "Sanktuarium",
        "shield": "Tarcza",
        "shield_of_faith": "Tarcza wiary",
        "silent_image": "Cichy obraz",
        "sleep": "Uśpienie",
        "speak_with_animals": "Rozmowa ze zwierzętami",
        "thunderwave": "Fala gromu",
        "unseen_servant": "Niewidzialny sługa",
    }

    assert {
        spell_id: _spell_data(spell_id)["name"]
        for spell_id in expected
    } == expected


def test_repaired_first_level_control_spells_keep_their_srd_board_contracts() -> None:
    color_spray = _spell_data("color_spray")["effect"]
    entangle = _spell_data("entangle")["effect"]
    grease = _spell_data("grease")["effect"]
    fog_cloud = _spell_data("fog_cloud")["effect"]
    protection = _parse_spell_definition(
        _spell_data("protection_from_evil_and_good"),
        "protection_from_evil_and_good",
    )

    assert color_spray["area"] == {
        "shape": "cone",
        "length_feet": 15,
        "target_mode": "all_creatures",
    }
    assert entangle["area"] == {
        "shape": "cube",
        "length_feet": 20,
        "target_mode": "all_creatures",
    }
    assert grease["area"] == {
        "shape": "cube",
        "length_feet": 10,
        "target_mode": "all_creatures",
    }
    assert fog_cloud["area"] == {
        "shape": "radius",
        "radius_feet": 20,
        "target_mode": "all_creatures",
    }
    assert protection.concentration is True
    assert protection.duration.kind == SpellDurationKind.HOUR


def test_lorians_thunderwave_uses_a_fifteen_foot_cone() -> None:
    effect = _spell_data("thunderwave")["effect"]

    assert effect["area"]["shape"] == "cone"
    assert effect["area"]["length_feet"] == 15


def test_nimras_lightning_path_has_board_chain_base_damage() -> None:
    spell = _spell_data("nimra_lightning_path")

    assert spell["range"] == {"kind": "distance", "feet": 60}
    assert spell["effect"]["save_ability"] == "dexterity"
    assert spell["effect"]["save_damage_on_success"] == "half"
    assert spell["effect"]["damage"] == {
        "dice": "3d6",
        "modifier": 0,
        "damage_type": "lightning",
    }


def test_all_second_level_srd_spell_names_are_presented_in_polish() -> None:
    assert {
        spell_id: _spell_data(spell_id)["name"]
        for spell_id in SRD_SPELL_IDS_BY_LEVEL[2]
    } == {
        spell_id: player_label(spell_id)
        for spell_id in SRD_SPELL_IDS_BY_LEVEL[2]
    }


def test_repaired_second_level_spells_keep_runtime_specific_contracts() -> None:
    acid_arrow = _spell_data("acid_arrow")["effect"]
    branding_smite = _spell_data("branding_smite")["effect"]
    darkness = _spell_data("darkness")["effect"]
    enhance_ability = _spell_data("enhance_ability")["effect"]
    flaming_sphere = _spell_data("flaming_sphere")["effect"]

    assert acid_arrow["miss_damage_on_failure"] == "half"
    assert acid_arrow["on_hit_effect_kind"] == "ongoing_damage:2:4:acid:-:none"
    assert branding_smite["target_faction"] == "self"
    assert darkness["area"] == {
        "shape": "radius",
        "radius_feet": 15,
        "target_mode": "all_creatures",
    }
    assert enhance_ability["effect_options"] == [
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
    ]
    assert enhance_ability["damage_die_sides"] == 6
    assert flaming_sphere["effect_kind"] == "ongoing_damage_zone"
    assert flaming_sphere["area"]["radius_feet"] == 5
    assert flaming_sphere["save_damage_on_success"] == "half"


def test_invisibility_and_gentle_repose_match_srd_metadata() -> None:
    invisibility = _parse_spell_definition(
        _spell_data("invisibility"),
        "invisibility",
    )
    gentle_repose = _parse_spell_definition(
        _spell_data("gentle_repose"),
        "gentle_repose",
    )

    assert invisibility.school == SpellSchool.ILLUSION
    assert invisibility.range.kind == SpellRangeKind.TOUCH
    assert invisibility.duration.kind == SpellDurationKind.HOUR
    assert invisibility.concentration is True
    assert gentle_repose.range.kind == SpellRangeKind.TOUCH
    assert gentle_repose.duration.kind == SpellDurationKind.TEN_DAYS
    assert gentle_repose.concentration is False
    assert gentle_repose.ritual is True


def test_misty_step_adapts_to_thirty_foot_bonus_action_teleport() -> None:
    data = _spell_data("misty_step")
    spell = _parse_spell_definition(data, "misty_step")
    collection, effect = _spell_effect_payload(data, spell)
    action = _parse_combat_action(effect, "catalog_caster")

    assert collection == "combat_action"
    assert action.spell_level == 2
    assert action.action_cost == ActionEconomyCost.BONUS_ACTION
    assert action.target_faction == "self"
    assert action.movement is not None
    assert action.movement.kind == MagicMovementKind.TELEPORT
    assert action.movement.distance_feet == 30
    assert action.concentration is False


def test_moonbeam_adapts_to_persistent_five_foot_radius_damage_zone() -> None:
    data = _spell_data("moonbeam")
    spell = _parse_spell_definition(data, "moonbeam")
    collection, effect = _spell_effect_payload(data, spell)
    action = _parse_combat_action(effect, "catalog_caster")

    assert collection == "combat_action"
    assert action.effect_kind == "ongoing_damage_zone"
    assert action.area is not None
    assert action.area.shape == SpellAreaShape.RADIUS
    assert action.area.radius_feet == 5
    assert action.range_feet == 120
    assert action.ongoing_damage_dice_count == 2
    assert action.damage_die_sides == 10
    assert action.damage_type == "radiant"
    assert action.save_ability == "constitution"
    assert action.save_damage_on_success == "half"


def test_pass_without_trace_is_self_anchored_dynamic_stealth_aura() -> None:
    data = _spell_data("pass_without_trace")
    spell = _parse_spell_definition(data, "pass_without_trace")
    collection, effect = _spell_effect_payload(data, spell)
    action = _parse_combat_action(effect, "catalog_caster")

    assert collection == "combat_action"
    assert action.target_faction == "self"
    assert action.target_count == 1
    assert action.effect_kind == "stealth_bonus_aura"
    assert action.value == 10
    assert action.concentration is True


def test_prayer_of_healing_keeps_ten_minute_srd_casting_contract() -> None:
    spell = _parse_spell_definition(
        _spell_data("prayer_of_healing"),
        "prayer_of_healing",
    )

    assert spell.name == "Modlitwa leczenia"
    assert spell.level == 2
    assert spell.casting_time.value == "ten_minutes"
    assert spell.range.kind == SpellRangeKind.DISTANCE
    assert spell.range.feet == 30
    assert spell.duration.kind == SpellDurationKind.INSTANTANEOUS
    assert spell.concentration is False


def test_protection_from_poison_is_touch_hour_non_concentration_status() -> None:
    data = _spell_data("protection_from_poison")
    spell = _parse_spell_definition(data, "protection_from_poison")
    collection, effect = _spell_effect_payload(data, spell)
    action = _parse_combat_action(effect, "catalog_caster")

    assert spell.name == "Ochrona przed trucizną"
    assert spell.range.kind == SpellRangeKind.TOUCH
    assert spell.duration.kind == SpellDurationKind.HOUR
    assert spell.concentration is False
    assert collection == "combat_action"
    assert action.effect_kind == "protection_from_poison"
    assert action.range_feet == 5


def test_ray_of_enfeeblement_is_concentration_ranged_spell_attack() -> None:
    data = _spell_data("ray_of_enfeeblement")
    spell = _parse_spell_definition(data, "ray_of_enfeeblement")
    collection, effect = _spell_effect_payload(data, spell)
    attack = _parse_attack(effect, "catalog_caster")

    assert spell.name == "Promień osłabienia"
    assert spell.range.kind == SpellRangeKind.DISTANCE
    assert spell.range.feet == 60
    assert spell.duration.kind == SpellDurationKind.MINUTE
    assert spell.concentration is True
    assert collection == "attack"
    assert attack.on_hit_effect_kind == "ray_of_enfeeblement"
    assert attack.on_hit_effect_duration.value == "concentration"


def test_rope_trick_keeps_hour_touch_non_concentration_contract() -> None:
    spell = _parse_spell_definition(
        _spell_data("rope_trick"),
        "rope_trick",
    )

    assert spell.name == "Sztuczka z liną"
    assert spell.range.kind == SpellRangeKind.TOUCH
    assert spell.duration.kind == SpellDurationKind.HOUR
    assert spell.concentration is False
    assert spell.effect_kind == "exploration"


def test_scorching_ray_defines_three_separate_upcastable_spell_attacks() -> None:
    data = _spell_data("scorching_ray")
    spell = _parse_spell_definition(data, "scorching_ray")
    collection, effect = _spell_effect_payload(data, spell)
    action = _parse_combat_action(effect, "catalog_caster")

    assert spell.name == "Palący promień"
    assert collection == "combat_action"
    assert action.action_type == "multi_target_damage"
    assert action.projectile_count == 3
    assert action.projectile_attack_roll is True
    assert action.projectile_damage_dice_count == 2
    assert action.damage_die_sides == 6
    assert action.damage_type == "fire"
    assert action.upcast_projectiles_per_level == 1


def test_see_invisibility_is_self_hour_non_concentration_status() -> None:
    data = _spell_data("see_invisibility")
    spell = _parse_spell_definition(data, "see_invisibility")
    collection, effect = _spell_effect_payload(data, spell)
    action = _parse_combat_action(effect, "catalog_caster")

    assert spell.name == "Widzenie niewidzialnego"
    assert spell.range.kind == SpellRangeKind.SELF
    assert spell.duration.kind == SpellDurationKind.HOUR
    assert spell.concentration is False
    assert collection == "combat_action"
    assert action.target_faction == "self"
    assert action.effect_kind == "see_invisibility"


def test_shatter_is_radius_thunder_damage_with_construct_disadvantage() -> None:
    data = _spell_data("shatter")
    spell = _parse_spell_definition(data, "shatter")
    collection, effect = _spell_effect_payload(data, spell)
    attack = _parse_attack(effect, "catalog_caster")

    assert spell.name == "Roztrzaskanie"
    assert spell.level == 2
    assert spell.range.kind == SpellRangeKind.DISTANCE
    assert spell.range.feet == 60
    assert collection == "attack"
    assert attack.area is not None
    assert attack.area.shape == SpellAreaShape.RADIUS
    assert attack.area.radius_feet == 10
    assert attack.save_ability == "constitution"
    assert attack.save_damage_on_success == "half"
    assert attack.save_disadvantage_creature_types == ("construct",)
    assert attack.damage_components[0].dice is not None
    assert attack.damage_components[0].dice.format() == "3d8"
    assert attack.damage_components[0].damage_type == "thunder"
    assert attack.upcast_damage_dice_per_level == 1


def test_silence_is_board_anchored_twenty_foot_concentration_zone() -> None:
    data = _spell_data("silence")
    spell = _parse_spell_definition(data, "silence")
    collection, effect = _spell_effect_payload(data, spell)
    action = _parse_combat_action(effect, "catalog_caster")

    assert spell.name == "Cisza"
    assert spell.level == 2
    assert spell.ritual is True
    assert spell.concentration is True
    assert spell.range.feet == 120
    assert collection == "combat_action"
    assert action.effect_kind == "silence_zone"
    assert action.area is not None
    assert action.area.shape == SpellAreaShape.RADIUS
    assert action.area.radius_feet == 20


def test_spider_climb_is_touch_concentration_mobility_effect() -> None:
    data = _spell_data("spider_climb")
    spell = _parse_spell_definition(data, "spider_climb")
    collection, effect = _spell_effect_payload(data, spell)
    action = _parse_combat_action(effect, "catalog_caster")

    assert spell.name == "Pajęcza wspinaczka"
    assert spell.range.kind == SpellRangeKind.TOUCH
    assert spell.duration.kind == SpellDurationKind.HOUR
    assert spell.concentration is True
    assert collection == "combat_action"
    assert action.effect_kind == "spider_climb"
    assert action.target_faction == "ally"
    assert action.range_feet == 5


def test_spike_growth_is_twenty_foot_persistent_board_zone() -> None:
    data = _spell_data("spike_growth")
    spell = _parse_spell_definition(data, "spike_growth")
    collection, effect = _spell_effect_payload(data, spell)
    action = _parse_combat_action(effect, "catalog_caster")

    assert spell.name == "Kolczaste zarośla"
    assert spell.range.feet == 50
    assert spell.concentration is True
    assert collection == "combat_action"
    assert action.effect_kind == "spike_growth_zone"
    assert action.area is not None
    assert action.area.shape == SpellAreaShape.RADIUS
    assert action.area.radius_feet == 20


def test_spiritual_weapon_is_non_concentration_bonus_action_summon() -> None:
    data = _spell_data("spiritual_weapon")
    spell = _parse_spell_definition(data, "spiritual_weapon")
    collection, effect = _spell_effect_payload(data, spell)
    action = _parse_combat_action(effect, "catalog_caster")

    assert spell.name == "Duchowa broń"
    assert spell.level == 2
    assert spell.casting_time.value == "bonus_action"
    assert spell.duration.kind == SpellDurationKind.MINUTE
    assert spell.concentration is False
    assert collection == "combat_action"
    assert action.action_type == "summon"
    assert action.action_cost == ActionEconomyCost.BONUS_ACTION
    assert action.summon is not None
    assert action.summon.id == "spiritual_weapon"
    assert action.summon.hp == 1
    assert action.summon.ac == 18
    assert action.summon.speed_feet == 20
    assert action.summon.attack_range_feet == 5
    assert action.summon.attack_damage_type.value == "force"


def test_dagna_board_spell_adjustments_are_data_driven() -> None:
    sacred_data = _spell_data("sacred_flame")
    sacred_spell = _parse_spell_definition(sacred_data, "sacred_flame")
    sacred_collection, sacred_effect = _spell_effect_payload(
        sacred_data,
        sacred_spell,
    )
    sacred = _parse_attack(sacred_effect, "dagna")
    guiding_data = _spell_data("guiding_bolt")
    guiding_spell = _parse_spell_definition(guiding_data, "guiding_bolt")
    guiding_collection, guiding_effect = _spell_effect_payload(
        guiding_data,
        guiding_spell,
    )
    guiding = _parse_attack(guiding_effect, "dagna")
    bless_data = _spell_data("bless")
    bless_spell = _parse_spell_definition(bless_data, "bless")
    bless_collection, bless_effect = _spell_effect_payload(bless_data, bless_spell)
    bless = _parse_combat_action(bless_effect, "dagna")
    care_data = _spell_data("divine_care_aura")
    care_spell = _parse_spell_definition(care_data, "divine_care_aura")
    care_collection, care_effect = _spell_effect_payload(care_data, care_spell)
    care = _parse_combat_action(care_effect, "dagna")
    grace_data = _spell_data("healing_grace_aura")
    grace_spell = _parse_spell_definition(grace_data, "healing_grace_aura")
    grace_collection, grace_effect = _spell_effect_payload(grace_data, grace_spell)
    grace = _parse_combat_action(grace_effect, "dagna")

    assert sacred_collection == "attack"
    assert sacred.area is not None
    assert sacred.area.shape == SpellAreaShape.CONE
    assert sacred.area.length_feet == 15
    assert sacred.area.target_mode.value == "enemies"
    assert guiding_collection == "attack"
    assert guiding.damage_components[0].dice is not None
    assert guiding.damage_components[0].dice.format() == "2d6"
    assert bless_collection == care_collection == grace_collection == "combat_action"
    assert bless.effect_kind == "bless_aura_source"
    assert (bless.aura_radius_feet, bless.duration_rounds) == (10, 5)
    assert care.effect_kind == "divine_care_aura_source"
    assert (care.aura_radius_feet, care.duration_rounds) == (5, 5)
    assert grace.effect_kind == "healing_grace_aura_source"
    assert (grace.aura_radius_feet, grace.duration_rounds) == (10, 3)
    assert grace.activation_count_ability == "wisdom"
    assert (grace.bonus_die_sides, grace.bonus_modifier_ability) == (8, "wisdom")


def test_suggestion_keeps_eight_hour_concentration_exploration_contract() -> None:
    data = _spell_data("suggestion")
    spell = _parse_spell_definition(data, "suggestion")

    assert spell.name == "Sugestia"
    assert spell.level == 2
    assert spell.range.feet == 30
    assert spell.duration.kind == SpellDurationKind.EIGHT_HOURS
    assert spell.concentration is True
    assert spell.effect_kind == "exploration"


def test_warding_bond_is_touch_hour_non_concentration_status() -> None:
    data = _spell_data("warding_bond")
    spell = _parse_spell_definition(data, "warding_bond")
    collection, effect = _spell_effect_payload(data, spell)
    action = _parse_combat_action(effect, "catalog_caster")

    assert spell.name == "Więź ochronna"
    assert spell.range.kind == SpellRangeKind.TOUCH
    assert spell.duration.kind == SpellDurationKind.HOUR
    assert spell.concentration is False
    assert spell.components.materials[0].quantity == 2
    assert spell.components.materials[0].minimum_value_cp == 5000
    assert collection == "combat_action"
    assert action.effect_kind == "warding_bond"
    assert action.value == 1
    assert action.target_faction == "ally"


def test_web_is_twenty_foot_persistent_cube_zone() -> None:
    data = _spell_data("web")
    spell = _parse_spell_definition(data, "web")
    collection, effect = _spell_effect_payload(data, spell)
    action = _parse_combat_action(effect, "catalog_caster")

    assert spell.name == "Sieć"
    assert spell.range.feet == 60
    assert spell.duration.kind == SpellDurationKind.HOUR
    assert spell.concentration is True
    assert collection == "combat_action"
    assert action.effect_kind == "web_zone"
    assert action.area is not None
    assert action.area.shape == SpellAreaShape.CUBE
    assert action.area.length_feet == 20
    assert action.save_ability == "dexterity"


def test_zone_of_truth_is_non_concentration_fifteen_foot_zone() -> None:
    data = _spell_data("zone_of_truth")
    spell = _parse_spell_definition(data, "zone_of_truth")
    collection, effect = _spell_effect_payload(data, spell)
    action = _parse_combat_action(effect, "catalog_caster")

    assert spell.name == "Strefa prawdy"
    assert spell.range.feet == 60
    assert spell.duration.kind == SpellDurationKind.TEN_MINUTES
    assert spell.concentration is False
    assert collection == "combat_action"
    assert action.effect_kind == "zone_of_truth_zone"
    assert action.area is not None
    assert action.area.shape == SpellAreaShape.RADIUS
    assert action.area.radius_feet == 15
    assert action.save_ability == "charisma"


def test_fire_bolt_and_burning_hands_adapt_to_attack_sources() -> None:
    fire_bolt_data = _spell_data("fire_bolt")
    fire_bolt = _parse_spell_definition(fire_bolt_data, "fire_bolt")
    collection, effect = _spell_effect_payload(fire_bolt_data, fire_bolt)
    fire_bolt_attack = _parse_attack(effect, "catalog_caster")

    assert collection == "attack"
    assert fire_bolt_attack.range_feet == 120
    assert fire_bolt_attack.damage_components[0].dice is not None
    assert fire_bolt_attack.damage_components[0].dice.format() == "1d10"
    assert fire_bolt_attack.cantrip_damage_dice_per_tier == 1

    burning_hands_data = _spell_data("burning_hands")
    burning_hands = _parse_spell_definition(burning_hands_data, "burning_hands")
    _collection, effect = _spell_effect_payload(burning_hands_data, burning_hands)
    burning_hands_attack = _parse_attack(effect, "catalog_caster")

    assert burning_hands_attack.area is not None
    assert burning_hands_attack.area.shape == SpellAreaShape.CONE
    assert burning_hands_attack.area.length_feet == 15
    assert burning_hands_attack.save_damage_on_success == "half"
    assert burning_hands_attack.upcast_damage_dice_per_level == 1


def test_vicious_mockery_compiles_next_weapon_attack_disadvantage() -> None:
    data = _spell_data("vicious_mockery")
    spell = _parse_spell_definition(data, "vicious_mockery")
    collection, effect = _spell_effect_payload(data, spell)
    attack = _parse_attack(effect, "catalog_caster")

    assert collection == "attack"
    assert attack.save_ability == "wisdom"
    assert attack.on_hit_effect_kind == "vicious_mockery_disadvantage"
    assert attack.on_hit_effect_duration == EffectDuration.UNTIL_NEXT_ATTACK


def test_cure_wounds_uses_touch_range_and_caster_ability() -> None:
    data = _spell_data("cure_wounds")
    spell = _parse_spell_definition(data, "cure_wounds")
    collection, effect = _spell_effect_payload(data, spell)
    healing = _parse_healing_source(effect, "catalog_caster")

    assert collection == "healing"
    assert healing.range_feet == 5
    assert healing.ability == "wisdom"
    assert healing.healing_die_sides == 8
    assert healing.upcast_healing_dice_per_level == 1


def test_sleep_and_faerie_fire_define_board_selected_areas() -> None:
    sleep_data = _spell_data("sleep")
    sleep_spell = _parse_spell_definition(sleep_data, "sleep")
    collection, sleep_effect = _spell_effect_payload(sleep_data, sleep_spell)
    sleep_action = _parse_combat_action(sleep_effect, "catalog_caster")

    assert collection == "combat_action"
    assert sleep_action.name == "Sen"
    assert sleep_action.target_faction == "any"
    assert sleep_action.area is not None
    assert sleep_action.area.shape == SpellAreaShape.RADIUS
    assert sleep_action.area.radius_feet == 20
    assert "najniższej liczby aktualnych PW" in sleep_action.instructions

    faerie_data = _spell_data("faerie_fire")
    faerie_spell = _parse_spell_definition(faerie_data, "faerie_fire")
    collection, faerie_effect = _spell_effect_payload(faerie_data, faerie_spell)
    faerie_action = _parse_combat_action(
        faerie_effect,
        "catalog_caster",
    )

    assert collection == "combat_action"
    assert faerie_action.target_faction == "any"
    assert faerie_action.area is not None
    assert faerie_action.area.shape == SpellAreaShape.CUBE
    assert faerie_action.area.length_feet == 20

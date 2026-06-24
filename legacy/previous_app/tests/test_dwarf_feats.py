from statuses.race.dwarf.feats.dwarven_lore import DWARVEN_LORE_STATUS
from statuses.race.dwarf.feats.dwarven_weapon_familiarity import DWARVEN_WEAPON_FAMILIARITY_STATUS
from statuses.race.dwarf.feats.rock_runner import ROCK_RUNNER_STATUS
from statuses.race.dwarf.feats.stonecunning import STONECUNNING_STATUS
from statuses.race.dwarf.feats.unburdened_iron import UNBURDENED_IRON_STATUS
from statuses.race.dwarf.feats.vengeful_hatred import VengefulHatredStatus


def test_dwarven_lore_has_runtime_trained_fields():
    data = DWARVEN_LORE_STATUS.data
    assert data.get("trained_skills") == ["crafting", "religion"]
    assert data.get("trained_lore") == ["dwarven_lore"]
    assert "Przykład" in str(data.get("ui_description", ""))


def test_dwarven_weapon_familiarity_has_tag_based_runtime_data():
    data = DWARVEN_WEAPON_FAMILIARITY_STATUS.data
    overrides = data.get("weapon_proficiency_overrides") or {}
    assert overrides.get("battle_axe") == "trained"
    assert overrides.get("pick") == "trained"
    assert overrides.get("warhammer") == "trained"
    assert data.get("weapon_category_adjustments")
    assert "Przykład" in str(data.get("ui_description", ""))


def test_unburdened_iron_contains_speed_hooks():
    data = UNBURDENED_IRON_STATUS.data
    assert bool(data.get("ignore_armor_move_penalty")) is True
    assert int(data.get("magical_slow_reduction_feet", 0) or 0) == 5


def test_rock_runner_and_stonecunning_have_mechanics_description():
    assert "Przykład" in str(ROCK_RUNNER_STATUS.data.get("ui_description", ""))
    assert "Przykład" in str(STONECUNNING_STATUS.data.get("ui_description", ""))


def test_vengeful_hatred_default_runtime_shape():
    status = VengefulHatredStatus("orc")
    data = status.data
    assert data.get("enemy_type") == "orc"
    assert int(data.get("damage_bonus_per_die", 0) or 0) == 1
    assert int(data.get("revenge_duration_rounds", 0) or 0) == 10

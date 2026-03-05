from statuses.race.dwarf.heritages.ancient_blooded import ANCIENT_BLOODED_DWARF_STATUS
from statuses.race.dwarf.heritages.forge_dwarf import FORGE_DWARF_STATUS
from statuses.race.dwarf.heritages.rock_dwarf import ROCK_DWARF_STATUS
from statuses.race.dwarf.heritages.strong_blooded import STRONG_BLOODED_DWARF_STATUS


def test_rock_dwarf_has_forced_movement_hook_and_prone_tag():
    data = ROCK_DWARF_STATUS.data
    assert float(data.get("forced_movement_multiplier", 1.0)) == 0.5
    assert int(data.get("forced_movement_threshold_feet", 0) or 0) == 10
    assert "prone" in list(data.get("defensive_effect_tags") or [])
    assert "Przykład" in str(data.get("ui_description", ""))


def test_strong_blooded_has_stage_reduction_rules():
    data = STRONG_BLOODED_DWARF_STATUS.data
    assert int(data.get("poison_stage_reduction_on_success", 0) or 0) == 2
    assert int(data.get("poison_stage_reduction_on_success_virulent", 0) or 0) == 1
    assert int(data.get("poison_stage_reduction_on_critical_success", 0) or 0) == 3
    assert int(data.get("poison_stage_reduction_on_critical_success_virulent", 0) or 0) == 2
    assert "Przykład" in str(data.get("ui_description", ""))


def test_forge_and_ancient_have_ui_examples():
    assert "Przykład" in str(FORGE_DWARF_STATUS.data.get("ui_description", ""))
    assert "Przykład" in str(ANCIENT_BLOODED_DWARF_STATUS.data.get("ui_description", ""))

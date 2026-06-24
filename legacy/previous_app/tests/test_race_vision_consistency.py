from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS
from statuses.race.gnome.gnome import GNOME_STATUS
from statuses.race.halfling.heritages.twilight_halfling import TWILIGHT_HALFLING_STATUS
from statuses.race.human.heritages.half_elf import HALF_ELF_STATUS
from statuses.race.human.heritages.half_orc import HALF_ORC_STATUS


def _grants(status):
    return list((status.data or {}).get("grants_statuses") or [])


def test_gnome_grants_dim_light_vision_status():
    grants = _grants(GNOME_STATUS)
    assert any(getattr(item, "id", None) == DIM_LIGHT_VISION_STATUS.id for item in grants)


def test_twilight_halfling_grants_dim_light_vision_status():
    grants = _grants(TWILIGHT_HALFLING_STATUS)
    assert any(getattr(item, "id", None) == DIM_LIGHT_VISION_STATUS.id for item in grants)


def test_half_elf_and_half_orc_grant_dim_light_vision_status():
    half_elf_grants = _grants(HALF_ELF_STATUS)
    half_orc_grants = _grants(HALF_ORC_STATUS)
    assert any(getattr(item, "id", None) == DIM_LIGHT_VISION_STATUS.id for item in half_elf_grants)
    assert any(getattr(item, "id", None) == DIM_LIGHT_VISION_STATUS.id for item in half_orc_grants)

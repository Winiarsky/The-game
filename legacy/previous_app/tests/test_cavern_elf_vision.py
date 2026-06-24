from hero import Hero
from statuses.darkvision import DARKVISION_STATUS
from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS
from statuses.race.elfs.elf import ELF_STATUS
from statuses.race.elfs.heritages.cavern_elf import CAVERN_ELF_STATUS


def test_cavern_elf_replaces_dim_light_from_elf():
    hero = Hero()
    hero.add_status(ELF_STATUS)

    assert hero.has_status(DIM_LIGHT_VISION_STATUS)
    assert not hero.has_status(DARKVISION_STATUS)

    hero.add_status(CAVERN_ELF_STATUS)

    assert not hero.has_status(DIM_LIGHT_VISION_STATUS)
    assert hero.has_status(DARKVISION_STATUS)


def test_cavern_elf_replaces_dim_light_direct():
    hero = Hero()
    hero.add_status(DIM_LIGHT_VISION_STATUS)

    assert hero.has_status(DIM_LIGHT_VISION_STATUS)

    hero.add_status(CAVERN_ELF_STATUS)

    assert not hero.has_status(DIM_LIGHT_VISION_STATUS)
    assert hero.has_status(DARKVISION_STATUS)

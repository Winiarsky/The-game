from combat.damage_utils import prompt_damage_summary
from hero import Hero
from statuses.race.elfs.heritages.arctic_elf import ARCTIC_ELF_STATUS


class DummyUI:
    def __init__(self):
        self.last_prompt_long = None
        self.last_title = None

    def prompt_info(self, title, *, prompt_long=None, **_kwargs):
        self.last_title = title
        self.last_prompt_long = prompt_long
        return "ok"


def _set_dummy_ui(monkeypatch):
    dummy = DummyUI()

    def _get_ui_client():
        return dummy

    monkeypatch.setattr("combat.damage_utils.get_ui_client", _get_ui_client)
    return dummy


def test_arctic_elf_no_status_full_cold_damage(monkeypatch):
    dummy_ui = _set_dummy_ui(monkeypatch)
    hero = Hero()

    prompt_damage_summary(hero, [("slashing", 4), ("cold", 3)])

    assert dummy_ui.last_prompt_long is not None
    text = dummy_ui.last_prompt_long.lower()
    assert "slashing 4" in text
    assert "cold 3" in text
    assert "odpornosc" not in text
    assert "arctic elf" not in text


def test_arctic_elf_level_1_reduces_cold_by_1(monkeypatch):
    dummy_ui = _set_dummy_ui(monkeypatch)
    hero = Hero()
    hero.add_status(ARCTIC_ELF_STATUS)

    prompt_damage_summary(hero, [("slashing", 4), ("cold", 3)])

    assert dummy_ui.last_prompt_long is not None
    text = dummy_ui.last_prompt_long.lower()
    assert "slashing 4" in text
    assert "cold 2" in text
    assert "-1" in text
    assert "arctic elf" in text


def test_arctic_elf_level_3_reduces_cold_by_2(monkeypatch):
    dummy_ui = _set_dummy_ui(monkeypatch)
    hero = Hero()
    hero.level = 3
    hero.add_status(ARCTIC_ELF_STATUS)

    prompt_damage_summary(hero, [("slashing", 4), ("cold", 3)])

    assert dummy_ui.last_prompt_long is not None
    text = dummy_ui.last_prompt_long.lower()
    assert "slashing 4" in text
    assert "cold 1" in text
    assert "-2" in text
    assert "arctic elf" in text

from combat.damage_utils import prompt_damage_summary
from hero import Hero
from statuses.race.dwarf.heritages.forge_dwarf import FORGE_DWARF_STATUS


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


def test_forge_dwarf_no_status_full_fire_damage(monkeypatch):
    dummy_ui = _set_dummy_ui(monkeypatch)
    hero = Hero()

    prompt_damage_summary(hero, [("slashing", 4), ("fire", 3)])

    assert dummy_ui.last_prompt_long is not None
    text = dummy_ui.last_prompt_long.lower()
    assert "slashing 4" in text
    assert "fire 3" in text
    assert "odpornosc" not in text
    assert "forge dwarf" not in text


def test_forge_dwarf_level_1_reduces_fire_by_1(monkeypatch):
    dummy_ui = _set_dummy_ui(monkeypatch)
    hero = Hero()
    hero.add_status(FORGE_DWARF_STATUS)

    prompt_damage_summary(hero, [("slashing", 4), ("fire", 3)])

    assert dummy_ui.last_prompt_long is not None
    text = dummy_ui.last_prompt_long.lower()
    assert "slashing 4" in text
    assert "fire 2" in text
    assert "-1" in text
    assert "forge dwarf" in text


def test_forge_dwarf_level_3_reduces_fire_by_2(monkeypatch):
    dummy_ui = _set_dummy_ui(monkeypatch)
    hero = Hero()
    hero.level = 3
    hero.add_status(FORGE_DWARF_STATUS)

    prompt_damage_summary(hero, [("slashing", 4), ("fire", 3)])

    assert dummy_ui.last_prompt_long is not None
    text = dummy_ui.last_prompt_long.lower()
    assert "slashing 4" in text
    assert "fire 1" in text
    assert "-2" in text
    assert "forge dwarf" in text

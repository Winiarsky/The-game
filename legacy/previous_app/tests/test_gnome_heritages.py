from __future__ import annotations

from GameObjects.interactions_mixin.status_mixin import StatusMixin
from hero import Hero
from statuses.darkvision import DARKVISION_STATUS
from statuses.race.gnome.heritages.chameleon_gnome import CHAMELEON_GNOME_STATUS
from statuses.race.gnome.heritages.fey_touched_gnome import FEY_TOUCHED_GNOME_STATUS
from statuses.race.gnome.heritages.sensate_gnome import SENSATE_GNOME_STATUS
from statuses.race.gnome.heritages.umbral_gnome import UMBRAL_GNOME_STATUS
from statuses.race.gnome.heritages.wellspring_gnome import WELLSPRING_GNOME_STATUS


class DummyHero(StatusMixin):
    def __init__(self):
        self.statuses = []


class DummyUI:
    def __init__(self, answers: list[str]):
        self.answers = list(answers)
        self.enabled = True

    def prompt_choice(self, _prompt: str, choices=None, **_kwargs):
        if self.answers:
            return self.answers.pop(0)
        if choices:
            return choices[0]
        return None


def test_chameleon_gnome_has_runtime_stealth_bonus_data():
    data = CHAMELEON_GNOME_STATUS.data
    assert int(data.get("chameleon_stealth_bonus", 0) or 0) == 2


def test_umbral_gnome_grants_darkvision():
    hero = Hero()
    hero.add_status(UMBRAL_GNOME_STATUS)
    assert hero.has_status(DARKVISION_STATUS)


def test_sensate_gnome_has_scent_range_and_seek_hook():
    data = SENSATE_GNOME_STATUS.data
    assert int(data.get("imprecise_scent_range_feet", 0) or 0) == 30
    assert int(data.get("seek_scent_locate_bonus_within_feet", 0) or 0) == 30


def test_fey_touched_choice_records_cantrip(monkeypatch):
    dummy_ui = DummyUI(["Guidance"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: dummy_ui)
    hero = DummyHero()
    added = hero.add_status(FEY_TOUCHED_GNOME_STATUS)
    assert added is True
    assert hero.get_status_data("fey_touched_gnome", "fey_touched_cantrip", None) == "guidance"
    assert hero.get_status_data("fey_touched_gnome", "innate_magic_tradition", None) == "primal"


def test_wellspring_choice_records_tradition_and_cantrip(monkeypatch):
    dummy_ui = DummyUI(["Occult", "Daze"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: dummy_ui)
    hero = DummyHero()
    added = hero.add_status(WELLSPRING_GNOME_STATUS)
    assert added is True
    assert hero.get_status_data("wellspring_gnome", "wellspring_tradition", None) == "occult"
    assert hero.get_status_data("wellspring_gnome", "wellspring_cantrip", None) == "daze"
    assert hero.get_status_data("wellspring_gnome", "innate_magic_tradition", None) == "occult"

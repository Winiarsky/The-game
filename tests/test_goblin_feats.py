from statuses import Status
from skills import Skill
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll

from statuses.race.goblin.feats.city_scavenger import CityScavengerStatus
from statuses.race.goblin.feats.goblin_scuttle import GoblinScuttleStatus


class Dummy:
    def __init__(self):
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)


def test_city_scavenger_society_bonus():
    actor = Dummy()
    actor.add_status(CityScavengerStatus())
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.SOCIETY.value,
        dc=15,
        actor=actor,
        tags=[Skill.SOCIETY.value],
        roll=14,
        apply_modifiers=True,
    )
    assert res.modifier == 1
    assert res.total == 15
    assert res.outcome == "success"


def test_city_scavenger_survival_promote():
    actor = Dummy()
    actor.add_status(CityScavengerStatus())
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.SURVIVAL.value,
        dc=15,
        actor=actor,
        tags=[Skill.SURVIVAL.value],
        roll=14,
        apply_modifiers=True,
    )
    assert res.modifier == 1
    assert res.total == 15
    assert res.outcome == "critical_success"


def test_goblin_scuttle_duration_default():
    status = GoblinScuttleStatus()
    assert status.duration == 1


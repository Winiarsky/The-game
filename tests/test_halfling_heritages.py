from skills import Skill
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll

from statuses.race.halfling.heritages.gutsy_halfling import GutsyHalflingStatus
from statuses.race.halfling.heritages.nomadic_halfling import NomadicHalflingStatus
from statuses.race.halfling.heritages.twilight_halfling import TwilightHalflingStatus
from statuses.race.halfling.heritages.wildwood_halfling import WildwoodHalflingStatus
from statuses.low_light_vision import LOW_LIGHT_VISION_STATUS


class Dummy:
    def __init__(self):
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)


def test_gutsy_halfling_promotes_emotion_success():
    actor = Dummy()
    actor.add_status(GutsyHalflingStatus())
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.WILL.value,
        dc=15,
        actor=actor,
        tags=["emotion", Skill.WILL.value],
        roll=15,
        apply_modifiers=True,
    )
    assert res.total == 15
    assert res.outcome == "critical_success"


def test_twilight_halfling_grants_low_light():
    status = TwilightHalflingStatus()
    grants = status.data.get("grants_statuses") or []
    assert any(getattr(s, "id", None) == LOW_LIGHT_VISION_STATUS.id for s in grants)


def test_wildwood_halfling_terrain_tags():
    status = WildwoodHalflingStatus()
    tags = status.data.get("ignore_move_cost_terrain_tags")
    assert "bushes" in tags


def test_nomadic_halfling_diplomacy_bonus():
    actor = Dummy()
    actor.add_status(NomadicHalflingStatus())
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.DIPLOMACY.value,
        dc=15,
        actor=actor,
        tags=[Skill.DIPLOMACY.value],
        roll=13,
        apply_modifiers=True,
    )
    assert res.modifier == 2
    assert res.total == 15

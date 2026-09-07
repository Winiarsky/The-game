"""Deterministic configuration for the isolated, one-hero recruitment trials."""

from dataclasses import dataclass, replace

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.actors.features import FeatureGrant, FeatureSourceKind
from dnd_board_game.combat.scene import SceneFlags, scene_flag
from dnd_board_game.scenarios.loader import LoadedEncounter
from dnd_board_game.world import Coordinate

ARENA_ID = "recruitment_arena"
COMBAT_ID = "recruitment_arena_combat"
HELPER_ID = "recruitment_helper"
NESSA_POSITION = Coordinate(3, 18)
HERO_ORDER = ("garran", "brakka", "mira", "dagna", "lorian", "nimra", "erynd")


@dataclass(frozen=True)
class TrainingConfig:
    mode: str = "basic"
    creature_type: str = "humanoid"

    def __post_init__(self) -> None:
        if self.mode not in {"basic", "support", "area"}:
            raise ValueError("Nieznany wariant próby.")
        if self.creature_type not in {"humanoid", "undead", "beast"}:
            raise ValueError("Nieznany rodzaj celu treningowego.")

    @classmethod
    def from_flags(cls, flags: SceneFlags) -> "TrainingConfig":
        return cls(
            str(scene_flag(flags, "training_mode", "basic")),
            str(scene_flag(flags, "training_creature_type", "humanoid")),
        )


def configure_training_encounter(
    encounter: LoadedEncounter, config: TrainingConfig
) -> LoadedEncounter:
    if encounter.scenario_id != COMBAT_ID:
        return encounter
    dummy = next(a for a in encounter.actors if str(a.id) == "recruitment_dummy")
    dummy = replace(
        dummy,
        creature_type=config.creature_type,
        features=(
            *dummy.features,
            FeatureGrant(
                "training_fixed_damage",
                "Bezpieczna kukła",
                FeatureSourceKind.SCENARIO,
                COMBAT_ID,
                "Zagrożenie i fale nie zwiększają obrażeń treningowych.",
            ),
        ),
    )
    actors = tuple(dummy if a.id == dummy.id else a for a in encounter.actors)
    sources = dict(encounter.attack_sources_by_actor)
    options = dict(encounter.attack_source_options_by_actor)
    if config.mode == "support":
        source = sources[dummy.id]
        source = replace(
            source,
            damage_fixed=1,
            damage_modifier=0,
            damage_components=tuple(
                replace(c, fixed=1, dice=None, modifier=0)
                for c in source.damage_components
            ),
        )
        sources[dummy.id] = source
        options[dummy.id] = (source,)
        helper = Actor(
            id=HELPER_ID,
            name="Pomocnik Nessy",
            ac=10,
            hp=10,
            max_hp=30,
            temp_hp=0,
            speed_feet=0,
            position=Coordinate(9, 16),
            faction=Faction.ALLY,
        )
        # A passive recipient can participate in Lorian's physical card abilities.
        profile = tuple(
            f
            for a in actors
            if a.faction == Faction.ALLY
            for f in a.features
            if f.feature_id == "physical_mana_v02"
        )[:1]
        helper = replace(helper, features=profile)
        actors = (*actors, helper)
    if config.mode == "area":
        for number, position in ((2, Coordinate(11, 12)), (3, Coordinate(10, 11))):
            extra = replace(
                dummy,
                id=f"recruitment_dummy_{number}",
                name=f"Kukła {number}",
                position=position,
            )
            actors = (*actors, extra)
            sources[extra.id] = sources[dummy.id]
            options[extra.id] = options[dummy.id]
    return replace(
        encounter,
        actors=actors,
        attack_sources_by_actor=sources,
        attack_source_options_by_actor=options,
    )

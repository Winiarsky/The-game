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
    hero_id: str = "garran"
    step_index: int = 0

    def __post_init__(self) -> None:
        if self.mode not in {"basic", "support", "area", "tutorial", "walkthrough", "traps"}:
            raise ValueError("Nieznany wariant próby.")
        if self.creature_type not in {"humanoid", "undead", "beast"}:
            raise ValueError("Nieznany rodzaj celu treningowego.")
        if self.hero_id not in HERO_ORDER:
            raise ValueError("Nieznany bohater samouczka.")

    @classmethod
    def from_flags(cls, flags: SceneFlags) -> "TrainingConfig":
        return cls(
            str(scene_flag(flags, "training_mode", "basic")),
            str(scene_flag(flags, "training_creature_type", "humanoid")),
            str(scene_flag(flags, "training_hero", "garran")),
            int(scene_flag(flags, "walkthrough_index", 0)),
        )


def configure_training_encounter(
    encounter: LoadedEncounter, config: TrainingConfig
) -> LoadedEncounter:
    if encounter.scenario_id != COMBAT_ID:
        return encounter
    if config.mode == "walkthrough":
        from .training_walkthrough import configure_walkthrough
        base = configure_training_encounter(encounter, replace(config, mode="tutorial"))
        return configure_walkthrough(base, config.hero_id, config.step_index)
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
    if config.mode in {"support", "tutorial"}:
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
            if f.feature_id in {"physical_mana_v02", "shared_mana_v03"}
        )
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
    if config.mode == "tutorial":
        # Only figurines change; terrain, start zones and scene objects remain
        # exactly the authored arena. Helpers have no initiative of their own.
        layouts = {
            "garran": (((10, 16), (11, 16), (11, 17)), (9, 17), 2),
            "brakka": (((10, 18), (10, 17), (11, 18)), (8, 18), 6),
            "mira": (((7, 17), (7, 18), (8, 19)), (8, 17), 2),
            "dagna": (((10, 17), (11, 17), (10, 16)), (9, 17), 1),
            "lorian": (((10, 16), (11, 16), (11, 17)), (9, 17), 3),
            "nimra": (((10, 18), (10, 17), (11, 17)), (9, 17), 2),
            "erynd": (((10, 12), (11, 12), (10, 11)), (9, 17), 1),
        }
        positions, ally_position, damage = layouts[config.hero_id]
        helper = next(a for a in actors if str(a.id) == HELPER_ID)
        helper = replace(helper, position=Coordinate(*ally_position), hp=12 if config.hero_id == "dagna" else 40,
                         max_hp=80, speed_feet=30, name="Ranny pomocnik Nessy")
        actors = tuple(helper if a.id == helper.id else a for a in actors if a.id != dummy.id)
        for index, position in enumerate(positions):
            enemy = replace(dummy, id="recruitment_dummy" if index == 0 else f"recruitment_dummy_{index + 1}",
                            name="Kukła napastnika" if index == 0 else f"Kukła do ćwiczeń {index + 1}",
                            position=Coordinate(*position), hp=180, max_hp=180,
                            speed_feet=20 if index == 0 else 0,
                            creature_type="undead" if config.hero_id == "dagna" else "humanoid")
            source = replace(sources[dummy.id], damage_fixed=damage if index == 0 else 0,
                             damage_components=tuple(replace(c, fixed=damage if index == 0 else 0)
                                                     for c in sources[dummy.id].damage_components))
            actors = (*actors, enemy)
            sources[enemy.id] = source
            options[enemy.id] = (source,)
        # Garran's command can order an actual weapon attack by this recipient.
        ally_source = replace(sources[dummy.id], id="training_helper_sword", name="Miecz pomocnika",
                              damage_fixed=2, damage_components=tuple(replace(c, fixed=2)
                                                                     for c in sources[dummy.id].damage_components))
        sources[helper.id] = ally_source
        options[helper.id] = (ally_source,)
        if config.hero_id == "garran":
            second_helper = replace(helper, id=f"{HELPER_ID}_2", name="Drugi pomocnik Nessy", position=Coordinate(8, 18))
            actors = (*actors, second_helper)
            sources[second_helper.id] = ally_source
            options[second_helper.id] = (ally_source,)
    return replace(
        encounter,
        actors=actors,
        attack_sources_by_actor=sources,
        attack_source_options_by_actor=options,
    )

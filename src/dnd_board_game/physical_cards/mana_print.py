"""Current character print data, derived from the same profile as new games.

HTML/PDF rendering is at the file boundary; this module only assembles data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache

from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.character_creation.physical_mana import apply_physical_mana_profile
from dnd_board_game.character_creation.physical_mana_help import (
    physical_mana_flaw,
    physical_mana_passives,
)
from dnd_board_game.core.player_labels_pl import ABILITY_LABELS_PL, SKILL_LABELS_PL
from dnd_board_game.inventory import effective_armor_class
from dnd_board_game.inventory.armor import effective_speed_feet
from dnd_board_game.rules import ability_modifier
from dnd_board_game.rules.physical_mana import hero_abilities
from dnd_board_game.ui.combat_keyboard import shortcut_for_option
from dnd_board_game.ui.board_panel_symbols import ability_panel_slot

from dnd_board_game.scenarios.character_text import load_text, revision

PROFILE = "pooled_mana_v01"


def mana_passive_reminder() -> str:
    return load_text()['tutorial']['mana_passive_reminder']


TIMING = {"A": "Akcja główna", "D": "Akcja dodatkowa", "R": "Reakcja", "MOD": "Modyfikacja"}
COLORS = {
    "C": "Czerwona",
    "N": "Niebieska",
    "Z": "Zielona",
    "B": "Biała",
    "F": "Czarna",
    "*": "Dowolna",
}


def common_keys() -> tuple:
    return tuple(load_text()['tutorial']['common_keys'])


def turn_reminders() -> tuple:
    return tuple(load_text()['tutorial']['turn_reminders'])


@dataclass(frozen=True, slots=True)
class PrintAbility:
    id: str
    name: str
    key: str
    timing: str
    cost: tuple[str, ...]
    description: str
    panel_slot: int | None
    sections: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class PrintExploration:
    id: str
    name: str
    kind: str
    ability: str
    modifier: int
    components: tuple[tuple[str, int], ...]
    description: str
    influence_modifier: int = 0


@dataclass(frozen=True, slots=True)
class PrintHero:
    id: str
    name: str
    role: str
    level: int
    hp: int
    ac: int
    speed: int
    initiative: int
    spell_dc: int | None
    abilities: tuple[tuple[str, int, int], ...]
    weapons: tuple[str, ...]
    saves: tuple[str, ...]
    skills: tuple[str, ...]
    equipment: tuple[str, ...]
    keep: int
    capacity: int | None
    cards: tuple[PrintAbility, ...]
    passives: tuple[tuple[str, str], ...]
    flaw: tuple[str, str]
    story: tuple[tuple[str, str], ...]
    exploration: tuple[PrintExploration, ...] = ()
    mana_values: tuple[tuple[str, int], ...] = ()
    exploration_passives: tuple[tuple[str, str], ...] = ()
    mana_passives: tuple[tuple[str, str], ...] = ()
    stacking_mana_colors: tuple[str, ...] = ()
    stacking_exploration_colors: tuple[str, ...] = ()

    def as_payload(self) -> dict[str, object]:
        return {"rules_profile": PROFILE, **asdict(self)}


@dataclass(frozen=True, slots=True)
class _KeyOption:
    id: str
    source_id: str
    action_id: str
    action: str = ""
    category: str = ""


def ability_key(hero_id: str, ability_id: str, timing: str) -> str:
    if timing == "R":
        return "AUTO"
    option_id = {"grapple": "turn:grapple", "hide": "basic:hide"}.get(ability_id, ability_id)
    return shortcut_for_option(hero_id, _KeyOption(option_id, ability_id, ability_id)) or "MENU"


def build_print_hero(hero_id: str, *, rune_profile: bool = False) -> PrintHero:
    return _build_print_hero(hero_id, revision(), rune_profile)


@lru_cache(maxsize=14)
def _build_print_hero(hero_id: str, text_revision: tuple[str, int, int], rune_profile: bool = False) -> PrintHero:
    # Reuse the canonical curated starter build; no fixed copies of HP/AC/scores.
    from .character_card_sets import _starter_builds, _SKILL_ABILITIES
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    from dnd_board_game.combat import attack_source_for_actor
    from dnd_board_game.scenarios.confrontation import passives as exploration_passives
    from dnd_board_game.scenarios.confrontation_terms import effect_text

    if hero_id not in PLAYABLE_HERO_IDS:
        raise ValueError(f"Nieznany bohater: {hero_id}")
    actor = apply_physical_mana_profile(_starter_builds()[1][hero_id][1].actor)
    if rune_profile:
        from dnd_board_game.character_creation.runes import apply_rune_profile
        actor = apply_rune_profile(actor)
    from dnd_board_game.scenarios.character_text import hero_text, present_ability
    profile = hero_text(hero_id)
    ability_ids = ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")
    scores = tuple(
        (
            ABILITY_LABELS_PL[a],
            getattr(actor.ability_scores, a),
            ability_modifier(getattr(actor.ability_scores, a)),
        )
        for a in ability_ids
    )
    saves = tuple(
        f"{ABILITY_LABELS_PL[a]} {ability_modifier(getattr(actor.ability_scores, a)):+d}"
        for a in ability_ids
    )
    skills = tuple(
        f"{SKILL_LABELS_PL[s]} {ability_modifier(getattr(actor.ability_scores, _SKILL_ABILITIES[s])):+d}"
        for s in sorted(actor.proficiencies.skills)
    )
    compiled = compile_actor_combat_content(actor)
    best_weapons = {}
    for source in compiled.attack_sources:
        source = attack_source_for_actor(source, actor)
        if not source.proficiency_id or source.source_type.value != "weapon":
            continue
        identity = (source.proficiency_id, source.attack_kind)
        bonus = sum(m.value for m in source.attack_roll_request.modifiers)
        if identity not in best_weapons or bonus > best_weapons[identity][0]:
            damage = " + ".join(c.hint() for c in source.damage_components).replace("1d", "1k")
            best_weapons[identity] = (bonus, f"{source.name}: {bonus:+d} do trafienia; {damage}")
    weapons = tuple(value[1] for value in best_weapons.values())
    from dnd_board_game.scenarios.pooled_mana_catalog import requirement_text, ability_description, hero_profile
    from .mana_ability_text import ability_sections
    cards = tuple(
        PrintAbility(
            a.id, a.name, ability_key(hero_id, a.id, a.timing), a.timing, (), requirement_text(a.id, hero_id) + " " + ability_description(hero_id, a.id),
            ability_panel_slot(hero_id, a.id), ability_sections(hero_id, a.id),
        )
        for a in map(present_ability, hero_abilities(hero_id))
    )
    from dnd_board_game.scenarios.rune_traits import rune_flaw
    flaw = rune_flaw(hero_id) if rune_profile else physical_mana_flaw(hero_id)
    role = profile['role']
    return PrintHero(
        hero_id,
        actor.name,
        role,
        actor.level,
        actor.max_hp,
        effective_armor_class(actor),
        effective_speed_feet(actor),
        ability_modifier(actor.ability_scores.dexterity)
        + (2 if any(f.feature_id == "scouts_vigilance" for f in actor.features) else 0),
        actor.spell_save_dc,
        scores,
        weapons,
        saves,
        skills,
        tuple(f"{item.name} ×{item.quantity}" for item in actor.inventory) + (("Święty symbol: A · " + requirement_text("turn_undead", hero_id) + " Nieumarli w 15 ft: obrona MDR; porażka odpędza do początku następnej tury Dagny. Obrażenia kończą wcześniej.",) if hero_id == "dagna" and not rune_profile else ()),
        1,
        None,
        cards,
        tuple((n.name, n.body) for n in physical_mana_passives(hero_id)),
        (flaw.name, flaw.body),
        (
            ("Historia", profile['history']),
            ("Dlaczego podróżuje", profile['motivation']),
            ("Cel osobisty", profile['personal_goal']),
        ),
        tuple(PrintExploration(kind, 'Podejście ze sceny', kind, 'Cecha podejścia', 0, (),
              'Wybierz runą podejście dostępne w tej scenie. Określa cechę, ST, kość efektu i dozwolone wsparcie. Wybór zostaje do końca konfrontacji.')
              for kind in ('npc', 'object')),
        tuple(hero_profile(hero_id)["values"].items()),
        tuple((c, effect_text(p["label"], None)) for c, p in exploration_passives(hero_id).items()),
        tuple((c, p["label"]) for c, p in hero_profile(hero_id)["color_passives"].items()),
        tuple(c for c, p in hero_profile(hero_id)["color_passives"].items() if p['stackable']),
        tuple(c for c, p in exploration_passives(hero_id).items() if p['stackable']),
    )

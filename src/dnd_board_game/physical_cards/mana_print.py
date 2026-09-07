"""Current character print data, derived from the same profile as new games.

HTML/PDF rendering is at the file boundary; this module only assembles data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache

from dnd_board_game.character_creation import PLAYABLE_HERO_IDS, HERO_ARCHETYPES_BY_ID
from dnd_board_game.character_creation.physical_mana import apply_physical_mana_profile
from dnd_board_game.character_creation.physical_mana_help import (
    physical_mana_flaw,
    physical_mana_passives,
)
from dnd_board_game.core.player_labels_pl import ABILITY_LABELS_PL, SKILL_LABELS_PL
from dnd_board_game.inventory import effective_armor_class
from dnd_board_game.inventory.armor import effective_speed_feet
from dnd_board_game.rules import ability_modifier
from dnd_board_game.rules.physical_mana import hero_abilities, turn_supply
from dnd_board_game.ui.combat_keyboard import shortcut_for_option

PROFILE = "physical_mana_v02"
TIMING = {"A": "Akcja główna", "D": "Akcja dodatkowa", "R": "Reakcja", "MOD": "Modyfikacja"}
COLORS = {
    "C": "Czerwona",
    "N": "Niebieska",
    "Z": "Zielona",
    "B": "Biała",
    "F": "Czarna",
    "*": "Dowolna",
}
COMMON_KEYS = (
    (
        "SPACJA",
        "Atak",
        "Jedna akcja: jeden zwykły atak za 1 dowolną manę. Tylko Lorian deklaruje serię: po 1 dowolnej za atak, osobne cele i rzuty.",
    ),
    (
        "M",
        "Ruch",
        "1 dowolna mana raz na turę. Trudny teren zwiększa koszt w stopach; 1 pole = 5 ft.",
    ),
    ("B", "Broń", "Otwórz wybór broni; koszt wykonania pokazuje aplikacja."),
    (
        "I",
        "Przedmiot",
        "Otwórz wybór przedmiotu; użycie podstawowe kosztuje 1 dowolną manę, a czas działania wskazuje aplikacja.",
    ),
    ("0", "Koniec tury", "Rozlicz skazę, zachowaj rezerwę, dobierz do 3 i uzupełnij rynek."),
    ("ENTER", "Potwierdź", "Wykonaj wybrane działanie; płatność kartami rozliczacie przy stole."),
    ("ESC", "Wróć", "Anuluj podgląd bez płatności. Backspace także wraca."),
)
TURN_REMINDERS = (
    "Jedna akcja główna, najwyżej jedna dodatkowa i jedna reakcja między własnymi turami. Mana nie przyznaje dodatkowych akcji.",
    "Start walki: 3 karty. Na początku tury nie dobierasz. Po skazie zachowaj starą rezerwę i wybierz do 3 kart rynku; uzupełnij go dopiero po wyborze.",
    "Koszt techniki zawiera wskazane ataki i ruch. Zwykły Atak: jedno uderzenie. Tylko Lorian wybiera liczbę zwykłych ataków; każdy kosztuje 1 dowolną manę. Zwrot many nie dodaje ataków.",
    "Dwie dowolne karty zastępują wymagany kolor. Raz w swojej turze przeciąż kartę: dowolny kolor za odrzucenie 2 wierzchnich kart talii.",
    "Karty wydaj przy wykonaniu, przed rzutem. Aplikacja nie kontroluje ręki ani płatności. Limity pasywów karcianych oznaczacie przy stole.",
    "Koniec rundy: odrzuć lewą kartę rynku i uzupełnij. Przewinięcia talii zgłaszaj jako fale w aplikacji.",
)


@dataclass(frozen=True, slots=True)
class PrintAbility:
    id: str
    name: str
    key: str
    timing: str
    cost: tuple[str, ...]
    description: str


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
    capacity: int
    cards: tuple[PrintAbility, ...]
    passives: tuple[tuple[str, str], ...]
    flaw: tuple[str, str]
    story: tuple[tuple[str, str], ...]

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


@lru_cache(maxsize=7)
def build_print_hero(hero_id: str) -> PrintHero:
    # Reuse the canonical curated starter build; no fixed copies of HP/AC/scores.
    from .character_card_sets import _starter_builds, _SKILL_ABILITIES
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    from dnd_board_game.combat import attack_source_for_actor

    if hero_id not in PLAYABLE_HERO_IDS:
        raise ValueError(f"Nieznany bohater: {hero_id}")
    actor = apply_physical_mana_profile(_starter_builds()[1][hero_id][1].actor)
    profile = HERO_ARCHETYPES_BY_ID[hero_id]
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
        f"{ABILITY_LABELS_PL[a]} {ability_modifier(getattr(actor.ability_scores, a)) + (actor.proficiency_bonus if a in actor.proficiencies.saving_throws else 0):+d}"
        for a in ability_ids
    )
    skills = tuple(
        f"{SKILL_LABELS_PL[s]} {ability_modifier(getattr(actor.ability_scores, _SKILL_ABILITIES[s])) + actor.proficiency_bonus * (2 if s in actor.proficiencies.expertise else 1):+d}"
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
    supply = turn_supply(hero_id)
    cards = tuple(
        PrintAbility(
            a.id, a.name, ability_key(hero_id, a.id, a.timing), a.timing, a.cost, a.description
        )
        for a in hero_abilities(hero_id)
    )
    flaw = physical_mana_flaw(hero_id)
    role = "Bard — zarządzanie maną, kusza i kontrola" if hero_id == "lorian" else profile.role
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
        tuple(f"{item.name} ×{item.quantity}" for item in actor.inventory),
        supply["keep"],
        supply["capacity"],
        cards,
        tuple((n.name, n.body) for n in physical_mana_passives(hero_id)),
        (flaw.name, flaw.body),
        (
            ("Historia", profile.history),
            ("Dlaczego podróżuje", profile.motivation),
            ("Cel osobisty", profile.personal_goal),
        ),
    )

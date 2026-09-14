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
from dnd_board_game.ui.board_panel_symbols import ability_panel_slot

PROFILE = "shared_mana_v03"
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
    ("", "Atak", "Jedna akcja główna: jeden zwykły atak bez many. Skaza może wymagać dopłaty przed rzutem."),
    ("", "Ruch", "Bez many. Możesz dzielić ruch na odcinki; pole to 5 ft. Trudny teren zwiększa koszt w stopach."),
    ("", "Broń", "Wybierz broń lub chwyt; aplikacja pokazuje koszt zmiany."),
    ("", "Przedmiot", "Otwórz ekwipunek; czas działania i koszt wskazuje opis przedmiotu."),
    ("", "Koniec tury", "Rozlicz efekty i uzupełnij wspólny rynek do pięciu kart, potem potwierdź fizyczny dobór."),
    ("✓", "Potwierdź", "Potwierdź wybór, płatność, wynik rzutu lub fizyczną operację kart przyciskiem w rogu planszy."),
    ("↩", "Wróć", "Anuluj podgląd przed płatnością. Opłacone działanie trzeba rozstrzygnąć."),
)
TURN_REMINDERS = (
    "Wspólna talia: 25 kart, po 5 każdego koloru. Wyłóż rynek 5 kart, w talii pozostaje 20; bez prywatnych rąk.",
    "Zadeklaruj akcję, cele i podbicia. Pełny koszt, razem ze skazami, mieści się w 5 kartach. Symbol dowolny opłać wybranym kolorem.",
    "Odłóż koszt z rynku na odrzucone i potwierdź, potem wykonaj akcję. Odzysk może zwrócić karty wydane na tę samą akcję.",
    "Nie uzupełniaj rynku w środku akcji. Po efektach końca tury uzupełnij go do 5 kart, na ile wystarczy talii, i potwierdź dobór.",
    "Po wyczerpaniu talii, jeśli bohater nie wydał many w swojej turze, po doborze odrzuć 1 kartę rynku bez ponownego uzupełniania. Pusty rynek i talia otwierają odświeżenie po zakończeniu akcji.",
    "Odświeżenie: zbierz wszystkie 25 kart, także rynek, przetasuj i wyłóż nowy rynek 5. Zgłoś odświeżenie w aplikacji i potwierdź ✓.",
    "T: do początku następnej tury bohatera będącego źródłem. O: do potwierdzonego odświeżenia talii. Koncentracja i opisane warunki mogą zakończyć efekt wcześniej.",
    "Jedna akcja główna, jedna dodatkowa i jedna reakcja między własnymi turami. Hymn daje drugą akcję dodatkową; nadal płać manę i zachowuj limity użyć.",
    "Dolny pasek run na mapie jest wyłączony. Używaj ikon w aplikacji; −, +, ✓ i ↩ pozostają aktywne w dotychczasowym rogu.",
)


@dataclass(frozen=True, slots=True)
class PrintAbility:
    id: str
    name: str
    key: str
    timing: str
    cost: tuple[str, ...]
    description: str
    panel_slot: int | None


@dataclass(frozen=True, slots=True)
class PrintExploration:
    id: str
    name: str
    kind: str
    ability: str
    modifier: int
    components: tuple[tuple[str, int], ...]
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
    exploration: tuple[PrintExploration, ...] = ()

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
    from dnd_board_game.application.exploration_mana_flow import method_modifiers
    from dnd_board_game.rules.exploration_mana_catalog import hero_methods

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
            a.id, a.name, ability_key(hero_id, a.id, a.timing), a.timing, a.cost, a.description,
            ability_panel_slot(hero_id, a.id),
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
        tuple(f"{item.name} ×{item.quantity}" for item in actor.inventory) + (("Święty symbol: A · niebieska + biała. Nieumarli w 15 ft: obrona MDR; porażka odpędza do początku następnej tury Dagny. Obrażenia kończą wcześniej.",) if hero_id == "dagna" else ()),
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
        tuple(PrintExploration(m.id, m.name, m.kind, ABILITY_LABELS_PL[m.ability],
              sum(part.value for part in method_modifiers(actor, m)),
              tuple((part.label, part.value) for part in method_modifiers(actor, m)), m.description)
              for m in hero_methods(hero_id)),
    )

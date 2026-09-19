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
from dnd_board_game.rules.physical_mana import hero_abilities
from dnd_board_game.ui.combat_keyboard import shortcut_for_option
from dnd_board_game.ui.board_panel_symbols import ability_panel_slot

PROFILE = "pooled_mana_v01"
MANA_PASSIVE_REMINDER = (
    "Pasywy są zablokowane, dopóki nie masz karty odpowiedniego koloru. "
    "Gruba obwódka symbolu: kumuluje się za kolejne karty tego koloru (według limitu). Cienka: nie kumuluje się. "
    "Utrata ostatniej karty koloru, drain i koniec walki wyłączają pasyw. "
    "Drain resetuje użycie Nieustępliwości; nowa czarna mana odblokowuje ją ponownie. Odzyskane PW pozostają. Dobór do 21+ pkt."
)
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
    ("", "Atak", "Jedna akcja główna: k20 + cecha + naładowanie + inne premie. Zwykły atak nie spala kart; pula zostaje."),
    ("", "Ruch", "Bez many. Możesz dzielić ruch na odcinki; pole to 5 ft. Trudny teren zwiększa koszt w stopach."),
    ("", "Broń", "Wybierz broń lub chwyt; aplikacja pokazuje koszt zmiany."),
    ("", "Przedmiot", "Otwórz ekwipunek; czas działania i koszt wskazuje opis przedmiotu."),
    ("", "Koniec tury", "Rozlicz efekty. Zachowaj pulę; dobór następuje na początku kolejnej własnej tury."),
    ("✓", "Potwierdź", "Potwierdź wybór, płatność, wynik rzutu lub fizyczną operację kart przyciskiem w rogu planszy."),
    ("↩", "Wróć", "Anuluj podgląd przed płatnością. Opłacone działanie trzeba rozstrzygnąć."),
)
TURN_REMINDERS = (
    "Każdą walkę zacznij od zebrania i przetasowania kompletu. Liczba kart: po max(5, 2 × liczba bohaterów) każdego z pięciu kolorów.",
    "Odkryj dwie karty. Poniżej 21 pkt na początku własnej tury weź jedną do puli; druga zostaje dla następnego bohatera. Przed jego wyborem uzupełnij ofertę do dwóch.",
    "Karty przechodzą między turami. Punkty 6/12/21 odblokowują zdolności. Przy 21+ pkt przestajesz dobierać do mana draina. Kolory uruchamiają osobne pasywy.",
    "Zdolność zachowuje CAŁĄ pulę. Bazowe użycie spala 1 kartę z wierzchu po efekcie, każde podbicie +2 karty. Wyjątki podano na kartach. Nie potrzebujesz koloru podbicia w puli.",
    "Test ataku, działania lub obrony: k20 + cecha + naładowanie + inne premie. Trafienie porównaj z KP. Zamiast biegłości: 0/6/12/21 pkt daje +0/+2/+4/+6. Naładowanie nie zwiększa obrażeń.",
    "Zwykły atak jest bez many. Darmowe zdolności zachowują pulę, nadal zużywają swoją akcję lub reakcję. Ruch działa normalnie.",
    "Spalone karty leżą osobno. Co rundę 1 karta z wierzchu wygasa; nie można jej odzyskać przed drainem. Uwięzione pozostają przy przeciwniku; po jego pokonaniu wracają na spód talii.",
    "Jeśli nie można wykonać pełnego spalenia/uwięzienia, następuje mana drain. Także gdy przy obowiązkowym doborze brak karty zarówno w ofercie, jak i w talii.",
    "Drain: zbierz i przetasuj WSZYSTKIE karty, również osobiste pule, spalone, wygasłe i uwięzione. Wyłóż nową ofertę. Drain nie odnawia akcji, reakcji ani pasywek i nie daje dodatkowego doboru.",
    "T: do początku następnej tury źródła. O: do mana draina; koncentracja i opisane warunki mogą zakończyć wcześniej. Premie kolorów również znikają przy drainie.",
    "Runy wybierają kolory, karty i zdolności. Rzuty: fokus jednej kości, −/+, ✓ do następnej, podsumowanie i końcowe ✓. ↩ pozwala poprawić wynik.",
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


@lru_cache(maxsize=7)
def build_print_hero(hero_id: str) -> PrintHero:
    # Reuse the canonical curated starter build; no fixed copies of HP/AC/scores.
    from .character_card_sets import _starter_builds, _SKILL_ABILITIES
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    from dnd_board_game.combat import attack_source_for_actor
    from dnd_board_game.scenarios.confrontation import passives as exploration_passives
    from dnd_board_game.scenarios.confrontation_terms import effect_text

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
        tuple(f"{item.name} ×{item.quantity}" for item in actor.inventory) + (("Święty symbol: A · " + requirement_text("turn_undead", hero_id) + " Nieumarli w 15 ft: obrona MDR; porażka odpędza do początku następnej tury Dagny. Obrażenia kończą wcześniej.",) if hero_id == "dagna" else ()),
        1,
        None,
        cards,
        tuple((n.name, n.body) for n in physical_mana_passives(hero_id)),
        (flaw.name, flaw.body),
        (
            ("Historia", profile.history),
            ("Dlaczego podróżuje", profile.motivation),
            ("Cel osobisty", profile.personal_goal),
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

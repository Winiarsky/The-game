"""Shared exploration methods and physical-card rules; no runtime or I/O."""
from __future__ import annotations

from dataclasses import dataclass

COLORS = ("C", "B", "Z", "F", "N")
COLOR_NAMES = ("Czerwona", "Biała", "Zielona", "Czarna", "Niebieska")
HEROES = ("garran", "brakka", "mira", "dagna", "lorian", "nimra", "erynd")
RULES_VERSION = 2
CONDITION_HELP = (
    ('Częściowe porozumienie', 'Pierwsze wejście w 15–17 otwiera ofertę. Klucz przyjmuje częściowy rezultat bez rzutu; Gwiazda odrzuca i wraca do pas/dobór. Oferta nie wraca.'),
    ('Drażliwy temat', 'Wybrany wskazany kolor zmienia korzyść i cenę sukcesu. Samo odkrycie karty nie liczy się. Cena pozostaje przy dokładnym 21 i po przerzucie.'),
    ('Dodatkowy cel', 'Zbierz dwie karty wskazanego koloru. Dodatkową nagrodę otrzymasz raz przy sukcesie, również przy 21 lub wygranej z utrudnieniem. Porażka nie daje nagrody.'),
    ('Przysługa za przysługę', 'Raz w próbie: Klucz pozwala wybrać kartę za 1 w zamian za jawne zobowiązanie. Gwiazda wyłącza ustępstwo przed wyborem. Wybór koloru przyjmuje zobowiązanie, które pozostaje także po porażce.'),
)
REMINDER = (
    "Eksploracja: przygotuj 25 kart, po 5 każdego koloru, bez rynku. "
    "Dobierz 2 i wybierz 1; resztę odrzuć. Przy tym samym kolorze możesz dobierać "
    "do pierwszej innej barwy, nadal zatrzymując jedną kartę. "
    "Pas lub dalszy dobór zadeklaruj przed odkryciem następnej oferty. "
    "1–10: +0; 11–14: +1; 15–17: +2; 18–19: +4; 20: +6; 21: sukces bez rzutu. "
    "Przekroczenie: brak premii za karty, test z utrudnieniem (2k20, niższy wynik). "
    "Dodaj właściwą cechę, należną biegłość i osobisty pasyw. "
    "Nie tasuj ponownie w środku próby. Brak kart wymusza zwykły pas."
)


@dataclass(frozen=True, slots=True)
class ExplorationMethod:
    id: str
    hero_id: str
    kind: str
    name: str
    ability: str
    proficiency: str
    description: str


METHODS = (
    ExplorationMethod("authority", "garran", "npc", "Autorytet", "strength", "intimidation", "Przejmij inicjatywę zdecydowaną obecnością i odpowiedzialnością za sytuację."),
    ExplorationMethod("intimidation", "brakka", "npc", "Zastraszanie", "constitution", "intimidation", "Wytrzymaj nacisk i pokaż, że nie ustąpisz. Test Kondycji, nie rzut obronny."),
    ExplorationMethod("deception", "mira", "npc", "Blef", "intelligence", "deception", "Zbuduj sprytne, spójne kłamstwo lub pozór."),
    ExplorationMethod("empathy", "dagna", "npc", "Empatia", "wisdom", "insight", "Rozpoznaj obawy rozmówcy i odwołaj się do jego potrzeb."),
    ExplorationMethod("inspiration", "lorian", "npc", "Inspiracja", "charisma", "persuasion", "Porusz rozmówcę i zachęć go do współpracy."),
    ExplorationMethod("argument", "nimra", "npc", "Argumentacja", "intelligence", "investigation", "Przedstaw rozumowanie i dowody prowadzące do porozumienia."),
    ExplorationMethod("inquiry", "erynd", "npc", "Dociekliwość", "wisdom", "investigation", "Wychwyć szczegół lub niespójność i zadaj właściwe pytanie."),
    ExplorationMethod("secure", "garran", "object", "Zabezpieczenie", "constitution", "athletics", "Utrzymaj konstrukcję stabilną i bezpiecznie zwolnij naprężenia."),
    ExplorationMethod("force", "brakka", "object", "Forsowanie", "strength", "athletics", "Pokonaj opór siłą: podnieś, wyważ lub rozerwij blokadę."),
    ExplorationMethod("manipulate", "mira", "object", "Manipulacja", "dexterity", "thieves_tools", "Precyzyjnie zwolnij zamek, zatrzask lub drobny mechanizm przy użyciu narzędzi."),
    ExplorationMethod("cleanse", "dagna", "object", "Oczyszczenie", "wisdom", "medicine", "Przywróć bezpieczne użycie skażonego obiektu dostępnymi środkami."),
    ExplorationMethod("improvise", "lorian", "object", "Pomysłowość", "intelligence", "investigation", "Znajdź obejście problemu i wykorzystaj dostępne części."),
    ExplorationMethod("analyze", "nimra", "object", "Analiza", "intelligence", "arcana", "Odczytaj symbole i zastosuj właściwą sekwencję obsługi urządzenia."),
    ExplorationMethod("survey", "erynd", "object", "Rozpoznanie", "wisdom", "perception", "Ze śladów używania odczytaj bezpieczny sposób obsługi."),
)

# These names describe arithmetic, not an unproven universal difficulty ordering.
PROFILES = (("fine", (7, 1, 1, 3, 5)), ("balanced", (7, 2, 3, 4, 5)), ("coarse", (7, 6, 5, 3, 2)))
OBSTACLES = (
    ("none", "Bez dodatkowej przeszkody", "Karty mają wartości z tabeli."),
    ("repeat", "Powtarzasz się", "Ten sam wybrany kolor co poprzednio ma +2. Pierwsza karta bez dopłaty."),
    ("after_red", "Rozchwianie", "Po czerwonej następna wybrana karta ma +2. Efekt nie kumuluje się."),
    ("four", "Krótka okazja", "Najwyżej cztery wybrane karty, potem zwykły pas. Odrzucone duplikaty nie liczą się do limitu."),
)


def method_by_id(method_id: str) -> ExplorationMethod:
    for method in METHODS:
        if method.id == method_id:
            return method
    raise ValueError("Nieznana metoda eksploracji.")


def hero_methods(hero_id: str) -> tuple[ExplorationMethod, ...]:
    return tuple(method for method in METHODS if method.hero_id == hero_id)


def profile_values(profile_id: str) -> tuple[int, ...]:
    for name, values in PROFILES:
        if name == profile_id:
            return values
    raise ValueError("Nieznany profil many.")


def obstacle_description(obstacle: str) -> tuple[str, str]:
    for key, name, description in OBSTACLES:
        if key == obstacle:
            return name, description
    raise ValueError("Nieznana przeszkoda.")

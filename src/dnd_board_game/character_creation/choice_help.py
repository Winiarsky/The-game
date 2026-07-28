"""Polish guidance for player decisions made in the class-choice step."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SkillChoiceHelp:
    ability_id: str
    description: str
    examples: str


@dataclass(frozen=True, slots=True)
class FightingStyleHelp:
    name: str
    rule_text: str
    play_text: str


SKILL_CHOICE_HELP = {
    "acrobatics": SkillChoiceHelp("dexterity", "Równowaga, akrobacje i utrzymanie się na nogach.", "chodzenie po belce, salto, wyrwanie się z chwytu"),
    "animal_handling": SkillChoiceHelp("wisdom", "Rozumienie zachowania zwierząt i uspokajanie ich.", "uspokojenie konia, kontrola wierzchowca"),
    "arcana": SkillChoiceHelp("intelligence", "Wiedza o magii, czarach, planach i magicznych stworzeniach.", "rozpoznanie rytuału lub magicznego symbolu"),
    "athletics": SkillChoiceHelp("strength", "Wysiłek fizyczny oparty na sile.", "wspinaczka, skok, pływanie, chwyt i odepchnięcie"),
    "deception": SkillChoiceHelp("charisma", "Wiarygodne kłamstwo, blef i ukrywanie intencji.", "fałszywa historia, odwracanie podejrzeń"),
    "history": SkillChoiceHelp("intelligence", "Wiedza o dawnych wydarzeniach, ludach i konfliktach.", "rozpoznanie herbu lub historycznej ruiny"),
    "insight": SkillChoiceHelp("wisdom", "Odczytywanie emocji, zamiarów i nieszczerości.", "wyczucie kłamstwa lub strachu NPC"),
    "intimidation": SkillChoiceHelp("charisma", "Wymuszanie ustępstw groźbą, postawą lub demonstracją siły.", "zastraszenie strażnika lub jeńca"),
    "investigation": SkillChoiceHelp("intelligence", "Logiczne łączenie śladów i dokładne badanie przedmiotów.", "odnalezienie mechanizmu albo ukrytej skrytki"),
    "medicine": SkillChoiceHelp("wisdom", "Ocena obrażeń, chorób i stanu żywej istoty.", "stabilizacja umierającego, rozpoznanie objawów"),
    "nature": SkillChoiceHelp("intelligence", "Wiedza o roślinach, zwierzętach, pogodzie i terenie.", "rozpoznanie trucizny lub śladów bestii"),
    "perception": SkillChoiceHelp("wisdom", "Zauważanie bodźców i zagrożeń zmysłami.", "usłyszenie zasadzki, dostrzeżenie ukrytego wroga"),
    "performance": SkillChoiceHelp("charisma", "Zabawianie publiczności muzyką, grą lub opowieścią.", "występ w gospodzie, odwrócenie uwagi tłumu"),
    "persuasion": SkillChoiceHelp("charisma", "Przekonywanie innych uczciwymi argumentami i taktem.", "negocjacje, prośba o pomoc, uspokojenie sporu"),
    "religion": SkillChoiceHelp("intelligence", "Wiedza o bóstwach, kultach, obrzędach i symbolach.", "rozpoznanie świętego znaku lub rytuału"),
    "sleight_of_hand": SkillChoiceHelp("dexterity", "Precyzyjne i dyskretne manipulowanie drobnymi przedmiotami.", "kieszonkostwo, ukrycie przedmiotu"),
    "stealth": SkillChoiceHelp("dexterity", "Poruszanie się i działanie bez zwracania uwagi.", "skradanie, ukrycie przed wartownikiem"),
    "survival": SkillChoiceHelp("wisdom", "Tropienie, orientacja i radzenie sobie w dziczy.", "śledzenie potwora, nawigacja, zdobywanie pożywienia"),
}


FIGHTING_STYLE_HELP = {
    "archery": FightingStyleHelp(
        "Łucznictwo",
        "Otrzymujesz +2 do rzutów ataku wykonywanych bronią dystansową.",
        "Najlepsze dla postaci regularnie używającej łuku lub kuszy; premia jest doliczana automatycznie.",
    ),
    "defense": FightingStyleHelp(
        "Obrona",
        "Kiedy nosisz pancerz, otrzymujesz +1 do Klasy Pancerza.",
        "Uniwersalny wybór defensywny. Karta i walka automatycznie uwzględniają premię po założeniu pancerza.",
    ),
    "dueling": FightingStyleHelp(
        "Walka jedną bronią",
        "Gdy dzierżysz broń jednoręczną i nie trzymasz innej broni, otrzymujesz +2 do obrażeń tą bronią.",
        "Działa także z tarczą w drugiej ręce. Silnik sprawdza układ dłoni przy każdym ataku.",
    ),
    "great_weapon_fighting": FightingStyleHelp(
        "Walka bronią dwuręczną",
        "Przy wyniku 1 lub 2 na kości obrażeń broni dwuręcznej albo uniwersalnej używanej oburącz możesz przerzucić tę kość.",
        "Opcja dla ciężkich broni; interfejs walki prowadzi przez wymagany fizyczny przerzut.",
    ),
    "protection": FightingStyleHelp(
        "Ochrona",
        "Reakcją nakładasz utrudnienie na atak przeciw pobliskiemu sojusznikowi, gdy używasz tarczy.",
        "W odpowiednim oknie reakcji aplikacja pokaże możliwość ochrony celu znajdującego się obok.",
    ),
    "two_weapon_fighting": FightingStyleHelp(
        "Walka dwiema broniami",
        "Do obrażeń ataku drugą lekką bronią dodajesz swój modyfikator cechy.",
        "Dla postaci walczącej dwiema lekkimi broniami; premia jest stosowana automatycznie do legalnego ataku dodatkowego.",
    ),
}


CLASS_CHOICE_GROUP_HELP = {
    "bard_instruments": (
        "Wybierasz instrument, w którego używaniu postać ma biegłość. "
        "Biegłość dodaje premię +2 do odpowiednich testów; sam instrument "
        "musi znajdować się w ekwipunku."
    ),
    "favored_enemy": (
        "Wybierz rodzaj przeciwnika, którego łowca zna najlepiej. W pasujących "
        "testach tropienia i wiedzy aplikacja uwzględni przewagę."
    ),
    "favored_enemy_humanoid_races": (
        "Ten wybór pojawia się tylko po wskazaniu humanoidów. Zamiast całego "
        "typu wybierasz dwie konkretne rasy humanoidów."
    ),
    "natural_explorer": (
        "Wybierz teren, na którym łowca jest specjalistą. Korzyści działają "
        "w podróży przez sceny oznaczone tym typem terenu."
    ),
}


__all__ = [
    "CLASS_CHOICE_GROUP_HELP",
    "FIGHTING_STYLE_HELP",
    "SKILL_CHOICE_HELP",
    "FightingStyleHelp",
    "SkillChoiceHelp",
]

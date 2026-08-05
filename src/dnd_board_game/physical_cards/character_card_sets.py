"""Character-specific printable decision-card decks for the starter roster."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from dnd_board_game.character_creation import (
    ABILITY_IDS,
    HERO_ARCHETYPES_BY_ID,
    SRD_CLASS_SPELL_IDS,
    build_character,
    apply_boardgame_archetype,
    default_character_drafts,
    load_character_catalog,
    load_character_resources,
)
from dnd_board_game.core.player_labels_pl import (
    ABILITY_LABELS_PL,
    SKILL_LABELS_PL,
    SPELL_NAMES_PL,
    TOOL_LABELS_PL,
)
from dnd_board_game.inventory.armor import effective_armor_class, effective_speed_feet
from dnd_board_game.rules import ability_modifier

from .hero_card_sheet import HERO_CARD_SPECS, HERO_PORTRAIT_ROOT, render_hero_card_front
from .action_catalog import CardPhase, card_action_definition
from .qr_payload import build_decision_card_qr_payload
from .universal_card_sheet import (
    A4_SIZE_PX,
    BLEED_MM,
    BLEED_PX,
    CARD_ART_SIZE_PX,
    CARD_HEIGHT_MM,
    CARD_SIZE_PX,
    CARD_WIDTH_MM,
    DPI,
    PROJECT_ROOT,
    QR_TARGET_MM,
    SAFE_MARGIN_MM,
    _draw_crop_marks,
    _font,
    _mm,
    _qr_image,
)


CHARACTER_SET_ROOT = PROJECT_ROOT / "assets" / "physical_cards" / "character_sets"
CHARACTER_SET_ART_ROOT = CHARACTER_SET_ROOT / "art"


@dataclass(frozen=True, slots=True)
class CharacterActionCardSpec:
    source_id: str
    title: str
    kind: str
    required_level: int
    timing: str
    mechanic: str
    flavor: str
    art_asset: str
    accent: tuple[int, int, int]

    @property
    def payload(self) -> str:
        return build_decision_card_qr_payload(self.kind, self.source_id)

    def payload_for(self, actor_id: str) -> str:
        if self.kind == "universal":
            return self.payload
        return build_decision_card_qr_payload(
            self.kind,
            self.source_id,
            actor_id=actor_id,
        )


@dataclass(frozen=True, slots=True)
class CharacterDeckSpec:
    actor_id: str
    deck_title: str
    subtitle: str
    accent: tuple[int, int, int]
    secondary: tuple[int, int, int]
    back_asset: str
    action_cards: tuple[CharacterActionCardSpec, ...]
    dossier_intro: str
    dossier_campaign: str
    passives: tuple[str, ...]
    progression: tuple[str, ...]

    @property
    def profile(self):
        return HERO_ARCHETYPES_BY_ID[self.actor_id]


@dataclass(frozen=True, slots=True)
class CharacterCardSetResult:
    pdf_path: Path
    manifest_path: Path
    card_count: int
    page_count: int


def _card(
    source_id: str,
    title: str,
    kind: str,
    level: int,
    timing: str,
    mechanic: str,
    flavor: str,
    art_asset: str,
    accent: tuple[int, int, int],
) -> CharacterActionCardSpec:
    return CharacterActionCardSpec(
        source_id,
        title,
        kind,
        level,
        timing,
        mechanic,
        flavor,
        art_asset,
        accent,
    )


GARRAN_BLUE = (91, 135, 168)
GARRAN_STEEL = (179, 190, 194)
DAGNA_GOLD = (218, 168, 72)
DAGNA_TEAL = (67, 139, 132)


GARRAN_ACTION_CARDS = (
    _card(
        "accept",
        "AKCEPTUJ",
        "universal",
        1,
        "REAKCJA STOŁU",
        "Potwierdź widoczny wybór. System ponownie sprawdzi cel, koszt i warunki akcji.",
        "„Skoro decyzja zapadła, nie traćmy światła dnia.”",
        "garran_tactics_plate.png",
        (74, 153, 123),
    ),
    _card(
        "decline",
        "ODRZUĆ",
        "universal",
        1,
        "REAKCJA STOŁU",
        "Anuluj bieżący wybór lub wróć. Karta nie cofa akcji, która została już rozstrzygnięta.",
        "„Zły rozkaz odrzuć, zanim zapłacą za niego inni.”",
        "garran_tactics_plate.png",
        (166, 78, 72),
    ),
    _card(
        "maneuvers",
        "MANEWRY",
        "universal",
        1,
        "MENU AKCJI",
        "Otwórz dostępne manewry, m.in. Sprint, Unik, Odstąpienie, Pomoc, Ukrycie, Szukanie, Grapple i Shove.",
        "„Najpierw pozycja. Potem siła.”",
        "garran_tactics_plate.png",
        GARRAN_BLUE,
    ),
    _card(
        "equipment",
        "EKWIPUNEK",
        "universal",
        1,
        "MENU WŁASNE",
        "Otwórz ekwipunek. Możesz dobyć, schować, zamienić lub upuścić broń oraz użyć dostępnego przedmiotu.",
        "„Sprawdź pasy, cięciwę i drogę odwrotu.”",
        "garran_tactics_plate.png",
        (155, 119, 75),
    ),
    _card(
        "second_wind",
        "DRUGI ODDECH",
        "feature",
        1,
        "AKCJA DODATKOWA",
        "Odzyskaj 1k10 + poziom wojownika PW. Jedno użycie; odnawia się po krótkim lub długim odpoczynku.",
        "„Jeszcze stoję. To na razie wystarczy.”",
        "garran_tactics_plate.png",
        (111, 163, 176),
    ),
    _card(
        "action_surge",
        "ZRYW AKCJI",
        "feature",
        2,
        "W SWOJEJ TURZE",
        "Natychmiast zyskujesz jedną dodatkową akcję w tej turze. Jedno użycie; odnawia się po krótkim lub długim odpoczynku.",
        "„Jedna chwila przewagi potrafi uratować cały oddział.”",
        "garran_battle_plate.png",
        (193, 111, 57),
    ),
)


DAGNA_ACTION_CARDS = (
    _card("accept", "AKCEPTUJ", "universal", 1, "REAKCJA STOŁU", "Potwierdź widoczny wybór. System ponownie sprawdzi cel, koszt i warunki akcji.", "„Jeśli to komuś pomoże — działajmy.”", "dagna_mercy_plate.png", (70, 157, 122)),
    _card("decline", "ODRZUĆ", "universal", 1, "REAKCJA STOŁU", "Anuluj bieżący wybór lub wróć. Karta nie cofa akcji, która została już rozstrzygnięta.", "„Nie każda ofiara jest konieczna.”", "dagna_mercy_plate.png", (166, 78, 72)),
    _card("maneuvers", "MANEWRY", "universal", 1, "MENU AKCJI", "Otwórz dostępne manewry, m.in. Sprint, Unik, Odstąpienie, Pomoc, Ukrycie, Szukanie, Grapple i Shove.", "„Czasem najlepszym cudem jest zrobić komuś miejsce.”", "dagna_mercy_plate.png", DAGNA_TEAL),
    _card("equipment", "EKWIPUNEK", "universal", 1, "MENU WŁASNE", "Otwórz ekwipunek. Możesz zmienić broń, tarczę lub użyć dostępnego przedmiotu i zapasów.", "„Bandaże, woda, światło. Dopiero potem relikwie.”", "dagna_mercy_plate.png", (163, 117, 66)),
    _card("sacred_flame", "ŚWIĘTY PŁOMIEŃ", "spell", 1, "AKCJA · 60 STÓP", "Cel wykonuje rzut obronny na Zręczność. Porażka: 1k8 obrażeń promienistych; sukces: bez obrażeń. Osłona nie daje premii do tego rzutu.", "„Światło znajduje drogę nawet przez dym pobojowiska.”", "dagna_miracles_plate.png", (239, 192, 78)),
    _card("guidance", "WSKAZÓWKI", "spell", 1, "AKCJA · DOTYK · KONC.", "Przez minutę cel może dodać 1k4 do jednego wybranego testu cechy. Potem czar się kończy.", "„Nie dam ci pewności. Dam ci spokojniejszą dłoń.”", "dagna_mercy_plate.png", (103, 177, 161)),
    _card("spare_the_dying", "OSZCZĘDŹ UMIERAJĄCEGO", "spell", 1, "AKCJA · DOTYK", "Stabilizujesz żywą istotę mającą 0 PW. Czar nie działa na nieumarłych ani konstrukty.", "„Jeszcze nie. Jeszcze możesz wrócić.”", "dagna_mercy_plate.png", (230, 204, 151)),
    _card("bane", "ZGUBA", "spell", 1, "AKCJA · 30 STÓP · KONC.", "Do 3 celów: rzut obronny na Charyzmę. Porażka: odejmują 1k4 od każdego rzutu ataku i rzutu obronnego przez 1 minutę.", "„Niech ciężar cudzych krzywd zadrży w waszych rękach.”", "dagna_miracles_plate.png", (151, 91, 135)),
    _card("bless", "BŁOGOSŁAWIEŃSTWO", "spell", 1, "AKCJA · 30 STÓP · KONC.", "Do 3 istot dodaje 1k4 do każdego rzutu ataku i rzutu obronnego przez 1 minutę. Wyższy slot: +1 cel za poziom.", "„Nie walczycie sami, nawet jeśli historia o was zapomni.”", "dagna_mercy_plate.png", DAGNA_GOLD),
    _card("command", "ROZKAZ", "spell", 1, "AKCJA · 60 STÓP", "Cel: rzut obronny na Mądrość. Porażka: w następnej turze wykonuje jednowyrazowy rozkaz, jeśli go rozumie i rozkaz nie krzywdzi go wprost.", "„Stać. Dosyć już ludzi pchanych pod ostrza.”", "dagna_miracles_plate.png", (207, 145, 68)),
    _card("create_or_destroy_water", "STWÓRZ / ZNISZCZ WODĘ", "spell", 1, "AKCJA · 30 STÓP", "Stwórz do 10 galonów czystej wody albo zniszcz tyle samo w otwartym pojemniku; możesz też wywołać lub usunąć deszcz w sześcianie 30 stóp.", "„Dla oblężonych kubek wody bywa większym cudem niż miecz.”", "dagna_mercy_plate.png", (73, 144, 174)),
    _card("cure_wounds", "LECZENIE RAN", "spell", 1, "AKCJA · DOTYK", "Żywa istota odzyskuje 1k8 + twój modyfikator z Mądrości PW. Wyższy slot: +1k8 za poziom.", "„Zszywam to, co wojna próbuje rozerwać.”", "dagna_mercy_plate.png", (102, 178, 130)),
    _card("detect_evil_and_good", "WYKRYCIE DOBRA I ZŁA", "spell", 1, "AKCJA · WŁASNY · KONC.", "Przez 10 minut wyczuwasz w 30 stopach określone istoty nadnaturalne oraz miejsca poświęcone lub zbezczeszczone.", "„Nie wszystko, co nosi ludzką twarz, należy do tego świata.”", "dagna_miracles_plate.png", (184, 141, 194)),
    _card("detect_magic", "WYKRYCIE MAGII", "spell", 1, "AKCJA · WŁASNY · RYTUAŁ", "Przez 10 minut wyczuwasz magię w 30 stopach; akcją widzisz aurę widocznego źródła i poznajesz szkołę. Wymaga koncentracji.", "„Pęknięcia rzeczywistości zostawiają blask jak gorączka.”", "dagna_miracles_plate.png", (113, 126, 207)),
    _card("detect_poison_and_disease", "WYKRYCIE TRUCIZNY I CHOROBY", "spell", 1, "AKCJA · WŁASNY · RYTUAŁ", "Przez 10 minut wyczuwasz w 30 stopach trucizny, jadowite istoty i choroby oraz rozpoznajesz ich rodzaj. Wymaga koncentracji.", "„Najgroźniejszy wróg często nie nosi barw żadnej armii.”", "dagna_miracles_plate.png", (111, 158, 91)),
    _card("guiding_bolt", "POCISK PRZEWODNI", "spell", 1, "AKCJA · 120 STÓP", "Wykonaj dystansowy rzut ataku czarem. Trafienie: 4k6 obrażeń promienistych; następny rzut ataku przeciw celowi przed końcem twojej następnej tury ma przewagę.", "„Zostawiam światło tam, gdzie inni mają uderzyć.”", "dagna_miracles_plate.png", (242, 190, 73)),
    _card("healing_word", "SŁOWO LECZENIA", "spell", 1, "AKCJA DOD. · 60 STÓP", "Żywa istota odzyskuje 1k4 + twój modyfikator z Mądrości PW. Wyższy slot: +1k4 za poziom.", "„Słyszysz mnie? To wracaj. Resztę zrobimy później.”", "dagna_mercy_plate.png", (94, 181, 146)),
    _card("inflict_wounds", "ZADAWANIE RAN", "spell", 1, "AKCJA · DOTYK", "Wykonaj rzut ataku czarem w zwarciu. Trafienie: 3k10 obrażeń nekrotycznych. Wyższy slot: +1k10 za poziom.", "„Ta sama dłoń, która leczy, wie też gdzie boli najbardziej.”", "dagna_miracles_plate.png", (145, 84, 119)),
    _card("protection_from_evil_and_good", "OCHRONA PRZED DOBREM I ZŁEM", "spell", 1, "AKCJA · DOTYK · KONC.", "Przez 1 godzinę wskazane typy istot mają utrudnienie w atakach przeciw celowi i nie mogą go opętać, zauroczyć ani przestraszyć.", "„Nie przekroczysz tej granicy, choćby świat pękł na pół.”", "dagna_miracles_plate.png", (204, 174, 107)),
    _card("purify_food_and_drink", "OCZYSZCZENIE JADŁA I NAPOJU", "spell", 1, "AKCJA · 10 STÓP · RYTUAŁ", "Niemagiczne jedzenie i napoje w promieniu 5 stóp od wybranego punktu stają się wolne od trucizn i chorób.", "„Czysta miska zupy też potrafi ocalić kompanię.”", "dagna_mercy_plate.png", (102, 157, 124)),
    _card("sanctuary", "SANKTUARIUM", "spell", 1, "AKCJA DOD. · 30 STÓP", "Przez 1 minutę napastnik musi zdać rzut obronny na Mądrość albo wybrać inny cel lub stracić atak. Efekt kończy atak albo wrogi czar podopiecznego.", "„Za moimi plecami macie jedną chwilę ciszy.”", "dagna_mercy_plate.png", (225, 187, 111)),
    _card("shield_of_faith", "TARCZA WIARY", "spell", 1, "AKCJA DOD. · 60 STÓP · KONC.", "Wybrana istota otrzymuje +2 do KP przez maksymalnie 10 minut.", "„Nie zatrzymam wojny. Zatrzymam ten jeden cios.”", "dagna_mercy_plate.png", (205, 173, 75)),
    _card("turn_undead", "ODPĘDZENIE NIEUMARŁYCH", "feature", 2, "AKCJA · BOSKA MOC", "Nieumarli w 30 stopach, którzy cię widzą lub słyszą: rzut obronny na Mądrość. Porażka: uciekają przez 1 minutę lub do otrzymania obrażeń.", "„Zmarli mają dość własnych wojen. Odejdźcie.”", "dagna_miracles_plate.png", (231, 197, 124)),
    _card("preserve_life", "ZACHOWANIE ŻYCIA", "feature", 2, "AKCJA · BOSKA MOC", "Rozdziel 5 × poziom kleryka punktów leczenia między istoty w 30 stopach. Nie leczysz ponad połowę maksimum PW ani nieumarłych i konstruktów.", "„Najpierw ci, którzy nie przeżyją kolejnej minuty.”", "dagna_mercy_plate.png", (91, 184, 143)),
    _card("aid", "WSPARCIE", "spell", 3, "AKCJA · 30 STÓP", "Maksymalne i aktualne PW maksymalnie 3 istot rosną o 5 na 8 godzin. Wyższy slot zwiększa premię o kolejne 5.", "„Nie obiecuję bezpieczeństwa. Daję wam większą szansę.”", "dagna_mercy_plate.png", (110, 176, 134)),
    _card("augury", "WRÓŻBA", "spell", 3, "1 MIN · WŁASNY · RYTUAŁ", "Otrzymujesz omen dobra, zła, obu lub żadnego dla działania planowanego w ciągu 30 minut. Wymaga znaczonych kości lub żetonów wartych 25 gp.", "„Kości nie mówią, kto wygra wojnę. Mówią, czy wrócimy z drogi.”", "dagna_miracles_plate.png", (184, 139, 91)),
    _card("blindness_deafness", "ŚLEPOTA / GŁUCHOTA", "spell", 3, "AKCJA · 30 STÓP", "Cel: rzut obronny na Kondycję. Porażka: wybierasz oślepienie albo ogłuchnięcie na 1 minutę; cel ponawia rzut na końcu każdej swojej tury.", "„Odbieram ci tylko to, czym krzywdzisz innych.”", "dagna_miracles_plate.png", (137, 111, 151)),
    _card("calm_emotions", "USPOKOJENIE EMOCJI", "spell", 3, "AKCJA · 60 STÓP · KONC.", "Humanoidy w sferze o promieniu 20 stóp: rzut obronny na Charyzmę. Możesz stłumić zauroczenie/strach albo wrogość przez 1 minutę.", "„Gniew dowódców nie musi stać się grobem zwykłych ludzi.”", "dagna_mercy_plate.png", (105, 151, 170)),
    _card("continual_flame", "WIECZNY PŁOMIEŃ", "spell", 3, "AKCJA · DOTYK", "Dotknięty przedmiot emituje światło jak pochodnia, bez ciepła i spalania, aż do rozproszenia. Zużywa rubinowy pył wart 50 gp.", "„Niech to światło czeka na tych, którzy wrócą po zmroku.”", "dagna_miracles_plate.png", (240, 159, 59)),
    _card("enhance_ability", "WZMOCNIENIE CECHY", "spell", 3, "AKCJA · DOTYK · KONC.", "Na 1 godzinę wybierz cechę: cel ma przewagę w jej testach i otrzymuje przypisany dodatkowy efekt. Szczegół wybierzesz w menu.", "„Każdy ma w sobie więcej siły, niż zostawiła mu wojna.”", "dagna_mercy_plate.png", (137, 174, 92)),
    _card("find_traps", "WYKRYCIE PUŁAPEK", "spell", 3, "AKCJA · 120 STÓP", "Wyczuwasz obecność pułapek w zasięgu i linii widzenia oraz ogólny rodzaj zagrożenia. Nie poznajesz liczby ani dokładnego położenia pułapek.", "„Droga, która wygląda na pustą, zwykle pamięta czyjś pośpiech.”", "dagna_miracles_plate.png", (177, 126, 63)),
    _card("gentle_repose", "ŁAGODNY SPOCZYNEK", "spell", 3, "AKCJA · DOTYK · RYTUAŁ", "Ciało przez 10 dni nie rozkłada się i nie może stać się nieumarłym; ten czas nie liczy się do limitu magii wskrzeszającej.", "„Nie pozwolę, by nawet śmierć zrobiła z ciebie narzędzie.”", "dagna_mercy_plate.png", (166, 158, 146)),
    _card("hold_person", "UNIERUCHOMIENIE OSOBY", "spell", 3, "AKCJA · 60 STÓP · KONC.", "Humanoid: rzut obronny na Mądrość. Porażka: jest sparaliżowany do 1 minuty; ponawia rzut na końcu każdej swojej tury.", "„Zostań tam, zanim twoja wojna dosięgnie kolejnego domu.”", "dagna_miracles_plate.png", (171, 118, 168)),
    _card("lesser_restoration", "POMNIEJSZE PRZYWRÓCENIE", "spell", 3, "AKCJA · DOTYK", "Kończysz jedną chorobę albo jeden stan: oślepienie, ogłuchnięcie, paraliż lub zatrucie.", "„Ciało pamięta drogę do zdrowia. Trzeba mu ją pokazać.”", "dagna_mercy_plate.png", (86, 181, 151)),
    _card("locate_object", "ODNALEZIENIE PRZEDMIOTU", "spell", 3, "AKCJA · WŁASNY · KONC.", "Przez 10 minut znasz kierunek do znanego przedmiotu w 1000 stóp, jeśli jest w ruchu — także kierunek ruchu. Ołów blokuje czar.", "„W ruinach wszystko ginie. Nie wszystko musi pozostać zgubione.”", "dagna_miracles_plate.png", (185, 141, 74)),
    _card("prayer_of_healing", "MODLITWA LECZENIA", "spell", 3, "10 MIN · 30 STÓP", "Do 6 żywych istot odzyskuje po 2k8 + twój modyfikator z Mądrości PW. Wyższy slot: +1k8 za poziom.", "„Usiądźcie. Przez dziesięć minut świat poradzi sobie bez nas.”", "dagna_mercy_plate.png", (103, 188, 147)),
    _card("protection_from_poison", "OCHRONA PRZED TRUCIZNĄ", "spell", 3, "AKCJA · DOTYK", "Neutralizujesz jedną truciznę w celu. Przez 1 godzinę ma przewagę w rzutach obronnych przeciw truciźnie i odporność na obrażenia od trucizny.", "„Jad nie pyta o sztandar. Ja też nie pytam, zanim pomogę.”", "dagna_mercy_plate.png", (118, 166, 83)),
    _card("silence", "CISZA", "spell", 3, "AKCJA · 120 STÓP · RYTUAŁ", "W sferze 20 stóp przez 10 minut nie powstaje ani nie przechodzi dźwięk. Istoty są ogłuszone słuchowo, a komponenty werbalne nie działają. Koncentracja.", "„Czasem trzeba uciszyć świat, żeby usłyszeć rannych.”", "dagna_miracles_plate.png", (115, 129, 150)),
    _card("spiritual_weapon", "DUCHOWA BROŃ", "spell", 3, "AKCJA DOD. · 60 STÓP", "Tworzysz broń na 1 minutę. Wykonaj rzut ataku czarem w zwarciu; trafienie: 1k8 + modyfikator Mądrości obrażeń od mocy. Akcją dodatkową przesuń ją o 20 stóp i zaatakuj ponownie.", "„Mój młot może być daleko. Moja odpowiedzialność — nigdy.”", "dagna_miracles_plate.png", (225, 171, 66)),
    _card("warding_bond", "WIĘŹ OCHRONNA", "spell", 3, "AKCJA · DOTYK", "Przez 1 godzinę cel ma +1 do KP i rzutów obronnych oraz odporność na obrażenia; ty otrzymujesz tyle samo obrażeń. Koniec powyżej 60 stóp.", "„Jeśli masz nieść ten ból, poniesiemy go razem.”", "dagna_mercy_plate.png", (205, 157, 99)),
    _card("zone_of_truth", "STREFA PRAWDY", "spell", 3, "AKCJA · 60 STÓP", "Przez 10 minut istota w sferze 15 stóp wykonuje rzut obronny na Charyzmę. Porażka: nie może świadomie kłamać. Zna efekt; ty znasz wynik.", "„Prawda nie kończy wojny. Ale odbiera jej jedną kryjówkę.”", "dagna_miracles_plate.png", (231, 190, 91)),
)


GARRAN_DECK = CharacterDeckSpec(
    actor_id="garran",
    deck_title="GARRAN · ŻELAZNA LINIA",
    subtitle="Wojownik · człowiek · tarczownik i były dowódca",
    accent=GARRAN_BLUE,
    secondary=GARRAN_STEEL,
    back_asset="garran_battle_plate.png",
    action_cards=GARRAN_ACTION_CARDS,
    dossier_intro=(
        "Garran walczy z tarczą, bo zawsze wolał osłaniać innych niż szukać chwały. "
        "Instynktownie staje między zagrożeniem a słabszym, pilnuje odwrotu i ostatni "
        "opuszcza niebezpieczne miejsce. W młodości wierzył w dyscyplinę, honor i armię, "
        "która nadaje przemocy zasady. Był dobrym dowódcą: dbał o podwładnych i nie wymagał "
        "niczego, czego sam nie zrobiłby pierwszy. Wojna nauczyła go jednak, że każdą "
        "krzywdę można rozsądnie uzasadnić — transport żywności, ewakuację osady czy "
        "aresztowanie człowieka — i właśnie to okazało się najgorsze."
    ),
    dossier_campaign=(
        "Garran odmówił zatrzymania mieszkańców wpisanych na błędną listę podejrzanych. "
        "Kilka dni później dwóch wypuszczonych uczestniczyło w ataku, w którym zginęli jego "
        "dawni podwładni. Wykonując rozkaz, skrzywdziłby niewinnych; odmawiając, pozwolił "
        "winnym uderzyć ponownie. Do dziś nie wie, czy postąpił słusznie. Odszedł z armii i "
        "pracuje dla Gildii, wybierając małe, konkretne zadania bez wielkich słów. Nie jest "
        "pacyfistą, lecz nie ufa państwom, doktrynom ani prostym zwycięstwom. W drużynie nadal "
        "liczy zapasy, sprawdza odwrót i wydaje polecenia, choć boi się odpowiedzialności za "
        "cudze życie. Chce chronić innych bez oddawania sumienia dowódcy. Jego zasada: rozkaz "
        "może wyjaśnić czyn, ale nie odbiera odpowiedzialności za jego wykonanie."
    ),
    passives=(
        "Styl walki: Obrona — +1 do KP podczas noszenia pancerza.",
        "Wszechstronność człowieka i wojskowa ranga wspierają testy wynikające z pochodzenia.",
        "Poziom 3, Czempion: trafienie krytyczne przy naturalnym 19–20.",
    ),
    progression=(
        "Poziom 1: Drugi oddech.",
        "Poziom 2: Zryw akcji.",
        "Poziom 3: archetyp Czempiona i Ulepszone trafienie krytyczne (pasywne).",
    ),
)


DAGNA_DECK = CharacterDeckSpec(
    actor_id="dagna",
    deck_title="DAGNA · ŚWIATŁO PRZYDROŻY",
    subtitle="Kleryczka Życia · krasnoludzica · uzdrowicielka polowa",
    accent=DAGNA_GOLD,
    secondary=DAGNA_TEAL,
    back_asset="dagna_mercy_plate.png",
    action_cards=DAGNA_ACTION_CARDS,
    dossier_intro=(
        "Dagna zachowuje zimną krew pośród krzyków, chaosu i krwi. Szybko ocenia "
        "obrażenia i bez wahania pomaga, choć szczerze nie lubi swojej pracy ani "
        "pacjentów wracających z ranami po kolejnej głupiej decyzji. Została kapłanką, "
        "gdy rodzina oddała ją pod opiekę świątyni jako spłatę długu. Była zbyt młoda "
        "i obowiązkowa, by zaprotestować. Kiedy ujawniła magię leczniczą, każdy uratowany "
        "człowiek stawał się dla otoczenia dowodem boskiego przeznaczenia. Dagna nigdy "
        "nie była pewna, czy dar jest błogosławieństwem, czy obowiązkiem nazwanym przez innych."
    ),
    dossier_campaign=(
        "Przez lata odkładała odejście na później: po nauce, po służbie, po spłaceniu "
        "długu i po zakończeniu wojny. Sytuacja nigdy się nie uspokoiła. Leczenie jest "
        "jedyną rzeczą, którą naprawdę potrafi, ale nie chce poświęcić mu całego życia. "
        "Nie umie odmówić, jeśli jej pomoc może kogoś uratować, więc tłumi własne potrzeby, "
        "a później złości się o poświęcenia, których sama nie przerwała. Wierzy w boga, "
        "lecz podejrzewa, że to ludzie — nie on — odebrali jej wybór. Rusza w drogę, aby "
        "odkryć, kim jest poza rolą uzdrowicielki, i znaleźć coś wybranego wyłącznie dla "
        "siebie. Jej zasada brzmi: talent nie oznacza obowiązku oddania mu całego życia."
    ),
    passives=(
        "Domena Życia: ciężki pancerz i zawsze przygotowane czary domenowe.",
        "Uczeń Życia: czary leczenia 1. poziomu lub wyższe przywracają dodatkowe 2 + poziom czaru PW.",
        "Krasnoludzka odporność: przewaga przeciw truciznom i odporność na obrażenia od trucizny.",
        "Mroczne widzenie, kamieniarska wiedza i krasnoludzka wytrzymałość.",
        "Schronienie Wiernych: wsparcie świątyń i wspólnot własnej wiary.",
    ),
    progression=(
        "Poziom 1: sztuczki, czary 1. poziomu, Domena Życia.",
        "Poziom 2: Boska Moc — Odpędzenie Nieumarłych albo Zachowanie Życia.",
        "Poziom 3: czary 2. poziomu; zawsze przygotowane Pomniejsze Przywrócenie i Duchowa Broń.",
    ),
)


CLASS_DECK_META: dict[str, dict[str, Any]] = {
    "brakka": {
        "title": "BRAKKA · NIEZŁOMNY SZLAK",
        "subtitle": "Barbarzyńczyni · półorczyca · najemniczka Gildii Poszukiwaczy Przygód",
        "accent": (198, 77, 54),
        "secondary": (224, 157, 76),
        "intro": (
            "Brakka przeżyła więcej wojen, oblężeń i źle opłaconych kontraktów, niż "
            "chciałaby pamiętać. Ryzykowała życiem dla ludzi, którzy później odmawiali "
            "jej ręki albo próbowali obniżyć zapłatę. Nauczyła się, że wszystko ma cenę: "
            "jedzenie, bezpieczeństwo, lojalność i cudza pomoc. Nie jest okrutna. Głodnemu "
            "da miskę zupy, ale pozwoli mu uczciwie odpracować ją przy drewnie, płocie lub stajni. "
            "Jej dobroć jest szorstka i praktyczna: zamiast pocieszać rannych, niesie ich do uzdrowiciela."
            " Jej zasada brzmi: nie masz pieniędzy — możesz odpracować; nie możesz pracować — wtedy porozmawiamy."
        ),
        "campaign": (
            "Jako najemniczka Gildii Poszukiwaczy Przygód skrupulatnie odkłada każdą monetę. "
            "Nie marzy o sławie, lecz o własnym zajeździe: solidnym dachu, pełnej spiżarni i "
            "drzwiach, do których tylko ona ma klucz. Twierdzi, że chce tylko zarobić i odejść "
            "na odpoczynek, ale ciągle bierze na siebie więcej, niż powinna. Najtrudniej przychodzi "
            "jej przyjmowanie pomocy — każdą przysługę rozlicza jak dług o nieznanej cenie. "
            "Obawia się, że nawet po osiągnięciu celu nie będzie już umiała żyć bez zagrożenia."
        ),
        "passives": (
            "Obrona bez pancerza: KP 10 + Zręczność + Kondycja; tarcza jest dozwolona.",
            "Nieustępliwość półorka pozwala raz uniknąć zejścia do 0 PW; Dzikie ataki wzmacniają trafienie krytyczne.",
            "Poziom 2: Czujność na niebezpieczeństwo daje przewagę w widzianych rzutach obronnych na Zręczność.",
        ),
        "progression": (
            "Poziom 1: Szał i Obrona bez pancerza.",
            "Poziom 2: Lekkomyślny atak i Czujność na niebezpieczeństwo.",
            "Poziom 3: Ścieżka Berserkera i Szał bojowy.",
        ),
    },
    "lorian": {
        "title": "LORIAN · PIEŚŃ OTWARTYCH DRZWI",
        "subtitle": "Bard · półelf · gawędziarz i paktujący artysta",
        "accent": (187, 86, 181),
        "secondary": (91, 176, 205),
        "intro": (
            "Lorian jest kolorową plamą w świecie szarzejącym od wojny. Ubiera się zbyt "
            "elegancko, zna pieśń na każdą okazję i odmawia pozwolenia, by strach był jedynym "
            "tematem rozmów. Nie zawsze miał taki talent. Podczas oblężenia był cichym, "
            "przeciętnym muzykiem grającym dla rannych, uchodźców i żołnierzy. Powiedział, "
            "że oddałby wszystko, byle do nich dotrzeć. Gość Ostatniego Rzędu odpowiedział: "
            "dał mu głos, charyzmę i magię wzbudzającą śmiech, odwagę, zachwyt albo łzy. "
            "W zamian Lorian dostarcza mu emocji wywoływanych w innych."
        ),
        "campaign": (
            "Gość nie żywi się krwią ani duszami, lecz uwagą. Obojętność jest jedyną rzeczą, "
            "której pakt nie toleruje. Lorian wypełnia więc każdą ciszę, żartuje w złych chwilach "
            "i czasem wybiera oburzenie, jeśli nie potrafi zdobyć sympatii. Jego optymizm pozostaje "
            "szczery: chce ocalić miejsce na śmiech, piękno i nadzieję. Drużyna jest pierwszą "
            "publicznością, która widziała go zmęczonego, rannego i bez następnego zdania. Nie wie, "
            "czy ceni jego, czy dar paktu, dlatego stale zasługuje na jej przywiązanie. Chce poznać "
            "naturę Gościa i stworzyć pieśń poruszającą bez magii. Boi się, że bez występu nie ma "
            "w nim nic wartego zatrzymania. Jego zasada: rozpacz nie mądrzeje od poważnego tonu."
        ),
        "passives": (
            "Wszechstronność: od poziomu 2 dodajesz połowę premii z biegłości do testów bez biegłości.",
            "Pieśń odpoczynku: podczas krótkiego odpoczynku sojusznicy odzyskują dodatkowe PW.",
            "Kolegium Wiedzy: na poziomie 3 zyskujesz trzy dodatkowe biegłości.",
        ),
        "progression": (
            "Poziom 1: Inspiracja bardowska, sztuczki i czary 1. poziomu.",
            "Poziom 2: Wszechstronność i Pieśń odpoczynku.",
            "Poziom 3: Kolegium Wiedzy, Cięta riposta i czary 2. poziomu.",
        ),
    },
    "sylwen": {
        "title": "SYLWEN · MAPA ŻYWYCH ŚCIEŻEK",
        "subtitle": "Druidka Kręgu Ziemi · elfka · kartografka",
        "accent": (83, 151, 92),
        "secondary": (191, 149, 68),
        "intro": (
            "Sylwen zarabiała na wyznaczaniu dróg przez lasy, których mapy starzały się szybciej "
            "niż atrament. Gdy armie zaczęły maszerować na przełaj, jej wiedza stała się cenna "
            "dla kupców, uchodźców, zwiadowców i każdego, kto wolał nie spotkać patrolu."
        ),
        "campaign": (
            "Wyprawy pozwalają jej uzupełniać atlas bezpiecznych szlaków i negocjować ochronę "
            "miejsc, których żadna korona nie uważa za ważne. Marzy o gospodzie pośrodku dziczy, "
            "gdzie za opowieść o drodze płaci się kolejną opowieścią."
        ),
        "passives": (
            "Znasz język druidów i możesz zostawiać ukryte wiadomości.",
            "Krąg Ziemi daje dodatkową sztuczkę i czary zależne od wybranego terenu.",
            "Naturalne odzyskiwanie: raz dziennie po krótkim odpoczynku odzyskujesz część komórek.",
        ),
        "progression": (
            "Poziom 1: sztuczki i przygotowywane czary 1. poziomu.",
            "Poziom 2: Dziki kształt, Krąg Ziemi i Naturalne odzyskiwanie.",
            "Poziom 3: czary 2. poziomu oraz czary wybranego kręgu.",
        ),
    },
    "pim": {
        "title": "PIM · DROGA PONAD MURAMI",
        "subtitle": "Mnich Otwartej Dłoni · niziołek · posłaniec",
        "accent": (219, 132, 52),
        "secondary": (75, 157, 181),
        "intro": (
            "Pim był najszybszym posłańcem w dzielnicy i jedynym, który uważał dachy za normalną "
            "część ulicy. Wędrowny mistrz nauczył go, jak zmienić pośpiech w dyscyplinę, a "
            "dyscyplinę — w serię bardzo celnych kopnięć."
        ),
        "campaign": (
            "Podejmuje wyprawy, bo każda nowa ruina jest torem przeszkód, a każda nagroda "
            "przybliża go do otwarcia własnej szkoły dla ulicznych dzieciaków. Przy okazji "
            "zbiera historie o mistrzu, który nigdy nie pożegnał się porządnie."
        ),
        "passives": (
            "Obrona bez pancerza: bez pancerza i tarczy KP 10 + Zręczność + Mądrość.",
            "Sztuki walki: broń mnicha może używać Zręczności i co najmniej k4 obrażeń.",
            "Poziom 2: szybkość rośnie o 10 stóp bez pancerza i tarczy.",
        ),
        "progression": (
            "Poziom 1: Sztuki walki i dodatkowy cios bez broni.",
            "Poziom 2: Ki, Nawałnica ciosów, Cierpliwa obrona i Krok wiatru.",
            "Poziom 3: Odbijanie pocisków i Technika Otwartej Dłoni.",
        ),
    },
    "rhogar": {
        "title": "RHOGAR · PRZYSIĘGA BEZ HERBU",
        "subtitle": "Paladyn Oddania · smoczy potomek · wolny obrońca",
        "accent": (199, 75, 52),
        "secondary": (230, 184, 81),
        "intro": (
            "Rhogar wychował się przy stołach negocjacyjnych rodu handlarzy. Zamiast przejąć "
            "rodzinny interes, odciął herb z tabardu i zaczął eskortować tych, których nie stać "
            "na prywatną armię. Ku własnemu zaskoczeniu okazał się w tym naprawdę dobry."
        ),
        "campaign": (
            "Chce zbudować nazwisko warte więcej niż odziedziczony tytuł. Kontrakty dają mu "
            "pieniądze, świadków i okazję, by sprawdzić, czy zasady działają również wtedy, gdy "
            "nikt ważny nie patrzy."
        ),
        "passives": (
            "Smocze pochodzenie daje odporność na ogień.",
            "Poziom 2: wybrany styl walki działa automatycznie, gdy spełniasz jego warunki.",
            "Poziom 3: Boskie zdrowie daje odporność na choroby; przysięga stale przygotowuje czary domenowe.",
        ),
        "progression": (
            "Poziom 1: Boski zmysł i Nakładanie rąk.",
            "Poziom 2: styl walki, czary 1. poziomu i Boskie porażenie.",
            "Poziom 3: Przysięga Oddania i dwa warianty Boskiego Kanału.",
        ),
    },
    "erynd": {
        "title": "ERYND · OSTATNI BEZPIECZNY SZLAK",
        "subtitle": "Łowca Myśliwy · elf · tropiciel i survivalista",
        "accent": (78, 132, 98),
        "secondary": (184, 133, 66),
        "intro": (
            "Erynd potrafi przeżyć niemal wszędzie. Znajduje wodę, rozpala ogień bez dymu, "
            "buduje ukryte schronienia i rozpoznaje ślady istot, których lepiej nie spotkać. "
            "Nosi zapasową cięciwę, hubkę, sól, drut, lekarstwa i jedzenie na dzień dłużej, "
            "niż przewiduje plan. Wychował się w leśnej osadzie łowców i przewodników. Gdy "
            "zwierzęta zaczęły odchodzić, ptaki milkły, a na szlakach pojawiły się obce ślady, "
            "ostrzegał mieszkańców przed magicznym przesileniem. Nikt nie potraktował go poważnie."
        ),
        "campaign": (
            "Nocą przez osadę przeszła fala wypaczenia: drzewa zmieniały miejsce, ścieżki prowadziły "
            "donikąd, a światło przyciągało istoty z ciemności. Erynd przeżył w przygotowanym "
            "schronieniu; wielu zaginęło, w tym jego ojciec. Pochwała, że miał rację, brzmi dla niego "
            "jak oskarżenie — skoro przewidział zagrożenie, powinien był zrobić więcej. Odtąd układa "
            "plany awaryjne i nie potrafi odpocząć, dopóki istnieje coś nieprzewidzianego. Drużynę "
            "chroni zapasami, ostrzeżeniami i drogami odwrotu, ale czasem sprawdza cudzy sprzęt, "
            "zabrania ryzyka lub ukrywa informacje. Chce odnaleźć ojca i stworzyć sieć bezpiecznych "
            "schronień. Boi się zarówno kolejnego zlekceważonego znaku, jak i życia zmarnowanego na "
            "katastrofę, która nie nadejdzie. Jego zasada: małe prawdopodobieństwo nie pomaga, kiedy "
            "zdarzenie już nastąpi."
        ),
        "passives": (
            "Ulubiony wróg daje przewagę przy tropieniu i przypominaniu wiedzy o wybranym typie.",
            "Naturalny odkrywca zapewnia korzyści podróżne w wybranym terenie.",
            "Poziom 3, Myśliwy: wybierasz Łowcę Kolosów, Zabójcę Olbrzymów albo Niszczyciela Hord.",
        ),
        "progression": (
            "Poziom 1: Ulubiony wróg i Naturalny odkrywca.",
            "Poziom 2: styl walki oraz dwa poznane czary 1. poziomu.",
            "Poziom 3: trzeci poznany czar, Pierwotna świadomość i archetyp Myśliwego.",
        ),
    },
    "mira": {
        "title": "MIRA · KLUCZ DO KAŻDYCH DRZWI",
        "subtitle": "Łotrzyca · niziołka · włamywaczka · była członkini Rodziny Jedwabnego Sznura",
        "accent": (126, 88, 169),
        "secondary": (67, 159, 161),
        "intro": (
            "Mira jest najmniejszą osobą w drużynie i zwykle pierwszą, którą się zauważa. "
            "Mówi szybko, głośno i bezczelnie; nie znosi protekcjonalnego tonu, rozkazów ani "
            "sugestii, że powinna znać swoje miejsce. Przez lata spłacała rodzinny dług w "
            "przestępczej Rodzinie Jedwabnego Sznura. Organizacja dopisywała do rachunku "
            "szkolenie, sprzęt, leczenie i każdy błąd, dlatego długu nie dało się spłacić. "
            "Mira została znakomitą włamywaczką, ale jej talent, komentarze i samowola czyniły "
            "z niej zarazem cenny nabytek i coraz bardziej kłopotliwą podwładną."
        ),
        "campaign": (
            "Kiedy zrozumiała, że obietnica wolności była smyczą, uciekła z łupem i fałszywymi "
            "dokumentami — bez starszego brata. Nie wie, czy został ukarany, nadal służy Rodzinie, "
            "czy sam jej szuka. Zbiera pieniądze i sojuszników, aby kiedyś po niego wrócić, lecz "
            "od kilku lat omija dawne miasto. Uwielbia być zauważana, choć jej życie zależy od "
            "tego, by niewłaściwi ludzie jej nie odnaleźli. Strach maskuje prowokacją i agresją, "
            "a każdą pomoc szybko spłaca. Wierzy, że dług, którego nie da się spłacić, nie jest "
            "długiem, tylko smyczą. Chce uwolnić brata i znów żyć pod własnym nazwiskiem."
        ),
        "passives": (
            "Ekspertyza podwaja premię z biegłości w Skradaniu i Percepcji.",
            "Podstępny atak: raz na turę +1k6, a od poziomu 3 +2k6, gdy spełniasz warunki.",
            "Złodziejka: Szybkie dłonie i Praca na wysokości rozszerzają użycie akcji dodatkowej i ruchu.",
        ),
        "progression": (
            "Poziom 1: Ekspertyza, Podstępny atak i Gwara złodziejska.",
            "Poziom 2: Przebiegła akcja.",
            "Poziom 3: archetyp Złodziejki i Podstępny atak 2k6.",
        ),
    },
    "veyra": {
        "title": "VEYRA · OGIEN POD KONTROLĄ",
        "subtitle": "Zaklinaczka Smoczej Krwi · diabelstwo · iluzjonistka",
        "accent": (191, 64, 84),
        "secondary": (113, 102, 203),
        "intro": (
            "Veyra przez lata zarabiała na iluzjach, zakładach i sprzedaży klientom dokładnie "
            "takiej wersji prawdy, jaką chcieli kupić. Gdy jej magia stała się potężniejsza, "
            "uznała, że uczciwiej będzie brać zapłatę za ratowanie ludzi z prawdziwych kłopotów."
        ),
        "campaign": (
            "Wyprawy są dla niej szkołą panowania nad mocą i rynkiem pełnym świetnie płatnych "
            "problemów. Zamierza stworzyć podręcznik bezpiecznej magii wrodzonej — albo przynajmniej "
            "listę rzeczy, których zdecydowanie nie należy robić w gospodzie."
        ),
        "passives": (
            "Smocza odporność zwiększa maksymalne PW i bazowe KP bez pancerza.",
            "Fontanna magii: od poziomu 2 punkty magii można wymieniać z komórkami czarów.",
            "Na poziomie 3 wybierasz dwa warianty Metamagii z ośmiu dostępnych.",
        ),
        "progression": (
            "Poziom 1: cztery sztuczki, dwa czary i Smocza odporność.",
            "Poziom 2: Fontanna magii i 2 punkty magii.",
            "Poziom 3: dwa wybory Metamagii, 3 punkty magii i czary 2. poziomu.",
        ),
    },
    "kael": {
        "title": "KAEL · UMOWA Z DOPISKAMI",
        "subtitle": "Czarnoksiężnik Czarta · półelf · badacz paktów",
        "accent": (142, 64, 173),
        "secondary": (212, 91, 55),
        "intro": (
            "Kael wszedł w posiadanie magicznej umowy i — jak każdy rozsądny badacz — przeczytał "
            "ją dopiero po podpisaniu. Od tamtej pory kataloguje przysługi patrona, ukryte koszty "
            "oraz wszystkie precedensy sugerujące możliwość renegocjacji."
        ),
        "campaign": (
            "Ruiny i anomalie są pełne prawników, kapłanów oraz istot starszych od prawa, więc "
            "wyprawy idealnie służą jego badaniom. Kael chce zostać pierwszym człowiekiem, który "
            "wypowie piekielny pakt zgodnie z jego własnym regulaminem."
        ),
        "passives": (
            "Magia paktu używa nielicznych komórek odnawianych po krótkim lub długim odpoczynku.",
            "Błogosławieństwo Mrocznego daje tymczasowe PW po pokonaniu wrogiej istoty.",
            "Na poziomie 2 wybierasz dwie inwokacje; na poziomie 3 jeden Dar Paktu.",
        ),
        "progression": (
            "Poziom 1: dwie sztuczki, dwa czary, patron Czart i Magia paktu.",
            "Poziom 2: dwie Inwokacje i druga komórka paktu.",
            "Poziom 3: czary 2. poziomu oraz Dar Łańcucha, Ostrza albo Księgi.",
        ),
    },
    "nimra": {
        "title": "NIMRA · KATALOG NIEMOŻLIWEGO",
        "subtitle": "Czarodziejka Ewokacji · gnomka · badaczka teorii magii",
        "accent": (74, 127, 205),
        "secondary": (188, 103, 198),
        "intro": (
            "Nimra potrafi patrzeć na innych z góry nawet wtedy, gdy musi zadzierać głowę. "
            "Mówi precyzyjnie, poprawia cudze błędy bez pytania i zakłada, że sprzeciw wynika "
            "z braku odpowiednich lektur. Jest błyskotliwa, perfekcyjna i nieznośnie pewna "
            "własnego rozumu. Pracowała w instytucie teorii magii, gdzie wolała opóźnić badania, "
            "niż zaakceptować wynik jedynie wystarczająco dobry. Podczas eksperymentu z "
            "niestabilnym źródłem mocy zignorowała ostrzeżenia. Laboratorium zostało zniszczone, "
            "kilku badaczy rannych, a jej najbliższy współpracownik zaginął wewnątrz anomalii."
        ),
        "campaign": (
            "Nimra nie wie, czy współpracownik zginął. Zamiast uznać, że czegoś nie rozumiała, "
            "uznała, że potrzebuje większej wiedzy. Obsesyjnie szuka zaklęć, artefaktów i teorii, "
            "wierząc, że potęga pozwoli jej przewidywać konsekwencje i naprawić własny błąd. "
            "Nie dopuszcza myśli, że większa moc może tylko zwiększyć skalę kolejnej pomyłki. "
            "Drużynę nazywa praktyczną ochroną badań, choć daje jej ona także poczucie przynależności. "
            "Troskę okazuje, przygotowując zaklęcia ochronne i zapamiętując słabości towarzyszy. "
            "Chce zrozumieć przesilenie i los zaginionego, lecz boi się dowodu, że katastrofę "
            "spowodowała pycha, nie brak informacji. Jej zasada: niemożliwe jest tylko to, co "
            "niewystarczająco opisane."
        ),
        "passives": (
            "Księga czarów zawiera więcej czarów, niż możesz jednocześnie przygotować.",
            "Znawca Ewokacji zmniejsza koszt przepisywania czarów tej szkoły.",
            "Rzeźbienie czarów chroni wybranych sojuszników przed twoimi ewokacjami obszarowymi.",
        ),
        "progression": (
            "Poziom 1: trzy sztuczki, księga z sześcioma czarami i Odzyskiwanie magiczne.",
            "Poziom 2: Szkoła Ewokacji, Znawca Ewokacji i Rzeźbienie czarów.",
            "Poziom 3: czary 2. poziomu i dwa kolejne czary w księdze.",
        ),
    },
}


FEATURE_CARDS: dict[str, tuple[tuple[str, str, int, str, str, str], ...]] = {
    "brakka": (
        ("rage", "SZAŁ", 1, "AKCJA DODATKOWA · PRZEŁĄCZNIK", "Gdy nieaktywny: zużyj 1 użycie i włącz Szał na maks. 10 rund. Otrzymujesz przewagę w testach i obronach Siły, +2 do obrażeń siłowych ataków wręcz oraz odporność na obrażenia kłute, cięte i obuchowe. Zeskanuj ponownie, aby zakończyć bez kolejnego kosztu.", "„Najpierw ostrzegam. Potem robi się głośno.”"),
        ("reckless_attack", "LEKKOMYŚLNY ATAK", 2, "PRZED 1. ATAKIEM", "Pierwszy atak wręcz oparty na Sile w tej turze ma przewagę. Do początku twojej następnej tury rzuty ataku przeciw tobie także mają przewagę.", "„Jeżeli odsłaniam gardę, to tylko po to, by dosięgnąć pierwsza.”"),
        ("frenzy", "SZAŁ BOJOWY", 3, "WYMAGA AKTYWNEGO SZAŁU", "Włącz podczas trwającego Szału. Od następnej swojej tury ponowny skan wydaje akcję dodatkową i daje 1 atak trzymaną bronią wręcz. Efekt kończy się ze Szałem: otrzymujesz 1 poziom Wyczerpania (poziom 1 daje utrudnienie w testach cech). Długi odpoczynek usuwa 1 poziom.", "„Dzisiaj odpoczynek poczeka.”"),
    ),
    "lorian": (
        ("bardic_inspiration", "INSPIRACJA BARDOWSKA", 1, "AKCJA DOD. · 60 STÓP", "Wybierz słyszącego cię sojusznika. Otrzymuje k6 do dodania w ciągu 10 minut do jednego testu cechy, rzutu ataku lub rzutu obronnego. Zużywa 1 użycie.", "„Refren jest prosty: jeszcze nie przegraliśmy.”"),
        ("cutting_words", "CIĘTA RIPOSTA", 3, "REAKCJA · 60 STÓP", "Gdy widoczny przeciwnik rzuca na atak, test cechy lub obrażenia, zużyj Inspirację i odejmij 1k6 od rzutu. Cel musi cię słyszeć i nie może być odporny na zauroczenie.", "„Nie każdy cios trzeba zatrzymać tarczą.”"),
    ),
    "sylwen": (
        ("wild_shape", "DZIKI KSZTAŁT", 2, "AKCJA · PRZEŁĄCZNIK", "Zużyj 1 z 2 użyć i wybierz Niedźwiedzia brunatnego (tank), Wilka (skradanie i współpraca) albo Wielkiego orła (mobilny atak; lot ignoruje trudny teren). Zeskanuj ponownie, aby wrócić do własnej postaci bez kolejnego kosztu.", "„Mapa wygląda inaczej, kiedy czyta się ją z wysokości trawy.”"),
        ("natural_recovery", "NATURALNE ODZYSKIWANIE", 2, "KRÓTKI ODPOCZYNEK", "Raz na długi odpoczynek odzyskaj zużyte komórki o łącznym poziomie nie większym niż połowa poziomu druida zaokrąglona w górę; żadna nie może być 6. poziomu lub wyższa.", "„Ziemia oddaje siłę temu, kto umie na chwilę przestać mówić.”"),
    ),
    "pim": (
        ("martial_arts_strike", "CIOS SZTUK WALKI", 1, "AKCJA DODATKOWA", "Po akcji Ataku nieuzbrojonym ciosem lub bronią mnicha wykonaj jeden nieuzbrojony cios. Musisz być bez pancerza i tarczy.", "„Jeden cios otwiera drogę drugiemu.”"),
        ("flurry_of_blows", "NAWAŁNICA CIOSÓW", 2, "AKCJA DOD. · 1 KI", "Natychmiast po akcji Ataku wydaj 1 Ki i wykonaj dwa nieuzbrojone ciosy zamiast jednego ciosu Sztuk walki.", "„Dwa kroki, dwa uderzenia, ani chwili na odpowiedź.”"),
        ("patient_defense", "CIERPLIWA OBRONA", 2, "AKCJA DOD. · 1 KI", "Wydaj 1 Ki, aby wykonać Unik jako akcję dodatkową. Do początku następnej tury widziane ataki przeciw tobie mają utrudnienie, a rzuty obronne na Zręczność — przewagę.", "„Nie każda przewaga wymaga ataku.”"),
        ("step_of_the_wind", "KROK WIATRU", 2, "AKCJA DOD. · 1 KI", "Wydaj 1 Ki, aby wykonać Sprint albo Odstąpienie jako akcję dodatkową; w tej turze podwajasz również dystans skoku.", "„Mur to tylko droga, która nie nauczyła się leżeć.”"),
        ("deflect_missiles", "ODBIJANIE POCISKÓW", 3, "REAKCJA", "Gdy trafia cię atak bronią dystansową, zmniejsz obrażenia o 1k10 + Zręczność + poziom mnicha. Jeśli spadną do 0, możesz wydać 1 Ki, by odrzucić pocisk jako atak.", "„Dziękuję. Oddaję.”"),
    ),
    "rhogar": (
        ("divine_sense", "BOSKI ZMYSŁ", 1, "AKCJA · 60 STÓP", "Do końca następnej tury poznajesz położenie nieosłoniętych całkowicie niebian, czartów i nieumarłych oraz poświęconych lub zbezczeszczonych miejsc. Zużywa 1 użycie.", "„Nie wszystko ukryje się za dobrym herbem.”"),
        ("lay_on_hands", "NAKŁADANIE RĄK", 1, "AKCJA · DOTYK", "Wydaj dowolną liczbę punktów z puli 5 × poziom paladyna, aby uleczyć tyle PW. Zamiast 5 punktów usuń jedną chorobę albo zneutralizuj jedną truciznę.", "„Przysięga zaczyna się od człowieka stojącego obok.”"),
        ("divine_smite", "BOSKIE PORAŻENIE", 2, "PO TRAFIENIU WRĘCZ", "Wydaj komórkę czaru: +2k8 obrażeń promienistych, +1k8 za każdy poziom komórki powyżej 1.; dodatkowo +1k8 przeciw czartom i nieumarłym. Maksymalnie 5k8.", "„Ten cios ma świadków.”"),
        ("channel_divinity_sacred_weapon", "ŚWIĘTA BROŃ", 3, "AKCJA · BOSKI KANAŁ", "Na 1 minutę dodajesz modyfikator Charyzmy (min. +1) do rzutów ataku wybraną trzymaną bronią; broń świeci. Kończy się po puszczeniu broni lub utracie przytomności.", "„Nie herb czyni broń godną.”"),
        ("channel_divinity_turn_the_unholy", "ODPĘDZENIE PLUGAWYCH", 3, "AKCJA · BOSKI KANAŁ", "Czarty i nieumarli w 30 stopach, którzy cię widzą lub słyszą, wykonują rzut obronny na Mądrość. Porażka: uciekają przez 1 minutę albo do otrzymania obrażeń.", "„Wracajcie tam, skąd przyszliście.”"),
    ),
    "erynd": (
        ("primeval_awareness", "PIERWOTNA ŚWIADOMOŚĆ", 3, "AKCJA · 1 KOMÓRKA", "Wydaj komórkę łowcy. Przez 1 minutę za poziom komórki wyczuwasz w promieniu 1 mili obecność wybranych typów istot; nie poznajesz liczby ani położenia.", "„Nie znam jeszcze drogi. Wiem tylko, kto po niej idzie.”"),
    ),
    "mira": (
        ("cunning_action", "PRZEBIEGŁA AKCJA", 2, "AKCJA DODATKOWA", "W każdej swojej turze możesz wykonać Sprint, Odstąpienie albo Ukrycie jako akcję dodatkową. Wybierz konkretną opcję po zagraniu karty.", "„Najlepsze wyjście to to, którego nikt nie pilnuje.”"),
    ),
    "veyra": (
        ("font_of_magic", "FONTANNA MAGII", 2, "AKCJA DODATKOWA", "Otwórz wymianę: zamień komórkę na punkty magii równe jej poziomowi albo wydaj punkty na komórkę. Koszt utworzenia komórki: 1./2./3. poziom = 2/3/5 punktów.", "„Moc jest walutą. Trzeba tylko znać kurs.”"),
        ("metamagic_careful", "OSTROŻNY CZAR", 3, "PRZY RZUCANIU · 1 PM", "Wybierz do modyfikatora Charyzmy istot w obszarze czaru wymagającego rzutu obronnego. Wybrane istoty automatycznie zdają pierwszy rzut obronny przeciw temu czarowi.", "„Ogień może znać nazwiska przyjaciół.”"),
        ("metamagic_distant", "ODLEGŁY CZAR", 3, "PRZY RZUCANIU · 1 PM", "Podwój zasięg czaru mającego co najmniej 5 stóp. Czar o zasięgu dotyku otrzymuje zasięg 30 stóp.", "„Bezpieczna odległość jest częścią planu.”"),
        ("metamagic_empowered", "WZMOCNIONY CZAR", 3, "PO RZUCIE OBRAŻEŃ · 1 PM", "Przerzuć do modyfikatora Charyzmy kości obrażeń czaru i użyj nowych wyników. Możesz połączyć ten wariant z inną Metamagią.", "„Jeszcze raz. Tym razem z przekonaniem.”"),
        ("metamagic_extended", "PRZEDŁUŻONY CZAR", 3, "PRZY RZUCANIU · 1 PM", "Podwój czas trwania czaru trwającego co najmniej 1 minutę, maksymalnie do 24 godzin.", "„Dobra magia powinna zostać na bis.”"),
        ("metamagic_heightened", "POTĘŻNY CZAR", 3, "PRZY RZUCANIU · 3 PM", "Jedna wybrana istota ma utrudnienie w pierwszym rzucie obronnym przeciw rzucanemu czarowi.", "„Tym razem los nie dostanie równego głosu.”"),
        ("metamagic_quickened", "PRZYSPIESZONY CZAR", 3, "PRZY RZUCANIU · 2 PM", "Zmień czas rzucania czaru z 1 akcji na 1 akcję dodatkową. W tej turze pozostałe czary mogą być tylko sztuczkami rzucanymi akcją.", "„Dlaczego czekać całą akcję?”"),
        ("metamagic_subtle", "SUBTELNY CZAR", 3, "PRZY RZUCANIU · 1 PM", "Rzuć czar bez komponentów werbalnych i somatycznych. Wymagane komponenty materialne nadal obowiązują.", "„Najlepsza sztuczka zaczyna się, zanim ktoś zauważy gest.”"),
        ("metamagic_twinned", "PODWOJONY CZAR", 3, "PRZY RZUCANIU · PM", "Czar celujący tylko w jedną istotę i niebędący czarem własnym obejmuje drugi legalny cel. Koszt: poziom czaru w PM, minimum 1 PM dla sztuczki.", "„Skoro działa raz, sprawdźmy próbę porównawczą.”"),
    ),
    "kael": (
        ("pact_of_the_blade", "BROŃ PAKTU", 3, "AKCJA · PRZEŁĄCZNIK", "Wybierz Rapier (1 ręka, finezyjny), Wielki miecz (2 ręce, 2k6) albo Glewię (2 ręce, zasięg 10 stóp). System sprawdza wolne ręce. Ponowny skan zmienia profil albo odwołuje magiczną broń.", "„Każda umowa potrzebuje narzędzia egzekucji.”"),
    ),
    "nimra": (
        ("arcane_recovery", "ODZYSKIWANIE MAGICZNE", 1, "KRÓTKI ODPOCZYNEK", "Raz na długi odpoczynek odzyskaj zużyte komórki o łącznym poziomie nie większym niż połowa poziomu czarodzieja zaokrąglona w górę; żadna nie może być 6. poziomu lub wyższa.", "„Porządek w notatkach oszczędza także energię magiczną.”"),
    ),
}


_DAMAGE_LABELS = {
    "acid": "od kwasu", "bludgeoning": "obuchowych", "cold": "od zimna",
    "fire": "od ognia", "force": "od mocy", "lightning": "od błyskawic",
    "necrotic": "nekrotycznych", "piercing": "kłutych", "poison": "od trucizny",
    "psychic": "psychicznych", "radiant": "promienistych", "slashing": "ciętych",
    "thunder": "od grzmotu",
}

_CONDITION_EFFECTS_PL = {
    "no_healing": "cel nie może odzyskiwać PW do początku twojej następnej tury",
    "no_reactions": "cel nie może wykonywać reakcji do początku swojej następnej tury",
    "ray_of_frost_slow": (
        "szybkość celu spada o 10 stóp do początku twojej następnej tury"
    ),
}


def _dice_pl(value: str) -> str:
    return value.replace("d", "k")


def _spell_timing(data: dict[str, Any]) -> str:
    casting = {
        "action": "AKCJA", "bonus_action": "AKCJA DOD.", "reaction": "REAKCJA",
        "minute": "1 MIN", "ten_minutes": "10 MIN", "hour": "1 GODZ.",
    }.get(str(data.get("casting_time")), str(data.get("casting_time", "AKCJA")).upper())
    range_data = data.get("range", {})
    range_kind = range_data.get("kind")
    if range_kind == "distance":
        range_text = f"{range_data.get('feet', 0)} STÓP"
    elif range_kind == "touch":
        range_text = "DOTYK"
    elif range_kind == "self":
        range_text = "WŁASNY"
    else:
        range_text = ""
    tags = [casting, range_text]
    if data.get("ritual"):
        tags.append("RYTUAŁ")
    if data.get("concentration"):
        tags.append("KONC.")
    return " · ".join(tag for tag in tags if tag)


_EXPLORATION_MECHANICS = {
    "comprehend_languages": "Przez 1 godzinę rozumiesz dosłowne znaczenie słyszanych języków i czytanego pisma; strona tekstu zajmuje około 1 minuty. Nie odszyfrowuje tajnych wiadomości.",
    "dancing_lights": "Tworzysz do 4 świateł w zasięgu. Akcją dodatkową przesuń je do 60 stóp; każde musi pozostawać w 20 stopach od innego. Koncentracja, maks. 1 minuta.",
    "druidcraft": "Wywołaj jeden drobny efekt natury: prognozę pogody, rozkwit rośliny, zmysłowy znak albo zapalenie lub zgaszenie małego płomienia.",
    "light": "Dotknięty przedmiot świeci jasno na 20 stóp i słabo przez kolejne 20 przez 1 godzinę. Wrogi trzymany przedmiot wymaga udanego rzutu obronnego na Zręczność.",
    "mage_hand": "Tworzysz widmową dłoń na 1 minutę. Akcją porusz nią do 30 stóp i manipuluj przedmiotem do 10 funtów; nie atakuje ani nie używa magicznych przedmiotów.",
    "mending": "W ciągu minuty naprawiasz pojedyncze pęknięcie lub rozdarcie do 1 stopy. Czar nie odtwarza utraconych właściwości magicznych.",
    "message": "Wskaż istotę w 120 stopach i wyszeptaj wiadomość słyszaną tylko przez nią; może odpowiedzieć szeptem. Czar omija narożniki, lecz blokują go grube bariery.",
    "minor_illusion": "Tworzysz na 1 minutę dźwięk albo nieruchomy obraz mieszczący się w sześcianie 5 stóp. Fizyczna interakcja ujawnia iluzję; badanie wymaga testu Śledztwa.",
    "prestidigitation": "Wywołaj drobny efekt magiczny: znak zmysłowy, zapalenie płomienia, oczyszczenie, smak, znamię albo mały niemagiczny drobiazg. Do 3 trwałych efektów naraz.",
    "thaumaturgy": "Na maks. 1 minutę wywołaj drobny cud: donośny głos, zmianę płomieni, drżenie ziemi, odległy dźwięk, ruch niezaryglowanych drzwi albo zmianę wyglądu oczu.",
}

_MECHANIC_OVERRIDES = {
    "sleep": (
        "Wskaż środek obszaru w 90 stopach i rzuć 5k8. Rozpatruj istoty w promieniu "
        "20 stóp od najniższych aktualnych PW: jeśli pula pokrywa całe PW celu, zasypia "
        "na 1 minutę. Obrażenia lub akcja sojusznika budzą; nie działa na nieumarłych "
        "ani istoty odporne na zauroczenie."
    ),
}


def _damage_text(damage: dict[str, Any]) -> str:
    dice = _dice_pl(str(damage.get("dice", "")))
    modifier = int(damage.get("modifier", 0))
    value = dice or str(damage.get("fixed", damage.get("value", 0)))
    if modifier:
        value += f" {'+' if modifier > 0 else '-'} {abs(modifier)}"
    return f"{value} obrażeń {_DAMAGE_LABELS.get(str(damage.get('damage_type')), str(damage.get('damage_type', '')))}"


def _normalize_instruction_pl(instructions: str) -> str:
    """Polonize recurring SRD shorthand without altering ordinary Polish words."""
    text = re.sub(r"(?<=\d)d(?=\d)", "k", instructions)
    replacements = (
        ("Ranged spell attack", "Wykonaj dystansowy rzut ataku czarem"),
        ("ranged spell attack", "dystansowy rzut ataku czarem"),
        ("Melee spell attack", "Wykonaj rzut ataku czarem w zwarciu"),
        ("melee spell attack", "rzut ataku czarem w zwarciu"),
        ("Charisma save", "rzut obronny na Charyzmę"),
        ("Wisdom save", "rzut obronny na Mądrość"),
        ("Wis save", "rzut obronny na Mądrość"),
        ("Dex save", "rzut obronny na Zręczność"),
        ("Con save", "rzut obronny na Kondycję"),
        ("Str save", "rzut obronny na Siłę"),
        ("bonus action", "akcję dodatkową"),
        ("Bonus action", "Akcja dodatkowa"),
        ("advantage", "przewagę"),
        ("disadvantage", "utrudnienie"),
        ("Dash", "Sprint"),
        ("Disengage", "Odstąpienie"),
        ("Dodge", "Unik"),
        ("Blinded", "Oślepiony"),
        ("Deafened", "Ogłuchnięty"),
        ("Paralyzed", "Sparaliżowany"),
        ("Restrained", "Unieruchomiony"),
        ("Incapacitated", "Obezwładniony"),
        ("Invisible", "Niewidzialny"),
        ("Prone", "Powalony"),
        ("darkvision", "widzenie w ciemności"),
        ("climb speed", "szybkość wspinania"),
        ("contest", "test przeciwstawny"),
        ("attunement", "dostrojenie"),
        ("Tiny beast", "malutkiej bestii"),
        ("Perception/Survival", "Percepcji/Sztuce przetrwania"),
        ("KP 10 + Dex", "KP 10 + modyfikator Zręczności"),
        ("bronią się Dex przed", "wykonują rzut obronny na Zręczność przeciw"),
        ("Investigation", "Śledztwo"),
        ("Poisoned", "Zatruty"),
        ("Ethereal Plane", "Plan Eteryczny"),
        ("statblock", "blok statystyk"),
        ("extradimensional space", "przestrzeni pozawymiarowej"),
        ("Medium istot", "istot Średniego rozmiaru"),
        ("celestial", "niebianie"),
        ("elemental", "żywiołaki"),
        ("fey", "fey"),
        ("fiend", "czarty"),
        ("undead", "nieumarli"),
        ("Int 4+", "Inteligencja 4+"),
        ("Wyższy slot zwiększa", "Komórka wyższego poziomu zwiększa"),
        ("Wyższy slot", "Komórka wyższego poziomu"),
        ("za wyższy slot", "za komórkę wyższego poziomu"),
        ("wyższy slot", "komórka wyższego poziomu"),
        ("poziom slotu", "poziom komórki"),
        (" slotu", " komórki"),
        (" slot", " komórkę"),
        (" fire", " obrażeń od ognia"),
        (" radiant", " obrażeń promienistych"),
        (" piercing", " obrażeń kłutych"),
        ("ponawia save", "ponawia rzut obronny"),
        ("przewagę save", "przewagę w rzutach obronnych"),
        ("przeciw poison", "przeciw truciźnie"),
        ("obrażenia poison", "obrażenia od trucizny"),
        (" i save", " i rzutów obronnych"),
        (
            "modyfikator cechy force",
            "modyfikator cechy czarowania obrażeń od mocy",
        ),
        (" force", " obrażeń od mocy"),
        (" ft", " stóp"),
    )
    for source, target in replacements:
        text = text.replace(source, target)
    return text


def _spell_mechanic(data: dict[str, Any]) -> str:
    spell_id = str(data["id"])
    if spell_id in _MECHANIC_OVERRIDES:
        return _MECHANIC_OVERRIDES[spell_id]
    effect = data["effect"]
    kind = effect["kind"]
    instructions = str(effect.get("instructions", "")).strip()
    if instructions:
        return _normalize_instruction_pl(instructions)
    if spell_id in _EXPLORATION_MECHANICS:
        return _EXPLORATION_MECHANICS[spell_id]
    if kind == "attack":
        damage = _damage_text(effect.get("damage", {}))
        save = effect.get("save_ability")
        if save:
            save_name = ABILITY_LABELS_PL.get(str(save), str(save))
            save_name = {
                "Siła": "Siłę",
                "Kondycja": "Kondycję",
                "Inteligencja": "Inteligencję",
                "Charyzma": "Charyzmę",
            }.get(save_name, save_name)
            success = (
                "połowa obrażeń"
                if effect.get("save_damage_on_success") == "half"
                else "bez obrażeń"
            )
            return f"Cel wykonuje rzut obronny na {save_name}. Porażka: {damage}; sukces: {success}."
        attack_kind = "dystansowy" if effect.get("attack_kind") == "ranged" else "wręcz"
        result = f"Wykonaj {attack_kind} rzut ataku czarem. Trafienie: {damage}."
        condition = effect.get("on_hit_condition")
        if condition:
            condition_text = _CONDITION_EFFECTS_PL.get(str(condition), str(condition))
            result += f" Dodatkowo: {condition_text}."
        return result
    if kind == "healing":
        healing = effect.get("healing", {})
        dice = _dice_pl(str(healing.get("dice", "")))
        modifier = " + modyfikator cechy czarowania" if effect.get("ability") else ""
        return (
            f"Żywa istota odzyskuje {dice}{modifier} PW. Komórka wyższego "
            "poziomu zwiększa liczbę kości zgodnie z opisem czaru."
        )
    if kind == "combat_action":
        action_type = effect.get("action_type")
        if action_type == "multi_target_damage":
            return f"Tworzysz {effect.get('projectile_count', 3)} pociski; każdy automatycznie trafia za 1k{effect.get('damage_die_sides', 4)} + {effect.get('damage_modifier', 0)} obrażeń od mocy. Możesz rozdzielić je między cele."
        if action_type == "reaction_ac_bonus":
            return f"Po trafieniu, przed obrażeniami, zyskujesz +{effect.get('value', 5)} do KP do początku następnej tury; ten sam atak jest oceniany ponownie."
        if action_type == "stabilize":
            return "Stabilizujesz żywą istotę mającą 0 PW. Czar nie działa na nieumarłych ani konstrukty."
        movement = effect.get("movement")
        if movement:
            move = {"teleport": "teleportuj się", "push": "odepchnij cel", "pull": "przyciągnij cel"}.get(movement.get("kind"), "przesuń cel")
            save = effect.get("save_ability")
            prefix = f"Po nieudanym rzucie obronnym na {ABILITY_LABELS_PL.get(str(save), str(save))} " if save else ""
            return f"{prefix}{move} o maks. {movement.get('distance_feet', 0)} stóp na legalne pole wskazane na planszy."
        if action_type == "spell_counter":
            return "Reakcją przerwij widziany czar w 60 stopach. Ten sam lub niższy poziom kończy się automatycznie; wyższy wymaga testu cechy czarującej ST 10 + poziom czaru."
    if kind == "exploration":
        return "Zagraj kartę, wybierz legalny cel i wykonaj dokładne instrukcje czaru pokazane przez system; wymagane komponenty i koszt są sprawdzane przed zatwierdzeniem."
    return f"System rozstrzyga efekt „{data['name']}” według aktualnych celów, zasobów i zasad czaru."


def _spell_flavor(actor_id: str, title: str, source_id: str) -> str:
    motifs = {
        "lorian": ("melodia", "refren", "opowieść", "szept"),
        "sylwen": ("korzeń", "wiatr", "żywa ziemia", "deszcz"),
        "rhogar": ("przysięga", "światło", "honor", "żar"),
        "erynd": ("trop", "cisza", "szlak", "strzała"),
        "veyra": ("iskra", "smoczy żar", "gest", "kaprys"),
        "kael": ("klauzula", "cień", "płomień", "dług"),
        "nimra": ("wzór", "margines", "teoria", "notatka"),
    }[actor_id]
    motif = motifs[sum(source_id.encode("utf-8")) % len(motifs)]
    return f"„{title}: {motif} na chwilę zmienia reguły świata.”"


def _spell_cards(actor_id: str) -> tuple[CharacterActionCardSpec, ...]:
    class_id = HERO_ARCHETYPES_BY_ID[actor_id].class_id
    if class_id not in SRD_CLASS_SPELL_IDS:
        return ()
    max_spell_level = 1 if class_id in {"paladin", "ranger"} else 2
    cards: list[CharacterActionCardSpec] = []
    for source_id in SRD_CLASS_SPELL_IDS[class_id]:
        path = PROJECT_ROOT / "content" / "spells" / f"{source_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        spell_level = int(data["level"])
        if spell_level > max_spell_level:
            continue
        required_level = (
            1 if spell_level == 0 or class_id not in {"paladin", "ranger"}
            else 2
        )
        if spell_level == 2:
            required_level = 3
        title = SPELL_NAMES_PL.get(source_id, str(data["name"])).upper()
        accent = tuple(CLASS_DECK_META[actor_id]["accent"])
        cards.append(
            _card(
                source_id,
                title,
                "spell",
                required_level,
                _spell_timing(data),
                _spell_mechanic(data),
                _spell_flavor(actor_id, title.title(), source_id),
                f"{class_id}_comic_v3",
                accent,
            )
        )
    return tuple(cards)


def _shared_cards(actor_id: str) -> tuple[CharacterActionCardSpec, ...]:
    class_id = HERO_ARCHETYPES_BY_ID[actor_id].class_id
    accent = tuple(CLASS_DECK_META[actor_id]["accent"])
    secondary = tuple(CLASS_DECK_META[actor_id]["secondary"])
    return (
        _card("accept", "AKCEPTUJ", "universal", 1, "", "", "", "control_comic_v2.png", (70, 157, 122)),
        _card("decline", "ODRZUĆ", "universal", 1, "", "", "", "control_comic_v2.png", (166, 78, 72)),
        _card("maneuvers", "MANEWRY", "universal", 1, "MENU AKCJI", "Otwórz dostępne manewry: Sprint, Unik, Odstąpienie, Pomoc, Przygotowanie, Ukrycie, Szukanie, Grapple i Shove.", "„Pozycja i właściwy moment są częścią każdego zwycięstwa.”", f"{class_id}_comic_v3", accent),
        _card(
            "equipment",
            "EKWIPUNEK",
            "universal",
            1,
            "MENU WŁASNE",
            (
                "Poza Szałem otwórz ekwipunek: dobądź, schowaj, zamień lub upuść przedmiot albo użyj legalnej aktywnej opcji. Podczas Szału Brakka nie może korzystać z ekwipunku; nadal może atakować trzymaną bronią."
                if actor_id == "brakka"
                else "Otwórz ekwipunek. Możesz dobyć, schować, zamienić lub upuścić przedmiot oraz użyć legalnej aktywnej opcji wyposażenia."
            ),
            "„Przygotowanie zaczyna się przed pierwszym rzutem.”",
            f"{class_id}_comic_v3",
            secondary,
        ),
    )


def _feature_cards(actor_id: str) -> tuple[CharacterActionCardSpec, ...]:
    accent = tuple(CLASS_DECK_META[actor_id]["accent"])
    class_id = HERO_ARCHETYPES_BY_ID[actor_id].class_id
    return tuple(
        _card(source_id, title, "feature", level, timing, mechanic, flavor, f"{class_id}_comic_v3", accent)
        for source_id, title, level, timing, mechanic, flavor in FEATURE_CARDS[actor_id]
    )


def _additional_deck(actor_id: str) -> CharacterDeckSpec:
    meta = CLASS_DECK_META[actor_id]
    class_id = HERO_ARCHETYPES_BY_ID[actor_id].class_id
    return CharacterDeckSpec(
        actor_id=actor_id,
        deck_title=str(meta["title"]),
        subtitle=str(meta["subtitle"]),
        accent=tuple(meta["accent"]),
        secondary=tuple(meta["secondary"]),
        back_asset=f"{class_id}_comic_v3_01.png",
        action_cards=(*_shared_cards(actor_id), *_feature_cards(actor_id), *_spell_cards(actor_id)),
        dossier_intro=str(meta["intro"]),
        dossier_campaign=str(meta["campaign"]),
        passives=tuple(meta["passives"]),
        progression=tuple(meta["progression"]),
    )


ADDITIONAL_DECKS = {
    actor_id: _additional_deck(actor_id)
    for actor_id in CLASS_DECK_META
}


CHARACTER_DECKS = {
    GARRAN_DECK.actor_id: GARRAN_DECK,
    DAGNA_DECK.actor_id: DAGNA_DECK,
    **ADDITIONAL_DECKS,
}


def _curated_action(
    actor_id: str,
    source_id: str,
    title: str,
    kind: str,
    level: int,
    timing: str,
    mechanic: str,
    flavor: str,
) -> CharacterActionCardSpec:
    deck = CHARACTER_DECKS[actor_id]
    return _card(
        source_id,
        title,
        kind,
        level,
        timing,
        mechanic,
        flavor,
        f"archetype_{actor_id}_cards_v1.png",
        deck.accent,
    )


def _curated_menu_cards(actor_id: str) -> tuple[CharacterActionCardSpec, ...]:
    existing = CHARACTER_DECKS[actor_id].action_cards
    return tuple(
        card
        for source_id in ("accept", "decline", "maneuvers", "equipment")
        for card in existing
        if card.source_id == source_id
    )


CURATED_ACTION_CARDS: dict[str, tuple[CharacterActionCardSpec, ...]] = {
    "garran": (
        _curated_action("garran", "second_wind", "DRUGI ODDECH", "feature", 1, "AKCJA DOD. · WŁASNY", "Rzuć k10. Odzyskaj wynik + poziom Garrana PW. 1 użycie; odnawia krótki lub długi odpoczynek.", "„Linia stoi tak długo, jak długo ktoś potrafi wstać.”"),
        _curated_action("garran", "action_surge", "ZRYW AKCJI", "feature", 1, "PO WYKORZYSTANIU AKCJI", "Natychmiast odzyskaj zużytą akcję tej tury. 1 użycie; odnawia krótki lub długi odpoczynek.", "„Jeszcze jeden krok. Jeszcze jeden rozkaz.”"),
        _curated_action("garran", "lay_on_hands", "RATUNEK POLOWY", "feature", 1, "AKCJA · DOTYK", "Wybierz na planszy rannego sojusznika i liczbę PW z puli 5 × poziom Garrana. Pula odnawia się po długim odpoczynku.", "„Najpierw zatamuj krew. Bohaterstwo może poczekać.”"),
        _curated_action("garran", "defensive_stance", "POZYCJA OBRONNA", "feature", 1, "AKCJA DOD. · WŁASNY", "Ataki przeciw Garranowi mają utrudnienie do początku jego następnej tury. 1 użycie; odnawia krótki lub długi odpoczynek.", "„Tarcza nie musi wygrać. Musi wytrzymać.”"),
        _curated_action("garran", "command", "ROZKAZ: STAĆ!", "spell", 2, "AKCJA · 60 STÓP", "Wskaż przeciwnika i wydaj rozkaz zatrzymania. Koszt: 1 Taktyka.", "„Jedno słowo w odpowiedniej chwili potrafi zatrzymać szarżę.”"),
        _curated_action("garran", "shield_of_faith", "OSŁONA TARCZĄ", "spell", 2, "AKCJA DOD. · SOJUSZNIK", "Wzmocnij obronę wybranego sojusznika. Koszt: 1 Taktyka.", "„Stań za mną i pilnuj lewej strony.”"),
        _curated_action("garran", "heroism", "MOWA DOWÓDCY", "spell", 3, "AKCJA · SOJUSZNIK", "Uodpornij sojusznika na strach i podtrzymuj jego wolę walki. Koszt: 1 Taktyka.", "„Nie musicie być bez strachu. Musicie zrobić następny krok.”"),
        _curated_action("garran", "warding_bond", "OSŁONA TOWARZYSZA", "spell", 3, "AKCJA · DOTYK", "Sąsiadujący sojusznik otrzymuje +1 KP, +1 do obron i odporność na obrażenia; Garran otrzymuje taką samą liczbę obrażeń. 1 użycie na długi odpoczynek.", "„Jeśli cios ma przejść, niech przejdzie także przeze mnie.”"),
    ),
    "brakka": (
        _curated_action("brakka", "rage", "SZAŁ", "feature", 1, "AKCJA DOD. · PRZEŁĄCZNIK", "Włącz Szał: przewaga w testach i obronach Siły, +2 do obrażeń ataków wręcz opartych na Sile oraz odporność na kłute, cięte i obuchowe. Zeskanuj ponownie, aby wyłączyć.", "„Nie jestem burzą. Jestem tym, co po niej nadal stoi.”"),
        _curated_action("brakka", "reckless_attack", "LEKKOMYŚLNY ATAK", "feature", 1, "PRZED PIERWSZYM ATAKIEM", "Pierwszy atak wręcz oparty na Sile ma przewagę. Ataki przeciw Brakce mają przewagę do początku jej następnej tury.", "„Jeśli odsłonię gardę, zobaczę, kto naprawdę chce podejść.”"),
        _curated_action("brakka", "frenzy", "SZAŁ BOJOWY", "feature", 1, "TYLKO PODCZAS SZAŁU", "Zeskanuj podczas Szału, aby włączyć. Od następnej swojej tury ponowny skan wydaje akcję dodatkową i daje 1 dodatkowy atak trzymaną bronią wręcz. Kończy się ze Szałem: otrzymujesz 1 poziom Wyczerpania (poziom 1: utrudnienie w testach cech). Długi odpoczynek usuwa 1 poziom.", "„Gniew ma jeszcze drugi bieg.”"),
        _curated_action("brakka", "action_surge", "NIEPOWSTRZYMANY IMPET", "feature", 2, "PO WYKORZYSTANIU AKCJI", "Natychmiast odzyskaj zużytą akcję. 1 użycie; odnawia krótki lub długi odpoczynek.", "„Jeszcze jeden zamach. Mur już pęka.”"),
        _curated_action("brakka", "cunning_action", "DRAPIEŻNY PĘD", "feature", 2, "AKCJA DOD. · WŁASNA TURA", "Wybierz Sprint, Odstąpienie albo Ukrycie jako akcję dodatkową.", "„Nie uciekam. Wybieram miejsce następnego uderzenia.”"),
        _curated_action("brakka", "false_life", "NIE DO ZDARCIA", "spell", 3, "AKCJA · WŁASNY", "Zyskaj tymczasowe PW. Koszt: 1 Dzikość.", "„Jeszcze stoję, więc jeszcze nie skończyliśmy.”"),
        _curated_action("brakka", "thunderwave", "OGŁUSZAJĄCY RYK", "spell", 3, "AKCJA · OBSZAR", "Uderz falą siły i odepchnij pobliskich przeciwników. Koszt: 1 Dzikość.", "„Kiedy ryczę, nawet kamień robi krok w tył.”"),
    ),
    "mira": (
        _curated_action("mira", "cunning_action", "PRZEBIEGŁA AKCJA", "feature", 1, "AKCJA DOD. · WŁASNA TURA", "Wybierz Sprint, Odstąpienie albo Ukrycie jako akcję dodatkową.", "„Najlepsze wyjście jest zwykle tam, gdzie nikt nie patrzy.”"),
        _curated_action("mira", "instinctive_dodge", "UNIK INSTYNKTOWNY", "feature", 1, "AKCJA DOD. · WŁASNY", "Ataki przeciw Mirze mają utrudnienie do początku jej następnej tury. 1 użycie; odnawia krótki lub długi odpoczynek.", "„Cios trafia tylko tam, gdzie byłam chwilę temu.”"),
        _curated_action("mira", "invisibility", "ZNIKNIĘCIE W DYMIE", "spell", 1, "AKCJA · WŁASNY", "Mira otrzymuje status Niewidzialna zgodnie z efektem karty. Koszt: 1 Fortel; pula 2/2 odnawia się po długim odpoczynku.", "„Najpierw dym. Potem już tylko brak Miry.”"),
        _curated_action("mira", "find_traps", "WYKRYCIE PUŁAPEK", "spell", 1, "AKCJA · OBSZAR", "W walce wskaż obszar na planszy i ujawnij wszystkie znajdujące się w nim pułapki. Koszt: 1 Fortel; pula 2/2 odnawia się po długim odpoczynku.", "„Mechanizm zawsze zostawia ślad dla kogoś, kto wie, gdzie nie stawiać dłoni.”"),
        _curated_action("mira", "vicious_mockery", "BRUDNA SZTUCZKA", "spell", 2, "AKCJA · 60 STÓP", "Zdezorientuj przeciwnika i utrudnij jego następny atak. Koszt: 1 Fortel.", "„Patrzysz na ostrze. Błąd był o pół kroku wcześniej.”"),
        _curated_action("mira", "true_strike", "WYKORZYSTANIE SŁABOŚCI", "spell", 2, "AKCJA · KONCENTRACJA", "Wskaż przeciwnika i przygotuj przewagę do następnego ataku. Koszt: 1 Fortel.", "„Każda garda ma szew. Trzeba tylko poczekać, aż pęknie.”"),
        _curated_action("mira", "mirror_image", "ZMYŁKA", "spell", 3, "AKCJA · WŁASNY", "Utwórz mylące duplikaty przechwytujące ataki. Koszt: 1 Fortel.", "„Jeśli widzisz trzy Miry, żadna nie stoi tam przypadkiem.”"),
    ),
    "dagna": (
        _curated_action("dagna", "sacred_flame", "ŚWIĘTY PŁOMIEŃ", "spell", 1, "AKCJA · 60 STÓP", "Cel wykonuje obronę na Zręczność. Porażka: 1k8 obrażeń promienistych; sukces: bez obrażeń.", "„Światło nie pyta, po której stronie stoi cień.”"),
        _curated_action("dagna", "healing_word", "LECZĄCE SŁOWO", "spell", 1, "AKCJA DOD. · 60 STÓP", "Legalny żywy cel odzyskuje 1k4 + modyfikator Mądrości PW. Zużywa komórkę 1. poziomu lub wyższą.", "„Jeszcze nie. Wrócisz, kiedy sama ci pozwolę.”"),
        _curated_action("dagna", "bless", "BŁOGOSŁAWIEŃSTWO", "spell", 1, "AKCJA · KONCENTRACJA", "Do 3 sojuszników dodaje k4 do ataków i rzutów obronnych przez maks. 1 minutę. Wynik kości wpisuje gracz przy rzucie.", "„Niech każdy z was znajdzie o pół kroku więcej odwagi.”"),
        _curated_action("dagna", "preserve_life", "ZACHOWANIE ŻYCIA", "feature", 2, "AKCJA · CELE NA PLANSZY", "Rozdziel 5 × poziom Dagny PW pomiędzy wskazane cele, ale nie lecz żadnego powyżej połowy maksymalnych PW. 1 Boska Moc.", "„Nie musicie być cali. Musicie być żywi.”"),
        _curated_action("dagna", "sanctuary", "SANKTUARIUM", "spell", 1, "AKCJA DOD. · 30 STÓP", "Atakujący chroniony cel wykonuje obronę na Mądrość; porażka wymusza zmianę celu albo utratę ataku. Kończy się, gdy chroniony atakuje lub szkodzi.", "„Przez chwilę wojna ominie właśnie ciebie.”"),
        _curated_action("dagna", "guiding_bolt", "POCISK PRZEWODNI", "spell", 2, "AKCJA · 120 STÓP", "Dystansowy atak czarem. Trafienie: 4k6 obrażeń promienistych; następny atak przeciw celowi ma przewagę.", "„Za tym światłem pójdą pozostali.”"),
        _curated_action("dagna", "aid", "POMOC", "spell", 3, "AKCJA · 30 STÓP", "Trzem celom zwiększ aktualne i maksymalne PW o 5 na 8 godzin.", "„Siła pożyczona na dziś nadal może ocalić jutro.”"),
        _curated_action("dagna", "lesser_restoration", "POMNIEJSZE PRZYWRÓCENIE", "spell", 3, "AKCJA · DOTYK", "Usuń jeden obsługiwany stan: Oślepiony, Ogłuchnięty, Sparaliżowany albo Zatruty.", "„Ciało pamięta drogę powrotną. Trzeba mu ją tylko pokazać.”"),
        _curated_action("dagna", "warding_bond", "WIĘŹ OCHRONNA", "spell", 3, "AKCJA · DOTYK", "Cel otrzymuje +1 KP, +1 do obron i odporność na obrażenia; Dagna otrzymuje taką samą liczbę obrażeń.", "„Ból podzielony nadal boli. Ale rzadziej zabija.”"),
    ),
    "lorian": (
        _curated_action("lorian", "bardic_inspiration", "INSPIRACJA BARDOWSKA", "feature", 1, "AKCJA DOD. / PROMPT PRZED RZUTEM", "Sojusznik otrzymuje k6 do jednego testu, ataku lub obrony przez 10 minut. Wpisanie 0 zachowuje efekt; 1–6 zużywa go.", "„Jeszcze nie znasz końca tej historii.”"),
        _curated_action("lorian", "vicious_mockery", "ZJADLIWA KPINA", "spell", 1, "AKCJA · 60 STÓP", "Cel wykonuje obronę na Mądrość. Porażka: 1k4 obrażeń psychicznych i utrudnienie następnego ataku.", "„To nie twoja zbroja skrzypi. To odwaga.”"),
        _curated_action("lorian", "thunderwave", "GRZMIĄCY REFREN", "spell", 1, "AKCJA · OBSZAR", "Uderz pobliskich przeciwników falą dźwięku i odepchnij ich.", "„Refren powinien poruszyć publiczność. Czasem dosłownie.”"),
        _curated_action("lorian", "healing_word", "LECZĄCE SŁOWO", "spell", 1, "AKCJA DOD. · 60 STÓP", "Legalny żywy cel odzyskuje 1k4 + modyfikator Charyzmy PW.", "„Wstawaj. Publiczność jeszcze nie wyszła.”"),
        _curated_action("lorian", "faerie_fire", "OGNIKI", "spell", 2, "AKCJA · KONCENTRACJA", "Cele w obszarze wykonują obronę na Zręczność. Porażka: ataki przeciw nim mają przewagę i nie korzystają z Niewidzialności.", "„Skoro chcą się ukryć, dajmy im lepsze światło.”"),
        _curated_action("lorian", "heroism", "BOHATERSKI REFREN", "spell", 2, "AKCJA · SOJUSZNIK", "Uodpornij sojusznika na strach i odnawiaj jego tymczasowe PW podczas koncentracji.", "„Odwaga lepiej trzyma rytm, kiedy nie śpiewa sama.”"),
        _curated_action("lorian", "cutting_words", "CIĘTA RIPOSTA", "feature", 3, "REAKCJA PO UJAWNIENIU RZUTU", "Po ujawnieniu ataku przeciwnika odejmij k6 od testu trafienia; po ujawnieniu obrażeń zamiast tego odejmij k6 od obrażeń.", "„Prawie imponujące. Prawie.”"),
        _curated_action("lorian", "hideous_laughter", "OBEZWŁADNIAJĄCY ŻART", "spell", 3, "AKCJA · KONTROLA", "Powal przeciwnika śmiechem i wyłącz go z działania do udanej obrony.", "„Najgorszy moment na śmiech jest zwykle najlepszym momentem dla mnie.”"),
    ),
    "nimra": (
        _curated_action("nimra", "ray_of_frost", "PROMIEŃ MROZU", "spell", 1, "AKCJA · 60 STÓP", "Dystansowy atak czarem. Trafienie: 1k8 obrażeń od zimna i szybkość celu spada o 10 stóp do następnej tury Nimry.", "„Ruch jest tylko ciepłem, któremu odebrano argumenty.”"),
        _curated_action("nimra", "grease", "PĘTAJĄCE KORZENIE", "spell", 1, "AKCJA · 60 STÓP", "Wskaż obszar 10 × 10 stóp. Staje się trudnym terenem; istoty po nieudanej obronie na Zręczność zostają Powalone.", "„Natura i geometria zgadzają się częściej, niż sądzisz.”"),
        _curated_action("nimra", "shield", "TARCZA", "spell", 1, "REAKCJA PO TRAFIENIU", "Po ujawnieniu trafienia, przed obrażeniami, zyskaj +5 KP do początku następnej tury. Atak zostaje oceniony ponownie.", "„Nie neguję ataku. Neguję jego wniosek.”"),
        _curated_action("nimra", "sleep", "SEN", "spell", 1, "AKCJA · 90 STÓP", "Rzuć 5k8. Usypiaj cele w obszarze od najniższych aktualnych PW, odejmując pełne PW każdego uśpionego celu.", "„Czasem najlepszą kontrolą jest bardzo przekonująca cisza.”"),
        _curated_action("nimra", "fog_cloud", "MGŁA", "spell", 2, "AKCJA · KONCENTRACJA", "Wskazany obszar staje się silnie przesłonięty. Blokuje widzenie i wymagające go cele do zakończenia koncentracji.", "„Jeśli nie można zmienić pola bitwy, można zmienić to, kto je widzi.”"),
        _curated_action("nimra", "web", "PAJĘCZYNA", "spell", 3, "AKCJA · KONCENTRACJA", "Tworzy trudny teren; cele po nieudanej obronie na Zręczność są Unieruchomione i mogą próbować się uwolnić.", "„Chaos jest znośniejszy, kiedy przyklei się go do podłogi.”"),
        _curated_action("nimra", "hold_person", "UNIERUCHOMIENIE OSOBY", "spell", 3, "AKCJA · KONCENTRACJA", "Humanoid po nieudanej obronie na Mądrość jest Sparaliżowany. Ponawia obronę na końcu swojej tury.", "„Proszę pozostać dokładnie tam, gdzie kończy się pański argument.”"),
        _curated_action("nimra", "misty_step", "MGLISTY KROK", "spell", 3, "AKCJA DOD. · WŁASNY", "Teleportuj Nimrę na widoczne, legalne pole w 30 stopach wskazane na planszy.", "„Odległość nie jest przeszkodą. Jest błędem indeksowania.”"),
        _curated_action("nimra", "shatter", "ROZTRZASKANIE", "spell", 3, "AKCJA · OBSZAR", "Cele wykonują obronę na Kondycję. Porażka: 3k8 obrażeń od grzmotu; sukces: połowa.", "„Rezonans to elegancka nazwa na właściwe pytanie zadane zbyt głośno.”"),
    ),
    "erynd": (
        _curated_action("erynd", "hunters_mark", "OZNACZENIE CELU", "spell", 1, "AKCJA DOD. · KONCENTRACJA", "Oznacz przeciwnika wskazanego na planszy. Trafienia bronią zadają mu dodatkowe 1k6 obrażeń. Koszt: 1 Instynkt.", "„Cel może uciekać. Ślad już nie.”"),
        _curated_action("erynd", "goodberry", "DOBRE JAGODY", "spell", 1, "AKCJA", "Utwórz pulę 10 jagód. Każda użyta w walce akcją leczy 1 PW. Koszt: 1 Instynkt.", "„Mały zapas jest różnicą między odwrotem a grobem.”"),
        _curated_action("erynd", "cunning_action", "ZWIADOWCZA MOBILNOŚĆ", "feature", 1, "AKCJA DOD. · WŁASNA TURA", "Wybierz Sprint, Odstąpienie albo Ukrycie jako akcję dodatkową.", "„Zwiadowca wraca z wiadomością albo nie był zwiadowcą.”"),
        _curated_action("erynd", "find_traps", "WYKRYCIE PUŁAPEK", "spell", 1, "AKCJA · OBSZAR", "Wskaż obszar na planszy i ujawnij wszystkie znajdujące się w nim pułapki. Koszt: 1 Instynkt.", "„Najgroźniejszy ślad jest zrobiony przez kogoś, kto chciał go ukryć.”"),
        _curated_action("erynd", "true_strike", "STRZELECKA CIERPLIWOŚĆ", "spell", 2, "AKCJA · KONCENTRACJA", "Wskaż przeciwnika i przygotuj przewagę do następnego ataku. Koszt: 1 Instynkt.", "„Najlepszy strzał zaczyna się od decyzji, żeby jeszcze nie strzelać.”"),
        _curated_action("erynd", "misty_step", "LEŚNY KROK", "spell", 2, "AKCJA DOD. · POLE", "Przenieś się na widoczne legalne pole. Koszt: 1 Instynkt.", "„Między dwoma cieniami zawsze istnieje krótsza droga.”"),
        _curated_action("erynd", "spike_growth", "KOLCZASTE POSZYCIE", "spell", 3, "AKCJA · OBSZAR", "Utwórz niebezpieczny trudny teren zadający obrażenia podczas ruchu. Koszt: 1 Instynkt.", "„Las nie ściga intruzów. Pozwala im wejść głębiej.”"),
        _curated_action("erynd", "see_invisibility", "OKO ŁOWCY", "spell", 3, "AKCJA · WŁASNY", "Ujawnij niewidzialnych i ukrytych przeciwników. Koszt: 1 Instynkt.", "„Nie wszystko, czego nie widać, potrafi przestać zostawiać ślady.”"),
    ),
}


for _actor_id, _cards in CURATED_ACTION_CARDS.items():
    _base = CHARACTER_DECKS[_actor_id]
    CHARACTER_DECKS[_actor_id] = replace(
        _base,
        action_cards=(*_curated_menu_cards(_actor_id), *_cards),
    )


CURATED_PASSIVES: dict[str, tuple[str, ...]] = {
    "garran": (
        "Styl walki: Obrona — +1 KP podczas noszenia pancerza.",
        "Żelazna linia — sojusznik flankujący z Garranem tego samego przeciwnika ma +1 KP przeciw jego atakom.",
        "Stopień wojskowy — sceny rozpoznające Garrana mogą udostępnić mu wojskową opcję interakcji.",
        "Skaza: Wina dowódcy — gdy żywy sojusznik w 30 stopach ma 0 PW i nie leży obok Garrana, Garran ma −1 do ataków i rzutów obronnych.",
    ),
    "brakka": (
        "Widzenie w ciemności — w niemagicznej ciemności do 60 stóp widzi jak w półmroku; nie przenika magicznej ciemności ani mgły.",
        "Obrona bez pancerza — KP 10 + Zręczność + Kondycja; tarcza jest dozwolona.",
        "Nieustępliwość półorka — automatycznie przy pierwszym zejściu do 0 PW pozostawia Brakkę z 1 PW, o ile obrażenia nie zabijają jej natychmiast; 1 użycie na długi odpoczynek.",
        "Dzikie ataki — krytyczny atak bronią wręcz dodaje jedną kość broni.",
        "Skaza: Bitewny amok — podczas Szału Brakka nie może używać mikstur, zwojów ani aktywnych właściwości przedmiotów. Może nadal atakować trzymaną bronią.",
    ),
    "mira": (
        "Ekspertyza — podwójna biegłość w Śledztwie i Zwinnych dłoniach.",
        "Atak ukradkowy — raz na turę +1k6 po spełnieniu warunków przewagi albo obecności sojusznika przy celu.",
        "Szczęście niziołka — ponów naturalną 1 w ataku, teście albo obronie.",
        "Odważna — przewaga w rzutach obronnych przeciw Przerażeniu.",
        "Niziołcza zwinność — przechodź przez większe istoty; +1 KP tylko przeciw atakom okazyjnym.",
        "Skaza: Lęk przed przesłuchaniem — pierwszy test Charyzmy wobec autorytetu w instancji ma utrudnienie, chyba że Mira jest przebrana albo otrzymuje Pomoc.",
    ),
    "dagna": (
        "Widzenie w ciemności — widzi w ciemności do 60 stóp; ciężki pancerz nie zmniejsza jej szybkości.",
        "Uczeń Życia — czar leczenia przywraca dodatkowe 2 + poziom czaru PW.",
        "Krasnoludzka wytrzymałość — +1 maksymalnego PW na każdy poziom.",
        "Krasnoludzka odporność — przewaga przeciw truciźnie i odporność na obrażenia od trucizny.",
        "Skaza: Nikogo nie zostawiam — gdy sojusznik w 30 stopach ma 0 PW, Dagna ma utrudnienie w atakach i testach innych niż Medycyna lub pomoc rannemu.",
    ),
    "lorian": (
        "Widzenie w ciemności — widzi w ciemności do 60 stóp.",
        "Wszechstronność półelfa — dodatkowe biegłości wspierają rozmowę, obserwację i skradanie.",
        "Fey Ancestry — przewaga przeciw zauroczeniu i odporność na magiczny sen.",
        "Skaza: Głód aprobaty — po nieudanym teście społecznym Lorian nie może użyć Inspiracji bardowskiej w tej interakcji, dopóki sojusznik nie udzieli mu Pomocy.",
    ),
    "nimra": (
        "Widzenie w ciemności — widzi w ciemności do 60 stóp.",
        "Gnomia przebiegłość — przewaga w obronach INT, MĄD i CHA przeciw magii.",
        "Odzyskiwanie magiczne — raz na długi odpoczynek odzyskaj komórki podczas krótkiego odpoczynku.",
        "Skaza: Echo magicznego wycieku — pierwsza naturalna 1 w ataku czarem lub utrata Koncentracji blokuje nowe czary z Koncentracją do końca tury; raz na walkę.",
    ),
    "erynd": (
        "Widzenie w ciemności — widzi w ciemności do 60 stóp.",
        "Styl walki: Łucznictwo — +2 do dystansowych ataków bronią.",
        "Ekspertyza zwiadowcy — podwójna biegłość w Skradaniu i Sztuce przetrwania.",
        "Naturalny odkrywca — korzyści nawigacji i podróży w wybranym terenie.",
        "Fey Ancestry — przewaga przeciw zauroczeniu i odporność na magiczny sen.",
        "Skaza: Ocalały z zasadzki — gdy przeciwnicy zaskakują drużynę, Erynd jest Przerażony do końca swojej pierwszej tury; Warta lub Alarm temu zapobiegają.",
    ),
}

CURATED_PROGRESSION: dict[str, tuple[str, ...]] = {
    "garran": (
        "Poziom 1: Drugi oddech, Zryw akcji, Ratunek polowy i Pozycja obronna.",
        "Poziom 2: 2 Taktyki — Rozkaz: Stać! oraz Osłona tarczą.",
        "Poziom 3: 3 Taktyki — Mowa dowódcy i Osłona towarzysza; Czempion daje krytyk 19–20.",
    ),
    "brakka": (
        "Poziom 1: Szał, Lekkomyślny atak i Szał bojowy.",
        "Poziom 2: Niepowstrzymany impet oraz Drapieżny pęd.",
        "Poziom 3: 2 Dzikości — Nie do zdarcia oraz Ogłuszający ryk. Każdy zakończony Szał bojowy daje 1 poziom Wyczerpania; długi odpoczynek usuwa 1 poziom.",
    ),
    "mira": (
        "Poziom 1: Przebiegła akcja, Unik instynktowny, Niewidzialność i Wykrycie pułapek; 2 Fortele.",
        "Poziom 2: Brudna sztuczka oraz Wykorzystanie słabości.",
        "Poziom 3: Zmyłka; pula rośnie do 3 Forteli, a Atak ukradkowy do 2k6.",
    ),
    "dagna": (
        "Poziom 1: Święty płomień, Leczące słowo, Błogosławieństwo i Sanktuarium.",
        "Poziom 2: Zachowanie życia oraz Pocisk przewodni.",
        "Poziom 3: Pomoc, Pomniejsze przywrócenie i Więź ochronna.",
    ),
    "lorian": (
        "Poziom 1: Inspiracja, Zjadliwa kpina, Grzmiący refren i Leczące słowo.",
        "Poziom 2: Ogniki oraz Bohaterski refren.",
        "Poziom 3: Cięta riposta oraz Obezwładniający żart.",
    ),
    "nimra": (
        "Poziom 1: Promień mrozu, Pętające korzenie, Tarcza i Sen.",
        "Poziom 2: Mgła.",
        "Poziom 3: Pajęczyna, Unieruchomienie osoby, Mglisty krok i Roztrzaskanie.",
    ),
    "erynd": (
        "Poziom 1: Oznaczenie celu, Dobre jagody, Zwiadowcza mobilność i Wykrycie pułapek; 2 Instynkty.",
        "Poziom 2: Strzelecka cierpliwość oraz Leśny krok.",
        "Poziom 3: Kolczaste poszycie i Oko łowcy; pula rośnie do 3 Instynktów.",
    ),
}

for _actor_id, _passives in CURATED_PASSIVES.items():
    CHARACTER_DECKS[_actor_id] = replace(
        CHARACTER_DECKS[_actor_id],
        passives=_passives,
        progression=CURATED_PROGRESSION[_actor_id],
    )

# Backward-compatible aliases must point at the fully curated versions, not the
# early construction templates used above.
GARRAN_DECK = CHARACTER_DECKS["garran"]
DAGNA_DECK = CHARACTER_DECKS["dagna"]


def _synchronized_action_card(
    card: CharacterActionCardSpec,
    *,
    actor_id: str,
) -> CharacterActionCardSpec | None:
    """Return the printable card backed by the current runtime/content contract."""
    if card.kind == "universal":
        if card.source_id in {"accept", "decline"}:
            return replace(card, timing="", mechanic="", flavor="")
        return card
    definition = card_action_definition(card.source_id)
    if definition.phase is CardPhase.REMOVED:
        return None
    if card.kind != "spell":
        return card
    # Alarm is intentionally adapted to the board game's short-rest prompt;
    # its SRD area/duration text would describe a flow the runtime does not use.
    if card.source_id == "alarm":
        return card
    spell_path = PROJECT_ROOT / "content" / "spells" / f"{card.source_id}.json"
    spell_data = json.loads(spell_path.read_text(encoding="utf-8"))
    mechanic = _spell_mechanic(spell_data)
    resource_note = {
        **{
            ("garran", source_id): (
                " Koszt: 1 Taktyka (2/2; od poziomu 3: 3/3; długi odpoczynek)."
            )
            for source_id in {"command", "shield_of_faith", "heroism", "warding_bond"}
        },
        **{
            ("brakka", source_id): (
                " Koszt: 1 Dzikość (2/2; długi odpoczynek)."
            )
            for source_id in {"false_life", "thunderwave"}
        },
        ("mira", "invisibility"): (
            " Koszt: 1 Fortel (2/2; od poziomu 3: 3/3; długi odpoczynek)."
        ),
        ("mira", "find_traps"): (
            " Koszt: 1 Fortel (2/2; od poziomu 3: 3/3; długi odpoczynek)."
        ),
        **{
            ("mira", source_id): " Koszt: 1 Fortel."
            for source_id in {"vicious_mockery", "true_strike", "mirror_image"}
        },
        ("erynd", "hunters_mark"): " Koszt: 1 Instynkt.",
        ("erynd", "goodberry"): " Koszt: 1 Instynkt.",
        ("erynd", "find_traps"): " Koszt: 1 Instynkt.",
        ("erynd", "true_strike"): " Koszt: 1 Instynkt.",
        ("erynd", "misty_step"): " Koszt: 1 Instynkt.",
        ("erynd", "spike_growth"): " Koszt: 1 Instynkt.",
        ("erynd", "see_invisibility"): " Koszt: 1 Instynkt.",
    }.get((actor_id, card.source_id), "")
    return replace(
        card,
        timing=_spell_timing(spell_data),
        mechanic=f"{mechanic}{resource_note}",
    )


def printable_action_cards(
    deck: CharacterDeckSpec,
) -> tuple[CharacterActionCardSpec, ...]:
    """Synchronize descriptions and omit cards deliberately removed from play."""
    synchronized = (
        _synchronized_action_card(card, actor_id=deck.actor_id)
        for card in deck.action_cards
    )
    return tuple(card for card in synchronized if card is not None)


def _phase_label(spec: CharacterActionCardSpec) -> str:
    if spec.kind == "universal":
        return "KONTROLA"
    phase = card_action_definition(spec.source_id).phase
    return {
        CardPhase.COMBAT: "WALKA",
        CardPhase.EXPLORATION: "EKSPLORACJA",
        CardPhase.BOTH: "WALKA/EKSPL.",
        CardPhase.REMOVED: "WYCOFANA",
    }[phase]


@dataclass(frozen=True, slots=True)
class CardArtPanel:
    asset: str
    panel_index: int
    columns: int = 2
    rows: int = 3


def _panel_assignments(
    asset: str,
    source_ids: tuple[str, ...],
) -> dict[str, CardArtPanel]:
    return {
        source_id: CardArtPanel(asset, panel_index)
        for panel_index, source_id in enumerate(source_ids)
    }


CONTROL_ART = {
    "accept": CardArtPanel("control_comic_v2.png", 0, columns=1, rows=2),
    "decline": CardArtPanel("control_comic_v2.png", 1, columns=1, rows=2),
}

GARRAN_ART = _panel_assignments(
    "fighter_comic_v2.png",
    (
        "basic_attack",
        "maneuvers",
        "equipment",
        "second_wind",
        "action_surge",
        "_deck_back",
    ),
)

DAGNA_ART = {
    **_panel_assignments(
        "cleric_comic_v2_01.png",
        (
            "basic_attack",
            "maneuvers",
            "equipment",
            "sacred_flame",
            "guidance",
            "spare_the_dying",
        ),
    ),
    **_panel_assignments(
        "cleric_comic_v2_02.png",
        (
            "bane",
            "bless",
            "command",
            "create_or_destroy_water",
            "cure_wounds",
            "detect_evil_and_good",
        ),
    ),
    **_panel_assignments(
        "cleric_comic_v2_03.png",
        (
            "detect_magic",
            "detect_poison_and_disease",
            "guiding_bolt",
            "healing_word",
            "inflict_wounds",
            "protection_from_evil_and_good",
        ),
    ),
    **_panel_assignments(
        "cleric_comic_v2_04.png",
        (
            "purify_food_and_drink",
            "sanctuary",
            "shield_of_faith",
            "turn_undead",
            "preserve_life",
            "aid",
        ),
    ),
    **_panel_assignments(
        "cleric_comic_v2_05.png",
        (
            "augury",
            "blindness_deafness",
            "calm_emotions",
            "continual_flame",
            "enhance_ability",
            "find_traps",
        ),
    ),
    **_panel_assignments(
        "cleric_comic_v2_06.png",
        (
            "gentle_repose",
            "hold_person",
            "lesser_restoration",
            "locate_object",
            "prayer_of_healing",
            "protection_from_poison",
        ),
    ),
    **_panel_assignments(
        "cleric_comic_v2_07.png",
        (
            "silence",
            "spiritual_weapon",
            "warding_bond",
            "zone_of_truth",
            "_deck_back",
            "_passive_back",
        ),
    ),
}


def _atlas_assignments(deck: CharacterDeckSpec) -> dict[str, CardArtPanel]:
    """Assign each class action and both reverses to a unique 4×6 atlas panel."""
    source_ids = (
        *(
            card.source_id
            for card in deck.action_cards
            if card.source_id not in {"accept", "decline"}
        ),
        "_deck_back",
        "_passive_back",
    )
    class_id = deck.profile.class_id
    result: dict[str, CardArtPanel] = {}
    for absolute_index, source_id in enumerate(source_ids):
        sheet_number = absolute_index // 24 + 1
        panel_index = absolute_index % 24
        result[source_id] = CardArtPanel(
            f"{class_id}_comic_v3_{sheet_number:02d}.png",
            panel_index,
            columns=4,
            rows=6,
        )
    return result


ADDITIONAL_ART = {
    actor_id: _atlas_assignments(deck)
    for actor_id, deck in ADDITIONAL_DECKS.items()
}


def _wrapped_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    max_width: int,
    *,
    max_lines: int | None = None,
) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or ("",):
        words = paragraph.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1] and draw.textbbox(
            (0, 0), f"{lines[-1]}…", font=font
        )[2] > max_width:
            lines[-1] = lines[-1][:-1].rstrip()
        lines[-1] = f"{lines[-1]}…"
    return lines


def _fit_title_font(draw: ImageDraw.ImageDraw, title: str, max_width: int):
    for size_mm in (4.25, 3.9, 3.55, 3.2, 2.9):
        font = _font(_mm(size_mm), serif=True, bold=True)
        if draw.textbbox((0, 0), title, font=font)[2] <= max_width:
            return font
    return _font(_mm(2.65), serif=True, bold=True)


def _fit_timing_font(
    draw: ImageDraw.ImageDraw,
    timing_text: str,
    max_width: int,
):
    size_mm = 2.05
    font = _font(_mm(size_mm), bold=True)
    while draw.textbbox((0, 0), timing_text, font=font)[2] > max_width and size_mm > 1.1:
        size_mm = max(1.1, size_mm - 0.1)
        font = _font(_mm(size_mm), bold=True)
    return font


def _art_panel_for(deck: CharacterDeckSpec, source_id: str) -> CardArtPanel:
    if source_id in CONTROL_ART:
        return CONTROL_ART[source_id]
    if deck.actor_id in CURATED_ACTION_CARDS:
        source_ids = tuple(
            card.source_id
            for card in deck.action_cards
            if card.source_id not in {"accept", "decline"}
        )
        try:
            panel_index = source_ids.index(source_id)
        except ValueError:
            if source_id == "_deck_back":
                panel_index = len(source_ids)
            elif source_id == "_passive_back":
                panel_index = len(source_ids) + 1
            else:
                raise KeyError(source_id) from None
        return CardArtPanel(
            f"archetype_{deck.actor_id}_cards_v1.png",
            panel_index,
            columns=4,
            rows=6,
        )
    if deck.actor_id == "garran":
        assignments = GARRAN_ART
    elif deck.actor_id == "dagna":
        assignments = DAGNA_ART
    else:
        assignments = ADDITIONAL_ART[deck.actor_id]
    return assignments[source_id]


def _extract_art_panel(panel: CardArtPanel) -> Image.Image:
    path = CHARACTER_SET_ART_ROOT / panel.asset
    with Image.open(path) as source:
        source = source.convert("RGB")
        cell_width = source.width / panel.columns
        cell_height = source.height / panel.rows
        column = panel.panel_index % panel.columns
        row = panel.panel_index // panel.columns
        # Trim a few source pixels so the generated black grid gutter never
        # becomes part of the card illustration.
        inset = max(3, round(min(cell_width, cell_height) * 0.012))
        left = round(column * cell_width) + inset
        top = round(row * cell_height) + inset
        right = round((column + 1) * cell_width) - inset
        bottom = round((row + 1) * cell_height) - inset
        return source.crop((left, top, right, bottom))


def _card_canvas_with_art(
    deck: CharacterDeckSpec,
    source_id: str,
    *,
    art_bottom: int,
) -> Image.Image:
    image = Image.new("RGB", CARD_ART_SIZE_PX, (4, 7, 9))
    panel = _extract_art_panel(_art_panel_for(deck, source_id))
    art = ImageOps.fit(
        panel,
        (CARD_ART_SIZE_PX[0], art_bottom),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    panel.close()
    image.paste(art, (0, 0))
    art.close()
    return image


def render_character_action_card(
    deck: CharacterDeckSpec,
    spec: CharacterActionCardSpec,
) -> Image.Image:
    width, height = CARD_ART_SIZE_PX
    trim_left = BLEED_PX
    trim_top = BLEED_PX
    trim_right = trim_left + CARD_SIZE_PX[0] - 1
    trim_bottom = trim_top + CARD_SIZE_PX[1] - 1
    safe = _mm(SAFE_MARGIN_MM)
    panel_top = trim_top + _mm(48)
    image = _card_canvas_with_art(deck, spec.source_id, art_bottom=panel_top + _mm(2))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, panel_top, width, height), fill=(4, 7, 9, 248))
    draw.rectangle(
        (trim_left, trim_top, trim_right, trim_bottom),
        outline=(*deck.accent, 255),
        width=_mm(0.7),
    )
    draw.rectangle(
        (trim_left + _mm(2), trim_top + _mm(2), trim_right - _mm(2), trim_bottom - _mm(2)),
        outline=(*deck.secondary, 145),
        width=max(1, _mm(0.25)),
    )

    # Universal confirmation cards intentionally contain only the command and QR.
    if spec.source_id in {"accept", "decline"}:
        veil = (14, 54, 37, 178) if spec.source_id == "accept" else (66, 12, 16, 184)
        draw.rectangle((0, panel_top - _mm(10), width, height), fill=veil)
        title_font = _fit_title_font(draw, spec.title, CARD_SIZE_PX[0] - 2 * safe)
        draw.text(
            (width // 2, panel_top + _mm(8)),
            spec.title,
            font=title_font,
            fill=(250, 241, 220),
            anchor="ma",
            stroke_width=max(1, _mm(0.2)),
            stroke_fill=(3, 5, 7),
        )
        qr = _qr_image(spec.payload_for(deck.actor_id), _mm(15))
        image.paste(
            qr,
            (
                trim_right - safe - qr.width,
                trim_bottom - safe - qr.height,
            ),
        )
        qr.close()
        return image

    title_font = _fit_title_font(draw, spec.title, CARD_SIZE_PX[0] - 2 * safe)
    draw.text(
        (width // 2, panel_top + _mm(1.2)),
        spec.title,
        font=title_font,
        fill=(248, 239, 218),
        anchor="ma",
        stroke_width=max(1, _mm(0.12)),
        stroke_fill=(4, 6, 8),
    )
    level_text = f"POZIOM {spec.required_level}"
    draw.rounded_rectangle(
        (trim_left + safe, panel_top + _mm(8), trim_right - safe, panel_top + _mm(13.5)),
        radius=_mm(1.2),
        fill=(*spec.accent, 46),
        outline=(*spec.accent, 190),
        width=max(1, _mm(0.2)),
    )
    level_font = _font(_mm(1.95), bold=True)
    level_width = draw.textbbox((0, 0), level_text, font=level_font)[2]
    timing_text = " · ".join(filter(None, (_phase_label(spec), spec.timing)))
    timing_room = CARD_SIZE_PX[0] - 2 * safe - level_width - _mm(8)
    timing_font = _fit_timing_font(draw, timing_text, timing_room)
    draw.text(
        (trim_left + safe + _mm(2), panel_top + _mm(9.1)),
        timing_text,
        font=timing_font,
        fill=spec.accent,
    )
    draw.text(
        (trim_right - safe - _mm(2), panel_top + _mm(9.1)),
        level_text,
        font=level_font,
        fill=(222, 215, 200),
        anchor="ra",
    )
    mechanic_top = panel_top + _mm(16)
    flavor_top = trim_bottom - safe - _mm(8.5)
    mechanic_width = CARD_SIZE_PX[0] - 2 * safe - _mm(3)
    mechanic_lines: list[str] = []
    mechanic_font = _font(_mm(1.82))
    for font_size_mm in (1.82, 1.65, 1.5, 1.35, 1.2):
        candidate_font = _font(_mm(font_size_mm))
        candidate_lines = _wrapped_lines(
            draw,
            spec.mechanic,
            candidate_font,
            mechanic_width,
        )
        candidate_text = "\n".join(candidate_lines)
        text_height = draw.multiline_textbbox(
            (0, 0),
            candidate_text,
            font=candidate_font,
            spacing=_mm(0.3),
        )[3]
        mechanic_font = candidate_font
        mechanic_lines = candidate_lines
        if text_height <= flavor_top - mechanic_top - _mm(1.5):
            break
    draw.multiline_text(
        (trim_left + safe + _mm(1.5), mechanic_top),
        "\n".join(mechanic_lines),
        font=mechanic_font,
        fill=(224, 221, 211),
        spacing=_mm(0.3),
    )
    qr = _qr_image(spec.payload_for(deck.actor_id), _mm(14.5))
    qr_left = trim_right - safe - qr.width
    qr_top = panel_top - qr.height - _mm(2)
    image.paste(qr, (qr_left, qr_top))
    flavor_font = _font(_mm(1.55), serif=True)
    flavor_lines = _wrapped_lines(
        draw,
        spec.flavor,
        flavor_font,
        CARD_SIZE_PX[0] - 2 * safe - _mm(3),
        max_lines=3,
    )
    draw.multiline_text(
        (trim_left + safe + _mm(1), flavor_top),
        "\n".join(flavor_lines),
        font=flavor_font,
        fill=(190, 174, 147),
        spacing=_mm(0.35),
    )
    human_code = f"{deck.actor_id[:2].upper()}-{spec.source_id[:8].upper()}"
    draw.text(
        (trim_left + safe + _mm(1), trim_bottom - safe - _mm(1.8)),
        human_code,
        font=_font(_mm(1.35), bold=True),
        fill=deck.secondary,
    )
    qr.close()
    return image


def render_character_card_back(deck: CharacterDeckSpec) -> Image.Image:
    background = _card_canvas_with_art(deck, "_deck_back", art_bottom=CARD_ART_SIZE_PX[1])
    background = background.filter(ImageFilter.GaussianBlur(radius=_mm(0.12)))
    draw = ImageDraw.Draw(background, "RGBA")
    width, height = CARD_ART_SIZE_PX
    trim_left = BLEED_PX
    trim_top = BLEED_PX
    trim_right = trim_left + CARD_SIZE_PX[0] - 1
    trim_bottom = trim_top + CARD_SIZE_PX[1] - 1
    draw.rectangle((0, 0, width, height), fill=(3, 5, 7, 112))
    draw.rectangle((trim_left, trim_top, trim_right, trim_bottom), outline=deck.accent, width=_mm(0.7))
    draw.rectangle(
        (trim_left + _mm(3), trim_top + _mm(3), trim_right - _mm(3), trim_bottom - _mm(3)),
        outline=(*deck.secondary, 165),
        width=_mm(0.25),
    )
    center_x = width // 2
    draw.text(
        (center_x, trim_top + _mm(9)),
        deck.deck_title,
        font=_font(_mm(3.1), serif=True, bold=True),
        fill=(239, 228, 207),
        anchor="ma",
    )
    draw.text(
        (center_x, trim_bottom - _mm(9)),
        "TALIA BOHATERA",
        font=_font(_mm(2.6), bold=True),
        fill=deck.accent,
        anchor="ma",
    )
    return background


def render_character_hero_back(deck: CharacterDeckSpec) -> Image.Image:
    """Render the hero-card reverse with passive rules instead of an action."""
    passive_source = "_passive_back" if deck.actor_id == "dagna" else "_deck_back"
    image = _card_canvas_with_art(deck, passive_source, art_bottom=CARD_ART_SIZE_PX[1])
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = CARD_ART_SIZE_PX
    trim_left = BLEED_PX
    trim_top = BLEED_PX
    trim_right = trim_left + CARD_SIZE_PX[0] - 1
    trim_bottom = trim_top + CARD_SIZE_PX[1] - 1
    safe = _mm(SAFE_MARGIN_MM)
    draw.rectangle(
        (trim_left + _mm(3), trim_top + _mm(3), trim_right - _mm(3), trim_bottom - _mm(3)),
        fill=(4, 7, 9, 232),
        outline=(*deck.secondary, 170),
        width=_mm(0.25),
    )
    draw.text(
        (width // 2, trim_top + _mm(7)),
        f"{deck.profile.helper_code} · ZASADY PASYWNE",
        font=_font(_mm(3.0), serif=True, bold=True),
        fill=(241, 230, 207),
        anchor="ma",
    )
    draw.line(
        (trim_left + safe, trim_top + _mm(14), trim_right - safe, trim_top + _mm(14)),
        fill=(*deck.accent, 210),
        width=_mm(0.3),
    )
    passive_font = _font(_mm(2.05))
    y = trim_top + _mm(18)
    for passive in deck.passives:
        lines = _wrapped_lines(
            draw,
            passive,
            passive_font,
            CARD_SIZE_PX[0] - 2 * safe - _mm(4),
            max_lines=4,
        )
        draw.ellipse(
            (trim_left + safe, y + _mm(1), trim_left + safe + _mm(1.4), y + _mm(2.4)),
            fill=deck.accent,
        )
        draw.multiline_text(
            (trim_left + safe + _mm(3), y),
            "\n".join(lines),
            font=passive_font,
            fill=(222, 218, 205),
            spacing=_mm(0.45),
        )
        y += len(lines) * _mm(2.8) + _mm(2.0)
    draw.text(
        (width // 2, trim_bottom - _mm(9)),
        "Szczegóły rozwoju znajdują się w dossier.",
        font=_font(_mm(1.85), serif=True),
        fill=deck.accent,
        anchor="ma",
    )
    return image


def _sheet_positions() -> tuple[tuple[int, int], ...]:
    horizontal_gap = _mm(10)
    vertical_gap = _mm(12)
    total_width = 2 * CARD_ART_SIZE_PX[0] + horizontal_gap
    total_height = 2 * CARD_ART_SIZE_PX[1] + vertical_gap
    start_x = (A4_SIZE_PX[0] - total_width) // 2
    start_y = (A4_SIZE_PX[1] - total_height) // 2
    return (
        (start_x, start_y),
        (start_x + CARD_ART_SIZE_PX[0] + horizontal_gap, start_y),
        (start_x, start_y + CARD_ART_SIZE_PX[1] + vertical_gap),
        (start_x + CARD_ART_SIZE_PX[0] + horizontal_gap, start_y + CARD_ART_SIZE_PX[1] + vertical_gap),
    )


def _render_sheet(
    cards: tuple[Image.Image, ...],
    *,
    backs: bool,
    sheet_number: int,
) -> Image.Image:
    sheet = Image.new("RGB", A4_SIZE_PX, "white")
    draw = ImageDraw.Draw(sheet)
    positions = _sheet_positions()[: len(cards)]
    if backs:
        positions = tuple(
            (A4_SIZE_PX[0] - left - CARD_ART_SIZE_PX[0], top)
            for left, top in positions
        )
    for card, (left, top) in zip(cards, positions, strict=True):
        sheet.paste(card, (left, top))
        _draw_crop_marks(draw, left, top)
    label = (
        f"ARKUSZ {sheet_number} · REWERSY · odwróć po długiej krawędzi"
        if backs
        else f"ARKUSZ {sheet_number} · PRZODY"
    )
    draw.text((_mm(10), _mm(7)), label, font=_font(_mm(3), bold=True), fill=(25, 25, 25))
    draw.text(
        (_mm(10), A4_SIZE_PX[1] - _mm(10)),
        "Druk 100% · bez dopasowania · po cięciu 63 × 88 mm · spad 3 mm",
        font=_font(_mm(2.2)),
        fill=(45, 45, 45),
    )
    return sheet


def _draw_section(
    draw: ImageDraw.ImageDraw,
    *,
    left: int,
    top: int,
    width: int,
    title: str,
    text: str,
    accent: tuple[int, int, int],
    font_size_mm: float = 3.0,
) -> int:
    draw.text((left, top), title.upper(), font=_font(_mm(3.25), serif=True, bold=True), fill=accent)
    rule_y = top + _mm(5)
    draw.line((left, rule_y, left + width, rule_y), fill=(*accent, 180), width=_mm(0.25))
    body_font = _font(_mm(font_size_mm))
    lines = _wrapped_lines(draw, text, body_font, width)
    body_top = rule_y + _mm(3)
    draw.multiline_text(
        (left, body_top),
        "\n".join(lines),
        font=body_font,
        fill=(224, 220, 207),
        spacing=_mm(1.0),
    )
    line_height = _mm(font_size_mm + 1.0)
    return body_top + line_height * len(lines) + _mm(5)


def render_character_dossier(deck: CharacterDeckSpec) -> Image.Image:
    page = Image.new("RGB", A4_SIZE_PX, (11, 14, 16))
    portrait_path = HERO_PORTRAIT_ROOT / f"{deck.actor_id}.png"
    with Image.open(portrait_path) as source:
        hero = ImageOps.fit(
            source.convert("RGB"),
            (A4_SIZE_PX[0], _mm(104)),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.2),
        )
    page.paste(hero, (0, 0))
    hero.close()
    draw = ImageDraw.Draw(page, "RGBA")
    draw.rectangle((0, 0, A4_SIZE_PX[0], _mm(104)), fill=(4, 6, 8, 35))
    draw.rectangle((0, _mm(67), A4_SIZE_PX[0], _mm(112)), fill=(5, 7, 9, 235))
    margin = _mm(14)
    draw.text(
        (margin, _mm(75)),
        deck.deck_title,
        font=_font(_mm(8.2), serif=True, bold=True),
        fill=(246, 235, 214),
    )
    draw.text(
        (margin, _mm(88)),
        deck.subtitle,
        font=_font(_mm(3.6), bold=True),
        fill=deck.accent,
    )
    draw.text(
        (margin, _mm(96)),
        f"„{deck.profile.tagline}”",
        font=_font(_mm(3.0), serif=True),
        fill=(205, 194, 174),
    )
    column_gap = _mm(10)
    column_width = (A4_SIZE_PX[0] - 2 * margin - column_gap) // 2
    left_x = margin
    right_x = margin + column_width + column_gap
    left_top = _mm(119)
    left_top = _draw_section(
        draw,
        left=left_x,
        top=left_top,
        width=column_width,
        title="Kim jest",
        text=deck.dossier_intro,
        accent=deck.accent,
        font_size_mm=2.75,
    )
    left_top = _draw_section(
        draw,
        left=left_x,
        top=left_top,
        width=column_width,
        title="Po co rusza w drogę",
        text=deck.dossier_campaign,
        accent=deck.accent,
        font_size_mm=2.65,
    )
    left_top = _draw_section(
        draw,
        left=left_x,
        top=left_top,
        width=column_width,
        title="Przy stole",
        text="\n".join(f"• {entry}" for entry in deck.profile.turn_plan),
        accent=deck.accent,
        font_size_mm=2.45,
    )
    right_top = _mm(119)
    right_top = _draw_section(
        draw,
        left=right_x,
        top=right_top,
        width=column_width,
        title="Zasady pasywne",
        text="\n".join(f"• {entry}" for entry in deck.passives),
        accent=deck.secondary,
        font_size_mm=2.55,
    )
    right_top = _draw_section(
        draw,
        left=right_x,
        top=right_top,
        width=column_width,
        title="Mocne strony i ryzyka",
        text=(
            f"Mocne: {', '.join(deck.profile.strengths)}.\n"
            f"Uważaj: {', '.join(deck.profile.pitfalls)}."
        ),
        accent=deck.secondary,
        font_size_mm=2.45,
    )
    right_top = _draw_section(
        draw,
        left=right_x,
        top=right_top,
        width=column_width,
        title="Rozwój 1–3",
        text="\n".join(f"• {entry}" for entry in deck.progression),
        accent=deck.secondary,
        font_size_mm=2.55,
    )
    draw.rounded_rectangle(
        (margin, _mm(268), A4_SIZE_PX[0] - margin, _mm(283)),
        radius=_mm(2),
        fill=(*deck.accent, 35),
        outline=(*deck.accent, 180),
        width=_mm(0.3),
    )
    draw.text(
        (A4_SIZE_PX[0] // 2, _mm(273)),
        "Nie wybraniec przepowiedni. Człowiek wplątany w historię, który próbuje ocalić to, co jest obok.",
        font=_font(_mm(2.65), serif=True),
        fill=(229, 218, 198),
        anchor="ma",
    )
    return page


@lru_cache(maxsize=1)
def _starter_builds():
    catalog = load_character_catalog(PROJECT_ROOT / "content" / "character_creation" / "catalog.json")
    resources = load_character_resources(catalog, PROJECT_ROOT / "content")
    builds = {
        draft.id: (
            draft,
            replace(
                build_character(draft, catalog, resources),
                actor=apply_boardgame_archetype(
                    build_character(draft, catalog, resources).actor,
                    spell_definitions=tuple(spell for _, spell in resources.spells),
                ),
            ),
        )
        for draft in default_character_drafts()
    }
    return catalog, builds


_SKILL_ABILITIES = {
    "acrobatics": "dexterity",
    "animal_handling": "wisdom",
    "arcana": "intelligence",
    "athletics": "strength",
    "deception": "charisma",
    "history": "intelligence",
    "insight": "wisdom",
    "intimidation": "charisma",
    "investigation": "intelligence",
    "medicine": "wisdom",
    "nature": "intelligence",
    "perception": "wisdom",
    "performance": "charisma",
    "persuasion": "charisma",
    "religion": "intelligence",
    "sleight_of_hand": "dexterity",
    "stealth": "dexterity",
    "survival": "wisdom",
}


def _signed(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


def _stat_lines(deck: CharacterDeckSpec) -> dict[str, str]:
    catalog, builds = _starter_builds()
    draft, created = builds[deck.actor_id]
    actor = created.actor
    character_class = catalog.class_by_id(created.class_id)
    species = catalog.species_by_id(created.species_id)
    background = catalog.background_by_id(created.background_id)
    assert character_class is not None and species is not None and background is not None
    scores = actor.ability_scores
    saves = []
    for ability_id in ABILITY_IDS:
        modifier = ability_modifier(getattr(scores, ability_id))
        if ability_id in actor.proficiencies.saving_throws:
            modifier += actor.proficiency_bonus
        marker = "●" if ability_id in actor.proficiencies.saving_throws else "○"
        saves.append(f"{marker} {ABILITY_LABELS_PL[ability_id]} {_signed(modifier)}")
    skills = []
    for skill_id in sorted(actor.proficiencies.skills, key=lambda item: SKILL_LABELS_PL.get(item, item)):
        ability_id = _SKILL_ABILITIES[skill_id]
        multiplier = 2 if skill_id in actor.proficiencies.expertise else 1
        value = ability_modifier(getattr(scores, ability_id)) + actor.proficiency_bonus * multiplier
        marker = "◆" if multiplier == 2 else "●"
        skills.append(f"{marker} {SKILL_LABELS_PL.get(skill_id, skill_id)} {_signed(value)}")
    equipment = []
    for item in actor.inventory:
        quantity = f" ×{item.quantity}" if item.quantity > 1 else ""
        equipped = " [założone]" if item.equipped else ""
        equipment.append(f"• {item.name}{quantity}{equipped}")
    tools = ", ".join(
        TOOL_LABELS_PL.get(tool_id, tool_id.replace("_", " "))
        for tool_id in actor.proficiencies.tools
    ) or "brak"
    known = tuple(dict.fromkeys((
        *draft.selected_cantrip_ids,
        *draft.selected_species_cantrip_ids,
        *draft.selected_spell_ids,
    )))
    prepared = tuple(dict.fromkeys(draft.selected_prepared_spell_ids))
    spell_lines = []
    if known:
        spell_lines.append(
            "Znane / księga: "
            + ", ".join(SPELL_NAMES_PL.get(spell_id, spell_id) for spell_id in known)
        )
    if prepared:
        spell_lines.append(
            "Przygotowane: "
            + ", ".join(SPELL_NAMES_PL.get(spell_id, spell_id) for spell_id in prepared)
        )
    if actor.spell_slots:
        spell_lines.append(
            "Komórki: "
            + ", ".join(f"{slot.level}. poziom — {slot.maximum}" for slot in actor.spell_slots)
        )
    if actor.spell_save_dc:
        spell_attack = actor.spell_save_dc - 8
        spell_lines.append(f"ST czarów {actor.spell_save_dc}; atak czarem {_signed(spell_attack)}")
    if not spell_lines:
        spell_lines.append("Brak czarów na 1. poziomie.")
    return {
        "identity": f"{species.name} · {character_class.name} · {background.name}",
        "combat": (
            f"Poziom 1  |  PB +{actor.proficiency_bonus}  |  PW {actor.max_hp}/{actor.max_hp}  |  "
            f"KP {effective_armor_class(actor)}  |  Inicjatywa {_signed(ability_modifier(scores.dexterity))}  |  "
            f"Szybkość {effective_speed_feet(actor)} stóp  |  Kość Wytrzymałości k{character_class.hit_die}"
        ),
        "saves": "\n".join(saves),
        "skills": "\n".join(skills),
        "equipment": "\n".join(equipment),
        "tools": tools,
        "spells": "\n".join(spell_lines),
        "gold": f"Startowe monety: {actor.currency.gp} sz.",
    }


def render_character_statistics(deck: CharacterDeckSpec) -> Image.Image:
    """Render the values a player copies to the maintained paper character sheet."""
    page = Image.new("RGB", A4_SIZE_PX, (12, 15, 18))
    draw = ImageDraw.Draw(page, "RGBA")
    margin = _mm(13)
    width = A4_SIZE_PX[0] - 2 * margin
    draw.rectangle((0, 0, A4_SIZE_PX[0], _mm(42)), fill=(*deck.accent, 48))
    draw.line((margin, _mm(39), A4_SIZE_PX[0] - margin, _mm(39)), fill=deck.accent, width=_mm(0.5))
    draw.text(
        (margin, _mm(11)),
        f"{deck.profile.actor_id.upper()} · ARKUSZ STARTOWY",
        font=_font(_mm(7), serif=True, bold=True),
        fill=(245, 234, 214),
    )
    stats = _stat_lines(deck)
    draw.text((margin, _mm(25)), stats["identity"], font=_font(_mm(3.2), bold=True), fill=deck.secondary)
    draw.text((margin, _mm(32)), stats["combat"], font=_font(_mm(2.65)), fill=(223, 219, 207))

    _, builds = _starter_builds()
    actor = builds[deck.actor_id][1].actor
    box_gap = _mm(3)
    box_width = (width - 5 * box_gap) // 6
    y = _mm(48)
    for index, ability_id in enumerate(ABILITY_IDS):
        left = margin + index * (box_width + box_gap)
        score = getattr(actor.ability_scores, ability_id)
        modifier = ability_modifier(score)
        draw.rounded_rectangle(
            (left, y, left + box_width, y + _mm(29)),
            radius=_mm(2),
            fill=(24, 29, 33, 255),
            outline=(*deck.accent, 210),
            width=_mm(0.35),
        )
        draw.text(
            (left + box_width // 2, y + _mm(4)),
            ABILITY_LABELS_PL[ability_id].upper(),
            font=_font(_mm(2.0), bold=True),
            fill=deck.secondary,
            anchor="ma",
        )
        draw.text(
            (left + box_width // 2, y + _mm(11)),
            str(score),
            font=_font(_mm(6.5), serif=True, bold=True),
            fill=(244, 235, 217),
            anchor="ma",
        )
        draw.text(
            (left + box_width // 2, y + _mm(22)),
            _signed(modifier),
            font=_font(_mm(3.2), bold=True),
            fill=deck.accent,
            anchor="ma",
        )

    column_gap = _mm(10)
    column_width = (width - column_gap) // 2
    left_x = margin
    right_x = margin + column_width + column_gap
    left_top = _mm(84)
    left_top = _draw_section(draw, left=left_x, top=left_top, width=column_width, title="Rzuty obronne", text=stats["saves"], accent=deck.accent, font_size_mm=2.55)
    left_top = _draw_section(draw, left=left_x, top=left_top, width=column_width, title="Biegłe umiejętności", text=stats["skills"], accent=deck.accent, font_size_mm=2.35)
    left_top = _draw_section(draw, left=left_x, top=left_top, width=column_width, title="Narzędzia", text=stats["tools"], accent=deck.accent, font_size_mm=2.35)
    right_top = _mm(84)
    right_top = _draw_section(draw, left=right_x, top=right_top, width=column_width, title="Ekwipunek startowy", text=stats["equipment"], accent=deck.secondary, font_size_mm=2.15)
    right_top = _draw_section(draw, left=right_x, top=right_top, width=column_width, title="Magia na start", text=stats["spells"], accent=deck.secondary, font_size_mm=2.2)
    _draw_section(draw, left=right_x, top=right_top, width=column_width, title="Majątek", text=stats["gold"], accent=deck.secondary, font_size_mm=2.35)

    draw.rounded_rectangle(
        (margin, _mm(267), A4_SIZE_PX[0] - margin, _mm(284)),
        radius=_mm(2),
        fill=(*deck.accent, 30),
        outline=(*deck.accent, 180),
        width=_mm(0.3),
    )
    draw.text(
        (A4_SIZE_PX[0] // 2, _mm(272)),
        "Przepisz te wartości na kartę postaci. Po awansie aktualizuj poziom, PW, zasoby, czary i wybrane zdolności.",
        font=_font(_mm(2.55), serif=True),
        fill=(229, 219, 201),
        anchor="ma",
    )
    return page


def _draw_bw_field(
    draw: ImageDraw.ImageDraw,
    bounds: tuple[int, int, int, int],
    label: str,
    value: str,
    *,
    value_size_mm: float = 4.6,
) -> None:
    left, top, right, bottom = bounds
    draw.rounded_rectangle(
        bounds,
        radius=_mm(1.5),
        fill="white",
        outline="black",
        width=max(1, _mm(0.25)),
    )
    draw.text(
        ((left + right) // 2, top + _mm(2.2)),
        label.upper(),
        font=_font(_mm(1.8), bold=True),
        fill="black",
        anchor="ma",
    )
    draw.text(
        ((left + right) // 2, top + (bottom - top) // 2 + _mm(1.5)),
        value,
        font=_font(_mm(value_size_mm), serif=True, bold=True),
        fill="black",
        anchor="mm",
    )


def _draw_bw_section(
    draw: ImageDraw.ImageDraw,
    bounds: tuple[int, int, int, int],
    title: str,
    text: str,
    *,
    font_size_mm: float = 2.25,
) -> None:
    left, top, right, bottom = bounds
    draw.rounded_rectangle(
        bounds,
        radius=_mm(1.5),
        fill="white",
        outline="black",
        width=max(1, _mm(0.25)),
    )
    draw.text(
        (left + _mm(3), top + _mm(2.2)),
        title.upper(),
        font=_font(_mm(2.2), bold=True),
        fill="black",
    )
    rule_y = top + _mm(7)
    draw.line((left, rule_y, right, rule_y), fill="black", width=max(1, _mm(0.2)))
    font = _font(_mm(font_size_mm))
    max_width = right - left - _mm(6)
    max_lines = max(1, (bottom - rule_y - _mm(4)) // _mm(font_size_mm + 0.9))
    lines = _wrapped_lines(draw, text, font, max_width, max_lines=max_lines)
    draw.multiline_text(
        (left + _mm(3), rule_y + _mm(2)),
        "\n".join(lines),
        font=font,
        fill="black",
        spacing=_mm(0.55),
    )


def render_character_sheet_bw(deck: CharacterDeckSpec) -> Image.Image:
    """Render a low-coverage A4 character sheet for ordinary black toner."""
    page = Image.new("RGB", A4_SIZE_PX, "white")
    draw = ImageDraw.Draw(page)
    margin = _mm(11)
    usable_width = A4_SIZE_PX[0] - 2 * margin
    stats = _stat_lines(deck)
    catalog, builds = _starter_builds()
    _draft, created = builds[deck.actor_id]
    actor = created.actor
    character_class = catalog.class_by_id(created.class_id)
    assert character_class is not None

    draw.text(
        (margin, _mm(10)),
        deck.profile.actor_id.upper(),
        font=_font(_mm(7), serif=True, bold=True),
        fill="black",
    )
    draw.text(
        (margin, _mm(20)),
        stats["identity"],
        font=_font(_mm(2.8), bold=True),
        fill="black",
    )
    draw.text(
        (A4_SIZE_PX[0] - margin, _mm(11)),
        "KARTA POSTACI · A4 · DRUK CZARNO-BIAŁY",
        font=_font(_mm(2.1), bold=True),
        fill="black",
        anchor="ra",
    )
    draw.text(
        (A4_SIZE_PX[0] - margin, _mm(20)),
        "Gracz: ____________________   PD: __________",
        font=_font(_mm(2.3)),
        fill="black",
        anchor="ra",
    )
    draw.line(
        (margin, _mm(27), A4_SIZE_PX[0] - margin, _mm(27)),
        fill="black",
        width=max(1, _mm(0.4)),
    )

    combat_values = (
        ("Poziom", str(actor.level)),
        ("Premia z biegłości", f"+{actor.proficiency_bonus}"),
        ("KP", str(effective_armor_class(actor))),
        ("Maks. PW", str(actor.max_hp)),
        ("Szybkość", f"{effective_speed_feet(actor)} st."),
        ("Kość Wytrzymałości", f"k{character_class.hit_die}"),
    )
    gap = _mm(2.5)
    box_width = (usable_width - gap * 5) // 6
    for index, (label, value) in enumerate(combat_values):
        left = margin + index * (box_width + gap)
        _draw_bw_field(
            draw,
            (left, _mm(32), left + box_width, _mm(55)),
            label,
            value,
            value_size_mm=3.7 if index in {1, 4, 5} else 5.0,
        )

    ability_gap = _mm(2.5)
    ability_width = (usable_width - ability_gap * 5) // 6
    for index, ability_id in enumerate(ABILITY_IDS):
        left = margin + index * (ability_width + ability_gap)
        score = getattr(actor.ability_scores, ability_id)
        _draw_bw_field(
            draw,
            (left, _mm(59), left + ability_width, _mm(85)),
            ABILITY_LABELS_PL[ability_id],
            f"{score}  ({_signed(ability_modifier(score))})",
            value_size_mm=3.8,
        )

    column_gap = _mm(5)
    column_width = (usable_width - column_gap) // 2
    left = margin
    right = margin + column_width + column_gap
    _draw_bw_section(
        draw,
        (left, _mm(90), left + column_width, _mm(143)),
        "Rzuty obronne",
        stats["saves"],
        font_size_mm=2.25,
    )
    _draw_bw_section(
        draw,
        (left, _mm(147), left + column_width, _mm(214)),
        "Biegłe umiejętności i narzędzia",
        f"{stats['skills']}\n\nNarzędzia: {stats['tools']}",
        font_size_mm=2.1,
    )
    _draw_bw_section(
        draw,
        (right, _mm(90), right + column_width, _mm(164)),
        "Ekwipunek startowy",
        f"{stats['equipment']}\n{stats['gold']}",
        font_size_mm=1.95,
    )
    _draw_bw_section(
        draw,
        (right, _mm(168), right + column_width, _mm(214)),
        "Magia i zasoby",
        stats["spells"],
        font_size_mm=1.95,
    )

    _draw_bw_section(
        draw,
        (margin, _mm(219), A4_SIZE_PX[0] - margin, _mm(252)),
        "Stan bieżący",
        (
            "Aktualne PW: __________ / __________    Tymczasowe PW: __________    "
            "Inicjatywa: __________\n"
            "Rzuty śmierci — sukcesy: ○ ○ ○    porażki: ○ ○ ○    "
            "Wykorzystane Kości Wytrzymałości: __________\n"
            "Wyczerpanie:  ○ 0    ○ 1    ○ 2    ○ 3    ○ 4    ○ 5    ○ 6\n"
            "Warunki / aktywne efekty: ________________________________________________"
        ),
        font_size_mm=2.1,
    )
    _draw_bw_section(
        draw,
        (margin, _mm(257), A4_SIZE_PX[0] - margin, _mm(286)),
        "Notatki, rozwój i zmiany ekwipunku",
        "\n\n\n",
        font_size_mm=2.2,
    )
    draw.text(
        (A4_SIZE_PX[0] // 2, A4_SIZE_PX[1] - _mm(6)),
        "Drukuj w skali 100% · tryb monochromatyczny · bez tła · margines drukarki co najmniej 5 mm",
        font=_font(_mm(1.8)),
        fill="black",
        anchor="ms",
    )
    return page


def render_character_dossier_bw(deck: CharacterDeckSpec) -> Image.Image:
    """Render the narrative/rules dossier without large toner-heavy backgrounds."""
    page = Image.new("RGB", A4_SIZE_PX, "white")
    draw = ImageDraw.Draw(page)
    margin = _mm(11)
    gap = _mm(5)
    column_width = (A4_SIZE_PX[0] - 2 * margin - gap) // 2
    right = margin + column_width + gap

    draw.text(
        (margin, _mm(10)),
        deck.deck_title,
        font=_font(_mm(6.2), serif=True, bold=True),
        fill="black",
    )
    draw.text(
        (margin, _mm(20)),
        deck.subtitle,
        font=_font(_mm(2.7), bold=True),
        fill="black",
    )
    draw.text(
        (A4_SIZE_PX[0] - margin, _mm(11)),
        "DOSSIER · DRUK CZARNYM TONEREM",
        font=_font(_mm(2.0), bold=True),
        fill="black",
        anchor="ra",
    )
    draw.text(
        (margin, _mm(27)),
        f"„{deck.profile.tagline}”",
        font=_font(_mm(2.45), serif=True),
        fill="black",
    )
    draw.line(
        (margin, _mm(34), A4_SIZE_PX[0] - margin, _mm(34)),
        fill="black",
        width=max(1, _mm(0.35)),
    )

    _draw_bw_section(
        draw,
        (margin, _mm(40), margin + column_width, _mm(104)),
        "Kim jest",
        deck.dossier_intro,
        font_size_mm=2.15,
    )
    _draw_bw_section(
        draw,
        (right, _mm(40), right + column_width, _mm(104)),
        "Po co rusza w drogę",
        deck.dossier_campaign,
        font_size_mm=2.05,
    )
    _draw_bw_section(
        draw,
        (margin, _mm(110), margin + column_width, _mm(176)),
        "Jak prowadzić bohatera",
        "\n".join(f"• {entry}" for entry in deck.profile.turn_plan),
        font_size_mm=2.05,
    )
    _draw_bw_section(
        draw,
        (right, _mm(110), right + column_width, _mm(176)),
        "Zasady pasywne i skaza",
        "\n".join(f"• {entry}" for entry in deck.passives),
        font_size_mm=1.82,
    )
    _draw_bw_section(
        draw,
        (margin, _mm(182), margin + column_width, _mm(258)),
        "Rozwój poziomy 1–3",
        "\n".join(f"• {entry}" for entry in deck.progression),
        font_size_mm=2.0,
    )
    _draw_bw_section(
        draw,
        (right, _mm(182), right + column_width, _mm(258)),
        "Mocne strony i ryzyka",
        (
            f"Mocne strony: {', '.join(deck.profile.strengths)}.\n\n"
            f"Uważaj na: {', '.join(deck.profile.pitfalls)}."
        ),
        font_size_mm=2.1,
    )
    draw.text(
        (A4_SIZE_PX[0] // 2, _mm(271)),
        "Opis, statystyki i talia tworzą jeden aktualny zestaw bohatera.",
        font=_font(_mm(2.25), serif=True),
        fill="black",
        anchor="ma",
    )
    return page


def _bw_test_card_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", CARD_ART_SIZE_PX, "white")
    draw = ImageDraw.Draw(image)
    trim_left = BLEED_PX
    trim_top = BLEED_PX
    trim_right = trim_left + CARD_SIZE_PX[0] - 1
    trim_bottom = trim_top + CARD_SIZE_PX[1] - 1
    draw.rounded_rectangle(
        (trim_left, trim_top, trim_right, trim_bottom),
        radius=_mm(1.5),
        fill="white",
        outline="black",
        width=max(1, _mm(0.35)),
    )
    draw.rounded_rectangle(
        (
            trim_left + _mm(2),
            trim_top + _mm(2),
            trim_right - _mm(2),
            trim_bottom - _mm(2),
        ),
        radius=_mm(1),
        outline="black",
        width=max(1, _mm(0.15)),
    )
    return image, draw


def render_character_action_card_bw_test(
    deck: CharacterDeckSpec,
    spec: CharacterActionCardSpec,
) -> Image.Image:
    """Render an illustration-free, low-toner action-card front for playtests."""
    image, draw = _bw_test_card_canvas()
    trim_left = BLEED_PX
    trim_top = BLEED_PX
    trim_right = trim_left + CARD_SIZE_PX[0] - 1
    trim_bottom = trim_top + CARD_SIZE_PX[1] - 1
    safe = _mm(SAFE_MARGIN_MM)
    content_left = trim_left + safe
    content_right = trim_right - safe

    if spec.source_id in {"accept", "decline"}:
        draw.text(
            ((trim_left + trim_right) // 2, trim_top + _mm(23)),
            spec.title,
            font=_fit_title_font(draw, spec.title, CARD_SIZE_PX[0] - 2 * safe),
            fill="black",
            anchor="ma",
        )
        draw.text(
            ((trim_left + trim_right) // 2, trim_top + _mm(35)),
            "KARTA KONTROLNA",
            font=_font(_mm(2.2), bold=True),
            fill="black",
            anchor="ma",
        )
        qr = _qr_image(spec.payload_for(deck.actor_id), _mm(24))
        image.paste(
            qr,
            (
                (image.width - qr.width) // 2,
                trim_bottom - safe - qr.height - _mm(8),
            ),
        )
        qr.close()
        return image

    draw.text(
        ((trim_left + trim_right) // 2, trim_top + _mm(7)),
        spec.title,
        font=_fit_title_font(draw, spec.title, CARD_SIZE_PX[0] - 2 * safe),
        fill="black",
        anchor="ma",
    )
    draw.line(
        (content_left, trim_top + _mm(13), content_right, trim_top + _mm(13)),
        fill="black",
        width=max(1, _mm(0.25)),
    )
    draw.text(
        (content_left, trim_top + _mm(16)),
        _phase_label(spec),
        font=_font(_mm(2.35), bold=True),
        fill="black",
    )
    draw.text(
        (content_right, trim_top + _mm(16)),
        f"POZIOM {spec.required_level}",
        font=_font(_mm(2.15), bold=True),
        fill="black",
        anchor="ra",
    )
    timing_font = _fit_timing_font(
        draw,
        spec.timing,
        content_right - content_left,
    )
    draw.text(
        (content_left, trim_top + _mm(22)),
        spec.timing,
        font=timing_font,
        fill="black",
    )
    mechanic_top = trim_top + _mm(29)
    mechanic_bottom = trim_top + _mm(64)
    draw.rounded_rectangle(
        (content_left, mechanic_top, content_right, mechanic_bottom),
        radius=_mm(1.2),
        outline="black",
        width=max(1, _mm(0.2)),
    )
    draw.text(
        (content_left + _mm(2), mechanic_top + _mm(2)),
        "EFEKT MECHANICZNY",
        font=_font(_mm(1.8), bold=True),
        fill="black",
    )
    mechanic_font = _font(_mm(1.8))
    mechanic_lines = _wrapped_lines(
        draw,
        spec.mechanic,
        mechanic_font,
        content_right - content_left - _mm(4),
        max_lines=10,
    )
    draw.multiline_text(
        (content_left + _mm(2), mechanic_top + _mm(7)),
        "\n".join(mechanic_lines),
        font=mechanic_font,
        fill="black",
        spacing=_mm(0.45),
    )
    qr = _qr_image(spec.payload_for(deck.actor_id), _mm(18))
    qr_left = content_right - qr.width
    qr_top = trim_bottom - safe - qr.height
    image.paste(qr, (qr_left, qr_top))
    flavor_font = _font(_mm(1.55), serif=True)
    flavor_lines = _wrapped_lines(
        draw,
        spec.flavor,
        flavor_font,
        qr_left - content_left - _mm(3),
        max_lines=4,
    )
    draw.multiline_text(
        (content_left, mechanic_bottom + _mm(4)),
        "\n".join(flavor_lines),
        font=flavor_font,
        fill="black",
        spacing=_mm(0.4),
    )
    draw.text(
        (content_left, trim_bottom - safe - _mm(1)),
        f"{deck.actor_id[:2].upper()}-{spec.source_id[:10].upper()}",
        font=_font(_mm(1.25), bold=True),
        fill="black",
        anchor="ls",
    )
    qr.close()
    return image


def render_character_hero_card_bw_test(deck: CharacterDeckSpec) -> Image.Image:
    """Render a portrait-free hero card matching the low-toner playtest deck."""
    image, draw = _bw_test_card_canvas()
    trim_left = BLEED_PX
    trim_top = BLEED_PX
    trim_right = trim_left + CARD_SIZE_PX[0] - 1
    trim_bottom = trim_top + CARD_SIZE_PX[1] - 1
    safe = _mm(SAFE_MARGIN_MM)
    content_left = trim_left + safe
    content_right = trim_right - safe
    hero_spec = _hero_spec(deck.actor_id)
    draw.text(
        ((trim_left + trim_right) // 2, trim_top + _mm(8)),
        hero_spec.name.upper(),
        font=_font(_mm(4.5), serif=True, bold=True),
        fill="black",
        anchor="ma",
    )
    draw.multiline_text(
        ((trim_left + trim_right) // 2, trim_top + _mm(17)),
        deck.subtitle,
        font=_font(_mm(2.0), bold=True),
        fill="black",
        anchor="ma",
        align="center",
    )
    draw.line(
        (content_left, trim_top + _mm(25), content_right, trim_top + _mm(25)),
        fill="black",
        width=max(1, _mm(0.25)),
    )
    draw.text(
        (content_left, trim_top + _mm(29)),
        "ZASADY PASYWNE",
        font=_font(_mm(2.0), bold=True),
        fill="black",
    )
    passive_font = _font(_mm(1.55))
    passive_text = "\n".join(f"• {entry}" for entry in deck.passives)
    passive_lines = _wrapped_lines(
        draw,
        passive_text,
        passive_font,
        content_right - content_left,
        max_lines=15,
    )
    draw.multiline_text(
        (content_left, trim_top + _mm(35)),
        "\n".join(passive_lines),
        font=passive_font,
        fill="black",
        spacing=_mm(0.45),
    )
    qr = _qr_image(hero_spec.payload, _mm(20))
    image.paste(
        qr,
        (content_right - qr.width, trim_bottom - safe - qr.height),
    )
    draw.text(
        (content_left, trim_bottom - safe - _mm(2)),
        f"KARTA BOHATERA · {deck.actor_id.upper()}",
        font=_font(_mm(1.35), bold=True),
        fill="black",
        anchor="ls",
    )
    qr.close()
    return image


def _hero_spec(actor_id: str):
    return next(spec for spec in HERO_CARD_SPECS if spec.actor_id == actor_id)


def generate_character_sheet_bw_pdf(
    actor_id: str,
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write one toner-friendly A4 character sheet."""
    pdf_path = Path(output_path)
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Arkusz postaci musi mieć rozszerzenie .pdf.")
    if pdf_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {pdf_path}")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    sheet = render_character_sheet_bw(CHARACTER_DECKS[actor_id])
    sheet.save(pdf_path, "PDF", resolution=DPI, quality=95)
    sheet.close()
    return pdf_path


def generate_combined_character_sheets_bw_pdf(
    actor_ids: tuple[str, ...],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write an ordered multi-page black-and-white starter-roster workbook."""
    if not actor_ids:
        raise ValueError("Wymagany jest co najmniej jeden bohater.")
    pdf_path = Path(output_path)
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Zbiór arkuszy postaci musi mieć rozszerzenie .pdf.")
    if pdf_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {pdf_path}")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pages = [render_character_sheet_bw(CHARACTER_DECKS[actor_id]) for actor_id in actor_ids]
    pages[0].save(
        pdf_path,
        "PDF",
        resolution=DPI,
        save_all=True,
        append_images=pages[1:],
        quality=95,
    )
    for page in pages:
        page.close()
    return pdf_path


def generate_character_card_set_bw_test(
    actor_id: str,
    output_path: str | Path,
    *,
    manifest_path: str | Path | None = None,
    preview_dir: str | Path | None = None,
    overwrite: bool = False,
) -> CharacterCardSetResult:
    """Write a front-only, illustration-free test deck for black toner."""
    deck = CHARACTER_DECKS[actor_id]
    pdf_path = Path(output_path)
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Testowy zestaw kart musi mieć rozszerzenie .pdf.")
    resolved_manifest = Path(manifest_path) if manifest_path else Path(f"{pdf_path}.json")
    if not overwrite:
        for candidate in (pdf_path, resolved_manifest):
            if candidate.exists():
                raise FileExistsError(f"Refusing to overwrite existing file: {candidate}")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_manifest.parent.mkdir(parents=True, exist_ok=True)
    previews = Path(preview_dir) if preview_dir else None
    if previews:
        previews.mkdir(parents=True, exist_ok=True)

    action_cards = printable_action_cards(deck)
    hero_spec = _hero_spec(actor_id)
    fronts: tuple[Image.Image, ...] = (
        render_character_hero_card_bw_test(deck),
        *(render_character_action_card_bw_test(deck, card) for card in action_cards),
    )
    pages: list[Image.Image] = []
    for offset in range(0, len(fronts), 4):
        sheet_number = offset // 4 + 1
        page = _render_sheet(
            fronts[offset : offset + 4],
            backs=False,
            sheet_number=sheet_number,
        )
        pages.append(page)
        if previews:
            page.save(
                previews / f"sheet_{sheet_number:02d}_fronts_bw.png",
                dpi=(DPI, DPI),
            )
    dossier = render_character_dossier_bw(deck)
    statistics = render_character_sheet_bw(deck)
    pages.extend((dossier, statistics))
    if previews:
        dossier.save(previews / "dossier_bw.png", dpi=(DPI, DPI))
        statistics.save(previews / "statistics_bw.png", dpi=(DPI, DPI))
    pages[0].save(
        pdf_path,
        "PDF",
        resolution=DPI,
        save_all=True,
        append_images=pages[1:],
        quality=95,
    )
    manifest = {
        "schema": "dnd_board_game.character_card_set_bw_test",
        "schema_version": 1,
        "actor_id": actor_id,
        "deck_title": deck.deck_title,
        "dpi": DPI,
        "print_mode": "black_and_white_toner_fronts_only_with_dossier_and_statistics",
        "page": {
            "format": "A4",
            "cards_per_sheet": 4,
            "pages": len(pages),
        },
        "backs_included": False,
        "dossier_pages": 1,
        "statistics_pages": 1,
        "cards": [
            {
                "source_id": actor_id,
                "title": hero_spec.name,
                "kind": "actor",
                "phase": "actor",
                "payload": hero_spec.payload,
                "passives_on_hero_front": list(deck.passives),
            },
            *[
                {
                    "source_id": card.source_id,
                    "title": card.title,
                    "kind": card.kind,
                    "required_level": card.required_level,
                    "phase": (
                        "control"
                        if card.kind == "universal"
                        else card_action_definition(card.source_id).phase.value
                    ),
                    "timing": card.timing,
                    "mechanic": card.mechanic,
                    "payload": card.payload_for(actor_id),
                }
                for card in action_cards
            ],
        ],
    }
    resolved_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for image in (*fronts, *pages):
        image.close()
    return CharacterCardSetResult(
        pdf_path=pdf_path,
        manifest_path=resolved_manifest,
        card_count=len(fronts),
        page_count=len(pages),
    )


def generate_character_card_set(
    actor_id: str,
    output_path: str | Path,
    *,
    manifest_path: str | Path | None = None,
    preview_dir: str | Path | None = None,
    overwrite: bool = False,
) -> CharacterCardSetResult:
    deck = CHARACTER_DECKS[actor_id]
    pdf_path = Path(output_path)
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Zestaw kart musi mieć rozszerzenie .pdf.")
    resolved_manifest = Path(manifest_path) if manifest_path else Path(f"{pdf_path}.json")
    if not overwrite:
        for candidate in (pdf_path, resolved_manifest):
            if candidate.exists():
                raise FileExistsError(f"Refusing to overwrite existing file: {candidate}")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_manifest.parent.mkdir(parents=True, exist_ok=True)
    previews = Path(preview_dir) if preview_dir else None
    if previews:
        previews.mkdir(parents=True, exist_ok=True)

    hero_spec = _hero_spec(actor_id)
    action_cards = printable_action_cards(deck)
    fronts: tuple[Image.Image, ...] = (
        render_hero_card_front(hero_spec),
        *(render_character_action_card(deck, card) for card in action_cards),
    )
    pages: list[Image.Image] = []
    back_template = render_character_card_back(deck)
    hero_back = render_character_hero_back(deck)
    for offset in range(0, len(fronts), 4):
        group = fronts[offset : offset + 4]
        backs = tuple(
            hero_back.copy() if offset + index == 0 else back_template.copy()
            for index, _ in enumerate(group)
        )
        sheet_number = offset // 4 + 1
        front_sheet = _render_sheet(group, backs=False, sheet_number=sheet_number)
        back_sheet = _render_sheet(backs, backs=True, sheet_number=sheet_number)
        pages.extend((front_sheet, back_sheet))
        if previews:
            front_sheet.save(previews / f"sheet_{sheet_number:02d}_fronts.png", dpi=(DPI, DPI))
            back_sheet.save(previews / f"sheet_{sheet_number:02d}_backs.png", dpi=(DPI, DPI))
        for back in backs:
            back.close()
    dossier = render_character_dossier(deck)
    statistics = render_character_sheet_bw(deck)
    pages.extend((dossier, statistics))
    if previews:
        dossier.save(previews / "dossier.png", dpi=(DPI, DPI))
        statistics.save(previews / "statistics.png", dpi=(DPI, DPI))
        statistics.save(previews / "character_sheet_bw.png", dpi=(DPI, DPI))
    pages[0].save(
        pdf_path,
        "PDF",
        resolution=DPI,
        save_all=True,
        append_images=pages[1:],
        quality=95,
    )
    sheet_count = (len(fronts) + 3) // 4
    manifest = {
        "schema": "dnd_board_game.character_card_set",
        "schema_version": 1,
        "actor_id": actor_id,
        "deck_title": deck.deck_title,
        "dpi": DPI,
        "page": {"format": "A4", "cards_per_sheet": 4},
        "card": {
            "trim_width_mm": CARD_WIDTH_MM,
            "trim_height_mm": CARD_HEIGHT_MM,
            "bleed_mm": BLEED_MM,
            "safe_margin_mm": SAFE_MARGIN_MM,
            "qr_target_mm": QR_TARGET_MM,
        },
        "duplex": {
            "sheets": sheet_count,
            "card_pages": sheet_count * 2,
            "flip": "long_edge",
        },
        "dossier_pages": 1,
        "statistics_pages": 1,
        "statistics_style": "black_and_white_toner",
        "cards": [
            {
                "source_id": actor_id,
                "title": hero_spec.name,
                "kind": "actor",
                "required_level": 1,
                "payload": hero_spec.payload,
                "passives_on_dossier": list(deck.passives),
                "passives_on_hero_back": list(deck.passives),
            },
            *[
                {
                    "source_id": card.source_id,
                    "title": card.title,
                    "kind": card.kind,
                    "required_level": card.required_level,
                    "phase": (
                        "control"
                        if card.kind == "universal"
                        else card_action_definition(card.source_id).phase.value
                    ),
                    "timing": card.timing,
                    "mechanic": card.mechanic,
                    "flavor": card.flavor,
                    "payload": card.payload_for(actor_id),
                    "art_asset": _art_panel_for(deck, card.source_id).asset,
                    "art_panel": _art_panel_for(deck, card.source_id).panel_index,
                }
                for card in action_cards
            ],
        ],
    }
    resolved_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for image in (*fronts, back_template, hero_back, *pages):
        image.close()
    return CharacterCardSetResult(
        pdf_path=pdf_path,
        manifest_path=resolved_manifest,
        card_count=len(fronts),
        page_count=sheet_count * 2 + 2,
    )


__all__ = [
    "ADDITIONAL_ART",
    "CHARACTER_DECKS",
    "DAGNA_DECK",
    "GARRAN_DECK",
    "CharacterActionCardSpec",
    "CharacterCardSetResult",
    "CharacterDeckSpec",
    "generate_character_sheet_bw_pdf",
    "generate_combined_character_sheets_bw_pdf",
    "generate_character_card_set_bw_test",
    "generate_character_card_set",
    "printable_action_cards",
    "render_character_action_card",
    "render_character_action_card_bw_test",
    "render_character_card_back",
    "render_character_dossier",
    "render_character_statistics",
    "render_character_sheet_bw",
    "render_character_hero_back",
    "render_character_hero_card_bw_test",
    "render_character_dossier_bw",
]

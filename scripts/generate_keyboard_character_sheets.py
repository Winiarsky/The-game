#!/usr/bin/env python3
"""Render print-ready keyboard reference sheets from generated backgrounds."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dnd_board_game.character_creation.archetypes import (  # noqa: E402
    HERO_ARCHETYPES_BY_ID,
)
from dnd_board_game.ui.combat_keyboard import HERO_SHORTCUTS  # noqa: E402
ASSET_ROOT = ROOT / "assets/physical_cards/character_sets/keyboard_v1"
BACKGROUND_ROOT = ASSET_ROOT / "backgrounds"
PNG_ROOT = ASSET_ROOT / "png"
PDF_ROOT = ASSET_ROOT / "pdf"
MINIMAL_ROOT = ASSET_ROOT / "minimal_bw"
MINIMAL_PNG_ROOT = MINIMAL_ROOT / "png"
MINIMAL_PDF_ROOT = MINIMAL_ROOT / "pdf"
CANVAS_SIZE = (2048, 3072)
A4_SIZE_300_DPI = (2480, 3508)

FONT_REGULAR = Path("/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.otf")
FONT_BOLD = Path("/usr/share/fonts/opentype/urw-base35/NimbusSans-Bold.otf")
FONT_CONDENSED = Path("/usr/share/fonts/opentype/urw-base35/NimbusSansNarrow-Regular.otf")
FONT_CONDENSED_BOLD = Path("/usr/share/fonts/opentype/urw-base35/NimbusSansNarrow-Bold.otf")
FONT_DISPLAY = Path("/usr/share/fonts/truetype/noto/NotoSerifDisplay-Bold.ttf")
FONT_ACTION = Path("/usr/share/fonts/truetype/noto/NotoSansDisplay-Bold.ttf")
FONT_BODY = Path("/usr/share/fonts/truetype/noto/NotoSansDisplay-Regular.ttf")

INK = (31, 28, 25, 255)
MUTED_INK = (72, 65, 58, 255)
PARCHMENT = (240, 226, 194, 255)
LIGHT = (250, 243, 224, 255)
SHADOW = (12, 13, 15, 210)


@dataclass(frozen=True)
class Action:
    key: str
    name: str
    meta: str
    body: str


@dataclass(frozen=True)
class Section:
    title: str
    actions: tuple[Action, ...]


@dataclass(frozen=True)
class Hero:
    hero_id: str
    name: str
    role: str
    level: int
    hp: int
    ac: int
    speed: int
    abilities: str
    attacks: str
    resource: str
    accent: tuple[int, int, int]
    sections: tuple[Section, Section, Section]


@dataclass(frozen=True)
class RuleNote:
    name: str
    body: str


COMMON_KEYS: tuple[tuple[str, str], ...] = (
    ("SPACJA", "ATAK"),
    ("M", "RUCH"),
    ("B", "BROŃ"),
    ("I", "PRZEDMIOT"),
    ("0", "KONIEC TURY"),
    ("ENTER", "POTWIERDŹ"),
    ("ESC / BACK", "WRÓĆ"),
)


def a(key: str, name: str, meta: str, body: str) -> Action:
    return Action(key, name, meta, body)


HEROES: tuple[Hero, ...] = (
    Hero(
        "garran", "GARRAN", "CZŁOWIEK · WOJOWNIK · DOWÓDCA", 3, 28, 19, 30,
        "SIŁ 18  ZRC 14  KON 15  INT 9  MDR 13  CHA 11",
        "MIECZ +6 · 1K8+4   |   KUSZA +4 · 1K8+2",
        "ZASOBY: TAKTYKA 4 · DRUGI ODDECH 1 · ZRYW AKCJI 1",
        (91, 135, 168),
        (
            Section("PRZETRWANIE", (
                a("Q", "DRUGI ODDECH", "AKCJA DOD. · 1/ODPOCZYNEK", "Odzyskaj 1k10 + poziom PW."),
                a("W", "ZRYW AKCJI", "AKCJA DOD. · 1/ODPOCZYNEK", "Po wykonaniu akcji odzyskaj akcję."),
                a("E", "UDERZENIE TARCZĄ", "AKCJA RUCHU · 5 STÓP", "Próba Siły. Wygrana: 1k4+SIŁ i odepchnięcie o 1 pole."),
            )),
            Section("OBRONA I ROZKAZY", (
                a("R", "POZYCJA OBRONNA", "AKCJA RUCHU", "Rezygnujesz z ruchu: +2 KP do następnej tury lub do ruchu."),
                a("A", "ROZKAZ: STAĆ!", "AKCJA · 60 STÓP · 1 TAKTYKA", "MDR ST 14. Porażka: cel nie porusza się dobrowolnie."),
                a("S", "OSŁONA TARCZĄ", "BONUS · 1 TAKTYKA", "Sąsiedni sojusznicy mają +2 KP do twojej następnej tury."),
            )),
            Section("WSPARCIE", (
                a("D", "MOWA DOWÓDCY", "AKCJA · 30 STÓP · 1 TAKTYKA", "Usuń strach; przewaga przy pierwszym ataku, teście lub rzucie obronnym."),
                a("F", "OSŁONA TOWARZYSZA", "AKCJA · 5 STÓP · 1 TAKTYKA", "Pierwszy pojedynczy atak lub efekt na wybranego sojusznika trafia Garrana."),
                a("AUTO", "REAKCJE", "GRA WYŚWIETLI PYTANIE", "Gdy reakcja jest możliwa, wybierz ją w oknie i potwierdź Enterem."),
            )),
        ),
    ),
    Hero(
        "brakka", "BRAKKA", "PÓŁORKA · BARBARZYNKA · ŁAMACZKA LINII", 3, 35, 14, 30,
        "SIŁ 18  ZRC 13  KON 16  INT 8  MDR 12  CHA 10",
        "TOPÓR +6 · 1K12+4   |   OSZCZEP +6 · 1K6+4",
        "ZASOBY: SZAŁ 3 · FURIA 3 W SZALE · NIEUGIĘTOŚĆ 1",
        (198, 77, 54),
        (
            Section("WEJŚCIE W SZAŁ", (
                a("Q", "SZAŁ", "BONUS · 3/DŁUGI ODPOCZYNEK", "+2 obrażeń wręcz, odporność na kłute/cięte/obuchowe; odnawia 3 Furii."),
                a("W", "LEKKOMYŚLNY ATAK", "AKCJA · ATAK WRĘCZ", "Atak z przewagą. Ataki przeciw Brakce mają przewagę do jej następnej tury."),
            )),
            Section("NACISK", (
                a("E", "POTĘŻNE UDERZENIE", "AKCJA · SZAŁ · 2 FURII", "Wykonaj atak wręcz z premią +10 do trafienia."),
                a("R", "Z BARA", "AKCJA · 5 STÓP", "Próba Atletyki. Odepchnij 5 stóp + 5 za każde 5 punktów przewagi, maks. 30."),
                a("A", "PRZYSPIESZENIE", "BONUS · SZAŁ · 1 FURII", "Podwój bazowy ruch Brakki w tej turze."),
            )),
            Section("KONTROLA", (
                a("S", "OGŁUSZAJĄCY RYK", "AKCJA · STOŻEK 15 · 2 FURII", "KON ST 15. 2k6 i brak ruchu; sukces: połowa obrażeń."),
                a("AUTO", "TWARDA JAK SKAŁA", "REAKCJA · SZAŁ · 1 FURII", "Po odporności zmniejsz otrzymane obrażenia o 1k12+KON."),
                a("AUTO", "REAKCJE", "GRA WYŚWIETLI PYTANIE", "Nie naciskaj skrótu: zaakceptuj albo odrzuć reakcję w oknie."),
            )),
        ),
    ),
    Hero(
        "mira", "MIRA", "NIZIOŁKA · ŁOTRZYCA · SKRYTOBÓJCZYNI", 3, 21, 15, 25,
        "SIŁ 8  ZRC 19  KON 13  INT 14  MDR 12  CHA 11",
        "RAPIER +6 · 1K8+4   |   NOŻE +6 · 1K4+4 · 15 STÓP",
        "ZASOBY: FORTELE 4 · UKRYCIE: +1K6 / +2K6 / +3K6",
        (126, 88, 169),
        (
            Section("MOBILNOŚĆ", (
                a("Q", "ZASŁONA DYMNA", "AKCJA · RUCH 15 · 1 FORTEL", "Bez ataków okazyjnych, potem Ukrycie nawet obok wroga."),
                a("W", "PRZESKOK PRZEZ GARDĘ", "AKCJA · WRĘCZ", "Jeśli pole za celem jest wolne: +2 do ataku i obrażeń, potem przejdź za cel."),
            )),
            Section("KONTROLA", (
                a("E", "WYKRYCIE PUŁAPEK", "AKCJA · PROMIEŃ 45 STÓP", "Fizyczny test Percepcji wykrywa pułapki w walce."),
                a("R", "CIĘCIE ŚCIĘGNA", "AKCJA · FLANKA · 1 FORTEL", "Po trafieniu wręcz prędkość celu spada o połowę aż do leczenia."),
            )),
            Section("SKRYTOBÓJSTWO", (
                a("A", "PRZESZYWAJĄCY ATAK", "AKCJA · FLANKA · 1 FORTEL", "Po trafieniu zaatakuj też wroga stojącego dokładnie za pierwszym."),
                a("S", "MISTRZYNI OSTRZY", "WZMOCNIENIE · 1 FORTEL", "Ukryty trafiony nożem cel krwawi 1k4 na początku tur do leczenia."),
                a("AUTO", "UNIK INSTYNKTOWNY", "REAKCJA · 1 FORTEL", "Gdy widoczny wróg atakuje ukrytą Mirę, jego atak ma utrudnienie."),
            )),
        ),
    ),
    Hero(
        "dagna", "DAGNA", "KRASNOLUDKA · KAPŁANKA · OPIEKUNKA", 3, 30, 16, 25,
        "SIŁ 13  ZRC 10  KON 16  INT 8  MDR 18  CHA 12",
        "BUŁAWA +3 · 1K6+1   |   CZARY +6 · ST 14",
        "ZASOBY: BOSKA MOC 1 · KONCENTRACJA: TYLKO 1 EFEKT",
        (218, 168, 72),
        (
            Section("MODLITWY", (
                a("Q", "ŚWIĘTY PŁOMIEŃ", "AKCJA · STOŻEK 15 · ZRC ST 14", "Wrogowie odnoszą 1k8 obrażeń od blasku przy porażce."),
                a("W", "LECZĄCE SŁOWO", "BONUS · 60 STÓP", "Wybrany cel odzyskuje 1k4+7 PW."),
                a("E", "BŁOGOSŁAWIEŃSTWO", "AKCJA · AURA 10 · KONC. · 5 RUND", "Ty i sojusznicy w aurze dodajecie 1k4 do ataków i rzutów obronnych."),
            )),
            Section("BOSKA MOC", (
                a("R", "ZACHOWANIE ŻYCIA", "AKCJA · 1 BOSKA MOC", "Rozdziel 15 PW między cele; nie lecz powyżej połowy maks. PW."),
                a("A", "AURA BOSKIEJ OPIEKI", "AKCJA · AURA 5 · KONC. · 5 RUND", "Wrogowie w aurze mają −2 do ataków i obrażeń."),
                a("S", "POCISK PRZEWODNI", "AKCJA · 75 STÓP · ATAK CZAREM", "2k6 blasku; następny atak przeciw celowi ma przewagę."),
            )),
            Section("CZARY WSPARCIA", (
                a("D", "AURA UZDRAWIAJĄCEJ ŁASKI", "AKCJA · AURA 10 · KONC. · 3 RUNDY", "Cztery pierwsze leczenia w aurze zyskują +1k8+MDR."),
                a("F", "POMNIEJSZE PRZYWRÓCENIE", "AKCJA · DOTYK", "Usuń jedną obsługiwaną negatywną kondycję."),
                a("Z", "DUCHOWA BROŃ", "BONUS · 60 STÓP", "Przywołaj broń: ruch 20, atak sąsiedni 1k8+4, KP 18."),
            )),
        ),
    ),
    Hero(
        "lorian", "LORIAN", "PÓŁELF · BARD · TAKTYK KUSZY", 3, 24, 13, 30,
        "SIŁ 8  ZRC 15  KON 14  INT 12  MDR 10  CHA 19",
        "KUSZA +4 · 1K6+2   |   CZARY +6 · ST 14",
        "ZASOBY: INSPIRACJA 4 · KOŚĆ 1K6 · KONCENTRACJA: 1 EFEKT",
        (187, 86, 181),
        (
            Section("KUSZA TAKTYCZNA", (
                a("Q", "BARDOWSKA INSPIRACJA", "BONUS · 60 STÓP", "Sojusznik zachowuje 1k6 do testu, ataku lub rzutu obronnego."),
                a("W", "CELOWNIK OPTYCZNY", "AKCJA · CAŁY RUCH · 60 STÓP", "Przed ruchem: dwa strzały w jeden cel, jego KP jest niższe o 2."),
                a("E", "KPIĄCY STRZAŁ", "AKCJA · 45 STÓP", "Trafienie: utrudnienie pierwszego ataku celu i jego rzutów MDR."),
                a("R", "PROWOKUJĄCY STRZAŁ", "AKCJA · 45 STÓP", "Cel zyskuje premię przeciw Lorianowi, lecz karę przeciw innym równą obrażeniom."),
            )),
            Section("KONTROLA I CZARY", (
                a("A", "WIĄŻĄCY STRZAŁ", "AKCJA · OBSZAR 3×3 · 45 STÓP", "Wszyscy w obszarze: ZRC; sukces pół ruchu, porażka brak ruchu."),
                a("S", "SZEPT PANIKI", "AKCJA · 45 STÓP · MDR ST 14", "2k6 psychicznych i ruch 15 stóp od Loriana; sukces: połowa."),
                a("D", "GRZMIĄCY REFREN", "AKCJA · STOŻEK 15 · KON ST 14", "2k8 i odepchnięcie 10 stóp; sukces: połowa bez odepchnięcia."),
                a("F", "OGNIKI", "AKCJA · SZEŚCIAN 20 · KONC.", "ZRC: porażka daje przewagę atakującym i blokuje niewidzialność."),
            )),
            Section("SCENA I REAKCJE", (
                a("Z", "OBEZWŁADNIAJĄCY ŻART", "AKCJA · 30 STÓP · KONC. · MDR ST 14", "Porażka: cel pada i jest obezwładniony."),
                a("X", "KOMENDA SCENICZNA", "AKCJA · 45 STÓP · MDR ST 14", "Wybierz: podejdź, odejdź albo zamilknij; ruch do 15 stóp."),
                a("C", "PRZYSPIESZONY REFREN", "AKCJA · KONC. · 3 RUNDY", "Przy rzuceniu jeden strzał; potem bonus daje trzeci strzał salwy."),
                a("AUTO", "KONTRAPUNKT / CIĘTA RIPOSTA", "REAKCJE · PYTANIE NA EKRANIE", "Gra sama zaproponuje dostępny strzał, redukcję obrażeń albo kość 1k6."),
            )),
        ),
    ),
    Hero(
        "nimra", "NIMRA", "GNOMKA · CZARODZIEJKA · KONTROLERKA POLA", 3, 20, 12, 25,
        "SIŁ 8  ZRC 14  KON 14  INT 19  MDR 12  CHA 10",
        "CZARY +6 · ST 14   |   SZTYLET +4 · 1K4+2",
        "ZASOBY: METAMAGIA 4 · NAJPIERW LITERA METAMAGII, POTEM CZAR · TARCZA: REAKCJA AUTO",
        (74, 127, 205),
        (
            Section("METAMAGIA · T Y U G H", (
                a("T", "RZEŹBIENIE POLA", "1 PUNKT", "Wyklucz z obszaru czaru do 4 pól."),
                a("Y", "ODLEGŁY CZAR", "1 PUNKT", "+15 stóp zasięgu, maksymalnie 75."),
                a("U", "PRZECIĄŻONY CZAR", "1 PUNKT", "Dodaj jedną bazową kość obrażeń."),
                a("G", "WYMUSZONY SPLOT", "2 PUNKTY", "Jeden cel ma utrudnienie pierwszego rzutu obronnego."),
                a("H", "TRANSMUTACJA ENERGII", "1 PUNKT", "Zmień typ: kwas, zimno, ogień, błyskawice lub grzmot."),
            )),
            Section("CZARY Q–S + J", (
                a("Q", "LODOWY IMPULS", "AKCJA · 50 STÓP · KON ST 14", "1k8 zimna i −10 stóp ruchu przy porażce."),
                a("W", "KWASOWY ROZPRYSK", "AKCJA · 40 STÓP · PROMIEŃ 5", "ZRC: 1k6 kwasu przy porażce."),
                a("E", "SZPILKA UMYSŁU", "AKCJA · 45 STÓP · MDR ST 14", "1k6 psychicznych i brak reakcji przy porażce."),
                a("R", "WACHLARZ PŁOMIENI", "AKCJA · STOŻEK 15 · ZRC ST 14", "2k6 ognia; sukces: połowa."),
                a("A", "FALA ODRZUTU", "AKCJA · LINIA 30 · SIŁ ST 14", "2k6 mocy i odepchnięcie 5 stóp; sukces: połowa."),
                a("S", "LEPKA MATRYCA", "AKCJA · 50 · OBSZAR 10 · 3 RUNDY", "Trudny teren; ZRC przy wejściu/starcie, porażka przewraca."),
                a("J", "MGLISTY KROK", "BONUS · TELEPORT 30 STÓP", "Wybierz wolne pole w zasięgu."),
            )),
            Section("CZARY D–V + K", (
                a("D", "SEN", "AKCJA · 50 STÓP", "Pula 5k8 usypia cele od najniższych PW."),
                a("F", "MGŁA", "AKCJA · 50 · PROMIEŃ 15 · KONC.", "Obszar jest całkowicie zasłonięty."),
                a("Z", "SIEĆ", "AKCJA · 50 · SZEŚCIAN 20 · KONC.", "Trudny teren; ZRC przy porażce unieruchamia."),
                a("X", "PIORUNOWY SZLAK", "AKCJA · 60 STÓP · ZRC ST 14", "3k6/połowa; łańcuch do najbliższych, także sojuszników."),
                a("C", "ZAŁAMANIE WOLI", "AKCJA · 50 · PROMIEŃ 10 · MDR ST 14", "2k6, brak reakcji i utrudnienie pierwszego ataku; sukces połowa."),
                a("V", "STAZA ISTOTY", "AKCJA · 50 · KONC. · MDR ST 14", "Ruch 0 i brak akcji ruchu; ponawiany rzut, maks. 3 rundy."),
                a("K", "ROZTRZASKANIE", "AKCJA · OBSZAR · KON ST 14", "3k8 grzmotu; sukces: połowa."),
            )),
        ),
    ),
    Hero(
        "erynd", "ERYND", "ELF · ŁOWCA · MOBILNY STRZELEC", 3, 25, 16, 30,
        "SIŁ 12  ZRC 19  KON 13  INT 11  MDR 14  CHA 8",
        "DŁUGI ŁUK +6 · 1K8+4   |   NÓŻ +3 · 1K4+1",
        "ZASOBY: INSTYNKT 4 · ZNACZNIK ŁOWCY: +1K6",
        (78, 132, 98),
        (
            Section("POZYCJA", (
                a("Q", "OZNACZENIE CELU", "BONUS · KONC. · 1 INSTYNKT", "+1k6 obrażeń bronią. Po pokonaniu celu przeniesienie jest darmowe."),
                a("W", "ZWIADOWCZA MOBILNOŚĆ", "BONUS", "Wybierz: Sprint albo Odstąpienie."),
                a("E", "CELOWANIE", "CAŁY RUCH · PRZED RUCHEM", "Następny atak długim łukiem ma przewagę."),
            )),
            Section("STRZAŁY INSTYNKTU", (
                a("R", "KOTWICZĄCA STRZAŁA", "AKCJA · 1 INSTYNKT · RZUT 1K4", "Trafienie: SIŁ ST 14; blokada ruchu albo pół ruchu przez wynik rund."),
                a("A", "OBNAŻAJĄCA STRZAŁA", "AKCJA · 1 INSTYNKT · RZUT 1K8", "Trafienie obniża KP celu o wynik do następnej tury Erynda."),
                a("S", "ZAKŁÓCAJĄCA STRZAŁA", "AKCJA · 1 INSTYNKT", "Trafienie odbiera reakcje i utrudnia następny atak celu."),
            )),
            Section("SALWA I TEREN", (
                a("D", "PODWÓJNY STRZAŁ", "AKCJA · 2 INSTYNKTU", "Jeden test: 2k8 + 2×ZRC. Znacznik i Pierwsza Krew tylko raz."),
                a("F", "LEŚNY KROK", "BONUS · 1 INSTYNKT", "Teleportuj się na wybrane wolne pole."),
                a("Z", "KOLCZASTE POSZYCIE", "AKCJA · 1 INSTYNKT", "Utwórz niebezpieczny trudny teren w wybranym obszarze."),
            )),
        ),
    ),
)


PASSIVES: dict[str, tuple[RuleNote, ...]] = {
    "garran": (
        RuleNote("Żelazna linia", "Sojusznik flankujący z Garranem tego samego przeciwnika ma przeciw niemu +1 KP."),
        RuleNote("Styl: Obrona", "+1 KP podczas noszenia pancerza; premia jest już uwzględniona na karcie."),
        RuleNote("Reakcje ochronne", "Gdy pojawi się legalna reakcja, gra sama wyświetli pytanie. Enter akceptuje, Esc odrzuca."),
    ),
    "brakka": (
        RuleNote("Nieustępliwa wytrzymałość", "Gdy obrażenia miałyby sprowadzić Brakkę do 0 PW, raz na długi odpoczynek pozostaje z 1 PW."),
        RuleNote("Odporność w Szale", "Podczas Szału otrzymuje połowę obrażeń kłutych, ciętych i obuchowych."),
        RuleNote("Twarda jak skała", "Po otrzymaniu obrażeń gra może zaproponować reakcję zmniejszającą je o 1k12 + KON za 1 Furię."),
    ),
    "mira": (
        RuleNote("Mistrzyni ukrycia", "Ukrycie Miry rośnie przy kolejnych udanych testach; przeciwnicy rozliczają wykrycie osobno."),
        RuleNote("Atak z cienia", "Trafienie z ukrycia lub przy właściwym wsparciu sojusznika zadaje dodatkowe obrażenia raz na turę."),
        RuleNote("Ruchomy cel", "Mira otrzymuje +2 KP przeciw zwykłym atakom dystansowym."),
    ),
    "dagna": (
        RuleNote("Uczeń Życia", "Czar leczenia poziomu 1 lub wyższego przywraca dodatkowo 2 + poziom czaru PW."),
        RuleNote("Krok ratowniczki", "Po uleczeniu innego sojusznika w promieniu 10 stóp lub usunięciu mu statusu może przesunąć się o 5 stóp bez ataku okazyjnego."),
        RuleNote("Odporność krasnoludzka", "Przewaga w rzutach obronnych przeciw truciźnie i odporność na obrażenia od trucizny."),
    ),
    "lorian": (
        RuleNote("Kusznik", "Akcja ataku kuszą ręczną wykonuje dwa strzały; broń ma zasięg 45 stóp i nie rozlicza amunicji."),
        RuleNote("Kontrapunkt i riposta", "Gdy spełniony jest warunek reakcji, gra sama proponuje strzał, redukcję obrażeń albo kość Inspiracji."),
        RuleNote("Improwizacja", "Po nieudanym teście interakcji może pojawić się możliwość improwizowanego przerzutu."),
    ),
    "nimra": (
        RuleNote("Katalog niemożliwego", "Nimra korzysta ze stałego zestawu czarów i pięciu modyfikacji Metamagii opisanych na stronie skrótów."),
        RuleNote("Gnomia przebiegłość", "Przewaga w rzutach obronnych na INT, MDR i CHA przeciw magii."),
        RuleNote("Tarcza", "Po trafieniu gra może zaproponować reakcję dającą +5 KP; nie wymaga osobnego skrótu."),
    ),
    "erynd": (
        RuleNote("Styl: Łucznictwo", "+2 do testów ataku bronią dystansową; premia jest już uwzględniona na karcie."),
        RuleNote("Pierwsza krew", "Pierwsze trafienie w pełni zdrowego celu zadaje dodatkowe 1k8 obrażeń, najwyżej raz na turę Erynda."),
        RuleNote("Czujność zwiadowcy", "+2 do inicjatywy i skuteczniejsze wykrywanie ukrytych przeciwników."),
    ),
}


FLAWS: dict[str, RuleNote] = {
    "garran": RuleNote("Wyrzuty sumienia", "Jeśli każdy sojusznik otrzymał co najmniej tyle obrażeń co Garran, a któryś więcej, Garran ma −2 do ataków, testów i rzutów obronnych."),
    "brakka": RuleNote("Bitewny amok", "Podczas Szału nie może używać mikstur, zwojów ani aktywnych właściwości przedmiotów; może nadal atakować trzymaną bronią."),
    "mira": RuleNote("Panika po zdemaskowaniu", "Przeciwnik, który przejrzał jej ukrycie, ma +2 do ataków przeciw Mirze; gdy widzą ją wszyscy, ukrycie się kończy."),
    "dagna": RuleNote("Nikogo nie zostawiam", "Gdy sojusznik w promieniu 30 stóp ma 0 PW, Dagna ma utrudnienie w działaniach innych niż ratunek."),
    "lorian": RuleNote("Potrzeba publiczności", "Zdolności specjalne wymagają żywego, przytomnego sojusznika w promieniu 10 stóp. Zwykłe ataki i czary działają normalnie."),
    "nimra": RuleNote("Echo magicznego wycieku", "Nie może użyć tego samego czaru ani tej samej Metamagii runda po rundzie."),
    "erynd": RuleNote("Trauma bratobójczego strzału", "Każdy przytomny sojusznik stojący obok celu daje Eryndowi −1 do ataku długim łukiem przeciw temu celowi."),
}


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def dark_accent(accent: tuple[int, int, int]) -> tuple[int, int, int, int]:
    """Return a parchment-safe version of the hero accent color."""

    return tuple(round(channel * 0.52) for channel in accent) + (255,)


def fit_font(draw: ImageDraw.ImageDraw, text: str, path: Path, max_size: int, max_width: int) -> ImageFont.FreeTypeFont:
    size = max_size
    while size > 18:
        candidate = font(path, size)
        if draw.textbbox((0, 0), text, font=candidate)[2] <= max_width:
            return candidate
        size -= 2
    return font(path, size)


def wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if not current or draw.textbbox((0, 0), trial, font=face)[2] <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_keycap(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    label: str,
    accent: tuple[int, int, int],
    *,
    dark: bool = False,
) -> None:
    fill = (*accent, 255) if dark else (39, 38, 39, 245)
    outline = LIGHT if dark else (*accent, 255)
    draw.rounded_rectangle(xy, radius=10, fill=fill, outline=outline, width=3)
    max_width = xy[2] - xy[0] - 12
    face = fit_font(draw, label, FONT_CONDENSED_BOLD, 30, max_width)
    box = draw.textbbox((0, 0), label, font=face)
    x = (xy[0] + xy[2] - (box[2] - box[0])) // 2
    y = (xy[1] + xy[3] - (box[3] - box[1])) // 2 - box[1]
    draw.text((x, y), label, font=face, fill=LIGHT)


def draw_header(image: Image.Image, hero: Hero) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    accent = hero.accent
    draw.rounded_rectangle((74, 900, 1974, 1030), radius=18, fill=SHADOW, outline=(*accent, 255), width=4)
    name_face = fit_font(draw, hero.name, FONT_CONDENSED_BOLD, 86, 1120)
    draw.text((105, 910), hero.name, font=name_face, fill=LIGHT, stroke_width=2, stroke_fill=(0, 0, 0, 220))
    role_face = fit_font(draw, hero.role, FONT_CONDENSED_BOLD, 34, 760)
    role_box = draw.textbbox((0, 0), hero.role, font=role_face)
    draw.text((1935 - role_box[2], 944), hero.role, font=role_face, fill=(*accent, 255))

    badge_face = font(FONT_CONDENSED_BOLD, 38)
    value_face = font(FONT_BOLD, 58)
    badges = (("POZIOM", str(hero.level)), ("PW", str(hero.hp)), ("KP", str(hero.ac)), ("RUCH", f"{hero.speed}′"))
    for index, (label, value) in enumerate(badges):
        x0 = 105 + index * 238
        draw.rounded_rectangle((x0, 1060, x0 + 205, 1205), radius=16, fill=(30, 30, 31, 235), outline=(*accent, 255), width=4)
        draw.text((x0 + 16, 1070), label, font=badge_face, fill=(*accent, 255))
        vbox = draw.textbbox((0, 0), value, font=value_face)
        draw.text((x0 + 185 - vbox[2], 1119), value, font=value_face, fill=LIGHT)

    info_x = 1080
    draw.text((info_x, 1065), "CECHY", font=font(FONT_CONDENSED_BOLD, 34), fill=(*accent, 255))
    draw.text((info_x, 1110), hero.abilities, font=fit_font(draw, hero.abilities, FONT_CONDENSED_BOLD, 31, 835), fill=INK)
    draw.text((info_x, 1162), hero.attacks, font=fit_font(draw, hero.attacks, FONT_CONDENSED_BOLD, 31, 835), fill=INK)

    draw.rounded_rectangle((102, 1240, 1938, 1395), radius=18, fill=(247, 236, 211, 180), outline=(*accent, 210), width=4)
    draw.text((128, 1255), hero.resource, font=fit_font(draw, hero.resource, FONT_CONDENSED_BOLD, 34, 1780), fill=INK)
    draw.text((128, 1312), "KLAWISZ = PODGLĄD  ·  ENTER = WYKONAJ  ·  ESC / BACKSPACE = ANULUJ BEZ KOSZTU", font=fit_font(draw, "KLAWISZ = PODGLĄD  ·  ENTER = WYKONAJ  ·  ESC / BACKSPACE = ANULUJ BEZ KOSZTU", FONT_CONDENSED, 28, 1780), fill=MUTED_INK)


def draw_common_keys(image: Image.Image, hero: Hero) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    x0, x1 = 102, 1938
    gap = 12
    cell_width = (x1 - x0 - gap * (len(COMMON_KEYS) - 1)) // len(COMMON_KEYS)
    for index, (key, label) in enumerate(COMMON_KEYS):
        left = x0 + index * (cell_width + gap)
        draw_keycap(draw, (left, 1487, left + cell_width, 1548), key, hero.accent, dark=True)
        label_face = fit_font(draw, label, FONT_CONDENSED_BOLD, 26, cell_width)
        box = draw.textbbox((0, 0), label, font=label_face)
        draw.text((left + (cell_width - box[2]) // 2, 1562), label, font=label_face, fill=LIGHT)


def draw_section(
    image: Image.Image,
    hero: Hero,
    section: Section,
    column_index: int,
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    columns = ((78, 670), (714, 1334), (1378, 1970))
    left, right = columns[column_index]
    inner_left, inner_right = left + 30, right - 30
    title_top, title_bottom = 1680, 1784
    draw.rounded_rectangle(
        (inner_left - 10, title_top, inner_right + 10, title_bottom),
        radius=14,
        fill=(28, 27, 25, 255),
        outline=(*hero.accent, 255),
        width=4,
    )
    draw.rectangle(
        (inner_left - 10, title_top, inner_left + 2, title_bottom),
        fill=(*hero.accent, 255),
    )
    title_face = fit_font(
        draw,
        section.title,
        FONT_DISPLAY,
        47,
        inner_right - inner_left - 32,
    )
    title_box = draw.textbbox((0, 0), section.title, font=title_face)
    title_y = title_top + (title_bottom - title_top - (title_box[3] - title_box[1])) // 2 - title_box[1]
    draw.text((inner_left + 18, title_y), section.title, font=title_face, fill=LIGHT)

    # The illustrated frame rises in the middle at the bottom; keep all copy
    # above it so even the densest Nimra columns remain fully readable.
    row_top, row_bottom = 1800, 2815
    row_height = (row_bottom - row_top) // max(1, len(section.actions))
    action_count = len(section.actions)
    if action_count <= 3:
        action_title_size, meta_size, body_size, max_body_lines, key_height = 34, 25, 27, 4, 56
    elif action_count <= 4:
        action_title_size, meta_size, body_size, max_body_lines, key_height = 31, 23, 25, 3, 54
    elif action_count <= 6:
        action_title_size, meta_size, body_size, max_body_lines, key_height = 27, 20, 22, 2, 48
    else:
        action_title_size, meta_size, body_size, max_body_lines, key_height = 24, 17, 19, 2, 42
    for index, action in enumerate(section.actions):
        cell_top = row_top + index * row_height
        cell_bottom = row_bottom if index == action_count - 1 else cell_top + row_height
        draw.line(
            (inner_left, cell_top, inner_right, cell_top),
            fill=dark_accent(hero.accent),
            width=3,
        )
        key_width = 86 if len(action.key) <= 2 else 126
        title_x = inner_left + key_width + 14
        action_title_face = fit_font(
            draw,
            action.name,
            FONT_ACTION,
            action_title_size,
            inner_right - title_x,
        )
        meta_face = font(FONT_ACTION, meta_size)
        body_face = font(FONT_BODY, body_size)
        meta_lines = wrap(draw, action.meta, meta_face, inner_right - inner_left)
        body_lines = wrap(draw, action.body, body_face, inner_right - inner_left)[:max_body_lines]
        text_height = key_height + 8 + len(meta_lines) * (meta_size + 4) + 4 + len(body_lines) * (body_size + 4)
        y = cell_top + max(5, (cell_bottom - cell_top - text_height) // 2)
        draw_keycap(
            draw,
            (inner_left, y, inner_left + key_width, y + key_height),
            action.key,
            hero.accent,
        )
        action_title_box = draw.textbbox((0, 0), action.name, font=action_title_face)
        action_title_y = y + (key_height - (action_title_box[3] - action_title_box[1])) // 2 - action_title_box[1]
        draw.text((title_x, action_title_y), action.name, font=action_title_face, fill=INK)
        y += key_height + 8
        for line in meta_lines:
            draw.text((inner_left, y), line, font=meta_face, fill=dark_accent(hero.accent))
            y += meta_size + 4
        y += 2
        for line in body_lines:
            draw.text((inner_left, y), line, font=body_face, fill=INK)
            y += body_size + 4


def render(hero: Hero) -> Image.Image:
    background_path = BACKGROUND_ROOT / f"{hero.hero_id}_keyboard_sheet_bg_v1.png"
    with Image.open(background_path) as source:
        image = source.convert("RGBA").resize(CANVAS_SIZE, Image.Resampling.LANCZOS)
    draw_header(image, hero)
    draw_common_keys(image, hero)
    for index, section in enumerate(hero.sections):
        draw_section(image, hero, section, index)
    return image.convert("RGB")


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    xy: tuple[int, int],
    width: int,
    face: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int] | tuple[int, int, int],
    line_gap: int = 8,
) -> int:
    x, y = xy
    for paragraph in text.splitlines():
        if not paragraph:
            y += face.size // 2
            continue
        for line in wrap(draw, paragraph, face, width):
            draw.text((x, y), line, font=face, fill=fill)
            y += face.size + line_gap
    return y


def draw_dossier_section(
    draw: ImageDraw.ImageDraw,
    hero: Hero,
    *,
    title: str,
    body: str,
    box: tuple[int, int, int, int],
    body_size: int = 27,
) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(
        box,
        radius=18,
        fill=(247, 238, 217, 236),
        outline=(*hero.accent, 220),
        width=4,
    )
    draw.text(
        (x0 + 24, y0 + 18),
        title,
        font=font(FONT_CONDENSED_BOLD, 33),
        fill=(*hero.accent, 255),
    )
    draw_wrapped_text(
        draw,
        body,
        xy=(x0 + 24, y0 + 66),
        width=x1 - x0 - 48,
        face=font(FONT_CONDENSED, body_size),
        fill=MUTED_INK,
        line_gap=7,
    )


def render_dossier(hero: Hero) -> Image.Image:
    """Render the narrative/rules companion page for a keyboard sheet."""

    profile = HERO_ARCHETYPES_BY_ID[hero.hero_id]
    background_path = BACKGROUND_ROOT / f"{hero.hero_id}_keyboard_sheet_bg_v1.png"
    with Image.open(background_path) as source:
        image = source.convert("RGBA").resize(CANVAS_SIZE, Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((74, 690, 1974, 850), radius=18, fill=SHADOW, outline=(*hero.accent, 255), width=4)
    draw.text((105, 704), hero.name, font=font(FONT_CONDENSED_BOLD, 78), fill=LIGHT, stroke_width=2, stroke_fill=(0, 0, 0, 220))
    draw.text((108, 790), "HISTORIA · CEL · ZASADY POSTACI", font=font(FONT_CONDENSED_BOLD, 29), fill=(*hero.accent, 255))
    tagline_face = fit_font(draw, profile.tagline, FONT_CONDENSED, 28, 820)
    tagline_box = draw.textbbox((0, 0), profile.tagline, font=tagline_face)
    draw.text((1938 - tagline_box[2], 760), profile.tagline, font=tagline_face, fill=LIGHT)

    left = (78, 1010)
    right = (1050, 1970)
    draw_dossier_section(draw, hero, title="HISTORIA", body=profile.history, box=(left[0], 890, left[1], 1370), body_size=28)
    draw_dossier_section(draw, hero, title="DLACZEGO PODRÓŻUJE", body=profile.motivation, box=(left[0], 1400, left[1], 1845), body_size=27)
    draw_dossier_section(draw, hero, title="CEL OSOBISTY", body=profile.personal_goal, box=(left[0], 1875, left[1], 2175), body_size=29)
    strengths = " · ".join(item.capitalize() for item in profile.strengths)
    draw_dossier_section(draw, hero, title="ATUTY", body=strengths, box=(left[0], 2205, left[1], 2475), body_size=29)
    resources = "\n".join(f"• {item}" for item in profile.resources)
    draw_dossier_section(draw, hero, title="ZASOBY I ODNAWIANIE", body=resources, box=(left[0], 2505, left[1], 2960), body_size=25)

    passives = "\n\n".join(f"{note.name.upper()}\n{note.body}" for note in PASSIVES[hero.hero_id])
    draw_dossier_section(draw, hero, title="PASYWKI", body=passives, box=(right[0], 890, right[1], 1705), body_size=25)
    flaw = FLAWS[hero.hero_id]
    draw_dossier_section(draw, hero, title=f"SKAZA · {flaw.name.upper()}", body=flaw.body, box=(right[0], 1735, right[1], 2150), body_size=27)
    turn_plan = "\n\n".join(f"{index}. {item}" for index, item in enumerate(profile.turn_plan, start=1))
    draw_dossier_section(draw, hero, title="JAK GRAĆ W TURZE", body=turn_plan, box=(right[0], 2180, right[1], 2960), body_size=25)
    return image.convert("RGB")


def draw_bw_keycap(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
) -> None:
    """Draw a low-ink key marker for the minimal print sheets."""

    draw.rounded_rectangle(box, radius=8, fill=255, outline=0, width=3)
    face = fit_font(draw, label, FONT_ACTION, 28, box[2] - box[0] - 12)
    text_box = draw.textbbox((0, 0), label, font=face)
    x = box[0] + (box[2] - box[0] - (text_box[2] - text_box[0])) // 2
    y = box[1] + (box[3] - box[1] - (text_box[3] - text_box[1])) // 2 - text_box[1]
    draw.text((x, y), label, font=face, fill=0)


def render_minimal_keyboard(hero: Hero) -> Image.Image:
    """Render an ink-saving, grayscale A4 keyboard reference page."""

    image = Image.new("L", A4_SIZE_300_DPI, 255)
    draw = ImageDraw.Draw(image)
    page_right = A4_SIZE_300_DPI[0] - 100
    draw.rectangle((70, 70, 2410, 3438), outline=0, width=3)

    draw.text((100, 105), hero.name, font=font(FONT_DISPLAY, 70), fill=0)
    role_face = fit_font(draw, hero.role, FONT_ACTION, 28, 1120)
    role_box = draw.textbbox((0, 0), hero.role, font=role_face)
    draw.text((page_right - role_box[2], 138), hero.role, font=role_face, fill=0)
    draw.text((100, 205), "KARTA TESTOWA · STEROWANIE KLAWIATURĄ", font=font(FONT_BODY, 25), fill=70)
    draw.line((100, 260, page_right, 260), fill=0, width=4)

    badges = (("POZIOM", hero.level), ("PW", hero.hp), ("KP", hero.ac), ("RUCH", f"{hero.speed}′"))
    for index, (label, value) in enumerate(badges):
        left = 100 + index * 250
        draw.rectangle((left, 300, left + 220, 475), outline=0, width=3)
        draw.text((left + 14, 315), label, font=font(FONT_ACTION, 25), fill=0)
        value_face = font(FONT_ACTION, 52)
        value_box = draw.textbbox((0, 0), str(value), font=value_face)
        draw.text((left + 205 - value_box[2], 375), str(value), font=value_face, fill=0)
    draw.text((1130, 305), "CECHY", font=font(FONT_ACTION, 27), fill=0)
    draw.text((1130, 350), hero.abilities, font=fit_font(draw, hero.abilities, FONT_ACTION, 27, 1210), fill=0)
    draw.text((1130, 405), hero.attacks, font=fit_font(draw, hero.attacks, FONT_ACTION, 27, 1210), fill=0)

    draw.rectangle((100, 505, page_right, 650), outline=0, width=3)
    draw.text((120, 522), hero.resource, font=fit_font(draw, hero.resource, FONT_ACTION, 27, 2220), fill=0)
    instruction = "KLAWISZ = PODGLĄD  ·  ENTER = WYKONAJ  ·  ESC / BACKSPACE = WRÓĆ BEZ KOSZTU"
    draw.text((120, 580), instruction, font=fit_font(draw, instruction, FONT_BODY, 25, 2220), fill=45)

    common_left, common_right, common_gap = 100, page_right, 12
    common_width = (common_right - common_left - common_gap * (len(COMMON_KEYS) - 1)) // len(COMMON_KEYS)
    for index, (key, label) in enumerate(COMMON_KEYS):
        left = common_left + index * (common_width + common_gap)
        draw_bw_keycap(draw, (left, 695, left + common_width, 755), key)
        label_face = fit_font(draw, label, FONT_ACTION, 22, common_width)
        label_box = draw.textbbox((0, 0), label, font=label_face)
        draw.text((left + (common_width - label_box[2]) // 2, 770), label, font=label_face, fill=0)
    draw.line((100, 825, page_right, 825), fill=0, width=3)

    columns = ((100, 840), (870, 1610), (1640, 2380))
    section_top, action_top, action_bottom = 875, 985, 3360
    for column_index, section in enumerate(hero.sections):
        left, right = columns[column_index]
        draw.rectangle((left, section_top, right, 960), fill=0)
        title_face = fit_font(draw, section.title, FONT_DISPLAY, 37, right - left - 30)
        title_box = draw.textbbox((0, 0), section.title, font=title_face)
        title_y = section_top + (85 - (title_box[3] - title_box[1])) // 2 - title_box[1]
        draw.text((left + 16, title_y), section.title, font=title_face, fill=255)
        draw.rectangle((left, section_top, right, action_bottom), outline=0, width=3)

        count = len(section.actions)
        row_height = (action_bottom - action_top) // max(1, count)
        if count <= 3:
            title_size, meta_size, body_size, body_lines = 32, 24, 27, 4
        elif count <= 4:
            title_size, meta_size, body_size, body_lines = 30, 22, 25, 3
        elif count <= 6:
            title_size, meta_size, body_size, body_lines = 27, 20, 23, 3
        else:
            title_size, meta_size, body_size, body_lines = 25, 18, 20, 3
        for action_index, action in enumerate(section.actions):
            cell_top = action_top + action_index * row_height
            if action_index:
                draw.line((left + 15, cell_top, right - 15, cell_top), fill=150, width=2)
            key_width = 88 if len(action.key) <= 2 else 132
            key_top = cell_top + 22
            draw_bw_keycap(draw, (left + 18, key_top, left + 18 + key_width, key_top + 50), action.key)
            name_x = left + 32 + key_width
            name_face = fit_font(draw, action.name, FONT_ACTION, title_size, right - name_x - 16)
            name_box = draw.textbbox((0, 0), action.name, font=name_face)
            name_y = key_top + (50 - (name_box[3] - name_box[1])) // 2 - name_box[1]
            draw.text((name_x, name_y), action.name, font=name_face, fill=0)
            meta_face = font(FONT_ACTION, meta_size)
            body_face = font(FONT_BODY, body_size)
            y = key_top + 66
            for line in wrap(draw, action.meta, meta_face, right - left - 36):
                draw.text((left + 18, y), line, font=meta_face, fill=45)
                y += meta_size + 5
            y += 3
            for line in wrap(draw, action.body, body_face, right - left - 36)[:body_lines]:
                draw.text((left + 18, y), line, font=body_face, fill=0)
                y += body_size + 5
    return image


def draw_minimal_dossier_section(
    draw: ImageDraw.ImageDraw,
    *,
    title: str,
    body: str,
    box: tuple[int, int, int, int],
    body_size: int = 28,
) -> None:
    x0, y0, x1, _y1 = box
    draw.rectangle(box, outline=0, width=3)
    draw.rectangle((x0, y0, x1, y0 + 65), fill=238)
    draw.line((x0, y0 + 65, x1, y0 + 65), fill=0, width=2)
    draw.text((x0 + 18, y0 + 13), title, font=font(FONT_ACTION, 28), fill=0)
    draw_wrapped_text(
        draw,
        body,
        xy=(x0 + 20, y0 + 85),
        width=x1 - x0 - 40,
        face=font(FONT_BODY, body_size),
        fill=0,
        line_gap=7,
    )


def render_minimal_dossier(hero: Hero) -> Image.Image:
    """Render the matching low-ink narrative and rules page."""

    image = Image.new("L", A4_SIZE_300_DPI, 255)
    draw = ImageDraw.Draw(image)
    profile = HERO_ARCHETYPES_BY_ID[hero.hero_id]
    draw.rectangle((70, 70, 2410, 3438), outline=0, width=3)
    draw.text((100, 105), hero.name, font=font(FONT_DISPLAY, 70), fill=0)
    draw.text((100, 205), "KARTA TESTOWA · HISTORIA I ZASADY POSTACI", font=font(FONT_BODY, 25), fill=70)
    tagline_face = fit_font(draw, profile.tagline, FONT_ACTION, 27, 1040)
    tagline_box = draw.textbbox((0, 0), profile.tagline, font=tagline_face)
    draw.text((2380 - tagline_box[2], 150), profile.tagline, font=tagline_face, fill=0)
    draw.line((100, 270, 2380, 270), fill=0, width=4)

    left, middle, right = 100, 1235, 2380
    draw_minimal_dossier_section(draw, title="HISTORIA", body=profile.history, box=(left, 315, 1195, 850), body_size=29)
    draw_minimal_dossier_section(draw, title="DLACZEGO PODRÓŻUJE", body=profile.motivation, box=(left, 885, 1195, 1395), body_size=28)
    draw_minimal_dossier_section(draw, title="CEL OSOBISTY", body=profile.personal_goal, box=(left, 1430, 1195, 1780), body_size=29)
    strengths = " · ".join(item.capitalize() for item in profile.strengths)
    draw_minimal_dossier_section(draw, title="ATUTY", body=strengths, box=(left, 1815, 1195, 2125), body_size=29)
    resources = "\n".join(f"• {item}" for item in profile.resources)
    draw_minimal_dossier_section(draw, title="ZASOBY I ODNAWIANIE", body=resources, box=(left, 2160, 1195, 3375), body_size=27)

    passives = "\n\n".join(f"{note.name.upper()}\n{note.body}" for note in PASSIVES[hero.hero_id])
    draw_minimal_dossier_section(draw, title="PASYWKI", body=passives, box=(middle, 315, right, 1735), body_size=27)
    flaw = FLAWS[hero.hero_id]
    draw_minimal_dossier_section(draw, title=f"SKAZA · {flaw.name.upper()}", body=flaw.body, box=(middle, 1770, right, 2310), body_size=28)
    turn_plan = "\n\n".join(f"{index}. {item}" for index, item in enumerate(profile.turn_plan, start=1))
    draw_minimal_dossier_section(draw, title="JAK GRAĆ W TURZE", body=turn_plan, box=(middle, 2345, right, 3375), body_size=27)
    return image


def write_minimal_print_set(heroes: Iterable[Hero]) -> None:
    """Write individual and aggregate grayscale PDFs for inexpensive playtests."""

    MINIMAL_PNG_ROOT.mkdir(parents=True, exist_ok=True)
    MINIMAL_PDF_ROOT.mkdir(parents=True, exist_ok=True)
    pages: list[Image.Image] = []
    for hero in heroes:
        keyboard_page = render_minimal_keyboard(hero)
        dossier_page = render_minimal_dossier(hero)
        pages.extend((keyboard_page, dossier_page))
        keyboard_page.save(
            MINIMAL_PNG_ROOT / f"{hero.hero_id}_keyboard_minimal_bw_v1.png",
            dpi=(300, 300),
            compress_level=4,
        )
        dossier_page.save(
            MINIMAL_PNG_ROOT / f"{hero.hero_id}_dossier_minimal_bw_v1.png",
            dpi=(300, 300),
            compress_level=4,
        )
        keyboard_page.save(
            MINIMAL_PDF_ROOT / f"{hero.hero_id}_minimal_bw_v1.pdf",
            "PDF",
            resolution=300.0,
            save_all=True,
            append_images=[dossier_page],
        )
    pages[0].save(
        MINIMAL_PDF_ROOT / "minimal_bw_character_sheets_v1.pdf",
        "PDF",
        resolution=300.0,
        save_all=True,
        append_images=pages[1:],
    )
    thumbs = [page.resize((354, 501), Image.Resampling.LANCZOS) for page in pages]
    contact = Image.new("L", (1416, 2004), 225)
    for index, thumb in enumerate(thumbs):
        contact.paste(thumb, ((index % 4) * 354, (index // 4) * 501))
    contact.save(MINIMAL_ROOT / "minimal_bw_character_sheets_v1_contact.png", compress_level=4)


def on_a4_page(image: Image.Image) -> Image.Image:
    """Center the 2:3 sheet on a true A4 page with a printable white margin."""
    page = Image.new("RGB", A4_SIZE_300_DPI, "white")
    max_width = A4_SIZE_300_DPI[0] - 120
    max_height = A4_SIZE_300_DPI[1] - 120
    scale = min(max_width / image.width, max_height / image.height)
    placed = image.resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    page.paste(
        placed,
        ((page.width - placed.width) // 2, (page.height - placed.height) // 2),
    )
    return page


def write_manifest(heroes: Iterable[Hero]) -> None:
    hero_payloads = []
    for hero in heroes:
        profile = HERO_ARCHETYPES_BY_ID[hero.hero_id]
        payload = asdict(hero)
        payload["shortcuts"] = [asdict(binding) for binding in HERO_SHORTCUTS[hero.hero_id]]
        payload["narrative"] = {
            "tagline": profile.tagline,
            "history": profile.history,
            "motivation": profile.motivation,
            "personal_goal": profile.personal_goal,
            "turn_plan": list(profile.turn_plan),
            "resources": list(profile.resources),
            "strengths": list(profile.strengths),
            "pitfalls": list(profile.pitfalls),
        }
        payload["passives"] = [asdict(note) for note in PASSIVES[hero.hero_id]]
        payload["flaw"] = asdict(FLAWS[hero.hero_id])
        hero_payloads.append(payload)
    payload = {
        "version": 2,
        "control_contract": {
            "idle_ui": "TURA: <postać> · WYBIERZ AKCJĘ NA KARCIE POSTACI.",
            "preview": "Naciśnięcie skrótu otwiera podgląd; nie zużywa akcji ani zasobu.",
            "confirm": "Enter potwierdza.",
            "cancel": "Esc lub Backspace wraca bez kosztu.",
            "reactions": "Gra wyświetla kontekstowe pytanie; reakcje nie mają osobnych skrótów.",
            "nimra_metamagic": "Najpierw wybierz literę metamagicznej modyfikacji, potem literę czaru.",
        },
        "common_keys": [{"key": key, "label": label} for key, label in COMMON_KEYS],
        "page_contract": {
            "page_1": "Skróty, statystyki i opisy aktywnych zdolności.",
            "page_2": "Historia, motywacja, cel, pasywki, skaza i plan tury.",
        },
        "heroes": hero_payloads,
    }
    (ASSET_ROOT / "keyboard_character_cards_v1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    PNG_ROOT.mkdir(parents=True, exist_ok=True)
    PDF_ROOT.mkdir(parents=True, exist_ok=True)
    rendered: list[Image.Image] = []
    pdf_pages: list[Image.Image] = []
    for hero in HEROES:
        keyboard_page = render(hero)
        dossier_page = render_dossier(hero)
        rendered.extend((keyboard_page, dossier_page))
        hero_pdf_pages = (on_a4_page(keyboard_page), on_a4_page(dossier_page))
        pdf_pages.extend(hero_pdf_pages)
        keyboard_page.save(PNG_ROOT / f"{hero.hero_id}_keyboard_sheet_v1.png", dpi=(300, 300), compress_level=4)
        dossier_page.save(PNG_ROOT / f"{hero.hero_id}_dossier_sheet_v1.png", dpi=(300, 300), compress_level=4)
        hero_pdf_pages[0].save(
            PDF_ROOT / f"{hero.hero_id}_keyboard_sheet_v1.pdf",
            "PDF",
            resolution=300.0,
            save_all=True,
            append_images=[hero_pdf_pages[1]],
        )
    pdf_pages[0].save(
        PDF_ROOT / "keyboard_character_sheets_v1.pdf",
        "PDF",
        resolution=300.0,
        save_all=True,
        append_images=pdf_pages[1:],
    )
    thumbs = [image.resize((384, 576), Image.Resampling.LANCZOS) for image in rendered]
    contact = Image.new("RGB", (1536, 2304), (20, 21, 23))
    for index, thumb in enumerate(thumbs):
        contact.paste(thumb, ((index % 4) * 384, (index // 4) * 576))
    contact.save(ASSET_ROOT / "keyboard_character_sheets_v1_contact.png", compress_level=4)
    write_manifest(HEROES)
    write_minimal_print_set(HEROES)


if __name__ == "__main__":
    main()

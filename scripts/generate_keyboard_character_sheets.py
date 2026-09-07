#!/usr/bin/env python3
"""Render print-ready keyboard reference sheets from generated backgrounds."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dnd_board_game.character_creation.archetypes import (  # noqa: E402
    HERO_ARCHETYPES_BY_ID,
)
from dnd_board_game.character_creation.boardgame_help import HERO_FLAWS, HERO_PASSIVES
from dnd_board_game.core.player_labels_pl import player_label
from dnd_board_game.physical_cards.character_card_sets import _starter_builds
from dnd_board_game.inventory import effective_armor_class
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
    source_id: str = ""


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


COMMON_KEYS: tuple[tuple[str, str], ...] = (
    ("SPACJA", "ATAK"),
    ("M", "RUCH"),
    ("B", "BROŃ"),
    ("I", "PRZEDMIOT"),
    ("0", "KONIEC TURY"),
    ("ENTER", "POTWIERDŹ"),
    ("ESC / BACK", "WRÓĆ"),
)


def a(hero_id: str, key: str, meta: str, body: str) -> Action:
    source_id = next(binding.action_ref for binding in HERO_SHORTCUTS[hero_id] if binding.key == key)
    name = {"@hide": "Ukryj się / przerwij skradanie", "@grapple": "Chwyt"}.get(source_id)
    name = name or player_label(source_id)
    actor = _starter_builds()[1][hero_id][1].actor
    spell = next((spell for spell in actor.spells if spell.id == source_id), None)
    if spell is not None and hero_id != "erynd":
        meta += f" · KOMÓRKA {spell.level}+" if spell.level else " · SZTUCZKA"
    return Action(key, name.upper(), meta, body, source_id)


HEROES: tuple[Hero, ...] = (
    Hero(
        "garran", "GARRAN", "CZŁOWIEK · WOJOWNIK · DOWÓDCA", 3, 28, 19, 30,
        "SIŁ 18  ZRC 14  KON 15  INT 9  MDR 13  CHA 11",
        "MIECZ +6 · 1K8+4   |   KUSZA +4 · 1K8+2",
        "ZASOBY: TAKTYKA 4 · DRUGI ODDECH 1 · ZRYW AKCJI 1",
        (91, 135, 168),
        (
            Section("PRZETRWANIE", (
                a('garran', 'Q', 'AKCJA DOD. · 1/ODPOCZYNEK', 'Odzyskaj 1k10 + poziom PW.'),
                a('garran', 'W', 'AKCJA DOD. · 1/ODPOCZYNEK', 'Po wykonaniu akcji odzyskaj akcję.'),
                a('garran', 'E', 'CAŁY RUCH · PRZED RUCHEM · 5 STÓP', 'Sporny test Siły; wygrana: 1k4+SIŁ i odepchnięcie o wolne pole. Remis: obrońca.'),
            )),
            Section("OBRONA I ROZKAZY", (
                a('garran', 'R', 'AKCJA RUCHU', 'Rezygnujesz z ruchu: +2 KP do następnej tury lub do ruchu.'),
                a('garran', 'A', 'AKCJA · 60 STÓP · 1 TAKTYKA', 'MDR ST 14: porażka blokuje ruch, sukces połowi. Naturalne 1: także -2 do ataków; 20: bez efektu.'),
                a('garran', 'S', 'BONUS · 1 TAKTYKA', 'Sąsiedni sojusznicy mają +2 KP do twojej następnej tury.'),
            )),
            Section("WSPARCIE", (
                a('garran', 'D', 'AKCJA · 30 STÓP · 1 TAKTYKA', 'Usuń strach; przewaga przy pierwszym ataku, teście lub rzucie obronnym.'),
                a('garran', 'F', 'AKCJA · 5 STÓP · 1 TAKTYKA', 'Pierwszy pojedynczy atak lub efekt na wybranego sojusznika trafia Garrana.'),
                Action('AUTO', 'REAKCJE', 'GRA WYŚWIETLI PYTANIE', 'Gdy reakcja jest możliwa, wybierz ją w oknie i potwierdź Enterem.'),
            )),
        ),
    ),
    Hero(
        "brakka", "BRAKKA", "PÓŁORKA · BARBARZYNKA · ŁAMACZKA LINII", 3, 35, 14, 30,
        "SIŁ 18  ZRC 13  KON 16  INT 8  MDR 12  CHA 10",
        "TOPÓR +6 · 1K12+4   |   OSZCZEP +6 · 1K6+4",
        "ZASOBY: SZAŁ 3 · DZIKOŚĆ 3 W SZALE · NIEUSTĘPLIWOŚĆ 1",
        (198, 77, 54),
        (
            Section("WEJŚCIE W SZAŁ", (
                a('brakka', 'Q', 'BONUS · 3/DŁUGI ODPOCZYNEK', 'Odnów 3 Dzikości; przewaga testów/obron SIŁ, +2 obrażeń wręcz i odporność na kłute/cięte/obuchowe.'),
                a('brakka', 'W', 'AKCJA · ATAK WRĘCZ', 'Atak z przewagą. Ataki przeciw Brakce mają przewagę do jej następnej tury.'),
            )),
            Section("NACISK", (
                a('brakka', 'E', 'AKCJA · SZAŁ · 2 DZIKOŚCI', 'Wykonaj atak wręcz z premią +10 do trafienia.'),
                a('brakka', 'R', 'AKCJA · 5 STÓP', 'Próba Atletyki. Odepchnij 5 stóp + 5 za każde 5 punktów przewagi, maks. 30.'),
                a('brakka', 'A', 'BONUS · SZAŁ · 1 DZIKOŚCI', 'Podwój bazowy ruch Brakki w tej turze.'),
            )),
            Section("KONTROLA", (
                a('brakka', 'S', 'AKCJA · SZAŁ · STOŻEK 15 · 2 DZIKOŚCI', 'KON ST 15: 2k6 i brak ruchu; sukces pół. Naturalne 1: utrudnienie ataków; 20: brak obrażeń.'),
                Action('AUTO', 'TWARDA JAK SKAŁA', 'REAKCJA · SZAŁ · 1 DZIKOŚCI', 'Po odporności zmniejsz otrzymane obrażenia o 1k12+KON.'),
                a('brakka', 'D', 'AKCJA · 5 STÓP · WOLNA RĘKA', 'Sporny test Atletyki przeciw Atletyce/Akrobatyce. Sukces zeruje ruch celu do uwolnienia.'),
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
                a('mira', 'D', 'AKCJA / DARMOWE WYJŚCIE', 'Test Skradania przeciw Percepcji każdego wroga. Ukrycie: ruch 20 stóp; wyjście przywraca limit 25.'),
                a('mira', 'Q', 'AKCJA · RUCH 15 · 1 FORTEL', 'Bez ataków okazyjnych, potem Ukrycie nawet obok wroga.'),
                a('mira', 'W', 'AKCJA · WRĘCZ', 'Jeśli pole za celem jest wolne: +2 do ataku i obrażeń, potem przejdź za cel.'),
            )),
            Section("KONTROLA", (
                a('mira', 'E', 'AKCJA · PROMIEŃ 45 STÓP', 'Fizyczny test Percepcji wykrywa pułapki w walce.'),
                a('mira', 'R', 'AKCJA · FLANKA · 1 FORTEL', 'Po trafieniu wręcz prędkość celu spada o połowę aż do leczenia.'),
            )),
            Section("SKRYTOBÓJSTWO", (
                a('mira', 'A', 'AKCJA · SOJUSZNIK PRZY CELU · 1 FORTEL', 'Po raniącym trafieniu rapierem zaatakuj osobno wroga dokładnie za pierwszym. Bez dalszego łańcucha.'),
                a('mira', 'S', 'AKCJA · NÓŻ Z UKRYCIA · 1 FORTEL', 'Cel, który cię nie widzi, po raniącym trafieniu krwawi 1k4 na początku tur do leczenia.'),
                Action('AUTO', 'UNIK INSTYNKTOWNY', 'REAKCJA · 1 FORTEL', 'Gdy widoczny wróg atakuje ukrytą Mirę, jego atak ma utrudnienie.'),
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
                a('dagna', 'Q', 'AKCJA · STOŻEK 15 · ZRC ST 14', 'Wrogowie odnoszą 1k8 obrażeń od blasku przy porażce.'),
                a('dagna', 'W', 'BONUS · 60 STÓP', 'Wybrany cel odzyskuje 1k4+7 PW.'),
                a('dagna', 'E', 'AKCJA · AURA 10 · KONC. · 5 RUND', 'Ty i sojusznicy w aurze dodajecie 1k4 do ataków i rzutów obronnych.'),
            )),
            Section("BOSKA MOC", (
                a('dagna', 'R', 'AKCJA · 1 BOSKA MOC', 'Rozdziel 15 PW między cele; nie lecz powyżej połowy maks. PW.'),
                a('dagna', 'A', 'AKCJA · AURA 5 · KONC. · 5 RUND', 'Wrogowie w aurze mają -2 do ataków i obrażeń.'),
                a('dagna', 'S', 'AKCJA · 75 STÓP · ATAK CZAREM', '2k6 blasku; następny atak przeciw celowi ma przewagę.'),
            )),
            Section("CZARY WSPARCIA", (
                a('dagna', 'D', 'AKCJA · AURA 10 · KONC. · 3 RUNDY', 'Cztery pierwsze leczenia w aurze zyskują +1k8+MDR.'),
                a('dagna', 'F', 'AKCJA · DOTYK', 'Usuń jedną obsługiwaną negatywną kondycję.'),
                a('dagna', 'T', 'AKCJA · BOSKA MOC 1 · 30 STÓP', 'Nieumarli wykonują obronę MDR ST 14; porażka odpędza. Dostępne tylko przy legalnym celu.'),
                a('dagna', 'Z', 'BONUS · 60 STÓP', 'Przywołaj broń: ruch 20, atak sąsiedni 1k8+4, KP 18.'),
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
                a('lorian', 'Q', 'BONUS · 60 STÓP', 'Sojusznik zachowuje 1k6 do testu, ataku lub rzutu obronnego.'),
                a('lorian', 'W', 'AKCJA · CAŁY RUCH · 60 STÓP', 'Przed ruchem: dwa strzały w jeden cel, jego KP jest niższe o 2.'),
                a('lorian', 'E', 'AKCJA · 45 STÓP', 'Trafienie: utrudnienie pierwszego ataku celu i jego rzutów MDR.'),
                a('lorian', 'R', 'AKCJA · 45 STÓP', 'Cel zyskuje premię przeciw Lorianowi, lecz karę przeciw innym równą obrażeniom.'),
            )),
            Section("KONTROLA I CZARY", (
                a('lorian', 'A', 'AKCJA · OBSZAR 3×3 · 45 STÓP', 'Wszyscy w obszarze: ZRC; sukces pół ruchu, porażka brak ruchu.'),
                a('lorian', 'S', 'AKCJA · 45 STÓP · MDR ST 14', '2k6 psychicznych i ruch 15 stóp od Loriana; sukces: połowa.'),
                a('lorian', 'D', 'AKCJA · SZEŚCIAN 15 · KON ST 14', '2k8 grzmotu i odepchnięcie 10 stóp; sukces: połowa bez odepchnięcia. Także sojusznicy.'),
                a('lorian', 'F', 'AKCJA · SZEŚCIAN 20 · KONC.', 'ZRC: porażka daje przewagę atakującym i blokuje niewidzialność.'),
            )),
            Section("SCENA I REAKCJE", (
                a('lorian', 'Z', 'AKCJA · 30 STÓP · KONC. · MDR ST 14', 'Porażka: cel pada i jest obezwładniony.'),
                a('lorian', 'X', 'AKCJA · 45 STÓP · MDR ST 14', 'Podejdź/odejdź/milcz; ruch do 15 stóp. Cel odporny na mowę: 1k6 psychicznych bez save, zamiast rozkazu.'),
                a('lorian', 'C', 'AKCJA · KONC. · 3 RUNDY', 'Przy rzuceniu jeden strzał; potem bonus daje trzeci strzał salwy.'),
                Action('AUTO', 'KONTRAPUNKT / OKRZYK / CIĘTE SŁOWA', 'REAKCJE · PYTANIE NA EKRANIE', 'Reakcje: strzał po zranieniu przez inspirowanego sojusznika, redukcja 1k6+2 lub odjęcie k6 od rzutu. Bez kosztu Inspiracji.'),
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
                a('nimra', 'T', '1 PUNKT', 'Wyklucz z obszaru czaru do 4 pól.'),
                a('nimra', 'Y', '1 PUNKT', '+15 stóp zasięgu, maksymalnie 75.'),
                a('nimra', 'U', '1 PUNKT', 'Dodaj jedną bazową kość obrażeń.'),
                a('nimra', 'G', '2 PUNKTY', 'Jeden cel ma utrudnienie pierwszego rzutu obronnego.'),
                a('nimra', 'H', '1 PUNKT', 'Zmień typ: kwas, zimno, ogień, błyskawice lub grzmot.'),
            )),
            Section("CZARY Q–S + J", (
                a('nimra', 'Q', 'AKCJA · 50 STÓP · KON ST 14', '1k8 zimna i -10 stóp ruchu przy porażce.'),
                a('nimra', 'W', 'AKCJA · 40 STÓP · PROMIEŃ 5', 'ZRC: 1k6 kwasu przy porażce.'),
                a('nimra', 'E', 'AKCJA · 45 STÓP · MDR ST 14', '1k6 psychicznych i brak reakcji przy porażce.'),
                a('nimra', 'R', 'AKCJA · STOŻEK 15 · ZRC ST 14', '2k6 ognia; sukces: połowa.'),
                a('nimra', 'A', 'AKCJA · LINIA 30 · SIŁ ST 14', '2k6 mocy i odepchnięcie 5 stóp; sukces: połowa.'),
                a('nimra', 'S', 'AKCJA · 50 · OBSZAR 10 · 3 RUNDY', 'Trudny teren; ZRC przy wejściu/starcie, porażka przewraca.'),
                a('nimra', 'J', 'BONUS · TELEPORT 30 STÓP', 'Wybierz wolne pole w zasięgu.'),
            )),
            Section("CZARY D–V + K", (
                a('nimra', 'D', 'AKCJA · 50 STÓP', 'Pula 5k8 usypia cele od najniższych PW.'),
                a('nimra', 'F', 'AKCJA · 50 · PROMIEŃ 15 · KONC.', 'Obszar jest całkowicie zasłonięty.'),
                a('nimra', 'Z', 'AKCJA · 50 · SZEŚCIAN 20 · KONC.', 'Trudny teren; ZRC przy porażce unieruchamia.'),
                a('nimra', 'X', 'AKCJA · 60 STÓP · ZRC ST 14', '3k6/połowa. Jeden przeskok do najbliższej istoty w 15 stopach, także sojusznika; remis preferuje wroga.'),
                a('nimra', 'C', 'AKCJA · 50 · PROMIEŃ 10 · MDR ST 14', '2k6, brak reakcji i utrudnienie pierwszego ataku; sukces połowa.'),
                a('nimra', 'V', 'AKCJA · 50 · KONC. · MDR ST 14', 'Ruch 0 i brak akcji ruchu; ponawiany rzut, maks. 3 rundy.'),
                a('nimra', 'K', 'AKCJA · OBSZAR · KON ST 14', '3k8 grzmotu; sukces: połowa.'),
            )),
        ),
    ),
    Hero(
        "erynd", "ERYND", "ELF · ŁOWCA · MOBILNY STRZELEC", 3, 25, 16, 30,
        "SIŁ 12  ZRC 19  KON 13  INT 11  MDR 14  CHA 8",
        "DŁUGI ŁUK +8 · 1K8+4   |   NÓŻ +3 · 1K4+1",
        "ZASOBY: INSTYNKT 4 · ZNACZNIK ŁOWCY: +1K6",
        (78, 132, 98),
        (
            Section("POZYCJA", (
                a('erynd', 'Q', 'BONUS · KONC. · 1 INSTYNKT', '+1k6 obrażeń bronią. Po pokonaniu celu przeniesienie jest darmowe.'),
                a('erynd', 'W', 'BONUS', 'Wybierz: Sprint albo Odstąpienie.'),
                a('erynd', 'E', 'CAŁY RUCH · PRZED RUCHEM', 'Następny atak długim łukiem ma przewagę.'),
            )),
            Section("STRZAŁY INSTYNKTU", (
                a('erynd', 'R', 'AKCJA · 1 INSTYNKT · RZUT 1K4', 'Trafienie: SIŁ ST 14; blokada ruchu albo pół ruchu przez wynik rund.'),
                a('erynd', 'A', 'AKCJA · 1 INSTYNKT · RZUT 1K8', 'Trafienie obniża KP celu o wynik do następnej tury Erynda.'),
                a('erynd', 'S', 'AKCJA · 1 INSTYNKT', 'Trafienie odbiera reakcje i utrudnia następny atak celu.'),
            )),
            Section("SALWA I TEREN", (
                a('erynd', 'D', 'AKCJA · 2 INSTYNKTU', 'Jeden test: 2k8 + 2×ZRC. Znak i Pierwsza krew tylko raz; krytyk podwaja wyłącznie bazowe kości.'),
                a('erynd', 'F', 'BONUS · 1 INSTYNKT', 'Teleportuj się na wybrane wolne pole.'),
                a('erynd', 'Z', 'AKCJA · 1 INSTYNKT', 'Utwórz niebezpieczny trudny teren w wybranym obszarze.'),
            )),
        ),
    ),
)


HEROES = tuple(
    replace(hero,
            level=(actor := _starter_builds()[1][hero.hero_id][1].actor).level,
            hp=actor.max_hp, ac=effective_armor_class(actor), speed=actor.speed_feet,
            abilities="  ".join(f"{label} {getattr(actor.ability_scores, ability)}" for ability, label in (
                ("strength", "SIŁ"), ("dexterity", "ZRC"), ("constitution", "KON"),
                ("intelligence", "INT"), ("wisdom", "MDR"), ("charisma", "CHA"),
            )))
    for hero in HEROES
)


PASSIVES = HERO_PASSIVES
FLAWS = HERO_FLAWS


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
        fitted_body_size = body_size
        while True:
            body_face = font(FONT_BODY, fitted_body_size)
            body_lines = wrap(draw, action.body, body_face, inner_right - inner_left)
            text_height = key_height + 8 + len(meta_lines) * (meta_size + 4) + 4 + len(body_lines) * (fitted_body_size + 4)
            if text_height <= cell_bottom - cell_top - 10:
                break
            fitted_body_size -= 1
            if fitted_body_size < 16:
                raise ValueError(f"Opis nie mieści się na karcie: {hero.hero_id} / {action.name}")
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
            y += fitted_body_size + 4


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


def fit_paragraph_font(draw: ImageDraw.ImageDraw, text: str, path: Path, size: int, width: int, height: int) -> ImageFont.FreeTypeFont:
    while size >= 18:
        face = font(path, size)
        needed = sum(size // 2 if not paragraph else len(wrap(draw, paragraph, face, width)) * (size + 7) for paragraph in text.splitlines())
        if needed <= height:
            return face
        size -= 1
    raise ValueError("Tekst dossier nie mieści się w sekcji.")


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
        font=fit_font(draw, title, FONT_CONDENSED_BOLD, 33, x1 - x0 - 48),
        fill=(*hero.accent, 255),
    )
    draw_wrapped_text(
        draw,
        body,
        xy=(x0 + 24, y0 + 66),
        width=x1 - x0 - 48,
        face=fit_paragraph_font(draw, body, FONT_CONDENSED, body_size, x1 - x0 - 48, y1 - y0 - 90),
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
            for line in wrap(draw, action.body, body_face, right - left - 36):
                draw.text((left + 18, y), line, font=body_face, fill=0)
                y += body_size + 5
            if y > cell_top + row_height - 10:
                raise ValueError(f"Opis nie mieści się na karcie BW: {hero.hero_id} / {action.name}")
    return image


def draw_minimal_dossier_section(
    draw: ImageDraw.ImageDraw,
    *,
    title: str,
    body: str,
    box: tuple[int, int, int, int],
    body_size: int = 28,
) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle(box, outline=0, width=3)
    draw.rectangle((x0, y0, x1, y0 + 65), fill=238)
    draw.line((x0, y0 + 65, x1, y0 + 65), fill=0, width=2)
    draw.text((x0 + 18, y0 + 13), title, font=fit_font(draw, title, FONT_ACTION, 28, x1 - x0 - 36), fill=0)
    draw_wrapped_text(
        draw,
        body,
        xy=(x0 + 20, y0 + 85),
        width=x1 - x0 - 40,
        face=fit_paragraph_font(draw, body, FONT_BODY, body_size, x1 - x0 - 40, y1 - y0 - 105),
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


def write_hero_reference(heroes: Iterable[Hero]) -> None:
    """Keep the current descriptive reference synchronized with the print source."""
    lines = [
        "# Siedem archetypów planszowych — aktualne zasady postaci",
        "",
        "Źródło: `scripts/generate_keyboard_character_sheets.py`, profile gry i wspólny katalog `character_creation/boardgame_help.py`.",
        "Dokument jest odtwarzany razem z wydrukami. Poprzednie wersje zestawów są dostępne w historii Git.",
        "",
        "Wszyscy bohaterowie zaczynają na poziomie 3 z premią +2 do głównej cechy, już wliczoną w statystyki. Wybierz 1–5 z siedmiu postaci, potem scenariusz. Awans talii pozostaje osobnym etapem projektu.",
        "",
        "W walce klawisz otwiera podgląd, Enter zatwierdza, Esc lub Backspace wraca bez kosztu. Plansza wskazuje pozycje, cele i obszary. Mysz jest awaryjnym mechanizmem. Działania oznaczone AUTO są proponowanymi reakcjami, nie skrótami.",
        "",
        "Komórka N+ oznacza komórkę co najmniej poziomu N. Sztuczki nie zużywają komórek. Koncentracja utrzymuje jeden efekt naraz; wydanie komórki, zasobu i akcji następuje dopiero przy wykonaniu. Szał odnawia Dzikość; przejście między scenariuszami nie odnawia zasobów.",
        "",
        "W aktualnej grze nie liczymy strzał ani bełtów. Długi łuk Erynda ma +8 do ataku (łącznie z Łucznictwem); nóż Erynda +3, a noże Miry +6 (łącznie z biegłością). Kara skazy Erynda zależy od sojuszników przy wybranym celu.",
        "",
    ]
    for hero in heroes:
        profile = HERO_ARCHETYPES_BY_ID[hero.hero_id]
        lines.extend([f"## {hero.name.title()} — {profile.role}", "",
                      f"PW {hero.hp} · KP {hero.ac} · ruch {hero.speed} stóp. {hero.abilities}.", "",
                      "### Zasoby i plan tury", "",
                      *(f"- {item}" for item in profile.resources), "",
                      *(f"{i}. {item}" for i, item in enumerate(profile.turn_plan, 1)), "",
                      "### Zdolności i skróty", "",
                      "| Klawisz | Zdolność | Koszt i warunki | Działanie |",
                      "|---|---|---|---|"])
        for section in hero.sections:
            for action in section.actions:
                cells = (action.key, action.name.title(), action.meta, action.body)
                lines.append("| " + " | ".join(cell.replace("|", " / ") for cell in cells) + " |")
        lines.extend(["", "### Pasywy i skaza", "",
                      *(f"- **{note.name}:** {note.body}" for note in PASSIVES[hero.hero_id]), "",
                      f"**Skaza — {FLAWS[hero.hero_id].name}:** {FLAWS[hero.hero_id].body}", ""])
    lines.extend(["## Aktualne wydruki", "",
                  "Kolorowe: `assets/physical_cards/character_sets/keyboard_v1/pdf/keyboard_character_sheets_v1.pdf`.",
                  "Oszczędne: `assets/physical_cards/character_sets/keyboard_v1/minimal_bw/pdf/minimal_bw_character_sheets_v1.pdf`.",
                  "Każdy zestaw zawiera siedem par: skróty i dossier. Manifest w `keyboard_v1/keyboard_character_cards_v1.json` wiąże skróty ze stabilnymi identyfikatorami zdolności.", ""])
    (ROOT / "docs/BOARDGAME_ARCHETYPES_LEVELS_1_3.md").write_text("\n".join(lines), encoding="utf-8")


def legacy_main() -> None:
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
    write_hero_reference(HEROES)
    write_minimal_print_set(HEROES)


def main() -> int:
    """Default exports always use the current physical-mana profile."""
    from dnd_board_game.physical_cards.mana_print_files import main as print_current
    return print_current(default_formats=('color', 'minimal'))


if __name__ == "__main__":
    raise SystemExit(main())

"""Shared data and printable modules for the personal rune basket playtest."""
from __future__ import annotations

from dataclasses import replace
from html import escape
from typing import Any

from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.character_creation.runes import apply_rune_profile
from dnd_board_game.physical_cards.mana_print import PrintHero, build_print_hero
from dnd_board_game.physical_cards.rune_prototype import PANEL_SYMBOLS, panel_icon
from dnd_board_game.scenarios.character_text import print_copy
from dnd_board_game.ui.training_arena import training_hero


CSS = """
.page{break-after:page;break-inside:avoid}.page:last-child{break-after:auto}
.basket-page h1,.basket-action-page h1{font-size:23pt}
.basket-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:4mm}
.basket-cell{height:77mm;padding:3mm;border:.45mm solid #333;border-radius:2mm}
.basket-title{display:flex;justify-content:space-between;align-items:baseline;border-bottom:.3mm solid #444;padding-bottom:1mm;margin-bottom:2mm}
.basket-title h2{font-size:16pt;margin:0}.basket-title span{font-size:9pt}
.basket-dice{display:grid;grid-template-columns:1fr 1fr;gap:1mm;font-size:7.3pt;margin-bottom:2mm}
.basket-dice .glyph{width:4mm;height:4mm}.basket-dice b{display:inline-block;min-width:3mm}
.basket-label{font:bold 7pt Arial;text-transform:uppercase;margin:1.4mm 0 .8mm;letter-spacing:.15mm}
.basket-slots{display:flex;gap:3mm}.basket-token{height:15mm;width:17mm;border:.3mm solid #444;border-radius:2mm;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:6pt;line-height:1.1;text-align:center}
.basket-token span{font-size:12pt;color:#888}.basket-token.discharged{border-style:dashed;color:#999}.basket-token.discharged span{color:#aaa}
.basket-example{font-size:6.8pt;margin:1.8mm 0 0;line-height:1.1}
.basket-recovery{margin-top:4mm;padding:2.5mm 3mm;border-left:1mm solid #333;background:#f3f3f3;font-size:8.5pt;line-height:1.25}
.basket-recovery h2{font-size:12pt;margin-bottom:1.5mm}.basket-recovery p{margin-bottom:1.5mm}
.basket-guide{display:grid;grid-template-columns:1fr 1fr;gap:2mm 5mm;margin-top:3mm;font-size:8.2pt;line-height:1.25}.basket-guide h3{font-size:10pt;margin-bottom:1mm}.basket-guide p{margin-bottom:1mm}
.basket-caption{font-size:7.4pt;margin:2mm 0}.basket-note{font-size:7.5pt;margin-top:2mm;line-height:1.25}
.basket-action-grid{display:grid;grid-template-columns:repeat(3,60mm);grid-auto-rows:54mm;gap:4mm 7mm}
.basket-action,.basket-action-slot{width:60mm;height:54mm;border:.3mm solid #333;padding:2mm;display:flex;flex-direction:column;font:7.2pt/1.17 Arial;background:#fff;gap:1.1mm}
.basket-action-slot{border-style:dashed;justify-content:center;align-items:center;text-align:center;color:#777}.basket-action-slot strong{font:24pt Georgia;color:#bbb}.basket-action-slot b{font:13pt Georgia}.basket-action-slot small{font-size:7.5pt}
.basket-action-head{display:flex;gap:1.5mm;align-items:center;min-height:8mm}.basket-action-head h2{font-size:10pt;line-height:1.05;margin:0;flex:1}.basket-button{display:flex;flex-direction:column;align-items:center;min-width:8mm;font-size:5.2pt;line-height:1.1}.basket-button .glyph{width:5mm;height:5mm}
.basket-cost{display:flex;justify-content:space-between;gap:1mm;border-top:.3mm solid #333;border-bottom:.3mm solid #333;padding:1mm 0;font-weight:bold;font-size:8.2pt}
.basket-action p{margin:0}.basket-resonances{border-top:.2mm dotted #777;padding-top:1mm;margin-top:auto;font-size:6.7pt;line-height:1.16}.basket-resonances>div{margin-top:.6mm}.basket-resonances .glyph{width:3.2mm;height:3.2mm}.basket-resonances b{font-weight:700}.basket-action-once{font-size:6.5pt;font-weight:bold}
.basket-action[data-dense="true"]{padding:1.5mm;gap:.5mm}.basket-action[data-dense="true"] .basket-action-head{min-height:6mm}.basket-action[data-dense="true"] .basket-cost{padding:.5mm 0}.basket-action[data-dense="true"] .basket-resonances{padding-top:.5mm}.basket-action[data-dense="true"] .basket-resonances>div{margin-top:.2mm}
.basket-blank{flex:1;background:repeating-linear-gradient(white,white 5mm,#ccc 5.15mm,white 5.3mm)}
"""


def glyph(rune: str) -> str:
    slot = next(i for i, (name, _) in enumerate(PANEL_SYMBOLS) if name == rune)
    return panel_icon(slot)


def build_payload(catalog: dict[str, Any]) -> dict[str, Any]:
    """Join the playtest rules with existing character identity and equipment."""
    copy = print_copy()
    heroes: list[dict[str, Any]] = []
    for hero_id in PLAYABLE_HERO_IDS:
        hero = build_print_hero(hero_id, rune_profile=True)
        actor = apply_rune_profile(training_hero(hero_id))
        equipment = []
        for item in actor.inventory:
            text = copy['equipment'][item.source_ref or item.id]
            equipment.append(dict(id=item.id, name=text.get('name', item.name),
                                  slot=text['slot'], quantity=item.quantity,
                                  effect=text['effect'], detail=text['detail']))
        heroes.append(dict(id=hero_id, name=hero.name, role=hero.role, level=hero.level,
                           hp=hero.hp, ac=hero.ac, speed=hero.speed, initiative=hero.initiative,
                           abilities=hero.abilities, story=hero.story, equipment=equipment,
                           character_line=copy['heroes'][hero_id]['character_line'],
                           portrait=f'../../content/scenarios/misja_0_dzwon/assets/images/comic_v2/{hero_id}.png',
                           **catalog['heroes'][hero_id]))
    return dict(version=catalog['version'], categories=catalog['categories'], rules=catalog['rules'],
                panel=[dict(slot=i, name=name, path=path) for i, (name, path) in enumerate(PANEL_SYMBOLS)],
                heroes=heroes)


def print_hero(hero: dict[str, Any]) -> PrintHero:
    """Use current base statistics and the playtest's revised flaw."""
    return replace(build_print_hero(hero['id'], rune_profile=True),
                   flaw=(hero['flaw']['name'], hero['flaw']['description']))


def basket_content(hero: dict[str, Any], categories: list[dict[str, Any]], rules: dict[str, Any]) -> str:
    cells = []
    for category in categories:
        key, name = category['id'], category['name']
        capacity = hero['capacities'][key]
        mapping = ''.join(f'<span data-d4="{n}"><b>{n}</b> {glyph(rune)} {escape(rune)}</span>'
                          for n, rune in enumerate(category['runes'], 1))
        active = ''.join(f'<div class="basket-token" data-ready-slot="{n}"><span>{n}</span></div>'
                         for n in range(1, capacity + 1))
        spent = ''.join(f'<div class="basket-token discharged" data-spent-slot="{n}"><span>{n}</span></div>'
                        for n in range(1, capacity + 1))
        cells.append(f'<section class="basket-cell" data-category="{key}" data-capacity="{capacity}">'
                     f'<div class="basket-title"><h2>{escape(name)}</h2><span>Pojemność <b>{capacity}</b></span></div>'
                     f'<div class="basket-dice">{mapping}</div><div class="basket-label">Naładowane</div>'
                     f'<div class="basket-slots">{active}</div><div class="basket-label">Rozładowane</div>'
                     f'<div class="basket-slots">{spent}</div><p class="basket-example">Przykład przygotowania: '
                     f'{escape(", ".join(hero["preparation"][key]))}.</p></section>')
    recovery = ''.join(f'<p data-regeneration="{escape(rule["id"])}"><b>□</b> {escape(rule["label"])}</p>'
                       for rule in hero['regeneration'])
    return ('<div class="basket-grid">' + ''.join(cells) + '</div>'
            '<p class="basket-caption">Połóż żetony z wybranymi symbolami. Przy ładowaniu rzuć k4 i dobierz żeton zgodny z tabelą kategorii.</p>'
            f'<section class="basket-recovery"><h2>{panel_icon(21)} Most · zgłoś odnowienie</h2>' + recovery +
            '<p>Po zdarzeniu naciśnij Most i potwierdź warunek. Aplikacja pilnuje limitu raz na rundę, także przy pełnym koszyku.</p></section>'
            f'<div class="basket-guide"><section><h3>{panel_icon(19)} Spirala · Skupienie · {escape(rules["focus_budget"])}</h3>'
            f'<p>{escape(rules["focus_description"])}</p></section>'
            '<section><h3>Rezonans i Wsparcie</h3>'
            f'<p>Najwyżej {rules["max_resonances"]} rezonans na moc. Zużyj wskazany symbol z innej kategorii. '
            f'{escape(rules["support_description"])}</p></section>'
            '<section><h3>Zużycie i ładowanie</h3><p>Przesuń znacznik do rozładowanych tej samej kategorii. '
            'Przy ładowaniu k4 określa nowy symbol. Nie przekraczaj pojemności.</p></section>'
            '<section><h3>Własność i tura</h3><p>Podstawę zawsze płacisz własną runą. '
            'Zwykły ruch i atak nie wymagają run. Skupienie zużywa specjalną; ruch i atak pozostają.</p></section></div>')


def action_mat_content() -> str:
    slots = ''.join(f'<section class="basket-action-slot" data-slot-number="{n}">'
                    f'<strong>{n:02}</strong><b>Miejsce na zdolność</b>'
                    '<small>Karta 60 × 54 mm<br>Przycisk wskazuje mały symbol.<br>Koszt określa kategoria.</small></section>'
                    for n in range(1, 13))
    return ('<div class="basket-action-grid">' + slots + '</div><p class="basket-note">'
            '12 miejsc na wymienne karty. Tura: ruch + atak/przedmiot + specjalna. '
            'Reakcja jest osobnym zasobem. Skupienie znajdziesz na macie koszyków.</p>')


def action_cards_content(hero: dict[str, Any], categories: list[dict[str, Any]]) -> str:
    names = {category['id']: category['name'] for category in categories}
    pieces = []
    for card in hero['cards']:
        resonance = ''.join(f'<div data-resonance="{escape(row["id"])}">{glyph(row["rune"])} '
                            f'<b>{escape(row["rune"])}:</b> {escape(row["description"])}</div>'
                            for row in card['resonances'])
        once = ('<p class="basket-action-once">Raz na walkę.</p>'
                if card.get('once') and 'raz na walkę' not in card['description'].lower() else '')
        dense = len(card['description']) + sum(len(row['description']) for row in card['resonances']) > 350
        pieces.append(f'<section class="basket-action" data-card-id="{escape(card["id"])}" data-category="{card["category"]}" data-dense="{str(dense).lower()}">'
                      f'<div class="basket-action-head"><h2>{escape(card["name"])}</h2>'
                      f'<div class="basket-button">{panel_icon(card["slot"])}<span>Przycisk</span></div></div>'
                      f'<div class="basket-cost"><span>1 własna · {escape(names[card["category"]])}</span>'
                      f'<span>{escape(card["budget"])}</span></div><p>{escape(card["description"])}</p>{once}'
                      f'<div class="basket-resonances"><b>Rezonans · wybierz najwyżej 1</b>{resonance}</div></section>')
    for _ in range(12 - len(pieces)):
        pieces.append('<section class="basket-action"><div class="basket-action-head"><h2>Nowa zdolność</h2></div>'
                      '<p>Przycisk: ........ Kategoria: ........</p><div class="basket-blank"></div>'
                      '<div class="basket-resonances">Rezonans: ................................</div></section>')
    return ('<div class="basket-action-grid">' + ''.join(pieces) + '</div><p class="basket-note">'
            '<b>S</b> — specjalna · <b>A</b> — atak/przedmiot · <b>M</b> — ruch · <b>R</b> — reakcja. '
            'Mały znak wybiera moc na planszy. Dowolny naładowany symbol kategorii opłaca podstawę. '
            'Rezonans zużywa dodatkową runę własną lub wspierającego sojusznika.</p>')


def first_page_tokens(hero: dict[str, Any], categories: list[dict[str, Any]]) -> str:
    cells = []
    for category in categories:
        count = hero['capacities'][category['id']]
        slots = ''.join(f'<span class="first-token" data-token-slot="{n}">{n}</span>' for n in range(1,count+1))
        cells.append(f'<section data-token-category="{category["id"]}"><b>{escape(category["name"])} · {count}</b><div>{slots}</div></section>')
    return '<section class="first-baskets"><h3>Żetony run · własne koszyki</h3><div class="first-baskets-grid">'+''.join(cells)+'</div><p>Połóż naładowane żetony w polach. Zużyte odłóż obok; granice kategorii i symbole śledzi aplikacja.</p></section>'

CSS += """
.first-baskets{margin-top:2mm;border-top:.35mm solid #333;padding-top:2mm}
.first-baskets h3{font:11pt Georgia;margin:0 0 1.5mm}
.first-baskets-grid{display:grid;grid-template-columns:1fr 1fr;gap:2mm 4mm}
.first-baskets-grid section{border:.3mm solid #444;padding:1.5mm 2mm}
.first-baskets-grid b{display:block;font:8pt Arial;margin-bottom:1mm}
.first-baskets-grid section>div{display:flex;gap:2mm}
.first-token{display:inline-flex;align-items:center;justify-content:center;width:15mm;height:15mm;border:.25mm dashed #666;border-radius:50%;color:#999;font:8pt Arial}
.first-baskets p{font:7pt Arial;margin:1mm 0 0}
"""

CSS += "\n.basket-recovery h2 .glyph,.basket-guide h3 .glyph{width:5mm;height:5mm;vertical-align:middle}\n"

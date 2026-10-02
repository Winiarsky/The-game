"""Printable presentation of the accepted directed rune-memory cards."""
from __future__ import annotations

from html import escape
from typing import Any

from dnd_board_game.physical_cards.rune_charges import (
    CSS as CHARGE_CSS,
    action_mat as action_mat,
    glyph,
    hero_rules as hero_rules,
    resonance_glyph,
)

CSS = CHARGE_CSS + '''
.relation-card{font-size:7.4pt;gap:.7mm;line-height:1.16}
.relation-card header{min-height:7mm;padding-bottom:.5mm}
.relation-card .charge-cost{font-size:7.4pt;padding:.6mm 0}
.relation-card .charge-bonus{font-size:6.7pt;line-height:1.13;padding-top:.6mm}
.relation-card .charge-bonus p+p{margin-top:.6mm}
.relation-card .requirement{font-size:6.8pt}
.relation-card .resonance-rune{width:3.5mm;height:3.5mm;border-width:.45mm;margin:0 .2mm}
.relation-card .resonance-rune .glyph{width:2.3mm;height:2.3mm}
.relation-card[data-dense="true"]{font-size:7pt}
.relation-card[data-dense="true"] .charge-bonus{font-size:6.4pt}
.relation-gate{font-weight:bold;border-bottom:.2mm dotted #777;padding-bottom:.5mm}
.relation-guide{font:8pt/1.2 Arial;margin-top:4mm}
.relation-guide h2{font:bold 12pt Georgia;margin:0 0 2mm}
.relation-guide p{margin:0 0 2mm}
.relation-map{display:grid;grid-template-columns:1fr 1fr;gap:1mm 4mm;margin:2mm 0}
.relation-edge{display:flex;align-items:center;gap:1mm;font-size:8pt}
.relation-edge .glyph{width:4mm;height:4mm}
.relation-edge .rune-label{min-width:15mm}
.relation-guide .resonance-rune{width:4mm;height:4mm}
.relation-guide .resonance-rune .glyph{width:2.5mm;height:2.5mm}
.relation-finish{border-top:.25mm solid #555;margin-top:1mm;padding-top:1mm;font-size:6.8pt}
'''


def conditions(runes: list[str]) -> str:
    """Render the AND condition using the same glyphs as the physical panel."""
    return ' + '.join(resonance_glyph(rune) for rune in runes)


def relationship_legend(catalog: dict[str, Any]) -> str:
    pieces = []
    for rune in catalog['rules']['starter_runes']:
        if rune == 'Fala':
            continue
        choices = [name for name in catalog['rules']['rune_relations'][rune] if name != 'Fala']
        pieces.append('<div class="relation-edge">' + glyph(rune) +
                      f'<span class="rune-label">{escape(rune)}</span><b>→</b>' +
                      ''.join(glyph(name) for name in choices) + '</div>')
    return '<div class="relation-map">' + ''.join(pieces) + '</div>'


def action_cards(hero: dict[str, Any], catalog: dict[str, Any]) -> str:
    pieces = []
    for card in hero['cards']:
        requirement = '' if card['requirements'] == 'Brak dodatkowych wymagań.' else (
            f'<p class="requirement">{escape(card["requirements"])}</p>')
        required = card.get('requires_resonance', [])
        gate = ('<p class="relation-gate">Wymaga ' + conditions(required) +
                ' i legalnej kontynuacji.</p>') if required else ''
        bonuses = ''.join('<p>' + conditions(bonus['requires']) + ' ' + escape(bonus['text']) + '</p>'
                          for bonus in card['resonance_bonuses'])
        ending = ('<p class="relation-finish"><b>Wyładowanie:</b> po całej mocy wygasza Rezonans, '
                  'także po pudle. Nie dodaje nowej runy.</p>') if card.get('ends_resonance') else ''
        length = len(card['effect']) + sum(len(bonus['text']) for bonus in card['resonance_bonuses'])
        dense = length > 340
        pieces.append(f'<section class="charge-card relation-card" data-card-id="{escape(card["id"])}" '
                      f'data-dense="{str(dense).lower()}" data-rune="{escape(card["rune"])}">'
                      f'<header>{glyph(card["rune"])}<h2>{escape(card["name"])}</h2></header>'
                      f'<div class="charge-cost"><span>{card["cost"]} ładunków</span><span>{escape(card["budget"])}</span></div>'
                      f'<p class="charge-target">{escape(card["target"])}</p>{requirement}{gate}'
                      f'<p>{escape(card["effect"])}</p>' +
                      ('<div class="charge-bonus">' + bonuses + '</div>' if bonuses else '') + ending + '</section>')
    pieces.append('<section class="charge-card relation-card" data-card-id="focus"><header>' + glyph('Spirala') +
                  '<h2>Skupienie</h2></header><div class="charge-cost"><span>0 ładunków</span><span>S</span></div>'
                  '<p>Natychmiast wygasza Rezonans. Odzyskaj 1k20 własnych ładunków, do maksimum 20.</p>'
                  '<p>Zużywasz akcję specjalną. Zachowujesz zwykły ruch oraz atak albo przedmiot.</p>'
                  '<div class="charge-bonus">Spirala jest przyciskiem Skupienia. Nie dodaje runy do pamięci.</div></section>')
    guide = ('<div class="relation-guide"><h2>Rezonans · pamięć 3 ostatnich run</h2>'
             '<p><b>Ostatnia runa</b> określa kontynuację. <b>Wszystkie trzy</b> spełniają warunki kart; '
             'powtórzenia nie mnożą premii. Pierwsza moc daje efekt podstawowy. '
             'Niepasująca moc czyści pamięć <b>przed działaniem</b> i zaczyna nowy łańcuch.</p>'
             '<p>Przy kontynuacji sprawdź premie przed dodaniem własnej runy. Po całej mocy dopisz ją; '
             'czwarta wypiera najstarszą. Symbole w podwójnej otoczce oznaczają warunki premii. '
             'Wszystkie spełnione premie działają razem; sama runa nie daje globalnego efektu.</p>' +
             relationship_legend(catalog) +
             '<p>' + glyph('Fala') + ' <b>Fala — tylko Nimra:</b> dowolna runa → Fala → dowolna runa. '
             'Zajmuje jedno miejsce pamięci, bez kopiowania lub zastępowania symboli.</p>'
             '<p><b>Wyładowanie:</b> wymaga wskazanych run i kontynuacji; opłata także po pudle, '
             'potem pamięć znika. Efekty o własnym czasie trwania pozostają. '
             '<b>Bez mocy:</b> koniec własnej przytomnej tury wygasza łańcuch.</p>'
             '<p><b>S</b> — specjalna · <b>A+S</b> — atak i specjalna · <b>M+S</b> — cały ruch i specjalna. '
             'Odzysk klasowy: 1k4, raz na bohatera na rundę; 20 ładunków maks. '
             'Nazwy cech oznaczają modyfikatory. Pozostałe runy czekają na rozwój postaci.</p></div>')
    return '<div class="charge-grid">' + ''.join(pieces) + '</div>' + guide

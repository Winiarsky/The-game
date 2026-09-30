"""Printable content for the charge and travelling-resonance card revision."""
from __future__ import annotations

from html import escape
from typing import Any

from dnd_board_game.ui.board_panel_symbols import panel_icon, rune_slot

CSS = '''
.charge-page h1{font-size:23pt}.charge-guide{font:9pt/1.3 Arial}.charge-guide h2{font:bold 13pt Georgia;margin:0 0 2mm}
.charge-guide h3{font:bold 10pt Georgia;margin:0 0 1mm}.charge-guide p{margin:0 0 2mm}
.charge-character .story section{margin-bottom:3mm}.charge-character .story{font-size:9.6pt;line-height:1.35}
.charge-personal{display:grid;grid-template-columns:1fr 1fr;gap:5mm;margin-top:3mm;flex:1;min-height:55mm;font:10.5pt/1.45 Arial}
.charge-personal>section{border:.3mm solid #777;border-top:1mm solid #333;padding:4mm;display:flex;flex-direction:column}
.charge-personal .rule-label{font:8pt Arial;text-transform:uppercase;letter-spacing:.5mm;color:#555;margin-bottom:2mm}
.charge-personal h2{font:bold 16pt/1.1 Georgia;margin:0 0 4mm}
.charge-personal p{margin:0}.charge-personal .passive-description{margin:auto 0}
.recovery-heading{display:flex;justify-content:space-between;align-items:center;gap:3mm;margin-bottom:3mm}
.recovery-heading h2{margin:0;max-width:45mm}.recovery-die{font:bold 19pt Georgia;border:.4mm solid #555;padding:2mm}
.charge-personal ol{list-style:none;counter-reset:trigger;padding:0;margin:auto 0;display:grid;gap:4mm}
.charge-personal li{counter-increment:trigger;display:grid;grid-template-columns:7mm 1fr;gap:2mm;align-items:start}
.charge-personal li:before{content:counter(trigger);font:bold 11pt Georgia;border:.3mm solid #888;border-radius:50%;width:6mm;height:6mm;text-align:center;line-height:6mm}
.charge-rune{display:flex;gap:3mm;border-top:.25mm solid #aaa;padding:2mm 0}
.charge-rune>.glyph{width:7mm;height:7mm;flex:none}.charge-rune p{font-size:8.6pt;margin:0}
.charge-grid{display:grid;grid-template-columns:repeat(3,60mm);grid-auto-rows:54mm;gap:4mm 7mm}
.charge-card,.charge-slot{box-sizing:border-box;width:60mm;height:54mm;border:.3mm solid #333;padding:2mm;display:flex;flex-direction:column;gap:1mm;font:7.8pt/1.2 Arial}
.charge-card h2{font:bold 10pt/1.1 Georgia;margin:0;flex:1}.charge-card p{margin:0}
.charge-card header{display:flex;align-items:center;gap:1.5mm;margin:0;padding:0 0 1mm;min-height:8mm;height:auto;flex:none;border:0}
.charge-card .glyph{width:6mm;height:6mm;flex:none}.charge-cost{padding:1mm 0;border-block:.25mm solid #555;font-weight:bold;display:flex;justify-content:space-between;font-size:7.6pt}
.charge-bonus{border-top:.25mm dotted #888;padding-top:1mm;margin-top:auto;font-size:7pt}
.resonance-rune{display:inline-flex;align-items:center;justify-content:center;width:5.5mm;height:5.5mm;border:.7mm double currentColor;border-radius:50%;vertical-align:middle;margin:0 .5mm;box-sizing:border-box}
.resonance-rune .glyph{width:3.7mm;height:3.7mm}
.charge-target{font-weight:bold}.charge-slot{border-style:dashed;align-items:center;justify-content:center;text-align:center;color:#777}
.charge-slot .glyph{width:12mm;height:12mm}.charge-slot b{font:13pt Georgia}.charge-slot small{font:8pt Arial}
.charge-card .requirement{font-size:7pt}.charge-card[data-dense="true"]{gap:.7mm;font-size:7.4pt}
.charge-card[data-dense="true"] .charge-bonus{font-size:7pt}
.charge-mat h2{font:14pt Georgia;margin:0 0 4mm}
.charge-mat>section+section{margin-top:12mm;border-top:.4mm solid #777;padding-top:5mm}
.charge-goal{display:grid;grid-template-columns:60mm 1fr;gap:7mm;align-items:center}
.goal-slot{width:60mm;height:54mm;border:.3mm dashed #888;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3mm;color:#777;text-align:center}
.goal-slot b{font:14pt Georgia}.goal-slot small{font:8pt Arial}
.goal-track{display:flex;justify-content:space-between;align-items:center;position:relative}
.goal-track:before{content:"";position:absolute;left:5mm;right:5mm;border-top:.3mm solid #aaa}
.goal-step{position:relative;display:block;width:14mm;height:14mm;border:.4mm solid #555;border-radius:50%;background:white}
.charge-reference{margin-top:3mm;font:9pt/1.3 Arial}.charge-reference h2{font:bold 13pt Georgia;margin:0 0 2mm}
.charge-reference p{margin:0 0 2mm}.charge-reference .glyph{width:5mm;height:5mm;vertical-align:middle}
.charge-reference .resonance-rune .glyph{width:3.7mm;height:3.7mm}
.resonance-legend{display:grid;grid-template-columns:1fr 1fr;gap:0 4mm}
.resonance-legend .charge-rune{gap:1.5mm;padding:1mm 0}
.resonance-legend .charge-rune>.glyph{width:5mm;height:5mm}
.resonance-legend h3{font-size:9pt;margin-bottom:.5mm}
.resonance-legend .charge-rune p{font-size:7.6pt;line-height:1.15}
'''


def glyph(name: str) -> str:
    return panel_icon(rune_slot(name))


def resonance_glyph(name: str) -> str:
    """A double halo distinguishes a resonance bonus from its activation rune."""
    return (f'<span class="resonance-rune" role="img" aria-label="Rezonans: {escape(name)}">'
            f'{glyph(name)}</span>')


def hero_rules(hero: dict[str, Any], regeneration_die: int) -> str:
    triggers = ''.join(f'<li><span>{escape(t)}</span></li>' for t in hero['regeneration'])
    return ('<div class="charge-personal"><section class="charge-passive"><p class="rule-label">Pasyw</p>'
            f'<h2>{escape(hero["passive"]["name"])}</h2><p class="passive-description">{escape(hero["passive"]["description"])}</p>'
            '</section>'
            '<section class="charge-recovery"><p class="rule-label">Odnawianie ładunków</p>'
            '<div class="recovery-heading"><h2>Odzysk klasowy</h2>'
            f'<span class="recovery-die">1k{regeneration_die}</span></div>'
            f'<ol>{triggers}</ol></section></div>')


def rune_legend(runes: list[dict[str, Any]]) -> str:
    return '<div class="charge-guide resonance-legend">' + ''.join(
        f'<section class="charge-rune" data-legend-rune="{escape(r["name"])}">{glyph(r["name"])}<div>'
        f'<h3>{escape(r["name"])}</h3><p>{escape(r["description"])}</p></div></section>'
        for r in runes) + '</div>'


def goal_slot() -> str:
    """One physical goal card with a five-step progress track to its right."""
    steps = ''.join(f'<span class="goal-step" aria-label="Postęp {step} z 5"></span>'
                    for step in range(1, 6))
    return ('<div class="charge-goal">'
            '<div class="goal-slot"><b>Cel osobisty</b><small>Miejsce na kartę celu<br>60 × 54 mm</small></div>'
            f'<div class="goal-track" role="group" aria-label="Postęp celu osobistego">{steps}</div></div>')


def action_mat(hero: dict[str, Any]) -> str:
    rows = [(c['rune'], c['name']) for c in hero['cards']] + [('Spirala', 'Skupienie')]
    slots = ''.join(f'<section class="charge-slot">{glyph(rune)}<b>{escape(name)}</b>'
                    '<small>Miejsce na kartę 60 × 54 mm</small></section>' for rune, name in rows)
    return ('<div class="charge-mat"><section><h2>Akcje specjalne</h2>'
            '<div class="charge-grid">' + slots + '</div></section>'
            '<section><h2>Cel osobisty · postęp</h2>' + goal_slot() + '</section></div>')


def action_cards(hero: dict[str, Any], catalog: dict[str, Any]) -> str:
    bonuses = {r['name']: r['short'] for r in catalog['runes']}
    pieces = []
    for card in hero['cards']:
        requirement = '' if card['requirements'] == 'Brak dodatkowych wymagań.' else (
            f'<p class="requirement">{escape(card["requirements"])}</p>')
        dense = sum(len(card[k]) for k in ('effect', 'target', 'requirements')) + len(bonuses[card['rune']]) > 300
        pieces.append(f'<section class="charge-card" data-card-id="{card["id"]}" data-dense="{str(dense).lower()}" '
                      f'data-rune="{escape(card["rune"])}"><header>{glyph(card["rune"])}'
                      f'<h2>{escape(card["name"])}</h2></header><div class="charge-cost">'
                      f'<span>Podst. {card["base_cost"]} / Wzm. {card["enhanced_cost"]}</span><span>{card["budget"]}</span></div>'
                      f'<p class="charge-target">{escape(card["target"])}</p>{requirement}'
                      f'<p>{escape(card["effect"])}</p><div class="charge-bonus">'
                      f'<b>Wzm.</b> {resonance_glyph(card["rune"])} {escape(bonuses[card["rune"]])}</div></section>')
    pieces.append('<section class="charge-card" data-card-id="focus"><header>' + glyph('Spirala') +
                  '<h2>Skupienie</h2></header><div class="charge-cost"><span>0 ładunków</span><span>S</span></div>'
                  '<p>Odzyskaj 1k20 własnych ładunków, do maksimum 20.</p>'
                  '<p>Zużywasz akcję specjalną. Możesz nadal wykorzystać zwykły ruch i atak albo przedmiot.</p>'
                  '<div class="charge-bonus"><b>Wygasza Rezonans.</b> Nie dodaje bonusu Spirali ani nie korzysta z paczki. '
                  'Nie ma trybu wzmocnionego.</div></section>')
    return ('<div class="charge-grid">' + ''.join(pieces) + '</div>'
            '<div class="charge-reference"><h2>Rezonans · bonus za każdą kopię runy</h2>'
            f'<p><b>Wzm.</b> {resonance_glyph("Wieża")} — symbol w podwójnej otoczce oznacza bonus Rezonansu. '
            'Zwykły symbol u góry karty wskazuje przycisk mocy na planszy. '
            '4 / 8 to całkowite koszty trybów w ładunkach, przed dopłatą skazy.</p>'
            + rune_legend(catalog['runes']) +
            '<p><b>S</b> — specjalna · <b>A+S</b> — atak i specjalna · <b>M+S</b> — cały ruch i specjalna.</p></div>')

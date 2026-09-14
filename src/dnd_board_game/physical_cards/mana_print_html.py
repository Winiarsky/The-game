"""A4 layouts with selectable text and explicit page boundaries."""

from __future__ import annotations

from html import escape
from pathlib import Path
from .mana_symbols import mana_symbol, mana_text
from dnd_board_game.ui.board_panel_symbols import PANEL_CONTROLS, panel_icon

from .mana_print import (
    COLORS,
    PROFILE,
    TIMING,
    TURN_REMINDERS,
    PrintAbility,
    PrintHero,
)
from dnd_board_game.rules.exploration_mana_catalog import REMINDER, OBSTACLES, CONDITION_HELP

FORMATS = ("color", "minimal", "cards", "bw_test")
CSS = """
@page { size: A4; margin: 10mm; }
* { box-sizing: border-box; }
body { margin: 0; color: #172129; font: 10pt/1.35 Arial, sans-serif; background: #ddd; }
.page { width: 190mm; height: 277mm; padding: 2mm; margin: 10mm auto; background: white; break-after: page; position: relative; }
.page:last-child { break-after: auto; }
header { border-bottom: 1mm solid #386779; padding-bottom: 3mm; margin-bottom: 4mm; display: flex; justify-content: space-between; align-items: center; gap: 4mm; }
h1 { font: bold 22pt Georgia,serif; margin: 0; } h2 { font-size: 13pt; margin: 3mm 0 2mm; } h3 { font-size: 11pt; margin: 0 0 2mm; }
p { margin: 0 0 2mm; } small,.muted { font-size: 8pt; color: #454b50; }
.stats,.scores { display: flex; gap: 2mm; margin-bottom: 3mm; }
.stats span,.scores span { flex: 1; border: .25mm solid #aaa; padding: 2mm; text-align: center; }
.stats b,.scores b { display: block; font-size: 13pt; }
.columns { display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; }
.controls { display: grid; grid-template-columns: 1fr 1fr; gap: 1mm; }
.controls p { margin: 0; display: flex; align-items: center; gap: 1.5mm; }
.note { margin-bottom: 2mm; } .note b { display: block; }
.box { padding: 3mm; border: .3mm solid #71848a; margin: 3mm 0; background: #edf4f5; }
.flaw { background: #fcf1e9; border-color: #a7795e; }
ul,ol { margin: 2mm 0; padding-left: 5mm; } li { margin-bottom: 2mm; }
.panel-symbol { width: 5mm; height: 5mm; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; vertical-align: middle; }
.cutouts .panel-symbol { width: 8mm; height: 8mm; }
.key { display: inline-block; border: .4mm solid #273941; border-radius: 1mm; padding: .4mm 2mm; font-weight: bold; color: #172129; background: #fff; min-width: 8mm; text-align: center; }
.chip { display: inline-block; border: .25mm solid #555; padding: .3mm 1.4mm; margin: 0 .6mm .6mm 0; font-weight: bold; font-size: 8pt; white-space: nowrap; }
.mana-symbol { display: inline-block; width: 4.5mm; height: 4.5mm; vertical-align: middle; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.mana-legend { display: flex; flex-wrap: wrap; gap: 1mm 3mm; font-size: 8pt; margin: 2mm 0; }
.C { background: #f4cccc; } .N { background: #d1e5fc; } .Z { background: #dbeed5; } .B { background: #fff; } .F { background: #d5d5d5; } .any { background: #ececec; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; }
.ability { height: 55mm; border: .3mm solid #80969d; border-top: 1mm solid #386779; padding: 3mm; break-inside: avoid; font-size: 9.5pt; }
.ability h3 { display: flex; align-items: start; gap: 2mm; font-size: 10.5pt; }
.ability p { line-height: 1.32; }
.exploration-cards .ability {height:auto;min-height:65mm;}
.cutouts .ability { height: 119mm; border: .3mm dashed #666; padding: 5mm; font-size: 13pt; }
.cutouts .ability h3 { font-size: 16pt; } .cutouts .chip { font-size: 11pt; } .cutouts .meta { margin: 4mm 0; }
.meta { margin-bottom: 2mm; font-size: 8pt; }
footer { position: absolute; bottom: 1mm; left: 2mm; right: 2mm; border-top: .2mm solid #bbb; padding-top: 1mm; font-size: 7pt; color: #555; }
.bw { color: black; } .bw .box,.bw .chip,.bw .key { background: white; border-color: black; color: black; } .bw header,.bw .ability { border-color: black; } .bw small,.bw .muted { color: #333; }
.portrait { width: 17mm; height: 21mm; object-fit: cover; object-position: center 20%; }
.screen { max-width: 190mm; margin: 10mm auto; }
@media print { body { background: white; } .page { margin: 0; } .screen { display: none; } }
"""


def chips(cost: tuple[str, ...]) -> str:
    return " ".join(
        f'<span class="chip {"any" if c == "*" else c}">{mana_symbol(c)} {COLORS[c]}</span>'
        for c in cost
    )


def ability_card(card: PrintAbility, hero_name: str) -> str:
    sign = "REAKCJA" if card.panel_slot is None else panel_icon(card.panel_slot)
    return f"""<article class="ability" data-card-id="{escape(card.id)}">
    <h3><span class="key">{sign}</span><span>{escape(card.name)}</span></h3>
    <div class="meta">{escape(hero_name)} · {TIMING[card.timing]}<br>{chips(card.cost)}</div>
    <p>{mana_text(card.description)}</p></article>"""


def page(
    hero: PrintHero,
    title: str,
    body: str,
    number: int,
    *,
    portrait: str = "",
    cutouts: bool = False,
) -> str:
    illustration = f'<img class="portrait" src="{escape(portrait)}" alt="">' if portrait else ""
    return f"""<section class="page{' cutouts' if cutouts else ''}" data-page="{number}">
    <header><div><h1>{escape(hero.name)}</h1><small>{escape(title)} · mana 0.3</small></div>{illustration}</header>
    {body}<footer>{escape(hero.name)} · fizyczna mana 0.3 · {number} · A4, skala 100% · Panel areny · runy v1 · 1 = dowolny kolor</footer></section>"""


def reference_page(hero: PrintHero) -> str:
    stats = "".join(
        f"<span>{name}<b>{value}</b></span>"
        for name, value in (
            ("PW", hero.hp),
            ("KP", hero.ac),
            ("Ruch", f"{hero.speed} ft"),
            ("Inicjatywa", f"{hero.initiative:+d}"),
            ("ST czarów", hero.spell_dc or "—"),
        )
    )
    scores = "".join(
        f"<span>{escape(name)}<b>{value} ({mod:+d})</b></span>"
        for name, value, mod in hero.abilities
    )
    metamagic = ""
    # Balance dense dossiers across both columns without shrinking the print.
    side_passive = hero.id in {"mira", "erynd"}
    main_notes = hero.passives[:-1] if side_passive else hero.passives
    passives = "".join(
        f'<div class="note"><b>{escape(name)}</b>{mana_text(text)}</div>'
        for name, text in main_notes
    )
    mana_note = (
        f'<div class="note"><h2>{escape(hero.passives[-1][0])}</h2>{mana_text(hero.passives[-1][1])}</div>'
        if side_passive else ""
    )
    weapons = "<br>".join(escape(w) for w in hero.weapons)
    controls = "".join(
        f'<p>{panel_icon(slot)} {escape(name)}</p>'
        for slot, name, _ in PANEL_CONTROLS
    )
    return f"""<p>{escape(hero.role)} · poziom {hero.level}</p><div class="stats">{stats}</div><div class="scores">{scores}</div>
    {metamagic}<p><b>Broń — wartości bazowe:</b><br>{weapons}</p>
    <div class="box"><b>Wspólna mana: 25 kart · rynek 5 · pozostałe 20 w talii</b><br>
    Zadeklaruj podbicia i zapłać pełny koszt z rynku na odrzucone przed efektem.
    Na koniec tury uzupełnij wspólny rynek do pięciu kart i potwierdź dobór.
    T: początek następnej tury źródła. O: potwierdzone odświeżenie całej talii.</div>
    <div class="mana-legend">{''.join(f'<span>{mana_symbol(c)} {COLORS[c]}</span>' for c in COLORS)}</div>
    <p class="muted">Jeden symbol kosztu = jedna karta many. Kolory sprawdzacie przy stole. Aplikacja liczy karty i wymaga potwierdzenia płatności.</p>
    <div class="columns"><div><h2>Zdolności pasywne</h2>{passives}</div><div>{mana_note}
    <div class="box flaw"><h2>Skaza: {escape(hero.flaw[0])}</h2>{mana_text(hero.flaw[1])}</div>
    <h2>Sterowanie</h2><div class="controls">{controls}</div><p class="muted">Ikona w aplikacji otwiera podgląd. Reakcje wybierasz w ich oknie. −, +, ✓ i ↩ działają w dotychczasowym rogu planszy.</p><p class="muted">Dolny pasek mapy jest wyłączony; wydrukowane runy zostają na przyszłość.</p>
    </div></div>"""


def dossier_page(hero: PrintHero) -> str:
    story = "".join(f"<h2>{escape(title)}</h2><p>{escape(text)}</p>" for title, text in hero.story)
    equipment = ", ".join(escape(item) for item in hero.equipment)
    return f"""<div class="columns"><div>{story}</div><div><h2>Ekwipunek początkowy</h2><p>{equipment}</p>
    <h2>Rzuty obronne</h2><p>{' · '.join(escape(s) for s in hero.saves)}</p>
    <h2>Biegłości</h2><p>{' · '.join(escape(s) for s in hero.skills)}</p></div></div>"""


def turn_rules_page(hero: PrintHero) -> str:
    reminders = "".join(f"<li>{escape(text)}</li>" for text in TURN_REMINDERS)
    controls = "".join(
        f'<div class="note"><b>{panel_icon(slot)} {escape(title)}</b>{mana_text(text)}</div>'
        for slot, title, text in PANEL_CONTROLS
    )
    return f'<div class="columns"><div><h2>Karty i kolejność tury</h2><ol>{reminders}</ol></div><div><h2>Sterowanie i akcje podstawowe</h2>{controls}<p>Dolny pasek mapy jest wyłączony. Używaj ikon na ekranie i przycisków w rogu.</p></div></div>'


def exploration_page(hero: PrintHero) -> str:
    cards = ''.join(f'<article class="ability" data-exploration-id="{escape(m.id)}">'
        f'<h3>{escape(m.name)}</h3><p>{"Rozmowa z NPC" if m.kind == "npc" else "Interakcja z obiektem"} · {escape(hero.name)}</p>'
        f'<p><b>{escape(m.ability)} · test {m.modifier:+d}</b></p>'
        f'<p>{escape(m.description)}</p><p class="muted">' +
        ' · '.join(f'{escape(label)} {value:+d}' for label, value in m.components) +
        '</p><p>Dodaj premię za karty. Dokładnie 21: sukces. Przekroczenie: utrudnienie, bez premii za karty.</p></article>'
        for m in hero.exploration)
    obstacles = ''.join(f'<li><b>{escape(name)}:</b> {escape(body)}</li>' for key, name, body in OBSTACLES if key != 'none')
    return (f'<div class="grid exploration-cards">{cards}</div><h2>Eksploracja — wspólna procedura</h2><p>{escape(REMINDER)}</p>'
            f'<p>Profil metody odsłania się po rozpoczęciu. Wybór wykonawcy jest stały. Jedna jawna przeszkoda na próbę:</p><ul>{obstacles}</ul>'
            '<p><b>Pułapki w walce:</b> zwykły test MDR (Percepcja) wykrywa, ZRĘ (narzędzia) dezaktywuje. Koszt akcji i pozycja obowiązują. Bez dobierania do 21.</p>')


def render_hero_html(hero: PrintHero, format_id: str, *, portrait_path: Path | None = None) -> str:
    if format_id not in FORMATS:
        raise ValueError(f"Nieznany format: {format_id}")
    bw = format_id in {"minimal", "bw_test"}
    cutouts = format_id in {"cards", "bw_test"}
    portrait = portrait_path.resolve().as_uri() if portrait_path and not bw else ""
    pages = [page(hero, "Karta postaci i sterowanie", reference_page(hero), 1, portrait=portrait)]
    cards = hero.cards
    per_page = 4 if cutouts else 8
    for offset in range(0, len(cards), per_page):
        body = (
            '<div class="grid">'
            + "".join(ability_card(card, hero.name) for card in cards[offset : offset + per_page])
            + "</div>"
        )
        pages.append(
            page(
                hero,
                "Zdolności · podbicia dolicz do kosztu bazowego",
                body,
                len(pages) + 1,
                cutouts=cutouts,
            )
        )
    pages.append(
        page(hero, "Historia, ekwipunek i zasady tury", dossier_page(hero), len(pages) + 1)
    )
    pages.append(page(hero, "Wspólny rynek i kolejność rozstrzygania", turn_rules_page(hero), len(pages) + 1))
    pages.append(page(hero, "Eksploracja · NPC i obiekty", exploration_page(hero), len(pages) + 1))
    condition_body = '<p>Jedna jawna zasada na rozmowę. Przeczytaj stawkę przed wyborem metody.</p>' + ''.join(
        f'<h2>{escape(title)}</h2><p>{escape(body)}</p>' for title, body in CONDITION_HELP)
    condition_body += '<p><b>Plansza:</b> Klucz i Gwiazda — wybory warunku. Kolory, pas i dobór mają własne runy. Rzuty: fokus jednej kości, −/+, ✓ dalej, podsumowanie i poprawka przez ↩. Końcowe ✓ rozstrzyga test.</p>'
    pages.append(page(hero, 'Rozmowy · cztery warunki', condition_body, len(pages) + 1))
    return f"""<!doctype html><html lang="pl"><meta charset="utf-8"><title>{escape(hero.name)} — mana 0.3 — {format_id}</title>
    <style>{CSS}</style><body class="{'bw' if bw else 'color'}" data-profile="{PROFILE}">
    <nav class="screen"><button onclick="print()">Drukuj / zapisz PDF</button> A4 · 100% · tło włączone w wersji kolorowej.</nav>{''.join(pages)}</body></html>"""

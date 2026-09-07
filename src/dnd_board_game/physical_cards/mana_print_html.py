"""A4 layouts with selectable text and explicit page boundaries."""

from __future__ import annotations

from html import escape
from pathlib import Path
from .mana_symbols import mana_symbol, mana_text

from .mana_print import (
    COLORS,
    COMMON_KEYS,
    PROFILE,
    TIMING,
    TURN_REMINDERS,
    PrintAbility,
    PrintHero,
)

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
.note { margin-bottom: 2mm; } .note b { display: block; }
.box { padding: 3mm; border: .3mm solid #71848a; margin: 3mm 0; background: #edf4f5; }
.flaw { background: #fcf1e9; border-color: #a7795e; }
ul,ol { margin: 2mm 0; padding-left: 5mm; } li { margin-bottom: 2mm; }
.key { display: inline-block; border: .4mm solid #273941; border-radius: 1mm; padding: .4mm 2mm; font-weight: bold; color: #172129; background: #fff; min-width: 8mm; text-align: center; }
.chip { display: inline-block; border: .25mm solid #555; padding: .3mm 1.4mm; margin: 0 .6mm .6mm 0; font-weight: bold; font-size: 8pt; white-space: nowrap; }
.mana-symbol { display: inline-block; width: 4.5mm; height: 4.5mm; vertical-align: middle; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.mana-legend { display: flex; flex-wrap: wrap; gap: 1mm 3mm; font-size: 8pt; margin: 2mm 0; }
.C { background: #f4cccc; } .N { background: #d1e5fc; } .Z { background: #dbeed5; } .B { background: #fff; } .F { background: #d5d5d5; } .any { background: #ececec; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; }
.ability { height: 55mm; border: .3mm solid #80969d; border-top: 1mm solid #386779; padding: 3mm; break-inside: avoid; font-size: 9.5pt; }
.ability h3 { display: flex; align-items: start; gap: 2mm; font-size: 10.5pt; }
.ability p { line-height: 1.32; }
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
    key = "REAKCJA" if card.key == "AUTO" else card.key
    return f"""<article class="ability" data-card-id="{escape(card.id)}">
    <h3><span class="key">{escape(key)}</span><span>{escape(card.name)}</span></h3>
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
    <header><div><h1>{escape(hero.name)}</h1><small>{escape(title)} · mana 0.2</small></div>{illustration}</header>
    {body}<footer>{escape(hero.name)} · fizyczna mana 0.2 · {number} · A4, skala 100% · Symbol 1 = dowolny kolor</footer></section>"""


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
    metamagic = (
        "<p><b>Metamagia:</b> najwyżej jedna modyfikacja na czar. Wybierz jej literę, następnie czar; opłać oba koszty.</p>"
        if hero.id == "nimra"
        else ""
    )
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
        f'<p><span class="key">{escape(k)}</span> {escape("Ruch: 1 mana; przy starcie obok wroga 2" if hero.id == "garran" and k == "M" else name)}</p>'
        for k, name, _ in COMMON_KEYS
    )
    return f"""<p>{escape(hero.role)} · poziom {hero.level}</p><div class="stats">{stats}</div><div class="scores">{scores}</div>
    {metamagic}<p><b>Broń — wartości bazowe:</b><br>{weapons}</p>
    <div class="box"><b>Mana: start 3 · maksymalnie {hero.capacity} kart w ręce</b><br>
    Na końcu tury: rozlicz skazę, zachowaj do {hero.keep} niewydanych kart, resztę odrzuć.
    Dobierz do 3 nowych kart z rynku — możesz mieć łącznie {hero.capacity}.
    Uzupełnij rynek dopiero po doborze. Początek tury: bez doboru.</div>
    <div class="mana-legend">{''.join(f'<span>{mana_symbol(c)} {COLORS[c]}</span>' for c in COLORS)}</div>
    <p class="muted">Jeden symbol kosztu = jedna karta many. Karty wydajesz przy stole; aplikacja nie sprawdza płatności.</p>
    <div class="columns"><div><h2>Zdolności pasywne</h2>{passives}</div><div>{mana_note}
    <div class="box flaw"><h2>Skaza: {escape(hero.flaw[0])}</h2>{mana_text(hero.flaw[1])}</div>
    <h2>Sterowanie</h2><div class="controls">{controls}</div><p class="muted">Reakcję wybierasz w oknie aplikacji. Mysz służy jako wejście awaryjne.</p>
    </div></div>"""


def dossier_page(hero: PrintHero) -> str:
    story = "".join(f"<h2>{escape(title)}</h2><p>{escape(text)}</p>" for title, text in hero.story)
    reminders = "".join(f"<li>{escape(text)}</li>" for text in TURN_REMINDERS)
    equipment = ", ".join(escape(item) for item in hero.equipment)
    controls = "".join(
        f'<div class="note"><b>{escape(key)} · {escape(title)}</b>{mana_text(hero.flaw[1] + " Trudny teren zwiększa koszt w stopach; 1 pole = 5 ft." if hero.id == "garran" and key == "M" else text)}</div>'
        for key, title, text in COMMON_KEYS[:5]
    )
    return f"""<div class="columns"><div>{story}<h2>Ekwipunek początkowy</h2><p>{equipment}</p>
    <h2>Rzuty obronne</h2><p>{' · '.join(escape(s) for s in hero.saves)}</p>
    <h2>Biegłości</h2><p>{' · '.join(escape(s) for s in hero.skills)}</p></div>
    <div><h2>Jak rozliczyć turę</h2><ol>{reminders}</ol><h2>Akcje podstawowe</h2>{controls}</div></div>"""


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
                "Zdolności · MOD modyfikuje czar/atak, jego koszt płacisz osobno",
                body,
                len(pages) + 1,
                cutouts=cutouts,
            )
        )
    pages.append(
        page(hero, "Historia, ekwipunek i zasady tury", dossier_page(hero), len(pages) + 1)
    )
    return f"""<!doctype html><html lang="pl"><meta charset="utf-8"><title>{escape(hero.name)} — mana 0.2 — {format_id}</title>
    <style>{CSS}</style><body class="{'bw' if bw else 'color'}" data-profile="{PROFILE}">
    <nav class="screen"><button onclick="print()">Drukuj / zapisz PDF</button> A4 · 100% · tło włączone w wersji kolorowej.</nav>{''.join(pages)}</body></html>"""

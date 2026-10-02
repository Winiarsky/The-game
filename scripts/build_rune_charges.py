"""Build the v0.2 charge cards and map; leave combat mechanics and mockup unchanged."""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
from html import escape
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import build_hero_mats as mats
import build_rune_baskets as baskets
import build_rune_prototype as previous
from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.character_creation.runes import apply_rune_profile
from dnd_board_game.physical_cards.mana_print import build_print_hero
from dnd_board_game.physical_cards.mana_print_files import merge_pdfs, render_pdf
from dnd_board_game.physical_cards.rune_charges import (
    CSS, action_cards, action_mat, glyph, hero_rules,
)
from dnd_board_game.scenarios.character_text import print_copy
from dnd_board_game.scenarios.rune_charge_catalog import load_rune_charge_catalog
from dnd_board_game.ui.board_panel_symbols import SYMBOLS, rune_slot
from dnd_board_game.ui.training_arena import training_hero

OUTPUT = ROOT / 'content/scenarios/misja_0_dzwon/print/runy_ladunki_v02'
PAGES_PER_HERO = 5
VALIDATE = baskets.VALIDATE.replace('.basket-action-slot', '.charge-slot').replace(
    '.basket-action', '.charge-card').replace('.basket-cell', '.charge-personal section')
VALIDATE = VALIDATE.replace('.charge-card,.charge-slot', '.charge-card,.charge-slot,.goal-slot')


def page(title: str, subtitle: str, number: str, content: str) -> str:
    return ('<article class="page charge-page">' + mats.base.header(escape(title), escape(subtitle), number,
            imprint='ŁADUNKI I REZONANS · V0.2') + content +
            mats.base.footer('Runy v0.2 · karty do testu · A4, 100%') + '</article>')


def render_hero(hero_id: str, catalog: dict[str, Any], output: Path = OUTPUT) -> str:
    hero = deepcopy(catalog['heroes'][hero_id])
    copy = print_copy()
    base = build_print_hero(hero_id, rune_profile=True)
    story = tuple((label, text) for label, text in base.story if label != 'Cel osobisty')
    story += ((hero['vignette']['title'], hero['vignette']['text']),)
    model = replace(base, flaw=(hero['flaw']['name'], hero['flaw']['description']), story=story)
    actor = apply_rune_profile(training_hero(hero_id))
    for card in hero['cards']:
        for source, ability in [('Siły','Siła'),('Mądrości','Mądrość'),('Charyzmy','Charyzma'),('Inteligencji','Inteligencja')]:
            base_dc = catalog['rules']['save_dc_base']
            card['effect'] = card['effect'].replace(f'ST {source}', f'ST {base_dc} + {ability}')
    character = baskets.body_only(mats.character_page(model, {
        **copy['heroes'][hero_id], 'flaw': hero['flaw']['description']}, output))
    character = character.replace('01 / 04', '01 / 05').replace('ZESTAW 02', 'RUNY V0.2')
    character = character.replace('bez nasycenia', 'wartość bazowa')
    character = character.replace('class="page character-page"', 'class="page character-page charge-character"')
    character = re.sub(r'<section class="commitments">.*?</section>',
                       hero_rules(hero, catalog['rules']['regeneration_die']), character, flags=re.S)
    equipment = baskets.body_only(mats.equipment_page(model))
    equipment = equipment.replace('04 / 04', '03 / 05').replace('ZESTAW 02', 'RUNY V0.2')
    equipment = equipment.replace('Znaczniki zajętej drugiej ręki są w osobnym pliku znaczniki_A4.pdf.',
                                  'Dla sprzętu oburęcznego zaznacz zajętą drugą rękę.')
    cutouts = baskets.body_only(mats.equipment_cutouts(model, copy['equipment'], output, actor=actor))
    cutouts = cutouts.replace('WYCINANKI', '05 / 05').replace('ZESTAW 02', 'RUNY V0.2').replace('Osobne noże mają osobne żetony. ', '')
    cutouts = cutouts.replace('Wspólne zasady znajdziesz w sciaga_graczy_A4.pdf, a znaczniki i legendę w znaczniki_A4.pdf.',
                              'Cel osobisty i jego postęp: strona 2. Bonusy wszystkich 10 run: strona 4.')
    parts = [character,
             page(f'{model.name} · zdolności',
                  'Zdolności i cel osobisty · nie wycinaj', '02 / 05',
                  action_mat(hero)),
             equipment,
             page(f'{model.name} · wytnij zdolności', 'Karty 60 × 54 mm · tnij po zewnętrznych liniach', '04 / 05', action_cards(hero, catalog)),
             cutouts]
    return ('<!doctype html><html lang="pl"><meta charset="utf-8"><title>' + escape(model.name) +
            ' · ładunki i Rezonans</title><style>' + mats.base.CSS + mats.EXTRA_CSS + CSS +
            '</style><body>' + ''.join(parts) + '</body></html>')


def render_index(output: Path, catalog: dict[str, Any], manifest: dict[str, Any],
                 *, cards_output: Path = OUTPUT) -> str:
    def link(path: Path, label: str) -> str:
        return f'<a href="{escape(os.path.relpath(path, output), quote=True)}">{escape(label)}</a>'

    rows = []
    for section in manifest['sections']:
        hero = catalog['heroes'][section['hero']]
        choices = ', '.join(r for r in catalog['rules']['starter_runes'] if r in {c['rune'] for c in hero['cards']})
        links = [link(cards_output / f'{section["hero"]}.html', 'Podgląd HTML')]
        if manifest['pdf']:
            links.insert(0, link(cards_output / f'{section["hero"]}.pdf', f'PDF · {section["pages"]} stron'))
        rows.append(f'<tr><th scope="row">{escape(section["name"])}</th><td>{len(hero["cards"])}</td>'
                    f'<td>{escape(choices)}</td><td>{" · ".join(links)}</td></tr>')
    bonus_rows = ''.join(f'<li>{glyph(r["name"])} <b>{escape(r["name"])}:</b> {escape(r["description"])}</li>'
                         for r in catalog['runes'])
    download = ('<p class="download">' + link(cards_output / 'karty_postaci_A4.pdf', f'Wszystkie karty · {manifest["pages"]} stron A4') + '</p>') if manifest['pdf'] else ''
    return '''<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Przy stole · ładunki i Rezonans v0.2</title><style>
*{box-sizing:border-box}body{max-width:1000px;margin:40px auto;padding:0 24px;background:#f3f0e8;color:#262a26;font:17px/1.6 system-ui}
h1,h2{font-family:Georgia;line-height:1.25}h2{margin-top:30px}a{color:#354e3e;text-underline-offset:3px}
a:focus-visible{outline:3px solid #958058;outline-offset:4px}.note{border-left:3px solid #958058;padding:12px 20px;background:#fff}
.download a{display:inline-block;background:#354e3e;color:white;padding:12px 20px;border-radius:4px;font-weight:650}
.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;background:#fff}th,td{text-align:left;padding:10px;border-bottom:1px solid #d6d4ca}
thead{background:#e5e6dc}li{margin:8px 0}.glyph{height:26px;width:26px;fill:none;stroke:currentColor;stroke-width:1.5;vertical-align:middle}
.edition{font-size:14px;color:#535b53}footer{margin:32px 0;border-top:1px solid #ccc;padding-top:16px}
</style></head><body><main><p class="edition">Materiały do gry · 29.09.2026 · etap 1: karty</p>
<h1>Ładunki i przekazywany Rezonans</h1>
<p>20 własnych ładunków na początku walki. Po cztery moce na bohatera, pięć u Nimry.
Każda moc ma tryb podstawowy za 4 i wzmocniony za 8 ładunków łącznie; skaza może wymagać dopłaty.</p>
<p class="note"><b>Najpierw karty, potem UI walki.</b> Ten zestaw opisuje nową wersję do uzgodnienia i testów przy stole.
Mechanika ładunków i przekazywanego Rezonansu nie jest jeszcze wdrożona w aplikacji ani w makiecie.</p>
''' + download + '<h2>Makieta interfejsu</h2><p>' + link(ROOT / 'docs/ui/prototype.html', 'Otwórz wcześniejszą makietę UI') + '''</p>
<p>Zachowany układ jest podstawą kolejnego kroku. Teraz pracujemy nad kartami; eksploracja pozostaje poza zakresem tych zmian.</p>
<h2>Karty siedmiu postaci</h2><div class="table-wrap"><table><thead><tr><th>Bohater</th><th>Moce</th><th>Runy początkowe</th><th>Materiały</th></tr></thead><tbody>
''' + ''.join(rows) + '''</tbody></table></div><p>Każdy zestaw to <b>3 planszetki + 2 arkusze wycinanek</b>: postać z pasywem i odzyskiem,
pionowa mata zdolności i jednego celu z torem pięciu pól, mata wyposażenia, wycinanki mocy oraz wycinanki sprzętu.
Ładunki gracz śledzi pokrętłem; docelowo ich liczbę pokaże również aplikacja.
Symbol runy w podwójnej otoczce oznacza bonus Rezonansu. Skupienie to osobna wspólna opcja, poza liczbą mocy postaci.</p>
<h2>Dziesięć run w przesuniętych zestawach</h2><p>Każdy następny bohater zaczyna o jedną runę dalej w ciągu: Wieża → Grot → Schody → Błysk → Hak → Oko → Kielich → Węzeł → Fala → Klepsydra. Nimra bierze pięć kolejnych run, pozostali po cztery. To podział kart, nie kolejność inicjatywy ani rozmieszczenie przycisków.</p><ul>''' + bonus_rows + '''</ul>
<p><b>Rezonans trwa wspólnie.</b> Bohater dołącza na początku swojej tury; jego premie działają też poza turą.
Zatwierdzenie mocy wzmocnionej dodaje runę przed wykonaniem mocy. Pierwsza runa rozpoczyna efekt od razu.
Podstawowa moc kończy Rezonans po rozpatrzeniu; Skupienie od razu, a tura bez mocy — na końcu.
Zakończenie usuwa premie wszystkich uczestników i spowolnienie wrogów. Obrażenia, odzyskane PW i wykonany ruch pozostają.</p>
<p>Grot obejmuje każde obrażenia pochodzące od uczestnika, Oko wszystkie jego k20.
Kielich to tymczasowe PW, Klepsydra to osobna prewencja obrażeń poza umysłowymi.
Fala powiela poprzednią runę na torze. Szczegóły Haka i przyszłego UI są w specyfikacji poniżej.</p>
<p><b>Skupienie — Spirala:</b> akcja specjalna, odzysk 1k20, do 20.
<b>Odzysk klasowy:</b> dwa warunki na postać, wspólny limit jednego rzutu 1k4 na rundę.</p>
<h2>Plansza i mapowanie</h2><p>Gwiazda jest przed +/−, w dawnym pustym polu.
Jej dawne miejsce zajmuje Iskra, zarezerwowana na rozwój. Pozostałe symbole zachowują swoje pozycje.
Panel ma 20 run, Gwiazdę informacji, 4 akcje podstawowe, +/−/✓/↩ i jedną przerwę — 30 pól.</p><ul><li>
''' + link(previous.OUTPUT / 'plansza_A4.pdf', 'Plansza z nową pozycją Gwiazdy · 12 stron A4') + '</li><li>' + link(previous.OUTPUT / 'plansza_panel_D3_A4.pdf', 'Sama poprawka panelu — arkusz D3 · 1 strona A4') + '</li><li>' + link(previous.OUTPUT / 'misja_0_kafle_A4.pdf', 'Kafle Misji 0') + '''</li></ul>
<p><b>Druk czarno-biały A4, jednostronnie, 100%, bez dopasowania.</b>
Plansza i kafle mają dotychczasową korektę +3%; nie dodawaj jej drugi raz. Zakładki 10 mm służą do sklejenia.
Zdolności: 60 × 54 mm; sprzęt: 60 × 42 mm.</p><footer><p>
''' + link(ROOT / 'docs/RUNE_CHARGES_CARDS_V02.md', 'Ustalenia kart, bonusy i następny krok') + ' · ' + link(ROOT / 'docs/RESONANCE_RUNTIME_SPEC.md', 'Specyfikacja ciągłego Rezonansu i obsługi Haka') + '</p></footer></main></body></html>\n'


def write_indexes(output: Path, catalog: dict[str, Any], manifest: dict[str, Any]) -> None:
    targets = [output]
    if output.resolve() == OUTPUT.resolve():
        targets += [previous.OUTPUT, baskets.OUTPUT]
    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
        (target / 'index.html').write_text(render_index(target, catalog, manifest, cards_output=output), encoding='utf-8')


def build(*, output: Path = OUTPUT, html_only: bool = False, maps: bool = False) -> dict[str, Any]:
    catalog = load_rune_charge_catalog()
    output.mkdir(parents=True, exist_ok=True)
    sections, parts, checks = [], [], {}
    for hero_id in PLAYABLE_HERO_IDS:
        path = output / f'{hero_id}.html'
        path.write_text(render_hero(hero_id, catalog, output), encoding='utf-8')
        if not html_only:
            checks[hero_id] = baskets.validate(path, script=VALIDATE)
            (output / 'validation.json').write_text(json.dumps(checks, indent=2) + '\n')
            if checks[hero_id]:
                raise RuntimeError(f'{hero_id}: {checks[hero_id]}')
            pdf = path.with_suffix('.pdf')
            render_pdf(path, pdf)
            if mats.pdf_pages(pdf) != PAGES_PER_HERO:
                raise RuntimeError(f'{hero_id}: oczekiwano {PAGES_PER_HERO} stron.')
            mats.compact_pdf(pdf)
            parts.append(pdf)
        sections.append(dict(hero=hero_id, name=build_print_hero(hero_id).name, pages=PAGES_PER_HERO,
                             first_page=PAGES_PER_HERO * len(sections) + 1, powers=len(catalog['heroes'][hero_id]['cards'])))
        print(f'{hero_id}: {PAGES_PER_HERO} stron' + (' HTML' if html_only else ', PDF i układ poprawne'), flush=True)
    manifest = dict(version=2, profile='rune_charges_v02', stage='cards_only', resonance_model=catalog['rules']['resonance_model'], pages=PAGES_PER_HERO * len(sections), sections=sections,
                    pdf=not html_only, layout_validated=not html_only, action_mm=[60,54], equipment_mm=[60,42],
                    panel=[dict(slot=i,name=name,board=[19,29-i]) for i,(name,_) in enumerate(SYMBOLS)])
    if parts:
        merge_pdfs(parts, output / 'karty_postaci_A4.pdf')
        if mats.pdf_pages(output / 'karty_postaci_A4.pdf') != manifest['pages']:
            raise RuntimeError(f"Komplet powinien mieć {manifest['pages']} stron.")
        mats.compact_pdf(output / 'karty_postaci_A4.pdf')
    if maps:
        previous.build_maps()
    (output / 'characters_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (output / 'README.md').write_text('# Runy v0.2 — ładunki i Rezonans\n\n'
        '[Spis materiałów](index.html). 7 postaci, 29 mocy, 35 stron A4. Po 3 planszetki i 2 arkusze wycinanek na bohatera. '
        'Ładunki: fizyczne pokrętło gracza i docelowo licznik w aplikacji; bez toru na karcie. '
        'Karty do testów; wdrożenie mechaniki w UI walki jest kolejnym krokiem.\n\n'
        'Druk monochromatyczny, jednostronny, 100%. Zdolności i cele 60 × 54 mm, sprzęt 60 × 42 mm. Wszystkie strony pionowe.\n\n'
        'Źródło: `content/print/rune_charges_v02/catalog.json`. '
        'Odbudowa: `PYTHONPATH=src .venv/bin/python scripts/build_rune_charges.py --maps`.\n', encoding='utf-8')
    write_indexes(output, catalog, manifest)
    return manifest


def main() -> None:
    """Build the current monochrome handouts from the canonical catalog."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_rune_relations import main as build_current
    build_current()


if __name__ == '__main__':
    main()

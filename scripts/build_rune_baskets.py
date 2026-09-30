"""Build the seven-hero live rune basket print pack, one browser at a time."""
from __future__ import annotations

import argparse
from html import escape, unescape
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import build_hero_mats as mats
from dnd_board_game.character_creation.runes import apply_rune_profile
from dnd_board_game.physical_cards.mana_print_files import merge_pdfs, render_pdf
from dnd_board_game.physical_cards.rune_baskets import (
    CSS, action_cards_content, action_mat_content, basket_content, build_payload, print_hero, first_page_tokens,
)
from dnd_board_game.physical_cards.rune_prototype import ACTION_MM, EQUIPMENT_MM
from dnd_board_game.scenarios.character_text import print_copy
from dnd_board_game.scenarios.rune_basket_catalog import load_rune_basket_catalog
from dnd_board_game.ui.training_arena import training_hero

OUTPUT = ROOT / 'content/scenarios/misja_0_dzwon/print/runy_koszyki_v01'
DATA = ROOT / 'docs/ui/rune-baskets-data.js'


def body_only(html: str) -> str:
    return html.split('<body>', 1)[1].split('</body>', 1)[0]


def page(title: str, subtitle: str, number: str, content: str, *, kind: str = '') -> str:
    return (f'<article class="page {kind}">' +
            mats.base.header(escape(title), escape(subtitle), number, imprint='KOSZYKI RUN · TEST 01') +
            content + mats.base.footer('Osobiste runy · koszyki v0.2 · A4, skala 100%') + '</article>')


def render_hero(hero: dict[str, Any], payload: dict[str, Any], output: Path = OUTPUT) -> str:
    """Compose existing identity/equipment mats with new resource and power pages."""
    copy = print_copy()
    model = print_hero(hero)
    actor = apply_rune_profile(training_hero(hero['id']))
    personal = {**copy['heroes'][hero['id']], 'flaw': hero['flaw']['description']}
    character = body_only(mats.character_page(model, personal, output))
    character = character.replace('01 / 04', '01 / 06').replace('ZESTAW 02', 'KOSZYKI 01')
    character = character.replace('bez nasycenia', 'wartość bazowa')
    character = re.sub(r'<section class="commitments">.*?</section>', first_page_tokens(hero, payload['categories']), character, flags=re.S)
    equipment = body_only(mats.equipment_page(model))
    equipment = equipment.replace('04 / 04', '04 / 06').replace('ZESTAW 02', 'KOSZYKI 01')
    equipment = equipment.replace('Znaczniki zajętej drugiej ręki są w osobnym pliku znaczniki_A4.pdf.',
                                  'Dla sprzętu oburęcznego zaznacz zajętą drugą rękę.')
    cutouts = body_only(mats.equipment_cutouts(model, copy['equipment'], output, actor=actor))
    cutouts = cutouts.replace('ZESTAW 02', 'KOSZYKI 01').replace('Osobne noże mają osobne żetony. ', '')
    cutouts = cutouts.replace('Wspólne zasady znajdziesz w sciaga_graczy_A4.pdf, a znaczniki i legendę w znaczniki_A4.pdf.',
                              'Zasady run są na macie koszyków. Kartę przedmiotu połóż w odpowiednim miejscu wyposażenia.')
    pages = [character,
             page(f'{model.name} · koszyki run', 'Wybierz symbole przed walką · podczas walki ładuj przez k4', '02 / 06',
                  basket_content(hero, payload['categories'], payload['rules']), kind='basket-page'),
             page(f'{model.name} · zdolności', 'Mata na wymienne karty · nie wycinaj', '03 / 06',
                  action_mat_content(), kind='basket-action-page'),
             equipment,
             page(f'{model.name} · wytnij zdolności', 'Karty 60 × 54 mm · tnij po zewnętrznych liniach', '05 / 06',
                  action_cards_content(hero, payload['categories']), kind='basket-action-page'),
             cutouts]
    return ('<!doctype html><html lang="pl"><meta charset="utf-8"><title>' + escape(model.name) +
            ' · koszyki run</title><style>' + mats.base.CSS + mats.EXTRA_CSS + CSS +
            '</style><body>' + ''.join(pages) + '</body></html>')


VALIDATE = r"""
addEventListener('load',()=>{
 const errors=[];
 for(const p of document.querySelectorAll('.page')){
  const b=p.getBoundingClientRect(),f=p.querySelector('footer')?.getBoundingClientRect();
  for(const child of p.children){if(child.tagName==='FOOTER')continue;const c=child.getBoundingClientRect();
   if(c.bottom>(f?.top??b.bottom)+1||c.right>b.right+1)errors.push('page-overflow:'+p.querySelector('h1').innerText+':'+child.className);}
 }
 for(const e of document.querySelectorAll('.basket-action,.basket-action-slot,.item,.equipment-slot')){
  const b=e.getBoundingClientRect(),size=e.matches('.basket-action,.basket-action-slot')?[60,54]:[60,42];
  if(Math.abs(b.width*25.4/96-size[0])>.12||Math.abs(b.height*25.4/96-size[1])>.12)errors.push('size:'+e.className);
 }
 for(const e of document.querySelectorAll('.basket-action,.basket-action-slot,.basket-cell,.item,.equipment-slot')){
  if(e.scrollHeight>e.clientHeight+2||e.scrollWidth>e.clientWidth+2)errors.push('overflow:'+e.innerText.slice(0,75));
  const b=e.getBoundingClientRect();
  for(const child of e.children){if(child.getBoundingClientRect().bottom>b.bottom+1)errors.push('card-text:'+e.innerText.slice(0,75));}
 }
 for(const image of document.images)if(!image.complete||!image.naturalWidth)errors.push('image:'+image.src);
 const r=document.createElement('pre');r.id='basket-validation';r.textContent=JSON.stringify(errors);document.body.append(r);
});
"""


def validate(path: Path, *, script: str = VALIDATE) -> list[str]:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if chrome is None:
        raise RuntimeError('Kontrola wydruku wymaga Chrome/Chromium. Użyj --html-only do podglądu.')
    check = path.with_name('_check_' + path.name)
    check.write_text(path.read_text(encoding='utf-8').replace('</body>', '<script>' + script + '</script></body>'),
                     encoding='utf-8')
    try:
        with TemporaryDirectory(prefix='rune-baskets-check-') as temporary:
            result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu',
                                     '--disable-dev-shm-usage', '--disable-background-networking',
                                     '--disable-extensions', '--disable-sync', '--no-first-run',
                                     f'--user-data-dir={temporary}', '--dump-dom', check.resolve().as_uri()],
                                    capture_output=True, text=True, check=True, timeout=45)
        match = re.search(r'<pre id="basket-validation">(.*?)</pre>', result.stdout, re.S)
        if match is None:
            raise RuntimeError(f'{path.name}: przeglądarka nie zwróciła kontroli układu.')
        return json.loads(unescape(match.group(1)))
    finally:
        check.unlink(missing_ok=True)


def write_data(payload: dict[str, Any], path: Path = DATA) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('/* Generated by scripts/build_rune_baskets.py. */\nwindow.RUNE_BASKET_DATA = ' +
                    json.dumps(payload, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')


def render_index(output: Path, payload: dict[str, Any], manifest: dict[str, Any],
                 *, cards_output: Path | None = None) -> str:
    """Keep both materials entry points linked to the current character pack."""
    cards = cards_output if cards_output is not None else output
    maps = ROOT / 'content/scenarios/misja_0_dzwon/print/runy_v01'

    def link(path: Path, label: str) -> str:
        return f'<a href="{escape(os.path.relpath(path, output), quote=True)}">{escape(label)}</a>'

    heroes = {hero['id']: hero for hero in payload['heroes']}
    rows = []
    for section in manifest['sections']:
        hero = heroes[section['hero']]
        capacity = ''.join(f'<td>{hero["capacities"][category["id"]]}</td>' for category in payload['categories'])
        downloads = []
        if manifest['pdf']:
            downloads.append(link(cards / f'{hero["id"]}.pdf', f'PDF · {section["pages"]} stron'))
        downloads.append(link(cards / f'{hero["id"]}.html', 'Podgląd HTML'))
        first, last = section['first_page'], section['first_page'] + section['pages'] - 1
        rows.append(f'<tr><th scope="row">{escape(hero["name"])}</th>{capacity}'
                    f'<td>{" · ".join(downloads)}<small>W komplecie: strony {first}–{last}</small></td></tr>')
    headings = ''.join(f'<th scope="col">{escape(category["name"])}</th>' for category in payload['categories'])
    combined = ('<p class="download">' + link(cards / 'karty_postaci_A4.pdf',
                f'Pobierz wszystkie karty · {manifest["pages"]} strony A4') + '</p>') if manifest['pdf'] else ''
    return '''<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Przy stole · aktualne karty i koszyki run</title>
<style>
*{box-sizing:border-box}body{max-width:1000px;margin:40px auto;padding:0 24px;background:#f3f0e8;color:#262a26;font:17px/1.6 system-ui}
h1,h2{font-family:Georgia;line-height:1.25}h1{margin-bottom:12px}h2{margin-top:32px}a{color:#354e3e;text-underline-offset:3px}
a:focus-visible{outline:3px solid #958058;outline-offset:4px}li{margin:8px 0}.note{border-left:3px solid #958058;padding:12px 20px;background:#fff}
.edition,small{color:#535b53;font-size:14px}small{display:block}.download a{display:inline-block;background:#354e3e;color:#fff;padding:12px 20px;border-radius:4px;font-weight:650}
.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;background:#fff}caption{text-align:left;margin-bottom:12px}
th,td{padding:10px 12px;border-bottom:1px solid #d6d4ca;text-align:center}th:first-child,td:last-child{text-align:left}thead{background:#e5e6dc}td:last-child{min-width:230px}
details{margin:24px 0}summary{cursor:pointer}footer{margin:32px 0;border-top:1px solid #ccc;padding-top:16px}
@media(max-width:600px){body{padding:0 14px;margin:24px auto;font-size:16px}th,td{padding:8px}h1{font-size:28px}}
@media print{body{max-width:none;margin:0;background:#fff;font-size:10pt}.download a{background:none;color:#000;padding:0}.table-wrap{overflow:visible}details{display:none}}
</style></head><body><main>
<p class="edition">Materiały do gry · koszyki run v0.2 · 23.09.2026</p>
<h1>Przy stole · karty, runy i plansza</h1>
<p>Aktualne zestawy siedmiu bohaterów do nowych walk Misji 0 i swobodnego treningu areny.
Każda postać ma własne żetony w czterech kategoriach; aplikacja śledzi ich symbole i wydawanie.</p>
''' + combined + '''
<p class="note"><strong>Druk A4, czarno-biały, jednostronnie, skala 100%.</strong>
Wyłącz „dopasuj do strony”. Pierwsza strona postaci ma miejsca na żetony zamiast części na notatki.</p>
<h2>Makieta interfejsu</h2>
<p>''' + link(ROOT / 'docs/ui/prototype.html', 'Otwórz wcześniejszą makietę UI · reputacja i runy') + '''</p>
<p>Wracamy do tego układu jako podstawy dalszych prac nad interfejsem.
Karty poniżej pozostają w obecnej wersji; kolejne zmiany uzgadniamy po kolei, zaczynając od kart.</p>
<h2>Karty postaci i pojemności koszyków</h2>
<div class="table-wrap"><table><caption>Liczby określają maksymalną liczbę żetonów w danej kategorii.</caption>
<thead><tr><th scope="col">Bohater</th>''' + headings + '<th scope="col">Materiały</th></tr></thead><tbody>' + ''.join(rows) + '''</tbody></table></div>
<p>Każdy zestaw ma sześć stron: postać i pola na żetony, mata koszyków, mata zdolności,
mata wyposażenia, zdolności do wycięcia i sprzęt do wycięcia.
Karty zdolności: 60 × 54 mm. Sprzęt: 60 × 42 mm.</p>
<h2>Jak używać run z planszy</h2>
<ol>
<li><strong>Przed walką:</strong> dla każdej postaci wybierz dowolne symbole w obrębie kategorii,
aż wypełnisz jej koszyk. Naciśnięcie runy zgłasza jeden żeton; symbole mogą się powtarzać.
✓ zatwierdza kategorię, ↩ cofa ostatni żeton.</li>
<li><strong>Wybór mocy:</strong> naciśnij jej runę, wskaż cel na planszy i zatwierdź podgląd.
Podstawowy koszt to jeden własny żeton kategorii przycisku. Na przykład Uderzenie tarczą
wybierasz Kotwicą, ale płacisz dowolną runą Obrony. Skaza może wymagać dopłaty.</li>
<li><strong>Opcjonalny Rezonans:</strong> wybierz najwyżej jedno ulepszenie i jego konkretną runę
z innej kategorii albo pomiń ten krok. Jeśli brakuje Ci tej runy, aplikacja wskaże
przytomnych sojuszników do 3 pól, również po przekątnej, z odpowiednim żetonem i wolną reakcją.
Wskaż figurkę pomocnika i potwierdź jego udział; użyczy on żetonu i wyda reakcję.</li>
<li><strong>Podsumowanie:</strong> sprawdź cel, efekt i koszty. Dopiero końcowe ✓ wydaje żetony
i uruchamia rozstrzygnięcie. Wcześniej możesz się cofnąć bez wydawania zasobów.
Własne rzuty wpisujesz przez +/−/✓; za przeciwników rzuca aplikacja.</li>
</ol>
<p>Zwykły ruch i podstawowy atak nie kosztują run. Dostępność akcji nadal zależy od budżetów
wskazanych na karcie: A — atak/przedmiot, S — specjalna, M — ruch, R — reakcja.</p>
<p><strong>Spirala — Skupienie:</strong> wydaj S, aby naładować do dwóch pustych miejsc.
Dla każdego wybierz kategorię i rzuć k4, która określi symbol.
<strong>Most — odnowienie:</strong> zgłoś spełniony warunek z karty postaci;
aplikacja pilnuje limitu raz na rundę i pojemności koszyka.</p>
<h2>Plansza i kafle Misji 0</h2>
<ul><li>''' + link(maps / 'plansza_A4.pdf', 'Plansza z panelem run — 12 stron A4') + '</li><li>' + link(maps / 'misja_0_kafle_A4.pdf', 'Wszystkie 18 kafli Misji 0') + '''</li></ul>
<p>Plansza i kafle uwzględniają tę samą korektę +3%. Nie dodawaj jej ponownie podczas drukowania.
Planszę składaj od A1 w wierszach A–D; pasy 10 mm służą jako zakładki do sklejenia.</p>
<footer><p>Te karty odpowiadają nowym walkom. Starsze zapisy i samouczek prowadzony
zachowują poprzednie zasady.</p><p>''' + link(ROOT / 'docs/RUNE_BASKETS_RUNTIME.md', 'Szczegółowe zasady koszyków w aplikacji') + '</p></footer>\n</main></body></html>\n'


def write_index(output: Path, payload: dict[str, Any], manifest: dict[str, Any]) -> None:
    # The latest card edition owns the public entry points; older exports stay archival.
    latest = ROOT / 'content/scenarios/misja_0_dzwon/print/runy_ladunki_v02/characters_manifest.json'
    if output.resolve() == OUTPUT.resolve() and latest.is_file():
        from build_rune_charges import OUTPUT as charge_output, write_indexes
        from dnd_board_game.scenarios.rune_charge_catalog import load_rune_charge_catalog
        write_indexes(charge_output, load_rune_charge_catalog(), json.loads(latest.read_text(encoding='utf-8')))
        return
    output.joinpath('index.html').write_text(render_index(output, payload, manifest), encoding='utf-8')
    if output.resolve() == OUTPUT.resolve():
        original = output.parent / 'runy_v01'
        original.joinpath('index.html').write_text(
            render_index(original, payload, manifest, cards_output=output), encoding='utf-8')
    output.joinpath('README.md').write_text(
        '# Koszyki run v0.2 — siedmiu bohaterów\n\n'
        '[Materiały do druku](index.html). A4, jednostronnie, 100%, bez dopasowania.\n\n'
        f'{len(payload["heroes"])} zestawów, {manifest["pages"]} stron łącznie. '
        'Postać i pola na żetony, koszyki, mata zdolności, wyposażenie, wycinanki zdolności i sprzętu.\n\n'
        'Zdolności: 60 × 54 mm. Wyposażenie: 60 × 42 mm. Koszyki mają osobne miejsca na '
        'naładowane i rozładowane znaczniki. Połóż po jednym znaczniku dla każdego punktu pojemności '
        'i przemieszczaj go pomiędzy tymi miejscami. Małe runy sugerują przygotowanie przed walką; '
        'możesz wybrać inne symbole z tej samej kategorii. Przy ładowaniu rzut k4 określa nowy symbol.\n\n'
        'Każda moc kosztuje jedną własną runę kategorii; najwyżej jeden rezonans z innej kategorii. '
        'Wsparcie: do 3 pól, własna runa wspierającego i jego Reakcja. Skupienie: specjalna, '
        'do dwóch ładowań k4. Indywidualne wyzwalacze mają limit raz na rundę.\n\n'
        'Źródło mechaniki: `content/print/rune_baskets_v01/catalog.json`. '
        'Statystyki, historie i wyposażenie: bieżące profile siedmiu bohaterów. '
        'Model działa w nowych walkach Misji 0 i swobodnym treningu areny. Stare zapisy zachowują poprzedni model. Warunki odnowienia zgłasza się Mostem; limit i żetony rozlicza aplikacja.\n\n'
        'Odbudowa: `PYTHONPATH=src .venv/bin/python scripts/build_rune_baskets.py`. '
        '`--data-only`: tylko dane makiety, `--html-only`: dane i HTML bez przeglądarki/PDF. '
        'Pełne generowanie sprawdza układ i wymiary w jednej przeglądarce naraz, a następnie drukuje PDF.\n',
        encoding='utf-8')


def build(*, output: Path = OUTPUT, data_path: Path = DATA, data_only: bool = False,
          html_only: bool = False) -> dict[str, Any]:
    payload = build_payload(load_rune_basket_catalog())
    write_data(payload, data_path)
    if data_only:
        return payload
    output.mkdir(parents=True, exist_ok=True)
    sections: list[dict[str, Any]] = []
    checks: dict[str, list[str]] = {}
    parts: list[Path] = []
    page_number = 1
    for hero in payload['heroes']:
        html = render_hero(hero, payload, output)
        path = output / f'{hero["id"]}.html'
        path.write_text(html, encoding='utf-8')
        expected = len(re.findall(r'<article class="page\b', html))
        pages = expected
        if not html_only:
            checks[hero['id']] = validate(path)
            (output / 'validation.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            if checks[hero['id']]:
                raise RuntimeError(f'{hero["id"]}: popraw układ — {checks[hero["id"]]}')
            pdf = path.with_suffix('.pdf')
            render_pdf(path, pdf)
            pages = mats.pdf_pages(pdf)
            if pages != expected:
                raise RuntimeError(f'{hero["id"]}: PDF ma {pages} stron zamiast {expected}.')
            mats.compact_pdf(pdf)
            parts.append(pdf)
        sections.append(dict(hero=hero['id'], name=hero['name'], first_page=page_number, pages=pages))
        page_number += pages
        print(f'{hero["name"]}: {pages} stron' + (' HTML' if html_only else ', układ i PDF poprawne'), flush=True)
    manifest = dict(version=1, profile='rune_baskets_v01', pages=page_number - 1, sections=sections,
                    action_mm=ACTION_MM, equipment_mm=EQUIPMENT_MM, ability_slots=12,
                    pdf=not html_only, layout_validated=not html_only)
    if parts:
        combined = output / 'karty_postaci_A4.pdf'
        merge_pdfs(parts, combined)
        if mats.pdf_pages(combined) != manifest['pages']:
            raise RuntimeError('Połączenie PDF zmieniło liczbę stron.')
        mats.compact_pdf(combined)
    (output / 'characters_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    write_index(output, payload, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--data-only', action='store_true')
    mode.add_argument('--html-only', action='store_true')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    build(output=args.output, data_only=args.data_only, html_only=args.html_only)


if __name__ == '__main__':
    main()

"""Build the modular rune prototype prints and shared mockup data, sequentially."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from html import escape, unescape
import json
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

import build_hero_mats as old
from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.physical_cards.mana_print import build_print_hero
from dnd_board_game.physical_cards.mana_print_files import merge_pdfs, render_pdf
from dnd_board_game.physical_cards.rune_prototype import (
    ACTION_MM, EQUIPMENT_MM, PANEL_SYMBOLS, PRINT_SCALE, RESOURCE_RUNES,
    map_tile_svg, map_tiles, panel_icon,
)
from dnd_board_game.physical_cards.scenario_cutouts import build_cutouts, render_document
from dnd_board_game.scenarios.character_text import print_copy
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.character_creation.runes import apply_rune_profile

MISSION = ROOT / 'content/scenarios/misja_0_dzwon'
OUTPUT = MISSION / 'print/runy_v01'
SOURCE = ROOT / 'content/print/runes_v01/action_cards.json'

CSS = '''
.page{break-after:page;break-inside:avoid}.page:last-child{break-after:auto}
.module-grid{display:grid;grid-template-columns:repeat(3,60mm);grid-auto-rows:54mm;gap:4mm 7mm}
.module-slot,.module-card{width:60mm;height:54mm;border:.3mm dashed #999;padding:2.5mm;position:relative}
.module-slot{display:flex;flex-direction:column;align-items:center;justify-content:center;color:#888;text-align:center;border-radius:1.5mm;background:#fcfcfc}
.module-slot b{font:15pt Georgia;margin-bottom:3mm}.module-slot small{font:8pt Arial;line-height:1.5}
.module-card{border:.3mm solid #333;font:8pt/1.2 Arial;background:white;display:flex;flex-direction:column;gap:1.4mm}
.module-card h2{font:bold 10.5pt/1.1 Georgia;margin:0}.module-card p{margin:0}
.module-head{display:flex;gap:1.6mm;align-items:center;min-height:8mm;border-bottom:.3mm solid #666;padding-bottom:1.4mm}
.module-head .glyph{width:6.5mm;height:6.5mm;flex:none}
.module-key{display:flex;flex-direction:column;align-items:center;flex:none}.module-key small{font:5.5pt Arial}
.module-cost{font:bold 7.2pt Arial;display:flex;justify-content:space-between;gap:1mm}
.module-boosts{border-top:.2mm dotted #888;margin-top:auto;padding-top:1mm;font-size:7.1pt;line-height:1.25}
.module-boosts div{margin-bottom:.5mm}.module-boosts b{font-weight:700}
.module-blank{flex:1;background:repeating-linear-gradient(white,white 5.5mm,#bbb 5.65mm,white 5.8mm)}
.module-note{font:8pt/1.3 Arial;margin-top:3mm}.action-page header h1{font-size:23pt}
.module-slot .slot-number{font:27pt Georgia;color:#ddd;margin-bottom:3mm}
@media screen{.page{margin-bottom:8mm}}
'''


def body_only(html: str) -> str:
    return html.split('<body>', 1)[1].split('</body>', 1)[0]


def page(title: str, subtitle: str, number: str, content: str) -> str:
    return '<article class="page action-page">' + old.base.header(
        escape(title), escape(subtitle), number, imprint='RUNY · MODUŁOWY ZESTAW 01'
    ) + content + old.base.footer('Mata i wycinanki mają wspólne wymiary · runy v0.1') + '</article>'


def action_mat(name: str) -> str:
    slots = ''.join(f'<div class="module-slot" data-slot-number="{i}">'
                    f'<span class="slot-number">{i:02}</span><b>Miejsce na zdolność</b>'
                    '<small>Wymienna karta 60 × 54 mm<br>Runę określa położona karta.</small></div>'
                    for i in range(1, 13))
    return page(f'{name} · zdolności', 'Pusta mata · nie wycinaj · wymieniaj karty przy rozwoju',
                '02 / 03', '<div class="module-grid">'+slots+'</div>'
                '<p class="module-note">12 miejsc to pojemność maty, nie dodatkowe akcje w turze. '
                'Ruch + atak/przedmiot + specjalna. Zwykły atak okazyjny: bez run, zużywa reakcję.</p>')


def action_cutouts(name: str, cards: list[dict[str, Any]]) -> str:
    pieces = []
    for card in cards:
        if card['rune'] != PANEL_SYMBOLS[card['slot']][0]:
            raise ValueError(f"{name}: {card['id']} — koszt nie odpowiada symbolowi przycisku.")
        prototype = card['status'] in {'prototype', 'ready'}
        rune = 'dowolna' if card['rune'] == '*' else card['rune']
        price = f"1 × {rune}" if not card.get('free_first') else f'Pierwszy raz 0; potem 1 × {rune}'
        cost = f"Koszt: {price} · {card['budget']}" if prototype else 'Koszt: ................  Akcja: ........'
        description = escape(card['description']) if prototype else 'Efekt: <div class="module-blank"></div>'
        if prototype:
            boosts = ''.join(f'<div><b>{escape("+dowolna" if key == "*" else "+"+key if key else "Wariant")}:</b> {escape(text)}</div>'
                             for key, text in card['boosts'])
        else:
            boosts = 'Wzmocnienie 1: ................................<br>Wzmocnienie 2: ................................<br>Wzmocnienie 3: ................................'
        pieces.append(f'<section class="module-card" data-card-id="{card["id"]}">'
                      f'<div class="module-head"><div class="module-key">{panel_icon(card["slot"])}<small>Przycisk</small></div><h2>{escape(card["name"])}</h2></div>'
                      f'<div class="module-cost"><span>{escape(cost)}</span><span>{"RUNY" if prototype else "SZABLON"}</span></div>'
                      f'<div class="module-effect">{description}</div><div class="module-boosts">{boosts}</div></section>')
    while len(pieces) < 12:
        pieces.append('<section class="module-card"><div class="module-head"><h2>Nowa zdolność</h2></div>'
                      '<p>Runa: ............. Koszt: .............</p><div class="module-blank"></div>'
                      '<div class="module-boosts">Wzmocnienia: ................................</div></section>')
    return page(f'{name} · wytnij zdolności', 'Karty 60 × 54 mm · linia ciągła do cięcia', 'WYCINANKI',
                '<div class="module-grid">'+''.join(pieces)+'</div>'
                '<p class="module-note">S — specjalna · A — atak/przedmiot · M — ruch · R — reakcja. '
                'Najwyżej jedno wzmocnienie na użycie. Gwiazda: informacja o bohaterze. Puste karty służą rozwojowi postaci.</p>')


VALIDATE = r'''
addEventListener('load',()=>{
 const errors=[];
 for(const p of document.querySelectorAll('.page')){
  const b=p.getBoundingClientRect(),footer=p.querySelector('footer')?.getBoundingClientRect();
  for(const child of p.children){if(child.tagName==='FOOTER')continue;const c=child.getBoundingClientRect();
   if(c.bottom>(footer?.top??b.bottom)+1||c.right>b.right+1)errors.push('page-overflow:'+p.querySelector('h1').innerText+':'+child.className);}
 }
 for(const e of document.querySelectorAll('.module-card,.module-slot,.item,.equipment-slot')){
  if(e.scrollHeight>e.clientHeight+2||e.scrollWidth>e.clientWidth+2)errors.push('overflow:'+e.innerText.slice(0,60));
  const b=e.getBoundingClientRect(),size=e.matches('.module-card,.module-slot')?[60,54]:[60,42];
  if(Math.abs(b.width*25.4/96-size[0])>.12||Math.abs(b.height*25.4/96-size[1])>.12)errors.push('size:'+e.className);
  for(const child of e.children){if(child.getBoundingClientRect().bottom>b.bottom+1)errors.push('card-text:'+e.innerText.slice(0,60));}
 }
 for(const i of document.images)if(!i.complete||!i.naturalWidth)errors.push('image:'+i.src);
 const r=document.createElement('pre');r.id='rune-validation';r.textContent=JSON.stringify(errors);document.body.append(r);
});
'''


def validate(path: Path) -> list[str]:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    check = path.with_name('_check_'+path.name)
    check.write_text(path.read_text().replace('</body>', '<script>'+VALIDATE+'</script></body>'))
    try:
        with TemporaryDirectory(prefix='rune-check-') as temp:
            result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu',
                '--disable-dev-shm-usage', '--disable-background-networking', f'--user-data-dir={temp}',
                '--dump-dom', check.as_uri()], capture_output=True, text=True, check=True, timeout=45)
        match = re.search(r'<pre id="rune-validation">(.*?)</pre>', result.stdout, re.S)
        if not match:
            raise RuntimeError('Brak wyniku kontroli układu.')
        return json.loads(unescape(match.group(1)))
    finally:
        check.unlink(missing_ok=True)


def export(html: str, name: str, *, check_layout: bool = False) -> Path:
    path = OUTPUT / f'{name}.html'
    path.write_text(html, encoding='utf-8')
    if check_layout:
        issues = validate(path)
        if issues:
            raise RuntimeError(f'{name}: {issues}')
    pdf = path.with_suffix('.pdf')
    render_pdf(path, pdf)
    print(f'{name}: {old.pdf_pages(pdf)} stron', flush=True)
    return pdf


def build_maps() -> list[Path]:
    sheets = ''.join('<section>'+map_tile_svg(tile)+'</section>' for tile in map_tiles())
    html = ('<!doctype html><html lang="pl"><meta charset="utf-8"><title>Plansza · runy v0.1</title>'
            '<style>@page{size:A4 landscape;margin:0}body{margin:0}section{width:297mm;height:210mm;'
            'break-after:page}section:last-child{break-after:auto}svg{display:block}</style>'+sheets+'</html>')
    board = export(html, 'plansza_A4')
    spec = json.loads((MISSION/'maps/cutouts.json').read_text())
    battle = json.loads((MISSION/'mechanics/battle.json').read_text())
    tokens = build_cutouts(spec, battle)
    art = {t.id: (MISSION/t.artwork).as_uri() for t in tokens if t.artwork}
    html = render_document(tokens, spec['cell_mm']*PRINT_SCALE, True, art)
    html = html.replace('Kalibracja areny 250/244; po wydruku 4 pola powinny mieć 100 mm.',
                        'Runy v0.1: dotychczasowa korekta × 1,03. Dopasuj do nowej planszy.')
    html = html.replace('kalibracja areny 250/244', 'runy v0.1 · korekta +3%')
    html = html.replace('Odcinek kontrolny: 100 mm na skalibrowanym wydruku.',
                        'Odcinek kontrolny: 4 pola; porównaj z nową planszą i czujnikami.')
    scenery = export(html, 'misja_0_kafle_A4')
    old.compact_pdf(scenery)
    (OUTPUT/'map_manifest.json').write_text(json.dumps(dict(print_scale=PRINT_SCALE,
        relative_scale=1.03, pdf_cell_mm=25*PRINT_SCALE, tiles=[asdict(t) for t in map_tiles()],
        cutout_ids=[t.id for t in tokens], panel=[dict(slot=i,name=n,path=p,board=[19,29-i])
        for i,(n,p) in enumerate(PANEL_SYMBOLS)]), ensure_ascii=False, indent=2)+'\n')
    return [board, scenery]


def build_heroes(data: dict[str, Any]) -> list[Path]:
    copy = print_copy()
    parts = []
    sections = []
    heroes = []
    for hid in PLAYABLE_HERO_IDS:
        h = build_print_hero(hid, rune_profile=True)
        actor = apply_rune_profile(training_hero(hid))
        own_copy = dict(copy['heroes'][hid])
        own_copy['flaw'] = h.flaw[1]
        character = body_only(old.character_page(h, own_copy, OUTPUT))
        character = character.replace('01 / 04','01 / 03').replace('ZESTAW 02','RUNY 01').replace('bez nasycenia','wartość bazowa')
        equipment = body_only(old.equipment_page(h)).replace('04 / 04','03 / 03').replace('ZESTAW 02','RUNY 01')
        equipment = equipment.replace('Znaczniki zajętej drugiej ręki są w osobnym pliku znaczniki_A4.pdf.', 'Dla sprzętu oburęcznego zaznacz zajętą drugą rękę.')
        cutouts = body_only(old.equipment_cutouts(h, copy['equipment'], OUTPUT, actor=actor)).replace('ZESTAW 02','RUNY 01')
        cutouts = cutouts.replace('Osobne noże mają osobne żetony. ', '')
        cutouts = cutouts.replace('Wspólne zasady znajdziesz w sciaga_graczy_A4.pdf, a znaczniki i legendę w znaczniki_A4.pdf.', 'Przygotuj wyposażenie przed wyprawą; karta przedmiotu zajmuje wskazane miejsce na macie.')
        html = ('<!doctype html><html lang="pl"><meta charset="utf-8"><title>'+h.name+' · runy</title><style>'+
                old.base.CSS+old.EXTRA_CSS+CSS+'</style><body>'+character+action_mat(h.name)+equipment+
                action_cutouts(h.name, data[hid])+cutouts+'</body></html>')
        pdf = export(html, hid, check_layout=True)
        if old.pdf_pages(pdf) != 5:
            raise RuntimeError(f'{hid}: oczekiwano trzech mat i dwóch arkuszy wycinanek.')
        old.compact_pdf(pdf)
        parts.append(pdf)
        sections.append(dict(hero=hid, name=h.name, first_page=len(sections)*5+1, pages=5))
        heroes.append(dict(id=hid,name=h.name,role=h.role,hp=h.hp,ac=h.ac,speed=h.speed,
            abilities=h.abilities,story=h.story,flaw=h.flaw,cards=data[hid],
            portrait=f'../../content/scenarios/misja_0_dzwon/assets/images/comic_v2/{hid}.png',
            equipment=[dict(id=i.id,name=copy['equipment'][i.source_ref or i.id].get('name',i.name),
                            slot=copy['equipment'][i.source_ref or i.id]['slot']) for i in actor.inventory]))
    combined = OUTPUT/'karty_postaci_A4.pdf'
    merge_pdfs(parts, combined)
    old.compact_pdf(combined)
    (OUTPUT/'characters_manifest.json').write_text(json.dumps(dict(pages=35,sections=sections,
        action_mm=ACTION_MM,equipment_mm=EQUIPMENT_MM,ability_slots=12),ensure_ascii=False,indent=2)+'\n')
    payload = dict(panel=[dict(slot=i,name=n,path=p) for i,(n,p) in enumerate(PANEL_SYMBOLS)],
                   resourceRunes=RESOURCE_RUNES,heroes=heroes)
    (ROOT/'docs/ui/rune-prototype-data.js').write_text('/* Generated by scripts/build_rune_prototype.py. */\nwindow.RUNE_DATA = '+
        json.dumps(payload,ensure_ascii=False,indent=2)+';\n')
    return parts


def write_index() -> None:
    names = [(h, build_print_hero(h).name) for h in PLAYABLE_HERO_IDS]
    links = ''.join(f'<li><a href="{h}.pdf">{name} — 5 stron</a> · <a href="{h}.html">podgląd</a></li>' for h,name in names)
    html = f'''<!doctype html><html lang="pl"><meta charset="utf-8"><title>Runy · materiały</title>
<style>body{{max-width:950px;margin:50px auto;padding:0 24px;background:#f3f0e8;color:#262a26;font:17px/1.65 system-ui}}h1,h2{{font-family:Georgia}}a{{color:#435d4c}}li{{margin:10px 0}}.note{{border-left:3px solid #958058;padding:12px 20px;background:#fff}}</style>
<h1>Przy stole · runy v0.1</h1><p>Nowa plansza, wymienne karty i klikalna makieta.</p>
<p class="note">Druk A4, 100%, bez dopasowania. Plansza i kafle mają tę samą dodatkową korektę +3%. Maty i wycinanki zachowują swoje wymiary.</p>
<h2>Plansza i Misja 0</h2><ul><li><a href="plansza_A4.pdf">Plansza — 12 stron A4</a></li><li><a href="misja_0_kafle_A4.pdf">Wszystkie 18 kafli Misji 0</a></li></ul>
<h2>Modułowe zestawy bohaterów</h2><p>1. Postać i zobowiązania · 2. Pusta mata zdolności · 3. Pusta mata wyposażenia · 4. Zdolności do wycięcia · 5. Sprzęt do wycięcia.</p>
<p><a href="karty_postaci_A4.pdf">Wszyscy bohaterowie — 35 stron</a></p><ul>{links}</ul>
<p>Zdolności: 60 × 54 mm. Sprzęt: 60 × 42 mm. Karty wszystkich bohaterów odpowiadają regułom run w aplikacji. Puste karty służą rozwojowi.</p>
<p><a href="../../../../../docs/ui/prototype.html">Otwórz klikalną makietę z panelem run</a></p>
<p class="note">Panel, karty i aplikacja używają wspólnego układu run. Gwiazda otwiera informacje o bohaterze.</p></html>'''
    (OUTPUT/'index.html').write_text(html)
    (OUTPUT/'README.md').write_text('''# Runy v0.1 — wydruki i makieta

Otwórz [spis materiałów](index.html). Druk A4, 100%, bez dopasowania.
Plansza: 12 arkuszy A1–D3. Tnij zewnętrzny obrys; pasy 10 mm służą jako zakładki.
Składaj od górnego lewego A1 w wierszach A–D. Panel znajduje się przy dolnej krawędzi.
Plansza oraz wszystkie 18 kafli Misji 0 mają skalę `(250/244) × 1,03`.
Przed pełnym drukiem porównaj kilka sąsiednich pól z fizycznymi czujnikami.

Każdy bohater: 3 niecięte maty + 2 arkusze wycinanek, łącznie 5 stron.
Zdolności 60 × 54 mm; sprzęt 60 × 42 mm. Nie skaluj tych elementów o 3%.
Mata zdolności ma 12 pustych miejsc; znaki run i zasady są na wymiennych kartach.
Karty siedmiu bohaterów zawierają koszty run, budżet akcji i do trzech wzmocnień.
Koszty i efekty pochodzą ze wspólnego źródła używanego przez aplikację.
Statystyki i wyposażenie pochodzą z obecnych postaci.

Źródło kart: `content/print/runes_v01/action_cards.json`.
Odbudowa: `PYTHONPATH=src .venv/bin/python scripts/build_rune_prototype.py`.
Można użyć `--only heroes` lub `--only maps`. Generator sprawdza układ przed publikacją.

Nowa aplikacja używa tego nadruku: ruch, atak, przedmiot, koniec tury, przerwa,
runy, przerwa, +, −, ✓, ↩. Gwiazda oznacza informację o bohaterze.
Runy dobieracie tylko na początku walki; reputacja jest osobnym zasobem drużyny.
Zwykły atak okazyjny bronią nie kosztuje run; zużywa dostępną reakcję.
Przy kilku dostępnych reakcjach wybiera się jedną, a koszt płaci po potwierdzeniu.
''')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', choices=('heroes','maps'))
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.only != 'heroes':
        build_maps()
    if args.only != 'maps':
        build_heroes(json.loads(SOURCE.read_text()))
    write_index()


if __name__ == '__main__':
    main()

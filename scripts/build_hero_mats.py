"""Build separate Mission 0 PDFs for hero sets, player reference, and markers.

Reuses the Garran prototype's print styles, symbols and layout validation.
Numbers/runes/starting equipment come from the live game; copy is editable.
"""
from __future__ import annotations

import argparse
import hashlib
from dataclasses import asdict
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from urllib.parse import quote

import build_garran_set_concept as base
from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.actors import Actor
from dnd_board_game.inventory.party_equipment import occupied, SLOTS
from dnd_board_game.physical_cards.mana_print import PrintHero, build_print_hero, COLORS
from dnd_board_game.physical_cards.mana_print_files import render_pdf, merge_pdfs
from dnd_board_game.physical_cards.handout_files import pdf_pages, compact_pdf
from dnd_board_game.physical_cards.mana_symbols import mana_symbol, passive_mana_symbol
from dnd_board_game.physical_cards.equipment_art import item_art
from dnd_board_game.scenarios.confrontation_terms import effect_name, effect_text
from dnd_board_game.scenarios.confrontation import passives as exploration_profile
from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
from dnd_board_game.scenarios.character_text import load_text, print_copy
from dnd_board_game.physical_cards.print_language import keyword_text
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.ui.board_panel_symbols import panel_icon

ROOT = base.ROOT
PRINT_ROOT = ROOT / 'content/scenarios/misja_0_dzwon/print'
OUTPUT = PRINT_ROOT / 'characters'
DESTINATION = PRINT_ROOT / 'karty_postaci_A4.pdf'
AID_DESTINATION = PRINT_ROOT / 'sciaga_graczy_A4.pdf'
MARKERS_DESTINATION = PRINT_ROOT / 'znaczniki_A4.pdf'


def rules_text(text: str) -> str:
    return keyword_text(text, tuple(t for forms in load_text()['keywords'].values() for t in forms))


def passive_text(text: str) -> str:
    for ending in ('. Nie kumuluje się.', ' Nie kumuluje się.', '. Kumuluje się.', ' Kumuluje się.', ' (bez kumulacji)'):
        text = text.replace(ending, '')
    name, _, body = text.partition(': ')
    when, separator, effect = body.partition(': ')
    if separator:
        return f'<b>{escape(name)}</b><p><span class="passive-when">{rules_text(when)}:</span> {rules_text(effect.rstrip(chr(46)) + chr(46))}</p>'
    return f'<b>{escape(name)}</b><p>{rules_text(body.rstrip(chr(46)) + chr(46))}</p>'


EXTRA_CSS = '''
.keyword{font-weight:700}
.identity{margin-bottom:3mm}.identity .portrait{height:68mm}
.quote{font-size:11pt;margin:2mm 0 3mm}
.page.character-page{display:flex;flex-direction:column;padding-bottom:11mm}
.character-page>header,.character-page>.vitals,.character-page>.stats,.character-page>.identity,.character-page>.flaw,.character-page>.note{flex-shrink:0}
.character-page .commitments{flex:1;min-height:28mm;display:flex;flex-direction:column;margin-top:2mm}
.commitments h3{margin-bottom:2mm}.commitment-lines{flex:1;background-image:radial-gradient(circle at 1mm 6.5mm,#aaa .16mm,transparent .23mm);background-size:2mm 7mm}

.aid-lead{font:12pt/1.4 Georgia;margin-bottom:5mm;padding:3mm 0;border-bottom:.3mm solid #333}
.aid-grid{display:grid;grid-template-columns:1fr 1fr;gap:4mm 6mm;align-items:start;font-size:10pt;line-height:1.35}
.aid-section h2{font: bold 13pt Georgia;margin-bottom:2mm;padding-bottom:1.5mm;border-bottom:.3mm solid #888}
.aid-section p{margin-bottom:2.3mm}.aid-section ol{padding-left:5mm;margin:0}.aid-section li{margin-bottom:2mm}
.aid-section.example{background:#eee;border-left:1mm solid #333;padding:3mm}.aid-section table{font-size:8.3pt;width:100%;border-collapse:collapse;margin-bottom:2mm}.aid-section td{border:.2mm solid #999;padding:1.2mm}.aid-section td:first-child{font-weight:bold}

.mana-head>.mana-symbol{width:7mm;height:7mm;margin-right:1mm}
.mode{display:flex;align-items:center;justify-content:space-between;gap:.5mm;padding:.6mm .7mm;font-size:6.6pt}
.mana-notes .mode .mana-passive-symbol{width:4.5mm;height:4.5mm;border-color:currentColor!important}
.mana-notes .mode .mana-symbol{width:3mm;height:3mm}.combat-passive .mana-passive-symbol{color:white}
.mana-notes{grid-template-rows:9mm auto auto}.mana-notes .mode{margin-bottom:1mm}
.passive-when{font-weight:600}.recovery-guide{border-top:.3mm solid #888;margin-top:2mm;padding-top:2mm}.recovery-guide h3{font-size:9pt}.recovery-diagram{display:block;width:100%;height:13mm;object-fit:contain;margin:1mm 0}
.mana-guide{font-size:8.2pt;padding:3mm}.mana-guide p{margin-bottom:1mm}.mana-guide .tiers{font-size:8.2pt;margin:1mm 0}.mana-guide .tiers td,.mana-guide .tiers th{padding:.6mm .5mm}.mana-guide h2{font-size:16pt}
.item h2{font-size:10pt}.item .detail{font-size:7pt}.item .slot-label{font-size:7.1pt}
.quantity-label{position:absolute;right:2mm;top:1.5mm;font-size:7pt;background:white}
.item h2.with-quantity{padding-right:7mm}.items-guide{margin-top:5mm;font-size:9pt}
.markers{display:grid;grid-template-columns:repeat(3,60mm);gap:6mm 7mm}.marker{height:42mm;border:.3mm solid #222;padding:3mm;display:flex;align-items:center;justify-content:center;flex-direction:column;text-align:center;gap:3mm}.marker b{font:12pt Georgia}.marker small{font-size:8pt}
.actions.dense{grid-template-columns:repeat(4,68mm);grid-template-rows:repeat(3,53mm);gap:3mm}
.dense .action{font-size:8.4pt;line-height:1.18;padding:1.7mm}.dense .action-head{min-height:8mm;margin-bottom:1mm;padding-bottom:1mm;gap:1.5mm}.dense .rune{width:7mm;height:7mm}.dense .rune svg{width:5mm;height:5mm}.dense .action h2{font-size:10.5pt}.dense .action-meta{font-size:7.5pt;margin-bottom:1mm;padding-bottom:1mm}.dense .boost{font-size:7.7pt;margin-top:1mm;padding-top:1mm}.dense .action p{margin-bottom:1mm}.dense-legend{font-size:7.3pt;line-height:1.2;margin-top:2mm}.dense-legend p{margin-bottom:.5mm}
.section-intro{margin:5mm 0;font-size:11pt}.toc{width:100%;border-collapse:collapse;margin:8mm 0}.toc th,.toc td{padding:3mm;border-bottom:.3mm solid #999;text-align:left}.toc th{background:#222;color:white}.cover-title{font:30pt Georgia;margin-top:8mm}.cover-box{padding:5mm;border:.4mm solid #555;margin:7mm 0}.cover-box li{margin:2mm 0}
'''


def header(hero: PrintHero, title: str, subtitle: str, number: str) -> str:
    return base.header(escape(title), subtitle, number, imprint=f'{hero.name.upper()} · ZESTAW 02')


def document(hero: PrintHero, body: str, *, landscape: bool = False) -> str:
    return base.document(body, landscape=landscape, title=f'{hero.name} · zestaw do gry', extra_css=EXTRA_CSS)


def character_page(hero: PrintHero, copy: dict, folder: Path) -> str:
    vitals = ''.join(f'<div class="vital"><label>{label}</label><b>{value}</b><small>{note}</small></div>' for label,value,note in (
        ('Punkty wytrzymałości',hero.hp,'maksimum PW'),('Klasa pancerza',hero.ac,'zestaw startowy, bez nasycenia'),
        ('Ruch',f'{hero.speed} ft',f'{hero.speed/5:g} pól po 5 ft'),('Inicjatywa',f'{hero.initiative:+d}','premia bazowa')))
    stats = ''.join(f'<div class="stat"><label>{name}</label><b>{score}</b><span>{mod:+d}</span></div>' for name,score,mod in hero.abilities)
    story = ''.join(f'<section><h3>{escape(label)}</h3><p>{escape(text)}</p></section>' for label,text in hero.story)
    portrait=quote(os.path.relpath(ROOT/f'content/scenarios/misja_0_dzwon/assets/images/comic_v2/{hero.id}.png',folder))
    return document(hero,header(hero,hero.name,f'{escape(hero.role.split("—")[0].strip())} · poziom {hero.level}','01 / 04')+f'''
<div class="vitals">{vitals}</div><div class="stats">{stats}</div>
<div class="identity"><div><img class="portrait" src="{portrait}" alt="{hero.name}"><p class="note">Wartość cechy — duża liczba.<br>Obok: modyfikator do rzutu.</p></div><div class="story">{story}<div class="quote">{escape(copy['character_line'])}</div></div></div>
<div class="flaw"><h3>Skaza · {escape(hero.flaw[0])}</h3><p>{rules_text(copy.get("flaw", hero.flaw[1]))}</p></div>
<section class="commitments"><h3>Aktualne zobowiązania <small class="notes-label">— do uzupełnienia podczas gry</small></h3><div class="commitment-lines" aria-label="Kropkowane linie na notatki"></div></section>
'''+base.footer('Postać · historia i statystyki · arkusz pozostaje w całości')).replace('class="page "', 'class="page character-page"', 1)


def mana_page(hero: PrintHero, copy: dict) -> str:
    cells=[]
    for color in base.ORDER:
        value=dict(hero.mana_values)[color]
        combat_data=hero_profile(hero.id)['color_passives'][color]['display']
        exploration_data=exploration_profile(hero.id)[color]['display']
        combat=passive_text(f"{combat_data['name']}: {combat_data['short']}")
        exploration=passive_text(effect_text(f"{exploration_data['name']}: {exploration_data['short']}", None))
        cells.append(f'''<section class="mana-cell" data-color="{color}"><div class="mana-slot">{mana_symbol(color)}<b>{COLORS[color]}</b><span>{"Atut · " if value == 2 else ""}{value} ładunku</span><small>Miejsce na karty 63 × 88 mm.<br>Ten sam kolor układaj w stos.</small></div><div class="mana-notes"><div class="mana-head">{mana_symbol(color)}<div><strong>{value}</strong><small>ładunku</small></div></div>
<section class="passive-block combat-passive"><div class="mode">Walka {passive_mana_symbol(color,color in hero.stacking_mana_colors)}</div>{combat}</section>
<section class="passive-block exploration-passive"><div class="mode">Eksploracja {passive_mana_symbol(color,color in hero.stacking_exploration_colors)}</div>{exploration}</section></div></section>''')
    cells.append(f'''<section class="mana-guide"><h2>Nasycenie maną</h2><p><b>Testy:</b> +1 za fizyczną kartę, maks. +6.<br><b>Ładunek:</b> atut = 2, reszta = 1, maks. 6.<br><b>Akcje:</b> progi 2 / 4 / 6 (ulta).</p><p><b>Dobór do 6 kart.</b> Trzy atuty dają ładunek 6 i test +3; nadal dobierasz. Kolory włączają pasywy.</p><p><span class="ring thick"></span> <b>Gruba:</b> premie kart sumują się do limitu.<br><span class="ring"></span> <b>Cienka:</b> wystarczy 1 karta.<br>Leczenie: przy każdym doborze, nie stale.</p><div class="recovery-guide"><h3>Pasywy bohatera</h3><p>Każdy bohater ma własne efekty. Pomoc, koszt i reakcja mogą się zmieniać — sprawdź warunek na tej macie.</p><p>Odzyskanie karty: przesuń ją zgodnie z instrukcją i potwierdź <b>✓</b>.</p></div><p><b>Mana Drain:</b> walka — reset talii i pasywów; eksploracja — koniec konfrontacji. Leczenie pozostaje.</p></section>''')
    return document(hero,header(hero,f'{hero.name} · mana','Pięć kolorów · osobista pula','02 / 04')+'<div class="mana-grid">'+''.join(cells)+'</div>',landscape=True)


def actions_page(hero: PrintHero, copy: dict) -> str:
    dense=len(hero.cards)>9
    if len(hero.cards)>12:
        raise ValueError('Zbyt wiele akcji dla jednostronicowego układu.')
    if not {a.id for a in hero.cards} <= set(copy['actions']):
        raise ValueError(f'{hero.id}: opisy nie odpowiadają zestawowi akcji.')
    cards=[]
    for action in sorted(hero.cards,key=lambda a:a.panel_slot):
        sections=dict(action.sections)
        threshold=int(re.search(r'\d+',sections['Ładunek']).group())
        burn=int(re.search(r'\d+',sections['Spalanie']).group())
        boost=copy['boosts'].get(action.id)
        if bool(boost)!=('Podbicia' in sections):
            raise ValueError(f'{hero.id}/{action.id}: niezgodne podbicia')
        extra=f'<div class="boost"><b>Podbicie: spal +2 karty za każde</b>{rules_text(boost)}</div>' if boost else ''
        cards.append(f'<section class="action" data-id="{action.id}"><div class="action-head"><div class="rune">{panel_icon(action.panel_slot)}</div><h2>{escape(action.name)}</h2></div><div class="action-meta"><span>Ładunek ≥ {threshold}/6</span><span>{action.timing}</span><span>Spalanie: {burn}</span></div><p>{rules_text(copy["actions"][action.id])}</p>{extra}</section>')
    size='68 × 53' if dense else '62 × 76'
    legend=f'''<div class="action-legend {'dense-legend' if dense else ''}"><p><b>A</b> — główna · <b>D</b> — dodatkowa · <b>R</b> — reakcja · <b>MOD</b> — modyfikacja. <b>mod.</b> — modyfikator cechy. <b>5 ft</b> = 1 pole.</p><p><b>Pula zostaje.</b> Spal koszt po efekcie, także po porażce; nasycenie i skaza mogą go zmienić. Podbicie nie wymaga koloru.</p></div>'''

    return document(hero,header(hero,f'{hero.name} · akcje','Zdolności · wybór runą na planszy','03 / 04')+f'<div class="actions {"dense" if dense else ""}">'+''.join(cards)+'</div>'+legend+(base.footer(f'{len(cards)} zdolności na jednym A4 · efekty i podbicia') if not dense else ''),landscape=dense)


def equipment_page(hero: PrintHero) -> str:
    slots=[('Szyja','neck'),('Głowa','head'),('Pierścień','ring'),('Pierwsza ręka','hand'),('Pancerz','shield'),('Druga ręka','hand'),('Przybory magiczne / instrument','focus')]
    markup=''.join(f'<div class="equipment-slot">{base.icon(symbol)}<b>{name}</b><small>1 przedmiot · 60 × 42 mm</small></div>' for name,symbol in slots)
    markup+='''<div class="equip-instruction"><h3>Przygotuj przed wyprawą</h3><p>Połóż sprzęt zgodnie ze slotami w aplikacji. Przedmiot oburęczny zajmuje obie ręce: żeton na jednej, znacznik „zajęta” na drugiej.</p><p>Zmiana w slocie oddaje poprzedni przedmiot do wspólnego zapasu. Wyposażenie jest ustalone do powrotu; zużywalnych nadal można używać.</p></div><div class="bag-label">PLECAK / PRZEDMIOTY · wspólne pole, bez limitu sześciu przedmiotów</div>'''
    markup+=''.join('<div class="equipment-slot"><small>Miejsce na żetony<br>Można układać w stos.</small></div>' for _ in range(6))
    return document(hero,header(hero,f'{hero.name} · wyposażenie','Pusta mata · połóż na niej wycięte elementy','04 / 04')+'<div class="equipment-grid">'+markup+'</div><p class="equip-note">Startowe rozmieszczenie znajdziesz pod wycinankami sprzętu tej postaci. Nowe znaleziska w misji trafiają do wspólnego zapasu. Znaczniki zajętej drugiej ręki są w osobnym pliku znaczniki_A4.pdf.</p>'+base.footer('Przerywane ramki są miejscami na żetony — nie wycinaj tej maty'))


def equipment_cutouts(hero: PrintHero, copy: dict, folder: Path, *, actor: Actor | None = None) -> str:
    actor = actor if actor is not None else training_hero(hero.id)
    tiles=[]
    positions=[]
    for item in actor.inventory:
        text=copy[item.source_ref or item.id]
        name=text.get('name',item.name)
        quantity=f'<span class="quantity-label">×{item.quantity}</span>' if item.quantity>1 else ''
        dice=base.die(text['die']) if 'die' in text else ''
        tiles.append(f'<section class="item" data-id="{item.id}"><h2 class="{"with-quantity" if quantity else ""}">{escape(name)}</h2>{quantity}<div class="slot-label">{escape(text["slot"])}</div><div class="item-art">{item_art(item,print_root=folder)}{dice}</div><div><div class="effect">{base.icon(text["icon"])} {rules_text(text["effect"])}</div><div class="detail">{rules_text(text["detail"])}</div></div></section>')
        slots=occupied(item)
        if slots!=('pack',):
            positions.append(escape(name)+' — '+('obie ręce' if len(slots)==2 else SLOTS[slots[0]].lower()))
    if len(tiles)>12:
        raise ValueError(f'{hero.id}: sprzęt wymaga dodatkowego arkusza.')
    guide=f'''<div class="items-guide"><h2>Połóż na macie wyposażenia</h2><p><b>Start:</b> {'; '.join(positions)}. Pozostałe przedmioty — plecak.</p><p><b>mod.</b> — modyfikator cechy, nie jej wartość. <b>SIŁ</b> — Siła; <b>ZRĘ</b> — Zręczność. Np. Siła 18 daje mod. +4. <b>KP 16</b> ustala pancerz na 16; <b>+2 KP</b> zwiększa go o 2.</p><p>Wycinanki mają <b>60 × 42 mm</b>. Liczba × przy nazwie oznacza zawartość stosu. Osobne noże mają osobne żetony. Każdy element przechodzi wraz z przedmiotem po zatwierdzeniu zmiany w aplikacji.</p><p>Wspólne zasady znajdziesz w sciaga_graczy_A4.pdf, a znaczniki i legendę w znaczniki_A4.pdf. Sprzęt znaleziony w przygodzie drukujesz z zestawu scenariusza.</p></div>'''
    return document(hero,header(hero,f'{hero.name} · sprzęt startowy',f'Wytnij {len(tiles)} elementów po zewnętrznych liniach','WYCINANKI')+'<div class="cutouts">'+''.join(tiles)+'</div>'+guide+base.footer('Ilustracja · nazwa · miejsce · efekt · każdy żeton 60 × 42 mm'))


def player_aid_page(data: dict) -> str:
    sections=[]
    for section in data['sections']:
        body=''
        if 'table' in section:
            body+='<table>'+''.join('<tr>'+''.join('<td>'+rules_text(cell)+'</td>' for cell in row)+'</tr>' for row in section['table'])+'</table>'
        body+=''.join('<p>'+rules_text(text)+'</p>' for text in section.get('paragraphs',[]))
        if 'steps' in section:
            body+='<ol>'+''.join('<li>'+rules_text(text)+'</li>' for text in section['steps'])+'</ol>'
        sections.append('<section class="aid-section '+('example' if section.get('example') else '')+'"><h2>'+escape(section['title'])+'</h2>'+body+'</section>')
    return base.document(base.header(escape(data['title']),escape(data['subtitle']),'ZASADY',imprint='DLA CAŁEJ DRUŻYNY')+'<div class="aid-lead">'+rules_text(data['lead'])+'</div><div class="aid-grid">'+''.join(sections)+'</div>'+base.footer('Jedna kopia dla drużyny · pogrubione nazwy oznaczają pojęcia mechaniczne'),title=data['title'],extra_css=EXTRA_CSS)


def markers_page() -> str:
    markers=''.join('<div class="marker"><b>DRUGA RĘKA ZAJĘTA</b><small>Broń oburęczna znajduje się<br>w drugim slocie ręki.</small></div>' for _ in range(6))
    markers+=''.join('<div class="marker"><b>WYKORZYSTANE<br>DO MANA DRAIN</b><small>Tylko przy zdolności, której opis<br>określa takie ograniczenie.</small></div>' for _ in range(6))
    return base.document(base.header('Znaczniki pomocnicze','Wspólna pula · wytnij po liniach','DODATKI',imprint='DLA CAŁEJ DRUŻYNY')+'<div class="markers">'+markers+'</div>'+f'<div class="items-guide"><h2>Legenda elementów wyposażenia</h2><div class="legend-row">{base.icon("sword")} obrażenia {base.icon("shield")} pancerz / KP {base.die(8)} kość k8</div><p>× przy nazwie oznacza liczbę przedmiotów w stosie. Skrót KP oznacza Klasę Pancerza; PW — Punkty Wytrzymałości. Opis rozstrzyga rodzaj obrażeń, właściwą cechę i ograniczenia.</p><p>Każdy znacznik ma 60 × 42 mm. To pomoc w śledzeniu stanu, nie dodatkowe zasoby ani nowe limity.</p></div>'+base.footer('6 znaczników zajętej ręki + 6 znaczników wykorzystania'),title='Dodatki drużyny',extra_css=EXTRA_CSS)


def cover_page(sections: list[dict]) -> str:
    rows=''.join(f'<tr><td><b>{s["name"]}</b></td><td>{s["first_page"]}–{s["last_page"]}</td><td>{s["description"]}</td></tr>' for s in sections)
    return base.document(base.header('Bohaterowie','Kompletny zestaw do gry · siedem postaci','SPIS',imprint='WERSJA 02')+'''<div class="cover-title">Jedna postać — własny zestaw</div><p class="section-intro">Wybierzcie bohaterów, wydrukujcie ich strony i połóżcie przed sobą. Wspólne zasady: sciaga_graczy_A4.pdf. Znaczniki do wycięcia: znaczniki_A4.pdf.</p>'''+f'<table class="toc"><tr><th>Postać / sekcja</th><th>Strony</th><th>Zawartość</th></tr>{rows}</table>'+'''<div class="cover-box"><h2>Jak przygotować wydruk</h2><ul><li><b>A4, jednostronnie, 100% / rzeczywisty rozmiar.</b> Nie dopasowuj do strony.</li><li>Maty many i akcje Nimry są poziomo. Drukarka może obrócić stronę, ale nie powinna jej skalować.</li><li>Arkusze postaci, many, akcji i wyposażenia pozostają w całości. Wytnij tylko sprzęt i znaczniki.</li><li>Mana: karty 63 × 88 mm bez koszulek. Ekwipunek: żetony 60 × 42 mm.</li><li>Akcje: ramki 62 × 76 mm; Nimra: 68 × 53 mm. Karty rozwoju powinny pasować do ramek i run swojej postaci.</li></ul></div><p>Na macie many czarny nagłówek oznacza walkę, jasny eksplorację. Obwódka symbolu przy każdym nagłówku określa kumulację tylko w tym trybie.</p>'''+base.footer('Postacie w kolejności · zasady i znaczniki osobno · kontrola skali linijką'),title='Spis zestawów bohaterów',extra_css=EXTRA_CSS)


def write_page(folder: Path, name: str, html: str, *, action_mm: tuple[float,float]=(62,76), render: bool=True) -> tuple[Path,list[dict]]:
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/(name+'.html')
    digest=hashlib.sha256(html.encode()).hexdigest()
    stamp=path.with_suffix('.sha256')
    if render and stamp.exists() and stamp.read_text()==digest and path.with_suffix('.pdf').exists() and path.with_suffix('.png').exists():
        print(f'{folder.name}/{name}: OK (bez zmian)',flush=True)
        return path.with_suffix('.pdf'),[]
    path.write_text(html,encoding='utf-8')
    issues=base.validate_html(path,action_mm=action_mm)
    print(f'{folder.name}/{name}: '+('OK' if not issues else json.dumps(issues,ensure_ascii=False)),flush=True)
    if render and not issues:
        render_pdf(path,path.with_suffix('.pdf'))
        info=subprocess.run(['pdfinfo',str(path.with_suffix('.pdf'))],capture_output=True,text=True,check=True,timeout=15).stdout
        if not re.search(r'Pages:\s+1\b',info):
            raise RuntimeError(f'{path}: arkusz zajmuje więcej niż jedną stronę')
        subprocess.run(['pdftoppm','-singlefile','-scale-to','1300','-png',str(path.with_suffix('.pdf')),str(path.with_suffix(''))],capture_output=True,check=True,timeout=30)
        stamp.write_text(digest)
    return path.with_suffix('.pdf'),issues



def publish_pdf(destination: Path, parts: list[Path], sections: list[dict], **metadata: object) -> None:
    """Publish a self-contained PDF and a page index only after layout checks."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected = sum(pdf_pages(path) for path in parts)
    merge_pdfs(parts, destination)
    if pdf_pages(destination) != expected:
        raise RuntimeError('Nieprawidłowa liczba stron po połączeniu zestawów.')
    compact_pdf(destination)
    manifest = dict(pdf=destination.name, pages=expected, sections=sections, **metadata)
    destination.with_suffix('.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    lines = [f'# {destination.stem}', '', 'A4 · jednostronnie · 100%, bez dopasowania.', '',
             '| Sekcja | Strony |', '| --- | --- |']
    lines += [f'| {s["name"]} | {s["first_page"]}–{s["last_page"]} |' for s in sections]
    destination.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    print(f'{destination}: {expected} stron', flush=True)


def build_player_aid(*, check_only: bool = False) -> Path:
    """Rebuild the separately editable common rules without rendering hero sheets."""
    shared = OUTPUT / 'wspolne'
    checks: dict[str, list[dict]] = {}
    parts: list[Path] = []
    sections: list[dict] = []
    for number, page in enumerate(load_text()['player_aid'], 1):
        pdf, issues = write_page(shared, page['id'], player_aid_page(page), render=not check_only)
        parts.append(pdf)
        checks[page['id']] = issues
        sections.append(dict(id=page['id'], name=page['title'], first_page=number, last_page=number))
    marker_pdf, issues = write_page(shared, '05_znaczniki', markers_page(), render=not check_only)
    checks['05_znaczniki'] = issues
    (shared/'validation.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2)+'\n')
    if any(checks.values()):
        raise RuntimeError('Ściąga lub znaczniki: popraw wskazane przepełnienia.')
    if not check_only:
        publish_pdf(AID_DESTINATION, parts, sections, format='player_aid_v1')
        publish_pdf(MARKERS_DESTINATION, [marker_pdf], [dict(id='markers', name='Znaczniki pomocnicze',
            first_page=1, last_page=1)], marker_mm=[60, 42])
    return AID_DESTINATION


def build_pack(*, check_only: bool=False, actors: tuple[str,...]=PLAYABLE_HERO_IDS) -> Path:
    copy=print_copy()
    sections=[];parts=[];checks={};snapshots={};page=2
    for hid in actors:
        hero=build_print_hero(hid);folder=OUTPUT/hid;own=copy['heroes'][hid]
        snapshots[hid]=asdict(hero)
        sheets=[('01_postac',character_page(hero,own,folder)),('02_mana',mana_page(hero,own)),('03_akcje',actions_page(hero,own)),('04_ekwipunek',equipment_page(hero)),('05_sprzet',equipment_cutouts(hero,copy['equipment'],folder))]
        for name,html in sheets:
            pdf,issues=write_page(folder,name,html,action_mm=(68,53) if hid=='nimra' and name=='03_akcje' else (62,76),render=not check_only)
            parts.append(pdf);checks[f'{hid}/{name}']=issues
        sections.append(dict(id=hid,name=hero.name,first_page=page,last_page=page+4,description='Postać · mana · akcje · wyposażenie · wycinanki'))
        page+=5
    cover,issues=write_page(OUTPUT,'00_spis',cover_page(sections),render=not check_only);checks['spis']=issues
    (OUTPUT/'validation.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    if any(checks.values()):
        raise RuntimeError('Wydruk nie został opublikowany: popraw wskazane przepełnienia.')
    build_player_aid(check_only=check_only)
    if check_only:
        return DESTINATION
    if actors!=PLAYABLE_HERO_IDS:
        raise ValueError('Publikacja kompletu wymaga wszystkich siedmiu bohaterów.')
    publish_pdf(DESTINATION,[cover,*parts],sections,format='hero_mats_v3',mana_mm=[63,88],equipment_mm=[60,42],action_mm=[62,76],nimra_action_mm=[68,53])
    (OUTPUT/'source_snapshot.json').write_text(json.dumps(snapshots,ensure_ascii=False,indent=2)+'\n')
    previews=''.join(f'<section><h2>{s["name"]} · strony {s["first_page"]}–{s["last_page"]}</h2><div>'+''.join(f'<a href="{s["id"]}/{key}.pdf"><img src="{s["id"]}/{key}.png" alt="{key}"></a>' for key in ['01_postac','02_mana','03_akcje','04_ekwipunek','05_sprzet'])+'</div></section>' for s in sections)
    shared_sheets=[p['id'] for p in load_text()['player_aid']]+['05_znaczniki']
    previews+='<section><h2>Ściąga i znaczniki — osobne pliki</h2><div>'+''.join(f'<a href="wspolne/{key}.pdf"><img src="wspolne/{key}.png" alt="{key}"></a>' for key in shared_sheets)+'</div></section>'
    (OUTPUT/'podglad.html').write_text('<!doctype html><meta charset="utf-8"><title>Bohaterowie — podgląd</title><style>body{font:16px Arial;background:#e7e4de;margin:24px;color:#222}h1,h2{font-family:Georgia}section{margin-bottom:24px}section>div{display:grid;grid-template-columns:repeat(5,1fr);gap:14px}img{width:100%;height:280px;object-fit:contain;object-position:top;background:white;box-shadow:0 2px 5px #0003}</style><h1>Bohaterowie · zestawy A4</h1><p><a href="../karty_postaci_A4.pdf">Karty postaci</a> · <a href="../sciaga_graczy_A4.pdf">Ściąga graczy</a> · <a href="../znaczniki_A4.pdf">Znaczniki</a> · kliknij arkusz, żeby otworzyć jego PDF.</p>'+previews)
    return DESTINATION


def main() -> None:
    """Build the current monochrome handouts from the canonical catalog."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_rune_relations import main as build_current
    build_current()


if __name__ == "__main__":
    main()

"""Four Garran mats, small equipment cutouts and a shared A4 rules reference.

Prototype only: live statistics/passives/runes, editable concise copy alongside
the output. Does not replace the published character packs or change rules.
"""
from __future__ import annotations

from dataclasses import asdict
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dnd_board_game.physical_cards.equipment_art import item_art
from dnd_board_game.physical_cards.mana_print import build_print_hero, COLORS
from dnd_board_game.physical_cards.mana_print_files import render_pdf, merge_pdfs
from dnd_board_game.physical_cards.mana_symbols import mana_symbol, passive_mana_symbol
from dnd_board_game.ui.board_panel_symbols import panel_icon
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.scenarios.confrontation_terms import effect_name

OUTPUT = ROOT / "content/print/prototypes/garran_set_v2"
ORDER = ("C", "B", "Z", "F", "N")

CSS = """
@page{size:A4 portrait;margin:8mm}
*{box-sizing:border-box}body{margin:0;color:#191919;background:white;font:10pt/1.32 Arial,sans-serif}
.page{width:194mm;height:281mm;position:relative}header{height:18mm;display:flex;justify-content:space-between;align-items:start;border-bottom:.7mm solid #222;margin-bottom:5mm}
h1{font:25pt/1 Georgia,serif;margin:0 0 1.2mm;letter-spacing:.4mm}h2{font:bold 14pt/1.15 Georgia,serif;margin:0 0 2mm}h3{font:bold 11pt/1.2 Georgia,serif;margin:0 0 1.2mm}p{margin:0 0 2.5mm}.sub{font-size:8pt;letter-spacing:.3mm;text-transform:uppercase}.number{font:20pt Georgia;text-align:right}.number small{display:block;font:7pt Arial;margin-top:1mm;letter-spacing:.4mm}
.footer{position:absolute;bottom:0;left:0;right:0;border-top:.3mm solid #444;padding-top:1.5mm;font-size:7pt;display:flex;justify-content:space-between;gap:4mm;height:8mm}.calibration{min-width:50mm;border-top:.3mm solid #222;text-align:center;padding-top:1mm}
.panel-symbol,.glyph{width:6mm;height:6mm;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linejoin:round;stroke-linecap:round;vertical-align:middle}.mana-symbol{width:6mm;height:6mm;fill:none;stroke:currentColor;stroke-width:1.65;stroke-linecap:round;stroke-linejoin:round}.mana-passive-symbol{display:inline-flex;align-items:center;justify-content:center;border-radius:50%;width:9mm;height:9mm;flex-shrink:0}
.vitals{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;margin-bottom:4mm}.vital{border:.3mm solid #777;padding:2mm 3mm}.vital b{display:block;font:bold 22pt Georgia}.vital label{font-size:8pt;text-transform:uppercase}.vital small{font-size:8pt}
.stats{display:grid;grid-template-columns:repeat(6,1fr);border-bottom:.4mm solid #222;padding-bottom:4mm;margin-bottom:5mm}.stat{text-align:center;border-right:.2mm solid #aaa}.stat:last-child{border:0}.stat label{display:block;font-size:8pt}.stat b{font:bold 19pt Georgia}.stat span{margin-left:1.5mm;font-size:11pt}.note{font-size:8.5pt;color:#444}.identity{display:grid;grid-template-columns:57mm 1fr;gap:6mm;margin-bottom:5mm}.portrait{width:57mm;height:76mm;object-fit:cover;object-position:top;filter:grayscale(1);border:.3mm solid #333}.story{font-size:10pt}.story section{margin-bottom:4mm}.quote{font:italic 12pt/1.35 Georgia;border-left:1mm solid #222;padding:1mm 4mm;margin:3mm 0 5mm}.two-cols{display:grid;grid-template-columns:1fr 1fr;gap:5mm}.box{border:.3mm solid #777;padding:3mm}.flaw{background:#f2f2f2;border-left:1.2mm solid #222;padding:3mm;margin:4mm 0}.flaw p{margin:0}.method{font-size:9pt}.method p{margin-bottom:1.5mm}.method p:last-child{margin-bottom:0}.method-context{font-size:8pt;font-weight:bold;text-transform:uppercase;letter-spacing:.15mm;border-bottom:.25mm solid #777;padding-bottom:1.3mm}.method h3{font-size:12pt;margin:2mm 0}.notes-label{font:8pt Arial;color:#555}.writing-lines{height:10mm;background:repeating-linear-gradient(white,white 5.8mm,#bbb 6mm,white 6.2mm)}
.landscape{width:281mm;height:194mm}.landscape header{height:10mm;margin-bottom:3mm}.landscape header>div:first-child{display:flex;align-items:baseline;gap:6mm}.landscape h1{font-size:19pt;margin:0}.landscape .number{font-size:13pt}.landscape .sub{font-size:7pt}.landscape .footer{height:3mm;padding-top:.5mm;font-size:6pt;border:0}.mana-grid{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:88mm 88mm;gap:3mm;height:179mm}.mana-cell{display:flex;gap:2mm;height:88mm;min-width:0}.mana-slot{width:63mm;height:88mm;flex-shrink:0;border:.3mm dashed #777;border-radius:3mm;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3mm;background:#fafafa;text-align:center}.mana-slot .mana-symbol{width:14mm;height:14mm}.mana-slot b{font:17pt Georgia}.mana-slot span{font-size:9pt}.mana-slot small{font-size:7.5pt;max-width:48mm}.mana-notes{min-width:0;flex:1;font-size:8.1pt;line-height:1.18;display:grid;grid-template-rows:9mm 37mm 1fr;gap:3mm}.mana-notes .mana-head{display:flex;align-items:center;gap:1mm;margin-bottom:0}.mana-notes .mana-passive-symbol{width:7mm;height:7mm}.mana-notes .mana-symbol{width:4.5mm;height:4.5mm}.mana-head strong{font:17pt Georgia}.mana-head small{display:block;font-size:6.5pt}.passive-block{min-height:0;border-bottom:.25mm solid #aaa;padding-bottom:1mm}.mode{font-size:7.2pt;font-weight:bold;letter-spacing:.2mm;text-transform:uppercase;margin-bottom:1.6mm;padding:1mm .8mm;border:.25mm solid #222}.combat-passive .mode{background:#222;color:white}.exploration-passive .mode{background:#eaeaea;color:#111}.mana-notes b{display:block;margin-bottom:.8mm}.mana-notes p{margin-bottom:2mm}.mana-guide{border:.4mm solid #222;padding:4mm;font-size:9.3pt}.mana-guide h2{font-size:17pt}.tiers{width:100%;border-collapse:collapse;margin:2mm 0 3mm;font-size:9pt}.tiers td,.tiers th{border-bottom:.2mm solid #bbb;text-align:center;padding:1.2mm .5mm}.ring{display:inline-block;width:3mm;height:3mm;border:.25mm solid;border-radius:50%;vertical-align:middle}.ring.thick{border-width:.8mm}
.actions{display:grid;grid-template-columns:repeat(3,62mm);grid-template-rows:repeat(3,76mm);gap:4mm}.action{border:.4mm solid #333;padding:2.4mm;position:relative;font-size:9pt;line-height:1.27}.action-head{display:flex;gap:2mm;align-items:center;min-height:11mm;border-bottom:.3mm solid #333;padding-bottom:2mm;margin-bottom:2mm}.rune{border:.3mm solid #333;width:10mm;height:10mm;display:flex;align-items:center;justify-content:center;flex-shrink:0}.action h2{font-size:12pt;margin:0}.action-meta{display:flex;justify-content:space-between;gap:1mm;font-size:8.2pt;border-bottom:.2mm solid #aaa;padding-bottom:1.5mm;margin-bottom:2mm;font-weight:bold}.action .boost{border-top:.2mm dashed #777;padding-top:1.5mm;margin-top:2mm;font-size:8.4pt}.action .boost b{display:block}.action-legend{font-size:7.7pt;line-height:1.2;margin-top:2mm}.action-legend p{margin-bottom:1mm}
.equipment-grid{display:grid;grid-template-columns:repeat(3,60mm);grid-template-rows:repeat(3,42mm) 6mm 42mm 42mm;gap:4mm 7mm}.equipment-slot{border:.3mm dashed #888;border-radius:1.5mm;padding:3mm;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:2mm;color:#555}.equipment-slot b{font:13pt Georgia}.equipment-slot small{font-size:8pt}.equipment-slot .glyph{width:9mm;height:9mm;opacity:.55}.equip-instruction{grid-column:2/4;font-size:9pt;padding:2mm 1mm}.bag-label{grid-column:1/4;border-bottom:.3mm solid #777;font-size:9pt;font-weight:bold}.equip-note{margin-top:3mm;font-size:8pt}
.cutouts{display:grid;grid-template-columns:repeat(3,60mm);grid-auto-rows:42mm;gap:6mm 7mm}.item{width:60mm;height:42mm;border:.3mm solid #333;position:relative;padding:1.5mm 2mm;background:white;display:grid;grid-template-rows:5mm 4mm 17mm 1fr;gap:.4mm}.item h2{font-size:10.5pt;margin:0;white-space:nowrap}.item .slot-label{font-size:7.4pt;text-transform:uppercase;letter-spacing:.1mm}.item-art{display:flex;align-items:center;justify-content:center;position:relative}.item-art img{width:100%;height:17mm;object-fit:contain}.item-art .die{position:absolute;right:0;bottom:1mm;width:8mm;height:8mm;background:white}.item-art .quantity{position:absolute;left:0;bottom:1mm;background:white;border:.25mm solid #444;border-radius:50%;padding:1mm;font:bold 9pt Arial}.item .effect{font-size:8.1pt;font-weight:bold;line-height:1.1}.item .effect .glyph{width:3.5mm;height:3.5mm}.item .detail{font-size:6.9pt;line-height:1.15;margin-top:.4mm}.cut-guide{margin-top:8mm;font-size:10pt}.legend-row{display:flex;gap:4mm;align-items:center;margin:4mm 0}.die{width:8mm;height:8mm;flex-shrink:0;fill:white;stroke:#222;stroke-width:1.3}.die text{stroke:none;fill:#222;font:bold 9px Arial}
.cheat-grid{display:grid;grid-template-columns:1fr 1fr;gap:3.5mm;font-size:9pt;line-height:1.3}.cheat-grid section{border-top:.6mm solid #222;padding-top:2mm}.cheat-grid h2{font-size:14pt}.cheat-grid ul,.cheat-grid ol{padding-left:5mm;margin:2mm 0}.cheat-grid li{margin-bottom:1.4mm}.wide{grid-column:1/3}.formula{font:14pt Georgia;border:.3mm solid #777;padding:3mm;margin-bottom:4mm;text-align:center}.controls{display:flex;justify-content:space-between;gap:2mm;font-size:8pt;margin-top:3mm}.controls span{display:flex;align-items:center;gap:1mm}.controls .glyph{width:4mm;height:4mm}
@media screen{body{background:#ddd}.page{background:white;margin:8mm auto;box-shadow:0 2px 10px #0003}}
@media print{*{-webkit-print-color-adjust:exact;print-color-adjust:exact}.page{break-inside:avoid}}
"""


def icon(kind: str) -> str:
    paths = {
        "sword": "M5 19 18 6l3-3v6L8 22M3 14l7 7M5 21l-2 2",
        "shield": "M12 2 3 6v7c0 5 9 9 9 9s9-4 9-9V6ZM12 6v12M7 11h10",
        "arrow": "M3 21 20 4M12 4h8v8M3 14l7 7",
        "pack": "M7 7V5a5 5 0 0 1 10 0v2M4 7h16v15H4ZM7 13h10v6H7Z",
        "head": "M5 15V9a7 7 0 0 1 14 0v6M3 15h18M9 15v6h6v-6",
        "ring": "M8 4 12 1l4 3-4 5ZM8 8a8 8 0 1 0 8 0",
        "neck": "M4 3c0 12 16 12 16 0M12 13l5 5-5 5-5-5Z",
        "focus": "M5 22 15 5M15 1v8M11 5h8M12 2l6 6M12 8l6-6",
        "hand": "M5 13V8h3V3h3v7-9h3v9-7h3v10-5h3v9l-5 6H9l-5-8Z",
        "dice": "M3 3h18v18H3ZM7 7h1M16 7h1M11 12h1M7 17h1M16 17h1",
    }
    return f'<svg class="glyph" viewBox="0 0 24 24" role="img" aria-label="{escape(kind)}"><path d="{paths[kind]}"/></svg>'


def die(sides: int) -> str:
    outlines = {
        4: 'M15 1 29 28H1Z M15 1 6 25h18Z',
        6: 'M3 7 9 2h18v20l-6 6H3Z M3 7h18v21M21 7l6-5M21 22h6',
        8: 'M15 1 28 15 15 29 2 15Z M15 1 6 23h18Z',
        12: 'M15 1 27 9v14l-12 6L3 23V9Z M15 7l8 6-3 10H10L7 13Z',
    }
    return f'<svg class="die" viewBox="0 0 30 30" aria-label="k{sides}"><path d="{outlines.get(sides, outlines[8])}"/><text x="15" y="19" text-anchor="middle">{sides}</text></svg>'


def header(title: str, subtitle: str, number: str, *, imprint: str = 'GARRAN · KONCEPT 02') -> str:
    return f'<header><div><h1>{title}</h1><div class="sub">{subtitle}</div></div><div class="number">{number}<small>{escape(imprint)}</small></div></header>'


def footer(text: str) -> str:
    return f'<footer class="footer"><span>{text}</span><span class="calibration">50 mm · druk 100% · bez dopasowania</span></footer>'


def document(body: str, *, landscape: bool = False, title: str = 'Garran · zestaw prototypowy', extra_css: str = '') -> str:
    extra = '@page{size:A4 landscape;margin:8mm}' if landscape else ''
    return f'<!doctype html><html lang="pl"><meta charset="utf-8"><title>{escape(title)}</title><style>{CSS}{extra}{extra_css}</style><body><article class="page {"landscape" if landscape else ""}">{body}</article></body></html>'


def character_page() -> str:
    hero = build_print_hero('garran')
    vitals = ''.join(f'<div class="vital"><label>{label}</label><b>{value}</b><small>{note}</small></div>' for label, value, note in (
        ('Punkty wytrzymałości', hero.hp, 'maksimum PW'), ('Klasa pancerza',hero.ac,'kolczuga 16 + tarcza 2'), ('Ruch',f'{hero.speed} ft','6 pól po 5 ft'),('Inicjatywa',f'{hero.initiative:+d}','modyfikator Zręczności')))
    stats = ''.join(f'<div class="stat"><label>{name}</label><b>{score}</b><span>{mod:+d}</span></div>' for name,score,mod in hero.abilities)
    story = ''.join(f'<section><h3>{escape(label)}</h3><p>{escape(text)}</p></section>' for label,text in hero.story)
    portrait = quote(os.path.relpath(ROOT/'content/scenarios/misja_0_dzwon/assets/images/comic_v2/garran.png', OUTPUT))
    methods = ''.join(f'<div class="box method"><p class="method-context">{"Przy rozmowie" if kind == "npc" else "Przy interakcji z obiektem"}</p><h3>Podejście ze sceny</h3><p>Wybierz runą sposób działania. Scena określa cechę, ST, kość efektu i powiązania pomocy.</p><p class="note"><b>Test:</b> k20 + cecha podejścia + naładowanie + premie.</p><p class="note"><b>{effect_name(kind)}:</b> kość podejścia + ta sama cecha + premie efektu.</p></div>' for kind in ('npc', 'object'))
    return document(header('Garran','Żelazna Straż · człowiek · poziom 3','01 / 04')+f'''
<div class="vitals">{vitals}</div><div class="stats">{stats}</div>
<div class="identity"><div><img class="portrait" src="{portrait}" alt="Garran"><p class="note">Wartość cechy — duża liczba.<br>Obok: modyfikator do rzutu.</p></div><div class="story">{story}</div></div>
<div class="quote">Lubi wiedzieć, kto za co odpowiada. Gdy nikt nie bierze odpowiedzialności za sprawę najgorszą, zwykle bierze ją na siebie.</div>
<div class="two-cols">{methods}</div>
<div class="flaw"><h3>Skaza · {hero.flaw[0]}</h3><p>{hero.flaw[1]}</p></div>
<p class="note">Bazowe statystyki zestawu startowego, bez nasycenia. Pasywy znajdują się na macie many. Zmiany wyposażenia i aktualne statusy uwzględnia aplikacja.</p>
<h3>Moje zobowiązania i cele <small class="notes-label">— do uzupełnienia podczas gry</small></h3><div class="writing-lines"></div>
'''+footer('Postać · historia i statystyki · arkusz pozostaje w całości'))


def passive(text: str) -> str:
    for ending in ('. Nie kumuluje się.', ' Nie kumuluje się.', '. Kumuluje się.', ' Kumuluje się.', ' (bez kumulacji)'):
        text = text.replace(ending, '')
    name, _, body = text.partition(': ')
    return f'<b>{escape(name)}</b><p>{escape(body.rstrip(".") + ".")}</p>'


def mana_page() -> str:
    hero = build_print_hero('garran')
    assert hero.stacking_mana_colors == hero.stacking_exploration_colors
    cells = []
    for color in ORDER:
        value = dict(hero.mana_values)[color]
        cells.append(f'''<section class="mana-cell" data-color="{color}"><div class="mana-slot" data-width-mm="63" data-height-mm="88">{mana_symbol(color)}<b>{COLORS[color]}</b><span>{value} pkt / karta</span><small>Miejsce na karty 63 × 88 mm.<br>Ten sam kolor układaj w stos.</small></div><div class="mana-notes"><div class="mana-head">{passive_mana_symbol(color,color in hero.stacking_mana_colors)}<div><strong>{value}</strong><small>pkt / karta</small></div></div><section class="passive-block combat-passive"><div class="mode">Walka</div>{passive(dict(hero.mana_passives)[color])}</section><section class="passive-block exploration-passive"><div class="mode">Eksploracja</div>{passive(dict(hero.exploration_passives)[color])}</section></div></section>''')
    cells.append('''<section class="mana-guide"><h2>Nasycenie maną</h2><p>Punkty odblokowują akcje i premię do testu. Kolory uruchamiają pasywy.</p><table class="tiers"><tr><th>Punkty</th><td>0–5</td><td>6–11</td><td>12–20</td><td>21+</td></tr><tr><th>Premia</th><td>+0</td><td>+2</td><td>+4</td><td>+6</td></tr></table><p><b>Poniżej 21:</b> wybierz 1 kartę z oferty na początku tury. <b>Przy 21+:</b> bez doboru i bez kary.</p><p><span class="ring thick"></span> <b>Kumuluje się</b> za kolejne karty.<br><span class="ring"></span> <b>Nie kumuluje się.</b> Wystarczy jedna.</p><p>Stosuj pasywy bieżącego trybu. Działają, dopóki masz kolor; drain usuwa nasycenie i resetuje wykorzystanie pasywów.</p><p class="note">Karty nie przykrywają opisów ani punktacji. Liczbę kart w stosie sprawdzisz także w UI.</p></section>''')
    return document(header('Garran · mana','Pięć kolorów · osobista pula · pełne miejsca na karty','02 / 04')+'<div class="mana-grid">'+''.join(cells)+'</div>',landscape=True)


def actions_page(copy: dict) -> str:
    cards=[]
    hero=build_print_hero('garran')
    for action in sorted(hero.cards,key=lambda a:a.panel_slot):
        sections=dict(action.sections)
        threshold=int(re.search(r'\d+',sections['Ładunek']).group())
        burn=int(re.search(r'\d+',sections['Spalanie']).group())
        boost=copy['boosts'].get(action.id)
        extra=f'<div class="boost"><b>Podbicie · +2 spalone karty / raz</b>{escape(boost)}</div>' if boost else ''
        cards.append(f'<section class="action" data-id="{action.id}"><div class="action-head"><div class="rune">{panel_icon(action.panel_slot)}</div><h2>{escape(action.name)}</h2></div><div class="action-meta"><span>≥ {threshold} pkt</span><span>{action.timing}</span><span>Spal: {burn}</span></div><p>{escape(copy["actions"][action.id])}</p>{extra}</section>')
    return document(header('Garran · akcje','Wybieraj odpowiadającą runę na planszy','03 / 04')+'<div class="actions">'+''.join(cards)+'</div>'+'''
<div class="action-legend"><p><b>A</b> — akcja główna · <b>D</b> — dodatkowa · <b>R</b> — reakcja. „Siła” / „Kondycja” w efektach oznacza modyfikator cechy.</p><p><b>Pula zostaje.</b> Spalanie z wierzchu wspólnej talii po efekcie, również przy niepowodzeniu. Podbicie nie wymaga koloru.</p><p>Ramki 62 × 76 mm. Nową akcją przykryj całą ramkę; musi odpowiadać runie przypisanej w aplikacji.</p></div>'''+footer('9 zdolności na jednym A4 · zwykły atak i obsługa: wspólna ściągawka'))


def equipment_page() -> str:
    slots=[('Szyja','neck'),('Głowa','head'),('Pierścień','ring'),('Pierwsza ręka','hand'),('Pancerz','shield'),('Druga ręka','hand'),('Przybory magiczne / instrument','focus')]
    markup=''.join(f'<div class="equipment-slot">{icon(symbol)}<b>{name}</b><small>1 przedmiot · 60 × 42 mm</small></div>' for name,symbol in slots)
    markup+='''<div class="equip-instruction"><h3>Przygotuj przed wyprawą</h3><p>Połóż sprzęt zgodnie ze slotami w aplikacji. Przedmiot oburęczny zajmuje obie ręce: żeton połóż na jednej, znacznik „zajęta” na drugiej.</p><p>Zmiana przedmiotu w slocie oddaje poprzedni do wspólnego zapasu. Wyposażenie jest ustalone do powrotu; zużywalnych nadal można używać.</p></div><div class="bag-label">PLECAK / PRZEDMIOTY · wspólne pole, bez limitu sześciu przedmiotów</div>'''
    markup+=''.join('<div class="equipment-slot"><small>Miejsce na żetony<br>Można układać w stos.</small></div>' for _ in range(6))
    return document(header('Garran · wyposażenie','Pusta mata · połóż na niej wycięte elementy','04 / 04')+'<div class="equipment-grid">'+markup+'</div><p class="equip-note">Start: miecz — pierwsza ręka; tarcza — druga ręka; kolczuga — pancerz. Pozostały sprzęt startowy — plecak. Nowe znaleziska w misji trafiają do wspólnego zapasu.</p>'+footer('Przerywane ramki są miejscami na żetony — nie wycinaj tej maty'))


def equipment_cutouts(copy: dict) -> str:
    tiles=[]
    for item in training_hero('garran').inventory:
        text=copy['equipment'][item.id]
        dice=die(text['die']) if 'die' in text else ''
        quantity=f'<span class="quantity">×{item.quantity}</span>' if item.quantity>1 else ''
        tiles.append(f'<section class="item" data-id="{item.id}"><h2>{escape(item.name)}</h2><div class="slot-label">{escape(text["slot"])}</div><div class="item-art">{item_art(item,print_root=OUTPUT)}{dice}{quantity}</div><div><div class="effect">{icon(text["icon"])} {escape(text["effect"])}</div><div class="detail">{escape(text["detail"])}</div></div></section>')
    return document(header('Garran · sprzęt startowy','Wytnij dziewięć elementów po zewnętrznych liniach','DO WYCIĘCIA')+'<div class="cutouts">'+''.join(tiles)+'</div>'+'''
<div class="cut-guide"><h2>Żetony pasują do maty wyposażenia</h2><p>Każdy ma <b>60 × 42 mm</b>. Nadruk na macie pozostaje pustym szablonem; nawet początkowy sprzęt jest osobnym elementem.</p><p>Przekazując przedmiot, przekaż też żeton. Zmianę wyposażenia zatwierdź w aplikacji. Nieoznaczone znaleziska trzymaj we wspólnym zapasie do przygotowania kolejnej wyprawy.</p>
<div class="legend-row">'''+icon('sword')+' obrażenia '+icon('shield')+' pancerz / KP '+die(8)+''' kość k8</div><p class="note">Symbole wspierają opis: rodzaj obrażeń, cecha, ograniczenia i miejsce pozostają zapisane słownie. Modyfikator cechy bierzesz z karty postaci.</p>
<div class="equipment-slot" style="width:60mm;height:42mm;margin-top:5mm;border-style:solid"><b>DRUGA RĘKA ZAJĘTA</b><small>Broń oburęczna znajduje się<br>w sąsiednim slocie.<br>Znacznik — wytnij.</small></div></div>'''+footer('9 przedmiotów + znacznik drugiej ręki · wyposażenie dodatkowe: przyszłe zestawy'))


def rules_page(*, imprint: str = 'GARRAN · KONCEPT 02') -> str:
    body='''<div class="formula">k20 + modyfikator cechy + naładowanie + pozostałe premie</div>
<div class="cheat-grid">
<section class="wide"><h2>Wspólna talia · osobiste pule</h2><p><b>3 / 4 / 5 / 6 bohaterów → 30 / 40 / 50 / 60 kart</b>, po równo pięciu kolorów. Nowa walka lub konfrontacja: zbierz cały komplet i przetasuj. Dla testów 1–2 postaci: 25 kart.</p><p>Na początku tury, jeśli masz mniej niż 21 pkt, wybierz <b>jedną z dwóch odkrytych kart</b>. Druga zostaje dla kolejnego gracza; ofertę uzupełniaj zgodnie z aplikacją. Przy 21+ nie dobierasz. Kolory w swojej puli przelicz według własnej maty.</p></section>
<section><h2>Walka</h2><ol><li>Dobierz manę, jeżeli masz mniej niż 21 pkt. Uaktywnij pasywy posiadanych kolorów.</li><li>Wykorzystaj ruch, akcję główną <b>A</b> i dostępną akcję dodatkową <b>D</b>. Reakcję <b>R</b> wykonujesz przy jej wyzwalaczu; odzyskujesz ją na początku własnej tury.</li><li>Wybierz atak lub zdolność runą. Rozstrzygnij cel, test i efekt, potem zgłoś wymagane spalanie.</li></ol><p><b>Zwykły atak:</b> zużywa A, nie spala many. Test ≥ KP trafia. Obrażenia: kości broni + właściwa cecha + premie obrażeń. <b>Naładowanie nie dodaje obrażeń.</b></p><p>Naturalne 1 chybia, 20 to krytyk: podwajasz kości obrażeń, nie stałe premie. Pasyw może poszerzać zakres krytyka.</p><p><b>1 pole = 5 ft.</b> Trudny teren: koszt wejścia ×2. Osłony i przeszkody stosuj według kafla oraz UI.</p><p>Po rundzie wygasa 1 karta z talii. Wrogowie mogą też spalać lub więzić manę.</p></section>
<section><h2>Eksploracja · NPC i obiekty</h2><ol><li>Cała drużyna ma tury i osobiste pule; na mapie porusza się jedną figurką.</li><li>Przed talią wybierz runą podejście ze sceny: cechę, ST, kość efektu i cele pomocy. Po doborze wybierz test, dozwoloną pomoc albo podgląd spodu talii.</li><li>Próba ≥ ST: rzuć kością podatności + cecha + premie efektu. Wynik to <b>wpływ przy rozmowie</b> lub <b>postęp przy obiekcie</b>; zmniejsza wspólny opór.</li><li>Po efekcie spal koszt próby, także po niepowodzeniu. Po rundzie rozstrzygnij reakcję sytuacji według UI.</li></ol><p><b>Podgląd:</b> obejrzyj dolną kartę; zostaw ją albo przenieś na wierzch. Całe działanie, bez spalania.</p><p><b>Pomoc:</b> +1 do najbliższej próby testu sojusznika (+2 ze Współpracą), za 1 spaloną kartę. Pomoce sumują się i cała suma znika po tej próbie, także nieudanej.</p><p>Test korzysta z najwyższej premii naładowania i spala 1 kartę. <b>21 nie gwarantuje sukcesu</b>, a przekroczenie nie daje kary. Naładowanie nie zwiększa wpływu ani postępu.</p><p><b>Opór 0 → sukces.</b> Warunki sceny mogą dawać kompromis lub dodatkową nagrodę.</p></section>
<section class="wide"><table class="tiers"><tr><th>Punkty w puli</th><td>0–5</td><td>6–11</td><td>12–20</td><td>21+</td></tr><tr><th>Premia do testu</th><td>+0</td><td>+2</td><td>+4</td><td>+6</td></tr><tr><th>Koszt próby w eksploracji</th><td>1 karta</td><td>1 karta</td><td>2 karty</td><td>3 karty</td></tr></table><p><b>W walce koszt podaje akcja</b>; każde jej podbicie to dodatkowe 2 spalone karty, do limitu podanego w opisie. W obu trybach osobista pula pozostaje po działaniu.</p></section>
<section><h2>Mana drain</h2><p>Gdy nie można wykonać wymaganej operacji kart, najpierw rozstrzygnij rozpoczęte działanie.</p><p><b>Walka:</b> zbierz wszystkie karty, również pule, ofertę, spalone, wygasłe i uwięzione. Przetasuj. Nasycenie znika; wykorzystanie pasywów resetuje się. Ładujesz się od nowa.</p><p><b>Eksploracja:</b> drain kończy konfrontację. Jeśli opór spadł do 0, jest sukces; inaczej porażka. Nie ma dodatkowej darmowej kolejki.</p></section>
<section><h2>Pasywy, kości i ekwipunek</h2><p><span class="ring thick"></span> Gruba obwódka: kumulacja za karty.<br><span class="ring"></span> Cienka: wystarczy jeden kolor.<br>Opis określa warunek i limit. Bez koloru pasyw nie działa.</p><p><b>Przewaga / utrudnienie:</b> rzuć 2k20, wybierz wyższy / niższy. Wpisuj wyniki naturalne, bez samodzielnego dodawania premii.</p><p>Sprzęt przydzielasz w bazie. W misji wyposażenie pozostaje ustalone; zużywalnych można używać. Znaleziska trafiają do wspólnego zapasu.</p></section>
</div>'''
    controls='<div class="controls">'+''.join(f'<span>{panel_icon(slot)} {label}</span>' for slot,label in [(1,'atak'),(3,'przedmiot'),(5,'koniec tury'),(26,'zmniejsz'),(27,'zwiększ'),(28,'zatwierdź'),(29,'wróć')])+'</div>'
    return document(header('Ściągawka drużyny','Wydrukuj jedną kopię dla wszystkich graczy','ZASADY',imprint=imprint)+body+controls+footer('Rzuty: fokus → −/+ → podsumowanie → zatwierdź · pełne efekty i wyjątki podaje UI'), title='Ściągawka drużyny')


def validate_html(path: Path, *, action_mm: tuple[float, float] = (62, 76)) -> list[dict]:
    """Check actual Chrome layout, assets, true-size pieces and text boundaries."""
    script='''<script>addEventListener('load',()=>{const issues=[];const page=document.querySelector('.page').getBoundingClientRect();for(const e of document.querySelectorAll('.page,.action,.mana-guide,.mana-notes,.passive-block,.mana-slot,.item,.equipment-slot,.cheat-grid,.cut-guide')){const b=e.getBoundingClientRect();if(e.scrollHeight>e.clientHeight+2||e.scrollWidth>e.clientWidth+2)issues.push({kind:'overflow',class:e.className,text:e.innerText.slice(0,70)});if(b.bottom>page.bottom+2||b.right>page.right+2)issues.push({kind:'outside',class:e.className});}for(const i of document.images){if(!i.complete||!i.naturalWidth)issues.push({kind:'image',src:i.src});}const f=document.querySelector('.footer');if(f){const fb=f.getBoundingClientRect();for(const e of document.querySelector('.page').children){if(e===f)continue;if(e.getBoundingClientRect().bottom>fb.top+1)issues.push({kind:'footer-overlap',class:e.className});}}const sizes={'.mana-slot':[63,88],'.action':[62,76],'.item':[60,42]};for(const [s,[w,h]]of Object.entries(sizes)){for(const e of document.querySelectorAll(s)){const b=e.getBoundingClientRect();if(Math.abs(b.width*25.4/96-w)>.1||Math.abs(b.height*25.4/96-h)>.1)issues.push({kind:'size',selector:s});}}const out=document.createElement('pre');out.id='validation-result';out.textContent=JSON.stringify(issues);document.body.append(out);});</script>'''
    script = script.replace("'.action':[62,76]", "'.action':" + json.dumps(action_mm))
    check=path.with_name('_check_'+path.name)
    check.write_text(path.read_text().replace('</body>',script+'</body>'))
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    try:
        with TemporaryDirectory(prefix='garran-layout-') as temporary:
            result=subprocess.run([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-background-networking',f'--user-data-dir={temporary}','--dump-dom',check.as_uri()],capture_output=True,text=True,check=True,timeout=30)
        match=re.search(r'<pre id="validation-result">(.*?)</pre>',result.stdout,re.S)
        if not match:
            raise RuntimeError('Brak wyniku kontroli układu')
        return json.loads(match.group(1))
    finally:
        check.unlink(missing_ok=True)


def main() -> None:
    """Build the current monochrome handouts from the canonical catalog."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_rune_relations import main as build_current
    build_current()


if __name__=='__main__':
    main()

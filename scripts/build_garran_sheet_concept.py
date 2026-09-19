"""Garran sheet 1/3 concept: true-scale A4 and a layered tabletop preview."""
from __future__ import annotations

from html import escape
from pathlib import Path
import json
import sys
import shutil
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from dnd_board_game.physical_cards.mana_print import build_print_hero, COLORS
from dnd_board_game.physical_cards.mana_symbols import mana_symbol, passive_mana_symbol
from dnd_board_game.physical_cards.mana_print_files import render_pdf

OUTPUT = ROOT / 'content/print/prototypes/garran_trio_v1'
SHEET_WIDTH, SHEET_HEIGHT = 190, 277
CARD_WIDTH, CARD_HEIGHT = 88, 63  # Standard card rotated sideways.
SLOT_HEIGHT, EXPOSED = 66, 18  # Clearance for a typical sleeve.
ROW_TOP, ROW_HEIGHT = 87, 33.5
COLORS_ORDER = ('C', 'B', 'Z', 'F', 'N')

CSS = '''
@page { size: A4; margin:10mm; }
*{box-sizing:border-box}body{margin:0;color:#161616;font:9.4pt/1.24 Arial,sans-serif;background:#e9e7e3}
.sheet{width:190mm;height:277mm;background:white;position:relative;border:.25mm solid #555;z-index:2}
.core{position:absolute;left:16mm;right:16mm}
header{top:6mm;height:16mm;display:flex;justify-content:space-between;align-items:flex-start;border-bottom:.6mm solid #171717}
h1{font:bold 26pt/1 Georgia,serif;letter-spacing:.7mm;margin:0 0 1mm}
.subtitle{font-size:8pt;letter-spacing:.16mm}.sheet-number{text-align:right;font-size:7.5pt;letter-spacing:.3mm;padding-top:1mm}.sheet-number b{display:block;font:22pt/1 Georgia,serif;margin-bottom:1mm}
.vitals{top:25mm;height:12mm;display:grid;grid-template-columns:repeat(4,1fr);gap:2mm}
.vital{border-bottom:.25mm solid #555;display:flex;flex-direction:column;justify-content:space-between}.vital label{font-size:7.5pt;letter-spacing:.35mm;text-transform:uppercase}.vital b{font-size:18pt;line-height:1}.vital em{font-style:normal;font-size:9pt;font-weight:normal}
.abilities{top:40mm;height:12mm;display:grid;grid-template-columns:repeat(6,1fr);gap:1mm}.ability{text-align:center;border-right:.2mm solid #ccc}.ability:last-child{border:0}.ability label{display:block;font-size:7.3pt;margin-bottom:1.1mm}.ability b{font-size:14pt}.ability span{font-size:9pt;margin-left:1.1mm;color:#444}
.flaw{top:55mm;height:12mm;padding:1.4mm 2mm;border-left:1mm solid #222;background:#f1f1f1;font-size:8.8pt}.flaw b{font-size:9pt}.flaw p{margin:.5mm 0 0}.eyebrow{font-size:7pt;letter-spacing:.3mm;text-transform:uppercase;margin-right:2mm}
.charge{top:69mm;height:10mm;display:flex;align-items:center;justify-content:space-between;gap:2mm;font-size:8pt}.charge b{font-size:9.6pt}.thresholds{display:flex;gap:1mm}.thresholds span{border:.25mm solid #aaa;padding:1mm 1.8mm;text-align:center;white-space:nowrap}.thresholds strong{font-size:10pt}.thresholds small{font-size:7pt}
.table-head{top:79mm;height:8mm;display:grid;grid-template-columns:26mm 1fr 1fr;align-items:center;border-bottom:.6mm solid #222;font-size:7.7pt;font-weight:bold;letter-spacing:.4mm;text-transform:uppercase}.table-head>div:not(:first-child){padding-left:2.5mm}
.mana-row{height:33.5mm;display:grid;grid-template-columns:26mm 1fr 1fr;border-bottom:.2mm solid #999}.mana-row:nth-of-type(2n){background:#f6f6f6}.color-cell{padding:2.2mm 1mm 1mm 0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1mm;border-right:.2mm solid #ccc}.color-cell .name{font-size:8pt}.points{display:flex;align-items:baseline;gap:1mm}.points b{font: bold 23pt/1 Georgia,serif}.points span{font-size:8pt}.passive{padding:3mm 2.3mm 2mm;font-size:9.4pt;line-height:1.26}.passive:last-child{border-left:.2mm solid #ddd}.passive b{display:block;font-size:10pt;margin-bottom:1.2mm}.passive p{margin:0}
.mana-symbol{width:6mm;height:6mm;fill:none;stroke:currentColor;stroke-width:1.65;stroke-linecap:round;stroke-linejoin:round;vertical-align:middle}.mana-passive-symbol{width:9mm;height:9mm;border-radius:50%;display:inline-flex;align-items:center;justify-content:center}
.slot{position:absolute;width:12mm;height:66mm;border:.25mm dashed #aaa;border-radius:2mm;display:flex;align-items:center;justify-content:center;background:#fafafa}.slot.left{left:-.25mm;border-left:0;border-radius:0 2mm 2mm 0}.slot.right{right:-.25mm;border-right:0;border-radius:2mm 0 0 2mm}.slot .arrow{position:absolute;top:3mm;font-size:13pt}.slot .vertical{position:absolute;bottom:4mm;writing-mode:vertical-rl;font-size:7pt;letter-spacing:.3mm;color:#555}.slot .mana-symbol{position:absolute;top:calc(50% - 2.5mm);width:5mm;height:5mm}
.legend{top:259mm;height:12mm;border-top:.6mm solid #222;padding-top:2mm;font-size:7.4pt;line-height:1.3}.legend p{margin:0 0 1mm}.frame-example{display:inline-block;width:3mm;height:3mm;border:1px solid currentColor;border-radius:50%;vertical-align:middle;margin:0 1mm}.frame-example.thick{border-width:3px}.mini{font-size:7pt;color:#444}
.cut-label{position:absolute;top:1mm;left:16mm;font-size:6.5pt;color:#555;letter-spacing:.2mm;white-space:nowrap}.calibration{position:absolute;bottom:1mm;left:16mm;width:50mm;border-top:.3mm solid #222;text-align:center;font-size:6.5pt}.calibration:before,.calibration:after{content:'';position:absolute;top:-1mm;height:2mm;border-left:.25mm solid #222}.calibration:before{left:0}.calibration:after{right:0}
.paper{width:210mm;min-height:297mm;margin:8mm auto;padding:10mm;background:white}.page-caption{max-width:900px;margin:30px auto 20px;font:15px/1.4 Arial,sans-serif}.page-caption h2{font:28px Georgia,serif;margin:0 0 6px}.page-caption p{margin:0}
.tabletop{position:relative;width:232mm;height:291mm;margin:20px auto 30px}.tabletop .sheet{position:absolute;top:7mm;left:21mm;box-shadow:0 4px 14px #0004}.tabletop .cut-label,.tabletop .calibration{display:none}.card{position:absolute;width:88mm;height:63mm;border:1.2mm solid #202020;border-radius:3mm;background:repeating-linear-gradient(45deg,#fafafa,#fafafa 2mm,#eee 2mm,#eee 2.3mm);z-index:1;box-shadow:0 2px 4px #0003}.card-strip{position:absolute;top:0;bottom:0;width:18mm;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:3mm;background:#eee;border-radius:2mm}.card.left .card-strip{left:0}.card.right .card-strip{right:0}.card-strip .mana-symbol{width:9mm;height:9mm}.card-strip small{font-size:7pt;writing-mode:vertical-rl}.demo .sheet{border-color:#222}
@media print{body{background:white}.paper{padding:0;margin:0;min-height:0;width:auto}.page-caption{display:none}.sheet{break-inside:avoid}.demo{display:none}}
'''


def passive_text(text: str) -> str:
    # Border legend carries the duplicate stacking sentence; numerical caps stay.
    for suffix in ('. Nie kumuluje się.', ' Nie kumuluje się.', '. Kumuluje się.', ' Kumuluje się.', ' (bez kumulacji)'):
        text = text.replace(suffix, '')
    name, _, body = text.partition(': ')
    return f'<b>{escape(name)}</b><p>{escape(body.rstrip(".") + ".")}</p>'


def sheet() -> str:
    hero = build_print_hero('garran')
    combat, exploration = dict(hero.mana_passives), dict(hero.exploration_passives)
    values = dict(hero.mana_values)
    rows, slots = [], []
    for index, color in enumerate(COLORS_ORDER):
        side = 'left' if index % 2 == 0 else 'right'
        center = ROW_TOP + (index + .5) * ROW_HEIGHT
        stacked = color in hero.stacking_mana_colors
        # Garran's current stacking flags match in both modes, so one symbol suffices.
        assert stacked == (color in hero.stacking_exploration_colors)
        slots.append(f'<aside class="slot {side}" data-color="{color}" style="top:{center-SLOT_HEIGHT/2}mm"><span class="arrow">{"→" if side=="left" else "←"}</span><span class="vertical">POD ARKUSZ</span>{mana_symbol(color)}</aside>')
        rows.append(f'<section class="mana-row core" data-color="{color}" style="top:{ROW_TOP+index*ROW_HEIGHT}mm"><div class="color-cell">{passive_mana_symbol(color,stacked)}<span class="name">{COLORS[color]}</span><div class="points"><b>{values[color]}</b><span>pkt / karta</span></div></div><div class="passive combat">{passive_text(combat[color])}</div><div class="passive exploration">{passive_text(exploration[color])}</div></section>')
    abilities = ''.join(f'<div class="ability"><label>{escape(name)}</label><b>{score}</b><span>({mod:+d})</span></div>' for name,score,mod in hero.abilities)
    vitals = ''.join(f'<div class="vital"><label>{label}</label><b>{value} <em>{unit}</em></b></div>' for label,value,unit in [('PW',hero.hp,'maks.'),('KP',hero.ac,'bazowe'),('Ruch',hero.speed,'ft'),('Inicjatywa',f'{hero.initiative:+d}','')])
    return f'''<article class="sheet">
<div class="cut-label">KONCEPT · wytnij po zewnętrznym obrysie · 190 × 277 mm</div>
<header class="core"><div><h1>{escape(hero.name.upper())}</h1><span class="subtitle">ŻELAZNA STRAŻ · POZIOM {hero.level}</span></div><div class="sheet-number"><b>01 / 03</b>POSTAĆ I NASYCENIE</div></header>
<div class="vitals core">{vitals}</div><div class="abilities core">{abilities}</div>
<div class="flaw core"><span class="eyebrow">Skaza · walka</span><b>{escape(hero.flaw[0])}</b><p>{escape(hero.flaw[1])}</p></div>
<div class="charge core"><div><b>k20 + cecha + naładowanie + premie</b><br><span class="mini">Suma punktów many określa dostępny bonus.</span></div><div class="thresholds">{''.join(f'<span><small>{p} pkt</small><br><strong>+{b}</strong></span>' for p,b in [('0–5',0),('6–11',2),('12–20',4),('21+',6)])}</div></div>
<div class="table-head core"><div>Osobista mana</div><div>Walka</div><div>Eksploracja</div></div>
{''.join(rows)}{''.join(slots)}
<footer class="legend core"><p><span class="frame-example thick"></span> <b>Kumuluje się</b> za kolejne karty tego koloru. <span class="frame-example"></span> <b>Nie kumuluje się.</b></p><p>Pasyw działa, gdy masz kolor. Utrata koloru lub drain wyłącza pasyw. Stosuj kolumnę bieżącego trybu.</p></footer>
<div class="calibration">50 mm · drukuj w skali 100%</div></article>'''


def document(*, demo: bool = False) -> str:
    body = sheet()
    if demo:
        cards = []
        for i,color in enumerate(COLORS_ORDER):
            side = 'left' if i%2==0 else 'right'
            center = ROW_TOP+(i+.5)*ROW_HEIGHT
            left = 21-EXPOSED if side=='left' else 21+SHEET_WIDTH-(CARD_WIDTH-EXPOSED)
            # A second red card demonstrates counting with a small horizontal fan.
            copies = (3,0) if color=='C' else (0,)
            for extra in copies:
                offset = -extra if side=='left' else extra
                cards.append(f'<div class="card {side}" style="left:{left+offset}mm;top:{7+center-CARD_HEIGHT/2}mm"><div class="card-strip">{mana_symbol(color)}<small>KARTA MANY</small></div></div>')
        body='<div class="page-caption"><h2>Garran · pierwszy arkusz zestawu</h2><p>Widok ułożenia: karty 63 × 88 mm obrócone bokiem, wsunięte pod arkusz.<br>Wystaje 18 mm. Kolejne karty tego samego koloru możesz wysunąć o 3 mm dalej.</p></div><div class="tabletop">'+''.join(cards)+body+'</div>'
    else:
        body='<div class="paper">'+body+'</div>'
    return '<!doctype html><html lang="pl"><meta charset="utf-8"><title>Garran · koncept arkusza 1/3</title><style>'+CSS+'</style><body class="'+('demo' if demo else 'print-sheet')+'">'+body+'</body></html>'


def main() -> None:
    OUTPUT.mkdir(parents=True,exist_ok=True)
    target=OUTPUT/'garran_01_postac_i_mana_A4.html'
    target.write_text(document(),encoding='utf-8')
    (OUTPUT/'garran_ulozenie.html').write_text(document(demo=True),encoding='utf-8')
    render_pdf(target,target.with_suffix('.pdf'))
    info = subprocess.run(['pdfinfo',str(target.with_suffix('.pdf'))], capture_output=True,text=True,check=True,timeout=15).stdout
    pages = next(line.split(':')[1].strip() for line in info.splitlines() if line.startswith('Pages:'))
    if pages != '1':
        raise RuntimeError('Koncept musi mieścić się na jednej stronie A4.')
    subprocess.run(['pdftoppm','-singlefile','-scale-to','1600','-png',str(target.with_suffix('.pdf')),str(OUTPUT/'garran_01_podglad')],check=True,timeout=30,capture_output=True)
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    with TemporaryDirectory(prefix='garran-sheet-preview-') as temporary:
        subprocess.run([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
            '--no-first-run','--disable-background-networking',f'--user-data-dir={temporary}',
            '--window-size=1100,1330',f'--screenshot={OUTPUT / "garran_ulozenie.png"}',
            (OUTPUT/'garran_ulozenie.html').as_uri()],check=True,timeout=30,capture_output=True)
    (OUTPUT/'dimensions.json').write_text(json.dumps(dict(
        paper_mm=[210,297],sheet_mm=[SHEET_WIDTH,SHEET_HEIGHT],card_mm=[63,88],
        card_orientation='landscape',exposed_mm=EXPOSED,slot_height_mm=SLOT_HEIGHT,
        row_pitch_mm=ROW_HEIGHT,same_side_pitch_mm=2*ROW_HEIGHT,
        slots=[dict(color=c,side='left' if i%2==0 else 'right',center_y_mm=ROW_TOP+(i+.5)*ROW_HEIGHT) for i,c in enumerate(COLORS_ORDER)]),indent=2)+'\n')
    print(target.with_suffix('.pdf'))

if __name__=='__main__':
    main()

"""Export one framed cart prototype; keep the approved tile set unchanged."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import shutil
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from dnd_board_game.physical_cards.mana_print_files import render_pdf
from dnd_board_game.physical_cards.handout_files import HANDOUT_BUILD_ROOT

PACK = ROOT/'content/scenarios/misja_0_dzwon'
OUTPUT = PACK/'maps/prototypes/cart_v3'
WORK = HANDOUT_BUILD_ROOT / 'cart_sample'


def tile(image_uri: str, scale: float = 1) -> str:
    """The whole tile, including its caption, fits within two 25 mm cells."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{50*scale:g}mm" height="{25*scale:g}mm"
        viewBox="0 0 50 25" font-family="DejaVu Sans,Arial,sans-serif">
      <rect x=".15" y=".15" width="49.7" height="24.7" fill="white" stroke="black" stroke-width=".3"/>
      <image href="{image_uri}" x="1.5" y="1.5" width="47" height="17.5" preserveAspectRatio="xMidYMid meet"/>
      <rect x="1" y="1" width="48" height="18.5" fill="none" stroke="black" stroke-width=".35"/>
      <text x="25" y="22.7" font-size="2.5" text-anchor="middle"><tspan font-weight="bold">Wóz</tspan><tspan> — blokuje ruch</tspan></text>
      <path d="M25 0v.8M25 24.3v.7" stroke="black" stroke-width=".2"/>
    </svg>'''


def main() -> None:
    image = OUTPUT/'wagon_ink.png'
    uri = 'data:image/png;base64,'+base64.b64encode(image.read_bytes()).decode('ascii')
    spec = json.loads((PACK/'maps/cutouts.json').read_text())
    WORK.mkdir(parents=True, exist_ok=True)
    for name, scale, label in [('cart_sample_A4',spec['print_scale'],'Kalibracja areny 250/244'),
                                ('cart_sample_A4_25mm',1,'Nominalne pole 25 mm')]:
        html=f'''<!doctype html><html lang="pl"><meta charset="utf-8"><title>Wóz — próbka kafla</title>
        <style>@page{{size:A4;margin:15mm}}body{{margin:0;font:11pt Arial,sans-serif;color:black}}
        h1{{font-size:18pt}}.tile{{margin:10mm 0}}svg{{display:block}}p{{line-height:1.5}}</style>
        <h1>Wóz — próbka kafla 2 × 1</h1>
        <p>{label}. Druk 100%, bez dopasowania do strony.<br>
        Wytnij zewnętrzny obrys — całość zajmuje dwa pola, razem z podpisem.</p>
        <div class="tile">{tile(uri,scale)}</div>
        <p>Ramka z ilustracją biegnie przez oba pola.<br>
        Pod ramką jedna linia: pogrubiona nazwa, myślnik i zwykły opis działania.<br>
        Małe kreski na krawędziach wskazują granicę pól.</p>
        <p>W walce cały kafel blokuje wejście i widoczność.<br>
        Wóz ustaw na polach (9,24) i (10,24); na drodze: (9,17) i (10,17).</p>
        <svg xmlns="http://www.w3.org/2000/svg" width="{110*scale:g}mm" height="10mm" viewBox="0 0 {110*scale:g} 10">
        <path d="M0 3h{100*scale:g}M.15 1v4M{100*scale:g} 1v4" stroke="black" stroke-width=".3"/>
        <text x="0" y="9" font-family="Arial" font-size="3">Odcinek kontrolny: 100 mm po wydruku.</text></svg></html>'''
        path=WORK/f'{name}.html';path.write_text(html)
        render_pdf(path,path.with_suffix('.pdf'))
        print(path.with_suffix('.pdf'),flush=True)
    # Review image is produced by rendering this layout in the browser.
    (WORK/'preview.html').write_text('''<!doctype html><html><meta charset="utf-8">
    <style>html,body{margin:0;width:1000px;height:500px;overflow:hidden;background:white}
    svg{display:block;width:1000px;height:500px}</style>'''+tile(uri))
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        raise RuntimeError('Podgląd wymaga Chrome/Chromium.')
    with TemporaryDirectory(prefix='cart-preview-') as profile:
        subprocess.run([chrome,'--headless','--no-sandbox','--disable-gpu',
            '--disable-dev-shm-usage','--hide-scrollbars','--no-first-run',
            '--disable-background-networking','--force-device-scale-factor=1',
            '--window-size=1000,500',f'--user-data-dir={profile}',
            f'--screenshot={WORK / "cart_preview.png"}',
            (WORK/'preview.html').as_uri()],check=True,capture_output=True,timeout=60)
    print(WORK/'cart_preview.png',flush=True)


if __name__=='__main__':
    main()

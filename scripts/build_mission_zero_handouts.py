"""Build the two player handouts from editable, spoiler-free scenario data."""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from dnd_board_game.physical_cards.mana_print_files import render_pdf, merge_pdfs


def render(data: dict[str, object]) -> str:
    paragraphs = ''.join(f'<p>{escape(p)}</p>' for p in data['paragraphs'])
    headers = ''.join(f'<th>{escape(h)}</th>' for h in data['headers'])
    rows = ''.join('<tr>'+''.join(f'<td>{escape(c)}</td>' for c in row)+'</tr>' for row in data['rows'])
    after = ''.join(f'<p>{escape(p)}</p>' for p in data['after'])
    return f'''<!doctype html><html lang="pl"><meta charset="utf-8"><title>{escape(data['title'])}</title>
<style>@page{{size:A4;margin:19mm}}*{{box-sizing:border-box}}body{{font:12pt Georgia,serif;color:#111;margin:0;line-height:1.6}}article{{border:2px solid #222;padding:9mm;min-height:247mm}}h1{{font-size:25pt;line-height:1.2;margin:2mm 0 4mm}}small{{display:block;border-bottom:2px solid;padding-bottom:5mm}}table{{border-collapse:collapse;width:100%;margin:8mm 0;font:10pt Georgia,serif}}th,td{{border:1px solid;padding:3mm;text-align:left}}th{{background:#eee}}td:first-child{{min-width:20mm}}footer{{margin-top:9mm;display:flex;justify-content:space-between;align-items:center;gap:8mm}}.seal{{border:3px double;border-radius:50%;width:36mm;height:25mm;display:flex;align-items:center;text-align:center;padding:3mm;font:bold 8pt Georgia,serif}}</style>
<article><h1>{escape(data['title'])}</h1><small>{escape(data['subtitle'])}</small>{paragraphs}<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>{after}<footer><p>{escape(data['signature'])}<br>________________________</p><div class="seal">{escape(data['seal'])}</div></footer></article></html>'''


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html-only',action='store_true')
    args=parser.parse_args()
    folder=ROOT/'content/scenarios/misja_0_dzwon/print'
    data=json.loads((folder/'handouts.json').read_text())
    outputs=[]
    for key, name in [('order','rozkaz_A4'),('receipts','pokwitowania_A4')]:
        html=folder/(name+'.html');html.write_text(render(data[key]),encoding='utf-8')
        if not args.html_only:
            pdf=html.with_suffix('.pdf');render_pdf(html,pdf);outputs.append(pdf)
        print(html if args.html_only else html.with_suffix('.pdf'),flush=True)
    if outputs:merge_pdfs(outputs,folder/'dokumenty_A4.pdf')


if __name__=='__main__':main()

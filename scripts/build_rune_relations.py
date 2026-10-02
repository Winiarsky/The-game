"""Build the current v0.3 character cards and shared player aid."""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
from html import escape
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import build_hero_mats as mats
import build_rune_baskets as baskets
from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.character_creation.runes import apply_rune_profile
from dnd_board_game.physical_cards.mana_print import build_print_hero
from dnd_board_game.physical_cards.mana_print_files import merge_pdfs, render_pdf
from dnd_board_game.physical_cards.handout_files import (
    HANDOUTS_ROOT, HANDOUT_BUILD_ROOT, compact_pdf, pdf_pages, publish_pdf,
)
from dnd_board_game.physical_cards.rune_relations import CSS, action_cards, action_mat, glyph, hero_rules
from dnd_board_game.scenarios.character_text import print_copy
from dnd_board_game.scenarios.rune_relation_catalog import load_rune_relation_catalog, load_rune_relation_player_aid
from dnd_board_game.ui.board_panel_symbols import SYMBOLS
from dnd_board_game.ui.training_arena import training_hero

CATALOG = ROOT / 'content/print/rune_relations_v03/catalog.json'
OUTPUT = HANDOUT_BUILD_ROOT / 'characters'
REFERENCE_OUTPUT = HANDOUT_BUILD_ROOT / 'reference'
PAGES_PER_HERO = 5
VALIDATE = baskets.VALIDATE.replace('.basket-action-slot', '.charge-slot').replace(
    '.basket-action', '.charge-card').replace('.basket-cell', '.charge-personal section')
VALIDATE = VALIDATE.replace('.charge-card,.charge-slot', '.charge-card,.charge-slot,.goal-slot')


def load_catalog() -> dict[str, Any]:
    return load_rune_relation_catalog(CATALOG)


def page(title: str, subtitle: str, number: str, content: str) -> str:
    return ('<article class="page charge-page">' + mats.base.header(escape(title), escape(subtitle), number,
            imprint='RELACJE RUN · V0.3') + content +
            mats.base.footer('Relacje run v0.3 · A4, 100%') + '</article>')


def render_hero(hero_id: str, catalog: dict[str, Any], output: Path = OUTPUT) -> str:
    hero = deepcopy(catalog['heroes'][hero_id])
    copy = print_copy()
    base = build_print_hero(hero_id, rune_profile=True)
    story = tuple((label, text) for label, text in base.story if label != 'Cel osobisty')
    story += ((hero['vignette']['title'], hero['vignette']['text']),)
    model = replace(base, flaw=(hero['flaw']['name'], hero['flaw']['description']), story=story)
    actor = apply_rune_profile(training_hero(hero_id))
    for card in hero['cards']:
        for source, ability in [('Siły', 'Siła'), ('Mądrości', 'Mądrość'),
                                ('Charyzmy', 'Charyzma'), ('Inteligencji', 'Inteligencja')]:
            card['effect'] = card['effect'].replace(f'ST {source}', f'ST 10 + {ability}')
    character = baskets.body_only(mats.character_page(model, {
        **copy['heroes'][hero_id], 'flaw': hero['flaw']['description']}, output))
    character = character.replace('01 / 04', '01 / 05').replace('ZESTAW 02', 'RELACJE V0.3')
    character = character.replace('bez nasycenia', 'wartość bazowa')
    character = character.replace('class="page character-page"', 'class="page character-page charge-character"')
    character = re.sub(r'<section class="commitments">.*?</section>',
                       hero_rules(hero, catalog['rules']['regeneration_die']), character, flags=re.S)
    equipment = baskets.body_only(mats.equipment_page(model))
    equipment = equipment.replace('04 / 04', '03 / 05').replace('ZESTAW 02', 'RELACJE V0.3')
    equipment = equipment.replace('Znaczniki zajętej drugiej ręki są w osobnym pliku znaczniki_A4.pdf.',
                                  'Dla sprzętu oburęcznego zaznacz zajętą drugą rękę.')
    cutouts = baskets.body_only(mats.equipment_cutouts(model, copy['equipment'], output, actor=actor))
    cutouts = cutouts.replace('WYCINANKI', '05 / 05').replace('ZESTAW 02', 'RELACJE V0.3')
    cutouts = cutouts.replace('Osobne noże mają osobne żetony. ', '')
    cutouts = cutouts.replace('Wspólne zasady znajdziesz w sciaga_graczy_A4.pdf, a znaczniki i legendę w znaczniki_A4.pdf.',
                              'Cel osobisty i postęp: strona 2. Warunki mocy i relacje run: strona 4.')
    parts = [character,
             page(f'{model.name} · zdolności', 'Zdolności i cel osobisty · nie wycinaj', '02 / 05', action_mat(hero)),
             equipment,
             page(f'{model.name} · wytnij zdolności', 'Karty 60 × 54 mm · tnij po zewnętrznych liniach', '04 / 05', action_cards(hero, catalog)),
             cutouts]
    return ('<!doctype html><html lang="pl"><meta charset="utf-8"><title>' + escape(model.name) +
            ' · relacje run v0.3</title><style>' + mats.base.CSS + mats.EXTRA_CSS + CSS +
            '</style><body>' + ''.join(parts) + '</body></html>')


def render_index(output: Path, catalog: dict[str, Any], manifest: dict[str, Any], *,
                 reference_output: Path = REFERENCE_OUTPUT,
                 publish_root: Path | None = HANDOUTS_ROOT) -> str:
    def link(path: Path, label: str) -> str:
        return f'<a href="{escape(os.path.relpath(path, output), quote=True)}">{escape(label)}</a>'

    rows = []
    descriptions = []
    for section in manifest['sections']:
        hero = catalog['heroes'][section['hero']]
        links = [link(output / f'{section["hero"]}.html', 'HTML')]
        if manifest['pdf']:
            links.append(link(output / f'{section["hero"]}.pdf', 'PDF · 5 stron'))
        rows.append('<tr><th>' + escape(section['name']) + '</th><td>' +
                    ', '.join(escape(card['rune']) for card in hero['cards']) + '</td><td>' +
                    ' · '.join(links) + '</td></tr>')
        skills = []
        for card in hero['cards']:
            gate = ('<p class="gate">Wyładowanie: wymaga ' + ', '.join(card['requires_resonance']) +
                    ' i legalnej kontynuacji. Po rozpatrzeniu wygasza całą pamięć, także po pudle.</p>') if card.get('ends_resonance') else ''
            bonuses = ''.join('<li><b>' + ' + '.join(escape(rune) for rune in bonus['requires']) +
                              ':</b> ' + escape(bonus['text']) + '</li>' for bonus in card['resonance_bonuses'])
            skills.append('<article class="review-card"><h3>' + glyph(card['rune']) + ' ' +
                          escape(card['name']) + f' <small>{card["cost"]} ładunków · {escape(card["budget"])}</small></h3>' +
                          gate + '<p><b>Cel:</b> ' + escape(card['target']) + '</p><p>' +
                          escape(card['requirements']) + '</p><p>' + escape(card['effect']) + '</p>' +
                          ('<ul>' + bonuses + '</ul>' if bonuses else '') + '</article>')
        descriptions.append('<section><h2>' + escape(section['name']) + '</h2><p><b>' +
                            escape(hero['passive']['name']) + ':</b> ' + escape(hero['passive']['description']) +
                            '</p><p><b>Skaza — ' + escape(hero['flaw']['name']) + ':</b> ' +
                            escape(hero['flaw']['description']) + '</p><div class="review-grid">' +
                            ''.join(skills) + '</div></section>')
    public = publish_root or output
    combined = link(public / 'characters.pdf', 'Wszystkie karty · 35 stron A4') if manifest['pdf'] else 'HTML do przeglądu'
    reference = (publish_root / 'reference') if publish_root else reference_output
    aid_link = link(reference / 'rules.pdf', 'Ściąga graczy · 3 strony A4') if manifest['pdf'] else link(reference_output / 'index.html', 'Ściąga graczy · HTML')
    markers_link = link(reference / 'markers.pdf', 'Znaczniki pomocnicze') if manifest['pdf'] else link(reference_output / 'markers.html', 'Znaczniki · HTML')
    return ('<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Relacje run v0.3 · siedmiu bohaterów</title><style>'
            '*{box-sizing:border-box}body{max-width:1160px;margin:36px auto;padding:0 24px;background:#f3f0e8;color:#262a26;font:16px/1.5 system-ui}'
            'h1,h2,h3{font-family:Georgia;line-height:1.25}h2{margin-top:36px}h3{margin-top:0}.glyph{width:28px;height:28px;vertical-align:middle}'
            '.glyph path{fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}'
            'a{color:#354e3e}table{border-collapse:collapse;width:100%;background:#fff}th,td{padding:12px;border-bottom:1px solid #ddd;text-align:left}'
            '.review-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.review-card{background:#fff;padding:20px;border:1px solid #cbc7bc;border-radius:6px}'
            '.review-card p{margin:8px 0}small{font:14px system-ui;display:block;margin-top:5px}.gate{border-left:3px solid #977128;padding-left:12px}'
            'ul{padding-left:20px}li{margin:8px 0}.notice{padding:14px;background:#e5e6dc;border-left:4px solid #354e3e}'
            '@media(max-width:700px){.review-grid{grid-template-columns:1fr}body{padding:0 14px}table{font-size:13px}}'
            '@media print{body{background:#fff;max-width:none;font-size:10pt}.review-card{break-inside:avoid}}'
            '</style></head><body><main><h1>Relacje run · wszystkie postacie</h1>'
            '<p class="notice">Aktualne zasady v0.3: 7 bohaterów, 29 mocy, jeden koszt każdej mocy. '
            'Nowe walki gry korzystają z tego samego katalogu.</p><p>' + combined + ' · ' +
            aid_link + ' · ' + markers_link + '</p><p>' +
            link(ROOT / 'docs/ui/prototype.html', 'Otwórz klikalny mock UI') + ' · ' +
            link(ROOT / catalog['rules_spec'], 'Pełne zasady i założenia') + ' · ' +
            link(ROOT / 'docs/ui/assets/rune-relations-circle-v03.png', 'Okrąg relacji run · same symbole') + '</p>'
            '<p>Ostatnia runa wyznacza kontynuację; trzy ostatnie runy spełniają warunki kart. '
            'Niepasująca moc zeruje pamięć przed działaniem. Premie sprawdzamy przed dopisaniem nowej runy. '
            'Fala jest mostem wyłącznie Nimry. Pozostałe runy to silniejsze nagrody rozwoju postaci.</p>'
            '<table><thead><tr><th>Bohater</th><th>Runy mocy</th><th>Do druku</th></tr></thead><tbody>' +
            ''.join(rows) + '</tbody></table>' + ''.join(descriptions) +
            '<p>Druk A4, jednostronnie, 100%, bez dopasowania. Zdolności 60 × 54 mm; sprzęt 60 × 42 mm. '
            'Kości w opisach to kości fizyczne; nazwy cech oznaczają modyfikatory. Liczby są do ogrania.</p></main></body></html>\n')


def _reference_sheet(output: Path, name: str, html: str, *, html_only: bool) -> tuple[Path, list[Any]]:
    """Keep validation, previews and individual PDFs in the working directory."""
    path = output / f'{name}.html'
    path.write_text(html, encoding='utf-8')
    pdf = path.with_suffix('.pdf')
    if html_only:
        return pdf, []
    issues = mats.base.validate_html(path)
    if not issues:
        render_pdf(path, pdf)
        if pdf_pages(pdf) != 1:
            raise RuntimeError(f'{name}: arkusz powinien zajmować jedną stronę.')
        subprocess.run(['pdftoppm', '-singlefile', '-scale-to', '1300', '-png', str(pdf),
                        str(path.with_suffix(''))], capture_output=True, check=True, timeout=30)
    return pdf, issues


def _check_pdfs(outputs: tuple[tuple[Path, int], ...]) -> None:
    """Catch format or page-count errors before publishing the first file."""
    for path, expected in outputs:
        with path.open('rb') as handle:
            if handle.read(5) != b'%PDF-':
                raise RuntimeError(f'Nieprawidłowy PDF do publikacji: {path.name}.')
        if pdf_pages(path) != expected:
            raise RuntimeError(f'{path.name}: oczekiwano {expected} stron.')


def _reference_index(output: Path, sections: list[dict[str, Any]], *, html_only: bool,
                     publish_root: Path | None) -> str:
    def link(path: Path, label: str) -> str:
        return f'<a href="{escape(os.path.relpath(path, output), quote=True)}">{escape(label)}</a>'

    links = [link(output / f'{section["id"]}.html', section['name']) for section in sections]
    links.append(link(output / 'markers.html', 'Znaczniki · HTML'))
    if not html_only:
        public = (publish_root / 'reference') if publish_root else output
        links.extend([link(public / 'rules.pdf', 'Ściąga · PDF'), link(public / 'markers.pdf', 'Znaczniki · PDF')])
    return ('<!doctype html><html lang="pl"><meta charset="utf-8"><title>Relacje run · materiały wspólne</title>'
            '<body><h1>Ściąga graczy i znaczniki</h1><p>A4, jednostronnie, 100%, bez dopasowania.</p><ul>' +
            ''.join(f'<li>{link_html}</li>' for link_html in links) + '</ul></body></html>\n')


def build_aid(*, output: Path = REFERENCE_OUTPUT, html_only: bool = False,
              publish_root: Path | None = HANDOUTS_ROOT) -> Path:
    """Use the same help text and generated relation table as the game UI."""
    output = output.resolve()
    publish_root = publish_root.resolve() if publish_root is not None else None
    output.mkdir(parents=True, exist_ok=True)
    checks: dict[str, list[Any]] = {}
    parts: list[Path] = []
    sections: list[dict[str, Any]] = []
    for number, sheet in enumerate(load_rune_relation_player_aid(), 1):
        html = mats.player_aid_page(sheet)
        pdf, issues = _reference_sheet(output, sheet['id'], html, html_only=html_only)
        if not html_only:
            checks[sheet['id']] = issues
            parts.append(pdf)
        sections.append(dict(id=sheet['id'], name=sheet['title'], first_page=number, last_page=number))
    markers = mats.markers_page().replace('WYKORZYSTANE<br>DO MANA DRAIN', 'EFEKT KARTY').replace(
        'Tylko przy zdolności, której opis<br>określa takie ograniczenie.',
        'Termin i pozostałą pulę<br>sprawdź w informacjach postaci.')
    markers_pdf, marker_issues = _reference_sheet(output, 'markers', markers, html_only=html_only)
    rules_pdf = output / 'rules.pdf'
    if not html_only:
        checks['markers'] = marker_issues
        (output / 'validation.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if any(checks.values()):
            raise RuntimeError('Ściąga lub znaczniki: popraw wskazane przepełnienia.')
        merge_pdfs(parts, rules_pdf)
        if pdf_pages(rules_pdf) != len(sections):
            raise RuntimeError('Nieprawidłowa liczba stron ściągi po połączeniu.')
        compact_pdf(rules_pdf)
        compact_pdf(markers_pdf)
        _check_pdfs(((rules_pdf, len(sections)), (markers_pdf, 1)))
    manifest = dict(profile='rune_relations_v03', pdf=not html_only,
                    rules=dict(file='rules.pdf', pages=len(sections), sections=sections),
                    markers=dict(file='markers.pdf', pages=1, marker_mm=[60, 42]))
    (output / 'reference_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'index.html').write_text(_reference_index(output, sections, html_only=html_only,
                                                     publish_root=publish_root), encoding='utf-8')
    if not html_only and publish_root:
        publish_pdf(rules_pdf, publish_root / 'reference/rules.pdf', expected_pages=len(sections))
        publish_pdf(markers_pdf, publish_root / 'reference/markers.pdf', expected_pages=1)
        return publish_root / 'reference/rules.pdf'
    return rules_pdf


def build(*, output: Path = OUTPUT, html_only: bool = False,
          publish_root: Path | None = HANDOUTS_ROOT) -> dict[str, Any]:
    output = output.resolve()
    publish_root = publish_root.resolve() if publish_root is not None else None
    catalog = load_catalog()
    output.mkdir(parents=True, exist_ok=True)
    sections: list[dict[str, Any]] = []
    parts: list[Path] = []
    checks: dict[str, Any] = {}
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
            if pdf_pages(pdf) != PAGES_PER_HERO:
                raise RuntimeError(f'{hero_id}: oczekiwano {PAGES_PER_HERO} stron.')
            compact_pdf(pdf)
            parts.append(pdf)
        sections.append(dict(hero=hero_id, name=build_print_hero(hero_id).name, pages=PAGES_PER_HERO,
                             first_page=PAGES_PER_HERO * len(sections) + 1,
                             powers=len(catalog['heroes'][hero_id]['cards'])))
        print(f'{hero_id}: {PAGES_PER_HERO} stron' + (' HTML' if html_only else ', PDF i układ poprawne'), flush=True)
    manifest = dict(version=3, profile=catalog['profile'], stage=catalog['stage'],
                    resonance_model=catalog['rules']['resonance_model'], memory_limit=3,
                    pages=PAGES_PER_HERO * len(sections), sections=sections,
                    pdf=not html_only, layout_validated=not html_only, action_mm=[60, 54], equipment_mm=[60, 42],
                    panel=[dict(slot=i, name=name, board=[19, 29-i]) for i, (name, _) in enumerate(SYMBOLS)])
    if parts:
        merge_pdfs(parts, output / 'characters.pdf')
        if pdf_pages(output / 'characters.pdf') != manifest['pages']:
            raise RuntimeError('Komplet powinien mieć 35 stron.')
        compact_pdf(output / 'characters.pdf')
    reference_output = REFERENCE_OUTPUT if output.resolve() == OUTPUT.resolve() else output / 'reference'
    build_aid(output=reference_output, html_only=html_only, publish_root=None)
    if not html_only:
        # Validate every public file before replacing any published handout.
        reference_manifest = json.loads((reference_output / 'reference_manifest.json').read_text(encoding='utf-8'))
        expected = ((output / 'characters.pdf', manifest['pages']),
                    (reference_output / 'rules.pdf', reference_manifest['rules']['pages']),
                    (reference_output / 'markers.pdf', 1))
        _check_pdfs(expected)
    (output / 'characters_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (output / 'index.html').write_text(render_index(output, catalog, manifest,
        reference_output=reference_output, publish_root=publish_root), encoding='utf-8')
    if not html_only and publish_root:
        publish_pdf(output / 'characters.pdf', publish_root / 'characters.pdf', expected_pages=manifest['pages'])
        publish_pdf(reference_output / 'rules.pdf', publish_root / 'reference/rules.pdf', expected_pages=expected[1][1])
        publish_pdf(reference_output / 'markers.pdf', publish_root / 'reference/markers.pdf', expected_pages=1)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html-only', action='store_true')
    parser.add_argument('--aid-only', action='store_true')
    parser.add_argument('--output', type=Path, help='Katalog roboczy; domyślnie .cache/handouts/characters albo reference.')
    parser.add_argument('--publish-root', type=Path, default=HANDOUTS_ROOT,
                        help='Katalog publicznych PDF; domyślnie handouts/.')
    args = parser.parse_args()
    if args.aid_only:
        build_aid(output=args.output or REFERENCE_OUTPUT, html_only=args.html_only, publish_root=args.publish_root)
    else:
        build(output=args.output or OUTPUT, html_only=args.html_only, publish_root=args.publish_root)


if __name__ == '__main__':
    main()

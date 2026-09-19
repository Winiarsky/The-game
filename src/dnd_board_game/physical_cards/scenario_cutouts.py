"""Deterministic, grid-aligned cutout sheets derived from scenario terrain."""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any
import re
from xml.etree import ElementTree


@dataclass(frozen=True)
class Cutout:
    id: str
    name: str
    scene: str
    origin: tuple[int, int]
    size: tuple[int, int]
    kind: str
    interaction: tuple[int, int] | None = None
    environment_id: str | None = None
    artwork: str | None = None
    print_name: str | None = None
    board_rotation: int = 0

    @property
    def board_size(self) -> tuple[int, int]:
        """Quarter turns change the LED footprint, never the printed dimensions."""
        return self.size[::-1] if self.board_rotation % 180 else self.size

    @property
    def interaction_offset(self) -> tuple[int, int] | None:
        """Map the board interaction cell back onto the unrotated paper tile."""
        if self.interaction is None:
            return None
        x, y = (self.interaction[i] - self.origin[i] for i in (0, 1))
        w, h = self.size
        return {0: (x, y), 90: (y, h-1-x), 180: (w-1-x, h-1-y),
                270: (w-1-y, x)}[self.board_rotation % 360]

    @property
    def positions(self) -> tuple[tuple[int, int], ...]:
        x, y = self.origin
        w, h = self.board_size
        return tuple((c, r) for c in range(x, x+w) for r in range(y, y+h))

    @property
    def rule(self) -> str:
        return {'blocking_terrain': 'BLOKADA', 'cover': '+2 KP',
                'difficult_terrain': 'KOSZT RUCHU ×2', 'place': 'INTERAKCJA'}[self.kind]


def build_cutouts(spec: dict[str, Any], battle: dict[str, Any]) -> tuple[Cutout, ...]:
    environment = {e['id']: e for e in battle['environment']}
    result: list[Cutout] = []
    occupied: dict[str, set[tuple[int, int]]] = {}
    for item in spec['items']:
        rotation = item.get('board_rotation', 0)
        if rotation not in (0, 90, 180, 270, -90, -180, -270):
            raise ValueError('Obrót kafla musi być wielokrotnością 90 stopni.')
        ref = item.get('environment_id')
        if ref:
            e = environment[ref]
            positions = {tuple(p) for p in e['positions']}
            x, y = min(c for c, _ in positions), min(r for _, r in positions)
            size = (max(c for c, _ in positions)-x+1, max(r for _, r in positions)-y+1)
            if rotation % 180:
                size = size[::-1]
            name, kind = e['name'], e['type']
            if kind == 'cover' and (e.get('cover_bonus') != 2 or e.get('projectile_cover_bonus') != 2 or e.get('blocks_movement') is not False):
                raise ValueError('Osłona wydruku wymaga +2 KP na polu i na linii strzału.')
        else:
            x, y = item['origin']
            size = tuple(item['size'])
            board_size = size[::-1] if rotation % 180 else size
            positions = {(c, r) for c in range(x, x+board_size[0]) for r in range(y, y+board_size[1])}
            name, kind = item['name'], 'place'
        token = Cutout(item['id'], name, item['scene'], (x, y), size, kind,
                       tuple(item['interaction']) if item.get('interaction') else None, ref, item.get('artwork'), item.get('print_name'), rotation)
        if len(positions) != size[0]*size[1] or not positions:
            raise ValueError(f'{token.id}: kafel musi być pełnym prostokątem; rozdziel elementy.')
        if not all(0 <= c < 19 and 0 <= r < 30 for c, r in positions):
            raise ValueError(f'{token.id}: kafel wychodzi poza pole gry lub na panel.')
        if token.interaction and token.interaction not in positions:
            raise ValueError(f'{token.id}: interakcja poza kaflem.')
        used = occupied.setdefault(token.scene, set())
        if used & positions:
            raise ValueError(f'{token.id}: kafle nakładają się.')
        used.update(positions)
        if token.id in {t.id for t in result}:
            raise ValueError(f'{token.id}: powtórzone ID.')
        # Access the rule here to reject unsupported terrain before rendering.
        token.rule
        result.append(token)
    if {t.environment_id for t in result if t.environment_id} != set(environment):
        raise ValueError('Każdy element terenu walki musi mieć kafel do wydruku.')
    return tuple(result)


@dataclass(frozen=True)
class Placement:
    token: Cutout
    page: int
    x: float
    y: float
    width: float
    height: float


def arrange(tokens: tuple[Cutout, ...], cell_mm: float) -> tuple[Placement, ...]:
    """Shelf packing; never resize or split a building to fit the paper."""
    if cell_mm <= 0:
        raise ValueError('Rozmiar pola musi być dodatni.')
    result: list[Placement] = []
    page, x, y, row_height = 0, 10.0, 30.0, 0.0
    for t in sorted(tokens, key=lambda t: (-t.size[1], -t.size[0], t.id)):
        w, h = t.size[0]*cell_mm, t.size[1]*cell_mm
        if w > 190 or h > 249:
            raise ValueError(f'{t.id}: kafel nie mieści się na A4; wymaga dzielenia na części.')
        if x+w > 200:
            x, y, row_height = 10.0, y+row_height+5, 0.0
        if y+h > 279:
            page, x, y, row_height = page+1, 10.0, 30.0, 0.0
        result.append(Placement(t, page, x, y, w, h))
        x += w+5
        row_height = max(row_height, h)
    return tuple(result)


def text(x: float, y: float, value: str, size: float = 3.3, anchor: str = 'start') -> str:
    return f'<text x="{x:g}" y="{y:g}" font-size="{size:g}" text-anchor="{anchor}">{escape(value)}</text>'


def svg(body: str) -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" '
            'viewBox="0 0 210 297" font-family="DejaVu Sans,Arial,sans-serif">'+body+'</svg>')


def illustration(source: str, x: float, y: float, width: float, height: float, *, stretch: bool) -> str:
    """Embed local editable SVG as vectors, retaining its original view box."""
    root = ElementTree.fromstring(source)
    if root.tag != '{http://www.w3.org/2000/svg}svg':
        raise ValueError('Grafika kafla musi być dokumentem SVG.')
    viewbox = escape(root.attrib.get('viewBox', '0 0 100 100'), quote=True)
    aspect = 'none' if stretch else 'xMidYMid meet'
    opening = (f'<svg xmlns="http://www.w3.org/2000/svg" x="{x:g}" y="{y:g}" '
               f'width="{width:g}" height="{height:g}" viewBox="{viewbox}" '
               f'preserveAspectRatio="{aspect}" overflow="hidden" fill="white" stroke="black" '
               'stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round">')
    return re.sub(r'<svg\b[^>]*>', lambda _: opening, source, count=1)


def tile_svg(t: Cutout, cell_mm: float, artwork: str = '') -> str:
    """One frame spans the full footprint; a single mixed-weight caption follows."""
    w, h = (v*cell_mm for v in t.size)
    large = h > 55
    footer = 8 if large else 5.8
    frame_height = h-footer-1
    parts = [f'<rect x=".15" y=".15" width="{w-.3:g}" height="{h-.3:g}" fill="white" stroke="black" stroke-width=".3"/>']
    if artwork:
        if not artwork.lstrip().startswith('<'):
            parts.append(f'<image href="{escape(artwork, quote=True)}" x="1.5" y="1.5" width="{w-3:g}" height="{frame_height-1:g}" preserveAspectRatio="xMidYMid meet"/>')
        else:
            parts.append(illustration(artwork,1.5,1.5,w-3,frame_height-1,stretch=False))
    parts.append(f'<rect x="1" y="1" width="{w-2:g}" height="{frame_height:g}" fill="none" stroke="black" stroke-width=".35"/>')
    # Grid registration stays on the outer edge, leaving the illustration whole.
    for c in range(1,t.size[0]):
        parts.append(f'<path d="M{c*cell_mm:g} 0v.8M{c*cell_mm:g} {h-.8:g}v.8" stroke="black" stroke-width=".2"/>')
    for r in range(1,t.size[1]):
        parts.append(f'<path d="M0 {r*cell_mm:g}h.8M{w-.8:g} {r*cell_mm:g}h.8" stroke="black" stroke-width=".2"/>')
    name=t.print_name or t.name
    effect={'blocking_terrain':'blokada' if t.size[0]==1 else 'blokuje ruch',
            'cover':'+2 KP','difficult_terrain':'koszt ruchu ×2','place':'interakcja'}[t.kind]
    caption=f'{name} — {effect}'
    font=min(4.2 if large else 2.6,(w-3)/(len(caption)*.58))
    parts.append(f'<text data-caption="{t.id}" x="{w/2:g}" y="{h-(2.5 if large else 1.8):g}" font-size="{font:g}" text-anchor="middle"><tspan font-weight="bold">{escape(name)}</tspan><tspan> — {escape(effect)}</tspan></text>')
    # ID is an assembly aid; kept small inside a white tab at the frame corner.
    parts.append('<rect x="1.3" y="1.3" width="6.2" height="3" fill="white"/>')
    parts.append(text(1.8,3.6,t.id,1.9))
    if t.interaction:
        ix_cell, iy_cell = t.interaction_offset
        if large:
            cx=(ix_cell+.5)*cell_mm
            cy=(iy_cell+.5)*cell_mm
            parts.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="5" fill="white" stroke="black" stroke-width=".5"/>')
            parts.append(text(cx,cy+1.3,'I',3.8,'middle'))
        else:
            ix=(ix_cell+1)*cell_mm-4
            parts.append(f'<circle cx="{ix:g}" cy="4" r="2.5" fill="white" stroke="black" stroke-width=".35"/>')
            parts.append(text(ix,5,'I',2.6,'middle'))
    return ''.join(parts)


def layout_svg(tokens: tuple[Cutout, ...], scene: str, x: float, y: float) -> str:
    cell=4.4
    parts=[f'<g transform="translate({x:g} {y:g})">', text(0,-5,'GILDIA' if scene=='guild' else 'POSTERUNEK',4)]
    for c in range(20):
        for r in range(30):
            parts.append(f'<rect x="{c*cell:g}" y="{r*cell:g}" width="{cell:g}" height="{cell:g}" fill="{ "#ddd" if c==19 else "white"}" stroke="#ccc" stroke-width=".12"/>')
    for t in tokens:
        if t.scene != scene:
            continue
        tx,ty=t.origin[0]*cell,t.origin[1]*cell
        w,h=t.board_size[0]*cell,t.board_size[1]*cell
        parts.append(f'<rect x="{tx:g}" y="{ty:g}" width="{w:g}" height="{h:g}" fill="#eee" stroke="black" stroke-width=".35"/>')
        parts.append(text(tx+w/2,ty+h/2+.7,t.id,2.0,'middle'))
        if t.board_rotation % 360 == 270:
            parts.append(f'<path d="M{tx+w-.7:g} {ty+.5:g}v{h-1:g}" stroke="black" stroke-width=".8"/>')
        if t.interaction:
            cx,cy=(t.interaction[0]+.5)*cell,(t.interaction[1]+.5)*cell
            parts.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="1.7" fill="none" stroke="black" stroke-width=".3"/>')
    for c in range(0,20,2):parts.append(text((c+.5)*cell,-1,str(c),1.8,'middle'))
    for r in range(0,30,2):parts.append(text(-1,(r+.7)*cell,str(r),1.8,'end'))
    parts.append('</g>')
    return ''.join(parts)


def render_document(tokens: tuple[Cutout, ...], cell_mm: float, calibrated: bool, artworks: dict[str, str] | None = None) -> str:
    instruction = text(10,17,'MISJA 0 · ELEMENTY DO WYCIĘCIA',5)
    lines=[
        'Druk jednostronny A4 • skala 100% • bez dopasowania do strony.',
        'Warstwy: plansza → własne tło → wycięte kafle → figurki.',
        'Wytnij zewnętrzny obrys razem z podpisem. Nie tnij ramki obrazka.',
        'Budynki wytnij w całości. Nie rozdzielaj ich na pojedyncze pola.',
        'Blokada / blokuje ruch: w walce blokuje wejście i widoczność.',
        '+2 KP: można wejść; premia KP dla figurki stojącej na kaflu.',
        'Osłona na linii strzału: +2 KP celu przeciw atakom dystansowym.',
        'KOSZT RUCHU ×2: wejście na pole kosztuje 10 ft zamiast 5 ft.',
        'I / kółko: interakcja. W eksploracji blokady i premie są nieaktywne.',
        'P15 Rozmowa: połóż dopiero po walce; nie zastępuje figurki Boruta.',
        'P02 Wóz: droga (9,16)–(9,17), potem posterunek (9,24)–(9,25).',
        'Gildia i posterunek używają oddzielnych zestawów, bez nakładania.',
        ('Kalibracja areny 250/244; po wydruku 4 pola powinny mieć 100 mm.' if calibrated else 'Wersja nominalna: dokładnie 25 mm/pole w PDF; 4 pola = 100 mm.'),
    ]
    for i,line in enumerate(lines):instruction+=text(10,28+i*6,line,3.0)
    line_y=110
    instruction+=f'<path d="M10 {line_y}h{4*cell_mm:g}m0-2v4M10 {line_y-2}v4" stroke="black" stroke-width=".4"/>'
    instruction+=text(10,118,'Odcinek kontrolny: 100 mm na skalibrowanym wydruku.',2.9)
    instruction+=text(10,130,'SPIS KAFELKÓW · rozmiar w polach · narożnik (kol., wiersz)',3.3)
    for i,t in enumerate(tokens):
        instruction+=text(10,138+i*7,f'{t.id}  {t.name}  ·  {t.board_size[0]}×{t.board_size[1]}  ·  {t.origin}  ·  {t.rule}',3)
    pages=[svg(instruction)]
    guide=text(10,17,'ROZMIESZCZENIE · PODGLĄD, NIE WYCINAĆ',4.5)
    guide+=layout_svg(tokens,'guild',13,40)+layout_svg(tokens,'outpost',113,40)
    for i,line in enumerate([
        'Współrzędne od zera: kolumna 0–18, wiersz 0–29.',
        'Szary pas kolumny 19 to panel sterowania — zostaw go wolny.',
        'Dół dla graczy = strona run. Wszystkie podpisy skieruj ku runom.',
        'Budynki zajmują cały prostokąt. Kółko wskazuje pole interakcji.',
        'Gildia: drużyna (9,18), Nessa (5,7). Wyjście: G03 (9,24).',
        'Droga: tylko P02 Wóz i figurka drużyny; potem zmień tło.',
        'Walka: rozstaw P01–P14 według podświetlenia w aplikacji.',
        'Po walce zostaw kafle i dołóż P15; drużyna wraca na (9,20).',
        'Figurki wrogów i bohaterów ustawiaj według bieżącego setupu.',
        'Rysunki mebli są dekoracją. Zasady określają podpis i obrys kafla.',
        'Kreski na zewnętrznej krawędzi wyznaczają granice pól.',
        'Obróć wycinanki o 90° w lewo względem siatki powyżej.',
        'Gruba krawędź każdego obrysu wskazuje stronę podpisu kafla.',
    ]):guide+=text(10,189+i*7,line,3.1)
    pages.append(svg(guide))
    placements=arrange(tokens,cell_mm)
    for page in range(max(p.page for p in placements)+1):
        body=text(10,16,f'MISJA 0 · KAFLE {page+1}',4.5)
        body+=text(10,23,'Tnij zewnętrzny obrys razem z podpisem. Druk 100%.',3)
        for p in placements:
            if p.page==page:
                body+=f'<g data-cutout="{p.token.id}" transform="translate({p.x:g} {p.y:g})">'+tile_svg(p.token,cell_mm,(artworks or {}).get(p.token.id,''))+'</g>'
        body+=text(10,289,f'Arkusz {page+3} · '+('kalibracja areny 250/244' if calibrated else 'nominalne 25 mm'),2.8)
        pages.append(svg(body))
    return ('<!doctype html><html lang="pl"><meta charset="utf-8"><title>Misja 0 — kafle A4</title>'
            '<style>@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0}section{width:210mm;height:297mm;break-after:page;overflow:hidden}section:last-child{break-after:auto}svg{display:block}</style>'
            '<body>'+''.join('<section>'+p+'</section>' for p in pages)+'</body></html>')

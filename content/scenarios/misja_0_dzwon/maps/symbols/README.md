# Wektorowe rysunki kafli Misji 0

14 lokalnych SVG, współdzielonych przez 18 kafli. Przypisania `artwork`
są w `../cutouts.json`. Każdy rysunek ma układ współrzędnych 0–100.
Pliki można edytować jako tekst lub w edytorze SVG. Grafiki są osadzane
wektorowo w PDF, bez rasteryzacji i pobierania z sieci.

Budynki: office, arena, armory, quarters, store. Przedmioty i teren:
bell, cart, crate, sacks, wall, rubble, rock. Punkty: exit, talk.

Styl: czarna kreska, białe wypełnienie, rzut z góry, mało pełnej czerni.
Duże wnętrza wypełniają obszar między nagłówkiem a podpisem; małe symbole
zachowują proporcje. Siatka, podpis, obrys cięcia i kółko interakcji są
nakładane przez generator — nie umieszczaj ich w samej ilustracji.
Meble we wnętrzach są dekoracyjne, nie tworzą dodatkowych przeszkód.

Po zmianach uruchom z katalogu projektu:

```sh
PYTHONPATH=src:. .venv/bin/python scripts/build_mission_zero_cutouts.py
```

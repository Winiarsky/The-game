# Wóz — próbny kafel z ramką v3

Jedna próbka do oceny przed zmianą całego kompletu.

- Cały kafel: 2 × 1 pola, nominalnie 50 × 25 mm, razem z podpisem.
- Ramka ilustracji: 48 × 18,5 mm, rozciągnięta przez oba pola.
- Pod ramką jedna linia: **Wóz** — blokuje ruch.
- Granicę pól wskazują tylko małe kreski na zewnętrznej krawędzi.
- W walce obydwa pola blokują ruch i widoczność zgodnie z obecnymi zasadami.

Źródła w tym katalogu:

- `wagon_ink.png`: ilustracja z wbudowanego image_gen (raster, nie SVG).
- `PROMPT.md`: dokładny prompt i tryb generowania.

Generator zapisuje podgląd `cart_preview.png`, próbne PDF-y
`cart_sample_A4.pdf` / `cart_sample_A4_25mm.pdf` i ich HTML wyłącznie do
`.cache/handouts/cart_sample/` w głównym katalogu repozytorium.
Próbki służą do oceny układu ramki i podpisu.

Do gry użyj bieżącego kompletu
[kafli Misji 0](../../../../../../handouts/mission_0/tiles.pdf).
Ma on wspólną z planszą kalibrację `(250/244) × 1,03`.
Drukuj 100%, bez dopasowania. Obrys do wycięcia zawiera ilustrację i tekst.
Układ ramki i podpisu z tej próbki został zastosowany do całego zestawu kafli.

Generator z głównego folderu projektu:

```sh
PYTHONPATH=src:. .venv/bin/python scripts/build_cart_cutout_sample.py
```

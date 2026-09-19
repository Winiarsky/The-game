# Wóz — próbny kafel z ramką v3

Jedna próbka do oceny przed zmianą całego kompletu.

- Cały kafel: 2 × 1 pola, nominalnie 50 × 25 mm, razem z podpisem.
- Ramka ilustracji: 48 × 18,5 mm, rozciągnięta przez oba pola.
- Pod ramką jedna linia: **Wóz** — blokuje ruch.
- Granicę pól wskazują tylko małe kreski na zewnętrznej krawędzi.
- W walce obydwa pola blokują ruch i widoczność zgodnie z obecnymi zasadami.

Pliki:

- `wagon_ink.png`: ilustracja z wbudowanego image_gen (raster, nie SVG).
- `PROMPT.md`: dokładny prompt i tryb generowania.
- `cart_preview.png`: podgląd kompletnego kafla wyrenderowany w przeglądarce.
- `cart_sample_A4.pdf`: pojedynczy kafel na A4, korekta areny 250/244.
- `cart_sample_A4_25mm.pdf`: pojedynczy kafel na A4, nominalne pola 25 mm.
- `*.html`: skład ilustracji, ramki i tekstu; źródło eksportu PDF i podglądu.

Druk 100%, bez dopasowania. Obrys do wycięcia zawiera ilustrację i tekst.
Ten układ ramki i podpisu został zastosowany do całego zestawu kafli.

Generator z głównego folderu projektu:

```sh
PYTHONPATH=src:. .venv/bin/python scripts/build_cart_cutout_sample.py
```

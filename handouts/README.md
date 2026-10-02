# Materiały do druku — czarno-biała wersja testowa

W tym folderze są wyłącznie aktualne PDF-y. Druk A4: jednostronnie,
**100% / rzeczywisty rozmiar**, bez dopasowania do strony.

| Plik | Zawartość | Strony |
| --- | --- | --- |
| [characters.pdf](characters.pdf) | Siedem postaci v0.3, po trzy planszetki i dwa arkusze wycinanek | 35 |
| [map_a4.pdf](map_a4.pdf) | Plansza z panelem, podzielona na A1–D3 do złożenia | 12 |
| [map_full.pdf](map_full.pdf) | Ta sama plansza na jednej stronie dla drukarni | 1 |

`map_a4.pdf`: druk A4 poziomo. Tnij zewnętrzny obrys, zachowaj zakładki;
składaj wierszami A–D, od A1. `map_full.pdf`: jedna strona
około **791,5 × 527,7 mm**; drukarnia powinna wydrukować ją w rzeczywistym
rozmiarze, bez dopasowania do A1 lub innego formatu. Oba warianty i kafle
mają tę samą kalibrację `(250/244) × 1,03`, pole w PDF ma 26,383 mm.
Przed całym drukiem porównaj próbkę z fizycznymi czujnikami.

Karty: Garran 1–5, Brakka 6–10, Mira 11–15, Dagna 16–20,
Lorian 21–25, Nimra 26–30, Erynd 31–35. Wytnij zdolności i cel ze strony 4
oraz sprzęt ze strony 5 każdego zestawu. Zdolności i cele: 60 × 54 mm;
sprzęt i znaczniki: 60 × 42 mm.

## Misja 0

| Plik | Zawartość | Strony |
| --- | --- | --- |
| [mission_0/tiles.pdf](mission_0/tiles.pdf) | Rozmieszczenie i 18 kafli gildii oraz posterunku do wycięcia | 7 |
| [mission_0/items.pdf](mission_0/items.pdf) | Przedmioty misji, w tym obie wersje pierścienia | 1 |
| [mission_0/order.pdf](mission_0/order.pdf) | Rozkaz Nessy | 1 |
| [mission_0/receipts.pdf](mission_0/receipts.pdf) | Pokwitowania Boruta | 1 |

Rozdawaj handouty w momencie wskazanym przez przygodę.
Zidentyfikowana karta pierścienia zastępuje jego niepoznaną kartę dopiero
po identyfikacji. Kafle są nakładane na wspólną planszę z `map_a4.pdf`
lub `map_full.pdf` zgodnie z instrukcją rozmieszczenia.

## Materiały wspólne

[reference/rules.pdf](reference/rules.pdf): ściąga graczy, 3 strony.
[reference/markers.pdf](reference/markers.pdf): znaczniki zajętej ręki i efektu karty, 1 strona.

## Odbudowa

Z katalogu projektu:

```bash
PYTHONPATH=src .venv/bin/python scripts/build_handouts.py
```

Można odbudować jedną część przez `--only characters`, `--only maps`,
`--only mission_0` lub `--only reference`. Robocze HTML, indywidualne PDF,
podglądy i metadane powstają w `.cache/handouts/`; nie są dodatkowymi
materiałami do druku. Źródła pozostają w `content/` i `scripts/`.
Starsze zestawy kart i alternatywne wydruki usunięto.

# Misja 0 — konfrontacje jednej kolejki

Model `mission_progress_v1.1`, silnik `progress_v1`. Wszystkie 98 składów 3–6 spośród siedmiu bohaterów.
30 ziaren na skład: 100000 × liczba osób + 1000 × indeks składu + 0…29.
Składy w kolejności combinations(HEROES, N); kości sparowane między wariantami i strategiami.
Wspólny z grą konstruktor i reguły, ST 14; wskazówka: ST 12 w kwaterze. Bez komplementu Nessy.
`best_no_spend_v1`: legalne podejście z najwyższą różnicą modyfikator − ST;
`random_no_spend_v1`: losowe legalne podejście; `best_minimum_reputation_v1`: najlepsze podejście,
po porażce najtańsza wystarczająca premia lub dodatkowa kość. Każda scena zaczyna z 20 reputacji.
To nie model całej ekonomii wyprawy ani zachowania ludzi. Pas bez podejść kończy kolej bohatera.
Kolejność bohaterów to HEROES; raport nie sprawdza jej permutacji ani optymalizacji przydziału podejść.
Sukces oznacza wynik `success`; częściowy wynik jest osobno. Rozkład podaje liczności poziomów.

| Osób | Scena | Wariant | Strategia | Prób | Sukces | Częściowy | Testy min–max | Śr. koszt reputacji | Rozkład poziomów |
|---:|---|---|---|---:|---:|---:|---|---:|---|
| 3 | nessa | bez wskazówki | best_no_spend_v1 | 1050 | 48.6% | 31.8% | 2–3 | 0.00 | complication: 334, full: 175, success: 335, unchanged: 170, worsened: 36 |
| 3 | nessa | bez wskazówki | random_no_spend_v1 | 1050 | 36.9% | 34.6% | 2–3 | 0.00 | complication: 363, full: 125, success: 262, unchanged: 247, worsened: 53 |
| 3 | nessa | bez wskazówki | best_minimum_reputation_v1 | 1050 | 94.2% | 5.3% | 2–3 | 5.64 | complication: 56, full: 716, success: 273, unchanged: 5 |
| 3 | cart | bez wskazówki | best_no_spend_v1 | 1050 | 52.4% | 29.6% | 2–3 | 0.00 | complication: 311, full: 207, success: 343, unchanged: 156, worsened: 33 |
| 3 | cart | bez wskazówki | random_no_spend_v1 | 1050 | 38.4% | 34.0% | 2–3 | 0.00 | complication: 357, full: 118, success: 285, unchanged: 235, worsened: 55 |
| 3 | cart | bez wskazówki | best_minimum_reputation_v1 | 1050 | 52.4% | 29.6% | 2–3 | 0.00 | complication: 311, full: 207, success: 343, unchanged: 156, worsened: 33 |
| 3 | armory | bez wskazówki | best_no_spend_v1 | 1050 | 53.4% | 29.7% | 2–3 | 0.00 | complication: 312, full: 214, success: 347, unchanged: 145, worsened: 32 |
| 3 | armory | bez wskazówki | random_no_spend_v1 | 1050 | 37.0% | 33.0% | 2–3 | 0.00 | complication: 347, full: 118, success: 271, unchanged: 256, worsened: 58 |
| 3 | armory | bez wskazówki | best_minimum_reputation_v1 | 1050 | 53.4% | 29.7% | 2–3 | 0.00 | complication: 312, full: 214, success: 347, unchanged: 145, worsened: 32 |
| 3 | quarters | bez wskazówki | best_no_spend_v1 | 1050 | 52.9% | 30.1% | 2–3 | 0.00 | complication: 316, full: 206, success: 349, unchanged: 147, worsened: 32 |
| 3 | quarters | wskazówka | best_no_spend_v1 | 1050 | 63.4% | 25.2% | 2–3 | 0.00 | complication: 265, full: 309, success: 357, unchanged: 98, worsened: 21 |
| 3 | quarters | bez wskazówki | random_no_spend_v1 | 1050 | 38.7% | 34.7% | 2–3 | 0.00 | complication: 364, full: 136, success: 270, unchanged: 230, worsened: 50 |
| 3 | quarters | wskazówka | random_no_spend_v1 | 1050 | 50.9% | 31.3% | 2–3 | 0.00 | complication: 329, full: 198, success: 336, unchanged: 153, worsened: 34 |
| 3 | quarters | bez wskazówki | best_minimum_reputation_v1 | 1050 | 52.9% | 30.1% | 2–3 | 0.00 | complication: 316, full: 206, success: 349, unchanged: 147, worsened: 32 |
| 3 | quarters | wskazówka | best_minimum_reputation_v1 | 1050 | 63.4% | 25.2% | 2–3 | 0.00 | complication: 265, full: 309, success: 357, unchanged: 98, worsened: 21 |
| 4 | nessa | bez wskazówki | best_no_spend_v1 | 1050 | 66.2% | 21.7% | 2–4 | 0.00 | bonus: 245, complication: 228, full: 130, success: 320, unchanged: 88, worsened: 39 |
| 4 | nessa | bez wskazówki | random_no_spend_v1 | 1050 | 52.7% | 29.5% | 2–4 | 0.00 | bonus: 170, complication: 310, full: 77, success: 306, unchanged: 135, worsened: 52 |
| 4 | nessa | bez wskazówki | best_minimum_reputation_v1 | 1050 | 98.8% | 1.2% | 2–4 | 7.31 | bonus: 308, complication: 13, full: 668, success: 61 |
| 4 | cart | bez wskazówki | best_no_spend_v1 | 1050 | 68.1% | 21.4% | 2–4 | 0.00 | bonus: 246, complication: 225, full: 151, success: 318, unchanged: 74, worsened: 36 |
| 4 | cart | bez wskazówki | random_no_spend_v1 | 1050 | 55.0% | 26.6% | 2–4 | 0.00 | bonus: 180, complication: 279, full: 80, success: 318, unchanged: 142, worsened: 51 |
| 4 | cart | bez wskazówki | best_minimum_reputation_v1 | 1050 | 68.1% | 21.4% | 2–4 | 0.00 | bonus: 246, complication: 225, full: 151, success: 318, unchanged: 74, worsened: 36 |
| 4 | armory | bez wskazówki | best_no_spend_v1 | 1050 | 70.2% | 20.0% | 2–4 | 0.00 | bonus: 265, complication: 210, full: 163, success: 309, unchanged: 70, worsened: 33 |
| 4 | armory | bez wskazówki | random_no_spend_v1 | 1050 | 54.3% | 28.5% | 2–4 | 0.00 | bonus: 182, complication: 299, full: 83, success: 305, unchanged: 127, worsened: 54 |
| 4 | armory | bez wskazówki | best_minimum_reputation_v1 | 1050 | 70.2% | 20.0% | 2–4 | 0.00 | bonus: 265, complication: 210, full: 163, success: 309, unchanged: 70, worsened: 33 |
| 4 | quarters | bez wskazówki | best_no_spend_v1 | 1050 | 69.0% | 20.5% | 2–4 | 0.00 | bonus: 259, complication: 215, full: 150, success: 316, unchanged: 75, worsened: 35 |
| 4 | quarters | wskazówka | best_no_spend_v1 | 1050 | 81.0% | 13.3% | 2–4 | 0.00 | bonus: 320, complication: 140, full: 244, success: 286, unchanged: 45, worsened: 15 |
| 4 | quarters | bez wskazówki | random_no_spend_v1 | 1050 | 55.6% | 26.0% | 2–4 | 0.00 | bonus: 190, complication: 273, full: 85, success: 309, unchanged: 141, worsened: 52 |
| 4 | quarters | wskazówka | random_no_spend_v1 | 1050 | 68.7% | 20.2% | 2–4 | 0.00 | bonus: 257, complication: 212, full: 143, success: 321, unchanged: 80, worsened: 37 |
| 4 | quarters | bez wskazówki | best_minimum_reputation_v1 | 1050 | 69.0% | 20.5% | 2–4 | 0.00 | bonus: 259, complication: 215, full: 150, success: 316, unchanged: 75, worsened: 35 |
| 4 | quarters | wskazówka | best_minimum_reputation_v1 | 1050 | 81.0% | 13.3% | 2–4 | 0.00 | bonus: 320, complication: 140, full: 244, success: 286, unchanged: 45, worsened: 15 |
| 5 | nessa | bez wskazówki | best_no_spend_v1 | 630 | 48.6% | 41.6% | 2–5 | 0.00 | bonus: 96, complication: 262, full: 58, success: 152, unchanged: 43, worsened: 19 |
| 5 | nessa | bez wskazówki | random_no_spend_v1 | 630 | 36.3% | 47.0% | 2–5 | 0.00 | bonus: 57, complication: 296, full: 37, success: 135, unchanged: 76, worsened: 29 |
| 5 | nessa | bez wskazówki | best_minimum_reputation_v1 | 630 | 96.5% | 3.5% | 3–5 | 9.26 | bonus: 187, complication: 22, full: 358, success: 63 |
| 5 | cart | bez wskazówki | best_no_spend_v1 | 630 | 51.3% | 40.6% | 2–5 | 0.00 | bonus: 98, complication: 256, full: 59, success: 166, unchanged: 35, worsened: 16 |
| 5 | cart | bez wskazówki | random_no_spend_v1 | 630 | 36.3% | 48.3% | 2–5 | 0.00 | bonus: 66, complication: 304, full: 31, success: 132, unchanged: 70, worsened: 27 |
| 5 | cart | bez wskazówki | best_minimum_reputation_v1 | 630 | 51.3% | 40.6% | 2–5 | 0.00 | bonus: 98, complication: 256, full: 59, success: 166, unchanged: 35, worsened: 16 |
| 5 | armory | bez wskazówki | best_no_spend_v1 | 630 | 56.7% | 36.3% | 2–5 | 0.00 | bonus: 99, complication: 229, full: 72, success: 186, unchanged: 28, worsened: 16 |
| 5 | armory | bez wskazówki | random_no_spend_v1 | 630 | 36.2% | 48.7% | 2–5 | 0.00 | bonus: 68, complication: 307, full: 31, success: 129, unchanged: 67, worsened: 28 |
| 5 | armory | bez wskazówki | best_minimum_reputation_v1 | 630 | 56.7% | 36.3% | 2–5 | 0.00 | bonus: 99, complication: 229, full: 72, success: 186, unchanged: 28, worsened: 16 |
| 5 | quarters | bez wskazówki | best_no_spend_v1 | 630 | 54.9% | 37.0% | 2–5 | 0.00 | bonus: 97, complication: 233, full: 66, success: 183, unchanged: 34, worsened: 17 |
| 5 | quarters | wskazówka | best_no_spend_v1 | 630 | 68.7% | 27.0% | 2–5 | 0.00 | bonus: 151, complication: 170, full: 105, success: 177, unchanged: 16, worsened: 11 |
| 5 | quarters | bez wskazówki | random_no_spend_v1 | 630 | 38.4% | 48.3% | 2–5 | 0.00 | bonus: 63, complication: 304, full: 40, success: 139, unchanged: 52, worsened: 32 |
| 5 | quarters | wskazówka | random_no_spend_v1 | 630 | 53.5% | 37.9% | 2–5 | 0.00 | bonus: 98, complication: 239, full: 66, success: 173, unchanged: 39, worsened: 15 |
| 5 | quarters | bez wskazówki | best_minimum_reputation_v1 | 630 | 54.9% | 37.0% | 2–5 | 0.00 | bonus: 97, complication: 233, full: 66, success: 183, unchanged: 34, worsened: 17 |
| 5 | quarters | wskazówka | best_minimum_reputation_v1 | 630 | 68.7% | 27.0% | 2–5 | 0.00 | bonus: 151, complication: 170, full: 105, success: 177, unchanged: 16, worsened: 11 |
| 6 | nessa | bez wskazówki | best_no_spend_v1 | 210 | 52.9% | 35.2% | 2–6 | 0.00 | bonus: 22, complication: 74, full: 8, success: 81, unchanged: 19, worsened: 6 |
| 6 | nessa | bez wskazówki | random_no_spend_v1 | 210 | 42.4% | 39.5% | 2–6 | 0.00 | bonus: 9, complication: 83, full: 3, success: 77, unchanged: 27, worsened: 11 |
| 6 | nessa | bez wskazówki | best_minimum_reputation_v1 | 210 | 97.6% | 1.9% | 4–6 | 11.74 | bonus: 69, complication: 4, full: 99, success: 37, unchanged: 1 |
| 6 | cart | bez wskazówki | best_no_spend_v1 | 210 | 51.9% | 37.1% | 2–6 | 0.00 | bonus: 15, complication: 78, full: 10, success: 84, unchanged: 18, worsened: 5 |
| 6 | cart | bez wskazówki | random_no_spend_v1 | 210 | 38.6% | 43.8% | 2–6 | 0.00 | bonus: 7, complication: 92, full: 5, success: 69, unchanged: 26, worsened: 11 |
| 6 | cart | bez wskazówki | best_minimum_reputation_v1 | 210 | 51.9% | 37.1% | 2–6 | 0.00 | bonus: 15, complication: 78, full: 10, success: 84, unchanged: 18, worsened: 5 |
| 6 | armory | bez wskazówki | best_no_spend_v1 | 210 | 58.1% | 33.8% | 2–6 | 0.00 | bonus: 19, complication: 71, full: 13, success: 90, unchanged: 13, worsened: 4 |
| 6 | armory | bez wskazówki | random_no_spend_v1 | 210 | 37.1% | 47.6% | 2–6 | 0.00 | bonus: 15, complication: 100, full: 3, success: 60, unchanged: 24, worsened: 8 |
| 6 | armory | bez wskazówki | best_minimum_reputation_v1 | 210 | 58.1% | 33.8% | 2–6 | 0.00 | bonus: 19, complication: 71, full: 13, success: 90, unchanged: 13, worsened: 4 |
| 6 | quarters | bez wskazówki | best_no_spend_v1 | 210 | 55.7% | 35.2% | 2–6 | 0.00 | bonus: 20, complication: 74, full: 11, success: 86, unchanged: 14, worsened: 5 |
| 6 | quarters | wskazówka | best_no_spend_v1 | 210 | 72.4% | 20.0% | 2–6 | 0.00 | bonus: 35, complication: 42, full: 21, success: 96, unchanged: 13, worsened: 3 |
| 6 | quarters | bez wskazówki | random_no_spend_v1 | 210 | 43.8% | 41.4% | 2–6 | 0.00 | bonus: 11, complication: 87, full: 6, success: 75, unchanged: 24, worsened: 7 |
| 6 | quarters | wskazówka | random_no_spend_v1 | 210 | 55.7% | 35.2% | 2–6 | 0.00 | bonus: 21, complication: 74, full: 10, success: 86, unchanged: 14, worsened: 5 |
| 6 | quarters | bez wskazówki | best_minimum_reputation_v1 | 210 | 55.7% | 35.2% | 2–6 | 0.00 | bonus: 20, complication: 74, full: 11, success: 86, unchanged: 14, worsened: 5 |
| 6 | quarters | wskazówka | best_minimum_reputation_v1 | 210 | 72.4% | 20.0% | 2–6 | 0.00 | bonus: 35, complication: 42, full: 21, success: 96, unchanged: 13, worsened: 3 |

## Kontrola konfiguracji walki

| Bohaterowie | Wrogowie | Suma PW wrogów |
|---:|---:|---:|
| 3 | 5 | 104 |
| 4 | 6 | 134 |
| 5 | 7 | 160 |
| 6 | 8 | 196 |

Kontrole granic, kosztów i zakończenia przeszły w 44100 przebiegach. Wskazówka nie pogorszyła sukcesu w 8820 parach.
To kontrola mechaniki, nie ocena atrakcyjności ani czasu gry. Brak symulacji ruchu, Rezonansu,
ataków, leczenia i negocjowania rozejmu. Naprawa uszkodzenia po rozejmie nie zmienia szansy znalezienia przedmiotu.
Wskazówka po rozejmie jest darmowa, poza nim kosztuje 1 sz (złoto nie w kolumnie reputacji).
Raport zastępuje wcześniejszą symulację talii, która nie odpowiadała aktualnej Misji 0.

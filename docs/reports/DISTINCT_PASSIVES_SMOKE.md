# Unikalne pasywy — próba kontrolna silnika, 20.09.2026

336 symulacji po zmianie pasywów, wyłącznie jako kontrola zakończenia rozgrywki i zachowania zasobów. Strategie nie planują sekwencji nowych pasywów; wyniki nie oceniają ich pełnej siły.

Po 3 próby na każdy z 7 rotowanych składów w każdym wierszu; stałe ziarna. Silnik produkcyjny, pełna talia i fizyczna oferta.

Obie strategie dobierają do sześciu kart i wykorzystują premię +1 za fizyczną kartę. Preferują przyrost pasywów: test, efekt, odzysk, wsparcie, ochrona; jedna dodatkowo wspiera przy niskiej szansie. To proste punkty odniesienia, bez pełnej optymalizacji kolorów i kosztów. Atut nie podwaja testów eksploracji. Nie jest to model zachowania ludzi ani pomiar czasu przy stole.

| Osób | Scena | Strategia | Sukces | Mediana rund | Średnia rund | Testów |
|---|---|---|---|---|---|---|
| 3 | nessa_raise | Zawsze test | 38.1% | 4 | 3.71 | 10.2 |
| 3 | nessa_raise | Pomoc przy szansie <35% | 33.3% | 4 | 3.95 | 7.1 |
| 3 | sealed_cache | Zawsze test | 81.0% | 3 | 3.19 | 8.9 |
| 3 | sealed_cache | Pomoc przy szansie <35% | 66.7% | 4 | 3.57 | 8.3 |
| 4 | nessa_raise | Zawsze test | 42.9% | 4 | 3.62 | 12.8 |
| 4 | nessa_raise | Pomoc przy szansie <35% | 19.0% | 4 | 3.95 | 9.0 |
| 4 | sealed_cache | Zawsze test | 85.7% | 3 | 3.38 | 12.0 |
| 4 | sealed_cache | Pomoc przy szansie <35% | 61.9% | 4 | 3.67 | 10.9 |
| 5 | nessa_raise | Zawsze test | 19.0% | 4 | 3.86 | 17.4 |
| 5 | nessa_raise | Pomoc przy szansie <35% | 23.8% | 4 | 3.95 | 11.4 |
| 5 | sealed_cache | Zawsze test | 81.0% | 3 | 3.33 | 15.3 |
| 5 | sealed_cache | Pomoc przy szansie <35% | 57.1% | 4 | 3.67 | 13.5 |
| 6 | nessa_raise | Zawsze test | 33.3% | 4 | 3.90 | 21.0 |
| 6 | nessa_raise | Pomoc przy szansie <35% | 9.5% | 4 | 3.95 | 12.6 |
| 6 | sealed_cache | Zawsze test | 71.4% | 4 | 3.52 | 18.8 |
| 6 | sealed_cache | Pomoc przy szansie <35% | 61.9% | 4 | 3.76 | 16.5 |

Podatność celowo wpływa na ST i kość wpływu. Solo nie ma wsparcia. Wyniki wymagają ręcznego ogrania: szczególnie udział odpornych metod, czytelność rozliczania kart i czas dwóch rzutów.

# Plansza i karty — aktualne materiały do druku

Bieżący czarno-biały komplet znajduje się w głównym katalogu
[handouts](../handouts/README.md). Dawny zbiorczy pakiet areny został usunięty.

| Plik | Zawartość | Strony |
| --- | --- | --- |
| [characters.pdf](../handouts/characters.pdf) | Karty siedmiu bohaterów, maty i wycinanki | 35 |
| [map_a4.pdf](../handouts/map_a4.pdf) | Plansza z panelem, dwanaście arkuszy A4 do złożenia | 12 |
| [map_full.pdf](../handouts/map_full.pdf) | Ta sama plansza na jednej stronie dla drukarni, bez zakładek i numerów kafli | 1 |

Drukuj **100% / rzeczywisty rozmiar, bez dopasowania**. Wybierz jedną z dwóch
wersji planszy. Mapa i kafle mają wspólną kalibrację **`(250/244) × 1,03`**,
już uwzględnioną w PDF-ach; nie dodawaj jej ponownie w sterowniku.
Porównaj próbny wydruk z fizyczną planszą przed drukowaniem całego zestawu.
Figurki i teren ustawiaj według setupu w aplikacji.

Odbudowa z głównego katalogu repozytorium:

```sh
PYTHONPATH=src .venv/bin/python scripts/build_handouts.py
```

Opcje `--only maps` i `--only characters` odświeżają wybraną część.
Pośrednie HTML, PDF i manifesty trafiają do `.cache/handouts/`.
Pozostałe materiały oraz instrukcję przygotowania opisuje
[handouts/README.md](../handouts/README.md).

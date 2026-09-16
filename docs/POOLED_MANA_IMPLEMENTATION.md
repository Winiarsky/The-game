# Osobiste pule many 1.0 — wdrożenie i punkt odniesienia

Aktualizacja: obowiązuje [trwałe ładowanie many 2.0](MANA_CHARGE_V02.md), 148 lekcji. Poniższy opis wcześniejszego obiegu i jego wyniki są historyczne.

2026-09-14. Profil `pooled_mana_v01`, katalog w wersji 1.
Nowe gry siedmioma gotowymi bohaterami i nowe lekcje używają tego profilu.
Stare zapisane walki z rynkiem zachowują dotychczasowy stan; rozpocznij nowy kurs,
aby sprawdzać nowe zasady. Ogólny silnik D&D 5e i eksploracyjne dobieranie do 21
pozostają osobnymi systemami.

## Reguły do sprawdzenia przy stole

1. Każda walka zaczyna się z pustymi pulami i pełną przetasowaną talią.
   Liczba kart każdego koloru: `max(5, liczba bohaterów + 1)`.
   Daje to 25 kart dla 1–4 bohaterów, 30 dla 5, 35 dla 6 i 40 dla 7.
   Interfejs konfiguracji drużyny nadal obsługuje maksymalnie 5 bohaterów;
   6–7 to również test skrajnego obciążenia silnika.
2. Przed własną turą uzupełnij ofertę do dwóch kart. Zgłoś nowo odkryte kolory
   runami. Obowiązkowo wybierz jedną kartę runą Klucz/Gwiazda. Druga zostaje.
   Jeśli dostępna jest tylko jedna, bierzesz ją; brak jakiejkolwiek wywołuje drain.
3. Wartości kolorów zależą od bohatera. Pule są jawne i zostają między turami.
   21 nie jest limitem i przekroczenie nie daje kary.
4. Płatna zdolność wymaga punktów i ewentualnie kolorów. Całą pulę odłóż
   **na spód, w kolejności dobrania, bez tasowania**. Kolor może jednocześnie
   spełniać wymaganie i zasilać podbicie. Wybrane podbicia dzielą dostępne karty
   danego koloru i przestrzegają limitu zdolności.
5. Zwykły ruch i atak są bez many. Na start także reakcje, modyfikatory i bazowe
   akcje dodatkowe są bez many; część mocniejszych akcji dodatkowych wymaga puli.
   Każda karta podaje swój konkretny próg albo „bez many”. Koszt akcji,
   limity tury, koncentracja i wymagania celu nadal obowiązują.
6. Wróg może spalić kartę oferty albo karty z wierzchu lub je uwięzić.
   Kolory spalane z wierzchu zgłasza się pojedynczo. Pokonanie więżącego wroga
   otwiera potwierdzenie oddania jego kart na spód, w kolejności uwięzienia.
7. Niewykonalne pełne spalenie/uwięzienie wywołuje jeden drain.
   Zbierz **wszystko**: talię, ofertę, osobiste pule, spalone i uwięzione karty.
   Przetasuj komplet i odbuduj ofertę. Nie ponawiaj tego samego wrogiego efektu.
   Drain nie przywraca akcji, reakcji ani pasywów i nie daje dodatkowego doboru.
8. Dotychczasowe efekty O trwają do końca walki, z zachowaniem koncentracji
   i opisanych warunków wcześniejszego zakończenia. Efekty T zachowują swój czas.
   Przywołania i pomocnicy nie otrzymują własnej puli ani dodatkowego doboru.
   Obowiązkowy dobór jest związany z faktycznym rozpoczęciem tury bohatera;
   silnik nie generuje tur poza walką do gromadzenia zasobu.

## Początkowe liczby

To zestaw do ogrania, nie deklaracja zakończonego balansu walki.

| Bohater | Czerwona | Biała | Zielona | Czarna | Niebieska |
|---|---:|---:|---:|---:|---:|
| Garran | 4 | 7 | 1 | 3 | 4 |
| Brakka | 7 | 1 | 3 | 4 | 4 |
| Mira | 3 | 1 | 7 | 4 | 4 |
| Dagna | 1 | 7 | 4 | 3 | 4 |
| Lorian | 1 | 4 | 4 | 3 | 7 |
| Nimra | 4 | 1 | 3 | 4 | 7 |
| Erynd | 4 | 1 | 7 | 3 | 4 |

Początkowe progi: 6 dla małych płatnych zdolności, 12 dla wzmocnionych,
21 plus wymagane kolory dla ultów. Istniejące kości obrażeń, PW, KP, cechy,
pozycjonowanie i rodzaje podbić zostały zachowane. Nie zmieniamy cech tylko
po to, żeby skorygować tempo many, ponieważ wpływają także na eksplorację.

| Bohater | Pasyw many | Skaza |
|---|---|---|
| Garran | +2 pkt do ochrony/wsparcia przy przytomnym sąsiadującym sojuszniku | Zachowane ograniczenie ruchu przy rozpoczęciu tury obok przeciwnika |
| Brakka | +2 pkt do ofensywy w Szale; zachowane tymczasowe PW ze zwykłego trafienia | Tura bez ofensywy kończy Szał |
| Mira | +2 pkt w ukryciu | W ukryciu utrudnienie obron i testów reakcji |
| Dagna | +2 pkt do leczenia innej postaci | Ofensywa przy sojuszniku poniżej połowy PW: próg +2 |
| Lorian | +2 pkt z przytomną publicznością w 10 ft | Bez publiczności: próg +2; solowa lekcja nie nakłada tej dopłaty |
| Nimra | +2 pkt z trzema różnymi kolorami | Kolejne użycie tej samej płatnej zdolności: próg +2 za poprzednie użycie w serii |
| Erynd | +2 pkt bez sąsiadującego przeciwnika | Strzał przy celu sąsiadującym z sojusznikiem: próg +2 |

Są to modyfikatory progu; fizyczne kolory pozostają niezmienione.
Lorian: Strojenie podgląda i porządkuje do dwóch wierzchnich kart; Odzysk
przenosi spalone na spód; Wielkie strojenie odzyskuje do trzech spalonych
na wierzch. Wydany koszt nie jest spalony. Późniejsze wydatki graczy nie
niszczą ustawionego wierzchu przez tasowanie.

Wrogowie: Głodny Cień spala ofertę, przywódca dwie karty z wierzchu,
Kamienny Strażnik więzi ofertę. Efekt występuje przy pierwszym trafieniu
wroga co drugą rundę, po reakcjach obronnych; najwyżej raz w jego turze.
Kukła finałowa uczy spalania wierzchu na tej samej ścieżce rozstrzygnięcia.

## Ewaluator

Skrypt: `scripts/evaluate_combat_mana.py`.
Raporty: [bazowy HTML](reports/pooled_mana_v01/baseline/report.html),
[niezależne seedy](reports/pooled_mana_v01/validation/report.html).
Obok znajdują się CSV, szczegółowe JSON i kopia badanego katalogu.

```bash
python scripts/evaluate_combat_mana.py --samples 28 --rounds 8 \
  --seed 20260914 --output /tmp/mana-baseline
python scripts/evaluate_combat_mana.py --samples 28 --rounds 8 \
  --seed 20260915 --output /tmp/mana-validation
python scripts/evaluate_combat_mana.py --catalog /tmp/kandydat.json \
  --samples 28 --rounds 8 --seed 20260914 --output /tmp/mana-kandydat
```

Każdy zapisany przebieg obejmuje 4480 prób: 160 wariantów × 28 seedowanych
rotacji składów. Polityki: zwykły atak, szybkie wydawanie, czekanie na ulta,
adaptacja do punktów/liczby kart, pozostawianie koloru następnemu bohaterowi.
Strategie nie podglądają zakrytej kolejności talii. Symulator i aplikacja
korzystają z tych samych funkcji doboru, wydawania, spalania i drainu.

JSON raportuje m.in. dostępność ulta, medianę pierwszego osiągnięcia,
odsetek nieosiągnięcia, drainy, karty i punkty stracone, przetrzymywane karty,
nadpłatę, udział zwykłych ataków oraz pokrycie bohaterów i użycia zdolności.
Zapisywane są seed, liczba prób/rund, hash katalogu, commit i stan worktree.
Skrypt nie nadpisuje produkcyjnego katalogu ani nie wybiera automatycznie zwycięzcy.

Przykład: oszczędzanie na ulta przy spalaniu dwóch kart na koniec każdej
rundy, osiem rund. To celowa próba obciążeniowa, silniejsza od pojedynczego
produkcyjnego wroga; obejmuje także brak używania odzysku przez barda.

| Graczy | Kart | Drainy/próbę: baza / nowe seedy | Bez ulta: baza / nowe seedy |
|---:|---:|---|---|
| 3 | 20 | 1,00 / 1,07 | 36% / 42% |
| 3 | 25 | 0,64 / 0,43 | 25% / 13% |
| 5 | 25 | 1,07 / 1,21 | 42% / 48% |
| 5 | 30 | 0,79 / 0,71 | 29% / 25% |
| 7 | 25 | 2,00 / 2,00 | 94% / 93% |
| 7 | 40 | 0,61 / 0,39 | 30% / 21% |

**Granica raportu:** jest to ekonomia kart, bez symulacji obrażeń, leczenia,
mapy, zwycięstwa, sytuacyjnych pasywów/skaz i aktywnych efektów zdolności barda.
Nie ocenia wartości umiejętności wyłącznie na podstawie częstotliwości użycia.
Polityki są heurystykami, składy rotują cyklicznie, nie obejmują wszystkich
kombinacji. Automatyczny runner pełnych walk opisany w pierwotnym planie
pozostaje osobnym rozszerzeniem. Czas wykonania skryptu nie jest czasem tury gracza.

## UI, zapis i samouczek

- Wybór koloru/oferty, potwierdzenie tasowania, odzysk i korekta Loriana
  przechodzą przez istniejące runy planszy. Przeglądarka ma zgodne przyciski.
  Runy akcji, fokus i −/+ do kości oraz podsumowania zachowują swoje ścieżki.
- Ekran pokazuje wartości aktywnego bohatera, punktową pulę, ofertę,
  liczbę kart w talii, spalone i więzienia oraz pule pozostałych.
- Zapis przechowuje wszystkie strefy, znane karty, fazę, wersję katalogu,
  rewizję i obowiązek doboru. Można wznowić samą operację kart.
  Zachowana blokada zapisu podczas nierozstrzygniętej zdolności/reakcji
  lub wyniku przeciwnika wymaga ich dokończenia przed zapisem.
- Nowy kurs ma 134 ćwiczenia: wcześniejsze 99 zdolności/podbić i po 5 nowych
  podstaw dla każdego bohatera. Osobny postęp nie zalicza automatycznie starego kursu.
  Podstawy: dobór, zwykły atak i oszczędzanie, spalanie, więzienie/uwolnienie, drain.
- Lekcje zdolności przygotowują jawnie konkretną pulę, aby dało się ćwiczyć
  efekt bez czekania kilku tur. To tylko tryb lekcji. Pojedynek zaczyna od pustej puli.
- Rozmowy z NPC, obiekty i ich warunki pozostają dostępne w samouczku eksploracji.
  Ich reguła przekroczenia 21 nadal oznacza utrudnienie końcowego rzutu.
- Karty we wszystkich czterech formatach, strona `/rules/physical-mana`
  i PDF areny korzystają z nowego katalogu. Stabilne ścieżki plików zawierają
  historyczne `physical_mana_v02`; manifest wskazuje aktualny profil.

## Pliki i walidacja

Reguły: `rules/pooled_mana*.py`, katalog: `content/balance/pooled_mana/catalog.json`,
odczyt: `scenarios/pooled_mana_catalog.py`, integracja: `combat/pooled_mana.py`,
ewaluacja: `evaluation/pooled_mana.py`. Adapter istniejących akcji pozostaje
w `rules/shared_mana.py` i `ui/shared_mana.py`, dzięki czemu efekty nie mają
osobnej kopii na potrzeby nowej ekonomii. Niskopoziomowe `board/` bez zmian.

Testy celowane obejmują zachowanie wszystkich kart, duplikaty oferty,
pełny zwrot przy drainie, kolejność spodu/wierzchu, warunki podbić, pasywy/skazy,
prawdziwe płatności i efekty, zapis, runy, lekcje, reakcje i wrogie spalanie.
Przeglądarka jest sprawdzana w 390/1100 px. Dodatkowo zachowujemy regresje
starego rynku dla wcześniejszych zapisów. Nie wykonano próby na fizycznej planszy;
ostateczne tempo, czytelność i użyteczność liczb oceni ręczna rozgrywka użytkownika.

Wykonane pliki testów (sekwencyjnie przez `scripts/safe_pytest.sh`, z timeoutem;
po korektach ponawiane pliki albo konkretne przypadki):

| Plik w `tests/unit/` | Zaliczone przypadki |
|---|---:|
| `test_pooled_mana.py` | 33 |
| `test_pooled_mana_runtime.py` | 10 |
| `test_pooled_mana_training.py` | 19 |
| `test_pooled_mana_enemies.py` | 6 |
| `test_pooled_mana_points.py` | 9 |
| `test_pooled_mana_browser.py` | 4 |
| `test_training_walkthrough.py` | 33 |
| `test_garran_training_regressions.py` | 11 |
| `test_training_walkthrough_browser.py` | 2 |
| `test_garran_training_browser.py` | 2 |
| `test_mana_character_prints.py` | 25 |
| `test_shared_mana.py` | 13 |
| `test_shared_mana_runtime.py` | 30 |
| `test_physical_mana.py` | 19 |
| `test_session_snapshot.py` | 64 |
| `test_content_audit.py` | 2 |
| `test_exploration_mana_runtime.py` | 20 |

Łącznie 302 przypadki; pełnej wielomodułowej suite repozytorium nie uruchamiano.
Wydruki: 28 zestawów HTML/PDF i pakiet areny 67 stron. Automatyczny test
geometrii obejmuje wszystkie siedem postaci w obu układach (arkusze/karty),
a ręczny podgląd renderu PDF potwierdził wygląd strony zdolności Nimry.

# Koszyki run w działającej grze — 23.09.2026

Nowe walki Misji 0 i swobodny trening areny używają osobistych koszyków.
Starsze zapisy zachowują swój model. Dawny samouczek prowadzony ma własne
scenariusze ćwiczeń i nadal używa poprzedniego profilu; nie należy mieszać
jego instrukcji z nowymi kartami.

## Przygotowanie i pojemności

Przed pierwszą turą aplikacja prowadzi kolejno przez bohaterów i cztery
kategorie. Naciśnięcie runy deklaruje jeden fizyczny żeton; można wybrać
powtórzenia. Po zapełnieniu kategorii ✓ przechodzi dalej. ↩ cofa ostatni
żeton tej kategorii. Stan przygotowania można zapisać i wczytać.

| Bohater | Ofensywa | Obrona | Mobilność | Aura |
| --- | ---: | ---: | ---: | ---: |
| Garran | 2 | 4 | 1 | 2 |
| Brakka | 4 | 1 | 3 | 1 |
| Mira | 3 | 1 | 4 | 1 |
| Dagna | 1 | 2 | 1 | 4 |
| Lorian | 1 | 2 | 2 | 4 |
| Nimra | 3 | 1 | 2 | 3 |
| Erynd | 4 | 1 | 3 | 1 |

## Użycie mocy

1. Przycisk mocy otwiera podgląd. Cel wybiera się jego polem na planszy.
2. Po zatwierdzeniu celu wybiera się jeden własny żeton kategorii przycisku.
   Kotwica oznacza więc koszt Obrony. Nie trzeba wydawać właśnie Kotwicy.
3. Skaza może wymagać dodatkowych, jawnie wybieranych własnych żetonów.
4. Można wybrać najwyżej jeden Rezonans. Wymaga konkretnego symbolu innej kategorii.
5. Przy braku tego symbolu aplikacja pokazuje przytomnych sojuszników do 3 pól
   (również po przekątnej), z żetonem oraz niewykorzystaną reakcją.
   Wskazuje się figurkę pomocnika, a potem zatwierdza jego udział przez ✓.
   Pomocnik nie może płacić podstawy ani dopłaty skazy.
6. Po ewentualnym wyborze dodatkowych parametrów wyświetla się podsumowanie
   celu, efektu, budżetu, żetonów i pomocnika. Dopiero końcowe ✓ atomowo
   rozlicza koszty. ↩ przed tym punktem nie wydaje zasobów.
7. Rozstrzygnięcie korzysta z istniejącego silnika. Gracz wpisuje własne
   kości przez +/−/✓; aplikacja rzuca za przeciwników.

Reakcje wracają na początku rundy. Podstawowy ruch i atak pozostają bez run;
S, A, M i R są osobnymi budżetami zgodnie z kartą. Każda z 65 mocy ma
podstawę i przynajmniej jeden zaimplementowany Rezonans. Moce bez dawnych
ulepszeń otrzymały prosty wariant: 3 tymczasowe PW wykonującego (bez sumowania).
Pierwszy Szał również kosztuje żeton swojej kategorii.

## Ładowanie

Spirala otwiera Skupienie: koszt S, do dwóch własnych rozładowanych miejsc.
Dla każdego wybiera się kategorię, rzuca fizyczną k4 i ustawia wynik przez
+/− (wartość początkowa 2). Osobne podsumowanie ✓ zatwierdza symbol.

Most służy do **zgłoszenia spełnionego warunku odnowienia** opisanego na
karcie. Gracz potwierdza zdarzenie; aplikacja pilnuje limitu raz na rundę,
pojemności oraz wyniku k4. Pełny koszyk również zużywa limit. Jest to jawne
potwierdzenie przy stole, a nie automatyczne wykrywanie wszystkich zdarzeń.
Odnowienie klasowe nie pozwala zmienić swojej kategorii przez cofanie.

Strojenie Loriana ładuje jedno własne miejsce, Odzysk do dwóch (do trzech
z Rezonansem), raz na walkę. Nie ma wspólnej talii, doboru N+2 ani limitu ręki 7.

## Pliki i wydruk

- `content/print/rune_baskets_v01/catalog.json`: wspólne definicje 65 mocy,
  kategorii, Rezonansów, pojemności i skaz.
- `rules/rune_baskets.py`: niezmienny stan żetonów, przygotowanie i ładowanie.
- `combat/rune_baskets.py`: sprawdzanie kosztów, pomocy i wspólne rozliczenie.
- `ui/rune_baskets.py`: etapy, przyciski i LED; klient wyświetla stan serwera.
- `scripts/build_rune_baskets.py`: komplet 42 stron dla siedmiu postaci,
  pierwsza strona z polami na żetony zamiast notatek. A4, 100%, monochromatycznie.

Aktualny PDF: [karty postaci](../content/scenarios/misja_0_dzwon/print/runy_koszyki_v01/karty_postaci_A4.pdf).
Przyciski materiałów w aplikacji kierują do tego pliku. Układ i przepełnienia
kontroluje generator w Chrome. Czujniki oraz jasność fizycznych LED wymagają
próby na sprzęcie; testy aplikacji używają symulatora wejścia.

## Weryfikacja

60 ukierunkowanych przypadków przeszło przez `scripts/safe_pytest.sh`,
sekwencyjnie, z limitami czasu: `test_personal_rune_runtime.py` (16),
`test_personal_rune_browser.py` (1), `test_rune_basket_catalog.py` (28),
`test_rune_baskets_prints.py` (5) i regresje `test_rune_garran.py` (10).
Chrome sprawdził rzeczywiste `/play` i symulowane wejście planszy przy 1131×800.
Generator sprawdził wszystkie 42 strony A4; `validation.json` nie zawiera błędów.

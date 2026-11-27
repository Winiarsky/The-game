# Refaktor interfejsu gracza — 27.11.2026

## Cel i granice

Jeden interfejs do prowadzenia sesji przy fizycznej planszy: menu startowe,
wybór drużyny, narracja, przygotowanie, rozmowy, walka i informacje o bohaterach.
Flask, Jinja i zwykły JavaScript pozostają. Plansza pokazuje przestrzeń;
ekran prowadzi decyzję. Reguły, zapisy i transport sprzętowy są poza refaktorem.

## Projekt przed implementacją

Zachowujemy istniejący motyw gildii i ciemnej zieleni. Wyrazistym elementem
jest ilustracja sceny albo postać podejmująca decyzję. Otoczenie pozostaje
spokojne, bez nowych ozdobnych etykiet i automatycznych animacji.

Wspólna paleta:

| Rola | Kolor |
| --- | --- |
| Tło stołu | `#15221e` |
| Powierzchnia panelu | `#1b2d26` |
| Tekst | `#f0eadf` |
| Tekst pomocniczy | `#bec7bc` |
| Akcent gildii / aktywna tura | `#d6bd86` |
| Zaznaczenie klawiatury | `#91c8e4` |

Georgia dla nazw scen i bohaterów; systemowa rodzina bezszeryfowa dla
sterowania i danych. Bez pobierania fontów. Ważne podpisy mają co najmniej
12–13 px, liczby jednakową szerokość, dłuższa narracja 18 px i większą interlinię.

Układ rozgrywki, wyrównany do lewej:

```text
scenariusz i lokacja                       stan połączenia / menu
uczestnicy       kto działa / dostępne zasoby
                 bieżąca decyzja i wybrany cel
                 kontekst wejścia i koszt
                 zatwierdzenie / powrót / informacje
```

Pełna ściąga pozostaje w panelu postaci. Stała stopka podaje wyłącznie
sterowanie bieżącym krokiem. Zamknięty panel jest nieaktywny dla klawiatury
i czytnika ekranu; otwarty zatrzymuje fokus i przy zamknięciu oddaje go
poprzedniemu wyborowi. Złota aktywna tura i niebieski fokus są odrębnymi stanami.

Przegląd projektu: zachowujemy zaakceptowane portrety, ilustracje, kolory
planszy i treść misji. Wspólne style nie wprowadzają nowej mapy, frameworka
ani mobilnego przepływu. Wąskie okno ma pozostać obsługiwalne, ale priorytetem
jest laptop przy stole. To rozwinięcie obecnego kierunku, bez zmiany marki gry.

## Wdrożenie

1. Wspólne tokeny i style w `player_ui.css`, używane przez launcher i grę.
2. `player_ui.js`: normalizacja numpada, kierunkowe wybieranie elementów,
   obsługa fokusu paneli i komunikaty bez blokujących alertów przeglądarki.
3. Launcher i runtime korzystają z tej samej nawigacji; wybór elementu
   i wykonanie akcji pozostają oddzielone.
4. Semantyczne zakładki, nieaktywne tło panelu, skrót do treści, ograniczenie
   animacji i widoczny kontekst sceny także na dużym ekranie.
5. Błąd API zachowuje poprawny stan gry i pokazuje komunikat przy decyzji.
   Odrzucenie ze stanem serwera odświeża projekcję i rewizje wejścia, aby
   gracz mógł wykonać następny wybór. Sam komunikat nie zastępuje stanu gry.
6. W walce runicznej zakładka Moce pokazuje właściwy katalog bohatera,
   a zakładka Stany uwzględnia aktualne efekty walki. Zmiana bohatera
   zachowuje fokus przycisku wyboru.

## Walidacja i zależności deweloperskie

Playwright Python jest opcjonalną zależnością `ui-test`; nie jest importowany
przez aplikację. Pozwala sprawdzać prawdziwe klawisze, Tab/Shift+Tab, dialogi,
geometrię paneli i błędy przeglądarki. Korzysta z istniejącego Chrome, bez osobnej
instalacji Node/npm i bez pobierania dodatkowej przeglądarki. Zysk: powtarzalne próby
całych przepływów zamiast kolejnych jednorazowych skryptów CDP.

Przygotowanie środowiska: `python -m pip install -e '.[ui-test]'`.
Próby uruchamiamy wyłącznie przez `scripts/safe_pytest.sh`, po jednym pliku
lub wskazanych testach, z timeoutem. Dane sesji i zrzuty pozostają tymczasowe.

```bash
scripts/safe_pytest.sh --timeout 90 tests/integration/test_player_ui_browser.py
```

Opcjonalne `DND_UI_ARTIFACTS=/tmp/dnd-ui` zapisuje zrzuty w stałym katalogu.
Bez tej zmiennej zrzuty trafiają do katalogu tymczasowego danej próby.

Macierz: menu i drużyna; narracja i przygotowanie; decyzja/kość/wynik;
ruch i anulowanie; moce wieloetapowe; postać/ekwipunek/menu sesji;
blokady i błąd API; Num Lock; ograniczone animacje; okna 1221×656,
883×687 i 1221×569. Istniejące testy planszy pozostają kontrolą zgodności.

### Wynik po wdrożeniu

58 różnych testów zakończonych powodzeniem, w oddzielnych szeregowych
partiach przez bezpieczny wrapper z timeoutem:

| Plik lub wskazany przypadek | Testy |
| --- | ---: |
| `tests/integration/test_player_ui_browser.py` | 14 |
| `tests/unit/test_keyboard_launcher.py` | 18 |
| `tests/unit/test_launcher_board_browser.py` | 10 |
| `tests/unit/test_party_selection_layout_browser.py` | 9 |
| `tests/unit/test_keyboard_control_browser.py` | 1 |
| `tests/unit/test_keyboard_mission_browser.py` i `test_keyboard_inventory_browser.py` | 3 |
| `test_keyboard_setup_browser.py::test_keyboard_manual_setup_primary_advances_all_heroes_and_starts_initiative[1221-656]` | 1 |
| `tests/unit/test_session_navigation_browser.py` | 1 |
| `tests/unit/test_ui_asset_versions.py` | 1 |

Playwright sprawdza także dwa warianty błędów: odpowiedź z samym komunikatem
oraz prawdziwe odrzucenie nieaktualnej rewizji ze świeżą projekcją serwera.
Pierwszy zachowuje stan, drugi pozwala od razu wykonać kolejny poprawny wybór.
Oglądanie zrzutów wykryło i pomogło poprawić trzy regresje: ciemny tekst opcji
areny, przycięty komunikat walki oraz zmianę kolumn rozmowy po błędzie.
Testy obejmują teraz kontrast tekstu menu, widoczną geometrię komunikatu
i niezmienną geometrię sceny rozmowy. Test wersjonowania obejmuje nowe
`player_ui.js/css`, aby zwykłe odświeżenie pobierało poprawki.

Sprawdzono zrzuty menu, drużyny, narracji, wyposażenia, rozmowy, walki,
podglądu ruchu, rozwiniętego ekwipunku, mocy i komunikatów błędów.
`git diff --check` bez uwag. Testy korzystają z izolowanych danych;
fizyczne światła i numpad przy rozłożonej planszy wymagają osobnego ogrania.

## Skille

- `frontend-design` — hierarchia, typografia i zgodność z kontekstem gry.
- `web-design-guidelines` — dostępność, fokus, błędy, ruch i przewijanie.
- `webapp-testing` — Playwright w Pythonie i oglądanie wyrenderowanej aplikacji.
- `python-testing-patterns` — izolowane fixtures i testy zachowania.
- `pdf` — zainstalowany do materiałów drukowanych; obecny refaktor nie zmienia PDF.

# Podbicia wybierane runami — 2026-09-10

Podczas płatności na arenie każda opcja podbicia pokazuje runę z planszy,
symbole dodatkowych kart many i dokładny efekt. Lista rozwijana oraz wspólne
−/+ do zmiany podbić zostały zastąpione osobnymi przyciskami wariantów.

Przykład Uderzenia tarczą Garrana:

- Rozwidlenie (slot 6, pole 19,23): jedna dodatkowa czerwona mana,
  +1k6 obrażeń przy wygranym teście.
- Wieża (slot 7, pole 19,22): dwie dodatkowe czerwone many,
  +2k6 obrażeń przy wygranym teście.

Naciśnięcie wybiera pokazaną liczbę podbić danego rodzaju. Ponowne naciśnięcie
wybranego wariantu wyłącza go. Inny wariant tego samego podbicia zastępuje
dotychczasowy; warianty różnych rodzajów można łączyć. Dla Z bara runy 6–7
wybierają niebieskie odepchnięcie, a 8–9 czerwone obrażenia. Łączny limit
tej zdolności nadal wynosi dwa podbicia.

Pozycje są stałe dla danej zdolności, również gdy wariant jest niedostępny.
Serwer uwzględnia limit rodzaju i sumy podbić, pełny koszt wraz ze skazami
i dostępne karty rynku. Niedostępne warianty pokazują powód; ich pola nie
są aktywne. Wybrany wariant można wyłączyć także po utracie dostępnych kart.
Kolor podświetlenia odpowiada manie; czarny koszt używa widocznego szarego
światła i czarnego symbolu w UI, ponieważ czarny LED oznaczałby zgaszenie.

✓ potwierdza fizyczne odłożenie całego kosztu. ↩ anuluje bez płatności.
W płatności zwykłe akcje bohatera są wyłączone. Po zamknięciu okna runy
wracają do zwykłego znaczenia. Podbicia nie wymagają nowego nadruku planszy.
−/+ pozostają kontrolkami liczbowymi rzutów.

## Implementacja

- ui/shared_mana.py wyznacza warianty, koszty i dostępność; polecenie
  boost_option waliduje slot i rewizję, następnie używa dotychczasowego
  mechanizmu podbić. Nie zmieniono efektów ani kosztów zasad.
- ui/exploration_app.py wyznacza maskę i LED płatności z tych samych opcji,
  obsługuje runy oraz ✓/↩ po stronie serwera i uwzględnia rewizję many
  w kontekście wejścia. Stara rejestracja przeglądarki nie nadpisuje maski.
- ui/static/shared_mana.js oraz physical_mana.css rysują wybory z SVG run,
  symbolami many, wielkością efektu, stanem wyboru i powodem blokady.
- ui/static/board_panel.js pozostawia panel płatności pod kontrolą serwera.
- Komunikaty w exploration_app.py, exploration.js, szablonie gry oraz
  przepływach ataku, ruchu, leczenia i tury przeciwnika wskazują ✓/↩
  albo wybór na ekranie. Przypomnienia o kosztach kart używają symboli many.
  Obsługa klawiatury jako alternatywy pozostała; instrukcje demonstracji
  terminalowych nadal opisują rzeczywiste wejście w terminalu.

## Walidacja

Testy przez scripts/safe_pytest.sh, plik po pliku, timeout 60 s:

- test_mana_boost_panel.py: maska/LED, czerwone symbole i warianty 1/2,
  łączenie kolorów, limity, brak kart, anulowanie, stare rewizje, pełna
  fizyczna ścieżka runa → płatność → dodatkowa kość Uderzenia tarczą.
  Chrome sprawdza widoki 390 i 1100 px, polecenia przycisków, symbole,
  brak rozwijanej listy i brak poziomego przewijania; kompiluje też JS gry.
- test_shared_mana_runtime.py: dotychczasowe rozliczanie many i efekty.
- test_board_panel_runtime.py: runy akcji i niezależność panelu płatności.
- test_shield_bash_ui_flow.py: przebieg Uderzenia tarczą.
- test_board_scan_scheduling.py: planowanie skanów i licznik kości w Chrome.
- Wybrany test prezentacji exploration_ui_app: zaktualizowane instrukcje.

Łącznie 72 testy przeszły (w tym cztery przypadki Chrome).

Firmware ESP32 nie wymaga zmiany. Próba na fizycznej planszy pozostaje
do wykonania po restarcie aplikacji i odświeżeniu strony.

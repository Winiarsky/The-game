# Wspólna mana 0.3 — wdrożenie do testów areny

Stan: 2026-09-09. Profil nowych gier: `shared_mana_v03`.

## Mechanika

- Jeden rynek pięciu kart; 25 kart łącznie, po pięć każdego koloru. Aplikacja liczy talię, rynek i odrzucone; kolory gracze wybierają i kontrolują przy stole.
- Deklaracja celu i podbić → cały koszt z rynku na odrzucone → potwierdzenie → rzuty i efekt. Podbicia, mana dowolna, zamiany koloru i dopłaty za skazy mieszczą się w pięciu kartach. Odzysk może przywrócić własny koszt.
- Na końcu tury bohatera najpierw efekty końca tury, następnie potwierdzony dobór do pięciu. Wyczerpanie talii włącza obowiązek odrzucenia jednej karty po turze bez wydanej many. Reakcja poza własną turą nie liczy się jako wydatek we własnej turze.
- Odświeżenie zbiera wszystkie 25 kart, włącznie z rynkiem. Potwierdzenie nowego rynku wygasza O. Pusta talia i rynek proszą o odświeżenie po całym rozstrzygnięciu; nigdy pomiędzy zapłatą i odzyskaniem kart ani w trakcie przerwanego ataku.
- T kończy się na początku następnej tury źródła. Zachowane są wcześniejsze zakończenia: wykorzystanie jednorazowej premii, ruch z postawy, leczenie krwawienia i przerwanie koncentracji. Odświeżenie nie przyznaje nowej tury ani akcji.
- 66 zdolności: po 4 basic / 3 z podbiciami / 2 ulty; Nimra 5 / 4 / 3. Odpędzenie nieumarłych jest osobnym Świętym symbolem Dagny.
- Skaza Dagny sprawdza sąsiedniego żywego sojusznika mającego **ściśle mniej niż połowę PW**, także 0 PW, i przypomina dopłatę przed każdą ofensywą. Ukryta Mira ma utrudnienie obron i wykonywanych testów reakcji; Unik pozostaje bez rzutu.
- Hymn daje maksymalnie dwie akcje dodatkowe we własnej turze podczas pobytu w aurze. Wyjście i ponowne wejście nie odnawia wykorzystanego budżetu.
- Z bara i Uderzenie tarczą korzystają z fizycznego rzutu bohatera i automatycznego rzutu przeciwnika. Deszcz strzał ma jeden test przeciw osobnym KP i osłonie, wspólne obrażenia oraz pojedyncze użycie Znaku i Pierwszej krwi.

## Interfejs i plansza

Akcje mają ikony oraz kolory: główna niebieski, dodatkowa pomarańczowy, ruch zielony, wyposażenie i koniec tury szary. Okno płatności pokazuje koszt, skazę, podbicia, zamiany kolorów i dodatkowe cele/pola. Osobne potwierdzenia opisują fizyczne operacje kart.

Poprawka po sesji 2026-09-10: dolny pasek ponownie podświetla dostępne akcje i pozwala wybierać je nadrukowanymi polami planszy, zgodnie z menu ekranowym i pozostałym budżetem tury. **Nadrukowane dolne runy na mapie nie zostały zastąpione ani usunięte.** Podczas płatności i rzutów wybór innych akcji jest zablokowany. Ikony w UI pozostają dodatkowym sposobem wyboru. Narożne −, +, ✓ i ↩ zachowują swoje pozycje; sterują wartościami, zatwierdzaniem i powrotem. Setup i inicjatywa nadal używają potwierdzenia planszy.

## Pliki

- `rules/shared_mana.py` i `rules/shared_mana_catalog.py`: deterministyczny licznik, procedura kart i katalog zdolności.
- `combat/shared_mana*.py`, `combat/shared_command.py`, `combat/shared_volley.py`: skazy, podbicia, efekty, dodatkowy ruch, reakcje i aura Hymnu; integracja w istniejących usługach walki.
- `ui/shared_*.py`, `ui/static/shared_mana.js`, `ui/exploration_app.py`: płatność przed efektem, transport przycisków, okna kart i prezentacja.
- `save/session_snapshot.py`: utrwalanie rynku, cyklu, Echa i budżetów tury.
- `physical_cards/mana_print*.py`: wspólne źródło aktualnych kart. Stała ścieżka eksportu `assets/physical_cards/character_sets/physical_mana_v02/` pozostaje dla zgodności linków; manifest zawiera profil 0.3.

Ścieżki kodu powyżej są względem `src/dnd_board_game/`.

## Materiały do druku

Dawny zbiorczy PDF areny i siedmiu bohaterów został usunięty. Obecne wydruki są w [handouts/README.md](../handouts/README.md): karty postaci, plansza A4 i pełna plansza dla drukarni. Aktualną skalę i sposób generowania opisuje [instrukcja wydruku](ARENA_A4_PRINT_PACK.md).

Wszystkie 28 indywidualnych PDF-ów zostało wygenerowanych ponownie i sprawdzonych pod względem liczby stron. Arkusze kolorowe/minimalistyczne mają po 5 stron na postać, warianty do wycinania po 6. Kontrola 28 HTML w trybie druku nie wykazała przepełnionych stron. Historia i wyposażenie oraz zasady mają osobne strony.

## Weryfikacja

Poprawka panelu 2026-09-10: 63 celowane testy (`test_board_panel_runtime.py`,
`test_initiative_panel.py`, `test_shared_mana_runtime.py`) przeszły kolejno przez
`scripts/safe_pytest.sh --timeout 60`. Sprawdzono powrót LED i skanowania po
inicjatywie, wszystkie siedem menu, kolory, wybór akcji przez skan, blokady
płatności/rzutów i przywrócenie menu po anulowaniu płatności. Próba na fizycznej
planszy wymaga ponownego uruchomienia aplikacji.

**286 celowanych testów zakończyło się powodzeniem.** Nie uruchamiano całego zestawu repozytorium. Testy uruchamiano kolejno przez `scripts/safe_pytest.sh --timeout 60`; bez równoległych procesów pytest. Sprawdzono:

- licznik 25 kart, presję talii, powtórzenia żądań, Odzysk własnego kosztu i granice odświeżenia;
- płatności, podbicia, pełny katalog, skazy, Hymn, reakcje, serie, czary, ruch dodatkowy i T/O;
- zapis/wczytanie, ruch magiczny, czary obszarowe, strefy i zachowanie zasobów zwykłych postaci;
- setup, inicjatywę, wyłączenie dolnych pól, narożne kontrolki i ochronę czasu odpowiedzi;
- zgodność kart z profilami postaci, skalę i kompletność mapy oraz pakiet PDF.

Chrome z lokalnym symulatorem planszy: wybór celu, +/− podbicia, ✓ płatności, k20, k6 i ✓ wyniku. Drugi przebieg sprawdził podbicia Odzysku i powrót właśnie wydanych kart na talię. Widoki 390 i 1280 px mieszczą się bez poziomego przewijania. Sprawdzono składnię skryptów i brak wyjątków przeglądarki. Statyczna kontrola zmienionych plików Pythona nie zgłasza niezdefiniowanych nazw.

Do próby przy stole uruchom ponownie aplikację, rozpocznij nową walkę areny i przygotuj 25 kart z rynkiem pięciu. Testy symulatorem nie zastępują oceny płynności fizycznych LED ani pomiaru rzeczywistego wydruku. Balans kosztów i siły zdolności wymaga rozgrywki z graczami. Przebudowa Głodnych Cieni na kafelki pozostaje odłożona zgodnie z ustaleniem.

# Odprawa Nessy — dopracowanie 2026-09-05

Wdrożono uzgodnione poprawki istniejącej sceny, bez dodawania many ani presji czasu do eksploracji.

## Przebieg dla graczy

1. Rozmowę otwiera portret Nessy, krótki opis postaci i odprawa. Wypowiedzi Nessy, gesty narratora i wynik mechaniczny są wizualnie rozdzielone. Zwykłe pytania nie wymagają wyboru bohatera ani rzutu.
2. Siedem tematów zachowuje numery, pola planszy i ilustracje: Zaginięcie, Ładunek, Ludzie, Obserwuj Nessę, Dokumenty, Warunki umowy, Zakończ odprawę. Omówione tematy pokazują przypomnienie faktycznie uzyskanego wyniku. Nie wykonują ponownie efektów, nie zużywają prób i nie wypłacają nagród. Podgląd przetrwa zapis/wczytanie.
3. Obserwacja Nessy to jedna próba Intuicji ST 16. Porażka nie pogarsza umowy. Sukces odkrywa szczególne znaczenie pyłu, bez ujawnienia jego przyczyny i bez sugerowania obojętności Nessy wobec ludzi. Zwykła odpowiedź o ładunku nie zdradza tej samej wskazówki.
4. Dokumenty pozostają osobistym testem Erynda, ponieważ zna opowieść drwali. Porażka przypomina podstawową trasę, ale nie potwierdza magii. Bez Erynda pole wyjaśnia niedostępność testu; niezbędne informacje można uzyskać w zwykłej rozmowie o zaginięciu.
5. Negocjacje prowadzą przez bohatera, podejście, krótki argument, warunki testu i rzut. Perswazja pozwala uzasadnić dopłatę za ryzyko (`risk_request`) albo premię za ocalonych (`fair_request`); Zastraszanie wymaga nacisku (`hard_terms`), Oszustwo dotyczy zaliczki (`calculated_lie`). UI pokazuje przed deklaracją rodzaj ustępstwa i poznane argumenty. Silnik nadal weryfikuje znane fakty i rozstrzyga nagrody; LLM interpretuje treść, a nie talent pisarski gracza.
6. Rozwijana karta umowy pokazuje stawkę, dopłatę, wypłaconą zaliczkę, pozostałą wypłatę po misji, premię do wspólnej puli, wydatki i zaopatrzenie. Zaliczka jest odliczana, nie dodawana drugi raz. Otwarcie karty nie zmienia pieniędzy ani ekwipunku.
7. „Zakończ odprawę” wymaga osobnego potwierdzenia i zamyka jej testy oraz negocjacje. Niewybrane tematy są opcjonalne, bez licznika ukończenia. „Wróć do Gildii” tylko odchodzi od biurka. Podróż rozpoczyna się osobno przy bramie.

Nierozstrzygnięte tematy zamkniętej odprawy nie pokazują sekretnej odpowiedzi. Przypomnienie jest zabezpieczone także w API; samo ukrycie przycisku nie jest granicą poprawności.

## Pliki

- `content/scenarios/ostatni_transport_00_gildia.json` — treść, blokady, próby i dodatkowy wariant negocjacji.
- `content/prompts/gm_npc_interaction_pl.md` — ocena sensu argumentu i zgodności żądanego ustępstwa.
- `src/dnd_board_game/ui/nessa_briefing.py` — prezentacja rzeczywistych wyników i umowy na podstawie istniejących flag/stanu NPC.
- `src/dnd_board_game/ui/exploration_app.py` — integracja podglądu, ochrona przed ponowieniem, lokalne testy autorskie bez LLM i nazwa wyjścia na planszy.
- `src/dnd_board_game/ui/static/exploration.js`, `static/nessa_briefing.css`, `templates/exploration.html` — kafelki, portret, czytelna rozmowa, przypomnienia i karta umowy.
- `tests/unit/test_nessa_briefing.py` — regresje rozstrzygnięć, podglądu, zapisu, informacji, pieniędzy i stałych pól.
- `GAME_DESIGN.md`, `TODO.md`, `content/scenarios/campaign/MAPA_0_GILDIA_NESSA_SPEC.md` — aktualizacja przyjętych zasad i dalszych zadań.

Wykorzystano istniejący portret i ilustracje. Nie dodano zależności ani nowych obrazów.

## Weryfikacja

Każdy plik uruchomiono osobno przez `scripts/safe_pytest.sh --timeout 60`:

- `tests/unit/test_nessa_briefing.py`: 11 zaliczonych przypadków.
- `tests/unit/test_nessa_dynamic_negotiation.py`: 7.
- `tests/unit/test_npc_goal_execution.py`: 8.
- `tests/unit/test_npc_arguments.py`: 3.
- `tests/unit/test_ostatni_transport_map0.py`: 38 zaliczonych, 1 niezaliczony test odtwarzania walki (opis poniżej). Ponownie sprawdzono 38 przypadków z wyłączeniem tej porażki.

Przeglądarka Chrome: widoki 1440 px i 390 px bez poziomego przepełnienia i wyjątków JavaScript. Sprawdzono podgląd omówionego tematu, warianty Perswazji, zachowanie otwartej karty umowy, Numpad 2 (przypomnienie) i Numpad 7 (potwierdzenie zakończenia, bez automatycznego wykonania). Kompilacja Pythona i `git diff --check` również sprawdzone. Fizyczna plansza nie była podłączona.

### Znany problem poza odprawą

`test_map1_defeat_enters_game_over_without_revealing_exploration` wykazał rozbieżność po wczytaniu checkpointu i ponowieniu walki: `reconcile_boardgame_feature_removals` dopisuje Brakce `flaw_chains`, podczas gdy aktor źródłowy scenariusza miał puste `features`. Różnica dotyczy migracji cech postaci przy odtwarzaniu starcia; nie zmieniano tej funkcji w pracach nad Nessą. Problem zapisano w TODO na etap sceny walki. Nie należy traktować całego pakietu testów Mapy 1 jako zaliczonego.

Do sprawdzenia przy stole: płynność rozmowy, rozmiar kafelków na docelowym ekranie i balans jednorazowych negocjacji. Starsze zapisy nie cofają już rozegranych decyzji; pełną nową odprawę należy sprawdzać od początku sceny.

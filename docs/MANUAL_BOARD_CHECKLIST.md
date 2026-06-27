# Manualna Checklista Planszy

Ten dokument opisuje ręczne testy na symulatorze albo fizycznej planszy.

Każdy punkt powinien mieć wynik:

- `PASS`
- `FAIL`
- `BLOCKED`
- `NOT TESTED`

## Przygotowanie

- [ ] Plansza ma zasilanie.
- [ ] Kontroler LED odpowiada.
- [ ] Skanowanie pól działa.
- [ ] `board.Connection` uruchamia się bez błędów.
- [ ] Jeśli używany jest symulator, strona symulatora działa.
- [ ] Testowy scenariusz ma znane pozycje aktorów i przeszkód.

## Test Mapowania LED

- [ ] Pole `(0, 0)` zapala oczekiwany LED.
- [ ] Pole `(0, 29)` zapala oczekiwany LED.
- [ ] Pole `(1, 29)` zapala oczekiwany LED.
- [ ] Pole `(1, 0)` zapala oczekiwany LED.
- [ ] Kilka pól w środku planszy zapala poprawne fizyczne pozycje.
- [ ] `leds_off()` gasi wszystkie testowane LED-y.

## Test Skanowania Pola

- [ ] Kliknięcie/wciśnięcie jednego pola zwraca poprawne `(col, row)`.
- [ ] Kilka pól w rogach zwraca poprawne koordynaty.
- [ ] Kilka pól w środku zwraca poprawne koordynaty.
- [ ] Anulowanie skanu działa.
- [ ] Ponowne uzbrojenie skanu działa po anulowaniu.

## Test Ruchu

Stan testowy:

- aktywny aktor na znanym polu,
- speed `30 feet`,
- kilka przeszkód,
- przynajmniej jedno pole trudnego terenu.

Checklist:

- [ ] Plansza pokazuje aktywnego aktora.
- [ ] LED-y pokazują pełny zasięg ruchu.
- [ ] Zasięg ortogonalny odpowiada 6 polom normalnego terenu.
- [ ] Ruch diagonalny kosztuje naprzemiennie 5/10/5/10 feet.
- [ ] Trudny teren kosztuje 10 feet.
- [ ] Ściany blokują przejście.
- [ ] Blokujące przeszkody blokują wejście na pole.
- [ ] Nie da się zakończyć ruchu na zajętym polu.
- [ ] Po wyborze celu LED-y pokazują wybraną ścieżkę.
- [ ] Po zatwierdzeniu ruchu aktor ma nową pozycję.

### Runtime `demo_movement`

Test bez planszy:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_movement --board-backend none --destination 3,3 --session-id manual_demo
```

- [ ] Terminal pokazuje origin, destination, reachable count, path i cost.
- [ ] Powstaje `data/session_observations/manual_demo.jsonl`.
- [ ] Plik zawiera `movement_path_selected` i `session_finished`.

Test celu zablokowanego:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_movement --board-backend none --destination 1,0 --session-id blocked_demo
```

- [ ] Terminal pokazuje `path_valid: False`.
- [ ] Plik obserwacji zawiera `movement_rejected`.
- [ ] Program kończy się bez stack trace.

Test w symulatorze:

```bash
python -m board.simulator.app
```

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_movement --board-backend simulator --board-url http://127.0.0.1:5000 --destination 3,3 --show-leds --session-id simulator_demo
```

- [ ] Aktywny aktor jest oznaczony LED.
- [ ] Zasięg ruchu jest widoczny.
- [ ] Trudny teren jest oznaczony pomarańczowo.
- [ ] Blokujące pole jest oznaczone czerwono.
- [ ] Przeciwnik jest oznaczony różowo.
- [ ] Sojusznik jest oznaczony cyan.
- [ ] Wybrana ścieżka jest pokazana LED.
- [ ] Cel jest wyróżniony.
- [ ] Plik obserwacji zawiera `led_feedback_sent`.

## Test Ataku

Stan testowy:

- aktywny aktor ma cel w zasięgu ataku,
- cel ma znane AC i HP.

Checklist:

- [ ] LED-y pokazują legalne cele ataku.
- [ ] Aplikacja prosi o naturalny wynik `d20`.
- [ ] Aplikacja dolicza modyfikator ataku.
- [ ] Trafienie/pudło jest rozstrzygnięte poprawnie.
- [ ] Naturalne `20` daje krytyczne trafienie.
- [ ] Naturalne `1` daje automatyczne pudło.
- [ ] Przy trafieniu aplikacja prosi o wynik obrażeń.
- [ ] HP celu zmienia się poprawnie.
- [ ] LED-y pokazują wynik ataku.

### Runtime `demo_mini_combat`

Terminal 1:

```bash
python -m board.simulator.app
```

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --hero-attack-roll 14 --hero-damage 6 --hero-damage-type slashing --session-id mini_combat_simulator_demo
```

- [ ] Aplikacja mówi, że aktywny aktor wybiera `Atak`.
- [ ] Symulator jest w trybie `Plansza`, nie `Przesuwanie figurek`.
- [ ] Legalne cele świecą na niebiesko.
- [ ] Podczas komunikatu wyboru celu legalne cele nadal świecą na niebiesko.
- [ ] Można kliknąć legalne pole celu w symulatorze zanim LED-y zgasną.
- [ ] Kliknięcie nielegalnego pola nie zawiesza flow i przechodzi do fallbacku.
- [ ] Jeśli skan celu nie zadziała, runtime używa fallbacku `--target-id`.
- [ ] Po wyborze świeci tylko wybrany cel.
- [ ] Komunikat pokazuje źródło ataku i aktywne modyfikatory.
- [ ] Trafienie świeci zielono.
- [ ] Pudło świeci czerwono.
- [ ] Trafienie krytyczne świeci żółto.
- [ ] Po potwierdzeniu LED gaśnie.
- [ ] Przy trafieniu HP celu spada.
- [ ] Plik obserwacji zawiera `attack_declared`, `attack_resolved` i `damage_applied`.

### Runtime `demo_mini_combat_loop`

Terminal 1:

```bash
python -m board.simulator.app
```

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/goblin_ambush.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --scan-timeout 30 --hero-attack-roll 14 --hero-damage 6 --hero-damage-type slashing --enemy-seed 7 --max-rounds 3 --session-id mini_combat_loop_simulator_demo
```

- [ ] Na początku każdej tury świeci aktywny aktor.
- [ ] Terminal pokazuje nazwę scenariusza z pliku contentu.
- [ ] Po potwierdzeniu aktywnego aktora LED gaśnie albo przechodzi do następnego kroku.
- [ ] Bohater widzi legalne cele ataku na niebiesko.
- [ ] Po wyborze świeci tylko wybrany cel.
- [ ] Wynik ataku bohatera świeci odpowiednim kolorem.
- [ ] Goblin wykonuje auto-atak bez wpisywania rzutu przez gracza.
- [ ] Podczas auto-ataku goblina LED-y pokazują jego cel i wynik.
- [ ] HP aktorów zmienia się w terminalu po trafieniach.
- [ ] Walka kończy się po pokonaniu jednej strony albo zatrzymuje po `--max-rounds`.
- [ ] Plik obserwacji zawiera `turn_started`, `action_used`, `turn_finished`, `enemy_action_selected` i `combat_finished` albo `combat_stopped`.

### Runtime `demo_mini_combat_loop` Multi-Actor

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/multi_actor_skirmish.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --scan-timeout 30 --enemy-seed 7 --max-rounds 5 --session-id multi_actor_simulator_demo
```

- [ ] Terminal pokazuje scenariusz `Potyczka przy rozbitych skrzyniach`.
- [ ] Tury przechodzą przez 2 bohaterów i 3 przeciwników.
- [ ] Przy wyborze celu świecą wszystkie legalne cele aktualnego bohatera.
- [ ] Kliknięcie legalnego celu wybiera właściwego przeciwnika.
- [ ] Wynik ataku świeci tylko na wybranym celu.
- [ ] Pokonani aktorzy nie wykonują kolejnych tur.
- [ ] Walka kończy się dopiero po pokonaniu całej strony.
- [ ] Plik obserwacji zawiera `target_selected`.

### Runtime `demo_mini_combat_loop` Board-First Turn

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/movement_skirmish.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --scan-timeout 30 --enemy-seed 7 --max-rounds 5 --session-id board_first_turn_simulator_demo
```

- [ ] Na starcie tury aktywny bohater świeci na biało.
- [ ] Legalne pola ruchu świecą przygaszonym niebieskim/cyan.
- [ ] Legalne cele ataku świecą mocnym niebieskim.
- [ ] Pierwsze kliknięcie pustego legalnego pola pokazuje ścieżkę ruchu na żółto i komunikat z kosztem.
- [ ] Drugie kliknięcie tego samego pola potwierdza ruch i aktualizuje pozycję aktora.
- [ ] Pierwsze kliknięcie legalnego celu pokazuje warunki ataku i prosi o ponowne kliknięcie.
- [ ] Drugie kliknięcie tego samego celu potwierdza atak.
- [ ] Kliknięcie innego legalnego pola przed potwierdzeniem zmienia podgląd bez wykonywania poprzedniej intencji.
- [ ] Kliknięcie pola aktywnego aktora pokazuje opcję zakończenia tury.
- [ ] Drugie kliknięcie pola aktywnego aktora kończy turę przed wykorzystaniem całego ruchu.
- [ ] Po ataku można jeszcze ruszyć się pozostałym ruchem.
- [ ] Przeciwnik bez celu ataku podchodzi do najbliższej pozycji ataku.
- [ ] Ruch przeciwnika pokazuje ścieżkę na czerwono i docelowe pole na pomarańczowo.
- [ ] Po fizycznym przestawieniu figurki przeciwnika kliknięcie pomarańczowego pola potwierdza ruch.
- [ ] Plik obserwacji zawiera `turn_intent_previewed`, `turn_intent_confirmed`, `movement_committed`, `attack_previewed` i `target_selected`.

### Runtime `demo_mini_combat_loop` Pierwsza Grywalna Scena

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/first_playable_scene.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --scan-timeout 30 --initiative-mode rolled --enemy-seed 7 --max-rounds 8 --session-id first_scene_simulator_demo
```

- [ ] Przed startem sceny aplikacja pokazuje komunikat setupu.
- [ ] Pola startowe bohaterów świecą na biało/cyan.
- [ ] Każdy bohater jest wywołany osobno do ustawienia figurki.
- [ ] Kliknięcie jednego z podświetlonych pól startowych potwierdza ustawienie danego bohatera.
- [ ] Jawni przeciwnicy i elementy sceny są ustawiane krokami, maksymalnie po 5 pól naraz.
- [ ] Kliknięcie jednego z pól aktualnej grupy potwierdza ustawienie tej grupy.
- [ ] Po setupie aplikacja komunikuje rozpoczęcie inicjatywy.
- [ ] Każdy bohater jest wywołany osobno do rzutu inicjatywy.
- [ ] Przy rzucie inicjatywy świeci pole aktualnie wywołanego aktora.
- [ ] Przeciwnicy mają inicjatywę rzuconą automatycznie i też są chwilowo podświetlani.
- [ ] Aplikacja pokazuje finalną kolejność inicjatywy przed pierwszą turą.
- [ ] Jeśli przeciwnik rusza się w swojej turze, ścieżka świeci na czerwono, docelowe pole na pomarańczowo, a ruch wymaga kliknięcia pola docelowego.
- [ ] Aplikacja pokazuje cel sceny.
- [ ] Widoczni przeciwnicy poza zasięgiem świecą przygaszonym czerwonym/różowym, a nie wyglądają jak puste pola.
- [ ] Obiekt interaktywny świeci na zielono.
- [ ] Kliknięcie obiektu pokazuje opcję interakcji i opis.
- [ ] Drugie kliknięcie tego samego obiektu potwierdza interakcję.
- [ ] Aplikacja pokazuje warunki testu cechy: cecha/skill, ST, aktywne modyfikatory i końcowy modyfikator.
- [ ] Po wpisaniu naturalnego wyniku d20 aplikacja pokazuje sukces albo porażkę.
- [ ] Sukces miga/świeci na zielono, porażka na czerwono.
- [ ] Po spełnieniu celu aplikacja kończy scenę.
- [ ] Plik obserwacji zawiera `scene_setup_started`, `scene_setup_step_confirmed`, `scene_setup_confirmed`, `roll_requested`, `roll_resolved`, `enemy_initiative_rolled`, `initiative_set`, `board_scan_requested`, `board_scan_received`, `objective_started`, `interaction_options_shown`, `ability_check_requested`, `ability_check_resolved`, `scene_flag_set`, `objective_completed` i `scene_finished`.

## Test Obserwacji Sesji

- [ ] Każdy ruch zapisuje metadane: aktor, start, cel, koszt, ścieżka.
- [ ] Każdy rzut zapisuje metadane: typ, naturalny wynik, modyfikator, wynik końcowy.
- [ ] Każdy atak zapisuje metadane: atakujący, cel, wynik, obrażenia.
- [ ] Każda tura zapisuje metadane: aktywny aktor, numer rundy, zużycie akcji i koniec tury.
- [ ] Każdy błąd zapisuje krótki opis i aktualny stan.
- [ ] Plik obserwacji można otworzyć i odczytać bez aplikacji.

## Test Setupu I Inicjatywy

Terminal 1:

```bash
python -m board.simulator.app
```

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_initiative_setup --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --session-id initiative_simulator_demo
```

Checklist:

- [ ] Jeśli LED-y są zbyt szybkie, uruchom demo z `--wait-for-enter`.
- [ ] Komunikat startu walki pojawia się przed setupem.
- [ ] LED-y setupu odpowiadają aktualnemu komunikatowi.
- [ ] Jawni bohaterowie są podświetleni podczas kroku ustawiania bohaterów.
- [ ] Jawni przeciwnicy są podświetleni podczas kroku ustawiania przeciwników.
- [ ] Jawne elementy otoczenia są podświetlane partiami zgodnymi z komunikatem.
- [ ] Po zakończeniu każdego kroku poprzednie LED-y gasną.
- [ ] Przy rzucie inicjatywy świeci tylko aktualnie wywołany aktor.
- [ ] Po wpisaniu wyniku albo auto-rollu pole aktora gaśnie.
- [ ] Ukryte i warunkowe elementy nie są zdradzane graczom.
- [ ] Po ustaleniu kolejności świeci aktywny aktor pierwszej tury.
- [ ] `data/session_observations/initiative_simulator_demo.jsonl` zawiera `setup_step_started`, `roll_requested`, `enemy_initiative_rolled`, `initiative_set` i `turn_started`.

## Test Eksploracji

Terminal 1:

```bash
python -m board.simulator.app
```

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_exploration_scene --scenario content/scenarios/abandoned_watchtower.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --scan-timeout 30 --session-id abandoned_watchtower_simulator_demo
```

Checklist:

- [ ] Aplikacja prosi o położenie mapki eksploracji na planszy.
- [ ] LED-y pokazują dostępne lokacje przez ich punkty główne, bez świecenia całych stref i bez dodatkowego potwierdzania setupu stref.
- [ ] Jawne elementy fizyczne oznaczone `requires_setup` są rozstawiane osobno i potwierdzane kliknięciem.
- [ ] Ukryta skrytka nie świeci podczas setupu.
- [ ] Domyślny widok eksploracji pokazuje tylko główne punkty dostępnych lokacji.
- [ ] Kliknięcie innej strefy pokazuje pytanie o przejście.
- [ ] Drugie kliknięcie tej samej strefy potwierdza przejście.
- [ ] Kliknięcie aktualnego punktu głównego pokazuje wszystkie opcje jako kolorowe pola menu.
- [ ] Kliknięcie pola opcji wybiera tę konkretną opcję.
- [ ] Opcja `Wycofaj` zamyka menu i wraca do widoku punktów głównych.
- [ ] Opcja `Rozejrzyj się po okolicy` podświetla całą strefę na 30% i pozwala kliknąć kafle strefy.
- [ ] Opcja `Zbadaj obszar` prosi o rzuty całej drużyny.
- [ ] Najwyższy wynik drużyny rozstrzyga test.
- [ ] Sukces ujawnia ukrytą skrytkę LED-em.
- [ ] Ponowne badanie tej samej strefy jest blokowane.
- [ ] JSONL zawiera `exploration_started`, `exploration_setup_confirmed`, `exploration_menu_opened`, `exploration_menu_option_selected`, `party_check_resolved` i `zone_search_revealed`.

## Notatki Z Testu

```text
Data:
Backend: simulator / hardware
Scenariusz:
Tester:

Wynik:

Problemy:

Następne poprawki:
```

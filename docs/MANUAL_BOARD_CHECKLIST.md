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
- [ ] Ruch diagonalny kosztuje 5 feet.
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

## Test Obserwacji Sesji

- [ ] Każdy ruch zapisuje metadane: aktor, start, cel, koszt, ścieżka.
- [ ] Każdy rzut zapisuje metadane: typ, naturalny wynik, modyfikator, wynik końcowy.
- [ ] Każdy atak zapisuje metadane: atakujący, cel, wynik, obrażenia.
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

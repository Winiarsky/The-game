# Uruchamianie I Testowanie

Ten dokument opisuje docelowy sposób uruchamiania nowej aplikacji oraz testowania jej bez fizycznej planszy i z fizyczną planszą.

Na obecnym etapie aplikacja ma pierwszy runtime debugowy dla ruchu. Nie jest to jeszcze docelowe UI gry.

## Tryby Uruchamiania

Docelowo projekt powinien mieć trzy tryby pracy.

### 1. Testy Jednostkowe

Służą do sprawdzania czystej logiki gry bez UI, hardware i plików contentu.

Przykład:

```bash
scripts/safe_pytest.sh --timeout 60 tests/unit/test_grid.py
```

Używać dla:

- koordynatów,
- planszy,
- pathfindingu,
- rzutów kośćmi,
- obrażeń,
- inicjatywy,
- prostych reguł D&D 5e.

### 2. Tryb Symulatora

Służy do sprawdzania integracji z warstwą `board.Connection` bez fizycznej planszy.

Docelowy model:

```bash
python -m board.simulator.app
```

W drugim terminalu:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_movement --board-backend simulator --board-url http://127.0.0.1:5000 --destination 3,3 --show-leds
```

Ten runtime pokazuje testowy zasięg ruchu i wybraną ścieżkę LED-ami.

### 3. Tryb Hardware

Służy do testów na fizycznej planszy.

Docelowy model:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_movement --board-backend hardware --destination 3,3 --show-leds
```

Opcjonalnie:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_movement --board-backend hardware --board-serial-port /dev/ttyUSB0 --wled-url http://192.168.0.50 --destination 3,3 --show-leds
```

Tryb hardware powinien być używany dopiero po przejściu testów jednostkowych i testów w symulatorze.

## Runtime Debugowy Ruchu

Pierwszy runtime jest terminalowym scenariuszem ruchu:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_movement --board-backend none --destination 3,3 --session-id manual_demo
```

Argumenty:

- `--board-backend none | simulator | hardware`
- `--board-url http://127.0.0.1:5000`
- `--board-serial-port /dev/ttyUSB0`
- `--wled-url http://192.168.0.50`
- `--destination COL,ROW`
- `--session-id NAZWA_SESJI`
- `--observation-dir data/session_observations`
- `--show-leds` albo `--no-show-leds`

Runtime pozwala:

- załadować testową planszę,
- ustawić aktywnego bohatera, sojusznika i przeciwnika,
- wskazać aktywnego aktora,
- pokazać zasięg ruchu LED-ami,
- wybrać pole docelowe przez `--destination`,
- pokazać ścieżkę,
- zapisać metadane sesji.

Legenda LED dla `demo_movement`:

- biały: aktywny aktor,
- niebieski: pole, na którym można zakończyć ruch,
- żółty: wybrana ścieżka,
- zielony: cel,
- pomarańczowy: trudny teren,
- czerwony: blokujące pole,
- różowy: przeciwnik,
- cyan: sojusznik.

Ataki, rzuty kośćmi i pełny przebieg tury nie są jeszcze częścią tego runtime.

## Zasada Testowania Funkcji

Każda większa funkcja powinna przejść przez trzy poziomy:

1. Test jednostkowy czystej logiki.
2. Test integracyjny bez hardware.
3. Manualny test na symulatorze albo fizycznej planszy.

Przykład dla ruchu:

- unit: `movement_range()` zwraca poprawne pola,
- integration: adapter LED dostaje `reachable_tiles`,
- manual: plansza podświetla pola zgodnie z checklistą.

## Gdzie Trzymać Wyniki Manualnych Testów

Manualne testy powinny zapisywać krótkie notatki w:

```text
data/manual_test_runs/
```

Ten katalog powinien być ignorowany przez git, chyba że zdecydujemy inaczej.

Docelowo obserwator sesji powinien automatycznie tworzyć metadane w:

```text
data/session_observations/
```

Te pliki również nie powinny trafiać do commita domyślnie.

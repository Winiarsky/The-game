# Uruchamianie I Testowanie

Ten dokument opisuje docelowy sposób uruchamiania nowej aplikacji oraz testowania jej bez fizycznej planszy i z fizyczną planszą.

Na obecnym etapie aplikacja nie ma jeszcze runtime. Ten dokument definiuje standard, do którego będziemy budować kolejne moduły.

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

W drugim terminalu, gdy powstanie runtime:

```bash
python -m dnd_board_game.runtime --board-backend simulator --board-url http://127.0.0.1:5000
```

Runtime jeszcze nie istnieje. Pierwszy runtime powinien być prosty i debugowy, nawet jeśli później zastąpi go UI.

### 3. Tryb Hardware

Służy do testów na fizycznej planszy.

Docelowy model:

```bash
python -m dnd_board_game.runtime --board-backend hardware
```

Opcjonalnie:

```bash
python -m dnd_board_game.runtime --board-backend hardware --board-serial-port /dev/ttyUSB0 --wled-url http://192.168.0.50
```

Tryb hardware powinien być używany dopiero po przejściu testów jednostkowych i testów w symulatorze.

## Minimalny Runtime Debugowy

Pierwszy runtime nie musi być pełnym UI.

Wystarczy terminalowy lub bardzo prosty webowy tryb debugowy, który pozwoli:

- załadować testową planszę,
- ustawić jednego bohatera i jednego potwora,
- wskazać aktywnego aktora,
- pokazać zasięg ruchu LED-ami,
- wybrać pole docelowe,
- pokazać ścieżkę,
- wykonać prosty atak,
- wpisać ręczny wynik rzutu,
- zapisać metadane sesji.

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

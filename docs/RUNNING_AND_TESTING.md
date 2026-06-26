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

## Runtime Debugowy Setupu I Inicjatywy

Scenariusz setupu i inicjatywy można uruchomić bez planszy:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_initiative_setup --board-backend none --session-id initiative_demo
```

W symulatorze:

```bash
python -m board.simulator.app
```

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_initiative_setup --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --session-id initiative_simulator_demo
```

Domyślnie każdy krok LED zostaje widoczny przez `1.5` sekundy. Przy testach manualnych można wymusić potwierdzanie Enterem:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_initiative_setup --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --session-id initiative_simulator_demo
```

Runtime pokazuje:

- start walki,
- setup bohaterów, jawnych przeciwników i jawnych elementów otoczenia,
- zsynchronizowane LED-y dla aktualnego komunikatu,
- wywołanie bohaterów do inicjatywy,
- automatyczny rzut inicjatywy przeciwnika,
- ustaloną kolejność inicjatywy,
- aktywnego aktora pierwszej tury.

Argumenty przydatne do testów:

- `--hero-roll 12`
- `--rogue-roll 8`
- `--enemy-seed 7`
- `--step-delay 1.5`
- `--wait-for-enter`

## Runtime Debugowy Mini-Combatu

Pierwszy mini-combat można uruchomić bez planszy:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat --board-backend none --target-id goblin --hero-attack-roll 14 --hero-damage 6 --hero-damage-type slashing --session-id mini_combat_demo
```

W symulatorze:

```bash
python -m board.simulator.app
```

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --hero-attack-roll 14 --hero-damage 6 --hero-damage-type slashing --session-id mini_combat_simulator_demo
```

Runtime pokazuje:

- wybór akcji `Atak`,
- legalne cele ataku na niebiesko,
- wybrany cel na niebiesko,
- komunikat z modyfikatorami attack roll,
- wynik ataku LED-em,
- obrażenia i zmianę HP przy trafieniu,
- eventy `attack_declared`, `attack_resolved` i `damage_applied`.

Przy backendzie `simulator` albo `hardware` runtime próbuje wybrać cel przez kliknięcie pola. Jeśli skan nie zwróci pola w czasie `--scan-timeout`, używa fallbacku `--target-id`.

W symulatorze kliknięcie celu działa tylko w trybie `Plansza (klikanie wywołuje scan_board)`. Tryb `Przesuwanie figurek` nie wysyła kliknięć do runtime.

Przydatne argumenty:

- `--target-id goblin`
- `--target-position 1,0`
- `--scan-timeout 30`

## Runtime Debugowy Pętli Mini-Combatu

Pętlę walki 1v1 można uruchomić bez planszy:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/goblin_ambush.json --board-backend none --hero-attack-roll 14 --hero-damage 6 --hero-damage-type slashing --enemy-seed 7 --max-rounds 3 --session-id mini_combat_loop_demo
```

W symulatorze:

```bash
python -m board.simulator.app
```

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/goblin_ambush.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --scan-timeout 30 --hero-attack-roll 14 --hero-damage 6 --hero-damage-type slashing --enemy-seed 7 --max-rounds 3 --session-id mini_combat_loop_simulator_demo
```

Runtime pokazuje:

- kolejne tury bohatera i goblina,
- dane aktorów, pozycji i ataków z `content/scenarios/goblin_ambush.json`,
- zużycie akcji w turze,
- automatyczny atak przeciwnika,
- zmianę HP po trafieniach,
- zakończenie walki po pokonaniu jednej strony albo kontrolowane zatrzymanie po `--max-rounds`,
- eventy `turn_started`, `action_used`, `turn_finished`, `enemy_action_selected`, `combat_finished` albo `combat_stopped`.

Przydatne argumenty:

- `--enemy-seed 7`
- `--max-rounds 3`
- `--wait-for-enter`
- `--scenario content/scenarios/goblin_ambush.json`

Wariant multi-actor bez planszy:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/multi_actor_skirmish.json --board-backend none --ally-attack-roll hero=14 --ally-attack-roll rogue=13 --ally-damage hero=6 --ally-damage rogue=5 --enemy-seed 7 --max-rounds 5 --session-id multi_actor_demo --step-delay 0
```

Wariant multi-actor w symulatorze:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/multi_actor_skirmish.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --scan-timeout 30 --enemy-seed 7 --max-rounds 5 --session-id multi_actor_simulator_demo
```

W multi-actor runtime dodatkowo obsługuje:

- `--target-id-by-actor hero=goblin_a`
- `--ally-attack-roll rogue=13`
- `--ally-damage rogue=5`

Wariant board-first ze skryptem ruchu bez planszy:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/movement_skirmish.json --board-backend none --ally-turn-script hero=move:1,0,attack:goblin_a,move:0,1,end --hero-attack-roll 14 --hero-damage 6 --enemy-seed 7 --max-rounds 5 --session-id board_first_turn_demo --step-delay 0
```

Wariant board-first w symulatorze:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/movement_skirmish.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --scan-timeout 30 --enemy-seed 7 --max-rounds 5 --session-id board_first_turn_simulator_demo
```

Board-first flow:

- biały LED wskazuje aktywnego aktora,
- przygaszony niebieski/cyan pokazuje legalne pola ruchu,
- mocny niebieski pokazuje legalne cele ataku,
- pierwsze kliknięcie pola pokazuje podgląd ruchu albo ataku,
- drugie kliknięcie tego samego pola potwierdza,
- kliknięcie innego pola przed potwierdzeniem zmienia podgląd,
- po ataku można jeszcze wykorzystać pozostały ruch.

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

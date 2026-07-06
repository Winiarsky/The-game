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
- kliknięcie pola aktywnego aktora pokazuje opcję zakończenia tury,
- drugie kliknięcie pola aktywnego aktora kończy turę i niewykorzystany ruch przepada,
- po ataku można jeszcze wykorzystać pozostały ruch.

Wariant pierwszej grywalnej sceny bez planszy:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/first_playable_scene.json --board-backend none --initiative-mode rolled --ally-initiative-roll hero=14 --ally-initiative-roll rogue=10 --ally-turn-script hero=move:1,0,interact:ancient_crate,end --ally-check-roll hero=13 --enemy-seed 7 --max-rounds 8 --session-id first_scene_demo --step-delay 0
```

Wariant pierwszej grywalnej sceny w symulatorze:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/first_playable_scene.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --scan-timeout 30 --initiative-mode rolled --enemy-seed 7 --max-rounds 8 --session-id first_scene_simulator_demo
```

Pierwsza scena pokazuje:

- setup pól startowych bohaterów potwierdzany kliknięciem w podświetlone pole,
- krokowy setup jawnych przeciwników i elementów sceny w paczkach do 5 pól,
- wywołanie bohaterów do rzutów inicjatywy po kolei,
- automatyczny rzut inicjatywy przeciwników,
- ustalenie kolejności inicjatywy przed pierwszą turą,
- ruch przeciwnika z czerwoną ścieżką, pomarańczowym polem docelowym i potwierdzeniem kliknięciem docelowego pola,
- cel sceny,
- jawny obiekt interaktywny,
- opcję interakcji z opisem,
- test cechy po potwierdzeniu interakcji,
- ustawienie flagi sceny po sukcesie albo porażce,
- przeciwników poza zasięgiem jako przygaszony czerwony/różowy,
- zakończenie sceny po spełnieniu objective zależnego od flagi.

Do regresji można uruchomić starą deterministyczną kolejność tur przez `--initiative-mode fixed`.

## Demo Eksploracji

Bez planszy:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_exploration_scene --scenario content/scenarios/abandoned_watchtower.json --board-backend none --gm-classifier gemini --interactive-freeform --freeform-retries 4 --gm-accept ask --session-id abandoned_watchtower_demo --max-steps 6
```

Deterministyczny smoke test LLM bez wywołania zewnętrznego API:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_exploration_scene --scenario content/scenarios/abandoned_watchtower.json --board-backend none --gm-dry-run --freeform-action "Próbujemy wejść górą przez bramę, używając liny z hakiem." --session-id abandoned_watchtower_dry_run --max-steps 1
```

W symulatorze:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_exploration_scene --scenario content/scenarios/abandoned_watchtower.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --scan-timeout 30 --session-id abandoned_watchtower_simulator_demo
```

LLM GM classifier przez Groq albo Gemini:

```bash
source .env
```

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_exploration_scene --scenario content/scenarios/abandoned_watchtower.json --board-backend none --gm-classifier groq --gm-accept yes --freeform-action "Próbujemy wejść górą przez bramę, używając liny z hakiem." --challenge-roll gm_generated=14 --session-id gm_classifier_demo --max-steps 2
```

Wariant Gemini jest domyślny dla `--freeform-action` i `--interactive-freeform`; używa `GEMINI_API_KEY` i opcjonalnie `GEMINI_MODEL` z `.env`:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_exploration_scene --scenario content/scenarios/abandoned_watchtower.json --board-backend none --gm-accept yes --freeform-action "Próbujemy wejść górą przez bramę, używając liny z hakiem." --challenge-roll gm_generated=14 --session-id gm_classifier_gemini_demo --max-steps 2
```

Dry-run bez rzutu i bez zmiany stanu:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_exploration_scene --scenario content/scenarios/abandoned_watchtower.json --board-backend none --gm-dry-run --freeform-action "Chcemy zrobić dźwignię z deski i kamienia, żeby podważyć mechanizm bramy." --session-id gm_classifier_dry_run --max-steps 2
```

Interaktywny retry po odrzuceniu:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_exploration_scene --scenario content/scenarios/abandoned_watchtower.json --board-backend none --interactive-freeform --freeform-retries 3 --session-id gm_context_retries_demo --max-steps 2
```

Lokalny web UI do wygodniejszego testowania freeform eksploracji:

```bash
source .env
```

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.exploration_ui --scenario content/scenarios/abandoned_watchtower.json --gm-classifier gemini --port 5200
```

Z symulatorem planszy od razu podłączonym do UI:

```bash
python -m board.simulator.app
```

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.exploration_ui --scenario content/scenarios/abandoned_watchtower.json --gm-classifier gemini --board-backend simulator --board-url http://127.0.0.1:5000 --port 5200
```

Potem otwórz:

```text
http://127.0.0.1:5200
```

UI działa jako prosty lokalny runtime testowy:

- pokazuje aktualną lokację, cel, wyzwanie, progress, hałas, komplikacje i zasoby drużyny,
- pozwala wpisać deklarację freeform,
- pokazuje interpretację MG i preview mechaniczne przed rzutem,
- obsługuje decyzje `+` / `-` / `?` / reinterpretację jako przyciski,
- po akceptacji prosi o fizyczne wyniki kości i rozstrzyga test przez deterministic engine,
- pokazuje `Stan sceny` jako czytelne wpisy zamiast surowych flag,
- po spełnieniu `encounter_triggers` z contentu pokazuje panel `Zaczyna się encounter` z powodem i scenariuszem walki,
- prowadzi krokowy setup encountera przed walką: start walki, bohaterowie, przeciwnicy i jawne elementy sceny,
- setup encountera pokazuje aktualną grupę do rozstawienia, kolor i pola z contentu; po potwierdzeniu ostatniego kroku pokazuje komendę do runtime'u walki,
- po setupie prowadzi inicjatywę: bohaterowie wpisują naturalne wyniki d20, przeciwnicy rzucają automatycznie,
- po ustaleniu inicjatywy tworzy początkowy `CombatState` i pokazuje rundę, aktywnego aktora, kolejność oraz HP/AC uczestników,
- ma panel `Plansza` z przełącznikiem `brak/symulator/hardware`,
- tryb `hardware` używa tego samego `board/config.json` i `board.Connection`, z którego korzystała aplikacja legacy,
- po podłączeniu planszy synchronizuje LED-y z aktualnym krokiem: dostępne lokacje, setup encountera, inicjatywa i aktywny aktor walki,
- przycisk `Czekaj na kliknięcie` czyta kliknięcie z `scan_board` i wykonuje właściwy krok, np. przejście do lokacji albo potwierdzenie setupu,
- zapisuje stan tylko w pamięci procesu; przycisk reset ładuje scenariusz od nowa.

Debug bez przechodzenia mapy, od razu na punkcie NPC:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.exploration_ui --scenario content/scenarios/abandoned_watchtower.json --gm-classifier gemini --debug-point wounded_scout --port 5200
```

Pierwsza mini-scena wioski w symulatorze:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_exploration_scene --scenario content/scenarios/village_square_mvp.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --scan-timeout 30 --session-id village_square_demo
```

Tryb eksploracji:

- nie używa inicjatywy ani tur walki,
- używa wspólnego pionka drużyny,
- pokazuje dostępne lokacje przez punkty główne bez dodatkowego potwierdzania setupu stref,
- jawne elementy fizyczne z `requires_setup` są rozstawiane osobno i potwierdzane kliknięciem,
- proste opcje informacyjne mogą ustawiać flagi sceny i kończyć objective, np. rozmowa z sołtysem w `village_square_mvp`,
- domyślnie świecą tylko główne punkty dostępnych lokacji,
- kliknięcie aktualnej strefy pokazuje kolorowe menu opcji na polach wokół punktu głównego,
- opcja `Rozejrzyj się po okolicy` dopiero wtedy podświetla całą strefę i pozwala klikać kafle,
- kliknięcie innej strefy pyta o przejście,
- `Zbadaj obszar` wykonuje drużynowy test i bierze najwyższy wynik.
- LLM classifier jest opcjonalny; w trybie freeform domyślnie używa Gemini, a `--gm-classifier groq|gemini|none` pozwala wymusić providera. Wymaga odpowiednio `GROQ_API_KEY` albo `GEMINI_API_KEY` w środowisku.
- LLM działa w dwóch krokach: analyzer deklaracji sprawdza zgodność ze światem/sceną, a classifier dopiero potem proponuje mechanikę testu.
- Odpowiedź LLM przechodzi przez Pydantic, walidację stanu gry i akceptację interpretacji przez `--gm-accept ask|yes|no`.
- W trybie `--gm-accept ask` decyzje terminalowe są jawne: `+` akceptuje, `-` odrzuca i prosi o korektę, `?` pokazuje wyjaśnienie mechaniczne bez zmiany stanu, a `r` prosi LLM o reinterpretację tej samej deklaracji.
- Payload LLM zawiera warstwy kontekstu: scenariusz, lokacja, challenge, dynamiczny stan gry i historię wcześniejszych prób.
- Payload LLM zawiera też `llm_policy` aktywnego challenge, czyli lokalnie dozwolone tagi, komplikacje, consequence types, zakres ST i zakres postępu.
- Ogólne słowniki LLM są w `content/llm/`; szczegóły konkretnej przeszkody są w scenariuszu, np. w `exploration.challenges[].llm_context` i `llm_policy`.
- Jeśli `llm_policy` zawiera `dc_policy`, LLM wybiera `difficulty_tier`, podaje `difficulty_reason` i musi ustawić `dc` dokładnie z tieru z contentu. Nie ustala ST swobodnie.
- Dla `abandoned_watchtower` brama ma content-driven tiery: `easy=12`, `medium=15`, `hard=18`.
- Analyzer LLM zwraca `action_flow`: `challenge_attempt`, `preparation`, `combined`, `player_question`, `unsupported` albo `needs_clarification`.
- Zasoby są twardo walidowane: deklarowany przedmiot musi być w `party_resources` albo w materiałach sceny. Inaczej runtime zapisuje `declaration_fact_rejected` i nie wykonuje rzutu.
- Przygotowanie zapisuje krótkotrwały efekt `modifier`, `reduce_negative_effect`, `advantage`, `disadvantage`, `effect_boost`, `grant_resource` albo `unlock_option`; działa tylko przy następnej pasującej próbie i po użyciu wygasa.
- `grant_resource` i `unlock_option` działają tylko na id istniejące w contentcie i dozwolone przez `llm_policy`.
- Przed akceptacją propozycji runtime pokazuje preview konsekwencji dla critical success / success / failure / critical failure. W trybie `--gm-accept ask` komenda `?` pokazuje to preview ponownie razem z notatkami MG.
- Payload LLM zawiera lokalny `declaration_thread`, jeśli gracz wcześniej odrzucił deklarację, zadał pytanie albo doprecyzował podejście w ramach tego samego promptu freeform.
- Po odrzuceniu deklaracji tryb `--interactive-freeform` może poprosić o kolejną próbę bez restartowania runtime.
- Błędy Groq/Gemini `429` i chwilowe `5xx` są ponawiane automatycznie z krótkim backoffem; `--freeform-retries` nadal oznacza liczbę prób deklaracji gracza, nie liczbę ponowień HTTP.
- Jeśli analyzer prosi o doprecyzowanie i podaje znormalizowaną intencję, odpowiedź `tak` potwierdza tę interpretację bez wysyłania samego `tak` jako nowej deklaracji do LLM.
- Decyzje terminalowe nie są deklaracjami fabularnymi: `+`, `-`, `?` i `r` sterują wyłącznie interpretacją LLM.
- Po `-` następny tekst gracza trafia do lokalnego `declaration_thread` jako korekta.
- Po `r` runtime nie pyta o nową deklarację, tylko odpala classifier ponownie z kontekstem poprzedniej odrzuconej interpretacji.

Manualne prompty do `--freeform-action`:

- `Próbujemy wejść górą przez bramę, używając liny z hakiem.`
- `Chcemy znaleźć deskę i kamień, zrobić prostą dźwignię i podważyć mechanizm bramy.`
- `Wojownik próbuje wyważyć bramę barkiem, zanim ktoś nas zauważy.`
- `Rozglądamy się wzdłuż muru i szukamy cichego bocznego przejścia.`
- `Używamy liny, żeby podważyć metalowy mechanizm bramy.`
- `Chcemy zdjąć kilka spróchniałych desek po cichu i zrobić przejście tylko dla jednej osoby.`
- `Chcemy teleportować się za bramę czarem, którego nikt z drużyny nie zna.`
- `Wsiadam na linę i przelatuję nad bramą.`
- `Wyciągam słoik z kwasem i polewam zawiasy.`
- `Owijamy linę wokół górnej belki, żeby łatwiej wejść później.`
- `Potem wchodzimy górą po bramie.`
- `Działamy powoli i cicho, zanim podważymy mechanizm.`
- `Ścinamy pobliskie wielkie drzewo i robimy taran.`
- `Używamy starej piły, zanim ją znaleźliśmy.`
- `Sypiemy piasek w mechanizm bramy, żeby ją odblokować.`
- `Klinujemy bramę drewnianym klinem i próbujemy cicho podważyć mechanizm.`
- `Przestrzeliwujemy zamek pistoletem laserowym.`
- `Wyważamy bramę mocnym dmuchnięciem.`
- `Jak przejść bez hałasu?`

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

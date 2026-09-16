# Tworzenie Scenariusza

Przy projektowaniu spotkań przygotuj warianty dla 3–6 graczy według
[strategii skalowania](PARTY_SCALING.md), zaczynając od czteroosobowej drużyny.
Podane budżety są wartościami do ogrania, nie zamkniętym balansem.

## 1. Utwórz paczkę

```bash
PYTHONPATH=src python scripts/scaffold_scenario.py popiol_i_stal "Popiół i stal"
```

Generator tworzy komponentowy, ładowalny scenariusz w
`content/scenarios/popiol_i_stal/`: nagłówek, aktora testowego, lokację startową,
puste katalogi mechanik, katalog grafik i manifest map. Istniejąca paczka nigdy
nie jest nadpisywana.

## 2. Pisz content

- `scenario.json` spina części oraz definiuje planszę 20 × 30.
- `exploration/zones.json` definiuje lokacje, sąsiedztwo i pola interakcji.
- `points.json`, `challenges.json` oraz `flows.json` tworzą właściwy przebieg.
- Interakcje projektuj według
  [SCENARIO_INTERACTION_FORM.md](SCENARIO_INTERACTION_FORM.md).
- Grafiki wskazane przez `image` są względne wobec katalogu paczki.
- Pliki `paper_map` są względne wobec głównego katalogu `assets/`.

## 3. Przygotuj mapy do druku

Uzupełnij `print_maps.json`, np.:

```json
{
  "schema": "dnd_board_game.print_map_manifest",
  "schema_version": 1,
  "output_root": "assets/print_maps/popiol_i_stal",
  "maps": [
    {
      "id": "village_overview",
      "title": "Wioska",
      "source": "assets/village_overview.png"
    }
  ]
}
```

Następnie:

```bash
python scripts/generate_print_maps.py \
  --manifest content/scenarios/popiol_i_stal/print_maps.json
```

Generator tworzy czarno-biały PNG 50 × 75 cm, PDF pełnowymiarowy oraz
wielostronicowy PDF A4 z zakładkami.

## 4. Uruchom bramkę jakości

```bash
PYTHONPATH=src python scripts/audit_content.py content
```

Błąd blokuje playtest. Oczekiwany jest tylko warning licencji lokalnego
`project_original`. Audyt obejmuje schemat, referencje, mechanikę, grafiki,
papierowe mapy oraz pola interakcji.

## 5. Playtest

Scenariusz eksploracyjny pojawia się automatycznie w menu `Nowa gra`. Przed
publikacją wykonaj test bez hardware oraz
[checklistę UI-5](PLAYER_UI_DESIGN.md#ui-5--walidacja-przy-stole) na prawdziwej
planszy.


## Lokalna paczka Misji 0

`content/scenarios/misja_0_dzwon/README.md` opisuje działający przykład narracyjnego
samouczka 3–6 osób. Teksty i media są lokalne oraz odczytywane bez cache;
mechanika konfrontacji jest utrwalana przy rozpoczęciu. Przejścia wymagające
skutków gry obsługuje `ui/mission_zero.py`, zasady pozostają we wspólnych silnikach.
Po edycji map ponów `scripts/build_mission_zero_prints.py`; do porównań liczbowych
użyj `scripts/evaluate_mission_zero.py`. To nie jest jeszcze uniwersalny edytor
przepływów dowolnej kampanii.

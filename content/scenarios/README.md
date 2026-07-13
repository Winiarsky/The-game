# Scenarios

Scenariusze opisują konkretne encountery uruchamiane przez runtime.

Scenariusz może być zapisany jako jeden plik JSON albo jako folder z manifestem.

## Pojedynczy Plik

Minimalny format MVP dla pojedynczego pliku:

- `id`: techniczny identyfikator scenariusza,
- `name`: polska nazwa widoczna w runtime,
- `board`: wymiary planszy, obecnie `cols` i `rows`,
- `actors`: bohaterowie, przeciwnicy i NPC biorący udział w scenie,
- `environment`: jawne albo ukryte elementy otoczenia.

Aktor może zawierać pełne statystyki inline albo użyć `source_ref`, np. `goblin`, aby doładować bazowe dane z `content/monsters/goblin.json`.

Przykład:

```json
{
  "id": "goblin_ambush",
  "name": "Zasadzka goblina",
  "board": {"cols": 20, "rows": 30},
  "actors": [],
  "environment": []
}
```

## Folder Scenariusza

Dla większych scenariuszy preferowany jest folder:

```text
content/scenarios/abandoned_watchtower/
  scenario.json
  actors.json
  objectives.json
  llm_context.json
  exploration/
    zones.json
    points.json
    challenges.json
    resources.json
    initial_resources.json
    party_start_zone.json
```

`scenario.json` trzyma metadane i mapę części:

```json
{
  "id": "abandoned_watchtower",
  "name": "Opuszczona strażnica",
  "scene_mode": "exploration",
  "board": {"cols": 20, "rows": 30},
  "parts": {
    "actors": "actors.json",
    "objectives": "objectives.json",
    "llm_context": "llm_context.json",
    "exploration": {
      "zones": "exploration/zones.json",
      "points": "exploration/points.json",
      "challenges": "exploration/challenges.json",
      "resources": "exploration/resources.json",
      "initial_resources": "exploration/initial_resources.json",
      "party_start_zone": "exploration/party_start_zone.json"
    }
  }
}
```

Każdy plik części może zawierać samą wartość albo obiekt nazwany polem, np. `{"actors": [...]}`. Drugi wariant jest czytelniejszy i obecnie zalecany.

Zasób eksploracji może być wielokrotnego użytku albo jednorazowy:

```json
{
  "id": "wedge",
  "label": "Drewniany klin",
  "bonus_tags": ["lever", "quiet"],
  "mitigates_noise": 1,
  "consume_on_use": true
}
```

`consume_on_use` domyślnie ma wartość `false`. Zasób jednorazowy znika dopiero po wykonaniu zaakceptowanego rzutu eksploracyjnego.

Aktor przygotowujący czary może deklarować generyczny profil:

```json
{
  "spell_preparation": {
    "source_label": "lista czarów kapłana",
    "preparation_limit": 2,
    "available_spell_ids": ["radiant_line", "healing_word", "bless_attack_bonus"],
    "default_prepared_spell_ids": ["healing_word", "bless_attack_bonus"],
    "always_prepared_spell_ids": []
  }
}
```

Identyfikatory muszą wskazywać źródła czarów poziomu 1+ tego aktora. Cantripy nie należą do profilu. Przed setupem scenariusza gracz potwierdza dokładnie `preparation_limit` pozycji; `always_prepared_spell_ids` nie zajmują limitu.

Stary płaski plik może zostać aliasem:

```json
{
  "$include": "abandoned_watchtower/scenario.json"
}
```

Dzięki temu stare komendy runtime nadal działają, a edycja większego scenariusza odbywa się w mniejszych plikach.

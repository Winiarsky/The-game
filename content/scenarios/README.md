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

Opcjonalne `size` przyjmuje `tiny`, `small`, `medium`, `large`, `huge` albo
`gargantuan`; brak pola oznacza `medium`. Rozmiar wpływa obecnie na legalność Grapple
i Shove, ale każda figurka nadal zajmuje jedno pole.

Opcjonalne listy `damage_resistances`, `damage_immunities` i
`damage_vulnerabilities` przyjmują identyfikatory typów obrażeń, np. `fire`,
`slashing` albo `poison`. Brak pól oznacza brak specjalnej relacji z obrażeniami.

Aktor może deklarować data-driven `auras`. Pierwszy obsługiwany efekt to
`saving_throw_bonus`; `target` przyjmuje `self_and_allies`, `allies`, `enemies`
albo `all_creatures`. Zasięg jest przeliczany po każdym ruchu, a identyczne `id`
aur nie sumują się:

```json
"auras": [{
  "id": "protective_presence",
  "label": "Ochronna obecność",
  "radius_feet": 10,
  "target": "self_and_allies",
  "effect_kind": "saving_throw_bonus",
  "value": 1
}]
```

Aktor może również deklarować `triggers`. Schemat przyjmuje zdarzenia
`attack_hit`, `damage_taken`, `actor_moved`, `turn_start`, `turn_end`,
`short_rest_completed`, `long_rest_completed` i `encounter_ended`. Pierwszym
obsługiwanym skutkiem jest `grant_temp_hp`:

```json
"triggers": [{
  "id": "runic_guard",
  "label": "Runiczna osłona",
  "event_type": "turn_start",
  "effect_kind": "grant_temp_hp",
  "value": 2
}]
```

Definicja nie oznacza automatycznie, że każde zdarzenie ma już emiter w runtime.
Aktualny vertical slice wykonuje triggery `turn_start` i `turn_end`.

Źródło ataku może użyć `save_ability`, `save_dc` i
`save_damage_on_success` (`none` albo `half`). Takie źródło nie wykonuje attack rolla:
cel wykonuje saving throw, a wynik modyfikuje obrażenia przed profilem odporności.

Każde nowe źródło ataku inline deklaruje `attack_kind`. Atak `melee` podaje również
`reach_feet` jako dodatnią wielokrotność 5 feet (zwykle 5), a atak `ranged` używa
`range_feet` i nie deklaruje reach. Loader zachowuje starsze wnioskowanie z zasięgu
jedynie dla kompatybilności istniejących scenariuszy.

Czar obszarowy deklaruje `area.shape` jako `radius`, `line` albo `cone`. Wymiary są
dodatnimi wielokrotnościami 5 feet: radius używa `radius_feet`, line i cone używają
`length_feet`, a line dodatkowo `width_feet`. Nowy content powinien jawnie podawać
`target_mode`: `all_creatures`, `enemies` albo `allies`; brak pola zachowuje
kompatybilne `all_creatures` z pełnym friendly fire.

```json
"area": {
  "shape": "line",
  "length_feet": 30,
  "width_feet": 5,
  "target_mode": "all_creatures"
}
```

Akcje w `combat_actions` oraz wpisy w `environment[].interactions` mogą deklarować
`action_cost`: `action`, `bonus_action`, `reaction`, `object_interaction` albo
`free`. Brak pola oznacza `action`. `object_interaction` zużywa darmową interakcję
aktora, a jeżeli została już wykorzystana — dostępną akcję główną. UI pokazuje ten
koszt przed potwierdzeniem.

Opcja challenge może też zawierać listę `hazards`. Zagrożenie jest uruchamiane przez
`failure` albo `critical_failure`, zatrzymuje interakcję na fizyczny saving throw i
dopiero po nim stosuje obrażenia:

```json
{
  "hazards": [{
    "id": "fall",
    "label": "Upadek",
    "trigger": "critical_failure",
    "saving_throw": {
      "ability": "dexterity",
      "dc": 12,
      "damage_on_success": "half"
    },
    "damage": {"dice": "1d6", "damage_type": "bludgeoning"},
    "success_message": "Kontrolowany upadek.",
    "failure_message": "Twarde lądowanie."
  }]
}
```

W jednej opcji może być najwyżej jedno zagrożenie dla danego triggera.

Aktor deklaruje biegłości przez jeden profil:

```json
{
  "proficiency_bonus": 2,
  "proficiencies": {
    "saving_throws": ["dexterity", "intelligence"],
    "skills": ["stealth", "perception"],
    "expertise": ["stealth"],
    "weapons": ["crossbow", "dagger"],
    "armor": ["light"],
    "tools": ["thieves_tools"]
  }
}
```

`expertise` wymaga wpisania tego samego skilla w `skills`. Biegłość broni wskazuje
stabilne id itemu albo id naturalnego źródła ataku. Loader nadal odczytuje starsze
`skill_proficiencies` i `skill_expertise`, ale nowe dane powinny używać profilu.

Test sceny może wskazać `tool` obok `ability` i opcjonalnego `skill`:

```json
{
  "ability_check": {
    "ability": "dexterity",
    "tool": "thieves_tools",
    "dc": 15
  }
}
```

`tool` jest stabilnym id wymaganym do sprawdzenia profilu aktora. Samo posiadanie
przedmiotu i biegłość w narzędziu są osobnymi pojęciami; wymóg przedmiotu należy
nadal opisać w wymaganiach opcji. Jeśli wpisano jednocześnie `skill` i `tool`,
proficiency nie jest doliczane dwa razy.

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
    observations.json
    traps.json
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
      "observations": "exploration/observations.json",
      "traps": "exploration/traps.json",
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

Aktor może posiadać Hit Dice i generyczne zasoby odpoczynku:

```json
{
  "hit_dice": {"d8": 2},
  "resource_pools": [
    {
      "id": "focus",
      "label": "Skupienie",
      "current": 0,
      "maximum": 2,
      "recovery": "short_rest"
    }
  ]
}
```

Lokacja eksploracyjna udostępnia short rest wyłącznie przez jawną politykę:

```json
{
  "short_rest": {
    "safety": "contested",
    "duration_minutes": 60,
    "max_completions": 1,
    "risk_summary": "Postój zwiększy hałas i może przyciągnąć patrol.",
    "completion_effects": [
      {
        "type": "add_noise",
        "parameters": {"challenge_id": "closed_gate", "value": 2}
      }
    ]
  }
}
```

Brak `short_rest` oznacza, że lokacja nie pozwala odpocząć. `max_completions: 0` oznacza brak contentowego limitu. Long rest nie ma osobnego przycisku scenariusza: jest automatycznie wykonywany przed etapem przygotowania czarów.

Stary płaski plik może zostać aliasem:

```json
{
  "$include": "abandoned_watchtower/scenario.json"
}
```

Dzięki temu stare komendy runtime nadal działają, a edycja większego scenariusza odbywa się w mniejszych plikach.

Pułapka eksploracyjna łączy wykrycie przez istniejącą obserwację z własnym stanem
oraz hazardem uruchamianym po nieudanej interakcji albo ukończeniu wskazanego challenge'a:

```json
{
  "id": "alarm_wire",
  "zone_id": "gate",
  "name": "Linka alarmowa",
  "revealed_description": "Cienka linka połączona z blaszkami.",
  "detection_observation_id": "search_gate_traps",
  "activation_challenge_id": "closed_gate",
  "required_item_id": "thieves_tools",
  "disarm_check": {"ability": "dexterity", "tool": "thieves_tools", "dc": 12},
  "disarm_intent_examples": ["rozbrajam linkę"],
  "bypass_intent_examples": ["omijam linkę"],
  "trigger_intent_examples": ["celowo uruchamiam linkę"],
  "hazard": {
    "id": "alarm_wire_trigger",
    "label": "Alarm",
    "saving_throw": {"ability": "dexterity", "dc": 12},
    "damage": {"fixed": 0, "damage_type": "bludgeoning"},
    "failure_effects": [
      {"type": "add_noise", "parameters": {"challenge_id": "closed_gate", "value": 3}}
    ]
  }
}
```

Obserwacja wykrywająca musi zawierać efekt `reveal_trap` z ID tej pułapki.
Runtime przechowuje stany `hidden`, `revealed`, `disarmed`, `bypassed` i `triggered`.

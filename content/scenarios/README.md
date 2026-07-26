# Scenarios

Scenariusze opisują konkretne encountery uruchamiane przez runtime.

Triggery eksploracyjne mogą przypisać osobne skutki do sposobu zakończenia
encountera. `outcome_on_victory` i `outcome_on_defeat` obsługują rozstrzygnięcie
przez zdolną do walki stronę, a opcjonalne `outcome_on_objective`,
`outcome_on_retreat` i `outcome_on_surrender` pozwalają nadać inne konsekwencje
wykonaniu celu, wycofaniu drużyny i kapitulacji. Każdy outcome używa tego samego
formatu `title`, `body`, `next_instruction` i `effects`.

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

Obrażenia źródła ataku mają kompatybilny stary format pojedynczego składnika:

```json
"damage": {"dice": "1d8", "modifier": 3, "damage_type": "slashing"}
```

Nowy format obsługuje dowolne `NdM` oraz wiele niezależnie typowanych składników:

```json
"damage": {
  "components": [
    {"id": "blade", "label": "Ostrze", "dice": "2d6", "modifier": 3, "damage_type": "slashing"},
    {"id": "flame", "label": "Płomień", "dice": "1d4", "damage_type": "fire"}
  ]
}
```

Krytyk podwaja liczbę kości każdego składnika, ale nie jego stały modyfikator.
Gracz wpisuje osobny końcowy wynik każdego składnika, a resistance, immunity i
vulnerability są stosowane według typu. Id składnika jest stabilnym kontraktem UI
i zapisu zdarzenia.

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
      "recovery": "short_rest",
      "recharge": null
    }
  ]
}
```

Atak może zużywać taki zasób przez `resource_pool_id` i opcjonalny
`resource_cost` (domyślnie `1`). Potworowe `Recharge 5–6` zapisujemy na puli:

```json
{
  "id": "breath_charge",
  "label": "Oddech",
  "maximum": 1,
  "recovery": "never",
  "recharge": {"die_sides": 6, "minimum_roll": 5}
}
```

Zużyta pula z `recharge` wykonuje rzut na początku tury właściciela i odnawia
się do maksimum po osiągnięciu progu. Atak wskazujący nieistniejącą pulę jest
odrzucany podczas ładowania scenariusza.

## Cechy aktorów

Aktor może składać istniejące mechaniki przez `feature_refs`:

```json
{"feature_refs": ["goblin_frenzied_lunge"]}
```

Referencja wskazuje plik `content/features/<id>.json`. Schemat v1 cechy ma postać:

```json
{
  "schema_version": 1,
  "id": "goblin_frenzied_lunge",
  "label": "Szarżujący wypad",
  "description": "Specjalny atak potwora.",
  "source_kind": "monster",
  "source_ref": "goblin",
  "grants": {
    "resource_pools": [],
    "attacks": [],
    "healing_sources": [],
    "combat_actions": [],
    "triggers": [],
    "auras": []
  }
}
```

`source_kind` przyjmuje `monster`, `item`, `race`, `species`, `background`, `class`,
`subclass`, `feat` albo `scenario`. Cecha musi przyznawać co najmniej jeden
prymityw. Loader rozwija granty do tych samych modeli co bezpośrednie dane aktora,
odrzuca nieznane referencje i kolizje ID, a runtime zachowuje `FeatureGrant`, aby UI
i snapshot mogły pokazać pochodzenie mechaniki.

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

## Trwały stan NPC

`npc_interaction` może określić początkowy stan niezależny od tekstu narracyjnego:

```json
{
  "id": "wounded_scout",
  "initial_attitude": "indifferent",
  "initial_physical_state": "Ranny i osłabiony.",
  "initial_emotional_state": "Przestraszony.",
  "policy": {
    "intent_permissions": {
      "medical": {
        "status": "allowed",
        "state_on_success": {
          "physical_state": "Opatrzony i ustabilizowany.",
          "emotional_state": "Wdzięczny za pomoc."
        },
        "state_on_failure": {
          "emotional_state": "Zaniepokojony nieudaną próbą."
        }
      },
      "social": {
        "status": "allowed",
        "uses_social_reaction": true,
        "attempt_policy": {
          "attempt_id": "scout_build_trust",
          "max_attempts": 2,
          "retry_requires_any_flags": ["scout_stabilized"],
          "retry_locked_message": "Najpierw pokażcie, że chcecie pomóc.",
          "exhausted_message": "NPC nie zmieni już zdania tym sposobem."
        },
        "state_on_success": {"attitude": "friendly"}
      }
    }
  }
}
```

Nastawienie przyjmuje `hostile`, `indifferent` albo `friendly`. Pola pominięte w
`state_on_success`/`state_on_failure` nie zmieniają poprzedniego stanu. Runtime
automatycznie zapisuje historię zaakceptowanych interakcji, wykorzystane intencje
wymagające rzutu oraz faktycznie ujawnione `locked_information`.

`uses_social_reaction: true` oznacza prośbę rozstrzyganą tabelą reakcji D&D 5e
zależną od bieżącego nastawienia. LLM klasyfikuje `request_risk` jako
`no_risk`, `minor_risk` albo `significant_risk`, natomiast silnik wyznacza ST
0/10/20 lub odmowę. Aktualne nastawienie i warunki reakcji są jawne w UI.

Opcjonalne `attempt_policy` dotyczy wyłącznie faktycznie wykonanych rzutów.
`attempt_id` jest stabilnym kluczem licznika, `max_attempts` ustala limit, a
`retry_requires_any_flags` wymaga zmiany sytuacji przed drugą i kolejną próbą.
Zablokowana deklaracja pokazuje `retry_locked_message`; wyczerpany limit pokazuje
`exhausted_message`. Samo pytanie, podgląd mechaniki i odrzucenie interpretacji
nie zużywają próby.

Ryzykowna intencja może definiować zamknięty katalog `targets`. Każdy cel ma
stabilne `id`, opis, maksymalną ilość, opcjonalny stały test oraz dokładnie
cztery gałęzie `outcomes`: `critical_success`, `success`, `failure` i
`critical_failure`. Gałąź zawiera tekst dla gracza, deterministyczne efekty,
opcjonalną zmianę stanu NPC i identyfikatory ujawnianych informacji. LLM wybiera
wyłącznie istniejący `target_id` i `quantity`; nie może dostarczać własnych
efektów dla takiej intencji. UI pokazuje nagrodę, ryzyko i wszystkie cztery
możliwe rezultaty przed zaakceptowaniem rzutu.

Przykładowy skrót:

```json
{
  "status": "allowed_with_consequence",
  "targets": [{
    "id": "scout_reports",
    "label": "Torba z meldunkami",
    "description": "Spróbuj zabrać torbę.",
    "max_quantity": 1,
    "ability": "dexterity",
    "skill": "sleight_of_hand",
    "dc": 14,
    "outcomes": {
      "critical_success": {"message": "Niezauważona kradzież.", "effects": []},
      "success": {"message": "Zdobyto torbę.", "effects": []},
      "failure": {"message": "NPC zauważa próbę.", "effects": []},
      "critical_failure": {"message": "NPC wszczyna alarm.", "effects": []}
    }
  }]
}
```

Gałąź wyniku może dodatkowo podać `transition_id`. Definicje z
`exploration.npc_transitions` są krótkimi, deterministycznymi etapami pomiędzy
wynikiem rozmowy a dalszą sceną. Warianty są sprawdzane kolejno i mogą wymagać
flag albo wcześniej rozstrzygniętych triggerów encountera; ostatni wariant musi
być bezwarunkowym fallbackiem. Każda jawna dla gracza reakcja kończy się jednym
z rezultatów: `resume_dialogue`, `end_interaction` albo `start_encounter`.
Reakcja może stosować zwykłe efekty eksploracji i wyciszyć wskazany trigger.
`start_encounter` zawsze wskazuje istniejący `encounter_trigger_id`; definicja
przejścia nie tworzy własnej walki ani nie pozwala LLM wybrać konsekwencji.
Podczas ładowania scenariusza wszystkie efekty wiedzy NPC, outcome branches i
reakcji przejścia przechodzą ten sam walidator co propozycje LLM w runtime.
Walidowane są parametry i referencje prymitywu oraz lokalne
`allowed_effect_types`/`allowed_flags`. Błąd wskazuje pełną ścieżkę wpisu, dzięki
czemu wadliwy content nie może rozpocząć sesji.

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

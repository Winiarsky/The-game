# Scenarios

Scenariusze opisują konkretne encountery uruchamiane przez runtime.

Każdy główny plik scenariusza ma nagłówek `schema`, `schema_version`,
`ruleset_id` oraz `source_pack_ids`. Stabilne `id` używa `snake_case`; jego
zmiana wymaga migracji zapisów i referencji. Szczegółowy kontrakt, polityka
źródeł i polecenie audytu znajdują się w
`docs/CONTENT_VERSIONING_AND_SOURCES.md`.

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

`success_effects` i `failure_effects` hazardu mogą nakładać trwały poza walką
warunek `prone`, `poisoned` albo `restrained`:

```json
{
  "type": "apply_condition",
  "parameters": {
    "condition": "poisoned",
    "duration": "until_short_rest",
    "source_label": "Zatrute kolce"
  }
}
```

Dozwolone duration poza walką to `until_encounter_end`, `until_short_rest`,
`until_long_rest`, `until_scenario_end` i `permanent`. Warunek zachowuje te dane
przy wejściu do encountera i powrocie do eksploracji.

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

Aktor może deklarować zasięgi zmysłów, a strefa bazowe oświetlenie:

```json
{
  "senses": {"darkvision_feet": 60},
  "ambient_light": "darkness"
}
```

Dozwolone zmysły to `darkvision_feet`, `blindsight_feet`,
`tremorsense_feet` i `truesight_feet`; każdy zasięg jest nieujemną
wielokrotnością 5 ft. `ambient_light` przyjmuje `bright`, `dim` albo `darkness`.
Authored observation zależna od wzroku dodaje `sight_based: true` oraz dodatni
`distance_feet` będący wielokrotnością 5 ft.

Strefa może udostępnić Hide i aktywny Search:

```json
{
  "allows_hiding": true,
  "search": {
    "dc": 12,
    "ability": "wisdom",
    "skill": "perception",
    "minutes": 10,
    "reveals": ["hidden_cache"]
  }
}
```

Pułapka może być wykrywana zarówno przez wskazaną authored observation, jak i
przez wspólny Search/passive Perception:

```json
{
  "detection_observation_id": "search_gate_traps",
  "detection_dc": 15,
  "detection_distance_feet": 10,
  "passive_detection": true
}
```

Brak `detection_dc` wyłącza generyczne wykrywanie i pozostawia wyłącznie
autorską observation. Dystans musi być dodatnią wielokrotnością 5 ft.

Strefa może deklarować trwałe fixture'y drzwi, pojemników i przeszkód:

```json
{
  "id": "supply_chest",
  "name": "Skrzynia",
  "kind": "container",
  "positions": [[7, 3]],
  "condition": "closed",
  "initially_locked": true,
  "lock_dc": 12,
  "destructible": true,
  "armor_class": 15,
  "hit_points": 10,
  "damage_threshold": 3,
  "cover_bonus": 2,
  "projectile_cover_bonus": 2,
  "action_policies": [
    {
      "operation": "unlock",
      "result_condition": "closed",
      "ability": "dexterity",
      "difficulty_tier": "easy"
    },
    {
      "operation": "open",
      "allowed_conditions": ["closed"],
      "result_condition": "open",
      "ability": "strength",
      "difficulty_tier": "automatic"
    },
    {
      "operation": "loot",
      "allowed_conditions": ["open"],
      "result_condition": "open",
      "ability": "wisdom",
      "difficulty_tier": "automatic",
      "release_yield_items": true
    }
  ],
  "yield_items": []
}
```

`kind` przyjmuje `object`, `door`, `container` albo `obstacle`. Fixture z
`destructible: true` musi podać `armor_class` i dodatnie `hit_points`.
`damage_threshold` jest opcjonalny. `blocks_movement_when_closed` oraz bonusy
cover są projektowane do encountera z aktualnego stanu eksploracji. Wartość
`difficulty_tier: "automatic"` oznacza lokalną operację bez rzutu.

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

Strefa może wskazywać fizyczną papierową mapę:

```json
{
  "id": "gate",
  "name": "Brama strażnicy",
  "paper_map": {
    "id": "watchtower_overview",
    "preview_path": "print_maps/village_watchtower/png/watchtower_overview.png",
    "a4_pdf_path": "print_maps/village_watchtower/pdf/a4/watchtower_overview.pdf",
    "full_size_pdf_path": "print_maps/village_watchtower/pdf/full_size/watchtower_overview.pdf",
    "width_cm": 50,
    "height_cm": 75
  }
}
```

Ścieżki są względne wobec głównego `assets/`. Przed pierwszym setupem oraz po
przejściu do strefy używającej innej mapy UI pokazuje podgląd i linki do druku,
a rozgrywka pozostaje zatrzymana do potwierdzenia rozłożenia mapy. Strefy na tej
samej mapie nie wymagają jej ponownego rozkładania. `interaction_pad_positions`
określa pola, na których runtime pokazuje dynamiczne, kolorowe opcje powiązane
numerem i kolorem z kafelkami UI. Strefa może zadeklarować najwyżej osiem takich
pozycji. Runtime rezerwuje ostatnią na czerwone systemowe wyjście, dlatego content
może jednocześnie udostępnić najwyżej `min(7, liczba_pozycji - 1)` działań. Nadmiar
jest błędem autora, a nie listą stronicowaną ani cicho uciętą. Dopiero później uruchamiane są kroki ustawiania
NPC, elementów sceny i pasywnego wykrywania.
Standard projektu to plansza 20×30 pól, pole 2,5 cm i mapa 50×75 cm bez
nadrukowanej kratki. Kafelkowe PDF-y A4 należy drukować w skali 100%.

## Kontrakt interakcji

Opcje stref i cele wyzwań/NPC jawnie określają sposób rozstrzygnięcia:

- `resolution_mode`: `automatic` (autorski rezultat bez rzutu i LLM), `check`
  (deterministyczny test D&D), `llm_rubric` (ocena tekstu według zapisanych
  kryteriów, bez rzutu) albo `conversation` (swobodna rozmowa w granicach
  wiedzy i polityki NPC);
- `description_mode`: `none`, `optional` albo `required`;
- `default_declaration`: tekst techniczny wykonywany po kliknięciu, wymagany
  przy `description_mode: none`;
- `llm_rubric`: lista jawnych kryteriów, wymagana tylko dla `llm_rubric`.

Opis opcjonalny może uruchomić wyłącznie premie, kary lub konsekwencje
zdefiniowane w contencie (np. regułę metody dla wyważania bramy). LLM nie może
sam zmieniać ST ani tworzyć nagród. Dla prostego, oskryptowanego testu runtime
przechodzi bezpośrednio do fizycznego rzutu, bez wcześniejszej interpretacji
deklaracji przez LLM.

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
Opcjonalne pole aktora `"level": 1` przechowuje poziom postaci (1–20) używany
między innymi do skalowania obrażeń cantripów. Brak pola zachowuje poziom 1.

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
    "spell_refs": [],
    "spell_access": [],
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

Krytyczny cel rozmowy może zawierać ukryte `grounded_response`:

```json
{
  "id": "accept_quest",
  "label": "Przyjmijcie zadanie",
  "description": "Potwierdźcie decyzję drużyny.",
  "intent_ids": ["commitment"],
  "grounded_response": {
    "player_narration": "NPC uważnie słucha decyzji drużyny.",
    "npc_response": "Dobrze. Wróćcie, kiedy będziecie gotowi wyruszyć.",
    "success_message": "NPC przyjmuje zobowiązanie drużyny.",
    "variants": [
      {
        "id": "relieved",
        "player_narration": "Napięcie na twarzy NPC nieco ustępuje.",
        "npc_response": "Dobrze. Przygotujcie się i wróćcie przed wymarszem.",
        "success_message": "NPC przyjmuje decyzję drużyny."
      }
    ]
  }
}
```

Pole nie jest wystawiane w zwykłym payloadzie gracza. Dla guarded route prompt
LLM zawiera wyłącznie aktywny cel i jego permission, a walidator zastępuje
widoczne `player_narration`, `npc_response`, `success_message` i
`failure_message` wartościami autorskimi. Opcjonalne `variants` są równoważnymi
parafrazami zatwierdzonymi w contencie. Model wybiera wyłącznie ich `id`, a
walidator kopiuje kompletny wariant; brak lub obcy identyfikator wraca do tekstu
bazowego. Model nadal klasyfikuje intencję,
ryzyko i metodę, ale nie może ustanowić nowego tropu, nagrody, zakupu ani
transferu waluty samym tekstem.

`uses_social_reaction: true` oznacza prośbę rozstrzyganą tabelą reakcji D&D 5e
zależną od bieżącego nastawienia. LLM klasyfikuje `request_risk` jako
`no_risk`, `minor_risk` albo `significant_risk`, natomiast silnik wyznacza ST
0/10/20 lub odmowę. Dla celu korzystającego z tej tabeli UI każe graczowi
wybrać Persuasion, Deception albo Intimidation. Wybór trafia do walidatora i
ma pierwszeństwo przed metodą proponowaną przez LLM. `allowed_skills` może
ograniczyć listę. Aktualne nastawienie i warunki reakcji są jawne w UI.

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

Cel sceny może opcjonalnie zawierać prezentacyjne `milestones`. Każdy kamień
milowy ma etykietę, klucz flagi i opcjonalną wartość oczekiwaną (domyślnie
`true`). Nie zmienia warunku ukończenia celu; pozwala UI pokazać graczom
czytelny postęp bez ujawniania technicznych nazw flag:

```json
{
  "id": "prepare_departure",
  "name": "Przygotujcie wyprawę",
  "condition": "flag_equals",
  "flag_key": "ready_to_depart",
  "flag_value": true,
  "milestones": [
    {"label": "Zdobądźcie trop", "flag_key": "hook_found"},
    {"label": "Przyjmijcie zadanie", "flag_key": "quest_accepted"},
    {"label": "Potwierdźcie gotowość", "flag_key": "ready_to_depart"}
  ]
}
```

Scenariusz eksploracyjny może mieć jedno autorskie `exploration.continuation`.
Wyjście wskazuje strefę odejścia, relatywną ścieżkę i oczekiwane `id` kolejnego
scenariusza oraz flagi wymagane do aktywacji:

```json
{
  "continuation": {
    "id": "depart_for_watchtower",
    "label": "Wyruszcie do strażnicy",
    "description": "Drużyna rusza starym traktem.",
    "departure_zone_id": "forest_road",
    "target_scenario_id": "abandoned_watchtower",
    "target_scenario_path": "abandoned_watchtower.json",
    "unavailable_hint": "Porozmawiajcie z sołtysem i potwierdźcie gotowość.",
    "available_if_flags": ["ready_for_watchtower"],
    "propagate_flags": ["quest_accepted", "watchtower_alerted"],
    "travel_minutes": 45,
    "travel": {
      "navigation_dc": 12,
      "navigation_ability": "wisdom",
      "navigation_skill": "survival",
      "navigation_failure_delay_minutes": 30,
      "safe_travel_minutes": 480
    },
    "outcomes": [
      {
        "id": "lost_route",
        "kind": "fail_forward",
        "label": "Zgubiony trakt",
        "navigation_result": "failure",
        "target_effects": [
          {
            "type": "set_flag",
            "parameters": {"key": "route_lost", "value": true}
          }
        ]
      },
      {
        "id": "prepared_arrival",
        "kind": "success",
        "label": "Przybycie zgodnie z planem"
      }
    ]
  }
}
```

Opcjonalne `unavailable_hint` jest bezpieczną dla gracza instrukcją wyświetlaną,
gdy przejście istnieje, ale nie zostały jeszcze spełnione jego flagi.

Loader odrzuca nieznaną strefę, brakujący plik, niezgodne `target_scenario_id`,
ścieżkę absolutną oraz `..`. Runtime pozwala zakończyć scenę przez continuation
dopiero po spełnieniu flag i wejściu do strefy wyjścia. Przed wystawieniem
handoffu zapisuje pełny snapshot sceny źródłowej. Z ekranu podsumowania można
następnie uruchomić scenę docelową: runtime zachowuje wspólnych członków drużyny
z ich HP, ekwipunkiem, walutą i zasobami, dodaje aktorów występujących dopiero
w scenie docelowej, przenosi godzinę i jawne zasoby eksploracyjne oraz stosuje
zweryfikowane `target_effects`. Podłączony backend planszy pozostaje aktywny,
a nowa scena zaczyna się od zwykłego setupu papierowej mapy.

Opcjonalne `outcomes` są sprawdzane w kolejności po rozliczeniu podróży i progów
zegara. Gałąź może deklarować `required_flags`, `forbidden_flags` oraz
`navigation_result` (`any`, `success`, `failure`). Ostatni wpis musi być
bezwarunkowym fallbackiem. `kind` przyjmuje `success`, `partial_success` albo
`fail_forward`, a `target_effects` dopuszcza obecnie tylko pełne efekty
`set_flag`. `propagate_flags` kopiuje do handoffu wyłącznie jawnie wymienione
wartości; efekt wybranej gałęzi nadpisuje propagowany klucz. Runtime pokazuje
rezultat i cele źródłowe, a po rozpoczęciu sceny docelowej automatycznie stosuje
wynikowe konsekwencje.

Pole `travel` jest opcjonalną polityką podróży. UI zbiera tempo
`fast`/`normal`/`slow`, nawigatora oraz fizyczne wyniki d20. Runtime oblicza
czas z tempa, dodaje opóźnienie po nieudanej nawigacji i rozstrzyga Constitution
saves forced march po przekroczeniu `safe_travel_minutes`.

Wspólny czas scenariusza można skonfigurować w `exploration.clock`. Koszt wejścia
do strefy podaje jej `travel_minutes`, a polityka intencji NPC może podać
`time_cost_minutes`. Short rest, rytuały, crafting i zmiana pancerza korzystają
z tego samego licznika. Progi są ukrytym contentem MG i uruchamiają się tylko raz:

```json
{
  "clock": {
    "start_hour": 17,
    "events": [
      {
        "id": "dusk_on_old_road",
        "at_minute": 90,
        "label": "Zapada zmierzch",
        "narration": "Drogę spowija półmrok.",
        "effects": [
          {"type": "set_flag", "parameters": {"key": "dusk_arrival", "value": true}}
        ]
      }
    ]
  }
}
```

`at_minute` jest czasem od początku scenariusza, nie godziną zegarową. UI pokazuje
wyliczoną porę dnia, ale nie ujawnia przyszłych progów. Loader waliduje efekty
zegarowe tym samym kontraktem co pozostałe efekty eksploracji.

Formalne rzemiosło wykonywane przez pełne dni pracy deklaruje się osobno od
improwizowanego `/zbuduj`:

```json
{
  "downtime": {
    "crafting_recipes": [{
      "id": "forge_dagger",
      "label": "Wykuj sztylet",
      "zone_id": "market",
      "workshop_label": "Kuźnia na rynku",
      "item_ref": "dagger",
      "quantity": 1,
      "required_tool_id": "smiths_tools"
    }]
  }
}
```

Produkt musi być zwykłym, przenośnym itemem o dodatniej wartości. Aktor musi
znajdować się w podanej strefie, mieć biegłość `required_tool_id`, posiadać
działający item z takim `tool_proficiency_id` i zapłacić połowę wartości
rynkowej produktu. Runtime liczy pełne ośmiogodzinne dni po 5 gp postępu i
przesuwa istniejący zegar scenariusza.

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

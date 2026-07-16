# Items

Minimalne przedmioty i wyposażenie dla lokalnego contentu MVP.

Na tym etapie obsługujemy broń, proste narzędzia i consumable potrzebne do MVP:

- `id`, `name`, `kind`,
- `quantity` w inventory aktora,
- `broken` w inventory aktora dla uszkodzonych narzędzi i przedmiotów,
- `attacks`,
- `combat_actions`,
- `source_type`,
- `attack_kind`: jawne `melee` albo `ranged`,
- `range_feet`: maksymalny zasięg źródła; dla melee zachowuje zgodną wartość bazową,
- `reach_feet`: wymagany dla nowego źródła melee, dodatnia wielokrotność 5 feet;
  nie występuje dla ranged,
- `ability` używana do wyliczenia ataku,
- `damage`.

Wyposażenie trzymane w dłoniach deklaruje również:

- `hands_required`: `1` albo `2`,
- opcjonalne `light_weapon`, które kwalifikuje jednoręczne źródło melee do walki
  dwiema broniami,
- opcjonalne `versatile_damage_dice` dla broni versatile. Gdy druga ręka jest wolna,
  runtime dodaje osobny wariant źródła ataku oburącz z podaną kością obrażeń.
- opcjonalne `armor_class_bonus` i `armor_proficiency` dla wyposażenia ochronnego.
  Tarcza używa `kind: shield`, zajmuje jedną rękę i wymaga akcji do założenia lub
  zdjęcia podczas walki.

Runtime przypisuje wyposażone przedmioty do jawnych slotów `main_hand` i
`off_hand`. Starsza broń bez `hands_required` jest traktowana jako jednoręczna.
Jeżeli broń dwuręczna zajmie obie dłonie, późniejsze wyposażone bronie zostają
znormalizowane do stanu niewyposażonego.

`damage` obsługuje MVP format `dice`, np. `1d6`, opcjonalny `modifier` i `damage_type`.
Premia ataku bronią jest liczona z modyfikatora `ability` aktora oraz jego biegłości
w id przedmiotu. `attack_modifier` jest obsługiwany wyłącznie jako fallback dla
starszego źródła ataku, które nie deklaruje `ability`.
Loader potrafi jeszcze odczytać starsze źródła bez `attack_kind`, ale nowy content
nie powinien polegać na wnioskowaniu rodzaju ataku z samego `range_feet`.
Narzędzia mogą nie mieć mechaniki walki, ale mogą być wymagane przez opcje eksploracji.
Uszkodzone narzędzia pozostają widoczne w ekwipunku, ale nie spełniają wymagań opcji i nie dają premii.
`healers_kit` używa `quantity` jako liczby pozostałych zastosowań; każde użycie w walce
stabilizuje sąsiedniego nieprzytomnego sojusznika bez testu Medicine i zmniejsza ilość o jeden.

## Kontekstowe akcje przedmiotów w walce

Przedmiot może wystawić akcję skierowaną na aktora przez wpis w `combat_actions`:

```json
{
  "id": "splash_sticky_flask",
  "label": "Oblij lepką cieczą",
  "action_type": "targeted_item_effect",
  "action_cost": "action",
  "target_faction": "enemy",
  "range_feet": 5,
  "effect_kind": "apply_condition",
  "condition": "restrained",
  "duration": "permanent",
  "save_ability": "dexterity",
  "save_dc": 12,
  "save_timing": "turn_end"
}
```

Runtime pokazuje taką akcję w kategorii przedmiotów tylko dla legalnego celu i
dostępnego egzemplarza. Przedmiot oraz akcja tury są zużywane dopiero przy wykonaniu,
nie przy otwarciu menu. Obsługiwane efekty to `grant_next_attack_penalty` oraz
`apply_condition`. Drugi wymaga oficjalnego ID warunku i, jeśli warunek kończy się
rzutem, kompletnego zestawu `save_ability`, `save_dc`, `save_timing`. Kolejne efekty
wymagają jawnego resolwera i testów, a nie interpretowania dowolnego tekstu z contentu.

`action_cost` korzysta ze wspólnego kontraktu ekonomii tury i przyjmuje `action`,
`bonus_action`, `reaction`, `object_interaction` albo `free`. Brak pola zachowuje
kompatybilną wartość domyślną `action`; nowy content powinien podawać koszt jawnie.

## Właściwości i materiały sceny

`properties.json` jest wersjonowanym katalogiem identyfikatorów używanych przez
ustrukturyzowane przedmioty oraz fixture'y scen eksploracyjnych. Definicja materiału
może zawierać:

- `description`,
- `properties`,
- `portable`,
- `default_weight_lb`.
- `collection_destination`: `actor_inventory` (domyślne), `party_treasure` albo
  `scenario_quest`.

`collection_destination` jest deterministyczną polityką komendy `/weź`. Nie należy
wyprowadzać miejsca docelowego z narracji LLM ani z samego `kind`. `portable: false`
blokuje bezpośrednie zabranie niezależnie od miejsca docelowego.

Scenariusz tworzy konkretne egzemplarze przez `definition_id` i może dodać albo
usunąć właściwości zależne od stanu egzemplarza. Nie należy dodawać nieznanych tagów
bez wcześniejszego rozszerzenia katalogu.

Ten sam katalog służy do ogólnego wyszukiwania funkcjonalnego. LLM opisuje potrzebę
gracza przez właściwości wymagane i preferowane, ale nie wybiera obiektu. Runtime
porównuje zapytanie wyłącznie z dostępnymi instancjami sceny; nie utrzymujemy aliasów
typu konkretne słowo gracza -> konkretna definicja przedmiotu.

`crafting_purposes.json` opisuje funkcjonalne cele konstrukcji, a nie gotowe
receptury przedmiotów. Każdy cel definiuje grupy wymaganych właściwości, minimalne
ilości, tagi zastosowania, czas, liczbę użyć, modyfikator i ryzyko. Nazwę oraz opis
konkretnej konstrukcji dostarcza draft graczy/LLM, natomiast wartości mechaniczne
zawsze pochodzą z tego katalogu i deterministycznego walidatora.

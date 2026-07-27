# Items

Minimalne przedmioty i wyposażenie dla lokalnego contentu MVP.

Katalog obejmuje komplet 37 broni, 12 pancerzy korpusu, tarczę, cztery rodziny
amunicji oraz 144 definicje adventuring gear, focusów, narzędzi, instrumentów
i pakietów SRD 5.1. Scenariusz używa stabilnego `item_ref` niezależnie od tego,
czy definicja ma osobny plik, czy jest wpisem `adventuring_gear.json`.

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
- opcjonalne `ammunition_type` wymagające jednej sztuki kompatybilnej amunicji
  przy każdym wykonanym ataku,
- opcjonalne `loading`, ograniczające broń do jednego strzału w ramach Action,
- opcjonalne `charges_maximum`, `charges_recovery` (`never`, `short_rest`,
  `long_rest`), `charges_recovery_dice` i `charges_recovery_modifier` dla
  niestosowalnych przedmiotów wielokrotnego użytku,
- opcjonalne `requires_attunement` dla magicznych przedmiotów, których specjalne
  moce wymagają dostrojenia podczas short resta,
- opcjonalne `magic_effects`: lista pasywnych efektów z unikalnym `id`, typem
  `kind`, niezerowym `value` i opcjonalnym `requires_equipped` (domyślnie `true`).
  Obsługiwane typy to `armor_class_bonus`, `saving_throw_bonus`,
  `ability_check_bonus`, `attack_roll_bonus` oraz `speed_bonus_feet`,
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
- pancerz korpusu używa `kind: armor`, `armor_category` (`light`, `medium`,
  `heavy`) i dodatniego `armor_base_ac`. Opcjonalne `armor_dexterity_cap`,
  `armor_strength_requirement` i `stealth_disadvantage` opisują pełną formułę
  bez kodowania jej w nazwie przedmiotu.

Runtime przypisuje wyposażone przedmioty do jawnych slotów `main_hand` i
`off_hand`. Starsza broń bez `hands_required` jest traktowana jako jednoręczna.
Jeżeli broń dwuręczna zajmie obie dłonie, późniejsze wyposażone bronie zostają
znormalizowane do stanu niewyposażonego.

`damage` zachowuje zgodność z pojedynczym formatem `dice`, np. `1d6`,
opcjonalnym `modifier` i `damage_type`. Nowe źródło może zamiast tego podać
`components`: niepustą listę składników z unikalnym `id`, formułą `NdM` albo
`fixed`, opcjonalnym `modifier`, `label` i osobnym `damage_type`. Nie wolno mieszać
`components` ze starymi polami na tym samym poziomie.
Premia ataku bronią jest liczona z modyfikatora `ability` aktora oraz jego biegłości
w id przedmiotu. `attack_modifier` jest obsługiwany wyłącznie jako fallback dla
starszego źródła ataku, które nie deklaruje `ability`.
Loader potrafi jeszcze odczytać starsze źródła bez `attack_kind`, ale nowy content
nie powinien polegać na wnioskowaniu rodzaju ataku z samego `range_feet`.

## Jednolity schemat broni

Nowa broń używa jednego zagnieżdżonego obiektu `weapon`, bez ręcznie powielanej
listy `attacks`:

```json
{
  "id": "spear",
  "kind": "weapon",
  "weapon": {
    "category": "simple",
    "attack_kind": "melee",
    "properties": ["thrown", "versatile"],
    "normal_range_feet": 20,
    "long_range_feet": 60,
    "versatile_damage_dice": "1d8",
    "damage": {"dice": "1d6", "damage_type": "piercing"}
  }
}
```

`category` przyjmuje `simple` albo `martial`. Właściwości to `ammunition`,
`finesse`, `heavy`, `light`, `loading`, `reach`, `special`, `thrown`,
`two_handed` i `versatile`. Ammunition wymaga `ammunition_type`; ranged i thrown
wymagają obu zasięgów; versatile wymaga `versatile_damage_dice`; special wymaga
`special_rule` (`lance` albo `net`). Loader waliduje każdy samodzielny item podczas
repozytoryjnego audytu, nawet jeśli żaden scenariusz MVP go nie referencjonuje.
Narzędzia mogą nie mieć mechaniki walki, ale mogą być wymagane przez opcje eksploracji.
Uszkodzone narzędzia pozostają widoczne w ekwipunku, ale nie spełniają wymagań opcji i nie dają premii.
`healers_kit` używa puli 10 nieregenerujących się ładunków; każde użycie w walce
stabilizuje sąsiedniego nieprzytomnego sojusznika bez testu Medicine.

## Jednolity schemat zwykłego ekwipunku

Pole `gear` zawiera wspólne, opcjonalne reguły:

```json
{
  "id": "hooded_lantern",
  "kind": "gear",
  "gear": {
    "category": "adventuring_gear",
    "light": {
      "bright_distance_feet": 30,
      "dim_additional_feet": 30,
      "duration_minutes": 360,
      "fuel_item_id": "oil_flask",
      "hooded_dim_distance_feet": 5
    }
  }
}
```

Obsługiwane metadane obejmują `category`, `stackable`, `tool_proficiency_id`,
`spellcasting_focus_kind`, `container`, `light`, `check_modifiers`, `durability`
i `bundle_contents`. Equipment pack musi wskazywać istniejące stabilne ID;
repozytoryjny audyt sprawdza wszystkie wpisy katalogu i referencje bundle.

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

Opcjonalny dodatni `charge_cost` zmienia zużycie sztuki przedmiotu na wydanie
podanej liczby ładunków. Loader wymaga wtedy źródłowego przedmiotu z
`charges_maximum`, a runtime ukrywa akcję po wyczerpaniu puli. Bieżące
`charges_current` należy do instancji i domyślnie zaczyna się od maksimum.

`attuned` jest stanem instancji inventory, nie definicji katalogowej. Może być
ustawione tylko dla przedmiotu z `requires_attunement: true`. Niedostrojona
instancja pozostaje w ekwipunku, ale jej specjalne źródła i akcje są niedostępne.
Każdy aktor może podczas jednego short resta zmienić jedną więź, przy limicie
trzech dostrojonych przedmiotów.

Efekty `magic_effects` są aktywne tylko dla dostępnego przedmiotu, po wymaganym
dostrojeniu i — domyślnie — założeniu. Premie do rzutów pojawiają się jako osobne
komponenty typu `item`; KP i szybkość pozostają wartościami pochodnymi.

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
- `default_weight_lb`,
- `default_value_cp`,
- `ammunition_type` dla stosów kompatybilnej amunicji,
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

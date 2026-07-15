# Items

Minimalne przedmioty i wyposażenie dla lokalnego contentu MVP.

Na tym etapie obsługujemy broń, proste narzędzia i consumable potrzebne do MVP:

- `id`, `name`, `kind`,
- `quantity` w inventory aktora,
- `broken` w inventory aktora dla uszkodzonych narzędzi i przedmiotów,
- `attacks`,
- `combat_actions`,
- `source_type`,
- `range_feet`,
- `attack_modifier`,
- `damage`.

`damage` obsługuje MVP format `dice`, np. `1d6`, opcjonalny `modifier` i `damage_type`.
Narzędzia mogą nie mieć mechaniki walki, ale mogą być wymagane przez opcje eksploracji.
Uszkodzone narzędzia pozostają widoczne w ekwipunku, ale nie spełniają wymagań opcji i nie dają premii.

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

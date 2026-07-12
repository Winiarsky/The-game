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

# Monsters

Minimalne statblocki przeciwników dla lokalnego contentu MVP.

Format na tym etapie obejmuje:

- `id`, `name`, `kind`,
- `faction` oraz opcjonalne `size` (`medium` domyślnie),
- `ac`, `hp`, `temp_hp`, `speed_feet`,
- `ability_scores`,
- `proficiency_bonus` i wspólny obiekt `proficiencies`,
- opcjonalne `damage_resistances`, `damage_immunities` i `damage_vulnerabilities`,
- `attacks`,
- opcjonalne `multiattack`: uporządkowaną listę identyfikatorów ataków, także z
  powtórzeniami, wykonywaną po kolei w jednej turze przeciwnika.

Atak może zamiast attack rolla wymuszać saving throw przez pola `save_ability`,
`save_dc` i `save_damage_on_success` (`none` albo `half`). W turze przeciwnika bohater
rzuca wtedy fizyczne d20, a aplikacja stosuje damage dopiero po wpisaniu wyniku.

`proficiencies` może zawierać listy `saving_throws`, `skills`, `expertise`,
`weapons`, `armor` i `tools`. Naturalna broń potwora używa id źródła ataku jako id
biegłości, np. `goblin_scimitar`.

Pola odporności przyjmują stabilne identyfikatory typów obrażeń. Przykładowy
`stone_guardian.json` jest technicznym fixture'em pokazującym wszystkie trzy relacje,
atak wymuszający Dexterity save oraz dwuczęściowy Multiattack;
nie jest częścią oficjalnego katalogu D&D.

To nie jest pełny import SRD ani pełny statblock D&D 5e. Dane są ręcznie tworzone pod demo i testy.

# Macierz Implementacji D&D 5e

Ten dokument odpowiada na pytanie: „co już rzeczywiście działa, co jest tylko MVP,
a czego jeszcze nie ma?”. `ROADMAP.md` określa kolejność, natomiast ta macierz ma
być aktualizowana po każdym ukończonym vertical slice.

## Statusy

- `stabilne MVP` — działa w głównym UI, ma testy i może być rozszerzane,
- `częściowe` — istnieje użyteczny fragment, ale brakuje ważnych zasad,
- `fixture` — przypadek testowy istnieje, lecz nie jest jeszcze ogólnym systemem,
- `brak` — mechanika nie jest zaimplementowana,
- `decyzja` — najpierw trzeba ustalić zakres lub reprezentację.

Status nie oznacza pełnej zgodności z każdym oficjalnym wariantem. Szczegółowe
odstępstwa zapisujemy w `docs/RULES_DECISIONS.md`.

## Stan Bazowy

| Rodzina | Status | Co obecnie istnieje | Następna zależność |
|---|---|---|---|
| Plansza i współrzędne | stabilne MVP | siatka 20x30, teren, przeszkody, ściany, adapter planszy | rozmiary aktorów, wysokość |
| Pathfinding i ruch | częściowe | budżet ruchu, difficult terrain, ruch dzielony, LED | prone, grapple, forced movement, special movement |
| Linia widzenia i zasięg | częściowe | Bresenham LOS i podstawowy range | cover, senses, darkness, line of effect |
| Rzuty d20 | stabilne MVP | natural roll, modyfikatory, advantage/disadvantage | pełne proficiency i pasywne wartości |
| Ability checks | stabilne MVP | testy cech/skilli w eksploracji | actor proficiency/expertise jako dane |
| Saving throws | częściowe | save dla czarów, efektów i koncentracji | proficiency, warunki, repeated saves |
| Inicjatywa i tury | stabilne MVP | kolejność, aktywny aktor, rundy | surprise i pełne triggery turn-boundary |
| Ekonomia akcji | częściowe | action, bonus/reaction placeholders, movement, wybrane akcje | pełne bonus actions i free interaction |
| Ataki | stabilne MVP | melee/ranged, target selection, crit, save-spell | cover, reach, two-weapon, grapple/shove |
| Obrażenia i leczenie | częściowe | HP, temp HP, damage, healing, defeat | resistance/immunity/vulnerability, 0 HP, death saves |
| Reakcje | częściowe | opportunity attack i Ready | generyczna kolejka reakcji i wiele triggerów |
| Akcje tury | częściowe | Dash, Dodge, Disengage, Help, Ready | Hide, Search, Use an Object i warianty zasad |
| Warunki | brak | pojedyncze efekty zachowują się podobnie do warunków | wspólny condition/effect framework |
| Efekty i czas trwania | częściowe | ActiveCombatEffect i efekty eksploracji | jeden model duration, expiry i triggerów |
| Odpoczynki i dzień przygody | stabilne MVP | short rest z Hit Dice i contentowym ryzykiem; automatyczny long rest przed scenariuszem | przerwania, scenario-end lifecycle i snapshot |
| Ekwipunek | częściowe | inventory, quantity, broken, consumables, item actions | equipment, armor, weight, attunement, charges |
| Spell slots | stabilne MVP | poziomy slotów i zużycie | upcasting, recovery profiles, multiclass slots |
| Przygotowanie czarów | stabilne MVP | wybór po automatycznym long reście, limit, always prepared | class-derived profile |
| Znane czary i spellbook | brak | brak osobnych profili | generic spell access profiles |
| Targeting czarów | częściowe | single target, radius, line, cone, save i healing | pełny range/target/line-of-effect |
| Koncentracja | częściowe | jeden efekt, zastępowanie, save po damage | wspólny duration framework i modyfikatory |
| Components, ritual, upcasting | brak | brak | stabilny spell schema i equipment |
| Eksploracja | stabilne MVP | zones, points, challenges, checks, resources, effects | czas, senses, hazards i trwałe konsekwencje |
| Freeform/LLM | stabilne MVP | analiza, klasyfikacja, korekta MG i deterministic effects | pełna walidacja branches i parametrów |
| NPC i sceny społeczne | częściowe | pierwszy przepływ NPC i lokalne policy | conversation state, attitude i szersze efekty |
| Encounter setup | stabilne MVP | setup mapy/aktorów, inicjatywa, powrót do eksploracji | szablony encounterów i różne cele |
| Save/load | brak | log obserwacyjny nie jest zapisem gry | wersjonowany snapshot i migracje |
| Kampania | brak | scenariusz i pojedyncze przejścia | persistent party/NPC/quest state |
| Potwory | fixture | kilka lokalnych definicji scenariuszy | monster schema, traits, recharge, katalog |
| Przedmioty | fixture | kilka broni, narzędzi i consumables | pełny schema i katalog rodzinami |
| Czary | fixture | kilka czarów bojowych i utility | spell schema i katalog rodzinami |
| Rasy/species i backgroundy | brak | anonimowi aktorzy testowi | feature composition framework |
| Klasy i subclassy | brak | mechaniki testowane bez modelu klasy | effects/resources/rest/spellcasting/level-up |
| Kreator bohatera | brak | postacie pochodzą z contentu | stabilne actor/class schemas i builder domenowy |
| Kreator scenariusza | brak | foldery JSON i formularze dokumentacyjne | stabilne schemas, authoring API i preview |

## Kolejka Audytu Mechanik

Przy rozpoczęciu każdego etapu należy rozbić jego rodzinę na osobne wiersze,
np. każdy oficjalny warunek albo każdą rodzinę czarów. Dla każdego wiersza
docelowo zapisujemy:

- identyfikator reguły,
- status implementacji,
- wersję zasad i źródło,
- moduł domenowy,
- fixture contentowe,
- testy jednostkowe i integracyjne,
- decyzję lub odstępstwo projektowe,
- ostatni zweryfikowany playtest.

## Zasada Aktualizacji

Pull request lub etap wdrażający mechanikę nie jest zakończony, dopóki nie
zaktualizuje odpowiedniego wiersza tej macierzy. Nie zmieniamy statusu na `stabilne MVP`
wyłącznie dlatego, że istnieje model danych; wymagane są runtime/UI, testy i widoczny
kontrakt zachowania.

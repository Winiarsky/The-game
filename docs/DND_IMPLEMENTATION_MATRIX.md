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
| Plansza i współrzędne | stabilne MVP | siatka 20x30, teren, przeszkody, ściany, adapter planszy oraz kategorie rozmiaru aktorów reprezentowanych przez jedno pole | wielopolowe footprinty, wysokość |
| Pathfinding i ruch | częściowe | budżet ruchu, difficult terrain, ruch dzielony, LED, prone, wymuszony ruch Shove oraz przeciąganie Grappled z szybkością zmniejszoną o połowę | pozostały forced movement, special movement, reguły przechodzenia zależne od rozmiaru |
| Linia widzenia i zasięg | częściowe | Bresenham LOS, jawne rozdzielenie melee `reach` i ranged `range`, half/three-quarters/total cover na linii pocisku | senses, darkness, dokładna geometria rogów i wysokości |
| Rzuty d20 | stabilne MVP | natural roll, modyfikatory, advantage/disadvantage oraz osobne składniki cechy, proficiency i expertise | modyfikatory cech i efektów klasowych |
| Ability checks | stabilne MVP | testy cech/skilli/narzędzi, alternatywna cecha skilla, proficiency/expertise, passive skill score, generyczne contesty oraz Athletics vs Athletics/Acrobatics dla Shove i Grapple | dalsze contesty |
| Saving throws | częściowe | wspólny request/result dla czarów i efektów, profil biegłości, fizyczny rzut gracza przeciw efektom przeciwnika, automatyczny rzut potwora przeciw czarom gracza, `none`/`half`, integracja z typed damage, osłona `+2/+5` dla Dex save czarów, powtarzane save-at-start/save-at-end warunków i pozycyjne modyfikatory aur | auto-fail STR/DEX z pozostałych warunków |
| Inicjatywa i tury | częściowe | kolejność, aktywny aktor, rundy, scenariuszowe utrudnienie inicjatywy oraz precombat Stealth vs passive Perception przenoszone do walki | pełny per-creature surprised condition i triggery turn-boundary |
| Ekonomia akcji | stabilne MVP | action, budżet pojedynczych ataków w Attack action, bonus action, reaction, dzielony movement, darmowa interakcja z obiektem, jawne koszty contentu, fallback drugiej interakcji do akcji oraz wspólne okno reakcji | cechy przyznające dodatkowe akcje |
| Ataki | stabilne MVP | melee/ranged, jawny reach źródła melee, cecha i biegłość broni z profilu aktora, grupowany katalog źródeł, target selection, crit, save-spell z osłoną dla Dex save, osłona AC, zwarcie, domyślne flankowanie, Extra Attack-ready `attacks_per_action`, Shove/Grapple zastępujące atak, bonusowy atak drugą lekką bronią oraz data-driven Multiattack potworów | zaawansowane właściwości broni |
| Obrażenia i leczenie | częściowe | HP, temp HP, wieloskładnikowe źródła obrażeń `NdM`, resistance/immunity/vulnerability per typ, healing, 0 HP, death saves, stabilization, massive damage, Medicine i healer's kit | redukcje płaskie |
| Reakcje | stabilne MVP | wspólne uporządkowane `ReactionWindow`, jedna reakcja na aktora, pomijanie niedostępnych opcji, bezpieczne wznowienie przerwanej akcji, opportunity attack opuszczający faktyczny reach oraz Ready | kolejne typy triggerów, np. reakcje czarów |
| Akcje tury | stabilne MVP | Dash, Dodge, Disengage, Help, Ready, Hide, Search i data-driven Use an Object | warianty zasad i bardziej złożone przedmioty |
| Warunki | częściowe | wspólny `ConditionState`, źródłowy Grappled, Prone, Poisoned i Restrained; odporności, modyfikatory ataków/testów/save'ów, blokada ruchu, timed expiry, repeated saves, UI i snapshot v1 | pozostałe oficjalne warunki i ich szczególne konsekwencje |
| Efekty, cechy i czas trwania | stabilne MVP | wspólny ActiveEffect, źródło, stacking oraz expiry; warunki współdzielą duration; aktor może wystawić pozycyjną aurę save'ów; data-driven triggery używają wspólnych event ids i emiterów hit/damage/move/turn/rest/encounter; ograniczone ataki zużywają wspólne pule z recovery albo Recharge; wersjonowane FeatureDefinition/FeatureGrant składają zasoby, akcje, triggery i aury z jawnym pochodzeniem | kolejne rodzaje skutków i grantów proficiency |
| Odpoczynki i dzień przygody | stabilne MVP | short rest z Hit Dice i contentowym ryzykiem; automatyczny long rest przed scenariuszem; scenario-end lifecycle i snapshot v1 | przerwania |
| Ekwipunek | częściowe | inventory, quantity, equipped, broken, consumables, contentowe akcje przedmiotów na wskazanym celu, upuszczanie i podnoszenie broni, jawne sloty obu rąk, broń jedno- i dwuręczna, wolna ręka dla Grapple, Two-Weapon Fighting, versatile oraz tarcza zajmująca rękę i dająca efektywne KP | pozostałe armor, weight, attunement, charges |
| Spell slots | stabilne MVP | poziomy slotów i zużycie | upcasting, recovery profiles, multiclass slots |
| Przygotowanie czarów | stabilne MVP | wybór po automatycznym long reście, limit, always prepared | class-derived profile |
| Znane czary i spellbook | brak | brak osobnych profili | generic spell access profiles |
| Targeting czarów | stabilne MVP | single target, radius, line z szerokością, rosnący cone w 8 kierunkach, line-of-effect, jawny target mode, friendly fire, save i healing | wysokość, nietypowe bryły i dokładne warianty geometrii rogów |
| Koncentracja | częściowe | jeden efekt, wspólne zastępowanie/expiry, save po damage | zaawansowane modyfikatory i pełne czasy czarów |
| Components, ritual, upcasting | brak | brak | stabilny spell schema i equipment |
| Eksploracja | stabilne MVP | zones, points, challenges, checks, resources, effects, data-driven hazards oraz ukryte pułapki z wykrywaniem, rozbrojeniem, ominięciem, aktywacją i snapshotem | pełne senses, rozbudowane pułapki mapowe i wykorzystanie pułapek przeciw przeciwnikom |
| Freeform/LLM | stabilne MVP | analiza, klasyfikacja, korekta MG, grounded conversation, progresywne podpowiedzi i deterministic effects; efekty propozycji NPC oraz strukturalnych branches korzystają ze wspólnego walidatora policy | pełna walidacja pozostałych niestrukturalnych gałęzi eksploracji |
| NPC i sceny społeczne | stabilne MVP | chat i lokalne policy; trwały NpcRuntimeState; tabela reakcji 2014 zależna od attitude; limity prób; strukturalne cele i cztery wyniki; load-time validation efektów/referencji; zapisane przejścia wznawiające, zamykające albo kierujące do encountera; dwa fixture'y NPC | handel, ceny i usługi po ustabilizowaniu pełniejszej ekonomii przedmiotów |
| Encounter lifecycle | stabilne MVP | scenariuszowy etap rozpoczęcia, setup mapy/aktorów, inicjatywa oraz typowane zakończenia przez zwycięstwo, porażkę, wykonanie celu, odwrót lub kapitulację z osobnymi efektami eksploracji | szablony encounterów i bardziej złożone cele wieloetapowe |
| Save/load | stabilne MVP | wersjonowany snapshot v1 aktorów, eksploracji, efektów i aktywnej walki; atomowy JSON, walidacja ids, web UI i round-trip | stan kampanii oraz migracje kolejnych wersji |
| Kampania | brak | scenariusz i pojedyncze przejścia | persistent party/NPC/quest state |
| Potwory | fixture | kilka lokalnych definicji scenariuszy, w tym specjalny atak z Recharge 5–6 | monster schema, traits i katalog |
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

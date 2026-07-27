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
| Ataki | stabilne MVP | melee/ranged, normal/long range, reach, finesse, thrown, heavy, light, loading, versatile, ammunition, dynamiczny modyfikator obrażeń, kategorie proficiency, lanca i grywalna sieć; grupowany katalog źródeł, target selection, crit, osłona, zwarcie, flankowanie, Extra Attack, Shove/Grapple, Two-Weapon Fighting i Multiattack | mounted lance oraz niszczenie sieci jako obiektu |
| Obrażenia i leczenie | częściowe | HP, temp HP, wieloskładnikowe źródła obrażeń `NdM`, resistance/immunity/vulnerability per typ, healing, 0 HP, death saves, stabilization, massive damage, Medicine i healer's kit | redukcje płaskie |
| Reakcje | stabilne M7.6 | wspólne uporządkowane `ReactionWindow`, jedna reakcja na aktora, pomijanie niedostępnych opcji, bezpieczne wznowienie przerwanej akcji, opportunity attack, Ready, Tarcza i Kontrczar z manualnym testem silniejszego czaru | reakcje na inne triggery i wielu uprawnionych kontrujących |
| Akcje tury | stabilne MVP | Dash, Dodge, Disengage, Help, Ready, Hide, Search i data-driven Use an Object | warianty zasad i bardziej złożone przedmioty |
| Warunki | częściowe | wspólny `ConditionState`, źródłowy Grappled, Prone, Poisoned i Restrained; odporności, modyfikatory ataków/testów/save'ów, blokada ruchu, timed expiry, repeated saves, UI i snapshot v4 | pozostałe oficjalne warunki i ich szczególne konsekwencje |
| Efekty, cechy i czas trwania | stabilne MVP | wspólny ActiveEffect, źródło, stacking oraz expiry; warunki współdzielą duration; aktor może wystawić pozycyjną aurę save'ów; data-driven triggery używają wspólnych event ids i emiterów hit/damage/move/turn/rest/encounter; ograniczone ataki zużywają wspólne pule z recovery albo Recharge; wersjonowane FeatureDefinition/FeatureGrant składają zasoby, akcje, triggery i aury z jawnym pochodzeniem | kolejne rodzaje skutków i grantów proficiency |
| Odpoczynki i dzień przygody | stabilne MVP | short rest z Hit Dice, contentowym ryzykiem i jedną zmianą attunement per aktor; automatyczny long rest przed scenariuszem; odzyskiwanie ładunków przedmiotów przy short/long rest; scenario-end lifecycle i snapshot v12 | przerwania |
| Ekwipunek | stabilne MVP | inventory, quantity, equipped, broken, wartość i masa; portfel pięciu nominałów, masa monet, udźwig `Siła × 15 lb`, selektywny loot i handel; komplet 12 pancerzy korpusu, tarcza i 37 broni SRD; 144 definicje adventuring gear, focusów, narzędzi i pakietów; typowane pojemności, światło/paliwo, modyfikatory użytkowe, durability i rozwijanie pakietów; amunicja, charges, attunement, efekty magiczne, sloty rąk, Two-Weapon Fighting i versatile | wariantowe encumbrance, automatyczne warunki zerwania attunement, targowanie, usługi oraz pojazdy |
| Spell slots | stabilne M7.4 | poziomy slotów, zużycie, jawny wybór slotu bazowego lub wyższego oraz skalowanie kości obrażeń/leczenia i liczby celów | recovery profiles, multiclass slots |
| Przygotowanie czarów | stabilne M7.1 | wybór po automatycznym long reście, limit, always prepared i wspólny profil dostępu | class-derived profile |
| Znane czary i spellbook | fundament M7.1 | osobne generyczne profile dostępu i odmienne reguły castability | class-derived acquisition oraz kopiowanie do spellbooka |
| Targeting czarów | stabilne MVP | single target, radius, line z szerokością, rosnący cone w 8 kierunkach, line-of-effect, jawny target mode, friendly fire, save i healing | wysokość, nietypowe bryły i dokładne warianty geometrii rogów |
| Koncentracja | częściowe | jedna koncentracja może grupować efekty wielu celów; wspólne zastępowanie/expiry i save po damage usuwający całą grupę | zaawansowane modyfikatory i pełne czasy czarów |
| Components, ritual, upcasting | stabilne M7.7 | wersjonowany spell schema, V/S/M, focus/component pouch, kosztowne i zużywane materiały, jawny cast-at-level, scaling kości i liczby celów, rytuał eksploracyjny oraz przerywalny casting minutowy/godzinny z akcją co turę, koncentracją i odroczonym zużyciem slotu | klasowe wyjątki komponentów i castingu |
| Przywołania | stabilne M7.8 | data-driven statblock, wolne widoczne pole w zasięgu, dynamiczny sojusznik zaraz po właścicielu w inicjatywie, własny atak, koncentracja, automatyczne usunięcie i zapis v17 | wiele istot z jednego czaru, komendy i klasowe skalowanie statblocku |
| Magiczny ruch | stabilne M7.9 | data-driven teleport na widoczne wolne pole, push/pull po nieudanym save, zatrzymanie przed przeszkodą lub aktorem, UI/LED i zwykłe eventy ruchu bez kosztu szybkości oraz opportunity attack | teleport sojuszników, wymiana miejsc, wielocelowy forced movement |
| Debuffy czarami | stabilne M7.10 | data-driven stan po nieudanym save, automatyczny pierwszy save przeciwnika, wspólny ConditionState i powtarzany save w zadanym momencie tury, UI/LED | koncentracyjne debuffy i wiele celów |
| Dispel | stabilne M7.11 | cel-istota z efektem czaru, automatyczne zakończenie efektów do poziomu slotu, osobne fizyczne testy dla silniejszych efektów, ActiveEffect/ConditionState provenance, dismissal summonów, UI/LED | samodzielne efekty obszarowe, obiekty i magia eksploracyjna |
| Eksploracja | stabilne M8.13 | zones, points, challenges, checks, resources, effects, guarded flow graphy, continuation i zegar; ambient light i senses; Search, passive trap detection i Hide; pułapki i hazards; drzwi, zamki, pojemniki i obiekty; podróż z tempem, nawigacją fail-forward, forced march i exhaustion; formalny crafting downtime; warunki zachowujące źródło i duration przy przejściu eksploracja↔combat; outcome branches success/partial/fail-forward, podsumowanie celów i typowane konsekwencje między scenami | automatyczne scalanie scen w kampanię, dynamiczne światło zależne od pory dnia, zdarzenia losowe, inne aktywności downtime oraz niszczenie fixture'ów bezpośrednio podczas walki |
| Freeform/LLM | stabilne M8.1 | analiza, klasyfikacja, korekta MG, grounded conversation, progresywne podpowiedzi i deterministic effects; jawny aktywny cel i krawędź flow narzucają mechanikę, a LLM klasyfikuje metodę bez tagowego przejmowania skutków innej trasy | pełna walidacja pozostałych niestrukturalnych gałęzi eksploracji |
| NPC i sceny społeczne | stabilne M8.10 | chat i lokalne policy; trwały NpcRuntimeState; tabela reakcji 2014 zależna od attitude; gracz wybiera Persuasion/Deception/Intimidation; limity prób; strukturalne cele i cztery wyniki; guarded NPC flows dla zwiadowcy, Brena i Olana; jawne stawki i przejścia sceny | migracja pozostałych legacy punktów, targowanie, reputacyjne modyfikatory cen i usługi |
| Encounter lifecycle | stabilne MVP | scenariuszowy etap rozpoczęcia, setup mapy/aktorów, inicjatywa oraz typowane zakończenia przez zwycięstwo, porażkę, wykonanie celu, odwrót lub kapitulację z osobnymi efektami eksploracji | szablony encounterów i bardziej złożone cele wieloetapowe |
| Save/load | stabilne MVP | snapshot v23 aktorów, exhaustion, eksploracji, walki, fixture'ów, kupców, ekwipunku, spellcastingu, efektów, długiego castingu i przywołań; sekwencyjne migracje v1→…→v23, atomowy JSON, walidacja ids, web UI i round-trip | stan kampanii oraz migracje kolejnych wersji |
| Kampania | typowany handoff M8.13 | continuation wskazuje zweryfikowany następny scenariusz, dolicza czas podróży, zachowuje pełny snapshot źródła oraz emituje rezultat, cele, propagowane flagi i efekty docelowe | zastosowanie handoffu oraz automatyczne mapowanie drużyny, NPC i quest state między snapshotami |
| Potwory | fixture | kilka lokalnych definicji scenariuszy, w tym specjalny atak z Recharge 5–6 | monster schema, traits i katalog |
| Przedmioty | stabilne mundane MVP | pełne 37 broni, 4 rodziny amunicji, 12 pancerzy, tarcza oraz 144 definicje adventuring gear/focus/tool/pack SRD 5.1 pod wspólnymi schematami; dwa magiczne fixture'y | magic items rodzinami oraz przedmioty zależne od pojazdów/mounted play |
| Czary | schema + pierwszy SRD content | rodziny M7 oraz sześć wykonywalnych czarów SRD: Sacred Flame, Healing Word, Fire Bolt, Burning Hands, Cure Wounds i Inflict Wounds; poziom aktora skaluje cantripy | dalszy katalog rodzinami i klasami |
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

# Mechanics Architecture

Ten dokument opisuje aktualną siatkę klas mechanik oraz zasady dodawania nowych funkcjonalności.

Cel tej warstwy: nowe akcje, czary, reakcje i interakcje mają trafiać do przewidywalnej hierarchii, zamiast rozrastać się jako warunki porozrzucane po UI.

## Zasada Główna

Mechanika ma trzy warstwy:

1. **Deklaracja mechaniki** w `src/dnd_board_game/actions/`.
2. **Czyste rozstrzyganie zasad** w `src/dnd_board_game/rules/`, `world/`, `actors/`, `combat/`.
3. **Transport i prezentacja** w `src/dnd_board_game/ui/` oraz `hardware/`.

Warstwa `actions/` opisuje czym jest akcja i jakiego rodzaju zasobów/targetowania używa. Nie powinna znać Flask, WLED, seriala, sesji webowej ani lokalnego czasu.

## Aktualna Hierarchia

```text
ActionMechanic
├── CombatActionMechanic
│   ├── AttackMechanic
│   │   ├── BasicAttack
│   │   │   ├── MeleeAttack
│   │   │   │   └── OpportunityAttack
│   │   │   └── RangedAttack
│   │   ├── SpellAttack
│   │   │   ├── SpellAttackRoll
│   │   │   └── SpellSaveAttack
│   │   │       └── AreaSpellAttack
│   │   └── ReadyAttack
│   ├── MovementMechanic
│   │   ├── BasicMove
│   │   └── DashAction
│   ├── DefensiveAction
│   │   ├── DodgeAction
│   │   └── DisengageAction
│   ├── SupportAction
│   │   ├── HelpAction
│   │   ├── ConcentrationAction
│   │   └── ReadyAction
│   ├── AwarenessAction
│   │   ├── HideAction
│   │   └── SearchAction
│   ├── HealingMechanic
│   │   ├── SpellHealing
│   │   ├── ItemHealing
│   │   └── CustomHealing
│   ├── ItemAction
│   │   └── StrengthPotionAction
│   └── SceneInteractionMechanic
│       └── ObjectInteraction
└── ExplorationActionMechanic
```

`ExplorationActionMechanic` jest miejscem na kolejne uporządkowanie wyzwań, NPC i eksploracji. Obecny etap porządkuje przede wszystkim combat.

## Exploration Mechanic Tools

Eksploracja ma osobną warstwę nazwanych "mechanic tools" w `src/dnd_board_game/exploration/mechanics.py`.
To nie jest jeszcze pełna hierarchia klas akcji jak w combacie. Jest to kontrakt między LLM jako MG, walidatorem deterministycznym i UI:

```text
ExplorationMechanicId
├── single_actor_check
├── lead_with_help_check
├── group_check
├── use_item_check
├── use_spell_check
├── improvised_tool_check
└── preparation_effect
```

LLM powinien wybierać `selected_mechanic` z tego katalogu, a nie wymyślać reguły. Pozostałe pola propozycji (`check_participants`, `check_aggregation`, `ability`, `skill`, `dc`, zasoby, konsekwencje i kontrolowane modyfikatory sytuacyjne) są parametrami wybranej mechaniki. Web UI pozwala MG skorygować wybraną mechanikę i podstawowe parametry testu przed zaakceptowaniem rzutu; korekta przechodzi przez tę samą walidację mechanic tool.

Modyfikatory sytuacyjne eksploracji są częścią planu rzutu, nie osobną mechaniką. Każdy wpis musi wskazywać źródło (`scenario_context`, `zone_context`, `challenge_context`, `interaction_object`, `player_declaration`, `dynamic_state`, `gm`) i powód. Runtime dopuszcza tylko małe premie/kary oraz `advantage`/`disadvantage`, a UI pokazuje je MG przed rzutem.

`improvised_tool_check` używa dodatkowego payloadu `ImprovisedToolUse`: etykieta, źródło, szczegół źródła, mały modyfikator, ryzyko i powód. To jest jednorazowy element planu rzutu, a nie nowy wpis w inventory. UI wymaga jawnej akceptacji MG, bo LLM nie może samodzielnie stworzyć trwałego narzędzia ani zasobu drużyny.

Zasoby sceny są odrębnymi, istniejącymi wpisami `ExplorationResource`. Wybrany posiadany zasób dokłada do deterministycznego planu rzutu premię i ewentualną przewagę, a resolver wyzwania stosuje redukcję hałasu oraz komplikacji. Zasób z `consume_on_use` jest po rzucie usuwany przez `apply_exploration_effect(remove_resource)`, dzięki czemu zmiana trafia do tego samego kontraktu obserwowalności co pozostałe efekty eksploracji. Korekta MG pokazuje i waliduje wybór przed rzutem.

Wspólny builder ability check składa modyfikator cechy, skilla i narzędzia. Skill
i narzędzie używają jednego klucza stackingowego proficiency, dzięki czemu ich
biegłości nie są doliczane podwójnie. `rules/contests.py` porównuje dwa gotowe
rzuty bez zależności od eksploracji, UI i konkretnej akcji; Grapple/Shove składają
własne deklaracje i skutki na tym resolverze.

Pierwszym konsumentem contestu jest `application/combat_shove_flow.py`. Serwis
oddziela przygotowanie widocznego preview od rozstrzygnięcia, ponownie sprawdza
zasięg i pole wymuszonego ruchu przed zużyciem akcji, a następnie deleguje
powalenie do wspólnego `ConditionState`. UI przechowuje `PendingShove`, dzięki
czemu anulowanie przed rzutem nie zużywa akcji.

`application/combat_grapple_flow.py` korzysta z tego samego resolvera contestu, ale
zapisuje relację źródłową `Grappled(target <- source)`. `combat/conditions.py`
odpowiada za zerowy ruch celu, połowę efektywnej szybkości chwytającego, normalizację zerwanych
relacji oraz serializowalne źródło warunku. `combat/session.py` wykonuje przesunięcie
chwytającego i celu jako jedną domenową operację ruchu. UI przechowuje
`PendingGrapple`, więc także próba chwytu i ucieczki nie zużywa akcji przed rzutem.

Walidator ma pilnować spójności:

- `single_actor_check`: jedna postać i `lead_result`,
- `lead_with_help_check`: prowadzący z pomocą i `lead_result`,
- `group_check`: `whole_party` albo `selected_actors` oraz agregacja grupowa,
- `use_item_check`: item jako wymóg/premia/koszt/ryzyko,
- `use_spell_check`: czar jako wymóg/premia/koszt slotu,
- `improvised_tool_check`: wymaga `ImprovisedToolUse` i jawnej akceptacji MG przed rzutem,
- `preparation_effect`: przygotowanie przyszłej próby.

Kolejny refaktor eksploracji powinien przenieść improwizowane narzędzia na ten kontrakt: deklaracja graczy -> `selected_mechanic` -> walidacja -> preview UI -> rzut.

## Pliki

- `actions/base.py`: wspólne enumy i `ActionMechanic`.
- `actions/attacks.py`: ataki bronią, czary ofensywne, area spell, opportunity/ready attack.
- `actions/movement.py`: ruch i Dash.
- `actions/turn_actions.py`: Dodge, Disengage, Help, koncentracyjne akcje wsparcia, Ready, item actions.
- `actions/healing.py`: leczenie czarem, itemem albo customowe.
- `actions/interactions.py`: interakcje z obiektami sceny.
- `actions/catalog.py`: fabryki mapujące obecny content/runtime na klasy mechanik.
- `actions/resolution.py`: małe serwisy aplikacyjne rozstrzygające akcję + zasób + efekt domenowy.
- `exploration/mechanics.py`: katalog mechanic tools dla wolnych deklaracji eksploracji i ich payloady dla LLM/UI.

## Serwisy Rozstrzygania

`actions/resolution.py` jest warstwą pośrednią między UI a czystym combatem. UI może wybrać cel, zebrać Enter/kliknięcie i wpisać wynik rzutu gracza, ale nie powinno samo składać pełnego efektu typu "zużyj akcję, zużyj slot, rzuć save, policz obrażenia, podmień aktora".

Aktualne serwisy:

- `ActionResourceResolver`: zużywa akcję główną i opcjonalny slot czaru.
- `AttackActionResolver`: aplikuje obrażenia do pojedynczego celu, także po rzucie obronnym.
- `SpellSaveAttackResolver`: potwierdza czar przeciw pojedynczemu celowi i wykonuje rzut obronny celu.
- `AreaSpellResolver`: potwierdza czar obszarowy, wykonuje save'y celów i aplikuje obrażenia w obszarze.

Przygotowanie czarów nie jest osobnym typem akcji. `actors/spell_preparation.py`
przechowuje czysty profil i waliduje wybór, a `application/spell_preparation_flow.py`
prowadzi sekwencję aktorów przed scenariuszem. Te same reguły dostępności są
sprawdzane przez combat, eksplorację i payload UI przed zużyciem slotu.
- `HealingActionResolver`: zużywa akcję/slot i aplikuje leczenie.

## Kontekstowy katalog akcji walki

`combat/context_menu.py` definiuje prezentacyjny kontrakt opcji oraz
`ContextualActionCatalog`. Poszczególne providery — broń, manewry, czary, przedmioty,
leczenie i interakcje sceny — dostarczają wyłącznie legalne `CombatMenuOption`.
Katalog scala je, odrzuca powtórzone identyfikatory i nadaje stabilną kolejność
kategorii. Nie wykonuje zasad i nie zużywa zasobów.

Wybór opcji deleguje wykonanie do istniejącego flow konkretnej mechaniki. Przykładowo
`application/combat_item_action_flow.py` waliduje contentową akcję przedmiotu na
wskazanym celu, zużywa akcję oraz egzemplarz itemu i nakłada jawny `ActiveCombatEffect`.
Dodanie nowej kategorii efektu przedmiotu wymaga rozszerzenia allowlisty, osobnego
rozstrzygnięcia i testu domenowego; opis contentu nie jest wykonywalnym skryptem.

Kolejne refaktory powinny przenosić podobne orkiestracje do tej warstwy, jeśli zaczynają łączyć więcej niż jeden element zasad. Przykłady: flankowanie z modyfikatorem ataku, koncentracja po rzuceniu czaru, efekty warunków po trafieniu.

## Reguły Dodawania Feature'a

1. **Najpierw nazwać mechanikę.**
   Dodaj klasę w `actions/`, jeśli feature jest nowym typem akcji, reakcji, ruchu, czaru albo interakcji.

2. **Dziedziczyć tylko po relacji "jest rodzajem".**
   Przykład: `AreaSpellAttack` jest rodzajem `SpellSaveAttack`, więc dziedziczy.
   Parametry typu DC, zasięg, kształt obszaru, koszt slotu albo typ obrażeń są danymi, nie osobnymi klasami.

3. **Rozstrzyganie zasad zostaje poza UI.**
   Rzut obronny, obrażenia, zasięg, ścieżka, line of sight i ekonomia akcji muszą być w `rules/`, `world/`, `combat/` albo w serwisie `actions/resolution.py`, jeśli chodzi o połączenie kilku czystych reguł w jedną akcję.

4. **UI tylko wybiera, pokazuje i transportuje.**
   `exploration_app.py` może pokazać `mechanic.as_payload()`, ale nie powinien decydować, czy czar jest melee, ranged, save-spell albo area-spell.

5. **Content jest mapowany przez fabrykę.**
   Jeśli `AttackSource`, `HealingSource` albo `ScenarioCombatActionDefinition` dostają nowe pole, dodaj mapowanie w `actions/catalog.py` albo module konkretnej mechaniki.

6. **Każda nowa mechanika ma test hierarchii.**
   Test powinien sprawdzać klasę, `inheritance_path()`, `resource`, `targeting` i tagi.

7. **Każda nowa mechanika ma test rozstrzygania.**
   Klasa mechaniki nie wystarcza. Drugi test musi sprawdzić realny efekt w czystej domenie albo sesji UI.

8. **Dokumenty są częścią implementacji.**
   Przy nowej mechanice aktualizuj `docs/RULES_DECISIONS.md`, `TODO.md` i w razie nowej gałęzi klas ten plik.

## Flankowanie

`combat/attack_positioning.py` oblicza osłonę, zagrożenie dla ataku dystansowego i
flankowanie w jednym czystym `AttackPositioning`. Flankowanie jest modyfikatorem
rzutu, nie osobną akcją: evaluator zapisuje `flanking_ally_ids`, a
`attack_source_with_positioning()` dodaje przewagę i jawny `RollModifier`.

Geometria dla jednopolowych aktorów wymaga przeciwnych wektorów względem celu,
łącznie z przeciwnymi rogami. Domyślny argument `flanking_enabled=True` ustanawia
regułę dla runtime; testy mogą ją jawnie wyłączyć bez zależności od UI lub contentu.

## Rozmiar stworzeń

`actors/size.py` definiuje uporządkowane kategorie `CreatureSize` i czystą regułę
celu Grapple/Shove. `Actor.size` domyślnie przyjmuje `Medium`, dzięki czemu starszy
content pozostaje zgodny. Przepływy manewrów walidują rozmiar przed utworzeniem
pending action i ponownie przed rozstrzygnięciem. Rozmiar jest obecnie cechą zasad,
nie geometrii: każdy aktor nadal zajmuje dokładnie jedno pole.

## Ręce i wyposażenie

`inventory/hands.py` jest czystą warstwą reguł dla dwóch slotów dłoni. Normalizuje
starsze `equipped=True` do `held_in`, buduje widok `HandLoadout` i przygotowuje
`HandEquipPlan` bez zależności od UI, walki ani plików contentu. `combat/session.py`
zużywa interakcję z obiektem, stosuje plan i dopiero potem emituje komunikat.

Mechaniki potrzebujące wolnej ręki, obecnie Grapple, korzystają z
`free_hand_count()` zamiast samodzielnie interpretować inventory. Rezerwacje rąk
wynikające z warunków walki są nakładane w payloadzie aktora, dzięki czemu UI pokazuje
zarówno przedmioty w dłoniach, jak i ręce zajęte przez aktywną mechanikę.

## Typy obrażeń i profile odporności

`core/damage_types.py` udostępnia stabilne identyfikatory trzynastu bazowych typów
obrażeń, a `Actor.damage_affinities` przechowuje resistance, immunity i vulnerability
bez zależności aktora od modułu walki. `combat/damage.py` grupuje składniki tego samego
typu, rozlicza profil celu i zwraca surową oraz końcową wartość każdego składnika.

`apply_damage_result()` zawsze ponownie rozlicza wejściowe składniki względem aktualnego
profilu celu. Dzięki temu ataki gracza, AI, reakcje i czary obszarowe nie mogą ominąć
odporności przez zastosowanie wcześniejszego, nierozliczonego `DamageResult`. Warstwa
aplikacji dodaje ten sam breakdown do komunikatu i payloadu UI.

## Rzuty obronne

`rules/saving_throws.py` definiuje neutralne `SavingThrowRequest` i
`SavingThrowResult`. Źródło efektu podaje cechę, ST oraz skutek sukcesu (`none` albo
`half`), a resolver aktora dokłada modyfikator cechy i biegłość z jednego profilu.
Spelle gracza nadal mogą rozstrzygać rzuty przeciwników automatycznie, natomiast efekt
przeciwnika skierowany w bohatera zatrzymuje turę w `EnemyTurnFlowService`. UI pokazuje
ST i składniki modyfikatora, przyjmuje naturalny wynik fizycznego d20, a dopiero potem
stosuje kolejno wynik save'a, typ obrażeń, affinity celu i temporary HP.

## Zagrożenia eksploracyjne

`ExplorationHazard` jest niezależnym, data-driven opisem zagrożenia: triggerem
`failure` albo `critical_failure`, neutralnym `SavingThrowRequest`, obrażeniami oraz
narracją obu wyników. Opcja challenge może wskazać najwyżej jedno zagrożenie danego
triggera. `application/exploration_hazard_flow.py` rozstrzyga fizyczny save i stosuje
ten sam typed-damage pipeline co walka. `ExplorationUiSession` jedynie kolejkuje etap,
aktualizuje aktora po resolverze i zapisuje pełny wynik w logu sesji.

`combat/two_weapon.py` jest czystą warstwą reguł Two-Weapon Fighting: rozpoznaje
kwalifikujący atak lekką bronią do walki wręcz, wybiera legalne źródła z przeciwnej
dłoni i buduje wariant źródła obrażeń bez dodatniego modyfikatora cechy. Stan tury
przechowuje wyłącznie stabilny identyfikator broni otwierającej bonusowy atak;
`application/player_combat_action_flow.py` waliduje go ponownie i zużywa akcję
bonusową podczas rzutu ataku.

`combat/weapon_grip.py` buduje pochodne źródła ataku zależne od aktualnego układu
dłoni. Dla broni versatile zachowuje źródło jednoręczne i dokłada wariant oburącz ze
stabilnym sufiksem id oraz kością z contentu. Wariant powstaje tylko przy wolnej,
niezarezerwowanej drugiej ręce i jest ponownie walidowany przed rozstrzygnięciem.

`inventory/armor.py` oblicza premię wyposażenia i efektywne KP bez mutowania bazowego
`Actor.ac`. `combat/targets.py`, payload UI i podgląd ataku korzystają z tej samej
funkcji. Tarcza pozostaje zwykłym itemem zajmującym slot dłoni, natomiast
`combat/session.py` odpowiada za pełnoakcyjne `don_shield`/`doff_shield`, walidację
biegłości i zastosowanie planu dłoni.

## Jak Dodać Nowy Czar

1. Użyć istniejącej gałęzi:
   - attack roll: `SpellAttackRoll`,
   - save przeciw celowi: `SpellSaveAttack`,
   - obszar: `AreaSpellAttack`.
2. Dodać dane do contentu: zasięg, damage, `spell_level`, opcjonalnie `area`, `save_ability`, `save_damage_on_success`.
3. Jeśli czar wymaga nowej geometrii, rozszerzyć `combat/spells.py` i dodać test geometrii.
4. Jeśli czar wymaga nowego efektu stanu, dodać czystą strukturę efektu i test wygasania.

## Aktualny Stan Refaktoru

Zakończony etap refaktoringu objął następujące kroki:

1. Klasowa warstwa deklaracji mechanik jest podpięta do payloadu UI.
2. Pierwsza część orkiestracji walki została przeniesiona z `exploration_app.py` do `actions/resolution.py`: akcja + slot, czary na save, czary obszarowe, obrażenia po save i leczenie.
3. Transport Flask, frontend, główny kontrakt widoku, stan `pending_*` i adapter sesji planszy zostały wydzielone z monolitycznego modułu UI bez zmiany endpointów.
4. `application/exploration_flow.py` przejął deterministyczne przejścia startu, setupu mapy, lokacji, podróży, wyboru punktu i wykrywania triggerów encountera; sesja UI zachowała logowanie i synchronizację LED jako efekty brzegowe.
5. `application/combat_movement_flow.py` przejął planowanie ruchu gracza, wykonanie bezpiecznego ruchu i wykrywanie zagrożeń atakiem okazyjnym.
6. `application/combat_reaction_flow.py` przejął zużywanie reakcji przy ruchu gracza, rozstrzyganie automatycznych ataków i obrażeń oraz decyzję, czy ruch dochodzi do skutku. Źródło rzutów jest wstrzykiwane, więc testy mogą używać jawnych wyników.
7. Ten sam moduł przejął wspólny rdzeń ręcznych reakcji bohaterów: ataki okazyjne na poruszającego się wroga, wykrywanie triggera Ready, rzut ataku, konsumpcję efektów i obrażenia. UI zachowuje wyłącznie kolejne ekrany rzutu oraz wznowienie albo przerwanie tury przeciwnika.
8. `application/combat_turn_action_flow.py` przejął walidację i wykonanie Dash, Dodge i Disengage oraz przygotowanie i potwierdzenie Help i Ready. Serwis zwraca stan walki, efekty i dotychczasowe payloady obserwowalności, a UI czyści wybory i synchronizuje planszę.
9. `application/enemy_turn_flow.py` przejął walidację tury przeciwnika, planowanie zamiaru, uruchomienie istniejącego resolvera AI i klasyfikację wyniku jako Ready, atak okazyjny, ruch, atak albo natychmiastowy koniec. Trigger `Ready: enemy_moves` rozpoznaje rzeczywisty ruch przez `PathResult.origin` i `destination`, niezależnie od pozycji aktora zapisanej w wyniku. Potwierdzenie fizycznej planszy pozostaje efektem brzegowym UI.
10. `application/combat_turn_finalization.py` przejął zatwierdzenie wyniku przeciwnika po potwierdzeniu planszy, zużycie efektów następnego ataku, przejście do kolejnej tury oraz wygaszanie efektów początku i końca tury. Zwracane przejście zachowuje dotychczasowe komunikaty i payloady obserwowalności; sesja UI nadal obsługuje koncentrację, czyszczenie ekranów oczekujących i LED-y.
11. `application/player_combat_action_flow.py` przejął wybór źródeł ataku i leczenia oraz pełny przepływ pojedynczego ataku gracza: wskazanie i potwierdzenie celu, atak z przewagą lub utrudnieniem, czar z rzutem obronnym, zużycie akcji i slotu, obrażenia oraz kompatybilną ścieżkę bezpośredniego rozstrzygnięcia. UI nadal pokazuje kolejne ekrany, uruchamia test koncentracji po obrażeniach i synchronizuje LED-y.
12. `application/player_area_healing_flow.py` przejął wybór celu i rozstrzygnięcie leczenia oraz pełny przepływ czaru obszarowego: geometrię radius/line/cone, wybór celów, saving throwy, zużycie akcji i slotu, obrażenia wielu celów oraz anulowanie. UI zachowuje kolejkę testów koncentracji po obrażeniach, logowanie i LED-y.
13. `application/player_combat_resource_flow.py` przejął specjalne akcje zasobowe i cykl koncentracji: zużycie eliksiru i przedmiotu, rozpoczęcie lub zastąpienie koncentracji, zużycie slotu, utworzenie efektu, reakcję na obrażenia, automatyczny test przeciwnika oraz ręczny CON save bohatera. UI zachowuje prezentację promptu, logowanie i synchronizację planszy.
14. `application/combat_scene_interaction_flow.py` przejął wybór obiektu i opcji interakcji w walce, zużycie akcji, saving throw interakcji, zastosowanie zmian AC/pozycji/efektów oraz wygaszanie efektów zależnych od pola. Ten etap domyka planowane wydzielanie przepływów walki z `ExplorationUiSession`; UI pozostaje koordynatorem payloadów, logów i LED-ów.

Planowane wydzielenie dużych przepływów walki i końcowa faza porządkowa zostały zakończone. `UiPendingState` ma jawne typy wszystkich zawieszonych przepływów, a nieużywane wrappery pozostałe po ekstrakcji zostały usunięte. `ExplorationUiSession` pozostaje celowo cienkim koordynatorem kontraktu API, logów, LED-ów i efektów brzegowych. Dalsze prace powinny wrócić do funkcji produktowych; kolejnym zadaniem z backlogu jest zużywanie zasobów sceny w rzutach eksploracyjnych.

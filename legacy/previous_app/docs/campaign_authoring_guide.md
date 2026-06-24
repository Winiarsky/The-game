# Campaign authoring guide

Ten dokument jest instrukcja dla AI, ktore ma zaprojektowac pierwszy zarys prawdziwej kampanii na bazie obecnego systemu scenariuszy. `bandit_cave` traktuj jako benchmark integracji, a nie jako fabule do kopiowania.

## Punkt odniesienia

Benchmark:

- `scenario_flows/bandit_cave.json` - flow wielomapowe, flagi, eventy, objectives, warunki przejsc i final.
- `scenarios/bandit_cave_cave_entrance.json` - mapa wejscia z przeciwnikami, sekretami i przejsciami.
- `scenarios/bandit_cave_treasure_room.json` - mapa opcjonalna ze skarbem, pulapka albo obiektem interaktywnym.
- `scenarios/bandit_cave_smuggler_docks.json` - mapa finalowa z NPC i zakonczeniem.
- `player_ui/content/bandit_cave.json` - briefing, rozdzialy, cele i podsumowanie dla UI graczy.
- `assets/ui_v2/bandit_cave/SCENARIO_BENCHMARK.md` - techniczne kryteria gotowosci scenariusza.

Nowa kampania powinna miec podobny zakres integracji, ale wlasna strukture fabularna, wlasnych NPC, wlasne mapy i wlasne konsekwencje wyborow.

## Cel pierwszego zarysu

Pierwszy zarys kampanii ma byc dokumentem projektowym, nie finalnym JSON-em. Ma odpowiedziec na pytania:

- o czym jest kampania,
- jaki jest glowny konflikt,
- kto zleca albo uruchamia przygode,
- jakie sa mapy i po co gracz przez nie przechodzi,
- jacy NPC napedzaja wybor,
- jakie questy sa glowne i poboczne,
- jakie flagi stanu trzeba sledzic,
- jakie eventy musza istniec w `scenario_flow_v1`,
- jakie assety beda potrzebne dla UI,
- jaki jest golden path i co trzeba przetestowac.

Zarys ma byc wystarczajaco konkretny, zeby kolejny krok mogl wygenerowac pliki `scenario_flows`, `scenarios`, `player_ui/content` i liste assetow.

## Minimalny zakres kampanii v1

Pierwsza prawdziwa kampania powinna byc mala, ale kompletna:

- 3 do 5 map.
- 1 quest glowny z jasnym finalem.
- 2 do 4 questow pobocznych.
- 3 do 6 waznych NPC.
- 2 do 3 realne wybory z konsekwencjami w flagach.
- Co najmniej jedna mapa opcjonalna.
- Co najmniej jedna sekwencja spoleczna albo dialogowa.
- Co najmniej jeden sekret.
- Co najmniej jedna pulapka albo obiekt interaktywny z konsekwencja.
- Co najmniej dwa zakonczenia albo warianty podsumowania.

Nie projektuj od razu duzej kampanii z kilkunastoma mapami. Najpierw zrob vertical slice, ktory da sie przejsc od briefingu do finalu.

## Warstwy projektu

### 1. High concept

Opisz kampanie w 3-5 zdaniach. Ustal:

- tytul roboczy,
- ton,
- stawke,
- glowny konflikt,
- antyagoniste albo sile sprawcza,
- dlaczego druzyna musi dzialac teraz.

### 2. Struktura map

Dla kazdej mapy opisz:

- `map_id`,
- robocza nazwe,
- funkcje fabularna,
- glowny encounter albo problem,
- wazne obiekty,
- wejscia i wyjscia,
- sekrety,
- stan po oczyszczeniu mapy.

Kazda mapa powinna miec powod istnienia. Unikaj map, ktore sa tylko kolejnym pokojem z walka.

### 3. Questy i objectives

Rozdziel:

- quest glowny,
- questy poboczne,
- cele opcjonalne,
- cele ukryte.

Dla kazdego celu okresl:

- `objective_id`,
- opis dla gracza,
- trigger rozpoczecia,
- trigger ukonczenia,
- flagi, ktore zmienia,
- nagrode albo konsekwencje.

W `scenario_flow_v1` obecny system zna `objectives` i akcje `complete_objective`. Jesli potrzebny jest pelniejszy quest log, zarys powinien zaznaczyc brakujace pola jako propozycje rozszerzenia, nie udawac, ze juz istnieja.

### 4. NPC

Dla kazdego waznego NPC opisz:

- `npc_id`,
- imie,
- role fabularna,
- czego chce,
- co wie,
- co moze odblokowac,
- jakie flagi ustawia,
- czy jest sprzymierzencem, wrogiem, swiadkiem, zakladnikiem albo zdrajca.

NPC powinien zmieniac stan kampanii albo wiedze gracza. Jesli NPC tylko mowi klimat, lepiej przeniesc go do narracji eventu.

### 5. Dialogi

Dialogi sa czescia kampanii, nie ozdobnikiem. Dla kazdego waznego NPC przygotuj przynajmniej jedna scene dialogowa, a dla kluczowych NPC dwie lub trzy sceny zalezne od stanu kampanii.

Dla kazdej sceny dialogowej okresl:

- `dialogue_id`,
- `npc_id`,
- `map_id`,
- kiedy rozmowa jest dostepna,
- warunki flag,
- wypowiedz otwierajaca NPC,
- 3 do 5 wyborow gracza,
- odpowiedz NPC na kazdy wybor,
- ewentualny test umiejetnosci,
- flagi ustawiane po wyborze albo sukcesie,
- objectives ukonczone albo odblokowane,
- wariant rozmowy po powrocie, gdy stan juz sie zmienil.

Rozmowy powinny byc bardziej rozbudowane niz pojedyncza kwestia. Dobra scena ma:

- krotkie wejscie narratora ustawiajace sytuacje,
- charakterystyczny glos NPC,
- przynajmniej jeden wybor informacyjny,
- przynajmniej jeden wybor ryzykowny albo konfrontacyjny,
- przynajmniej jeden wybor empatyczny, sprytny albo oparty na dowodzie,
- skutek zapisany we flagach.

Przyklad struktury:

```text
dialogue_id: elna_first_warning
npc_id: elna_barrow
map_id: brindleford_square
conditions: elna_trusts_party=false
narrator: Elna zamyka drzwi dopiero, gdy patrol kasztelana znika za studnia.
npc_opening: "Nie wiem, kto was przyslal, ale jesli przyszliscie sluchac Vale'a, to juz jestescie spoznieni."
choices:
- label: "Powiedz nam, czego sie boisz."
  response: "Moj bratanek widzial cos przy kaplicy. Od tamtej pory trzymaja go w mlynie."
  set_flags: elna_trusts_party=true, acolyte_lead_received=true
  unlock_objective: free_the_acolyte
- label: "Kasztelan mowi, ze winna jest czarodziejka."
  response: "Kasztelan mowi to, co pozwala mu spac za zamknieta brama."
  set_flags: castellan_doubted=true
```

Jesli obecny runtime nie obsluguje jeszcze pelnego drzewa dialogowego, zarys nadal powinien je opisac jako content projektowy. Implementacja moze pozniej przeniesc dialogi do eventow, NPC action albo osobnego formatu.

### 6. Flagi i konsekwencje

Projektuj flagi od razu. Dobre flagi sa konkretne:

- `gate_guard_convinced`
- `relic_taken`
- `prisoner_freed`
- `cult_alarm_raised`
- `hidden_route_found`

Unikaj flag typu `quest_good` albo `story_done`, bo nie mowia, co naprawde zaszlo.

### 7. Eventy flow

Kazdy wazny beat fabularny powinien miec event:

- `map_start` dla wejscia na mape,
- `object_revealed` dla sekretow,
- `exit_enter` albo `exit_interact` dla przejsc,
- `combat_end` dla skutkow walki,
- event z akcja `finish_scenario` dla finalu.

Story eventy powinny zawierac tekst gotowy do UI i docelowo audio:

```json
{
  "type": "show_prompt",
  "audio": "audio/voiceover/example_001.mp3",
  "message": "Krotka narracja dla graczy."
}
```

### 8. Player UI content

Zarys powinien przewidziec:

- tytul i tagline,
- briefing,
- stawke,
- punkty briefingu,
- rozdzialy odpowiadajace mapom,
- cele glowne i opcjonalne,
- tekst wyniku,
- asset manifest.

To nie jest duplikat `scenario_flow`. `scenario_flow` jest runtime, a `player_ui/content` jest prezentacja dla gracza.

### 9. Assety

Dla kampanii przygotuj liste potrzebnych assetow:

- sceny dla map,
- portrety waznych NPC,
- ikony interactables,
- przeciwnicy,
- akcje specjalne,
- muzyka,
- ambience,
- voiceover dla waznych eventow.

Nie trzeba generowac assetow w pierwszym zarysie, ale trzeba wiedziec, czego brakuje.

## Format odpowiedzi AI

AI generujace zarys kampanii powinno zwrocic:

1. `Campaign overview`
2. `Map graph`
3. `Quest structure`
4. `NPC roster`
5. `Dialogue scripts`
6. `Narration beats`
7. `Flags`
8. `Scenario flow plan`
9. `Player UI plan`
10. `Asset plan`
11. `Golden path`
12. `Branching and consequences`
13. `Implementation checklist`
14. `Open questions`

Kazda sekcja ma byc konkretna. Zamiast ogolnego "dodac NPC", wpisz `npc_id`, lokalizacje, trigger i konsekwencje.

## Zasady projektowe

- Projektuj pod obecny runtime, nie pod wymarzony silnik.
- Nie mnoz mechanik, jesli ten sam efekt da sie osiagnac eventem, flaga i objective.
- Kazda mapa musi dodawac nowa decyzje, informacje albo konsekwencje.
- Kazdy quest musi miec jasny start, warunek sukcesu i skutek.
- Kazdy sekret musi miec sensowna nagrode: skrot, informacje, loot, sojusznika albo alternatywne zakonczenie.
- Kazdy wybor musi byc widoczny pozniej w dialogu, fladze, przejsciu, finalnym podsumowaniu albo dostepnosci mapy.
- Nie kopiuj nazw, postaci ani struktury fabuly z `bandit_cave`; kopiuj poziom kompletnosci integracji.

## Definition of ready

Zarys kampanii jest gotowy, kiedy mozna na jego podstawie jednoznacznie stworzyc:

- `scenario_flows/<scenario_id>.json`,
- pliki map w `scenarios/`,
- `player_ui/content/<scenario_id>.json`,
- liste assetow w `assets/ui_v2/<scenario_id>/`,
- test golden path,
- test co najmniej jednej negatywnej albo alternatywnej sciezki.

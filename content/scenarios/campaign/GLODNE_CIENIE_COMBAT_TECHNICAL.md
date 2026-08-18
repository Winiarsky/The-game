# Głodne Cienie — statystyki, decyzje i LED

Status: kontrakt implementacyjny pierwszego encountera  
Powiązane: `MAPA_1_GLODNE_CIENIE_ENCOUNTER_SPEC.md`, `docs/UTILITY_ENEMY_AI.md`

## 1. Granica Gemini

Tura przeciwnika nie wysyła zapytania do Gemini. Lokalny silnik wyznacza:

- legalne cele i pola;
- kandydatów ruchu oraz akcji;
- cechy i wynik utility;
- seeded noise;
- ostateczny cel, trasę, akcję i rezultat;
- śmierć, ucieczkę oraz zwycięstwo.

Opcjonalna narracja LLM może dostać dopiero zamknięty wynik `EnemyTurnPlan` i nie może go zmienić. Pierwsza implementacja Głodnych Cieni nie potrzebuje tej narracji.

Diagramy:

- `assets/diagrams/ostatni_transport_01/glodne_cienie_ai_decision_flow.svg`;
- edytowalne źródło: `glodne_cienie_ai_decision_flow.mmd`.

## 2. Głodny Cień

Źródło: `content/monsters/hungry_shadow.json`  
Rola AI: `skirmisher`

| Parametr | Wartość |
|---|---:|
| Rozmiar / typ | Medium beast |
| KP | 13 |
| PW | 14 |
| Szybkość | 40 ft |
| STR | 12 (`+1`) |
| DEX | 14 (`+2`) |
| CON | 12 (`+1`) |
| INT | 3 (`−4`) |
| WIS | 13 (`+1`) |
| CHA | 6 (`−2`) |
| Proficiency bonus | `+2` |
| Perception | `+3` |
| Stealth | `+4` |
| Passive Perception | 13 |
| Darkvision | 60 ft |
| Death saves | nie |

### Atak: Rozdarcie

- melee weapon attack;
- zasięg 5 ft;
- premia ataku `+5` (`+1` scenariuszowej premii do trafienia);
- trafienie: `1d6 + 2` slashing, średnio 5.5;
- jedna akcja ataku, bez Multiattack.

### Skok stada

Warunek: Cień przemieścił się w tej turze co najmniej 10 ft, trafia Rozdarciem, a przy celu stoi co najmniej jeden żywy członek stada.

Efekt: cel wykonuje Strength save ST 12. Porażka nakłada `prone`; sukces nie daje dodatkowego skutku. Obrażenia nie rosną.

Zaimplementowane przez generyczny hook `conditional_on_hit_save`: runtime
sprawdza przebyty dystans i sąsiedztwo sojusznika, a następnie otwiera fizyczny
rzut obronny i nakłada `prone` po porażce.

## 3. Przewodnica Głodnych Cieni

Źródło: `content/monsters/hungry_shadow_leader.json`  
Rola AI: `leader`

| Parametr | Wartość |
|---|---:|
| Rozmiar / typ | Medium beast |
| KP | 14 |
| PW | 30 |
| Szybkość | 40 ft |
| STR | 14 (`+2`) |
| DEX | 16 (`+3`) |
| CON | 14 (`+2`) |
| INT | 4 (`−3`) |
| WIS | 14 (`+2`) |
| CHA | 8 (`−1`) |
| Proficiency bonus | `+2` |
| Dex save | `+5` |
| Perception | `+4` |
| Stealth | `+5` |
| Passive Perception | 14 |
| Darkvision | 60 ft |
| Death saves | nie |

### Atak: Rozdarcie przewodnicy

- melee weapon attack;
- zasięg 5 ft;
- premia ataku `+6` (`+1` scenariuszowej premii do trafienia);
- trafienie: `1d8 + 3` slashing, średnio 7.5;
- jedna akcja ataku, bez Multiattack.

### Skok stada przewodnicy

Identyczny zaimplementowany warunek jak u harcownika. Strength save ma ST 13.

### Kotwica morale

To nie jest akcja aktora, tylko zdarzenia encountera:

- pierwszy spadek do połowy PW: morale `−1`;
- śmierć: morale `−2`;
- ucieczka przewodnicy: morale `−2`.

Każde zdarzenie działa najwyżej raz. Nie wprowadzamy aktywnego skowytu przesuwającego kilka figurek — komplikowałby ekonomię akcji, reakcje i fizyczne potwierdzenia, a rola przewodnicy jest już czytelna przez wagi `guard` i morale.

## 4. Ekonomia ruchu

- 40 ft daje budżet ruchu, a nie stałe osiem pól: ruch po skosie nadal stosuje projektową regułę 5–10–5;
- trudny teren podwaja koszt wejścia na pole;
- `Dash` dodaje drugi budżet 40 ft i zużywa akcję;
- `Disengage` zużywa akcję i wyłącza opportunity attacks dla całego ruchu w tej turze;
- `regroup` używa Disengage, jeśli bez niego ścieżka prowokuje OA; w innym przypadku może zakończyć ruch Dodge;
- `flee` używa Disengage przy OA, w innym przypadku Dash;
- wejście na `pack_escape` kończy ruch i natychmiast nadaje `escaped`.

## 5. Śmierć i warunek zwycięstwa

Przeciwnik przy 0 PW natychmiast otrzymuje `dead`. Nie ma stanu nieprzytomności ani death saves. `dead` i `escaped`:

- usuwają aktora z aktywnej inicjatywy;
- zwalniają jego pole;
- usuwają go z legalnych celów;
- uruchamiają instrukcję zdjęcia figurki;
- zapisują osobny wpis w outcome ledgerze.

Walka kończy się, gdy `active_hostile_count == 0`.

## 6. Skalowanie składu

| Bohaterowie | Harcownicy | Przewodnica | Morale |
|---:|---:|---|---:|
| 1 | 1 osłabiony do 10 PW | nie | 1 |
| 2 | 1 | osłabiona do 20 PW | 2 |
| 3 | 2 | pełna | 3 |
| 4 | 3 | pełna | 4 |
| 5 | 4 | pełna | 4 |

Podstawowym balansem pozostają warianty 3–5. Skalowanie zwiększa liczbę tur przeciwników, nie KP, obrażenia ani PW każdego harcownika.

## 7. Kontrakt LED

Plansza nie pokazuje wszystkich informacji jednocześnie. Każdy etap ma ograniczony zestaw warstw.

### Setup

| Element | Kolor | Istniejąca rola |
|---|---|---|
| pola startowe bohaterów | turkus `(0,220,255)` | `PLAYER_START_ZONE` |
| pola przeciwników | róż `(255,0,80)` | `ENEMY` |
| blokujący środek wozu | ciemna czerwień `(180,0,0)` | `BLOCKING_TERRAIN` |
| błoto i podejście na skarpę | pomarańcz `(255,120,0)` | `DIFFICULT_TERRAIN` |
| dzwon | zieleń `(0,255,120)` | `INTERACTIVE_OBJECT` |

Pola ucieczki i strefa młodego nie świecą podczas setupu; są właściwością AI, nie poleceniem dla graczy.

### Normalna tura przeciwnika

| Sygnał | Kolor |
|---|---|
| aktywna figurka | biały `(255,255,255)` |
| `engage` / `advance`: trasa | czerwony `(220,0,0)` |
| pole końcowe agresywnego ruchu | pomarańcz `(255,120,0)` |
| wybrany cel ataku | niebieski `(0,80,220)` |
| `regroup`: trasa | bursztyn `(255,190,40)` |
| `guard`: trasa i pole | fiolet `(180,0,255)` |

### Ucieczka

Potrzebne nowe role semantyczne:

| Rola | RGB | Zastosowanie |
|---|---|---|
| `ENEMY_FLEE_PATH` | `(255,0,180)` | droga uciekającej bestii |
| `ENEMY_ESCAPE_DESTINATION` | `(0,220,255)` | wybrane pole `pack_escape` |
| `ENEMY_REGROUP_PATH` | `(255,190,40)` | ruch defensywny |
| `ENEMY_GUARD_DESTINATION` | `(180,0,255)` | pozycja ochrony przepustu |

Sekwencja `flee`:

1. aktywny przeciwnik świeci na biało;
2. cała planowana ścieżka świeci na różowo;
3. docelowe pole ucieczki świeci na turkusowo;
4. po fizycznym potwierdzeniu ścieżka gaśnie;
5. gdy figurka osiągnie wyjście, jej pole błyska różowo i wszystkie LED-y tego aktora gasną;
6. UI pokazuje „Głodny Cień uciekł — zdejmij figurkę”.

### Śmierć

Po spadku do 0 PW pole przeciwnika:

1. świeci czerwono jako `ATTACK_MISS`/dedykowane `ACTOR_DEFEATED` przez krótki feedback;
2. następnie gaśnie;
3. UI prosi o zdjęcie figurki.

Docelowo należy dodać semantyczne `ACTOR_DEFEATED`, zamiast używać koloru o nazwie pudła.

### Priorytet warstw

`ACTOR_DEFEATED` / efekt trafienia > aktywny aktor > cel > pole końcowe > ścieżka > teren. Statyczny teren nie może przykryć bieżącej instrukcji ruchu.

Storyboard: `assets/diagrams/ostatni_transport_01/glodne_cienie_led_storyboard.svg`.

## 8. Kolejność implementacji przed finalnym playtestem

Stan przed testem fizycznym: punkty 1–8 i warstwa symulacyjna z punktu 10 są
wdrożone. Pełne wejścia pozycyjne utility AI, Dash, morale, Skok stada,
semantyczne role LED, skalowanie, checkpoint i Retry mają pokrycie automatyczne.
Raport 64 walk znajduje się w `GLODNE_CIENIE_PLAYTEST_REPORT.md`. Do wykonania
pozostaje test na fizycznej planszy oraz późniejsze hotspoty eksploracyjne.

1. **Zamrozić layout v4:** przepisać strefy i warianty z `glodne_cienie_tactical_layout_v4.json` do runtime encountera oraz zweryfikować pathfinding dla wszystkich slotów startowych, trzech przechodnich defensive spots i obu wyjść.
2. **Podłączyć skład 1–5:** wybierać dokładnie jeden `setup_by_party_size`, stosować modyfikatory PW wariantów 1–2 i podczas setupu pokazywać wyłącznie obsadzane pola `S1–S4`, `P` albo `1P`.
3. **Wdrożyć reguły terenu:** trudny teren, blokadę i połowiczną osłonę wozu, skarpę, przepust, strumień, dzwon oraz dwa pola `pack_escape`.
4. **Wdrożyć utility AI:** loader `weighted_utility_v1`, role `skirmisher`/`leader`, legalnych kandydatów ruchu, seeded noise i krótką pamięć celu. Gemini nie uczestniczy w wyborze tury.
5. **Domknąć mechanikę stada:** morale i jednorazowe zdarzenia, `regroup`, `cornered`, dobrowolne oraz wymuszone `flee`, a także `dead`/`escaped`, outcome ledger i zwycięstwo przy `active_hostile_count == 0`.
6. **Domknąć zdolności i otwarcie:** generyczny `conditional_on_hit_save` dla Skoku stada, warianty tempa podróży i wpływ flagi Erynda.
7. **Podłączyć UI, LED i fizyczne potwierdzenia:** setup terenu i figurek, podgląd zamiaru AI, trasy ucieczki, komunikaty zdjęcia figurki oraz nowe role LED z tego dokumentu.
8. **Zapisać pełny checkpoint Retry:** seed, wariant, pozycje, inicjatywę, zasoby, morale, pamięć AI, użyte interakcje i stan terenu; po porażce odtworzyć identyczny setup.
9. **Przekazać stan do eksploracji:** po zwycięstwie odblokować hotspoty i zachować stan wozu, dzwonu, ognia, ładunku, młodego oraz wyników `dead`/`escaped`.
10. **Testować warstwami:** najpierw unit testy reguł i AI, potem integracja setup–walka–Retry–handoff, następnie symulator/LED, a dopiero na końcu manualny balans wariantów 3–5.

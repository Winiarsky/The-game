# Raport playtestu referencyjnego MVP

Data: 2026-07-27  
Zakres: `village_square_mvp` → handoff → `abandoned_watchtower`  
Środowisko: web UI, symulator planszy 20×30, prawdziwe requesty Gemini, fizyczne rzuty wpisywane przez API

## Werdykt

Mechaniczny vertical slice jest szeroki i w większości działa: setup papierowych map,
wybór lokacji na planszy, NPC, handel, zapis/wczytanie, wyzwania, narzędzia,
pułapka, encounter, inicjatywa, osłona, krytyki, amunicja, rzucona broń,
przeszukiwanie i zakończenie scenariusza zostały wykonane w jednej sesji testowej.

Nie jest to jednak jeszcze prawdziwa rozgrywka „od wioski do końca strażnicy” bez
pomocy technicznej. Dwa blokery i kilka niespójności zasad wymagają poprawy przed
uznaniem MVP za samodzielnie grywalną referencję:

1. handoff wioska → strażnica jest tylko payloadem; nie uruchamia ani nie zasila
   kolejnej sceny,
2. powrót z rozmowy z NPC nie czyści aktywnego punktu po stronie serwera i blokuje
   działania lokacji,
3. jawnie zadeklarowany czar w rozmowie z NPC może zostać zamieniony przez LLM na
   zwykły test, bez zużycia slotu i bez użycia reguł czaru.

Po ręcznym uruchomieniu strażnicy i technicznym obejściu aktywnego NPC scenariusz
dało się zakończyć.

## Co zostało rzeczywiście rozegrane

### Wioska

- start sesji i obowiązkowe potwierdzenie mapy Rynku,
- ustawienie punktu NPC na fizycznej planszy,
- odczytanie tablicy ogłoszeń,
- dwie kontrolowane rozmowy z Brenem przez Gemini,
- przyjęcie zadania i potwierdzenie gotowości,
- handel: zakup dwóch pochodni za 2 cp,
- zapis sesji, podróż do Karczmy, rozmowa z Olanem i wczytanie zapisu,
- swobodna rozmowa oraz próba wmówienia NPC czerwonego smoka i nagrody 100 gp,
- rozłożenie mapy Drogi do lasu,
- nawigacja, podróż 45 minut i wygenerowanie handoffu do strażnicy.

Zapis/wczytanie poprawnie odtworzyło lokację, czas, rozmowy, walutę i dwie kupione
pochodnie.

### Strażnica

- osobny start scenariusza, long rest i przygotowanie czarów Kapłana,
- pełny setup mapy Bramy i elementów środowiska,
- otwarcie zamka narzędziami złodziejskimi przez Gemini,
- użycie istniejącej w scenie deski jako dźwigni oraz Help dający przewagę,
- rzut obronny na linkę alarmową,
- rozstrzygnięcie otwarcia encounteru,
- setup bohaterów i przeciwników na planszy,
- pełna inicjatywa,
- dwa ataki dystansowe, half cover, amunicja, dwa krytyki i pokonanie goblinów,
- rzut sztyletem pozostawiający broń na planszy,
- zastosowanie wyniku walki do eksploracji,
- rozłożenie mapy Dziedzińca i ustawienie zwiadowcy,
- pomoc zwiadowcy, aktywny Search w półmroku z utrudnieniem,
- odkrycie skrytki, ukończenie celu i zakończenie scenariusza.

Koszary i Wieża nie były wymagane do celu i nie zostały odwiedzone. To samo w
sobie jest obserwacją: scenariusz pozwala zakończyć się po jednym udanym Search na
Dziedzińcu.

## Perspektywa początkującego gracza

### Co jest zrozumiałe

- setup papierowej mapy jasno podaje nazwę, rozmiar 50×75 cm i wymaga potwierdzenia,
- ustawianie figurek prowadzi gracza po jednej postaci lub jednym punkcie,
- instrukcje rzutów pokazują kość, tryb, ST i pełne rozbicie modyfikatora,
- pasek postaci, HP, kolejność inicjatywy i aktualny etap walki są czytelne,
- przy wyzwaniach widać konkretne cele zamiast pustego pola tekstowego,
- handel poprawnie liczy monety, masę i udźwig,
- wynik podróży i podsumowanie celu wioski są czytelne.

### Co dezorientuje lub blokuje

- wpisanie zwykłej wypowiedzi bez wybranego NPC/wyzwania zwraca błąd
  „brak aktywnego wyzwania ani punktu NPC”, a wypowiedź może pozostać w historii,
- każda bezkostkowa odpowiedź NPC wymaga dodatkowego zaakceptowania i dopiero wtedy
  dolicza czas; dla rozmowy kosmetycznej jest to niepotrzebne tarcie,
- po kliknięciu powrotu od NPC działania lokacji nadal zwracają
  „Najpierw wróć z punktu interakcji do lokacji”,
- status pułapki pokazuje „uruchomiona” także po udanym złapaniu alarmu,
- przy krytyku główna instrukcja podaje `2d8 + 3`, ale wiadomość dla gracza nadal
  mówi `1d8 + 3`; ten sam błąd wystąpił dla sztyletu (`2d4` kontra `1d4`),
- podgląd ataku potrafi pokazać `amunicja bolt: 0`, mimo że Łotrzyca miała 20 bełtów,
- ekran końcowy Strażnicy nie pokazuje podsumowania celów ani zdobytych rzeczy;
  mówi o resecie, lecz Reset jest schowany w menu,
- nagłówek wioski pokazuje HP, ale bez nazw i portretów dwóch postaci.

Ocena początkującego: mechaniczne kroki są dobrze opisane, lecz błędne komunikaty i
blocker powrotu od NPC uniemożliwiają samodzielne przejście bez pomocy.

## Perspektywa zaawansowanego gracza

### Co działa

- system poprawnie rozpoznał lockpicking, narzędzia złodziejskie, biegłość i karę
  za zatarty zamek,
- istniejący obiekt sceny został użyty jako dźwignia bez tworzenia fikcyjnego itemu,
- prowadzący z pomocą otrzymał przewagę, a pomocnik nie rzucał osobno,
- half cover podniosło KP goblina z 13 do 15,
- rzucony sztylet został zdjęty z ekwipunku i umieszczony na konkretnym polu,
- próba wmówienia Olanowi smoka i 100 gp została przez Gemini odrzucona bez zmiany
  flag ani waluty,
- zapis utrzymał zakupione przedmioty i przeliczoną walutę.

### Co ogranicza świadome używanie zasad

- deklaracja „rzucam przygotowane Słowo leczenia” została potraktowana jako
  Medycyna ST 12. Slot pozostał 2/2. W D&D Healing Word nie wymaga testu Medycyny,
- odpowiedź NPC opisała działanie magii przed rozstrzygnięciem rzutu,
- swobodna rozmowa może dopisywać drobne nieautoryzowane fakty świata, np. że Olan
  prowadzi karczmę od 20 lat; nie zmienia to stanu mechanicznego, ale może
  niezamierzenie stać się kanonem przy kolejnych rozmowach,
- finał walki nie udostępnił ekwipunku ani waluty goblinów, choć przeciwnicy mieli
  po fiolce trucizny i 5 sp,
- rzucony sztylet oraz niezebrana amunicja zniknęły po zastosowaniu wyniku
  encounteru do eksploracji,
- „ukryta skrytka” ustawia tylko flagę i cel; nie pojawia się odkryte źródło ani
  możliwy do zebrania przedmiot.

Ocena zaawansowanego: reguły walki i testów są już użyteczne, ale freeform nie może
jeszcze bezpiecznie wybierać mechanik czarów, a pętla ciało/skrytka → loot →
ekwipunek nie jest domknięta w scenariuszu referencyjnym.

## Perspektywa techniczna

### Integracja

- symulator odpowiadał i obsłużył wszystkie wybory pól,
- stan planszy w API raportuje `backend: simulator`, ale jednocześnie
  `configured_backend: hardware`; to niespójny kontrakt diagnostyczny,
- start symulatora zgłosił brak importu `game_objects_loader`, lecz podstawowa
  plansza 30×20 działała,
- jeden krok rozpoczęcia encounteru trwał około 40 s; pozostałe lokalne requesty
  zwykle 3–9 s, w tym Gemini,
- payload `/api/state` w walce wielokrotnie serializuje pełnych aktorów, całe
  inventory i ponad sto tras ruchu. Przy większej drużynie, większej liczbie
  efektów i dłuższym katalogu będzie to kosztowne dla sieci, renderowania i logów.

### Kampania i ciągłość

Handoff jest poprawnie typowany: zawiera target scenario, czas podróży, wynik
nawigacji, source snapshot, propagowane flagi i target effects. Brakuje jednak
consumera handoffu.

W praktyce:

- strażnicę trzeba uruchomić osobno,
- drużyna wioski ma `hero` i `rogue`,
- strażnica tworzy `hero`, `rogue` i `cleric`,
- zakupione pochodnie, przeliczona waluta i aktualny czas nie zostały przekazane,
- efekty `target_effects` nie zostały automatycznie zastosowane.

Tekst UI „Konsekwencje zostaną zastosowane przy uruchomieniu kolejnej sceny” opisuje
zachowanie, którego runtime jeszcze nie wykonuje.

### Stan i zapis

Snapshot v23 przeszedł rzeczywisty round-trip dla wioski. Scenariusz Strażnicy po
ręcznym zakończeniu nie zapisał się automatycznie (`exists: false`), choć UI
pozwalał na zapis. Warto jednoznacznie zdecydować, czy scenario finish ma tworzyć
checkpoint automatycznie.

## Skalowanie contentu

### Bronie i zwykłe przedmioty

Fundament jest dobry:

- wspólne, wersjonowane definicje i stabilne ID,
- osobne pliki 37 broni oraz katalog 144 pozycji adventuring gear,
- `item_refs` dla prostych instancji,
- `inventory` z `item_ref` i override'ami ilości, wyposażenia, właściwości,
  attunement i stanu dla instancji scenariuszowych,
- wspólne generowanie źródeł ataku z itemu,
- content audit zweryfikował 240 wpisów i 7 scenariuszy bez błędów.

Dodanie typowej broni albo zwykłego itemu nie wymaga zmiany silnika, jeśli mieści
się w istniejącym schemacie. Nietypowa aktywna mechanika nadal wymaga
`combat_action`, efektu lub nowej rodziny domenowej.

Największy problem skalowania nie leży w katalogu, lecz w przesyłaniu pełnych
definicji itemów w każdym stanie UI oraz w braku wspólnej pętli lootu po encounterze.

### Potwory

Istnieje wersjonowany loader i dwie definicje (`goblin`, `stone_guardian`), ale to
za mało, by uznać katalog potworów za gotowy do masowej produkcji. Potrzebne są:

- ujednolicony model traitów, akcji, loot policy i wariantów statblocku,
- test instancji wielu potworów z jednego template,
- jawne zasady przenoszenia inventory/currency pokonanego aktora do ciała lub
  battlefield loot.

### Scenariusze i formularze

JSON-y są podzielone na mniejsze pliki i nadają się do dalszego rozszerzania.
Dokumentacyjne formularze nie są jednak aktualnym źródłem prawdy:

- `courtyard_search.md`, `hidden_cache.md`, `old_camp_tools.md` i
  `gate_inspect_area.md` nadal zawierają liczne `TODO`,
- formularz skrytki wprost nie określa jej zawartości ani mechaniki zebrania,
- `docs/RUNNING_AND_TESTING.md` zaczyna się stwierdzeniem, że istnieje tylko pierwszy
  debugowy runtime ruchu, co jest już nieaktualne,
- formularze powinny otrzymać walidowalne pola dla mapy papierowej, setupu punktów,
  loot bundle/corpse policy, warunków ukończenia i testów akceptacyjnych.

## Gotowość do kreatora postaci D&D

Można rozpocząć pracę nad fundamentem kreatora, ale nie nad końcowym formularzem UI.

### To już można wykorzystać

- `Actor`, Ability Scores, poziom 1–20, proficiency bonus,
- profile biegłości, expertise, saving throws, senses i size,
- HP, Hit Dice, death saves, exhaustion i odpoczynki,
- inventory, waluta, udźwig, pancerz, broń i ręce,
- spell access, spell preparation, sloty i komponenty,
- `FeatureDefinition` / `FeatureGrant` z pochodzeniem species, background, class,
  subclass i feat.

### Tego brakuje przed kreatorem zgodnym z D&D

- definicji species/race i backgroundów,
- definicji klas, subclass i tabel poziomów,
- domenowego buildera składającego granty i wykrywającego konflikty,
- wyboru metody Ability Scores i walidacji limitów,
- wyprowadzania HP, Hit Dice, proficiency bonus, save'ów, biegłości, wyposażenia,
  spell list i liczby przygotowanych czarów z klasy/poziomu,
- modelu level-up i multiclass,
- zapisu pochodzenia każdego wyboru gracza,
- finalnej walidacji „legal character”.

Aktualni aktorzy ujawniają, dlaczego builder jest konieczny:

- pole `level` jest pominięte, więc runtime domyślnie traktuje aktorów jako poziom 1,
- jednocześnie bohaterowie mają po 2 Hit Dice,
- Kapłan poziomu domyślnego 1 ma slot poziomu 3,
- ten sam Kapłan ma na profilu „known” m.in. Shield i Counterspell,
- UI nie pokazuje poziomu ani klasy.

Najpierw powinien powstać builder domenowy i minimalne definicje 1. poziomu dla
Fighter/Rogue/Cleric/Wizard. Dopiero potem warto budować formularze webowe; inaczej
formularz tylko utrwali ręcznie wpisywane, niespójne statblocki.

## Priorytety napraw

### P0 — przed kolejnym pełnym playtestem

1. Naprawić opuszczanie aktywnego NPC: UI i serwer muszą wyczyścić `active_point_id`.
2. Dodać consumer handoffu uruchamiający target scenario i mapujący drużynę, czas,
   inventory, zasoby, flagi i target effects.
3. Zablokować LLM-owi zastępowanie jawnie wybranego, dostępnego czaru zwykłym testem;
   użycie czaru ma przejść przez deterministyczny spell flow.

### P1 — żeby MVP było wiarygodną referencją

4. Ujednolicić komunikat obrażeń krytycznych z rzeczywistą formułą.
5. Domknąć corpse/battlefield loot, odzyskanie rzuconej broni i przejście lootu do
   eksploracji przed usunięciem combat state.
6. Dać ukrytej skrytce prawdziwą zawartość i możliwość zebrania.
7. Poprawić status złapanej pułapki, licznik amunicji i nagłówek drużyny wioski.
8. Nie zapisywać nieudanej deklaracji do rozmowy.
9. Ograniczyć dodatkowe zatwierdzenie dla bezkostkowych rozmów kosmetycznych.

### P2 — skalowanie i dalszy rozwój

10. Odchudzić view model: ID/ref zamiast pełnych kopii itemów i aktorów, stronicować
    historię oraz nie wysyłać wszystkich tras ruchu przy każdym odświeżeniu.
11. Uzupełnić formularze interakcji i zaktualizować dokument uruchamiania.
12. Rozpocząć K1–K3 od buildera postaci i wersjonowanego contentu klas/species/
    background, nie od samego formularza UI.

## Walidacja

Ręcznie:

- pełna sesja HTTP wioski i strażnicy,
- realne requesty Gemini dla kontrolowanych i swobodnych rozmów, lockpickingu,
  improwizowanej dźwigni i czaru przy NPC,
- symulator planszy dla map, lokacji, punktów, setupu encounteru, celów i rzutów,
- wizualny zrzut końcowych ekranów obu scenariuszy.

Automatycznie:

- `scripts/audit_content.py --json content` — 240 wpisów, 7 scenariuszy,
  0 błędów, 1 ostrzeżenie licencyjne,
- `tests/unit/test_weapon_catalog.py` — 5 passed,
- `tests/unit/test_adventuring_gear.py` — 7 passed,
- `tests/unit/test_content_audit.py` — 2 passed,
- `tests/unit/test_actor_features.py` — 2 passed,
- `tests/unit/test_spell_preparation_flow.py` — 1 passed,
- `test_village_quest_lifecycle_creates_guarded_watchtower_handoff` — 1 passed.

Nie testowano prawdziwego hardware. Wyniki dotyczą symulatora planszy.

## Follow-up implementacyjny — 2026-07-27

Po playteście domknięto punkty P0 oraz wskazane poprawki P1:

- wyjście z czatu czyści aktywny punkt przed ponownym wyborem z planszy,
- jawnie zadeklarowany, przygotowany czar leczący przy celu medycznym NPC omija
  test Medicine i zużywa slot dopiero po zatwierdzeniu,
- handoff uruchamia scenę docelową i przenosi drużynę, ekwipunek, walutę,
  zasoby, godzinę, flagi oraz `target_effects`, zachowując backend planszy,
- pozostały loot po zwycięskiej walce, monety i odzyskana amunicja są
  zabezpieczane przed usunięciem combat state; brak udźwigu blokuje wyjście,
- ukryta skrytka jest contentowym fixture'em z możliwym do zebrania sztyletem,
- komunikaty krytycznych reakcji pokazują podwojone kości,
- status pułapki rozróżnia oczekiwanie na save i zakończone rozstrzygnięcie,
- podgląd ataku pokazuje faktyczny stan amunicji,
- bohaterowie w scenie wioski mają portrety.

Walidacja po poprawkach:

- pakiet regresyjny zmienionych przepływów: `13 passed`,
- pełny `tests/unit/test_exploration_ui_app.py`: `72 passed`,
- `python -m compileall -q src/dnd_board_game`: bez błędów,
- `git diff --check`: bez błędów.

Próba uruchomienia całego `tests/unit/test_exploration_ui_session.py` została
przerwana przez limit procesu po około 64% bez raportu nieudanego testu. Zgodnie
z zasadami bezpieczeństwa repo nie uruchamiano kolejnych szerokich procesów
pytest; zmienione ścieżki pokrywa osobny, zakończony pakiet regresyjny.

# Raport: MVP z własną drużyną i Gemini

Data: 2026-07-28  
Model: `gemini-3.1-flash-lite`  
Zakres: kreator → roster → nowa gra → wioska → handoff → strażnica →
eksploracja → encounter → NPC po walce  
Tryb: prawdziwe requesty Gemini, Flask test client, runtime sesji i symulowany
backend planszy; bez przeglądarkowego testu wizualnego i bez fizycznego hardware

## Werdykt

Pętla jest mechanicznie szeroka i większość jej elementów działa z postaciami
utworzonymi przez kreator. Cztery własne postacie zostały zapisane, wybrane do
nowej gry, przeniesione z wioski do strażnicy i użyte w eksploracji, inicjatywie,
walce oraz rozmowie z NPC. Zwykłe podejście, broń, czar i przedmiot docierają do
wspólnego flow deklaracji. Ruch, zasięg, ekonomia akcji, obrażenia, test społeczny
i zmiana nastawienia NPC działają deterministycznie.

MVP z custom party nie jest jednak jeszcze gotowe do samodzielnej rozgrywki.
Test wykrył dwa blokery P0:

1. `gate_skirmish` ma trzy pola startowe bohaterów. Drużyna czteroosobowa nie może
   zakończyć setupu encounteru, mimo że ekran Nowej gry pozwala wybrać do pięciu
   postaci.
2. Wybrane źródło eksploracji nie jest twardo związane z propozycją Gemini.
   System zaakceptował łom Miry, gdy UI wysłało mały nożyk Vaela i Vaela jako
   uczestnika. Resolver wykonał skuteczną próbę, mimo niespójnego przedmiotu,
   właściciela i deklarowanej postaci.

Po diagnostycznym dodaniu czwartego pola startowego walka i NPC po walce
zadziałały. Nie zmieniano kodu gry; obejście istniało wyłącznie w skrypcie
playtestu.

## Drużyna testowa

Utworzono cztery legalne postacie 1. poziomu:

| Postać | Klasa | HP | Istotny zakres testu |
|---|---|---:|---|
| Brunna Żelazna | Fighter | 12 | longsword, wyważanie bramy |
| Mira Cichy Krok | Rogue | 10 | rapier, shortbow, thieves' tools, crowbar |
| Vael z Atramentem | Wizard | 8 | Fire Bolt, Magic Missile, mały nożyk |
| Elowen Kamienne Serce | Life Cleric | 12 | czary kapłańskie, Persuasion z NPC |

Kreator zwrócił formularz z sekcjami wyborów i pomocą dla standard array.
Wszystkie cztery rekordy pojawiły się w rosterze. Start Nowej gry zwrócił
przekierowanie do `/play`, a runtime zachował identyfikatory, statystyki,
ekwipunek i czary przez handoff do strażnicy.

Wniosek: domenowy builder, zapis postaci, roster, party selection i handoff są
spięte. Formularz jest jednak jednym długim ekranem z wieloma sekcjami, a nie
prowadzonym wizardem. To nie blokuje działania, ale dla pierwszej postaci może
być przytłaczające.

## Przebieg

### 1. Setup papierowych map

Runtime pokazał mapę Rynku o rozmiarze 50 × 75 cm, linki do podglądu, A4 PDF i
pełnego PDF. Po potwierdzeniu poprowadził osobny setup figurki Sołtysa Brena.
Handoff uruchomił analogiczny setup mapy strażnicy.

Wynik: **PASS**. Rozdzielenie lokacji na fizyczne mapy i confirm step są widoczne
w kontrakcie UI.

### 2. NPC w wiosce

Trzy realne deklaracje przeszły przez Gemini:

- pytanie o strażnicę: 1,71 s,
- przyjęcie zadania: 1,65 s,
- gotowość do wymarszu: 1,69 s.

Guarded flow poprawnie prowadził kolejno przez informację, commitment i travel.
Po handoffie drużyna przybyła do `abandoned_watchtower` o 18:20.

Wynik: **PASS**. Początkujący dostaje jasny cel, a model nie musi sam wymyślać
mechaniki ani skutków zadania.

### 3. Zwykłe podejście

Mira opisała oględziny muru bez użycia zasobu. Gemini utworzył obserwację w
2,15 s, a wysoki test ujawnił trasę przy murze, gobliny i przewagę do inicjatywy.

Wynik: **PASS**. Standardowa deklaracja bez źródła pozostaje pełnoprawną drogą.

### 4. Pułapka przejmująca następną deklarację

Po rozpoznaniu bramy runtime zakolejkował linkę alarmową. Następna deklaracja
użycia nożyka nie trafiła do klasyfikatora; po 0,02 s UI nadal pokazywało pending
pułapki. Dopiero rozstrzygnięcie pułapki odblokowało kolejną próbę.

Mechanicznie pending ma pierwszeństwo poprawnie, ale przepływ jest nieczytelny:
gracz może wybrać przedmiot i wysłać opis, który nie zostanie wykonany.

Wynik: **PARTIAL / P1 UX**. Gdy istnieje nierozstrzygnięty pending, composer
nowej akcji powinien być zablokowany albo UI powinno automatycznie przenieść
gracza do obowiązkowego kroku przed przyjęciem tekstu.

### 5. Broń

Dwie dłuższe, sensowne deklaracje użycia nożyka i miecza doprowadziły do
niepoprawnych payloadów `situational_modifiers`. Po retry gracz dostał bezpieczny
komunikat „Deklaracja wymaga korekty”, ale stracił około 9 s na każdą próbę.

Krótka deklaracja „Brunna uderza mieczem w drewniany środek bramy” przeszła w
5,53 s. Resolver wykonał Athletics, zastosował wynik, hałas i stan bramy.

Wynik: **PASS mechaniczny / PARTIAL UX**. Bezpieczny fallback działa, lecz
naturalny, bardziej precyzyjny opis paradoksalnie ma mniejszą skuteczność niż
krótka komenda.

### 6. Czar

Vael wybrał Fire Bolt jako jawne źródło i opisał trafienie w drewniany środek
bramy. Runtime:

- zachował wybrany spell source,
- ustawił `cast_fire_bolt=challenge:closed_gate`,
- nie zużył slotu, ponieważ Fire Bolt jest cantripem,
- wykonał test Inteligencji przeciw ST 11,
- zastosował hałas i postęp bramy.

Wynik techniczny: **PASS**. Wybrane źródło czaru oraz brak kosztu slotu są
poprawne.

Wierność 5e: **PARTIAL / P2**. Fire Bolt przeciw destrukcyjnemu obiektowi w 5e
naturalniej używałby spell attack przeciw AC obiektu i obrażeń, a nie testu
Inteligencji. Obecny challenge check jest grywalnym uproszczeniem, ale powinien
być jawnie opisany jako odstępstwo albo zastąpiony wspólnym fixture damage.

### 7. Zwykły przedmiot i krytyczna niespójność źródła

Pierwsza próba nożyka została odrzucona przez niepoprawny payload Gemini. Osobny
kontrolny test ujawnił poważniejszy problem:

- selected source z UI: `actor:vael:item:small_knife`,
- selected participant: `vael`,
- tekst gracza: „Mira używa łomu...”,
- propozycja Gemini: `used_resource_ids=["actor:mira:item:crowbar"]`,
- narracja i authored option: łom Miry,
- pending nadal raportował action source jako mały nożyk Vaela,
- resolver zaakceptował próbę i otworzył bramę.

Payload źródła jednocześnie miał `available: true` i tekst
`unavailable_reason: "Mały nożyk jest uszkodzony albo niedostępny."`, co jest
dodatkową niespójnością prezentacyjną.

Wynik: **FAIL / P0**. LLM nie może zmienić źródła wybranego przez UI. Grounding
powinien wymusić:

- identyczność selected source i `used_resource_ids`,
- zgodność właściciela źródła z uczestnikiem albo jawny transfer/pomoc,
- zgodność source kind/tags z trasą,
- brak `unavailable_reason`, gdy `available=true`,
- odrzucenie propozycji zmieniającej postać lub zasób.

### 8. Brama i odporność na błąd providera

Krótkie próby broni po wznowieniu przechodziły przez Gemini w 3,83–5,82 s i
poprawnie ustawiały `gate_passed`. W pierwotnym przebiegu końcowa deklaracja
trafiła jednak na 429 po retry.

Runtime nie zastosował częściowej propozycji i pokazał czytelny komunikat o
limicie. Proces pozostał sprawny, ale snapshot dostępny po teście odtwarzał
wcześniejszy checkpoint startu strażnicy, nie ostatni stan eksploracji.

Wynik: **PARTIAL / P1**. Potrzebny jest jawny retry ostatniej deklaracji,
backoff/jitter oraz decyzja, czy bezpieczny checkpoint ma powstawać po każdym
zaakceptowanym wyniku, czy tylko na żądanie gracza.

### 9. Setup encounteru z custom party

Encounter przejął wszystkie cztery własne postacie, ale krok „pola startowe
bohaterów” zawierał tylko trzy pozycje wynikające z trzech authored bohaterów
scenariusza. Po ustawieniu trzech figurek:

- `current_player_start_actor` nadal wskazywał Elowen,
- `remaining_player_start_positions()` zwróciło pustą kolekcję,
- setup nie mógł przejść dalej.

Wynik: **FAIL / P0**. To łamie oficjalny kontrakt Nowej gry „1–5 postaci”.

Po diagnostycznym dodaniu pola `(10, 6)` inicjatywa uwzględniła wszystkie cztery
postacie i dwóch goblinów.

### 10. Walka

Mira wygrała inicjatywę. Z rapierem na pozycji startowej nie miała legalnego
celu. Próba dobycia shortbow zużywała prawidłowo darmową interakcję, ale geometria
sceny nadal nie dawała linii strzału. Próba natychmiastowego powrotu do rapiera
była poprawnie blokowana brakiem kolejnej darmowej interakcji/akcji.

W finalnym przebiegu Mira:

- zachowała dobyty rapier,
- przeszła 15 feet na `(6, 8)`,
- dostała legalny cel `goblin_a`,
- uzyskała 23 do trafienia,
- zadała 4 piercing, zmieniając HP goblina z 10 na 6,
- zużyła akcję, zachowała bonus action, reaction i 15 feet ruchu.

Wynik: **PASS**. Ruch, zasięg, LoS, ręce, object interaction i turn economy
zachowują ducha 5e.

Wskazówka dla początkujących mogłaby być lepsza: przy braku legalnego celu UI
powinno wprost zasugerować „podejdź”, „zmień broń” albo „brak linii widzenia”,
zamiast pozostawiać pustą listę celu.

### 11. NPC po walce

Po zwycięstwie runtime:

- ustawił `gate_skirmish_cleared`,
- ujawnił `wounded_scout`,
- wymagał przejścia na osobną mapę Dziedzińca,
- pozwolił wybrać zwiadowcę dopiero w jego lokacji.

Elowen schowała broń, zachowała dystans i zaoferowała pomoc. Gemini odpowiedział
w 2,68 s. Persuasion ST 10 zakończyło się sukcesem, a nastawienie zmieniło się z
obojętnego na przyjazne.

Wynik: **PASS**. Treść, test, skutek społeczny i lokacja NPC są spójne.

## Perspektywa początkującego

Najlepiej działają setup map, NPC, jawne instrukcje rzutów i walka po wybraniu
legalnego celu. Gracz widzi ST, postać wykonującą test, wynik, HP i koszt tury.

Największe problemy:

1. czteroosobowa drużyna zatrzymuje się bez wyjaśnienia na setupie walki,
2. pending pułapki może „połknąć” następną deklarację,
3. dłuższe naturalne opisy bywają odrzucane, choć krótka komenda działa,
4. pusty zestaw celów ataku nie mówi wystarczająco jasno, czy problemem jest
   zasięg, LoS czy wyposażenie.

Ocena: **grywalne z osobą techniczną, jeszcze nie samodzielne dla nowej grupy**.

## Perspektywa zaawansowanego gracza

Na plus:

- custom buildy zachowują statystyki, ekwipunek, czary i inicjatywę,
- cantrip nie zużywa slotu,
- zasięg i LoS wpływają na legalność celu,
- draw/stow respektuje object interaction,
- ruch i akcja rozliczają się osobno,
- NPC używa authored DC i deterministycznej zmiany nastawienia.

Na minus:

- eksploracyjny Fire Bolt nie używa spell attack/damage przeciw obiektowi,
- model może podmienić wybrany item i jego właściciela,
- brak pola startowego jest zależny od authored template encounteru, a nie od
  liczebności wybranej drużyny.

Ocena: **rdzeń zasad walki jest wiarygodny, granica LLM–zasoby eksploracji nie**.

## Perspektywa techniczna i skalowanie

### Postacie

Builder i roster skalują się data-driven. Custom actor jest tym samym modelem,
który konsumują eksploracja i walka. Nie wykryto utraty czarów, ekwipunku ani
biegłości podczas handoffu.

### Encountery

Content authored dla konkretnej liczby bohaterów nie skaluje się automatycznie do
partii 1–5. Loader/content audit powinien sprawdzać pojemność strefy startowej,
a runtime potrzebuje polityki rozszerzenia pozycji albo limitu zależnego od
scenariusza pokazanego przed startem gry.

### Bronie, itemy i czary

Wspólny action-source contract upraszcza dodawanie contentu, ale zaufanie do
`used_resource_ids` zwróconego przez LLM podważa cały model. Źródło wybrane przez
gracza musi być niezmiennym inputem deterministycznego resolvera; Gemini może
opisać sposób użycia i dobrać dozwoloną trasę, lecz nie podmienić przedmiotu,
czaru, właściciela ani kosztu.

### Gemini

Typowe udane requesty trwały około 1,65–5,99 s. Niepoprawne payloady z retry
trwały około 8,98 s. Wystąpił jeden 429 po ponowieniach. Odpowiedzi NPC były
stabilniejsze od swobodnych deklaracji challenge.

## Priorytety

### P0

1. Generować/zweryfikować pola startowe encounteru dla rzeczywistej liczebności
   custom party 1–5.
2. Uszczelnić source binding: selected source, participant, owner i
   `used_resource_ids` muszą być jednym deterministycznym kontraktem.

### P1

1. Zablokować composer nowej akcji, gdy pułapka/hazard/observation ma pending.
2. Naprawić retry schematu `situational_modifiers`, aby poprawne naturalne opisy
   nie wymagały skracania do komendy.
3. Dodać w walce przyczynę braku legalnych celów i sugerowany następny krok.
4. Dodać provider retry/backoff oraz jasno określony checkpoint po wyniku akcji.
5. Walidować sprzeczność `available=true` z `unavailable_reason`.

### P2

1. Ujednolicić atakowanie destrukcyjnych fixture w eksploracji z AC/HP/damage
   broni i czarów albo jawnie udokumentować challenge-check jako odstępstwo.
2. Rozważyć prowadzony, etapowy kreator zamiast jednego długiego formularza.
3. Dokończyć manualny UI-5 na fizycznej planszy; ten test nie oceniał precyzji
   LED, wydruku A4 ani czytelności ekranu z normalnej odległości od stołu.

## Artefakty

- `data/session_observations/custom_party_gemini_1785233273.jsonl` — główny
  przebieg wioski i eksploracji,
- `data/session_observations/custom_party_gemini_1785233273_resume.jsonl` —
  brama, encounter, walka i NPC po walce,
- `data/session_observations/custom_party_gemini_item_probe.jsonl` — kontrolny
  przypadek niespójności selected source,
- `/tmp/custom_party_gemini_1785233273_result.json` — skrócony wynik głównego
  przebiegu,
- `/tmp/custom_party_gemini_1785233273_resume_result.json` — wynik walki i NPC.

Nie uruchamiano pytest, ponieważ zadaniem był playtest runtime z realnym Gemini,
a nie zmiana reguł. Skrypty diagnostyczne znajdowały się wyłącznie w `/tmp`.

## Follow-up implementacyjny

Po raporcie wdrożono wszystkie poprawki możliwe do zweryfikowania bez
fizycznego stołu:

- strefa startowa encounteru zachowuje authored pola, a następnie bezpiecznie
  rozszerza je do rzeczywistej liczby 1–5 bohaterów;
- źródło wybrane w UI jest wiążące dla właściciela, `used_resource_ids`,
  wymaganego przedmiotu i kosztu czaru; Gemini nie może podmienić go w
  resolverze;
- dostępne źródło nie pokazuje już tekstu `unavailable_reason`;
- backend odrzuca nową deklarację przy dowolnym pending, a frontend ukrywa
  composer i prowadzi do obowiązkowego kroku;
- odpowiedź klasyfikatora jest normalizowana przed walidacją: modelowe
  `situational_modifiers` i `roll_mode` są ignorowane, bo liczby pozostają
  własnością deterministycznego silnika;
- retry providera ma wykładniczy backoff z jitterem, a runtime zapisuje stabilny
  checkpoint po zakończonym rozstrzygnięciu eksploracyjnym;
- HUD walki wyjaśnia brak legalnego celu i sugeruje ruch, zmianę broni albo
  odzyskanie linii widzenia;
- challenge-check dla broni i czarów przeciw fixture został jawnie opisany w
  `GAME_DESIGN.md` jako świadoma abstrakcja eksploracyjna;
- kreator postaci jest prowadzonym formularzem pięcioetapowym.

Regresje automatyczne pokrywają partie 1/3/4/5, source binding, pending,
normalizację payloadu Gemini, checkpoint, onboarding walki i kreator. Pozostaje
manualne wykonanie UI-5 na fizycznej planszy według checklisty w
`docs/PLAYER_UI_DESIGN.md`; testów LED, wydruku i czytelności z odległości nie da
się rzetelnie zamknąć w samym środowisku programistycznym.

## Rekomendowany kolejny krok

Powtórzyć krótki pionowy wycinek z prawdziwym Gemini: fresh custom party → jedna
akcja itemem z próbą podmiany właściciela → start `gate_skirmish` czteroosobową
drużyną → jeden legalny atak → restart i wczytanie checkpointu. Następnie
wykonać manualny UI-5 na fizycznej planszy. Pełny scenariusz nie jest potrzebny
do regresji dwóch dawnych P0.

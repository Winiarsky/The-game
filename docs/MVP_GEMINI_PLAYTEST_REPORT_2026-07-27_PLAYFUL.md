# Raport: żartobliwy playtest MVP z Gemini

Data: 2026-07-27  
Model: `gemini-3.1-flash-lite`  
Zakres: wioska → handoff → brama → zwiadowca → walka i łup  
Tryb: prawdziwe requesty Gemini przez runtime sesji; bez przeglądarki i fizycznej
planszy w tej rundzie

## Werdykt

Warstwa rozmowy radzi sobie z żartobliwymi graczami znacznie lepiej niż podczas
poprzedniego testu. Gemini rozumie dowcip, odpowiada w podobnym tonie i zwykle nie
próbuje zamienić żartu w fakt świata. Deterministyczne granice także robią swoją
robotę: fałszywy czerwony smok nie stworzył nagrody, Healing Word zużył slot bez
testu Medycyny, a walka poprawnie przekazała łup do ekwipunku.

Nie można jednak jeszcze uznać przejścia wioska → strażnica za bezpieczną
referencję kampanii. Test odkrył dwa istotne problemy:

1. handoff zachowuje stan aktora ze sceny źródłowej kosztem jego statycznych
   możliwości ze sceny docelowej; Łotrzyca traci narzędzia i biegłości potrzebne
   do otwarcia zamka,
2. kontrola zablokowanych informacji pilnuje identyfikatorów, ale nie całej treści
   wygenerowanej wypowiedzi; Gemini przemyciło sugestię o starej zbroi przed
   formalnym odblokowaniem tropu klątwy komendanta.

To są problemy architektury przepływu, nie jakości samego scenariusza. Powinny
zostać naprawione przed rozpoczęciem masowej produkcji contentu.

## Przebieg

### 1. Sołtys i czerwony smok w kapeluszu

Gracze zapytali Brena, czy w strażnicy naprawdę mieszka czerwony smok w kapeluszu,
który zalega im sto sztuk złota.

Gemini rozpoznało żart, ale odpowiedziało wyłącznie autoryzowanymi faktami:
strażnica, gobliny i zagrożenie dla mieszkańców. W `gm_notes` wprost zaznaczyło,
że ignoruje zmyśloną historię. Po zaakceptowaniu:

- `quest_hook_found` zostało ustawione,
- stan złota Bohatera pozostał bez zmian: 10 gp,
- nie powstała nagroda, smok ani nowy fakt świata.

Wynik: **PASS**. Grounding ważnych faktów i ekonomii zadziałał.

Przyjęcie zadania i deklaracja wymarszu również zostały poprawnie sklasyfikowane
jako bezkostkowe `commitment` i `travel`. Gemini zachowało lekki ton, a stan celu
przeszedł dalej.

### 2. Handoff do strażnicy

Runtime uruchomił docelowy scenariusz i prawidłowo zastosował:

- czas przybycia 18:20,
- flagi `quest_hook_found`, `quest_accepted` i `watchtower_clean_approach`,
- outcome `prepared_watchtower_arrival`,
- docelową drużynę `hero`, `rogue`, `cleric`.

To potwierdza, że wcześniejszy brak consumera handoffu został naprawiony.

Pierwsza naturalna akcja w strażnicy — wybranie Łotrzycy do otwarcia zamka —
została jednak zablokowana komunikatem, że postać nie spełnia wymagań sposobu.
Przyczyna: aktor `rogue` z wioski zastąpił aktora `rogue` ze strażnicy jako niemal
cały obiekt. Zachował stan źródłowy, ale nie dostał docelowych narzędzi
złodziejskich i biegłości.

Wynik: **FAIL / P0**. Handoff działa transportowo, ale błędnie rozdziela dane
mutowalne i statyczne. Należy zachować HP, walutę, zużyte zasoby i zdobyty
ekwipunek, natomiast klasowe możliwości, biegłości, czary i bazowy loadout powinny
pochodzić z kanonicznej postaci albo zostać jawnie scalone.

### 3. Pan Łomot kontra brama

Pierwsza deklaracja nazwała dębową belkę „Panem Łomotem” i opisywała plan jako
subtelny niczym spadająca szafa. Gemini zwróciło pole `improvised_tool` w payloadzie
dla niewłaściwego rodzaju mechaniki. Walidator słusznie odrzucił propozycję i nie
zmienił stanu.

Mechanicznie: **PASS**.  
Doświadczenie gracza: **FAIL**.

Gracz zobaczył techniczny tekst:
`Pole improvised_tool jest dozwolone tylko dla improvised_tool_check`.
Odrzucona wypowiedź pozostała też w historii rozmowy. Runtime powinien sam
poprosić model o korektę albo pokazać prosty komunikat w rodzaju „Nie udało się
zinterpretować pomysłu — spróbuj ponownie”.

Druga, prostsza deklaracja wspólnego wyważania przeszła:

- Siła (Atletyka), ST 15,
- Bohater prowadził, Łotrzyca pomagała,
- przewaga,
- rzuty 17 i 12,
- wynik 23 i otwarcie bramy,
- hałas 2 oraz poprawnie zakolejkowany rzut obronny na linkę alarmową.

Gemini dodało jednak dwa własne modyfikatory liczbowe: +2 za spróchniałe drewno i
-1 za głośne wyważanie. Grounding zachował je, więc realnie zmieniły sumę rzutu.
To nie wpłynęło na ten wynik, ale przy rzucie granicznym LLM mógłby sam rozstrzygnąć
powodzenie. Model powinien wybierać tylko modyfikatory z listy autoryzowanej przez
content lub wymagać ich jawnego zatwierdzenia.

### 4. „Licencjonowane” Słowo leczenia

Kapłan oznajmił, że jest to licencjonowana magia, i rzucił przygotowane Healing
Word na zwiadowcę.

Gemini odpowiedziało naturalnie i w tonie sceny: zwiadowca zażartował z licencji,
ale nadal brzmiał jak poturbowana osoba, a nie generator dowcipów. Po akceptacji:

- nie wykonano testu Medycyny,
- zużyto jeden slot 1. poziomu,
- ustawiono `scout_treated`, `scout_stabilized` i `scout_trusts_party`,
- pojawił się komunikat, że czar zapewnia pomoc bez testu.

Wynik: **PASS**. Poprzedni błąd zamiany jawnie wybranego czaru na test umiejętności
jest naprawiony.

Pozostaje mniejsze tarcie: opis efektu czaru pojawia się już w podglądzie przed
akceptacją i faktycznym zużyciem slotu. Narrację wyniku należy odseparować od
narracji zamiaru.

### 5. Sowiogłowy napastnik

Pierwsze pytanie po leczeniu zostało prawidłowo zatrzymane, ponieważ brakowało
flagi `scout_calmed`. Samo leczenie i zaufanie nie wystarczają do ujawnienia tropu
bestii. Po odtworzeniu stanu uspokojonego zwiadowcy Gemini przygotowało test
Perswazji ST 10 i ujawniło dozwolone identyfikatory `tower_hint` oraz `beast_hint`.

Odpowiedź była klimatyczna i dobrze reagowała na żart gracza, ale zawierała
„odór starej zbroi i gnijącej dumy”. To semantycznie wskazuje na późniejszy
`commander_curse_hint`, mimo że model nie podał tego identyfikatora i nie były
spełnione wszystkie warunki jego ujawnienia.

Wynik: **PARTIAL / P0**. Kontrola listy `revealed_information_ids` nie wystarczy.
Krytyczne odpowiedzi powinny być parafrazą dokładnie wybranych, odblokowanych
faktów albo przechodzić kontrolę treści względem pozostałych zablokowanych tropów.

### 6. Walka i łup

W deterministycznym etapie końcowym pokonano oba gobliny i zastosowano wynik walki
do eksploracji:

- combat został zamknięty,
- Bohater otrzymał 10 sp,
- do ekwipunku trafiły dwie fiolki osłabiającej trucizny,
- pojawiło się czytelne podsumowanie zabezpieczonego łupu.

Wynik: **PASS**. Pętla pokonany przeciwnik → łup → ekwipunek działa.

Osobne regresje potwierdziły też, że:

- nieudane rozbrojenie pułapki kolejkuje rzut obronny i zwiększa alarm,
- ukryta skrytka staje się źródłem łupu dopiero po odkryciu jej punktu.

## Perspektywa graczy

Początkujący gracz dostałby czytelne prowadzenie przy czarze, bramie, rzucie i
łupie. Największym problemem byłby techniczny błąd walidacji oraz nieoczekiwany
brak kompetencji Łotrzycy po zmianie sceny.

Zaawansowany gracz doceni Help, przewagę, jawne ST, slot czaru i trwały loot.
Jednocześnie zauważy, że Gemini nadal posiada zbyt dużą władzę nad liczbowymi
modyfikatorami testu.

Żartobliwa drużyna może mówić naturalnym językiem. System nie wymaga sztywnych
komend, a NPC potrafią odpowiedzieć z lekkim humorem bez rozwalania tonu sceny.
Najlepiej działa to w rozmowach. Bardziej złożone żarty połączone z użyciem
przedmiotu nadal zwiększają ryzyko niepoprawnego payloadu.

## Perspektywa techniczna i skalowanie

- Prawdziwe odpowiedzi Gemini trwały w tej próbie około 23–31 sekund. UI potrzebuje
  jednoznacznego stanu „MG myśli”, timeoutu i bezpiecznego retry.
- Guardy stanu i ekonomii są skuteczne, lecz walidacja mechaniczna nie gwarantuje
  braku spoilerów w swobodnym tekście.
- Scalanie całych dataclass aktorów między scenami nie skaluje się do kampanii.
  Potrzebny jest jawny model kanonicznej postaci i osobny zapis jej mutowalnego
  stanu.
- LLM może pozostać klasyfikatorem i parafrazatorem, ale liczby oraz zakres
  odblokowanej wiedzy muszą pozostać deterministyczne.

## Priorytety

### P0 — przed następnym pełnym przejściem

1. Naprawić merge aktorów podczas handoffu.
2. Uszczelnić semantyczne ujawnianie zablokowanych informacji NPC.

### P1 — przed uznaniem MVP za wygodne dla nowych graczy

1. Ukryć techniczne błędy schematu Gemini i automatycznie ponawiać bezpieczną
   klasyfikację.
2. Nie zapisywać odrzuconej deklaracji jako poprawnej części rozmowy.
3. Ograniczyć modyfikatory liczbowe do źródeł authored/approved.
4. Pokazywać wynik narracyjny dopiero po akceptacji kosztu lub rzutu.
5. Dodać czytelny loading, timeout i retry dla wolnych odpowiedzi modelu.

## Artefakty i weryfikacja

Logi sesji:

- `data/session_observations/gemini_fun_retest_20260727.jsonl`
- `data/session_observations/gemini_fun_gate_stage_20260727.jsonl`
- `data/session_observations/gemini_fun_npc_stage_20260727.jsonl`
- `data/session_observations/gemini_fun_npc_question_20260727.jsonl`
- `data/session_observations/gemini_fun_combat_stage_20260727.jsonl`

Uruchomione testy:

```text
tests/unit/test_exploration_ui_session.py::test_failed_trap_disarm_queues_save_and_adds_alarm_noise
tests/unit/test_exploration_ui_session.py::test_hidden_cache_becomes_a_lootable_fixture_only_after_its_point_is_revealed
2 passed in 1.14s
```

Końcowa ocena: **mechaniki pojedynczych scen są blisko referencyjnego MVP, ale
ciągłość postaci i ochrona zablokowanego contentu wymagają jeszcze jednego cyklu
napraw przed kolejnym pełnym testem od początku do końca.**

## Follow-up implementacyjny

Po raporcie wdrożono jego P0 i P1:

- handoff scala mutowalny stan źródłowy z kanonicznymi możliwościami aktora sceny
  docelowej; Łotrzyca zachowuje narzędzia złodziejskie i pełny loadout,
- guarded NPC prompt nie zawiera prywatnego `gm_context`, ukrytych key issues ani
  nadal zablokowanych informacji,
- ujawniany tekst jest deterministycznie ograniczony do autoryzowanych faktów,
- niepoprawny payload LLM otrzymuje jedną automatyczną próbę korekty, a po niej
  wyłącznie nietechniczny komunikat dla gracza,
- odrzucona deklaracja znika z widocznej historii, pozostając tylko w technicznym
  kontekście korekty,
- modyfikatory liczbowe LLM są usuwane; pozostają wyłącznie źródła authored/runtime,
- odpowiedź NPC i narracja skutku pojawiają się po akceptacji oraz rozstrzygnięciu,
- czysto kosmetyczna rozmowa bez skutków nie wymaga dodatkowej akceptacji,
- UI pokazuje przedłużające się oczekiwanie i przycisk bezpiecznego ponowienia,
- payload ruchu nie powiela pełnej trasy dla każdego osiągalnego pola,
- deklaracja wysłana bez aktywnej interakcji kończy się wskazówką dla gracza,
  a nie technicznym błędem i fałszywym wpisem w historii,
- ekran końcowy pokazuje cele, zabezpieczone łupy oraz dostępny przycisk
  rozpoczęcia scenariusza ponownie.

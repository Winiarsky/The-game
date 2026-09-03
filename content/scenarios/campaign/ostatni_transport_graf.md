# Ostatni transport do Czarnego Brodu — edytowalny graf przygody

Status: roboczy graf logiczny v1  
Źródło: `Ostatni transport do Czarnego Brodu.pdf`  
Docelowa drużyna: 3–5 bohaterów poziomu 3, wybieranych spośród siedmiu
bohaterów startowych.

Kanon roboczy organizacji zlecającej kampanię opisuje dokument
[`GILDIA_SZLAKOW_I_EKSPEDYCJI.md`](GILDIA_SZLAKOW_I_EKSPEDYCJI.md).
Techniczną specyfikację Mapy 0 i odprawy Nessy rozwijamy w
[`MAPA_0_GILDIA_NESSA_SPEC.md`](MAPA_0_GILDIA_NESSA_SPEC.md).

Ten dokument jest tekstowym źródłem diagramów Mermaid. Można go poprawiać
ręcznie bez edytora graficznego i generować z niego plik `.drawio`, w którym
pozycje węzłów można swobodnie zmieniać myszą.

Wielostronicowa, interaktywna wersja znajduje się w
[`ostatni_transport_graf.drawio`](ostatni_transport_graf.drawio). Każdy węzeł,
kontener i łącznik jest w niej osobnym obiektem, który można przesuwać,
edytować, łączyć i zwijać. Plik można otworzyć w diagrams.net, aplikacji
draw.io albo odpowiednim rozszerzeniu VS Code.

Po zmianie logicznego źródła Mermaid wersję draw.io można odtworzyć poleceniem:

```bash
python scripts/generate_campaign_drawio.py
```

Ponowne wygenerowanie pliku nadpisuje ręczne ustawienie obiektów w `.drawio`.
Dlatego po rozpoczęciu ręcznej pracy graficznej należy traktować `.drawio` jako
wersję roboczą, a generator uruchamiać tylko świadomie po zmianach struktury.

## Jak czytać graf

### Typy węzłów

```mermaid
flowchart LR
    map[["MAPA / PACZKA SCENARIUSZA"]]
    tile["KAFEL GRACZA"]
    npc(["NPC"])
    instance(["INSTANCJA / LOKACJA"])
    interaction["INTERAKCJA / OBIEKT"]
    combat{{"WALKA / ZAGROŻENIE"}}
    hero[["MOMENT BOHATERA"]]
    decision{"DECYZJA"}
    transition(["PRZEJŚCIE"])
    clue["TROP / INFORMACJA"]
    resource[("ZASÓB / STAN")]
    inactive["PLACEHOLDER · JESZCZE NIEAKTYWNY"]

    classDef map fill:#172554,color:#ffffff,stroke:#60a5fa,stroke-width:3px;
    classDef tile fill:#d9f99d,color:#1a2e05,stroke:#4d7c0f,stroke-width:3px;
    classDef npc fill:#dbeafe,color:#172554,stroke:#2563eb,stroke-width:2px;
    classDef instance fill:#fef3c7,color:#451a03,stroke:#d97706,stroke-width:2px;
    classDef interaction fill:#ccfbf1,color:#134e4a,stroke:#0f766e,stroke-width:2px;
    classDef combat fill:#fee2e2,color:#450a0a,stroke:#dc2626,stroke-width:3px;
    classDef hero fill:#f3e8ff,color:#3b0764,stroke:#9333ea,stroke-width:2px;
    classDef decision fill:#ffedd5,color:#431407,stroke:#ea580c,stroke-width:2px;
    classDef transition fill:#dcfce7,color:#052e16,stroke:#16a34a,stroke-width:3px;
    classDef clue fill:#ecfeff,color:#164e63,stroke:#0891b2,stroke-width:2px;
    classDef resource fill:#f1f5f9,color:#0f172a,stroke:#475569,stroke-width:2px;
    classDef inactive fill:#e5e7eb,color:#4b5563,stroke:#9ca3af,stroke-width:2px,stroke-dasharray:5 5;

    class map map;
    class tile tile;
    class npc npc;
    class instance instance;
    class interaction interaction;
    class combat combat;
    class hero hero;
    class decision decision;
    class transition transition;
    class clue clue;
    class resource resource;
    class inactive inactive;
```

### Typy połączeń

- `A → B` — zwykła kolejność albo odblokowanie;
- `A ⇢ B` — główne przejście między mapami;
- linia przerywana — droga opcjonalna, moment bohatera albo dodatkowy trop;
- podpis na strzałce — warunek, koszt albo skutek przejścia;
- kilka strzałek wchodzących do decyzji nie oznacza, że wszystkie są
  wymagane; wymagania są jawnie podpisane.

### Co na diagramie jest kafelkiem gracza

Zielony węzeł `KAFEL` jest wyborem widocznym w interfejsie i przypisanym do
pola interakcji na planszy. Opisuje cel gracza, nie cały dialog ani techniczną
metodę wykonania. Przykładowo kafelek `Poznaj wersję Marka` może otworzyć
rozmowę z kilkoma pytaniami, próbą przekonania i różnymi reakcjami NPC, ale graf
kampanii nie rozpisuje tych wewnętrznych kroków.

Diagram przybliżenia pokazuje pełną pulę możliwych kafelków. Runtime ma
jednocześnie pokazywać najwyżej siedem działań wraz z czerwonym wyjściem.
Kafelki zakończone znikają, a warunkowe pojawiają się dopiero po spełnieniu
opisanej flagi, odkryciu informacji albo obecności odpowiedniego bohatera.

## Założone uproszczenia względem PDF-u

1. Przygoda jest podzielona na cztery paczki scenariusza, a nie jeden monolit.
2. Siedziba Gildii jest osobną, wielokrotnego użytku Mapą 0. Otwiera kampanię,
   a po finale przyjmuje raport i zapisuje długoterminowe konsekwencje.
3. Podróż do zawalonej drogi jest krótkim montażem i wyborem, nie osobną
   czwartą mapą.
4. Głodne Cienie to jedno stado z przywódcą i morale. Nie trzeba pokonać
   każdej bestii, aby zakończyć encounter.
5. Tłum w strażnicy jest licznikiem paniki/stanu strefy. Fizyczne pionki mają
   tylko Marek, Alven, Salka i ewentualnie jedna grupa cywilów.
6. Osobiste momenty bohaterów są opcjonalne i widoczne tylko wtedy, gdy dany
   bohater znajduje się w drużynie.
7. Żaden obowiązkowy cel nie wymaga konkretnego bohatera. Bohater może dawać
   najlepszą albo tańszą drogę, ale zawsze istnieje alternatywa.
8. Dynamiczna woda w Cysternie jest podzielona na kilka stanów/stref, a nie
   zmienia każdego pola mapy co rundę.
9. Zakłócanie magii przez Rezonans będzie jawną zdolnością z rzutem obronnym
   albo testem koncentracji, nie losowym anulowaniem kart.
10. Każda z czterech skrzyń pyłu ma własny, policzalny stan.

## Tempo pierwszej podróży

Droga z Gildii do zawalonego traktu ma bazowo 60 minut. Wybór tempa jest
decyzją między czasem a przygotowaniem do najbliższej walki, a nie wyłącznie
kosmetycznym mnożnikiem:

| Tempo | Udana nawigacja | Otwarcie walki z Głodnymi Cieniami | Stan dla dalszych map |
| --- | ---: | --- | --- |
| Szybkie | 45 min | bez ostrzeżenia Erynda przeciwnicy mają przewagę do inicjatywy; ostrzeżenie tylko neutralizuje zasadzkę | `travel.arrival.early`, jeśli nie było opóźnienia |
| Normalne | 60 min | domyślnie bez przewagi; ostrzeżenie Erynda daje przewagę drużynie | `travel.arrival.on_time` |
| Wolne | 80 min | drużyna może wykonać Stealth; z ostrzeżeniem Erynda ma również przewagę do inicjatywy | `travel.arrival.late` |

Test Wisdom (Survival) ST 12 rozstrzyga nawigację. Porażka nie blokuje
przygody, ale dodaje 30 minut i ponownie wylicza okno przybycia. Handoff zapisuje
też `travel.total_minutes`, `travel.schedule_delta_minutes`, wynik nawigacji,
modyfikator Pasywnej Percepcji i dostępność skradania. Późniejsze mapy mają
używać okna przybycia do stanu tropów, ocalałych i czasu uzyskanego przez
przeciwników; konkretne gałęzie należy uruchamiać dopiero wraz z ich contentem.

---

# Graf całej przygody

```mermaid
flowchart LR
    START(["START KAMPANII"])

    subgraph ACT0["PACZKA 0 · SIEDZIBA GILDII"]
        GUILD[["MAPA 0 · SIEDZIBA GILDII"]]
        INTRO["Intro narratora"]
        NESSA(["NPC · Nessa Vel"])
        BRIEFING["Obowiązkowa odprawa"]
        QUEST_ACTIVE["Stan · kontrakt aktywny"]
        DEPARTURE(["Brama wyjazdowa"])
        HANDOFF0(["Handoff 00 → 01"])
        GUILD_RETURN[["POWRÓT · MAPA 0"]]
        REPORT(["Raport dla Nessy"])
        ARCHIVE["Archiwum · zapis następstw"]
        EPILOG(["Epilog i konsekwencje kampanii"])
    end

    subgraph ACT1["PACZKA 1 · ZAWALONA DROGA"]
        TRAVEL["Montaż drogi przez zerwane szlaki"]
        ROAD[["MAPA 1 · ZAWALONA DROGA"]]
        TEREN(["Teren · ranny strażnik"])
        WAGON(["Przewrócony wóz i tropy"])
        SHADOWS{{"Głodne Cienie"}}
        ROUTE{"Wybrać drogę do strażnicy"}
        HANDOFF1(["Handoff 01 → 02"])
    end

    subgraph ACT2["PACZKA 2 · CZARNY BRÓD"]
        KEEP[["MAPA 2 · STRAŻNICA CZARNEGO BRODU"]]
        GATE(["Brama i pierwszy kontakt"])
        APPROACH{"Negocjacje, infiltracja czy atak?"}
        MARK(["Marek Venn"])
        ALVEN(["Alven Rost"])
        SALKA(["Salka"])
        KEEP_TRUTH["Prawda o transporcie, chorobie i Raven"]
        DESCENT{"Czy i jak zejść do Cysterny?"}
        HANDOFF2(["Handoff 02 → 03"])
    end

    subgraph ACT3["PACZKA 3 · GŁODNY REZONANS"]
        CISTERN[["MAPA 3 · PODZIEMNA CYSTERNA"]]
        RESONANCE{{"Głodny Rezonans"}}
        VALVES["Trzy zawory i poziom wody"]
        RITUAL["Komora rytualna i pęknięcie"]
        TACTICAL_END{"Jak zakończyć zagrożenie?"}
        DUST_DECISION{"Komu przypadnie szary pył?"}
        HANDOFF3(["Handoff 03 → 00"])
    end

    START ==> GUILD --> INTRO --> NESSA --> BRIEFING --> QUEST_ACTIVE
    QUEST_ACTIVE --> DEPARTURE ==> HANDOFF0 ==> TRAVEL ==> ROAD
    ROAD --> WAGON
    ROAD --> TEREN
    ROAD --> SHADOWS
    WAGON --> ROUTE
    TEREN --> ROUTE
    SHADOWS --> ROUTE
    ROUTE ==> HANDOFF1 ==> KEEP

    KEEP --> GATE --> APPROACH
    APPROACH --> MARK
    APPROACH --> ALVEN
    APPROACH --> SALKA
    MARK --> KEEP_TRUTH
    ALVEN --> KEEP_TRUTH
    SALKA --> KEEP_TRUTH
    KEEP_TRUTH --> DESCENT ==> HANDOFF2 ==> CISTERN

    CISTERN --> RESONANCE
    CISTERN --> VALVES
    CISTERN --> RITUAL
    RESONANCE --> TACTICAL_END
    VALVES --> TACTICAL_END
    RITUAL --> TACTICAL_END
    TACTICAL_END --> DUST_DECISION ==> HANDOFF3 ==> GUILD_RETURN
    GUILD_RETURN --> REPORT --> ARCHIVE --> EPILOG

    classDef map fill:#172554,color:#ffffff,stroke:#60a5fa,stroke-width:3px;
    classDef npc fill:#dbeafe,color:#172554,stroke:#2563eb,stroke-width:2px;
    classDef instance fill:#fef3c7,color:#451a03,stroke:#d97706,stroke-width:2px;
    classDef interaction fill:#ccfbf1,color:#134e4a,stroke:#0f766e,stroke-width:2px;
    classDef combat fill:#fee2e2,color:#450a0a,stroke:#dc2626,stroke-width:3px;
    classDef decision fill:#ffedd5,color:#431407,stroke:#ea580c,stroke-width:2px;
    classDef transition fill:#dcfce7,color:#052e16,stroke:#16a34a,stroke-width:3px;
    classDef clue fill:#ecfeff,color:#164e63,stroke:#0891b2,stroke-width:2px;

    class GUILD,GUILD_RETURN,ROAD,KEEP,CISTERN map;
    class NESSA,TEREN,MARK,ALVEN,SALKA npc;
    class DEPARTURE,GATE instance;
    class INTRO,BRIEFING,TRAVEL,WAGON,VALVES,RITUAL,ARCHIVE interaction;
    class SHADOWS,RESONANCE combat;
    class ROUTE,APPROACH,DESCENT,TACTICAL_END,DUST_DECISION decision;
    class START,HANDOFF0,HANDOFF1,HANDOFF2,HANDOFF3,REPORT,EPILOG transition;
    class QUEST_ACTIVE,KEEP_TRUTH clue;
```

---

# Mapa 0 — Siedziba Gildii

Mapa 0 jest ekranem-bazą w konwencji point-and-click, a nie planem budynku do
swobodnego chodzenia. Ilustracja pokazuje sześć czytelnych miejsc, lecz w
pierwszej wersji mechanicznie działają tylko Nessa i brama wyjazdowa. Pozostałe
obszary rezerwują kompozycję pod przyszły rozwój, ale nie mają jeszcze pól LED,
skanów ani pustych menu.

## Główny przepływ

```mermaid
flowchart TB
    START(["Start kampanii"])
    NARRATOR["Intro narratora · rola Gildii i sytuacja na szlakach"]

    subgraph HUB["MAPA 0 · SIEDZIBA GILDII · 20×30"]
        MAP0[["Widok główny bazy"]]
        NESSA(["NPC · Nessa Vel · aktywna od początku"])
        DEPARTURE(["Instancja · Brama i dziedziniec wyjazdowy"])
        QUARTERMASTER["Placeholder · Kwatermistrz"]
        TRAINING["Placeholder · Plac treningowy"]
        QUARTERS["Placeholder · Kwatery i sala wspólna"]
        ARCHIVE["Placeholder · Archiwum Następstw i Kartografii"]
    end

    subgraph BRIEFING["INSTANCJA · BIURO NESSY"]
        ENTER_NESSA["Wejście A→A · otwórz instancję"]
        CORE["Automatyczna odprawa · transport zaginął pod Czarnym Brodem"]
        QUEST["Stan · aktywuj kontrakt"]
        OBJECTIVES["Cele · znajdź wozy, odzyskaj ładunek,<br/>sprowadź ocalałych, ustal przebieg zdarzeń"]
        OPTIONAL["Opcjonalne kafelki · informacje, dokumenty,<br/>negocjacje i odczytanie intencji Nessy"]
        FINISH["KAFEL · Zakończ odprawę"]
        CHECKPOINT["Checkpoint · briefing_complete"]
    end

    subgraph LEAVE["INSTANCJA · BRAMA WYJAZDOWA"]
        UNLOCK["Odblokuj i podświetl bramę"]
        PREVIEW["Pierwsze A · podgląd celu i stanu przygotowania"]
        CONFIRM["Drugie A · Wyrusz w drogę"]
        HANDOFF(["Handoff Mapy 0 → Mapy 1"])
    end

    START --> NARRATOR ==> MAP0
    MAP0 --> NESSA --> ENTER_NESSA --> CORE --> QUEST --> OBJECTIVES
    OBJECTIVES --> OPTIONAL --> FINISH
    OBJECTIVES --> FINISH
    FINISH --> CHECKPOINT ==> MAP0
    CHECKPOINT --> UNLOCK --> DEPARTURE
    DEPARTURE --> PREVIEW --> CONFIRM ==> HANDOFF

    MAP0 -.-> QUARTERMASTER
    MAP0 -.-> TRAINING
    MAP0 -.-> QUARTERS
    MAP0 -.-> ARCHIVE

    classDef map fill:#172554,color:#ffffff,stroke:#60a5fa,stroke-width:3px;
    classDef npc fill:#dbeafe,color:#172554,stroke:#2563eb,stroke-width:2px;
    classDef instance fill:#fef3c7,color:#451a03,stroke:#d97706,stroke-width:2px;
    classDef interaction fill:#ccfbf1,color:#134e4a,stroke:#0f766e,stroke-width:2px;
    classDef tile fill:#d9f99d,color:#1a2e05,stroke:#4d7c0f,stroke-width:3px;
    classDef transition fill:#dcfce7,color:#052e16,stroke:#16a34a,stroke-width:3px;
    classDef clue fill:#ecfeff,color:#164e63,stroke:#0891b2,stroke-width:2px;
    classDef inactive fill:#e5e7eb,color:#4b5563,stroke:#9ca3af,stroke-width:2px,stroke-dasharray:5 5;

    class MAP0 map;
    class NESSA npc;
    class DEPARTURE instance;
    class NARRATOR,ENTER_NESSA,CORE,OPTIONAL,UNLOCK,PREVIEW interaction;
    class FINISH,CONFIRM tile;
    class START,CHECKPOINT,HANDOFF transition;
    class QUEST,OBJECTIVES clue;
    class QUARTERMASTER,TRAINING,QUARTERS,ARCHIVE inactive;
```

## Przybliżenie: kafelki gracza na Mapie 0

```mermaid
flowchart LR
    subgraph HUB_TILES["WIDOK GŁÓWNY · SIEDZIBA GILDII"]
        HUB(["Mapa bazy"])
        H_NESSA["PUNKT AKTYWNY · Nessa"]
        H_DEPARTURE["PUNKT WARUNKOWY · Brama wyjazdowa"]
        H_QUARTERMASTER["PLACEHOLDER · Kwatermistrz"]
        H_TRAINING["PLACEHOLDER · Plac treningowy"]
        H_QUARTERS["PLACEHOLDER · Kwatery"]
        H_ARCHIVE["PLACEHOLDER · Archiwum"]
    end

    subgraph NESSA_TILES["INSTANCJA · NESSA · MAKSYMALNIE 7 KAFELKÓW"]
        NESSA(["Nessa Vel"])
        N_MISSING["KAFEL · Co wiadomo o zaginięciu?"]
        N_CARGO["KAFEL · Co przewoził transport?"]
        N_PEOPLE["KAFEL · Kto podróżował z karawaną?"]
        N_PAY["KAFEL · Negocjuj wynagrodzenie"]
        N_INSIGHT["KAFEL · Oceń prawdziwe priorytety Nessy"]
        N_DOCS["KAFEL BOHATERA · Erynd: Przejrzyj papiery przewozowe"]
        N_FINISH["KAFEL · Zakończ odprawę"]
    end

    subgraph OUTCOMES["SKUTKI · BEZ ROZPISYWANIA CAŁYCH DIALOGÓW"]
        O_MISSING["Trop · ostatni sygnał i miejsce zaginięcia"]
        O_CARGO["Trop · lekarstwa oraz cztery skrzynie szarego pyłu"]
        O_PEOPLE["Zasób · lista załogi, pasażerów i rachmistrza"]
        O_PAY["Stan · wynegocjowana zaliczka lub premia za ocalałych"]
        O_INSIGHT["Trop · skrzynie są dla Nessy ważniejsze niż przyznaje"]
        O_DOCS["Trop PO SUKCESIE · na trasie prawdopodobnie działa magia"]
        O_FINISH["Stan · briefing_complete i aktywna brama"]
    end

    subgraph DEPARTURE_TILES["INSTANCJA · BRAMA WYJAZDOWA"]
        GATE(["Brama"])
        D_PREVIEW["KAFEL · Sprawdź cel wyprawy"]
        D_GO["KAFEL · Wyrusz w drogę"]
        D_BACK["WYJŚCIE · Wróć do bazy"]
    end

    HUB --> H_NESSA
    HUB -.-> H_DEPARTURE
    HUB -.-> H_QUARTERMASTER
    HUB -.-> H_TRAINING
    HUB -.-> H_QUARTERS
    HUB -.-> H_ARCHIVE

    H_NESSA ==> NESSA
    NESSA --> N_MISSING --> O_MISSING
    NESSA --> N_CARGO --> O_CARGO
    NESSA --> N_PEOPLE --> O_PEOPLE
    NESSA --> N_PAY --> O_PAY
    NESSA --> N_INSIGHT --> O_INSIGHT
    NESSA -.-> N_DOCS --> O_DOCS
    NESSA --> N_FINISH --> O_FINISH
    O_FINISH ==> H_DEPARTURE ==> GATE
    GATE --> D_PREVIEW
    GATE --> D_GO
    GATE --> D_BACK

    classDef npc fill:#dbeafe,color:#172554,stroke:#2563eb,stroke-width:2px;
    classDef instance fill:#fef3c7,color:#451a03,stroke:#d97706,stroke-width:2px;
    classDef tile fill:#d9f99d,color:#1a2e05,stroke:#4d7c0f,stroke-width:3px;
    classDef exit fill:#fee2e2,color:#450a0a,stroke:#dc2626,stroke-width:3px;
    classDef clue fill:#ecfeff,color:#164e63,stroke:#0891b2,stroke-width:2px;
    classDef resource fill:#f1f5f9,color:#0f172a,stroke:#475569,stroke-width:2px;
    classDef hero fill:#f3e8ff,color:#3b0764,stroke:#9333ea,stroke-width:2px;
    classDef inactive fill:#e5e7eb,color:#4b5563,stroke:#9ca3af,stroke-width:2px,stroke-dasharray:5 5;

    class NESSA npc;
    class HUB,GATE instance;
    class N_MISSING,N_CARGO,N_PEOPLE,N_PAY,N_INSIGHT,N_FINISH,D_PREVIEW,D_GO tile;
    class D_BACK exit;
    class O_MISSING,O_CARGO,O_INSIGHT,O_DOCS clue;
    class O_PEOPLE resource;
    class N_DOCS hero;
    class O_PAY,O_FINISH,H_NESSA,H_DEPARTURE interaction;
    class H_QUARTERMASTER,H_TRAINING,H_QUARTERS,H_ARCHIVE inactive;
```

Mapa powinna mieć dwa aktywne znaczniki runtime, ale nie jednocześnie: przed
odprawą pulsuje Nessa, po jej zakończeniu zaczyna pulsować brama. Cztery
placeholdery pozostają elementami ilustracji. Archiwum po przyszłym wdrożeniu
ma prezentować zapis długoterminowych następstw decyzji, odkrytych faktów i
zmian w świecie, a nie być kolejną tablicą zadań.

---

# Mapa 1 — Zawalona Droga

## Główny przepływ

```mermaid
flowchart TB
    subgraph JOURNEY["MONTAŻ PODRÓŻY · BEZ OSOBNEJ MAPY"]
        FROM_GUILD(["Handoff Mapy 0 → Mapy 1"])
        WORLD["Klimat · spalone posterunki, uchodźcy,<br/>obce mundury, drożejąca żywność"]
        ANOMALY["Trop · dźwięk biegnie z niewłaściwego kierunku"]
        ERYND_SIGN["Trop · zwierzęta omijają okolice brodu"]
        NIMRA_SIGN["Trop · nieregularne impulsy magiczne"]
        ARRIVAL(["Przejście · przybycie do wąwozu"])
    end

    subgraph MAP1["MAPA 1 · ZAWALONA DROGA · 20×30"]
        ENTRY(["Instancja · Wejście do wąwozu"])

        WAGON(["Instancja · Przewrócony wóz<br/>osłona i częściowa blokada drogi"])
        SEARCH_WAGON["Interakcja · Przeszukaj wóz"]
        MOVE_WAGON["Interakcja · Przesuń wóz"]
        SALVAGE_WAGON["Interakcja · Rozbierz na materiały"]
        BARRICADE_WAGON["Interakcja · Ustaw barykadę"]
        MANIFEST[("Zasób · manifest transportowy")]
        MEDICINE[("Zasób · ukryta paczka lekarstw")]
        BLOOD["Trop · ślady krwi i puste skrzynki"]

        SLOPE(["Instancja · Zawalona skarpa"])
        CLIMB["Interakcja · Wejdź na wysokość<br/>porażka: ruch lub osunięcie, nie blokada"]

        CULVERT(["Instancja · Stary przepust"])
        FIND_CULVERT["Trop · Znajdź wejście"]
        SNEAK_CULVERT["Interakcja · Przejdź pojedynczo i cicho"]

        TOWER(["Instancja · Wieża sygnałowa"])
        PLATFORM["Interakcja · Wejdź na platformę"]
        BELL["Interakcja · Użyj starego dzwonu"]
        CUT_SUPPORTS["Interakcja · Przetnij podpory"]
        STONE_BARREL["Interakcja · Zepchnij beczkę kamieni"]

        STREAM(["Instancja · Boczne zejście do strumienia<br/>trudny teren i obejście"])
        TRACKS["Trop · świeże ślady ku strażnicy"]

        TEREN(["NPC · Teren<br/>ranny, odwodniony, przerażony"])
        AID_TEREN["Interakcja · Opatrz ranę"]
        WATER_TEREN["Interakcja · Daj wodę lub lekarstwo"]
        QUESTION_TEREN["Interakcja · Uspokój i wypytaj"]
        ORDER_TEREN["Interakcja · Zdecyduj, czy może iść"]
        TEREN_LIE["Trop · wersja Terena jest niepełna"]
        TEREN_TRUTH["Trop · strażnicy chcieli odebrać wodę;<br/>bójka poprzedziła atak zwierząt"]
        SINGING_WELL["Trop · pasterz mówił o „śpiewającej studni”"]

        PACK{{"Encounter · Głodne Cienie<br/>wypaczone, głodne stado"}}
        PACK_CHOICE{"Jak poradzić sobie ze stadem?"}
        FIGHT["Walka · wykorzystaj teren i osłony"]
        FOOD["Interakcja · Odciągnij jedzeniem"]
        FIRE["Interakcja · Odstrasz ogniem"]
        RING_BELL["Interakcja · Użyj dzwonu"]
        BYPASS["Interakcja · Obejdź przepustem lub strumieniem"]
        CALM["Interakcja · Uspokój wiedzą łowiecką lub magią"]
        MORALE["Stan · stado ucieka po utracie przywódcy<br/>albo przełamaniu morale"]
        YOUNG_BEAST{"Decyzja · Co zrobić z młodą bestią?"}
        SPARE["Pozostaw lub ulecz<br/>późniejsza reakcja Salki/uchodźców"]
        KILL["Dobij<br/>późniejsza reakcja Terena/uchodźców"]

        ROUTE_DECISION{"Decyzja · Droga do Czarnego Brodu"}
        MAIN_ROUTE["Główny trakt<br/>szybciej, ale drużynę widać"]
        FOREST_ROUTE["Leśny szlak<br/>wolniej, blisko źródła anomalii"]
        TO_KEEP(["Przejście · handoff do Mapy 2"])
    end

    FROM_GUILD ==> WORLD --> ANOMALY --> ARRIVAL
    WORLD -.-> ERYND_SIGN --> ARRIVAL
    WORLD -.-> NIMRA_SIGN --> ARRIVAL

    ARRIVAL ==> ENTRY
    ENTRY --> WAGON
    ENTRY --> SLOPE
    ENTRY --> CULVERT
    ENTRY --> TOWER
    ENTRY --> STREAM
    ENTRY --> TEREN
    ENTRY --> PACK

    WAGON --> SEARCH_WAGON
    WAGON --> MOVE_WAGON
    WAGON --> SALVAGE_WAGON
    WAGON --> BARRICADE_WAGON
    SEARCH_WAGON --> MANIFEST
    SEARCH_WAGON --> MEDICINE
    SEARCH_WAGON --> BLOOD

    SLOPE --> CLIMB
    CULVERT --> FIND_CULVERT --> SNEAK_CULVERT
    TOWER --> PLATFORM
    TOWER --> BELL
    TOWER --> CUT_SUPPORTS
    TOWER --> STONE_BARREL
    STREAM --> TRACKS

    TEREN --> AID_TEREN
    TEREN --> WATER_TEREN
    TEREN --> QUESTION_TEREN
    TEREN --> ORDER_TEREN
    QUESTION_TEREN --> TEREN_LIE
    QUESTION_TEREN -->|zaufanie lub cierpliwość| TEREN_TRUTH
    QUESTION_TEREN --> SINGING_WELL

    PACK --> PACK_CHOICE
    PACK_CHOICE --> FIGHT --> MORALE
    PACK_CHOICE --> FOOD --> MORALE
    PACK_CHOICE --> FIRE --> MORALE
    PACK_CHOICE --> RING_BELL --> MORALE
    PACK_CHOICE --> BYPASS
    PACK_CHOICE --> CALM --> MORALE
    BELL -.-> RING_BELL
    SNEAK_CULVERT -.-> BYPASS
    STREAM -.-> BYPASS
    MORALE --> YOUNG_BEAST
    YOUNG_BEAST --> SPARE
    YOUNG_BEAST --> KILL

    MANIFEST --> ROUTE_DECISION
    TEREN_LIE --> ROUTE_DECISION
    TEREN_TRUTH --> ROUTE_DECISION
    TRACKS --> ROUTE_DECISION
    BYPASS --> ROUTE_DECISION
    SPARE --> ROUTE_DECISION
    KILL --> ROUTE_DECISION
    ROUTE_DECISION --> MAIN_ROUTE --> TO_KEEP
    ROUTE_DECISION --> FOREST_ROUTE --> TO_KEEP

    classDef npc fill:#dbeafe,color:#172554,stroke:#2563eb,stroke-width:2px;
    classDef instance fill:#fef3c7,color:#451a03,stroke:#d97706,stroke-width:2px;
    classDef interaction fill:#ccfbf1,color:#134e4a,stroke:#0f766e,stroke-width:2px;
    classDef combat fill:#fee2e2,color:#450a0a,stroke:#dc2626,stroke-width:3px;
    classDef decision fill:#ffedd5,color:#431407,stroke:#ea580c,stroke-width:2px;
    classDef transition fill:#dcfce7,color:#052e16,stroke:#16a34a,stroke-width:3px;
    classDef clue fill:#ecfeff,color:#164e63,stroke:#0891b2,stroke-width:2px;
    classDef resource fill:#f1f5f9,color:#0f172a,stroke:#475569,stroke-width:2px;

    class TEREN npc;
    class ENTRY,WAGON,SLOPE,CULVERT,TOWER,STREAM instance;
    class WORLD,ANOMALY,SEARCH_WAGON,MOVE_WAGON,SALVAGE_WAGON,BARRICADE_WAGON,CLIMB,FIND_CULVERT,SNEAK_CULVERT,PLATFORM,BELL,CUT_SUPPORTS,STONE_BARREL,AID_TEREN,WATER_TEREN,QUESTION_TEREN,ORDER_TEREN,FIGHT,FOOD,FIRE,RING_BELL,BYPASS,CALM,MAIN_ROUTE,FOREST_ROUTE,SPARE,KILL interaction;
    class PACK combat;
    class PACK_CHOICE,YOUNG_BEAST,ROUTE_DECISION decision;
    class FROM_GUILD,ARRIVAL,TO_KEEP transition;
    class ERYND_SIGN,NIMRA_SIGN,BLOOD,TRACKS,TEREN_LIE,TEREN_TRUTH,SINGING_WELL clue;
    class MANIFEST,MEDICINE,MORALE resource;
```

## Przybliżenie: kafelki gracza na Mapie 1

Diagram pokazuje pulę kafelków, a nie wszystkie kafelki jednocześnie. Etykieta
`warunkowy` oznacza, że kafelek pojawia się dopiero po odkryciu odpowiedniego
tropu, zmianie stanu albo wejściu wskazanego bohatera do drużyny.

```mermaid
flowchart LR
    subgraph WAGON_TILES["INSTANCJA · PRZEWRÓCONY WÓZ"]
        WAGON(["Przewrócony wóz"])
        W_SEARCH["KAFEL · Przeszukaj wóz"]
        W_TRACKS["KAFEL · Zbadaj ślady walki"]
        W_CLEAR["KAFEL · Uwolnij przejazd"]
        W_SALVAGE["KAFEL · Pozyskaj materiały"]
        W_BARRICADE["KAFEL · Przygotuj barykadę"]
        W_TAKE_MEDS["KAFEL WARUNKOWY · Zabierz lekarstwa"]
        W_MIRA["KAFEL BOHATERA · Mira: zbadaj znak przemytników"]
        W_LEAVE["WYJŚCIE · Opuść wóz"]
    end

    subgraph TEREN_TILES["INSTANCJA · TEREN"]
        TEREN(["Teren"])
        T_AID["KAFEL · Opatrz ranę"]
        T_SUPPLY["KAFEL · Daj wodę lub lekarstwo"]
        T_TALK["KAFEL · Poznaj wersję Terena"]
        T_MARCH["KAFEL · Oceń, czy Teren może iść"]
        T_BRACCA["KAFEL BOHATERA · Brakka: odpowiedz na propozycję zapłaty"]
        T_DAGNA["KAFEL BOHATERA · Dagna: zdecyduj o zakresie leczenia"]
        T_NIMRA["KAFEL BOHATERA · Nimra: zapytaj o śpiewającą studnię"]
        T_LORIAN["KAFEL BOHATERA · Lorian: pozwól mu opowiedzieć prawdę"]
        T_GARRAN["KAFEL BOHATERA · Garran: odpowiedz na prośbę o rozkaz"]
        T_LEAVE["WYJŚCIE · Zakończ rozmowę"]
    end

    subgraph TERRAIN_TILES["INSTANCJE TERENU"]
        SLOPE(["Skarpa"])
        S_CLIMB["KAFEL · Zdobądź przewagę wysokości"]
        CULVERT(["Przepust"])
        C_SEARCH["KAFEL · Poszukaj wejścia"]
        C_PASS["KAFEL WARUNKOWY · Przejdź przepustem"]
        TOWER(["Wieża sygnałowa"])
        O_CLIMB["KAFEL · Wejdź na platformę"]
        O_BELL["KAFEL · Sprawdź stary dzwon"]
        O_TRAP["KAFEL · Przygotuj pułapkę z wieży"]
        STREAM(["Strumień"])
        S_TRACK["KAFEL · Zbadaj świeże tropy"]
        S_BYPASS["KAFEL · Poszukaj obejścia"]
    end

    subgraph PACK_TILES["INSTANCJA / ENCOUNTER · GŁODNE CIENIE"]
        PACK(["Głodne Cienie"])
        P_FOOD["KAFEL · Odciągnij stado jedzeniem"]
        P_FIRE["KAFEL · Odstrasz stado ogniem"]
        P_BELL["KAFEL WARUNKOWY · Użyj dzwonu"]
        P_BYPASS["KAFEL WARUNKOWY · Obejdź stado"]
        P_CALM["KAFEL · Spróbuj uspokoić bestie"]
        P_FIGHT["KAFEL · Przygotuj się do walki"]
        P_RETREAT["WYJŚCIE · Wycofaj się"]
        P_YOUNG["KAFEL PO ENCOUNTERZE · Zdecyduj o losie młodej bestii"]
    end

    subgraph ROUTE_TILES["PRZEJŚCIE · WYBÓR DROGI"]
        ROUTE(["Droga do Czarnego Brodu"])
        R_MAIN["KAFEL · Rusz głównym traktem<br/>szybciej, ale jawnie"]
        R_FOREST["KAFEL · Wybierz leśny szlak<br/>wolniej, bliżej anomalii"]
        R_ERYND["KAFEL BOHATERA · Erynd: przygotuj drużynę do wybranej trasy"]
    end

    WAGON --> W_SEARCH
    WAGON --> W_TRACKS
    WAGON --> W_CLEAR
    WAGON --> W_SALVAGE
    WAGON --> W_BARRICADE
    WAGON -.-> W_TAKE_MEDS
    WAGON -.-> W_MIRA
    WAGON --> W_LEAVE

    TEREN --> T_AID
    TEREN --> T_SUPPLY
    TEREN --> T_TALK
    TEREN --> T_MARCH
    TEREN -.-> T_BRACCA
    TEREN -.-> T_DAGNA
    TEREN -.-> T_NIMRA
    TEREN -.-> T_LORIAN
    TEREN -.-> T_GARRAN
    TEREN --> T_LEAVE

    SLOPE --> S_CLIMB
    CULVERT --> C_SEARCH
    CULVERT -.-> C_PASS
    TOWER --> O_CLIMB
    TOWER --> O_BELL
    TOWER --> O_TRAP
    STREAM --> S_TRACK
    STREAM --> S_BYPASS

    PACK --> P_FOOD
    PACK --> P_FIRE
    PACK -.-> P_BELL
    PACK -.-> P_BYPASS
    PACK --> P_CALM
    PACK --> P_FIGHT
    PACK --> P_RETREAT
    PACK -.-> P_YOUNG

    ROUTE --> R_MAIN
    ROUTE --> R_FOREST
    ROUTE -.-> R_ERYND

    classDef npc fill:#dbeafe,color:#172554,stroke:#2563eb,stroke-width:2px;
    classDef instance fill:#fef3c7,color:#451a03,stroke:#d97706,stroke-width:2px;
    classDef tile fill:#d9f99d,color:#1a2e05,stroke:#4d7c0f,stroke-width:3px;
    classDef hero fill:#f3e8ff,color:#3b0764,stroke:#9333ea,stroke-width:2px;
    classDef exit fill:#fee2e2,color:#450a0a,stroke:#dc2626,stroke-width:3px;

    class TEREN npc;
    class WAGON,SLOPE,CULVERT,TOWER,STREAM,PACK,ROUTE instance;
    class W_SEARCH,W_TRACKS,W_CLEAR,W_SALVAGE,W_BARRICADE,W_TAKE_MEDS,T_AID,T_SUPPLY,T_TALK,T_MARCH,S_CLIMB,C_SEARCH,C_PASS,O_CLIMB,O_BELL,O_TRAP,S_TRACK,S_BYPASS,P_FOOD,P_FIRE,P_BELL,P_BYPASS,P_CALM,P_FIGHT,P_YOUNG,R_MAIN,R_FOREST tile;
    class W_MIRA,T_BRACCA,T_DAGNA,T_NIMRA,T_LORIAN,T_GARRAN,R_ERYND hero;
    class W_LEAVE,T_LEAVE,P_RETREAT exit;
```

Uwaga dla instancji Terena: pełna pula jest większa niż siedem. Kafelki
leczenia i podstawowej rozmowy znikają po rozstrzygnięciu, a kafelki bohaterów
pojawiają się tylko dla obecnego składu. Jeżeli mimo tego aktywnych byłoby więcej
niż sześć działań, momenty bohaterów należy pokazywać kolejno po zmianie stanu
Terena, nie stronicować menu.

## Opcjonalne momenty siedmiu bohaterów na Mapie 1

```mermaid
flowchart LR
    TEREN(["Teren"])
    WAGON(["Przewrócony wóz"])
    ROUTES{"Wybór trasy"}

    BRACCA[["Brakka · Pierścień za wodę<br/>zapłata, pomoc, odmowa albo brak pytań"]]
    MIRA[["Mira · Znak Jedwabnego Sznura<br/>ujawnić drużynie czy zachować sekret?"]]
    DAGNA[["Dagna · Szybkie czy dokładne leczenie<br/>koszt lekarstw ma dalszy skutek"]]
    NIMRA[["Nimra · Kierunkowa anomalia<br/>potraktować „śpiewającą studnię” poważnie?"]]
    LORIAN[["Lorian · Bez występu<br/>pozwolić rannemu mówić zamiast go zabawiać"]]
    GARRAN[["Garran · „Jaki jest rozkaz?”<br/>rozkaz, pytanie o zdanie albo odrzucenie roli"]]
    ERYND[["Erynd · Dwie niebezpieczne trasy<br/>szybka jawna albo wolna przy anomalii"]]

    TEREN -.-> BRACCA
    WAGON -.-> MIRA
    TEREN -.-> DAGNA
    TEREN -.-> NIMRA
    TEREN -.-> LORIAN
    TEREN -.-> GARRAN
    ROUTES -.-> ERYND

    classDef npc fill:#dbeafe,color:#172554,stroke:#2563eb,stroke-width:2px;
    classDef instance fill:#fef3c7,color:#451a03,stroke:#d97706,stroke-width:2px;
    classDef decision fill:#ffedd5,color:#431407,stroke:#ea580c,stroke-width:2px;
    classDef hero fill:#f3e8ff,color:#3b0764,stroke:#9333ea,stroke-width:2px;
    class TEREN npc;
    class WAGON instance;
    class ROUTES decision;
    class BRACCA,MIRA,DAGNA,NIMRA,LORIAN,GARRAN,ERYND hero;
```

### Stan przekazywany z Mapy 1

- przyjęty kontrakt, zaliczka i warunki premii;
- manifest oraz wiedza o prawdziwej wartości transportu;
- paczka lekarstw: znaleziona, zabrana, zużyta lub pozostawiona;
- Teren: stan rany, pragnienie, zdolność do drogi, zaufanie i ujawniona prawda;
- stan przewróconego wozu i zabrane materiały;
- rozwiązanie spotkania ze stadem i los młodej bestii;
- wybrana trasa, hałas, opóźnienie oraz rozpoznanie anomalii;
- aktywowane momenty osobiste i ujawnione informacje;
- aktualne PW, zasoby kart, ekwipunek, warunki i czas drużyny.

---

# Mapa 2 — Strażnica Czarnego Brodu

## Główny przepływ

```mermaid
flowchart TB
    ARRIVE(["Przejście · przybycie pod strażnicę<br/>warunki zależą od trasy, czasu i hałasu"])

    subgraph CONTACT["PIERWSZY KONTAKT"]
        GATE(["Instancja · Zewnętrzna brama<br/>wóz-barykada, brona, łucznicy na wieży"])
        OBSERVE["Trop · Obrońcy nie chcą walczyć,<br/>ale odpowiedzą na siłowe wejście"]
        ENTRY_CHOICE{"Decyzja · Jak wejść?"}

        TALK["Droga · Negocjacje przez bramę"]
        PEACE_COST{"Warunek pokoju<br/>rozmowa, kontrakt, pomoc chorym<br/>lub czasowe zabezpieczenie broni"}

        INFILTRATE["Droga · Infiltracja"]
        STABLE_ENTRY["Wejście · przez stajnię"]
        DRAIN_ENTRY["Wejście · kanałem odpływowym"]
        ROOF_ENTRY["Wejście · po dachu lub murze"]
        WALL_ENTRY["Wejście · uszkodzonym fragmentem muru"]
        DETECTED{"Czy infiltracja została wykryta?"}

        ASSAULT{{"Encounter opcjonalny · Siłowe wejście<br/>łucznicy, barykady, cywile i ryzyko pożaru"}}
        TRUCE["Interakcja · Rozejm podczas walki<br/>możliwy, gdy zagrożeni są cywile"]
    end

    subgraph COURTYARD["DZIEDZINIEC I INSTANCJE STRAŻNICY"]
        YARD(["Instancja · Dziedziniec<br/>studnia, wozy, legowiska, zwierzęta"])
        PANIC[("Stan · Panika cywilów")]
        WELL["Interakcja · Zbadaj studnię"]
        WELL_SOUND["Trop · metal wywołuje cichy śpiew"]
        WELL_NATURE["Trop · zwierzęta unikają wody"]
        WELL_RESIDUE["Trop · srebrzysty osad na linie"]
        WELL_SOURCE["Wniosek · skażenie pochodzi z podziemi"]

        CUSTOMS(["Instancja · Dawna izba celna"])
        MARK(["NPC · Marek Venn<br/>były sierżant i dowódca obrońców"])
        MARK_ACCOUNT["Informacja · lekarstwa zabrano chorym;<br/>transport przejęto po bójce"]

        STABLE(["Instancja · Stajnia"])
        ALVEN(["NPC · Alven Rost<br/>ranny rachmistrz, nie więzień"])
        ALVEN_ACCOUNT["Informacja · transport publiczny<br/>nie może być przejmowany przez każdą osadę"]

        INFIRMARY(["Instancja · Prowizoryczna lecznica"])
        SALKA(["NPC · Salka<br/>utalentowana, wyczerpana medyczka"])
        SICK_CHILD(["NPC/punkt · Chory chłopiec<br/>„Ktoś śpiewa pod wodą”"])
        DISEASE["Trop · gorączka, ciemne żyły,<br/>halucynacje i magiczne skurcze"]

        WAREHOUSE(["Instancja · Magazyn"])
        DUST_TWO[("Zasób · dwie skrzynie szarego pyłu")]
        FOOD_STOCK[("Zasób · część żywności")]
        RECORDS["Trop · dokumenty transportowe"]
        RAVEN_RESERVE["Informacja · Raven ma małą rezerwę;<br/>brak pyłu oznacza racjonowanie, nie natychmiastowy upadek"]

        MED_WAGON(["Instancja · Wóz z lekarstwami"])
        BROKEN_LOCK["Trop · zamek otwarto fachowo,<br/>ale celowo zostawiono część zapasów"]

        KITCHEN(["Instancja · Kuchnia"])
        RATIONS[("Stan · malejące racje żywności")]
        UNFAIR_RATIONS["Trop · dezerterzy dostają więcej niż cywile"]

        STAIRS(["Instancja · Zabarykadowane schody do Cysterny"])
        OLD_MINER(["NPC · Stary kopacz"])
        STONE_PLATE["Trop · śpiew zaczął się po usunięciu kamiennej płyty"]
    end

    subgraph TRUTH["USTALENIE PRAWDY I DROGA DO FINAŁU"]
        CONFLICT_TRUTH["Prawda · obie strony mają częściowo rację"]
        DUST_BELOW["Prawda · dwie skrzynie przeniesiono do Cysterny;<br/>jedna została otwarta"]
        FAILED_CLEANSE["Prawda · pył ograniczył skażenie,<br/>ale pobudził istotę pod strażnicą"]
        ACCESS{"Decyzja · Jak uzyskać dostęp do Cysterny?"}
        COOPERATE["Współpraca z Markiem, Salką lub Alvenem"]
        OPEN_STAIRS["Usuń barykadę i zabezpiecz zejście"]
        FORCE_DESCENT["Zejście bez zgody<br/>większa panika i gorszy handoff"]
        TO_CISTERN(["Przejście · handoff do Mapy 3"])
    end

    ARRIVE ==> GATE --> OBSERVE --> ENTRY_CHOICE
    ENTRY_CHOICE --> TALK --> PEACE_COST --> YARD
    ENTRY_CHOICE --> INFILTRATE
    INFILTRATE --> STABLE_ENTRY --> DETECTED
    INFILTRATE --> DRAIN_ENTRY --> DETECTED
    INFILTRATE --> ROOF_ENTRY --> DETECTED
    INFILTRATE --> WALL_ENTRY --> DETECTED
    DETECTED -->|nie| YARD
    DETECTED -->|tak| PANIC
    PANIC -->|wysoka panika lub agresja| ASSAULT
    ENTRY_CHOICE --> ASSAULT
    ASSAULT -.-> TRUCE --> YARD
    ASSAULT -->|przełamanie obrony| YARD

    YARD --> WELL
    YARD --> CUSTOMS
    YARD --> STABLE
    YARD --> INFIRMARY
    YARD --> WAREHOUSE
    YARD --> MED_WAGON
    YARD --> KITCHEN
    YARD --> STAIRS

    WELL --> WELL_SOUND
    WELL --> WELL_NATURE
    WELL --> WELL_RESIDUE
    WELL_SOUND --> WELL_SOURCE
    WELL_NATURE --> WELL_SOURCE
    WELL_RESIDUE --> WELL_SOURCE

    CUSTOMS --> MARK --> MARK_ACCOUNT
    STABLE --> ALVEN --> ALVEN_ACCOUNT
    INFIRMARY --> SALKA
    INFIRMARY --> SICK_CHILD
    INFIRMARY --> DISEASE
    WAREHOUSE --> DUST_TWO
    WAREHOUSE --> FOOD_STOCK
    WAREHOUSE --> RECORDS --> RAVEN_RESERVE
    MED_WAGON --> BROKEN_LOCK
    KITCHEN --> RATIONS
    KITCHEN --> UNFAIR_RATIONS
    STAIRS --> OLD_MINER --> STONE_PLATE

    MARK_ACCOUNT --> CONFLICT_TRUTH
    ALVEN_ACCOUNT --> CONFLICT_TRUTH
    RAVEN_RESERVE --> CONFLICT_TRUTH
    WELL_SOURCE --> DUST_BELOW
    STONE_PLATE --> DUST_BELOW
    DUST_TWO --> DUST_BELOW
    DUST_BELOW --> FAILED_CLEANSE --> ACCESS
    CONFLICT_TRUTH --> ACCESS
    ACCESS --> COOPERATE --> OPEN_STAIRS --> TO_CISTERN
    ACCESS --> FORCE_DESCENT --> TO_CISTERN

    classDef npc fill:#dbeafe,color:#172554,stroke:#2563eb,stroke-width:2px;
    classDef instance fill:#fef3c7,color:#451a03,stroke:#d97706,stroke-width:2px;
    classDef interaction fill:#ccfbf1,color:#134e4a,stroke:#0f766e,stroke-width:2px;
    classDef combat fill:#fee2e2,color:#450a0a,stroke:#dc2626,stroke-width:3px;
    classDef decision fill:#ffedd5,color:#431407,stroke:#ea580c,stroke-width:2px;
    classDef transition fill:#dcfce7,color:#052e16,stroke:#16a34a,stroke-width:3px;
    classDef clue fill:#ecfeff,color:#164e63,stroke:#0891b2,stroke-width:2px;
    classDef resource fill:#f1f5f9,color:#0f172a,stroke:#475569,stroke-width:2px;

    class MARK,ALVEN,SALKA,SICK_CHILD,OLD_MINER npc;
    class GATE,YARD,CUSTOMS,STABLE,INFIRMARY,WAREHOUSE,MED_WAGON,KITCHEN,STAIRS instance;
    class OBSERVE,TALK,PEACE_COST,INFILTRATE,STABLE_ENTRY,DRAIN_ENTRY,ROOF_ENTRY,WALL_ENTRY,TRUCE,WELL,COOPERATE,OPEN_STAIRS,FORCE_DESCENT interaction;
    class ASSAULT combat;
    class ENTRY_CHOICE,DETECTED,ACCESS decision;
    class ARRIVE,TO_CISTERN transition;
    class WELL_SOUND,WELL_NATURE,WELL_RESIDUE,WELL_SOURCE,MARK_ACCOUNT,ALVEN_ACCOUNT,DISEASE,RECORDS,RAVEN_RESERVE,BROKEN_LOCK,UNFAIR_RATIONS,STONE_PLATE,CONFLICT_TRUTH,DUST_BELOW,FAILED_CLEANSE clue;
    class PANIC,DUST_TWO,FOOD_STOCK,RATIONS resource;
```

## Przybliżenie: kafelki gracza na Mapie 2

Kafelki rozmowy pokazują cel rozmowy, nie gotowe kwestie dialogowe. Po wybraniu
`Poznaj wersję Marka` gracz nadal opisuje pytania i argumenty, a flow NPC
kontroluje informacje, testy, próby i konsekwencje.

```mermaid
flowchart LR
    subgraph GATE_TILES["INSTANCJA · BRAMA"]
        GATE(["Brama strażnicy"])
        G_TALK["KAFEL · Poproś o rozmowę"]
        G_CONTRACT["KAFEL · Pokaż kontrakt Gildii"]
        G_HELP["KAFEL · Zaoferuj pomoc chorym"]
        G_SURVEY["KAFEL · Zbadaj zabezpieczenia"]
        G_ALT["KAFEL WARUNKOWY · Spróbuj wejścia alternatywnego"]
        G_FORCE["KAFEL · Wymuś wejście"]
        G_LEAVE["WYJŚCIE · Odejdź od bramy"]
    end

    subgraph MARK_TILES["NPC · MAREK VENN"]
        MARK(["Marek Venn"])
        M_ACCOUNT["KAFEL · Poznaj wersję Marka"]
        M_ACCESS["KAFEL · Negocjuj swobodę poruszania się"]
        M_CARGO["KAFEL · Porozmawiaj o losie transportu"]
        M_SICK["KAFEL · Zaproponuj pomoc mieszkańcom"]
        M_DESCENT["KAFEL WARUNKOWY · Poproś o dostęp do Cysterny"]
        M_GARRAN["KAFEL BOHATERA · Garran: oceń obronę strażnicy"]
        M_LEAVE["WYJŚCIE · Zakończ rozmowę"]
    end

    subgraph ALVEN_TILES["NPC · ALVEN ROST"]
        ALVEN(["Alven Rost"])
        A_ACCOUNT["KAFEL · Poznaj wersję Alvena"]
        A_RECORDS["KAFEL · Zapytaj o dokumenty transportu"]
        A_RAVEN["KAFEL · Ustal sytuację Raven"]
        A_EVAC["KAFEL · Przekonaj go do ewakuacji"]
        A_DUST["KAFEL · Zapytaj o szary pył"]
        A_LEAVE["WYJŚCIE · Zakończ rozmowę"]
    end

    subgraph SALKA_TILES["NPC · SALKA / LECZNICA"]
        SALKA(["Salka i prowizoryczna lecznica"])
        S_PATIENTS["KAFEL · Pomóż chorym"]
        S_DISEASE["KAFEL · Zbadaj objawy choroby"]
        S_WATER["KAFEL · Zapytaj o wodę i początek skażenia"]
        S_SUPPLIES["KAFEL · Ustal stan lekarstw"]
        S_CHILD["KAFEL WARUNKOWY · Wysłuchaj chorego chłopca"]
        S_DAGNA["KAFEL BOHATERA · Dagna: porozmawiaj z młodą medyczką"]
        S_LEAVE["WYJŚCIE · Opuść lecznicę"]
    end

    subgraph YARD_TILES["INSTANCJE · DZIEDZINIEC I STUDNIA"]
        YARD(["Dziedziniec"])
        Y_SURVEY["KAFEL · Rozejrzyj się po obozie"]
        Y_WELL["KAFEL · Zbadaj studnię"]
        Y_WAGONS["KAFEL · Obejrzyj wozy karawany"]
        Y_CROWD["KAFEL · Oceń nastroje mieszkańców"]
        Y_LORIAN["KAFEL BOHATERA · Lorian: odpowiedz na prośbę o pieśń"]
        Y_LEAVE["WYJŚCIE · Wróć do wyboru lokacji"]
    end

    subgraph STORE_TILES["INSTANCJE · MAGAZYN I WÓZ LEKARSTW"]
        STORE(["Magazyn i wóz lekarstw"])
        W_INVENTORY["KAFEL · Sprawdź zapasy"]
        W_DUST["KAFEL · Obejrzyj skrzynie pyłu"]
        W_RECORDS["KAFEL · Przejrzyj dokumenty"]
        W_LOCK["KAFEL · Zbadaj złamany zamek"]
        W_SECURE["KAFEL WARUNKOWY · Zabezpiecz ładunek"]
        W_LEAVE["WYJŚCIE · Opuść magazyn"]
    end

    subgraph KITCHEN_TILES["INSTANCJA · KUCHNIA"]
        KITCHEN(["Kuchnia i racje"])
        K_RATIONS["KAFEL · Sprawdź podział racji"]
        K_OPEN["KAFEL WARUNKOWY · Otwórz gildyjne zapasy"]
        K_BRACCA["KAFEL BOHATERA · Brakka: ustal zasady podziału jedzenia"]
        K_LEAVE["WYJŚCIE · Opuść kuchnię"]
    end

    subgraph KELL_TILES["NPC WARUNKOWY · KELL"]
        KELL(["Kell"])
        E_RECOGNIZE["KAFEL BOHATERA · Mira: porozmawiaj z paserem"]
        E_BROTHER["KAFEL WARUNKOWY · Zapytaj o brata Miry"]
        E_DEAL["KAFEL WARUNKOWY · Rozważ układ dotyczący pyłu"]
        E_LEAVE["WYJŚCIE · Zakończ rozmowę"]
    end

    subgraph STAIRS_TILES["INSTANCJA · SCHODY DO CYSTERNY"]
        STAIRS(["Zabarykadowane zejście"])
        D_INSPECT["KAFEL · Zbadaj barykadę i zejście"]
        D_MINER["KAFEL · Wypytaj starego kopacza"]
        D_NIMRA["KAFEL BOHATERA · Nimra: zweryfikuj teorię anomalii"]
        D_PREPARE["KAFEL · Przygotuj zejście i drogę odwrotu"]
        D_ENTER["KAFEL WARUNKOWY · Zejdź do Cysterny"]
        D_LEAVE["WYJŚCIE · Wróć na dziedziniec"]
    end

    subgraph ERYND_TILES["PUNKT WARUNKOWY · UKRYTY MAGAZYN"]
        FOREST(["Leśna skrytka zapasów"])
        F_ERYND["KAFEL BOHATERA · Erynd: sprawdź ukryty magazyn"]
        F_REVEAL["KAFEL WARUNKOWY · Ujawnij zapasy Markowi"]
        F_KEEP["KAFEL WARUNKOWY · Zachowaj położenie w tajemnicy"]
        F_LEAVE["WYJŚCIE · Wróć do strażnicy"]
    end

    GATE --> G_TALK
    GATE --> G_CONTRACT
    GATE --> G_HELP
    GATE --> G_SURVEY
    GATE -.-> G_ALT
    GATE --> G_FORCE
    GATE --> G_LEAVE

    MARK --> M_ACCOUNT
    MARK --> M_ACCESS
    MARK --> M_CARGO
    MARK --> M_SICK
    MARK -.-> M_DESCENT
    MARK -.-> M_GARRAN
    MARK --> M_LEAVE

    ALVEN --> A_ACCOUNT
    ALVEN --> A_RECORDS
    ALVEN --> A_RAVEN
    ALVEN --> A_EVAC
    ALVEN --> A_DUST
    ALVEN --> A_LEAVE

    SALKA --> S_PATIENTS
    SALKA --> S_DISEASE
    SALKA --> S_WATER
    SALKA --> S_SUPPLIES
    SALKA -.-> S_CHILD
    SALKA -.-> S_DAGNA
    SALKA --> S_LEAVE

    YARD --> Y_SURVEY
    YARD --> Y_WELL
    YARD --> Y_WAGONS
    YARD --> Y_CROWD
    YARD -.-> Y_LORIAN
    YARD --> Y_LEAVE

    STORE --> W_INVENTORY
    STORE --> W_DUST
    STORE --> W_RECORDS
    STORE --> W_LOCK
    STORE -.-> W_SECURE
    STORE --> W_LEAVE

    KITCHEN --> K_RATIONS
    KITCHEN -.-> K_OPEN
    KITCHEN -.-> K_BRACCA
    KITCHEN --> K_LEAVE

    KELL --> E_RECOGNIZE
    KELL -.-> E_BROTHER
    KELL -.-> E_DEAL
    KELL --> E_LEAVE

    STAIRS --> D_INSPECT
    STAIRS --> D_MINER
    STAIRS -.-> D_NIMRA
    STAIRS --> D_PREPARE
    STAIRS -.-> D_ENTER
    STAIRS --> D_LEAVE

    FOREST --> F_ERYND
    FOREST -.-> F_REVEAL
    FOREST -.-> F_KEEP
    FOREST --> F_LEAVE

    classDef npc fill:#dbeafe,color:#172554,stroke:#2563eb,stroke-width:2px;
    classDef instance fill:#fef3c7,color:#451a03,stroke:#d97706,stroke-width:2px;
    classDef tile fill:#d9f99d,color:#1a2e05,stroke:#4d7c0f,stroke-width:3px;
    classDef hero fill:#f3e8ff,color:#3b0764,stroke:#9333ea,stroke-width:2px;
    classDef exit fill:#fee2e2,color:#450a0a,stroke:#dc2626,stroke-width:3px;

    class MARK,ALVEN,SALKA,KELL npc;
    class GATE,YARD,STORE,KITCHEN,STAIRS,FOREST instance;
    class G_TALK,G_CONTRACT,G_HELP,G_SURVEY,G_ALT,G_FORCE,M_ACCOUNT,M_ACCESS,M_CARGO,M_SICK,M_DESCENT,A_ACCOUNT,A_RECORDS,A_RAVEN,A_EVAC,A_DUST,S_PATIENTS,S_DISEASE,S_WATER,S_SUPPLIES,S_CHILD,Y_SURVEY,Y_WELL,Y_WAGONS,Y_CROWD,W_INVENTORY,W_DUST,W_RECORDS,W_LOCK,W_SECURE,K_RATIONS,K_OPEN,E_BROTHER,E_DEAL,D_INSPECT,D_MINER,D_PREPARE,D_ENTER,F_REVEAL,F_KEEP tile;
    class M_GARRAN,S_DAGNA,Y_LORIAN,K_BRACCA,E_RECOGNIZE,D_NIMRA,F_ERYND hero;
    class G_LEAVE,M_LEAVE,A_LEAVE,S_LEAVE,Y_LEAVE,W_LEAVE,K_LEAVE,E_LEAVE,D_LEAVE,F_LEAVE exit;
```

## Opcjonalne momenty siedmiu bohaterów na Mapie 2

```mermaid
flowchart LR
    KITCHEN(["Kuchnia"])
    KELL(["Kell · paser Jedwabnego Sznura"])
    SALKA(["Salka"])
    MINER(["Stary kopacz"])
    CROWD(["Mieszkańcy strażnicy"])
    MARK(["Marek Venn"])
    FOREST(["Ukryty magazyn w lesie"])

    BRACCA[["Brakka · Cena posiłku<br/>dzieci, obrońcy, równe porcje lub otwarcie zapasów"]]
    MIRA[["Mira · Człowiek Jedwabnego Sznura<br/>informacja o bracie za pomoc w kradzieży pyłu"]]
    DAGNA[["Dagna · Młoda medyczka<br/>potwierdzić nieprawdę czy pomóc Salce postawić granice?"]]
    NIMRA[["Nimra · Błędna teoria<br/>przyjąć dowód, że anomalię wywołał człowiek?"]]
    LORIAN[["Lorian · Publiczność chce kłamstwa<br/>pieśń podnosząca morale czy prawda o poległym?"]]
    GARRAN[["Garran · Dowodzenie obroną<br/>przejąć inicjatywę, doradzić lub wesprzeć Marka"]]
    ERYND[["Erynd · Bezpieczny magazyn<br/>ujawnić zapasy, zachować sekret czy sprawdzić skrytkę?"]]

    KITCHEN -.-> BRACCA
    KELL -.-> MIRA
    SALKA -.-> DAGNA
    MINER -.-> NIMRA
    CROWD -.-> LORIAN
    MARK -.-> GARRAN
    FOREST -.-> ERYND

    classDef npc fill:#dbeafe,color:#172554,stroke:#2563eb,stroke-width:2px;
    classDef instance fill:#fef3c7,color:#451a03,stroke:#d97706,stroke-width:2px;
    classDef hero fill:#f3e8ff,color:#3b0764,stroke:#9333ea,stroke-width:2px;
    class KELL,SALKA,MINER,MARK npc;
    class KITCHEN,CROWD,FOREST instance;
    class BRACCA,MIRA,DAGNA,NIMRA,LORIAN,GARRAN,ERYND hero;
```

### Stan przekazywany z Mapy 2

- droga wejścia: pokojowa, skryta, wykryta albo siłowa;
- nastawienie Marka, Alvena, Salki, obrońców i cywilów;
- poziom paniki, ofiary, pożar i stan bramy;
- poznana wersja wydarzeń i wiedza o rezerwach Raven;
- stan lekarstw, żywności oraz ukrytych zapasów;
- cztery instancje skrzyń: dwie w magazynie, jedna zamknięta w Cysternie,
  jedna otwarta i częściowo rozsypana;
- wiedza o płycie, studni, anomalii i nieudanej próbie oczyszczenia;
- osoby schodzące do Cysterny oraz przygotowane liny, narzędzia, ładunki i
  drogi odwrotu;
- aktualne PW, zasoby, warunki, ekwipunek oraz czas drużyny.

---

# Mapa 3 — Podziemna Cysterna

## Główny przepływ

```mermaid
flowchart TB
    ARRIVE(["Przejście · zejście do Cysterny<br/>skład i warunki zależą od Mapy 2"])

    subgraph MAP3["MAPA 3 · PODZIEMNA CYSTERNA · 20×30"]
        STAIRS(["Instancja · Wąskie schody wejściowe"])
        TANK(["Instancja · Główny zbiornik"])
        SHALLOW["Teren · płytka woda = trudny teren"]
        DEEP["Teren · głęboka woda = zagrożenie"]
        WALKWAYS(["Instancja · Kamienne pomosty<br/>wysokość, skoki, blokowanie, zawalenie"])
        CHANNELS(["Instancja · Boczne kanały<br/>obejście i zmiana przepływu"])
        CRACK(["Instancja · Kamienna płyta i magiczne pęknięcie"])
        RITUAL_ROOM(["Instancja · Stara komora rytualna"])
        DUST_CLOSED[("Zasób · zamknięta skrzynia pyłu")]
        DUST_OPEN[("Zasób · otwarta skrzynia i rozsypany pył")]

        VALVE1["Obiekt · Zawór 1<br/>obniża poziom wody"]
        VALVE2["Obiekt · Zawór 2<br/>odcina skażony dopływ"]
        VALVE3["Obiekt · Zawór 3<br/>odsłania kanał awaryjny"]
        VALVE_STATE[("Stan · liczba ustawionych zaworów")]
        WATER_CLOCK[("Stan rundy · poziom wody / ryzyko zalania")]

        RESONANCE{{"Boss · Głodny Rezonans<br/>woda, głosy, przyciąganie i jawne zakłócenie magii"}}
        FEAR_FEED[("Stan · Rezonans wzmacnia się przez panikę/hałas")]
        WEAKEN["Reguła · zawory i odcięcie przepływu<br/>osłabiają zdolności Rezonansu"]

        GOALS{"Aktualny priorytet drużyny"}
        CLOSE_VALVES["Cel · Ustaw zawory"]
        PROTECT["Cel · Ochroń osobę wykonującą rytuał"]
        CONTROL_WATER["Cel · Nie dopuść do zalania komory"]
        SECURE_DUST["Cel · Zabezpiecz skrzynie pyłu"]
        ESCAPE_ROUTE["Cel · Utrzymaj drogę odwrotu"]

        END_METHOD{"Decyzja taktyczna · Jak zakończyć zagrożenie?"}
        KILL_RESONANCE["Pokonaj Rezonans obrażeniami<br/>istota znika, pęknięcie pozostaje"]
        SEAL_RIFT["Zamknij pęknięcie rytuałem<br/>trwale, ale zużywa większość pyłu"]
        CUT_WATER["Odtnij źródło wody<br/>daje czas, nie usuwa anomalii"]
        TRAP_RESONANCE["Uwięź Rezonans dźwiękiem i magią<br/>ryzykowne i tymczasowe"]
        COLLAPSE["Zawal Cysternę<br/>odcina skażenie, niszczy wodę i część strażnicy"]

        THREAT_RESOLVED(["Przejście · zagrożenie opanowane lub odwrót"])
    end

    subgraph FINALE["OSTATECZNA DECYZJA I RAPORT"]
        COUNT_DUST[("Stan · policz ocalały i zużyty pył")]
        DUST_CHOICE{"Decyzja · Komu należy się szary pył?"}
        RAVEN["Wszystko dla Raven<br/>pełny kontrakt, zagrożenie dla Czarnego Brodu"]
        KEEP["Wszystko dla strażnicy<br/>ocaleni mieszkańcy, koszt dla Raven i Gildii"]
        SPLIT["Podział<br/>oba problemy ograniczone, żaden zamknięty"]
        TEMPORARY["Rozwiązanie tymczasowe<br/>większość pyłu dla Raven, przyszły quest"]
        LIE["Ukrycie prawdy<br/>fałszywy raport, ukryte skrzynie lub wina anomalii"]
        NESSA(["NPC · Nessa Vel<br/>„Ile skrzyń odzyskaliście?”"])
        CONSEQUENCES["Konsekwencje · zapłata, reputacja, kontakty,<br/>klucz, baza, kanały i dalsze zadania"]
        END(["KONIEC PIERWSZEJ PRZYGODY"])
    end

    ARRIVE ==> STAIRS
    STAIRS --> TANK
    TANK --> SHALLOW
    TANK --> DEEP
    TANK --> WALKWAYS
    TANK --> CHANNELS
    TANK --> CRACK
    TANK --> RITUAL_ROOM
    TANK --> DUST_CLOSED
    TANK --> DUST_OPEN
    TANK --> RESONANCE

    TANK --> VALVE1 --> VALVE_STATE
    TANK --> VALVE2 --> VALVE_STATE
    TANK --> VALVE3 --> VALVE_STATE
    RESONANCE --> FEAR_FEED
    RESONANCE --> WATER_CLOCK
    VALVE_STATE --> WEAKEN

    RESONANCE --> GOALS
    GOALS --> CLOSE_VALVES
    GOALS --> PROTECT
    GOALS --> CONTROL_WATER
    GOALS --> SECURE_DUST
    GOALS --> ESCAPE_ROUTE
    CLOSE_VALVES --> VALVE1
    CLOSE_VALVES --> VALVE2
    CLOSE_VALVES --> VALVE3
    PROTECT --> RITUAL_ROOM
    CONTROL_WATER --> WATER_CLOCK
    SECURE_DUST --> DUST_CLOSED
    SECURE_DUST --> DUST_OPEN
    ESCAPE_ROUTE --> WALKWAYS
    ESCAPE_ROUTE --> CHANNELS

    RESONANCE --> END_METHOD
    WEAKEN --> END_METHOD
    RITUAL_ROOM --> END_METHOD
    CRACK --> END_METHOD
    END_METHOD --> KILL_RESONANCE --> THREAT_RESOLVED
    END_METHOD --> SEAL_RIFT --> THREAT_RESOLVED
    END_METHOD --> CUT_WATER --> THREAT_RESOLVED
    END_METHOD --> TRAP_RESONANCE --> THREAT_RESOLVED
    END_METHOD --> COLLAPSE --> THREAT_RESOLVED

    THREAT_RESOLVED ==> COUNT_DUST --> DUST_CHOICE
    DUST_CHOICE --> RAVEN --> NESSA
    DUST_CHOICE --> KEEP --> NESSA
    DUST_CHOICE --> SPLIT --> NESSA
    DUST_CHOICE --> TEMPORARY --> NESSA
    DUST_CHOICE --> LIE --> NESSA
    NESSA --> CONSEQUENCES --> END

    classDef npc fill:#dbeafe,color:#172554,stroke:#2563eb,stroke-width:2px;
    classDef instance fill:#fef3c7,color:#451a03,stroke:#d97706,stroke-width:2px;
    classDef interaction fill:#ccfbf1,color:#134e4a,stroke:#0f766e,stroke-width:2px;
    classDef combat fill:#fee2e2,color:#450a0a,stroke:#dc2626,stroke-width:3px;
    classDef decision fill:#ffedd5,color:#431407,stroke:#ea580c,stroke-width:2px;
    classDef transition fill:#dcfce7,color:#052e16,stroke:#16a34a,stroke-width:3px;
    classDef resource fill:#f1f5f9,color:#0f172a,stroke:#475569,stroke-width:2px;

    class NESSA npc;
    class STAIRS,TANK,WALKWAYS,CHANNELS,CRACK,RITUAL_ROOM instance;
    class SHALLOW,DEEP,VALVE1,VALVE2,VALVE3,WEAKEN,CLOSE_VALVES,PROTECT,CONTROL_WATER,SECURE_DUST,ESCAPE_ROUTE,KILL_RESONANCE,SEAL_RIFT,CUT_WATER,TRAP_RESONANCE,COLLAPSE,RAVEN,KEEP,SPLIT,TEMPORARY,LIE,CONSEQUENCES interaction;
    class RESONANCE combat;
    class GOALS,END_METHOD,DUST_CHOICE decision;
    class ARRIVE,THREAT_RESOLVED,END transition;
    class DUST_CLOSED,DUST_OPEN,VALVE_STATE,WATER_CLOCK,FEAR_FEED,COUNT_DUST resource;
```

## Przybliżenie: kafelki gracza na Mapie 3

W Cysternie część kafelków jest eksploracyjna, a część pojawia się jako
kontekstowa akcja pola podczas encountera. Z punktu widzenia gracza oba typy są
decyzją wybraną na planszy; różni je koszt czasu walki i stan tury.

```mermaid
flowchart LR
    subgraph ENTRY_TILES["INSTANCJA · WEJŚCIE I ROZPOZNANIE"]
        ENTRY(["Wejście do Cysterny"])
        E_SURVEY["KAFEL · Oceń układ Cysterny"]
        E_WATER["KAFEL · Zbadaj skażoną wodę"]
        E_ESCAPE["KAFEL · Przygotuj drogę odwrotu"]
        E_DUST["KAFEL · Zlokalizuj skrzynie pyłu"]
        E_RITUAL["KAFEL · Znajdź komorę rytualną"]
        E_ADVANCE["KAFEL · Wejdź do głównego zbiornika"]
        E_LEAVE["WYJŚCIE · Wróć do strażnicy"]
    end

    subgraph VALVE_TILES["OBIEKTY WALKI · TRZY ZAWORY"]
        VALVES(["Zawory Cysterny"])
        V_INSPECT["KAFEL / AKCJA · Rozpoznaj działanie zaworu"]
        V_LOWER["KAFEL / AKCJA · Obniż poziom wody"]
        V_CUTOFF["KAFEL / AKCJA · Odetnij skażony dopływ"]
        V_ESCAPE["KAFEL / AKCJA · Otwórz kanał awaryjny"]
        V_FORCE["KAFEL / AKCJA · Wymuś pracę zablokowanego mechanizmu"]
        V_LEAVE["WYJŚCIE · Wróć do działań walki"]
    end

    subgraph RITUAL_TILES["INSTANCJA / CEL WALKI · KOMORA RYTUALNA"]
        RITUAL(["Komora rytualna"])
        R_INSPECT["KAFEL · Zbadaj pęknięcie i płytę"]
        R_PLAN["KAFEL · Przygotuj rytuał stabilizacji"]
        R_BEGIN["KAFEL WARUNKOWY / AKCJA · Rozpocznij rytuał"]
        R_CONTINUE["KAFEL WARUNKOWY / AKCJA · Kontynuuj rytuał"]
        R_DUST["KAFEL WARUNKOWY · Przeznacz pył na zamknięcie pęknięcia"]
        R_NIMRA["KAFEL BOHATERA · Nimra: zmień błędną metodę"]
        R_LEAVE["WYJŚCIE · Przerwij przygotowanie"]
    end

    subgraph DUST_TILES["OBIEKT · SKRZYNIE SZAREGO PYŁU"]
        DUST(["Zamknięta skrzynia i rozsypany pył"])
        D_SECURE["KAFEL / AKCJA · Zabezpiecz zamkniętą skrzynię"]
        D_GATHER["KAFEL / AKCJA · Zbierz rozsypany pył"]
        D_USE_VALVE["KAFEL WARUNKOWY · Użyj pyłu do wsparcia mechanizmu"]
        D_USE_RITUAL["KAFEL WARUNKOWY · Użyj pyłu w rytuale"]
        D_ABANDON["KAFEL · Porzuć pył i zabezpiecz odwrót"]
        D_LEAVE["WYJŚCIE · Wróć do działań walki"]
    end

    subgraph CHANNEL_TILES["INSTANCJA · KANAŁY I KONSTRUKCJA"]
        CHANNELS(["Kanały, pomosty i podpory"])
        C_BYPASS["KAFEL · Znajdź boczne przejście"]
        C_BLOCK["KAFEL / AKCJA · Zablokuj dopływ"]
        C_COLLAPSE["KAFEL / AKCJA · Przygotuj zawalenie Cysterny"]
        C_BRACCA["KAFEL BOHATERA · Brakka: utrzymaj niestabilną podporę"]
        C_MIRA["KAFEL BOHATERA · Mira: uruchom mechanizm awaryjny"]
        C_ERYND["KAFEL BOHATERA · Erynd: uruchom procedurę odwrotu"]
        C_LEAVE["WYJŚCIE · Wróć do działań walki"]
    end

    subgraph CRISIS_TILES["KAFELKI BOHATERÓW · KRYZYS FINAŁU"]
        CRISIS(["Kryzys podczas walki"])
        H_DAGNA["KAFEL BOHATERA · Dagna: rozdziel ograniczoną pomoc"]
        H_LORIAN["KAFEL BOHATERA · Lorian: odpowiedz na pokusę Gościa"]
        H_GARRAN["KAFEL BOHATERA · Garran: wybierz plan działania"]
    end

    subgraph END_TILES["DECYZJA TAKTYCZNA · ZAKOŃCZENIE ZAGROŻENIA"]
        THREAT(["Głodny Rezonans i anomalia"])
        T_DEFEAT["KAFEL · Zniszcz Rezonans"]
        T_SEAL["KAFEL WARUNKOWY · Zamknij pęknięcie"]
        T_WATER["KAFEL WARUNKOWY · Odetnij źródło wody"]
        T_TRAP["KAFEL WARUNKOWY · Uwięź Rezonans"]
        T_COLLAPSE["KAFEL WARUNKOWY · Zawal Cysternę"]
        T_RETREAT["WYJŚCIE · Zarządź odwrót"]
    end

    subgraph DUST_DECISION_TILES["DECYZJA FABULARNA · LOS SZAREGO PYŁU"]
        DECISION(["Ocalały szary pył"])
        O_RAVEN["KAFEL · Przekaż wszystko Raven"]
        O_KEEP["KAFEL · Zostaw wszystko w Czarnym Brodzie"]
        O_SPLIT["KAFEL · Podziel ocalały pył"]
        O_TEMP["KAFEL WARUNKOWY · Wybierz zabezpieczenie tymczasowe"]
        O_HIDE["KAFEL WARUNKOWY · Ukryj część prawdy i ładunku"]
    end

    subgraph REPORT_TILES["NPC · RAPORT DLA NESSY"]
        NESSA(["Nessa Vel"])
        N_REPORT["KAFEL · Złóż prawdziwy raport"]
        N_EXPLAIN["KAFEL · Uzasadnij decyzję drużyny"]
        N_LIE["KAFEL WARUNKOWY · Przedstaw przygotowaną fałszywą wersję"]
        N_REWARD["KAFEL · Rozlicz kontrakt i nagrody"]
        N_FUTURE["KAFEL WARUNKOWY · Zapytaj o dalsze konsekwencje"]
        N_END["WYJŚCIE · Zakończ pierwszą przygodę"]
    end

    ENTRY --> E_SURVEY
    ENTRY --> E_WATER
    ENTRY --> E_ESCAPE
    ENTRY --> E_DUST
    ENTRY --> E_RITUAL
    ENTRY --> E_ADVANCE
    ENTRY --> E_LEAVE

    VALVES --> V_INSPECT
    VALVES --> V_LOWER
    VALVES --> V_CUTOFF
    VALVES --> V_ESCAPE
    VALVES --> V_FORCE
    VALVES --> V_LEAVE

    RITUAL --> R_INSPECT
    RITUAL --> R_PLAN
    RITUAL -.-> R_BEGIN
    RITUAL -.-> R_CONTINUE
    RITUAL -.-> R_DUST
    RITUAL -.-> R_NIMRA
    RITUAL --> R_LEAVE

    DUST --> D_SECURE
    DUST --> D_GATHER
    DUST -.-> D_USE_VALVE
    DUST -.-> D_USE_RITUAL
    DUST --> D_ABANDON
    DUST --> D_LEAVE

    CHANNELS --> C_BYPASS
    CHANNELS --> C_BLOCK
    CHANNELS --> C_COLLAPSE
    CHANNELS -.-> C_BRACCA
    CHANNELS -.-> C_MIRA
    CHANNELS -.-> C_ERYND
    CHANNELS --> C_LEAVE

    CRISIS -.-> H_DAGNA
    CRISIS -.-> H_LORIAN
    CRISIS -.-> H_GARRAN

    THREAT --> T_DEFEAT
    THREAT -.-> T_SEAL
    THREAT -.-> T_WATER
    THREAT -.-> T_TRAP
    THREAT -.-> T_COLLAPSE
    THREAT --> T_RETREAT

    DECISION --> O_RAVEN
    DECISION --> O_KEEP
    DECISION --> O_SPLIT
    DECISION -.-> O_TEMP
    DECISION -.-> O_HIDE

    NESSA --> N_REPORT
    NESSA --> N_EXPLAIN
    NESSA -.-> N_LIE
    NESSA --> N_REWARD
    NESSA -.-> N_FUTURE
    NESSA --> N_END

    classDef npc fill:#dbeafe,color:#172554,stroke:#2563eb,stroke-width:2px;
    classDef instance fill:#fef3c7,color:#451a03,stroke:#d97706,stroke-width:2px;
    classDef tile fill:#d9f99d,color:#1a2e05,stroke:#4d7c0f,stroke-width:3px;
    classDef hero fill:#f3e8ff,color:#3b0764,stroke:#9333ea,stroke-width:2px;
    classDef exit fill:#fee2e2,color:#450a0a,stroke:#dc2626,stroke-width:3px;

    class NESSA npc;
    class ENTRY,VALVES,RITUAL,DUST,CHANNELS,CRISIS,THREAT,DECISION instance;
    class E_SURVEY,E_WATER,E_ESCAPE,E_DUST,E_RITUAL,E_ADVANCE,V_INSPECT,V_LOWER,V_CUTOFF,V_ESCAPE,V_FORCE,R_INSPECT,R_PLAN,R_BEGIN,R_CONTINUE,R_DUST,D_SECURE,D_GATHER,D_USE_VALVE,D_USE_RITUAL,D_ABANDON,C_BYPASS,C_BLOCK,C_COLLAPSE,T_DEFEAT,T_SEAL,T_WATER,T_TRAP,T_COLLAPSE,O_RAVEN,O_KEEP,O_SPLIT,O_TEMP,O_HIDE,N_REPORT,N_EXPLAIN,N_LIE,N_REWARD,N_FUTURE tile;
    class R_NIMRA,C_BRACCA,C_MIRA,C_ERYND,H_DAGNA,H_LORIAN,H_GARRAN hero;
    class E_LEAVE,V_LEAVE,R_LEAVE,D_LEAVE,C_LEAVE,T_RETREAT,N_END exit;
```

Kafelki `Zniszcz Rezonans`, `Zamknij pęknięcie` itd. nie zastępują kart
bojowych. Wskazują aktualny cel taktyczny i odblokowują odpowiednie obiekty lub
akcje pola. Zwykłe ataki, czary i cechy nadal są wybierane kartami postaci oraz
kontekstowym menu planszy.

## Opcjonalne momenty siedmiu bohaterów na Mapie 3

```mermaid
flowchart LR
    SUPPORT(["Niestabilna podpora"])
    EMERGENCY(["Zamknięty mechanizm awaryjny"])
    WOUNDED(["Ciężko ranni podczas finału"])
    RITUAL(["Zmiana prawdy o rytuale"])
    EMOTIONS(["Emocje Głodnego Rezonansu"])
    COMMAND(["Kryzys wymagający decyzji"])
    ESCAPE(["Przygotowana droga odwrotu"])

    BRACCA[["Brakka · Utrzymać podporę<br/>ryzykować obrażenia czy zarządzić odwrót?"]]
    MIRA[["Mira · Mechanizm awaryjny<br/>opróżnić Cysternę i zaufać drużynie?"]]
    DAGNA[["Dagna · Ograniczona pomoc<br/>jedno potężne leczenie czy rozdzielona pomoc?"]]
    NIMRA[["Nimra · Błąd w rytuale<br/>przyznać się i zmienić plan czy brnąć dalej?"]]
    LORIAN[["Lorian · Gość Ostatniego Rzędu<br/>przejąć emocje istoty i ryzykować wpływ na pakt?"]]
    GARRAN[["Garran · Wszyscy czekają na rozkaz<br/>wybrać plan czy oddać decyzję innej osobie?"]]
    ERYND[["Erynd · Procedura awaryjna działa<br/>uruchomić ją kosztem drogi cywilów?"]]

    SUPPORT -.-> BRACCA
    EMERGENCY -.-> MIRA
    WOUNDED -.-> DAGNA
    RITUAL -.-> NIMRA
    EMOTIONS -.-> LORIAN
    COMMAND -.-> GARRAN
    ESCAPE -.-> ERYND

    classDef instance fill:#fef3c7,color:#451a03,stroke:#d97706,stroke-width:2px;
    classDef hero fill:#f3e8ff,color:#3b0764,stroke:#9333ea,stroke-width:2px;
    class SUPPORT,EMERGENCY,WOUNDED,RITUAL,EMOTIONS,COMMAND,ESCAPE instance;
    class BRACCA,MIRA,DAGNA,NIMRA,LORIAN,GARRAN,ERYND hero;
```

---

# Model najważniejszego stanu przygody

Ten diagram nie pokazuje kolejności scen. Pokazuje, które stany wpływają na
finał i nie mogą pozostać wyłącznie narracją LLM.

```mermaid
flowchart LR
    subgraph DUST["SZARY PYŁ · JEDNO ŹRÓDŁO PRAWDY"]
        BOX1[("Skrzynia 1 · magazyn")]
        BOX2[("Skrzynia 2 · magazyn")]
        BOX3[("Skrzynia 3 · Cysterna, zamknięta")]
        BOX4[("Skrzynia 4 · Cysterna, otwarta")]
        SPILL[("Rozsypany pył")]
        DUST_TOTAL["Wyliczony stan<br/>zabezpieczony / zużyty / utracony / ukryty"]
    end

    subgraph PEOPLE["LUDZIE I RELACJE"]
        TEREN[("Teren · zdrowie, zaufanie, prawda")]
        MARK[("Marek · zaufanie i dowództwo")]
        ALVEN[("Alven · zdrowie i raport")]
        SALKA[("Salka · zdrowie i zdolność leczenia")]
        CIVILIANS[("Cywile · panika, choroba, ofiary")]
        GUILD[("Gildia · kontrakt, zaliczka, reputacja")]
    end

    subgraph SUPPLIES["ZASOBY"]
        MEDS[("Lekarstwa · znalezione i zużyte")]
        FOOD[("Żywność · odzyskana, wydana, ukryta")]
        TIME[("Czas · podróż, leczenie, odpoczynki")]
        HERO_STATE[("Drużyna · PW, karty, warunki, ekwipunek")]
    end

    subgraph TRUTH["WIEDZA I PRAWDZIWE FAKTY"]
        GUARD_TRUTH[("Prawda o bójce strażników")]
        RAVEN_TRUTH[("Prawda o rezerwie Raven")]
        RIFT_TRUTH[("Prawda o płycie i pęknięciu")]
        SILK_ROPE[("Jedwabny Sznur i sekret Miry")]
    end

    subgraph CISTERN["WYNIK CYSTERNY"]
        VALVES[("Stan trzech zaworów")]
        ANOMALY[("Anomalia · aktywna, odcięta, zamknięta lub uwięziona")]
        RESONANCE[("Rezonans · aktywny, pokonany lub uwięziony")]
        KEEP_WATER[("Woda strażnicy · dostępna lub utracona")]
    end

    ENDING{"Wylicz dostępne zakończenia"}
    REPORT{"Prawdziwy czy fałszywy raport?"}
    CONSEQUENCE(["Konsekwencje kampanii"])

    BOX1 --> DUST_TOTAL
    BOX2 --> DUST_TOTAL
    BOX3 --> DUST_TOTAL
    BOX4 --> DUST_TOTAL
    SPILL --> DUST_TOTAL

    DUST_TOTAL --> ENDING
    TEREN --> ENDING
    MARK --> ENDING
    ALVEN --> REPORT
    SALKA --> ENDING
    CIVILIANS --> ENDING
    GUILD --> REPORT
    MEDS --> ENDING
    FOOD --> ENDING
    TIME --> ENDING
    HERO_STATE --> ENDING
    GUARD_TRUTH --> REPORT
    RAVEN_TRUTH --> ENDING
    RIFT_TRUTH --> ENDING
    SILK_ROPE --> REPORT
    VALVES --> ANOMALY
    RESONANCE --> ANOMALY
    ANOMALY --> ENDING
    KEEP_WATER --> ENDING
    ENDING --> REPORT --> CONSEQUENCE

    classDef resource fill:#f1f5f9,color:#0f172a,stroke:#475569,stroke-width:2px;
    classDef decision fill:#ffedd5,color:#431407,stroke:#ea580c,stroke-width:2px;
    classDef transition fill:#dcfce7,color:#052e16,stroke:#16a34a,stroke-width:3px;
    class BOX1,BOX2,BOX3,BOX4,SPILL,TEREN,MARK,ALVEN,SALKA,CIVILIANS,GUILD,MEDS,FOOD,TIME,HERO_STATE,GUARD_TRUTH,RAVEN_TRUTH,RIFT_TRUTH,SILK_ROPE,VALVES,ANOMALY,RESONANCE,KEEP_WATER resource;
    class ENDING,REPORT decision;
    class CONSEQUENCE transition;
```

---

# Mapowanie grafu na pliki contentu

| Element grafu | Docelowe miejsce w paczce |
|---|---|
| Mapa/paczka | `scenario.json`, `environment.json`, `print_maps.json` |
| Kafelek gracza | player-facing `goal` oraz przejście w `flows.json`; najwyżej sześć kafelków i czerwone wyjście naraz |
| Instancja/lokacja | `exploration/zones.json` albo `exploration/points.json` |
| NPC | `actors.json`, definicja punktu, `npc_transitions.json`, `flows.json` |
| Interakcja/cel | `challenges.json`, cel punktu/NPC albo polityka fixture'a |
| Trop/informacja | `observations.json`, ujawniana informacja NPC albo efekt flagowy |
| Obiekt/fixture | zasób/fixture w eksploracji albo `scene_object` encountera |
| Walka | `exploration/encounter_triggers.json` i osobny plik/paczka encountera |
| Moment bohatera | warunkowy cel wymagający odpowiedniego `actor_id` w drużynie |
| Decyzja | węzeł i przejścia `flows.json` oraz deterministyczne efekty |
| Przejście map | continuation i jawna lista propagowanych flag/efektów |
| Zasób/stan | item questowy, zasób eksploracji, stan NPC albo flaga sceny |

## Elementy oznaczone do późniejszego doprecyzowania

- statblock oraz dokładny wygląd Głodnego Rezonansu;
- liczba i statblocki Głodnych Cieni dla drużyn 3-, 4- i 5-osobowych;
- konkretne progi trudności testów;
- reguła morale stada oraz obrońców;
- kontrakt wielorundowego rytuału i zdarzeń `round_started`;
- dokładne warunki pięciu zakończeń;
- skutki osobistych momentów bohaterów;
- sposób przekazania prywatnej informacji Mirze przy wspólnym ekranie;
- finalne pozycje wszystkich pól, stref, fixture'ów i interaction padów.

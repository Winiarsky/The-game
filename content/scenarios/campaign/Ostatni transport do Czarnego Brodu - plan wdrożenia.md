# Ostatni transport do Czarnego Brodu — ocena i plan wdrożenia

Edytowalny graf logiczny przygody znajduje się w
[`ostatni_transport_graf.md`](ostatni_transport_graf.md).

## 1. Werdykt

Materiał z dokumentu `Ostatni transport do Czarnego Brodu.pdf` nadaje się na
pierwszą docelową przygodę dla siedmiu przygotowanych bohaterów. Bardzo dobrze
pasuje do najważniejszych założeń gry:

- fizyczna plansza jest potrzebna do eksploracji, ustawiania pozycji, walki i
  obsługi elementów otoczenia;
- każda z trzech map ma rozmiar około 20×30 pól;
- sceny dopuszczają negocjacje, skradanie, improwizację, walkę i odwrót;
- porażka komplikuje sytuację, ale nie powinna blokować dalszej gry;
- cele walk wykraczają poza sprowadzenie PW wszystkich przeciwników do zera;
- wybory zmieniają stan świata i prowadzą do kilku sensownych zakończeń;
- każdy z siedmiu bohaterów ma osobistą okazję do odegrania roli;
- konflikt jest lokalny i zrozumiały, ale moralnie niejednoznaczny.

Nie rekomenduję jednak wdrażania całych 22 stron jako jednej niepodzielnej
paczki contentu. To faktycznie mała kampania albo przygoda na 1–2 długie sesje,
a nie pojedyncza scena referencyjna. Najlepszym wariantem jest podział na trzy
połączone scenariusze komponentowe:

1. `ostatni_transport_01_zawalona_droga` — zlecenie, podróż, wóz, Teren i
   Głodne Cienie;
2. `ostatni_transport_02_czarny_brod` — strażnica, uchodźcy, konflikt Marka z
   Alvenem oraz pokojowe i siłowe drogi wejścia;
3. `ostatni_transport_03_glodny_rezonans` — cysterna, zawory, rytuał,
   Głodny Rezonans i ostateczna decyzja o szarym pyle.

Prolog w Gildii powinien należeć do pierwszej paczki, a raport dla Nessy i
epilog do trzeciej. Przejścia pomiędzy paczkami powinny korzystać z istniejącego
handoffu scenariuszy, przenosząc bohaterów, czas, zasoby, ekwipunek oraz jawnie
wymienione flagi.

### Ocena dopasowania

| Obszar | Ocena | Komentarz |
|---|---:|---|
| Plansza 20×30 i LED | 5/5 | Każdy akt ma konkretną, taktyczną mapę z alternatywnymi drogami. |
| Eksploracja i fail-forward | 5/5 | Wóz, przepust, skarpa, brama, studnia, kanały i zawory naturalnie pasują do obecnych flowgrafów. |
| NPC i negocjacje | 5/5 | Nessa, Teren, Marek, Alven i Salka mają sprzeczne cele i informacje, które można ugruntować w contencie. |
| Walka | 4/5 | Pierwsze dwa encountery są wykonalne obecnymi regułami; finał potrzebuje dodatkowego kontraktu celów i zdarzeń środowiskowych. |
| Siedmiu bohaterów | 5/5 | Dokument daje każdemu wyraźny moment charakterologiczny i kompetencyjny. |
| Zakres pierwszego wdrożenia | 2/5 jako monolit, 5/5 etapami | Trzy mapy, liczni NPC, kilka encounterów i pięć zakończeń to za dużo na jeden pierwszy merge/playtest. |
| Zgodność z poziomem 3 | 4/5 | Należy przeliczyć DC, obrażenia i liczbę przeciwników dla 3–5 bohaterów na poziomie 3. |

## 2. Najważniejsza decyzja projektowa: siedmiu dostępnych, nie siedmiu naraz

Aktualny runtime pozwala utworzyć drużynę z 1–5 bohaterów wybranych spośród
siedmiu. Scenariusz powinien być projektowany przede wszystkim dla 3–5 postaci,
nie dla siedmiu jednocześnie.

Wszystkie osobiste sceny powinny istnieć w contencie, ale pojawiać się tylko,
gdy dany bohater jest w drużynie. Nie mogą być wymagane do ukończenia
głównego wątku. Przykładowo:

- Nimra daje najlepszą drogę do zrozumienia anomalii, ale rytuał musi być
  możliwy również z innym bohaterem dysponującym odpowiednią wiedzą,
  dokumentami albo pomocą NPC;
- Mira może odkryć kanał lub znak Jedwabnego Sznura, lecz strażnica musi mieć
  także drogę negocjacyjną i siłową;
- Brakka może podtrzymać podporę, ale zawalenie lub ewakuacja nie mogą
  wymagać obecności Brakki;
- Lorian może uwięzić Rezonans dźwiękiem, ale nie może to być jedyne
  zakończenie oszczędzające pył.

Balans należy sprawdzać osobno dla drużyn trzy-, cztero- i pięcioosobowych.
Tryby 1–2 postaci mogą pozostać wspierane technicznie, lecz powinny otrzymać
wyraźne ostrzeżenie o wysokiej trudności albo dodatkowego sojusznika NPC.

## 3. Co obecny silnik już obsługuje

Poniższych elementów nie należy implementować na nowo ani zaszywać w kodzie
specjalnie dla Czarnego Brodu:

- komponentowe paczki scenariusza i bezpieczny scaffold;
- strefy eksploracji, punkty, wyzwania, obserwacje i deterministyczne flowgrafy;
- cele NPC, nastawienie, ograniczenia wiedzy, kluczowe kwestie, próby i trwałe
  zmiany stanu NPC;
- wybór prowadzącego, pomocnika albo testu całej drużyny;
- testy umiejętności, przewaga/utrudnienie i konsekwencje sukcesu, porażki,
  sukcesu częściowego oraz porażki popychającej fabułę naprzód;
- widoczne i ukryte informacje, przeszukiwanie, światło, pułapki i zagrożenia;
- sceniczne fixture'y: drzwi, zamki, pojemniki, elementy uszkadzalne,
  odłączalne oraz dostarczające materiałów;
- improwizację i crafting z elementów sceny;
- ekwipunek, ciężar, walutę, łupy oraz zużywalne zasoby;
- walkę z terenem trudnym, przeszkodami, osłoną, wysokością umowną,
  obiektami interaktywnymi i celami flagowymi;
- przejście eksploracja → encounter → eksploracja oraz przeniesienie wyniku;
- odwrót, kapitulację, zwycięstwo i zakończenie przez osiągnięcie celu;
- czas scenariusza, odpoczynki, checkpointy i wznowienie zapisanej gry;
- przejścia pomiędzy paczkami wraz z przenoszeniem stanu drużyny;
- generowanie papierowych map i walidację ich manifestów;
- warunkowe momenty przypisane do konkretnego bohatera;
- fizyczne karty siedmiu bohaterów i ich zasoby na poziomie 3.

## 4. Elementy wymagające adaptacji lub rozszerzenia

### 4.1. Finałowa walka jest bardziej złożona niż obecny standard

Głodny Rezonans ma być jednocześnie przeciwnikiem, zagrożeniem środowiskowym i
zagadką. Obecny system obsługuje interaktywne obiekty oraz cele oparte na
flagach, ale nie posiada jeszcze kompletnego, data-driven kontraktu dla:

- rytuału rozwijanego i bronionego przez kilka rund;
- automatycznych zmian mapy na początku kolejnych rund;
- podnoszenia i opuszczania poziomu wody;
- przenoszenia grup cywilów w trakcie walki;
- zwycięstwa wyliczanego z kilku alternatywnych kombinacji celów.

Rekomendowany minimalny rozwój silnika przed finałem:

1. generyczny `progress_objective`, który otrzymuje postęp przez interakcje w
   walce i może wymagać kilku sukcesów;
2. generyczne zdarzenia `round_started` z warunkami i efektami contentowymi;
3. możliwość zakończenia encountera przez jedną z kilku autorskich gałęzi
   flag, a nie wyłącznie przez wszystkie cele naraz;
4. stan kanałowania/rytuału, który zużywa akcję, może zostać przerwany i
   nie jest konkretnym zaklęciem jednej klasy.

Każdy z tych prymitywów powinien być ogólny i testowany poza contentem Czarnego
Brodu. Nie należy dodawać do UI warunków typu `if scenario_id == ...`.

Jeżeli celem jest szybszy pierwszy playtest, wersja MVP finału może użyć
trzech zwykłych obiektów-zaworów, statycznego trudnego terenu i jednej końcowej
interakcji rytualnej odblokowywanej po ustawieniu zaworów. Dynamiczną wodę oraz
wielorundowe kanałowanie należy wtedy jawnie oznaczyć jako etap późniejszy,
a nie udawać ich samą narracją.

### 4.2. Dynamiczna woda i zawalenia

Na pierwszą wersję mapa powinna zawierać trzy jawne rodzaje pól:

- suchy pomost — normalny ruch;
- płytka woda — trudny teren;
- głęboka woda — pole z ograniczeniem wejścia albo autorskim zagrożeniem.

Zawory powinny ustawiać flagi `valve_n_closed`, zmieniać opis sytuacji i
osłabiać akcje Rezonansu. Fizyczna mapa nie może wymagać przekładania całej
warstwy terenu co rundę. Jeśli poziom wody ma się zmieniać, należy przygotować
małą liczbę jednoznacznie oznaczonych stref oraz nakładki papierowe albo markery.

### 4.3. Cywile

Nie należy ustawiać kilkudziesięciu osobnych pionków. Tłum w strażnicy
powinien być stanem strefy i licznikiem paniki. Tylko 1–3 fabularnie istotne osoby
mogą być aktorami albo fizycznymi punktami:

- Salka;
- Alven;
- ewentualnie jedno pole reprezentujące grupę cywilów.

Atak w strażnicy może zwiększać `civilian_panic`, blokować pokojowe cele i
zmieniać konsekwencje zakończenia. Obrażenia cywilów powinny wynikać z jawnych
zagrożeń lub efektów obszarowych, nie z arbitralnej narracji LLM.

### 4.4. Morale, ucieczka i rozwiązania bez zabijania

Głodne Cienie powinny próbować uciec po pokonaniu przywódcy albo po osiągnięciu
progu strat. Jeśli nie powstanie jeszcze ogólny system morale, encounter może
zakończyć się autorską flagą `pack_broken`, ustawianą po pokonaniu przywódcy,
odstraszeniu ogniem, użyciu dzwonu lub oddaniu pożywienia.

Obrońcy strażnicy nie mogą być traktowani jak standardowi wrogowie walczący do
śmierci. Powinni mieć jawny próg przerwania walki, jeżeli:

- Marek zostanie przekonany do rozejmu;
- zagrożeni są cywile;
- drużyna osiągnie cel bez dalszej przemocy;
- obrońcy stracą zdolność utrzymania bramy.

### 4.5. Zakłócanie czarów przez Rezonans

Sformułowanie z PDF-u jest zbyt nieprecyzyjne do implementacji. Rezonans nie
powinien losowo anulować kart czarów ani odbierać graczom zasobów bez widocznej
reguły. Należy wybrać jeden lub dwa czytelne efekty, na przykład:

- ograniczony atak wywołujący test koncentracji;
- reakcję po rzuceniu czaru w wodzie;
- strefę wymagającą rzutu obronnego przeciw przyciągnięciu;
- premię obronną Rezonansu, dopóki nie zamknięto odpowiedniej liczby zaworów.

Reguła musi być widoczna przed podjęciem decyzji i korzystać z istniejących
rzutów obronnych, warunków, reakcji albo zasobów.

### 4.6. Szary pył musi być policzalnym stanem, nie tylko flagą fabularną

Należy reprezentować cztery skrzynie i rozsypany pył w sposób, który pozwala
jednoznacznie odtworzyć:

- ile skrzyń odnaleziono;
- ile zabezpieczono;
- ile otwarto lub uszkodzono;
- ile zużyto przy anomalii;
- ile przekazano Raven;
- ile ukryto albo zadeklarowano jako zniszczone.

Najbezpieczniejszy model to cztery stabilne instancje przedmiotu questowego oraz
osobny licznik rozsypanego pyłu. Nie wolno przechowywać tej samej prawdy
równocześnie w niezależnym liczniku, ekwipunku i kilku niesynchronizowanych
flagach. Zakończenia powinny wynikać z jednego autorytatywnego stanu.

### 4.7. Sekrety osobiste przy wspólnym ekranie

Znak Jedwabnego Sznura i propozycja Kella zakładają, że Mira może zachować
informację dla siebie. Obecny interfejs jest wspólny dla całego stołu i nie ma
prywatnego ekranu gracza. W pierwszej wersji należy wybrać jedną z opcji:

- prezentować scenę jawnie i pytać Mirę, co przekazuje drużynie;
- przekazać graczowi Miry fizyczną notatkę;
- zrezygnować z faktycznej tajności, zachowując decyzję fabularną.

Nie należy dodawać całego systemu prywatnych ekranów tylko dla tej jednej
sceny.

## 5. Adaptacja treści do zasad gry

### Poziom i trudność

Określenie „poziom początkowy” należy zastąpić: „drużyna 3–5 bohaterów na
poziomie 3”. Progi testów powinny używać projektowych tierów trudności zamiast
ręcznie wpisywanych przypadkowych DC. Każdy test powinien mieć:

- informację dostępną bez rzutu;
- stawkę znaną przed rzutem;
- konsekwencję porażki, która zmienia czas, hałas, zasób, pozycję albo
  nastawienie, ale nie zamyka jedynej drogi;
- regułę krytycznego sukcesu i krytycznej porażki tylko tam, gdzie faktycznie
  mają sens.

### Głodne Cienie

Pierwszy encounter powinien być krótki i pokazywać:

- osłonę przewróconego wozu;
- trudny teren bocznego zejścia;
- wysokość skarpy albo wieży;
- obejście przez przepust;
- co najmniej dwa rozwiązania bez walki;
- ucieczkę stada zamiast obowiązku dobicia wszystkich zwierząt.

Młoda bestia jest dobrym wyborem fabularnym, ale decyzja musi mieć później
mały, widoczny skutek: zmianę nastawienia Terena, Salki albo uchodźców, trop do
anomalii albo konsekwencję podczas podróży. Bez skutku scena stanie się pozornym
wyborem.

### Strażnica

Strażnica powinna być przede wszystkim sceną społeczną z możliwością walki,
nie obowiązkowym drugim encounterem. Najważniejsze stany to:

- stosunek obrońców do drużyny;
- poziom paniki cywilów;
- stan bramy i wejść alternatywnych;
- zaufanie Marka, Alvena i Salki;
- prawda poznana o transporcie;
- dostęp do lecznicy, magazynu i cysterny;
- liczba i stan skrzyń pyłu;
- zużycie lekarstw oraz żywności.

Na jednej lokacji/instancji należy pokazywać najwyżej siedem działań zgodnie
z kontraktem UI. Dziedziniec, izba celna, lecznica, magazyn i stajnia powinny być
osobnymi instancjami lub punktami, a nie jednym panelem ze wszystkimi NPC.

### Cysterna

Finał powinien mieć cztery czytelne warstwy:

1. pozycje i zagrożenie Rezonansu;
2. trzy zawory jako fizyczne punkty interakcji;
3. rytuał lub inne alternatywne rozwiązanie;
4. stan skrzyń pyłu i droga odwrotu.

Gracz musi w każdej chwili rozumieć bieżący cel. Nie należy jednocześnie
wyświetlać pięciu równorzędnych zadań. Kolejne cele powinny się ujawniać albo
zmieniać priorytet wraz z flagami i stanem rundy.

## 6. Proponowana architektura paczek

Każda z trzech paczek powinna zostać utworzona przez
`scripts/scaffold_scenario.py`, a następnie zachować standardowy podział:

```text
content/scenarios/ostatni_transport_0x_.../
  scenario.json
  actors.json
  environment.json
  objectives.json
  llm_context.json
  print_maps.json
  exploration/
    party_start_zone.json
    zones.json
    points.json
    challenges.json
    encounter_triggers.json
    npc_transitions.json
    observations.json
    flows.json
    traps.json
    resources.json
    initial_resources.json
  assets/
  interaction_forms/
```

Encountery bojowe mogą pozostać osobnymi plikami scenariuszy wskazywanymi z
`encounter_triggers.json`. Wspólne definicje przeciwników, szarego pyłu i
unikalnych cech powinny trafić do katalogu contentu i być referencjami, jeżeli
mają wystąpić więcej niż raz.

### Minimalny kontrakt handoffu 01 → 02

- stan Terena: uratowany, porzucony, zdolny do drogi;
- prawda poznana o zajściu;
- manifest i znaleziona paczka lekarstw;
- stan młodej bestii;
- poziom hałasu/alarmu;
- wybrana trasa i czas przybycia;
- osobiste informacje odkryte przez bohaterów;
- aktualne PW, zasoby, ekwipunek i czas drużyny.

### Minimalny kontrakt handoffu 02 → 03

- nastawienie Marka, Alvena, Salki i obrońców;
- panika oraz bezpieczeństwo cywilów;
- kto schodzi do cysterny;
- stan lekarstw i żywności;
- prawda o otwartej płycie i próbie oczyszczenia;
- liczba, położenie i stan skrzyń szarego pyłu;
- przygotowane liny, ładunki, drogi odwrotu i inne trwałe przygotowania;
- aktualne PW, zasoby, warunki i czas drużyny.

## 7. Plan wdrożenia i testowania

### Etap 0 — zamknięcie briefu

Zakres:

- potwierdzić drużynę docelową 3–5 bohaterów poziomu 3;
- ustalić, czy pierwszym releasem jest tylko Mapa 1, czy od razu cała
  trzyczęściowa przygoda;
- spisać prawdę scenariusza, informacje jawne i informacje ukryte;
- ustalić autorytatywny model czterech skrzyń;
- zatwierdzić pięć zakończeń i warunki ich dostępności;
- wybrać zakres tajemnicy Miry przy wspólnym ekranie.

Test/akceptacja:

- każdy główny fakt ma jedno źródło prawdy;
- każdy obowiązkowy problem ma co najmniej dwie drogi rozwiązania;
- nieobecność dowolnego bohatera nie blokuje przygody;
- każde zakończenie wynika z policzalnego stanu, a nie oceny LLM.

### Etap 1 — scaffold i kontrakt trzech paczek

Zakres:

- utworzyć trzy paczki bez nadpisywania istniejących plików;
- dodać minimalne nagłówki, strefy startowe i continuation 01 → 02 → 03;
- dodać manifesty map z roboczymi placeholderami;
- dodać formularze interakcji dla wszystkich ważnych NPC, przeszkód i
  obiektów.

Testy:

```bash
scripts/safe_pytest.sh --timeout 60 tests/unit/test_scenario_authoring.py
scripts/safe_pytest.sh --timeout 60 tests/unit/test_scenario_loader.py
scripts/safe_pytest.sh --timeout 60 tests/unit/test_scenario_continuation_flow.py
PYTHONPATH=src python scripts/audit_content.py content
```

Akceptacja:

- wszystkie trzy paczki ładują się tym samym loaderem co scenariusze
  referencyjne;
- istniejące scenariusze nadal przechodzą audyt;
- continuation nie przenosi niejawnych albo technicznych flag przypadkiem.

### Etap 2 — prolog Gildii

Zakres:

- Nessa jako NPC z celami: przyjęcie zlecenia, pytania o transport,
  negocjowanie zaliczki i analiza dokumentów;
- oddzielić prawdę o własności pyłu od wiedzy Nessy i tego, co ujawnia;
- zaliczka i premia muszą być realną walutą albo kontraktem, nie obietnicą LLM;
- odblokować wymarsz dopiero po przyjęciu zadania.

Testy:

- cele rozmowy są dostępne tylko w odpowiednim stanie flowgrafu;
- nie można uzyskać wielokrotnie tej samej zaliczki;
- Nessa nie zdradza ukrytej motywacji bez wyniku testu lub odpowiedniej kwestii;
- odrzucenie negocjacji nadal pozwala przyjąć zlecenie;
- zapis i wczytanie zachowują kontrakt oraz walutę.

Uruchamiać przede wszystkim testy NPC, flowgrafu, efektów i sesji UI w małych
partiach.

### Etap 3 — Mapa 1: eksploracja Zawalonej Drogi

Zakres:

- wóz jako fixture z osłoną, blokowaniem ruchu, przeszukaniem i materiałami;
- skarpa, przepust, wieża i strumień jako osobne, czytelne punkty lub strefy;
- Teren jako NPC z trwałym stanem ran, pragnienia, strachu i ujawnionej prawdy;
- manifest, lekarstwa i pierścień jako rzeczywiste przedmioty/stany;
- tropy trasy i anomalii jako stopniowane obserwacje;
- warunkowe sceny siedmiu bohaterów.

Testy:

- każdy punkt zajmuje stabilne pole i nie zmienia numeru po zniknięciu innego;
- w instancji jest najwyżej siedem akcji oraz czerwone wyjście;
- przeszukanie nie przenosi automatycznie przedmiotu do ekwipunku;
- zabranie lekarstw jest osobną, potwierdzaną operacją;
- dokładne leczenie Terena zużywa właściwy zasób tylko raz;
- porażka na skarpie lub w przepuście kosztuje ruch/czas/hałas, ale nie
  blokuje mapy;
- sceny osobiste pojawiają się wyłącznie dla obecnych bohaterów;
- checkpoint odtwarza stan Terena, wozu i zebranych przedmiotów.

Testy automatyczne powinny objąć odpowiednie pliki `test_exploration_*`,
`test_exploration_fixture_actions.py`, `test_exploration_collection.py` oraz
scenariuszowe przypadki w osobnym nowym pliku testowym.

### Etap 4 — encounter Głodne Cienie

Zakres:

- przygotować skalowane warianty liczby bestii dla 3, 4 i 5 bohaterów;
- dodać przywódcę stada i warunek złamania morale;
- umożliwić walkę, pożywienie, ogień, dzwon, obejście oraz uspokojenie;
- wykorzystać wóz, skarpę, przepust i strumień w geometrii encountera;
- zachować decyzję o młodej bestii.

Testy:

- każda pokojowa metoda ma deterministyczne wymagania i koszt;
- zasób nie jest zużywany przed potwierdzeniem;
- stado ucieka po spełnieniu warunku morale;
- wygrana nie wymaga dobicia uciekających stworzeń;
- przeciwnicy nie wybierają nielegalnych tras ani zajętych pól;
- osłona, zasięg, teren trudny i wysokość są czytelne w preview;
- wynik wraca do eksploracji i zachowuje stan mapy oraz Terena;
- encounter jest wykonalny bez odpoczynku zarówno drużyną 3-, 4-, jak i
  5-osobową.

Po tym etapie Mapa 1 stanowi pierwszy kompletny, wydawalny vertical slice. Dopiero
po jego fizycznym playteście należy zamrozić wzorzec kolejnych map.

### Etap 5 — handoff do strażnicy

Zakres:

- wybór szybszej drogi głównej albo wolniejszego szlaku przy anomalii;
- wpływ czasu, hałasu, Terena i rozpoznania na pierwszy kontakt;
- jawne podsumowanie przenoszonych konsekwencji.

Testy:

- wszystkie kombinacje sukces / częściowy sukces / fail-forward uruchamiają
  drugi scenariusz;
- nowa paczka zachowuje aktualne PW, zużyte zasoby, przedmioty i czas;
- statyczne definicje bohaterów pochodzą z docelowej paczki/rosteru, a stan
  zmienny z handoffu;
- zapis scenariusza źródłowego powstaje przed przejściem.

### Etap 6 — Mapa 2: Strażnica Czarnego Brodu

Zakres:

- strefy: brama, dziedziniec, izba celna, lecznica, magazyn, kuchnia, stajnia i
  zejście do cysterny;
- Marek, Alven, Salka i Kell jako oddzielne interakcje/NPC;
- wejście pokojowe, infiltracyjne i siłowe;
- brama, brona, barykada, magazyn oraz studnia jako fixture'y;
- trwały konflikt racji, lekarstw i skrzyń;
- osobiste sceny siedmiu bohaterów;
- walka tylko jako konsekwencja decyzji, nie obowiązkowy przerywnik.

Testy:

- każda droga wejścia prowadzi do spójnego stanu wnętrza;
- pokojowe wejście nie wymaga oddania broni bez możliwości jej odzyskania;
- infiltracja wykryta zmienia nastawienie i cele NPC, ale nie psuje scenariusza;
- siłowe wejście uruchamia poprawny setup i nie ustawia cywilów jako
  standardowych wrogów;
- dokumenty Raven aktualizują wiedzę drużyny, nie zmieniając automatycznie
  decyzji finałowej;
- skrzynie i zapasy nie mogą zostać zebrane dwukrotnie;
- rozmowy zachowują stan po opuszczeniu i ponownym wejściu;
- żadna odpowiedź generatywna nie może wymyślić dodatkowej skrzyni,
  lekarstw, nagrody ani faktu o anomalii.

### Etap 7 — fundament finałowej mechaniki

Zakres:

- wdrożyć albo jawnie odroczyć `progress_objective`, zdarzenia rundowe,
  alternatywne warunki zwycięstwa i kanałowanie;
- dodać generyczne testy mechanik bez zależności od nazwy scenariusza;
- dopiero potem połączyć je z Cysterną.

Testy jednostkowe:

- postęp nie wzrasta dwa razy od jednego potwierdzenia;
- koszt akcji jest pobierany przed zastosowaniem legalnego efektu i nie jest
  pobierany dla odrzuconej deklaracji;
- przerwanie kanałowania zachowuje albo resetuje postęp zgodnie z jawną polityką;
- zdarzenie rundowe uruchamia się raz na odpowiedniej granicy rundy;
- zapis/wczytanie w połowie celu odtwarza identyczny stan;
- spełnienie jednej alternatywnej gałęzi kończy scenę tylko wtedy, gdy wszystkie
  warunki tej gałęzi są spełnione;
- stare encountery zachowują dotychczasowe zachowanie.

### Etap 8 — Mapa 3: Cysterna i Głodny Rezonans

Zakres:

- statyczna topologia pomostów, wody, kanałów i komory rytualnej;
- trzy zawory jako osobne obiekty z kosztem akcji i czytelnym stanem LED/UI;
- Głodny Rezonans z małą liczbą jawnych, testowalnych zdolności;
- rytuał, odcięcie wody, uwięzienie, zawalenie oraz klasyczne pokonanie jako
  rozłączne lub jasno połączone gałęzie;
- ochrona skrzyń i drogi odwrotu;
- osobiste momenty bohaterów jako opcjonalne komplikacje lub okazje, nie
  osobne obowiązkowe minigry.

Testy:

- każdy zawór można obsłużyć tylko z legalnego pola i przy dostępnym koszcie
  akcji;
- stan zaworu, wody i rytuału jest widoczny oraz przeżywa snapshot;
- Rezonans nie może zajmować nielegalnego pola ani przyciągać przez ściany;
- wszystkie rzuty obronne i zakłócenia czarów używają wspólnych resolverów;
- pokonanie PW Rezonansu bez zamknięcia anomalii daje właściwe, niepełne
  zakończenie;
- zamknięcie anomalii może zakończyć encounter bez zabicia Rezonansu;
- zużycie pyłu jest atomowe i nie może spaść poniżej zera;
- każda kompozycja drużyny ma co najmniej jedną realną drogę rozwiązania;
- odwrót zachowuje aktywny problem i prowadzi do konsekwencji, nie do
  technicznego końca bez opisu.

### Etap 9 — decyzja o pyle i epilog

Zakres:

- wyliczyć dostępne zakończenia z autorytatywnego stanu pyłu, anomalii,
  mieszkańców i wiedzy drużyny;
- umożliwić raport prawdziwy, częściowy albo fałszywy;
- Nessa reaguje na fakty i kontrakt, a LLM może jedynie wybrać/odtworzyć
  zatwierdzony wariant narracji;
- nagrody, reputacja, klucz, kontakty i haki dalszej kampanii muszą mieć jawne
  efekty albo zapisane flagi.

Testy macierzowe:

1. wszystko dla Raven;
2. wszystko dla strażnicy;
3. podział;
4. zabezpieczenie tymczasowe;
5. ukrycie prawdy wykryte i niewykryte;
6. część skrzyń utracona przed finałem;
7. Alven, Marek albo Salka niezdolni do złożenia własnej relacji;
8. drużyna wraca po odwrocie zamiast po pełnym zwycięstwie.

Każdy przypadek powinien sprawdzać pieniądze, przedmioty, flagi reputacji,
treść podsumowania i dostępne dalsze zadania.

### Etap 10 — mapy, QR/LED i pełny playtest

Zakres:

- przygotować trzy finalne mapy 50×75 cm i warianty A4;
- sprawdzić kontrast LED na czarno-białym wydruku;
- ustalić fizyczne znaczniki zaworów, skrzyń, poziomu wody i cywilów;
- wykonać pełny przebieg bez cyfrowej mapy;
- przeprowadzić co najmniej dwa playtesty innymi składami bohaterów.

Komendy bramki jakości:

```bash
python scripts/generate_print_maps.py --manifest content/scenarios/ostatni_transport_01_zawalona_droga/print_maps.json
python scripts/generate_print_maps.py --manifest content/scenarios/ostatni_transport_02_czarny_brod/print_maps.json
python scripts/generate_print_maps.py --manifest content/scenarios/ostatni_transport_03_glodny_rezonans/print_maps.json
PYTHONPATH=src python scripts/audit_content.py content
scripts/safe_pytest.sh --timeout 60 tests/unit/test_content_audit.py
```

Manualna macierz:

- drużyna 3-osobowa bez Nimry i Miry;
- drużyna 4-osobowa z jednym pełnym czarującym;
- drużyna 5-osobowa z Dagną, Lorianem i Nimrą;
- droga pokojowa do strażnicy;
- infiltracja wykryta;
- wejście siłowe i późniejsza próba rozejmu;
- finał przez obrażenia;
- finał przez rytuał;
- finał bez zużycia całego pyłu;
- odwrót i wznowienie z checkpointu;
- zapis pomiędzy każdą z trzech paczek;
- skanowanie kart, zasobów i reakcji każdego obecnego bohatera.

## 8. Kolejność prac rekomendowana do pierwszego grywalnego wydania

### Release OT-0: dokumentacja

- brief, prawda scenariusza, diagram flag i formularze interakcji;
- bez finalnych grafik;
- bez nowych mechanik runtime.

### Release OT-1: Zawalona Droga

- prolog Nessy;
- pełna Mapa 1;
- Teren;
- Głodne Cienie z drogami bez walki;
- decyzja o trasie;
- handoff do pustej jeszcze paczki Strażnicy.

To powinien być pierwszy cel produkcyjny i pierwszy fizyczny playtest.

### Release OT-2: Czarny Bród

- pełna Mapa 2;
- Marek, Alven, Salka i Kell;
- pokojowe, skryte i siłowe wejście;
- ekonomia lekarstw, żywności i skrzyń;
- handoff do Cysterny.

### Release OT-3: Głodny Rezonans

- generyczne brakujące prymitywy finału;
- Mapa 3;
- wielocelowy encounter;
- wszystkie zakończenia i epilog.

### Release OT-4: polish

- finalna grafika map i kafelków;
- audio/narracja, jeżeli będą potrzebne;
- balans po playtestach;
- skrócenie powtarzalnych komunikatów;
- pełna checklista UI-5 na fizycznej planszy.

## 9. Na co szczególnie uważać

1. **Nie budować trzech map naraz.** Najpierw należy doprowadzić Mapę 1 do
   pełnego, fizycznego playtestu.
2. **Nie kodować fabuły w UI.** Wszystkie fakty, cele, flagi, warianty i
   konsekwencje należą do contentu.
3. **LLM nie rozdziela zasobów.** Skrzynie, lekarstwa, jedzenie, pieniądze,
   reputacja i obrażenia zmienia wyłącznie deterministyczny silnik.
4. **Nie zakładać obecności konkretnego bohatera.** Osobiste sceny są
   dodatkiem, a nie kluczem do głównego przejścia.
5. **Nie zmuszać do walki.** Dokument jest najmocniejszy wtedy, gdy negocjacje,
   odstraszenie, obejście i odwrót są prawdziwymi rozwiązaniami.
6. **Nie ukrywać kosztu decyzji do czasu wyniku.** Gracze powinni znać
   podstawową stawkę przed wydaniem zasobu lub rzutem.
7. **Nie mnożyć testów bez decyzji.** Oględziny powinny dawać podstawową
   informację bez rzutu; d20 jest potrzebne dopiero przy ryzyku lub stopniowanym
   odkryciu.
8. **Pilnować budżetu siedmiu akcji na instancję.** Strażnica musi być
   podzielona na czytelne miejsca.
9. **Ograniczyć liczbę fizycznych pionków cywilów.** Tłum powinien być stanem
   strefy, nie osobną armią aktorów.
10. **Każda wielka decyzja musi wrócić w epilogu.** Młoda bestia, Teren,
    racje, kłamstwo Miry, autorytet Garrana i decyzja o pyle powinny mieć
    proporcjonalny, choć nie zawsze duży skutek.

## 10. Ostateczna rekomendacja

Warto wdrożyć ten materiał. Ma wyraźną tożsamość, korzysta z fizycznej
planszy lepiej niż liniowy loch i sprawdza niemal wszystkie filary projektu:
eksplorację, NPC, zasoby, improwizację, walkę, karty postaci, konsekwencje oraz
zapis stanu.

Warunkiem powodzenia jest potraktowanie go jako trzech kolejno wydawanych
scenariuszy, a nie jednego wielkiego zadania. Mapa 1 jest bardzo dobrym pierwszym
produkcyjnym scenariuszem: ma jedną lokację, jednego ważnego NPC, jeden encounter,
kilka dróg rozwiązania i naturalny punkt zakończenia. Dopiero jej playtest
powinien otworzyć produkcję Strażnicy, a dopiero Strażnica — najbardziej
ambitnego finału w Cysternie.

## 11. Stan weryfikacji repozytorium przed rozpoczęciem prac

Weryfikacja wykonana 2026-08-05 potwierdziła, że testy scaffoldu, loadera,
continuation oraz większości audytu działają na obecnej bazie: 48 testów
przeszło, a jeden test zbiorczego audytu nie przeszedł z powodu wcześniej
istniejącej kolizji w scenariuszu laboratorium mechanik:

```text
interaction_pad_overlaps_marker:
scenarios/mechanics_playground/scenario.json
exploration.zones.social_lab.interaction_pad_positions:
pole (12, 18) pokrywa się z polem lokacji lub punktu
```

Audyt zgłasza też oczekiwane ostrzeżenie o braku zadeklarowanej licencji co
najmniej jednego lokalnego source packa `project_original`.

Kolizja z `mechanics_playground` nie podważa wykonalności Czarnego Brodu i nie
została zmieniona w ramach tej analizy, ale powinna zostać poprawiona przed
uznaniem pierwszej nowej paczki za przechodzącą bramkę content-production. Dzięki
temu nowy scenariusz nie odziedziczy niejednoznacznej, już czerwonej bazy audytu.

# Osobiste pule wspólnej many — plan wdrożenia i ewaluacji

Data: 2026-09-14. Status: pierwotny plan, zastąpiony opisem wdrożenia.
**Bieżące reguły, zakres wykonany i ograniczenia:** [wdrożenie 1.0](POOLED_MANA_IMPLEMENTATION.md).
Poniższy szeroki plan obejmuje również przyszły runner pełnych walk; obecny ewaluator ocenia ekonomię kart.
Roboczy identyfikator nowego profilu: `pooled_mana_v01`.
Poprzedni profil walki: `shared_mana_v03`.

## 1. Cel i ustalone reguły

Zastępujemy płatności z pięciokartowego rynku gromadzeniem osobistych pul.
Decyzja: wykorzystać mniejszą zdolność teraz czy trzymać zasób na mocniejszą,
ograniczając dostęp drużyny do kart i ryzykując utratę puli przez mana drain.

- Wspólna talia: po `max(5, liczba bohaterów + 1)` kart kolorów C/B/Z/F/N.
  Skalowanie wybrano po próbach ekonomii; wymaga dalszego ogrania.
- Na początku walki odkrywamy dwie karty. Na początku własnej tury bohater
  obowiązkowo bierze jedną; druga zostaje. Przed kolejnym wyborem uzupełniamy
  ofertę do dwóch. Jeżeli dostępna jest tylko jedna karta, gracz bierze ją.
- Osobiste pule są jawne i przechodzą między turami. Każdy bohater ma własne
  wartości pięciu kolorów. Nie ma limitu 21 ani kary za jego przekroczenie.
- Zdolność ma minimalną sumę punktów, ewentualny warunek kolorystyczny i efekty
  podbić. Kolor może jednocześnie spełniać warunek i wzmacniać efekt.
- Płatna zdolność zużywa całą pulę. Zwykły atak jest bez many, zachowuje koszt
  akcji. Wszystkie pozostałe ograniczenia działań, celów i koncentracji obowiązują.
- Wydana pula wraca na spód talii w kolejności dobrania, BEZ tasowania.
  Odkryta karta pozostaje na miejscu. Nie ma zwykłego stosu odrzuconych.
- Spalone karty leżą oddzielnie i wracają dopiero przy drain lub opisanym odzysku.
- Atak może spalić odkrytą kartę albo N kart z wierzchu. Niemożność wykonania
  pełnego spalania powoduje drain, także brak celu dla spalenia odkrytej karty.
  Odkrytą ofertę uzupełniamy dopiero przy następnym obowiązkowym doborze.
- Drain następuje również, gdy przy obowiązkowym doborze brak kart w talii
  i w ofercie. Zbieramy wszystkie pule, spalone karty i pozostałe stosy,
  tasujemy komplet, wystawiamy dwie karty. Drain nie daje dodatkowego doboru,
  akcji, tury, reakcji ani odnowienia pasywek. Przerwany obowiązkowy dobór trwa dalej.
- Lorian wykonuje manipulację po zwrocie własnego kosztu na spód.
  Późniejsze wydawanie many nie tasuje wierzchu. Drain zbiera także uwięzione karty.
- Rozmowy, obiekty i ich system do 21 pozostają osobnym modelem eksploracji.
  Wejście/wyjście z walki wymaga jawnego odtworzenia właściwego układu fizycznych kart.

## 2. Decyzje do zamknięcia w pierwszym etapie

Nie traktujemy poniższych propozycji jako już zatwierdzonych reguł.

1. Akcje dodatkowe, reakcje, podtrzymania i przywołania: każdej istniejącej
   zdolności przypisać `free` z jawnym limitem albo `whole_pool`. Bez ukrytych
   częściowych płatności. Osobno ocenić, czy mała reakcja jest warta utraty ulta.
   Szał → Potężne uderzenie, Hymn i aktywacja Duchowego oręża wymagają jawnego
   projektu całej sekwencji. Nowe odzyski nie mogą tworzyć nieskończonych działań.
2. Efekty O: usunąć zależność ich czasu od zwykłego tasowania. Każdemu nadać
   osobny czas/warunek wygaśnięcia. Drain sam z siebie nie resetuje buffów;
   odstępstwa muszą być zapisane przy efekcie. Czasy T zachowują swój kontrakt.
3. Przekroczenie maksymalnej liczby podbić: liczyć do jawnego limitu; jeśli
   podbicia są alternatywne lub wymagają różnych celów, wybór nadal jest potrzebny.
   Wirtualna zamiana koloru musi określać wpływ na próg, warunek i podbicia
   oddzielnie, bez fizycznego tworzenia szóstej karty danego koloru.
4. Nieprzytomność, śmierć, opuszczenie walki, pominięta tura i tymczasowa jednostka:
   kiedy dobór następuje i gdzie wraca pula. Przywołania nie powinny potajemnie
   dodawać drużynie darmowych doborów. Nie przyjmować, że siedem dostępnych
   postaci oznacza siedmiu graczy w każdej walce.
5. Początek/koniec walki: proponowane puste pule i kompletna talia na starcie;
   bez gromadzenia many przez fikcyjne tury poza walką. Potwierdzić zasady przed
   pomiarem czasu dojścia do ulta, bo początkowa pula silnie zmienia wyniki.
6. Kolejność wrogiej zdolności: zapowiedź → reakcje/obrona → zatwierdzony efekt
   obrażeń/spalania → ewentualny drain → dalszy ciąg walki. Każdy efekt określa,
   czy spalanie zależy od trafienia, porażki obrony czy działa niezależnie.
   Niewykonalne spalanie wywołuje jeden drain, bez ponawiania tego samego spalania
   na świeżej talii. Pozostałe, odrębne efekty zdolności nie znikają.

## 3. Stan, źródła danych i zasady wykonania

### Jeden katalog liczb

Nowy wersjonowany katalog pod `content/balance/pooled_mana/`:

- `heroes.json`: wartości kolorów, role, nowe definicje pasywek i skaz, referencje
  do istniejących statystyk; tylko jawne eksperymentalne nadpisania cech.
- `abilities.json`: stabilne id, typ akcji, minimum punktów, wymagane kolory,
  sposób płatności, podbicia/limity, cele, efekty, czas trwania, warunki użycia.
- `enemies.json`: warianty testowe obrażeń, spalania, częstości, zapowiedzi,
  obron i kontrdziałań; produkcyjne potwory przez istniejący system contentu.
- `experiments.json`: drużyny, scenariusze, strategie, zakresy parametrów,
  liczby przebiegów i oczekiwania projektowe z wersją.

Katalog przechowuje parametry typowanych efektów, nie kod do `eval` ani kopię
całego silnika walki. Runtime, generator kart, samouczki i ewaluator czytają
te same zatwierdzone definicje. Warianty eksperymentalne są osobnymi plikami;
skrypt nigdy automatycznie nie nadpisuje aktywnego balansu.

Walidator odrzuca ujemne wartości, płatne zdolności uruchamiane pustą pulą,
warunki wymagające nieistniejących kolorów/liczb kart i nieznane efekty.
Dla bazowej talii można wyliczyć wszystkie 6^5 = 7776 układów liczebności
kolorów w osobistej puli (0–5 każdego koloru): sprawdzić osiągalność zdolności
i minimalną liczbę kart. To test matematycznej możliwości, nie prawdopodobieństwa
uzbierania puli przed końcem walki lub drain.

### Silnik kart i dwie reprezentacje talii

Proponowane nowe moduły: `rules/pooled_mana.py`,
`rules/pooled_mana_catalog.py`, `scenarios/pooled_mana_catalog.py` (odczyt danych),
`combat/pooled_mana.py`, `application/pooled_mana_flow.py`.

Czysty stan obejmuje ofertę, pule po actor_id, spalone kolory, licznik talii,
znane informacje o wierzchu, wersję profilu/katalogu, fazę, rewizję,
identyfikator obsłużonej tury i trwającą transakcję zdolności.

- Runtime fizyczny zna kolory ujawnione przez graczy; nie wymyśla kolejności
  fizycznie potasowanej talii. Dwie początkowe karty i każde nowe odkrycie
  trzeba zarejestrować. Wybór między dwiema już znanymi kartami przenosi kartę
  w stanie bez ponownego pytania o jej kolor.
- Przy spalaniu wierzchu również zgłaszamy kolory; dzięki temu sumy per kolor,
  odzysk i informacje o składzie pozostają prawdziwe. Koszt tej obsługi mierzymy.
- Symulator utrzymuje pełną kolejność w pamięci i dostarcza te same zdarzenia
  odkrycia do wspólnego silnika. Strategia gracza dostaje wyłącznie publiczny
  widok i informacje zdobyte legalnym podglądem.
- Zwykłe tasowanie unieważnia wiedzę o kolejności, nie o składzie talii.
  Fizyczne tasowanie kończy się potwierdzeniem; symulowane ma zapisany seed.
- Zawsze: talia + oferta + pule + spalone + karty w operacji = 25,
  a dla każdego koloru suma = 5. Stany przejściowe nie mogą zgubić karty.
- Deklaracja waliduje cele, akcję, pulę i skazę. Płatność zamraża sumę, kolory,
  podbicia i wersję definicji. Ich wynik pozostaje dostępny po opróżnieniu puli.
- Anulowanie przed płatnością jest bezkosztowe. Po płatności nie przywraca puli
  ani nie pozwala bezpłatnie zmieniać zdolności. Zwrot na spód przed efektami,
  np. odzyskiem; całość jest wznawialna, chroniona przed ponownym żądaniem/skanem.

## 4. Przebudowa siedmiu postaci

Audyt obejmuje 66 aktualnych zdolności i osobny Święty symbol Dagny. Liczba
run pozostaje istniejącym ograniczeniem interfejsu; nie dokładamy skilli tylko
dlatego, że zmienia się ekonomia. Dla każdego id przygotować wiersz stary→nowy:
rola, czas akcji, punkty, kolory, podbicia, czas efektu, pasywa/skaza, lekcja.

| Bohater | Co zachować i co sprawdzić w szczególności |
|---|---|
| Garran | Ochrona i koordynacja; reakcje, aury, Mowa, Kontratak i akcje sojusznika |
| Brakka | Szał i mocne uderzenia; użyteczność ataku podczas oszczędzania, czerwone podbicia |
| Mira | Pozycjonowanie i ukrycie; warunki na planszy, tempo małych zdolności i skaza |
| Dagna | Leczenie/ochrona; ratowanie sojusznika zamiast oszczędzania, podtrzymanie oręża |
| Lorian | Wsparcie, pozostawianie koloru, strojenie i odzysk spalonych kart; zapobieganie drain |
| Nimra | Kontrola, obszary i zmiana planu pod kolory; metamagia i powtarzanie zdolności |
| Erynd | Mobilność, wybór celu i łuk; Znak, Celowanie oraz sens zwykłych strzałów |

Nie wymuszać identycznego DPR ani tego samego progu ulta u każdego bohatera.
Preferencje kolorów mają się częściowo nakładać, a słabsze kolory nadal mieć
zastosowanie. Przykład Brakki (7/1/3/4/4 w C/B/Z/F/N) nie jest gotową tabelą
dla produkcji. Najpierw stroimy manę/koszty/efekty; cechy, KP i PW dopiero po
diagnozie, żeby nie naprawiać ekonomii kosztem eksploracji i podstawowych testów.

## 5. Ewaluator: trzy poziomy, wspólne reguły

Istnieją `scripts/check_exploration_mana_balance.py` i
`scripts/check_social_mana_balance.py`. To porównania strategii eksploracji,
nie symulator nowego combatu. Wykorzystać sposób seedowania i raportowania,
ale nie importować UI ani kopiować formuł efektów do osobnej uproszczonej walki.

### A. Ekonomia kart — pierwszy działający raport

Uruchomić wiele kolejek tur na skończonej talii dla siedmiu tabel wartości,
różnych składów, kolejności inicjatywy, kosztów i strategii. Mierzyć dojście do
progu/kolorów, utrzymywanie pul, wydawanie, zapychanie oferty i drain. Ten poziom
nie ocenia wygrywania walki ani wartości leczenia, terenu czy kontroli.

### B. Pełna walka bez przeglądarki

Runner korzysta z rzeczywistego silnika tur, akcji, obrażeń, leczenia, stanów,
zasięgów, map, reakcji i AI przeciwników. Dostarcza zamiast człowieka legalne
wybory i zamiast fizycznych kości wyniki z seeda. Jeżeli istniejący resolver
jest schowany w UI, wyodrębnić tylko potrzebną orkiestrację do application/combat.
Raport jawnie wskazuje zdolności, których runner jeszcze nie obsługuje; brak
obsługi nie może być raportowany jako słabość postaci lub zerowe użycie.

Scenariusze: pojedynczy cel, grupa słabszych, przeciwnik opancerzony, mapa z
osłonami/przewężeniem, obrona celu/limit tur, presja na leczenie, utrata odkrytej
karty, spalanie wierzchu, zapowiadany duży drain. Warianty bez spalania, z nim
i bez konkretnej pasywy/barda pokazują zmianę wyniku w porównywalnych warunkach.

### C. Sesja przy stole

Logować wybory, liczbę operacji kart i wejść planszy. Zmierzyć rzeczywisty czas
decyzji, fizycznego tasowania i wpisywania spalonych kolorów. Czas wykonania
symulatora NIE jest czasem tury człowieka. Symulacja nie dowodzi, że gra jest
ciekawa, a przechowywanie kart nie powoduje konfliktów przy stole.

### Strategie graczy

- `basic_only`: zwykłe legalne ataki; nadal obowiązkowy dobór i wynikający drain.
- `spend_early`: używaj pierwszej sensownej dostępnej zdolności.
- `save_ultimate`: zbieraj pod ulta; dodatkowo wariant uparcie oszczędzający.
- `adaptive`: zmieniaj plan pod pulę, cele, PW, pozostałą talię i zapowiedzi.
- `cooperative`: uwzględniaj potrzeby następnych bohaterów, ratowanie obiegu
  i rolę wsparcia; ograniczony wgląd jak u prawdziwych graczy.
- `random_legal`: słaby punkt odniesienia, nie główny przeciwnik dla optymalizatora.

Każda strategia musi umieć używać wszystkich badanych typów efektów. Scenariusze
izolowane sprawdzają zdolności przed porównaniem całości. Rotować inicjatywę,
bo pozostawiona karta i spalanie pomiędzy turami mogą faworyzować konkretne miejsca.

### Macierz doświadczeń i parametry

Osobne jednostki to własna tura bohatera, runda i cała walka. Zacząć od
trzyosobowych składów oraz solowych prób funkcjonalnych. Następnie wszystkie
35 trójek siedmiu bohaterów, obsługiwane rozmiary 1–5 i skrajny test 7 dla
oceny granicy 25 kart, bez automatycznego rozszerzania selektora drużyny.

Przeszukiwane parametry: pięć wartości na bohatera, progi i warunki, siła/limity
podbić, limity pasywów i skaz, siła/częstość/zapowiedź spalania oraz dopiero
później wybrane parametry bojowe. Liczba kart może być osobnym eksperymentem,
lecz profil bazowy nadal zawiera dokładnie 25; walidator używa konfiguracji.

Najpierw analizy pojedynczych zmian ±1 i niewielkie siatki parametrów; potem
losowe przeszukiwanie i lokalna poprawa kandydatów. Ograniczyć zakresy, aby
nie produkować ułamkowych kosztów lub dziesiątek wyjątków. Nie potrzeba LLM,
uczenia sieci ani dodatkowych zależności do pierwszej wersji.

Przy przeszukiwaniu ustalić skalę punktową: jednoczesne pomnożenie wszystkich
wartości i progów przez tę samą liczbę zwykle daje identyczną ekonomię.
Nie raportować takiego przeskalowania jako poprawy balansu ani przeszukiwać
niepotrzebnie równoważnych konfiguracji. Progi do prób dopasować do docelowej
liczby własnych tur, nie do arbitralnego przywiązania do liczby 21.

### Raport

| Grupa | Metryki |
|---|---|
| Dostępność | P50/P90 własnych tur do progu i pierwszego użycia, odsetek walk bez osiągnięcia ulta, brak punktów vs brak koloru |
| Decyzje | Udział zwykłych ataków, użycie każdej legalnej zdolności, podbicia, niewydana nadwyżka, odrzucenie dostępnego ulta |
| Obieg | Wielkość pul, czas przetrzymania koloru, zaleganie oferty, liczba tasowań/spaleń, drain według przyczyny |
| Straty | Punkty i karty utracone przy drain na bohatera, kumulacja kolejnych drainów, możliwość odbudowy |
| Wynik | Wygrana/cel sceny, rundy, przeżycie, skuteczne obrażenia bez overkill, realne leczenie bez overheal |
| Wsparcie | Zapobiegnięte obrażenia, odebrane działania, uratowani sojusznicy, wpływ manipulacji many na wynik drużyny |
| Obsługa | Liczba decyzji, potwierdzeń, kart do zgłoszenia i tasowań; oddzielnie pomiary ludzi |

Nie sprowadzać wszystkiego do jednej sumy punktów. Raport podaje próbę,
przedziały niepewności, mediany/ogony rozkładu i różnice względem wariantu bazowego.
Nie liczyć czasu ulta tylko w walkach, w których wystąpił: raportować również
walki zakończone przed jego uzyskaniem i odsetek nieosiągnięcia do N-tej tury.
Zerowe użycie zdolności dzielić przez okazje, kiedy była legalna i potrzebna.
Wpływ wsparcia oceniać również przez porównania ze zdolnością wyłączoną, bez
arbitralnego uznania jednej odzyskanej karty za określoną liczbę obrażeń.

Raport HTML do lokalnego przeglądania + JSON/CSV; filtrowanie postaci, składu,
strategii, scenariusza, wariantu i inicjatywy. Macierz użycia zdolności,
wykres dojścia do ulta, obieg kart oraz oś zdarzeń dla przykładowej/podejrzanej
walki. Ostrzeżenia: niemożliwy warunek, dominacja jednej strategii w wielu
scenach, ulty poza długością walk, spirala drain, nieużyteczne kolory, nadmiar
obsługi. Każde ostrzeżenie ma dane i odtwarzalny przebieg; nie ogłasza samo nerfa.

### Powtarzalność i dobór kandydatów

Manifest: wersja reguł, hash całego contentu, kod/commit i informacja o lokalnych
zmianach, strategie, scenariusze, seed, limity, liczba zakończonych prób.
Oddzielne strumienie losowości talii, kości i decyzji, aby inna liczba tasowań
nie przesuwała sekwencji trafień. Porównania używają sparowanych seedów, ale
różne strategie nadal mogą prowadzić do różnych zdarzeń; nie obiecywać identycznej walki.

Przegląd kandydatów na małych próbach, potem większe próby finalistów i osobne
seedy/scenariusze walidacyjne nieużywane do doboru parametrów. Raportować
kompromisy (np. częstszy ult kosztem martwej średniej zdolności), a nie jednego
pozornie najlepszego bohatera. Docelowe widełki zapisujemy po pierwszym raporcie
i decyzji o pożądanym tempie walki; nie wymyślamy dzisiaj procentu zwycięstw.

Ograniczony czas/liczba tur na próbę, osobna kategoria timeout/stalemate/error;
nie liczyć ich jako porażek. Domyślnie jeden proces, małe porcje, checkpoint,
wznowienie i agregacja strumieniowa. Pełne logi tylko dla wybranych seedów/błędów.
Przy limicie rund trzeba zakończyć również wewnętrzną pętlę jednej tury.

## 6. UI, plansza, zapis i wydruki

- Na początku tury: instrukcja odkrycia brakujących kart, zgłoszenie kolorów
  runami, potem wybór jednej z dwóch znanych kart. Identyczne kolory są legalne.
  Zachowana karta na ekranie nie jest ponownie wpisywana w następnej turze.
- Widok główny: własna pula/suma, tabela wartości, oferta, licznik talii/spalonych,
  zapowiedź wroga; krótkie powody niedostępności umiejętności (punkty/kolory/cel/akcja).
  Pule drużyny są dostępne do rozwinięcia. Nie wyświetlać procentów bez danych.
- Podbicia automatyczne podsumowują się przed płatnością; wybór tylko przy
  faktycznej alternatywie lub wymaganych celach. Osobne wskazanie zużywanej
  całej puli i limitów, żeby gracz nie oczekiwał reszty z płatności.
- Decyzje przez istniejące runy i fizyczne pola celów, stabilne przypisania
  zdolności. Rzuty: fokus kości, −/+, ✓ do następnej, końcowe podsumowanie/↩.
  UI/LED/maska skanu korzystają z jednego kontraktu legalnych wyborów.
- Spalanie/drain prowadzi przez fizyczne operacje i ✓. Ponowne kliknięcie,
  reconnect lub wczytanie nie powtarza doboru, płatności ani drain.
- Wersjonowany zapis przechowuje fazę i potwierdzenia. Stare zapisy 0.3 nie mogą
  automatycznie zamieniać wspólnego rynku na czyjeś osobiste pule. Dokończenie
  starej walki w starym profilu; nowy profil na jawnej granicy nowej walki.
  Stare zaliczenia lekcji zachować, nowe mechaniki mają nowe identyfikatory zaliczeń.
- Druk wszystkich siedmiu postaci: wartości kolorów, progi, warunki, podbicia,
  pasywy, skazy, zwykły atak, czas efektów i skrót obiegu/drain. Zachować treści
  NPC/obiektów. Manifest zapisuje profil i wersję katalogu; wszystkie formaty,
  HTML/pomoc i pakiet areny generować z tego samego zatwierdzonego zestawu.

## 7. Samouczek i próba całości

Wspólne podstawy: dobór/pozostawienie koloru → zwykły atak i zachowanie puli →
próg oraz wydanie wszystkiego → kolor/podbicie → współpraca dwóch bohaterów →
spalona odkryta karta → spalanie wierzchu/zapowiedź → uratowanie obiegu → drain.
Oddzielna lekcja Loriana uczy tasowania i manipulacji po płatności.

Dla każdego z siedmiu bohaterów: tabela wartości, pasywa, skaza, wszystkie
utrzymane zdolności i istotne warianty podbić, reakcje/podtrzymania oraz wybór
„użyj teraz albo zachowaj”. Układy przygotowane jawnie w lekcjach mechaniki;
swobodne ćwiczenia ze zwykłą talią i prawdziwymi konsekwencjami.

Zachować schemat Nessa → setup → działanie → podsumowanie; nie wymuszać
dłuższej liniowej lekcji na każdą możliwą kombinację kolorów. Na koniec walka
bez gwarantowanej many, z zapowiadanym zagrożeniem obiegu. Rozmowa z NPC,
interakcja z obiektem i zwykłe pułapki pozostają osobnymi dostępnymi ćwiczeniami.

## 8. Etapy realizacji i kryteria ukończenia

| Etap | Wynik do sprawdzenia | Główne miejsca zmian |
|---|---|---|
| 1. Kontrakt i audyt | Decyzje z sekcji 2, mapa wszystkich 67 zdolności, 7 pasywów/skaz i O; eksperymentalny katalog | `content/balance/pooled_mana/`, `rules/shared_mana_catalog.py`, `rules/physical_mana.py`, `character_creation/physical_mana.py` |
| 2. Rdzeń i ekonomia | Legalne przejścia, pierwszy raport obiegu, wszystkie 7 profili; brak wycieku wiedzy o talii | Nowe `rules/pooled_mana*`, loader, `evaluation/pooled_mana/`, `scripts/evaluate_combat_mana.py` |
| 3. Pełna walka pilotażowa | Brakka, Nimra, Lorian, podstawowe działania i przeciwnik spalający; porównanie strategii na prawdziwym silniku | `combat/pooled_mana.py`, `application/pooled_mana_flow.py`, istniejące resolvery i runner |
| 4. Cały katalog i przeciwnicy | Wszystkie 7 postaci, wszystkie utrzymane zdolności/pasywy/skazy, role, reakcje, aury, brak nieobsługiwanych efektów w raporcie | `combat/shared_mana*.py`, źródła postaci, `actors/triggers.py`, `combat/triggers.py`, `application/enemy_turn_flow.py`, content |
| 5. UI i zapis | Pełna walka przez planszę, rejestracja kart, podbicia, drain, wznowienie faz | `ui/shared_mana.py`, `ui/shared_mana_board.py`, `ui/combat_menu_mana.py`, `ui/exploration_app.py`, `ui/static/shared_mana.js`, `save/session_snapshot.py` |
| 6. Samouczek | Wspólne podstawy, lekcje 7 postaci, swobodne ćwiczenia i zachowane NPC/obiekty | `application/training_walkthrough*`, `application/recruitment_arena.py`, `ui/training_arena.py`, `ui/static/training_arena.js`, `content/tutorials/recruitment_arena.json` |
| 7. Karty i walidacja | Zgodny komplet HTML/PDF, raport finalistów, test fizyczny i poprawki | `physical_cards/mana_print*.py`, `scripts/generate_mana_character_prints.py`, `scripts/build_arena_print_pack.py`, dokumentacja |

Etapy 2–4 tworzą pętlę: katalog → raport → diagnoza → kontrolowana zmiana →
powtórzenie i walidacja. Nie czekamy z pierwszym raportem na UI i druk.
Interfejs można oprzeć na wersjonowanym katalogu przed końcem strojenia liczb;
finalne wydruki następują po wyborze kandydata. Pilotaż 3 postaci nie zastępuje
obowiązkowego zakończenia prac nad pozostałymi 4.

## 9. Testy i definicja ukończenia

- Unit: każda operacja zachowuje karty/kolory; oferta 0/1/2 i duplikaty,
  dokładny próg/nadwyżka/warunek, podbicia i zamiany, cała pula, oba rodzaje
  spalania i niedobór, brak ponownego drain/doboru, Lorian i unieważnienie wiedzy.
- Sekwencje generowane z seedów sprawdzają inwarianty bez nowej zależności.
  Małe ręcznie policzone układy sprawdzają statystyki i polityki; odtwarzanie
  jednej sekwencji przez runner i runtime daje te same efekty.
- Integracja: akcje D/R/MOD, nieprzytomność, koniec walki, czas efektów,
  koncentracja, przeciwnik/reakcje, migracja oraz save/load w każdej fazie.
- UI/browser: wybór wyłącznie planszą, duplikaty kolorów, brak legalnych celów,
  stare skany, fokus −/+ i podsumowanie, desktop i mały ekran.
- Katalog/druk/samouczek: te same liczby i wersja, wszystkie postacie/id,
  każda skaza/pasywa wykonywalna i nauczana, brak odwołań do starej płatności.
- Regresja: NPC/obiekty i ich utrudnienie za >21, pułapki, ogólne postacie 5e,
  stare zapisy i istniejące mechaniki walki niezależne od profilu.
- Testy pojedynczymi plikami przez `scripts/safe_pytest.sh --timeout 60`;
  dłuższy jawnie określony limit tylko dla uzasadnionego batcha. Jeden pytest
  i domyślnie jeden runner ewaluacji, bez równoległych ciężkich zadań.

Ukończenie oznacza grywalne siedem postaci, raport obejmujący ich realne efekty,
spójne karty i samouczki oraz opis ograniczeń i wynik próby fizycznej. Samo
przejście testów nie jest potwierdzeniem balansu. Na dziś przygotowano wyłącznie plan.

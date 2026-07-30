# Docelowy interfejs gracza

## Status dokumentu

Ten dokument definiuje docelowy kierunek przebudowy web UI dla wspólnego monitora
przy fizycznej planszy. Nie zmienia reguł gry ani kontraktów domenowych. Jest podstawą
do kolejnych, małych etapów implementacji UI.

Koncepcyjne mockupy ustalają klimat dark fantasy, ale nie są specyfikacją układu.
W szczególności cyfrowe mapy, minimapy i diagramy pozycji widoczne na mockupach nie
powinny trafić do produktu, ponieważ powielałyby fizyczną planszę.

## Główna zasada

> Fizyczna plansza pokazuje przestrzeń. Monitor prowadzi decyzje, zasady, narrację
> i konsekwencje.

Plansza pozostaje podstawowym interfejsem dla:

- pozycji aktorów i obiektów,
- legalnych pól ruchu i wybranej ścieżki,
- legalnych celów oraz pola aktualnie wskazanego,
- obszarów czarów, linii i kierunków,
- jawnych miejsc interakcji,
- krótkiego przestrzennego feedbacku: trafienie, leczenie, zagrożenie i efekt.

Plansza pełni też rolę pasywnego wskaźnika uwagi. Kiedy monitor wywołuje konkretną
postać do rzutu, pokazuje mówiącego NPC albo prowadzi działanie jednego obiektu,
jego pole jest podświetlone bez rozpoczynania skanu. Zapisanie wyniku lub zamknięcie
akcji usuwa focus; jeśli następna postać od razu przejmuje prompt, LED przechodzi na
jej pole.

Monitor pozostaje podstawowym interfejsem dla:

- narracji MG oraz rozmów z NPC,
- informacji, czyja jest tura i czego gra teraz oczekuje,
- wyboru pomiędzy wieloma intencjami przypisanymi do jednego pola,
- kosztów, warunków, modyfikatorów i konsekwencji przed zatwierdzeniem,
- wpisywania wyników fizycznych kości,
- HP, stanów, koncentracji, zasobów i ekonomii akcji,
- wyników rozstrzygnięć i trwałych zmian stanu,
- ekwipunku, czarów i danych szczegółowych otwieranych na żądanie.

Monitor nie powinien domyślnie pokazywać:

- cyfrowej mapy ani minimapy,
- cyfrowych odpowiedników figurek i ich współrzędnych,
- ścieżki ruchu, gdy jest już podświetlona na planszy,
- diagramów zasięgu lub obszaru, gdy pokazują je LED-y,
- pełnego arkusza postaci podczas zwykłej tury,
- debug payloadów, technicznych identyfikatorów i mechaniki MG na powierzchni gracza.

Wyjątkiem może być tryb diagnostyczny albo symulator planszy uruchamiany świadomie
przez twórcę. Nie jest on częścią domyślnego doświadczenia gracza.

## Hierarchia informacji

Każdy stan UI ma odpowiadać kolejno na cztery pytania:

1. **Co dzieje się teraz?** — jedna dominująca narracja albo instrukcja.
2. **Kto lub co wymaga decyzji?** — aktywny aktor, NPC, cel albo reakcja.
3. **Jakie są legalne wybory?** — tylko opcje dostępne w tym momencie.
4. **Co się stanie po zatwierdzeniu?** — koszt, rzut, ryzyko i istotne cele.

Informacje dzielimy na trzy poziomy:

- **zawsze widoczne:** aktualny tryb, aktywny aktor, najważniejszy prompt i krytyczne
  stany;
- **kontekstowe:** menu wskazanego pola, parametry próby, cele efektu, reakcja;
- **na żądanie:** pełny ekwipunek, lista czarów, historia, szczegóły efektów i debug.

Jeżeli informacja nie zmienia bieżącej decyzji, nie powinna rywalizować z głównym
promptem. Powinna trafić do panelu szczegółów albo historii.

## Wspólna powłoka aplikacji

Wszystkie tryby korzystają z jednej powłoki, dzięki czemu przejście eksploracja →
encounter → walka nie wygląda jak uruchomienie innej aplikacji.

Początkowy setup przebiega w kolejności: podłączenie planszy, ustawienie jawnych
elementów mapy, przygotowanie czarów postaci, a następnie wybór pierwszej lokacji.
Przygotowanie czarów jest ostatnim krokiem setupu, nie ekranem poprzedzającym
konfigurację planszy.

### Pasek górny

Zawiera wyłącznie:

- nazwę scenariusza i aktualnej lokacji,
- aktualny tryb: eksploracja, rozmowa, przygotowanie encountera albo walka,
- kompaktowy stan drużyny: portret/nazwa, opisowy poziom HP i krytyczne stany,
- przycisk otwierający panel dodatkowy.

W walce miejsce nazwy trybu może zająć kompaktowa kolejka inicjatywy. Nie pokazujemy
pełnych statystyk wszystkich uczestników.

### Obszar główny

Ma dokładnie jeden dominujący kontekst. Może nim być chat, bieżąca decyzja bojowa,
formularz rzutu albo blokująca reakcja. Nie układamy obok siebie kilku równorzędnych
paneli z działaniami.

### Panel dodatkowy

Panel otwierany na żądanie zawiera zakładki zależne od trybu:

- Drużyna / Postać,
- Stany i efekty,
- Czary,
- Ekwipunek,
- Odkrycia i zasoby sceny,
- Historia,
- Zapis gry,
- MG/debug, tylko w świadomie włączonym trybie deweloperskim.

Konfiguracja hardware, adres symulatora, log sesji i surowy payload nie mogą być
kartami stale obecnymi w głównym flow gracza.

### Pasek komunikatów

Krótkie potwierdzenia pojawiają się jako toast lub wpis historii. Blokujący alert
jest używany tylko wtedy, gdy gracz musi coś zrobić przed kontynuacją. Jeden stan
nie powinien być równocześnie powtarzany w nagłówku, karcie i historii.

### Uniwersalne karty sterujące

Czytnik QR może działać przez całą sesję jako wejście typu keyboard-wedge.
`ACCEPT` wywołuje tę samą główną operację co Enter i widoczny przycisk
potwierdzenia. `DECLINE` wywołuje bieżące odrzucenie, anulowanie albo pominięcie.
Karty nie wskazują własnego endpointu reguł i nie omijają walidacji aktualnego
stanu. Po skanie monitor pokazuje jeden krótki toast z nazwą karty i informacją,
czy znaleziono pasującą operację. Nie dodajemy osobnego panelu skanera do głównego
flow, a przyciski ekranowe pozostają równoważnym fallbackiem.

## Widok eksploracji

Eksploracja jest pełnoekranową rozmową z MG.

### Wejście do interakcji

Pierwszą wiadomością MG jest:

- ilustracja sceny, jeżeli istnieje,
- tytuł lokacji lub punktu,
- opis fabularny bez listy rozwiązań i parametrów mechanicznych.

Pod spodem znajduje się jeden chronologiczny, przewijany strumień: historia,
kafle decyzji, skan planszy, formularze rozstrzygnięcia, wynik i kolejne wybory.
Podczas oczekiwania na LLM widoczny jest wpis „MG pisze…” z animowanymi kropkami.
Opcjonalna swobodna rozmowa „Zapytaj MG” jest schowana w dialogu otwieranym ze
strumienia i po wysłaniu wraca do historii.

### Zwykła rozmowa

W chat trafiają:

- wiadomości graczy,
- odpowiedzi i narracja MG,
- odkryte fakty oraz znalezione elementy sceny,
- krótkie, czytelne rezultaty zmian stanu.

Komendy slash pozostają opcjonalnym sposobem doprecyzowania intencji. Bez komendy
LLM nadal rozpoznaje ją automatycznie.

### Próba eksploracyjna

Interpretacja wymagająca rzutu pojawia się jako karta systemowa wewnątrz rozmowy,
a nie jako osobny duplikat poniżej chata. Karta zawiera:

- fabularny opis podejścia,
- prowadzącego test,
- cechę/skill/tool i ST,
- przewagę albo utrudnienie,
- nazwane modyfikatory sytuacyjne,
- jawny koszt i ryzyko,
- przyciski: Akceptuj, Zmień, Zrezygnuj.

Po akceptacji ta sama karta przechodzi w stan wpisywania rzutu. Pokazuje, jaką
fizyczną kością rzucić, jedno lub dwa pola naturalnego wyniku oraz składniki
modyfikatora. Po rozstrzygnięciu zamienia się w zwarty wynik; nie tworzymy drugiej
karty z tymi samymi danymi.

### Odkrycia i przedmioty sceny

Znalezienie przedmiotu daje wiadomość MG i kompaktowy chip/kartę odkrycia z nazwą,
cechami i stanem. Przedmiot pozostaje w scenie. Osobne działanie może go użyć,
zabrać albo przekształcić. Lista wszystkich odkryć jest dostępna w panelu dodatkowym.

### Opuszczenie interakcji

Stały przycisk „Opuść interakcję” wraca do prostego wyboru odkrytych lokacji i
punktów. Nie kasuje historii rozmowy ani jej kontekstu.

## Widok rozmowy z NPC

Rozmowa z NPC korzysta z tego samego chata, lecz nagłówek pokazuje:

- portret i imię NPC,
- jawnie rozpoznawalne nastawienie opisowe, np. „ostrożny” albo „przerażony”,
- istotny stan fizyczny lub emocjonalny, jeżeli gracze mogą go zauważyć.

Nie pokazujemy ukrytych liczników relacji, progów testów ani przyszłych branchy.

Eskalacja jest kartą blokującą w strumieniu rozmowy. Pokazuje krótko, co zrobił
NPC, oraz 2–4 authored reakcje graczy z czytelnym skutkiem kategorii, np. „wycofaj
się — zakończ rozmowę” albo „nie ustępuj — może rozpocząć encounter”. Dopiero wybór
prowadzi dalej. Karta nie może być schowana poza aktualnym viewportem.

## Etap przejścia do encountera

Przejście eksploracja → walka ma własny krótki ekran, ale używa wspólnej powłoki.
Pokazuje kolejno:

1. przyczynę rozpoczęcia encountera,
2. rezultat otwarcia: drużyna zaskakuje, brak przewagi albo przeciwnicy są gotowi,
3. ewentualne przygotowania scenariuszowe i próby Stealth,
4. instrukcję ustawienia figurek na podświetlonych polach,
5. wpisanie inicjatywy i rozpoczęcie walki.

Nie pokazuje cyfrowego rozmieszczenia. Plansza podświetla kolejny element setupu,
a monitor nazywa figurkę i oczekiwane działanie.

## Widok walki

### Stały kontekst tury

Monitor stale pokazuje:

- numer rundy i kompaktową kolejkę inicjatywy,
- aktywnego aktora,
- opisowy stan HP i krytyczne warunki,
- pozostały ruch w feet,
- dostępność: akcja, ataki w Akcji, akcja bonusowa, reakcja i interakcja z obiektem,
- jedną instrukcję następnego kroku.

Plansza pokazuje aktywną figurkę i legalne pola. Monitor nie rysuje mapy.

### Wskazanie pustego pola

Jeżeli pole ma tylko intencję ruchu, plansza pokazuje ścieżkę i pole docelowe, a
monitor wyświetla zwięzłe potwierdzenie kosztu. Jeśli projekt zachowa dwuklik jako
potwierdzenie na planszy, monitor nie wymaga dodatkowego kliknięcia.

Jeżeli pole ma kilka intencji, monitor pokazuje kontekstowe menu, np.:

- Idź tutaj,
- Podejdź i podnieś miecz,
- Podejdź i użyj dźwigni.

Opcja złożona zawsze pokazuje łączny koszt ruchu, wymagany zasięg interakcji,
ekonomię akcji oraz ewentualny atak okazyjny.

### Wskazanie przeciwnika

Monitor pokazuje pogrupowane legalne działania:

- Ataki — osobno dla każdego legalnego źródła i wariantu,
- Manewry — Shove, Grapple i inne dostępne,
- Czary,
- Przedmioty,
- Wsparcie lub działania scenariuszowe.

Każda opcja pokazuje nazwę, zasięg, koszt ekonomii i istotny modyfikator. Pełne
obliczenia pojawiają się dopiero w preview wybranej akcji. Niedostępne działania
mogą być widoczne tylko wtedy, gdy krótki powód blokady pomaga graczowi podjąć
decyzję; długa lista niedostępnych źródeł jest ukrywana.

### Kliknięcie własnego pola

Otwiera menu własne z kategoriami:

- Ruch i postawa: Padnij, Wstań, Dash, Disengage, Dodge, Hide,
- Akcje i wsparcie: Help, Ready, Search,
- Czary,
- Ekwipunek: użyj, wyposaż, schowaj, upuść,
- Lokalne interakcje na aktualnym polu,
- Zakończ turę.

Menu pokazuje wyłącznie działania legalne dla bieżącego stanu lub wyjaśnia jeden
bezpośrednio istotny powód blokady.

### Preview akcji i rzut

Po wybraniu działania obszar główny przechodzi przez jeden spójny ciąg:

1. **Preview:** wykonawca, cel wskazany na planszy, koszt, zasięg, cover,
   przewaga/utrudnienie, zasób i jawne cele obszaru.
2. **Potwierdzenie:** plansza nadal podświetla cel lub obszar.
3. **Rzut fizyczny:** duży prompt kości i pole naturalnego wyniku; dwa pola przy
   przewadze/utrudnieniu.
4. **Wynik:** wybrana kość, modyfikator, porównanie, skutek mechaniczny i krótka
   narracja.
5. **Powrót do tury:** zaktualizowana ekonomia akcji i kolejny legalny krok.

Rzut ataku, save, obrażenia i leczenie korzystają z tej samej wizualnej gramatyki.
Typ rzutu zmienia treść, nie układ całej aplikacji.

### Reakcja i przerwanie

Reakcja jest pilnym, modalnym stanem przykrywającym bieżący kontekst. Zawsze zawiera:

- powód przerwania,
- aktora posiadającego reakcję,
- cel i proponowane działanie,
- informację, kiedy reakcja wróci,
- dwie główne opcje: Wykonaj / Pomiń.

Po rozstrzygnięciu UI wraca dokładnie do przerwanego ruchu albo tury. Nie pokazuje
mapki objaśniającej geometrię; właściwe pola migają na fizycznej planszy.

### Czary obszarowe

Monitor prowadzi etapami: wybierz czar → wskaż środek/kierunek na planszy → sprawdź
cele → potwierdź. LED-y pokazują geometrię. Monitor podaje liczbę i nazwy objętych
aktorów, friendly fire, cover, slot i koncentrację, ale nie rysuje cyfrowego obszaru.

### Tura przeciwnika

Podczas automatycznej tury przeciwnika monitor pokazuje krótką intencję i kolejne
rezultaty. Plansza pokazuje ruch oraz cel. Ekran zatrzymuje się tylko dla fizycznego
rzutu gracza, reakcji albo decyzji, której silnik nie może podjąć automatycznie.

## Stany przeciążenia i przypadki brzegowe

### Dużo efektów na postaci

W głównym widoku pokazujemy maksymalnie trzy najbardziej istotne chipy oraz licznik
„+N”. Krytyczne blokady, np. Restrained albo obowiązkowy save na końcu tury, mają
priorytet nad buffami informacyjnymi. Pełna lista ze źródłem i wygaśnięciem jest w
panelu Stany.

### Wiele legalnych działań

Najpierw grupujemy je kategoriami, potem sortujemy: dostępne i często używane,
scenariuszowe, pozostałe. Filtrowanie nie może usuwać poprawnych źródeł mechanicznych.
Klawiatura: strzałki zmieniają wybór, Enter zatwierdza, Escape wraca o jeden poziom.

### Kilka obiektów na jednym polu

Monitor pokazuje jedną listę nazwanych intencji, nie listę surowych obiektów. Każda
pozycja identyfikuje obiekt oraz wynikowy czasownik: „Podnieś miecz”, „Użyj dźwigni”,
„Przeszukaj skrzynię”. „Idź tutaj” pozostaje osobną opcją, jeśli pole jest legalne.

### Brak komunikacji z planszą

UI pokazuje stały, niepanikujący komunikat „Plansza rozłączona” i oferuje Ponów oraz
tryb awaryjny. Tryb awaryjny może udostępnić techniczny wybór współrzędnych, ale musi
być jawnie oznaczony jako zastępczy i nie staje się domyślnym flow.

### Długi czas odpowiedzi LLM

Chat zachowuje wpis gracza, pokazuje „MG pisze…” i blokuje tylko kolejną deklarację
w tej samej interakcji. Odejście do panelu lub anulowanie oczekiwania nie może
skasować historii. Błąd dostawcy LLM jest przedstawiany jako możliwość ponowienia,
bez technicznego tekstu walidatora na powierzchni gracza.

### Obowiązkowe rozstrzygnięcie

Save na końcu tury, death save, koncentracja albo setup encountera blokują akcję
„Dalej”, ale ekran podaje dokładnie jedną instrukcję potrzebną do odblokowania gry.
Nieaktywne elementy tła są przygaszone.

## Język wizualny

Kierunek: ciemne fantasy, czytelne i oszczędne, bez imitowania ciężkiego interfejsu
MMO. Ornament jest ramą dla informacji, nie jej konkurencją.

- tło: grafit, ciemny kamień i skóra;
- główne powierzchnie: ciepła czerń i bardzo ciemny brąz;
- tekst: ciepła kość słoniowa;
- akcent aktywnej decyzji: stare złoto;
- ruch i wybór neutralny: błękit;
- sukces i leczenie: zieleń;
- zagrożenie, obrażenia i reakcja pilna: czerwień;
- magia i koncentracja: fiolet;
- ostrzeżenie bez bezpośredniego zagrożenia: bursztyn.

Kolor nie może być jedynym nośnikiem znaczenia. Każdy stan otrzymuje ikonę, etykietę
albo wzór obramowania. Tekst mechaniczny używa prostego kroju UI; ozdobny krój może
pojawić się tylko w dużych tytułach. Przyciski i wyniki kości muszą być czytelne z
odległości wspólnego stołu.

## Kontrakt plansza–monitor

Każdy interaktywny stan przestrzenny powinien dostarczać dwie skoordynowane części:

- **board intent:** zestaw pól, znaczenie podświetlenia i oczekiwany typ wskazania;
- **screen prompt:** instrukcja, aktualny wybór, koszt i następna decyzja.

Monitor nie może obliczać legalności niezależnie od domenowego/application flow.
Renderuje ten sam wynik, z którego adapter planszy buduje LED-y. Jeśli plansza
wskazuje pole nielegalne, monitor wyjaśnia jeden konkretny powód i pozostawia gracza
w aktualnym stanie.

## Płynny kontrakt wykonania

Plansza jest domyślnym kontrolerem przestrzennym, dlatego legalny wybór uzbraja
nasłuchiwanie automatycznie. Gracz nie powinien wykonywać osobnej czynności
„uruchom skan” przed każdym ruchem, celem lub kafelkiem. Monitor pokazuje przy
aktywnym kroku jeden z czterech stanów: przygotowanie, nasłuchiwanie, odczyt albo
bezpieczne ponowienie. Przycisk ręcznego skanu pozostaje tylko jako fallback po
timeoutcie lub utracie połączenia.

Wybranie kafelka wymagającego testu może uzbroić jeszcze jeden krótki kontrakt
planszy: wybór wykonawcy. Bohaterowie mają stałe kolory wynikające z kolejności
drużyny (czerwony, niebieski, zielony, fioletowy, pomarańczowy), a pola wyboru
oraz karty portretów pokazują to samo przypisanie. Po wskazaniu wykonawcy skan
zostaje wstrzymany. Wybór źródła, wpisywanie opisu, akceptacja warunków oraz
wpisywanie wyniku kości nie zużywają timeoutu planszy. Anulowanie formularza
czyści także wybór po stronie backendu i dopiero wtedy ponownie uzbraja pola.

Każdy kontrakt wyboru planszy ma stabilną rewizję i listę legalnych pól. Wynik
otrzymany dla nieaktualnej rewizji jest ignorowany, więc spóźniony skan nie może
uruchomić akcji należącej do poprzedniego promptu. Rozpoczęcie działania w UI
anuluje oczekujący skan, a nowy stan uzbraja kolejne nasłuchiwanie.

W czacie istnieje jedna aktywna karta kroku. Poprzednie wybory pozostają w historii
jako wiadomości i wyniki, ale nie konkurują wizualnie z bieżącą decyzją. Działania
deterministyczne bez opisu przechodzą dalej automatycznie, kiedy wykonawca, typ
testu i źródło są jednoznaczne. Opis opcjonalny ma jawny wariant wykonania bez
tekstu; opis wymagany i ocena LLM nadal zatrzymują flow.

Oczekiwanie na Gemini od razu dopisuje deklarację graczy i pokazuje odpowiedź
„NPC/MG zastanawia się…”. Aktywne kontrolki mechaniczne są wtedy zamrożone, ale
historia i boczne karty postaci, czarów oraz ekwipunku pozostają dostępne. Timeout
nie usuwa deklaracji i oferuje bezpieczne ponowienie.

LED-y zmieniają pełne klatki z krótkim przejściem zamiast sekwencji
wygaś–zapal. Animacja pocisku jest nakładana na kontekst pola walki i po przelocie
przywraca bazowe podświetlenie. Powtórzenie identycznej klatki lub ponowne
wyczyszczenie pustej planszy nie wysyła zbędnej komendy.

## Plan wdrożenia

Przebudowę należy wykonywać bez zmiany reguł i bez szerokiego refaktoringu backendu.

### UI-1 — fundament i powłoka

- tokeny kolorów, typografii, odstępów i stanów,
- wspólny pasek górny oraz panel dodatkowy,
- oddzielenie kontrolek gracza od konfiguracji/debug,
- jeden komponent promptu, wyniku, alertu i toastu.

### UI-2 — eksploracja i NPC

- pełnoekranowy chat jako dominujący widok,
- karty próby zmieniające stan bez duplikacji,
- odkrycia i NPC w tej samej gramatyce rozmowy,
- responsywny dialog „Zapytaj MG” i czytelny stan oczekiwania.

### UI-3 — encounter i walka

- osobny ekran przejścia do encountera,
- kompaktowy HUD tury bez cyfrowej mapy,
- kontekstowe menu planszy i menu własne,
- wspólny flow preview → rzut → wynik,
- modalne reakcje z poprawnym powrotem do przerwanego stanu.

### UI-4 — informacje złożone i dostępność

- panele Postać/Stany/Czary/Ekwipunek,
- priorytetyzacja wielu efektów i legalnych działań,
- klawiatura oraz czytelność z odległości stołu,
- tryb rozłączonej planszy i pozostałe przypadki brzegowe.

### UI-5 — walidacja przy stole

- scenariusz `abandoned_watchtower` jako pełny vertical slice,
- test eksploracji, NPC, przejścia i walki bez używania cyfrowej mapy,
- manualna checklista hardware,
- korekty wynikające z obserwacji graczy, nie z dodawania kolejnych stałych paneli.

Manualna checklista dla custom party:

- `Nowa gra` pokazuje wszystkie paczki eksploracyjne, a wybór faktycznie
  uruchamia wskazany scenariusz i jego właściwy setup mapy;
- wydruk A4 obu map składa się do deklarowanych 50 × 75 cm, a znaczniki rogów
  pokrywają się z planszą;
- w każdej lokacji liczba, kolejność i kolory LED-owych pól interakcji zgadzają
  się z kafelkami widocznymi w oknie rozmowy, a kliknięcie pola uruchamia
  dokładnie wskazany kafelek;
- po wybraniu testu pola wykonawców świecą stałymi kolorami drużyny, kliknięta
  postać trafia do formularza jako prowadząca, a podczas wpisywania opisu skan
  pozostaje wyłączony;
- setup walki pozwala kolejno ustawić 1, 3, 4 i 5 własnych bohaterów, bez pustego
  kroku i bez pola zajętego przez przeciwnika albo blokujący obiekt;
- przy oczekującej pułapce, obserwacji i rzucie ekran prowadzi tylko do
  obowiązkowego rozstrzygnięcia i nie przyjmuje kolejnej deklaracji;
- przy braku celu ataku komunikat odpowiada temu, co pokazują LED-y: ruch,
  zasięg albo linia widzenia;
- po ruchu, wyborze celu i obszaru podświetlenie pozostaje czytelne z normalnego
  miejsca graczy przy stole, także na czarno-białej papierowej mapie;
- po stabilnym wyniku eksploracji ponowne uruchomienie i `Wczytaj grę` odtwarza
  ostatni checkpoint.

## Kryteria akceptacji

Docelowy UI można uznać za spójny, gdy:

- gracz w każdym momencie potrafi wskazać jedną bieżącą decyzję,
- podstawowe wskazanie ruchu, celu i obszaru odbywa się na fizycznej planszy,
- ekran nie powiela mapy ani pozycji figurek,
- koszt, rzut i ryzyko są widoczne przed zatwierdzeniem,
- naturalny wynik fizycznej kości można wprowadzić bez otwierania panelu technicznego,
- historia eksploracji i NPC przetrwa opuszczenie oraz ponowne wejście do interakcji,
- reakcja lub obowiązkowy save nie gubią stanu przerwanej tury,
- informacje drugorzędne są dostępne, ale nie konkurują z aktualnym promptem,
- debug i konfiguracja hardware są dostępne dla twórcy, lecz niewidoczne w normalnej grze.

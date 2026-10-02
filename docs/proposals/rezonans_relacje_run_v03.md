# Propozycja rezonansu opartego na relacjach między runami

**Status: propozycja do dyskusji, niezatwierdzona i niewdrożona.** Liczby, połączenia run i zmiany kart są robocze. Ten dokument zachowuje pełną propozycję z rozmowy; nie zmienia obowiązujących reguł ani kodu gry.

Rezonans stałby się wspólnie przygotowywaną kombinacją, a wybór umiejętności zależałby od sytuacji na planszy i tego, co drużyna zostawiła poprzednimi akcjami. To ciekawszy kierunek niż płacenie więcej za dokładanie kolejnych ogólnych premii.

Najważniejsze rozróżnienie byłoby takie:

> **Ostatnia runa określa, czym podtrzymasz rezonans. Runy zachowane w rezonansie określają, jakie dodatkowe efekty uzyska twoja umiejętność.**

Poniżej znajduje się spójna wersja do pierwszego testu. Nazwy, przypisania run i podstawowe działania przyjęto w pierwotnej propozycji na podstawie aktualnych kart; opisane zmiany są propozycjami.

**Tak działałby pojedynczy łańcuch.**

1. **Każda umiejętność ma jeden koszt i jeden opis działania.** Dodatkowe efekty uruchamiają się automatycznie po spełnieniu warunków runicznych. Gracz nie wybiera trybu podstawowego albo wzmocnionego.

2. **Pierwsza moc rozpoczyna rezonans swoją runą.** Działa bez premii rezonansu, ponieważ wcześniej nie było żadnych run.

3. **Następna moc podtrzymuje łańcuch, jeśli jej runa pasuje do ostatniej runy.** Zachowuje dotychczasową pamięć i korzysta z odpowiednich premii swojej karty.

4. **Premie sprawdzamy przed dodaniem nowej runy.** Umiejętność nie może sama sobie dostarczyć brakującego symbolu. Dopiero po rozpatrzeniu dopisujemy jej runę.

5. **Niepasująca moc pozostaje dostępna.** Wygasza poprzedni rezonans przed swoim działaniem, wykonuje efekt podstawowy i rozpoczyna nowy łańcuch własną runą. Można więc świadomie zmienić kierunek, gdy sytuacja wymaga leczenia albo przemieszczenia.

6. **Na początek proponowana jest pamięć trzech ostatnich run.** Czwarta wypiera najstarszą, już po rozpatrzeniu mocy. Powtórzenia zajmują miejsca, ale nie mnożą premii: dwa Groty spełniają warunek „Grot”, bez dodatkowego wzmocnienia.

Limit trzech jest dodatkową propozycją. Bez niego długi łańcuch stopniowo zbierze większość symboli i zacznie automatycznie odblokowywać niemal wszystkie ulepszenia. Trzy miejsca pozwalają przygotować kombinację, ale wymagają dbania o jej kolejność.

Przykładowo:

`Wieża → Błysk → Schody`

Następna moc korzysta jeszcze z tych trzech run. Jeżeli doda Grot, pamięć po jej wykonaniu wynosi:

`Błysk → Schody → Grot`

**Relacje run proponowane na początek przedstawia poniższy układ.** Strzałka jest kierunkowa: możliwość przejścia z Wieży do Grota nie oznacza automatycznie możliwości powrotu.

| Ostatnia runa | Runa następnej mocy podtrzymującej rezonans |
|---|---|
| Wieża | Grot, Schody, Błysk |
| Grot | Klepsydra, Hak, Kielich |
| Schody | Grot, Oko, Błysk |
| Błysk | Wieża, Schody, Kielich |
| Hak | Schody, Oko, Klepsydra |
| Oko | Wieża, Grot, Węzeł |
| Kielich | Wieża, Błysk, Węzeł |
| Węzeł | Schody, Oko, Kielich |
| Klepsydra | Oko, Grot, Hak |
| Fala | Dowolna runa |

Dodatkowo **po dowolnej runie można zagrać Falę**.

To trzy możliwe symbole kontynuacji, a nie gwarantowane trzy dostępne moce każdego bohatera. Przykładowo Lorian nie ma odpowiedzi na Wieżę w swoim obecnym zestawie. Drużyna musi uwzględnić, kto działa następny; czasami rozsądne będzie rozpoczęcie nowego łańcucha. Rozkład tych połączeń wymaga ogrania z różnymi składami.

![Poglądowa grafika relacji między runami](rezonans_relacje_run_v03.png)

Grafika poglądowa została wygenerowana wbudowanym narzędziem imagegen: [pełny prompt](rezonans_relacje_run_v03_prompt.txt). Tabela powyżej jest tekstowym zapisem relacji.

**Fala byłaby specjalnością Nimry.**

Jej Mglisty krok nadal wykonuje teleportację, a runicznie działa jako most:

`dowolna runa → Fala → dowolna runa`

Fala zajmuje jedno z trzech miejsc pamięci. Nie kopiuje innych run i nie zastępuje symboli wymaganych przez umiejętność: `Wieża + Fala` nie spełnia warunku `Wieża + Grot`.

Roboczo Mglisty krok kosztowałby **5 ładunków**, z zachowaniem dopłat wynikających ze skazy Nimry. Dzięki temu podtrzymanie wymaga konkretnej mocy i wydatku.

Obecnie Falę ma również **Strzała wichru Erynda** — propozycja przenosi tę umiejętność pod **Schody**, których nie ma w jego pozostałych mocach.

**Pozostałe zasady zamykają przypadki brzegowe.**

- Pozostają: **20 ładunków**, odzysk klasowy **1k4 raz na rundę**, Skupienie za S odzyskujące **1k20**. Koszty ustalamy osobno dla każdej mocy.
- Jedna akcja specjalna pozwala dołożyć najwyżej jedną runę. Dodatkowe trafienia, reakcje i ruchy nie tworzą kolejnych ogniw.
- Zwykły atak i ruch nie przerywają łańcucha. Zakończenie własnej tury bez użycia mocy runicznej wygasza go. Skupienie wygasza go natychmiast.
- Tury przeciwników i koniec rundy nie przerywają rezonansu. Całkowicie pominięta tura nieprzytomnego bohatera również go nie przerywa.
- Legalnie użyta moc podtrzymuje łańcuch także po pudle. Nielegalna deklaracja nie pobiera kosztu ani nie zmienia run.
- Początek i koniec walki czyszczą pamięć.
- **Runy nie dają już samodzielnych, globalnych premii.** Wszystkie efekty wynikają z kart umiejętności.
- Przyznane efekty mają własny czas trwania. Jeśli moc dała ochronę do następnej tury, zakończenie rezonansu jej nie odbiera. Identyczne premie z ponownego użycia tej samej mocy nie sumują się.

To ostatnie upraszcza obsługę: warunki sprawdzamy podczas użycia, a potem rozpatrujemy już konkretny efekt karty.

Dokładnie tak działałby **Całun cienia**:

| Runy w pamięci przed użyciem | Działanie Całunu |
|---|---|
| Brak odpowiednich run | Test Zręczności przeciw pasywnej Percepcji każdego przeciwnika, jak obecnie. |
| Schody | Po udanym ukryciu przed co najmniej jednym wrogiem możesz przejść do 2 pól. |
| Grot | Przeciwnicy mają −2 do pasywnej Percepcji **przy rozpatrywaniu tej próby ukrycia**. |
| Schody i Grot | Oba powyższe efekty oraz przewaga w teście ukrycia: 2k20, wybierasz wyższy wynik. |

Dodatkowy ruch nie zużywa zwykłego ruchu. Okazyjne nadal mogą wykonywać przeciwnicy, przed którymi Mira się nie ukryła.

Całun pozostaje pod **Błyskiem**. Przykładowe przygotowanie obu premii:

`Grot → Hak → Schody → Całun/Błysk`

Analogicznie **Tarcza splotu/Klepsydra → Hymn odwagi/Oko** jest legalną kontynuacją. Hymn mógłby mieć prosty zapis: „Jeżeli w rezonansie jest Klepsydra, przyznaj kość **1k8 zamiast 1k6**”. Nadal jest jedną umiejętnością o jednym koszcie.

Dla **Garrana** proponowany jest taki zestaw. A oznacza atak, S specjalną, M ruch; nazwy cech w formułach oznaczają modyfikatory.

| Umiejętność | Koszt | Działanie i premie z pamięci |
|---|---:|---|
| **Impuls egidy — Wieża** | **4, S** | Jak obecnie: test Siły przeciw Sile/Zręczności sąsiedniego wroga; wygrana daje **1k6 + Siła** obrażeń i przesunięcie o 1 pole. **Oko:** przewaga w tym teście. **Schody:** po wygranej możesz dodatkowo przejść o 1 pole bez okazyjnych. |
| **Ostrze przełamania — Grot** | **5, A+S** | Atak wręcz; trafienie: **broń + 1k6 magicznych**. **Schody:** dodatkowe **1k6 magicznych** przy trafieniu. **Wieża:** po rozpatrzeniu ataku otrzymujesz **+1 KP do początku swojej następnej tury**, również po pudle. Obie premie mogą działać razem. |
| **Szarża bastionu — Schody** | **4, M+S** | Zachowuje wymóg pełnego ruchu, dojście do wroga i obronę Kondycji przeciw **10 + Siła + przebyte pola**; porażka powoduje Powalenie. **Wieża:** ruch szarży nie prowokuje okazyjnych. **Błysk:** cel ma **−2 do tej obrony**. |
| **Żar odnowy — Błysk** | **4, S** | Odzyskujesz **1k10 + poziom PW**. **Wieża:** otrzymujesz także **4 tymczasowe PW do początku swojej następnej tury**. **Kielich:** dodatkowo jeden sąsiedni żywy sojusznik odzyskuje **1k6 PW**. |

Żywa osłona, skaza i klasowy odzysk pozostają częścią jego tożsamości. Garran przygotowuje bezpieczne wejście innych postaci, ale potrafi też wykorzystać ustawioną przez drużynę kombinację.

Dla **Brakki**:

| Umiejętność | Koszt | Działanie i premie z pamięci |
|---|---:|---|
| **Runiczny szał — Błysk** | **5, S** | Jak obecnie: **+1k6 obrażeń wręcz**, połowa obrażeń obuchowych, kłutych i ciętych; czas równy Siła + Kondycja własnych tur. **Wieża:** dodatkowe **+1 KP do początku następnej własnej tury**. **Oko:** przewaga w najbliższym ataku bronią przed początkiem następnej własnej tury. |
| **Pęd gromu — Schody** | **4, A+S** | Ruch do **3 pól** i atak wręcz. **Wieża:** ten ruch nie prowokuje okazyjnych. **Grot:** przy trafieniu dodatkowe **1k6 obrażeń broni**. |
| **Echo gromu — Hak** | **3, S** | Słyszący wrogowie do **2 pól** wykonują obronę Mądrości przeciw **10 + Siła**; porażka utrudnia najbliższy atak przed końcem ich następnej tury. **Błysk:** zasięg wzrasta do **3 pól**. **Węzeł:** po porażce cel ma dodatkowo **−2 pola ruchu w swojej następnej turze**. |
| **Gniew runy — Grot** | **8, A+S** | **Finiszer wymagający Wieży i Błysku w pamięci.** Pełne działanie poniżej. |

Szału nadal nie można aktywować ponownie podczas jego trwania. To istotne ograniczenie: Błysk nie jest dla Brakki stale dostępną odpowiedzią.

**Gniew runy byłby pierwszą flagową mocą wymagającą przygotowania.**

Można go użyć, gdy:

- w pamięci są **Wieża i Błysk**;
- ostatnia runa pozwala kontynuować Grotem;
- Brakka ma odpowiedni cel, atak, specjalną i 8 ładunków.

Wykonuje jeden atak wręcz. Trafienie zadaje:

**obrażenia broni + 3k6 obrażeń gromowych**, a cel otrzymuje **−2 KP do początku następnej tury Brakki**.

Aktywny Szał nadal dodaje swoje **1k6**. Po pełnym rozpatrzeniu Gniewu **cały rezonans wygasa**. Dzieje się tak również po pudle; Grot finishera nie rozpoczyna nowego łańcucha.

To jedna moc o jednym działaniu, dostępna pod konkretnym warunkiem.

Na pierwszy test taki finiszer otrzymałaby Brakka, a Ostrze Garrana pozostałoby mocą budującą rezonans. **Tylko te dwie postacie mają obecnie Grot** — zamiana obu mocy w zakończenia łańcucha usunęłaby możliwość przygotowania Grota dla innych bohaterów.

Przykładowa walka wyglądałaby następująco. Grają Garran i Brakka, w tej kolejności, a po nich przeciwnicy. Garran blokuje przejście, obok walczy Brakka; dalej stoi dowódca wrogów.

| Moment | Decyzja i efekt | Pamięć po mocy |
|---|---|---|
| **Runda 1 — Garran** | **Impuls egidy, 4 ładunki.** Wygrywa test i odpycha strażnika, otwierając przejście. Rezonans był pusty, więc otrzymuje wyłącznie podstawowy efekt. | **Wieża** |
| **Runda 1 — Brakka** | **Runiczny szał, 5 ładunków.** Wieża pozwala przejść do Błysku. Szał otrzymuje premię **+1 KP do początku kolejnej tury Brakki**. Brakka wykonuje też zwykły atak, już z dodatkowym 1k6 Szału. | **Wieża · Błysk** |
| **Tury przeciwników** | Walka trwa; runy pozostają. Przeciwnicy mogą zranić bohaterów albo zmienić sytuację na planszy. | **Wieża · Błysk** |
| **Runda 2 — Garran** | **Szarża bastionu, 4 ładunki.** Błysk pozwala przejść do Schodów. Garran dociera do dowódcy: dzięki Wieży nie prowokuje okazyjnych, dzięki Błyskowi dowódca ma −2 do obrony. Przyjmijmy, że zostaje Powalony. Garran zachowuje zwykły atak. | **Wieża · Błysk · Schody** |
| **Runda 2 — Brakka** | Podchodzi zwykłym ruchem i używa **Gniewu runy, 8 ładunków**. Schody pozwalają przejść do Grota, a Wieża i Błysk spełniają warunek finishera. Atakuje Powalonego wręcz z przewagą. | **Pusto — wyładowanie** |

Przy toporze Brakki jej trafienie w ostatnim kroku zadaje:

`1k12 + 4 + 3k6 z Gniewu + 1k6 ze Szału`

Przykładowe wyniki kości: `8 + 4 + 12 + 3 = 27 obrażeń`, a do tego −2 KP celu.

Na same moce Garran wydał **8 ładunków**, Brakka **13**. Ewentualny odzysk klasowy rozliczają oddzielnie. Szał Brakki trwa dalej mimo zakończenia rezonansu.

Jest też krótsza alternatywa:

`Impuls Garrana/Wieża → Pęd Brakki/Schody → Ostrze Garrana/Grot`

Brakka bezpiecznie doskakuje dzięki Wieży. Następnie Garran korzysta z obu zapisanych symboli: Ostrze zadaje **broń + 2k6 magicznych** i przyznaje mu **+1 KP**. Rezonans pozostaje aktywny, więc Brakka może dalej odpowiedzieć Echem pod Hakiem.

To daje rzeczywisty wybór: przygotować duże wyładowanie albo wcześniej wykorzystać ruch, ochronę i umiarkowane obrażenia, zachowując łańcuch.

Przy dostosowaniu pozostałych kart zmieniłby się jeszcze pasyw **Loriana**, który obecnie odwołuje się do trybu podstawowego: „Po podtrzymaniu rezonansu pozostawionego przez innego bohatera odzyskaj 1 ładunek, raz we własnej turze, po opłaceniu i rozpatrzeniu mocy”.

Najważniejsze do sprawdzenia przy stole będzie, **czy drużyna ma kilka użytecznych sekwencji**, czy szybko odkrywa jedną powtarzaną kombinację. Szczególnie trzeba obserwować dostępność Błysku Brakki podczas Szału, ciasne przejścia między zestawami bohaterów oraz to, czy nagroda za finiszer uzasadnia wydatek i utratę pamięci.

**Zakres tej wersji:** propozycja mechaniki do dyskusji. Nie wdrożono zmian w kodzie ani kartach gry; nie uruchamiano testów kodu.

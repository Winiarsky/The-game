# Runy zamiast many — propozycja v0.1

Późniejsza korekta użytkownika: wsparcie runami w rozmowach zastępuje
[reputacja drużyny](REPUTATION_PROTOTYPE.md), start 20. Trzy wyłączne opcje
po rzucie: +1 za 1, +5 za 3, dodatkowa k20 za 5. Zamiana wozu: próg 20,
koszt 3. Opisy run w konfrontacjach poniżej są historyczną propozycją.
Istnieją już osobne wydruki i makieta; poniższy status opisuje moment
powstania pierwotnego dokumentu.

Data: 22.09.2026. **Dokument do omówienia przed wdrożeniem.** Nie opisuje
działającej wersji gry. Liczby, koszty, progi, nagrody i doprecyzowania oznaczone
jako propozycje wymagają zatwierdzenia oraz ogrania. Runtime, katalogi, UI i PDF-y
nie zostały zmienione.

## 1. Punkt wyjścia przekazany przez użytkownika

- Runy z dolnego paska zastępują manę.
- Lewa strona paska: ruch, atak bronią, przedmiot, koniec tury. Usuwamy zmianę
  broni. Wyposażenie rąk, korpusu i pozostałych slotów wybiera się przed misją.
- Co najmniej jedno puste pole przed runami i po nich. W prawym dolnym rogu
  kolejno +, −, zatwierdź, cofnij/odrzuć.
- Bazowa mapa i wszystkie kafle Misji 0 mają być większe o 3% względem
  obecnego wydruku. Liczba run (20 lub np. 10) pozostaje do rozważenia.
- Plansza obsługuje aplikację od startu. Każda dostępna kontrolka ma przypisanie
  do pola; +/− obsługują też przewijanie. Zachowujemy obecny wygląd UI poza
  zmianami wymaganymi przez zasady i obsługę.
- Konfrontacja NPC/obiektu trwa jedną rundę drużyny. Każdy wybiera podejście
  i od razu wykonuje test, bez rzutu wpływu. Sukces +1, porażka 0, naturalne
  20 +2, naturalne 1 −1. Start 0; próba zejścia poniżej −1 kończy scenę
  pogorszeniem. Szczyt toru również kończy scenę. Po ostatnim działaniu
  obowiązuje osiągnięty poziom. Długość toru zależy od liczby uczestników.
- Walka: na początku każdej rundy dobór N+2 run i wspólny podział między graczy.
  N oznacza liczbę bohaterów. Osobista ręka mieści najwyżej 7 run.
- Tura: ruch do limitu, atak bronią LUB przedmiot oraz jedna akcja specjalna.
  Wszystko opcjonalne. Moc może zajmować dwa albo wszystkie trzy elementy tury.
- Moc bazowa wymaga jednej określonej runy; do trzech dostępnych wzmocnień,
  opłacanych konkretną lub dowolną runą. Specjalne reakcje kosztują runy;
  zwykły atak okazyjny bronią jest bezpłatny (późniejsza korekta użytkownika).
- Płatne aury/pasywy są częścią kart bohaterów. Przenosimy tożsamość obecnych
  zdolności do nowych zasad.

Ten wariant **zastępuje wcześniejszą propozycję ręcznego odświeżania rynku**.
W pierwszym prototypie nie dokładamy osobnej płatnej wymiany rynku do
automatycznego doboru N+2 co rundę.

## 2. Proponowany obieg run

1. Moc jest znana od początku. Runa w ręce daje możliwość jej użycia;
   zatwierdzona aktywacja zużywa runę. Same trzymane runy nie dają premii.
2. Nowa walka: puste ręce, pełna przetasowana talia. Dobór N+2 odbywa się
   również przed pierwszą rundą, przed działaniem pierwszego uczestnika.
3. Raz na rundę gracze wspólnie przydzielają odkryte runy. Nie narzucamy
   równego podziału ani mechanizmu naprzemiennego wybierania.
4. Niewydane runy pozostają w rękach między rundami. Ręce i przydział są jawne.
   Już przydzielonych run nie przekazujemy sobie dowolnie w trakcie rundy;
   przyszła moc Loriana może oferować takie przekazanie za własny koszt.
5. Limit 7 obowiązuje po przydziale. Gracz przy limicie może zastąpić starą
   runę nową, odrzucając starą. Runy nieprzydzielone trafiają na odrzut;
   nie ma dodatkowej wspólnej rezerwy poza rękami.
6. Koszt i wariant deklaruje się przed rzutem. Pudło lub udana obrona wroga
   nie zwracają run. Cofnięcie podglądu przed zatwierdzeniem niczego nie wydaje.
7. Gdy zabraknie talii, tasujemy odrzut i uzupełniamy dobór. Nie zbieramy rąk
   ani nie resetujemy efektów. Jeśli odrzut też jest pusty, dobieramy tyle,
   ile zostało — nie tworzymy nowych run.
8. Na końcu sceny runy wracają do talii. Konfrontacja z Nessą nie jest miejscem
   ładowania ręki przed walką. Powtórne otwarcie tej samej rozstrzygniętej
   interakcji nie daje nowego doboru ani nowej próby.
9. Losuje aplikacja albo fizyczna talia — jeden sposób na daną rozgrywkę.
   Rekomendowany pierwszy prototyp: aplikacja, z zapisem kolejności talii,
   odrzutu, przydziału i rąk. Odświeżenie strony nie ponawia losowania.

**Propozycja przeciw pechowi:** dwie dowolne runy mogą zastąpić jedną wymaganą
runę bazową. Nie zastępują konkretnej runy ulepszenia. To ułatwia dostęp do
tożsamości bohatera bez zapewniania najlepszego wariantu co turę.

**Propozycja ulepszeń:** do trzech różnych dopłat na karcie, lecz przy jednym
użyciu wybór najwyżej jednej. Nie powtarzamy dopłaty. To założenie do akceptacji;
trzy kumulowane ulepszenia dawałyby mocniejsze skoki obrażeń i więcej kombinacji
do sprawdzania. Odpłatne aktywacje nie dają dodatkowego budżetu akcji.

## 3. Dziesięć rodzajów zasobów a dwadzieścia pól

To dwa oddzielne wybory. Rekomendacja robocza: **przetestować 10 rodzajów run
w talii, zachowując na razie 20 fizycznych znaków jako przyciski interfejsu**.
Dziesięć pozostałych znaków służy menu i pozostaje miejscem na przyszły rozwój;
nie udaje zasobów, których nie ma w talii. Jest to kompromis do oceny, nie
zatwierdzony docelowy układ. Alternatywą jest pełne 20 rodzajów zasobów.

Zestaw do przykładowej karty: Wieża, Klepsydra, Brama, Błysk, Oko, Korona,
Węzeł, Kotwica, Kielich, Klucz. Wszystkie są już nadrukowane na planszy.

Przy 10 typach propozycja talii to N kopii każdego: 30/40/50/60 run dla
3/4/5/6 bohaterów. Przy 20 typach można porównać 2 kopie dla 3–4 osób
i 3 kopie dla 5–6 osób. To warianty do porównania przy stole.

W 40-elementowej talii i doborze 6 szansa na co najmniej jedną konkretną runę
wynosi 49,3% przy czterech kopiach oraz 28,1% przy dwóch. Dotyczy całej wspólnej
oferty, nie gwarantowanego przydziału dla jednej osoby. Mniej typów ułatwia
składanie określonych kombinacji; więcej typów zwiększa różnorodność i ryzyko
oczekiwania na ulubioną moc.

Garran ma obecnie 9 mocy, Nimra 12. Dziesięć rodzajów zasobów nie wystarczy
na 12 niezależnych przycisków Nimry przy zasadzie „znak mocy = jej runa bazowa”.
Trzeba byłoby połączyć część jej mocy w warianty albo pozostać przy 20 typach.
Nie zmieniać wszystkich kart i druku przed taką kontrolą całej drużyny.

## 4. Tura, reakcje i czas działania

- **Ruch:** obecny limit i zasady pól; można dzielić między własne działania.
- **Zwykła akcja:** jeden zwykły atak bronią albo użycie przedmiotu.
- **Specjalna:** jedna moc z karty, opłacona runami.
- **Reakcja:** osobny limit, odnawiany na początku własnej tury. Na wejściu
  do walki dostępna jedna reakcja. Reakcja nie zużywa następnej specjalnej.

Karta „zwykła + specjalna” wymaga obu niewykorzystanych. Karta „ruch + zwykła
+ specjalna” wymaga także, żeby bohater nie wykonał jeszcze zwykłego ruchu
w tej turze; ewentualny ruch zapisany w mocy jest częścią tej mocy. Nie można
najpierw zaatakować, a potem opłacić ruchu, by obejść zabrany atak.

Korekta użytkownika: zwykły atak okazyjny bronią nie kosztuje run; zużywa
dostępną reakcję. Specjalne reakcje mają koszty swoich kart. Jeżeli zdarzenie
dopuszcza kilka reakcji, gracz wybiera jedną lub odmawia; aplikacja nie wybiera
płatnej reakcji automatycznie. Koszt pobierany jest dopiero po zatwierdzeniu.
Przeciwnicy zachowują własne opisane działania, bez wspólnej talii graczy.

**Propozycja aur:** maksymalnie jedna utrzymywana aura na bohatera. Aktywacja
kosztuje runę i wskazane akcje. Na początku następnej własnej tury, przed
pozostałymi działaniami, wybiera się opłatę podtrzymania lub wygaśnięcie.
Podtrzymanie nie jest dodatkową specjalną. Utrata przytomności i koniec sceny
kończą aurę. Zwykłe krótkie efekty mają jawny termin zamiast „do Mana Drain”.

Premie do KP z poniższych mocy Garrana nie sumują się: stosujemy najwyższą.
Tymczasowe PW także się nie sumują. Pasyw jest efektem kupionej mocy;
samo posiadanie symbolu w ręce nie uruchamia dawnego pasywu many.

**Luka wymagająca decyzji:** obecne ataki i obrony używają premii od liczby
kart zamiast dawnej biegłości. Zachowanie +1 za runę karałoby wydawanie zasobów.
Proponujemy stałą premię bazową niezależną od ręki, dobraną przy przeliczeniu
bohaterów i przeciwników. Nie zakładamy automatycznego przywrócenia całego
systemu biegłości ani dawnej listy umiejętności. Mechanizm zwykłego ataku,
obrażenia broni i bazowe cechy pozostają punktem odniesienia.

## 5. Przykładowa karta Garrana

Robocza adaptacja wszystkich dziewięciu obecnych mocy. Rola, historia, skaza
Nieustępliwość i wyposażenie pozostają. Przykład zakłada miecz i tarczę
wybrane przed misją, SIŁ +4 i KON +2. Moc wymagająca tarczy jest niedostępna
bez wyposażonej tarczy. Poza przypisaniem nowych kosztów zmieniamy niektóre
siły efektów i czasy — nie jest to sama wymiana grafiki.

W tabeli „+symbol” oznacza dodatkowo zużytą runę. Alternatywy rozdzielone
średnikiem oznaczają wybór jednej. „Do następnej tury” znaczy do początku
następnej własnej tury Garrana, chyba że opis podaje inaczej.

| Runa i moc | Zajęte działania | Podstawa | Dostępne dopłaty — wybierz najwyżej jedną |
| --- | --- | --- | --- |
| Kotwica — Uderzenie tarczą | Specjalna | Sąsiadujący wróg, tarcza. Sporny test Siły; remis broni cel. Wygrana: 1k6 + SIŁ obrażeń i odepchnięcie o 1 wolne pole. | +dowolna: +1k4 obrażeń; +Błysk: +1k6 obrażeń; +Klepsydra: trafiony ma połowę ruchu do następnej tury. |
| Kielich — Drugi oddech | Specjalna | Odzyskaj 1k10 + KON PW, do maksimum. Proponowany limit: raz na walkę, niezależnie od tasowania. | +dowolna: +1k4 leczenia; +Wieża: dodatkowo 5 tymczasowych PW. |
| Wieża — Pozycja obronna | Specjalna | +2 KP do następnej tury. Każda zmiana pola kończy postawę. | +Kotwica: ochrona przed przymusowym przesunięciem; +dowolna: 5 tymczasowych PW. |
| Klepsydra — Rozkaz: Stać! | Specjalna | Wróg do 12 pól, obrona MDR ST 14. Porażka: połowa ruchu i brak reakcji do następnej tury Garrana. Sukces: brak efektu. | +Kotwica: zamiast połowy ruchu — ruch 0; +Korona: drugi wróg do 2 pól od pierwszego, z własną obroną. |
| Węzeł — Osłona towarzysza | Reakcja | Przed rzutem pojedynczego ataku na sąsiada przejmij atak. Porównanie z KP Garrana, obrażenia dla niego. Nie działa na obszary. | +Wieża: ewentualne obrażenia mniejsze o 1k6; +dowolna: mniejsze o 1k4; minimum 0. |
| Brama — Osłona tarczą | Specjalna | Z tarczą: sąsiadujący sojusznicy +2 KP do następnej tury Garrana, bez premii dla niego. Ochrona kończy się dla postaci, gdy przestaje sąsiadować z Garranem. | +Kielich: jeden chroniony otrzymuje 5 tymczasowych PW; +Kotwica: chronieni mają ochronę przed przymusowym przesunięciem. |
| Korona — Mowa dowódcy | Specjalna | Garran i słyszący sojusznicy do 3 pól usuwają Strach. Jeden z uczestników dostaje przewagę pierwszego ataku do następnej tury Garrana. | +Węzeł: przewaga dla wszystkich uczestników; +Kielich: jeden uczestnik odzyskuje 1k6 PW; +dowolna: przewaga dla drugiego uczestnika. |
| Klucz — Żelazny bastion | Zwykła + specjalna | Aura o promieniu 2 pól: Garran i sojusznicy +1 KP i ochrona przed przymusowym przesunięciem. Działa do następnej tury. | +Wieża: premia +2 KP; +Brama: promień 3 pól. |
| Błysk — Rozkaz: Kontratak! | Ruch + zwykła + specjalna | Garran i sojusznik do 3 pól mogą przejść po 2 pola bez ataków okazyjnych i wykonać po jednym zwykłym ataku. Sojusznik musi wydać reakcję i jedną własną dowolną runę. | +dowolna: obaj mogą przejść o 1 pole dalej; +Kotwica: pierwsze trafienie Garrana odpycha o 1 wolne pole. |

Żelazny bastion: na początku kolejnej tury podtrzymanie podstawy kosztuje
jedną dowolną runę. Wariant ulepszony wymaga ponownej odpowiedniej dopłaty;
bez niej aura wraca do podstawy. Opłacenie podtrzymania pozostawia zwykłą
i specjalną akcję tej nowej tury. Obecne +4 KP do Mana Drain nie przechodzi
automatycznie do nowego systemu.

Rozkazy nie tworzą nowych tur i nie pozwalają uruchomić kolejnego rozkazu.
Atak przyznany mocą nie daje kolejnej specjalnej. Ruch z Kontrataku stanowi
wyraźny wyjątek opisany na karcie, nie ponowne odnowienie zwykłego ruchu.

### Przykład walki — czterech bohaterów

Runda 1: wspólna oferta to Kotwica, Błysk, Węzeł, Kielich, Oko, Korona.
Drużyna daje Garranowi Kotwicę i Węzeł, pozostałe cztery runy dzieli między
trzy osoby. Nierówny podział jest dozwolony.

Garran przemieszcza się do wroga i zwyczajnie atakuje mieczem. Następnie
wydaje Kotwicę na Uderzenie tarczą. Wygrywa sporny test, wyrzuca 4 na k6:
zadaje 8 obrażeń (4 + SIŁ 4) i odpycha wroga o wolne pole. To zużywa
specjalną, a nie drugą zwykłą akcję. W ręce zostaje Węzeł.

Przed atakiem innego przeciwnika na sąsiadującego sojusznika Garran może
wydać Węzeł i reakcję, aby przejąć atak. Jeśli to zrobi, kończy tę część walki
z pustą ręką. Jeśli odmówi, zachowa runę do kolejnej rundy, ale sojusznik
przyjmie swój atak. Nie może potem wydać zużytego Węzła na następną reakcję.

Alternatywnie drużyna mogła dać mu Błysk zamiast Węzła: jego tarcza dostałaby
dodatkowe 1k6 obrażeń, kosztem braku tej konkretnej osłony. Zastępstwo bazowej
runy dwiema dowolnymi nadal byłoby możliwe tylko przy posiadaniu takich run.

Runda 2: nowy dobór sześciu run. Garran otrzymuje Gwiazdę i Wieżę. Może
uruchomić Bastion +2 KP, wydając obie runy oraz zwykłą i specjalną akcję;
pozostaje mu ruch. Nie wykonuje przed tym zwykłego ataku. W następnej rundzie
wybierze opłacenie podtrzymania albo wygaśnięcie aury.

Nie wszystkie moce zmieszczą się co turę w dopływie zasobów. Przy N+2 na
rundę czterech bohaterów dostaje średnio 1,5 runy na osobę; dopłaty, reakcje
i aury konkurują z następnymi aktywacjami. Limit 7 umożliwia oszczędzanie,
ale nie gwarantuje wzrostu ręki. Odkładanie wymaga czasem tury bez specjalnej.

## 6. Konfrontacja NPC/obiektu

### Przebieg jednej rundy

1. Ustalamy uczestników i tor. Progi nie zmieniają się, gdy ktoś później pasuje.
2. Jeden dobór N+2 run na całą scenę i wspólny podział; bez odświeżania i bez
   doboru po każdym uczestniku. Osobiste ręce z poprzedniej sceny nie przechodzą.
3. Kolejny bohater wybiera podejście z listy tej sceny. Od razu deklaruje
   ewentualne wsparcie runiczne, rzuca k20 i rozstrzyga przesunięcie toru.
   Nie ma wcześniejszej pełnej rundy przypisywania podejść ani rzutu wpływu.
4. Sukces +1, zwykła porażka 0, naturalne 20 +2, naturalne 1 −1. Wynik
   naturalny ma pierwszeństwo przed ST; premia runiczna nie usuwa krytyka.
5. Szczyt toru kończy scenę natychmiast. Próba zejścia poniżej −1 kończy ją
   wynikiem pogorszenia, bez kolejnego poziomu dodatkowej kary.
6. W przeciwnym razie koniec po działaniu ostatniego bohatera. Rezultat
   wynika z aktualnego poziomu, a nie najwyższego osiągniętego wcześniej.
   Nagrody i komplikacje rozliczamy raz, po zakończeniu; nie zbieramy nagród
   z każdego mijanego pola.

Propozycja: można spasować, zużywając swoją kolej bez rzutu. Gracz nie musi
ryzykować pogorszenia dobrego wyniku. Pozostają jawne cechy i ograniczenia
powtarzalności podejść; podejście wyłączne zużywa się po próbie, również
nieudanej. Musi istnieć co najmniej jedna sensowna opcja powtarzalna.

### Tor startowy do porównania przy stole

Użytkownik opisał cztery dodatnie stopnie. Zachowujemy je dla 4–6 bohaterów;
przy trzech łączymy oba stopnie bonusowe w jeden, aby skrócić tor.

| Bohaterowie | Sukces z komplikacją | Sukces | Sukces z bonusem | Pełny sukces z większym bonusem, automatyczny koniec |
| --- | --- | --- | --- | --- |
| 3 | 1 | 2 | — | 3 |
| 4 | 1 | 2 | 3 | 4 |
| 5 | 1–2 | 3 | 4 | 5 |
| 6 | 1–2 | 3–4 | 5 | 6 |

We wszystkich składach: −1 pogorszenie, 0 brak wynegocjowanej poprawy.
Szczyt przy N sukcesach jest ambitny; naturalne 20 pozwala nadrobić porażkę.
Większa drużyna ma także więcej okazji do naturalnej 1, więc tabela jest
prototypem, a nie obietnicą identycznych prawdopodobieństw dla każdego składu.

### Zasób do ułatwienia testu

Propozycja: każde podejście wskazuje jedną wspierającą runę, np. Koronę
przy osobistej gwarancji, Oko przy ocenie gruntu, Kotwicę przy podnoszeniu
wozu. **+2 do testu kosztuje tę runę albo dwie dowolne.** Maksymalnie jedno
takie wsparcie, deklarowane przed rzutem; koszt przepada również po porażce.
Bez dodatkowej kości i bez modyfikacji wielkości przesunięcia toru.

W tej procedurze nie uruchamiamy oddzielnie całej bojowej akcji Mowa dowódcy,
a potem kolejnej osobistej próby. Korona może być jej narracyjnym odpowiednikiem
w podejściu Garrana, ale bohater nadal ma jeden test. Bojowe aury nie dają
automatycznie premii do negocjacji. Zachowujemy prostotę jednej rundy.
To świadome uproszczenie pierwszego prototypu: +2 nie oddaje jeszcze całej
odrębności bohaterów poza walką. Osobiste warianty podejść można później
opisać na kartach jako modyfikację tej jednej próby, zamiast dokładać kolejne
akcje i rzuty; ich projekt pozostaje osobną decyzją.

Jeśli kosztowałoby to tylko jedną dowolną runę, N+2 niemal zapewniałoby
premię wszystkim. Koszt dwóch dowolnych pozostawia dylemat, komu pomóc;
pasujące symbole nagradzają dopasowanie podejść do doboru.

ST należy przeliczyć. Obecne 18–25 u Nessy zakłada rosnącą premię many
i różne kości wpływu. Startowe testy o ST 12–16 są propozycją do sprawdzenia
przy rzeczywistych cechach, nie gotowym bilansem. Trudniejsze podejście
z identycznym +1 musi mieć dodatkową korzyść albo niższy inny koszt.

### Nessa — przykład czterech postaci

Zachowujemy obecny cel: dodatkowa mikstura, zamiast zmieniać fabułę kontraktu.
Przykładowe nowe rezultaty, jeszcze nie wpisane do scenariusza:

- −1: brak mikstury i konkretny dodatkowy koszt, np. 2 sz przy rozliczeniu
  wyprawy. Ten negatywny skutek wymaga dopasowania tekstu Nessy i akceptacji.
- 0: obecny kontrakt bez dodatkowej mikstury.
- 1: słabsza mikstura 1k8+2, z jawnym obowiązkiem zdania dokładnego raportu.
- 2: pełna mikstura 2k8+4.
- 3: pełna mikstura i użyteczna informacja mieszcząca się w wiedzy Nessy.
- 4: jak wyżej oraz druga, słabsza mikstura; natychmiastowe zakończenie.

Lorian wybiera komplementy, sukces: 0→1. Nimra wybiera logiczne argumenty,
porażka: nadal 1. Garran składa osobistą gwarancję; jego wynik z cechą to 12
przy proponowanym ST 14. Zadeklarowana wcześniej Korona daje +2: sukces, 1→2.
Mira wybiera blef i wyrzuca naturalne 20: 2→4, najlepszy wynik i koniec.
Łącznie cztery k20 i żadnego rzutu wpływu.

Gdyby ostatnia próba dała naturalne 1, tor spadłby z 2 na 1 i końcowym
rezultatem byłaby słabsza mikstura z obowiązkiem. Mira mogła też wcześniej
spasować, zachowując pełną miksturę z poziomu 2. Informacje i mikstury
wydaje się dopiero po rozstrzygnięciu sceny.

### Wóz — przykład i ciągłość misji

Wydobycie awaryjne musi pozostawać możliwe także przy 0 lub −1, aby
nieudany test nie blokował całej misji. Proponowany koszt zastępczy:

- −1: wóz wydobyty awaryjnie, zmęczenie przez 1k4+1 rund nadchodzącej walki.
- 0: wóz wydobyty awaryjnie, obecne 1k4 rund zmęczenia.
- sukces z komplikacją: wóz wolny, zmęczenie przez 1 rundę.
- sukces: wóz wolny bez zmęczenia.
- bonus: dodatkowo ocalony przydatny element wyposażenia, np. lina.
- największy bonus: dodatkowa korzyść do dobrania w paczce scenariusza;
  przy trzech postaciach połączony poziom bonusowy daje ustalony najlepszy wynik.

Trzech bohaterów: Brakka podnosi wóz i odnosi sukces, 0→1. Garran
podpiera oś, naturalne 1: 1→0. Mira mocuje wiązanie, z dopłatą pasującej
runy odnosi sukces: 0→1. Koniec rundy: wóz wydobyty z jedną rundą zmęczenia.

Osobny przykład granicy: naturalne 1 przy starcie daje 0→−1. Następne
naturalne 1 próbowałoby dać −2, więc od razu kończy scenę pogorszeniem,
nawet jeśli pozostali nie zdążyli wykonać swoich prób.

## 7. Moralność i cena skrótów

Zachować wskaźnik postawy i obecne fabularne alternatywy. Propozycja na
pierwszy test: postawa nie usuwa run z talii. Dawne wyłączanie kolorów nie
ma oczywistego odpowiednika; usunięcie konkretnego symbolu mogłoby blokować
bohaterowi podstawową moc.

Konkretną cenę przypisujemy decyzji, a nie każdej nieudanej próbie:

- Wymuszenie zamiany wozu zachowuje obecny skrót bez testu i zmęczenia oraz
  krok ku Bezwzględności. Proponowana dalsza cena: utrata określonej późniejszej
  pomocy poszkodowanych, wymagająca faktycznego zapisania i użycia w scenariuszu.
- Osobiste poręczenie może ułatwić próbę, ale zapisuje zobowiązanie z warunkiem
  i ceną, np. 5 sz odpowiedzialności za niezwrócony sprzęt. Obowiązek powstaje
  po podjęciu decyzji, również jeśli sam test nie da korzyści. Wielkość
  ułatwienia oraz jego kumulacja ze wsparciem runicznym +2 pozostają do
  ustalenia; nie zakładać drugiej, nieopisanej premii w przykładzie Nessy.
- Pomoc mieszkańcom może kosztować realny przedmiot, pieniądze albo czas,
  zachowując zmianę postawy i dostęp do współpracy. Nie dokładamy automatycznie
  nowego toru moralnego ani premiowych punktów do konfrontacji.

To propozycje sposobu naliczania kosztów. Konkretnych kwot ani nowych
konsekwencji nie uznajemy za zatwierdzoną zmianę fabuły. Koszt i pewny skutek
są jawne przed zatwierdzeniem; obietnica przyszłej kary bez realnego skutku
w grze nie równoważy pewnej nagrody teraz.

## 8. Plansza, wyposażenie, interfejs i druk

Przy zachowanych 20 fizycznych znakach układ mieści się dokładnie w 30 polach:

```text
Ruch | Atak | Przedmiot | Koniec | puste | 20 run | puste | + | − | ✓ | ↩
```

Sloty od lewej, od zera: 0–3 podstawy, 4 puste, 5–24 runy, 25 puste,
26 plus, 27 minus, 28 zatwierdzenie, 29 powrót. Dzisiaj runy są na 6–25,
a minus/plus w odwrotnej kolejności. Zmiana dotyczy jednocześnie nadruku,
mapowania skanu, LED, kart bohaterów i podpowiedzi ekranowych.

Mapowanie sprzętowe to `Coordinate(19, 29-slot)`, więc slot 0 rzeczywiście
jest po lewej stronie osoby siedzącej przy runach. Przy wyborze tylko 10
fizycznych run konieczny jest osobny projekt zajęcia pozostałych pól i menu;
nie rozszerzamy jednego przycisku na kilka pól czujników bez takiej decyzji.

Zmiana broni znika z walki. Sloty wyposażenia ustala przygotowanie przed
misją, a znaleziony sprzęt czeka w zapasie do kolejnego przygotowania. Nadal
można używać zabranych przedmiotów zużywalnych. Trzeba ustalić przypadek
dwóch broni od początku trzymanych w rękach oraz przymusowego rozbrojenia:
propozycja to wybór spośród już wyposażonych źródeł ataku bez osobnej akcji
zmiany oraz możliwość odzyskania upuszczonego sprzętu jako interakcja.
Nie daje to swobodnego zakładania nowej broni z zapasu w terenie.

Każdy ekran otrzymuje komplet przypisań, również launcher, wczytywanie,
wybór bohaterów, wyposażenie, podział run, reakcje, podglądy i menu. Przewijanie
+/− dotyczy aktywnej listy/panelu. W trybie wpisywania wyniku te same klawisze
zmieniają liczbę, a nie przewijają strony. ✓ zatwierdza, ↩ cofa lub odrzuca.
Brak nowych gestów, podwójnych kliknięć i konieczności używania myszy do
zwykłej rozgrywki. Zachowujemy obecne karty i układ UI; dodajemy rękę,
koszt, dostępne dopłaty i nowy tor zamiast starej many/oporu.

Aktualna korekta druku wynosi 250/244. Dodatkowe +3% względem obecnego PDF
oznacza `(250/244) × 1,03 = 1,055327869`, a bok nominalnego pola 25 mm
w skorygowanym PDF wyniesie ok. 26,3832 mm. To wymiar projektu kompensującego
drukarkę, nie nowy deklarowany rozstaw czujników.

Powiększamy spójnie mapę bazową i geometrię kafli Misji 0, łącznie z nadrukami
i miejscami interakcji, a nie tylko ilustracje. Manifest obejmuje 18 kafli
P01–P15 i G01–G03. Sprawdzić nowy podział A4: obecne znaczniki cięcia po
powiększeniu mogą dojść zbyt blisko marginesu. Wydruk 100%, bez ponownego
skalowania w sterowniku. Przed pełnym kompletem próba kontrolna kilku pól
przy rzeczywistych czujnikach. Karty sprzętu i bohaterów zachowują własne
wymiary; użytkownik zlecił +3% map i kafli, nie wszystkich materiałów.

Źródła późniejszej zmiany: `ui/board_panel_symbols.py`, `hardware/board_panel.py`,
`scripts/build_arena_print_pack.py`, `scripts/build_mission_zero_prints.py`,
`scripts/build_mission_zero_cutouts.py`, `scripts/build_session_print_packs.py`,
`physical_cards/scenario_cutouts.py` i źródła paczki Misji 0. Wariant nominalny
25 mm ma pozostać wyraźnie oddzielony od skorygowanego profilu drukarki.

## 9. Najważniejsze ryzyka i zakres następnego kroku

- **Mocniejsza tura:** broń i specjalna mogą prawie podwoić ofensywę. Obecnego
  bilansu obrażeń, PW wrogów i ST nie wolno uznać za gotowy po zmianie nazw.
- **Dominujący gracz:** podział może zamienić się w dyktowanie ruchów. Zgodnie
  z życzeniem użytkownika najpierw sprawdzamy dobrowolne uzgodnienie, bez
  dodawania narzuconej kolejki wyboru.
- **Martwe runy:** osobista ręka ograniczona do 7 może zapchać się symbolami
  służącymi tylko dopłatom. Testujemy koszt zastępstwa 2:1 i wymianę przy limicie.
- **Rzadkie klucze:** 20 typów i mały dobór utrudniają konkretne plany. Decyzja
  10/20 wymaga przejrzenia wszystkich bohaterów, szczególnie Nimry.
- **Aury i leczenie:** nie mogą rosnąć bez końca przez tasowanie albo bezpieczne
  czekanie. Dobór tylko podczas rzeczywistego spotkania; jawne limity, koszty
  utrzymania, brak sumowania identycznych premii, koniec po rozstrzygnięciu.
- **Opłacalność podejść:** wyższe ST przy tym samym +1 musi mieć uzasadnienie.
- **Udział wszystkich:** wcześniejszy sukces lub pogorszenie świadomie może
  zakończyć scenę przed ostatnimi graczami. Zmieniać prowadzącego między scenami.
- **Nagrody i tor:** nie rozdawać nagród za mijane stopnie. Próg 0 wóz/NPC
  musi pozwalać kontynuować misję.
- **Koszt obsługi:** jedna faza podziału na rundę; aplikacja odejmuje runy
  automatycznie. Nie wraca ręczne zgłaszanie spalania po każdym działaniu.
- **Zapis i stare materiały:** przyszłe wdrożenie wymaga jawnej granicy między
  dawnym profilem many a nowym, bez zmiany trwającego rzutu pod graczem.
- **Sterowanie walką:** zgłoszona blokada planszy pozostaje osobnym zadaniem;
  projekt run sam jej nie naprawia.

Przed implementacją do uzgodnienia pozostają przede wszystkim: 10/20 typów
i fizycznych znaków, zasada jednej dopłaty, zastępstwo 2:1, stała premia
ataków/testów, powyższe progi toru, reset rąk między scenami, utrzymanie aur
oraz dokładne konsekwencje moralne. Po tym: krótki test papierowy Garrana
z Nessą/wozem i walką, następnie zmiany katalogów, zasad, transportu i wydruków.

Sprawdzono istniejące opisy i mapowanie; policzono prawdopodobieństwa doboru
i mnożnik druku. Nie uruchamiano pytest ani sprzętu — to dokument projektowy.

# Fizyczna mana — projekt do testów 0.2

Od 2026-09-07 fioletową manę zastępuje czarna. Symbole: biała — słońce,
niebieska — kropla, czarna — czaszka, czerwona — płomień, zielona — drzewo;
cyfra 1 w kółku oznacza dowolny kolor. Do testów używamy podstawowych lądów
MTG: Plains, Island, Swamp, Mountain i Forest. Każdy ląd jest jedną kartą
many; wydany trafia na stos odrzuconych. Koszty, dobór i fale pozostają
według zasad fizycznej many. Wydarzenie 5 nazywa się „Czarne zakłócenie”.
Mapowanie lądów i kolorów: [Wizards of the Coast](https://magic.wizards.com/en/news/feature/anatomy-magic-card-2006-10-21).

Status: profil fizycznej many wdrażany do nowych rozgrywek siedmiu bohaterów na polecenie użytkownika z 2026-09-05. Instrukcja i talie tego profilu są dostępne w aplikacji pod `/rules/physical-mana`. Aktualne PDF-y wszystkich czterech formatów znajdują się w `assets/physical_cards/character_sets/physical_mana_v02/`; dotychczasowe ścieżki PDF `keyboard_v1` i `bw_test` wskazują kopie tych aktualnych materiałów. Koszty i liczby pozostają punktem wyjścia do testów balansu; poprawność implementacji nie oznacza potwierdzonego balansu.

Zmiany względem 0.1: dobór na końcu tury, wielokrotny zwykły Atak opłacany za każde uderzenie, Lorian jako zarządzający maną z pojemnością większą o jedną kartę.

Zakres: siedem grywalnych bohaterów na poziomie 3. Źródło obecnych zdolności: `BOARDGAME_ARCHETYPES_LEVELS_1_3.md`. Fizyczna talia, rynek, rezerwy, opłacanie i wymiany pozostają wyłącznie przy stole. Aplikacja obsługuje deklaracje i skutki działań.

## 1. Tura i koszty podstawowe

W swojej turze bohater ma jedną akcję główną, jeden limit ruchu i najwyżej jedną akcję dodatkową. Ma również jedną reakcję odnawianą na początku swojej tury. Runda obejmuje tury wszystkich uczestników. Mana nie kupuje dodatkowych akcji.

| Działanie | Koszt many | Koszt czasu |
| --- | --- | --- |
| Zwykła akcja Ataku — jedno uderzenie | 1 dowolna | Jedna akcja główna |
| Tylko Lorian: zadeklarowana seria zwykłych ataków | 1 dowolna za każdy atak | Jedna akcja główna na całą serię |
| Zwykły ruch do limitu szybkości | 1 dowolna | Ruch; płatność raz na turę, można dzielić przed/po akcji |
| Użycie zwykłego przedmiotu, pomoc, stabilizacja, ucieczka z chwytu, przeszukanie | 1 dowolna | Akcja główna; przedmiot nadal musi istnieć |
| Atak okazyjny | 1 dowolna | Reakcja |
| Prosta zmiana broni/interakcja z obiektem | 1 dowolna | Istniejący limit interakcji; kolejna może wymagać akcji |
| Zakończenie tury, pas, podgląd, anulowanie, dobór i porządkowanie kart | 0 | Bez dodatkowej akcji |
| Mimowolne przesunięcie, ratunkowy ruch z pasywu | 0 | Wynika z efektu, bez uruchamiania zwykłego ruchu |

Zwykła akcja Ataku daje jedno uderzenie za 1 dowolną manę. Wyjątek stanowi Lorian: jego gracz wpisuje dodatnią liczbę zwykłych ataków. Przy zatwierdzeniu opłaca fizycznie tyle kart dowolnych; nie ma dodatkowego kosztu uruchomienia akcji. Każdy atak ma osobno wybierany legalny cel, rzut trafienia, obrażenia i okno reakcji. Kolejny cel można wybrać po rozstrzygnięciu poprzedniego ataku. Można atakować ten sam cel wielokrotnie albo różne cele i korzystać z różnych aktualnie dostępnych broni zgodnie z zasadami wyposażenia. Opłacony ruch można dzielić pomiędzy atakami. Seria nie pozwala rzucać kilku czarów ani wykonywać kilku odrębnych technik specjalnych.

Liczba zadeklarowanych ataków nie rośnie podczas serii, nawet po odzyskaniu many. Niewykorzystane ataki przepadają przy świadomym przerwaniu albo utracie możliwości ich wykonania; zapłacona mana nie wraca. Anulowanie całego podglądu przed rozpoczęciem serii nie kosztuje many. Dodatkowe koszty skaz płaci się przy pierwszym ataku, który spełnia ich warunek; nie liczy się ich od każdego uderzenia. Atak okazyjny pozostaje pojedynczym atakiem za jedną reakcję.

Aplikacja przyjmuje liczbę i prowadzi kolejkę rozstrzygnięć, ale nie porównuje jej z ręką gracza, pojemnością ani starym klasowym limitem liczby ataków. Legalność opłacenia tej liczby jest sprawą stołu. Wszystkie zdolności dające kilka ataków również rozstrzygają je osobno — bez wspólnego testu trafienia lub obrażeń. Koszty specjalnych serii zawierają wymienioną liczbę ataków; nie dokupuje się do nich następnych ataków za *. Zakup większej serii dotyczy tylko zwykłej akcji Ataku Loriana. Pozostałe postacie nie deklarują liczby ataków; aplikacja od razu prowadzi do wyboru celu pojedynczego ataku.

Koszt zdolności specjalnej jest całkowity: nie dodajemy do niego opłaty za zwykły atak. Ruch zawarty w zdolności jest w jej cenie. Osobny zwykły ruch kosztuje dodatkowo 1 dowolną. Płatność za ruch nie omija stanów, trudnego terenu, zasięgu ani ataków okazyjnych. Wstanie nadal zużywa połowę dostępnego ruchu i wymaga uruchomienia ruchu, jeśli nie zrobił tego inny efekt.

Podstawowe działania kontekstowe nie przyznają wszystkim klasowych technik, np. Ukrycia Miry czy Sprintu Erynda. Nie dodajemy uniwersalnego darmowego uniku. Pasywne rzuty obronne i ratowanie przed śmiercią nie kosztują many.

## 2. Karty, rynek i rezerwa

Kody poniżej to wewnętrzne oznaczenia aplikacji, zachowane dla zgodności zapisów; nie są skrótami MTG. Na kartach i w interfejsie używamy nazw kolorów i symboli. Oznaczenia kosztów: C = czerwony/płomień, N = niebieski/kropla, Z = zielony/drzewo, B = biały/słońce, F = czarny/czaszka, * = dowolna karta (ikona 1 w kółku). Każdy znak oznacza osobną fizyczną kartę; N+* to dwie karty, N lub dowolna byłoby innym kosztem. Karty mają symbole i nazwy obok koloru.

| Kolor | Funkcja |
| --- | --- |
| C | Siła, obrażenia, przełamanie |
| N | Kontrola, obrona magiczna, porządkowanie |
| Z | Mobilność, precyzja, natura |
| B | Ochrona, leczenie, współpraca |
| F | Podstęp, osłabienia, zmiana właściwości |

Start walki: tasujemy talię i wykładamy rynek. Następnie rozgrywamy trzy krótkie kolejki doboru w kolejności inicjatywy: każdy bierze jedną kartę, po każdym wyborze rynek jest uzupełniany. Każdy, również Lorian, zaczyna z trzema kartami. To jednorazowy dobór startowy.

W zwykłej turze NIE ma doboru na początku. Bohater działa kartami przygotowanymi na poprzednim końcu tury, pomniejszonymi o reakcje i skutki między turami. Po działaniach wykonuje kolejno:

1. Rozliczenie skazy i innych efektów końca tury.
2. Zachowanie do dwóch niewydanych kart, Lorian do trzech. Nadmiar odrzuca. To limit starej rezerwy PRZED dołożeniem nowych kart.
3. Wybór z rynku do trzech nowych kart, także przez Loriana. Nie uzupełnia się rynku pomiędzy tymi wyborami. Wolno dobrać mniej.
4. Uzupełnienie rynku do pełna. Koniec tury — nowo dobranymi kartami nie wykonuje się już własnych działań, można nimi później płacić za reakcje.

| Bohater | Zachowuje stare karty przed doborem | Dobiera na końcu | Może mieć po doborze / całkowita pojemność |
| --- | --- | --- | --- |
| Garran, Brakka, Mira, Dagna, Nimra, Erynd | Do 2 | Do 3 | Do 5 |
| Lorian | Do 3 | Do 3 | Do 6 |

Przykład: z pięciu kart gracz wydał trzy, zachowuje dwie i dobiera trzy — ma pięć na reakcje i następną turę. Wydał wszystkie pięć: dobiera trzy i ma trzy. Nie ma dodatkowego uzupełniania na początku następnej rundy ani tury. Lorian z trzema niewydanymi kartami zachowuje wszystkie trzy i dobiera trzy, osiągając sześć.

Pojemność pięciu/sześciu obowiązuje zawsze, także przy prezentach i odzyskiwaniu many; nadmiar natychmiast odrzuca właściciel. Wyjątkiem jest wyraźnie opisane wydarzenie Zielonego przypływu. Nieprzytomny lub obezwładniony bohater zachowuje posiadane karty, ale nie dobiera; po odzyskaniu możliwości działania dobiera na końcu najbliższej swojej tury. Posiadanie kart nie znosi stanów. Pasywna stabilizacja i rzuty ratowania przed śmiercią pozostają bezpłatne.

Rynek jest jednym rzędem: po zabraniu kart pozostałe przesuwają się w lewo, nowe dokładamy z prawej. Koniec każdej rundy: odrzucamy jedną skrajną lewą kartę i uzupełniamy rynek. To minimalny upływ czasu także przy oszczędzaniu zasobów.

Parametry startowe do testów, ustalane według liczby bohaterów rozpoczynających walkę; pokonanie bohatera nie zmienia talii:

| Bohaterowie | Karty w talii | Każdego koloru | Rynek |
| --- | --- | --- | --- |
| 1 | 20 | 4 | 5 |
| 2 | 30 | 6 | 6 |
| 3 | 40 | 8 | 7 |
| 4 | 50 | 10 | 8 |
| 5 | 60 | 12 | 9 |

Przy trzech bohaterach wykładanie rynku i startowych rąk zużywa 16 z 40 kart. Pełne dobory końca tur i odpływ zużywają następnie około dziesięciu kart na rundę. Pierwsza fala wypada orientacyjnie w trzeciej rundzie, wcześniej przy przeciążeniach i zdolnościach dobierania. To rachunek przepływu, nie wynik rozegranych walk. Dobór na końcu tury oznacza planowanie przed następną turą oraz wybór między reakcją teraz a zachowaniem kombinacji.

## 3. Wymiana, przeciążenie i płatność

- Dwie dowolne karty mogą zastąpić jeden wymagany kolor. Wszystkie opłaty za jedno działanie trzeba pokryć naraz; nie można zagrać czaru częściowo.
- Raz we własnej turze można przeciążyć jedną posiadaną kartę: liczy się jako dowolny kolor, a dwie wierzchnie karty talii trafiają zakryte na stos odrzucony. Nadal wydaje się kartę zastępującą kolor. Nie daje to akcji, dodatkowej karty ani możliwości przekroczenia pojemności.
- Zdolności wymiany zamieniają istniejące karty 1:1, nie dobierają nowych i nie uzupełniają rynku. Przekazanie karty między graczami jest możliwe tylko przez wyraźną zdolność; zwykły handel rezerwami jest niedozwolony.
- Karty wydaje się przy ostatecznym wykonaniu, przed rzutem. Pudło lub udana obrona celu nie zwracają kart. Anulowany podgląd nic nie kosztuje. Gracze sami rozliczają błędną deklarację cofniętą przed rozstrzygnięciem.
- Skaza z przymusowym odrzuceniem: bez karty nic nie odrzucasz i nie zaciągasz długu. Skaza z dopłatą: koszt trzeba opłacić, żeby zgodnie z zasadami wykonać działanie; aplikacja tego nie blokuje ani nie sprawdza.
- Limity dotyczące fizycznej many gracze oznaczają obróceniem karty pasywu/skazy. Limity „raz we własnej turze” zerują się na początku kolejnej własnej tury. „Raz między własnymi turami” obejmuje też reakcje i używa tego samego znacznika.

## 4. Co zastępujemy

W wariancie fizycznej many usuwamy bojowe koszty Taktyki, Forteli, Instynktu, Dzikości, Inspiracji, Metamagii, komórek czarów i Boskiej Mocy dla siedmiu talii. Nie wymagamy dodatkowo starych użyć Drugiego oddechu/Zrywu/Szału. Szał pozostaje stanem. Inspiracja Loriana zostaje zdolnością zmiany koloru, bez dawnej kości k6. Nieustępliwość Brakki pozostaje wyjątkiem raz na długi odpoczynek.

Zostają statystyki, bronie, rzuty, osłony, linia widzenia, koncentracja, ograniczenia stanów i cele. Zachowujemy rasowe cechy niewymagające zasobów, cechy fabularne i umiejętności. Wyjątki i zastępowane pasywy są nazwane poniżej. Nie nakładamy starych kar skazy na nową wersję.

Jeżeli tabela podaje „jak obecnie”, pełny efekt, cele i zasięg bierze się z aktualnej talii, ale koszty punktów/komórek zastępuje wymieniona mana. Czary działają na bazowym poziomie; nie wybieramy komórki ani podwyższenia poziomu. A = akcja główna, D = dodatkowa, R = reakcja, MOD = modyfikator jednej akcji, bez osobnego czasu. Każda pozycja kosztu ma swój czas niezależnie od posiadanej many.

## 5. Garran — obrona i oszczędna współpraca

| Zdolność | Czas | Mana | Proponowany efekt |
| --- | --- | --- | --- |
| Drugi oddech | A | B+* | Odzyskaj 1k10+3 PW. Zmiana z akcji dodatkowej na główną: leczenie konkuruje z ofensywą. |
| Zryw akcji | D | C | Następny zwykły atak w tej turze otrzymuje +2 do trafienia. Atak nadal kosztuje *. Nie odnawia akcji, nie dodaje ataków ani premii do technik specjalnych. |
| Uderzenie tarczą | D | C+N | Sporny test Siły; za przeciwnika rzuca aplikacja. Wygrana: 1k6 + modyfikator Siły obrażeń obuchowych i odepchnięcie o jedno wolne pole (5 ft). Remis wygrywa obrońca. Nie zużywa ruchu ani akcji głównej. |
| Pozycja obronna | D | B | +2 KP do początku następnej tury; każda zmiana pola kończy efekt. Zastępuje dawny koszt całego ruchu. |
| Rozkaz: Stać | A | N+* | Obecny rozkaz, w tym naturalne 1/20. |
| Osłona tarczą | D | B+N | Sąsiadujący sojusznicy mają +2 KP do początku następnej tury Garrana; bez premii dla niego. |
| Mowa dowódcy | A | B+* | Usuń Strach u słyszących sojuszników w 30 stopach i siebie; przewaga na ich pierwszy atak/test/obronę jak obecnie. |
| Osłona towarzysza | A | B+N | Przekieruj pierwszy pojedynczy wrogi efekt z sąsiadującego sojusznika na Garrana jak obecnie. |

Pasywy: Obrona daje +1 KP w pancerzu; Ulepszony krytyk daje krytyki bronią przy naturalnym 19–20; Żelazna linia daje sojusznikowi flankującemu z Garranem +1 KP przeciw wspólnemu przeciwnikowi. Nowy „Za tarczą”: raz we własnej turze, gdy przytomny bohater jest w 5 stopach, Garran może potraktować jedną N jako B w swojej zdolności ochronnej: Pozycji, Osłonie tarczą lub Osłonie towarzysza. Nie działa na samoleczenie.

Nieustępliwość: jeśli Garran rozpoczyna zwykły Ruch obok niepokonanego przeciwnika (w 5 ft, także po skosie), płaci 2 dowolne many zamiast 1. Cena jest ustalana przy pierwszym rozpoczęciu Ruchu w turze; podział na odcinki i późniejsze sąsiedztwo nie zmieniają ceny. Odepchnięcia i przemieszczenia ze zdolności nie uruchamiają skazy. Działa również solo. Ruch opłacony N + * pomija Ciężkie powietrze. Aplikacja pokazuje koszt przy ruchu i pamięta jego rozpoczęcie, ale nie weryfikuje fizycznej zapłaty. Anulowany podgląd nie uruchamia ruchu. Zastępuje Wyrzuty sumienia w profilu many; ataki i zdolności nie mają dopłaty.

## 6. Brakka — wykorzystanie czerwonej many i presja ataku

| Zdolność | Czas | Mana | Proponowany efekt |
| --- | --- | --- | --- |
| Szał | D | C | Przez KON mod + SIŁ mod rund (minimum 1), licząc rundę uruchomienia: +2 obrażeń wręcz z SIŁ, odporności fizyczne i przewaga SIŁ. Płacisz raz; utrata przytomności kończy Szał. Aplikacja odlicza rundy. |
| Lekkomyślny atak | MOD | C | Następny zwykły atak wręcz oparty na SIŁ w tej turze ma przewagę. Atak jest opłacany dodatkowo przez *. Ataki przeciw Brakce mają przewagę do początku jej następnej tury. Raz we własnej turze; nie jest osobną akcją ani kolejnym atakiem. |
| Potężne uderzenie | A | C+C | W Szale: jeden atak z +2 do trafienia i +1k12 obrażeń przy trafieniu. Zastępuje dawne +10 do trafienia. |
| Z bara | A | C+N | Obecne odpychanie Atletyką. |
| Przyspieszenie | D | Z | W Szale: uruchamia zwykły ruch bez dodatkowej opłaty i podwaja jego bazowy limit w tej turze. Wykonany wcześniej ruch liczy się do nowego limitu. |
| Ogłuszający ryk | A | C+N+* | W Szale: obecny stożek, 2k6, ograniczenie ruchu i naturalne wyniki. |
| Twarda jak skała | R | B | W Szale: redukcja 1k12+KON po odporności jak obecnie. |
| Chwyt | A | * | Obecny chwyt, wolna ręka i limit wielkości celu. |

Pasywy: Widzenie w ciemności 60 stóp; Obrona bez pancerza daje KP 10 + modyfikator ZRC + modyfikator KON i pozwala na tarczę; Dzikie ataki dodają jedną kość broni do krytyka wręcz. Nieustępliwość półorka zostaje raz na długi odpoczynek, jako wyjątek ratunkowy — mana nie pozwala jej ponawiać. Nowy „Bitewny rozpęd”: raz we własnej turze, po trafieniu zwykłym atakiem opłaconym C, odzyskaj tę C z odrzuconych. Dotyczy podstawowego ataku, także objętego Lekkomyślnym, ale nie Potężnego ani innej techniki. Zwrot następuje dopiero po rozstrzygnięciu tego ataku, nie daje kolejnego ataku i podlega limitowi pięciu kart. Dopłata C za Lekkomyślny nie jest kartą opłacającą podstawowe uderzenie.

Nowy Bitewny amok: jeśli Brakka jest w Szale, lecz w swojej turze nie zadeklarowała żadnego ataku ani szkodliwej techniki przeciw wrogowi, przed porządkowaniem rezerwy odrzuca jedną posiadaną kartę. Pudło nie uruchamia kary. Ta wersja zastępuje zakaz używania przedmiotów.

## 7. Mira — poprawianie doboru dzięki pozycji

| Zdolność | Czas | Mana | Proponowany efekt |
| --- | --- | --- | --- |
| Ukryj się | A | * | Obecny test ukrycia i osobni obserwatorzy. Dobrowolne zakończenie ukrycia bez many/akcji. |
| Zasłona dymna | A | Z+F | Ruch do 15 stóp bez ataków okazyjnych i próba ukrycia nawet przy wrogu; cały ruch w cenie. |
| Przeskok przez gardę | A | Z+* | Obecny atak +2/+2 i przejście na wolne pole za celem; to przesunięcie w cenie. |
| Wykrycie pułapek | A | * | Obecny test Percepcji w walce. |
| Cięcie ścięgna | A | Z+N | Atak z własnej flanki; trafienie połowi ruch do początku następnej tury Miry, zamiast do leczenia. |
| Przeszywający atak | A | Z+C | Atak rapierem w przeciwnika stojącego przy sojuszniku. Po raniącym trafieniu osobny atak z +2 do trafienia w drugiego wroga dokładnie jedno pole za pierwszym, na tej samej linii od Miry. Drugie trafienie dosięga tego pola mimo zwykłego zasięgu rapiera; ściana je blokuje. Bez łańcucha dalszych celów. Oba ataki w cenie. |
| Mistrzyni ostrzy | A | Z+F | Trafienie nożem z ukrycia powoduje krwawienie 1k4 przez najwyżej dwie tury celu; leczenie kończy wcześniej. Bez kumulowania. |
| Unik instynktowny | R | Z | Obecna reakcja z utrudnieniem ataku przeciw ukrytej Mirze. |

Pasywy: Mistrzyni ukrycia zachowuje test przeciw osobnym obserwatorom, limit ruchu 20 stóp podczas ukrycia i 25 po jego dobrowolnym zakończeniu, bez zwrotu wykonanego ruchu. Szczęście pozwala przerzucić naturalną 1 w ataku, teście i obronie. Ruchomy cel daje +2 KP przeciw dystansowym atakom bronią/czarem, nie obszarom. Ekspertyza podwaja biegłość w wybranych umiejętnościach. Atak z cienia ma +1k6 za ukrycie przed celem lub własną flankę, +2k6 za oba; raz na własną turę. Zmniejszamy dotychczasowe +2k6/+3k6, aby pojedynczy bonus nie mnożył się przez serię zwykłych ataków. Właściciel wybiera jedno kwalifikujące się trafienie przed rzutem jego obrażeń. Atak kończy ukrycie; kolejne uderzenia nie dziedziczą ukrycia z początku serii.

Nowe „Zwinne dłonie”: raz we własnej turze po zakończeniu dowolnego odcinka legalnego ruchu o co najmniej 5 stóp zamień jedną posiadaną kartę z jedną kartą rynku. Zamiana 1:1, bez dobierania. Nie uruchamia się od przymusowego przesunięcia.

Nowa Panika po zdemaskowaniu: raz między początkami własnych tur odrzuć jedną kartę, gdy test przeciwnika wykryje Mirę podczas aktywnej sesji ukrycia. Własny atak i dobrowolne wyjście nie uruchamiają kary. Zastępuje premię +2 dla obserwatorów; zasady widoczności pozostają.

## 8. Dagna — leczenie jako decyzja główna

| Zdolność | Czas | Mana | Proponowany efekt |
| --- | --- | --- | --- |
| Święty płomień | A | B | Obecny stożek 15 stóp, 1k8 blasku przy porażce ZRC. |
| Słowo leczenia | A | B+* | 1k4+7 PW w 60 stopach. Zmiana z akcji dodatkowej na główną. |
| Błogosławieństwo | A | B+N | Obecna aura +1k4, koncentracja; maksymalnie trzy rundy zamiast pięciu. |
| Zachowanie życia | A | B+B+* | Rozdziel 15 PW, najwyżej do połowy maksymalnych PW celu, jak obecnie. |
| Aura Boskiej Opieki | A | B+N | Obecna aura -2 do ataków/obrażeń wrogów; koncentracja, maksymalnie trzy rundy. |
| Naprowadzający pocisk | A | B+C | Obecne 2k6 i przewaga kolejnego ataku przeciw trafionemu celowi. |
| Aura Uzdrawiającej Łaski | A | B+Z+* | Przez trzy rundy, z koncentracją: dwa pierwsze leczenia w aurze dodają po 1k8 PW. Zastępuje cztery wzmocnienia +1k8+MDR. |
| Pomniejsze przywrócenie | A | B+Z | Usuń jedną obecnie obsługiwaną negatywną kondycję przez dotyk. |
| Odpędzanie nieumarłych | A | B+N | Obecny obszar i rzut MDR; odpędzenie najwyżej do końca następnej tury Dagny, obrażenia kończą wcześniej. |
| Duchowa broń | A | B+C+* | Przywołanie i jeden atak w cenie. Trwa trzy rundy, najwyżej jedna broń; dalsze aktywacje to D za B, każda zawiera ruch broni do 20 stóp i jeden atak. Brak osobnej darmowej tury przywołania. |

Pasywy: Widzenie w ciemności 60 stóp; Krasnoludzki ruch ignoruje karę szybkości z niewystarczającej Siły do pancerza; Krasnoludzka wytrzymałość daje +1 maksymalnego PW na poziom, już wliczone; Krasnoludzka odporność daje przewagę przeciw truciźnie i odporność na obrażenia od niej. Krok ratowniczki — po pomocy innemu sojusznikowi ruch 5 stóp bez many, raz we własnej turze. Nowy Uczeń Życia: raz we własnej turze można zastąpić jedną B przez Z w zdolności, która faktycznie przywraca PW innemu bohaterowi. Nie dotyczy przygotowania aury ani własnego leczenia. Stara premia zależna od poziomu komórki znika; +7 Słowa leczenia to już pełna premia, bez dodatkowego doliczania.

Nowe Nikogo nie zostawiam: jeśli żywy bohater z 0 PW jest w 30 stopach, pierwsze ofensywne działanie Dagny we własnej turze kosztuje dodatkowo *. Leczenie, ratowanie, osłony i ruch nie dostają dopłaty. Zastępuje dotychczasowe utrudnienia/przewagę obron wrogów.

## 9. Lorian — zarządzający wspólną maną

Pełny zestaw: czternaście zdolności. Zamiast dublować kontrolne zaklęcia Nimry, siedem pozycji dawnej talii zastępujemy gospodarką many. Mana pozostaje fizyczna także przy jego zdolnościach; aplikacja może zużyć A/D/R i pokazać instrukcję, ale nie rozlicza kart. W zdolnościach wsparcia bohaterowie muszą być przytomni, zgadzający się i w 30 stopach, chyba że podano inny zasięg. Własne efekty Loriana nie wymagają osobnego odbiorcy.

| Zdolność | Czas | Mana | Pełny efekt roboczy |
| --- | --- | --- | --- |
| Inspiracja barw | D | B | Jeden inny bohater w 30 stopach może przy opłaceniu jednego działania do początku następnej tury Loriana potraktować jedną posiadaną kartę jako dowolny kolor. Jedna niewykorzystana Inspiracja na odbiorcę; bez k6 i bez tworzenia karty. |
| Strojenie rynku | D | N | Wymień do dwóch własnych kart z taką samą liczbą wybranych kart rynku. Jeden jednoczesny zestaw wymian 1:1, bez dobierania. |
| Transmutacja | D | F | Do końca tej tury dwie wskazane posiadane karty możesz opłacić jako dowolne kolory. Każda nadal jest wydawana i nie może opłacić dwóch symboli. Nie działa na kartę zużytą do uruchomienia Transmutacji. |
| Przerzut energii | D | Z | Przekaż do dwóch własnych kart jednemu innemu bohaterowi w 30 stopach. Nie dobiera on nowych. Obowiązuje pojemność odbiorcy. |
| Rezerwacja | D | N | Zabierz jedną kartę rynku do swojego depozytu, wliczanego do rezerwy i pojemności. Nie można jej wydać, oddać ani wymienić przed początkiem następnej własnej tury; wolno ją odrzucić. Maksymalnie jeden depozyt, na następnej turze staje się zwykłą kartą. Rynek uzupełnia się na końcu obecnej tury. |
| Odzysk energii | A | B+N | Wybierz do trzech kart obecnych na odrzuconych przed opłaceniem zdolności i rozdaj je sobie lub bohaterom w 30 stopach, najwyżej dwie jednemu odbiorcy. Nie wolno odzyskać właśnie zapłaconych B/N; nie zwiększa pojemności. Brak odpowiednich kart oznacza mniejszy odzysk. |
| Nowe rozdanie | A | N+* | Odrzuć do trzech kart rynku, uzupełnij go z talii. Następnie każdy przytomny bohater w 30 stopach, w tym Lorian, może raz wymienić własną kartę z rynkiem, w kolejności inicjatywy. Nie ma kolejnego doboru pomiędzy wymianami. |
| Awaryjna pożyczka | R | B | Gdy inny bohater w 30 stopach deklaruje działanie, przed jego opłaceniem przekaż mu jedną dodatkową własną kartę. B za reakcję jest osobnym kosztem; łącznie Lorian traci dwie karty. Bez zwrotu/długu mimo nazwy. Nie otwiera dodatkowej akcji ani nie zwiększa już zadeklarowanej serii ataków. |
| Luneta optyczna | A | Z+N+* | Przed ruchem wykonaj dwa osobne strzały w jeden cel, każdy z +2 do trafienia i ignorowaniem częściowej osłony; całkowita osłona blokuje. Zużywa cały ruch. Dwa strzały są już opłacone. |
| Ostrzał destabilizujący | A | Z+F | Jeden strzał w 45 stopach. Trafienie: utrudnienie pierwszego ataku i obron MDR celu do początku następnej tury Loriana. |
| Oplatający ostrzał | A | Z+N | Obszar 3×3 w 45 stopach, także sojusznicy. ZRC ST 14: porażka blokuje ruch, sukces połowi do początku następnej tury Loriana. Bez obrażeń. |
| Podszept paniki | A | F+N | Cel w 45 stopach, MDR ST 14: 2k6 psychicznych i ruch do 15 stóp od Loriana; sukces połowa bez ruchu. |
| Fala gromu | A | C+N | Sześcian 15 stóp, także sojusznicy. KON ST 14: 2k8 grzmotu i odepchnięcie o 10 stóp; sukces połowa bez odepchnięcia. |
| Rozpraszający okrzyk | R | B | Gdy bohater w 30 stopach otrzymuje obrażenia od pojedynczego ataku, zmniejsz je o 1k6+2, minimum 0. |

Pasywy:

- **Rezerwuar:** pojemność sześciu kart i zachowanie trzech starych przed końcowym doborem. Dobór nadal trzy, start nadal trzy.
- **Zgranie:** raz we własnej turze, przed końcowym doborem, zamień jedną swoją kartę z jedną kartą innego bohatera w 30 stopach. Zamiana 1:1. W grze solo zamiana z rynkiem.
- **Obycie i targowanie:** +2 do pozabojowych testów Charyzmy.
- **Improwizacja:** raz na NPC przerzut nieudanego pozabojowego testu Charyzmy przed konsekwencjami, drugi wynik ostateczny.
- **Widzenie w ciemności:** 60 stóp w niemagicznej ciemności, bez widzenia przez mgłę.
- **Dziedzictwo elfów:** przewaga przeciw zauroczeniu i odporność na magiczny sen.

Stary Kusznik dający dwa darmowe strzały znika. Każdy zwykły strzał Loriana kosztuje * tak samo jak u innych. Inspiracja barw zastępuje Inspirację bardowską. Prowokujący ostrzał, Baśniowy ogień, Ohydny śmiech, Rozkaz sceniczny, Przyspieszony refren, Kontrapunkt i Cięte słowa ustępują siedmiu nowym zdolnościom zarządzania maną. To świadoma wymiana pozycji talii, nie dodatkowe ukryte czary.

**Skaza — Potrzeba publiczności:** bez innego przytomnego bohatera w 10 stopach pierwsza zdolność specjalna użyta między początkami własnych tur kosztuje dodatkowo *. Dotyczy także reakcji, nie pasywów, zwykłego Ataku, ruchu i przedmiotów. W grze solo skaza jest nieaktywna. Nie wraca stara blokada zdolności.

## 10. Nimra — kształtowanie kombinacji

| Czar | Czas | Mana | Proponowany efekt |
| --- | --- | --- | --- |
| Lodowy impuls | A | N | Obecne 1k8 zimna i -10 stóp ruchu przy porażce. |
| Kwasowy rozprysk | A | C | Obecne 1k6 kwasu w małym obszarze. |
| Szpilka umysłu | A | F | Obecne 1k6 psychicznych i odebranie reakcji. |
| Wachlarz płomieni | A | C+* | Obecny stożek, 2k6/połowa. |
| Fala odrzutu | A | N+C | Obecna linia, 2k6 i przesunięcie. |
| Lepka matryca | A | Z+N | Obecny teren i przewracanie, trzy rundy. |
| Mglisty krok | D | N+Z | Teleport 30 stóp, bez dodatkowej opłaty ruchu. |
| Sen | A | F+N+* | Pula 5k8 jak obecnie, sen najwyżej do końca następnej tury Nimry; pozostałe sposoby obudzenia pozostają. |
| Mgła | A | N+* | Obecny zasłonięty obszar; koncentracja, trzy rundy. |
| Sieć | A | Z+N+* | Obecne unieruchamianie i trudny teren; koncentracja, trzy rundy. |
| Piorunowy szlak | A | C+N+* | Obecne 3k6 i pojedynczy przeskok, również w sojusznika. |
| Załamanie woli | A | F+N | Obecny obszar 2k6, brak reakcji i utrudnienie ataku. |
| Staza istoty | A | N+F+* | Obecna blokada ruchu, ponawiane obrony, koncentracja do trzech rund. |
| Roztrzaskanie | A | C+C+* | Obecne 3k8/połowa w obszarze. |
| Tarcza | R | B | +3 KP wyłącznie przeciw jednemu atakowi; ponowna ocena trafienia. Zastępuje +5 KP do następnej tury. |

Metamagia to MOD, najwyżej jeden wariant na czar. Dodatkową manę płaci się łącznie z czarem. Bazowy czar z Metamagią może kosztować najwyżej cztery karty przed ewentualną dopłatą skazy; nie obniża się kosztu przekraczającego limit. To ograniczenie many egzekwują wyłącznie gracze, aplikacja nie blokuje kombinacji na podstawie jej ceny. Żadna Metamagia nie daje osobnej akcji i nie wzmacnia reakcyjnej Tarczy.

| Metamagia | Dopłata | Efekt |
| --- | --- | --- |
| Rzeźbienie pola | N | Wyłącz do czterech pól jak obecnie. |
| Odległy czar | Z | +15 stóp, maksymalnie 75. |
| Przeciążony czar | C | Jedna dodatkowa bazowa kość obrażeń. To inna zdolność niż ogólne przeciążenie koloru. |
| Wymuszony splot | F+F | Jeden cel ma utrudnienie pierwszej obrony; przez limit czar bazowy może kosztować najwyżej dwie karty. |
| Transmutacja energii | F | Zmień typ obrażeń w obecnym katalogu. |

Pasywy: Widzenie w ciemności 60 stóp; Gnomia przebiegłość daje przewagę w obronach INT/MDR/CHA przeciw magii; Katalog niemożliwego daje dostęp do wszystkich piętnastu czarów bez przygotowania. Odzyskiwanie magiczne zastępujemy „Alchemią barw”: raz we własnej turze potraktuj jedną N jako dowolny kolor przy opłacaniu czaru lub Metamagii. Karta zostaje normalnie wydana; nie tworzy dodatkowej many.

Nowe Echo magicznego wycieku: powtórzenie czaru lub Metamagii użytych w poprzedniej własnej turze powoduje dopłatę * do pierwszego takiego rzucenia w bieżącej własnej turze. Łączna dopłata najwyżej jedna, nawet gdy powtarzasz oba. Usuwamy zakaz powtarzania. Reakcje poza własną turą nie budują Echa. Pominięta tura czyści listę poprzednich wyborów. Maksymalny koszt po tej dopłacie wynosi pięć kart i mieści się w pojemności.

## 11. Erynd — przygotowywanie rynku i wybór celu

| Zdolność | Czas | Mana | Proponowany efekt |
| --- | --- | --- | --- |
| Znak łowcy | D | Z | +1k6 raz na własną turę przy trafieniu oznaczonego celu bronią; koncentracja, trzy rundy. Przeniesienie po pokonaniu celu bez many i akcji. Ograniczenie raz na turę zastępuje dodawanie do każdego trafienia. |
| Zwiadowcza mobilność | D | Z | Sprint albo Odstąpienie; obejmuje opłatę za zwykły ruch w tej turze. Sprint zwiększa limit, Odstąpienie znosi ataki okazyjne. Wcześniejszy ruch liczy się do limitu. |
| Celowanie | D | Z | Przed ruchem oddaj cały ruch, aby następny atak łukiem w tej turze miał przewagę. Osobny atak ma swój koszt many. |
| Strzała kotwicząca | A | Z+N | Obecne trafienie i obrona SIŁ; ograniczenie ruchu do początku następnej tury Erynda, bez losowania 1k4 rund. |
| Strzała odsłaniająca | A | Z+F | Trafienie: -2 KP do początku następnej tury Erynda. Zastępuje obniżenie o 1k8. Nie kumuluje się. |
| Strzała zakłócająca | A | Z+N | Obecne odebranie reakcji i utrudnienie następnego ataku. |
| Podwójny strzał | A | Z+C+* | Dwa osobne strzały długim łukiem, każdy z +2 do trafienia, z możliwością różnych celów. Jedno wybrane trafienie dodaje +1k6 obrażeń tej techniki. Znak i Pierwsza krew również najwyżej raz w całej turze. Oba ataki są w cenie; obrażenia, krytyki i reakcje rozstrzygane osobno. |
| Mglisty krok | D | N+Z | Teleport 30 stóp bez dodatkowej opłaty ruchu. |
| Kolczaste zarośla | A | Z+Z+* | Obecny niebezpieczny trudny teren; koncentracja, najwyżej trzy rundy. |

Pasywy: Łucznictwo daje +2 do dystansowych ataków bronią, już wliczone w +8 łuku; Ekspertyza podwaja biegłość Skradania i Sztuki przetrwania; Widzenie w ciemności 60 stóp; Dziedzictwo elfów daje przewagę przeciw zauroczeniu i odporność na magiczny sen; Czujność daje +2 do inicjatywy i wykrywania ukrytych przeciwników, nie pułapek. Pierwsza krew zmniejszona do +1k6 raz na własną turę, wyłącznie łukiem w cel z pełnymi PW. Nowe „Czytanie prądów”: raz na końcu własnej tury, po własnym doborze z rynku, ale przed jego uzupełnieniem, obejrzyj dwie wierzchnie karty talii i odłóż je w wybranej kolejności. Jeśli pozostała jedna, widzisz jedną; oglądanie samo nie przewija talii. Przygotowuje uzupełnienie rynku dla kolejnych osób.

Nowa Trauma bratobójczego strzału: pierwszy w swojej turze atak łukiem w cel mający przytomnego innego bohatera drużyny w 5 stopach kosztuje dodatkowo *. Jedna dopłata niezależnie od liczby bohaterów, bez starej kary do trafienia. Nóż, przywołania i NPC nie powodują dopłaty.

## 12. Przewinięcie talii i fala

Gdy trzeba dobrać lub odrzucić kartę, a talia jest pusta: natychmiast tasujemy stos odrzucony, pozostawiając rynek i rezerwy na stole, oraz dokładamy znacznik Fali. Kontynuujemy przerwaną operację. Samo dobranie ostatniej karty jeszcze nie jest przewinięciem. W wyjątkowym przypadku braku kart także na odrzuconych dobór nie odbywa się do pojawienia się odrzutów; nie tworzymy kart zastępczych.

Na końcu rundy najpierw wykonujemy odpływ rynku, a potem rozpatrujemy wszystkie zgromadzone znaczniki Fali kolejno. Gracze zgłaszają fale aplikacji; silnik sam ich nie wykrywa. Przewinięcie nie przerywa ataku ani reakcji.

Każda fala:

1. Podnosi Zagrożenie o jeden, maksymalnie do trzech. Każdy pojedynczy atak wroga zadający obrażenia otrzymuje płaskie +Zagrożenie do obrażeń; raz na trafiony cel, nie na kość/składnik obrażeń. Nie zwiększa trucizn okresowych, terenów ani strat PW niebędących atakiem. Premia nie jest kością krytyka; podlega zwykłym odpornościom jak obrażenia ataku.
2. Uruchamia zapowiedziane wydarzenie z tabeli poniżej na całą następną rundę.
3. Gracze rzucają k6 i wykładają zapowiedź kolejnego wydarzenia. Pierwszą zapowiedź losuje się przed pierwszą turą walki. Losowanie jest jawne, nie zależy od decyzji aplikacji.

Przy kilku falach jednego końca rundy wszystkie podnoszą Zagrożenie; wydarzenia różnych nazw współistnieją, powtórzenie tej samej nazwy nie kumuluje efektu. Natychmiastową wymianę z wyniku 6 wykonuje się osobno dla każdej fali. Wydarzenia rundowe wygasają na końcu następnej rundy przed nowymi falami.

| k6 | Wydarzenie | Dokładny efekt na następną rundę |
| --- | --- | --- |
| 1 | Żar | Każdy bohater może raz w swojej turze zastąpić C dowolną jedną kartą. Każdy wróg ma dodatkowe +1 do obrażeń ataków ponad Zagrożenie. |
| 2 | Ciężkie powietrze | Bazowa szybkość wszystkich istot spada o 10 stóp, minimum 5; teleporty i przymusowe przesunięcia bez zmiany. Bohater może opłacić zwykły ruch N zamiast *, uzyskując na tę turę odporność na to konkretne spowolnienie. To wybór wariantu efektu, zgłaszany aplikacji bez dowodu płatności. |
| 3 | Zielony przypływ | Na następną rundę limit starej rezerwy i całkowita pojemność każdego bohatera rosną o jeden: zwykle 3/6, Lorian 4/7. Dobór nadal trzy. Po wygaśnięciu nadmiar ponad zwykłą pojemność odrzuca się od razu, a starą rezerwę normalnie porządkuje na końcu kolejnej własnej tury. |
| 4 | Blada osłona | Wszystkie istoty, również wrogowie, mają +1 KP. Pierwsze przywrócenie PW każdemu bohaterowi w tej rundzie leczy dodatkowo 2 PW. |
| 5 | Czarne zakłócenie | Ogólne przeciążenie koloru odrzuca trzy wierzchnie karty zamiast dwóch. Pierwsza własna zdolność specjalna każdego bohatera w tej rundzie może potraktować jedną F jako dowolny kolor. |
| 6 | Przetasowanie prądów | Natychmiast każdy bohater, w kolejności inicjatywy, może wymienić jedną posiadaną kartę z rynkiem. Bez dobierania; rynek zmienia się dla kolejnych osób. Brak dalszego efektu rundowego. |

Zagrożenie zawsze rośnie, nawet przy korzystnym wydarzeniu. Nie ma losowej utraty całej tury, natychmiastowego zabijania ani niesygnalizowanych posiłków. Specjalne wydarzenia scenariuszowe i pola wyładowań to późniejsze rozszerzenie, po przetestowaniu prostego zestawu.

## 13. Granica aplikacji

Aplikacja NIE przechowuje talii, rynku, liczby kart, kolorów rezerwy, historii fizycznych płatności ani wyników wymian. Nie skanuje kart many. Nie pyta o dowód opłacenia, nie blokuje z powodu many i nie przedstawia dostępności zdolności na podstawie domniemanej rezerwy. Reset walki w aplikacji wymaga ręcznego odtworzenia kart przez graczy; zapis gry nie zapisuje fizycznego stołu.

Aplikacja pokazuje koszt jako informację, np. „Wydaj zieloną i niebieską manę”. Przy znanej z walki skazie może pokazać dopłatę. Nie dokłada się osobnego okna „potwierdź płatność”: dotychczasowe wykonanie decyzji wystarcza. Przekroczenie limitu fizycznych kart lub niewłaściwy kolor pozostaje kwestią zasad przy stole.

Aplikacja nadal sprawdza: czyja tura, zużycie akcji i reakcji, stan postaci, legalny cel, zasięg, wyposażenie, koncentrację i skutki. Warianty wpływające na walkę, np. Metamagia, Zryw, uruchomienie Szału lub ruch niewrażliwy na Ciężkie powietrze, muszą być zadeklarowane; kontrolujemy ich efekt i czas, nie płatność. Pasywy wpływające wyłącznie na fizyczne karty są obsługiwane w całości przy stole.

Jedyny nowy transport potrzebny dla fali: zgłoszenie „Nadeszła fala” wraz z numerem odkrytego wydarzenia. Aplikacja rozlicza Zagrożenie i efekty bojowe; nie sprawdza, czy talia faktycznie się skończyła. Wydarzenia czysto karciane mogą otrzymać tylko przypomnienie. Fizyczną zapowiedź następnej fali prowadzą gracze.

## 14. Po walce i test balansu

Po zakończeniu starcia rezerwy i rynek wracają do talii, Zagrożenie oraz wydarzenia wygasają. Pozostała mana nie leczy drużyny po zakończeniu walki. Nie rozpoczynamy sztucznej walki dla odnowienia zasobów. Eksploracyjne leczenie opieramy w pierwszym teście o odpoczynek/kości wytrzymałości i istniejące przedmioty; bojowe zdolności objęte talią nie otrzymują nowych zastosowań poza walką. Uczciwie wymaga to późniejszego sprawdzenia tempa całej kampanii.

Pierwotna kolejność proponowanych prac (użytkownik następnie zlecił implementację przed testami stołowymi):

1. Omówić i zamrozić wersję zasad stołu: płatny ruch, pojedynczy zwykły atak i seria wyłącznie Loriana za 1* każdy, dobór 3 na końcu tury, stara rezerwa 2/3 i całkowita pojemność 5/6. Nie drukować jeszcze finalnych kart.
2. Test papierowy trzech bohaterów: Garran, Dagna, Nimra, po cztery zdolności i pełne koszty podstawowe. Porównać walkę z grupą, z jednym silnym wrogiem i z celem wymagającym ruchu.
3. Test wszystkich siedmiu, w tym pełny zestaw zarządzania maną Loriana, zwroty Brakki po ataku, Lorian+Erynd, Brakka+Mira, różne kolejności inicjatywy i składy 1–5. Sprawdzić, czy grupy bez użytkownika danego koloru nadal mają sensowną ekonomię.
4. Notować czas decyzji, wybierane zdolności, dopłaty skaz, wymiany 2:1, niewykorzystane akcje z powodu kart, rundę pierwszej fali, karty zużywane przez każdego bohatera oraz leczenie. Sprawdzić celowe przeciąganie walki, monopolizację rynku i powtarzane usypianie/obezwładnianie pojedynczego wroga. Powtarzać te same spotkania i zapisane kolejności talii przy porównywaniu kosztów.
5. Dopiero po testach wdrożyć jawnie osobny profil reguł dla siedmiu bohaterów: oddzielić koszty fizyczne od dawnych bramek zasobów, w tym reakcji, czarów i inicjowania podglądu. Nie wyłączać walidacji czasu/pozycji i nie zmieniać automatycznie generycznych postaci 5e.
6. Zaimplementować skutki zmienionych zdolności, pasywów/skaz bojowych i zgłaszanych fal; objąć je testami. Osobno sprawdzić, że brak starych punktów nie blokuje gry, a aplikacja nie wymaga żadnego stanu fizycznej many.
7. Na końcu wspólnie odtworzyć instrukcję, koszty w UI i wszystkie karty z zatwierdzonego katalogu.

Kryteria decyzji: zwykły ruch + atak muszą dać się opłacić po zwykłym doborze bez konkretnego koloru; silny czar z Metamagią powinien wymagać rezerwy lub rezygnacji z ruchu; seria zwykłych ataków nie może zawsze wypierać technik za dwa/trzy kolory; techniki wygrywają pozycją, kontrolą, dokładnością albo obszarem, nie samą liczbą rzutów; żadna postać nie powinna rutynowo potrzebować całego rynku. Te kryteria i powyższe liczby wymagają rozegrania, nie są jeszcze potwierdzonym balansem.


## 15. Dodatkowe sprawdzenia wersji 0.2

- Tylko Lorian może opłacić wiele zwykłych ataków. Do sprawdzenia są czas jego serii i konkurencja ataków z zarządzaniem maną drużyny. Pozostali wykonują jedno zwykłe uderzenie; liczba ataków technik wynika z ich opisu.
- Premie raz na własną turę (Atak z cienia, Pierwsza krew, Znak łowcy) dotyczą jednego wybranego kwalifikującego się trafienia, nie każdego ataku. Wybór przed rzutem obrażeń. Różne premie mogą wystąpić na tym samym trafieniu, ale każda zużywa swój limit. Krytyki nadal mnożą kości zgodnie z regułami danego ataku, nie płaskie premie.
- Dodatkowe ataki w zwykłej serii nie są dodatkowymi akcjami; MOD Lekkomyślnego i D Zrywu mają własny koszt i nie odnawiają akcji. Koszty skaz nie są mnożone przez długość serii.
- Efekty Loriana nie uruchamiają kolejnego doboru końca tury. Odzysk kosztuje akcję główną, zwrot Brakki działa raz po ataku, a przyrost ponad pojemność jest odrzucany. Sprawdzić możliwość powtarzanego tworzenia nadwyżki przez Odzysk — jego wartość dla drużyny jest zamierzona, nieskończony łańcuch nie.
- Rezerwa na kolejną turę jest ujawniona wcześniej. Reakcja może zniszczyć zaplanowaną kombinację; nie dodajemy automatycznego uzupełnienia dla zrekompensowania reakcji/skazy. Zweryfikować, czy nadal jest to przyjemny wybór, szczególnie przy atakach obszarowych i częstym wykrywaniu Miry.

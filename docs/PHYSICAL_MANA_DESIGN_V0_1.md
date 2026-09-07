# Fizyczna mana — projekt do testów 0.1

> Wersja historyczna. Aktualne kolory i symbole (czarna zamiast fioletowej) oraz zasady są w [wersji 0.2](PHYSICAL_MANA_DESIGN_V0_2.md).

Archiwalna propozycja. Aktualna dyskusja: [wersja 0.2](PHYSICAL_MANA_DESIGN_V0_2.md).

Status: propozycja do dyskusji i testów przy stole, nie obowiązujące zasady aplikacji. Nie wdraża zmian w silniku ani w aktualnych wydrukach. Wszystkie podane koszty i zmiany efektów są konkretnym punktem wyjścia, nie wynikiem testów balansu.

Zakres: siedem grywalnych bohaterów na poziomie 3. Źródło obecnych zdolności: `BOARDGAME_ARCHETYPES_LEVELS_1_3.md`. Fizyczna talia, rynek, rezerwy, opłacanie i wymiany pozostają wyłącznie przy stole. Aplikacja obsługuje deklaracje i skutki działań.

## 1. Tura i koszty podstawowe

W swojej turze bohater ma jedną akcję główną, jeden limit ruchu i najwyżej jedną akcję dodatkową. Ma również jedną reakcję odnawianą na początku swojej tury. Runda obejmuje tury wszystkich uczestników. Mana nie kupuje dodatkowych akcji.

| Działanie | Koszt many | Koszt czasu |
| --- | --- | --- |
| Zwykły atak bronią — jeden atak | 1 dowolna | Akcja główna |
| Zwykły ruch do limitu szybkości | 1 dowolna | Ruch; płatność raz na turę, można dzielić przed/po akcji |
| Użycie zwykłego przedmiotu, pomoc, stabilizacja, ucieczka z chwytu, przeszukanie | 1 dowolna | Akcja główna; przedmiot nadal musi istnieć |
| Atak okazyjny | 1 dowolna | Reakcja |
| Prosta zmiana broni/interakcja z obiektem | 1 dowolna | Istniejący limit interakcji; kolejna może wymagać akcji |
| Zakończenie tury, pas, podgląd, anulowanie, dobór i porządkowanie kart | 0 | Bez dodatkowej akcji |
| Mimowolne przesunięcie, ratunkowy ruch z pasywu | 0 | Wynika z efektu, bez uruchamiania zwykłego ruchu |

Koszt zdolności specjalnej jest całkowity: nie dodajemy do niego opłaty za zwykły atak. Ruch zawarty w zdolności jest w jej cenie. Osobny zwykły ruch kosztuje dodatkowo 1 dowolną. Płatność za ruch nie omija stanów, trudnego terenu, zasięgu ani ataków okazyjnych. Wstanie nadal zużywa połowę dostępnego ruchu i wymaga uruchomienia ruchu, jeśli nie zrobił tego inny efekt.

Podstawowe działania kontekstowe nie przyznają wszystkim klasowych technik, np. Ukrycia Miry czy Sprintu Erynda. Nie dodajemy uniwersalnego darmowego uniku. Pasywne rzuty obronne i ratowanie przed śmiercią nie kosztują many.

## 2. Karty, rynek i rezerwa

Oznaczenia kosztów: C = czerwony/płomień, N = niebieski/fala, Z = zielony/liść, B = biały/tarcza, F = fioletowy/spirala, * = dowolna karta. Każdy znak oznacza osobną fizyczną kartę; N+* to dwie karty, N lub dowolna byłoby innym kosztem. Karty mają symbole i nazwy obok koloru.

| Kolor | Funkcja |
| --- | --- |
| C | Siła, obrażenia, przełamanie |
| N | Kontrola, obrona magiczna, porządkowanie |
| Z | Mobilność, precyzja, natura |
| B | Ochrona, leczenie, współpraca |
| F | Podstęp, osłabienia, zmiana właściwości |

Na początku walki tasujemy talię. Każdy bohater otrzymuje jedną losową odkrytą kartę do rezerwy, następnie wykładamy rynek. Na początku własnej tury przytomny i zdolny do działania bohater bierze z rynku do trzech kart. Nie uzupełnia rynku pomiędzy tymi wyborami. Limit posiadania to pięć kart; pomijanie doboru jest dozwolone. Nie dobiera się osobno na reakcję.

Po turze zachowuje najwyżej dwie niewydane karty. Nadmiar odrzuca, rynek uzupełnia się do pełna. Zachowane karty mogą być używane na reakcje albo w następnej turze. Gracz sam wybiera, które zachować. Po utracie przytomności karty pozostają przy postaci, ale nie dają możliwości działania.

Rynek jest jednym rzędem: po zabraniu kart pozostałe przesuwają się w lewo, nowe dokładamy z prawej. Koniec każdej rundy: odrzucamy jedną skrajną lewą kartę i uzupełniamy rynek. To minimalny upływ czasu także przy oszczędzaniu zasobów.

Parametry startowe do testów, ustalane według liczby bohaterów rozpoczynających walkę; pokonanie bohatera nie zmienia talii:

| Bohaterowie | Karty w talii | Każdego koloru | Rynek |
| --- | --- | --- | --- |
| 1 | 20 | 4 | 5 |
| 2 | 30 | 6 | 6 |
| 3 | 40 | 8 | 7 |
| 4 | 50 | 10 | 8 |
| 5 | 60 | 12 | 9 |

To zmiana wobec wcześniejszej propozycji: koszt płatnego ruchu i podstawowego ataku wymaga większego dopływu niż dwie karty na turę. Dla trzech osób start pochłania 10 z 40 kart; przy pełnym doborze i odpływie zużywamy następnie około 10 kart na rundę. Pierwsza fala wypada orientacyjnie po trzech rundach, wcześniej przy przeciążeniach. To rachunek przepływu, nie wynik rozegranych walk.

## 3. Wymiana, przeciążenie i płatność

- Dwie dowolne karty mogą zastąpić jeden wymagany kolor. Wszystkie opłaty za jedno działanie trzeba pokryć naraz; nie można zagrać czaru częściowo.
- Raz we własnej turze można przeciążyć jedną posiadaną kartę: liczy się jako dowolny kolor, a dwie wierzchnie karty talii trafiają zakryte na stos odrzucony. Nadal wydaje się kartę zastępującą kolor. Nie daje to akcji, dodatkowej karty ani możliwości przekroczenia pojemności.
- Zdolności wymiany zamieniają istniejące karty 1:1, nie dobierają nowych i nie uzupełniają rynku. Przekazanie karty między graczami jest możliwe tylko przez wyraźną zdolność; zwykły handel rezerwami jest niedozwolony.
- Karty wydaje się przy ostatecznym wykonaniu, przed rzutem. Pudło lub udana obrona celu nie zwracają kart. Anulowany podgląd nic nie kosztuje. Gracze sami rozliczają błędną deklarację cofniętą przed rozstrzygnięciem.
- Skaza z przymusowym odrzuceniem: bez karty nic nie odrzucasz i nie zaciągasz długu. Skaza z dopłatą: koszt trzeba opłacić, żeby zgodnie z zasadami wykonać działanie; aplikacja tego nie blokuje ani nie sprawdza.
- Limity dotyczące fizycznej many gracze oznaczają obróceniem karty pasywu/skazy. Limity „raz we własnej turze” zerują się na początku kolejnej własnej tury. „Raz między własnymi turami” obejmuje też reakcje i używa tego samego znacznika.

## 4. Co zastępujemy

W wariancie fizycznej many usuwamy bojowe koszty Taktyki, Forteli, Instynktu, Dzikości, Inspiracji, Metamagii, komórek czarów i Boskiej Mocy dla siedmiu talii. Nie wymagamy dodatkowo starych użyć Drugiego oddechu/Zrywu/Szału. Inspiracja jako efekt k6 i Szał jako stan mogą pozostać.

Zostają statystyki, bronie, rzuty, osłony, linia widzenia, koncentracja, ograniczenia stanów i cele. Zachowujemy rasowe cechy niewymagające zasobów, cechy fabularne i umiejętności. Wyjątki i zastępowane pasywy są nazwane poniżej. Nie nakładamy starych kar skazy na nową wersję.

Jeżeli tabela podaje „jak obecnie”, pełny efekt, cele i zasięg bierze się z aktualnej talii, ale koszty punktów/komórek zastępuje wymieniona mana. Czary działają na bazowym poziomie; nie wybieramy komórki ani podwyższenia poziomu. A = akcja główna, D = dodatkowa, R = reakcja, MOD = modyfikator jednej akcji, bez osobnego czasu. Każda pozycja kosztu ma swój czas niezależnie od posiadanej many.

## 5. Garran — obrona i oszczędna współpraca

| Zdolność | Czas | Mana | Proponowany efekt |
| --- | --- | --- | --- |
| Drugi oddech | A | B+* | Odzyskaj 1k10+3 PW. Zmiana z akcji dodatkowej na główną: leczenie konkuruje z ofensywą. |
| Zryw akcji | D | C+* | Następna zwykła akcja Ataku w tej turze zawiera dwa osobne ataki bronią zamiast jednego. Sam atak kosztuje nadal 1*. Nie odnawia akcji, nie wzmacnia technik specjalnych, nie tworzy łańcucha Zrywów. |
| Uderzenie tarczą | A | C+N | Sporny test Siły, 1k4+SIŁ i odepchnięcie o 5 stóp jak obecnie. Nie zużywa całego ruchu. |
| Pozycja obronna | D | B | +2 KP do początku następnej tury; każda zmiana pola kończy efekt. Zastępuje dawny koszt całego ruchu. |
| Rozkaz: Stać | A | N+* | Obecny rozkaz, w tym naturalne 1/20. |
| Osłona tarczą | D | B+N | Sąsiadujący sojusznicy mają +2 KP do początku następnej tury Garrana; bez premii dla niego. |
| Mowa dowódcy | A | B+* | Usuń Strach u słyszących sojuszników w 30 stopach i siebie; przewaga na ich pierwszy atak/test/obronę jak obecnie. |
| Osłona towarzysza | A | B+N | Przekieruj pierwszy pojedynczy wrogi efekt z sąsiadującego sojusznika na Garrana jak obecnie. |

Pasywy: zostają Obrona, krytyk 19–20 i Żelazna linia. Nowy „Za tarczą”: raz we własnej turze, gdy przytomny bohater jest w 5 stopach, Garran może potraktować jedną N jako B w swojej zdolności ochronnej: Pozycji, Osłonie tarczą lub Osłonie towarzysza. Nie działa na samoleczenie.

Nowe Wyrzuty sumienia: jeżeli Garran otrzymał w tej walce mniej łącznych obrażeń niż co najmniej jeden inny bohater, pierwsze ofensywne działanie w jego turze kosztuje dodatkowo *. Ofensywne = atak, szkodliwy rozkaz lub technika przeciw wrogowi. Zryw sam nie jest ofensywnym działaniem; dopłata dotyczy następnej akcji Ataku. Limit jednej dopłaty na turę. Bez starego -2. W grze solo brak innego bohatera wyłącza warunek.

## 6. Brakka — wykorzystanie czerwonej many i presja ataku

| Zdolność | Czas | Mana | Proponowany efekt |
| --- | --- | --- | --- |
| Szał | D | C | Na bieżącą turę i do początku następnej: +2 obrażeń wręcz z SIŁ, odporności fizyczne i przewaga SIŁ jak obecnie. Bez Dzikości; w kolejnej turze można uruchomić ponownie. |
| Lekkomyślny atak | A | C | Jeden atak wręcz z SIŁ z przewagą, ataki przeciw Brakce mają przewagę do jej następnej tury. |
| Potężne uderzenie | A | C+C | W Szale: jeden atak z +2 do trafienia i +1k12 obrażeń przy trafieniu. Zastępuje dawne +10 do trafienia. |
| Z bara | A | C+N | Obecne odpychanie Atletyką. |
| Przyspieszenie | D | Z | W Szale: uruchamia zwykły ruch bez dodatkowej opłaty i podwaja jego bazowy limit w tej turze. Wykonany wcześniej ruch liczy się do nowego limitu. |
| Ogłuszający ryk | A | C+N+* | W Szale: obecny stożek, 2k6, ograniczenie ruchu i naturalne wyniki. |
| Twarda jak skała | R | B | W Szale: redukcja 1k12+KON po odporności jak obecnie. |
| Chwyt | A | * | Obecny chwyt, wolna ręka i limit wielkości celu. |

Pasywy: zostają rasowe cechy i Dzikie ataki. Nieustępliwość półorka zostaje raz na długi odpoczynek, jako wyjątek ratunkowy — mana nie pozwala jej ponawiać. Nowy „Bitewny rozpęd”: raz we własnej turze, po trafieniu zwykłym atakiem opłaconym C, odzyskaj tę C z odrzuconych. Dotyczy wyłącznie podstawowego ataku, nie Lekkomyślnego ani Potężnego; nie wyzwala kolejnej akcji i podlega limitowi pięciu kart.

Nowy Bitewny amok: jeśli Brakka uruchomiła Szał, lecz w swojej turze nie zadeklarowała żadnego ataku ani szkodliwej techniki przeciw wrogowi, przed porządkowaniem rezerwy odrzuca jedną posiadaną kartę. Pudło nie uruchamia kary. Ta wersja zastępuje zakaz używania przedmiotów.

## 7. Mira — poprawianie doboru dzięki pozycji

| Zdolność | Czas | Mana | Proponowany efekt |
| --- | --- | --- | --- |
| Ukryj się | A | * | Obecny test ukrycia i osobni obserwatorzy. Dobrowolne zakończenie ukrycia bez many/akcji. |
| Zasłona dymna | A | Z+F | Ruch do 15 stóp bez ataków okazyjnych i próba ukrycia nawet przy wrogu; cały ruch w cenie. |
| Przeskok przez gardę | A | Z+* | Obecny atak +2/+2 i przejście na wolne pole za celem; to przesunięcie w cenie. |
| Wykrycie pułapek | A | * | Obecny test Percepcji w walce. |
| Cięcie ścięgna | A | Z+N | Atak z własnej flanki; trafienie połowi ruch do początku następnej tury Miry, zamiast do leczenia. |
| Przeszywający atak | A | Z+C+* | Obecny atak i drugi cel za pierwszym, z warunkiem sojusznika przy pierwszym celu. |
| Mistrzyni ostrzy | A | Z+F | Trafienie nożem z ukrycia powoduje krwawienie 1k4 przez najwyżej dwie tury celu; leczenie kończy wcześniej. Bez kumulowania. |
| Unik instynktowny | R | Z | Obecna reakcja z utrudnieniem ataku przeciw ukrytej Mirze. |

Pasywy: pozostają warunki ukrycia, Szczęście, Ruchomy cel i Ekspertyza. Atak z cienia ma +1k6 za ukrycie przed celem lub własną flankę, +2k6 za oba; raz na własną turę. Zmniejszamy dotychczasowe +2k6/+3k6, ponieważ nie ogranicza go długoterminowa pula.

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

Pasywy: pozostają cechy krasnoludzkie i Krok ratowniczki — po pomocy innemu sojusznikowi ruch 5 stóp bez many, raz we własnej turze. Nowy Uczeń Życia: raz we własnej turze można zastąpić jedną B przez Z w zdolności, która faktycznie przywraca PW innemu bohaterowi. Nie dotyczy przygotowania aury ani własnego leczenia. Stara premia zależna od poziomu komórki znika; +7 Słowa leczenia to już pełna premia, bez dodatkowego doliczania.

Nowe Nikogo nie zostawiam: jeśli żywy bohater z 0 PW jest w 30 stopach, pierwsze ofensywne działanie Dagny we własnej turze kosztuje dodatkowo *. Leczenie, ratowanie, osłony i ruch nie dostają dopłaty. Zastępuje dotychczasowe utrudnienia/przewagę obron wrogów.

## 9. Lorian — przekazywanie odpowiednich kolorów

| Zdolność | Czas | Mana | Proponowany efekt |
| --- | --- | --- | --- |
| Inspiracja bardowska | D | B | Obecna kość k6 dla sojusznika; maksymalnie jedna niewydana Inspiracja na odbiorcę. |
| Luneta optyczna | A | Z+N+* | Przed ruchem dwa strzały w jeden cel, ignorujące 2 KP; zużywa cały ruch. Nie trzeba dodatkowo płacić za niewykonany ruch. |
| Ostrzał destabilizujący | A | Z+F | Jeden strzał, obecne utrudnienia po trafieniu. |
| Prowokujący ostrzał | A | C+F | Jeden strzał; trafienie daje celowi +2 przeciw Lorianowi i -2 przeciw pozostałym do następnej tury Loriana. Zastępuje premię/karę równą obrażeniom. |
| Oplatający ostrzał | A | Z+N | Obecny obszar 3×3, ograniczenie ruchu, bez obrażeń. |
| Podszept paniki | A | F+N | Obecne 2k6 i ucieczka; sukces połowa bez ruchu. |
| Fala gromu | A | C+N | Obecne 2k8 i odepchnięcie, także sojusznicy. |
| Baśniowy ogień | A | F+B | Obecny obszar, przewaga i ujawnienie; koncentracja, maksymalnie trzy rundy. |
| Ohydny śmiech | A | F+N+* | Obecny upadek/obezwładnienie, koncentracja; maksymalnie do końca następnej tury Loriana. |
| Rozkaz sceniczny | A | F+* | Obecny pojedynczy rozkaz i ograniczenia celów; bez zmiany na dłuższą kontrolę. |
| Przyspieszony refren | A | Z+C+* | Dwa strzały w cenie. Koncentracja do końca następnej własnej tury: wtedy można wykonać D za Z, dającą jeden dodatkowy strzał. Bez odnawiania i bez trzeciego strzału pasywnego. |
| Kontrapunkt | R | Z | Obecny jeden strzał po zranieniu celu przez inspirowanego sojusznika. |
| Rozpraszający okrzyk | R | B | Obecna redukcja obrażeń 1k6+2. |
| Cięte słowa | R | F | Obecne odjęcie k6 od kwalifikującego się rzutu. |

Kusznik zostaje zmieniony: zwykła akcja Ataku za * daje jeden strzał. Nowy pasyw „Zgranie”: raz we własnej turze zamień jedną posiadaną kartę z jedną kartą przytomnego, zgadzającego się bohatera w 30 stopach. Zamiana 1:1, bez nadwyżki. W grze jednym bohaterem zamiana odbywa się z rynkiem. Zachowujemy rasowe cechy, Obycie i pozabojową Improwizację.

Nowa Potrzeba publiczności: bez przytomnego bohatera w 10 stopach pierwsza zdolność specjalna użyta między początkami własnych tur kosztuje dodatkowo *. Dotyczy również reakcji i czarów, nie zwykłego ataku, ruchu czy przedmiotu. Usuwamy dawną blokadę specjalnych zdolności. W składzie z jednym bohaterem skaza jest nieaktywna.

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

Pasywy: pozostają rasowe cechy i pełen katalog czarów bez przygotowania. Odzyskiwanie magiczne zastępujemy „Alchemią barw”: raz we własnej turze potraktuj jedną N jako dowolny kolor przy opłacaniu czaru lub Metamagii. Karta zostaje normalnie wydana; nie tworzy dodatkowej many.

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
| Podwójny strzał | A | Z+C+* | Obecne 2k8+2×ZRC w jednym teście; Znak i Pierwsza krew najwyżej raz. |
| Mglisty krok | D | N+Z | Teleport 30 stóp bez dodatkowej opłaty ruchu. |
| Kolczaste zarośla | A | Z+Z+* | Obecny niebezpieczny trudny teren; koncentracja, najwyżej trzy rundy. |

Pasywy: zostają Łucznictwo, Ekspertyza, rasowe cechy i Czujność. Pierwsza krew zmniejszona do +1k6 raz na własną turę, wyłącznie łukiem w cel z pełnymi PW. Nowe „Czytanie prądów”: raz we własnej turze, po własnym doborze, obejrzyj dwie wierzchnie karty talii i odłóż je w wybranej kolejności. Jeśli pozostała jedna, widzisz jedną; oglądanie samo nie przewija talii. Przygotowuje uzupełnienie rynku dla kolejnych osób.

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
| 3 | Zielony przypływ | Każdy bohater może zachować do trzech kart zamiast dwóch na końcu swojej tury. Pojemność pięciu i dobór do trzech pozostają. Nadmiar ponad dwie po wygaśnięciu odrzuca się dopiero na końcu kolejnej własnej tury. |
| 4 | Blada osłona | Wszystkie istoty, również wrogowie, mają +1 KP. Pierwsze przywrócenie PW każdemu bohaterowi w tej rundzie leczy dodatkowo 2 PW. |
| 5 | Fioletowe zakłócenie | Ogólne przeciążenie koloru odrzuca trzy wierzchnie karty zamiast dwóch. Pierwsza własna zdolność specjalna każdego bohatera w tej rundzie może potraktować jedną F jako dowolny kolor. |
| 6 | Przetasowanie prądów | Natychmiast każdy bohater, w kolejności inicjatywy, może wymienić jedną posiadaną kartę z rynkiem. Bez dobierania; rynek zmienia się dla kolejnych osób. Brak dalszego efektu rundowego. |

Zagrożenie zawsze rośnie, nawet przy korzystnym wydarzeniu. Nie ma losowej utraty całej tury, natychmiastowego zabijania ani niesygnalizowanych posiłków. Specjalne wydarzenia scenariuszowe i pola wyładowań to późniejsze rozszerzenie, po przetestowaniu prostego zestawu.

## 13. Granica aplikacji

Aplikacja NIE przechowuje talii, rynku, liczby kart, kolorów rezerwy, historii fizycznych płatności ani wyników wymian. Nie skanuje kart many. Nie pyta o dowód opłacenia, nie blokuje z powodu many i nie przedstawia dostępności zdolności na podstawie domniemanej rezerwy. Reset walki w aplikacji wymaga ręcznego odtworzenia kart przez graczy; zapis gry nie zapisuje fizycznego stołu.

Aplikacja pokazuje koszt jako informację, np. „Wydaj zieloną i niebieską manę”. Przy znanej z walki skazie może pokazać dopłatę. Nie dokłada się osobnego okna „potwierdź płatność”: dotychczasowe wykonanie decyzji wystarcza. Przekroczenie limitu fizycznych kart lub niewłaściwy kolor pozostaje kwestią zasad przy stole.

Aplikacja nadal sprawdza: czyja tura, zużycie akcji i reakcji, stan postaci, legalny cel, zasięg, wyposażenie, koncentrację i skutki. Warianty wpływające na walkę, np. Metamagia, Zryw, uruchomienie Szału lub ruch niewrażliwy na Ciężkie powietrze, muszą być zadeklarowane; kontrolujemy ich efekt i czas, nie płatność. Pasywy wpływające wyłącznie na fizyczne karty są obsługiwane w całości przy stole.

Jedyny nowy transport potrzebny dla fali: zgłoszenie „Nadeszła fala” wraz z numerem odkrytego wydarzenia. Aplikacja rozlicza Zagrożenie i efekty bojowe; nie sprawdza, czy talia faktycznie się skończyła. Wydarzenia czysto karciane mogą otrzymać tylko przypomnienie. Fizyczną zapowiedź następnej fali prowadzą gracze.

## 14. Po walce i test balansu

Po zakończeniu starcia rezerwy i rynek wracają do talii, Zagrożenie oraz wydarzenia wygasają. Pozostała mana nie leczy drużyny po zakończeniu walki. Nie rozpoczynamy sztucznej walki dla odnowienia zasobów. Eksploracyjne leczenie opieramy w pierwszym teście o odpoczynek/kości wytrzymałości i istniejące przedmioty; bojowe zdolności objęte talią nie otrzymują nowych zastosowań poza walką. Uczciwie wymaga to późniejszego sprawdzenia tempa całej kampanii.

Kolejność prac:

1. Omówić i zamrozić wersję zasad stołu, w szczególności płatny ruch, dobór 3, rezerwę 2 i jedną akcję główną. Nie drukować jeszcze finalnych kart.
2. Test papierowy trzech bohaterów: Garran, Dagna, Nimra, po cztery zdolności i pełne koszty podstawowe. Porównać walkę z grupą, z jednym silnym wrogiem i z celem wymagającym ruchu.
3. Test wszystkich siedmiu, w tym Lorian+Erynd, Brakka+Mira, różne kolejności inicjatywy i składy 1–5. Sprawdzić, czy grupy bez użytkownika danego koloru nadal mają sensowną ekonomię.
4. Notować czas decyzji, wybierane zdolności, dopłaty skaz, wymiany 2:1, niewykorzystane akcje z powodu kart, rundę pierwszej fali, karty zużywane przez każdego bohatera oraz leczenie. Sprawdzić celowe przeciąganie walki, monopolizację rynku i powtarzane usypianie/obezwładnianie pojedynczego wroga. Powtarzać te same spotkania i zapisane kolejności talii przy porównywaniu kosztów.
5. Dopiero po testach wdrożyć jawnie osobny profil reguł dla siedmiu bohaterów: oddzielić koszty fizyczne od dawnych bramek zasobów, w tym reakcji, czarów i inicjowania podglądu. Nie wyłączać walidacji czasu/pozycji i nie zmieniać automatycznie generycznych postaci 5e.
6. Zaimplementować skutki zmienionych zdolności, pasywów/skaz bojowych i zgłaszanych fal; objąć je testami. Osobno sprawdzić, że brak starych punktów nie blokuje gry, a aplikacja nie wymaga żadnego stanu fizycznej many.
7. Na końcu wspólnie odtworzyć instrukcję, koszty w UI i wszystkie karty z zatwierdzonego katalogu.

Kryteria decyzji: zwykły ruch + atak muszą dać się opłacić po zwykłym doborze bez konkretnego koloru; silny czar z Metamagią powinien wymagać rezerwy lub rezygnacji z ruchu; zwykły atak nie może być zawsze gorszy od taniej techniki; żadna postać nie powinna rutynowo potrzebować całego rynku. Te kryteria i powyższe liczby wymagają rozegrania, nie są jeszcze potwierdzonym balansem.

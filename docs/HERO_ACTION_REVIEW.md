# Przegląd zdolności bohaterów po przejściu na runy

Stan analizy: 22 września 2026. Zakres: wszystkie 66 kart siedmiu bohaterów,
ich koszty, wzmocnienia i odpowiadające im ścieżki wykonania w grze.
Audyt przedstawia stan przed korektami. Użytkownik następnie zlecił ich wdrożenie;
wybrane warianty i aktualny zestaw 65 kart opisuje [RUNE_BALANCE_V02.md](RUNE_BALANCE_V02.md).
Poniższe porównania pozostają uzasadnieniem zmian, nie bieżącą specyfikacją kart.

**Zatwierdzona zmiana Miry:** Zasłona dymna tworzy obszar 3×3, w którym
testy Ukrycia mają przewagę. Ukrycie pozostaje osobną zdolnością. Dotychczasowe
automatyczne Ukrycie i darmowe przemieszczenie z tej karty odpadają. Przyjęty
czas dymu to koniec następnej tury Miry: przy jednej akcji
specjalnej na turę musi zdążyć skorzystać z osobnego Ukrycia. Dawne
wzmocnienie „przewaga Ukrycia” powielałoby teraz efekt podstawowy. Nowa
karta nie ma wzmocnień. Dym jest stacjonarny, ze środkiem na polu Miry,
i działa także na wrogów, co pozostawia ryzyko złego ustawienia.

## Co wymaga decyzji w pierwszej kolejności

1. **Rozdzielić Szpilkę umysłu i Załamanie woli Nimry.** Obecnie drugie
   wykonuje niemal to samo, lepiej, za taki sam budżet akcji i liczbę run.
2. **Porównać liczbę ataków kupowaną za S.** Podwójny strzał Erynda daje
   dwa ataki i zachowuje zwykły atak; Luneta Loriana zużywa całą turę na
   jeden strzał z premią +2. Sam inny symbol kosztu tego nie równoważy.
3. **Ustalić rolę odzyskiwania run.** Odzysk energii i Wielkie strojenie
   są bardzo podobne. Mogą odzyskiwać właśnie zapłacony koszt, więc Lorian
   istotnie zmienia zasadę skończonego zapasu na walkę.
4. **Rozstrzygnąć, co ma oznaczać „zbieram na mocniejsze”.** Wszystkie
   podstawowe karty kosztują jedną właściwą runę, również największe moce.
   Dodatkową ceną jest zwykle rezygnacja z ataku lub ruchu, a nie oszczędzanie
   większej liczby run.
5. **Ujednolicić czytanie symboli.** Symbol naciskany na planszy i symbol
   wydawanej runy często są różne. To działa technicznie, ale wymaga dwóch
   skojarzeń dla jednej karty.

## Założenia ekonomii użyte w ocenie

`S` to jedna akcja specjalna, `A` to zwykły atak lub przedmiot, `M` to cały
niewykorzystany ruch, `R` to reakcja. Zatem karta `S`, która wykonuje atak,
daje go **oprócz** zachowanego zwykłego ataku. `A+S` zastępuje oba te
elementy tury. Zwykły atak okazyjny bronią jest bezpłatny w runach; płatne
reakcje konkurują z nim o reakcję bohatera.

Na początku pierwszej rundy drużyna dzieli `N+2` run. Nie ma automatycznego
doboru co rundę. Daje to średnio 1,67 runy na osobę przy trzech graczach
i 1,33 przy sześciu. Talia ma dziesięć równolicznych rodzajów; ręka mieści
siedem run. Zapłacone runy trafiają na stos odrzuconych. Efekty Loriana mogą
je odzyskiwać. Brakujący symbol podstawowy można zastąpić dwiema dowolnymi
runami; symbol konkretnego wzmocnienia nadal musi się zgadzać.

Każda karta ma koszt bazowy jednej runy. W danym użyciu wybiera się najwyżej
jedno wzmocnienie, zazwyczaj za kolejną runę. Bez odzyskiwania i innych
źródeł zasobu drużyna ma więc najwyżej `N+2` opłaconych użyć na całą walkę,
a mniej, jeśli wzmacnia moce, płaci zastępczo lub podtrzymuje Bastion.
To silnie premiuje efekty działające przez wiele tur.

**Wniosek:** teraz gracze przede wszystkim wybierają, kto dostanie swoją
jedną moc i czy opłaca się uruchomić długi efekt. Limit siedmiu rzadko
ogranicza zwykły podział; ma znaczenie przy gromadzeniu run przez Loriana.
Hymn, reakcje i kolejne aktywacje Duchowego oręża potrzebują zasobu, którego
po pierwszych dwóch turach może już zabraknąć.

Nie proponuję dodania automatycznego doboru co rundę, ponieważ ustalenie
mówi o doborze wyłącznie w pierwszej. Do przetestowania są dwa świadome
kierunki: zachować jednorazowe, rzadkie moce albo nadać kilku największym
mocom koszt dwóch–trzech run i zapewnić ograniczony, jawny sposób zdobywania
run w walce. Samo podniesienie kosztów przy obecnej puli może sprawić, że
większość graczy nie użyje swojej mocy ani razu.

## Garran — ochrona pozycji i kierowanie drużyną

| Karta | Koszt i budżet | Ocena funkcji i wzmocnień |
| --- | --- | --- |
| Uderzenie tarczą | Kotwica, S | Obrażenia i przesunięcie wyróżniają je od ataku bronią. Dowolna runa za k4 jest słabsza od Błysku za k6 celowo: kupuje elastyczność. Klepsydra dodaje odrębną funkcję hamowania. |
| Drugi oddech | Kielich, S, raz na walkę | Wyraźna samopomoc; nie dubluje ochrony sojuszników. Dodatkowe leczenie i tymczasowe PW odpowiadają innym sytuacjom. |
| Pozycja obronna | Wieża, S | Sam Garran, +2 KP i nieruchomość. Kotwica zapobiega wymuszonemu przerwaniu postawy; tymczasowe PW pomagają przeciw zagrożeniom omijającym KP. |
| Rozkaz: Stać! | Klepsydra, S | Kontrola z dystansu i odebranie reakcji. Zatrzymanie oraz drugi cel są różnymi, sensownymi wzmocnieniami. |
| Osłona towarzysza | Węzeł, R | Przejęcie pojedynczego ataku ma własną rolę. Redukcja k6 za Wieżę i k4 za dowolną runę powtarza czytelny wybór skuteczność/elastyczność. |
| Osłona tarczą | Brama, S | +2 KP sąsiadów, bez ochrony samego Garrana. Tymczasowe PW jednego sojusznika i odporność na przesunięcia pasują do roli. |
| Mowa dowódcy | Korona, S | Usuwa strach i przygotowuje atak sojusznika. Wzmocnienia: drugi uczestnik, wszyscy albo leczenie. Zachowuje rolę dowódcy poza obroną. |
| Żelazny bastion | Klucz, A+S; później runa podtrzymania | Szersza aura +1 KP i odporności na przesunięcia, obejmująca także Garrana. Wyższa KP lub większy promień wzmacniają uruchomienie; późniejsze podtrzymanie zachowuje podstawę +1 KP i 2 pola. Koszt utrzymania silnie konkuruje z całą pulą drużyny. |
| Rozkaz: Kontratak! | Błysk, M+A+S | Wspólne przemieszczenie i atak Garrana oraz sojusznika; sojusznik dodatkowo wydaje reakcję i własną dowolną runę. Większy ruch lub odepchnięcie poprawiają ustawienie, nie tylko obrażenia. |

**Nakładanie:** Pozycja, Osłona tarczą i Bastion należą do jednej rodziny,
ale chronią kolejno siebie, bliskich sojuszników i większą grupę. To dobre
rozróżnienie. Problemem jest opłacalność Bastionu: za większy koszt akcji
i podtrzymanie daje bazowo mniejszą premię KP niż tańsza Osłona. Mowa
dowódcy częściowo spotyka się ze wsparciem Loriana, lecz usuwanie strachu
i jednorazowe przygotowanie ataku odróżniają ją od zarządzania runami.

Propozycje do decyzji:

1. **P1:** zachować trzy karty obronne, ale dać Bastionowi odrębną rolę
   utrzymania terenu, np. stałą strefę chroniącą przejście. Najpierw
   przetestować utrzymanie bez dopłaty przez jedną dodatkową rundę.
2. **P1:** na Kontrataku pokazywać łączny koszt drużyny przed zatwierdzeniem:
   dwie runy, cała tura Garrana i reakcja partnera. Porównać go z dwoma
   zwykłymi atakami, które drużyna mogłaby wykonać bez tej karty.
3. **P2:** zachować obecne wzmocnienia Garrana jako wzorzec: zmieniają cel,
   obszar, bezpieczeństwo albo sposób ustawienia figur, a nie tylko liczbę kości.

## Brakka — wejście w Szał i krótkie wybuchy siły

| Karta | Koszt i budżet | Ocena funkcji i wzmocnień |
| --- | --- | --- |
| Szał | Wieża, S | Długie wzmocnienie obrażeń i wytrzymałości, a zarazem warunek sześciu innych kart. Najważniejszy wybór przydziału. |
| Lekkomyślny atak | Wieża, S | Przewaga zwykłego ataku za ryzyko przyjęcia ataków z przewagą. Nie daje dodatkowego uderzenia; konkuruje z mocami, które je dają. |
| Potężne uderzenie | Klepsydra, S; Szał | Dodatkowy atak z k12; Błysk dokłada drugie k12. Czytelny, bardzo wydajny pojedynczy cios. |
| Z bara | Błysk, S | Przesunięcie bez Szału i bez konieczności trafienia KP. Dłuższe odepchnięcie albo obrażenia dają różne zastosowania. |
| Przyspieszenie | Brama, S; Szał | Mobilność bez ataku w efekcie. Ma własne zastosowanie do odległego celu, ale konkuruje o rzadkie S z zadawaniem obrażeń. |
| Ogłuszający ryk | Korona, S; Szał | Obrażenia obszarowe odróżniają od ciosów. Błysk wzmacnia obrażenia, Klepsydra zatrzymuje po nieudanej obronie. |
| Twarda jak skała | Węzeł, R; Szał | Redukcja po odporności Szału: dobra ochrona przed pojedynczym dużym trafieniem. Inna rola niż reakcje Nimry i Miry zmieniające trafienie. |
| Siekator | Błysk, A+S; Szał | Trzy ataki i elastyczny rozdział celów. Główna karta nacisku w zwarciu. |
| Niepowstrzymana | Oko, M+A+S; Szał | Dojście, dwa różne cele i powalenie. Liczba ataków mniejsza niż Siekatora jest uzasadniona przemieszczeniem i kontrolą. |

**Nakładanie:** Potężne uderzenie, Siekator i Niepowstrzymana mają sens jako
pojedynczy cios, seria w zwarciu oraz natarcie przez pole walki. To nie są
zbędne kopie. Słabszym punktem jest zależność sześciu kart od Szału: gracz
najpierw płaci runę i S za uruchomienie, a potem potrzebuje kolejnej runy
i kolejnej tury, aby skorzystać z większości talii. Przy małej puli część
kart może nigdy nie wejść do gry.

Propozycje do decyzji:

1. **P1:** uczynić wejście w Szał odrębną, łatwą do finansowania decyzją,
   np. raz na walkę bez runy, z zachowaniem kosztu S, albo za dowolną runę.
   To warianty do porównania, nie zmiana zatwierdzona.
2. **P1:** rozważyć Lekkomyślność jako płatny wariant zwykłego ataku,
   zachowujący S, zamiast poświęcania S tylko na przewagę jednego rzutu.
   Ryzyko ataków z przewagą przeciw Brakce pozostaje. Taki wariant
   pomaga przygotować mocny atak w tej samej turze, bez dokładania
   kolejnej samodzielnej karty z dodatkowymi obrażeniami.
3. **P2:** pozostawić Przyspieszenie jako kartę drogi do celu, ale rozważyć
   użycie również poza Szałem. Nie dodawać mu kolejnego pełnego ataku,
   bo zaczęłoby przejmować rolę Niepowstrzymanej.

## Mira — przygotowanie pozycji, skrytość i precyzyjne uderzenie

| Karta | Koszt i budżet | Ocena funkcji i wzmocnień |
| --- | --- | --- |
| Ukryj się | Wieża, S | Osobny test Skradania. Powinien pozostać podstawowym sposobem uzyskania ukrycia. |
| Zasłona dymna | Wieża, S | Po zatwierdzonej zmianie: obszar 3×3 umożliwiający Ukrycie i dający przewagę jego testu, także wrogom. Bez automatycznego ukrycia, przemieszczenia i dawnych wzmocnień. |
| Przeskok przez gardę | Klepsydra, S | Atak i przejście dokładnie za cel, jeśli pole jest wolne. Premia obrażeń jest dodatkiem; główna wartość to przygotowanie pozycji. |
| Unik instynktowny | Błysk, R | Ochrona przez utrudnienie jednego ataku. Dobrze odróżnia się od redukcji obrażeń Brakki i przejmowania ciosu Garrana. |
| Cięcie ścięgna | Brama, S | Atak z własnej flanki i spowolnienie. Kontrola ucieczki, nie kolejna karta czystych obrażeń. |
| Zwód | Korona, S | Wyłącza ataki okazyjne jednego sąsiada przeciw Mirze. Wąski efekt wobec Przeskoku, lecz działa bez udanego ataku i bez wolnego pola za celem. |
| Mistrzyni ostrzy | Węzeł, S | Atak nożem z ukrycia lub flanki, dodatkowe k6. Błysk daje obrażenia natychmiast, Oko krwawienie w czasie — sensowny wybór. |
| Wyrok z cienia | Błysk, A+S | Wymaga jednocześnie ukrycia i własnej flanki; przewaga i dodatkowe 5k6. Wyraźne wynagrodzenie przygotowania, ale warunki są wymagające. |
| Taniec ostrzy | Oko, M+A+S | Ruch i ataki w dwóch różnych wrogów; Atak z cienia tylko raz. Dobra odrębność od pojedynczego Wyroku. |

**Nakładanie:** dotychczasowy Dym zawierał lepsze Ukrycie za ten sam koszt,
więc zwykłe Ukrycie traciło rację bytu. Zatwierdzona zmiana rozwiązuje ten
problem. Cięcie i Mistrzyni ostrzy dzielą wymóg pozycji, lecz oferują
kontrolę albo obrażenia — to użyteczny wybór. Zwód jest bardziej sytuacyjny
niż Przeskok, ale nie jest jego ścisłą kopią.

Propozycje do decyzji:

1. **P1:** zachować czas dymu co najmniej do końca następnej tury Miry
   i jasno pokazywać, że Dym nie oznacza „jesteś ukryta”. Sekwencja
   Dym → Ukrycie zużywa dwa S i co najmniej dwie właściwe runy, zwykle
   w dwóch turach; drużynowa wartość obszaru musi to uzasadniać.
2. **P1:** zamiast dawnego wzmocnienia przewagi proponuję większy obszar
   **albo** dłuższy czas dymu. Nie łączyć obu korzyści w jednym tanim
   wariancie i nie oddawać tej karcie automatycznego Ukrycia.
3. **P2:** jeśli Zwód jest pomijany w testach, rozszerzyć jego rolę na
   pomoc jednemu sojusznikowi w opuszczeniu zwarcia. To odróżni go od
   osobistego skoku Miry bez dodawania kolejnego ataku.

## Dagna — utrzymanie drużyny przy życiu i bezpieczna pozycja

| Karta | Koszt i budżet | Ocena funkcji i wzmocnień |
| --- | --- | --- |
| Święty płomień | Wieża, S | Stożek, k8 blasku, zero po udanej obronie, możliwość trafienia sojuszników. Nisza obszarowa istnieje, ale obrażenia i ryzyko są mało atrakcyjne. |
| Słowo leczenia | Wieża, S | Leczenie z dystansu k4+7, dopłata Kielicha za k6. Dobra interwencja podczas zachowania zwykłego ataku. |
| Błogosławieństwo | Klepsydra, S | Aura k4 do ataków i obron, koncentracja. Wartość rośnie z liczbą chronionych osób i długością walki. |
| Zachowanie życia | Błysk, A+S | Do 40 PW dowolnie rozdzielanych w zasięgu. Bardzo wysoka wydajność jednej runy; nie ma runicznego limitu „raz na walkę”. |
| Aura Boskiej Opieki | Brama, S | Osłabia pobliskich przeciwników, koncentracja. Większy promień albo redukcja obrażeń są dobrymi, odrębnymi wzmocnieniami. |
| Naprowadzający pocisk | Korona, S | Atak dystansowy 2k6 i przygotowanie kolejnego ataku drużyny. Błysk za k6 jest prostym wzrostem siły. |
| Opiekuńczy gest | Węzeł, S | Tymczasowe PW sąsiada, bez leczenia i kumulowania. Przygotowanie do ciosu, nie ratowanie z już odniesionych ran. |
| Pomniejsze przywrócenie | Błysk, S | Usunięcie zatrucia, oślepienia lub głuchoty. Nie dubluje leczenia PW. Użyteczność zależy od obecności tych stanów w scenariuszu. |
| Duchowy oręż | Kielich, A+S; kolejne aktywacje Kielich+S | Oddzielne źródło ataków bez koncentracji. Ciągła opłata dobrze odróżnia je od jednorazowej aury, ale jest droga przy doborze tylko na starcie. |

**Nakładanie:** Słowo, Zachowanie życia, Gest i Przywrócenie to cztery
różne problemy: ranny na odległość, wiele ran, zapobieganie i zły stan.
Nie łączyłbym ich tylko dlatego, że wszystkie „pomagają”. Błogosławieństwo
i Opieka konkurują o koncentrację, więc wybór ofensywnego wsparcia lub
obrony jest rzeczywisty. Święty płomień przegrywa jednak porównanie
wydajności z Wachlarzem Nimry, a w pojedynczy cel z Pociskiem.

Propozycje do decyzji:

1. **P1:** nadać Zachowaniu życia cenę odpowiadającą dużemu ratunkowi:
   limit raz na walkę **albo** większy koszt run. W modelu run dawny
   zasób Boskiej Mocy nie ogranicza dodatkowo tego użycia.
2. **P1:** wyróżnić Święty płomień bezpieczeństwem wobec sojuszników lub
   wąskim efektem oczyszczającym, zamiast kopiować obrażenia Nimry.
3. **P2:** porównać Duchowy oręż ze zwykłym atakiem i Pociskiem przez
   pełne trzy tury. Jeżeli opłata każdej aktywacji czyni go pomijanym,
   rozważyć droższe przywołanie zawierające jedną późniejszą aktywację.

## Lorian — gospodarowanie runami i wsparcie tempa drużyny

| Karta | Koszt i budżet | Ocena funkcji i wzmocnień |
| --- | --- | --- |
| Inspiracja | Wieża, S | k4 do jednego ataku albo obrony innego bohatera. Bez koncentracji i z większym zasięgiem niż aura Dagny, ale wyraźnie mniejszy łączny efekt. |
| Strojenie talii | Wieża, S | Wydaje runę na uruchomienie, a potem wymienia dodatkową własną runę na losową. Ręka maleje o koszt; sama wymiana nie tworzy zasobu. Obecnie wymieniana jest pierwsza pozostała runa. |
| Rozpraszający okrzyk | Klepsydra, R | Redukcja obrażeń sojusznika z dystansu. Osobna, przydatna rola niezależna od własnej kolejki. |
| Wielkie strojenie | Błysk, A+S | Odzysk do trzech najstarszych odrzuconych run, tylko do ręki Loriana. Bardzo podobne do Odzysku energii. |
| Hymn zwycięstwa | Brama, A+S | Koncentracja, dodatkowe S uczestników aury, normalna zapłata każdej mocy. Silne tempo tylko wtedy, gdy drużyna nadal ma runy. |
| Odzysk energii | Korona, S | Do dwóch najstarszych run; Klepsydra dodaje trzecią. Wzmocnienie wydaje jedną dodatkową runę, aby dostać jedną dodatkową — samo nie zwiększa przyrostu liczby run. |
| Luneta optyczna | Błysk, M+A+S | Jeden strzał +2, pominięcie częściowej osłony. Dopłata Bramy daje drugi w ten sam cel. Najwyraźniej zbyt duży koszt akcji względem innych ataków specjalnych. |
| Ostrzał destabilizujący | Oko, S | Dodatkowy atak i utrudnienie następnego ataku celu. Zwykły atak i ruch zostają, więc to często lepszy zakup niż Luneta. |
| Oplatający ostrzał | Kielich, S | Obszar spowolnienia bez obrażeń, również dla sojuszników. Zatrzymanie lub większy obszar sensownie różnicują warianty. |

**Nakładanie:** Odzysk i Wielkie strojenie różnią się głównie liczbą run
oraz poświęceniem A. To bardziej kandydaci na jedną kartę z wariantem niż
na dwie samodzielne tożsamości. Strojenie losowego koloru jest odrębną
funkcją, lecz przy jednej–dwóch runach na osobę potrafi zużyć połowę
zapasu bez pewności poprawy ręki. Inspiracja nie jest kopią Błogosławieństwa,
ale wymaga powodu, by kupować małą jednorazową premię zamiast mocnego ataku.

Propozycje do decyzji:

1. **P1:** połączyć Odzysk i Wielkie strojenie w jeden mechanizm z wariantem
   większego kosztu akcji; zwolnione miejsce przeznaczyć na przekazanie
   odzyskanej runy sojusznikowi. Rozstrzygnąć, czy wolno odzyskać koszt
   właśnie rozpatrywanej karty. Obecnie wolno, także wielokrotnie w walce.
2. **P1:** zmienić Lunetę w przygotowanie zwykłego strzału za `M+S`
   albo pozostawić `M+A+S` i nadać jej rzeczywiście mocny, własny efekt
   snajperski. Nie poprawiać tego wyłącznie jeszcze jednym k6.
3. **P2:** dać Inspiracji przewagę proceduralną, np. świadome użycie
   po zobaczeniu rzutu. W Strojenie docelowo wybierać runę wymienianą
   przez planszę. Na najbliższy test jest już jawny podgląd „odrzucisz X”
   z możliwością anulowania; sam wybór pozostaje automatyczny.

Odzysk nie tworzy run z niczego: przenosi je ze stosu do ręki. Jednak
odzyskiwanie własnego kosztu sprawia, że zasób może krążyć przez kolejne
tury, a nie wyczerpywać się. To zasadnicza decyzja o roli Loriana, nie
drobna korekta liczby na karcie. Hymn dodatkowo przyspiesza ten obieg.

## Nimra — geometria obszarów i kontrola przeciwników

| Karta | Koszt i budżet | Ocena funkcji i wzmocnień |
| --- | --- | --- |
| Lodowy impuls | Wieża, S | Jeden cel, k8 i spowolnienie po nieudanej obronie KON. Funkcja prosta i odrębna od ataków obszarowych. |
| Tarcza | Wieża, R | +3 KP przeciw jednemu atakowi. Konkuruje z ofensywnym wydaniem Wieży; dobry wybór zachowania runy na obronę. |
| Szpilka umysłu | Klepsydra, S | k6 psychicznych i brak reakcji; sukces obrony niweluje wszystko. Niemal zawarta w Załamaniu woli. |
| Wachlarz płomieni | Błysk, S | Stożek 2k6, połowa po obronie. Wzmocnienia: obrażenia albo wyłączenie dwóch pól — dobry wybór siła/bezpieczeństwo. |
| Fala odrzutu | Brama, S | Linia 2k6 i przesunięcie. Dodatkowe obrażenia lub dalsze przesunięcie zachowują odrębną rolę przestrzenną. |
| Lepka matryca | Korona, S | Obszar 2×2 trudnego terenu z próbami powalenia. Bez wymogu koncentracji na karcie; mniej wiążąca kontrola niż Sieć. |
| Mglisty krok | Węzeł, S | Teleport na legalne widoczne pole. Czysta mobilność, bez kopiowania ofensywnego skoku Miry. |
| Sieć | Kotwica, S | Trudny teren i unieruchomienie, koncentracja; wyrwanie kosztuje akcję. Większy bok lub bezpieczne pola dobrze zmieniają wykorzystanie. |
| Piorunowy szlak | Korona, A+S | 4k6 w łańcuchu do trzech istot. Przeskok do najbliższej, również sojusznika, tworzy rzeczywiste ryzyko geometrii. |
| Załamanie woli | Węzeł, S | Jak Szpilka, lecz większy zasięg, połowa obrażeń przy udanej obronie i możliwość drugiego celu lub większych obrażeń. |
| Staza istoty | Wieża, A+S | Odbiera niemal całą turę po nieudanej obronie, koncentracja. Silna kontrola jednego celu, potencjalnie rozstrzygająca walkę z pojedynczym przeciwnikiem. |
| Roztrzaskanie | Kotwica, A+S | 4k8 w obszarze, obrona KON, szczególna skuteczność przeciw konstruktom. Inna geometria i inna obrona niż Piorunowy szlak. |

**Nakładanie:** Szpilka/Załamanie to najbardziej problematyczna para całego
katalogu. Inny symbol zapłaty daje powód użycia słabszej karty przy złej
ręce, ale nie tworzy innego pomysłu na działanie. Matryca/Sieć mają
uzasadnione rozróżnienie: powalenie i brak koncentracji kontra mocniejsze
uwięzienie kosztem koncentracji. Wachlarz/Fala/Piorun/Roztrzaskanie
różnią się kształtem i ryzykiem dla drużyny; nie usuwałbym tych różnic
tylko po to, żeby zmniejszyć liczbę zaklęć.

Propozycje do decyzji:

1. **P1:** zachować Szpilkę jako prosty atak blokujący reakcję, a Załamanie
   zmienić w inny rodzaj kontroli, np. utrudnienie najbliższej obrony MDR.
   Alternatywa: jedna karta z dwoma wariantami i zwolnione miejsce na
   rzeczywiście inną moc. Nie wdrażać obu rozwiązań równocześnie.
2. **P1:** ocenić Stazę i oba duże obszary jako pierwszych kandydatów do
   wyższej ceny runicznej, jeżeli zostanie przyjęte oszczędzanie na wielką
   moc. Dla Stazy jawnie opisać moment końca oraz możliwość kolejnej obrony.
3. **P2:** zacząć z mniejszym aktywnym zestawem, a nadmiarowe karty używać
   jako wymienne elementy rozwoju. Nimra ma 12 kart przy 9 pozostałych
   postaci; pełny katalog nie musi oznaczać 12 naraz na planszetce.

## Erynd — przygotowanie strzału i kontrola szlaków

| Karta | Koszt i budżet | Ocena funkcji i wzmocnień |
| --- | --- | --- |
| Znak łowcy | Wieża, S | Koncentracja, k6 raz we własnej turze przy trafieniu bronią; przeniesienie po pokonaniu celu darmowe. Długi efekt premiuje wczesne użycie. |
| Zwiadowcza mobilność | Wieża, S | Bieg albo bezpieczne opuszczenie zwarcia. Własna rola pozycyjna; świadomie konkuruje ze Znakiem o tę samą runę. |
| Celowanie | Klepsydra, M+S | Przewaga następnego strzału za pozostanie w miejscu. Zwykły atak zostaje. Czytelne przygotowanie zamiast dodatkowego ataku. |
| Strzała kotwicząca | Błysk, S | Atak i zatrzymanie albo spowolnienie; Brama dodaje osobny atak w drugiego sąsiadującego przeciwnika. Wzmocnienie jest znacznie większe niż typowe k6. |
| Strzała odsłaniająca | Brama, S | Atak i −2 KP celu, bez kumulowania; Błysk dodaje k6. Wspiera kolejne ataki całej drużyny. |
| Strzała zakłócająca | Korona, S | Atak, brak reakcji i utrudnienie następnego ataku. Łączy dwie korzyści, podczas gdy podobny Ostrzał Loriana daje jedną. |
| Podwójny strzał | Węzeł, S | Dwa ataki, również w różne cele; Błysk dodaje k6 jednemu trafieniu. Z zachowanym zwykłym atakiem daje trzy strzały w turze. |
| Deszcz strzał | Błysk, A+S | Obszar 3×3, tylko wrogowie; jeden rzut przeciw indywidualnym KP. Inna rola niż seria w dwóch odległych przeciwników. |
| Kolczaste zarośla | Oko, A+S | Duży obszar trudnego terenu, koncentracja; obrażenia również za wymuszony ruch i dla sojuszników. Bardzo dobra współpraca z odepchnięciami drużyny. |

**Nakładanie:** trzy strzały z osłabieniami dają kontrolę ruchu, otwarcie
na obrażenia drużyny i osłabienie ataku — to przydatne rozróżnienie.
Problem nie polega na samym istnieniu trzech kart, lecz na tym, że za
to samo S i jedną runę Podwójny strzał kupuje dwa pełne ataki.
Odpowiedniki u innych bohaterów oddają za serie również A lub M.
Zarośla i Znak konkurują o koncentrację, więc wybór polowania na cel albo
kontrolowania przestrzeni ma realny koszt.

Propozycje do decyzji:

1. **P1:** zmienić Podwójny strzał na `A+S` albo pozostawić `S` i podnieść
   cenę runiczną. Pierwszy wariant jest prostszy: dwa strzały zamiast
   zwykłego ataku i specjalnej, bez trzeciego darmowego ataku obok serii.
2. **P1:** ograniczyć bazową Strzałę zakłócającą do jednego osłabienia,
   przenosząc drugie do wzmocnienia, jeśli testy potwierdzą jej przewagę
   nad wsparciem Loriana. Daje to rzeczywisty wybór sposobu użycia runy.
3. **P2:** zachować Zarośla jako wyróżnik współpracy, ale precyzyjnie
   wypisać na karcie, kiedy odnawia się limit 4k4 na turę istoty. To
   kluczowe przy kilku sojusznikach kolejno przepychających tego samego wroga.

## Współpraca między postaciami i czytelność kosztów

Podobny efekt nie zawsze jest zbędny. Garran przejmuje atak, Mira utrudnia
jego trafienie, Nimra podnosi KP, Brakka zmniejsza przyjęte obrażenia,
a Lorian osłania kogoś z dystansu. To pięć różnych decyzji zależnych od
pozycji, rzutu i rodzaju zagrożenia. Darmowy atak okazyjny musi pozostać
osobnym wyborem obok dostępnych płatnych reakcji.

Dobre zestawienia to odepchnięcie Garrana/Brakki/Nimry w Zarośla Erynda,
Naprowadzający pocisk Dagny przed silnym ciosem oraz dym Miry wspierający
przygotowanie kolejnej tury. Warto zachować takie połączenia, lecz nie
stawiać wymogu posiadania Loriana, aby reszta drużyny mogła regularnie
korzystać z kart. Jego odzysk powinien pomagać w gospodarowaniu zasobem,
a nie być jedynym sposobem podtrzymania mechaniki po pierwszej rundzie.

W bazowych kosztach 66 kart **Wieża pojawia się 14 razy, Błysk 12,
a Klucz raz**, wyłącznie w Bastionie Garrana. Nie jest to pomiar
rzeczywistej częstotliwości użycia: wzmocnienia i zastępowanie kosztu
też zużywają runy. Pokazuje jednak, że równoliczna talia ma bardzo różną
liczbę bezpośrednich zastosowań poszczególnych symboli. Drużyna bez
Garrana nigdy nie wyda Klucza jako dokładnego kosztu bazowego obecnej karty.

Przykład dodatkowego obciążenia pamięci: Ukrycie Miry wybiera przycisk
Rozwidlenia, a płaci się za nie Wieżą. Pula ma dziesięć typów zasobu,
więc nie da się automatycznie utożsamić wszystkich przycisków zdolności
z dziesięcioma kosztami, bez zmiany samego sposobu wybierania kart.
Na teraz karta powinna wyraźnie rozdzielać **„naciśnij [symbol]”** oraz
**„koszt [runa]”**, a podgląd powtarzać oba znaczenia. Dalszy projekt
powinien przypisać dziesięciu zasobom rozpoznawalne zastosowania, np.
ochronę, ruch czy kontrolę, a następnie sprawdzić pokrycie każdej drużyny.
Nie przestawiałbym wszystkich kosztów według numerów przycisków.

## Rozbieżności i kontrole wykonania

To ustalenia z czytania kodu, nie wyniki nowych testów rozgrywki:

- **Błąd walidacji Strojenia znaleziony i poprawiony podczas audytu:** sprawdzenie dwóch run
  przed zapłatą nie wystarcza, gdy brakującą Wieżę zastępują obie. Ręka
  jest wtedy pusta, a wykonanie próbowało pobrać jej pierwszy element.
  Walidacja kontroluje już rękę po wyliczeniu kosztu, przed pobraniem opłaty;
  wykonanie ma też własną kontrolę pustej ręki zamiast indeksowania w ciemno.
- **Automatyczny wybór wymienianej runy:** wykonanie Strojenia bierze
  pierwszą pozostałą runę, a podgląd wskazuje już jej nazwę przed
  zatwierdzeniem. Ręczny wybór pozostaje propozycją dalszego usprawnienia.
- **Zapłata dowolną runą:** algorytm również wybiera pierwszą dostępną
  runę. Zwykły podgląd płatności pokazuje konkretny koszt przed akceptacją;
  taki sam komunikat dodano do podtrzymania Bastionu i opłaty partnera
  Kontrataku. Pokazanie nazwy chroni przed zaskoczeniem, lecz nie zastępuje
  możliwości świadomego wyboru runy do wydania. Podtrzymanie za jedną
  dowolną runę zachowuje podstawowy Bastion (+1 KP, 2 pola), zgodnie
  z makietą. Podgląd Gwiazdy przypomina o tym koszcie.
- **Odzysk własnego kosztu:** obie karty odzysku czytają stos po zapłacie;
  wybierają najstarsze dostępne runy, także koszt, jeśli kolejka do niego
  dojdzie. Wzmocnienie Odzysku zwiększa odzysk o jedną i cenę o jedną.
- **Zachowanie życia:** dawny licznik Boskiej Mocy nie jest dodatkowo
  zużywany dla profilu runicznego. Nie należy zakładać nieopisanej blokady
  „raz na walkę”; jedyny taki limit w obecnym katalogu run dotyczy Drugiego
  oddechu.
- **Czasy trwania:** część efektów nadal otrzymuje czas z dawnego katalogu
  wspólnej many. W profilu run oznaczenie `O` zazwyczaj staje się końcem
  walki, a `T` początkiem następnej tury właściciela, z dodatkowymi
  warunkami zakończenia. Na nowych kartach trzeba użyć pełnego opisu.
  Inspiracja ma w wykonaniu granicę początku kolejnej tury Loriana,
  choć jej tekst mówi tylko o wcześniejszym wykorzystaniu. Strzała
  odsłaniająca również powinna jawnie podawać koniec osłabienia KP.

Przed zmianą liczb proponuję sprawdzić trzy układy: drużyna bez Loriana,
drużyna z Lorianem odzyskującym własne koszty oraz drużyna oparta na
Brakce i przygotowaniu Miry. W każdej zanotować liczbę użyć S i R przez
bohatera, liczbę niewydanych run oraz karty pomijane mimo dostępnej ceny.
To odróżni faktycznie słabą kartę od karty przydatnej tylko w innym
układzie mapy. Niniejszy audyt nie zmienia kosztów ani efektów pozostałych kart.

## Źródła w repozytorium

- [Pełne karty i koszty](../content/print/runes_v01/action_cards.json)
- [Katalog używany przez runtime](../src/dnd_board_game/scenarios/rune_catalog.py)
- [Talia, zapłata i odzysk run](../src/dnd_board_game/rules/runes.py)
- [Budżety S/A/M/R i wycena](../src/dnd_board_game/combat/runes.py)
- [Wykonanie wsparcia Loriana](../src/dnd_board_game/combat/physical_mana.py)
- [Aury i proste zdolności](../src/dnd_board_game/combat/shared_mana_features.py)
- [Synchronizacja czasu efektów](../src/dnd_board_game/combat/shared_mana.py)
- [Cechy klasowe i Zachowanie życia](../src/dnd_board_game/combat/class_features.py)
- [Obsługa dawnych zasobów w profilu runicznym](../src/dnd_board_game/actors/resources.py)
- [Katalog dotychczasowych efektów i wzmocnień](../src/dnd_board_game/rules/shared_mana_catalog.py)

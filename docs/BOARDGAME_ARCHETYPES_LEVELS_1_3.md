# Siedem archetypów — aktualne karty fizycznej many 0.2

Źródło: katalog `rules/physical_mana.py`, profile postaci i skróty aplikacji.
Wygenerowano przez `scripts/generate_mana_character_prints.py`.

Każdy symbol oznacza osobną kartę. Biała: słońce (Plains); niebieska: kropla (Island); czarna: czaszka (Swamp); czerwona: płomień (Mountain); zielona: drzewo (Forest). Cyfra 1 w kółku: dowolny kolor.
A = akcja główna, D = dodatkowa, R = reakcja, MOD = modyfikacja; koszt czaru/ataku płacisz osobno.

PDF-y: `assets/physical_cards/character_sets/physical_mana_v02/` — color, minimal, cards i bw_test.

## Garran — Żelazna Straż — obrona pierwszej linii

PW 28; KP 19; ruch 30 ft.
Start 3; zachowaj do 2; dobierz do 3; pojemność 5.

| Klawisz | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| Q | Drugi oddech | A | Biała + Dowolna | Odzyskaj 1k10+3 PW. Leczenie zajmuje akcję główną. |
| W | Zryw akcji | D | Czerwona | Następny zwykły atak w tej turze otrzymuje +2 do trafienia. Atak nadal kosztuje *. Nie odnawia akcji, nie dodaje ataków ani premii do technik specjalnych. |
| E | Uderzenie tarczą | D | Czerwona + Niebieska | Akcja dodatkowa; wymaga tarczy. Wybierz wroga na sąsiednim polu (5 ft). Rzuć k20 + modyfikator Siły; aplikacja rzuci za cel. Wygrana: 1k6 + modyfikator Siły obrażeń obuchowych i odepchnięcie o jedno wolne pole od Garrana. Zablokowane pole zatrzymuje tylko odepchnięcie. Remis lub przegrana: brak efektu. |
| R | Pozycja obronna | D | Biała | +2 KP do początku następnej własnej tury. Każda zmiana pola kończy efekt. |
| A | Rozkaz: Stać | A | Niebieska + Dowolna | Cel w 60 ft wykonuje obronę Mądrości ST 14. Porażka: brak dobrowolnego ruchu w następnej turze; sukces: połowa ruchu. Naturalne 1 daje również −2 do ataków; naturalne 20 neguje efekt. |
| S | Osłona tarczą | D | Biała + Niebieska | Sąsiadujący sojusznicy mają +2 KP do początku następnej tury Garrana; bez premii dla niego. |
| D | Mowa dowódcy | A | Biała + Dowolna | Garran i słyszący sojusznicy w 30 ft usuwają Strach i zyskują przewagę na pierwszy atak, test albo rzut obronny do końca swojej następnej tury. |
| F | Osłona towarzysza | A | Biała + Niebieska | Wybierz sąsiadującego sojusznika w 5 ft. Pierwszy pojedynczy wrogi atak, czar lub efekt przeciw niemu zostaje w całości przekierowany na Garrana i zużywa osłonę. |

### Pasywy i skaza

- **Styl walki: Obrona:** Gdy nosisz pancerz, masz +1 KP. Aplikacja i karta postaci uwzględniają tę premię.
- **Ulepszony krytyk:** Atak bronią trafia krytycznie, gdy na k20 wypadnie naturalne 19 lub 20. Nie dotyczy testu Siły przy Uderzeniu tarczą.
- **Żelazna linia:** Gdy Garran i sojusznik flankują wspólnego przeciwnika, ten sojusznik ma +1 KP przeciw atakom tego przeciwnika. Premia nie chroni Garrana ani nie działa przeciw innym wrogom.
- **Za tarczą:** Raz w swojej turze, gdy na sąsiednim polu (także po skosie) stoi inny przytomny bohater, możesz zapłacić niebieską maną (N) zamiast jednej wymaganej białej (B). Dotyczy tylko Pozycji obronnej, Osłony tarczą i Osłony towarzysza. Kartę normalnie wydajesz; pozostały koszt się nie zmienia. Przykład: Osłonę tarczą opłacisz dwiema niebieskimi kartami zamiast białej i niebieskiej.

**Skaza — Nieustępliwość:** Gdy po raz pierwszy w swojej turze zaczynasz zwykły ruch, sprawdź sąsiednie pola, także po skosie. Jeśli stoi tam przeciwnik, wydaj 2 dowolne many (*) zamiast 1. To cena całego ruchu w tej turze; kolejne odcinki nie wymagają dopłaty. Odepchnięcia i przemieszczenia ze zdolności nie uruchamiają skazy. Przykład: odpychasz jedynego sąsiadującego wroga tarczą, a potem ruszasz — płacisz 1 manę.

## Brakka — Niszczycielka — obrażenia i wytrzymałość

PW 35; KP 14; ruch 30 ft.
Start 3; zachowaj do 2; dobierz do 3; pojemność 5.

| Klawisz | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| Q | Szał | D | Czerwona | Szał trwa modyfikator KON + modyfikator SIŁ rund (minimum 1), licząc rundę uruchomienia. +2 obrażeń ataków wręcz opartych na SIŁ, przewaga testów i obron SIŁ oraz odporność na obrażenia kłute, cięte i obuchowe. Płacisz raz; nie odnawiaj co turę. Utrata przytomności kończy Szał. |
| W | Lekkomyślny atak | MOD | Czerwona | Następny zwykły atak wręcz oparty na SIŁ w tej turze ma przewagę. Atak jest opłacany dodatkowo przez *. Ataki przeciw Brakce mają przewagę do początku jej następnej tury. Raz we własnej turze; nie jest osobną akcją ani kolejnym atakiem. |
| E | Potężne uderzenie | A | Czerwona + Czerwona | Wymaga Szału. Jeden atak wręcz oparty na SIŁ: +2 do trafienia i +1k12 obrażeń przy trafieniu. Cały atak jest w cenie. |
| R | Z bara | A | Czerwona + Niebieska | Przeciwnik w 5 ft, najwyżej o jeden rozmiar większy. Sporny test Atletyki; remis wygrywa obrońca. Odepchnij o 5 ft i dodatkowe 5 ft za każde pełne 5 punktów przewagi, maksymalnie 30 ft. Przeszkody zatrzymują przesunięcie. |
| A | Przyspieszenie | D | Zielona | W Szale: uruchamia zwykły ruch bez dodatkowej opłaty i podwaja jego bazowy limit w tej turze. Wykonany wcześniej ruch liczy się do nowego limitu. |
| S | Ogłuszający ryk | A | Czerwona + Niebieska + Dowolna | W Szale: stożek 15 ft, tylko wrogowie. Obrona KON, ST 12+KON Brakki. Porażka: 2k6 grzmotu i brak dobrowolnego ruchu do końca najbliższej tury celu; sukces: połowa obrażeń. Naturalne 1 daje też utrudnienie ataków, naturalne 20 neguje obrażenia. |
| AUTO | Twarda jak skała | R | Biała | Wymaga Szału. Po ujawnieniu obrażeń ataku i uwzględnieniu odporności zmniejsz je o 1k12+KON, minimum 0. |
| D | Chwyt | A | Dowolna | Chwyt przeciwnika w 5 ft wymaga wolnej ręki i celu najwyżej o jeden rozmiar większego. Atletyka przeciw Atletyce/Akrobatyce celu; remis wygrywa obrońca. Sukces blokuje ruch celu do uwolnienia. |

### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Obrona bez pancerza:** Bez pancerza twoja KP wynosi 10 + modyfikator Zręczności + modyfikator Kondycji. Możesz korzystać z tarczy.
- **Nieustępliwość półorka:** automatycznie przy pierwszym zejściu do 0 PW pozostawia Brakkę z 1 PW, o ile obrażenia nie zabijają jej natychmiast; 1 użycie na długi odpoczynek.
- **Dzikie ataki:** krytyczny atak bronią wręcz dodaje jedną kość broni.
- **Bitewny rozpęd:** Raz w swojej turze po trafieniu zwykłym atakiem opłaconym czerwoną maną (C) odzyskaj tę kartę z odrzuconych (limit 5 kart). Zwrot nie daje kolejnego ataku. Nie dotyczy dopłaty za Lekkomyślny atak ani kosztów technik.

**Skaza — Bitewny amok:** Na końcu swojej tury, jeśli nadal jesteś w Szale i nie zaatakowałaś wroga ani nie użyłaś przeciw niemu szkodliwej techniki, odrzuć 1 kartę many. Zrób to przed zachowaniem kart na kolejną turę. Nawet nieudany atak pozwala uniknąć tej kary. Jeśli nie masz kart, nic nie tracisz.

## Mira — Specjalistka — infiltracja i precyzyjne obrażenia

PW 21; KP 15; ruch 25 ft.
Start 3; zachowaj do 2; dobierz do 3; pojemność 5.

| Klawisz | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| D | Ukryj się | A | Dowolna | Wykonaj test Skradania przeciw osobnym obserwatorom. Wymagana legalna pozycja ukrycia; aplikacja pokazuje, kto nadal cię wykrywa. Dobrowolne zakończenie ukrycia nie kosztuje many ani akcji. |
| Q | Zasłona dymna | A | Zielona + Czarna | Przemieść Mirę do 15 ft bez ataków okazyjnych i wykonaj nowy test Ukrycia nawet obok wroga. Obserwatorzy mają karę do Percepcji równą połowie modyfikatora ZRC Miry, w dół. Ruch zawarty w cenie. |
| W | Przeskok przez gardę | A | Zielona + Dowolna | Atak wręcz z +2 do trafienia i +2 obrażeń wymaga wolnego pola dokładnie za celem. Po ataku przejdź na to pole; przesunięcie jest w cenie techniki. |
| E | Wykrycie pułapek | A | Dowolna | Wykonaj bojowy test Percepcji, aby wykryć ukryte pułapki w zasięgu obserwacji. Aplikacja podświetla pola wykrytych pułapek; samo wykrycie ich nie rozbraja. |
| R | Cięcie ścięgna | A | Zielona + Niebieska | Atak wręcz z własnej flanki. Trafienie zadaje obrażenia broni i połowi szybkość celu do początku następnej tury Miry. |
| A | Przeszywający atak | A | Zielona + Czerwona | Atak rapierem w przeciwnika stojącego przy sojuszniku. Po raniącym trafieniu osobny atak z +2 do trafienia w drugiego wroga dokładnie jedno pole za pierwszym, na tej samej linii od Miry. Drugie trafienie dosięga tego pola mimo zwykłego zasięgu rapiera; ściana je blokuje. Bez łańcucha dalszych celów. Oba ataki w cenie. |
| S | Mistrzyni ostrzy | A | Zielona + Czarna | Trafienie nożem z ukrycia powoduje krwawienie 1k4 przez najwyżej dwie tury celu; leczenie kończy wcześniej. Bez kumulowania. |
| AUTO | Unik instynktowny | R | Zielona | Reakcja proponowana przed atakiem przeciw ukrytej Mirze. Nadaj temu jednemu atakowi utrudnienie. |

### Pasywy i skaza

- **Mistrzyni ukrycia:** Ukryj się zużywa akcję główną. Wykonujesz jeden test Skradania; aplikacja rzuca osobno na Percepcję każdego wroga. Remis oznacza wykrycie. Nie potrzebujesz osłony, ale sąsiadujący wróg lub blokujący stan uniemożliwia zwykłe ukrycie.
- **Skradanie:** Podczas ukrycia możesz przebyć do 20 ft w turze. Dobrowolne ujawnienie się zwiększa ten limit do 25 ft; odejmij od niego ruch już wykonany.
- **Atak z cienia:** Rapier lub nóż: +1k6 za ukrycie przed celem albo własną flankę; +2k6 za oba. Raz we własnej turze, przy jednym wybranym trafieniu przed obrażeniami. Atak kończy ukrycie. Ukrycie przed celem daje też przewagę ataku.
- **Szczęście niziołka:** ponów naturalną 1 w ataku, teście albo obronie.
- **Ruchomy cel:** Mira ma +2 KP przeciw dystansowym testom ataku bronią i czarem; nie działa przeciw obszarom ani rzutom obronnym.
- **Ekspertyza:** Podwójna premia z biegłości w wybranych umiejętnościach; jest już wliczona w ich modyfikatory.
- **Zwinne dłonie:** Raz w swojej turze, po dobrowolnym przemieszczeniu się o co najmniej jedno pole (5 ft), możesz wymienić 1 kartę z ręki na 1 wybraną kartę rynku. Własną kartę połóż w miejsce zabranej. Nie dobierasz dodatkowych kart. Przymusowe przesunięcie nie uruchamia tej zdolności.

**Skaza — Panika po zdemaskowaniu:** Gdy przeciwnik wykryje cię testem podczas ukrycia, odrzuć 1 kartę many. Karę ponosisz najwyżej raz do początku swojej następnej tury. Ujawnienie się przez własny atak lub dobrowolne zakończenie ukrycia nie powoduje kary. Jeśli nie masz kart, nic nie tracisz.

## Dagna — Uzdrowicielka — leczenie i wzmocnienia

PW 30; KP 16; ruch 25 ft.
Start 3; zachowaj do 2; dobierz do 3; pojemność 5.

| Klawisz | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| Q | Święty płomień | A | Biała | Stożek 15 ft. Cele w obszarze wykonują obronę Zręczności; porażka: 1k8 obrażeń od blasku, sukces: brak obrażeń. |
| W | Słowo leczenia | A | Biała + Dowolna | Przywróć 1k4+7 PW celowi w 60 ft. To pełna premia leczenia; nie doliczaj osobno Ucznia Życia. |
| E | Błogosławieństwo | A | Biała + Niebieska | Aura 10 ft wokół Dagny obejmuje ją i sojuszników: +1k4 do ataków i rzutów obronnych. Koncentracja, do 3 rund. |
| R | Zachowanie życia | A | Biała + Biała + Dowolna | Rozdziel 15 PW między siebie i sojuszników w 30 ft. Każdy cel może odzyskać PW najwyżej do połowy swojego maksimum; niewykorzystane leczenie przepada. |
| A | Aura Boskiej Opieki | A | Biała + Niebieska | Aura 5 ft wokół Dagny: wrogowie w zasięgu mają −2 do ataków i obrażeń. Koncentracja, do 3 rund. |
| S | Naprowadzający pocisk | A | Biała + Czerwona | Cel w 75 ft. Atak czarem; trafienie: 2k6 blasku i przewaga następnego ataku przeciw temu celowi. |
| D | Aura Uzdrawiającej Łaski | A | Biała + Zielona + Dowolna | Aura 10 ft, koncentracja do 3 rund. Dwa pierwsze leczenia w aurze dodają po 1k8 PW. |
| F | Pomniejsze przywrócenie | A | Biała + Zielona | Dotknij celu w 5 ft i usuń jeden negatywny stan z listy dostępnej dla tej zdolności. Aplikacja pokazuje legalne stany i cele. |
| T | Odpędzanie nieumarłych | A | Biała + Niebieska | Nieumarli w obszarze odpędzenia wykonują obronę Mądrości. Porażka: odpędzenie do końca następnej tury Dagny. Obrażenia kończą efekt wcześniej. |
| Z | Duchowa broń | A | Biała + Czerwona + Dowolna | Przywołanie i jeden atak w cenie. Trwa trzy rundy, najwyżej jedna broń; dalsze aktywacje kosztują akcję dodatkową i jedną białą manę, każda zawiera ruch broni do 20 stóp i jeden atak. Brak osobnej darmowej tury przywołania. |

### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Krasnoludzki ruch:** Ciężki pancerz nie zmniejsza szybkości Dagny z powodu niewystarczającej Siły.
- **Krok ratowniczki:** Raz na turę Dagny, po leczeniu lub zdjęciu negatywnego stanu innego sojusznika w 10 stopach: ruch 5 stóp bez kosztu ruchu, reakcji i ataków okazyjnych.
- **Krasnoludzka wytrzymałość:** +1 maksymalnego PW na każdy poziom.
- **Krasnoludzka odporność:** przewaga przeciw truciźnie i odporność na obrażenia od trucizny.
- **Uczeń Życia:** Raz w swojej turze, gdy zdolność przywraca PW innemu bohaterowi, możesz zapłacić zieloną maną (Z) zamiast jednej wymaganej białej (B). Kartę normalnie wydajesz. Własne leczenie i samo uruchomienie aury nie pozwalają na tę zamianę.

**Skaza — Nikogo nie zostawiam:** Jeśli w odległości do 30 ft leży żywy bohater z 0 PW, pierwsze działanie ofensywne w twojej turze kosztuje o 1 dowolną manę (*) więcej. Sprawdź ten warunek przy deklaracji działania. Leczenie, ratowanie, osłony i ruch nie wymagają dopłaty.

## Lorian — Bard — zarządzanie maną, kusza i kontrola

PW 24; KP 13; ruch 30 ft.
Start 3; zachowaj do 3; dobierz do 3; pojemność 6.

| Klawisz | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| Q | Inspiracja barw | D | Biała | Jeden inny bohater w 30 stopach może przy opłaceniu jednego działania do początku następnej tury Loriana potraktować jedną posiadaną kartę jako dowolny kolor. Jedna niewykorzystana Inspiracja na odbiorcę; bez k6 i bez tworzenia karty. |
| R | Strojenie rynku | D | Niebieska | Wymień do dwóch własnych kart z taką samą liczbą wybranych kart rynku. Jeden jednoczesny zestaw wymian 1:1, bez dobierania. |
| F | Transmutacja | D | Czarna | Do końca tej tury dwie wskazane posiadane karty możesz opłacić jako dowolne kolory. Każda nadal jest wydawana i nie może opłacić dwóch symboli. Nie działa na kartę zużytą do uruchomienia Transmutacji. |
| Z | Przerzut energii | D | Zielona | Przekaż do dwóch własnych kart jednemu innemu bohaterowi w 30 stopach. Nie dobiera on nowych. Obowiązuje pojemność odbiorcy. |
| X | Rezerwacja | D | Niebieska | Zabierz jedną kartę rynku do swojego depozytu, wliczanego do rezerwy i pojemności. Nie można jej wydać, oddać ani wymienić przed początkiem następnej własnej tury; wolno ją odrzucić. Maksymalnie jeden depozyt, na następnej turze staje się zwykłą kartą. Rynek uzupełnia się na końcu obecnej tury. |
| C | Odzysk energii | A | Biała + Niebieska | Wybierz do trzech kart obecnych na odrzuconych przed opłaceniem zdolności i rozdaj je sobie lub bohaterom w 30 stopach, najwyżej dwie jednemu odbiorcy. Nie wolno odzyskać właśnie wydanych kart białej i niebieskiej many; nie zwiększa pojemności. Brak odpowiednich kart oznacza mniejszy odzysk. |
| V | Nowe rozdanie | A | Niebieska + Dowolna | Odrzuć do trzech kart rynku, uzupełnij go z talii. Następnie każdy przytomny bohater w 30 stopach, w tym Lorian, może raz wymienić własną kartę z rynkiem, w kolejności inicjatywy. Nie ma kolejnego doboru pomiędzy wymianami. |
| AUTO | Awaryjna pożyczka | R | Biała | Gdy inny bohater w 30 stopach deklaruje działanie, przed jego opłaceniem przekaż mu jedną dodatkową własną kartę. Biała mana za reakcję jest osobnym kosztem; łącznie Lorian traci dwie karty. Bez zwrotu/długu mimo nazwy. Nie otwiera dodatkowej akcji ani nie zwiększa już zadeklarowanej serii ataków. |
| W | Luneta optyczna | A | Zielona + Niebieska + Dowolna | Przed ruchem wykonaj dwa osobne strzały w jeden cel, każdy z +2 do trafienia i ignorowaniem częściowej osłony; całkowita osłona blokuje. Zużywa cały ruch. Dwa strzały są już opłacone. |
| E | Ostrzał destabilizujący | A | Zielona + Czarna | Jeden strzał w 45 stopach. Trafienie: utrudnienie pierwszego ataku i obron MDR celu do początku następnej tury Loriana. |
| A | Oplatający ostrzał | A | Zielona + Niebieska | Obszar 3×3 w 45 stopach, także sojusznicy. ZRC ST 14: porażka blokuje ruch, sukces połowi do początku następnej tury Loriana. Bez obrażeń. |
| S | Podszept paniki | A | Czarna + Niebieska | Cel w 45 stopach, MDR ST 14: 2k6 psychicznych i ruch do 15 stóp od Loriana; sukces połowa bez ruchu. |
| D | Fala gromu | A | Czerwona + Niebieska | Sześcian 15 stóp, także sojusznicy. KON ST 14: 2k8 grzmotu i odepchnięcie o 10 stóp; sukces połowa bez odepchnięcia. |
| AUTO | Rozpraszający okrzyk | R | Biała | Gdy bohater w 30 stopach otrzymuje obrażenia od pojedynczego ataku, zmniejsz je o 1k6+2, minimum 0. |

### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Feyowskie pochodzenie:** przewaga przeciw zauroczeniu i odporność na magiczny sen.
- **Obycie i targowanie:** +2 do każdego pozabojowego testu Charyzmy. Nie tworzy nowych nagród ani możliwości fabularnych.
- **Improwizacja:** raz na NPC przerzuć nieudany pozabojowy test Charyzmy przed konsekwencjami; drugi wynik jest ostateczny. Zużycie jest zapisywane.
- **Rezerwuar i Zgranie:** Pojemność 6 kart. Na koniec tury zachowaj do 3 niewydanych kart i dobierz do 3 nowych; walkę zaczynasz z 3. Raz w swojej turze, przed doborem, możesz wymienić 1 kartę z ręki na 1 kartę innego bohatera w odległości do 30 ft. W grze solo wymieniasz ją z rynkiem. Wymiana nie daje dodatkowej karty.

**Skaza — Potrzeba publiczności:** Jeśli nie ma innego przytomnego bohatera w odległości do 10 ft, pierwsza zdolność specjalna kosztuje o 1 dowolną manę (*) więcej. Dopłata może dotyczyć też reakcji; ponosisz ją najwyżej raz do początku swojej następnej tury. Zwykły atak, ruch, przedmioty i pasywy nie wymagają dopłaty. W grze solo skaza nie działa.

## Nimra — Kontrolerka magiczna — teren i wiedza

PW 20; KP 12; ruch 25 ft.
Start 3; zachowaj do 2; dobierz do 3; pojemność 5.

| Klawisz | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| Q | Lodowy impuls | A | Niebieska | Cel w 50 ft, obrona KON przeciw ST czarów Nimry. Porażka: 1k8 zimna i −10 ft szybkości do początku następnej tury Nimry; sukces: brak efektu. |
| W | Kwasowy rozprysk | A | Czerwona | Wskaż środek w 40 ft, promień 5 ft, także sojusznicy. Obrona ZRC przeciw ST Nimry: porażka 1k6 kwasu, sukces bez obrażeń. |
| E | Szpilka umysłu | A | Czarna | Cel w 45 ft, obrona MDR przeciw ST Nimry. Porażka: 1k6 psychicznych i brak reakcji do początku następnej tury Nimry; sukces: brak efektu. |
| R | Wachlarz płomieni | A | Czerwona + Dowolna | Stożek 15 ft, także sojusznicy. Obrona ZRC przeciw ST Nimry: porażka 2k6 ognia, sukces połowa obrażeń. |
| A | Fala odrzutu | A | Niebieska + Czerwona | Linia 30×5 ft, także sojusznicy. Obrona SIŁ przeciw ST Nimry: porażka 2k6 mocy i odepchnięcie o 5 ft; sukces połowa obrażeń bez odepchnięcia. |
| S | Lepka matryca | A | Zielona + Niebieska | Środek w 50 ft, kwadrat 10×10 ft. Trudny teren przez 3 rundy, bez koncentracji. Przy rzuceniu, wejściu lub początku tury istota wykonuje obronę ZRC przeciw ST Nimry; porażka powala. |
| J | Mglisty krok | D | Niebieska + Zielona | Teleport 30 stóp, bez dodatkowej opłaty ruchu. |
| D | Sen | A | Czarna + Niebieska + Dowolna | Środek w 50 ft, promień 15 ft. Rzuć 5k8; pula usypia cele od najniższych aktualnych PW. Bez obrony; nie działa na nieumarłych i odpornych na zauroczenie. Sen do końca następnej tury Nimry, obrażeń lub obudzenia akcją. Bez koncentracji. |
| F | Mgła | A | Niebieska + Dowolna | Środek w 50 ft, promień 15 ft. Mgła silnie przesłania obszar i ogranicza widoczność wszystkim istotom. Koncentracja, do 3 rund. |
| Z | Sieć | A | Zielona + Niebieska + Dowolna | Środek w 50 ft, kwadrat 20×20 ft. Trudny teren; obrona ZRC przeciw ST Nimry może unieruchomić. Uwolnienie: akcja i test SIŁ przeciw ST czaru. Koncentracja, do 3 rund. |
| X | Piorunowy szlak | A | Czerwona + Niebieska + Dowolna | Cel w 60 ft: obrona ZRC przeciw ST Nimry, 3k6 błyskawic przy porażce, połowa przy sukcesie. Następnie przeskok na jedną istotę w 15 ft od celu; aplikacja wskazuje najbliższą istotę, także sojusznika; przy remisie wybiera wroga. Przeskok ma osobną obronę i te same obrażenia. |
| C | Załamanie woli | A | Czarna + Niebieska | Środek w 50 ft, promień 10 ft, także sojusznicy. Obrona MDR przeciw ST Nimry: porażka 2k6 psychicznych i brak reakcji do początku następnej tury Nimry; sukces połowa obrażeń. |
| V | Staza istoty | A | Niebieska + Czarna + Dowolna | Wróg w 50 ft wykonuje obronę MDR przeciw ST Nimry. Porażka blokuje ruch i akcję ruchu; powtarza obronę na końcu swoich tur. Koncentracja, do 3 rund. |
| K | Roztrzaskanie | A | Czerwona + Czerwona + Dowolna | Środek w 60 ft, promień 10 ft, także sojusznicy. Obrona KON przeciw ST Nimry: porażka 3k8 grzmotu, sukces połowa obrażeń. Konstrukty mają utrudnienie obrony. |
| AUTO | Tarcza | R | Biała | Reakcja na atak przeciw Nimrze: +3 KP wyłącznie przeciw temu atakowi i ponowna ocena trafienia. |
| T | Rzeźbienie pola | MOD | Niebieska | Wyłącz do 4 wskazanych pól z obszaru następnego czaru. Modyfikuje obszar, nie czar pojedynczego celu; koszt czaru płacisz osobno. |
| Y | Odległy czar | MOD | Zielona | Zwiększ zasięg następnego zgodnego czaru o 15 ft, najwyżej do 75 ft. Nie działa na Tarczę ani Mglisty krok. Koszt czaru płacisz osobno. |
| U | Przeciążony czar | MOD | Czerwona | Jedna dodatkowa bazowa kość obrażeń. To inna zdolność niż ogólne przeciążenie koloru. |
| G | Wymuszony splot | MOD | Czarna + Czarna | Jeden cel ma utrudnienie pierwszej obrony; przez limit czar bazowy może kosztować najwyżej dwie karty. |
| H | Transmutacja energii | MOD | Czarna | Zmień kwas, zimno, ogień, błyskawice lub grzmot następnego czaru na inny typ z tej listy. Nie zmienia obrażeń psychicznych ani mocy. Koszt czaru płacisz osobno. |

### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Gnomia przebiegłość:** przewaga w obronach INT, MĄD i CHA przeciw magii.
- **Katalog niemożliwego:** wszystkie czary z talii są stale dostępne; Nimra nie przygotowuje ich po odpoczynku.
- **Alchemia barw:** Raz w swojej turze, płacąc za czar lub Metamagię, możesz użyć jednej niebieskiej many (N) jako dowolnego koloru. Kartę normalnie wydajesz; opłaca tylko jeden symbol kosztu.

**Skaza — Echo magicznego wycieku:** Zapamiętaj czary i Metamagię użyte we własnej turze. Jeśli w następnej turze powtórzysz któryś z nich, przy pierwszym powtórzeniu dopłać 1 dowolną manę (*). Łącznie płacisz najwyżej raz w turze, nawet jeśli powtórzysz i czar, i Metamagię. Reakcje poza własną turą nie liczą się do Echa. Pominięta tura usuwa zapamiętane wybory.

## Erynd — Zwiadowca — tropienie i ostrzał

PW 25; KP 16; ruch 30 ft.
Start 3; zachowaj do 2; dobierz do 3; pojemność 5.

| Klawisz | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| Q | Znak łowcy | D | Zielona | +1k6 raz na własną turę przy trafieniu oznaczonego celu bronią; koncentracja, trzy rundy. Przeniesienie po pokonaniu celu bez many i akcji. Ograniczenie raz na turę zastępuje dodawanie do każdego trafienia. |
| W | Zwiadowcza mobilność | D | Zielona | Sprint albo Odstąpienie; obejmuje opłatę za zwykły ruch w tej turze. Sprint zwiększa limit, Odstąpienie znosi ataki okazyjne. Wcześniejszy ruch liczy się do limitu. |
| E | Celowanie | D | Zielona | Przed ruchem poświęć cały jego limit: następny atak łukiem w tej turze ma przewagę. Atak opłacasz osobno. |
| R | Strzała kotwicząca | A | Zielona + Niebieska | Atak długim łukiem. Trafiony cel wykonuje obronę Siły ST 14: porażka blokuje ruch, sukces połowi ruch do początku następnej tury Erynda. |
| A | Strzała odsłaniająca | A | Zielona + Czarna | Atak długim łukiem. Trafienie obniża KP celu o 2 do początku następnej tury Erynda. Efekt nie kumuluje się. |
| S | Strzała zakłócająca | A | Zielona + Niebieska | Atak długim łukiem. Trafienie zadaje obrażenia broni, odbiera reakcje i daje utrudnienie następnego ataku celu, najpóźniej do końca jego następnej tury. |
| D | Podwójny strzał | A | Zielona + Czerwona + Dowolna | Dwa osobne strzały długim łukiem, każdy z +2 do trafienia, z możliwością różnych celów. Jedno wybrane trafienie dodaje +1k6 obrażeń tej techniki. Znak i Pierwsza krew również najwyżej raz w całej turze. Oba ataki są w cenie; obrażenia, krytyki i reakcje rozstrzygane osobno. |
| F | Mglisty krok | D | Niebieska + Zielona | Teleport 30 stóp bez dodatkowej opłaty ruchu. |
| Z | Kolczaste zarośla | A | Zielona + Zielona + Dowolna | Środek w 50 ft, promień 20 ft. Trudny teren: każde 5 ft ruchu w obszarze zadaje 2k4 obrażeń kłutych. Dotyczy również sojuszników. Koncentracja, do 3 rund. |

### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Styl walki: Łucznictwo:** +2 do dystansowych ataków bronią; premia jest już wliczona w atak na arkuszu.
- **Ekspertyza zwiadowcy:** podwójna biegłość w Skradaniu i Sztuce przetrwania.
- **Pierwsza krew:** Raz we własnej turze trafienie długim łukiem w cel z pełnymi PW dodaje 1k6 obrażeń. Wybierz trafienie przed rzutem obrażeń.
- **Czujność zwiadowcy:** +2 do inicjatywy i testów wykrywania ukrytych przeciwników; premia nie dotyczy pułapek.
- **Feyowskie pochodzenie:** przewaga przeciw zauroczeniu i odporność na magiczny sen.
- **Czytanie prądów:** Na końcu swojej tury, po doborze many i przed uzupełnieniem rynku, możesz obejrzeć 2 wierzchnie karty talii i odłożyć je na wierzch w wybranej kolejności. Jeśli została tylko 1 karta, oglądasz tylko ją. Nie tasuj odrzuconych na potrzeby tego podglądu.

**Skaza — Trauma bratobójczego strzału:** Pierwszy w twojej turze atak łukiem w cel sąsiadujący z innym przytomnym bohaterem kosztuje o 1 dowolną manę (*) więcej. Sąsiedztwo obejmuje też pola po skosie. Ataki nożem nie wymagają dopłaty. NPC i przywołane istoty stojące przy celu nie uruchamiają skazy.

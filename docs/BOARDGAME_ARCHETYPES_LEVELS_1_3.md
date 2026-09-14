# Siedem archetypów — aktualne karty wspólnej many 0.3

Źródło: katalog `rules/physical_mana.py`, profile postaci i stałe oznaczenia panelu areny.
Wygenerowano przez `scripts/generate_mana_character_prints.py`.

Każdy symbol oznacza osobną kartę. Biała: słońce (Plains); niebieska: kropla (Island); czarna: czaszka (Swamp); czerwona: płomień (Mountain); zielona: drzewo (Forest). Cyfra 1 w kółku: dowolny kolor.
A = akcja główna, D = dodatkowa, R = reakcja, MOD = modyfikacja. Koszt obejmuje opisane ataki. T = początek następnej tury źródła; O = odświeżenie talii. Dolny pasek mapy wyłączony; symbole pozostają wydrukowane.

PDF-y: `assets/physical_cards/character_sets/physical_mana_v02/` — color, minimal, cards i bw_test.

## Garran — Żelazna Straż — obrona pierwszej linii

PW 28; KP 19; ruch 30 ft.
Wspólna talia 25 kart; rynek 5; brak prywatnej ręki. Płatność przed efektem, dobór na końcu tury.

| Symbol panelu | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| Rozwidlenie | Drugi oddech | A | Dowolna | Odzyskaj 1k10 + KON PW. |
| Trójząb | Pozycja obronna | D | Biała | +2 KP; każda zmiana pola kończy postawę. Do odświeżenia talii (O). |
| Brama | Rozkaz: Stać! | A | Niebieska | Wróg w 60 ft: obrona MDR. Porażka połowi ruch i odbiera reakcje. Do początku następnej tury źródła (T). |
| Błysk | Osłona towarzysza | R | Biała | Przed rozstrzygnięciem pojedynczego ataku na sąsiadującego sojusznika przejmij go na siebie. Nie obejmuje obszarów. |
| Klepsydra | Uderzenie tarczą | D | Niebieska + Czerwona | Sporny test SIŁ: twój fizyczny k20 + SIŁ, automatyczny rzut wroga. Remis wygrywa obrońca. Wygrana: 1k6 + SIŁ i odepchnięcie o pole. Czerwona: +1k6 obrażeń (maks. 2). |
| Romb | Osłona tarczą | D | Biała + Dowolna | Sąsiadujący sojusznicy otrzymują +2 KP; bez premii dla Garrana. Do początku następnej tury źródła (T). Biała: 5 tymczasowych PW jednemu sojusznikowi; różne cele (maks. 2). |
| Hak | Mowa dowódcy | A | Biała + Dowolna | Garran i sojusznicy w 15 ft usuwają Strach i mają przewagę pierwszego ataku. Do początku następnej tury źródła (T). Biała: wybrany uczestnik odzyskuje 1k6 PW (maks. 2). |
| Wieża | Żelazny bastion | A | Biała + Biała + Biała + Niebieska | Aura 10 ft: Garran i sojusznicy w niej mają premię do KP równą modyfikatorowi Siły Garrana oraz ochronę przed przymusowym przesunięciem. Do odświeżenia talii (O). |
| Oko | Rozkaz: Kontratak! | A | Biała + Biała + Czerwona + Czerwona | Garran i jeden sojusznik w 15 ft przemieszczają się do 10 ft bez ataków okazyjnych i wykonują po jednym ataku bronią. Sojusznik zużywa reakcję. |

### Eksploracja — NPC i obiekty

- **Autorytet (NPC):** Siła, bazowy test +6. Przejmij inicjatywę zdecydowaną obecnością i odpowiedzialnością za sytuację.
- **Zabezpieczenie (obiekt):** Kondycja, bazowy test +4. Utrzymaj konstrukcję stabilną i bezpiecznie zwolnij naprężenia.

Dobieranie do 21: pas przed następną ofertą. Przekroczenie daje utrudnienie końcowego rzutu (2k20, niższy wynik), bez premii za karty.


### Pasywy i skaza

- **Styl walki: Obrona:** Gdy nosisz pancerz, masz +1 KP. Aplikacja i karta postaci uwzględniają tę premię.
- **Ulepszony krytyk:** Atak bronią trafia krytycznie, gdy na k20 wypadnie naturalne 19 lub 20. Nie dotyczy testu Siły przy Uderzeniu tarczą.
- **Żelazna linia:** Gdy Garran i sojusznik flankują wspólnego przeciwnika, ten sojusznik ma +1 KP przeciw atakom tego przeciwnika. Premia nie chroni Garrana ani nie działa przeciw innym wrogom.
- **Za tarczą:** Raz we własnej turze przy przytomnym sąsiadującym bohaterze użyj niebieskiej zamiast jednej białej w koszcie bazowym Pozycji obronnej, Osłony tarczą lub Osłony towarzysza. Nie zastępuje podbić ani ultów.

**Skaza — Nieustępliwość:** Rozpoczęcie własnej tury przy wrogu, także po skosie, zmniejsza limit zwykłego ruchu o połowę do końca tej tury. Późniejsze usunięcie wroga nie znosi kary.

## Brakka — Niszczycielka — obrażenia i wytrzymałość

PW 35; KP 14; ruch 30 ft.
Wspólna talia 25 kart; rynek 5; brak prywatnej ręki. Płatność przed efektem, dobór na końcu tury.

| Symbol panelu | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| Rozwidlenie | Szał | D | Czerwona | +2 obrażeń ataków wręcz opartych na SIŁ, przewaga testów i obron SIŁ, odporność na kłute, cięte i obuchowe. Nieprzytomność albo tura bez ofensywy kończy Szał. Do odświeżenia talii (O). |
| Wieża | Lekkomyślny atak | MOD | Czerwona | Przewaga następnego zwykłego ataku wręcz opartego na SIŁ w tej turze. Wrogowie mają przewagę ataków przeciw Brakce. Do początku następnej tury źródła (T). |
| Brama | Przyspieszenie | D | Zielona | W Szale podwaja limit ruchu bieżącej tury. Wcześniejszy ruch wlicza się do limitu. |
| Hak | Twarda jak skała | R | Dowolna | W Szale: po odporności zmniejsz otrzymane obrażenia o 1k12 + KON, minimum zero. |
| Klepsydra | Potężne uderzenie | A | Czerwona + Dowolna | W Szale wykonaj jeden atak bronią z dodatkowym 1k12 obrażeń. Czerwona: +1k12 obrażeń (maks. 2). |
| Trójząb | Z bara | A | Czerwona + Dowolna | Sporny test Atletyki przeciw sąsiadującemu wrogowi, maksymalnie o rozmiar większemu. Wygrana odpycha o pole; remis broni cel. Niebieska: dodatkowe pole odepchnięcia (maks. 2). Czerwona: 1k6 obrażeń (maks. 2). |
| Romb | Ogłuszający ryk | A | Czerwona + Niebieska | W Szale: wrogowie w stożku 15 ft, obrona KON; 1k6 grzmotu, sukces daje połowę. Czerwona: +1k6 obrażeń (maks. 2). Niebieska: przy porażce brak ruchu (T) (maks. 1). |
| Błysk | Siekator | A | Czerwona + Czerwona + Czerwona + Czerwona | W Szale wykonaj trzy osobne ataki wręcz, rozdzielane między dostępnych wrogów. |
| Oko | Niepowstrzymana | A | Czerwona + Czerwona + Czerwona + Zielona | W Szale: ruch do 20 ft bez ataków okazyjnych i trudnego terenu, potem ataki w dwóch różnych wrogów. Trafieni bronią się SIŁ przed powaleniem (T lub do wstania). |

### Eksploracja — NPC i obiekty

- **Zastraszanie (NPC):** Kondycja, bazowy test +5. Wytrzymaj nacisk i pokaż, że nie ustąpisz. Test Kondycji, nie rzut obronny.
- **Forsowanie (obiekt):** Siła, bazowy test +6. Pokonaj opór siłą: podnieś, wyważ lub rozerwij blokadę.

Dobieranie do 21: pas przed następną ofertą. Przekroczenie daje utrudnienie końcowego rzutu (2k20, niższy wynik), bez premii za karty.


### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Obrona bez pancerza:** Bez pancerza twoja KP wynosi 10 + modyfikator Zręczności + modyfikator Kondycji. Możesz korzystać z tarczy.
- **Nieustępliwość półorka:** automatycznie przy pierwszym zejściu do 0 PW pozostawia Brakkę z 1 PW, o ile obrażenia nie zabijają jej natychmiast; 1 użycie na długi odpoczynek.
- **Dzikie ataki:** krytyczny atak bronią wręcz dodaje jedną kość broni.
- **Bitewny rozpęd:** Raz we własnej turze trafienie zwykłym atakiem w Szale daje 2 tymczasowe PW do początku następnej własnej tury.

**Skaza — Bitewny amok:** Tura bez ataku lub szkodliwej techniki przeciw wrogowi kończy Szał. Nieudany atak wystarcza, by utrzymać Szał.

## Mira — Specjalistka — infiltracja i precyzyjne obrażenia

PW 21; KP 15; ruch 25 ft.
Wspólna talia 25 kart; rynek 5; brak prywatnej ręki. Płatność przed efektem, dobór na końcu tury.

| Symbol panelu | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| Rozwidlenie | Ukryj się | D | Dowolna | Test Skradania w legalnej pozycji. Wykrycie, atak lub dobrowolne ujawnienie kończy ukrycie. Do odświeżenia talii (O). |
| Trójząb | Unik instynktowny | R | Zielona | Nadaj utrudnienie jednemu atakowi przeciw Mirze. Nie wymaga rzutu Miry. |
| Romb | Zwód | D | Czarna | Sąsiadujący wróg nie może wykonywać ataków okazyjnych przeciw Mirze. Do początku następnej tury źródła (T). |
| Brama | Cięcie ścięgna | A | Zielona + Dowolna | Atak wręcz z własnej flanki. Trafienie zadaje obrażenia broni i połowi ruch celu. Do początku następnej tury źródła (T). |
| Wieża | Zasłona dymna | D | Zielona + Dowolna | Ruch do 10 ft bez ataków okazyjnych i próba ukrycia, także po rozpoczęciu obok wroga. Ukrycie kończą atak lub wykrycie. Do odświeżenia talii (O). Zielona: +5 ft ruchu (maks. 2). Czarna: przewaga testu ukrycia (maks. 1). |
| Klepsydra | Przeskok przez gardę | A | Zielona + Dowolna | Atak wręcz i przejście na wolne pole dokładnie za celem. Czerwona: +1k6 obrażeń (maks. 2). |
| Hak | Mistrzyni ostrzy | A | Zielona + Czarna | Atak nożem z ukrycia albo własnej flanki, dodatkowe 1k6 obrażeń. Czerwona: +1k6 obrażeń (maks. 2). Czarna: krwawienie 1k4 na początku tury celu (O); leczenie kończy, bez kumulowania (maks. 1). |
| Błysk | Wyrok z cienia | A | Czarna + Czarna + Czarna + Czarna | Wymaga ukrycia przed celem i własnej flanki. Jeden atak z przewagą i dodatkowym 5k6 obrażeń. |
| Oko | Taniec ostrzy | A | Zielona + Zielona + Czarna + Czarna | Ruch do 15 ft bez ataków okazyjnych i dwa ataki w różnych wrogów po drodze. Atak z cienia najwyżej raz. |

### Eksploracja — NPC i obiekty

- **Blef (NPC):** Inteligencja, bazowy test +4. Zbuduj sprytne, spójne kłamstwo lub pozór.
- **Manipulacja (obiekt):** Zręczność, bazowy test +6. Precyzyjnie zwolnij zamek, zatrzask lub drobny mechanizm przy użyciu narzędzi.

Dobieranie do 21: pas przed następną ofertą. Przekroczenie daje utrudnienie końcowego rzutu (2k20, niższy wynik), bez premii za karty.


### Pasywy i skaza

- **Mistrzyni ukrycia:** Ukryj się zużywa akcję dodatkową. Wykonujesz jeden test Skradania; aplikacja rzuca osobno na Percepcję każdego wroga. Remis oznacza wykrycie. Nie potrzebujesz osłony, ale sąsiadujący wróg lub blokujący stan uniemożliwia zwykłe ukrycie.
- **Skradanie:** Podczas ukrycia możesz przebyć do 20 ft w turze. Dobrowolne ujawnienie się zwiększa ten limit do 25 ft; odejmij od niego ruch już wykonany.
- **Atak z cienia:** Rapier lub nóż: +1k6 za ukrycie przed celem albo własną flankę; +2k6 za oba. Raz we własnej turze, przy jednym wybranym trafieniu przed obrażeniami. Atak kończy ukrycie. Ukrycie przed celem daje też przewagę ataku.
- **Szczęście niziołka:** ponów naturalną 1 w ataku, teście albo obronie.
- **Ruchomy cel:** Mira ma +2 KP przeciw dystansowym testom ataku bronią i czarem; nie działa przeciw obszarom ani rzutom obronnym.
- **Ekspertyza:** Podwójna premia z biegłości w wybranych umiejętnościach; jest już wliczona w ich modyfikatory.
- **Zwinne dłonie:** Raz we własnej turze po trafieniu nożem możesz przemieścić się o pole bez ataków okazyjnych i bez kosztu zwykłego ruchu.

**Skaza — Ostrożność w ukryciu:** Podczas ukrycia masz utrudnienie wszystkich rzutów obronnych oraz testów wykonywanych w ramach reakcji. Efekty bez rzutu, w tym Unik instynktowny, nie otrzymują kary.

## Dagna — Uzdrowicielka — leczenie i wzmocnienia

PW 30; KP 16; ruch 25 ft.
Wspólna talia 25 kart; rynek 5; brak prywatnej ręki. Płatność przed efektem, dobór na końcu tury.

| Symbol panelu | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| Rozwidlenie | Święty płomień | A | Biała | Stożek 15 ft, także sojusznicy. Obrona ZRC: porażka 1k8 blasku, sukces bez obrażeń. |
| Klepsydra | Błogosławieństwo | A | Biała + Niebieska | Aura 10 ft: Dagna i sojusznicy mają +1k4 do ataków i obron. Koncentracja. Do odświeżenia talii (O). |
| Błysk | Pomniejsze przywrócenie | A | Biała + Dowolna | Dotykiem usuń jeden dostępny stan: zatrucie, oślepienie lub głuchotę. |
| Hak | Opiekuńczy gest | D | Dowolna | Sąsiadujący sojusznik otrzymuje 1k4 + MDR tymczasowych PW. Nie leczy ran; tymczasowe PW nie kumulują się. Do początku następnej tury źródła (T). |
| Wieża | Słowo leczenia | A | Biała + Dowolna | Cel w 60 ft odzyskuje 1k4 + 7 PW. Biała: +1k6 leczenia (maks. 3). |
| Brama | Aura Boskiej Opieki | A | Biała + Dowolna | Wrogowie w 5 ft mają −2 do ataków. Koncentracja. Do odświeżenia talii (O). Niebieska: promień 10 ft (maks. 1). Biała: również −2 do zadawanych obrażeń (maks. 1). |
| Romb | Naprowadzający pocisk | A | Biała + Dowolna | Atak czarem w 75 ft: 2k6 blasku; przewaga następnego ataku przeciw celowi (T lub do wykorzystania). Czerwona: +1k6 obrażeń (maks. 3). |
| Trójząb | Zachowanie życia | A | Biała + Biała + Biała + Biała | Rozdziel 40 PW leczenia między Dagnę i sojuszników w 30 ft, do ich maksymalnych PW. |
| Schody | Duchowy oręż | A | Biała + Biała + Czerwona + Czerwona | Przywołaj broń i wykonaj nią atak za 2k8 + MDR. Kolejne aktywacje: D + biała, ruch broni do 20 ft i jeden atak. Najwyżej jedna broń; bez koncentracji. Do odświeżenia talii (O). |

### Eksploracja — NPC i obiekty

- **Empatia (NPC):** Mądrość, bazowy test +6. Rozpoznaj obawy rozmówcy i odwołaj się do jego potrzeb.
- **Oczyszczenie (obiekt):** Mądrość, bazowy test +6. Przywróć bezpieczne użycie skażonego obiektu dostępnymi środkami.

Dobieranie do 21: pas przed następną ofertą. Przekroczenie daje utrudnienie końcowego rzutu (2k20, niższy wynik), bez premii za karty.


### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Krasnoludzki ruch:** Ciężki pancerz nie zmniejsza szybkości Dagny z powodu niewystarczającej Siły.
- **Krok ratowniczki:** Raz na turę Dagny, po leczeniu lub zdjęciu negatywnego stanu innego sojusznika w 10 stopach: ruch 5 stóp bez kosztu ruchu, reakcji i ataków okazyjnych.
- **Krasnoludzka wytrzymałość:** +1 maksymalnego PW na każdy poziom.
- **Krasnoludzka odporność:** przewaga przeciw truciźnie i odporność na obrażenia od trucizny.
- **Uczeń Życia:** Raz w swojej turze, gdy zdolność przywraca PW innemu bohaterowi, możesz zapłacić zieloną maną (Z) zamiast jednej wymaganej białej (B). Kartę normalnie wydajesz. Własne leczenie i samo uruchomienie aury nie pozwalają na tę zamianę.

**Skaza — Nikogo nie zostawiam:** Gdy przy deklaracji sąsiadujesz z żywym sojusznikiem mającym mniej niż połowę maksymalnych PW (również 0 PW), każde działanie ofensywne kosztuje dodatkową dowolną manę. Także zwykły atak; raz za działanie, nie za cel. UI przypomina przed płatnością.

## Lorian — Bard — zarządzanie maną, kusza i kontrola

PW 24; KP 13; ruch 30 ft.
Wspólna talia 25 kart; rynek 5; brak prywatnej ręki. Płatność przed efektem, dobór na końcu tury.

| Symbol panelu | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| Rozwidlenie | Inspiracja | D | Dowolna | Inny bohater w 30 ft otrzymuje 1k4 do jednego ataku albo obrony, do wcześniejszego wykorzystania. Do początku następnej tury źródła (T). |
| Wieża | Strojenie rynku | D | Niebieska | Po zapłacie odrzuć dodatkową kartę rynku. Dobierz dwie: jedną na rynek, drugą na spód talii. Wymaga dwóch kart talii i dodatkowej karty rynku poza kosztem. |
| Oko | Ostrzał destabilizujący | A | Zielona + Dowolna | Strzał z kuszy. Trafiony wróg ma utrudnienie następnego ataku, do wcześniejszego wykorzystania. Do początku następnej tury źródła (T). |
| Klepsydra | Rozpraszający okrzyk | R | Biała | Zmniejsz obrażenia pojedynczego ataku przeciw bohaterowi w 30 ft o 1k6 + CHA, minimum zero. |
| Romb | Odzysk energii | A | Biała + Dowolna | Po zapłacie połóż dwie wybrane karty odrzucone na wierzchu talii, w dowolnej kolejności. Możesz odzyskać właśnie wydany koszt. Niebieska: kolejna karta na wierzch talii (maks. 3). |
| Błysk | Luneta optyczna | A | Zielona + Dowolna | Przed ruchem poświęć cały jego limit. Strzał z +2 do trafienia, ignorujący częściową osłonę. Całkowita osłona blokuje. Zielona: drugi taki strzał w ten sam cel (maks. 1). |
| Schody | Oplatający ostrzał | A | Zielona + Dowolna | Obszar 3×3, także sojusznicy. Obrona ZRC: porażka połowi ruch, bez obrażeń. Do początku następnej tury źródła (T). Niebieska: zamiast połowienia blokuje ruch (maks. 1). Zielona: obszar 4×4 (maks. 1). |
| Trójząb | Wielkie strojenie | A | Niebieska + Niebieska + Niebieska + Niebieska | Po zapłacie przenieś trzy wybrane karty z odrzuconych do pustych miejsc rynku. Możesz odzyskać właśnie wydane karty. |
| Brama | Hymn zwycięstwa | A | Biała + Biała + Niebieska + Niebieska | Aura 30 ft, koncentracja. Lorian i sojusznicy mogą wykorzystać jedną dodatkową akcję dodatkową we własnej turze, będąc w aurze. Płać normalnie; wejście i wyjście nie odnawia użycia. Do odświeżenia talii (O). |

### Eksploracja — NPC i obiekty

- **Inspiracja (NPC):** Charyzma, bazowy test +8. Porusz rozmówcę i zachęć go do współpracy.
- **Pomysłowość (obiekt):** Inteligencja, bazowy test +3. Znajdź obejście problemu i wykorzystaj dostępne części.

Dobieranie do 21: pas przed następną ofertą. Przekroczenie daje utrudnienie końcowego rzutu (2k20, niższy wynik), bez premii za karty.


### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Feyowskie pochodzenie:** przewaga przeciw zauroczeniu i odporność na magiczny sen.
- **Obycie i targowanie:** +2 do każdego pozabojowego testu Charyzmy. Nie tworzy nowych nagród ani możliwości fabularnych.
- **Improwizacja:** raz na NPC przerzuć nieudany pozabojowy test Charyzmy przed konsekwencjami; drugi wynik jest ostateczny. Zużycie jest zapisywane.
- **Zgranie:** Przygotowuj wspólny rynek Strojeniem i Odzyskiem. Karty kosztu trafiają na odrzucone przed efektem i również mogą być odzyskane. Brak prywatnej ręki lub rezerwy.

**Skaza — Potrzeba publiczności:** Jeśli nie ma innego przytomnego bohatera w odległości do 10 ft, pierwsza zdolność specjalna kosztuje o 1 dowolną manę (*) więcej. Dopłata może dotyczyć też reakcji; ponosisz ją najwyżej raz do początku swojej następnej tury. Zwykły atak, ruch, przedmioty i pasywy nie wymagają dopłaty. W grze solo skaza nie działa.

## Nimra — Kontrolerka magiczna — teren i wiedza

PW 20; KP 12; ruch 25 ft.
Wspólna talia 25 kart; rynek 5; brak prywatnej ręki. Płatność przed efektem, dobór na końcu tury.

| Symbol panelu | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| Rozwidlenie | Lodowy impuls | A | Niebieska | Cel w 50 ft: obrona KON; porażka 1k8 zimna i −10 ft ruchu, sukces bez efektu. Do początku następnej tury źródła (T). |
| Klepsydra | Szpilka umysłu | A | Czarna | Cel w 45 ft: obrona MDR; porażka 1k6 psychicznych i brak reakcji, sukces bez efektu. Do początku następnej tury źródła (T). |
| Romb | Lepka matryca | A | Zielona + Dowolna | Obszar 2×2 w 50 ft: trudny teren. Wejście lub początek tury: obrona ZRC przed powaleniem, najwyżej raz na turę istoty. Najwyżej jedna matryca. Powalenie T lub do wstania. Do odświeżenia talii (O). |
| Hak | Mglisty krok | D | Niebieska + Zielona | Teleport do 30 ft na legalne, widoczne pole. |
| Wieża | Tarcza | R | Dowolna | +3 KP przeciw jednemu atakowi i ponowna ocena trafienia. |
| Trójząb | Wachlarz płomieni | A | Czerwona + Dowolna | Stożek 15 ft, także sojusznicy. Obrona ZRC: 2k6 ognia, sukces daje połowę. Czerwona: +1k6 obrażeń (maks. 2). Niebieska: wyłącz dwa wskazane pola (maks. 1). |
| Brama | Fala odrzutu | A | Niebieska + Dowolna | Linia 30×5 ft, także sojusznicy. Obrona SIŁ: 2k6 mocy i odepchnięcie o pole; sukces połowa bez przesunięcia. Czerwona: +1k6 obrażeń (maks. 2). Niebieska: dodatkowe pole odepchnięcia (maks. 1). |
| Schody | Sieć | A | Zielona + Niebieska | Obszar 2×2 w 50 ft, także sojusznicy: trudny teren i obrona ZRC przed unieruchomieniem. Koncentracja. Uwolnienie: akcja i test SIŁ. Do odświeżenia talii (O). Zielona: bok większy o jedno pole (maks. 2). Niebieska: wyłącz dwa wskazane pola (maks. 1). |
| Węzeł | Załamanie woli | A | Czarna + Dowolna | Cel w 50 ft: obrona MDR, 1k6 psychicznych i brak reakcji (T); sukces połowa bez osłabienia. Czarna: dodatkowy cel w 10 ft od pierwszego (maks. 2). Czerwona: +1k6 obrażeń wszystkim celom (maks. 1). |
| Korona | Piorunowy szlak | A | Czerwona + Czerwona + Czerwona + Niebieska | Cel w 60 ft, potem do dwóch przeskoków po 15 ft do najbliższej nieporażonej istoty, także sojusznika. 4k6 błyskawic, osobne obrony ZRC, sukces połowa. |
| Kotwica | Roztrzaskanie | A | Czerwona + Czerwona + Niebieska + Niebieska | Środek w 60 ft, promień 10 ft, także sojusznicy. 4k8 grzmotu, obrona KON daje połowę. Konstrukty mają utrudnienie obrony. |
| Grot | Staza istoty | A | Niebieska + Niebieska + Niebieska + Czarna | Wróg w 50 ft: obrona MDR. Porażka odbiera ruch, akcję główną, dodatkową i reakcję. Koncentracja. Do początku następnej tury źródła (T). |

### Eksploracja — NPC i obiekty

- **Argumentacja (NPC):** Inteligencja, bazowy test +6. Przedstaw rozumowanie i dowody prowadzące do porozumienia.
- **Analiza (obiekt):** Inteligencja, bazowy test +6. Odczytaj symbole i zastosuj właściwą sekwencję obsługi urządzenia.

Dobieranie do 21: pas przed następną ofertą. Przekroczenie daje utrudnienie końcowego rzutu (2k20, niższy wynik), bez premii za karty.


### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Gnomia przebiegłość:** przewaga w obronach INT, MĄD i CHA przeciw magii.
- **Katalog niemożliwego:** wszystkie czary z talii są stale dostępne; Nimra nie przygotowuje ich po odpoczynku.
- **Alchemia barw:** Raz we własnej turze użyj jednej niebieskiej jako dowolnego koloru bazowego kosztu czaru. Nie dotyczy wymaganych kolorów podbić ani ultów; kartę normalnie wydajesz.

**Skaza — Echo magicznego wycieku:** Kolejne użycia tego samego czaru z rzędu: dopłata 0, 1, 2, 3… dowolnych kart. Inny czar przerywa serię. Ruch, zwykły atak, pusta tura i odświeżenie talii nie zerują serii; reakcje jej nie zmieniają. Podbicie nie zmienia tożsamości czaru. Cały koszt maksymalnie 5.

## Erynd — Zwiadowca — tropienie i ostrzał

PW 25; KP 16; ruch 30 ft.
Wspólna talia 25 kart; rynek 5; brak prywatnej ręki. Płatność przed efektem, dobór na końcu tury.

| Symbol panelu | Zdolność | Czas | Mana | Działanie |
|---|---|---|---|---|
| Rozwidlenie | Znak łowcy | D | Zielona | Koncentracja. Raz we własnej turze trafienie oznaczonego celu bronią dodaje 1k6. Przeniesienie po pokonaniu celu bez many i akcji. Do odświeżenia talii (O). |
| Wieża | Zwiadowcza mobilność | D | Zielona | Sprint albo Odstąpienie w bieżącej turze. |
| Klepsydra | Celowanie | D | Dowolna | Przed ruchem poświęć cały jego limit: przewaga następnego ataku łukiem w bieżącej turze. |
| Romb | Strzała zakłócająca | A | Zielona + Dowolna | Trafienie bronią odbiera reakcje i daje utrudnienie następnego ataku celu. Do początku następnej tury źródła (T). |
| Trójząb | Strzała kotwicząca | A | Zielona + Dowolna | Trafiony wróg: obrona SIŁ, porażka blokuje ruch, sukces połowi. Do początku następnej tury źródła (T). Zielona: osobny strzał kotwiczący w drugiego wroga sąsiadującego z pierwszym (maks. 1). |
| Brama | Strzała odsłaniająca | A | Zielona + Dowolna | Trafienie bronią obniża KP celu o 2, bez kumulowania. Do początku następnej tury źródła (T). Czerwona: +1k6 obrażeń (maks. 2). |
| Hak | Podwójny strzał | A | Zielona + Czerwona + Dowolna | Dwa osobne ataki łukiem, z możliwością różnych celów. Czerwona: +1k6 do jednego wybranego trafienia (maks. 2). |
| Błysk | Deszcz strzał | A | Zielona + Zielona + Zielona + Zielona | Wskaż środek obszaru 3×3. Jeden wspólny test łuku przeciw KP każdego legalnego wroga, wspólne 1k8 + 1k6 + ZRC obrażeń. Osłona liczona osobno. Znak i Pierwsza krew najwyżej raz. |
| Oko | Kolczaste zarośla | A | Zielona + Zielona + Niebieska + Niebieska | Środek w 50 ft, promień 20 ft: trudny teren, koncentracja. 1k4 za przebyte pole, maks. 4k4 na turę istoty; także wymuszony ruch i sojusznicy. Do odświeżenia talii (O). |

### Eksploracja — NPC i obiekty

- **Dociekliwość (NPC):** Mądrość, bazowy test +4. Wychwyć szczegół lub niespójność i zadaj właściwe pytanie.
- **Rozpoznanie (obiekt):** Mądrość, bazowy test +6. Ze śladów używania odczytaj bezpieczny sposób obsługi.

Dobieranie do 21: pas przed następną ofertą. Przekroczenie daje utrudnienie końcowego rzutu (2k20, niższy wynik), bez premii za karty.


### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Styl walki: Łucznictwo:** +2 do dystansowych ataków bronią; premia jest już wliczona w atak na arkuszu.
- **Ekspertyza zwiadowcy:** podwójna biegłość w Skradaniu i Sztuce przetrwania.
- **Pierwsza krew:** Raz we własnej turze trafienie długim łukiem w cel z pełnymi PW dodaje 1k6 obrażeń. Wybierz trafienie przed rzutem obrażeń.
- **Czujność zwiadowcy:** +2 do inicjatywy i testów wykrywania ukrytych przeciwników; premia nie dotyczy pułapek.
- **Feyowskie pochodzenie:** przewaga przeciw zauroczeniu i odporność na magiczny sen.
- **Praktyka terenowa:** +2 do własnego końcowego testu wyzwania przy obiekcie w eksploracji. Nie dodaje punktów many ani premii do pułapek w walce.
- **Czytanie prądów:** Przed końcowym uzupełnieniem rynku obejrzyj do dwóch wierzchnich kart talii i odłóż je w wybranej kolejności. Nie tasuj w tym celu stosu odrzuconych.

**Skaza — Trauma bratobójczego strzału:** Pierwszy w twojej turze atak łukiem w cel sąsiadujący z innym przytomnym bohaterem kosztuje o 1 dowolną manę (*) więcej. Sąsiedztwo obejmuje też pola po skosie. Ataki nożem nie wymagają dopłaty. NPC i przywołane istoty stojące przy celu nie uruchamiają skazy.

# Siedem archetypów — ładowanie many 2.0

Źródło: katalog `content/balance/pooled_mana/catalog.json`, profile postaci i stałe oznaczenia panelu areny.
Wygenerowano przez `scripts/generate_mana_character_prints.py`.

Każdy symbol oznacza osobną kartę. Biała: słońce (Plains); niebieska: kropla (Island); czarna: czaszka (Swamp); czerwona: płomień (Mountain); zielona: drzewo (Forest). Cyfra 1 w kółku: dowolny kolor.
A = akcja główna, D = dodatkowa, R = reakcja, MOD = modyfikacja. Koszt obejmuje opisane ataki. T = początek następnej tury źródła; O = mana drain. Dolny pasek mapy wyłączony; symbole pozostają wydrukowane.

PDF-y: `assets/physical_cards/character_sets/physical_mana_v02/` — color, minimal, cards i bw_test.

## Garran — Żelazna Straż — obrona pierwszej linii

PW 28; KP 18; ruch 30 ft.
Wspólna talia: po max(5, 2 × liczba bohaterów) kart każdego koloru. Oferta dwóch kart, dobór jednej na początku własnej tury poniżej 21 pkt. Ładunek pozostaje do draina; bazowa akcja spala 1 kartę z wierzchu, podbicie dodatkowe 2.

### Drugi oddech · Rozwidlenie

- **Ładunek:** Co najmniej 6 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Rzuć 1k10 i dodaj modyfikator Kondycji. Odzyskaj tyle PW, najwyżej do swojego maksimum. Leczenie zajmuje akcję główną, więc konkuruje ze zwykłym atakiem.

### Pozycja obronna · Trójząb

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 0 kart.
- **Efekt:** Otrzymujesz +2 KP. Każda zmiana pola kończy postawę; ponowne użycie nie zwiększa tej premii. Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.

### Rozkaz: Stać! · Brama

- **Ładunek:** Co najmniej 6 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Wybierz wroga w zasięgu 60 ft (12 pól). Aplikacja wykonuje jego obronę Mądrości przeciw ST 14. Przy porażce wróg ma połowę ruchu i nie może używać reakcji. Przy sukcesie nie nakładasz efektu. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.

### Osłona towarzysza · Błysk

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Reakcja
- **Spalanie:** 0 kart.
- **Efekt:** Przed rozstrzygnięciem pojedynczego ataku na sąsiadującego sojusznika przejmij ten atak na siebie. Zużywasz reakcję. Nie obejmuje ataków obszarowych.

### Uderzenie tarczą · Klepsydra

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Wybierz sąsiadującego wroga. Rzuć k20 + modyfikator Siły + naładowanie; aplikacja rzuca za wroga i dodaje jego modyfikator testu. Musisz uzyskać wyższy wynik — remis wygrywa wróg. Wygrana: 1k6 + modyfikator Siły obrażeń i odepchnięcie o pole, jeśli jest wolne. Przegrana: brak efektu.
- **Podbicia:** +1k6 obrażeń. Maks. 2 razy. Każde: +2 spalone karty. Łącznie maks. 2. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Osłona tarczą · Romb

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Sąsiadujący sojusznicy otrzymują +2 KP. Ty nie otrzymujesz tej premii. Sojusznik poza sąsiedztwem traci ochronę. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.
- **Podbicia:** 5 tymczasowych PW jednemu sojusznikowi; różne cele. Maks. 2 razy. Każde: +2 spalone karty. Łącznie maks. 2. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Mowa dowódcy · Hak

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Ty i słyszący sojusznicy w zasięgu 15 ft (3 pól) usuwacie Strach i macie przewagę pierwszego ataku: rzut dwiema k20, wyższy wynik. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.
- **Podbicia:** wybrany uczestnik odzyskuje 1k6 PW. Maks. 2 razy. Każde: +2 spalone karty. Łącznie maks. 2. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Żelazny bastion · Wieża

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Uruchom aurę o promieniu 10 ft (2 pól). Ty i sojusznicy w niej macie premię do KP równą twojemu modyfikatorowi Siły oraz ochronę przed przymusowym przesunięciem. Nie opłacasz aury ponownie w kolejnych turach. Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.

### Rozkaz: Kontratak! · Oko

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Wybierz sojusznika w zasięgu 15 ft (3 pól), który ma reakcję. Każdy z was może przemieścić się do 10 ft (2 pól) bez ataków okazyjnych i wykonać jeden atak bronią. Sojusznik zużywa reakcję. Opisane ataki są częścią tej akcji.


### Eksploracja — NPC i obiekty

- **Autorytet (NPC):** Siła, bazowy test +4; wpływ: kość podatności +4. Przejmij inicjatywę zdecydowaną obecnością i odpowiedzialnością za sytuację.
- **Zabezpieczenie (obiekt):** Kondycja, bazowy test +2; wpływ: kość podatności +2. Utrzymaj konstrukcję stabilną i bezpiecznie zwolnij naprężenia.

Konfrontacja drużynowa: każdy ma własną pulę i turę. Poniżej 21 pkt obowiązkowo wybierz jedną z dwóch odkrytych kart; druga zostaje. Przy 21+ nie dobierasz, bez kary za przekroczenie. Po doborze: własny test albo pomoc +2 do następnego testu sojusznika, bez kumulacji i bez spalania. Premia many +0/+2/+4/+6 wymaga 0/6/12/21 pkt i spala 1/1/2/3 karty. Możesz wybrać słabszą próbę. Test: k20 + cecha + naładowanie + pozostałe premie. Sukces: kość wpływu zależna od podatności + modyfikator cechy + premie wpływu. Pula pozostaje. Pasywy działają, dopóki masz dany kolor, bez limitu tur. Gruba obwódka symbolu: kumuluje się; cienka: nie. Oddech odzyskuje kartę po każdej udanej próbie, przed spalaniem kosztu. Drain wyłącza wszystkie pasywy. Spalanie z wierzchu po efekcie, także przy niepowodzeniu. Po rundzie sytuacja reaguje. Opór 0 = sukces. Brak kart do wymaganej operacji kończy konfrontację; najpierw rozstrzygnij rozpoczęte działanie. Bez ostatniej darmowej kolejki. Na nową konfrontację zbierz cały komplet i przetasuj. Runy wybierają działania; rzuty przez fokus, −/+, podsumowanie i ✓.

- **Czerwona:** Stanowczość: +1 do wpływu za każdą kartę czerwonej many (maks. +2). Kumuluje się.
- **Biała:** Opanowanie: osłoń 1 kartę puli przed każdą reakcją (bez kumulacji)
- **Zielona:** Oddech: po każdej udanej próbie oddaj najstarszą spaloną kartę na spód talii, przed spaleniem kosztu próby. Nie kumuluje się.
- **Czarna:** Skupienie: +1 do testu za każdą kartę czarnej many (maks. +2). Kumuluje się.
- **Niebieska:** Współpraca: pomoc daje +3 zamiast +2 (bez kumulacji)

### Pasywy i skaza


#### Nasycenie maną

- **Czerwona:** Natarcie: +1 obrażeń wręcz za każdą kartę czerwonej many. Kumuluje się.
- **Biała:** Żelazna linia: sojusznik flankujący z tobą wroga ma +1 KP przeciw temu wrogowi. Nie kumuluje się.
- **Zielona:** Ulepszony krytyk: od pierwszej zielonej ataki bronią krytykują przy naturalnym 19–20. Nie dotyczy testu Uderzenia tarczą. Nie kumuluje się.
- **Czarna:** Wytrwałość: +1 do obron KON (maks. +2). Kumuluje się.
- **Niebieska:** Osłona: +1 KP dla Garrana. Nie kumuluje się.

Pasywy są zablokowane, dopóki nie masz karty odpowiedniego koloru. Gruba obwódka symbolu: kumuluje się za kolejne karty tego koloru (według limitu). Cienka: nie kumuluje się. Utrata ostatniej karty koloru, drain i koniec walki wyłączają pasyw. Drain resetuje użycie Nieustępliwości; nowa czarna mana odblokowuje ją ponownie. Odzyskane PW pozostają. Dobór do 21+ pkt.

**Skaza — Nieustępliwość:** Rozpoczęcie własnej tury przy wrogu zmniejsza limit zwykłego ruchu o połowę do końca tury.

## Brakka — Niszczycielka — obrażenia i wytrzymałość

PW 35; KP 11; ruch 30 ft.
Wspólna talia: po max(5, 2 × liczba bohaterów) kart każdego koloru. Oferta dwóch kart, dobór jednej na początku własnej tury poniżej 21 pkt. Ładunek pozostaje do draina; bazowa akcja spala 1 kartę z wierzchu, podbicie dodatkowe 2.

### Szał · Rozwidlenie

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 0 kart.
- **Efekt:** +2 obrażeń ataków wręcz opartych na SIŁ, przewaga testów i obron SIŁ, odporność na kłute, cięte i obuchowe. Nieprzytomność albo tura bez ofensywy kończy Szał. Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.

### Lekkomyślny atak · Wieża

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Modyfikacja opisanego działania
- **Spalanie:** 0 kart.
- **Efekt:** Przewaga następnego zwykłego ataku wręcz opartego na SIŁ w tej turze. Wrogowie mają przewagę ataków przeciw Brakce. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.

### Przyspieszenie · Brama

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 0 kart.
- **Efekt:** W Szale podwaja limit ruchu bieżącej tury. Wcześniejszy ruch wlicza się do limitu.

### Twarda jak skała · Hak

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Reakcja
- **Spalanie:** 0 kart.
- **Efekt:** W Szale: po odporności zmniejsz otrzymane obrażenia o 1k12 + KON, minimum zero.

### Potężne uderzenie · Klepsydra

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** W Szale wykonaj jeden atak bronią z dodatkowym 1k12 obrażeń.
- **Podbicia:** +1k12 obrażeń. Maks. 2 razy. Każde: +2 spalone karty. Łącznie maks. 2. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Z bara · Trójząb

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Sporny test Atletyki przeciw sąsiadującemu wrogowi, maksymalnie o rozmiar większemu. Wygrana odpycha o pole; remis broni cel.
- **Podbicia:** dodatkowe pole odepchnięcia. Maks. 2 razy. 1k6 obrażeń. Maks. 2 razy. Każde: +2 spalone karty. Łącznie maks. 2. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Ogłuszający ryk · Romb

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** W Szale: wrogowie w stożku 15 ft, obrona KON; 1k6 grzmotu, sukces daje połowę.
- **Podbicia:** +1k6 obrażeń. Maks. 2 razy. przy porażce brak ruchu (T). Maks. 1 razy. Każde: +2 spalone karty. Łącznie maks. 3. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Siekator · Błysk

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** W Szale wykonaj trzy osobne ataki wręcz, rozdzielane między dostępnych wrogów.

### Niepowstrzymana · Oko

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** W Szale: ruch do 20 ft bez ataków okazyjnych i trudnego terenu, potem ataki w dwóch różnych wrogów. Trafieni bronią się SIŁ przed powaleniem (T lub do wstania).


### Eksploracja — NPC i obiekty

- **Zastraszanie (NPC):** Kondycja, bazowy test +3; wpływ: kość podatności +3. Wytrzymaj nacisk i pokaż, że nie ustąpisz. Test Kondycji, nie rzut obronny.
- **Forsowanie (obiekt):** Siła, bazowy test +4; wpływ: kość podatności +4. Pokonaj opór siłą: podnieś, wyważ lub rozerwij blokadę.

Konfrontacja drużynowa: każdy ma własną pulę i turę. Poniżej 21 pkt obowiązkowo wybierz jedną z dwóch odkrytych kart; druga zostaje. Przy 21+ nie dobierasz, bez kary za przekroczenie. Po doborze: własny test albo pomoc +2 do następnego testu sojusznika, bez kumulacji i bez spalania. Premia many +0/+2/+4/+6 wymaga 0/6/12/21 pkt i spala 1/1/2/3 karty. Możesz wybrać słabszą próbę. Test: k20 + cecha + naładowanie + pozostałe premie. Sukces: kość wpływu zależna od podatności + modyfikator cechy + premie wpływu. Pula pozostaje. Pasywy działają, dopóki masz dany kolor, bez limitu tur. Gruba obwódka symbolu: kumuluje się; cienka: nie. Oddech odzyskuje kartę po każdej udanej próbie, przed spalaniem kosztu. Drain wyłącza wszystkie pasywy. Spalanie z wierzchu po efekcie, także przy niepowodzeniu. Po rundzie sytuacja reaguje. Opór 0 = sukces. Brak kart do wymaganej operacji kończy konfrontację; najpierw rozstrzygnij rozpoczęte działanie. Bez ostatniej darmowej kolejki. Na nową konfrontację zbierz cały komplet i przetasuj. Runy wybierają działania; rzuty przez fokus, −/+, podsumowanie i ✓.

- **Czerwona:** Stanowczość: +1 do wpływu za każdą kartę czerwonej many (maks. +2). Kumuluje się.
- **Biała:** Opanowanie: osłoń 1 kartę puli przed każdą reakcją (bez kumulacji)
- **Zielona:** Oddech: po każdej udanej próbie oddaj najstarszą spaloną kartę na spód talii, przed spaleniem kosztu próby. Nie kumuluje się.
- **Czarna:** Współpraca: pomoc daje +3 zamiast +2 (bez kumulacji)
- **Niebieska:** Skupienie: +1 do testu za każdą kartę niebieskiej many (maks. +2). Kumuluje się.

### Pasywy i skaza


#### Nasycenie maną

- **Czerwona:** Dzikie ataki: krytyczne trafienie bronią wręcz dodaje jedną kość tej broni. Nie kumuluje się.
- **Biała:** Obrona bez pancerza: bez pancerza KP = 10 + Zręczność + Kondycja; tarcza dozwolona. Nie kumuluje się.
- **Zielona:** Witalność: przy doborze odzyskaj 5 PW. Każdy dobór działa osobno; nie wzmacnia kolejnego leczenia.
- **Czarna:** Nieustępliwość: mając czarną manę, przy zejściu do 0 PW pozostajesz na 1 PW (oprócz natychmiastowej śmierci). Jedno użycie do draina; po drainie i ponownym zdobyciu czarnej działa znów. Nie kumuluje się.
- **Niebieska:** Hart: +2 do obron KON (maks. +2). Nie kumuluje się.

Pasywy są zablokowane, dopóki nie masz karty odpowiedniego koloru. Gruba obwódka symbolu: kumuluje się za kolejne karty tego koloru (według limitu). Cienka: nie kumuluje się. Utrata ostatniej karty koloru, drain i koniec walki wyłączają pasyw. Drain resetuje użycie Nieustępliwości; nowa czarna mana odblokowuje ją ponownie. Odzyskane PW pozostają. Dobór do 21+ pkt.

**Skaza — Głód walki:** Tura bez ofensywy kończy Szał.

## Mira — Specjalistka — infiltracja i precyzyjne obrażenia

PW 21; KP 15; ruch 25 ft.
Wspólna talia: po max(5, 2 × liczba bohaterów) kart każdego koloru. Oferta dwóch kart, dobór jednej na początku własnej tury poniżej 21 pkt. Ładunek pozostaje do draina; bazowa akcja spala 1 kartę z wierzchu, podbicie dodatkowe 2.

### Ukryj się · Rozwidlenie

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 0 kart.
- **Efekt:** Wykonaj test Zręczności: k20 + cecha + naładowanie + inne premie. Aplikacja rozstrzyga wykrycie osobno dla każdego wroga; remis oznacza wykrycie. Sąsiadujący wróg lub blokujący stan uniemożliwia zwykłe ukrycie. Atak, wykrycie lub dobrowolne ujawnienie kończy ukrycie. Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.

### Unik instynktowny · Trójząb

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Reakcja
- **Spalanie:** 0 kart.
- **Efekt:** Nadaj utrudnienie jednemu atakowi przeciw Mirze. Nie wymaga rzutu Miry.

### Zwód · Romb

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 0 kart.
- **Efekt:** Sąsiadujący wróg nie może wykonywać ataków okazyjnych przeciw Mirze. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.

### Cięcie ścięgna · Brama

- **Ładunek:** Co najmniej 6 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Atak wręcz z własnej flanki. Trafienie zadaje obrażenia broni i połowi ruch celu. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.

### Zasłona dymna · Wieża

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Ruch do 10 ft bez ataków okazyjnych i próba ukrycia, także po rozpoczęciu obok wroga. Ukrycie kończą atak lub wykrycie. Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.
- **Podbicia:** +5 ft ruchu. Maks. 2 razy. przewaga testu ukrycia. Maks. 1 razy. Każde: +2 spalone karty. Łącznie maks. 3. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Przeskok przez gardę · Klepsydra

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Atak wręcz i przejście na wolne pole dokładnie za celem.
- **Podbicia:** +1k6 obrażeń. Maks. 2 razy. Każde: +2 spalone karty. Łącznie maks. 2. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Mistrzyni ostrzy · Hak

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Atak nożem z ukrycia albo własnej flanki, dodatkowe 1k6 obrażeń.
- **Podbicia:** +1k6 obrażeń. Maks. 2 razy. krwawienie 1k4 na początku tury celu (O); leczenie kończy, bez kumulowania. Maks. 1 razy. Każde: +2 spalone karty. Łącznie maks. 3. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Wyrok z cienia · Błysk

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Wymaga ukrycia przed celem i własnej flanki. Jeden atak z przewagą i dodatkowym 5k6 obrażeń.

### Taniec ostrzy · Oko

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Ruch do 15 ft bez ataków okazyjnych i dwa ataki w różnych wrogów po drodze. Pasywy many działają przy każdym trafieniu spełniającym warunek ukrycia lub własnej flanki.


### Eksploracja — NPC i obiekty

- **Blef (NPC):** Inteligencja, bazowy test +2; wpływ: kość podatności +2. Zbuduj sprytne, spójne kłamstwo lub pozór.
- **Manipulacja (obiekt):** Zręczność, bazowy test +4; wpływ: kość podatności +4. Precyzyjnie zwolnij zamek, zatrzask lub drobny mechanizm przy użyciu narzędzi.

Konfrontacja drużynowa: każdy ma własną pulę i turę. Poniżej 21 pkt obowiązkowo wybierz jedną z dwóch odkrytych kart; druga zostaje. Przy 21+ nie dobierasz, bez kary za przekroczenie. Po doborze: własny test albo pomoc +2 do następnego testu sojusznika, bez kumulacji i bez spalania. Premia many +0/+2/+4/+6 wymaga 0/6/12/21 pkt i spala 1/1/2/3 karty. Możesz wybrać słabszą próbę. Test: k20 + cecha + naładowanie + pozostałe premie. Sukces: kość wpływu zależna od podatności + modyfikator cechy + premie wpływu. Pula pozostaje. Pasywy działają, dopóki masz dany kolor, bez limitu tur. Gruba obwódka symbolu: kumuluje się; cienka: nie. Oddech odzyskuje kartę po każdej udanej próbie, przed spalaniem kosztu. Drain wyłącza wszystkie pasywy. Spalanie z wierzchu po efekcie, także przy niepowodzeniu. Po rundzie sytuacja reaguje. Opór 0 = sukces. Brak kart do wymaganej operacji kończy konfrontację; najpierw rozstrzygnij rozpoczęte działanie. Bez ostatniej darmowej kolejki. Na nową konfrontację zbierz cały komplet i przetasuj. Runy wybierają działania; rzuty przez fokus, −/+, podsumowanie i ✓.

- **Czerwona:** Skupienie: +1 do testu za każdą kartę czerwonej many (maks. +2). Kumuluje się.
- **Biała:** Opanowanie: osłoń 1 kartę puli przed każdą reakcją (bez kumulacji)
- **Zielona:** Stanowczość: +1 do wpływu za każdą kartę zielonej many (maks. +2). Kumuluje się.
- **Czarna:** Współpraca: pomoc daje +3 zamiast +2 (bez kumulacji)
- **Niebieska:** Oddech: po każdej udanej próbie oddaj najstarszą spaloną kartę na spód talii, przed spaleniem kosztu próby. Nie kumuluje się.

### Pasywy i skaza


#### Nasycenie maną

- **Czerwona:** Atak z cienia: każde trafienie bronią z ukrycia przed celem zadaje dodatkowe 1k6 obrażeń. Łączy się z Atakiem z flanki. Nie kumuluje się.
- **Biała:** Ruchomy cel: +2 KP przeciw dystansowym atakom bronią i czarami; nie przeciw obszarom ani obronom. Nie kumuluje się.
- **Zielona:** Atak z flanki: każde trafienie bronią we wroga, którego flankujesz, zadaje dodatkowe 2k6 obrażeń. Z ukryciem łącznie +3k6. Nie kumuluje się.
- **Czarna:** Zwinne dłonie: po każdym trafieniu nożem możesz ruszyć się o 5 ft bez kosztu ruchu i ataków okazyjnych. Nie kumuluje się.
- **Niebieska:** Szczęście: naturalną 1 w ataku, teście lub obronie przerzuć raz; drugi wynik obowiązuje. Nie kumuluje się.

Pasywy są zablokowane, dopóki nie masz karty odpowiedniego koloru. Gruba obwódka symbolu: kumuluje się za kolejne karty tego koloru (według limitu). Cienka: nie kumuluje się. Utrata ostatniej karty koloru, drain i koniec walki wyłączają pasyw. Drain resetuje użycie Nieustępliwości; nowa czarna mana odblokowuje ją ponownie. Odzyskane PW pozostają. Dobór do 21+ pkt.

**Skaza — Cienka granica:** W ukryciu masz utrudnienie obron i testów reakcji.

## Dagna — Uzdrowicielka — leczenie i wzmocnienia

PW 27; KP 16; ruch 25 ft.
Wspólna talia: po max(5, 2 × liczba bohaterów) kart każdego koloru. Oferta dwóch kart, dobór jednej na początku własnej tury poniżej 21 pkt. Ładunek pozostaje do draina; bazowa akcja spala 1 kartę z wierzchu, podbicie dodatkowe 2.

### Święty płomień · Rozwidlenie

- **Ładunek:** Co najmniej 6 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Stożek 15 ft, także sojusznicy. Obrona ZRC: porażka 1k8 blasku, sukces bez obrażeń.

### Błogosławieństwo · Klepsydra

- **Ładunek:** Co najmniej 6 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Aura 10 ft: Dagna i sojusznicy mają +1k4 do ataków i obron. Koncentracja. Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.

### Pomniejsze przywrócenie · Błysk

- **Ładunek:** Co najmniej 6 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Dotykiem usuń jeden dostępny stan: zatrucie, oślepienie lub głuchotę.

### Opiekuńczy gest · Hak

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 0 kart.
- **Efekt:** Sąsiadujący sojusznik otrzymuje 1k4 + MDR tymczasowych PW. Nie leczy ran; tymczasowe PW nie kumulują się. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.

### Słowo leczenia · Wieża

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Cel w 60 ft odzyskuje 1k4 + 7 PW.
- **Podbicia:** +1k6 leczenia. Maks. 3 razy. Każde: +2 spalone karty. Łącznie maks. 3. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Aura Boskiej Opieki · Brama

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Wrogowie w 5 ft mają −2 do ataków. Koncentracja. Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.
- **Podbicia:** promień 10 ft. Maks. 1 razy. również −2 do zadawanych obrażeń. Maks. 1 razy. Każde: +2 spalone karty. Łącznie maks. 2. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Naprowadzający pocisk · Romb

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Atak czarem w 75 ft: 2k6 blasku; przewaga następnego ataku przeciw celowi (T lub do wykorzystania).
- **Podbicia:** +1k6 obrażeń. Maks. 3 razy. Każde: +2 spalone karty. Łącznie maks. 3. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Zachowanie życia · Trójząb

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Rozdziel 40 PW leczenia między Dagnę i sojuszników w 30 ft, do ich maksymalnych PW.

### Duchowy oręż · Schody

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Przywołaj broń i wykonaj nią atak za 2k8 + MDR. Kolejne aktywacje: akcja dodatkowa, bez spalania, ruch broni do 20 ft i jeden atak. Najwyżej jedna broń; bez koncentracji. Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.


### Eksploracja — NPC i obiekty

- **Empatia (NPC):** Mądrość, bazowy test +4; wpływ: kość podatności +4. Rozpoznaj obawy rozmówcy i odwołaj się do jego potrzeb.
- **Oczyszczenie (obiekt):** Mądrość, bazowy test +4; wpływ: kość podatności +4. Przywróć bezpieczne użycie skażonego obiektu dostępnymi środkami.

Konfrontacja drużynowa: każdy ma własną pulę i turę. Poniżej 21 pkt obowiązkowo wybierz jedną z dwóch odkrytych kart; druga zostaje. Przy 21+ nie dobierasz, bez kary za przekroczenie. Po doborze: własny test albo pomoc +2 do następnego testu sojusznika, bez kumulacji i bez spalania. Premia many +0/+2/+4/+6 wymaga 0/6/12/21 pkt i spala 1/1/2/3 karty. Możesz wybrać słabszą próbę. Test: k20 + cecha + naładowanie + pozostałe premie. Sukces: kość wpływu zależna od podatności + modyfikator cechy + premie wpływu. Pula pozostaje. Pasywy działają, dopóki masz dany kolor, bez limitu tur. Gruba obwódka symbolu: kumuluje się; cienka: nie. Oddech odzyskuje kartę po każdej udanej próbie, przed spalaniem kosztu. Drain wyłącza wszystkie pasywy. Spalanie z wierzchu po efekcie, także przy niepowodzeniu. Po rundzie sytuacja reaguje. Opór 0 = sukces. Brak kart do wymaganej operacji kończy konfrontację; najpierw rozstrzygnij rozpoczęte działanie. Bez ostatniej darmowej kolejki. Na nową konfrontację zbierz cały komplet i przetasuj. Runy wybierają działania; rzuty przez fokus, −/+, podsumowanie i ✓.

- **Czerwona:** Stanowczość: +1 do wpływu za każdą kartę czerwonej many (maks. +2). Kumuluje się.
- **Biała:** Współpraca: pomoc daje +3 zamiast +2 (bez kumulacji)
- **Zielona:** Oddech: po każdej udanej próbie oddaj najstarszą spaloną kartę na spód talii, przed spaleniem kosztu próby. Nie kumuluje się.
- **Czarna:** Opanowanie: osłoń 1 kartę puli przed każdą reakcją (bez kumulacji)
- **Niebieska:** Skupienie: +1 do testu za każdą kartę niebieskiej many (maks. +2). Kumuluje się.

### Pasywy i skaza


#### Nasycenie maną

- **Czerwona:** Gniew: +2 obrażeń zaklęć za każdą kartę czerwonej many. Kumuluje się.
- **Biała:** Wiara: +1 do wszystkich obron (maks. +2). Kumuluje się.
- **Zielona:** Ukojenie: przy doborze przytomni sojusznicy w 10 ft i ty odzyskujecie 2 PW. Każdy dobór działa osobno; nie wzmacnia kolejnego leczenia.
- **Czarna:** Odporność na truciznę: przewaga w obronach przeciw truciźnie i połowa obrażeń od trucizny. Nie kumuluje się.
- **Niebieska:** Krok ratowniczki: po każdym leczeniu lub zdjęciu negatywnego stanu innego sojusznika w 10 ft możesz ruszyć się o 5 ft bez kosztu i ataków okazyjnych. Nie kumuluje się.

Pasywy są zablokowane, dopóki nie masz karty odpowiedniego koloru. Gruba obwódka symbolu: kumuluje się za kolejne karty tego koloru (według limitu). Cienka: nie kumuluje się. Utrata ostatniej karty koloru, drain i koniec walki wyłączają pasyw. Drain resetuje użycie Nieustępliwości; nowa czarna mana odblokowuje ją ponownie. Odzyskane PW pozostają. Dobór do 21+ pkt.

**Skaza — Nikogo nie zostawiam:** Ofensywna płatna zdolność przy sojuszniku poniżej połowy PW spala dodatkową kartę.

## Lorian — Bard — zarządzanie maną, kusza i kontrola

PW 24; KP 13; ruch 30 ft.
Wspólna talia: po max(5, 2 × liczba bohaterów) kart każdego koloru. Oferta dwóch kart, dobór jednej na początku własnej tury poniżej 21 pkt. Ładunek pozostaje do draina; bazowa akcja spala 1 kartę z wierzchu, podbicie dodatkowe 2.

### Inspiracja · Rozwidlenie

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 0 kart.
- **Efekt:** Inny bohater w 30 ft otrzymuje 1k4 do jednego ataku albo obrony, do wcześniejszego wykorzystania. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.

### Strojenie talii · Wieża

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 0 kart.
- **Efekt:** Podejrzyj dwie wierzchnie karty i odłóż je na wierzch w wybranej kolejności. Przy jednej karcie obejrzyj tylko ją. Bez tasowania.

### Ostrzał destabilizujący · Oko

- **Ładunek:** Co najmniej 6 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Strzał z kuszy. Trafiony wróg ma utrudnienie następnego ataku, do wcześniejszego wykorzystania. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.

### Rozpraszający okrzyk · Klepsydra

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Reakcja
- **Spalanie:** 0 kart.
- **Efekt:** Zmniejsz obrażenia pojedynczego ataku przeciw bohaterowi w 30 ft o 1k6 + CHA, minimum zero.

### Odzysk energii · Romb

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 0 kart.
- **Efekt:** Przenieś do dwóch spalonych kart na spód talii, w wybranej kolejności. Nie odzyskujesz kart wygasłych ani uwięzionych. Zachowujesz ładunek. Bez spalania bazowego; każde podbicie spala 2 karty po odzysku.
- **Podbicia:** kolejna karta na wierzch talii. Maks. 3 razy. Każde: +2 spalone karty. Łącznie maks. 3. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Luneta optyczna · Błysk

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Przed ruchem poświęć cały jego limit. Strzał z +2 do trafienia, ignorujący częściową osłonę. Całkowita osłona blokuje.
- **Podbicia:** drugi taki strzał w ten sam cel. Maks. 1 razy. Każde: +2 spalone karty. Łącznie maks. 1. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Oplatający ostrzał · Schody

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Obszar 3×3, także sojusznicy. Obrona ZRC: porażka połowi ruch, bez obrażeń. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.
- **Podbicia:** zamiast połowienia blokuje ruch. Maks. 1 razy. obszar 4×4. Maks. 1 razy. Każde: +2 spalone karty. Łącznie maks. 2. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Wielkie strojenie · Trójząb

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 0 kart.
- **Efekt:** Przenieś do trzech spalonych kart na wierzch talii, w wybranej kolejności. Nie odzyskujesz kart wygasłych ani uwięzionych. Zachowujesz ładunek. Bez spalania bazowego; każde podbicie spala 2 karty po odzysku.

### Hymn zwycięstwa · Brama

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Aura 30 ft, koncentracja. Lorian i sojusznicy mogą wykorzystać jedną dodatkową akcję dodatkową we własnej turze, będąc w aurze. Płać normalnie; wejście i wyjście nie odnawia użycia. Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.


### Eksploracja — NPC i obiekty

- **Inspiracja (NPC):** Charyzma, bazowy test +4; wpływ: kość podatności +4. Porusz rozmówcę i zachęć go do współpracy.
- **Pomysłowość (obiekt):** Inteligencja, bazowy test +1; wpływ: kość podatności +1. Znajdź obejście problemu i wykorzystaj dostępne części.

Konfrontacja drużynowa: każdy ma własną pulę i turę. Poniżej 21 pkt obowiązkowo wybierz jedną z dwóch odkrytych kart; druga zostaje. Przy 21+ nie dobierasz, bez kary za przekroczenie. Po doborze: własny test albo pomoc +2 do następnego testu sojusznika, bez kumulacji i bez spalania. Premia many +0/+2/+4/+6 wymaga 0/6/12/21 pkt i spala 1/1/2/3 karty. Możesz wybrać słabszą próbę. Test: k20 + cecha + naładowanie + pozostałe premie. Sukces: kość wpływu zależna od podatności + modyfikator cechy + premie wpływu. Pula pozostaje. Pasywy działają, dopóki masz dany kolor, bez limitu tur. Gruba obwódka symbolu: kumuluje się; cienka: nie. Oddech odzyskuje kartę po każdej udanej próbie, przed spalaniem kosztu. Drain wyłącza wszystkie pasywy. Spalanie z wierzchu po efekcie, także przy niepowodzeniu. Po rundzie sytuacja reaguje. Opór 0 = sukces. Brak kart do wymaganej operacji kończy konfrontację; najpierw rozstrzygnij rozpoczęte działanie. Bez ostatniej darmowej kolejki. Na nową konfrontację zbierz cały komplet i przetasuj. Runy wybierają działania; rzuty przez fokus, −/+, podsumowanie i ✓.

- **Czerwona:** Stanowczość: +1 do wpływu za każdą kartę czerwonej many (maks. +2). Kumuluje się.
- **Biała:** Skupienie: +1 do testu za każdą kartę białej many (maks. +2). Kumuluje się.
- **Zielona:** Opanowanie: osłoń 1 kartę puli przed każdą reakcją (bez kumulacji)
- **Czarna:** Współpraca: pomoc daje +3 zamiast +2 (bez kumulacji)
- **Niebieska:** Oddech: po każdej udanej próbie oddaj najstarszą spaloną kartę na spód talii, przed spaleniem kosztu próby. Nie kumuluje się.

### Pasywy i skaza


#### Nasycenie maną

- **Czerwona:** Akcent: +2 obrażeń dystansowej broni za każdą kartę czerwonej many. Kumuluje się.
- **Biała:** Rytm kroków: +1 KP (maks. +1). Nie kumuluje się.
- **Zielona:** Otucha: przy doborze ulecz o 3 PW najbardziej rannego przytomnego sojusznika w 10 ft, wliczając siebie. Każdy dobór działa osobno; nie wzmacnia kolejnego leczenia.
- **Czarna:** Oszczędna harmonia: spalanie własnej zdolności −1 (minimum 1, maks. rabatu 1). Nie kumuluje się.
- **Niebieska:** Nieugięty umysł: przewaga w obronach przeciw zauroczeniu i odporność na magiczny sen. Nie kumuluje się.

Pasywy są zablokowane, dopóki nie masz karty odpowiedniego koloru. Gruba obwódka symbolu: kumuluje się za kolejne karty tego koloru (według limitu). Cienka: nie kumuluje się. Utrata ostatniej karty koloru, drain i koniec walki wyłączają pasyw. Drain resetuje użycie Nieustępliwości; nowa czarna mana odblokowuje ją ponownie. Odzyskane PW pozostają. Dobór do 21+ pkt.

**Skaza — Potrzeba publiczności:** Bez przytomnego sojusznika w 10 ft, w wieloosobowej drużynie: płatna zdolność spala dodatkową kartę.

## Nimra — Kontrolerka magiczna — teren i wiedza

PW 20; KP 12; ruch 25 ft.
Wspólna talia: po max(5, 2 × liczba bohaterów) kart każdego koloru. Oferta dwóch kart, dobór jednej na początku własnej tury poniżej 21 pkt. Ładunek pozostaje do draina; bazowa akcja spala 1 kartę z wierzchu, podbicie dodatkowe 2.

### Lodowy impuls · Rozwidlenie

- **Ładunek:** Co najmniej 6 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Cel w 50 ft: obrona KON; porażka 1k8 zimna i −10 ft ruchu, sukces bez efektu. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.

### Szpilka umysłu · Klepsydra

- **Ładunek:** Co najmniej 6 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Cel w 45 ft: obrona MDR; porażka 1k6 psychicznych i brak reakcji, sukces bez efektu. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.

### Lepka matryca · Romb

- **Ładunek:** Co najmniej 6 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Obszar 2×2 w 50 ft: trudny teren. Wejście lub początek tury: obrona ZRC przed powaleniem, najwyżej raz na turę istoty. Najwyżej jedna matryca. Powalenie T lub do wstania. Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.

### Mglisty krok · Hak

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 0 kart.
- **Efekt:** Teleport do 30 ft na legalne, widoczne pole.

### Tarcza · Wieża

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Reakcja
- **Spalanie:** 0 kart.
- **Efekt:** +3 KP przeciw jednemu atakowi i ponowna ocena trafienia.

### Wachlarz płomieni · Trójząb

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Stożek 15 ft, także sojusznicy. Obrona ZRC: 2k6 ognia, sukces daje połowę.
- **Podbicia:** +1k6 obrażeń. Maks. 2 razy. wyłącz dwa wskazane pola. Maks. 1 razy. Każde: +2 spalone karty. Łącznie maks. 3. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Fala odrzutu · Brama

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Linia 30×5 ft, także sojusznicy. Obrona SIŁ: 2k6 mocy i odepchnięcie o pole; sukces połowa bez przesunięcia.
- **Podbicia:** +1k6 obrażeń. Maks. 2 razy. dodatkowe pole odepchnięcia. Maks. 1 razy. Każde: +2 spalone karty. Łącznie maks. 3. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Sieć · Schody

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Obszar 2×2 w 50 ft, także sojusznicy: trudny teren i obrona ZRC przed unieruchomieniem. Koncentracja. Uwolnienie: akcja i test SIŁ. Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.
- **Podbicia:** bok większy o jedno pole. Maks. 2 razy. wyłącz dwa wskazane pola. Maks. 1 razy. Każde: +2 spalone karty. Łącznie maks. 3. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Załamanie woli · Węzeł

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Cel w 50 ft: obrona MDR, 1k6 psychicznych i brak reakcji (T); sukces połowa bez osłabienia.
- **Podbicia:** dodatkowy cel w 10 ft od pierwszego. Maks. 2 razy. +1k6 obrażeń wszystkim celom. Maks. 1 razy. Każde: +2 spalone karty. Łącznie maks. 3. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Piorunowy szlak · Korona

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Cel w 60 ft, potem do dwóch przeskoków po 15 ft do najbliższej nieporażonej istoty, także sojusznika. 4k6 błyskawic, osobne obrony ZRC, sukces połowa.

### Roztrzaskanie · Kotwica

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Środek w 60 ft, promień 10 ft, także sojusznicy. 4k8 grzmotu, obrona KON daje połowę. Konstrukty mają utrudnienie obrony.

### Staza istoty · Grot

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Wróg w 50 ft: obrona MDR. Porażka odbiera ruch, akcję główną, dodatkową i reakcję. Koncentracja. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.


### Eksploracja — NPC i obiekty

- **Argumentacja (NPC):** Inteligencja, bazowy test +4; wpływ: kość podatności +4. Przedstaw rozumowanie i dowody prowadzące do porozumienia.
- **Analiza (obiekt):** Inteligencja, bazowy test +4; wpływ: kość podatności +4. Odczytaj symbole i zastosuj właściwą sekwencję obsługi urządzenia.

Konfrontacja drużynowa: każdy ma własną pulę i turę. Poniżej 21 pkt obowiązkowo wybierz jedną z dwóch odkrytych kart; druga zostaje. Przy 21+ nie dobierasz, bez kary za przekroczenie. Po doborze: własny test albo pomoc +2 do następnego testu sojusznika, bez kumulacji i bez spalania. Premia many +0/+2/+4/+6 wymaga 0/6/12/21 pkt i spala 1/1/2/3 karty. Możesz wybrać słabszą próbę. Test: k20 + cecha + naładowanie + pozostałe premie. Sukces: kość wpływu zależna od podatności + modyfikator cechy + premie wpływu. Pula pozostaje. Pasywy działają, dopóki masz dany kolor, bez limitu tur. Gruba obwódka symbolu: kumuluje się; cienka: nie. Oddech odzyskuje kartę po każdej udanej próbie, przed spalaniem kosztu. Drain wyłącza wszystkie pasywy. Spalanie z wierzchu po efekcie, także przy niepowodzeniu. Po rundzie sytuacja reaguje. Opór 0 = sukces. Brak kart do wymaganej operacji kończy konfrontację; najpierw rozstrzygnij rozpoczęte działanie. Bez ostatniej darmowej kolejki. Na nową konfrontację zbierz cały komplet i przetasuj. Runy wybierają działania; rzuty przez fokus, −/+, podsumowanie i ✓.

- **Czerwona:** Stanowczość: +1 do wpływu za każdą kartę czerwonej many (maks. +2). Kumuluje się.
- **Biała:** Opanowanie: osłoń 1 kartę puli przed każdą reakcją (bez kumulacji)
- **Zielona:** Oddech: po każdej udanej próbie oddaj najstarszą spaloną kartę na spód talii, przed spaleniem kosztu próby. Nie kumuluje się.
- **Czarna:** Współpraca: pomoc daje +3 zamiast +2 (bez kumulacji)
- **Niebieska:** Skupienie: +1 do testu za każdą kartę niebieskiej many (maks. +2). Kumuluje się.

### Pasywy i skaza


#### Nasycenie maną

- **Czerwona:** Żar: +2 obrażeń zaklęć za każdą kartę czerwonej many. Kumuluje się.
- **Biała:** Powłoka: +1 KP (maks. +1). Nie kumuluje się.
- **Zielona:** Regeneracja: przy doborze odzyskaj 4 PW. Każdy dobór działa osobno; nie wzmacnia kolejnego leczenia.
- **Czarna:** Magiczna przezorność: przewaga w obronach Inteligencji, Mądrości i Charyzmy przeciw magii. Nie kumuluje się.
- **Niebieska:** Nasycenie: +1 obrażeń zaklęć za każdą kartę niebieskiej many. Kumuluje się.

Pasywy są zablokowane, dopóki nie masz karty odpowiedniego koloru. Gruba obwódka symbolu: kumuluje się za kolejne karty tego koloru (według limitu). Cienka: nie kumuluje się. Utrata ostatniej karty koloru, drain i koniec walki wyłączają pasyw. Drain resetuje użycie Nieustępliwości; nowa czarna mana odblokowuje ją ponownie. Odzyskane PW pozostają. Dobór do 21+ pkt.

**Skaza — Echo:** Echo: kolejna ta sama płatna zdolność z rzędu spala o 1 kartę więcej (maks. +2). Inna płatna zdolność zeruje serię.

## Erynd — Zwiadowca — tropienie i ostrzał

PW 25; KP 16; ruch 30 ft.
Wspólna talia: po max(5, 2 × liczba bohaterów) kart każdego koloru. Oferta dwóch kart, dobór jednej na początku własnej tury poniżej 21 pkt. Ładunek pozostaje do draina; bazowa akcja spala 1 kartę z wierzchu, podbicie dodatkowe 2.

### Znak łowcy · Rozwidlenie

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 0 kart.
- **Efekt:** Koncentracja. Raz we własnej turze trafienie oznaczonego celu bronią dodaje 1k6. Przeniesienie po pokonaniu celu bez many i akcji. Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.

### Zwiadowcza mobilność · Wieża

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 0 kart.
- **Efekt:** Sprint albo Odstąpienie w bieżącej turze.

### Celowanie · Klepsydra

- **Ładunek:** 0 pkt — dostępna bez naładowania.
- **Akcja:** Akcja dodatkowa
- **Spalanie:** 0 kart.
- **Efekt:** Przed ruchem poświęć cały jego limit: przewaga następnego ataku łukiem w bieżącej turze.

### Strzała zakłócająca · Romb

- **Ładunek:** Co najmniej 6 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Trafienie bronią odbiera reakcje i daje utrudnienie następnego ataku celu. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.

### Strzała kotwicząca · Trójząb

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Trafiony wróg: obrona SIŁ, porażka blokuje ruch, sukces połowi. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.
- **Podbicia:** osobny strzał kotwiczący w drugiego wroga sąsiadującego z pierwszym. Maks. 1 razy. Każde: +2 spalone karty. Łącznie maks. 1. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Strzała odsłaniająca · Brama

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Trafienie bronią obniża KP celu o 2, bez kumulowania. Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.
- **Podbicia:** +1k6 obrażeń. Maks. 2 razy. Każde: +2 spalone karty. Łącznie maks. 2. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Podwójny strzał · Hak

- **Ładunek:** Co najmniej 12 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Dwa osobne ataki łukiem, z możliwością różnych celów.
- **Podbicia:** +1k6 do jednego wybranego trafienia. Maks. 2 razy. Każde: +2 spalone karty. Łącznie maks. 2. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.

### Deszcz strzał · Błysk

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Wskaż środek obszaru 3×3. Jeden wspólny test łuku przeciw KP każdego legalnego wroga, wspólne 1k8 + 1k6 + ZRC obrażeń. Osłona liczona osobno. Znak i Pierwsza krew najwyżej raz.

### Kolczaste zarośla · Oko

- **Ładunek:** Co najmniej 21 pkt. Pula zostaje po użyciu.
- **Akcja:** Akcja główna
- **Spalanie:** 1 karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.
- **Efekt:** Środek w 50 ft, promień 20 ft: trudny teren, koncentracja. 1k4 za przebyte pole, maks. 4k4 na turę istoty; także wymuszony ruch i sojusznicy. Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.


### Eksploracja — NPC i obiekty

- **Dociekliwość (NPC):** Mądrość, bazowy test +2; wpływ: kość podatności +2. Wychwyć szczegół lub niespójność i zadaj właściwe pytanie.
- **Rozpoznanie (obiekt):** Mądrość, bazowy test +2; wpływ: kość podatności +2. Ze śladów używania odczytaj bezpieczny sposób obsługi.

Konfrontacja drużynowa: każdy ma własną pulę i turę. Poniżej 21 pkt obowiązkowo wybierz jedną z dwóch odkrytych kart; druga zostaje. Przy 21+ nie dobierasz, bez kary za przekroczenie. Po doborze: własny test albo pomoc +2 do następnego testu sojusznika, bez kumulacji i bez spalania. Premia many +0/+2/+4/+6 wymaga 0/6/12/21 pkt i spala 1/1/2/3 karty. Możesz wybrać słabszą próbę. Test: k20 + cecha + naładowanie + pozostałe premie. Sukces: kość wpływu zależna od podatności + modyfikator cechy + premie wpływu. Pula pozostaje. Pasywy działają, dopóki masz dany kolor, bez limitu tur. Gruba obwódka symbolu: kumuluje się; cienka: nie. Oddech odzyskuje kartę po każdej udanej próbie, przed spalaniem kosztu. Drain wyłącza wszystkie pasywy. Spalanie z wierzchu po efekcie, także przy niepowodzeniu. Po rundzie sytuacja reaguje. Opór 0 = sukces. Brak kart do wymaganej operacji kończy konfrontację; najpierw rozstrzygnij rozpoczęte działanie. Bez ostatniej darmowej kolejki. Na nową konfrontację zbierz cały komplet i przetasuj. Runy wybierają działania; rzuty przez fokus, −/+, podsumowanie i ✓.

- **Czerwona:** Stanowczość: +1 do wpływu za każdą kartę czerwonej many (maks. +2). Kumuluje się.
- **Biała:** Opanowanie: osłoń 1 kartę puli przed każdą reakcją (bez kumulacji)
- **Zielona:** Skupienie: +1 do testu za każdą kartę zielonej many (maks. +2). Kumuluje się.
- **Czarna:** Współpraca: pomoc daje +3 zamiast +2 (bez kumulacji)
- **Niebieska:** Oddech: po każdej udanej próbie oddaj najstarszą spaloną kartę na spód talii, przed spaleniem kosztu próby. Nie kumuluje się.

### Pasywy i skaza


#### Nasycenie maną

- **Czerwona:** Pierwsza krew: każde trafienie w cel mający pełne PW zadaje dodatkowe 1k6 obrażeń. Działa, dopóki masz czerwoną manę. Nie kumuluje się.
- **Biała:** Kamuflaż: +1 KP (maks. +1). Nie kumuluje się.
- **Zielona:** Instynkt: +1 do obron ZRĘ (maks. +2). Kumuluje się.
- **Czarna:** Czujność zwiadowcy: +2 do wykrywania ukrytych przeciwników; nie dotyczy pułapek. Nie kumuluje się.
- **Niebieska:** Łucznictwo: +2 do ataków dystansową bronią. Nie kumuluje się.

Pasywy są zablokowane, dopóki nie masz karty odpowiedniego koloru. Gruba obwódka symbolu: kumuluje się za kolejne karty tego koloru (według limitu). Cienka: nie kumuluje się. Utrata ostatniej karty koloru, drain i koniec walki wyłączają pasyw. Drain resetuje użycie Nieustępliwości; nowa czarna mana odblokowuje ją ponownie. Odzyskane PW pozostają. Dobór do 21+ pkt.

**Skaza — Trauma bratobójczego strzału:** Płatny strzał w cel sąsiadujący z innym bohaterem spala dodatkową kartę.

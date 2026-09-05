# Siedem archetypów planszowych — aktualne zasady postaci

Źródło: `scripts/generate_keyboard_character_sheets.py`, profile gry i wspólny katalog `character_creation/boardgame_help.py`.
Dokument jest odtwarzany razem z wydrukami. Poprzednie wersje zestawów są dostępne w historii Git.

Wszyscy bohaterowie zaczynają na poziomie 3 z premią +2 do głównej cechy, już wliczoną w statystyki. Wybierz 1–5 z siedmiu postaci, potem scenariusz. Awans talii pozostaje osobnym etapem projektu.

W walce klawisz otwiera podgląd, Enter zatwierdza, Esc lub Backspace wraca bez kosztu. Plansza wskazuje pozycje, cele i obszary. Mysz jest awaryjnym mechanizmem. Działania oznaczone AUTO są proponowanymi reakcjami, nie skrótami.

Komórka N+ oznacza komórkę co najmniej poziomu N. Sztuczki nie zużywają komórek. Koncentracja utrzymuje jeden efekt naraz; wydanie komórki, zasobu i akcji następuje dopiero przy wykonaniu. Szał odnawia Dzikość; przejście między scenariuszami nie odnawia zasobów.

W aktualnej grze nie liczymy strzał ani bełtów. Długi łuk Erynda ma +8 do ataku (łącznie z Łucznictwem); nóż Erynda +3, a noże Miry +6 (łącznie z biegłością). Kara skazy Erynda zależy od sojuszników przy wybranym celu.

## Garran — Żelazna Straż — obrona pierwszej linii

PW 28 · KP 19 · ruch 30 stóp. SIŁ 18  ZRC 14  KON 15  INT 9  MDR 13  CHA 11.

### Zasoby i plan tury

- Taktyka: 4 punkty (modyfikator Siły); długi odpoczynek.
- Drugi oddech i Zryw akcji: po 1 użyciu; krótki lub długi odpoczynek.
- Pozycja obronna i Uderzenie tarczą: cały ruch, bez puli użyć.

1. Zajmij przejście i osłoń sojuszników; ustawienie tarczy jest twoją główną decyzją.
2. Przed ruchem wybierz Uderzenie tarczą albo Pozycję obronną; oba zużywają cały ruch.
3. Taktykę wydawaj na rozkazy i osłonę. Po wykonaniu akcji możesz użyć Zrywu akcji akcją dodatkową.

### Zdolności i skróty

| Klawisz | Zdolność | Koszt i warunki | Działanie |
|---|---|---|---|
| Q | Drugi Oddech | AKCJA DOD. · 1/ODPOCZYNEK | Odzyskaj 1k10 + poziom PW. |
| W | Zryw Akcji | AKCJA DOD. · 1/ODPOCZYNEK | Po wykonaniu akcji odzyskaj akcję. |
| E | Uderzenie Tarczą | CAŁY RUCH · PRZED RUCHEM · 5 STÓP | Sporny test Siły; wygrana: 1k4+SIŁ i odepchnięcie o wolne pole. Remis: obrońca. |
| R | Pozycja Obronna | AKCJA RUCHU | Rezygnujesz z ruchu: +2 KP do następnej tury lub do ruchu. |
| A | Rozkaz: Stać | AKCJA · 60 STÓP · 1 TAKTYKA | MDR ST 14: porażka blokuje ruch, sukces połowi. Naturalne 1: także -2 do ataków; 20: bez efektu. |
| S | Osłona Tarczą | BONUS · 1 TAKTYKA | Sąsiedni sojusznicy mają +2 KP do twojej następnej tury. |
| D | Mowa Dowódcy | AKCJA · 30 STÓP · 1 TAKTYKA | Usuń strach; przewaga przy pierwszym ataku, teście lub rzucie obronnym. |
| F | Osłona Towarzysza | AKCJA · 5 STÓP · 1 TAKTYKA | Pierwszy pojedynczy atak lub efekt na wybranego sojusznika trafia Garrana. |
| AUTO | Reakcje | GRA WYŚWIETLI PYTANIE | Gdy reakcja jest możliwa, wybierz ją w oknie i potwierdź Enterem. |

### Pasywy i skaza

- **Styl walki: Obrona:** +1 KP podczas noszenia pancerza.
- **Ulepszony krytyk:** ataki bronią trafiają krytycznie przy naturalnym 19 albo 20.
- **Żelazna linia:** sojusznik flankujący z Garranem tego samego przeciwnika ma +1 KP przeciw jego atakom.

**Skaza — Wyrzuty sumienia:** gdy Garran otrzymał najmniej obrażeń w drużynie, a ktoś otrzymał więcej, ma -2 do ataków, obron i testów. Leczenie nie cofa licznika.

## Brakka — Niszczycielka — obrażenia i wytrzymałość

PW 35 · KP 14 · ruch 30 stóp. SIŁ 18  ZRC 13  KON 16  INT 8  MDR 12  CHA 10.

### Zasoby i plan tury

- Szał: 3 użycia; długi odpoczynek.
- Dzikość: każdy Szał odnawia 3 punkty (modyfikator Kondycji); koniec Szału usuwa resztę.
- Nieustępliwość półorka: 1 użycie; długi odpoczynek.

1. Podejdź do przeciwnika i włącz Szał akcją dodatkową.
2. Lekkomyślny atak ułatwia trafienie, lecz wystawia cię na łatwiejszy odwet.
3. Dzikość wydawaj na Potężne uderzenie, Przyspieszenie, ryk albo reakcję Twarda jak skała.

### Zdolności i skróty

| Klawisz | Zdolność | Koszt i warunki | Działanie |
|---|---|---|---|
| Q | Szał | BONUS · 3/DŁUGI ODPOCZYNEK | Odnów 3 Dzikości; przewaga testów/obron SIŁ, +2 obrażeń wręcz i odporność na kłute/cięte/obuchowe. |
| W | Lekkomyślny Atak | AKCJA · ATAK WRĘCZ | Atak z przewagą. Ataki przeciw Brakce mają przewagę do jej następnej tury. |
| E | Potężne Uderzenie | AKCJA · SZAŁ · 2 DZIKOŚCI | Wykonaj atak wręcz z premią +10 do trafienia. |
| R | Z Bara | AKCJA · 5 STÓP | Próba Atletyki. Odepchnij 5 stóp + 5 za każde 5 punktów przewagi, maks. 30. |
| A | Przyspieszenie | BONUS · SZAŁ · 1 DZIKOŚCI | Podwój bazowy ruch Brakki w tej turze. |
| S | Ogłuszający Ryk | AKCJA · SZAŁ · STOŻEK 15 · 2 DZIKOŚCI | KON ST 15: 2k6 i brak ruchu; sukces pół. Naturalne 1: utrudnienie ataków; 20: brak obrażeń. |
| AUTO | Twarda Jak Skała | REAKCJA · SZAŁ · 1 DZIKOŚCI | Po odporności zmniejsz otrzymane obrażenia o 1k12+KON. |
| D | Chwyt | AKCJA · 5 STÓP · WOLNA RĘKA | Sporny test Atletyki przeciw Atletyce/Akrobatyce. Sukces zeruje ruch celu do uwolnienia. |

### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Obrona bez pancerza:** KP 10 + Zręczność + Kondycja; tarcza jest dozwolona.
- **Nieustępliwość półorka:** automatycznie przy pierwszym zejściu do 0 PW pozostawia Brakkę z 1 PW, o ile obrażenia nie zabijają jej natychmiast; 1 użycie na długi odpoczynek.
- **Dzikie ataki:** krytyczny atak bronią wręcz dodaje jedną kość broni.

**Skaza — Bitewny amok:** podczas Szału Brakka nie może używać mikstur, zwojów ani aktywnych właściwości przedmiotów. Może nadal atakować trzymaną bronią.

## Mira — Specjalistka — infiltracja i precyzyjne obrażenia

PW 21 · KP 15 · ruch 25 stóp. SIŁ 8  ZRC 19  KON 13  INT 14  MDR 12  CHA 11.

### Zasoby i plan tury

- Fortele: 4 punkty (modyfikator Zręczności); długi odpoczynek.
- Unik instynktowny: reakcja i 1 Fortel; nie ma osobnej puli.
- Atak z cienia: raz na turę; +1k6 flanka, +2k6 ukrycie, +3k6 razem.

1. Szukaj własnej flanki lub celu, który cię nie widzi; razem dają +3k6 raz na turę.
2. Ukryj się wykonuje nowy test Skradania przeciw osobnym testom Percepcji wrogów. Atak kończy ukrycie.
3. Oszczędzaj Fortele na specjalne ataki, Zasłonę dymną i Unik instynktowny.

### Zdolności i skróty

| Klawisz | Zdolność | Koszt i warunki | Działanie |
|---|---|---|---|
| D | Ukryj Się / Przerwij Skradanie | AKCJA / DARMOWE WYJŚCIE | Test Skradania przeciw Percepcji każdego wroga. Ukrycie: ruch 20 stóp; wyjście przywraca limit 25. |
| Q | Zasłona Dymna | AKCJA · RUCH 15 · 1 FORTEL | Bez ataków okazyjnych, potem Ukrycie nawet obok wroga. |
| W | Przeskok Przez Gardę | AKCJA · WRĘCZ | Jeśli pole za celem jest wolne: +2 do ataku i obrażeń, potem przejdź za cel. |
| E | Wykrycie Pułapek | AKCJA · PROMIEŃ 45 STÓP | Fizyczny test Percepcji wykrywa pułapki w walce. |
| R | Cięcie Ścięgna | AKCJA · FLANKA · 1 FORTEL | Po trafieniu wręcz prędkość celu spada o połowę aż do leczenia. |
| A | Przeszywający Atak | AKCJA · SOJUSZNIK PRZY CELU · 1 FORTEL | Po raniącym trafieniu rapierem zaatakuj osobno wroga dokładnie za pierwszym. Bez dalszego łańcucha. |
| S | Mistrzyni Ostrzy | AKCJA · NÓŻ Z UKRYCIA · 1 FORTEL | Cel, który cię nie widzi, po raniącym trafieniu krwawi 1k4 na początku tur do leczenia. |
| AUTO | Unik Instynktowny | REAKCJA · 1 FORTEL | Gdy widoczny wróg atakuje ukrytą Mirę, jego atak ma utrudnienie. |

### Pasywy i skaza

- **Mistrzyni ukrycia:** Ukryj się: akcja, bez osłony; blokuje je wróg w 5 stopach lub stan. Jeden test Skradania przeciw osobnej Percepcji wrogów; remis wykrywa Mirę.
- **Skradanie:** limit ruchu 20 stóp. Dobrowolne wyjście przywraca limit 25 stóp, ale nie zwraca wykonanego ruchu ani akcji.
- **Atak z cienia:** Raz na turę rapier lub nóż daje +2k6 i przewagę przeciw celowi, który nie widzi Miry; własna flanka daje +1k6, oba warunki +3k6. Atak kończy ukrycie.
- **Szczęście niziołka:** ponów naturalną 1 w ataku, teście albo obronie.
- **Ruchomy cel:** Mira ma +2 KP przeciw dystansowym testom ataku bronią i czarem; nie działa przeciw obszarom ani rzutom obronnym.
- **Ekspertyza:** Podwójna premia z biegłości w wybranych umiejętnościach; jest już wliczona w ich modyfikatory.

**Skaza — Panika po zdemaskowaniu:** podczas tej sesji skradania widzący Mirę wróg ma +2 do testów ataku przeciw niej. Gdy widzą ją wszyscy, skradanie się kończy i premia znika.

## Dagna — Uzdrowicielka — leczenie i wzmocnienia

PW 30 · KP 16 · ruch 25 stóp. SIŁ 13  ZRC 10  KON 16  INT 8  MDR 18  CHA 12.

### Zasoby i plan tury

- Komórki czarów: 4 pierwszego i 2 drugiego poziomu; długi odpoczynek.
- Boska Moc: 1 użycie wspólne dla Zachowania życia i Odpędzania nieumarłych; krótki odpoczynek.
- Koncentracja: jedna aura lub inny efekt naraz; Krok ratowniczki najwyżej raz na turę Dagny.

1. Utrzymuj sojuszników w zasięgu wybranej aury i pilnuj koncentracji.
2. Słowo leczenia podnosi rannych na odległość; Boską Moc zachowaj na ciężkie obrażenia lub nieumarłych.
3. Po pomocy pobliskiemu sojusznikowi skorzystaj z Kroku ratowniczki, gdy gra go zaproponuje.

### Zdolności i skróty

| Klawisz | Zdolność | Koszt i warunki | Działanie |
|---|---|---|---|
| Q | Święty Płomień | AKCJA · STOŻEK 15 · ZRC ST 14 · SZTUCZKA | Wrogowie odnoszą 1k8 obrażeń od blasku przy porażce. |
| W | Słowo Leczenia | BONUS · 60 STÓP · KOMÓRKA 1+ | Wybrany cel odzyskuje 1k4+7 PW. |
| E | Błogosławieństwo | AKCJA · AURA 10 · KONC. · 5 RUND · KOMÓRKA 1+ | Ty i sojusznicy w aurze dodajecie 1k4 do ataków i rzutów obronnych. |
| R | Zachowanie Życia | AKCJA · 1 BOSKA MOC | Rozdziel 15 PW między cele; nie lecz powyżej połowy maks. PW. |
| A | Aura Boskiej Opieki | AKCJA · AURA 5 · KONC. · 5 RUND · KOMÓRKA 1+ | Wrogowie w aurze mają -2 do ataków i obrażeń. |
| S | Naprowadzający Pocisk | AKCJA · 75 STÓP · ATAK CZAREM · KOMÓRKA 1+ | 2k6 blasku; następny atak przeciw celowi ma przewagę. |
| D | Aura Uzdrawiającej Łaski | AKCJA · AURA 10 · KONC. · 3 RUNDY · KOMÓRKA 2+ | Cztery pierwsze leczenia w aurze zyskują +1k8+MDR. |
| F | Pomniejsze Przywrócenie | AKCJA · DOTYK · KOMÓRKA 2+ | Usuń jedną obsługiwaną negatywną kondycję. |
| T | Odpędzanie Nieumarłych | AKCJA · BOSKA MOC 1 · 30 STÓP | Nieumarli wykonują obronę MDR ST 14; porażka odpędza. Dostępne tylko przy legalnym celu. |
| Z | Duchowa Broń | BONUS · 60 STÓP · KOMÓRKA 2+ | Przywołaj broń: ruch 20, atak sąsiedni 1k8+4, KP 18. |

### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Krasnoludzki ruch:** Ciężki pancerz nie zmniejsza szybkości Dagny z powodu niewystarczającej Siły.
- **Uczeń Życia:** Czar leczenia poziomu 1 lub wyższego przywraca dodatkowo 2 + poziom użytej komórki PW.
- **Krok ratowniczki:** Raz na turę Dagny, po leczeniu lub zdjęciu negatywnego stanu innego sojusznika w 10 stopach: ruch 5 stóp bez kosztu ruchu, reakcji i ataków okazyjnych.
- **Krasnoludzka wytrzymałość:** +1 maksymalnego PW na każdy poziom.
- **Krasnoludzka odporność:** przewaga przeciw truciźnie i odporność na obrażenia od trucizny.

**Skaza — Nikogo nie zostawiam:** Żywy sojusznik z 0 PW w 30 stopach: utrudnienie ataków i testów poza ratunkiem; cele wrogich czarów Dagny mają przewagę w obronach.

## Lorian — Bard-wynalazca — kusza, kontrola i improwizacja

PW 24 · KP 13 · ruch 30 stóp. SIŁ 8  ZRC 15  KON 14  INT 12  MDR 10  CHA 19.

### Zasoby i plan tury

- Inspiracja bardowska: 4 użycia (modyfikator Charyzmy), kość k6; krótki odpoczynek.
- Komórki czarów: 4 pierwszego i 2 drugiego poziomu; długi odpoczynek.
- Techniki kuszy, Kontrapunkt i Rozpraszający okrzyk nie zużywają Inspiracji. Improwizacja: raz na NPC.

1. Stań w 10 stopach od przytomnego sojusznika, aby móc używać zdolności specjalnych.
2. Wybierz dwa zwykłe strzały, Lunetę optyczną albo ostrzał odpowiadający sytuacji.
3. Inspiruj sojusznika przed ważnym rzutem; reakcje Kontrapunktu i Rozpraszającego okrzyku gra proponuje sama.

### Zdolności i skróty

| Klawisz | Zdolność | Koszt i warunki | Działanie |
|---|---|---|---|
| Q | Inspiracja Bardowska | BONUS · 60 STÓP | Sojusznik zachowuje 1k6 do testu, ataku lub rzutu obronnego. |
| W | Luneta Optyczna | AKCJA · CAŁY RUCH · 60 STÓP | Przed ruchem: dwa strzały w jeden cel, jego KP jest niższe o 2. |
| E | Ostrzał Destabilizujący | AKCJA · 45 STÓP | Trafienie: utrudnienie pierwszego ataku celu i jego rzutów MDR. |
| R | Prowokujący Ostrzał | AKCJA · 45 STÓP | Cel zyskuje premię przeciw Lorianowi, lecz karę przeciw innym równą obrażeniom. |
| A | Oplatający Ostrzał | AKCJA · OBSZAR 3×3 · 45 STÓP | Wszyscy w obszarze: ZRC; sukces pół ruchu, porażka brak ruchu. |
| S | Podszept Paniki | AKCJA · 45 STÓP · MDR ST 14 · KOMÓRKA 1+ | 2k6 psychicznych i ruch 15 stóp od Loriana; sukces: połowa. |
| D | Fala Gromu | AKCJA · SZEŚCIAN 15 · KON ST 14 · KOMÓRKA 1+ | 2k8 grzmotu i odepchnięcie 10 stóp; sukces: połowa bez odepchnięcia. Także sojusznicy. |
| F | Baśniowy Ogień | AKCJA · SZEŚCIAN 20 · KONC. · KOMÓRKA 1+ | ZRC: porażka daje przewagę atakującym i blokuje niewidzialność. |
| Z | Ohydny Śmiech | AKCJA · 30 STÓP · KONC. · MDR ST 14 · KOMÓRKA 1+ | Porażka: cel pada i jest obezwładniony. |
| X | Rozkaz Sceniczny | AKCJA · 45 STÓP · MDR ST 14 · KOMÓRKA 2+ | Podejdź/odejdź/milcz; ruch do 15 stóp. Cel odporny na mowę: 1k6 psychicznych bez save, zamiast rozkazu. |
| C | Przyspieszony Refren | AKCJA · KONC. · 3 RUNDY · KOMÓRKA 2+ | Przy rzuceniu jeden strzał; potem bonus daje trzeci strzał salwy. |
| AUTO | Kontrapunkt / Okrzyk / Cięte Słowa | REAKCJE · PYTANIE NA EKRANIE | Reakcje: strzał po zranieniu przez inspirowanego sojusznika, redukcja 1k6+2 lub odjęcie k6 od rzutu. Bez kosztu Inspiracji. |

### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Fey Ancestry:** przewaga przeciw zauroczeniu i odporność na magiczny sen.
- **Kusznik:** zwykła akcja Ataku kuszą ręczną daje dwa osobne strzały; każdy może mieć inny legalny cel. Ostrzały specjalne określają własną liczbę celów.
- **Obycie i targowanie:** +2 do każdego pozabojowego testu Charyzmy. Nie tworzy nowych nagród ani możliwości fabularnych.
- **Improwizacja:** raz na NPC przerzuć nieudany pozabojowy test Charyzmy przed konsekwencjami; drugi wynik jest ostateczny. Zużycie jest zapisywane.

**Skaza — Potrzeba publiczności:** Zdolności specjalne wymagają żywego, przytomnego i nieobezwładnionego sojusznika w 10 stopach. Zwykłe ataki i czary pozostają dostępne.

## Nimra — Kontrolerka magiczna — teren i wiedza

PW 20 · KP 12 · ruch 25 stóp. SIŁ 8  ZRC 14  KON 14  INT 19  MDR 12  CHA 10.

### Zasoby i plan tury

- Komórki czarów: 4 pierwszego i 2 drugiego poziomu; długi odpoczynek.
- Punkty Metamagii: 4 (modyfikator Inteligencji); długi odpoczynek.
- Odzyskiwanie magiczne: raz na długi odpoczynek, podczas krótkiego odzyskaj łącznie 2 poziomy komórek.

1. Wybierz czar i jego obszar; opcjonalną Metamagię wybierz przed czarem.
2. Sprawdź pola sojuszników: obszary i Piorunowy szlak mogą ich objąć.
3. Zmieniaj czary i Metamagię między rundami; Echo blokuje powtórzenie wyboru z poprzedniej rundy.

### Zdolności i skróty

| Klawisz | Zdolność | Koszt i warunki | Działanie |
|---|---|---|---|
| T | Rzeźbienie Pola | 1 PUNKT | Wyklucz z obszaru czaru do 4 pól. |
| Y | Odległy Czar | 1 PUNKT | +15 stóp zasięgu, maksymalnie 75. |
| U | Przeciążony Czar | 1 PUNKT | Dodaj jedną bazową kość obrażeń. |
| G | Wymuszony Splot | 2 PUNKTY | Jeden cel ma utrudnienie pierwszego rzutu obronnego. |
| H | Transmutacja Energii | 1 PUNKT | Zmień typ: kwas, zimno, ogień, błyskawice lub grzmot. |
| Q | Lodowy Impuls | AKCJA · 50 STÓP · KON ST 14 · SZTUCZKA | 1k8 zimna i -10 stóp ruchu przy porażce. |
| W | Kwasowy Rozprysk | AKCJA · 40 STÓP · PROMIEŃ 5 · SZTUCZKA | ZRC: 1k6 kwasu przy porażce. |
| E | Szpilka Umysłu | AKCJA · 45 STÓP · MDR ST 14 · SZTUCZKA | 1k6 psychicznych i brak reakcji przy porażce. |
| R | Wachlarz Płomieni | AKCJA · STOŻEK 15 · ZRC ST 14 · KOMÓRKA 1+ | 2k6 ognia; sukces: połowa. |
| A | Fala Odrzutu | AKCJA · LINIA 30 · SIŁ ST 14 · KOMÓRKA 1+ | 2k6 mocy i odepchnięcie 5 stóp; sukces: połowa. |
| S | Lepka Matryca | AKCJA · 50 · OBSZAR 10 · 3 RUNDY · KOMÓRKA 1+ | Trudny teren; ZRC przy wejściu/starcie, porażka przewraca. |
| J | Mglisty Krok | BONUS · TELEPORT 30 STÓP · KOMÓRKA 2+ | Wybierz wolne pole w zasięgu. |
| D | Sen | AKCJA · 50 STÓP · KOMÓRKA 1+ | Pula 5k8 usypia cele od najniższych PW. |
| F | Mgła | AKCJA · 50 · PROMIEŃ 15 · KONC. · KOMÓRKA 1+ | Obszar jest całkowicie zasłonięty. |
| Z | Sieć | AKCJA · 50 · SZEŚCIAN 20 · KONC. · KOMÓRKA 2+ | Trudny teren; ZRC przy porażce unieruchamia. |
| X | Piorunowy Szlak | AKCJA · 60 STÓP · ZRC ST 14 · KOMÓRKA 2+ | 3k6/połowa. Jeden przeskok do najbliższej istoty w 15 stopach, także sojusznika; remis preferuje wroga. |
| C | Załamanie Woli | AKCJA · 50 · PROMIEŃ 10 · MDR ST 14 · KOMÓRKA 2+ | 2k6, brak reakcji i utrudnienie pierwszego ataku; sukces połowa. |
| V | Staza Istoty | AKCJA · 50 · KONC. · MDR ST 14 · KOMÓRKA 2+ | Ruch 0 i brak akcji ruchu; ponawiany rzut, maks. 3 rundy. |
| K | Roztrzaskanie | AKCJA · OBSZAR · KON ST 14 · KOMÓRKA 2+ | 3k8 grzmotu; sukces: połowa. |

### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Gnomia przebiegłość:** przewaga w obronach INT, MĄD i CHA przeciw magii.
- **Katalog niemożliwego:** wszystkie czary z talii są stale dostępne; Nimra nie przygotowuje ich po odpoczynku.
- **Odzyskiwanie magiczne:** Raz na długi odpoczynek, podczas krótkiego odzyskaj komórki o sumie poziomów do połowy poziomu czarodziejki, w górę (obecnie 2).

**Skaza — Echo magicznego wycieku:** W danej rundzie nie możesz powtórzyć czaru ani opcji Metamagii użytych w poprzedniej rundzie. Anulowanie podglądu nie wywołuje Echa.

## Erynd — Zwiadowca — tropienie i ostrzał

PW 25 · KP 16 · ruch 30 stóp. SIŁ 12  ZRC 19  KON 13  INT 11  MDR 14  CHA 8.

### Zasoby i plan tury

- Instynkt: 4 punkty (modyfikator Zręczności); długi odpoczynek.
- Podwójny strzał: 2 Instynktu; pozostałe strzały i czary talii po 1.
- Celowanie zużywa cały ruch; Zwiadowcza mobilność akcję dodatkową. Nie mają puli użyć.

1. Wybierz linię strzału i cel, obok którego stoi jak najmniej sojuszników.
2. Przed ruchem zdecyduj, czy zużyć go na Celowanie; Zwiadowcza mobilność pomaga utrzymać dystans.
3. Instynkt wydawaj na Znak łowcy, strzały kontroli lub teren. Po pokonaniu celu przenieś Znak bez kosztu.

### Zdolności i skróty

| Klawisz | Zdolność | Koszt i warunki | Działanie |
|---|---|---|---|
| Q | Znak Łowcy | BONUS · KONC. · 1 INSTYNKT | +1k6 obrażeń bronią. Po pokonaniu celu przeniesienie jest darmowe. |
| W | Zwiadowcza Mobilność | BONUS | Wybierz: Sprint albo Odstąpienie. |
| E | Celowanie | CAŁY RUCH · PRZED RUCHEM | Następny atak długim łukiem ma przewagę. |
| R | Strzała Kotwicząca | AKCJA · 1 INSTYNKT · RZUT 1K4 | Trafienie: SIŁ ST 14; blokada ruchu albo pół ruchu przez wynik rund. |
| A | Strzała Odsłaniająca | AKCJA · 1 INSTYNKT · RZUT 1K8 | Trafienie obniża KP celu o wynik do następnej tury Erynda. |
| S | Strzała Zakłócająca | AKCJA · 1 INSTYNKT | Trafienie odbiera reakcje i utrudnia następny atak celu. |
| D | Podwójny Strzał | AKCJA · 2 INSTYNKTU | Jeden test: 2k8 + 2×ZRC. Znak i Pierwsza krew tylko raz; krytyk podwaja wyłącznie bazowe kości. |
| F | Mglisty Krok | BONUS · 1 INSTYNKT | Teleportuj się na wybrane wolne pole. |
| Z | Kolczaste Zarośla | AKCJA · 1 INSTYNKT | Utwórz niebezpieczny trudny teren w wybranym obszarze. |

### Pasywy i skaza

- **Widzenie w ciemności:** W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.
- **Styl walki: Łucznictwo:** +2 do dystansowych ataków bronią; premia jest już wliczona w atak na arkuszu.
- **Ekspertyza zwiadowcy:** podwójna biegłość w Skradaniu i Sztuce przetrwania.
- **Pierwsza krew:** Raz na turę trafienie długim łukiem w cel z pełnymi PW zadaje dodatkowe 1k8. Inne bronie nie otrzymują tej premii.
- **Czujność zwiadowcy:** +2 do inicjatywy i testów wykrywania ukrytych przeciwników; premia nie dotyczy pułapek.
- **Fey Ancestry:** przewaga przeciw zauroczeniu i odporność na magiczny sen.

**Skaza — Trauma bratobójczego strzału:** -1 do ataku długim łukiem za przytomnego bohatera drużyny w 5 stopach od celu. Pomija Erynda, pokonanych, przywołania i NPC; nie działa na nóż.

## Aktualne wydruki

Kolorowe: `assets/physical_cards/character_sets/keyboard_v1/pdf/keyboard_character_sheets_v1.pdf`.
Oszczędne: `assets/physical_cards/character_sets/keyboard_v1/minimal_bw/pdf/minimal_bw_character_sheets_v1.pdf`.
Każdy zestaw zawiera siedem par: skróty i dossier. Manifest w `keyboard_v1/keyboard_character_cards_v1.json` wiąże skróty ze stabilnymi identyfikatorami zdolności.

# Karty v0.2 — ładunki i ciągły Rezonans

Aktualizacja 29.09.2026. Najnowsze ustalenia użytkownika zastępują wcześniejszą
paczkę bonusów działającą tylko na moc i ochronę wygasającą na początku następnej tury.
**Specyfikacja do przyszłego wdrożenia: [ciągły Rezonans](RESONANCE_RUNTIME_SPEC.md).**
Starszy [dokument kierunkowy](../system_run_v0.2_ladunki_i_rezonans.md) pozostaje
historyczny; w razie rozbieżności obowiązuje nowa specyfikacja i katalog.

[Spis materiałów](../content/scenarios/misja_0_dzwon/print/runy_ladunki_v02/index.html) ·
[Komplet PDF](../content/scenarios/misja_0_dzwon/print/runy_ladunki_v02/karty_postaci_A4.pdf).
Poprzednie adresy `runy_v01/index.html` i `runy_koszyki_v01/index.html`
prowadzą do tego samego aktualnego zestawu.

## Rzuty i ST bez premii biegłości

W obecnym kierunku nie dodajemy premii biegłości do rzutów bohaterów.
Rzut: k20 + modyfikator właściwej cechy + odpowiednie aktywne premie (np. Oko).
ST mocy: **10 + modyfikator cechy wskazanej na karcie**. Oko nie zwiększa ST.
Stała 10 zastępuje dawny zapis 8 + biegłość (+2 u obecnych bohaterów), więc
korekta nie zmienia ich aktualnych liczbowych ST. Nie przywraca dawnych premii
od poziomu naładowania. Biegłość jako uprawnienie do sprzętu jest odrębną sprawą.
Źródło stałej dla wydruku i wyliczeń: `rules.save_dc_base` w katalogu kart.
Na kartach pozostaje formuła, np. **ST 10 + Siła**, a nie bieżący wynik
ST 14. Nazwy cech w efektach oznaczają modyfikatory. Generator nie podstawia
aktualnej cechy bohatera; rozwój postaci nie dezaktualizuje wydrukowanego ST.

## Granice etapu

Zmieniono katalog, legendy, karty i PDF-y. Mechanika ciągłego Rezonansu
**nie jest jeszcze wdrożona w działającej walce ani makiecie**. Nie zmieniono
wejścia planszy, położenia symboli ani eksploracji. Najpierw omawiamy postaci,
potem wdrażamy walkę na bazie wcześniejszej makiety `docs/ui/prototype.html`.

## Ustalenia wspólne

- Każdy bohater zaczyna z 20/20 jednorodnych ładunków; gracz używa pokrętła,
  a docelowa aplikacja ma pokazywać ich aktualną liczbę.
- Podstawowa moc: 4; wzmocniona: 8 łącznie. To bieżące ceny robocze, przed skazą.
- Ruch + zwykły atak albo przedmiot + jedna specjalna; A+S zajmuje także zwykły atak.
- M+S: specjalna i cały ruch; Szarża bastionu wymaga pełnej puli i braku
  wcześniejszego ruchu w turze. Atak pozostaje dostępny.
- Skupienie (Spirala): specjalna, koszt 0, odzysk 1k20 do 20. Natychmiast kończy Rezonans.
- Odzysk klasowy: dwa warunki, jeden wspólny limit 1k4 na rundę na bohatera.
- Zatwierdzony tryb wzmocniony dodaje runę i jej bonus **przed** wykonaniem mocy.
- Bohater dołącza na początku swojej tury, zachowuje premie poza nią;
  bohater czekający na pierwszą turę w danym łańcuchu jeszcze ich nie ma.
- Zwykłe działania także mogą korzystać z premii. Grot obejmuje wszystkie
  obrażenia źródłowego uczestnika, Oko wszystkie jego k20 i nie zwiększa ST.
- Moc podstawowa kończy Rezonans po rozpatrzeniu, w tym po przeniesieniach Haka.
  Brak mocy kończy go z końcem tury; tury wrogów i granica rundy nie przerywają.
- Zakończenie usuwa wszystkie premie czasowe, dodatkowe liczniki oraz Węzeł u wrogów.
  Nie cofa otrzymanego leczenia, obrażeń ani wykonanego ruchu.
- Brak zasięgu, kosztu reakcji i limitu długości Rezonansu.
- Fala wymaga uporządkowanego toru: powiela jedną kopię bonusu poprzedniej runy.
- Błysk działa na początku **własnej tury**, zgodnie z przykładem użytkownika,
  a nowy Błysk w tej turze daje jedną dodatkową kość.

## Bonusy run na kartach

| Runa | Opis |
| --- | --- |
| Wieża | Od dołączenia do Rezonansu masz +1 KP za każdą aktywną Wieżę. Premia działa także poza twoją turą. Koniec Rezonansu usuwa ją u wszystkich uczestników; bohater przed swoją pierwszą turą w tym łańcuchu jej nie ma. |
| Grot | Gdy jesteś objęty Rezonansem, każde zdarzenie obrażeń pochodzących od ciebie otrzymuje +1k4 za każdy Grot, na każdy cel. Także zwykłe ataki, reakcje i obrażenia okresowe. Premia ma typ obrażeń źródła i nie uruchamia kolejnej premii Grota. Znika z końcem Rezonansu. |
| Schody | Na początku swojej tury otrzymujesz 2 dodatkowe punkty ruchu za każde Schody. Dodanie Schodów w tej turze daje kolejne 2. To zwykły ruch: trudny teren, blokady i ataki okazyjne obowiązują. Koniec Rezonansu usuwa niewykorzystaną premię; nie cofa ruchu. |
| Błysk | Na początku swojej tury w Rezonansie odzyskaj 1k4 PW za każdy Błysk. Gdy w tej turze dodasz kolejny Błysk, od razu rzuć dodatkowe 1k4; nie powtarzaj wcześniejszych kości. Leczenie do maksimum PW. Koniec Rezonansu zatrzymuje kolejne leczenia, nie cofa odzyskanych PW. |
| Hak | Po obrażeniach przenieś każdy legalny cel raz, na dowolne legalne pole do N pól od jego pozycji, gdzie N to liczba Haków. Możesz zostawić go w miejscu. Najpierw wszystkie obrażenia z Grotem, potem cele kolejno: pole → podgląd → zatwierdź. Więcej Haków zwiększa dystans, nie liczbę przeniesień. |
| Oko | Od dołączenia do Rezonansu masz +1 do wszystkich własnych rzutów k20 za każde Oko, także poza swoją turą. Nie zwiększa ST, obrażeń ani naturalnego wyniku kości. Przy przewadze lub utrudnieniu premię dodaj raz do wybranego wyniku. Koniec Rezonansu usuwa premię. |
| Kielich | Osobny licznik: 2 tymczasowe PW za Kielich, zużywane przed zwykłymi PW. Utrata choć 1 tymczasowego PW liczy się jako otrzymanie obrażeń i uruchamia odpowiednie efekty. Kolejna tura nie odnawia zużytej puli. Koniec Rezonansu usuwa ten licznik, bez zmiany zwykłych PW. |
| Węzeł | Każdy przeciwnik ma spowolnienie równe liczbie Węzłów: −1 pole zwykłego ruchu za kopię, minimum 0, po innych zmianach limitu. Bez trafienia, obrażeń ani rzutu obronnego. Działa przez cały Rezonans, także na nowych wrogów; jego koniec usuwa spowolnienie. |
| Fala | Fala zwiększa o 1 liczbę kopii bonusu poprzedniej runy na torze; nie podwaja całej jej puli. Wieża → Fala daje 2 Wieże. Kolejna Fala powtarza ten sam bonus; przy pustym torze nie ma czego powtórzyć. Powielony bonus działa i wygasa według zasad swojej runy. |
| Klepsydra | Osobny licznik osłony: 2 punkty za Klepsydrę. Zapobiega obrażeniom oprócz umysłowych (psychicznych), przed tymczasowymi i zwykłymi PW. Całkiem pochłonięte obrażenia nie uruchamiają efektów po zadaniu obrażeń. Pula zużywa się między trafieniami; nie odnawia co turę i znika z końcem Rezonansu. |

Wartości liczbowe są nadal do testu. Klepsydra zachowuje robocze 2 punkty/kopię,
a Schody +2 punkty ruchu/kopię. Przypadki Fala→Fala i Fala na pustym torze,
wzrost premii wcześniejszych uczestników oraz przyrost zużywalnych pul
są jawnie oznaczone jako doprecyzowania robocze w specyfikacji.

## Przesunięte zestawy

Ciąg: Wieża → Grot → Schody → Błysk → Hak → Oko → Kielich → Węzeł → Fala → Klepsydra.
Każda kolejna postać zaczyna o jedną pozycję dalej: cztery runy, Nimra pięć.
To dobór kart, nie inicjatywa ani nowe rozmieszczenie przycisków.
Spirala jest osobnym Skupieniem; dziewięć pozostałych run panelu to rezerwa rozwoju.

| Bohater | Moce |
| --- | --- |
| Garran | Wieża: Impuls egidy; Grot: Ostrze przełamania; Schody: Szarża bastionu; Błysk: Żar odnowy. |
| Brakka | Grot: Gniew runy; Schody: Pęd gromu; Błysk: Runiczny szał; Hak: Echo gromu. |
| Mira | Schody: Parkour; Błysk: Całun cienia; Hak: Więzy mroku; Oko: Ostrze zmierzchu. |
| Dagna | Błysk: Tchnienie życia; Hak: Płomień świtu; Oko: Pieczęć łaski; Kielich: Krąg odnowy. |
| Lorian | Hak: Dysonans; Oko: Hymn odwagi; Kielich: Akord odnowy; Węzeł: Pieśń przejścia. |
| Nimra | Oko: Fala uderzeniowa; Kielich: Strefa ognia; Węzeł: Groty eteru; Fala: Mglisty krok; Klepsydra: Tarcza splotu. |
| Erynd | Kielich: Bliźniacze groty; Węzeł: Więzy korzeni; Fala: Strzała wichru; Klepsydra: Piętno łowcy. |

Przegląd kart obejmuje Garrana (27.09) i pozostałych bohaterów (29.09).
Erynd został zaakceptowany bez zmian. Koszty i przypisania run pozostają.
Źródło kart: `content/print/rune_charges_v02/catalog.json`.

## Brakka, Mira, Dagna, Lorian i Nimra — 29.09

- Brakka: Zaciekłość dodaje dwie dodatkowe kości broni przy krytyku zamiast
  jednej. Runiczny szał daje +1k6 bronią wręcz i połowę otrzymywanych obrażeń
  obuchowych, kłutych i ciętych; trwa Siła + Kondycja własnych tur.
  Pęd gromu pozostaje; Echo gromu ma ST 10 + Siła.
- Mira: Cios z zaskoczenia daje 1k6 z flanki z sojusznikiem albo ukrycia
  przed celem. Ostrze zmierzchu wymaga niewidzącego jej celu, daje przewagę
  i ujawnia po ataku. Całun jest testem Zręczności, bez wymogu osłony.
  Parkour prowadzi do dowolnego wolnego pola przy wrogu do 4 pól, ignoruje
  przeszkody i figurki wrogów; okazyjne zależą od ukrycia przed każdym wrogiem.
  Więzy mroku dopuszczają każdą broń wręcz; trafienie połowi ruch, a z ukrycia
  dodatkowo blokuje ruch w następnej rundzie.
- Dagna: Płomień świtu drukuje ST 10 + Mądrość.
- Lorian: usunięty wyjątek treningowy skazy, Dysonans ze ST 10 + Charyzma.
  Hymn daje 1k6 do wybranego k20, także po porażce; pozostaje do wykorzystania,
  bez limitu czasu, najwyżej jeden niewykorzystany Hymn na bohatera.
- Nimra: Precyzyjny splot zawiera wybór pola stworzenia albo „Nie pomijaj”.
  Fala uderzeniowa ma ST 10 + Inteligencja. Strefa ognia zastępuje Wachlarz:
  kwadrat 3×3, wskazanie środka do 6 pól, ST 10 + Inteligencja.

Dokładna obsługa wyborów, reakcji, stanów i zapisów jest w
[notatkach do implementacji](RESONANCE_RUNTIME_SPEC.md#przegląd-pozostałych-bohaterów--29092026).
Zmiany obejmują karty i dokumentację; wdrożenie mechaniki jest następnym krokiem.

## Przegląd Garrana i układ wszystkich kart — 27.09

Żywa osłona nadaje sąsiednim przytomnym sojusznikom stan +1 KP, gdy Garran
trzyma tarczę; stan znika po utracie warunku. Usunięto uwagę o kilku osłonach.
Drugi warunek odzysku to pudło przeciwnika w Garrana, zamiast obrażeń Impulsu.
Impuls egidy po wygranej odrzuca na wybrane legalne pole odległe o 1 od celu,
z podglądem i akceptacją. Ostrze przełamania dodaje 1k6 obrażeń magicznych.
Szarża bastionu zastępuje Ścieżkę przysięgi: M+S, wybór osiągalnego wroga,
niebieski podgląd najbliższego legalnego pola przy nim i zużycie całego ruchu.
Obrona Kondycji celu: ST 10 + mod. Siły + przebyte pola. Porażka: Powalony;
wręcz przeciw niemu z przewagą, dystansowo −2; utrata następnego ruchu.
Żar odnowy pozostaje bez zmian. Pełny przepływ, stany i przypadki akceptacyjne
są w [specyfikacji walki](RESONANCE_RUNTIME_SPEC.md#przegląd-garrana--27092026).

Każdy bohater otrzymał scenkę zamiast sekcji „Cel osobisty” na stronie 1.
Pasyw i odzysk mają większe nagłówki, osobny znak kości i rozdzielone warunki.
Usunięto wspólny długi dopisek o limitach odzysku. Limit 1k4 raz na rundę
pozostaje w katalogu i zasadach ogólnych. Na pionowej stronie 2 jest jedno
puste miejsce na kartę celu, z pięcioma okręgami postępu po prawej.
Cele do realizacji będą opracowane osobno; ramka nie narzuca treści ani nagród.

## Liczniki i Hak w przyszłym UI

Przykład: `PW 15/20 · Kielich 2/2 · Klepsydra 2/2`.
Kielich przyjmuje obrażenia przed zwykłymi PW; utrata choć jednego tymczasowego
PW uruchamia odpowiednie efekty po zadaniu obrażeń. Klepsydra zapobiega
obrażeniom: pełne pochłonięcie nie uruchamia tych efektów. Obrażenia umysłowe
omijają Klepsydrę. Kolejne początki tury nie odnawiają zużytych liczników.

Hak: najpierw wszystkie obrażenia z Grotem, potem kolejka legalnych celów.
Plansza podświetla pola do N od celu oraz jego obecne pole; kliknięcie wybiera
podgląd w innym kolorze, kolejny klik go zmienia, akceptacja zatwierdza.
Cele rozpatrujemy pojedynczo i przeliczamy zajętość po każdym zatwierdzeniu.
Dwa Haki oznaczają jeden wybór do dwóch pól, nie dwa przeniesienia.
Pełne przypadki obrażeń, anulowania i zapisu kolejki: [specyfikacja](RESONANCE_RUNTIME_SPEC.md).

## Panel i wydruk

Panel 30 pól: 0–3 podstawowe, 4 przerwa, 5–24 runy, 25 Gwiazda informacji,
26 plus, 27 minus, 28 akceptacja, 29 powrót. Indeksy od zera.
W tej korekcie **mapowanie ani mapa nie zmieniają się**.

35 stron A4, po 3 planszetki i 2 wycinanki:

1. Postać: portret, historia, scenka, statystyki, skaza, pasyw i odzysk.
2. Pionowa mata: moce u góry; poniżej jedna ramka celu i tor pięciu pól po prawej.
3. Mata wyposażenia.
4. Wycinanki mocy i bonusy wszystkich dziesięciu run.
5. Wycinanki wyposażenia.

Brak toru ładunków na pierwszej stronie. „Wzm.” z symbolem w podwójnej otoczce
oznacza bonus Rezonansu, zwykły symbol wskazuje przycisk mocy.
Druk monochromatyczny, jednostronny, 100%. Zdolności i cele 60×54 mm;
sprzęt 60×42 mm. Wszystkie strony są pionowe.
Generator kontroluje w Chrome przepełnienia, rozmiary, obrazy i liczbę stron.
Odbudowa kart: `PYTHONPATH=src .venv/bin/python scripts/build_rune_charges.py`.
`--maps` dodaj tylko przy zmianie mapy, `--html-only` daje sam podgląd.

## Weryfikacja i następny etap

Testy katalogu i wydruku: `tests/unit/test_rune_charge_cards.py`, przez
`scripts/safe_pytest.sh --timeout 60`. Kontrola wszystkich siedmiu zestawów
oraz 35 stron PDF. Testy nie weryfikują przyszłej mechaniki w silniku — jej
przypadki akceptacyjne są zapisane w specyfikacji do późniejszej implementacji.
Następny krok: wdrożenie walki według zapisanych reguł i przepływów UI.

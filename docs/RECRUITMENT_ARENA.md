# Arena — prowadzony samouczek postaci

## Eksploracja i pułapki — wdrożone 2026-09-14

Pod wyborem ćwiczeń walki dodano sekcję **Rozmowy i obiekty**. Każda postać
ma **Porozmawiaj z NPC**, **Interakcja z obiektem** i **Pułapka w walce**.
Objaśnienie Nessy → setup → normalny silnik → wynik. Dobór/pas, duplikaty,
21, utrudnienie po przekroczeniu i trzy przeszkody mają praktyczne lekcje.
Podstawy zalicza się raz wspólnie; własne metody i samodzielne sceny osobno.
Lorian ma lekcję przerzutu, a Erynd rzeczywistą premię +2 do obiektu.

Pułapka z atramentem używa normalnych testów MDR/ZRĘ i akcji podczas walki;
bez dobierania do 21. Kurs zachowuje istniejące zaliczenia combatu. Nowe id
lekcji i zapis faz są odrębne od dawnych indeksów. Wczytanie doboru wymaga
potwierdzenia fizycznych stosów. [Szczegóły wdrożenia](EXPLORATION_MANA_IMPLEMENTATION.md).

## Aktualny przebieg — 2026-09-11

Wejście: menu główne → arena → wybrana postać. Domyślny tryb API i panelu
nazywa się `walkthrough`. Każda postać przechodzi uporządkowane ćwiczenia,
a następnie samodzielny pojedynek. Nie ustawiamy figurki Nessy: jest narratorką.
Teren (zasłona, filar, skrzynie, osłona i gruz) pozostaje na tych samych polach.
Mapa SVG przedstawia teren; aktualne ustawienie figurek wskazuje plansza.

1. Osobne okno przedstawia zdolność: narrację Nessy, runę, symbole kosztu
   i dokładną mechanikę. Ogólne zasady kursu pojawiają się tylko przy pierwszym
   wprowadzeniu. ✓ zamyka opis i rozpoczyna ustawianie, bez zaliczania jego kroku.
2. Pierwsze przygotowanie prowadzi przez teren i figurki. W kolejnych
   sytuacjach zdejmij poprzednich pomocników, kukły i przywołane istoty;
   ustaw tylko wskazane figurki. Każdy krok potwierdzasz niebieskim ✓.
   Dotyczy to również ponowienia pierwszej lekcji i zmiany postaci. Teren
   uznajemy za gotowy dopiero po zakończeniu pierwszego setupu. Bieżące
   polecenie dostaje fokus pod nagłówkiem, a mapa i opcje pozostają zwinięte.
3. Po setupie pojawia się krótkie polecenie; ✓ otwiera ćwiczenie.
   Dostępna jest wskazana umiejętność i kroki potrzebne
   do jej rozstrzygnięcia. Podbicia mają osobne lekcje; nie można zapłacić
   za niewłaściwy wariant. Do ćwiczenia każdego rodzaju podbicia używamy
   jednej dodatkowej karty, a pełne limity pozostają w opisie mechaniki.
4. Rozstrzygnij działanie przez normalną płatność, fizyczne kości, wybór
   celów i potwierdzenie efektu. Samo zamknięcie objaśnienia ani płatność
   nie daje zaliczenia; serie wymagają dokończenia całej techniki.
5. Po wyniku pojawia się objaśnienie i ✓ do następnej sytuacji. Pchnięcie
   tarczą/Z bara oraz ukrycie wymagają uzyskania efektu; niepowodzenie
   odtwarza próbę z pełnymi zasobami. Pozostałe ćwiczenia zaliczają pełne
   rozstrzygnięcie, także przy pudle lub udanej obronie celu; rzeczywisty
   wynik i znaczniki są pokazywane przez normalny ekran działania.

Opis kursu nie jest wyświetlany nad rozstawieniem. Podczas ćwiczenia jest
dostępny w rozwijanej pomocy „Cel ćwiczenia i opcje samouczka”; płatność
i wybór celów mają własny ekran bez powtórzonego polecenia w tle.

## Zestawy ćwiczeń

| Postać | Kroki (zdolności i podbicia) | Przygotowywane sytuacje |
| --- | ---: | --- |
| Garran | 12 | Najpierw rana i Drugi oddech, potem tarcza bez podbicia i z czerwoną maną; ochrona, wsparcie, aura, wspólny Kontratak |
| Brakka | 14 | Szał, mobilność, kontrolowane trafienie do redukcji, pchnięcie, grupa do ryku i serii |
| Mira | 14 | Zasłona do ukrycia, unik, partner do własnej flanki, wolne pole za kukłą, przygotowane ukrycie + flanka do Wyroku |
| Dagna | 14 | Ranny/zatruty pomocnik, tymczasowe PW, aury, nieumarłe kukły, dzielenie leczenia i figurka duchowego oręża |
| Lorian | 13 | Pomocnik do Inspiracji, fizyczne operacje kart, odrzucone karty do odzysku, strzały i reakcja na obrażenia |
| Nimra | 20 | Cele pojedyncze, grupy, linia kukieł, pomocnik do wyłączenia z obszaru, teleport i przygotowany atak do Tarczy |
| Erynd | 12 | Dalsze cele, znak, celowanie, różne cele serii, sąsiadujące kukły do podbicia i obszary |

Razem: **99 ćwiczeń**, obejmujących wszystkie **67 aktywnych zdolności**
(w tym Święty symbol Dagny) i **32 rodzaje podbić**, oraz **7 pojedynków**.
Przed ćwiczeniem odnawiamy PW, budżet tury, manę i wymagane warunki. Szał
Brakki oraz ukrycie Miry do Wyroku są jawnie przygotowane; nie zużywają
akcji ćwiczenia. Nie przyznajemy obrażeń ani efektów bez ich rozstrzygnięcia.

## Mana, reakcje i finał

W ćwiczeniach gracz ma zapewnione potrzebne kolory many. Licznik zaczyna
z 5 kartami rynku i 20 talii; do Odzysku energii Loriana przygotowujemy
5/17/3, o czym mówi narracja. Koszt i fizyczne operacje nadal są zatwierdzane.
Nie przenosimy zużycia kart ani efektów między osobnymi ćwiczeniami.

Lekcje reakcji mają przygotowany atak kukły, aby losowe pudło nie usuwało
okazji do nauki. Objaśnienie mówi o tym przed rozpoczęciem. Atak korzysta
z normalnego rozstrzygnięcia i okien reakcji; własne kości gracza pozostają
fizyczne. Objaśnienie zaliczenia czeka na dokończenie całego przerwanego ataku.

W Osłonie towarzysza kukła deklaruje atak na pomocnika. ✓ po odłożeniu kosztu
przekierowuje go na Garrana, bez przestawiania figurki i ponownego wyboru celu
przez przeciwnika. Lekcja przygotowuje trafienie przeciw faktycznej KP Garrana
(z ekwipunkiem) oraz 6 obrażeń. Pomocnik nie traci PW; zwykła walka może dać pudło.

Podgląd i podsumowanie Osłony tarczą / Żelaznego bastionu pokazują przygaszony
zasięg aury oraz jasne turkusowe figurki odbiorców; Garran świeci na biało.
Osłona nie daje premii Garranowi, Bastion obejmuje także jego i daje premię
KP równą modyfikatorowi Siły Garrana (+4 przy Sile 18). Przy wybieraniu
białego podbicia priorytet ma zaznaczenie celów: niewybrane są przygaszone,
wybrane świecą mocniej. Podgląd zasięgu sam nie nadaje premii.

Ten sam przebieg podświetlenia dotyczy Błogosławieństwa (10 ft) i Boskiej Opieki
Dagny (5 ft, niebieskie podbicie 10 ft) oraz Hymnu Loriana (30 ft). Sojusznicy
objęci premiami świecą turkusowo; przeciwnicy objęci Boską Opieką złoto.
Promień podglądu reaguje już na wybór podbicia przed płatnością. Po użyciu
źródłem podświetlenia jest aktywny efekt, więc ruch i zakończenie koncentracji
zmieniają widok. Aura pozostaje widoczna również w turze innej figurki;
bieżący ruch lub wybór celu zachowuje pierwszeństwo. W ćwiczeniu Hymnu
stoi obok Loriana pomocnik, żeby pokazać premię drużynową.

Rozkaz: Kontratak pokazuje „1/2 — Garran”, a po pierwszym ataku „2/2 — pomocnik”.
Dla każdej figurki od razu podświetla się ruch do 10 ft. Wskaż pole, ustaw
figurkę i zakończ ruch przyciskiem ✓; ✓ bez wyboru pola pozostawia ją w miejscu.
Potem automatycznie podświetlają się cele wyposażonej broni: wskaż kukłę,
potwierdź ✓ i wykonaj rzuty. Nie wybierasz akcji z menu ani kolejnej runy.
Ustawienie ćwiczebne umożliwia oba ataki bez ruchu. Brak celu pozwala przejść
dalej przyciskiem ✓ bez ataku, ale wymaga ponowienia lekcji; pudło zalicza atak.
Koszt płacimy raz, pomocnik zużywa reakcję. Samouczek nie pozwala pominąć ciosu
przyciskiem końca tury, ale pudło nadal jest wykonaniem swojej części rozkazu.

W nowym profilu many Lorian nie podlega historycznemu zakazowi używania
zdolności bez publiczności; aktualną skazę nadal wycenia moduł wspólnej many.

Finał tworzy świeżego bohatera i dokładnie jedną kukłę: **30 PW, KP 13,
ruch 30 ft, atak wręcz +3, obrażenia 1k6**. Brak pomocników, skryptowanych
rzutów i zapewnianej many. Gracz przygotowuje normalną talię 25 kart
(po 5 każdego koloru): rynek 5, talia 20, odrzucone 0. Rzuca na inicjatywę,
sam wybiera ruch, ataki i zdolności. Zwycięstwo zalicza kurs. Utrata wszystkich
PW kończy próbę pojedynku; nie wymaga rozgrywania śmierci treningowej postaci.
✓ po wyniku wraca bezpośrednio do wyboru bohaterów.

## Zapis i pliki

`walkthrough_progress_<hero>` zapisuje indeks następnego ćwiczenia,
`walkthrough_completed_<hero>` zwycięstwo w pojedynku. Bieżąca faza i token
objaśnienia także należą do zapisu. Nie zaliczamy przyszłych kroków ani
starych potwierdzeń. Wyjście do wyboru zachowuje postęp. Po porażce można
wrócić prosto do finału; wybranie ukończonej postaci powtarza kurs od początku.
Zapis przygotowania odtwarza ustawienie figurek, aby nie ominąć fizycznego setupu.
Zapis we wprowadzeniu odtwarza najpierw jego okno. Znacznik przygotowanego
terenu jest zachowany w zapisie; rozpoczęty, niedokończony setup go nie ustawia.
Wcześniejsze zaliczenia dowolnej kolejności nie są zaliczeniami nowej sekwencji.

- `application/training_walkthrough.py`: kolejność i deterministyczne ustawienia.
- `ui/training_walkthrough.py`: fazy, płatność, warunki zaliczenia, powtarzanie i powrót.
- `content/tutorials/walkthrough.json`: narracja Nessy dla każdej zdolności;
  stabilny `narration_id` w payloadzie pozwala później przypisać nagrania.
- `ui/static/training_arena.js`: panel zadania, objaśnienia i wybór postaci.
- `tests/unit/test_training_walkthrough.py`: przygotowanie wszystkich 99 kroków,
  rzeczywiste leczenie/pchnięcie/podbicie, pełne reakcje, zapis i wynik pojedynku.
- `tests/unit/test_training_walkthrough_browser.py`: Chrome, symbole, ✓ i ekran wąski/szeroki.

Walidacja 2026-09-11: **125 testów przeszło**, uruchamianych kolejno przez
`scripts/safe_pytest.sh --timeout 60`: walkthrough 32, Chrome 2, wspólna mana
30, dotychczasowa arena 25, wcześniejsze objaśnienia 22, przepływ USB v2 4,
przygotowanie planszy 9 i dotychczasowy warunek publiczności Loriana 1.
Sprawdzono również kompilację nowych modułów Python, poprawność XML mapy SVG
oraz `git diff --check`. Chrome wymagał uruchomienia poza sandboxem, który
blokuje jego lokalne gniazda; oba rozmiary ekranu przeszły testy.

Nagrania głosu i pełna próba 99 ćwiczeń na fizycznej planszy pozostają do wykonania.
Nie zmieniono firmware ESP ani transportu planszy.

---

## Archiwum: wcześniejsze tryby areny

Poniższy opis dokumentuje dawne zapisy i testy. Nowy panel nie oferuje
swobodnej listy ćwiczeń ani kończenia próby rozmową z figurką Nessy.

## Samouczki postaci — 2026-09-10

Warunkiem zaliczenia jest rozstrzygnięcie każdej aktywnej zdolności postaci,
również gdy atak nie trafi lub cel obroni się. Samo wybranie akcji, zapłata,
podgląd wyniku, anulowanie ani przerwanie serii nie zaliczają ćwiczenia.
Każda postać ma 9 ćwiczeń, Dagna dodatkowo Święty symbol, Nimra 12: razem 67.
Kolejność jest dowolna; panel wskazuje następną propozycję i zawiera pełną
listę z symbolami run i many. Podbicia są opisane w lekcjach, nie mają
osobnego obowiązkowego zaliczenia. Pasywy i skazy nadal działają normalnie.

Po wykonaniu zdolności Nessa pokazuje objaśnienie. Niebieskie ✓ na planszy
lub przycisk na ekranie zamyka je i przywraca menu. Objaśnienie reakcji
czeka na dokończenie przerwanego ataku; nie przejmuje panelu w środku rzutu.
Zapis gry zachowuje listę zaliczeń i oczekujące objaśnienie. Po zakończeniu
podejścia można kontynuować tę samą postać z zachowaniem zaliczeń. Wybranie
już ukończonego samouczka rozpoczyna go ponownie od zera.

Teren, pozycja bohatera, Nessa, skrzynie, zasłona, filar, osłona i gruz
pozostają bez zmian. Setup wskazuje pozycje figurek dla konkretnego bohatera.
Każdy wariant ma trzy kukły po 180 PW, KP 10 i +5 do trafienia. Pierwsza
porusza się 20 ft, pozostałe pozostają na miejscu i zadają zero obrażeń.
To cele do ćwiczeń; pokonanie kukieł nie zastępuje zaliczenia umiejętności.

| Bohater | Kukła napastnika; pozostałe kukły | Pomocnicy | Obrażenia napastnika |
| --- | --- | --- | --- |
| Garran | (10,16); (11,16), (11,17) | (9,17), (8,18) — ochrona, podbicia osłony, Kontratak | 2 |
| Brakka | (10,18); (10,17), (11,18) | (8,18) | 6 przed odpornością — reakcja w Szale |
| Mira | (7,17); (7,18), (8,19) | (8,17) — własna flanka, blisko zasłony | 2 |
| Dagna | (10,17); (11,17), (10,16), wszystkie nieumarłe | (9,17) — rana i zatrucie | 1 |
| Lorian | (10,16); (11,16), (11,17) | (9,17) — Inspiracja i cel do ochrony reakcją | 3 |
| Nimra | (10,18); (10,17), (11,17) | (9,17) — wyłączanie pól, ryzyko obszarów | 2 |
| Erynd | (10,12); (11,12), (10,11) | (9,17) | 1 |

Pomocnik nie ma osobnej tury, ale może flankować, przyjmować Inspirację
i wykonać atak w Rozkazie: Kontratak! Garran i Dagna zaczynają z 8 ranami;
pomocnik Dagny ma 12/80 PW, inni pomocnicy 40/80 PW. Pierwszy pomocnik ma
treningowy znacznik zatrucia. Po utracie potrzebnego celu zakończ podejście
u Nessy i rozpocznij je ponownie, zachowując dotychczasowe zaliczenia.

Treść lekcji: `content/tutorials/recruitment_arena.json`, połączona z aktualnym
katalogiem zdolności i nadrukowanymi symbolami panelu. Testy:
`tests/unit/test_training_tutorial.py`, w tym Chrome, zapis/wczytanie,
niezmieniony teren, płatność, reakcje, objaśnienia i zatwierdzanie na planszy.
Test Kontrataku przechodzi przez oba ataki, a Osłony towarzysza przez wybór
pomocnika jako celu, przejęcie i rozliczenie ataku. Unik instynktowny Miry
w profilu wspólnej many jest dostępny także bez ukrycia, zgodnie z katalogiem;
usunięto ograniczający go stary warunek w obsłudze reakcji.

Poniższe warianty należały do wcześniejszego panelu.

## Przebieg

1. Nessa zaprasza jednego kandydata. Każda próba tworzy świeżą kopię gotowego
   bohatera z aktualnym ekwipunkiem, pasywami, skazą i całym zestawem zdolności.
2. Zwykły setup prowadzi przez teren, Nessę, kukłę i bohatera. Rozstawienie
   jest stałe, aby łatwo powtarzać porównywalne próby.
3. Rzut inicjatywy rozpoczyna normalną walkę: te same skróty, wybór na planszy,
   kreator fizycznych rzutów, stany, efekty i interfejs many co w kampanii.
4. Pokonaj wszystkie kukły **albo** podejdź na sąsiednie pole Nessy i wybierz
   „Nesso, kończę pokaz”. Rozmowa jest darmowa, bez many. Sąsiednia Nessa jest
   dostępna przez zielone pole na planszy i przycisk w panelu rekrutacji;
   potwierdzenie przebiega przez zwykły interfejs interakcji. Nessa nie jest
   aktorem bojowym ani legalnym celem ataku.
5. Po zakończeniu wybierz dowolnego następnego bohatera lub powtórz próbę.
   Znaczniki ukończenia nie oznaczają sprawdzenia każdej umiejętności:
   są zapisem zakończonych pokazów, także zakończonych rozmową.

## Warianty

| Próba | Przeciwnicy i pomocnik | Zastosowanie |
| --- | --- | --- |
| Podstawowa | Jedna kukła, 50 PW, KP 10, +5 do trafienia, 0 obrażeń | Ataki, ruch, skradanie, efekty i pasywy |
| Wsparcie | Jedna kukła z 1 obrażeniem; bohater zaczyna z 8 ranami; pomocnik 10/30 PW ze znacznikiem zatrucia | Leczenie, usuwanie stanu, wsparcie i przekazywanie many |
| Obszarowa | Trzy kukły po 50 PW, KP 10, +5 do trafienia, 0 obrażeń | Czary obszarowe, rozdzielanie celów, ukrycie względem wielu obserwatorów |

Kukła ma szybkość 20 ft i używa zwykłego prostego AI: podchodzi do celu
oraz wykonuje atak wręcz o zasięgu 5 ft. Nie ma szczególnych odporności.
Rodzaj celu można ustawić na humanoida, nieumarłego albo zwierzę; to
symulacja pozwalająca sprawdzić ograniczenia celu konkretnych zdolności.
Stany kontroli działają zgodnie z regułami i mogą zatrzymać kukłę.

Pomocnik nie ma swojej tury ani doboru kart. Jest legalnym odbiorcą
wsparcia Loriana (w tym fizycznej many); nie powiększa drużyny graczy.

## Mana i izolacja

Na każdą próbę przygotuj 25 kart, po 5 każdego koloru: rynek 5 i talię 20.
Nie ma prywatnej ręki. Koszt odkłada się przed efektem, a rynek uzupełnia
na końcu tury, zgodnie z instrukcjami wspólnej many 0.3. Karty i kolory
płatności rozliczają gracze na stole; aplikacja prowadzi liczniki.

Fale zgłasza się i rozlicza jak w zwykłej walce. Wyjątek treningowy:
Zagrożenie i fala nie zwiększają obrażeń kukieł. Atak w próbie podstawowej
lub obszarowej nadal zadaje 0, a we wsparciu bazowo 1; normalne redukcje
obrażeń postaci nadal działają.

Brak doświadczenia i łupów. Próba nie aktualizuje postaci w katalogu
bohaterów ani kampanijnego zapisu. Zwykłe „Zapisz” zachowuje bieżącą
walkę, wariant i ukończone pokazy w osobnym zapisie areny. Aby wrócić
do niego po uruchomieniu aplikacji, otwórz arenę i użyj menu wczytywania
zapisu bieżącego scenariusza. Nie jest to automatyczny zapis po każdej próbie.

## Plansza

Mapa: `assets/maps/recruitment_arena/arena.svg`, siatka 20×30.
Współrzędne poniżej to `(kolumna, wiersz)`, liczone od zera.

| Element | Pole/pola |
| --- | --- |
| Nessa | (3,18) |
| Bohater | (9,18) |
| Kukła główna | (10,12) |
| Pomocnik — tylko wsparcie | (9,16) |
| Dodatkowe kukły — tylko próba obszarowa | (11,12), (10,11) |
| Pełna zasłona: blokuje ruch i widoczność | (6,14), (6,15), (6,16) |
| Niska osłona: +2 KP, ruch dozwolony | (13,15), (14,15) |
| Wysoki stos skrzyń: blokuje ruch i widoczność | (4,11), (5,11) |
| Kamienny filar: blokuje ruch i widoczność | (13,11), (14,11), (13,12), (14,12) |
| Gruz: trudny teren, bez osłony | kolumny 8–11, wiersze 14–15 |

Gruz podwaja koszt ruchu na jego polach: prosty krok kosztuje 10 ft zamiast
5 ft. Pas leży na bezpośredniej drodze do kukły, ale można obejść go
z obu stron. Szare pola ze znakiem × oznaczają pełne przeszkody, brązowe
z +2 niską osłonę, pomarańczowe z kamieniami trudny teren. Setup pokazuje
wszystkie elementy także na fizycznej planszy. Po zmianie rozstawienia
rozpocznij nową próbę, aby ustawić nowy teren zgodnie z setupem.

## Implementacja i sprawdzenie

Scenariusze: `content/scenarios/recruitment_arena*.json`.
Konfiguracja wariantów: `application/recruitment_arena.py`.
Przebieg i prezentacja: `ui/training_arena.py`, `ui/static/training_arena.*`,
warunkowe podłączenie w sesji UI, trasach i szablonach.

Testy `tests/unit/test_recruitment_arena.py` obejmują start wszystkich
siedmiu postaci, normalne zdolności w payloadzie, AI i obrażenia, rozmowę,
wybór Nessy z planszy, powtarzanie prób, warianty i zapis/odczyt.
Testy fal sprawdzają także utrzymanie obrażeń kukieł przy Zagrożeniu 3.
Przeglądarka: pełny przebieg Mira → rozmowa → Brakka, kreator inicjatywy,
setup, widoki 1440, 1280 i 390 px, brak poziomego przewijania i błędów JS.
Fizyczne odczyty planszy i LED wymagają sprawdzenia przy stole.

Weryfikacja 2026-09-06: 86 zaliczonych testów, uruchamianych kolejno przez
`scripts/safe_pytest.sh --timeout 60 <plik> -q`:

- `tests/unit/test_recruitment_arena.py`: 19.
- `tests/unit/test_combat_scene_interaction_flow.py`: 5.
- `tests/unit/test_physical_mana.py`: 19.
- `tests/unit/test_combat_playtest_polish.py`: 7.
- `tests/unit/test_scenario_loader.py`: 36.

Dodatkowo: poprawność XML mapy SVG, składnia Python i `git diff --check`.
Nie jest to jeszcze ręczne sprawdzenie wszystkich kombinacji zdolności.

Rozszerzenie terenu (2026-09-06): ponownie uruchomiono cały plik
`tests/unit/test_recruitment_arena.py` — 23 testy zaliczone, w tym koszt
ruchu przez gruz, blokowanie widoczności, oba obejścia, dojście do Nessy,
obecność terenu w setupie oraz wolne pola startowe wszystkich wariantów.

Korekta instrukcji osłony: setup rozdziela pełne blokady od niskiej osłony.
Na niską osłonę można wejść i zakończyć ruch; stojąca na niej figurka ma
+2 KP. Osłona na linii ataku dystansowego daje celowi +2 KP.
Elementy o różniących się zasadach nie są łączone w jeden krok setupu,
nawet gdy mają ten sam typ w danych scenariusza.

## Podgląd panelu 30 pól — 2026-09-07

Osobny, klikalny prototyp: `assets/maps/recruitment_arena/panel_preview/index.html`.
Mapa SVG i podglądy PNG znajdują się w tym samym katalogu. Dłuższy bok jest
na dole; 30 pól panelu zastępuje skrajną kolumnę po obróceniu widoku.
To materiał do oceny, jeszcze bez rezerwacji pól i sterowania w aktywnej grze.
Układ, mapowanie oraz krytyczne porównanie: [panel 30 pól](BOARD_PLAYER_PANEL_30_PREVIEW.md).

Aktualizacja: podgląd nie ma już zaokrąglonego obrysu; wszystkie pola
prostokąta ponad panelem są terenem areny. Karty wszystkich postaci mają
runy ze wspólnego katalogu. Następne etapy i warunki dopuszczenia do testów:
[plan wdrożenia panelu](ARENA_PANEL_IMPLEMENTATION_PLAN.md).

## Modułowy wydruk do testów

[Pakiet A4 z kartami](ARENA_A4_PRINT_PACK.md) zawiera pustą siatkę z panelem
oraz osobny arkusz 19 znaczników terenu. Pozycje NPC, bohatera, kukieł i terenu
nie są nadrukowane. Aktorów reprezentują figurki. Przeszkody i gruz układa się
z wyciętych pól 25 × 25 mm zgodnie z podświetleniem podczas setupu.
Każdy rodzaj ma osobny krok i podpis zgodny z wydrukiem: ZASŁONA, SKRZYNIE,
FILAR, OSŁONA, GRUZ. Znaczniki pozostają ruchome, bez przyklejania do mapy.

## Inicjatywa z fizycznego panelu

Na arenie aktywny rzut inicjatywy używa dolnego panelu: minus na `(19,3)`
świeci czerwono, plus na `(19,2)` zielono, a zatwierdzenie na `(19,1)`
niebiesko. To współrzędne modelu planszy (kolumna, wiersz, od zera), zgodne
z wydrukowanymi slotami 26–28. Początek każdej kości k20 to 10, zakres 1–20.
Minus gaśnie przy 1, plus przy 20. Sprzęt przekazuje zdarzenia `press`;
zdarzenia zwolnienia nie zwiększają wyniku.

Pierwsza akceptacja zapisuje kość. Przy przewadze/utrudnieniu następna kość
zaczyna osobno od 10. Po wszystkich kościach aplikacja pokazuje podsumowanie;
kolejna akceptacja rozstrzyga inicjatywę i dodaje premię. W podsumowaniu
świecą tylko niebieskie zatwierdzenie oraz pomarańczowy powrót `(19,0)`
do poprawiania kości. Przeciwnicy nadal rzucają automatycznie.

Ekran i plansza korzystają z jednego stanu wyniku; klawiatura pozostaje
awaryjnym wejściem. Okno inicjatywy nie zatrzymuje już nasłuchu planszy.
Stara odpowiedź skanu lub powtórzone żądanie ze starą rewizją nie mogą
zatwierdzić następnego kroku. Po zakończeniu inicjatywy oddajemy LED-y
bieżącemu etapowi rozgrywki.

Sprawdzenie: `tests/unit/test_initiative_panel.py` oraz pełny przebieg
w przeglądarce z kolejką symulującą sprzęt (plus, minus, podsumowanie,
korekta, awaryjne wpisanie liczby, fizyczna akceptacja i start walki).

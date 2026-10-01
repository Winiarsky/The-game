## Karty ładunków v0.2 — 24.09.2026

- [x] 30.09: przenieść zaakceptowaną walkę do Python/UI: wszystkie 29 mocy,
  pasywy/skazy, Rezonans i premie, kolejki reakcji/przesunięć, indywidualne
  kości gracza i automatyczne rzuty przeciwników; panel, LED-y oraz zapis 34.
- [x] Przygotować izolowany launcher `scripts/resonance_playtest.py`,
  tryb symulatora/sprzętu i instrukcję `docs/playtests/RESONANCE_RUNTIME_MANUAL.md`.
- [ ] Wykonać próby stołowe z fizyczną planszą według instrukcji: opóźnienia
  wejść, czytelność kolorów, przerwane ruchy i powrót po wczytaniu.
- [ ] Po teście ręcznym ocenić balans kosztów 4/8, skaz i odzysku 1k4.
- [ ] Zaktualizować historyczny test
  `test_mission_zero.py::test_guild_destinations_use_tile_fields_and_arena_is_informational`:
  pomija istniejący już w HEAD przycisk powrotu (slot 29) w skanie gildii.
  Nie zmieniać przy tej okazji eksploracji w ramach wdrożenia walki.

- [x] 30.09: pod torem Rezonansu w mocku pokazać liczbowe podsumowanie
  aktywnych bonusów, z sumowaniem kopii i Fali oraz rozróżnieniem limitów
  osłon od ich pozostałych pul. Bez zmiany mechaniki.

- [x] 30.09: w mocku aplikacja rzuca za przeciwników (atak, obrażenia,
  obrona i test przeciwstawny). Okazyjny: zapowiedź i podświetlenie wroga
  → ✓ → pełny wynik → ✓ → dalszy ruch / następna reakcja. Wyniki zachowane
  w zapisie, bez ponownego losowania; ręczne kości tylko dla bohaterów.

- [x] Rzuty w mocku walki: jedna kość → ✓ → następna kość, również
  wewnątrz puli 2k6 i przy przewadze/utrudnieniu. Skutki dopiero po ostatniej
  kości; zapis próby zachowuje dotychczas zatwierdzone wyniki.

- [x] 29.09: zaktualizować wyłącznie walkę w dotychczasowym mocku UI:
  dane z aktualnych kart, ładunki, 29 mocy, Rezonans i jego prezentację,
  stany, koszty/skazy, odzysk, reakcje oraz kolejki wskazywania pól.
  Dodać symulator pól i niezależny zapis próby; zachować rozmowy/reputację.
  Zakres, założenia i instrukcja: `docs/ui/RESONANCE_MOCK.md`.
- [x] Ograć i zatwierdzić mock walki z użytkownikiem. Dopiero potem
  przenieść zaakceptowane mechaniki do Python/UI aplikacji i planszy;
  testować rzeczywiste zdarzenia, zapis, powtórzenia i geometrię areny.

- [x] 29.09: zaktualizować karty Brakki, Miry, Dagny, Loriana i Nimry;
  Erynd bez zmian. ST jako formuły, Szał i krytyk Brakki, Parkour/ukrycie
  Miry, bezterminowy Hymn, Precyzyjny splot i Strefa ognia 3×3. Odświeżyć PDF.
- [x] W kolejnym kroku wdrożyć mechaniki z przeglądu 29.09:
  krytyk i Szał Brakki, ukrycie per obserwator i Parkour z kolejką okazyjnych,
  terminy Więzów, decyzję Hymnu po k20, wybór pominięcia i obszar 3×3 Nimry.
  Notatki i przypadki akceptacyjne: `docs/RESONANCE_RUNTIME_SPEC.md`.

- [x] 27.09: przegląd kart Garrana — stan Żywa osłona, odzysk po pudle
  w Garrana, odrzucenie Impulsu, magiczne obrażenia Ostrza, Szarża bastionu
  M+S i opis Powalonego; Żar bez zmian. Przepływ planszy w specyfikacji.
- [x] 27.09: wspólna korekta siedmiu zestawów — scenki zamiast celu na
  stronie 1, formatowanie pasywu i odzysku, usunięcie wspólnego dopisku.
  Pionowa strona 2: jeden cel 60×54 mm i pięć okręgów postępu po prawej.
  Usunięta sekcja obsługi; wszystkie bonusy run na stronie 4.
- [x] Przy wdrożeniu walki ładunków zrealizować stany Żywej osłony i
  Powalonego oraz wybór/podgląd/zatwierdzenie Impulsu i Szarży zgodnie z
  `docs/RESONANCE_RUNTIME_SPEC.md`; sprawdzić zapis i powtórzoną akceptację.

- [x] 26.09: zmienić odzysk klasowy na 1k4 raz na rundę w katalogu,
  walidacji, kartach i dokumentacji zasad.

- [x] 26.09: usunąć powtórzony opis Skupienia spod pasywu na pierwszej
  stronie wszystkich postaci; zachować kartę i miejsce na macie zdolności.

- [x] 25.09: usunąć pozostałość biegłości z mat i formuły ST; ST = 10 +
  modyfikator cechy, bez zmiany obecnych wartości liczbowych. Odświeżyć PDF-y.

- [x] Przygotować 29 mocy: po 4 dla sześciu bohaterów, 5 dla Nimry.
  Wspólne bonusy run, koszty obu trybów, pula 20, Skupienie 1k20,
  pasywy, skazy i dwa warunki odzysku ze wspólnym limitem 1k6 na rundę.
- [x] Zachować wygląd kart i wygenerować komplet A4, zaktualizować spis
  materiałów; pozostawić wcześniejszą makietę UI.
- [x] Korekta ogólna kart: usunąć tor 0–20 i dawną stronę 02; przenieść
  pasyw, Skupienie i odzysk na stronę 1. Po 3 planszetki + 2 wycinanki,
  35 stron razem. Magiczne nazwy mocy i symbol Rezonansu w podwójnej otoczce.
  Zachować koszty, efekty i rozmiary. Odnowić PDF-y, spisy i legendy.
- [x] Przenieść Gwiazdę przed +/− (slot 25); zachować 20 run, dodając Iskrę
  w dawnym slocie 24. Uaktualnić PDF mapy, osobny arkusz D3, wejście i LED.
- [x] 25.09: przesunięte zestawy po 4 runy (Nimra 5), 10 używanych run mocy;
  nowe bonusy Oka, Kielicha, Węzła, Fali i Klepsydry z zasadami kumulowania.
  Katalog, przypisania na kartach, legendy, HTML i 35 stron PDF zaktualizowane.
- [x] 25.09: zapisać ciągły Rezonans, wejście bohaterów od własnej tury,
  premie przed mocą i wspólne wygaszenie; nowe działanie 10 run na kartach.
  Osobne liczniki Kielicha/Klepsydry, Fala kopiuje poprzednią runę, Węzeł globalny.
  Specyfikacja `docs/RESONANCE_RUNTIME_SPEC.md` zawiera kolejkę Haka i przypadki testowe.
- [x] Przegląd postać po postaci: korekty Garrana 27.09 i pozostałych
  bohaterów 29.09 zapisane na kartach; Erynd zaakceptowany bez zmian.
- [x] Przed wdrożeniem do silnika zamknąć jawne doprecyzowania w specyfikacji (wzrost premii
  wcześniejszych uczestników, brzegowe Fale, pule osłon i legalność przeniesień).
- [x] Omówić karty z użytkownikiem, następnie wdrożyć ładunki i przekazywany
  Rezonans **tylko w walce**, zachowując wcześniejszą makietę i eksplorację.
  Wyświetlać liczbę ładunków bohatera; fizyczny licznik gracza to pokrętło.
  Pominięta tura nieprzytomnego nie przerywa łańcucha; balans pozostaje do ogrania.
- [ ] Uporządkować stary fixture `tests/unit/test_board_panel_runtime.py`:
  helper `begin()` usuwa pulę run, pozostawiając postaci z profilem runicznym.
  22 przypadki zatrzymują się przed kontrolą panelu na `ActionEconomyCost('special')`.
  Aktualne testy mapowania i `test_rune_combat_board.py` używają spójnej puli.

## Dalszy kierunek prac — 23.09.2026

- [ ] Przygotować indywidualne cele dla każdej postaci, które będzie mogła
  realizować podczas gry, z jasno określonymi warunkami ukończenia.
- [x] Przywrócić wcześniejszą makietę `docs/ui/prototype.html` jako widok
  wskazywany przez stronę materiałów; zachować aktualne karty i ich PDF-y.
- [ ] Dopracowywać zmiany po kolei z użytkownikiem, zaczynając od kart.
  Makieta koszyków nie jest przyjętym docelowym układem UI.

## Osobiste koszyki run — prototyp 23.09.2026

- [ ] Przygotować wspólny katalog siedmiu bohaterów według
  `system_run_v0.1.md`: cztery kategorie, pojemności, regeneracja, skazy,
  osobny przycisk mocy, koszt kategorią i konkretne rezonanse.
- [ ] Wygenerować komplet nowych kart, planszetek koszyków i wyposażenia;
  zachować wymiary wycinanek i sprawdzić przepełnienia wydruków.
- [ ] Przygotować klikalną makietę: wybór symboli przed walką,
  moc → pole → własna runa → rezonans/wsparcie → zatwierdzenie,
  rozładowanie, Skupienie, klasowe ładowanie k4 i zapis prototypu.
- [ ] Sprawdzić koszty, anulowanie, reakcję pomocnika, limity regeneracji,
  zapis w trakcie decyzji oraz pełny przykład Uderzenia tarczą z Okiem.
- [ ] Ograć przy stole profile i nowe koszty wszystkich siedmiu postaci;
  dopracować robocze pojemności Dagny/Nimry/Erynda oraz tempo regeneracji.
- [ ] Po ograniu przenieść zaakceptowany wariant z prototypu do aplikacji.

[Zakres i doprecyzowania](docs/RUNE_BASKETS_PROTOTYPE.md).

## Wnioski po ręcznym teście — 22.09.2026

- [x] Spisać punkt wyjścia przed wdrożeniem: wymagania użytkownika, proponowany
  obieg run, przykładowa adaptacja dziewięciu mocy Garrana, jedna runda
  konfrontacji, skalowanie toru, przykłady i luki. Dokument do omówienia:
  [Runy v0.1](docs/RUNE_SYSTEM_PROPOSAL_V01.md). Liczby i doprecyzowania
  pozostają propozycją; bez zmian runtime, kart i PDF-ów.
- [ ] Po uzgodnieniu projektu dostosować pasek: ruch/atak/przedmiot/koniec,
  przerwa, runy, przerwa, +/−/✓/↩. Usunąć zmianę broni w terenie, zachować
  przygotowanie wyposażenia przed misją. Ustalić liczbę rodzajów run i znaków.
- [ ] Po uzgodnieniu projektu powiększyć mapę bazową i wszystkie kafle Misji 0
  o 3% względem obecnego profilu wydruku; wspólna geometria, kontrola A4
  i pasowania do czujników. Pozostałe fizyczne karty zachowują swoje wymiary.
- [ ] Po uzgodnieniu projektu sprawdzić pełną obsługę planszą od launchera,
  przypisania wszystkich kontrolek oraz rozdzielenie przewijania i wpisywania
  wartości przez +/−, zachowując obecny wygląd UI.
- [ ] Wybrać i przetestować na stole mechanikę zastępującą manę: wspólna,
  ograniczona pula do uzgadnianego podziału, wydawanie teraz lub oszczędzanie
  między rundami, różne układy zasobów zmieniające dostępne rozwiązania.
  Punkt wyjścia użytkownika: N+2 run co rundę walki, ręka do 7, płatne moce,
  reakcje i aury; ruch + atak/przedmiot + specjalna. Stałe przypisania run,
  liczba 10/20 do ustalenia. Konfrontacje: jedna runda i tor zamiast wpływu.
  Zachować sterowanie polami, fabułę i postawę drużyny; doprecyzowania
  z dokumentu nie są jeszcze zatwierdzoną specyfikacją.
- [ ] Skrócić konfrontację z Nessą. Log `exploration_ui_4cd122c1af.jsonl`
  z 21.09: wejście 22:37:06, porażka 22:55:29, wyjście 22:56:09 czasu lokalnego;
  ok. 19 minut obejmuje przygotowanie i obsługę. Próba doszła do 4. rundy,
  9 testów i 90 operacji konfrontacji; przy wyczerpaniu talii zostały 2 oporu.
- [ ] W kolejnym kroku zdiagnozować zgłoszoną blokadę sterowania walką.
  Ten sam log, linie 726, 752 i 756: kliknięcia ataku Miry odebrane, lecz
  odrzucone jako „Rapier: brak legalnych celów”. Końcowe skany i potwierdzenia
  LED są obecne; przyczyna problemu nie została jeszcze ustalona.

## Terminal — szybki start po scenie z wozem — 21.09.2026

- [x] `runtime.mission_combat_ui`: wybór 3–6 unikalnych bohaterów oraz
  postawy −3…3. Domyślnie fabularne przybycie do posterunku, potem normalne
  rozstawianie, inicjatywa i walka. Opcjonalne skróty setup/initiative/combat,
  ziarno rzutów, port i backend planszy; automatyczne wykrywanie USB.
- [x] Nowe próby mają osobne katalogi zapisów, obserwacji i biblioteki postaci.
  Tryb bez planszy nie przejmuje ustawienia automatycznego łączenia z USB.
  Postawa przechodzi do checkpointu i fizycznego składu talii. Opis i przykłady
  w `docs/RUNNING_AND_TESTING.md` oraz README Misji 0.
- [x] 15 testów: cztery punkty startu, drużyny 3/4/6 osób, postawa i talia,
  przejście z fabularnego intro przez ✓, zapis/odczyt, powtarzalność rzutów,
  błędne parametry, przekazanie opcji połączenia i zamknięcie backendu.
  Sprawdzono również polecenie `--help`.

## Inicjatywa, kolory many i postawa — 21.09.2026

- [x] Log `exploration_ui_b0f14c085f`, zdarzenia 543–548: ogólny panel
  zastępował przyciski inicjatywy przez ✓/↩. Panel inicjatywy ma teraz
  pierwszeństwo przy wyborze pól, LED i rozstrzyganiu naciśnięć. Start czyści
  poprzedni kontekst; przeglądarka i serwer blokują jego nadpisanie.
- [x] Zdarzenie 562 potwierdzało jeden niebieski kolor dla pięciu run many.
  Zgłaszanie koloru i wybór z oferty używają palety rozmów: czerwony, biały,
  zielony, fiolet dla czarnego symbolu i niebieski. Także dwie karty tego
  samego koloru podświetlają właściwe runy tym samym kolorem.
- [x] Wyróżniony komunikat przygotowania talii przy odchyleniu od Równowagi:
  postawa, wyłączone karty i pełny skład talii z symbolami. Operacja pozostaje
  zablokowana do ✓; zapis zachowuje ten etap. Dane pochodzą z talii danej
  walki. Teksty w `text/ui/combat.json`; Równowaga zachowuje zwykłą instrukcję.
- [x] 26 testów zaliczonych: inicjatywa i LED, kolory zgłaszania/oferty,
  wszystkie siedem pozycji postawy, zapis/odczyt przygotowania; trzy próby
  Chrome z automatycznym odczytem symulowanej planszy od inicjatywy do many
  (Równowaga, Solidarność, Bezwzględność).

## Ustawianie bohaterów przed walką — 21.09.2026

- [x] Portret obok „Aktualnie ustaw” wskazuje bohatera, którego figurkę
  należy postawić. Zmienia się po zatwierdzeniu pola, razem z imieniem;
  korzysta z istniejących portretów postaci i paczki misji.
- [x] Test Chrome na laptopie: przygotowanie terenu, kolejne portrety trzech
  bohaterów, wybór pola i zatwierdzenie przez wejście planszy; instrukcja
  mieści się w widoku. Zaktualizowano oczekiwania testu o przycisk menu.

## Przygotowanie drużyny — instrukcja i portrety — 21.09.2026

- [x] Przed wyposażaniem na wyprawę osobny ekran instrukcji: wspólny zapas,
  rzeczy postaci, miejsca noszenia i plecak, przekazywanie fizycznych kart,
  obsługa runami oraz przykład zamiany miecza i tarczy na broń dwuręczną.
  Tekst w `text/equipment_intro.md`, tytuł i przyciski w plikach tekstowych misji.
- [x] Portret i imię aktualnie wyposażanej postaci; runa instrukcji w menu
  pozwala wrócić do opisu również ze starszego zapisu. Powrót z instrukcji
  zachowuje bohatera, źródło i wybrany przedmiot. Instrukcja obsługuje −/+/✓/↩.
- [x] 14 testów: wyposażenie, przebieg przygotowania, zapis/odczyt instrukcji,
  powrót i portrety; dwie próby Chrome na laptopie z automatycznym odczytem
  symulowanej planszy (1131 × 720 i 1300 × 720), bez obciętych przycisków.

## Plansza — sterowanie w oknach podglądu — 21.09.2026

- [x] Okna „Twoje efekty”, premii i menu sesji nie zatrzymują automatycznego
  odczytu planszy, gdy ich kontekst został zarejestrowany na serwerze.
  −/+ przewijają podgląd, ✓/↩ zamykają go i przywracają sterowanie rozmową.
  Pozostałe okna nadal blokują wejście do gry w tle.
- [x] Test Chrome odtworzył brak ponownego skanowania po otwarciu efektów.
  Po poprawce dwa warianty (otwarcie runą i myszą podczas oczekiwania planszy)
  przechodzą przez prawdziwe HTTP skanowania z symulowanym odbiornikiem;
  sprawdzają przewijanie, obie drogi zamknięcia, menu i zachowanie stanu gry.
  Łącznie 19 testów zaliczonych. W starszym teście blokady podczas spalania
  użyto zwykłej porażki (2), bo naturalna 1 ma teraz dodatkowy koszt krytyczny.

## Misja 0 — kradzież mikstury przez Mirę — 21.09.2026

- [x] Po porażce konfrontacji z Nessą i tylko z Mirą w drużynie: opcjonalna
  kradzież jednej słabszej mikstury (1k8 + 2 PW) za krok ku Bezwzględności.
  Osobna scena z Nessą zajętą papierami i fiolką pozostawioną na biurku;
  runy kradzieży/odmowy, potem powrót do odprawy. Wynik konfrontacji pozostaje
  porażką. Sukces, kompromis i porażki innych scen nie odblokowują kradzieży.
- [x] Edytowalne teksty w `text/nessa_theft*.md` oraz `text/ui.json`, zdarzenie
  postawy w `mechanics/ethos.json`. Nagroda trafia do wspólnego zapasu.
  Jednorazowość decyzji i kosztu; autozapis przed wyborem i po obu odpowiedziach.
- [x] Weryfikacja: 18 testów dostępności, nagród, postawy, zapisów i wcześniejszych
  wyników negocjacji; w tym dwie próby Chrome na laptopie (kradzież/odmowa runami).

## Konfrontacje — czytelna reakcja po rundzie — 21.09.2026

- [x] Doprecyzowano „Poza podejrzeniem” Miry: podgląd dolnej karty talii,
  ochrona przed reakcją przeciwnika po rundzie (przykład: Kontrargument Nessy),
  osobna pula a spalanie wspólnej talii; przy obiektach reakcja sytuacji.
  Wspólne źródło UI/druku oraz opis w rozpisce pasywów.

- [x] Log `exploration_ui_7d3ae5182e`, zdarzenia 150/153/156: Nimra
  opłaciła test jedną kartą, potem Nessa uruchomiła „Przeciąganie rozmowy”
  ze spalaniem 3 kart. UI błędnie utrzymywał wyróżnienie „Teraz Nimra”.
  Reakcja ma teraz własny nagłówek i źródło, nazwę działania, zapowiedź kosztu,
  licznik pozostałych kart i zakończenie przed kolejną rundą. Podczas reakcji
  żaden bohater nie jest wyróżniony jako aktywny. Obiekty używają tego samego
  etapu bez przypisywania im działania NPC. Teksty w `text/ui/confrontation.json`.
- [x] Podgląd kosztu uwzględnia ochronę Garrana. Tożsamość reakcji pozostaje
  podczas zgłaszania kart, po odtworzeniu stanu i gdy zabraknie talii.
  Log rozróżnia źródło działania (`hero` / `reaction`). Zasady reakcji bez zmian.

## Konfrontacje — krytyczne wyniki — 21.09.2026

- [x] Naturalne 20: automatyczny sukces i maksimum kości efektu + premie,
  bez drugiego rzutu. Naturalne 1: automatyczna porażka i 1 dodatkowa karta
  spalania po obniżkach zwykłego kosztu. Zachowano pasywy, zużycie pomocy,
  odzysk przed kosztem oraz rozliczenie efektu przed końcem talii.
- [x] Wyróżnienie wyniku w UI, edytowalne komunikaty w `text/ui/confrontation.json`,
  opisy Łagodności i samouczka w `text/karty_postaci.json` oraz zasady
  rozmów/obiektów w `text/sciaga_graczy.json`. Starsze zapisy z oczekującym
  rzutem wpływu zachowują rozpoczęte rozstrzygnięcie.
- [x] Weryfikacja: 149 testów zasad, pasywów, zapisów, prezentacji NPC/obiektu
  i potwierdzeń, w tym 2 próby w Chrome z runami spalania. Odbudowano karty
  postaci (36 stron) i ściągę (4 strony); walidacja bez przepełnień.
- [ ] Podczas ogrania ocenić wpływ krytyków na tempo konfrontacji i presję talii.

## Eksploracja — bez warunków kart atutowych — 21.09.2026

- [x] Przejrzano 35 pasywów siedmiu postaci. Usunięto jedyny warunek
  wymagający kart atutowych: Skupiona myśl Nimry daje po sukcesie +1 wpływu
  / postępu za czarną kartę, maks. +2, również bez niebieskich kart.
  Zaktualizowano wspólne opisy UI/druku i dokumentację. Regresje obejmują
  sukces, porażkę, limit, odtworzenie zapisu i niezależność premii wszystkich
  postaci od przypisania koloru atutowego.
  Odbudowano `print/karty_postaci_A4.pdf` (36 stron); zmieniona mata Nimry
  przeszła walidację układu i kontrolę tekstu w wynikowym PDF.

## Połączenie USB — 21.09.2026

- [x] Po zmianie numeru portu `/dev/ttyUSB0` → `/dev/ttyUSB1` włączono
  domyślne automatyczne wyszukiwanie (`hardware.serial_port: ""` w `board/config.json`).
  Aplikacja sprawdza dostępne porty po kolei, rozpoznaje gotową planszę po
  protokole v2 i ponownie odczytuje listę przy każdym połączeniu.
  Niedostępny port, rozłączenie podczas próby oraz obcy/niezgodny firmware
  nie blokują dalszego szukania; końcowy błąd zachowuje szczegóły diagnostyczne.
  Testy obejmują również zmianę numeru portu przy ponownym połączeniu.
  Weryfikacja: 29 testów (`hardware/test_serial_probe.py`, `test_connection_backends.py`)
  oraz rzeczywiste automatyczne znalezienie `/dev/ttyUSB1` bez podania portu.
  Produkcyjny transport na rzeczywistej planszy potwierdził firmware v2_2,
  HELLO i PING/status: `ready: true`, `state: idle`, `i2c_errors: 0`.
  Port zamknięto po próbie; nie zmieniano firmware ani WLED.
- [x] Błąd otwarcia wskazanego portu zachowuje przyczynę systemową zamiast
  sugerować brak odpowiedzi protokołu. UI pokazuje szczegół błędu serwera.
  Testy wykrywania używają atrap portów, bez podłączania sprzętu.

## UI laptopa i materiały Misji 0 — 21.09.2026

- [x] Log `exploration_ui_835773ee9e`, zdarzenie 98: nieudany test Garrana
  (11 + 2 = 13, ST 19) przyznał Brakce i Nimrze pomoc +1. Podpis „Test +0”
  pokazywał sam bonus many. Karta bohatera pokazuje teraz osobno „Mana”
  i otrzymaną „Pomoc” z czasem obowiązywania, również podczas doboru kart.
  Odtworzenie przebiegu potwierdza doliczenie pomocy i jej zużycie dopiero
  po próbie (udanej lub nieudanej); stan rzeczywistej sesji nie jest zmieniany.

- [x] Naprawiono ciemny tekst białej karty w doborze many: wspólne ciemne
  tło oferty ma jawny jasny kolor opisów, niezależnie od koloru symbolu.
  Podpis „Ta karta aktywuje:” poprzedza konkretną nazwę i opis zdolności.
  Test przeglądarkowy sprawdza obecność opisów i kontrast białej oraz czarnej karty.

- [x] Nowy widok w aplikacji: konfrontacja z jedną kartą pomocy i symbolami
  many; szczegóły premii i efektów pod runami 24/25. W walce jeden lewy
  tor z portretami, PW i stanami oraz prawa karta akcji/celu; podgląd
  uczestnika jest niezależny od aktywnej tury. Zakres: laptop, bez wersji mobilnej.
- [x] Sterowanie od launchera przez runy i −/+/✓/↩, wybór do sześciu
  bohaterów, osobne konteksty menu, dziennika, ściągi i szczegółów.
  Zamknięcie przywraca wejście bieżącej gry; stare zdarzenia i release
  nie przejmują następnego panelu. Obowiązkowe operacje kart zachowują priorytet.
- [x] Edytowalne treści w `content/scenarios/misja_0_dzwon/`: `text/ui/`,
  narracja `text/`, wspólne `text/karty_postaci.json` i osobne
  `text/sciaga_graczy.json`. Gra i druk korzystają z tych samych źródeł;
  edycja ściągi odświeża się niezależnie od kart. Instrukcja: [EDITING.md](content/scenarios/misja_0_dzwon/EDITING.md).
- [x] Pięć gotowych PDF-ów w `print/`: misja 10 stron (kalibracja 250/244),
  wariant nominalny 25 mm — 10 stron, karty postaci — 36, ściąga — 4,
  znaczniki — 1. Zachowane wymiary kart; starsze pliki w `print/archive/`.
  Generator zakończony bez przepełnień; zgodne manifesty i liczby stron,
  obejrzane strony postaci, akcji, zasad, kafli, handoutów i przedmiotów.
  Gotowe PDF-y mogą być wersjonowane; oba komplety map zoptymalizowano
  do około 1,65 MB przy zachowaniu geometrii i czytelności.
- [x] Aktualna instrukcja startu, edycji i drukowania jest w folderze Misji 0.
- [x] Weryfikacja wdrożenia: testy `session_copy`, `session_board_navigation`,
  `tabletop_combat`, `session_zero_materials`, źródeł kart, języka druku,
  pasywów, launchera oraz prezentacji i potwierdzeń konfrontacji.
  Chrome: menu startowe i sześciu bohaterów, rozmowy Nessy/wozu dla 3 i 6 osób,
  szczegóły 24/25, pomoc, obowiązkowe operacje kart, menu i przewijanie ściągi;
  rozdzielczości laptopowe 1131×720 i 1300×720.
  Rzeczywisty runtime walki: 31 kontroli podglądu uczestnika, akcji i celu,
  anulowania oraz przejścia do kości. Test Misji 0 potwierdza setup sześciu
  postaci, zapis/wznowienie, zmęczenie i rozejm. Sprawdzone liczby stron pięciu PDF.

### Projekt poprzedzający wdrożenie i pozostałe sprawdzenia

- [x] [UI, 20.09.2026] Audyt obecnej prezentacji i projekt hierarchii informacji dla fizycznej
  planszy bez mapy na ekranie: [propozycja i makieta](docs/ui/PROPOSAL.md).
  Doprecyzowany kierunek: Test / Pomoc / Podgląd, jedna karta odbiorcy
  pomocy przełączana −/+ z licznikiem, wykonanie pomocy stałą runą osoby;
  dotychczasowe symbole many zamiast nazw i liter; w walce „Wybierz akcję”
  i podgląd po naciśnięciu runy, z fizycznymi kartami postaci jako źródłem opcji.
  Makieta rozmowy ma także górny pasek symulacji fizycznych −/+ oraz run
  odbiorców, testu i podglądu; przyciski −/+ w karcie pomocy pozostają.
  Szczegóły rozmowy dostępne runami: Klucz (24) — premia, Gwiazda (25) —
  efekty; także po zużyciu działania. W oknie −/+ przewija, Accept/Decline wraca.
  Uzupełniony kierunek walki: jeden pionowy tor wszystkich uczestników
  po lewej, portrety przeciwników, aktywna tura wyróżniona niezależnie od
  kursora podglądu −/+; bez poziomego toru i dolnego paska drużyny.
  Po prawej karta: runa akcji → wskazanie figurki → portret i warunki celu
  → Accept; Decline cofa krok, podglądy nie wydają zasobów. PW, tymczasowe
  PW, stany i premie z aur wraz ze źródłem i momentem wygaśnięcia.
  Makieta dokumentuje zatwierdzony kierunek; wdrożenie runtime opisano wyżej. Atlas portretów i prompt: docs/ui/assets/PROMPTS.md.
  Przycisk przejścia w narracji używa symbolu ✓ z fizycznego Accept.
  Przy wyborze celu duży nagłówek zastępuje krótki podpis akcji; portret
  i warunki celu są główną treścią, koszt pozostaje przy zatwierdzeniu.
- [ ] [Ogranie nowego UI] Porównać czytelność przy stole dla 3 i 6 osób:
  odbiorcy pomocy (0, 1 i wielu), wyróżnienie aktywnej tury i oglądanego
  uczestnika, długie stany, 0 PW, wejście/wyjście z aury oraz drain.
  Sprawdzić sąsiadujące figurki, nieaktualny cel i cofanie przed płatnością.
- [ ] [Plansza, pełna próba sprzętowa] Przejść Misję 0 od uruchomienia
  aplikacji bez myszy: drużyna, scenariusz, setup, narracja, kości, karty,
  walka, szczegóły, dziennik, menu i wynik. Sprawdzić wznowienie, zgodność
  fizycznych stosów, rozłączenie i automatyczny powrót po odzyskaniu planszy.
- [ ] [Plansza, propozycja UI] Osobno sprawdzić podgląd pola uczestnika
  i jednej aury przez istniejące LED; pierwszeństwo dla ruchu, celu i wejścia
  gracza. Zasięg i skutki dostarcza silnik, adapter tylko je prezentuje.
  Porównać czytelność z opcjonalnymi drukowanymi znacznikami stanów;
  nie wymagać nowego sprzętu ani mapy na ekranie.

- [x] UI pasywów i potwierdzenia odzysku: opisy tekstowe bez schematu stosów kart.

- [x] Kolumny bohaterów w konfrontacji: zebrana mana i nazwy aktywnych pasywów, bez opisów ani diagramów.

- [x] Dobór many w konfrontacji: portret aktywnego bohatera tylko przy wyborze karty z oferty. Zgłaszanie kolorów i pozostałe etapy pokazują ilustrację sceny (w rozmowie z Nessą — Nessę).

- [x] [Komplet kafli w stylu próbki wozu] 18 kafli z 14 ilustracjami tuszem

- [x] Mana: 6 fizycznych kart, premia +1/karta, atut = 2 ładunku; progi 2/4/6. Silnik, migracja zapisów, UI, samouczki, zestawy PDF i ewaluacja zaktualizowane. [Zasady](docs/TRUMP_MANA.md).
- [ ] Ograć nowy model many w Misji 0: tempo odblokowania ultów i drainów przy 3–6 osobach; wartości ST i obrażeń na razie pozostają.
  (13 nowych z image_gen i zaakceptowany wóz). Ramka przez cały kafel,
  jedna linia podpisu: pogrubiona nazwa — zwykły tekst efektu. Zachowane
  obrysy, pola I i skale obu PDF-ów; grafiki i prompty w maps/illustrations/ink_v3.
  Weryfikacja: 8 testów kafli, oględziny 14 ilustracji i 5 arkuszy, pomiar
  18 podpisów w Chrome (mieszczą się także w nominalnych polach 25 mm).

- [x] [Próbny kafel wozu z ramką v3] Jedna ilustracja image_gen: rozpoznawalny
  drewniany wóz w czerni i bieli. Ramka przez oba pola 2×1, poniżej efekt
  „BLOKUJE RUCH” i nazwa, wszystko w obrysie 50×25 mm. Osobny podgląd i PDF-y
  w maps/prototypes/cart_v3; ocena próbki poprzedza zmianę reszty zestawu.

- [x] [Wektorowe ilustracje kafli Misji 0] 14 lokalnych czarno-białych SVG
  dla 18 kafli: wyposażone wnętrza, przedmioty, osłony i gruz. Edytowalne
  przypisania artwork w maps/cutouts.json; oba PDF-y zachowują skalę i siatkę.
  Podpis trudnego terenu: „KOSZT RUCHU ×2” i „10 ft / pole”.

- [x] [Kafle Misji 0 do wycięcia, 2026-09-16] 18 kafli w 7-stronicowym PDF A4:
  całe budynki, punkty eksploracji i teren bojowy. Katalog obrysów korzysta z
  danych walki; trzy osłony +2 KP, dwa kafle gruzu i dwa głazy działają w silniku.
  Skala areny 250/244 oraz wariant nominalny 25 mm; pełne podświetlenie miejsc
  w setupie, link PDF w UI. Generator: scripts/build_mission_zero_cutouts.py.
  Weryfikacja: 38 testów (kafle, misja i Chrome 390 px); geometria A4,
  zgodność terenu i startów dla 3–6 osób, LED i pobranie PDF. Oba PDF-y
  mają po 7 stron; obejrzano wszystkie arkusze wariantu kalibrowanego.

# TODO

- [x] Orientacja Gildii od strony run: kafle G01–G03 obrócone o 90°
  w lewo, obrysy LED dopasowane, pola interakcji bez zmian. Rozdzielony
  rozmiar wydruku i obrót na planszy; obecne wycinanki nadal pasują.
  Zaktualizowane instrukcje oraz mapka w komplecie PDF Misji 0.
- [x] Posterunek: wszystkie P01–P15 obrócone podpisem ku runom.
  Obrysy terenu i LED zgodne; gruz omija strefę startową, woźnica
  przesunięty na (6,13) poza magazynek. Pola I i wycinanki zachowane.
  Zaktualizowane instrukcje, podglądy i komplet PDF Misji 0.

- [x] Konfrontacje Misji 0: portret rozmówcy i portrety uczestników, kompromis
  ujawniany dopiero przy ofercie, przygotowanie opisujące tylko skład talii.
  Widok dopasowany do wysokości ekranu, przewijanie +/−, wybór pod każdą
  odkrytą kartą; runy raportowania i wyboru świecą kolorami many
  (czarna: intensywny fiolet). Rzuty zachowują własną obsługę +/−.

- [x] Koncept Garrana 1/3: jedna strona A4 ze statystykami, pięcioma kolorami
  i pasywami walki/eksploracji; miejsca na karty 63 × 88 mm wsuwane z boków,
  trzy stosy z lewej i dwa z prawej. Osobny PDF i podgląd ułożenia w
  content/print/prototypes/garran_trio_v1. Do oceny przed dalszym redesignem.

- [x] Pasywy bez limitów tur/odpoczynku: Garran rozdzielona ochrona, Mira ukrycie
  i flanka, Erynd każde pełne PW, Brakka jedno uratowanie na cykl draina.
  Status gotowe/zużyte, ikony z obwódką kumulacji, trwały Oddech eksploracji,
  aktualizacja kart, samouczka i kompletu wydruków.

- [x] Usunąć darmowe pasywy wszystkich siedmiu bohaterów; kluczowe cechy
  odblokowywać kolorami nasycenia. Obsłużyć utratę koloru, drain, nową walkę
  i migrację zapisów; pozostawić skazy. Zaktualizować UI, lekcje i karty.

- [x] Dwa kompletne wydruki: Misja 0 (kafle → rozkaz → pokwitowania → przedmioty)
  oraz bohaterowie (pełne karty postaci → jej startowy ekwipunek, osobno dla
  każdego z siedmiu bohaterów). Wspólny generator z aktualnych źródeł,
  zachowana kalibracja kafli, spisy stron i manifesty ułatwiające druk drużyny.

- [x] [Setup Misji 0 kaflami, 2026-09-16] Zastąpić mapy poglądowe
  podglądem całego kafla z jego grafiką, ramką i polem I; instrukcja po prawej.
  Duże kafle osobno, małe przeszkody walki w seriach; teren przed figurkami.
  Podświetlać słabiej obszar kafla, mocniej pole interakcji, potwierdzać ✓.
  Wspólna geometria z wydrukiem, edytowalne grupy w maps/setup.json,
  weryfikacja pełnego zestawu kafli i ta sama kolejność przy ponawianiu walki.
  Po walce zachować teren, zmienić figurki i dodać kafel rozmowy.
  Weryfikacja: 21 testów setupu, adaptera LED, Misji 0 i przeglądarki;
  oględziny podglądu biura i zbrojowni, pełne przejście do walki dla 6 osób.

- [x] [Czytanie intro z planszy, 2026-09-16] Usunąć link do wycinanek
  z panelu rozgrywki (przygotowanie przed sesją). Intro świata, bohaterów
  i wezwania do Nessy ma przewijany opis: + w dół, − w górę, ✓ dalej.
  Nawigacja pozostaje widoczna także po zmianie wysokości komunikatu planszy.
  Przewijanie nie zmienia stanu misji; aktualizacje panelu zachowują pozycję,
  nowy fragment ją zeruje. Spóźnione zdarzenia z poprzedniej sceny są pomijane,
  a podczas rzutów +/− nadal służą do wprowadzania wyniku.

- [x] [Narracyjne otwarcie Misji 0, 2026-09-16] Osobna komiksowa ilustracja
  Pogranicza zamiast napastników przy dzwonie; narracja świata, osobne pełne
  portrety i stałe opisy wybranych bohaterów, zamknięcie o powstaniu drużyny
  i pierwszym wezwaniu do Nessy. Rozwinięte opisy siedmiorga bohaterów
  zsynchronizowane z profilami autorskimi. `image` i `image_layout` w
  `text/index.json` sterują grafiką i układem bez zmiany kodu. Nowy obraz
  i prompt w paczce scenariusza; posterunek dopiero przy dotarciu do celu.

- [ ] [Pomysł: arena jako konfigurowalna walka, 2026-09-16] Docelowo
  przebudować arenę/poligon w modularny tryb walki konfigurowany przez UI:
  wybór składu drużyny, typów i liczby przeciwników, rozstawienia bohaterów
  i przeciwników oraz przeszkód i kafli terenu z ich efektami mechanicznymi.
  Po konfiguracji przejść przez setup fizycznej planszy i uruchomić walkę
  według aktualnych zasad. Tryb ma służyć do swobodnego testowania starć
  i zestawień; Misja 0 pozostaje samouczkiem drużynowym podczas przygody.
  Na razie wyłącznie zapis pomysłu — bez przebudowy obecnej areny.

- [x] [Wybór drużyny bez przewijania, 2026-09-16] Dopasować siedem kafelków
  bohaterów i nawigację do wysokości okna. Na mniejszych ekranach pozostawić
  krótki nagłówek roli; szczegółowe zasady są na kartach postaci. Sprawdzić
  dziewięć rozmiarów widoku, limit sześciu bohaterów, powrót ze scenariuszy
  i wybór runami (13 testów przeglądarkowych).
  Doprecyzowanie oprawy: portrety 64–88 px i jedno zdanie o stylu gry,
  pokazywane zależnie od dostępnego miejsca w kafelku. Sprawdzone ponownie
  na dziewięciu rozmiarach okna, bez przewijania i ucinania opisów.

- [x] [Komiksowa oprawa Misji 0] Wariant `comic_v2`: trzy sceny, Nessa i siedmioro
  bohaterów; wspólny styl, żywe kolory i przełączanie przez `visuals.json`.
  Weryfikacja: test przełączania wariantu/cache oraz 11 poprawnych odpowiedzi
  HTTP obrazów i nowe portrety w payloadzie misji. Oryginały zachowane lokalnie.

- [x] [Masterplan misji 0] Zapisano `content/scenarios/misja_0_dzwon/MASTERPLAN.md`:
  lokalna edytowalna paczka narracji i mediów, profile i narrator, intro składu,
  odprawa/negocjacje, droga/zmęczenie, walka/poddanie, eksploracja, trzy decyzje
  i rozliczenie. Podlinkowano w kontekście i projekcie gry; bez zmian runtime.
- [x] [Implementacja misji 0] Lokalna paczka, teksty/profile i ilustracje, mapy PDF,
  wybór 3–6, checkpointy, wspólne konfrontacje, zmęczenie −2 przez k4 rund,
  warianty wrogów i poddanie, eksploracja, realne przedmioty/mikstury i rozliczenie.
  Zapis końcowy zachowuje drużynę i przyszłe zobowiązania. Poligon zachowany.
  Weryfikacja: 122 testy w sekwencyjnych partiach (misja, Chrome 390/1100,
  konfrontacje, menu eksploracji, launcher, premie ładowania); oba PDF po 9 A4.
- [ ] [Ogranie misji 0] Sprawdzić fizyczny stół, szczególnie 3 i 6 osób, długość
  walki ze zmęczeniem 4 rund oraz tempo poddania. Raport 1960 konfrontacji daje
  średnio 3,3–3,6 rund; mniejsze drużyny częściej przegrywają. Audio na końcu.

- [x] [Strategia skalowania 3–6 osób] Zapisano uzgodnione zasady w
  `docs/PARTY_SCALING.md` i podlinkowano w kontekście, projekcie gry oraz
  instrukcji tworzenia scenariuszy. Baza czteroosobowa, wspólne karty,
  talia 10/osobę, warianty walk i proporcjonalny opór/presja eksploracji.
  Liczby do ogrania; bez zmian w mechanice i UI.
- [ ] [Próby skalowania przy budowie scenariusza] Warianty 3/4/5/6, wybór sześciu
  bohaterów i ewaluacja wszystkich 98 składów są gotowe w Misji 0. Pozostaje
  ograć czas scen, presję many i brak podatnych metod przy fizycznym stole.
  Pełny balans walk wymaga pomiaru obrażeń, leczenia i powaleń poza obiegiem
  kart. Punkt odniesienia: `docs/PARTY_SCALING.md`.

- [x] [Ukrycie dawnych umiejętności] Karty i UI bohaterów many nie pokazują
  osobnej listy umiejętności ani nieaktywnych ekspertyz. Dane zachowane na
  przyszłość; działania (np. ukrycie, chwyt, pułapki) opisane przez cechy.
  Test nadal: k20 + cecha + premia z naładowania + inne bonusy, bez zmian
  w obliczeniach. Ujednolicono opisy w panelach, kartach i lekcji naładowania.
  Pliki: `character_creation/physical_mana_help.py`, `physical_cards/mana_print*`,
  `ui/routes.py`, `ui/exploration_app.py`, widoki postaci i eksploracji,
  opisy katalogu many i `application/pooled_mana_training.py`.
  55 testów przeszło w sekwencyjnych partiach: prezentacja, wydruki,
  cztery formaty A4, UI 390/1100 px, chwyt i pchnięcie. Odświeżono 28 PDF,
  cztery zbiory oraz 67-stronicowy pakiet areny; sprawdzono liczbę stron
  i brak dawnych sekcji umiejętności/ekspertyzy we wszystkich 32 PDF postaci.

- [x] [Naładowanie zamiast biegłości] Bohaterowie osobistej many: testy ataku,
  obron, umiejętności i narzędzi bez biegłości/ekspertyzy, z premią +0/+2/+4/+6
  przy 0/6/12/21 pkt. Konfrontacje używają wybranego progu raz; zachowane
  zapisane pule i postęp, aktualizacja oczekujących testów starego zapisu.
  Chwyt/pchnięcie, Uderzenie tarczą, koncentracja, pułapki, Duchowy oręż
  i podglądy stosują tę samą premię; obrażenia, wpływ i ST zdolności bez zmian.
  UI postaci/puli, samouczki i 28 PDF + cztery zbiory + pakiet areny odświeżone.
  248 testów przeszło w sekwencyjnych partiach: reguły, regresje starszych
  profili, samouczki, zapis, wydruki, Chrome 390/1100 px i cztery formaty A4.
  Pliki: `rules/charge_rolls.py`, `rules/pooled_mana.py`, `actors/proficiencies.py`,
  `actors/skills.py`, `combat/mana_charge.py`, ścieżki testów w `application/`,
  `ui/`, `physical_cards/mana_print*`; opis w `docs/MANA_CHARGE_V02.md`.

- [x] [Nasycenie maną na kartach] Pięć osobnych punktów z symbolami many
  zamiast liter dla wszystkich siedmiu bohaterów. Opisy z katalogu pasywów,
  wspólna uwaga pod listą; układ Loriana dopasowany bez zmniejszania czcionki.
  Zaktualizowano `physical_cards/mana_print*`, stronę kart (`ui/routes.py`,
  `ui/templates/physical_mana.html`) i generowaną rozpiskę archetypów.
  31 testów wydruków i układu czterech formatów przeszło.

- [x] [Czytelne opisy kart] Osobne pola: nazwa, wymagany ładunek, akcja,
  spalanie, efekt i rzeczywiste podbicia. Ten sam układ w PDF-ach, na stronie
  kart i w oknie zdolności. Rozwinięte opisy Garrana, jednoznaczna nazwa
  zielonego pasywu (Wytchnienie). 44 testy przeszły: wydruki, układ czterech
  formatów, runtime oraz okna zdolności 390/1100 px. 28 PDF (po 8 stron),
  cztery zbiory i HTML/JSON odświeżone. Reguły walki bez zmian.
  Pliki: `physical_cards/mana_ability_text.py`, `mana_print*`, katalog many,
  `ui/shared_mana.py`, widoki kart i `docs/BOARDGAME_ARCHETYPES_LEVELS_1_3.md`.

- [x] [Drużynowe konfrontacje eksploracji] Nowy silnik NPC/obiektów: trwałe
  pule, dobór do 21+, progi testu i spalania, wspólny opór, podatności ST/kość,
  pomoc, reakcje i drain kończący próbę. 35 pasywów kolorów i właściwe cechy.
  UI/runy, osobne rzuty testu i wpływu przez fokus/−/+/podsumowanie, zapis
  i wznowienie, wybór składu 1–5, 84 przypadki, przygotowane 21/reakcja/drain.
  Cztery warunki, historia rezultatów i zobowiązań; zgodność starych zapisów.
  146 testów w 10 plikach przeszło (sekwencyjne safe_pytest), w tym Chrome
  390/1100 px i pełne próby HTTP/runy. 2520 symulacji: drużyny 3–5 osób
  kończą średnio po ok. 3–3,3 rundy. Odświeżono 28 PDF, cztery zbiory,
  HTML/JSON/manifest i pakiet areny 67 stron; sprawdzono liczbę stron i treść.
  Opis: `docs/PARTY_CONFRONTATIONS.md`, raport: `docs/reports/PARTY_CONFRONTATIONS_V01.md`.
- [ ] [Konfrontacje: próba przy stole] Sprawdzić rzeczywisty czas zgłaszania
  kart i dwóch rzutów, wartość wsparcia odpornych metod, czytelność pasywów
  oraz sceny dla 1/3/5 osób. Dostosować profile konkretnych przygód po ograniu.

- [x] [Wspólny wybór walki i eksploracji] Hierarchia: postać → Walka /
  Eksploracja → Po kolei / Wybierz ćwiczenie, z powrotem na każdym poziomie.
  127 lekcji eksploracji w tym samym menu run; osobny postęp kursu, pojedyncze
  próby bez przesuwania kursu i powrót do właściwej strony. Pułapka w przypadkach
  walki. Stały powrót/restart również przy setupie i kościach eksploracji.
  110 testów z 10 plików przeszło, w tym mobilny/desktopowy Chrome i trzy
  pełne próby strony przez HTTP/runy (obiekt, przekroczenie i wyjście z kości).
  Szczegóły: `docs/RECRUITMENT_ARENA.md`.

- [x] [Samouczek: pojedyncze przypadki i kurs] Po wyborze każdej z siedmiu
  postaci wybór „Po kolei” / „Wybierz ćwiczenie”. Wszystkie 148 lekcji,
  podbicia i siedem pojedynków dostępne bez wcześniejszych zaliczeń; runy,
  strony −/+, powrót do tej samej listy. Osobne zaliczenia prób zachowują
  postęp kursu. Szybki restart/wyjście czyści także nierozstrzygniętą płatność,
  spalenie i rzuty; zapis zachowuje tryb. 101 testów w pięciu plikach
  przeszło, w tym Chrome 390/1100 px. Opis: `docs/RECRUITMENT_ARENA.md`.

- [x] [Ładowanie many 2.0] Zachowanie ładunku, próg kończący dobór 21+,
  odrębne pasywy 35 kolorów jako statusy, spalanie akcji i podbić, wygasanie
  rundy, pełny drain, Lorian, skazy, UI, 148 lekcji, karty i nowy ewaluator.
  272 testy w 16 plikach przeszły; 4704 próby ekonomii. Odświeżono 28 PDF
  bohaterów, cztery zbiory i pakiet areny 67 stron.
  Reguły i wyniki: `docs/MANA_CHARGE_V02.md`.
- [ ] [Próba przy stole many 2.0] Ocenić tempo spalania, powtarzanie ultów,
  specjalizację kontra obronę oraz odzysk Loriana w pełnych walkach.


- [x] [Punkty many w UI] Jawna suma nad akcjami i w oknach kart/płatności,
  wartości kart, podgląd sumy po doborze i porównanie puli z bazowym progiem zdolności.

- [x] [Pule many 1/7] Wersjonowany katalog siedmiu bohaterów: punkty, kolory,
  progi, pasywy/skazy, bezpłatne reakcje i czas O do końca walki.
- [x] [Pule many 2/7] Wspólny czysty silnik i skrypt ewaluacji ekonomii;
  raport bazowy i sprawdzający: łącznie 8960 prób, HTML/CSV/JSON z katalogiem.
- [x] [Pule many 3/7] Integracja płatności i rzeczywistych efektów wszystkich
  bohaterów; strojenie/odzysk Loriana, zachowany zwykły atak bez many.
- [x] [Pule many 4/7] Spalanie oferty/wierzchu, uwięzienie i uwolnienie przez
  śmierć wroga, pełny drain i świeża talia przy każdej nowej walce.
- [x] [Pule many 5/7] Runy, podgląd pul i kosztów, zapis operacji kart.
  Zapisu podczas nierozstrzygniętej zdolności nadal nie dopuszcza istniejąca blokada.
- [x] [Pule many 6/7] 134 lekcje: dobór/oszczędzanie/spalanie/więzienie/drain
  oraz zdolności i podbicia; finałowy wróg atakuje manę. Zachowane NPC i obiekty.
- [x] [Pule many 7/7] Zaktualizowane cztery formaty kart i pakiet areny,
  testy reguł, rzeczywistych lekcji, zapisów, wejść planszy i przeglądarki.
  Opis i ograniczenia: `docs/POOLED_MANA_IMPLEMENTATION.md`.
- [ ] [Balans po ograniu] Zebrać uwagi użytkownika o tempie, akcjach darmowych,
  progach ultów i presji na talie 25/30 kart; porównać kandydatów na tych samych seedach.
- [ ] [Dalsza ewaluacja] Rozszerzyć ekonomiczny runner o pełne walki,
  sytuacyjne pasywy/skazy i efekty manipulacji Loriana. Obecny raport ich nie modeluje.

- [x] [Rozmowy: plan czterech warunków startowych] Zapisano reguły,
  konsekwencje, zakres siedmiu postaci, runy Klucz/Gwiazda, migracje oraz
  cztery lekcje z rzeczywistym wyborem w
  `docs/SOCIAL_MANA_DECISIONS_IMPLEMENTATION_PLAN.md`. Wdrożone; bieżący opis w `docs/EXPLORATION_MANA_IMPLEMENTATION.md`.
- [x] [Rozmowy 1/6] Jawny typ wyniku, stan warunku i migracje v1→v2
  bez nakładania warunków na rozpoczęte próby.
- [x] [Rozmowy 2/6] Jednorazowe porozumienie 15–17 i drażliwy kolor;
  dodatkowy cel za układ kolorów i jednorazowe ustępstwo (karta = 1 za
  zobowiązanie). Pierwszeństwo 21/przekroczenia, koszty i przerzut Loriana.
- [x] [Rozmowy 3/6] Sceny wybierane po id, cztery warianty Ireny, siedem
  metod i wspólny resolver rzeczywistych konsekwencji.
- [x] [Rozmowy 4/6] Nowe decyzje przez runy, UI i maski LED/skanu,
  zapis oferty, aktualne rewizje i niepowtarzalne skutki.
- [x] [Rozmowy 5/6] Cztery lekcje z własnym wyborem, ćwiczenia samodzielne
  i reakcja Nessy z opcjami zależnymi od uzyskanego wyniku.
- [x] [Rozmowy 6/6] Ściąga, wszystkie formaty kart i pakiet areny,
  testy Chrome/zasad/zapisu oraz porównanie strategii przed próbą przy stole.
  Walidacja: 160 ukierunkowanych testów przeszło, 5600 symulowanych prób,
  28 zestawów PDF odświeżonych, pakiet areny 67 stron i sprawdzona strona ściągi.

- [ ] [Rozmowy: próba przy stole] Ograć cztery warunki i obie drogi wyboru,
  szczególnie opłacalność listu i pogoni za kolorem. Dopiero po tej próbie
  dobierać nowe warianty do konkretnych przygód.

- [x] [Eksploracja: wspólny widok rzutów, 2026-09-14] NPC, obiekty i pułapki
  używają fokusowania jednej kości, −/+ na planszy, ✓ do kolejnej kości,
  podsumowania i poprawki przez ↩. Końcowe ✓ rozstrzyga test. Przy utrudnieniu
  podsumowanie wybiera niższe k20 i dolicza modyfikatory raz. Panel w fazie
  rzutu należy do kości; nie uruchamia metod ani powrotu do postaci. Zachowany
  wspólny strumień wejścia i odrębny kontekst następnej kości/podsumowania.
  Walidacja: 54 testy — runtime 20, plansza 20, pełny Chrome 2, regresja
  kości walki 3, pułapki 9. `git diff --check` bez błędów.

- [x] [Eksploracja: wybory przez runy, 2026-09-14] Metody siedmiu postaci,
  pięć kolorów, pas/dobór, przerzut, pusta talia i nawigacja lekcji obsługiwane
  przez wydrukowane runy. Wspólny katalog zasila UI, legalne pola skanu i LED;
  tylko dozwolone wybory świecą. ✓ zatwierdza wpisane wyniki kości. Stałe
  przypisania metod przy brakujących bohaterach, blokada pasu po odkryciu
  oferty, wznowienie zapisanych stosów i ochrona przed starym skanem.
  Walidacja: 40 testów — runtime 20, skany/LED 17 (w tym wszystkie 14 metod),
  widoki Chrome 2 i pełna strona z wyborem przez planszę 1. Fizyczny sprzęt
  pozostaje do próby użytkownika. Opis: `docs/EXPLORATION_MANA_IMPLEMENTATION.md`.

- [x] [Garran: Bastion od SIŁ i automatyczny Kontratak, 2026-09-11]
  Bastion zapisuje przy użyciu premię KP równą modyfikatorowi Siły źródła
  (+4 dla Garrana z SIŁ 18); katalog, podgląd i objaśnienia używają tej zasady.
  Kontratak ma zapisany etap ruch/atak/brak celu: automatyczne pola ruchu do
  10 ft, ✓ kończy ruch lub pozostawia figurkę w miejscu, następnie automatyczne
  cele wyposażonej broni. Bez menu i run wyboru akcji dla obu uczestników.
  Po pierwszym ataku natychmiast synchronizuje LED-y ruchu sojusznika.
  ↩ czyści wybór pola/celu; płatność pozostaje wspólna. Brak celu pozwala
  przejść dalej bez ataku i kończy lekcję jako próbę do powtórzenia.
  Walidacja: 95 testów (11 przepływów Garrana, 8 nowych przypadków, 30 many,
  33 walkthrough, 11 aur LED, 2 Chrome), kompilacja i diff-check.
- [ ] [Wydruki po zmianie Bastionu] Przy następnym odświeżeniu kompletu kart
  wygenerować ponownie statyczne HTML/PDF: Bastion daje modyfikator SIŁ do KP.

- [x] [Nakładanie aur, 2026-09-11] Wspólny wybór najsilniejszego efektu
  danej aury na odbiorcę dla Osłony tarczą, Bastionu, Błogosławieństwa i
  Boskiej Opieki. Zachowanie wszystkich źródeł pozwala automatycznie wrócić
  do słabszego po ruchu, pokonaniu źródła lub utracie koncentracji.
  Boska Opieka wybiera jeden cały wariant: kara ataku, następnie obrażeń;
  promień służy tylko do sprawdzenia zasięgu. Łaska uzdrowienia wybiera
  najsilniejszą średnią premię i zużywa tylko jej źródło. Różne aury nadal
  się łączą; kilka Hymnów daje najwyżej jedną dodatkową akcję dodatkową.
  Walidacja: 55 testów (18 nakładania, 7 aur, 11 LED, 11 walkthrough Garrana,
  7 zdolności Garrana, 1 kar Boskiej Opieki), kompilacja i diff-check.

- [x] [Kontratak: instrukcja dla gracza, 2026-09-11] Osobny nagłówek
  „Teraz działa” dla uczestników 1/2 i 2/2, symbol ruchu z instrukcją
  opcjonalnego przemieszczenia i wyróżnione polecenie ponownego użycia runy
  Rozkazu do ataku. Potwierdzenie jednorazowej płatności oraz automatycznego
  przejścia po ataku, także przy pudle. Po wejściu w podgląd instrukcja
  ogólna ustępuje wyborowi pola/celu. Uaktualniona narracja lekcji.
  Walidacja: 11 testów przepływu Garrana i 2 testy Chrome (390/1100 px).

- [x] [Kontratak: zawieszenie po runie ruchu, 2026-09-11] Sesja
  `exploration_ui_b9ed4739ff` zatrzymała obsługę po odczycie (19,29).
  Podgląd aur tworzył deklarację many bez zdolności dla zwykłego ruchu
  podczas opłaconego Kontrataku, wywołując „Brak opłaconej zdolności”.
  Pomija teraz opcje niebędące aurami przed tworzeniem podglądu.
  Regresja przez API planszy obejmuje ruch i ✓ obu uczestników, zachowanie
  płatności oraz zakończenie ćwiczenia po trafieniu i pudle. Walidacja:
  22 testy przepływów Garrana i aur pozostałych bohaterów.

- [x] [Aury pozostałych bohaterów, 2026-09-11] Błogosławieństwo i Boska
  Opieka Dagny oraz Hymn Loriana używają wspólnego podglądu LED: zasięg,
  odbiorcy, podbicie promienia 5 → 10 ft, faza płatności i podsumowanie.
  Premie oznaczone turkusem, wrogowie w Boskiej Opiece złotem. Aktywne aury
  widoczne też w turze innej postaci, z pierwszeństwem bieżącej akcji;
  przesunięcie i utrata koncentracji aktualizują światła. Zasięg Hymnu
  korzysta z tej samej reguły co dodatkowa akcja. Ćwiczenie Hymnu ma pomocnika.
  Walidacja: 103 testy (11 nowych LED, 9 Garrana, 7 reguł aur, 30 wspólnej
  many, 13 wyboru celów, 33 walkthrough), kompilacja i `git diff --check`.
- [ ] [Próba aur Dagny i Loriana na planszy] Sprawdzić oba kolory odbiorców,
  przełączenie podbicia promienia, przesunięcie źródła/odbiorcy i zakończenie
  koncentracji; potwierdzić czytelność dużego zasięgu Hymnu.

- [x] [Garran: przejęcie, aury i kontratak, 2026-09-11] Sesja
  `exploration_ui_3892f8dd85`: Osłona towarzysza wracała do pierwotnego celu,
  gdy Garran był poza zasięgiem kukły; po płatności wyłączał się też ćwiczebny
  rzut. Przejęty atak zachowuje obrońcę, koszt i zużytą reakcję. Lekcja pokazuje
  6 obrażeń Garrana bez obrażeń pomocnika. Aury Osłony tarczą i Żelaznego
  bastionu pokazują zasięg oraz odbiorców w podglądzie/płatności/podsumowaniu.
  Wybór podbicia nadal rozróżnia przygaszone i zaznaczone cele. Kontratak
  udostępnia atak i tę samą runę również pomocnikowi bez prywatnej many;
  widoczne 1/2 i 2/2, bez dodatkowej płatności. Samouczek wymaga obu ataków.
  Walidacja: 129 testów (9 nowych przepływów Garrana, 40 ataków/tur wroga,
  13 celów planszy, 33 walkthrough, 30 wspólnej many, 4 Chrome), kompilacja
  zmienionych modułów i `git diff --check`.
- [ ] [Próba Garrana po poprawkach] Na planszy sprawdzić Osłonę towarzysza
  (cel: pomocnik, trafiony: Garran), oba zasięgi aur, białe podbicie Osłony
  tarczą i pełny Kontratak: Garran → pomocnik → zakończenie ćwiczenia.

- [x] [Jeden bieżący krok samouczka, 2026-09-11] Osobne wprowadzenie przed
  setupem, potem aktualny element pod nagłówkiem i krótkie polecenie ćwiczenia.
  Opis kursu, mapa i pomoc nie spychają bieżącej akcji poniżej ekranu.
  Teren po pełnym setupie pozostaje gotowy także przy ponowieniu pierwszej
  lekcji i zmianie bohatera. Zapis rozróżnia wprowadzenie i ustawianie;
  stare naciśnięcie ✓ nie zatwierdza następnego kroku. Walidacja: 72 testy
  (33 walkthrough, 7 nowe przejścia, 19 launcher, 9 setup, 4 Chrome),
  kompilacja zmienionych modułów Python i `git diff --check`.
- [ ] [Próba nowego przebiegu setupu] Na fizycznej planszy przejść wybór
  Garrana → opis → ustawianie → ćwiczenie, ponowić pierwszą lekcję i zmienić
  bohatera; sprawdzić fokus polecenia i brak ponownego ustawiania terenu.

- [x] [Wybór sojuszników na planszy, 2026-09-11] Cele okien wspólnej many
  przez pola figurek zamiast dropdownu: legalne przygaszone, zaznaczone jasne,
  ponowne naciśnięcie odznacza, ✓ wymaga legalnego wyboru. Białe podbicia
  Osłony tarczą obsługują kilka różnych celów jednym zatwierdzeniem;
  po zapłacie ↩ czyści zaznaczenie bez cofania kosztu. Walidacja ponownie
  sprawdza wszystkie cele przed nadaniem efektów. Natywne maski i rewizje
  odcinają stare panele kości i spóźnione kliknięcia. Testy adaptera i widoku
  390/1100 px; fizyczny test wyboru pozostaje poniżej.
- [ ] [Próba wyboru sojuszników na planszy] W samouczku Garrana sprawdzić
  kontrast LED, odznaczanie, wybór dwóch sojuszników do białych podbić,
  zatwierdzenie ✓ oraz powrót do kolejnego kroku.

- [x] [Menu sterowane runami, 2026-09-11] Kafelki menu głównego, wczytanie,
  profile bohaterów i wybór drużyny/scenariusza obsługiwane podświetlonymi
  runami; wybór bez dodatkowego ✓. ↩ wraca o ekran/etap. Siedem run wyboru
  bohaterów walkthrough od razu rozpoczyna/ponawia ich ćwiczenia, a powrót
  przywraca maskę rosteru. Jeden adapter USB/WLED także poza /play; token
  dokumentu, jednorazowe zdarzenie i anulowanie odcinają stare skany/wyjścia.
  Symbole pochodzą z istniejącego wydruku panelu, bez zmian firmware'u.
- [ ] [Próba menu na fizycznej planszy] Po restarcie aplikacji przejść
  menu → arena → postać → powrót oraz nowa gra → drużyna → scenariusz.
  Sprawdzić podświetlenie i krótkie naciśnięcia przy zmianie ekranów.

- [x] [Bezpośredni Ethernet WLED, 2026-09-11] Gledopto GL-C-618WL,
  firmware 16.0.1, 620 LED: stały adres 192.168.50.2/24, brama 192.168.50.1.
  Komputer: profil NetworkManager „Plansza-WLED”, enp2s0, 192.168.50.1/24,
  bez trasy domyślnej, autopołączenie. WLED wymaga niezerowej bramy także
  przy połączeniu bez routera. Tymczasowy DHCP wyłączony po konfiguracji.
  Aplikacja przełączona na nowy adres; 10 odczytów i 10 poleceń HTTP bez
  błędów, mediana polecenia 10,8 ms. Szczegóły: docs/WLED_DIRECT_ETHERNET.md.
- [ ] [Próba gry po Ethernet] Po ponownym uruchomieniu aplikacji sprawdzić
  podświetlenie podczas samouczka i pełny start zestawu po odłączeniu zasilania.
- [x] [Timeouty Ethernet przy aktywnym Wi-Fi WLED, 2026-09-11] Wyczyszczono
  zapisane SSID przez formularz ustawień, zachowując adres/bramę Ethernetu,
  konfigurację LED, hasło oraz awaryjny hotspot. Po restarcie domyślne
  `Your_Network`, brak połączenia Wi-Fi. Łącznie 40 odczytów/poleceń HTTP
  przed i po restarcie bez błędów; po restarcie mediana poleceń 10,15 ms,
  cały panel 37,5 ms. Szczegóły: docs/WLED_DIRECT_ETHERNET.md.

- [x] [Czytelne polecenia samouczka, 2026-09-11] Osobny blok „Teraz zrób”
  ze złotą ramką, mocniejszym tłem i większym, pogrubionym poleceniem
  w oknie narracji oraz przy bieżącym ćwiczeniu.

- [x] [Pozycja obronna w walkthrough, 2026-09-11] Sesja
  `exploration_ui_610a6683d0`: Drugi oddech i oba Uderzenia tarczą zaliczone;
  potem ponowne naciśnięcia runy Pozycji obronnej, bez ✓ (potwierdzone przez
  gracza). Wskazówka lekcji przechodzi z wyboru zdolności do niebieskiego ✓,
  a następnie do odłożenia many; usunięte mylące „✓ ponownie” w podglądzie.
  Test obejmuje powtarzanie runy bez kosztu, podgląd, płatność, zaliczenie
  i następną sytuację. Błąd HTTP/walidacji WLED trafia teraz do diagnostyki
  ramek także podczas przerwy między ponowieniami; wejście USB niezależne.
- [ ] [Zanik aktualizacji WLED, sesja 610a6683d0] Po 08:56:31 UTC
  brak potwierdzenia bieżących ramek aż do końca ćwiczenia. Dotychczasowy
  log nie zachował przyczyny HTTP. Sprawdzić kolejną fizyczną sesję z nową
  diagnostyką; bieżący odczyt `/json/info` działa (336 ms, RSSI −57 dBm).

- [x] [Walkthrough areny, 2026-09-11] 99 kolejnych ćwiczeń dla siedmiu
  postaci: sytuacja, narracja Nessy, wymagana umiejętność i osobne podbicia.
  Zapewniona mana, świeże zasoby, kontrolowane okazje do reakcji, ponowienie
  nieudanego pchnięcia/ukrycia. Po ćwiczeniach zwykły pojedynek 1 na 1
  (30 PW, KP 13, +3, 1k6) oraz powrót przez ✓ do wyboru postaci.
  Figurka Nessy usunięta z nowego trybu; teren bez zmian. Postęp w zapisie.
  Usunąć stary warunek publiczności blokujący zdolności Loriana w profilu
  wspólnej many: skazę wycenia istniejący koszt, bez zakazu użycia solo.
- [ ] [Próba walkthrough na planszy] Przejść 99 ćwiczeń i 7 pojedynków;
  sprawdzić przestawianie figurek, narracje i rytm potwierdzeń. Dodać nagrania
  Nessy do gotowych tekstów i identyfikatorów narracji w osobnym zadaniu.

- [x] [Świecące ✓ bez reakcji, 2026-09-10] Sesja `exploration_ui_be3fc3a4ad`:
  pierwszy krok przygotowania areny i ręczne ponowienie kończyły się po 5 s
  błędem ACK WLED, zanim uruchomiono wejście USB. Usunąć zależność skanu
  od potwierdzenia LED; zachować maskę/kontekst ESP, anulowanie oraz osobne
  ponowienia i diagnostykę LED. Testy obejmują przejście kroków przygotowania
  przez ✓ mimo błędów WLED i anulowanie przy zablokowanym wysyłaniu LED.

- [x] [Samouczki areny, 2026-09-10; zastąpione walkthrough] Pierwszy tryb dla siedmiu postaci:
  67 ćwiczeń aktualnego katalogu (ze Świętym symbolem Dagny), dowolna kolejność,
  automatyczne zaliczanie rozstrzygniętych działań, objaśnienia z symbolami
  i niebieskim ✓. Figurki dostosowane do leczenia, reakcji, flanki, serii
  i obszarów; teren bez zmian. Zapis/wczytanie oraz kontynuacja przechowują
  postęp. Trzy wcześniejsze warianty pozostają swobodnym treningiem.
  Unik instynktowny w profilu wspólnej many nie wymaga już starego warunku
  ukrycia; jego rzeczywiste wywołanie przy ataku obejmuje test regresji.


- [x] [Kości i ponawianie skanu, 2026-09-10] Uderzenie tarczą z podbiciem
  pokazuje osobne k6, postęp, poprawkę i sumę; Siła jest doliczana raz.
  Anulowanie zwalnia także blokadę skanu w przeglądarce. Ponowienie ręczne
  i załadowanie strony kończą poprzedni skan; reset serwera czeka na wyjście
  czytnika poza blokadą gry. Testy Chrome i HTTP obejmują płatność za Pozycję
  obronną oraz następny wybór. W sesji `exploration_ui_84076df971` po płatności
  (seq 242–246) ruszył skan trzech dostępnych akcji; ponowienia były odrzucane
  jako duplikaty (247–254). Brak danych rozstrzygających, dlaczego pierwszy
  fizyczny wybór nie dotarł. Ponowna próba na planszy pozostaje do wykonania.

- [x] [Runy podbić i komunikaty, 2026-09-10] Zastąpić listę rozwijaną
  i −/+ podbić wariantami z runą, symbolami kosztu oraz wielkością efektu.
  W płatności serwer wyznacza aktywne runy, LED i ✓/↩; warianty różnych
  kolorów można łączyć, ponowny wybór odznacza, limity są walidowane.
  Uaktualnić instrukcje gry z Enter/Numpad na planszę, ekran i ✓/↩.
  Opis: `docs/MANA_BOOST_RUNES.md`; fizyczna próba podbić pozostaje do wykonania.

- [x] [WLED po migracji v2, 2026-09-10] Usunąć blokowanie UI podczas
  wysyłania LED; jeden pracownik, najnowsza pełna ramka i ponowienia błędów.
  Nie zapamiętywać odrzuconych ramek jako wysłanych. Po późniejszej poprawce
  świecącego ✓ wejście ESP nie czeka na ACK LED; anulowanie odcina stary skan.
  Regresja: Garran wybiera kukłę mieczem, sesja `exploration_ui_c4636e91fa`.
  Analiza: `docs/BOARD_WLED_LATENCY_2026-09-10.md`.
- [ ] [Fizyczne LED po poprawce] Sprawdzić ponownie potwierdzenie ataku
  Garrana i płynność UI. Sieć WLED nadal odpowiada z opóźnieniem; zmiana
  oddziela je od UI i ponawia aktualny obraz, nie przyspiesza samego Wi-Fi.

- [x] [Wgranie v2 bez v1, 2026-09-10] `board_scan_protocol_v2_2` na ESP32:
  cztery sumy zapisu potwierdzone; produkcyjny transport Python sprawdził
  HELLO, maskę panelu, 12 s heartbeat/skanowania bez błędów I²C i STOP.
  Raport: `docs/BOARD_FIRMWARE_DEPLOYMENT.md`. Próby przy stole poniżej.

- [x] [USB v2 bez zgodności v1, 2026-09-10] Przenieść aplikację na maski
  single/stream/finish, jeden czytnik USB, ACK/deduplikację, heartbeat i ścisły
  parser. Usunąć SCAN/STOP v1, stare ustawienia skanowania i ponawianie po
  TypeError. Firmware `board_scan_protocol_v2_2`; tekstowy PING tylko do info v2.
  Źródła: `board/serial_v2.py`, `board/connection.py`, adapter gry i panel UI,
  `future/board_20x30_usb_wled_test/`. Kontrakt: `docs/BOARD_SCAN_PROTOCOL_V2.md`.
- [x] [Ciągłe wejście kości] Stały kontekst i maska +/− tej samej kości,
  koniec na ✓/powrocie, kolejka transportu niezależna od HTTP i WLED.
  Sekcja krytyczna gry odcina spóźnione zdarzenia przy sterowaniu ekranem.
  Testy kontrolera C++, transportu Python, przepływu gry i panelu Chrome.
- [x] [Audyt i projekt protokołu, 2026-09-10] Wyłącznie aktywne pola, bez
  skanowania tła i błędnych naciśnięć. Audyt: `docs/BOARD_SCAN_PROTOCOL_REVIEW.md`;
  aktualny kontrakt i ograniczenia integracji: `docs/BOARD_SCAN_PROTOCOL_V2.md`.
- [ ] [Próba scenariusza i areny na v2] Sprawdzić start połączenia, LED/menu,
  szybkie osobne +/−, zatwierdzenie, następną kość, naciśnięcia nieaktywnych
  pól i równoczesną obsługę ekranu. Zmierzyć pełną reakcję do UI i LED.

- [x] [Licznik inicjatywy / analiza USB, 2026-09-10] Sesja
  `exploration_ui_37657b3f1c`: trzy fizyczne plusy, wynik 13; obsługa po
  odbiorze 0–1 ms, kolejne skany po 147–159 ms, bez wolnych ramek LED podczas
  zmian licznika. Przygotować grupowy odczyt ekspanderów w roboczym szkicu
  ESP32 (40 zamiast 600 odczytów), oznaczenie wersji w STATUS i test wszystkich
  pól oraz filtrowania styków. Źródło: `future/board_20x30_usb_wled_test/`.
- [ ] [Pomiar szybszego skanera ESP32] Po wgraniu `board_scan_protocol_v2_2`
  zmierzyć wykrywanie krótkich naciśnięć −/+ na fizycznej planszy.
  Skan aktywnego panelu sprawdzono bez dotykania; pozostała ocena wykrywania
  naciśnięć i całego przepływu do UI/LED.

- [x] [Połączenie przy wejściu do gry, 2026-09-10] Ekran `/play` sam łączy
  skonfigurowaną planszę lub symulator. Pokazuje „Łączę z planszą…” podczas
  próby, a ostrzeżenie i Ponów dopiero po błędzie; nie dubluje prób i respektuje
  jawny tryb awaryjny. Reset/zmiana scenariusza i nowa próba areny zachowują
  otwarty adapter i ustawienia, anulując stary skan. Ostatni log
  `exploration_ui_51cbf025ef` pokazywał pierwsze połączenie dopiero po ręcznym
  Ponów. Testy obejmują start i błąd w Chrome, oba backendy, reset obu map,
  wejście do próby areny, zachowanie ustawień i zamknięcie połączenia.

- [x] [Opóźnienia wejścia planszy, 2026-09-10] Naprawić wyścig timera skanu
  z zatwierdzaniem akcji i rejestracją kontrolek; ignorować stare odpowiedzi
  bez zwalniania blokady nowego odczytu. Po odebranym naciśnięciu wysyłać
  kolejny SCAN bez technicznego STOP i pauz 80/120 ms; zachować reset przy
  starcie, anulowaniu i błędach. Test Chrome z kontrolowanymi timerami oraz
  testy USB, panelu i inicjatywy. Analiza: `docs/BOARD_INPUT_LATENCY_2026-09-10.md`.
- [ ] [Pomiar fizycznego wejścia i LED] Po ponownej próbie zmierzyć czas od
  dotknięcia do sygnału USB oraz pełnego przebiegu czujników; sprawdzić wersję
  wgranego firmware przed jego optymalizacją. Osobno sprawdzić opóźnienia WLED
  (w sesji z 2026-09-10 do 954 ms), których testy symulowane nie odtwarzają.

- [x] [Panel akcji po inicjatywie, 2026-09-10] Przywrócić LED-y i wybór akcji
  nadrukowanymi polami areny, wyłączone podczas wdrożenia wspólnej many.
  Korzystać z tego samego mapowania i budżetu co menu ekranowe; zachować
  blokadę podczas płatności/rzutów, kolory i przełączanie podglądów.
  Regresja z sesji `exploration_ui_0920b468f2`: start tury Garrana po inicjatywie.
  Walidacja: 63 testy panelu, inicjatywy i wspólnej many przez `safe_pytest.sh`;
  adapter symulowany, ponowna próba fizycznej planszy pozostaje do wykonania.

## Wspólna mana 0.3 — wdrożenie 2026-09-09

- [x] Liczony rynek 5 kart / talia 25, transakcyjna płatność, podbicia, Odzysk własnego kosztu, odświeżenie i presja końca talii.
- [x] Podłączyć pełne 66 zdolności, święty symbol Dagny, nowe skazy, T/O i Hymn do runtime walki, reakcji i zapisu.
- [x] UI wyboru podbić i potwierdzania kart; róg −/+ /✓/↩ bez zmiany pozycji. Dolny pasek akcji aktywny zgodnie z bieżącym menu, nadruk run na mapach pozostaje.
- [x] Regeneracja kart bohaterów i zbiorczego PDF areny z kalibracją 250/244; testy reguł, UI, setupu i kompletnych rozstrzygnięć akcji.


Walidacja: 286 celowanych testów, dwa przebiegi Chrome z symulatorem planszy, widoki 390/1280 px, 28 zestawów HTML/PDF i zbiorczy PDF 53 stron. Szczegóły: [wdrożenie 0.3](docs/SHARED_MANA_V03_IMPLEMENTATION.md).

- [ ] Rozegrać nowy model 0.3 na fizycznej arenie: ocenić balans rynku/podbić i współpracę graczy, płynność LED oraz skalę wydruku na używanej drukarce.

- [x] [Po teście walki 2026-09-06] Doprecyzować ukrycie Miry i priorytet LED, naprawić stary ekwipunek, wydłużyć Szał z licznikiem rund, poprawić „Z bara”, symbole many, pojedyncze kości z akceptacją i wspólny wynik przeciwnika. Uaktualnić wydruki. Walidacja: 122 celowane testy, Chrome 390/1280/1440 px i 28 HTML/PDF; szczegóły w `docs/COMBAT_PLAYTEST_POLISH_2026-09-06.md`.

- [x] [Seria zwykłych ataków] Ograniczyć deklarację liczby ataków do Loriana. Pozostali bohaterowie przechodzą bez formularza do pojedynczego ataku; API i stare zapisy przestrzegają ograniczenia, techniki zachowują własną liczbę uderzeń. Uaktualnić Zryw, Lekkomyślny atak, opisy, karty i zbiorcze PDF-y. Walidacja: 61 celowanych testów i kontrola 28 PDF-ów.

- [x] [Garran / Nieustępliwość] Zastąpić Wyrzuty sumienia w profilu fizycznej many kosztem 2 dowolnych many za zwykły ruch rozpoczęty obok przeciwnika. Dodać podpowiedź przy ruchu i w panelu many, zachować cenę przy dzieleniu ruchu oraz zapisie gry; zaktualizować cztery wydania karty i kompletne PDF-y. Walidacja: 69 celowanych testów, 28 HTML/PDF bez przepełnień, podgląd statusu 390/1440 px.

- [x] [Przed testem z wydrukami] Zaktualizować generatory i komplet PDF-ów siedmiu postaci dla `physical_mana_v02`: kolorowe i minimalistyczne arkusze oraz karty do wycięcia, wszystkie 77 zdolności, skróty, koszty, pasywy, skazy i dobór. Aktualne pliki: `assets/physical_cards/character_sets/physical_mana_v02/`; dotychczasowe ścieżki PDF także zaktualizowane. Walidacja: 48 testów, kontrola 28 HTML/PDF. Dokumentacja: `docs/PHYSICAL_MANA_PRINTS_V02.md`.

- [x] Przebudować Głodne Cienie v6: rozstawienie, spójny teren i mapa do druku, role skrzydeł, setup terenu przed szykiem, instrukcje dla graczy i kotwice eksploracji. Dokumentacja: `docs/HUNGRY_SHADOWS_REDESIGN_V6.md`.

- [x] [Scena walki / zapis] Naprawić rozbieżność testu ponowienia Mapy 1: przy wczytaniu checkpointu `reconcile_boardgame_feature_removals` dodaje Brakce `flaw_chains`, mimo że aktor źródłowy scenariusza miał puste `features`. Test: `test_map1_defeat_enters_game_over_without_revealing_exploration`.

- [x] Dopracować odprawę Nessy: stałe tematy i bezpieczne przypomnienia, jedna lokalna próba Intuicji bez kary, spójny sekret/osobowość, Perswazja za ryzyko, poznane argumenty, karta umowy i osobne zakończenie odprawy.
- [ ] Rozegrać poprawioną odprawę i walkę v6 przy fizycznej planszy; sprawdzić czytelność nadruku/LED, użycie obu flank, tempo pierwszego kontaktu i balans many dla 1–5 graczy.

- [x] Replace the combat waiting screen's three example keys with a compact,
  character-specific index of every currently exposed keyboard action, showing
  only its shortcut and title while keeping full rules text on character cards.

## Setup

- [x] Remove the obsolete previous application from the active tree after the
  D&D 5e rebuild became self-contained; retain recoverability through Git history.
- [x] Keep low-level board communication in root `board/`.
- [x] Add rebuild documentation and Codex working rules.
- [x] Add package structure for the new D&D 5e application.
- [x] Add local rules decision document for implemented D&D mechanics.
- [x] Add project roadmap with implementation milestones.

## Current Roadmap Focus

Master kolejności znajduje się w `ROADMAP.md`. Aktualny stan rodzin zasad jest
prowadzony w `docs/DND_IMPLEMENTATION_MATRIX.md`. Ta sekcja powinna zawierać tylko
najbliższy horyzont, a nie kopię całej roadmapy.

- [x] [Physical mana] Add an explicit profile for new games with the seven heroes:
  physical-only card economy, full ability costs/help, independent attack series,
  Lorian support and larger reserve, revised combat effects, reported end-round
  waves and a printable instruction/ability catalog at `/rules/physical-mana`.
  Preserve generic 5e actors and legacy saves. Implementation evidence:
  `docs/PHYSICAL_MANA_IMPLEMENTATION_2026-09-05.md`.
- [ ] [Physical mana balance] Playtest the complete 0.2 economy with 1–5 heroes:
  attack-series duration, market contention, Lorian recovery, reaction reserves,
  repeatable healing/control and deck-cycle pressure. Tune numerical values
  against actual table results before preparing a final graphical card edition.

- [x] Replace the historical milestone roadmap with the mechanics-first master roadmap.
- [x] Add a living D&D implementation matrix separating stable MVP, partial, fixture, and missing systems.
- [x] Lock the first full release rules baseline to D&D 5e 2014.
- [x] Decide and document the SRD 5.1 CC BY 4.0/source-pack strategy for the target 2014 content catalog.
- [x] Define schema versions, stable content ids, sequential migration rules, and a repository content audit.
- [x] Start M6 with coin denominations, item value/weight, Strength-based carrying capacity, generic corpse/container loot bundles, and selective combat looting of whole bundles, item stacks, or currency.
- [x] Add typed ammunition stacks, per-attack consumption for player/AI/reactions, empty-ammo blocking, crossbow `loading`, UI counts, lootable bolts, and snapshot v4 migration.
- [x] Recover half of party-fired ammunition after victory as persistent battlefield loot, with UI collection and snapshot v5 migration.
- [x] Add partial combat-loot selection for item stacks, recovered ammunition, and individual coin denominations, with live mass/capacity preview and atomic transfer validation.
- [x] Add scenario-defined merchants with deterministic partial buy/sell transactions, buyback prices, wallet/carrying-capacity validation, web UI previews, and snapshot v6 persistence.
- [x] Add light, medium, and heavy body armor with 2014 AC formulas, Strength speed penalties, Stealth disadvantage, exploration don/doff time, merchant content, and snapshot v7 persistence.
- [x] Add generic item charges with action costs, depletion blocking, deterministic short/long-rest recovery, UI counts, a reference binding wand, and snapshot v8 persistence.
- [x] Add D&D 5e 2014 item attunement with a three-item limit, one change per actor during short rest, power gating, UI selection, encounter persistence, and snapshot v9.
- [x] Close M6 with composable passive magic-item effects for AC, saves, checks, attacks, and speed; add an attunement-gated reference amulet, UI disclosure, and snapshot v10.
- [x] Add the complete 37-weapon SRD 5.1 catalog under one typed schema, category proficiency, dynamic ability damage, finesse choices, thrown recovery, normal/long range, heavy, reach, loading, ammunition hand requirements, lance/net rules, UI disclosure, content audit, and snapshot v11.
- [x] Complete mundane equipment before M7 with all 12 body armors, 144 SRD adventuring-gear/focus/tool/pack definitions, typed containers, light/fuel, utility checks, durability, pack expansion, merchant/UI integration, content audit, and snapshot v12.
- [x] Start M7 with a versioned `SpellDefinition` schema, spell refs as the single source for existing fixture effects, prepared/known/spellbook access profiles, V/S/M and focus validation, costly/consumed materials, cast-at-level slot selection, casting-time action costs, UI metadata, and snapshot v13.
- [x] Add M7.2 data-driven damage/healing scaling per slot level, an explicit higher-slot UI flow, exploration ritual casting with access/component validation, +10 minute time cost, no slot consumption, a utility ritual fixture, and snapshot v14.
- [x] Add M7.3 shared minute-based lifecycle for exploration magic, automatic expiry through ritual/crafting/rest/armor time advances, refresh semantics, UI disclosure, expiration notices, and snapshot v15.
- [x] Add M7.4 target-count upcasting with explicit slot selection, bounded multi-target selection in UI/board flow, grouped concentration effects, and a three-target Bless fixture gaining one target per higher slot.
- [x] Add M7.5 defensive spell reactions with a post-hit/pre-damage interrupt, shared reaction and slot consumption, persistent AC effects, expiry at the caster's next turn start, and a data-driven Shield fixture.
- [x] Add M7.6 Counterspell with a pre-resolution enemy-spell interrupt, 60-foot line-of-sight eligibility, reaction and selected-slot consumption, automatic same/lower-level interruption, a manual spellcasting-ability check for stronger spells, and shared UI/board resumption.
- [x] Add M7.7 interruptible long casting with one action per turn, transient concentration, damage checks, missed-action/cancel/defeat interruption, deferred slot/component consumption, UI progress, a data-driven reference ward, and snapshot v16.
- [x] Add M7.8 data-driven concentration summons with board/LOS placement, dynamic allied actors, owner-adjacent initiative, independent attacks, automatic dismissal, UI/LED flow, and snapshot v17.
- [x] Add M7.9 data-driven spell movement with visible free-tile teleportation, save-based push/pull, obstacle-aware final positions, no movement-cost/opportunity triggers, UI/LED selection, and project-original fixtures.
- [x] Add M7.10 generic save-first spell debuffs with shared condition state, automatic enemy saves, repeated saves at authored timing, UI/LED target selection, and project-original Poisoned/Restrained fixtures.
- [x] Close M7.11 with generic creature-targeted spell dispelling, automatic same/lower-level removal, physical spellcasting-ability checks for stronger effects, shared ActiveEffect/ConditionState provenance, summon dismissal, UI/LED flow, and snapshot v18.
- [x] Add M7.12's first executable SRD spell-content tranche (Sacred Flame, Healing Word, Fire Bolt, Burning Hands, Cure Wounds, and Inflict Wounds), character-level cantrip scaling at 5/11/17, spell-attack proficiency, caster-ability healing, reference-scenario preparation, and snapshot v19.
- [x] Start M8 by auditing its already-complete foundations and migrating the terminal exploration harness to authoritative guarded flow routes.
- [x] Add M8.2 guarded NPC flow for `village_square_mvp`: explicit information/reward goals, state-gated negotiation, terminal refusal state, shared planner/UI payload, and regression coverage.
- [x] Add M8.3 guarded tavern-keeper flow for `village_square_mvp`: migrate the legacy rumor option to Olan's NPC interaction, apply the authored quest hook, hide the consumed rumor goal, and keep ordinary conversation available.
- [x] Add M8.4 village quest lifecycle and authored scenario continuation: separate hook/acceptance/readiness flags, gate departure by state and location, validate the watchtower target, expose objective progress in UI, and save a source-scene handoff snapshot.
- [x] Add M8.5 scenario time and delay consequences: data-driven clock thresholds, travel/conversation/rest costs, one-shot effects and narration, visible time of day, and timed watchtower handoff metadata.
- [x] Add M8.6 exploration visibility: typed ambient light and actor senses, darkvision/blindsight/truesight evaluation, sight-based observations, dim-light Perception disadvantage/passive -5, darkness blocking, party light ranges and burn time, precombat Stealth integration, UI disclosure, and snapshot v20.
- [x] Add M8.7 exploration awareness: active zone Search with time and light rules, passive trap detection, typed trap detection DC/range, persistent zone Hide totals, reveal-on-light/time/travel, encounter stealth handoff, UI controls, and snapshot v21.
- [x] Add M8.8 interactive exploration fixtures: typed doors, locks and containers; local unlock/open/close/loot flows; object AC, HP and damage thresholds; persistent state, combat movement/cover projection, UI controls, reference content, and snapshot v22.
- [x] Add M8.9 overland travel: fast/normal/slow pace, authored navigation checks and fail-forward delay, forced-march Constitution saves, six exhaustion levels shared by exploration/combat/resting, village-to-watchtower UI handoff, and snapshot v23.
- [x] Audit Brakka's combat identity: apply 60-foot darkvision to nonmagical combat darkness, keep Relentless Endurance as an automatic first-drop long-rest resource, replace the restraint flaw with Rage-time active-equipment blocking, enforce Frenzy's next-turn timing, and regenerate color/toner card sets.
- [x] Close M8.10 social interaction rules: persistent NPC state and attitude, deterministic 2014 reaction thresholds, authored retries/outcomes/transitions, visible stakes, and player-authoritative Persuasion/Deception/Intimidation selection.
- [x] Add M8.11 formal downtime crafting: location-bound data-driven recipes, tool ownership and proficiency, half-price materials, 5 gp workdays, permanent inventory results, shared-clock consequences, and player confirmation.
- [x] Add M8.12 shared condition boundaries: exploration hazards can author persistent Poisoned/Restrained states with source and duration; conditions enter combat, return to exploration, and expire consistently on encounter, rest, long-rest, and scenario events.
- [x] Close M8.13 with ordered continuation outcomes: success, partial success and fail-forward branches can depend on final flags/navigation, carry selected flags, emit validated target effects and summarize source objectives in the verified handoff.
- [x] Harden the M8 village playtest UI: expose authored zone options, show objective milestones, make NPC setup/location messages generic, avoid repeated dialogue intros, and replace continuation prompts/raw ids with an in-page Polish travel form and friendly scenario names.
- [x] Ground generative NPC narration against authored facts and effects: scope prompts to the active goal/permission and let critical routes enforce hidden content-authored narration so Gemini cannot invent quest evidence, rewards, purchases, or currency transfers.
- [x] Add controlled authored paraphrases for guarded NPC routes: Gemini selects an approved variant id matching the player's tone, while validation copies the complete variant and safely falls back to the base response.
- [x] [Spell fidelity] Add creature-type healing exclusions for undead/constructs and an explicit unattended-flammable-object rider for Fire Bolt.
- [x] Replace character-creator standard-array-only input with D&D 5e 2014 27-point buy, show base score/cost/origin bonus/final modifier separately, and add audited Polish tooltips for every level-1 class feature.
- [x] Rebuild class choices as a guided player step with skill use/proficiency explanations, fighting-style rule cards, automatic expanded starting packages, origin-skill conflict prevention, and a final live character-sheet review.
- [ ] [Deferred character creator] Add an optional starting-wealth mode with class-specific wealth generation, a restricted pre-game shop, affordability/carrying-capacity checks, and an explicit choice between wealth and the automatic class package.
- [ ] [Deferred subclass expansion] Add real multi-option subclass branches and
  corresponding level-up card pools only from a registered lawful source pack;
  do not source catalogue text or definitions directly from the Player's
  Handbook. If no additional licensed pack is established, author
  `project_original` subclasses with original names, descriptions and mechanics,
  then cover their grants with runtime resolvers, Polish help, audits and focused
  tests.
- [ ] [Deferred mounted combat] Let a mounted wielder use a lance in one hand; until an explicit mounted actor state exists, the lance correctly uses two hands and retains its close-range disadvantage.
- [ ] [Deferred destructible equipment] Model the net as an AC 10 object with 5 HP that can be cut using slashing damage; Strength DC 10 escape is implemented.
- [ ] [Deferred attunement fidelity] End attunement automatically after the official distance/time, death, prerequisite-loss, or another-creature-attunement conditions.
- [x] Add the versioned material-property catalog and schemas for item definitions, item instances, and scene fixtures.
- [x] Add a unified crafting-source registry for zone items, fixtures, exploration resources, and party inventory.
- [x] Add deterministic property-based crafting drafts, component validation, allocation, dismantling, and engine-owned costs.
- [x] Integrate property-based crafting with the GM classifier and chat confirmation, without a default build roll.
- [x] Close the exploration MVP with a chat-first GM, grounded scene answers, progressive hints, and persisted reveal context.
- [x] Give LLM narration a lively D&D table voice and resolve absurd-but-possible declarations as policy-limited world actions with immediate fictional consequences.
- [x] Drop no-op LLM situational modifiers so descriptive details such as loud actions do not reject otherwise valid declarations.
- [x] Add persistent NpcRuntimeState with attitude, physical/emotional state, revealed information, used attempts, relationship events, content-driven updates, UI, LLM context, and snapshot compatibility.
- [x] Add filterable slash-command intent hints to the exploration chat while preserving automatic intent detection.
- [x] Unify player questions and progressive hint requests under `/pytaj`; infer hint strength from message content.
- [x] Add deterministic graded observations that reveal cumulative scene facts without advancing the active challenge.
- [x] Add goal-scoped contextual searches: semantic no-roll material lookup, graded hidden discoveries, preselected observers, and flag-driven follow-up cards.
- [x] Separate free GM conversation from goal actions and route known scene-item uses through authored procedural source actions.
- [x] Add the first guarded exploration flow-graph vertical slice and migrate the watchtower gate's goal availability and routing.
- [x] Make authored flow options authoritative for check mechanics and accept a reduced LLM method-only contract on migrated routes.
- [x] Add one pre-declaration exploration source contract for resources, tools, items, weapons and spells; filter sources by capability tags, keep ownership/cost/modifier/consequence resolution deterministic, and add the watchtower rope setup-to-persistent-route reference flow.
- [ ] Migrate remaining exploration/NPC scenes to guarded flow graphs and reduce the LLM contract to route selection plus grounded method details.
  - [x] Revalidate the selected goal against its currently active graph transition, with participant choice made before the method description and roll.
  - [x] Extract goal, participant, observation and procedural-source planning from `ExplorationUiSession` into an application service and remove duplicated gate routing fields.
  - [x] Migrate the wounded scout to an NPC-owned flow with authored intent routing and pre-declaration participant selection.
  - [x] Migrate the legacy `demo_exploration_scene` freeform harness from tag-based goal inference to explicit flow routes, then update its watchtower regression cases.
  - [x] Migrate village elder Bren to an NPC-owned flow with quest-state and refusal-state gating.
- [x] Route authored observation intents before generic challenge classification and ground numeric DCs to content tiers.
- [x] Replace the gate's predefined approach/risk lists with structured guidance facts and update the interaction form.
- [x] Give `/szukaj` an exact-first and semantic-fallback flow with player-confirmed substitutes and persisted scene findings.
- [x] Give `/użyj` explicit source resolution, deterministic source binding, and a property/risk preview for scene-item use.
- [x] Normalize actor-inventory source ids selected by `/użyj` before exploration resource validation.
- [x] Add explicit take/collect policies for portable findings, quest items, and treasure without conflating search with inventory transfer.
- [x] Let detachable scene fixtures be acquired during confirmed crafting instead of requiring an unavailable technical detachment command.
- [x] Ground actor-inventory items in generated exploration checks and restrict the test leader to an actor who owns the item.
- [x] Route visible-source searches and immediate improvised use before observation/crafting, with player-facing validation messages.
- [x] Carry exact reconnaissance into a one-use initiative advantage for its observer in the matching encounter.
- [x] Keep the wounded scout hidden until the gate encounter is won instead of revealing it when the gate opens.
- [x] Add a scenario-driven encounter-opening stage with initiative disadvantage for the surprised side.
- [x] Bridge scenario-driven quiet encounter openings into optional per-character Stealth vs passive Perception before initiative.
- [x] Split critical gate openings into independent party-wide initiative advantage and precombat Hide opportunities for force, lock-and-bolt, and wall routes.
- [ ] [Deferred rules fidelity] Replace side-wide initiative disadvantage with the full per-creature D&D 5e 2014 surprised condition when a scenario needs exact rules fidelity.
- [x] Replace text-only exploration materials and predefined temporary-item templates with deterministic property-based crafting.
- [x] Persist component reservations and dynamically crafted temporary items in scenario snapshots.
- [x] Persist runtime fixture state changes once fixture detachment and destruction actions are implemented.
- [x] Migrate the watchtower gate as the reference fixture/crafting interaction after the generic runtime is ready.
- [x] Unify effect source, duration, expiration, stacking, and replacement contracts.
- [x] Add generic actor resources with short-rest and long-rest recovery policies.
- [x] Implement automatic pre-scenario long rest and content-driven short rest independently from classes.
- [x] Extend the duration/recovery model with scenario-end expiration and recovery policies.
- [x] Add a versioned actor/scenario snapshot and deterministic round-trip test.
- [x] Add actor life states at 0 HP, death saves, stabilization, massive damage, and recovery through healing.
- [x] Add unconscious attack consequences and combat stabilization with Medicine or a healer's kit.
- [x] Represent equipped weapons dropped at 0 HP as scene-positioned combat objects persisted in snapshots.
- [x] Add contextual combat field/self-action menus for overlapping field intents with arrow/Enter/Escape control.
- [x] Add compound approach-and-interact plans with path cost, range validation, and opportunity-attack interruption.
- [x] Route the watchtower cart and rubble through contextual combat interactions while keeping the fallen gate non-interactive.
- [x] Implement dropped-weapon pickup as the first inventory interaction using the contextual field menu.
- [x] Add explicit equip/swap/drop weapon actions to the self-action equipment menu.
- [x] Add geometric projectile cover and ranged-attack-in-melee disadvantage with visible combat previews.
- [x] Add D&D 5e 2014 Hide/Search with per-observer detection, passive Perception, movement/attack reveal, and enemy Search.
- [x] Replace Mira's interrogation flaw with session-scoped `Panika po zdemaskowaniu`: visible enemies gain `+2` to attack rolls until Mira ends stealth or every active enemy detects her.
- [x] Add a shared combat condition state and D&D 5e 2014 Prone rules for movement, attacks, AI, UI, and snapshots.
- [x] Complete the actor proficiency-profile vertical slice for skills, expertise, saves, weapons, armor, and tools.
- [x] Add tool proficiency checks and a generic opposed-check resolver as groundwork for Grapple and Shove.
- [x] Implement D&D 5e 2014 Shove with Athletics contest, prone/push modes, forced movement validation, and combat UI.
- [x] Implement D&D 5e 2014 Grapple with sourced condition state, escape action, zero target speed, dragging, snapshots, and combat UI.
- [x] Enable D&D 5e 2014 optional flanking by default for player and enemy melee attacks, with visible advantage context.
- [x] Add creature-size categories with Medium defaults, content/snapshot/UI support, and D&D 5e size eligibility for Grapple and Shove while keeping all actors one-tile.
- [x] Add a grouped contextual combat action catalog with every legal weapon source, maneuvers, spells, support actions, and content-defined targeted item actions.
- [x] Add explicit main/off-hand slots, one- and two-handed equipment plans, visible hand occupancy, and free-hand validation for Grapple.
- [x] Add D&D 5e 2014 two-weapon bonus-action rules with light melee weapon validation, a per-turn trigger, visible contextual UI, bonus-action consumption, and off-hand damage rules.
- [x] Add D&D 5e 2014 versatile-weapon attack variants that require a free second hand and expose the stronger damage die in combat UI.
- [x] Add shields as held equipment with don/doff action cost, proficiency validation, effective AC, hand conflicts, UI, content, and snapshots.
- [x] Add typed damage components with D&D 5e 2014 resistance, immunity, vulnerability, content/snapshot support, and visible damage breakdowns.
- [x] Add compatible `NdM` and multi-component attack damage content, including
  per-component manual player input, automatic enemy rolls, critical dice doubling,
  per-type affinity resolution, area spells, Ready attacks, and opportunity attacks.
- [x] Add a shared ordered reaction window and migrate Ready plus manual/automatic
  opportunity attacks to one pause, advancement, skip, and resume contract.
- [x] Unify saving-throw requests/results and add enemy effects that pause for a physical player d20 before applying save-adjusted typed damage.
- [x] Add data-driven exploration hazards triggered by failed checks, with a visible physical saving throw and save-adjusted typed damage.
- [x] Add save-dependent exploration hazard effects, persistent actor conditions, snapshot support, and an exploration-to-combat condition bridge.
- [x] Add the M5 condition-engine vertical slice with Poisoned, Restrained, condition immunities, timed expiry, repeated turn-boundary saves, UI, content, and snapshots.
- [x] Add data-driven actor auras with dynamic position coverage, non-stacking save modifiers, defeated-source shutdown, UI visibility, and snapshot support.
- [x] Add the first data-driven trigger-engine vertical slice with shared event ids, deterministic turn-boundary activation, `grant_temp_hp`, UI logs, content validation, and snapshots.
- [x] Connect the shared trigger engine to attack-hit, damage-taken, movement, rest, and encounter-end emitters, including reactions, forced movement, and exploration hazards.
- [x] Add resource-backed limited attacks with short/long-rest recovery, deterministic monster Recharge rolls at turn start, UI availability/logs, content validation, and snapshots.
- [x] Close M5 with versioned FeatureDefinition/FeatureGrant composition for resources, actions, triggers, and auras, including provenance, collision validation, UI, snapshots, and two content fixtures.
- [x] Add data-driven exploration traps with detection, disarm/bypass/trigger actions, hazard activation, snapshots, and an alarm-wire reference fixture.
- [x] Close the combat turn-economy MVP with explicit action costs, data-driven Use an Object, separate draw/stow interactions, and visible UI costs.
- [x] Define the board-first player UI direction, target exploration/combat/NPC views, information hierarchy, and edge cases in `docs/PLAYER_UI_DESIGN.md`.
- [x] UI-1: Add the shared player shell and visual tokens; move hardware configuration and debug surfaces out of the normal player flow.
- [x] UI-2: Rework exploration and NPC presentation around one stateful full-screen chat without duplicated trial/result cards.
- [x] Make tall interaction composers scrollable and give every watchtower gate goal a responsive illustrated tile.
- [x] UI-3: Rework encounter setup and combat around a compact turn HUD, board-context menus, and one preview/roll/result flow without a digital map.
- [x] UI-4: Add on-demand character/state/spell/inventory drawers, information-overload priorities, keyboard navigation, and disconnected-board fallback.
- [x] Add the smooth-play runtime contract: revision-safe automatic board listening,
  one active chat step, automatic deterministic advances, non-blocking Gemini
  feedback, redundant-frame suppression, and contextual projectile animation.
- [x] [Hardware scan reliability] Apply idle recovery inside bounded hardware scans,
  reset the listener after a final timeout, and persist the timeout reason in session
  observations instead of leaving an unmatched scan-start event.
- [x] [Hardware scan reliability] Preserve the firmware STOP acknowledgement during a
  soft reset so a cancelled scan releases its lock before the next combat turn, and
  normalize keyboard-wedge `?` underscores in the browser before card validation.
- [x] [Hardware scan reliability] Ignore delayed acknowledgements of the defensive
  pre-scan STOP while still honoring explicit scan cancellation, so a newly armed
  hardware scan cannot terminate before the player presses a field.
- [x] [Hardware scan reliability] Release a cancelled serial scan locally without
  requiring a firmware STOP acknowledgement, and wait for that request to finish
  before the browser arms the next board revision.
- [x] [Combat action preview responsiveness] Debounce Numpad action changes,
  update the highlighted row optimistically, refresh LED previews without waiting
  for the obsolete scan, tint action sections, and keep the 5×4 hero start zone whole.
- [x] [Combat action list stability] Update only the selected action row during
  Numpad preview changes and keep scrolling inside the list, avoiding full-screen
  rerenders and page-level scroll flashes.
- [x] [Enemy attack result acknowledgement] Keep hit, damage, HP and effect results
  visible after board confirmation until the players explicitly acknowledge them.
- [x] [Combat preview scan handoff] Keep Numpad preview changes optimistic, but wait
  for the obsolete hardware scan to release its lock before arming the selected
  movement or ranged-attack revision.
- [x] [Board shutdown safety] Send the all-LEDs-off command and close the board
  transport when the exploration runtime exits, including terminal Ctrl+C.
- [x] [Area preview and scan lifecycle] Limit Spike Growth center placement to
  50 feet, retain dim legal centers under the stronger selected spell area,
  allow repeated repositioning before Enter, and centrally re-arm cancelled scans.
- [x] [Combat action section order] Keep movement first, followed by weapon
  attacks, hero abilities, spells, equipment, maneuvers and basic actions.
- [x] [Black Ford aftermath] Keep the battlemap active after the Hungry Shadows,
  reveal the wagon, tracks, Teren, young beast and route choice, gate departure
  on their fail-forward outcomes, and provide a working Map 2 entry handoff.
- [x] [Simple scenario continuation] Replace pace, navigator and travel-roll
  selection with one fixed-duration handoff confirmation.
- [x] Replace the fixed 2×4 hotspot grid with the visible continuation composer as soon
  as its board tile is selected, instead of hiding the composer below a clipped grid
  while board listening is intentionally paused.
- [x] Show player-visible mechanical rules for every highlighted environment group
  during encounter setup, including difficult terrain, cover, blockers and interactions.
- [x] Make universal ACCEPT trigger the sole visible forward action and replace
  spell hand-juggling restrictions with explicit hands-bound, gagged and Silence states.
- [x] Add passive board focus for physically placed initiative/Stealth actors and exploration objects, without treating exploration party members or NPCs as separate board pieces.
- [x] Move prepared-spell selection to the final initial-setup step before first-location selection.
- [ ] UI-5: Validate the complete board-first UI vertical slice with `abandoned_watchtower` and the manual hardware checklist.
- [ ] [Post-scenario control experiment] After completing the first target
  scenario, playtest an optional LED-only board mode without figurine detection:
  keep LEDs as spatial output, use the numpad/UI for declared positions and
  confirmations, provide fast position correction, and compare reliability,
  pace and player experience against the scanner-driven mode before deciding
  whether detection remains required or becomes an optional enhancement.
- [ ] P1: After the first target scenario, add the physical player-interface vertical
  slice: a player-maintained A4/A5 character sheet updated through level-up, printable
  illustrated decision cards with stable QR ids, a scanner input adapter, shared
  action-catalog validation, and board-based spatial targeting. Hero identity has no
  screen or board fallback; recovery may retry, reconnect, cancel, or return to menu.
  - [x] Add the versioned decision-card QR payload and deterministic PNG/SVG generator
    with printable quiet zones, metadata sidecars, and focused unit tests.
  - [x] Add the first duplex A4 control-card batch (`ACCEPT`/`DECLINE`) with real
    QR payloads, poker-size trim, bleed, crop marks, mirrored backs, and a manifest.
  - [x] Replace the flat control-card art with image-generated heroic dark-fantasy
    front and back backgrounds while keeping text and QR layers deterministic.
  - [x] Add the browser keyboard-wedge scanner adapter and route universal control
    cards through the existing context-sensitive primary/secondary UI actions.
  - [x] Make `ACCEPT` start a ready session and confirm instruction-only setup
    steps before considering an optional board-scan button.
  - [x] Normalize the keyboard-wedge scanner's observed `>` separator output to
    canonical `:` payloads in the shared card input adapter.
  - [x] Remove redundant physical NPC-placement setup from village instances so
    selecting a city location opens its interaction tiles directly.
  - [x] Anchor duplicate physical-card suppression to response completion so one
    slow ACCEPT request cannot spill into and confirm the following UI stage.
  - [x] Replace the player-facing character creator entry with twelve level-1
    archetypes while preserving the dormant creator and player-chosen legal level-up
    choices through level 3.
  - [x] Add player-facing histories, motivations, personal goals, turn guidance,
    resources, strengths, and pitfalls for every starter archetype.
  - [x] Refresh all twelve starter portraits as a versioned, comic dark-fantasy set.
  - [x] Add stable `dndbg:v1:actor:<actor_id>` hero-card payloads and use scans as
    the exclusive party-selection and exploration check-participant input.
  - [x] Generate the twelve-card duplex poker-size A4 hero set with real QR codes,
    bleed, crop marks, mirrored backs, previews, and a machine-readable manifest.
  - [x] Generate the first complete character-specific card sets for Garran and
    Dagna through level 3, with unique themed art treatments, stable QR payloads,
    concise mechanics, level requirements, duplex backs, and narrative dossiers.
  - [x] Extend the class-themed card sets to all twelve starter heroes and add a
    printable level-1 statistics, saves, proficiencies, spell, and equipment page
    to every character PDF.
  - [x] Audit all level 0–2 class spells: keep combat damage/status effects
    executable and record narrative-fidelity follow-ups without disabling combat magic.
  - [ ] Extend hero-card participant declarations to any remaining combat/support
    prompts that still introduce a separate choice of acting hero.
- [x] Fix the pre-combat Stealth transition renderer after encounter setup confirmation.
- [x] Remove physical-card gating from the New Game launcher and restore on-screen party and scenario confirmation.
- [x] Keep exploration numpad actions on stable board-backed numbers and restore readable, uncropped action tiles in the NPC workspace.
- [x] Reserve Numpad 0 as the visible, stable shortcut for leaving an NPC conversation.
- [x] Clarify rubble interaction targets, prioritize movement paths over object LEDs, and require visible acknowledgement of automatic enemy opportunity-attack results.
- [x] Keep combat result acknowledgements inside the combat panel, name ranged-melee threats, clarify compound movement destinations, and surface defeated-enemy results.
- [x] Keep the idle combat panel board-first by moving hero spells, common actions, equipment, and turn ending behind the active hero's board tile menu.
- [x] Render acknowledged combat results once instead of duplicating the same message across prompt, inline summary, and acknowledgement card.
- [x] Scope automatic spell-result acknowledgements to messages created by the current combat request so a previous caster's result cannot reappear during another actor's attack.
- [x] Keep exploration LEDs aligned with actual input mode: passive focus during an open interaction and selectable locations/points only after leaving it.
- [x] Add a courtyard-entry NPC placement setup, persisted selected point positions, location action cards, and passive LED focus for the physically placed wounded scout.
- [x] Add a direct courtyard-entry debug preset (including the legacy `courtyard_search` shortcut), full arrival narration, mandatory wounded-scout miniature placement, and illustrated scout/search action tiles.
- [x] Make wounded-scout intimidation a deterministic Charisma (Intimidation) check with authored outcome branches, without contradictory social-table refusal or a premature NPC response.
- [x] Add strict combat targeting after selecting an attack or spell source so movement tiles cannot steal target/area clicks, with explicit single-target and area labels.
- [x] Replace clear-then-render combat LED updates with atomic fading frames, preserve attacker/target focus during rolls, and keep the acting enemy visible through movement previews.
- [x] Clarify exploration checks by naming the tested skill and separating the rolling leader from a non-rolling helper.
- [x] Give exploration goal cards `must`/`allow` policies for D&D single, optional Help, and whole-party checks, selected before the free-form method.
- [x] Fix watchtower gate board-tile synchronization, restore a persisted hardware selection in the chat UI, log the activated target, and remove the duplicate gate-search card.
- [x] [Combat playtest] Block ending a turn with an unresolved action, expose executable spells and active class features in the board context menu, explain prepared spells from their real resolver contracts, and animate ranged projectiles across LEDs.
- [x] [Progression playtest] Award every player hero 300 XP after the gate-goblin victory, persist custom-character progress, and expose direct level-up actions in the encounter result.
- [x] Add a selectable mechanics playground with configurable training dummies, normal board-first combat setup, spell/area targets, exploration fixtures, a social-test NPC, repeatable short rests, and a one-click trial reset.
- [x] Remove the playground hotspot/location overlap and align its card tests with
  canonical level-3 archetypes, including replacement of inherited spell
  definitions by their resource-powered physical-deck variants.
- [x] Open the guild map directly into widely spaced interaction hotspots after
  paper-map acceptance, remove Nessa miniature setup, and confirm hotspot previews
  with a second click on the same board field.
- [x] Keep map hotspots widely separated while placing an entered point's action
  tiles and exit locally around that point's physical board field.
- [x] Keep automatic board listening armed during hotspot previews and enrich
  character feature lists with player-facing rules text plus runtime mechanics.
- [x] Fit the desktop New Game party/scenario selection flow into one responsive
  viewport while preserving normal document scrolling on narrow screens.
- [x] Split desktop hotspot previews and active conversations into a responsive
  two-pane workspace with a fixed 4-by-2 board-tile grid, independent dialogue
  scrolling, compact portrait/HP party HUD, and content-aware image cropping.
- [x] Execute description-free interaction goals immediately once their required
  participant/source choices are resolved, without a redundant confirmation card.
- [x] Use the compact portrait-and-HP party HUD throughout desktop exploration,
  hiding the campaign title and fitting the full party without horizontal scrolling.
- [x] Normalize the fixed keyboard-wedge scanner's `?` output back to `_` for
  every D&D board-game QR signature, including owned action cards.
- [x] Skip redundant participant selection for actor-assigned interaction tests
  and stage social checks as actor, approach, authored description, then test preview.
- [x] Keep authored setup LEDs passive on instruction-only encounter/map steps,
  preventing false board-scan errors while retaining scans for actual placement choices.

## Completed Work And Deferred Backlog

Ta sekcja zachowuje historię dotychczasowych prac. Nie określa kolejności wykonania;
obowiązują `Current Roadmap Focus` oraz etapy z `ROADMAP.md`.

- [x] Add `.gitignore` entries for local manual test runs and session observations.
- [x] Implement session observation writer for local JSONL metadata.
- [x] Define first debug runtime command shape.
- [ ] Keep `docs/RULES_DECISIONS.md` updated when implementing each D&D mechanic.
- [x] Define `Coordinate`, board dimensions, and grid primitives.
- [x] Implement pure neighbor lookup and bounds checks.
- [x] Implement pathfinding with terrain/passability callbacks.
- [x] Add unit tests for grid and pathfinding.
- [x] Define D&D 5e dice primitives: d20 roll, advantage, disadvantage.
- [x] Define basic actor state: AC, HP, speed, ability scores, position.
- [x] Implement initiative order.
- [x] Implement basic melee/ranged attack resolution.
- [x] Implement first mini-combat turn loop.
- [x] Implement board-first turn intent flow with split movement.
- [x] Add enemy auto movement before melee attack.
- [x] Implement first playable scene with setup, objective, and interaction.
- [x] Implement exploration interactions with ability checks and scene flags.
- [x] Integrate rolled initiative into the playable scene runtime.
- [x] Add multi-option tile preview for overlapping attack and interaction choices.
- [x] Add first scene-object flags for movement, interaction while occupied, and cover.
- [x] Implement exploration mode MVP with zones and shared party position.
- [x] Add abandoned watchtower exploration scenario.
- [x] Replace binary exploration gates with progress-based `ExplorationChallenge` model.
- [x] Add fail-forward outcomes and complications for exploration challenge options.
- [x] Add MVP item/resource tags for exploration option bonuses.
- [x] Replace exploration option cycling with board menu option slots.
- [x] Show only exploration anchors by default and move full-zone LEDs to look-around mode.
- [x] Add first village exploration mini-scene with setup NPC/object points.
- [x] Allow simple exploration message options to set scene flags and complete objectives.
- [x] Add optional Groq LLM GM classifier MVP for free-form exploration declarations.
- [x] Add optional Gemini LLM provider for free-form exploration declarations.
- [x] Add LLM context layers and retry flow for rejected free-form declarations.
- [x] Add LLM declaration analyzer, prompt registry, interpretation acceptance, and challenge attempt history.
- [x] Move LLM classifier MVP policy lists into exploration challenge content.
- [x] Add local declaration thread for freeform corrections inside active exploration challenges.
- [x] Add resource/fact grounding and structured freeform action flow for challenge attempts and preparations.
- [x] Add LLM interpretation explain/reject/reclassify controls before freeform challenge resolution.
- [x] Add content-driven DC policy tiers for freeform challenge proposals.
- [x] Move general LLM vocabularies and freeform grounding terms into `content/llm`.
- [x] Remove obsolete single-step legacy GM classifier prompt.
- [x] Add folder-based scenario manifests and split `abandoned_watchtower` into smaller JSON parts.
- [x] Add interaction/object-level LLM policy when freeform interactions expand beyond challenges.
- [x] Add global LLM intent catalog in `content/llm/intent_catalog.json`.
- [x] Add global LLM effect and condition catalogs for deterministic content-driven outcomes.
- [x] Replace NPC `allowed_actions` with local `intent_permissions` based on the global intent catalog.
- [x] Add hybrid exploration goal cards, authored method tradeoffs, and first NPC key issue vertical slice for the watchtower gate and wounded scout.
- [x] Add inherited instance/goal narrative profiles with heroic D&D defaults and serious-scene overrides.
- [x] Replace the watchtower gate progress track with lock/bolt state flags, repeatable outcome branches, capped goblin alert, and a concrete weaken-structure goal.
- [x] Remove stale progress validation, LLM context, and decision UI from flag-completed gate interactions.
- [x] Keep End Turn beside combat board scanning and require acknowledgement of automatic enemy saves against player spells.
- [ ] Add grounded value/currency requirements and a guard-bribe hard-boundary fixture for NPC key-issue validation.
- [ ] Add semantic LLM key-issue classification beyond authored phrase matching, with deterministic engine validation.
- [x] Route exploration web UI NPC flags and challenge reveals through the effect executor.
- [x] Add content-driven NPC effect fields with legacy flag-change fallback.
- [x] Add per-session web UI JSONL debug logs for actions, LLM proposals, rolls, and effects.
- [x] Add web UI session log panel backed by `/api/session-log`.
- [x] Make exploration presentation fiction-first with freeform questions, optional player inspiration, and separate GM mechanics.
- [x] Integrate the exploration effect executor with NPC runtime and load-time validation for intent parameters, limits, outcome branches, and scene transitions.
- [x] Extend preparation effects with advantage/disadvantage, effect boost, unlock option, and grant resource.
- [x] Show consequence preview before accepted freeform challenge rolls.
- [x] Add second exploration challenge in abandoned watchtower and reveal first hidden NPC hook.
- [x] Add first NPC interaction MVP after exploration point reveal.
- [x] Add persistent visible NPC attitude and deterministic 2014 social reaction thresholds for content-marked intents.
- [x] Add content-driven NPC attempt limits, retry unlock flags, natural blocking, and persisted roll history.
- [x] Add structured NPC intent targets with limits, deterministic checks, four outcome branches, preview, and effect execution.
- [x] Add persisted content-driven NPC escalation stages with state-aware variants and explicit player reactions before dialogue closure or encounter start.
- [x] Add exploration check plans for actor selection, result aggregation, and consequence targets.
- [x] Add simple local web UI for exploration and LLM playtesting.
- [x] Add content-driven exploration encounter triggers and pending encounter UI.
- [x] Add guided pre-combat encounter setup steps to the exploration web UI.
- [x] Start rolled initiative and initial combat state from the exploration web UI.
- [x] Apply combat outcome effects back into exploration after an encounter.
- [x] Add MVP combat actions to the exploration web UI.
- [x] Add player combat movement to the exploration web UI.
- [x] Add Bresenham line-of-sight and MVP ranged attacks.
- [x] Add a small gate skirmish encounter for immediate ranged testing.
- [x] Improve combat UI current-step clarity.
- [x] Close D&D combat core MVP for HP, damage, defeat, and attack results.
- [x] Add explicit combat turn economy placeholders for action, bonus action, reaction, and split movement.
- [x] Add deterministic combat interactions for the broken cart with LED support.
- [x] Add data-driven combat scene interaction conditions and effects.
- [x] Add rubble combat interaction with next-attack penalty and LED support.
- [x] Add enemy Dexterity saving throw for rubble combat interaction.
- [x] Show active combat effects with clear value and expiration in the combat UI.
- [x] Add combat actor status chips for action economy and active effects.
- [x] Add Dash and Dodge player combat actions to the exploration UI.
- [x] Add Disengage player combat action as a turn-end status effect.
- [x] Add opportunity attack reaction tracking and player movement confirmation.
- [x] Add hero opportunity attack choice during enemy movement preview.
- [x] Add explicit melee reach to attack sources, legal targeting, opportunity threats, enemy positioning, UI, and reference content.
- [x] Apply half and three-quarters cover to Dexterity saves for single-target and area spells, using each effect's point of origin.
- [x] Complete area-spell MVP geometry with line width, expanding cones, line of effect, data-driven target modes, and visible friendly fire.
- [x] Add Attack action budgets, Extra Attack-ready actors, attack-replacing Shove/Grapple, split movement between attacks, and data-driven monster Multiattack.
- [x] Add combat Help action with ally advantage against a chosen target.
- [x] Add combat Ready action for prepared attacks triggered during enemy turns.
- [x] Add generic encounter conclusions for victory, defeat, objective completion, party retreat, and surrender with scenario-driven outcomes.
- [x] Add full advantage/disadvantage d20 input and resolution for combat attacks.
- [x] Add combat action sources, cleric healing, and strength potion MVP.
- [x] Add MVP spell slots and area spell targeting for combat.
- [x] Add MVP spell save DC and automatic enemy saving throws.
- [x] Show cantrip vs spell-slot sources in the gate skirmish UI.
- [x] Add MVP concentration spell with a real attack-bonus effect.
- [x] Add concentration saving throws after damage.
- [x] Add actor inventory MVP with item-backed combat actions and consumable quantity.
- [x] Add inventory and spell requirements for exploration challenge options.
- [x] Add action mechanics class hierarchy and extension guide.
- [x] Extract first combat action resolution services from exploration UI.
- [x] Extract Flask routes, frontend assets, pending UI state, session view contract, and board session adapter from exploration UI.
- [x] Extract deterministic exploration start, setup, location, travel, point-selection, and encounter-trigger flow service.
- [x] Extract player combat movement planning, direct movement application, and opportunity-threat detection service.
- [x] Extract player opportunity-attack reaction resolution from the UI session.
- [x] Extract hero opportunity/Ready attack resolution and Ready trigger detection from the UI session.
- [x] Extract Dash, Dodge, Disengage, Help, and Ready preparation flow from the UI session.
- [x] Extract enemy-turn intent planning and result classification from the UI session.
- [x] Extract enemy-result commit and combat-turn finalization from the UI session.
- [x] Extract player attack/healing source selection and single-target player attack flow.
- [x] Extract player healing resolution and area-spell targeting/damage flow.
- [x] Extract strength-potion resources and concentration lifecycle/check resolution.
- [x] Extract combat scene interactions and position-bound effect expiration.
- [x] Extract combat flow services from `ExplorationUiSession` in small contract-preserving slices.
- [x] Complete pending-state typing and remove dead compatibility helpers after combat-flow extraction.
- [x] Fix real enemy-movement Ready detection when `EnemyAutoTurnResult.enemy` already has the destination position.
- [x] Add exploration map environment setup before location selection.
- [x] Consolidate the MVP into two printable black-and-white 20×30 overview maps (village and watchtower), tiled A4 and full-size PDFs; require physical-map confirmation only when the active paper map changes.
- [x] Add authored interaction-pad pools, dynamic numbered/color-coded UI-to-LED bindings, and board-driven point/goal/zone-option selection.
- [x] [Board interaction UX] Keep the entire interaction in one chat stream: one set of actionable tiles with board badges, a compact scan control, then an explicit per-action actor choice, player description, resolution, and result.
- [x] [Board actor identity UX] Assign stable red/blue/green/purple/orange colors by new-game party order and route exploration test-performer selection through matching illuminated board pads, with screen-card fallback.
- [x] [Party decision UX] Distinguish actor-owned actions and group checks from
  `no_actor` party decisions; let automatic information requests, accepting Bren's
  quest, and confirming departure resolve without an artificial hero-selection step.
- [x] [Interaction resolution UX] Add data-driven automatic, deterministic-check, LLM-rubric, and conversation modes with none/optional/required descriptions; migrate every village/watchtower MVP interaction and bypass LLM for fully scripted challenge checks.
- [x] [Board color fidelity] Stop reordering logical RGB values before sending them to the configured WLED API, so physical LEDs, Polish color labels, and UI borders use the same palette.
- [x] [Village playtest regression] Synchronize physical board-pad selections with the chat exactly once per click, clear stale NPC presentation after board-driven transitions, keep navigation inside the chat, and disclose the authored watchtower departure gate.
- [x] Couple exploration web UI with board/simulator backend for LEDs and board clicks.
- [x] Boost LED brightness only while an active board scan is waiting for a physical click.
- [x] Add data-driven actor portraits to party, test selection, rolls, combat order, and actor-linked messages.
- [x] Add inventory/cantrip option bonuses with actor item consumption and breakage checks to exploration rolls.
- [x] Add named exploration mechanic tools for LLM-selected challenge mechanics.
- [x] Add GM correction UI for selected exploration mechanic before rolls.
- [x] Add grounded situational modifiers and advantage/disadvantage to exploration rolls.
- [x] Add improvised tool mechanic validation and explicit GM approval flow.
- [x] Add scene-scoped temporary items built from grounded materials, with visible uses, snapshot support, and scenario-end expiration.
- [x] Ground omitted temporary-item template IDs from an unambiguous challenge policy and hide technical validator fields from players.
- [x] Persist interaction-scoped exploration conversations and restore their LLM context from snapshots.
- [x] Present exploration interactions as full-screen chat instances with scene intro, typing indicator, and an explicit return to the location menu.
- [x] Add visible scene-resource effects, correction, and consumption to exploration rolls.
- [x] Replace hardcoded functional item aliases with LLM property queries and deterministic scene-source matching.
- [x] Add generic pre-scenario prepared-spell selection and runtime enforcement MVP.
- [x] [K3-K4] Add class-derived spell lists, known/spellbook/prepared profiles, and full Constitution-save modifiers for concentration.
- [ ] [Deferred product UX] Add voice input and richer UI for free-form exploration declarations.
- [x] [Content production gate S0] Add a non-overwriting component-scenario scaffold, extended asset/paper-map/interaction-pad preflight, generic print-map manifests, and a real exploration-scenario selector in New Game.
- [x] [Content production gate S0] Document the current interaction resolvers and the scaffold → author → map → audit workflow.
- [ ] [Content production gate S0] Complete the final UI-5 checklist on the physical LED board before authoring the target scenario.
- [x] [MVP playtest P0] Clear `active_point_id` when the player leaves an NPC chat so zone actions are available again.
- [x] [MVP playtest P0] Consume scenario handoff by launching the target scene and mapping party, time, inventory, resources, flags, and target effects.
- [x] [MVP playtest P0] Route an explicitly declared available spell through deterministic spell execution instead of replacing it with an LLM-selected skill check.
- [x] [MVP playtest P1] Keep critical-hit player messages consistent with doubled damage dice.
- [x] [MVP playtest P1] Preserve defeated-actor loot, currency, dropped weapons, and recoverable ammunition when combat resolves back into exploration.
- [x] [MVP playtest P1] Give the watchtower hidden cache a collectible content-backed reward.
- [x] [MVP playtest P1] Fix caught-trap status, attack-preview ammunition count, and missing village party labels/portraits.
- [x] [MVP playtest P2] Stop serializing a complete path for every reachable combat tile; send only destination/cost and expose the full path for the selected preview.
- [ ] [MVP playtest P2] Replace repeated full actor/item definitions with stable refs and paginate long UI/session histories.
- [x] [MVP playful Gemini retest P0] Merge scenario handoff actors by preserving mutable campaign state while retaining target/canonical proficiencies, tools, spells, and other static capabilities.
- [x] [MVP playful Gemini retest P0] Prevent semantic leakage of locked NPC information from generated narration, not only unauthorized `revealed_information_ids`.
- [x] [MVP playful Gemini retest P1] Replace raw LLM validation errors with a player-facing retry and do not retain rejected declarations as accepted conversation history.
- [x] [MVP playful Gemini retest P1] Restrict generated numeric situational modifiers to authored/approved modifiers instead of allowing Gemini to change roll totals.
- [x] [MVP playful Gemini retest P1] Keep outcome narration behind player acceptance and add a visible loading/retry state for 20–30 second provider latency.
- [x] [MVP reference playtest P1] Resolve zero-risk cosmetic NPC exchanges immediately without a redundant acceptance step.
- [x] [MVP reference playtest UX] Return player guidance instead of a technical error when no interaction is active, without retaining the rejected declaration in chat.
- [x] [MVP reference playtest UX] Show objectives, secured loot, and an accessible restart action on the scenario-complete screen.
- [x] [Custom-party Gemini playtest P0] Make encounter player-start setup support the actual selected party size 1–5 instead of exhausting authored template positions.
- [x] [Exploration source binding P0] Require selected action source, participant/owner, grounded `used_resource_ids`, availability, and resolved cost to describe the same deterministic resource.
- [x] [Exploration pending UX P1] Disable or redirect the action composer while an observation, trap, or hazard must be resolved so the next declaration cannot be swallowed.
- [x] [Gemini declaration robustness P1] Normalize or repair `situational_modifiers` schema retries so valid longer weapon/item descriptions do not fail on missing generated metadata.
- [x] [Combat onboarding P1] Explain why the active attack source has no legal targets and suggest movement, line-of-sight, or weapon changes.
- [x] [Exploration provider resilience P1] Add jittered retry delays and automatic stable checkpoints after completed exploration resolutions.
- [x] [Exploration fixture fidelity P2] Document challenge checks as the intentional abstraction for attacking fixtures inside authored exploration goals.
- [x] [Character creator onboarding P2] Split the long character form into a five-step guided flow while preserving server-side validation.
- [x] [Character creator UX] Keep save ids internal and generated from unique character-name slugs; replace the public portrait path with a validated local image picker and roster-owned uploads.
- [x] [Character creator origin UX] Split species, species benefits, background, and background benefits into explicit stages; expose narrative and mechanical descriptions, live final ability values, and all 13 core 2014 background archetypes.
- [x] [Character creator feature help] Add mouse, keyboard, and touch-accessible explanations for every species, ancestry-variant, and background feature; distinguish automatic, creator, action, contextual, and table-assisted execution and enforce complete help/runtime coverage with an audit.
- [x] [Polish player terminology] Replace creator-facing technical ids and English spell/tool/skill names with one audited Polish label catalogue; localize all 138 loaded spell definitions and explain gaming-set, instrument, and artisan-tool proficiency choices.
- [ ] [Background content coverage] Add authored opportunities for appropriate background permissions across future scenarios; the generic ownership-plus-scene resolver is complete, but the current reference content does not exercise every one of the 13 backgrounds.
- [ ] [Deferred character art] Generate and integrate consistent class/species reference illustrations after the creator mechanics and content are final.
- [x] [Starter roster] Add, validate, and install one playable level-1 default build for every core class, with persistent portraits and Polish explanatory character cards.
- [x] [Village tavern] Replace the dice-game placeholder with a replayable physical-d20 gaming-set check, a real wager/payout, elapsed time, and wallet persistence.
- [x] [Village tavern] Add the nested Olan beer conversation: ordering unlocks a tasting prompt, Gemini interprets the player's description, the D&D social resolution handles uncertainty, and the outcome persists in Olan's attitude.
- [x] Clarify that the old watchtower interaction forms are historical briefs and update the current web-runtime instructions.
- [x] [Character creator MVP K1] Add a separate deterministic single-class level-1 character-creation module with versioned species/class/background catalogues and choice-derived Actor construction.
- [x] [Character creator MVP K1] Compose executable Fighter/Rogue level-1 grants: four Fighting Styles, Second Wind, Expertise, and Sneak Attack with shared combat/resource rules.
- [x] [Character creator MVP K1] Apply the currently supported species grants: ability bonuses, speed, skill/weapon proficiencies, darkvision, dwarf poison resistance, and dwarf heavy-armor speed.
- [x] [Character creator MVP K1] Separate cantrips, class-list/spellbook access, prepared spells and always-prepared domain spells; add an executable level-1 Life Domain and Arcane Recovery.
- [x] [Character creator MVP K1] Add shared physical-d20 species hooks: Halfling Lucky rerolls, Brave fear-save advantage, Fey Ancestry charm-save/magical-sleep protection, and dwarf poison-save advantage.
- [x] [Character creator MVP K1] Complete utility species/background hooks: Halfling Nimbleness, Trance duration, tagged Stonecunning expertise, and authored scene-gated background permissions exposed to the GM classifier.
- [x] [Test maintenance] Update the stale party-check fixture that assumes the expanded watchtower exploration contains exactly two actors.
- [x] [Exploration UX regression] Restore the `/szukaj` guidance for an unknown `/użyj` source instead of falling through to the generic declaration error.
- [x] [Character creator MVP] Add the main menu and separate New Game, Load Game, and Create Character flows.
  - [x] Add the launcher shell, move the existing runtime to `/play`, and provide separate routed New Game, compatible-snapshot Load Game, and catalogue-backed character-module entry screens.
  - [x] Add the persistent creator roster so Create Character can validate, save, reopen, copy, and recoverably delete a playable character.
- [x] [Character creator MVP] Add scenario selection followed by a one-to-five saved-character party selection.
- [x] [Character creator MVP] Replace scenario-authored player templates with the selected custom party while preserving scenario-owned NPCs and enemies.
- [x] [Character creator MVP] Complete the village-to-watchtower route with a saved custom party; use `docs/CHARACTER_CREATOR_MVP.md` as the milestone DOD.
- [x] [Character level 1–3 master milestone] Complete the legal SRD 5.1 character catalogue as one release target: all 12 classes, SRD species/variants, one SRD subclass per class, XP/level-up, executable class/species grants, spells levels 0–2, creator/roster integration, completeness audit, and documented board-game exceptions.
  - [x] Add persistent actor XP, official 2014 thresholds, party encounter awards, visible progress, character record v3, and session snapshot v24 migration.
  - [x] Add data-driven level progression and level-up choices/grants.
  - [x] Complete SRD species and variant choices.
  - [x] Complete all 12 classes and SRD subclasses through level 3.
  - [x] Complete executable SRD spell content required through spell level 2,
    replacing all 99 former assisted-table entries with deterministic combat,
    status, reaction, area or typed exploration-flag contracts.
  - [x] Add the pure one-level advancement transaction with XP gating, HP/Hit
    Dice/slot/resource reconciliation, and no implicit rest.
  - [x] Add flexible species ability-bonus choices and character-record v4
    migration; expand the top-level species catalogue to the nine SRD species.
  - [x] Execute Fighter Action Surge, Rogue Cunning Action, Barbarian Rage
    activation/damage, universal unarmed strikes and Monk Martial Arts basics.
  - [x] Add an authoritative SRD level-3 completeness manifest and gap report
    for 9 species, 12 classes/subclasses, and all 127 unique spells at levels 0–2.
  - [x] Preserve source-specific spellcasting abilities in spell access, attacks,
    save DC calculation, and session snapshot v25.
  - [x] Add per-slot rest recovery and session snapshot v26 so Warlock Pact
    Magic can recharge independently from ordinary Spellcasting.
  - [x] Replace placeholder background proficiencies with real gaming-set and
    language choices in creator, actor build, record v7, copy, and level-up.
  - [x] Add actor creature types and snapshot v27, plus executable Ray of Frost,
    Chill Touch, and Shocking Grasp secondary effects.
  - [x] Add all eight level-3 Metamagic choices, sorcery-point costs, legal
    combinations, targeting/range/action transformations, Twinned resolution,
    Careful/Heightened saves, Empowered rerolls and the bonus-action spell rule.
  - [x] Add an executable feature audit which rejects every unclassified
    species/class/subclass/choice feature and malformed assisted spell.
  - [x] Model the Ranger's humanoid Favored Enemy choice as exactly two
    humanoid races and require authored race tags before granting advantage.
  - [x] Route Bardic Inspiration, two-stage Help, and direct status, movement,
    summon, debuff and dispel targets through illuminated board fields instead
    of public actor ids; add area selection for Sleep and Faerie Fire.
  - [x] Route stabilization and secondary spell selections (Twinned, Sculpt,
    Careful and Heightened) through illuminated figures on the board; keep only
    dice values and non-spatial effect variants in the UI.
  - [x] Connect the second physical class-feature batch: Bardic Inspiration,
    Cutting Words, Preserve Life, Turn Undead, three-form Wild Shape with
    rescan-to-revert, Cunning Action, three-form Pact Weapon, and spell-first
    scanned Metamagic without pre-cast digital variant buttons.
  - [x] Complete the physical-card timing/resource follow-up: stage Prayer of
    Healing targets and dice before a cancellable 10-minute completion, use
    concentration while casting, advance the scenario clock only on completion,
    retain Goodberry's replaceable 10-charge pool, and return live class/slot
    counters in scanner feedback.
  - [x] Show an explicit mechanical effect while resolving every spell family
    and remove duplicate target selectors from status, movement, summon,
    debuff, and dispel panels.
- [x] Implement hardware adapter interface around `board.Connection`.
- [x] Add LED frame generation for selected path and movement range.
- [x] Decide first UI/runtime surface.
- [x] Add manual board checklist coverage for the first movement demo.

## SRD Level 3 Runtime Audit Follow-up

- [x] [P0 spell fidelity] Correct erroneous concentration metadata for
  `invisibility` and `gentle_repose`; add semantic validation for concentration
  and duration instead of auditing only supported schema kinds.
- [x] [P0 spell fidelity] Require every combat `effect_kind` to have a registered
  runtime consumer and close the marker-only effects identified in
  `docs/SRD_LEVEL_3_RUNTIME_AUDIT_2026-07-29.md`.
- [x] [P0 spell areas] Represent supported persistent spell zones as board objects with
  point/area targeting, entry/turn triggers, movement, expiry and visible LEDs.
- [x] [P1 Arena audit] Register all 236 canonical spell, species, class,
  subclass and cross-cutting cases with reproducible Arena configurations;
  link 177 cases to automatic behavioral tests and document an explicit,
  justified skip for the remaining 59.
- [x] [P1 character help] Extend player-facing help and Arena audit coverage
  from level-1 class grants to level-2/3 class, subclass and option features.
- [x] [P1 flanking] Exclude incapacitated allies from flanking and present
  flanking as advantage rather than a numeric `+0` modifier.

## Content Tasks

- [x] [Eksploracja z maną 0.2 — projekt i plan, 2026-09-13] Rozpisać
  cechy 14 metod (Zastraszanie Brakki na KON), trzy pierwsze przeszkody,
  rekomendację ujawnienia profilu po rozpoczęciu oraz zwykłe testy pułapek
  bojowych. Plan `docs/EXPLORATION_CONFRONTATIONS_MANA_V02_PLAN.md` obejmuje
  silnik, zapis, UI, content, wszystkie karty i praktyczne lekcje Nessy.
  Sprawdzono kanoniczne cechy bohaterów oraz aktualne generatory/walkthrough.
  To zakończenie planowania, bez zaliczania poniższego wdrożenia.
- [x] [Mana eksploracji 1/6 — katalog i porównanie, 2026-09-14] Wspólne
  14 metod z cechami, profile i trzy przeszkody. Skrypt porównał 134 400 prób
  fizycznej talii bez zwracania kart, dla rzeczywistych modyfikatorów.
  Profile pozostają różnymi rozkładami; nie mają mylących etykiet trudności.
- [x] [Mana eksploracji 2/6 — reguły i zapis] Silnik do 21, utrudnienie
  zamiast −3 po przekroczeniu, cechy i jednokrotna biegłość, osobiste pasywy,
  przerzut Loriana. Wersjonowany stan w snapshotach, rewizje poleceń,
  jednokrotny skutek i potwierdzenie zachowanych fizycznych stosów po wczytaniu.
- [x] [Mana eksploracji 3/6 — aplikacja i sceny] Działające wejścia NPC/obiekt
  dla siedmiu postaci, scena Ireny i skrzyni, wybrany kolor/pas/dobór, kości
  i jawne składniki. Ćwiczenia samodzielne ustawiają trzy postacie i metody;
  skutki sukcesu i porażki są zapisywane w odizolowanej scenie ćwiczenia.
- [x] [Mana eksploracji 4/6 — pułapki] Zwykłe wykrycie i dezaktywacja
  w combacie, zasięg, narzędzia i koszt akcji. Lekcja z atramentem dla każdej
  postaci, trwały wynik i zapis oczekującego rzutu. Zachowana obsługa dawnych
  ExplorationTrap; bez destrukcyjnej konwersji contentu i zapisów.
- [x] [Mana eksploracji 5/6 — karty] Dwie metody/cechy i premie z katalogu,
  pasyw Erynda, właściwy zakres Loriana, wspólna ściąga z utrudnieniem.
  Wygenerowano cztery formaty siedmiu zestawów HTML/PDF, manifesty i aliasy;
  arkusze 42 strony, karty 49, pakiet areny 60. Sprawdzono widok stron Erynda.
- [x] [Mana eksploracji 6/6 — samouczek] Nessa prowadzi opis → setup →
  wykonanie → wynik. Praktyczne lekcje doboru/duplikatów/pasu, 21, utrudnienia,
  trzech przeszkód, 14 metod, pasywów i pułapki. Podstawy zaliczane wspólnie,
  własne metody osobno; stabilne id i zachowany postęp combatu. Testy
  przeglądarkowe oraz pełna strona Flask z interakcją Erynda. Łącznie 123
  ukierunkowane testy przeszły; zapis sprawdzony dla 14 interakcji i pułapek
  wszystkich siedmiu postaci. Wyniki w `docs/EXPLORATION_MANA_IMPLEMENTATION.md`.
- [ ] [Próba użytkownika — eksploracja i pułapki] Na planszy sprawdzić
  nowe wejścia każdej postaci, tempo doboru, koszty metod, balans profili,
  czytelność druków oraz wznowienie zachowanych stosów. Dokumentacja:
  `docs/EXPLORATION_MANA_IMPLEMENTATION.md`.

- [x] [Eksploracja z maną — NPC i obiekty, 2026-09-13] Przygotować zbiorczy
  projekt `docs/EXPLORATION_CONFRONTATIONS_MANA_V01.md`: siedem metod
  obiektowych, stali wykonawcy, nowy proponowany pasyw Erynda +2, wspólne
  zasady do 21 i przykłady Ireny oraz skrzyni ewakuacyjnej. Zweryfikować
  obecne premie Erynda i istnienie pułapek eksploracyjnych. Aktualizacja
  dokumentów projektowych, bez wdrożenia nowego modelu.
- [x] [Wyzwania obiektowe — prototyp] Wdrożony jako część modułu 0.2:
  siedem metod, Erynd +2, trwały skutek i drogi po porażce. Dawne stany
  ExplorationTrap zachowują kompatybilny format; nie zostały usunięte.

- [x] [Konfrontacje społeczne z maną — projekt, 2026-09-13] Uporządkować
  dobieranie do 21, wybór jednej z dwóch barw, ukryte profile podatności,
  stałych wykonawców i przeszkody w `docs/SOCIAL_CONFRONTATIONS_MANA_V01.md`.
  Sprawdzić obecne Obycie i Improwizację Loriana: 5 istniejących testów
  zaliczonych przez safe_pytest. To projekt, bez implementacji minigry.
- [x] [Konfrontacje społeczne — prototyp] Wdrożono ujawnienie profilu po
  rozpoczęciu, siedem wykonawców i ich cechy, trzy przeszkody, koniec talii
  i pasywy Loriana. Próbę przy fizycznym stole obejmuje zadanie użytkownika wyżej.

- [x] [Spokojna okolica — likwidacja żerowiska, 2026-09-13] Dodać do grafu
  etap między odkryciem procederu a finałem: przygotowanie, opcjonalna pomoc
  Witka, warunkowa walka z tym samym stadem, spokojne zabezpieczenie i rezygnacja.
  Przekazywać wynik do oceny bezpieczeństwa. Uaktualnić projekt fabularny v0.3;
  mechaniki i runtime pozostają do osobnego wdrożenia.
  Walidacja Chrome: 15 kontroli nowego etapu, dróg bez walki, zagnieżdżonej
  pomocy Witka, wyszukiwania i widoku mobilnego; podgląd układu grafu.

- [x] [Spokojna okolica — interaktywny graf, 2026-09-13] Przygotować samodzielny
  `content/scenarios/campaign/spokojna_okolica_graf.html`: kolorowane sceny,
  rozwijane podgrafy, szczegóły węzłów, wyszukiwanie, zoom i przesuwanie;
  osobny graf przyczyn sprzed przygody oraz oznaczenie roboczego finału.
  Walidacja w lokalnym Chrome: 22 kontrole interakcji, geometrii, klawiatury,
  widoków 1440×1000 / 390×844 i braku zależności sieciowych; podgląd zrzutów.

- [x] [Nowa pojedyncza misja — propozycja, 2026-09-13] Przygotować roboczy
  kierunek „Spokojna okolica”: klasyczne oczyszczenie drogi, odkrycie powodów
  podtrzymywania zagrożenia, dwie opcjonalne odnogi, wybór i rola planszy.
  Dokument: `content/scenarios/campaign/SPOKOJNA_OKOLICA_PROPOZYCJA.md`.
  To propozycja do rozwijania, bez zastąpienia obecnej kampanii w runtime.
- [x] [Spokojna okolica — przyczyna zagrożenia, 2026-09-13] W propozycji v0.2
  zastąpić fałszywe ślady celowym podtrzymywaniem żerowiska przez Irenę i Witka.
  Rozpisać żeraki, logistykę, przyzwyczajanie do wozów, eskalację i tropy.
  Zmiana wyłącznie projektu; obecne potwory i scenariusze pozostają bez zmian.
- [ ] [Spokojna okolica — dalszy projekt] Po omówieniu kierunku dopracować
  dialogi, logistykę i koszty przenosin oraz mapę ratunku; sprawdzić główną
  ścieżkę bez opcjonalnych rozmów i bez udanych testów wiedzy. Ustalić wagę
  odpowiedzialności za wabienie i jeden dominujący konflikt finału. Nie traktować
  nowych mechanik ani treści propozycji jako już wdrożonych.

- [x] Define first demo scenario placeholder.
- [x] Define minimal monster schema.
- [x] Define minimal item/equipment schema.

## Open Decisions

- [x] [Physical card vertical slice] Add the reviewed action phase catalog,
  scanner routing, named combat checkpoints, Rage/Frenzy toggling, optional
  Bardic Inspiration/Guidance dice, two-stage Cutting Words, Preserve Life
  board targeting, short-rest Alarm protection, and combat Invisibility routing;
  complete scan-to-board-to-confirm flows and scanner
  feedback, then exercise them in the Mechanics Playground.
- [x] [Board-first basic attack] Retire the redundant `basic_attack` card and
  keep ordinary weapon/unarmed attacks behind contextual enemy-field selection;
  reserve physical cards for spells, class features and special maneuvers.
- [x] [Seven board-game archetypes] Replace the visible twelve-class starter
  roster with seven role-first level-3 builds defined in
  `docs/BOARDGAME_ARCHETYPES_LEVELS_1_3.md`: complete combat/exploration kits,
  fixed caster decks without preparation, a
  content-authored `ExplorationCardIntent` handler/attempt contract, short and
  long rests exposed only by eligible instances, hidden legacy starters and
  regenerated physical card set. The runtime installs complete level-3 kits
  and every personal card is available from the start.
- [x] [Archetype flaws and exploration reactions] Give each of the seven
  archetypes one deterministic flaw, synchronize its combat/exploration
  trigger, add data-driven card reactions to the village and abandoned
  watchtower, connect route preparation to the navigation roll, and regenerate
  color plus black-and-white playtest PDFs with the flaw rules on hero cards.
- [x] [Character-dependent exploration tiles] Disable physical exploration-card
  declarations without deleting their assets; let authored zone options require
  and auto-assign a party hero, show that hero on the tile, and add two optional
  narrative interactions for each of the seven playable archetypes across the
  village and abandoned-watchtower MVP.
- [ ] [Deferred archetype progression] Design progression only after scenario
  playtests establish whether levels, card unlocks, upgrades, or a hybrid are
  the better reward loop. Until then all seven heroes remain level 3 with their
  complete personal decks.
- [x] [Physical combat-card batch 1] Route 15 common spell cards through one
  shared attack/healing/combat-action/reaction dispatcher reused by the screen
  menu; cover single-target attacks, saves, healing, areas, movement, statuses,
  summons, multi-projectile damage and Shield in the Mechanics Playground.
- [x] [Physical combat-card batch 2] Route 15 damage and battlefield-control
  spell cards through the shared dispatcher; cover attack/save riders,
  directional and radial areas, separate Scorching Ray attacks, persistent
  difficult/obscuring zones and concentration, including scan-to-board Fog
  Cloud resolution in the Mechanics Playground.
- [x] [Physical combat-card batch 3] Route 15 defense, support and reaction
  spell cards through the shared dispatcher; auto-bind self spells, add scanned
  Hellish Rebuke after applied enemy damage, and make See Invisibility reveal
  both invisible and per-observer hidden enemies in the Mechanics Playground.
- [x] [Physical combat-card batch 4] Route 15 debuff and persistent battlefield
  spell cards through the shared dispatcher; support repeated saves, delayed
  riders, movement/start-turn zones, explicit healing targeting, and Moonbeam/
  Flaming Sphere rescan-to-move without spending another slot.
- [x] [Physical combat-card batch 5] Route 15 weapon buffs, mobility, rescue and
  utility spell cards through the shared dispatcher; bind selected weapons,
  support three emulated familiar forms, create/spend the Goodberry pool,
  stabilize from a scan, and exercise scanning plus representative resolutions
  in the Mechanics Playground.
- [x] [Physical martial-feature batch 1] Route Fighter, Barbarian, Monk and
  Paladin cards through their existing class-feature resolvers; add a shared
  scanner prompt for physical dice, weapon, saving-roll and spell-slot input,
  preserve pending hit/reaction windows for Divine Smite and Deflect Missiles,
  and cover all four classes in the Mechanics Playground.
- [x] [Physical card Arena smoke matrix] Start a fresh Mechanics Playground
  encounter for every one of the 12 classes and scan a real card from each
  starter set; verify scanner routing, next-step prompts and resource feedback.
- [x] [Martial archetype decision budget] Expand the level-1 combat decks for
  Garran, Brakka, Mira and Erynd using existing resolvers, add short/long-rest
  resources for their remixed techniques, and verify scans plus resource spend
  in fresh Mechanics Playground encounters.
- [x] [Seven-hero combat deck audit] Remove exploration cards from the seven
  current print decks; balance each level 1–3 pool to 7–9 tactical combat
  cards; synchronize level gates, named resources, passives, flaws, dossiers
  and statistics; verify routes, reaction windows and resource spending in the
  Mechanics Playground; regenerate color and toner-ready print sets.
- [x] [Physical card timing reminders] Add the compact inline combat reminder
  driven by the legal contextual-action catalogue and ordered reaction window;
  cover every printable combat card in the seven active decks, allow an
  explicitly selected non-active reaction owner, and verify action plus reaction
  reminders in the Mechanics Playground.
- [x] [Level-3 hero gameplay review] Start all seven heroes at level 3, add +2
  to each primary ability, expose every personal card immediately, replace the
  weak True Strike variants with same-turn attack setup, make MANEWRY and
  EKWIPUNEK cards open real menus, align spell riders/flaws/deck access with the
  runtime, and show finite resources in legal-card reminders.
- [x] [Level-3 dossier resource pass] Remove the obsolete level 1–3 progression
  section, replace it with exact card pools/slots and recovery rules, list only
  physical-deck spells on character sheets, and recalculate Lorian's Inspiration
  pool after the archetype Charisma bonus.
- [x] [Target campaign flow authoring] Extract the complete `Ostatni transport do
  Czarnego Brodu` map/NPC/interaction/player-tile flow into editable Mermaid and
  generate a multi-page `.drawio` workspace with individually movable nodes,
  collapsible instance groups, typed colors and regeneration coverage; model
  the reusable Guild hub as Map 0 with mandatory Nessa briefing, gated departure
  and visibly reserved but mechanically inactive future facilities.
- [x] [Guild Map 0 implementation spec] Create the living technical source for
  Nessa's mandatory briefing, optional information cards, persistent flags,
  departure flow and cross-scene knowledge callbacks that reward players for
  deliberately applying remembered details without blocking ordinary discovery.
- [x] [Guild Map 0 mechanical runtime] Add deterministic, knowledge-gated LLM
  argument scoring before a physical social roll; support unique performers,
  critical-failure/exhaustion effects and assigned NPC-goal actors; implement
  the loadable Nessa briefing, three negotiation outcomes, Erynd document check,
  persistent knowledge flags and gated departure to a Map 1 placeholder; render
  Nessa's negotiation response in a second, post-roll LLM phase while keeping
  the authored mechanical result immutable and providing safe fallbacks.
- [x] [Guild Map 0 authored briefing] Complete Nessa's opening assignment,
  disappearance, cargo, personnel, Insight, Erynd document-check and departure
  text; align route marks, medicine-cache details, caravan roster and propagated
  knowledge flags with the living campaign specification.
- [x] [Guild Map 0 art pack] Define the shared gothic-comic art direction and
  production prompts, generate the guild map, Nessa portrait, desk scene, seven
  interaction tiles and three future-feature placeholders, and bind the current
  zone, NPC point and authored goals to their scenario-local assets.
- [x] [Guild Map 0 hotspot and contract closure] Bind Nessa, Archive,
  Quartermaster, Training and the departure gate to stable board positions
  matching the isometric map; keep the locked gate inspectable, summarize only
  learned departure facts, define level-3-scale contract values, pay advances
  to every living party member, persist preparation packs, and verify the full
  Map 0 → Map 1 handoff.
- [x] [Guild Map 0 physical setup parity] Add the MVP-style paper-map setup,
  portrait 50 × 75 cm print source, eight-page A4 and full-size PDFs, location
  preview/confirmation, immediate single-field Nessa placement after unfolding
  the map, portrait preview before accepting her interaction, and illustrated
  Archive, Quartermaster and Training hotspots on the same physical map.
- [x] [Player campaign launcher] Make Ostatni transport the default runtime
  campaign; enforce New Game as physical-card party selection followed by
  scenario selection; expose only the Guild Map 0 campaign in the player
  catalog while retaining MVP, arenas and playgrounds as direct test content.
- [ ] [Black Ford Map 1 implementation] Replace the Zawalona Droga placeholder
  with the authored locations, interactions, encounter flow and callbacks from
  the campaign graph, consuming the knowledge flags propagated from Map 0.
  - [x] Add the encounter-first phase contract: immediate arrival trigger,
    exploration hidden until victory, and content-driven terminal Game Over on
    defeat, retreat or surrender.
  - [x] Add a dedicated encounter-start checkpoint and exact Game Over retry
    that restores party resources, actors, positions, terrain and initiative
    without overwriting the ordinary scenario save, then repeats the physical
    hero, enemy and terrain setup before reactivating combat.
  - [x] Add approach-mode and Erynd-knowledge opening variants.
  - [x] Add final tactical terrain, monster scaling, statblocks and AI profiles.
    - [x] Define the encounter fiction, tactical zones, provisional stat targets,
      party-size presets, morale sources, low-HP behavior, flee flow and
      exploration handoff in `MAPA_1_GLODNE_CIENIE_ENCOUNTER_SPEC.md`.
    - [x] Replace the bespoke behavior tree with the implementable
      `weighted_utility_v1` contract and a tunable Hungry Shadow pack JSON
      profile covering roles, fuzzy features, seeded noise and morale.
    - [x] Prepare the top-down encounter map base and editable tactical-zone
      overlay, AI decision diagram, complete skirmisher/leader statblocks and
      the LED feedback storyboard/semantic-role contract.
    - [x] Produce the comic-style v2 battlemap with stronger linework and
      saturated colors, plus explicit enemy start fields and party-size setup
      groups in the editable overlay and tactical layout JSON.
    - [x] Revise the battlemap to v3 with a restrained dark-fantasy palette and
      lower texture density while retaining the tactical layout and enemy slots.
    - [x] Wire the v3 map into encounter setup, add data-driven party-size
      variants 1–5, apply the tactical terrain to pathfinding, expose the map
      preview, and preserve the selected setup through Game Over Retry.
    - [x] Connect the `weighted_utility_v1` runtime baseline: profile/role/tag
      loading, deterministic intent scoring, pack morale, regroup/guard,
      forced flee/cornered behavior, escape fields, dead/escaped outcome ledger,
      victory without killing every beast, and snapshot persistence.
    - [x] Complete the remaining tactical scoring inputs (cover, isolation,
      opportunity risk, hazards and guard-zone threat) and tune voluntary flee
      behavior with simulated parties before the manual balance pass.
    - [x] Add the production-AI playtest runner, execute and persist 64 seeded
      fights across eight compositions and party sizes 1–5, fix repeated
      pathfinding, idle regroup/guard/flee loops, Dash approach, fixed-deck
      preparation and spell-handling regressions, and publish the result table.
    - [x] Add three walkable passive defensive spots granting automatic +2 AC,
      revise the battlemap/layout to v4, raise Hungry Shadow HP slightly, let
      guard/regroup attack after movement, and tune ranged-fire cover response
      so reachable attacks and low-HP/low-morale flee behavior take priority;
      rerun the 64-fight matrix with no timeout or deadlock.
    - [x] Add a data-driven `attack_bonus` that raises only attack rolls, give
      every Hungry Shadow attack `+1` (`+5` skirmisher, `+6` leader), and rerun
      the 64-fight matrix: 517 total damage, 64 resolved fights, no timeout.
    - [x] Add a deterministic end-to-end campaign walkthrough covering New Game,
      physical-card party selection, Guild setup, the complete useful Nessa
      briefing, checked knowledge, negotiation, quest activation, travel,
      same-session Map 1 handoff, encounter setup/initiative/checkpoint and
      victory-gated aftermath; publish its audit report and regression command.
  - [x] Replace the aftermath placeholder with same-map wagon and track
    investigation, Teren aid/question/fate, young-beast choice, route selection
    and a validated handoff to the Black Ford entry shell.
- [x] [Physical card print synchronization] Regenerate all 12 character-set
  PDFs from the current phase/effect catalogue, omit removed cards, validate
  every QR/manifest/page count, and add individual plus combined toner-friendly
  black-and-white A4 character sheets for the starter roster.
- [x] [Physical card low-toner playtest edition] Add illustration-free,
  front-only black-and-white card layouts with crop marks and validated QR
  payloads; generate 12 per-character PDFs and one combined 100-page test PDF.
- [x] [Exploration performer card scan] Let a scanned hero card select the
  performer for a checked zone option exactly like clicking that hero in the
  local action composer, while rejecting defeated, hostile or invalid actors.
- [x] [Physical spell preparation] Replace setup checkboxes with a visual
  default card set accepted by `ACCEPT`; let `DECLINE` start a scanner-only
  custom set that validates each spell and completes at the actor's limit.
- [x] [Board-native exploration navigation] Stop using `ACCEPT`/`DECLINE` for
  location and instance navigation; keep all location markers lit, use repeated
  `A → A` selection to confirm entry, reserve one red system-exit pad beside at
  most seven authored actions, and block that exit during unresolved flow.
- [x] [Hybrid board and numpad controls] Mirror exploration choices on numeric
  keypad keys, navigate combat context actions with Numpad 8/2, Enter and minus,
  keep the visible combat list compact with explicit overflow indicators, and
  require repeated board selection for movement, hotspots and area anchors.
- [x] [Exploration interaction input regression] Route the visible action button,
  Enter and `ACCEPT` through the same open-composer action; require explicit
  confirmation for automatic NPC goals, lock authored character moments to their
  assigned performer, expose all unlocked locations of the current scene after
  leaving an instance, and separate purple interaction LEDs from the fourth white
  option.
- [x] [Stable instance tiles and scoped results] Keep every interaction action on
  its initially assigned board position, number and color when sibling actions
  disappear; scope roll acknowledgements to messages created by the current
  request so an earlier NPC result cannot leak into a later location.
- [x] [Brakka QR and gate group-check regression] Accept owner-bound v2 combat
  card payloads from the keyboard scanner, keep board selection listening for
  five minutes, ignore cancelled stale scans, and make force-entry a fixed
  whole-party check resolved by any single success.
- [x] [Staged scenario travel] Split continuation into pace, hero-card
  navigator and physical-roll stages; show arrival/perception/stealth tradeoffs,
  preserve Natural Explorer and forced-march shortcuts, and make control cards
  advance or retreat one stage at a time.
- [x] [Ostatni transport travel consequences] Turn the Guild departure into a
  60-minute time-versus-readiness decision with authored pace explanations,
  Survival navigation delay, distinct Hungry Shadows combat openings, and
  persisted arrival-window/timing flags for later campaign maps.
- [ ] [Physical card timing follow-up] Give 10-minute Prayer of Healing a
  dedicated encounter-time/long-cast presentation instead of resolving its
  already-tested multi-target healing immediately after confirmation, and
  expire unused Goodberries after 24 hours of exploration time.

- [x] Preserve dynamically granted area attacks (including Rhogar's Breath
  Weapon) in the combat preview payload so the player can explicitly confirm
  the attack or return to area selection before spending the action/resource.
- [x] Replace the idle hero combat view with a persistent Numpad-driven action
  mode list, movement-first LED previews, Enter-confirmed area placement that
  retains legal anchors, Numpad 0 turn ending, and a 75-foot board range cap.
- [x] Present spell-backed starter-deck actions under their hero archetype
  groups (Taktyki, Dzikość, Fortele and Instynkt), label class actions as
  special abilities, and keep attacks from duplicate weapon copies uniquely
  selectable.
- [x] Accelerate the Hungry Shadows encounter with a player-chosen 5×4
  deployment zone, closer asymmetric enemy positions, flanker/harrier roles,
  real approach-progress scoring, anti-dogpile prey memory and one board
  confirmation for ordinary enemy turns; reduce ordinary Hungry Shadow Rend
  damage to `1d4 + 2` for the coordinated-pack rebalance.
- [x] Replace Hungry Shadows utility tactics with deterministic coordinated-pack
  focus fire, per-support attack/damage bonuses, leader ranged/melee and deferred
  healing, irreversible leader/follower retreat, illuminated escape targets,
  zero-progress dead-loop guards, and removal of the obsolete old bell.
- [x] Make targetless combat previews non-blocking: keep the active-hero LED
  passive, stop automatic scanning when an attack or healing action has no legal
  target, show an explicit player-facing explanation, move the action chooser
  into a compact list/stats layout, and prevent Numpad minus from cancelling a
  healing roll while its numeric input is focused.
- [x] Rebuild Brakka around three per-long-rest Rages and a three-point
  per-Rage Ferocity pool; replace Frenzy/Action Surge/Cunning Action and the
  two pseudo-spells with Reckless Attack, Powerful Strike, Shoulder Check,
  Hard as Rock, Acceleration and Deafening Roar, including board targeting,
  reaction timing, critical-save riders and edge-case tests.
- [x] Remove Danger Sense from Brakka's board-game archetype so her runtime
  passive rules match the deliberately reduced printed passive set.
- [x] Rebalance Dagna's starter kit: replace Warding Bond with Spiritual
  Weapon, expose Life Domain healing in card text, use the 75-foot board range
  for Guiding Bolt, hide Turn Undead without a legal target, and make her
  rescue flaw grant enemy saves advantage against her hostile spells.
- [x] Remove Dagna's non-playable Diagnosis feature, its card route and stale
  authored scenario references while retaining ordinary Medicine checks.
- [x] Rebalance Dagna's active spells: reduce Guiding Bolt to `2d6`, turn
  Sacred Flame into a 15-foot enemy-only cone, make Aid expire at encounter
  end, select Lesser Restoration conditions from actual target state, and
  verify Spiritual Weapon as a targetable 1 HP / AC 18 blocking flanker with
  owner-adjacent initiative.
- [x] Remove Stonecunning and Shelter of the Faithful from Dagna's curated
  board-game archetype and passive card while preserving her flaw.
- [x] Rebuild Dagna around mobile combat support: make Bless a moving 10-foot
  aura, replace Sanctuary with the 5-foot Divine Care attack/damage penalty
  aura, replace Aid with the limited-use Healing Grace aura, add the
  once-per-turn Field Medic Step prompt, dynamic actor statuses and optional
  LED aura inspection, with action previews retaining display priority.
- [x] Rebuild Garran as a stationary shield commander: make Action Surge spend
  a bonus action, replace field healing with Shield Bash, make Defensive Stance
  consume movement, add four Strength-scaled Tactics with board targeting and
  one-shot protection redirection, replace Command Guilt with cumulative-wound
  Remorse, remove Guard Duty/Military Rank, and cover edge cases and saves.
- [x] Rebuild Erynd as a mobile ranged controller: replace swords and travel
  passives with a Strength-based hunting knife, First Blood, Scout's Vigilance,
  movement-cost Aim and four Instinct arrows; collect the physical d4/d8 rider
  rolls, enforce ammunition/resources, statuses and expiry, allow free Hunter's
  Mark transfer after defeat, and cover profile, scanner and edge-case tests.
- [x] Make combat Hide unique to Mira with per-observer active Perception,
  20/25-foot stealth movement, visibility LEDs, manual exit, observer-aware AI
  targeting and accidental path-collision replanning; replace her shortbow with
  15-foot throwing knives and stack flank/hidden damage as `+1d6/+2d6/+3d6`.
- [x] Complete Mira's stealth-killer rebuild: Dexterity-scaled Fortels, ranged
  AC, Instinctive Dodge and Smoke Screen, Hamstring/Piercing/Vault/Blade attacks,
  persistent wound statuses, 45-foot combat trap detection, and retirement of
  Break In plus the obsolete rogue/spell package, with edge-case tests.
- [x] Rebuild Lorian as a social crossbow tactician: two-shot Crossbowman,
  Mocking/Provoking shots, Inspiration-linked Counterpoint and Distracting
  Shout reactions, narrow social expertise with one final Improvisation reroll,
  Panic Whisper, Stage Command and Accelerated Refrain, including bounded AI
  movement, silence fallbacks, bonus-action competition and edge-case tests.
- [x] Recast Lorian as a bard-inventor: reusable optical, destabilizing,
  provoking and entangling crossbow techniques; nearby-ally flaw; broad
  non-combat Charisma expertise; short-rest Inspiration; and persisted
  once-per-NPC Improvisation.
- [x] Rebuild Nimra as a save-based area controller with an Intelligence-scaled
  Metamagic pool, immediate board previews and atomic confirmation; add a
  deterministic ally-risking Lightning Path chain and make Arcane Leak Echo
  prevent repeating either the previous round's spell or Metamagic.
- [x] Simplify the shared combat action surface to Move, weapon attacks,
  character abilities/spells, Change Weapon, Use Item and End Turn; keep
  retired actions as hidden legacy resolvers, move Dash/Disengage to Erynd,
  Grapple to Brakka, auto-stand on movement, and collect victory loot into a
  persisted shared party pool.
- [x] Replace eager combat action previews with an explicit list/preview/selection
  protocol: Numpad 2/8 navigates without LED churn, first Enter arms the preview,
  board clicks only select, second Enter commits, and minus cancels without cost.
- [x] Route Bardic Inspiration selected from Lorian's own combat-field menu through
  board target selection instead of resolving it prematurely without an ally.
- [x] Generate the seven print-ready keyboard character sheets with shared basic
  action keys, hero-specific shortcuts, automatic-reaction reminders and Nimra's
  metamagia-first flow; keep exact Polish text in a reproducible render script.
- [x] Implement the keyboard-first combat input contract used by the new sheets:
  shortcut opens preview, Enter commits, Esc/Backspace cancels without cost, and
  the idle UI shows only the active hero and a prompt to use the character sheet.
- [x] Extend each keyboard character sheet with a second A4 dossier page containing
  history, motivation, personal goal, passives, flaw, resources and turn guidance;
  keep active skill descriptions on the first quick-reference page.
- [x] Improve the keyboard sheets' three-column readability with larger display-font
  headings, stronger parchment contrast and adaptive vertical spacing for dense heroes.
- [x] Replace Nimra's number and Shift combinations with single-letter shortcuts for
  all Metamagic options and spells; synchronize the runtime bindings and print sheet.
- [x] Generate a separate low-ink, grayscale A4 edition of all keyboard sheets and
  dossiers for inexpensive home-printed playtests.
- [x] Resolve the keyboard playtest blockers found in review: defer the `D` shortcut
  around HID-card prefixes, cancel pending Nimra Metamagic with Esc/Backspace, ignore
  modified/repeated shortcuts and remove stale 8/2/minus guidance from the main flow.
- [x] Replace click-heavy physical-roll forms with a centered keyboard wizard that
  collects one die result at a time, validates die bounds, adds visible sourced
  modifiers, supports Backspace correction, and confirms a final roll summary.
- [x] Keep the physical board LEDs off during non-combat point interactions and
  exploration resolutions, restoring hotspot guidance after returning to the zone.
- [ ] [Hungry Shadows balance] Revisit the three-hero scaling and coordinated-pack
  pressure against the 2026-09-03 baseline (20% wins for Garran/Dagna/Erynd and
  45% for Lorian/Mira/Nimra across 20 seeded runs per composition).
- [x] [Mobile combat UX] Remove the tall empty board/workspace gap that pushes the
  active hero's action list below the first viewport at 390×844, then repeat the
  desktop/mobile render and keyboard/touch smoke test.
  Fixed 2026-09-05: scoped drawer styles to `#side-panel`, allowed combat grid
  children to shrink, and placed mobile actor details after the decision. Chrome
  checks passed at 1440×1000, 768×1024 and 390×844 for both connection-banner
  presentation states, internal overflow, drawer isolation, keyboard preview/cancel
  and screen-fallback selection; six focused pytest checks also passed.
- [x] [Combat touch continuity] Add screen confirmation/cancellation to combat
  action previews through the existing dispatcher. Keep mouse controls in the
  default-collapsed "Awaryjny wybór ekranowy" disclosure; preserve its explicit
  open/closed choice across list/preview transitions without replacing keyboard
  and paper-sheet input. Verified desktop/mobile mouse selection, cancellation
  without resource cost, explicit end-turn confirmation and unchanged shortcuts;
  ten focused pytest checks passed.
- [x] [Combat shortcut readability] Let shortcut badges size to their text and
  wrap full action labels; use a single-column index on phones. Verified SPACJA
  and Nimra's 26 visible shortcuts without overlap or clipped labels.
- [x] [Combat HUD clarity] Keep one turn HUD and one current-decision card; move
  level, slots, resources and the full effect list into collapsed actor details.
  Preserve critical HUD statuses and reaction reminders, hide duplicate action-card
  reminders while the shortcut menu is present, retain details for the same actor
  and collapse them on actor change. Verified 320/390/768/1440 px layouts, connected
  and disconnected presentation states, keyboard preview/cancel and mouse fallback;
  eight focused pytest checks passed. Documented the layout in PLAYER_UI_DESIGN.md.
- [x] [Campaign walkthrough contract] Confirmed the documented replacement of
  the historical +6 leader attack in commit `dd5d4bf`: life drain uses +3 and
  spirit bolt +5. The walkthrough now checks all enemy attack sources by id;
  content and balance are unchanged. Complete walkthrough to Black Ford entry
  and ten coordinated-pack AI tests passed on 2026-09-05. Updated the technical
  contract and separated current walkthrough results from the historical audit.

- [x] [Hero selection guidance] Add role, play style, editorial complexity and
  separately expandable ability/flaw summaries for the seven playable heroes.
  Preserve mouse/keyboard selection and the 1–5 party contract; scroll desktop
  cards without hiding navigation and keep readable mobile cards. Launcher tests
  and browser checks cover selection, disclosures, limits and scenario/back flow.
- [x] [Hero guidance consistency] Reconcile all seven playable heroes with the
  current board-game rules: shared flaw/passive/feature help, actual resource
  recovery, spell costs, canonical names, keyboard access and generated reference.
  Erynd's longbow flaw now counts conscious player allies beside each target.
  Fix custom-knife proficiency and preserve Archery when rebuilding attack sources.
  Hide spells outside curated decks in the exploration sidebar. Regenerate color
  and monochrome cards with complete text, including keyboard sheets/dossiers.
  Focused rules, UI, print consistency and campaign walkthrough checks passed.
  Evidence: `docs/HERO_RULES_CONSISTENCY_2026-09-05.md`.

Review evidence and UI/gameplay proposals: `docs/PROJECT_REVIEW_2026-09-05.md`.

- [x] UI framework: local Flask/web UI for the current runtime and future authoring modules.
- [x] Content licensing/source strategy for D&D 5e data.
- [x] Save file format and state versioning.
- [x] Whether diagonal movement follows 5e optional grid rules or simplified board rules.

- [x] [Recruitment arena] Add optional Map 0 with Nessa and one fresh hero at
  a time, all seven heroes, dummy 50 HP / AC 10 / +5 hit / zero damage,
  normal board setup and combat, finish by defeating dummies or talking to
  adjacent Nessa. Include repeatable support/area variants, creature-type
  selection, manual physical mana, isolated saves and completed-trial markers.
  Rules, save/load, board-selection and browser checks documented in
  `docs/RECRUITMENT_ARENA.md`.

- [x] [Recruitment terrain] Add a central rubble strip with double movement cost,
  tall crates and a 2×2 pillar; preserve clear detours and Nessa access.
  Synchronize scenario setup, SVG symbols/legend and player instructions.

- [x] [Setup rule clarity] Separate environment steps by their rules as well
  as type. Classify the arena's passable low cover as cover and explicitly
  distinguish its AC bonuses from solid obstacles that forbid entry.

- [x] [Action tile mana] Show structured mana symbols on every physical-mana
  action tile, fallback row and preview, including free actions, movement
  continuation and Metamagic surcharges. Remove duplicate class-feature aliases
  when the same ability already has an attack/healing source selector.
  Checked all seven menus, Brakka's Q/S/Esc flow and 1280/390 px browser layouts;
  28 focused tests passed (menu mana 10, keyboard 4, Garran movement 14).

- [x] [Dice iconography] Add distinct local SVG icons for k4/k6/k8/k10/k12/k20
  to the physical-roll wizard and review, including bounded d20 inputs and
  multi-die counts. Browser checks cover all six dice, advantage, split 2k6,
  fixed values without dice, validation, autofocus, back/review/submission
  and 390/1280 px layouts; JavaScript compilation and diff checks pass.

- [x] [Active rage availability] Hide Brakka's Rage activation throughout an
  active physical-mana rage, both before and after spending the main action.
  Reject stale/direct activation without toggling rage or spending a bonus;
  restore availability when rage ends. Save/load and legacy rage regressions
  pass: 8 playtest checks plus 2 generic rage/Frenzy checks.

- [x] [Shield Bash physical rolls] Replace silent automatic k20/k20/k4 rolls
  after selecting Garran's target with a staged flow: physical hero k20/k4,
  automatic enemy k20 (clarified 2026-09-07). Ask for
  damage only after winning the contest, show damage/HP/push in a persistent
  result card and commit only on confirmation. Preserve terrain-entry effects,
  reject duplicate/out-of-range submissions and block saving unfinished rolls.
  Six flow regressions, seven Garran rules tests and full browser Enter flow
  at 1280/390 px passed; add explicit structured observation events.
  Enemy rolls are generated once on the server, shown in the result and cannot
  be supplied by the client; invalid/repeated inputs do not reroll the enemy.

- [x] [Shield Bash bonus action and mana wording, 2026-09-07] Make Garran's
  Shield Bash a bonus action with d6 + Strength modifier damage and the existing
  push. Keep it available after a basic attack; prevent a second bonus action.
  Clarify all seven mana passives/flaws, add Garran payment examples, and use
  matching SVG mana symbols in color/minimal sheets and color/BW cutout cards.
  Regenerate the canonical PDFs and familiar legacy print links.

- [x] [Combat action economy columns, 2026-09-07] Group combat shortcuts and
  screen fallback by main action, bonus action, and free options above movement.
  Keep equipment/end-turn controls below the columns. Use canonical ability
  timing, preserve shortcut/preview/confirmation behavior, and stack columns on
  narrow screens. Verify all seven heroes, mana symbols and browser navigation.

- [x] [Spent action choices, 2026-09-07] Filter the authoritative turn menu by
  remaining action/bonus/reaction/movement budgets; reject stale option IDs.
  Remove unusable modifiers after the main action and movement below one step.
  Preserve partial movement and the remaining attacks of the already-started
  Lorian series or multiattack technique, without exposing a different action.
  Verify all seven heroes, fresh-turn restoration and actual keyboard use.

- [x] [Black mana and MTG-style symbols, 2026-09-07] Replace purple mana
  with black in costs, combat UI, wave 5, rules help and all character prints.
  Use sun/drop/skull/flame/tree and a circled 1 for generic payment. Explain
  basic-land playtest cards; preserve internal cost IDs and saved wave labels.
  Regenerate all 28 hero PDFs, four collections and existing print aliases.
  Verify 45 focused tests, browser icons and all 28 page layouts.

- [x] [Return to actions after movement, 2026-09-07] Close the movement
  preview after each resolved segment, including opportunity attacks, and
  show the updated action menu. Preserve remaining movement and the original
  mana payment; exhausted movement disappears. Cover all seven heroes,
  repeated segments, selecting an attack and invalid movement destinations.

- [x] [30-cell board panel preview, 2026-09-07] Build a landscape recruitment
  arena preview with one bottom row: six basic icons, twenty distinct runes
  and minus/plus/accept/back. Include matching card/dialog symbols and an
  interactive dice prototype starting at half the die size. Document tradeoffs.
- [ ] [30-cell panel runtime] After the ergonomic trial, audit situational
  options and freeze symbol mappings; reserve the long edge in scenario setup,
  movement and targeting. Connect sensor press/release events, dice input,
  reactions, dialogs, waves and session navigation. Regenerate production cards
  and validate a complete session without keyboard/mouse; no LLM roll bonuses.

- [x] [Rune cards and arena panel plan, 2026-09-07] Share thirty SVG signs
  and explicit hero ability mappings between arena preview and all four print
  formats. Replace printed keyboard labels with runes/basic icons, remove the
  rounded internal arena border, support direct switching between available
  previews and Back to the full menu, and document arena-only rollout with
  sensor, spatial, dice and whole-session acceptance checks.

- [x] [Panel movement icon, 2026-09-07] Use a walking person for movement
  across the arena preview and all card formats. Clarify the basic weapon
  control as “Zmiana broni”; document that the interaction control is a
  proposed shortcut to existing scene interactions, redundant for direct Nessa selection.

- [x] [Remove panel interaction button, 2026-09-07] Remove its command,
  icon and card instructions. Keep slot 4 blank and every other symbol fixed.
  Preserve single-figure exploration and direct NPC/object field selection.

- [x] [Combined monochrome A4 playtest pack, 2026-09-07] Generate one PDF
  with assembly/calibration instructions, nine tiled arena sheets and all
  seven current hero card sets (45 pages total). Preserve 25 mm cells,
  750 × 500 mm board, 10 mm labelled glue overlaps, cut lines and blank
  interaction slot. Use toner-friendly vector art and verify coverage,
  physical scale, current symbols, PDF pages and card layouts.

- [x] [Reusable arena grid and terrain cutouts, 2026-09-07] Remove all
  permanent actor/start/terrain marks from the printed map. Add one A4 sheet
  with 19 labelled 25 mm terrain tokens; preserve the panel, tiled overlaps
  and all hero cards (46 pages). Give each terrain kind its own setup
  instruction and LED footprint, matching the printed token label.

- [x] [Panel lighting preview, 2026-09-07] Show available actions at 65%,
  selected at 100%, other available previews at 35% and legal controls at
  85%; unavailable fields are unlit. Restore menu brightness on Back,
  preserve direct switching and lock action runes during dice input.
  Document matching physical LED behavior and target-layer composition in
  the existing panel runtime plan; hardware connection remains pending.

- [x] [Arena initiative on physical panel, 2026-09-07] Connect the actual
  initiative flow to board scans: red minus, green plus, blue accept and
  amber correction; start every d20 at 10. Keep a shared server draft,
  separate advantage dice, review before resolution and automatic enemy
  rolls. Allow scans inside the initiative overlay, discard stale requests,
  and avoid sending STOP after a completed scan during re-rendering.

- [x] [Live action-menu UI and asset refresh, 2026-09-07] Verify live menu
  and action previews show printed icons/runes for all seven heroes.
  Label unmapped fallback variants as screen choices and replace remaining
  action-preview keyboard instructions. Version all exploration JS/CSS URLs
  by file contents so ordinary refreshes load the current interface after
  updates; cover version stability/invalidation and current UI wording.

- [x] [Arena runtime panel and action colors, 2026-09-07] Connect the printed
  action/rune slots to live combat availability and board scans; retain targets
  under the panel LED layer, support preview switching and Back, and lock runes
  during dice entry. Bridge all existing dice-wizard steps to red minus, green
  plus and blue accept, with half-die defaults, bounds and explicit review.
  Replace keyboard badges with shared print SVGs; use one responsive tile grid
  with dark main/bonus/movement/control colors, without scrolling category columns.
  Reserve the arena panel edge outside playable geometry and reject old saves
  with actors on that strip. The broader whole-session panel audit above remains
  open (contextual submenus, reactions, setup/navigation and physical sensor trial).

- [x] [Compact action menu colors, 2026-09-07] Use green backgrounds for
  main actions and movement, blue for bonus actions, and explicit economy labels.
  Pack printed runes into one responsive grid; show mana across the full tile
  width and reduce spacing without clipping labels or prices. Browser checks:
  all seven heroes at 1284x720; Nimra at 1920x1080, 1284x595, 1024x768 and
  390x844, with no tile overflow or horizontal scrolling. Small screens retain
  normal page scrolling for readable text; no independently scrolling columns.

- [x] [Action economy colors on screen and board, 2026-09-08] Separate main
  action blue, bonus action orange and movement green backgrounds. Color live
  panel runes by the same authoritative economy groups; equipment/end-turn LEDs
  are white. Preserve menu/preview brightness and independent dice controls.
  Verify all seven hero menus and colors sent through the board adapter.

- [x] [Arena print calibration, 2026-09-08] Apply the measured 250/244 scale
  correction to arena tiles, panel, cut/glue lines, terrain tokens and the guide
  ruler. Keep A4 paper and hero card scale unchanged; reposition tiles to retain
  printer margins. Accept the current 19-column play area plus physical panel
  when rebuilding the full 30×20 print. Regenerate the combined PDF and manifest.

- [x] [Encounter setup on the board, 2026-09-08] Confirm figure and terrain
  placement with the blue printed ✓ button and automatically arm setup scans.
  Stage start-zone choices before committing: multiple free fields require a
  click, the last free field is selected implicitly, and players can change
  their choice until confirmation. Keep multi-field terrain groups intact,
  clear each actor's selection and reject stale scans between setup steps.
  Show the selected field and board instructions, with a gated screen fallback.
  Cover physical scan/API behavior and verify Garran's setup in the browser.

- [x] [Setup transition fixes, 2026-09-08] Re-arm automatic board input after
  the reconnect request clears its busy state; the first map step previously
  lit accept without starting a scan. Add a native blue ✓ scan target for
  starting initiative after setup and any optional stealth. Keep this press
  separate from accepting the first die, with stale-revision protection.
  Verify the reconnect path and all setup steps through initiative in a browser.

- [x] [Steady automatic LEDs and Shield Bash clarity, 2026-09-08] Preserve
  normal brightness while automatically scanning, avoiding brightness pulses
  and redundant WLED frames on each press. Include transport time in projectile
  frame intervals instead of adding it to every full delay. Keep explicit manual
  scan brightness available. Clarify Shield Bash's physical player k20, starting
  counter value, automatic enemy Strength roll, and both equations before commit.
  The observed trial submitted the initial 10; no player die is rolled by the app.

- [x] [Pause after sword damage, 2026-09-08] Reuse the shortest paths already
  computed by movement_range when planning an approach to scene objects.
  Check destinations by cost and stable coordinate order, returning the first
  legal interaction instead of recomputing the whole board for every tile.
  Reproduce Garran (13,15), dummy (12,14), 11 damage: profiler reduced full
  movement searches from 861 to 21 and damage processing from 36.3 s to 1.1 s
  with the same local simulated transport. Cover route selection, exhausted
  actions and the damage-to-next-action API flow. Existing legacy approach
  integration tests remain marked skipped by the repository.

- [ ] [Kafelki map bitewnych — po bohaterach na arenie, 2026-09-08]
  Wrócić do tematu dopiero po dopracowaniu bohaterów na arenie. Przygotować
  zestaw gotowych, pojedynczo rozkładanych kafelków terenu do druku i ponownego
  użycia (np. filar, osłona +2), każdy z czytelnymi właściwościami, premiami,
  karami lub ograniczeniami. Przy przyszłej aktualizacji istniejącej walki
  z Głodnymi Cieniami zastosować ten sam model składania mapy i setupu.
  Ustalenie zapisane w `PROJECT_CONTEXT.md`, sekcja „Plansza I Hardware”.
  Obecnie nie zmieniać tej walki ani jej wydruków w ramach tego zadania.

- [x] [Remaining panel delays, 2026-09-08] Remove movement searches used only
  to label the action menu; share action options between rune availability and
  color mapping, and reuse the freshly prepared scan target for its revision.
  Mark completed browser scans finished before rendering so a panel transition
  does not send a redundant serial reset. Reuse native accept/back controls
  instead of registering an equivalent browser panel. Local browser comparison:
  damage-to-ready 0.89→0.46 s, shield-selection-to-ready 1.73→0.61 s.
  Read-only WLED probes varied 0.16–0.73 s; physical latency remains distinct
  from the local simulator measurement. Log slow request durations, LED planning
  versus transport, and scan preparation/wait/post-input durations separately.

- [x] Misja 0: wspólny układ obraz po lewej / przewijany opis po prawej,
  stałe opcje dialogowe i +/− na planszy; po setupie wybór Nessy lub
  niedostępnej jeszcze areny przez pola kafli w siedzibie Gildii.
- [ ] Rozbudować siedzibę Gildii w centrum rozwoju i zadań: trening na arenie
  za zdobyte punkty, zbrojownia ze sprzedażą broni, handlarz przedmiotami
  oraz kolejne zlecenia. Na razie arena pokazuje wyłącznie informację.

- [x] Siedziba Gildii: wybór Nessy i areny wyłącznie przez pola planszy
  z figurką drużyny; usunięto powielające je przyciski i runy.

- [x] Misja 0 — kontrakt odbioru sprzętu, zapasów i dokumentów; drukowany rozkaz
  i pokwitowania, rozejm po pierwszym pokonanym, dwa przeszukania z ryzykiem
  uszkodzeń, pomoc wieśniaków, plotka, komplement Loriana i osobne losy dzwonu/długu.
- [x] Pierścień zamiast amuletu: identyfikacja Nimry lub Gildii, +1 do wartości
  Siły z wyposażenia, przekazanie/zdejmowanie, UI i zapis; odroczona nagroda
  pasera z jednorazowym punktem wejścia rozliczenia kampanii.
- [ ] Przy budowie Misji 2 podłączyć `campaign_rewards.complete_mission` na jej
  zakończeniu oraz narrację `misja_0_dzwon/mechanics/followups.json`; zachować
  flagi kampanii przy kontynuacji. W przyszłym mieście dodać adwokata i obsługę
  pokwitowań / poręczenia Garrana. Nie zdradzać terminu wypłaty w tekście gry.

- [x] Wspólny zapas Misji 0, przygotowanie bohaterów przed wyjściem i po powrocie,
  sloty i atomowa zamiana, lista −/+, zapis, blokada wyposażenia w terenie,
  mikstury z zapasu, płatna identyfikacja / próba Nimry przy odkryciu, sprzedaż
  z potwierdzeniem oraz ilustrowane karty startowego sprzętu i znalezisk.
- [x] Zachowanie wspólnego zapasu przy przekazaniu drużyny do kolejnego scenariusza.
- [ ] Rozszerzyć przygotowanie o zakupy, rozwój postaci i dobór zestawu akcji
  specjalnych. Ustalić liczbę slotów akcji i ograniczenia przed implementacją.

- [x] Karty ekwipunku: zastąpić schematyczne SVG pełnymi czarno-białymi
  ilustracjami tuszem w stylu kafli mapy; wspólne grafiki w UI i nowych PDF-ach.

- [x] Prototyp Garrana v2: cztery osobne arkusze A4 (historia/statystyki,
  pełne miejsca 63 × 88 mm na manę, dziewięć akcji z runami, pusta mata
  wyposażenia), żetony sprzętu 60 × 42 mm i wspólna jednostronicowa ściągawka.
  Generator `scripts/build_garran_set_concept.py`; PDF-y i podglądy
  `content/print/prototypes/garran_set_v2/`. Sprawdzić fizyczny wydruk przed
  przeniesieniem układu na wszystkie postaci i zastąpieniem oficjalnych paczek.
- [x] Prototyp maty many Garrana: wyraźnie oddzielić walkę i eksplorację,
  wyrównać bloki między kolorami oraz odróżnić ich nagłówki w druku czarno-białym.
- [x] Prototyp karty Garrana: najpierw kontekst rozmowy / interakcji z obiektem,
  następnie nazwa podejścia i mechanika; jawnie oznaczyć pole na notatki gracza.
- [x] Nazwy efektów konfrontacji: „wpływ” dla NPC, „postęp” dla obiektów;
  kontekstowe instrukcje, rzuty, podsumowania i pasywy w UI oraz wydrukach.
- [x] Przenieść zatwierdzony układ Garrana na siedem postaci: cztery maty
  i startowy sprzęt każdej postaci, wspólne dodatki na końcu jednego PDF-u.
  Osobne obwódki kumulacji dla walki/eksploracji; 12 akcji Nimry na jednym A4.
  Generator `scripts/build_hero_mats.py`, materiały w `content/print/characters/mats_v2/`.

- [x] [Redakcja kompletu postaci, 2026-09-18] Naturalne opisy akcji, pasywów i
  wyposażenia; słownik pogrubianych terminów mechanicznych. „Przybory magiczne /
  instrument” zastępują „ognisko”. Pomocnik z przykładami walki, rozmów i obiektów
  na końcu zbiorczego PDF-u; edytowalne copy.json, keywords.json i player_aid.json.
  Weryfikacja: 50 testów (język wydruków, karty many, ekwipunek, grafiki),
  41 arkuszy bez przepełnień; sprawdzono kolejność pomocnika i wynikowy PDF.

- [ ] [Po ukończeniu pierwszej kampanii — wersja online] Udostępnić jedną
  stronę gry z logowaniem, indywidualnymi zapisami kampanii i automatycznym
  zapisem postępu. Przepływ: zaloguj się → nowa kampania / kontynuuj → połącz
  planszę → graj przez dotychczasowy interfejs. Zachowywać drużynę, ekwipunek,
  decyzje fabularne i aktualny etap; oddzielić stan, zapisy i plansze różnych
  użytkowników, umożliwiając równoczesne niezależne rozgrywki.
  Docelowo podłączanie planszy ze strony bez instalowania programu: najpierw
  sprawdzić Web Serial dla przycisków USB oraz dostęp przeglądarki do LED-ów
  WLED. Zweryfikować zgodność przeglądarek, parowanie planszy z sesją oraz
  wznowienie po utracie połączenia bez powtarzania akcji. Jeśli potrzebny
  będzie lokalny program pośredniczący, omówić ten kompromis przed wdrożeniem.
  Po próbie jednej zdalnej rozgrywki wykonać test wielu stołów i dobrać hosting,
  trwałe zapisy oraz kopie zapasowe. Wstępny budżet infrastruktury: 600–1000 zł
  rocznie dla małej wersji publicznej; ponownie sprawdzić ceny i obciążenie
  przed zakupem. Zadanie odłożone do zakończenia pierwszej kampanii.

## Misja 0 — audyt rozgrywki przez UI (2026-09-18)

Raport i dowody: `docs/playtests/2026-09-18-misja0/REPORT.md`.

- [x] Przejść Misję 0 przez UI drużynami 3, 4, 5 i 6 osób z symulowaną
  fizyczną talią/kośćmi, realnym WLED, zapisem wyników i raportem.

- [x] Ujednolicić instrukcje wyboru działań w walce: runy faktycznie działają,
  choć tekst mówi o wyłączonym pasku; główne ikony ekranowe nie są przyciskami.
- [x] Usunąć fałszywe „Brak dostępnych pól ruchu” przy niepustej liście pól.
- [x] Zastąpić stare przypomnienia „Wydaj: czerwona” aktualnymi progami
  naładowania/spalaniem we wszystkich wariantach UI walki.
- [x] Ujednolicić statystyki Brakki z wydrukiem: zapisany bohater ma 32 PW,
  SIŁ 19/KON 15; generator mat 35 PW, SIŁ 18/KON 16. Pozostałe sześć
  wartości PW było zgodnych.
- [x] Generować współrzędne wozu w narracji drogi z geometrii kafla;
  obecny tekst nadal podaje położenie sprzed obrotu.
- [x] Naprawić problem ✓ podczas inicjatywy Misji 0: panel był ograniczony
  do scenariusza areny. Profil fizycznej many korzysta teraz z tego samego
  panelu. Chrome: +/−, podsumowanie i ✓ trzech bohaterów przez endpoint planszy.
- [ ] W teście przy stole potwierdzić inicjatywę fizycznymi przyciskami;
  regresja automatyczna wysyła wskazania pól i nie naciska sprzętu.
- [x] Ukryć znaczniki techniczne stanów („Rodzaj rozpoczętej serii: 0”,
  „Ofensywa w tej turze”, „Czas Rage”) i skrócić powtarzane akapity pasywów.
- [ ] Rozważyć opcjonalną lekcję pełnego naładowania i draina dla drużyn,
  które przyjmują rozejm i kończą walkę przed poznaniem tych mechanik.
- [ ] Podczas testów przy stole zmierzyć obciążenie zgłaszaniem spalanych
  kart oraz czterema pełnymi konfrontacjami w jednej misji wprowadzającej.
- [x] Naprawić nominały przy nagrodach/opłatach Misji 0: zapis wartości jako
  `CurrencyWallet(cp=total_cp)` zamienia np. 44 sz na 4400 miedziaków i 88 lb.
  Zachować poprawną wartość bez sztucznego zwiększania masy waluty/udźwigu.
- [ ] Zweryfikować sens odmowy rozejmu: w próbie brak dodatkowego XP lub
  nagrody, za to dłuższa walka, rany, płatna plotka i brak pomocy. Świadomie
  zaakceptować przewagę rozejmu albo nadać drugiej ścieżce odrębną korzyść.

- [x] Naprawić identyfikację Nimry w terenie: udany test wywołuje
  `identify_paid()` i zabiera 5 sz. Płatność dotyczy tylko Gildii; sukces
  Nimry powinien wywoływać bezpłatne `identify()`. Potwierdzone w P5.
- [x] W konfrontacji sześciu postaci odsłaniać kartę aktualnego aktora:
  Nimra zostaje w drugim rzędzie poza widokiem także w swojej turze
  (1131×720). Przypiąć podsumowanie lub przewijać do aktywnej karty.
- [x] Przy zakończeniu walki usuwać znaczniki `mana_series_source` oraz
  `shared_offensive_used`: w P3–P6 dotrwały do końcowego zapisu misji
  mimo czasu „do końca tury”.
- [x] Dopracować drobne komunikaty Misji 0: odmiana „1 pełną rundę”,
  „Zastosuj wynik encountera”, sprzeczny brak aktywnego aktora podczas
  tury wroga oraz wzmianki o Mirze/Nimrze przy nieobecności w drużynie.

Poprawki po audycie: patrz tabela statusów i weryfikacja w raporcie. Lokalny
rekord startowy Brakki dostosowano do kanonicznego zestawu (35 PW, SIŁ 18,
KON 16); wcześniejsze snapshoty i historyczne wyniki audytu pozostają bez zmian.

## Eksploracja — kumulowana pomoc (19.09.2026)

- [x] Test i pomoc spalają po 1 karcie z wierzchu wspólnej talii; UI pokazuje
  jeden test z najwyższą dostępną premią naładowania.
- [x] Pomoc daje +1, ze Współpracą +2. Kolejne pomoce sumują się bez limitu;
  cała suma znika po pierwszej próbie k20 odbiorcy, także nieudanej.
  Dobór, kolejna runda i pomaganie innym nie zużywają premii.
- [x] Zachować zgłaszanie spalonej karty przez runy, blokadę następnej tury
  do zakończenia płatności i zakończenie konfrontacji przy braku karty.
- [x] Zaktualizować opisy UI, lekcje pomocy/naładowania, pasywy wszystkich
  siedmiu bohaterów i zbiorczy PDF (41 stron, walidacja bez przepełnień).
- [x] Regresje: kumulacja do +3, zużycie przy sukcesie i porażce, NPC/obiekt,
  zapis podczas próby, Współpraca oraz fizyczny koszt. Chrome: runy pomocy
  na ekranach 1300×657 i 390×800 oraz przebieg sześciu bohaterów.
- [ ] Ocenić przy stole balans płatnej, kumulowanej pomocy; poprzedni raport
  symulacyjny dotyczy wcześniejszego modelu kosztów.

## Podejścia zależne od sceny i graf pomocy (19.09.2026)

- [x] Zastąpić stałe metody bohaterów opcjami NPC/obiektu: nazwa, opis,
  cecha, ST, kość wpływu/postępu i skierowane powiązania `supports`.
- [x] Wybór każdego uczestnika runą przed talią, w kolejności tur; wspólne
  podejścia dozwolone, przydział trwa do końca konfrontacji. Bez symetrii cech.
- [x] Nessa: komplementy, żądania, argumenty, blef, zrozumienie obaw.
  Osobno dopasować wóz, zbrojownię, kwaterę i schowek treningowy.
- [x] Pokazać skierowane powiązania podczas wyboru; pomoc tylko wskazanym
  podejściom. `*` pozwala wybrać dowolnego sojusznika, jedna osoba na akcję.
- [x] Dodać alternatywę za całe działanie: podgląd dolnej karty, zgłoszenie
  koloru i pozostawienie na spodzie/przeniesienie na wierzch, bez spalania.
  Pusta talia: czekanie. Reakcje po rundzie nadal obowiązują.
- [x] Zachować kolejność/kolory w zapisie, odrzucać nielegalne powiązania
  i przekroczenie liczby kart. Nie resetować konfrontacji rozpoczętej wcześniej.
- [x] Zaktualizować lekcje, opisy, karty siedmiu bohaterów i wspólny pomocnik
  (41 stron); skrypty ewaluacji wybierają podejścia przed talią.
- [x] Testy wyboru, grafu, zużycia akcji, kart, zapisu i run w Chrome;
  testowa symulacja pełnych konfrontacji (`--trials 1`, 84 przebiegi, wynik w /tmp).
- [ ] Przy stole ocenić balans podejść i decyzji podgląd/test/wsparcie.
  Szybki przebieg skryptu nie ocenia optymalnej współpracy ani balansu scen.

- [x] Wybór podejść: przypisać opcje do run od pola 6 zamiast akcji
  podstawowych 0–5; umieścić wybór bezpośrednio w kafelkach z pełnymi opisami.
  Usunąć powtórzony pasek wyborów, zastąpić duże panele uczestników zwięzłym
  podsumowaniem przydziału. Chrome: wszystkie pięć opcji bez przewijania
  na 1300×657 i 1131×720; mały ekran zachowuje dostęp przez przewijanie.
  Test adaptera potwierdza, że podstawowe pola nie są celami wyboru podejść.


- [x] Konfrontacje: wyłączne podejścia na bohatera, niezmienne runy po zajęciu opcji, sześć logicznych podejść w scenach Misji 0 i treningu. Portret wybierającego, oddzielenie nagłówka i wsparcie z runami w kółkach; aktualizacja pomocnika. Starsze przydziały przed doborem zachowują poprawny początek; rozpoczęta rozgrywka zachowuje stan.

- [x] Podejścia mieszane: `repeatable` w katalogach NPC i obiektów, blokowanie tylko wyłącznych opcji, oznaczenia na kafelkach i zgodność zapisów. Sceny z opcją powtarzalną nie wymagają sześciu różnych podejść. Pomocnik i oznaczenia UI opisują oba warianty; testy obejmują sześć postaci i zachowanie run po ponownym wyborze.

- [x] Wóz: osobny zwięzły opis konfrontacji bez powtórzenia setupu drogi; sprawdzenie mieszanego przydziału, run, starszego zapisu i widoku jak u Nessy.

- [x] Odświeżyć wszystkie zestawy postaci po zmianie podejść: wspólny blok eksploracji, trzy działania, modyfikator cechy zamiast nieprecyzyjnej „cechy”, wsparcie i powtarzalność w pomocniku. Komplet PDF: 41 stron bez przepełnień, rozmiary fizycznych kart zachowane; 38 testów opisów i danych wydruku przeszło.

- [x] Podgląd w konfrontacjach bez zgłaszania koloru: tylko zostawienie/przełożenie, zachowanie znanej kolejności i migracja trwającego podglądu; odświeżone samouczek, karty i PDF. Testy reguł, zapisu, run i przeglądarki przeszły.

- [x] Usunąć blok eksploracji z kart wszystkich postaci; pod portretem i historią umieścić skazę oraz aktualne zobowiązania z kropkowanymi liniami. Wspólny pomocnik zachowany; PDF 41 stron, kontrola układu bez przepełnień.

- [x] Postawa drużyny: siedmiopolowy wskaźnik, skład talii z wyłączonymi kartami, zapis kampanii; wymuszona zamiana wozu oraz przyjęcie/odmowa rozejmu w Misji 0. UI i instrukcje podają aktualny skład; pomocnik w PDF (41 stron bez przepełnień). Testy reguł, zapisów, scenariusza, run i Chrome (3/6 postaci oraz widoki Nessy i wozu).
- [ ] Ograć wpływ postawy na balans: po 1 karcie z dwóch kolorów na krok (maks. 6 wyłączonych), szczególnie dla drużyn 3 i 6 osób; sprawdzić długość konfrontacji i dostęp do pasywów.

- [x] Konfrontacje: większy portret wybierającego obok podejść, usunięcie ogólnego zdania o wsparciu, cofanie pomyłek podejścia/koloru/doboru przez runę Fala z zachowaniem talii i zapisu. Granice korekt przed rzutem/działaniem; 4 testy cofania i 6 prób Chrome (Nessa/wóz, trzy rozmiary ekranu) przeszły.

- [x] Konfrontacje — poprawki po sesji 19.09: Oddech wymaga przełożenia najstarszej spalonej karty i potwierdzenia ✓ przed kosztem testu; kompromis zatrzymuje postęp na osobnym wyborze przyjęcia/odrzucenia po rozliczeniu akcji. Zapis zachowuje oczekujące potwierdzenie; logi pokazują zmiany kart i decyzję. Regresje reguł/run/zapisu oraz Chrome na 1300×657 i 390×800; skrypty symulacji obsługują nowy krok.

- [x] Czytelne pasywy many wszystkich siedmiu postaci: wspólne dane opisu dla UI i mat (warunek, efekt, szczegóły, kumulacja, krótki tekst do druku). Schemat jednej karty ze spalonych na spód talii przy Oddechu, pogrubione wartości w UI, wyraźne rozróżnienie leczenia przy doborze i stałych premii. Nowe opisy także w wyborze many podczas walki i w pomocniku. Testy opisów, UI rozmowy/walki i potwierdzenia Dagny w Chrome; walidacja A4 i rozmiarów kart.


## Unikalne pasywy many — 2026-09-20

- [x] Wdrożono indywidualne zestawy pasywów walki i eksploracji dla siedmiu bohaterów. Katalogi są wspólnym źródłem dla zasad, UI i drukowanych mat; pełna rozpiska: [docs/DISTINCT_MANA_PASSIVES.md](docs/DISTINCT_MANA_PASSIVES.md).
- [ ] Po ręcznym ograniu ocenić siłę nowych kombinacji pasywów, szczególnie odzysk i darmową pomoc Loriana oraz wsparcie po porażkach Garrana. Punkt odniesienia: `docs/reports/DISTINCT_PASSIVES_SMOKE.md`.

- [x] Autozapis Misji 0 po etapach, rozstrzygnięciach konfrontacji, nagrodach, wozie, walce i przygotowaniu; oddzielny od startowych checkpointów. Usunąć ręczne zapisy z widoku misji, zachować wczytywanie; regresje pełnego odtworzenia skutków i UI.

- [x] Usunąć nieużywane kopie pasywów walki i eksploracji z `mats_v2/copy.json`; wskazać w instrukcji edycji aktywne katalogi i pola `display`.

- [x] Wspólne źródło treści `content/scenarios/misja_0_dzwon/text/karty_postaci.json`: historie, skazy, akcje i podbicia, 70 pasywów, samouczek i pomocnik. Gra i druk czytają ten sam plik; usunięto poprzednie kopie. Testy edycji i odświeżania bez restartu.
- [ ] Dostosować stare `test_garran_mana_movement.py` (13 wariantów oczekujących płatnego ruchu) i `test_hero_rules_consistency.py` (7 oczekiwań profilu `shared_mana_v03`) do obecnego systemu. Szczegóły: `docs/reports/CHARACTER_TEXT_SOURCE.md`.

## Runy — techniczny prototyp 22.09.2026

- [x] Osobna paczka `print/runy_v01`: plansza z czterema akcjami podstawowymi,
  dwiema przerwami, 20 runami i przyciskami +/−/✓/↩. Plansza oraz wszystkie
  18 kafli Misji 0 powiększone o 3% względem poprzedniej korekty drukarki.
- [x] Siedem modułowych zestawów: postać i zobowiązania, mata 12 zdolności,
  mata wyposażenia, dwa arkusze wycinanek. Wspólny PDF ma 35 stron.
  Garran: robocze moce; pozostali: nazwane szablony bez kosztów starej many.
- [x] Makieta UI: nowy panel i podświetlenia, dobór N+2, podział run,
  ręka do 7, koszt po zatwierdzeniu, dopłata do mocy, utrzymanie aury,
  jedna runda konfrontacji. Darmowy atak okazyjny i wybór reakcji.
- [x] Kontrola układu i wymiarów wszystkich mat/wycinanek w Chrome;
  testy geometrii planszy, spójności danych oraz klikania przepływów.
- [x] Dostosować karty pozostałych sześciu bohaterów do run i wspólnego źródła
  kosztów używanego przez silnik oraz generator wydruków.
- [ ] Ograć skazy, balans talii i dalsze koszty moralnych decyzji.
- [x] Wdrożyć mapowanie panelu i zasady zaakceptowanej makiety do aplikacji;
  szczegóły i pozostała kontrola fizyczna poniżej.
- [x] Naprawić sterowanie walką zgłoszone po teście manualnym: legalność świateł
  i zatwierdzania, wybór pól i anulowanie, sprawdzone przez symulowany skaner.

## Reputacja w makiecie — 22.09.2026

- [x] Gwiazda: niebieski skrót informacji o aktywnym bohaterze i drobna legenda.
  Bieżące PW, KP, statusy/efekty/aura, budżet tury, runy, cechy, sprzęt i historia.
  Powrót zachowuje podgląd akcji i cel. Bastion oraz jego koszt przeniesione na
  Klucz; odświeżone źródło i PDF kart. Regresje UI oraz spójności druku.
- [x] Cele ataków/mocy: informacyjna lista bez przycisków i przypisań run.
  Wybór sygnałem pola figurki, wyróżnienie wybranego celu i aktywacja ✓.
  Regresje Chrome: klik listy nic nie wybiera, pola nielegalne odrzucane,
  wybór legalny bez kosztu, zmiana celu oraz ignorowanie zdarzeń poza podglądem.
- [x] Sekwencyjny przydział run: jedno kliknięcie przenosi jedną sztukę
  do bieżącej postaci; ostatnia kopia wygasza pole. ↩ cofa wybory w odwrotnej
  kolejności, ✓ zatwierdza i przechodzi do następnego bohatera. Bez przełączania
  odbiorcy przez +/−. Limit 7, pusta pula i kolejny obieg reszty sprawdzone w Chrome.
- [x] Przedmiot: automatycznie wybrać jedyną dostępną miksturę w podglądzie,
  od razu aktywować ekranowe zatwierdzenie i podświetlić ✓ na panelu planszy.
  Efekt dopiero po potwierdzeniu; regresja anulowania i ponownego ✓.
- [x] Ruch: usunąć ekranowe kafelki odległości. Pozostawić limit pól,
  instrukcję wyboru podświetlonego pola fizycznej planszy i potwierdzenie.
  Regresja: brak przypisań odległości do run, wybór pola bez kosztu,
  odrzucanie błędnego dystansu, rozliczenie dopiero po ✓.
- [x] Walka: usunąć katalog akcji z ekranu oczekiwania. „Wybierz akcję” →
  pole planszy → opis i dystans/cele/obszar aury → wybór → ✓ wykonuje.
  Ruch i przedmiot również wymagają potwierdzenia; anulowanie bez kosztu.
  Testy Chrome: brak katalogu, zachowane przypisania, legalne cele, promień
  aury i jego wzmocnienie, brak skutków przed potwierdzeniem.
- [x] Korekta doboru: tylko początek pierwszej rundy walki; ilustracja i opis
  posterunku zamiast Nessy. Przejście od wozu otwiera dobór. Kolejne rundy
  zachowują ręce bez losowania; utrzymanie aury nadal działa. Regresja Chrome.
- [x] Zastąpić dobór i wsparcie runami w rozmowach wspólną reputacją od 20.
  Podejście otwiera rzut; podsumowanie oferuje trzy wyłączne opcje pod runami:
  +1 za 1, +5 za 3, dodatkowa k20 i wyższy wynik za 5. Bez kupowania premii +/−.
- [x] Koszt po potwierdzeniu; dodatkowa kość opłacana przed rzutem, bez zwrotu
  po poznaniu wyniku. Saldo wspólne, bez odnowienia przy zmianie sceny.
- [x] Zamiana wozu: bieżąca reputacja ≥20, koszt 3, wybór i potwierdzenie.
  Przykład jednorazowej nagrody misji +5; wartość nagrody robocza.
- [x] Testy Chrome: trzy opcje, brak kumulacji, koszty, krytyki, dodatkowa kość,
  próg wozu, zachowanie salda i brak ponownego przyznania nagrody.
- [ ] Uzgodnić nagrody i koszty decyzji, wpływ reputacji na ceny i progi dialogów;
  reputacja jest już zapisywana w kampanii. Zasady:
  [docs/REPUTATION_PROTOTYPE.md](docs/REPUTATION_PROTOTYPE.md).

## Wdrożenie run i reputacji — 22.09.2026

- [x] Reputacja kampanii od 20: trzy rozłączne premie po rzucie, zapis opłaconej
  dodatkowej kości, próg 20 i koszt 3 za zamianę wozu, jednorazowa nagroda misji.
- [x] Nowe konfrontacje Nessy i wozu: jedna kolejka, test bez wpływu, postęp
  skalowany liczbą bohaterów i natychmiastowe zakończenie na skrajnych wynikach.
- [x] Produkcyjny panel zgodny z wydrukiem: cztery akcje podstawowe, runy od 5,
  Gwiazda informacyjna 24, +26/−27; aktualizacja launchera i adapterów.
- [x] Naprawa sterowania zgłoszonego po teście manualnym: brak legalnego celu
  wygasza atak; ruch i cel muszą być wybrane przed ✓. Podgląd Gwiazdy zachowuje
  akcję i cel. Dwa testy Chrome używają automatycznego skanera przez całą turę.
- [x] Przydział run kliknięciami po jednej sztuce, cofanie bieżących wyborów,
  limit 7 i zapis skończonej talii. Dobór N+2 tylko na początku walki.
- [x] Zasłona dymna Miry: stacjonarny obszar 3×3 i przewaga do osobnego
  Ukrycia, bez darmowego ruchu i automatycznego ukrywania. Roboczy czas:
  do końca następnej tury Miry, żeby mogła wykorzystać swoją kolejną specjalną.
- [x] Strojenie Loriana wymaga runy pozostałej po pełnej zapłacie, także
  zastępczej. Podgląd wskazuje runę wymienianą z ręki.
- [x] Audyt wszystkich 66 kart siedmiu bohaterów: pokrywanie się efektów,
  koszty S/A/M/R i wzmocnień, ekonomia N+2 tylko raz na walkę oraz czytelność
  symbolu przycisku i kosztu. Ustalenia i propozycje bez samowolnej zmiany
  balansu: [docs/HERO_ACTION_REVIEW.md](docs/HERO_ACTION_REVIEW.md).
- [x] Jawny wybór dowolnych run przy dopłacie, zastępczym koszcie,
  podtrzymaniu Bastionu i Kontrataku. Rezerwacja wymaganych symboli, wybór
  po jednej kopii, cofanie i zatwierdzenie przed pobraniem kosztu. Strojenie
  i Odzysk Loriana pozwalają wybrać konkretne wymieniane/odzyskiwane runy.
- [x] Wdrożyć zaakceptowane korekty audytu: stacjonarny Bastion z pierwszą
  kolejną turą bez podtrzymania, pierwszy Szał bez runy, Zwód osłaniający
  sojuszników, bezpieczny Święty płomień i Zachowanie życia raz na walkę.
  Połączyć odzyski Loriana w jedną kartę raz na walkę bez odzysku kosztu;
  poprawić budżety Lunety i Podwójnego strzału; odróżnić Załamanie woli
  utrudnieniem kolejnej obrony MDR. Zachować N+2 tylko na początku walki.
  Szczegóły: [docs/RUNE_BALANCE_V02.md](docs/RUNE_BALANCE_V02.md).
- [x] Doprecyzować na kartach czas Inspiracji i obniżenia KP Strzały
  odsłaniającej; zastąpić dawne skróty T/O jawnymi granicami efektów.
  Opisać podstawowy koszt i dopłaty wzmocnień. Zregenerować komplet 65 kart
  siedmiu postaci (35 stron A4) oraz dane klikalnej makiety.
- [ ] Po wdrożeniu fizycznie sprawdzić wydruk powiększony o 3% względem czujników
  i rozegrać Misję 0 na urządzeniu. Testy symulatora nie potwierdzają tej geometrii.
- [ ] Ograć balans kart siedmiu bohaterów oraz nagrodę reputacji +5; określić
  konkretne rabaty sklepowe i dalsze progi dialogów.

Aktualne zasady aplikacji: [docs/RUNES_RUNTIME.md](docs/RUNES_RUNTIME.md).
Historyczne wpisy o osobistych pulach many dotyczą poprzedniego wariantu.

- [x] Ścisnąć wybór podejścia w konfrontacji: mniejsze odstępy, reputacja
  przy bohaterze, „Pas” w dolnym pasku. Sześć pełnych opisów bez przewijania
  na ekranach 1285×632, 1131×632 i 1285×600. Kontrola geometrii i pełnego
  przebiegu konfrontacji w Chrome na tymczasowej sesji z symulatorem planszy.
- [x] Przydział run: portret obok nagłówka pokazuje bieżącego odbiorcę run
  i zmienia się po zatwierdzeniu przydziału. Sprawdzone w Chrome dla każdego
  odbiorcy podczas pełnego testu przydziału i tury sterowanej planszą.
- [x] Tura przeciwnika: podświetlać i skanować ✓ na początku, przy zamiarze
  i potwierdzeniu wyniku. Zachować pierwszeństwo reakcji, rzutów i fizycznych
  pól docelowych. Regresja odtworzyła brak ✓; testy maski i LED oraz Chrome
  potwierdziły przejście bohater → przeciwnik i uruchomienie akcji planszą.

- [x] Ujednolicić podstawowe koszty wszystkich 65 mocy z symbolami ich
  przycisków: poprawione 26 kart, m.in. Z bara = 1 × Trójząb. Pierwszy
  Szał pozostaje bez run, kolejne użycia za Rozwidlenie; Duchowa broń
  i jej ponowne aktywacje za Schody. Talia nowych walk zawiera 16 używanych
  symboli. Wersjonowanie zachowuje pulę i kolejność kart rozpoczętych walk.
  Wspólna lista zasobów dla aplikacji, wydruków i makiety; przydział i LED
  wyliczają pola po nazwach run. Generator odrzuca rozbieżność koszt/przycisk.
  Zregenerowane siedem kompletów i zbiorczy PDF (35 stron A4).
  Weryfikacja: 72 testy zasobów, płatności, efektów, kart i planszy, w tym
  Chrome dla działającej walki oraz makiety. Odczyt dotychczasowego checkpointu
  walki przeszedł bez modyfikowania zapisu.

- [x] Podstawowy ekwipunek nowych postaci runicznych i wydruków: jedna
  wyposażona broń, dotychczasowy pancerz/tarcza oraz osobiste przedmioty;
  usunąć zapasowe bronie i zbędną amunicję, zachować KP i brak zbroi
  Brakki/Nimry. Wspólny profil dla gry, mat, wycinanek i danych makiety.
- [x] Mistrzyni ostrzy: wyposażona broń, wymagane Ukrycie przed konkretnym
  celem, +1k6 oraz dodatkowe +1k6 z własnej flanki. Nie sumować ponownie
  tych premii z Atakiem z cienia; zachować kość flanki do rozliczenia
  obrażeń po ujawnieniu. Legalne pola wykluczają widzących Mirę wrogów.
- [x] Rozwidlenie w trybie Ukrycia otwiera darmowe wyjście z niego:
  ✓ ujawnia, ↩ anuluje, bez zwrotu ani pobrania akcji/run. Zachować
  potwierdzony przez użytkownika wyjątek Ukrycia na otwartym polu.
  Weryfikacja: testy wyposażenia siedmiu bohaterów, pełny atak Miry
  z flanką i bez niej, rozliczenie kości po ujawnieniu, brak podwójnej
  premii, płatności i darmowe wyjście z Ukrycia. Regresje starszych
  technik Miry, flankowania i dymu przeszły. Chrome sprawdził legalne
  cele i podświetlenia, anulowanie oraz zatwierdzenie Rozwidlenia.
  Zregenerowano 35 stron kart; generator sprawdził przepełnienia.

- [x] Ponowny audyt siedmiu bohaterów po przejściu na runy: wspólny katalog
  skaz dla UI i PDF, dopłaty wybieranymi runami dla Dagny/Loriana/Nimry/Erynda,
  Echo z limitem +2 i zapisem serii, dopłata także przy drugim strzale Erynda.
  Usunięte wycofane cechy i Metamagia, poprawiony alias Zachowania życia oraz
  pierwszeństwo aktualnych opisów. Wczytanie odświeża wyłącznie cechy;
  nie resetuje PW, ekwipunku ani puli. Zregenerowane 35 stron kart.
  Szczegóły: [docs/RUNE_HERO_AUDIT.md](docs/RUNE_HERO_AUDIT.md).


- [x] [Panel: rezygnacja z opcjonalnej reakcji, 2026-09-23] Na pierwszej
  kości Cutting Words lub Rozpraszającego okrzyku podświetlić ↩ i pokazać
  „Pomiń reakcję”. Przycisk pomija nieopłaconą ofertę bez wydania run;
  obowiązkowe i opłacone rzuty pozostają do rozliczenia. W podsumowaniu
  ↩ oraz awaryjny Escape wracają do poprawy wyniku, zamiast pomijać reakcję.
  Rozszerzyć test Chrome o Ruch → Atak → Wróć bez kosztu oraz pełną turę
  przeciwnika: pominięcie reakcji, automatyczny rzut, jedno okno wyniku,
  potwierdzenie bez ponownego losowania i powrót do następnego bohatera.
  Weryfikacja używa symulatora wejścia; test fizycznych sensorów pozostaje osobny.

- [x] [Koszyki run w grze, 23.09.2026] Wspólny katalog 65 mocy i pojemności
  siedmiu bohaterów; koszt zgodny z kategorią przycisku, opcjonalny konkretny
  Rezonans, wybór pomocnika do 3 pól i atomowe rozliczenie żetonu oraz reakcji.
  Przygotowanie kategoriami przez planszę, powtórzenia symboli, cofanie,
  podsumowanie i kontrola nieaktualnych komend. Skupienie, ładowanie k4,
  zgłaszanie warunków odnowienia oraz limit raz na rundę. Reakcje po rundzie.
  Pierwsza strona kart: żetony zamiast notatek; pełny komplet A4 i nowe odsyłacze
  z aplikacji. Starsze zapisy zachowują dawny model.
  Weryfikacja: 60 ukierunkowanych testów (reguły, zapis, plansza, Chrome,
  druk i regresje Garrana), walidacja 42 stron A4 oraz `git diff --check`.
- [ ] Osobno przepisać prowadzony samouczek dawnej many na scenariusze ćwiczeń
  koszyków; swobodna arena już używa nowego modelu. Zdarzenia odnowienia są
  obecnie zgłaszane Mostem, z walidacją limitu i pojemności; ewentualną pełną
  automatyzację wyzwalaczy rozpatrzyć po testach balansu.
- [x] [Spis wydruków, 23.09.2026] Zaktualizować `runy_v01/index.html`
  i spis koszyków: odsyłacze do bieżących 42 stron, siedem zestawów,
  pojemności z katalogu i instrukcja obsługi przez planszę. Zachować dostęp
  do mapy i kafli. Oba generatory korzystają ze wspólnego spisu, żeby
  ponowny eksport nie przywracał starych kart ani opisów.

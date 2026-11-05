# Plan: plansza LED i sterowanie klawiaturą

Status: **do akceptacji; implementacja nierozpoczęta**. Data: 05.11.2026.
Branch: `feat/led-keyboard-control`.

## Cel i zakres

Przygotować osobny, opcjonalny profil **klawiatura + LED**, w którym fizyczna
plansza wyświetla informacje, a wszystkie decyzje gracza można przekazać z
klawiatury komputera. Czujniki pól, przyciski runiczne i skaner kart nie są
wymagane. Figurki, kafle, karty i fizyczne rzuty pozostają częścią gry.
Późniejsze podłączenie pada ma wymagać adaptera wejścia, bez przebudowy gameplayu.

Zakres pierwszego wdrożenia: menu startowe, wybór i przygotowanie drużyny,
Misja 0, swobodna arena, rozstawianie planszy i figurek, inicjatywa,
eksploracja, konfrontacje, aktualna walka `rune_relations_v03`, ekwipunek,
runy, rzuty, reakcje, dziennik, ściąga oraz zapis/wczytanie. Wspólne elementy
pozostałych scenariuszy korzystają z tej samej obsługi; starsze profile walki
zachowują dotychczasowe działanie i wymagają regresji tam, gdzie dotykamy
wspólnego kodu. Nie przebudowujemy wszystkich historycznych interfejsów.

Na tym branchu na razie zapisujemy plan i TODO. Zmiany runtime oraz testy
implementacji powstaną dopiero po akceptacji planu.

## Co już istnieje

- `ui/combat_keyboard.py` i `ui/static/exploration.js` obsługują część
  starszych skrótów, zatwierdzanie, cofanie i wprowadzanie rzutów.
- Obecna walka działa przez `ui/resonance.py` i `static/resonance_combat.js`.
  Ma komendy `choose`, `select`, `accept`, `back` i kontrolę rewizji.
  Enter/Escape/+/− są częściowo przekazywane przez wspólny panel, ale brakuje
  kursora pól i kompletnej nawigacji run/akcji klawiaturą.
- Podgląd ruchu i wybór celu są już oddzielone od wykonania akcji.
  Istnieją niebieski zasięg, żółta trasa, zielony cel oraz czerwone
  niedostępne cele z przyczyną odmowy.
- Backend `hardware` tworzy połączenie USB przed uruchomieniem WLED.
  `none` wyłącza również LED-y. Obecnie nie ma profilu samych LED-ów.
- Automatyczny skan jest powiązany ze statusem połączenia planszy, także
  w launcherze. Reset i wczytywanie uwzględniają konkretne nazwy backendów.
- Kolumna `col=19` jest panelem funkcyjnym. Zachowujemy jej rezerwację
  i istniejące wymiary map; usunięcie czujników nie poszerza pola gry.
- `actions/player_input.py` obsługuje deklaracje tekstowe typu `/pytaj`.
  Nie jest routerem klawiatury do tego zadania.

## Warstwa 1: core — kontrakt wejścia i logika sesji

„Core” oznacza tu wspólną obsługę decyzji na granicy UI i aplikacji.
Reguły domenowe pozostają w obecnych modułach.

Plan zmian:

1. Wprowadzić mały kontrakt poleceń niezależny od urządzenia: nawigacja,
   wskazanie pola, wybór opcji po stabilnym ID, zatwierdzenie, cofnięcie,
   otwarcie panelu informacji i zmiana wartości kości. Klawiatura mapuje
   klawisze na te polecenia; przyszły pad będzie drugim adapterem.
   Dispatcher wykorzystuje istniejące komendy poszczególnych przepływów.
2. Opisywać bieżący kontekst wejścia: menu/lista, pole mapy, wybór celu,
   kość, informacyjny panel albo blokująca decyzja/reakcja. Udostępniać
   stabilne ID, podpisy, dostępność, powody odmowy i rewizję. Oddzielić
   pola mapy od współrzędnych run panelu.
3. Dodać przejściowy stan kursora i zaznaczenia, oddzielny od pozycji aktora.
   Serwer pozostaje źródłem legalności, trasy, kosztu i efektów.
   Nawigacja nie losuje kości, nie przesuwa aktora ani nie wydaje zasobów.
4. Dodać jawny podgląd kursora. **Nie wysyłać każdej strzałki jako
   `/api/board/select`**: obecny handler może od razu otworzyć scenę,
   wybrać uczestnika albo uruchomić polecenie panelu. W ruchu i celowaniu
   używać istniejących bezkosztowych podglądów; w pozostałych kontekstach
   kursor jedynie wyróżnia opcję do późniejszego wybrania Enterem.
5. Wymagać aktualnego kontekstu i rewizji przy poleceniach. Zmiana ekranu,
   tury, etapu wyboru lub wczytanie usuwa zaległe wejścia. Zatwierdzanie
   ma dotyczyć ostatniego potwierdzonego przez serwer wskazania; błędny
   lub jeszcze niesynchronizowany kursor nie może wykonać poprzedniego celu.
6. Stan nawigacji trzymać w sesji/prezentacji, bez globalnego stanu gry.
   Nie dodawać go do zapisu domenowego. Już zapisywane decyzje pozostają
   obsługiwane przez istniejący format; po wczytaniu odtwarzamy kontekst.

Przewidywane pliki: nowe `ui/input_commands.py` i `ui/keyboard_input.py`
(kontrakt i obsługa kontekstu), punktowe zmiany w `ui/session_state.py`,
`ui/session_view.py`, `ui/exploration_app.py`, `ui/routes.py`, `ui/resonance.py`.
Bez szerokiej ekstrakcji ani przebudowy dużego koordynatora sesji.

## Warstwa 2: hardware — WLED bez USB

1. Dodać do `board.Connection` backend wyjściowy, roboczo `wled`.
   Wykorzystuje istniejący klient WLED, mapowanie i kolejkę ramek.
   Nie otwiera ani nie wyszukuje portów USB, nie tworzy `SerialV2`.
   Nieznana nazwa backendu kończy się błędem walidacji, zamiast domyślnie
   uruchamiać sprzęt USB.
2. W adapterze rozdzielić możliwości wejścia i wyjścia, np.
   `can_scan` i `can_display_leds`, od diagnostyki dostępności WLED.
   Klawiatura nie wymaga stanu „czujniki połączone”.
3. Uzależnić `auto_arm`, ponawianie i anulowanie skanów od `can_scan`
   w grze oraz launcherze. W profilu klawiatury nie tworzyć pozornych
   skanów ani heartbeatów USB. Zmiana kontekstu nadal unieważnia wejście.
4. Zachować obecne semantyczne ramki: aktywny aktor, zasięg, trasa, cel,
   obszary, reakcje, setup i wyniki. Kursor składa się z tymi warstwami.
   Wskazanie do podglądu nie włącza jasności przeznaczonej na fizyczny skan.
5. Zachować asynchroniczne wysyłanie i ponawianie najnowszej ramki.
   Awaria WLED nie uruchamia USB ani nie zmienia źródła wejścia.
   UI pokazuje osobno gotowość klawiatury i błąd świateł; po powrocie
   połączenia wysyłamy aktualny podgląd, bez odgrywania starych kroków.
   Także start z niedostępnym WLED zachowuje działający profil klawiatury.
6. Zachować profil przy restarcie sesji, wczytaniu i powrocie do menu.
   Wyjście z aplikacji korzysta z obecnego wygaszania i zamykania połączeń.

Przewidywane pliki: `board/connection.py`,
`src/dnd_board_game/hardware/board_session.py`, punktowo
`hardware/resonance_feedback.py`, `ui/exploration_app.py`,
`ui/launcher_board.py`. `board/settings.py` tylko jeśli konfiguracja tego wymaga.
W `board/` pozostaje wyłącznie komunikacja; nie trafiają tam decyzje gry.

## Warstwa 3: UI — klawiatura i widoczny podgląd

Proponowane przypisania obowiązują w nowym profilu. Jeden aktywny router
zastępuje nakładające się handlery tego profilu. Litery używane przez starsze
moce bohaterów nie są równocześnie globalnymi skrótami. Dotychczasowy profil
planszy zachowuje swoje przypisania.

| Klawisz | Działanie w aktualnym kontekście |
| --- | --- |
| Strzałki | Na mapie: przesunięcie kursora o pole. W menu: wybór opcji; w panelu: nawigacja. |
| Enter | Wybranie opcji albo istniejące zatwierdzenie aktualnego podglądu. |
| Esc | Cofnięcie dozwolonego kroku lub zamknięcie najwyższego panelu. |
| M | Otwórz ruch, jeżeli bieżąca decyzja go dopuszcza. |
| A | Otwórz podgląd zwykłego ataku. |
| I | Otwórz ekwipunek; samo otwarcie niczego nie zużywa. |
| R | Otwórz menu dostępnych run i mocy. |
| C / J / H | Informacje o postaci / dziennik / ściąga i skróty. |
| 0 | Otwórz istniejące potwierdzenie końca tury. |
| + / − | Zmień wynik kości; w obsługiwanym pickerze — wartość/opcję. |
| Tab / Shift+Tab | Standardowa nawigacja fokusem po kontrolkach. |

Ruch krok po kroku:

1. `M` otwiera obecny podgląd ruchu; kursor zaczyna na polu bohatera.
2. Strzałki przesuwają **cel podglądu**. LED-y pokazują istniejący zasięg,
   wyliczoną trasę i docelowe pole. UI podaje współrzędne i koszt.
3. Trasę liczy aktualny silnik od pozycji bohatera do celu; sekwencja
   strzałek nie staje się ręcznie wytyczoną trasą. Dotarcie kursorem
   do pola po skosie nadal pozwala wykorzystać legalną trasę diagonalną.
4. Kursor nie zawija na krawędziach i nie wchodzi w panel `col=19`.
   Kierunki odpowiadają orientacji rozłożonej planszy; ustalamy je jawnie
   przy próbie sprzętowej, bez zmiany modelu współrzędnych.
5. Niedostępny cel pokazuje odmowę i blokuje wykonanie. Nawigacja nie może
   utknąć dlatego, że sąsiednie pole jest przeszkodą: kursor jest wskazaniem,
   a legalność trasy nadal ocenia silnik.
6. `Enter` wykonuje zatwierdzony ruch. Gracz przestawia figurkę na wskazane
   pole; UI pokazuje nową pozycję i pozostały ruch. Zachowujemy obecne
   przerwania, ataki okazyjne i powrót do menu. `Esc` anuluje podgląd.

Pozostałe zmiany UI:

- Ataki i moce używają tego samego kursora dla pola celu/centrum obszaru.
  Wieloetapowe akcje prowadzą przez obecne kroki, np. wróg → miejsce
  lądowania albo obszar → postać wyłączona z efektu. Kursor resetuje się
  odpowiednio do nowego etapu; nie zatwierdza go automatycznie.
- Menu run pokazuje obecne symbole, nazwy, koszty i dostępność. `R` otwiera
  listę, strzałki wybierają, Enter otwiera podgląd mocy; jej wykonanie
  zachowuje obecne potwierdzenie. Bez drugiego katalogu zdolności w JS.
- `I` otwiera podgląd ekwipunku, a jawne „Użyj” prowadzi do istniejącego
  przepływu przedmiotu. Przygotowanie, zmiana wyposażenia i blokady podczas
  misji zachowują aktualne zasady. Panel informacyjny nie wykonuje akcji pod nim.
- Podpisy pokazują skróty i aktualny sens Enter/Esc. Zachowujemy układ
  laptopa przy fizycznej planszy; wystarczy informacja o wskazanym polu,
  bez budowania ekranowego VTT i bez przebudowy całego wyglądu.
- Tekst, pola liczbowe, `contenteditable`, kompozycja znaków i najwyższy
  modal mają pierwszeństwo. Skróty nie przechwytują pisania ani standardowych
  kombinacji systemowych. Skaner keyboard-wedge jest wyłączony w tym profilu,
  aby parser prefiksu kart nie buforował zwykłych liter.
- Powtarzanie klawisza jest dozwolone tylko dla kontrolowanej nawigacji.
  Enter, użycie przedmiotu, rzut i koniec tury nie powtarzają się.
  Przy szybkich strzałkach utrzymujemy jedno żądanie podglądu w locie
  i najnowszą docelową pozycję; zatwierdzenie czeka na jej synchronizację.
  Utrata fokusu i zmiana kontekstu czyszczą oczekujące wejścia.

Przewidywane pliki: nowy `ui/static/keyboard_input.js`,
`ui/static/exploration.js`, `ui/static/resonance_combat.js`,
`ui/static/launcher_board.js`, `ui/static/session_navigation.js`,
`ui/templates/exploration.html` i używane szablony launchera.
Punktowo także `ui/static/mission_zero.js`, `ui/static/confrontation.js`,
`ui/static/exploration_mana.js`, `ui/party_preparation.py` oraz właściwe CSS.
Dotykamy ich tylko w zakresie integracji wejścia i podpisów.

## Warstwa 4: gameplay — wymagane dostosowania

Docelowa lista zmian w zasadach jest pusta. Zostają obecne koszty, zasięgi,
pathfinding, przekątne właściwe dla aktywnego profilu, teren, widoczność,
ekonomia akcji, runy/Rezonans, AI, rzuty, ekwipunek i następstwa fabularne.
Nie ujednolicamy przy tej okazji historycznych modeli ruchu i walki.

Zmienia się sposób zadeklarowania i potwierdzenia decyzji:

- W setupie gracz wskazuje pole klawiaturą i potwierdza fizyczne ustawienie
  według istniejących kroków. LED-y nadal prowadzą przez kafle i aktorów.
- Pozycja w aplikacji pozostaje źródłem prawdy. Figurka jest przesuwana
  ręcznie zgodnie z podświetleniem; bez czujników nie obiecujemy wykrywania
  pomyłek ani automatycznego rozpoznawania jej położenia.
- Ruch zachowuje obecne zatwierdzenie. Nie dodajemy nowego obowiązkowego
  potwierdzania każdego pola trasy ani dodatkowej fazy każdej tury.
- W eksploracji wybieramy obecne miejsca, uczestników i opcje scen;
  nie dodajemy swobodnego chodzenia drużyny, jeżeli scena go nie modeluje.
- Rzuty bohaterów pozostają fizyczne, wyniki wprowadzamy klawiaturą
  przez istniejący przepływ kości. Przeciwników nadal rozlicza aplikacja.
- Reakcje i rozpatrywanie akcji blokują skróty niepowiązanych działań.
  Cofnięcie korzysta z obecnych granic; nie odwraca rozliczonych efektów.

Nowe odstępstwo od zasad, kosztów lub kolejności rozstrzygania wymaga
osobnego uzgodnienia. Swobodna korekta pozycji/teleportacja nie jest częścią
tego zadania; błędy rozstawienia obsługujemy istniejącym cofaniem setupu.

## Warstwa 5: konfiguracja i uruchamianie

- Dodać jawny wybór profilu sterowania, niezależny od wyjścia LED:
  klawiatura albo dotychczasowe wejście planszy; WLED albo symulator.
  Dla nowego profilu na sprzęcie wymagany jest adres WLED, bez portu serial.
- Umożliwić rozwój i testowanie klawiatury z symulatorem jako podglądem LED,
  bez klikania w jego mapę. Profil sterowania nie zmienia zasad scenariusza.
- Zachować wspólną konfigurację przy przejściach menu ↔ gra i wczytywaniu;
  nie uruchamiać prób podłączenia USB w tle. Ustawienia sprzętu pozostają
  poza zwykłym przepływem decyzji gracza.
- Rozszerzyć obecne entry pointy, bez tworzenia drugiej wersji silnika.
  Pada na razie nie implementujemy i nie dodajemy zależności do obsługi wejścia.

Przewidywane pliki: `runtime/exploration_ui.py`,
`scripts/resonance_playtest.py`, konfiguracja w `ui/launcher_board.py`
i `ui/routes.py`; `runtime/mission_combat_ui.py` tylko jeśli korzysta
ze zmienianej wspólnej konfiguracji. Ścieżki modułów są pod
`src/dnd_board_game/`, o ile nie wskazano inaczej.

## Kolejność realizacji po akceptacji

| Etap | Zakres | Warunek zakończenia |
| --- | --- | --- |
| 1 | Kontrakt wejścia, konteksty, rewizje i profil WLED bez seriala | Świecenie działa bez USB; profil nie uruchamia skanera. |
| 2 | Pierwszy pełny przepływ w arenie v0.3 | M → strzałki → podgląd LED → Enter/Esc; atak i jedna moc obsłużone klawiaturą. |
| 3 | Pełna walka, ekwipunek i menu run | Wszystkie postacie, moce, cele, obszary, reakcje, kości i koniec tury obsługiwane klawiaturą. |
| 4 | Launcher, setup, Misja 0 i eksploracja | Cała sesja od startu do zapisu/wczytania bez czujników i myszy. |
| 5 | Regresje i próba fizyczna | Potwierdzona zgodność zasad i działanie LED z odłączonym USB skanera. |

Każdy etap ma mały, osobny zakres zmian i własne sprawdzenia. Akceptacja
planu uruchamia tę kolejność; zakończenie etapu nie oznacza zgody na zmianę
mechanik ani konieczności kolejnych formalnych akceptacji implementacyjnych.

## Testy i kryteria odbioru

Nowe testy planujemy pod `tests/unit/`, `tests/integration/` i `tests/hardware/`:

- Czysta nawigacja kursora: granice, panel, orientacja i przejścia kontekstu.
- WLED bez USB: każde otwarcie/probe portu lub utworzenie `SerialV2` oznacza
  błąd testu; brak skanów podczas startu, resetu, wczytania i powrotu do menu.
- Zgodność wejść: ta sama zatwierdzona decyzja z klawiatury i dotychczasową
  ścieżką daje ten sam stan domenowy i wynik przy tych samych rzutach.
- W bezkosztowym podglądzie przed zatwierdzeniem kilka zmian celu oraz Esc
  nie zmienia pozycji, zasobów, kolejki rozpatrywania efektów ani wyników
  kości. W rozpoczętych reakcjach obowiązują istniejące granice anulowania.
  Jeden Enter rozlicza dokładnie jeden dozwolony krok.
- Niedozwolony cel i zaległa rewizja nie wykonują poprzedniego wyboru.
  Szybkie strzałki, przytrzymanie Enter, zmiana tury i utrata fokusu
  nie powodują podwójnych ani opóźnionych działań.
- Rzeczywiste zdarzenia klawiatury w przeglądarce, nie tylko wywołania API:
  menu, wszystkie siedem postaci, setup, inicjatywa, konfrontacja, obszar,
  przestawienie, reakcja, mikstura, ekwipunek, zapis/wczytanie i modal.
- Opóźnione/błędne WLED nie blokuje routera wejścia; powrót połączenia
  pokazuje najnowszą ramkę, a zamknięcie wygasza LED-y dostępną ścieżką.

Istniejące testy do punktowej aktualizacji/regresji: `test_combat_keyboard.py`,
`test_rune_combat_board.py`, `test_mission_combat_board_input.py`,
`test_board_connection_startup.py`, `test_wled_output.py`,
`test_board_scan_scheduling.py`, `test_runtime_exploration_ui.py`,
`test_resonance_decision_details.py`, `test_movement_returns_to_menu.py`,
odpowiednie testy browserowe launchera/ekwipunku/nawigacji oraz
`tests/integration/test_combat_board_feedback.py`.

Pytest uruchamiamy **pojedynczo, z timeoutem**, przez
`scripts/safe_pytest.sh --timeout 60 <konkretny plik lub node id>`.
Nie uruchamiamy równoległych procesów pytest. Końcowy test sprzętowy:
odłączone USB skanera, działający WLED i pełne przejście Misji 0
klawiaturą. Wyniki symulatora i próby fizycznej zapisujemy oddzielnie.

## Poza tym wdrożeniem

Obsługa pada, multiplayer, zmiana balansu, nowe akcje, odzyskanie kolumny
panelu dla mapy, przeprojektowanie wydruków, wymiana protokołu WLED,
automatyczna detekcja figurek i przebudowa silnika pozostają osobnymi tematami.

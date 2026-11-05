# Plansza LED — klawiatura i plan rozbudowy o pada

Status: **zakres klawiaturowy zaakceptowany i wdrożony; pad odłożony**.
Aktualizacja: 05.11.2026.
Branch: `feat/led-keyboard-control`.

## Aktualne wdrożenie: klawiatura + LED

Zgodnie z najnowszą decyzją implementacja obejmuje najpierw klawiaturę.
Gotowy start: `.venv/bin/python scripts/keyboard_playtest.py`;
szybka walka: `--arena --skip-setup`; prawdziwe światła: `--wled-url ADRES`.
[Instrukcja i przypisania](playtests/KEYBOARD_LED_MANUAL.md).

Zrealizowano WLED bez seriala, osobny profil wejścia, przejściowy kursor,
podgląd na prywatnej kopii silnika, zabezpieczenie rewizji i modalów,
klawiaturę w launcherze, setupie, Misji 0, rozmowach, ekwipunku i walce v0.3.
Strzałki nie mutują wyboru celów. Enter korzysta z istniejącego zatwierdzenia;
Spacja wybiera cele do zestawu. Zasady i format zapisu domenowego są zachowane.
Sprawdzono atrapy hardware i rzeczywiste zdarzenia klawiatury w Chrome.
Próba fizycznej planszy pozostaje osobnym punktem odbioru.

Poniższy projekt pada i jego Gamepad API opisują dalszą rozbudowę, której
obecne wdrożenie nie zawiera. Klawiatura jest teraz głównym wejściem.

## Docelowa rozbudowa: pad

Przygotować osobny, opcjonalny profil **pad + LED** na obecnym komputerze
z Linuxem. Pad jest głównym wejściem od pierwszego etapu; klawiatura pozostaje
dostępna do obsługi awaryjnej i swobodnego tekstu. Fizyczna plansza wyświetla
informacje. Czujniki pól, przyciski runiczne i skaner kart nie są wymagane.
Figurki, kafle, karty i fizyczne rzuty pozostają częścią gry. Jeden bezprzewodowy
pad przekazujemy graczowi podejmującemu bieżącą decyzję, bez zmiany własności
postaci i kolejności tur. Wielu równoczesnych kontrolerów nie obejmuje ten etap.

Zakres pierwszego wdrożenia: menu startowe, wybór i przygotowanie drużyny,
Misja 0, swobodna arena, rozstawianie planszy i figurek, inicjatywa,
eksploracja, konfrontacje, aktualna walka `rune_relations_v03`, ekwipunek,
runy, rzuty, reakcje, dziennik, ściąga oraz zapis/wczytanie. Wspólne elementy
pozostałych scenariuszy korzystają z tej samej obsługi; starsze profile walki
zachowują dotychczasowe działanie i wymagają regresji tam, gdzie dotykamy
wspólnego kodu. Nie przebudowujemy wszystkich historycznych interfejsów.

Wdrożona warstwa klawiatury dostarcza wspólny dispatcher i kontrakt wejścia
dla przyszłego adaptera pada. Zakup i próba pada nie blokują testu klawiatury.

## Pad do testów i odbiór — sprawdzone 05.11.2026

Pierwszy wybór dla obecnego Linuxa: **Sony DualSense**, przez Bluetooth.
Sterownik `hid-playstation` w źródłach Linuxa 6.8 obsługuje tę rodzinę przez
USB i Bluetooth; środowisko robocze zgłasza kernel `6.8.0-147-generic`.
To podstawa rekomendacji, a nie wynik próby fizycznego egzemplarza.
Zgodność wybranego pada z adapterem Bluetooth i przeglądarką sprawdzamy
przed rozbudową interfejsu. [Źródło sterownika](https://raw.githubusercontent.com/torvalds/linux/v6.8/drivers/hid/hid-playstation.c).

| Wariant | Oferta i cena w chwili sprawdzenia | Połączenie do testów |
| --- | --- | --- |
| Polecany: nowy Sony DualSense Nocna Czerń v3 | [MediaMarkt — 299,99 zł, dostępny online](https://mediamarkt.pl/pl/product/_kontroler-bezprzewodowy-playstation-dualsense-nocna-czern-v3-czarny-1501214.html) | Bluetooth; USB do porównania i ładowania. |
| Ten sam typ, opcja sprawdzenia odbioru w Wołominie: DualSense Biały | [Media Expert — 349,99 zł](https://www.mediaexpert.pl/gaming/kontrolery-pady/kontroler-sony-dualsense-bialy-6) | Bluetooth; dostępność w salonie Geodetów 2 niepotwierdzona. |
| Tańsza alternatywa: 8BitDo Ultimate 2C Wireless Miętowy | [Media Expert — 129,00 zł](https://www.mediaexpert.pl/gaming/kontrolery-pady/kontroler-8bitdo-ultimate-2c-mietowy) | Dołączony odbiornik USB 2,4 GHz; zgodność obecnego Linuxa wymaga próby. |

8BitDo deklaruje Windows/Android, połączenie PC przez 2,4 GHz lub USB,
a Bluetooth dla Androida; nie deklaruje Linuxa. Nowszy sterownik `xpad`
ma wpis tego modelu, ale nie dowodzi to działania na obecnym systemie.
Nie mylić wariantu **Wireless** z modelem **2C Bluetooth** do Switcha.
[Specyfikacja producenta](https://www.8bitdo.com/ultimate-2c-wireless-controller/),
[xpad w Linuxie 6.12](https://raw.githubusercontent.com/torvalds/linux/v6.12/drivers/input/joystick/xpad.c).

Lokalnie działa [Media Expert Wołomin, Geodetów 2](https://www.mediaexpert.pl/sklepy/wolomin/geodetow-2),
tel. 539 549 741, pon.–sob. 9:00–21:00. Strony 8BitDo i DualSense pokazują możliwość
odbioru w sklepie, ale nie potwierdzono zapasu ani terminu w tym salonie.
Dla DualSense opcją w okolicy jest
[MediaMarkt Targówek, Głębocka 13](https://mediamarkt.pl/pl/store/mediamarkt-warszawa-targowek-945).
Jego strona produktu wymaga wyboru sklepu; odbiór tego egzemplarza pozostaje
niepotwierdzony. Potwierdzona jest oferta online, a ceny i stany są zmienne.

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
   otwarcie panelu informacji i zmiana wartości kości. Pad i klawiatura
   mapują przyciski na te same polecenia od pierwszego etapu.
   Dispatcher wykorzystuje istniejące komendy poszczególnych przepływów.
   Adapter pada nie generuje sztucznych zdarzeń `KeyboardEvent`.
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
   kursor jedynie wyróżnia opcję do późniejszego wybrania krzyżykiem / Enterem.
5. Wymagać aktualnego kontekstu i rewizji przy poleceniach. Zmiana ekranu,
   tury, etapu wyboru lub wczytanie usuwa zaległe wejścia. Zatwierdzanie
   ma dotyczyć ostatniego potwierdzonego przez serwer wskazania; błędny
   lub jeszcze niesynchronizowany kursor nie może wykonać poprzedniego celu.
6. Stan nawigacji trzymać w sesji/prezentacji, bez globalnego stanu gry.
   Nie dodawać go do zapisu domenowego. Już zapisywane decyzje pozostają
   obsługiwane przez istniejący format; po wczytaniu odtwarzamy kontekst.

Przewidywane pliki: nowe `ui/input_commands.py` i `ui/input_context.py`
(kontrakt i obsługa kontekstu), punktowe zmiany w `ui/session_state.py`,
`ui/session_view.py`, `ui/exploration_app.py`, `ui/routes.py`, `ui/resonance.py`.
Bez szerokiej ekstrakcji ani przebudowy dużego koordynatora sesji.

## Warstwa 2: hardware — WLED bez USB

1. Dodać do `board.Connection` backend wyjściowy, roboczo `wled`.
   Wykorzystuje istniejący klient WLED, mapowanie i kolejkę ramek.
   Nie otwiera ani nie wyszukuje portów serial planszy, nie tworzy `SerialV2`.
   Nieznana nazwa backendu kończy się błędem walidacji, zamiast domyślnie
   uruchamiać skaner planszy przez USB.
2. W adapterze rozdzielić możliwości wejścia i wyjścia, np.
   `can_scan` i `can_display_leds`, od diagnostyki dostępności WLED.
   Pad i klawiatura nie wymagają stanu „czujniki połączone”.
3. Uzależnić `auto_arm`, ponawianie i anulowanie skanów od `can_scan`
   w grze oraz launcherze. W profilu pada/klawiatury nie tworzyć pozornych
   skanów ani heartbeatów skanera USB. Zmiana kontekstu nadal unieważnia wejście.
4. Zachować obecne semantyczne ramki: aktywny aktor, zasięg, trasa, cel,
   obszary, reakcje, setup i wyniki. Kursor składa się z tymi warstwami.
   Wskazanie do podglądu nie włącza jasności przeznaczonej na fizyczny skan.
5. Zachować asynchroniczne wysyłanie i ponawianie najnowszej ramki.
   Awaria WLED nie uruchamia USB ani nie zmienia źródła wejścia.
   UI pokazuje osobno gotowość pada, klawiatury i błąd świateł; po powrocie
   połączenia wysyłamy aktualny podgląd, bez odgrywania starych kroków.
   Także start z niedostępnym WLED zachowuje działające wejście.
6. Zachować profil przy restarcie sesji, wczytaniu i powrocie do menu.
   Wyjście z aplikacji korzysta z obecnego wygaszania i zamykania połączeń.

Przewidywane pliki: `board/connection.py`,
`src/dnd_board_game/hardware/board_session.py`, punktowo
`hardware/resonance_feedback.py`, `ui/exploration_app.py`,
`ui/launcher_board.py`. `board/settings.py` tylko jeśli konfiguracja tego wymaga.
W `board/` pozostaje wyłącznie komunikacja; nie trafiają tam decyzje gry.
USB do ładowania pada lub jego odbiornika 2,4 GHz jest dozwolone;
„bez USB” w tym planie oznacza brak wymaganego skanera planszy.

## Warstwa 3: UI — pad, klawiatura i widoczny podgląd

Podstawowy adapter przeglądarkowy używa `navigator.getGamepads()` i
`requestAnimationFrame`, bez nowej biblioteki Python/JS, Steam Input
i emulacji klawiatury. Zdarzenia połączenia służą wykrywaniu urządzenia,
a aktualny stan przycisków i osi odczytujemy w pętli. Korzystamy ze wspólnego
dispatchera. [Opis API](https://developer.mozilla.org/en-US/docs/Web/API/Gamepad_API/Using_the_Gamepad_API).

| Pad DualSense / układ Xbox | Polecenie |
| --- | --- |
| Krzyżak | Krok kursora po siatce; w menu wybór opcji; przy kości góra/dół zmienia wynik. |
| Lewy analog | Ten sam dyskretny kursor, także po skosie; bez płynnego ruchu postaci. |
| Krzyżyk × / A | Wybór opcji albo obecne zatwierdzenie podglądu. |
| Kółko ○ / B | Cofnięcie dozwolonego kroku lub zamknięcie najwyższego panelu. |
| Kwadrat □ / X | Ekwipunek, jeśli dopuszcza go bieżący kontekst. |
| Trójkąt △ / Y | Menu run i akcji, w tym ruch oraz zwykły atak. |
| L1/R1 / LB/RB | Poprzedni/następny cel albo zakładka w odpowiednim kontekście. |
| Options / Menu | Menu gry: postać, dziennik, ściąga, zapis i koniec tury. |

Skróty menu jedynie otwierają wybór. Koniec tury wymaga obecnego
potwierdzenia; nie przypisujemy go bezpośrednio do bumpera ani spustu.
Przyciski PS/Guide i Create/Share nie są wymagane do rozgrywki.
Podpisy pokazujemy według rozpoznanego układu: ×/○/□/△ dla DualSense.

Zasady adaptera pada:

- Ekran sprawdzenia urządzenia pokazuje wykryty model, stan osi i mapowanie.
  Pierwszy świadomy przycisk aktywuje wybrany pad; to naciśnięcie nie wykonuje
  jednocześnie decyzji gry. Pozostałe podłączone pady nie przejmują wejścia.
- Przy `mapping === "standard"` stosujemy standardowe pozycje przycisków;
  pustego/innego mapowania nie zgadujemy z napisu na urządzeniu. Pokazujemy
  diagnostykę i pozostawiamy klawiaturę. Osobne mapowanie dodajemy tylko,
  jeżeli wymaga go kupiony pad; uniwersalny kreator kalibracji odkładamy.
  [Standard mapowania](https://www.w3.org/TR/gamepad/#remapping).
- Krzyżak jest podstawą, analog ma martwą strefę i histerezę. Wartości
  startowe do ogrania: wejście w kierunek przy 0,5, powrót do neutralnego
  poniżej 0,3; pierwszy krok od razu, powtórzenia po 300 ms co 120 ms.
  To ustawienia interfejsu, a nie zmiana zasięgu lub kosztów ruchu.
- Na mapie dwie sąsiednie składowe kierunku mogą dać jeden ukośny krok
  kursora; przeciwne kierunki znoszą się. W menu nawigacja jest pojedyncza.
  Krzyżak ma pierwszeństwo przed analogiem, aby nie generować podwójnych kroków.
- Akcje reagują tylko na przejście puszczony → wciśnięty. Wciśnięty krzyżyk
  nie zatwierdza kolejnej kości, reakcji ani ekranu. Powtarza się tylko nawigacja.
- Zmiana kontekstu, ukrycie strony, utrata fokusu i rozłączenie zerują
  powtórzenia. Powrót wymaga zwolnienia przycisków i wycentrowania analoga.
  Rozłączenie nie zatwierdza ani nie anuluje akcji; klawiatura pozostaje dostępna.
- Testujemy istniejący adres `127.0.0.1`. Wykrywamy dostępność API i obsługujemy
  odmowę dostępu. Nie dokładamy wdrożenia HTTPS do tego zadania; działanie
  przez inny adres sprawdzamy osobno dla używanej przeglądarki.

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

1. Trójkąt → „Ruch” → krzyżyk (albo `M`) otwiera obecny podgląd ruchu;
   kursor zaczyna na polu bohatera.
2. Krzyżak/analog albo strzałki przesuwają **cel podglądu**. LED-y pokazują istniejący zasięg,
   wyliczoną trasę i docelowe pole. UI podaje współrzędne i koszt.
3. Trasę liczy aktualny silnik od pozycji bohatera do celu; sekwencja
   naciśnięć nie staje się ręcznie wytyczoną trasą. Dotarcie kursorem
   do pola po skosie nadal pozwala wykorzystać legalną trasę diagonalną.
4. Kursor nie zawija na krawędziach i nie wchodzi w panel `col=19`.
   Kierunki odpowiadają orientacji rozłożonej planszy; ustalamy je jawnie
   przy próbie sprzętowej, bez zmiany modelu współrzędnych.
5. Niedostępny cel pokazuje odmowę i blokuje wykonanie. Nawigacja nie może
   utknąć dlatego, że sąsiednie pole jest przeszkodą: kursor jest wskazaniem,
   a legalność trasy nadal ocenia silnik.
6. Krzyżyk / `Enter` wykonuje zatwierdzony ruch. Gracz przestawia figurkę na wskazane
   pole; UI pokazuje nową pozycję i pozostały ruch. Zachowujemy obecne
   przerwania, ataki okazyjne i powrót do menu. Kółko / `Esc` anuluje podgląd.

Pozostałe zmiany UI:

- Ataki i moce używają tego samego kursora dla pola celu/centrum obszaru.
  Wieloetapowe akcje prowadzą przez obecne kroki, np. wróg → miejsce
  lądowania albo obszar → postać wyłączona z efektu. Kursor resetuje się
  odpowiednio do nowego etapu; nie zatwierdza go automatycznie.
- Menu run pokazuje obecne symbole, nazwy, koszty i dostępność. Trójkąt / `R`
  otwiera listę, kierunki wybierają, krzyżyk / Enter otwiera podgląd mocy; jej wykonanie
  zachowuje obecne potwierdzenie. Bez drugiego katalogu zdolności w JS.
- Kwadrat / `I` otwiera podgląd ekwipunku, a jawne „Użyj” prowadzi do istniejącego
  przepływu przedmiotu. Przygotowanie, zmiana wyposażenia i blokady podczas
  misji zachowują aktualne zasady. Panel informacyjny nie wykonuje akcji pod nim.
- Podpisy pokazują przyciski pada, skróty i aktualny sens potwierdzenia/cofnięcia. Zachowujemy układ
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

Przewidywane pliki: nowe `ui/static/input_dispatcher.js`,
`ui/static/gamepad_input.js` i `ui/static/keyboard_input.js`,
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

- W setupie gracz wskazuje pole padem i potwierdza fizyczne ustawienie
  według istniejących kroków. LED-y nadal prowadzą przez kafle i aktorów.
- Pozycja w aplikacji pozostaje źródłem prawdy. Figurka jest przesuwana
  ręcznie zgodnie z podświetleniem; bez czujników nie obiecujemy wykrywania
  pomyłek ani automatycznego rozpoznawania jej położenia.
- Ruch zachowuje obecne zatwierdzenie. Nie dodajemy nowego obowiązkowego
  potwierdzania każdego pola trasy ani dodatkowej fazy każdej tury.
- W eksploracji wybieramy obecne miejsca, uczestników i opcje scen;
  nie dodajemy swobodnego chodzenia drużyny, jeżeli scena go nie modeluje.
- Rzuty bohaterów pozostają fizyczne, wyniki ustawiamy krzyżakiem góra/dół
  i zatwierdzamy krzyżykiem przez istniejący przepływ kości; klawiatura
  pozostaje alternatywą. Przeciwników nadal rozlicza aplikacja.
- Swobodne deklaracje i pytania do MG nadal wpisujemy klawiaturą. Nie
  zastępujemy ich automatycznymi wyborami ani nie budujemy klawiatury ekranowej.
- Reakcje i rozpatrywanie akcji blokują skróty niepowiązanych działań.
  Cofnięcie korzysta z obecnych granic; nie odwraca rozliczonych efektów.

Nowe odstępstwo od zasad, kosztów lub kolejności rozstrzygania wymaga
osobnego uzgodnienia. Swobodna korekta pozycji/teleportacja nie jest częścią
tego zadania; błędy rozstawienia obsługujemy istniejącym cofaniem setupu.

## Warstwa 5: konfiguracja i uruchamianie

- Dodać jawny wybór profilu sterowania, niezależny od wyjścia LED:
  pad z klawiaturą awaryjną, sama klawiatura albo dotychczasowe wejście
  planszy; WLED albo symulator.
  Dla nowego profilu na sprzęcie wymagany jest adres WLED, bez portu serial.
- Umożliwić rozwój i testowanie pada oraz klawiatury z symulatorem jako podglądem LED,
  bez klikania w jego mapę. Profil sterowania nie zmienia zasad scenariusza.
- Zachować wspólną konfigurację przy przejściach menu ↔ gra i wczytywaniu;
  nie uruchamiać prób podłączenia USB w tle. Ustawienia sprzętu pozostają
  poza zwykłym przepływem decyzji gracza.
- Rozszerzyć obecne entry pointy, bez tworzenia drugiej wersji silnika.
  Nie dodawać zależności do obsługi wejścia. Parowanie Bluetooth wykonujemy
  w systemie; aplikacja nie zarządza sterownikami i usługą Bluetooth.

Przewidywane pliki: `runtime/exploration_ui.py`,
`scripts/resonance_playtest.py`, konfiguracja w `ui/launcher_board.py`
i `ui/routes.py`; `runtime/mission_combat_ui.py` tylko jeśli korzysta
ze zmienianej wspólnej konfiguracji. Ścieżki modułów są pod
`src/dnd_board_game/`, o ile nie wskazano inaczej.

## Kolejność realizacji po akceptacji

| Etap | Zakres | Warunek zakończenia |
| --- | --- | --- |
| 0 | Próba konkretnego pada na obecnym Linuxie i prosty podgląd wejścia | Bluetooth, przyciski, mapping, powrót z uśpienia i widoczność w przeglądarce sprawdzone. |
| 1 | Kontrakt wejścia, adapter pada i klawiatury, rewizje i WLED bez seriala | Świecenie i polecenia pada działają bez skanera planszy. |
| 2 | Pierwszy pełny przepływ w arenie v0.3 | Menu ruchu → krzyżak → podgląd LED → krzyżyk/kółko; atak i jedna moc obsłużone padem. |
| 3 | Pełna walka, ekwipunek i menu run | Wszystkie postacie, moce, cele, obszary, reakcje, kości i koniec tury obsługiwane padem. |
| 4 | Launcher, setup, Misja 0 i eksploracja | Strukturalne decyzje całej sesji od startu do zapisu/wczytania bez czujników i myszy; wolny tekst na klawiaturze. |
| 5 | Regresje i próba fizyczna | Zgodność zasad, LED-y z odłączonym skanerem, poprawne rozłączenie/wznowienie pada i klawiatura awaryjna. |

Każdy etap ma mały, osobny zakres zmian i własne sprawdzenia. Akceptacja
planu uruchamia tę kolejność; zakończenie etapu nie oznacza zgody na zmianę
mechanik ani konieczności kolejnych formalnych akceptacji implementacyjnych.

## Testy i kryteria odbioru

Nowe testy planujemy pod `tests/unit/`, `tests/integration/` i `tests/hardware/`:

- Czysta nawigacja kursora: granice, panel, orientacja i przejścia kontekstu.
- Adapter pada: standardowe pozycje przycisków, odmowa zgadywania innego układu,
  martwa strefa, histereza, przekątne, krzyżak + analog, rytm powtórzeń,
  jeden pad, pierwszy przycisk aktywacji i puszczenie po zmianie kontekstu.
- WLED bez USB: każde otwarcie/probe portu lub utworzenie `SerialV2` oznacza
  błąd testu; brak skanów podczas startu, resetu, wczytania i powrotu do menu.
- Zgodność wejść: ta sama zatwierdzona decyzja z pada, klawiatury i dotychczasową
  ścieżką daje ten sam stan domenowy i wynik przy tych samych rzutach.
- W bezkosztowym podglądzie przed zatwierdzeniem kilka zmian celu oraz Esc
  nie zmienia pozycji, zasobów, kolejki rozpatrywania efektów ani wyników
  kości. W rozpoczętych reakcjach obowiązują istniejące granice anulowania.
  Jeden Enter rozlicza dokładnie jeden dozwolony krok.
- Niedozwolony cel i zaległa rewizja nie wykonują poprzedniego wyboru.
  Szybkie strzałki, przytrzymanie Enter, zmiana tury i utrata fokusu
  nie powodują podwójnych ani opóźnionych działań.
- Przytrzymany krzyżyk nie zatwierdza dwóch etapów; odłączenie pada,
  ukrycie strony, zmiana fokusu i ponowne połączenie nie odtwarzają komend.
  Brak API lub nieznane mapowanie pozostawia działającą klawiaturę.
- Kontrolowane próbki Gamepad API oraz rzeczywiste zdarzenia klawiatury
  w przeglądarce, nie tylko wywołania serwera:
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
odłączone USB skanera, działający WLED i przejście decyzji Misji 0 padem
przez Bluetooth, z fizycznymi rzutami i wpisaniem swobodnego tekstu
klawiaturą tam, gdzie wymaga tego scena. Wyniki symulatora, symulowanego
wejścia pada i fizycznej próby Bluetooth zapisujemy oddzielnie.

## Poza tym wdrożeniem

Wiele jednoczesnych padów, wibracje/adaptacyjne spusty, multiplayer,
zmiana balansu, nowe akcje, odzyskanie kolumny
panelu dla mapy, przeprojektowanie wydruków, wymiana protokołu WLED,
automatyczna detekcja figurek i przebudowa silnika pozostają osobnymi tematami.

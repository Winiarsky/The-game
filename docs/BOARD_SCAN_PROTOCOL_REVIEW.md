# Przegląd skanera ESP32 i protokołu planszy

Stan: 2026-09-10. Audyt aktualnego kodu i propozycja następnego wdrożenia.
Opis v2 poniżej jest projektem, nie działającym jeszcze protokołem.
Nie wgrywano firmware ani nie podłączano fizycznego portu podczas audytu.

**Aktualizacja po rozmowie:** docelowo skanujemy tylko aktywne pola, bez tła
i `rejected_press`. Aktualny kontrakt opisuje
[BOARD_SCAN_PROTOCOL_V2.md](BOARD_SCAN_PROTOCOL_V2.md). Poniższe ustalenia
o błędach obecnego kodu pozostają aktualne; propozycje tła, ARM i etapowego
rozszerzania kontraktu zachowano jako historię audytu, nie plan wdrożenia.

**Stan po przygotowaniu firmware:** szkic został zastąpiony przez
`board_scan_protocol_v2_1` z kompatybilnością v1. Poniższa tabela opisuje kod
sprzed tej zmiany. Parser ESP, sprawdzane I²C, maski i mechanizmy v2 są już
w źródle urządzenia; aktualny backend aplikacji nadal używa v1. Fizycznej
płytki nie aktualizowano podczas samego przygotowania kodu. Następnie, na
osobne polecenie użytkownika, wgrano firmware i sprawdzono na urządzeniu:
[raport wdrożenia](BOARD_FIRMWARE_DEPLOYMENT.md).

## Wniosek

Warto przekazywać ESP listę aktywnych pól. Największa oszczędność wynika
z pomijania niepotrzebnych **kolumn i ekspanderów wierszy**, ponieważ odczyt
grupowy już pobiera wiele wierszy jednocześnie. Przy inicjatywie potrzebna
jest jedna kolumna panelu, zamiast wszystkich dwudziestu.

Rekomendowany po rozmowie wariant: odczyt wyłącznie aktywnych pól,
ignorowanie pozostałych i ciągłe wejście w ramach jednej kości.
Aplikacja nadal sprawdza legalność działania.
ESP zna tylko maskę wejścia — nie zasady walki, cele ataków ani koszt many.

Drugą równie ważną zmianą jest rozdzielenie oczekiwania na człowieka od
wykrywania awarii oraz powiązanie każdej komendy i odpowiedzi z konkretnym
kontekstem wejścia. Samo szybsze odczytywanie pinów nie rozwiąże tych problemów.

## Jak działa obecna ścieżka

```mermaid
sequenceDiagram
    participant UI as Przeglądarka
    participant App as Sesja gry
    participant USB as board.Connection
    participant ESP as ESP32
    UI->>App: scan(rewizja ekranu)
    App->>USB: scan_board(dozwolone pola)
    USB->>ESP: SCAN
    ESP-->>USB: armed
    Note over ESP: Cała plansza; najpierw zwolnienie styków
    ESP-->>USB: press(col,row)
    Note over ESP: Skan zakończony także dla złego pola
    alt Pole dozwolone
        USB-->>App: współrzędne
        App->>App: sprawdzenie rewizji i reguł
        App-->>UI: nowy stan
    else Pole niedozwolone
        USB->>ESP: STOP i ponowne SCAN
        Note over USB: Ostrzeżenie tylko w logu transportu
    end
```

Lista pól już istnieje w `_current_board_scan_target()` i przechodzi przez
`BoardSessionAdapter.scan()` do `_HardwareBackend.scan_board()`. Ostatni krok
nie wysyła jej do ESP: `_send_scan_command()` wysyła sam tekst `SCAN`.
Rewizja ekranu także pozostaje po stronie aplikacji.

Źródła: [sesja gry](../src/dnd_board_game/ui/exploration_app.py),
[adapter](../src/dnd_board_game/hardware/board_session.py),
[transport](../board/connection.py),
[szkic ESP32](../future/board_20x30_usb_wled_test/esp32_board_scan_trigger_test.ino).

## Potwierdzone problemy

| Priorytet | Obecne zachowanie | Skutek i proponowana zmiana |
|---|---|---|
| Wysoki | ESP milczy po `armed`; Python ma `scan_recovery_timeout_s=10`. | Zdrowy skaner czekający na gracza jest resetowany po 10 s ciszy. Dodać okresowy status i osobny termin odpowiedzi urządzenia. |
| Wysoki | `press`, `armed` i `cancel` nie mają ID żądania ani ID uruchomienia urządzenia. | Nie można jednoznacznie przypisać opóźnionej odpowiedzi do starego skanu. Rewizja UI i lokalny licznik anulowań ograniczają ryzyko, ale nie są protokołem end-to-end. |
| Wysoki | Parser po przekroczeniu 64 znaków zeruje bufor i zbiera dalszy fragment tej samej linii. | Końcówka uszkodzonej linii może zostać wykonana jako nowa komenda. Odrzucać całą linię aż do separatora. |
| Wysoki | W `Connection.scan_board()` dowolny `TypeError` powoduje ponowne wywołanie backendu bez `timeout_s`. | Błąd danych może uruchomić drugi skan bez limitu czasu. Zgodność sygnatur sprawdzać przed wywołaniem, nie przez przechwytywanie błędów z wnętrza metody. |
| Wysoki | `int(payload["col"])` przyjmuje bool i obcina ułamek; nie ma pełnego schematu odpowiedzi. | Wadliwa wiadomość może stać się poprawnym polem. Wymagać typu int, granic 20×30, kompletnych pól i właściwego ID. Pusta maska ma wyłączać wejście, a nie znaczyć „wszystko”. |
| Średni | Każde złe pole kończy skan na ESP i wywołuje ponowne uzbrojenie z Pythona. | Zbędna przerwa; brak komunikatu dla gracza. Odrzucać lokalnie, wysłać informacyjne zdarzenie i dalej skanować. |
| Średni | `waitingForClear` wymaga zwolnienia całej planszy; skaner zwraca pierwsze znalezione pole. | Przytrzymany lub uszkodzony styk może blokować inne przyciski. Śledzić zwolnienie poszczególnych aktywnych pól i diagnozować przytrzymane styki. |
| Średni | `allColumnsHigh()` używa 20 osobnych `digitalWrite` przy każdym przebiegu i ponownie przy wykryciu styku. | Pozostaje dużo operacji I²C mimo odczytu grupowego. W pętli przywracać tylko aktywowaną kolumnę; pełne wygaszenie kolumn zostawić na start, błąd i reset. |
| Średni | Rozpoznanie portu przyjmuje dowolny obiekt z właściwym `protocol`, także wczesny `boot`. | „Port odpowiedział” nie oznacza „czujniki gotowe”. Negocjować wersję, możliwości, rozmiar i status inicjalizacji. |
| Średni | Polecenia są „czyszczone”, a PING/STATUS wykrywane jako fragment napisu. | `S C A N` staje się `SCAN`, a `NOTPING` wywołuje PING. Używać ścisłej gramatyki i jawnego błędu. |
| Średni | Odczyt grupowy zainstalowanej biblioteki Adafruit zwraca wartość bez informacji o powodzeniu. | Błąd I²C może wyglądać jak same nieaktywne wejścia. Potrzebny sprawdzany wynik operacji, licznik błędów i stan awarii czujników. |

Ostatni punkt sprawdzono w lokalnych bibliotekach
`Adafruit_MCP23017_Arduino_Library` i `Adafruit_BusIO`: `readGPIOAB()` zwęża
wynik `GPIO.read()` do 16 bitów, a `Adafruit_BusIO_Register::read()` zwraca
`0xFFFFFFFF` przy błędzie. W efekcie `0xFFFF` nie rozróżnia braku naciśnięć
od nieudanego odczytu. Dotyczy to również części wcześniejszego odczytu pinów.

## Co daje ograniczenie skanowania

| Wariant | Odczyty wierszy przy pełnym przebiegu bez naciśnięć | Pozostałe koszty |
|---|---:|---|
| Pierwotny szkic | do 600 pojedynczych odczytów | przełączanie kolumn, czas ustalania sygnału, filtr styków |
| Przygotowane `bulk_rows_v2` | 40 odczytów grupowych | nadal 60 wywołań `digitalWrite` dla pustej planszy |
| Proponowany odczyt −/+ /✓ w kolumnie 19 | 1 odczyt ekspandera obejmującego te wiersze | aktywacja/przywrócenie jednej kolumny, filtr styków, odczyty tła |
| Proponowany ruch po dużym obszarze | zależy od aktywnych kolumn i banków wierszy, do 40 | mniejsza oszczędność niż dla samego panelu |

To **liczby operacji wynikające z kodu**, nie pomiar szybkości urządzenia.
`digitalWrite` użytej biblioteki wykonuje odczyt i zapis rejestru. Przy polu
w ostatniej kolumnie obecny szybki szkic wykonuje nawet 79 takich wywołań:
20 na początku, 38 dla wcześniejszych kolumn, 1 aktywację i 20 przy powrocie.

Ograniczenie liczby wierszy w tym samym ekspanderze zwykle nie oszczędza
kolejnego odczytu — rejestr już zawiera stan całej grupy. Maska pomaga
przede wszystkim ominąć całe kolumny i niewykorzystywane ekspandery.
Nie zaczynałbym od skracania filtra 25 ms ani podnoszenia zegara I²C.

## Rozważane warianty wykrywania niewłaściwego pola (historyczne)

| Tryb | Zaleta | Ograniczenie |
|---|---|---|
| Tylko aktywne pola | Najmniej pracy, szybki panel | Poza obserwowanymi kolumnami brak informacji o dotknięciu |
| Pełna plansza | Można klasyfikować każde wykryte dotknięcie | Dłuższy przebieg niezależnie od liczby aktywnych pól |
| Aktywne pola szybko + reszta w tle | Szybka obsługa przycisków i diagnostyka reszty | Krótkie dotknięcie pola tła może zostać pominięte |

Pierwotna rekomendacja audytu wskazywała trzeci wariant; po rozmowie wybrano
pierwszy. Pełny skan pozostaje jawnie uruchamianą diagnostyką.
W aktywnej kolumnie dodatkowe wiersze z już odczytanego
ekspandera są dostępne bez osobnego odczytu. Pozostałe banki i kolumny
trzeba jednak naprawdę odczytać — nie ma sposobu, aby zagwarantować
wykrycie dotknięcia nieobserwowanego miejsca.

Praktyczny harmonogram: przebieg aktywnych kolumn, następnie mały fragment
tła, znów aktywne kolumny. Nie wykonywać dużego pełnego przebiegu tła naraz,
bo powodowałby okresowe przerwy w obsłudze przycisków. Częstotliwość dobrać
z pomiarów czasu pętli; roboczy cel całego obchodu tła to 100–200 ms,
nie gwarancja przed pomiarem. Przy wielu aktywnych kolumnach przejść na
jeden wspólny przebieg bez podwójnego odczytywania tych samych pól.

`rejected_press` powinno zawierać pole i kontekst. Przykładowy komunikat UI:
„To pole jest teraz nieaktywne — wybierz podświetlone”. Zdarzenie nie kończy
skanu, nie trafia do rozstrzygania akcji i nie wymusza STOP/SCAN.
Raportować zbocze naciśnięcia raz, po filtrowaniu, z limitem powtarzanych
powiadomień. Przytrzymane złe pole nie powinno zagłuszać dobrego przycisku.

Jeżeli wymaganiem będzie wykrycie każdego krótkiego błędnego naciśnięcia,
trzeba ustalić minimalny czas dotknięcia i odpowiednio szybko skanować całość.
Przerwania ekspanderów można rozważyć później, po sprawdzeniu rzeczywistego
okablowania; same nie identyfikują pola matrycy bez odczytu kolumn.

## Pierwotny szkic kontraktu v2 (zastąpiony osobną specyfikacją)

Zostawiłbym czytelne wiadomości tekstowe zakończone znakiem nowej linii,
z ograniczoną długością i ścisłą walidacją. JSON Lines jest wygodny dla
diagnostyki, ale jego parser na ESP musi mieć stały budżet pamięci.
Protokół binarny nie jest pierwszym krokiem: obecny główny koszt to skanowanie,
przełączanie kontekstów i transport LED, nie rozmiar krótkiego `press`.

Odpowiedzi v2 powinny zawierać wersję i identyfikator uruchomienia ESP
`boot_id`. Po HELLO komendy wskazują poznany `boot_id` i identyfikator
połączenia klienta. Komendy dostają `request_id`,
konteksty wejścia `context_id`, a zdarzenia monotoniczny `event_seq`.
Nie należy utożsamiać tych trzech liczników z jedną rewizją całego ekranu.

| Komenda/zdarzenie | Znaczenie |
|---|---|
| `HELLO` / `hello` | Wersja firmware, możliwości, rozmiar, mapa pinów, `boot_id`, gotowość czujników |
| `ARM` / `armed` | Atomowo przyjęta maska, kontekst i tryb skanu; odpowiedź potwierdza konkretne żądanie |
| `input_ready` | Wejścia gotowe po wymaganym zwolnieniu styków; `armed` nie musi jeszcze tego oznaczać |
| `press` | Wykryte poprawne pole, ID kontekstu, numer zdarzenia i czas urządzenia |
| `rejected_press` | Wykryte nieaktywne pole; skan trwa dalej |
| `ACK_EVENT` | Odbiór zdarzenia przez transport hosta; nie oznacza rozstrzygnięcia akcji gry |
| `STOP` / `stopped` | Zatrzymanie wskazanego kontekstu; ponowienie jest bezpieczne, stary STOP nie zatrzymuje nowego kontekstu |
| `status` / `fault` | Stan skanera, błędy I²C, przytrzymane pola, czas przebiegu i zapełnienie bufora |

Maska może być zapisana jako 20 liczb 30-bitowych: jedna na kolumnę.
W RAM wygodnie zajmuje 20×32 bity = 80 bajtów; sam ciąg HEX ma 160 znaków.
Dla rzutów można przesyłać rzadką listę tylko aktywnych kolumn, np.
`[[19,"0000000e"]]` oznacza wiersze 1, 2 i 3. Jest to maska przykładowa;
źródłem ma być aktualna lista `BoardScanTarget.positions`, nie stała w ESP.

Maskę i pozostałe parametry należy zweryfikować w całości przed zastosowaniem.
Jawnie ustalić: pustą maskę, nieobsługiwaną wersję, nadmiarowy wiersz/kolumnę,
limit długości i zachowanie po urwaniu ramki. Po błędnym ARM wejście powinno
pozostać zatrzymane z odpowiedzią błędu, aby host nie pomylił starego menu
z nowym. Przekroczenie limitu oznacza odrzucenie reszty linii aż do LF,
a nie próbę wykonania jej końcówki.

Okresowy status, np. co 1 s, pozwoli sprawdzać urządzenie bez resetowania
skanu. Brak statusu powinien najpierw uruchomić ograniczone sprawdzenie
łączności, a dopiero potem odzyskiwanie połączenia. Termin oczekiwania na
gracza pozostaje niezależny. Nowy `boot_id` unieważnia stare maski i zdarzenia;
po restarcie potrzebne jest ponowne jawne uzbrojenie właściwego kontekstu.
Żywotność odświeża tylko poprawna wiadomość bieżącego urządzenia, nie dowolny
tekst otrzymany z portu, jak w obecnej pętli odczytu.

Komenda o tym samym ID i tej samej treści powinna zwracać poprzednie
potwierdzenie bez zerowania filtrowania styków. Ten sam ID z inną treścią
jest błędem. Bufor zdarzeń i ponawianie muszą być ograniczone; przepełnienie
ma dawać jawny błąd, a nie ciche gubienie kliknięć. Deduplikacja zdarzeń
dotyczy pary `boot_id,event_seq` w ramach połączenia. Nie odtwarzać starych
kliknięć jako nowych akcji po restarcie gry.

## Ciągłe wejście i licznik kości

Pierwsze wdrożenie może zachować API „czekaj na jeden poprawny wybór”, już
z maską, ID, statusem i odrzucaniem złego pola bez zatrzymania skanu.
Pozwoli to ograniczyć zakres zmian w aplikacji.

Następnie warto dodać ciągłe raportowanie naciśnięć/zwolnień dla jednego
kontekstu kości. Wtedy zmiana 10→11 nie wymaga zatrzymania ESP i ponownego
SCAN po odpowiedzi przeglądarki. Skaner powinien pracować również podczas
przesyłania statusu i oczekiwania na potwierdzenie odbioru zdarzenia.

Kontekst pozostaje ten sam przy zmianach liczby dla tej samej kości, ale
zmienia się przy podsumowaniu, kolejnej kości lub bohaterze. Seria szybkich
plusów może być kolejką tylko w tym kontekście. Kliknięcia sprzed ✓ nie mogą
podnieść wyniku następnej kości. Zmiana maski na granicy 1/20 wymaga osobnego
ID aktualizacji; nie należy omijać walidacji po stronie aplikacji.

Potrzebny będzie jeden właściciel odczytu portu po stronie Pythona, kolejka
zdarzeń z limitami i serializacja komend. Nie tworzyć osobnego czytnika
portu dla każdego żądania Flask. Nie dodawać automatycznego powtarzania
przytrzymanego „+” bez oddzielnej decyzji o ergonomii.

## Pozostałe granice aplikacji

- `board/` powinno obsługiwać protokół, maski, zgodność wersji i transport.
  Adapter w `src/dnd_board_game/hardware/` przekazuje kontekst i zdarzenia;
  reguły gry pozostają w obecnych modułach.
- Simulator musi odtwarzać ID, błędne pola, opóźnione odpowiedzi, anulowanie
  i restart. Obecnie używa własnego HTTP i współrzędnych 1-based, podczas
  gdy USB zwraca 0-based; normalizacja ma pozostać na granicy transportu.
- WLED to oddzielna ścieżka. Odczyt USB nie powinien zatrzymywać się na
  wysłaniu ramki LED. Potrzebne są spójne wersje maski i podświetlenia oraz
  jawny stan gotowości, aby nie zachęcać do klikania nieuzbrojonych pól.
- Jeśli ramki LED trafią do kolejki, zwykłe podświetlenia można zastępować
  nowszymi. Animacje wymagają osobnej polityki — nie wolno bez rozróżnienia
  usuwać dowolnych ramek efektu.
- Dla wielu styków ustalić zachowanie. Obecny wybór pierwszego pola
  nie jest obsługą multitouch. Ghosting i elektryczne skutki kilku zwartych
  pól wymagają znajomości fizycznej matrycy, nie tylko zmiany protokołu.

## Sprawdzenie ustaleń

Wykonano bez urządzenia:

1. Kompilacja i wykonanie aktualnego parsera ESP w małym programie C++:
   `NOTPING` daje `pong`, `S C A N` uzbraja skan, a linia 65 znaków `X`
   zakończona `SCAN\n` również uzbraja skan. To potwierdza problem parsera
   i odzyskiwania ramki po przepełnieniu.
2. Symulowany port Python: 10 s ciszy wywołuje `_BoardScanIdleTimeout`,
   mimo większego limitu oczekiwania na gracza.
3. Wadliwe współrzędne `col=1.9,row=true` stają się `(1,1)`;
   pusta lista akceptowanych pól także przepuszcza wynik.
4. Backend rzucający `TypeError` jest wywoływany ponownie:
   pierwszy raz z `timeout_s=3`, drugi z `timeout_s=None`.
5. Istniejące testy skanera C++ oraz backendów USB i ponownego uzbrajania
   uruchamiane pojedynczo przez `scripts/safe_pytest.sh`.

Przykłady 1–4 są kontrolowanymi reprodukcjami z kodu, nie zarejestrowanymi
awariami fizycznej planszy. Dotychczasowe testy nie pokrywają całego parsera,
schematu wiadomości, utraty odpowiedzi ani weryfikacji ID, więc ich poprawny
wynik nie obala tych ustaleń. Nie zmieniano runtime ani firmware w tym audycie.

## Pierwotna kolejność wdrożenia (aktualna w specyfikacji v2)

1. **Odporność obecnego połączenia:** walidacja odpowiedzi i sygnatur,
   ograniczony parser, wykrywanie faktycznej gotowości, sensowne sprawdzanie
   żywotności i diagnostyka błędów. Dodać testy reprodukujące wskazane przypadki.
2. **Negocjowany protokół v2:** ID, maski kolumn/wierszy, potwierdzenie
   uzbrojenia, status i `rejected_press`. Stary firmware obsługiwać wyłącznie
   jawnie rozpoznaną ścieżką v1; nie wysyłać mu długich ramek v2 na próbę.
3. **Skaner:** aktywne kolumny, ograniczenie zapisów, per-field release,
   odczyt tła i sprawdzanie I²C. Testować wszystkie maski brzegowe, stare
   naciśnięcia i jednoczesne styki w symulatorze oraz na urządzeniu.
4. **Płynność całej aplikacji:** ciągłe wejście w obrębie kości, pojedynczy
   czytnik portu, ograniczone kolejki i uniezależnienie USB od WLED.
5. **Pomiar przy stole:** czasy pełnego i aktywnego przebiegu, detekcji,
   wysłania/odbioru zdarzenia, potwierdzenia UI i LED; p50/p95/max,
   szybkie −/+, ✓, błąd pola, przytrzymanie, 30 s namysłu i odłączenie USB.

W pierwszym etapie wydajnościowym największy sens ma panel inicjatywy:
ma małą, jednoznaczną maskę i łatwo sprawdzić, czy każde osobne naciśnięcie
daje dokładnie jedną zmianę licznika. Potem ruch, cele, setup i menu akcji.

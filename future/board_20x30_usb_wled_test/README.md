# Skaner planszy ESP32 — wyłącznie protokół v2

Aktualna wersja: **`board_scan_protocol_v2_2`**, protokół **`board_scan_usb_v2`**.
Aplikacja i firmware obsługują maskowane wejście single/stream, bez zgodności v1.
Raport wgrania i sprawdzenia: [wdrożenie](../../docs/BOARD_FIRMWARE_DEPLOYMENT.md).

## Wgranie przez Arduino IDE

Gotowa paczka lokalna: `dist/board_scanner_v2.zip` w katalogu projektu.
Rozpakuj ją w całości i otwórz **`board_scanner_v2/board_scanner_v2.ino`**.
W tym samym folderze muszą zostać trzy pliki `.h`; IDE pokaże je jako zakładki.
Nie kopiuj samego pliku `.ino` do pustego szkicu.

1. Zamknij grę i inne programy korzystające z portu planszy.
2. Wybierz dotychczasową płytkę i jej port w Arduino IDE. Szkic sprawdzono
   dla **ESP32 Dev Module** (`esp32:esp32:esp32`), core Espressif **3.3.7**.
3. Kliknij Wgraj. Nie trzeba instalować Adafruit ani ArduinoJson: szkic
   używa wyłącznie bibliotek wbudowanych w core ESP32.
4. Otwórz monitor portu z prędkością **115200**, zakończenie linii **Newline**.
   Wyślij `PING`. Odpowiedź powinna zawierać
   `"firmware":"board_scan_protocol_v2_2"` i `"ready":true`.
5. Zamknij monitor przed uruchomieniem gry lub programu testowego.

Pliki źródłowe w repozytorium:

- `esp32_board_scan_trigger_test.ino` — setup, USB i ograniczona kolejka zapisu;
- `board_protocol_v2.h` — sesje, konteksty, debounce, kolejki i protokół v2;
- `board_json.h` — parser komend ze stałym budżetem pamięci;
- `board_mcp_io.h` — sprawdzane odczyty/zapisy MCP23017 i maskowane skanowanie.

## Mapowanie sprzętu

Zachowane z poprzedniego szkicu: SDA **21**, SCL **22**, I²C **400 kHz**.
MCP23017 w trybie BANK=0 i SEQOP=0:

| Ekspander | Podłączenie |
|---|---|
| 0x20 | Wiersze 0–15 na pinach 0–15 |
| 0x21 | Wiersze 16–29 na pinach 0–13 |
| 0x22 | Kolumny 0–15 na pinach 0–15 |
| 0x23 | Kolumny 16–19 na pinach 0–3 |

Wejścia mają pull-up, wybrana kolumna jest aktywna stanem niskim. Nowy sterownik
zachowuje te poziomy i mapowanie. Błędy I²C są sprawdzane także przy zapisie;
nieudany odczyt nie może zostać uznany za zwolnienie przycisków.
`ready:false` oznacza, że trzeba sprawdzić inicjalizację/okablowanie MCP.

## Co działa w obecnej grze

`board/serial_v2.py` ma jednego właściciela USB, kolejkę naciśnięć,
ACK, deduplikację i PING niezależny od oczekiwania gracza. Aplikacja przesyła
wyłącznie legalne pola. Wybory akcji działają w single, edycja kości w stream.
Kolejne +/− tej samej kości nie wysyłają SET_INPUT; ✓ i powrót kończą kontekst
na ESP. Zmiana ekranu anuluje poprzednie wejście. Nieaktywne pola są ignorowane.

Uruchom ponownie aplikację po aktualizacji kodu. Stary firmware powoduje
błąd wersji, bez automatycznego przejścia na v1. Do testów przy stole:
start scenariusza/areny, wybór akcji, kilka osobnych szybkich +/−, ✓,
następna kość i mieszane użycie ekranu oraz planszy.

## Próba v2 bez gry

Z katalogu projektu, przy zamkniętej grze i monitorze portu:

```bash
./.venv/bin/python future/board_20x30_usb_wled_test/protocol_v2_probe.py --port /dev/ttyUSB0
```

Podaj rzeczywisty port, np. `/dev/ttyUSB0`, `/dev/ttyACM0` lub `COM3`.
Program używa istniejącej zależności projektu `pyserial`.

Aktywne są tylko **(19,3) −, (19,2) +, (19,1) ✓**. Po zwolnieniu przycisków
każde osobne +/− powinno zmienić próbny wynik raz. Pozostałe pola są ignorowane.
✓ kończy test od razu na ESP. Program sam wysyła HELLO, ACK, PING i końcowy
STOP. Domyślnie kończy się także po 60 s; `--duration 120` wydłuża próbę.

Pełna maska do sprawdzenia pojedynczego pola:

```bash
./.venv/bin/python future/board_20x30_usb_wled_test/protocol_v2_probe.py --port /dev/ttyUSB0 --full
```

Nie ma automatycznego powtarzania przytrzymanego przycisku ani multitouch.
Kilka aktywnych styków wymaga zwolnienia, zamiast wybierać arbitralnie pierwszy.
Przytrzymane aktywne pola są raportowane w statusie. Fizyczny ghosting matrycy
pozostaje do sprawdzenia na urządzeniu.

## Protokół i walidacja

Kontrakt: [BOARD_SCAN_PROTOCOL_V2.md](../../docs/BOARD_SCAN_PROTOCOL_V2.md).
JSON Lines, 2048 bajtów, ścisły podzbiór JSON komend, uint32 bez konwersji bool
lub ułamków, bez escape w napisach. Przepełniona/urwana linia jest odrzucana
w całości. Ponowienie komendy musi zachować identyczne bajty.

V2: SET_INPUT single/stream, maska finish, ID uruchomienia/sesji/kontekstu,
32 zdarzenia z ACK i retransmisją, filtrowanie naciśnięcia i zwolnienia 25 ms.
Brak ACK przez 2 s daje fault. Brak komendy/ACK hosta przez 5 s zamyka sesję;
PING hosta co 1 s utrzymuje ją bez naciskania. Status zawiera także `scan_us`
i `scan_max_us`. Dokładny tekstowy PING zwraca wyłącznie info v2.

Wyjście USB ma bufor 4096 bajtów i wysyła tylko tyle, ile mieści UART.
Brak miejsca nie powoduje cichego zgubienia zdarzenia v2. Skan czeka na
wysłanie potwierdzenia ustawienia kontekstu, zanim przyjmie jego pierwsze wejście.

Testy bez podłączania urządzenia:

```bash
scripts/safe_pytest.sh --timeout 60 tests/hardware/test_firmware_scan.py
scripts/safe_pytest.sh --timeout 60 tests/hardware/test_serial_v2_transport.py
scripts/safe_pytest.sh --timeout 60 tests/test_connection_backends.py
```

Test C++ wykonuje produkcyjny parser, kontroler i sterownik MCP z symulowaną
magistralą oraz kontrolą undefined behavior. Sprawdza wszystkie 600 pól,
maski, filtrowanie styków, konteksty, ACK, utratę hosta i błędy I²C. Testy
obejmują też produkcyjny transport Python połączony z tym samym kontrolerem C++:
ciągłe wejście, zakończenie kości, anulowanie, heartbeat, błędne ramki i awarie.
Pomiary fizycznego naciskania pozostają do wykonania.

Kompilacja ESP32 Dev Module, core 3.3.7: **313 036 bajtów flash,
39 764 bajty zmiennych globalnych RAM**.

## Test USB → WLED (v2)

`button_to_led_test.py` używa produkcyjnego transportu v2. Odbiera pojedyncze
pole po USB i zapala odpowiadającą mu diodę przez osobne połączenie WLED.
`--dry-run` sprawdza USB bez sterowania LED.
Poniższe ustawienia dotyczą wyłącznie testu, nie firmware skanera.

## Zalozone mapowanie LED

- plansza ma `20` kolumn i `30` wierszy
- LED `0` jest na polu `(0,0)`
- LED `29` jest na polu `(0,29)`
- LED `30` to LED nawrotki po kolumnie `0`
- LED `31` jest na polu `(1,29)`
- dalej idzie zygzak po calej planszy
- lacznie: `600` LED od pol planszy + `20` LED nawrotek = `620`

Formula w skrypcie:

- parzysta kolumna: `led = col * 31 + row`
- nieparzysta kolumna: `led = col * 31 + (29 - row)`

## Wymagania

Najwygodniej uruchomic ze wspolnego venv projektu:

```bash
./.venv/bin/python -m pip install pyserial requests
```

## Uruchomienie

```bash
./.venv/bin/python future/board_20x30_usb_wled_test/button_to_led_test.py --wled http://192.168.0.50
```

Jesli autodetekcja portu nie trafi:

```bash
./.venv/bin/python future/board_20x30_usb_wled_test/button_to_led_test.py --port /dev/ttyUSB0 --wled http://192.168.0.50
```

Przydatne opcje:

```bash
--color FF0000
--brightness 180
--dry-run
```

## Co zobaczysz

Po nacisnieciu pola skrypt wypisze cos w stylu:

```text
PRESS col=01 row=29 -> led=031
```

I zapali ten LED przez WLED.

## Uwaga o WLED

- segment `0` powinien obejmowac caly pasek `620` LED
- skrypt steruje diodami przez `POST /json/state`
- przy wyjściu skrypt gasi testowany zakres LED (poza `--dry-run`)

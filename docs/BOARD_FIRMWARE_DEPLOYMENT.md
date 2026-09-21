# Wgranie firmware skanera — 2026-09-10

## Aktualizacja portu — 2026-09-21

Po ponownym podłączeniu system przypisał CP2102 `/dev/ttyUSB1`; stary wpis
`/dev/ttyUSB0` powodował błąd otwarcia. Zgodnie z wyborem użytkownika
`board/config.json` ma teraz `hardware.serial_port: ""`: aplikacja wyszukuje
planszę we wszystkich dostępnych portach i zatrzymuje się po poprawnej odpowiedzi
protokołu v2 z właściwym mapowaniem i gotowymi czujnikami. Porty USB są sprawdzane
w pierwszej kolejności. Budżet oczekiwania na odpowiedź jednego portu określa
`probe_timeout_s` (domyślnie 6 s). Błąd lub niezgodna odpowiedź jednego portu
nie przerywają dalszego wyszukiwania. Przy ponownym połączeniu lista urządzeń
jest odczytywana od nowa; UI ponawia nieudane próby. Numer `ttyUSB` nie jest
zapisywany jako wymuszone ustawienie.

Po zmianie konfiguracji uruchom aplikację ponownie. Opcjonalny niepusty
`hardware.serial_port` lub `BOARD_SERIAL_PORT` nadal wymusza konkretny port;
dla automatycznego wyszukiwania pozostaw pole puste i usuń tę zmienną środowiskową.

Sprawdzono prawdziwe urządzenie przez `_open_serial_probe` i `SerialV2`:
firmware `board_scan_protocol_v2_2`, HELLO poprawne, PING/status `idle`,
`ready: true`, `i2c_errors: 0`. Próba zwolniła port i nie zmieniała firmware,
WLED ani stanu rozgrywki. Poniższe nazwy `/dev/ttyUSB0` opisują wcześniejsze wdrożenie.

## Aktualny stan: v2 bez zgodności v1

Na życzenie użytkownika aplikację i firmware przeniesiono wyłącznie na v2.
Na tej samej płytce ESP32-D0WD-V3 / 4 MB, `/dev/ttyUSB0`, wgrano
**`board_scan_protocol_v2_2`**. Usunięto obsługę SCAN/STOP v1 oraz odpowiedź
pong v1. Dokładny tekstowy PING pozostał jako wykrywanie info v2.

Kompilacja: ESP32 Dev Module, core 3.3.7, 313 036 bajtów flash,
39 764 bajty globalnego RAM. Zapis jak poprzednio: esptool 5.1.0,
ROM `--no-stub`, baud 115200, DIO 80 MHz / 4 MB, cztery standardowe obszary.
Każdy zapis zakończył się `Hash of data verified`, następnie reset ESP.
SHA-256 aplikacji: `39a02099d5284404bb0056af951229970dd388a6489f7fe0868a6fc9ec84d3d6`.

Sprawdzenie po zapisie użyło **produkcyjnego kodu aplikacji**:
`board.connection._open_serial_probe` oraz `board.serial_v2.SerialV2`.

- Info i HELLO: v2_2, poprawne mapowanie, czujniki gotowe.
- SET_INPUT stream: (19,3) −, (19,2) +, (19,1) ✓, finish na (19,1).
- 12 s bez naciskania: 12 potwierdzonych PING/status, stan scanning,
  zero błędów I²C, zero press, heartbeat utrzymywał sesję.
- `scan_us` 707–731 µs, `scan_max_us` 741 µs. To czas przebiegu odczytu,
  bez filtra 25 ms, USB, obsługi gry i LED.
- STOP potwierdził idle, port zamknięto i pozostawiono dostępny dla gry v2.

Nie wykonywano fizycznych naciśnięć ani pełnej rozgrywki. Użytkownik sprawdzi
scenariusz i arenę po ponownym uruchomieniu aplikacji. WLED nie był zmieniany
przez tę próbę USB.

Artefakty lokalne: `dist/board_scanner_v2/upload_v2_2.log`,
`dist/board_scanner_v2/device_verification_v2_2.json`, `binaries/` w tym katalogu
oraz aktualna paczka `dist/board_scanner_v2.zip`. Poprzednią paczkę źródeł
zachowano jako `dist/board_scanner_v2_1.zip`.

## Walidacja aplikacji i firmware v2_2

Małe, sekwencyjne uruchomienia przez `scripts/safe_pytest.sh --timeout 60`:

| Plik testów | Wynik |
|---|---:|
| hardware/test_firmware_scan.py | 39 |
| hardware/test_serial_v2_transport.py | 12 |
| test_connection_backends.py | 15 |
| test_connection_class.py | 5 |
| unit/test_board_scan_rearming.py | 1 |
| unit/test_initiative_panel.py | 10 |
| unit/test_board_v2_game_flow.py | 3 |
| unit/test_board_scan_scheduling.py (Chrome) | 2 |
| unit/test_board_panel_runtime.py | 23 |
| unit/test_encounter_setup_panel.py | 9 |
| unit/test_board_connection_startup.py | 3 |
| unit/test_exploration_ui_app.py — wybór testów skanu | 7 |
| unit/test_request_timing.py | 1 |
| unit/test_led_feedback.py | 13 |

Łącznie 143 różne testy przeszły; nie uruchamiano całego zestawu projektu.
Wybór z exploration_ui_app: `(board_scan or revisioned_automatic_board) and
not combat_turn_controls`. W szerszym wyborze pozostała wcześniejsza
niezgodność `test_exploration_ui_combat_turn_controls_remain_available_during_board_scan`:
asercja wymaga tekstu „Atak został już rozstrzygnięty”, nieobecnego także
w interfejsie z HEAD. Nie zmieniano treści gry w ramach migracji USB.

## Historia: wcześniejsze wgranie v2_1 z v1

Poniżej zapis wcześniejszego wdrożenia; **nie opisuje aktualnej wersji**.

Na polecenie użytkownika wgrano `board_scan_protocol_v2_1` do podłączonej
planszy. Port `/dev/ttyUSB0`, most CP2102, ESP32-D0WD-V3 rev. 3.1, flash 4 MB.
Przed zapisem urządzenie potwierdziło protokół v1 i wymiary 20×30; port był wolny.

## Zapis

Wsad skompilowany dla `esp32:esp32:esp32`, core 3.3.7. Narzędzie esptool 5.1.0,
tryb `--no-stub`, baud 115200, DIO, flash 80 MHz / 4 MB.
Zapisano bootloader 0x1000, tablicę partycji 0x8000, boot_app0 0xe000 i aplikację
0x10000. Każdy z czterech bloków zakończył się `Hash of data verified`.
Po zapisie urządzenie zrestartowano i poprawnie uruchomiło nowy firmware.

SHA-256 pliku aplikacji przed zapisem:
`7547ce5fcea34c689d4895fce84c8b2daa0fdca25811d69a1e4ce70d3d68f7d3`.

Nie uzyskano kopii poprzedniego firmware. Próby dużych odczytów, zarówno przez
stub, jak i ROM przy obniżonych prędkościach, kończyły się błędami transmisji.
Udał się tylko diagnostyczny odczyt 4096 bajtów bootloadera. Nie traktować go
jako kopii umożliwiającej odtworzenie starego wsadu. Zapis przez ROM oraz
weryfikacja jego sum zakończyły się poprawnie. Przyczyna błędów dużego odczytu
pozostaje nieustalona; nie stanowią same w sobie dowodu awarii kabli lub czujników.

## Sprawdzenie na urządzeniu

- Odpowiedź `hello`: właściwe firmware, mapowanie 20×30 i `ready:true`.
- SET_INPUT: aktywny panel (19,1), (19,2), (19,3), tryb stream i finish na ✓.
- Przez 12 sekund 11 potwierdzonych PING/status: stan scanning,
  `i2c_errors:0`, brak przytrzymanych pól i brak zdarzeń naciśnięć.
- Raportowane `scan_us`: 711–739 µs, `scan_max_us`: 754 µs.
- STOP potwierdził idle. Po wygaśnięciu sesji v2 tekstowy PING dał poprawny
  `pong` v1, `ready:true`, `armed:false`.
- Port zamknięto po weryfikacji; urządzenie pozostawiono dostępne dla gry v1.

Nie wykonywano fizycznych naciśnięć ani rozgrywki. Czas przebiegu skanera
nie obejmuje filtra 25 ms, USB, aplikacji ani LED i nie jest pomiarem czasu
reakcji całego systemu. Adapter gry nadal korzysta z kompatybilności v1.

Lokalne artefakty, pomijane przez Git:
`dist/board_scanner_v2/upload.log`,
`dist/board_scanner_v2/device_verification.json`,
`dist/board_scanner_v2/binaries/` oraz paczka `dist/board_scanner_v2.zip`.
Testów jednostkowych nie powtarzano przy samym wgrywaniu; źródło wsadu było
już sprawdzone 40 testami firmware i 23 testami backendów przed kompilacją.

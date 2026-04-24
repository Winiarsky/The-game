# Test planszy 20x30: USB -> WLED

To jest odseparowany prototyp do sprawdzenia synchronizacji:

- PC wysyla do ESP komende `SCAN`
- ESP uzbraja pojedynczy skan i czeka na jedno nacisniecie
- ESP odsylka jeden event `press` po USB
- opcjonalnie moze odeslac event `cancel`, jesli skan zostal anulowany lokalnie
- skrypt odbiera `press`
- skrypt mapuje `(col,row)` na LED nowej planszy 20x30
- odpowiadajacy LED zapala sie przez WLED

Nie dotyka to obecnej integracji gry.

## Plik dla ESP

Roboczy szkic jest tutaj:

- [esp32_board_scan_trigger_test.ino](/home/winiar/Desktop/projects/boardgame/The%20game/The-game/future/board_20x30_usb_wled_test/esp32_board_scan_trigger_test.ino)

Obsluguje komendy po serialu:

- `PING`
- `STATUS`
- `SCAN`
- `STOP`

Backend gry rozumie teraz rowniez anulowanie skanu przez event JSON:

```json
{"protocol":"board_scan_usb_v1","event":"cancel"}
```

To pozwala dodac na ESP32 np. osobny przycisk anulowania albo lokalna logike timeoutu,
bez udawania klikniecia w pole planszy.

Docelowy przeplyw testu jest taki:

1. skrypt PC laczy sie z ESP
2. skrypt wysyla `SCAN`
3. ESP czeka na jedno poprawne nacisniecie
4. ESP wysyla `press`
5. skrypt zapala LED i od razu znow wysyla `SCAN`

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
--scan-command SCAN
--raw-serial
--dry-run
```

## Co zobaczysz

Po nacisnieciu pola skrypt wypisze cos w stylu:

```text
PRESS col=01 row=29 -> led=031 (turn_after_col=061)
```

I zapali ten LED przez WLED.

## Uwaga o WLED

- segment `0` powinien obejmowac caly pasek `620` LED
- skrypt steruje diodami przez `POST /json/state`
- przy starcie i przy wyjsciu skrypt gasi testowany zakres LED

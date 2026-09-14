# Opóźnienia wejścia planszy — 2026-09-10

Źródło: `data/session_observations/exploration_ui_d1d6dc684f.jsonl`,
11:33–11:35 czasu lokalnego (09:33–09:35 UTC), arena Garrana.

## Co widać w logu

- Po zatwierdzeniu ruchu i Postawy obronnej przeglądarka wysłała skany starej
  rewizji: zdarzenia 91 i 98. Oba nakładają się na przetwarzanie komendy gry.
- 20 wpisów `ui_board_feedback_slow`: transport LED 311–954 ms; mediana 475,5 ms.
  To statystyka tylko raportowanych wolnych aktualizacji, nie wszystkich ramek.
- Przy ruchu przygotowanie skanu zajmowało 31–40 ms, a czynności po odebraniu
  sygnału 63–96 ms. Te wartości nie tłumaczą wielosekundowego oczekiwania.
- Zdarzenie 95: 37,273 s oczekiwania na sygnał USB, potem 41 ms pracy aplikacji.
  Nie jest to pomiar czasu od dotknięcia: log nie zapisuje chwil każdego
  fizycznego naciśnięcia ani krótkich dotknięć niewykrytych przez firmware.
- Początek setupu zawiera też równoległe próby skanowania (11–13), odrzucone
  przez blokadę serwera, oraz nieudaną pierwszą próbę podłączenia (6).

## Poprawka

`ui/static/exploration.js` usuwa zaplanowany timer przed rozpoczęciem komendy
oraz przed synchronizacją panelu. Timer ponownie sprawdza aktualną rewizję,
stan zajętości, rejestrację panelu i istniejący skan tuż przed wysłaniem żądania.
Odpowiedź z przyciskiem narożnym najpierw trafia do obsługi przycisku; blok
kończący odczyt nie uruchamia wcześniej skanu starego menu. Stara odpowiedź
nie zeruje obietnicy ani flagi nowszego odczytu.

`board/connection.py` po poprawnym zdarzeniu `press` uzbraja kolejny skan
samym `SCAN`. Pomija techniczny `STOP` i stałe pauzy 80/120 ms. Początkowe
połączenie, anulowanie, odrzucone pole i odzyskiwanie połączenia zachowują
dotychczasową procedurę resetu. Usunięte pauzy nie są deklaracją identycznego
skrócenia czasu od fizycznego dotknięcia, ponieważ praca firmware i odbiór USB
mogą częściowo nakładać się na oczekiwanie klienta.

## Walidacja i granice

59 testów uruchamianych kolejno przez `scripts/safe_pytest.sh`:

- `tests/unit/test_board_scan_scheduling.py`: rzeczywisty Chrome, kontrolowane
  timery i opóźniona odpowiedź; blokada skanów przy komendzie, zmianie rewizji
  i synchronizacji panelu, kolejność obsługi ✓, ochrona nowszego żądania.
- `tests/unit/test_board_scan_rearming.py`: kolejny przycisk bez pauz i STOP,
  poprawne przywrócenie resetu po anulowaniu i odrzuceniu pola.
- `tests/test_connection_backends.py`, `tests/unit/test_board_panel_runtime.py`
  i `tests/unit/test_initiative_panel.py`: istniejące regresje transportu,
  anulowania, LED, menu siedmiu bohaterów, płatności i inicjatywy.

Chrome wymagał uruchomienia poza sandboxem, który blokuje start jego procesu;
test otwiera tylko lokalny plik i używa symulowanych odpowiedzi.

Nie sterowano fizyczną planszą ani WLED podczas weryfikacji. Źródło firmware
w `future/board_20x30_usb_wled_test/esp32_board_scan_trigger_test.ino` skanuje
pola osobnymi odczytami i po uzbrojeniu czeka na zwolnienie planszy. Może to
wpływać na krótkie naciśnięcia, ale wersja faktycznie wgrana do urządzenia
nie została potwierdzona. Dalszy pomiar powinien oddzielić ten czas od sieci WLED.

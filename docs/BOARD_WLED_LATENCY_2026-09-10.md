# Zastoje UI i potwierdzenie ataku Garrana po migracji USB v2

## Korekta: świecące ✓ bez reakcji podczas przygotowania areny

Ostatnia sesja `data/session_observations/exploration_ui_be3fc3a4ad.jsonl`,
2026-09-10, 21:27:05–21:27:21 UTC: automatyczny skan pierwszego kroku
przygotowania i ręczne ponowienie oczekiwały tylko pola (19,1). Oba kończyły
się po 5 s błędem potwierdzenia WLED, przed uruchomieniem wejścia ESP.
Brak zdarzeń `ui_board_scan_received`. Przed ponowieniem poprzednia ramka
LED była już potwierdzona, ale nowa ramka znów blokowała skan.

`_HardwareBackend.prepare_scan` uruchamia teraz wejście USB niezależnie
od potwierdzenia LED. Brak odpowiedzi HTTP nie dowodzi, że LED się nie
zapaliła. Anulowanie przed uzbrojeniem nadal odcina stary skan, a aktywny
odczyt zachowuje generację, maskę i kontekst USB. ACK poleceń USB nadal
obowiązuje. Pracownik LED ponawia najnowszą ramkę i osobno raportuje błędy;
nie zgłaszamy niepotwierdzonej ramki jako dostarczonej.

Ta korekta zastępuje opisane niżej wcześniejsze oczekiwanie na ACK LED
przed SET_INPUT. Nie zmienia firmware ani nie usuwa opóźnienia sieci WLED.
Ponowna próba fizycznego ✓ wymaga restartu aplikacji.

Walidacja korekty: `tests/unit/test_wled_output.py` — 12 testów, w tym
przejście dwóch kroków przygotowania areny przez automatyczny i ręczny skan
przy błędach WLED, odczyt przy zablokowanym HTTP oraz anulowanie starego skanu.
Dodatkowo `test_board_v2_game_flow.py` — 4, `test_connection_backends.py` — 15,
`test_encounter_setup_panel.py` — 9. Razem 40 testów przeszło, uruchamianych
kolejno przez `scripts/safe_pytest.sh --timeout 60`; `git diff --check` bez błędów.

## Wcześniejsza analiza i pierwsza poprawka

Źródło: data/session_observations/exploration_ui_c4636e91fa.jsonl,
2026-09-10, 13:50:52–13:52:30 czasu lokalnego (11:50:52–11:52:30 UTC).

## Ustalenia

Wybór kukły mieczem Garrana: odebrano pole (9,13) o 13:52:12.359,
zapisano podgląd celu o 13:52:12.365. Następnie transport LED trwał
2083 ms, do 13:52:14.448. Dopiero o 13:52:14.661 ruszył skan potwierdzenia.
Ramka w logu zawiera niebieskie ✓ na (19,1) oraz powrót na (19,0).
Nie jest to dowód fizycznego zapalenia diody: dawny log zapisywał plan,
a informacja o niepowodzeniu wysłania ginęła pomiędzy warstwami.

Po naciśnięciu ✓ o 13:52:21.341 aktualizacja LED zajęła kolejne 2365 ms.
Żądanie potwierdzenia ataku trwało 2427 ms, po nim rejestracja panelu kości
wymagała następnego wysłania LED (912 ms). UI czekało na te operacje.

W sesji jest 25 wpisów wolnych aktualizacji LED: 331–2365 ms,
mediana 909 ms. To statystyka zgłoszonych wolnych operacji, nie wszystkich
ramek. Nie zapisano ui_board_scan_error ani ui_board_scan_timeout.
Oczekiwanie na press obejmuje namysł gracza i nie mierzy czasu dotknięcia.

Odczyt diagnostyczny /json/info z rzeczywistego WLED podczas analizy:
trzy osobne połączenia 309/1269/1533 ms, następnie trzy żądania przez
requests.Session 1134/1015/921 ms. Odpowiedzi poprawne, wersja 16.0.1,
raportowany sygnał 82–90%. Mała próbka potwierdza aktualne opóźnienie HTTP;
nie rozstrzyga, czy odpowiada za nie radio, sieć, czy praca WLED.
Nie zmieniano konfiguracji urządzenia ani jego LED podczas pomiaru.

## Zmiana

- board/led_output.py: jeden pracownik HTTP, jedna najnowsza pełna ramka
  do dostarczenia, ograniczona pamięć i ponowienia nieudanej aktualnej ramki.
  Żądania już wysłanego nie przerywa; po nim wysyła najnowszy stan,
  pomijając zastąpione aktualizacje. Pośrednie klatki animacji mogą być
  pominięte przy wolnej transmisji; końcowe podświetlenie pozostaje aktualne.
- board/connection.py: gra zleca LED bez czekania na sieć. Przygotowany
  skan czeka na potwierdzenie bieżącej ramki poza blokadą sesji gry.
  Anulowanie budzi oczekiwanie i odcina późniejsze uzbrojenie starego menu.
  Odczyt USB i jego heartbeat działają niezależnie. Po 5 s oczekiwania
  na LED pojawia się jawny błąd; wysyłanie aktualnej ramki nadal się ponawia.
  HTTP 200 z treścią zgłaszającą błąd WLED nie potwierdza ramki.
- hardware/led_feedback.py: jawnie odrzucona ramka lub gaszenie nie trafia
  do pamięci ostatnio wysłanego obrazu. Zgłoszenie do pracownika oznacza
  przejęcie odpowiedzialności za dostarczenie, a nie ACK urządzenia.
- ui/exploration_app.py: stan i logi skanu zawierają rewizję żądanego
  podświetlenia, potwierdzoną rewizję, błąd oraz wynik/czas ostatniej próby.

Nie zmieniano protokołu USB ani firmware ESP32. Nie dodano zależności.
Potwierdzenie HTTP jest potwierdzeniem WLED, nie pomiarem optycznym LED.
Zmiana usuwa oczekiwanie sieciowe ze ścieżki odpowiedzi UI; nie usuwa
samego opóźnienia fizycznego podświetlenia. Po awarii nie pozostawia
identycznej, niewysłanej ramki trwale pominiętej przez pamięć adaptera.

## Walidacja

Testy wykonywane pojedynczymi plikami przez scripts/safe_pytest.sh --timeout 60:

- tests/unit/test_wled_output.py: 10, w tym wybór kukły mieczem Garrana
  przy celowo zablokowanym wysyłaniu LED; odpowiedź z ✓ i GET stanu nie
  czekają na WLED. Ponadto anulowanie, oczekiwanie przed SET_INPUT,
  pomijanie starych ramek, automatyczne ponowienie i błąd treści HTTP.
- tests/unit/test_led_feedback.py: 14, w tym brak zapamiętywania błędu
  jako wysłanego obrazu i ponowienie gaszenia.
- tests/test_connection_backends.py: 15.
- tests/test_connection_class.py: 5.
- tests/unit/test_board_panel_runtime.py: 23.
- tests/unit/test_board_v2_game_flow.py: 3.
- tests/unit/test_encounter_setup_panel.py: 9.
- tests/unit/test_request_timing.py: 1.

Łącznie 80 testów przeszło.

Ponowna fizyczna próba scenariusza/areny pozostaje do wykonania przez
użytkownika po restarcie aplikacji i odświeżeniu przeglądarki.

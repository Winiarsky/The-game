# The-game
Repo for e-board game project v2

## Symulator planszy

Do szybszego testowania logiki gry możesz użyć wbudowanej aplikacji webowej (15×20 pól), która odtwarza zachowanie metod `scan_board`, `set_leds` i `leds_off` klasy `Connection`.

1. Zainstaluj zależności: `pip install -r requirements.txt`.
2. Uruchom serwer: `python -m board.simulator.app`.
3. Wejdź w przeglądarce na `http://127.0.0.1:5000`.
4. W kodzie gry ustaw adres `Connection` na `http://127.0.0.1:5000` (np. `Connection(esp_ip="http://127.0.0.1:5000")` albo tymczasowo zmień `ESP_IP` w `board/consts.py`).

Na stronie zobaczysz podświetlenia wysłane przez `set_leds`, a każde kliknięcie pola zasymuluje odpowiedź `scan_board` (żądanie GET blokuje się do czasu kliknięcia). Przycisk `leds_off` w kodzie gry czyści całą tablicę.

W zakładce symulatora możesz także ustawić własne tło planszy (np. skan mapy scenariusza) przez wczytanie obrazu lub usunięcie go jednym kliknięciem.

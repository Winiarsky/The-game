# The-game
Repo for e-board game project v2

## Symulator planszy

Do szybszego testowania logiki gry możesz użyć wbudowanej aplikacji webowej (15×20 pól), która odtwarza zachowanie metod `scan_board`, `set_leds` i `leds_off` klasy `Connection`.

1. Zainstaluj zależności: `pip install -r requirements.txt`.
2. Uruchom serwer: `python -m board.simulator.app`.
3. Wejdź w przeglądarce na `http://127.0.0.1:5000`.
4. W kodzie gry ustaw adres `Connection` na `http://127.0.0.1:5000` (np. `Connection(esp_ip="http://127.0.0.1:5000")` albo tymczasowo zmień `ESP_IP` w `board/consts.py`).

Na stronie zobaczysz podświetlenia wysłane przez `set_leds`, a każde kliknięcie pola zasymuluje odpowiedź `scan_board` (żądanie GET blokuje się do czasu kliknięcia). Przycisk `leds_off` w kodzie gry czyści całą tablicę.

### Dodatkowe narzędzia symulatora

- **Tryby pracy** – włącz „Tryb planszy”, aby kliknięcia wysyłały zdarzenia do gry, lub „Tryb przesuwania figurek”, by swobodnie rozstawiać pionki bez wywołań HTTP.
- **Generator figurek** – w panelu „Figurki” dodasz żetony (litery + kolory), zaznaczysz je i ustawisz na polach w trybie przesuwania. Kliknięcie pola z figurką bez wybranej figurki zaznaczy ją, dzięki czemu łatwo ją przenieść.
- **Tło planszy** – ustaw własny obraz (np. mapę scenariusza) lub usuń go jednym kliknięciem.

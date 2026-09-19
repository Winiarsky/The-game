# Powtórzenie testu

Z katalogu repozytorium, przy zainstalowanym Chrome i dostępnych pakietach `requests` oraz `websocket-client`:

```bash
PYTHONPATH=src:. python scripts/mission_playtest_server.py \
  --serial-port /dev/ttyUSB0 --wled-url http://192.168.50.2
```

To prawdziwe sterowanie wskazaną planszą. Nie uruchamiać równocześnie drugiego serwera korzystającego z tego samego portu szeregowego. Serwer używa osobnego katalogu `/tmp/mission0-audit-runtime`; port aplikacji 8765, debugowanie Chrome 9223. Ctrl+C zwalnia sprzęt.

W drugim terminalu:

```bash
PYTHONPATH=scripts:src:. python scripts/playtest_mission_zero_parties.py p4
```

Dostępne składy: p3, p4, p5, p6. `--resume` wznawia **aktualny stan otwartej strony**, a nie odtwarza etapu z logu. Log i stan fizycznego symulatora kart znajdują się w `docs/playtests/2026-09-18-misja0/`. Przed nową niezależną sesją należy zachować/odłożyć poprzednie `pN-driver.json` i `pN-events.jsonl`; inaczej kontynuowany będzie stary generator i lista wykonanych kroków.

Sterownik celowo zatrzymuje się na nieobsłużonym kontekście. To pomoc do obserwowanych rozgrywek, nie kompletny autonomiczny gracz ani ogólny test regresji każdej zdolności. Zatrzymanie sterownika nie oznacza blokady gry. Przebieg z raportu obejmował także ręczną analizę DOM i zrzutów przez osobę prowadzącą audyt (agenta).

Nie porównywać czasu wykonania z długością sesji przy stole. Zapisy obejmują pauzy audytu, rozwijanie sterownika i oczekiwanie na fizyczną planszę. Inicjatywa AI i wyniki automatycznych działań silnika nie są objęte ziarnem symulatora kart/kości.

Skrypt odtwarza procedurę testu, nie gwarantuje bitowej powtarzalności historycznych wyników: pierwsze przebiegi zawierały poprawki sterownika, a P4 także wznowienie punktu kontrolnego po zamknięciu serwera. Dokładne wykonane rzuty i kolejność kart są zapisane w dziennikach zdarzeń.

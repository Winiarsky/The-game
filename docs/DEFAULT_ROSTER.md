# Domyślny roster postaci

Projekt zawiera 12 gotowych postaci 1. poziomu — po jednej dla każdej klasy.
Można je od razu wybrać w `Nowa gra` (maksymalnie pięć naraz).

| Postać | Build | Rola na start |
|---|---|---|
| Brakka | półork, barbarzyńca, wędrowiec | prosty frontliner; Szał i ciężka broń |
| Lorian | półelf, bard, artysta | wsparcie, leczenie i kontrola |
| Dagna | krasnolud wzgórzowy, kleryk Domeny Życia | opancerzony obrońca i uzdrowiciel |
| Sylwen | wysoki elf, druid | kontrola terenu, wsparcie i eksploracja |
| Garran | człowiek, wojownik | najbardziej przystępny tank z tarczą |
| Pim | niziołek lekkostopy, mnich | mobilny wojownik bez pancerza |
| Rhogar | smocze dziecię, paladyn | obrona drużyny, leczenie i smoczy oddech |
| Erynd | wysoki elf, łowca | zwiad i walka z dystansu |
| Mira | niziołek lekkostopy, łotrzyca | skradanie, narzędzia i Podstępny atak |
| Veyra | diabelstwo, zaklinacz o smoczej krwi | ofensywna magia i dobra obrona bez pancerza |
| Kael | półelf, czarnoksiężnik Piekielnego | ataki magiczne z dystansu i slot odnawiany po krótkim odpoczynku |
| Nimra | gnom skalny, czarodziejka | szeroki zestaw czarów kontroli i narzędzi |

## Instalacja

```bash
PYTHONPATH=src python scripts/install_default_roster.py
```

Instalator nie nadpisuje istniejących zapisów ani portretów. Definicje buildów
są w `src/dnd_board_game/character_creation/default_roster.py`, źródłowe
portrety w `assets/character_portraits/default_roster/`, a lokalne zapisy
trafiają do `data/characters/`.

## Kierunek graficzny

Portrety wygenerowano wbudowanym narzędziem `imagegen`. Wspólny prompt:
kwadratowy portret fantasy od klatki piersiowej, ręcznie malowany z komiksowym
konturem tuszem, klasyczny klimat papierowego RPG, ciemne ciepłe tło o fakturze
pergaminu, spójna skala i oświetlenie; bez tekstu, interfejsu, ramki, logo i
znaku wodnego. Dla każdej postaci podmieniono opis rasy, klasy, wyposażenia,
kolorystyki i krótkiego motywu magii.

## Zakres reguł

Buildy są zgodne z bazową progresją D&D 5e z 2014 roku. Paladyn i łowca nie
rzucają jeszcze czarów na 1. poziomie, druid nie ma jeszcze Dzikiego Kształtu,
a większość klas wybierze podklasę dopiero na 2. lub 3. poziomie. Nie są to
braki kart, tylko właściwa progresja poziomów.

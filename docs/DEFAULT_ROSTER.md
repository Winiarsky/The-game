# Domyślny roster postaci

Projekt przechowuje 12 szablonów klasowych, ale w `Nowa gra` dostępnych jest
siedmiu dopracowanych bohaterów 3. poziomu (maksymalnie pięciu naraz). Pięć
pozostałych szablonów 1. poziomu pozostaje ukrytym materiałem regresyjnym dla
kreatora i reguł, a nie częścią aktualnego rosteru gry.

| Postać | Build | Rola na start |
|---|---|---|
| Brakka | półork, barbarzyńca, wędrowiec | prosty frontliner; Szał i ciężka broń |
| Lorian | półelf, bard, artysta | kusza, wsparcie, rozmowa i kontrola |
| Dagna | krasnolud wzgórzowy, kleryk Domeny Życia | opancerzony obrońca i uzdrowiciel |
| Garran | człowiek, wojownik | najbardziej przystępny tank z tarczą |
| Erynd | wysoki elf, łowca | zwiad i walka z dystansu |
| Mira | niziołek lekkostopy, łotrzyca | ukrycie, flankowanie i Atak z cienia |
| Nimra | gnom skalny, czarodziejka | szeroki zestaw czarów kontroli i narzędzi |

## Instalacja

```bash
PYTHONPATH=src python scripts/install_default_roster.py
```

Instalator zachowuje postęp istniejących postaci na poziomie 3, ale migruje
starsze zapisy poziomu 1–2 do aktualnych buildów poziomu 3 i uzupełnia
idempotentną premię `+2` do głównego atrybutu. Nie nadpisuje portretów. Definicje buildów
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

Buildy bazują na progresji D&D 5e z 2014 roku, lecz siedem planszowych
archetypów ma jawne odstępstwa: start na poziomie 3, premię `+2` do głównego
atrybutu oraz stałe osobiste talie. Wszystkie karty w talii są dostępne od
startu; dalszy rozwój postaci zostanie zaprojektowany osobno.

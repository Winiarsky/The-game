# Teksty kart postaci i samouczka

Edytuj **`karty_postaci.json`**. To wspólne źródło opisów dla aplikacji,
mat postaci, zbiorczego PDF i lekcji samouczka. Nie edytuj wygenerowanych
HTML/PDF ani `source_snapshot.json`.

## Gdzie jest dany tekst

- `heroes.garran` (analogicznie `brakka`, `mira`, `dagna`, `lorian`, `nimra`, `erynd`):
  - `role`, `history`, `motivation`, `personal_goal`, `character_line` — postać;
  - `flaw.name`, `flaw.description` — skaza;
  - `actions.<id>.name`, `description` — nazwa i efekt akcji, wspólne dla gry i druku;
  - `actions.<id>.boosts.<id>` — nazwa/opis konkretnego podbicia w selektorze;
  - `actions.<id>.boost_summary` — zbiorczy opis podbić na karcie i w objaśnieniu akcji;
  - `passives.combat.<kolor>` — pasywy walki;
  - `passives.exploration.<kolor>` — pasywy eksploracji;
  - `tutorial.<id>` — narracja lekcji tej postaci.
- `tutorial.intro` — wstęp do samouczka;
- `tutorial.foundations.<id>` — nazwy i instrukcje wspólnych lekcji many;
- `tutorial.exploration_lessons.<id>` — nazwy i instrukcje ćwiczeń eksploracji;
- `tutorial.exploration_reminder`, `conditions`, `turn_reminders`,
  `mana_passive_reminder`, `common_keys` — wspólne objaśnienia w aplikacji;
- `equipment` — podpisy i opisy wycinanek sprzętu startowego;
- `player_aid` — cztery strony pomocnika na końcu zestawu;
- `keywords` — słowa i odmiany pogrubiane na wydruku.

Kolory: **C** czerwona, **B** biała, **Z** zielona, **F** czarna, **N** niebieska.
Zachowujemy istniejące identyfikatory; zmieniaj teksty, nie klucze bohaterów,
akcji, podbić, lekcji i kolorów.

## Pasywy

- `name`: nazwa (również na liście aktywnych pasywów).
- `when`: kiedy działa.
- `effect`: pełny efekt w aplikacji.
- `short`: krótki opis do druku — ograniczone miejsce obok kart many.
- `note`: dodatkowe objaśnienie.
- `stacking`: czy kolejne karty kumulują efekt.
- Opcjonalne `instruction`, `diagram`: potwierdzenie operacji i oznaczenie diagramu.

Pełny i krótki opis służą różnym układom, ale znajdują się obok siebie w tym
samym pliku. Przy zmianie znaczenia zaktualizuj oba. Nie trzeba osobno zmieniać
`label` w katalogach — aplikacja składa go z tych pól.

W opisach eksploracji używaj słowa „wpływ”. Aplikacja zamienia je na „postęp”
przy obiektach, a mata pokazuje „wpływ / postęp”.

## Po zapisaniu

Aplikacja odczytuje zmiany przy kolejnym odświeżeniu widoku/żądaniu. Istniejące
wpisy historii rozgrywki nie są przepisywane. Aby odnowić plik do druku,
uruchom z głównego katalogu projektu:

```sh
PYTHONPATH=src .venv/bin/python scripts/build_hero_mats.py
```

Wynik: `content/print/characters/bohaterowie_zestawy_startowe_A4.pdf`.
Generator sprawdza przepełnienia i wymiary przed opublikowaniem zestawu.

## Tekst a mechanika

Ten plik jest źródłem **treści**, nie skryptem efektów. Zmiana „+1” na „+2”
w opisie nie zwiększy premii naliczanej przez grę. PW, cechy, progi, spalanie,
runy, rodzaje pasywów i ich liczbowe efekty nadal pochodzą z reguł i katalogów
balansu; layout i bieżące instrukcje sterowania wynikają z kodu UI.
Fabuła Misji 0 i innych przygód pozostaje w folderach scenariuszy.

Dawne `mats_v2/copy.json`, `player_aid.json`, `keywords.json` oraz
`content/tutorials/walkthrough.json` przeniesiono tutaj i usunięto, aby nie
było kilku konkurujących plików do edycji. Historyczny prototyp Garrana nie
jest źródłem aktualnych zestawów.

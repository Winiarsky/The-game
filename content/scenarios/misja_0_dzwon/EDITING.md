# Edycja Misji 0

W tym folderze są teksty przygody, teksty używane przez aplikację, karty
bohaterów i materiały do druku. **Edytuj źródła, potem odbuduj PDF-y.**
HTML, PDF, podglądy PNG i `source_snapshot.json` są wynikami generatorów.
Bieżący UI przygotowujemy dla **laptopa** i sterowania fizyczną planszą;
nie ma osobnego zakresu wdrożenia mobilnego.

| Co chcesz zmienić | Źródło w tej paczce |
| --- | --- |
| Narracja, kwestie NPC, wyniki scen | `text/*.md`, przypisania w `text/index.json` |
| Podpisy i komunikaty nowego UI | `text/ui/navigation.json`, `common.json`, `confrontation.json`, `combat.json` |
| Etykiety scen, instrukcje i dziennik Misji 0 | `text/ui.json` |
| Przygotowanie wyposażenia: instrukcja planszy i przykład | `text/equipment_intro.md`; tytuł w `text/index.json`, przyciski w `text/ui.json` |
| Obecne moce v0.3, koszty, premie, skazy, pasywy i relacje run | `content/print/rune_relations_v03/catalog.json` w katalogu projektu |
| Historie i sprzęt bohaterów; wcześniejsze lekcje i opisy | `text/karty_postaci.json` |
| Obecna ściąga gry i PDF | `text/sciaga_relacje_v03.json`; tabela relacji pochodzi z katalogu |
| Rozkaz Nessy i pokwitowania Boruta | `text/handouts.json` |
| Nazwy, obrysy, podpisy i grafiki elementów mapy | `maps/cutouts.json` |
| Rozmieszczenie sceny i przygotowanie planszy | `maps/setup.json` |
| Przedmioty scenariusza i opis działania | `mechanics/items.json` |
| Profile spotkań i ustawienia walki | `mechanics/confrontations.json`, `mechanics/battle.json` |
| Nagrody i kolejne kroki przygody | pozostałe pliki `mechanics/` oraz `scenario.json` |

## Teksty UI i narracji

W `text/ui/` plik `navigation.json` opisuje start, drużynę, scenariusz i zapisy;
`common.json` — menu, dziennik, ściągę i wspólne komunikaty;
`confrontation.json` — rozmowy, dobór many, testy i pomoc;
`combat.json` — inicjatywę, akcje, cel i efekty walki. Zmieniaj wartości,
a identyfikatory kluczy pozostaw. Zachowaj pola w klamrach, np. `{hero}`,
`{count}` lub `{total}`: aplikacja wstawia tam bieżące dane.

`text/ui.json` pozostaje osobnym źródłem instrukcji konkretnych etapów Misji 0.
Pliki `text/*.md` zawierają narrację i dialogi; `text/index.json` przypisuje im
mówcę, tytuł i ilustrację. Zmiana tekstu nie powtarza nagrody ani działania.
Nowe teksty UI są odczytywane przy kolejnym żądaniu, bez budowania aplikacji.
Odśwież ekran, aby od razu zobaczyć poprawiony podpis strony startowej.

## Karty bohaterów — wspólne źródło gry i wydruków

Moce, pasywy, skazy i relacje run nowych walk znajdują się w
`content/print/rune_relations_v03/catalog.json` w katalogu projektu.
`scenarios/rune_relation_catalog.py` sprawdza koszty, warunki, graf
i słownik modyfikatorów przed rozpoczęciem gry. Nie wpisuj drugiej
definicji efektu do UI lub adaptera LED. Odbuduj karty przez
`scripts/build_rune_relations.py`, a dane mocka przez
`scripts/build_resonance_mock.py`.

`text/karty_postaci.json` pozostaje źródłem historii, sprzętu oraz starszych
lekcji i opisów używanych poza nową mechaniką walki.
Aplikacja i generatory odczytują ten sam plik przez `scenarios/character_text.py`.
Nie ma drugiej kopii w dawnym `content/characters/`.

- `heroes.garran` (analogicznie `brakka`, `mira`, `dagna`, `lorian`, `nimra`, `erynd`):
  - `role`, `history`, `motivation`, `personal_goal`, `character_line` — postać;
  - `flaw.name`, `flaw.description` — skaza;
  - `actions.<id>.name`, `description` — nazwa i efekt akcji;
  - `actions.<id>.boosts.<id>` — nazwa/opis konkretnego podbicia;
  - `actions.<id>.boost_summary` — zbiorczy opis podbić na karcie;
  - `passives.combat.<kolor>` i `passives.exploration.<kolor>` — pasywy;
  - `tutorial.<id>` — narracja lekcji bohatera.
- `equipment` — podpisy i opisy wycinanek sprzętu startowego.
- `tutorial` — wspólne lekcje i przypomnienia samouczka.
- `keywords` — słowa i odmiany pogrubiane na wydruku.
- `player_aid_file` — odsyłacz do `sciaga_graczy.json`; nie wpisuj tu kopii ściągi.

Kolory w danych: C — czerwona, B — biała, Z — zielona, F — czarna,
N — niebieska. Zachowaj identyfikatory bohaterów, akcji, lekcji i kolorów.

Opis pasywu ma `name` (nazwę), `when` (warunek), `effect` (pełny efekt),
`short` (krótką wersję na macie), `note` (objaśnienie) i `stacking` (kumulację).
Pełny i krótki opis są obok siebie w tym samym pliku. Przy zmianie sensu
zaktualizuj obydwa. W eksploracji wpisuj „wpływ”; przy obiekcie aplikacja
wyświetla „postęp”, a mata „wpływ / postęp”.

## Osobna ściąga dla graczy

`text/sciaga_graczy.json` zawiera cztery strony w `pages`: podstawy, walkę,
rozmowy i obiekty. Każda ma tytuł, podtytuł, wprowadzenie oraz sekcje.
Sekcja może zawierać `paragraphs`, `steps` i `table`; `example: true`
wyróżnia przykład. Zachowaj `version: 1` i unikalne identyfikatory stron.

Zmiana tego pliku jest odczytywana niezależnie od kart bohaterów.
Aplikacja czyta nowe teksty przy kolejnym żądaniu, bez restartu;
wcześniej zapisane wpisy historii nie zmieniają się wstecz.

## Jak odbudować materiały

Uruchom z głównego katalogu projektu:

```sh
PYTHONPATH=src .venv/bin/python scripts/build_handouts.py
```

Komenda publikuje aktualne czarno-białe PDF-y w głównym folderze `handouts/`:
`characters.pdf`, `map_a4.pdf`, `map_full.pdf`, materiały `mission_0/` oraz
ściągę i znaczniki w `reference/`. Mapa i kafle mają wspólną skalę
`(250/244) × 1,03`. Dokładną listę oraz instrukcję druku opisuje
[przewodnik wydruków](../../../handouts/README.md).

Można odnowić tylko zmienioną część:

```sh
PYTHONPATH=src .venv/bin/python scripts/build_handouts.py --only mission_0
PYTHONPATH=src .venv/bin/python scripts/build_handouts.py --only characters
PYTHONPATH=src .venv/bin/python scripts/build_handouts.py --only maps
PYTHONPATH=src .venv/bin/python scripts/build_handouts.py --only reference
```

`characters` odświeża też ściągę i znaczniki, bo zmiana słownika może wpływać
na ich skład. `reference` pomija 35 arkuszy bohaterów. Generator sprawdza w Chrome
przepełnienia, grafiki i fizyczne wymiary kart przed publikacją.
Potrzebuje istniejących Chrome/Chromium, `pdfinfo`, `pdfunite` i `pdftoppm`;
nie instaluje dodatkowych zależności. Ghostscript, jeśli jest dostępny,
zmniejsza rozmiar PDF przy zachowaniu wymiarów i liczby stron; ilustracje
są przygotowane do druku w 300 dpi. Dziewięć końcowych PDF-ów w `handouts/`
może być wersjonowanych w Git; robocze HTML, PDF-y, manifesty i podglądy
trafiają do ignorowanego `.cache/handouts/`.

## Opis a mechanika

Zmiana liczby w opisie akcji nie zmienia jej działania w silniku.
Statystyki, progi, koszty, runy i efekty liczbowe pochodzą z profili postaci,
reguł oraz katalogów balansu (m.in. `content/balance/pooled_mana/catalog.json`).
Pliki `mechanics/` są faktycznymi danymi misji. Edycja narracji lub wyglądu
nie wymaga zmiany reguł. Układ i stałe nagłówki arkuszy pozostają
w `scripts/build_hero_mats.py`; treści postaci i ściągi edytuj w JSON.

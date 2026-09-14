# Aktualne karty postaci — wspólna mana 0.3

## Eksploracja — aktualne wydruki 2026-09-14

Wszystkie siedem zestawów zawiera dwie metody eksploracji z cechami i rzeczywistym
rozbiciem premii. Zastraszanie Brakki używa KON; Erynd ma Praktykę terenową +2
do obiektu. Wspólna ściąga opisuje dobieranie do 21, jawne przeszkody i
**utrudnienie po przekroczeniu: 2k20, niższy wynik, bez premii karcianej**.

Przegenerowano cztery formaty, HTML/PDF, manifesty, aliasy i zbiorczy pakiet
areny. Arkusze mają 7 stron na postać (49 razem), wersje kart 8 stron (56 razem),
a pakiet areny i kart 67 stron. [Opis wdrożenia](EXPLORATION_MANA_IMPLEMENTATION.md).

## Obecne materiały

Wspólny czarno-biały PDF A4 z wszystkimi kartami i areną do sklejenia:
[pakiet 67 stron](ARENA_A4_PRINT_PACK.md). Pusta mapa i osobne znaczniki terenu mają pola 25 mm,
oznaczenia cięcia i zakładki 10 mm do kleju lub taśmy.

Wszystkie siedem postaci ma odnowione materiały: statystyki, pełne 66 zdolności, Święty symbol Dagny w ekwipunku,
aktualne koszty, runy panelu, reakcje, pasywy, skazy, dobór i historię postaci.
Źródło danych jest wspólne z aplikacją: profil nowej gry, katalog fizycznej many,
kompilator broni oraz stały katalog symboli panelu. Nie przepisujemy ręcznie PW,
KP ani premii broni do arkuszy.

Od 2026-09-07 fioletową manę zastępuje czarna. Symbole: biała — słońce,
niebieska — kropla, czarna — czaszka, czerwona — płomień, zielona — drzewo;
cyfra 1 w kółku oznacza dowolny kolor. Do testów używamy podstawowych lądów
MTG: Plains, Island, Swamp, Mountain i Forest. Każdy ląd jest jedną kartą
many; wydany trafia na stos odrzuconych. Nowy rynek ma stale najwyżej pięć kart, talia liczy 25 kart. Nie ma prywatnych rezerw ani fal.
Mapowanie lądów i kolorów: [Wizards of the Coast](https://magic.wizards.com/en/news/feature/anatomy-magic-card-2006-10-21).

Wszystkie symbole są wektorowe i rozróżnialne również bez koloru. Wewnętrzne
kody kosztów pozostały stabilne (`F` oznacza teraz czarną); nie są to litery
kolorów MTG. Interfejs i legenda wydruku pokazują nazwy oraz ikony.

## Gotowe pliki

Katalog: `assets/physical_cards/character_sets/physical_mana_v02/`.

| Podkatalog | Zawartość | Zbiorczy PDF |
|---|---|---|
| `minimal` | Oszczędne arkusze z runami, bez ilustracji | `all_heroes.pdf`, 49 stron |
| `color` | Kolorowe arkusze z portretem | `all_heroes.pdf`, 49 stron |
| `bw_test` | Czarno-białe awersy do wycięcia, 4 karty na A4 | `all_heroes.pdf`, 56 stron |
| `cards` | Kolorowe awersy do wycięcia, 4 karty na A4 | `all_heroes.pdf`, 56 stron |

Każdy podkatalog zawiera także `garran.pdf`, `brakka.pdf`, `mira.pdf`, `dagna.pdf`,
`lorian.pdf`, `nimra.pdf`, `erynd.pdf`, odpowiedniki HTML i manifesty JSON.
Każdy zestaw postaci obejmuje kartę statystyk/pasywów/skazy, zdolności oraz
osobną stronę historii, ekwipunku i biegłości oraz osobną stronę zasad tury.
Każdy zestaw ma dodatkową stronę czterech warunków rozmów. Każdy bohater zajmuje siedem stron arkuszy albo osiem stron wersji do wycięcia.

Druk: A4, skala 100%, jednostronnie. Karty do wycięcia nie zawierają rewersów.
Dolne runy na mapie pozostają nadrukowane, ale cały pasek akcji jest wyłączony. Wybieraj ikonę w UI; narożne −, +, ✓ i ↩ zachowują pozycje.
REAKCJA/AUTO oznacza wybór w kontekstowym oknie gry. MOD modyfikuje czar albo
atak — nie daje dodatkowej akcji; opłaca się także modyfikowane działanie.

Dotychczasowe ścieżki PDF pod `keyboard_v1/pdf`, `keyboard_v1/minimal_bw/pdf`,
`bw_test`, `character_sheets_bw` oraz `card_set_<postać>.pdf` zawierają kopie
aktualnych materiałów. Stary manifest klawiatury został zastąpiony manifestem
wersji 5 z mapowaniem run v1 i jawnym `rules_profile: shared_mana_v03`. Starsze ilustracje i PNG
są archiwum graficznym; aktualnym kompletem do gry są powyższe PDF-y.

Linki do wszystkich czterech kompletów są w aplikacji na `/rules/physical-mana`.

## Generowanie

```bash
PYTHONPATH=src python scripts/generate_mana_character_prints.py --overwrite
```

Opcje: `--actor lorian`, `--format minimal` (powtarzalne), `--html-only`,
`--output-dir /tmp/moje-karty`. Eksport do innego katalogu nie podmienia
standardowych plików projektu.

Dotychczasowe generatory domyślnie wywołują ten sam eksport:

- `generate_keyboard_character_sheets.py`: kolorowe i minimalistyczne arkusze;
- `generate_character_card_sets.py`: kolorowe i czarno-białe karty;
  zachowano `--bw-test-only`.

Każdy PDF jest renderowany osobno, kolejno, przy użyciu zainstalowanego
Chrome/Chromium. Zbiorcze PDF-y scala `pdfunite` z Popplera. Nie dodano pakietów
Pythona ani nie używano generowania grafiki. HTML pozostaje dostępny do
ręcznego druku, jeśli tych programów nie ma. PDF ma tekst możliwy do zaznaczenia.

## Zmienione źródła

- `physical_cards/mana_print.py`: dane siedmiu postaci, statystyki i oznaczenia panelu;
- `physical_cards/mana_print_html.py`: cztery układy A4;
- `physical_cards/mana_print_files.py`: kolejny eksport, manifesty i kopie
  pod dotychczasowymi ścieżkami;
- `character_creation/physical_mana_help.py`: pasywy i skazy używane również
  przez stronę instrukcji w aplikacji;
- `rules/physical_mana.py`: rozwinięte opisy efektów, bez zmiany kosztów
  ani wykonawczej mechaniki; m.in. obszary i obrony Nimry, ryzyko przeskoku
  pioruna na sojusznika, czasy efektów i wyjaśnienie Metamagii;
- `ui/routes.py` i `ui/templates/physical_mana.html`: wspólne opisy i linki PDF;
- generatory w `scripts/`, `TODO.md` i dokumentacja profilu.

Ścieżki modułów powyżej są względem `src/dnd_board_game/`.

## Weryfikacja

Uruchomiono kolejno, przez `scripts/safe_pytest.sh --timeout 60`:

- `tests/unit/test_mana_character_prints.py`: 13 testów;
- `tests/unit/test_physical_mana.py`: 19 testów;
- `tests/unit/test_hero_rules_consistency.py`: 16 testów.

Łącznie **48 testów zaliczonych**. Oba dotychczasowe skrypty sprawdzono również
przez rzeczywisty eksport HTML do osobnych katalogów tymczasowych.

Sprawdzono wszystkie 28 dokumentów HTML w Chrome: brak tekstu poza kartami
lub stopką. Z rzeczywistych PDF-ów odczytano tekst przez `pdftotext`: każdy
format zawiera wszystkie właściwe opisy zdolności, pasywów i skaz. Manifesty
mają prawidłowe koszty i klawisze. Zweryfikowano liczbę stron w plikach
indywidualnych i zbiorczych oraz zgodność kopii pod starymi ścieżkami.

Przejrzano wizualnie arkusze Nimry i Loriana; kontrola rastrowego podglądu
wersji minimalistycznej sprawdza wyłącznie odcienie szarości. Nie wykonywano
fizycznego wydruku na drukarce ani testów balansu przy stole.

## Garran — Nieustępliwość (2026-09-06)

W czterech wydaniach karty Garrana, dossier i zbiorczych kompletach stary opis
Wyrzutów sumienia zastąpiono Nieustępliwością: 2 dowolne many za zwykły Ruch
rozpoczęty obok niepokonanego przeciwnika, także po skosie. Koszt ustala się
przy pierwszym zwykłym ruchu w turze. Dalsze odcinki nie wymagają dopłat,
a przemieszczenia ze zdolności i wymuszone nie uruchamiają skazy.
Przy skrócie M również jest przypomnienie o warunkowym koszcie.

Aplikacja pokazuje tę samą regułę przy wyborze i podglądzie ruchu oraz w panelu
many; deklaracja jest zachowana w zapisie gry. Identyfikator `flaw_remorse`
pozostaje stabilny dla istniejących zapisów, ale pomoc profilu many pobiera
aktualny opis z katalogu. Dawne kary do k20 nie działają w profilu many.

Walidacja zmiany Garrana: 69 testów w pięciu celowanych plikach:
`test_garran_mana_movement.py` (14), `test_physical_mana.py` (19),
`test_archetype_flaws.py` (7), `test_mana_character_prints.py` (13),
`test_hero_rules_consistency.py` (16). Uruchomione kolejno przez
`scripts/safe_pytest.sh --timeout 60`. Kontrola 28 HTML/PDF: pełne teksty,
liczby stron, brak przepełnień i zgodność kopii w dotychczasowych ścieżkach.
Podgląd komponentu statusu z rzeczywistym payloadem przy 390 i 1440 px:
widoczny koszt startu i brak ponownej dopłaty po rozpoczęciu ruchu.
Nie wykonywano nowego testu z fizyczną planszą ani drukarką.

## Wielokrotny zwykły Atak tylko dla Loriana (2026-09-06)

Pozostałe sześć postaci wykonuje jedno zwykłe uderzenie za 1 dowolną manę,
bez formularza liczby ataków. Tylko Lorian deklaruje serię w ramach jednej
akcji. Podwójny strzał Erynda i Celownik optyczny Loriana zachowują dwa
ataki wynikające z techniki. Zryw Garrana i Lekkomyślny Brakki opisują
teraz premię do następnego pojedynczego zwykłego ataku; zwrot Brakki
następuje po nim. Zaktualizowano wszystkie cztery wydania kart, dossier,
zasady wspólne i zbiorcze PDF-y.

`combat/physical_mana.py` kontroluje uprawnienie do serii i ogranicza stare
deklaracje zapisane dla pozostałych bohaterów. UI pomija formularz u innych
postaci, a bezpośrednia deklaracja przez API jest odrzucana. Rozpoczęte
serie technik pozostają bez zmian. Karty i płatności nadal są fizyczne.

Walidacja: `test_lorian_attack_series.py` (13), `test_physical_mana.py` (19),
`test_mana_character_prints.py` (13), `test_hero_rules_consistency.py` (16):
łącznie 61 testów, kolejno przez `scripts/safe_pytest.sh --timeout 60`.
Kontrola 28 PDF-ów potwierdziła kompletność opisów i kopii pod starymi linkami.
Kontrola układu 28 HTML: brak przepełnień. Podgląd formularza przy 390 i 1440 px: widoczny tylko dla Loriana, niewidoczny dla Erynda.

## Weryfikacja czarnej many — 2026-09-07

45 testów przez `scripts/safe_pytest.sh --timeout 60`, kolejno:
`test_mana_character_prints.py` (16), `test_physical_mana.py` (19),
`test_combat_menu_mana.py` (10). Przeglądarka: wszystkie 28 układów bez
przepełnienia, ikony duże i małe, nowa nazwa fali ze starego zapisu oraz
zachowanie liczby wymian w wydarzeniu 6. Zweryfikowano 28 PDF-ów postaci,
cztery kolekcje (26/26/35/49 stron), tekst „Czarna”, brak dawnej nazwy
oraz zgodność kopii pod dotychczasowymi linkami. Obejrzano także
wyrenderowaną stronę minimalistycznego PDF-u Miry.

## Karty panelu areny — 2026-09-07

Wszystkie cztery formaty mają runy i ikony zamiast drukowanych liter
klawiatury. Reakcje są oznaczone słowem REAKCJA i wybierane kontekstowo.
Manifest przechowuje `panel_slot` oraz dawny `key` wyłącznie dla zgodności
ze starszym wejściem. Przypisania identyfikatorów do run są jawne i nie
zależą od sortowania katalogu. Karta statystyk zawiera dziewięć ikon
sterowania, a opisy wyjaśniają obie ścieżki zmiany podglądu. Reguły many,
statystyki, pasywy, skazy i koszty zdolności pozostają wspólne z grą.

Weryfikacja kart z runami: 23 testy `test_mana_character_prints.py` przez
bezpieczny wrapper (limit 60 s), 28 układów HTML bez przepełnienia,
28 PDF-ów postaci i cztery kolekcje (26/26/35/49 stron) oraz kopie pod
poprzednimi linkami. Sprawdzono identyczne przypisania znaków w manifestach
kart i areny, brak drukowanych ENTER/ESC/SPACJA oraz wygląd karty Nimry.
Przeglądarka: bezpośrednia zmiana podglądu run i ikon, Wróć do menu,
blokada niedostępnej akcji oraz brak przełączania podczas rzutu.

Aktualizacja panelu: usunięty osobny przycisk Interakcja; nie występuje
w legendzie sterowania ani opisach przycisków na kartach. Puste miejsce
w panelu nie zmienia przypisania żadnej runy.

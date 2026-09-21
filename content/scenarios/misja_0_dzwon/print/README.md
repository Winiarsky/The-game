# Misja 0 — materiały do przygotowania gry

Aktualne, gotowe pliki są bezpośrednio w tym folderze. Otwórz PDF,
wybierz **A4, jednostronnie, 100% / rzeczywisty rozmiar**. Wyłącz
„dopasuj do strony”. Strony poziome mogą się obrócić, ale nie skalować.

| Plik | Zawartość | Strony |
| --- | --- | --- |
| [misja_0_komplet_A4.pdf](misja_0_komplet_A4.pdf) | Rozmieszczenie i kafle mapy, rozkaz Nessy, pokwitowania Boruta, przedmioty i obie wersje pierścienia | 10 |
| [misja_0_komplet_A4_25mm.pdf](misja_0_komplet_A4_25mm.pdf) | Ten sam komplet scenariusza z nominalnymi polami 25 mm, bez korekty drukarki | 10 |
| [karty_postaci_A4.pdf](karty_postaci_A4.pdf) | Spis i po 5 stron dla siedmiu bohaterów: postać, mana, akcje, mata wyposażenia, sprzęt do wycięcia | 36 |
| [sciaga_graczy_A4.pdf](sciaga_graczy_A4.pdf) | Wspólne zasady, walka, rozmowy i obiekty | 4 |
| [znaczniki_A4.pdf](znaczniki_A4.pdf) | Znaczniki drugiej ręki i wykorzystanej zdolności; legenda sprzętu | 1 |

Drukuj wybrane zestawy postaci: Garran 2–6, Brakka 7–11, Mira 12–16,
Dagna 17–21, Lorian 22–26, Nimra 27–31, Erynd 32–36. Maty i arkusze
pozostają w całości; wytnij sprzęt oraz znaczniki po zewnętrznych liniach.
Ściągę wydrukuj przynajmniej raz dla drużyny. Pełny spis stron jest także
w plikach `.md` i `.json` obok każdego PDF. [Podgląd kart](characters/podglad.html).

Handouty i przedmioty trzymaj osobno do wskazanego momentu przygody.
Pierścień ma wersję niepoznaną i zidentyfikowaną — drugą przekaż dopiero
po identyfikacji. Nie rozdawaj całego pakietu scenariusza na początku.

## Kontrola skali

- Kafle w `misja_0_komplet_A4.pdf` zachowują korektę drukarki **250/244**.
  Projektowane pole ma 25 mm; PDF kompensuje wcześniej zmierzone zmniejszenie
  na drukarce. Nie dodawaj drugiej korekty w oknie wydruku.
- Dla drukarki drukującej rzeczywiste 25 mm użyj wariantu
  [misja_0_komplet_A4_25mm.pdf](misja_0_komplet_A4_25mm.pdf).
- Maty many: karta **63 × 88 mm**, bez koszulki.
- Wyposażenie i znaczniki: **60 × 42 mm**.
- Ramki akcji: **62 × 76 mm**, u Nimry **68 × 53 mm**.
- Najpierw wydrukuj stronę próbną i zmierz linię kontrolną linijką.

## Odbudowa i edycja

Źródła opisano w [EDITING.md](../EDITING.md). W głównym katalogu projektu:

```sh
PYTHONPATH=src .venv/bin/python scripts/build_session_print_packs.py
PYTHONPATH=src .venv/bin/python scripts/build_session_print_packs.py --only mission --nominal
```

`characters/` zawiera wygenerowane pojedyncze arkusze, podglądy i wyniki
kontroli wymiarów. `archive/` zachowuje poprzedni zbiorczy PDF postaci;
`../maps/print/` zawiera wcześniejsze wydruki map i kafli. Bieżące zestawy
wymieniono wyłącznie w tabeli powyżej. Nie edytuj wygenerowanych plików.

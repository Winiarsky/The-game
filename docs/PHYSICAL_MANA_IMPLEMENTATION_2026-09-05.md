# Fizyczna mana 0.2 — implementacja

Nowa gra uruchamia jawny profil `physical_mana_v02` dla siedmiu gotowych bohaterów.
Poprzednie zapisy nie są automatycznie konwertowane. Nie przywracano historycznej
aplikacji ani nie zmieniano sprzętowej warstwy `board/`.

## Granica stołu i aplikacji

Aplikacja nie zawiera stanu talii, rynku, ręki ani płatności. Wyświetla koszty,
instrukcje wymian, pasywy, skazy i dobór. Gracze prowadzą też znaczniki limitów
karcianych. Nie ma potwierdzania zapłaty ani blokad zależnych od koloru/liczby kart.
Pozostają walidacje czasu działania, reakcji, warunków, wyposażenia i legalnych celów.

Seria zwykłych ataków ma niezmienną dodatnią liczbę uderzeń oraz osobne cele,
trafienia i obrażenia. Nie porównuje się jej z pojemnością ręki. Postęp serii i efekty
zapisują się zwykłym mechanizmem snapshotów. Premie ograniczone do jednego trafienia
można zachować przed rzutem obrażeń. Zdolności wielostrzałowe mają własne stałe serie.

Lorian ma pełny zestaw 14 zdolności, w tym wymiany i reakcję przekazania karty.
Duchowa broń wykonuje opłaconą aktywację w obrębie tury Dagny; po niej wraca jej
poprzedni stan akcji i ruchu. Nie otrzymuje bezpłatnej powtarzalnej tury.

## Interfejs i dokumentacja

- Podsumowanie many pokazuje dobór, rezerwę i pojemność, bez fikcyjnego licznika kart.
- Deklaracja liczby ataków obsługuje formularz, Enter i anulowanie podglądu.
- Zachowano podstawowe sterowanie planszą/klawiaturą i awaryjny wybór ekranowy.
- Rozwijana pomoc zawiera pełne zdolności, pasywy karciane, skazy i zgłoszenie fali.
- `/rules/physical-mana` zawiera instrukcję oraz wszystkie 77 zdolności/Metamagii
  w siedmiu zestawach, z widokiem do drukowania lub zapisania przez przeglądarkę jako PDF.
- Generatory kart i arkuszy domyślnie eksportują fizyczną manę 0.2. Komplet aktualnych PDF-ów: `assets/physical_cards/character_sets/physical_mana_v02/`. Dotychczasowe ścieżki PDF `keyboard_v1` i `bw_test` zawierają aktualne kopie. Opis: `docs/PHYSICAL_MANA_PRINTS_V02.md`.

## Walidacja

`tests/unit/test_physical_mana.py` sprawdza wszystkie profile, usunięcie dawnych
bramek zasobów, rezerwy, granicę rundy i kumulowanie fal, akcje Loriana,
serie różnych celów, zapis/odczyt, Podwójny strzał, leczenie, aktywację duchowej broni
oraz wpływ fali na KP, szybkość i płaską premię obrażeń.

Uruchamiano osobno celowane testy Garrana, Erynda, Miry, reakcji i przywołań,
spójności bohaterów oraz rozpoczęcia nowej gry. Kontrola Chrome obejmowała panel
many, deklarację serii, strony instrukcji/nowej gry/postaci oraz szerokości 1440 i 390 px.

To walidacja reguł i przepływów aplikacji, nie dowód balansu. Następny etap:
rozgrywki przy stole i pomiar czasu serii, presji rynku oraz tempa przewijania talii.


Końcowa kontrola: 19 testów nowego profilu; ponadto celowane pliki reguł bohaterów,
reakcji, przywołań, cech klasowych, spójności opisów i dwa przypadki startu nowej gry.
`compileall` i `git diff --check` bez błędów. Nie wykonywano pełnego zestawu testów
ani testu na podłączonej fizycznej planszy. Materiały przeglądarkowe sprawdzono
w Chrome, przy szerokości 1440 i 390 px, bez przepełnienia szerokości strony.


## Najważniejsze pliki

- `rules/physical_mana.py`: katalog 77 kosztów, opisów, pasywów i skaz.
- `character_creation/physical_mana.py`: jawne zastosowanie profilu do bohatera.
- `combat/physical_mana.py`, `physical_mana_sources.py`, `physical_mana_summon.py`:
  serie, fale, wsparcie, adaptacje zdolności i sterowanie duchową bronią.
- `ui/exploration_app.py`, `ui/routes.py`, `ui/static/physical_mana.js`,
  `ui/static/physical_mana.css`: transport decyzji i interfejs.
- `ui/templates/physical_mana.html`: instrukcja i komplet talii do wydruku.
- `tests/unit/test_physical_mana.py`: 19 celowanych przypadków nowego profilu.

Ścieżki modułów powyżej są względem `src/dnd_board_game/`, poza katalogiem testów.

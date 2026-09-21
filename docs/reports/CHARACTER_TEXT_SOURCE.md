# Wspólne źródło opisów postaci

Aktualne źródła: `content/scenarios/misja_0_dzwon/text/karty_postaci.json`
oraz osobne `text/sciaga_graczy.json` w tej samej paczce.
Adapter: `scenarios/character_text.py`. [Instrukcja autora](../../content/scenarios/misja_0_dzwon/EDITING.md).

Aktualizacja 21.09.2026: źródła są w folderze Misji 0, a loader zachowuje
dotychczasowe API i odświeża oba pliki niezależnie. Wydruki rozdzielono
na karty (36 stron), ściągę (4) i znaczniki (1); starszy zbiorczy PDF
jest w `print/archive/`. Nowe teksty UI są w `text/ui/*.json` tej paczki.

Przeniesiono historie, skazy, opisy akcji i podbić, 70 pasywów, narracje lekcji,
instrukcje samouczka, opisy sprzętu startowego, pomocnik i słownik wyróżnień.
Usunięto cztery stare pliki redakcyjne; katalogi balansu nie przechowują już
kopii opisów pasywów i akcji. Układy pozostają w kodzie, statystyki i efekty liczbowe w regułach.
Bieżące komunikaty nowego UI odczytują osobne pliki `text/ui/*.json`.

Test edycji zapisuje tymczasowy JSON i sprawdza odświeżenie w już działającej
sesji: opis akcji, pasywy walki i eksploracji, historia/skaza, lekcja, pomocnik.
Sprawdza także niezmienność kosztu akcji i statystyk bohatera.

## Walidacja pierwotnego scalenia źródeł

Testy przez `scripts/safe_pytest.sh`, sekwencyjnie, z limitami czasu:

- `test_character_text_source.py`, `test_mana_character_prints.py`,
  `test_print_language.py`, `test_mana_passive_copy.py`: 46 testów zakończonych sukcesem.
- `test_training_walkthrough.py`: 32 testy zakończone sukcesem; wariant porażki
  tarczą miał zbyt niski rzut obrońcy, który po doliczeniu obecnego naładowania
  pozwalał Garranowi wygrać. Poprawiono przygotowanie testu (bez zmian zasad).
  Wszystkie trzy warianty tarczy przeszły przy powtórzeniu.
- `test_pooled_mana_training.py` + trzy warianty tarczy: 36 testów zakończonych sukcesem.
- `test_confrontation_presentation.py`, `test_distinct_combat_passives.py`,
  `test_distinct_exploration_passives.py`: 67 testów zakończonych sukcesem.
- Generator `build_hero_mats.py`: 41 stron, brak problemów w `validation.json`.
  Porównanie HTML wszystkich mat przed i po przeniesieniu treści: bez zmian układu.

Pierwsza łączna próba obu plików samouczka przekroczyła 60 s; uruchomiono je
osobno z odpowiednimi limitami. Nie uruchamiano całego repozytorium testów.

## Starsze testy wymagające aktualizacji

Dodatkowy przebieg `test_character_text_source.py`, `test_garran_mana_movement.py`
i `test_hero_rules_consistency.py`: 16 sukcesów i 20 porażek.

- 13 wariantów `test_garran_mana_movement.py` wciąż oczekuje kosztu ruchu 1 lub
  2 kart. Obecne reguły dają ruch bez many. Plik implementacji
  `combat/physical_mana_movement.py` nie był zmieniany przy scalaniu opisów.
- 7 wariantów `test_hero_rules_consistency.py` oczekuje manifestu
  `shared_mana_v03`, podczas gdy publikowany zestaw ma profil `pooled_mana_v01`.

Nie przywracano poprzedniego systemu many, aby dopasować do niego testy.
Aktualizację tych starych scenariuszy testowych dodano do TODO.

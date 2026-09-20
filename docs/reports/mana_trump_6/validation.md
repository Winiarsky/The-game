# Weryfikacja wdrożenia — 20.09.2026

Testy uruchamiane kolejno przez `scripts/safe_pytest.sh`, z limitami czasu 60–120 sekund. Chromium uruchamiany osobno w testach przeglądarkowych.

| Plik / zakres w tests/unit | Zaliczone przypadki |
|---|---:|
| test_trump_mana.py | 14 |
| test_mana_charge.py | 21 |
| test_charge_roll_bonus.py | 27 |
| test_pooled_mana.py | 33 |
| test_pooled_mana_runtime.py | 11 |
| test_pooled_mana_training.py | 33 |
| test_pooled_mana_points.py | 9 |
| test_pooled_mana_enemies.py | 6 |
| test_confrontation.py | 30 |
| test_confrontation_presentation.py | 11 |
| test_confrontation_confirmations.py | 6 |
| test_mana_passive_copy.py | 2 |
| test_print_language.py | 4 |
| test_pooled_mana_browser.py::test_pool_dialog_runes_and_native_board_ownership | 2 |
| test_confrontation_presentation_browser.py | 6 |
| test_confrontation_confirmations_browser.py | 4 |
| **Łącznie unikalnych przypadków** | **219** |

Pierwsze przebiegi wykryły oczekiwania dawnej punktacji w testach; zostały dostosowane do faktycznej liczby kart. Po poprawkach ponowiono odpowiednie pliki. W `test_confrontation_presentation.py` powtórzono wyłącznie naprawiony przypadek pełnej puli (pozostałe 10 już przechodziło). Poprawiono też migrację dawnej biegłości, aby zachowywała cechę wybranego podejścia.

`build_hero_mats.py`: wygenerowano kompletny PDF 41 stron. Wszystkie wpisy `content/print/characters/mats_v2/validation.json` bez błędów; zachowane miejsca na karty 63 × 88 mm. Obejrzano rastrowy podgląd maty Garrana.

`git diff --check`: bez błędów.

Raport ekonomii: 2744 próby, 392 konfiguracje, 8 rund, drużyny 3–6-osobowe. Raport konfrontacji: 224 próby, 16 konfiguracji. Nie przeprowadzono pełnej ręcznej rozgrywki ani ponownego badania balansu obrażeń i ST. Testy przeglądarkowe korzystają z testowego transportu planszy; nie są nowym testem fizycznego WLED.

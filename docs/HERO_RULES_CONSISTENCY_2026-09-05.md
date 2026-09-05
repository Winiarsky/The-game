# Zgodność zasad i opisów bohaterów — 2026-09-05

Zakres: siedem grywalnych postaci na poziomie 3. Punktem odniesienia jest obecny wariant planszowy projektu. Historyczne, ukryte szablony postaci nie należą do tego zestawu.

## Sprawdzone i poprawione opisy

| Bohater | Najważniejsze doprecyzowania |
| --- | --- |
| Garran | Taktyka 4; odnawianie zasobów; koszt ruchu przy tarczy i postawie; rozkazy i naturalne wyniki; wada oparta na sumie otrzymanych obrażeń. |
| Brakka | Szał 3 na długi odpoczynek; Dzikość 3 na rozpoczęcie Szału; koszty zdolności; przedmioty w Szale; chwyt pod D. |
| Mira | Fortele 4; ukrycie i osobne wykrywanie przez wrogów; flanka i Atak z cienia; reakcja uniku; ukrycie/wyjście pod D. |
| Dagna | Komórki 4/2; wspólna Boska Moc; premia Ucznia Życia; Krok ratowniczki raz na jej turę; ratowanie przy wadzie; odpędzanie pod T. |
| Lorian | Inspiracja 4k6 na krótki odpoczynek; ostrzały i reakcje bez wydawania Inspiracji; warunek publiczności; Improwizacja raz na NPC; nazwy i obszary czarów. |
| Nimra | 15 czarów i 5 opcji Metamagii; koszty komórek; skutki dodatkowe czarów; Echo poprzedniej rundy; Odzyskiwanie magiczne. |
| Erynd | Instynkt 4; koszty strzał; Pierwsza krew wyłącznie z łuku; podwójny strzał; Czujność; wada liczona przy celu. |

Opisy wad, pasywów i cech znajdują się w `src/dnd_board_game/character_creation/boardgame_help.py`. Korzystają z nich interfejs i generatory kart. `docs/BOARDGAME_ARCHETYPES_LEVELS_1_3.md` jest generowane razem z arkuszami klawiaturowymi. Panel czarów pokazuje aktywną talię bohatera.

## Poprawki mechaniczne

- Wada Erynda daje -1 do ataku długim łukiem za każdego przytomnego bohatera drużyny w 5 stopach od wybranego celu. Pomija samego Erynda, pokonanych, nieprzytomnych, przywołania i NPC. Inny cel ma osobną karę; nóż i czary jej nie otrzymują. Synchronizacja usuwa stare efekty bez celu.
- Odtwarzanie źródła ataku zachowuje premię +2 za Łucznictwo aktualnego właściciela. Ponowne odtworzenie nie kumuluje premii, a właściciel bez stylu jej nie otrzymuje.
- Profil Miry zapewnia biegłość w jej nożach do rzucania, a profil Erynda w jego nożu myśliwskim. Wyniki: łuk Erynda +8, jego nóż +3, noże Miry +6.

## Weryfikacja

- `tests/unit/test_hero_rules_consistency.py`: wszystkie siedem kart kontra rzeczywiste statystyki, skróty, nazwy, koszty komórek, wady i dostępne czary; premie głównej broni każdego bohatera; biegłości i ponowne wiązanie źródeł ataku.
- `test_archetype_flaws.py`, `test_attack_flow.py`, `test_boardgame_profiles.py`, `test_scene_interactions.py`, `test_player_combat_action_flow.py`: naliczanie wad i działanie zmienionych ścieżek ataku.
- Testy zdolności Garrana, Miry, Loriana, Nimry i Erynda; `test_level_one_class_features.py`, `test_combat_auras.py`, `test_player_area_healing_flow.py`: istniejące zachowania klas, reakcji, aur i leczenia.
- Testy skrótów i launchera; pięć konkretnych testów sesji UI obejmujących opisy, Mirę, Nimrę, chwyt Brakki i Krok ratowniczki Dagny.
- Testy manifestu arkuszy i kart; rzeczywiste wygenerowanie wszystkich siedmiu zestawów kolorowych oraz czarno-białych. Renderery dopasowują pełny tekst lub zgłaszają brak miejsca zamiast go ucinać. Kontrola wizualna arkuszy.
- `tests/integration/test_ostatni_transport_campaign_walkthrough.py`: przebieg kampanii do wejścia w Czarny Bród.

Pytest uruchamiano kolejno, małymi partiami, przez `scripts/safe_pytest.sh` z limitem czasu. Cały plik testów kart przekroczył początkowo 60 sekund; po poprawkach sprawdzono osobno testy bez generowania oraz wygenerowano komplet rzeczywistych zestawów. Nie wykonywano pełnej globalnej suity ani fizycznej sesji na planszy. Zgodność opisów nie stanowi pomiaru balansu rozgrywki.

## Aktualne wydruki

- Kolorowe arkusze i dossier: `assets/physical_cards/character_sets/keyboard_v1/pdf/keyboard_character_sheets_v1.pdf` — 14 stron.
- Oszczędne arkusze i dossier: `assets/physical_cards/character_sets/keyboard_v1/minimal_bw/pdf/minimal_bw_character_sheets_v1.pdf` — 14 stron.
- Zestawy QR: `assets/physical_cards/character_sets/card_set_<hero>.pdf`.
- Zbiorcze karty bez rewersów: `assets/physical_cards/character_sets/bw_test/card_sets_bw_test.pdf` — 44 strony.

Pliki PDF i PNG są lokalnymi artefaktami w ignorowanym przez Git katalogu `assets/`.

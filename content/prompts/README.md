# Prompty LLM

Prompty są centralnie trzymane w tym katalogu i ładowane przez `src/dnd_board_game/llm/prompts.py`.

- `gm_declaration_analyzer_pl.md` - pierwszy krok LLM; ocenia, czy deklaracja gracza pasuje do świata gry, sceny i aktywnego wyzwania.
- `gm_challenge_classifier_pl.md` - drugi krok LLM; zamienia zaakceptowaną deklarację na mechaniczne pola challenge.
- `gm_classifier_pl.md` - starszy prompt zachowany tymczasowo jako archiwum kompatybilności; nowe runtime powinny używać dwóch promptów powyżej.

# Prompt Template For Codex

Use this shape for larger tasks.

```text
Kontekst:
Przeczytaj PROJECT_CONTEXT.md, GAME_DESIGN.md, ARCHITECTURE.md i TODO.md.

Cel:
...

Ograniczenia:
- Nie zmieniaj legacy/.
- Nie zmieniaj board/ bez wyraźnego powodu.
- Nie dodawaj zależności.
- Zachowaj deterministyczną logikę poza UI/hardware.

Pliki do zmiany:
...

Nie zmieniaj:
...

Kryterium sukcesu:
- ...
- Dodaj/uruchom testy przez scripts/safe_pytest.sh.
- Zaktualizuj TODO.md, jeśli kończysz punkt.
```

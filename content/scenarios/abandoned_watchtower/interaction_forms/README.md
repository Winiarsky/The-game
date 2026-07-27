# Formularze Interakcji: Opuszczona Strażnica

Ten folder zawiera historyczne formularze projektowe użyte podczas
przeprojektowania interakcji. Nie jest źródłem prawdy runtime.

Aktualne, wykonywalne definicje znajdują się w `content/scenarios/abandoned_watchtower/`
i są walidowane przez loader oraz testy. Pozostawione w formularzach znaczniki
`TODO` opisują pierwotne pytania projektowe; nie oznaczają brakującej mechaniki,
jeżeli odpowiadające pole istnieje już w JSON. Przy dalszej rozbudowie najpierw
aktualizujemy content i test, a formularz tylko wtedy, gdy nadal służy jako brief
autorski.

Wypełnij pliki Markdown po ludzku. Na podstawie tych formularzy kolejny etap powinien wygenerować albo zaktualizować:

- JSON scenariusza,
- `intent_permissions`,
- zablokowane informacje,
- flagi,
- efekty mechaniczne,
- brakujące prymitywy runtime,
- testy jednostkowe i manualne.

## Formularze Referencyjne

### Wyzwania

- `challenges/closed_gate.md` - brama strażnicy.
- `challenges/courtyard_search.md` - przeszukanie dziedzińca i odkrycie rannego zwiadowcy.

### Punkty Eksploracji

- `points/old_camp_tools.md` - ślady dawnego obozowiska i piła.
- `points/hidden_cache.md` - ukryta skrytka.
- `points/wounded_scout.md` - ranny zwiadowca jako NPC.

### Lokacje / Opcje Stref

- `zones/gate_inspect_area.md` - badanie okolicy bramy.

### Pułapki

- `traps/gate_alarm_wire.md` - goblińska linka alarmowa za bramą.

## Zasada

Nie musisz od razu wpisywać JSON-a. Opisz intencje, ograniczenia, informacje, konsekwencje i przykładowe deklaracje. Implementacja ma przełożyć to na mechanikę zgodną z `docs/SCENARIO_INTERACTION_FORM.md`.

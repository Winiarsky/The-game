# Campaign generation prompt

Uzyj tego promptu, kiedy chcesz, zeby AI wygenerowalo pierwszy zarys kampanii na podstawie wypelnionego briefu.

```text
Masz zaprojektowac pierwszy zarys kampanii dla repo The-game.

Traktuj `bandit_cave` jako benchmark integracji:
- `scenario_flows/bandit_cave.json`
- `scenarios/bandit_cave_cave_entrance.json`
- `scenarios/bandit_cave_treasure_room.json`
- `scenarios/bandit_cave_smuggler_docks.json`
- `player_ui/content/bandit_cave.json`
- `assets/ui_v2/bandit_cave/SCENARIO_BENCHMARK.md`

Nie kopiuj fabuly `bandit_cave`. Kopiuj tylko poziom kompletnosci: kilka map, przejscia, flagi, objectives, eventy, NPC, sekret, obiekt interaktywny, final i plan assetow.

Wejscie:
1. Przeczytaj `docs/campaign_authoring_guide.md`.
2. Przeczytaj wypelniony brief kampanii oparty o `docs/campaign_brief_template.md`.
3. Jesli brief ma luki, wypisz maksymalnie 5 najwazniejszych pytan. Jesli da sie przyjac rozsadne zalozenia, przyjmij je i oznacz jako zalozenia.

Wynik:
Wygeneruj dokument "Campaign outline v1" w tej strukturze:

1. Campaign overview
2. Map graph
3. Quest structure
4. NPC roster
5. Dialogue scripts
6. Narration beats
7. Flags
8. Scenario flow plan
9. Player UI plan
10. Asset plan
11. Golden path
12. Branching and consequences
13. Implementation checklist
14. Open questions

Wymagania:
- Kampania v1 ma miec 3-5 map.
- Ma miec 1 quest glowny i 2-4 questy poboczne.
- Ma miec 3-6 waznych NPC.
- Ma miec co najmniej 2 wybory z konsekwencjami zapisanymi we flagach.
- Ma miec co najmniej jedna mape opcjonalna.
- Ma miec co najmniej jeden sekret i jeden obiekt interaktywny z ryzykiem albo kosztem.
- Ma miec co najmniej dwa warianty zakonczenia.
- Ma miec pelniejsze dialogi dla co najmniej 3 waznych NPC.
- Kazdy objective musi miec `objective_id`, start, warunek ukonczenia i skutek.
- Kazdy NPC musi miec `npc_id`, mape, motywacje, wiedze, mozliwe odblokowanie i flagi.
- Kazdy dialog musi miec `dialogue_id`, `npc_id`, `map_id`, warunki dostepnosci, wejscie narratora, kwestie NPC, 3-5 wyborow gracza, odpowiedzi NPC i skutki zapisane jako flagi/objectives.
- Dialogi maja zawierac warianty po zmianie stanu, np. po uratowaniu NPC, odkryciu dowodu, ujawnieniu zdrady albo wejsciu do finalu.
- Narration beats maja zawierac gotowe teksty narratora dla startow map, odkryc sekretow, plot twistu i zakonczen.
- Kazda flaga musi miec wartosc poczatkowa i opis, co ja ustawia.
- Kazdy event w planie flow musi miec trigger, map_id, warunki i akcje na poziomie projektowym.
- Wskaz, ktore elementy da sie zrobic obecnym runtime, a ktore wymagaja rozszerzenia kodu.

Styl:
- Pisz konkretnie.
- Uzywaj stabilnych identyfikatorow snake_case.
- Nie generuj jeszcze pelnych plikow JSON, chyba ze zostaniesz o to poproszony.
- Nie dodawaj mechaniki, ktorej nie da sie powiazac z mapa, eventem, flaga, NPC albo objective.
```

## Nastepny krok po wygenerowaniu zarysu

Po zaakceptowaniu "Campaign outline v1" AI powinno wygenerowac paczke implementacyjna:

- `scenario_flows/<scenario_id>.json`
- `scenarios/<scenario_id>_<map_id>.json` dla kazdej mapy
- `player_ui/content/<scenario_id>.json`
- szkic `assets/ui_v2/<scenario_id>/manifest.json`
- `assets/ui_v2/<scenario_id>/IMAGE_PROMPTS.md`
- `assets/ui_v2/<scenario_id>/AUDIO_PROMPTS.md`
- testy kontraktowe dla flow i golden path

# Campaign brief template

Wypelnij ten szablon przed prosba o wygenerowanie kampanii. Pola oznaczone `TODO` sa wymagane dla sensownego pierwszego zarysu.

## 1. Podstawy

- `scenario_id`: TODO
- Tytul roboczy: TODO
- Ton: TODO
- Docelowy poziom druzyny: TODO
- Liczba graczy / bohaterow: TODO
- Czas gry: TODO
- Inspiracje, ktorych wolno uzyc: TODO
- Czego unikac: TODO

## 2. High concept

Opisz kampanie w 3-5 zdaniach:

TODO

## 3. Stawka

- Co zlego stanie sie, jesli druzyna nic nie zrobi?
- Dlaczego sprawa jest pilna?
- Co gracze moga zyskac?
- Co gracze moga stracic?

TODO

## 4. Glowny konflikt

- Glowny antagonista albo sila sprawcza: TODO
- Czego chce antagonista: TODO
- Co ukrywa: TODO
- Jak jego plan zmienia mapy albo NPC: TODO

## 5. Mapa kampanii

Wpisz planowane mapy. Dla pierwszej kampanii v1 celuj w 3-5 map.

### Map 1

- `map_id`: TODO
- Nazwa: TODO
- Funkcja fabularna: TODO
- Glowny problem: TODO
- Wazne obiekty: TODO
- Wejscia: TODO
- Wyjscia: TODO
- Sekrety: TODO
- Co zmienia sie po ukonczeniu mapy: TODO

### Map 2

- `map_id`: TODO
- Nazwa: TODO
- Funkcja fabularna: TODO
- Glowny problem: TODO
- Wazne obiekty: TODO
- Wejscia: TODO
- Wyjscia: TODO
- Sekrety: TODO
- Co zmienia sie po ukonczeniu mapy: TODO

### Map 3

- `map_id`: TODO
- Nazwa: TODO
- Funkcja fabularna: TODO
- Glowny problem: TODO
- Wazne obiekty: TODO
- Wejscia: TODO
- Wyjscia: TODO
- Sekrety: TODO
- Co zmienia sie po ukonczeniu mapy: TODO

### Opcjonalne dodatkowe mapy

TODO

## 6. Quest glowny

- `objective_id`: TODO
- Nazwa dla gracza: TODO
- Start: TODO
- Kroki: TODO
- Warunek ukonczenia: TODO
- Flagi ustawiane po drodze: TODO
- Finalny skutek: TODO

## 7. Questy poboczne

### Side quest 1

- `objective_id`: TODO
- Nazwa dla gracza: TODO
- Kto albo co go uruchamia: TODO
- Warunek ukonczenia: TODO
- Nagroda: TODO
- Konsekwencja fabularna: TODO

### Side quest 2

- `objective_id`: TODO
- Nazwa dla gracza: TODO
- Kto albo co go uruchamia: TODO
- Warunek ukonczenia: TODO
- Nagroda: TODO
- Konsekwencja fabularna: TODO

### Side quest 3 opcjonalny

TODO

## 8. NPC

### NPC 1

- `npc_id`: TODO
- Imie: TODO
- Mapa: TODO
- Rola: TODO
- Motywacja: TODO
- Co wie: TODO
- Co moze odblokowac: TODO
- Flagi: TODO
- Mozliwe wyniki interakcji: TODO

### NPC 2

- `npc_id`: TODO
- Imie: TODO
- Mapa: TODO
- Rola: TODO
- Motywacja: TODO
- Co wie: TODO
- Co moze odblokowac: TODO
- Flagi: TODO
- Mozliwe wyniki interakcji: TODO

### NPC 3

- `npc_id`: TODO
- Imie: TODO
- Mapa: TODO
- Rola: TODO
- Motywacja: TODO
- Co wie: TODO
- Co moze odblokowac: TODO
- Flagi: TODO
- Mozliwe wyniki interakcji: TODO

## 9. Dialogi

Wpisz pelniejsze sceny dialogowe. Dla waznego NPC daj 3-5 wyborow gracza i skutki we flagach.

### Dialogue 1

- `dialogue_id`: TODO
- `npc_id`: TODO
- `map_id`: TODO
- Kiedy dostepny: TODO
- Warunki flag: TODO
- Wejscie narratora: TODO
- Kwestia otwierajaca NPC: TODO
- Wybor gracza A: TODO
- Odpowiedz NPC A: TODO
- Skutek A / flagi / objective: TODO
- Wybor gracza B: TODO
- Odpowiedz NPC B: TODO
- Skutek B / flagi / objective: TODO
- Wybor gracza C: TODO
- Odpowiedz NPC C: TODO
- Skutek C / flagi / objective: TODO
- Wariant po powrocie: TODO

### Dialogue 2

- `dialogue_id`: TODO
- `npc_id`: TODO
- `map_id`: TODO
- Kiedy dostepny: TODO
- Warunki flag: TODO
- Wejscie narratora: TODO
- Kwestia otwierajaca NPC: TODO
- Wybor gracza A: TODO
- Odpowiedz NPC A: TODO
- Skutek A / flagi / objective: TODO
- Wybor gracza B: TODO
- Odpowiedz NPC B: TODO
- Skutek B / flagi / objective: TODO
- Wybor gracza C: TODO
- Odpowiedz NPC C: TODO
- Skutek C / flagi / objective: TODO
- Wariant po powrocie: TODO

### Dialogue 3 opcjonalny

TODO

## 10. Teksty narratora

Wpisz kluczowe narracje pod `show_prompt`, `show_log` i voiceover.

- Intro kampanii: TODO
- Start mapy 1: TODO
- Start mapy 2: TODO
- Start mapy 3: TODO
- Odkrycie sekretu: TODO
- Zwrot fabularny: TODO
- Final dobry: TODO
- Final alternatywny: TODO
- Final porazki albo kosztu: TODO

## 11. Wybory i konsekwencje

Wpisz 2-3 wybory, ktore maja realny skutek.

### Choice 1

- Sytuacja: TODO
- Opcja A: TODO
- Skutek A: TODO
- Opcja B: TODO
- Skutek B: TODO
- Flagi: TODO

### Choice 2

- Sytuacja: TODO
- Opcja A: TODO
- Skutek A: TODO
- Opcja B: TODO
- Skutek B: TODO
- Flagi: TODO

### Choice 3 opcjonalny

TODO

## 12. Sekrety i obiekty interaktywne

- Sekret 1: TODO
- Pulapka albo ryzyko: TODO
- Obiekt fabularny: TODO
- Loot albo informacja: TODO
- Skrot albo alternatywne przejscie: TODO

## 13. Flagi globalne

Wpisz robocze flagi stanu.

```text
TODO_flag_name=false
TODO_flag_name=false
TODO_flag_name=false
```

## 14. Zakonczenia

### Zakonczenie glowne

- Warunek: TODO
- Tekst wyniku: TODO

### Zakonczenie alternatywne

- Warunek: TODO
- Tekst wyniku: TODO

### Porazka albo koszt zwyciestwa

- Warunek: TODO
- Tekst wyniku: TODO

## 15. Assety

- Sceny map: TODO
- Portrety NPC: TODO
- Przeciwnicy: TODO
- Interactables: TODO
- Muzyka: TODO
- Ambience: TODO
- Voiceover: TODO

## 16. Ograniczenia techniczne

- Czy kampania ma uzywac tylko obecnych typow eventow: TODO
- Czy mozna dodac nowe NPC klasy: TODO
- Czy mozna dodac nowe interactables: TODO
- Czy mapy maja byc runtime JSON czy layered: TODO
- Inne ograniczenia: TODO

## 17. Notatki

TODO

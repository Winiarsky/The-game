# Formularz Interakcji

## 1. Typ Interakcji
lokacja / wyzwanie eksploracyjne

## 2. Nazwa
Przeszukanie dziedzińca

Id robocze / obecne id: `courtyard_search`

## 3. Gdzie Na Mapie
Strefa/lokacja: `courtyard` / Dziedziniec
Pole albo obszar na planszy: obszar dziedzińca, główny punkt strefy
Czy jest jawna od początku? po przejściu bramy

## 4. Opis Dla Graczy
TODO: opisz, co gracze widzą na dziedzińcu po wejściu.

Obecny opis roboczy:
Pusty dziedziniec z deskami, błotem, śladami walki i zawalonym wozem.

## 5. Informacje Dla MG / LLM
TODO: opisz prawdę za kulisami.

Obecnie: przeszukanie może ujawnić rannego zwiadowcę.

## 6. Rola Interakcji W Scenie
- [ ] cel sceny
- [x] trop/informacja
- [ ] zasób
- [x] ryzyko/komplikacja
- [ ] przejście do innej lokacji
- [ ] walka/encounter
- [x] klimat
- [ ] inne:

## 7. Stan Początkowy
Dla lokacji:
- stan fizyczny:
- czy jest zamknięty/uszkodzony/aktywny:
- czy jest niebezpieczny:

## 8. Co Gracze Mogą Realnie Próbować
- TODO
- TODO
- TODO

Obecne przykłady z contentu: sprawdzenie śladów w błocie, nasłuchiwanie, ostrożne przeszukanie wozu, obejrzenie krwi i tropów.

## 9. Czego Nie Powinno Się Dać Zrobić
- TODO

## 10. Intencje
Propozycja do weryfikacji:

```json
{
  "search": "allowed",
  "information": "allowed",
  "medical": "allowed",
  "stealth": "allowed_with_consequence",
  "force": "allowed_with_consequence",
  "theft": "blocked",
  "social": "blocked"
}
```

TODO: popraw statusy i dopisz lokalne limity/konsekwencje.

## 11. Informacje Do Odkrycia
Informacja 1:
- id robocze: `wounded_scout_presence`
- treść: TODO
- warunek ujawnienia:
- flaga po ujawnieniu:

## 12. Możliwe Efekty Mechaniczne
- ustawia flagę: `courtyard_searched`
- daje zasób:
- zabiera zasób:
- ujawnia punkt: `wounded_scout`
- odblokowuje lokację:
- zaczyna walkę:
- dodaje komplikację: TODO
- zmienia nastawienie NPC:
- inne:

## 13. Testy I Trudności
Czy chcesz konkretne ST, czy LLM ma dobrać tier z policy?

Dla jakich sytuacji:
- tropienie:
- nasłuchiwanie:
- przeszukanie wozu:
- szybkie/głośne przeszukanie:

## 14. Sukces / Porażka / Krytyczne Wyniki
Sukces:
- co się dzieje:
- jaki efekt mechaniczny:

Porażka:
- co się dzieje:
- jaki efekt mechaniczny:

Krytyczny sukces:
- co dodatkowo:

Krytyczna porażka:
- co się pogarsza:

## 15. Limity I Parametry
- liczba prób:
- koszt czasu:
- poziom hałasu:
- limit zasobów:

## 16. Czy Interakcja Ma Progres?
Tak.

Jeśli tak:
- ile punktów postępu potrzeba: obecnie `2`
- co daje postęp:
- co kończy interakcję: ujawnienie `wounded_scout`

## 17. Konsekwencje Długoterminowe
- NPC pamięta:
- zmienia się reputacja:
- odblokowuje quest:
- zmienia encounter:
- wpływa na zakończenie sceny:

## 18. Przykładowe Deklaracje Graczy
- "..."
- "..."
- "..."

## 19. Oczekiwany Feeling
- [ ] napięcie
- [x] tajemnica
- [ ] humor
- [ ] moralny dylemat
- [ ] szybka przeszkoda
- [ ] ważna rozmowa
- [ ] groza
- inne:

## 20. Uwagi
TODO

# Formularz Interakcji

## 1. Typ Interakcji
NPC

## 2. Nazwa
Ranny zwiadowca

Id robocze / obecne id: `wounded_scout`

## 3. Gdzie Na Mapie
Strefa/lokacja: `courtyard` / Dziedziniec
Pole albo obszar na planszy: `(8, 8)`
Czy jest jawna od początku? nie, ujawniany po przeszukaniu dziedzińca

## 4. Opis Dla Graczy
TODO

Obecny opis roboczy:
Pod zawalonym wozem leży ranny zwiadowca. Jest przytomny, ale osłabiony.

## 5. Informacje Dla MG / LLM
TODO: doprecyzuj, kim jest, czego wie, czego nie wie, czego się boi, co zablokuje informacje.

Obecnie: przestraszony i ranny; powinien zostać uspokojony albo opatrzony zanim zdradzi ważne informacje.

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
Dla NPC:
- emocje: przestraszony
- zdrowie: ranny
- nastawienie do drużyny: nieufny
- co robi teraz: leży pod zawalonym wozem

## 8. Co Gracze Mogą Realnie Próbować
- TODO

Przykłady: uspokoić, opatrzyć, wypytać, zastraszyć, okraść, zostawić.

## 9. Czego Nie Powinno Się Dać Zrobić
- TODO

Przykłady do weryfikacji: nie zna pełnego planu goblinów, nie ma magicznego klucza, nie powinien zdradzić informacji bez zaufania/pomocy.

## 10. Intencje
Docelowo użyć `intent_permissions`, nie ad hoc `allowed_actions`.

Propozycja do weryfikacji:

```json
{
  "social": "allowed",
  "medical": "allowed",
  "information": "locked",
  "theft": "allowed_with_consequence",
  "harm": "allowed_with_consequence",
  "magic": "blocked",
  "trade": "blocked",
  "gambling": "blocked"
}
```

TODO: dopisz lokalne limity, konsekwencje i warunki odblokowania informacji.

## 11. Informacje Do Odkrycia
Informacja 1:
- id robocze: `tower_hint`
- treść: TODO
- warunek ujawnienia: np. `scout_stabilized`
- flaga po ujawnieniu: `tower_hint_learned`

Informacja 2:
- id robocze: `hidden_cache_hint`
- treść: TODO
- warunek ujawnienia: np. `scout_trusts_party`
- flaga po ujawnieniu: `cache_hint_learned`

## 12. Możliwe Efekty Mechaniczne
- ustawia flagę: `scout_calmed`, `scout_treated`, `scout_stabilized`, `scout_trusts_party`, `scout_panicked`, `scout_robbed`
- daje zasób:
- zabiera zasób:
- ujawnia punkt:
- odblokowuje lokację:
- zaczyna walkę:
- dodaje komplikację:
- zmienia nastawienie NPC:
- inne:

## 13. Testy I Trudności
Czy chcesz konkretne ST, czy LLM ma dobrać tier z policy?

Dla jakich sytuacji:
- uspokojenie NPC:
- leczenie:
- przeszukanie:
- kradzież:
- zastraszenie:
- pytanie o informacje:

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
- maksymalna nagroda:
- minimalna/maksymalna stawka:
- liczba prób:
- koszt czasu:
- poziom hałasu:
- limit zasobów:

## 16. Czy Interakcja Ma Progres?
TODO

Możliwy model: zaufanie/stabilizacja jako flagi zamiast progress baru.

## 17. Konsekwencje Długoterminowe
- NPC pamięta:
- zmienia się reputacja:
- odblokowuje quest:
- zmienia encounter:
- wpływa na zakończenie sceny:

## 18. Przykładowe Deklaracje Graczy
- "Spokojnie, nie zrobimy ci krzywdy, chcemy pomóc."
- "Opatrujemy mu ranę i odsuwamy deski."
- "Pytamy, co widział na dziedzińcu."
- "Przeszukuję go, kiedy reszta odwraca jego uwagę."
- "Grożę mu, żeby powiedział wszystko od razu."

## 19. Oczekiwany Feeling
- [x] napięcie
- [x] tajemnica
- [ ] humor
- [x] moralny dylemat
- [ ] szybka przeszkoda
- [x] ważna rozmowa
- [ ] groza
- inne:

## 20. Uwagi
TODO

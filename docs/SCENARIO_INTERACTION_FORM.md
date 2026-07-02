# Formularz Interakcji Scenariusza

Ten formularz służy do projektowania spójnych interakcji dla NPC, obiektów, lokacji, przeszkód i wydarzeń.

Cel: autor scenariusza opisuje interakcję po ludzku, a implementacja przekłada ją na JSON contentu, `intent_permissions`, flagi, efekty mechaniczne, testy i ewentualne brakujące prymitywy runtime.

## Zasady

- LLM strukturyzuje deklaracje graczy, ale nie wykonuje efektów gry.
- Każdy efekt zmieniający stan gry musi mieć znany prymityw mechaniczny, np. `set_flag`, `grant_resource`, `reveal_information`, `start_challenge`, `offer_trade`.
- Globalne intencje powinny pochodzić z katalogu systemowego, a lokalna interakcja tylko je dopuszcza, blokuje albo ogranicza przez `intent_permissions`.
- Content szczegółowy należy do scenariusza, nie do kodu runtime.
- Jeśli czegoś nie da się jeszcze wyrazić istniejącym prymitywem, formularz powinien to ujawnić jako zadanie implementacyjne.

## Pełny Formularz

```markdown
# Formularz Interakcji

## 1. Typ Interakcji
NPC / obiekt / lokacja / przeszkoda / wydarzenie

## 2. Nazwa
Jak interakcja ma się nazywać w scenariuszu?

## 3. Gdzie Na Mapie
Strefa/lokacja:
Pole albo obszar na planszy:
Czy jest jawna od początku? tak/nie/warunkowo

## 4. Opis Dla Graczy
Co gracze widzą/słyszą/czują od razu?

## 5. Informacje Dla MG / LLM
Co jest prawdą za kulisami?
Czego NPC/obiekt chce?
Czego się boi?
Czego nie wie?
Jakie są ważne ograniczenia świata?

## 6. Rola Interakcji W Scenie
Po co ta interakcja istnieje?
- cel sceny
- trop/informacja
- zasób
- ryzyko/komplikacja
- przejście do innej lokacji
- walka/encounter
- klimat
- inne

## 7. Stan Początkowy
Dla NPC:
- emocje:
- zdrowie:
- nastawienie do drużyny:
- co robi teraz:

Dla obiektu/lokacji:
- stan fizyczny:
- czy jest zamknięty/uszkodzony/aktywny:
- czy jest niebezpieczny:

## 8. Co Gracze Mogą Realnie Próbować
Wypisz naturalnym językiem, nie mechanicznie:
- mogą spróbować...
- mogą spróbować...
- mogą spróbować...

## 9. Czego Nie Powinno Się Dać Zrobić
Twarde blokady i zakazane założenia:
- nie da się...
- ten NPC/obiekt nie wie...
- tego przedmiotu tu nie ma...
- magia/technologia/zasób X nie działa...

## 10. Intencje
Które globalne intencje mają sens?

Możesz opisać słownie albo użyć szkicu:

```json
{
  "social": "allowed",
  "information": "locked",
  "medical": "allowed",
  "theft": "allowed_with_consequence",
  "harm": "allowed_with_consequence",
  "magic": "blocked"
}
```

## 11. Informacje Do Odkrycia
Lista informacji, których gracze mogą się dowiedzieć.

Informacja 1:
- id robocze:
- treść:
- warunek ujawnienia:
- flaga po ujawnieniu:

Informacja 2:
- id robocze:
- treść:
- warunek ujawnienia:
- flaga po ujawnieniu:

## 12. Możliwe Efekty Mechaniczne
Co może się zmienić w stanie gry?

- ustawia flagę:
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

Przykłady:
- łatwe: ST 10
- średnie: ST 13
- trudne: ST 16
- bardzo trudne: ST 18+

Dla jakich sytuacji:
- uspokojenie NPC:
- leczenie:
- przeszukanie:
- kradzież:
- zastraszenie:
- badanie śladów:

## 14. Sukces / Porażka / Krytyczne Wyniki
Dla głównych typów działań:

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
Czy są wartości liczbowe?
- maksymalna nagroda:
- minimalna/maksymalna stawka:
- liczba prób:
- koszt czasu:
- poziom hałasu:
- limit zasobów:

## 16. Czy Interakcja Ma Progres?
Tak/nie

Jeśli tak:
- ile punktów postępu potrzeba:
- co daje postęp:
- co kończy interakcję:

## 17. Konsekwencje Długoterminowe
Czy to ma wrócić później?
- NPC pamięta:
- zmienia się reputacja:
- odblokowuje quest:
- zmienia encounter:
- wpływa na zakończenie sceny:

## 18. Przykładowe Deklaracje Graczy
Podaj 3-8 zdań, które gracze mogliby wpisać:

- "..."
- "..."
- "..."

## 19. Oczekiwany Feeling
Jak to ma się czuć przy stole?
- napięcie
- tajemnica
- humor
- moralny dylemat
- szybka przeszkoda
- ważna rozmowa
- groza
- inne

## 20. Uwagi
Cokolwiek dodatkowego.
```

## Krótki Formularz

Użyj tego wariantu, jeśli interakcja jest jeszcze tylko pomysłem.

```markdown
# Krótki Formularz Interakcji

Typ:
Nazwa:
Gdzie:
Opis dla graczy:
Prawda dla MG:
Po co istnieje:
Co gracze mogą próbować:
Czego nie wolno / czego tu nie ma:
Informacje do odkrycia:
Efekty mechaniczne:
Przykładowe deklaracje graczy:
Feeling:
```

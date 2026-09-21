# Terminologia wydruków

Nazwy mechaniczne wyróżniamy pogrubieniem w opisach zasad. Odmiany fleksyjne
pozostają naturalne: „wpływ”, „wpływu”; „rzut obronny”, „rzutu obronnego”.
Lista form jest w `content/characters/karty_postaci.json` → `keywords`; treść jest escapowana przed generowaniem HTML.
Nie pogrubiamy historii postaci, aby zwykłe użycie słowa nie wyglądało jak reguła.

| Nazwa | Znaczenie w tej grze |
| --- | --- |
| Pula many | Karty zatrzymane przez jednego bohatera. |
| Punkty many | Suma wartości kart według tabeli tej postaci. |
| Naładowanie | Premia do testu wynikająca z progu punktowego: +0/+2/+4/+6. Pełna nazwa: premia z naładowania. |
| Nasycenie | Zdolności pasywne uruchamiane kolorami posiadanych kart. |
| Spalanie | Koszt ze wspólnej talii, rozliczany po efekcie. Osobista pula pozostaje. |
| Podbicie | Opcjonalne wzmocnienie zdolności, zwykle +2 spalone karty za każde. |
| Mana Drain | Brak kart do wymaganej operacji: reset many w walce, koniec konfrontacji w eksploracji. |
| Wpływ | Efekt udanej próby społecznej, zmniejszający opór NPC. |
| Postęp | Efekt udanej próby przy obiekcie, zmniejszający opór zadania. |
| Opór | Pozostała trudność konfrontacji; nie punkty życia NPC ani obiektu. |
| Podatność | Profil metody określający ST i kość wpływu lub postępu. |
| Modyfikator cechy | Premia wyliczona z cechy; np. Siła 18 daje +4. Skrót: mod. |
| Test ataku | Rzut atakującego przeciw KP celu. |
| Rzut obronny | Rzut celu przeciw ST efektu. Nie nazywamy go „obroną KON”. |
| Przewaga / utrudnienie | 2k20, wyższy / niższy wynik. |
| KP / PW / ST | Klasa pancerza / punkty wytrzymałości / stopień trudności. |
| Tura / runda | Działania jednego uczestnika / komplet tur uczestników. |
| Przybory magiczne / instrument | Nazwa miejsca na macie wyposażenia; wewnętrzny identyfikator `focus` pozostaje bez zmian. |

Zamiast „ognisko kapłańskie” piszemy, że święty symbol jest używany do czarów.
Zamiast „własna flanka” — „wróg, którego flankujesz”. Nie stosujemy kodów T/O
na akcjach: podajemy wprost, kiedy efekt się kończy. Rozdzielamy test ataku,
obrażenia, wpływ i postęp. Naładowania nie dolicza się do trzech ostatnich.

## Źródła i zakres

Aktualna mechanika pochodzi z kodu gry i jej katalogów. Redakcja wydruku nie
przywraca biegłości, umiejętności ani mechaniki blackjacka ze starszych wersji.
`copy.json` przechowuje opisy, `player_aid.json` cztery strony wspólnego pomocnika.

Przy sprawdzaniu rozróżnienia tury, rundy, akcji i reakcji konsultowano
[oficjalne Basic Rules D&D — Combat](https://www.dndbeyond.com/sources/dnd/basic-rules-2014/combat).
To punkt odniesienia dla pojęć, a nie źródło naszych kosztów many, nasycenia
ani konfrontacji eksploracyjnych. Polskie sformułowania są własną redakcją,
nie deklaracją oficjalnego tłumaczenia podręcznika.

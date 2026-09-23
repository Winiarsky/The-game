# Reputacja drużyny — makieta 22.09.2026

Aktualizacja klikalnej [makiety](ui/prototype.html). Zastępuje wsparcie runami
w rozmowach z NPC. Runy pozostają przyciskami planszy oraz zasobem walki.
Zmiana nie jest jeszcze podłączona do silnika gry, zapisu kampanii ani hardware.

Późniejsza korekta: dobór run odbywa się tylko w pierwszej rundzie walki,
z ilustracją posterunku. Kolejne rundy nie odnawiają puli; ręce pozostają.
Przejście od wozu do walki otwiera ten pierwszy dobór.

## Zatwierdzone zasady

- Wspólna reputacja drużyny zaczyna się od **20**. Saldo przechodzi między
  scenami. Rozmowa i kolejna runda nie odnawiają reputacji.
- Gracz wybiera podejście (np. komplementy lub argumenty) i od razu rzuca k20.
- W podsumowaniu wybiera najwyżej **jedną z trzech osobnych opcji**:

| Przycisk planszy | Efekt | Koszt reputacji |
| --- | --- | --- |
| Rozwidlenie | +1 do testu | 1 |
| Wieża | +5 do testu | 3 |
| Klepsydra | Dodatkowa k20; zachowaj wyższy naturalny wynik | 5 |

Opcje się nie sumują. Runy odróżniają wybór dostępny, wybrany i niedostępny.
Przy braku punktów droższe opcje są wygaszone; test nadal można zakończyć.
Ponowne naciśnięcie wybranej runy lub ↩ usuwa wybór przed zatwierdzeniem.
`+` i `−` nie kupują premii: wpisują wynik kości albo przewijają ekran.

Premię +1/+5 opłaca się wraz z zatwierdzeniem rezultatu. Dodatkową k20 opłaca
się przed jej rzutem, również jeśli wynik będzie niższy. Po poznaniu drugiej
kości nie ma zwrotu ani możliwości dokupienia premii. Wynik i tor postępu
rozliczają się dopiero po potwierdzeniu podsumowania.

Zamiana wozu wymaga **bieżącej reputacji co najmniej 20** i kosztuje **3**.
Warunek jest sprawdzany przed pobraniem kosztu: 20 → 17 jest poprawne.
Zamiana kończy konfrontację bez testu i zmęczenia; anulowanie nic nie kosztuje.

## Doprecyzowania w makiecie

- Naturalne 1/20 zachowują krytyki. +1/+5 nie zmienia naturalnej kości.
  Dodatkowa k20 może zastąpić naturalną 1; naturalna 20 nie potrzebuje wsparcia.
- Rozmowa nadal trwa jedną rundę; sukces przesuwa tor o 1, krytyczny sukces
  o 2, porażka o 0, krytyczna porażka o −1. Dotychczasowe warunki końca pozostają.
- Fizyczne podejścia do wydobycia wozu nie korzystają z reputacji. W tej scenie
  społecznym zastosowaniem reputacji jest żądanie zamiany.
- Menu → „Ukończona misja” prezentuje jednorazową nagrodę **+5**. To robocza
  wartość do demonstracji odnawiania, nie uzgodniony balans nagród kampanii.
- „Nowa wyprawa” rozpoczyna nową próbę makiety z 20 reputacji. Przełączanie
  scen zachowuje saldo; przeładowanie pliku resetuje lokalną makietę.

Przykład: wynik 10 + cecha 0 przeciw ST 14. Opcja +1 za 1 daje 11 i nadal
porażkę, +5 za 3 daje 15 i sukces. Opcja drugiej kości za 5 daje kolejną
szansę, ale jej koszt pozostaje nawet po niskim rzucie. Każdy wydatek z salda
20 zamknie późniejszą zamianę wozu, dopóki drużyna nie odzyska reputacji.

## Następne decyzje projektowe

Ceny sklepowe, pozostałe progi dialogowe i reputacja za konkretne decyzje
fabularne wymagają tabel w scenariuszach. Nie przyjęto jeszcze wartości zniżek
ani pełnej listy nagród. Przy integracji potrzebne będą zapis salda kampanii
i ochrona nagród przed ponownym odebraniem po wczytaniu.

Sprawdzenia: `tests/unit/test_rune_prototype_browser.py` obejmuje wybór jednej
opcji, koszty 1/3/5, drugi rzut, brak zwrotu po rzucie, krytyki, próg wozu,
koszt zamiany, brak automatycznego odnowienia i jednorazową nagrodę.

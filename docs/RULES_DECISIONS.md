# Decyzje Zasad D&D 5e

Ten plik jest lokalnym zapisem tego, jak projekt interpretuje i implementuje konkretne zasady Dungeons & Dragons 5e.

Nie jest to pełna kopia podręcznika ani encyklopedia D&D. Ma zawierać krótkie, praktyczne decyzje potrzebne do implementacji i testów.

## Zasada Aktualizacji

Po każdej implementacji nowej mechaniki D&D należy dopisać albo zaktualizować odpowiednią sekcję w tym pliku.

Dotyczy to zwłaszcza:

- ruchu,
- rzutów,
- ataków,
- obrażeń,
- osłony,
- przewagi i utrudnienia,
- inicjatywy,
- stanów,
- czarów,
- reakcji,
- ataków okazyjnych.

Każda sekcja powinna zawierać:

- nazwę mechaniki,
- krótki opis decyzji implementacyjnej,
- zakres MVP,
- rzeczy poza zakresem,
- odnośnik do testów,
- źródło albo notatkę, że reguła wymaga późniejszej weryfikacji.

## Szablon Sekcji

```md
## Nazwa Mechaniki

Status: planned / implemented / partial

Źródło:
- TODO: SRD 5.1 / SRD 5.2 / inna decyzja projektowa

Implementacja MVP:
- ...

Poza zakresem MVP:
- ...

Odstępstwa / decyzje planszowe:
- ...

Testy:
- `tests/unit/...`
```

## Ruch Po Planszy

Status: partial

Źródło:

- `GAME_DESIGN.md`
- TODO: zweryfikować względem SRD / zasad ruchu na siatce przed rozbudową o reakcje, rozmiary istot i ruch wymuszony.

Implementacja MVP:

- Jedno pole planszy odpowiada 5 feet.
- Ruch ortogonalny kosztuje 5 feet.
- Ruch diagonalny jest dozwolony i kosztuje 5 feet.
- Trudny teren kosztuje 10 feet za wejście na pole.
- Sojusznik zajmuje pole, przez które można przejść, ale traktujemy je jako trudny teren.
- Przeciwnik blokuje przejście i zakończenie ruchu.
- Aktor nie może zakończyć ruchu na polu zajętym przez inną istotę.
- Ściany i blokujące przeszkody blokują przejście.
- Zamknięte drzwi blokują ruch, otwarte drzwi nie blokują ruchu.
- Ruch po skosie przez całkowicie zablokowany róg jest niedozwolony.

Poza zakresem MVP:

- wariant diagonalny 5/10,
- rozmiary istot,
- przeciskanie się,
- skakanie,
- wspinaczka,
- pływanie,
- latanie,
- ruch wymuszony.

Odstępstwa / decyzje planszowe:

- Diagonalny ruch kosztuje stale 5 feet, ponieważ jest prostszy do wizualizacji LED i płynniejszy na fizycznej planszy.

Testy:

- `tests/unit/test_coordinates.py`
- `tests/unit/test_neighbors.py`
- `tests/unit/test_movement_cost.py`
- `tests/unit/test_movement_blocking.py`
- `tests/unit/test_pathfinding.py`
- `tests/unit/test_led_feedback.py`

## Rzuty Kośćmi

Status: implemented

Źródło:

- `GAME_DESIGN.md`
- TODO: zweryfikować względem SRD dla rzutów d20, przewagi, utrudnienia i trafień krytycznych.

Implementacja MVP:

- Gracze i Mistrz Gry rzucają fizycznymi kośćmi.
- Przed rzutem aplikacja pokazuje warunki rzutu: normalny rzut, przewagę albo utrudnienie.
- Przed rzutem aplikacja pokazuje aktywne bonusy i minusy, odrzucone duplikaty oraz końcowy modyfikator.
- Aplikacja pyta o jeden naturalny wynik rzutu.
- Dla przewagi aplikacja instruuje gracza, aby rzucił `2d20` i wpisał wyższy wynik.
- Dla utrudnienia aplikacja instruuje gracza, aby rzucił `2d20` i wpisał niższy wynik.
- Aplikacja dodaje tylko aktywne modyfikatory i rozstrzyga wynik.
- Modyfikatory bez `stacking_key` sumują się.
- Modyfikatory z tym samym `stacking_key` traktujemy jako ten sam efekt, więc nie stackują się.
- Z duplikatów dodatnich wybierany jest najwyższy bonus.
- Z duplikatów ujemnych wybierana jest najsilniejsza kara.
- Odrzucone duplikaty pozostają widoczne w breakdown, ale nie liczą się do końcowego wyniku.
- Naturalne `20` przy rzucie ataku oznacza trafienie krytyczne.
- Naturalne `1` przy rzucie ataku oznacza automatyczne pudło.
- Naturalne `20` i `1` przy testach cech nie oznaczają automatycznego sukcesu/porażki w MVP.

Poza zakresem MVP:

- obowiązkowy cyfrowy roller kości,
- automatyczne rozpoznawanie rzutów kamerą,
- automatyczne wyliczanie wszystkich bonusów z pełnej karty postaci, klas, czarów i ekwipunku,
- szczegółowe rozbijanie wszystkich kości obrażeń w UI.

Odstępstwa / decyzje planszowe:

- Domyślnym modelem są fizyczne kości, nie cyfrowy roller.
- Przewaga i utrudnienie nie są bonusami liczbowymi i nie trafiają do listy modyfikatorów.
- Obrażenia, typy obrażeń i kości obrażeń są osobnym modelem późniejszego etapu.

Testy:

- `tests/unit/test_dice.py`
- `tests/unit/test_checks.py`
- `tests/unit/test_attack_rolls.py`

## Inicjatywa

Status: implemented

Źródło:

- `GAME_DESIGN.md`
- TODO: zweryfikować względem SRD przed dodaniem zaskoczenia, gotowych akcji i efektów zmieniających kolejkę.

Implementacja MVP:

- Rozpoczęcie walki poprzedza setup jawnych figurek i elementów otoczenia.
- Komunikaty aplikacji i LED-y są zsynchronizowane: świeci tylko to, czego dotyczy aktualny krok.
- Bohaterowie są wywoływani do rzutu inicjatywy po kolei.
- Bohater rzuca fizycznie `1d20` i wpisuje jeden naturalny wynik.
- Przed rzutem aplikacja pokazuje warunki rzutu i aktywne modyfikatory.
- Przeciwnicy kontrolowani przez aplikację mają inicjatywę rzuconą automatycznie.
- Automatyczny rzut przeciwnika używa wstrzykiwanego RNG, żeby testy były deterministyczne.
- Kolejność inicjatywy sortuje po najwyższym wyniku końcowym.
- Remis rozstrzyga wyższy modyfikator ze Zręczności.
- Pełny remis zachowuje stabilną kolejność wejściową.
- Po ostatnim aktorze kolejka wraca na początek i zwiększa rundę.
- Pokonani aktorzy mogą pozostać w kolejce, ale przechodzenie tury może ich pomijać.

Poza zakresem MVP:

- zaskoczenie,
- opóźnianie tury,
- gotowe akcje,
- reakcje,
- efekty dynamicznie zmieniające inicjatywę,
- skanowanie pól jako potwierdzenie setupu.

Odstępstwa / decyzje planszowe:

- Klikanie pionka nie jest wymagane do ustalenia, kto rzuca inicjatywę.
- Jawne elementy setupu są podświetlane LED-ami, ukryte i warunkowe elementy nie są zdradzane graczom.

Testy:

- `tests/unit/test_ability_modifiers.py`
- `tests/unit/test_encounter_setup.py`
- `tests/unit/test_setup_led_feedback.py`
- `tests/unit/test_initiative.py`
- `tests/unit/test_initiative_led_feedback.py`
- `tests/unit/test_demo_initiative_setup.py`

## Atak I Obrażenia

Status: planned

Źródło:

- `GAME_DESIGN.md`
- TODO: zweryfikować względem SRD dla attack roll, AC, damage roll i critical hit.

Implementacja MVP:

- Atak porównuje wynik ataku z AC celu.
- Naturalne `20` przy ataku oznacza trafienie krytyczne.
- Naturalne `1` przy ataku oznacza automatyczne pudło.
- Przy trafieniu aplikacja prosi o wynik obrażeń.
- W MVP gracz może wpisać końcowy wynik obrażeń krytycznych samodzielnie.
- Obrażenia zmniejszają HP celu.
- Stan pokonania/śmierci jest uproszczony w MVP.

Poza zakresem MVP:

- reakcje,
- ataki okazyjne,
- odporności i podatności,
- pełne death saving throws,
- efekty wielu typów obrażeń w jednym ataku.

Odstępstwa / decyzje planszowe:

- Szczegółowe zasady śmierci i umierania zostają odłożone, dopóki nie będą potrzebne w pierwszej scenie.

Testy:

- TODO: `tests/unit/test_attack_resolution.py`
- TODO: `tests/unit/test_damage.py`

# Roadmap Projektu

Efektem końcowym projektu ma być grywalny port Dungeons & Dragons 5e na fizyczną planszę 20x30, obsługiwany przez aplikację i system LED.

Gra ma wspierać:

- taktyczne encountery,
- fizyczne figurki i kości,
- planszę jako interfejs wejścia/wyjścia,
- aplikację jako silnik zasad i asystenta Mistrza Gry,
- interakcje społeczne,
- eksplorację,
- krótką kampanię z kilkoma scenami.

Ten dokument opisuje master plan. `TODO.md` służy do bieżących małych zadań.

## Zasady Roadmapy

- Każdy etap powinien kończyć się czymś działającym.
- Najpierw budujemy stabilny rdzeń, potem UI i content.
- Mechaniki D&D 5e dodajemy stopniowo.
- Po implementacji mechaniki aktualizujemy `docs/RULES_DECISIONS.md`.
- Każdy większy etap powinien mieć testy jednostkowe, testy integracyjne i checklistę manualną, jeśli dotyka planszy.
- Nie dodajemy pełnego systemu D&D naraz.

## Etap 0: Fundament Projektu

Status: w toku.

Cel: przygotować repozytorium, dokumenty, strukturę i sposób pracy.

Zakres:

- [x] zarchiwizować poprzednią aplikację w `legacy/previous_app/`,
- [x] zostawić niskopoziomową warstwę `board/`,
- [x] przygotować `PROJECT_CONTEXT.md`,
- [x] przygotować `GAME_DESIGN.md`,
- [x] przygotować `ARCHITECTURE.md`,
- [x] przygotować `TODO.md`,
- [x] przygotować workflow testów,
- [x] przygotować checklistę manualną planszy,
- [x] przygotować koncepcję obserwacji sesji,
- [x] przygotować `docs/RULES_DECISIONS.md`,
- [x] przygotować `ROADMAP.md`.

Kryterium zakończenia:

- projekt ma jasne dokumenty startowe,
- wiadomo, gdzie pisać kod,
- wiadomo, jak testować,
- wiadomo, jak dokumentować decyzje zasad.

## Etap 1: Czysty Rdzeń Planszy I Ruchu

Cel: stworzyć deterministyczny, testowalny model planszy i ruchu bez UI oraz hardware.

Zakres:

- `Coordinate`,
- wymiary planszy 20x30,
- walidacja granic planszy,
- sąsiedzi ortogonalni i diagonalni,
- teren normalny i trudny,
- blokujące pola,
- ściany między polami,
- drzwi otwarte/zamknięte,
- zajęte pola,
- podstawowe rozróżnienie sojusznik/przeciwnik/neutralny,
- koszt ruchu,
- zasięg ruchu,
- wyznaczanie ścieżki,
- zakaz przechodzenia po skosie przez zablokowany róg.

Testy:

- unit testy dla koordynatów,
- unit testy dla sąsiadów,
- unit testy dla kosztów ruchu,
- unit testy dla ścian i przeszkód,
- unit testy dla pathfindingu.

Kryterium zakończenia:

- dla aktora ze `Speed = 30 feet` system potrafi wyznaczyć osiągalne pola,
- wynik jest deterministyczny,
- logika nie importuje `board`,
- testy przechodzą przez `scripts/safe_pytest.sh`.

## Etap 2: Rzuty Kośćmi I Podstawowe Reguły D&D 5e

Cel: obsłużyć fizyczne rzuty kośćmi wpisywane do aplikacji.

Zakres:

- naturalny wynik rzutu,
- modyfikator,
- wynik końcowy,
- przewaga,
- utrudnienie,
- rzuty ataku,
- testy cech,
- rzuty obronne,
- inicjatywa,
- naturalne `20` i `1` dla ataków,
- deterministyczne modele wyników do testów.

Testy:

- unit testy dla zwykłego rzutu d20,
- unit testy dla przewagi,
- unit testy dla utrudnienia,
- unit testy dla naturalnego `20`,
- unit testy dla naturalnego `1`,
- unit testy dla rozróżnienia naturalnego wyniku i wyniku końcowego.

Kryterium zakończenia:

- silnik potrafi rozstrzygnąć podstawowy rzut d20 bez losowości,
- dane rzutu nadają się do zapisania w obserwacji sesji,
- `docs/RULES_DECISIONS.md` jest zaktualizowany.

## Etap 3: Aktorzy, HP I Inicjatywa

Cel: stworzyć podstawowy model istot i kolejności tur.

Zakres:

- wspólny model `Actor`,
- bohater testowy,
- potwór testowy,
- AC,
- HP,
- temporary HP,
- speed,
- ability scores,
- pozycja,
- initiative bonus,
- kolejność inicjatywy,
- aktywny aktor,
- stan pokonania/śmierci w uproszczonym MVP.

Testy:

- unit testy modelu aktora,
- unit testy HP i temporary HP,
- unit testy inicjatywy,
- unit testy przechodzenia tury.

Kryterium zakończenia:

- można utworzyć jednego bohatera i jednego potwora,
- można ustawić ich na planszy,
- można ustalić kolejność tur,
- system wie, kto jest aktywnym aktorem.

## Etap 4: Atak, Obrażenia I Pierwszy Mini-Combat

Cel: umożliwić prostą walkę 1 bohater vs 1 potwór bez UI produkcyjnego.

Zakres:

- deklaracja ataku melee,
- sprawdzenie legalnego celu,
- rzut ataku wpisywany ręcznie,
- porównanie z AC,
- trafienie,
- pudło,
- trafienie krytyczne,
- automatyczne pudło,
- wpisanie obrażeń,
- odjęcie HP,
- zakończenie walki po pokonaniu jednej strony.

Testy:

- unit testy ataku,
- unit testy obrażeń,
- unit testy trafienia krytycznego,
- unit testy automatycznego pudła,
- integracyjny test mini-walki bez hardware.

Kryterium zakończenia:

- terminalowy albo testowy runtime potrafi przeprowadzić prostą walkę 1v1,
- wszystkie decyzje są zapisane w obserwacji sesji,
- testy przechodzą.

## Etap 5: Obserwacja Sesji I Runtime Debugowy

Cel: mieć wspólny punkt odniesienia do debugowania rozgrywki.

Zakres:

- lokalny zapis JSONL,
- `session_started`,
- `turn_started`,
- `movement_range_calculated`,
- `movement_path_selected`,
- `roll_entered`,
- `roll_resolved`,
- `attack_resolved`,
- `damage_applied`,
- `session_error`,
- prosty runtime debugowy w terminalu albo minimalnym web UI.

Testy:

- unit testy formatowania eventów,
- test zapisu do katalogu tymczasowego,
- test kolejności `seq`,
- test czy runtime tworzy plik obserwacji.

Kryterium zakończenia:

- po sesji istnieje plik `.jsonl`,
- plik da się otworzyć i przeanalizować bez aplikacji,
- przy zgłoszeniu błędu można odtwórczo ustalić, co się wydarzyło.

## Etap 6: Adapter Planszy I Wizualizacja LED

Cel: połączyć czystą logikę ruchu i celu z fizyczną planszą albo symulatorem.

Zakres:

- adapter wokół `board.Connection`,
- zamiana `reachable_tiles` na ramki LED,
- zamiana `selected_path` na ramki LED,
- wizualizacja aktywnego aktora,
- wizualizacja celu ataku,
- feedback trafienia/pudła/obrażeń,
- testy w symulatorze,
- manualna checklista hardware.

Testy:

- unit testy generowania ramek LED bez hardware,
- integracyjne testy adaptera z fake connection,
- manualne testy w symulatorze,
- manualne testy na fizycznej planszy.

Kryterium zakończenia:

- ruch aktora jest widoczny na LED,
- ścieżka jest widoczna na LED,
- cele ataku są widoczne na LED,
- warstwa zasad nadal nie importuje `board`.

## Etap 7: Pierwsza Grywalna Scena

Cel: przejść od mini-combatu do pierwszej sceny stołowej.

Zakres:

- 2 bohaterów,
- 3 potwory,
- jedna prosta mapa z przeszkodami,
- jeden NPC albo obiekt interaktywny,
- prosty cel sceny,
- tury i walka,
- prosta interakcja przed albo po walce,
- podsumowanie wyniku.

Testy:

- test ładowania sceny,
- test rozmieszczenia aktorów,
- test zakończenia walki,
- test podstawowej interakcji,
- manualna próba przejścia całej sceny.

Kryterium zakończenia:

- da się rozegrać krótką scenę od początku do końca,
- gracze używają planszy, figurek i fizycznych kości,
- aplikacja prowadzi stan i feedback LED.

## Etap 8: Interakcje Społeczne I Eksploracja

Cel: dodać więcej niż walkę, bez budowania pełnej kampanii.

Zakres:

- obiekty interaktywne,
- proste dialogi NPC,
- wybory gracza,
- testy cech wpisywanymi rzutami,
- konsekwencje wyborów,
- podświetlanie punktów zainteresowania LED,
- proste flagi sceny.

Testy:

- unit testy interakcji,
- testy flag sceny,
- testy wyborów,
- manualna checklista eksploracji.

Kryterium zakończenia:

- scena może zawierać rozmowę, obiekt albo test umiejętności,
- wynik interakcji wpływa na stan sceny.

## Etap 9: Pierwszy Stabilny Zestaw Contentu D&D

Cel: uporządkować lokalne dane potrzebne do pierwszych scen i potwierdzić format contentu przed większą rozbudową.

Zakres:

- schemat potwora,
- schemat broni,
- schemat aktora testowego,
- schemat scenariusza,
- pierwszy stabilny zestaw potworów,
- pierwszy stabilny zestaw broni,
- pierwszy stabilny zestaw obiektów interaktywnych,
- attribution/licencje dla danych SRD, jeśli używane.

Testy:

- walidacja JSON,
- test ładowania contentu,
- test brakujących pól,
- test stabilnych identyfikatorów.

Kryterium zakończenia:

- pierwsze sceny nie mają danych zaszytych w kodzie,
- dane są czytelne i wersjonowalne,
- format danych nadaje się do rozbudowy,
- nie kopiujemy niepotrzebnych opisów podręcznikowych.

## Etap 10: Pierwszy Stabilny UI Dla Prowadzenia Gry

Cel: zastąpić runtime debugowy pierwszym stabilnym interfejsem używalnym przy stole.

Zakres:

- ekran aktywnego aktora,
- panel tury,
- wpisywanie rzutów,
- wybór akcji,
- podgląd HP,
- podgląd inicjatywy,
- komunikaty dla graczy,
- połączenie z planszą/symulatorem,
- dostęp do obserwacji sesji.

Testy:

- testy API albo warstwy aplikacyjnej,
- manualne testy przepływu tury,
- manualne testy połączenia z planszą.

Kryterium zakończenia:

- da się prowadzić pierwszą scenę bez pracy bezpośrednio w terminalu,
- UI nie miesza się z silnikiem zasad,
- UI nadaje się do rozbudowy bez przepisywania rdzenia aplikacji.

## Etap 11: Mała Kampania

Cel: przygotować krótką kampanię demonstracyjną.

Zakres:

- 3-5 scen,
- przynajmniej 2 encountery,
- przynajmniej 2 interakcje społeczne,
- przynajmniej 2 obiekty eksploracyjne,
- proste przejścia między scenami,
- zapis postępu,
- podsumowanie sesji.

Testy:

- test ładowania kampanii,
- test przejść między scenami,
- test zachowania flag,
- manualne przejście kampanii.

Kryterium zakończenia:

- da się rozegrać krótką kampanię przy stole,
- plansza i aplikacja są używane razem,
- mechaniki są stabilne na tyle, żeby poprawiać content zamiast walczyć z runtime.

## Etap 12: Stabilizacja I Playtest

Cel: poprawić realne problemy po graniu.

Zakres:

- poprawki UX,
- poprawki manualnych checklist,
- poprawki obserwacji sesji,
- redukcja tarcia przy stole,
- lepsze komunikaty,
- porządkowanie testów,
- dokumentacja uruchamiania.

Kryterium zakończenia:

- projekt da się uruchomić według dokumentacji,
- nowa osoba może przejść checklistę,
- błędy da się diagnozować z obserwacji sesji,
- gra jest faktycznie grywalna.

## Etap 13: Rozbudowany Katalog D&D

Cel: rozszerzyć pierwszy stabilny zestaw contentu do większego katalogu użytecznego w wielu scenach i kampaniach.

Ten etap powinien ruszyć dopiero po potwierdzeniu, że schematy z etapu 9 działają w praktyce.

Zakres:

- większy katalog potworów,
- większy katalog broni,
- pancerze i tarcze,
- podstawowy ekwipunek,
- podstawowe warunki,
- wybrane czary potrzebne do kampanii,
- akcje specjalne potworów,
- walidacja danych contentu,
- attribution/licencje dla danych SRD,
- narzędzia do audytu brakujących pól.

Testy:

- testy walidacji całego katalogu,
- testy ładowania losowo wybranych potworów/przedmiotów,
- testy stabilności identyfikatorów,
- testy kompatybilności danych ze scenariuszami.

Kryterium zakończenia:

- content jest wystarczający do budowy wielu encounterów bez ręcznego dopisywania danych w kodzie,
- katalog jest spójny i walidowany,
- dane są zgodne z przyjętą strategią licencji.

## Etap 14: Docelowy UI Kampanii

Cel: rozbudować pierwszy stabilny UI do interfejsu wygodnego przy prowadzeniu kampanii, a nie tylko pojedynczej sceny.

Ten etap powinien wynikać z realnych playtestów, a nie z założeń z początku projektu.

Zakres:

- widok kampanii,
- lista scen,
- przejścia między scenami,
- stan drużyny,
- stan NPC,
- stan questów lub celów,
- historia sesji,
- podgląd obserwacji sesji,
- wygodniejsze zarządzanie encounterami,
- lepsze komunikaty dla graczy,
- narzędzia dla Mistrza Gry,
- opcjonalne widoki dla graczy.

Testy:

- testy przepływu kampanii,
- testy zachowania stanu między scenami,
- testy API/UI dla kluczowych akcji,
- manualny playtest krótkiej kampanii.

Kryterium zakończenia:

- UI pozwala wygodnie prowadzić krótką kampanię,
- użytkownik nie musi znać struktury plików projektu,
- debugowanie nadal opiera się na obserwacji sesji,
- silnik zasad pozostaje oddzielony od UI.

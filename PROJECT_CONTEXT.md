# Kontekst Projektu

Budujemy nową lokalną aplikację do prowadzenia taktycznej gry RPG w stylu Dungeons & Dragons 5e na fizycznej planszy 20x30 z podświetleniem LED i wykrywaniem pól.

Poprzednia aplikacja została zarchiwizowana w `legacy/previous_app/`. Używała mechanik zbliżonych do Pathfindera i z czasem zbyt mocno połączyła logikę gry, UI, scenariusze i hardware. Nowy projekt ma zachować tylko niskopoziomową komunikację z planszą/LED oraz wybrane pomysły techniczne opisane w `legacy/LEGACY_DESCRIPTION.md`.

## Cel Jednym Zdaniem

Aplikacja ma działać jak cyfrowy prowadzący i silnik zasad dla planszowej gry D&D 5e, w której gracze nadal fizycznie używają planszy, figurek i kości.

## Język Aplikacji

Docelowy język aplikacji dla graczy i Mistrza Gry to polski.

Zasady:

- komunikaty widoczne dla graczy piszemy po polsku,
- instrukcje wykonywania rzutów piszemy po polsku,
- nazwy własne i rozpoznawalne terminy D&D można zostawić po angielsku, jeżeli tłumaczenie byłoby mniej czytelne,
- nazwy techniczne w kodzie, API, enumach, testach i plikach mogą pozostać po angielsku,
- dokumenty robocze mogą używać angielskich nazw mechanik, jeśli są nazwami własnymi albo ułatwiają mapowanie do D&D 5e.

## Typ Gry

To nie ma być pełne VTT. Fizyczna plansza jest głównym medium między aplikacją a graczami, trochę jak kontroler lub planszowy interfejs wejścia/wyjścia.

Pierwsza wersja ma wspierać:

- ustawienie postaci, potworów, NPC i obiektów na planszy,
- inicjatywę i tury,
- ruch po planszy,
- ataki melee/ranged,
- HP i obrażenia,
- proste efekty LED,
- interakcje z NPC i otoczeniem,
- zapis stanu gry lub walki.

Gracze mają zachować charakter gry planszowej:

- fizycznie rzucają kośćmi,
- wpisują wynik rzutu do aplikacji,
- przesuwają figurki po fizycznej planszy,
- reagują na podświetlenia LED i komunikaty aplikacji.

## Plansza I Hardware

Plansza:

- fizyczna siatka 20 kolumn x 30 rzędów,
- współrzędne zapisujemy jako `(col, row)`,
- jedno pole reprezentuje 5 feet, chyba że późniejsza decyzja projektowa ustali inaczej,
- Ruch po skosie: pierwsze pole diagonalne kosztuje 5 feet, kolejne 10 feets, potem znowu 5 feet i tak dalej zgodnie z regola 5-10-5
- niskopoziomowa komunikacja odbywa się przez istniejące `board.Connection`,
- logika gry nie może bezpośrednio importować `board`.

Wejście z planszy:

- skanowanie pól przez USB/serial z istniejącego pakietu `board`,
- alternatywnie backend symulatora z istniejącego pakietu `board`.

Wyjście na planszę:

- LED-y sterowane przez WLED przez istniejącą warstwę `board`,
- nowa aplikacja powinna używać adaptera w `src/dnd_board_game/hardware/`, a nie wywoływać hardware bezpośrednio z mechanik D&D.

LED-y służą do komunikacji między aplikacją a graczami:

- pokazują aktywną postać,
- pokazują możliwy ruch,
- pokazują wybraną ścieżkę,
- wskazują cele ataku,
- wskazują obszary działania efektów,
- sygnalizują trafienie, pudło, obrażenia, leczenie lub inne rezultaty,
- podświetlają interesujące miejsca, NPC, obiekty i punkty fabularne.

## Bazowy System Zasad

Bazujemy na Dungeons & Dragons 5e, ale zaczynamy od minimalnego, grywalnego podzbioru.

Na start implementujemy lub przygotowujemy miejsce na:

- ability scores i modyfikatory,
- proficiency bonus,
- AC,
- HP i temporary HP,
- speed,
- initiative,
- attack roll,
- damage roll,
- saving throw,
- ability check,
- advantage/disadvantage,
- podstawowe warunki jako placeholder.

Na tym etapie nie implementujemy pełnego systemu klas, wszystkich czarów, featów, pełnego bestiariusza ani pełnej listy warunków.

Jeśli zasada D&D 5e jest trudna do pogodzenia z fizyczną planszą albo spowalnia grę przy stole, wybieramy prostsze rozwiązanie i zapisujemy odstępstwo w `GAME_DESIGN.md`.

## Interakcje Społeczne I Eksploracja

Aplikacja nie ma obsługiwać tylko walki. Plansza powinna pomagać też w eksploracji i scenach społecznych:

- LED-y mogą wskazywać interesujące miejsca,
- NPC mogą mieć pozycje na planszy,
- obiekty interaktywne mogą otwierać dialogi lub wybory,
- interakcje z NPC i otoczeniem mogą przypominać okna dialogowe z klasycznych gier komputerowych,
- aplikacja może podpowiadać opcje, testy umiejętności i konsekwencje.

Pierwsza wersja nie musi mieć rozbudowanych dialogów, ale architektura powinna zostawić na nie miejsce.

## Pierwszy Grywalny Cel

Pierwsza grywalna wersja ma umożliwić rozegranie krótkiej sceny zawierającej prostą interakcję z NPC lub otoczeniem oraz prostą walkę.

Minimalny zakres:

- 2 bohaterów,
- 3 potwory,
- podstawowy algorytm zachowania potworów w walce,
- plansza z przeszkodami,
- tury według inicjatywy,
- ruch po planszy,
- atak melee/ranged,
- obrażenia i HP,
- zakończenie walki po pokonaniu jednej strony,
- przynajmniej jeden obiekt lub NPC możliwy do interakcji.

## Decyzje Techniczne

- Język: Python.
- Nowy kod aplikacji trafia do `src/dnd_board_game/`.
- Stary kod w `legacy/previous_app/` jest tylko referencją.
- Zaczynamy od czystego rdzenia domenowego i zasad, zanim odbudujemy UI.
- Nie kopiujemy mechanik Pathfindera z legacy, jeśli są sprzeczne z podejściem D&D 5e.
- Potwory, przedmioty i scenariusze docelowo powinny być data-driven.
- Obiekty gry powinny być możliwie proste i przechowywać stan.
- Mechaniki i interakcje między obiektami powinny być realizowane przez osobne funkcje lub klasy usługowe, np. `ApplyDamage`, `ResolveAttack`, `AttemptMeleeAttack`.
- Deterministyczna logika gry ma być testowalna bez Flask, WLED, seriala, realnej planszy i plików contentu.

## Czego Na Razie Nie Robimy

Na tym etapie nie robimy:

- pełnego kreatora postaci,
- pełnej bazy czarów,
- multiplayera,
- edytora kampanii,
- zaawansowanego AI przeciwników,
- importu gotowych statblocków,
- pełnego VTT,
- rozbudowanego systemu zapisu kampanii.

## Decyzje I Otwarte Pytania

- Aktualny runtime korzysta z lokalnego Flask/web UI połączonego z planszą albo symulatorem.
- Pierwszym scenariuszem referencyjnym jest `abandoned_watchtower` wraz z encounterem `gate_skirmish`.
- Ruch po skosie korzysta z przyjętej w projekcie reguły 5-10-5.
- Gracze domyślnie rzucają fizycznymi kośćmi i wpisują naturalne wyniki do aplikacji.
- Strategia licencji i źródła danych D&D 5e pozostaje do ustalenia przed budową docelowego katalogu.
- Snapshot pojedynczego scenariusza ma wersjonowany format v1 opisany w `docs/SAVE_FORMAT.md`;
  stan kampanii oraz migracje przyszłych wersji pozostają do zaprojektowania w M9.
- Bazową wersją zasad dla pierwszego pełnego wydania jest D&D 5e 2014. Odstępstwa wymagane przez fizyczną planszę albo tempo gry zapisujemy jawnie w `GAME_DESIGN.md` i `docs/RULES_DECISIONS.md`.

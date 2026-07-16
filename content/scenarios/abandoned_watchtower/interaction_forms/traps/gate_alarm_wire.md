# Goblińska linka alarmowa

## Umiejscowienie i widoczność

Pułapka znajduje się tuż za bramą i na początku jest ukryta. Publiczny opis sceny
nie zdradza jej istnienia. Gracze mogą jej szukać przez dokładne oglądanie przejścia,
podłoża, szczelin i mechanizmów alarmowych.

## Wykrycie

- Test: Wisdom (Perception), ST 13.
- Sukces ujawnia cienką linkę połączoną z metalowymi blaszkami.
- Porażka nie potwierdza, że przejście jest bezpieczne.

## Jawne działania po wykryciu

- Rozbrojenie: Dexterity z narzędziami złodziejskimi, ST 12.
- Ominięcie: Dexterity (Acrobatics), ST 10.
- Celowe uruchomienie: bez testu, następnie hazard.
- Porażka rozbrojenia albo ominięcia uruchamia hazard.

## Aktywacja

Jeżeli brama zostanie otwarta, zanim pułapkę rozbrojono albo bezpiecznie ominięto,
linka aktywuje się automatycznie. Bohater wykonuje Dexterity save ST 12. Sukces
zatrzymuje blaszki w ostatniej chwili. Porażka dodaje 3 punkty hałasu do bramy i
ustawia flagę `gate_alarm_triggered`, wpływając na otwarcie encounteru.

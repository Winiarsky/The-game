# Format Zapisu Gry

## Zakres v1

Snapshot sesji używa identyfikatora schematu `dnd_board_game.session` i pola
`schema_version: 1`. Zapis obejmuje mechaniczny stan potrzebny do deterministycznego
wznowienia scenariusza:

- pełny bieżący stan aktorów, przygotowanych czarów, slotów, ekwipunku i zasobów,
- pozycję drużyny, flagi, widoczność punktów, postęp wyzwań, czas i odpoczynki,
- aktywne efekty wraz ze źródłem, czasem trwania i regułą stackowania,
- oczekujący encounter oraz opcjonalny stan aktywnej walki,
- kolejność inicjatywy, rundę, bieżącą turę, ekonomię akcji i zużyte reakcje,
- stabilne wybory źródeł ataku/leczenia i stan nawigacji UI potrzebny do wznowienia.

Snapshot nie jest logiem sesji. Nie zawiera historii komunikatów, połączenia z
planszą, klienta LLM ani chwilowego formularza trwającego rzutu lub decyzji. Zapis
jest blokowany do czasu rozstrzygnięcia albo anulowania takiego kroku.

## Stabilne identyfikatory

Identyfikatory scenariusza, aktorów, lokacji, punktów, wyzwań, zasobów, triggerów,
efektów i źródeł akcji są częścią kontraktu zapisu. Zmiana takiego identyfikatora
jest zmianą schematu danych i wymaga migracji. Loader v1 sprawdza odwołania do
aktualnego contentu i odrzuca zapis, jeśli nie można go jednoznacznie odtworzyć.

## Wersjonowanie i migracje

- Runtime zapisuje wyłącznie bieżącą wersję.
- Loader odrzuca nieznany `schema` oraz nieobsługiwany `schema_version` z czytelnym
  błędem; nie próbuje zgadywać brakujących danych.
- Pierwsza zmiana formatu tworzy migrację `v1 -> v2` jako czystą transformację
  słownika JSON, test fixture starej wersji oraz deterministyczny test
  `load -> migrate -> save`.
- Migracje są wykonywane kolejno, bez pomijania wersji, przed budową modeli domeny.
- Migracja nie może uruchamiać odpoczynku, losowania, sprzętu, Flask ani LLM.

Snapshot v1 jest zapisem pojedynczego scenariusza. Stan drużyny pomiędzy
scenariuszami, kampania i migracje rzeczywistych starszych formatów należą do M9.
Sekcja eksploracji zapisuje również opcjonalne `temporary_items`: przedmioty
zbudowane z materiałów sceny, wraz z pozostałą liczbą użyć, źródłowymi materiałami
i lokacją utworzenia. Są odtwarzane wyłącznie w ramach tego samego scenariusza.
`conversation_entries` przechowuje uporządkowany transcript rozmów eksploracyjnych.
Każdy wpis ma stabilne `interaction_id`, rolę, tytuł i treść, dzięki czemu po
wczytaniu można odtworzyć osobny wątek konkretnego challenge'a, punktu albo NPC.

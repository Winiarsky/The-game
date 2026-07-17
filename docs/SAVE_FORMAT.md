# Format Zapisu Gry

## Zakres v1

Snapshot sesji używa identyfikatora schematu `dnd_board_game.session` i pola
`schema_version: 1`. Zapis obejmuje mechaniczny stan potrzebny do deterministycznego
wznowienia scenariusza:

- pełny bieżący stan aktorów, przygotowanych czarów, slotów, ekwipunku, zasobów oraz profilu biegłości w save'ach, skillach, broniach, pancerzach i narzędziach,
- pozycję drużyny, flagi, widoczność punktów, postęp wyzwań, czas i odpoczynki,
- aktywne efekty wraz ze źródłem, czasem trwania i regułą stackowania,
- oczekujący encounter oraz opcjonalny stan aktywnej walki,
- kolejność inicjatywy, rundę, bieżącą turę, ekonomię akcji, darmową interakcję z obiektem i zużyte reakcje,
- broń upuszczoną podczas aktywnej walki wraz z polem, właścicielem źródłowym i rundą,
- wynik Stealth oraz listę obserwatorów, przed którymi każdy aktor pozostaje ukryty,
- jawne stany warunków walki przypisane do aktorów wraz ze źródłem, czasem trwania
  i opcjonalnym rzutem kończącym warunek,
- jawne stany postaci powstałe w eksploracji, przenoszone do następnego encountera,
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
Oczekujący encounter zapisuje rozstrzygnięcie otwarcia starcia oraz ukończenie i
wyniki opcjonalnych prób Stealth przed inicjatywą. Każda próba przechowuje wynik i
relacje wykrycia per obserwator, dzięki czemu po rozpoczęciu walki można odtworzyć
ten sam `hidden_states` bez ponownego rzutu.

Sekcja eksploracji może zawierać `condition_states`. Stan wskazuje stabilne ID aktora
i warunek, np. `prone`. Brak pola w starszym snapshotcie v1 oznacza brak aktywnych
stanów eksploracyjnych. Przy rozpoczęciu encountera warunki znanych aktorów są
kopiowane do `CombatState`; po walce ich aktualny stan jest synchronizowany z eksploracją.
Stan może dodatkowo zawierać `source_label`, `duration`, `expiration_actor_id`,
`save_ability`, `save_dc` i `save_timing`. Aktor zapisuje także listę
`condition_immunities`. Brak tych pól zachowuje zgodne wartości domyślne v1.

`trap_states` zapisuje wyłącznie runtime'owy stan pułapek zdefiniowanych w aktualnym
contentcie: `hidden`, `revealed`, `disarmed`, `bypassed` albo `triggered`. Definicja
testów i hazardu pozostaje w scenariuszu. Loader odrzuca stan odwołujący się do
nieznanego ID pułapki, a brak pola w starszym snapshotcie v1 oznacza stan początkowy.

Instancje inventory oraz upuszczone bronie zapisują wymaganie dłoni
`hands_required`, listę zajętych slotów `held_in`, `light_weapon` i opcjonalne
`versatile_damage_dice`. Odczyt starszego snapshotu bez tych pól zachowuje zgodność:
broń bez jawnego wymagania jest normalizowana jako jednoręczna przy użyciu reguł
inventory.

Item może również zapisywać `armor_class_bonus` i `armor_proficiency`. Dzięki temu
stan założonej tarczy, zajęty slot dłoni i wynikające efektywne KP są odtwarzane bez
zapisywania pochodnej premii bezpośrednio w `Actor.ac`. Brak pól w starszym zapisie
oznacza odpowiednio premię `0` i brak wymagania biegłości.

Stan ekonomii bieżącej tury może zawierać `two_weapon_trigger_item_id`. Identyfikuje
lekką broń używaną w zwykłym ataku i pozwala po wczytaniu zachować legalność ataku
drugą bronią w tej samej turze. Starszy snapshot bez pola przyjmuje brak triggera.

Aktor zapisuje `attacks_per_action`, a stan tury pola `attack_action_active`,
`attacks_used` i `attacks_maximum`. Pozwala to wznowić turę dokładnie pomiędzy
atakami, również po częściowym Multiattack. Starszy snapshot bez tych pól przyjmuje
jeden atak na akcję oraz brak rozpoczętej Attack action.

Każdy aktor zapisuje `size` jako stabilną wartość `tiny`, `small`, `medium`, `large`,
`huge` albo `gargantuan`. Starszy snapshot bez pola jest odczytywany jako `medium`.
Rozmiar nie zmienia jeszcze liczby pól zajmowanych przez figurkę.

Profil `damage_affinities` zapisuje trzy listy stabilnych typów obrażeń:
`resistances`, `immunities` i `vulnerabilities`. Brak całego obiektu w starszym
snapshocie oznacza trzy puste listy i zwykłe przyjmowanie obrażeń.

Aktor może zapisywać listę `auras`. Każda aura zawiera stabilne `id`, etykietę,
promień, relację celów, typ efektu i wartość. Snapshot nie zapisuje listy objętych
aktorów: jest ona pochodną aktualnych pozycji, frakcji i stanu źródła. Brak pola
`auras` w starszym snapshotcie v1 oznacza pustą listę.

Aktor może zapisywać listę `triggers`. Każdy wpis zawiera stabilne `id`, etykietę,
`event_type`, `effect_kind` i wartość. Sam fakt jednorazowej aktywacji nie jest
osobnym stanem; jej wynik, np. bieżące temporary HP, znajduje się już w aktorze.
Brak pola `triggers` w starszym snapshotcie v1 oznacza pustą listę.

Każdy wpis `resource_pools` zapisuje bieżącą i maksymalną wartość oraz recovery.
Opcjonalny obiekt `recharge` zawiera `die_sides` i `minimum_roll`; brak tego pola
oznacza zasób bez recharge i zachowuje zgodność ze starszymi snapshotami v1.

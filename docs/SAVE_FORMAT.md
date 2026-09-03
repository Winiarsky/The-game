# Format Zapisu Gry

## Zapisane postacie

Własne postacie używają dokumentu oddzielnego od snapshotu scenariusza:

- schemat: `dnd_board_game.character`,
- aktualna wersja: `7`,
- ruleset: `dnd_5e_2014`.

Dokument przechowuje wybory źródłowe gracza: tożsamość, poziom, species, klasę,
background, archetyp klasy, bazowe ability scores, umiejętności klasowe, zestaw
wyposażenia, cantripy, czary znane lub zapisane w spellbooku, osobny zestaw
przygotowanych czarów i portret. Wczytanie ponownie waliduje te wybory względem wersjonowanego
katalogu i deterministycznie buduje wspólny model `Actor`. Pochodne HP, KP,
biegłość, metadane ekwipunku, sloty i spell DC nie są przyjmowane z pliku jako
źródło prawdy.

Pliki rosteru znajdują się domyślnie w `data/characters/` pod nazwą
`<character_id>.character.json`. Zapis jest atomowy, istniejący identyfikator nie
jest nadpisywany podczas tworzenia postaci, a nazwa pliku musi odpowiadać id
wewnątrz dokumentu. Odczyt rosteru izoluje uszkodzony lub niekompatybilny plik,
zamiast blokować pozostałe postacie. Operacja usunięcia przenosi dokument do
`data/characters/.trash/`, dzięki czemu lokalny zapis można ręcznie odzyskać.

Wersja v3 dodała `experience_points`. Wersja v4 zapisuje elastyczne wybory
premii cech species (`selected_species_bonus_ability_ids`). Wersja v5 dodaje
wybory umiejętności, narzędzi, języków, wariantu i cantripu species, a v6
zapisuje ogólne opcje klasowe (`selected_class_option_ids`). Wersja v7 dodaje
wybrane narzędzia i języki backgroundu. Migracje uzupełniają starsze dokumenty
deterministycznymi, kompatybilnymi wyborami.

## Zakres v33

Snapshot sesji używa identyfikatora schematu `dnd_board_game.session` i pola
`schema_version: 33`. Zapis obejmuje mechaniczny stan potrzebny do deterministycznego
wznowienia scenariusza:

- kontrakt contentu: schemat scenariusza, jego wersję, ruleset i wymagane source packi,
- pełny bieżący stan aktorów, exhaustion, przygotowanych czarów, zwykłych i
  tymczasowych slotów, ekwipunku, zasobów oraz profilu biegłości w save'ach,
  skillach, broniach, pancerzach i narzędziach,
- pozycję drużyny, flagi, widoczność punktów, postęp wyzwań, czas i odpoczynki,
- aktywne czasowe efekty magii eksploracyjnej wraz z czarem, aktorem, flagą,
  minutą rozpoczęcia i opcjonalną minutą wygaśnięcia,
- aktywne efekty wraz ze źródłem, poziomem źródłowego czaru, czasem trwania,
  regułą stackowania oraz opcjonalnym promieniem aury, kością premii,
  modyfikatorem, limitem użyć i licznikiem pozostałych rund,
- oczekujący encounter oraz opcjonalny stan aktywnej walki,
- kolejność inicjatywy, rundę, bieżącą turę, ekonomię akcji, darmową interakcję
  z obiektem, dostępność darmowej zmiany broni i zużyte reakcje,
- ograniczenie czaru rzucanego akcją bonusową oraz informację o poziomowym
  czarze rzuconym akcją w bieżącej turze,
- rozdzielenie zwykłego darkvision od widzenia w magicznej ciemności
  zapewnianego przez Devil's Sight,
- postęp długotrwałych czarów: rzucającego, czar, poziom slotu, wymagane i wykonane
  akcje oraz rundę ostatniego postępu,
- przywołane istoty wraz z właścicielem, czarem, efektem koncentracji i pełną
  definicją statystyk/ataku potrzebną do wznowienia dynamicznego aktora,
- broń upuszczoną podczas aktywnej walki wraz z polem, właścicielem źródłowym i rundą,
- rejestr wystrzelonej amunicji oraz pozostałe stosy łupu pola walki,
- trwałą wspólną pulę łupu drużyny, do której automatycznie trafiają przenośne
  przedmioty i monety pokonanych przeciwników po zwycięskiej walce,
- bieżący towar, portfel i procent odkupu każdego kupca,
- wynik Stealth oraz listę obserwatorów, przed którymi każdy aktor pozostaje ukryty,
- jawne stany warunków walki przypisane do aktorów wraz ze źródłem, czasem trwania
  i opcjonalnym rzutem kończącym warunek,
- jawne stany postaci powstałe w eksploracji, przenoszone do następnego encountera,
- trwałe stany fixture'ów eksploracji: otwarcie, zamek, opróżnienie pojemnika,
  aktualne HP, zniszczenie oraz ujawnione elementy,
- stabilne wybory źródeł ataku/leczenia i stan nawigacji UI potrzebny do wznowienia.

Snapshot nie jest logiem sesji. Nie zawiera historii komunikatów, połączenia z
planszą, klienta LLM ani chwilowego formularza trwającego rzutu lub decyzji. Zapis
jest blokowany do czasu rozstrzygnięcia albo anulowania takiego kroku.

## Stabilne identyfikatory

Identyfikatory scenariusza, aktorów, lokacji, punktów, wyzwań, zasobów, triggerów,
efektów i źródeł akcji są częścią kontraktu zapisu. Zmiana takiego identyfikatora
jest zmianą schematu danych i wymaga migracji. Loader sprawdza odwołania do
aktualnego contentu i odrzuca zapis, jeśli nie można go jednoznacznie odtworzyć.

## Wersjonowanie i migracje

- Runtime zapisuje wyłącznie bieżącą wersję.
- Loader odrzuca nieznany `schema`, przyszły `schema_version` i brak kroku
  migracji z czytelnym błędem; nie próbuje zgadywać brakującego stanu.
- Migracja `v1 -> v2` jest czystą transformacją słownika JSON. Dodaje kontrakt
  contentu `dnd_board_game.scenario` v1, ruleset `dnd_5e_2014` oraz historyczny
  pack `project_original`; nie zmienia stanu mechanicznego.
- Migracja `v2 -> v3` dodaje aktorom pusty portfel, a instancjom inventory
  domyślną wartość `0 cp` i masę `0 lb`.
- Migracja `v3 -> v4` dodaje instancjom inventory opcjonalne `ammunition_type`.
- Migracja `v4 -> v5` dodaje walce pusty rejestr wystrzelonej amunicji i pustą
  listę trwałych pakietów łupu pola walki.
- Migracja `v5 -> v6` zachowuje brak stanu kupców; podczas odczytu ich stan
  początkowy jest wtedy pobierany z aktualnego, zweryfikowanego contentu scenariusza.
- Migracja `v6 -> v7` zachowuje brak opcjonalnych pól pancerza. Dotychczasowe
  przedmioty zachowują wcześniejsze zachowanie, dopóki content nie nada im kategorii
  i formuły pancerza.
- Migracja `v7 -> v8` zachowuje brak opcjonalnych pól ładunków. Dotychczasowe
  przedmioty pozostają zwykłymi consumable albo wyposażeniem bez puli ładunków.
- Migracja `v8 -> v9` dodaje zgodne wartości domyślne attunement. Dotychczasowe
  przedmioty nie wymagają dostrojenia i zachowują wcześniejszą dostępność mocy.
- Migracja `v9 -> v10` dodaje pustą listę `magic_effects`. Dotychczasowe
  przedmioty zachowują wcześniejsze zachowanie.
- Migracja `v10 -> v11` dodaje puste `weapon_category` i `weapon_properties`.
  Starsze instancje zachowują kompatybilne, jawnie zapisane pola wyposażenia.
- Migracja `v11 -> v12` zachowuje brak opcjonalnych pól mundane gear. Starsze
  przedmioty pozostają zwykłymi instancjami bez kategorii, pojemności, światła,
  reguł użytkowych, durability i zawartości pakietu. Aktor bez `active_light`
  zaczyna bez zapalonego źródła światła.
- Migracja `v12 -> v13` zachowuje brak opcjonalnych definicji czarów i profili
  dostępu. Nowe zapisy utrwalają pełne `SpellDefinition` oraz profile
  prepared/known/spellbook aktora.
- Migracja `v13 -> v14` zachowuje brak opcjonalnych reguł skalowania i efektów
  eksploracyjnych czarów. Nowe zapisy utrwalają dane upcastingu oraz rytuałów.
- Migracja `v14 -> v15` zachowuje brak czasowych efektów magii eksploracyjnej.
  Nowe zapisy utrwalają ich źródło, flagę oraz minutowy lifecycle.
- Migracja `v15 -> v16` dodaje aktywnej walce pustą listę `long_casts`. Nowe
  zapisy utrwalają postęp długotrwałego castingu.
- Migracja `v16 -> v17` dodaje aktywnej walce pustą listę `summoned_creatures`.
  Nowe zapisy utrwalają dynamicznych aktorów i ich relację z koncentracją.
- Migracja `v17 -> v18` dodaje aktywnym efektom opcjonalny poziom źródłowego
  czaru, a stanom opcjonalne ID i poziom czaru. Brak tych danych zachowuje efekt,
  ale nie pozwala traktować go jako bezpiecznie rozpraszalnej magii.
- Migracja `v18 -> v19` dodaje aktorom jawny poziom `level`, domyślnie `1`.
- Migracja `v19 -> v20` dodaje aktorom typowany profil `senses` z zerowymi
  zasięgami darkvision, blindsight, tremorsense i truesight.
- Migracja `v20 -> v21` dodaje eksploracji pustą listę `hidden_actor_states`.
  Nowe wpisy przechowują aktora, strefę, naturalny wynik i końcowy wynik Stealth.
- Migracja `v21 -> v22` uzupełnia istniejące stany fixture'ów o pola
  `opened`, `locked`, `looted` i `current_hit_points`.
- Migracja `v22 -> v23` dodaje wszystkim aktorom eksploracji i walki
  `exhaustion_level: 0`.
- Migracja `v23 -> v24` dodaje wszystkim aktorom eksploracji i walki
  `experience_points: 0`.
- Migracja `v24 -> v25` zachowuje starsze profile dostępu do czarów; nowe
  profile zapisują opcjonalną `casting_ability`, aby ten sam czar mógł używać
  innej cechy zależnie od klasy albo species.
- Migracja `v25 -> v26` zachowuje dla starszych slotów regenerację po długim
  odpoczynku. Nowe sloty zapisują `recovery`, dzięki czemu Pact Magic może
  poprawnie odzyskiwać sloty po krótkim odpoczynku.
- Migracja `v26 -> v27` nadaje starszym aktorom domyślny typ `humanoid`.
- Migracja `v27 -> v28` dodaje opcjonalne mapowanie wrodzonych czarów na ich
  zasoby odnawiane podczas odpoczynku.
- Migracja `v31 -> v32` zachowuje starsze efekty z bezpiecznymi wartościami
  domyślnymi pól aur; nowe efekty zapisują geometrię, licznik rund i limity
  aktywacji.
- Migracja `v32 -> v33` dodaje pustą wspólną pulę łupu drużyny. Brak pola
  `weapon_change_available` w stanie tury oznacza, że darmowa zmiana broni jest
  jeszcze dostępna.
  Nowe zapisy utrwalają `creature_type`, potrzebny m.in. Turn Undead,
  Favored Enemy i pełnemu efektowi Chill Touch.
- Migracje są wykonywane kolejno, bez pomijania wersji, przed budową modeli domeny.
- Migracja nie może uruchamiać odpoczynku, losowania, sprzętu, Flask ani LLM.

Snapshot v33 jest zapisem pojedynczego scenariusza. Stan drużyny pomiędzy
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
`save_ability`, `save_dc`, `save_timing`, `source_spell_id` i
`source_spell_level`. Aktor zapisuje także listę
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

Snapshot v28 zapisuje portfel aktora w nominałach `cp`, `sp`, `ep`, `gp`, `pp`
oraz jednostkową `value_cp` i `weight_lb` każdej instancji inventory. Całkowita
wartość, masa monet (50 monet = 1 lb), masa ekwipunku i udźwig są wartościami
pochodnymi i nie są osobnym autorytatywnym stanem.

Sekcja eksploracji zapisuje pełny runtime'owy stan kupców: stabilne ID, nazwę,
`buyback_percent`, portfel oraz pozostałe stosy inventory. Loader wymaga dokładnie
tego samego zbioru ID kupców co aktualny content scenariusza. Starszy snapshot bez
tego pola inicjalizuje kupców z contentu; późniejsze zapisy zachowują już wszystkie
wykonane zakupy i sprzedaże.

Instancja amunicji zapisuje stabilne `ammunition_type`, np. `bolt`, oraz zwykłe
`quantity`. Wymagany typ i właściwość `loading` pozostają częścią wersjonowanej
definicji źródła ataku; snapshot przechowuje zużyty, pozostały stan stosów.
Aktywna walka zapisuje również wpisy `ammunition_expenditures` z aktorem, frakcją,
typem, liczbą i prototypem zużytego stosu. `battlefield_loot` przechowuje pozycję
oraz pozostałą zawartość odzyskanego pakietu, więc zapis w trakcie walki i po
częściowym zebraniu łupu nie duplikuje ani nie gubi pocisków.

Item może również zapisywać `armor_class_bonus` i `armor_proficiency`. Dzięki temu
stan założonej tarczy, zajęty slot dłoni i wynikające efektywne KP są odtwarzane bez
zapisywania pochodnej premii bezpośrednio w `Actor.ac`. Brak pól w starszym zapisie
oznacza odpowiednio premię `0` i brak wymagania biegłości.

Pancerz korpusu zapisuje również `armor_category`, `armor_base_ac`,
`armor_dexterity_cap`, opcjonalne `armor_strength_requirement` oraz
`stealth_disadvantage`. Stan `equipped` wskazuje jedyny założony pancerz. Efektywne
KP i szybkość pozostają wartościami pochodnymi i nie są zapisywane osobno.

Przedmiot z pulą ładunków zapisuje `charges_maximum`, bieżące
`charges_current`, moment `charges_recovery` oraz opcjonalne
`charges_recovery_dice` i `charges_recovery_modifier`. Snapshot zachowuje wyłącznie
stan puli; koszt konkretnej akcji pozostaje w wersjonowanym contentcie. Odtworzenie
nie wykonuje rzutu ani odpoczynku.

Instancja zapisuje także `requires_attunement` i bieżące `attuned`. Dzięki temu
zapis w eksploracji albo walce zachowuje dostępność mocy bez ponownego short resta.
Limit trzech więzi jest walidowany przy nowym dostrajaniu, a nie wyliczany jako
osobne pole snapshotu.

Lista `magic_effects` jest zapisywana razem z instancją, aby aktywna walka mogła
odtworzyć dokładne, wersjonowane prymitywy przedmiotu. Efektywne KP, szybkość i
sumy modyfikatorów nadal są wyliczane, nie serializowane.

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

Aktywny efekt obszarowy może zapisywać `excluded_positions`: pola wycięte z
obszaru przez Rzeźbienie pola Nimry. Brak listy oznacza zwykły, pełny obszar;
zapisane wycięcia pozostają nieaktywne przez cały czas życia strefy.

Aktor może zapisywać listę `features`. Snapshot przechowuje grant cechy: stabilne
`feature_id`, etykietę, opis, `source_kind`, `source_ref` oraz identyfikatory
przyznanych zasobów, akcji, triggerów i aur. Definicje mechaniki pozostają w
wersjonowanym contentcie; snapshot zapisuje ich pochodzenie i aktualny stan
przyznanych prymitywów. Brak pola `features` oznacza pustą listę.

Eksploracja zapisuje `npc_states` dla każdego NPC znanego aktualnej wersji
scenariusza. Wpis zawiera `npc_id`, nastawienie, stan fizyczny i emocjonalny,
ujawnione informacje, wykorzystane próby oraz uporządkowaną historię ważnych
zdarzeń relacji. Brak pola w starszym snapshotcie v1 odtwarza stan początkowy z
contentu. Nieznane NPC albo identyfikatory informacji powodują odrzucenie zapisu.
Pole `used_feature_ids` przechowuje jednorazowe zdolności zużyte wobec tego NPC,
np. `lorian:improvisation`; brak pola w starszym zapisie oznacza pustą listę.
Zdarzenie powstałe po rzucie może zawierać `attempt_id`, używany do liczenia
contentowych limitów prób. Starsze zdarzenie bez tego pola korzysta z
`used_attempt_ids` jako zgodnego wstecznie potwierdzenia co najmniej jednej próby.
Stan NPC zapisuje też `interaction_status` i `closure_reason`, dzięki czemu ponowne
wejście do zamkniętej rozmowy nie wywołuje LLM. Opcjonalne
`pending_npc_transition` przechowuje stabilne identyfikatory przejścia, wariantu i
NPC; po wczytaniu wariant jest odtwarzany z aktualnego contentu, a nie kopiowany
do snapshotu.

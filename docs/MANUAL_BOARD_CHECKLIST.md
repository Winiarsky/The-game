# Manualna Checklista Planszy

Ten dokument opisuje ręczne testy na symulatorze albo fizycznej planszy.

Każdy punkt powinien mieć wynik:

- `PASS`
- `FAIL`
- `BLOCKED`
- `NOT TESTED`

## Przygotowanie

- [ ] Plansza ma zasilanie.
- [ ] Kontroler LED odpowiada.
- [ ] Skanowanie pól działa.
- [ ] `board.Connection` uruchamia się bez błędów.
- [ ] Jeśli używany jest symulator, strona symulatora działa.
- [ ] Testowy scenariusz ma znane pozycje aktorów i przeszkód.

## Test Mapowania LED

- [ ] Pole `(0, 0)` zapala oczekiwany LED.
- [ ] Pole `(0, 29)` zapala oczekiwany LED.
- [ ] Pole `(1, 29)` zapala oczekiwany LED.
- [ ] Pole `(1, 0)` zapala oczekiwany LED.
- [ ] Kilka pól w środku planszy zapala poprawne fizyczne pozycje.
- [ ] `leds_off()` gasi wszystkie testowane LED-y.

## Test Skanowania Pola

- [ ] Kliknięcie/wciśnięcie jednego pola zwraca poprawne `(col, row)`.
- [ ] Kilka pól w rogach zwraca poprawne koordynaty.
- [ ] Kilka pól w środku zwraca poprawne koordynaty.
- [ ] Anulowanie skanu działa.
- [ ] Ponowne uzbrojenie skanu działa po anulowaniu.

## Test Ruchu

Stan testowy:

- aktywny aktor na znanym polu,
- speed `30 feet`,
- kilka przeszkód,
- przynajmniej jedno pole trudnego terenu.

Checklist:

- [ ] Plansza pokazuje aktywnego aktora.
- [ ] LED-y pokazują pełny zasięg ruchu.
- [ ] Zasięg ortogonalny odpowiada 6 polom normalnego terenu.
- [ ] Ruch diagonalny kosztuje naprzemiennie 5/10/5/10 feet.
- [ ] Trudny teren kosztuje 10 feet.
- [ ] Ściany blokują przejście.
- [ ] Blokujące przeszkody blokują wejście na pole.
- [ ] Nie da się zakończyć ruchu na zajętym polu.
- [ ] Po wyborze celu LED-y pokazują wybraną ścieżkę.
- [ ] Po zatwierdzeniu ruchu aktor ma nową pozycję.

### Runtime `demo_movement`

Test bez planszy:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_movement --board-backend none --destination 3,3 --session-id manual_demo
```

- [ ] Terminal pokazuje origin, destination, reachable count, path i cost.
- [ ] Powstaje `data/session_observations/manual_demo.jsonl`.
- [ ] Plik zawiera `movement_path_selected` i `session_finished`.

Test celu zablokowanego:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_movement --board-backend none --destination 1,0 --session-id blocked_demo
```

- [ ] Terminal pokazuje `path_valid: False`.
- [ ] Plik obserwacji zawiera `movement_rejected`.
- [ ] Program kończy się bez stack trace.

Test w symulatorze:

```bash
python -m board.simulator.app
```

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_movement --board-backend simulator --board-url http://127.0.0.1:5000 --destination 3,3 --show-leds --session-id simulator_demo
```

- [ ] Aktywny aktor jest oznaczony LED.
- [ ] Zasięg ruchu jest widoczny.
- [ ] Trudny teren jest oznaczony pomarańczowo.
- [ ] Blokujące pole jest oznaczone czerwono.
- [ ] Przeciwnik jest oznaczony różowo.
- [ ] Sojusznik jest oznaczony cyan.
- [ ] Wybrana ścieżka jest pokazana LED.
- [ ] Cel jest wyróżniony.
- [ ] Plik obserwacji zawiera `led_feedback_sent`.

## Test Ataku

Stan testowy:

- aktywny aktor ma cel w zasięgu ataku,
- cel ma znane AC i HP.

Checklist:

- [ ] LED-y pokazują legalne cele ataku.
- [ ] Aplikacja prosi o naturalny wynik `d20`.
- [ ] Aplikacja dolicza modyfikator ataku.
- [ ] Trafienie/pudło jest rozstrzygnięte poprawnie.
- [ ] Naturalne `20` daje krytyczne trafienie.
- [ ] Naturalne `1` daje automatyczne pudło.
- [ ] Przy trafieniu aplikacja prosi o wynik obrażeń.
- [ ] HP celu zmienia się poprawnie.
- [ ] LED-y pokazują wynik ataku.

### Runtime `demo_mini_combat`

Terminal 1:

```bash
python -m board.simulator.app
```

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --hero-attack-roll 14 --hero-damage 6 --hero-damage-type slashing --session-id mini_combat_simulator_demo
```

- [ ] Aplikacja mówi, że aktywny aktor wybiera `Atak`.
- [ ] Symulator jest w trybie `Plansza`, nie `Przesuwanie figurek`.
- [ ] Legalne cele świecą na niebiesko.
- [ ] Podczas komunikatu wyboru celu legalne cele nadal świecą na niebiesko.
- [ ] Można kliknąć legalne pole celu w symulatorze zanim LED-y zgasną.
- [ ] Kliknięcie nielegalnego pola nie zawiesza flow i przechodzi do fallbacku.
- [ ] Jeśli skan celu nie zadziała, runtime używa fallbacku `--target-id`.
- [ ] Po wyborze świeci tylko wybrany cel.
- [ ] Komunikat pokazuje źródło ataku i aktywne modyfikatory.
- [ ] Trafienie świeci zielono.
- [ ] Pudło świeci czerwono.
- [ ] Trafienie krytyczne świeci żółto.
- [ ] Po potwierdzeniu LED gaśnie.
- [ ] Przy trafieniu HP celu spada.
- [ ] Plik obserwacji zawiera `attack_declared`, `attack_resolved` i `damage_applied`.

### Runtime `demo_mini_combat_loop`

Terminal 1:

```bash
python -m board.simulator.app
```

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/goblin_ambush.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --scan-timeout 30 --hero-attack-roll 14 --hero-damage 6 --hero-damage-type slashing --enemy-seed 7 --max-rounds 3 --session-id mini_combat_loop_simulator_demo
```

- [ ] Na początku każdej tury świeci aktywny aktor.
- [ ] Terminal pokazuje nazwę scenariusza z pliku contentu.
- [ ] Po potwierdzeniu aktywnego aktora LED gaśnie albo przechodzi do następnego kroku.
- [ ] Bohater widzi legalne cele ataku na niebiesko.
- [ ] Po wyborze świeci tylko wybrany cel.
- [ ] Wynik ataku bohatera świeci odpowiednim kolorem.
- [ ] Goblin wykonuje auto-atak bez wpisywania rzutu przez gracza.
- [ ] Podczas auto-ataku goblina LED-y pokazują jego cel i wynik.
- [ ] HP aktorów zmienia się w terminalu po trafieniach.
- [ ] Walka kończy się po pokonaniu jednej strony albo zatrzymuje po `--max-rounds`.
- [ ] Plik obserwacji zawiera `turn_started`, `action_used`, `turn_finished`, `enemy_action_selected` i `combat_finished` albo `combat_stopped`.

### Runtime `demo_mini_combat_loop` Multi-Actor

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/multi_actor_skirmish.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --scan-timeout 30 --enemy-seed 7 --max-rounds 5 --session-id multi_actor_simulator_demo
```

- [ ] Terminal pokazuje scenariusz `Potyczka przy rozbitych skrzyniach`.
- [ ] Tury przechodzą przez 2 bohaterów i 3 przeciwników.
- [ ] Przy wyborze celu świecą wszystkie legalne cele aktualnego bohatera.
- [ ] Kliknięcie legalnego celu wybiera właściwego przeciwnika.
- [ ] Wynik ataku świeci tylko na wybranym celu.
- [ ] Pokonani aktorzy nie wykonują kolejnych tur.
- [ ] Walka kończy się dopiero po pokonaniu całej strony.
- [ ] Plik obserwacji zawiera `target_selected`.

### Runtime `demo_mini_combat_loop` Board-First Turn

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/movement_skirmish.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --scan-timeout 30 --enemy-seed 7 --max-rounds 5 --session-id board_first_turn_simulator_demo
```

- [ ] Na starcie tury aktywny bohater świeci na biało.
- [ ] Legalne pola ruchu świecą przygaszonym niebieskim/cyan.
- [ ] Legalne cele ataku świecą mocnym niebieskim.
- [ ] Pierwsze kliknięcie pustego legalnego pola pokazuje ścieżkę ruchu na żółto i komunikat z kosztem.
- [ ] Drugie kliknięcie tego samego pola potwierdza ruch i aktualizuje pozycję aktora.
- [ ] Pierwsze kliknięcie legalnego celu pokazuje warunki ataku i prosi o ponowne kliknięcie.
- [ ] Drugie kliknięcie tego samego celu potwierdza atak.
- [ ] Kliknięcie innego legalnego pola przed potwierdzeniem zmienia podgląd bez wykonywania poprzedniej intencji.
- [ ] Kliknięcie pola aktywnego aktora pokazuje opcję zakończenia tury.
- [ ] Drugie kliknięcie pola aktywnego aktora kończy turę przed wykorzystaniem całego ruchu.
- [ ] Po ataku można jeszcze ruszyć się pozostałym ruchem.
- [ ] Przeciwnik bez celu ataku podchodzi do najbliższej pozycji ataku.
- [ ] Ruch przeciwnika pokazuje ścieżkę na czerwono i docelowe pole na pomarańczowo.
- [ ] Po fizycznym przestawieniu figurki przeciwnika kliknięcie pomarańczowego pola potwierdza ruch.
- [ ] Plik obserwacji zawiera `turn_intent_previewed`, `turn_intent_confirmed`, `movement_committed`, `attack_previewed` i `target_selected`.

### Runtime `demo_mini_combat_loop` Pierwsza Grywalna Scena

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop --scenario content/scenarios/first_playable_scene.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --wait-for-enter --scan-timeout 30 --initiative-mode rolled --enemy-seed 7 --max-rounds 8 --session-id first_scene_simulator_demo
```

- [ ] Przed startem sceny aplikacja pokazuje komunikat setupu.
- [ ] Pola startowe bohaterów świecą na biało/cyan.
- [ ] Każdy bohater jest wywołany osobno do ustawienia figurki.
- [ ] Kliknięcie jednego z podświetlonych pól startowych potwierdza ustawienie danego bohatera.
- [ ] Jawni przeciwnicy i elementy sceny są ustawiane krokami, maksymalnie po 5 pól naraz.
- [ ] Kliknięcie jednego z pól aktualnej grupy potwierdza ustawienie tej grupy.
- [ ] Po setupie aplikacja komunikuje rozpoczęcie inicjatywy.
- [ ] Każdy bohater jest wywołany osobno do rzutu inicjatywy.
- [ ] Przy rzucie inicjatywy świeci pole aktualnie wywołanego aktora.
- [ ] Przeciwnicy mają inicjatywę rzuconą automatycznie i też są chwilowo podświetlani.
- [ ] Aplikacja pokazuje finalną kolejność inicjatywy przed pierwszą turą.
- [ ] Jeśli przeciwnik rusza się w swojej turze, ścieżka świeci na czerwono, docelowe pole na pomarańczowo, a ruch wymaga kliknięcia pola docelowego.
- [ ] Aplikacja pokazuje cel sceny.
- [ ] Widoczni przeciwnicy poza zasięgiem świecą przygaszonym czerwonym/różowym, a nie wyglądają jak puste pola.
- [ ] Obiekt interaktywny świeci na zielono.
- [ ] Kliknięcie obiektu pokazuje opcję interakcji i opis.
- [ ] Drugie kliknięcie tego samego obiektu potwierdza interakcję.
- [ ] Aplikacja pokazuje warunki testu cechy: cecha/skill, ST, aktywne modyfikatory i końcowy modyfikator.
- [ ] Po wpisaniu naturalnego wyniku d20 aplikacja pokazuje sukces albo porażkę.
- [ ] Sukces miga/świeci na zielono, porażka na czerwono.
- [ ] Po spełnieniu celu aplikacja kończy scenę.
- [ ] Plik obserwacji zawiera `scene_setup_started`, `scene_setup_step_confirmed`, `scene_setup_confirmed`, `roll_requested`, `roll_resolved`, `enemy_initiative_rolled`, `initiative_set`, `board_scan_requested`, `board_scan_received`, `objective_started`, `interaction_options_shown`, `ability_check_requested`, `ability_check_resolved`, `scene_flag_set`, `objective_completed` i `scene_finished`.

## Test Obserwacji Sesji

- [ ] Każdy ruch zapisuje metadane: aktor, start, cel, koszt, ścieżka.
- [ ] Każdy rzut zapisuje metadane: typ, naturalny wynik, modyfikator, wynik końcowy.
- [ ] Każdy atak zapisuje metadane: atakujący, cel, wynik, obrażenia.
- [ ] Każda tura zapisuje metadane: aktywny aktor, numer rundy, zużycie akcji i koniec tury.
- [ ] Każdy błąd zapisuje krótki opis i aktualny stan.
- [ ] Plik obserwacji można otworzyć i odczytać bez aplikacji.

## Test Setupu I Inicjatywy

Terminal 1:

```bash
python -m board.simulator.app
```

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_initiative_setup --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --session-id initiative_simulator_demo
```

Checklist:

- [ ] Jeśli LED-y są zbyt szybkie, uruchom demo z `--wait-for-enter`.
- [ ] Komunikat startu walki pojawia się przed setupem.
- [ ] LED-y setupu odpowiadają aktualnemu komunikatowi.
- [ ] Jawni bohaterowie są podświetleni podczas kroku ustawiania bohaterów.
- [ ] Jawni przeciwnicy są podświetleni podczas kroku ustawiania przeciwników.
- [ ] Jawne elementy otoczenia są podświetlane partiami zgodnymi z komunikatem.
- [ ] Po zakończeniu każdego kroku poprzednie LED-y gasną.
- [ ] Przy rzucie inicjatywy świeci tylko aktualnie wywołany aktor.
- [ ] Po wpisaniu wyniku albo auto-rollu pole aktora gaśnie.
- [ ] Ukryte i warunkowe elementy nie są zdradzane graczom.
- [ ] Po ustaleniu kolejności świeci aktywny aktor pierwszej tury.
- [ ] `data/session_observations/initiative_simulator_demo.jsonl` zawiera `setup_step_started`, `roll_requested`, `enemy_initiative_rolled`, `initiative_set` i `turn_started`.

## Test Eksploracji

Terminal 1:

```bash
python -m board.simulator.app
```

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_exploration_scene --scenario content/scenarios/abandoned_watchtower.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --scan-timeout 30 --session-id abandoned_watchtower_simulator_demo
```

Checklist:

- [ ] Aplikacja prosi o położenie mapki eksploracji na planszy.
- [ ] LED-y pokazują dostępne lokacje przez ich punkty główne, bez świecenia całych stref i bez dodatkowego potwierdzania setupu stref.
- [ ] Jawne elementy fizyczne oznaczone `requires_setup` są rozstawiane osobno i potwierdzane kliknięciem.
- [ ] Ukryta skrytka nie świeci podczas setupu.
- [ ] Domyślny widok eksploracji pokazuje tylko główne punkty dostępnych lokacji.
- [ ] Kliknięcie innej strefy pokazuje pytanie o przejście.
- [ ] Drugie kliknięcie tej samej strefy potwierdza przejście.
- [ ] Kliknięcie aktualnego punktu głównego pokazuje opis aktywnego wyzwania.
- [ ] Aplikacja prosi drużynę o wolną deklarację działania.
- [ ] LLM proponuje interpretację mechaniczną, a gracz akceptuje ją `+` albo odrzuca `-`.
- [ ] Przed rzutem aplikacja pokazuje test, ST, aktywne bonusy i konsekwencje.
- [ ] Po rozstrzygnięciu wyzwanie aktualizuje progress, hałas, komplikacje i odblokowane lokacje.
- [ ] JSONL zawiera `exploration_started`, `exploration_setup_confirmed`, `challenge_freeform_prompted`, `gm_classifier_option_proposed`, `gm_classifier_option_resolved` i `challenge_progress_updated`.

### Runtime `demo_exploration_scene` Mini-Scena Wioski

Terminal 2:

```bash
PYTHONPATH=src python -m dnd_board_game.runtime.demo_exploration_scene --scenario content/scenarios/village_square_mvp.json --board-backend simulator --board-url http://127.0.0.1:5000 --show-leds --scan-timeout 30 --session-id village_square_demo
```

- [ ] Terminal pokazuje scenariusz `Wioska pod strażnicą`.
- [ ] Dostępne lokacje są wypisane z nazwami i kolorami.
- [ ] Setup jawnych elementów prowadzi przez fizyczne punkty: sołtys, tablica ogłoszeń i karczmarz.
- [ ] Ukryta sakiewka nie świeci podczas setupu.
- [ ] Kliknięcie głównego punktu `Rynek` pokazuje menu opcji wokół lokacji.
- [ ] Opcje mają czytelne nazwy kolorów, bez wartości RGB.
- [ ] Główny widok rynku pokazuje `Sprawdź tablicę ogłoszeń` i `Popytaj mieszkańców`; pierwsza opcja rozstrzyga się bez rzutu, a druga prosi o postać i fizyczny d20.
- [ ] Cel `Przygotujcie wyprawę do strażnicy` pokazuje trzy kamienie milowe i zaznacza je kolejno po zdobyciu tropu, przyjęciu zadania i potwierdzeniu gotowości.
- [ ] Rozmowa z Brenem najpierw ujawnia problem, potem pozwala przyjąć zadanie, a na końcu potwierdzić gotowość.
- [ ] Ponowne otwarcie rozmowy z Brenem nie dodaje drugi raz jego tekstu powitalnego.
- [ ] Samo zdobycie tropu nie kończy objective; kończy je dopiero `ready_for_watchtower`.
- [ ] Przycisk wyjścia pozostaje zablokowany poza `Droga do lasu`.
- [ ] W `Droga do lasu` karta wyjścia otwiera formularz tempa, nawigatora i fizycznego rzutu Survival.
- [ ] Po rozstrzygnięciu wyjście pokazuje nazwę `Opuszczona strażnica`, bez surowego `abandoned_watchtower` i bez absolutnej ścieżki snapshotu.
- [ ] UI pokazuje bieżącą porę dnia i dolicza czas rozmów oraz przejść między lokacjami.
- [ ] Szybkie wyjście nie ustawia flag zwłoki; po short reście w karczmie dalsza podróż pokazuje narrację zmierzchu i alarmu goblinów.
- [ ] Handoff zawiera `departure_minute`, `arrival_minute`, `travel_minutes`, `arrival_clock` i uruchomione eventy zegara.
- [ ] JSONL zawiera `ui_scenario_time_advanced`, `ui_scenario_clock_event_triggered`, `ui_scenario_completed` oraz `ui_scenario_continuation_ready`.

### Runtime `demo_exploration_scene` LLM GM Classifier

Terminal 2:

```bash
source .env
PYTHONPATH=src python -m dnd_board_game.runtime.demo_exploration_scene --scenario content/scenarios/abandoned_watchtower.json --board-backend none --gm-classifier groq --gm-accept yes --goal-id force_entry --freeform-action "Próbujemy wyważyć bramę z całej siły." --challenge-roll gm_generated=14 --session-id gm_classifier_demo --max-steps 2
```

- [ ] Freeform działa domyślnie na Gemini, jeśli w środowisku jest `GEMINI_API_KEY`; `--gm-classifier groq` nadal pozwala wymusić Groq.
- [ ] Brak `GROQ_API_KEY` albo `GEMINI_API_KEY` daje czytelny błąd bez stack trace.
- [ ] Aplikacja pokazuje narrację propozycji LLM.
- [ ] Aplikacja pokazuje wybrany test, ST, progress i pasujący zasób.
- [ ] Analyzer odrzuca deklaracje spoza fantasy/sceny, np. laserowy pistolet albo wyważanie dmuchnięciem.
- [ ] `--gm-accept no` odrzuca interpretację bez rzutu i bez zmiany progressu.
- [ ] Pytanie graczy, np. `Jak przejść bez hałasu?`, daje odpowiedź bez rzutu.
- [ ] Zasób działa tylko wtedy, gdy jest w ekwipunku i ma pasujący tag.
- [ ] Wynik rzutu aktualizuje challenge przez zwykły progress/fail-forward flow.
- [ ] `--gm-dry-run` pokazuje propozycję bez rzutu i bez zmiany progressu.
- [ ] JSONL zawiera analizę deklaracji, propozycję, akceptację/odrzucenie i historię prób.
- [ ] Deklaracja sprzeczna z kontekstem, np. lot na linie, jest odrzucana albo zamieniana na legalną alternatywę bez naciągania zasad.
- [ ] `--interactive-freeform --freeform-retries 3` pozwala wpisać kolejną deklarację po odrzuceniu.
- [ ] Payload JSONL zawiera `scenario_context`, `zone_context`, `challenge.context` i `dynamic_state`.

## Notatki Z Testu

```text
Data:
Backend: simulator / hardware
Scenariusz:
Tester:

Wynik:

Problemy:

Następne poprawki:
```
## P1 — karty bohaterów i czytnik QR

- [ ] Na ekranie nowej gry wybierz scenariusz i potwierdź, że nie ma checkboxów
  postaci ani ekranowego przycisku rozpoczęcia.
- [ ] Zeskanuj dwie różne karty bohaterów. Ekran powinien pokazać kolejność 1–2,
  a ponowny skan tej samej karty nie może utworzyć duplikatu.
- [ ] Zeskanuj `DECLINE`: ostatnia postać ma zniknąć. Zeskanuj ją ponownie, a
  następnie `ACCEPT`: aplikacja ma przejść do przygotowania z właściwą drużyną.
- [ ] Spróbuj zatwierdzić pustą drużynę oraz dodać szóstą postać. Obie deklaracje
  muszą zostać odrzucone czytelnym komunikatem.
- [ ] Przy teście z jednym wykonawcą zeskanuj kartę postaci legalnej i nielegalnej.
  Legalna ma zostać wybrana, a nielegalna odrzucona bez zmiany stanu.
- [ ] Przy teście z opcjonalną Pomocą zeskanuj prowadzącego i pomocnika. Powtórz,
  skanując prowadzącego i `ACCEPT`; drugi przebieg ma kontynuować bez pomocnika.
- [ ] Podczas oczekiwania na kartę bohatera plansza nie może podświetlać pól
  postaci ani automatycznie uruchamiać skanu pola.
- [ ] Odłącz czytnik. Dostępne mają być ponowienie połączenia, anulowanie lub
  powrót, ale nie ekranowy i nie planszowy wybór bohatera.
- [ ] Wydrukuj `assets/physical_cards/heroes/hero_cards_a4_v1.pdf` w skali 100%,
  odwracając po długiej krawędzi. Sprawdź wymiar 63 × 88 mm oraz odczyt każdego QR.

## M8.6 — światło i widzenie

- [ ] W `abandoned_watchtower` sprawdź, że brama pokazuje półmrok, a obserwacja
  Perception przez szczelinę wymaga dwóch k20 i wybiera niższy wynik.
- [ ] Zapal pochodnię Bohatera i potwierdź, że obserwacja do 20 ft nie ma
  utrudnienia, UI pokazuje zasięg/czas, a po 60 minutach mechanicznego czasu
  pochodnia gaśnie.
- [ ] W ciemnej strefie potwierdź, że sight-based observation bez światła lub
  odpowiedniego zmysłu jest blokowana czytelnym komunikatem.

## M8.7 — Search, Hide i pułapki

- [ ] W panelu Łotrzycy wybierz „Przeszukaj”, wpisz dwa wyniki k20 wymagane
  przez półmrok i potwierdź koszt 10 minut oraz wykrycie linki przy wyniku 15+.
- [ ] Po wykryciu linki sprawdź osobno rozbrojenie, obejście i świadome
  uruchomienie; nieudane rozbrojenie powinno przejść do fizycznego Dexterity save.
- [ ] Wykonaj Hide Łotrzycą, potwierdź widoczny zapis wyniku, a potem rozpocznij
  ciche wejście. Po setupie bohater nie powinien rzucać ponownie, a wynik ma być
  porównany osobno z goblinami.
- [ ] Zapalenie pochodni ukrytym bohaterem powinno natychmiast usunąć jego
  eksploracyjny stan Hide.

## M8.8 — drzwi, zamki, pojemniki i obiekty

- [ ] Przy bramie sprawdź, że Stara brama i Skrzynia strażnicza pokazują stan
  zamka, KP oraz HP bez wpisywania deklaracji do chatu.
- [ ] Łotrzycą wybierz „Otwórz zamek” skrzyni. UI powinno wymagać fizycznego d20,
  pokazać narzędzia złodziejskie i doliczyć biegłość.
- [ ] Po odblokowaniu wybierz „Otwórz”, a następnie „Przeszukaj zawartość”.
  Dwanaście strzał powinno zostać ujawnionych w scenie, ale nie przeniesionych
  automatycznie do ekwipunku.
- [ ] Zaatakuj skrzynię: wynik poniżej KP nie zmienia HP, obrażenia poniżej progu
  nie zmieniają HP, a zejście do 0 niszczy obiekt i ujawnia zawartość.
- [ ] Otwórz Starą bramę przed encounterem i potwierdź, że jej projekcja w walce
  nie blokuje ruchu ani nie zapewnia cover. Powtórz z zamkniętą bramą i sprawdź
  blokadę oraz `+5`.

## M8.9 — podróż i exhaustion

- [ ] W `village_square_mvp` odblokuj wyjście do strażnicy, wybierz normalne
  tempo, nawigatora i udany fizyczny rzut. Handoff powinien doliczyć 45 minut.
- [ ] Powtórz z nieudanym rzutem nawigacji. Drużyna nadal dociera, ale handoff
  pokazuje dodatkowe 30 minut i uruchamia odpowiednie progi zegara.
- [ ] Sprawdź szybkie i wolne tempo: payload pokazuje odpowiednio karę do
  passive Perception albo możliwość Stealth oraz zmieniony czas.
- [ ] W testowym contentcie z trasą ponad 8 godzin wpisz rzuty Constitution save
  dla każdego rozpoczętego dodatkowego odcinka. Porażka zwiększa exhaustion.
- [ ] Rozpocznij encounter wyczerpanym aktorem i potwierdź zachowanie poziomu
  oraz odpowiednie kary; long rest powinien usunąć dokładnie jeden poziom.

## M8.10 — rozmowy i testy społeczne

- [ ] Przy rannym zwiadowcy wybierz cel uspokojenia. UI powinno jawnie pokazać
  Perswazję, Oszustwo i Zastraszanie przed wpisaniem deklaracji.
- [ ] Wybierz Oszustwo, choć narracja klienta LLM sugeruje Perswazję. Podgląd
  testu ma nadal pokazać Charisma (Deception) oraz ST z tabeli reakcji.
- [ ] Sprawdź automatyczną zgodę, test i odmowę dla różnych kombinacji
  attitude/risk; odmowa niemożliwej prośby nie może uruchomić efektów sukcesu.
- [ ] Po nieudanej próbie potwierdź blokadę ponowienia, odblokowanie po zmianie
  wymaganej flagi i ostateczne wyczerpanie limitu.
- [ ] Zmień nastawienie przez authored outcome, wyjdź z rozmowy i wróć. UI oraz
  snapshot powinny zachować attitude, historię i ujawnione informacje.

## M8.11 — crafting w downtime

- [ ] Na rynku w `village_square_mvp` otwórz kartę „Rzemiosło w downtime”.
  Bohater z narzędziami kowala powinien móc wykuć sztylet, a Łotrzyca powinna
  widzieć konkretny powód blokady.
- [ ] Przed potwierdzeniem sprawdź podgląd: 1 gp materiałów, 8 godzin pracy,
  kuźnia na rynku i trwały sztylet.
- [ ] Po potwierdzeniu sprawdź spadek portfela Bohatera z 10 gp do 9 gp, sztylet
  w jego ekwipunku oraz przesunięcie zegara o 480 minut.
- [ ] Potwierdź, że oba autorskie progi zwłoki wioski uruchomiły się tylko raz.

## M8.12 — wspólne warunki eksploracji i walki

- [ ] Przy `vault_gate` doprowadź do krytycznej porażki i nieudanego save'a
  hazardu. Bohater powinien otrzymać `Prone` oraz `Poisoned` ze źródłem
  „Zatrute kolce na bramie” i duration `until_short_rest`.
- [ ] Rozpocznij encounter bez leczenia. `Poisoned` ma nadal dawać utrudnienie
  do ataków i testów cech.
- [ ] Zakończ encounter zwycięstwem. `Poisoned` powinno wrócić do eksploracji,
  natomiast warunki `until_encounter_end` oraz chwyty przeciwników mają zniknąć.
- [ ] Ukończ short rest i potwierdź komunikat wygaśnięcia zatrucia. Warunek
  permanentny nie może zostać usunięty przez ten odpoczynek.

## M8.13 — rezultaty i konsekwencje między scenami

- [ ] Ukończ zadanie wioski bez zwłoki i przejdź do strażnicy. Ekran końca ma
  pokazać sukces „Sprawne dotarcie do strażnicy” oraz ukończony cel źródłowy.
- [ ] Powtórz po short reście uruchamiając alarm strażnicy. Wynik ma być
  `partial_success`, a narracja ma informować o przygotowanych obrońcach.
- [ ] Powtórz z nieudaną nawigacją. Drużyna nadal dociera, ale wynik ma być
  `fail_forward` i wskazywać zgubienie starego traktu.
- [ ] Sprawdź payload handoffu: zawiera tylko wskazane `propagated_flags`,
  zwalidowane `target_effects` oraz `source_objectives`; ekran gracza nie
  ujawnia technicznych nazw ukrytych flag docelowych.

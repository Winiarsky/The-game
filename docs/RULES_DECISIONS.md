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
- Ruch diagonalny jest dozwolony i kosztuje naprzemiennie 5/10/5/10 feet w ramach ścieżki.
- Trudny teren kosztuje 10 feet za wejście na pole.
- Diagonalne wejście w trudny teren używa tego samego mnożnika: 10/20/10/20 feet.
- Sojusznik zajmuje pole, przez które można przejść, ale traktujemy je jako trudny teren.
- Przeciwnik blokuje przejście i zakończenie ruchu.
- Aktor nie może zakończyć ruchu na polu zajętym przez inną istotę.
- Ściany i blokujące przeszkody blokują przejście.
- Zamknięte drzwi blokują ruch, otwarte drzwi nie blokują ruchu.
- Ruch po skosie przez całkowicie zablokowany róg jest niedozwolony.
- W turze walki ruch jest pulą `speed_feet`, którą można dzielić przed i po ataku.
- Atak zużywa akcję, ale nie kasuje pozostałego ruchu.
- Koniec tury resetuje akcję i pulę ruchu.

Poza zakresem MVP:

- rozmiary istot,
- przeciskanie się,
- skakanie,
- wspinaczka,
- pływanie,
- latanie,
- ruch wymuszony.
- Dash, Disengage, Dodge,
- ataki okazyjne,

Odstępstwa / decyzje planszowe:

- Licznik kosztu diagonalnego jest częścią pathfindingu i nie resetuje się po kroku ortogonalnym w tej samej ścieżce.

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
- Grywalna scena po setupie używa realnego flow inicjatywy przed pierwszą turą.
- Runtime debugowy może użyć `--initiative-mode fixed` tylko jako trybu testowego.
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

Status: partial

Źródło:

- `GAME_DESIGN.md`
- TODO: zweryfikować względem SRD dla attack roll, AC, damage roll i critical hit.

Implementacja MVP:

- MVP obsługuje prosty melee weapon attack.
- Aplikacja pokazuje legalne cele ataku LED-ami.
- Gracz wybiera cel przez planszę albo fallback runtime.
- Atak porównuje wynik ataku z AC celu.
- Naturalne `20` przy ataku oznacza trafienie krytyczne.
- Naturalne `1` przy ataku oznacza automatyczne pudło.
- Przy trafieniu aplikacja prosi o wynik obrażeń.
- W MVP gracz może wpisać końcowy wynik obrażeń krytycznych samodzielnie.
- Obrażenia są wpisywane jako komponenty z typem obrażeń.
- Obrażenia najpierw zmniejszają temporary HP, potem HP.
- HP nie spada poniżej `0`.
- Stan pokonania/śmierci jest uproszczony w MVP.
- `hp > 0` nie oznacza automatycznie, że obiekt jest legalnym celem ataku.
- Cel ataku musi być `attackable=True` i `visible`.
- Mini-pętla walki obsługuje start tury, zużycie akcji, koniec tury, przejście inicjatywy i zakończenie walki.
- W runtime demo przeciwnik wykonuje automatyczny melee attack przez wstrzyknięty RNG.
- Jeśli przeciwnik musi się ruszyć przed atakiem, aplikacja pokazuje ścieżkę LED i wymaga kliknięcia pola docelowego po fizycznym przestawieniu figurki.
- Domyślny przeciwnik demo używa ataku `Szabla`, modyfikatora `+4` i obrażeń `1d6 + 2 slashing`.
- Walka kończy się, gdy żywa zostaje tylko strona bohaterów albo tylko strona przeciwników.
- Runtime może zatrzymać demo po limicie rund bez rozstrzygania zwycięzcy.
- Statystyki demo mogą pochodzić z lokalnego contentu JSON w `content/`.
- Lokalny content MVP nie jest pełnym SRD ani pełną bazą D&D 5e.
- Multi-actor MVP obsługuje wielu bohaterów i wielu przeciwników w jednej kolejce tur.
- Wszyscy aktorzy używają pierwszego ataku z contentu jako domyślnej akcji.
- Przeciwnicy wybierają najbliższy legalny cel; remis rozstrzyga pozycja i `id`.

Poza zakresem MVP:

- pełne reakcje,
- pełne ranged attacks,
- czary, area effects i złożone itemy,
- odporności i podatności,
- pełne death saving throws,
- destrukcja obiektów i przeszkód.
- pełne AI ruchu przeciwników,
- ruch w turze podczas multi-actor MVP,
- bonus action, reaction i multiattack.

Odstępstwa / decyzje planszowe:

- Szczegółowe zasady śmierci i umierania zostają odłożone, dopóki nie będą potrzebne w pierwszej scenie.
- Obiekty atakowalne są przewidziane w modelu targetowania, ale pełny flow niszczenia obiektów zostaje później.
- Komunikat aplikacji i LED-y muszą być zsynchronizowane: legalne cele, wybrany cel, wynik ataku.
- W board-first MVP gracz nie wybiera najpierw akcji z menu: klika pole na planszy, a aplikacja interpretuje intencję jako ruch albo atak.
- Pierwsze kliknięcie pola pokazuje podgląd intencji, drugie kliknięcie tego samego pola potwierdza.
- Kliknięcie innego legalnego pola przed potwierdzeniem zmienia podgląd.
- Kliknięcie pola aktywnego aktora pokazuje podstawowe opcje aktora; w MVP obsługiwana jest opcja zakończenia tury.
- Zakończenie tury przed wykorzystaniem całego ruchu jest legalne; niewykorzystany ruch przepada na końcu tury.
- Przeciwnicy w MVP mogą wykonać ruch w stronę najbliższego celu, a potem zaatakować, jeśli cel stał się legalny.
- Ruch przeciwnika jest wizualizowany jako czerwona ścieżka i pomarańczowe pole docelowe.
- Pole może mieć wiele dostępnych intencji, np. przeciwnik stojący na obiekcie interaktywnym.
- W takim przypadku plansza pokazuje kolor `multi-option`, kliknięcie tego samego pola przełącza opcję, a Enter potwierdza aktualną opcję.
- Obiekty sceny mogą deklarować `blocks_movement`, `allow_interaction_when_occupied_by_enemy` i `cover_bonus`.
- Jeśli cel ataku stoi na obiekcie z `cover_bonus`, runtime dodaje jawny modyfikator osłony do instrukcji rzutu ataku.
- Interakcja przy przeciwniku może wywołać uproszczony atak okazyjny jako decyzję planszowego MVP.
- Pierwsza scena grywalna może zakończyć się przez spełnienie celu sceny, a nie tylko przez pokonanie wszystkich przeciwników.
- Interakcja z jawnym obiektem jest akcją główną: kliknięcie obiektu pokazuje podgląd, drugie kliknięcie potwierdza i zużywa akcję.
- Interakcja może mieć test cechy `d20`; aplikacja pokazuje cechę, skill, ST, aktywne modyfikatory i końcowy modyfikator przed wpisaniem wyniku.
- Wynik eksploracyjnej interakcji może ustawić flagę sceny, np. `crate_secured` albo `crate_trap_missed`.
- Objective może używać warunku `flag_equals`, więc scena może zakończyć się dopiero po konkretnym skutku interakcji, a nie samym kliknięciu obiektu.
- Setup startowy pokazuje pola, na których gracze mogą ustawić figurki, ale MVP nie skanuje automatycznie poprawności ustawienia.

Testy:

- `tests/unit/test_combat_targets.py`
- `tests/unit/test_attack_targets.py`
- `tests/unit/test_attack_flow.py`
- `tests/unit/test_attack_resolution.py`
- `tests/unit/test_damage.py`
- `tests/unit/test_attack_led_feedback.py`
- `tests/unit/test_demo_mini_combat.py`
- `tests/unit/test_combat_session.py`
- `tests/unit/test_turn_intent.py`
- `tests/unit/test_enemy_auto_movement.py`
- `tests/unit/test_enemy_auto_attack.py`
- `tests/unit/test_demo_mini_combat_loop.py`
- `tests/unit/test_scenario_loader.py`
- `tests/unit/test_scenario_content_files.py`
- `tests/unit/test_scene_setup.py`
- `tests/unit/test_scene_objectives.py`
- `tests/unit/test_scene_flags.py`
- `tests/unit/test_scene_interactions.py`
- `tests/unit/test_interaction_intent.py`
- `tests/unit/test_turn_led_feedback.py`

## Eksploracja

Status: partial

Implementacja MVP:

- Eksploracja jest osobnym trybem sceny, niezależnym od encountera.
- Nie ma inicjatywy, tur walki ani indywidualnego ruchu bohaterów.
- Drużyna ma wspólny pionek i aktualną strefę.
- Setup eksploracji pokazuje jawne strefy/lokacje bez wymuszania kliknięcia potwierdzającego.
- Fizyczne jawne elementy sceny, np. NPC, obiekty albo markery, mogą wymagać rozstawienia przez `requires_setup`; wtedy są prowadzone batchami i potwierdzane kliknięciem.
- Ukryte i warunkowe elementy nie są zdradzane w setupie.
- Kliknięcie innej strefy tworzy podgląd przejścia, a drugie kliknięcie tej samej strefy potwierdza.
- Domyślny widok eksploracji pokazuje tylko główne punkty dostępnych lokacji, nie całe strefy.
- Kliknięcie aktualnego punktu głównego pokazuje wszystkie dostępne opcje jako kolorowe menu planszowe.
- Kliknięcie pola menu wybiera konkretną opcję; `Wycofaj` zamyka menu.
- `Rozejrzyj się po okolicy` dopiero wtedy podświetla całą strefę i pozwala klikać jej kafle.
- `Zbadaj obszar` dotyczy aktualnej strefy, może być wykonane raz na strefę i bierze najwyższy wynik z testu drużyny.
- Sukces badania może ujawnić ukryty punkt i ustawić flagę sceny.
- Eksploracyjne przeszkody docelowo nie powinny być twardymi blokadami rzutu.
- Domyślny model eksploracyjnego testu to `fail-forward`: porażka zmienia koszt, ryzyko albo komplikację, ale nie powinna zatrzymywać całej sceny.
- Wyzwania eksploracyjne mają model postępu, np. `progress_required`, `current_progress`, opcje działań, postęp na sukcesie, postęp na porażce i konsekwencje. Pierwszy zaimplementowany slice to zamknięta brama w `abandoned_watchtower`.
- Opcje wyzwań mogą mieć tagi zasobów/narzędzi/czarów, np. `climbing`, `crowbar`, `quiet`; pasujące itemy mogą dawać premię, przewagę albo łagodzić hałas/komplikacje. Pełny ekwipunek pozostaje poza MVP.
- Proste opcje eksploracyjne typu `message` mogą ustawiać flagi sceny. Dzięki temu rozmowa, odczytanie tablicy albo obejrzenie punktu zainteresowania może domknąć objective bez sztucznego testu cechy.
- `village_square_mvp` jest pierwszą mini-sceną eksploracji społecznej: kilka jawnych lokacji, setup jawnych NPC/obiektów, ukryty punkt i objective zależne od flagi.
- LLM może analizować i klasyfikować kreatywne deklaracje graczy do ustrukturyzowanych propozycji challenge, ale nie może samodzielnie zmieniać zasad ani stanu gry.
- LLM MVP obsługuje opcjonalnych providerów Groq i Gemini oraz ma dwa kroki: analyzer deklaracji oraz classifier mechaniki challenge. Gemini jest domyślnym providerem dla trybu freeform, a zwykła eksploracja bez freeform nadal nie odpala LLM.
- Prompt LLM składa się z centralnie ładowanych plików w `content/prompts/` oraz warstw kontekstu: scenariusz, lokacja, challenge, dynamiczny stan gry i historia prób.
- `llm_context` może opisywać dostępne materiały, zakazane założenia, sensowne podejścia, niemożliwe podejścia i ryzyka.
- Zasób zaproponowany przez LLM działa mechanicznie tylko wtedy, gdy drużyna go posiada i `bonus_tags` zasobu przecinają się z tagami podejścia.
- Propozycja LLM może utworzyć tymczasową opcję `gm_generated`, która jest rozstrzygana przez zwykły deterministic `resolve_challenge_option`.
- Propozycja LLM musi zostać zaakceptowana przed rzutem; odrzucenie interpretacji nie zmienia stanu gry.
- Historia prób challenge jest częścią deterministycznego stanu eksploracji i trafia do payloadu LLM.
- `gm_classifier.py` powinien zawierać mechanikę integracji, parsowania i walidacji, a nie content konkretnej sceny. Aktualne globalne listy tagów, lokalnych umiejętności i komplikacji są oznaczone jako polityka MVP; docelowo powinny przejść do definicji scenariusza, challenge albo obiektu interakcji.

Poza zakresem MVP:

- pełny UI point-and-click,
- losowe wydarzenia,
- czas/ryzyko za ponawianie działań,
- automatyczne przejście z eksploracji do encountera.
- pełny silnik wyzwań z wieloetapowymi konsekwencjami poza pierwszym challenge bramy,
- integracja pełnego ekwipunku i czarów z opcjami eksploracyjnymi,
- głosowy interfejs kreatywnych deklaracji przez LLM.

Testy:

- `tests/unit/test_exploration_setup.py`
- `tests/unit/test_exploration_menu.py`
- `tests/unit/test_exploration_led_feedback.py`
- `tests/unit/test_exploration_zones.py`
- `tests/unit/test_party_checks.py`
- `tests/unit/test_demo_exploration_scene.py`

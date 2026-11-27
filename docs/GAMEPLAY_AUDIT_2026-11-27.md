# Audyt gry i wdrożenie — 27.11.2026

Praca lokalna na `feat/led-keyboard-control`; początkowy stan Git był czysty.
Zakres wykonany: aktualna Misja 0, jej konfrontacje, konsekwencje, prezentacja
reguł oraz narzędzie balansu. To działająca planszowa gra RPG w Pythonie,
z Flaskem i fizycznymi kośćmi. Bazą jest D&D 5e 2014/SRD 5.1, z jawnymi
odstępstwami projektu: konfrontacje `progress_v1`, runy i Rezonans w walce.
Zachowano motyw długu wieśniaków, ton Gildii, bohaterów i identyfikatory treści.

## Skille i źródła

Dziesięć skillów było już zainstalowanych w `.agents/skills`. Porównano wszystkie
94 pliki z archiwami oryginalnych repozytoriów dla commitów zapisanych w
[rejestrze źródeł](../.agents/skills/SOURCES.json): zawartość była identyczna.
Zachowano references, skrypty, szablony i dostarczone licencje. Rejestr wskazuje
też upstreamy bez zadeklarowanej licencji; nie przypisujemy im licencji MIT.
Nie zastępowano istniejącej instalacji ani nie instalowano drugich kopii.

| Skill | Zastosowanie w tej pracy |
|---|---|
| `game-design-review` | audyt informacji, decyzji, wyzwań, ekonomii, tempa i weryfikacji; końcowy przegląd trzech niezależnych agentów tylko do odczytu |
| `game-architect` | wspólny konstruktor konfrontacji poza UI, bez nowego frameworka |
| `game-balance-analysis` | diagnoza brakującej korzyści wskazówki, porównanie efektów i ograniczeń |
| `design-quest-structure` | odbiór ładunku, dzwon, rozliczenie i odrębność długu |
| `audit-narrative-state` | flagi, rozpoczęta próba, zapis/wznowienie, konsekwencje finału |
| `audit-choice-quality` | płatna wskazówka po zakończeniu pokoju, jawne nagrody dzwonu |
| `rpg-dev` | korekty istniejących scen i informacji przed decyzją; bez zmiany świata |
| `rpg-critic` | krytyczny przegląd i [trwały rejestr](../content/scenarios/misja_0_dzwon/MASTERPLAN-critiques.md) |
| `headless-game-balance` | trzy strategie, sparowane ziarna, ślady i wspólny silnik |
| `property-based-testing` | enumeracja pełnej domeny k20 i niezmienniki przebiegów, bez nowej biblioteki |

Lokalne adaptacje: przykłady `~/work/bin/python` zastąpiono projektowym
`.venv/bin/python` i ścieżkami `.agents/skills`; brakujące opcjonalne odwołanie
do `design-player-choice` zastąpiono zainstalowanym `audit-choice-quality`.
Wskazówki projektowe odsyłają do `AGENTS.md`, a szablon krytyki wskazuje Codexa.
Warsztatowe potwierdzanie każdego kroku zastępuje wyraźna zgoda użytkownika
na autonomiczne zmiany. `rpg-npc-cast` jest opcjonalny i nie był potrzebny;
nie uruchamiano generatorów postaci ani ilustracji. Skrypt `context_stack.py`
przeczytano przed uruchomieniem; użyto go wyłącznie do rozpoznania dokumentów.
Zmienione opisy skillów będą wykryte w kolejnej turze; ich pliki przeczytano
i zastosowano bezpośrednio w tej pracy.

Nie dodawano storyletów ani osobnego modelu wiedzy: scenariusz ma mały, jawny
model stanów. Nie dodawano skilli D&D 2024/SRD 5.2 ani generowania grafiki.
`skill-installer` posłużył do oceny instalacji. `python-testing-patterns` oraz
`webapp-testing` wspierały testy i kontrolę prawdziwego Chrome.
Przegląd objął dziewięć domen `game-design-review`; pominięto nową koncepcję/
zmianę estetyki oraz społeczność/rywalizację platformową, poza zakresem zmian.

## Potwierdzone problemy i wykonane poprawki

| ID / wpływ | Dowód przed poprawką | Skutek i naprawa | Sprawdzenie |
|---|---|---|---|
| G1 / wysoki | `ui/mission_zero.py:scene` zmieniało tylko stare `approaches[].dc`; nowy konstruktor czytał `progress_dc` | zakup wskazówki nie pomagał. Nowa konfrontacja kwatery ma ST 12 zamiast 14, także przy ST określonym dla pojedynczego podejścia | rzeczywiste komendy adaptera: suma 12 daje postęp; zapis i wczytanie zachowują zatwierdzony wynik |
| G2 / wysoki | `scripts/evaluate_mission_zero.py` używał `application.confrontation` i modelu talii | raport mierzył inny system. Używa teraz `application.progress_confrontation.build` oraz `rules.progress_confrontation` | znany wynik dla seed 0, koszty, zakończenie i 44 100 przebiegów |
| G3 / średni | `mission_zero.command` sprawdzało akcje ukrytego panelu mimo aktywnej konfrontacji | możliwa zmiana sceny spod otwartej decyzji. Serwer wymaga zakończenia lub opuszczenia konfrontacji; świadome wczytanie checkpointu nadal działa | odrzucenie żądania bez zmiany stanu |
| G4 / średni | `mission_zero_recovery.choices` oferowało plotkę również po odbiorze kwatery | można było wydać 1 sz na już nieużyteczną wskazówkę. Opcja znika po rozstrzygnięciu pokoju | odrzucenie powtórnej transakcji, brak ubytku złota |
| G5 / średni | wspólny `dilemma.md` obiecywał wybór dzwonu także pokonanej drużynie | osobny tekst porażki zgodny z warunkami Boruta i rzeczywistą listą opcji | Chrome i przejście do rozliczenia |
| G6 / średni | cena alternatyw dzwonu pojawiała się po decyzji | przed wyborem widać +10 sz teraz, brak premii dla wsi i 20 sz u pasera później; kwoty pochodzą z `rewards.json`. Termin przyszłej Misji 2 pozostaje tajny zgodnie z masterplanem | pełne teksty dla drużyn z Mirą i bez niej, brak nierozwiązanych znaczników |
| G7 / średni | teksty po rozejmie i przy wozie wymagały przygotowania dawnej many | usunięto nieistniejący krok; wznowienie opisuje zachowany postęp i działania, także w starszym silniku | przegląd treści, regresje konfrontacji |
| G8 / średni | `after_accepted.md` obiecywał powrót postawy do środka po zamianie wozu | kradzież mikstury jest dodatkowym przesunięciem. Tekst opisuje jedno przesunięcie ku Solidarności, zachowując pamięć poprzednich decyzji | przegląd trzech wydarzeń i istniejących reguł postawy |

Refaktor zachowujący zachowanie: konstruktor przeszedł z UI do warstwy aplikacji;
import `ui.progress_confrontation.build` pozostaje zgodny. Logika reguł pozostaje
niezależna od Flask, urządzeń, plików i czasu. `board/` nie wymagało zmian.
Zmiana zachowania: przywrócenie obiecanej wskazówki, walidacja aktywnej sceny
i ukrycie bezużytecznej transakcji. Koszty, bazowe ST 14, progi wyników,
statystyki walki i nagrody zachowano. Pozostałe wartości balansu nie wymagały korekty.

## Stan i ścieżki przygody

| Stan | Inicjalizacja i zapis | Odczyt / konsekwencja |
|---|---|---|
| `flags: rumor_known` | rozmowa z Borutem, po rozejmie bez opłaty, inaczej 1 sz | ST nowej kwatery −2; zapis zachowuje wiedzę i koszt |
| `cargo` / `searches` | pusty słownik; jednorazowy bezpieczny odbiór lub konfrontacja | trzy części dostawy wymagane do rozliczenia; powrót do pokoju nie odnawia nagrody |
| `current.state`, `token`, `committed` | konstruktor konfrontacji; kolejne komendy i autozapis | wznowienie tej samej próby; płatna dodatkowa kość i zastosowanie wyniku bez podwójnej zapłaty |
| `outcome` | wynik walki, rozejm albo odmowa | darmowa plotka, jednorazowa naprawa, ograniczenie dzwonu po porażce |
| `bell` / `debt` | osobne decyzje | premia albo odroczona płatność; pokwitowania i obietnica nie znikają przy połączeniu ścieżek |
| `campaign_mission_zero_case` | aktualizacja decyzji i rozliczenie | gotowy trwały wątek przyszłej kampanii, nadal `resolved=False` |

Sprawdzono rozliczenie po rozejmie, po odmowie, przez pasera i po porażce;
bezpieczny odbiór omija dodatkowe znaleziska i pozwala ukończyć misję.
Pokonanie Boruta nie jest zabiciem: masterplan jawnie określa 0 PW bez śmierci.
Gra nie oferuje usuwania kluczowych NPC ani utraty dokumentu fabularnego jako
osobnej akcji; nie dopisywano fikcyjnych gałęzi takich działań.

## Wynik balansu i jego granice

[Pełny raport](../content/scenarios/misja_0_dzwon/BALANCE_REPORT.md): 98 składów,
30 ziaren na skład, trzy nazwane strategie, 44 100 przebiegów i 8820 par
kwatery bez wskazówki / ze wskazówką. Każda scena bota startuje z 20 reputacji;
raport nie udaje ekonomii całej wyprawy. Używa stałej kolejności `HEROES`,
nie wszystkich permutacji tur. Wybór strategii nie przesuwa kości innych postaci.

| Drużyna | Próby na wariant, najlepsza cecha bez wydawania reputacji | Sukces bez wskazówki | Sukces ze wskazówką |
|---|---:|---:|---:|
| 3 | 1050 | 52,9% | 63,4% |
| 4 | 1050 | 69,0% | 81,0% |
| 5 | 630 | 54,9% | 68,7% |
| 6 | 210 | 55,7% | 72,4% |

Dla modyfikatorów −3…+5 enumeracja k20 potwierdza dokładnie dwie dodatkowe
zwykłe udane ścianki, bez zmiany naturalnej 1 i 20. To naprawa korzyści już
obiecanej graczowi. Boty potwierdzają skuteczność, a nie atrakcyjność decyzji.
Próg sukcesu jest zaokrąglany względem liczby bohaterów; próbka pokazuje
różnicę między czterema a pięcioma osobami. Nie ma jeszcze przyjętego celu
trudności ani danych od graczy uzasadniających zmianę tych progów.

Większy przebieg po 100 ziaren przekroczył limit 60 sekund; nie uznano jego
częściowego pliku za wynik. Zakończony raport ma 30 ziaren. Pełne ślady są
opcjonalnym JSONL, generowanym strumieniowo do wybranej lokalizacji.

## Zgodność i dalsze sprawdzenia

Snapshot pozostaje w schemacie 35. Nie ma migracji ani zmiany istniejących ID.
Rozpoczęta konfrontacja zachowuje utrwalone ST i silnik: starego ST 14 nie
przeliczamy w środku próby. ST 12 obowiązuje przy utworzeniu nowej kwatery
z posiadaną wskazówką. Teksty wznowienia pozostają poprawne dla dawnego silnika.

Pozostają: fizyczny test numpada i WLED; ogranie tempa przeszukań oraz różnic
trudności dla 3–6 osób; przyszłe rozstrzygnięcie długu i sprzedaży dzwonu
w treści kolejnych misji. To istniejące otwarte wątki, nie blokady ukończenia Misji 0.

## Uruchomienie i weryfikacja

```bash
.venv/bin/python scripts/keyboard_playtest.py
.venv/bin/python scripts/keyboard_playtest.py --arena --skip-setup
.venv/bin/python scripts/evaluate_mission_zero.py --trials 30 --jsonl /tmp/mission-zero.jsonl
PATH="$PWD/.venv/bin:$PATH" scripts/safe_pytest.sh --timeout 60 tests/integration/test_mission_audit.py
PATH="$PWD/.venv/bin:$PATH" scripts/safe_pytest.sh --timeout 60 tests/integration/test_mission_quest_paths.py
PATH="$PWD/.venv/bin:$PATH" scripts/safe_pytest.sh --timeout 60 tests/unit/test_mission_balance.py
PATH="$PWD/.venv/bin:$PATH" scripts/safe_pytest.sh --timeout 60 tests/integration/test_mission_audit_browser.py
```

Pierwsze polecenie otwiera grę pod `http://127.0.0.1:5202/play` i podgląd
LED pod portem 5002, z osobnymi danymi testu. `--check` sprawdza przygotowanie
bez serwerów. Testy uruchamiać szeregowo. Przeglądarka korzysta z istniejącego
Chrome i opcjonalnego `ui-test`; w lokalnym `.venv` doinstalowano zadeklarowane
już `pytest` i `playwright`, bez zmiany zależności aplikacji.

## Wykonane testy

Ostateczne wyniki: **121 różnych testów, wszystkie zakończone powodzeniem**.
Każdy plik uruchamiano osobno przez `safe_pytest.sh`, szeregowo, z timeoutem
60 sekund. Nie uruchamiano pełnej, szerokiej kolekcji pytest.

| Plik | Wynik |
|---|---:|
| `tests/unit/test_progress_confrontation.py` | 24 passed |
| `tests/unit/test_mission_balance.py` | 24 passed |
| `tests/unit/test_mission_recovery.py` | 14 passed |
| `tests/unit/test_progress_confrontation_runtime.py` | 6 passed |
| `tests/unit/test_mission_zero.py` | 39 passed |
| `tests/integration/test_mission_audit.py` | 5 passed |
| `tests/integration/test_mission_quest_paths.py` | 5 passed |
| `tests/integration/test_mission_audit_browser.py` | 2 passed |
| `tests/unit/test_keyboard_mission_browser.py` | 1 passed |
| `tests/unit/test_progress_confrontation_browser.py` | 1 passed |

Przed zmianami: reguły 24/24; Misja 0 38/39; recovery 12/14.
Zastane błędy dotyczyły nieuwzględnionego menu na planszy, czytania nowego
stanu starym silnikiem i pomijania istniejącej biegłości w rzucie obronnym/
ataku. Testy dostosowano do rzeczywistej umowy; nie usuwano biegłości z gry.
Nowe regresje wskazówki i walidacji scen odtworzyły błędy przed naprawą.

Chrome sprawdził widoczne ST 12 i przejście do rzutu, finał porażki,
początek misji sterowany klawiaturą do wyjścia z Gildii oraz wydawanie
reputacji. Obejrzano dwa zrzuty przy 1221×656 w `/tmp/dnd-mission-audit-ui/`.
Początkowo opcjonalny Playwright był niedostępny w interpreterze testów;
po instalacji `ui-test` testy wykonano. Sandbox blokował `setsockopt` Chrome;
te same próby przeszły po uruchomieniu lokalnego Chrome poza sandboxem.

Dodatkowo: oba tryby launchera `--check` (pełna misja i arena), 93 wpisy
indeksu tekstów i ścieżki ich plików, dziesięć metadanych skillów i wskazane
licencje, sekwencja postawy 3→4→5→4 oraz `git diff --check` zakończyły się
powodzeniem. Fizycznych świateł ani czujników nie używano.

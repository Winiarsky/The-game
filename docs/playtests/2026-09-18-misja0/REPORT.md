# Misja 0 — raport z rozgrywek przez UI

**Cztery pełne przejścia Misji 0 — drużyny 3, 4, 5 i 6 osób — dotarły do podsumowania i mają zachowane końcowe zapisy.** Misja jest przechodnia, a kontrakt, rozejm i rozliczenie tworzą spójną całość. Przed sesją nowych graczy poprawiłbym przede wszystkim opłatę Nimry, zgodność Brakki z wydrukiem oraz instrukcje sterowania. Największą niewiadomą gameplayową pozostaje obciążenie obsługą kart przy stole.

## Poprawki po audycie — 18.09.2026

**Potwierdzone usterki techniczne i UI poprawiono.** Poniższe przebiegi, liczby,
zrzuty i zapisy P3–P6 dokumentują wersję sprzed poprawek; nie przeliczano ich
wstecz. Balans, nagrody za odmowę rozejmu i tempo konfrontacji pozostają do
ręcznej oceny autora.

| Zgłoszenie | Status i zmiana | Sprawdzenie |
|---|---|---|
| Opłata Nimry | **Naprawione.** Sukces identyfikuje bez opłaty; Gildia nadal pobiera 5 sz. | Sukces przy 0 i 20 sz, osobny test płatnej Gildii. |
| Ciężar pieniędzy | **Naprawione.** Identyfikacja, plotka i potrącenia korzystają z przeliczenia na nominały, zamiast zamiany całego portfela na cp. | Wartość i liczba monet dla trzech rodzajów opłat. |
| Inicjatywa przez ✓ | **Naprawione.** Przyczyną było ograniczenie panelu inicjatywy do identyfikatora areny. Teraz obejmuje starcia bohaterów z fizyczną maną, w tym Misję 0. | Chrome, prawdziwy serwer i endpoint planszy: +, −, zatwierdzenie kości i podsumowania dla 3 bohaterów, wejście do walki. Fizyczne przyciski pozostają do sprawdzenia przy stole. |
| Brakka a wydruk | **Poprawiony lokalny rekord startowy.** 35 PW, SIŁ 18, KON 16 — zgodnie z kanoniczną definicją używaną przez samouczek i maty. | Start nowej gry przez formularz i porównanie z generatorem wydruku. Plik `data/characters/brakka.character.json` jest lokalnym, ignorowanym przez Git rekordem. |
| Instrukcje walki | **Naprawione.** Wybór runą; ekranowy wybór awaryjny wskazany osobno. Dostępny ruch nie zgłasza braku pól, a tura wroga pokazuje instrukcję rozegrania zamiaru. | Regresja menu/ruchu i kontrola tekstów UI. |
| Dawne koszty many | **Naprawione dla aktualnego profilu.** Przypomnienia, opisy menu i celowania korzystają z katalogu progów/spalania. Tarcza nie sugeruje wydania białej karty. | Regresja aktualnego menu i przypomnień; zachowana obsługa dawnych profili zapisów. |
| Szósty bohater poza widokiem | **Naprawione.** Początek tury odsłania kartę aktywnego bohatera; kolejne zgłoszenia kart zachowują przewinięcie. +/− nadal przewijają ręcznie. | Chrome 1131×720: pięć tur pomocy, szósta aktywna postać i zgłoszenie kolejnej karty. |
| Techniczne stany i długie pasywy | **Naprawione.** Liczniki serii/ofensywy/czasu szału/ruchu ukryte w prezentacji. Pasywy mają krótką nazwę i szczegóły do rozwinięcia; odblokowanie cechy nie udaje premii +1. | Chrome: nazwa, zachowanie pełnego opisu, filtrowanie znaczników. |
| Stany pozostające po walce | **Naprawione.** Koniec starcia wygasza efekty do końca/początku tury, rundy i następnego ataku. Długotrwałe efekty pozostają. | Test granicy efektów oraz przyjęcia rozejmu z aktywnymi znacznikami serii/ofensywy. |
| Obrócony wóz | **Naprawione.** Narracja wylicza pola z obróconego kafla P02 i ustawienia drogi w `maps/setup.json`: (9,16), (9,17). | Porównanie geometrii i tekstu sceny. |
| Drobne teksty | **Naprawione.** „1 pełną rundę”, „2–4 pełne rundy”, przycisk „Zakończ walkę i przejdź dalej”; wzmianki o możliwościach Miry/Nimry tylko przy ich obecności. Opcjonalne akapity nadal są edytowalnymi plikami scenariusza. | Regresje odmiany oraz drużyn z bohaterkami i bez nich. |

### Weryfikacja poprawek

Testy uruchamiane pojedynczymi plikami przez `scripts/safe_pytest.sh`.
Nie powtarzano czterech pełnych rozgrywek ani nie podłączano ponownie WLED;
sprawdzenie poprawek obejmuje logikę oraz Chrome z produkcyjnym przepływem UI.

**93 testy zaliczone** (bez pominięć):

| Plik | Wynik |
|---|---:|
| `tests/unit/test_mission_audit_fixes.py` | 18 passed |
| `tests/unit/test_mission_recovery.py` | 14 passed |
| `tests/unit/test_mission_zero.py` | 38 passed |
| `tests/unit/test_effects.py` | 9 passed |
| `tests/unit/test_initiative_panel.py` | 10 passed |
| `tests/unit/test_mission_audit_browser.py` | 2 passed |
| `tests/unit/test_confrontation_presentation_browser.py` | 2 passed |

Weryfikacja przeglądarkowa: 1131×720, 1300×657 i 390×800. Test inicjatywy
odtworzył brak panelu przed poprawką i przeszedł po jej wdrożeniu. Testy
funkcjonalne przygotowują stany scen, po czym sprawdzają produkcyjne operacje;
nie są dodatkowymi pełnymi przejściami kampanii. Pierwsza partia
`test_mission_zero.py` osiągnęła limit 90 s; ponowienie z limitem 180 s
zakończyło się wynikiem 38 passed. Kontrola składni Pythona i `git diff --check`
również zakończone poprawnie.

Główne zmienione pliki: `ui/mission_zero_recovery.py` (identyfikacja i portfel),
`ui/exploration_app.py` (inicjatywa, instrukcje i koszty), `rules/effects.py`
(wygaszanie), `ui/static/exploration.js`, `confrontation.js`, `physical_mana.js`
(panele), `ui/mission_zero.py`, `ui/mission_setup.py` oraz teksty i ustawienie
drogi w `content/scenarios/misja_0_dzwon/`. Pliki aplikacji są pod
`src/dnd_board_game/`. Aktualizację zadań zapisano również w `TODO.md`.

**Do testu ręcznego:** odczucia z gry, liczba zgłoszeń kart, wartość rozejmu,
opcjonalna lekcja draina i wygoda sterowania fizycznymi przyciskami.
Poprawione statystyki Brakki dotyczą nowej gry. Stare zapisy, w tym dowody
audytu, zachowują swoje dotychczasowe statystyki i rozliczenia.

## Jak testowano

Normalny launcher → wybór bohaterów → Misja 0 → rozgrywka. Chrome 1300×720 dla P3–P5 i 1131×720 dla P6, prawdziwa aplikacja Flask, osobny katalog zapisów. Sterownik klikał formularze i przyciski oraz wysyłał wskazania pól/run przez produkcyjny endpoint planszy. Fizyczny egzemplarz kart zastępowała tasowana lista; naturalne wyniki kości pochodziły z zapisywanego generatora losowego. Nie ustawiano zwycięstw, PW, etapów ani zawartości puli bezpośrednio w silniku.

WLED i adapter szeregowy były rzeczywiście podłączone. Potwierdzenia WLED zapisano, lecz nie było obserwacji LED kamerą ani ręcznego naciskania fizycznych przycisków. Wnioski o czytelności i emocjach są oceną projektu na podstawie zachowania UI — nie badaniem z prawdziwymi uczestnikami. To mała próba jakościowa, nie statystyczny dowód balansu.

Działania odpowiadały początkującym graczom: najczęściej większa wartość dobranej karty, proste skupianie ataków, pomoc przy trudnym ST. Nie korzystano z wiedzy o przyszłych kartach. W walce nie optymalizowano całego zestawu zdolności: w P3–P5 wybierano pierwszy dostępny atak; P6 preferował atak magiczny Nimry przed kosturem. Sterownik czasami odkładał niedostępny wcześniej atak do następnej tury także po podejściu w zasięg. Te uproszczenia zaniżają skuteczność części bohaterów; długość walk nie jest miarodajnym pomiarem optymalnej gry ani siły klas. Losowanie AI przeciwników pochodziło z aplikacji (`encounter_rng = random.Random(7)` przy resetowaniu sesji); nie było niezależnym eksperymentem Monte Carlo.

## Przebiegi

| Drużyna | Skład | Nessa | Wóz | Walka | Koniec |
|---|---|---|---|---|---|
| 3 | Brakka, Dagna, Erynd | Kompromis, runda 2 | Sukces, runda 4; 1 karta została | Rozejm w rundzie 2 po pierwszym pokonanym | Podsumowanie: pełny ładunek, dzwon dla wsi, dokumenty Boruta, medalik, zidentyfikowany pierścień |
| 4 | Garran, Lorian, Mira, Nimra | Sukces, runda 3 | Porażka, runda 3; zmęczenie na 2 rundy | Rozejm odrzucony; zwycięstwo w rundzie 7 | Pełny ładunek, medalik, pierścień; poręczenie Garrana, dzwon u pośrednika Miry; zapis końcowy |
| 5 | Brakka, Dagna, Erynd, Garran, Nimra | Kompromis, runda 3 | Sukces, runda 3; 19 kart zostało | Rozejm w rundzie 3 | Pełny ładunek, dzwon do Gildii (+10 sz), pierścień rozpoznany przez Nimrę; błędnie pobrano 5 sz |
| 6 | Brakka, Dagna, Garran, Lorian, Mira, Nimra | Sukces, runda 4; 1 karta została | Porażka, runda 4; zmęczenie na 1 rundę | Rozejm w rundzie 3 | Pełny ładunek, pierścień rozpoznany przez Nimrę, poręczenie Garrana, dzwon u pośrednika Miry; zapis końcowy |

Skalowanie potwierdzone w UI: 3/4/5/6 bohaterów otrzymało odpowiednio 30/40/50/60 kart many (6/8/10/12 każdego koloru), opór Nessy wynosił 27/36/45/54, a na posterunku stało 5/6/7/8 przeciwników.

## Najważniejsze problemy do poprawienia przed testami ręcznymi

**Najwyższy priorytet: bezpłatna identyfikacja Nimry jest płatna.** P5: kwatera → Nimra: spróbuj identyfikacji → naturalne 14 + INT 4 = 18, ST 15 → sukces. W rozliczeniu natychmiast pojawiło się −5 sz, jeszcze przed powrotem do Gildii. `mission_zero_recovery.py:279` wywołuje `identify_paid()` tak samo jak gildyjny specjalista. Powinno wywołać bezpłatne `identify()`. Przy braku pieniędzy kod może również odrzucić udany test komunikatem o braku złota — ten wariant wynika z kodu, nie był odegrany. Błąd powtórzył się w P6 przy naturalnym 20 + 4. Dowód: `p5-events.jsonl`, kroki 1170–1175 i 1206 (rozliczenie); P6: 1557–1559 i końcowe rozliczenie.

1. **Sprzeczne instrukcje wyboru akcji walki.** Nagłówek: „Wybierz akcję na panelu planszy”; opis: „Wybierz ikonę na ekranie” i „Dolny pasek run jest wyłączony”. Ikony w głównym indeksie są nieklikalnymi `span`, działające ekranowe przyciski kryją się pod „Awaryjnym wyborem ekranowym”. Runy ruchu i ataku faktycznie działały. Ujednolicić instrukcję z docelowym sterowaniem.
2. **Fałszywy komunikat braku ruchu.** Po wyborze ruchu Brakki UI mówi „Brak dostępnych pól ruchu”, choć są legalne pola i dało się przejść z (6,20) na (7,16). Nie wyświetlać komunikatu pustej listy, gdy lista nie jest pusta.
3. **Pozostałości starej ekonomii many.** Przypomnienia i rozwijane opisy mówią „Wydaj: czerwona”, podczas gdy nowy panel Szału poprawnie pokazuje brak kosztu many, a inne zdolności próg i spalanie. Podać jedną obowiązującą wersję we wszystkich miejscach.
4. **Rozjazd statystyk Brakki między aplikacją i kartami.** Nowa gra z zapisanej postaci: 32 PW, Siła 19, Kondycja 15 (+2). Aktualny PDF `content/print/characters/bohaterowie_zestawy_startowe_A4.pdf` i jego generator: 35 PW, Siła 18, Kondycja 16 (+3). Zmienia to także testy Kondycji i efekt założenia pierścienia +1 Siły. Pozostałe sześć bazowych wartości PW jest zgodnych. Ujednolicić źródło mat i postaci startowych albo jasno oznaczyć wariant.
5. **Instrukcja położenia wozu nadal sprzed obrotu.** Na drodze podaje (9,17)–(10,17), a obecny obrót wymaga (9,16)–(9,17). Czerpać instrukcję z tej samej definicji geometrii co podświetlenie.
6. **Zatwierdzanie inicjatywy wymaga dodatkowego odtworzenia na fizycznym przycisku.** W próbie przez endpoint pola ✓ nie przesuwało kreatora, mimo instrukcji. Widoczny przycisk ekranowy działał. Nie mylić tego z późniejszymi turami wroga, w których właściwym potwierdzeniem jest wskazanie pola figurki.

7. **Opłaty zamieniają cały portfel na miedziaki i zwiększają masę waluty.** W końcowym zapisie P4 Garran ma 4400 cp = 44 sz wartości, ale 88 lb monet. W P3 Brakka ma 3500 cp = 35 sz i 70 lb. Opłaty za identyfikację, plotkę i potrącenia używają `CurrencyWallet(cp=...)`: zachowują kwotę, lecz zmieniają nominały. Sama wypłata nagrody dodaje złote monety poprawnie. Poprawić przed dalszym użyciem udźwigu i zakupów.

8. **Szósta postać znika pod przewijaniem także podczas swojej tury.** P6, 1131×720: w drugiej rundzie Nessy Nimra jest aktywna, ale jej karta zaczyna się na y=786, a widoczny obszar kończy na y=508; scrollTop pozostaje 0. Nazwa w nagłówku i przyciski są widoczne, natomiast punkty/pasywy wymagają ręcznego przewinięcia. Pokazywać bieżącą postać stale albo automatycznie przewijać do jej karty. Dowód: `screenshots/p6-nimra-active-confrontation.png`, geometria w `checks.jsonl`.

Źródła do poprawek: `src/dnd_board_game/ui/static/exploration.js` (opis panelu akcji, okolice 7041), `src/dnd_board_game/ui/exploration_app.py` (podgląd ruchu, okolice 22711), `src/dnd_board_game/ui/mission_zero_recovery.py` (opłaty: 166, 206, 258), `src/dnd_board_game/physical_cards/mana_print.py` (139, źródło postaci do wydruku), `content/scenarios/misja_0_dzwon/text/road.md` (3, współrzędne wozu).

## Czytelność i narracja

- P6: wybór sześciu bohaterów oraz pasek portretów mieszczą się przy 1131×720; narracja przewija się przez pola +/− (scrollTop 0 → 166 → 0). Wejście na arenę i powrót do siedziby działają.
- Układ odprawy/konfrontacji z portretem Nessy i portretami bohaterów jest czytelny. Główny opis przewija się oddzielnie, decyzje pozostają pod nim. Kompromis nie był ujawniony na początku.
- Techniczne stany zaśmiecają panel: „Rodzaj rozpoczętej serii: 0”, „Ofensywa w tej turze: +1”, „Czas Rage”, podwójne „koszt tej tury: 0: 0”. Gracz potrzebuje tylko skutku, który wpływa na decyzję. Dwa znaczniki „Rodzaj rozpoczętej serii” i „Ofensywa w tej turze” pozostają także w końcowych zapisach P3–P6 mimo czasu „do końca tury”; należy je sprzątać przy końcu walki, a nie tylko ukryć. Nie potwierdzono wpływu tych resztek na kolejną walkę.
- Pasyw często pojawia się jako pełen akapit w kilku miejscach, z dopiskiem „+1”, chociaż jest przełącznikiem, a nie premią liczbową. W panelu wystarczy nazwa i krótki stan; szczegóły po rozwinięciu. Przy 1300×720 pełne opisy wypychają część kafli akcji pod dolną krawędź ekranu (np. `screenshots/p5-combat-turn-1-erynd.png`).
- W turze Procarza pasek planszy mówi „Nie ma aktywnego aktora walki”, choć niżej trwa „Tura Procarz: rozegraj zamiar”. Pokazać instrukcję właściwą dla tury wroga (zrzut `p6-combat-turn-2-procarz.png`).
- Przycisk kończący walkę brzmi „Zastosuj wynik encountera”. Zastąpić np. „Zakończ walkę i przejdź dalej”.
- Po wyniku k4=1 opis mówi „przez 1 pełnych rund”. Dodać odmianę liczby („1 pełną rundę”, „2–4 pełne rundy”).
- Narrator wspomina możliwość Miry bez Miry w składzie i identyfikację Nimry bez Nimry. Nie blokuje to gry, lecz tekst może być warunkowy tak jak przyciski.
- Kontrakt, dług wsi i dzwon jako rzecz spoza spisu dobrze łączą się w spójny dylemat. Zostawienie dzwonu nie uniemożliwiło poprawnego rozliczenia transportu.

## Gameplay — ocena jakościowa

Z perspektywy pierwszej sesji cel jest zrozumiały: odebrać wskazany ładunek, a potem zdecydować, co zrobić z dzwonem i długiem. Narrator prowadzi przez sceny bez konieczności samodzielnego szukania właściwej lokacji. Największe tarcie powstaje przy przejściu do walki: gracz musi odróżnić wybór akcji, podgląd, wskazanie celu, deklarację, wpisanie kości i zatwierdzenie wyniku, a teksty sterowania nie są spójne.

Naprawa wozu z jedną kartą na końcu daje wyraźne napięcie. Podobnie P6 dopiero w czwartej rundzie negocjacji wywalczyło pełną miksturę z jedną kartą w talii, po odrzuceniu dostępnego kompromisu. W rozmowie działa alternatywa „pomóż mocniejszemu podejściu” i wybór kompromisu. Cztery pełne konfrontacje (Nessa, wóz, zbrojownia, kwatera) wymagają jednak wielu powtarzalnych zgłoszeń kart i rzutów. To największe potencjalne źródło zmęczenia obsługą. W ukończonych konfrontacjach P3 było 25 prób i 78 zgłoszeń kolorów, P4: 44 próby i 146 zgłoszeń, P5: 31 prób i 99 zgłoszeń, P6: 46 prób i 154 zgłoszenia (P5 i P6 już bez przeszukania zbrojowni). Liczby obejmują dobieranie/spalanie, także ponownie odzyskane karty; nie obejmują walki ani porzuconej pierwszej próby drogi P4. Nie są to czasy sesji ani czyste porównanie balansu składów.

W P3 szybki rozejm zakończył walkę przed 21 pkt i mana drainem. W P5 Garran zdążył osiągnąć 21 pkt w trzeciej rundzie przed przyjęciem rozejmu, więc nie jest to reguła każdego pokojowego przebiegu. Wariant pokojowy jest fabularnie sensowny, ale nie gwarantuje poznania pełnego cyklu walki. Warto dodać opcjonalną krótką lekcję, zamiast sztucznie przedłużać tę walkę.

W P6 potwierdzono wygaszenie jednorundowego zmęczenia w rundzie 2 i wykonanie Lodowego impulsu Nimry. W dłuższym przebiegu P4 potwierdzono wygaszenie zmęczenia po dwóch rundach, poprawne użycie mikstury (8 + 1 + 4 = 13 PW, zużycie akcji i fiolki), 21+ pkt z zatrzymaniem doboru oraz spalanie kosztów czarów. Walka zakończyła się w rundzie 7, z Garranem na 6 PW i siedmioma kartami talii. **Mana drain w walce nie wystąpił w tej próbie.**

Odmowa rozejmu nie przyniosła widocznej dodatkowej nagrody ani XP (końcowe XP pozostają 0), za to kosztowała dodatkowe rundy, rany i płatną plotkę. Rozejm wygląda na mechanicznie lepszy wybór. Można uznać to za zamierzony przekaz misji albo dodać drugiej ścieżce osobną korzyść; obecnie nie są to równorzędne warianty ryzyka/nagrody.

## Sprawdzone rozliczenia i stan techniczny

- P3: 30 sz kontraktu − 5 sz identyfikacji = 25 sz netto; medalik i pierścień, dzwon dla wsi.
- P4: 40 − 1 za plotkę − 5 za identyfikację = 34 sz netto; wykorzystana mikstura, medalik i pierścień.
- P5: 50 + 10 za dzwon − błędne 5 za Nimrę = 55 sz netto; pierścień, bez medalika po pominięciu przeszukania.
- P6: 60 − błędne 5 za Nimrę = 55 sz netto; pierścień, bez medalika.
- P4 i P6: przyszła wypłata Miry 20 sz zapisana z `after_mission=misja_2`, `paid=false`; teraz nie wypłacono jej drugi raz. Poręczenie Garrana i dokumenty pozostają otwartym wątkiem.
- Zarejestrowano 11 945 odpowiedzi HTTP 200, cztery przekierowania 302 i jedną poprawną odmowę 400 za zajęte pole w początkowym sterowniku P3. **Brak HTTP 500.** Licznik obejmuje także odpytywanie planszy, nie oznacza liczby decyzji graczy.
- WLED w ostatniej próbce potwierdził rewizję 1632, bez oczekującej aktualizacji i błędu (11 ms dla tej próby). Serwer audytu zamknięto, a adapter wysłał polecenie wygaszenia i zwolnił port.
- Końcowy ekran sprawdzono dodatkowo przy 1131×584: przyciski zakończenia i przewijania mieszczą się, rozliczenie przewija się osobno.

Nie zmieniano implementacji zasad podczas rozgrywek. Dodano raport, dowody, skrypty audytu i zadania w `TODO.md`. Sprawdzenie składni czterech skryptów przez `py_compile` przeszło; nie uruchamiano pełnego pytest, ponieważ przedmiotem zadania były przejścia przez UI.

## Dowody i ograniczenia

`metrics.json`: liczba rund, prób, wsparć i zgłoszeń kart w zakończonych konfrontacjach. `pN-events.jsonl`: sceny, wybory, rzeczywiste wyniki, tasowania i pobrania kart. `http.jsonl`: odpowiedzi i opóźnienia API. `screenshots/`: obrazy etapów. `completed_saves/`: odseparowane końcowe zapisy drużyn do analizy. `wled-status.jsonl`: potwierdzenia sterownika LED.

Pierwszy przebieg służył także dopracowaniu sterownika. Jego błędy opisano w `NOTES.md` i nie zaliczono do błędów gry: pominięte trzy zwroty Oddechu odtworzono z historii, próba zajętego pola została słusznie odrzucona, powtarzane potwierdzenia bez wskazania oczekiwanego pola wroga były niewłaściwym wejściem. Nie wolno traktować liczby wszystkich prób sterownika ani jego czasu wykonania jako czasu normalnej sesji.

Nie sprawdzono wszystkich zdolności, wariantów podbić, manipulacji talią Loriana, upadku bohatera/ratowania przy 0 PW, krytycznej porażki przeszukania ani przyszłej wypłaty po misji 2. Wypłata Miry została sprawdzona jako odroczony wpis kampanii, nie jako wykonana późniejsza misja. Przygotowanie ekwipunku przechodzono z zestawem domyślnym. Reset wspólnej talii sprawdzano przy zmianach scen; draina w toku walki nie wymuszano.

P4 wymagał ponownego otwarcia serwera audytu i wczytania punktu kontrolnego drogi po zamknięciu procesu testowego. Przyczyny zakończenia procesu nie ustalono; nie zaliczono go jako awarii aplikacji. Nieukończona próba drogi jest w surowym dzienniku, ale nie w tabeli wyników i metrykach zakończonych konfrontacji.

Wybrane zrzuty:

- [Sześciu bohaterów — aktywna Nimra poza widokiem](screenshots/p6-nimra-active-confrontation.png).
- [Powtarzane opisy i sprzeczna instrukcja akcji walki](screenshots/p5-combat-turn-1-erynd.png).
- [Podsumowanie pięcioosobowej drużyny](screenshots/p5-final-summary.png).
- [Wybór sześciu bohaterów przy 1131×720](screenshots/p6-party-selection.png).

[Instrukcja uruchomienia narzędzi audytu](REPRODUCE.md) · [notatki i korekty sterownika](NOTES.md) · [metryki konfrontacji](metrics.json).

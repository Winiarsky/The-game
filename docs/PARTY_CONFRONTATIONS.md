# Drużynowe konfrontacje eksploracji — aktualizacja 19.09.2026

Aktualny model rozmów i obiektów w Misji 0 i samouczku. Zastępuje aktywny samouczek blackjacka; starsze rozpoczęte próby nadal odczytuje silnik zgodności. Zwykłe rozmowy fabularne i pułapki walki zachowują swoje dotychczasowe przepływy.

## Wspólna procedura

Jedna figurka drużyny, osobna pula i tura każdego uczestnika. Misja obsługuje 3–6 bohaterów; menu ćwiczeń pozwala wybrać 1–5 spośród siedmiu. Prowadzący działa pierwszy, następni w kolejności składu; bez dodatkowego rzutu inicjatywy. NPC i obiekt mają wspólny opór oraz profil ST i kości efektu dla każdego podejścia.

Najpierw przypisz podejścia zgodnie z poniższą sekcją.

1. Przygotuj pełny komplet: po `max(5, 2 × liczba bohaterów)` każdego koloru, przetasuj. Osobiste pule puste.
2. Poniżej 21 punktów obowiązkowo dobierz jedną z dwóch odkrytych kart. Druga pozostaje; następny dobierający uzupełnia ofertę. Jeśli została tylko jedna karta, można ją wziąć. Przy 21+ nie dobierasz; przekroczenie nie szkodzi.
3. Kolor uruchamia pasyw. Punkty korzystają z tej samej tabeli bohatera co w walce.
4. Po doborze wybierz test, pomoc dozwoloną przez powiązania albo podgląd dolnej karty.
5. Test: `k20 + cecha + premia naładowania + pasywy + pomoc`. Naturalne 20 nie omija ST, naturalne 1 nie przesądza porażki.
6. Sukces: `kość podejścia + modyfikator cechy + pasywy wpływu`, minimum 0. Odejmij od wspólnego oporu. Biegłość i premia many nie zwiększają wpływu.
7. Po efekcie spal 1 kartę z wierzchu, również po nieudanym teście. Zgłaszaj kolory; aplikacja zachowuje bilans wszystkich fizycznych kart. Osobisty ładunek zostaje.
8. Po działaniach wszystkich postaci następuje jedna reakcja sytuacji, potem kolejna runda.

| Ładunek wymagany | Premia many do testu | Spalanie |
|---|---|---|
| 0 | +0 | 1 |
| 6 | +2 | 1 |
| 12 | +4 | 1 |
| 21 | +6 | 1 |

UI wybiera najwyższy osiągnięty próg. Pomoc zastępuje test, spala 1 kartę i daje +1 do najbliższej próby testu wybranego sojusznika (+2 ze Współpracą). Kolejne pomoce, także od tej samej postaci w kolejnej turze, sumują się bez limitu. Cała suma jest zużywana po jego pierwszej próbie k20 — także po porażce. Nie znika przy doborze, końcu rundy ani gdy wsparty bohater pomaga komuś innemu. Nie zwiększa wpływu/postępu. Nie można wspierać siebie; bonus nie przechodzi do nowej konfrontacji. Płatność po efekcie; wymagane spalenie musi zostać zgłoszone przed następną turą.

## Podejścia i graf pomocy

Każda scena ma własną listę `approaches` w katalogu. W Misji 0 jest to
`content/scenarios/misja_0_dzwon/mechanics/confrontations.json`, a w samouczku
`content/balance/confrontation.json`. Opcja zawiera `id`, `name`, `description`,
`ability`, `dc`, `die`, `repeatable` i `supports` (identyfikatory wspieranych podejść).
`supports: ["*"]` pozwala wybrać dowolnego innego sojusznika; `[]` nie daje pomocy.
Strzałki są skierowane: A → B nie oznacza B → A. Działanie wspiera jedną osobę.

Przed przygotowaniem talii bohaterowie wybierają runami, w kolejności swoich tur.
Nie rzucamy dodatkowo na inicjatywę. Każdy może wybrać dowolną opcję sceny,
opcje dla jednej postaci znikają po wyborze, a powtarzalne pozostają dostępne. Wybrane podejście zostaje do końca konfrontacji.
Zajęte opcje z `repeatable: false` znikają z wyboru; opcje z `repeatable: true` pozostają.
Brak pola oznacza `false`. Przypisanie run pozostaje stałe. Scena może mieć mniej
opcji niż bohaterów, jeśli choć jedna jest powtarzalna. Wsparcie zawsze kierujesz
do innego bohatera; powtarzalność sama nie dodaje nowych powiązań pomocy.
Cechę wybranego podejścia dodajemy zarówno do testu, jak i wpływu/postępu.
Nie doliczamy dawnych umiejętności, biegłości ani darmowych premii Loriana/Erynda.
Efektywna cecha uwzględnia założone przedmioty.

| Nessa — podejście | Cecha | ST | Wpływ | Może wspierać | Przydział |
| --- | --- | --- | --- | --- | --- |
| Komplementy | Charyzma | 18 | k4 + cecha | Argumenty, Zrozumienie obaw | Jedna postać |
| Stanowcze żądania | Kondycja | 25 | k10 + cecha | Blef | Jedna postać |
| Logiczne argumenty | Inteligencja | 20 | k4 + cecha | Żądania, Zrozumienie obaw | Powtarzalne |
| Blef | Charyzma | 22 | k8 + cecha | Żądania | Jedna postać |
| Zrozumienie obaw | Mądrość | 19 | k6 + cecha | Dowolne podejście | Powtarzalne |
| Osobista gwarancja | Charyzma | 20 | k6 + cecha | Argumenty, Zrozumienie obaw | Jedna postać |

Opcje nie muszą pokrywać wszystkich cech ani dawać każdej cesze jednej metody.
Przy wozie występują unoszenie, mocowanie osi, dźwignia i ocena gruntu;
w kwaterze dwa różne podejścia korzystają z Inteligencji. Wartości są startowe,
do oceny przy stole, a nie wyniki ukończonego balansu.

## Bezpieczna alternatywa: podgląd spodu talii

Po obowiązkowym doborze (albo przy 21+) zamiast testu/pomocy można podejrzeć
jedną dolną kartę. Bez zgłaszania koloru wybierz runą pozostawienie na spodzie
lub przeniesienie na wierzch. To całe działanie, bez spalania; nie zmienia
odkrytej oferty, osobistych pul ani zgromadzonej pomocy. Aplikacja zapisuje przesunięcie karty, zachowując już znaną kolejność.
Kolor nieznanej karty zgłaszasz dopiero przy odkryciu do oferty lub spalaniu.
Gdy talia jest pusta, alternatywa to czekanie bez podglądu. Reakcja sytuacji
po rundzie nadal zużywa talię — czekanie nie zatrzymuje zegara konfrontacji.

## Pasywy kolorów

Każdy bohater ma pięć wpisów w `content/balance/confrontation.json`. Pięć prostych efektów przypisano różnym kolorom:

- Stanowczość: +1 do wpływu za kartę, maksymalnie +2.
- Skupienie: +1 do testu za kartę, maksymalnie +2.
- Współpraca: pomoc +2 zamiast +1, nadal za 1 kartę. Kolejne pomoce kumulują się; dodatkowe karty koloru nie wzmacniają samego pasywu.
- Opanowanie: chroni jedną kartę osobistej puli przed każdą reakcją, bez kumulacji.
- Oddech: mając właściwy kolor, po każdej udanej próbie oddaj najstarszą spaloną kartę na spód talii, przed spaleniem kosztu. Nie kumuluje się i nie zużywa się po aktywacji.

Premie utrzymują się tylko tak długo, jak odpowiednie karty są w puli. Utrata karty usuwa jej premię i może przywrócić dobieranie poniżej 21. Kolorowe pasywy eksploracji są oddzielne od bojowych. Wszystkie 35 przypisań widnieje w UI i na kartach.

## Presja i zakończenie

Początkowy opór: 9 × liczba osób dla Nessy, 10 × liczba osób dla schowka. Po każdej rundzie reakcja spala `max(3, liczba osób)` kart. Cykl reakcji to presja, presja z odebraniem ostatniej karty największego ładunku, presja z odzyskaniem k4 oporu. Przy remisie utraty decyduje kolejność drużyny. K4 aplikacja losuje jednokrotnie i zapisuje wynik; odświeżenie nie przerzuca.

Opór 0 oznacza sukces. Wyczerpanie oznacza brak kart do **wymaganej operacji**, nie sam pusty stos. Jeżeli nie da się pokryć pełnego spalania, konfrontacja kończy się. Rozpoczęty test i jego wpływ rozstrzyga się wcześniej: zwycięski cios pozostaje sukcesem. Brak karty do obowiązkowego doboru także kończy scenę. Nie ma ostatniej darmowej rundy ani automatycznego resetu i dalszej rozmowy. Przed następną próbą zbierz wszystkie pule i spalone karty do nowej talii.

Nie dodajemy bojowego wygasania jednej karty na rundę: zegarem tej konfrontacji jest reakcja sytuacji. Nie ma też osobnych manewrów, ruchu w sporze ani bojowych ataków/ultów.

Cztery opcjonalne warunki zachowane w nowej procedurze: kompromis po zbiciu połowy oporu; dodatkowa informacja za sukces z dwiema niebieskimi w całej drużynie; czerwony drażliwy temat zmieniający cenę sukcesu; jednorazowy odzysk karty za zobowiązanie. Wyniki i zobowiązania zapisują się w historii prób.

## Obsługa i samouczek

Postać → Eksploracja → Skład drużyny / Po kolei / Wybierz ćwiczenie. Domyślnie prowadzący i dwoje towarzyszy. Skład można zmienić przed próbą. Dwanaście przypadków dla każdej postaci (84): NPC, obiekt, pomoc, 21+, reakcja, drain, cztery warunki, dwie samodzielne konfrontacje. Postęp nowego kursu nie dziedziczy zaliczeń starego blackjacka.

Próg 21, reakcja i drain mają jawne przygotowane stany fizycznych stosów, opisane przed rozpoczęciem. Pozostałe próby startują od pełnego kompletu. Ćwiczenie pomocy wymaga co najmniej dwóch osób. Powrót i restart działają także podczas doboru, spalania i rzutu. Pojedyncza próba nie przesuwa postępu kursu.

Wybory idą przez podświetlone runy. Naturalne wyniki testu i wpływu wprowadza się osobno przez fokus, −/+, podsumowanie, korektę i końcowe ✓. Premie doliczane są raz. Po wczytaniu trzeba potwierdzić zachowanie fizycznych stosów albo powtórzyć próbę. Zapisy przechowują profil sceny, podejścia i powiązania uczestników, etap wyboru, podglądu i rzutu, premie, karty oraz wynik reakcji. Nierozpoczęty starszy zapis otrzymuje nowy wybór podejść; rozpoczęta konfrontacja zachowuje dotychczasowy profil do zakończenia.

## Granice i ewaluacja

To wersja startowa do ręcznego sprawdzenia. `python scripts/evaluate_party_confrontations.py --trials 30` uruchamia 2520 prób w produkcyjnym silniku. [Raport](reports/PARTY_CONFRONTATIONS_V01.md) porównuje ciągłe testowanie ze wsparciem przy niskiej szansie. Historyczny raport sprzed 19.09.2026 dotyczy darmowej, niekumulującej się pomocy i dawnych kosztów prób; jego wyników nie należy traktować jako oceny bieżącego balansu. Symulacja nie mierzy czasu zgłaszania fizycznych kart ani jakości decyzji ludzi.

Silnik: `rules/confrontation.py`; budowanie profili i przygotowane lekcje: `application/confrontation.py`; katalog: `scenarios/confrontation.py`; transport i zapis: `ui/confrontation.py`. Niskopoziomowe `board/` pozostaje bez zmian.

Pasywy działają jako statusy przy posiadaniu koloru; drain/koniec konfrontacji je wyłącza. Gruba obwódka symbolu oznacza kumulację (test i wpływ, do +2), cienka brak kumulacji samego pasywu (Współpraca, ochrona puli, odzysk). Niezależnie od obwódki kolejne akcje pomocy sumują premię odbiorcy.

## Postawa drużyny a przygotowanie

Przed konfrontacją stosujemy [postawę drużyny](PARTY_ETHOS.md): ze standardowego
kompletu wyłączamy wskazane kolory. Instrukcja podaje dokładny skład i sumę.
Wyłączone karty nie są spalonymi i nie podlegają odzyskowi. Rozpoczęta konfrontacja
zachowuje swój skład także po wznowieniu zapisu.

## Poprawianie pomyłek w obsłudze

„Cofnij ostatni wybór” jest dostępne na ekranie i pod runą Fala (slot 23).
Koryguje ostatnie podejście, zgłoszenie koloru lub wybór karty do osobistej puli.
Historia obejmuje do ośmiu kolejnych takich kroków i jest zachowana w zapisie.
Starsze zapisy zaczynają zbierać historię od pierwszego wyboru po aktualizacji.
Cofnięcie podejścia zwalnia jego wyłączność i przywraca poprzedniego wybierającego.
Cofnięcie doboru odtwarza ofertę, pulę, punkty i pasywy; fizyczną kartę trzeba
odłożyć do oferty. Przy korekcie koloru zgłaszamy tę samą kartę, bez nowego doboru.
Przy korekcie spalania poprzednia karta wraca na wierzch do ponownego zgłoszenia.

Tasowanie, deklaracja testu/pomocy, podgląd, reakcja i przejście do kolejnej tury
zamykają wcześniejsze okno korekt. Nie cofamy rzutów ani wyników zakończonej
konfrontacji. Poprawa koloru spalonego za pomoc nie cofa ani nie powiela samej
pomocy. Po odczycie zapisu najpierw trzeba potwierdzić zachowanie fizycznych stosów.
Powrót do opisu misji pozostaje osobną kontrolką ↩ (slot 29).

## Potwierdzenia przy fizycznej talii (19.09.2026)

Oddech po udanej próbie zatrzymuje rozliczenie przed kosztem testu. UI podaje
kolor najstarszej spalonej karty: należy przełożyć ją na spód talii i nacisnąć ✓.
Dopiero potwierdzenie aktualizuje stosy i rozpoczyna spalanie kosztu. Zapis
zachowuje ten krok; ponowne potwierdzenie nie odzyskuje drugiej karty.

Kompromis przy połowie oporu pojawia się po opłaceniu bieżącej akcji, przed
następną turą. Osobne runy przyjmują lub odrzucają ofertę. Test, pomoc i podgląd
nie mogą zastąpić tej decyzji. Odmowa jest jednorazowa i trwa w zapisie.
Starsze zapisy zachowują już rozliczone odzyskania oraz odrzucone oferty.

Log akcji zawiera zgłoszone dane, aktora przed akcją, strefę spalonych i licznik
talii przed/po, oczekujące odzyskanie oraz stan oferty kompromisu.

## Czytelne opisy pasywów

Każdy pasyw ma osobno warunek uruchomienia, efekt i zasady kumulacji.
UI pokazuje warunek oraz efekt od razu; wyjątki i dokładniejsze wyjaśnienia
są w szczegółach. Dane `display` w katalogach konfrontacji i walki są wspólne
dla aplikacji i mat do druku, z krótszym wariantem `short` na macie.

Oddech ma schemat „spalone → 1 karta → spód talii”. Dotyczy karty spalonej
najwcześniej, dowolnego koloru, a nie koniecznie koloru uruchamiającego pasyw.
Sam dobór many nie odzyskuje kart. Przykład: przed sukcesem Dagny są 3 spalone
karty. Po przełożeniu jednej i potwierdzeniu zostają 2. Następnie Dagna spala
koszt testu i znowu są 3 — pasyw zadziałał, mimo identycznej końcowej liczby.

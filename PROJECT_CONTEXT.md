# Kontekst Projektu

Budujemy nową lokalną aplikację do prowadzenia taktycznej gry RPG w stylu Dungeons & Dragons 5e na fizycznej planszy 20x30 z podświetleniem LED i wykrywaniem pól.

Poprzednia aplikacja używała mechanik zbliżonych do Pathfindera i z czasem zbyt
mocno połączyła logikę gry, UI, scenariusze i hardware. Została usunięta z
aktywnego drzewa po usamodzielnieniu przebudowy; w razie potrzeby można ją
odtworzyć z historii Git. Zachowaliśmy wyłącznie niskopoziomową komunikację z
planszą/LED w `board/`.

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

Gracze wpisują wyłącznie rzuty swoich bohaterów. Za przeciwników aplikacja
zawsze rzuca automatycznie — również w testach spornych, takich jak Uderzenie
tarczą. Wynik przeciwnika i jego modyfikatory pokazujemy w podsumowaniu;
nie prosimy gracza o rzut ani wpisanie wyniku za przeciwnika.

Rzuty Uderzenia tarczą wieloma k6 używają wspólnego widoku kości: osobna
ikona i wynik każdej kości, poprawka oraz podsumowanie sumy. Modyfikator
Siły jest doliczany tylko raz. Odświeżenie strony i ręczne ponowienie skanu
kończą poprzednie oczekiwanie planszy przed uruchomieniem nowego odczytu.

## Eksploracja z maną — 2026-09-14

Arena ma dla każdej z siedmiu postaci osobne wejścia „Porozmawiaj z NPC”,
„Interakcja z obiektem” i „Pułapka w walce”. Nowy silnik do 21 używa cech
przypisanych 14 metodom; Zastraszanie Brakki jest na KON. Przekroczenie
powoduje utrudnienie (2k20, niższy wynik) bez premii za karty. Trzy jawne
przeszkody i profile oraz osobiste pasywy działają również w praktycznych
lekcjach. Stan i zaliczenia są zapisywane; podstawy doboru zalicza się wspólnie,
a istniejący postęp walki zachowuje się przy zmianie modułu. Pułapki używają
zwykłych testów i akcji w combacie. Wszystkie karty i pomoc zostały odświeżone;
pakiet areny i kart ma teraz 67 stron. Szczegóły: `docs/EXPLORATION_MANA_IMPLEMENTATION.md`.

W lekcjach eksploracji wybory metod, kolorów, pasu, doboru i przerzutu idą
przez runy na planszy. UI pokazuje ich istniejące symbole i nazwy, a jeden
katalog wyborów steruje również maską skanu i LED. Niedostępne opcje nie
przesuwają przypisań. Rzuty eksploracji i pułapek używają wspólnego widoku:
fokus jednej kości, −/+ ustawia wynik, ✓ przechodzi dalej, końcowe podsumowanie
pozwala poprawić kość przez ↩ lub zatwierdzić cały test przez ✓. Przy dwóch k20
z utrudnieniem premia jest dodawana raz do niższego wyniku. Poza widokiem rzutu
✓ potwierdza setup, zachowane stosy i następne ćwiczenie; ↩ wraca do wyboru postaci.

Cztery warunki rozmów są wdrożone w osobnych lekcjach wszystkich postaci:
porozumienie 15–17, drażliwy kolor, dodatkowy cel za dwie niebieskie oraz karta
za 1 w zamian za zobowiązanie. Jedna zasada na scenę, obie decyzje legalne.
Klucz/Gwiazda obsługują warunki; wynik otwiera odpowiednie opcje Nessy.
Zapis v2 migruje stare próby bez narzucania nowych warunków. Odrębna ściąga
w kartach i pomocy; balans pozostaje do ogrania przy stole.

## Wspólny rynek many 0.3

Arena domyślnie prowadzi liniowy walkthrough (`walkthrough`): 99 ćwiczeń
siedmiu bohaterów, obejmujących 67 zdolności i osobne warianty każdego rodzaju
podbicia. Każdy krok zaczyna osobne okno narracji Nessy i mechaniki; ✓ przechodzi
do ustawiania, a po setupie krótkie polecenie otwiera wymaganą zdolność.
Setup pokazuje i ustawia fokus na bieżącym elemencie, bez opisu całego kursu
nad nim. Teren ustawiamy raz po wejściu; ukończone przygotowanie zachowuje
się przy ponowieniu pierwszej lekcji i zmianie bohatera. Opis lekcji podczas
gry jest rozwijaną pomocą i znika z tła okna płatności/wyboru celów.
Mana jest zapewniona, rozstrzygnięcia
korzystają z normalnego silnika. Pchnięcie i ukrycie wymagają osiągnięcia efektu;
niepowodzenie pozwala odtworzyć próbę. Reakcje mają jawnie przygotowany atak.
Teren zostaje; figurkę Nessy zastępuje narracja. Po ćwiczeniach: normalny pojedynek
1 na 1 z kukłą 30 PW, KP 13, +3, 1k6 obrażeń. ✓ po wyniku wraca do wyboru
postaci, zaliczenie całego kursu wymaga zwycięstwa. Postęp i objaśnienia są
zapisywane. Dawne tryby pozostają do odczytu wcześniejszych zapisów i testów,
bez wyboru w nowym panelu. Opis: `docs/RECRUITMENT_ARENA.md`.

Nowe gry siedmioma bohaterami używają 25 kart (po pięć każdego koloru), wspólnego rynku pięciu kart i licznika talii/rynku/odrzuconych. Nie ma prywatnych rezerw. Koszt bazowy, podbicia i skaza mieszczą się łącznie w pięciu kartach. Najpierw deklaracja i fizyczna płatność, następnie rzuty i efekt; Odzysk może przywrócić własny koszt. Rynek uzupełniamy dopiero na końcu tury bohatera, po efektach końca tury.

Odświeżenie zbiera wszystkie 25 kart, również rynek. Potwierdzenie nowego rynku kończy efekty O; efekty T kończą się na początku następnej tury źródła. Po wyczerpaniu talii tura bez wydanej many wymusza odrzucenie jednej karty rynku po uzupełnieniu. Pusta talia i rynek otwierają odświeżenie po zakończeniu bieżącego działania.

Katalog: `rules/shared_mana_catalog.py`, 66 zdolności i osobny Święty symbol Dagny. Dagna płaci dodatkową dowolną manę za ofensywę przy sojuszniku poniżej połowy PW; Mira w ukryciu ma utrudnienie rzutów obronnych i testów reakcji. Dolne runy na arenie podświetlają i wybierają dostępne akcje z bieżącego menu; podczas płatności i rzutów są zablokowane. Narożne −, +, ✓ i ↩ zachowują pozycje. Aktualny zbiorczy PDF areny ma 67 stron. Mechanika kafelków dla Głodnych Cieni pozostaje odłożona. Przebieg wdrożenia, pliki i walidacja: [wspólna mana 0.3](docs/SHARED_MANA_V03_IMPLEMENTATION.md).

Podczas płatności podbicia wybiera się osobnymi wariantami run: każda opcja
pokazuje dokładną liczbę symboli many i efekt. Ponowne wybranie wariantu go
wyłącza; inne kolory można łączyć w granicach kosztu. ✓ potwierdza odłożenie
kart, ↩ wraca bez płatności. Runy mają to znaczenie tylko w oknie płatności.
Opis: `docs/MANA_BOOST_RUNES.md`.

Okna wyboru celów wspólnej many używają pól figurek: legalne cele świecą
przygaszonym turkusem, zaznaczone jaśniej. Ponowne naciśnięcie odznacza cel;
✓ zatwierdza dopiero legalny wybór. Białe podbicia Osłony tarczą pozwalają
wybrać kilku różnych sąsiadujących sojuszników i nadać im po 5 tymczasowych
PW jednym zatwierdzeniem. Bazowa aura +2 KP nadal działa automatycznie.
Po zapłacie ↩ czyści wybór, zachowując opłaconą akcję; przed zapłatą anuluje
deklarację. Rozwijaną listę zastępuje instrukcja planszowa i awaryjne przyciski
postaci. Cele Mowy dowódcy, Opiekuńczego gestu, Inspiracji i Rozkazu kontrataku
korzystają z tego samego wejścia; ich limity, zasięgi i rzuty pozostają zgodne
z silnikiem zasad.

Osłona towarzysza zachowuje przejęty cel także poza zwykłym zasięgiem kukły;
nie wybiera ponownie pomocnika. Osłania tylko pojedynczy atak, z KP Garrana
i jego obrażeniami. Lekcja przygotowuje trafienie (6 obrażeń); normalna walka
nadal używa losowych rzutów. Plan przeciwnika zachowuje opłaconą manę i reakcję.
Osłona tarczą i Żelazny bastion pokazują LED-ami promień i rzeczywistych
odbiorców. Podgląd nie nakłada efektu ani nie dodaje pól zasięgu do maski wejścia.
Rozkaz: Kontratak prowadzi kolejno 1/2 Garrana i 2/2 sojusznika: automatyczny
podgląd ruchu do 10 ft → ✓ → cele ataku wyposażoną bronią → wybór i ✓ → rzuty.
✓ bez wybranego pola pomija ruch; nie wybiera się kolejnych run akcji. Brak
legalnych celów wymaga ✓ i pomija atak; w samouczku oznacza ponowienie próby.
Działa także dla pomocnika treningowego bez własnego profilu many.

Wspólny podgląd obejmuje również Błogosławieństwo i Aurę Boskiej Opieki Dagny
oraz Hymn zwycięstwa Loriana. Przed zapłatą pokazuje planowany promień,
w tym zmianę 5 → 10 ft po wybraniu niebieskiego podbicia; po użyciu korzysta
wyłącznie z aktywnych źródeł. Sojusznicy z premią świecą turkusowo, wrogowie
w Boskiej Opiece złoto. Zmiana pozycji i utrata koncentracji aktualizują
zasięg/odbiorców także poza turą źródła. Podgląd ruchu i wybór celu mają
pierwszeństwo przed aurami w tle. Lekcja Hymnu ustawia pobliskiego pomocnika.

Aury różnych zdolności działają równocześnie, także od jednej postaci:
Żelazny bastion daje premię KP równą modyfikatorowi Siły Garrana (+4 przy
Sile 18), ustaloną przy użyciu. Z Osłoną tarczą sojusznik otrzymuje wtedy +6 KP. Kopie tej
samej aury od różnych źródeł nie sumują się; każdy odbiorca korzysta z jednego
najsilniejszego wariantu w swoim zasięgu. Dla Boskiej Opieki porównujemy karę
do ataku, a przy remisie redukcję obrażeń; wybieramy cały wariant, bez łączenia
jego części z innym źródłem. Promień określa zasięg, nie siłę efektu.
Błogosławieństwo wybiera największą kość, a Łaska uzdrowienia największą
średnią premię leczenia i zużywa jedno użycie wybranego źródła. Hymny dają
łącznie najwyżej jedną dodatkową akcję dodatkową. Słabsze źródła pozostają
aktywne i przejmują działanie po utracie zasięgu lub wygaśnięciu silniejszego.
Nadal obowiązuje jedna koncentracja na postać; rzucenie drugiego efektu
koncentracyjnego kończy pierwszy.

## Plansza I Hardware

Menu główne i jego podstrony korzystają z tych samych run i jednego połączenia
USB/WLED co gra. Kafelki pokazują odpowiadające im symbole; naciśnięcie od razu
wybiera opcję, a ↩ wraca. Wybór bohatera walkthrough używa siedmiu kolejnych
run (sloty 6–12) w kolejności Garran, Brakka, Mira, Dagna, Lorian, Nimra, Erynd.
✓ nie jest wymagane przy nawigacji; potwierdzenia przygotowania planszy,
płatności i rzutów zachowują dotychczasowe znaczenie. Przy zmianie strony
token dokumentu i anulowanie wejścia odcinają spóźnione naciśnięcia.

Ustalenie na przyszłość (2026-09-08): plansze do walk składamy z pojedynczych,
fizycznie rozkładanych kafelków terenu, zgodnie z kierunkiem sprawdzanym na
arenie. Każdy kafelek ma opisane właściwości mechaniczne: premie, kary lub
ograniczenia dotyczące odpowiednich działań. Przygotujemy gotowe kafelki do
druku i ponownego użycia, np. filar oraz osłonę +2, z czytelnym oznaczeniem
właściwości. Szczegółowe efekty pozostałych kafelków ustalimy przy realizacji.

Ten sam sposób budowania mapy i rozstawiania elementów należy zastosować przy
przyszłej aktualizacji istniejącej walki z Głodnymi Cieniami. Temat jest
odłożony do zakończenia dopracowywania bohaterów na arenie; na tym etapie
zapisujemy kierunek, bez przebudowy scenariusza, mechanik i wydruków.

Plansza:

- fizyczna siatka 20 kolumn x 30 rzędów,
- współrzędne zapisujemy jako `(col, row)`,
- jedno pole reprezentuje 5 feet, chyba że późniejsza decyzja projektowa ustali inaczej,
- Ruch po skosie: pierwsze pole diagonalne kosztuje 5 feet, kolejne 10 feets, potem znowu 5 feet i tak dalej zgodnie z regola 5-10-5
- niskopoziomowa komunikacja odbywa się przez istniejące `board.Connection`,
- logika gry nie może bezpośrednio importować `board`.

Wejście z planszy:

- USB wyłącznie `board_scan_usb_v2`, firmware `board_scan_protocol_v2_2`;
  usunięta zgodność v1 (2026-09-10),
- ESP skanuje tylko maskę legalnych pól, bez sygnału naciśnięcia złego pola,
- jeden czytnik USB w `board/serial_v2.py`, kolejka z ACK/deduplikacją,
  heartbeat niezależny od gracza oraz tryb stream dla +/− tej samej kości,
- kontrakt i ograniczenia: `docs/BOARD_SCAN_PROTOCOL_V2.md`,
- alternatywnie backend symulatora z istniejącego pakietu `board`.

Wyjście na planszę:

- LED-y sterowane przez WLED przez istniejącą warstwę `board`,
- wysyłanie i ponawianie LED działa w tle; odczyt przycisków USB nie czeka
  na potwierdzenie HTTP WLED. Maska i kontekst USB nadal ograniczają wejście
  do bieżącego wyboru; stan LED osobno raportuje oczekiwanie i błędy,
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

Aktualny master milestone implementuje legalny zakres postaci SRD 5.1 do
poziomu 3: wszystkie klasy/species z tego zakresu, ich wykonywalne granty,
level-up oraz czary poziomów 0–2. Featy, poziomy 4+, pełny bestiariusz i pełna
lista warunków pozostają poza tym zakresem.

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
- Zaczynamy od czystego rdzenia domenowego i zasad, zanim odbudujemy UI.
- Nie przywracamy mechanik Pathfindera sprzecznych z podejściem D&D 5e.
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
- Bazowy otwarty source pack zasad 2014 to SRD 5.1 na CC BY 4.0; content
  projektowy i jego brak zadeklarowanej licencji są śledzone oddzielnie w
  `content/source_packs.json` oraz `docs/CONTENT_VERSIONING_AND_SOURCES.md`.
- Snapshot pojedynczego scenariusza ma wersjonowany format v24 opisany w `docs/SAVE_FORMAT.md`;
  stan kampanii oraz migracje przyszłych wersji pozostają do zaprojektowania w M9.
- Bazową wersją zasad dla pierwszego pełnego wydania jest D&D 5e 2014. Odstępstwa wymagane przez fizyczną planszę albo tempo gry zapisujemy jawnie w `GAME_DESIGN.md` i `docs/RULES_DECISIONS.md`.


## Physical mana profile (2026-09-05)

New-game party selection explicitly applies `physical_mana_v02` to the seven
curated heroes. Cards, market, mana payments and physical passive/flaw markers
remain outside the application. Combat tracks only declared actions/attack
sequences, effects and reported waves; existing saves are not silently migrated.
The current economy is documented in `docs/PHYSICAL_MANA_DESIGN_V0_2.md`.
Player help and printable ability sets are served at `/rules/physical-mana`.
A temporary spiritual-weapon activation returns to the owner's saved turn state;
it does not grant the weapon an unpaid recurring initiative turn.

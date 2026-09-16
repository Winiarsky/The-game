# Kontekst Projektu

## Misja 0 — narracyjny samouczek drużyny

Docelowe wejście: wybór drużyny 3–6 → intro wybranych bohaterów → odprawa
Nessy i negocjacja mikstury → wóz → walka o dzwon → krótka eksploracja
i decyzja o długu wieśniaków → powrót i podsumowanie. Narrator spina sceny;
dotychczasowe pojedyncze ćwiczenia pozostają jako osobny Poligon.
Wszystkie teksty, profile i media misji mają być edytowalną lokalną paczką.
Pierwsza grywalna wersja jest wdrożona. [Instrukcja paczki](content/scenarios/misja_0_dzwon/README.md)
opisuje edycję, checkpointy, realne nagrody, mapy do druku i zapis pełnej drużyny.
Przepływ korzysta ze wspólnych silników walki, konfrontacji i fizycznych kości.

## Skalowanie scenariuszy: 3–6 graczy

Przy budowie scenariuszy stosujemy [strategię skalowania](docs/PARTY_SCALING.md).
Baza: cztery osoby; wspólne karty bohaterów, talia 10 kart na osobę,
warianty składu i działań wrogów oraz proporcjonalny opór eksploracji.
Liczby są do ogrania. Misja 0 obsługuje 3–6 osób; starszy scenariusz nadal 1–5.
`evaluate_mission_zero.py` sprawdza wszystkie składy 3–6 w konfrontacjach;
pełna taktyka walki wymaga osobnego ogrania.

## Umiejętności ukryte w prezentacji

Karty i aktualne UI nie pokazują dawnej listy umiejętności ani nieczynnych
opisów ekspertyzy. Test opisuje działanie oraz cechę: `k20 + cecha + premia
z naładowania + inne bonusy`. Dane umiejętności zachowujemy na przyszłość;
ukrywanie, szukanie, chwyt i inne działania pozostają dostępne według swoich
zasad. Ta zmiana nie usuwa cech ani nie zmienia obliczeń testów.


## Naładowanie zamiast biegłości — aktualne testy

Bohaterowie z profilem osobistej many nie dodają biegłości ani ekspertyzy do
ataków, obron, umiejętności i narzędzi. Test: `k20 + cecha + naładowanie + inne
premie`. Progi punktów 0/6/12/21 dają +0/+2/+4/+6. W walce używasz aktualnej
premii swojej puli; w konfrontacji wybierasz dostępny próg wraz z jego kosztem,
licząc premię tylko raz. Bez puli i po drainie premia wynosi zero.
Naładowanie nie zwiększa obrażeń ani wpływu. ST zdolności pozostają wartościami
określonymi przez zdolność; ta zmiana dotyczy składników rzutów, nie ST.
Garran: miecz `k20 +4 Siła + naładowanie + inne premie`, obrażenia `1k8 +4`
i pasywy kolorów. Biegłości jako uprawnienia do sprzętu nie zmieniają się.
Samouczki ładowania i zwykłego ataku, panel postaci, kości oraz wydruki używają
tej reguły. Starsze profile zapisów zachowują dotychczasowe zasady.


## Aktualna eksploracja: konfrontacje drużynowe

NPC i obiekty w Arenie używają wspólnego oporu, tur całej drużyny i trwałych
osobistych pul many. Dobór z oferty dwóch kart do 21+, potem test albo pomoc.
Progi 0/6/12/21: premia +0/+2/+4/+6 i spalanie 1/1/2/3 po efekcie. Podatność
zmienia ST i kość wpływu. Reakcje uszczuplają talię/pule lub odnawiają opór;
drain kończy konfrontację. Brak kary za przekroczenie i automatycznego sukcesu
przy 21. Nowy kurs: 12 przypadków na bohatera (84), wybór składu 1–5 osób,
jedna figurka, runy, dwa osobne rzuty przez fokus i podsumowanie.
Opis: [Konfrontacje drużynowe](docs/PARTY_CONFRONTATIONS.md).
Poniższe opisy blackjacka i 127 lekcji są historyczne; stare zapisy mają
oddzielny silnik zgodności. Pułapki w walce pozostają zwykłymi testami.

## Samouczek: kurs lub pojedynczy przypadek

Menu: bohater → Walka / Eksploracja → Po kolei / Wybierz ćwiczenie.
Wszystkie lekcje walki i eksploracji, podbicia oraz pojedynek można uruchomić
osobno przez runy; −/+ zmienia stronę. Pułapka jest przypadkiem w dziale walki.
Kurs eksploracji ma własny zapis kolejności, niezależny od pojedynczych prób.
Powtarzanie przypadków zachowuje postęp kursu. Pasek ekranowy pozwala odtworzyć
próbę lub wrócić do wyboru również w trakcie rzutu/płatności. Szczegóły:
[Struktura samouczka](docs/RECRUITMENT_ARENA.md).

## Trwały ładunek many 2.0 — aktualizacja

Aktualny katalog many ma wersję 2: osobisty ładunek pozostaje po zdolności;
punkty 6/12/21 odblokowują akcje, pięć kolorów daje własne pasywy każdego
bohatera. Przy 21+ pkt dobór ustaje do draina. Zdolność bazowo spala 1 kartę
z wierzchu, każde podbicie +2; darmowe akcje i bazowy odzysk Loriana nie spalają.
Co rundę 1 karta wygasa bez możliwości odzysku. Drain zbiera wszystkie strefy,
kończy premie kolorów i efekty O, zachowuje leczenie i zużycie akcji.
Talia: po max(5, 2 × bohaterowie) każdego koloru. Samouczek: 148 lekcji.
Ta aktualizacja zastępuje poniższe historyczne zasady wydawania całej puli
i O do końca walki. Tabele 35 pasywów, wyjątki, UI, migracja i raport:
[Ładowanie many 2.0](docs/MANA_CHARGE_V02.md).


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

## Osobiste pule many 1.0

Aktualny profil (2026-09-14): osobiste pule `pooled_mana_v01`.
Nowe walki: po max(5, liczba bohaterów + 1) kart każdego koloru, dwie odkryte
karty, obowiązkowy wybór jednej na początku własnej tury. Płatna zdolność
zużywa całą pulę i oddaje ją na spód BEZ tasowania. Drain zbiera także spalone
oraz uwięzione; każda walka zaczyna z pełną przetasowaną talią i pustymi pulami.
O = koniec walki, nie drain. Katalog progów/pasywów/skaz: `content/balance/pooled_mana/catalog.json`.
Wdrożenie i raporty 8960 prób: [pule many 1.0](docs/POOLED_MANA_IMPLEMENTATION.md).
Ewaluator mierzy ekonomię kart; pełne walki i czas graczy wymagają odrębnej oceny.

Arena domyślnie prowadzi liniowy walkthrough (`walkthrough`): 134 ćwiczenia
siedmiu bohaterów: po pięć podstaw nowego obiegu oraz wcześniejsze 99 lekcji
67 zdolności i wariantów podbić. Każdy krok zaczyna osobne okno narracji Nessy i mechaniki; ✓ przechodzi
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

Historyczny rynek `shared_mana_v03` jest zachowany do odczytu poprzednich
zapisów; jego dawne zasady i weryfikacja: [opis 0.3](docs/SHARED_MANA_V03_IMPLEMENTATION.md).
Nowe karty, aplikacja i samouczek używają osobistych pul. PDF areny: 67 stron.

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

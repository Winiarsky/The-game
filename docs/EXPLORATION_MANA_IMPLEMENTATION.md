# Eksploracja z maną — wdrożenie 2026-09-14

## Jak sprawdzić

Menu główne → Arena. Pod ćwiczeniami walki jest sekcja **Rozmowy i obiekty**.
Każdy z siedmiu bohaterów ma przyciski **Porozmawiaj z NPC**, **Interakcja
z obiektem**, **Pułapka w walce** oraz wybór dodatkowych lekcji eksploracji.

Nessa prowadzi przez objaśnienie, ustawienie figurek i przygotowanie fizycznych
kart. ✓ potwierdza kroki setupu. Metodę, kolor karty, pas, dalszy dobór oraz
przerzut wybieramy podświetloną runą na planszy. Ekran pokazuje symbol i nazwę
runy przy każdej dostępnej opcji; przyciski ekranowe pozostają alternatywą.
Rzuty używają tego samego widoku co walka: fokus na jednej kości, ustawienie
naturalnego wyniku przyciskami − / + na planszy, ✓ do kolejnej kości, następnie
podsumowanie. ↩ pozwala poprawić kość, a końcowe ✓ rozstrzyga test. Dotyczy
NPC, obiektów oraz wykrywania i dezaktywacji pułapek. Początkowe 10 na k20 jest
ustawieniem licznika; gracze wprowadzają faktyczny wynik fizycznego rzutu.
Przy utrudnieniu podsumowanie pokazuje obie kości, wybiera niższą i dolicza
cechę, biegłość oraz pasyw tylko raz. Nie sumuje dwóch k20 ani ich premii.

Runy metod są stałe dla bohaterów w obu rodzajach interakcji: Garran —
Rozwidlenie, Brakka — Wieża, Mira — Klepsydra, Dagna — Trójząb, Lorian —
Brama, Nimra — Romb, Erynd — Hak. Brak bohatera nie przesuwa pozostałych run.
Kolory: czerwona — Błysk, biała — Oko, zielona — Schody, czarna — Korona,
niebieska — Węzeł. Grot oznacza dalszy dobór, Kotwica — pas, Spirala — przerzut,
Kielich — przyjęcie porażki, Most — pustą talię, Fala — powtórzenie lekcji.
✓ obsługuje potwierdzenie, wznowienie stosów, rzut i następne ćwiczenie;
↩ poza widokiem rzutu wraca do wyboru postaci. W widoku rzutu służy do
poprawiania kości. Znaczenie wynika z bieżącego kroku.

Tylko legalne wybory są aktywne i podświetlone. Po odkryciu oferty nie świeci
runa pasu, a przygotowana lekcja udostępnia wymagany kolor. Runa metody
rozpoczyna próbę także wtedy, gdy dostępna jest tylko jedna metoda; ✓ ani
pole NPC nie zastępują tego wyboru. Mapowanie UI/LED/skanu pochodzi wspólnie
z `ui/exploration_mana_board.py` i nie wymaga zmiany wydrukowanego panelu.

Pierwsze sceny to Irena, która ma złożyć świadectwo Nessie, oraz zablokowana
skrzynia lekarstw. Każda ma siedem autorskich metod; wybór metody wybiera
bohatera. Lekcja własnej postaci udostępnia jej metodę. Samodzielne ćwiczenia
przygotowują trzy rzeczywiście obecne postacie i trzy dostępne rozwiązania.
Sukces i porażka zapisują różne wyniki sceny; porażka otwiera własny raport
albo drogę przez warsztat. Próbę treningową można jawnie powtórzyć.

Sceny kursu są ćwiczebne: ich wyniki i przedmioty nie tworzą nagród w kampanii.
Silnik reguł i katalog metod są niezależne od areny i używane przez te same
przepływy rozstrzygania. Dotychczasowe scenariusze pozostają czytelne przez
istniejące loadery; nie wykonywano destrukcyjnej konwersji starych pułapek.

## Cztery warunki rozmów — wersja 2

Arena → Rozmowy i obiekty → wybrana postać → **Cztery warunki rozmów**.
Dostępne są cztery krótkie lekcje oraz odpowiadające im ćwiczenia samodzielne
w wyborze lekcji eksploracji. Obsługują wszystkie siedem postaci. Lekcje
wprowadzające zaliczają się wspólnie; nie trzeba powtarzać ich siedem razy.

- **Coś pewnego czy szansa na więcej?** Przygotowana talia prowadzi do 16.
  Klucz przyjmuje podpisany dokument bez rzutu; Gwiazda odrzuca ofertę i wraca
  do pas/dobór. Odrzucona oferta nie wraca. Gracz sam wybiera obie drogi.
- **Nazwiska mają cenę.** Czerwona karta daje przy sukcesie dodatkowe nazwiska,
  ale zamyka prywatną pomoc Ireny. Samo odkrycie/odrzucenie nie uruchamia ceny.
  Dokładne 21 i sukces po przerzucie zachowują zapowiedzianą cenę.
- **Jeszcze jedna niebieska.** Dwie wybrane niebieskie odblokowują przy sukcesie
  informację o pomysłodawcy. Postęp jest widoczny. Nagroda jest jednorazowa;
  można ją uzyskać także po wygranym teście z utrudnieniem.
- **Ile kosztuje pewność?** Podczas oglądania oferty Klucz pozwala wybrać kartę
  za 1. Gwiazda rezygnuje z ustępstwa przed wyborem. Dopiero wybór koloru
  zapisuje zobowiązanie zaniesienia listu, także przy późniejszej porażce.
  Raz na próbę; nie cofa wcześniej wybranej karty ani przekroczenia.

Jedna nowa zasada na rozmowę. Lekcje wprowadzające używają jawnie przygotowanego
profilu balanced, bez innych przeszkód; praktyka zachowuje różne profile metod.
Każda praktyka ustawia trzy rzeczywiste postacie. Zaliczenie wymaga zakończenia
próby, a nie wybrania pokusy czy wygrania k20; lekcja porozumienia wymaga też
odpowiedzi na ofertę. Rozstrzygnięcie nadal korzysta z właściwych cech i pasywów.

Po wyniku **Co dalej u Nessy?** udostępnia odpowiedzi wynikające z uzyskanej
informacji: dalsze pytanie do Ireny, nazwiska świadków, sprawdzenie pomysłodawcy,
przygotowanie pytań do dokumentu albo weryfikację własnego raportu. Wybór runy
zapisuje odpowiednią flagę i komunikat; ponowienie nie dubluje skutków.
Przyjęte zobowiązanie otwiera również odnogę z dostarczeniem listu. W Arenie
jest to krótka symulowana odnoga ćwiczenia, nie podróż w docelowej kampanii.

Specyfikacja sceny i jej obiecane wyniki są zamrożone przy uruchomieniu lekcji,
wartości kart w próbie, a ST w stanie lekcji. Próba oraz magazyn kursu mają
wersję 2. Stare zapisy v1 dostają warunek none i zachowują swoje wybory,
rezultaty i zaliczenia. Podczas zapisanej oferty można przyjąć dokument bez
odtwarzania talii; odrzucenie wymaga potwierdzenia zachowanych stosów.
Uzbrojone ustępstwo, zobowiązanie, postęp kolorów i wybrane odpowiedzi Nessy
przetrwają zapis. Zobowiązanie zapisuje się raz przy karcie, wynik raz w finale.

Główne pliki rozszerzenia: `rules/exploration_mana_conditions.py`,
`rules/exploration_mana.py`, `application/exploration_mana_outcomes.py`,
`scenarios/exploration_mana.py`, `content/tutorials/exploration_mana.json`,
`ui/exploration_mana.py`, `ui/exploration_mana_board.py` i skrypt panelu.
Pomoc oraz wszystkie formaty wydruków mają osobną ściągę czterech warunków.

`check_social_mana_balance.py --samples 100` porównał 5600 prób fizycznej talii
(seed 20260914), cztery warunki i dwie proste strategie dla siedmiu postaci.
Pogoń za niebieskimi zwiększyła częstość dodatkowej informacji z 27,4% do 50,3%,
przy spadku sukcesów z 85,7% do 69,4%. Przysługa używana wyłącznie do ratowania
ryzykownej oferty wystąpiła w 16/700 prób; nie jest to analiza optymalnej gry.
Symulacja raportuje osobno porozumienia, informacje, cenę relacji i zobowiązania,
bez przypisywania im arbitralnej wartości. Balans i cena dodatkowej drogi są
celowo pozostawione do próby przy stole.

## Zasady obowiązujące

- 25 fizycznych kart, pięć każdego koloru, bez rynku eksploracyjnego.
- Dobór dwóch kart; zachowaj jedną. Przy dwóch identycznych kolorach możesz
  dociągać do pierwszej innej barwy; wszystkie niewybrane odkryte odrzucasz.
- Pas albo dalszy dobór przed odkryciem oferty. Rozpoczęcie metody zobowiązuje
  do pierwszego doboru i dopiero wtedy odsłania pełną tabelę tej metody.
- 1–10: +0; 11–14: +1; 15–17: +2; 18–19: +4; 20: +6; dokładnie 21: sukces
  bez rzutu. Znany koszt sposobu działania pozostaje również przy 21.
- **Przekroczenie daje utrudnienie, bez premii karcianej: 2k20, niższy wynik.**
  Nie ma dodatkowej kary −3. Nadal dodajemy cechę, należną biegłość i pasyw.
- Jedna jawna przeszkoda: +2 za powtórzony kolor, +2 do następnego po czerwonej
  albo limit czterech wyborów ze zwykłym pasem. Wartości na ekranie uwzględniają
  aktualną dopłatę. Limit liczy wybrane karty, nie odrzucone duplikaty.
- Bez tasowania w środku próby. Ostatnia karta może być wybrana; zgłoszony
  brak kart wymusza pas. Aplikacja nie udaje znajomości fizycznych odrzuconych.

| Bohater | NPC | Obiekt |
| --- | --- | --- |
| Garran | Autorytet, SIŁ | Zabezpieczenie, KON |
| Brakka | Zastraszanie, KON | Forsowanie, SIŁ |
| Mira | Blef, INT | Manipulacja, ZRĘ |
| Dagna | Empatia, MDR | Oczyszczenie, MDR |
| Lorian | Inspiracja, CHA | Pomysłowość, INT |
| Nimra | Argumentacja, INT | Analiza, INT |
| Erynd | Dociekliwość, MDR | Rozpoznanie, MDR |

KON Zastraszania zastępuje CHA w tym konkretnym teście; nie dodajemy gotowej
sumy Zastraszania ani premii rzutu obronnego. Biegłość/ekspertyza liczy się
jednokrotnie. Obycie Loriana daje +2 do jego testu CHA, a Improwizacja pozwala
przerzucić nieudany test przed konsekwencjami, również oba k20 po przekroczeniu.
Erynd ma Praktykę terenową: +2 do własnego końcowego testu obiektu. Premie
nie obejmują innych bohaterów ani puli kart, a Praktyka nie obejmuje pułapek.

## Kurs i zapis

Sześć podstawowych lekcji (dobór/duplikat/pas, 21, przekroczenie, trzy przeszkody)
zalicza się wspólnie. Każdy bohater ma własną rozmowę, obiekt i dwa samodzielne
ćwiczenia; Lorian dodatkową lekcję Improwizacji. Wszystkie lekcje można wybrać
bez przechodzenia całego kursu walki. Widok rozdziela zaliczenia combatu,
eksploracji i pułapek.

Lekcje z przygotowaną talią pokazują jej fizyczną kolejność i wymagany wybór.
Właściwe efekty zawsze wylicza normalny silnik. Ćwiczenie przekroczenia zalicza
wykonanie testu z utrudnieniem, także przy porażce. Lekcja przerzutu jawnie
przygotowuje wysoki ST; nie fałszuje naturalnych wyników kości.

Wersjonowany stan próby jest zapisany w istniejących flagach snapshotu: metoda,
profil, faza, wybrane kolory/wartości, suma, oczekiwany rzut, przerzut i wynik.
Każde polecenie ma rewizję; nieaktualne potwierdzenie nie wybiera drugiej karty
ani nie powtarza skutku. Zaliczenia mają stabilne id; osobny moduł nie przesuwa
indeksów dawnych lekcji walki. Przechodzenie między modułami zachowuje postęp.

Po wczytaniu aktywnego doboru aplikacja wymaga potwierdzenia zachowanych stosów.
Pomieszane karty oznaczają jawne powtórzenie lekcji, a nie pozorne odtworzenie
nieznanej kolejności. W fazie rzutu zapis zachowuje oczekiwaną liczbę k20.
Przejście do ćwiczenia walki przygotowuje jego własny, normalny rynek.

## Pułapka bojowa

Szkoleniowa pułapka z atramentem stoi na polu (8,18). Wykrywanie korzysta
z MDR i Percepcji, dezaktywacja ze ZRĘ i należnej biegłości narzędziowej.
Nessa zapewnia narzędzia dla każdej postaci. Zwykły zasięg szukania to 10 ft,
Mira zachowuje 45 ft; dezaktywacja wymaga sąsiedztwa. Każdy test zużywa akcję.
Pomiędzy testami normalnie przechodzą tury. Nie ma minigry ani wydatku many
za zwykłą obsługę pułapki.

Nieudane wykrycie zostawia pułapkę ukrytą. Udana dezaktywacja ją rozbraja;
nieudana uruchamia atrament i oznacza bohatera. Mechanizm jest zużyty;
w tej lekcji nie zadaje obrażeń. Zaliczenie wymaga rozstrzygnięcia dezaktywacji.
Oczekiwany rzut jest zapisywany i blokuje rozpoczęcie innej akcji.

## Katalogi, kod i wydruki

- `rules/exploration_mana_catalog.py`: 14 metod, cechy, profile, przeszkody,
  wspólna instrukcja. `rules/exploration_mana.py`: czysty stan i przejścia.
- `application/exploration_mana_flow.py`: modyfikatory aktora i fizyczne k20.
- `scenarios/exploration_mana.py` i `content/tutorials/exploration_mana.json`:
  walidowany content scen i lekcji, poprawność przygotowanych ofert.
- `ui/exploration_mana.py`, skrypt JS i integracja istniejącego panelu areny:
  przebieg lekcji, trwałe skutki, snapshot, input i LED setupu.
- `combat/simple_traps.py` i `ui/simple_traps.py`: zwykłe testy pułapki,
  rzeczywista akcja w combacie i osobne zaliczenie.
- Generator kart korzysta z tego samego katalogu i składników testu co runtime.
  Wszystkie cztery formaty i siedem postaci mają dodatkową stronę eksploracji;
  pomoc `/rules/physical-mana` również pokazuje metody i modyfikatory.

Aktualne arkusze kolorowe/minimalistyczne mają po **49 stron** zbiorczo.
Karty kolorowe/BW mają po **56 stron**. Pakiet areny i kart ma **67 stron**:
jedenaście stron mapy/instrukcji/znaczników oraz 56 stron siedmiu postaci.
Manifesty, kopie pod dawnymi linkami i referencja archetypów są odświeżone.
Obejrzano stronę pasywów i eksploracji Erynda; brak obciętych opisów.

## Sprawdzenie matematyki

`PYTHONPATH=src python scripts/check_exploration_mana_balance.py --samples 200`
porównuje 672 kombinacje metody, profilu, przeszkody i progu pasowania, razem
**134 400 prób**. Seed: 20260914. Faktyczna talia 25 kart bez zwracania kart,
duplikaty, koniec talii, rzeczywiste modyfikatory 14 metod oraz przerzut Loriana.
Polityka preferuje dokładne 21, następnie próg pasowania 17/18/19/20; nie zna
przyszłej kolejności. Jest to porównanie prostych strategii, nie optymalna gra.

Średnia skuteczność bez przeszkód: profil małych kroków 79,9%, pośredni 79,9%,
dużych kroków 77,2%. Przy limicie czterech wyborów: odpowiednio 71,6%, 79,6%,
77,6%. Profile nie są więc globalnymi poziomami „łatwy/trudny”; content dobiera
profil i przeszkodę razem. Balans pozostaje do oceny podczas gry użytkownika.

## Weryfikacja i dalsza próba

Po wdrożeniu czterech warunków przeszło **160 ukierunkowanych testów**:
reguły warunków 9, runtime warunków 59 (wszystkie postacie i obie decyzje),
pełny Chrome nowych lekcji 2, reguły bazowe 23, runtime bazowy 20,
plansza 20, karty 25 oraz pełna strona z obsługą kości 2. Uruchamiane osobno
przez bezpieczny wrapper z limitem 60 sekund. `git diff --check` bez błędów.
Chrome przeszedł także wejście z menu „Cztery warunki rozmów” na 390/1100 px.
Wszystkie 28 zestawów PDF odświeżono; zbiorcze pliki mają 49/49/56/56 stron,
a pakiet areny 67. Obejrzano nową stronę ściągi Garrana bez obciętego tekstu.
Fizyczny sprzęt i balans przy stole pozostają do próby użytkownika.

Widok rzutów sprawdzono w pełnej stronie Chrome dla jednego k20 oraz dwóch
k20 z utrudnieniem: fokus, −/+, następna kość, podsumowanie, poprawka przez ↩
i końcowe zatwierdzenie. Próba 10 i 8 wybiera 8 i dolicza premię raz. Testy
transportu sprawdzają maski −/+/✓/↩, strumień bieżącej kości i zmianę na
podsumowanie również dla pułapki. Kontekst rzutu znika po rozstrzygnięciu.
Regresja wspólnego widoku obejmuje także dotychczasowe rzuty obrażeń walki.

Po podpięciu run ponownie przeszło **40 testów**: runtime (20), nowy
`test_exploration_mana_board.py` (17), widoki Chrome (2) i pełna strona (1).
Nowe testy przechodzą przez transport skanu i maski LED dla 14 metod, odrzucają
stary skan, sprawdzają dostępność run w lekcjach, wznowienie stosów i przerzut.
Pełna strona wykonuje wybory przez `/api/board/select`, również ✓ po wpisaniu
wyniku kości. Sprzęt zastępuje adapter testowy; nie jest to próba fizycznej planszy.

Testy reguł sprawdzają wszystkie 14 metod, KON zamiast CHA, biegłości, osobiste
pasywy, utrudnienie i przerzut, kolejność faz i pierwszeństwo 21/przekroczenia.
Testy runtime przechodzą rozmowę i obiekt każdym bohaterem, zapis i wznowienie,
odrzucenie starych poleceń oraz trzy dostępne postacie w samodzielnej scenie.
Testy przeglądarkowe sprawdzają widoki 390/1100 px, a pełna strona Flask
została rozegrana przez Chrome od wyboru Erynda do wyniku interakcji z obiektem.
Regresje obejmują istniejący walkthrough oraz generator kart.

Wyniki ukierunkowanych uruchomień przez `scripts/safe_pytest.sh` (osobno,
z limitem 60 sekund): **123 testy przeszły**.

| Plik w `tests/unit/` | Wynik |
| --- | ---: |
| `test_exploration_mana.py` | 23 |
| `test_exploration_mana_runtime.py` | 20 |
| `test_simple_combat_traps.py` | 9 |
| `test_mana_character_prints.py` | 25 |
| `test_training_walkthrough.py` | 33 |
| `test_training_walkthrough_browser.py` | 2 |
| `test_training_setup_focus_browser.py` | 2 |
| `test_exploration_mana_browser.py` | 2 |
| `test_exploration_mana_live_browser.py` | 1 |
| `test_arena_print_pack.py` | 6 |

Zapis i wczytanie sprawdzono dla wszystkich 14 własnych interakcji oraz
oczekującego rzutu pułapki każdej postaci. Chrome sprawdził też widoczność
instrukcji ustawiania figurek po dołączeniu nowego modułu. `git diff --check`
nie zgłosił błędów. Nie uruchamiano całego zestawu testów projektu.

Do próby użytkownika pozostaje ergonomia na fizycznej planszy, tempo doboru,
czytelność kosztów metod i balans. Nie zastępujemy tej próby testem symulatora.

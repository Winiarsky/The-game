# Eksploracja z maną — NPC i obiekty

Aktualizacja 2026-09-14: wdrożono moduł eksploracji i lekcje siedmiu postaci.
Przekroczenie daje **utrudnienie (2k20, niższy wynik), bez premii za karty**,
zamiast wcześniejszego −3. [Opis wdrożenia](EXPLORATION_MANA_IMPLEMENTATION.md). Poniżej historyczny projekt.

Aktualna propozycja i plan: [Eksploracja z maną 0.2](EXPLORATION_CONFRONTATIONS_MANA_V02_PLAN.md).
Wersja 0.2 aktualizuje cechy testów, przeszkody, ujawnianie profili i proste
pułapki bojowe oraz obejmuje karty i praktyczny samouczek. Poniżej wcześniejszy
projekt v0.1; w wymienionych obszarach pierwszeństwo ma v0.2.

Status: zbiorcza propozycja v0.1, 2026-09-13. Łączy uzgodniony kierunek
dobierania do 21 z nową propozycją siedmiu metod oddziaływania na obiekty.
Nie wdraża minigry, nowych pasywów ani migracji obecnych pułapek.

Dokument zbiera całość do rozmowy i pierwszej próby przy stole. Szczegółowe
przypadki procedury kart i wcześniejsze ustalenia społeczne opisuje
[projekt konfrontacji społecznych](SOCIAL_CONFRONTATIONS_MANA_V01.md).
Proponowane doprecyzowania są oznaczone; nie zastępują odpowiedzi użytkownika
na nadal otwarte pytania.

## 1. Jedna procedura, dwa zastosowania

| Element | Konfrontacja społeczna | Wyzwanie przy obiekcie |
| --- | --- | --- |
| Cel | Konkretne ustępstwo lub informacja | Konkretna zmiana stanu albo poznanie obiektu |
| Wykonawca | Bohater przypisany do podejścia społecznego | Bohater przypisany do sposobu działania |
| Profil kart | Reakcja NPC na daną metodę | Przydatność metody do danego obiektu |
| Przeszkoda | Drażliwy temat, niechęć do powtórzeń | Niestabilność, delikatny mechanizm, ograniczenie sekwencji |
| Sukces | Zgoda, współpraca, świadectwo, ustępstwo | Otwarcie, zabezpieczenie, naprawa, oczyszczenie, odczyt |
| Koszt porażki | Gorsze warunki, odmowa, utrata zaufania | Hałas, uszkodzenie, koszt materiału, inna droga dostępu |

Minigra obejmuje istotne przeszkody i konfrontacje. Zwykłe pytanie, obejrzenie
przedmiotu, podniesienie dostępnej rzeczy lub otwarcie niezablokowanej skrzyni
pozostaje zwykłą interakcją. Jedno znaczące wyzwanie ma jeden ustalony cel;
nie powtarzamy pełnej minigry osobno dla każdej śrubki.

Każde projektowane wyzwanie ma co najmniej trzy sensowne autorskie metody.
Nie każdy obiekt musi obsługiwać wszystkie siedem. Metody mogą prowadzić
do wspólnego celu innym kosztem, np. otwarcie skrzyni z zachowaniem zamka
albo przez jego zniszczenie. Dokładnie 21 spełnia deklarowany cel danej metody;
nie usuwa jej znanego kosztu ani nie przyznaje dodatkowych, nieopisanych mocy.

## 2. Siedem bohaterów i ich dwie specjalizacje

| Bohater | Metoda społeczna | Metoda przy obiekcie | Co konkretnie robi z obiektem |
| --- | --- | --- | --- |
| Garran | Autorytet | **Zabezpieczenie** | Podpiera konstrukcję, blokuje ruch części, kontroluje naprężenia; umożliwia bezpieczne użycie przejścia lub urządzenia. |
| Brakka | Zastraszanie | **Forsowanie** | Wyważa, rozrywa, podnosi, rozbija; pokonuje opór siłą, z określonym kosztem dla otoczenia. |
| Mira | Blef | **Manipulacja** | Otwiera zamek, zwalnia zatrzask, operuje drobnym mechanizmem; stawia na precyzję. |
| Dagna | Empatia | **Oczyszczenie** | Przywraca możliwość bezpiecznego korzystania ze skażonej wody, zabrudzonego wyposażenia medycznego lub obiektu objętego znanym jej obrzędem. |
| Lorian | Inspiracja | **Pomysłowość** | Buduje obejście problemu z dostępnych części: dźwignię, prowizoryczną korbę, zamiennik uszkodzonego elementu. |
| Nimra | Argumentacja | **Analiza** | Odczytuje runy, symbole i zasady działania urządzenia; wykonuje wynikającą z tego poprawną sekwencję obsługi. |
| Erynd | Dociekliwość | **Rozpoznanie** | Czyta ślady używania i zużycia, odnajduje ukrytą blokadę, punkt dostępu lub bezpieczny sposób obsługi. |

Wybór metody od razu wybiera jej bohatera. Nie następuje drugi wybór wykonawcy.
Zwykłe oglądanie otoczenia jest nadal swobodne; powyższe przypisanie dotyczy
mechanicznej próby rozwiązania wyzwania.

Różnice są praktyczne: Garran utrzymuje konstrukcję stabilną, Brakka pokonuje
jej opór; Mira precyzyjnie obsługuje istniejący mechanizm, Lorian przygotowuje
zamiennik lub obejście. Nimra rozumie zapis albo zasadę działania, Erynd
wnioskuje ze śladów, jak faktycznie posługiwano się przedmiotem.

Oczyszczenie i Analiza nie dają dowolnej magii za uzbieranie punktów.
Scena określa wymagane umiejętności, istniejący obrzęd/czar oraz materiały.
Pomysłowość również korzysta z rzeczy obecnych w scenie lub ekwipunku.
Nie dodajemy siedmiu nowych zestawów wyjątków karcianych; wszyscy używają
jednej procedury doboru.

### Dostępność i minimum trzech metod

Nadal otwarte pozostaje znaczenie minimum trzech metod przy składach 1–5.
Ścisłe przypisanie nie pozwala dać trzech dostępnych metod dwóm bohaterom.
Trzy zapisane metody nie zapewniają też dopasowania do każdej większej drużyny.

Roboczo: minimum trzy metody w autorskiej definicji; dostępne są te, których
wykonawcy uczestniczą i spełniają warunki. Autor musi sprawdzić wspierane składy
i dodać pasujące metody lub inną drogę fabularną, aby główny postęp nie utknął.
Nie zamieniamy automatycznie wykonawcy przy braku jego figurki.

## 3. Procedura dobierania do 21

1. Ustalamy cel, metodę, bohatera i znany koszt sposobu działania. Aplikacja
   przygotowuje profil wartości i ewentualną przeszkodę.
2. Propozycja przygotowania: tasujemy 25 kart, po pięć każdego koloru.
   Nie wykładamy rynku walki. Zaczynamy z pustą pulą wybranych kart.
3. Rozpoczęcie próby obejmuje pierwszy dobór dwóch kart. Wybieramy jedną,
   drugą odrzucamy. Gdy mają ten sam kolor, można dobierać do pierwszego
   innego koloru; jedna karta zostaje wybrana, wszystkie pozostałe odkryte
   trafiają na odrzucone. Nie dobieramy dalej po uzyskaniu drugiej barwy.
4. Zgłaszamy aplikacji wybrany kolor. Aplikacja sprawdza legalność względem
   reguł sceny, dodaje jego wartość i prowadzi ewentualny rzut przeszkody.
5. Po rozstrzygnięciu przeszkód dokładnie 21 kończy próbę sukcesem. Więcej
   niż 21 kończy dobieranie i prowadzi do testu z karą.
6. Poniżej 21 wybieramy pas albo dobór kolejnej oferty. Decyzja zapada przed
   odkryciem kart. Po zadeklarowaniu doboru trzeba przyjąć legalną kartę;
   nie wolno wycofać się dlatego, że obie opcje przekraczają 21.
7. Pas otwiera końcowy fizyczny test k20. Silnik dodaje normalny modyfikator
   przypisany temu działaniu, premię/karę za sumę i właściwe pasywy bohatera.
8. Wynik zmienia stan NPC albo obiektu i kończy próbę. Możliwość nowego
   podejścia zależy od tego stanu; nie ponawiamy bezkosztowo do skutku.

Fizyczna oferta dwóch barw pozostaje na stole. Do aplikacji zgłaszamy kolor,
pas/dobór i wymagane rzuty, a wyjątkowo wyczerpanie talii lub brak legalnej
karty. Aplikacja nie zna wszystkich odrzuconych duplikatów, więc nie może
wiarygodnie odtwarzać pozostałych fizycznych kart z samych wyborów.

Propozycja końca talii: bez przetasowania w środku próby. Jeżeli została jedna
legalna karta/barwa, przyjmujemy ją. Przy braku kart lub legalnego wyboru
wymuszony pas zachowuje obecną sumę. Jeśli jedyna barwa w bieżącej ofercie
jest zakazana, szukamy drugiej do wyczerpania talii — nie jest to darmowy pas.

Przygotowanie talii społecznej/obiektowej nie odświeża samo z siebie bojowych
efektów i zasobów. Przejścia między trybami oraz odtworzenie fizycznych stosów
po zapisie wymagają osobnego projektu implementacyjnego.

## 4. Wartości, informacja i przeszkody

Profil dotyczy konkretnego celu i metody przy danym NPC/obiekcie. Stary zamek
może sprzyjać Forsowaniu, ale sprawiać trudność Manipulacji; subtelny mechanizm
może mieć odwrotny układ. Wartości są ustalane przed próbą i nie zmieniają się
potajemnie podczas dobierania.

Ukryte pozostają etykiety podatności i porównanie metod przed wyborem.
Propozycja ujawniania: każda wartość jest odkrywana po pierwszym wybraniu
danego koloru i potem pozostaje widoczna w tej konfrontacji. Suma oraz premia
są zawsze jawne. Alternatywa ujawnienia całej tabeli po wybraniu metody nadal
pozostaje otwartą decyzją, nie potwierdzonym ustaleniem.

Na początek najwyżej jedna przeszkoda, pokazana przed pierwszym doborem:

- **Zakaz tego samego koloru z rzędu.** Przy obiekcie może oznaczać konieczność
  naprzemiennego zwalniania naprężeń; przy NPC niechęć do powtarzania nacisku.
  Dotyczy kolejnych wybranych kart, nie kolejności odrzuconych.
- **Ryzyko wskazanego koloru.** Np. po czerwonej gracz rzuca k6; na 1 dobieranie
  kończy się jak po przekroczeniu. Przy NPC to drażliwy temat, przy obiekcie
  kruchy zawias. Jest to ten sam mechanizm w innym kontekście.

Propozycja: rzut ryzyka poprzedza automatyczny sukces za 21. Karta domykająca
21 nie omija przeszkody. Nie naliczamy dwóch kar za ten sam wybór, który
zarówno uruchomił przeszkodę, jak i przekroczył limit.

## 5. Końcowe premie — wspólna tabela startowa do próby

| Suma / zakończenie | Efekt |
| --- | --- |
| 1–10 | Test bez premii karcianej |
| 11–14 | +1 do testu |
| 15–17 | +2 do testu |
| 18–19 | +4 do testu |
| 20 | +6 do testu |
| 21 po przeszkodach | Automatyczny sukces celu wybranej metody |
| Przekroczenie lub przerwanie przeszkodą | Test z −3 zamiast premii |

Przekroczenie oznacza gorszą próbę, nie automatyczne zniszczenie przedmiotu.
Uszkodzenie, hałas i inne następstwa wynikają z końcowego rozstrzygnięcia oraz
z góry opisanych kosztów metody. Dla pierwszego porównania metod proponujemy
wspólny bazowy ST w obrębie wyzwania; różnice profili i pasywów już wpływają
na wynik. Tabela, rozkłady i koszty wymagają testów balansu.

## 6. Specjaliści: Lorian i Erynd

### Lorian — obecne zdolności

**Obycie i targowanie:** +2 do własnego pozabojowego testu Charyzmy.
W konfrontacji społecznej dochodzi do normalnego modyfikatora i premii/karze
karcianej. Nie podnosi sumy many ani nie przechodzi na test innego bohatera.

**Improwizacja:** jeden przerzut własnego nieudanego pozabojowego testu
Charyzmy na NPC, przed konsekwencjami; drugi wynik jest ostateczny. Propozycja
integracji zachowuje to przy końcowym k20, również po przekroczeniu. Nie
przerzuca k6 przeszkody. Przy automatycznym 21 nie ma testu do przerzucenia.

Pomysłowość przy obiektach jest nową metodą, odrębną od istniejącego pasywu
Improwizacja. Pasywy Charyzmy nie stają się automatycznie premią do narzędzi,
Inteligencji ani prób przy przedmiotach bez NPC.

### Erynd — nowa propozycja pasywu

**Praktyka terenowa: +2 do własnego końcowego testu wyzwania przy obiekcie
podczas eksploracji.**

Przy stałych wykonawcach najczęściej działa to w Rozpoznaniu. Premia wynika
z rodzaju wyzwania, a nie z każdej czynności, która wspomina jakiś przedmiot.
Nie dodaje punktów do puli kart, nie obejmuje całej drużyny, k6 przeszkody,
walki ani rozbrajania bojowej pułapki. Przy dokładnym 21 nie jest potrzebna.
Nie dodajemy jeszcze drugiego przerzutu lub manipulowania kartami.

Erynd obecnie ma **Czujność zwiadowcy** (+2 do inicjatywy i wykrywania ukrytych
przeciwników; opis wyłącza pułapki) oraz **Ekspertyzę zwiadowcy** (podwójna
biegłość w Skradaniu i Sztuce przetrwania). Żadna z nich nie jest ogólną premią
do obiektów. Czytanie prądów w bieżącej referencji dotyczy końcowego uzupełnienia
rynku walki; nie przenosimy go automatycznie do nowego doboru dwóch kart.

Źródła obecnych premii: `src/dnd_board_game/character_creation/boardgame_help.py`,
`src/dnd_board_game/application/combat_turn_action_flow.py` i
`docs/BOARDGAME_ARCHETYPES_LEVELS_1_3.md`. Praktyka terenowa jest nowym projektem,
a nie opisem już działającego pasywu.

## 7. Pułapki i obiekty — kierunek a obecny runtime

Kierunek użytkownika: pułapki jako element taktyczny działają w walce, z
pozycją, obszarem, akcjami i uruchamianiem mechanizmu. Poza walką istotne
przeszkody przy przedmiotach, konstrukcjach i urządzeniach korzystają z
powyższej procedury. Pęknięty zawias albo zablokowany rygiel nie wymaga
osobnej bojowej figurki pułapki, aby stanowić wyzwanie eksploracyjne.

Korekta opisu stanu obecnego: kod posiada również `ExplorationTrap`,
wykrywanie, rozbrajanie, omijanie i uruchamianie pułapek poza walką
(`src/dnd_board_game/exploration/traps.py`). W tym zadaniu ich nie usuwamy
ani nie migrujemy zapisów. Docelowy podział wymaga późniejszego przeglądu
istniejącego contentu i jednoznacznych przejść eksploracja → walka.

Jeżeli ten sam obiekt pojawia się potem w walce, musi zachować swój stan:
otwarty zamek pozostaje otwarty, zniszczony element zniszczony. Jeden sukces
eksploracyjny nie może drugi raz wymagać identycznego odblokowania w walce.

## 8. Przykład NPC — świadectwo Ireny

Cel: uzyskać zgodę Ireny, żeby wspólnie z drużyną złożyła Nessie świadectwo
o dokarmianiu żeraków. Sama informacja o procederze jest już znana.

Wartości poniżej są widokiem autora, a nie jawnym porównaniem dla graczy.
Przykładowy ST końcowego testu: 16. Profile są materiałem do testowania.

| Podejście / wykonawca | Czerwona | Biała | Zielona | Czarna | Niebieska | Warunek metody |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Empatia — Dagna | 7 | 1 | 1 | 3 | 5 | Bez dodatkowej przeszkody |
| Zastraszanie — Brakka | 7 | 6 | 5 | 3 | 2 | Po czerwonej k6; 1 przerywa dobieranie |
| Inspiracja — Lorian | 5 | 3 | 2 | 6 | 1 | Nie wybieraj identycznego koloru z rzędu |

Efekt sukcesu: Irena składa świadectwo. Empatia buduje współpracę przez
zrozumienie obaw, Zastraszanie daje wymuszoną zgodę z ochłodzeniem relacji,
Inspiracja przekonuje ją do naprawienia części szkód. Ustępstwo nie obejmuje
gwarancji bezkarności, której drużyna nie może udzielić.

Porażka: Irena odmawia wspólnego wystąpienia; drużyna nadal może złożyć własny
raport. Porażka po nacisku dodatkowo zamyka dalsze osobiste negocjacje w tej
scenie. Nie znika poznana prawda i nie blokuje się zakończenie misji.

Przykładowy przebieg Inspiracji:

| Oferta na stole | Wybrana karta | Wartość | Suma |
| --- | --- | ---: | ---: |
| Czerwona / niebieska | Czerwona | 5 | 5 |
| Czarna / zielona | Czarna | 6 | 11 |
| Biała / niebieska | Biała | 3 | 14 |
| Czerwona / zielona | Czerwona | 5 | 19 |

Lorian nie powtórzył koloru bezpośrednio po sobie. Przy 19 może spasować:
test to **k20 + normalny modyfikator testu Charyzmy + 4 za sumę + 2 za Obycie**.
Obycie dodajemy tylko raz; jeżeli podsumowanie aplikacji już je zawiera,
nie doliczamy go ponownie. Przy porażce dostępna jest niewykorzystana
Improwizacja na Irenę.

Jeżeli zamiast pasu zadeklaruje dobór, wynik nie jest jeszcze znany. Oferta
zielona/czarna pozwoli wybrać zieloną 2 i uzyskać 21. Oferta czerwona/biała
zawiera zakazaną czerwoną (poprzedni wybór) i białą 3: musi przyjąć białą,
dojść do 22 i wykonać test z −3. Nie wolno wtedy wrócić do pasu przy 19.

## 9. Przykład obiektu — skrzynia ewakuacyjna

Przy kuchni stoi wojskowa skrzynia z lekami. Wieko jest zakleszczone, a
mechanizm ma blokadę transportową. Cel: odzyskać zawartość. To istotny
obiekt eksploracyjny; nie ma ukrytej bojowej pułapki.

Ponownie: tabela jest dla autora. Przykładowy ST: 15.

| Podejście / wykonawca | Czerwona | Biała | Zielona | Czarna | Niebieska | Przeszkoda / koszt |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Rozpoznanie — Erynd | 7 | 1 | 1 | 3 | 5 | Bez dodatkowej przeszkody |
| Manipulacja — Mira | 6 | 2 | 4 | 1 | 5 | Nie wybieraj identycznego koloru z rzędu |
| Forsowanie — Brakka | 7 | 6 | 5 | 3 | 2 | Po czerwonej k6; 1 przerywa dobieranie |

- Erynd odnajduje po śladach tarcia ukryty sposób zwolnienia blokady,
  następnie odblokowuje i otwiera skrzynię. Sukces obejmuje wykonanie
  rozwiązania, nie samo odkrycie potrzeby następnej minigry.
- Mira precyzyjnie zwalnia zakleszczony mechanizm z użyciem dostępnych
  narzędzi. Skrzynia pozostaje sprawna.
- Brakka wyłamuje okucie i otwiera wieko. Zniszczony zamek i hałas są znanym
  kosztem tej metody także przy 21; sukces zachowuje zawartość.

Zwykła porażka Rozpoznania nie potwierdza braku mechanizmu: drużyna ustala,
że konieczny jest demontaż okucia, co otwiera dalszą drogę kosztem materiału
i opisanej pracy. Nie ponawiamy identycznego badania do skutku. Nieudana
Manipulacja pogarsza zakleszczenie i zamyka tę metodę; pozostaje demontaż
lub Forsowanie. Porażka Forsowania może zniszczyć określoną w contencie
część leków. Samo przekroczenie 21 jeszcze tego nie robi — jest test z karą.

Przykładowy przebieg Rozpoznania Erynda:

| Oferta na stole | Wybrana karta | Wartość | Suma |
| --- | --- | ---: | ---: |
| Czerwona / biała | Czerwona | 7 | 7 |
| Niebieska / zielona | Niebieska | 5 | 12 |
| Czarna / czerwona | Czarna | 3 | 15 |
| Niebieska / niebieska, dociągnięta zielona | Jedna niebieska | 5 | 20 |

W ostatniej ofercie odrzucamy drugą niebieską i zieloną. Pula Erynda zawiera
cztery karty, a nie pięć; wszystkie dobrane karty mieszczą się w talii 25.

Erynd może spasować przy 20: **k20 + normalny modyfikator wskazanego testu
Rozpoznania + 6 za sumę + 2 za proponowaną Praktykę terenową**, przeciw ST 15.
Test opiera się np. na Inteligencji (Śledztwo), określonej w definicji obiektu;
premia +2 jest osobistą cechą nowego wyzwania, nie zmianą jego atrybutu.

Przy dalszym doborze biała albo zielona 1 domknie 21 po jej wybraniu.
Czerwona/czarna wymusi przekroczenie. Wartości nieznanych jeszcze kolorów
pozostają nieznane aż do ujawnienia według wybranej polityki informacyjnej.

## 10. Zakres pierwszego prototypu

- Dwa rodzaje celu, jedna procedura i tabela premii.
- Siedem stałych wykonawców dla NPC i siedem metod obiektowych.
- Minimum trzy autorskie sposoby na każde istotne wyzwanie, z kontrolą
  dopasowania składu i możliwości kontynuacji po porażce.
- Profile pięciu kolorów; najwyżej jedna dodatkowa przeszkoda na metodę.
- Obecne społeczne pasywy Loriana oraz nowa, osobista premia +2 Erynda.
- Przykład Ireny i skrzyni jako pierwsze sceny do próby przy stole.

Pozostają do decyzji: ujawnianie wartości, gwarancja trzech dostępnych metod
przy małych składach, finalne profile i premie, dokładne efekty porażek,
przygotowanie/wznowienie fizycznej talii oraz migracja obecnych pułapek.
Nie dodajemy na tym etapie nowych zdolności mieszania kart dla każdej postaci.

## Weryfikacja obecnego stanu

W poprzednim etapie sprawdzono 5 istniejących testów Obycia i Improwizacji
Loriana. W tym etapie sprawdzono opis i zastosowania Czujności zwiadowcy,
Ekspertyzę Erynda oraz istniejący model `ExplorationTrap`. Nowy pasyw +2
do obiektów nie jest jeszcze zaimplementowany.

Uruchomienie istniejących testów eksploracyjnych pułapek:
`scripts/safe_pytest.sh --timeout 60 tests/unit/test_exploration_traps.py::test_successful_disarm_and_bypass_prevent_trigger tests/unit/test_exploration_traps.py::test_failed_disarm_triggers_trap`.
Wynik: **2 testy zaliczone**.
Nie są to testy nowej minigry; potwierdzają działanie obecnego modelu,
który wymaga uwzględnienia przy przyszłej zmianie.

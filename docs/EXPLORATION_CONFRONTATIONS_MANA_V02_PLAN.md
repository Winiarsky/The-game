# Eksploracja z maną 0.2 — propozycja i plan wdrożenia

Aktualizacja 2026-09-14: wdrożono moduł eksploracji i lekcje siedmiu postaci.
Przekroczenie daje **utrudnienie (2k20, niższy wynik), bez premii za karty**,
zamiast wcześniejszego −3. [Opis wdrożenia](EXPLORATION_MANA_IMPLEMENTATION.md). Poniżej historyczny projekt.

Status: projekt i plan, 2026-09-13; minigra, nowe pasywy, karty i lekcje
nie są jeszcze wdrożone. Ten dokument zastępuje propozycje v0.1 w zakresie
cech, ujawniania profili, przeszkód i pułapek. Ustalenia użytkownika oraz
rekomendacje do prototypu rozróżniamy poniżej.

## 1. Kierunek i wspólna procedura

Ustalone przez użytkownika: siedem metod społecznych i analogicznie siedem
obiektowych, stali wykonawcy, minimum trzy sposoby rozwiązania wyzwania,
fizyczne dobieranie jednej z dwóch kart do 21, decyzja o pasie przed ofertą,
premia za bliskość oraz kara po przekroczeniu. Końcowe testy korzystają
z odpowiednich cech; Zastraszanie Brakki z Kondycji. Pułapki w walce mają
pozostać proste: wykrycie i zwykły test dezaktywacji. Wdrożenie musi objąć
karty oraz praktyczne etapy samouczka na wzór ćwiczeń combatu.

Minigrę uruchamiamy dla znaczącej przeszkody. Zwykłe pytanie, oglądanie,
podnoszenie dostępnej rzeczy i otwieranie zwykłych drzwi nie wymagają kart.
Metoda opisuje konkretny cel oraz znany koszt, np. otwarcie skrzyni przez
wyłamanie zamka. Dokładnie 21 gwarantuje ten cel, ale nie usuwa kosztu metody.

1. Wybierz cel i metodę; aplikacja wskazuje przypisanego bohatera, cechę,
   właściwą biegłość, pasyw, znane koszty i jedną ewentualną przeszkodę.
2. Rozpocznij próbę. Rekomendacja: przygotuj i przetasuj 25 kart, po pięć
   każdego koloru, bez rynku. Metoda zostaje zablokowana przed ujawnieniem
   jej profilu. Rozpoczęcie zobowiązuje do pierwszego doboru.
3. Odkryj dwie karty, wybierz jedną. Przy identycznym kolorze możesz dobierać
   do pierwszej innej barwy. Zatrzymujesz jedną kartę; resztę odkrytych
   odrzucasz. Do aplikacji zgłaszasz wybrany kolor.
4. Aplikacja stosuje widoczną regułę przeszkody i liczy sumę. Dokładnie 21
   daje sukces; przekroczenie kończy dobieranie i otwiera test z karą.
5. Poniżej 21 pasujesz albo deklarujesz kolejny dobór przed odkryciem kart.
   Po zobaczeniu oferty nie można spasować ani zmienić bohatera/metody.
6. Końcowy test i skutek zmieniają stan sceny. Nowa próba wymaga warunków
   określonych w scenie; odświeżenie strony nie odtwarza szansy od zera.

Tabela startowa pozostaje do sprawdzenia w prototypie:

| Suma | Efekt |
| --- | --- |
| 1–10 | Bez premii karcianej |
| 11–14 | +1 |
| 15–17 | +2 |
| 18–19 | +4 |
| 20 | +6 |
| 21 po rozstrzygnięciu przeszkód | Automatyczny sukces |
| Przekroczenie albo przerwanie przez ryzyko | −3 zamiast premii |

Kara nie oznacza automatycznej porażki fabularnej. Limit liczby wyborów
wymusza zwykły pas, nie karę za przekroczenie. Jedno zdarzenie nie nalicza
dwukrotnie −3. Naturalne 1/20 końcowego testu cechy nie zastępuje oceny
sumy przeciw ST; automatyczny sukces pochodzi z 21 na kartach.

Bez przetasowania w środku próby: ostatnia pojedyncza legalna karta może
zostać wybrana; brak kart/legalnego wyboru wymusza pas. Przy zakazanej jedynej
barwie szukamy drugiej do wyczerpania talii. Fizycznej oferty nie rekonstruujemy
z samych wybranych kolorów. Zgłaszanie wyczerpania pozostaje czynnością graczy.
Szczegóły pierwotnej procedury: [v0.1](SOCIAL_CONFRONTATIONS_MANA_V01.md).

## 2. Metody i cechy końcowego testu

Poniższe przypisania poza wskazaną przez użytkownika Kondycją Brakki są
rekomendacją do prototypu. Cecha metody jest stała, widoczna przed wyborem
i wspólna dla reguł, karty oraz lekcji. Nie wybiera jej narrator ani LLM.

| Bohater | NPC | Cecha | Obiekt | Cecha |
| --- | --- | --- | --- | --- |
| Garran | Autorytet — zdecydowana obecność i przejęcie kontroli | Siła | Zabezpieczenie — stabilizacja, utrzymanie naprężeń | Kondycja |
| Brakka | Zastraszanie — nieustępliwość i odporność na nacisk | Kondycja | Forsowanie — wyważenie, podniesienie, rozerwanie | Siła |
| Mira | Blef — zbudowanie spójnego pozoru, sprytne kłamstwo | Inteligencja | Manipulacja — zamek, zatrzask, precyzyjny mechanizm | Zręczność |
| Dagna | Empatia — rozpoznanie obaw i potrzeb | Mądrość | Oczyszczenie — bezpieczne użycie skażonego obiektu | Mądrość |
| Lorian | Inspiracja — poruszenie rozmówcy i zachęta | Charyzma | Pomysłowość — obejście problemu z dostępnych części | Inteligencja |
| Nimra | Argumentacja — rozumowanie i dowody | Inteligencja | Analiza — zasada działania, runy, sekwencja | Inteligencja |
| Erynd | Dociekliwość — wychwycenie szczegółu i niespójności | Mądrość | Rozpoznanie — ślady zużycia i sposób obsługi | Mądrość |

Nie próbujemy użyć każdej cechy w rozmowie za wszelką cenę. Blef Miry opiera
się na sprycie, a nie na szybkości dłoni. Są to jawne reguły autorskie dla
tych metod; nie zmieniamy globalnego mapowania umiejętności D&D ani innych
testów w aplikacji. Oczyszczenie i Analiza nie przyznają dowolnej magii;
scena wymaga odpowiednich umiejętności, narzędzi, materiałów lub znanego obrzędu.

Wzór: **k20 + modyfikator wskazanej cechy + należna biegłość + premia/kara
z kart + właściwy pasyw**. Poprawna postać jest właścicielem każdej premii.

- Definicja czynności może wskazać istniejącą umiejętność/narzędzie. Biegłość
  jest dodawana tylko wtedy, gdy bohater ją posiada. Nie tworzymy automatycznie
  biegłości we wszystkich siedmiu metodach.
- Ekspertyza zastępuje mnożnik biegłości ×1 mnożnikiem ×2. Umiejętność
  i narzędzie nie dają dwóch premii za tę samą próbę.
- Dla Zastraszania na KON liczymy KON i biegłość w Zastraszaniu od nowa.
  Nie dodajemy gotowej premii Zastraszania zawierającej CHA ani biegłości
  w rzutach obronnych na KON. To test cechy, nie rzut obronny.
- UI pokazuje rozbicie, np. „KON +3, Zastraszanie +2, karty +4”.
- Lorian zachowuje Obycie (+2 do własnego pozabojowego testu CHA) oraz
  Improwizację (jeden przerzut własnego nieudanego takiego testu na NPC,
  przed konsekwencjami). Jego obiektowa Pomysłowość na INT ich nie otrzymuje.
- Nowa propozycja Erynda: Praktyka terenowa, +2 do własnego końcowego testu
  wyzwania obiektowego w eksploracji. Bez wpływu na sumę many, innych
  bohaterów, kość przeszkody oraz wykrywanie/dezaktywowanie pułapek w walce.

Minimum trzech autorskich metod nadal wymaga kontroli składu 1–5. Przy jednym
lub dwóch bohaterach trzy dostępne metody są niemożliwe przy ścisłym przypisaniu.
Projekt sceny zapewnia wspieranemu składowi drogę postępu, również po porażce;
nie pożycza nieobecnej postaci. Gwarancja trzech zawsze dostępnych opcji pozostaje
osobną decyzją, nie ukrytym założeniem tego planu.

## 3. Podatności: profil ukryty przed wyborem, czytelny podczas próby

Rekomendacja: przed wyborem widzimy fabularną sytuację i zapowiedziane koszty,
bez etykiet „podatny/odporny” i tabel konkurencyjnych metod. Po rozpoczęciu
odsłaniamy pełną tabelę wybranej metody. Nie można wrócić do menu, podejrzeć
drugiej i zacząć od nowa. To proponowana zmiana wobec odkrywania wartości
dopiero po pierwszym użyciu w v0.1, nie potwierdzona już odpowiedź użytkownika.

Dzięki temu najpierw odczytujemy rozmówcę lub obiekt, a później podejmujemy
świadome ryzyko kart. Jeśli wartości pozostaną nieznane także podczas próby,
pierwsze wybory będą w dużej części zgadywaniem. Obie wersje można porównać
w pierwszej próbie przy stole; plan implementacji przyjmuje odsłonięcie po
zablokowaniu metody jako wariant roboczy.

Zaczynamy od trzech współdzielonych szablonów, zamiast osobnej matematyki
każdego NPC. Kolory można przypisać inaczej w definicji sceny, ale profil
pozostaje stały w trakcie próby. Katalog używa istniejących kodów
many: C = czerwona, B = biała, Z = zielona, F = czarna, N = niebieska.

| Szablon do testów | C | B | Z | F | N |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ostrożne domykanie, kandydat dla podatności | 7 | 1 | 1 | 3 | 5 |
| Pośredni | 7 | 2 | 3 | 4 | 5 |
| Większe skoki, kandydat dla odporności | 7 | 6 | 5 | 3 | 2 |

To kandydaci, nie udowodnione stopnie trudności. Niska karta pomaga przy 20,
ale karta 2 pomaga przy 19; większe wartości mogą szybciej zbudować dobrą
sumę. Limit czterech wyborów może szczególnie zaszkodzić profilowi z małymi
wartościami. Nie oznaczamy profilu „łatwy” tylko na podstawie średniej.

Rozdzielamy trzy elementy: profil określa sposób budowania sumy, przeszkoda
zmienia jedną decyzję, konsekwencje określają stawkę. W pierwszym prototypie
metody jednego wyzwania mają wspólny bazowy ST. Odporność nie dodaje jeszcze
wyższego ST, drugiej przeszkody i kolejnej kary do kości jednocześnie.
Niemożliwe ustępstwo jest niedostępną metodą z fabularnym uzasadnieniem,
a nie ukrytą odpornością udającą wykonalny cel.

Kalibracja przed zamrożeniem: rozegrać rzeczywistą talię 25 kart, duplikaty
i koniec talii; porównać pasowanie przy 17/18/19/20 i strategię uwzględniającą
stan. Mierzyć sukces, dokładne 21, przekroczenia, liczbę wyborów i koszt
fabularny dla rzeczywistych modyfikatorów bohaterów. Osobno bez przeszkody
i z każdą z trzech pierwszych. Nie zakładać znajomości niewidocznej kolejności
talii ani pełnych odrzuconych w aplikacji. Zrezygnować z etykiet trudności
albo zmienić szablony, jeśli wyniki nie potwierdzą zamierzonego porządku.

## 4. Ciekawsze przeszkody — jedna reguła na próbę

Przeszkoda jest jawna przed rozpoczęciem. Aplikacja pokazuje jej bieżący efekt
i przeliczone wartości wszystkich kolorów przed następnym doborem.

| Przeszkoda | Dokładna reguła | NPC / obiekt |
| --- | --- | --- |
| **Powtarzasz się** | Wybranie tego samego koloru co poprzednio dodaje +2 do wartości tej karty; wolno go wybrać. Pierwsza karta bez dopłaty. | Rozmówca traci cierpliwość / powtarzany ruch napina element. |
| **Rozchwianie** | Jeśli poprzednio wybrano czerwoną, następna wybrana karta ma +2. Po jej rozliczeniu efekt znika; kolejna czerwona ustanawia go ponownie. Nie kumuluje się powyżej +2. | Mocny nacisk zaostrza rozmowę / szarpnięcie rozchwiewa mechanizm. |
| **Krótka okazja** | Najwyżej cztery wybrane karty; po czwartej, jeśli nie ma 21 ani przekroczenia, następuje zwykły pas. Duplikaty i odrzucone nie zużywają limitu. | Odjeżdżający urzędnik / zacinający się mechanizm chwilowo puszcza. |
| **Cena skrótu** — później | Wybrany oznaczony kolor daje niską wartość zgodnie z profilem, ale przy sukcesie nakłada jeden wcześniej opisany koszt metody. Powtórzenie koloru nie mnoży tego kosztu. | Zgoda w zamian za konkretną przysługę / otwarcie z trwałym zniszczeniem zamka. |
| **Drażliwy punkt** — opcjonalnie później | Po wskazanym kolorze k6; 1 kończy dobieranie z −3 do testu. Rzut poprzedza sprawdzenie 21. | Osobisty temat / kruchy element. |

Na start wdrażamy trzy pierwsze. Dają inne decyzje bez dodatkowych rzutów
i wymagają jedynie już zgłaszanych kolorów. Cena skrótu wymaga powiązania
historii wyborów ze skutkiem, a k6 pozostaje dostępną późniejszą odmianą.
Dotychczasowy zakaz powtórzenia jest alternatywą dla dopłaty, nie dodatkową
regułą tej samej próby. Nie łączymy tych przeszkód na początku.

Kolejność: sprawdzenie legalności koloru → wartość bazowa i dopłata wynikająca
z poprzedniej karty → zapis wyboru i nowego stanu przeszkody → ewentualny k6
→ przerwanie ryzykiem/przekroczenie → sukces 21 → limit wyborów → pas/dobór.
Wartości wcześniejszych kart nie zmieniają się wstecz. Cena skrótu, jeśli
zostanie później włączona, jest rozliczana raz z końcowym sukcesem, także 21.

## 5. Dwa przykłady do pierwszego prototypu

### NPC — Irena i świadectwo dla Nessy

Cel: Irena osobiście potwierdza znany już drużynie proceder dokarmiania żeraków.
Trzy drogi: Empatia Dagny, Zastraszanie Brakki, Inspiracja Loriana. Zgoda
wymuszona naciskiem ochładza relację; 21 nie usuwa tego znanego kosztu.
Porażka nie blokuje własnego raportu drużyny. Roboczy ST 16.

Brakka: profil pośredni C7/B2/Z3/F4/N5, przeszkoda Rozchwianie. Wybiera
C7 → B(2+2) → N5 → Z3, sumy 7 → 11 → 16 → 19. Biała zużyła efekt czerwonej;
następne karty mają zwykłe wartości. Przy pasie:

**k20 + KON 3 + biegłość Zastraszania 2 + karty 4 = k20 +9**, przeciw ST 16.
Naturalne 7 daje 16 i sukces. Wyniki KON 16 oraz biegłość pochodzą z obecnego
startowego Brakki. Nie dodajemy jego premii do rzutów obronnych na KON.

Jeżeli zadeklaruje dobór przy 19: oferta B2/N5 pozwala wybrać B i uzyskać 21;
oferta Z3/F4 wymusza przekroczenie. W drugim przypadku końcowy test to
k20 +3 +2 −3 = k20 +2. Nie można spasować po zobaczeniu oferty.

### Obiekt — skrzynia lekarstw

Cel: dostać się do lekarstw. Erynd odczytuje ślady używania i zwalnia blokadę,
Mira precyzyjnie otwiera mechanizm, Brakka wyłamuje zamek z zapowiedzianym
hałasem. Roboczy ST 15. Metody mają inne profile; nie wymagają kolejnej
minigry po udanym odkryciu sposobu otwarcia.

Erynd: C7/B1/Z1/F3/N5, przeszkoda Powtarzasz się. Wybiera
C7 → N5 → F3 → N5 = 20. Niebieskie nie są kolejne, więc nie ma dopłaty.
Test tej sceny: Mądrość z Percepcją (odczytanie śladów na obiekcie), jawnie
określony przed rozpoczęciem. Przy pasie:

**k20 + MDR 2 + biegłość Percepcji 2 + karty 6 + Praktyka terenowa 2 = k20 +12**,
przeciw ST 15. Ostatnie +2 jest projektowanym pasywem, pozostałe cechy
i biegłość wynikają z obecnego Erynda. Czujność zwiadowcy nie dodaje następnych +2.

Przy kolejnym doborze B1/Z1 pozwala osiągnąć 21. Przy N/F powtórzona N ma 7,
a F ma 3 — obie przekraczają. Sukces otwiera skrzynię bez zniszczenia zamka;
porażka ujawnia konieczność demontażu obejmy kosztem materiałów albo innej drogi.
Nie wolno powtarzać tej samej bezkosztowej próby do skutku.

## 6. Pułapki bojowe: wykryj, podejdź, dezaktywuj

Ustalenie użytkownika: bez dobierania do 21 w obsłudze pułapki podczas walki.
Rekomendacja szczegółu dla zwykłej mechanicznej pułapki:

1. Wykrywanie: akcja i k20 + MDR + należna Percepcja przeciw ST wykrycia.
   Istniejące szczególne zdolności wykrycia zachowują swój zakres i warunki.
2. Po wykryciu aplikacja ujawnia znacznik i dostępne podejście. Dezaktywacja
   wymaga odpowiedniej pozycji (domyślnie sąsiedztwa) oraz wymaganych narzędzi.
3. Dezaktywacja: jedna akcja i k20 + ZRĘ + należna biegłość narzędziowa
   przeciw ST pułapki. Sukces trwale rozbraja; porażka uruchamia jej opisany
   efekt. Nie dodajemy minigry, etapów „żywotności” mechanizmu ani profilów many.
4. Ewentualny rzut obronny przed skutkiem uruchomionej pułapki jest osobnym,
   zwykłym rzutem. Nie mylimy go z testem dezaktywacji.

To rekomendacja jednego bazowego rodzaju, bez katalogu specjalnych pułapek.
Aktualny runtime ma też ExplorationTrap, a bojowe interakcje są osobnym
przepływem. Najpierw obsłużyć powyższy przebieg, potem sklasyfikować istniejący
content i zapisy. Obiekt rozbrojony lub otwarty nie odzyskuje blokady po
przejściu między eksploracją a walką. Migracja nie może usuwać zapisanych stanów.

## 7. Plan działania i oczekiwane pliki

Każdy etap ma konkretny wynik. Aktualne zadanie kończy projekt i plan;
poniższe prace wykonawcze pozostają w TODO. Nowe nazwy plików są proponowane.

### Etap 1 — katalog, profile i kalibracja

- Jeden katalog 14 metod z bohaterem, cechą i opisem; trzy profile i trzy
  pierwsze przeszkody; zamrożenie tabeli premii po próbie z rzeczywistą talią.
- Sprawdzenie modyfikatorów siedmiu startowych bohaterów, pasywów oraz
  rozstrzygania biegłości z inną cechą. Wybór informacji odsłanianej w próbie.
- Pliki: nowy `rules/exploration_mana_catalog.py`, konfiguracje wyzwań w
  `content/`, ten dokument i `docs/BOARDGAME_ARCHETYPES_LEVELS_1_3.md`.
- Odbiór: porównanie wyników profili przy różnych strategiach i przeszkodach;
  metoda nie staje się automatycznie najlepsza wyłącznie przez swój numer.

### Etap 2 — czysty silnik i zapis

- Nowy `rules/exploration_mana.py`: stan próby i czyste przejścia dla
  rozpoczęcia, deklaracji doboru, wybranego koloru, pasu oraz rzutu.
- Końcowy test wykorzystuje istniejące prymitywy `rules/checks.py` i kości;
  cecha pochodzi z katalogu metody. Bez odczytu plików, Flask, RNG i hardware
  w regułach. Kości oraz wybrane kolory są danymi wejściowymi.
- Zapisać id próby/celu/metody/profilu, bohatera, fazę, wybrane kolory i ich
  naliczone wartości, sumę, stan przeszkody, oczekiwany rzut, użycie przerzutu,
  skutek i znacznik jego zatwierdzenia. Zapis nie zawiera fikcyjnej kolejności
  fizycznej talii ani odrzuconych, których gracz nie zgłosił.
- Dodać jawne wznawianie fizycznych stosów: zachowane stosy pozwalają kontynuować;
  po ich pomieszaniu nie oferować darmowego resetu. Procedurę odzyskania trzeba
  ustalić przed udostępnieniem zapisu próby graczom.
- Pliki: `rules/`, `save/`, nowe `tests/unit/test_exploration_mana.py` oraz
  `tests/unit/test_exploration_mana_checks.py`, odpowiednie testy migracji.
- Odbiór: 21/bust/pas/limit, duplikaty po stronie stołu, legalność koloru,
  koniec talii, +2 przeszkody, KON zamiast CHA, biegłość tylko raz, pasywy
  i przerzut, odtworzenie każdej fazy oraz jednokrotne zastosowanie skutku.

### Etap 3 — aplikacja, plansza i dwie sceny

- Nowy `application/exploration_mana_flow.py`, adaptery istniejących celów
  NPC i obiektów; loader contentu waliduje autorstwo i dostępność metod.
- UI: wybór metody → profil i pierwszy dobór → wybrany kolor → pas/dobór
  → ewentualne kości → wynik. Pola NPC/obiektu wybierają cel; ikony ekranu
  oraz istniejące potwierdzenia obsługują dalszy przebieg. Nie zakładać
  aktywnego dolnego paska run: bieżące wydruki oznaczają go jako wyłączony.
- Jasne rozbicie cechy/biegłości/kart/pasywu, bieżąca dopłata do koloru,
  liczba wyborów tylko gdy wymaga jej przeszkoda. Bez pokazywania wewnętrznych
  id lub kodów C/B/Z/F/N graczowi.
- Zablokować nieaktualne potwierdzenia, podwójne zgłoszenia i zmianę metody
  po rozpoczęciu. Przy minimalnym wejściu ufamy fizycznej ofercie graczy.
- Pierwszy grywalny wycinek: Irena i skrzynia, każde z trzema metodami,
  realnym skutkiem i drogą po porażce. Potem pokrycie wszystkich 14 metod.
- Ustalić przejście 25 kart eksploracji ↔ rynek walki bez bezprawnego
  odświeżania efektów/zasobów; przetestować przerwanie sceny przez walkę.
- Pliki: `application/`, integracja `ui/exploration_app.py`, widoki `ui/`,
  `scenarios/`, `content/scenarios/`, testy przepływu i integracji obu celów.

### Etap 4 — proste pułapki bojowe

- Dopiąć zwykły test wykrycia i test narzędziowy dezaktywacji do kosztu akcji,
  pozycji i trwałego stanu pułapki. Przejrzeć obecne zdolności wykrywania.
- Pliki: istniejące `combat/scene_interactions.py`,
  `application/combat_scene_interaction_flow.py`, odpowiedni content oraz
  `exploration/traps.py`/adapter stanów tylko w zakresie migracji.
- Odbiór: nieudane wykrycie, ujawnienie, zły zasięg, brak narzędzi, sukces,
  uruchomienie po porażce, właściwy koszt akcji i brak doboru many do 21.

### Etap 5 — karty i pomoc z tego samego katalogu

- Każda postać: sekcja/karta „Eksploracja” z jej dwiema metodami, cechami,
  opisem celu i właściwymi pasywami. Bez stałych tabel wartości NPC na karcie.
- Wspólna ściąga: dwie karty → wybierz jedną → decyzja przed następną ofertą,
  tabela premii, 21, kara i fizyczne odrzucanie duplikatów.
- Poprawić opis Zastraszania Brakki na KON w sekcji nowej metody, nie
  nadpisując globalnej tabeli umiejętności CHA. Dodać Praktykę terenową Erynda,
  zachować właściwy zakres premii/przerzutu Loriana. Wyjaśnić różnicę między
  Pomysłowością na INT a pasywem Improwizacja na CHA.
- Źródła: `character_creation/boardgame_help.py`,
  `character_creation/physical_mana_help.py`, katalog metod,
  `physical_cards/mana_print.py`, `mana_print_html.py`, `mana_print_files.py`.
  Główne generatory: `scripts/generate_mana_character_prints.py` oraz
  `scripts/build_arena_print_pack.py`; nie edytować tylko starych PDF-ów.
- Przegenerować wszystkie siedem kompletów w czterech formatach, HTML/PDF
  i manifesty oraz zbiorczy pakiet areny i kart. Obliczyć nową liczbę stron,
  zaktualizować aliasy/linki. Kanoniczna lokalizacja pozostaje
  `assets/physical_cards/character_sets/physical_mana_v02/`.
- Odbiór: zgodność treści z runtime, komplet 14 metod, brak obciętych opisów,
  czytelne symbole również w czerni i bieli. Testy `test_mana_character_prints.py`,
  `test_arena_print_pack.py`; kontrola wygenerowanych PDF i widoku pomocy.

### Etap 6 — samouczek w istniejącym stylu Nessy

- Wspólny kurs podstaw eksploracji przechodzimy raz, z możliwością powtórzenia;
  nie powtarzamy pełnej instrukcji dla każdego bohatera.
- Każdy krok: krótkie okno Nessy → ✓ → setup niezbędnej figurki/obiektu i kart
  → jedno polecenie „Teraz zrób” → normalny silnik → wyjaśnienie wyniku → ✓.
- Nowe definicje lekcji eksploracyjnych obok bojowych. Obecny TrainingStep
  wymaga SharedAbility, a configure_walkthrough buduje walkę z kukłami;
  nie podkładać rozmowy jako fikcyjnego ataku. Dodać osobny typ/adapter kroku,
  współdzieląc prezentację i zapis postępu.
- Stabilne id lekcji, wersja kursu i migracja obecnego postępu indeksowego.
  Dopisanie kroku nie może przestawić zaliczenia na inną zdolność. Ukończony
  combat pozostaje ukończony, eksploracja pojawia się jako nowy moduł.

| Lekcja | Czego gracz faktycznie dokonuje |
| --- | --- |
| Pierwsza rozmowa | Wybiera metodę i poznaje automatyczny wybór bohatera oraz jego cechę. |
| Dobór i pas | Fizycznie wybiera jedną z dwóch kart; przy duplikacie odrzuca właściwe karty; pasuje przed ofertą i rzuca k20. |
| Dokładnie 21 | Domyka przygotowaną sumę i widzi sukces bez rzutu. |
| O jeden krok za daleko | Deklaruje dobór przed ofertą, przekracza i wykonuje prawdziwy test z −3; poznaje dalszy przebieg po porażce. |
| Reakcja na poprzednią kartę | W osobnych krótkich próbach poznaje Powtarzasz się i Rozchwianie, z jawną dopłatą. |
| Krótka okazja | Kończy cztery wybory i widzi zwykły wymuszony pas. |
| Obiekt i specjalista | Otwiera skrzynię Eryndem; widzi MDR, biegłość i osobną premię +2. |
| Własna postać | Dwie krótkie próby na bohatera: jego metoda społeczna i obiektowa. Próby podstaw mogą zaliczać odpowiednie id, bez powtarzania tego samego ćwiczenia. |
| Lorian | Końcowy test CHA z Obyciem; osobna możliwość wykonania Improwizacji po rzeczywistej porażce. |
| Pułapka podczas walki | Wykrywa i dezaktywuje pułapkę zwykłymi kośćmi, bez minigry. |
| Samodzielna scena | Wybiera jedną z co najmniej trzech metod dostępnym składem i kończy NPC oraz obiekt bez narzuconych kart. |

Ćwiczenia 21/przekroczenia mają jawnie przygotowane fizyczne kolejności kart,
podobnie jak przygotowana mana w combacie. Nie fałszujemy naturalnych rzutów
gracza ani wyników zasad. Aby uczyć przerzutu Loriana, można przygotować
ST gwarantujący pierwszą porażkę przy danym modyfikatorze i wyraźnie to wyjaśnić;
zaliczenie wymaga wykonania przerzutu, nie jego sukcesu. Ćwiczenie porażki
zalicza poprawne rozstrzygnięcie; tylko lekcje wymagające konkretnego efektu
dają możliwość powtórzenia przygotowanej sytuacji. Reset jest regułą treningu.

- Pliki: `application/training_walkthrough.py`, `ui/training_walkthrough.py`,
  nowe definicje/adaptacje kroków eksploracji, `content/tutorials/walkthrough.json`
  i nowy `content/tutorials/exploration_mana.json`, zapis oraz widok lekcji.
- Odbiór: praktyczne pokrycie wszystkich 14 metod i trzech przeszkód, obu
  pasywów specjalistów, 21, pasu, kary, zwykłych pułapek, kontynuacji i zapisu.
  Testy reguł/zaliczeń oraz przeglądarki w stylu istniejących
  `test_training_walkthrough.py` i `test_training_walkthrough_browser.py`.
  Na fizycznej planszy sprawdzić setup, wejście kolorów, ✓ i odtworzenie stosów.

## 8. Kiedy uznajemy całość za wdrożoną

Obie sceny działają od wyboru do konsekwencji; modyfikatory używają właściwych
cech; zapis nie daje ponownego losowania ani powtórnej nagrody. Pułapka bojowa
ma zwykłe testy. Wszystkie siedem kompletów kart i pomoc pokazują te same
zasady co aplikacja. Samouczek pozwala każdą nową zasadę wykonać i wznowić.
Sprawdzenie samych dokumentów nie zalicza etapów wykonawczych.

Walidacja implementacji: małe, pojedyncze partie przez
`scripts/safe_pytest.sh --timeout 60 <konkretny plik lub node>`; bez równoległych
pytest. Eksporty PDF kolejno; kontrola widoku na komputerze i małym ekranie,
próba na planszy. Bez nowych zależności i bez zmian niskopoziomowego `board/`.

W tym etapie odczytano bieżące statystyki/biegłości siedmiu bohaterów przez
kanoniczny build kart, sprawdzono strukturę generatorów, walkthrough i testów
cech. To przygotowanie planu, nie test działania nowej mechaniki.

Weryfikacja dokumentu: poprawne odnośniki, rachunki obu przykładów i dopłaty
przeszkód; `git diff --check` bez uwag. Istniejące `tests/unit/test_checks.py`
uruchomione przez safe_pytest: **5 testów zaliczonych**. Kontrola dziesięciu
kombinacji dwóch różnych kolorów potwierdza, że pierwszy szablon ma 7 par
z bezpiecznym wyborem przy 20, a trzeci 0; przy 19 trzeci ma 4 pary z kartą
domykającą 21, a pierwszy 0. To sprawdzenie kombinacji, nie pomiar częstości
ofert w zużywanej talii ani pełna kalibracja balansu.

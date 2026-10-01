# Rezonans ciągły — specyfikacja mechaniki

Aktualizacja: 30.09.2026, po akceptacji mocka przez użytkownika.
Status: implementacja Python/UI/LED dla nowych walk Misji 0 i swobodnej areny;
próba na fizycznej planszy pozostaje do wykonania.
[Uruchomienie i test ręczny](playtests/RESONANCE_RUNTIME_MANUAL.md).
Osobny mock `docs/ui/prototype.html` pozostaje materiałem referencyjnym;
[zakres i założenia mocka](ui/RESONANCE_MOCK.md).
Ten dokument zastępuje wcześniejsze zasady paczki wzmacniającej wyłącznie moc,
indywidualnych terminów ochrony i jednorazowej Klepsydry. Źródło opisów na
kartach: `content/print/rune_charges_v02/catalog.json`, model `ongoing_chain_effects`.
Koszty 4/8, 20 ładunków, Skupienie 1k20 i odzysk klasowy 1k4.

## Przegląd pozostałych bohaterów — 29.09.2026

Zakres bieżącego kroku: karty, PDF-y i poniższe notatki do implementacji.
Na etapie przeglądu kart zmiany nie były jeszcze aktywne w silniku ani
makiecie; późniejszy mock z 29.09 opisano w linku powyżej. Nazwy przycisków mocy
zmieniono w katalogu kart, zachowując identyfikatory, runy i koszty.
Karty Erynda zaakceptowano bez zmian.

### ST na kartach i modyfikatory cech

Drukujemy **ST 10 + Siła / Mądrość / Charyzma / Inteligencja**, zamiast
zamrażać bieżący wynik ST 14. Zapis dotyczy również Szarży bastionu:
ST 10 + Siła + liczba przebytych pól. Nazwa cechy w formule oznacza jej
modyfikator, nie pełną wartość cechy. W silniku należy wyliczać bieżące ST
z aktualnej cechy, bez premii biegłości i bez Oka. Wzrost cechy nie wymaga
ponownego drukowania karty. Stała nadal pochodzi z `rules.save_dc_base`.

### Brakka

- **Zaciekłość:** krytyczny atak bronią dodaje **dwie kości obrażeń broni
  zamiast jednej dodatkowej**. Zastępuje wcześniejsze +2 po trafieniu.
  Przykład dla broni 1k12 + Siła: krytyk daje 3k12 + Siła. Nie dodawać
  modyfikatora trzy razy ani naliczać jednocześnie starej premii +2.
  Pasyw dotyczy ataków bronią, także w mocach i reakcjach; nie czarów.
  Dodatkowe kości pasywu są kośćmi broni, nie Szału ani Grota. Przed
  kodowaniem rozpisać osobno przykład broni z bazowym 2k6, aby nie pomylić
  dwóch pojedynczych dodatkowych kości z potrojeniem całej puli obrażeń.
- **Runiczny szał:** aktywacja S; +1k6 do obrażeń trafienia bronią wręcz
  oraz połowa otrzymywanych obrażeń obuchowych, kłutych i ciętych.
  Czas: mod. Siły + mod. Kondycji własnych tur, minimum jedna; zachowano
  wliczenie tury aktywacji. Wyliczyć czas przy aktywacji i pokazać licznik
  na widocznym stanie. Zachowano brak ponownej aktywacji podczas trwania
  oraz możliwość wcześniejszego zakończenia przez Głód walki.
- **Pęd gromu:** bez zmian, A+S, do 3 pól ruchu i atak wręcz, okazyjne
  normalnie. Zapis użytkownika „niech będzie” odczytano jako akceptację.
- **Echo gromu** (`roar`, wcześniej Echo grozy): obrona Mądrości przeciw
  ST 10 + Siła; pozostałe efekty i zasięg bez zmian. Nazwę „Ego gromu”
  odczytano jako „Echo gromu”.

### Mira — ukrycie, ataki i pasyw

- **Cios z zaskoczenia:** +1k6 do trafienia, jeśli Mira flankuje cel ze
  swoim sojusznikiem albo jest ukryta przed tym konkretnym celem.
  Zachowano dotychczasowy limit raz we własnej turze. Samo posiadanie
  przewagi z innego źródła nie wystarcza. Na nowej karcie nie ma wymogu
  subtelnej broni ani osobnej blokady premii przy utrudnieniu.
- **Ostrze zmierzchu:** legalny cel to wróg w zasięgu broni, który nie
  widzi Miry. Atak bronią z przewagą, ujawnienie po rozpatrzeniu ataku,
  również po pudle. Sprawdzić pasyw i efekty ataku z ukrycia na stanie
  sprzed ujawnienia. Nie oferować tej mocy przeciw wrogowi, który widzi Mirę.
- **Całun cienia:** jeden test Zręczności (k20 + modyfikator), porównany
  osobno z pasywną Percepcją każdego wroga. Ukrycie przed danym wrogiem
  wymaga wyniku większego od jego wartości. Zachować relacje per obserwator.
  Nie wymagać osłony i nie odrzucać próby na otwartej przestrzeni. Ogólny
  kod widoczności nie może natychmiast kasować tak uzyskanego ukrycia
  wyłącznie z powodu braku przeszkody. UI pokazuje, przed kim Mira jest ukryta.
- **Notatka tylko do mechaniki mapy, nie na kartę:** głaz, worki czy
  skrzynia mogą zapewniać premię do testu ukrycia. Wartości mają pochodzić
  z danych elementu mapy; nie wymyślono teraz stałej premii ani wymogu
  posiadania takiego elementu obok postaci.

### Parkour — wybór wroga, pola i drogi

Parkour zastępuje Krok widma; id `guard_vault`, runa Schody, S, koszt 4/8.
To ruch w ramach mocy, nie teleportacja i nie zużycie zwykłej puli ruchu.

1. Podświetl wrogów w odległości do **4 pól od Miry**, mających co najmniej
   jedno wolne, legalne sąsiednie pole. Odległość liczymy jak na planszy,
   z przekątną jako jednym polem. Limit czterech pól dotyczy wroga,
   nie końcowego pola Miry: pole po dalszej stronie wroga może być dalej.
2. Kliknięcie wroga wybiera cel. Następnie podświetl jego wolne legalne
   pola sąsiednie. Cel końcowy musi leżeć na planszy, poza panelem,
   mieścić figurkę i nie być zajęty ani zablokowany.
3. Kliknięcie jednego z tych pól wyznacza i pokazuje najkrótszą drogę,
   ignorując przeszkody i figurki wrogów po drodze. Nie stosować starego
   limitu 3 pól, wymogu widoczności celu ani zakazu minięcia muru.
   Ignorowanie przeszkód po drodze nie pozwala skończyć na przeszkodzie.
   Przy kilku równych drogach podgląd ma być deterministyczny.
4. Gracz przesuwa figurkę Miry na wybrane pole, zgłasza pole docelowe
   i zatwierdza ✓. Do tego momentu wybory są podglądem; zmiana pola lub
   powrót nie wydają ładunków ani S i nie uruchamiają reakcji.
5. Po potwierdzeniu ponownie sprawdź legalność, opłać moc raz i rozpatrz
   faktyczne przejście po pokazanej drodze. **Okazyjne oceniać po drodze,
   nie tylko między początkiem a końcem.** Reakcje stosują normalny
   zasięg, widoczność i dostępność reakcji danego wroga.
6. Mira ignoruje okazyjne **od tych przeciwników, przed którymi jest ukryta**.
   Wróg, który ją widzi, nadal może reagować. Nie zastępować tego jedną
   globalną flagą „ukryta przed kimkolwiek”. To przyjęte rozumienie końcowego,
   dwukrotnie zaprzeczonego zdania użytkownika o okazyjnych.
7. Samo użycie Parkouru nie ujawnia automatycznie Miry. Jeśli reakcja
   przerwie ruch, aplikacja wskazuje rzeczywistą pozycję zatrzymania
   i prosi o korektę fizycznej figurki. Powtórzone ✓ nie rusza jej drugi raz,
   nie wydaje kolejnych ładunków i nie ponawia reakcji.

Zapisać wybranego wroga, pole, drogę, fazę potwierdzenia, opłatę i kolejkę
reakcji. Wczytanie w podglądzie nie rozpatruje ruchu; wczytanie po opłacie
kontynuuje tę samą akcję. Koszyk starszego profilu nie jest źródłem tej reguły.

### Więzy mroku

Dowolna broń wręcz, A+S. Trafienie zadaje obrażenia broni i zmniejsza
liczbę punktów ruchu celu o połowę do końca jego następnej tury.
Jeśli trafienie nastąpiło z ukrycia **przed tym celem**, dodatkowo odbiera
mu ruch **w następnej rundzie**. Nie wystarczy ukrycie przed innym wrogiem.
Pudło nie nakłada żadnego z efektów.

Na karcie zachowano wskazane przez użytkownika „w następnej rundzie”,
nie zamieniono tego na „do końca następnej tury”. Docelowo są to dwa
oddzielne terminy: połowa ruchu do końca następnej tury celu i blokada
zaplanowana na całą rundę R+1, gdzie trafienie nastąpiło w R. Pokazywać
zapowiedzianą blokadę w stanie celu, a przy początku R+1 ustawić jego ruch
na 0. Nie jest to Powalony: nie dodawać premii do ataków ani zabierać
celowi ataku, specjalnej lub przedmiotu. Reguły wymuszonego przesuwania
pozostają odrębne od własnego ruchu celu.

### Dagna

Płomień świtu: obrona Zręczności przeciw **ST 10 + Mądrość**.
Pozostałe zasady i opisy Dagny bez zmian.

### Lorian — Hymn odwagi

- Usunięto wyjątek treningowy ze skazy Potrzeba publiczności. Jej zwykły
  warunek i dopłata pozostają. Dysonans drukuje **ST 10 + Charyzma**.
- Hymn daje wybranemu sojusznikowi jedną kość **1k6 do wybranego rzutu k20**:
  ataku, testu cechy lub rzutu obronnego. Cel i zasięg pozostają jak na karcie.
- Kość trwa **bezterminowo, do wykorzystania**, także poza następną turą
  Loriana i poza aktualnym Rezonansem. Nie resetować jej automatycznie na
  granicy rundy, walki, odpoczynku ani przy zapisie. Na bohaterze widoczny
  stan „Hymn odwagi · 1k6”. Zachować źródłowego Loriana dla wyzwalaczy odzysku.
- Limit **jednego niewykorzystanego Hymnu na bohatera**. Kolejne użycie
  nie może tworzyć stosu kości. UI nie pozwala wybrać takiego celu ponownie
  i nie pobiera kosztu za niedozwolone przyznanie drugiej kości.
- Po nieudanym rzucie k20 aplikacja pyta odbiorcę: **„Czy chcesz dodać
  1k6 z Hymnu odwagi do wyniku?”** z wyborami „Użyj Hymnu” i „Zachowaj”.
  Jest to decyzja po obliczeniu pierwotnego wyniku, ale **przed końcowymi
  skutkami porażki**. Nie zadawać wcześniej obrażeń ani nie domykać akcji.
- Odmowa zachowuje Hymn i kończy rzut z pierwotnym wynikiem. Zgoda zużywa
  kość, przyjmuje rzut 1k6 gracza, dodaje go do sumy i ponownie ocenia sukces.
  Kość zostaje zużyta także wtedy, gdy bonus nie wystarczył. Nie powtarzać k20.
  Premia nie zmienia naturalnego wyniku kości ani zasad krytyków.
- Ponieważ gracz wybiera rzut k20, umożliwić świadome użycie także w podglądzie
  rzutu bez binarnego wyniku sukces/porażka; automatyczne pytanie jest pomocą
  po porażce, nie zawężeniem Hymnu wyłącznie do ataków.
- Zachować pending wynik k20, jego ST/KP, decyzję i ewentualny rzut 1k6
  w zapisie. Powtórzona akceptacja lub odświeżenie nie zużywa kości ponownie
  ani nie dodaje kolejnego 1k6. Wspólna obsługa obejmuje rzuty w walce
  i pozostałe rzuty k20 bohatera, gdy zostanie podłączona do aplikacji.

Pierwszy warunek odzysku klasowego Loriana nadal mówi o **udanym ataku**
sojusznika z Hymnem. Poszerzenie użycia Hymnu na inne k20 samo w sobie
nie poszerza tego wyzwalacza; rzut obronny z Hymnem nie włącza odzysku.

### Nimra — Precyzyjny splot i obszary

- **Precyzyjny splot:** po wskazaniu obszaru zatrzymaj przepływ i wyraźnie
  zapytaj o pominięcie celu: „Wskaż pole stworzenia do pominięcia albo
  wybierz Nie pomijaj”. Pokaż obszar i legalne pola jego uczestników.
- Wybór pola wskazuje jedno stworzenie objęte mocą; UI pokazuje jego
  nazwę jako pomijaną. Osobna opcja **„Nie pomijaj”** zatwierdza brak wyjątku,
  również gdy nie ma nikogo do pominięcia. Wymagana jest jawna decyzja,
  nie automatyczny wybór sojusznika ani domyślne pominięcie pierwszego celu.
- Dopiero po tej decyzji zatwierdzać moc i wykonywać obrony/obrażenia.
  Pominięty cel nie otrzymuje żadnego efektu mocy, nie rzuca obrony i nie
  trafia do kolejki Haka ani licznika zranionych celów dla odzysku klasowego.
- Powrót do wyboru obszaru czyści poprzedni wyjątek i ponawia pytanie.
  Przed opłatą anulowanie niczego nie wydaje. Zapis przechowuje obszar,
  wybranego uczestnika albo jawne „brak” oraz fazę potwierdzenia.
- **Fala uderzeniowa** (`force_wave`, wcześniej Fala odrzutu): obrona Siły,
  **ST 10 + Inteligencja**; 2k6 siłowych, połowa przy sukcesie. Dotychczasowi
  wrogowie do 2 pól od Nimry pozostają obszarem; pokaż go, potem zapytaj
  o Precyzyjny splot. Nie dodawano nowego efektu odrzucenia.
- **Strefa ognia** (`flame_fan`, zamiast Wachlarza płomieni): gracz wybiera
  **środek do 6 pól**, a podgląd pokazuje kwadrat **3×3** wokół tego pola,
  wraz z przekątnymi. Limit zasięgu odnosi się do środka, nie wszystkich
  dziewięciu pól. Końcową listę pól filtrują zwykłe zasady legalności planszy.
  Po wybraniu środka następuje osobny wybór Precyzyjnego splotu.
- Strefa obejmuje wszystkich w obszarze, także sojuszników, poza świadomie
  pominiętym stworzeniem. Obrona Zręczności przeciw **ST 10 + Inteligencja**;
  porażka 2k6 ognia, sukces połowa; jeden wspólny rzut obrażeń. Pozostaje
  jednorazowym efektem mocy — sama nazwa nie tworzy trwałej strefy ani
  dodatkowych obrażeń okresowych.

### Testy akceptacyjne następnego kroku

- Krytyk Brakki: dwie dodatkowe kości broni, modyfikator raz; zwykłe
  trafienie bez starego +2. Szał: 1k6 na trafienie wręcz, połowa tylko
  trzech wskazanych typów obrażeń, poprawny licznik własnych tur i skaza.
- ST rośnie wraz z cechą, bez zmiany druku. Używa modyfikatora, nie
  wartości cechy, Oka ani biegłości.
- Mira: przewaga bez flanki/ukrycia nie wyzwala pasywu; ukrycie przed
  jednym wrogiem nie działa przeciw innemu. Ostrze ujawnia po ataku,
  także po pudle; premię ukrycia sprawdza przed ujawnieniem.
- Całun działa bez przeszkody i ma różne wyniki per obserwator;
  konfigurowana premia mapy zmienia test, nie tekst karty ani legalność próby.
- Parkour: wróg do 4 pól z przynajmniej jednym wolnym polem; odrzuć cel
  całkiem otoczony. Dalsze pole może być odległe o 5 od Miry. Podgląd
  przecina przeszkody i wrogów, nie kończy na nich; zmiana wyboru jest darmowa.
- Parkour: tylko wrogowie widzący Mirę reagują na przejście; testować
  mieszaną widoczność, przerwanie ruchu, wczytanie oraz powtórzone ✓.
- Więzy: każda broń wręcz; pudło niczego nie nakłada; połowa ruchu i
  blokada następnej rundy mają własne terminy, także przy granicy rundy.
- Hymn: nieudany atak, test i obrona; odmowa zachowuje kość, użycie
  rozlicza ją raz, niewystarczający bonus też ją zużywa. Brak wygaśnięcia
  i brak drugiego Hymnu na postaci. Sukces ataku dopiero po 1k6 uruchamia
  właściwy odzysk Loriana; udana obrona z Hymnem nie uruchamia go.
- Nimra: wybór pola albo „Nie pomijaj”, powrót i nowy obszar, zapis
  przed/po decyzji, brak obrażeń i wyzwalaczy na pominiętym celu.
  Strefa ognia: 9 pól dla środka wewnątrz planszy, zasięg środka i rzut
  wspólny; przy krawędzi brak wyjścia poza legalną planszę.

## Przegląd Garrana — 27.09.2026

Poniższe reguły dotyczą profilu ładunków. Opisy kart i nowy silnik korzystają
z tego samego katalogu; stare zapisy koszyków zachowują swój wcześniejszy profil.

### Żywa osłona i odzysk

- Tarcza w ręce Garrana: przytomny sojusznik na sąsiednim polu otrzymuje
  widoczny stan **Żywa osłona · +1 KP**, ze źródłem Garran. Garran sam nie
  otrzymuje stanu ze swojego pasywu. Stan musi wpływać na rzeczywistą KP celu.
- Stan jest wyliczany z bieżącego wyposażenia, pozycji i przytomności
  odbiorcy. Odświeżać po ruchu obu postaci, przesunięciu wymuszonym, zmianie
  tarczy, utracie/odzyskaniu przytomności i wczytaniu zapisu. Wyjście z
  sąsiedztwa lub brak tarczy usuwa ten stan i jego premię. Nie usuwa premii Wieży.
- Stan jest widoczny w informacjach chronionej postaci i przy podglądzie
  ataku na nią. Kolejne odświeżenia nie tworzą dodatkowych kopii premii.
- Garran odzyskuje **1k4 ładunków**, gdy przeciwnik chybi atakiem w niego
  albo w sojusznika objętego w tej chwili Żywą osłoną. Impuls egidy nie
  uruchamia już odzysku za zadanie obrażeń.
- Oba warunki współdzielą dotychczasowy limit raz na rundę, do 20 ładunków.
  Z kart wszystkich postaci usunięto długi wspólny dopisek o rozliczaniu
  odzysku; nie zmienia to limitu w zasadach ani katalogu.

### Impuls egidy

Pozostaje specjalną S z tarczą przeciw sąsiedniemu wrogowi. Test Siły
Garrana przeciw Sile albo Zręczności celu (wyższa premia); wygrana daje
1k6 + modyfikator Siły obrażeń obuchowych. Remis i przegrana nie dają efektu.

Po wygranej i rozliczeniu obrażeń aplikacja podświetla wszystkie legalne
pola **w odległości 1 od pola przeciwnika**, również po przekątnej. Kierunek
nie musi prowadzić prosto od Garrana. Wykluczone są pola zajęte, zablokowane,
panel i pola poza planszą. Obowiązują przeszkody uniemożliwiające przesunięcie
oraz odporność na wymuszony ruch. Brak legalnego pola nie cofa obrażeń.

Kliknięcie pola wybiera podgląd; kolejny wybór zmienia podgląd. Dopiero ✓
zatwierdza pozycję i pozwala przestawić figurkę. Powrót przed zatwierdzeniem
czyści wybór, nie powtarza obrażeń ani opłaty. Przesunięcie nie zużywa ruchu
celu ani nie prowokuje ataków okazyjnych. Ponowiona akceptacja jest bezskuteczna.
Interakcję z dodatkowym Hakiem rozpatrujemy kolejno: najpierw odrzucenie mocy,
potem Hak liczony od nowej pozycji. Każdy etap ma własny podgląd i zatwierdzenie.

### Ostrze przełamania i Żar odnowy

Ostrze przełamania zachowuje A+S i atak bronią wręcz. Trafienie: obrażenia
broni oraz osobny składnik **1k6 obrażeń magicznych**, zamiast dodatkowych
obrażeń fizycznego typu broni. Całość jest jednym trafieniem; bonus Grota
nie nalicza się ponownie za sam dodatkowy składnik.
Żar odnowy pozostaje bez zmian: S, 1k10 + poziom PW, do maksimum.

### Szarża bastionu (zamiast Ścieżki przysięgi)

Identyfikator nowej mocy: `bastion_charge`, runa Schody, koszt 4/8,
budżet **M+S**: specjalna i cała akcja ruchu, bez zużywania zwykłego ataku.

1. Garran musi mieć dostępny ruch i specjalną, pełną aktualną pulę ruchu
   oraz nie wykonać wcześniej własnego ruchu w tej turze, także z mocy.
   Powrót na pole startowe lub późniejsze dodanie punktów nie przywraca
   uprawnienia. Uwzględniać limit po skazie, stanach i aktywnych Schodach.
2. Podświetl legalnych wrogów, obok których Garran może stanąć po legalnej
   drodze w swoim budżecie. Nie wystarczy sam dystans w linii prostej:
   przeszkody, zajętość, narożniki i trudny teren nadal obowiązują.
3. Kliknięcie pola wroga wybiera cel i uruchamia podgląd. Aplikacja wybiera
   **najbliższe Garranowi osiągalne, legalne pole sąsiadujące z tym wrogiem**
   i pokazuje je na niebiesko. Przy remisie zachować stałą kolejność pól;
   podgląd nie może losowo zmieniać miejsca przy odświeżeniu.
4. Podsumowanie pokazuje cel, docelowe pole, drogę, liczbę przebytych pól,
   ST i koszt wybranego trybu. Zmiana celu przelicza podgląd. Przed ✓
   nie ma opłaty, przestawienia ani rzutu. Zatwierdzenie ponownie sprawdza
   legalność; nieaktualny podgląd wraca do wyboru bez utraty zasobów.
5. Po ✓ zużyj S i całą akcję ruchu; gracz stawia Garrana na niebieskim polu.
   Ruch jest rozpatrywany jak normalny ruch po pokazanej drodze, również
   wobec ataków okazyjnych. Pozostałe punkty ruchu wynoszą **0**, niezależnie
   od długości szarży. Wzmocnione Schody wchodzą przed mocą i także zostają
   zużyte przez koszt całego ruchu. Nie zostawiają punktów po szarży.
6. Po dotarciu wróg wykonuje rzut obronny **Kondycji** przeciw
   **ST = 10 + modyfikator Siły Garrana + liczba faktycznie przebytych pól**.
   Zachowano bazę ST 10 z pozostałych mocy. Przykład: Siła +4 i droga
   długości 3 pól daje ST 17. Liczymy kroki drogi, nie koszt trudnego terenu;
   przekątna to jeden krok. Oko nie zwiększa ST. Przerwanie szarży przed
   dotarciem nie nakłada Powalonego.
7. Nieudana obrona nakłada stan **Powalony**. Udana obrona nie nakłada stanu;
   ruch i koszt pozostają zużyte. Szarża sama nie zadaje obrażeń.

### Powalony — wspólna zasada nowego profilu

- Ataki **wręcz** przeciw powalonemu mają przewagę (2k20, wybierz wyższy).
- Ataki **dystansowe** przeciw powalonemu otrzymują **−2 do testu ataku**,
  a nie utrudnienie. Rozróżnienie wynika z rodzaju ataku, nie dystansu.
- Powalony traci całą akcję ruchu w swojej następnej turze. Nadal może
  zaatakować i użyć dostępnej akcji specjalnej albo przedmiotu zgodnie
  ze zwykłą ekonomią tury. Sam stan nie zabiera mu tych działań.
- Przyjęty moment wstania: początek następnej tury powalonego. Wstanie
  zużywa cały ruch, usuwa stan i kończy premie do ataków przeciw niemu;
  nie ma opcji wstania za połowę ruchu. Zapisać osobno utratę ruchu w tej
  turze, aby późniejsze premie nie oddały już zużytej akcji ruchu.
- Powtórne nałożenie przed tą turą nie sumuje kar ani kolejnych utraconych
  tur. Stan ma być widoczny przy postaci i uwzględniany w podglądach ataków.

### Przypadki akceptacyjne do wdrożenia walki

- Wejście/wyjście z sąsiedztwa Garrana i utrata tarczy aktualizują stan
  oraz KP chronionego; powtórne odświeżenie nie zwiększa premii.
- Pudło w Garrana i pudło w chronionego sojusznika korzystają z jednego
  limitu 1k4; trafienie Impulsem nie wyzwala odzysku.
- Impuls: wybór bocznego pola, brak wolnego pola, zmiana podglądu,
  powrót i podwójne ✓; obrażenia oraz opłata rozliczają się raz.
- Ostrze: fizyczne obrażenia broni i magiczna dodatkowa kość są osobnymi
  składnikami jednego trafienia. Żar nadal leczy 1k10 + poziom.
- Szarża: blokada po wcześniejszym ruchu, także powrocie na pole startowe;
  przeciwnik odcięty ścianą nie świeci; wybierane pole jest wolne i najbliższe.
- Podgląd szarży nie zużywa zasobów; akceptacja zeruje ruch, wydaje S
  i ładunki raz. Atak pozostaje dostępny. Przykład drogi 3 pól daje ST 17.
- Powalony: przewaga wręcz, −2 dystansowo, następna tura bez ruchu,
  ale z atakiem i specjalną/przedmiotem; brak utrudnienia do własnego ataku.
- Zapis/odczyt podczas wyboru celu lub podglądu zachowuje kolejność,
  naliczone koszty, statusy i znacznik ruchu wykonanego w turze.

## Rzuty i ST bez premii biegłości

W obecnym kierunku nie dodajemy premii biegłości do rzutów bohaterów.
Rzut: k20 + modyfikator właściwej cechy + odpowiednie aktywne premie (np. Oko).
ST mocy: **10 + modyfikator cechy wskazanej na karcie**. Oko nie zwiększa ST.
Stała 10 zastępuje dawny zapis 8 + biegłość (+2 u obecnych bohaterów), więc
korekta nie zmienia ich aktualnych liczbowych ST. Nie przywraca dawnych premii
od poziomu naładowania. Biegłość jako uprawnienie do sprzętu jest odrębną sprawą.
Źródło stałej dla wydruku i wyliczeń: `rules.save_dc_base` w katalogu kart.

## 1. Tor i uczestnicy

- Nieaktywny Rezonans: `null`, pusty tor i brak uczestników.
- Tor jest **uporządkowaną listą** dodanych run. Liczniki bez historii nie wystarczą,
  ponieważ Fala korzysta z poprzedniego wpisu.
- Bohater rozpoczynający turę przy aktywnym Rezonansie dołącza do niego **przed
  pierwszym działaniem**. Od razu otrzymuje odpowiednie premie.
- Zatwierdzony wybór mocy wzmocnionej dodaje runę **przed** efektami i rzutami
  mocy. Jeśli tor był pusty, tworzy łańcuch, a wykonujący od razu dołącza.
- Bohater, który jeszcze nie zaczął tury w tym łańcuchu, nie ma premii. Uczestnik
  zachowuje je poza swoją turą, aż do wspólnego zakończenia Rezonansu.
- Tura wroga i granica rundy niczego nie zerują. Brak zasięgu pomiędzy
  uczestnikami, kosztu reakcji ani limitu długości toru.
- Zwykły atak, ruch, przedmiot, reakcja i obrażenia okresowe mogą korzystać
  z odpowiednich premii. Nie dodają samodzielnie runy.

**Przykład wiążący:** Garran dokłada Wieżę do pustego toru. Dostaje +1 KP
przed wykonaniem mocy. Drugi bohater na początku swojej tury również dostaje
+1 KP. Garran nadal ma premię. Trzeci bohater jeszcze jej nie ma. Jeśli drugi
zakończy Rezonans, obaj tracą +1 KP; trzeci zaczyna turę bez premii.

### Wzrost toru a wcześniejsi uczestnicy — doprecyzowanie robocze

Użytkownik został zapytany, czy nowa runa podnosi premie również wcześniejszym
uczestnikom. Do potwierdzenia przyjęto **bieżące liczniki dla wszystkich już
objętych Rezonansem**: druga Wieża zmienia +1 na +2 także u Garrana.
Nie obejmuje to postaci, które jeszcze nie dołączyły.
Jednorazowego leczenia Błysku nie rozsyłamy przy tym poza turą: nową kość rzuca
wykonujący; inni uczestnicy rzucą pełną aktualną pulą na początku swoich tur.

## 2. Zatwierdzenie, rozpatrzenie i zakończenie

Docelowy przebieg: moc → cel → wybór trybu → podsumowanie → zatwierdzenie trybu
→ opłata i dopisanie runy → premie aktywacji → rzuty/obrażenia → Hak → wynik.
To techniczne rozumienie „od wyboru wersji wzmocnionej”: efekt jest aktywny
przed mocą, a nie dopiero po niej. Podgląd wariantu może pokazać przyszłe wartości,
ale nie pozwala leczyć się ani zwiększać puli przez wielokrotne otwieranie okna.
Po opłaceniu i aktywacji anulowanie nie może zwracać kosztu przy zachowaniu premii.

Zakończenie wspólnego łańcucha następuje:

1. Po pełnym rozpatrzeniu mocy podstawowej, włącznie z kolejką Haka i wynikiem.
2. Przy zatwierdzonym Skupieniu, przed jego odzyskiem ładunków.
3. Na końcu tury bohatera bez kontynuującej mocy.
4. Na końcu walki.

Zakończenie czyści tor, uczestników i **wszystkie czasowe efekty tego łańcucha**:
KP Wieży, dodatkowe kości Grota, Oko, niewydany ruch Schodów, liczniki Kielicha
i Klepsydry oraz globalne spowolnienie Węzła. Fala nie ma niezależnego czasu
trwania — jej kopia znika wraz z łańcuchem.
Nie cofamy otrzymanych/zadanych obrażeń, odzyskanych zwykłych PW ani przesunięć.
Błysk na początku tury leczy również gracza, który potem zdecyduje się wygasić
Rezonans; wykonane leczenie pozostaje. Pasyw Loriana sprawdza stan sprzed
zamknięcia, żeby rozpoznać użycie mocy podstawowej z aktywnym Rezonansem.

## 3. Runy

`N` = efektywna liczba kopii runy w aktywnym Rezonansie, z uwzględnieniem Fali.

| Runa | Moment i dokładny efekt | Koniec / kumulowanie |
| --- | --- | --- |
| Wieża | Uczestnik ma +N KP od dołączenia, także przed swoją mocą i poza turą. | Do końca łańcucha. Nie tworzyć osobnych premii z poprzednich tur. |
| Grot | +Nk4 do każdego zdarzenia obrażeń, którego źródłem jest objęty efektem bohater, osobno na każdy cel. Także zwykłe ataki, reakcje, pułapki i efekty okresowe z przypisanym źródłem. | Sprawdzać uczestnictwo w chwili zadawania obrażeń, nie tylko w chwili rzucania czaru. Nie stosować po końcu łańcucha. |
| Schody | Na początku własnej tury +2N tymczasowych punktów zwykłego ruchu. Nowa kopia w tej turze dodaje +2. | Trudny teren i ataki okazyjne normalnie. Niewydana część znika z końcem tury lub Rezonansu; następna tura wylicza nową pulę. |
| Błysk | Na początku własnej tury rzut Nk4 leczenia własnych PW. Nowy Błysk w tej turze daje tylko dodatkowe 1k4. | Do maksimum PW. Nie ponawiać starych kości przy dokładaniu runy. Zakończenie zatrzymuje przyszłe wyzwolenia, nie cofa leczenia. |
| Hak | Po obrażeniach: każdy legalny zraniony cel można raz przenieść na legalne pole w odległości do N od jego pola. Zostawienie w miejscu jest legalne. | Dystans rośnie, liczba przeniesień na cel nie. Cała grupa obrażeń przed pierwszym przeniesieniem. Szczegóły w sekcji 5. |
| Oko | +N do wszystkich własnych rzutów k20 objętego bohatera, także poza turą. | Bez podbijania ST. Nie zmienia naturalnego wyniku. Przy przewadze/utrudnieniu premia raz do wybranej kości. |
| Kielich | Oddzielne tymczasowe PW: maksimum 2N, początkowo pełne. Obrażenia schodzą z nich przed zwykłymi PW. | Utrata tymczasowych PW to obrażenia, może odpalać efekty „po zadaniu obrażeń”. Pozostała pula i maksimum znikają na końcu łańcucha. |
| Węzeł | Wszyscy przeciwnicy mają spowolnienie N: limit zwykłego ruchu −N pól, minimum 0, po innych zmianach limitu. | Bez testu, trafienia i ograniczenia dystansem. Także nowi przeciwnicy. Usunąć po zakończeniu Rezonansu. |
| Fala | Dodaje jedną efektywną kopię poprzedniej runy na torze. Nie podwaja jej dotychczasowego licznika. | Kopia podlega wszystkim zasadom tej runy, również dodatkowej kości Błysku i punktom Schodów. |
| Klepsydra | Oddzielna osłona o maksimum 2N; zapobiega obrażeniom oprócz umysłowych (psychicznych). Przed tymczasowymi i zwykłymi PW. | Zużywalna pula na wiele trafień. Całkowita prewencja nie odpala „po zadaniu obrażeń”. Cała pula znika na końcu łańcucha. |

„Początek rundy” dla Błysku interpretujemy z przykładu użytkownika jako
**początek tury danego bohatera**, nie jedno wspólne leczenie drużyny co rundę.
Wartości +2 ruchu Schodów i 2 punktów Klepsydry zachowano z poprzednich kart.

### Obrażenia Grota

Jedna premia na zdarzenie obrażeń i cel, nie na każdą kość czy składnik tego
samego trafienia. Bonus nie tworzy nowego zdarzenia, więc nie wywołuje sam siebie
ani drugiej kolejki Haka. Pięć trafionych celów obszarówki otrzymuje po +Nk4.
Trzy oddzielne pociski są trzema zdarzeniami i każdy otrzymuje premię.
Podpalenie zadane przez bohatera zachowuje identyfikator źródła; jego kolejne
obrażenia mogą korzystać z aktualnego Rezonansu tego bohatera.
Pozostawione roboczo zasady wcześniejsze: typ obrażeń zgodny ze źródłem,
krytyk podwaja kości trafienia wraz z Grotem, rzut obronny redukuje całość
według reguły mocy. Pudło/udane pełne uniknięcie nie staje się trafieniem.

### Liczniki i brak darmowego odnawiania

Dołączenie do łańcucha następuje raz; kolejne początki tury nie odnawiają
Kielicha ani Klepsydry. Przy wzroście N o 1 roboczo dodajemy 2 do maksimum
oraz 2 do pozostałej puli — bez odnawiania wcześniej zużytych punktów.
Przykład: Kielich 1/2 po nowej kopii to 3/4, nie 4/4.
Po końcu łańcucha liczników nie ma; nowy łańcuch zaczyna własne pełne pule.
Schody mają osobny licznik wydanych punktów, dzięki czemu wygaśnięcie nie
cofa figurki ani nie daje ujemnego ruchu. Roboczo ruch zużywa najpierw premię
Schodów. Węzeł zmienia limit, a nie usuwa informacji o już przebytym dystansie:
`pozostało = max(0, limit po spowolnieniu − wydany ruch)`.

### Fala i kolejność toru — przypadki brzegowe przyjęte roboczo

- `Wieża → Fala`: Wieża ×2.
- `Wieża → Wieża → Fala`: Wieża ×3, nie ×4.
- `Wieża → Fala → Fala`: Wieża ×3. Druga Fala kopiuje efektywny bonus pierwszej.
- `Wieża → Grot → Fala`: Wieża ×1, Grot ×2.
- `Błysk → Fala`: Błysk ×2; aktywny gracz rzuca dodatkowe 1k4, nie całe 2k4 ponownie.
- Fala jako pierwszy wpis: brak poprzednika, brak dodatkowego bonusu;
  podgląd informuje o tym przed opłatą. Nie wybieramy dowolnej runy zastępczej.
- Na torze pozostaje widoczna Fala z oznaczeniem skopiowanej runy.
  Kopiowany efekt zostaje ustalony przy dodaniu wpisu, bez rekurencyjnego przeliczania.

## 4. Kielich, Klepsydra i efekty obrażeń

Docelowy model UI: `PW 15/20 · Kielich 2/2 · Klepsydra 2/2`.
Nie łączyć obu osłon w jeden zasób i nie nadpisywać bieżących zwykłych PW.
Kolejność: obrażenia wraz z Grotem → rzuty obronne/odporności → prewencja
Klepsydry (poza umysłowymi) → tymczasowe PW Kielicha → zwykłe PW.

Dla każdego zdarzenia zachować osobno `prevented`, `temporary_hp_lost`,
`hp_lost`, typ obrażeń i źródło. Warunek „zadano obrażenia” wymaga dodatnich
obrażeń po prewencji, także kiedy są zużywane tylko tymczasowe PW.
Sam fakt trafienia jest osobnym warunkiem: osłona nie zmienia trafienia w pudło.

| Stan i zdarzenie | Wynik | „Po zadaniu obrażeń” |
| --- | --- | --- |
| PW 15/20, Kielich 2/2, brak Klepsydry; 1 obrażenie | PW 15/20, Kielich 1/2 | Tak. |
| PW 15/20, Kielich 2/2, Klepsydra 2/2; 1 fizyczne | PW 15/20, Kielich 2/2, Klepsydra 1/2 | Nie. |
| Ten sam początkowy stan; 3 fizyczne | PW 15/20, Kielich 1/2, Klepsydra 0/2 | Tak — 1 punkt po prewencji. |
| Ten sam początkowy stan; 1 umysłowe | PW 15/20, Kielich 1/2, Klepsydra 2/2 | Tak; pomija Klepsydrę. |
| Koniec Rezonansu | PW pozostają; oba dodatkowe liczniki znikają | Samo zniknięcie liczników nie jest obrażeniami. |

Przy obrażeniach mieszanych osłona pochłania tylko składowe inne niż umysłowe.
Leczenie nie odnawia żadnego z dwóch dodatkowych liczników.

## 5. Hak — kolejka wyborów na planszy

1. Ustal całą grupę trafień/celów i policz obrażenia, w tym Groty oraz prewencję.
2. Zbuduj stabilną listę różnych legalnych przeciwników zranionych w tej grupie.
   Trafienie pochłonięte całkowicie przez prewencję nie uruchamia Haka;
   utrata tymczasowych PW kwalifikuje cel. Nie przenosimy usuniętych z planszy figurek.
3. Komunikat: **„Rezonans runy Hak: przenieś [nazwa przeciwnika] i potwierdź.”**
4. Podświetl legalne docelowe pola w odległości do N **od pola tego przeciwnika**,
   łącznie z jego aktualnym polem. Reszta zajętych pól, blokady i panel sterowania
   są wykluczone. Docelowa komórka musi mieścić figurkę zgodnie z regułami planszy.
5. Kliknięcie ustawia podgląd pola i zmienia jego kolor. Inne kliknięcie zmienia
   podgląd, nie zatwierdza. Gracz przenosi figurkę zgodnie z podglądem.
6. Pole akceptacji zatwierdza pozycję. Dopiero wtedy aktualizuj zajętość i przejdź
   do kolejnego celu, ponownie wyliczając jego legalne pola. Aktualne pole + akceptacja
   oznacza pozostawienie przeciwnika na miejscu.
7. Wróć czyści podgląd bieżącego celu. Nie cofa już zadanych obrażeń, zapłaty,
   dopisania runy ani zatwierdzonych przesunięć poprzednich celów.
8. Po ostatnim celu pokaż jedno podsumowanie całej akcji. Dopiero potem można
   domknąć Rezonans mocą podstawową. Ponowne przesłanie akceptacji nie może
   drugi raz przenieść figury ani powtórzyć obrażeń.

Dwa Haki = jeden wybór do 2 pól, a nie dwa wybory po jednym polu. Obszarówka
z pięcioma legalnymi zranionymi celami = pięć kolejnych wyborów po obrażeniach.
Dla wielu trafień w jeden cel w ramach jednej akcji — jeden wybór dla tego celu.
Roboczo odległość to standard planszy (przekątna = 1 pole); przeniesienie
sprawdza pole docelowe, nie koszt marszu po drodze. Nie jest to zwykły ruch,
nie zużywa ruchu przeciwnika i nie prowokuje ataków okazyjnych.
Nie dodawać bonusowych obrażeń od samego przeniesienia.

## 6. Plan stanu i zdarzeń — jeszcze bez implementacji

- `chain_id`, uporządkowane wpisy `{rune, contributor, effective_rune, copied_from}`,
  efektywne liczniki oraz zbiór uczestników z momentem dołączenia.
- Osobisty stan uczestnika: bieżące/maksymalne PW Kielicha i Klepsydry,
  wykorzystana premia ruchu, znacznik rozpatrzonego początku tury Błysku.
- Zdarzenia: `hero_turn_started`, `enhanced_mode_committed`, `rune_added`,
  `source_damage_resolved`, `hook_destination_selected`, `hook_destination_confirmed`,
  `basic_power_resolved`, `focus_committed`, `turn_ended`, `chain_ended`.
- Początek tury i nowy wpis muszą być idempotentne: odświeżenie UI, zapis/odczyt
  lub ponowienie pakietu planszy nie powtarza leczenia, ruchu ani przyznania osłony.
- Źródło obrażeń zapisujemy także dla stanów okresowych i przywołanych efektów.
- Kolejka Haka ma identyfikator akcji, unikalne cele, indeks bieżącego celu,
  zatwierdzone pozycje i osobny podgląd. Stan nadaje się do zapisu w połowie kolejki.
- Modyfikatory oznaczać `chain_id`; wygaszenie nie może usunąć podobnych premii
  z ekwipunku, zwykłych mocy ani innego źródła.
- UI pokazuje tor z kolejnością i licznikami, objętych bohaterów, ich premie,
  ładunki, oba liczniki osłon oraz spowolnienie przeciwników. Obsługa przez planszę.

## 7. Przypadki do przyszłych testów silnika

- Przykład Garrana i drugiego/trzeciego bohatera z sekcji 1; globalne wygaszenie.
- Zwykły atak i obrażenia okresowe źródłowego uczestnika z Grotem; brak premii
  przed dołączeniem/po zakończeniu; brak rekurencyjnych obrażeń.
- Błysk raz na rozpoczęcie własnej tury; dołożenie/Fala daje tylko jedną nową kość.
- Schody: częściowe zużycie, dodanie kopii, wygaśnięcie bez cofania ruchu.
- Wszystkie wiersze tabeli obrażeń, w tym mieszanina fizycznych i umysłowych.
- Węzeł na niezranionych i nowo dodanych przeciwnikach, minimum ruchu 0.
- Fala po zwykłej runie, po Fali i jako pierwszy wpis; kopiuje jedną kopię.
- Hak po obszarówce: wiele celów, jeden cel trafiony kilka razy, zajęte pola,
  pozostanie w miejscu, zmiana podglądu, odświeżenie i ponowienie akceptacji.
- Moc podstawowa rozpatruje obrażenia i Haki przed globalnym zakończeniem.
- Nie resetować osłon przy kolejnym początku tury w tym samym łańcuchu.

## 8. Pozostałe doprecyzowania przed kodowaniem

Powyżej jawnie oznaczono interpretacje robocze: wzrost premii wcześniejszych
uczestników, przyrost zużywalnych liczników, początek tury dla Błysku, brzegowe
Fale oraz legalność przeniesienia przez teren. Ponadto pozostają: pomijana tura
nieprzytomnego bohatera; interakcja Kielicha z tymczasowymi PW spoza Rezonansu;
przypisanie źródła obrażeń przywołań; typ kości Grota przy trafieniu mieszanym.
Nie dopisywać tych decyzji do silnika niejawnie. Następny etap rozmowy:
przegląd każdej postaci, dopiero później wdrożenie walki.

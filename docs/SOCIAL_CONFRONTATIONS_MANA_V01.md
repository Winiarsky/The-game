# Konfrontacje społeczne — dobieranie many do 21

Aktualizacja 2026-09-14: wdrożono moduł eksploracji i lekcje siedmiu postaci.
Przekroczenie daje **utrudnienie (2k20, niższy wynik), bez premii za karty**,
zamiast wcześniejszego −3. [Opis wdrożenia](EXPLORATION_MANA_IMPLEMENTATION.md). Poniżej historyczny projekt.

Aktualizacja: [zbiorcza propozycja i plan 0.2](EXPLORATION_CONFRONTATIONS_MANA_V02_PLAN.md)
przypisuje cechy metodom (w tym KON Zastraszaniu Brakki), proponuje nowe
przeszkody i ujawnienie wybranego profilu po rozpoczęciu. Te zapisy mają
pierwszeństwo przed odpowiadającymi im rekomendacjami v0.1 poniżej.

Status: projekt v0.1, 2026-09-13. Porządkuje propozycję użytkownika; nie jest
wdrożeniem ani zmianą obecnych zasad walki. Sekcje oznaczone „propozycja”
doprecyzowują nierozstrzygnięte reguły i wymagają próby przy stole.

Rozszerzenie na obiekty, zbiorczą rozpiskę czternastu podejść, proponowany
pasyw Erynda i pełne przykłady obu zastosowań zawiera
[Eksploracja z maną — NPC i obiekty](EXPLORATION_CONFRONTATIONS_MANA_V01.md).
Poniższy dokument zachowuje szczegóły procedury społecznej i jej przypadków
brzegowych; reguły nierozstrzygnięte pozostają propozycjami.

## 1. Rdzeń wskazany przez użytkownika

- Konfrontacja z NPC ma konkretny cel i co najmniej trzy autorskie sposoby
  rozwiązania. Różne podejścia mogą dawać różne warunki porozumienia.
- Każde podejście należy do jednego bohatera. Wybór Zastraszania automatycznie
  wybiera Brakkę; nie wybieramy następnie dowolnego wykonawcy.
- NPC ma różną, ukrytą podatność na podejścia. Podatność jest realizowana
  przez rozkład wartości pięciu kolorów many dla danego podejścia.
- Gracz buduje sumę wybranych kart. Dokładnie 21 daje automatyczny sukces;
  wynik poniżej 21 daje premię do testu zależną od bliskości celu.
- Przed każdą nową ofertą gracz wybiera: pas albo dalsze dobieranie.
- Po decyzji o doborze odkrywa dwie karty i wybiera jedną. Jeżeli obie mają
  ten sam kolor, może dobierać dalej do pojawienia się innego koloru.
  Wybrana karta dołącza do budowanej puli, wszystkie pozostałe odkryte karty
  trafiają na odrzucone. To nie jest wybór z pięciokartowego rynku walki.
- Przekroczenie 21 kończy dobieranie i pogarsza końcowy test.
- NPC/podejście może mieć dodatkową przeszkodę, np. zakaz dwóch identycznych
  kolorów z rzędu albo rzut k6 po czerwonej manie, z przerwaniem próby na 1.
- Aplikacja otrzymuje wybrany kolor, decyzję o dalszym doborze lub pasie
  oraz potrzebne wyniki rzutów. Dobieranie fizycznych kart prowadzą gracze.

To zastępuje wcześniejsze pomysły na tory sporu, cel 10 i kartę zabezpieczenia.
Siedem specjalnych sztuczek karcianych z poprzedniej rozmowy pozostaje luźnymi
propozycjami; nie dodajemy ich automatycznie do tego modelu.

## 2. Podejście wybiera bohatera

| Podejście | Stały wykonawca | Sens w fikcji |
| --- | --- | --- |
| Autorytet | Garran | Odpowiedzialność, gwarancje, jasny plan |
| Zastraszanie | Brakka | Presja i postawienie granicy |
| Blef | Mira | Pozory, ukryte zamiary, niepewność rozmówcy |
| Empatia | Dagna | Zrozumienie potrzeb i obaw |
| Inspiracja | Lorian | Nadzieja, duma, poczucie wspólnoty |
| Argumentacja | Nimra | Fakty, dowody i logiczne wyjaśnienie |
| Dociekliwość | Erynd | Pytania, uniki i przemilczane informacje |

Przed rozpoczęciem musi istnieć sensowny, osiągalny cel: np. dodatkowy kurs,
ujawnienie świadectwa, zgoda na wspólne wystąpienie. Dokładnie 21 gwarantuje
ustalony wynik danego podejścia, a nie dowolne późniejsze żądanie wobec NPC.

### Minimum trzech metod a skład drużyny — do rozstrzygnięcia

Obecna gra pozwala wybrać 1–5 spośród siedmiu bohaterów. Przy ścisłym
przypisaniu metoda → bohater drużyna 1–2 postaci nie może mieć trzech
dostępnych metod. Nawet drużyna trzyosobowa może nie mieć autorów trzech
metod wybranych przez twórcę sceny.

Propozycja robocza: minimum trzy metody zapisane w scenariuszu, z czego menu
udostępnia metody obecnych i zdolnych do działania bohaterów. Nie podstawiamy
innego wykonawcy. Trzeba osobno sprawdzić każdy wspierany skład: przy braku
dopasowania zapewnić dodatkowe autorskie podejście lub drogę fabularną poza
konfrontacją. Sama liczba trzech zapisanych metod nie gwarantuje grywalności.

Jeśli minimum trzech ma dotyczyć zawsze aktywnego menu, trzeba ograniczyć
liczbę/skład drużyny albo zmienić wyłączność metod. Dla dowolnych trzech
bohaterów gwarancja trzech opcji wymaga obsługi wszystkich siedmiu podejść.

## 3. Rozkład wartości: NPC × konfrontacja × podejście

Rozkład należy do konkretnego podejścia w danej sytuacji. Ten sam NPC może
inaczej reagować na zastraszanie przy swoich podwładnych i podczas prywatnej
rozmowy. Profil zostaje ustalony przed rozpoczęciem próby i nie zmienia się
potajemnie w odpowiedzi na dobierane karty.

Przykład użytkownika:

| Kolor | Podatność na zastraszanie | Odporność na zastraszanie |
| --- | ---: | ---: |
| Czerwona | 7 | 7 |
| Biała | 1 | 6 |
| Zielona | 1 | 5 |
| Czarna | 3 | 3 |
| Niebieska | 5 | 2 |

Pierwszy profil daje więcej drobnych kroków. Jego średnia wartość karty to
3,4; drugiego 4,6. To trafniejsze określenie niż „bardziej płaski rozkład”.

Niższa średnia nie gwarantuje łatwiejszego trafienia dokładnie 21 w każdym
stanie. Przy sumie 20 pierwszy profil ma dwie barwy pozwalające wygrać,
a drugi żadnej. Przy sumie 19 drugi profil pozwala skończyć niebieską dwójką,
a pierwszy potrzebuje jeszcze dwóch jedynek. Profil trudności trzeba oceniać
łącznie z doborem dwóch kolorów, zapasem kart, wiedzą graczy i przeszkodami.

Kontrola liczbowa pojedynczej oferty: przy jednakowej dostępności wszystkich
pięciu barw istnieje dziesięć jednakowo prawdopodobnych par różnych kolorów.
Przy sumie 20 profil podatny daje bezpieczny wybór w 7/10 par, odporny w 0/10.
Przy sumie 19 możliwość natychmiastowego 21 występuje odpowiednio w 0/10
i 4/10 par. To nie są szanse wygrania całej konfrontacji ani prognoza przy
wyczerpanej, nierównomiernej talii.

## 4. Ukryta podatność i świadomy wybór — propozycja

Pewne jest, że gracz nie dostaje etykiety „podatny/odporny” ani oceny szans
przed wyborem podejścia. Moment ujawniania wartości kolorów pozostaje do decyzji.

Propozycja robocza: nieznany kolor pokazuje „?”. Po jego pierwszym zatwierdzeniu
aplikacja ujawnia dodaną wartość i zapamiętuje ją w tej konfrontacji. Znane
wartości pozostają widoczne przy kolejnych wyborach. Suma i bieżąca premia są
zawsze jawne; ich przyrost i tak ujawnia wartość wybranej karty.

Dzięki temu początek zawiera rozpoznanie, a późniejsze decyzje korzystają
z poznanych wartości. Ukrywanie wartości również po użyciu nie zapewnia
rzeczywistej tajemnicy, tylko wymaga pamiętania różnic sum.

Alternatywa: ujawnić całą tabelę po zatwierdzeniu podejścia. Nadal nie można
porównać profili przed wyborem, ale od pierwszego doboru gra się pełną informacją.
Nie należy przedstawiać tego wariantu jako już wybranego przez użytkownika.

Widoczne zachowanie NPC może dawać wskazówkę fabularną. Generał nie musi być
automatycznie odporny na wszelką presję; treść sceny opisuje jego konkretne
interesy. Dodatkowe mechaniczne zakazy i ryzyka proponujemy pokazać najpóźniej
po wybraniu podejścia, przed pierwszym doborem — są odrębne od tajnej podatności.

## 5. Jedna próba krok po kroku

1. Gracze wybierają cel i podejście. Aplikacja przypisuje bohatera, ustala
   profil oraz prezentuje stawkę i mechaniczne przeszkody.
2. Propozycja: na początku każdej nowej próby tasujemy komplet 25 kart,
   po pięć każdego koloru. Nie wykładamy rynku. Wybrane karty i odrzucone
   będą osobnymi stosami; suma zaczyna od 0.
3. Gracz deklaruje „Dobieram”. Dopiero wtedy odkrywa dwie karty. Wybranie
   doboru zobowiązuje do przyjęcia jednej karty, o ile istnieje legalny wybór.
   Propozycja: rozpoczęcie próby obejmuje pierwszy dobór; pas jest dostępny
   dopiero po rozliczeniu pierwszej wybranej karty. Przed rozpoczęciem można
   odejść od rozmowy, ale nie otrzymuje się za to końcowego testu.
4. Przy dwóch jednakowych kolorach można przyjąć ten kolor albo dobierać
   dalej do pierwszego innego. Nie dobieramy kolejnych różnych kolorów,
   aby powiększać ofertę. Prostszy wariant obowiązkowego szukania drugiej barwy
   byłby zmianą względem słowa „można” w propozycji użytkownika.
5. Gracz wybiera jeden z legalnych oferowanych kolorów i zgłasza go aplikacji.
   Jedna fizyczna karta trafia do puli, wszystkie pozostałe odkryte na odrzucone.
   Nie dodajemy do sumy kart odrzuconych, nawet jeśli mają ten sam kolor.
6. Aplikacja sprawdza zakazy wyboru, zapisuje wybraną kartę i jej wartość,
   a następnie rozstrzyga ewentualną przeszkodę wymagającą rzutu.
7. Jeżeli przeszkoda nie przerwała próby: dokładnie 21 daje natychmiastowy
   sukces; powyżej 21 wymusza końcowy test z karą. Poniżej 21 gracz ponownie
   wybiera pas albo dobór. Nie może zobaczyć następnej oferty przed pasem.
8. Pas kończy dobieranie i otwiera jeden końcowy test. Aplikacja liczy normalny
   modyfikator wykonawcy oraz premię/karę karcianą. Gracz rzuca fizycznym k20.
9. Wynik i autorskie konsekwencje zamykają próbę. Kolejna metoda nie jest
   darmowym ponowieniem: jej dostępność zależy od zmienionej sytuacji.

Propozycja: przełączenie metody po rozpoczęciu nie zeruje próby. Wyjście z
konfrontacji po deklaracji doboru także nie pozwala uniknąć przyjęcia karty.
Odświeżenie strony i zapis/wczytanie muszą zachować dokładny etap.

### Koniec talii — propozycja

Nie tasujemy odrzuconych w środku próby. Jeżeli końcowa oferta ma tylko jeden
kolor, można wybrać jedną kartę tego koloru. Brak kart lub brak legalnej karty
w końcowej ofercie oznacza wymuszony pas z dotychczasową sumą, bez dodatkowej
kary. To jawny wyjątek od obowiązku przyjęcia karty po decyzji o doborze.

Gracze zgłaszają wyjątkowo „Brak legalnej karty / talia pusta”. Przy podawaniu
samych wybranych kolorów aplikacja nie wie, ile duplikatów odrzucono i kiedy
fizyczna talia się wyczerpała. Procedura nie może kręcić się bez końca, gdy
w stosie pozostał wyłącznie jeden kolor.

Jeżeli oba pierwsze kolory są identyczne i zakazane przez „Nie powtarzaj się”,
trzeba szukać drugiego koloru, dopóki są karty. Dobrowolna rezygnacja z tego
szukania nie daje wymuszonego pasu ani nowej oferty. Wyjątek bez kary dotyczy
wyłącznie faktycznego końca talii i braku legalnego wyboru.

Fizyczne przygotowanie tej talii jest osobną procedurą sceny społecznej.
Nie wywołuje samo z siebie bojowego odświeżenia ani wygaszenia efektów O/T.
Przed implementacją trzeba ustalić przejście z istniejącego stanu walki
i odtwarzanie fizycznych stosów po zapisie; nie uruchamiamy konfrontacji
społecznej wewnątrz nierozstrzygniętej akcji walki.

## 6. Końcowy test — tabela startowa do sprawdzenia

| Suma / zakończenie | Proponowany efekt |
| --- | --- |
| 0–10 | Bez modyfikatora karcianego |
| 11–14 | +1 do testu |
| 15–17 | +2 do testu |
| 18–19 | +4 do testu |
| 20 | +6 do testu |
| 21 po rozstrzygnięciu przeszkód | Automatyczny sukces ustalonego podejścia |
| Powyżej 21 albo przerwanie przez przeszkodę | Test z −3 zamiast premii |

Przerwanie dobierania nie oznacza automatycznie porażki całej konfrontacji.
Domyślnie pozostawia test z karą, tak samo jak przekroczenie. Jeżeli konkretny
NPC ma twarde zakończenie bez testu, byłaby to osobna, jawna reguła sceny.

Przeszkoda i przekroczenie nie naliczają dwóch kar −3 za tę samą kartę.
Złe zakończenie może mieć inne konsekwencje fabularne niż zwykłe niepowodzenie
po pasie, np. utratę zaliczki albo odmowę dalszych rozmów. Efekty muszą być
zdefiniowane w contencie, a nie dopowiadane przez model po rzucie.

Na pierwszy test warto zachować wspólny bazowy ST dla podejść w tej samej
konfrontacji. Podatność zmienia już profil kart; dodatkowa ukryta zmiana ST
utrudni ocenę, z czego naprawdę wynika trudność. Różnice uzasadnione inną
stawką lub argumentem są możliwe później, jako świadoma decyzja projektu.

## 7. Przeszkody — mały katalog

### „Nie powtarzaj się”

Nie wolno wybrać tego samego koloru co bezpośrednio poprzednio. Chodzi o
kolejność wybranych kart, nie o powtarzające się karty w puli oferty.
Odrzucone karty nie resetują poprzedniego koloru.

Wybór zakazanej barwy aplikacja odrzuca przed zmianą sumy. Gracz wraca do
tej samej fizycznej oferty, nie dostaje nowej. Dwa różne kolory zapewniają
co najmniej jedną legalną opcję przy tym pojedynczym zakazie. Wyjątek dla
końca talii opisano wyżej.

### „Drażliwy temat”

Po każdej wybranej czerwonej karcie gracz rzuca fizycznym k6 za ryzyko
własnego zagrania. Na 1 kończy dobieranie i przechodzi do testu z karą.
Na 2–6 normalnie sprawdza sumę. Nie rzucamy za odrzucone czerwone karty.

Propozycja kolejności: ten rzut poprzedza automatyczny sukces za 21, więc
czerwona domykająca 21 nadal niesie zapowiedziane ryzyko. Jeśli sama suma już
przekroczyła 21, zbędny k6 można pominąć, o ile jego wynik nie ma osobnego
skutku w contencie. Zasada powinna być pokazana przed decyzją o doborze.

Na początek: najwyżej jedna przeszkoda na podejście. Same profile wartości
już tworzą różnice; dodatkowe wyjątki zwiększają obciążenie graczy i balansowania.

## 8. Dane autora oraz minimalny interfejs

Konfrontacja zawiera NPC, cel, warunki rozpoczęcia i zamknięcia, listę metod,
informacje fabularne oraz zasady następnej próby po porażce.

Każde podejście zawiera:

- stałego wykonawcę i warunki dostępności;
- pięć wartości mana → liczba, niezmiennych podczas próby;
- sposób ujawniania wartości i ewentualne wcześniejsze wskazówki;
- najwyżej jedną przeszkodę w pierwszym prototypie;
- właściwy test, ST i stawkę;
- wynik dokładnego 21, sukcesu testu, porażki i przerwania;
- konkretne ustępstwo NPC oraz konsekwencje dla dalszej sceny.

Przykład: ten sam cel „Irena składa z nami świadectwo” może mieć Empatię
Dagny, Zastraszanie Brakki i Argumentację Nimry. Przy sukcesie Irena może
współpracować z zaufaniem, zgodzić się pod presją albo potwierdzić wyłącznie
udowodnione fakty. Warunki i granice ustępstwa opisujemy przed grą.

Panel gracza potrzebuje tylko nazwy celu i wykonawcy, „Pas / Dobieram”, pięciu
kolorów, aktualnej sumy, poznanych wartości, premii, krótkiej reguły przeszkody
i ewentualnego wejścia rzutu. Po „Dobieram” opcja „Pas” jest zablokowana do
rozliczenia karty. Zakazany poprzedni kolor może być wygaszony. Pozostałe
kolory nie są filtrowane po fizycznej ofercie, której aplikacja nie zna.

Plansza może pokazywać sumę na 21 polach i wyróżniać aktualny próg premii;
kolory wybieramy z pięciu stałych pól/run. Nie jest potrzebna dodatkowa
taktyczna mapa rozmowy ani ruch wszystkich bohaterów.

Przy zgłaszaniu wyłącznie wybranego koloru aplikacja może sprawdzić sumę,
poprzedni wybór, etap, przeszkody i rzuty. Nie zweryfikuje rzeczywistej oferty,
odrzuconych duplikatów ani składu pozostałej talii. To świadome zaufanie do
stołu, a nie automatycznie wykryta legalność doboru. Pełne liczenie oferty
wymagałoby dodatkowego wejścia, którego użytkownik chce na razie uniknąć.

Stan do wznowienia: NPC, konfrontacja, podejście, wykonawca, wybrane kolory
w kolejności, suma, ujawnione wartości, etap, oczekujący rzut, wynik i zużyte
uprawnienia. Kontynuacja po wczytaniu wymaga zachowania lub odtworzenia
fizycznych stosów; same wybrane kolory nie wystarczą do ich rekonstrukcji.

## 9. Lorian — co naprawdę działa obecnie

- **Obycie i targowanie:** +2 do własnych pozabojowych testów Charyzmy.
  To pasyw osobisty, nie premia dla całej drużyny.
- **Improwizacja:** raz na danego NPC Lorian może przerzucić własny nieudany
  pozabojowy test Charyzmy przed konsekwencjami. Drugi wynik jest ostateczny,
  a zużycie zapisane w stanie NPC.

Źródła: `src/dnd_board_game/character_creation/boardgame_help.py`,
`combat/lorian_features.py::social_grace_bonus` oraz obsługa rzutów i
`lorian:improvisation` w `ui/exploration_app.py` (dwie ostatnie ścieżki względem
`src/dnd_board_game/`). Zweryfikowano pięć istniejących testów:
`scripts/safe_pytest.sh --timeout 60 tests/unit/test_lorian_features.py -k 'social_grace or improvisation'`.
Wynik: 5 zaliczonych, 13 pominiętych przez filtr.

Propozycja integracji: zachować oba efekty przy końcowym teście Charyzmy
Loriana, również teście z karą po przekroczeniu. Nie podnoszą sumy kart,
nie zmieniają celu 21 i nie przerzucają k6 przeszkody. Przy automatycznym
sukcesie za 21 nie ma k20 do przerzucenia. Inspirowanie innego bohatera
w tej minigrze wymagałoby osobnej decyzji; nie wynika z obecnego pasywu.

Nie dodajemy jeszcze nowej zdolności manipulującej talią. Najpierw sprawdzamy
wartość obecnego +2 oraz przerzutu razem z premiami za sumę i automatycznym 21.

## 10. Następny krok projektowy

1. Ustalić moment ujawniania wartości oraz znaczenie minimum trzech metod
   wobec składu drużyny. Pytania zadane użytkownikowi; propozycje powyżej
   nie oznaczają uzyskanej odpowiedzi.
2. Przejść ręcznie tę samą konfrontację trzema metodami: bez przeszkód,
   następnie z jedną. Zachować identyczną stawkę i ST przy porównaniu.
3. Zmierzyć trafienia 21, świadome pasy, przekroczenia, końcowe sukcesy,
   liczbę ofert, liczbę fizycznie odkrytych kart oraz czas obsługi.
4. Sprawdzić małe składy, brak pasującego bohatera, końcówkę talii, powtarzanie
   koloru, czerwone 21 z pechowym k6, przerzut Loriana i wznowienie próby.
5. Dopiero po tej próbie ustalić rozkłady, tabelę premii i ewentualne nowe
   pasywy. Nowy model zasad i UI wymagają osobnego wdrożenia oraz testów.

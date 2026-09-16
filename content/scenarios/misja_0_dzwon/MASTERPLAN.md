# Misja 0 — Dzwon do odebrania

Status: wdrożona pierwsza grywalna wersja, 2026-09-16. Szczegóły rzeczywistych
plików, liczb i obsługi opisuje [README](README.md), wyniki symulacji —
[BALANCE_REPORT](BALANCE_REPORT.md). Poniższy masterplan zachowuje uzgodnienia
i pierwotne propozycje jako odniesienie; liczby nadal wymagają ogrania.

## 1. Cel i zakres

Pierwsza wspólna wyprawa wybranej drużyny 3–6 bohaterów. Narrator prowadzi
między konkretnymi punktami rozgrywki: odprawą, negocjacjami, przeszkodą
drogową, walką, niewielką eksploracją i decyzją. Nie budujemy rozległego
swobodnego zwiedzania ani obowiązkowych ćwiczeń wszystkich zdolności.

Zadanie: zabrać wóz, odzyskać ciężki dzwon alarmowy z niedawno ewakuowanego
posterunku i wrócić. Dzwon zdjęto już z wieży; transport zabrał rannych,
dokumentację i pilne zaopatrzenie. Dowódca zginął wcześniej w walce.
Wieśniacy zaopatrywali posterunek, nie dostali zapłaty i próbują zabrać dzwon
jako rekompensatę. Zachowali własne pokwitowania dostaw.

Dzwon wraca z drużyną w zwykłym przebiegu misji. Główna decyzja dotyczy
roszczenia i potraktowania wieśniaków, nie pozostawienia dzwonu. Zwrot dzwonu
nie rozstrzyga moralnej oceny sposobu wykonania zadania.

## 2. Samodzielna, edytowalna paczka

Wszystkie teksty, portrety, ilustracje, mapy i późniejsze nagrania dotyczące
tej misji mają znajdować się w tym folderze. Istniejące materiały do ponownego
wykorzystania kopiujemy do paczki z zapisaniem źródła. Nie odwołujemy się
po kryjomu do narracji innej przygody ani do tekstów zaszytych w Pythonie/JS.
Wspólny silnik zasad i techniczne kontrolki aplikacji pozostają poza paczką.

Planowana struktura (nazwy i kontrakt plików do wdrożenia w loaderze):

```text
misja_0_dzwon/
  MASTERPLAN.md
  README.md                      instrukcja edycji i mapa plików
  scenario.json                  manifest oraz odwołania do części
  flow.json                      przejścia, warunki, checkpointy
  profiles/
    narrator.md
    nessa.md
    heroes/<hero_id>.md           siedem profili, wspólny kanon i styl
    villagers/<npc_id>.md
    objects/<object_id>.md
    sources.json                 pochodzenie i wersje profili
  text/
    intro/world.md
    intro/heroes/<hero_id>.md     stały fragment dla danego bohatera
    intro/party.md
    scenes/<scene_id>/...md       narrator, NPC, wybory, wyniki, podpowiedzi
    journal/...md                przypomnienia i niedokończone sprawy
    tutorial/...md               treści lekcji osadzone w misji
    index.json                   stabilne ID tekstów, mówca, odwołania
  mechanics/
    confrontations.json
    enemies.json
    items.json
    effects.json
    rewards.json
    party_variants.json
  maps/                          mapy, pola, setup i wersje do druku
  assets/
    images/                      portrety, obiekty, ilustracje scen
    prompts/                     instrukcje tworzenia ilustracji
    audio/                       dopiero na końcu projektu
```

Tekst z pliku jest tekstem widocznym w grze. Jego zmiana nie wymaga zmiany
kodu ani ponownego generowania scenariusza. Docelowo odświeżenie widoku lub
ponowne otwarcie sceny czyta aktualną treść, nie powtarzając efektów gry.
Obrazy wymagają odświeżania cache po zmianie zawartości. Zmiany mechaniki lub
topologii wchodzą po walidacji i ponownym uruchomieniu etapu, nie w połowie rzutu.
Zapis przechowuje ID, wybory i efekty; historia może zachować dawny zapis
zdarzeń, ale nie powinna przesłaniać nowej treści przyszłych scen.

Profil jest instrukcją tworzenia tekstu i obrazu, a zatwierdzony tekst osobnym
edytowalnym rezultatem. Edycja profilu nie nadpisuje ręcznie poprawionych
dialogów: ponowne generowanie jest świadomą czynnością autorską. Pierwszy
komplet profili, tekstów i materiałów przygotowuje asystent, potem użytkownik
może swobodnie go poprawiać. Gra odtwarza gotowe warianty, nie wymyśla przy
każdym wejściu nowej wersji fabuły.

## 3. Profile i narrator

Każdy profil zawiera: stałe fakty i wygląd, temperament, sposób mówienia lub
opisywania, charakterystyczne szczegóły, wiedzę i jej ograniczenia, tajemnice,
zakazane sprzeczności, instrukcje ilustracji. Sytuacja w scenie jest dodatkiem
do profilu, nie zmianą charakteru postaci.

Nessa: podstawą jest istniejący opis w
`../campaign/MAPA_0_GILDIA_NESSA_SPEC.md`, szczególnie sekcja 4. Zachowujemy
opiekuńczość, pragmatyzm, ciepłą poufałość, oszczędny humor, czerwony ołówek,
bordowo-śliwkowy ubiór i troskę o ludzi. Wiedza o pyle i transporcie z dawnej
przygody nie przechodzi do tej misji. Dla bohaterów najpierw wykorzystujemy
istniejące opisy; uzupełnienia zapisujemy jawnie. Lokalna kopia profilu ma
źródło i wersję, by późniejsze scenariusze nie tworzyły sprzecznych postaci.

Narrator: przygodowa proza XIX wieku, inspiracja tonem Aleksandra Dumasa.
Dostojny, życzliwy, nieco tajemniczy obserwator; powaga przełamana rzadką
ironią. Humor dotyczy ludzkich przywar i instytucji, nie szydzi z cierpienia.
Bez nadmiernej archaizacji, pompatycznych monologów i żartu w każdym akapicie.
Zna więcej niż ujawnia, ale nie zdradza motywów wieśniaków przed właściwą sceną.
Nie ocenia wyborów za graczy. Opisuje konsekwencje i spina podróż.

Narracja, wypowiedź NPC i instrukcja techniczna są osobnymi blokami.
Instrukcje rozłożenia figurek i reguły muszą być jednoznaczne, bez literackich
ozdobników. Krótkie segmenty mają stałe ID i mówcę, aby później przypisać
voiceover oraz oznaczać nagranie jako nieaktualne po zmianie tekstu.
Audio i muzykę robimy po ustabilizowaniu gry i tekstów.

## 4. Przebieg

### 00 — Wybór drużyny i intro

Wybór 3–6 postaci, potem: intro świata → stałe fragmenty tylko wybranych
bohaterów, w kolejności składu → wspólne zakończenie o poznaniu się drużyny
i wezwaniu do Nessy po pierwsze zadanie. Fragment bohatera powstaje raz
na podstawie jego profilu; nie tworzymy odrębnego tekstu dla każdej kombinacji.
Można pominąć lub ponownie odczytać intro bez zmiany stanu misji.

### 01 — Setup gildii

Normalny setup planszy: mapa, kolejne podświetlane miejsca, Nessa, arena jako
punkt orientacyjny, figurka drużyny i wyjście. Każdy krok wymaga potwierdzenia.
Arena nie uruchamia automatycznie całego starego kursu. Pojedyncze ćwiczenia
pozostają dostępne osobno jako Poligon do testowania mechanik.

### 02 — Odprawa i negocjacje

Nessa przekazuje cel, informację o ewakuacji i ciężarze dzwonu, zasady
wynagrodzenia oraz wyposażenie wozu. Dwie krótkie opcjonalne kwestie:
„Dlaczego dzwon został?” i „Czego spodziewać się na drodze?”. Nie zdradzają
wieśniaków. Powrót do tematu pokazuje poznaną odpowiedź bez ponawiania nagród.

Opcja „Negocjuj stawkę” otwiera aktualną konfrontację całej drużyny.
Przed rozpoczęciem jasno wskazujemy, że stawką jest dodatkowe zaopatrzenie:
jedna zwykła mikstura leczenia do wspólnego ekwipunku, lecząca `2k8 + 4`.
Propozycja słabszej mikstury: `1k8 + 2` (dodatek +2 jest roboczy).

Proponowany kompromis: po zbiciu połowy oporu Nessa raz proponuje słabszą
miksturę. Przyjęcie kończy negocjacje z tą nagrodą. Odmowa pozwala walczyć
o zwykłą; przegrana nie daje mikstury i nie zmienia podstawowego zlecenia.
Nie otrzymujemy obu przedmiotów. Propozycja nie przerywa nierozstrzygniętego
rzutu ani rozliczania kart.

Podatności, progi, dobór, pomoc i wpływ zgodne z aktualnym modelem eksploracji.
Reakcje Nessy mają własne teksty: przypomnienie kosztów spala karty, rzeczowa
kontra odbiera kartę puli według reguł, powrót do warunków wyjściowych odnawia
k4 oporu. Liczby bazują na obecnym profilu i strategii skalowania.

Po odprawie drużyna fizycznie idzie figurką do wyjścia. To uruchamia podróż;
zamknięcie okna rozmowy samo nie przenosi do następnej sceny.

### 03 — Droga i wóz

Narrator opisuje podróż i zakleszczone w koleinie koło; trzeba wydostać
i zabezpieczyć wóz. Pełna konfrontacja z obiektem, świeża talia zgodnie
z zasadami eksploracji, cała drużyna uczestniczy. Sukces: dalsza droga bez kary.

Porażka: wóz udaje się uratować siłą, ale drużyna jest wyczerpana. Gracze
od razu rzucają fizyczne `1k4`, wpisują przez fokus/−/+ i zatwierdzają wynik.
Jeden wspólny wynik ustala czas zmęczenia wszystkich bohaterów w najbliższej
walce. Dopiero po zatwierdzeniu narrator opisuje skutek wraz z czasem trwania.

Status „Zmęczenie po przeprawie”: −2 do testów ataku oraz −2 do obrażeń
zadawanych przez bohatera przez N pełnych rund najbliższego starcia.
Propozycja doprecyzowania: kara obrażeń raz na rozstrzygnięcie obrażeń
wobec celu, nie od każdej kostki; wynik nie schodzi poniżej zera. Przy ataku
wielokrotnym każde osobne trafienie jest osobnym rozstrzygnięciem. Leczenie
i wpływ społeczny nie są obrażeniami. Zakres musi być opisany na statusie.

Do początku walki status ma stan „oczekuje”, potem licznik maleje na końcu
pełnych rund: wynik 1 obejmuje całą pierwszą rundę. Status pokazuje źródło,
kary i pozostały czas w panelu każdego bohatera. Nie znika przy setupie,
przejściu sceny ani mana drainie; wygasa po N rundach lub końcu tej walki.
Odtworzenie ekranu nie przerzuca k4 i nie skraca czasu.

### 04 — Dotarcie i setup walki

Narrator pokazuje uzbrojoną grupę przy dzwonie i próbie przejęcia wozu.
Krótka wymiana jednoznacznie prowadzi do starcia. Nie ujawnia długu ani
pochodzenia grupy. Celem napastników jest transport i dzwon, nie przypadkowy
mord. Rozkładamy mapę posterunku, dzwon, osłony, wóz i figurki wszystkich
uczestników według podświetlanych kroków. Dopiero potem inicjatywa.

### 05 — Walka i poddanie

Podstawą jest normalna walka. Przeciwnik przy 0 HP przestaje działać,
a jego figurkę usuwamy. Propozycja dla tej misji: 0 HP oznacza wyeliminowanie
z walki, nie automatyczny zgon. Po starciu przywódca może być ranny;
nie dajemy mu ukrytej niewrażliwości dla potrzeb późniejszego dialogu.

Po pełnym rozstrzygnięciu akcji, gdy liczba zdolnych do walki przeciwników
spadnie poniżej liczby bohaterów wybranych do misji i pozostaje przynajmniej
jeden przeciwnik, grupa jednokrotnie proponuje poddanie. Nie porównujemy
z chwilową liczbą przytomnych bohaterów. Oferta nie przerywa obrażeń ani
spalania many i jest zapisywana, aby wczytanie jej nie powielało.

- Przyjmij: walka natychmiast się kończy, pozostali oddają broń; oszczędzamy
  HP i zasoby. W zamian drużyna uznaje poddanie: osobiste narzędzia i dobytek
  po zabezpieczeniu sytuacji pozostają u właścicieli. Łatwiejsza współpraca,
  ale nie rozwiązany dług ani bezwarunkowe prezenty.
- Kontynuuj: walka trwa do eliminacji ostatniego przeciwnika, z normalnym
  ryzykiem strat. Po wygranej można zarekwirować określony w paczce przedmiot
  użytkowy jako zdobycz. Wieśniacy są mniej skłonni pomagać i nie oferują
  bezpłatnie wskazówki o skrytce. Dokumenty i główne wybory nadal dostępne.

To propozycja różnych kosztów i korzyści w grze, nie twierdzenie narratora,
że odmowa przyjęcia poddania i przyjęcie mają identyczną wagę moralną.
Wybór nie daje magicznie dodatkowego łupu, którego wcześniej nie było.

Przy eliminacji wszystkich w jednym efekcie nie ma oferty poddania: osobny
wariant „rozbici bez oferty” nie traktuje tego jako świadomej odmowy.
Przy porażce bohaterów proponowany wariant pozwala powtórzyć starcie albo
kontynuować po rozbrojeniu: wieśniacy chcą rozmowy i transportu, nie egzekucji.
Warunki odzyskania dzwonu w tym wariancie trzeba rozpisać przed implementacją.

#### Robocze role wrogów

Poniższe statystyki są punktem startowym do ewaluacji, nie zatwierdzonym
balansem. Wrogowie używają prostych stałych premii, nie ładowania bohaterów.

| Rola | HP | KP | Atak | Obrażenia | Zachowanie |
|---|---:|---:|---:|---|---|
| Przywódca | 32 | 13 | +4 | 1k6 + 3 | Trzyma przejście przy dzwonie |
| Silny drwal | 28 | 12 | +4 | 1k8 + 3 | Zbliża się do najbliższego zagrożenia |
| Zwinny parobek | 18 | 14 | +4 | 1k6 + 2 | Szuka dojścia z boku i osłon |
| Procarz | 16 | 12 | +3 | 1k4 + 2 | Ostrzeliwuje z dystansu |
| Woźnica z drągiem | 22 | 12 | +3 | 1k6 + 2 | Broni wozu i przejścia |

Składy przygotować osobno dla 3/4/5/6 osób, według strategii skalowania.
Na początku musi być co najmniej tylu przeciwników co bohaterów; wstępnie
sprawdzić N+1 lub N+2, aby próg poddania nie działał od startu. Dodatkowi
przeciwnicy wykorzystują proste role. Sprawdzić szczególnie czas walki,
zmęczenie do czterech rund oraz moment oferty względem ładowania postaci.
Nie dawać wieśniakom nadnaturalnego spalania many tylko dla demonstracji
mechaniki. Talia i użycia zdolności już wprowadzają presję; zaawansowane
ataki w manę można nadal przećwiczyć na Poligonie.

### 06 — Narrator i przejście do jednej figurki

Osobne krótkie wejścia po przyjęciu poddania, odmowie, rozbiciu bez oferty
oraz ewentualnej porażce drużyny. Tekst uwzględnia odniesione straty i ton
rozmowy, ale nie dopisuje śmierci, których mechanika nie rozstrzygnęła.

Gra prowadzi przez zebranie figurek bojowych, pozostawienie mapy i ustawienie
figury drużyny oraz oznaczeń punktów: przywódcy, dzwonu, zbrojowni,
kwatery dowódcy i magazynku. Przywódca wraca jako rozmówca, także ranny,
nie jako odrodzony przeciwnik z pełnym HP.

### 07 — Krótka eksploracja posterunku

- Przywódca: ujawnia pochodzenie, dostawy i brak zapłaty. Pokazuje własne
  pokwitowania; nie trzeba wygrać testu, aby poznać sedno konfliktu.
- Dzwon: oględziny i przygotowanie załadunku, finalizacja po decyzji.
- Zbrojownia: opuszczone stojaki i pozostawiony w pośpiechu medalik żołnierza.
  Propozycja: odkrycie bez rzutu, ale po świadomym zbadaniu podpowiedzianego
  miejsca, np. połysku pod stojakiem. To nagroda za uwagę i opcjonalną
  interakcję, nie kolejna pełna konfrontacja. Roboczy napis: „Wracaj. E.”,
  inicjały właściciela „J. R.”. Można zachować lub później sprzedać;
  przyszłe spotkanie właściciela zależy od posiadania przedmiotu.
- Kwatera dowódcy: oddzielna skrytka i plotka o cennym przedmiocie.
  Wieśniacy mogą sprzedać wskazówkę lub dać ją za współpracę. Plotka wskazuje
  konkretny element pomieszczenia, lecz nie jest jedyną drogą odkrycia.
  Znalezisko nie jest medalikiem ze zbrojowni. Robocza nagroda: prosty amulet,
  z jednym efektem do ustalenia; nie dokładamy tu rozbudowanego podsystemu.
- Magazynek/kuchnia: krótki ślad pośpiesznej ewakuacji i drobny przedmiot
  użytkowy. Zakres maksymalnie jednej krótkiej interakcji.

Nie ma kancelarii ani pozostawionych dla wygody fabuły archiwów garnizonu.
Trzy dodatkowe punkty są opcjonalne, bez obowiązku odhaczania wszystkich.
Odkrycia i odebrane nagrody zapisujemy; ponowne kliknięcie ich nie powiela.

### 08 — Dylemat i decyzja drużyny

Po poznaniu roszczenia narrator zbiera znane fakty i pyta, co drużyna zrobi
z cudzym długiem, skoro przybyła po dzwon. Formułuje sytuację literacko,
ale decyzje mają krótkie czytelne etykiety i jawny zakres obietnicy.
Wybór przez runy i potwierdzenie, bez kolejnego rzutu. Trzy ścieżki:

1. **Podejmiemy się sprawy.** Drużyna bierze pokwitowania, zobowiązuje się
   szukać pomocy i zabiera dzwon. Brak natychmiastowej premii pieniężnej.
   Powstaje niedokończona sprawa; narrator przypomina o niej przy sensownych
   okazjach, np. przybyciu do miasta, nie co scenę. Przyszły prawnik może
   przejąć roszczenie; obecna misja nie gwarantuje wyniku sądu.
2. **Zgłosimy zajście.** Drużyna odsyła wieśniaków do samodzielnego dochodzenia
   roszczeń i zgłasza próbę przejęcia mienia. Zabiera dzwon; możliwa jawna,
   niewielka premia za raport. Pokwitowania zostają u wieśniaków. Nessa
   nagradza informację o bezpieczeństwie szlaku, nie cierpienie cywilów.
3. **Załatwimy to — za opłatą.** Świadome oszustwo: drużyna podaje się za
   pośrednika mogącego przyspieszyć sprawę, pobiera jednorazową opłatę i bierze
   dokumenty bez zamiaru działania. Natychmiastowy zysk kosztem wieśniaków;
   zapis kłamstwa, zapłaty i nierozwiązanej obietnicy może wrócić później.
   Autorska gałąź bez dodatkowego rzutu, nie uniwersalne prawo skutecznego
   kłamania w grze. Opłata ograniczona do faktycznego zasobu grupy, bez farmienia.

Nie łączymy automatycznie premii za donos z opłatą za fałszywe pośrednictwo.
Narracja oraz późniejsze skutki biorą pod uwagę także przyjęcie/odmowę
poddania. Nessa zna tylko to, co przekazano jej przy rozliczeniu; nie ma
magicznej wiedzy o kłamstwie. Konkretne sumy trafiają do `rewards.json`.

### 09 — Załadunek, powrót i rozliczenie

Interakcja z dzwonem kończy się załadunkiem na wóz. Propozycja: krótka
sekwencja czynności z potwierdzeniem, bez trzeciej pełnej konfrontacji.
Narrator opisuje następstwa decyzji, drogę powrotną i rozliczenie u Nessy.
Nie otwieramy ponownie całego drzewa dialogu ani kolejnego setupu gildii.

Okno końcowe pokazuje osobno: podstawowe wynagrodzenie, premie, uzyskaną
opłatę, wydatki, zdobyte i zużyte przedmioty, końcowy stan ekwipunku oraz
niedokończone sprawy. Odróżnia wspólną pulę od wypłat na bohatera.
Nagrody przyznawane raz; odczyt podsumowania niczego ponownie nie wypłaca.
Misja oznaczona ukończoną; przejście do następnej dopiero po zatwierdzeniu.

## 5. UI, zapis i samouczek

Każda główna scena ma checkpoint, powrót do menu i możliwość powtórzenia
w trybie testowym. Wznowienie pokazuje stan figur i wszystkich fizycznych
stosów; nie wystarczy odtworzyć sam ekran. Powtórki nie dopisują ponownie
łupów i wypłat do kampanii. Pojedyncze dotychczasowe przypadki pozostają
w osobnym Poligonie, nawet po dodaniu narracyjnej misji 0.

Pouczenia są kontekstowe: pierwsza oferta, pierwszy test, pomoc, przedmiot,
przejście do walki, 6/12/21, podbicie, status, poddanie, powrót do eksploracji.
Nie wymagamy, aby każdy użył każdej zdolności lub osiągnął 21. Przy braku
naturalnej okazji zaawansowane ćwiczenie pozostaje opcjonalne na Poligonie.
Wybory obsługują runy, wyniki kości fokus/−/+ i końcowy przegląd.

Kluczowy stan: skład; odwiedzone sceny; wynik negocjacji; otrzymana/zużyta
mikstura; wynik drogi i zatwierdzone k4; czas statusu; straty w walce; czy
zaoferowano poddanie i odpowiedź; znaleziska; decyzja o długu; właściciel
dokumentów; opłata/premia; dzwon załadowany/dostarczony; rozliczenie wypłacone.
To fakty do narracji i kolejnych przygód, nie ukryty licznik dobra i zła.

## 6. Etapy wdrożenia i kryteria ukończenia

1. Ustalić kontrakt paczki i wczytywania tekstów, profili oraz obrazów.
   Przygotować wszystkie pierwsze teksty, warianty, profile i manifest mediów.
2. Dodać przepływ misji, wybór 3–6 osób, intro składu, setup i checkpointy.
3. Podpiąć odprawę, konfrontację Nessy i kompromis mikstur; drogę, k4,
   trwały między scenami status zmęczenia i rzeczywiste modyfikatory.
4. Przygotować warianty walki, mapę, role i statystyki; ofertę poddania
   oraz przejście do eksploracji, także gdy przywódca wcześniej ma 0 HP.
5. Dodać punkty eksploracji, trzy decyzje, journal, załadunek i rozliczenie.
6. Ewaluacja 3/4/5/6, testy przepływu/UI/zapisu i ręczne próby na planszy.
   Dopiero po poprawkach końcowe voiceovery i muzyka.

Weryfikacja obejmuje: edycję tekstu/obrazu widoczną w grze; intro tylko
wybranych postaci; brak wycieku tajemnicy; słabą/zwykłą/brak mikstury;
status dla k4=1 i 4, granice rund, mana drain i wczytanie; poddanie raz,
atak obszarowy eliminujący wszystkich, powalonego przywódcę; wszystkie
ścieżki decyzji; brak duplikacji przedmiotów i pieniędzy; brak blokady przez
pominięcie opcjonalnego znaleziska; powrót do menu na każdym etapie.

Do dopięcia w implementacji: końcowe statystyki i składy, pełny wariant
porażki walki, właściwość amuletu, ceny/nagrody, bazowy czas użycia mikstur
zgodny z systemem przedmiotów oraz ostateczna wartość dodatku słabej mikstury.
Nie blokują one przygotowania paczki i tekstów roboczych.

Odniesienia: [skalowanie](../../../docs/PARTY_SCALING.md),
[konfrontacje](../../../docs/PARTY_CONFRONTATIONS.md),
[ładowanie many](../../../docs/MANA_CHARGE_V02.md).

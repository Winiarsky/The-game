# Rozmowy z maną: cztery warunki startowe — plan wdrożenia

Status: wdrożono 2026-09-14. Cztery warunki, lekcje, runy, zapis i druki
są dostępne. Aktualny przebieg i ograniczenia próby: `EXPLORATION_MANA_IMPLEMENTATION.md`.
Punkt wyjścia: `EXPLORATION_MANA_IMPLEMENTATION.md`.

## 1. Zakres pierwszego wdrożenia

Cztery opcjonalne warunki rozmowy: **częściowe porozumienie**, **drażliwy
temat**, **dodatkowy cel** i **przysługa za przysługę**. Rozmowa ma najwyżej
jeden z nich. W scenach wprowadzających warunek
zastępuje dotychczasową przeszkodę liczbową; nie dokładamy kilku wyjątków naraz.
Zwykłe rozmowy i dotychczasowe lekcje nadal mogą działać bez warunku.

Każdy wariant obsługuje siedem istniejących metod i przypisanych bohaterów.
Samodzielna scena udostępnia minimum trzy metody obecnych postaci. Zachowujemy
obecne cechy, premie Loriana/Erynda, dobór dwóch kart, pas przed doborem,
automatyczny sukces przy 21 oraz disadvantage bez premii karcianej po przekroczeniu.
Wszystkie decyzje idą przez runy. Rzuty zachowują fokus, −/+, kolejne kości,
podsumowanie, poprawkę i końcowe ✓.

Pierwszy grywalny zakres to cztery warianty Ireny w Arenie oraz reakcja Nessy
zależna od faktycznego wyniku. Mechanika ma być niezależna od samouczka.
Adaptację nowych warunków do obiektów i docelowej kampanii planujemy osobno;
istniejący samouczek obiektów pozostaje częścią testów regresji.

## 2. Częściowe porozumienie — dokładna zasada

Przed wyborem metody gracz widzi warunek: „Gdy pula pierwszy raz wyniesie
15–17, Irena zaproponuje podpisane świadectwo bez osobistego wystąpienia”.
Zasada i stawka są jawne; ukryty profil wartości zachowuje obecny moment ujawnienia.

Po pierwszym **wylądowaniu** w przedziale 15–17 pojawia się oferta.
Przeskoczenie z 14 na 18 jej nie uruchamia. Decyzję podejmujemy przed
odkryciem kolejnej pary kart:

- **Przyjmij porozumienie:** koniec próby bez k20, wynik `compromise`.
  Otrzymujemy wyłącznie obiecany częściowy rezultat, bez nagrody pełnego sukcesu.
- **Odrzuć porozumienie:** wracamy do normalnego wyboru pas/dobór.
  Można wykonać zwykły test z obecnej puli albo zaryzykować następną ofertę.
  Odrzucona propozycja nie wraca w tej próbie, również przy kolejnych 15–17.

Odrzucenie nie daje dodatkowej kary ani nie podnosi ST. Po późniejszej porażce
nie można odzyskać częściowego porozumienia. Wyjście z lekcji i wczytanie zapisu
nie odnawiają oferty; jawne powtórzenie ćwiczenia rozpoczyna nową próbę.

Pierwszy wariant Ireny:

| Wynik | Uzyskane świadectwo | Reakcja Nessy |
| --- | --- | --- |
| Porozumienie | Podpisany dokument, bez obecności Ireny | Przyjmuje dokument; dodatkowe pytania wymagają powrotu do Ireny |
| Pełny sukces | Irena przychodzi osobiście | Można od razu zadać pytania uzupełniające |
| Porażka | Własny raport drużyny | Nessa wymaga dodatkowego potwierdzenia relacji |

Porozumienie jest wiarygodną, użyteczną alternatywą. Nie oznaczamy go jako
„porażka” ani „pełny sukces”. Dotychczasowa cena wybranej metody nadal obowiązuje
przy uzyskanym porozumieniu, jeśli została jawnie zapowiedziana; nowe sceny
definiują cenę dla każdego wyniku zamiast dziedziczyć ją niejawnie.

## 3. Drażliwy temat — dokładna zasada

Przed rozpoczęciem metoda pokazuje drażliwy kolor, jego fabularne znaczenie,
dodatkową korzyść i cenę. Po ujawnieniu profilu karta ma normalną wartość.
Nie dokładamy drugiego rzutu ani osobnej waluty.

W referencyjnej scenie czerwona mana oznacza nacisk na ujawnienie nazwisk.
To znaczenie lokalne dla tej rozmowy, nie globalna definicja czerwonej many.

- Wybór drażliwego koloru zapisuje `sensitive_used = true` do końca próby.
- Samo odkrycie albo odrzucenie tej karty niczego nie uruchamia.
- Kolejne wybory drażliwego koloru nie mnożą ceny.
- Przed wyborem karta i jej runa pokazują: „Użycie zmieni warunki sukcesu”.
  Po wyborze stale widnieje krótka informacja o zobowiązaniu.
- Rzut i dokładne 21 rozstrzygają powodzenie normalnie. Cena wybranego
  rezultatu obowiązuje również przy 21 i przy sukcesie po przerzucie Loriana.

Drugi wariant Ireny:

| Wynik | Korzyść | Cena |
| --- | --- | --- |
| Sukces bez drażliwego koloru | Świadectwo o własnym udziale | Irena zachowuje gotowość do prywatnych wyjaśnień |
| Sukces z drażliwym kolorem | Świadectwo i nazwiska współuczestników | Irena odmawia dalszej prywatnej pomocy drużynie |
| Porażka, w obu przypadkach | Pozostaje własny raport | Brak dodatkowych informacji; w pierwszej wersji bez dodatkowej kary za kolor |

Nazwiska odblokowują w reakcji Nessy możliwość wskazania kolejnych osób do
rozmowy. Zachowana współpraca odblokowuje pytanie uzupełniające do Ireny.
Oba warianty mają użyteczność: liczbowo dogodna karta może przybliżyć do 21,
a wynik z nazwiskami daje inną korzyść kosztem relacji.
Koszt jest realizowany po końcowym rozstrzygnięciu, nigdy między pierwszym
nieudanym rzutem Loriana a decyzją o przerzucie.

## 3a. Dodatkowy cel — układ kolorów

Jawny warunek, np. **dwie wybrane niebieskie karty**, odblokowuje dodatkowy
rezultat przy końcowym sukcesie. U Ireny: oprócz świadectwa poznajemy osobę,
która pierwsza zaproponowała dokarmianie żeraków. Zwykły sukces bez układu
nadal realizuje główny cel rozmowy.

- Liczymy tylko karty zachowane w puli. Kolejność nie ma znaczenia.
- Warunek ma semantykę „co najmniej”; cztery niebieskie nie mnożą nagrody.
- Przekroczenie nie kasuje układu: wygrana z utrudnieniem również daje nagrodę.
- Dokładne 21 spełniające układ daje nagrodę. Porażka nie przyznaje jej.
- W pierwszym katalogu wymagamy dwóch kart jednego koloru. Kolor i nagroda
  są parametrami sceny; bardziej złożone układy powstaną pod konkretne przygody.
- UI pokazuje postęp 0/2, 1/2 i „Warunek spełniony — uzyskaj sukces”.
  Nie potrzeba dodatkowego przycisku; liczą się normalne wybory kolorów przez runy.

Pokusą jest dobór karty przydatnej do układu, choć gorszej dla sumy. Nagroda
powinna dawać informację, przysługę lub nową opcję działania, bez automatycznego
zwiększania szansy na sukces kolejnym modyfikatorem.

## 3b. Przysługa za przysługę — kontrola za zobowiązanie

**Raz w próbie możesz potraktować wybieraną kartę jako 1, przyjmując jawne
zobowiązanie.** To dodatkowa decyzja podczas oglądania legalnie odkrytej oferty;
nie umożliwia zmiany karty już zachowanej ani cofnięcia przekroczenia.

Przykład: masz 18, oferta daje 5 albo 7. Irena proponuje ustępstwo pod warunkiem
zaniesienia jej listu do obozu uchodźców. Możesz wybrać kartę za 1, dojść do 19
z premią +4 i zachować zobowiązanie, albo przyjąć normalną wartość i ryzykować
przekroczenie. List wymaga dodatkowej drogi; cena jest opisana przed rozpoczęciem.

- Przed startem widać korzyść i konkretny koszt. Po wyborze metody przypomnienie
  pozostaje przy runie ustępstwa. Nie ma ukrytej dodatkowej ceny listu.
- W fazie oferty Klucz (24) włącza użycie ustępstwa przy najbliższym wyborze.
  UI pokazuje wartość 1 oraz zobowiązanie przy dostępnych kolorach. Gwiazda (25)
  pozwala zrezygnować z ustępstwa przed wyborem karty. Kolor wybieramy normalną runą.
- Dopiero wybór koloru zużywa ustępstwo i zapisuje zobowiązanie. Samo włączenie
  podglądu nie ponosi kosztu. Karta zachowuje kolor i zajmuje miejsce w puli.
- Wartość końcowa tej jednej karty wynosi 1. W pierwszym contentcie nie łączymy
  ustępstwa z przeszkodami modyfikującymi wartości.
- Przyjęte zobowiązanie pozostaje także po porażce lub przerzucie. Dzięki temu
  jest rzeczywistą ceną kontroli ryzyka. Jest to wyraźna różnica względem ceny
  sukcesu przy drażliwym temacie; ekran musi ją podać przed użyciem.
- Ze stanu 20 można w ten sposób uzyskać 21 i automatyczny sukces za cenę.
  Jest to zamierzona możliwość, nie wyjątek cofający zobowiązanie.
- Zobowiązanie zapisujemy raz przy użyciu, nie ponownie przy wyniku.
  Samouczek pokazuje je Nessie jako dodatkowe zadanie, również po porażce.

## 4. Dane, stan i kolejność zdarzeń

Zmiany oprzeć na małych dataclasses i czystych funkcjach w `rules/`:

- Specyfikacja warunku: `none`, `compromise`, `sensitive_topic`,
  `color_goal` albo `favor`. Parametry: zakres propozycji, kolor/liczba kart
  lub zobowiązanie; teksty i efekty pozostają w contentcie.
- Stan próby: specyfikacja warunku zamrożona przy starcie, `proposal_status`
  (`unseen`, `offered`, `accepted`, `declined`), `sensitive_used`, stan
  ustępstwa (`available`, `armed`, `used`) i id przyjętego zobowiązania,
  jawny wynik `outcome_kind` (`success`, `compromise`, `failure`).
- Nowa faza `bargain` oraz komendy `accept_bargain`, `decline_bargain`.
- Każda metoda dostaje komplet wariantów wyniku: opis, koszty i stabilne flagi.
  Jeden resolver wybiera wariant; ten sam wynik zasila ekran, zapis i reakcję Nessy.
  Unikamy obecnego rozdzielenia `_commit()` i osobnego składania opisu w `payload()`.
- `success: bool | None` pozostaje jako pole zgodności z rzutem: przy
  porozumieniu ma wartość `None`, a `outcome_kind` wynosi `compromise`.
  Ekran, zaliczenia i konsekwencje sprawdzają jawny typ wyniku, nie ten bool.

Kolejność po wyborze karty: walidacja → zapis koloru i drażliwego tematu →
zastosowanie ustępstwa i jednorazowy zapis zobowiązania, jeśli wybrane →
obliczenie sumy → przekroczenie / dokładne 21 → wymuszony koniec od przeszkody
→ ewentualna oferta porozumienia → zwykła decyzja pas/dobór.
Jeśli technicznie połączymy warunek z limitem czterech kart, limit ma
pierwszeństwo przed ofertą. Pierwszy content nie łączy tych zasad.

Loader dostaje `scene_by_id()` i jawne `scene_id` w lekcjach. Obecne
`scene_for(kind)` pozostaje zgodnym domyślnym wyborem dla starych danych.
Nowe id scen: `irena_compromise`, `irena_names`, `irena_color_goal`, `irena_favor`. Nie wybieramy „pierwszego NPC”
z listy przy wznowieniu konkretnej próby.

Wynik i jego skutki zapisujemy raz dla id próby. Zobowiązanie za ustępstwo
ma własne stabilne id i zapisuje się raz już przy wyborze karty. Ponowiony request, stary skan,
odświeżenie ekranu lub ponowne otwarcie podsumowania nie powtarzają skutków.
W Arenie skutki dotyczą wyłącznie stanu ćwiczenia; reakcja Nessy czyta ten stan.

## 5. Plansza i prezentacja

Istniejące runy metod, kolorów, doboru i pasu zachowują przypisania.
W fazie oferty udostępniamy dwie dotąd wolne runy:

| Runa | Slot istniejącego panelu | Działanie |
| --- | --- | --- |
| Klucz | 24 | Przyjmij częściowe porozumienie |
| Gwiazda | 25 | Odrzuć propozycję; wróć do pas/dobór |

Runy pasu/doboru są nieaktywne, dopóki oferta czeka na odpowiedź. ✓ nie może
milcząco zaakceptować porozumienia. ↩ zachowuje istniejące wyjście z lekcji,
z zapisaniem nierozstrzygniętej propozycji. W widoku kości nadal oznacza poprawkę.

UI: krótki warunek przy metodzie, jedna wyróżniona propozycja w momencie wyboru,
wyraźny wynik „Porozumienie” oraz lista faktycznie uzyskanych korzyści i kosztów.
Drażliwa karta ma tekst i ikonę przy swojej runie; nie polegamy wyłącznie na kolorze.
Podgląd porozumienia mówi dokładnie, co otrzymujemy i z czego rezygnujemy.

Wspólny `board_choices` steruje UI, maską skanu i LED. Bez osobnej logiki
przycisków w przeglądarce. Nie zmieniamy firmware ani wydrukowanych symboli.

## 6. Zapis i zgodność

Wersja próby i magazynu kursu przechodzi z 1 do 2 z jawną, czystą migracją
w miejscu odczytu tych struktur. Format całego snapshotu nie wymaga zmiany.
Istniejący `core/migrations.py` wymaga `schema/schema_version`, a te struktury
używają `version`; nie przekazujemy starych danych bezpośrednio do tego rejestru.
Dodajemy dedykowany adapter migracji, testowany niezależnie.

Stare próby otrzymują warunek `none`; nie nakładamy nowej zasady na rozpoczętą
rozmowę. Stare wyniki true/false mapują się na success/failure. Zachowujemy
kolory, kości, aktualną fazę, przerzut, id próby, dotychczasowe skutki i zaliczenia.
Nieznana nowsza wersja daje czytelny błąd, bez resetowania danych.

Zapis w fazie `bargain` zachowuje dokładną ofertę i odpowiedź, jeśli padła.
Przyjęcie zapisanej oferty nie wymaga dobierania kart. Odrzucenie może wrócić
do pas/dobór dopiero po istniejącym potwierdzeniu zachowanych stosów.
Zmiana contentu nie może zmienić przyrzeczenia w już rozpoczętej próbie:
zapis przechowuje jej specyfikację i warianty konsekwencji.

## 7. Samouczek, reakcje i karty

Cztery nowe krótkie lekcje, dostępne dla wszystkich siedmiu postaci i zaliczane
wspólnie. Ich ukończenie nie wymaga określonej decyzji ani wygranego k20.

1. **„Coś pewnego czy szansa na więcej?”** Przygotowane oferty doprowadzają
   do 16: N/B → N=5, C/B → C=7, F/Z → F=4 (profil balanced).
   Gracz sam wybiera przyjęcie/odrzucenie. Po odrzuceniu wraca normalny dobór;
   N=5 może doprowadzić do 21, ale nie jest wymuszonym wyborem.
   Zaliczenie: odpowiedź na ofertę i doprowadzenie próby do końca.
2. **„Nazwiska mają cenę”** Nessa pokazuje warunek czerwonej karty. Gracz
   może jej użyć lub unikać; lekcja nie blokuje jednej z dróg. Finał pokazuje
   różnicę informacji i dalszej współpracy. Zaliczenie: rozstrzygnięcie próby.

3. **„Jeszcze jedna niebieska”** Jawna nagroda za dwie niebieskie. Gracz sam
   wybiera między sumą a domknięciem układu; ekran pokazuje postęp i końcową
   nagrodę tylko przy sukcesie. Zaliczenie wymaga rozstrzygnięcia próby,
   nie wymusza pogoni za dodatkowym celem.
4. **„Ile kosztuje pewność?”** Nessa pokazuje ustępstwo. Można z niego skorzystać
   lub rozegrać rozmowę normalnie. Po użyciu podsumowanie przypomina o zadaniu
   również przy porażce. Zaliczenie wymaga końca próby, nie przyjęcia zobowiązania.

Osobne ćwiczenia samodzielne dla czterech wariantów Ireny z trzema metodami.
Opcjonalne powtórzenie umożliwia sprawdzenie drugiej drogi, bez przymusu
powtarzania wprowadzających lekcji siedem razy.

Obecne `lesson.choices` narzuca jeden kolor na krok. Dla nowych lekcji potrzebny
jest skończony odcinek przygotowania, po którym ograniczenie znika, oraz cel
sprawdzany na podstawie decyzji i końcowego wyniku. Nie wymuszamy całej
fabularnej ścieżki pojedynczą tablicą kolorów. Walidator zlicza również karty
odrzucone w przygotowanym odcinku; dalsze dobory korzystają z reszty tej samej talii.

Reakcja Nessy ma rzeczywiste warunki dostępności odpowiedzi zależne od flag
ćwiczenia. „Nazwiska”, „pytanie do Ireny” i „wymagane potwierdzenie” nie mogą
być tylko trzema ozdobnymi zdaniami z identycznym dalszym przebiegiem.

Ściąga i pomoc `/rules/physical-mana`: krótki opis czterech warunków i run Klucz/Gwiazda.
Karty siedmiu bohaterów zachowują własne metody i premie. Odświeżamy wszystkie
formaty HTML/PDF i zbiorczy pakiet areny po ostatecznym składzie; liczby stron
sprawdzamy po generowaniu, nie zakładamy utrzymania dotychczasowych 60 stron.

## 8. Kolejność prac i oczekiwane pliki

Wszystkie ścieżki `rules/`, `ui/` itd. poniżej odnoszą się do `src/dnd_board_game/`.

| Etap | Zmiany | Warunek zakończenia |
| --- | --- | --- |
| 1. Stan, wynik, migracje | `rules/exploration_mana.py`, nowy `rules/exploration_mana_conditions.py`, adapter migracji | Stara próba odtwarza się bez nowego warunku; każdy wynik ma jednoznaczny typ |
| 2. Reguły decyzji | Nowy moduł warunków, `application/exploration_mana_flow.py` | Oferta jest jednorazowa; cena przetrwa 21 i przerzut; brak skutków przed finałem |
| 3. Content i konsekwencje | `scenarios/exploration_mana.py`, `content/tutorials/exploration_mana.json`, resolver wariantu wyniku w `application/` | Cztery warianty Ireny, siedem metod, jawne koszty, rzeczywiście różne następstwa |
| 4. Transport i plansza | `ui/exploration_mana.py`, `ui/exploration_mana_board.py`, `ui/static/exploration_mana.js`, `ui/static/training_arena.css` | Całą decyzję można podjąć przez runy; stare komendy nie powtarzają efektów |
| 5. Lekcje i reakcja Nessy | Content lekcji, `COMMON_LESSONS`, obsługa nowego finału w UI | Gracz wybiera obie drogi; nowy cel zaliczenia nie myli decyzji z wygraną |
| 6. Pomoc, druki, balans | `rules/exploration_mana_catalog.py`, `physical_cards/mana_print*.py`, szablon pomocy, skrypty druku i symulacji | Spójna ściąga, poprawne PDF, porównane ryzyko i korzyści obu dróg |

W każdym etapie aktualizujemy skupione testy. Po wdrożeniu uaktualniamy
`GAME_DESIGN.md`, `PROJECT_CONTEXT.md`, `TODO.md` i opis wdrożenia.
Bez nowych zależności, szerokiego refaktoru i zmian w `board/`.

## 9. Kryteria odbioru

- Reguły: 14→16 daje ofertę; 14→18 nie daje. Przyjęcie kończy bez k20.
  Odrzucona oferta nie wraca przy 16→17. Po odmowie legalny jest zwykły pas.
- Dokładne 21 i przekroczenie zachowują pierwszeństwo. Pula drażliwego koloru
  przy 21 daje pełny sukces z zapowiedzianą ceną, nigdy sukces „bez konsekwencji”.
- Tylko wybrana karta uruchamia temat. Kolejne takie karty nie mnożą kosztu.
  Porażka, przerzut i częściowe porozumienie nie uruchamiają cudzych wariantów.
- Zapis/wznowienie przed ofertą, z otwartą ofertą, po odrzuceniu, po drażliwej
  karcie, przed przerzutem i po wyniku. Stare zapisy v1 oraz ponowione komendy.
- Wszystkie siedem postaci, właściwe cechy, minimum trzy opcje w praktyce.
  Dwa różne sukcesy prowadzą do właściwych opcji w reakcji Nessy.
- Skany i LED: Klucz/Gwiazda tylko przy ofercie; żadnego przypadkowego doboru,
  pasu ani akceptacji przez ✓. Przy rzucie nadal działa strumień −/+ i podsumowanie.
- Pełna strona Chrome na 390/1100 px: przyjęcie, odrzucenie, drażliwa karta,
  21 z ceną, poprawka kości. Testy przez API planszy, nie tylko kliknięcia ekranowe.
- Regresje: stare lekcje rozmów i obiektów, przerzut Loriana, pułapki i karty.
  Pytest przez `scripts/safe_pytest.sh`, jeden konkretny plik na raz, z timeoutem.

Symulacja porównuje przyjmowanie propozycji i grę o pełny wynik, unikanie
drażliwego koloru i jego świadome używanie, zbieranie układu oraz grę
z ustępstwem i bez niego. Raportujemy osobno częstość
compromise/success/failure, uzyskane informacje i koszt relacji; nie zamieniamy
automatycznie każdego porozumienia w pełne zwycięstwo ani fabularnej ceny
w arbitralne −2 punkty. Ostatecznie próbą przy stole sprawdzamy, czy obie drogi
są kuszące, czy warunek jest czytelny i czy rozmowa zachowuje tempo.

Dodatkowe kryteria dla dwóch nowych warunków:

- Układ: wybrane kontra odrzucone kolory, dwie kontra cztery niebieskie,
  21 z układem i bez, sukces po przekroczeniu/przerzucie, porażka bez nagrody.
- Ustępstwo: aktywacja i anulowanie przed wyborem, wartość 1 i zachowany kolor,
  brak ponownego użycia i zmiany wcześniejszej karty. Zobowiązanie przetrwa
  porażkę, 21, przerzut i zapis/wczytanie; duplikat komendy nie mnoży kosztu.
- Zapis odtwarza uzbrojone ustępstwo; postęp układu wylicza z zachowanych kart.
- Klucz/Gwiazda obsługują ustępstwo tylko w fazie oferty danego wariantu;
  nie kolidują z częściowym porozumieniem, ponieważ scena ma jeden warunek.
- Wszystkie cztery warianty mają testy dla siedmiu bohaterów i próbę Chrome
  obejmującą runy, prawdziwą decyzję, rezultat i dostępność dalszych opcji.

## 10. Następne rozszerzenia

Na start zamykamy katalog na czterech warunkach. Kolejne warianty i układy
powstaną pod konkretne przygody. Łączenie kilku warunków w jednej rozmowie
dopiero po ocenie złożoności pierwszej wersji.

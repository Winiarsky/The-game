# Plan: obiekty sceny, przedmioty i improwizowany crafting

## Cel

Swobodna deklaracja gracza ma pozwalać używać elementów otoczenia oraz wyposażenia
drużyny bez definiowania wcześniej każdego gotowego rozwiązania. LLM tłumaczy
deklarację na ustrukturyzowaną propozycję, ale dostępność komponentów, poprawność
konstrukcji, koszty i zmiany stanu rozstrzyga deterministyczny runtime.

Nowy kontrakt ma być używany przez każdy nowo tworzony element interakcji. Istniejący
content może być migrowany etapami, z bramą strażnicy jako sceną referencyjną.

## Granice modelu

### `ItemDefinition`

Data-driven definicja powtarzalnego przedmiotu, narzędzia albo materiału z katalogu
`content/items/`. Zawiera stabilne `id`, nazwę, opis, rodzaj oraz kontrolowane
`properties`. Nie przechowuje położenia ani bieżącego stanu konkretnego egzemplarza.

### `ItemInstance`

Konkretny egzemplarz definicji należący do aktora, drużyny albo sceny. Przechowuje
ilość, stan, dostępność oraz lokalne nadpisania właściwości. Docelowo zastępuje
duplikowanie pełnych danych przedmiotu w ekwipunku i scenariuszu.

### `SceneFixture`

Element konkretnej instancji sceny: brama, zawias, drzewo, głaz, sterta gruzu albo
fragment ogrodzenia. Fixture nie jest domyślnie przenośnym przedmiotem, ale może być
badany, uszkadzany, odłączany lub stanowić źródło materiału. Jego zmienny stan jest
zapisywany w snapshotcie scenariusza.

### `TemporaryItem`

Dynamiczna konstrukcja wykonana przez graczy z uziemionych komponentów, np.
prowizoryczna drabina, taran albo dźwignia. Istnieje w określonym zakresie
(`interaction`, `scene` albo `scenario`), przechowuje komponenty, zastosowania,
trwałość i ryzyko. Nie wymaga wcześniejszej definicji gotowego przedmiotu.

## Właściwości

Właściwości są kontrolowanymi identyfikatorami danych, a nie zamkniętym enumem w
Pythonie. Loader waliduje je względem wersjonowanego katalogu. Opis narracyjny pomaga
LLM prowadzić fikcję, natomiast silnik korzysta wyłącznie ze struktury.

Pierwszy mały katalog powinien pokrywać co najmniej:

- geometrię: `long`, `short`, `wide`, `narrow`;
- zachowanie: `rigid`, `flexible`, `fragile`, `load_bearing`;
- masę i powierzchnię: `heavy`, `light`, `hard`, `sharp`;
- zastosowanie: `binding`, `cutting`, `prying`, `container`;
- materiał: `wooden`, `metallic`, `stone`, `textile`;
- zagrożenia: `flammable`, `corroded`, `slippery`.

Nie należy katalogować każdego kamienia jako globalnego itemu. Jednorazowy element
może być lokalnym fixture'em z właściwościami, a powtarzalny ekwipunek powinien
odwoływać się do `ItemDefinition`.

## Przepływ deklaracji

1. Gracz opisuje działanie naturalnym językiem.
2. LLM wybiera istniejące identyfikatory komponentów i proponuje cel konstrukcji,
   sposób użycia oraz narracyjne uzasadnienie.
3. Deterministyczny walidator sprawdza istnienie, dostępność, ilość, właściwości,
   zasięg sceny oraz wcześniejsze rezerwacje komponentów.
4. Runtime wylicza koszt czasu, wymagany test, ryzyko, trwałość i efekt. LLM nie
   dostarcza wiążących premii liczbowych.
5. UI pokazuje graczom interpretację i koszty przed zatwierdzeniem.
6. Po akceptacji komponenty są zużywane albo rezerwowane, a zmiany fixture'ów i
   nowy `TemporaryItem` trafiają do stanu instancji i snapshotu.
7. Użycie, rozmontowanie, zniszczenie lub koniec zakresu zwalnia albo usuwa zasoby
   zgodnie z zapisanym sposobem użycia komponentu.

## Etapy implementacji

### Etap 1: kontrakty contentu i authoringu

Status: ukończony 2026-07-14.

- dodać wersjonowany katalog właściwości;
- zdefiniować schematy `ItemDefinition`, `ItemInstance` i `SceneFixture`;
- rozszerzyć formularz interakcji o obiekty sceny, dostępne itemy, źródła materiałów,
  możliwość odłączenia, trwałość i oczekiwane zmiany stanu;
- przygotować przykłady oraz walidację referencji bez zmiany runtime.

Kryterium wyjścia: nową interakcję można opisać bez tekstowej listy
`available_materials` i bez gotowej receptury przedmiotu tymczasowego.

### Etap 2: modele domenowe i loader

Status: ukończony 2026-07-14.

- dodać małe dataclassy domenowe w granicach `inventory` i `exploration`;
- wczytywać definicje katalogowe i lokalne fixture'y;
- łączyć właściwości definicji z dozwolonymi lokalnymi nadpisaniami instancji;
- zachować tymczasową kompatybilność odczytu obecnego `available_materials`;
- walidować unikalne identyfikatory, referencje, właściwości i ilości.

Kryterium wyjścia: loader buduje jedną ustrukturyzowaną listę dostępnych źródeł,
niezależnie od tego, czy pochodzą z ekwipunku, sceny czy fixture'a.

### Etap 3: deterministyczny crafting

Status: ukończony 2026-07-15. Konstrukcje referencyjne powstają dynamicznie z celu
funkcjonalnego i właściwości. Odczyt starego template'u pozostaje wyłącznie jako
kompatybilność historycznego contentu, nie jako ścieżka bramy.

- dodać dynamiczny szkic konstrukcji obok tymczasowej kompatybilności
  `TemporaryItemTemplate`;
- wprowadzić wymagania funkcjonalne oparte na grupach właściwości, nie nazwach
  gotowych przedmiotów;
- dodać walidator komponentów, rezerwowanie, zużycie i rozmontowanie;
- wyliczać czas, zastosowania, modifier oraz ryzyko z policy silnika;
- rozdzielić jednorazową improwizację podczas testu od budowy przedmiotu na później.

Kryterium wyjścia: te same reguły obsługują taran, drabinę i dźwignię bez trzech
predefiniowanych template'ów.

### Etap 4: kontrakt LLM i UI

Status: ukończony 2026-07-15. LLM wybiera cel oraz ugruntowane komponenty i tłumaczy
opis funkcji gracza na wymagane/preferowane właściwości. Deterministyczny silnik
wybiera wyłącznie istniejące źródła, wylicza konsekwencje, a UI wymaga potwierdzenia
przed zmianą stanu i pozwala rozmontować aktywną konstrukcję.

- przekazywać LLM wyłącznie widoczne lub odkryte źródła wraz z identyfikatorami;
- wymagać strukturalnej propozycji komponentów i celu, bez własnych wartości
  mechanicznych;
- dodać czytelne komunikaty o brakujących lub zajętych komponentach;
- pokazać w czacie krok potwierdzenia: konstrukcja, komponenty, czas, test i ryzyko;
- pokazać aktywne przedmioty tymczasowe, ich użycia oraz akcję rozmontowania.

Kryterium wyjścia: gracz nigdy nie widzi technicznego błędu brakującego ID i przed
utworzeniem konstrukcji rozumie konsekwencje decyzji.

### Etap 5: stan instancji i snapshot

Status: ukończony 2026-07-15.

- zapisywać stan fixture'ów, dostępność itemów, rezerwacje i konstrukcje;
- odtwarzać je po opuszczeniu i ponownym wejściu do interakcji;
- wygaszać elementy zgodnie z zakresem, nie bezwarunkowo po zamknięciu czatu;
- zapewnić kompatybilny odczyt snapshotów zawierających obecne template'y.

Kryterium wyjścia: powrót do sceny zachowuje wyłamany zawias, zabrane deski,
zarezerwowaną linę i wcześniej zbudowaną drabinę.

### Etap 6: migracja sceny referencyjnej

Status: ukończony 2026-07-15. Brama nie zawiera już template'u taranu, a testy
referencyjne pokrywają taran, drabinę, dźwignię, niepasujące materiały oraz konflikt
o zarezerwowaną linę.

- przepisać bramę strażnicy na fixture'y oraz ustrukturyzowane materiały;
- usunąć template `improvised_battering_ram` z contentu bramy;
- dodać scenariusze testowe: taran, drabina, dźwignia, brak materiałów oraz próba
  równoczesnego wykorzystania tej samej liny;
- kompatybilność starego `available_materials` i template'ów pozostawić tylko na
  granicy loadera do czasu formalnej migracji wersji schematu contentu.

## Zmiana formularza interakcji

Każdy nowy formularz powinien jawnie odpowiedzieć na cztery grupy pytań:

1. **Fixture'y:** co jest trwałą częścią sceny, jakie ma właściwości i stan, czy jest
   przenośne, odłączalne albo zniszczalne oraz co powstaje po zmianie stanu.
2. **Dostępne itemy i materiały:** które pozycje odwołują się do katalogu, jaka jest
   ich ilość, stan, widoczność i właściciel.
3. **Crafting i improwizacja:** czy są dozwolone, jakie funkcjonalne cele mają sens,
   jakie koszty i ryzyka może ustalać policy oraz jaki jest zakres konstrukcji.
4. **Trwałe zmiany instancji:** które modyfikacje muszą przetrwać powrót do sceny i
   które komponenty są zużywane, rezerwowane albo odzyskiwalne.

Formularz nie powinien wymagać listy wszystkich możliwych gotowych konstrukcji.
Przykłady deklaracji służą testom i promptom, ale nie są zamkniętą listą rozwiązań.

## Przewidywane obszary kodu

- `src/dnd_board_game/inventory/` — definicje i instancje przedmiotów;
- `src/dnd_board_game/exploration/` — fixture'y, crafting i przedmioty tymczasowe;
- `src/dnd_board_game/scenarios/loader.py` — parsing i walidacja contentu;
- `src/dnd_board_game/llm/gm_classifier.py` oraz prompty — uziemiona propozycja;
- `src/dnd_board_game/ui/` — potwierdzenie, prezentacja i komunikaty;
- `src/dnd_board_game/save/session_snapshot.py` — trwały stan instancji;
- `content/items/`, `content/llm/` i scenariusze — katalogi oraz dane;
- odpowiednie testy jednostkowe loadera, domeny, klasyfikatora, UI i snapshotu.

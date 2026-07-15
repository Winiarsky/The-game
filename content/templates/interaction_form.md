# Formularz Interakcji

## 1. Typ Interakcji
NPC / obiekt / lokacja / przeszkoda / wydarzenie

## 2. Nazwa


## 3. Gdzie Na Mapie
Strefa/lokacja:
Pole albo obszar na planszy:
Czy jest jawna od początku? tak/nie/warunkowo

## 4. Opis Dla Graczy


## 5. Informacje Dla MG / LLM


## 6. Rola Interakcji W Scenie
- cel sceny
- trop/informacja
- zasób
- ryzyko/komplikacja
- przejście do innej lokacji
- walka/encounter
- klimat
- inne

## 7. Stan Początkowy
Dla NPC:
- emocje:
- zdrowie:
- nastawienie do drużyny:
- co robi teraz:

Dla obiektu/lokacji:
- stan fizyczny:
- czy jest zamknięty/uszkodzony/aktywny:
- czy jest niebezpieczny:

## 7A. Elementy Sceny (Fixture'y)
Wypisz istotne części tej konkretnej sceny. Nie wpisuj tu zwykłego wyposażenia drużyny.

Fixture 1:
- id robocze:
- nazwa i opis:
- stan początkowy:
- właściwości mechaniczne (tagi):
- czy jest widoczny od razu:
- czy jest przenośny: tak/nie
- czy jest odłączalny albo zniszczalny:
- co może powstać po odłączeniu/zniszczeniu:
- jaka zmiana stanu ma zostać zapisana przy powrocie do sceny:
- dozwolone operacje `/akcja` (`detach`, `damage`, `destroy`, `move`, `open`, `close`, `repair`):
- dla każdej operacji: dozwolone stany początkowe, stan wynikowy, ability/skill, difficulty tier:
- postęp, hałas i komplikacja sukcesu/porażki:
- czy sukces wyłącza fixture i ujawnia `yield_items`:

Operacja musi być opisana w `action_policies` fixture'a. LLM może rozpoznać cel i
rodzaj zmiany, ale mechanika oraz wynikowy stan pochodzą wyłącznie z tych danych.

## 7B. Dostępne Przedmioty I Materiały
Wypisz tylko elementy istotne dla interakcji. Użyj `definition_id` z katalogu, jeśli
to powtarzalny przedmiot; jednorazowe elementy opisz jako fixture'y powyżej.

Element 1:
- id instancji:
- definition_id albo lokalny opis:
- ilość i stan:
- właściwości lokalnie dodane/zmienione:
- właściciel albo miejsce:
- widoczność/dostępność:
- miejsce docelowe po `/weź`: `actor_inventory` / `party_treasure` / `scenario_quest`:
- czy użycie zużywa, rezerwuje czy tylko wykorzystuje element:
- co dzieje się po znalezieniu: pozostaje w scenie / wymaga osobnej akcji zabrania / jawny efekt scenariusza przyznaje zasób:

Widoczny i dostępny element może zostać znaleziony przez `/szukaj` bez rzutu. Autor
opisuje jego właściwości z katalogu, LLM przekłada funkcję podaną przez gracza na
wymagane i preferowane właściwości, a runtime wybiera wyłącznie istniejące elementy.
Nie dopisuj ręcznie aliasów nazw przedmiotów do sceny.
Samo znalezienie nie oznacza dodania do ekwipunku. `/weź` sprawdza `portable` oraz
`collection_destination`, pokazuje transfer do akceptacji i dopiero potem usuwa
ilość ze sceny. Automatyczne przyznanie bez deklaracji gracza nadal wymaga jawnego
efektu scenariusza.

## 7C. Crafting I Improwizacja
- czy crafting jest dozwolony:
- jakie funkcjonalne cele mają tu sens (np. wspinanie, dźwignia, ciężkie uderzenie):
- typowy koszt czasu:
- czy wymagany jest test i od czego zależy trudność:
- typowe ryzyka wynikające ze stanu materiałów:
- zakres konstrukcji: interakcja/scena/scenariusz
- co można odzyskać po rozmontowaniu:
- twarde ograniczenia (czego nie da się zbudować z dostępnych elementów):

Bezpośrednie użycie istniejącego elementu w tej samej deklaracji jest improwizowanym
użyciem, a nie craftingiem. Crafting stosuj dopiero, gdy gracze rzeczywiście składają
lub przerabiają konstrukcję do późniejszego użycia.

Nie definiuj gotowych konstrukcji dla `/zbuduj`. Wskaż cele funkcjonalne oraz ich
wymagania właściwościowe. Gdy gracz nie ogranicza listy materiałów, runtime dobiera
brakujące komponenty deterministycznie i pokazuje propozycję przed zmianą stanu.
Jeżeli gracz mówi „tylko z tych elementów”, dobór automatyczny jest wyłączony i
deklarowany komplet musi sam spełnić wymagania.

Dla `/użyj` określ, które właściwości i stan elementu wpływają na zastosowanie,
jakie ryzyko może wystąpić oraz czy element pozostaje dostępny po rozstrzygnięciu.
Runtime musi związać próbę z konkretnym `source_id`; opis MG nie może podmienić źródła.

## 8. Fakty Sceny Dla Rozmowy Z MG
Nie twórz listy gotowych rozwiązań. Opisz fakty, właściwości, ryzyka i ograniczenia,
z których gracze mogą samodzielnie zbudować podejście.

Fakt 1:
- id:
- treść naturalnym językiem:
- rodzaj: `observation` / `affordance` / `risk` / `constraint`
- widoczność: `obvious` / `hint` / `hidden`
- minimalny poziom podpowiedzi: 0-3
- flagi wymagane do ujawnienia ukrytego faktu:
- dla `constraint`: frazy deklaracji używane do deterministycznego odrzucenia:

Zasady:
- `obvious` używa poziomu 0 i opisuje coś dostępnego bez rzutu;
- `hint` używa poziomu 1-3 i może naprowadzać, ale nie zastępuje deklaracji;
- `hidden` pozostaje za kurtyną, dopóki nie spełni warunku ujawnienia;
- twarde ograniczenia zapisuj jako `constraint`, nie jako listę zakazanych rozwiązań.

## 9. Zasady Odpowiadania MG
- na jakie pytania MG odpowiada od razu z faktów `obvious`:
- kiedy odpowiedź staje się stopniowaną podpowiedzią:
- kiedy potrzebna jest aktywna obserwacja i test:
- czego MG nie może potwierdzić na podstawie porażki:

## 10. Intencje
Opisz słownie albo uzupełnij szkic:

```json
{
  "social": "allowed",
  "information": "locked",
  "medical": "allowed",
  "theft": "allowed_with_consequence",
  "harm": "allowed_with_consequence",
  "magic": "blocked"
}
```

## 11. Aktywne I Stopniowane Obserwacje (opcjonalne)
Użyj tej sekcji tylko wtedy, gdy samo pytanie nie wystarcza i bohater musi aktywnie
coś zbadać, nasłuchiwać, śledzić albo obserwować.

- id obserwacji:
- skąd można obserwować / czego dotyczy:
- przykładowe deklaracje graczy:
- cecha / umiejętność:
- uczestnicy testu:
- komunikat poniżej najniższego progu (nie może potwierdzać braku zagrożenia):
- próg 1 — minimalny wynik, id faktu, narracja, flaga/efekty:
- próg 2 — minimalny wynik, id faktu, narracja, flaga/efekty:
- próg 3 — minimalny wynik, id faktu, narracja, flaga/efekty:
- opcjonalna nagroda progu `encounter_edge` — typ, id triggera encountera, etykieta:
- czy nagroda ma trafić do bohatera prowadzącego test i dlaczego:

## 12. Możliwe Efekty Mechaniczne
- ustawia flagę:
- daje zasób:
- zabiera zasób:
- ujawnia punkt:
- odblokowuje lokację:
- zaczyna walkę:
- dodaje komplikację:
- zmienia nastawienie NPC:
- inne:

## 13. Testy I Trudności
Czy chcesz konkretne ST, czy LLM ma dobrać tier z policy?

Dla jakich sytuacji:
- uspokojenie NPC:
- leczenie:
- przeszukanie:
- kradzież:
- zastraszenie:
- badanie śladów:

## 14. Sukces / Porażka / Krytyczne Wyniki
Sukces:
- co się dzieje:
- jaki efekt mechaniczny:

Porażka:
- co się dzieje:
- jaki efekt mechaniczny:

Krytyczny sukces:
- co dodatkowo:

Krytyczna porażka:
- co się pogarsza:

## 15. Limity I Parametry
- maksymalna nagroda:
- minimalna/maksymalna stawka:
- liczba prób:
- koszt czasu:
- poziom hałasu:
- limit zasobów:

## 16. Czy Interakcja Ma Progres?
Tak/nie

Jeśli tak:
- ile punktów postępu potrzeba:
- co daje postęp:
- co kończy interakcję:

## 17. Konsekwencje Długoterminowe
- NPC pamięta:
- zmienia się reputacja:
- odblokowuje quest:
- zmienia encounter:
- wpływa na zakończenie sceny:
- zmienia stan fixture'a:
- zużywa/rezerwuje/uwalnia item albo materiał:
- czy zmiana musi przetrwać opuszczenie i ponowne wejście do interakcji:

### Jeśli interakcja uruchamia encounter
- id challenge'a dostarczającego stan rozpoczęcia:
- domyślny wynik: drużyna zaskakuje / nikt / przeciwnicy zaskakują
- uporządkowane reguły (pierwsza pasująca wygrywa):
  - próg lub zakres hałasu:
  - wymagane i zabronione flagi rozpoznania:
  - tagi kończącego podejścia:
  - wynik i narracja dla graczy:

## 18. Przykładowe Deklaracje Graczy
- "..."
- "..."
- "..."

## 19. Oczekiwany Feeling
- napięcie
- tajemnica
- humor
- moralny dylemat
- szybka przeszkoda
- ważna rozmowa
- groza
- inne

## 20. Uwagi

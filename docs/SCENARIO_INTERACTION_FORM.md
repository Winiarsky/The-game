# Formularz Interakcji Scenariusza

Ten formularz służy do projektowania spójnych interakcji dla NPC, obiektów, lokacji, przeszkód i wydarzeń.

Cel: autor scenariusza opisuje interakcję po ludzku, a implementacja przekłada ją na JSON contentu, `intent_permissions`, flagi, efekty mechaniczne, testy i ewentualne brakujące prymitywy runtime.

## Zasady

- LLM strukturyzuje deklaracje graczy, ale nie wykonuje efektów gry.
- Każdy efekt zmieniający stan gry musi mieć znany prymityw mechaniczny, np. `set_flag`, `grant_resource`, `reveal_information`, `start_challenge`, `offer_trade`.
- Globalne intencje powinny pochodzić z katalogu systemowego, a lokalna interakcja tylko je dopuszcza, blokuje albo ogranicza przez `intent_permissions`.
- Content szczegółowy należy do scenariusza, nie do kodu runtime.
- LLM może wskazywać wyłącznie istniejące identyfikatory itemów, materiałów i fixture'ów;
  dostępność, właściwości, koszty oraz zmiany stanu waliduje deterministyczny runtime.
- Powtarzalne przedmioty odwołują się do katalogu, a jednorazowe części otoczenia
  należy opisywać lokalnie jako fixture'y sceny.
- Sekcja `Informacje Dla MG / LLM` zawsze powinna być rozbita na `Prawda Scenariusza`, `Zasady Prowadzenia` oraz `Wiedza I Ograniczenia`.
- Jeśli czegoś nie da się jeszcze wyrazić istniejącym prymitywem, formularz powinien to ujawnić jako zadanie implementacyjne.

## Pełny Formularz

```markdown
# Formularz Interakcji

## 1. Typ Interakcji
NPC / obiekt / lokacja / przeszkoda / wydarzenie

## 2. Nazwa
Jak interakcja ma się nazywać w scenariuszu?

## 3. Gdzie Na Mapie
Strefa/lokacja:
Pole albo obszar na planszy:
Czy jest jawna od początku? tak/nie/warunkowo

## 4. Opis Dla Graczy
Co gracze widzą/słyszą/czują od razu?

## 5. Informacje Dla MG / LLM
Krótki opis kontekstu dla MG/LLM:

### Prawda Scenariusza
Fakty, które są obiektywnie prawdziwe w scenariuszu, nawet jeśli gracze jeszcze ich nie znają.
- fakt:
- fakt:
- fakt:

### Zasady Prowadzenia
Jak MG/LLM ma prowadzić tę interakcję przy stole.
- co nagradzać:
- czego nie zdradzać od razu:
- kiedy dawać podpowiedzi:
- jaki ton utrzymać:

### Wiedza I Ograniczenia
Co NPC/obiekt/lokacja wie, czego nie wie i czego nie może zrobić.
- czego NPC/obiekt chce:
- czego się boi:
- czego nie wie:
- jakie są ważne ograniczenia świata:
- jakie założenia graczy trzeba odrzucać:

## 6. Rola Interakcji W Scenie
Po co ta interakcja istnieje?
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
Które istotne elementy należą do tej konkretnej instancji sceny?

Fixture 1:
- id robocze:
- nazwa i opis:
- stan początkowy:
- właściwości mechaniczne (tagi z katalogu):
- czy jest widoczny od razu:
- czy jest przenośny: tak/nie
- czy jest odłączalny albo zniszczalny:
- co może powstać po odłączeniu/zniszczeniu:
- jaka zmiana stanu ma zostać zapisana przy powrocie do sceny:
- dozwolone operacje `/akcja` (`detach`, `damage`, `destroy`, `move`, `open`, `close`, `repair`):
- dla każdej operacji: dozwolone stany początkowe, stan wynikowy, ability/skill, difficulty tier:
- postęp, hałas i komplikacja sukcesu/porażki:
- czy sukces wyłącza fixture i ujawnia `yield_items`:

Każda trwała operacja wymaga wpisu w `action_policies`. Analyzer wybiera wyłącznie
istniejący `source_id` i operację, natomiast runtime narzuca parametry próby,
stosuje zmianę stanu oraz zapisuje ją w snapshocie.

## 7B. Dostępne Przedmioty I Materiały
Wpisz tylko elementy istotne dla interakcji. Powtarzalny przedmiot powinien używać
`definition_id` z katalogu; jednorazowy element otoczenia powinien być fixture'em.

Element 1:
- id instancji:
- definition_id albo lokalny opis:
- ilość i stan:
- właściwości lokalnie dodane/zmienione:
- właściciel albo miejsce:
- widoczność/dostępność:
- miejsce docelowe po `/weź`: `actor_inventory` / `party_treasure` / `scenario_quest`:
- czy użycie zużywa, rezerwuje czy tylko wykorzystuje element:
- zachowanie po znalezieniu: pozostaje w scenie / wymaga osobnej akcji zabrania / jawny efekt scenariusza przyznaje zasób:

Widoczny i dostępny element może zostać znaleziony przez `/szukaj` bez testu. Autor
przypisuje mu właściwości z katalogu. LLM przekłada opis funkcji gracza na właściwości
wymagane i preferowane, a runtime wybiera tylko istniejące elementy sceny. Formularz
nie powinien zawierać ręcznych aliasów w rodzaju „kij = deska”.
Znalezienie zapisuje wiedzę drużyny o elemencie sceny, ale nie przenosi go do
ekwipunku. `/weź` wykonuje osobny, potwierdzany transfer zgodny z `portable` i
`collection_destination`. Automatyczne przyznanie bez deklaracji gracza wymaga
jawnego, deterministycznego efektu scenariusza.

## 7C. Crafting I Improwizacja
- czy crafting jest dozwolony:
- jakie funkcjonalne cele mają tu sens:
- typowy koszt czasu:
- czy wymagany jest test i od czego zależy trudność:
- typowe ryzyka wynikające ze stanu materiałów:
- zakres konstrukcji: interakcja/scena/scenariusz
- co można odzyskać po rozmontowaniu:
- twarde ograniczenia:

Bezpośrednie użycie istniejącego elementu w tej samej deklaracji powinno trafić do
`improvised_tool_check`. Pełny crafting jest właściwy dopiero przy składaniu albo
przerabianiu konstrukcji przeznaczonej do późniejszego użycia.

`/zbuduj` opisuj przez cele funkcjonalne i wymagane właściwości, nigdy przez listę
gotowych drabin, taranów czy dźwigni. Runtime może deterministycznie uzupełnić
komponenty z dostępnych źródeł, chyba że gracz jawnie ograniczył budowę do dokładnie
wskazanego zestawu. Podgląd musi pokazać finalny dobór przed akceptacją.

Dla `/użyj` opisz wpływ właściwości i stanu elementu, ryzyko oraz jego dostępność po
rozstrzygnięciu. Deklaracja musi zostać związana z jednym istniejącym `source_id`,
a propozycja MG nie może zmienić wskazanego przez gracza źródła.

## 8. Fakty Sceny Dla Rozmowy Z MG
Nie wypisuj katalogu gotowych rozwiązań. Opisz prawdziwe fakty i właściwości sceny,
z których gracze oraz MG mogą składać nieprzewidziane podejścia.

Fakt 1:
- id stabilne w obrębie scenariusza:
- treść naturalnym językiem:
- rodzaj: `observation` / `affordance` / `risk` / `constraint`
- widoczność: `obvious` / `hint` / `hidden`
- `minimum_hint_level`: 0-3
- `reveal_if_flags`: flagi wymagane do ujawnienia faktu ukrytego
- `match_phrases`: dla `constraint` konkretne frazy deklaracji używane przez walidator

Znaczenie pól:
- `observation` opisuje stan albo właściwość świata;
- `affordance` wskazuje możliwe zastosowanie istniejącej właściwości, ale nie nakazuje rozwiązania;
- `risk` opisuje możliwy koszt albo komplikację;
- `constraint` jest twardym ograniczeniem świata;
- `obvious` jest dostępne bez testu i zawsze używa poziomu 0;
- `hint` jest ujawniane stopniowo i używa poziomu 1-3;
- `hidden` pozostaje za kurtyną, dopóki nie zostaną spełnione warunki ujawnienia.

## 9. Zasady Odpowiadania MG
- na jakie pytania MG odpowiada bez rzutu z faktów `obvious`:
- kiedy pytanie może odsłonić `affordance` albo `risk` jako podpowiedź:
- kiedy potrzebna jest aktywna obserwacja i test:
- czego porażka nie może potwierdzić:
- jaki bezpieczny komunikat zwrócić, gdy pytanie wykracza poza dostępny poziom wiedzy:

## 10. Intencje
Które globalne intencje mają sens?

Możesz opisać słownie albo użyć szkicu:

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

Użyj tej sekcji, gdy jedno aktywne badanie może ujawnić kilka warstw informacji.
Progi odnoszą się do końcowego wyniku jednego testu i są kumulatywne. Komunikat
poniżej pierwszego progu nie może stwierdzać, że ukrytego obiektu albo zagrożenia nie ma.

- id obserwacji:
- strefa oraz opcjonalne aktywne wyzwanie:
- opis punktu obserwacji i ograniczeń widoku:
- przykładowe deklaracje pasujące do obserwacji:
- cecha / umiejętność:
- uczestnicy i agregacja testu:
- tryb rzutu:
- komunikat poniżej najniższego progu:
- próg 1 — `minimum_total`, id faktu, narracja, `reveal_flag`, dodatkowe efekty:
- próg 2 — `minimum_total`, id faktu, narracja, `reveal_flag`, dodatkowe efekty:
- próg 3 — `minimum_total`, id faktu, narracja, `reveal_flag`, dodatkowe efekty:
- opcjonalna nagroda progu `encounter_edge`:
  - `type`: obecnie `initiative_advantage`
  - `encounter_trigger_id`: id dokładnie tego encountera, którego dotyczy wiedza
  - `label`: krótka, widoczna dla gracza nazwa źródła przewagi

Nagroda jest przypisana do bohatera prowadzącego test, zachowywana w zapisie sesji
i zużywana tylko przy jego rzucie inicjatywy w pasującym encounterze. Nie używaj jej,
jeżeli rozpoznanie nie daje konkretnej przewagi pozycyjnej lub czasowej.

## 12. Możliwe Efekty Mechaniczne
Co może się zmienić w stanie gry?

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

Przykłady:
- łatwe: ST 10
- średnie: ST 13
- trudne: ST 16
- bardzo trudne: ST 18+

Dla jakich sytuacji:
- uspokojenie NPC:
- leczenie:
- przeszukanie:
- kradzież:
- zastraszenie:
- badanie śladów:

## 14. Sukces / Porażka / Krytyczne Wyniki
Dla głównych typów działań:

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
Czy są wartości liczbowe?
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
Czy to ma wrócić później?
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
  - tagi kończącego podejścia, np. `heavy_force`:
  - wynik i narracja widoczna dla graczy:
- czy scena naprawdę potrzebuje dokładnego, indywidualnego testu Stealth vs passive Perception:

## 18. Przykładowe Deklaracje Graczy
Podaj 3-8 zdań, które gracze mogliby wpisać:

- "..."
- "..."
- "..."

## 19. Oczekiwany Feeling
Jak to ma się czuć przy stole?
- napięcie
- tajemnica
- humor
- moralny dylemat
- szybka przeszkoda
- ważna rozmowa
- groza
- inne

## 20. Uwagi
Cokolwiek dodatkowego.
```

## Krótki Formularz

Użyj tego wariantu, jeśli interakcja jest jeszcze tylko pomysłem.

```markdown
# Krótki Formularz Interakcji

Typ:
Nazwa:
Gdzie:
Opis dla graczy:
Informacje dla MG / LLM:
Prawda scenariusza:
Zasady prowadzenia:
Wiedza i ograniczenia:
Fixture'y i ich stan:
Dostępne itemy i materiały:
Crafting/improwizacja oraz ograniczenia:
Po co istnieje:
Fakty sceny (`id`, treść, rodzaj, widoczność, poziom podpowiedzi, warunki):
Zasady odpowiadania MG:
Aktywne obserwacje wymagające testu:
Efekty mechaniczne:
Przykładowe deklaracje graczy:
Feeling:
```

Szczegółowy plan docelowego modelu znajduje się w
`docs/SCENE_ITEMS_AND_CRAFTING_PLAN.md`.

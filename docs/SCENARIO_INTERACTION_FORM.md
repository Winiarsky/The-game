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

## 6A. Cele Widoczne Dla Graczy
Karty opisują rezultat, który drużyna chce osiągnąć, a nie gotową metodę ani kwestię dialogową.

Cel 1:
- id:
- etykieta:
- krótki opis:
- opcjonalny obraz kafelka (`image`, ścieżka względem katalogu scenariusza):
- pytanie „jak to robicie?” po wyborze:
- resolver (`resolution_mode`):
  - `automatic` — deterministyczny skutek bez rzutu i bez oceny LLM,
  - `check` — fizyczny d20 i reguły 5e; opis może wpływać tylko przez
    autorskie reguły metod,
  - `llm_rubric` — opis ocenia LLM według jawnego `llm_rubric`, bez rzutu,
  - `conversation` — swobodna rozmowa bez automatycznego testu:
- pole opisu (`description_mode`): `none` / `optional` / `required`:
- deklaracja używana przy `none` (`default_declaration`):
- kryteria oceny przy `llm_rubric`:
- dozwolone intencje NPC (`intent_ids`), jeśli dotyczy:
- sugerowane tagi podejścia, jeśli dotyczy przeszkody:
- flagi wymagane / zabraniające pokazania (tylko interakcja bez flowgrafu):
- tryb wyboru uczestników: `must` / `allow`
- domyślny albo wymagany model: `single_actor` / `lead_with_help` / `whole_party`
- modele dozwolone przy `allow`:
- dozwolone aktywne obserwacje (`observation_ids`) — tylko bez flowgrafu; przy
  grafie lista należy do przejścia:
- domyślna stopniowana obserwacja (`default_observation_id`) — tylko bez
  flowgrafu; przy grafie należy do przejścia:
- proceduralne użycia znanych elementów (`source_actions`):
  - id użycia:
  - `source_ref`: id istniejącego itemu albo fixture'a sceny:
  - `option_id`: autorski profil testu i konsekwencji:
  - widoczna nazwa oraz narracja:

Autor wybiera jedną z dwóch polityk:

- `must`: kafelek wymusza jeden model;
- `allow`: kafelek zawiera listę dozwolonych modeli, a UI wyprowadza wybór z
  uczestników wskazanych przed opisaniem metody: pierwszy bohater prowadzi, drugi
  pomaga, a osobny przycisk wybiera całą drużynę.

Modele testu:

- `single_actor`: dokładnie jedna postać;
- `lead_with_help`: prowadzący i opcjonalnie jeden zdolny pomocnik; pomoc daje
  prowadzącemu przewagę, a pomocnik nie rzuca osobno;
- `whole_party`: cała drużyna rzuca, a klasyczny test grupowy zdaje co najmniej
  połowa drużyny.

LLM opisuje wybraną metodę i wskazane role, ale nie zmienia wybranego modelu.
W propozycji MG nie wybiera się tych postaci ponownie: karta pokazuje ustalonego
prowadzącego, pomocnika albo całą drużynę.

Znane połączenie elementu z działaniem, np. `deska → podważ rygiel`, powinno być
`source_action`, a nie ponownie zgadywanym `improvised_tool`. Runtime rozpoznaje
istniejący `source_ref`, podstawia wskazany profil i nie pyta LLM o mechanikę.

Dla wyzwania prowadzonego przez flowgraf nie dodawaj ogólnego celu `Własny plan`
ani `Własny sposób`. Kafelek określa rezultat, a pole „Jak to robicie?” pozostawia
graczom swobodę metody. Jeśli ważny zamiar nie mieści się w żadnym celu, dodaj
konkretny kafelek rezultatu zamiast furtki omijającej graf.

Dla NPC prowadzonego przez flowgraf stosuj tę samą zasadę. Graf ma `npc_id`, a
każde przejście celu używa `route_kind: npc_intent` oraz `route_ref` wskazującego
jedną intencję z `intent_permissions`. Dostępność kafelków należy wtedy do
węzłów grafu, nie do powielonych flag na celu. Gracze wybierają prowadzącego i
opcjonalnego pomocnika przed wpisaniem argumentu lub sposobu działania.

## 6B. Reguły Metod I Kompromisów
Wpisuj tylko reguły, które silnik ma stosować deterministycznie po rozpoznaniu
konkretnego opisu graczy. Karta celu sama nie daje premii.

Reguła 1:
- id:
- cele, których dotyczy:
- frazy albo sygnały metody:
- wymagany istniejący przedmiot, fixture lub właściwość:
- modyfikator od -2 do +2:
- zmiana hałasu:
- inne ograniczenie ryzyka:
- widoczne uzasadnienie:

## 6C. Kluczowe Kwestie NPC
Kluczowa kwestia jest autorskim priorytetem, drażliwym tematem, pokusą, strachem,
twardą granicą albo wyjątkiem. Gracz nie musi widzieć rozwiązania na karcie celu.

Kwestia 1:
- id:
- rodzaj: `priority` / `sensitivity` / `temptation` / `fear` / `hard_boundary` / `exception`
- widoczność: `obvious` / `hint` / `hidden`
- czego dotyczy:
- cele rozmowy, przy których może zadziałać:
- frazy lub semantyczne sygnały deklaracji:
- wymagane ugruntowanie, np. realne monety albo posiadany przedmiot:
- efekt natychmiastowy:
- odblokowywane lub blokowane cele/intencje:
- narracja i kwestia NPC:
- kiedy uważa się ją za zużytą:

Twarda granica blokuje test, dopóki nie zadziała autorski wyjątek. Naturalne 20 nie
omija rozkazu, braku zasobu ani niemożliwości świata.

## 6D. Styl Narracji
Jeśli sekcja zostanie pominięta, obowiązuje `heroic_dnd`: bohaterskie power fantasy,
lekka ironia, sytuacyjny humor i poważne traktowanie konsekwencji.

Styl bazowy instancji:
- `preset`: stabilna nazwa profilu:
- `tone`: opis głosu i energii sceny:
- `humor_level`: `none` / `light` / `medium` / `high`
- `irony_level`: `none` / `light` / `medium` / `high`
- `dramatic_intensity`: `none` / `light` / `medium` / `high`
- `guidance`: czego pilnować i czego unikać:

Każdy cel z sekcji 6A może opcjonalnie zawierać własne `narrative_style`. Pełny
profil celu nadpisuje wtedy profil instancji. Używaj tego dla wyjątków, np.
karczemnej bójki prowadzonej z humorem albo poważnego wyznania bez ironii.

## 6E. Flowgraf Wyzwania

Dla interakcji, której dostępne cele zmieniają się wraz ze stanem sceny, opisz
deterministyczny graf:

- id grafu oraz id wyzwania:
- węzły stanu wyprowadzane z flag (`all_flags`, `any_flags`, `no_flags`):
- które węzły są terminalne:
- dla każdego przejścia:
  - stabilne id:
  - id kafelka celu:
  - wymagane aktywne węzły:
  - rodzaj resolvera: `challenge_option` / `observation_router`:
  - id autorskiej opcji albo lista obserwacji:
  - opcjonalna domyślna obserwacja:
  - opcjonalne proceduralne `source_action_ids`:

Flowgraf decyduje, które kafelki są widoczne i do jakiej mechaniki prowadzą.
Wybrany kafelek jest jedynym wejściem do działania. LLM interpretuje metodę opisaną
w jego polu, ale nie wybiera innego celu, nie aktywuje zablokowanej krawędzi i nie
wymyśla skutków mechanicznych.

W wyzwaniu posiadającym graf nie duplikuj na kafelkach `required_flags`,
`forbidden_flags`, `resolution_option_id`, `observation_ids` ani
`default_observation_id`. Definicje proceduralnych `source_actions` pozostają przy
kafelku jako treść działania, ale przejście grafu wskazuje aktywne identyfikatory.

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
- dozwolone operacje strukturalne (`detach`, `damage`, `destroy`, `move`, `open`, `close`, `repair`):
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
- miejsce docelowe po zabraniu: `actor_inventory` / `party_treasure` / `scenario_quest`:
- czy użycie zużywa, rezerwuje czy tylko wykorzystuje element:
- zachowanie po znalezieniu: pozostaje w scenie / wymaga osobnej akcji zabrania / jawny efekt scenariusza przyznaje zasób:

Widoczny i dostępny element może zostać znaleziony przez `/szukaj` bez testu. Autor
przypisuje mu właściwości z katalogu. LLM przekłada opis funkcji gracza na właściwości
wymagane i preferowane, a runtime wybiera tylko istniejące elementy sceny. Formularz
nie powinien zawierać ręcznych aliasów w rodzaju „kij = deska”.
Znalezienie zapisuje wiedzę drużyny o elemencie sceny, ale nie przenosi go do
ekwipunku. Akcja zabrania wykonuje osobny, potwierdzany transfer zgodny z `portable` i
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

Budowanie opisuj przez cele funkcjonalne i wymagane właściwości, nigdy przez listę
gotowych drabin, taranów czy dźwigni. Runtime może deterministycznie uzupełnić
komponenty z dostępnych źródeł, chyba że gracz jawnie ograniczył budowę do dokładnie
wskazanego zestawu. Podgląd musi pokazać finalny dobór przed akceptacją.

Dla użycia elementu opisz wpływ właściwości i stanu, ryzyko oraz jego dostępność po
rozstrzygnięciu. Deklaracja musi zostać związana z jednym istniejącym `source_id`,
a propozycja MG nie może zmienić wskazanego przez gracza źródła.

Komendy z ukośnikiem pozostają formatem diagnostycznym kompatybilności. Gracze
korzystają z kart celów i opisują metodę naturalnym językiem.

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

### 11A. Kontekstowe Poszukiwania

Dla karty typu „Rozejrzyjcie się” rozdziel dwa rodzaje szukania:

- oczywisty materiał opisany funkcją, np. „coś ciężkiego na taran” — bez rzutu;
  LLM tworzy semantyczne `source_query`, a silnik dopasowuje wyłącznie istniejące
  elementy po ich właściwościach;
- ukryta informacja, słabość, pułapka, narzędzie lub droga — przypisana obserwacja
  i rzut z progami;
- szerokie „coś przydatnego/interesującego” — `default_observation_id`, jeden rzut
  i kumulatywne warstwy znalezisk.

Dla każdej intencji poszukiwawczej podaj:

- czego gracz szuka funkcjonalnie, nie tylko dokładną nazwą;
- czy wynik jest oczywisty (`source_query`) czy ukryty (`observation_id`);
- przykłady różnych naturalnych opisów intencji;
- przy ukrytym wyniku: test, progi, flagi i efekty;
- co zmienia się w widocznych kartach po odkryciu;
- czy znalezisko daje przewagę w późniejszym encounterze.

`intent_examples` uczą znaczenia wypowiedzi i pomagają lokalnemu matcherowi, ale
nie są zamkniętą listą haseł. LLM ma rozpoznawać parafrazy, np. „belka do rozwalenia
wrót” tak samo jak „materiał na taran”.

## 11B. Swobodna Rozmowa Z MG

Pole „Napisz wiadomość do MG” nie deklaruje działania. MG może:

- odpowiedzieć na jawny fakt sceny;
- wyjaśnić, co bohaterowie widzą albo już wiedzą;
- ironicznie naprowadzić na sposób samodzielnego sprawdzenia tajemnicy;
- odmówić ujawnienia ukrytej informacji przed działaniem.

Rozmowa nie tworzy rzutu, pendingu ani efektu świata. Działanie rozpoczyna się
wyłącznie z wybranej karty celu i osobnego pola „Jak to robicie?”.

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

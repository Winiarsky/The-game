# Roadmap Projektu

## Cel Końcowy

Docelowo projekt ma być lokalną, planszowo-cyfrową implementacją Dungeons & Dragons
5e, która:

- prowadzi zasady walki, eksploracji i scen społecznych,
- korzysta z fizycznej planszy, figurek, kości i LED,
- posiada walidowany, data-driven katalog dozwolonego contentu D&D,
- obsługuje bohaterów, potwory, przedmioty, czary i scenariusze,
- ma moduł tworzenia bohaterów,
- ma moduł tworzenia i walidowania scenariuszy,
- pozwala rozgrywać oraz zapisywać scenariusze i kampanie bez edycji plików ręcznie.

Roadmapa opisuje kolejność zależności. `TODO.md` zawiera tylko najbliższe
zadania wykonawcze, a `docs/DND_IMPLEMENTATION_MATRIX.md` pokazuje aktualny stan
poszczególnych rodzin zasad.

## Rekomendowany Model Rozwoju

Ogólny kierunek jest następujący:

```text
kontrakty silnika
    -> mechaniki ogólne
        -> mały content testowy
            -> pełniejsze katalogi contentu
                -> rasy/species, backgroundy i klasy
                    -> kreator bohatera
                        -> kreator scenariusza i kampanii
```

Nie należy jednak implementować wszystkich mechanik bez żadnego contentu, a potem
dopiero zaczynać dane. Każdą nową mechanikę trzeba potwierdzić małym zestawem
fixture'ów: zwykle dwoma lub trzema czarami, przedmiotami, potworami albo fragmentami
scenariusza. Dopiero po ustabilizowaniu kontraktu można masowo rozbudowywać katalog.

Taki model chroni przed dwoma problemami znanymi z legacy:

- logiką konkretnej klasy, czaru albo scenariusza zaszytą w runtime,
- dużą ilością contentu zależną od schematów, które trzeba później masowo migrować.

## Reguły Kolejności

1. Najpierw powstaje ogólny prymityw mechaniczny.
2. Następnie powstają małe fixture'y udowadniające, że prymityw nie jest
   dopasowany tylko do jednego przypadku.
3. Mechanika trafia do UI i obserwacji sesji dopiero przez warstwę aplikacyjną.
4. Masowy content powstaje dopiero po ustabilizowaniu schematu i migracji danych.
5. Rasa albo klasa składa istniejące prymitywy. Nie może wymuszać warunku
   `if actor.class == ...` w ogólnym resolverze.
6. Edytory korzystają z tych samych schematów i walidatorów co runtime. Nie mogą
   mieć osobnego, rozjeżdżającego się modelu danych.
7. Każdy etap kończy się grywalnym vertical slice'em i bramką jakości.

## Definition Of Done Dla Mechaniki

Mechanika jest ukończona dopiero, gdy posiada:

- czystą, deterministyczną logikę domenową,
- jawne dane wejściowe, wynik i błędy walidacji,
- co najmniej dwa reprezentatywne przypadki contentowe,
- testy jednostkowe reguł i test przepływu aplikacyjnego,
- widoczny stan, koszt, modyfikatory i niedostępność w UI,
- zdarzenia w obserwacji sesji,
- opis decyzji lub odstępstwa w `docs/RULES_DECISIONS.md`,
- wpis w macierzy implementacji,
- brak zależności od Flask, hardware, plików i realnego czasu w regułach.

## Bramka 0: Zamknięcie Zakresu Zasad I Contentu

Status: następny krok organizacyjny.

Przed masowym dodawaniem zasad i danych trzeba ustalić:

- bazową wersję reguł; rekomendacja dla pierwszego pełnego wydania to D&D 5e
  2014, ponieważ obecne modele i decyzje projektu są już do niej zbliżone,
- listę świadomych odstępstw wynikających z fizycznej planszy,
- strategię licencji i źródła danych,
- znaczenie słowa „pełny”: pełne SRD/otwarty pakiet czy dodatkowe materiały,
  do których projekt ma legalne prawo,
- wersjonowanie schematów contentu i zapisów gry,
- stabilne identyfikatory reguł i obiektów contentu.

Kryterium wyjścia:

- wersja zasad i zakres danych są zapisane w dokumentacji,
- content ma jawne pochodzenie i attribution,
- każdy format danych posiada pole wersji albo uzgodnioną strategię migracji.

# Część I: Mechaniki

## Etap M1: Wspólne Kontrakty Efektów, Czasu I Zasobów

Status: ukończony. Kontrakty efektów, czasu, zasobów, odpoczynków i snapshotu v1 mają grywalny vertical slice.

To jest fundament dla czarów, warunków, cech klasowych, odpoczynków, przedmiotów
i efektów scenariusza.

Kolejność:

1. ujednolicony model efektu i jego źródła,
2. czas trwania i punkty wygaśnięcia: tura, runda, odpoczynek, scenariusz,
3. jawne zasoby z maksimum, aktualną wartością i regułą odnowienia,
4. short rest, long rest i granica scenariusza jako cykl przygody,
5. jedno miejsce nakładania, odświeżania, zastępowania i usuwania efektów,
6. wersjonowalny snapshot stanu aktora i scenariusza.

Zaimplementowany vertical slice:

- wspólny `ActiveEffect` ze źródłem, duration, stacking key i polityką replace/refresh/stack,
- centralne nakładanie oraz wygaszanie przez zdarzenia tury, rundy, ataku, ruchu,
  koncentracji, encountera, odpoczynku i scenariusza,
- migracja efektów akcji, koncentracji, przedmiotów i obiektów sceny,
- jawne źródło i moment wygaśnięcia efektu w UI,
- ręczne zakończenie scenariusza wygaszające efekty dzienne,
- generyczne zasoby aktora odnawiane po short albo long rest,
- Hit Dice i leczenie `die + CON` wydawane pojedynczo po short reście,
- content-driven polityka short resta dla lokacji,
- godzinny koszt i jawne konsekwencje odpoczynku,
- automatyczny long rest przed przygotowaniem scenariusza,
- odnowienie HP, slotów i zasobów oraz ponowne otwarcie przygotowania czarów.
- wersjonowany snapshot v1 stanu aktora, eksploracji, efektów i opcjonalnej walki,
- atomowy zapis/odczyt JSON, jawna walidacja content ids oraz blokada zapisu w połowie decyzji,
- przyciski zapisu i odczytu w web UI oraz deterministyczny round-trip.

Fixture'y:

- przygotowanie czarów do końca scenariusza,
- zasób odnawiany po long rest,
- efekt do początku lub końca następnej tury,
- efekt koncentracyjny zastępujący poprzedni efekt.

Kryterium wyjścia:

- czas i odnowienie nie są implementowane osobno dla każdego czaru lub klasy,
- reset scenariusza, odpoczynek i zapis/odczyt dają deterministyczny wynik.

## Etap M2: Pełny Fundament Aktora I Rzutów

Kolejność:

1. proficiency bonus zależny od poziomu,
2. biegłości w skillach, save'ach, broni, pancerzach i narzędziach,
3. expertise i wielokrotne źródła modyfikatorów bez stackowania proficiency,
4. pasywne wartości, np. Passive Perception,
5. senses, rozmiar, języki i podstawowe tagi aktora,
6. stabilny model maksimum HP, Hit Dice i tymczasowego HP,
7. utrata przytomności, stabilizacja, death saves i śmierć,
8. odpoczynek oraz odzyskiwanie HP, Hit Dice i zasobów.

Kryterium wyjścia:

- bohater, NPC i potwór korzystają z tych samych podstawowych reguł,
- test cechy, save i attack roll składają modyfikatory z jednego kontraktu.

## Etap M3: Domknięcie Ruchu I Taktycznej Planszy

Kolejność:

1. wszystkie typy terenu i kosztów ruchu potrzebne przez bazowy zakres,
2. prone, wstawanie i ograniczenia ruchu,
3. Dash, Disengage i opportunity attacks w pełnym wspólnym kontrakcie,
4. cover, linia widzenia i zasłonięcie,
5. reach, rozmiary stworzeń i zajmowany obszar,
6. grapple, escape i shove,
7. skok, wspinanie, pływanie i crawling,
8. teleportacja, forced movement oraz reakcje na opuszczanie zasięgu,
9. opcjonalnie lot i wysokość, dopiero po ustaleniu reprezentacji na planszy.

Kryterium wyjścia:

- wszystkie zmiany pozycji przechodzą przez jeden zestaw reguł,
- LED pokazuje legalne pola, koszt i powód blokady bez duplikowania zasad w UI.

## Etap M4: Domknięcie Walki

Kolejność:

1. komplet ekonomii tury: action, bonus action, reaction, movement, free interaction,
2. melee/ranged, reach, disadvantage w zwarciu i cover,
3. two-weapon fighting oraz podstawowe akcje improwizowane,
4. Ready, Help, Dodge, Hide, Search i Use an Object,
5. critical hit, critical miss i wieloskładnikowe obrażenia,
6. typy obrażeń, resistance, immunity i vulnerability,
7. healing, temporary HP, damage at 0 HP i massive damage,
8. saving throws wymuszane przez ataki i efekty,
9. reakcje i przerwania rozstrzygane w jawnej kolejce,
10. zakończenie encountera, ucieczka, kapitulacja i cele inne niż wybicie strony.

Fixture'y powinny obejmować wojownika wręcz, postać dystansową, potwora z
odpornością i potwora wymuszającego save.

## Etap M5: Warunki I Ogólny Silnik Cech

Stan: punkty 1-4 mają działający vertical slice dla `Poisoned` i `Restrained`,
łącznie z odpornościami, czasem trwania, save-at-start/save-at-end, automatycznymi
rzutami przeciwników i jawnymi rzutami graczy. Punkt 5 ma pierwszy data-driven
vertical slice aury modyfikującej save według aktualnej pozycji. Punkt 6 ma wspólny
katalog zdarzeń, contentowe definicje triggerów, skutek `grant_temp_hp` i wykonanie
na początku oraz końcu tury. Pozostałe oficjalne warunki, kolejne rodzaje aur,
pozostałe emitery triggerów oraz punkty 7-8 nadal są do wdrożenia.

Kolejność:

1. generyczne modyfikatory statystyk i roll mode,
2. warunki oficjalnego bazowego zakresu,
3. immunities na warunki,
4. duration, save-at-end, save-at-start i automatyczne wygaśnięcie,
5. aury i efekty zależne od pozycji,
6. triggery: on hit, on damage, on move, turn start/end, rest i encounter end,
7. ograniczone użycia i recharge,
8. wspólny mechanizm feature definitions dla potworów, przedmiotów, ras i klas.

To jest ostatni etap, po którym wolno zacząć implementować dane ras i klas.

## Etap M6: Ekwipunek I Przedmioty

Kolejność:

1. waluta, ilość, masa i carrying capacity,
2. wyposażenie, dobywanie, chowanie i free object interaction,
3. broń, properties, amunicja i improwizowana broń,
4. pancerz, tarcza, wymogi i obliczanie AC,
5. narzędzia oraz zużywalne przedmioty,
6. charges i reguły odnowienia,
7. attunement,
8. magiczne przedmioty składane z ogólnych efektów.

## Etap M7: Pełny Podsystem Magii

Kolejność:

1. stabilny schemat czaru i jego źródła,
2. cantripy, spell slots i cast at level,
3. przygotowane czary, znane czary i spellbook jako osobne profile,
4. components V/S/M, focus i kosztowne komponenty,
5. casting time: action, bonus action, reaction i dłuższe rzucanie,
6. range, target, area, linia efektu i legalność celów,
7. duration, concentration i repeated saves,
8. upcasting,
9. ritual casting,
10. attack spells, save spells, healing, buff, debuff, summon, movement i utility,
11. dispel/counter oraz interakcje magiczne dopiero po stabilizacji bazowego castingu.

Czary należy dodawać rodzinami mechanicznymi. Najpierw jeden reprezentant każdej
rodziny, potem katalog. Unikalny czar może dodać nowy generyczny prymityw, ale nie
powinien tworzyć jednorazowego przepływu w UI.

## Etap M8: Eksploracja, Sceny Społeczne I Cykl Przygody

Obecny challenge/freeform MVP pozostaje podstawą. Kolejność rozszerzeń:

1. czas scenariusza, odpoczynki i zużycie zasobów,
2. light, darkness, senses i stealth/perception,
3. ukrywanie, poszukiwanie, pułapki i hazards,
4. drzwi, zamki, pojemniki, cover i obiekty niszczalne,
5. podróż, tempo, nawigacja i exhaustion, jeśli należą do ustalonego zakresu,
6. conversation state, attitude i testy społeczne bez zastępowania decyzji graczy,
7. downtime oraz crafting tylko wtedy, gdy wymaga tego docelowy zakres,
8. wspólne efekty eksploracji, walki i scenariusza,
9. rozgałęzienia, cele, porażki fail-forward i konsekwencje między scenami.

LLM pozostaje klasyfikatorem deklaracji i pomocnikiem narracyjnym. Nie staje się
źródłem reguł ani bezpośrednim wykonawcą zmian stanu.

## Etap M9: Progresja, Kampania I Zapis

Kolejność:

1. rozszerzenie snapshotu scenariusza v1 o migracje i stan między scenariuszami,
2. stan drużyny między scenariuszami,
3. XP albo milestone jako wybrana strategia progresji,
4. level-up jako deterministyczna transformacja postaci,
5. stan kampanii, questów, NPC i trwałych konsekwencji,
6. migracje zapisów i contentu,
7. eksport diagnostyczny wraz z logiem sesji.

# Część II: Content

## Etap C1: Schematy, Walidacja I Pochodzenie Danych

Ten etap biegnie równolegle z mechanikami, ale nie oznacza masowego katalogu.

Zakres:

- wersjonowane schematy actor, monster, item, spell, feature i scenario,
- wspólne referencje oraz stabilne ID,
- walidacja referencji i zgodności z dostępnymi prymitywami,
- migracje schematów,
- attribution, source id i informacja o licencji,
- raport nieobsługiwanych mechanik podczas ładowania,
- narzędzie audytujące kompletność katalogu.

## Etap C2: Referencyjny Pakiet Testowy

Przez wszystkie etapy M1–M9 utrzymujemy mały pakiet przekrojowy:

- kilka broni, pancerzy, narzędzi i consumables,
- potwory melee, ranged, save-based i ze specjalnym traitem,
- czary reprezentujące każdą rodzinę mechaniczną,
- hazards, pułapki, NPC i obiekty interaktywne,
- scenariusz eksploracyjny, społeczny i encounter,
- bohaterowie testowi korzystający z różnych profili zasobów.

Ten pakiet jest testem architektury, nie docelowym katalogiem.

## Etap C3: Bazowy Katalog Gry

Po ustabilizowaniu odpowiednich mechanik katalog rozszerzamy w tej kolejności:

1. mundane weapons, armor, adventuring gear i tools,
2. podstawowe potwory o prostych statblockach,
3. oficjalne warunki, damage types i hazards,
4. czary rodzinami mechanicznymi i poziomami,
5. magiczne przedmioty według rodzin efektów,
6. bardziej złożone potwory, recharge, legendary i lair actions, jeśli są w zakresie,
7. gotowe NPC templates i encounter templates.

Każda partia danych musi przejść walidację całego katalogu i test kilku
reprezentatywnych obiektów w prawdziwym scenariuszu.

## Etap C4: Biblioteka Scenariuszy

Kolejność:

1. małe sceny testujące jedną rodzinę mechanik,
2. pełny jednostrzał: eksploracja, NPC, walka, odpoczynek i konsekwencje,
3. kilka scenariuszy o różnej strukturze,
4. krótka kampania testująca trwały stan,
5. biblioteka szablonów map, encounterów, challenge'y i NPC.

## Etap C5: Docelowy Katalog

Docelowy katalog powstaje dopiero po zamknięciu macierzy mechanik. Zakres zależy od
decyzji licencyjnej z Bramki 0. „Pełny content” oznacza kompletny, automatycznie
walidowany katalog w legalnie dozwolonym pakiecie danych, a nie kopiowanie wszystkich
tekstów podręcznikowych do repozytorium.

Kryterium wyjścia:

- brak zerwanych referencji i nieznanych prymitywów,
- raport kompletności wskazuje 100% ustalonego zakresu,
- każdy złożony typ obiektu ma scenariusz lub test integracyjny,
- aktualizacja contentu nie wymaga warunków specjalnych w UI/runtime.

# Część III: Rasy, Backgroundy I Klasy

## Warunek Startu

Nie zaczynamy masowego wdrażania ras i klas, dopóki nie są stabilne:

- feature/effect/trigger/resource framework,
- odpoczynki i odnowienie zasobów,
- warunki i modyfikatory,
- equipment i spellcasting,
- level-up oraz wersjonowany actor snapshot.

Wyjątkiem są anonimowi bohaterowie-fixture'y używani do testowania mechanik.

## Etap K1: Generyczna Kompozycja Postaci

Zakres:

- `FeatureDefinition` i `FeatureGrant`,
- źródło cechy: species/race, background, class, subclass, feat, item,
- wymagania poziomu i wybory gracza,
- zasoby, proficiency, akcje i efekty grantowane przez feature,
- walidacja konfliktów i duplikatów,
- deterministyczne złożenie końcowego aktora.

## Etap K2: Backgroundy I Rasy/Species

Kolejność:

1. backgroundy jako proficiency, języki, narzędzia, equipment i feature,
2. podstawowe rasy/species reprezentujące senses, speed, resistance i innate magic,
3. wybory wariantów i subrace/subspecies, jeśli należą do wybranej wersji zasad,
4. pełny legalnie dozwolony katalog.

## Etap K3: Cztery Klasy Referencyjne

Najpierw wdrażamy klasy reprezentujące odmienne rodziny mechanik:

1. Fighter — broń, pancerz, zasób odnawiany po odpoczynku i dodatkowe akcje,
2. Rogue — expertise, Sneak Attack, Cunning Action i reakcje sytuacyjne,
3. Cleric — przygotowywanie czarów, channel resource i divine features,
4. Wizard — spellbook, przygotowywanie, ritual casting i odzyskiwanie slotów.

To nie jest jeszcze moment na pełny katalog subclass. Celem jest udowodnienie, że
mechanizmy klasowe składają się z ogólnych prymitywów.

## Etap K4: Pozostałe Klasy I Subclassy

Klasy dodajemy rodzinami zależności:

1. Barbarian, Monk i Ranger po ustabilizowaniu ruchu, warunków i zasobów,
2. Bard, Druid, Paladin, Sorcerer i Warlock po pełnym spellcastingu,
3. pozostałe klasy należące do ustalonego zakresu,
4. po jednej referencyjnej subclassie na klasę,
5. pełny dozwolony katalog subclass,
6. multiclassing dopiero po stabilnym level-up każdej klasy osobno,
7. feats po stabilizacji prerequisite i feature composition.

Kryterium wyjścia:

- level 1–20 albo inny jawnie ustalony zakres jest pokryty automatycznym audytem,
- level-up nie wymaga ręcznego poprawiania JSON aktora,
- feature'y klas nie są interpretowane przez nazwę klasy w resolverach.

# Część IV: Moduły Autorskie

## Wspólny Fundament Authoringu

Walidatory, schematy, katalogi, migracje i preview payloads powstają wcześniej jako
narzędzia developerskie. Graficzne sub-aplikacje powstają dopiero po stabilizacji
modeli, ale korzystają z tego samego authoring API.

## Etap A1: Kreator Bohatera

Kolejność ekranów:

1. ruleset i dozwolone source packi,
2. metoda ability scores,
3. rasa/species i wybory cech,
4. background,
5. klasa, poziom i subclass,
6. proficiency, języki i narzędzia,
7. equipment,
8. spellcasting: known, spellbook i prepared profile,
9. podsumowanie statystyk wraz z wyjaśnieniem ich źródeł,
10. walidacja, zapis, eksport, import i level-up.

Kreator nie oblicza zasad samodzielnie. Wysyła wybory do domenowego buildera i
wyświetla jego wynik oraz błędy.

Kryterium wyjścia:

- można utworzyć każdą postać z ustalonego zakresu bez edycji pliku,
- każda wartość na karcie ma widoczne źródło,
- zapisana postać przechodzi ten sam loader co postacie scenariusza.

## Etap A2: Kreator Scenariusza

Kolejność modułów:

1. metadane i ruleset scenariusza,
2. mapa, teren, ściany, drzwi, strefy i punkty,
3. aktorzy, start positions i encounter groups,
4. obiekty, hazards i zasoby sceny,
5. NPC, wiedza, intencje i lokalne policy,
6. challenge'e, testy, DC policy i konsekwencje,
7. triggery, warunki, efekty i przejścia,
8. odpoczynki, cele i wyniki scenariusza,
9. walidacja referencji i raport nieobsługiwanych mechanik,
10. preview mapy/LED, dry run, playtest i publikacja paczki.

Edytor powinien mieć tryb formularza dla typowych przypadków oraz kontrolowany tryb
zaawansowany dla data-driven prymitywów. LLM może proponować tekst lub strukturę,
ale wynik musi przejść te same deterministyczne walidatory.

## Etap A3: Kreator Kampanii

Powstaje jako rozszerzenie kreatora scenariusza:

- graf scen,
- warunki przejść,
- persistent flags i NPC state,
- stan drużyny i odpoczynki między scenami,
- questy i zakończenia,
- migracje, wersjonowanie i publikacja pakietu kampanii.

# Część V: Wydania I Bramki Produktowe

## Release R1: Stabilny Rules Kernel

- M1–M2 ukończone,
- wersjonowane efekty, zasoby i snapshoty,
- aktualna macierz zasad,
- brak nowej logiki klasowej.

## Release R2: Pełna Walka Bazowa

- M3–M6 ukończone dla ustalonego zakresu,
- reprezentatywny encounter przechodzi automatycznie i manualnie,
- UI i LED wyjaśniają legalne akcje oraz modyfikatory.

## Release R3: Magia I Przygoda

- M7–M9 ukończone,
- pełny jednostrzał z odpoczynkiem i zapisem,
- brak osobnych przepływów dla pojedynczych czarów.

## Release R4: Content-Ready Engine

- schematy C1 stabilne,
- pakiet C2 pokrywa wszystkie rodziny mechanik,
- raport nieobsługiwanych mechanik jest pusty dla pakietu testowego.

## Release R5: Bazowy Katalog I Biblioteka Scenariuszy

- C3–C4 ukończone,
- kilka różnych scenariuszy przechodzi playtest,
- licencje i attribution są kompletne.

## Release R6: Postacie D&D

- K1–K4 ukończone dla jawnie ustalonego zakresu,
- klasy i rasy korzystają z ogólnych feature definitions,
- automatyczny audyt progresji nie wykazuje luk.

## Release R7: Authoring Suite

- kreator bohatera i scenariusza działają na wspólnym API,
- twórca nie musi edytować JSON,
- preview, walidacja i dry run są dostępne przed publikacją.

## Release R8: Docelowy Pakiet

- C5 osiąga 100% legalnie ustalonego zakresu,
- kampania demonstracyjna przechodzi od utworzenia bohatera do zakończenia,
- projekt posiada instrukcję uruchamiania, authoringu, migracji i playtestu,
- problemy rozgrywki można diagnozować z obserwacji sesji.

## Najbliższa Kolejność Prac

Po obecnym MVP przygotowywania czarów nie przechodzimy jeszcze do klas. Najbliższe
etapy to:

1. zatwierdzić bazową wersję zasad oraz strategię licencji,
2. zinwentaryzować mechaniki w macierzy i oznaczyć luki,
3. domknąć fundament aktora: proficiency, skills, 0 HP i death saves,
4. następnie realizować M3–M8 w zapisanej kolejności,
5. w M9 rozszerzyć snapshot v1 o stan kampanii i rzeczywiste migracje między wersjami.

# Game Design

Projekt jest aplikacją do wspomagania taktycznych starć w Dungeons & Dragons 5e z użyciem fizycznej planszy i systemu LED.

Docelowo aplikacja ma wspierać dużą część zasad walki i spotkań z D&D 5e.

Pierwsza wersja jest celowo ograniczona i skupia się na technicznie poprawnej pętli taktycznego starcia połączonej z fizyczną planszą, fizycznymi kośćmi oraz wizualizacją LED.

Aplikacja nie jest pełnym wirtualnym stołem RPG. W pierwszej wersji ma działać jako asystent walki taktycznej.

---

## Filozofia Projektu

Aplikacja powinna stosować zasady Dungeons & Dragons 5e wszędzie tam, gdzie jest to możliwe.

Zasad D&D 5e nie należy zastępować własnymi mechanikami bez wyraźnego powodu.

Jeżeli fizyczna plansza, LED-y albo ograniczenia pierwszej wersji wymagają uproszczenia, odstępstwo musi być opisane w tym pliku.

Jeżeli dana mechanika D&D 5e nie jest jeszcze zaimplementowana:

* należy dodać TODO,
* należy jasno oznaczyć ograniczenie,
* nie należy wymyślać własnego systemu zastępczego bez opisania powodu.

Lepsze jest niepełne, ale poprawne zachowanie zgodne z D&D 5e niż kompletna, ale własna mechanika niezgodna z systemem.

Każda implementacja reguły powinna dać się powiązać z konkretnym pojęciem z D&D 5e.

---

## Główna Pętla Gry

1. Wczytaj albo utwórz spotkanie.
2. Rozmieść aktorów na planszy.
3. Rzuć fizycznymi kośćmi albo przypisz inicjatywę.
4. Wpisz wyniki rzutów do aplikacji.
5. Rozgrywaj rundy walki.
6. Rozwiązuj ruch i akcje.
7. Aktualizuj stan planszy.
8. Generuj informacje zwrotne dla LED.
9. Zakończ spotkanie.
10. Zapisz podsumowanie spotkania.

---

## Pierwszy Techniczny Kamień Milowy

Pierwszy techniczny kamień milowy służy sprawdzeniu, czy podstawowe systemy działają poprawnie.

Ta wersja nie musi jeszcze być pełną sceną grywalną.

Pierwszy techniczny kamień milowy musi obsługiwać:

* jedną postać gracza,
* jednego potwora,
* inicjatywę,
* kolejność tur,
* ruch,
* ataki wręcz,
* rzuty ataku,
* rzuty obrażeń,
* punkty życia,
* stan śmierci albo pokonania,
* ręczne wpisywanie wyników rzutów kośćmi,
* wizualizację ruchu LED,
* wizualizację celów ataku LED.

Nie jest wymagane w pierwszym technicznym kamieniu milowym:

* czary,
* reakcje,
* ataki okazyjne,
* stany,
* koncentracja,
* cechy klasowe,
* sztuczna inteligencja potworów,
* ekwipunek,
* progresja kampanii,
* cyfrowy roller kości jako główny sposób wykonywania rzutów.

---

## Pierwsza Grywalna Scena

Po ukończeniu pierwszego technicznego kamienia milowego projekt powinien obsłużyć pierwszą prostą scenę grywalną.

Pierwsza grywalna scena powinna zawierać:

* dwóch bohaterów,
* trzy potwory,
* jednego NPC albo jeden obiekt interaktywny,
* prostą mapę z przeszkodami,
* podstawowy cel sceny,
* możliwość zakończenia starcia,
* podsumowanie wyniku.

Ta scena powinna nadal korzystać tylko z mechanik MVP.

Nie należy dodawać nowych dużych systemów tylko po to, aby scena była bardziej rozbudowana.

---

## Bazowe Mechaniki D&D 5e

Mechaniki początkowe:

* cechy postaci,
* modyfikatory cech,
* premia z biegłości,
* klasa pancerza,
* punkty życia,
* tymczasowe punkty życia,
* szybkość,
* inicjatywa,
* rzuty ataku,
* rzuty obrażeń,
* testy cech,
* rzuty obronne,
* przewaga,
* utrudnienie.

Silnik walki musi obsługiwać:

* ruch,
* akcję,
* placeholder na akcję dodatkową,
* placeholder na reakcję.

Mechaniki należy implementować tylko wtedy, gdy są potrzebne.

Nie należy implementować całego systemu D&D 5e naraz.

---

## Rzuty Kośćmi

Aplikacja nie zastępuje fizycznych kości.

Domyślny model gry zakłada, że gracze i Mistrz Gry wykonują rzuty fizycznymi kośćmi przy stole, a następnie wpisują wynik do aplikacji.

Aplikacja może obliczać modyfikatory, premie i końcowy rezultat, ale nie powinna wymuszać cyfrowego rzutu.

### Główna Zasada

Gracz rzuca fizyczną kością.

Aplikacja pyta o wynik rzutu.

Gracz wpisuje naturalny wynik z kości.

Aplikacja dolicza odpowiednie modyfikatory i rozstrzyga efekt.

Przykład:

* gracz wykonuje rzut ataku,
* fizycznie rzuca `d20`,
* wypada `14`,
* gracz wpisuje `14`,
* aplikacja dodaje premię do ataku, na przykład `+5`,
* aplikacja porównuje wynik `19` z klasą pancerza celu.

### Rodzaje Rzutów

Aplikacja musi obsługiwać następujące typy rzutów:

* rzut ataku,
* rzut obrażeń,
* test cechy,
* rzut obronny,
* rzut inicjatywy,
* rzut leczenia,
* rzut śmierci w późniejszej iteracji.

### Rzuty d20

Rzuty d20 obejmują:

* rzuty ataku,
* testy cech,
* rzuty obronne,
* inicjatywę.

Aplikacja powinna przechowywać:

* naturalny wynik na kości,
* użyty modyfikator,
* premię z biegłości, jeśli dotyczy,
* informację o przewadze albo utrudnieniu,
* wynik końcowy,
* rezultat rozstrzygnięcia.

### Przewaga I Utrudnienie

W przypadku przewagi albo utrudnienia gracz nadal rzuca fizycznymi kośćmi.

Aplikacja powinna pozwolić wpisać dwa wyniki `d20`.

Dla przewagi:

* aplikacja wybiera wyższy wynik.

Dla utrudnienia:

* aplikacja wybiera niższy wynik.

Aplikacja powinna przechowywać oba wyniki, wybrany wynik oraz końcowy rezultat.

### Naturalne 20 I Naturalne 1

Aplikacja musi przechowywać naturalny wynik rzutu, ponieważ naturalne `20` i naturalne `1` mogą mieć specjalne znaczenie.

W MVP specjalne rozstrzyganie naturalnego `20` i naturalnego `1` dotyczy tylko rzutów ataku.

Dla MVP:

* naturalne `20` przy rzucie ataku oznacza trafienie krytyczne,
* naturalne `1` przy rzucie ataku oznacza automatyczne pudło,
* naturalne `20` i naturalne `1` przy testach cech nie powinny automatycznie oznaczać sukcesu albo porażki, chyba że późniejsza reguła projektu zdecyduje inaczej.

### Rzuty Obrażeń

Rzuty obrażeń są wykonywane fizycznymi kośćmi.

Aplikacja powinna pozwolić wpisać:

* wynik z kości obrażeń,
* modyfikator obrażeń,
* typ obrażeń, jeśli jest znany.

Przykład:

* broń zadaje `1d8 + 3`,
* gracz rzuca fizycznie `d8`,
* wypada `6`,
* gracz wpisuje `6`,
* aplikacja dodaje `+3`,
* końcowe obrażenia wynoszą `9`.

### Trafienia Krytyczne

W przypadku trafienia krytycznego aplikacja powinna jasno wskazać, że wymagany jest rzut obrażeń dla trafienia krytycznego.

W MVP dopuszczalne są dwa warianty implementacji:

* gracz ręcznie wpisuje końcowy wynik obrażeń krytycznych,
* aplikacja prosi o wpisanie osobnych wyników z dodatkowych kości obrażeń.

Preferowany wariant MVP:

* gracz wpisuje końcowy wynik obrażeń po samodzielnym rzucie wszystkimi wymaganymi kośćmi.

Bardziej szczegółowe rozbijanie kości obrażeń można dodać później.

### Cyfrowe Rzuty Kośćmi

Cyfrowy roller kości nie jest wymagany w MVP.

Może zostać dodany później jako opcja pomocnicza.

Jeżeli cyfrowy roller zostanie dodany w przyszłości:

* nie może zastąpić domyślnego modelu fizycznych kości,
* powinien być opcjonalny,
* powinien dać się wyłączyć,
* nie powinien być wymagany do rozegrania spotkania.

### Wymagania Implementacyjne Dla Rzutów

System rzutów powinien rozdzielać:

* naturalny wynik kości,
* modyfikatory,
* wynik końcowy,
* rezultat mechaniczny.

Silnik zasad nie powinien losować wyników, jeżeli gracz podaje wynik fizycznego rzutu.

Funkcje rozstrzygające rzuty powinny być deterministyczne i testowalne.

Przykładowe dane wejściowe:

```text
roll_type: attack_roll
natural_roll: 14
modifier: 5
advantage_state: normal
target_ac: 16
```

Przykładowe dane wyjściowe:

```text
natural_roll: 14
total_result: 19
target_number: 16
success: true
critical_hit: false
critical_miss: false
```

---

## Model Aktora

Wszystkie istoty powinny używać wspólnego modelu `Actor`.

### Postacie Graczy

* id
* imię albo nazwa
* poziom
* placeholder klasy
* cechy
* premia z biegłości
* klasa pancerza
* punkty życia
* tymczasowe punkty życia
* szybkość
* modyfikator inicjatywy
* pozycja
* dostępne akcje

### Potwory

* id
* nazwa
* id bloku statystyk
* klasa pancerza
* punkty życia
* szybkość
* cechy
* akcje
* modyfikator inicjatywy
* pozycja

### NPC

* używają modelu `Actor`
* implementacja odłożona na później

---

## Model Planszy

### Fizyczna Plansza

* 20 kolumn
* 30 rzędów

### Koordynaty

```text
(col, row)
```

### Skala

* jedno pole odpowiada 5 feet

### Elementy Planszy

* aktorzy,
* teren,
* ściany,
* blokery,
* drzwi,
* obiekty interaktywne,
* efekty obszarowe.

Pathfinding musi być:

* deterministyczny,
* niezależny od sprzętu,
* w pełni testowalny.

---

## Eksploracja I Wyzwania

Tryb eksploracji nie powinien działać jak walka bez przeciwników.

W eksploracji drużyna porusza się wspólnie między strefami, a aplikacja prowadzi przez lokacje, punkty zainteresowania, decyzje i konsekwencje.

### Brak Twardych Blokad Rzutem

Domyślnie test eksploracyjny nie może być prostą blokadą typu:

* porażka oznacza brak przejścia,
* gracze powtarzają ten sam test aż do sukcesu,
* cała scena stoi, dopóki nie wypadnie odpowiedni wynik.

Takie zachowanie jest dopuszczalne tylko jako świadome odstępstwo opisane w contentcie albo w decyzjach reguł.

Domyślnym modelem jest `fail-forward`:

* rzut rozstrzyga jakość efektu,
* porażka może dać postęp z kosztem,
* sukces może dać postęp bez kosztu,
* wysoki sukces może dać dodatkową korzyść,
* poważna porażka może dodać komplikację.

### Wyzwanie Z Postępem

Eksploracyjne przeszkody powinny być modelowane jako wyzwania z postępem, a nie jako pojedyncze testy.

Przykład:

```text
Wyzwanie: Zamknięta brama
Cel: dostać się na dziedziniec
Postęp wymagany: 3
Postęp aktualny: 0
Ryzyka: hałas, strata czasu, uszkodzenie sprzętu
```

Każda dostępna opcja opisuje:

* wymagany test albo warunek,
* postęp na sukcesie,
* postęp na porażce,
* konsekwencję sukcesu,
* konsekwencję porażki,
* możliwe komplikacje,
* flagi sceny ustawiane po rozstrzygnięciu.

Przykładowe opcje dla zamkniętej bramy:

```text
Wyważ bramę:
- test: Siła / Atletyka
- sukces: +3 postępu, brama otwarta, hałas
- porażka: +1 postępu, hałas, zmęczenie albo uszkodzenie narzędzia
```

```text
Przejdź górą:
- test: Zręczność / Akrobatyka
- sukces: +2 postępu, ciche przejście części drużyny
- porażka: +1 postępu, ryzyko upadku albo utrata czasu
```

```text
Podważ mechanizm:
- test: Inteligencja / narzędzia albo rzemiosło
- sukces: +3 postępu, ciche otwarcie
- porażka: +1 postępu, narzędzie się zużywa albo mechanizm klinuje się częściowo
```

```text
Wyłam sztachetę:
- test: Siła albo Zręczność, zależnie od opisu
- sukces: +1 postępu, tworzy małe przejście albo nową opcję
- porażka: +1 postępu z komplikacją albo tylko informacja o stanie przeszkody
```

Opcje mogą mieć różne profile: szybkie, głośne, bezpieczne, ryzykowne, ciche, kosztowne albo wymagające zasobu.

### Przygotowanie Do Testu

Gracze powinni móc przygotować się do wyzwania przed głównym rozstrzygnięciem.

Przygotowanie może:

* dodać premię,
* dać przewagę,
* obniżyć ST,
* usunąć albo złagodzić komplikację,
* odblokować nową opcję,
* ujawnić informację o ryzyku.

Przykład:

```text
Zbadaj okolice bramy:
- sukces: odkrywa słaby zawias; następne "Podważ mechanizm" ma przewagę
- porażka: ujawnia tylko, że wyważenie będzie głośne
```

### Zasoby, Ekwipunek I Flagi

Opcje wyzwania mogą mieć tagi wymagań albo tagi bonusów, np.:

* `climbing`,
* `lockpicking`,
* `crowbar`,
* `rope`,
* `fire`,
* `quiet`,
* `heavy_force`.

Przed wykonaniem opcji aplikacja może pozwolić graczom otworzyć ekwipunek i wybrać zasób, narzędzie albo czar.

Jeżeli wybrany element ekwipunku ma pasującą flagę bonusu, może dodać efekt zdefiniowany po stronie itemu:

* premia liczbowa,
* przewaga,
* redukcja ST,
* dodatkowy postęp,
* anulowanie konkretnej komplikacji,
* zużycie zasobu.

Przykład:

```text
Opcja: Przejdź górą
Tag: climbing

Item: Lina z hakiem
Bonus tag: climbing
Efekt: advantage albo +2 do testu
```

### Rola LLM W Przyszłości

W pierwszej implementacji opcje eksploracyjne są predefiniowane w contentcie.

W przyszłości LLM może zostać dodany jako warstwa interpretacji kreatywnych deklaracji graczy.

LLM nie powinien być źródłem zasad ani samodzielnie zmieniać stanu gry.

Docelowa rola LLM:

* przetłumaczyć deklarację gracza na istniejące podejście,
* zaproponować pasującą cechę, skill, ryzyko i tagi,
* wskazać możliwy koszt albo komplikację,
* zwrócić ustrukturyzowaną propozycję do walidacji przez silnik gry albo MG.

Silnik gry nadal powinien walidować wynik i stosować tylko znane efekty.

---

## Ruch Po Planszy

Ruch po planszy powinien być zgodny z zasadami D&D 5e, ale jednocześnie prosty do wizualizacji na planszy LED.

### Podstawowe Założenia

* Jedno pole planszy odpowiada 5 feet.
* Aktor posiada wartość `Speed` wyrażoną w feet.
* Dostępny ruch w turze jest obliczany na podstawie wartości `Speed`.
* Przykład: aktor posiadający `Speed = 30 feet` może poruszyć się maksymalnie o 6 pól normalnego terenu.
* Ruch jest liczony w segmentach po 5 feet.

### Ruch Ortogonalny

Za ruch ortogonalny uznaje się przejście:

* góra,
* dół,
* lewo,
* prawo.

Koszt ruchu:

* 5 feet za wejście na sąsiednie pole.

### Ruch Diagonalny

Na potrzeby pierwszej wersji projektu:

* ruch diagonalny jest dozwolony,
* ruch diagonalny kosztuje 5 feet,
* diagonalne pole sąsiadujące traktowane jest jako oddalone o jedno pole ruchu.

Powód:

* prostsza implementacja,
* prostsza wizualizacja LED,
* płynniejsza rozgrywka na fizycznej planszy,
* zgodność z prostym wariantem gry na siatce w D&D 5e.

W przyszłości koszt ruchu diagonalnego może zostać rozszerzony do wariantu alternatywnego, na przykład:

* pierwsza diagonala kosztuje 5 feet,
* druga diagonala kosztuje 10 feet,
* wzór 5/10 powtarza się dalej.

Ten wariant nie jest częścią MVP.

### Zakaz Przechodzenia Przez Rogi

Aktor nie może wykonać ruchu diagonalnego przez róg, jeżeli róg jest zablokowany przez:

* ścianę,
* duży obiekt terenowy,
* blokującą przeszkodę,
* inne pole całkowicie blokujące przejście.

Przykład:

* jeżeli aktor chce przejść diagonalnie między dwoma polami, a oba przyległe ortogonalnie pola są zablokowane, ruch diagonalny jest niedozwolony.

Ta zasada zapobiega przenikaniu przez narożniki ścian i przeszkód.

### Trudny Teren

Trudny teren jest wspierany od pierwszej wersji.

Koszt wejścia na pole trudnego terenu:

* 10 feet.

Przykłady trudnego terenu:

* gruz,
* błoto,
* gęsta roślinność,
* śnieg,
* płytka woda,
* niskie meble,
* nierówne schody.

Jeżeli pole zawiera kilka źródeł trudnego terenu, koszt nie powinien być wielokrotnie zwiększany.

Na potrzeby MVP trudny teren po prostu podwaja koszt wejścia na pole.

### Przeszkody

Przeszkody mogą posiadać różne właściwości.

#### Ściany

Ściana blokuje przejście pomiędzy dwoma polami.

Aktor nie może:

* przejść przez ścianę,
* zakończyć ruchu za ścianą bez istniejącego przejścia,
* przejść diagonalnie przez róg ściany.

#### Drzwi

Drzwi mogą być:

* otwarte,
* zamknięte.

Otwarte drzwi nie blokują ruchu.

Zamknięte drzwi blokują ruch.

Interakcja z drzwiami powinna zostać zaimplementowana jako osobna mechanika akcji albo interakcji z obiektem.

#### Blokujące Przeszkody

Przykłady:

* głazy,
* kolumny,
* ciężkie meble,
* obiekty scenografii,
* barykady.

Blokują wejście na zajmowane pole.

### Inni Aktorzy

#### Sojusznicy

Aktor może przechodzić przez pole zajmowane przez sojusznika.

Pole zajmowane przez sojusznika traktowane jest jako trudny teren.

Aktor nie może zakończyć ruchu na polu zajmowanym przez sojusznika.

#### Przeciwnicy

Na potrzeby MVP:

* aktor nie może przechodzić przez pole zajmowane przez przeciwnika,
* aktor nie może zakończyć ruchu na polu zajmowanym przez przeciwnika.

Wyjątki wynikające z różnicy rozmiarów istot należy dodać w późniejszej iteracji.

#### Neutralni Aktorzy

Neutralni aktorzy powinni być traktowani jak sojusznicy, chyba że konkretna mechanika spotkania określi inaczej.

### Zakończenie Ruchu

Ruch może zostać zakończony wyłącznie na polu:

* znajdującym się w zasięgu ruchu,
* niezajętym przez innego aktora,
* niebędącym blokującą przeszkodą,
* dostępnym zgodnie z zasadami ruchu,
* znajdującym się w granicach planszy.

Aktor nigdy nie może dobrowolnie zakończyć ruchu na polu zajmowanym przez inną istotę.

### Obliczanie Zasięgu Ruchu

System powinien wyznaczać wszystkie osiągalne pola na podstawie:

* aktualnej pozycji,
* dostępnego ruchu,
* kosztów terenu,
* przeszkód,
* ścian,
* drzwi,
* obecności innych aktorów,
* zakazu przechodzenia przez zablokowane rogi,
* granic planszy.

Algorytm powinien być deterministyczny i niezależny od sprzętu.

Rekomendowany kierunek implementacji:

* użyć algorytmu podobnego do Dijkstra albo BFS z kosztami,
* traktować każde pole jako węzeł grafu,
* koszt wejścia na pole zależy od typu terenu i obecności aktora,
* wynik powinien zawierać zarówno osiągalne pola, jak i możliwe ścieżki.

### Wizualizacja LED Ruchu

Podczas tury aktywnego aktora plansza LED powinna wyświetlać:

* aktualną pozycję aktora,
* wszystkie osiągalne pola ruchu,
* aktualnie wybraną ścieżkę ruchu,
* pole docelowe.

System LED powinien obsługiwać jednocześnie:

* wizualizację pełnego zasięgu ruchu,
* wizualizację wybranej ścieżki.

Silnik zasad nie powinien generować kolorów ani animacji.

Silnik zasad powinien zwrócić dane logiczne, na przykład:

* `reachable_tiles`
* `selected_path`
* `origin`
* `destination`
* `movement_cost`

Warstwa LED odpowiada za zamianę tych danych na konkretne kolory, efekty i ramki animacji.

### Wymagania Implementacyjne Dla Ruchu

* Pathfinding musi być niezależny od sprzętu.
* Pathfinding musi być pokryty testami jednostkowymi.
* Silnik zasad nie może bezpośrednio sterować LED-ami.
* Silnik zasad zwraca dane opisujące możliwe pola ruchu oraz ścieżkę.
* Warstwa LED odpowiada wyłącznie za wizualizację otrzymanych danych.
* Ruch musi być możliwy do przetestowania bez Arduino, Raspberry Pi i fizycznych LED-ów.

---

## Struktura Tury

Walka używa kolejności inicjatywy.

Każda tura aktora zawiera:

* ruch,
* akcję,
* opcjonalną akcję dodatkową,
* opcjonalne śledzenie reakcji.

Silnik musi wspierać przyszłe rozszerzenia dla:

* ataków okazyjnych,
* przygotowanych akcji,
* reakcji,
* koncentracji.

---

## Projekt LED

LED-y zapewniają szybką informację taktyczną na stole.

Obsługiwane wizualizacje:

* aktywny aktor,
* zasięg ruchu,
* wybrana ścieżka,
* cele ataku,
* efekty obszarowe,
* informacja o trafieniu,
* informacja o obrażeniach,
* informacja o leczeniu,
* znaczniki przygotowania spotkania.

Efekty LED muszą być generowane jako niemutowalne dane ramek.

Adaptery sprzętowe odpowiadają za odtwarzanie tych ramek.

Silnik zasad nie może wiedzieć:

* jaki typ taśmy LED jest używany,
* ile LED-ów znajduje się na planszy,
* jaki protokół komunikacyjny jest używany,
* jaka jest częstotliwość odświeżania.

---

## Zapis Danych

Dane spotkania powinny być serializowalne.

Preferowany format:

* JSON

Przyszły zapis powinien obejmować:

* spotkania,
* stan walki,
* aktorów,
* stan planszy,
* historię rzutów,
* podsumowanie starcia.

---

## Wymagania Testowe

Każda mechanika rozgrywki wymaga testów jednostkowych.

Wymagane pokrycie testami:

* kolejność inicjatywy,
* zasięg ruchu,
* pathfinding,
* rozstrzyganie ataku,
* obliczanie obrażeń,
* rzuty obronne,
* przewaga i utrudnienie,
* ręczne wpisywanie wyników rzutów,
* rozróżnianie naturalnego wyniku i wyniku końcowego.

Adaptery sprzętowe nie wymagają testów jednostkowych w MVP.

---

## Poza Zakresem Pierwszej Wersji

Pierwsza wersja nie obejmuje:

* pełnego kreatora postaci,
* pełnego katalogu czarów,
* pełnego katalogu potworów,
* gry sieciowej,
* zarządzania kampanią,
* symulacji świata,
* własnych zasad homebrew,
* odtwarzania starego interfejsu Pathfinder bez zmian,
* obowiązkowego cyfrowego rollera kości,
* automatycznego rozpoznawania wyników fizycznych kości kamerą.

---

## Przyszłe Rozszerzenia

Szczegółową listę przyszłych funkcji należy prowadzić w osobnym pliku `ROADMAP.md`.

Najważniejsze przyszłe obszary rozwoju:

* reakcje i ataki okazyjne,
* stany,
* czary,
* koncentracja,
* ekwipunek,
* pełniejsze bloki statystyk potworów,
* rozmiary istot,
* zaawansowany ruch,
* kampanie,
* opcjonalny cyfrowy roller kości,
* opcjonalne automatyczne rozpoznawanie rzutów fizycznych kości.

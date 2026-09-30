# System run v0.2 — ładunki i przekazywany rezonans

> **Aktualizacja 25.09.2026:** poniższy tekst jest wcześniejszym projektem.
> Bieżące ustalenia użytkownika zapisano w [specyfikacji ciągłego Rezonansu](docs/RESONANCE_RUNTIME_SPEC.md).
> Premie zaczynają się przed mocą, obejmują uczestników od ich tur i wygasają wspólnie.
> Grot działa na wszystkie obrażenia źródłowego bohatera; Kielich i Klepsydra są osobnymi licznikami.
> Fala powiela poprzednią runę. Skupienie: 1k20, odzysk klasowy: 1k4.
> W razie rozbieżności obowiązuje nowa specyfikacja i katalog kart, nie poniższe przykłady.

**Status:** opis nowego podejścia do prototypu i testów przy stole.  
**Zakres:** osobiste ładunki, dwa tryby mocy specjalnych oraz wspólnie budowana paczka bonusów runicznych.  
**Zastępuje:** wcześniejszy wariant koszyków run, losowania konkretnych symboli i opłacania wzmocnień runami sojuszników.

> **Moc wzmocniona:** korzystasz z rezonansu, dokładasz bonus własnej runy i przekazujesz powiększoną paczkę dalej.  
> **Moc podstawowa:** korzystasz z otrzymanej paczki, a po rozpatrzeniu mocy zamykasz rezonans.

Dokument oddziela ustalony rdzeń od roboczych wartości. Liczby takie jak 20 ładunków, koszty 4/8, Skupienie +6 i regeneracja klasowa +2 są parametrami startowymi do sprawdzenia, a nie zakończonym balansem. Efekty run innych niż Grot oraz przykłady kart są robocze.

---

## 1. Główna idea

Każdy bohater ma niewielki zestaw mocy specjalnych — roboczo cztery. Każda moc jest przypisana do konkretnej runy na planszy. Runa identyfikuje moc i określa jej stały bonus runiczny, ale nie jest osobną walutą.

Wszystkie moce bohatera korzystają z jednego osobistego licznika **ładunków runicznych**. Nie ma osobnych pul Ofensywy, Obrony, Mobilności i Aury. Nie trzeba zbierać ani dopasowywać symboli do kosztów.

Drużyna ma natomiast jedną wspólną **paczkę Rezonansu**. Paczka zawiera bonusy run dodane przez kolejne wzmocnione moce. Następny bohater może ją powiększyć i przekazać dalej albo wykorzystać tańszą mocą i domknąć łańcuch.

Docelowa pętla:

**Przygotowane ładunki → wzmocnione moce → rosnąca paczka bonusów → wykorzystanie jej odpowiednią mocą → domknięcie → odzyskiwanie energii i następny łańcuch.**

---

## 2. Co zachowujemy, a z czego rezygnujemy

### Zachowujemy

- Klimat run i powiązanie symbolu na planszy z konkretną mocą.
- Indywidualne zestawy zdolności bohaterów.
- Osobiste zasoby, które można zużywać i odnawiać podczas walki.
- Regenerację przez Skupienie oraz zachowania charakterystyczne dla postaci.
- Współpracę opartą na świadomym przygotowywaniu kolejnych akcji drużyny.

### Rezygnujemy w tym prototypie

- Z czterech kategorii waluty i osobnych koszyków run.
- Z losowania symboli podczas ładowania.
- Z wymagania konkretnych run jako kosztu podstawowej mocy lub jej wzmocnienia.
- Z losowej talii efektów rezonansu.
- Z opłacania budowania rezonansu Reakcją pomocnika i przekazywania mu zadania zapłaty.
- Z wymogu odległości między bohaterami przekazującymi rezonans.
- Ze sztywnego limitu liczby bonusów w paczce i automatycznego wyładowania po określonej liczbie ogniw.

---

## 3. Osobiste ładunki

### 3.1. Jedna pula na bohatera

Każdy bohater ma własny licznik:

`aktualne ładunki / maksymalne ładunki`

Roboczy punkt wyjścia to **20/20 na początku każdej walki**. Maksimum, liczba początkowych ładunków i ewentualne różnice między postaciami pozostają parametrami balansu.

Ładunki są jednorodne. Dowolną moc opłaca się z tej samej puli, niezależnie od jej runy.

### 3.2. Płatność

Koszt mocy opłaca bohater, który ją wykonuje. Przekazanie rezonansu nie przekazuje ładunków i nie przenosi kosztu mocy na poprzedniego gracza.

Tryb mocy i wydatek wybiera się przed rozpatrzeniem jej efektu. Nie można zapłacić energią, którą dopiero planuje się odzyskać w wyniku tej samej akcji.

Ładowanie zwiększa licznik, ale nie przekracza jego maksimum. Nie losuje się przy nim żadnego symbolu.

---

## 4. Moce specjalne i ich dwa tryby

### 4.1. Wspólna konstrukcja

Każda moc ma:

- nazwę i przypisaną runę;
- wymagania, zasięg i koszt w ekonomii akcji;
- podstawowy efekt;
- koszt trybu podstawowego;
- koszt lub jednoznaczny próg trybu wzmocnionego.

**Tryb podstawowy** wykonuje normalny efekt zdolności. Jeżeli istnieje rezonans, moc korzysta z otrzymanych bonusów i następnie zamyka łańcuch.

**Tryb wzmocniony** wykonuje normalny efekt zdolności i dodaje do paczki bonus runy przypisanej do tej mocy. Moc korzysta już z powiększonej paczki, po czym przekazuje ją dalej.

W tym podejściu nie trzeba tworzyć osobnego, rozbudowanego zestawu ulepszeń każdej karty. Stałe wzmocnienie wynika z runy.

### 4.2. Runa ma ten sam bonus niezależnie od postaci

Przykład ustalonego kierunku:

> **Grot: +1k4 do obrażeń mocy.**

Jeżeli różne moce są przypisane do Grota, każda dodaje ten sam bonus przy użyciu wzmocnionym. Ich podstawowe efekty nadal mogą być zupełnie inne.

Przekazywany jest **bonus Grota**, a nie atak, zasięg, podstawowe obrażenia, odepchnięcie czy inne elementy mocy poprzedniego bohatera.

### 4.3. Koszty stałe i koszt X

Roboczy przykład kosztów:

| Tryb | Koszt |
|---|---:|
| Podstawowy | 4 ładunki |
| Wzmocniony | 8 ładunków łącznie |

Koszt 8 oznacza całkowity wydatek, nie dopłatę 8 do wcześniej zapłaconych 4.

Moce mogą mieć różne ceny. Możliwy jest także koszt **X**, jeżeli skala efektu zależy od wydatku. W takim przypadku karta musi jawnie określać, kiedy użycie liczy się jako wzmocnione i dokłada bonus runy.

Przykładowy zapis konstrukcyjny, nie gotowa zdolność:

> Koszt X w zakresie 3–8. Efekt podstawowy skaluje się zgodnie z kartą. Wydatek 8 uruchamia tryb wzmocniony.

„Wzmocniona” nie znaczy „wydałem wszystkie ładunki, które akurat miałem”. Próg wynika z karty.

---

## 5. Paczka Rezonansu

### 5.1. Zawartość

Paczka przechowuje liczbę bonusów poszczególnych run, na przykład:

`Grot ×3 | Wieża ×1 | Schody ×1`

Nie trzeba przechowywać pełnej kolejności wcześniejszych mocy ani rozpatrywać ponownie ich podstawowych efektów.

Jeżeli potrzebny jest podgląd poziomu rezonansu, można pokazywać sumę dołożonych bonusów. Sam poziom nie mnoży dodatkowo ich siły: paczka rośnie przez dokładanie kolejnych bonusów.

### 5.2. Wzmocniona moc

1. Bohater deklaruje legalną moc i opłaca jej wzmocniony tryb.
2. Do aktywnej paczki dodaje się jeden bonus runy tej mocy. Gdy paczka była pusta, rozpoczyna to rezonans.
3. Moc jest rozpatrywana z całą powiększoną paczką.
4. Paczka pozostaje aktywna dla następnego bohatera.

**Nowy bonus działa już na moc, która go dodała.**

### 5.3. Podstawowa moc

1. Bohater deklaruje legalną moc i opłaca jej podstawowy tryb.
2. Moc jest rozpatrywana z całą dotychczasową paczką.
3. Po rozpatrzeniu mocy paczka zostaje wyzerowana.

Podstawowa moc nie dodaje bonusu własnej runy. Jeżeli taki bonus jest już w otrzymanej paczce, korzysta z niego normalnie.

### 5.4. Zestawienie

| Stan przed mocą | Wybrany tryb | Bonusy dla tej mocy | Stan po mocy |
|---|---|---|---|
| Pusta paczka | Podstawowy | Brak rezonansu. | Pusta paczka. |
| Pusta paczka | Wzmocniony | Bonus runy wykonywanej mocy. | Pierwszy bonus pozostaje. |
| Aktywna paczka | Podstawowy | Wszystkie pasujące bonusy otrzymanej paczki. | Paczka wyzerowana. |
| Aktywna paczka | Wzmocniony | Otrzymana paczka plus nowy bonus własnej runy. | Powiększona paczka pozostaje. |

Domknięcie nie jest karą ani „zepsuciem” gry drużynie. Tańsza moc korzystająca z dużej paczki może być celowym i bardzo wydajnym zakończeniem sekwencji.

---

## 6. Grot: wszystkie trafienia i wszystkie cele

### 6.1. Reguła

> **Grot dodaje 1k4 do obrażeń zadawanych przez rozpatrywaną moc każdemu celowi. Jeżeli moc zadaje obrażenia kilkoma osobnymi trafieniami, premia działa przy każdym z nich. Kolejne Groty sumują się.**

Nie stosujemy ograniczenia „jeden bonus obrażeń na całą moc” ani „tylko jeden wybrany cel”.

Przy paczce `Grot ×2`:

| Rodzaj mocy | Zastosowanie bonusu |
|---|---|
| Jeden atak | +2k4 do obrażeń trafienia. |
| Trzy osobne trafienia | +2k4 do każdego z trzech trafień. |
| Atak obszarowy | +2k4 do obrażeń przeciw każdemu trafionemu lub objętemu obrażeniami celowi. |
| Moc zwiększająca KP sojuszników | Nie otrzymuje obrażeń; Groty pozostają jednak w przekazywanej paczce przy kontynuacji. |

Obrażenia nadal podlegają zwykłym zasadom danej mocy, na przykład chybieniu, rzutowi obronnemu lub redukcji obrażeń.

### 6.2. Bez samopowielania premii

Grot powiększa obrażenia, ale nie tworzy nowego trafienia, które uruchamia kolejnego Grota.

Jeżeli jedno trafienie zadaje bazowo:

`1k8 + 1k6`

to przy dwóch Grotach zadaje:

`1k8 + 1k6 + 2k4`

Premii nie dodaje się osobno do każdej kości składowej tego samego trafienia.

### 6.3. Cel projektowy

Kumulowanie Grotów pod wielokrotne trafienia lub moc obszarową jest **zamierzoną synergią**. Drużyna powinna móc przygotować potężne uderzenie przez wcześniejsze działania kilku bohaterów.

Nie istnieje osobny obowiązkowy „finisher”. Rolę zakończenia pełni moc, która szczególnie dobrze wykorzystuje zgromadzone bonusy.

Wpływ Grotów na obrażenia zadawane później przez podpalenie, truciznę i podobne stany nie został jeszcze rozstrzygnięty; nie należy go domyślnie dopisywać do powyższej reguły.

---

## 7. Dopasowanie bonusów i czas ich działania

### 7.1. Bonus musi pasować do efektu

Bonus obrażeń wzmacnia obrażenia. Nie powoduje, że leczenie albo zwiększenie KP zaczyna zadawać obrażenia.

Niepasujący bonus nie jest usuwany z paczki. Bohater może nie skorzystać z Grota przy swojej mocy wspierającej, a mimo to przekazać go następnej osobie, jeżeli użyje trybu wzmocnionego.

Sposób zastosowania wynika z opisu konkretnej runy. Nie ma uniwersalnego ograniczenia „każdy bonus najwyżej raz na moc”, które blokowałoby wielokrotne zastosowanie Grota.

### 7.2. Domknięcie nie cofa efektów

Wyzerowanie paczki usuwa możliwość korzystania z niej przez kolejne moce. Nie cofa tego, co już nastąpiło:

- zadane obrażenia pozostają zadane;
- odzyskane PW pozostają odzyskane;
- wykonany ruch nie jest cofany;
- przyznana ochrona trwa do terminu określonego w jej opisie.

Czas działania osłon i innych efektów czasowych musi być zapisany w definicji runy.

### 7.3. Robocze przykłady innych run

| Runa | Przykładowy bonus | Status |
|---|---|---|
| Grot | +1k4 obrażeń przy każdym trafieniu i przeciw każdemu celowi mocy. | Ustalony kierunek działania. |
| Wieża | Po mocy +1 KP do początku następnej tury korzystającego bohatera. | Efekt i liczby robocze. |
| Schody | Po mocy ruch do 2 pól bez ataków okazyjnych. | Efekt i liczby robocze. |

Wielokrotne Groty na pewno się sumują. Zasady kumulowania pozostałych bonusów, w tym kilku Wież lub Schodów oraz nakładających się czasów ochrony, wymagają osobnego doprecyzowania przy projektowaniu run.

---

## 8. Ciągłość i zakończenie łańcucha

### 8.1. Bez ograniczenia odległości

W tym prototypie przekazywanie rezonansu działa drużynowo, niezależnie od odległości między bohaterami. Nie kosztuje Reakcji, nie wymaga wskazywania pomocnika ani przekazywania zasobów.

Zasięg, widoczność i legalność celów samych mocy nadal wynikają z normalnych zasad. Brak zasięgu rezonansu nie pozwala atakować ani leczyć poza zasięgiem zdolności.

### 8.2. Zwykłe działania

Zwykły ruch, atak bronią lub użycie przedmiotu przed mocą specjalną nie przerywają rezonansu. Same nie otrzymują jednak bonusów paczki.

Paczka wzmacnia rozpatrywaną moc specjalną. Jeżeli jej efektem jest atak bronią, ten atak korzysta z bonusów jako część mocy.

### 8.3. Tura bez kontynuacji

Podstawowa moc domyka rezonans po skorzystaniu z paczki.

Jeżeli bohater przeznacza swoją specjalną akcję na Skupienie albo kończy turę bez użycia mocy specjalnej, rezonans wygasa. Skupienie nie korzysta z paczki i nie przechowuje jej na później.

### 8.4. Pudła, dodatkowe trafienia i reakcje

Legalnie użyta i opłacona moc wzmocniona kontynuuje rezonans nawet wtedy, gdy jej atak chybi. Efekty wymagające trafienia po prostu nie występują.

Dodatkowe trafienia, ruchy i efekty wynikające z jednej mocy nie tworzą kolejnych ogniw. Moce reakcyjne i działania przeciwników nie powiększają paczki w tym prototypie.

Sam koniec rundy lub tura przeciwnika nie zerują rezonansu. Paczka oczekuje na rozstrzygnięcie w kolejnej turze bohatera.

### 8.5. Brak sztywnego limitu

Nie ma obowiązkowego wyładowania po czterech, sześciu ani innej ustalonej liczbie bonusów.

Ograniczeniem są osobiste ładunki i konieczność korzystania z droższego trybu przez kolejnych bohaterów. Koszt nie rośnie automatycznie wraz z poziomem paczki — przy tej samej mocy pozostaje taki sam, ale energii stopniowo ubywa.

---

## 9. Odzyskiwanie ładunków

Mechanizm regeneracji zachowuje dwa wcześniejsze kierunki. Konkretne wartości i warunki klasowe są robocze.

### 9.1. Skupienie

Propozycja do testu:

> **Skupienie:** zużyj swoją akcję specjalną i odzyskaj 6 własnych ładunków, nie przekraczając maksimum.

Przy roboczej ekonomii akcji bohater nadal może wykonać dostępny ruch i zwykły atak albo użyć przedmiotu. Rezygnuje jednak z mocy specjalnej, więc nie kontynuuje rezonansu.

### 9.2. Regeneracja klasowa

Propozycja do testu:

> **Odzyskaj 2 ładunki po spełnieniu własnego warunku klasowego, najwyżej raz na rundę.**

Każda postać powinna mieć krótki, jednoznaczny warunek. Przykładowe kierunki, nie ostateczne zdolności:

- Mira: wejście ruchem na flankę.
- Garran: skuteczne osłonięcie sojusznika.
- Pozostałe postacie: warunki dopasowane do ich roli i faktycznie dostępnych działań.

Zwrot następuje po rozpatrzeniu działania wywołującego regenerację. Nie ma już odnawiania określonej kategorii ani symbolu — odzyskuje się po prostu ładunki.

### 9.3. Warunek bilansu

Przy regularnym kontynuowaniu rezonansu zużycie energii powinno być większe od regeneracji dostępnej w tym samym cyklu działań.

Przykład bez regeneracji, dla pojemności 20 i kosztu wzmocnienia 8:

`20 → 12 → 4`

Po dwóch własnych wzmocnieniach bohater nie ma środków na trzecie. Może jednak użyć podstawowej mocy za 4, skorzystać z otrzymanej paczki i domknąć łańcuch.

Jeżeli zestaw efektów pozwala stale odzyskiwać cały koszt wzmocnionych mocy bez przerwy na Skupienie, ograniczenie przez ładunki przestaje działać. To istotny punkt testów, nie powód do automatycznego dodawania limitu długości.

---

## 10. Robocza ekonomia tury

Na pierwszy test pozostaje prosty punkt wyjścia:

- ruch;
- zwykły atak albo użycie przedmiotu;
- jedna akcja specjalna.

Podstawowe działania nie kosztują ładunków. Konkretna moc może jednocześnie zajmować zwykły atak i akcję specjalną — powinno to wynikać z jej karty, zwłaszcza przy mocniejszych atakach bronią.

Jeden bohater dokłada najwyżej jeden bonus runiczny w swojej turze. Dodatkowy atak w obrębie mocy nadal jest częścią tej samej mocy, a nie następną aktywacją rezonansu.

Liczba mocy i szczegółowa ekonomia akcji mogą ulec zmianie po teście. Nie należy zwiększać ich tylko po to, by równocześnie testować więcej zmiennych.

---

## 11. Przykład pełnej sekwencji

Przykład ilustruje mechanikę; nie jest gotowym zestawem kart postaci. Przyjmujemy 20 ładunków na bohatera, koszt podstawowy 4 i wzmocniony 8. Dla czytelności pomijamy regenerację.

| Bohater | Wykonana moc | Wydatek | Paczka użyta przez moc | Co dzieje się dalej? |
|---|---|---:|---|---|
| Brakka | Atak pod Grotem, wzmocniony | 8 | Grot ×1 | Przekazuje Grot ×1. |
| Garran | Uderzenie pod Wieżą, wzmocnione | 8 | Grot ×1, Wieża ×1 | Przekazuje oba bonusy. |
| Mira | Atak pod Grotem, wzmocniony | 8 | Grot ×2, Wieża ×1 | Przekazuje powiększoną paczkę. |
| Nimra | Czar obszarowy, podstawowy | 4 | Grot ×2, Wieża ×1 | Korzysta z paczki, następnie ją zeruje. |

### Rozpatrzenie czaru Nimry

Jeżeli czar zadaje bazowo `2k6` obrażeń obszarowych, otrzymuje `+2k4` przeciw każdemu celowi, któremu zadaje obrażenia. Ostatecznie jest to `2k6 + 2k4`, z zastosowaniem normalnych zasad czaru dotyczących rzutów obronnych, redukcji i doboru celów.

Nimra otrzymuje również przykładową ochronę z Wieży. Wyzerowanie rezonansu nie usuwa tej ochrony przed jej określonym terminem.

Po sekwencji Brakka, Garran i Mira mają po 12 ładunków, a Nimra 16. Drużyna świadomie zainwestowała w trzy wzmocnienia, żeby czwarty bohater wykorzystał zgromadzone efekty tańszą mocą obszarową.

Nimra mogłaby zamiast tego użyć wersji wzmocnionej, dopisać bonus runy własnego czaru i przekazać jeszcze większą paczkę dalej.

---

## 12. Szablon karty mocy

```text
NAZWA MOCY
Runa: [symbol / nazwa]

Wymagania: [jeśli występują]
Zasięg i cele: [...]
Akcje: [specjalna / atak + specjalna / inny jawny zapis]

EFEKT PODSTAWOWY
[Opis działania.]

TRYB PODSTAWOWY — [koszt] ładunków
Wykonaj efekt z otrzymaną paczką Rezonansu.
Po rozpatrzeniu mocy zamknij rezonans.

TRYB WZMOCNIONY — [koszt całkowity] ładunków
Dodaj bonus swojej runy do paczki.
Wykonaj efekt z powiększoną paczką i przekaż ją dalej.

BONUS RUNY
[Ten sam opis dla każdej mocy przypisanej do tej runy.]
```

W aplikacji i na wydrukach warto używać jednej wspólnej definicji bonusu każdej runy, żeby Grot nie miał różnych znaczeń na różnych kartach.

Do podglądu wystarczą osobisty licznik ładunków oraz wspólne liczniki bonusów, np. `Grot ×3 / Wieża ×1 / Schody ×1`. Historia kolejnych właścicieli paczki nie jest potrzebna do rozpatrywania efektów.

---

## 13. Parametry pierwszego testu

| Element | Punkt wyjścia | Status |
|---|---|---|
| Liczba mocy bohatera | Około 4 | Propozycja; można zmienić. |
| Ładunki na początku walki | Około 20 | Wartość robocza. |
| Koszt podstawowy / wzmocniony | Np. 4 / 8 | Przykład; ceny mogą zależeć od mocy. |
| Regeneracja klasowa | +2, najwyżej raz na rundę | Wartość i warunki robocze. |
| Skupienie | Akcja specjalna, +6 ładunków | Wartość robocza. |
| Bonus Grota | +1k4 do wszystkich trafień i celów rozpatrywanej mocy | Ustalony sposób działania. |
| Powtórzenia Grota | Sumują się | Ustalone. |
| Zasięg przekazywania rezonansu | Bez ograniczenia w pierwszym prototypie | Przyjęte uproszczenie. |
| Koszt Reakcji za rezonans | Brak | Przyjęte uproszczenie. |
| Sztywny limit długości | Brak | Ustalone; ogranicza ekonomia ładunków. |
| Losowanie bonusów | Brak | Bonus wynika z wybranej runy mocy. |

---

## 14. Co pozostaje do ustalenia i sprawdzenia

### 14.1. Definicje run

Potrzebna jest finalna lista używanych run oraz ich bonusów. Szczególnie należy doprecyzować kumulowanie premii obronnych, dodatkowego ruchu i ponownych zastosowań efektów czasowych.

### 14.2. Szczegóły obrażeń

Należy ustalić, jak Grot współpracuje z trafieniami krytycznymi, obrażeniami okresowymi oraz mocami korzystającymi ze wspólnego lub osobnych rzutów obrażeń. Nie zmienia to ustalonej zasady, że premia obejmuje wszystkie bezpośrednie trafienia i cele rozpatrywanej mocy.

### 14.3. Koszty i regeneracja

Należy sprawdzić, ile wzmocnień można wykonać przed wyczerpaniem energii, czy Skupienie jest użyteczne i czy któryś zestaw zdolności nie podtrzymuje rezonansu bez końca. Bardzo tanie wzmocnienie może stać się dominującym sposobem dokładania bonusów.

### 14.4. Liczba bohaterów i kolejność tur

Większa drużyna może dołożyć więcej bonusów, zanim ten sam bohater ponownie zapłaci za kontynuację. Test powinien obejmować docelową liczbę graczy i rzeczywisty porządek aktywacji z gry.

Ten dokument nie dodaje nowego systemu inicjatywy ani dowolnego przestawiania kolejności bohaterów. Nietypowe przypadki, takie jak pominięcie tury nieprzytomnej postaci, wymagają późniejszego doprecyzowania.

### 14.5. Różnorodność decyzji

Kumulowanie Grotów pod obszarówkę ma być dostępne i opłacalne. Trzeba jednak sprawdzić, czy jest jedną z kilku sensownych sekwencji, czy wypiera wszystkie pozostałe runy i sposoby gry.

Warto obserwować, czy gracze zmieniają plan w reakcji na sytuację, czy każda walka sprowadza się do identycznego przygotowanego łańcucha.

### 14.6. Obsługa paczki

Nie ma limitu długości, więc istotna jest czytelność podglądu i liczba różnych efektów. Liczniki powtórzeń ograniczają księgowość, ale nie zastąpią testu długiej paczki przy stole.

---

## 15. Wyjaśnienie dla gracza

> Masz własne ładunki i kilka mocy oznaczonych runami. Każdą moc możesz wykonać taniej albo wzmocnić większym wydatkiem. Wzmocnienie dodaje do wspólnego Rezonansu stały bonus runy tej mocy. Korzystasz z całej paczki i przekazujesz ją następnemu bohaterowi. On może dołożyć kolejny bonus swoim wzmocnieniem albo użyć tańszej mocy, wykorzystać całą paczkę i zakończyć łańcuch. Groty sumują się i wzmacniają wszystkie trafienia oraz cele mocy, więc warto wspólnie przygotowywać mocne kombinacje. Ładunki odzyskujesz przez działania swojej postaci albo Skupienie. Rezonans nie ma sztywnego limitu długości — trwa, dopóki drużyna potrafi i chce płacić za kolejne wzmocnienia.

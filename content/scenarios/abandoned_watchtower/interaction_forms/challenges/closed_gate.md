# Formularz Interakcji

## 1. Typ Interakcji
przeszkoda / wyzwanie eksploracyjne

## 2. Nazwa
Zamknięta brama

Id robocze / obecne id: `closed_gate`

## 3. Gdzie Na Mapie
Strefa/lokacja: `gate` / Brama strażnicy
Pole albo obszar na planszy: okolice głównego punktu strefy `gate`
Czy jest jawna od początku? tak

## 4. Opis Dla Graczy
Stary trakt urywa się przed zamkniętą bramą opuszczonej strażnicy, której dwa niskie, omszałe filary podtrzymują ciężkie skrzydła zbite z grubych, napuchniętych od wilgoci desek. Zardzewiałe okucia trzymają się ledwie na słowo honoru, stare gwoździe wystają pod dziwnymi kątami, a dolną część bramy oplatają ciernie, mokre pnącza i gęste zarośla, jakby natura przez lata próbowała wciągnąć całe przejście z powrotem w ziemię. Przez wąskie szczeliny między deskami widać tylko ciemność, omszałe kamienie i fragment zawalonej konstrukcji po drugiej stronie. W powietrzu czuć pleśń, rdzę i starą wilgoć, a każde mocniejsze dotknięcie bramy wywołuje skrzypienie, które w martwej ciszy brzmi niepokojąco głośno.

## 5. Informacje Dla MG / LLM
Krótki opis kontekstu dla MG/LLM:
Brama jest pierwszą realną przeszkodą eksploracyjną sceny. Ma sprawdzić, czy drużyna próbuje siły, sprytu, ostrożnego badania, narzędzi albo obejścia. Nie jest zagadką z jednym poprawnym rozwiązaniem.

### Prawda Scenariusza
- Brama jest drewniana, stara i napuchnięta od wilgoci, ale nadal trzyma się solidnie dzięki metalowym okuciom, zardzewiałym zawiasom i drewnianemu ryglowi po wewnętrznej stronie.
- Najsłabszym punktem bramy są zawiasy. Nie jest to od razu oczywiste dla graczy.
- Z tyłu, po stronie dziedzińca, znajduje się drewniany rygiel, który utrudnia siłowe wyważenie bramy. Jeśli ktoś przedostanie się na drugą stronę, może zdjąć rygiel i wtedy dalsze otwarcie bramy będzie dużo łatwiejsze.
- Zamek jest zatarty, więc da się próbować narzędzi złodziejskich, ale jest to trudniejsze niż przy sprawnym mechanizmie.
- Przy dokładniejszym zbadaniu można odkryć wyrytą pieczęć zakładu kowalskiego oraz datę wykonania. Po znaku i dacie widać, że brama ma około 20 lat.
- Ziemia pod bramą to twardy kamień/beton, więc szybki podkop nie ma sensu w tej scenie.
- Na górze bramy są słabo widoczne z dołu kolce, niebezpieczne przy przechodzeniu górą.
- Obok bramy jest solidny murowany płot, po którym można spróbować wejść, ale grozi to poślizgnięciem albo hałasem.

### Zasady Prowadzenia
- Nie kanalizuj graczy do jednej gotowej opcji. LLM/MG ma interpretować deklarację drużyny i dobrać mechanikę do opisu.
- Nagradzaj wcześniejsze badanie bramy, sensowne użycie narzędzi, asekurację i ciche działanie.
- Siłowe działania mogą od razu usunąć obie blokady, ale zwykle generują hałas.
- Ciche, precyzyjne działania powinny być mniej ryzykowne pod względem hałasu, ale mogą wymagać lepszego opisu, narzędzia albo trudniejszego testu.
- Nie zdradzaj od razu, że zawiasy są najsłabszym punktem. Ujawnij to po badaniu bramy, dobrym opisie działania albo sukcesie odpowiedniego testu.
- Jeśli gracze pytają o ryzyko, można opisać je fabularnie: skrzypienie, mokre drewno, kolce na górze, zatarty zamek, niestabilne okucia.
- Fail-forward nie oznacza abstrakcyjnych punktów postępu. Porażka może trwale
  zmienić konkretny element bramy, podnieść czujność goblinów, zastawić zasadzkę
  albo zranić wykonującego próbę. Dozwolone próby można powtarzać.

### Wiedza I Ograniczenia
- Brama nie ma magicznego hasła ani sekretnego przycisku otwierającego przejście.
- Szybki podkop jest niewykonalny w tej scenie z powodu twardego podłoża i ograniczonego czasu.
- Podpalenie bramy jest zablokowane jako szybkie rozwiązanie: wilgotne drewno i zarośla dadzą głównie dym, hałas i ryzyko, nie natychmiastowe przejście.
- Latanie, teleportacja albo inne magiczne obejścia działają tylko wtedy, gdy drużyna faktycznie ma odpowiedni czar, zasób albo efekt.
- Zwykła broń bez narzędzi i czasu nie powinna tworzyć dużej, bezpiecznej dziury w bramie.
- Jeśli gracze używają nieistniejącego zasobu, LLM/MG powinien poprosić o doprecyzowanie albo odrzucić założenie, zamiast przyznawać ten zasób.

## 6. Rola Interakcji W Scenie
- [ ] cel sceny
- [ ] trop/informacja
- [ ] zasób
- [x] ryzyko/komplikacja
- [x] przejście do innej lokacji
- [ ] walka/encounter
- [ ] klimat
- [x] wyzwanie
- [ ] inne:

## 7. Stan Początkowy
Dla obiektu/lokacji:
- stan fizyczny: stara drewniana brama z metalowymi okuciami, zawiasami i zardzewialym zamkiem
- czy jest zamknięty/uszkodzony/aktywny: zamknieta / stara / zatarty zamek / skorodowane zawiasy / rygiel po wewnetrznej stronie
- czy jest niebezpieczny: kolce na gorze, wystajace gwozdzie, ryzyko upadku przy wspinaczce

### 7A. Cele Widoczne Dla Graczy

- `force_entry`: Wyważcie bramę — `allow`: jedna postać, pomoc albo test grupowy.
- `open_lock`: Otwórzcie zamek — `must`: jedna postać.
- `look_around`: Rozejrzyjcie się — `must`: jedna wybrana postać; opis graczy
  rozstrzyga, czy chodzi o oczywisty materiał bez rzutu, czy ukryte znalezisko.
- `remove_bolt`: Zdejmijcie rygiel — pojawia się dopiero po
  `gate_lock_cleared`, ma ilustrację rygla i pozwala na jedną postać lub pomocnika.
  Znaleziona `gate_rotten_planks` ma proceduralne użycie `pry_bolt_with_plank`:
  Strength/Athletics ST 12 i autorskie konsekwencje bez klasyfikowania improwizacji
  przez LLM.
- `use_wall_route`: Przejdźcie odkrytą drogą — pojawia się dopiero po
  `gate_wall_route_found`.

Po wyborze gracze opisują metodę. Cel nie przyznaje premii i nie zastępuje
sprawdzenia przedmiotów oraz elementów sceny. Kafelki znikają, gdy ich konkretny
rezultat został już osiągnięty: nie można drugi raz otworzyć otwartego zamka ani
ponownie odkryć tego samego słabego punktu.

### 7AA. Reguły Metod

- `quiet_tradeoff`: jawne „po cichu” lub „bez hałasu” daje `-1` do próby.
  Sukces nie zwiększa czujności goblinów, a hałas porażki jest mniejszy o `1`.
- Lina z hakiem nadal daje `+2` wyłącznie przez istniejący zasób `rope` i pasujący
  tag `climbing`.

### 7AB. Styl Narracji

- Instancja: `heroic_dnd`, bohaterskie fantasy z lekką ironią starej bramy.
- `force_entry`: `heroic_charge`, dynamiczny power fantasy z sytuacyjnym humorem.
- `look_around`: `tense_discovery`, bez humoru i ironii; napięcie budowane detalem.

### 7AC. Kontekstowe „Rozejrzyjcie się”

- „Szukamy czegoś ciężkiego, czym można wyważyć bramę” albo parafraza funkcjonalna:
  bez rzutu, semantyczne dopasowanie istniejących desek i kamieni.
- „Szukamy czegoś przydatnego/interesującego”: stopniowane
  `survey_gate_surroundings`; progi ujawniają materiały, zawias, przejście i piłę.
- „Szukamy alternatywnej drogi”: `search_gate_alternate_route`, rzut odkrywający
  `gate_wall_route_found`; nowa karta może doprowadzić do zaskoczenia goblinów.
- „Oglądam zawiasy / gdzie najlepiej podważyć”: `inspect_gate_hinges`.
- „Szukam piły / czegoś do cięcia drewna”: `search_gate_cutting_tool`.
- Pułapki i zaglądanie przez szczelinę nadal korzystają z własnych obserwacji.
- Przykłady są semantycznymi wzorcami, a nie hasłami wymagającymi dosłownego tekstu.

Pole wiadomości pod kafelkami służy wyłącznie rozmowie z MG. Pytanie o to, czy
brama jest strzeżona, nie odkrywa goblinów i nie tworzy rzutu; MG sugeruje
nasłuchiwanie albo zajrzenie przez szczelinę. Metodę działania wpisuje się dopiero
w polu wybranej karty.

### 7B. Dostępne Przedmioty I Materiały

- `gate_rotten_planks`: 4 spróchniałe deski; widoczne, przenośne; po `/weź`
  trafiają do ekwipunku wybranego bohatera (`actor_inventory`).
- `gate_loose_stones`: 3 luźne kamienie; widoczne, przenośne; po `/weź`
  trafiają do ekwipunku wybranego bohatera (`actor_inventory`).
- `gate_corroded_hinges`: przytwierdzony fixture; `/weź` nie odłącza go
  automatycznie. Najpierw potrzebna jest osobna `/akcja`, która rozstrzygnie koszt,
  hałas i ewentualne pozyskanie `detached_gate_metal`.
- Samo `/szukaj` zapisuje wiedzę o elemencie, a `/użyj` wykorzystuje go w scenie;
  żadna z tych komend nie przenosi przedmiotu do ekwipunku.

### 7C. Crafting I Improwizacja

- `/zbuduj` korzysta z globalnych celów funkcjonalnych `heavy_force`,
  `climbing_aid`, `leverage` i `precision_tool`; scena nie definiuje gotowego taranu.
- Runtime dobiera brakujące komponenty według właściwości i pokazuje deski, kamienie,
  linę albo inne faktycznie dostępne źródła przed akceptacją.
- Jawnie ograniczony zestaw, np. „drabina tylko z kamieni”, nie może zostać po cichu
  uzupełniony innymi materiałami.
- Budowa rozlicza czas oraz zużycie/rezerwację komponentów, ale domyślnie nie wymaga
  rzutu. Ryzykowny test pojawia się dopiero przy późniejszym `/użyj`.

## 8. Co Gracze Mogą Realnie Próbować
- wywazenie
- wspinaczka
- poszukanie obejścia (wspinaczka po murze obok)
- wylamanie albo podwazenie zawiasow
- przerzucenie albo podsadzenie czlonka druzyny
- otworzenie zardzewialego zamka
- zbadanie bramy w poszukiwaniu slabszego punktu
- ciche oslabienie desek albo okuć

## 9. Czego Nie Powinno Się Dać Zrobić
- szybki podkop pod brama
- magiczne haslo do otworzenia bramy
- wyrabanie duzej dziury zwykla bronia bez narzedzi i czasu
- latanie/przelot na linie bez magii
- znalezienie gotowego ukrytego przycisku otwierajacego brame


## 10. Intencje
Propozycja docelowa:

```json
{
  "force": "allowed_with_consequence",
  "crafting": "allowed",
  "search": "allowed",
  "stealth": "allowed_with_consequence",
  "movement": "allowed_with_consequence",
  "lockpicking": "allowed_with_consequence",
  "magic": "blocked",
  "social": "blocked",
  "medical": "blocked",
  "theft": "blocked",
  "burn": "blocked"
}
```

Lokalne limity / konsekwencje:
- `force`: może usunąć zamek i rygiel w jednej próbie, ale zwykle generuje hałas.
- `crafting`: moze byc cichsze i stabilniejsze, szczegolnie po odkryciu skorodowanego zawiasu.
- `search`: moze ujawnic `weak_left_hinge` albo `craftsman_logo`.
- `stealth`: dozwolone, ale porazka zwieksza halas albo marnuje czas.
- `movement`: obejmuje wspinaczke po bramie/murze; porazka moze dac upadek, rane albo halas.
- `lockpicking`: dozwolone, ale zamek jest zatarty; porazka moze zaklinowac mechanizm.
- `burn`: zablokowane w tej scenie, bo wilgotne drewno i zarośla dadza raczej dym/halas niz szybkie przejscie.

## 11. Informacje Do Odkrycia
Informacja 1:
- id robocze: weak_left_hinge
- treść: Lewy zawias jest mocno skorodowany i można go podważyć dużo ciszej niż resztę bramy.
- warunek ujawnienia: sukces w badaniu bramy / dobre opisanie oględzin zawiasów
- flaga po ujawnieniu: weak_left_hinge_found
Informacja 2:
- id robocze: craftsman_logo
- treść: Na dole w rogu jest emblemat kowala ktory robil brame.
- warunek ujawnienia: krytyczny sukces przy badaniu bramy albo szukaniu znakow szczegolnych
- flaga po ujawnieniu: craftsman_emblem_revealed 

## 12. Możliwe Efekty Mechaniczne
- ustawia flagę: `gate_passed`
- blokady: `gate_lock_cleared`, `gate_bolt_cleared`
- przygotowanie: `weak_left_hinge_found`, `gate_structure_weakened`,
  `gate_ram_materials_found`, `gate_saw_found`, `gate_wall_route_found`
- stan przeciwników: `gate_goblin_ambush_prepared`, `gate_critical_breach`
- daje zasób: nie
- zabiera zasób: nie
- ujawnia punkt: nie
- odblokowuje lokację: `courtyard`
- zaczyna walkę: nie
- dodaje komplikację: hałas, zaklinowany zamek, bolesny upadek, skaleczenie o gwozdzie/kolce, stracony czas
- zmienia nastawienie NPC: duzy hałas moze zaniepokoic albo przestraszyc rannego zwiadowce po drugiej stronie sceny
- inne: `craftsman_emblem_revealed` jest informacja/flaga, nie zasobem, chyba ze pozniej zdecydujemy, ze emblemat da sie fizycznie zabrac
## 13. Testy I Trudności

tier content-driven (`easy`, `medium`, `hard`) zamiast ST per gotowe rozwiązanie.

Dla jakich sytuacji:
- siłowe sforsowanie: hard/medium/easy w zaleznosci od tego, jak gracze oslabia brame (zawiasy, zamek, rygiel z tylu)
- ciche obejście: medium
- podważanie/narzędzia: medium
- otwieranie zatartego zamka: hard, chyba ze gracze najpierw odkryja stan mechanizmu albo uzyja dobrego narzedzia
- mechanicznie otwieranie zamka to Dexterity check z `thieves_tools`; zestaw jest wymaganym itemem, a biegłość wynika z profilu aktora (bez dodatkowej premii za samo posiadanie)
- wspinaczka: medium, ale z ryzykiem kolcow/upadku
- badanie słabości: easy
- wejscie murem obok: easy
- przejscie gora przez brame bez przygotowania: medium/hard, zależnie od opisu zabezpieczenia i asekuracji

## 14. Sukces / Porażka / Krytyczne Wyniki
- `force_gate`, krytyczny sukces: puszcza zamek i rygiel, czujność nie rośnie,
  `gate_critical_breach` daje drużynie zaskoczenie.
- `force_gate`, sukces: puszcza zamek i rygiel, czujność rośnie o 2.
- `force_gate`, porażka: puszcza tylko zamek, czujność osiąga 3, gobliny
  przygotowują zasadzkę; próbę można powtórzyć.
- `force_gate`, krytyczna porażka: żadna blokada nie puszcza, czujność osiąga 3,
  gobliny przygotowują zasadzkę, a wykonujący próbę rozstrzyga hazard obrażeń.
- Otwarty zamek obniża ST późniejszego wyważania o 2. Zdjęty rygiel obniża je o 3.
  Odkryty słaby zawias i osłabiona konstrukcja obniżają je o kolejne 2 każdy.
- `lockpick_gate`, sukces: otwiera wyłącznie zamek; rygiel nadal trzyma bramę.
  Kafelek otwierania zamka znika.
- `remove_gate_bolt`, sukces: zdejmuje rygiel; właściwy test i modyfikatory
  zależą od opisanej metody, ale skutki flagowe pozostają autorskie.
- `find_way_around`, sukces: ustawia `gate_bypass_open` oraz
  `gate_wall_bypass_surprise`; wejście przy hałasie najwyżej 1 zaskakuje gobliny.
- Podważanie zawiasu albo budowa narzędzia nadal mogą ustawić
  `gate_structure_weakened`, lecz nie mają osobnego kafelka — wynikają z opisu
  działania po znalezieniu odpowiednich elementów.
- krytyczna porażka `force_gate` uruchamia `force_gate_backlash`: Constitution
  save ST 10 przeciw `1d6 bludgeoning`, połowa obrażeń przy sukcesie.
- formularz nowej opcji powinien jawnie podać: trigger hazardu, narrację, ability/ST save'a, skutek sukcesu, skutek porażki oraz typ i kość obrażeń; zagrożenie nie może istnieć wyłącznie w opisie dla LLM
  

## 15. Limity I Parametry
- maksymalna nagroda: otwarta brama i ciche wejscie na dziedziniec
- minimalna/maksymalna stawka:
- liczba prób: do skutku
- koszt czasu: kazda nieudana albo glosna proba moze zwiekszac ryzyko komplikacji fabularnej
- poziom hałasu: 0-3, zależnie od metody i wyniku
- limit zasobów: jeden istotny zasob/narzedzie na probe, chyba ze runtime pozniej obsluzy laczenie zasobow

## 16. Czy Interakcja Ma Progres?
Nie ma abstrakcyjnego paska postępu.

- Stan przejścia opisują dwie blokady: `gate_lock_cleared` i
  `gate_bolt_cleared`.
- Interakcję kończy usunięcie obu blokad albo ustawienie alternatywnej flagi
  `gate_bypass_open`.
- `gate_passed` jest ustawiane automatycznie po spełnieniu jednego z tych
  warunków.
- Osobny licznik `noise` ma zakres 0–3 i oznacza czujność goblinów:
  0 — nieświadome, 1–2 — podejrzliwe/gotowe, 3 — przygotowana zasadzka.

## 17. Konsekwencje Długoterminowe
- NPC pamięta: niedotyczy
- zmienia się reputacja: niedotyczy
- odblokowuje quest: niedotyczy
- zmienia encounter:niedotyczy
- wpływa na zakończenie sceny:niedotyczy

## 18. Przykładowe Deklaracje Graczy
- "biore rozbieg i wywarzam brame"
- "chce sprobowac przejsc gora"
- "szukam jakiegos bardziej dogodnego miejsca do przejscia"

## 19. Oczekiwany Feeling
- [ ] napięcie
- [ ] tajemnica
- [ ] humor
- [ ] moralny dylemat
- [x] szybka przeszkoda
- [ ] ważna rozmowa
- [ ] groza
- inne:

## 20. Uwagi
TODO

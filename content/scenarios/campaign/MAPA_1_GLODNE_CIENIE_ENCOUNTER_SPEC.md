# Mapa 1 — encounter „Głodne Cienie”

Status: robocza specyfikacja projektowa do implementacji i playtestu  
Scenariusz: `ostatni_transport_01_zawalona_droga`  
Encounter: `ostatni_transport_01_glodne_cienie`  
Docelowa drużyna: 3–5 bohaterów na poziomie 3  
Tryb sceny: encounter natychmiast po wejściu na Mapę 1, eksploracja dopiero po jego rozstrzygnięciu

## Obowiązująca rewizja walki (2026-08-26)

Ta rewizja zastępuje niżej opisany prototyp dzwonu, Skoku stada, morale i
`weighted_utility_v1`:

- stary dzwon nie jest obiektem ani interakcją encountera;
- profil działa jako deterministyczny `coordinated_pack_v1`;
- poplecznicy koncentrują się na bohaterze otoczonym przez największą liczbę
  innych popleczników, następnie wybierają najbliższego, bardziej rannego i
  stabilnie losowany remis; każdy inny poplecznik przy celu daje `+1` do ataku
  i obrażeń, niezależnie od flankowania;
- przewodnica używa Duchowego pocisku (`+5`, 60 ft, `1d6 + 2` psychic), a przy
  sąsiadującym bohaterze Wysysającego rozdarcia (`+3`, `1d4 + 2` necrotic),
  które leczy ją o połowę faktycznych obrażeń;
- po ataku dystansowym bez ruchu może uleczyć najbardziej rannego żywego
  poplecznika w 60 ft i linii widzenia o `1d6 + 2`; obecność bohatera przy niej
  blokuje tę regenerację;
- utrata przewodnicy albo wszystkich popleczników uruchamia nieodwracalny
  odwrót przez `pack_escape`. Nieosiągalne wyjście daje `cornered` i ponowną
  ocenę w kolejnej turze, bez ruchu zerowego i bez pętli stanów.

Źródłem wykonawczym pozostają pliki contentu i
`src/dnd_board_game/combat/coordinated_pack_ai.py`. Starsze sekcje poniżej
zachowano jako historię projektu mapy, nie jako aktywny kontrakt zasad.

## 1. Cel sceny

Encounter ma w pierwszych minutach pokazać najważniejsze cechy walki tej gry:

- fizyczny setup bohaterów, przeciwników i jawnego terenu;
- ruch, osłony, trudny teren, przewężenia oraz wysokość;
- przeciwników podejmujących czytelne decyzje zamiast atakowania najbliższego celu do śmierci;
- zwycięstwo przez obrażenia albo przełamanie zachowania stada;
- konsekwencję wcześniejszego rozpoznania Erynda;
- zachowanie stanu planszy po przejściu z walki do eksploracji.

Scena nie jest polowaniem na potwory. Drużyna ma przetrwać pierwszy napór i uzyskać kontrolę nad drogą. Zabicie wszystkich przeciwników jest legalne, ale nie jest wymagane ani dodatkowo nagradzane.

## 2. Prawda fabularna

### 2.1. Czym są Głodne Cienie

Głodne Cienie są wychudzonymi, czworonożnymi drapieżnikami żyjącymi w lasach wokół Czarnego Brodu. Nie są czartami, demonami ani nieumarłymi. Nazwę nadali im drwale, ponieważ:

- poruszają się niemal bezgłośnie;
- ich mokra, ciemna sierść zlewa się z cieniem drzew;
- przy ataku wydają dźwięk dochodzący jakby z niewłaściwego kierunku;
- po zmroku w ich oczach pojawia się szarobiały połysk.

Bliskość Głodnego Rezonansu wypaczyła ich orientację, głód oraz komunikację. Impulsy związane z szarym pyłem kojarzą im się jednocześnie z pożywieniem, bólem i obecnością obcego stada. Nie rozumieją tego zjawiska, ale reagują na nie kompulsywnie.

### 2.2. Co wydarzyło się przed przybyciem bohaterów

Transport zatrzymał się przy osuwisku. Jeden z wozów został uszkodzony, a impuls pochodzący z przewożonego ładunku ściągnął stado. Ludzie bronili się, część uciekła, a część została zaciągnięta w stronę lasu. W zamieszaniu młoda bestia została ranna i uwięziona przy starym przepuście.

Przewodnica stada pozostała w okolicy z trzech powodów:

1. chroni ranne młode;
2. próbuje zdobyć jedzenie z porzuconych zapasów;
3. reaguje na kolejne impulsy Rezonansu dobiegające od wozów.

Kiedy drużyna wchodzi do wąwozu, zostaje uznana za konkurencyjne stado idące w stronę młodego i źródła impulsu.

### 2.3. Czego chce stado

Priorytety stada, od najważniejszego:

1. nie dopuścić obcych do przepustu i młodego;
2. odgonić bohaterów od uszkodzonego wozu;
3. zdobyć łatwe pożywienie;
4. ocalić przewodnicę i zdolnych do ucieczki członków stada.

Stado nie chce honorowej walki ani śmierci bohaterów za wszelką cenę. Gdy uzna drogę za zbyt niebezpieczną, wycofa się.

### 2.4. Czego się boi

- **Otwarty ogień:** nie zwykłego pojedynczego trafienia obrażeniami od ognia, lecz trwałej płonącej bariery albo gwałtownego płomienia blokującego drogę.
- **Stary dzwon:** jego metaliczny ton nakłada się na Rezonans i dezorientuje stado.
- **Bieżąca woda:** strumień tłumi zapach oraz nieprawidłowe impulsy; bestie przekraczają go tylko w desperacji.
- **Utrata przewodnicy:** bez jej sygnałów poszczególne Cienie przestają działać jak jedna grupa.
- **Odcięcie drogi odwrotu:** nie przełamuje morale. Przeciwnie, osaczone stworzenie broni się rozpaczliwie, dopóki nie zobaczy wyjścia.

## 3. Przeciwnicy

### 3.1. Głodny Cień — harcownik stada

Rola: szybki przeciwnik oskrzydlający i wypychający bohaterów z bezpiecznych pozycji.

Wstępny profil do playtestu:

| Parametr | Wartość robocza |
|---|---:|
| KP | 13 |
| PW | 14 |
| Szybkość | 40 ft |
| Atak | +5 |
| Obrażenia | `1d4 + 2` cięte |
| Save zdolności | ST 12 |

Zdolności robocze:

- **Skok stada:** jeżeli Cień przemieścił się co najmniej 10 ft i przy celu stoi inny Cień, trafiony cel wykonuje Strength save ST 12. Porażka przewraca go. Zdolność nie dodaje obrażeń.
- **Zmysł Rezonansu:** potrafi wskazać kierunek uszkodzonego ładunku, ale nie zna pozycji ukrytych bohaterów i nie ignoruje zwykłych zasad widoczności.

Głodny Cień nie otrzymuje odporności na zwykłą broń. Pierwsza walka nie powinna karać postaci niemagicznych ani udawać wyższego poziomu trudności przez sztuczne zwiększanie PW.

### 3.2. Przewodnica stada — kontroler i kotwica morale

Rola: utrzymuje spójność stada, blokuje podejście do przepustu i zarządza odwrotem. Nie powinna zadawać obrażeń jak boss kampanii.

Wstępny profil do playtestu:

| Parametr | Wartość robocza |
|---|---:|
| KP | 14 |
| PW | 30 |
| Szybkość | 40 ft |
| Atak | +6 |
| Obrażenia | `1d8 + 3` cięte |
| Save zdolności | ST 12–13 |

Zdolności robocze:

- **Skok stada przewodnicy:** działa jak u harcownika, ale używa Strength save ST 13.
- **Osłona młodego:** przewodnica preferuje cel znajdujący się najbliżej wejścia do przepustu, jeżeli taki bohater rzeczywiście zagraża młodemu.
- **Kotwica morale:** jej zranienie do połowy PW, śmierć albo ucieczka uruchamiają jednorazowe zdarzenia morale encountera.

### 3.3. Ranna młoda bestia

Młoda bestia nie jest aktorem bojowym ani legalnym celem podczas encountera. Jej głos dobiega z przepustu i uzasadnia zachowanie przewodnicy. Po zakończeniu walki zostaje ujawniona jako punkt eksploracyjny.

Jest ranna i częściowo uwięziona. Dzięki temu pozostaje na miejscu niezależnie od tego, czy reszta stada została zabita, odpędzona albo odciągnięta jedzeniem. Drużyna podejmuje później osobną decyzję: pomóc, pozostawić albo dobić.

## 4. Skalowanie według liczby bohaterów

Skalowanie zmienia liczbę akcji przeciwników, a nie mnoży ich PW.

| Bohaterowie | Wariant encountera | Morale początkowe |
|---:|---|---:|
| 1 | 1 osłabiony Głodny Cień; przełamanie po jego zranieniu do połowy PW | 1 |
| 2 | 1 Głodny Cień + osłabiona przewodnica, 20 PW | 2 |
| 3 | 2 Głodne Cienie + przewodnica | 3 |
| 4 | 3 Głodne Cienie + przewodnica | 4 |
| 5 | 4 Głodne Cienie + przewodnica | 4 |

Podstawowym zakresem balansu pozostaje 3–5 bohaterów. Warianty 1–2 służą temu, aby kampania nie przestawała działać technicznie, ale wymagają osobnego playtestu pod kątem losowości i ekonomii akcji.

## 5. Plansza taktyczna 20 × 30

Kierunek wejścia drużyny: południe.  
Droga do dalszej eksploracji: północ.  
Przepust i legowisko: zachód.  
Wieża sygnałowa: północny wschód.

### 5.1. Strefy

| Strefa | Pola robocze | Funkcja taktyczna | Kto korzysta |
|---|---|---|---|
| Wejście do wąwozu | kol. 5–14, rzędy 25–28 | pola startowe bohaterów; szeroki front, mało osłon | bohaterowie ustawiają szyk |
| Błotnista koleina | kol. 5–14, rzędy 17–23 | trudny teren spowalniający pierwszy napór | strzelcy i kontrolerzy |
| Przewrócony wóz | kol. 6–13, rzędy 11–14 | blokada ruchu i połowiczna osłona | obie strony; bohaterowie łatwiej utrzymują front |
| Zwalony pień | `[3–6,16]` | przechodnie defensive spots; automatyczne `+2 KP` bez akcji | obie strony |
| Rozsypane skrzynie | `[5–7,19]` | przechodnie defensive spots; automatyczne `+2 KP` bez akcji | obie strony |
| Szczątki wozu | `[12–14,19]` | przechodnie defensive spots; automatyczne `+2 KP` bez akcji | obie strony |
| Zachodni przepust | kol. 0–5, rzędy 9–14 | wąskie przejście, osłona i wejście do młodego | stado zna skrót; bohater może zablokować przejście |
| Wschodnia skarpa | kol. 14–19, rzędy 4–17 | pozycja strzelecka z czystą linią widzenia, jedno podejście | Erynd i inni strzelcy; ryzyko odcięcia |
| Rozsypany ładunek | kol. 7–12, rzędy 7–10 | kotwica fabularna Rezonansu; przyciąga stado | przeciwnicy patrolują tę strefę |
| Wieża i stary dzwon | kol. 15–19, rzędy 1–6 | cel taktyczny przełamujący morale | mobilny bohater lub silna postać utrzymująca podejście |
| Boczne zejście i strumień | kol. 0–6, rzędy 0–10 | trudny teren i bezpieczna trasa ucieczki stada | stado po przełamaniu; bohaterowie mogą skierować tam przynętę |

Współrzędne layoutu v4 są zamrożone po przejściu testów pathfindingu i 64
symulowanych walk. Zmiana pól od tej chwili wymaga równoczesnej aktualizacji
mapy, encountera, layoutu taktycznego i testów setupu.

### 5.2. Relacje przestrzenne

```text
PÓŁNOC

  STRUMIEŃ / UCIECZKA      ŁADUNEK       WIEŻA + DZWON
          \                   |                /
           \---- PRZEWRÓCONY WÓZ ------------/
            \       BŁOTNISTA KOLEINA        /
      PRZEPUST + MŁODE             SKARPA STRZELECKA
                       \           /
                    WEJŚCIE DRUŻYNY

POŁUDNIE
```

### 5.3. Przewagi i ryzyka

- **Wóz:** zapewnia bezpieczny front, ale pozostanie całej drużyny za jednym obiektem pozwala Cieniom obejść ją przepustem i skarpą.
- **Skarpa:** daje czystą linię strzału i pozwala ignorować osłonę wozu, lecz postać na szczycie może zostać odcięta.
- **Przepust:** jedna postać może zatrzymać tam kilka bestii, ale wejście głębiej uruchamia zachowanie ochronne przewodnicy.
- **Błoto:** spowalnia obie strony. Bohaterowie mogą wykorzystać je do kontroli pierwszego naporu; Cienie próbują omijać je bokami.
- **Dzwon:** jest silnym celem taktycznym, ale wymaga opuszczenia wygodnej osłony.
- **Strumień:** osłabia agresję stada i zapewnia czytelny kierunek ucieczki. Zablokowanie go może zmusić złamane Cienie do dalszej walki.

### 5.4. Kontrakt reguł terenu

Jedno pole odpowiada 5 ft. Elementy nie dodają ukrytych modyfikatorów: ich działanie musi być widoczne w podglądzie pola przed zatwierdzeniem ruchu albo akcji.

| Element | Reguła podczas walki |
|---|---|
| Błotnista koleina | Każde 5 ft ruchu kosztuje 10 ft. Nie wpływa na testy ani ataki. |
| Środek przewróconego wozu | Pole blokujące ruch i linię widzenia. |
| Krawędź wozu | Daje połowiczną osłonę, czyli `+2 KP`, jeśli znajduje się między źródłem ataku a celem. Nie działa przeciw atakowi z tej samej strony wozu. |
| Podejście na skarpę | Trudny teren; wejście kosztuje dodatkowy ruch wynikający wyłącznie z oznaczonych pól podejścia. |
| Krawędź skarpy | Daje połowiczną osłonę przed atakiem z dołu. Wysokość nie daje przewagi do rzutu ataku ani premii do obrażeń, ale otwiera linię widzenia ponad niską krawędzią wozu. |
| Przepust | Przewężenie szerokie na jedno pole. Stworzenia mogą przechodzić pojedynczo; nie można przeciskać się przez wrogie pole. |
| Strumień | Trudny teren. Przekroczenie go przez niezłamany Cień jest legalne tylko wtedy, gdy nie istnieje inna droga do celu. |
| Pole ucieczki | Wejście na nie kończy ruch uciekającego Cienia i usuwa go z encountera jako żywego. Zwykłe opportunity attacks nadal obowiązują. |

### 5.5. Interakcje bojowe

Interakcje są hotspotami dostępnymi tylko podczas tury bohatera. Podejście do obiektu zużywa zwykły ruch, a uruchomienie — akcję, o ile karta albo cecha nie mówi wyraźnie inaczej.

#### Stary dzwon

- warunek: bohater stoi przy mechanizmie dzwonu;
- koszt: akcja, bez testu;
- efekt: morale stada `−2`, tylko przy pierwszym uruchomieniu;
- dalsze użycia: wyłącznie opis i dźwięk, bez kolejnego efektu;
- ryzyko: mechanizm znajduje się poza główną osłoną i nie chroni używającego przed opportunity attack podczas dojścia.

#### Bariera ognia

- zaklęcie lub karta tworząca utrzymujący się obszar ognia działa zgodnie ze swoim tekstem;
- źródło niemagiczne wymaga odpowiedniego przedmiotu, legalnego miejsca oraz akcji jego użycia;
- `fire_used_against_pack` i morale `−1` aktywują się dopiero, gdy ogień tworzy co najmniej trzy sąsiadujące pola odcinające jedną z normalnych dróg stada;
- pojedyncza pochodnia, chwilowe obrażenia od ognia ani ponowne podpalenie tej samej linii nie zmieniają morale;
- płonące pola są niebezpieczne dla obu stron i pozostają jawne aż do wygaśnięcia źródła.

#### Przynęta z żywności

- warunek: drużyna posiada zapas żywności i bohater stoi na polu sąsiadującym z miejscem wyłożenia;
- koszt: akcja i trwałe zużycie jednego zapasu drużyny;
- legalne miejsce: oznaczone pole przy trasie do strumienia, które nie jest zajęte ani objęte ogniem;
- efekt nie jest natychmiastowy: na początku kolejnej tury stada, jeśli istnieje legalna droga do przynęty, morale spada o `2` i ustawiana jest flaga `pack_lured_with_food`;
- jeżeli bohaterowie zablokują jedyną drogę albo zniszczą przynętę przed tym momentem, zapas przepada, ale morale nie spada.

#### Odgłosy z przepustu

Przepust jest podczas walki widocznym źródłem dźwięku, nie interakcją. Pierwsze zbliżenie bohatera ujawnia komunikat, że w środku znajduje się coś młodego i rannego. Nie otwiera eksploracji i nie wymaga testu; ma pozwolić graczom zrozumieć zachowanie przewodnicy jeszcze przed końcem walki.

### 5.6. Robocze sloty setupu

Współrzędne są zapisane jako `[kolumna, rząd]` i służą pierwszemu testowi pathfindingu. Pozycje bohaterów są wybierane przez graczy w obrębie strefy, natomiast pozycje bestii i terenu są odtwarzane dokładnie również po Retry.

- pola bohaterów: `[8,27]`, `[9,27]`, `[10,27]`, `[11,27]`, `[12,27]`;
- lewy harcownik: `[6,17]`;
- prawy harcownik: `[13,17]`;
- tylny prawy harcownik: `[13,14]`;
- harcownik przepustu: `[5,12]`;
- przewodnica: `[6,13]`;
- wariant jednoosobowy: osłabiony Cień zaczyna na `[10,17]`.

Nakładka `glodne_cienie_tactical_zones_v3.svg` zachowuje krótkie oznaczenia
slotów `S1–S4`, `P` i `1P`; nowe defensive spots są zapisane w
`glodne_cienie_tactical_layout_v5.json` i nadrukowane na battlemapie v5 bez starego dzwonu.
Runtime podświetla tylko pola należące do wariantu wybranego dla aktualnej
liczby bohaterów; komplet oznaczeń startowych jest widoczny wyłącznie na
grafice projektowej.

| Bohaterowie | Obsadzane sloty przeciwników |
|---:|---|
| 1 | wariant jednoosobowy |
| 2 | prawy harcownik, przewodnica |
| 3 | lewy harcownik, prawy harcownik, przewodnica |
| 4 | jak wyżej oraz tylny prawy harcownik |
| 5 | jak wyżej oraz harcownik przepustu |

Setup na ekranie powinien prowadzić kolejno przez: mapę i orientację, jawny teren, bohaterów, zwykłe Cienie, przewodnicę. Młode nie otrzymuje figurki przed eksploracją.

## 6. Rozpoczęcie encountera

Decyzja o tempie podejścia wpływa na otwarcie walki. Wiedza Erynda nie daje stałego bonusu do ataków; pozwala poprawnie zinterpretować ciszę, odwrócone echo i zachowanie zwierząt.

| Podejście | Bez wiedzy Erynda | Z `knowledge.convoy_route_magic_suspected` |
|---|---|---|
| Szybkie | drużyna ma utrudnienie do inicjatywy | brak zaskoczenia |
| Normalne | brak zaskoczenia | drużyna może wykonać precombat Hide |
| Ostrożne | drużyna może wykonać precombat Hide | Hide oraz przewaga do inicjatywy |

W otwarciu z wiedzą Erynda narrator mówi wprost, że Erynd rozpoznaje magicznie zaburzone echo i ostrzega drużynę chwilę przed skokiem stada. Nie ujawnia jeszcze prawdy o Rezonansie ani ładunku.

## 7. Przebieg walki

### 7.1. Ton i czytelność sceny

Walka ma być nerwowa i zwierzęca, nie heroicznie monumentalna. Cienie najpierw słychać po obu stronach drogi, potem na moment widać ich sylwetki, a dopiero później następuje skok. Nie warczą bez przerwy i nie wygłaszają kwestii. Komunikują zamiar ustawieniem ciała, krótkim skowytem i wycofaniem uszu.

Każda ważna zmiana zachowania otrzymuje komunikat przed wykonaniem wynikającej z niej akcji:

- przewodnica spogląda ku przepustowi, zanim zacznie go bronić;
- ranny Cień obniża sylwetkę i szuka drogi do stada, zanim się wycofa;
- złamane stado odpowiada na skowyt i odwraca się ku strumieniowi;
- osaczone zwierzę pokazuje zęby i rzuca się wyłącznie na blokującego drogę.

Dzięki temu algorytm może być przewidywalny, ale nie powinien sprawiać wrażenia mechanicznego. Gracz ma rozumieć, dlaczego przeciwnik zmienił cel.

### Faza A — pierwszy napór

Czas: zwykle runda 1.

- Cienie próbują wejść z dwóch stron błotnistej koleiny.
- Nie więcej niż połowa stada wybiera ten sam bok, jeżeli drugi legalny bok pozostaje dostępny.
- Przewodnica pozostaje między wozem a przepustem i nie szarżuje samotnie na pierwszą linię.
- Wagi `leader` utrzymują przewodnicę między wozem a przepustem, dopóki młode jest zagrożone.

Cel fazy: nauczyć graczy, że pozostawienie otwartych boków ma konsekwencje, a błoto i wóz są rzeczywistymi narzędziami.

### Faza B — polowanie albo impas

Czas: zwykle rundy 2–4.

Stado wybiera między trzema zachowaniami:

- **Polowanie:** co najmniej jeden bohater jest odizolowany i osiągalny.
- **Ochrona:** bohater zbliżył się do przepustu albo młodego.
- **Obejście:** front przy wozie jest zablokowany, ale istnieje legalna droga przez bok lub skarpę.

W tej fazie drużyna może przejąć inicjatywę, docierając do dzwonu, tworząc linię ognia, wystawiając jedzenie albo raniąc przewodnicę.

### Faza C — załamanie stada

Rozpoczyna się, gdy morale spadnie do zera.

- wszystkie zdolne do ruchu Cienie otrzymują stan `fleeing`;
- wybierają najkrótszą legalną trasę do strumienia albo północnej krawędzi;
- preferują Disengage, następnie Dash;
- nie atakują, jeżeli istnieje legalna droga ucieczki;
- encounter kończy się, gdy wszystkie pozostałe Cienie uciekną albo zostaną pokonane;
- uciekających bestii nie trzeba fizycznie ścigać do ostatniego pola, jeśli żadna postać nie blokuje wyjścia i nie deklaruje pościgu.

Osaczone stworzenie nie uzyskuje `fleeing`. Przechodzi w `cornered`: używa Dodge, próbuje stworzyć przejście i atakuje wyłącznie aktora blokującego ucieczkę.

## 8. Morale stada

Morale jest jawnym paskiem encountera. Gracze widzą stan opisowy, ale nie muszą widzieć wszystkich ukrytych wag przed ich odkryciem.

| Zdarzenie | Zmiana morale | Limit |
|---|---:|---|
| Przewodnica spada do połowy PW | −1 | raz |
| Przewodnica zostaje pokonana | −2 | raz |
| Przewodnica ucieka z planszy | −2 | raz |
| Połowa zwykłych Cieni zostaje pokonana | −1 | raz |
| Bohater uruchamia stary dzwon | −2 | raz |
| Powstaje trwała linia otwartego ognia | −1 | raz |
| Jedzenie zostaje wystawione przy trasie odwrotu | −2 | raz |

Morale nie spada od każdego trafienia ogniem ani od wielokrotnego dzwonienia. Ma nagradzać zmianę sytuacji na planszy, a nie spamowanie jednej akcji.

Zmiana morale jest rozpatrywana natychmiast po zdarzeniu i ograniczana do zakresu `0..maximum`. Zero oznacza złamane stado. Nie uruchamia darmowego ruchu: w swojej turze bestia ucieka, jeśli ma legalną drogę, albo przechodzi w `cornered`, jeśli jest osaczona. Po późniejszym otwarciu drogi zacznie uciekać bez potrzeby kolejnego zdarzenia morale.

### Taktyczne drogi zakończenia

1. **Siła:** pokonać przewodnicę i wystarczającą część stada.
2. **Dzwon:** dotrzeć do wieży i uruchomić dzwon, następnie pozostawić drogę odwrotu.
3. **Ogień:** stworzyć trwałą barierę i dołożyć drugi bodziec morale, np. zranić przewodnicę.
4. **Pożywienie:** zużyć rzeczywisty zapas, umieścić go przy strumieniu i utrzymać drogę dojścia do końca kolejnej tury stada.
5. **Podejście mieszane:** dowolna kombinacja strat, ognia, dzwonu i przynęty.

Nie ma osobnego pokojowego dialogu z bestiami. Uspokojenie jest przyszłą akcją dla legalnego źródła magicznego albo zdolności postaci i musi używać tego samego paska morale.

## 9. AI przeciwników

AI tego encountera korzysta z generycznego modelu `weighted_utility_v1` opisanego w `docs/UTILITY_ENEMY_AI.md` i strojonego przez `content/ai_profiles/hungry_shadow_pack.json`.

### 9.1. Uproszczony algorytm

W normalnej turze silnik:

1. generuje legalne warianty `engage`, `advance`, `regroup`, `guard` i `flee`;
2. każdy wariant zawiera już konkretny cel, pole końcowe, ścieżkę i akcję;
3. wylicza cechy `0.0–1.0`, np. izolację celu, własne obrażenia, osłonę, wsparcie stada i ryzyko opportunity attack;
4. mnoży cechy przez wagi roli `skirmisher` albo `leader`;
5. dodaje niewielki szum `−3..+3` ze stabilnego seeda encountera;
6. zachowuje cały zwycięski plan, pokazuje jego intencję i wykonuje go po potwierdzeniu planszy.

Wzór:

```text
score = base_score[intent]
      + suma(feature_value * configured_weight)
      + seeded_noise
```

Nie ma osobnego drzewa `jeśli PW < 50%, to uciekaj`. Wraz ze spadkiem PW rośnie `self_injury`: ryzykowny atak stopniowo traci punkty, a przegrupowanie i ucieczka je zyskują. `morale_pressure` rośnie wraz ze stratami stada. Harcownik nadal może zaatakować, jeśli ranny cel jest bardzo dobry, ale ciężko ranny i przestraszony osobnik może sam wybrać `flee`, zanim morale całej grupy spadnie do zera.

### 9.2. Role

- **Harcownik:** wysoko punktuje odizolowany cel, wsparcie drugiego Cienia i możliwość ataku po ruchu. Traci punkty za oddalenie od stada, własne obrażenia, ogień i opportunity attacks.
- **Przewodnica:** najmocniej punktuje ochronę strefy `pack_den`. Jest mniej zainteresowana dalekim pościgiem; obrażenia przesuwają ją ku osłonie, ale zagrożenie młodego nadal może przeważyć.

Role różnią się wyłącznie wagami. Silnik nie zawiera klas `HungryShadowAI` ani `PackLeaderAI`.

### 9.3. Twarde wymuszenia

Utility scoring nie powinien rozstrzygać wszystkiego:

- morale większe od zera: `flee` konkuruje z pozostałymi intencjami;
- morale równe zero i dostępne wyjście: wymuś `flee`;
- morale równe zero i brak wyjścia: wymuś `cornered`;
- brak widocznego celu: użyj istniejącego `Search`;
- nielegalne akcje i ścieżki nigdy nie stają się kandydatami.

Przy `flee` Cień preferuje Disengage, jeżeli grozi mu opportunity attack, a w przeciwnym razie Dash. Przy `cornered` używa Dodge albo atakuje postać blokującą najkrótszą drogę. Nie potrzebujemy stanu `break_pending`: morale pozostaje na zero i po otwarciu drogi kolejna decyzja automatycznie staje się ucieczką.

### 9.4. Kontrolowana losowość

Losowość nie pochodzi z czasu systemowego. Seed uwzględnia encounter, rundę, aktora, numer decyzji i stabilny klucz kandydata. Dzięki temu:

- podobnie dobre flanki mogą być wybierane różnie w osobnych rozgrywkach;
- zapis i odczyt odtwarzają decyzję;
- Retry odtwarza seed checkpointu;
- szum nie przebija dużych kar za ogień, osaczenie lub porzucenie młodego.

### 9.5. Zakres wiedzy

AI używa tylko widocznych aktorów, jawnego PW, stanu terenu, legalnych ścieżek, osłon i otagowanych stref. Nie zna klasy bohatera, jego niewydanych kart ani zasobów. Nie dobija automatycznie postaci przy 0 PW; nieprzytomny aktor nie jest legalnym celem `engage`, dopóki istnieje żywe zagrożenie.

### 9.6. Diagnostyka

Log każdej decyzji przechowuje zwycięski wynik, dodany szum i trzy cechy o największym wpływie. Przykład:

```text
hungry_shadow_b -> regroup @ [8,12]
raw=51.0 noise=-1.4 final=49.6
reasons: self_injury +25.5, end_near_leader +18.0, hazard_exposure -8.0
```

Gracz widzi jedynie wynikową intencję, np. „Ranny Cień wycofuje się ku przewodnicy”. Pełna punktacja służy debugowaniu i strojeniu profilu.

## 10. Warunki końca i stan przekazywany eksploracji

### Zwycięstwo

Encounter kończy się zwycięstwem, jeśli:

- na planszy i w aktywnej inicjatywie nie pozostał żaden żywy przeciwnik;
- technicznie: `active_hostile_count == 0`.

Każdy przeciwnik kończy udział w encounterze dokładnie jednym wynikiem:

- `dead` — jego PW spadły do zera;
- `escaped` — wszedł na pole `pack_escape` podczas realizacji `flee`.

Przeciwnicy nie stają się nieprzytomni, nie wykonują death saves i nie mogą być stabilizowani. Zarówno śmierć, jak i ucieczka usuwają aktora z inicjatywy, blokowania ruchu oraz legalnych celów i otwierają instrukcję zdjęcia figurki. Uciekinier pozostaje żywy wyłącznie w outcome ledgerze.

### Porażka

- wszyscy bohaterowie są martwi albo niezdolni do kontynuowania;
- drużyna deklaruje odwrót albo kapitulację — w obecnym encounter-first przebiegu oznacza to Game Over.

### Flagi wyniku

| Flaga | Znaczenie |
|---|---|
| `map1_encounter_cleared` | można rozpocząć eksplorację |
| `pack_broken` | stado uciekło przez morale |
| `pack_killed` | wszystkie dorosłe bestie zostały zabite |
| `pack_resolution` | `killed`, `escaped` albo `mixed` |
| `pack_killed_count` | liczba przeciwników z wynikiem `dead` |
| `pack_escaped_count` | liczba przeciwników z wynikiem `escaped` |
| `pack_lured_with_food` | zużyto zapasy i odciągnięto stado |
| `bell_used_against_pack` | użyto starego dzwonu |
| `fire_used_against_pack` | utworzono trwałą barierę ognia |
| `pack_leader_survived` | przewodnica opuściła mapę żywa |
| `young_beast_revealed` | po walce ujawniono młodą bestię |

Flagi opisują sposób rozwiązania i późniejsze konsekwencje. Nie zmieniają bazowej nagrody za ukończenie encountera.

## 11. Kontrakt techniczny implementacji

### 11.1. Elementy generyczne do dodania w silniku

- data-driven wariant składu encountera według liczby bohaterów;
- loader profilu `weighted_utility_v1`, generator kandydatów i punktowanie cech;
- role przeciwników różniące się wagami zamiast osobnymi klasami AI;
- encounter seed i krótka pamięć poprzedniego celu;
- jawny licznik morale oraz jednorazowe źródła jego zmiany;
- pola ucieczki i usuwanie aktora po ich osiągnięciu;
- wynik aktora `dead` albo `escaped` bez nieprzytomności przeciwników;
- jeden warunek zwycięstwa `active_hostile_count == 0`;
- outcome ledger rozróżniający zabitych i zbiegłych;
- interakcje bojowe: dzwon, linia ognia i wystawienie pożywienia;
- zachowanie stanu fixture'ów po przejściu do eksploracji.

### 11.2. Elementy scenariuszowe

- pięć wariantów składu dla drużyn 1–5;
- strefy startowe, teren trudny, osłony, skarpa, przepust, strumień i dzwon;
- przewodnica i zwykły Głodny Cień jako osobne definicje potworów;
- `ai_profile_ref: hungry_shadow_pack` oraz rola `skirmisher` lub `leader` na aktorach;
- tag `pack_den` na przepuście, `pack_escape` na wyjściach oraz `pack_hazard` na aktywnym ogniu;
- młoda bestia jako ukryty punkt eksploracyjny;
- opening policy zależne od tempa i flagi Erynda;
- outcome zapisujący sposób rozstrzygnięcia.

### 11.3. Elementy wyłączone podczas walki

- rozmowa z Terenem;
- przeszukiwanie wozów i skrzyń;
- zabieranie lekarstw, manifestu i pierścienia;
- wybór dalszej drogi;
- długie obserwacje śladów i ładunku.

Teren może być widocznym elementem chronionym albo leżącą postacią sceny, ale nie otwiera interakcji NPC przed zakończeniem encountera.

## 12. Testy

### Jednostkowe

- każdy rozmiar drużyny wybiera dokładnie jeden wariant składu;
- zmiany morale są jednorazowe i nie przekraczają zakresu;
- morale zero z zablokowaną drogą wybiera `cornered`, a po jej otwarciu `flee`;
- ranny osobnik może wybrać punktowane `flee` przy morale większym od zera;
- AI nie zna ukrytych aktorów ani klas postaci;
- wzrost `self_injury` płynnie zwiększa wynik `regroup` względem `engage`;
- ten sam seed i stan dają ten sam plan, a różne seedy zmieniają tylko zbliżone wyniki;
- duża kara za hazard nie może zostać przebita przez szum `−3..+3`;
- `fleeing` preferuje Disengage, następnie Dash;
- `cornered` nie próbuje przejść przez zajęte albo blokujące pole;
- wejście przeciwnika na `pack_escape` zapisuje `escaped` i usuwa go z aktywnej walki;
- 0 PW zapisuje `dead` bez stanu nieprzytomności i death saves;
- ostatni wynik `dead` lub `escaped` kończy encounter przez `active_hostile_count == 0`;
- dzwon, ogień i żywność stosują prawidłowy koszt i efekt.

### Integracyjne

- wejście na Mapę 1 uruchamia setup encountera przed eksploracją;
- pierwszy setup oraz retry pokazują bohaterów, przeciwników i teren;
- flaga Erynda zmienia wyłącznie opening policy;
- zwycięstwo przez obrażenia i morale ujawnia te same podstawowe punkty eksploracji;
- stan wozu, ognia, dzwonu i żyjących bestii przechodzi do eksploracji;
- Game Over i retry odtwarzają identyczny wariant, pozycje i inicjatywę.

### Manualny playtest

- walka trwa zwykle 3–6 rund;
- co najmniej dwa elementy terenu są faktycznie używane;
- gracze rozumieją, że stado można złamać bez zabicia wszystkich;
- droga do dzwonu jest ryzykowna, ale wykonalna;
- Cienie sprawiają wrażenie stada, a nie niezależnych pionków;
- odwrót przeciwników jest czytelny i nie wymaga żmudnego dobijania;
- żadna pojedyncza metoda morale nie kończy pełnego wariantu 3–5 osobowego bez dodatkowego działania drużyny.

## 13. Kryteria zamrożenia projektu przed grafikami

Przed wygenerowaniem finalnej mapy i ilustracji trzeba zatwierdzić:

1. liczbę i rozmieszczenie stref;
2. skład wariantów dla 3, 4 i 5 bohaterów;
3. wartości PW, KP i obrażeń;
4. próg morale oraz wagi dzwonu, ognia i żywności;
5. położenie młodej bestii i tras ucieczki;
6. sposób pokazania wysokości oraz osłony na fizycznej planszy;
7. listę obiektów wymagających osobnych znaczników lub ilustracji.

Po zamrożeniu topologii można przygotować mapę, portrety, tokeny przeciwników, ikonę morale i grafiki interakcji bojowych.

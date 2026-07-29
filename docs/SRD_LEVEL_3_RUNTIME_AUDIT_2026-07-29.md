# Audyt zgodności mechanik postaci z SRD 5.1

Data audytu: 2026-07-29  
Zakres: D&D 5e 2014 / SRD 5.1, postacie jednoklasowe do 3. poziomu,
9 ras, 12 klas i 127 czarów poziomów 0–2.

Źródłem porównawczym jest
[System Reference Document 5.1](https://media.wizards.com/2016/downloads/DND/SRD-OGL_V5.1.pdf).
Audyt sprawdza nie tylko obecność wpisu w katalogu, ale również koszt akcji,
celowanie, zasięg, koncentrację, czas działania, skalowanie, rzeczywisty wpływ
na stan gry, obsługę planszy oraz komunikat widoczny dla gracza.

## Domknięcie audytu na Arenie

Lista robocza audytu została przeniesiona do wykonywalnego rejestru
`content/scenarios/mechanics_playground/audit_cases.json`. Rejestr jest
autorytatywnym źródłem bieżącego statusu i zapisanych konfiguracji Areny.

| Wynik | Liczba |
|---|---:|
| Wszystkie przypadki | 236/236 |
| Przetestowane automatycznie | 177 |
| Świadomie pominięte z komentarzem | 59 |
| Nierozstrzygnięte | 0 |

Pokrycie obejmuje 127 czarów, 29 cech rasowych, 58 cech klasowych, 20 cech
podklas oraz 2 mechaniki przekrojowe: flankowanie i rejestr konsumentów efektów
czarów. Każdy przypadek zawiera odtwarzalny `arena_config`, kroki ręczne i
oczekiwany rezultat. Status `skipped` nie oznacza przeoczenia: wskazuje element,
którego uczciwe domknięcie wymaga nowego systemu (np. trwałych iluzji, aktorów
chowańców, zegara świata albo kontraktu rozmowy LLM), a komentarz w rejestrze
opisuje konkretną granicę.

Poniższe tabele zachowują stan i rozpoznanie problemów z chwili pierwotnego
audytu. Bieżący wynik napraw i testów należy odczytywać z rejestru Areny.

## Legenda

| Status | Znaczenie |
|---|---|
| ✅ Zgodne | Główna mechanika działa deterministycznie i odpowiada SRD. |
| 🟡 Adaptacja | Grywalne, lecz uproszczone albo zależne od oznaczonej sceny/stanu stołu. |
| 🟠 Częściowe | Czar lub cecha działa tylko w części; istotny rider, wybór, czas albo przypadek brzegowy nie jest egzekwowany. |
| 🔴 Błąd/brak efektu | Dane są błędne albo po użyciu powstaje głównie znacznik bez deklarowanego skutku. |
| ⚪ Wybór/marker | Wpis sam nie powinien mieć efektu; wskazuje podklasę, styl albo grupę dalszych opcji. |
| 🧪 | Brak testu behawioralnego odwołującego się bezpośrednio do tego czaru/efektu. |

## Wynik ogólny

| Obszar | Pokrycie katalogu | Wynik audytu semantycznego |
|---|---:|---|
| Rasy | 9/9 | Rdzeń jest grywalny; `Tinker` jest świadomie stołowy, a część cech zależy od tagów sceny. |
| Klasy/podklasy | 12/12 | Większość rdzenia walki działa, lecz istnieją uproszczenia czasu, widoczności, eksploracji i kilka niepełnych riderów. |
| Czary 0–2 | 127/127 | 17 ataków, 2 leczenia, 61 akcji bojowych i 47 flag eksploracyjnych. Komplet plików nie oznacza kompletu mechaniki. |
| Testy czarów | — | 65/127 identyfikatorów czarów nie występuje bezpośrednio w testach; obecny audyt sprawdza głównie schemat, nie rezultat każdego czaru. |
| Flankowanie | reguła opcjonalna | Geometria ostatniej sesji była poprawna, ale brakuje kontroli `incapacitated`, a UI błędnie pokazuje przewagę jako `+0`. |

### Najważniejsze wykryte problemy

| Priorytet | Problem | Skutek dla gracza |
|---|---|---|
| P0 | `Invisibility` ma `concentration: false`. | Czar nie kończy poprzedniej koncentracji i nie może zostać przerwany obrażeniami zgodnie z SRD. |
| P0 | `Gentle Repose` ma `concentration: true`, choć SRD jej nie wymaga. | Legalny czar bez koncentracji niepotrzebnie blokuje inne czary koncentracyjne. |
| P0 | Efekty `Feather Fall`, `Mirror Image`, `Sanctuary`, `Levitate`, `Silence`, `Enhance Ability`, `Expeditious Retreat`, `Jump`, `See Invisibility`, `Spider Climb`, `Pass without Trace` i części ochronnych czarów nie mają pełnego konsumenta zasad. | Czar można rzucić i zużyć slot, ale oczekiwany efekt nie wpływa albo wpływa tylko częściowo na grę. |
| P0 | Strefy `Darkness`, `Fog Cloud`, `Grease`, `Entangle`, `Web`, `Silence`, `Spike Growth`, `Flaming Sphere` i `Moonbeam` nie mają spójnego kontraktu punkt/obszar/ruch strefy. | UI często wybiera aktora zamiast pola; puste pole i wejście w strefę nie działają jak w SRD. |
| P0 | `Vicious Mockery` nie nakłada utrudnienia do następnego ataku. | Sztuczka zadaje tylko obrażenia, tracąc główny rider. |
| P1 | `Acid Splash` nie obsługuje opcjonalnego drugiego celu w odległości 5 stóp od pierwszego. | Czar jest słabszy niż w SRD. |
| P1 | `Produce Flame` nie tworzy utrzymywanego źródła światła, a `Shatter` i `Fire Bolt` mają niepełną obsługę obiektów. | Brakuje zastosowań eksploracyjnych i interakcji z otoczeniem. |
| P1 | Minuty i godziny są mapowane na granice `encounter`, `short_rest` lub `scenario`. | Efekty mogą skończyć się za wcześnie albo trwać za długo między scenami. |
| P1 | `Sleep` budzi po obrażeniach, lecz brak ogólnej akcji sojusznika „obudź”; czas jest mapowany na encounter. | Jedna z dwóch standardowych metod pobudki nie ma własnej akcji. |
| P1 | Pomoc klasowa w kreatorze obejmuje głównie cechy poziomu 1. | Gracz po awansie nie dostaje równie pełnego wyjaśnienia cech poziomu 2–3. |

## Flankowanie — rekonstrukcja ostatniej sesji

W `data/session_observations/exploration_ui_dee7ac6aa2.jsonl`:

| Aktor | Pozycja |
|---|---|
| Pim | `(11, 6)` |
| Goblin przy rumowisku | `(10, 6)` |
| Nimra | `(9, 6)` |

Pim i Nimra stali dokładnie po przeciwnych stronach jednopolowego goblina.
`flanking_ally_ids=["nimra"]` było więc geometrycznie poprawne. Wynik ataku
poprosił o `2d20 z przewagą`, co również odpowiada włączonej opcjonalnej regule
flankowania. Dwie rzeczy były jednak nieprawidłowe:

| Kontrola | Obecnie | Oczekiwane |
|---|---|---|
| Prezentacja | `Flankowanie +0` w liście modyfikatorów. | `Flankowanie — przewaga`; bez sugerowania premii liczbowej. |
| Zdolność sojusznika do flankowania | Sprawdzane: frakcja, życie, sąsiedztwo, przeciwna strona i LOS. | Dodatkowo sojusznik nie może być `incapacitated`; docelowo powinien też realnie zagrażać celowi. |
| Nakładanie przewag | Jedna przewaga, niezależnie od liczby źródeł. | To jest zgodne z D&D 5e; flankowanie nie dodaje trzeciej kości ani `+X`. |
| Duże istoty | Każdy aktor zajmuje jedno pole. | Znana adaptacja projektu; pełna geometria rozmiaru wymaga footprintów. |

Wniosek: ostatnia flanka nie była policzona po złej stronie. Problem był przede
wszystkim komunikacyjny, a evaluator ma dodatkową lukę dla obezwładnionego
sojusznika.

## Czary — poziom 0

| Czar | Status | Efekt w grze i przykład użycia | Uwaga zgodności |
|---|---|---|---|
| Acid Splash / Kwasowy rozprysk | 🟠 | Cel na planszy wykonuje Dex save; porażka zadaje 1k6 kwasu. Przykład: rozprysk w goblina za barykadą. | Brak opcjonalnego drugiego celu stojącego do 5 ft od pierwszego. |
| Chill Touch / Dotyk chłodu | ✅ | Ranged spell attack, 1k8 necrotic i zakaz leczenia do początku następnej tury rzucającego. | Rider jest reprezentowany stanem `no_healing`. |
| Dancing Lights / Tańczące światła | 🟡 🧪 | Ustawia flagę użycia światła dla sceny. Przykład: wysłanie świateł w ciemny korytarz. | Brak czterech ruchomych źródeł na planszy i bonus-action przesuwania. |
| Druidcraft / Druidztwo | 🟡 | Flaga sceny pozwala rozstrzygnąć drobny efekt natury. Przykład: przewidzenie pogody albo zapalenie świecy. | Właściwa adaptacja narracyjna, ale wymaga authored reakcji sceny. |
| Eldritch Blast / Niesamowity podmuch | ✅ | Ranged spell attack za 1k10 force; na tym poziomie jeden promień. | Agonizing/Repelling Blast są dokładane przez cechy czarnoksiężnika. |
| Fire Bolt / Ognisty pocisk | 🟠 | Ranged spell attack za 1k10 fire. Przykład: strzał w goblina. | Zapalenie nieprzymocowanego, łatwopalnego obiektu pozostaje riderem stołowym. |
| Guidance / Wskazówki | 🔴 | Tworzy efekt `guidance_roll_bonus`. Przykład zamierzony: k4 do jednego testu cechy. | Brak ogólnego konsumenta tego efektu w testach cech; slot nie jest problemem, rezultat jest. |
| Light / Światło | 🟡 | Flaga sceny uruchamia źródło światła w przygotowanych interakcjach. | Brak uniwersalnego, przenośnego zaczarowanego obiektu po dotknięciu. |
| Mage Hand / Dłoń maga | 🟡 | Flaga/capability dla zdalnej manipulacji w scenie. Przykład: pociągnięcie dźwigni. | Limit 30 ft, ciężar 10 lb i zakazy są zależne od authored celu. |
| Mending / Naprawa | 🟡 🧪 | Flaga naprawy obiektu. Przykład: sklejenie pękniętego bukłaka. | Jednominutowy cast i ograniczenia uszkodzenia nie mają uniwersalnego resolvera. |
| Message / Wiadomość | 🟡 | Flaga komunikacji w scenie. Przykład: szept do sojusznika za drzwiami. | Droga dźwięku i blokujące materiały nie są obliczane uniwersalnie. |
| Minor Illusion / Pomniejsza iluzja | 🟡 | Flaga iluzji dla authored interakcji/LLM. Przykład: odgłos kroków za strażnikiem. | Brak trwałego obiektu iluzji, testu Investigation i rozpoznania fizyczną interakcją. |
| Poison Spray / Trujący rozprysk | ✅ 🧪 | Cel w zasięgu wykonuje Con save; porażka zadaje 1k12 poison. | Prosty resolver odpowiada SRD. |
| Prestidigitation / Kuglarstwo | 🟡 🧪 | Flaga drobnej magii użytkowej. Przykład: zmiana smaku piwa lub oczyszczenie ubrania. | Celowo sceniczne; limity jednoczesnych efektów nie są śledzone. |
| Produce Flame / Stworzenie płomienia | 🟠 🧪 | Można wykonać ranged spell attack za 1k8 fire. | Brak trzymanego źródła światła i decyzji „świeć albo rzuć”. |
| Ray of Frost / Promień mrozu | ✅ | Ranged spell attack za 1k8 cold i redukcja szybkości o 10 ft do następnej tury. | Rider ma stan i wpływa na ruch. |
| Resistance / Odporność | ✅ | Cel może dodać fizyczne k4 do jednego save podczas koncentracji. | UI ma ścieżkę zużycia efektu. |
| Sacred Flame / Święty płomień | ✅ | Dex save bez korzyści z cover; porażka zadaje 1k8 radiant. | Należy utrzymać wyjątek ignorowania cover w testach regresji. |
| Shillelagh / Kostur | ✅ | Pałka/kostur używa cechy czarowania, k8 i staje się magiczny. | Działa jako modyfikacja źródła broni. |
| Shocking Grasp / Porażający dotyk | ✅ | Melee spell attack, przewaga przeciw metalowemu pancerzowi, trafiony traci reakcje. | Rider i warunek pancerza są wykonywalne. |
| Spare the Dying / Oszczędź umierającego | ✅ | Dotknięty żywy cel z 0 PW zostaje ustabilizowany przez wybór figurki. | Nie działa na konstrukty i nieumarłych. |
| Thaumaturgy / Taumaturgia | 🟡 | Flaga scenicznego cudu. Przykład: wzmocnienie głosu przy zastraszaniu. | Efekt zależy od opisu/sceny; brak śledzenia trzech efektów przez minutę. |
| True Strike / Prawdziwe uderzenie | ✅ 🧪 | Koncentracja; w następnej turze pierwsza próba ataku przeciw wskazanemu celowi ma przewagę. | Efekt jest zużywany przez następny atak. |
| Vicious Mockery / Zjadliwa kpina | 🔴 | Wis save i 1k4 psychic. Przykład: bard obraża goblina. | Brak utrudnienia do następnego ataku celu — istotna część czaru nie działa. |

## Czary — poziom 1

| Czar | Status | Efekt w grze i przykład użycia | Uwaga zgodności |
|---|---|---|---|
| Alarm | 🟡 | Ustawia flagę chronionego obszaru. Przykład: alarm przy wejściu do obozu. | Brak uniwersalnej strefy 20 ft, whitelisty istot i automatycznego triggera przez 8 h. |
| Animal Friendship | 🟡 | Flaga celu dla sceny z bestią. Przykład: uspokojenie psa strażniczego. | Save, Int < 4, czas 24 h i reakcja bestii wymagają authored sceny/LLM. |
| Bane | ✅ | Do 3 celów: Cha save; porażka odejmuje fizyczne k4 od ataków i save podczas koncentracji. | Efekt jest konsumowany także w turze wroga. |
| Bless | ✅ | Do 3 celów dodaje fizyczne k4 do ataków i save podczas koncentracji. | Upcast liczby celów jest modelowany. |
| Burning Hands | ✅ | Wybór kierunku na planszy, stożek 15 ft, Dex save, 3k6/połowa. | Obszar i friendly fire są widoczne. |
| Charm Person | 🟡 | Flaga zauroczenia humanoida w scenie. Przykład: próba udobruchania strażnika. | Przewaga save w walce, godzina i późniejsza świadomość celu nie są uniwersalnym stanem. |
| Color Spray | 🔴 🧪 | Pula 6k10 ma oślepiać najsłabsze cele. | Brak stożka w danych obszaru; obecne celowanie może objąć aktorów w zasięgu zamiast w stożku. |
| Command | 🟡 | Wariant `Halt`: Wis save, porażka odbiera akcje do następnej tury. | Grywalna, jawna adaptacja; pozostałe rozkazy SRD nie są dostępne. |
| Comprehend Languages | 🟡 | Flaga rozumienia dosłownego znaczenia języka. | Brak uniwersalnego warunku dotykania pisma i tempa jednej strony/minutę. |
| Create or Destroy Water | 🟡 🧪 | Flaga stworzenia/zniszczenia wody lub deszczu. | Ilość, pojemnik i usuwanie mgły są egzekwowane tylko przez scenę. |
| Cure Wounds | ✅ | Dotknięty sojusznik odzyskuje 1k8 + cecha rzucania; skaluje się slotem. | Konstrukty i nieumarli wykluczeni. |
| Detect Evil and Good | 🟡 🧪 | Flaga wykrywania typów istot i miejsc w 30 ft. | Brak automatycznego skanu pozycji, blokad i poświęconych/sprofanowanych miejsc. |
| Detect Magic | 🟡 🧪 | Flaga wykrywania magii i aury. | Koncentracja jest w danych, ale wynik zależy od sceny. |
| Detect Poison and Disease | 🟡 🧪 | Flaga wykrywania trucizn i chorób. | Brak uniwersalnego skanu oraz identyfikacji typu. |
| Disguise Self | 🟡 🧪 | Flaga przebrania dla rozmów i eksploracji. | Investigation przeciw ST oraz fizyczna interakcja zależą od sceny. |
| Divine Favor | ✅ 🧪 | Podczas koncentracji trafienia bronią dodają 1k4 radiant. | Efekt jest dokładany jako osobny komponent obrażeń. |
| Entangle | 🔴 | Nakłada Restrained po Str save. | Brak faktycznej strefy 20-ft square i utrzymywanego difficult terrain; wybór aktorów zastępuje obszar. |
| Expeditious Retreat | 🔴 🧪 | Po rzuceniu zapisuje `bonus_action_dash`. | Brak konsumenta udostępniającego Dash bonus action w kolejnych turach. |
| Faerie Fire | ✅ | Wybór obszaru na planszy; Dex save, świecenie, brak korzyści z niewidzialności i przewaga ataków. | Sześcian jest przybliżony do pól siatki; warto doprecyzować kotwicę narożnika. |
| False Life | ✅ 🧪 | Rzut k4+4 daje tymczasowe PW; wyższy slot +5. | Rdzeń efektu działa; czas godziny jest mapowany do granicy odpoczynku. |
| Feather Fall | 🔴 🧪 | Można utworzyć znacznik ochrony do 5 celów. | Brak reakcyjnego triggera na upadek, prędkości opadania i automatycznego anulowania obrażeń. |
| Find Familiar | 🟡 | Flaga przywołania chowańca. Przykład: wysłanie sowy na zwiad. | Brak pełnego aktora, form, telepatii, dismiss/resummon i dostarczania czarów dotykowych. |
| Floating Disk | 🟡 🧪 | Flaga dysku transportowego. | Nośność, podążanie 20 ft, przeszkody i limit 100 ft nie są wykonywane. |
| Fog Cloud | 🟠 🧪 | Efekt `obscuring_zone` wpływa na ataki. | Brak wyboru dowolnego środka pustego pola i trwałego wizualnego obszaru; kotwiczenie przy aktorze zniekształca czar. |
| Goodberry | 🟡 🧪 | Flaga stworzenia 10 jagód. | Nie tworzy 10 rzeczywistych, 24-godzinnych przedmiotów z akcją leczenia 1 PW. |
| Grease | 🔴 🧪 | Może nałożyć Prone po Dex save. | Brak kwadratu 10 ft, difficult terrain i ponawiania save przy wejściu/końcu tury. |
| Guiding Bolt | ✅ | Ranged spell attack 4k6 radiant; następny atak przeciw celowi ma przewagę. | Znacznik znika po następnym ataku. |
| Healing Word | ✅ | Bonus action, 60 ft, 1k4 + cecha rzucania; skaluje się slotem. | Cele wskazywane przez planszę. |
| Hellish Rebuke | ✅ | Reakcja po obrażeniach; Dex save, 2k10 fire/połowa. | Reakcyjne okno i upcast są modelowane. |
| Heroism | ✅ | Odporność na Frightened i odnawiane temp PW na początku tury. | Efekt działa w pętli tury; czas jest encounter zamiast dokładnej minuty. |
| Hideous Laughter | ✅ 🧪 | Wis save; Prone + Incapacitated, powtórki save po obrażeniu i na końcu tury. | Wymaga testu całej ścieżki UI; rdzeń warunku jest obecny. |
| Hunter's Mark | 🟠 🧪 | Oznaczony cel otrzymuje dodatkowe 1k6 od trafień bronią rzucającego. | Przeniesienie znaku po 0 PW i przewaga Perception/Survival nie mają pełnego flow. |
| Identify | 🟡 | Flaga identyfikacji przedmiotu. | W przygotowanej scenie może ujawnić authored dane; brak uniwersalnego wyboru i pełnego raportu przedmiotu. |
| Illusory Script | 🟡 | Flaga magicznego pisma. | Odbiorcy, 10 dni i True Seeing nie są śledzone. |
| Inflict Wounds | ✅ | Melee spell attack za 3k10 necrotic; skaluje się slotem. | Prosty resolver zgodny. |
| Jump | 🔴 🧪 | Zapisuje efekt `jump_multiplier`. | Kalkulator skoku nie konsumuje tego efektu. |
| Longstrider | 🟠 🧪 | Efekt `speed_bonus` zwiększa szybkość. | Wymaga weryfikacji konsumenta dla aktywnego efektu; czas 1 h mapowany jest do short rest. |
| Mage Armor | ✅ | Bazowe KP 13 + Dex dla nieopancerzonego celu. | Warunek pancerza i AC są egzekwowane; czas jest uproszczony. |
| Magic Missile | ✅ | Gracz wskazuje na planszy cele dla trzech pocisków i rozdziela je; każdy 1k4+1 force. | Upcast dodaje pociski; brak ataku/save jest poprawny. |
| Protection from Evil and Good | 🔴 🧪 | Tworzy nazwany efekt ochrony. | Brak pełnego konsumenta: utrudnienie ataków typów oraz odporność/wyjście z charm, frighten i possession. |
| Purify Food and Drink | 🟡 🧪 | Flaga oczyszczenia żywności. | Działa w authored scenie, bez uniwersalnego zaznaczania wszystkich zasobów w 5 ft. |
| Sanctuary | 🔴 🧪 | Tworzy efekt `sanctuary`. | Atakujący nie otrzymuje wymaganego Wis save, nie wybiera nowego celu, a ofensywna akcja nie kończy efektu. |
| Shield | ✅ | Reakcja po trafieniu daje +5 KP do początku następnej tury i ponownie ocenia atak. | Magic Missile powinien być również blokowany — wymaga utrzymania osobnego testu. |
| Shield of Faith | ✅ | +2 KP wskazanego celu podczas koncentracji. | Efekt jest używany przez kalkulator AC. |
| Silent Image | 🟡 🧪 | Flaga iluzji dla sceny/LLM. | Brak obiektu 15-ft cube, przesuwania akcją i deterministycznego Investigation. |
| Sleep | 🟠 | Wybór środka i obszaru; pula 5k8 od najniższych PW, undead i magic-sleep immunity wykluczone. | Brak ogólnej akcji obudzenia; dokładna minuta jest zastąpiona encounter. |
| Speak with Animals | 🟡 🧪 | Flaga komunikacji z bestiami. | Odpowiedzi i zakres wiedzy bestii zależą od NPC/sceny. |
| Thunderwave | ✅ 🧪 | Sześcian 15 ft od rzucającego, Con save, 2k8/połowa, porażka odpycha 10 ft. | Plansza pokazuje obszar i wymaga legalnego pola docelowego odepchnięcia. |
| Unseen Servant | 🟡 🧪 | Flaga niewidzialnego sługi. | Brak tokena z KP/PW, bonus-action poleceń, zasięgu 60 ft i poruszania 15 ft. |

## Czary — poziom 2

| Czar | Status | Efekt w grze i przykład użycia | Uwaga zgodności |
|---|---|---|---|
| Acid Arrow | ✅ 🧪 | Ranged spell attack: 4k4 acid, kolejne 2k4; pudło połowę pierwszych obrażeń. | Wymaga testu timingu końca następnej tury celu. |
| Aid | ✅ | Do 3 celów: +5 aktualnych i maksymalnych PW; upcast +5. | Czas do long rest jest rozsądną adaptacją 8 h. |
| Alter Self | 🟡 🧪 | Flaga wybranego wariantu: wodny, broń naturalna lub wygląd. | Żaden wariant nie ma pełnego uniwersalnego resolvera walki/eksploracji. |
| Animal Messenger | 🟡 🧪 | Flaga Tiny beast, odbiorcy i wiadomości. | Podróż, dystans dzienny i dostarczenie nie są symulowane. |
| Arcane Lock | 🟡 | Flaga blokady obiektu i hasła. | Działa tylko, jeśli authored fixture respektuje flagę i +10 ST. |
| Arcanist's Magic Aura | 🟡 🧪 | Flaga fałszywej aury/typu. | Efekt ma znaczenie tylko dla przygotowanych detektorów. |
| Augury | 🟡 🧪 | Flaga pytania do MG/LLM. | Omen i kumulatywna szansa losowej odpowiedzi przy kolejnych castach nie są deterministycznie prowadzone. |
| Barkskin | ✅ 🧪 | KP celu nie spada poniżej 16 podczas koncentracji. | Konsument AC istnieje. |
| Blindness/Deafness | ✅ 🧪 | Con save, wybrany stan, ponowny save na końcu tury. | Board target działa; potrzeba testu obu wariantów i repeated save. |
| Blur | 🟠 🧪 | Ataki przeciw celowi mają utrudnienie. | Wyjątek dla blindsight/truesight i napastników niewidzących celu nie jest pełny. |
| Branding Smite | 🟠 🧪 | Następne trafienie bronią dodaje radiant i znacznik świecenia. | Kod ogranicza rider do melee weapon, podczas gdy SRD dopuszcza weapon attack; kończenie niewidzialności wymaga pełnego testu. |
| Calm Emotions | 🟡 🧪 | Flaga stłumienia emocji albo zawieszenia charm/frightened. | Brak obszaru, Cha save i wyboru efektu jako deterministycznego stanu. |
| Continual Flame | 🟡 | Flaga stałego światła na obiekcie. | Brak trwałej instancji zaczarowanego przedmiotu oraz interakcji z Darkness/Dispel. |
| Darkness | 🟠 | `obscuring_zone` wpływa na ataki. | Brak wyboru dowolnego punktu/obiektu i trwałej strefy; zwykłe darkvision jest uproszczone. |
| Darkvision | ✅ | Cel otrzymuje darkvision 60 ft. | Zmysł jest konsumowany przez widoczność; czas 8 h jest mapowany do odpoczynku. |
| Detect Thoughts | 🟡 🧪 | Flaga odczytu myśli w scenie. | Brak automatycznego sondowania, Wis save i contested Intelligence. |
| Enhance Ability | 🔴 🧪 | Tworzy `ability_check_advantage:<ability>`. | Brak ogólnego konsumenta przewagi i dodatkowych efektów sześciu wariantów. |
| Enlarge/Reduce | 🟠 🧪 | Enlarge dodaje 1k4 do obrażeń, zapisuje zmianę rozmiaru. | Reduce, niechętny Con save, masa, zasięg i geometria rozmiaru są niepełne. |
| Enthrall | 🟡 🧪 | Flaga rozproszenia uwagi. | Brak obszaru, wykluczeń, Wis save i filtrowanego utrudnienia Perception. |
| Find Steed | 🟡 🧪 | Flaga przywołanego wierzchowca. | Brak pełnego aktora, formy, inteligencji, więzi i współdzielenia czarów self. |
| Find Traps | 🟡 🧪 | Flaga zapytania o obecność zagrożeń. | Authored scena może odpowiedzieć; blokada LOS i „bez lokalizacji” muszą być pilnowane contentem. |
| Flame Blade | 🟠 🧪 | Tworzy dodatkowe 3k6 fire przy ataku melee. | Powinien tworzyć osobny melee spell attack, nie rider zwykłej broni. |
| Flaming Sphere | 🔴 🧪 | Nakłada okresowe 2k6 fire wskazanemu celowi. | Brak tokena kuli, pola startowego, końca tury w 5 ft, bonus-action ruchu i taranowania. |
| Gentle Repose | 🔴 🧪 | Flaga zabezpieczenia zwłok. | Błędnie oznaczony jako koncentracyjny; SRD nie wymaga koncentracji. |
| Gust of Wind | 🟠 🧪 | Linia i forced movement mają resolver. | Brak utrzymywanej kierunkowej strefy, podwójnego kosztu ruchu i bonusowej zmiany kierunku co turę. |
| Heat Metal | 🟠 🧪 | Okresowe obrażenia fire na celu. | Brak wyboru konkretnego metalowego obiektu, wymuszenia upuszczenia i utrudnienia, gdy nie może upuścić. |
| Hold Person | ✅ | Humanoid: Wis save, Paralyzed, powtórka na końcu tury; upcast dodaje cele. | Typ celu i repeated save są częścią kontraktu. |
| Invisibility | 🔴 | Ataki celu/na cel respektują niewidzialność i efekt może wygasać przy ofensywie. | Krytyczny błąd danych: `concentration: false`; opis sam mówi o koncentracji. |
| Knock | 🟡 | Flaga otwarcia blokady i hałasu. | Authored fixture musi obsłużyć otwarcie, tłumienie Arcane Lock i dźwięk 300 ft. |
| Lesser Restoration | ✅ | Dotknięty cel usuwa jedną chorobę albo Blinded/Deafened/Paralyzed/Poisoned. | Stany są wybierane i usuwane; choroby zależą od modelu sceny. |
| Levitate | 🔴 🧪 | Tworzy efekt `levitate`. | Brak wysokości, ograniczenia 500 lb, Con save dla wroga i reguł ruchu przez odpychanie. |
| Locate Animals or Plants | 🟡 🧪 | Flaga wyszukiwanego gatunku. | Kierunek/dystans do 5 mil zależy od danych świata, których runtime nie indeksuje. |
| Locate Object | 🟡 🧪 | Flaga wyszukiwanego obiektu. | Brak indeksu 1000 ft, ruchomego kierunku i blokady ołowiem. |
| Magic Mouth | 🟡 | Flaga obiektu, wiadomości i wyzwalacza. | Brak trwałego triggera na dowolnym przedmiocie. |
| Magic Weapon | ✅ | Niemagiczna broń ma +1 do ataku/obrażeń i staje się magiczna. | Trzeba utrzymać wybór konkretnej broni; wyższe sloty poza zakresem postaci 3. poziomu. |
| Mirror Image | 🔴 | Tworzy licznik trzech duplikatów. | Ataki nie wykonują rzutu przekierowania i nie zużywają duplikatów. |
| Misty Step | ✅ | Bonus action teleportuje rzucającego na podświetlone wolne pole do 30 ft. | Teleport nie prowokuje OA. |
| Moonbeam | 🔴 🧪 | Okresowe obrażenia mogą zostać przypisane wskazanemu celowi. | Brak cylindra jako obiektu planszy, wejścia/startu tury, ruchu akcją i ridera dla shapechangerów. |
| Pass without Trace | 🔴 🧪 | Tworzy `stealth_bonus_aura`. | Brak konsumenta +10 do Stealth i dynamicznego aura range; ślady pozostają warstwą narracyjną. |
| Prayer of Healing | 🟡 🧪 | Flaga dziesięciominutowego leczenia. | Nie wykonuje deterministycznego wyboru do 6 celów, rzutu leczenia ani wydania slotu po long cast. |
| Protection from Poison | 🔴 🧪 | Tworzy nazwany efekt ochronny. | Neutralizacja trucizny, przewaga save i resistance nie mają pełnego konsumenta. |
| Ray of Enfeeblement | 🟠 🧪 | Trafienie zmniejsza o połowę obrażenia Strength weapon attacks. | Należy zweryfikować Con save na końcu każdej tury i zakończenie koncentracji. |
| Rope Trick | 🟡 🧪 | Flaga extradimensional space. | Brak wejścia/wyjścia, pojemności 8 Medium, czasu i reguły ataków/czarów przez portal. |
| Scorching Ray | ✅ | Trzy osobne ranged spell attacks; każdy 2k6 fire; cele przez planszę. | Upcast dodaje promień. |
| See Invisibility | 🔴 🧪 | Tworzy efekt `see_invisibility`. | Widoczność nie konsumuje go uniwersalnie; Ethereal Plane również nie jest modelowany. |
| Shatter | 🟠 🧪 | Wybór obszaru, Con save, 3k8 thunder/połowa. | Brak automatycznego utrudnienia dla nieorganicznych istot i obrażeń niemagicznym obiektom. |
| Silence | 🔴 🧪 | Tworzy `silence_zone`. | Brak realnej strefy, Deafened w obszarze i blokady czarów z komponentem werbalnym. |
| Spider Climb | 🔴 🧪 | Tworzy efekt `spider_climb`. | Pathfinding nie otrzymuje climb speed ani przejścia po ścianach/suficie. |
| Spike Growth | 🟠 🧪 | UI nalicza obrażenia przy ruchu dla efektu strefy. | Brak poprawnego wyboru i prezentacji obszaru oraz pełnej obsługi ukrycia strefy/Perception. |
| Spiritual Weapon | 🟠 | Przywołuje token z atakiem i ruchem. | Wymaga weryfikacji bonus-action ataku przy cast, ruchu 20 ft i braku koncentracji; model generic summon upraszcza zachowanie. |
| Suggestion | 🟡 🧪 | Flaga sugestii dla sceny/LLM. | Wis save, rozsądność polecenia, warunki zakończenia i 8 h nie są deterministycznie prowadzone. |
| Warding Bond | 🟠 🧪 | Cel otrzymuje +1 KP, a część defensywna jest widoczna kalkulatorowi. | Brak pełnego +1 do save, resistance i kopiowania każdej porcji obrażeń na rzucającego wraz z limitem 60 ft. |
| Web | 🔴 🧪 | Może nałożyć Restrained po Dex save. | Brak prawdziwego sześcianu, wejścia/startu tury, difficult terrain, lekkiego zasłonięcia, podpór i palności. |
| Zone of Truth | 🟡 🧪 | Flaga strefy prawdy dla rozmowy. | Brak 15-ft strefy, powtarzanego Cha save przy wejściu i listy wyników znanej rzucającemu. |

## Rasy

Warianty smoczego pochodzenia o tym samym typie obrażeń są zgrupowane, ponieważ
korzystają z tego samego resolvera kształtu, save i odporności.

| Rasa / cecha | Status | Efekt i przykład użycia | Uwaga |
|---|---|---|---|
| Człowiek — Human Versatility | ✅ | +1 do wszystkich sześciu cech i dodatkowy język są rozliczane w kreatorze. | Naprawia wcześniejszy brak premii człowieka. |
| Wysoki elf — Darkvision | ✅ | Widoczność do 60 ft w ciemności. | Silnik światła respektuje zmysł. |
| Wysoki elf — Fey Ancestry | ✅ | Przewaga przeciw charm i odporność na magiczny sen. | Używane także przez `Sleep`. |
| Wysoki elf — Trance | ✅ | Pełny odpoczynek po 4 h medytacji. | Adaptacja zakłada równoważność odpoczynku bez osobnego czuwania. |
| Wysoki elf — Elf Weapon Training | ✅ | Biegłości broni są zapisane i wpływają na ataki. | Efekt kreatora. |
| Wysoki elf — High Elf Cantrip | ✅ | Wybrana sztuczka czarodzieja używa Inteligencji. | Profil źródła zachowuje cechę rzucania. |
| Krasnolud wzgórzowy — Darkvision | ✅ | Widoczność do 60 ft. | — |
| Krasnolud — Dwarven Resilience | ✅ | Przewaga przeciw poison i resistance poison damage. | Obie części mają osobne hooki. |
| Krasnolud — Dwarven Speed | ✅ | Ciężki pancerz nie obniża szybkości przez brak Siły. | Kara innego pochodzenia nadal może działać. |
| Krasnolud — Stonecunning | 🟡 | Podwójna biegłość w History dla oznaczonych testów kamienia. | Wymaga poprawnego tagu scenariusza. |
| Krasnolud wzgórzowy — Dwarven Toughness | ✅ | +1 maks. PW za każdy poziom. | Uwzględniane przy awansie. |
| Niziołek lekkostopy — Lucky | ✅ | Naturalne 1 prosi o przerzut fizycznej k20. | Należy utrzymać we wszystkich trzech typach d20. |
| Niziołek — Brave | ✅ | Przewaga przeciw Frightened. | — |
| Niziołek — Halfling Nimbleness | ✅ | Może przechodzić przez pole większej istoty, bez kończenia tam ruchu. | Projekt traktuje to pole jako difficult terrain — jawna adaptacja. |
| Niziołek lekkostopy — Naturally Stealthy | ✅ | Większa istota może zapewnić warunek Hide. | Zależne od LOS i rozmiaru. |
| Smocze dziecię — Breath Weapon | ✅ | Akcja, linia/stożek na LED, save Con/Dex, 2k6 i połowa przy sukcesie. | Zasób odpoczynku działa. |
| Smocze dziecię — ancestry acid/lightning/fire/cold/poison | ✅ | Genealogia ustawia typ, kształt, save i damage resistance. | Warianty korzystają ze wspólnego resolvera. |
| Gnom skalny — Darkvision | ✅ | Widoczność do 60 ft. | — |
| Gnom — Gnome Cunning | ✅ | Przewaga w Int/Wis/Cha save przeciw magii. | Efekt wymaga poprawnego tagu „magical”. |
| Gnom skalny — Artificer's Lore | 🟡 | Podwójna biegłość w oznaczonych testach historii magicznych/alchemicznych/technicznych przedmiotów. | Zależne od tagów sceny. |
| Gnom skalny — Tinker | 🟡 | Cecha i rekwizyty są zapisane; gracz może opisać użycie. | Świadomie stołowe, brak uniwersalnej mechaniki trzech urządzeń. |
| Półelf — Darkvision/Fey Ancestry | ✅ | Jak u elfa. | — |
| Półelf — Skill Versatility | ✅ | Dwie wybrane biegłości są dodawane w kreatorze. | — |
| Półork — Darkvision | ✅ | Widoczność do 60 ft. | — |
| Półork — Relentless Endurance | ✅ | Raz na long rest spadek do 0 PW zmienia się na 1 PW, z wyjątkami instant death. | Automatyczny trigger. |
| Półork — Savage Attacks | ✅ | Krytyk broni dodaje jedną dodatkową kość obrażeń broni. | Nie powinien podwajać dodatkowych kości cech/czarów. |
| Diabelstwo — Darkvision | ✅ | Widoczność do 60 ft. | — |
| Diabelstwo — Hellish Resistance | ✅ | Resistance fire. | — |
| Diabelstwo — Infernal Legacy | ✅ | Thaumaturgy na 1., Hellish Rebuke raz/long rest od 3. poziomu. | Cechą rzucania jest Charyzma. |

## Klasy i podklasy do 3. poziomu

Wiersze „wybór” są poprawnymi markerami, jeśli ich konkretne opcje są później
przyznawane i wykonywane.

| Klasa / cecha | Status | Efekt i przykład użycia | Uwaga |
|---|---|---|---|
| Barbarzyńca — Rage | ✅ | Bonus action; przewaga Strength, bonus melee Strength damage, resistance B/P/S. | Silnik śledzi zużycie i warunki utrzymania. |
| Barbarzyńca — Unarmored Defense (Con) | ✅ | KP 10 + Dex + Con, tarcza dozwolona. | Kalkulator wybiera legalnie najlepsze KP. |
| Barbarzyńca — Reckless Attack | ✅ | Pierwszy Strength melee attack może dostać przewagę; ataki przeciw barbarzyńcy mają przewagę do następnej tury. | Deklaracja jest osobną akcją UI przed atakiem. |
| Barbarzyńca — Danger Sense | 🟠 | Przewaga w widocznych Dex saves. | Wymaga pełnego testu wykluczeń blinded/deafened/incapacitated. |
| Berserker — Frenzy | ✅ | W rage udostępnia bonusowy melee attack; po rage dodaje exhaustion. | Nie mylić aktywacji frenzy z samym rage. |
| Bard — Spellcasting | ✅ | Znane czary, sloty i Charisma. | Zastrzeżenia poszczególnych czarów są w tabeli wyżej. |
| Bard — Bardic Inspiration | 🟠 | Bonus action, cel na planszy, k6 do ability check/attack/save. | W walce trwa do końca encounter zamiast dokładnych 10 min; trzeba potwierdzić pełne zużycie w eksploracji. |
| Bard — Jack of All Trades | ✅ | Połowa proficiency do niebiegłych ability checks. | Powinno obejmować initiative jako Dex check. |
| Bard — Song of Rest | ✅ | Dodatkowe k6 leczenia przy short rest, gdy wydano Hit Die. | — |
| College of Lore — Bonus Proficiencies | ✅ | Trzy biegłości wybrane w kreatorze/awansie. | — |
| College of Lore — Cutting Words | 🟠 | Reakcja przeciw attack roll działa. | Ability check i damage roll pozostają korektą stołową. |
| Kleryk — Spellcasting/Life Domain | ✅ | Prepared Wisdom casting i always-prepared domain spells. | — |
| Life — Disciple of Life | ✅ | +2 + poziom czaru do leczenia leveled spell. | Nakładane na źródło leczenia. |
| Kleryk — Channel Divinity / Turn Undead | ✅ | Akcja, Wis save widocznych undead w 30 ft, stan odpędzenia. | Widoczność i zachowanie na turze muszą pozostać w testach. |
| Life — Preserve Life | ✅ | Rozdziela 5 × poziom kleryka PW, maks. do połowy PW celu; bez undead/construct. | Cele i przydział przez planszę/UI. |
| Druid — Druidic | 🟡 | Sekretny język jako permission sceny. | Świadomie stołowe. |
| Druid — Spellcasting | ✅ | Prepared Wisdom casting. | — |
| Druid — Wild Shape | ✅ | Wybór legalnej formy, statystyki bestii, PW formy, atak i powrót. | Dostępna lista form jest ograniczonym katalogiem; pełne SRD wymaga wszystkich legalnych bestii. |
| Circle of the Land — Bonus Cantrip | ✅ | Dodatkowa sztuczka druida. | — |
| Circle of the Land — Natural Recovery | ✅ | Po short rest odzyskuje legalną sumę poziomów slotów raz/dzień. | — |
| Circle Land terrain choices | ✅ | Wybrany teren przyznaje właściwe always-prepared circle spells od poziomu 3. | Osiem opcji jest data-driven. |
| Wojownik — Fighting Style | ⚪ | Wybór stylu w kreatorze. | Konkretne style poniżej. |
| Archery | ✅ | +2 do ranged weapon attacks. | Nie do ranged spell attacks. |
| Defense | ✅ | +1 KP podczas noszenia pancerza. | — |
| Dueling | ✅ | +2 damage przy jednej broni jednoręcznej i bez innej broni. | Tarcza jest dozwolona. |
| Two-Weapon Fighting | ✅ | Ability modifier do damage bonusowego ataku drugą bronią. | — |
| Wojownik — Second Wind | ✅ | Bonus action, 1k10 + fighter level, short-rest resource. | Fizyczny k10. |
| Wojownik — Action Surge | ✅ | Odzyskuje dodatkową akcję raz/short rest. | Nie dodaje bonus action. |
| Champion — Improved Critical | ✅ | Krytyk na 19–20. | — |
| Mnich — Unarmored Defense (Wis) | ✅ | KP 10 + Dex + Wis bez pancerza i tarczy. | — |
| Mnich — Martial Arts | ✅ | Dex dla monk weapons/unarmed, k4, bonus unarmed po Attack. | Wymaga legalnego wyposażenia i braku pancerza/tarczy. |
| Mnich — Ki: Flurry/Patient Defense/Step of the Wind | ✅ | Trzy akcje bonusowe wydają 1 Ki i uruchamiają właściwy efekt. | Step of the Wind powinien także podwajać jump distance. |
| Mnich — Unarmored Movement +10 | ✅ | Zwiększa szybkość bez pancerza/tarczy. | — |
| Mnich — Deflect Missiles | ✅ | Reakcja redukuje ranged weapon damage; przy redukcji do 0 może wydać Ki i odrzucić pocisk. | Target odrzutu powinien zawsze iść przez planszę. |
| Open Hand Technique | ✅ | Po trafieniu Flurry: prone, push 15 ft albo brak reakcji. | Push i cel przez planszę; save DC z Ki. |
| Paladyn — Divine Sense | 🟠 | Akcja wykrywa typy celestial/fiend/undead do 60 ft. | Brak pełnej kontroli total cover oraz consecrated/desecrated place. |
| Paladyn — Lay on Hands | 🟠 | Dotyk i wydawanie puli leczenia działa. | Interfejs opisuje leczenie; neutralizacja poison/disease za 5 punktów wymaga osobnej, dobrze widocznej ścieżki. |
| Paladyn — Fighting Style/Spellcasting | ✅ | Style i prepared Charisma casting od poziomu 2. | — |
| Paladyn — Divine Smite | ✅ | Po melee weapon hit można wydać slot na radiant dice; więcej przeciw undead/fiend. | Nie zużywa akcji. |
| Paladyn — Divine Health | ✅ | Odporność na disease. | Zależne od prawidłowego tagu efektu jako disease. |
| Devotion — Sacred Weapon | 🟠 | Akcja dodaje Cha do ataku konkretnej broni. | Czas jest encounter zamiast 1 min; brak emisji światła. |
| Devotion — Turn the Unholy | ✅ | Jak Turn Undead dla fiend/undead. | — |
| Łowca — Favored Enemy | 🟡 | Przewaga do oznaczonych Survival/Intelligence checks; humanoid wybiera dwie rasy. | Wymaga `creature_type` i `race_tag` w contentcie. |
| Łowca — Natural Explorer | 🟡 | Korzyści podróży na wybranym terenie. | Działa tylko dla prawidłowo otagowanych podróży; pełny pakiet śledzenia/foraging wymaga contentu. |
| Łowca — Fighting Style/Spellcasting | ✅ | Styl i known Wisdom spells od poziomu 2. | — |
| Łowca — Primeval Awareness | 🟠 | Wydaje slot i ujawnia obecność odpowiednich typów. | Obecny zakres jest związany z uczestnikami encounter; SRD mówi 1 milę/6 mil w favored terrain i bez liczby/lokalizacji. |
| Hunter — Colossus Slayer | ✅ | Raz na turę +1k8, gdy cel ma mniej niż maks. PW. | Automatyczny rider po trafieniu. |
| Hunter — Giant Killer | 🟠 | Reakcyjny atak na Large+ po ataku celu. | Wymaga pełnego, czytelnego okna reakcji i zasięgu 5 ft. |
| Hunter — Horde Breaker | 🟠 | Drugi atak na inny cel do 5 ft od pierwszego raz/turę. | Wymaga podświetlenia tylko legalnych drugich celów. |
| Łotrzyk — Expertise | ✅ | Dwie biegłości mają podwójne proficiency. | — |
| Łotrzyk — Sneak Attack 1k6/2k6 | ✅ | Raz/turę po legalnym finesse/ranged hit z przewagą lub sąsiadującym sojusznikiem. | Flankowanie może dać przewagę, ale nie jest warunkiem samym w sobie. |
| Łotrzyk — Thieves' Cant | 🟡 | Język/permission sceny. | Świadomie stołowe. |
| Łotrzyk — Cunning Action | ✅ | Bonus action Dash/Disengage/Hide. | Hide tylko przy legalnej widoczności. |
| Thief — Fast Hands | 🟠 | Bonus action dla interakcji/użycia obiektu. | Pełny wybór Sleight of Hand, thieves' tools i Use an Object wymaga konsekwentnego menu; nie może automatycznie obejmować magic items. |
| Thief — Second-Story Work | ✅ | Szybsze wspinanie i dłuższy running jump. | Bonus skoku opiera się na Dex modifier zgodnie z SRD. |
| Czarownik — Spellcasting/Draconic Resilience | ✅ | Charisma casting; bez pancerza KP 13+Dex i +1 PW/poziom. | — |
| Czarownik — Font of Magic | ✅ | Bonus action konwertuje sloty i Sorcery Points według tabeli. | — |
| Metamagic — Careful | ✅ | Wskazane cele automatycznie zdają pierwszy save obszaru. | Cel przez planszę. |
| Metamagic — Distant | ✅ | Podwaja range albo zmienia touch na 30 ft. | — |
| Metamagic — Empowered | ✅ | Przerzut do Cha modifier kości obrażeń. | Może łączyć się z inną metamagic. |
| Metamagic — Extended | 🟠 | Zapisuje mnożnik czasu ×2. | Uproszczony zegar encounter/rest może uniemożliwić odczuwalny efekt. |
| Metamagic — Heightened | ✅ | Wybrany cel ma utrudnienie do pierwszego save. | Cel przez planszę. |
| Metamagic — Quickened | ✅ | Zmienia action na bonus action i respektuje bonus-action spell rule. | — |
| Metamagic — Subtle | 🟠 | Legalność castu bez V/S jest zapisana. | Komponenty V/S nie są jeszcze konsekwentnie blokowane przez Silence/restrained hands. |
| Metamagic — Twinned | ✅ | Drugi legalny cel pojedynczego czaru, wskazany przez planszę. | Waliduje brak self/area/multi-target. |
| Czarnoksiężnik — Pact Magic | ✅ | Osobne sloty najwyższego poziomu odnawiane po short rest. | — |
| Fiend — Dark One's Blessing | ✅ | Po pokonaniu wroga temp PW = Cha mod + warlock level. | Automatyczny trigger. |
| Invocations — Agonizing/Repelling Blast | ✅ | Cha do obrażeń Eldritch Blast; trafiony może zostać odepchnięty 10 ft. | Cel/droga odepchnięcia przez planszę. |
| Invocations — Armor of Shadows, Beast Speech, Eldritch Sight, Fiendish Vigor, Mask of Many Faces, Misty Visions | 🟠 | Przyznają at-will spell access. | Ostateczna zgodność zależy od niepełnych resolverów odpowiadających im czarów. |
| Invocation — Beguiling Influence | ✅ | Biegłość Deception i Persuasion. | Efekt kreatora. |
| Invocation — Devil's Sight | ✅ | Widzenie także w magicznej ciemności do 120 ft. | Musi współpracować z poprawioną strefą Darkness. |
| Pact of the Blade | ✅ | Przywołanie wybranej pact weapon i biegłość. | Część rytualnego wiązania magicznej broni jest uproszczona. |
| Pact of the Chain | 🟡 | Przyznaje Find Familiar i znacznik specjalnego paktu. | Specjalne formy, telepatia/atak chowańca pozostają stołowe. |
| Pact of the Tome | ✅ | Trzy sztuczki dowolnych list używające Charisma. | — |
| Czarodziej — Spellcasting/Spellbook | ✅ | Intelligence, księga, prepared spells i rytuały. | Poszczególne rytuały mogą mieć tylko flagę sceny. |
| Czarodziej — Arcane Recovery | ✅ | Po short rest legalny wybór odzyskiwanych slotów raz/dzień. | — |
| Evocation — Savant | 🟡 | Metadane kosztu/czasu kopiowania evocation. | Aplikacja nie ma jeszcze pełnego ekonomicznego flow kopiowania czarów do księgi. |
| Evocation — Sculpt Spells | ✅ | Wybór do 1 + poziom czaru chronionych istot; save auto-success i zero damage. | Cele przez planszę. |

## Luki w obecnych audytach automatycznych

| Audyt | Co obecnie udowadnia | Czego nie udowadnia |
|---|---|---|
| `audit_srd_character_coverage` | Istnieją 9 ras, 12 klas/podklas i 127 canonical spell IDs na właściwych poziomach/listach. | Poprawności koncentracji, zasięgu, czasu, komponentów ani efektu. |
| `audit_character_implementation` | Każda cecha ma etykietę `executable/data_driven/marker/table_assisted`; każdy czar ma obsługiwany `effect.kind/action_type`. | Że `effect_kind` ma konsumenta albo że konsument realizuje opis. |
| `audit_assisted_spell_plans` | Nie zostały stare wpisy `kind=assisted`. | Czy zamiana `assisted` na `exploration:set_flag` lub `targeted_status` rzeczywiście dodała mechanikę. |
| Test kompilacji czarów | Każdy nieeksploracyjny czar kompiluje się do źródła akcji. | Że po użyciu źródła zmienia się właściwy stan i efekt wygasa w odpowiednim momencie. |

## Zalecany plan napraw

1. P0: poprawić błędne metadane koncentracji i dodać walidator zgodności
   `instructions ↔ concentration ↔ duration`.
2. P0: wprowadzić rejestr `effect_kind -> consumer` i sprawić, aby audyt odrzucał
   efekt bojowy bez wykonującego go resolvera.
3. P0: ujednolicić trwałe strefy czarów jako obiekty planszy z kotwicą,
   geometrią, triggerami wejście/start/koniec tury i możliwością przesuwania.
4. P0: domknąć wymienione efekty-marker (`Mirror Image`, `Sanctuary`,
   `Feather Fall`, `Levitate`, `Silence` itd.).
5. P1: dodać test behawioralny dla każdego z 127 czarów: cast, koszt, cel,
   rezultat, upcast i wygaśnięcie.
6. P1: rozszerzyć tooltipy/kartę awansu na wszystkie cechy poziomów 2–3.
7. P1: poprawić flankowanie: wykluczyć `incapacitated`, zmienić komunikat
   `+0` na `przewaga` i dodać test ostatniego układu `(9,6)-(10,6)-(11,6)`.

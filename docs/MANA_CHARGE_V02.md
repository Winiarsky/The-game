# Trwałe ładowanie many — wersja 2

## Naładowanie zamiast biegłości — aktualne testy

Bohaterowie z profilem osobistej many nie dodają biegłości ani ekspertyzy do
ataków, obron, umiejętności i narzędzi. Test: `k20 + cecha + naładowanie + inne
premie`. Progi punktów 0/6/12/21 dają +0/+2/+4/+6. W walce używasz aktualnej
premii swojej puli; w konfrontacji wybierasz dostępny próg wraz z jego kosztem,
licząc premię tylko raz. Bez puli i po drainie premia wynosi zero.
Naładowanie nie zwiększa obrażeń ani wpływu. ST zdolności pozostają wartościami
określonymi przez zdolność; ta zmiana dotyczy składników rzutów, nie ST.
Garran: miecz `k20 +4 Siła + naładowanie + inne premie`, obrażenia `1k8 +4`
i pasywy kolorów. Biegłości jako uprawnienia do sprzętu nie zmieniają się.
Samouczki ładowania i zwykłego ataku, panel postaci, kości oraz wydruki używają
tej reguły. Starsze profile zapisów zachowują dotychczasowe zasady.


Wdrożony wariant do prób przy stole. Zastępuje wydawanie całej osobistej puli.
Katalog: `content/balance/pooled_mana/catalog.json`, wersja 2.

## Obieg i kolejność

- Każda walka: zbierz aktywny komplet zgodny z [postawą drużyny](PARTY_ETHOS.md), przetasuj; pule są puste. Po `max(5, 2 × bohaterowie)` kart każdego koloru: 25 kart dla 1–2, 30 dla 3, 40 dla 4, 50 dla 5, 60 dla 6, 70 dla 7. UI wyboru drużyny nadal obsługuje maksymalnie pięciu bohaterów.
- Poniżej 21 pkt: na początku własnej tury uzupełnij ofertę do dwóch, wybierz jedną runą; pozostała karta czeka na następnego gracza. Przy jednej dostępnej karcie bierzesz ją. Zero dostępnych kart powoduje drain.
- Dobór ostatniej karty może przekroczyć 21 bez kary. Od 21 pkt nie dobierasz ani nie uzupełniasz oferty w swojej turze. Po drainie wracasz do zwykłego ładowania przy następnym należnym doborze.
- Punkty 6/12/21 odblokowują zdolności. Bez dodatkowych warunków kolorów: limit doboru nie może zamknąć dostępu do części karty postaci.
- Umiejętność zachowuje całą osobistą pulę. Bazowo spala 1 kartę wspólnej talii. Zwykły atak, ruch i darmowe zdolności nie spalają; wyjątki odzysku Loriana mają koszt 0 przy zachowaniu progu punktów.
- Podbicie kosztuje dodatkowe 2 karty. Zachowujemy efekty, runy oraz indywidualne i łączne limity dotychczasowych wariantów. Kolor przy wariancie jest oznaczeniem, nie kosztem z osobistej puli. Łączenie kilku podbić jest dozwolone w granicach limitów.
- Wybierz wariant i potwierdź koszt PRZED efektem. Rozstrzygnij akcję, następnie zgłoś kolory spalanych kart z wierzchu. Jeśli nie ma całej wymaganej liczby, efekt akcji pozostaje i następuje drain. Przy dokładnym wyczerpaniu reset dopiero przy kolejnej niemożliwej operacji.
- Na granicy rund jedna karta z wierzchu **wygasa**. Osobny stos, nieodzyskiwalny przez zdolności. Jeśli brakuje karty — drain. Ta zasada zapewnia reset nawet przy samych darmowych akcjach i odzysku Loriana.
- Wrogowie nadal spalają ofertę/wierzch i więżą manę. Pokonanie więżącego oddaje jego karty na spód bez tasowania. Po wygaśnięciu karty na koniec rundy aplikacja wraca do należnego doboru nowego aktora.
- Drain: WSZYSTKIE karty aktywnej talii (bez wyłączonych przez postawę drużyny), także ładowane, spalone, wygasłe i uwięzione, wracają do przetasowanego kompletu. Znikają premie kolorów i efekty O, z uwzględnieniem koncentracji. Leczenie, zadane obrażenia i pozycje pozostają. Nie odnawia akcji/reakcji/znaczników użycia w turze i nie daje dodatkowego doboru.

## Punkty i kolory

Wartości punktowe celowo są oddzielne od efektów kolorów. Najszybszy kolor nie zawsze daje najbardziej pożądaną premię. Specjalizacja jest legalna; brak dodatkowej nagrody za tęczę. Premie obrażeń sumują się za każdą kartę; KP, trafienie i obrony mają jawne limity. Nie zmieniamy bazowych wartości cech.

Leczenie działa tylko w momencie rzeczywistego wyboru karty, nie przy odświeżeniu ekranu, przygotowaniu puli lekcji ani na początku kolejnych tur. Nie wskrzesza nieprzytomnych. Automatyczny odbiorca: największy brak PW wśród przytomnych sojuszników w 10 ft, wliczając właściciela; remis rozstrzyga stałe ID. Brak drugiego okna wyboru przy każdym doborze.

### Garran

| Kolor | Punkty | Pasyw |
|---|---:|---|
| Czerwona | 4 | Natarcie: +1 obrażeń wręcz za kartę |
| Biała | 7 | Mur tarcz: +1 KP za kartę (maks. +2) |
| Zielona | 1 | Drugi oddech: przy doborze odzyskaj 5 PW |
| Czarna | 3 | Wytrwałość: +1 do obron KON (maks. +2) |
| Niebieska | 4 | Czujność: +2 do obron MĄD (maks. +2) |

Skaza — **Nieustępliwość**: Rozpoczęcie własnej tury przy wrogu zmniejsza limit zwykłego ruchu o połowę do końca tury.

### Brakka

| Kolor | Punkty | Pasyw |
|---|---:|---|
| Czerwona | 7 | Rozpęd: +1 obrażeń wręcz za kartę |
| Biała | 1 | Garda: +1 KP (maks. +1) |
| Zielona | 3 | Witalność: przy doborze odzyskaj 5 PW |
| Czarna | 4 | Nieustraszona: +2 do obron MĄD (maks. +2) |
| Niebieska | 4 | Hart: +2 do obron KON (maks. +2) |

Skaza — **Głód walki**: Tura bez ofensywy kończy Szał.

### Mira

| Kolor | Punkty | Pasyw |
|---|---:|---|
| Czerwona | 3 | Precyzja: +1 do trafienia (maks. +1) |
| Biała | 1 | Unik: +1 KP (maks. +1) |
| Zielona | 7 | Ostrze: +1 obrażeń wręcz za kartę |
| Czarna | 4 | Refleks: +2 do obron ZRĘ (maks. +2) |
| Niebieska | 4 | Wytchnienie: przy doborze odzyskaj 4 PW |

Skaza — **Cienka granica**: W ukryciu masz utrudnienie obron i testów reakcji.

### Dagna

| Kolor | Punkty | Pasyw |
|---|---:|---|
| Czerwona | 1 | Gniew: +2 obrażeń zaklęć za kartę |
| Biała | 7 | Wiara: +1 do wszystkich obron (maks. +2) |
| Zielona | 4 | Ukojenie: przy doborze przytomni sojusznicy w 10 ft i ty odzyskujecie 2 PW |
| Czarna | 3 | Ochrona: +1 KP (maks. +1) |
| Niebieska | 4 | Łaska: przy doborze ulecz o 4 PW najbardziej rannego przytomnego sojusznika w 10 ft, wliczając siebie |

Skaza — **Nikogo nie zostawiam**: Ofensywna płatna zdolność przy sojuszniku poniżej połowy PW spala dodatkową kartę.

### Lorian

| Kolor | Punkty | Pasyw |
|---|---:|---|
| Czerwona | 1 | Akcent: +2 obrażeń dystansowej broni za kartę |
| Biała | 4 | Rytm kroków: +1 KP (maks. +1) |
| Zielona | 4 | Otucha: przy doborze ulecz o 3 PW najbardziej rannego przytomnego sojusznika w 10 ft, wliczając siebie |
| Czarna | 3 | Oszczędna harmonia: spalanie własnej zdolności −1 (minimum 1, maks. rabatu 1) |
| Niebieska | 7 | Rezonans: +1 do obron CHA (maks. +2) |

Skaza — **Potrzeba publiczności**: Bez przytomnego sojusznika w 10 ft, w wieloosobowej drużynie: płatna zdolność spala dodatkową kartę.

### Nimra

| Kolor | Punkty | Pasyw |
|---|---:|---|
| Czerwona | 4 | Żar: +2 obrażeń zaklęć za kartę |
| Biała | 1 | Powłoka: +1 KP (maks. +1) |
| Zielona | 3 | Regeneracja: przy doborze odzyskaj 4 PW |
| Czarna | 4 | Skupienie: +2 do obron KON (maks. +2) |
| Niebieska | 7 | Nasycenie: +1 obrażeń zaklęć za kartę |

Skaza — **Echo**: Echo: kolejna ta sama płatna zdolność z rzędu spala o 1 kartę więcej (maks. +2). Inna płatna zdolność zeruje serię.

### Erynd

| Kolor | Punkty | Pasyw |
|---|---:|---|
| Czerwona | 4 | Siła cięciwy: +1 obrażeń dystansowej broni za kartę |
| Biała | 1 | Kamuflaż: +1 KP (maks. +1) |
| Zielona | 7 | Instynkt: +1 do obron ZRĘ (maks. +2) |
| Czarna | 3 | Opanowanie: +2 do obron MĄD (maks. +2) |
| Niebieska | 4 | Skupiony wzrok: +1 do trafienia (maks. +1) |

Skaza — **Trauma bratobójczego strzału**: Płatny strzał w cel sąsiadujący z innym bohaterem spala dodatkową kartę.

## Lorian

Strojenie jest darmową akcją dodatkową: podejrzyj do dwóch kart i ustal kolejność wierzchu. Odzysk od 12 pkt to akcja główna zwracająca do dwóch spalonych kart na spód bez bazowego spalania. Podbicie zwiększa odzysk, ale po nim spala dwie karty; czarna premia może obniżyć tę dopłatę do jednej. Wielkie strojenie od 21 pkt odzyskuje do trzech spalonych kart na wierzch. Odzysk nigdy nie dotyka wygasłych ani uwięzionych kart. Koszt akcji i nieodzyskiwalne wygasanie ograniczają pętlę odzysku.

## UI, samouczek, zapis

Punkty, pełne naładowanie, wartości kart i premie są widoczne przy aktywnym bohaterze; efekty trafiają też do zwykłego panelu statusów. Wybór karty pokazuje jej punkty oraz pasyw przed decyzją. Panel talii pokazuje oddzielnie spalone, wygasłe i uwięzione. Runy obsługują dobór, podbicia i operacje talii; dotychczasowy fokus kości, −/+, przegląd i ✓ pozostają.

Walkthrough: 148 lekcji, po siedem podstaw na bohatera i wcześniejsze 99 ćwiczeń zdolności/podbić. Dodano dojście do 21+ i następną turę bez doboru oraz wygaśnięcie karty. Lekcje zdolności kończą się dopiero po fizycznym rozliczeniu spalania. Postęp ma nowy klucz `walkthrough_charge_progress_*`, aby wcześniejsze zaliczenia nie pomijały nowych zasad. Rozmowy z NPC i obiekty pozostają dostępne z areny, z własnymi zasadami eksploracji.

Zapis przechowuje wartości punktów, pule, wszystkie stosy, pozostałe spalanie i wznowienie doboru po granicy rundy. Dawny znacznik bohatera `pooled_mana_v01` pozostaje identyfikatorem kompatybilności; katalog i nowe pola stanu mają wersję 2. Dawne zapisane pule dostają bieżącą tabelę punktów przy synchronizacji. Nie należy kontynuować dawnej próby balansu: nowy pojedynek samouczka daje czysty komplet i aktualne reguły. Płatne akcje w trakcie nierozstrzygniętych rzutów nadal blokują zapis zgodnie z istniejącym kontraktem.

## Ewaluacja

`python scripts/evaluate_combat_mana.py --samples 14 --rounds 8 --output docs/reports/mana_charge_v02/baseline`

Raport HTML/JSON/CSV zawiera kopię katalogu, hash, seed i ograniczenia. Symulacja używa tego samego silnika obiegu kart: zatrzymanie doboru, koszt 1/3, wygasanie, pełny drain, odzysk Loriana i rabat czarnej many. Strategie mają wyłącznie publiczną wiedzę. Nie symuluje obrażeń, trafień, leczenia, pozycji ani wygranych; nie dowodzi równowagi bohaterów. `overburn` to eksperyment ekonomiczny z jedną dopłatą +2 na akcję, nie polityka wyboru konkretnego efektu podbicia. `sustain` wstrzymuje kosztowne akcje przy małej talii, a Lorian odzyskuje karty. Nadwyżka ponad próg nie jest już stratą punktów.

W bazowych 4704 próbach (336 wariantów) dla pięciu bohaterów i 50 kart, bez presji wroga: adaptive daje ok. 4,3 zdolności na bohatera przez 8 rund, średnio 1 drain; overburn ok. 3,7 i 1,6 draina. Oszczędzanie daje ok. 3 użyć, bez draina w tym ośmiorundowym oknie, i około połowę tur na pełnym ładunku. Brak draina przez 8 rund nie oznacza nieskończonej pętli. Próba „deck” spala 2 dodatkowe karty co rundę i jest mocniejsza od produkcyjnych wrogów trafiających co drugą rundę.

Do oceny przy stole: tempo obsługi spalania, atrakcyjność kolorów niskopunktowych, siła wielokrotnych ataków z premią obrażeń, dominacja powtarzanego ulta i akcje regeneracji Loriana. Liczby są propozycją wdrożoną do gry, nie zamkniętym balansem.

## Weryfikacja wdrożenia

272 testy w 16 plikach, uruchamiane sekwencyjnie przez `scripts/safe_pytest.sh`:

- `test_mana_charge.py` — 21: limit, statusy, leczenie, obrażenia, obrony, pełny drain i rzeczywiste operacje Loriana.
- `test_pooled_mana.py` — 33; `test_pooled_mana_runtime.py` — 11; `test_pooled_mana_points.py` — 9; `test_pooled_mana_enemies.py` — 6.
- `test_pooled_mana_training.py` — 33; `test_training_walkthrough.py` — 33 (w tym dostępność akcji wszystkich 148 lekcji); `test_garran_training_regressions.py` — 11.
- `test_shared_mana.py` — 13; `test_shared_mana_runtime.py` — 30; `test_physical_mana.py` — 19; `test_exploration_mana_runtime.py` — 20.
- `test_mana_character_prints.py` — 25.
- Chrome: `test_pooled_mana_browser.py` — 4; `test_training_walkthrough_browser.py` — 2; `test_garran_training_browser.py` — 2. Widoki 390/1100 px i układ wszystkich bohaterów w arkuszach/kartach, bez przepełnień.

Ponadto: 4704 deterministyczne próby ekonomii, zgodność hasha raportu z katalogiem, kompilacja Pythona i `git diff --check`. Wygenerowano 28 PDF bohaterów, cztery zbiorcze PDF i pakiet areny 67 stron; wizualnie sprawdzono pierwszą stronę arkusza Loriana. Nie uruchamiano całego repozytorium ani próby na fizycznych czujnikach.

# Głodne Cienie — gameplay/UI playtest

Data serii: 2026-09-03  
Zakres: aktualny runtime `Ostatni transport — Zawalona droga`, warianty dla
1–5 bohaterów, siedem postaci dostępnych w ekranie Nowa gra.

## Werdykt

Encounter jest grywalny od otwarcia, przez sześć kroków ustawienia i inicjatywę,
aż do zwycięstwa/porażki oraz powrotu do eksploracji. W pięciu pełnych sesjach
prowadzonych przez kontrakt UI cztery drużyny wygrały, a jedna została pokonana.
Nie wystąpił crash, utknięty prompt ani nierozstrzygalny stan walki.

Obecna trudność jest jednak dużo wyższa niż w serii z 2026-08-10. W dodatkowych
160 deterministycznych walkach ofensywnego automatu gracze wygrali 97 razy
(60,6%), przegrali 52 razy, a 11 walk przekroczyło limit 15 rund. Najbardziej
podejrzany jest wariant trzyosobowy: Garran/Dagna/Erynd wygrał tylko 20% prób.

Desktopowy interfejs dobrze komunikuje kolejkę, aktywnego bohatera, PW/KP, ruch
i ekonomię akcji. Na widoku telefonu 390×844 lista działań zostaje zepchnięta
pod bardzo wysoki pusty obszar i nie mieści się w pierwszym ekranie. To jest
realny problem UX, a nie tylko kosmetyka.

## Metoda

### Pięć pełnych przejść przez UI

Każdą sesję rozpoczęto wyborem drużyny w formularzu Nowa gra. Następnie test
wchodził bezpośrednio do aktualnej sceny `Zawalona droga` (bez powtarzania
wcześniejszej części kampanii) i wykonywał dokładnie kolejne operacje dostępne
graczom:

1. rozstrzygnięcie otwarcia encountera,
2. rozpoczęcie setupu i sześć kroków ustawiania figurek/terenu,
3. fizyczne wskazania pól przez wejście symulatora planszy,
4. wpisanie fizycznych rzutów inicjatywy,
5. wybór akcji z menu aktywnego bohatera,
6. wskazanie celów/pól na planszy i jawne potwierdzenia,
7. rzuty ataku, obrażeń, obronne, koncentracji, reakcji i death saves,
8. potwierdzanie intencji/ruchów/ataków AI,
9. potwierdzenie wyniku i sprawdzenie przejścia do następnego stanu sceny.

Rzuty były pseudolosowe, ale powtarzalne dzięki zapisanym ziarnom. Polityka
graczy skupiała ogień na rannych celach, zbliżała się do najbliższego legalnego
pola ataku i korzystała z reprezentatywnych zdolności. Nie znała przyszłych
rzutów i nie cofała niekorzystnych wyników. Nie była pełnym taktycznym botem:
nie optymalizowała leczenia, wszystkich aur ani pozycji kilku tur naprzód.

### Dodatkowa matryca balansu

Runner `scripts/run_glodne_cienie_playtests.py` wykonał 20 walk dla każdego z
ośmiu składów (160 łącznie, ziarna od 93000, limit 15 rund). Korzysta on z tej
samej mapy, zasad ataku/ruchu i produkcyjnego AI, ale ze świadomie prostą
polityką bohaterów: wybiera najmocniejszy dostępny atak i najsłabszy cel. Nie
używa leczenia, rozbudowanych reakcji ani większości specjalnych kombinacji.

## Wyniki pełnych walk UI

| Test | Drużyna | Ziarno | Wynik | Rundy / tury | Stan końcowy |
|---|---|---:|---|---:|---|
| Solo obrońca | Garran | 7301 | zwycięstwo | 2 / 3 | Garran 20/28; Cień pokonany |
| Szał i wiara | Brakka, Dagna | 7302 | zwycięstwo | 3 / 9 | Brakka 22/32, Dagna 30/30; zwykły Cień pokonany, Herszt uciekł |
| Mobilne trio | Mira, Lorian, Erynd | 7303 | zwycięstwo | 3 / 15 | Mira 8/21, Lorian 24/24, Erynd 25/25; dwa Cienie pokonane, Herszt uciekł |
| Kontrolna czwórka | Garran, Dagna, Nimra, Mira | 7304 | porażka | 30 / 138 | wszyscy bohaterowie 0 PW; dwa Cienie pokonane, jeden Cień 16 PW i Herszt 34 PW pozostali |
| Mieszana piątka | Brakka, Lorian, Dagna, Erynd, Nimra | 7305 | zwycięstwo | 4 / 26 | Nimra 16/20, reszta pełne PW; cztery Cienie pokonane, Herszt uciekł |

Po każdym zwycięstwie UI prawidłowo ustawił `map1_encounter_cleared`, ujawnił
`road_aftermath` i `teren` oraz pokazał komunikat „Droga ucichła”. Po porażce
nastąpił stan `game_over`; nie ujawniono punktów dostępnych tylko po wygranej.

## Pokrycie postaci i zdolności

- Garran: Pozycja obronna, walka mieczem i utrzymywanie pierwszej linii.
- Brakka: Szał, Twarda jak skała oraz ataki toporem.
- Mira: walka rapierem, pozycjonowanie i ekspozycja kruchej postaci walczącej
  blisko celu. Jej pełne drzewo Forteli wymaga osobnego, celowanego testu UX.
- Dagna: Bless, Guiding Bolt, aura wsparcia oraz przejście na broń w zwarciu.
- Lorian: Inspiracja bardowska, Podszept paniki, Cutting Words i ataki Ready.
- Nimra: Ścieżka błyskawic, Impuls mrozu, kostur i wielokrotne czary obronne.
- Erynd: Hunter's Mark, długi łuk oraz transfer nacisku między celami.

W walkach pojawiły się akcje, akcje dodatkowe, ruch dzielony, koncentracja,
reakcje, akcje przygotowane, rzuty obronne, obrażenia wieloskładnikowe i rzuty
śmierci. Wszystkie siedem postaci z aktualnego selektora Nowa gra wystąpiło w
co najmniej dwóch składach; jeden z testów Garrana celowo rozegrano solo.

## Wyniki matrycy 160 walk

| Skład | Wygrane | Porażki | Timeout | Śr. rund | Śr. pokonani bohaterowie | Śr. pozostałe PW |
|---|---:|---:|---:|---:|---:|---:|
| Garran | 20/20 (100%) | 0 | 0 | 3,40 | 0,00 | 89,6% |
| Brakka, Dagna | 15/20 (75%) | 2 | 3 | 7,85 | 0,40 | 45,7% |
| Mira, Erynd | 14/20 (70%) | 5 | 1 | 9,25 | 1,10 | 32,8% |
| Garran, Dagna, Erynd | 4/20 (20%) | 14 | 2 | 12,35 | 2,45 | 12,4% |
| Lorian, Mira, Nimra | 9/20 (45%) | 9 | 2 | 9,00 | 2,00 | 25,5% |
| Brakka, Dagna, Erynd, Nimra | 12/20 (60%) | 8 | 0 | 7,35 | 2,00 | 42,6% |
| Garran, Brakka, Dagna, Mira, Erynd | 12/20 (60%) | 5 | 3 | 9,25 | 2,85 | 38,6% |
| Lorian, Dagna, Mira, Nimra, Erynd | 11/20 (55%) | 9 | 0 | 6,95 | 2,95 | 39,0% |

AI wykonało 3612 intencji: 2080 `pack_attack`, 1103 `leader_ranged`, 303
`flee`, 95 `pack_advance` i 31 `engage`. Z 315 przeciwników 159 zginęło, a
156 uciekło. Bohaterowie łącznie osiągnęli 0 PW 275 razy. Wynik pokazuje, że
spotkanie często kończy się ucieczką stada, ale obecne skupianie ognia i presja
Herszta potrafią wcześniej wyeliminować dużą część drużyny.

## Wrażenia z rozgrywki

### Przejrzystość UI

Ocena desktop: **7/10**.

Najlepiej działają: wstęga inicjatywy, duży nagłówek aktywnej postaci, paski PW,
czytelne kapsułki „Akcja/Bonus/Interakcja/Reakcja gotowa”, kolorowe grupy akcji
oraz stałe podpowiedzi Numpad 8/2/Enter. Rozdzielenie listy, podglądu, wskazania
na planszy, rzutu i wyniku dobrze chroni przed przypadkowym wydaniem zasobu.

Słabsze strony: Lorian ma już 18 pozycji w jednej przewijanej liście, więc
znalezienie konkretnej techniki jest wolniejsze niż sama decyzja. Opisy kilku
cech są generyczne („interfejs poprosi tylko o wymagany cel...”), zamiast od
razu komunikować koszt i efekt. Wariant mobilny 390×844 oceniam na **3/10** z
powodu pustej przestrzeni wypychającej najważniejszą listę działań pod ekran.

### Taktyczny charakter

Ocena: **8/10**.

Gra wymusza prawdziwe decyzje o koncentracji ognia, linii strzału, wejściu w
zwarcie, zużyciu reakcji, ruchu przed/po ataku oraz ryzyku związanym z aurami i
obszarami. AI nie jest workiem PW: ustawia stado, korzysta ze wsparcia,
zapamiętuje ofiarę, atakuje dystansowo Hersztem i wycofuje się po złamaniu
warunków. Zwycięskie trio i piątka dobrze pokazały wartość Mark/Inspiracji,
reakcji i szybkiego usuwania zwykłych Cieni.

Czwórka kontrolna pokazała drugą stronę. Bez leczenia i skutecznego wyłączenia
Herszta dwa cele zostały zniszczone, ale pozostały Cień długo wiązał drużynę,
a Herszt stopniowo eliminował kolejne postacie. 31 ruchów i 39 ataków graczy
w 30 rundach to zbyt długi finał jak na pierwszy encounter, nawet jeżeli sam
stan był poprawny mechanicznie.

### Balans postaci i encountera

Nie widać jednej postaci, która samodzielnie psuje grę. Garran jest bardzo
bezpieczny w wariancie solo, Brakka daje wyraźny skok przeżywalności i obrażeń,
Dagna podnosi stabilność drużyny, a Lorian/Erynd/Nimra zapewniają mocne opcje
dystansowe i kontrolę. Mira ma najwyższy koszt błędu: jej obecny zestaw zachęca
do agresywnego pozycjonowania, ale 21 PW szybko znika po utracie osłony.

Największy problem leży w skalowaniu spotkania, nie w pojedynczej karcie.
Krzywa trudności nie jest monotoniczna: solo Garran ma 100% zwycięstw, a
zbalansowane trio tylko 20%. Składy cztero- i pięcioosobowe również kończą ze
średnio 2–3 bohaterami na 0 PW. Na encounter uczący aktualnego systemu to za
duża kara i zbyt częsty długi cleanup.

## Błędy i dalsze działania

### Naprawione w tej serii

- Inspiracja bardowska była widoczna w menu pola Loriania, ale jej wybranie
  próbowało natychmiast rozstrzygnąć cechę bez sojusznika i zwracało błąd
  „Bardic Inspiration wymaga innego sojusznika”. Menu prowadzi teraz do
  poprawnego wskazania celu na planszy; dodano test regresyjny.

### Otwarte

1. **P0 mobile UX:** usunąć pusty pionowy obszar przed listą działań na 390×844.
2. **P0 balans tria:** sprawdzić o jednego zwykłego Cienia mniej, słabszą premię
   wsparcia stada albo późniejsze wejście pełnej presji Herszta; porównać na tych
   samych ziarnach zamiast jednocześnie zmieniać kilka parametrów.
3. **P1 długość walk:** dodać zabezpieczenie przed wielorundowym finałem jednego
   zdrowego Cienia i Herszta albo szybciej uruchamiać ich nieodwracalny odwrót.
4. **P1 lista akcji:** dla zestawów z 15+ opcjami rozważyć szybkie filtrowanie,
   zwijane grupy lub zapamiętanie ostatnio używanych pozycji.
5. **P1 pokrycie:** wykonać osobny scenariusz taktyczny dla pełnej sekwencji
   Forteli Miry (Smoke Screen i nazwany atak) oraz celowane testy obszarów Nimry.

## Artefakty i odtwarzalność

- `artifacts/playtests/glodne_cienie_2026-09-03/summary.json` — agregaty,
- `artifacts/playtests/glodne_cienie_2026-09-03/results.json` — 160 wyników,
- `artifacts/playtests/glodne_cienie_2026-09-03/results.csv` — dane tabelaryczne,
- `artifacts/playtests/glodne_cienie_2026-09-03/events.jsonl.gz` — skompresowane
  pełne logi tur.

Polecenie odtwarzające serię:

```bash
PYTHONPATH=src:. python scripts/run_glodne_cienie_playtests.py \
  --runs 20 --base-seed 93000 \
  --output-dir artifacts/playtests/glodne_cienie_2026-09-03
```

Render sprawdzono w Chrome headless dla 1440×1000 i 390×844. Zrzuty robocze
pozostały poza repozytorium w `/tmp/gc_ui_desktop.png` i
`/tmp/gc_ui_mobile.png`.

# Głodne Cienie — raport automatycznych playtestów

Data serii: 2026-08-10  
Wersja danych: battlemap v4, pasywne defensive spots, `+1` do ataków Cieni, `weighted_utility_v1`, skalowanie 1–5 bohaterów  
Liczba walk: 64 (8 ziaren dla każdego składu), limit: 15 rund

## Co rzeczywiście testuje automat

Przeciwnicy korzystają z tej samej implementacji co aplikacja: produkcyjnego
pathfindingu, trudnego terenu, utility AI, seeded noise, morale, ucieczki,
outcome ledgeru, ataków i `conditional_on_hit_save` Skoku stada. Gemini nie
bierze udziału w decyzjach.

Polityka bohaterów korzysta z ich prawdziwych postaci poziomu 3, wyposażenia,
kart ataku i czarów, slotów/zasobów, akcji, ruchu, zasięgu, osłon i rzutów.
Chowa broń, gdy potrzebuje wolnej ręki do czaru. Pasywne pola obronne są
przechodnie i automatycznie dodają stojącej na nich figurce `+2 KP`, niezależnie
od frakcji i bez wydawania akcji. W każdej turze polityka wybiera najsilniejszy
dostępny atak oraz cel o najniższych PW. Nie korzysta z leczenia,
reakcji, dzwonu ani bardziej kreatywnych kombinacji kart. Jest więc dobrym
testem regresji i górnej granicy ofensywnej skuteczności, ale nie zastępuje
ludzkiego balansu.

## Wyniki

| Skład | Liczba | Zwycięstwa | Śr. rund | Śr. utracone PW | Śr. pokonani bohaterowie |
|---|---:|---:|---:|---:|---:|
| Garran | 1 | 8/8 | 4,38 | 8,0% | 0,00 |
| Brakka, Dagna | 2 | 8/8 | 5,62 | 13,3% | 0,00 |
| Mira, Erynd | 2 | 8/8 | 6,00 | 16,8% | 0,00 |
| Garran, Dagna, Erynd | 3 | 8/8 | 6,00 | 16,6% | 0,00 |
| Lorian, Mira, Nimra | 3 | 8/8 | 6,25 | 8,3% | 0,00 |
| Brakka, Dagna, Erynd, Nimra | 4 | 8/8 | 6,50 | 14,8% | 0,12 |
| Garran, Brakka, Dagna, Mira, Erynd | 5 | 8/8 | 5,50 | 6,3% | 0,00 |
| Lorian, Dagna, Mira, Nimra, Erynd | 5 | 8/8 | 4,12 | 3,6% | 0,00 |

Łącznie: 64 zwycięstwa, 0 porażek, 0 timeoutów i 1 bohater zredukowany do
0 PW. Z 200 przeciwników 55 zginęło, a 145 uciekło. AI wykonało 181 ataków;
83 zadały obrażenia, łącznie 517. Przed premią `+1` było to 71 skutecznych
trafień i 452 obrażenia, więc wzrost wyniósł 65 obrażeń (`+14,4%`). AI wybrało:
`advance` 138 razy, `engage` 180, `regroup` 291, `guard` 37 i `flee` 222. W 231 turach
`regroup` kończył się na jednym z nowych pól obronnych. Skok stada otworzył
5 fizycznych rzutów obronnych.

## Ocena

Mechanicznie encounter jest domknięty i nie wykazał pętli, crashy ani
nierozstrzygalnych stanów. Wszystkie rodzaje intencji AI wystąpiły w logach,
a każda walka zakończyła się przed limitem rund. Symulacja wykryła i pozwoliła
usunąć dwie oscylacje: osłona nie konkuruje już z osiągalnym atakiem, a zwykłe
`regroup` ani reakcja na ostrzał nie mogą przebić `flee` przy `≤25% PW` lub
morale na progu ucieczki.

Balans pozostaje po stronie graczy, szczególnie dla pięcioosobowego składu
dystansowego. Podniesienie PW Cieni (`14→16`, przewodnica `30→34`, warianty
solo/duo `12/24`), osłony i premia do ataku zwiększyły presję głównie na
składy 3–4-osobowe, lecz morale nadal często kończy starcie ucieczką. To jest
akceptowalne dla pierwszego encountera uczącego reaktywnego AI i odwrotu.
Nie zwiększałbym już statystyk przed testem fizycznym.

## Co sprawdzić na fizycznej planszy

1. Czy setup 1–5 pokazuje wyłącznie właściwe pola figurek i terenu.
2. Czy Dash przez błoto, trasy `advance`/`flee` oraz pola zejścia są czytelne.
3. Czy trzy niskie defensive spots są intuicyjnie przechodnie i czy automatyczne
   `+2 KP` jest jasne bez osobnej akcji.
4. Czy LED-y odróżniają atak, przegrupowanie, pilnowanie i ucieczkę.
5. Czy po Skoku stada gracz dostaje ST 12/13 i po porażce jest powalony.
6. Czy zdjęcie uciekającej figurki i zwycięstwo bez zabicia stada są jasne.
7. Czy Retry ponawia setup i odtwarza identyczny wariant, seed i zasoby.
8. Czy drużyna dystansowa odczuwa realne zagrożenie przed złamaniem morale.

## Artefakty do analizy

- `artifacts/playtests/glodne_cienie/events.jsonl` — pełny log każdej tury,
- `artifacts/playtests/glodne_cienie/results.json` — wyniki pojedynczych walk,
- `artifacts/playtests/glodne_cienie/results.csv` — dane do arkusza,
- `artifacts/playtests/glodne_cienie/summary.json` — agregaty powyższej tabeli.

Każdą walkę można odtworzyć przez `case_id` i `seed` zapisane w logu.

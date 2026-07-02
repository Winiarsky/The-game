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
Brama jest drewniana, stara i napuchnieta od wilgoci, ale nadal trzyma sie calkiem solidnie przez metalowe okucia, zardzewiale zawiasy i drewniany rygiel po wewnetrznej stronie. Przy dokladniejszym zbadaniu mozna odkryc wyryta pieczec zakladu kowalskiego oraz date wykonania. Po znaku i dacie widac, ze brama ma okolo 20 lat.

Najsłabszym punktem bramy sa zawiasy. Nie jest to od razu oczywiste dla graczy. Z tylu, po stronie dziedzinca, znajduje sie drewniany rygiel, ktory utrudnia wywazenie bramy. Jesli ktos przedostanie sie na druga strone, moze zdjac rygiel i wtedy dalsze otwarcie bramy bedzie duzo latwiejsze.

Brama jest zamknieta, a sam zamek jest zatarty, co utrudnia otwarcie narzedziami zlodziejskimi. Ziemia pod brama to twardy kamien/beton, wiec szybki podkop nie ma sensu w tej scenie. Na gorze bramy sa slabo widoczne z dolu kolce, niebezpieczne przy przechodzeniu gora. Obok bramy jest solidny murowany plot, po ktorym mozna sprobowac wejsc, ale tez grozi poslizgnieciem albo halasem.

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

Lokalne limity / konsekwencje do przyszlego JSON:
- `force`: moze szybko dac duzy postep, ale zwykle generuje halas.
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
- wspinaczka: medium, ale z ryzykiem kolcow/upadku
- badanie słabości: easy
- wejscie murem obok: easy
- przejscie gora przez brame bez przygotowania: medium/hard, zależnie od opisu zabezpieczenia i asekuracji

## 14. Sukces / Porażka / Krytyczne Wyniki
Sukces:
- co się dzieje: brama sie otwiera albo wyraznie oslabia, zależnie od deklaracji
- jaki efekt mechaniczny: progress pointy, flaga pomocnicza albo bonus/przygotowanie do nastepnego rzutu

Porażka:
- co się dzieje: brama stawia opor
- jaki efekt mechaniczny: mniej progress pointow, kara do nastepnych rzutow, rany, halas, stracony czas albo komplikacja

Krytyczny sukces: wyjatkowo dobrze otwieracie brame
- co dodatkowo: dodatkowe progress pointy, redukcja halasu

Krytyczna porażka: brama okazuje sie bardziej stabilna niz sie wydaje
- co się pogarsza: brak albo redukcja progress pointow, powazniejsze konsekwencje, np. zaklinowanie zamka, upadek, skaleczenie albo duzy halas
  

## 15. Limity I Parametry
- maksymalna nagroda: otwarta brama i ciche wejscie na dziedziniec
- minimalna/maksymalna stawka:
- liczba prób: do skutku
- koszt czasu: kazda nieudana albo glosna proba moze zwiekszac ryzyko komplikacji fabularnej
- poziom hałasu: 0-3, zależnie od metody i wyniku
- limit zasobów: jeden istotny zasob/narzedzie na probe, chyba ze runtime pozniej obsluzy laczenie zasobow

## 16. Czy Interakcja Ma Progres?
Tak.

Jeśli tak:
- ile punktów postępu potrzeba:  `3`
- co daje postęp: brama zaczyna coraz bardziej sie otwierac, rygiel/okucia puszczaja albo drużyna zdobywa praktyczna droge przejscia
- co kończy interakcję: osiągnięcie progressu i ustawienie `gate_passed`

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

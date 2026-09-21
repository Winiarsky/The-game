# Mana: sześć kart i kolor atutowy — 20.09.2026

Aktualny model zastępuje punktację 1–7 oraz progi 6/12/21 w walce i drużynowych konfrontacjach. Dawny blackjack pozostaje wyłącznie zgodnością historycznych scen.

- Osobista pula: **maksymalnie 6 fizycznych kart**. Na początku tury przy mniejszej puli wybierz jedną kartę z oferty. Druga zostaje dla następnej osoby. Przy sześciu kartach pomiń dobór. Po utracie karty ponownie dobierasz na początku następnej tury.
- **Naładowanie do testów = liczba fizycznych kart**, od +0 do +6. Dotyczy ataków, obron i testów eksploracji. Nie zwiększa obrażeń, wpływu ani postępu.
- **Ładunek zdolności = karty + liczba kart atutowych**, maksymalnie 6. Zwykła karta daje 1, atut daje 2. Progi akcji: 2 / 4 / 6; 6 odblokowuje ultę. Akcje darmowe nadal wymagają 0.
- Trzy atuty: ładunek 6, test +3, nadal dobierasz do sześciu fizycznych kart. Sześć kart dowolnych kolorów: ładunek 6 i test +6.
- Kolory uruchamiają dotychczasowe pasywy. Atut nie podwaja ich efektów ani liczby kart do kumulacji.
- Użycie zdolności zachowuje osobistą pulę. Spalanie akcji, podbicia, skazy, odzysk Loriana i presja przeciwników działają jak dotąd.
- Test i pomoc w konfrontacji nadal spalają po jednej karcie. Podgląd jest bez spalania. Atut nie daje dodatkowej premii do testów rozmowy/obiektu.
- Pasywy eksploracji wszystkich bohaterów nie wymagają kart atutowych.
- Mana drain w walce zbiera wszystkie aktywne strefy i resetuje nasycenie; w konfrontacji kończy próbę według jej zasad. Karty wyłączone przez postawę drużyny nadal pozostają poza talią.

## Kolory atutowe

| Bohater | Atut |
|---|---|
| Garran | Biały |
| Brakka | Czerwony |
| Mira | Zielony |
| Dagna | Biały |
| Lorian | Niebieski |
| Nimra | Niebieski |
| Erynd | Zielony |

## Bilans talii przy pełnych pulach

Skład bazowy: po `max(5, 2 × liczba bohaterów)` każdego koloru.

| Drużyna | Cała talia | W pulach | Poza pulami | W zakrytej talii przy jednej karcie w ofercie |
|---|---|---|---|---|
| 3 | 30 | 18 | 12 | 11 |
| 4 | 40 | 24 | 16 | 15 |
| 5 | 50 | 30 | 20 | 19 |
| 6 | 60 | 36 | 24 | 23 |

To górne granice bez spalania, wygasania, uwięzienia i postawy. Każda karta w tych strefach dodatkowo zmniejsza dostępny zapas. Wartość atutu nie zmienia bilansu fizycznych kart.

## Zapisy, UI i wydruki

Katalog ma wersję 3. Odczyt wersji 1/2 przelicza najwyższą dawną wartość na atut, pozostałe na 1; nie zmienia fizycznych stref. Historyczne pule większe niż 6 zachowujemy do draina, blokując dobór i ograniczając premię do +6. Rozpoczęte rozstrzygnięcie zachowuje już zadeklarowany bonus; nowa deklaracja używa nowych zasad.

Panel pokazuje osobno liczbę kart, naładowanie testu i ładunek zdolności. Mata many oznacza atut, progi akcji oraz premię +1 za kartę. Wspólny pomocnik ma zaktualizowane przykłady walki i eksploracji. Aktualne, osobne PDF-y: `content/scenarios/misja_0_dzwon/print/karty_postaci_A4.pdf` oraz `sciaga_graczy_A4.pdf` w tym samym folderze. [Instrukcja wydruku i spis materiałów](../content/scenarios/misja_0_dzwon/print/README.md).

## Ewaluacja

`scripts/evaluate_combat_mana.py --samples 7 --sizes 3,4,5,6 --rounds 8 --output docs/reports/mana_trump_6`

Raport JSON/CSV/HTML zawiera 2744 deterministyczne próby ekonomii kart (392 konfiguracje). Rozróżnia pełną pulę fizyczną i dostępność ulty. Nie modeluje obrażeń, czasu obsługi ludzi ani pełnego balansu zwycięstw; te wymagają testów misji.

Przy bazowych taliach i strategii `adaptive`, w próbach bez ataków przeciwnika na manę mediana pierwszej dostępności ulty wyniosła 4–5 rund (wyłącznie dla postaci, które ją osiągnęły). W ośmiu rundach nie osiągnęło jej 2–11% postaci zależnie od liczby graczy; średnio wystąpił jeden drain. To 7 prób na konfigurację, więc nie należy traktować różnic między składami jako gotowego balansu.

Dodatkowy raport [konfrontacji](reports/mana_trump_6/confrontations.md) obejmuje po 14 rozgrywek na scenę, strategię i wielkość drużyny. Typowa mediana wynosi 3–4 rundy; próba jest mała, bez obsługi czasu ludzi i wyborów fabularnych.

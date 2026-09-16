# Skalowanie scenariuszy dla 3–6 graczy

Status: przyjęta strategia projektowa do pierwszych prób przy stole, 2026-09-15.
Wartości są punktem wyjścia do balansu. Ten dokument nie wdraża nowych
wariantów spotkań ani obsługi sześciu osób w UI.

## Wspólne zasady

Scenariusze projektujemy dla 3, 4, 5 i 6 graczy. Wariant dla czterech osób
jest punktem odniesienia. Karty bohaterów pozostają wspólne dla wszystkich
liczebności: te same cechy, wartości kolorów, pasywy, progi 6/12/21 i koszty
spalania. Test nadal wynosi k20 + modyfikator cechy + premia z naładowania
+ inne bonusy. Skalujemy zasoby wspólne i spotkania.

## Talia i presja na manę

| Graczy | Kart w talii | Kart każdego z pięciu kolorów |
|---|---:|---:|
| 3 | 30 | 6 |
| 4 | 40 | 8 |
| 5 | 50 | 10 |
| 6 | 60 | 12 |

W tym zakresie obecna reguła `max(5, 2 × liczba bohaterów)` kopii każdego
koloru daje 10 kart na osobę. Oferta pozostaje dwukartowa. Więcej graczy
oznacza więcej doborów i płatnych działań w rundzie, więc większa talia
nie jest automatycznie dłuższym czasem ładowania pojedynczego bohatera.

W walce zachowujemy wygasanie jednej karty na rundę. Stałe wygasanie oraz
pojedynczy atak w manę mają relatywnie mniejszą siłę przy większej talii.
Najpierw sprawdzamy wyrównanie tej presji przez skład i działania przeciwników;
nie wprowadzamy teraz dodatkowego mnożnika wygasania. Zachowujemy aktualne
różnice zakończenia: w walce drain odbudowuje pełną talię, w konfrontacji
eksploracji brak kart do wymaganej operacji kończy próbę zgodnie z jej zasadami.

## Walki

| Graczy | Orientacyjna łączna pula HP wrogów | Przykładowy skład |
|---|---:|---|
| 3 | 75% wariantu bazowego | Dowódca + 1 pomocnik |
| 4 | 100% | Dowódca + 2 pomocników |
| 5 | 125% | Dowódca + 3 pomocników |
| 6 | 150% | Dowódca + 4 pomocników |

Procent oznacza budżet całego spotkania. Dodany pomocnik już zużywa część
tego budżetu; nie dodajemy go i jednocześnie nie zwiększamy wszystkim HP
o wskazany procent. Składy są ilustracją, nie obowiązkową liczbą wrogów.

Zasadniczo zachowujemy KP, ST i obrażenia pojedynczego ciosu. Większe drużyny
otrzymują więcej zagrożeń i działań przeciwników, a nie wyłącznie większy
zapas HP do zbicia. Rozstawienie musi pozostawiać miejsce na ruch oraz
sensowne wykorzystanie osłon i zdolności obszarowych.

Samotny boss wymaga rozpisanych dla liczebności drużyny działań lub krótkich
reakcji między turami bohaterów, ewentualnie działań areny. Jedna zwykła tura
bossa przy sześciu turach graczy nie powinna być równoważona samym HP.

Ataki spalające lub więżące manę wliczamy w siłę spotkania. Przykład:
pomocnik zamiast ciosu spala odkrytą kartę. Większy skład wrogów może zwiększyć
presję na talię, a gracze mogą usunąć jej źródło. Nie dokładamy tej presji
automatycznie do pełnego, już przeskalowanego zestawu ataków z obrażeniami.

## NPC i obiekty

Zachowujemy proporcjonalny opór i presję sytuacji. Obecne sceny dają bazę:

| Graczy | Opór Nessy: 9/osobę | Opór schowka: 10/osobę | Spalanie reakcji/rundę |
|---|---:|---:|---:|
| 3 | 27 | 30 | 3 |
| 4 | 36 | 40 | 4 |
| 5 | 45 | 50 | 5 |
| 6 | 54 | 60 | 6 |

W nowych scenach dobieramy bazowy opór do sytuacji, a nie kopiujemy zawsze
9 lub 10. ST oraz kości wpływu metod nie zmieniają się z liczebnością.
Podatność nadal wpływa na oba te parametry. Nie zmieniamy profilu NPC
pod aktualny skład drużyny.

Sprawdzamy także składy bez bohatera z podatną metodą: wsparcie i neutralne
podejścia powinny pozostawiać realną drogę do sukcesu. Większy wybór metod
przy sześciu osobach jest istotną przewagą niezależną od liczby akcji.

Zwykła konfrontacja powinna trwać około trzech rund, z czwartą jako zapasem.
Jedna reakcja sytuacji następuje po całej rundzie. Pomoc pozostaje prosta,
bez osobnego rzutu czy dodatkowej tury. Duże konfrontacje z osobnymi zasadami
pozostają poza tym etapem projektu. Mierzymy również czas przy stole:
cztery rundy to do 12 tur przy trzech osobach i do 24 przy sześciu.

## Zastosowanie przy tworzeniu scenariusza

1. Rozpisz spotkanie bazowe dla czterech osób: cel, przeciwników lub opór,
   działania, presję na manę i warunki zakończenia.
2. Przygotuj warianty dla 3, 5 i 6 osób: skład/łączną pulę HP i działania
   wrogów albo opór i presję konfrontacji. Zachowaj wspólne karty bohaterów.
3. Sprawdź pole gry, czas oczekiwania i możliwość odpowiedzi na ataki w manę.
4. Ograj różne składy, zapisz wynik i dostrój liczby dla tej sceny.

## Późniejsza ewaluacja

Rozszerzyć raporty dokładnie na 3/4/5/6 osób i różne składy, w tym bez
Loriana, bez leczenia oraz bez podatnej metody rozmowy. Porównywać rundę
osiągnięcia 12 i 21 pkt, pierwszy drain, użycia zdolności, tury przy pełnym
naładowaniu oraz długość i skuteczność konfrontacji. Dla pełnego balansu
walk dodać obrażenia, leczenie i powalenia; osobno mierzyć czas fizycznej obsługi.

Obecny symulator walki bada ekonomię many, nie pełną skuteczność starcia.
Dotychczasowe raporty nie weryfikują osobno wszystkich czterech liczebności.
UI wyboru drużyny obsługuje obecnie maksymalnie pięciu bohaterów; rozszerzenie
do sześciu jest pracą do wykonania przed próbami takiego składu.

Powiązane zasady: [ładowanie many](MANA_CHARGE_V02.md),
[konfrontacje drużynowe](PARTY_CONFRONTATIONS.md),
[tworzenie scenariuszy](SCENARIO_AUTHORING.md).

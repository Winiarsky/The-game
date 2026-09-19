# Postawa drużyny

Wspólny, trwały wskaźnik: trzy pola ku Solidarności, Równowaga, trzy ku
Bezwzględności. Start w środku. Jedna oznaczona decyzja przesuwa o jedno pole;
na końcu toru pozostaje na skrajnym polu. Nie pokazujemy znaków plus/minus.
Zdarzenia mają unikalne identyfikatory, więc ponowienie żądania nie nalicza ich drugi raz.

## Talia

Baza pozostaje po max(5, 2 × liczba bohaterów) każdego koloru.
Każde pole od środka wyłącza jedną kartę z KAŻDEGO wskazanego koloru:

| Postawa | Czerwona | Biała | Zielona | Czarna | Niebieska |
| --- | --- | --- | --- | --- | --- |
| Solidarność, 1 / 2 / 3 pola | mniej o 1 / 2 / 3 | bez zmian | bez zmian | mniej o 1 / 2 / 3 | bez zmian |
| Równowaga | bez zmian | bez zmian | bez zmian | bez zmian | bez zmian |
| Bezwzględność, 1 / 2 / 3 pola | bez zmian | mniej o 1 / 2 / 3 | bez zmian | bez zmian | mniej o 1 / 2 / 3 |

Zmniejsza się też liczba kart. Przykład: 3 bohaterów, Bezwzględność 1:
czerwone 6, białe 5, zielone 6, czarne 6, niebieskie 5 — 28 kart.
Na skraju toru talia ma 24 / 34 / 44 / 54 karty dla 3 / 4 / 5 / 6 bohaterów.
To pierwsze liczby do ogrania; nie zmieniamy równocześnie kosztów akcji ani oporu.

Zmiana obowiązuje przy przygotowaniu NASTĘPNEJ walki lub konfrontacji.
Nie usuwamy kart z trwającej puli, oferty ani stosu. Wyłączone karty leżą osobno,
poza spalonymi/więzionymi/wygasłymi. Mana drain zbiera wszystkie strefy aktywnej
talii, ale nie przywraca kart wyłączonych postawą; bard nie może ich odzyskać.
Powrót ku Równowadze przywraca je przy następnym przygotowaniu.

## Misja 0

- Wóz: przed rozpoczęciem testu można wymusić zamianę z gospodarzem. Drużyna
  zostawia mu uszkodzony wóz, bierze sprawny i przepina własnego muła. Nie ma
  testu ani zmęczenia; krok ku Bezwzględności. Po rozpoczęciu testu pozostaje
  jego normalne rozstrzygnięcie, także po wyjściu do narracji.
- Pierwszy pokonany wieśniak: przyjęcie jednorazowego rozejmu kończy walkę
  i przesuwa ku Solidarności. Odmowa przesuwa ku Bezwzględności; bieżąca
  walka i jej drainy zachowują dawny skład talii.
- Wymuszenie, a potem rozejm przywracają Równowagę. Sam rozejm wyłącza
  czerwone/czarne w następnej konfrontacji.

To nie reputacja ani morale przeciwników. Pozostałe decyzje obecnie nie przesuwają
wskaźnika. Nie zmieniamy wcześniejszych nagród i konsekwencji tych gałęzi.

## Zapis i implementacja

`rules/party_ethos.py`: czysta reguła toru i zdarzeń.
`application/party_ethos.py`: flaga `campaign_party_ethos_v1`; przechodzi przez
zapis i istniejące przenoszenie flag kampanii między scenariuszami. Checkpoint
odtwarza także dawną postawę i historię zdarzeń. Starszy zapis bez flagi oznacza
Równowagę; nie naliczamy decyzji wstecz.
`rules/pooled_mana.py`: osobna strefa `excluded`, zachowanie liczby i kolorów
kart, aktualny skład `composition`, wielkość `total`. Stary zapis puli bez
`excluded` zachowuje pełen skład. Przygotowanie walki oraz Misji 0 używa flagi.
Ćwiczenia Poligonu pozostają neutralnymi, izolowanymi przykładami.

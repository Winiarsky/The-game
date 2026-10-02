# Relacje run i karty postaci v0.3

Aktualizacja: 01.10.2026. Status: zaakceptowana wersja wdrożona do gry,
UI, zapisu i adaptera LED.
Źródło kart: `content/print/rune_relations_v03/catalog.json`.
Nowe walki Misji 0 i swobodnej areny używają `rune_relations_v03`.
Trwające walki ze starszych zapisów zachowują poprzedni profil.

[Makieta walki](ui/prototype.html?scene=combat) ·
[Karty siedmiu postaci — 35 stron A4](../handouts/characters.pdf) ·
[Materiały do druku](../handouts/README.md) ·
[Okrąg relacji](ui/assets/rune-relations-circle-v03.png).

## Zasada wyboru mocy

Każda z 29 mocy ma jeden koszt i jeden sposób użycia. Jej dodatkowe efekty
wynikają z run zachowanych przez poprzednie działania drużyny. Ostatnia runa
określa legalne kontynuacje, a cała pamięć określa dostępne premie karty.
Zwykłe ataki i reakcje korzystają z własnych stanów, wyposażenia i pasywów;
same symbole nie przyznają ogólnych premii.

Pamięć zawiera maksymalnie trzy ostatnie wpisy, od najstarszego do najnowszego.
Duplikaty zajmują miejsca, ale obecność runy jest warunkiem logicznym:
kilka Grotów nie zwielokrotnia premii. Łańcuch może trwać dowolnie długo,
lecz jego pamięć przesuwa się wraz z kolejnymi mocami.

1. Przy pustej pamięci legalna zwykła moc wykonuje efekt podstawowy i zostawia
   własną runę. Nie wzmacnia się runą, którą właśnie dodaje.
2. Przy zgodności z ostatnią runą sprawdź warunki na pamięci sprzed działania.
   Zastosuj wszystkie pasujące premie karty. Dopiero po całym rozpatrzeniu
   dodaj nową runę i usuń najstarszy wpis, jeśli przekroczono trzy miejsca.
3. Przy braku zgodności zwykła moc wygasza starą pamięć przed działaniem,
   wykonuje efekt podstawowy i rozpoczyna nowy łańcuch. Podgląd uprzedza o tym
   przed wydaniem ładunków. Premie starej pamięci nie przechodzą do tej mocy.
4. Nielegalna deklaracja, zmiana celu i anulowanie podglądu nie pobierają kosztu.
   Potwierdzenie opłaca moc oraz jej budżety raz, przed rzutami i odzyskiem.
5. Pudło lub udana obrona przeciwnika nie zmienia sposobu kontynuacji.
   Koszt i runa legalnie użytej mocy pozostają rozliczone.

## Kierunkowe połączenia

| Ostatnia runa | Zwykłe kontynuacje |
| --- | --- |
| Wieża | Grot, Schody, Błysk |
| Grot | Klepsydra, Hak, Kielich |
| Schody | Grot, Oko, Błysk |
| Błysk | Wieża, Schody, Kielich |
| Hak | Schody, Oko, Klepsydra |
| Oko | Wieża, Grot, Węzeł |
| Kielich | Wieża, Błysk, Węzeł |
| Węzeł | Schody, Oko, Kielich |
| Klepsydra | Oko, Grot, Hak |

Po każdej runie można użyć Fali; po Fali można użyć każdej runy.
Trzy zwykłe kontynuacje nie oznaczają trzech legalnych mocy u każdego bohatera.
Znaczenie mają kolejność tur, zestawy kart, cel, zasoby i aktywne stany.
Przykładowo Brakka nie może ponownie aktywować trwającego Szału, a Lorian
nie ma zwykłej odpowiedzi na Wieżę. Niezgodna moc pozwala zmienić kierunek.

## Fala i późniejsze zdobycze

Fala jest runą Mglistego kroku Nimry, za 5 ładunków przed ewentualną skazą.
Przyjmuje dowolnego poprzednika i pozwala na dowolnego następcę. Zajmuje
jedno miejsce pamięci. Nie powiela runy i nie zastępuje symbolu wymaganego
przez premię albo finiszer. Jako pierwsza moc rozpoczyna pamięć samą Falą.

Strzała wichru Erynda używa teraz Schodów. Pozostałe zwykłe przypisania
zachowano. Spirala oznacza wspólne Skupienie, Gwiazda otwiera informacje.

Runy Rozwidlenie, Trójząb, Brama, Romb, Korona, Kotwica, Most, Klucz i Iskra
pozostają przyszłymi silniejszymi zdobyczami. W tej wersji nie mają startowych
mocy, kosztów ani dopisanych połączeń. Makieta pokazuje je jako rozwój;
nie używa ich do wyboru trybu, zapłaty ani podtrzymywania łańcucha.

## Finiszery i role postaci

Finiszer wymaga jednocześnie obu wskazanych run w starej pamięci oraz legalnego
przejścia z ostatniej runy do symbolu mocy. Nie można użyć go podstawowo przy
niespełnionym warunku. Po opłaceniu i całym rozpatrzeniu wygasza pamięć,
również po pudle. Jego symbol nie rozpoczyna następnego łańcucha.

| Bohater | Przygotowana moc | Koszt | Wymagane runy |
| --- | --- | ---: | --- |
| Brakka | Gniew runy, Grot | 8, A+S | Wieża i Błysk |
| Mira | Ostrze zmierzchu, Oko | 7, A+S | Hak i Schody |
| Nimra | Strefa ognia, Kielich | 8, S | Oko i Węzeł |
| Erynd | Bliźniacze groty, Kielich | 8, A+S | Oko i Węzeł |

Garran zachowuje Ostrze przełamania jako zwykłego producenta Grota. Bez tego
Grot występowałby tylko przy wygaszającym finiszerze Brakki. Dagna zachowuje
dostęp do wszystkich swoich mocy leczenia, a Lorian do wsparcia i odzysku.
Ich mocniejsze kombinacje wynikają z kilku jednocześnie pasujących premii.

Karty obejmują 51 warunkowych premii. Wszystkie ich warunki oraz wszystkie
cztery finiszery da się przygotować w legalnej pamięci trzech wpisów.
To sprawdzenie grafu; rzeczywista dostępność zależy dodatkowo od składu i tur.

## Zasoby, stany i granice tury

Start i maksimum: 20 ładunków na bohatera. Koszty kart wynoszą 3–8,
przed dopłatami skaz. Skupienie pod Spiralą zużywa specjalną, wygasza pamięć
od razu i odzyskuje 1k20 do maksimum. Odzysk klasowy pozostaje 1k4,
raz na bohatera na rundę; dwóch wyzwalaczy nie traktujemy jako dwóch limitów.
Pasyw Loriana zwraca 1 ładunek po legalnym podtrzymaniu cudzej runy,
raz we własnej turze, po opłaceniu i rozpatrzeniu mocy.

Jedna moc zużywa jedną specjalną. A+S zajmuje też atak, M+S cały ruch.
Szarża Garrana nadal wymaga pełnej, niewykorzystanej puli ruchu. Dodatkowy
ruch przyznany konkretną mocą nie tworzy nowego ogniwa.

Zwykły ruch, atak, przedmiot i reakcje nie przerywają pamięci w trakcie tury.
Zakończenie przytomnej tury bohatera bez mocy runicznej wygasza ją.
Tura wroga, koniec rundy i pominięcie tury nieprzytomnego bohatera nie wygaszają
łańcucha. Początek i koniec walki czyszczą pamięć.

Premie czasowe karty pozostają do własnego wydrukowanego terminu także
po wyładowaniu albo zerwaniu łańcucha. Podobne ponowne efekty tej samej mocy
nie sumują się. Tymczasowe PW i osłony nie odnawiają się na początku tury.
Hymn przechowuje wielkość przyznanej kości (k6 lub k8), źródło i pozostaje
do wykorzystania; limit to jeden niewykorzystany Hymn na bohatera.

## Dwa przykłady Garrana i Brakki

`Impuls/Wieża → Szał/Błysk → Szarża/Schody → Gniew/Grot`

Impuls zaczyna od podstawowego działania. Szał dostaje krótką ochronę
z Wieży. Szarża korzysta z Wieży (bez okazyjnych) i Błysku (−2 do obrony).
Gniew ma legalne wejście ze Schodów oraz obie wymagane runy: Wieżę i Błysk.
Przy trafieniu zadaje broń +3k6 gromowych i −2 KP celu. Szał nadal dodaje
swoje 1k6. Po całej akcji pamięć jest pusta, ale Szał i przyznane stany trwają.

`Impuls/Wieża → Pęd/Schody → Ostrze/Grot → Echo/Hak`

Pęd omija okazyjne dzięki Wieży. Ostrze korzysta ze Schodów (+1k6 magicznych)
i Wieży (+1 KP po ataku), po czym zachowuje Grot dla kolejnych bohaterów.
Echo jest legalną kontynuacją i działa podstawowo, gdy nie ma jego premii.

## Przegląd i odtwarzanie materiałów

Makieta ma osobny zapis `resonance-mock-v3` i stan wersji 3. Stare próby
v0.2 nie są automatycznie przeliczane. Galeria kart pozwala obejrzeć wszystkich
siedmiu bohaterów, również tych spoza wybranej drużyny. W podglądzie widać
koszt po skazie, sposób kontynuacji, uzyskane i brakujące premie oraz pamięć
po akcji. Interaktywny okrąg pokazuje połączenia wybranej runy.

Odbudowa danych mocka:
`PYTHONPATH=src .venv/bin/python scripts/build_resonance_mock.py`.
Odbudowa kart:
`PYTHONPATH=src .venv/bin/python scripts/build_rune_relations.py`.

Gra, wydruki i makieta odczytują ten sam katalog, kierunkowe połączenia
i słownik modyfikatorów. Właściwy silnik rozstrzyga kolejkę w Pythonie;
UI i adapter sprzętu korzystają z jego podglądu, bez własnych reguł.
Stan nowego profilu ma wersję 2, a zapis sesji schemat 35. Wczytanie
nie powtarza opłaty, rzutów ani skutków. Stary profil v0.2 jest zachowany
w tym samym silniku dla rozpoczętych walk, bez przeliczania pamięci.

Uruchomienie właściwej gry i symulatora:
`.venv/bin/python scripts/resonance_playtest.py --skip-setup`.
[Instrukcja prób](playtests/RESONANCE_RUNTIME_MANUAL.md) opisuje obsługę,
LED-y i przypadki do sprawdzenia przy stole. Ściąga UI i PDF pochodzi
z `text/sciaga_relacje_v03.json`; jej tabela relacji powstaje z katalogu.
Makieta HTML nadal ma osobny zapis i nie steruje sprzętem.

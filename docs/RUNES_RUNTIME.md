# Runy i reputacja — aplikacja, 22.09.2026

Aktualne źródło kart siedmiu postaci: `content/print/runes_v01/action_cards.json`.
Nowe rozgrywki Misji 0 używają run; trwające zapisy starego systemu zachowują swój stan.
Wydruki: `content/scenarios/misja_0_dzwon/print/runy_v01/index.html`.

## Panel i decyzje

Kolejność pól: ruch, atak, przedmiot, koniec tury, puste pole, 20 symboli,
puste pole, +, −, ✓, ↩. Gwiazda (24) jest niebieską informacją o bohaterze;
Klucz (23) pozostaje runą mocy. Ruch i cele wybiera się na polach figurek.
Podgląd nie wydaje zasobów. Zatwierdzenie świeci dopiero po legalnym wyborze.
Niedostępny atak jest wygaszony. Wyposażenie ustala się przed wyprawą.

## Runy w walce

Na początku walki aplikacja tasuje skończoną talię: po N kopii każdego z szesnastu
rodzajów używanych przez karty (Rozwidlenie, Wieża, Klepsydra, Trójząb, Brama,
Romb, Hak, Błysk, Oko, Schody, Korona, Węzeł, Grot, Kotwica, Kielich, Klucz). Odkrywa N+2 run. N to liczba bohaterów. Kolejne rundy nie dobierają run.
Moce związane z odzyskiem mają osobno opisane efekty.

Podstawowy koszt każdej mocy to 1 × symbol jej przycisku na planszy.
Pierwszy Szał pozostaje bezpłatny; kolejne aktywacje wymagają Rozwidlenia.
Wzmocnienia i podtrzymanie mają własne, jawne dopłaty. Gwiazda służy wyłącznie
informacji; nieużywane przez karty Spirala, Most i Fala nie trafiają do talii.
Zapisy rozpoczętych walk zachowują dotychczasową talię, ręce i kolejność kart;
brakujący symbol można opłacić dwiema wybranymi dowolnymi runami. Nowa talia
obowiązuje od następnej rozpoczętej walki.

Gracze po kolei klikają runy dla aktualnie wskazanej postaci. Jedno kliknięcie
przenosi jedną kopię; ↩ oddaje ostatnią niezatwierdzoną runę tej osoby.
✓ zamyka jej wybór. Limit ręki to 7. Reszta puli przechodzi kolejny obieg;
gdy wszyscy mają pełne ręce, reszta trafia na stos odrzuconych.

Tura: ruch + atak bronią albo przedmiot + jedna specjalna. Karta określa,
czy wymaga także niewykorzystanego ataku lub całego ruchu. Podstawowe działania
nie kosztują run. Moc wymaga wskazanej runy; brakującą podstawową runę mogą
zastąpić dwie dowolne. Można wybrać najwyżej jedno z maksymalnie trzech
wzmocnień. Konkretnej runy wzmocnienia nie zastępuje para dowolnych.
Koszt pobierany jest przy zatwierdzeniu. Zwykły atak okazyjny jest bezpłatny
i zużywa reakcję. Reakcje specjalne mają koszt z karty.

Bastion tworzy stacjonarny krąg na polu rzucenia. Pierwsza kolejna tura
Garrana nie wymaga opłaty; od drugiej podtrzymanie kosztuje jedną wybraną
dowolną runę albo krąg wygasa. Podtrzymanie przywraca +1 KP i promień 2 pól.
Ręce, talia, odrzucone karty i przydział są zapisywane.

Zasłona dymna Miry tworzy stacjonarny obszar 3×3 ze środkiem na jej polu.
Pozwala ukrywać się w tym obszarze i daje przewagę do testu Ukrycia wszystkim
postaciom wewnątrz, także wrogom. Nie daje automatycznego ukrycia ani ruchu.
Ukrycie pozostaje osobną akcją. Roboczo dym trwa do końca następnej tury Miry,
aby mogła skorzystać z niego przy limicie jednej specjalnej na turę.

Strojenie Loriana wymaga runy pozostałej po pełnej zapłacie; gracz wybiera,
którą wymienić. Dowolne koszty, zastępstwo bazowej runy, podtrzymanie i koszt
partnera Kontrataku mają osobny krok wyboru konkretnych run przed pobraniem
zasobów. Odzysk Loriana łączy dwa wcześniejsze odzyski, działa raz na walkę
i nie odzyskuje własnej opłaty. Gracz wskazuje runy ze stosu sprzed zapłaty.

[Aktualne korekty kart](RUNE_BALANCE_V02.md) wdrażają wnioski z
[pierwotnego audytu 66 kart](HERO_ACTION_REVIEW.md). Po połączeniu odzysków
Lorian ma osiem kart, pozostali bez zmiany liczby; cały zestaw ma 65 kart.
Pierwszy Szał Brakki jest bez run, Zachowanie życia raz na walkę,
Podwójny strzał zajmuje A+S. Szczegóły pozostałych zmian opisuje dokument korekt.

## Podstawowy ekwipunek i Ukrycie Miry

Nowy zestaw startowy ma jedną wyposażoną broń, dotychczasowy pancerz,
tarczę tam, gdzie należy do zestawu, oraz osobiste przedmioty. Usunięto
zapasowe bronie i amunicję do nich. Brakka i Nimra zachowują ochronę bez
pancerza i dotychczasową KP. Druk i nowe gry używają tego samego zestawu;
nie usuwamy przedmiotów z istniejących zapisów i rozwiniętych postaci.

Mira nadal może próbować Ukrycia na otwartym polu, jeżeli nie sąsiaduje
z żywym wrogiem. Dym znosi ograniczenie sąsiedztwa i daje przewagę.
Pozostają wymagania dostępnej specjalnej, opłaty Rozwidleniem i stanów
pozwalających się ukryć. Test jest osobny względem każdego obserwatora.
Udana próba przeciw jednemu przeciwnikowi nie ukrywa Miry przed pozostałymi.
W trybie Ukrycia Rozwidlenie otwiera podgląd dobrowolnego ujawnienia;
✓ kończy Ukrycie bez kosztu run i akcji, ↩ pozostawia je aktywne.

Mistrzyni ostrzy wymaga wyposażonej broni i Ukrycia przed wskazanym celem:
obrażenia broni +1k6, z osobistą flanką dodatkowe +1k6. Flanka sama nie
spełnia wymagań. Atak z cienia nie dolicza drugi raz tych premii do tej
mocy. Wzmocnienia z karty pozostają opcjonalne. Premia za flankę zostaje
zachowana w rzucie obrażeń po ujawnieniu Miry przez atak. Zarówno ta moc,
jak i Wyrok z cienia wygaszają pole celu, który widzi Mirę.

## Konfrontacje i reputacja

Nessa i wóz mają jedną kolejkę drużyny. Wybór podejścia otwiera test k20,
bez drugiego rzutu na wpływ. Zwykły sukces przesuwa postęp o 1, porażka o 0,
naturalne 20 o 2, naturalne 1 cofa o 1. Tor zaczyna na 0. Zejście poniżej −1
kończy konfrontację pogorszeniem; dotarcie do N kończy ją najwyższym wynikiem.
Po ostatnim graczu obowiązuje osiągnięty wynik. Pełny sukces zaczyna się od
zaokrąglonego w górę N/2; 1 oznacza sukces z komplikacją, a N−1 daje dodatkową
korzyść przy więcej niż trzech bohaterach. Nowe testy mają bazowo ST 14.

Wspólna reputacja zaczyna na 20 i pozostaje między scenami. Po rzucie społecznym
można wybrać jedną opcję: +1 za 1 reputacji, +5 za 3 albo dodatkową k20
z zachowaniem wyższego naturalnego wyniku za 5. Premie nie kumulują się.
Koszt liczbowej premii pobierany jest z zatwierdzeniem wyniku; dodatkowa kość
jest opłacana przed rzutem i nie daje zwrotu po jego poznaniu. Naturalnej 1
nie naprawia premia liczbowa. Fizyczne próby wydobycia wozu nie używają reputacji.

Wymuszona zamiana wozu wymaga bieżącej reputacji co najmniej 20 i kosztuje 3;
zachowuje konsekwencję moralną scenariusza. Nagroda za ukończenie Misji 0 wynosi
roboczo +5, jest konfigurowalna i przyznawana jednokrotnie. Dokładne rabaty
sklepowe oraz dalsze progi dialogów pozostają decyzją projektową.

## Test manualny

Log `exploration_ui_4cd122c1af.jsonl` pokazał działające wybieranie ruchu,
a następnie podświetlony atak Miry bez legalnego celu. Nie znaleziono błędów
transmisji LED. Regresje sprawdzają zgodność dostępności, maski skanera i diod,
wybór pola przed zatwierdzeniem, cofanie przydziału i powrót z informacji
bez utraty akcji ani celu. Symulator nie zastępuje kontroli wydruku i czujników
na fizycznym egzemplarzu planszy.

## Skazy i porządkowanie profili — 23.09.2026

Opisy skaz wariantu runicznego pochodzą z `content/print/runes_v01/flaws.json`.
Ten sam tekst trafia do cech postaci, podglądu pod Gwiazdą, makiety i wydruków.
Nie korzystamy w nich ze spalania kart, ładunku ani pasywów kolorów many.

- Garran: rozpoczęcie tury przy wrogu połowi zwykły ruch; bez nowej dopłaty.
- Brakka: tura bez ofensywy kończy Szał; bez nowej dopłaty.
- Mira: ukrycie utrudnia obrony i testy reakcji; zachowany wyjątek ukrywania
  na otwartym polu bez sąsiadującego wroga i rozliczanie widoczności osobno dla celów.
- Dagna: żywy sąsiad z mniej niż połową PW oznacza +1 dowolną runę do każdej
  ofensywnej mocy. Leczenie i zwykły atak nie otrzymują dopłaty.
- Lorian: w drużynie wieloosobowej brak przytomnego sojusznika do 2 pól oznacza
  +1 dowolną runę do każdej płatnej mocy, również reakcji. Samotna gra bez kary.
- Nimra: druga z rzędu taka sama płatna moc kosztuje dodatkowo 1 dowolną runę,
  trzecia i dalsze po 2. Inna płatna moc, także reakcja, rozpoczyna nową serię.
  Podgląd i anulowanie nie zmieniają serii. Zwykłe akcje jej nie przerywają.
  Seria pozostaje między turami i w zapisie walki, zaczyna od zera w nowej walce.
- Erynd: płatny strzał w cel sąsiadujący z innym przytomnym bohaterem kosztuje
  +1 dowolną runę, najwyżej raz na całą moc. Jeżeli warunek pojawia się dopiero
  przy drugim strzale, wybór dopłaty następuje przed jego rzutem; bez ponownego
  zużycia akcji. Zwykłe ataki i ataki okazyjne pozostają darmowe.

To robocze dostosowanie czterech dawnych kar spalania do kosztów run.
Wybór dowolnej runy jest jawny i odwracalny do zatwierdzenia; aplikacja nie
wybiera za gracza. Wymagane symbole pozostają zarezerwowane. Brak zasobów
blokuje płatność, a nie pobiera części kosztu. Podtrzymanie aury nie jest nową mocą.

Wczytanie zapisu runicznego odświeża opisy cech i usuwa wycofane przyznania:
Wielkie strojenie Loriana, Odpędzanie nieumarłych Dagny, dawne dodatkowe akcje
Garrana/Miry/Loriana oraz samodzielną Metamagię Nimry. Pozostają warianty jej
kart i uprawnienie do katalogu czarów. Alias Zachowania życia ma pełny aktualny
opis, w tym limit raz na walkę. Dawne znaczniki Echa nie wracają do podglądu.
Aktualizacja nie ustawia ponownie PW, zasobów ani wyposażenia. Starsze zapisy
bez profilu runicznego zachowują dawny system.

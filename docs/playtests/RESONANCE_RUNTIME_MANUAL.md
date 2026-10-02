# Test ręczny: relacje run v0.3

Wersja 01.10.2026. To silnik Python i ekran `/play`. Nowe walki Misji 0
oraz swobodnej areny korzystają z `rune_relations_v03`. Rozpoczęte walki
wczytane ze starszych zapisów zachowują swoje zasady; zapis wersji 34
z Rezonansem v0.2 pozostaje w profilu `rune_charges_v02`. Prowadzone lekcje
areny i historyczne profile zachowują dotychczasowe działanie.
Do sprawdzenia relacji run rozpocznij nowe starcie.

Źródło kart i warunków: `content/print/rune_relations_v03/catalog.json`.
Pełne zasady: [RUNE_RELATIONS_V03.md](../RUNE_RELATIONS_V03.md).
Ściąga na ekranie jest wspólna z materiałami do druku:
`content/scenarios/misja_0_dzwon/text/sciaga_relacje_v03.json`.

## Uruchomienie

Z katalogu projektu:

```bash
.venv/bin/python scripts/resonance_playtest.py
```

Gra: <http://127.0.0.1:5201/play>; plansza w drugim oknie:
<http://127.0.0.1:5001>. Skrypt uruchamia oba serwery i pomija fabułę,
ale pozostawia rozstawienie figurek i inicjatywę. Zaczynasz bez zmęczenia
z drogi. Domyślna drużyna: Garran, Brakka, Mira, Dagna, Lorian, Nimra.
Każde uruchomienie dostaje oddzielny katalog `/tmp/rune-relations-v03-*`,
wypisany w terminalu. Ctrl+C kończy serwery; katalog testu pozostaje
z zapisami i obserwacjami.

Szybki początek samej walki w symulatorze:

```bash
.venv/bin/python scripts/resonance_playtest.py --skip-setup
```

Osobna próba z Eryndem:

```bash
.venv/bin/python scripts/resonance_playtest.py --heroes garran mira erynd
```

Zajęte porty zmień przez `--port 5202 --board-port 5002`.
`--check` sprawdza przygotowanie sesji bez uruchamiania serwerów i sprzętu.

## Fizyczna plansza

Podaj rzeczywisty port szeregowy oraz adres WLED:

```bash
.venv/bin/python scripts/resonance_playtest.py --hardware \
  --serial-port /dev/ttyACM0 --wled-url http://ADRES_TWOJEGO_WLED
```

Ten tryb wymaga ręcznego rozstawienia figurek. Weryfikacja automatyczna
korzysta z symulatora i połączenia testowego; fizyczne serial/WLED pozostają
do sprawdzenia przy stole.

## Obsługa i światła

- Wybierz runę mocy, potem cel lub pole i zatwierdź ✓. Moc ma jeden koszt.
  Podgląd pokazuje rozpoczęcie, podtrzymanie, przerwanie albo wyładowanie,
  a także premie aktywne przed dodaniem jej runy. ↩ anuluje podgląd bez kosztu.
- Złota runa oznacza dostępną moc. Pomarańczowa uprzedza, że moc rozpocznie
  nowy łańcuch. Niedostępna moc, w tym wyładowanie bez wymaganych run,
  pozostaje wygaszona. Wybrana runa świeci na biało.
- Złote pola pokazują legalne cele; wybrana figurka jest biała. Zakres ruchu,
  ścieżka i pole docelowe bohatera są niebieskie. Ścieżka przeciwnika jest
  czerwona; przy jego ataku okazyjnym wyróżniony jest reagujący przeciwnik.
  Obszar pozostaje pomarańczowy, a pomijana postać turkusowa.
- Wynik gracza wpisuj osobno dla każdej fizycznie rzuconej kości przez +/−,
  zatwierdzając ✓. Dotyczy to także przewagi, 2k6 i dodatkowych kości karty.
  +/− podczas podglądu mocy nie wybierają wariantu kosztu.
- Przeciwnik: zapowiedź → ✓ → automatyczny rzut z widocznym wynikiem → ✓.
  Ruch czeka na rozpatrzenie reakcji i nie losuje ponownie przy odświeżeniu.
- Niebieska Gwiazda otwiera informacje. Wskaż postać na planszy lub
  w kolejce; +/− zmieniają strony, ↩ wraca do zachowanej decyzji.
- Dodatkowy ruch po Całunie/Impulsie oraz leczenie sojusznika z Żaru odnowy
  rozpatrz przed zamknięciem mocy. Dopiero potem jej runa trafia do pamięci.
- Nieużywane runy rozwoju pozostają ciemne i nie uruchamiają dawnych wyborów.

## Próby wspólnej mechaniki

- [ ] Nowa walka zaczyna się z pustą pamięcią i 20/20 ładunków na bohatera.
  Każda moc ma jeden koszt 3–8, powiększony tylko przez swoją skazę.
- [ ] Pusta pamięć daje podstawowe działanie. Własna runa nie wzmacnia
  właśnie wykonywanej mocy; trafia do pamięci po wszystkich jej skutkach.
- [ ] Ostatnia runa określa legalne połączenie, a trzy poprzednie wpisy
  warunki premii. Czwarta runa usuwa najstarszą dopiero po rozpatrzeniu mocy.
- [ ] Kilka takich samych symboli zajmuje miejsca, ale nie mnoży bonusu.
  Zwykły atak i reakcja nie dostają ogólnych premii z samych symboli.
- [ ] Moc niezgodna z ostatnią runą uprzedza w podglądzie, wygasza starą
  pamięć przed efektami i kończy się jednym nowym wpisem. Nie dziedziczy
  bonusów starego łańcucha.
- [ ] Podgląd, zmiana celu i ↩ niczego nie opłacają. ✓ pobiera koszt i budżety
  raz; pudło lub udana obrona przeciwnika nie cofają płatności ani wpisu runy.
- [ ] Skupienie wygasza pamięć od razu i daje 1k20 ładunków, maksymalnie 20.
  Koniec przytomnej tury bez mocy runicznej również wygasza łańcuch.
- [ ] Tury wrogów, zmiana rundy i nieprzytomny bohater zachowują pamięć.
  Czasowe efekty nadal wygasają w swoim wskazanym momencie inicjatywy.
- [ ] Fala jest wyłącznie pod Mglistym krokiem Nimry. Łączy się z każdą runą
  w obu kierunkach, zajmuje jedno miejsce i nie zastępuje wymaganych symboli.
- [ ] Odzysk klasowy 1k4 jest dobrowolny, raz na bohatera na rundę.
  Pominięcie i pełna pula nie zużywają możliwości odzysku.
- [ ] Premie KP, tymczasowe PW, osłona i inne stany z kart przeżywają koniec
  Rezonansu oraz wygasają według czasu podanego na karcie.

## Próby postaci i wyładowań

- [ ] Garran: Żywa osłona sąsiadów +1 KP; Impuls z Okiem daje przewagę,
  a ze Schodami dodatkowy krok dopiero po wygranej i odrzuceniu celu.
  Ostrze z Wieżą daje +1 KP także po pudle. Żar z Kielichem pozwala wybrać
  jednego sąsiedniego sojusznika i rozpatrzyć osobne leczenie 1k6.
- [ ] Brakka: Szał, odporność na trzy fizyczne typy obrażeń i dwie dodatkowe
  kości broni na krytyku. Gniew runy wymaga Wieży + Błysku oraz legalnej
  kontynuacji Grotem. Obecność pary sama nie omija wymogu ostatniej runy.
  Cios zadaje dodatkowe 3k6 gromowych i wygasza pamięć także przy pudle.
- [ ] Mira: Całun ze Schodami daje dodatkowy ruch po udanym ukryciu,
  z Grotem odejmuje 2 Percepcji podczas próby, z oboma daje również przewagę.
  Ostrze zmierzchu wymaga ukrycia przed celem, Haka + Schodów i legalnego Oka;
  dodatkowe 3k6 oraz ujawnienie rozpatrz przed wygaszeniem pamięci.
- [ ] Dagna: Pieczęć z Klepsydrą daje +2 do ataków/obron zamiast +1.
  Tchnienie życia z Kielichem dodaje 1k6 leczenia; Krąg odnowy z Węzłem daje własne
  czasowe PW. Pasyw +2 leczenia innemu bohaterowi rozlicz raz na moc.
- [ ] Lorian: +1 ładunek dopiero po opłaconej legalnej kontynuacji runy
  innego bohatera. Hymn z Klepsydrą jest 1k8; zwykły 1k6. Kość pozostaje
  do wykorzystania, najwyżej jedna na postaci, także między walkami.
  Pieśń przejścia korzysta z legalnej drogi i nie wywołuje okazyjnych.
- [ ] Nimra: każdy pocisk jest osobnym trafieniem; Grot dodaje 1k4 tylko
  pierwszemu. Tarcza z Wieżą daje 3 pkt osłony, która omija psychiczne;
  z Okiem daje łącznie +3 KP. Strefa ognia wymaga Oka + Węzła i legalnego
  Kielicha, daje 4k6 ognia i po całym obszarze wygasza pamięć.
- [ ] Erynd: Piętno z Okiem daje przewagę w najbliższym ataku; Więzy
  korzeni z Okiem w tym strzale. Strzała wichru używa Schodów.
  Bliźniacze groty wymaga Oka + Węzła oraz legalnego Kielicha; oba ataki
  i ich kości rozpatrz przed wygaszeniem. Amunicja i skaza są rozliczane raz.
- [ ] Wszystkie cztery wyładowania: brak pary lub nielegalna ostatnia runa
  blokują wybór; anulowanie nie kosztuje; zatwierdzone pudło zużywa koszt
  i kończy łańcuch dopiero po pełnym rozstrzygnięciu.

Dla próby współpracy trzyosobowej ustaw kolejność Garran → Brakka → Mira.
Garran: Impuls (Wieża), Brakka: Pęd gromu (Schody), Mira: Całun (Błysk),
w następnej rundzie Garran: Impuls (Wieża). Przed turą Brakki pamięć to
Schody → Błysk → Wieża: Gniew runy ma wymagane symbole i legalną
kontynuację Grotem. Cele i skutki ruchu nadal muszą być legalne na planszy.

## Zapis i przerwane decyzje

- [ ] Zapis/wczytanie po pierwszej kości przewagi lub pierwszej kości obrażeń
  zachowuje zaakceptowane wyniki i otwiera dokładnie następną kość.
- [ ] Zapis/wczytanie przed wyborem oraz po wyborze dodatkowego ruchu,
  odrzucenia albo leczenia z Żaru nie przyznaje efektów ponownie.
- [ ] Wczytanie podczas okazyjnego i na ekranie wyniku przeciwnika nie
  losuje nowych wyników, nie pobiera kosztu ani nie przesuwa kolejki.
- [ ] Wczytanie zamyka poprzednie oczekiwanie planszy. Stare kliknięcie
  ani stara rewizja skanu nie wykonują przywróconej decyzji.
- [ ] Po zakończeniu starcia wraca właściwy etap misji. Hymn zachowuje swój
  rozmiar 1k6/1k8; chwilowe premie nie przechodzą do nowego starcia.
- [ ] Wczytany zapis wersji 34 z rozpoczętą walką v0.2 pozostaje w v0.2,
  razem z dawną pamięcią i oczekującą kolejką. Kolejne nowe starcie używa v0.3.

Zapis sesji ma schemat 35; `CombatState.resonance` dla nowych walk ma
wersję 2 i jawny profil `rune_relations_v03`. Walidacja sprawdza uczestników,
pamięć, wymagania opłaconej mocy i zapamiętane modyfikatory przed przywróceniem.
Odczyt UI i zapis nie wykonują kroków kolejki ani rzutów. Panel w kolumnie 19
nie jest celem ruchu, ataku ani obszaru.

Automatyczne testy obejmują 29 mocy oraz wykonanie wszystkich 51 premii kart,
zapis przerwanych decyzji i tłumaczenie sygnałów LED na połączeniu testowym.
Balans, czytelność świateł, ustawianie figurek i opóźnienia fizycznego sprzętu
należy sprawdzić przy stole według powyższej listy.

## Weryfikacja wdrożenia — 01.10.2026

282 przypadki przeszły w oddzielnych, serialnych wywołaniach
`scripts/safe_pytest.sh`, każde z timeoutem:

| Plik testów | Przypadki |
| --- | --- |
| `tests/unit/test_rune_relation_catalog.py` | 13 |
| `tests/unit/test_rune_relations_combat.py` | 62 |
| `tests/unit/test_rune_relation_effects.py` | 52 |
| `tests/unit/test_resonance_presentation.py` | 8 |
| `tests/integration/test_resonance_session.py` | 16 |
| `tests/hardware/test_resonance_feedback.py` | 3 |
| `tests/integration/test_resonance_browser.py` | 3 |
| `tests/unit/test_session_snapshot.py` | 64 |
| `tests/unit/test_resonance_combat.py` — regresja v02 | 60 |
| `tests/unit/test_resonance_mock.py::test_generated_mock_data_matches_current_cards` | 1 |

Chrome sprawdził 1366×768, 1131×720 i 390×844, wszystkie 29 podglądów,
stronicowanie premii i fizyczne sterowanie. Wydruki: wszystkie siedem
zestawów po 5 stron, komplet 35 stron, ściąga 3 strony i znaczniki 1 strona;
walidacja nie wykazała przepełnień. Sprawdzono też wizualnie strony ściągi.

Launcher przeszedł przygotowanie sześciu bohaterów oraz osobnej drużyny
z Eryndem. Rzeczywisty Flask i lokalny symulator odpowiedziały przez HTTP;
aktualny PDF został pobrany, wybrana Spirala dostała białą diodę,
anulowanie nie pobrało zasobów, a Ctrl+C zamknęło oba serwery.
Compile i `git diff --check` przeszły. Nie uruchamiano ogólnej pełnej suity
projektu ani prób na fizycznym serial/WLED.

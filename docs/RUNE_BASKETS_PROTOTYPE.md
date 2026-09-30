# Osobiste koszyki run — prototyp v0.1

Źródło zasad: [system_run_v0.1.md](../system_run_v0.1.md).
Zakres: siedem postaci, karty i planszetki do druku oraz
[klikalna makieta](ui/rune-baskets.html) do sprawdzenia sterowania.
Historyczny opis makiety. Aktualne wdrożenie działającej gry i późniejsze
ustalenia użytkownika opisuje [Koszyki w runtime](RUNE_BASKETS_RUNTIME.md);
mają pierwszeństwo przed poniższymi propozycjami.

## Cztery koszyki

Każdy bohater ma cztery osobiste koszyki. Pojemność oznacza liczbę miejsc
na runy danej kategorii. Każde miejsce jest naładowane konkretnym symbolem
albo rozładowane. Zużycie nie zmienia kategorii ani właściciela miejsca.
Nie ma wspólnej talii, stosu odrzuconych, doboru N+2 ani limitu ręki 7.

| Kategoria | k4 = 1 | k4 = 2 | k4 = 3 | k4 = 4 |
| --- | --- | --- | --- | --- |
| Ofensywa | Grot | Hak | Trójząb | Błysk |
| Obrona | Wieża | Kotwica | Brama | Węzeł |
| Mobilność | Oko | Schody | Rozwidlenie | Klepsydra |
| Aura | Korona | Kielich | Klucz | Romb |

Przed walką gracz wybiera symbole, w tym powtórzenia. Przygotowany zestaw
startowy jest propozycją do zmiany, nie wynikiem losowania. W walce każde
ładowanie wymaga osobnego fizycznego rzutu k4; wybierana jest kategoria,
a rzut określa symbol. Nie można przekroczyć pojemności koszyka.

| Bohater | Ofensywa | Obrona | Mobilność | Aura | Źródło pojemności |
| --- | ---: | ---: | ---: | ---: | --- |
| Garran | 2 | 4 | 1 | 2 | Dokument użytkownika |
| Brakka | 4 | 1 | 3 | 1 | Dokument użytkownika |
| Mira | 3 | 1 | 4 | 1 | Dokument użytkownika |
| Dagna | 1 | 2 | 1 | 4 | Roboczo do ogrania |
| Lorian | 1 | 2 | 2 | 4 | Dokument użytkownika |
| Nimra | 3 | 1 | 2 | 3 | Roboczo do ogrania |
| Erynd | 4 | 1 | 3 | 1 | Roboczo do ogrania |

## Przyciski i płatność

Przycisk mocy jest stały i niezależny od kategorii kosztu. Uderzenie tarczą
Garrana nadal wybiera Kotwica; koszt to jedna własna Ofensywa. Oko jest
opcjonalnym rezonansem Mobilności zwiększającym odepchnięcie.

Przebieg: **przycisk mocy → pole celu → własna runa kosztu → opcjonalny
rezonans → ✓**. Jeżeli istnieje tylko jeden rodzaj legalnej runy kosztu,
można zaznaczyć go automatycznie. Ostateczna płatność nadal czeka na ✓.
↩ cofa wybór przed zatwierdzeniem. Sam podgląd nie zużywa run ani akcji.

Każda moc kosztuje jedną własną runę swojej kategorii. Jeden rezonans
wymaga dokładnego symbolu z innej kategorii. Sojusznik nie płaci podstawy.
Pomocnik do trzech pól może opłacić rezonans własną runą i reakcją.
Własny rezonans nie wymaga reakcji. Koszt wszystkich uczestników oraz
budżet działania rozlicza się razem, przed rzutem rozstrzygającym moc.
Pudło nie zwraca run. Powtórne zatwierdzenie nie pobiera kosztu ponownie.

## Doprecyzowania do pierwszego testu

- Skupienie kosztuje S i ładuje do dwóch własnych rozładowanych miejsc.
  Można wybrać oba w tej samej kategorii; przy jednym rozładowanym miejscu
  ładuje się jedno. Brak rozładowanych miejsc blokuje Skupienie.
- Warunki regeneracji mają limit raz na rundę dla każdego warunku osobno.
  Pierwsze zdarzenie zużywa limit również przy pełnym koszyku. Wtedy nie
  wykonuje się rzutu ani nie przechowuje ładowania na później.
  Regeneracja nie uruchamia samoczynnie kolejnej regeneracji.
- Dla próby zasięg wsparcia liczymy jako maksymalną różnicę współrzędnych
  (przekątna to jedno pole). Plansza testowa nie ma przeszkód.
- W prototypie reakcje wracają na początku nowej rundy, zgodnie z przykładem
  z rozdziału 19 dokumentu. To świadomie opisany wariant do ogrania;
  obecny runtime odnawia reakcję na początku własnej tury.
- Zachowujemy budżety S/R/A+S/M+S/M+A+S i jawne limity raz na walkę.
  Nowy profil każdą moc opłaca kategorią, również pierwsze użycie Szału.
- Kategorie mocy, konkretne rezonanse, skazy oraz doprecyzowania regeneracji
  wszystkich bohaterów są roboczą adaptacją kart do nowego systemu.
  Zasadzki i rozwój postaci pozostają późniejszymi wariantami z dokumentu.

## Wspólne źródła i odbudowa

- `content/print/rune_baskets_v01/catalog.json`: kategorie, koszyki,
  przygotowanie, regeneracja, skazy i wszystkie karty siedmiu bohaterów.
- `src/dnd_board_game/scenarios/rune_basket_catalog.py`: odczyt i walidacja.
- `scripts/build_rune_baskets.py`: dane makiety oraz wydruki.
- `docs/ui/rune-baskets-data.js`: wygenerowany katalog dla przeglądarki.
- `docs/ui/rune-baskets.html`, `.js`, `.css`: samodzielna makieta.
- `content/scenarios/misja_0_dzwon/print/runy_koszyki_v01/`: materiały do druku.

Biografie, portrety, bazowe statystyki i wyposażenie pochodzą z istniejących
postaci. Koszty i opisy nowego wariantu pochodzą wyłącznie z nowego katalogu.
Wymiary wycinanek pozostają: zdolności 60 × 54 mm, sprzęt 60 × 42 mm.

## Próba przy stole

Sprawdzić Uderzenie tarczą z własnym Okiem i Okiem pomocnika, anulowanie
przed płatnością, wyczerpanie pojedynczego koszyka, Skupienie i klasowe
ładowanie k4. Następnie przejść całą rundę i porównać koszt wsparcia
z zachowaniem reakcji do obrony. Ogranie ma ocenić liczbę naciśnięć,
czytelność przycisk/koszt oraz dostępność rezonansów.

Makieta służy do sprawdzenia przepływu decyzji i ekonomii zasobów.
Nie zastępuje pełnego silnika rozstrzygania D&D ani fizycznego adaptera planszy.

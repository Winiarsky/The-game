# Walka: makieta relacji run v0.3

Aktualizacja: 01.10.2026. [Otwórz makietę](prototype.html?scene=combat).
[Karty wszystkich postaci](../../handouts/characters.pdf)
· [Pełne zasady](../RUNE_RELATIONS_V03.md).

To klikalny materiał do przeglądu kart i UI. Zaakceptowana wersja v0.3
działa też we właściwej grze; [uruchomienie](../playtests/RESONANCE_RUNTIME_MANUAL.md).
Makieta nie wywołuje Flask, czujników ani LED. Rozmowy,
reputacja, wyprawa i eksploracja zachowują dotychczasowy przebieg.

## Jak ograć

1. Otwórz `prototype.html?scene=combat`. Bohaterowie zaczynają z 20 ładunkami.
   Rozwiń panel testowy, aby wybrać skład i rozpocząć świeżą próbę.
2. Wybierz symbol mocy na dolnym panelu. Każda moc ma jeden koszt i działanie
   podstawowe. Podgląd pokazuje dopłatę skazy, premie z obecnej pamięci,
   brakujące warunki oraz pamięć po całej akcji.
3. Wybierz cel w **Symulatorze pól**. Złote pola są legalne, niebieskie
   pokazują drogę i przyszłą pozycję. Kliknięcie zastępuje sygnał planszy.
4. Sprawdź, czy moc rozpoczyna, podtrzymuje lub resetuje łańcuch.
   Wyładowanie pozostaje zablokowane bez obu wymaganych run i legalnego wejścia.
   ✓ opłaca i uruchamia moc; ↩ przed potwierdzeniem anuluje bez kosztu.
5. Dla bohaterów podawaj wynik jednej fizycznej kości naraz, bez modyfikatora.
   +/− zmienia wynik, ✓ zatwierdza i pokazuje następną kość. Dotyczy to także
   przewagi, utrudnienia i pul obrażeń. Skutki następują po ostatniej kości.
6. Za przeciwników rzuca aplikacja dopiero po ✓. Przy okazyjnym najpierw
   pojawia się zapowiedź i podświetlenie atakującego; po rzucie pełny wynik.
   Kolejne ✓ wznawia ruch lub pokazuje następną reakcję. Przy 0 PW ruch ustaje.
7. Dokończ obrony, obrażenia, wybory przesunięcia, dodatkowego celu i odzysku.
   Po zapłacie cofnięcie nie zwraca zasobów.

Gwiazda pokazuje statystyki, zasoby, stany, pasyw, skazę i wyposażenie,
bez zmiany podglądu. W spoczynku +/− przegląda uczestników. Panel testowy
zawiera galerię wszystkich siedmiu postaci, także spoza wybranego składu,
oraz klikalny okrąg połączeń. Wybierz symbol, aby zobaczyć jego następców.

**Zapisz próbę / Wczytaj próbę** używa osobnego klucza `resonance-mock-v3`.
Zapis obejmuje opłaconą akcję, kolejkę decyzji, zatwierdzone kości, Hymny,
pamięć i czasowe efekty kart. Wczytanie nie losuje ponownie ani nie powtarza
skutków. Próby v0.2 nie są przeliczane na nowe zasady.

## Co się zmieniło

- Pamięć obejmuje trzy ostatnie wpisy. Ostatni określa kierunkową kontynuację;
  obecność symboli w całej pamięci spełnia warunki kart. Duplikaty nie mnożą premii.
- Premie sprawdza się przed dodaniem własnej runy. Dopisywanie i przesunięcie
  pamięci następuje po całej mocy, również po pudle.
- Niezgodna zwykła moc czyści pamięć przed podstawowym działaniem i zaczyna
  własny łańcuch. Podgląd uprzedza o utracie przygotowania.
- Cztery wyładowania mają koszt i twarde warunki. Po całej akcji wygaszają
  pamięć, również po pudle, bez dodawania własnego symbolu.
- Fala występuje tylko u Nimry: przyjmuje każdego poprzednika i następcę,
  zajmuje miejsce pamięci, bez kopiowania i zastępowania warunków.
  Strzała wichru Erynda korzysta ze Schodów.
- Wszystkie dodatkowe efekty opisano na kartach. Same runy nie dają globalnych
  premii do KP, obrażeń, ruchu, leczenia ani reakcji. Czasowe efekty kart
  trwają do własnego terminu także po zerwaniu pamięci.
- Koszty wynoszą 3–8 przed skazami. Skupienie zużywa S, natychmiast kończy
  pamięć i odzyskuje 1k20 do maksimum. Odzysk klasowy: 1k4 raz na rundę.
- Koniec przytomnej tury bohatera bez mocy runicznej kończy pamięć.
  Tury wrogów, granica rundy i pominięcie nieprzytomnego nie kończą jej.

Dziewięć nieużywanych run mocy pokazano jako przyszłe silniejsze zdobycze.
Spirala/Skupienie i Gwiazda/informacje pozostają przyciskami sterowania.

## Zachowane zachowania i granice

Makieta obejmuje 29 mocy, pasywy i skazy, budżety S / A+S / M+S, reakcje,
osłony, ukrycie per obserwator, Szał i krytyk Brakki, obszary Nimry 3×3,
wybór pominięcia celu, Hymn po k20 i kolejki przesunięć. Hymn przechowuje
przyznaną kość k6 lub k8, trwa do wykorzystania i ma limit jeden na bohatera.
Obrażenia psychiczne omijają osłonę Tarczy splotu. Leczenie jej nie odnawia.

Arena 12×10 i trzech wrogów są przykładem. Kolejność jest stała: wybrani
bohaterowie, potem wrogowie. Drogi uwzględniają zajęte pola, blokady, narożniki
i przykładowy trudny teren; widoczność jest uproszczona. Nie ma AI wrogów,
testów śmierci, kampanijnego ekwipunku ani zewnętrznych obrażeń okresowych.
Powalony wstaje na początku swojej następnej tury, tracąc cały ruch.
To materiał do oceny wyborów, kosztów i przepływu obok właściwego silnika.

## Pliki i odtwarzanie

- `resonance-data.js`: wygenerowane dane osobnego katalogu v0.3 i statystyki.
- `resonance-model.js`: deterministyczna symulacja JS z serializowalną kolejką;
  kości wrogów dostarcza adapter. Nie importować do właściwego silnika Python.
- `resonance-prototype.js` / `.css`: prezentacja i obsługa panelu.
- `assets/rune-relations-circle-v03.png`: grafika bez napisów; tekstura imagegen,
  symbole i kierunki z dokładnej mapy katalogu. Wersja SVG zachowuje wektory.

Odświeżenie danych:
`PYTHONPATH=src .venv/bin/python scripts/build_resonance_mock.py`.

Testy uruchamiaj osobno, przez bezpieczny wrapper:
`scripts/safe_pytest.sh --timeout 60 tests/unit/test_resonance_mock.py`
oraz `scripts/safe_pytest.sh --timeout 60 tests/unit/test_rune_prototype_browser.py`.
Testy przeglądarki wymagają lokalnego Chrome; nie uruchamiaj równoległych pytest.

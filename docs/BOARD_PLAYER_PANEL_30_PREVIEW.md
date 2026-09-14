# Panel 30 pól — podgląd do testu ergonomii

Status: prototyp wizualny i klikalny, 2026-09-07. Nie jest podłączony do
bieżącej rozgrywki, odczytów planszy ani WLED. Nie zmienia zapisów, mapy
bojowej ani aktualnego wprowadzania rzutów. Wydruki kart zostały już
zaktualizowane do tych samych run.

## Pliki

- `assets/maps/recruitment_arena/panel_preview/index.html`: samodzielny podgląd,
  działa po otwarciu w przeglądarce, bez serwera i sieci.
- `arena-panel-v1.svg` w tym samym katalogu: mapa z dokładnie 30 polami panelu.
- `arena-panel-map.png`: podgląd rastrowy mapy z przeglądarki.
- `arena-panel-desktop.png`, `arena-panel-d20.png`: widoki prototypu.
- `panel-manifest.json`: znaki, współrzędne i przypisania siedmiu talii.
- Generator: `python scripts/build_arena_panel_preview.py`; szablon:
  `scripts/arena_panel_preview.html`.

Mapa źródłowa jest edytowalnym SVG. Zgodnie ze skillem imagegen użyto
wektorów i kodu, bez generowania rastra przez model; symbole są dokładnie
powtarzalne i niezależne od fontów. PNG to zrzuty przeglądarki.

## Orientacja i miejsce

Obecny model planszy to 20 kolumn × 30 wierszy. Podgląd obraca widok zgodnie
z ruchem wskazówek zegara: `(col,row) → (29-row,col)`. Daje to 30 pól
w poziomie i 20 w pionie. Dolny panel odpowiada istniejącej kolumnie 19,
od wiersza 29 do 0. Współrzędne scenariusza i zapisów nie zostały zmienione.
Wszystkie przeszkody, osłony i miejsca figur mają położenie wynikające
z oryginalnego scenariusza. Nie kolidują z proponowanym paskiem.

Panel zajmuje 30/600 = 5% pól. Do gry pozostanie 570 pól (30 × 19).
W implementacji pas musi być wyłączony z ruchu, ustawiania aktorów,
celowania i obszarów działania. Jest granicą gry, nie ścianą zapewniającą
osłonę ani terenem wywołującym efekty. Rozmiar geometryczny planszy pozostaje
20 × 30; osobno oznaczamy pola sterujące.

## Stałe miejsca

| Miejsca od lewej | Znaczenie |
| --- | --- |
| 1–6 | Ruch, atak, zmiana broni, przedmiot, puste pole, koniec tury |
| 7–26 | Dwadzieścia różnych run przypisanych zdolnościom aktywnej postaci |
| 27–30 | Minus, plus, zatwierdź, wróć |

Numery powyżej są wyłącznie dokumentacją pozycji. Użytkownik widzi ikony
lub runy. Nazwy run w podglądzie pomagają o nich rozmawiać; nie są nowymi
nazwami zdolności. Znaki podstawowe są stałe dla wszystkich postaci.

Nimra ma 19 aktywnie wybieranych zdolności w obecnym katalogu. Reakcje
pojawiają się kontekstowo. Jedno pole Ataku oznacza aktualną broń; zmiana
chwytu lub wariantu trafia do wyboru broni. Nie przydzielamy osobnych pól
każdemu wariantowi ataku bez broni/kosturem/oburącz. To konkretne uproszczenie
względem aktualnych 25 opcji świeżej tury Nimry.

Przed wdrożeniem trzeba przejrzeć wszystkie opcje sytuacyjne: uwolnienie
z chwytu, zakończenie ukrycia, anulowanie metamagii, aktywację przywołania,
reakcje, wyposażenie i interakcje. Sama liczba kart nie dowodzi, że cały
interfejs mieści się w 20 runach. Prototyp nie jest takim audytem.

Dostępne działania świecą, zużyte gasną. Nie zmieniamy ich miejsca po ruchu,
ataku ani zużyciu bonusu. Jedno dotknięcie wybiera działanie; cel oraz
akceptacja to osobne decyzje. Ten sam znak pojawia się na karcie i ekranie.
W dialogu runy identyfikują aktualne odpowiedzi i świecą wyłącznie używane pola.

## Wpisywanie kości

Wyłącznie − / +; żadnej klawiatury numerycznej ani wybierania wyniku runami.
Każda kość zaczyna od połowy liczby ścianek: k4=2, k6=3, k8=4, k10=5,
k12=6, k20=10. Zakres 1…liczba ścianek, bez zawijania na krańcach.
Jeden nowy nacisk zmienia wynik o jeden. Na razie bez automatycznego
powtarzania przy przytrzymaniu; odczyt tej samej aktywacji nie może naliczać
kolejnych zmian. Wymaga to sprawdzenia sygnału zwolnienia/przerwy sensora.

Dla uczciwej k20 średnia liczba zmian od 10 to 5, maksimum 10; z akceptacją
odpowiednio 6 i 11 dotknięć. Dla k6 średnio 1,5 zmiany plus akceptacja.
Podsumowanie całej czynności wymaga dodatkowego zatwierdzenia.

Każdą kość potwierdza się osobno, także niezmienioną wartość startową.
Następna kość ponownie startuje od swojej połowy. Po ostatniej wyświetlamy
wszystkie wyniki i obliczenia, a ✓ akceptuje komplet. Wróć z podsumowania
pozwala poprawić ostatni wynik; kolejne cofnięcia wracają do wcześniejszych.
Rzuty przeciwników nadal wykonuje aplikacja. Prototyp pokazuje sumę kości;
regułowe premie i rozstrzygnięcia pozostają zadaniem silnika gry.

## Ocena względem klawiatury i aktualnego menu

| Obszar | Obecnie | Panel 30 pól |
| --- | --- | --- |
| Działania | Skróty i kafelki pogrupowane według kosztu akcji | Jeden stały adres na planszy; grupa ekonomii akcji nadal czytelna na ekranie |
| Wprowadzanie rzutów | Szybkie wpisanie cyfr | Wolniej przy k20 i wielu kościach; cała obsługa przy planszy |
| Nauka | Znane litery, nazwy akcji na ekranie | Dwadzieścia run do rozpoznania; konieczne dopasowanie karta–pole |
| Geometria | Klawiatura obok planszy | Długi pas 30 pól; wygoda zależy od zasięgu ręki każdego gracza |
| Przestrzeń | Pełne 600 pól | 570 pól gry i 30 pól sterowania |
| Zmienne opcje | Łatwo dodać kafelek i tekst | Stały limit pól; potrzebne dopracowane podmenu i konteksty |
| Błędy | Literówka lub zły skrót | Pomylenie podobnej runy, przypadkowe dotknięcie, wielokrotny odczyt |
| Reakcje | Obsługa przy komputerze | Osoba reagująca też musi dosięgnąć panelu; wspólne sterowanie |
| Dialogi | Możliwość wpisania własnej wypowiedzi | Gotowe odpowiedzi z runami; szybsze, ale mniej swobodne |

Mocna strona: wspólny fizyczny rytm gry i brak przekazywania klawiatury.
Największe ryzyka: szukanie dwudziestu podobnych znaków, dostęp do całego
pasa oraz liczba dotknięć przy rzutach wieloma kośćmi. Runy powinny różnić
się sylwetką, nie tylko obrotem lub pojedynczą kreską. Nazwa zdolności
pozostaje na ekranie i karcie; sam symbol nie ma jej zastępować.

Kolory w prototypie grupują po pięć run, żeby pomagać w odnalezieniu miejsca.
Nie oznaczają kosztu many. Wygaszenie oznacza niedostępność, jasna obwódka
wybór. Fizyczny LED może wskazywać stan światłem, ale nie narysuje runy:
na planszy potrzebny jest trwały nadruk/nakładka. Czytelność trzeba ocenić
z każdego miejsca przy stole, również po odwróceniu widoku. Reakcje i kroki
rzutu podświetlają tylko pola właściwe dla bieżącej decyzji.

Rezygnacja z LLM oceniającego wypowiedź to osobna decyzja mechaniczna,
nie wymóg sprzętu. Zgodnie z ustaleniem pierwsza wersja ma gotowe opcje
z testami i premiami wynikającymi z zasad oraz historii decyzji. Brak
obowiązku opisywania zamiaru powinien przyspieszyć turę; ogranicza natomiast
swobodę formułowania rozwiązań. Komputer nadal jest potrzebny do czytania
opisów, celów, wyników i dialogów. Znika obsługa jego urządzeń wejściowych,
nie potrzeba patrzenia na ekran.

## Kolejny etap

1. Test ergonomii: Nimra (gęstość run), Brakka (krótka lista), Lorian (serie),
   a także dwa k20, obrażenia kilkoma kośćmi i dialog Nessy. Mierzyć pomyłki,
   liczbę dotknięć, czas decyzji oraz dostęp do panelu z miejsc graczy.
2. Ustalić mapowanie pełnego zbioru opcji sytuacyjnych i trwały manifest;
   późniejsze zmiany kolejności katalogu nie mogą przesuwać znaków na kartach.
3. Zarezerwować pas w scenariuszach/setupie i adapterze celów, następnie
   podłączyć pojedyncze zdarzenia nacisku do istniejących komend UI.
4. Przenieść rzuty, wybory, reakcje, zapisy/wznowienia, zgłaszanie fal,
   ustawianie postaci i dialogi. Zweryfikować całą sesję bez klawiatury.
5. Wygenerować produkcyjne karty z zatwierdzonymi runami i dopiero wtedy
   zmienić główną mapę oraz oznaczenia w aplikacji.

## Sprawdzenie prototypu

Przeglądarka Chrome, 1600 × 1100: 30 pól, wszystkie siedem talii, k4/k6/k8/
k10/k12/k20, wartości początkowe, oba krańce, dwie kości, cofnięcie i poprawa,
akceptacja niezmienionego wyniku 10, wygaszenie akcji, pozostawienie ruchu,
odpowiedzi dialogowe oraz brak poziomego przepełnienia widoku desktopowego.
Dodatkowo poprawność XML SVG, unikalność 30 znaków i brak przecięcia terenu
areny z panelem. To weryfikacja prototypu; nie wykonywano testów sprzętowych
ani pytest silnika gry, którego kod nie został zmieniony.

## Aktualizacja: karty i nawigacja

Wydruki wszystkich postaci używają wspólnego katalogu znaków
`ui/board_panel_symbols.py`. Usunięto wewnętrzny zaokrąglony obrys areny;
cały prostokąt nad panelem jest terenem gry. Podgląd A można zamienić na
B jednym dotknięciem dostępnej runy, bez kosztu. Wróć przywraca menu.
Rzuty i obowiązkowe rozstrzygnięcia nie pozwalają zmienić akcji.
Szczegółowy [plan wdrożenia](ARENA_PANEL_IMPLEMENTATION_PLAN.md) obejmuje
rezerwację pasa, odczyty sprzętu i pełny przebieg próby bez komputera jako
urządzenia wejściowego.

Przycisk Interakcja usunięty. Nie ma go na mapie, w menu ani na kartach;
slot 4 pozostaje pusty. Nie zmieniamy obsługi eksploracji jedną figurką.
W prototypie rozmowę otwiera bezpośrednie wskazanie Nessy na mapie.

## Aktualny interfejs gry i odświeżanie plików

Menu akcji w aplikacji pokazuje ikony i runy z katalogu kart, także w podglądzie
wybranej akcji. Główny indeks obejmuje przypisane pola panelu. Warianty bez
przypisanej runy są jawnie oznaczone w awaryjnym wyborze ekranowym.

Szablon gry używa adresów JS/CSS z wersją obliczoną z treści każdego pliku.
Po aktualizacji aplikacji i odświeżeniu strony przeglądarka pobiera zmienione
zasoby, bez ręcznego czyszczenia całej pamięci podręcznej. Po zmianach kodu
Pythona trzeba ponownie uruchomić serwer aplikacji.

Kontrola: menu i podgląd ruchu wszystkich siedmiu bohaterów w przeglądarce;
`tests/unit/test_ui_asset_versions.py` sprawdza stabilne adresy niezmienionych
plików i nową wersję po zmianie JS.

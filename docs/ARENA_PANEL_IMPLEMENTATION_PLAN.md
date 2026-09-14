# Panel areny — plan wdrożenia do testów

Ustalenia z 2026-09-07. Cel: przejście pełnej próby rekrutacyjnej bez
klawiatury i myszy, z komputerem wyświetlającym stan i rozstrzygnięcia.
Zakres pierwszego wdrożenia: arena, wszystkie siedem postaci oraz trzy
warianty próby. Dopiero po teście rozszerzamy rozwiązanie na kampanię.

## Gotowe teraz

- 30 pól: pięć ikon podstawowych, jedno puste pole, dwadzieścia run, minus, plus,
  zatwierdź i wróć. Wspólne źródło: `ui/board_panel_symbols.py`.
- Jawne przypisania identyfikatorów zdolności do run dla siedmiu postaci.
  Sortowanie katalogu nie zmienia przypisań. Reakcje są kontekstowe.
- Cztery formaty kart używają tych run; metadane nadal przechowują skróty
  jako zgodność ze starą obsługą, ale drukowane oznaczenia są panelowe.
- Mapa podglądowa to pełny prostokąt 30 × 19 pól ponad panelem.
  Usunięta wewnętrzna zaokrąglona granica. Brak niewidocznego ograniczenia
  przejścia na dawnym obrysie areny.
- Prototyp: przełączanie podglądów, powrót do menu, próbne wygaszanie
  zużytych działań, dialog oraz +/- z wartością startową połowy kości.

Aktualizacja wdrożenia: menu akcji areny i kreator rzutów korzystają już
z panelu w runtime. Kolor dostępnej runy odpowiada rodzajowi działania: akcja główna świeci
na niebiesko, bonusowa na pomarańczowo, ruch na zielono, a wyposażenie
i koniec tury na biało. Wybrana runa świeci jaśniej, pozostałe podglądy słabiej. Minus jest czerwony, plus zielony,
a zatwierdzenie niebieskie. Niedostępne działania i granice +/- są wygaszane.
Kreator zbiera każdą kość osobno od połowy jej zakresu i wymaga potwierdzenia
podsumowania. Przeglądarka przekazuje kontrolki do adaptera planszy;
rozstrzygnięcia nadal wykonują dotychczasowe walidatory i komendy sesji.

UI używa znaków z wydruków i jednego płynnego układu kafelków. Akcja główna
ma ciemnoniebieskie tło, dodatkowa ciemnopomarańczowe, ruch zieleń,
a wyposażenie i koniec tury szarość. Nie ma osobno przewijanych kolumn grup.

Arena gry ma 19 × 30 pól modelu; kolumna 19 pozostaje fizycznym panelem.
Ładowanie zapisu z figurką na panelu zgłasza konieczność ponownego setupu.
Pozostałe punkty audytu pełnej próby oraz test realnych sensorów pozostają
do wykonania. Symulowane odczyty nie zastępują testu rzeczywistej planszy.

## 1. Kontrakt pól i pełny katalog decyzji

Stałe pola podstawowe oraz runy korzystają ze wspólnego katalogu.
Pozycja panelu w obecnych współrzędnych: `(19, 29-slot)`, sloty 0…29.
Widok obrócony w prawo daje 30 kolumn i 20 rzędów; model planszy nadal
ma 20 kolumn i 30 rzędów. Reakcje dotyczą osoby reagującej, a nie zawsze
bohatera bieżącej tury — panel musi wskazywać właściwego właściciela.

Uzupełnić audyt decyzji sytuacyjnych: zakończenie ukrycia na polu ukrywania,
uwolnienie z chwytu, metamagia i wybór rodzaju obrażeń, obsługa przywołania,
Lorianowa seria, opcje wyposażenia i sceny, wybór spośród kilku reakcji.
Przypisania są jawne; nie tworzymy ich z indeksu bieżącej listy dostępności.
Puste miejsca nie są przejmowane przez inną zdolność po zużyciu akcji.
Wybór wariantu aktualnej broni odbywa się w menu broni, nie przez osobne
stałe kafelki dla każdej postaci.

Pliki: `ui/board_panel_symbols.py`, nowy `ui/board_panel.py`,
`ui/combat_menu_layout.py`, `ui/combat_menu_mana.py`.
Sprawdzenie: unikalne pola, pełne pokrycie aktywnych i sytuacyjnych opcji,
bez cichego obcinania listy. Brak miejsca ma dawać czytelny błąd konfiguracji.

## 2. Prostokątna arena i setup panelu

Zarezerwować 30 pól na dłuższej krawędzi we wszystkich trzech próbach.
Pola nie są dostępne dla aktorów, ruchu, celów, efektów obszarowych,
przywołań ani interakcji sceny. Nie traktować panelu jako osłony, przeszkody
magicznej czy źródła kary terenowej. Siatka gry kończy się na granicy pasa.
Wczytanie próby z aktorem na pasie wymaga ponownego setupu, bez cichego
przesunięcia figurki. Obiekty obecnej areny nie kolidują z pasem.

Setup pokazuje osobny krok: ustawić nakładkę, sprawdzić lewy i prawy
koniec, zatwierdzić. Ekran i fizyczny widok mają zgodną orientację.
Wgranie samej nowej grafiki nie jest rezerwacją pól w silniku.

Pliki: `content/scenarios/recruitment_arena*.json`,
`application/recruitment_arena.py`, `application/battle_setup.py`,
`world/` — oddzielna klasyfikacja pól sterujących,
`ui/training_arena.py`, zasób mapy.
Sprawdzenie: ścieżki, pola przywołania, cele i obszary nie obejmują panelu;
żadna dawna zaokrąglona krawędź nie ogranicza gry.

## 3. Zdarzenia panelu i podwójna ścieżka podglądu

Adapter zamienia naciśnięcie na identyfikator pola. Reguły nadal wykonują
istniejące komendy sesji UI. Jeden fizyczny nacisk daje jedno zdarzenie;
ponowny odczyt bez zwolnienia nie może powielić komendy. W pierwszym
teście bez automatycznego powtarzania przytrzymanego +/-.

| Bieżący stan | Wejście | Oczekiwane zachowanie |
| --- | --- | --- |
| Menu | Dostępna ikona/runa A | Podgląd A, bez wydania akcji i many |
| Podgląd A | Wróć | Pełne aktualne menu |
| Podgląd A | Dostępna ikona/runa B | Bezpośrednio podgląd B, bez kosztu |
| Podgląd A | Ponownie A | Pozostaje podgląd A; nie wykonuje akcji |
| Podgląd A | Niedostępna runa | Bez zmiany; wyjaśnić powód na ekranie |
| Podgląd A | Pole celu | Zaznaczyć legalny cel/ścieżkę |
| Podgląd A | Zatwierdź | Wykonać albo przejść do wymaganego rzutu |
| Wpisywanie rzutu / obowiązkowe rozstrzygnięcie | Runa innej akcji | Nie przełączać; dokończyć bieżące rozstrzygnięcie |
| Akcja zakończona | — | Aktualne menu; nieaktywny podgląd i stare cele |

Przejście A→B musi atomowo sprawdzić dostępność B, wyczyścić wyłącznie
niezatwierdzony podgląd A i zbudować B. Usuwa stary cel, trasę ruchu,
obszar i LED-y podglądu. Nie cofa wydanej akcji, wykonanego ruchu, poznanego
rzutu ani użytego efektu. Odrzucenie niedostępnego B zachowuje podgląd A.
Nie wywoływać ogólnego resetu pending state, który mógłby kasować obowiązkowy
rzut, koncentrację, reakcję lub pozostałe ataki rozpoczętej serii.

Pliki: nowy `ui/board_panel.py`, `ui/exploration_app.py`, `ui/routes.py`,
`hardware/` — adapter panelu nad `board.Connection`; niskopoziomowy
`board/` pozostaje bez reguł gry.
Sprawdzenie: A→B→Wróć, A→A, niedostępne B, brak kosztu podglądów,
brak podwójnej aktywacji, nieprzerwany obowiązkowy rzut i seria.

## 4. Rzuty i prezentacja

Domyślne wartości: k4=2, k6=3, k8=4, k10=5, k12=6, k20=10.
Minus i plus zmieniają wyłącznie naturalny wynik bieżącej kości, w zakresie
1…liczba ścianek. Modyfikatory dolicza aplikacja. Każda kolejna kość ma
własną wartość startową; nie dziedziczy poprzedniego wyniku. Akceptacja
niezmienionej połowy kości również jest konieczna.

Jedna kość na krok, osobne kroki przewagi/utrudnienia, końcowe podsumowanie
wszystkich wyników i premii do zatwierdzenia. Wróć umożliwia poprawę
wprowadzonych liczb zgodnie z istniejącym etapem; nie ponawia automatycznego
rzutu przeciwnika. Przeciwnicy zawsze rzucają automatycznie.

Na ekranie symbole zastępują litery skrótów. Opisy i grupy kosztów akcji
pozostają czytelne. LED-y oznaczają dostępność, aktualny wybór i legalne cele;
kolor nie zastępuje znaku ani nie sugeruje opłacenia many. W trakcie rzutu
aktywne są tylko odpowiednie kontrolki. Ruch po każdym odcinku wraca do menu.

Uzgodniony sposób świecenia panelu (zaimplementowany w podglądzie):

| Stan pola | Jasność robocza |
| --- | --- |
| Dostępna akcja w menu | 65% |
| Wybrana akcja / odpowiedź w podglądzie | 100% |
| Pozostałe dostępne akcje / odpowiedzi podczas podglądu | 35% |
| Dostępne Wróć, Zatwierdź, +/- | 85% |
| Niedostępne działanie, niewykorzystana runa, puste pole | 0% |

Przygaszone runy nadal przyjmują wybór i przełączają podgląd bez kosztu.
Wróć zapala się przy wejściu w podgląd; jego użycie przywraca menu i jasność
65% dostępnych akcji. Wykonanie akcji wygasza wszystkie działania zużytego
rodzaju. Podczas rzutu runy akcji są wyłączone, a +/- gasną na granicach
zakresu. W stanie wyniku świecą tylko dostępne zatwierdzenie i cofnięcie.
Bez migania; jasność nie oznacza posiadanej/opłaconej many.

W integracji sprzętowej trzeba składać podświetlenie panelu z osobną warstwą
celów/ruchu, aby odświeżenie celów nie gasiło run ani przycisku Wróć.
Należy wysyłać także wygaszenie poprzednich pól, bez pozostawiania starego
wyboru po zmianie postaci, fazy lub zakończeniu akcji. Wartości procentowe
są punktem wyjścia do kalibracji na fizycznej planszy, nie gwarancją liniowej
jasności postrzeganej. Podgląd nie wysyła jeszcze komend do sprzętu.

Pliki: `ui/static/exploration.js`, `ui/static/exploration.css`,
`ui/static/dice_icons.js`, `ui/templates/exploration.html`,
`ui/shield_bash.py` / `ui/static/shield_bash.js` i pozostałe istniejące
wielostopniowe wejścia rzutów.
Sprawdzenie: wszystkie rodzaje kości, granice, korekty, wiele kości,
ponowne potwierdzenie, rzuty automatyczne bez ponownego losowania.

## 5. Pełna próba rekrutacyjna

Panel obsługuje wybór postaci i wariantu, setup, inicjatywę, turę bohatera,
reakcje, turę kukły, zgłaszanie fal many, koniec tury, rozmowę z Nessą,
powtórzenie próby i powrót do wyboru postaci. Wyjście, zapis i wczytanie
muszą być osiągalne przez kontekstowe menu; nie zabierają nowego stałego pola.

Nessa używa gotowych opcji z runami. Nie wymagamy wpisywania tekstu ani
przyznawania przez LLM premii do rzutu. Nazwy i zasady testów pokazujemy
przed zatwierdzeniem. Wycofanie z dialogu przywraca właściwy stan areny.

Pliki: `ui/training_arena.py`, `ui/static/training_arena.js`,
`ui/nessa_briefing.py`, treści areny i trasy sesji. Dotychczasowe urządzenia
wejściowe można zachować technicznie jako awaryjne na czas testu, ale żaden
krok zaplanowanej próby nie może wymagać ich użycia.

## Warunki dopuszczenia do testu przy stole

- Po jednej pełnej próbie każdym bohaterem oraz wariant wsparcia i obszarowy.
- Nimra: wszystkie runy, metamagia, zmiana podglądu bez kosztu.
- Lorian: seria ataków i dobór; Mira: ukrycie/wyjście i zmiana LED-ów;
  Garran: ruch, atak i Uderzenie tarczą; Brakka: aktywny szał;
  Dagna/Erynd: wsparcie, przywołania i decyzje sytuacyjne.
- Dwa k20, obrażenia kilkoma kośćmi, anulowanie podglądu i korekta wyniku.
- Każdy gracz dosięga panelu również podczas swojej reakcji.
- Brak nacisków zdublowanych lub zgubionych przy normalnym tempie;
  błędny odczyt nie wykonuje innej akcji.
- Zapis/wczytanie nie gubi etapu, nie przywraca zużytej akcji i nie zmienia run.
- Gra nie wymaga dotykania klawiatury ani myszy od wyboru próby do jej końca.

Testy automatyczne uruchamiać pojedynczymi plikami przez `safe_pytest.sh`:
mapowanie, rezerwacja panelu, routing/podglądy, wejście kości, integracja
areny. Następnie przeglądarka z symulacją nacisków i osobno rzeczywisty sprzęt.
Nie uznawać podglądu HTML ani samych testów jednostkowych za test LED/sensorów.

## Doprecyzowanie ikon podstawowych

Ruch używa sylwetki idącego człowieka. „Zmiana broni” otwiera istniejący
wybór wyposażenia; nie oznacza drugiego rodzaju ataku. Przycisk „Interakcja” został usunięty.
Eksploracja pozostaje bez zmian: jedna figurka i wybór odpowiedniego pola
bezpośrednio uruchamiają rozmowę albo działanie na obiekcie. W arenie
Nessę wskazujemy bezpośrednio na mapie. Pole slot 4 pozostaje puste,
bez komendy, symbolu i podświetlenia; inne przypisania są niezmienione.

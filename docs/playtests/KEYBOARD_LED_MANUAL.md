# Numpad + LED — uruchomienie i obsługa

Wariant działa na branchu `feat/led-keyboard-control`. Pad pozostaje kolejnym
etapem. Obecny profil zachowuje zasady walki, sceny, fizyczne kości oraz ręczne
przesuwanie figurek. Czujniki i przyciski planszy nie są wymagane.

Stary fizyczny pasek run i przycisków pozostaje wygaszony. Menu ma tekstowe
opcje z widocznym zaznaczeniem: 8 / 2 zmienia wybór, Enter wybiera.
Dłuższy opis przewijasz klawiszami − / +. LED-y pokazują pola, trasy, cele
i pozostałe informacje przestrzenne na mapie.

Ściągę sterowania otwierasz klawiszem `1`, w ekranowej karcie postaci.
Zawiera przypisania i informację o bieżącym wyborze. Górny pasek skrótów
został usunięty, aby zostawić więcej miejsca na rozgrywkę.

## Szybki start

Z katalogu repozytorium uruchom:

```bash
.venv/bin/python scripts/keyboard_playtest.py
```

Gra: <http://127.0.0.1:5202/play>. Menu: <http://127.0.0.1:5202/>.
Podgląd LED: <http://127.0.0.1:5002/>. Otwórz grę i podgląd obok siebie;
decyzje podejmujesz w oknie gry. Nie trzeba klikać pól symulatora.

Każde uruchomienie tworzy osobne zapisy, obserwacje i katalog bohaterów
w `/tmp/keyboard-led-…`. Zwykłe zapisy nie są zmieniane. Opcja
`--runtime /tmp/moj-test-klawiatury` pozwala wskazać stały katalog testu.
`Ctrl+C` zatrzymuje serwery i wygasza podłączone LED-y.

Szybki test samej walki, z automatycznym setupem i inicjatywą:

```bash
.venv/bin/python scripts/keyboard_playtest.py --arena --skip-setup
```

Domyślni bohaterowie: Garran, Brakka i Nimra. Własny skład, 3–6 różnych osób:

```bash
.venv/bin/python scripts/keyboard_playtest.py --heroes erynd mira dagna
```

## Prawdziwe LED-y bez skanera USB

Adres zapisany obecnie w konfiguracji repozytorium to `http://192.168.50.2`:

```bash
.venv/bin/python scripts/keyboard_playtest.py --wled-url http://192.168.50.2
```

Jeśli kontroler WLED ma inny adres, podaj go w `--wled-url`. Aplikacja używa
istniejącego mapowania LED. Nie wyszukuje portu serial ani nie uruchamia ESP
skanera. Setup fizycznej mapy pozostaje ręczny; `--skip-setup` jest dostępne
wyłącznie dla areny z symulatorem.

W istniejącym launcherze eksploracji dostępne są też
`--input-mode keyboard --board-backend wled --wled-url ADRES`.
W panelu konfiguracji UI można osobno wybrać sterowanie klawiaturą i wyjście
„same LED-y (WLED)”. Status wejścia i błędy świateł są pokazywane oddzielnie.

## Klawisze

| Klawisz | Znaczenie |
| --- | --- |
| 8 / 6 / 2 / 4 | Góra / prawo / dół / lewo: wybierz pole kursorem lub opcję bieżącego menu. |
| Enter | Otwórz opcję, zatwierdź podgląd albo przejdź przez istniejące podsumowanie. |
| Backspace | Cofnij dozwolony krok lub zamknij najwyższy panel. |
| 7 | Otwórz podgląd ruchu. |
| 9 | Otwórz podgląd ataku bronią. |
| 5 | Przejdź do dostępnych run i akcji lub przełącz kursor mapy na opcje bieżącego kroku; 8 / 2 wybiera, Enter otwiera podgląd lub opcję. |
| 1 | Otwórz kartę postaci ze ściągą sterowania. |
| 3 | Otwórz/zamknij ekwipunek. |
| 0 | Otwórz istniejące potwierdzenie końca tury. |
| + / − | Zmień wynik kości lub pozycję obsługiwanego pickera; podczas czytania przewiń opis w dół / w górę. |
| . | W wyborze wielu celów dodaj/odznacz wskazany cel bez wykonania akcji. Działa też przecinek na klawiszu separatora numpada. |
| * | Otwórz dziennik. |
| / | Otwórz menu sesji. |
| = | Otwórz pomoc. |

Klawisze numpada działają przy włączonym i wyłączonym Num Lock. Klawisz 5
otwiera akcje, a narożniki 7/9/1/3 mają skróty opisane powyżej; nie służą do
przesuwania kursora po skosie. W menu można wybierać również przez 4 / 6.
Dotychczasowe strzałki, skróty literowe, Esc, Spacja i PageUp/PageDown
pozostają dodatkowymi aliasami. Tab / Shift+Tab pozwala opcjonalnie przejść
fokusem do konkretnej kontrolki ekranowej.

W polu tekstowym klawisze służą do pisania. Przytrzymanie Entera nie wykonuje
następnej decyzji. Kierunki mogą się powtarzać; przy szybkiej zmianie celu
poczekaj na aktualizację podglądu przed Enterem.

## Ruch i cele

Sterowanie polami jest dopasowane do ustawienia fizycznej planszy gracza.
W jej współrzędnych 6 (prawo) zmniejsza wiersz, 8 (góra) zmniejsza
kolumnę, 4 (lewo) zwiększa wiersz, a 2 (dół) zwiększa kolumnę.
Menu, ekwipunek i wprowadzanie wyników kości zachowują zwykłe kierunki.

`7` → `8/6/2/4` → sprawdź podświetlenie i koszt → `Enter`.
Kierunki przesuwają kursor, nie figurkę. Silnik liczy trasę od bieżącej
pozycji postaci, więc dojście kursorem do pola po skosie nie narzuca
ortogonalnej trasy. Niebieski to zasięg, żółty trasa, zielony cel.
Czerwone wskazanie blokuje wykonanie; UI podaje powód odmowy.

Po wykonaniu przestaw figurkę zgodnie z LED-ami. Jeśli gra pokazuje wynik
lub reakcję, rozpatrz ten krok przed nową akcją. Enter potwierdza tylko
jeden etap; nie pomija komunikatów i nie kończy automatycznie tury.

Przy mocy z wieloma celami używaj kropki do dodawania celów, a Entera do
zatwierdzenia gotowego zestawu. Bez gotowego zestawu Enter wskazuje pole
i pozostawia wybór otwarty. Możliwe jest wielokrotne wskazanie tego samego
wroga, jeśli zezwala na to konkretna moc. Wybór centrum obszaru i wyłączenie
postaci pozostają osobnymi krokami. Opcję „Nie wyłączaj żadnego pola” wybierz
przez `5` → `8/2` → `Enter`. Ponowne `5` wraca z opcji do kursora mapy.

## Przygotowanie i rozmowy

Menu, wybór drużyny, sceny i ekwipunek obsługujesz klawiszami 8 / 2 i Enterem.
W rozstawianiu postaci 8/6/2/4 wskazuje pole na LED-ach; Enter przekazuje
wybór do istniejącego setupu, a kolejny Enter zatwierdza ustawienie figurki.
Widoczny przycisk „Dalej” potwierdza bieżący element, a po ostatnim kroku
„Rozpocznij inicjatywę” prowadzi do rzutów. „Poprzedni element” wybierz
świadomie klawiszami 8 / 2 lub użyj Backspace, aby poprawić rozstawienie.

Wyposażenie i ponumerowane miejsca plecaka mają osobne przewijane listy.
8 / 2 przenosi zaznaczenie i przewija listę do wybranej pozycji;
Enter otwiera zmianę przedmiotu. +/− przegląda pasujące przedmioty,
Enter zatwierdza wybraną opcję, a Backspace anuluje zmianę. Pasek akcji na dole
pozwala zajrzeć do zapasu drużyny, otworzyć pomoc i zatwierdzić bohatera.

Wyniki fizycznych kości wprowadza istniejący kreator: ustaw wartość przez
`+`/`−` lub `8`/`2`, zatwierdź kość Enterem i na końcu zatwierdź podsumowanie.
Backspace wraca do poprzedniego dozwolonego kroku. Przeciwników rozlicza aplikacja.
Swobodne deklaracje i pytania do MG nadal wpisujesz klawiaturą.

## Sprawdzenie sprzętowe

Próby automatyczne obejmują symulator, atrapy połączeń i rzeczywisty Chrome.
Fizyczny test WLED pozostaje do ogrania: odłącz USB skanera, sprawdź kierunki
8/6/2/4 względem rozłożonej planszy, zmianę celu, ruch, czerwony cel,
setup, kości oraz wygaszenie po `Ctrl+C`. Awaria WLED nie uruchamia skanera
i nie zamienia podglądu w wykonaną akcję. Po odzyskaniu połączenia wysyłana
jest aktualna ramka.

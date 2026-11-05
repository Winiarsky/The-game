# Klawiatura + LED — uruchomienie i obsługa

Wariant działa na branchu `feat/led-keyboard-control`. Pad pozostaje kolejnym
etapem. Obecny profil zachowuje zasady walki, sceny, fizyczne kości oraz ręczne
przesuwanie figurek. Czujniki i przyciski planszy nie są wymagane.

Stary fizyczny pasek run i przycisków pozostaje wygaszony. Menu ma tekstowe
opcje z widocznym zaznaczeniem: strzałki zmieniają wybór, Enter wybiera.
Dłuższy opis przewijasz PageUp/PageDown. LED-y pokazują pola, trasy, cele
i pozostałe informacje przestrzenne na mapie.

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
| Strzałki | Wybierz pole kursorem lub opcję bieżącego menu. |
| Enter | Otwórz opcję, zatwierdź podgląd albo przejdź przez istniejące podsumowanie. |
| Esc / Backspace | Cofnij dozwolony krok lub zamknij najwyższy panel. |
| M | Otwórz podgląd ruchu. |
| A | Otwórz podgląd ataku bronią. |
| R | Przejdź do dostępnych run i akcji; strzałki wybierają, Enter otwiera podgląd. |
| I | Otwórz/zamknij ekwipunek. |
| C / J / H | Postać / dziennik / ściąga. |
| 0 | Otwórz istniejące potwierdzenie końca tury. |
| + / − | Zmień wynik kości lub pozycję obsługiwanego pickera. |
| Spacja | W wyborze wielu celów dodaj/odznacz wskazany cel bez wykonania akcji. |
| Tab / Shift+Tab | Przejdź fokusem do konkretnej kontrolki ekranowej. |
| PageUp / PageDown | Przewiń dłuższy opis. |

W polu tekstowym klawisze służą do pisania. Przytrzymanie Entera nie wykonuje
następnej decyzji. Strzałki mogą się powtarzać; przy szybkiej zmianie celu
poczekaj na aktualizację podglądu przed Enterem.

## Ruch i cele

`M` → strzałki → sprawdź podświetlenie i koszt → `Enter`.
Strzałki przesuwają kursor, nie figurkę. Silnik liczy trasę od bieżącej
pozycji postaci, więc dojście kursorem do pola po skosie nie narzuca
ortogonalnej trasy. Niebieski to zasięg, żółty trasa, zielony cel.
Czerwone wskazanie blokuje wykonanie; UI podaje powód odmowy.

Po wykonaniu przestaw figurkę zgodnie z LED-ami. Jeśli gra pokazuje wynik
lub reakcję, rozpatrz ten krok przed nową akcją. Enter potwierdza tylko
jeden etap; nie pomija komunikatów i nie kończy automatycznie tury.

Przy mocy z wieloma celami używaj Spacji do dodawania celów, a Entera do
zatwierdzenia gotowego zestawu. Bez gotowego zestawu Enter wskazuje pole
i pozostawia wybór otwarty. Możliwe jest wielokrotne wskazanie tego samego
wroga, jeśli zezwala na to konkretna moc. Wybór centrum obszaru i wyłączenie
postaci pozostają osobnymi krokami. Opcję „Nie wyłączaj żadnego pola” można
wybrać przez Tab i Enter.

## Przygotowanie i rozmowy

Menu, wybór drużyny, sceny i ekwipunek obsługujesz strzałkami i Enterem.
W rozstawianiu postaci strzałki wskazują pole na LED-ach; Enter przekazuje
wybór do istniejącego setupu. Esc cofa tam, gdzie przewiduje to scena.

Wyniki fizycznych kości wprowadza istniejący kreator: ustaw wartość,
zatwierdź kość i na końcu podsumowanie. Przeciwników rozlicza aplikacja.
Swobodne deklaracje i pytania do MG nadal wpisujesz klawiaturą.

## Sprawdzenie sprzętowe

Próby automatyczne obejmują symulator, atrapy połączeń i rzeczywisty Chrome.
Fizyczny test WLED pozostaje do ogrania: odłącz USB skanera, sprawdź kierunki
strzałek względem rozłożonej planszy, zmianę celu, ruch, czerwony cel,
setup, kości oraz wygaszenie po `Ctrl+C`. Awaria WLED nie uruchamia skanera
i nie zamienia podglądu w wykonaną akcję. Po odzyskaniu połączenia wysyłana
jest aktualna ramka.

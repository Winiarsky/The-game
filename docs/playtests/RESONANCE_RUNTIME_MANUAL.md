# Test ręczny: Ładunki i Rezonans

Wersja 30.09.2026. To rzeczywisty silnik Python i ekran `/play`, nie mock HTML.
Nowy profil jest domyślny w nowych walkach Misji 0 i swobodnej areny.
Rozmowy, reputacja i eksploracja zachowują dotychczasowe zasady. Walki
wczytane ze starych zapisów oraz prowadzone lekcje areny zachowują stary profil.
Do sprawdzania nowych zasad rozpocznij nowe starcie.

## Najprostsze uruchomienie

Z katalogu projektu:

```bash
.venv/bin/python scripts/resonance_playtest.py
```

Otwórz grę: <http://127.0.0.1:5201/play>, a w drugim oknie planszę:
<http://127.0.0.1:5001>. Skrypt uruchamia oba serwery, pomija fabułę, ale
zostawia rozstawienie figurek i inicjatywę. Zaczynasz bez zmęczenia z drogi.
Domyślna drużyna: Garran, Brakka, Mira, Dagna, Lorian, Nimra.
Każde uruchomienie dostaje osobny katalog `/tmp/resonance-playtest-*`,
wypisany w terminalu. Nie nadpisuje normalnej kampanii. Ctrl+C kończy serwery;
katalog testu pozostaje do inspekcji i wczytania zapisów.

Do szybkiego sprawdzenia samej walki w symulatorze:

```bash
.venv/bin/python scripts/resonance_playtest.py --skip-setup
```

Osobna próba z Eryndem:

```bash
.venv/bin/python scripts/resonance_playtest.py --heroes garran mira erynd
```

Zajęte porty zmień przez `--port 5202 --board-port 5002`.
Opcja `--check` sprawdza przygotowanie sesji bez serwerów i bez sprzętu.

## Prawdziwa plansza

Najpierw zakończ inne połączenie z tą samą planszą. Podaj jej rzeczywisty port
szeregowy i adres WLED, np. zastępując poniższe wartości:

```bash
.venv/bin/python scripts/resonance_playtest.py --hardware \
  --serial-port /dev/ttyACM0 --wled-url http://ADRES_TWOJEGO_WLED
```

Ten tryb nie uruchamia symulatora i wymaga ręcznego rozstawienia figurek.
Nie był zweryfikowany na fizycznym sprzęcie podczas wdrożenia.

## Obsługa

- Wybór mocy/runy → cel/pole → tryb podstawowy lub wzmocniony → ✓.
  Do ✓ możesz wrócić; koszt pobierany jest raz po zatwierdzeniu.
- Gracz: ustaw wynik jednej fizycznie rzuconej kości przez +/−, zatwierdź ✓.
  Dopiero potem pojawi się następna, także przy 2k6 i przewadze.
- Przeciwnik: zapowiedź → ✓ → aplikacja losuje i pokazuje wynik → ✓.
  Przy okazyjnym odpowiedni przeciwnik jest podświetlony; ruch czeka na wynik.
- Gwiazda otwiera informacje; wybierz postać na planszy lub w kolejce.
  +/− zmieniają strony opisów, powrót wznawia przerwaną decyzję bez kosztu.
- Niebieskie pole to cel ruchu. Żółta ścieżka dotyczy bohatera, czerwona
  przeciwnika. Obszar jest pomarańczowy, pominięta postać turkusowa.
  Atakujący przeciwnik jest wyróżniony; wynik zmienia kolor na trafienie/pudło.
- Długie kolejki, łańcuch Rezonansu i raporty mają strony zamiast pionowego
  przewijania. Pełne stany są w informacjach postaci; ekran walki nie dubluje
  listy współrzędnych i technicznych informacji o skanowaniu planszy.

## Lista prób przy stole

- [ ] 20/20 ładunków na starcie; koszt 4/8 plus skaza; A, S i ruch zużywane
  zgodnie z kartą. Anulowanie podglądu nie pobiera kosztu.
- [ ] Moc wzmocniona dodaje runę przed skutkami. Nowy bohater dołącza od
  początku swojej tury. Ekran pokazuje kolejność, uczestników i sumy premii.
- [ ] Wieża działa również podczas własnej tury; Grot dodaje kości obrażeń;
  Schody dają ruch, Błysk osobne kości leczenia. Oko nie zmienia ST.
- [ ] Kielich i Klepsydra mają osobne pozostałe pule. Fala powiela poprzedni
  skuteczny efekt; kolejne wejście w informacje nie odnawia osłon.
- [ ] Węzeł ogranicza ruch wrogów. Hak po obrażeniach pozwala przenieść każdy
  zraniony, żywy cel raz, bez okazyjnych, albo pozostawić go na miejscu.
- [ ] Moc podstawowa wygasza Rezonans dopiero po skutkach i Haku;
  Skupienie od razu. Koniec tury bez wzmocnienia też kończy łańcuch.
- [ ] Odzysk klasowy 1k4 jest dobrowolny, raz na rundę; pominięcie nie
  zużywa limitu, a pełna pula nie wywołuje zbędnego pytania.
- [ ] Garran: osłona +1 KP sąsiadów, odzysk po pudle, odrzucenie Impulsu,
  magiczny składnik Ostrza, pełny ruch wymagany do Szarży, ST zależne od drogi.
- [ ] Powalony: przewaga wręcz, −2 dystansowo, brak ruchu w następnej turze,
  lecz atak i akcja specjalna nadal dostępne.
- [ ] Brakka: dwie dodatkowe kości broni na krytyku; Szał +1k6, połowa
  trzech fizycznych typów obrażeń i poprawny czas; Echo używa ST 10 + Siła.
- [ ] Mira: ukrycie osobno wobec każdego wroga; Cios z flanki/ukrycia;
  Parkour wybiera wroga i wolne sąsiednie pole, przecina przeszkody, nie
  zużywa zwykłego ruchu. Widzący ją przeciwnicy nadal wykonują okazyjne.
- [ ] Przerwanie ruchu przez utratę przytomności zatrzymuje dalszą drogę
  i wskazuje pole, na które należy odłożyć figurkę.
- [ ] Więzy mroku: połowa ruchu, a z ukrycia dodatkowo brak ruchu w kolejnej rundzie.
- [ ] Dagna: ST 10 + Mądrość, Pieczęć, leczenie i +2 innemu bohaterowi;
  Krąg podnosi także żywego sojusznika z 0 PW.
- [ ] Lorian: Hymn czeka bezterminowo, najwyżej jeden na postaci. Po k20
  można odmówić albo rzucić dodatkowe 1k6; naturalna 1/20 się nie zmienia.
  Hymn pozostaje po zakończeniu walki. Pieśń przejścia nie wywołuje reakcji.
- [ ] Nimra: obszar → jawny wybór pomijanego celu albo „Nie pomijaj”;
  Strefa ognia 3×3 może zranić sojuszników. Pociski mają osobne trafienia;
  kolejne użycia tej samej mocy uwzględniają skazę.
- [ ] Erynd: nieruchomy pierwszy strzał, Piętno, dwa ataki, ruch i strzał,
  unieruchomienie, skaza i zużycie amunicji.
- [ ] Mikstura zużywa jedną akcję i jedną sztukę z ekwipunku lub wspólnego
  łupu. Rzuć każdą kością oddzielnie.
- [ ] Zapisz/wczytaj po pierwszej kości, przed Hakiem, podczas okazyjnego
  i na ekranie wyniku przeciwnika. Kości, koszty, stany i LED-y nie powtarzają się.
- [ ] Po starciu wraca poprawny etap misji, a komunikat kapitulacji nie
  znika pod ekranem walki. Sprawdź ponownie prawdziwe LED-y i przyciski.

## Uwagi implementacyjne

Stan profilu znajduje się w `CombatState.resonance`; zapis ma wersję 34.
Stare zapisy nie są przeliczane na nowe zasady w połowie walki. Serwer
odrzuca powtórzoną decyzję ze starą rewizją i nie losuje nic przy odczycie.
Geometria używa faktycznej mapy; panel w kolumnie 19 nigdy nie jest celem.
Opcjonalne `environment.stealth_bonus` pochodzi z danych mapy i daje
najsilniejszą premię przy obiekcie (na jego polu lub sąsiednim). Domyślnie 0;
nie dodano wymogu osłony ani nie przypisano samowolnie premii obecnym mapom.

Automatyczne testy nie zastępują powyższych prób stołowych, zwłaszcza
rzeczywistego przesuwania figurek, czytelności kolorów i opóźnień sprzętu.

## Weryfikacja wdrożenia — 30.09.2026

Testy uruchamiane kolejno przez `scripts/safe_pytest.sh`, z timeoutem:

- `tests/unit/test_resonance_combat.py`: 60 przypadków — wszystkie karty,
  kości, pule, reakcje, warunki, ekwipunek, geometria i klatki LED.
- `tests/integration/test_resonance_session.py`: 9 przypadków — prawdziwa
  sesja misji, API/panel, blokada powtórzeń, zapis, AI, mikstury, osłony mapy,
  zmęczenie, przeniesienie Hymnu między walkami i swobodna arena bez panelu misji.
- `tests/integration/test_resonance_browser.py`: 2 przypadki — Chrome,
  1366×768 i 1131×720, automatyczne skany panelu, kości i brak przepełnienia,
  także dla 6 bohaterów, 14 uczestników i 9 rodzajów premii Rezonansu.
- Regresja: zapisy 64, karty 32, starszy panel run 9, prezentacja walki 10,
  loader scenariuszy 36, zaakceptowany mock 11 — przeszły.
- Misja 0: 37 przeszło, 1 stary test menu gildii nie przeszedł:
  `test_guild_destinations_use_tile_fields_and_arena_is_informational` nie
  uwzględnia przycisku powrotu (slot 29), obecnego już w kodzie HEAD przed
  tym wdrożeniem. Wpis do naprawy w TODO; nie zmieniano zachowania gildii.

Launcher sprawdzono dla 6 bohaterów i oddzielnie drużyny z Eryndem. Uruchomiono
też rzeczywisty Flask i lokalny symulator, sprawdzono HTTP, wysłanie klatki
LED oraz zamknięcie po Ctrl+C. Nie uruchamiano pełnej, ogólnoprojektowej
suity ani prób na rzeczywistym serial/WLED.

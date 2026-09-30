# Walka: makieta ładunków i ciągłego Rezonansu

Aktualizacja: 29.09.2026. [Otwórz makietę](prototype.html?scene=combat).

Zmiana obejmuje wyłącznie walkę w `prototype.html`. Rozmowy, reputacja,
przygotowanie wyprawy i eksploracja zachowują wcześniejszy przebieg.
Nie podłączono Flask, czujników, LED ani zapisów właściwej gry. Starsza
aplikacja nadal korzysta ze swojego dotychczasowego modelu walki.

## Jak ograć

1. Otwórz `prototype.html` i wybierz **Walka · Rezonans**. Każdy bohater
   zaczyna z 20 ładunkami; nie ma doboru run ani ręki.
2. Wybierz runę mocy na dolnym panelu. Przycisk pokazuje dostępność, a jego
   podpowiedź nazwę aktualnej mocy lub powód blokady. Zwykły atak, ruch,
   przedmiot i koniec tury zachowują dotychczasowe pola.
3. Rozwiń **Symulator pól · panel testowy** nad listą inicjatywy. Kliknięcie
   pola zastępuje sygnał fizycznej planszy. Złote pola są legalne;
   niebieskie pokazują docelową pozycję i drogę. Lista celów po prawej
   jest informacyjna — nie zastępuje wyboru pola.
4. W podglądzie wybierz **Podstawowa** (Rozwidlenie) albo **Wzmocniona**
   (Trójząb). Widać pełny koszt ze skazą i przyszłą liczbę ładunków.
   ✓ opłaca i uruchamia moc; ↩ wcześniej anuluje bez kosztu.
5. Wprowadzaj wynik **jednej kości naraz**, bez modyfikatora. +/− ustawia
   wynik, a ✓ zatwierdza go i pokazuje następną kość. Dotyczy to różnych
   składników obrażeń, puli 2k6/3k12 oraz dwóch k20 przy przewadze lub
   utrudnieniu. Dopiero ostatnie ✓ rozlicza cały rzut i dolicza premie;
   wcześniej zatwierdzone wyniki pozostają widoczne i są zachowane w zapisie.
6. Dokończ kolejkę obron, obrażeń, przesunięć i odzysku, następnie wróć
   do swojej tury. Po opłacie nie ma zwrotu zasobów przez cofnięcie.

Gwiazda pokazuje aktualne PW, KP, ładunki, osłony, stany, pasyw, odzysk,
skazę i wyposażenie. Otwieranie informacji nie zmienia podglądu ani opłat.
W spoczynku −/+ przegląda uczestników bez zmiany aktywnej tury.

W panelu testowym można rozpocząć nową próbę od dowolnego z siedmiu
bohaterów. To **reset przykładu**, nie darmowa zmiana postaci w środku tury.
„Zapisz próbę” / „Wczytaj próbę” używają osobnego wpisu `localStorage`.
Zapis obejmuje również opłaconą akcję, oczekujący rzut, Hymn i kolejkę Haka;
wczytanie nie ponawia efektów ani nie wykonuje oczekującego zatwierdzenia.

## Co można sprawdzić

- Wszystkie 29 mocy z aktualnych kart, Skupienie 1k20, odzysk 1k4 raz
  na rundę, koszty 4/8 i dopłaty skaz. Budżety S, A+S oraz M+S.
- Uporządkowany tor, efektywne liczniki, Fala z oznaczeniem kopiowanej
  runy, dołączanie bohaterów od własnej tury i premie poza nią.
- Wieża/KP, Grot przy obrażeniach, Schody jako osobna pula ruchu, Błysk
  na początku tury i po nowej kopii, Oko bez zwiększania ST, globalny Węzeł.
- Kielich i Klepsydra jako oddzielne, zużywalne liczniki. Obrażenia
  psychiczne omijają Klepsydrę; leczenie nie odnawia żadnej osłony.
- Hak po wszystkich obrażeniach: po jednym wyborze na zranionego wroga,
  z pozostaniem na miejscu, podglądem i potwierdzeniem. Impuls najpierw
  rozpatruje swoje odrzucenie, potem Hak od nowej pozycji.
- Szarża z legalną drogą i niebieskim polem; Powalony i utrata następnego
  ruchu. Szał i krytyk Brakki. Ukrycie per obserwator, Parkour z reakcjami
  po drodze, Więzy z osobnym terminem następnej rundy.
- Hymn bez terminu, maksymalnie jeden na bohatera; decyzja po k20, przed
  konsekwencjami, fizyczna 1k6, zachowanie naturalnej kości. Pytanie jest
  dostępne także przy udanym rzucie, aby odbiorca mógł sam wybrać użycie.
- Jawne pominięcie stworzenia / „Nie pomijaj” w obszarówkach Nimry,
  Strefa ognia 3×3, wspólna kość obrażeń i oddzielne obrony.
- Przeciwnicy mają własne tury, ruch i ręcznie rozstrzygane ataki.
  Okazyjne bohaterów można przyjąć lub odrzucić, bez kosztu ładunków;
  przeciwnicy korzystają z dostępnej reakcji automatycznie. Rzuty nadal
  wymagają potwierdzenia. Rezonans działa w reakcjach, również Hak.

## Jawne założenia i granice próby

Przyjęto robocze doprecyzowania ze
[specyfikacji](../RESONANCE_RUNTIME_SPEC.md), do oceny przed produkcyjnym
wdrożeniem: nowa runa podnosi premie dotychczasowych uczestników, przyrost
osłony dodaje tylko nowe 2 punkty, Schody zużywane są przed bazowym ruchem,
Fala kopiuje jedną poprzednią efektywną runę (pierwsza nie daje bonusu).
Błysk leczy na początku własnej tury; wcześniejsi uczestnicy nie dostają
natychmiastowego leczenia po cudzym Błysku. Powalony wstaje na początku
swojej następnej tury, tracąc cały ruch. Nieprzytomne figury pomijają turę;
samo pominięcie nie zamyka łańcucha. Ostatnie założenie nadal wymaga
decyzji dla właściwego silnika.

Przykład krytyka Brakki: bazowe 1k12 → 3k12, hipotetyczne bazowe 2k6 →
4k6, a nie 6k6. Pasyw dodaje dwie pojedyncze kości broni, modyfikator raz.
Kości dodatkowych efektów i Grota zachowują robocze podwojenie na krytyku.
Grot w trafieniu mieszanym przyjmuje typ pierwszego składnika źródła.

Arena 12×10 i trzech przeciwników są **danymi demonstracyjnymi**. Kolejność
tur jest stała: wybrani bohaterowie, potem wrogowie. Figury zajmują jedno
pole. Drogi uwzględniają blokady, zajętość, narożniki i przykładowy trudny
teren; widoczność jest uproszczonym testem od środka pola do środka pola.
To nie zastępuje docelowej topologii/LoS planszy. Nie ma tu AI przeciwników,
zużycia amunicji i ekwipunku kampanii, testów śmierci ani obrażeń okresowych
z zewnętrznych źródeł. Świeża próba resetuje cały fixture, także Hymny;
w ramach próby i jej zapisu Hymn nie wygasa przy rundzie ani końcu łańcucha.

## Pliki i kontrola

- `resonance-data.js`: generowane dane kart i startowych statystyk, bez
  modyfikowania danych rozmów w `rune-prototype-data.js`.
- `resonance-model.js`: deterministyczny stan i serializowalna kolejka
  wyłącznie symulacji; nie importować tego modułu do silnika Python.
- `resonance-prototype.js` / `.css`: prezentacja i wejście mocka.
- `rune-prototype.js`: istniejąca powłoka, routowanie walki do nowego modułu.

Odświeżenie danych po korekcie kart:
`PYTHONPATH=src .venv/bin/python scripts/build_resonance_mock.py`.

Testy: `scripts/safe_pytest.sh --timeout 60 tests/unit/test_resonance_mock.py`
oraz osobno `tests/unit/test_rune_prototype_browser.py` (regresja reputacji
i wyprawy). Testy wymagają lokalnego Chrome. Nie łączyć równoległych pytest.

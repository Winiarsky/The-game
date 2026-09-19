# Garran — cztery arkusze i wyposażenie do wycięcia

Prototyp nowego układu, do sprawdzenia przy stole. Nie zastępuje jeszcze
opublikowanych zestawów wszystkich postaci ani nie zmienia mechaniki gry.

## Pliki do wydrukowania

- `garran_zestaw_A4.pdf` — pięć stron: postać i historia, mata many,
  akcje, pusta mata wyposażenia, sprzęt startowy do wycięcia.
- `sciagawka_druzyny.pdf` — jedna strona, **jedna kopia dla całej drużyny**.
- `podglad.html` / `podglad.png` — przegląd wszystkich stron.
- Poszczególne strony są też dostępne osobno jako HTML, PDF i PNG.

Druk jednostronny, **100% / rzeczywisty rozmiar**, bez dopasowywania do strony.
Druga strona jest A4 poziomo, pozostałe pionowo. Pozwól drukarce automatycznie
obracać strony, ale nie skalować. Na arkuszach pionowych jest odcinek 50 mm
do kontroli wydruku. Na macie many sprawdź linijką prostokąt 63 × 88 mm.

## Użycie

1. **Postać:** bieżąca historia, motywacje, cechy, bazowe PW/KP/ruch/inicjatywa,
   skaza oraz metody konfrontacji z NPC i obiektami. Portret w skali szarości.
   Metody opisuje kolejność: kontekst → nazwa → działanie i mechanika testu.
   „Moje zobowiązania i cele” to miejsce na odręczne notatki podczas kampanii;
   cel osobisty z biografii pozostaje wydrukowany wyżej.
2. **Mana:** pięć pełnych miejsc na karty **63 × 88 mm**, bez wsuwania pod arkusz.
   Kolory mają oddzielne stosy. Punktacja i pasywy pozostają widoczne obok kart.
   Kolejne karty tego samego koloru kładź na stos; licznik puli jest również w UI.
   To wymiar kart bez koszulek; większe koszulki mogą zachodzić na opisy i odstępy.
   Gruba obwódka symbolu oznacza kumulację, cienka brak kumulacji.
   Pasywy walki i eksploracji mają oddzielne bloki z odstępem; czarny nagłówek
   oznacza walkę, jasny eksplorację. Bloki zaczynają się na tej samej wysokości
   przy każdym kolorze w danym rzędzie.
3. **Akcje:** dziewięć zdolności w ramkach **62 × 76 mm**, ułożonych w kolejności
   run panelu. Arkusza nie trzeba ciąć. Przyszła karta zastępująca akcję powinna
   mieć ten wymiar i runę zgodną z przypisaniem w aplikacji. Ten prototyp nie
   implementuje jeszcze rozwoju ani podmiany akcji w aplikacji.
4. **Wyposażenie:** puste miejsca na pancerz, głowę, obie ręce, szyję,
   pierścień i ognisko/instrument oraz zbiorczy plecak. Sześć ramek plecaka
   to porządek na stole, nie nowy limit ekwipunku. Więcej żetonów można piętrować.
5. **Wycinanki:** dziewięć przedmiotów startowych, każdy **60 × 42 mm**,
   i znacznik zajętej drugiej ręki. Połóż miecz w pierwszej ręce, tarczę w drugiej,
   kolczugę w pancerzu, pozostałe rzeczy w plecaku. Broń oburęczna zajmuje dwa
   sloty: żeton plus znacznik. Fizyczne przekazanie żetonu musi odpowiadać
   zatwierdzonej zmianie wyposażenia w aplikacji podczas przygotowania.

Przedmioty z Misji 0 pozostają w dotychczasowym zestawie scenariusza.
Nie są częścią startowego wyposażenia Garrana.

## Źródła i edycja

Generator: `python scripts/build_garran_set_concept.py` (z katalogu repozytorium).
Korzysta z zainstalowanego Chrome, Popplera i wspólnych funkcji eksportu PDF;
nie wymaga nowych zależności. Nie uruchamia gry ani nie łączy się z planszą.

- Statystyki, historia, skaza, pasywy, progi, koszt i runy: aktualny
  `build_print_hero('garran')` i katalog gry.
- `copy.json`: skrócone opisy działań, podbić i sprzętu. Edytowalne ręcznie;
  to warstwa redakcyjna prototypu, nie nowe definicje reguł. Przy zmianie
  mechaniki należy uzgodnić je z katalogiem przed ponownym eksportem.
- Ilustracje sprzętu: istniejące czarno-białe obrazy `equipment_art`.
- Portret: wariant komiksowy Garrana w paczce Misji 0; skala szarości w CSS.
- `source_snapshot.json`: zapis danych postaci użytych do ostatniego eksportu.
- `dimensions.json`: wymiary arkuszy, kart i żetonów.
- `validation.json`: kontrola przepełnienia, granic stron, stopek, grafik
  oraz wymiarów elementów w Chrome. Eksport sprawdza również jedną stronę
  w każdym PDF przed połączeniem pięciu stron Garrana.

Pozostaje ocena fizycznego wydruku: wygoda stosów many, czytelność małego
druku przy przedmiotach i wielkość arkuszy na wspólnym stole.

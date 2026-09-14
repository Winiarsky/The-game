# Arena i wszystkie karty — wspólny wydruk A4

Gotowy plik: [arena_i_karty_A4_czarno_biale.pdf](../assets/maps/recruitment_arena/print/arena_i_karty_A4_czarno_biale.pdf).

67 stron, jednostronnie:

- 1: instrukcja składania, przymiar 50 mm, legenda i spis postaci;
- 2–10: arena A1–C3, dziewięć poziomych arkuszy A4;
- 11: 19 osobnych znaczników terenu do wycięcia;
- 12–67: komplet siedmiu postaci w formacie `bw_test`, z 66 zdolnościami (9 na postać, 12 dla Nimry),
  statystykami, pasywami, skazami, 14 metodami eksploracji i zasadami many. Bez rewersów.

Drukuj na A4, **100% / rzeczywisty rozmiar**, z automatycznym obrotem stron,
bez dopasowywania do papieru. Najpierw zmierz przymiar ze strony 1.
Wersja z 2026-09-08 zawiera korektę **250/244 = 102,459%** pod zgłoszony
pomiar wydruku. Korekta obejmuje mapę, panel, linie cięcia, zakładki, znaczniki
terenu oraz przymiar; karty postaci zachowują swoją skalę. **Nie dodawaj tej
korekty ponownie w oknie drukowania.** Najpierw wydrukuj stronę 1.

Docelowa mapa po skorygowanym wydruku ma **750 × 500 mm**, czyli 30 × 20 pól
po **25 mm**. Sam PDF ma teraz pole około **25,6148 mm**, aby skompensować
zmniejszenie do 97,6% zgłoszone przy wydruku. Jeżeli drukarka drukuje bez tego
zmniejszenia, wynik będzie większy — przymiar 50 mm pozwala to sprawdzić.
To dotychczasowa skala fizycznych map projektu. Dolne runy pozostają nadrukowane, ale pola akcji 0–25 są nieaktywne; narożne −, +, ✓ i ↩ pozostają aktywne. Dolne 30 pól zajmuje panel;
pole po usuniętej Interakcji pozostaje puste. Ruch ma ikonę idącej postaci.

Mapa to pusta siatka i panel obsługi. Nie ma nadrukowanych pozycji Nessy,
bohaterów, kukieł ani terenu. Figurki ustawia się według setupu w aplikacji.

Arkusz terenu zawiera osobne kwadraty 25 × 25 mm: 3 × ZASŁONA,
2 × SKRZYNIE, 4 × FILAR, 2 × OSŁONA i 8 × GRUZ. Każdy znacznik ma
czytelny podpis i czarny symbol na białym tle. Wytnij je po obrysie;
można je przestawiać i układać w innych konfiguracjach.

Setup areny osobno wskazuje każdy rodzaj znacznika i podświetla tylko jego
pola. Dłuższy pas gruzu jest rozkładany w dwóch krokach. Nazwy w instrukcjach odpowiadają podpisom na wydruku. Pełne przeszkody
blokują ruch i widoczność; niska osłona pozwala wejść i daje +2 KP;
gruz podwaja koszt ruchu, bez osłony. Rozstawienie i reguły scenariusza
pozostają w aplikacji — wydruk nie koduje ich na stałe.

## Cięcie i klejenie

Wytnij zewnętrzny przerywany obwód każdego arkusza. **Zachowaj zakładki 10 mm**
po prawej i na dole, jeżeli dany arkusz je ma. Linia z drobnych kropek to
granica części widocznej, a nie linia cięcia. Na zakładce znajduje się
powtórzony fragment mapy oraz napis wskazujący, który arkusz ma go przykryć.

Sklej kolejno A1 → A2 → A3, potem rzędy B i C. Następnie nałóż rząd B na
dolne zakładki rzędu A, a C na zakładki B. Smaruj podpisane zakładki klejem
lub przyklejaj na nich taśmę dwustronną. Zwykłą taśmę można dać od spodu.
Dopasuj siatkę; napisy o kleju zostają pod kolejną częścią. Zakładki nie
powiększają planszy i nie są dodatkowymi polami.

## Ponowne generowanie i weryfikacja

`python scripts/build_arena_print_pack.py`

Generator używa bieżącego scenariusza, wspólnych symboli panelu i kanonicznego
generatora kart. Każdą postać generuje od nowa, bez kopiowania starszych PDF-ów.
Wymaga już używanych w projekcie Chrome/Chromium i narzędzi Poppler
(`pdfinfo`, `pdfunite`); nie dodaje zależności. Oprócz PDF zapisuje
pełnowymiarowy SVG, części HTML/PDF i manifest wymiarów, zakładek i stron.

Testy: `scripts/safe_pytest.sh --timeout 60 tests/unit/test_arena_print_pack.py -q`.
Sprawdzają pełne pokrycie 600 pól, zakładki i marginesy, skalę viewportów,
pustą siatkę, 29 ikon ze stałym pustym polem i zgodność znaczników z setupem. Osobno sprawdzono aktualne
karty, rozmiary wszystkich 67 stron, kompletność tekstu i podgląd PDF.

To pakiet do wydruku i testów układu. Podłączenie całego panelu do obsługi
aplikacji pozostaje zadaniem z [planu wdrożenia](ARENA_PANEL_IMPLEMENTATION_PLAN.md).

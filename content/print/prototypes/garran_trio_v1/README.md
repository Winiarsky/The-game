# Garran — koncept pierwszego arkusza zestawu 1/3

Prototyp układu do oceny i fizycznej przymiarki. Pierwszy arkusz zawiera
statystyki, sześć cech z modyfikatorami, skazę, progi naładowania, osobiste
wartości pięciu kolorów oraz obok siebie pasywy walki i eksploracji.

- `garran_01_postac_i_mana_A4.pdf` — jedna strona A4, druk 100% bez dopasowania.
- `garran_01_podglad.png` — podgląd arkusza.
- `garran_ulozenie.png` / `.html` — przykład ułożenia z kartami pod arkuszem.
- `garran_01_postac_i_mana_A4.html` — wersja do otwarcia i druku w przeglądarce.
- `dimensions.json` — wymiary oraz położenie pięciu miejsc na stosy many.

## Przymiarka

1. Wydrukuj PDF w skali 100%; linia kontrolna na dole powinna mieć 50 mm.
2. Wytnij arkusz po zewnętrznym prostokącie: 190 × 277 mm.
3. Obróć karty 63 × 88 mm bokiem: przy krawędzi arkusza zajmują 63 mm wysokości.
4. Czerwoną, zieloną i niebieską manę wsuwaj z lewej; białą i czarną z prawej.
   Zostaw około 18 mm karty na zewnątrz. Strzałki wskazują wsuwanie pod arkusz;
   nie przykrywaj kartami tekstu na wierzchu.
5. Kolejne karty danego koloru możesz wysunąć o dalsze 3 mm, żeby policzyć stos.

Prowadnice mają wysokość 66 mm. Odstęp kolejnych stosów po tej samej stronie
wynosi 67 mm — karty bez koszulek nie nachodzą na siebie. Jest też miejsce
na koszulkę o krótszym boku do 66 mm; większe koszulki wymagają przymiarki.
Podgląd pokazuje schematyczne karty many, nie reprodukcje kart Magic.
Arkusz z jednym wystającym stosem z każdej strony zajmuje około 226 × 277 mm
na stole; dodatkowy wachlarz kart zwiększa szerokość.

Cienka/gruba obwódka symbolu zachowuje obecne oznaczenie kumulacji. U Garrana
status kumulowania każdego koloru jest taki sam w walce i eksploracji,
więc jeden symbol w kolumnie many opisuje oba pasywy.

To pierwszy arkusz koncepcji trzyczęściowego zestawu, nie gotowy zestaw trzech
stron. Pozostałe arkusze wymagają dalszego projektu. Główne zestawy wydruków
pozostają dostępne w dotychczasowym układzie.

## Źródła i ponowne generowanie

`python scripts/build_garran_sheet_concept.py`

Generator pobiera statystyki oraz wszystkie opisy z `build_print_hero('garran')`,
a więc z tych samych danych co działająca gra i aktualne karty. Nie kopiuje
wartości cech ani pasywów do osobnego katalogu. Geometria i CSS są w generatorze.
PDF powstaje przez lokalny Chrome; grafika interfejsu i symbole pozostają
wektorowe, tekst można zaznaczać.

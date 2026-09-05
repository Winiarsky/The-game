# Bohaterowie startowi

Gra rozpoczyna się wyborem spośród siedmiu gotowych archetypów na poziomie 3. Nie są
wybrańcami sterującymi losami wojny. To ludzie, którzy próbują wykonywać swoją
pracę, realizować osobiste cele i przeżyć w świecie zamkniętych granic,
przesiedleń, kryzysów i cudzych konfliktów.

Pełne, wyświetlane graczowi instrukcje są wersjonowane w
`src/dnd_board_game/character_creation/archetypes.py`. Każdy profil zawiera:

- krótką historię, motywację i osobisty cel;
- rolę w drużynie oraz trzyczęściowy plan typowej tury;
- zasoby odnawiane podczas odpoczynku;
- mocne strony i najczęstsze pułapki;
- stały kod pomocniczy i payload karty bohatera.

## Skład startowy

| Karta | Bohater | Klasa | Rola |
|---|---|---|---|
| BR-01 | Brakka | Barbarzyńca | pierwsza linia i ochrona |
| LO-01 | Lorian | Bard | wsparcie, rozmowa i kontrola |
| DA-01 | Dagna | Kleryczka | pancerne wsparcie i ratunek |
| GA-01 | Garran | Wojownik | stabilna pierwsza linia |
| ER-01 | Erynd | Łowca | zwiad i ostrzał |
| MI-01 | Mira | Łotrzyca | ekspertka i precyzyjne obrażenia |
| NI-01 | Nimra | Czarodziejka | elastyczna magia i wiedza |

## Rozpoczęcie gry

1. W Nowej grze porównaj role, styl gry, złożoność, zdolności i skazy.
2. Zaznacz od 1 do 5 bohaterów myszą lub klawiaturą, a następnie wybierz Dalej.
3. Wybierz scenariusz i rozpocznij przygotowanie planszy.
4. Powrót do wyboru drużyny zachowuje zaznaczenia.

W walce korzystamy z klawiatury i arkuszy postaci: skrót otwiera podgląd,
Enter zatwierdza, Esc lub Backspace wraca bez kosztu. Cele i ruch wskazuje się
na fizycznej planszy. Mysz pozostaje w rozwijanym wyborze awaryjnym.

Aktualne opisy zasad, zasobów i skrótów całej siódemki znajdują się w
[referencji archetypów](BOARDGAME_ARCHETYPES_LEVELS_1_3.md), odtwarzanej przez
generator arkuszy. Wspólne pasywy i skazy aplikacji oraz wydruków pochodzą z
`src/dnd_board_game/character_creation/boardgame_help.py`.

## Wybór wykonawcy testu

Gdy aplikacja pyta, kto wykonuje test, gracz skanuje kartę tego bohatera.
Jeżeli dozwolona jest Pomoc, drugi skan wybiera pomocnika. Po wyborze
prowadzącego karta `ACCEPT` przechodzi dalej bez pomocnika. Plansza nadal służy
do ruchu, pozycji, celów i obszarów, lecz nie do deklarowania tożsamości.

## Poziom startowy i rozwój

Wszyscy bohaterowie zaczynają na poziomie 3, otrzymują premię archetypu `+2`
do głównego atrybutu i od pierwszej sceny mogą korzystać ze wszystkich kart
swojej talii. System awansu oraz odblokowywania kart jest świadomie odłożony
do osobnego etapu projektowego. Drukowane karty mają plakietkę `OD STARTU`;
poziom pochodzenia zdolności pozostaje wyłącznie w manifeście technicznym.

Siedem kart bohaterów to pula dostępnych postaci, nie rozmiar jednej drużyny.
Ze względu na obecną planszę i interfejs scenariusz nadal przyjmuje od 1 do 5
bohaterów.

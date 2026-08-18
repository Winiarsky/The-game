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

1. Na ekranie wybierz scenariusz.
2. Zeskanuj od jednej do pięciu kart bohaterów. Kolejność skanów jest
   kolejnością drużyny.
3. Powtórny skan tej samej karty niczego nie duplikuje.
4. `DECLINE` usuwa ostatnio dodaną postać.
5. `ACCEPT` zatwierdza drużynę i rozpoczyna przygotowanie.

Nie ma ekranowego wyboru postaci. Awaria czytnika pozwala ponowić połączenie,
anulować rozpoczęcie lub wrócić do menu, ale nie zmienia źródła deklaracji.

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

# Bohaterowie startowi

Gra rozpoczyna się dwunastoma gotowymi archetypami na poziomie 1. Nie są
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
| SY-01 | Sylwen | Druidka | kontrola terenu i przetrwanie |
| GA-01 | Garran | Wojownik | stabilna pierwsza linia |
| PI-01 | Pim | Mnich | mobilny napastnik |
| RH-01 | Rhogar | Paladyn | obrońca i awaryjne leczenie |
| ER-01 | Erynd | Łowca | zwiad i ostrzał |
| MI-01 | Mira | Łotrzyca | ekspertka i precyzyjne obrażenia |
| VE-01 | Veyra | Czarownica | artyleria magiczna |
| KA-01 | Kael | Czarnoksiężnik | stały ostrzał i ryzykowna magia |
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

## Awans

Wszystkie postacie zaczynają na poziomie 1. Po zdobyciu odpowiedniego XP gracz
sam wybiera legalny rozwój na poziomie 2 i 3: czary, przygotowanie, styl walki,
ekspertyzę, opcje klasowe i podklasę, jeśli dana klasa wymaga ich na tym
poziomie. Nie ma z góry narzuconej ścieżki archetypu.


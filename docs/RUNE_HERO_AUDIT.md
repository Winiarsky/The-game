# Audyt zgodności postaci z runami — 23.09.2026

Przejrzano 65 kart siedmiu postaci, przyznane cechy, skazy, prezentację oraz
ścieżkę płatności. Zasady wariantu: [RUNES_RUNTIME.md](RUNES_RUNTIME.md).

| Postać | Wynik kontroli i korekta |
|---|---|
| Garran | Zachowane koszty kart i Nieustępliwość. Usunięte stare przyznanie Zrywu akcji. Sprawdzone budżety i utrzymanie Bastionu. |
| Brakka | Pierwszy Szał bez runy, kolejne za Rozwidlenie; Głód walki kończy Szał. Karta Z bara zgodna z Trójząbem. |
| Mira | Usunięte stare przyznanie Przeszywającego ataku. Zachowane aktualne Ukrycie, dym i zależność legalności celu od tego, czy widzi Mirę. |
| Dagna | Skaza otrzymuje rzeczywistą dopłatę runiczną. Usunięte Odpędzanie nieumarłych z dawnym ładunkiem. Alias Zachowania życia pokazuje limit raz na walkę. |
| Lorian | Usunięte Wielkie strojenie i dawne przyznanie Okrzyku. Potrzeba publiczności stosuje runy, uwzględnia zasięg, przytomność i grę solo. |
| Nimra | Echo działa na opłaconych mocach, z limitem +2 i trwałym zapisem serii. Usunięta samodzielna stara Metamagia i dawne znaczniki Echa. Podgląd pokazuje rzeczywisty koszt powtórzenia. |
| Erynd | Skaza stosuje dopłatę za wybrany cel, także gdy pojawia się dopiero przy drugim strzale. Nie obciąża zwykłych ataków; nie pobiera ponownie kosztu mocy ani akcji. |

Naprawiono też wspólny błąd prezentacji: pomoc cechy runicznej mogła zastąpić
jej aktualny opis tekstem z dawnego katalogu klasowego. Opisy skaz mają teraz
osobne wspólne źródło dla aplikacji, makiety i PDF. Zniknęły placeholdery skaz
oraz notka starej mocy świętego symbolu na liście ekwipunku Dagny.

Regresje obejmują wybór, cofanie i zatwierdzanie dopłaty, pełny przebieg dwóch
strzałów, granicę połowy PW, przytomność i odległość sojuszników, serię Echa,
stare zapisy i zachowanie wyposażenia/PW podczas aktualizacji opisów.
Kontrola kosztów i symboli obejmuje wszystkie 65 kart; nie jest testem balansu.
Wydruk: siedem zestawów po pięć stron, zbiorczo 35 stron; kontrola przepełnień
w Chrome. Próba na fizycznej planszy i balans skaz pozostają testem manualnym.

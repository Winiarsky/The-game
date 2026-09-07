# Poprawki po teście walki — 2026-09-06

## Plan i zakres

1. Uporządkować ukrycie Miry: wynik dla każdego obserwatora, stały status,
   priorytet podglądów LED, pasyw oraz aktualny ekwipunek.
2. Zmienić czas Szału i poprawić opis ofensywnej zdolności „Z bara”.
3. Przeprowadzać graczy przez pojedyncze kości i akceptację podsumowania;
   zastąpić tekstowe koszty w interfejsie walki symbolami.
4. Zmieścić bieżącą decyzję na mniejszych ekranach i scalić wynik przeciwnika.
5. Sprawdzić zapisy, testy, przeglądarkę i wydruki postaci.

Pliki wykonawcze: `ui/exploration_app.py`, `ui/static/exploration.js`,
`ui/static/exploration.css`, `ui/static/physical_mana.js` i `.css`,
`ui/templates/exploration.html`, `combat/class_features.py`,
`combat/physical_mana.py`, `rules/physical_mana.py`, `rules/effects.py`,
`application/combat_turn_action_flow.py`, `character_creation/physical_mana.py`
oraz nowy `character_creation/loadout_repair.py` (pod `src/dnd_board_game/`).
Regresje: `tests/unit/test_combat_playtest_polish.py`.

## Ustalenia z ostatniej sesji

Sprawdzono `data/session_observations/exploration_ui_1ba80297ec.jsonl`:
286 zdarzeń, 2026-09-05 22:23:35–22:35:00 UTC, oraz ekwipunek Miry
w ostatnim checkpoincie spotkania. Oryginalnych zapisów nie przepisywano.

- Pierwsze ukrycie: wynik 20; Mira ukryta przed S2/S3, widoczna dla S1/lidera.
  Silnik zapamiętywał te relacje, lecz ekran oczekiwania usuwał ich LED.
- Stara informacja o Panice sugerowała premię do ataków przeciwnika, choć
  wariant fizycznej many posługuje się karcianą skazą.
- „Z bara” wskazywało prawidłowego wroga, ale opis interfejsu pochodził
  z ogólnego wariantu zdolności leczącej.
- Zapis Miry nadal zawierał stary pakiet `rogue_burglar`: krótki łuk,
  strzały i sztylety. Nowy pakiet startowy miał już rapier i noże do rzucania.
- W logu są dwa uruchomienia Szału w kolejnych rundach. Dotychczasowy czas
  efektu wymuszał ponowne wejście w Szał.
- Jedno odrzucenie ruchu dotyczyło braku legalnego pola. Nie znaleziono
  zarejestrowanej awarii aplikacji. Log nie zastępuje obserwacji planszy.
- Przegląd kodu ujawnił dodatkowo pomijanie startu formularza kości podczas
  oczekiwania na API oraz pierwszeństwo ogólnej instrukcji menu nad rzutem.

## Zachowanie po zmianie

- Mira po ukryciu otrzymuje komunikat z obiema grupami przeciwników.
  W jej turze turkus oznacza „nie widzi Miry”, pomarańczowy „widzi Mirę”.
  Kolory pozostają w spoczynku; podgląd ataku, ruchu lub zdolności je zastępuje.
  Anulowanie przywraca je, jeśli ukrycie nadal trwa. UI pokazuje nazwy obu grup
  oraz licznik ukrycia względem wrogów. Nie oferuje jednocześnie dwóch akcji D.
  Zakończenie skradania jest bez many. Rozwijana pomoc wyjaśnia Atak z cienia:
  +1k6 za ukrycie przed celem lub flankę, +2k6 za oba, raz we własnej turze.
- Rozpoznany stary pakiet Miry jest naprawiany przy tworzeniu profilu i wczytaniu
  walki: rapier i cztery noże zamiast dawnego łuku/strzał/sztyletów.
  PW, waluta i pozostały ekwipunek zostają zachowane; naprawa nie odnawia
  później zużytych noży. Oddzielnie oznaczony zdobyczny łuk pozostaje.
- Szał: KON mod + SIŁ mod rund, minimum 1, z wliczeniem rundy uruchomienia.
  Efekty zachowują się między turami; licznik maleje na końcu rundy i jest
  widoczny w statusie. Koszt uruchomienia płaci się raz. Bitewny amok dotyczy
  każdej tury w Szale. Wczytanie dawnego, jednoturowego Szału w profilu many
  dostosowuje czas efektu. Generyczne postacie 5e zachowują wcześniejsze zasady.
- „Z bara” używa właściwego opisu ofensywnego i strukturalnego kosztu many.
- Koszty w podglądach walki i talii mają kolorowe symbole SVG: płomień, fala,
  liść, tarcza, spirala i gwiazdka dla dowolnej many. Różnią się też kształtem;
  etykiety dostępności i legenda podają nazwy. Mana nadal jest fizyczna.
- Każda kość dostaje osobny krok i fokus. Enter przechodzi dalej, po ostatniej
  kości pokazuje podsumowanie do osobnej akceptacji. Można poprawić wynik;
  przy 2k6+3 wartości 4 i 5 dają 12, a premia jest doliczona raz.
  Dobrowolne skradanie przed walką zaczyna rzuty po wyborze bohatera.
  Wybór zachowania premii raz na turę jest dostępny również przed pierwszą
  kością obrażeń. Podczas wpisywania i czytania wyniku nie uzbraja się skan.
- Wynik przeciwnika to jedna karta: trafienie/pudło, rzut, obrażenia, PW
  przed/po i potwierdzenie. Szczegóły obliczeń można rozwinąć w tej karcie.
- Bieżąca decyzja jest nad instrukcją many i szczegółami. Aplikacja przywołuje
  ją do widoku także po wyborze planszą. Na niskich ekranach zmniejsza odstępy
  i nagłówek wyboru; nie skaluje całej strony. Dłuższe treści i telefony nadal
  mogą wymagać przewijania. Okno kości ma wysokość ograniczoną do ekranu.

## Weryfikacja

122 celowane testy jednostkowe, uruchamiane kolejno przez
`scripts/safe_pytest.sh --timeout 60`, w plikach:

- `test_combat_playtest_polish.py`: 7;
- `test_combat_turn_action_flow.py`: 13;
- `test_mira_features.py`: 14;
- `test_effects.py`: 9;
- `test_level_one_class_features.py`: 31;
- `test_physical_mana.py`: 19;
- `test_mana_character_prints.py`: 13;
- `test_hero_rules_consistency.py`: 16.

Lokalny Chrome, odizolowana instancja Flask i dane testowe w `/tmp`:
sprawdzenie składni JS, startu formularza po API, fokusu, oddzielnych 2k6,
premii doliczonej raz, powrotu i korekty, zdarzeń Enter, odrzucenia wyniku 21
na k20, osobnej akceptacji i dobrowolnego skradania. Widoki 1280×600,
1440×900 i 390×844: jedna karta wyniku, bez poziomego przepełnienia.

Regeneracja wszystkich czterech formatów siedmiu bohaterów:
`PYTHONPATH=src:. python scripts/generate_mana_character_prints.py --overwrite`.
28 HTML/PDF: komplet 77 opisów, pasywy, skazy, koszty i skróty zgodne z katalogiem;
bez przepełnień stron. Zbiorcze PDF: 26/26/35/35 stron; dawne aliasy zaktualizowane.
Bieżący zestaw: `assets/physical_cards/character_sets/physical_mana_v02/`.

LED zweryfikowano jako wynik adaptera, bez uruchamiania fizycznej planszy.
Następny test przy stole powinien objąć zmianę widoczności Miry po ruchu wroga,
kilka pełnych rund Szału, czytelność kolorów i rzeczywiste tempo formularza kości.

## Koszty na kafelkach i podwójny ryk

Kafelki skrótów, awaryjna lista ekranowa i podgląd mają osobny wiersz
symboli kosztu z katalogu many. Działania bez opłaty mają podpis „bez many”.
Ruch pokazuje koszt wynikający z deklaracji i skazy Garrana, a po rozpoczęciu
nie sugeruje kolejnej opłaty. Lekkomyślny atak jest podpisany jako dopłata;
zmodyfikowany czar zawiera koszt Metamagii. To przypomnienia, bez kontroli kart.

Menu usuwa alias zdolności klasowej, jeśli tę samą zdolność udostępnia
już wybór źródła ataku/leczenia. Ogłuszający ryk Brakki ma jeden kafelek S,
który otwiera podgląd obszaru.

Implementacja: `ui/combat_menu_mana.py`, podłączenie w `ui/exploration_app.py`,
renderowanie `ui/static/physical_mana.js`, `exploration.js` i `exploration.css`.
Testy przez bezpieczny wrapper: `test_combat_menu_mana.py` (10),
`test_combat_keyboard.py` (4), `test_garran_mana_movement.py` (14).
Przeglądarka: Brakka przed/po Szale, jedno S, ikony w podglądzie, klawisze
Q/Enter/S/Esc, szerokości 1280 i 390 px bez poziomego przepełnienia i błędów JS.

## Ikony kości w kreatorze rzutów

`ui/static/dice_icons.js` dostarcza lokalne ikony SVG k4, k6, k8, k10,
k12 i k20. Kształt, oznaczenie kN i etykieta dostępności identyfikują kość
bez polegania na kolorze. Kreator pokazuje dużą ikonę obok nazwy kroku,
a podsumowanie mniejszą przy każdym składniku. Dla sumy wielu kości
widoczna jest liczba, np. 2× k6. Każdy krok rozbitego rzutu nadal pokazuje
jedną kość. Stałe wartości nie otrzymują ikony sugerującej rzut.

Podłączenie: `ui/static/exploration.js`, `exploration.css` oraz szablon
`ui/templates/exploration.html`. Wykorzystano wektorową ikonografię bez
zewnętrznych grafik i nowych zależności.

Sprawdzenie przeglądarkowe na funkcjach rzeczywistego kreatora: wszystkie
sześć typów, dwa k20 z przewagi, 2k6 i suma 8, stały wynik bez ikony,
odrzucenie wyniku powyżej zakresu, autofocus, poprawianie i zatwierdzanie.
Widoki 390×844, 1280×600 oraz 1280×720 bez poziomego przepełnienia okna.
Składnia obu plików JavaScript poprawna, brak wyjątków JS.

## Szał: dostępność ponownej aktywacji

W profilu fizycznej many „Szał” jest uruchomieniem efektu na określoną
liczbę rund. Nie jest przełącznikiem do ręcznego zakończenia. Wspólna
walidacja `rage_activation_block_reason` w `combat/class_features.py`
blokuje ponowne użycie, gdy trwa efekt tej postaci. Menu kontekstowe
oraz kafelki nie pokazują wtedy aktywacji Q, niezależnie od zużycia
akcji głównej. Żądanie ze starego UI/API jest odrzucane przed wyczyszczeniem
wyborów i zmianą zasobów. Po zakończeniu efektu aktywacja wraca.

Test `test_active_physical_rage_cannot_be_toggled_in_later_turns` odtwarza
rundę 2 z gotową akcją dodatkową, obejmuje obie dostępności akcji głównej,
zapis/odczyt, brak mutacji po odrzuconym wywołaniu i aktywację po wygaśnięciu.
`test_combat_playtest_polish.py`: 8 zaliczonych testów; dodatkowo dwa testy
Rage/Frenzy z `test_level_three_class_feature_rules.py` zachowują starszą
mechanikę dla postaci bez profilu many. Wszystkie uruchomiono bezpiecznym
wrapperem z limitem 60 sekund.

## Uderzenie tarczą — znikający test i wynik

Zgłoszenie potwierdzone w najnowszej obserwacji sesji: po wyborze celu
silnik sam losował dwa k20 i k4. W zapisanym przypadku wynik wyniósł
17 przeciw 2, 5 obrażeń i odepchnięcie na (10,11); rezultat był tylko
wiadomością, po której wracało menu.

Nowy przepływ (doprecyzowany 2026-09-07): wybór i potwierdzenie celu →
naturalne k20 Garrana → automatyczny rzut k20 przeciwnika → przy wygranej
fizyczne k6 Garrana → jawne podsumowanie efektu →
„Zastosuj wynik”. Kreator pokazuje ikony kości, autofocus i modyfikatory
Siły; gracze wpisują tylko naturalne wyniki bohaterów, a aplikacja dodaje premię dokładnie
raz. Remis wygrywa obrońca; wtedy nie ma rzutu obrażeń. Zablokowane pole
za celem uniemożliwia odepchnięcie, lecz nie obrażenia po wygranym teście.
Za przeciwników zawsze rzuca aplikacja. Rzut obrony jest wykonywany raz,
po prawidłowym wyniku Garrana; kolejne etapy zachowują ten wynik. Formularz
nie zawiera kości przeciwnika, a serwer ignoruje przekazaną przez klienta
wartość obrony. Podsumowanie pokazuje kość przeciwnika, premię i sumę.

Stan i akcja zmieniają się dopiero po zatwierdzeniu wyniku. Podgląd pola
odepchnięcia świeci na zielono; ekran prosi o przesunięcie figurki. Nie
można powtórzyć zatwierdzenia. Przed rozstrzygnięciem można anulować rzuty;
wynik już pokazany wymaga zatwierdzenia. Niedokończonego przepływu nie
zapisujemy, zgodnie z blokadą zapisywania pozostałych aktywnych rzutów.
Wczytanie innego zapisu usuwa poprzedni podgląd i nie pozwala go zastosować.

Nowe pliki: `application/shield_bash_flow.py`, `ui/shield_bash.py`,
`ui/static/shield_bash.js`. Podłączenie w `ui/exploration_app.py`, trasach,
głównym rendererze i szablonie. Logi zawierają żądanie fizycznych rzutów,
wpisane naturalne wartości, automatyczne źródło rzutu przeciwnika i ostatecznie
zastosowany wynik.

Weryfikacja: `test_shield_bash_ui_flow.py` (8 testów) i
`test_garran_features.py` (7), przez `safe_pytest.sh --timeout 60` kolejno.
Przeglądarka z rzeczywistą lokalną sesją: Enter przez k20/k6 bohatera,
automatyczne k20 przeciwnika, poprawne premie, wynik 19 przeciw 5,
10 obrażeń stosowanych dopiero po potwierdzeniu,
widoki 1280/390 px, brak wyjątków JS i sprzecznego „Brak rezultatu”.
Wyświetlenie na fizycznych LED wymaga sprawdzenia przy stole.

## Poprawki kart i tarczy — 2026-09-07

Uderzenie tarczą kosztuje akcję dodatkową i C + N. Po wygranym teście
zadaje 1k6 + modyfikator Siły obrażeń obuchowych. Odepchnięcie pozostaje
bez zmian. Można wykonać zwykły atak i tarczę w jednej turze, również po
wcześniejszym ruchu. Każde z tych działań ma własną opłatę many; dostępność
akcji dodatkowej nadal ogranicza pozostałe zdolności Garrana.

Przeredagowano siedem pasywów many i siedem skaz oraz niejasne opisy
pasywów Garrana, Miry i Brakki. Za tarczą ma przykład płatności dwiema
niebieskimi kartami za Osłonę tarczą; Nieustępliwość wyjaśnia pierwsze
rozpoczęcie ruchu, brak kolejnych dopłat i ruch po odepchnięciu wroga.

Karty zawierają wektorowe symbole many zgodne z aplikacją: płomień, fale,
liść, tarcza, spirala i gwiazda dla dowolnej many. Zachowano nazwy kolorów
oraz czytelność czarno-białą. Symbole pojawiają się w kosztach, legendzie
oraz opisach zamiany many. Wszystkie cztery formaty obejmują siedmiu bohaterów;
kanoniczne pliki i starsze odnośniki PDF prowadzą do aktualnych wydruków.

Weryfikacja tej poprawki: 56 ukierunkowanych testów (przepływ tarczy 8,
reguły Garrana 7, koszt ruchu 14, menu many 10, wydruki many 15 oraz 2
kontrole tras i etykiet starszych kart). Cały plik testów starego generatora
przekroczył limit 60 s przy generowaniu grafiki; jego dwie kontrole istotne
dla zmiany przeszły osobno. Przeglądarka: k20/k6, automatyczna obrona,
10 obrażeń dopiero po zatwierdzeniu, widoki 1280/390 px. Kontrola układu
28 dokumentów HTML: brak wyjścia treści poza karty lub stopki; czcionek
nie zmniejszono. Fizyczne LED pozostają do sprawdzenia przy stole.

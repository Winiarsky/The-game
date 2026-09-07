# Głodne Cienie — przebudowa walki v6

Wdrożenie: 2026-09-05. Aktualny układ zastępuje v5 przy rozpoczynaniu nowego
encountera Mapy 1. Ekonomia fizycznej many i statystyki przeciwników pozostają
zgodne z ich osobnymi kontraktami. Wariant solo nadal ma jednego osłabionego
Cienia; warianty 2–5 graczy używają stada z przewodnicą.

## Rozstawienie i teren

Współrzędne są zerowe: kolumny 0–19, wiersze 0–29.

- Wspólna strefa bohaterów: kolumny 5–14, wiersze 19–22, czyli 40 suchych,
  przechodnich pól. Każdy gracz wybiera wolne pole całej strefy.
- Front stada: S1 (6,17), S2 (13,17). Wschodnie obejście: S3 (17,15).
  Zachodnia presja: S4 (3,14). Przewodnica: (11,10). Solo: (10,17).
  Setup podświetla wyłącznie skład wybranego wariantu.
- Wrak jest małą, zwartą przeszkodą w centrum, w rejonie (8–11,13–15).
  Nieprzechodnia skała zajmuje (15–16,10–13); suche przejścia łączą jej
  wschodni bok z drogą powyżej i poniżej skały.
- Małe koleiny zastępują szeroki pas błota. Pień i dwie grupy skrzyń tworzą
  czytelne osłony, a południe pozostaje miejscem manewru i odwrotu bohaterów.
- Lewa droga daje osłony, środek prowadzi przez koleiny, prawa droga daje
  suche obejście i dostęp do zaplecza stada. Skarpa nie daje dodatkowego
  bonusu za wysokość: oznaczona skała jest blokadą, a ścieżka obok jest sucha.

Źródłem dokładnych pól jest `content/scenarios/ostatni_transport_01_glodne_cienie.json`.
Ilustracja jest tłem. Zasięg terenu wyznaczają obrysy SVG wygenerowane z tego
samego contentu: czerwony ciągły = blokada ruchu i widoczności, złoty przerywany
= osłona kierunkowa, niebieski kropkowany = trudny teren. Pozostałe pola są
przechodnie. Strumień zachowuje zachodnie wyjście stada.

## Decyzje przeciwników

S1 wiąże front według dotychczasowych zasad wsparcia stada. S2/S3 oraz S4
szukają pobliskich bohaterów, których naciska mniej Cieni, preferując osoby
oddzielone od sojuszników. Kandydaci mogą być najwyżej o 3 pola dalej od
najbliższego celu, aby skrzydłowy nie biegł bez potrzeby przez całą planszę.
Przeciwnik już związany walką atakuje sąsiadującego bohatera.

Pozycja ataku i bieg uwzględniają stronę podejścia; legalny ruch, koszt terenu,
blokady i dotychczasowe flankowanie nadal rozstrzyga wspólny silnik. AI jest
deterministyczne. Ataki przewodnicy, leczenie stada, premia za wsparcie i
odwrót po utracie przewodnicy lub wszystkich popleczników zachowują reguły.
Zmiana nie gwarantuje stałego rozproszenia: ruchy graczy mogą skupić stado.

## Setup i informacja dla graczy

1. Wprowadzenie do walki i dostęp do mapy.
2. Wrak, krótka skarpa i oznaczone brzegi lasu.
3. Osłony kierunkowe: przeszkoda między źródłem ataku a celem daje +2 KP
   przeciw atakom dystansowym i +2 do pasujących save'ów Zręczności.
   Samo stanie na polu osłony nie daje premii.
4. Błoto i strumień: 5 ft przejścia kosztuje 10 ft ruchu.
5. Bohaterowie wybierają szyk. Skan planszy jest głównym wejściem;
   ręczny wybór pól pozostaje pod rozwijaną opcją awaryjną.
6. Rozstawienie przeciwników odpowiednie do liczby graczy.
7. Cel walki, zachowanie przewodnicy, trzy podejścia i przypomnienie many.
   W solo instrukcja dotyczy pokonania jednego Cienia, bez przewodnicy.

Każdy krok ma mapę i legendę do rozwinięcia. Przyciski wykonania kroku są
przed podglądem mapy. Obraz mieści całą planszę, zamiast przycinać ją do
poziomego kadru. Karta zasad starcia jest dostępna przy wyborze akcji w walce,
również po wczytaniu zapisu. Karty many pozostają fizyczne; trudny teren
zwiększa koszt w stopach, nie liczbę kart płaconych za zwykły ruch.

Po walce badanie wozu wskazuje faktyczny wrak. Początkowy punkt pobojowiska
jest przy południowym podejściu, a Teren i jego pola interakcji leżą przy
suchym wschodnim boku skały. Zachowano identyfikatory i skutki fabularne.

## Mapa i wydruk

W `assets/maps/ostatni_transport_01/` znajdują się:

- `glodne_cienie_illustration_v6.png` — tło wygenerowane wbudowanym imagegen;
- `glodne_cienie_battlemap_v6.svg` — mapa graczy z siatką i obrysami;
- `glodne_cienie_print_v6.html` — wydruk 50 × 75 cm, pole 2,5 cm;
- `glodne_cienie_print_v6.pdf` — gotowy PDF, jedna strona 50 × 75 cm;
- `glodne_cienie_tactical_layout_v6.json` — eksport pól, startów i wariantów.

Drukować w skali 100%, bez dopasowania do strony. Na drukarce A4 użyć trybu
plakatowego/kafelkowania w czytniku PDF. Sprawdzić linijką pole 2,5 cm przed
mocowaniem nadruku na planszy. Linki do mapy i wydruku są w setupie.

`python scripts/build_hungry_shadows_map.py` odtwarza SVG, HTML i eksport
layoutu po zmianie contentu. PDF należy wtedy ponownie wydrukować z HTML
(z zachowaniem rozmiaru strony z CSS). Skrypt nie generuje nowej ilustracji.
Prompt i informacja o referencji: `docs/HUNGRY_SHADOWS_V6_IMAGE_PROMPT.md`.
Zgodnie z `.gitignore` grafiki i wydruki pozostają lokalnymi zasobami projektu.

## Zmienione pliki

- `content/scenarios/ostatni_transport_01_glodne_cienie.json` — teren, starty,
  role i instrukcje; `ostatni_transport_01_zawalona_droga.json` — mapa i kotwice.
- `src/dnd_board_game/combat/coordinated_pack_ai.py` — wybór celu i boku podejścia.
- `src/dnd_board_game/application/battle_setup.py` — kolejność i instrukcje setupu.
- `src/dnd_board_game/ui/exploration_app.py` — payload i zachowanie pomocy po zapisie.
- `src/dnd_board_game/ui/static/exploration.js`, `exploration.css` oraz
  `ui/templates/exploration.html` — mapa, legenda, wydruk i karta zasad.
- `src/dnd_board_game/character_creation/boardgame_profiles.py` — migracja checkpointu.
- `scripts/build_hungry_shadows_map.py`, materiały v6 i testy wymienione poniżej.
- `GAME_DESIGN.md`, `TODO.md` i specyfikacja Mapy 1 — aktualny kontrakt sceny.

## Weryfikacja

Wynik: **97 testów zaliczonych** w siedmiu plikach (40 + 13 + 12 + 16 + 10 + 4 + 2).
Testy uruchamiane pojedynczo przez `scripts/safe_pytest.sh --timeout 60`:

- `test_ostatni_transport_map0.py`: setup i LED wariantów 1–5, wybór szyku,
  zwycięstwo, Game Over/retry, zachowanie zasad po wczytaniu;
- `test_hungry_shadows_layout.py`: legalność pól, osiągalność przeciwników,
  suche przejścia po obu stronach skały, rzeczywiste osłony i kotwice eksploracji;
- `test_coordinated_pack_ai.py`: zachowanie lidera, odwrót, odrębne cele
  skrzydłowego i frontowego oraz utrzymanie celu w zwarciu;
- `test_attack_positioning.py`, `test_boardgame_profiles.py`,
  `test_encounter_setup.py`, `test_setup_led_feedback.py`: regresje.

Chrome: desktop 1440×1000 i telefon 390×844, poprawny obraz SVG, brak poziomego
przewijania, wybór czterech bohaterów, końcowa instrukcja, bez błędów JS.
Walka: karta zasad obecna, brak błędów JS i poziomego przewijania w obu rozmiarach.
Sprawdzono zgodność eksportu layoutu i grup SVG ze wszystkimi polami runtime.
`compileall` zmienionych modułów oraz `git diff --check`: poprawne.
PDF: jedna strona 1416,96 × 2125,92 pt (50 × 75 cm).

Naprawiono również wczytywanie checkpointu pustego aktora scenariuszowego:
migracja nie dopisuje mu skazy wyłącznie na podstawie identyfikatora bohatera.
Postacie z istniejącymi cechami nadal przechodzą migrację.

Pozostaje playtest przy fizycznej planszy: czy pierwszy kontakt następuje
w oczekiwanym czasie, czy obie flanki są atrakcyjne, czy warto atakować
przewodnicę, oraz jak presja stada współgra z nową ekonomią many. Testy kodu
nie rozstrzygają balansu i czytelności rzeczywistego nadruku/LED.

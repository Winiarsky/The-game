# Mapa 0 — Rekrutacja u Nessy

Opcjonalna arena do testowania aktualnych umiejętności siedmiu bohaterów,
odrębna od kampanijnej sceny gildii. Wejście: menu główne →
**Mapa 0 · Rekrutacja u Nessy**. Wybierz wariant, rodzaj kukły i bohatera.

## Przebieg

1. Nessa zaprasza jednego kandydata. Każda próba tworzy świeżą kopię gotowego
   bohatera z aktualnym ekwipunkiem, pasywami, skazą i całym zestawem zdolności.
2. Zwykły setup prowadzi przez teren, Nessę, kukłę i bohatera. Rozstawienie
   jest stałe, aby łatwo powtarzać porównywalne próby.
3. Rzut inicjatywy rozpoczyna normalną walkę: te same skróty, wybór na planszy,
   kreator fizycznych rzutów, stany, efekty i interfejs many co w kampanii.
4. Pokonaj wszystkie kukły **albo** podejdź na sąsiednie pole Nessy i wybierz
   „Nesso, kończę pokaz”. Rozmowa jest darmowa, bez many. Sąsiednia Nessa jest
   dostępna przez zielone pole na planszy i przycisk w panelu rekrutacji;
   potwierdzenie przebiega przez zwykły interfejs interakcji. Nessa nie jest
   aktorem bojowym ani legalnym celem ataku.
5. Po zakończeniu wybierz dowolnego następnego bohatera lub powtórz próbę.
   Znaczniki ukończenia nie oznaczają sprawdzenia każdej umiejętności:
   są zapisem zakończonych pokazów, także zakończonych rozmową.

## Warianty

| Próba | Przeciwnicy i pomocnik | Zastosowanie |
| --- | --- | --- |
| Podstawowa | Jedna kukła, 50 PW, KP 10, +5 do trafienia, 0 obrażeń | Ataki, ruch, skradanie, efekty i pasywy |
| Wsparcie | Jedna kukła z 1 obrażeniem; bohater zaczyna z 8 ranami; pomocnik 10/30 PW ze znacznikiem zatrucia | Leczenie, usuwanie stanu, wsparcie i przekazywanie many |
| Obszarowa | Trzy kukły po 50 PW, KP 10, +5 do trafienia, 0 obrażeń | Czary obszarowe, rozdzielanie celów, ukrycie względem wielu obserwatorów |

Kukła ma szybkość 20 ft i używa zwykłego prostego AI: podchodzi do celu
oraz wykonuje atak wręcz o zasięgu 5 ft. Nie ma szczególnych odporności.
Rodzaj celu można ustawić na humanoida, nieumarłego albo zwierzę; to
symulacja pozwalająca sprawdzić ograniczenia celu konkretnych zdolności.
Stany kontroli działają zgodnie z regułami i mogą zatrzymać kukłę.

Pomocnik nie ma swojej tury ani doboru kart. Jest legalnym odbiorcą
wsparcia Loriana (w tym fizycznej many); nie powiększa drużyny graczy.

## Mana i izolacja

Na każdą próbę przygotuj 20 kart, po 4 każdego koloru, rynek 5 i rękę
startową 3. Dalej obowiązują zwykłe zasady postaci: zachowanie do 2 kart,
dobór do 3 i pojemność 5; Lorian zachowuje do 3 i ma pojemność 6.
Karty i płatności rozliczają gracze na stole.

Fale zgłasza się i rozlicza jak w zwykłej walce. Wyjątek treningowy:
Zagrożenie i fala nie zwiększają obrażeń kukieł. Atak w próbie podstawowej
lub obszarowej nadal zadaje 0, a we wsparciu bazowo 1; normalne redukcje
obrażeń postaci nadal działają.

Brak doświadczenia i łupów. Próba nie aktualizuje postaci w katalogu
bohaterów ani kampanijnego zapisu. Zwykłe „Zapisz” zachowuje bieżącą
walkę, wariant i ukończone pokazy w osobnym zapisie areny. Aby wrócić
do niego po uruchomieniu aplikacji, otwórz arenę i użyj menu wczytywania
zapisu bieżącego scenariusza. Nie jest to automatyczny zapis po każdej próbie.

## Plansza

Mapa: `assets/maps/recruitment_arena/arena.svg`, siatka 20×30.
Współrzędne poniżej to `(kolumna, wiersz)`, liczone od zera.

| Element | Pole/pola |
| --- | --- |
| Nessa | (3,18) |
| Bohater | (9,18) |
| Kukła główna | (10,12) |
| Pomocnik — tylko wsparcie | (9,16) |
| Dodatkowe kukły — tylko próba obszarowa | (11,12), (10,11) |
| Pełna zasłona: blokuje ruch i widoczność | (6,14), (6,15), (6,16) |
| Niska osłona: +2 KP, ruch dozwolony | (13,15), (14,15) |
| Wysoki stos skrzyń: blokuje ruch i widoczność | (4,11), (5,11) |
| Kamienny filar: blokuje ruch i widoczność | (13,11), (14,11), (13,12), (14,12) |
| Gruz: trudny teren, bez osłony | kolumny 8–11, wiersze 14–15 |

Gruz podwaja koszt ruchu na jego polach: prosty krok kosztuje 10 ft zamiast
5 ft. Pas leży na bezpośredniej drodze do kukły, ale można obejść go
z obu stron. Szare pola ze znakiem × oznaczają pełne przeszkody, brązowe
z +2 niską osłonę, pomarańczowe z kamieniami trudny teren. Setup pokazuje
wszystkie elementy także na fizycznej planszy. Po zmianie rozstawienia
rozpocznij nową próbę, aby ustawić nowy teren zgodnie z setupem.

## Implementacja i sprawdzenie

Scenariusze: `content/scenarios/recruitment_arena*.json`.
Konfiguracja wariantów: `application/recruitment_arena.py`.
Przebieg i prezentacja: `ui/training_arena.py`, `ui/static/training_arena.*`,
warunkowe podłączenie w sesji UI, trasach i szablonach.

Testy `tests/unit/test_recruitment_arena.py` obejmują start wszystkich
siedmiu postaci, normalne zdolności w payloadzie, AI i obrażenia, rozmowę,
wybór Nessy z planszy, powtarzanie prób, warianty i zapis/odczyt.
Testy fal sprawdzają także utrzymanie obrażeń kukieł przy Zagrożeniu 3.
Przeglądarka: pełny przebieg Mira → rozmowa → Brakka, kreator inicjatywy,
setup, widoki 1440, 1280 i 390 px, brak poziomego przewijania i błędów JS.
Fizyczne odczyty planszy i LED wymagają sprawdzenia przy stole.

Weryfikacja 2026-09-06: 86 zaliczonych testów, uruchamianych kolejno przez
`scripts/safe_pytest.sh --timeout 60 <plik> -q`:

- `tests/unit/test_recruitment_arena.py`: 19.
- `tests/unit/test_combat_scene_interaction_flow.py`: 5.
- `tests/unit/test_physical_mana.py`: 19.
- `tests/unit/test_combat_playtest_polish.py`: 7.
- `tests/unit/test_scenario_loader.py`: 36.

Dodatkowo: poprawność XML mapy SVG, składnia Python i `git diff --check`.
Nie jest to jeszcze ręczne sprawdzenie wszystkich kombinacji zdolności.

Rozszerzenie terenu (2026-09-06): ponownie uruchomiono cały plik
`tests/unit/test_recruitment_arena.py` — 23 testy zaliczone, w tym koszt
ruchu przez gruz, blokowanie widoczności, oba obejścia, dojście do Nessy,
obecność terenu w setupie oraz wolne pola startowe wszystkich wariantów.

Korekta instrukcji osłony: setup rozdziela pełne blokady od niskiej osłony.
Na niską osłonę można wejść i zakończyć ruch; stojąca na niej figurka ma
+2 KP. Osłona na linii ataku dystansowego daje celowi +2 KP.
Elementy o różniących się zasadach nie są łączone w jeden krok setupu,
nawet gdy mają ten sam typ w danych scenariusza.

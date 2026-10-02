# Misja 0 — Sprawy pozostawione

Działająca misja wprowadzająca dla wybranej drużyny **3–6 bohaterów**.
Gramy z **laptopa przy fizycznej planszy**. Uruchom aplikację i wybierz
**Nowa gra → drużyna → Misja 0**. Runy wybierają opcje; **−/+** przegląda,
**✓** zatwierdza, **↩** wraca. Osobne ćwiczenia pozostają w
**Poligon · Samouczki postaci**. Wersja mobilna nie jest obecnym celem.

Przed grą otwórz [gotowe wydruki](../../../handouts/README.md). Teksty aplikacji i materiałów
zmienisz według [instrukcji edycji](EDITING.md), bez szukania ich w kodzie UI.

## Przebieg

Do ogrania samego przybycia i walki, bez przechodzenia odprawy i sceny z wozem:

```bash
PYTHONPATH=src .venv/bin/python -m dnd_board_game.runtime.mission_combat_ui \
  --heroes brakka garran nimra --morality 1 --board-backend hardware
```

Uruchom z katalogu repozytorium i otwórz `http://127.0.0.1:5201/play`.
Zaczynasz od fabularnego przybycia do posterunku. `--morality`: −3…−1
Solidarność, 0 Równowaga, 1…3 Bezwzględność. Bez planszy pomiń ostatni
parametr. [Opcje szybkiego startu i katalogi testowe](../../../docs/RUNNING_AND_TESTING.md#szybki-start-misji-0-po-scenie-z-wozem).

Elementy do wycięcia przygotuj przed rozpoczęciem scenariusza, z aktualnych
PDF-ów w głównym katalogu `handouts/`. Materiały są też dostępne z ekranu przygotowania gry.
Podczas intro świata, bohaterów i pierwszego wezwania **+** przewija opis
w dół, **−** w górę, a **✓** przechodzi do kolejnego fragmentu. Przyciski
pozostają widoczne; podczas przygotowania można też używać myszy. Aktualizacje
panelu zachowują miejsce w tekście, nowy fragment zaczyna się od góry.

Intro → rozłożenie Gildii i wybór miejsca figurką → odprawa oraz drukowany
rozkaz → opcjonalny komplement Loriana i negocjacja mikstury → droga i wóz
→ wyważona brama → walka z propozycją rozejmu po pierwszym pokonanym
→ eksploracja → trzy części ładunku, opcjonalne przeszukania, dług i dzwon
→ dostawa do Gildii → identyfikacja / przekazanie pierścienia → rozliczenie.

Miejsca wybieracie figurką na polach planszy. Dialogi i decyzje korzystają
z run. Kości wpisuje się przez fokus, − / +, potwierdzenie wyniku i przegląd
przed zatwierdzeniem. Współrzędne są liczone od zera.

## Gotowe materiały do druku

Wszystkie bieżące PDF-y są w głównym katalogu repozytorium `handouts/`.
To aktualny, czarno-biały komplet do testów.

| PDF | Zawartość | Strony |
| --- | --- | --- |
| [Karty postaci](../../../handouts/characters.pdf) | Siedmiu bohaterów, po pięć stron: postać, zdolności, mata wyposażenia i wycinanki | 35 |
| [Plansza A4](../../../handouts/map_a4.pdf) | Plansza 20 × 30 z panelem; dwanaście arkuszy do złożenia | 12 |
| [Pełna plansza](../../../handouts/map_full.pdf) | Ta sama geometria na jednej stronie dla drukarni, bez zakładek i oznaczeń składania | 1 |
| [Kafle Misji 0](../../../handouts/mission_0/tiles.pdf) | Instrukcja, rozmieszczenie i 18 elementów do wycięcia | 7 |
| [Przedmioty Misji 0](../../../handouts/mission_0/items.pdf) | Znaleziska, mikstury i dokumenty; również karta rozpoznanego pierścienia | 1 |
| [Rozkaz Nessy](../../../handouts/mission_0/order.pdf) | Zlecenie wręczane podczas odprawy | 1 |
| [Pokwitowania Boruta](../../../handouts/mission_0/receipts.pdf) | Dokument wręczany przy podjęciu sprawy długu | 1 |
| [Ściąga graczy](../../../handouts/reference/rules.pdf) | Wspólne zasady i relacje run | 3 |
| [Znaczniki](../../../handouts/reference/markers.pdf) | Pomocnicze znaczniki wyposażenia i efektów | 1 |

Drukuj jednostronnie, **100%, bez dopasowania**. Wybierz planszę A4 albo
jedną pełną planszę; oba pliki przedstawiają ten sam podkład. Mapa i kafle
mają wspólną kalibrację **`(250/244) × 1,03`**, już uwzględnioną w PDF-ach.
Nie dodawaj jej ponownie w sterowniku. Pełna plansza ma
około **791,5 × 527,7 mm**, a pole w pliku około **26,383 mm**.
Porównaj próbny wydruk z fizyczną planszą przed drukowaniem całego kompletu.
Figurki, kości i talia do konfrontacji są wielokrotnego użytku.

Handouty rozdaj przy odpowiednich wydarzeniach. Kartę rozpoznanego pierścienia
przekaż dopiero po identyfikacji; zastępuje nieznaną — to jeden przedmiot.

Odbudowa z aktualnych źródeł, z głównego katalogu projektu:

```sh
PYTHONPATH=src .venv/bin/python scripts/build_handouts.py
```

Opcje `--only characters`, `--only maps`, `--only mission_0` i `--only reference`
odświeżają wybraną część. Pośrednie HTML, manifesty i robocze PDF-y powstają
w `.cache/handouts/`; gotowe materiały pozostają w `handouts/`.

## Nowy widok na laptopie

Rozmowa pokazuje bieżące działanie oraz jednego odbiorcę pomocy. **−/+**
zmienia odbiorcę, a jego stała runa wykonuje pomoc. **Klucz (24)** otwiera
składniki premii, **Gwiazda (25)** — efekty. W szczegółach **−/+** przewija,
**✓ / ↩** zamyka podgląd. Dobór many posługuje się symbolami kart.

Walka ma jeden pionowy tor uczestników po lewej: portrety, PW i stany.
Aktywna tura jest wyróżniona niezależnie od uczestnika oglądanego przez **−/+**.
Po prawej: wybór runy akcji, wskazanie pola figurki, podgląd celu i **✓**.
Przy wskazanym celu główne miejsce zajmują jego portret, PW, stany i warunki
akcji. **↩** cofa bieżący krok; samo oglądanie nie wydaje zasobów.
Mapa i pozycje figurek pozostają na fizycznej planszy.

Menu, dziennik i ściąga mają własną obsługę przyciskami planszy. Ich zamknięcie
przywraca właściwe przyciski bieżącego etapu. Wpisywanie kości i obowiązkowe
operacje kart zachowują swoje konteksty sterowania. Pełne ogranie bez myszy
na rzeczywistym sprzęcie pozostaje osobnym sprawdzeniem przy stole.

## Dokumenty źródłowe do druku

Przed grą przygotujcie [rozkaz odbioru](../../../handouts/mission_0/order.pdf)
oraz [pokwitowania dostaw](../../../handouts/mission_0/receipts.pdf).
Rozkaz wręcza Nessa; pokwitowania otrzymujecie dopiero przy podjęciu sprawy długu.
Oba wydruki są pozbawione informacji o ukrytych przedmiotach, premiach dialogowych
i przyszłych scenach. Edytowalne źródło: `text/handouts.json`. Odtworzenie:
`PYTHONPATH=src .venv/bin/python scripts/build_handouts.py --only mission_0`.

## Wersja kontraktu i przedmiotów

- Zlecenie: dwie skrzynie Z-1/Z-2, zapasy M-1–M-5, dokumenty K-1.
  Wszystkie trzy części muszą zostać odebrane przed wyborem losu dzwonu.
- Bezpieczny odbiór pomija opcjonalne znalezisko i zamyka pomieszczenie.
  Przeszukanie zbrojowni / kwatery używa wspólnej konfrontacji z obiektem.
  Sukces daje medalik / niezidentyfikowany pierścień; porażka sam ładunek.
  Porażka z przynajmniej jedną naturalną 1 w teście k20 uszkadza partię
  (2 sz potrącenia). Jedynka na kości wpływu nie powoduje tego warunku.
- Rozejm: pierwsze uszkodzenie naprawiają wieśniacy, plotka jest bezpłatna.
  Dokończona walka: samodzielne pakowanie i plotka za 1 sz.
  Plotka obniża ST wszystkich podejść w kwaterze o 2.
- Komplement Loriana jest jednorazowy, przed rozpoczęciem negocjacji.
  Wariant o rannych daje +2 do pierwszego testu drużyny, nie do wpływu.
- Dzwon: Gildia +10 sz; wieśniacy bez premii; Mira — odroczone 20 sz.
  Kontrakt daje 10 sz na osobę niezależnie od decyzji o dzwonie.
- Dług to osobny wybór. Z Garranem można dać osobiste poręczenie, a druk
  i przedmiot „Pokwitowania Boruta” trafiają do niego.
- Nimra może raz identyfikować pierścień na miejscu: k20 + Inteligencja
  i aktywne premie przedmiotów, ST 15; bez ładunku zakończonej konfrontacji.
  W Gildii identyfikacja jest pewna i płatna (startowo 5 sz).
- Pierścień zwiększa **wartość Siły o 1**, nie jej modyfikator. Baza cechy
  pozostaje nienaruszona. Noszony 18→19 nadal daje +4, 19→20 daje +5.
  Zdjęcie, przekazanie, uszkodzenie przedmiotu i zapis nie dublują efektu.

## Otwarte sprawy i przyszła Misja 2

Odroczona nagroda jest zapisana w `campaign_delayed_rewards_v1` w flagach
kampanii. `application/campaign_rewards.complete_mission(flags, actors, id)`
rozlicza ją dokładnie raz i zwraca zdarzenie narracyjne. Integrując ukończenie
przyszłej `misja_2`, trzeba wywołać ten punkt wejścia i pokazać narrację z
`mechanics/followups.json` / `text/bell_payment.md`, po czym zapisać wynik.
Misja 2 jeszcze nie istnieje — w Misji 0 nie ma przycisku wcześniejszej wypłaty.
Standardowa kontynuacja scenariusza przenosi flagi `campaign_*`, w tym
odroczoną nagrodę i `campaign_mission_zero_case` (dług, dzwon, rozejm).
Nowa gra nie jest kontynuacją kampanii.

Do sprawdzenia nowej wersji rozpocznij **nową Misję 0**. Starsze checkpointy
zachowują dawny etap i nie służą do ponownego oglądania zmienionej odprawy.

## Przygotowanie kafli na planszy

Setup pokazuje grafikę rzeczywistego kafla z ramką i oznaczeniem I po lewej,
a instrukcję po prawej. Nie pokazuje całej mapy. Słabsza zielona poświata
wyznacza cały obszar kafla, jasnozielone pole — jego punkt interakcji.
Pole I należy położyć nad jaśniejszym LED-em, podpis skierować ku dołowi
planszy. Każdy krok lub całą serię zatwierdza **niebieski przycisk ✓**;
podświetlone pola terenu nie służą do zatwierdzania.

- Gildia: Biuro Nessy → Arena → Wyjście → jedna figurka drużyny.
- Walka: Zbrojownia → Kwatera dowódcy → Magazynek → Dzwon i wóz → obie
  skrzynie → trzy osłony → oba kafle gruzu → oba głazy → bohaterowie i wrogowie.
  Duży kafel jest zawsze jednym krokiem, niezależnie od liczby zajętych pól.
- Po walce teren pozostaje: zmiana na jedną figurkę drużyny i kafel rozmowy
  z Borutem. Nie ma ponownego rozkładania budynków.

Kolejność, grupy `cutout_ids` i instrukcje zmienia się w `maps/setup.json`
(`guild_setup`, `battle_setup`, `post_setup`). Geometria i znaczniki pochodzą
z `maps/cutouts.json` i `mechanics/battle.json`, tak samo jak na wydruku.
Setup walki sprawdza, czy każdy z 14 kafli terenu występuje dokładnie raz.

## Co edytować

Otwarcie: `world` (krajobraz Pogranicza) → osobny portret i stała narracja
każdego wybranego bohatera, w kolejności drużyny → `party` (pierwsze wspólne
wezwanie do Nessy) → setup Gildii. Ilustracja napastników przy dzwonie pojawia
się dopiero przy dotarciu do posterunku. Pola `image` i `image_layout` we
wpisach `text/index.json` pozwalają zmienić grafikę i układ: `landscape`
(pełna scena obok tekstu) lub `portrait` (pełny portret obok tekstu).
Pozostałe wpisy domyślnie używają `landscape`. Aktualny układ jest przeznaczony
do ekranu laptopa; nie przygotowujemy osobnego wariantu mobilnego.
Nowa ilustracja: `assets/images/comic_v2/world_intro.png`; pełny prompt
w `assets/prompts/world_intro.json`, wygenerowany wbudowanym image_gen.

| Plik lub katalog | Zawartość i moment aktualizacji |
|---|---|
| `text/*.md` | Narrator, dialogi i wyniki. Edycja jest widoczna przy odświeżeniu widoku, bez powtarzania nagród. |
| `text/index.json` | Stabilne ID, tytuł, mówca, ścieżka tekstu oraz opcjonalne `image` i `image_layout`. |
| `text/ui.json` | Etykiety wyborów, instrukcje konkretnej misji i wpisy dziennika. |
| `text/ui/*.json` | Podpisy nowego UI: nawigacja, wspólne menu, rozmowy i walka. |
| `text/karty_postaci.json` | Wspólne opisy postaci, akcji, pasywów, sprzętu i samouczka; czytane przez grę i druk. |
| `text/sciaga_relacje_v03.json` | Źródło trzech stron aktualnej ściągi; tabela relacji pochodzi z katalogu v0.3. |
| `text/handouts.json` | Edytowalny rozkaz Nessy i pokwitowania Boruta. |
| `../../../handouts/` | Gotowe bieżące PDF-y; źródła i pliki robocze pozostają poza tym katalogiem. |
| `../../../.cache/handouts/` | Pośrednie HTML, PDF i manifesty generowane przy odbudowie materiałów. |
| `profiles/` | Instrukcje tworzenia tekstów i obrazów: narrator, Nessa, siedmioro bohaterów, wieśniacy i obiekty. |
| `assets/images/` | Pierwotne portrety i ilustracje; nowa oprawa komiksowa w `comic_v2/`. Zmiana pliku zmienia identyfikator cache obrazu. |
| `visuals.json` | Wybór obrazów do gry. `image_overrides` kieruje dotychczasowe nazwy na wariant komiksowy; pusta mapa przywraca oryginały. |
| `profiles/visual_style.md` | Wspólna instrukcja komiksowej kreski, żywych kolorów i zachowania wyglądu postaci. |
| `assets/prompts/` | Pierwotne prompty w `generated_images.md`; pełen zestaw promptów zmian stylu w `comic_v2.json`. Obrazy utworzono wbudowanym image_gen. |
| `maps/setup.json` | Instrukcje rozstawiania i wskazywane pola. `party: true` oznacza położenie figurki drużyny. |
| `maps/*.svg` | Źródłowe mapy z siatką, edytowalne jako tekst lub grafika wektorowa. |
| `content/print/rune_relations_v03/catalog.json` (od głównego katalogu repozytorium) | Aktualne moce wszystkich siedmiu bohaterów, koszty i kierunkowe relacje run używane przez grę oraz karty. |
| `maps/illustrations/ink_v3/` | Aktualne czarno-białe ilustracje PNG z image_gen i pełne prompty. `artwork` wskazuje plik, `print_name` krótką nazwę na kaflu. |
| `maps/symbols/*.svg` | Zachowany wcześniejszy wariant wektorowych rysunków. |
| `maps/cutouts.json` | Spis 18 kafli, skala i pola interakcji. Obrysy i zasady terenu walki są pobierane z `mechanics/battle.json`. |
| `mechanics/confrontations.json` | Opór, ST, kości wpływu, reakcje oraz położenie figurki/celu. Rozpoczęta konfrontacja zachowuje zasady z chwili startu. |
| `mechanics/battle.json` | Statystyki i ataki, teren, pozycje, cztery warianty wielkości drużyny. Wczytywane przy przygotowaniu walki. |
| `mechanics/items.json` | Przedmioty, kości mikstur, parametry pierścienia, identyfikacji i ceny. Zmiana już zdobytego przedmiotu wymaga powtórzenia etapu. |
| `mechanics/rewards.json` | Zapłata, premie za dzwon, potrącenia i cena plotki. |
| `flow.json` | Indeks etapów, pozycje punktów oraz proste przejścia `simple_next`. Złożone skutki pozostają w adapterze misji. |
| `scenario.json` | Standardowy manifest eksploracji i wyzwalacz walki. |

Opis/sukces/porażka konfrontacji są pobierane z `text/` przez ID; kopie w JSON
nie zastępują tych tekstów. Rdzeń reguł i transport przycisków pozostają wspólne dla gry. Opisy postaci,
ściąga oraz teksty nowego UI są w tej paczce i pozostają edytowalne osobno
od reguł. Szczegóły pól i odbudowy materiałów: [EDITING.md](EDITING.md).
Zmiana profilu jest instrukcją do kolejnej redakcji, **nie automatycznym nadpisaniem**
ręcznie poprawionych tekstów. W grze nie ma generowania dialogów na żywo.

## Ustalone skutki

- Nessa: pełny sukces daje jedną miksturę **2k8 + 4**. Po zbiciu połowy oporu
  proponuje **1k8 + 2**. Kontynuowanie testem lub pomocą odrzuca jednorazową
  ofertę. Przegrana nie blokuje zadania. Wyjście z rozmowy ją pauzuje.
- Po przegranej negocjacji, tylko z Mirą w drużynie, pojawia się jednorazowa
  okazja kradzieży słabszej mikstury **1k8 + 2 PW**. Runa 6: kradzież do
  wspólnego zapasu i jeden krok ku Bezwzględności; runa 7: zostawienie fiolki
  bez nagrody i zmiany postawy. Sukces i przyjęty kompromis nie dają tej opcji.
  Teksty: `text/nessa_theft.md`, `text/nessa_theft_taken.md`, podpisy w `text/ui.json`.
  Zapis zachowuje oczekującą decyzję, zdobyty przedmiot i zmianę postawy.
- Mikstura: akcja główna, cel to działający bohater lub sąsiedni sojusznik;
  fizyczne kości, ograniczenie leczenia do maksymalnych PW i rzeczywiste zużycie fiolki.
  Wspólne zapasy drużyny są dostępne przez runę mikstury w walce.
- Wóz: porażka nadal pozwala jechać dalej, ale wymaga wspólnego rzutu k4.
  W następnej walce każdy bohater ma **−2 do testów ataku i obrażeń** przez
  dokładnie tyle pełnych rund. Status jest widoczny i nie znika przy mana drainie.
- Walka: **N+2 przeciwników**, jedna oferta rozejmu po pierwszym pokonanym,
  po rozliczeniu bieżącej akcji i kart. 0 PW: zdjąć figurkę; fabularnie ranny.
  Rozejm daje współpracę opisaną wyżej. Przegrana drużyny kończy się odzyskaniem
  przytomności przy 1 PW; możecie odebrać kontrakt, ale dzwon zostaje u wieśniaków.
- Nagrody, potrącenia, identyfikacja i przekazanie pierścienia są rzeczywistymi
  zmianami ekwipunku / portfela. Ich odbiór nie może być powtarzany.

## Zapis i powtarzanie

Automatyczne punkty kontrolne: **odprawa, droga, przed walką, eksploracja**.
Menu „Punkty kontrolne” odtwarza cały stan, również ekwipunek i pieniądze,
bez dublowania łupów. Po powrocie odtwórz fizyczne ustawienie opisane w scenie.
Rozpoczęta konfrontacja po wczytaniu wymaga potwierdzenia zachowanych stosów.
Jeśli karty zostały pomieszane, użyj wcześniejszego punktu kontrolnego.

Autozapis: `misja_0_dzwon.snapshot.json` w skonfigurowanym katalogu zapisów.
Aktualizuje się po etapach narracji, wyniku konfrontacji i odebraniu jej nagród,
zdarzeniu z wozem (także rzucie na zmęczenie), walce oraz decyzjach i przygotowaniu
wyposażenia. Wynik konfrontacji zapisuje się już przed zamknięciem podsumowania.
Wczytanie zachowuje skutki i nie wymaga ponawiania ukończonego testu.
Punkty kontrolne są osobnymi kopiami początku sceny do testów; nie blokują
aktualizacji autozapisu przy kolejnej wizycie. W trakcie nierozstrzygniętej walki
lub konfrontacji autozapis pozostaje przy ostatnim zakończonym etapie.
Przyciski ręcznego zapisu są ukryte w Misji 0; wznawianie: **Wczytaj grę**.
Podsumowanie zapisuje także `misja_0_dzwon.completed.json`: pełną drużynę,
ekwipunek, pieniądze, decyzje i dziennik do dalszej kampanii. Nowa gra jest nową
rozgrywką, nie kontynuacją tego zapisu. Po restarcie aplikacji **Wczytaj grę**
pozwala wybrać zapis Misji 0 także przy innym aktywnym scenariuszu.

## Kafle do wycięcia — własne tło

Docelowe warstwy: plansza z przyciskami i LED → własne tło → kafle → figurki.
**[Kafle Misji 0](../../../handouts/mission_0/tiles.pdf)**: 7 stron,
18 elementów. Strona 1: instrukcja i spis; 2: plan rozmieszczenia;
**3–7: arkusze do wycinania**. Budynki wycinaj jako jeden prostokąt,
nie jako osobne kratki. Wycinaj **zewnętrzny obrys razem z podpisem**.
Kafle mają rozpoznawalne czarno-białe ilustracje z image_gen w stylu
zaakceptowanej próbki wozu: duża ramka przez cały obrys pól, poniżej jedna
linia **Nazwa** — działanie. Na małych blokujących kaflach krótki podpis
„blokada” oznacza blokowanie ruchu i widoczności. Gruz: **Gruz** — koszt ruchu ×2
(10 ft za pole zamiast 5 ft). To ilustracje rastrowe; ramka i podpis są wektorowe.

Granice pól wskazują kreski na zewnętrznych krawędziach. Ilustracja pozostaje
niepodzielona. Kółka I nadal odpowiadają tym samym polom interakcji; ustawiaj
według nich, a nie według narysowanych drzwi. Meble i ściany na rysunku są
dekoracją; zasady wyznaczają cały obrys kafla i podpis. Dzwon jest pokazany
jako ciężki ładunek na drewnianych płozach, zajmujący kafel 2×1.
Nominalne rozmiary: biuro 5×7, arena 5×9, zbrojownia i kwatera po 6×8,
magazynek 4×5, pozostałe kafle 1×1, 2×1 lub 3×1 pól.

Kafle używają tej samej skali **`(250/244) × 1,03`** co obie wersje planszy.
Drukuj **100%, bez dopasowania**. Odcinek kontrolny odpowiada czterem polom;
porównaj go z mapą i fizycznymi czujnikami. Nie nakładaj drugiej korekty
w ustawieniach drukarki.

- **Blokada / blokuje ruch**: w walce blokuje wejście i widoczność. Budynki, skrzynie, głazy,
  dzwon i wóz. Podczas eksploracji jedna figurka może wskazać pole w budynku.
- **+2 KP**: wejście dozwolone; figurka na kaflu ma premię do KP.
  Osłona przecinająca linię ataku dystansowego daje celowi +2 KP.
  Osłony korzystają z istniejącej reguły największej premii, nie sumują się.
- **KOSZT RUCHU ×2**: każde wejście na pole kosztuje 10 ft zamiast 5 ft.
  To koszt terenu, nie trwałe −10 ft do szybkości postaci.
- **I w kółku**: pole interakcji eksploracyjnej. Nie oznacza przejścia
  w czasie walki. P15 Rozmowa dokładamy dopiero po walce.

Rozkład jest jednakowy dla 3–6 osób; liczba i statystyki wrogów nadal się skalują.
Trzy osłony, dwa kafle gruzu i dwa głazy są obecne w danych walki, a nie tylko
na wydruku. Przy rozstawianiu aplikacja podświetla ich pola. Setup Gildii
podświetla całe biuro i arenę; koło wskazuje konkretne miejsce figurki/interakcji.
Przy okazji dopasowania obrysów procarzy i woźnicę przesunięto z zablokowanych
budynków na wolne pola obok. Nowy teren wymaga rozpoczęcia walki od nowa;
wczytany zapis trwającej walki zachowuje wcześniejszy układ.

P02 Wóz jest używany ponownie: na drodze (9,17)–(10,17), w posterunku
(9,24)–(10,24). Nie dokładaj kopii. Kafle posterunku zostają po walce;
I wskazuje punkt eksploracji, bojowe premie i blokady wtedy nie obowiązują.
W setupie i widoku misji jest link „Elementy do wycięcia”.

Ponowny eksport bieżących materiałów Misji 0 z katalogu projektu:

```sh
PYTHONPATH=src .venv/bin/python scripts/build_handouts.py --only mission_0
```

Edytuj nazwę, rodzaj i `positions` terenu w `mechanics/battle.json`, a rozmiary
miejsc Gildii i pola interakcji w `maps/cutouts.json`. Zmienione punkty muszą
zgadzać się z `flow.json` i `maps/setup.json`. Generator odrzuca nieprostokątne
obrysy, nakładanie kafli, wejście na panel i brakujące elementy walki.
HTML w cache i gotowe PDF-y są eksportem, więc po zmianie danych trzeba uruchomić generator.

## Mapy i sprawdzanie

[Plansza A4](../../../handouts/map_a4.pdf) ma dwanaście arkuszy;
[pełna plansza](../../../handouts/map_full.pdf) jedną stronę w tej samej skali.
Drukuj **100%, bez dopasowania**. W wariancie A4 zachowaj znaczniki składania;
pełny plik dla drukarni nie zawiera zakładek ani numerów kafli.
Ponowny eksport, z głównego katalogu repozytorium:

```sh
PYTHONPATH=src .venv/bin/python scripts/build_handouts.py --only maps
python scripts/evaluate_mission_zero.py --trials 10
scripts/safe_pytest.sh --timeout 60 tests/unit/test_mission_zero.py
scripts/safe_pytest.sh --timeout 60 tests/unit/test_mission_zero_browser.py
```

Testy uruchamiaj pojedynczo. Przeglądarka i eksport PDF wymagają lokalnego Chrome.
[Raport](BALANCE_REPORT.md) obejmuje wszystkie 98 składów 3–6 bohaterów, po trzy ziarna na skład:
nowe przeszukania trwają w tej próbie średnio 2,5–3,0 rund. Dla większych
drużyn są wyraźnie łatwiejsze; wynik nie uwzględnia wskazówki ani komplementu. To wartości startowe do ogrania, nie zamknięty balans.
Symulacja nie ocenia taktyki walki. Przy stole sprawdź szczególnie cztery rundy
zmęczenia, moment poddania i czy każdy gracz ma sensowny wybór.

Audio i muzyka pozostają ostatnim etapem projektu. Stabilne ID tekstów i pole
`speaker` są przygotowane jako podstawa późniejszych nagrań.

### Wybór miejsca w Gildii

Po ułożeniu kafli i figurki otwiera się wybór miejsca. Naciśnięcie pola I
biura Nessy rozpoczyna odprawę; pole I areny pokazuje informację o jej
niedostępności i pozwala wrócić. Miejsca wybieracie wyłącznie przez pola
planszy, przestawiając figurkę drużyny; nie mają przycisków ani run wyboru.
Powiązania miejsc z kaflami znajdują się w `flow.json` (`guild_points`),
a położenia pól wynikają z danych kafli. Teksty to `text/guild_hub.md`
i `text/arena_unavailable.md`.

Sceny, dialogi i instrukcje rozstawiania korzystają z obrazu po lewej
i opisu po prawej (na małym ekranie jedna kolumna). +/− przewijają treść;
opcje pozostają w dolnym pasku. Podczas wpisywania rzutu +/− zmieniają
wynik kości, zgodnie z instrukcją rzutu.

### Wspólny ekwipunek i przygotowanie wyprawy

Po wybraniu „Wyrusz” w odprawie drużyna przechodzi przez przygotowanie każdej
postaci. Początkowe wyposażenie pozostaje przy swoich bohaterach. Znaleziska,
przedmioty zadania i mikstury od Nessy trafiają do **wspólnego zapasu**.

- −/+ wybiera poprzedni/następny przedmiot bez przewijania całej listy.
- Runa przełącza zapas / wyposażenie postaci. Wybrany przedmiot można odłożyć
  albo przydzielić do zgodnego slotu. Zastępowany przedmiot wraca do zapasu.
- Sloty: pancerz, głowa, dwie ręce, szyja, ognisko/instrument, pierścień i plecak. Broń dwuręczna
  zajmuje obie ręce; uprawnienia do pancerzy i tarcz nadal obowiązują.
- ✓ zatwierdza wyposażenie i przechodzi do następnej postaci; ↩ wraca do
  poprzedniej. Na pierwszej postaci wraca do odprawy bez cofania wykonanych zmian.
- Po wyjściu wyposażenie jest zablokowane do powrotu. Mikstury pozostają
  dostępne, również bezpośrednio ze wspólnego zapasu; koszt akcji nie zmienia się.
- W Gildii przycisk „Ekwipunek drużyny” otwiera ten sam ekran. Sprzedaż
  wymaga potwierdzenia; cena wynosi połowę wartości całego wybranego stosu.
  Dokumenty, klucz i nieznany pierścień nie mają opcji sprzedaży.
- Nimra może spróbować identyfikacji bezpośrednio na ekranie odkrycia. Brak
  sukcesu nie niszczy znaleziska. Gildia rozpoznaje je pewnie za **5 sz**;
  cenę zmienisz w `mechanics/rewards.json`, pole `identification_gp`.
- Nawet rozpoznany w terenie pierścień pozostaje w zapasie aż do powrotu.
  Pierścień daje +1 do **wartości cechy**, nie +1 do modyfikatora.
- Skarbiec Misji 0 jest nadal zapisany w portfelu pierwszej postaci. Dokumenty
  są wspólne, ale dziennik pamięta Garrana jako opiekuna, jeśli poręczył sprawę.

Stan listy, kolejność postaci, wyposażenie i zapas są zapisywane. Stare zapisy
przenoszą przedmioty `mission_*` z ekwipunków do zapasu przy pierwszym wczytaniu.
Wczytanie checkpointu nadal odtwarza cały wcześniejszy stan, wraz z pieniędzmi.

Wyposażenie startowe jest częścią [kart postaci](../../../handouts/characters.pdf):
maty i wycinanki wszystkich siedmiu bohaterów. Drukuj strony wybranego składu.
Jedna karta stosu reprezentuje podaną liczbę sztuk.

[Przedmioty Misji 0](../../../handouts/mission_0/items.pdf) zawierają karty
63 × 88 mm: pierścień, medalik, mikstury, klucz i dokumenty. Karta rozpoznanego
pierścienia jest na tym samym arkuszu — podmień ją dopiero po identyfikacji.
A4, **100%, bez dopasowania**.

Odbudowa: `python scripts/build_handouts.py --only characters` oraz
`python scripts/build_handouts.py --only mission_0`. Ilustracje są czarno-białymi rysunkami tuszem w PNG; ramki i tekst pozostają
wektorowe. Sprzęt wspólny: `content/print/equipment/illustrations/ink_v2/`,
znaleziska Misji 0: `assets/items/ink_v2/`. Mapowanie w
`physical_cards/equipment_art.py` jest wspólne dla UI i wydruków. Nazwy i zasady biorą
się z rzeczywistych ekwipunków startowych i `mechanics/items.json`.

Kolejne rozszerzenia: zakupy, trening/poziomy, zestawy akcji specjalnych.
Nie mają jeszcze przycisków ani fikcyjnych transakcji w tym ekranie.

### Orientacja kafli Gildii

Gracze siedzą od strony run (kolumna 19) — to umowny dół planszy.
G01, G02 i G03 układamy podpisem ku runom, czyli obrócone o 90° w lewo
względem siatki kolumn i wierszy. Biuro zajmuje teraz kolumny 2–8,
wiersze 5–9; arena kolumny 10–18, wiersze 6–10. Pola I pozostają
na (5,7) i (14,8). Istniejące wycinanki pasują bez ponownego druku.
Podgląd i instrukcje w komplecie PDF uwzględniają nowy układ.
`maps/cutouts.json`: `size` to rozmiar papierowego kafla, `origin` to
narożnik obrysu na planszy, `board_rotation` to obrót względem siatki.

### Orientacja kafli posterunku

Wszystkie P01–P15 również układamy podpisami ku runom (obrót −90°).
Zbrojownia: kolumny 1–8, wiersze 5–10; kwatera: kolumny 10–17,
wiersze 4–9; magazynek: kolumny 2–6, wiersze 14–17. Pola I
pozostają bez zmian. Wóz zajmuje (9,24)–(9,25), dzwon (9,15)–(9,16).
Gruz przeniesiono poza inne kafle i strefę startową bohaterów; woźnica
stoi na (6,13), przed obróconym magazynkiem. Nie zmienia to parametrów
terenu ani rozmiarów papierowych kafli — istniejący zestaw nadal pasuje.

### Podejścia w konfrontacjach

Każdy bohater przed przygotowaniem talii wybiera runą podejście ze sceny.
Opcje i skierowane powiązania pomocy są w `mechanics/confrontations.json`
(`approaches`: id, nazwa, opis, cecha, ST, kość efektu, supports). Mogą się
powtarzać cechy, a podejścia oznaczone `repeatable: true` może wybrać kilku graczy; nie tworzymy osobnych metod dla każdej klasy.
Nessa: komplementy, stanowcze żądania, argumenty, blef, zrozumienie obaw i osobista gwarancja.
Wóz, zbrojownia i kwatera mają własne zestawy. Plotka nadal obniża wszystkie
ST w kwaterze o 2. Wybór trwa do końca konfrontacji.

W turze po doborze: test lub dozwolona pomoc za 1 spaloną kartę; alternatywnie
podgląd dolnej karty i pozostawienie jej na spodzie albo przeniesienie na wierzch,
bez spalania, za całe działanie. Podgląd nie zatrzymuje reakcji po rundzie.

Przy wozie **Uniesienie wozu** i **Odciążenie wozu** mogą wybrać różni
bohaterowie. Mocowanie osi, dźwignia, ocena gruntu i uspokojenie muła są dla
jednej postaci. Przydział używa tego samego widoku i run co rozmowa z Nessą.
`text/road.md` opisuje drogę i przygotowanie planszy; `text/cart_confrontation.md`
to osobny, zwięzły opis samej konfrontacji (Postęp, powiązania wsparcia).

## Postawa drużyny

Przed testem z wozem runy pozwalają wybrać naprawę lub wymuszoną zamianę
z gospodarzem: bez testu i zmęczenia, jedno pole ku Bezwzględności.
Rozpoczętej konfrontacji nie można obejść wymuszeniem. Przyjęty rozejm przesuwa
o jedno pole ku Solidarności; odmowa daje krok ku Bezwzględności. Zdarzenia deklaruje
`mechanics/ethos.json`; narracje są w `text/road.md`, `text/cart_coerced.md`,
`text/surrender.md` i `text/after_accepted.md`. Skład kolejnej talii pokazuje
wskaźnik postawy i instrukcja przygotowania. Starsze zapisy zaczynają od Równowagi;
nie doliczamy wstecz wcześniej zakończonych decyzji.

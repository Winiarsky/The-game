# Misja 0 — Dzwon do odebrania

Działająca misja wprowadzająca dla wybranej drużyny **3–6 bohaterów**.
Uruchom aplikację jak dotychczas: **Nowa gra → wybierz drużynę → Misja 0**.
Osobne ćwiczenia pozostają w **Poligon · Samouczki postaci**.

## Przebieg

Intro świata i wybranych bohaterów → setup Gildii → odprawa Nessy → opcjonalne
negocjacje mikstury → wyjście jedną figurką → wóz w koleinie → setup i walka
przy posterunku → propozycja poddania → powrót do jednej figurki → Borut,
trzy opcjonalne miejsca i plotka → decyzja w sprawie długu → załadunek dzwonu
→ powrót opowiedziany przez narratora → rozliczenie.

Wybory mają runy planszy. Podczas eksploracji posterunku można także wybrać
podświetlone pole miejsca. Kości wpisuje się przez wspólny fokus, − / +,
potwierdzenie każdej kości i końcowe podsumowanie. Przyciski ekranowe
wywołują te same komendy co plansza. Współrzędne są liczone od zera.

## Co edytować

| Plik lub katalog | Zawartość i moment aktualizacji |
|---|---|
| `text/*.md` | Narrator, dialogi i wyniki. Edycja jest widoczna przy odświeżeniu widoku, bez powtarzania nagród. |
| `text/index.json` | Stabilne ID, tytuł, mówca i ścieżka każdego tekstu. |
| `text/ui.json` | Etykiety wyborów, instrukcje misji i wpisy dziennika. |
| `profiles/` | Instrukcje tworzenia tekstów i obrazów: narrator, Nessa, siedmioro bohaterów, wieśniacy i obiekty. |
| `assets/images/` | Lokalne portrety i ilustracje. Zmiana pliku zmienia identyfikator cache obrazu. |
| `assets/prompts/generated_images.md` | Prompty dwóch nowych ilustracji wygenerowanych wbudowanym image_gen. Portrety i Nessa pochodzą z istniejących materiałów. |
| `maps/setup.json` | Instrukcje rozstawiania i wskazywane pola. `party: true` oznacza położenie figurki drużyny. |
| `maps/*.svg` | Źródłowe mapy z siatką, edytowalne jako tekst lub grafika wektorowa. |
| `maps/print/` | Gotowe PDF i HTML do druku. Po zmianie SVG trzeba ponowić eksport. |
| `mechanics/confrontations.json` | Opór, ST, kości wpływu, reakcje oraz położenie figurki/celu. Rozpoczęta konfrontacja zachowuje zasady z chwili startu. |
| `mechanics/battle.json` | Statystyki i ataki, teren, pozycje, cztery warianty wielkości drużyny. Wczytywane przy przygotowaniu walki. |
| `mechanics/items.json` | Przedmioty, kości mikstur, premia amuletu i ceny. Zmiana już zdobytego przedmiotu wymaga powtórzenia etapu. |
| `mechanics/rewards.json` | Zapłata, premia za raport, opłata za kłamstwo i cena plotki. |
| `flow.json` | Indeks etapów, pozycje punktów oraz proste przejścia `simple_next`. Złożone skutki pozostają w adapterze misji. |
| `scenario.json` | Standardowy manifest eksploracji i wyzwalacz walki. |

Opis/sukces/porażka konfrontacji są pobierane z `text/` przez ID; kopie w JSON
nie zastępują tych tekstów. Rdzeń reguł, wspólne objaśnienia mechaniki i kontrolki
UI pozostają wspólne dla gry. Wszystkie materiały fabularne tej misji są lokalne.
Zmiana profilu jest instrukcją do kolejnej redakcji, **nie automatycznym nadpisaniem**
ręcznie poprawionych tekstów. W grze nie ma generowania dialogów na żywo.

## Ustalone skutki

- Nessa: pełny sukces daje jedną miksturę **2k8 + 4**. Po zbiciu połowy oporu
  proponuje **1k8 + 2**. Kontynuowanie testem lub pomocą odrzuca jednorazową
  ofertę. Przegrana nie blokuje zadania. Wyjście z rozmowy ją pauzuje.
- Mikstura: akcja główna, cel to działający bohater lub sąsiedni sojusznik;
  fizyczne kości, ograniczenie leczenia do maksymalnych PW i rzeczywiste zużycie fiolki.
  Wspólne zapasy drużyny są dostępne przez runę mikstury w walce.
- Wóz: porażka nadal pozwala jechać dalej, ale wymaga wspólnego rzutu k4.
  W następnej walce każdy bohater ma **−2 do testów ataku i obrażeń** przez
  dokładnie tyle pełnych rund. Status jest widoczny i nie znika przy mana drainie.
- Walka: **N+2 przeciwników**. Po zejściu liczby zdolnych do walki poniżej N
  pojawia się jedna oferta poddania, po rozliczeniu bieżącej akcji/kart.
  0 HP oznacza tutaj wyeliminowanie; figurkę należy zabrać. Budynki są zamknięte
  i blokują przejście podczas walki. Szczegóły wnętrz są etapem eksploracji.
- Przyjęcie poddania: wcześniejszy koniec walki i bezpłatna plotka.
  Odmowa: walka trwa, po zwycięstwie drużyna rekwiruje narzędzia; plotka kosztuje
  1 sz. Wyeliminowanie wszystkich jedną akcją ma osobny tekst, bez przypisania
  drużynie świadomej odmowy. Przegrana to pojmanie; polegli wracają do 1 PW,
  dzwon oddawany jest w zamian za podjęcie sprawy dokumentów. Można też powtórzyć walkę.
- Zbrojownia: medalik J. R., „Wracaj. E.”. Kwatera: osobny amulet **+1 KP**,
  przypisywany wybranemu bohaterowi. Magazynek: lina. Oględziny bez dodatkowego
  rzutu; nagroda wymaga świadomego wybrania wskazanego miejsca.
- Dług: pomoc zachowuje pokwitowania i zobowiązanie; raport daje dodatkowe 5 sz
  przy powrocie; kłamliwa obietnica daje 5 sz opłaty i pozostawia niedokończoną sprawę.
  Podstawowa zapłata: **10 sz na bohatera**. Wspólny depozyt jest u pierwszego bohatera.
- Dzwon zawsze wraca w ukończonej misji. Załadunek to potwierdzane wykonanie
  czynności, bez trzeciej powtarzalnej konfrontacji.

Nagrody powstają w ekwipunku i portfelu, nie tylko w opisie. Ich odbiór jest
jednorazowy. Medalik i dokumenty pozostają na przyszłe przygody; spotkanie
żołnierza i prawnika nie jest jeszcze nową misją w tej paczce.

## Zapis i powtarzanie

Automatyczne punkty kontrolne: **odprawa, droga, przed walką, eksploracja**.
Menu „Punkty kontrolne” odtwarza cały stan, również ekwipunek i pieniądze,
bez dublowania łupów. Po powrocie odtwórz fizyczne ustawienie opisane w scenie.
Rozpoczęta konfrontacja po wczytaniu wymaga potwierdzenia zachowanych stosów.
Jeśli karty zostały pomieszane, użyj wcześniejszego punktu kontrolnego.

Zwykły zapis: `misja_0_dzwon.snapshot.json` w skonfigurowanym katalogu zapisów.
Podsumowanie zapisuje także `misja_0_dzwon.completed.json`: pełną drużynę,
ekwipunek, pieniądze, decyzje i dziennik do dalszej kampanii. Nowa gra jest nową
rozgrywką, nie kontynuacją tego zapisu. Po restarcie aplikacji **Wczytaj grę**
pozwala wybrać zapis Misji 0 także przy innym aktywnym scenariuszu.

## Mapy i sprawdzanie

PDF dla każdej mapy ma dziewięć arkuszy A4. Drukuj **100%, bez dopasowania**;
zachowaj znaczniki składania i sprawdź odcinek kalibracyjny przed całą serią.
Ponowny eksport, z głównego katalogu repozytorium:

```sh
python scripts/build_mission_zero_prints.py
python scripts/evaluate_mission_zero.py --trials 10
scripts/safe_pytest.sh --timeout 60 tests/unit/test_mission_zero.py
scripts/safe_pytest.sh --timeout 60 tests/unit/test_mission_zero_browser.py
```

Testy uruchamiaj pojedynczo. Przeglądarka i eksport PDF wymagają lokalnego Chrome.
[Raport](BALANCE_REPORT.md) obejmuje wszystkie 98 składów 3–6 bohaterów:
konfrontacje trwają średnio 3,3–3,6 rund, ale szanse sukcesu różnią się między
wielkościami drużyny. To wartości startowe do ogrania, nie zamknięty balans.
Symulacja nie ocenia taktyki walki. Przy stole sprawdź szczególnie cztery rundy
zmęczenia, moment poddania i czy każdy gracz ma sensowny wybór.

Audio i muzyka pozostają ostatnim etapem projektu. Stabilne ID tekstów i pole
`speaker` są przygotowane jako podstawa późniejszych nagrań.

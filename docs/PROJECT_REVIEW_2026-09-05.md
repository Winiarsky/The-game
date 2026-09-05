# Review projektu — UI, obsługa i gameplay

Data: 2026-09-05. Przegląd wersji `f31a208`, bez zmian w runtime.

Projekt ma wyraźną tożsamość: fizyczna plansza, figurki i kości, a aplikacja
prowadzi decyzje oraz rozstrzyga zasady. Największą wartość kolejnego etapu
widzę w dopracowaniu jednej kompletnej sesji: wyboru bohaterów, odprawy,
eksploracji, walki i jej konsekwencji. Rozbudowany silnik już daje materiał
na ciekawą grę; teraz warto zmniejszyć koszt jego obsługi przy stole.

## Zakres i wiarygodność ustaleń

Przejrzano główne dokumenty projektu, specyfikację UI, checklistę płynności,
raporty kampanii, fragmenty scenariuszy, transport UI, aktualny JS/CSS oraz
testy. Sprawdzono render testowej walki `abandoned_watchtower` w Chrome
1440×1000 i 390×844 oraz podgląd akcji Ruch. Sesja korzystała z danych
testowych, bez podłączonej planszy, z zapisem w `/tmp`.

Osobno wykonano 16 deterministycznych walk aktualnego Głodne Cienie.
Nie przeprowadzono pełnej sesji z ludźmi, rzeczywistego skanowania planszy ani
sieciowej rozmowy z Gemini. Propozycje tempa, czytelności z odległości i
balansu wymagają takiego playtestu. Raport z 3 września jest materiałem
historycznym, a nie automatycznie wynikiem bieżącej wersji.

## Potwierdzone problemy

### 1. P1 — style panelu bocznego uszkadzają układ walki

`ui/static/exploration.css:74–75` styluje wszystkie elementy `aside` jako
wysuwany panel, m.in. przez szerokość do 480 px i `translateX(100%)`.
`combatTurnActorStatsHtml()` w `ui/static/exploration.js:6671` również zwraca
`aside`. Jego własny styl nie resetuje odziedziczonych z selektora właściwości.

W przeglądarce potwierdzono przesunięcie panelu statystyk o 480 px. Desktop
ma poziomy scroll i statystyki poza właściwą kolumną. Na 390×844 pozostaje
pusta przestrzeń, a karta wyboru akcji zaczyna się około y=903; obecny był
również baner rozłączonej planszy. Mobilne `grid-row: 1` dodatkowo umieszcza
statystyki przed decyzją.

Propozycja: ograniczyć reguły wysuwania do `#side-panel`, sprawdzić szerokości
kolumn i umieścić bieżącą decyzję przed szczegółami na małym ekranie.
Nie wystarczy jedynie zmniejszyć wysokości pustego panelu.

Akceptacja: brak poziomego przewijania głównej walki; bieżąca instrukcja i
sterowanie widoczne na pierwszym ekranie; otwarcie Menu nie porusza statystyk
bohatera. Sprawdzić zarówno podłączoną, jak i rozłączoną planszę.

### 2. P1 — wybór ekranowy nie zapewnia ciągłości obsługi

`combatTurnActionMenuHtml()` (`ui/static/exploration.js:6694`) zawiera
przyciski w „Awaryjnym wyborze ekranowym”. Po przejściu do podglądu zostają
jednak tylko instrukcje Enter/Esc. W odtworzonym podglądzie Ruch przeglądarka
wykazała zero widocznych przycisków w `.combat-current-step`.

Bez klawiatury lub innego skonfigurowanego wejścia użytkownik może otworzyć
podgląd, ale nie ma równoważnego ekranowego potwierdzenia i powrotu.
Dodatkowo widoczny indeks skrótów wygląda jak zestaw przycisków, lecz składa
się z nieklikalnych `span`.

Propozycja: zachować papierową kartę i skróty jako szybkie sterowanie, lecz
zapewnić „Potwierdź · Enter” oraz „Wróć · Esc” w każdym właściwym podglądzie.
Indeks skrótów może otwierać ten sam podgląd przez ten sam dispatcher.
Nie dokładać oddzielnej ścieżki rozstrzygania zasad.

### 3. P1 — test przejścia kampanii nie zgadza się z contentem

`tests/integration/test_ostatni_transport_campaign_walkthrough.py:227`
oczekuje premii +6 dla Przewodnicy Głodnych Cieni. Aktualne źródło ataku
wraca z +3, zgodnie z `content/monsters/hungry_shadow_leader.json:45`.
Test kończy się przed weryfikacją dalszego przejścia po zwycięstwie.

To potwierdzona rozbieżność test–content, nie dowód błędnego obliczania ataku.
Najpierw należy ustalić zamierzone parametry spotkania, potem uzgodnić test
i dokumentację. Nie zmieniać balansu wyłącznie po to, aby odtworzyć starą
asercję. Powtórzyć cały walkthrough po uzgodnieniu.

## Propozycje UI i obsługi

### Jeden HUD i jedna bieżąca decyzja

PW, KP, ruch i ekonomia akcji powtarzają się w HUD-zie i panelu aktywnego
bohatera, a część dostępności ponownie w chipach. Na desktopie informacje
o stanie i skrótach często mają 9–11 px. To wymaga sprawdzenia z rzeczywistego
miejsca graczy przy stole, nie tylko z bliska na laptopie.

Proponowany układ walki:

1. Kompaktowa inicjatywa.
2. Jedna linia: bohater, PW, ruch, dostępna akcja/bonus/reakcja, krytyczne stany.
3. Dominująca karta: wybrana akcja → cel → koszt → następny krok.
4. Szczegóły postaci, wyliczenia i historia otwierane na żądanie.

W podglądzie zamiast ogólnego opisu sterowania pokazać konkret, np.
„Leczenie sojusznika — akcja dodatkowa, 1 slot; wybierz podświetlony cel”.
Po wskazaniu celu zastąpić instrukcję jego nazwą i podsumowaniem skutku.
Koszt oraz utrata koncentracji powinny być czytelne przed zatwierdzeniem.

### Wybór bohatera powinien wyjaśniać styl gry

`ui/templates/new_game.html:32` pokazuje nazwę, poziom i klasę. Nowy gracz
nie dowie się z tego, czy chce grać daną postacią ani czym różni się ona od
pozostałych archetypów.

Dodać krótką rolę, poziom złożoności i przykład charakterystycznej decyzji.
Przykładowo: Garran — obrona drużyny; Mira — mobilność i ryzykowne
pozycjonowanie; Nimra — kontrola obszaru i więcej decyzji. Szczegóły mocy
oraz skazy dostępne przed wyborem. Oznaczenia złożoności zweryfikować z nowymi
graczami; nie przedstawiać ich jako zmierzonego faktu.

### Zmniejszyć liczbę potwierdzeń, zachowując kontrolę

Kreator rzutów daje duże pole, walidację i możliwość poprawy — to dobry kierunek.
Jednocześnie każdy formularz przechodzi do dodatkowego podsumowania
(`ui/static/exploration.js:754–880`), nawet jeśli zawiera jeden wynik.
W zwykłym ataku takie kroki sumują się z wyborem akcji, celem i obrażeniami.

Przetestować wariant, w którym pojedynczy rzut zatwierdza jeden Enter, a
podsumowanie pozostaje dla kilku składników lub opcji. Zachować potwierdzenie
wydania zasobu i możliwość korekty omyłkowego wpisu. Dla obowiązkowego rzutu
nie wyświetlać obietnicy „Esc — anuluj akcję”, skoro anulowanie jest blokowane.

## Propozycje gameplayu

### Pierwsza walka ma uczyć, a potem sprawdzać

Zachować taktykę stada i jego morale. Rozważyć stopniowe wprowadzenie presji:
pierwsza runda demonstruje ruch i podstawowy atak, kolejne pozwalają odczuć
wsparcie stada oraz presję Przewodnicy. Jeżeli wymagany jest trudny start,
uprzedzić graczy o zagrożeniu w fikcji i dać czytelny sposób jego ograniczenia.

Zwycięstwo nie musi zawsze wymagać wyczyszczenia mapy. Istniejący odwrót po
utracie przywódcy lub podwładnych jest dobrym fundamentem. Długi finał lepiej
skracać jawnym, autorskim warunkiem złamania morale, ewakuacji lub wykonania
celu niż ukrytym limitem rund. To propozycja zmiany scenariusza, nie diagnoza
brakującego mechanizmu ucieczki.

### Balans mierzyć czasem i udziałem graczy

Krótka bieżąca seria: 16 walk, 11 zwycięstw, 5 porażek, 0 timeoutów przy limicie
15 rund. Garran/Dagna/Erynd przegrał 2/2 próby, obie trwały 13 rund; inna
trójka wygrała 2/2. Dwie próby na skład nie wystarczają do oszacowania jego
szans zwycięstwa. Automat nie korzysta z pełnego arsenału leczenia i kombinacji.

Przed nerfami powtórzyć większą matrycę z tymi samymi ziarnami dla wersji
porównywanych. Zmieniać jeden parametr naraz. Dodatkowo przy stole mierzyć:
czas wyboru akcji, czas obsługi po decyzji, liczbę potwierdzeń, długość walki,
czas nieaktywności gracza przy 0 PW i momenty braku jasnego następnego kroku.

### Eksploracja powinna nagradzać decyzję, nie odklikanie wszystkich tematów

Założenie krótkiej odprawy Nessy z opcjonalnym pogłębianiem wiedzy jest dobre.
Zachować wyraźną możliwość „Wiemy dość — ruszamy” po rdzeniu zadania.
Dodatkowe pytania powinny przynosić rozpoznawalny trop, przewagę lub zmianę
relacji. W kolejnej scenie warto przypomnieć przyczynę korzyści, np. wiedzę
zdobytą w Gildii, bez ujawniania technicznych flag.

Dla autorskich decyzji, takich jak pomoc Terenowi, eksponować najpierw
sytuację i stawkę, potem legalne działania. Swobodny opis powinien mieć sens
w miejscach, gdzie metoda coś zmienia; standardowego otwarcia, zebrania lub
przejścia nie warto obciążać kolejnym formularzem i oczekiwaniem na LLM.
To kryteria do playtestu scen, nie stwierdzenie, że każda obecna rozmowa łamie
te zasady.

## Utrzymanie projektu

Dokumentacja miesza stan docelowy z aktualnym. `PLAYER_UI_DESIGN.md:286`
wciąż wymienia stare menu ruchu/postaw, podczas gdy TODO i runtime opisują
uproszczoną walkę oraz skróty z papierowej karty. Specyfikacja Mapy 0 nadal
ma status „przed implementacją”, mimo obecnego scenariusza i walkthrough.
Ustalić jedną krótką, aktualną specyfikację sterowania z datą weryfikacji.

`ui/exploration_app.py` ma 34 831 linii, a `ui/static/exploration.js` 9 124.
Istniejący podział domeny i usług aplikacyjnych jest wartościowy, ale warstwa
sesji/presentacji pozostaje duża. Przy kolejnych poprawkach wydzielać małe
komponenty: HUD, podgląd akcji, prompt rzutu, reakcja. Nie uzależniać napraw UI
od wymiany frameworka lub pełnego przepisania aplikacji.

Część testów UI sprawdza obecność tekstu w JS/CSS. Uzupełnić je kilkoma
testami wykonywanymi w przeglądarce: wybór ekranowy → podgląd → anulowanie,
skrót → wskazanie → rzut, reakcja → powrót oraz widok na małym ekranie.
Sprawdzać także przewijane kontenery — sam brak overflow na `body` nie wykrył
poziomego scrolla wewnątrz widoku walki.

## Zalecana kolejność

1. Naprawić selektory `aside`, kolejność mobilną i kompletność przycisków.
2. Uzgodnić parametry przeciwnika, przywrócić walkthrough i odświeżyć kontrakt UI.
3. Uprościć HUD, zwiększyć czytelność i dopisać role w wyborze bohaterów.
4. Przetestować pełną scenę z nowymi graczami i zmierzyć koszt obsługi.
5. Dopiero na tej podstawie korygować balans, potwierdzenia i dalszy content.

## Wykonana walidacja

Wszystkie uruchomienia pytest wykonano kolejno przez `scripts/safe_pytest.sh`
z timeoutem 60 s i konkretnymi plikami/node id:

- `tests/integration/test_ostatni_transport_campaign_walkthrough.py` — 1 failed,
  rozbieżność +6/+3 opisana wyżej.
- `tests/unit/test_combat_keyboard.py tests/unit/test_launcher_ui.py` — 19 passed.
- `tests/unit/test_glodne_cienie_playtest.py` oraz
  `tests/unit/test_exploration_ui_session.py::test_combat_turn_action_payload_exposes_keyboard_shortcuts_for_nimra`
  — 3 passed.

Symulacje: `scripts/run_glodne_cienie_playtests.py --runs 2 --base-seed 93000
--max-rounds 15`, timeout procesu 60 s; wyniki w
`/tmp/project-review-20260905/balance/`.

Zrzuty bieżącej walki: `/tmp/project-review-20260905/desktop.png`,
`/tmp/project-review-20260905/mobile.png`. Dane w `/tmp` są robocze i nietrwałe.

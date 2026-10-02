# UI przy stole — audyt i propozycja

## Walka: ładunki i ciągły Rezonans — 29.09.2026

Zaktualizowano część bojową [tej samej makiety](prototype.html?scene=combat)
według aktualnych kart siedmiu postaci. Zamiast doboru/ręki: 20 ładunków,
tryby 4/8 ze skazami i uporządkowany tor Rezonansu. Nowy model symuluje
wszystkie 29 mocy, stany, rzuty, odzysk, reakcje i kolejki wyborów pól.
Wygląd powłoki, rozmowy, reputacja i przygotowanie wyprawy pozostają.
Brak wdrożenia do właściwego silnika i sprzętu.

[Instrukcja ogrania, zakres, założenia i testy](RESONANCE_MOCK.md).
Rozwijany symulator pól jest narzędziem testowym, nie nową mapą w docelowym UI.
Starsze opisy ręki, doboru i kosztów run poniżej są historyczne.

Ustalenie z 23.09.2026: wracamy do [wcześniejszej makiety UI](prototype.html)
jako punktu wyjścia. Aktualne karty zostają; następne zmiany uzgadniamy
po kolei, zaczynając od kart. Nie przenosimy kolejnych rozwiązań z makiety
koszyków do docelowego interfejsu bez omówienia ich z użytkownikiem.
Eksperyment `rune-baskets.html` pozostaje zachowany jako materiał roboczy.
Poniższy opis dotyczy wcześniejszej makiety i działającej aplikacji.

Gwiazda (osobny przycisk przed +/−, slot 25) jest stałym skrótem „Informacja o bohaterze”,
z niebieskim podświetleniem i drobnym podpisem przy panelu. Pokazuje bieżące
PW/maksimum, tymczasowe PW, KP, statusy, efekty, aurę, zużycie akcji i reakcji,
runy, reputację, cechy, sprzęt, skazę i historię. Dotyczy aktywnej postaci.
Otwarcie i powrót nie zmieniają akcji, celu ani zasobów; +/− przewijają treść.
Klucz (slot 23) przejmuje Żelazny bastion i zastępuje Gwiazdę w talii zasobów
oraz na karcie Garrana. Gwiazda nie służy już do płatnej mocy ani doboru.
Zaakceptowane przepływy wdrożono w aplikacji Misji 0. Reguły i źródła danych:
[Runy i reputacja w aplikacji](../RUNES_RUNTIME.md). Poniżej także opis makiety.

Cele ataku i mocy są wypisane informacyjnie, bez przycisków, ikon run
i przypisań do dolnego panelu. Wybór następuje przez pole figurki na planszy;
lista wskazuje wybraną postać, a ✓ uaktywnia się dopiero dla legalnego celu.
W lokalnej makiecie sygnał pola symuluje `RunePrototype.previewTargetField(row,column)`.

Przydział run odbywa się kolejno dla bohaterów. Kliknięcie runy od razu
przenosi jedną sztukę z puli do ręki aktywnej postaci. Pole świeci, dopóki
pozostaje kolejna sztuka i miejsce w ręce. ↩ cofa ostatni niezatwierdzony
wybór, przywracając runę i podświetlenie; ✓ zatwierdza przydział i przechodzi
do następnej osoby. Limit ręki 7 pozostaje. Po ostatniej osobie reszta puli
przechodzi do kolejnego obiegu bez nowego losowania. Pusta pula nie blokuje
cofania wyborów bieżącej postaci. +/− przewijają, nie zmieniają odbiorcy.

Ruch: podgląd zawiera wyłącznie limit pól i instrukcję przesunięcia figurki,
kliknięcia podświetlonego pola planszy oraz potwierdzenia. Usunięto ekranowe
kafelki odległości i ich przypisania do run. W samodzielnej makiecie sygnał
wyboru pola symuluje `RunePrototype.previewMovement(distance)`; rzeczywisty
adapter planszy nadal pozostaje poza zakresem makiety.

Korekta wyboru akcji: ekran walki pokazuje „Wybierz akcję”, bez katalogu
działań podstawowych i mocy. Runy nadal obsługują wszystkie dostępne akcje.
Wybranie pola otwiera opis tej jednej akcji: ruch pokazuje dostępny dystans,
atak i moc legalne cele, aura promień (także po zmianie wzmocnienia).
Wskazanie celu lub wariantu nie pobiera kosztu. Dopiero ✓ wykonuje działanie;
↩ anuluje podgląd. Wybór pól ruchu i figurki jest osobnym sygnałem planszy;
nie jest to podłączenie fizycznych LED ani pełna geometria walki.
Pełny katalog mocy pozostaje na kartach postaci.

Korekta doboru: runy losowane są tylko na początku pierwszej rundy walki.
Dobór pokazuje posterunek i kontekst starcia. Kolejne rundy zachowują ręce
bez nowej puli; konfrontacje społeczne korzystają z reputacji.

Nowsza korekta z 22.09.2026: rozmowy korzystają ze wspólnej reputacji (start 20),
bez doboru run. Po rzucie trzy runy wybierają jedną opcję: +1 za 1, +5 za 3
lub dodatkową k20 za 5. Wóz: próg 20, koszt zamiany 3.
[Zasady i granice makiety](../REPUTATION_PROTOTYPE.md).

Aktualizacja 22.09.2026: [makieta](prototype.html) przedstawia teraz runy v0.1:
wspólny dobór, ręce bohaterów, płatne moce i wybór reakcji. Zwykły atak
okazyjny bronią kosztuje 0 run. Dolny panel odpowiada nowym
[wydrukom](../../handouts/README.md).
`+` i `−` zmieniają wynik kości albo przewijają ekran;
podświetlenie odróżnia opcje dostępne, wybrane i zablokowane.
Garran ma robocze moce, pozostałe postacie szablony. To lokalna makieta,
bez połączenia z czujnikami i bez pełnego rozstrzygania efektów walki.
Weryfikacja: [raport run v0.1](rune-verification.json).

Poniższy audyt i starsze zrzuty opisują wersję z 20.09, sprzed zmiany zasobów.

Stan: 20.09.2026. Propozycja do obejrzenia, bez wdrożenia zmian w aplikacji.
Podgląd: [klikalna makieta](prototype.html). Otwórz plik w przeglądarce;
grafiki bohaterów korzystają z istniejącej lokalnej paczki Misji 0, a przeciwnicy
mają własne małe [portrety](assets/enemies-atlas.png). Dane w makiecie
są przykładowe, a przełączniki scen służą prezentacji projektu.
Gotowy zrzut: [ekran rozmowy](preview.png).
Pozostałe podglądy: [start](start.png), [symbole many](draw.png),
[wybór akcji](combat.png), [podgląd po runie](combat-preview.png),
[podgląd celu](combat-target.png), [atak na cel za osłoną](combat-ranged.png),
[Rozkaz: Stać! — wybór celu](combat-command-target.png),
[pomoc dla pięciu osób](help-five.png), [szczegóły stanów](combat-effects.png),
[szczegóły aury](combat-aura.png).
W rozmowie przełącznik „Pomoc” w górnym pasku pozwala porównać dwa i pięć
legalnych celów. Pasek „Runy planszy · makieta” symuluje fizyczne runy
oraz przyciski −, +, Accept i Decline wyłącznie na potrzeby tego podglądu.
Start i menu pokazują proponowaną nawigację od uruchomienia. W walce −/+
przenosi kursor po lewym torze inicjatywy. Wybierz runę akcji, obejrzyj
jej kartę po prawej, wskaż cel na symulowanej planszy i dopiero po sprawdzeniu
portretu celu oraz warunków użyj Accept. Decline wraca o jeden krok.
W rozmowie jego −/+ przełączają odbiorcę pomocy, a stałe runy odbiorców,
testu i podglądu wykonują właściwe akcje. Przyciski −/+ w samej karcie
pomocy również pozostają dostępne.

## Rekomendacja

**Ekran powinien prowadzić uwagę do aktualnej decyzji i jej skutku.**
Wspólna rama dla narracji, konfrontacji i walki; w środku zmienia się zadanie.
Fizyczna plansza pozostaje miejscem poruszania figurek, wskazywania celów
i sterowania runami. Gracze mają fizyczne karty postaci: to z nich wybierają
akcje w walce, a aplikacja pokazuje podgląd po naciśnięciu odpowiedniej runy.
Cyfrowa mapa nie jest potrzebna.

W walce jeden pionowy tor po lewej łączy całą kolejność bohaterów
i przeciwników, ich portrety, PW i stany. Aktywna tura jest wyraźnie
podświetlona, a −/+ pozwala obejrzeć inną osobę bez zmiany tury. Karta
akcji i celu po prawej pozostaje widoczna razem z torem. Usuwamy poziomy
tor oraz osobny dolny pasek drużyny w walce.

Obecny UI ma już dobry fundament: ilustracje, portrety, wyraźne runy,
zwijane zasady, oddzielny widok kości i schowane narzędzia techniczne.
Najwięcej poprawy przyniesie uporządkowanie informacji, a następnie
typografii, odstępów i akcentów kolorystycznych.

Założenie projektu: jeden wspólny ekran dla 3–6 osób, odczytywany przy stole.
Punktem odniesienia są 1300×720 i 1131×720; wąski ekran zachowuje wszystkie
informacje w pionowym układzie. Docelową drogą sterowania od uruchomienia
aplikacji są wyłącznie plansza i jej przyciski. Dotyk, mysz i klawiatura
mogą służyć sprawdzaniu makiety, ale nie mogą być wymagane do rozgrywki.

## Co obecnie utrudnia grę

| Obserwacja | Skutek dla gracza | Proponowana zmiana |
| --- | --- | --- |
| Konfrontacja powtarza opis sceny oraz karty całej drużyny podczas kolejnych mikrokroków. | Trzeba odszukać to, co zmieniło się właśnie teraz. | Po wprowadzeniu zostaje krótki cel; pełna scena na żądanie. Rozwinięty jest aktywny bohater. |
| Walka pokazuje skrót many, osobny panel many i dodatkowo informacje w oknie operacji kart. | Te same liczby konkurują z wyborem działania. | Jeden pasek stanu; centrum pokazuje tylko bieżącą operację. |
| Instrukcja i dane postaci są w osobnych przewijanych obszarach konfrontacji. | Gracz musi pamiętać, który obszar przewijają −/+. | Dane potrzebne do wyboru i sam wybór w jednym obszarze. |
| Wiele wyborów ma podobny kolor i ciężar wizualny. | Wyjście z rozmowy może przyciągać uwagę tak mocno jak jej aktualny krok. | Mocny akcent dla bieżącego działania; nawigacja spokojniejsza i zawsze w tym samym miejscu. Równorzędne decyzje fabularne pozostają równorzędne. |
| „Naładowanie”, premia testu i ładunek zdolności pojawiają się blisko siebie. | Trudno szybko ocenić korzyść z atutu. | Stałe nazwy: „Karty”, „Premia testu”, „Ładunek zdolności”; przy ofercie konkretna zmiana. |
| Menu walki przedstawia długi katalog opcji. | Ekran powiela informacje z fizycznych kart postaci i utrudnia odczytanie bieżącego kroku. | „Wybierz akcję”; naciśnięcie jej stałej runy otwiera podgląd wyłącznie tej akcji, z kosztem, efektem i ewentualnym powodem blokady. |
| „Plansza nasłuchuje” stoi obok kolejnych instrukcji gry. | Informacja o urządzeniu konkuruje z poleceniem dla człowieka. | Normalne połączenie jako dyskretny status; błąd lub konieczne działanie jako komunikat. |
| Historia komunikatów jest w narzędziach; konfrontacja pokazuje głównie ostatni wynik. | Trudno wrócić do skutku pasywu lub decyzji bez szukania w technicznych danych. | Dostępny z ramy ekranu „Dziennik”: czytelne skutki i historia narracji. |

Podstawa audytu kodu:

- [confrontation.js](../../src/dnd_board_game/ui/static/confrontation.js):
  `renderPartyConfrontation`, zwłaszcza wspólny opis, karty drużyny i sterowanie;
  `scrollConfrontation` wybiera między dwoma obszarami przewijania.
- [exploration.js](../../src/dnd_board_game/ui/static/exploration.js):
  okolice 4457–4464 — skrót i pełny panel many; 7032–7078 — indeks działań
  i sterowanie; 7853–7866 — status nasłuchu.
- [shared_mana.js](../../src/dnd_board_game/ui/static/shared_mana.js):
  okolice 165–172 — powtórzone informacje o puli i stałe objaśnienia.
- [mission_zero.js](../../src/dnd_board_game/ui/static/mission_zero.js):
  `renderMission` — pasek menu, zapisu i checkpointów nad narracją.
- [exploration.html](../../src/dnd_board_game/ui/templates/exploration.html):
  historia komunikatów w sekcji narzędzi.

Numery linii odnoszą się do stanu audytu. Starszy
[raport z rozgrywek](../playtests/2026-09-18-misja0/REPORT.md) jest kontekstem,
nie listą aktualnych błędów. Naprawione: odsłanianie szóstej postaci,
instrukcje run, techniczne liczniki i skrócenie pasywów. Dawne liczby
zgłoszeń kart dotyczą zasad sprzed modelu sześciu kart.

Oględziny bieżącego renderera w Chrome, 1300×720: odprawa, początek
konfrontacji, wybór podejść i dobór many Nessy. Sesja korzystała z kopii
stanu checkpointu, zapisy trafiały do `/tmp`, bez podłączania hardware.
W ekranie doboru automatyczne odsłonięcie aktywnej postaci przesunęło cel
i opór ponad widoczny obszar; pozostał za to komunikat poprzedniego wyboru
Nimry. To konkretny przykład, dlaczego sam automatyczny scroll nie zastępuje
hierarchii informacji. Nie był to pełny playtest misji.

## Jak wyglądałaby gra

Stała rama ma trzy części:

1. **Kontekst:** nazwa sceny, krótki cel i etap. Opór oraz talia podczas
   konfrontacji; kolejność i runda podczas walki. Bez zdradzania przyszłych scen.
2. **Bieżący krok:** kto działa, jedno polecenie, informacje potrzebne do
   decyzji, dostępne opcje z ich runami. To wizualne centrum ekranu.
3. **Uczestnicy i dostęp do szczegółów:** w rozmowie zwarta drużyna,
   zasoby i zgromadzona pomoc; w walce jeden pionowy tor wszystkich
   uczestników po lewej, z aktywną turą i podglądem wybranej osoby.
   Szczegóły i dziennik są dostępne przez sterowanie planszą.

Nie ograniczamy wszystkich ekranów do trzech przycisków. Przy wyborze
podejścia pokazujemy legalne opcje z ich runami. W głównej decyzji rozmowy
zostają trzy sekcje: **Test / Pomoc / Podgląd**. Sekcja pomocy pokazuje
jednego legalnego odbiorcę, a −/+ przełączają oglądaną osobę. Dzięki temu
liczba odbiorców nie rozbudowuje ekranu; każdy pozostaje dostępny pod swoją
stałą runą.
W walce punktem odniesienia jest fizyczna karta postaci: ekran czeka na
wybór runy, a potem pokazuje wybraną akcję. Nie potrzebuje katalogu ani grup
zdolności. Upraszczamy prezentację, zachowując wszystkie dostępne działania.

| Sytuacja | Główny ekran | Szczegóły na żądanie |
| --- | --- | --- |
| Narracja | Ilustracja, tekst sceny, dostępne decyzje. Dłuższy tekst w jednym obszarze czytania. | Historia, przypomnienie kontraktu, ustawienia. |
| Podejście | Aktualny bohater; opcje z cechą i jego modyfikatorem, ST, kością efektu, powiązaniami pomocy i wyłącznością. | Pełne karty innych bohaterów i zasady konfrontacji. |
| Przygotowanie | Dokładny skład talii, wyłączone karty, jedna aktualna instrukcja ustawienia na planszy. | Powody zmian składu i wcześniejsze instrukcje. |
| Dobór many | Dwie karty z dotychczasowymi symbolami many, runy wyboru, skutek dla tej osoby, aktualna pula, kto otrzyma pozostawioną ofertę. | Pełne warunki pasywów i księgowość pozostałych stosów. |
| Konfrontacja | Podejście aktywnej osoby; Test / Pomoc / Podgląd. Jedna karta odbiorcy pomocy ze stałą runą, kosztem i przewidywanym efektem; przy wielu odbiorcach −/+ i licznik. | Pozostałe pasywy i rozwinięte dane innych bohaterów. |
| Walka — wybór | Lewy pionowy tor bohaterów i przeciwników: portrety, PW, stany i mocno wyróżniona aktywna tura. Po prawej „Wybierz akcję”; wybór runą z fizycznej karty. −/+ ogląda uczestników. | Wszystkie efekty wybranego uczestnika, ich źródła i czas trwania oraz dziennik. |
| Walka — podgląd akcji | Niezmieniony tor po lewej; po prawej jedna karta: nazwa i runa, koszt, efekt oraz instrukcja wskazania celu lub powód niedostępności. | Obliczenia dotyczące tej akcji. |
| Walka — podgląd celu | W tej samej karcie portret, nazwa, PW i stany celu, dystans, widoczność, osłona, przewaga/utrudnienie z powodami, końcowy wzór rzutu i koszt. Accept wykonuje dopiero legalną, aktualną deklarację; Decline wraca do wyboru celu. | Składowe końcowych wartości i powody blokady. |
| Rzut | Właściwe kości, fokus na aktualnie wpisywanej i postęp przy wielu kościach; naturalne wyniki, „Aplikacja doliczy +X”, ST i podsumowanie do zatwierdzenia. Zachowana przewaga/utrudnienie; potem osobno wpływ/obrażenia. | Rozpiska modyfikatorów. |
| Obsługa kart | Konkretna czynność, np. „Przełóż najstarszą spaloną kartę na spód talii”; bieżący postęp i właściwe potwierdzenie. | Wyjaśnienie reguły. |
| Wynik | Co się wydarzyło, co zmieniło się mechanicznie, następny krok. | Pełne obliczenie i historia. |
| Tura przeciwnika | Kto działa, co robi, polecenie przesunięcia figurki i właściwe potwierdzenie; potem wynik. | Rozpiska automatycznego rzutu. |

Przykładowa zmiana komunikatu:

> **Garran — wybierz działanie**  
> Osobista gwarancja · k20 +5 przeciw ST 20  
> Sukces: k6 wpływu · koszt: spal 1 kartę ze wspólnej talii  
> Test [runa testu] / Pomóż Nimrze [stała runa Nimry] / Podejrzyj spód talii [runa podglądu]  
> Pomoc: odbiorca 1/2 · −/+ zmienia osobę · widoczna runa wykonuje pomoc

To przykład określonego stanu, nie uniwersalna formuła. UI musi brać premie,
legalne cele, koszt i efekt z silnika. Karta pomocy pokazuje portret i imię
oglądanego odbiorcy, jego podejście, zgromadzoną pomoc oraz wartość po dodaniu
kolejnej, koszt i właściwą stałą runę. Oglądanie karty nie wybiera odbiorcy
za gracza: pomoc wykonuje dopiero naciśnięcie jego runy.
Oznaczenia w nawiasach w przykładzie zastępują rysunki istniejących run.

**Pomoc przy większej drużynie:** przyciski −/+ na planszy cyklicznie
przełączają kartę legalnego odbiorcy: po ostatnim wracamy do pierwszego,
a przed pierwszym do ostatniego. Licznik, np. „2/5”, pokazuje pozycję
i liczbę dostępnych osób. Przełączanie nie zużywa akcji ani kart i nie
zmienia przypisań run. Wszystkie legalne runy odbiorców nadal działają
jako bezpośrednie skróty, także gdy oglądamy inną osobę. Nie dodajemy
osobnego ekranu „Pomóż” ani wspólnej runy pomocy.

Podstawowe sterowanie to fizyczne −/+ na planszy. W makiecie rozmowy
odpowiada im górny pasek symulacji, tak jak w walce: zawiera −/+,
stałe runy wszystkich legalnych odbiorców oraz runy testu i podglądu.
Szczegóły mają własne oznaczenia także przy przyciskach: Klucz (24) otwiera
„Skąd premia?”, a Gwiazda (25) — „Twoje efekty”. To podglądy bez kosztu,
dostępne również po wykorzystaniu działania. W oknie szczegółów −/+
przewija treść, Accept lub Decline zamyka okno i wraca do tej samej rozmowy.
Pozwala przełączyć oglądaną osobę albo od razu udzielić pomocy wskazaną
runą. Przyciski −/+ przy karcie są drugim sposobem wykonania tego samego
przełączenia i pozostają widoczne, gdy jest więcej niż jeden odbiorca.

Przy jednym odbiorcy zostaje jego karta, bez aktywnych przycisków
przełączania. Przy braku legalnych odbiorców sekcja wyjaśnia przyczynę
i nie oferuje wykonania pomocy. Legenda zawsze opisuje bieżący kontekst:
w decyzji rozmowy −/+ zmienia odbiorcę pomocy, podczas rzutu wynik kości,
a podczas narracji przewija tekst. Te czynności nie mogą działać naraz.

Makieta zawiera dwa przykładowe stany rozmowy z Nessą: domyślną „Osobistą
gwarancję” z dwoma legalnymi odbiorcami pomocy oraz „Zrozumienie obaw”
z pięcioma. Drugi stan ma alternatywny, autorski dobór podejść drużyny,
aby pokazać skalowanie interfejsu; przełącznik makiety nie jest propozycją
zmiany podejścia w trakcie bieżącej konfrontacji.

W walce naciśnięcie runy otwiera podgląd, a samo obejrzenie akcji nie zużywa
zasobów. Wybór innej runy zmienia podgląd. Stałe przypisania pozostają takie
same także wtedy, gdy akcja jest niedostępna; jej podgląd wyjaśnia przyczynę.

## Walka: uczestnicy, inicjatywa i stany

**Po lewej jeden pionowy tor inicjatywy wszystkich bohaterów i przeciwników;
po prawej stała karta bieżącego kroku.** Nie ma drugiego toru nad sceną ani
paska drużyny u dołu. Wiersze toru pokazują mały portret, nazwę, PW oraz
krótkie oznaczenia stanów. Portrety przeciwników zastępują cyfry jako główny
sposób ich rozpoznawania. Powtórzone profesje mają różne twarze; stały
identyfikator aktora pozostaje w danych i nie zmienia się po pokonaniu wroga.
Powiązanie z konkretną figurką zapewnia wskazanie jej pola i podświetlenie
na planszy, a wyraźny portret z nazwą potwierdza tożsamość na ekranie.

**Aktywna tura i oglądana postać to dwa różne stany.** Aktywny wiersz ma
mocne wyróżnienie i więcej informacji: PW, tymczasowe PW oraz działające
efekty. −/+ przenosi osobny kursor podglądu w górę i w dół toru; oglądana
osoba rozwija swoje dane, a znacznik aktualnej tury pozostaje przy aktorze,
który działa. Oglądanie nie zmienia kolejności, nie kończy tury i nie wydaje
zasobów. Powrót do bieżącej decyzji odsłania aktywnego uczestnika.
Długą listę przewija sama aplikacja tak, aby kursor był widoczny. Nie trzeba
sięgać do myszy ani trafiać w mały pasek przewijania.

Tor pochodzi z aktualnego stanu walki, również po przywołaniu uczestnika;
nie jest ponownie sortowaną kopią początkowych wyników inicjatywy. Pokonani
przeciwnicy są oznaczeni i wyszarzeni, a bohater z 0 PW zachowuje miejsce
w kolejności oraz właściwą turę. Runda i następny uczestnik są częścią
nagłówka tego samego toru. Wąski ekran układa tor i kartę pionowo, zachowując
jednoznaczną kolejność i obsługę planszą.

W makiecie pokazano autorski stan w trakcie starcia: sześciu bohaterów
i ośmiu przeciwników, z czego trzech pokonanych. Maksymalne PW odpowiadają
wariantowi Misji 0 dla sześciu osób; bieżące PW, stany i inicjatywa są
przykładowe. Nowy atlas portretów powstał wbudowanym `image_gen` wyłącznie
do makiety; [prompt i przypisania](assets/PROMPTS.md) są zapisane obok pliku.
Nie zmieniono zasobów scenariusza w działającej aplikacji.

PW pokazujemy liczbą i paskiem, tymczasowe PW oddzielnie. W zwiniętym
wierszu mieszczą się najważniejsze krótkie znaczniki; podgląd udostępnia
wszystkie efekty. Ograniczenia wpływające na decyzję mają pierwszeństwo,
np. brak akcji lub nieprzytomność przed mniej pilnym efektem. Sam kolor
nie wystarcza do rozpoznania stanu. Otrzymywana korzyść z aury, np.
**„Bastion +4 KP”**, jest widoczna przy odbiorcy bez szukania jej u źródła.
Wartości pobiera się z silnika; nie powtarzamy całej fizycznej karty postaci
ani katalogu odblokowanych zdolności.

Szczegóły uczestnika otwieramy przyciskiem wskazanym w legendzie po
wybraniu go przez −/+. Każdy efekt ma nazwę, skutek, źródło i dokładny
warunek zakończenia: np. „do początku tury Garrana”, „do końca tury Garrana”
albo „dopóki pozostajesz w zasięgu”. Warunek otrzymywania premii z aury
i czas istnienia samej aury są oddzielne: wyjście z zasięgu może odebrać
korzyść tej osobie, a wygaśnięcie przy drainie usuwa jej źródło. Nie używamy
ogólnego „1 tura”, które nie wskazuje czyja to tura. Pokazujemy zasady
łączenia premii, bez ponownego liczenia tej samej korzyści jako osobnego
stanu. Wygaśnięcie lub zmiana jest odnotowana w dzienniku.

Dla obecnego Bastionu szczegół brzmi np. „W zasięgu Garrana · aura do mana
drainu”: premia do KP zależy od Siły źródła, a efekt chroni też przed
przymusowym przesunięciem. Wyjście poza 10 ft odbiera korzyść odbiorcy;
powrót przywraca ją, jeśli źródło nadal działa. Dwa Bastiony nie sumują
premii — działa najsilniejszy — natomiast różne rodzaje premii mogą się
łączyć zgodnie z silnikiem. Podstawa:
[Bastion i jego synchronizacja](../../src/dnd_board_game/combat/shared_mana_features.py),
[wybór najsilniejszej aury](../../src/dnd_board_game/combat/auras.py)
i [obliczanie KP](../../src/dnd_board_game/combat/targets.py).

**Na planszy wskazujemy figurkę i zasięg, a na ekranie znaczenie efektu.**
Podgląd uczestnika może wyróżnić jego pole; podgląd aury pokazuje zasięg
jednego wybranego źródła, z nazwą i legendą na ekranie. Wskazanie celu,
ruch i oczekiwane wejście gracza mają pierwszeństwo. Nie kodujemy wszystkich
stanów osobnymi kolorami LED — nakładające się efekty byłyby nieczytelne,
a kolory many mają własne znaczenie.

Opcjonalne drukowane karty stanów lub żetony przy karcie postaci mogą
powtarzać ikonę i krótki opis. Aplikacja pozostaje źródłem bieżącego czasu
trwania, wartości i zasięgu. Nie wymagamy dodatkowej elektroniki ani mapy
na ekranie. Podświetlenie pola i aury mają już wsparcie w obecnym adapterze
([podgląd aur](../../src/dnd_board_game/ui/aura_preview.py)); nowy UI powinien
udostępnić je z planszy i zachować priorytety. Makieta nie steruje diodami.
Przykładowe Błogosławieństwo Dagny daje +k4 do ataków i obron w 10 ft,
do Mana Drain lub utraty koncentracji, zgodnie z aktualnym wariantem
wspólnej many, bez starszego limitu trzech rund.

## Walka: akcja, cel i zatwierdzenie

Karta po prawej zmienia zawartość w kolejnych krokach. Nie zasłania toru
inicjatywy osobnym oknem. Dzięki temu gracz może równocześnie sprawdzić
swoją akcję, konkretny cel i kolejność działania.

1. **Wybierz akcję.** Naciśnięcie runy z fizycznej karty otwiera podgląd:
   nazwa, efekt, koszt i wymagany rodzaj celu. Nie wydaje jeszcze akcji,
   kart ani ładunku. Inna runa zmienia podgląd; niedostępna wyjaśnia powód.
2. **Wskaż cel na planszy.** Wybrane pole identyfikuje konkretną figurkę,
   także gdy kilka stoi obok siebie. Aplikacja wyróżnia jej pole i pokazuje
   portret z nazwą, PW oraz stanami w tej samej karcie po prawej. Duży blok
   akcji znika; pozostaje mały podpis, np. „Rozkaz: Stać! · Wybór celu”.
   Koszt jest przypomniany drobnym tekstem przy zatwierdzeniu.
3. **Sprawdź warunki.** Podgląd łączy akcję z tym celem: dystans i zasięg,
   linię widzenia, osłonę, końcową KP celu, przewagę lub utrudnienie wraz
   z powodami, wzór rzutu i koszt. Dla ataku strzeleckiego częściowa osłona
   pokazuje np. „Osłona +2 KP” albo „Osłona +5 KP”; pełna osłona blokuje
   atak, nie jest kolejną premią do KP. Utrudnienie za daleki zasięg i inne
   warunki muszą być rozliczone przez silnik, bez samodzielnych reguł w UI.
4. **Accept wykonuje deklarację.** Dopiero jawne zatwierdzenie aktualnej,
   legalnej akcji na konkretnym celu rozpoczyna rozstrzygnięcie. Decline
   wraca o jeden krok; kolejny Decline prowadzi do wyboru akcji. Zmiana
   celu lub cofnięcie podglądu niczego nie wydaje.

Nielegalny cel pozostaje czytelnie opisany, z konkretną przyczyną, ale
Accept nie wykonuje ataku. Po zmianie położenia, stanów, zasobów lub tury
trzeba ponownie obliczyć podgląd. Jeżeli cel lub warunki zmieniły się między
podglądem a zatwierdzeniem, stara deklaracja nie może zostać wykonana:
najpierw aktualny podgląd, potem nowe potwierdzenie. Interfejs nie może
przenieść ataku na sąsiednią figurkę po utracie pierwotnego celu.

Stan neutralny, oglądanie uczestnika i podgląd akcji są bezkosztowe.
Rzuty, obrażenia, reakcje i płatność nadal mają własne kroki zgodne
z obecnymi zasadami. Zmienia się prezentacja, nie moment wydawania zasobów
ani mechanika automatycznych tur przeciwników.

Obecny silnik już rozdziela wskazanie celu od potwierdzenia i ponownie
sprawdza legalność przy wykonaniu:
[`select_attack_target` i `confirm_attack_target`](../../src/dnd_board_game/application/player_combat_action_flow.py).
Zasięg, osłony i warunki strzału pochodzą z
[pozycjonowania ataku](../../src/dnd_board_game/combat/attack_positioning.py)
oraz [filtrowania legalnych celów](../../src/dnd_board_game/combat/attack_flow.py).
[Projekcja UI](../../src/dnd_board_game/ui/exploration_app.py) ma już dane
podglądu i wyróżnienie aktora oraz celu przez LED. Nowy układ powinien
wykorzystać te wartości, a wymaganie ponownego potwierdzenia zmienionego
podglądu trzeba osobno zweryfikować na poziomie przepływu wejść.

Przykład strzału w makiecie wykorzystuje Garrana z kuszą o zasięgu 80/320 ft.
To oddzielny przykładowy stan wyposażenia: bez założonej tarczy, więc
uderzenie tarczą pozostaje niedostępne. Nie jest to zmiana karty bohatera
ani startowego wyposażenia Misji 0.

## Cała obsługa z planszy

Docelowo od uruchomienia aplikacji użytkownik nie potrzebuje myszy:
start, wybór misji i drużyny, wznowienie, przygotowanie planszy i kart,
narracja, rozmowa, walka, szczegóły, dziennik i menu mają pełną ścieżkę
przez runy oraz −, +, Accept i Decline. Przycisk nie może wykonywać dwóch
czynności naraz. Legenda pokazuje bieżący kontekst, np. „−/+ uczestnik”,
„−/+ wynik kości” albo „−/+ przewiń tekst”. Przyciski i skróty w przeglądarce
służą symulacji tych samych wejść.

Runa wybiera nazwaną opcję lub akcję. −/+ przesuwa kursor, przewija albo
zmienia wpisywaną wartość zgodnie z aktualnym krokiem. Accept zatwierdza
wskazaną operację; Decline cofa o jeden poziom. Podglądy efektów, wybór
źródła aury i długie teksty wymagają tej samej kompletnej nawigacji co
podstawowe akcje. Menu sesji musi być osiągalne również w trakcie gry;
powrót zachowuje rozpatrywaną decyzję.

To rozszerzenie istniejących możliwości, nie sterowanie budowane od zera.
Obecny launcher korzysta już z run 6–25 i 29, ale trzeba uzupełnić pełną
obsługę funkcyjnych 26–28. Wznowienie przez link, ponowne połączenie oraz
część szczegółów, przewijania i przejść między krokami wymagają osobnego
sprawdzenia i spięcia z planszą. Należy również uzgodnić limit pięciu osób
w launcherze z obsługą sześciu przy tworzeniu gry. Podstawa:
[obsługiwane sloty launchera](../../src/dnd_board_game/ui/launcher_board.py),
[wiązania run, limit i ponowne łączenie](../../src/dnd_board_game/ui/static/launcher_board.js),
[link wznowienia](../../src/dnd_board_game/ui/templates/main_menu.html),
[szczegóły i awans postaci](../../src/dnd_board_game/ui/templates/character_detail.html)
oraz [wybór drużyny](../../src/dnd_board_game/ui/templates/new_game.html).

Menu startowe makiety pokazuje rozpoczęcie przykładowej wyprawy, wczytanie
przykładowej walki i instrukcję obsługi planszy. „Wczytaj” wybiera stan
prezentacyjny, nie rzeczywisty plik zapisu. Nie jest to pełna implementacja
launchera, wyboru drużyny ani odzyskiwania sesji.

Ścieżka musi obejmować także przerwanie i odzyskanie sesji: wybór zapisu,
potwierdzenie zgodności fizycznych stosów, błędny odczyt karty, utratę
połączenia, ponowne podłączenie i powrót do oczekiwanego kroku. Gdy plansza
jest rozłączona, aplikacja powinna automatycznie czekać na jej powrót i po
odzyskaniu wejścia pozwalać kontynuować przyciskami; niedziałający sprzęt
nie może wymagać naciśnięcia przycisku na tym samym sprzęcie, aby rozpocząć
ponowne łączenie. Makieta pokazuje kierunek nawigacji, nie dowodzi jeszcze
pełnej obsługi tych przypadków ani uruchomienia programu na urządzeniu.

## Mana i pasywy: mniej tekstu, zachowane znaczenie

Aktualne źródła: [sześć kart i atuty](../TRUMP_MANA.md),
[indywidualne pasywy](../DISTINCT_MANA_PASSIVES.md),
[konfrontacje](../PARTY_CONFRONTATIONS.md), [postawa](../PARTY_ETHOS.md).
Starsze opisy 21 punktów oraz wspólnych pasywów nie są podstawą projektu.

- **Walka:** `Karty 3/6 · Premia testu +3 · Ładunek zdolności 6/6`,
  gdy trzy karty są atutami. Dobór nadal trwa do sześciu fizycznych kart.
- **Konfrontacja:** `Karty 3/6 · Premia testu +3`; ładunek zdolności jest
  zbędny na głównym ekranie tej mechaniki. Pomoc i inne premie są pokazane
  oddzielnie lub w rozpisce pełnego modyfikatora testu.
- **Dobór:** zachować 1:1 symbole many z obecnego UI, również w osobistej
  puli i zgłaszaniu kart. Rozpoznawalny symbol zastępuje widoczną nazwę koloru
  i literę, zgodnie z językiem symboli używanym w grach takich jak Magic:
  The Gathering. Nazwa koloru pozostaje w etykiecie dostępności, np.
  `aria-label`. Obok symbolu pokaż zmianę, np. `+3 → +4 do testów`, i nowy
  pasyw. W walce także zmianę ładunku i konkretną odblokowaną akcję.
- **Pasywy:** nazwa przy postaci, pełen warunek w szczegółach, wyraźny
  komunikat gdy efekt faktycznie działa. „Odblokowane kolorem” i „premia
  doliczona do tej próby” to różne informacje.
- **Koszt:** „Spal 1 ze wspólnej talii” nie może wyglądać jak wydanie
  osobistej karty. Osobista pula pozostaje po użyciu zdolności.
- **Napięcie:** opór i liczba kart wspólnej talii pozostają widoczne.
  Dokładną następną reakcję ujawniamy wyłącznie przez dostępny `forecast`
  ze Zwiadu Erynda.
- **Postawa:** siedem pól w spokojnym elemencie ramy; zmianę podkreślamy
  przy decyzji. Wpływ na skład kart opisujemy jako obowiązujący od następnej
  walki/konfrontacji, a pełną instrukcję podajemy przy przygotowaniu talii.

Nie usuwamy fizycznej obsługi kart przez samo ukrycie komunikatów.
Zgłoszenie koloru, korekta, odzysk i potwierdzenie zachowanych stosów
przy wznowieniu nadal są potrzebne. Podgląd spodniej karty nie pyta o kolor.
Drain ma odrębne znaczenie w walce i konfrontacji; pustej talii nie wolno
automatycznie przedstawiać jako porażki niezależnie od stanu rozstrzygnięcia.

## Kierunek wizualny i inspiracje

Zachować obecne ilustracje i świat gry. Zastosować spokojne tło, większe
odstępy, mniej obramowań i wyraźną skalę tekstu. Duży nagłówek odpowiada
na „co teraz?”, krótki podtytuł na „dlaczego?”, a detal jest dostępny dalej.
Kolory many zostają zarezerwowane dla many; dotychczasowe symbole zapewniają
czytelność bez rozpoznawania samego koloru. Nazwy są etykietami dostępności,
bez powtarzania ich na ekranie. Drobny tekst nie może być
jedynym nośnikiem kosztu lub powodu niedostępności.

FFG opisuje aplikację **Posiadłości Szaleństwa 2 ed.** jako prowadzącą
narrację i stopniowe przygotowanie odkrywanych przestrzeni
([oficjalna prezentacja](https://www.fantasyflightgames.com/en/news/2016/7/28/a-haunting-atmosphere/)).
Przenosimy stąd prowadzenie przez aktualną sytuację i dawkowanie instrukcji.

W **Podróżach przez Śródziemie** aplikacja prowadzi przeciwników i przyjmuje
wyniki ataków oraz ich modyfikatory
([oficjalna prezentacja walki](https://www.fantasyflightgames.com/en/news/2019/4/5/against-the-darkness/)).
Przenosimy czytelny podział: czynność przy stole → rozstrzygnięcie aplikacji
→ następne polecenie. To nasza interpretacja przydatnych wzorców;
nie kopiujemy ich zasad, grafik ani cyfrowej mapy.

## Wdrożenie małymi krokami

1. **Konfrontacja Nessy jako pierwszy wycinek:** aktywna osoba, zwarta
   drużyna, jeden obszar decyzji, cel i opór, pełna narracja na żądanie.
   Trzy sekcje Test / Pomoc / Podgląd; jedna karta odbiorcy pomocy,
   przełączana −/+ z licznikiem, wykonanie pomocy jego stałą runą.
   Obsłużyć brak odbiorców, jednego oraz wielu; zachować skróty pozostałych
   legalnych run i wyraźną legendę −/+ zależną od bieżącego kroku.
   Tu najłatwiej porównać obecny i nowy układ bez ruszania silnika.
2. **Dobór i obsługa kart:** podgląd zmian, jedno miejsce prezentacji many,
   dotychczasowe symbole zamiast nazw i liter, wyraźne komunikaty odzysku
   i spalania. Zachować wszystkie legalne korekty.
3. **Walka:** komunikat „Wybierz akcję”, po naciśnięciu runy podgląd wyłącznie
   wskazanej akcji. Gracze korzystają z fizycznych kart postaci. Usunąć katalog
   akcji i powielone panele; zachować stałe przypisania run, także niedostępnych.
   Jeden pionowy tor z portretami wszystkich uczestników po lewej; aktywna
   tura i kursor oglądania przez −/+ są oddzielne. Karta akcji po prawej
   prowadzi przez wskazanie figurki, podgląd celu i warunków do Accept;
   Decline cofa krok. Zweryfikować osłonę, zasięg, widoczność i zmianę
   warunków przed zatwierdzeniem. Szczegóły podają źródła, zasady łączenia
   i dokładne warunki końca efektów. Podgląd pola i jednej aury przez LED
   musi zachować pierwszeństwo bieżącego celu oraz wejścia.
4. **Pełna nawigacja planszą:** od launchera i wznowienia po menu sesji,
   szczegóły, dziennik, setup i wyniki. Uzupełnić kontekstowe −/+, Accept
   i Decline, dostęp do wszystkich opcji oraz powrót bez utraty stanu.
   Sprawdzić ścieżki odzyskania po błędnym wejściu, rozłączeniu i wznowieniu
   zapisu; uzgodnić wybór 3–6 graczy w launcherze i tworzeniu nowej gry.

Przewidywane miejsca zmian przy późniejszym wdrożeniu:
`ui/static/confrontation.js`, `training_arena.css`, `exploration.js/css`,
`physical_mana.js/css`, `shared_mana.js`, `mission_zero.js/css`, sterowanie
launchera oraz szablony startu i `ui/templates/exploration.html`. Uzupełnienia projekcji stanu ewentualnie
w `ui/confrontation.py` i `ui/session_view.py`. Bez przepisywania reguł ani przenoszenia ich do JavaScriptu.
Routing wejść planszy należy uzupełniać tam, gdzie audyt wykazał brakującą
ścieżkę, zachowując stałe przypisania run i kontekst przycisków funkcyjnych.
Opisy postaci nadal pochodzą z `content/characters/karty_postaci.json`.
Stan walki i korzyści z aur musi rzutować silnik; reguły pozostają niezależne
od UI i urządzeń. Ewentualny podgląd LED należy do `hardware/`, które
otrzymuje gotowy wynik reguł i nie oblicza własnych premii ani zasięgów.

## Jak ocenić poprawę

- Na 1131×720 widać aktywną osobę, instrukcję i dane do aktualnej decyzji
  bez szukania w kartach pozostałych pięciu osób.
- Nowy gracz potrafi wskazać: kto działa, co ma zrobić, ile to kosztuje
  i gdzie wykonać czynność. Sprawdzić to przy stole, nie wyłącznie w kodzie.
- Trzy atuty nie sugerują pełnej puli fizycznej; udany test nie sugeruje,
  że premia testu zwiększa wpływ/obrażenia.
- Każdy legalny odbiorca pomocy jest dostępny w karuzeli i ma na swojej
  karcie właściwą stałą runę. −/+ tylko przełącza podgląd osoby, runa
  wykonuje pomoc, a licznik pokazuje liczbę możliwości. Sprawdzić brak
  odbiorców, jednego, dwóch i pięciu, zawijanie końców oraz bezpośredni
  wybór runą osoby spoza aktualnego podglądu. Przy zmianie etapu −/+
  musi wykonywać wyłącznie czynność podaną w aktualnej legendzie.
- Symbole many odpowiadają obecnemu UI i mają tekstowe etykiety dostępności.
- W walce z ekranu „Wybierz akcję” każda runa otwiera właściwy podgląd;
  oglądanie i zmiana podglądu nie wydają zasobów. Niedostępna akcja pokazuje
  powód blokady. Sprawdzić wybór przy użyciu fizycznych kart postaci.
- Wybór akcji i podgląd celu pozostawiają widoczny lewy tor. Portret i nazwa
  odpowiadają wskazanej figurce. −/+ zmienia oglądaną osobę, pozostawiając
  aktywną turę, zasoby i kolejność bez zmian. Sprawdzić pokonanego wroga,
  bohatera z 0 PW, tymczasowe PW, wiele stanów i wejście/wyjście z aury.
  Źródło i moment końca efektu muszą być jednoznaczne; LED podglądu nie
  może zasłaniać bieżącego celu.
- Dla sąsiadujących figurek potwierdzić tożsamość celu przed Accept.
  Sprawdzić zasięg, widoczność, osłonę +2/+5, pełną osłonę, końcową
  przewagę/utrudnienie, wzór rzutu i koszt. Niedostępny lub nieaktualny
  cel nie może zostać zaatakowany; cofnięcie nie wydaje zasobów.
- Przejść pełną sesję bez myszy: start, wybór misji i 3–6 graczy, zapis
  i wznowienie, szczegóły, menu, długie teksty oraz powrót po błędnym
  odczycie i rozłączeniu planszy. To warunek wdrożenia, nie osiągnięcie
  potwierdzone samą makietą.
- Zmniejsza się liczba poszukiwań informacji i pomyłek; liczba niezbędnych
  zgłoszeń fizycznych kart pozostaje zgodna z zasadami.
- Przy 3 i 6 osobach sprawdzić: dobór, pomoc, rzut, odzysk, spalanie,
  reakcję, kompromis, przerwanie/wznowienie, drain i turę przeciwnika.
- Sprawdzić obsługę run, dotyku, klawiatury, fokus, czytelność z odległości,
  mały ekran i powiększenie. Zmiany stanu nie powinny gubić fokusu.

Audyt i makieta nie dowodzą jeszcze szybszej gry ani lepszego balansu.
Potrzebne jest krótkie porównanie przy stole na tej samej scenie.

## Weryfikacja makiety

Chrome: 18 stanów na 1300×720, 1131×720 i 390×800, czyli 54 kombinacje.
Obejmują start, narrację, rozmowę z różną liczbą odbiorców pomocy, dobór,
rzut oraz etapy walki: wybór akcji, oglądanie uczestnika i efektów, wskazanie
celu, podgląd, osłonę, daleki zasięg, blokadę oraz zatwierdzenie.
Bez poziomego przepełnienia i bez brakujących ilustracji. Na obu rozmiarach
laptopa karta walki mieści cały podgląd i przyciski zatwierdzenia/cofnięcia;
dłuższy lewy tor przewija się lokalnie przy zmianie kursora przez −/+.
W rozmowie i doborze dodatkowy pasek symulacji może wymagać krótkiego
przewinięcia do dolnej części drużyny. Telefon korzysta z pionowego układu.

Sprawdzono 83 warunki interakcji, w tym:

- rozmowę, wynik testu, spalanie, symbole many, legalność pomocy, stałe runy
  odbiorców oraz karuzelę dla 0, 1, 2 i 5 odbiorców;
- nawigację symulowanymi przyciskami planszy od startu do przykładowej walki,
  menu, dziennik, dialog pomocy, dobór i zgłoszenie rzutu;
- jeden pionowy tor 14 uczestników z ośmioma portretami przeciwników,
  odrębność aktywnej tury i kursora oglądania, przewijanie oraz kolejne
  strony efektów ze źródłem i warunkiem końca;
- podgląd akcji bez wydawania zasobów, wskazanie i zmianę celu,
  zachowanie celu podczas oglądania uczestników, cofanie o jeden etap,
  ponowne sprawdzenie legalności przed Accept oraz brak podwójnego wykonania;
- blokadę ataku poza zasięgiem i za pełną osłoną, premie osłony +2/+5,
  właściwe KP i wzory rzutu, przewagę/utrudnienie oraz ich znoszenie,
  test przeciwstawny uderzenia tarczą i niedostępność tarczy przy kuszy.

Osobno porównano ścieżki SVG symboli many z bieżącym UI: zgodne 1:1.
Po uproszczeniu nagłówka celu sprawdzono dodatkowo pięć akcji na czterech
rozmiarach okna (20 układów) oraz podgląd uczestnika, cofanie i zatwierdzenie.
„Rozkaz: Stać!” mieści cel i przyciski także na 850×650; dłuższy podgląd
ataku kuszą przy tej szerokości może wymagać pionowego przewinięcia.
Runy szczegółów rozmowy sprawdzono w 26 warunkach interakcji i 6 układach:
otwieranie z planszy, powrót bez zmiany zasobów i odbiorcy pomocy, dostęp
po wykorzystaniu działania, aktualne efekty, przewijanie −/+ i zachowanie
obowiązkowego zgłoszenia spalonej karty. Wyniki są w `talk_detail_rune_review`.
Wyniki: [verification.json](verification.json). Sprawdzenie `git diff --check`
przeszło. To weryfikacja niezależnej makiety w przeglądarce z symulowanymi
wejściami. Nie testowano fizycznych przycisków ani diod. Pytest nie uruchamiano:
nie zmieniono silnika, aplikacji wykonawczej ani adaptera sprzętu. Pełna
obsługa rzeczywistej sesji planszą, zapis/wznowienie i odzyskiwanie po
rozłączeniu pozostają zadaniami wdrożeniowymi opisanymi wyżej i w TODO.

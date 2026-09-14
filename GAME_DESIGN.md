# Game Design

Projekt jest aplikacją do wspomagania taktycznych starć w Dungeons & Dragons 5e z użyciem fizycznej planszy i systemu LED.

Docelowo aplikacja ma wspierać dużą część zasad walki i spotkań z D&D 5e.

Pierwsza wersja jest celowo ograniczona i skupia się na technicznie poprawnej pętli taktycznego starcia połączonej z fizyczną planszą, fizycznymi kośćmi oraz wizualizacją LED.

Aplikacja nie jest pełnym wirtualnym stołem RPG. W pierwszej wersji ma działać jako asystent walki taktycznej.

---

## Warunki rozmów — 2026-09-14

W Arenie działają cztery opcjonalne warunki: częściowe porozumienie przy
pierwszym wejściu w 15–17, drażliwy kolor zmieniający cenę sukcesu, dodatkowa
informacja za dwie niebieskie przy sukcesie i jednorazowa karta za 1 w zamian
za zobowiązanie. Zobowiązanie pozostaje również przy porażce. Jedna zasada
na rozmowę, jawna stawka, decyzje przez runy, podstawowa procedura do 21
bez zmian. Każdy bohater ma dostęp do lekcji, a finał otwiera różne możliwości
u Nessy. Wynik „Porozumienie” jest odrębny od sukcesu i porażki. Opis i pliki:
[wdrożenie eksploracji](docs/EXPLORATION_MANA_IMPLEMENTATION.md).

## Aktualny wariant areny: wspólna mana 0.3

Ustalenia rynku i czasu efektów opisuje `PROJECT_CONTEXT.md`, a wspólny katalog akcji dla aplikacji i druku znajduje się w `src/dnd_board_game/rules/shared_mana_catalog.py`. Każdy bohater ma 4 podstawowe zdolności, 3 z podbiciami i 2 ulty; Nimra odpowiednio 5/4/3. Zwykły ruch i atak są darmowe poza dopłatami skaz. Koszt odkłada się przed rozstrzyganiem efektu, dzięki czemu zdolności odzysku mogą odzyskać własny koszt. Historyczne opisy prywatnych rezerw i fal poniżej nie dotyczą tego wariantu.

## Opcjonalna Mapa 0 — arena rekrutacyjna (2026-09-06)

Nessa prowadzi klasyczny samouczek krok po kroku dla każdej z siedmiu postaci.
Sekwencja: osobne okno narracji i mechaniki → ustawienie planszy krok po kroku
→ krótkie polecenie wykonania → wymagana zdolność
→ rozstrzygnięcie → objaśnienie i następna sytuacja. Każdy rodzaj podbicia ma
oddzielne ćwiczenie, razem 99 kroków. W ćwiczeniach zapewniamy potrzebną manę,
świeże PW, budżet tury i przygotowane warunki (rana, flanka, Szał, atak do reakcji).
Wyniki rzutów gracza są prawdziwe; nieudane pchnięcie lub ukrycie prowadzi do
ponowienia. Ataki do ćwiczenia reakcji są jawnie przygotowane, bez losowego
oczekiwania na okazję. Figurka Nessy i rozmowa na arenie nie są potrzebne.
Teren pozostaje wspólny. Po pierwszym pełnym przygotowaniu nie powtarzamy
ustawiania terenu przy kolejnych lekcjach, ponowieniach ani zmianie postaci.
Podczas setupu na pierwszym planie jest tylko bieżący element i jego potwierdzenie;
mapa pozostaje zwinięta. W trakcie działania opis lekcji jest rozwijaną pomocą.
Narracja ma tekst i stabilne identyfikatory pod przyszły głos.

Finał: zwykły pojedynek 1 na 1 z pełnymi PW i normalnym rynkiem many (5/20/0).
Kukła ma 30 PW, KP 13, ruch 30 ft, atak wręcz +3 i 1k6 obrażeń. Samouczek kończy
zwycięstwo, a utrata wszystkich PW bohatera kończy próbę bez zaliczenia pojedynku.
Po wyniku ✓ wraca do wyboru postaci. Ukończone ćwiczenia można kontynuować;
ukończoną postać można przejść ponownie. Kampania nie jest modyfikowana.
Opis: `docs/RECRUITMENT_ARENA.md`.

## Fizyczna mana dla siedmiu bohaterów — 2026-09-05

Od 2026-09-07 fioletową manę zastępuje czarna. Symbole: biała — słońce,
niebieska — kropla, czarna — czaszka, czerwona — płomień, zielona — drzewo;
cyfra 1 w kółku oznacza dowolny kolor. Do testów używamy podstawowych lądów
MTG: Plains, Island, Swamp, Mountain i Forest. Każdy ląd jest jedną kartą
many; wydany trafia na stos odrzuconych. Koszty, dobór i fale pozostają
według zasad fizycznej many. Wydarzenie 5 nazywa się „Czarne zakłócenie”.
Mapowanie lądów i kolorów: [Wizards of the Coast](https://magic.wizards.com/en/news/feature/anatomy-magic-card-2006-10-21).

Nowe rozgrywki gotowymi bohaterami używają profilu `physical_mana_v02`.
Jest to jawne, zlecone przez użytkownika odstępstwo od ekonomii zasobów 5e.
Pełny opis: `docs/PHYSICAL_MANA_DESIGN_V0_2.md`; katalog wykonawczy kosztów:
`src/dnd_board_game/rules/physical_mana.py`. Poniższe historyczne opisy pul
punktów i komórek nie obowiązują w tym profilu. Generyczne postacie oraz
zapisane wcześniej walki zachowują dotychczasowe reguły.

Karty, rynek, rezerwy, dopłaty skaz i limity pasywów karcianych są prowadzone
fizycznie przez graczy. Aplikacja nie przechowuje ręki ani historii płatności
oraz nie sprawdza legalności many. Waliduje tury, akcje, reakcje, wyposażenie,
pozycje i skutki. Zwykły Atak to jedno uderzenie za jedną dowolną manę. Tylko Lorian
może zadeklarować w ramach tej akcji dodatnią liczbę osobnych zwykłych
ataków za po jednej dowolnej manie. Techniki zachowują własne liczby ataków. Czary działają na poziomie bazowym.
Ruch kosztuje bazowo jedną dowolną manę raz na turę. Skaza Garrana
„Nieustępliwość” (2026-09-06): pierwszy zwykły Ruch rozpoczęty obok
niepokonanego przeciwnika kosztuje 2 dowolne many. Dalsze odcinki nie
zmieniają tej ceny; ruch ze zdolności i wymuszone przemieszczenia nie
uruchamiają skazy. Aplikacja pamięta deklarację ruchu i pokazuje koszt,
bez sprawdzania zapłaty. Ta reguła zastępuje Wyrzuty sumienia w profilu many.

Zmiana Garrana (2026-09-07): Uderzenie tarczą zużywa akcję dodatkową i zadaje
1k6 + modyfikator Siły obrażeń obuchowych po wygranym teście Siły. Odepchnięcie
o jedno wolne pole pozostaje; remis wygrywa obrońca. Za przeciwnika rzuca
aplikacja. Zwykły atak i tarczę można wykonać w jednej turze, w dowolnej
kolejności, o ile cel pozostaje w zasięgu. Koszt many tarczy: C + N; atak
opłacany osobno. Uderzenie tarczą nie zużywa ruchu, ale konkuruje o akcję
dodatkową z Pozycją obronną, Zrywem akcji i Osłoną tarczą.

Koniec tury: zachowaj do 2 starych kart (Lorian 3), dobierz do 3, uzupełnij
rynek. Pojemność 5 (Lorian 6); bez dodatkowego doboru na początku tury/rundy.
Fale zgłaszają gracze. Rozliczenie na granicy rund podnosi Zagrożenie do 3
i uruchamia jawne wydarzenie. Materiał do wydruku: `/rules/physical-mana`.
Koszty wymagają jeszcze testów balansu przy stole.

Doprecyzowanie po teście 2026-09-06: Szał Brakki trwa KON mod + SIŁ mod
rund (minimum 1), licząc rundę uruchomienia. Koszt jednorazowy; utrata
przytomności kończy efekt. Bitewny amok rozliczamy w każdej turze w Szale.
Ukrycie Miry pozostaje relacją względem poszczególnych wrogów: turkusowe LED
oznaczają nieświadomych, pomarańczowe świadomych. W jej turze podgląd akcji
zastępuje te kolory, a powrót do wyboru przywraca je, jeśli ukrycie nadal trwa.
Opis zmian i walidacja: `docs/COMBAT_PLAYTEST_POLISH_2026-09-06.md`.

## Głodne Cienie: układ walki v6 — 2026-09-05

Mapa 1 ma wspólną szeroką strefę startową bliżej wraku, trzy podejścia,
lokalne koleiny i krótką skałę z połączeniem suchego obejścia na obu końcach.
Osłony działają między źródłem ataku a celem, a nie jako premia za stanie na
polu. Front stada skupia ataki, skrzydła szukają pobliskich odsłoniętych celów.
Setup wyjaśnia teren przed wyborem szyku, potem prowadzi przez przeciwników
i końcową instrukcję. Skład i instrukcja uwzględniają wariant 1–5 graczy.
Pełny kontrakt i materiały do druku: `docs/HUNGRY_SHADOWS_REDESIGN_V6.md`.

## Filozofia Projektu

Aplikacja powinna stosować zasady Dungeons & Dragons 5e wszędzie tam, gdzie jest to możliwe.

Zasad D&D 5e nie należy zastępować własnymi mechanikami bez wyraźnego powodu.

Jeżeli fizyczna plansza, LED-y albo ograniczenia pierwszej wersji wymagają uproszczenia, odstępstwo musi być opisane w tym pliku.

Jeżeli dana mechanika D&D 5e nie jest jeszcze zaimplementowana:

* należy dodać TODO,
* należy jasno oznaczyć ograniczenie,
* nie należy wymyślać własnego systemu zastępczego bez opisania powodu.

Lepsze jest niepełne, ale poprawne zachowanie zgodne z D&D 5e niż kompletna, ale własna mechanika niezgodna z systemem.

Zwykły ekwipunek pozostaje pełnoprawnym elementem fikcji i zasad. Przedmioty takie
jak atrament, pióro, papier, lina, źródło światła albo focus nie są tworzone
doraźnie przez narrację LLM: muszą istnieć w ekwipunku, scenie, łupie lub ofercie
kupca pod stabilnym ID. Mechanika korzysta z ich typowanych właściwości, nie z
porównywania polskiej nazwy.

Każda implementacja reguły powinna dać się powiązać z konkretnym pojęciem z D&D 5e.

---

## Główna Pętla Gry

1. Wczytaj albo utwórz spotkanie.
2. Rozmieść aktorów na planszy.
3. Rzuć fizycznymi kośćmi albo przypisz inicjatywę.
4. Wpisz wyniki rzutów do aplikacji.
5. Rozgrywaj rundy walki.
6. Rozwiązuj ruch i akcje.
7. Aktualizuj stan planszy.
8. Generuj informacje zwrotne dla LED.
9. Zakończ spotkanie.
10. Zapisz podsumowanie spotkania.

---

## Plansza jako główny interfejs

Fizyczna plansza jest głównym medium wejścia i wyjścia podczas eksploracji oraz walki.

W walce aplikacja powinna komunikować dostępne intencje przez LED:

* niebieskie pola oznaczają legalne pola ruchu aktywnego bohatera,
* czerwone albo czerwono-różowe pola z przeciwnikiem oznaczają legalny cel ataku,
* inne kolory mogą oznaczać jawne interakcje lub setup, jeśli dana scena je posiada.

Gracz powinien wskazywać intencję przez kliknięcie podświetlonego pola na planszy:

* kliknięcie niebieskiego pola wykonuje ruch,
* kliknięcie pola z legalnym przeciwnikiem pokazuje wszystkie legalne działania
  wobec niego, a pojedyncza jednoznaczna intencja może przejść bezpośrednio do podglądu,
* kliknięcie pola interakcji wykonuje albo otwiera odpowiednią interakcję sceny,
* gdy pole ma jedną legalną intencję, aplikacja przechodzi bezpośrednio do jej podglądu lub wykonania,
* gdy pole ma kilka legalnych intencji, monitor pokazuje kontekstowe menu wybierane strzałkami i Enterem,
* kliknięcie aktualnego pola bohatera otwiera skrócone menu własne: ataki i
  zdolności postaci, `Zmiana broni`, `Użyj przedmiotu` oraz zakończenie tury.

Kontekstowe menu nadal jest składane z niezależnych źródeł, lecz interfejs
board-game wystawia tylko aktualnie wspierany, krótki katalog. Zwykłe
`Sprint`, `Odwrót`, `Unik`, Shove, Padnij/Wstań, Szukaj, podnoszenie/upuszczanie
broni, atak drugą bronią i ręczne przeszukiwanie pokonanych są ukrytym legacy —
ich resolvery pozostają w silniku do ewentualnego ponownego użycia. `Sprint` i
`Odwrót` są dostępne Eryndowi przez `Zwiadowczą mobilność`, `Unik instynktowny`
pozostaje reakcją Miry, a rozpoczęcie Chwytu jest zdolnością Brakki. Ucieczka z
istniejącego chwytu lub sieci pozostaje akcją kontekstową.

`Zmiana broni` otwiera jedną listę wszystkich dostępnych broni w ekwipunku.
Pierwsza faktyczna zmiana w turze jest darmowa i atomowo odkłada poprzednią broń;
ponowne wskazanie aktualnej broni niczego nie zużywa. `Użyj przedmiotu` otwiera
wyłącznie przedmioty z zakodowaną po ich stronie akcją bojową i legalnymi celami.

Opcja interakcji wskazana poza aktualnym zasięgiem obsługi jest intencją złożoną, a nie
zdalnym użyciem obiektu. Silnik wybiera najtańsze osiągalne pole spełniające warunki
interakcji, pokazuje ścieżkę i koszt ruchu, wykonuje ruch, a dopiero potem otwiera
interakcję. Obiekt może wymagać stania obok (np. dźwignia) albo na jego polu
(np. podnoszony przedmiot). Atak okazyjny jest rozstrzygany przed interakcją; jeśli
bohater nie dotrze na zaplanowane pole, dalsza część intencji zostaje anulowana.

Panele web UI mogą pokazywać stan, koszty ruchu, cele i awaryjne kontrolki, ale nie powinny być podstawowym sposobem wyboru ruchu albo celu ataku w grywalnym przepływie.

Gdy monitor jawnie oczekuje działania konkretnego aktora albo opisuje aktywnego NPC
lub obiekt, jego pole otrzymuje pasywny focus LED. Focus nie uruchamia skanowania i
nie wymaga kliknięcia planszy: zapisanie rzutu, zakończenie kroku albo zmiana
aktywnego uczestnika gasi poprzednie wskazanie lub przenosi je na kolejny cel.

Pasywny focus i zwykłe podświetlenie używają standardowej jasności planszy. Po
jawnym uruchomieniu skanu te same legalne pola przechodzą na osobną, wyższą
`scan_brightness`, żeby fizycznie odróżnić „informację” od „plansza czeka teraz na
kliknięcie”. Po wyborze pola, anulowaniu albo timeoutcie jasność wraca do standardu.

Każdy bohater otrzymuje na czas gry stały kolor tożsamości wynikający z kolejności
wyboru drużyny: pierwszy czerwony, drugi niebieski, trzeci zielony, czwarty
fioletowy, piąty pomarańczowy. Kolor nie jest cechą zapisaną w karcie postaci;
należy do miejsca w bieżącej drużynie i po wczytaniu zachowuje się dzięki
stabilnej kolejności aktorów. Gdy eksploracja wymaga wskazania wykonawcy testu,
runtime chwilowo zamienia pola interakcji w kolorowe pola bohaterów. Gracz klika
pole odpowiadające portretowi. Po wyborze skan zostaje wyłączony na czas opisu i
rzutu. Karty ekranowe pozostają równoważnym wyborem awaryjnym.

Docelowa hierarchia informacji, widoki eksploracji, NPC, encountera i walki oraz
kontrakt plansza–monitor są opisane w `docs/PLAYER_UI_DESIGN.md`. Koncepcyjne mockupy
ustalają klimat dark fantasy, ale cyfrowe mapy i pozycje figurek nie są częścią
docelowego layoutu: przestrzeń pozostaje domeną fizycznej planszy.

### Eksploracja zaczyna się od fikcji

Po wejściu do lokacji gracze najpierw widzą ilustrację i opis sytuacji. Aplikacja
nie pokazuje od razu listy testów, ST ani kompletnego menu rozwiązań. Drużyna
wybiera widoczny cel sceny, wskazuje uczestników i swobodnie opisuje metodę jego
osiągnięcia. Osobne pole rozmowy służy wyłącznie pytaniom do MG.

Pytanie o jawny fakt otrzymuje odpowiedź bez rzutu. Poszukiwanie albo przygotowanie
może dopiero później prowadzić do testu, zasobu lub komplikacji. System nie może
tworzyć przedmiotów i faktów tylko dlatego, że gracz o nie zapytał.

MG odpowiada w fikcji także na działania dziwne, nieskuteczne albo nierozsądne.
Jeżeli bohater może wykonać samą czynność, brak sensownego sposobu pokonania
wyzwania nie jest błędem wejścia: świat reaguje narracyjnie, a oczywiste skutki,
takie jak hałas lub dozwolona komplikacja, są stosowane natychmiast bez sztucznego
rzutu. Skutki pozostają ograniczone polityką contentu i walidowane przez runtime.

Teksty LLM powinny brzmieć jak żywy MG przy stole: obrazowo, zwięźle i z lekkim
humorem sytuacyjnym w duchu D&D. Humor wynika z postaci i konsekwencji sceny; nie
używa współczesnych memów, nie ośmiesza graczy i nie ujawnia technicznych flag,
identyfikatorów ani progów mechaniki.

Komenda wyszukiwania najpierw sprawdza konkretną nazwę w istniejących elementach
sceny. Jeśli nazwanego przedmiotu nie ma, LLM może przełożyć potrzebną funkcję na
właściwości, ale zamiennik wybiera deterministyczny runtime, a gracze muszą go
zaakceptować. Znaleziony element pozostaje częścią lokacji i jest pokazywany jako
wiedza drużyny o scenie; nie trafia automatycznie do ekwipunku. Przeniesienie,
zabranie albo przyznanie przedmiotu zadaniowego jest osobnym efektem gry.

Komenda użycia zawsze wiąże deklarację z jednym istniejącym źródłem ze sceny,
zasobów albo ekwipunku. LLM rozpoznaje odniesienie językowe i proponuje mechanikę,
ale runtime sprawdza identyfikator, dostępność oraz zgodność źródła. Bezpośrednie
użycie elementu sceny pokazuje przed akceptacją jego stan, właściwości, wpływ na
test i ryzyko. Samo użycie nie przenosi elementu sceny do ekwipunku.

Komenda zabrania jest osobnym, potwierdzanym transferem. Runtime rozpoznaje dokładny
element, sprawdza jego dostępność i przenośność, a następnie pokazuje ilość, źródłową
lokację, niosącą postać oraz docelowe miejsce. Zwykłe przedmioty trafiają do ekwipunku
wybranego bohatera, skarby do wspólnych łupów, a przedmioty fabularne do zasobów
scenariusza zgodnie z `collection_destination` definicji. Element przytwierdzony nie
może zostać automatycznie odłączony przez `/weź`; wymaga osobnej akcji i jawnych
konsekwencji. Znalezienie, użycie i zabranie pozostają trzema różnymi zmianami stanu.

Jawna `/akcja` może trwale zmienić fixture sceny tylko wtedy, gdy content tego
fixture'a definiuje odpowiednią `action_policy`. LLM wybiera istniejący cel oraz
operację (`detach`, `damage`, `destroy`, `move`, `open`, `close`, `unlock`,
`loot`, `repair`), ale
silnik narzuca cechę, umiejętność, poziom trudności, postęp, hałas, komplikację i
wynikowy stan. Sukces zapisuje runtime state obiektu i może ujawnić authored
`yield_items`; porażka nie może samodzielnie zmienić stanu fixture'a. Wzmianka o
obiekcie w opisie działania nie wystarcza do uruchomienia operacji na nim.

Drzwi, zamki i pojemniki mają również bezpośrednie przyciski lokalnego runtime.
Nie wymagają klasyfikacji LLM: content ustala dozwolone operacje, DC zamka,
wymagane narzędzia, stan początkowy i zawartość. Otwarty lub zniszczony fixture
przestaje blokować ruch i zapewniać cover po przejściu do encountera. Obiekt
niszczalny używa jawnego KP, HP oraz opcjonalnego progu obrażeń; wpisanie rzutu
ataku i obrażeń pozostaje fizyczną czynnością graczy.

Jeśli drużyna nie ma pomysłu, może rozwinąć opcjonalne inspiracje zawierające
przykładowe działania bez ST i ukrytych konsekwencji. Dokładne parametry testów,
postęp, hałas i sekretne ryzyka pozostają w osobnej sekcji MG/debug. Mechanika
pojawia się graczom dopiero po interpretacji ich deklaracji i przed akceptacją rzutu.

Aktywne badanie niepewnego albo ukrytego fragmentu sceny może uruchomić stopniowane
rozpoznanie. Jeden test ujawnia wszystkie warstwy informacji, których progi osiągnął
końcowy wynik. Nieosiągnięcie najniższego progu oznacza brak rozstrzygającej informacji,
a nie potwierdzenie nieobecności zagrożenia. Ujawnione fakty i ich efekty są definiowane
w contencie oraz rozliczane deterministycznie; LLM wybiera pasującą obserwację i tworzy
narrację, ale nie ustala wyniku ani nie ujawnia faktów zza kurtyny przed rzutem.

### Rozpoczęcie encountera wynika ze sceny

Przejście z eksploracji do walki ma osobny, jawny etap przed setupem i inicjatywą.
Silnik obsługuje trzy wyniki: drużyna zaskakuje przeciwników, nikt nie jest
zaskoczony albo przeciwnicy zaskakują drużynę. Nie próbuje sam wymyślać, co powinno
dać zaskoczenie: scenariusz definiuje uporządkowane reguły oparte na zapisanym stanie,
np. poziomie hałasu, ujawnionych faktach i tagach podejścia kończącego przeszkodę.

W scenie bramy głośne wyważenie oznacza gotowość obu stron, wysoki hałas bez
rozpoznania pozwala goblinom przygotować zasadzkę, rozpoznanie chroni drużynę przed
tą zasadzką, a ciche wejście zaskakuje gobliny. Przy cichym wejściu po setupie i
przed inicjatywą każdy bohater może wykonać jedną próbę Stealth. Wynik jest
porównywany osobno z passive Perception przeciwników i określa, przed kim bohater
zaczyna walkę ukryty. Bazowa kara zaskoczenia nadal obejmuje całą stronę i jest
uproszczeniem D&D 5e 2014: zamiast utraty ruchu, akcji i reakcji daje utrudnienie do
inicjatywy. Po ustaleniu kolejności obie strony rozgrywają pełne tury.

Scenariusz może oznaczyć porażkę encountera jako terminalne `game_over` zamiast
powrotu do eksploracji. Gdy automatyczne checkpointy są aktywne, runtime zapisuje
osobny checkpoint bezpośrednio po setupie i ustaleniu inicjatywy, ale przed
pierwszą akcją. Retry odtwarza dokładnie skład, zasoby, pozycje, teren i kolejność
inicjatywy, ale nie przechodzi od razu do aktywnej tury: najpierw ponownie prowadzi
graczy przez grupowy setup bohaterów, jawnych przeciwników i elementów terenu na
zapisanych polach. Checkpoint encountera nie zastępuje zwykłego zapisu scenariusza.

W MVP pola z `blocking_terrain` i przeszkodami blokującymi ruch są niewchodzalne. Pola obiektów sceny typu `container`, np. rozbity wóz, mogą być zajmowane, dopóki content nie oznaczy ich jako blokujące.

---

## Pierwszy Techniczny Kamień Milowy

Pierwszy techniczny kamień milowy służy sprawdzeniu, czy podstawowe systemy działają poprawnie.

Ta wersja nie musi jeszcze być pełną sceną grywalną.

Pierwszy techniczny kamień milowy musi obsługiwać:

* jedną postać gracza,
* jednego potwora,
* inicjatywę,
* kolejność tur,
* ruch,
* ataki wręcz,
* rzuty ataku,
* rzuty obrażeń,
* punkty życia,
* stan śmierci albo pokonania,
* ręczne wpisywanie wyników rzutów kośćmi,
* wizualizację ruchu LED,
* wizualizację celów ataku LED.

Nie jest wymagane w pierwszym technicznym kamieniu milowym:

* czary,
* reakcje,
* ataki okazyjne,
* stany,
* koncentracja,
* cechy klasowe,
* sztuczna inteligencja potworów,
* ekwipunek,
* progresja kampanii,
* cyfrowy roller kości jako główny sposób wykonywania rzutów.

---

## Pierwsza Grywalna Scena

Po ukończeniu pierwszego technicznego kamienia milowego projekt powinien obsłużyć pierwszą prostą scenę grywalną.

Pierwsza grywalna scena powinna zawierać:

* dwóch bohaterów,
* trzy potwory,
* jednego NPC albo jeden obiekt interaktywny,
* prostą mapę z przeszkodami,
* podstawowy cel sceny,
* możliwość zakończenia starcia,
* podsumowanie wyniku.

Ta scena powinna nadal korzystać tylko z mechanik MVP.

Nie należy dodawać nowych dużych systemów tylko po to, aby scena była bardziej rozbudowana.

---

## Bazowe Mechaniki D&D 5e

Mechaniki początkowe:

* cechy postaci,
* modyfikatory cech,
* premia z biegłości,
* klasa pancerza,
* punkty życia,
* tymczasowe punkty życia,
* szybkość,
* inicjatywa,
* rzuty ataku,
* rzuty obrażeń,
* testy cech,
* rzuty obronne,
* przewaga,
* utrudnienie.

Silnik walki musi obsługiwać:

* ruch,
* akcję,
* placeholder na akcję dodatkową,
* placeholder na reakcję.

Mechaniki należy implementować tylko wtedy, gdy są potrzebne.

Nie należy implementować całego systemu D&D 5e naraz.

---

## Rzuty Kośćmi

Aplikacja nie zastępuje fizycznych kości.

Domyślny model gry zakłada, że gracze i Mistrz Gry wykonują rzuty fizycznymi kośćmi przy stole, a następnie wpisują wynik do aplikacji.

Aplikacja może obliczać modyfikatory, premie i końcowy rezultat, ale nie powinna wymuszać cyfrowego rzutu.

### Główna Zasada

Gracz rzuca fizyczną kością.

Aplikacja pyta o wynik rzutu.

Gracz wpisuje naturalny wynik z kości.

Aplikacja dolicza odpowiednie modyfikatory i rozstrzyga efekt.

Przykład:

* gracz wykonuje rzut ataku,
* fizycznie rzuca `d20`,
* wypada `14`,
* gracz wpisuje `14`,
* aplikacja dodaje premię do ataku, na przykład `+5`,
* aplikacja porównuje wynik `19` z klasą pancerza celu.

### Rodzaje Rzutów

Aplikacja musi obsługiwać następujące typy rzutów:

* rzut ataku,
* rzut obrażeń,
* test cechy,
* rzut obronny,
* rzut inicjatywy,
* rzut leczenia,
* rzut śmierci, gdy aktywny bohater ma 0 HP i nie jest stabilny.

### Rzuty d20

Rzuty d20 obejmują:

* rzuty ataku,
* testy cech,
* rzuty obronne,
* inicjatywę.

Aplikacja powinna przechowywać:

* naturalny wynik na kości,
* użyty modyfikator,
* premię z biegłości, jeśli dotyczy,
* informację o przewadze albo utrudnieniu,
* wynik końcowy,
* rezultat rozstrzygnięcia.

### Przewaga I Utrudnienie

W przypadku przewagi albo utrudnienia gracz nadal rzuca fizycznymi kośćmi.

Aplikacja powinna pozwolić wpisać dwa wyniki `d20`.

Dla przewagi:

* aplikacja wybiera wyższy wynik.

Dla utrudnienia:

* aplikacja wybiera niższy wynik.

Aplikacja powinna przechowywać oba wyniki, wybrany wynik oraz końcowy rezultat.

### Naturalne 20 I Naturalne 1

Aplikacja musi przechowywać naturalny wynik rzutu, ponieważ naturalne `20` i naturalne `1` mogą mieć specjalne znaczenie.

W MVP specjalne rozstrzyganie naturalnego `20` i naturalnego `1` dotyczy rzutów ataku oraz rzutów śmierci.

Dla MVP:

* naturalne `20` przy rzucie ataku oznacza trafienie krytyczne,
* naturalne `1` przy rzucie ataku oznacza automatyczne pudło,
* naturalne `20` przy rzucie śmierci przywraca 1 HP,
* naturalne `1` przy rzucie śmierci daje dwie porażki,
* naturalne `20` i naturalne `1` przy testach cech nie powinny automatycznie oznaczać sukcesu albo porażki, chyba że późniejsza reguła projektu zdecyduje inaczej.

### Rzuty Obrażeń

Rzuty obrażeń są wykonywane fizycznymi kośćmi.

Aplikacja powinna pozwolić wpisać:

* wynik z kości obrażeń,
* modyfikator obrażeń,
* typ obrażeń, jeśli jest znany.

Przykład:

* broń zadaje `1d8 + 3`,
* gracz rzuca fizycznie `d8`,
* wypada `6`,
* gracz wpisuje `6`,
* aplikacja dodaje `+3`,
* końcowe obrażenia wynoszą `9`.

### Trafienia Krytyczne

W przypadku trafienia krytycznego aplikacja powinna jasno wskazać, że wymagany jest rzut obrażeń dla trafienia krytycznego.

W MVP dopuszczalne są dwa warianty implementacji:

* gracz ręcznie wpisuje końcowy wynik obrażeń krytycznych,
* aplikacja prosi o wpisanie osobnych wyników z dodatkowych kości obrażeń.

Preferowany wariant MVP:

* gracz wpisuje końcowy wynik obrażeń po samodzielnym rzucie wszystkimi wymaganymi kośćmi.

Bardziej szczegółowe rozbijanie kości obrażeń można dodać później.

### Nieprzytomność I Stabilizacja

Bohater przy 0 HP pozostaje w inicjatywie dla rzutów śmierci, ale nie może wykonywać
zwykłej tury ani reakcji. Ataki przeciw niemu mają przewagę, a trafienie z odległości
nie większej niż 5 feet jest krytyczne. Sąsiedni sojusznik może zużyć akcję na test
Wisdom (Medicine) ST 10 albo jedno użycie zestawu uzdrowiciela, aby go ustabilizować.
Przy zejściu do 0 HP wyposażona broń zostaje niewyposażona i pojawia się jako prosty
obiekt na aktualnym polu aktora. Podniesienie wymaga stania na jej polu i korzysta
z darmowej interakcji z obiektem, a po jej wykorzystaniu z akcji. Podniesiona broń
pozostaje niewyposażona. Bohater wyposaża albo zamienia broń przez kategorię
`Ekwipunek` w menu własnego pola; obowiązuje ten sam koszt interakcji. Uproszczona
zamiana nie łączy już schowania i dobycia w jedną czynność: każda obsługa osobnego
przedmiotu jest oddzielną interakcją. Pierwsza jest darmowa, druga zużywa akcję, a
czynność wymagająca trzech interakcji nie mieści się w zwykłej turze. Jawne upuszczenie
wyposażonej broni nie zużywa akcji ani interakcji i tworzy obiekt na aktualnym polu.
Jawny model obu dłoni oraz lekkich broni obsługuje walkę dwiema broniami. Tarcza
zajmuje jedną dłoń, daje premię do efektywnego KP oraz wymaga akcji do założenia i
zdjęcia. Opcja „wyposaż i zaatakuj” jest dostępna tylko wtedy, gdy dobycie nie wymaga
wcześniejszego schowania innego przedmiotu; gracz może zamiast tego upuścić trzymaną
broń, dobrać nową i zaatakować.

### Cyfrowe Rzuty Kośćmi

Cyfrowy roller kości nie jest wymagany w MVP.

Może zostać dodany później jako opcja pomocnicza.

Jeżeli cyfrowy roller zostanie dodany w przyszłości:

* nie może zastąpić domyślnego modelu fizycznych kości,
* powinien być opcjonalny,
* powinien dać się wyłączyć,
* nie powinien być wymagany do rozegrania spotkania.

### Wymagania Implementacyjne Dla Rzutów

System rzutów powinien rozdzielać:

* naturalny wynik kości,
* modyfikatory,
* wynik końcowy,
* rezultat mechaniczny.

Silnik zasad nie powinien losować wyników, jeżeli gracz podaje wynik fizycznego rzutu.

Funkcje rozstrzygające rzuty powinny być deterministyczne i testowalne.

Przykładowe dane wejściowe:

```text
roll_type: attack_roll
natural_roll: 14
modifier: 5
advantage_state: normal
target_ac: 16
```

Przykładowe dane wyjściowe:

```text
natural_roll: 14
total_result: 19
target_number: 16
success: true
critical_hit: false
critical_miss: false
```

---

## Model Aktora

Postać z kreatora zachowuje źródła swoich grantów jako `FeatureGrant`, ale
wykonanie mechaniki pozostaje we wspólnym silniku:

- Fighting Style: Defense zwiększa efektywne KP tylko podczas noszenia pancerza,
- Archery daje `+2` wyłącznie do ataków bronią dystansową,
- Dueling daje `+2` do obrażeń jednoręcznej broni melee, jeżeli druga ręka nie
  trzyma innej broni; tarcza jest dozwolona,
- Two-Weapon Fighting zachowuje dodatni modyfikator cechy w obrażeniach drugiej broni,
- Second Wind wymaga fizycznego wyniku `d10`, zużywa akcję bonusową i jedno użycie
  odnawiane po short lub long rest,
- Sneak Attack na poziomie 1 dodaje osobny komponent `1d6` tego samego typu co
  broń. Wymaga broni finesse albo ranged, braku disadvantage oraz advantage lub
  aktywnego sojusznika przy celu. Użycie oznaczamy dopiero po trafieniu i
  wygaszamy na początku następnej tury łotrzyka,
- kreator rozdziela znane cantripy, listę klasową albo spellbook, przygotowane
  czary oraz czary domenowe niezużywające limitu przygotowania,
- Domena Życia zapewnia ciężki pancerz, zawsze przygotowane czary domenowe oraz
  `Disciple of Life` skalowane poziomem użytego slotu,
- Arcane Recovery jest zasobem odnawianym przez long rest; po ukończonym short
  reście może odzyskać legalny, zużyty slot,
- Lucky nie losuje za gracza: naturalna jedynka otwiera kontrakt dodatkowego
  fizycznego rzutu, a wynik zachowuje pierwotną i zastępczą kość; przy
  advantage/disadvantage każda jedynka jest przerzucana przed wyborem wyniku,
- Brave, Fey Ancestry i Dwarven Resilience korzystają ze wspólnych tagów save'a
  (`fear`, `charm`, `poison`); Fey Ancestry udostępnia też deterministyczną
  ochronę przed `magical_sleep`,
- Halfling Nimbleness pozwala przejść przez pole większego przeciwnika jako
  difficult terrain, ale nie pozwala zakończyć tam ruchu,
- Trance ustawia indywidualny wymóg long resta na 240 zamiast 480 minut,
- Stonecunning daje podwójną biegłość wyłącznie testom oznaczonym przez content
  tagiem `stonework`,
- Military Rank, Criminal Contact, Shelter of the Faithful i Researcher są
  stabilnymi uprawnieniami backgroundu. Zadziałają tylko wtedy, gdy postać je
  posiada i bieżąca scena jawnie udostępnia odpowiadającą okazję.

Kreator używa bazowych dziewięciu ras i dwunastu klas zgodnych z projektem
SRD 5.1 oraz rozszerza wybór tła do trzynastu archetypów podstawowej gry 2014.
Background zawsze przyznaje dwie biegłości umiejętności, wyposażenie, złoto,
odpowiednie języki lub narzędzia oraz stabilne uprawnienie scenowe. Wybrane
narzędzie jest jednocześnie faktycznym przedmiotem startowym, jeśli jego definicja
znajduje się w katalogu wyposażenia. Opisy fabularne w UI są tekstami projektu,
a mechaniczne podsumowania powstają bezpośrednio z tych samych definicji, których
używa builder postaci.

Każdy profit rasy, wariantu rasy i backgroundu ma wspólny opis gracza w
`character_creation/feature_help.py`. Kreator pokazuje przy nazwie dostępny
myszą i klawiaturą tooltip, który rozdziela treść zasady od sposobu wykonania
w tej aplikacji. Audyt pochodzenia odrzuca profit bez takiego opisu, bez
sklasyfikowanego kontraktu runtime albo background bez stabilnego permission
ID.

Profity backgroundów są mechaniką kontekstową, a nie bezwarunkowym bonusem.
`rules/background_features.py` wymaga jednocześnie grantu postaci i permission
udostępnionego przez bieżącą scenę. Oznacza to, że np. `False Identity` może
odblokować gotową przykrywkę, ale nie gwarantuje sukcesu wobec podejrzliwego
NPC, a `Researcher` wskazuje źródło wiedzy zamiast automatycznie ujawniać
odpowiedź. Aktualne scenariusze referencyjne nie zawierają jeszcze okazji dla
wszystkich trzynastu backgroundów; ich stopniowe dodawanie jest pracą
contentową, nie brakującym resolverem.

Jawny wyjątek rasowy to `Tinker`: biegłość w narzędziach majsterkowicza jest
wykonywalna, ale dowolne drobne urządzenia nadal wymagają receptury, authored
okazji w scenariuszu albo rozstrzygnięcia przy stole. Nie istnieje jeszcze
uniwersalny kreator tych gadżetów.

Nazwy widoczne dla gracza korzystają ze wspólnego polskiego katalogu
`core/player_labels_pl.py`. Stabilne angielskie ID pozostają wewnętrznym
kontraktem contentu i zapisów, ale kreator, karta postaci i załadowane definicje
czarów pokazują polskie nazwy. Audyt wymaga wpisu dla wszystkich czarów oraz
każdej umiejętności, biegłości narzędziowej, opcji i języka używanych przez
kreator.

„Tool proficiency” jest prezentowane zależnie od faktycznej kategorii jako
zestaw do gry, instrument muzyczny, narzędzia rzemieślnicze albo ogólna
biegłość narzędziowa. Wybranie zestawu przyznaje biegłość i odpowiadający jej
przedmiot. Test wykorzystujący narzędzie dodaje premię z biegłości tylko wtedy,
gdy postać ma właściwą biegłość oraz dostępny przedmiot.

Wszystkie istoty powinny używać wspólnego modelu `Actor`.

### Postacie Graczy

* id
* imię albo nazwa
* poziom
* placeholder klasy
* cechy
* premia z biegłości
* wspólny profil biegłości w saving throwach, skillach, broniach, pancerzach i narzędziach
* klasa pancerza
* punkty życia
* tymczasowe punkty życia
* szybkość
* modyfikator inicjatywy
* pozycja
* dostępne akcje

### Fizyczna Karta Postaci I Karty Decyzji

Każdy gracz docelowo otrzymuje fizyczną kartę postaci A4/A5 oraz małą talię kart
decyzji. Materiały te uzupełniają planszę i monitor:

* plansza pozostaje interfejsem pozycji, ruchu, celów i obszarów,
* karta z QR deklaruje szczególną intencję gracza, np. czar, cechę, manewr,
  przedmiot albo akcję uniwersalną,
* fizyczne kości dostarczają naturalny wynik rzutu,
* monitor pokazuje preview, wymagane koszty, kolejne kroki i rozstrzygnięcie.

Zeskanowanie karty nie wykonuje działania bezpośrednio. QR zawiera wyłącznie
stabilny, wersjonowany identyfikator, a warstwa aplikacyjna mapuje go na aktualny
katalog legalnych działań i ponownie sprawdza aktywną postać, właściciela źródła,
wyposażenie, zasoby, ekonomię akcji oraz legalność celu. Menu ekranowe pozostaje
pełnym fallbackiem. Czytnik QR jest osobnym adapterem wejścia i nie należy do
pakietu `board/`.

Pierwsza wersja payloadu ma kanoniczny format
`dndbg:v1:action:<rodzaj>:<source_id>`, na przykład
`dndbg:v1:action:spell:eldritch_blast`. Rodzaj należy do zamkniętego katalogu
`attack`, `spell`, `feature`, `item` i `universal`, a `source_id` używa wspólnej
składni stabilnych identyfikatorów `snake_case`. QR nie zawiera statystyk postaci,
kosztów ani reguł działania. Generator zapisuje obok obrazu metadane umożliwiające
sprawdzenie payloadu, wersji, korekcji błędów i rozmiaru symbolu.

Podstawowy atak bronią jest świadomym wyjątkiem od przepływu kart. Gracz wskazuje
pole przeciwnika na planszy, a kontekstowe menu pokazuje legalne warianty ataku
aktywną bronią; gdy nie ma aktywnej broni, wystawia atak bez broni. Jeśli pole
łączy przeciwnika z obiektem lub inną intencją, to samo menu rozdziela atak,
ruch i interakcję. Karty nadal wybierają czary, cechy i manewry specjalne, po
czym plansza służy wyłącznie do wskazania ich celu albo obszaru. Wycofana karta
`attack:basic_attack` nie jest częścią aktywnego katalogu skanera.

Zagrywanie fizycznych kart eksploracji jest obecnie wyłączone. Ich definicje,
QR-y i pliki pozostają w repozytorium jako materiał projektowy, ale skan poza
walką nie tworzy efektu ani nie zużywa zasobu. Eksploracja korzysta zamiast tego
z autorskich kafelków contentu. Kafelek może wymagać obecności konkretnego
bohatera w aktywnej drużynie i automatycznie przypisać go jako wykonawcę. Dzięki
temu scena może wystawić zarówno funkcjonalne podejście, jak i opcjonalny moment
rozwoju postaci bez globalnej reguły próbującej zastosować tę samą zdolność w
każdej lokacji. Nieobecność bohatera ukrywa kafelek i nigdy nie blokuje głównego
przebiegu scenariusza. Fizyczne karty pozostają aktywnym interfejsem walki.

Walka pokazuje nienachalne przypomnienie o kartach dokładnie w chwili, w której
skaner może je legalnie przyjąć. W kroku wyboru jest to zwarta lista kart
bieżącego bohatera wyliczona z tego samego katalogu legalnych akcji co menu
planszy. W oknie reakcji pasek wskazuje konkretną postać i kartę, na przykład
`Lorian — Cięta riposta`. Przypomnienie nie otwiera modala, nie zużywa zasobu i
nie blokuje zwykłego przycisku kontynuacji. Legalność uwzględnia właściciela,
aktualne okno rozstrzygnięcia, ekonomię akcji i dostępność źródła; karta bohatera
nieaktywnego w inicjatywie jest dozwolona wyłącznie wtedy, gdy otwarte okno
reakcji wskazuje właśnie jego jako reagującego.

Pierwsza talia kontrolna zawiera dwie uniwersalne karty:

* `ACCEPT` (`universal:accept`) działa jak kontekstowy Enter: zatwierdza widoczną
  decyzję, przechodzi dalej, wchodzi w przygotowaną interakcję albo potwierdza
  aktualny preview; obejmuje też Start oraz instrukcyjne kroki setupu, natomiast
  krok wymagający fizycznego przypisania figurki uruchamia skan planszy;
* `DECLINE` (`universal:decline`) odrzuca decyzję, zamyka dialog albo anuluje
  aktualny, jeszcze nierozstrzygnięty wybór, w tym czar, atak lub reakcję. Gdy
  nie ma już głębszego wyboru, zamyka ukończoną interakcję, kończy rozmowę z NPC
  albo wychodzi z bieżącej instancji eksploracyjnej do wyboru lokacji. Kolejny
  skan może więc najpierw anulować formularz, a dopiero następny zakończyć scenę.

Karta kontrolna działa tylko wtedy, gdy bieżący stan wystawia dokładnie
odpowiadającą operację. Brak pasującej operacji daje krótki komunikat i nie zmienia
stanu. `DECLINE` nie cofa kosztu ani działania, które zostało już rozstrzygnięte.
Czytnik USB w trybie keyboard-wedge wysyła cały payload zakończony Enterem;
przeglądarka buforuje szybki prefiks `dndbg:` także wtedy, gdy fokus znajduje się
w polu tekstowym, dzięki czemu kod nie trafia do wiadomości gracza. Równoległy
bufor ostatnich klawiszy rozpoznaje pełny payload również wtedy, gdy czytnik ma
skonfigurowane wolniejsze odstępy między znakami. Adapter normalizuje też
zaobserwowane translacje układu klawiatury `>` → `:` oraz `?` → `_`, na
przykład `dndbg>v2>action>spell>hunters?mark>erynd`, zanim payload trafi do
wspólnego parsera.
Przyciski ekranowe pozostają potrzebnym fallbackiem przy braku lub awarii
czytnika. Blokada powtórzeń jest liczona od zakończenia obsługi karty, dzięki
czemu pojedynczy skan nie może zatwierdzić dwóch kolejnych etapów, nawet gdy
pierwsza odpowiedź serwera trwa dłużej.

W miejskich instancjach wybór lokacji prowadzi bezpośrednio do dostępnych
kafelków interakcji. Nie wymaga dodatkowego ustawiania figurki NPC, ponieważ
pozycja nie rozstrzyga tam ruchu, zasięgu ani celu mechanicznego. Fizyczny setup
figurek pozostaje wymagany w scenach, w których położenie ma znaczenie regułowe.

Warstwa ilustracyjna kart może korzystać z generowanych teł rastrowych, ale tekst,
symbole, właściwy kod QR, spady i znaczniki cięcia są nakładane deterministycznie
przez generator PDF. Dzięki temu stylistyka może się zmieniać bez ryzyka
zniekształcenia payloadu lub utraty czytelności informacji użytkowych.

Fizyczna karta postaci jest artefaktem gracza. Zawiera generowane dane
mechaniczne oraz miejsca uzupełniane ręcznie, między innymi notatki, historię,
osobowość i więzi. Aktualnie bohaterowie zaczynają na poziomie 3 z pełną talią,
a system dalszego rozwoju jest odłożony. Gdy zostanie zaprojektowany, aplikacja
pozostanie źródłem prawdy dla poziomu, PW, zasobów, statystyk, ekwipunku i
legalności akcji, aby papier i zapis kampanii nie tworzyły dwóch sprzecznych
stanów mechanicznych.

Pierwszy zakres wdrożenia obejmuje jedną postać i małą talię reprezentującą
akcję uniwersalną, czar lub cechę klasową oraz przedmiot. Podstawowy atak wybiera
się bez karty przez pole przeciwnika na planszy.
Karty powinny być generowane do gotowego do druku PDF z grafiką, tekstem,
rewersem, marginesami i kodem QR sprawdzonym w docelowym rozmiarze.

### Potwory

* id
* nazwa
* id bloku statystyk
* klasa pancerza
* punkty życia
* szybkość
* cechy
* akcje
* modyfikator inicjatywy
* pozycja

### Profil biegłości aktora

Każdy typ aktora korzysta z tego samego `ProficiencyProfile`. Profil przechowuje
biegłości w saving throwach, skillach, broniach, pancerzach i narzędziach oraz
expertise w skillach. Klasa, rasa albo statblock będą później składać ten profil,
ale resolvery nie sprawdzają nazwy klasy ani typu aktora.

Ability check, saving throw i attack roll budują wspólny `D20RollRequest` z osobnych
składników. Premia ataku bronią wynika z wybranej cechy oraz biegłości aktora w id
broni; nie jest przepisywana jako gotowa liczba do każdego aktora. Saving throw
dodaje proficiency tylko wtedy, gdy dana cecha znajduje się w profilu. Wszystkie
składniki są widoczne w instrukcji i podglądzie rzutu.

Test narzędzia jest nadal ability checkiem: content wskazuje cechę i stabilne id
narzędzia, a profil aktora decyduje, czy doliczyć premię z biegłości. Jeśli jedna
próba sensownie korzysta równocześnie ze skilla i narzędzia, premia z biegłości
nie sumuje się drugi raz; expertise może zastąpić zwykłą biegłość.

Test przeciwstawny rozstrzyga dwa kompletne rzuty ability check. Wyższy wynik
wygrywa, a remis zachowuje stan sprzed próby. Ten resolver jest wspólną podstawą
dla akcji takich jak Shove i przyszły Grapple, ale sam nie narzuca ich ekonomii
akcji, zasięgu ani skutków.

### Typy obrażeń i odporności

Każde obrażenia mają jawny typ. Jedno zdarzenie może zawierać kilka składników,
na przykład obrażenia cięte i od ognia; silnik rozlicza każdy typ osobno. Aktor ma
generyczny profil resistance, immunity i vulnerability niezależny od klasy, rasy
czy konkretnego statblocku.

UI zawsze pokazuje wartość przed profilem celu, zastosowaną relację i końcowe
obrażenia. Resistance, immunity ani vulnerability nie mogą być ukrytym modyfikatorem
widocznym wyłącznie w logach. Temporary HP pochłania obrażenia dopiero po tym
rozliczeniu.

### Shove

Resolver Shove pozostaje przetestowaną mechaniką legacy, ale nie jest obecnie
wystawiany na liście działań bohaterów.

Gracz wybiera sąsiedniego przeciwnika bezpośrednio na jego polu, a następnie
decyduje, czy chce go powalić, czy odepchnąć o 5 ft. Atakujący wykonuje Strength
(Athletics), cel broni się korzystniejszym Strength (Athletics) albo Dexterity
(Acrobatics). Wyłącznie wyższy wynik atakującego daje sukces; remis broni celu.

Powalenie nakłada wspólny stan `Prone`. Odepchnięcie jest ruchem wymuszonym i nie
zużywa ruchu celu ani nie prowokuje ataków okazyjnych. Opcja odepchnięcia nie jest
pokazywana, gdy pole bezpośrednio za celem jest poza planszą, zajęte lub blokowane
przez teren, ścianę albo obiekt sceny.

### Grapple

Rozpoczęcie chwytu jest aktywną zdolnością specjalną Brakki. Brakka wybiera
sąsiedniego przeciwnika z listy/trybu celu. Chwytający wykonuje
Strength (Athletics), a cel broni się lepszym Strength (Athletics) albo Dexterity
(Acrobatics). Wyłącznie wyższy wynik chwytającego nakłada `Grappled`; remis broni
celu. W obecnym modelu manewr zużywa całą akcję, dopóki Attack action nie obsługuje
wielu ataków.

`Grappled` przechowuje id chwytającego i ustawia pozostały ruch celu na 0. Chwytany
bohater może z menu własnego pola zużyć akcję na ucieczkę: wybiera automatycznie
lepsze Athletics/Acrobatics przeciw Athletics chwytającego. Chwyt kończy się również,
gdy chwytający albo cel zostaje pokonany lub zostają rozdzieleni na więcej niż 5 ft.

Chwytający może poruszać się z celem, ale jego efektywna szybkość zostaje zmniejszona
o połowę, np. z 30 do 15 ft. UI od razu ogranicza zasięg podświetlonych pól i pokazuje
redukcję szybkości. Cel trafia na poprzednie pole chwytającego; preview wskazuje to
pole różowym LED-em i podaje, którą figurkę trzeba przestawić. Wymuszony ruch celu nie
prowokuje ataku okazyjnego. Rozpoczęcie chwytu wymaga wolnej ręki; UI pokazuje rękę
zarezerwowaną przez trwający chwyt. Cel Grapple może być najwyżej o jedną kategorię
rozmiaru większy od chwytającego. Jedna postać nadal może utrzymywać tylko jeden
chwyt.

### Ręce i trzymane wyposażenie

Każdy aktor ma dwa jawne sloty: `main_hand` i `off_hand`. Przedmiot jednoręczny
zajmuje jeden slot, a dwuręczny oba. Wyposażenie jednoręcznej broni wykorzystuje
najpierw wolną dłoń; jeśli obie są zajęte, zastępuje domyślnie przedmiot w drugiej
ręce. Wyposażenie broni dwuręcznej zwalnia obie dłonie. Upuszczenie zwalnia wszystkie
sloty zajmowane przez przedmiot.

Stan dłoni jest widoczny w panelu aktywnego aktora i zapisywany w snapshocie.
Atak lekką bronią do walki wręcz ustawia do końca tury jawny trigger. Jeśli w drugiej
dłoni znajduje się inna lekka broń do walki wręcz, można nią zaatakować w ramach akcji
bonusowej. Do obrażeń tego ataku nie dodaje się dodatniego modyfikatora cechy, ale
pozostają inne premie oraz ujemny modyfikator cechy. Broń z
`versatile_damage_dice` wystawia dodatkowy wariant ataku oburącz, jeżeli druga ręka
jest wolna i nie została zarezerwowana przez trwający Grapple. Wariant zmienia kość
obrażeń tylko dla wybranego ataku; nie zapisujemy sztucznego trwałego stanu chwytu.

Tarcza jest trzymanym wyposażeniem z `hands_required=1`, `armor_class_bonus` oraz
`armor_proficiency`. Założona tarcza blokuje użycie tej samej ręki przez broń,
wariant versatile i Grapple. Runtime pokazuje bazowe KP oraz premię ekwipunku.
Zakładanie i zdejmowanie zużywa akcję zgodnie z tabelą czasu zakładania pancerza 5e
2014. Obecne MVP nie pozwala założyć tarczy bez biegłości, zamiast implementować cały
pakiet kar za niebiegły pancerz oraz blokadę rzucania czarów.

### Katalog broni SRD 5.1

Docelowy katalog obejmuje wszystkie 37 broni SRD 5.1 z podziałem na simple/martial
oraz melee/ranged. Definicja przechowuje wyłącznie kość lub stałą bazę obrażeń;
modyfikator Siły albo Zręczności jest wiązany z aktualnym aktorem także po
podniesieniu broni przez inną postać. Finesse wystawia jawne warianty cechy.

Thrown tworzy wariant dystansowy i po wykonaniu ataku przenosi jeden egzemplarz
broni z ekwipunku na pole celu jako podnoszalny obiekt. Normalny/daleki zasięg jest
jawny, a atak powyżej normalnego zasięgu ma utrudnienie. Heavy daje utrudnienie
Small wielbicielowi, reach ustawia 10 ft, loading i sieć ograniczają liczbę ataków,
a jednoręczna broń z ammunition wymaga wolnej drugiej dłoni do przeładowania.

Lanca ma utrudnienie przeciw celowi w odległości 5 ft. Ponieważ runtime nie ma
jeszcze stanu mounted, pozostaje dwuręczna; wariant jednoręczny będzie częścią
mounted combat. Trafienie siecią nakłada Restrained na cel Large lub mniejszy,
zużywa/rzuca egzemplarz sieci i ogranicza Attack action do jednego ataku. Cel może
zużyć akcję na Strength check ST 10. Niszczenie sieci jako AC 10 / 5 HP wymaga
przyszłego wspólnego modelu atakowalnego wyposażenia.

### NPC

* trwały stan rozmówcy obejmuje nastawienie, kondycję fizyczną i emocjonalną,
  ujawnione informacje, wykorzystane próby oraz historię relacji,
* reakcje na prośby korzystają z deterministycznej tabeli attitude/risk 2014,
* gracz wybiera Persuasion, Deception albo Intimidation; LLM nie wybiera skilla,
  ST ani skutków testu społecznego,
* content definiuje zmiany stanu, limity ponowień, wyniki i przejścia sceny.

---

## Model Planszy

### Fizyczna Plansza

* 20 kolumn
* 30 rzędów

### Koordynaty

```text
(col, row)
```

### Skala

* jedno pole odpowiada 5 feet

### Elementy Planszy

* aktorzy,
* teren,
* ściany,
* blokery,
* drzwi,
* obiekty interaktywne,
* efekty obszarowe.

Pathfinding musi być:

* deterministyczny,
* niezależny od sprzętu,
* w pełni testowalny.

---

## Eksploracja I Wyzwania

### Konfrontacje z maną — wdrożenie 2026-09-14

Wspólny silnik obsługuje siedem metod społecznych i siedem obiektowych,
ze stałymi wykonawcami i cechami (w tym KON Zastraszania Brakki). Wartości
wybranej metody odsłaniają się po zobowiązującym rozpoczęciu. Trzy profile
wartości mają różne właściwości; nie są uniwersalną skalą trudności.

Fizyczna talia 25 kart; wybór jednej z dwóch, opcjonalne dociąganie duplikatów
do innej barwy, pas przed ofertą. Dokładnie 21 daje sukces. Przekroczenie
powoduje **utrudnienie końcowego testu, bez premii za karty**: dwa k20 i niższy
wynik; nie ma −3. Test dodaje właściwą cechę, należną biegłość i pasyw.
Jedna jawna przeszkoda: powtórzony kolor +2, następny po czerwonej +2 lub
limit czterech wyborów ze zwykłym pasem. Lorian zachowuje +2 i przerzut własnego
testu CHA; Erynd ma +2 do własnego końcowego testu obiektu w eksploracji.

Arena udostępnia każdej postaci rozmowę z Ireną, interakcję ze skrzynią,
lekcje podstaw i samodzielne sceny z trzema obecnymi wykonawcami. Pułapka
bojowa ma zwykłe wykrywanie MDR/Percepcja i dezaktywację ZRĘ/narzędzia,
z pozycją, kosztem akcji i zapisem stanu. Zaliczenia eksploracji są oddzielne
od dotychczasowego combatu; podstawy kart zalicza się raz wspólnie.

Nowe karty i pomoc korzystają z tego samego katalogu. Stan próby oraz
zaliczenia są zapisywane; stare polecenia są odrzucane, a wczytany dobór
wymaga potwierdzenia zachowanych fizycznych stosów. Dotychczasowe treści
kampanii i ExplorationTrap pozostają obsługiwane w ich istniejącym formacie.
Szczegóły i nawigacja: [opis wdrożenia](docs/EXPLORATION_MANA_IMPLEMENTATION.md).

### Odprawa Nessy — dopracowanie 2026-09-05

Siedem tematów ma stałe numery/pola. Omówione tematy udostępniają wyłącznie
odczyt rzeczywistego wyniku; nie ponawiają nagród, rzutów ani efektów.
Nierozstrzygnięty temat zamkniętej odprawy nie ujawnia ukrytej odpowiedzi.
Obserwacja Nessy to jedna próba Intuicji ST 16, bez kary za porażkę.
Rzeczowe negocjowanie ryzyka używa Perswazji; Zastraszanie wymaga nacisku.
Umowa pokazuje należności, wypłaconą zaliczkę odliczaną od wypłaty i warunki.
Zakończenie odprawy zamyka jej testy i negocjacje; wymarsz następuje osobno przy
bramie. Bez many i toru presji. Szczegóły: `docs/NESSA_BRIEFING_POLISH.md`.


Tryb eksploracji nie powinien działać jak walka bez przeciwników.

W eksploracji drużyna porusza się wspólnie między strefami, a aplikacja prowadzi przez lokacje, punkty zainteresowania, decyzje i konsekwencje.

### Brak Twardych Blokad Rzutem

Domyślnie test eksploracyjny nie może być prostą blokadą typu:

* porażka oznacza brak przejścia,
* gracze powtarzają ten sam test aż do sukcesu,
* cała scena stoi, dopóki nie wypadnie odpowiedni wynik.

Takie zachowanie jest dopuszczalne tylko jako świadome odstępstwo opisane w contentcie albo w decyzjach reguł.

Domyślnym modelem jest `fail-forward`:

* rzut rozstrzyga jakość efektu,
* porażka może dać postęp z kosztem,
* sukces może dać postęp bez kosztu,
* wysoki sukces może dać dodatkową korzyść,
* poważna porażka może dodać komplikację.

Jedno autorskie działanie lokacji może ustawić kilka flag wyniku. Służy to
decyzjom bez rzutu, które jednocześnie zamykają wspólny wybór i zachowują jego
konkretny wariant, oraz testom fail-forward zapisującym zarówno obowiązkowy
postęp, jak i dodatkową wiedzę. Wspólna flaga wyniku uniemożliwia późniejsze
wybranie sprzeczne z już podjętą decyzją.

### Wyzwanie Z Postępem

Eksploracyjne przeszkody powinny być modelowane jako wyzwania stanowe, a nie jako
pojedyncze testy. W zależności od sceny stan może być opisany punktami postępu albo
konkretnymi flagami fizycznych blokad.

Przykład:

```text
Wyzwanie: Przeprawa przez rwącą rzekę
Cel: dostać się na drugi brzeg
Postęp wymagany: 3
Postęp aktualny: 0
Ryzyka: hałas, strata czasu, uszkodzenie sprzętu
```

Każda dostępna opcja opisuje:

* wymagany test albo warunek,
* postęp na sukcesie,
* postęp na porażce,
* konsekwencję sukcesu,
* konsekwencję porażki,
* możliwe komplikacje,
* flagi sceny ustawiane po rozstrzygnięciu.

Przykładowy model flagowy dla zamkniętej bramy:

```text
Wyważ bramę:
- test: Siła / Atletyka
- sukces: puszcza zamek i rygiel, brama otwarta, hałas
- porażka: puszcza tylko zamek, gobliny szykują zasadzkę
```

```text
Przejdź górą:
- test: Zręczność / Akrobatyka
- sukces: bohater zdejmuje rygiel od środka
- porażka: rygiel pozostaje, ryzyko upadku albo utrata czasu
```

```text
Podważ mechanizm:
- test: Inteligencja / narzędzia albo rzemiosło
- sukces: osłabia konstrukcję i ułatwia kolejne wyważanie
- porażka: narzędzie się ześlizguje, a czujność przeciwników rośnie
```

```text
Wyłam sztachetę:
- test: Siła albo Zręczność, zależnie od opisu
- sukces: +1 postępu, tworzy małe przejście albo nową opcję
- porażka: +1 postępu z komplikacją albo tylko informacja o stanie przeszkody
```

Opcje mogą mieć różne profile: szybkie, głośne, bezpieczne, ryzykowne, ciche, kosztowne albo wymagające zasobu.

Scena eksploracyjna może mieć kilka wyzwań w kolejnych strefach. Ukończenie jednego wyzwania może odblokować następną strefę, ujawnić nowy punkt zainteresowania albo przygotować hook pod inny typ interakcji, np. NPC.

Przykład:

```text
Brama -> odblokowuje Dziedziniec
Dziedziniec -> po przeszukaniu ujawnia Rannego zwiadowcę
Ranny zwiadowca -> kolejny etap: interakcja z NPC
```

### Przygotowanie Do Testu

Gracze powinni móc przygotować się do wyzwania przed głównym rozstrzygnięciem.

Przygotowanie może:

* dodać premię,
* dać przewagę,
* obniżyć ST,
* usunąć albo złagodzić komplikację,
* odblokować nową opcję,
* ujawnić informację o ryzyku.

Przykład:

```text
Zbadaj okolice bramy:
- sukces: odkrywa słaby zawias; następne "Podważ mechanizm" ma przewagę
- porażka: ujawnia tylko, że wyważenie będzie głośne
```

### Zasoby, Ekwipunek I Flagi

Opcje wyzwania mogą mieć tagi wymagań albo tagi bonusów, np.:

* `climbing`,
* `lockpicking`,
* `crowbar`,
* `rope`,
* `fire`,
* `quiet`,
* `heavy_force`.

Przed wykonaniem opcji aplikacja może pozwolić graczom otworzyć ekwipunek i wybrać zasób, narzędzie albo czar.

Jeżeli wybrany element ekwipunku ma pasującą flagę bonusu, może dodać efekt zdefiniowany po stronie itemu:

* premia liczbowa,
* przewaga,
* redukcja ST,
* dodatkowy postęp,
* anulowanie konkretnej komplikacji,
* zużycie zasobu.

Zasób sceny z `consume_on_use: true` jest jednorazowy. Silnik usuwa go dopiero po faktycznie wykonanym rzucie, także przy porażce. Sam wybór zasobu, korekta decyzji MG albo anulowanie próby nie zmieniają ekwipunku drużyny. Zasoby bez tej flagi, np. lina lub narzędzie wielokrotnego użytku, pozostają dostępne po próbie.

Scenariusz pełni także rolę pojedynczego dnia przygody. Jeśli postać korzysta z przygotowywanych czarów, wybiera listę na ten scenariusz jako ostatni krok setupu: po podłączeniu planszy i ustawieniu mapy, ale przed wyborem pierwszej lokacji. Mechanicznie wybór nadal odpowiada przygotowaniu po zakończonym długim odpoczynku w D&D 5e. Ten etap jest generyczną mechaniką aktora, a nie implementacją konkretnej klasy; cantripy nie wchodzą do wyboru, a czary zawsze przygotowane nie zajmują limitu. UI pokazuje domyślny zestaw jako karty: `AKCEPTUJ` zatwierdza go, a `ODRZUĆ` rozpoczyna własne przygotowanie przez skanowanie kolejnych legalnych kart czarów. Po zeskanowaniu dokładnie tylu różnych kart, ile wynosi limit, aplikacja zapisuje zestaw automatycznie. Klasy korzystające z czarów znanych zamiast przygotowywanych nie otrzymują tego kroku.

Long rest odbywa się automatycznie bezpośrednio przed scenariuszem. Short rest jest decyzją drużyny podczas eksploracji: UI pokazuje godzinny koszt, bezpieczeństwo miejsca, jawne zagrożenie i zasoby możliwe do odzyskania. Po ukończeniu gracze wydają Hit Dice pojedynczo. Zagrożenie nie jest uniwersalnym losowym encounterem; wynika z contentu lokacji, np. odpoczynek przed bramą zwiększa hałas, a zawalone koszary zapewniają jedno bezpieczne miejsce odpoczynku.

Podczas jednego short resta każdy bohater może dodatkowo dostroić albo odstroić
jeden wymagający tego magiczny przedmiot. Bohater może utrzymywać najwyżej trzy
więzi. Przed dostrojeniem przedmiot pozostaje w ekwipunku, ale jego akcje, specjalne
źródła i ładunki są nieaktywne. Automatyczne zakończenie więzi przez dystans, śmierć,
utratę wymagań albo dostrojenie innej istoty pozostaje poza zakresem obecnego MVP.

Pasywne moce magicznych przedmiotów są składane z typowanych efektów contentu.
Obecne prymitywy obejmują premie do KP, rzutów obronnych, testów cech, ataków i
szybkości. Wszystkie przechodzą przez wspólną bramkę dostępności, wyposażenia oraz
dostrojenia; UI pokazuje zarówno wartość efektu, jak i jego nieaktywny stan.

Aktywne efekty zawsze pokazują graczowi nazwę, źródło i moment wygaśnięcia. Ten sam
cykl życia obsługuje efekty akcji, czarów, przedmiotów i sceny: mogą kończyć się na
granicy tury lub rundy, po właściwym ataku/ruchu, po utracie koncentracji, odpoczynku,
encounterze albo scenariuszu. Ponowne nałożenie korzysta z jawnej polityki
`replace`, `refresh` albo `stack`; nie wynika z przypadkowego duplikowania wpisów.
Zakończenie scenariusza jest jawną akcją w UI i wygasza wszystkie niepermanentne
efekty dnia. Kolejny reset uruchamia automatyczny long rest.

Przykład:

```text
Opcja: Przejdź górą
Tag: climbing

Item: Lina z hakiem
Bonus tag: climbing
Efekt: advantage albo +2 do testu
```

### Rola LLM W Eksploracji

Eksploracja używa trybu hybrydowego. Content definiuje kilka widocznych kart celu,
ale nie gotowe sposoby wykonania. Po wyborze celu gracze opisują metodę naturalnym
językiem, LLM ją strukturyzuje, a deterministyczny silnik sprawdza zasoby, reguły
metod, koszty i konsekwencje. Wyzwanie grafowe nie pokazuje karty całkowicie
dowolnego planu: swoboda graczy znajduje się w opisie metody po wybraniu
konkretnego rezultatu. Brakujący ważny zamiar powinien dostać czytelny kafelek
celu, a nie ogólną furtkę omijającą graf.

Każda karta celu definiuje politykę wyboru modelu testu. `must` wymusza jeden
model, natomiast `allow` podaje listę modeli dostępnych przed opisaniem metody:

* `single_actor`: gracze wskazują jednego wykonawcę i nie mogą dodać pomocnika;
* `lead_with_help`: wskazują prowadzącego oraz opcjonalnie jednego pomocnika,
  który musi być zdolny do podjęcia próby; pomoc daje jedną przewagę i nie tworzy
  osobnego rzutu;
* `whole_party`: wybór wykonawcy jest wyłączony, rzuca cała drużyna, a klasyczny
  test grupowy udaje się, gdy co najmniej połowa postaci odniesie sukces.

Wybór następuje przed opisaniem metody. Role trafiają do LLM jako kontekst narracji,
ale dozwolony zakres, ostateczny wybór, uczestników i agregację waliduje
deterministycznie silnik.

UI nie pokazuje osobnego technicznego etapu wyboru modelu. Pierwsza kliknięta
postać zostaje prowadzącym (`single_actor`), druga pomocnikiem
(`lead_with_help`), a przycisk „Cała drużyna” wybiera `whole_party`. Przy `must`
niedozwolone warianty po prostu nie są dostępne.

Pierwszy zaimplementowany vertical slice tego modelu to brama w scenariuszu
`Opuszczona strażnica`: zamek i rygiel są osobnymi blokadami, czujność goblinów
rośnie w zakresie 0–3, a badanie lub osłabienie konstrukcji modyfikuje późniejsze
próby. Jawna deklaracja działania po cichu utrudnia test, ale udany test nie
zwiększa czujności.

LLM może działać jako opcjonalna warstwa interpretacji kreatywnych deklaracji graczy.

LLM nie powinien być źródłem zasad ani samodzielnie zmieniać stanu gry.

Rola LLM:

* przeanalizować, czy deklaracja pasuje do świata fantasy, kontekstu sceny i aktywnego wyzwania,
* rozdzielić deklarację na próbę wyzwania, przygotowanie albo połączenie obu,
* przetłumaczyć deklarację gracza na istniejące podejście,
* zaproponować pasującą cechę, skill, ryzyko i tagi,
* wskazać możliwy koszt albo komplikację,
* zwrócić ustrukturyzowaną propozycję do walidacji przez silnik gry albo MG.

Silnik gry nadal waliduje wynik i stosuje tylko znane efekty.

Minimalny kontrakt:

* Pydantic waliduje kształt odpowiedzi LLM.
* Silnik gry waliduje aktualny stan: aktywną strefę, wyzwanie, flagi, zasoby i tagi.
* Wybrany `InteractionGoal` wiąże interpretację z zamierzonym rezultatem, ale sam
  nie dowodzi wykonalności metody i nie przyznaje premii.
* `InteractionGoal.participant_mode` oraz lista dozwolonych modeli są autorskim
  kontraktem. Ostateczny model może wynikać z `must` albo wyboru graczy w `allow`,
  ale nie może zostać podmieniony przez LLM ani ekran późnej akceptacji.
* `InteractionMethodRule` może deterministycznie narzucić autorski kompromis, np.
  `-1` za działanie po cichu wraz z redukcją hałasu.
* LLM nie tworzy liczbowych modyfikatorów sytuacyjnych, przewagi ani utrudnienia.
  Te wartości pochodzą wyłącznie z authored option/method rule, rzeczywiście
  posiadanego zasobu, stanu aktora albo innej deterministycznej reguły runtime.
  Model może opisać mokrą linę lub spróchniałe drewno, ale sam opis nie zmienia rzutu.
* Każda instancja interakcji ma `NarrativeStyle`. Domyślny `heroic_dnd` prowadzi
  bohaterskie power fantasy z lekką ironią i sytuacyjnym humorem.
* Pojedynczy `InteractionGoal` może nadpisać pełny profil narracyjny instancji.
  Pozwala to przejść od karczemnego rozmachu do poważnego wyznania bez zmiany
  mechaniki ani globalnego promptu.
* Poziom humoru lub ironii `none` jest wiążący. LLM nie powinien wtedy dopisywać
  dowcipu do sceny, która ma wybrzmieć serio.
* LLM nie wykonuje efektów gry. LLM strukturyzuje deklarację graczy, a deterministic engine wykonuje tylko znane prymitywy mechaniczne.
* Każde wyzwanie może definiować `llm_policy`: lokalne skille, tagi podejść, komplikacje, dozwolone konsekwencje, zakres ST, zakres postępu, dozwolone typy przygotowania, whitelisty grantowanych zasobów/odblokowywanych opcji i limit zasobów.
* Trudność testów freeform powinna być content-driven: challenge może definiować `dc_policy` z tierami trudności i odpowiadającymi im ST.
* LLM wybiera `difficulty_tier` na podstawie deklaracji graczy i kontekstu przeszkody, a silnik sprawdza, czy `dc` dokładnie odpowiada wartości tieru z contentu.
* `dc_policy` opisuje profil przeszkody, nie listę gotowych rozwiązań. Nie należy definiować ST per predefiniowany sposób pokonania przeszkody, jeśli celem jest kreatywny freeform.
* Jeśli challenge nie ma `llm_policy`, freeform nie powinien dostawać bogatego domyślnego słownika z kodu. Szczegółowy słownik tagów, komplikacji, efektów i whitelist musi pochodzić z contentu scenariusza.
* Ogólne słowniki LLM, np. cechy i skille D&D 5e oraz aliasy pilnowanych zasobów, są trzymane w `content/llm/`.
* Item albo zasób daje efekt tylko wtedy, gdy drużyna go posiada i jego `bonus_tags` pasują do tagów podejścia.
* Deklarowany zasób spoza inventory albo materiałów sceny nie może działać mechanicznie. Analyzer ma go odrzucić albo poprosić o doprecyzowanie, a silnik robi dodatkową walidację faktów.
* Pomoc złożona z jawnych materiałów sceny może działać na dwa sposoby: konstrukcja i natychmiastowe użycie to jednorazowe `improvised_tool_check`, natomiast jawne `/zbuduj` tworzy dynamiczny `TemporaryItem` do późniejszego użycia.
* `/zbuduj` wybiera cel funkcjonalny z polityki craftingu, a deterministyczny silnik dobiera brakujące komponenty według właściwości. Gracz przed akceptacją widzi materiały, sposób ich rozliczenia, czas, zastosowania, efekt, ryzyko i zakres konstrukcji.
* `TemporaryItem` nie jest stałym ekwipunkiem i nie wymaga gotowego szablonu konkretnego przedmiotu. Ma parametry wyliczone z celu funkcjonalnego, jawną liczbę użyć, zakres życia i zapisane komponenty. Starsze template'y pozostają wyłącznie formatem kompatybilności dla historycznego contentu.
* Formalny crafting w downtime jest osobnym flow od `/zbuduj`. Receptura jest
  dostępna tylko w autorskim warsztacie, wymaga biegłości i fizycznie posiadanych
  narzędzi, pobiera połowę wartości rynkowej produktu na materiały i liczy pełne
  ośmiogodzinne dni po 5 gp postępu. Rezultatem jest trwały mundane
  `InventoryItem`, a koszt czasu przesuwa wspólny zegar scenariusza.
* Warunek aktora nie należy wyłącznie do ekranu walki. `ConditionState` nałożony
  przez hazard eksploracyjny przechodzi do encountera, a po nim wraca do
  eksploracji, jeśli jego duration nadal obowiązuje. `until_encounter_end`,
  `until_short_rest`, `until_long_rest`, `until_scenario_end` i `permanent`
  rozstrzygają wspólne eventy lifecycle; UI nie usuwa warunków według lokalnej
  listy wyjątków.
* Freeform `action_flow` obsługuje w MVP: `challenge_attempt`, `preparation` i `combined`.
* Rozmowa jest przypisana do stabilnego identyfikatora instancji interakcji (`challenge`, punkt albo NPC), a nie do samego ekranu. Powrót do tej instancji odtwarza jej transcript bez mieszania rozmów z innymi obiektami.
* Snapshot przechowuje pełny transcript. Do LLM trafia ograniczone okno najnowszych wpisów aktualnej interakcji; starsza historia pozostaje dostępna dla UI i przyszłego mechanizmu podsumowań.
* Aktywna interakcja eksploracyjna jest prezentowana jako osobny, pełnoekranowy czat: opis i opcjonalna ilustracja są pierwszą wiadomością MG, deklaracje graczy są wiadomościami wychodzącymi, a oczekiwanie na LLM ma widoczny wskaźnik pisania.
* Gracze mogą opuścić czat bez kończenia ani kasowania instancji. Wracają wtedy do menu lokacji i punktów, skąd mogą ponownie otworzyć zachowany wątek albo przejść do innego miejsca.
* Przygotowanie może dać krótkotrwały efekt `modifier`, `reduce_negative_effect`, `advantage`, `disadvantage`, `effect_boost`, `grant_resource` albo `unlock_option`, jeśli typ jest dopuszczony przez policy aktywnego challenge.
* `grant_resource` i `unlock_option` mogą dotyczyć tylko istniejących id z contentu i tylko wtedy, gdy id znajduje się w whitelistach `allowed_grant_resource_ids` albo `allowed_unlock_option_ids`.
* Efekt przygotowania działa tylko przy następnej próbie, której tagi pasują do `target_tags`, i po użyciu wygasa.
* Odpowiedź LLM może utworzyć tymczasową opcję challenge, ale rozstrzygnięcie nadal przechodzi przez deterministic engine.
* Interpretacja LLM musi zostać zaakceptowana przed rzutem. Przed akceptacją aplikacja pokazuje kontrakt mechaniczny: test, ST, tier trudności, postęp oraz konsekwencje critical success / success / failure / critical failure.
* Narracja opisująca osiągnięty skutek, reakcję NPC lub ujawniony trop pojawia się
  dopiero po zaakceptowaniu kosztu i rozstrzygnięciu ewentualnego rzutu. Podgląd
  może opisywać wyłącznie zamiar oraz warunki próby.
* Gracz może poprosić o wyjaśnienie interpretacji, odrzucić ją, skorygować albo poprosić o reinterpretację tej samej deklaracji.
* Historia prób challenge jest częścią stanu gry i trafia do dynamicznego kontekstu LLM.
* Lokalny wątek deklaracji przechowuje odrzucone deklaracje, pytania i korekty w ramach aktywnego challenge, żeby odpowiedzi typu "to bez butów" miały kontekst.
  Odrzucony tekst może pozostać w technicznym kontekście ponowienia, ale nie jest
  pokazywany jako zaakceptowana wypowiedź w historii graczy.

Warstwy kontekstu dla LLM:

* prompt analyzer opisuje rolę MG-analityka deklaracji,
* prompt classifier opisuje rolę MG-klasyfikatora mechaniki,
* `content/llm` opisuje ogólne słowniki i konfigurację wspólną,
* scenario context opisuje klimat, dostępne materiały i zakazane założenia scenariusza,
* zone context opisuje lokalne warunki,
* challenge context opisuje sensowne i niemożliwe podejścia do konkretnej przeszkody,
* challenge policy opisuje lokalny słownik mechaniczny konkretnej przeszkody,
* declaration thread opisuje lokalną rozmowę/korekty dotyczące bieżącej przeszkody,
* dynamic state opisuje fakty, które już zaszły w tej sesji.

Po odrzuceniu deklaracji aplikacja powinna dać graczom możliwość wpisania kolejnego podejścia bez resetowania sceny.

### Globalne Intencje I Lokalne Policy

Freeform nie powinien być budowany jako sztywne menu gotowych akcji per obiekt.
Karty pokazują cele rozmowy lub interakcji, nie gotowe wypowiedzi. System nadal ma
globalny katalog intencji, a każdy obiekt, NPC, lokacja albo przeszkoda definiują
lokalne policy.

NPC może dodatkowo definiować `NpcKeyIssue`: ukryty lub jawny priorytet, drażliwy
temat, pokusę, twardą granicę albo wyjątek. Ugruntowane trafienie w taką kwestię
uruchamia wyłącznie autorski efekt. Twardej granicy nie można obejść samym wysokim
rzutem.

Globalny katalog intencji powinien być trzymany w contentcie, np. `content/llm/intent_catalog.json`, a nie zaszyty w promptach lub runtime. Przykładowe intencje:

* `social`,
* `information`,
* `medical`,
* `theft`,
* `harm`,
* `force`,
* `stealth`,
* `crafting`,
* `search`,
* `magic`,
* `trade`,
* `gambling`,
* `movement`.

Każda intencja może mieć globalne, domyślne mapowanie na mechanikę, np.:

```json
{
  "theft": {
    "label": "kradzież albo przeszukanie bez zgody",
    "default_checks": [
      ["dexterity", "sleight_of_hand"],
      ["charisma", "deception"],
      ["intelligence", "investigation"]
    ]
  }
}
```

Lokalny obiekt nie powinien kopiować całej mechaniki globalnej. Powinien raczej określać lokalne granice:

```json
{
  "intent_permissions": {
    "social": {"status": "allowed"},
    "medical": {"status": "allowed"},
    "theft": {"status": "allowed_with_consequence"},
    "harm": {"status": "allowed_with_consequence"},
    "magic": {"status": "blocked"}
  }
}
```

Statusy intencji powinny być enumem, np.:

* `allowed`,
* `allowed_with_consequence`,
* `blocked`,
* `locked`,
* `hidden`.

LLM powinien najpierw sklasyfikować deklarację gracza do globalnej intencji i,
gdy gracz nie dokonał jawnego wyboru, ewentualnej metody, np. `theft` +
`stealth` albo `gambling` + `high_stakes`. W testach społecznych głównego UI
Persuasion, Deception lub Intimidation wybiera gracz. Dopiero potem engine
sprawdza lokalne `intent_permissions`.

### Parametry, Warunki I Efekty

Każdy skutek zmieniający stan gry musi ostatecznie mieć znany typ mechaniczny. Nie oznacza to osobnego kodu dla każdego pomysłu scenariusza. Oznacza to zestaw globalnych prymitywów, z których content scenariusza składa lokalne zachowanie.

Globalny katalog efektów powinien być trzymany w contentcie, np. `content/llm/effect_catalog.json`. Przykładowe typy efektów:

* `set_flag`,
* `grant_resource`,
* `remove_resource`,
* `reveal_information`,
* `start_challenge`,
* `offer_trade`,
* `trigger_encounter`,
* `npc_refuses`,
* `change_relationship`,
* `add_complication`,
* `add_noise`.

Globalny katalog warunków powinien być trzymany w contentcie, np. `content/llm/condition_catalog.json`. Przykładowe typy warunków:

* `flag_equals`,
* `resource_available`,
* `parameter_compare`,
* `relationship_at_least`,
* `challenge_completed`.

Lokalne policy może definiować parametry intencji oraz branch'e:

```json
{
  "intent_permissions": {
    "gambling": {
      "status": "allowed",
      "parameters": {
        "stake_gold": {"type": "integer", "min": 1, "max": 500}
      },
      "branches": [
        {
          "if": {"stake_gold": {"lt": 100}},
          "then": {"type": "start_challenge", "challenge_id": "small_dice_game"}
        },
        {
          "if": {"stake_gold": {"gte": 100}},
          "then": {"type": "offer_trade", "offer_id": "magic_ring_wager"}
        }
      ]
    }
  }
}
```

W tym modelu LLM ekstrahuje parametry z deklaracji, np. `stake_gold: 150`, ale engine egzekwuje limity, warunki i efekty. LLM nie może samodzielnie przyznać złota, dodać itemu, odpalić encountera albo ujawnić informacji, jeśli nie istnieje odpowiedni globalny efekt oraz lokalne policy na to nie pozwala.

Przykład podziału odpowiedzialności:

* gracz: "Stawiam 150 sztuk złota u hazardzisty",
* LLM: `intent=gambling`, `parameters.stake_gold=150`,
* engine: sprawdza lokalne policy hazardzisty,
* engine: wybiera branch `stake_gold >= 100`,
* engine: wykonuje globalny efekt `offer_trade` z `offer_id=magic_ring_wager`.

Nowy kod powinien być potrzebny dopiero wtedy, gdy projekt potrzebuje nowego globalnego prymitywu, np. pełnego sklepu, systemu reputacji, craftingu, mini-gry hazardowej albo kalendarza. Pojedyncze pomysły scenariuszowe powinny być wyrażane przez istniejące prymitywy.

### NPC I Obiekty Interaktywne

NPC, obiekty i lokacje powinny korzystać z tego samego modelu intencji. NPC może mieć dodatkowy kontekst odgrywania postaci, np. osobowość, stan emocjonalny i zablokowane informacje, ale mechaniczny kontrakt powinien nadal opierać się na globalnych intencjach, lokalnym policy i znanych efektach.

Przykład NPC:

```json
{
  "intent_permissions": {
    "social": {"status": "allowed"},
    "medical": {"status": "allowed"},
    "information": {
      "status": "locked",
      "unlock_if_flags": ["scout_stabilized"],
      "reveals": ["tower_hint"]
    },
    "theft": {
      "status": "allowed_with_consequence",
      "limits": {
        "loot_table_id": "wounded_scout_pockets"
      },
      "consequences": {
        "on_success": [{"type": "set_flag", "key": "scout_robbed", "value": true}],
        "on_failure": [{"type": "set_flag", "key": "scout_panicked", "value": true}]
      }
    }
  }
}
```

Przykład przeszkody:

```json
{
  "intent_permissions": {
    "force": {"status": "allowed"},
    "crafting": {"status": "allowed"},
    "search": {"status": "allowed"},
    "social": {"status": "blocked", "reason": "Brama nie jest istotą żywą."}
  }
}
```

Ważna zasada: lokalne policy opisuje granice i konsekwencje sceny, a nie musi przewidywać dokładnej treści deklaracji gracza. Gracz może pisać kreatywnie, LLM klasyfikuje intencję i parametry, a engine waliduje i wykonuje znane efekty.

---

## Ruch Po Planszy

Ruch po planszy powinien być zgodny z zasadami D&D 5e, ale jednocześnie prosty do wizualizacji na planszy LED.

### Podstawowe Założenia

* Jedno pole planszy odpowiada 5 feet.
* Aktor posiada wartość `Speed` wyrażoną w feet.
* Dostępny ruch w turze jest obliczany na podstawie wartości `Speed`.
* Przykład: aktor posiadający `Speed = 30 feet` może poruszyć się maksymalnie o 6 pól normalnego terenu.
* Ruch jest liczony w segmentach po 5 feet.

### Ruch Ortogonalny

Za ruch ortogonalny uznaje się przejście:

* góra,
* dół,
* lewo,
* prawo.

Koszt ruchu:

* 5 feet za wejście na sąsiednie pole.

### Ruch Diagonalny

Na potrzeby pierwszej wersji projektu:

* ruch diagonalny jest dozwolony,
* ruch diagonalny kosztuje 5 feet,
* diagonalne pole sąsiadujące traktowane jest jako oddalone o jedno pole ruchu.

Powód:

* prostsza implementacja,
* prostsza wizualizacja LED,
* płynniejsza rozgrywka na fizycznej planszy,
* zgodność z prostym wariantem gry na siatce w D&D 5e.

W przyszłości koszt ruchu diagonalnego może zostać rozszerzony do wariantu alternatywnego, na przykład:

* pierwsza diagonala kosztuje 5 feet,
* druga diagonala kosztuje 10 feet,
* wzór 5/10 powtarza się dalej.

Ten wariant nie jest częścią MVP.

### Zakaz Przechodzenia Przez Rogi

Aktor nie może wykonać ruchu diagonalnego przez róg, jeżeli róg jest zablokowany przez:

* ścianę,
* duży obiekt terenowy,
* blokującą przeszkodę,
* inne pole całkowicie blokujące przejście.

Przykład:

* jeżeli aktor chce przejść diagonalnie między dwoma polami, a oba przyległe ortogonalnie pola są zablokowane, ruch diagonalny jest niedozwolony.

Ta zasada zapobiega przenikaniu przez narożniki ścian i przeszkód.

### Trudny Teren

Trudny teren jest wspierany od pierwszej wersji.

Koszt wejścia na pole trudnego terenu:

* 10 feet.

Przykłady trudnego terenu:

* gruz,
* błoto,
* gęsta roślinność,
* śnieg,
* płytka woda,
* niskie meble,
* nierówne schody.

Jeżeli pole zawiera kilka źródeł trudnego terenu, koszt nie powinien być wielokrotnie zwiększany.

Na potrzeby MVP trudny teren po prostu podwaja koszt wejścia na pole.

### Przeszkody

Przeszkody mogą posiadać różne właściwości.

#### Ściany

Ściana blokuje przejście pomiędzy dwoma polami.

Aktor nie może:

* przejść przez ścianę,
* zakończyć ruchu za ścianą bez istniejącego przejścia,
* przejść diagonalnie przez róg ściany.

#### Drzwi

Drzwi mogą być:

* otwarte,
* zamknięte.

Otwarte drzwi nie blokują ruchu.

Zamknięte drzwi blokują ruch.

Interakcja z drzwiami powinna zostać zaimplementowana jako osobna mechanika akcji albo interakcji z obiektem.

#### Blokujące Przeszkody

Przykłady:

* głazy,
* kolumny,
* ciężkie meble,
* obiekty scenografii,
* barykady.

Blokują wejście na zajmowane pole.

### Inni Aktorzy

#### Sojusznicy

Aktor może przechodzić przez pole zajmowane przez sojusznika.

Pole zajmowane przez sojusznika traktowane jest jako trudny teren.

Aktor nie może zakończyć ruchu na polu zajmowanym przez sojusznika.

#### Przeciwnicy

Na potrzeby MVP:

* aktor nie może przechodzić przez pole zajmowane przez przeciwnika,
* aktor nie może zakończyć ruchu na polu zajmowanym przez przeciwnika.

Kategorie rozmiaru istnieją już w modelu, ale wyjątki dotyczące przechodzenia przez
pola mniejszych i większych istot pozostają odłożone do etapu geometrii rozmiarów.

#### Neutralni Aktorzy

Neutralni aktorzy powinni być traktowani jak sojusznicy, chyba że konkretna mechanika spotkania określi inaczej.

### Zakończenie Ruchu

Ruch może zostać zakończony wyłącznie na polu:

* znajdującym się w zasięgu ruchu,
* niezajętym przez innego aktora,
* niebędącym blokującą przeszkodą,
* dostępnym zgodnie z zasadami ruchu,
* znajdującym się w granicach planszy.

Aktor nigdy nie może dobrowolnie zakończyć ruchu na polu zajmowanym przez inną istotę.

### Obliczanie Zasięgu Ruchu

System powinien wyznaczać wszystkie osiągalne pola na podstawie:

* aktualnej pozycji,
* dostępnego ruchu,
* kosztów terenu,
* przeszkód,
* ścian,
* drzwi,
* obecności innych aktorów,
* zakazu przechodzenia przez zablokowane rogi,
* granic planszy.

Algorytm powinien być deterministyczny i niezależny od sprzętu.

Rekomendowany kierunek implementacji:

* użyć algorytmu podobnego do Dijkstra albo BFS z kosztami,
* traktować każde pole jako węzeł grafu,
* koszt wejścia na pole zależy od typu terenu i obecności aktora,
* wynik powinien zawierać zarówno osiągalne pola, jak i możliwe ścieżki.

### Wizualizacja LED Ruchu

Podczas tury aktywnego aktora plansza LED powinna wyświetlać:

* aktualną pozycję aktora,
* wszystkie osiągalne pola ruchu,
* aktualnie wybraną ścieżkę ruchu,
* pole docelowe.

System LED powinien obsługiwać jednocześnie:

* wizualizację pełnego zasięgu ruchu,
* wizualizację wybranej ścieżki.

Silnik zasad nie powinien generować kolorów ani animacji.

Silnik zasad powinien zwrócić dane logiczne, na przykład:

* `reachable_tiles`
* `selected_path`
* `origin`
* `destination`
* `movement_cost`

Warstwa LED odpowiada za zamianę tych danych na konkretne kolory, efekty i ramki animacji.

### Wymagania Implementacyjne Dla Ruchu

* Pathfinding musi być niezależny od sprzętu.
* Pathfinding musi być pokryty testami jednostkowymi.
* Silnik zasad nie może bezpośrednio sterować LED-ami.
* Silnik zasad zwraca dane opisujące możliwe pola ruchu oraz ścieżkę.
* Warstwa LED odpowiada wyłącznie za wizualizację otrzymanych danych.
* Ruch musi być możliwy do przetestowania bez Arduino, Raspberry Pi i fizycznych LED-ów.

---

## Struktura Tury

Walka używa kolejności inicjatywy.

Każda tura aktora zawiera:

* ruch,
* akcję,
* opcjonalną akcję dodatkową,
* opcjonalne śledzenie reakcji.

### Ataki dystansowe i osłona

Źródło ataku rozdziela rodzaj ataku od jego odległości. Ataki wręcz deklarują
`attack_kind: melee` i `reach_feet` (domyślnie 5 feet w contentcie), natomiast
ataki dystansowe deklarują `attack_kind: ranged` oraz `range_feet`. Legalne cele,
podświetlenie planszy i podgląd akcji korzystają z tej samej wartości efektywnej.

Na fizycznej planszy efekty dystansowe mają maksymalny zasięg 75 feet (15 pól),
nawet jeżeli źródło D&D deklaruje większy zasięg normalny lub daleki. Jest to
świadome skalowanie do pola gry 20×30: ten sam limit obowiązuje legalne cele,
podświetlenie LED i rozstrzygnięcie ataku. Zasięg wręcz pozostaje bez zmian.

Reach wyznacza również strefę zagrożenia: dobrowolne opuszczenie jej może uruchomić
atak okazyjny, ale przesunięcie między polami nadal znajdującymi się w reach nie.
Krótki atak dystansowy nigdy nie tworzy takiej strefy. AI z atakiem o wydłużonym
reach zatrzymuje ruch, gdy osiągnie pierwsze legalne pole ataku. Shove i Grapple
pozostają osobnymi manewrami wymagającymi odległości 5 feet.

Atak dystansowy ma utrudnienie, jeżeli żywy przeciwnik znajduje się nie dalej niż
5 feet od atakującego i ma do niego linię widzenia. Przewaga i utrudnienie nadal
znoszą się zgodnie ze zwykłym kontraktem rzutu d20.

Dla rzutów ataku linia pocisku może zapewniać celowi half cover (`+2 AC`) albo
three-quarters cover (`+5 AC`). Żywa postać na polu pośrednim zapewnia half cover,
a obiekty sceny deklarują osłonę przez `projectile_cover_bonus`. Osłony nie sumują
się: obowiązuje najwyższa wartość. Całkowicie zablokowana linia widzenia oznacza
total cover i wyklucza cel. Preview ataku pokazuje rodzaj i źródło osłony,
efektywne AC oraz ewentualne utrudnienie za zwarcie.

Osłona działa także dla rzutów obronnych na Zręczność przeciw czarom: half cover
daje `+2`, a three-quarters cover `+5`. UI pokazuje premię przed potwierdzeniem oraz
jako osobny składnik wyniku save'a. Dla obszaru liczymy ją od środka `radius` albo
od rzucającego dla `line` i `cone`; pełna przeszkoda wyklucza cel z efektu.

### Czary obszarowe

Gracz wskazuje środek `radius` albo jedno z ośmiu sąsiednich pól wyznaczających
kierunek `line` lub `cone`. Linia wykorzystuje długość i szerokość z contentu;
stożek rośnie warstwami 1, 2, 3... pól. Wszystkie pola są widoczne na planszy
przed potwierdzeniem.

W turze bohatera lista działań ma jawne etapy `list` i `preview`. Ruch jest wyborem
startowym, a Numpad 8/2 przełącza kolejno ataki bronią, zdolności specjalne,
czary, `Zmianę broni`, `Użyj przedmiotu`, akcje kontekstowe i zakończenie tury.
Poruszanie się po liście nie uruchamia skanowania planszy ani podświetlenia
zasięgu. Pierwszy Enter uzbraja podgląd wybranej akcji i dopiero wtedy pokazuje
legalne pola lub cele. Kliknięcie planszy wybiera albo zmienia pole/cel, ale nie
wykonuje akcji. Następny Enter zatwierdza bieżący podgląd; minus wraca do listy
bez zużycia akcji, slotu, przedmiotu ani zasobu klasowego. `Zakończ turę` używa
tego samego podwójnego potwierdzenia i nie ma osobnego skrótu Numpad 0.

Akcja bez legalnego celu nie przechodzi do `preview`: UI podaje przyczynę i
pozostaje na liście, dzięki czemu plansza nie oczekuje bezskutecznego kliknięcia.
Dla czaru obszarowego legalne środki pozostają lekko podświetlone, gdy wybrany
środek pokazuje właściwy obszar i objęte cele. Kolejne kliknięcia zmieniają
środek bez wydawania zasobu, a Enter zatwierdza bieżący podgląd. Wieloetapowe
zdolności zachowują tę zasadę na każdym etapie wymagającym wyboru planszy.

Obszar nie przechodzi przez ściany, zamknięte krawędzie ani blocking terrain.
Content jawnie wybiera `target_mode`: wszystkie istoty, przeciwników albo
sojuszników. Wariant `all_creatures` oznacza friendly fire. UI pokazuje objętych
sojuszników i rzucającego jako ostrzeżenie, zanim zostanie zużyta akcja oraz slot.

Geometria jest deterministyczną interpretacją jednopolowej siatki. Dokładne bryły
3D, wysokość oraz alternatywne sposoby rozstrzygania pól dotkniętych na krawędzi
pozostają poza zakresem board MVP.

### Flankowanie

Opcjonalna reguła flankowania z D&D 5e 2014 jest domyślnie włączona. Atak wręcz
otrzymuje przewagę, jeśli atakujący stoi na polu sąsiadującym z celem, a żywy
sojusznik zdolny do walki zajmuje dokładnie przeciwległe pole lub róg i widzi cel.
Flankowanie nie działa dla ataków dystansowych, save-spelli ani efektów obszarowych.

Preview ataku jawnie pokazuje `Flankowanie: tak — przewaga` oraz id sojuszników,
którzy spełniają geometrię. Przewaga i utrudnienie znoszą się przez standardowy
kontrakt `RollMode`. Czysty evaluator dopuszcza wyłączenie reguły parametrem, ale
runtime gry korzysta z wartości domyślnej `flanking_enabled=True`.

### Hide, Search i wykrywanie

Walka używa modelu D&D 5e 2014. Hide jest akcją i wymaga, aby żaden przeciwnik nie
widział postaci wyraźnie. Na deterministycznej planszy spełnia to zablokowana linia
widzenia albo three-quarters/total cover; half cover nie wystarcza. Wynik Dexterity
(Stealth) jest porównywany osobno z passive Perception każdego przeciwnika, dlatego
postać może być ukryta przed częścią encountera, ale wykryta przez pozostałych.

Search jest akcją Wisdom (Perception) przeciw zapisanemu wynikowi Stealth i ujawnia
cel wyłącznie szukającemu. Ruch na pole widoczne dla danego obserwatora kończy tę
relację ukrycia. Atak z ukrycia ma przewagę, po czym atakujący ujawnia się wszystkim.
AI bez widocznego celu używa Search i nie może korzystać z pozycji figurki jako
wiedzy postaci.

Jeżeli rozstrzygnięcie eksploracji potwierdzi ciche, niezauważone podejście drużyny,
po setupie i przed inicjatywą pojawia się opcjonalny etap skradania. Każdy przytomny
bohater może wykonać jedną próbę albo ją pominąć. Relacje ukrycia uzyskane przeciw
poszczególnym obserwatorom przechodzą bezpośrednio do pierwszej rundy walki.

Fizyczna plansza nie obsługuje jeszcze oficjalnej możliwości zgadywania pozycji
ukrytego celu i atakowania wskazanego pola z utrudnieniem. Do czasu osobnego modelu
wiedzy o ostatniej znanej pozycji ukryty aktor nie jest legalnym celem ani celem LED.

### Warunki walki i prone

Trwałe warunki mechaniczne aktywnej walki są przechowywane w osobnym
`ConditionState` przypisanym do aktora i zapisywanym w snapshocie. Pierwszym
obsługiwanym warunkiem jest D&D 5e 2014 `Prone/Powalony`.

Padnięcie jest darmowym wyborem z menu własnego pola. Wstanie nie zużywa akcji,
ale wymaga i zużywa połowę bazowej szybkości aktora. Powalony aktor może poruszać
się tylko przez czołganie: każdy odcinek kosztuje dwukrotnie, a difficult terrain
dodaje swój koszt osobno. UI pokazuje stan oraz rzeczywisty pozostały budżet ruchu.

Powalony atakujący ma utrudnienie do ataku. Atak przeciw powalonemu celowi z 5 feet
ma przewagę, a z większej odległości utrudnienie. Modyfikatory przechodzą przez
wspólny kontrakt advantage/disadvantage i są widoczne w podglądzie rzutu. AI przed
planowaniem ruchu próbuje wstać i płaci ten sam koszt co gracz.

Silnik musi wspierać przyszłe rozszerzenia dla:

* ataków okazyjnych,
* przygotowanych akcji,
* kolejnych rodzin reakcji,
* koncentracji.

Reakcja obronna po trafieniu zatrzymuje atak przed zastosowaniem obrażeń. `Tarcza`
zużywa reakcję i slot 1. poziomu, podnosi AC o 5, ponownie ocenia ten sam rzut ataku
i utrzymuje premię do początku następnej tury chronionego aktora. Trafienie krytyczne
nie otwiera tego promptu, ponieważ premia do AC nie może zmienić jego wyniku.

`Kontrczar` otwiera wspólne okno reakcji przed zatwierdzeniem widzianego wrogiego
czaru w zasięgu 60 stóp. Zużywa reakcję i jawnie wybrany slot: automatycznie
przerywa czar na nie wyższym poziomie, a przeciw silniejszemu wymaga fizycznego
testu d20 cechy rzucania czarów przeciw ST `10 + poziom wrogiego czaru`. Sukces
usuwa skutki oczekującego czaru, zachowując zużytą akcję i wykonany ruch wroga.

Czar o czasie rzucania dłuższym niż jedna akcja zapisuje jawny postęp: minuta to
10 akcji, 10 minut to 100, a godzina 600. Rzucający musi poświęcić akcję w każdej
swojej turze i przez cały proces utrzymuje koncentrację. Obrażenia uruchamiają
zwykły CON save; porażka, utrata przytomności, dobrowolne anulowanie albo
zakończenie tury bez wymaganej akcji przerywa czar. Zwykły ruch nie przerywa
rzucania. Slot oraz zużywane komponenty są pobierane dopiero przy ukończeniu.
`Rytuał ochronny` jest referencyjnym, data-driven fixture tego przepływu.

---

## Projekt LED

LED-y zapewniają szybką informację taktyczną na stole.

Obsługiwane wizualizacje:

* aktywny aktor,
* zasięg ruchu,
* wybrana ścieżka,
* cele ataku,
* efekty obszarowe,
* informacja o trafieniu,
* informacja o obrażeniach,
* informacja o leczeniu,
* znaczniki przygotowania spotkania.

Efekty LED muszą być generowane jako niemutowalne dane ramek.

Adaptery sprzętowe odpowiadają za odtwarzanie tych ramek.

Silnik zasad nie może wiedzieć:

* jaki typ taśmy LED jest używany,
* ile LED-ów znajduje się na planszy,
* jaki protokół komunikacyjny jest używany,
* jaka jest częstotliwość odświeżania.

---

## Zapis Danych

Dane spotkania powinny być serializowalne.

Preferowany format:

* JSON

Przyszły zapis powinien obejmować:

* spotkania,
* stan walki,
* aktorów,
* stan planszy,
* historię rzutów,
* podsumowanie starcia.

---

## Wymagania Testowe

Każda mechanika rozgrywki wymaga testów jednostkowych.

Wymagane pokrycie testami:

* kolejność inicjatywy,
* zasięg ruchu,
* pathfinding,
* rozstrzyganie ataku,
* obliczanie obrażeń,
* rzuty obronne,
* przewaga i utrudnienie,
* ręczne wpisywanie wyników rzutów,
* rozróżnianie naturalnego wyniku i wyniku końcowego.

Adaptery sprzętowe nie wymagają testów jednostkowych w MVP.

---

## Zagrożenia Eksploracyjne

Niebezpieczne podejście eksploracyjne może uruchomić hazard z osobnym fizycznym
saving throwem. Wynik save'a wybiera skutki sukcesu albo porażki; skutkami mogą być
obrażenia, hałas, komplikacja, flaga sceny, przesunięcie drużyny lub stan postaci.
Stan aktora nie jest wyłącznie narracją: pozostaje jawny, jest zapisywany i przechodzi
do encountera. `Prone` można usunąć bez kosztu poza inicjatywą przez zwykłe wstanie,
natomiast po rozpoczęciu walki obowiązują zasady ruchu D&D 5e 2014.

Pułapki są osobnymi, początkowo ukrytymi elementami contentu. Wykrycie nie może
wynikać wyłącznie z narracyjnego domysłu LLM: wymaga ustrukturyzowanej obserwacji i
efektu `reveal_trap`. Po ujawnieniu gracz widzi dozwolone działania oraz warunki
rzutu. Aktywacja deleguje konsekwencje do ogólnego silnika hazardów.

## Przywołania na fizycznej planszy

- Przywołanie wybiera jedno wolne, nieblokujące i widoczne pole w zasięgu czaru.
  Pole można wskazać skanem planszy albo tym samym wyborem w UI.
- Przywołana istota jest pełnym dynamicznym aktorem tej samej frakcji co
  przywołujący. Działa bezpośrednio po właścicielu, współdzieląc jego wynik
  inicjatywy, ale ma własny ruch, HP, KP i źródło ataku.
- Pierwszy pionowy zakres obsługuje jedną istotę na jedno rzucenie. Rozpoczęcie
  innej koncentracji usuwa przywołanie atomowo; utrata koncentracji, pokonanie
  rzucającego, spadek przywołanej istoty do 0 HP lub zastąpienie efektu usuwa
  aktora także z inicjatywy.
- Statblock referencyjnego ducha jest contentem `project_original`, a nie próbą
  odwzorowania konkretnego chronionego czaru. Mechanika pozostaje generyczna.

## Magiczny ruch na fizycznej planszy

- Teleport wskazuje wolne, widoczne pole w deklarowanym zasięgu. Nie wymaga
  ścieżki, nie zużywa szybkości i nie wywołuje ataków okazyjnych.
- Push i pull wybierają widocznego przeciwnika w zasięgu. Po nieudanym save cel
  porusza się po prostej względem rzucającego, maksymalnie o zadany dystans.
- Wymuszony ruch kończy się na ostatnim legalnym polu przed ścianą, zamkniętą
  krawędzią, blokującym obiektem albo żywym aktorem. Nie omija przeszkody przez
  skrócenie deklarowanego dystansu i nie wydaje ruchu celu.
- Pierwszy zakres nie obsługuje teleportowania innego sojusznika, zamiany miejsc
  ani wyboru dowolnego kierunku push/pull niezależnego od rzucającego.

## Osłabienia czarami

- Czar osłabiający wybiera jednego widocznego przeciwnika w zasięgu przez UI
  albo skan planszy. Akcja i slot są zużywane dopiero po potwierdzeniu celu.
- Przeciwnik wykonuje pierwszy save automatycznie. Porażka nakłada zwykły
  `ConditionState`, dzięki czemu Poisoned, Restrained i kolejne stany korzystają
  z tych samych modyfikatorów, prezentacji, zapisu oraz lifecycle co inne źródła.
- Powtarzany save odbywa się w zadanym przez content momencie tury. Sukces usuwa
  stan. Pierwsze fixtures są `project_original`, trwają do udanego save'a lub
  rozproszenia i celowo nie wymagają koncentracji.
- Ten pionowy zakres obsługuje czary sojusznika przeciw przeciwnikom; fizyczne
  save'y bohaterów na efekty wrogów nadal przechodzą przez istniejący przepływ.

## Przejście między scenariuszami

- Continuation deklaruje jeden autorski, stały czas przejścia do kolejnej sceny.
- Panel pokazuje cel i czas, a pojedynczy przycisk `Wyrusz` zatwierdza przejście.
  Gracze nie wybierają tempa ani nawigatora i nie wykonują osobnych rzutów podróży.
- Po przesunięciu zegara continuation wybiera pierwszą pasującą autorską gałąź
  `success`, `partial_success` albo `fail_forward` na podstawie końcowych flag.
  Gałąź przekazuje nazwany rezultat graczom oraz typowane konsekwencje przyszłej
  scenie.
- Handoff zawiera rozstrzygnięcie celów sceny źródłowej. Wybrane flagi mogą być
  propagowane jawnie; runtime nie kopiuje całego prywatnego stanu scenariusza.
- Exhaustion 1–6 nakłada kolejno: disadvantage na ability checks, połowę
  szybkości, disadvantage na ataki i save'y, połowę maksimum HP, szybkość 0
  oraz śmierć. Long rest usuwa jeden poziom.

## Broń i czary przeciw obiektom w wyzwaniach eksploracyjnych

- Gdy gracz wybiera authored cel eksploracyjny, taki jak sforsowanie bramy,
  broń, narzędzie lub czar jest źródłem możliwości dla testu tego celu. Nie
  uruchamia automatycznie bojowego attack roll przeciw AC ani odejmowania HP
  fixture.
- Jest to jawne uproszczenie dla tempa gry przy stole: authored flow określa
  cechę, ST, postęp, hałas i konsekwencje, a tagi wybranego źródła określają,
  czy metoda jest legalna. Przykładowo Fire Bolt użyty do sforsowania bramy
  może prowadzić do testu cechy czarującej zamiast serii ataków i rzutów
  obrażeń przeciw drewnu.
- Jeżeli scena udostępnia bezpośrednią operację na destrukcyjnym fixture poza
  wyzwaniem, stosuje jego AC, HP, typ obrażeń i zwykłe zasady ataku. Content
  musi wybrać jeden z tych kontraktów i nie może mieszać ich w ramach tej samej
  nierozstrzygniętej deklaracji.
- UI zawsze informuje, że źródło wybrane dla celu eksploracyjnego wspiera test
  wyzwania. Wybrany przedmiot/czar, jego właściciel i koszt są autorytatywne;
  LLM opisuje metodę, ale nie może podmienić źródła.

## Rozpraszanie magii

- Czar rozpraszający wskazuje jedną widoczną istotę z aktywnym efektem czaru.
  Może to być sojusznik, przeciwnik albo dynamicznie przywołana istota.
- Runtime grupuje efekty według celu, źródłowego rzucającego, stabilnego ID czaru
  i poziomu rzeczywiście użytego slotu. Nie rozpoznaje magii po polskiej nazwie.
- Każdy efekt czaru o poziomie nie wyższym niż slot rozproszenia kończy się
  automatycznie. Każdy silniejszy wymaga osobnego fizycznego testu d20 cechy
  rzucania czarów przeciw ST `10 + poziom efektu`, bez proficiency.
- Rozproszenie usuwa tylko elementy pochodzące z czarów. Warunki z trucizny,
  manewru, przedmiotu lub sceny pozostają. Usunięcie koncentracyjnego efektu
  przywołania usuwa również dynamicznego aktora z planszy i inicjatywy.
- Pierwszy zakres działa w aktywnej walce i celuje w istoty. Rozpraszanie
  samodzielnych efektów obszarowych, obiektów oraz magii eksploracyjnej pozostaje
  do przyszłego wspólnego modelu takich celów.

## Planszowa nawigacja eksploracji i budżet instancji

- Karty akcji eksploracyjnych pozostają w katalogu jako wyłączone dziedzictwo,
  ale nie trafiają do aktualnych zestawów siedmiu bohaterów i runtime nie
  wykonuje ich podczas eksploracji. Zdolności postaci pojawiają się jako
  authored kafelki zależne od składu drużyny. Drukowane karty aktywne są bojowe.
- `ACCEPT` i `DECLINE` rozstrzygają właściwe decyzje, reakcje i przygotowanie
  czarów. Nie służą do wybierania lokacji, kończenia rozmowy ani opuszczania
  instancji.
- Pierwsze wskazanie znacznika lokacji pokazuje jej podgląd. Powtórne wskazanie
  tej samej lokacji potwierdza wejście. Wskazanie innego znacznika przełącza
  podgląd, a wszystkie znaczniki pozostają podświetlone. Zablokowana lokacja może
  pokazać podgląd, lecz nie przyjmuje potwierdzenia.
- Wyjście z lokacji pokazuje wszystkie odblokowane lokacje należące do tej
  samej sceny. Graf sąsiedztwa pozostaje danymi świata, ale nie ogranicza menu
  lokalnych instancji sceny.
- Wybór kafelka nigdy sam nie wykonuje automatycznego celu NPC ani działania bez
  opisu. Najpierw pokazuje podgląd, a wykonanie wymaga przycisku, Entera albo
  `ACCEPT`. Kafelek z przypisanym bohaterem ma stałego wykonawcę i nie uruchamia
  ani nie przyjmuje dodatkowego wyboru karty bohatera.
- Jednoczesne pola interakcji używają barw rozróżnialnych na fizycznych LED-ach;
  biały zastępuje różowy w zestawie, w którym występuje już fioletowy.
  Konkretna akcja zachowuje ten sam numer, pole i kolor przez cały czas życia
  instancji. Zniknięcie ukończonej akcji pozostawia pusty slot i nie przesuwa
  pozostałych kafelków.
- Ekranowe potwierdzenie wyniku może korzystać wyłącznie z wiadomości dodanych
  przez aktualnie rozstrzygany rzut. Nie wolno ponownie wyświetlić starszego
  wyniku NPC znalezionego w historii rozmowy.
- Instancja wykorzystuje najwyżej osiem authored pozycji interakcji. Ostatnia
  pozycja jest zawsze zarezerwowana na czerwone systemowe wyjście; pozostaje więc
  najwyżej siedem jednoczesnych działań. Runtime odrzuca przepełnienie zamiast
  ukrywać albo stronicować działania.
- Systemowe wyjście cofa o jeden poziom: rozmowa/obiekt → działania lokacji,
  działania lokacji → wybór lokacji. Nierozliczony rzut, decyzja, reakcja NPC,
  encounter albo setup blokuje wyjście bez cofania wykonanych kosztów i efektów.

## Budżet decyzji startowych archetypów

- Podstawowy atak bronią nadal wybiera się przez planszę i nie ma osobnej karty.
- Każdy z siedmiu startowych archetypów ma kilka aktywnych decyzji bojowych;
  wyrównujemy liczbę znaczących wyborów, a nie dosłowną liczbę kart czarów.
- Bohaterowie startują na poziomie 3, dostają autorską premię `+2` do głównego
  atrybutu i od pierwszej sceny mają dostęp do pełnej osobistej talii. System
  awansu oraz odblokowywania kart jest odłożony do osobnego projektu.
- Wielkość pełnej talii zależy od roli bohatera. Wyrównujemy liczbę znaczących
  wyborów, ale nie ścinamy technicznych wariantów tylko po to, by każda postać
  miała identyczną liczbę kart.
- Zdolności przeniesione z innych klas są przedstawiane jako osobiste techniki
  archetypu. Wykorzystują istniejące resolvery, lecz mają własne nazwy i pule.
- Pozycja obronna Garrana kosztuje cały niewykorzystany ruch, nie ma limitu i
  daje `+2 KP` do początku następnej tury albo do zmiany pola. Unik instynktowny
  Miry jest proponowaną przed rzutem reakcją, która kosztuje 1 Fortel.
- Mira zaczyna z liczbą Forteli równą modyfikatorowi Zręczności (obecnie 4),
  Erynd z 4 Instynktami, a Garran z liczbą Taktyk
  równą modyfikatorowi Siły (obecnie 4). Brakka zaczyna każdy Szał z 3 punktami
  Dzikości; Taktyki, Fortele i Instynkt wracają po długim odpoczynku.
- Nimra zaczyna z komórkami 2. poziomu i od razu może używać wszystkich swoich
  piętnastu czarów i pięciu wariantów Metamagii.

### Lorian — bard-wynalazca

- `Kusznik` daje dwa niezależne ataki kuszą ręczną w zwykłej akcji Ataku.
- Specjalne ostrzały nie mają puli użyć. `Luneta optyczna` wymaga pozostania w
  miejscu, zużywa cały ruch, wydłuża zasięg o 15 stóp, obniża efektywne KP celu
  o 2 i kieruje oba strzały w ten sam cel.
- `Ostrzał destabilizujący` zakłóca pierwszy atak i obrony na Mądrość, a
  `Prowokujący ostrzał` skaluje premię przeciw Lorianowi i karę przeciw innym
  celom z faktycznie zadanymi obrażeniami.
- `Oplatający ostrzał` wybiera środek obszaru 3×3 w zasięgu 45 stóp. Wszystkie
  istoty w obszarze, również sojusznicy, bronią się Zręcznością; sukces daje
  połowę ruchu, a porażka blokuje ruch do początku następnej tury Loriana.
- Zdolności specjalne wymagają żywego i przytomnego sojusznika w promieniu
  10 stóp. Ograniczenie nie dotyczy zwykłych ataków ani czarów.
- `Obycie i targowanie` daje +2 do każdego pozabojowego testu Charyzmy.
  `Improwizacja` pozwala raz na konkretnego NPC przerzucić nieudany taki test;
  drugi wynik jest ostateczny, a zużycie pozostaje w zapisie sesji.
- Inspiracja ma liczbę użyć równą modyfikatorowi Charyzmy i odnawia się po
  krótkim odpoczynku. Pozostałe specjalne akcje i reakcje nie wydają Inspiracji.

### Garran — wieża i koordynator linii

- `Zryw akcji` jest dostępny dopiero po wydaniu akcji głównej, kosztuje akcję
  dodatkową, przywraca akcję główną i ma jedno użycie na krótki odpoczynek.
- `Uderzenie tarczą` od 2026-09-07 kosztuje akcję dodatkową i nie zużywa ruchu.
  Wygrany sporny test Siły zadaje `1k6 + modyfikator Siły` obuchowych;
  cel jest odpychany dokładnie o jedno przeciwległe pole, jeżeli jest legalne.
  Zablokowane pole nie anuluje obrażeń, a remis wygrywa obrońca.
- Garran ma cztery Taktyki po 1 punkcie: `Rozkaz: Stać` ogranicza najbliższy
  ruch celu po obronie Mądrości ST 14, `Osłona tarczą` dynamicznie daje `+2 KP`
  sąsiadującym sojusznikom, `Mowa dowódcy` zdejmuje Strach ze słyszących
  sojuszników i wzmacnia ich pierwszy test k20, a `Osłona towarzysza`
  przekierowuje na Garrana pierwszy pojedynczy wrogi atak, czar albo efekt.
- `Wyrzuty sumienia` śledzą nieodwracalną przez leczenie sumę utraconych PW w
  bieżącej walce. Gdy Garran jest w grupie bohaterów z najmniejszą liczbą ran i
  przynajmniej jeden sojusznik otrzymał więcej, Garran ma `−2` do ataków,
  rzutów obronnych i testów; kara nie dotyczy KP, obrażeń ani leczenia.
- Warta, Stopień wojskowy, Ratunek polowy oraz czaropodobne wersje dawnych
  Taktyk nie należą już do archetypu Garrana.

### Dagna — mobilne wsparcie pola walki

- `Błogosławieństwo` jest autorską aurą koncentracji o promieniu 10 stóp przez
  5 rund. Dagna i sojusznicy aktualnie znajdujący się w aurze dodają fizyczne
  `k4` do każdego ataku i rzutu obronnego; premia pojawia się i znika wraz ze
  zmianą pozycji.
- `Aura Boskiej Opieki` jest czarem 1. poziomu, koncentracją przez 5 rund i ma
  promień 5 stóp. Wrogie ataki wykonywane z aury otrzymują karę do testu ataku
  i obrażeń równą połowie modyfikatora Mądrości Dagny, zaokrągloną w dół,
  minimum 1. Efekt nie obniża obrażeń czarów opartych wyłącznie na rzucie
  obronnym.
- `Aura Uzdrawiającej Łaski` jest czarem 2. poziomu, koncentracją przez 3 rundy
  i ma promień 10 stóp. Faktyczne leczenie sojusznika z dowolnego bojowego
  źródła automatycznie otrzymuje `1k8 + Mądrość Dagny`; aura ma liczbę
  aktywacji równą jej modyfikatorowi Mądrości, minimum 1. Premia nie uruchamia
  się od temporary HP, stabilizacji ani zwiększenia maksymalnych PW i nie
  wywołuje samej siebie.
- `Krok ratowniczki` raz na turę Dagny proponuje opcjonalny ruch 5 stóp po
  faktycznym uleczeniu innego sojusznika w promieniu 10 stóp albo zdjęciu z
  niego negatywnego stanu. Ruch nie zużywa szybkości ani reakcji i nie prowokuje
  ataków okazyjnych; brak legalnego pola pomija prompt.
- Zasięgi aur są komunikowane przede wszystkim statusami figur. Gracz może
  chwilowo włączyć LED-owy podgląd konkretnej aury, ale wybór akcji natychmiast
  przywraca podgląd ruchu, celu lub obszaru tej akcji.

### Erynd — mobilny łucznik kontroli pola

- Premia Łucznictwa pozostaje uwzględniona po ponownym związaniu broni z
  aktorem: obecnie długi łuk ma +8 do ataku. Autorski nóż jest bronią, w której
  Erynd ma biegłość; atakuje z Siły z premią +3. Mira analogicznie ma biegłość
  w autorskich nożach do rzucania (+6 ze Zręczności).

- Erynd walczy długim łukiem w ćwiekowanej skórze bez kary do Skradania; jego
  awaryjny nóż myśliwski zadaje `1k4 + Siła`. Dawne dwa miecze, Dobre jagody,
  Wykrycie pułapek, Tropienie, Naturalny odkrywca i Ulubiony wróg nie należą do
  jego aktywnego zestawu.
- Instynkt ma maksimum równe modyfikatorowi Zręczności (obecnie 4) i odnawia się
  po długim odpoczynku. `Celowanie` zużywa cały niewykorzystany ruch przed
  ruszeniem się i daje przewagę wyłącznie następnemu atakowi z długiego łuku w
  tej turze.
- `Pierwsza krew` raz na turę dodaje `1k8` do trafienia długim łukiem w cel,
  który przed obrażeniami miał pełne PW. `Czujność zwiadowcy` daje `+2` do
  inicjatywy oraz wykrywania ukrytych przeciwników, ale nie pułapek.
- `Strzała kotwicząca` kosztuje 1 Instynkt; gracz rzuca `k4` i wpisuje liczbę
  rund. Trafiony cel broni się Siłą przeciw `ST 8 + biegłość + Zręczność`:
  porażka zeruje ruch, sukces zmniejsza go o połowę na podany czas.
- `Strzała odsłaniająca` kosztuje 1 Instynkt; gracz rzuca `k8`, a trafienie
  obniża KP celu o wynik do początku następnej tury Erynda. `Strzała
  zakłócająca` kosztuje 1 Instynkt, odbiera reakcje do końca następnej tury celu
  i daje utrudnienie do jego następnego ataku, nie dłużej niż do końca tej tury.
- `Podwójny strzał` kosztuje 2 Instynktu; amunicja nie jest liczona. Jeden test przeciw
  jednemu celowi zadaje `2k8 + 2 × Zręczność`; Znak
  łowcy i Pierwsza krew dodają swoje kości tylko raz. Trafienie krytyczne
  podwaja wyłącznie bazowe kości dwóch strzał, nie kości tych dwóch dodatków.
- `Znak łowcy` kosztuje 1 Instynkt przy pierwszym nałożeniu. Jeśli oznaczony cel
  zostanie pokonany, podczas trwającej koncentracji znak można przenieść na
  kolejny legalny cel bez akcji i bez dodatkowego Instynktu.
- Skaza `Trauma bratobójczego strzału` daje `−1` do testu ataku z łuku za
  każdego przytomnego bohatera drużyny w 5 stopach od wybranego celu.
  Nie liczy Erynda, pokonanych,
  przywołań ani NPC i nie wpływa na nóż ani inne testy.

### Mira — ukrycie zależne od obserwatora

- Spośród bohaterów tylko Mira ma bojową akcję `Ukryj się`. Kosztuje akcję
  główną, nie wymaga osłony ani przerwania linii wzroku, lecz jest niedostępna
  przy przytomnym wrogu w 5 stopach, stanie blokującym ruch lub ujawniającym
  świetle. Mira nie ma wspólnego Sprintu/Odstąpienia; obie akcje należą wyłącznie
  do `Zwiadowczej mobilności` Erynda.
- Mira wykonuje jeden fizyczny test Skradania. Każdy aktywny przeciwnik wykonuje
  osobny automatyczny test Percepcji; remis oznacza wykrycie. Stan zapisuje
  widoczność i wynik osobno dla każdego obserwatora. Gdy widzą ją wszyscy
  aktywni przeciwnicy, tryb skradania kończy się automatycznie.
- W trybie skradania limit całego ruchu w turze wynosi 20 stóp. Dobrowolne
  przerwanie trybu przywraca normalny limit 25 stóp, ale nie zwraca akcji ani
  już wydanego ruchu. Podczas podglądu ruchu turkusowe figurki nie widzą Miry,
  a pomarańczowe ją widzą.
- Rapier i nóż do rzucania (zasięg 15 stóp) korzystają z premii zabójczyni raz
  na turę: osobista flanka daje `+1k6`, cel niewidzący Miry daje przewagę i
  `+2k6`, a oba warunki sumują się do `+3k6`. Atak kończy ukrycie globalnie.
- Wróg niewidzący Miry ignoruje ją przy wyborze celu i atakach okazyjnych, ale
  nie może zakończyć ruchu na jej polu. Gdy zaplanowana trasa przechodzi przez
  to pole, wróg zatrzymuje się przed Mirą, wydaje przebyty ruch, wykrywa ją tylko
  dla siebie i po potwierdzeniu ponownie planuje pozostałą część tury.
- Skaza `Panika po zdemaskowaniu`: w ramach bieżącej sesji skradania każdy
  przeciwnik, który widzi Mirę (po teście Percepcji, wyszukaniu albo przypadkowym
  wejściu na jej pole), ma płaską premię `+2` do testów ataku przeciw niej.
  Efekt nie działa dla
  obserwatorów, przed którymi nadal jest ukryta. Dobrowolne wyjście kończy sesję;
  jeżeli wykryje ją ostatni niewidzący jej wróg, sesja kończy się automatycznie.
  Kolejne użycie `Ukryj się` tworzy nową sesję i wykonuje nowe testy Percepcji.
- `Ruchomy cel` daje Mirze `+2 KP` przeciw dystansowym testom ataku bronią i
  czarem, lecz nie przeciw obszarom ani efektom wymagającym rzutu obronnego.
  Jeśli zakończy turę obok przeciwnika, który jej dotąd nie widział, ten
  przeciwnik ją wykrywa.
- `Unik instynktowny` może zostać zaproponowany tylko podczas aktywnego
  skradania, gdy widzący Mirę wróg wybiera ją jako cel testu ataku. Wydaje
  reakcję i 1 Fortel, dając pojedynczemu atakowi utrudnienie; nie usuwa płaskiej
  premii `+2` ze skazy. Bez reakcji albo Fortelu prompt się nie pojawia.
- `Zasłona dymna` kosztuje akcję i 1 Fortel. Mira przemieszcza się do 15 stóp
  bez ataków okazyjnych, a następnie rozpoczyna nową sesję skradania nawet obok
  przeciwnika. Każdy wróg ponawia test Percepcji z karą równą połowie dodatniego
  modyfikatora Zręczności Miry, zaokrągloną w dół.
- `Cięcie ścięgna` wymaga osobistej flanki, rapiera i 1 Fortelu. Raniące
  trafienie połowi szybkość celu aż do faktycznego leczenia albo oczyszczenia.
  `Przeszywający atak` wymaga sojusznika angażującego pierwszy cel z dowolnego
  sąsiedniego pola; to specjalne otwarcie liczy się jako flanka, ponieważ ścisła
  flanka po przeciwnej stronie zajęłaby pole drugiego celu. Po raniącym
  trafieniu wykonuje osobny, niełańcuchowy atak przeciw jedynemu wrogowi
  dokładnie za pierwszym, z ponownym naliczeniem właściwych premii ukrycia.
- `Przeskok przez gardę` nie kosztuje Fortelu. Wymaga sąsiadującego celu i
  wolnego legalnego pola dokładnie za nim, daje `+2` do ataku i obrażeń, po czym
  przenosi Mirę na to pole bez prowokowania ataku za sam skok.
- `Mistrzyni ostrzy` kosztuje 1 Fortel i wymaga rzutu nożem z ukrycia przeciw
  celowi, który Miry nie widzi. Raniące trafienie nakłada niekumulujące się
  Krwawienie `1k4` na początku tur celu, usuwane leczeniem albo oczyszczeniem.
- Bojowe `Wykrycie pułapek` kosztuje akcję, nie Fortel: uruchamia fizyczny test
  Percepcji, podświetla i skanuje promień 45 stóp oraz ujawnia wykryte pułapki
  w bieżącej strefie. `Włamanie` oraz dawny pakiet czarów Miry są wycofane.
- Z rasowych pasywek Miry pozostaje `Szczęście niziołka`; wycofane są `Odważny`,
  `Zwinność niziołka` i `Naturalne ukrywanie`.

### Nimra — kontrola obszaru i Metamagia

- Nimra ma pulę Punktów Metamagii równą dodatniemu modyfikatorowi Inteligencji;
  odzyskuje ją po długim odpoczynku. Do jednego czaru można dołączyć jedną
  Metamagię. Wybór i podgląd nie wydają punktów, akcji ani slotu — zasoby są
  rozliczane atomowo dopiero przy ostatecznym potwierdzeniu czaru.
- `Rzeźbienie pola`, `Odległy czar`, `Przeciążony czar`, `Wymuszony splot` i
  `Transmutacja energii` są wybierane przed czarem. Interfejs pokazuje wyłącznie
  zgodne czary, zachowując zwykły podgląd legalnego zasięgu, obszaru i celów.
- `Piorunowy szlak` ma zasięg 60 stóp. Wybrany cel wykonuje obronę Zręczności
  przeciw `3k6` obrażeń od błyskawic (połowa przy sukcesie), po czym piorun raz
  przeskakuje na najbliższą inną żywą istotę w 15 stopach. Odległość ma
  pierwszeństwo; przy remisie wybierany jest wróg, a dalszy remis rozstrzyga
  stabilny identyfikator. Gdy jedynym albo najbliższym celem jest sojusznik,
  piorun trafia sojusznika.
- Skaza `Echo magicznego wycieku` blokuje w następnej rundzie zarówno czar,
  jak i wariant Metamagii użyte w poprzedniej rundzie. Blokada powstaje dopiero
  po wykonaniu czaru; anulowany podgląd nie zapisuje Echa.

## Poza Zakresem Pierwszej Wersji

Pierwsza wersja nie obejmuje:

* kreatora postaci powyżej aktualnego limitu poziomu 3,
* czarów powyżej 2. poziomu w milestone postaci 1–3,
* pełnego katalogu potworów,
* gry sieciowej,
* zarządzania kampanią,
* symulacji świata,
* własnych zasad homebrew,
* odtwarzania starego interfejsu Pathfinder bez zmian,
* obowiązkowego cyfrowego rollera kości,
* automatycznego rozpoznawania wyników fizycznych kości kamerą.

---

## Przyszłe Rozszerzenia

Szczegółową listę przyszłych funkcji należy prowadzić w osobnym pliku `ROADMAP.md`.

Najważniejsze przyszłe obszary rozwoju:

* reakcje i ataki okazyjne,
* stany,
* czary,
* koncentracja,
* ekwipunek,
* pełniejsze bloki statystyk potworów,
* wielopolowe footprinty dużych istot,
* zaawansowany ruch,
* kampanie,
* opcjonalny cyfrowy roller kości,
* opcjonalne automatyczne rozpoznawanie rzutów fizycznych kości.

# Decyzje Zasad D&D 5e

Ten plik jest lokalnym zapisem tego, jak projekt interpretuje i implementuje konkretne zasady Dungeons & Dragons 5e.

Nie jest to pełna kopia podręcznika ani encyklopedia D&D. Ma zawierać krótkie, praktyczne decyzje potrzebne do implementacji i testów.

## Zasada Aktualizacji

Po każdej implementacji nowej mechaniki D&D należy dopisać albo zaktualizować odpowiednią sekcję w tym pliku.

Dotyczy to zwłaszcza:

- ruchu,
- rzutów,
- ataków,
- obrażeń,
- osłony,
- przewagi i utrudnienia,
- inicjatywy,
- stanów,
- czarów,
- reakcji,
- ataków okazyjnych.

Każda sekcja powinna zawierać:

- nazwę mechaniki,
- krótki opis decyzji implementacyjnej,
- zakres MVP,
- rzeczy poza zakresem,
- odnośnik do testów,
- źródło albo notatkę, że reguła wymaga późniejszej weryfikacji.

## Szablon Sekcji

```md
## Nazwa Mechaniki

Status: planned / implemented / partial

Źródło:
- TODO: SRD 5.1 / SRD 5.2 / inna decyzja projektowa

Implementacja MVP:
- ...

Poza zakresem MVP:
- ...

Odstępstwa / decyzje planszowe:
- ...

Testy:
- `tests/unit/...`
```

## Ruch Po Planszy

Status: partial

Źródło:

- `GAME_DESIGN.md`
- TODO: zweryfikować względem SRD / zasad ruchu na siatce przed rozbudową o wielopolowe footprinty i wyjątki przechodzenia zależne od rozmiaru.

Implementacja MVP:

- Jedno pole planszy odpowiada 5 feet.
- Ruch ortogonalny kosztuje 5 feet.
- Ruch diagonalny jest dozwolony i kosztuje naprzemiennie 5/10/5/10 feet w ramach ścieżki.
- Trudny teren kosztuje 10 feet za wejście na pole.
- Diagonalne wejście w trudny teren używa tego samego mnożnika: 10/20/10/20 feet.
- Sojusznik zajmuje pole, przez które można przejść, ale traktujemy je jako trudny teren.
- Przeciwnik blokuje przejście i zakończenie ruchu.
- Aktor nie może zakończyć ruchu na polu zajętym przez inną istotę.
- Ściany i blokujące przeszkody blokują przejście.
- Zamknięte drzwi blokują ruch, otwarte drzwi nie blokują ruchu.
- Ruch po skosie przez całkowicie zablokowany róg jest niedozwolony.
- W turze walki ruch jest pulą `speed_feet`, którą można dzielić przed i po ataku.
- Atak zużywa akcję, ale nie kasuje pozostałego ruchu.
- Koniec tury resetuje akcję i pulę ruchu.

Poza zakresem MVP:

- wielopolowe footprinty i przeciskanie zależne od rozmiaru,
- przeciskanie się,
- skakanie,
- wspinaczka,
- pływanie,
- latanie,
- ruch wymuszony.
- Dash, Disengage, Dodge,
- ataki okazyjne,

Odstępstwa / decyzje planszowe:

- Licznik kosztu diagonalnego jest częścią pathfindingu i nie resetuje się po kroku ortogonalnym w tej samej ścieżce.

Testy:

- `tests/unit/test_coordinates.py`
- `tests/unit/test_neighbors.py`
- `tests/unit/test_movement_cost.py`
- `tests/unit/test_movement_blocking.py`
- `tests/unit/test_pathfinding.py`
- `tests/unit/test_led_feedback.py`

## Rzuty Kośćmi

Status: implemented

Źródło:

- `GAME_DESIGN.md`
- TODO: zweryfikować względem SRD dla rzutów d20, przewagi, utrudnienia i trafień krytycznych.

Implementacja MVP:

- Gracze i Mistrz Gry rzucają fizycznymi kośćmi.
- Przed rzutem aplikacja pokazuje warunki rzutu: normalny rzut, przewagę albo utrudnienie.
- Przed rzutem aplikacja pokazuje aktywne bonusy i minusy, odrzucone duplikaty oraz końcowy modyfikator.
- Aplikacja pyta o jeden naturalny wynik rzutu.
- Dla przewagi aplikacja instruuje gracza, aby rzucił `2d20` i wpisał wyższy wynik.
- Dla utrudnienia aplikacja instruuje gracza, aby rzucił `2d20` i wpisał niższy wynik.
- Aplikacja dodaje tylko aktywne modyfikatory i rozstrzyga wynik.
- Modyfikatory bez `stacking_key` sumują się.
- Modyfikatory z tym samym `stacking_key` traktujemy jako ten sam efekt, więc nie stackują się.
- Z duplikatów dodatnich wybierany jest najwyższy bonus.
- Z duplikatów ujemnych wybierana jest najsilniejsza kara.
- Odrzucone duplikaty pozostają widoczne w breakdown, ale nie liczą się do końcowego wyniku.
- Naturalne `20` przy rzucie ataku oznacza trafienie krytyczne.
- Naturalne `1` przy rzucie ataku oznacza automatyczne pudło.
- Naturalne `20` i `1` przy testach cech nie oznaczają automatycznego sukcesu/porażki w MVP.

Poza zakresem MVP:

- obowiązkowy cyfrowy roller kości,
- automatyczne rozpoznawanie rzutów kamerą,
- automatyczne wyliczanie wszystkich bonusów z pełnej karty postaci, klas, czarów i ekwipunku,
- szczegółowe rozbijanie wszystkich kości obrażeń w UI.

Odstępstwa / decyzje planszowe:

- Domyślnym modelem są fizyczne kości, nie cyfrowy roller.
- Przewaga i utrudnienie nie są bonusami liczbowymi i nie trafiają do listy modyfikatorów.
- Obrażenia, typy obrażeń i kości obrażeń są osobnym modelem późniejszego etapu.

Testy:

- `tests/unit/test_dice.py`
- `tests/unit/test_checks.py`
- `tests/unit/test_attack_rolls.py`

## Inicjatywa

Status: implemented

Źródło:

- `GAME_DESIGN.md`
- D&D 5e 2014 odbiera zaskoczonemu ruch i akcje w pierwszej turze oraz reakcje do końca tej tury. MVP świadomie nie używa tej pełnej kary.

Implementacja MVP:

- Rozpoczęcie walki poprzedza setup jawnych figurek i elementów otoczenia.
- Komunikaty aplikacji i LED-y są zsynchronizowane: świeci tylko to, czego dotyczy aktualny krok.
- Bohaterowie są wywoływani do rzutu inicjatywy po kolei.
- Bohater rzuca fizycznie `1d20` i wpisuje jeden naturalny wynik.
- Przed rzutem aplikacja pokazuje warunki rzutu i aktywne modyfikatory.
- Przeciwnicy kontrolowani przez aplikację mają inicjatywę rzuconą automatycznie.
- Automatyczny rzut przeciwnika używa wstrzykiwanego RNG, żeby testy były deterministyczne.
- Kolejność inicjatywy sortuje po najwyższym wyniku końcowym.
- Remis rozstrzyga wyższy modyfikator ze Zręczności.
- Pełny remis zachowuje stabilną kolejność wejściową.
- Grywalna scena po setupie używa realnego flow inicjatywy przed pierwszą turą.
- Runtime debugowy może użyć `--initiative-mode fixed` tylko jako trybu testowego.
- Po ostatnim aktorze kolejka wraca na początek i zwiększa rundę.
- Pokonani aktorzy mogą pozostać w kolejce, ale przechodzenie tury może ich pomijać.
- Między eksploracją a setupem encountera działa jawny etap rozpoczęcia starcia. Content wybiera wynik na podstawie zapisanego stanu sceny, np. hałasu, rozpoznania i tagów kończącego podejścia.
- W MVP zaskoczona strona zachowuje pełną pierwszą turę, ale wykonuje testy inicjatywy z utrudnieniem. Bohaterowie wpisują dwa rzuty d20, a przeciwnicy mają oba rzuty wykonane automatycznie.
- Jeżeli scenariusz rozstrzygnął ciche podejście drużyny, po setupie i przed inicjatywą pojawia się opcjonalny etap skradania. Każdy przytomny bohater ma jedną próbę Dexterity (Stealth), porównywaną osobno z passive Perception każdego przeciwnika.
- Zakończenie etapu, również bez wykonywania prób, jest jawną decyzją. Udane relacje ukrycia przechodzą do `CombatState` i obowiązują od pierwszej rundy bez ponownego rzutu.

Poza zakresem MVP:

- opóźnianie tury,
- gotowe akcje,
- reakcje,
- efekty dynamicznie zmieniające inicjatywę,
- skanowanie pól jako potwierdzenie setupu.

Odstępstwa / decyzje planszowe:

- Klikanie pionka nie jest wymagane do ustalenia, kto rzuca inicjatywę.
- Jawne elementy setupu są podświetlane LED-ami, ukryte i warunkowe elementy nie są zdradzane graczom.
- MVP nadal rozstrzyga bazowe zaskoczenie całej strony przez reguły scenariusza i zastępuje pełną karę D&D utrudnieniem do inicjatywy. Indywidualne Stealth vs passive Perception określa natomiast, przed którymi konkretnie przeciwnikami bohater zaczyna walkę ukryty; nie zastępuje jeszcze oficjalnego per-creature surprised condition.

Testy:

- `tests/unit/test_ability_modifiers.py`
- `tests/unit/test_encounter_setup.py`
- `tests/unit/test_setup_led_feedback.py`
- `tests/unit/test_initiative.py`
- `tests/unit/test_initiative_led_feedback.py`
- `tests/unit/test_combat_session.py`
- `tests/unit/test_encounter_opening_flow.py`
- `tests/unit/test_demo_initiative_setup.py`

## Atak I Obrażenia

Status: partial

Źródło:

- `GAME_DESIGN.md`
- TODO: zweryfikować względem SRD dla attack roll, AC, damage roll i critical hit.

Implementacja MVP:

- MVP obsługuje prosty melee weapon attack oraz prosty ranged weapon attack.
- Aplikacja pokazuje legalne cele ataku LED-ami.
- Gracz wybiera cel przez planszę albo fallback runtime.
- Źródło ataku jawnie rozróżnia `attack_kind`: melee korzysta z `reach_feet`, a ranged z `range_feet`. Zwykły atak wręcz ma reach 5 feet; nowy content podaje oba pola jawnie zamiast polegać na nazwie albo heurystyce.
- Legalny cel ataku musi mieścić się w efektywnym zasięgu właściwym dla rodzaju źródła.
- Dystans na siatce liczony jest w uproszczony sposób: `max(abs(dc), abs(dr)) * 5 feet`.
- Ranged line of sight / line of effect używa prostego algorytmu Bresenhama na siatce.
- Linia jest blokowana przez ściany/krawędzie, zamknięte drzwi i blokujący terrain na polach pośrednich.
- Żywa postać znajdująca się na polu pośrednim daje celowi half cover (`+2 AC`) przeciw rzutowi ataku.
- Obiekt sceny może deklarować `projectile_cover_bonus` równy `2` albo `5`, odpowiednio dla half cover i three-quarters cover. Premie osłony nie sumują się; działa najwyższa osłona na linii pocisku.
- Pełna blokada linii widzenia oznacza total cover i wyklucza cel z legalnych celów ataku.
- Atak dystansowy ma utrudnienie, jeśli w odległości 5 feet od atakującego znajduje się żywy, widzący go przeciwnik. Jak zwykle jedna przewaga i jedno utrudnienie wzajemnie się znoszą.
- Opcjonalna reguła flankowania z D&D 5e 2014 jest domyślnie włączona. Atak wręcz z sąsiedniego pola ma przewagę, gdy żywy sojusznik atakującego stoi na dokładnie przeciwległym polu albo rogu względem jednopolowego celu i ma do niego linię widzenia.
- Flankowanie nie działa dla ataków dystansowych, save-spelli ani efektów obszarowych. Pokonany sojusznik nie zapewnia flankowania. Preview i log zdarzenia zapisują flankujących aktorów, a `Flankowanie` jest jawnym modyfikatorem sytuacyjnym rzutu.
- Half cover dodaje `+2`, a three-quarters cover `+5` również do rzutów obronnych na Zręczność przeciw czarom. Premia jest jawnym `RollModifier` i pojawia się w preview oraz rozbiciu wyniku save'a; save oparty na innej cesze nie otrzymuje premii.
- Dla czaru obszarowego osłona jest liczona od punktu pochodzenia efektu: wskazanego środka dla `radius` oraz pozycji rzucającego dla `line` i `cone`. Pełna przeszkoda między punktem pochodzenia a aktorem wyklucza go z celów obszaru.
- Te zasady dotyczą obecnie czarów single-target i obszarowych. Hazardy eksploracyjne bez pozycji źródła nie zgadują osłony.
- Atak porównuje wynik ataku z AC celu.
- Naturalne `20` przy ataku oznacza trafienie krytyczne.
- Naturalne `1` przy ataku oznacza automatyczne pudło.
- Przy trafieniu aplikacja prosi o wynik obrażeń.
- Gracz wpisuje końcowy wynik każdego składnika obrażeń osobno. Dla źródła
  jednoskładnikowego stary pojedynczy input pozostaje kompatybilny.
- Źródło ataku może deklarować wiele składników z osobnym typem oraz formułą `NdM`
  albo wartością stałą. Krytyk podwaja wyłącznie liczbę kości każdego składnika;
  płaski modyfikator jest dodawany jeden raz.
- Obrażenia są wpisywane jako komponenty z typem obrażeń.
- `hp` aktora oznacza aktualne HP, a `max_hp` oznacza maksymalne HP z contentu/scenariusza.
- Obrażenia najpierw zmniejszają temporary HP, potem HP.
- HP nie spada poniżej `0`.
- Wynik aplikacji obrażeń zapisuje HP i temporary HP przed/po, ile obrażeń pochłonęło temporary HP, ile weszło w HP oraz czy cios pokonał cel.
- Komunikaty UI po trafieniu muszą pokazywać obrażenia oraz zmianę HP celu.
- Bohater z cechą `uses_death_saves` po zejściu do 0 HP traci przytomność i pozostaje w inicjatywie, aby wykonywać rzuty śmierci; przeciwnik bez tej cechy jest pokonany przy 0 HP.
- `hp > 0` nie oznacza automatycznie, że obiekt jest legalnym celem ataku.
- Cel ataku musi być `attackable=True` i `visible`.
- `RollMode.ADVANTAGE` i `RollMode.DISADVANTAGE` rozstrzygają pełne `2d20`: zapisujemy oba wyniki, a wybrana kość to wyższa przy przewadze i niższa przy utrudnieniu.
- Przy ręcznych rzutach ataku UI wymaga wpisania obu wyników d20, jeśli rzut ma przewagę albo utrudnienie; przeciwnicy rzucają oba d20 automatycznie.
- Mini-pętla walki obsługuje start tury, zużycie akcji, koniec tury, przejście inicjatywy i zakończenie walki.
- Tura śledzi osobno akcję główną, akcję bonusową, reakcję i zużyty ruch.
- Pierwszy weapon attack rozpoczyna Attack action i zużywa jeden wpis z budżetu
  `attacks_per_action` aktywnego aktora. Między kolejnymi atakami można wykorzystać
  pozostały ruch, zmienić cel i wybrać inne legalne źródło broni.
- Spell attack i save-spell zużywają Cast a Spell action, więc nie korzystają z
  budżetu Extra Attack. Bonusowy atak drugą bronią nadal zużywa bonus action.
- Potwory mogą deklarować osobną, uporządkowaną listę `multiattack`; runtime wykonuje
  każde źródło po kolei i po każdym wyniku wraca do planowania, dzięki czemu może
  ponownie wybrać legalny cel lub wykorzystać pozostały ruch.
- Reakcja jest śledzona per aktor, również poza jego własną turą, i odświeża się na początku jego następnej tury.
- Reakcje przerywające akcję korzystają ze wspólnego, uporządkowanego
  `ReactionWindow`. Okno przechowuje przerwanego aktora i stabilną kolejność opcji;
  każda opcja jest rozstrzygana lub pomijana przed wznowieniem akcji. Aktor, który
  zużył reakcję, jest automatycznie pomijany w późniejszych opcjach tego samego okna.
  W obecnym contencie Ready ma pierwszeństwo przed wykrytymi atakami okazyjnymi,
  zachowując dotychczasowy kontrakt sceny; nowe rodzaje reakcji muszą jawnie określić
  miejsce w kolejności zamiast tworzyć osobny stan oczekujący w UI.
- `Kontrczar` ma pierwszeństwo przed reakcją `Tarcza`, ponieważ przerywa rzucanie
  wrogiego czaru przed jego skutkiem. Wymaga widoczności i dystansu do 60 stóp,
  zużywa reakcję oraz jawnie wybrany slot. Czar na poziomie nie wyższym od slotu
  jest przerywany automatycznie; silniejszy wymaga testu cechy rzucania czarów
  przeciw ST `10 + poziom czaru`. Dopóki model aktora przechowuje ST czarów, ale
  nie identyfikator głównej cechy, modyfikator testu jest odtwarzany jako
  `spell_save_dc - 8 - proficiency_bonus`, bez dodawania biegłości do testu.
- Casting time `minute`, `ten_minutes` i `hour` jest przeliczany na odpowiednio
  10, 100 i 600 sześciusekundowych rund. Rozpoczęcie i każdy dalszy krok zużywa
  akcję, a stan `LongCastState` zapisuje ostatnią rundę postępu. Brak tej akcji
  przed końcem kolejnej tury przerywa czar.
- Długie rzucanie korzysta ze wspólnego lifecycle koncentracji niezależnie od
  późniejszego duration czaru. Ruch jest legalny; obrażenia wywołują zwykły CON
  save. Przerwanie nie zużywa slotu, ponieważ slot i komponenty są rozliczane
  dopiero po ukończeniu castingu.
- `Dash` zużywa akcję główną i dodaje aktorowi dodatkową pulę ruchu równą jego `speed_feet` do końca bieżącej tury.
- `Dodge/Unik` zużywa akcję główną i daje efekt `Unik`: ataki przeciwko aktorowi mają utrudnienie; efekt wygasa na początku następnej tury tego aktora.
- `Disengage/Odwrót` zużywa akcję główną i w MVP daje efekt `Odwrót`: bezpieczne odejście do końca tury, blokujące ataki okazyjne.
- Warunki walki mają osobny, serializowany `ConditionState`; nie są kodowane jako chwilowy komunikat UI ani zwykły `ActiveEffect`.
- `Prone/Powalony` używa zasad D&D 5e 2014: aktor może paść bez zużywania akcji ani ruchu, a wstanie kosztuje połowę jego bazowej szybkości i jest możliwe tylko przy wystarczającym pozostałym ruchu.
- Powalony aktor czołga się: każdy foot drogi kosztuje dodatkowy foot ruchu. Koszt ten kumuluje się z difficult terrain, więc krok 5 feet po trudnym terenie kosztuje 15 feet.
- Powalony atakujący ma utrudnienie. Atak przeciw powalonemu celowi ma przewagę z odległości do 5 feet, a z większej odległości ma utrudnienie; przewagi i utrudnienia znoszą się standardowo.
- UI pokazuje stan `Powalony` jako status aktora. Padnięcie i wstanie wybiera się z menu własnego pola; AI wstaje na początku swojej tury, jeśli ma wystarczający ruch.
- `Actor` przechowuje jeden `ProficiencyProfile` dla saving throwów, skilli, expertise, broni, pancerzy i narzędzi. `proficiency_bonus` pozostaje wartością aktora, niezależną od konkretnej klasy.
- Ability check, saving throw i attack roll składają osobne `RollModifier`: cechę, proficiency albo expertise oraz modyfikatory sytuacyjne. UI pokazuje te składniki zamiast anonimowej premii końcowej.
- Biegłość w broni jest wiązana ze stabilnym id itemu, a dla naturalnego ataku potwora z id źródła ataku. Atak bronią wskazujący `ability` wylicza premię z cechy i dodaje proficiency wyłącznie przy pasującej biegłości aktora. Historyczne `attack_modifier` pozostaje fallbackiem dla starszego contentu bez `ability`.
- Katalog SRD 5.1 obejmuje 37 broni w jednym kontrakcie `weapon`. Biegłość może
  pochodzić z id broni albo kategorii `simple_weapons`/`martial_weapons`; kość
  obrażeń nie zawiera statystyki konkretnego właściciela.
- Finesse wystawia warianty Strength i Dexterity. Thrown wystawia wariant ranged,
  usuwa jeden egzemplarz z dłoni/stacku i pozostawia podnoszalną broń na polu celu.
  Long range jest legalny z utrudnieniem; heavy daje utrudnienie Small istocie.
- Jednoręczna broń ammunition wymaga wolnej drugiej dłoni. Loading i sieć
  ograniczają ataki w ramach jednej Attack action do jednego.
- Lanca ma reach 10 ft i utrudnienie przeciw celowi w 5 ft. Do czasu wdrożenia
  mounted combat jest dwuręczna. Sieć trafieniem nakłada Restrained tylko na cel
  Large lub mniejszy; akcja Strength ST 10 usuwa stan. Zniszczenie sieci jako
  atakowalnego obiektu AC 10 / 5 HP pozostaje odroczone.
- Saving throwy czarów, efektów sceny i koncentracji korzystają z tego samego profilu. Samo posiadanie wysokiej cechy nie oznacza biegłości.
- Wszystkie nowe save'y opisuje wspólny `SavingThrowRequest`: cecha, ST, źródło oraz skutek sukcesu. `SavingThrowResult` zachowuje naturalny d20, jawne składniki modyfikatora, sumę i mnożnik obrażeń.
- Save wymuszony przez przeciwnika na bohaterze jest rzutem fizycznym gracza. Po potwierdzeniu celu tura przeciwnika zatrzymuje się, UI pokazuje cechę, ST i modyfikatory, a wpisany naturalny d20 rozstrzyga pełne, połowę albo brak obrażeń.
- Mnożnik wynikający z save'a stosuje się przed resistance/immunity/vulnerability i przed temporary HP. Rzut obronny potwora przeciw efektowi gracza pozostaje automatyczny.
- Zagrożenie eksploracyjne może po porażce albo krytycznej porażce wywołać osobny fizyczny saving throw. Nie zmienia HP przed rozstrzygnięciem tego rzutu i korzysta z tego samego typed-damage pipeline co walka.
- Standardowy upadek D&D 5e 2014 zadaje `1d6 bludgeoning` za każde 10 ft i nie daje domyślnie save'a redukującego obrażenia. Dexterity save ST 12 przy wspinaczce po bramie jest jawnym rozstrzygnięciem scenariuszowym: reprezentuje odzyskanie kontroli i redukuje obrażenia o połowę.
- Test narzędzia jest ability checkiem z cechą wybraną przez sytuację i stabilnym id narzędzia. Biegłość narzędziowa dodaje jeden proficiency bonus; biegłość skilla i narzędzia w tej samej próbie nie sumują proficiency podwójnie, a expertise ma pierwszeństwo przed zwykłą biegłością.
- Test przeciwstawny porównuje końcowe wyniki dwóch niezależnych ability checków. Wyższy wynik wygrywa, a remis zachowuje stan sprzed próby. Resolver jest neutralny wobec konkretnej akcji i stanowi wspólną podstawę Shove oraz Grapple.
- Shove bazuje na zasadach D&D 5e 2014: wymaga celu w zasięgu 5 ft, atakujący rzuca Strength (Athletics), a cel broni się korzystniejszym Strength (Athletics) albo Dexterity (Acrobatics). Remis oznacza skuteczną obronę.
- Przed rzutem gracz wybiera powalenie albo odepchnięcie o 5 ft. Powalenie używa wspólnego `Prone`; odepchnięcie przesuwa cel bez zużywania jego movement i bez ataków okazyjnych. Niedostępne pole docelowe blokuje wariant odepchnięcia, ale nie wariant powalenia.
- Shove zastępuje jeden atak w ramach Attack action. Cel Shove może być najwyżej o jedną kategorię rozmiaru większy od atakującego.
- Grapple używa zasad D&D 5e 2014: sąsiedni cel broni się lepszym Athletics/Acrobatics przed Strength (Athletics) chwytającego, a remis oznacza obronę. Rozpoczęcie Grapple zastępuje jeden atak Attack action; ucieczka z chwytu nadal zużywa całą akcję.
- `Grappled` jest źródłowym `ConditionState`: wskazuje chwytającego i ustawia ruch celu na 0. Chwytany bohater może zużyć akcję na lepsze Athletics/Acrobatics przeciw Athletics chwytającego; sukces usuwa konkretną relację chwytu.
- Chwytający przeciąga jeden cel na swoje poprzednie pole z efektywną szybkością zmniejszoną o połowę. Ta redukcja jest stosowana przed Dash i niezależnie od kosztu difficult terrain; UI pokazuje skrócony zasięg, wartość bazową/efektywną oraz różowe pole docelowe chwytanej figurki. Przymusowe przesunięcie celu nie prowokuje jego ataków okazyjnych. Pokonanie jednej strony albo rozdzielenie ich poza 5 ft automatycznie kończy chwyt.
- Grapple wymaga co najmniej jednej wolnej ręki po uwzględnieniu trzymanego wyposażenia. Cel może być najwyżej o jedną kategorię rozmiaru większy; obecne MVP nadal pozwala jednemu aktorowi utrzymywać najwyżej jeden chwyt.
- `CreatureSize` obejmuje Tiny, Small, Medium, Large, Huge i Gargantuan. Brak pola w starszym contentcie oznacza Medium. Wszystkie rozmiary nadal używają jednej figurki i jednego pola; footprinty wielopolowe są osobnym przyszłym etapem.
- Obrażenia używają trzynastu bazowych typów D&D 5e 2014. Składniki jednego zdarzenia są sumowane według typu przed zastosowaniem resistance, immunity albo vulnerability, aby zaokrąglenie nie zależało od technicznego podziału źródła.
- Resistance dzieli obrażenia danego typu przez dwa z zaokrągleniem w dół, vulnerability je podwaja, a immunity redukuje do zera. Wielokrotna ta sama relacja nie kumuluje się. Jeśli resistance i vulnerability dotyczą tego samego typu, stosowana jest kolejność z zasad 2014: najpierw resistance, potem vulnerability; immunity ma pierwszeństwo.
- Saving throw i pozostałe modyfikatory źródła są rozliczane przed profilem odporności celu. Temporary HP pochłania dopiero końcową wartość obrażeń.
- Obecny profil jest zależny wyłącznie od typu obrażeń. Kwalifikatory typu „od niemagicznych ataków”, srebrzona broń oraz wyjątki omijające odporność wymagają przyszłego kontraktu cech źródła obrażeń i nie są zgadywane z nazwy broni.
- Otwieranie zamka bramy jest Dexterity check z `thieves_tools`, nie Dexterity (Sleight of Hand). Posiadanie zestawu pozostaje wymogiem, biegłość pochodzi z profilu aktora, a scenariuszowe ryzyko uszkodzenia jest osobną konsekwencją.
- Bazą Hide i Search jest D&D 5e 2014. Stealth oraz Perception korzystają ze wspólnego wyliczenia ability modifier + proficiency/expertise.
- Hide zużywa akcję dopiero po wpisaniu rzutu Dexterity (Stealth). Próba jest legalna, jeśli żaden żywy przeciwnik nie widzi aktora wyraźnie.
- Dla deterministycznej planszy „nie widzi wyraźnie” oznacza zablokowaną linię widzenia albo co najmniej three-quarters cover na linii. Half cover nie wystarcza. Jest to jawne doprecyzowanie pozostawionej MG oceny okoliczności z zasad 2014.
- Wynik Stealth jest porównywany osobno z passive Perception każdego przeciwnika. Remis oznacza wykrycie; aktor może pozostawać ukryty przed jednym obserwatorem, a widoczny dla innego.
- Stan ukrycia przechowuje wynik Stealth i listę obserwatorów. Search zużywa akcję i wykonuje Wisdom (Perception) przeciw zapisanemu wynikowi; sukces ujawnia cel tylko szukającemu.
- Wejście na pole, z którego obserwator znowu widzi aktora wyraźnie, kończy ukrycie względem tego obserwatora. Utrata przytomności albo wykonanie attack roll ujawnia aktora wszystkim.
- Atakujący ukryty przed celem ma przewagę do rzutu ataku. Przewaga nadal znosi się z pojedynczym utrudnieniem według zwykłych reguł d20.
- Przeciwnik nie wybiera celu ukrytego przed nim i nie podąża do jego pozycji na podstawie wiedzy UI. Gdy nie widzi żadnego celu, automatycznie używa Search.
- Ukrycie może powstać również przed inicjatywą, ale tylko gdy scenariuszowe rozpoczęcie starcia potwierdziło, że drużyna podeszła niezauważona. Każdy bohater ma jedną próbę, a wynik i relacje per obserwator są zapisywane w oczekującym encounterze i przenoszone do walki.
- Board MVP nie obsługuje jeszcze zgadywania pola ukrytego celu i ataku z utrudnieniem. Ukryty cel nie jest legalnie podświetlany, nawet jeśli obserwator mógł wcześniej znać jego pozycję. Dźwięk, czary z komponentem Verbal, invisible i specjalne senses pozostają kolejnymi rozszerzeniami.
- Atak okazyjny może zostać sprowokowany, gdy aktor dobrowolnie opuszcza `reach_feet` żywego wroga z dostępną reakcją i aktywnym źródłem ataku wręcz. Sam ruch wewnątrz tego zasięgu nie prowokuje.
- Źródła dystansowe nie tworzą strefy zagrożenia niezależnie od ich krótkiego `range_feet`. Dzięki temu krótki ranged attack nie jest omyłkowo traktowany jak broń wręcz, a melee reach może przekraczać 10 feet bez specjalnej heurystyki.
- AI przeciwnika uwzględnia reach wybranego źródła i zatrzymuje się na pierwszym osiągalnym polu, z którego może zaatakować, zamiast zawsze podchodzić do sąsiedniego pola.
- Shove i Grapple pozostają manewrami o stałym zasięgu 5 feet; reach trzymanej broni ich nie rozszerza.
- Loader zachowuje kompatybilność ze starszym contentem: przy braku `attack_kind` źródło z `range_feet > 10` jest interpretowane jako ranged, a krótsze jako melee. Jest to wyłącznie fallback migracyjny; nowy content ma deklarować rodzaj i reach jawnie.
- UI gracza zatrzymuje ruch prowokujący, pokazuje zagrożenia i wymaga Entera albo przycisku przed rozstrzygnięciem reakcji i wykonaniem ruchu.
- Wykrywanie ataku okazyjnego jest symetryczne dla bohaterów i przeciwników.
- Gdy przeciwnik opuszcza zasięg bohatera podczas zapowiedzianego ruchu, UI pozwala wykonać albo pominąć reakcję bohatera; przy wykonaniu gracz wpisuje rzut d20 i, po trafieniu, obrażenia.
- Jeśli atak okazyjny bohatera pokona przeciwnika, ruch i dalsza część tury przeciwnika zostają przerwane.
- `Help/Pomoc` w combacie zużywa akcję główną pomagającego.
- W MVP `Help` działa tylko dla ataku: pomagający musi wskazać żywego sojusznika oraz żywego przeciwnika w zasięgu 5 ft pomagającego.
- Wybrany sojusznik dostaje przewagę na następny atak przeciw wskazanemu celowi; efekt nie działa na inne cele.
- Efekt `Help` znika po takim ataku albo na początku następnej tury pomagającego.
- `Help` w eksploracji i testach umiejętności jest poza zakresem tego etapu.
- `Ready/Przygotowanie` w combacie zużywa akcję główną aktywnego aktora i zapisuje przygotowany atak jako efekt `ready_attack`.
- W MVP przygotowany atak może reagować na ruch przeciwnika albo atak przeciwnika; gdy warunek zajdzie, UI pozwala wykonać albo pominąć reakcję.
- Wykonanie przygotowanego ataku zużywa reakcję aktora, wymaga wpisania rzutu d20 i, po trafieniu, wpisania obrażeń.
- Efekt `Ready` znika po użyciu reakcji albo na początku następnej tury aktora.
- Jeśli przygotowany atak pokona przeciwnika przed zakończeniem jego zamiaru, tura tego przeciwnika zostaje przerwana.
- Aktor może mieć wiele źródeł ataku (`AttackSource`), np. broń albo czar ofensywny; UI wybiera aktywne źródło, a legalne cele i LED-y liczą się dla tego źródła.
- `AttackSource` może wskazywać cechę (`ability`), żeby efekty typu premia do Siły działały tylko na właściwe źródła, np. miecz, ale nie kuszę ani czar.
- Aktor może mieć proste sloty czarów (`spell_slots`); czary poziomu `0` nie zużywają slotu, a czary poziomu `1+` zużywają slot wskazanego poziomu w momencie użycia akcji.
- Źródła czarów mają jawne `casting_kind`: `cantrip` albo `leveled`; jeśli content go nie poda, loader wylicza go ze `source_type=spell` i `spell_level`.
- Aktor wymagający przygotowywania czarów ma generyczny `SpellPreparationProfile`: listę dostępnych czarów poziomu 1+, limit, wybór zajmujący limit oraz czary zawsze przygotowane poza limitem.
- Przed setupem scenariusza UI wymaga wybrania dokładnie tylu czarów, ile wynosi limit profilu. Jest to projektowy odpowiednik przygotowania czarów po zakończonym długim odpoczynku; wybór pozostaje zablokowany do końca scenariusza.
- Fizyczny przepływ podaje legalny zestaw domyślny jako karty. `AKCEPTUJ` zatwierdza go, `ODRZUĆ` przełącza na pusty zestaw własny, a każda kolejna karta czaru dodaje jeden unikalny czar należący do bieżącego profilu. Osiągnięcie limitu zapisuje zestaw automatycznie; cantripy, czary spoza listy oraz czary zawsze przygotowane nie mogą zająć miejsca w limicie.
- Cantripy nie wymagają przygotowania. Nieprzygotowany czar poziomu 1+ nie daje bonusu eksploracyjnego i nie może zostać użyty jako atak, leczenie ani akcja czarowa, nawet jeśli aktor ma wolny slot.
- Profil jest źródłowy: kreator wylicza listę, rodzaj dostępu
  (`known`, `spellbook`, `prepared`), limit przygotowania i cechę czarującą z
  klasy, poziomu, subclassy, species oraz wybranych opcji. Runtime nie zgaduje
  klasy na podstawie samego identyfikatora czaru.
- Scenariusz rozpoczyna się automatycznym long restem drużyny. Odnawia on utracone HP, sloty czarów oraz zasoby z recovery `short_rest` lub `long_rest`, usuwa temporary HP, odzyskuje połowę maksymalnej liczby Hit Dice (minimum jedną) i ponownie otwiera przygotowanie czarów.
- Aktor z 0 HP nie może skorzystać z long resta. Obecne automatyczne odzyskiwanie Hit Dice wypełnia pule w kolejności danych; wybór odzyskiwanych pul dla przyszłego multiclassingu pozostaje poza MVP.
- Short rest jest akcją eksploracyjną trwającą co najmniej 60 minut. Dostępność, poziom bezpieczeństwa, limit ukończeń i konsekwencje są definiowane przez `ShortRestPolicy` bieżącej lokacji.
- Ukończenie short resta odnawia wyłącznie generyczne zasoby z recovery `short_rest`. Nie odnawia zwykłych slotów czarów i nie otwiera przygotowania czarów.
- Po ukończeniu short resta każdy gracz może wydawać dostępne Hit Dice pojedynczo. Aplikacja dodaje modyfikator CON, ogranicza HP do maksimum i po każdym rzucie pozwala zakończyć albo wydać następną kość.
- Anulowanie preview short resta nie przesuwa czasu ani nie zużywa Hit Dice. Contentowe konsekwencje są wykonywane dopiero po potwierdzonym ukończeniu odpoczynku.
- Nie ma globalnego limitu short restów. Opcjonalny `max_completions` jest ograniczeniem konkretnej lokacji/scenariusza, nie ogólną zasadą D&D.

## Aktywne Efekty I Czas Trwania

- Aktywny efekt posiada jawne `source`, `duration`, `stacking` i `stacking_key`; UI pokazuje graczowi źródło oraz moment wygaśnięcia.
- Wspólne granice lifecycle obejmują początek/koniec tury, koniec rundy, właściwy atak, ruch z pozycji, zakończenie koncentracji, encountera, short/long resta oraz scenariusza.
- Efekt może mieć więcej niż jeden warunek zakończenia. Przykładowo Help kończy się po właściwym ataku albo na początku następnej tury pomagającego.
- `replace` zastępuje efekt o tym samym stacking key, `refresh` robi to samo i raportuje odświeżenie, a `stack` zachowuje osobne instancje z unikalnymi id.
- Long rest i koniec scenariusza usuwają wszystkie efekty niepermanentne. Short rest usuwa tylko efekty jawnie trwające do short resta; nie przerywa automatycznie koncentracji.
- Efekty ograniczone do encountera wygasają przed przeniesieniem stanu bohaterów z walki do eksploracji. Jeżeli efekt materializował zmianę stanu, np. premię do AC, wygaśnięcie przywraca wartość bazową.
- Ręczne zakończenie scenariusza jest obecnie granicą lifecycle, nie systemem zapisu. Wersjonowany snapshot pozostaje następnym etapem M1.
- Koncentracja MVP działa jako wspólny `ActiveEffect` z `source_actor_id`; jeden rzucający może utrzymywać tylko jeden efekt `concentration_*`.
- Rzucenie nowego czaru koncentracyjnego tego samego aktora usuwa jego poprzedni efekt koncentracji i pokazuje komunikat w UI.
- `Błogosławieństwo` w `gate_skirmish` jest testowym czarem koncentracyjnym: zużywa akcję i slot 1. poziomu, wybiera sojusznika i daje mu `+1` do ataku, dopóki koncentracja trwa.
- Gdy aktor utrzymujący koncentrację otrzyma obrażenia, wykonuje CON save przeciw ST `max(10, obrażenia // 2)`. Sojusznik wymaga wpisania d20 w UI, przeciwnik rzuca automatycznie; porażka usuwa efekty `concentration_*` tego aktora.
- Test koncentracji jest zwykłym Constitution saving throwem: uwzględnia
  modyfikator cechy, biegłość, aury, exhaustion oraz wspólny tryb
  advantage/disadvantage. Fizyczny rzut wymaga dwóch wyników d20, gdy aktywny
  tryb tego wymaga.
- Aktor rzucający czary może mieć `spell_save_dc`; źródło czaru może nadpisać DC własnym `save_dc`.
- `AttackSource` może być save-spellem przez `save_ability`; wtedy przeciwnik wykonuje automatyczny rzut obronny, a UI pokazuje naturalny d20, modyfikator cechy, sumę, ST i sukces/porażkę.
- `AttackSource` może mieć obszar (`area`) typu `radius`, `line` albo `cone`; plansza wybiera środek obszaru albo jedno z ośmiu sąsiednich pól kierunku, UI pokazuje pełny preview LED i wymaga Entera/przycisku przed wykonaniem.
- Wszystkie wymiary obszaru są dodatnimi wielokrotnościami 5 feet. `line` respektuje `length_feet` i `width_feet`, tworząc równoległe tory pól. `cone` rośnie warstwami o szerokości 1, 2, 3... pól do `length_feet`; parzysta warstwa ma deterministyczne przesunięcie widoczne w preview.
- Każde pole obszaru wymaga line-of-effect od punktu pochodzenia. Ściany, zamknięte krawędzie i blocking terrain odcinają pola znajdujące się za przeszkodą; dla radiusa punktem pochodzenia jest środek, a dla line/cone rzucający.
- `area.target_mode` jest data-driven: `all_creatures` obejmuje każdą żywą istotę w obszarze i stanowi domyślne friendly fire, `enemies` ogranicza efekt do przeciwników, a `allies` do sojuszników. Rzucający również może być celem `all_creatures` albo `allies`, jeżeli jego pole faktycznie znajduje się w obszarze.
- UI ostrzega przed potwierdzeniem, jeśli obszar obejmuje rzucającego albo jego sojusznika, i nadal pokazuje osobny save oraz osłonę dla każdego celu.
- W MVP czary obszarowe i save-spelle aplikują wpisany przez gracza końcowy wynik obrażeń po wyniku save’a: `none` oznacza brak obrażeń przy sukcesie, `half` oznacza połowę obrażeń przy sukcesie.
- Leczenie w combacie jest osobnym źródłem akcji (`HealingSource`), a nie atakiem; legalnym celem jest ranny sojusznik w zasięgu i linii widzenia.
- Gracz wpisuje końcowy wynik leczenia z fizycznego rzutu, a aplikacja ogranicza HP do `max_hp`.
- Aktor może mieć proste `inventory` z itemami rozwijanymi z `content/items`; `item_refs` pozostają skrótem dla wyposażonych itemów.
- Item może dostarczać źródła ataku, leczenia albo `combat_actions`; akcje pochodzące z consumable zapisują `source_item_id`.
- Aktor ma uproszczone `spell_ids` wyliczane z jego źródeł czarów, leczenia i akcji czarowych. Eksploracja sprawdza dodatkowo profil przygotowania dla czarów poziomu 1+, ale nie jest to jeszcze klasowo wyliczana pełna lista znanych/dostępnych czarów.
- Opcje wyzwań eksploracji mogą deklarować wymagania `requires.items`, `requires.spells` oraz `requires.ability_scores`; UI pokazuje, którzy aktorzy spełniają wymagania, a LLM dostaje te dane jako grounding.
- Opcje wyzwań eksploracji mogą deklarować `bonuses` z itemów lub czarów. Aktywne bonusy są dodawane do zwykłego testu d20 jako `RollModifier`, a UI pokazuje ich źródło przed rzutem.
- Bonus eksploracji z czaru ma `spell_level`: poziom `0` jest cantripem bez zużycia slotu, a poziom `1+` wymaga wolnego slotu i zużywa go po użyciu opcji.
- Item aktora może mieć stan `broken`; uszkodzony item pozostaje widoczny w inventory, ale nie spełnia `requires`, nie daje bonusów i ma `available=false`.
- Bonus eksploracji z itemu może deklarować `breakage` przy krytycznej porażce. Runtime nie losuje tego ukrycie: po naturalnej 1 UI prosi o k100, a wynik w progu oznacza `broken`.
- Bonus eksploracji może deklarować `consume`; po rozstrzygnięciu testu aktywny item z takim bonusem zmniejsza `quantity`.
- Wolne deklaracje eksploracji są porządkowane przez named `ExplorationMechanicId`, np. `single_actor_check`, `lead_with_help_check`, `group_check`, `use_item_check`, `use_spell_check`, `improvised_tool_check`. LLM wybiera mechanikę, ale walidacja i rozstrzygnięcie pozostają deterministyczne.
- Magiczny napój siły w MVP jest akcją walki pochodzącą z itemu aktora: zużywa akcję główną, zmniejsza `quantity` itemu o 1 i daje efekt `strength_potion` do początku następnej tury aktora.
- `strength_potion` daje premię do ataku i obrażeń tylko źródłom opartym o Siłę.
- Nie implementujemy jeszcze klasowo wyliczanych list czarów, profili casterów znanych czarów, zaawansowanych modyfikatorów testu koncentracji ani zaawansowanych efektów czarów poza obrażeniami/lekkim leczeniem i prostym buffem do ataku.
- Jawne obiekty sceny deklarują jawny `action_cost`: `action`, `bonus_action`, `reaction`, `object_interaction` albo `free`. `object_interaction` najpierw zużywa jedną darmową interakcję w turze, a po jej wykorzystaniu może zużyć akcję główną.
- Interakcje walki są data-driven: `SceneInteraction` może deklarować listę `conditions` oraz listę `effects`.
- Warunki interakcji MVP obejmują dostępną akcję, sąsiedztwo obiektu, stanie na obiekcie, sąsiedniego przeciwnika oraz wolne pole docelowe.
- Efekty interakcji MVP obejmują `grant_ac_bonus_until_move`, `move_actor_to_tile`, `grant_attack_bonus_while_on_object` i `grant_next_attack_penalty`.
- `Rozbity wóz` w `gate_skirmish` ma dwie interakcje opisane tym modelem: osłona `+2 AC` do opuszczenia pola oraz wejście na wóz dające `+2` do ataku, dopóki aktor stoi na polu wozu.
- `Rumowisko` w `gate_skirmish` jest jednocześnie trudnym terenem i obiektem interakcji: aktor stojący na rumowisku może użyć akcji `Sypnij gruzem`, żeby wymusić u najbliższego sąsiedniego przeciwnika rzut obronny na Zręczność ST 12; porażka daje `-2` do następnego ataku, sukces nie nakłada kary.
- Warunki interakcji są jawne w payloadzie UI, np. pozycja aktora przy obiekcie, wolne pole docelowe i dostępna akcja.
- Aktywne efekty walki zwracają do UI jednolity opis wartości i wygaśnięcia, np. `+2 AC | znika po ruchu z pola` albo `-2 do następnego ataku | znika po następnym ataku`.
- W runtime demo przeciwnik wykonuje automatyczny melee attack przez wstrzyknięty RNG.
- Jeśli przeciwnik musi się ruszyć przed atakiem, aplikacja pokazuje ścieżkę LED i wymaga kliknięcia pola docelowego po fizycznym przestawieniu figurki.
- Domyślny przeciwnik demo używa ataku `Szabla`, modyfikatora `+4` i obrażeń `1d6 + 2 slashing`.
- Walka kończy się, gdy żywa zostaje tylko strona bohaterów albo tylko strona przeciwników.
- Runtime może zatrzymać demo po limicie rund bez rozstrzygania zwycięzcy.
- Statystyki demo mogą pochodzić z lokalnego contentu JSON w `content/`.
- Lokalny content MVP nie jest pełnym SRD ani pełną bazą D&D 5e.
- Multi-actor MVP obsługuje wielu bohaterów i wielu przeciwników w jednej kolejce tur.
- Wszyscy aktorzy używają pierwszego ataku z contentu jako domyślnej akcji.
- Przeciwnicy wybierają najbliższy legalny cel; remis rozstrzyga pozycja i `id`.

Poza zakresem MVP:

- pełne reakcje,
- czary, area effects i złożone itemy,
- pełne zasady osłony dla ranged attacks,
- odporności i podatności,
- automatyczne trafienia krytyczne przeciw nieprzytomnemu celowi atakowanemu z 5 feet,
- destrukcja obiektów i przeszkód.
- pełne AI ruchu przeciwników,
- ruch w turze podczas multi-actor MVP,
- testy sporne, rzuty obronne i obrażenia obszarowe z interakcji sceny,
- przesuwanie obiektów sceny po planszy,
- konkretne bonus actions, konkretne reactions i multiattack.

Odstępstwa / decyzje planszowe:

- Profil death saves jest cechą aktora, a nie klasy ani frakcji; content MVP włącza go bohaterom i wyłącza zwykłym przeciwnikom.
- Obiekty atakowalne są przewidziane w modelu targetowania, ale pełny flow niszczenia obiektów zostaje później.
- Komunikat aplikacji i LED-y muszą być zsynchronizowane: legalne cele, wybrany cel, wynik ataku.
- W board-first MVP gracz nie wybiera najpierw akcji z globalnego menu: klika pole na planszy, a aplikacja buduje katalog wszystkich legalnych intencji dla tego pola lub aktora.
- Pierwsze kliknięcie pola pokazuje podgląd intencji, drugie kliknięcie tego samego pola potwierdza.
- Kliknięcie innego legalnego pola przed potwierdzeniem zmienia podgląd.
- Kliknięcie pola aktywnego aktora pokazuje podstawowe opcje aktora; w MVP obsługiwana jest opcja zakończenia tury.
- Zakończenie tury przed wykorzystaniem całego ruchu jest legalne; niewykorzystany ruch przepada na końcu tury.
- Przeciwnicy w MVP mogą wykonać ruch w stronę najbliższego celu, a potem zaatakować, jeśli cel stał się legalny.

- Ruch przeciwnika jest wizualizowany jako czerwona ścieżka i pomarańczowe pole docelowe.
- Pole może mieć wiele dostępnych intencji, np. przeciwnik stojący na obiekcie interaktywnym.
- W takim przypadku plansza pokazuje kolor `multi-option`, kliknięcie tego samego pola przełącza opcję, a Enter potwierdza aktualną opcję.
- Obiekty sceny mogą deklarować `blocks_movement`, `allow_interaction_when_occupied_by_enemy`, efekt interakcji `cover_bonus` oraz niezależne geometryczne `projectile_cover_bonus`.
- Jeśli cel ataku stoi na obiekcie z `cover_bonus`, runtime dodaje jawny modyfikator osłony do instrukcji rzutu ataku.
- W web UI walki efekty interakcji obiektu są przypięte do pozycji aktora: osłona wygasa po ruchu z pola, a premia z wozu wygasa po zejściu z pól wozu.
- W encounterze strażnicy przewrócona brama pozostaje nieinteraktywnym `blocking_terrain`: blokuje ruch i linię widzenia, ale nie generuje menu akcji.
- Rozbity wóz udostępnia pełnoakcyjne zajęcie osłony albo wejście na wolne pole wozu. Rumowisko udostępnia pełnoakcyjne sypnięcie gruzem tylko aktorowi stojącemu na rumowisku, gdy obok znajduje się przeciwnik.
- UI walki nie rozpoznaje już efektów wozu po ID interakcji; wykonuje znane prymitywy efektów z contentu.
- Zielone LED-y oznaczają legalne pola interakcji sceny; jeśli pole jest jednocześnie ruchem i interakcją, kliknięcie z dostępną akcją otwiera wybór interakcji.
- Interakcja przy przeciwniku może wywołać uproszczony atak okazyjny jako decyzję planszowego MVP.
- Pierwsza scena grywalna może zakończyć się przez spełnienie celu sceny, a nie tylko przez pokonanie wszystkich przeciwników.
- Wynik encountera ma jawny typ: `victory`, `defeat`, `objective_completed`,
  `retreat` albo `surrender`. Odwrót nie tworzy zwycięzcy, kapitulacja przyznaje
  zwycięstwo stronie przeciwnej, a wykonanie wszystkich aktywnych celów może
  zakończyć walkę mimo żywych przeciwników.
- Content triggera może definiować osobne `outcome_on_objective`,
  `outcome_on_retreat` i `outcome_on_surrender`. Brak wyniku celu używa wyniku
  zwycięstwa, a brak wyniku odwrotu lub kapitulacji używa wyniku porażki przed
  przejściem do neutralnego fallbacku runtime.
- Broń podniesiona z pola pozostaje niewyposażona. Menu własnego pola pokazuje osobne opcje dobycia, schowania i upuszczenia broni wraz z kosztem. Dobycie i schowanie są osobnymi interakcjami z obiektem: pierwsza w turze jest darmowa, druga wymaga akcji, a trzecia nie mieści się w zwykłej turze. Upuszczenie jest darmowe i pozostawia broń na aktualnym polu.
- Sloty `main_hand` i `off_hand` są jawnym, serializowanym stanem instancji przedmiotu przez `held_in`. UI pokazuje zawartość obu dłoni, liczbę wolnych rąk oraz rękę zarezerwowaną przez trwający Grapple.
- Ataki broni są katalogowane przez źródłowy item niezależnie od pierwotnego właściciela, dzięki czemu broń podniesiona od innego aktora zachowuje swoje akcje ataku po wyposażeniu.
- Kontekstowy katalog celu grupuje opcje jako ataki bronią, manewry, czary, przedmioty, wsparcie/leczenie, ekwipunek, akcje podstawowe i akcje tury. Każdy provider dostarcza tylko legalne opcje, a katalog gwarantuje stabilną kolejność i unikalne identyfikatory.
- Wszystkie legalne źródła ataku są widoczne równocześnie. Niewyposażona niesiona broń może udostępnić opcję „wyposaż i zaatakuj” tylko przy wolnej wymaganej dłoni; opcja zużywa darmową interakcję, a następnie przechodzi do zwykłego podglądu ataku. Zmiana wymagająca schowania trzymanej broni nie może zostać połączona z atakiem, ponieważ zużywa również akcję.
- Zwykły atak lekką bronią do walki wręcz trzymaną w jednej dłoni otwiera do końca tury bonusowy atak inną lekką bronią do walki wręcz trzymaną w przeciwnej dłoni. Trafienie pierwszym atakiem nie jest wymagane.
- Drugi atak zużywa akcję bonusową. Do rzutu ataku stosuje zwykłe modyfikatory, natomiast do obrażeń nie dodaje dodatniego modyfikatora cechy; ujemny modyfikator i premie niezależne od cechy pozostają. Stan triggera jest serializowany i zerowany wraz ze stanem następnej tury.
- Broń versatile ma równocześnie jawny wariant jednoręczny i oburęczny. Wariant oburęczny jest legalny tylko przy wolnej drugiej ręce, używa `versatile_damage_dice` i nie tworzy trwałego stanu chwytu między atakami. Ręka zarezerwowana przez Grapple blokuje ten wariant.
- Założona tarcza zajmuje jedną rękę i dodaje `+2` do efektywnego KP. Bazowe `Actor.ac` nie jest mutowane; ataki, podgląd celu i UI korzystają ze wspólnego `effective_armor_class()`.
- Założenie albo zdjęcie tarczy zużywa akcję. Aktor może korzystać najwyżej z jednej tarczy, a zajęta dłoń automatycznie blokuje niezgodne warianty Two-Weapon Fighting, versatile i Grapple.
- Pancerz korpusu ma kategorię `light`, `medium` albo `heavy`. Lekki dodaje pełny modyfikator Zręczności do bazowego KP, średni ogranicza go do `+2`, a ciężki używa limitu `0`. Założony pancerz zastępuje bazowe `Actor.ac`; premia tarczy jest dodawana później.
- Aktor może mieć założony najwyżej jeden pancerz korpusu. Zakładanie trwa odpowiednio 1, 5 albo 10 minut, a zdejmowanie 1, 1 albo 5 minut dla pancerza lekkiego, średniego i ciężkiego. Operacje są dostępne w spokojnej eksploracji, nie podczas encountera.
- Niespełnienie wymagania Siły ciężkiego pancerza nie blokuje jego noszenia, lecz zmniejsza szybkość o 10 ft. Flaga pancerza `stealth_disadvantage` daje utrudnienie do testów Dexterity (Stealth), w tym Hide, skradania przed walką i authored testów eksploracyjnych.
- Pełne zasady 2014 pozwalają nosić pancerz lub tarczę bez biegłości kosztem zestawu kar obejmujących testy, save'y, ataki i czary. MVP odrzuca ich założenie bez wymaganej biegłości, żeby nie tworzyć częściowo zaimplementowanego stanu.
- Akcja `targeted_item_effect` jest definiowana w contentowym itemie, ale jej `effect_kind` musi należeć do jawnie obsługiwanych efektów. Runtime sprawdza dostępność przedmiotu, frakcję i zasięg celu, a akcję tury oraz ilość przedmiotu zużywa dopiero podczas wykonania. `apply_condition` nakłada ustrukturyzowany warunek z opcjonalnym save-at-start/save-at-end; odporność celu blokuje aplikację bez zużycia niejawnych wyjątków.
- `Poisoned` daje utrudnienie do ataków i testów cech. `Restrained` zeruje szybkość, daje utrudnienie do ataków i Dex save'ów oraz przewagę atakom przeciw celowi. Przewaga i utrudnienie nadal znoszą się według wspólnego kontraktu d20.
- Bohater wykonuje jawny fizyczny rzut kończący warunek przed zakończeniem właściwej granicy tury. Przeciwnik wykonuje ten rzut automatycznie i zapisuje wynik w historii sesji. Warunki bez save'a mogą wygasać automatycznie na wskazanej granicy tury.
- Aura aktora jest definicją contentową, a jej aktualny zasięg jest zawsze wyliczany z pól źródła i celu. Pokonane źródło nie emituje aury. Pierwszy obsługiwany efekt, `saving_throw_bonus`, obejmuje wskazaną relację frakcji w promieniu będącym wielokrotnością 5 ft.
- Identyczne aury używają wspólnego klucza stackowania, dlatego nie sumują się; działa najsilniejszy modyfikator. UI pokazuje źródło, promień, wartość i liczbę aktualnie objętych aktorów. Referencyjna `Aura ochronnego relikwiarza` jest fixture'em mechaniki, a nie implementacją klasy Kapłana.
- Trigger cechy aktora jest contentową definicją stabilnego `event_type`, skutku i wartości. Schemat rozpoznaje `attack_hit`, `damage_taken`, `actor_moved`, granice tury, odpoczynki i koniec encountera; runtime używa istniejącego `EffectEvent`, a nie osobnego event busa.
- Pierwszy wykonawca `grant_temp_hp` nigdy nie dodaje temporary HP do istniejących — zachowuje wyższą wartość. Pokonany aktor nie aktywuje triggerów. Aktualny vertical slice emituje triggery początku i końca tury; pozostałe emitery są jawnie odłożone.
- Interakcja z jawnym obiektem jest akcją główną: kliknięcie obiektu pokazuje podgląd, drugie kliknięcie potwierdza i zużywa akcję.
- Interakcja może mieć test cechy `d20`; aplikacja pokazuje cechę, skill, ST, aktywne modyfikatory i końcowy modyfikator przed wpisaniem wyniku.
- Wynik eksploracyjnej interakcji może ustawić flagę sceny, np. `crate_secured` albo `crate_trap_missed`.
- Objective może używać warunku `flag_equals`, więc scena może zakończyć się dopiero po konkretnym skutku interakcji, a nie samym kliknięciu obiektu.
- Setup startowy pokazuje pola, na których gracze mogą ustawić figurki, ale MVP nie skanuje automatycznie poprawności ustawienia.
- Ranged MVP pokazuje w preview half/three-quarters cover, źródło osłony, efektywne AC oraz utrudnienie za strzał w zwarciu. Ten sam kontrakt obowiązuje ataki graczy i automatyczne ataki przeciwników.
- Uproszczony LOS i osłona używają jednego promienia Bresenhama. Model nie rozstrzyga jeszcze rogów, części miniaturek, wysokości ani wielu promieni do różnych części pola.

Testy:

- `tests/unit/test_combat_targets.py`
- `tests/unit/test_attack_targets.py`
- `tests/unit/test_attack_flow.py`
- `tests/unit/test_attack_resolution.py`
- `tests/unit/test_line_of_sight.py`
- `tests/unit/test_damage.py`
- `tests/unit/test_attack_led_feedback.py`
- `tests/unit/test_demo_mini_combat.py`
- `tests/unit/test_combat_session.py`
- `tests/unit/test_turn_intent.py`
- `tests/unit/test_enemy_auto_movement.py`
- `tests/unit/test_enemy_auto_attack.py`
- `tests/unit/test_demo_mini_combat_loop.py`
- `tests/unit/test_scenario_loader.py`
- `tests/unit/test_scenario_content_files.py`
- `tests/unit/test_scene_setup.py`
- `tests/unit/test_scene_objectives.py`
- `tests/unit/test_scene_flags.py`
- `tests/unit/test_scene_interactions.py`
- `tests/unit/test_interaction_intent.py`
- `tests/unit/test_turn_led_feedback.py`
- `tests/unit/test_exploration_ui_session.py`

## Zero HP, Rzuty Śmierci I Stabilizacja

Status: implemented

Źródło:

- D&D 5e 2014 / SRD 5.1, zasady dropping to 0 hit points i death saving throws.

Implementacja MVP:

- Aktor z `uses_death_saves=True` przy 0 HP jest nieprzytomny, nie może działać, poruszać się ani używać reakcji, ale pozostaje w kolejce inicjatywy.
- Na początku swojej tury wykonuje jawny rzut d20 bez modyfikatora. Wynik 10–20 daje sukces, 1–9 porażkę; trzy sukcesy stabilizują, a trzy porażki oznaczają śmierć.
- Naturalne 1 daje dwie porażki. Naturalne 20 przywraca 1 HP, zeruje liczniki i pozwala rozegrać bieżącą turę.
- Stabilizacja zeruje sukcesy i porażki. Otrzymanie obrażeń przy 0 HP kończy stabilizację i daje jedną porażkę albo dwie, jeśli obrażenia pochodzą z trafienia krytycznego.
- Obrażenia pozostałe po zejściu do 0 HP zabijają natychmiast, jeśli są co najmniej równe maksymalnym HP aktora. Taka sama granica obowiązuje dla pojedynczej porcji obrażeń otrzymanej już przy 0 HP.
- Dowolne leczenie podnoszące HP powyżej 0 zeruje stan rzutów śmierci i przywraca przytomność.
- Stabilny bohater nie wykonuje tur. Jeśli po jednej stronie pozostają wyłącznie stabilne lub martwe postacie, walka kończy się na korzyść strony zdolnej działać.
- Stan jest widoczny w UI, zapisywany w snapshotach i logowany po każdym rzucie.
- Ataki przeciw nieprzytomnemu aktorowi mają przewagę. Trafienie wykonane przez atakującego znajdującego się nie dalej niż 5 feet od celu jest krytyczne; wpisane obrażenia krytyczne powodują przy 0 HP dwie porażki rzutu śmierci.
- Stabilizacja w walce zużywa akcję i wymaga sąsiedniego, nieprzytomnego sojusznika. Test Wisdom (Medicine) ma ST 10; sukces stabilizuje, a porażka nadal zużywa akcję.
- Jedno użycie zestawu uzdrowiciela stabilizuje bez rzutu. Liczba użyć jest przechowywana jako `quantity` przedmiotu i zmniejszana deterministycznie.
- Medicine korzysta ze wspólnego profilu skilli i dolicza proficiency albo expertise stabilizującego aktora.
- Przy pierwszym zejściu z dodatnich HP do 0 aktor upuszcza wszystkie dostępne, wyposażone elementy inventory typu `weapon`. Broń otrzymuje osobny identyfikator, pozycję aktora i numer rundy, a jej wpis w inventory staje się niewyposażony.
- Upuszczona broń jest widoczna w UI, zachowywana w snapshotcie i nie może być użyta po odzyskaniu przytomności, dopóki pozostaje niewyposażona.
- Pierwsze proste podniesienie przedmiotu w turze zużywa darmową interakcję z obiektem. Kolejna taka interakcja zużywa akcję, jeśli jest jeszcze dostępna.
- Podniesienie wymaga stania na polu broni. Menu może połączyć dojście i podniesienie w jedną intencję, ale ruch oraz ewentualne ataki okazyjne są rozstrzygane przed zmianą ekwipunku.
- Podniesiona broń znika z pola, przechodzi do ekwipunku podnoszącego i pozostaje niewyposażona.

Poza zakresem MVP:

- odzyskanie 1 HP po `1d4` godzinach stabilności,
- automatyczne niezdawanie rzutów obronnych na Strength i Dexterity,
- przekazywanie i wyposażanie broni,
- rozróżnienie jednej ręki, dwóch rąk, tarczy oraz innych trzymanych przedmiotów,
- osobna reprezentacja prone,

Testy:

- `tests/unit/test_death_saves.py`
- `tests/unit/test_damage.py`
- `tests/unit/test_combat_session.py`
- `tests/unit/test_exploration_ui_session.py`
- `tests/unit/test_session_snapshot.py`
- `tests/unit/test_attack_resolution.py`
- `tests/unit/test_scene_interactions.py`
- `tests/unit/test_combat_stabilization_flow.py`

## Eksploracja

Status: partial

Implementacja MVP:

- Eksploracja jest osobnym trybem sceny, niezależnym od encountera.
- Nie ma inicjatywy, tur walki ani indywidualnego ruchu bohaterów.
- Drużyna ma wspólny pionek i aktualną strefę.
- Setup eksploracji pokazuje jawne strefy/lokacje bez wymuszania kliknięcia potwierdzającego.
- Przed startem eksploracji web UI może przeprowadzić setup jawnych elementów mapy z `environment`, np. blokad, rumowisk i obiektów sceny.
- Ta sama mapa `environment` może być używana w eksploracji i w encounterach, żeby fizyczne przeszkody nie zmieniały się między trybami.
- Fizyczne jawne elementy sceny, np. NPC, obiekty albo markery, mogą wymagać rozstawienia przez `requires_setup`; wtedy są prowadzone batchami i potwierdzane kliknięciem.
- Ukryte i warunkowe elementy nie są zdradzane w setupie.
- Kliknięcie innej strefy tworzy podgląd przejścia, a drugie kliknięcie tej samej strefy potwierdza.
- Domyślny widok eksploracji pokazuje tylko główne punkty dostępnych lokacji, nie całe strefy.
- Kliknięcie aktualnego punktu głównego pokazuje wszystkie dostępne opcje jako kolorowe menu planszowe.
- Kliknięcie pola menu wybiera konkretną opcję; `Wycofaj` zamyka menu.
- `Rozejrzyj się po okolicy` dopiero wtedy podświetla całą strefę i pozwala klikać jej kafle.
- `Zbadaj obszar` dotyczy aktualnej strefy, może być wykonane raz na strefę i bierze najwyższy wynik z testu drużyny.
- Testy eksploracyjne mają jawny plan: kto rzuca (`single_actor`, `lead_with_help`, `whole_party`, `selected_actors`), jak agregujemy wynik (`lead_result`, `highest`, `lowest`, `majority`, `all_must_succeed`, `any_success`, `sum_progress`) i kogo dotyczą konsekwencje (`lead_actor`, `helper_actor`, `failed_actors`, `whole_party`, `scene`, `npc`, `object`).
- Testy eksploracyjne mogą mieć kontrolowane modyfikatory sytuacyjne oparte o opis scenariusza, lokacji, aktywnego wyzwania/obiektu, dynamiczny stan gry albo deklarację gracza.
- Modyfikator sytuacyjny musi mieć etykietę, źródło, powód i efekt mechaniczny: premię/karę od -2 do +2 albo `roll_mode` równy `advantage`/`disadvantage`.
- Kilka źródeł przewagi i utrudnienia w eksploracji stosuje standardowe znoszenie D&D 5e: jeśli występuje przewaga i utrudnienie, rzut wraca do `normal`.
- `improvised_tool_check` obsługuje prowizoryczne użycie elementu sceny jako narzędzia. Taki element musi mieć źródło i uzasadnienie z kontekstu sceny albo deklaracji gracza, daje tylko mały jednorazowy modyfikator i nie trafia do inventory.
- Improwizowane narzędzie jest pokazywane w preview decyzji MG i może zostać poprawione albo odrzucone przed rzutem.
- Dla wspólnego szukania domyślnie pasuje `whole_party/highest` albo `any_success`; dla skradania całej drużyny pasuje `whole_party/lowest`; dla działań prowadzonych przez jedną postać pasuje `single_actor` albo `lead_with_help` z `lead_result`.
- Sukces badania może ujawnić ukryty punkt i ustawić flagę sceny.
- Eksploracyjne przeszkody docelowo nie powinny być twardymi blokadami rzutu.
- Domyślny model eksploracyjnego testu to `fail-forward`: porażka zmienia koszt, ryzyko albo komplikację, ale nie powinna zatrzymywać całej sceny.
- Wyzwania eksploracyjne mają model postępu, np. `progress_required`, `current_progress`, opcje działań, postęp na sukcesie, postęp na porażce i konsekwencje. Pierwszy zaimplementowany slice to zamknięta brama w `abandoned_watchtower`.
- Scenariusz eksploracyjny może mieć kilka wyzwań w kolejnych strefach. `abandoned_watchtower` ma teraz bramę oraz przeszukanie dziedzińca po jej sforsowaniu.
- Ukończone wyzwanie może ujawnić ukryty punkt eksploracji przez `reveals_on_complete`. W `abandoned_watchtower` przeszukanie dziedzińca ujawnia punkt `Ranny zwiadowca`, który ma pierwszą interakcję NPC przez LLM.
- Interakcje NPC są content-driven: opis publiczny, kontekst dla MG, osobowość, stan, capabilities, zablokowane informacje i policy testów/flag są definiowane przy punkcie eksploracji w scenariuszu. LLM może narracyjnie odgrywać NPC i proponować test/flagę, ale deterministic runtime waliduje dozwolone akcje, ST, skille, flagi i ujawniane informacje.
- Kluczowe informacje NPC mogą być zablokowane przez `reveal_if_flags`; runtime nie ujawnia ich tylko dlatego, że LLM je wymienił. Najpierw musi zostać ustawiona wymagana flaga, np. po uspokojeniu albo opatrzeniu rannego zwiadowcy.
- Kolejny model interakcji powinien przejść z ad hoc `allowed_actions` na globalny katalog intencji oraz lokalne `intent_permissions`. Globalne intencje, np. `social`, `information`, `medical`, `theft`, `harm`, `force`, `stealth`, `crafting`, `search`, `magic`, `trade`, `gambling`, powinny być zdefiniowane w contentcie wspólnym, a obiekty/NPC/lokacje powinny tylko gate'ować je statusami typu `allowed`, `allowed_with_consequence`, `blocked`, `locked`, `hidden`.
- Intencje mogą mieć parametry, limity i branch'e, np. `gambling.stake_gold`. LLM może wyekstrahować `intent` i parametry z deklaracji gracza, ale runtime musi egzekwować limity i wybrać branch z contentu.
- Każdy skutek zmieniający stan gry musi być znanym prymitywem mechanicznym, np. `set_flag`, `grant_resource`, `remove_resource`, `reveal_information`, `start_challenge`, `offer_trade`, `trigger_encounter`, `npc_refuses`, `change_relationship`, `add_complication`, `add_noise`. Scenariusze powinny składać lokalne zachowanie z tych prymitywów zamiast wymagać osobnego kodu dla każdego pomysłu.
- Globalne katalogi intencji, efektów i warunków powinny docelowo trafić do `content/llm/`, np. `intent_catalog.json`, `effect_catalog.json`, `condition_catalog.json`. Kod powinien zawierać parser/walidator i wykonawców znanych prymitywów, a nie szczegółowy content scenariusza.
- Opcje wyzwań mogą mieć tagi zasobów/narzędzi/czarów, np. `climbing`, `crowbar`, `quiet`; pasujące itemy mogą dawać premię, przewagę albo łagodzić hałas/komplikacje. Pełny ekwipunek pozostaje poza MVP.
- Proste opcje eksploracyjne typu `message` mogą ustawiać flagi sceny. Dzięki temu rozmowa, odczytanie tablicy albo obejrzenie punktu zainteresowania może domknąć objective bez sztucznego testu cechy.
- `village_square_mvp` jest pierwszą mini-sceną eksploracji społecznej: kilka jawnych lokacji, setup jawnych NPC/obiektów, ukryty punkt i objective zależne od flagi.
- LLM może analizować i klasyfikować kreatywne deklaracje graczy do ustrukturyzowanych propozycji challenge, ale nie może samodzielnie zmieniać zasad ani stanu gry.
- Jeśli challenge posiada guarded flow graph, cel deklaracji musi być wybrany
  przed opisaniem metody. Aktywna krawędź grafu jest autorytatywna dla profilu
  opcji, uczestników, ST i skutków; tagi propozycji LLM nie mogą przełączyć
  rozstrzygnięcia na inny cel.
- Główne web UI i terminalowy `demo_exploration_scene` korzystają z tego samego
  `ExplorationInteractionFlowService`. Tryb nieinteraktywny terminala wymaga
  `--goal-id`, gdy aktywnych jest kilka celów; cel nieaktywny jest odrzucany
  przed wywołaniem analyzer/classifiera.
- Flow NPC może wystawić inne cele w zależności od flag świata, niezależnie od
  opisowej odpowiedzi modelu. W `village_square_mvp` negocjacja zaliczki jest
  dostępna tylko przed zdobyciem tropu o strażnicy, pytania informacyjne
  pozostają dostępne po jego zdobyciu, a `elder_refuses_party` aktywuje
  terminalny węzeł bez dalszych celów.
- Jednorazowa informacja NPC jest modelowana jako cel dostępny tylko w węźle
  sprzed ustawienia flagi wiedzy. Karczmarz Olan nadaje autorskie
  `tavern_rumor_heard` i `quest_hook_found`; runtime usuwa efekty zaproponowane
  przez LLM, po czym flow ukrywa wykorzystany cel plotki i nadal wystawia zwykłą
  rozmowę.
- Zdobycie tropu nie kończy już automatycznie mini-sceny wioski. Autorski flow
  rozdziela `quest_hook_found`, `quest_accepted` oraz
  `ready_for_watchtower`; objective kończy się dopiero po świadomym przyjęciu
  zadania i potwierdzeniu gotowości.
- `ScenarioContinuation` jest typowanym wyjściem ze sceny. Loader sprawdza
  ścieżkę oraz identyfikator scenariusza docelowego, a runtime wymaga wszystkich
  flag i właściwej strefy wyjścia. Przejście wygasza efekty końca scenariusza,
  zapisuje pełny snapshot źródłowy i emituje jawny handoff. Łączenie tego
  snapshotu ze stanem następnej sceny pozostaje odpowiedzialnością przyszłego
  modelu kampanii, zamiast niejawnego nadpisywania różniących się definicji
  postaci.
- Continuation może mieć uporządkowane outcome branches. Pierwsza gałąź pasująca
  do końcowych flag i wyniku nawigacji wygrywa; ostatnia musi być bezwarunkowym
  fallbackiem. Wynik ma jawny typ `success`, `partial_success` albo
  `fail_forward`, opis dla graczy i wyłącznie walidowane efekty `set_flag` dla
  sceny docelowej.
- Handoff zawiera statusy celów źródłowych i tylko flagi wskazane w
  `propagate_flags`. Efekt gałęzi o tym samym kluczu ma pierwszeństwo przed
  propagowaną wartością. Zastosowanie efektów przy utworzeniu stanu celu należy
  do warstwy kampanii M9.
- Główny widok aktywnej eksploracji jest rozmową z MG. Obraz i publiczny opis sceny są pierwszą wiadomością, a gotowe listy inspiracji, opcji i ukrytych ryzyk nie są wystawiane w player API.
- Pytania graczy o otoczenie są odpowiedziami strukturalnymi typu `observation`, `clarification`, `gentle_hint`, `strong_hint`, `requires_check` albo `impossible`. Naturalny tekst MG musi wskazywać identyfikatory faktów, na których został oparty, a runtime odrzuca nieznane fakty.
- Jawne obiekty i ich właściwości mogą być opisane bez rzutu. Gdy odpowiedź wymaga niepewnej albo ukrytej obserwacji, MG nie ujawnia wyniku, tylko proponuje dalszą deklarację przez `requires_check`.
- Podpowiedzi mają progresję 1–3: naprowadzenie, użyteczny kierunek i konkretne rozwiązanie. Poziom oraz ujawnione fakty są zapisywane razem z historią rozmowy per instancja i przechodzą przez snapshot.
- LLM MVP obsługuje opcjonalnych providerów Groq i Gemini oraz ma dwa kroki: analyzer deklaracji oraz classifier mechaniki challenge. Gemini jest domyślnym providerem dla trybu freeform, a zwykła eksploracja bez freeform nadal nie odpala LLM.
- Prompt LLM składa się z centralnie ładowanych plików w `content/prompts/` oraz warstw kontekstu: scenariusz, lokacja, challenge, dynamiczny stan gry i historia prób.
- Ogólne słowniki używane przez LLM, np. cechy/skille D&D 5e i pilnowane aliasy zasobów, są trzymane w `content/llm/`, a nie zaszyte bezpośrednio w walidatorze.
- `llm_context` może opisywać dostępne materiały, zakazane założenia, sensowne podejścia, niemożliwe podejścia i ryzyka.
- `llm_policy` przy challenge definiuje lokalny słownik mechaniczny dla LLM: lokalne skille, tagi podejść, komplikacje, dozwolone konsekwencje, zakres ST, zakres postępu, dozwolone typy przygotowania, zakresy efektów przygotowania, whitelisty zasobów/opcji i limit zasobów.
- Jeśli challenge ma `dc_policy`, LLM musi zwrócić `difficulty_tier`, `difficulty_reason` i `dc`; silnik waliduje, że `dc` jest dokładnie wartością tieru z contentu.
- `dc_policy` jest definiowane dla przeszkody/scenariusza, nie dla z góry wymyślonych rozwiązań. LLM ocenia trudność deklaracji graczy względem profilu przeszkody.
- Zasób zaproponowany przez LLM działa mechanicznie tylko wtedy, gdy drużyna go posiada i `bonus_tags` zasobu przecinają się z tagami podejścia.
- Zasób sceny może deklarować `consume_on_use`. Taki zasób jest usuwany przez prymityw `remove_resource` dopiero po wykonaniu rzutu, niezależnie od wyniku; odrzucenie lub anulowanie propozycji przed rzutem niczego nie zużywa.
- Premia, przewaga, redukcja hałasu, chronione komplikacje i koszt zużycia zasobu muszą być widoczne w korekcie MG oraz w planie rzutu. MG może przed akceptacją wybrać inny pasujący posiadany zasób albo zrezygnować z zasobu.
- Analyzer deklaracji zwraca `action_flow`, zadeklarowane zasoby, istniejące resource ids, założone nowe fakty i brakujące wymagania. Jeśli zasób nie istnieje w inventory albo materiałach sceny, runtime nie wykonuje rzutu.
- Freeform challenge MVP rozróżnia `challenge_attempt`, `preparation` i `combined`.
- Przygotowanie może utworzyć krótkotrwały efekt `modifier`, `reduce_negative_effect`, `advantage`, `disadvantage`, `effect_boost`, `grant_resource` albo `unlock_option` z `duration=next_attempt`, ale tylko jeśli typ jest dopuszczony w `llm_policy`.
- `grant_resource` i `unlock_option` nie tworzą nowych elementów świata. Mogą wskazywać tylko istniejące resource/option ids z contentu i tylko jeśli są na whitelistach policy.
- Efekt przygotowania działa tylko wtedy, gdy `target_tags` przecinają się z tagami następnej próby. Po użyciu wygasa i jest zapisywany w obserwacji sesji.
- Propozycja LLM może utworzyć tymczasową opcję `gm_generated`, która jest rozstrzygana przez zwykły deterministic `resolve_challenge_option`.
- Propozycja LLM może dodać maksymalnie trzy modyfikatory sytuacyjne do bieżącego rzutu, ale walidator odrzuca wpisy bez realnego efektu albo bez źródła/powodu.
- Propozycja LLM może użyć `improvised_tool_check` tylko razem z payloadem `improvised_tool`; walidator odrzuca payload improwizowanego narzędzia przy innych mechanikach.
- Propozycja LLM musi zostać zaakceptowana przed rzutem; odrzucenie interpretacji nie zmienia stanu gry.
- Przed akceptacją runtime pokazuje preview konsekwencji: critical success, success, failure i critical failure, razem z ST, tierem trudności, postępem, hałasem, komplikacjami i aktywnymi przygotowaniami.
- Terminalowy flow akceptacji interpretacji używa `+` do akceptacji, `-` do odrzucenia i korekty, `?` do wyjaśnienia mechanicznego oraz `r` do reinterpretacji tej samej deklaracji bez wpisywania nowej.
- Wyjaśnienie interpretacji nie wykonuje rzutu i nie zmienia stanu gry.
- Historia prób challenge jest częścią deterministycznego stanu eksploracji i trafia do payloadu LLM.
- Opcja wyzwania może uruchomić data-driven hazard po porażce albo krytycznej porażce. Hazard zatrzymuje flow na jawny fizyczny saving throw, rozstrzyga typowane obrażenia i wybiera osobne `success_effects` albo `failure_effects`.
- Skutki hazardu korzystają ze znanych prymitywów eksploracji (`set_flag`, `add_noise`, `add_complication`, `move_party`) albo nakładają wspólny stan aktora. Pierwszy pionowy slice to `Prone` po nieudanym Dexterity save przy upadku z bramy.
- `Prone` powstałe w eksploracji jest jawne, zapisywane w snapshotcie i przechodzi do encountera. Poza inicjatywą gracz może po prostu zadeklarować wstanie; w UI jest to jawna akcja bez kosztu ruchu. W walce obowiązuje zwykły koszt wstania.
- Pułapka eksploracyjna jest contentem z trwałym stanem `hidden`, `revealed`, `disarmed`, `bypassed` albo `triggered`. Wykrycie korzysta z istniejącego systemu obserwacji, a mechaniczny efekt `reveal_trap` ujawnia pułapkę dopiero po osiągnięciu progu.
- Ujawniona pułapka może oferować data-driven test rozbrojenia, test ominięcia albo świadome uruchomienie. Nieudane rozbrojenie lub ominięcie i scenariuszowy trigger przechodzą do wspólnego hazardu z fizycznym saving throwem.
- Referencyjna linka alarmowa przy bramie dodaje hałas zamiast obrażeń. Dzięki temu stan pułapki wpływa na istniejące reguły rozpoczęcia encounteru bez osobnego systemu zaskoczenia.
- Odrzucone lub niejasne deklaracje tworzą lokalny `declaration_thread` dla aktywnego challenge. Dzięki temu korekta gracza może odnosić się do poprzedniej deklaracji, ale nie tworzymy jeszcze globalnego czatu całej kampanii.
- `gm_classifier.py` zawiera mechanikę integracji, parsowania i walidacji. Content konkretnej przeszkody powinien pochodzić z `llm_policy` oraz `llm_context`; domyślna policy w kodzie jest celowo minimalna, żeby nie przemycać szczegółowego contentu poza scenariuszem.

## Ograniczone użycia i Recharge

- Ograniczone użycie nie posiada osobnego licznika w definicji ataku. Atak wskazuje `resource_pool_id` oraz koszt, a stan pozostaje w istniejącym `ActorResourcePool`.
- Akcja lub atak zużywa zasób w momencie zatwierdzenia użycia, także gdy późniejszy attack roll pudłuje. Brak zasobu blokuje źródło przed zużyciem ekonomii tury.
- `RecoveryPeriod.SHORT_REST` oraz `LONG_REST` pozostają jedyną regułą odnowienia odpoczynkowego. `ResourceRechargeRule` jest niezależną regułą początku tury dla zdolności w stylu potworowego `Recharge 5–6`.
- Recharge wykonuje jawny, deterministycznie wstrzykiwany rzut po rozpoczęciu tury, przed triggerami `turn_start`. Sukces odnawia pulę do maksimum; pełna pula nie wykonuje rzutu.
- Runtime zapisuje wynik recharge w historii sesji i pokazuje graczom wynik, próg oraz aktualną dostępność. Snapshot przechowuje zarówno bieżącą wartość puli, jak i definicję recharge.

## Ogólny mechanizm cech

- `FeatureDefinition` nie wprowadza osobnego wykonawcy zasad. Składa istniejące zasoby, ataki, akcje, triggery i aury, które nadal rozstrzygają ich właściwe deterministyczne resolvery.
- Aktor przechowuje lekki `FeatureGrant` z identyfikatorem cechy, źródłem i listą przyznanych prymitywów. Dzięki temu runtime i UI potrafią wyjaśnić pochodzenie mechaniki bez sprawdzania klasy lub rodzaju potwora.
- Loader odrzuca powtórzone cechy oraz kolizje identyfikatorów między bazowym aktorem i grantami. Cecha nie może być pustym opisem bez mechanicznego grantu.
- Snapshot zachowuje grant i aktualny stan przyznanych prymitywów; definicja pozostaje wersjonowanym contentem. Mechanizm jest fundamentem dla przyszłych ras, klas, featów i magicznych przedmiotów, ale sam ich jeszcze nie implementuje.

## Ekonomia przedmiotów i łup

- Portfel aktora przechowuje osobne, nieujemne ilości `cp`, `sp`, `ep`, `gp` i `pp`.
  Wartość porównawcza jest liczona w miedzi: `sp=10`, `ep=50`, `gp=100`,
  `pp=1000 cp`.
- Każde 50 monet waży 1 lb. Masa inventory to suma `weight_lb × quantity`;
  standardowy udźwig wynosi `Strength × 15 lb`. Ten etap nie włącza wariantowych
  progów encumbrance ani kar do szybkości.
- Łup jest neutralnym `LootBundle` z inventory i portfelem. Pokonany aktor jest
  pierwszym adapterem; ten sam kontrakt może obsłużyć znalezione zwłoki i skrzynie.
- W walce przeszukanie pokonanego przeciwnika wymaga stania w zasięgu 5 ft i zużywa
  akcję. Po walce zebranie łupu nie ma kosztu akcji.
- Menu pozwala zabrać cały pakiet, cały stos przedmiotu, wszystkie monety albo
  wybraną liczbę sztuk ze stosu i wybranego nominału. Kontrolka pokazuje masę
  wybranej części oraz pozostały po transferze udźwig; dotyczy to również
  odzyskanej amunicji, mikstur i materiałów.
- Każdy transfer jest atomowy i zostaje odrzucony, jeśli wybrana część przekroczyłaby
  udźwig albo dostępną liczbę. Przy błędzie menu pozostaje otwarte, a akcja nie jest
  wydawana. Niewybrane przedmioty oraz monety pozostają w źródle i są zapisywane
  jako zwykły stan aktora lub pakietu pola walki.
- Wyposażone bronie upuszczone przy 0 HP pozostają osobnymi obiektami pola i nie są
  duplikowane w pakiecie łupu. Nieprzenośne, zepsute i nadal wyposażone przedmioty
  również nie wchodzą do bieżącego transferu.
- Kupiec jest stanem scenariusza z własnym inventory, portfelem i procentem odkupu.
  Zakup używa katalogowej `value_cp`, a sprzedaż ceny
  `floor(value_cp × buyback_percent / 100)`; wartość zerowa i wynik poniżej `1 cp`
  wykluczają przedmiot z handlu.
- Kupno i sprzedaż dopuszczają część stosu. Resolver przed zatwierdzeniem sprawdza
  dostępny towar, monety kupującego, monety kupca oraz udźwig postaci. Transakcja
  jest atomowa: błąd nie zmienia żadnej strony.
- Kupiec odkupuje wyłącznie dostępne, przenośne i niewyposażone przedmioty. Portfele
  są po transakcji normalizowane do nominałów `pp/gp/sp/cp`, więc wydawanie reszty
  nie zależy od fizycznego zapasu konkretnego nominału.
- Handel jest dostępny tylko w lokacji przypisanej do kupca, poza aktywną walką,
  oczekującym encounterem i nierozstrzygniętą decyzją. `village_square_mvp`
  stanowi pierwszy fixture pełnego przepływu content–UI–snapshot.

## Amunicja i loading

- Źródło ataku dystansowego może wymagać stabilnego `ammunition_type`. Inventory
  spełnia wymaganie sumą dostępnych stosów tego typu, niezależnie od ich ID.
- Jedna sztuka amunicji jest zużywana przy faktycznym wykonaniu ataku, również przy
  pudle. Sam wybór źródła/celu i anulowanie podglądu niczego nie zużywają.
- Brak kompatybilnej amunicji blokuje atak gracza, reakcję i atak AI przed wydaniem
  odpowiedniej akcji albo reakcji.
- Właściwość `loading` ogranicza broń do jednego strzału w ramach Action niezależnie
  od `attacks_per_action`; nie blokuje osobnego strzału z reakcji.
- Referencyjna kusza wymaga `bolt`, a scenariuszowi użytkownicy zaczynają z 20
  bełtami. Pozostałe bełty są zwykłym, ważonym i lootowalnym inventory.
- Każdy faktycznie wystrzelony pocisk jest zapisywany w rejestrze bieżącego
  encountera wraz z frakcją strzelca i pełnymi metadanymi stosu. Rejestr obejmuje
  ataki zwykłe, AI i reakcje oraz jest częścią snapshotu.
- Po zwycięstwie drużyny można poświęcić minutę na przeszukanie pola walki i
  odzyskać połowę amunicji wystrzelonej przez bohaterów, osobno dla każdego typu,
  z zaokrągleniem w dół. Odzysk tworzy zwykły, trwały `LootBundle` na polu
  pokonanego przeciwnika; można zebrać cały pakiet albo pojedynczy stos.
- Amunicja przeciwników nie zwiększa odzysku drużyny. Odwrót, kapitulacja i
  porażka nie tworzą stosu odzyskanej amunicji, ponieważ drużyna nie kontroluje
  pola walki.

## Ładunki przedmiotów

- Instancja przedmiotu może mieć niestosowalną pulę `charges_current` /
  `charges_maximum`. Akcja z dodatnim `charge_cost` sprawdza i wydaje tę pulę;
  koszt `0` zachowuje dotychczasowe zużycie jednej sztuki consumable.
- Ładunek i koszt ekonomii tury są wydawane dopiero przy wykonaniu akcji. Samo
  otwarcie menu, wskazanie celu albo anulowanie nie zmienia stanu.
- Wyczerpana pula blokuje akcję przed wydaniem Action. Przedmiot pozostaje w
  inventory z ilością `1`, dzięki czemu może później odzyskać ładunki.
- `charges_recovery` może wskazać short rest, long rest albo brak recovery.
  Brak kości odnawia pulę do maksimum; formuła `NdM` z modyfikatorem korzysta
  wyłącznie ze wstrzykniętego RNG i ogranicza wynik do maksimum. Long rest
  obejmuje także przedmioty odnawiane przy short rest.
- Referencyjna Różdżka oplątania wydaje 1 z 7 ładunków, aby nałożyć Restrained
  po nieudanym Dex save ST 13, i odzyskuje `1d6+1` po long rest. Stan jest
  widoczny w UI i zachowywany w snapshotcie v9.

## Attunement magicznych przedmiotów

- Przedmiot może deklarować `requires_attunement`. Jego instancja przechowuje
  bieżące `attuned`; zwykłe przedmioty nie mogą ustawić tego stanu.
- Bohater może utrzymywać najwyżej trzy dostrojone przedmioty. Podczas jednego
  ukończonego short resta może dostroić albo dobrowolnie odstroić najwyżej jeden.
  Wspólny odpoczynek drużyny pozwala każdemu bohaterowi dokonać własnego wyboru.
- Niedostrojony przedmiot pozostaje dostępny jako fizyczny element inventory, ale
  nie wystawia specjalnych ataków, akcji ani efektów i nie może wydawać ładunków.
  Sam odpoczynek może nadal odnowić jego pulę ładunków.
- Wybór jest zatwierdzany razem z short restem. Anulowanie podglądu odpoczynku
  nie zmienia więzi ani czasu scenariusza.
- Stan instancji z eksploracji jest nakładany na odpowiadający mu przedmiot
  encountera, więc dostrojenie i liczba ładunków nie resetują się przy rozpoczęciu
  walki. Snapshot v12 zachowuje oba pola.
- MVP nie kończy więzi automatycznie wskutek dystansu przez 24 godziny, śmierci,
  utraty wymagań ani dostrojenia innej istoty; te oficjalne warunki pozostają
  odroczoną regułą fidelity.

## Kompozycyjne efekty magicznych przedmiotów

- Definicja lub instancja przedmiotu może deklarować typowane `magic_effects`.
  Pierwszy zestaw prymitywów obejmuje premie do KP, save, ability check, attack
  roll i szybkości.
- Wspólny evaluator aktywuje efekt wyłącznie dla dostępnej instancji, po
  wymaganym attunement i — jeśli `requires_equipped` nie wyłączono — wyposażeniu.
- Premie do d20 są osobnymi komponentami `ITEM` nazwanymi nazwą przedmiotu.
  Pozwala to UI wyjaśnić wynik i zachowuje istniejące reguły stackingu.
- Referencyjny `guardian_amulet` składa premię +1 KP oraz +1 do wszystkich rzutów
  obronnych bez własnego resolwera. Snapshot v12 zachowuje deklaracje efektów.

## Zwykły ekwipunek i przygotowanie M7

- Zwykły ekwipunek SRD 5.1 jest przechowywany w jednym katalogu
  `content/items/adventuring_gear.json`. Stabilne ID pozostaje globalnym ID
  przedmiotu; ścieżka katalogu nie jest częścią zapisu ani referencji scenariusza.
- `gear.category` rozróżnia pojemniki, consumable, ubrania, focusy, narzędzia,
  instrumenty i equipment packi bez wyprowadzania mechaniki z polskiej nazwy.
- Pojemności, źródła światła i paliwo, modyfikatory testów, durability oraz
  zawartość pakietów są typowanymi regułami domenowymi. Świeca i pochodnia
  zużywają własną sztukę przy zapaleniu; lampy zużywają jedną butelkę oliwy.
- Equipment pack jest kupowalnym bundle. Rozpakowanie zużywa jedną instancję
  pakietu i atomowo dodaje rzeczywiste stosy wskazanych przedmiotów.
- Focus mistyczny, focus druida, święty symbol, component pouch, instrument
  oraz spellbook mają jawne metadane przygotowane dla walidacji komponentów
  V/S/M w M7. Samo posiadanie focusu nie omija jeszcze przyszłego kontraktu czaru.
- Snapshot v12 zapisuje cały kontrakt instancji mundane gear. Migracja v11→v12
  pozostawia starsze przedmioty bez nowych opcjonalnych właściwości.

## Światło, zmysły i obserwacja eksploracyjna

- Strefa eksploracji deklaruje `ambient_light`: `bright`, `dim` albo `darkness`.
  Obserwacja zależna od wzroku deklaruje też abstrakcyjny dystans w stopach.
- Półmrok jest lightly obscured: test Wisdom (Perception) oparty na wzroku ma
  utrudnienie, a pasywna Perception otrzymuje odpowiadające mu `-5`. Pełna
  ciemność blokuje zwykły wzrok.
- Darkvision w swoim zasięgu traktuje ciemność jak półmrok, a półmrok jak jasne
  światło. Blindsight i truesight w zasięgu omijają poziom światła. Tremorsense
  jest zapisanym zmysłem, ale nie zastępuje wzroku w authored obserwacji.
- Zapalone światło członka drużyny może oświetlić abstrakcyjny dystans
  obserwacji. Jego czas jest zużywany przez każdy mechaniczny upływ czasu
  eksploracji; po wyczerpaniu źródło gaśnie i runtime pokazuje komunikat.
- Te same korekty widzenia obserwatorów są stosowane podczas opcjonalnego
  skradania przed encounterem. Dokładna geometria światła na siatce pozostaje
  osobnym rozszerzeniem.

## Search, Hide, pułapki i hazards w eksploracji

- Aktywny Search strefy jest jawną akcją lokalnego runtime, a nie decyzją LLM.
  Content strefy ustala cechę, skill, DC, koszt minutowy i odkrywane punkty.
  Jeden wynik może równocześnie ujawnić wszystkie pułapki, których osobne
  `detection_dc` osiągnął.
- Passive Perception jest sprawdzana przy wejściu do strefy dla pułapek z
  `passive_detection`. Półmrok stosuje `-5`, ciemność bez odpowiedniego zmysłu
  wyklucza wzrokowe wykrycie.
- Hide w strefie dozwolone jest wyłącznie, gdy content deklaruje
  `allows_hiding`. Zapisujemy wynik Stealth bez sztucznego stałego sukcesu:
  dopiero obecność obserwatora pozwala porównać go z jego passive Perception.
  Zapalone światło, istotny upływ czasu, odpoczynek, dłuższa czynność, podróż
  albo rozpoczęcie encountera kończą nieprzeniesione ukrycie.
- Jeżeli authored opening dopuszcza Hide, wynik zapisany w eksploracji jest po
  fizycznym setupie porównywany osobno z każdym przeciwnikiem i przechodzi do
  combatowego `HiddenState`. Bohater nie rzuca ponownie.
- Pułapka po wykryciu korzysta z istniejących stanów `revealed`, `disarmed`,
  `bypassed` i `triggered`. Nieudane rozbrojenie może uruchomić ten sam
  data-driven hazard: fizyczny save, obrażenia oraz authored effects.

## Drzwi, zamki, pojemniki i obiekty niszczalne

- Fixture sceny deklaruje typ `door`, `container`, `obstacle` albo `object`.
  Drzwi i przeszkody mają pola planszy; zamknięte drzwi mogą blokować ruch oraz
  zapewniać połowę (`+2`) lub trzy czwarte (`+5`) osłony.
- `unlock`, `open`, `close` i `loot` są lokalnymi operacjami runtime. LLM nie
  ustala ich DC ani skutków. Otwieranie zamka bez klucza wymaga fizycznego d20,
  narzędzi złodziejskich i korzysta z profilu biegłości aktora.
- Pojemnik ujawnia `yield_items` dopiero po udanym otwarciu i operacji `loot`.
  Ujawnienie zawartości nie przenosi jej automatycznie do ekwipunku; obowiązuje
  istniejący, jawny przepływ zabrania przedmiotu.
- Obiekt niszczalny ma KP, HP i opcjonalny próg obrażeń. Cios poniżej progu nie
  zmniejsza HP. Przy 0 HP obiekt jest zniszczony, przestaje blokować i zapewniać
  osłonę, a zawartość pojemnika zostaje ujawniona.
- Encounter otrzymuje projekcję bieżącego stanu fixture'ów z eksploracji.
  Otwarte lub wcześniej zniszczone drzwi nie odzyskują blokowania ani cover po
  rozpoczęciu walki. Bezpośrednie niszczenie tych fixture'ów w trakcie walki
  pozostaje kolejnym rozszerzeniem combatowego targetingu obiektów.

## Trwały stan NPC

- Opis, osobowość i wiedza NPC są definicją contentu, natomiast zmieniające się nastawienie, kondycja fizyczna i emocjonalna, ujawnione informacje, wykorzystane próby oraz zdarzenia relacji należą do `NpcRuntimeState`.
- Zaakceptowana interakcja zawsze dopisuje uporządkowane zdarzenie relacji. Interakcja wymagająca rzutu zapisuje stabilny identyfikator wykorzystanej próby; blokowanie ponowień będzie osobnym etapem reguł społecznych.
- Zmiana stanu wynika z `state_on_success` albo `state_on_failure` właściwej polityki intencji. LLM tworzy narrację i klasyfikuje zamiar, ale nie może samodzielnie ustawić dowolnego nastawienia poza contentowym kontraktem.
- Kolejne wywołanie NPC otrzymuje zarówno lokalną historię rozmowy, jak i aktualny runtime state. Snapshot zapisuje oba elementy osobno.
- Intencja oznaczona `uses_social_reaction` korzysta z tabeli Conversation Reaction z DMG 2014. LLM klasyfikuje wyłącznie koszt prośby dla NPC (`no_risk`, `minor_risk`, `significant_risk`), a deterministyczny silnik łączy go z nastawieniem: friendly 0/10/20, indifferent 10/20/brak możliwości, hostile 20/brak możliwości/brak możliwości.
- Dla celu korzystającego z tej tabeli gracz przed wysłaniem deklaracji wybiera
  `Persuasion`, `Deception` albo `Intimidation`. Ten wybór jest autorytatywny:
  propozycja LLM nie może go zastąpić. Content może ograniczyć dostępny zestaw
  przez `allowed_skills`; wszystkie trzy testy używają Charisma.
- ST, automatyczna zgoda i odmowa wynikają z tej tabeli, nie z propozycji LLM. UI pokazuje aktualne nastawienie, poziom ryzyka i warunek reakcji przed akceptacją; każda contentowa zmiana nastawienia pojawia się również jako wpis rozmowy.
- Powtarzalne testy NPC mogą mieć contentowe `attempt_policy`. Runtime liczy wyłącznie zaakceptowane i rozstrzygnięte rzuty oznaczone stabilnym `attempt_id`; rozmowa bez rzutu, odmowa i odrzucony preview nie zużywają limitu.
- `max_attempts` jest limitem bezwzględnym, a `retry_requires_any_flags` wymaga, aby przed ponowieniem zaszła co najmniej jedna wskazana zmiana świata. Blokada oraz wyczerpanie zwracają naturalne teksty contentowe i nigdy nie uruchamiają efektów sukcesu ani porażki.
- Intencje NPC o zamkniętej stawce używają contentowych `targets`. LLM klasyfikuje istniejący cel i ilość, natomiast cel narzuca limit, test oraz cztery gałęzie wyniku. Propozycja LLM zawierająca własne flagi, efekty albo ujawniane informacje dla strukturalnego celu jest odrzucana.
- Gałąź krytycznego sukcesu wymaga udanego testu i naturalnego 20; gałąź krytycznej porażki wymaga nieudanego testu i naturalnego 1. Skrajny wynik nie zmienia sam w sobie zasad sukcesu testu cechy 5e.
- Executor gałęzi używa wspólnego `apply_exploration_effect`, aktualizuje trwały stan NPC, zapisuje próbę i emituje osobne logi efektów. Referencyjne cele zwiadowcy to kradzież meldunków i wymuszenie informacji.
- Gałąź wyniku może wskazać `transition_id`. Runtime wybiera pierwszy pasujący wariant z contentu na podstawie flag i rozstrzygniętych encounterów, po czym zatrzymuje automatyczne triggery do jawnej reakcji drużyny. Reakcja może wznowić dialog, trwale zamknąć interakcję albo uruchomić nazwany istniejący encounter; LLM jedynie narracyjnie opisuje scenę.
- Efekty propozycji LLM, strukturalnych wyników NPC, ujawnianej wiedzy i reakcji przejścia korzystają z jednego walidatora. Loader sprawdza typ prymitywu, wymagane parametry, referencje do zasobów/punktów/challenge'y/stref/pułapek oraz lokalne `allowed_effect_types` i `allowed_flags`, zwracając pełną ścieżkę błędnego wpisu przed rozpoczęciem sesji.
- `village_square_mvp` zawiera drugi fixture tego kontraktu: krytycznie nieudane negocjacje z sołtysem prowadzą do przeprosin i wznowienia dialogu albo jego zamknięcia, bez encountera. Potwierdza to, że transition router nie jest mechaniką specyficzną dla walki lub rannego zwiadowcy.

## Zegar scenariusza i konsekwencje zwłoki

- `ExplorationState.elapsed_minutes` jest jednym autorytatywnym licznikiem czasu
  eksploracji. Podróż między strefami, rozmowy NPC, short rest, rytuały, crafting,
  zmiana pancerza i continuation nie prowadzą własnych zegarów.
- Content scenariusza może zdefiniować godzinę rozpoczęcia oraz uporządkowane
  progi minutowe. Godzina i pora dnia w UI są prezentacją; decyzje reguł opierają
  się na czasie od rozpoczęcia sceny.
- Po przekroczeniu progu jego efekty są wykonywane przez wspólny
  `apply_exploration_effect`. Wewnętrzna flaga markera jest zapisywana w
  snapshotcie, więc ten sam event nie uruchamia się ponownie po kolejnym
  przesunięciu czasu albo wczytaniu sesji.
- Progi pozostają ukrytym contentem MG. Gracz widzi koszt jawnej decyzji, bieżącą
  porę dnia i narrację konsekwencji dopiero wtedy, gdy ta nastąpi.
- `village_square_mvp` rozpoczyna się o 17:00. Szybka ścieżka zadania pozwala
  dotrzeć do strażnicy przed progami zwłoki; dodatkowy odpoczynek może spowodować
  przybycie o zmierzchu i dać goblinom czas na przygotowanie obrony.
- Handoff zapisuje minutę wyjścia i przybycia, czas dalszej podróży, wyliczoną
  godzinę oraz eventy uruchomione podczas continuation. Po przesunięciu zegara
  wybierana jest gałąź rezultatu, więc konsekwencje zmierzchu i alarmu mogą
  zmienić wynik tego samego przejścia. Handoff jawnie wskazuje flagi i efekty do
  przeniesienia; ich zastosowanie pozostaje zadaniem kampanii M9.

## Podróż, nawigacja i exhaustion

- Bazowy `travel_minutes` continuation jest czasem tempa normalnego. Tempo
  szybkie używa `ceil(3/4 czasu)`, a wolne `ceil(4/3 czasu)`.
- Nawigacja jest zwykłym fizycznym ability checkiem wybranego aktora przeciw
  authored DC. Porażka nie zatrzymuje przejścia: dodaje authored delay przed
  obliczeniem forced march i progów zegara.
- UI zbiera continuation etapami: jawne tempo, prowadzący wskazany kartą
  bohatera oraz naturalny wynik fizycznego d20. `ACCEPT` zatwierdza bieżący
  etap, `DECLINE` cofa o jeden. Natural Explorer pomija wybór i rzut, gdy teren
  pasuje; forced-march saves są zbierane w końcowym etapie bez zmiany ich
  deterministycznej kolejności.
- Forced march liczy każdą rozpoczętą godzinę ponad `safe_travel_minutes`.
  Każdy żywy członek drużyny wykonuje Constitution save o rosnącym ST
  `10 + numer dodatkowej godziny`; porażka zwiększa exhaustion o jeden.
- Używamy tabeli exhaustion D&D 5e 2014. Poziom 1 daje disadvantage na ability
  checks, 2 połowi szybkość, 3 dodaje disadvantage na ataki i save'y, 4 połowi
  maksimum HP, 5 ustawia szybkość na 0, a 6 zabija aktora. Advantage i
  disadvantage nadal znoszą się zgodnie ze wspólnym resolverem d20.
- Stan exhaustion należy do aktora, przechodzi pomiędzy eksploracją i combatem
  oraz jest zapisywany. Long rest zdejmuje jeden poziom po spełnieniu zwykłych
  warunków odpoczynku.

## XP i awans postaci do poziomu 3

- Używamy progów doświadczenia D&D 5e 2014: poziom 2 od 300 XP i poziom 3
  od 900 XP. Tabela domenowa zachowuje progi 1–20, ale aktualny limit produktu
  i kreatora wynosi 3.
- Przyznanie XP nie zmienia automatycznie poziomu aktora. Osiągnięcie progu
  udostępnia osobny level-up, ponieważ awans może wymagać wyboru subclassy,
  czarów, Expertise, Metamagii, invocation albo innych grantów.
- Content encountera podaje całkowitą nagrodę. Runtime dzieli ją równo, z
  zaokrągleniem w dół, pomiędzy żywe postacie sojusznicze używające death
  saves. NPC, summon i martwa postać nie otrzymują udziału; niepodzielna reszta
  jest jawnie rejestrowana.
- XP należy do trwałego stanu aktora, jest widoczne w payloadzie UI i przechodzi
  przez zapis postaci v4 oraz snapshot sesji v24.
- Awans jest osobną, czystą transakcją. Wymaga progu XP, zwiększa dokładnie
  jeden poziom, przebudowuje granty/sloty/HP/Hit Dice i nie daje darmowego
  odpoczynku: zachowuje obrażenia oraz zużyte istniejące zasoby.
- Elastyczne premie cech species są jawnym wyborem źródłowym, a nie zakodowaną
  na sztywno odmianą statystyk.
- Kreator używa wariantu point buy D&D 5e 2014: sześć bazowych cech mieści się
  w zakresie 8–15, pełna pula wynosi 27 punktów, a koszty wartości 8–15 to
  odpowiednio 0, 1, 2, 3, 4, 5, 7 i 9. Premie species są dodawane dopiero do
  kupionej wartości bazowej i nie zużywają puli point buy.
- Interfejs pokazuje osobno kupioną wartość bazową, jej koszt, wszystkie premie
  species oraz końcową wartość i modyfikator. Standard array
  `15, 14, 13, 12, 10, 8` pozostaje legalnym gotowym rozkładem kosztującym
  dokładnie 27 punktów.
- Wybór umiejętności klasowej przyznaje biegłość, a nie nową osobną akcję.
  Na poziomie 1 dodaje premię `+2` do pasującego testu. Kreator pokazuje
  powiązaną cechę i przykłady użycia oraz blokuje ponowny wybór biegłości
  otrzymanej już z species albo backgroundu.
- Style walki są trwałymi cechami postaci. Kreator opisuje warunek i efekt
  każdego stylu, a istniejące resolvery automatycznie uwzględniają go przy
  wyliczaniu KP, ataku, obrażeń, reakcji albo walki dwiema broniami.
- Obecny kreator przyznaje jednej klasie jeden kompletny, automatyczny zestaw
  startowy. UI rozwija jego przedmioty, ilości i zawartość pakietów; wyposażenie
  oraz monety backgroundu są dodawane osobno. Alternatywa polegająca na
  rezygnacji z zestawu i zakupach za klasowy startowy majątek wymaga osobnego
  trybu sklepu i nie jest symulowana samym polem wyboru.
- Ostatni etap pokazuje żywe podsumowanie pochodzenia, klasy, końcowych cech,
  biegłości, specjalizacji i zestawu. Gracz może wrócić bezpośrednio do
  właściwego etapu, a zapis następuje dopiero przez jawne
  „Akceptuj i utwórz postać” oraz pełną walidację domenową.

## Kompletność postaci SRD do poziomu 3

- Autorytatywny zakres to D&D 5e 2014 / SRD 5.1: dziewięć głównych species,
  dwanaście klas, po jednej subclassie SRD i 127 unikalnych czarów poziomu
  0–2. Multiclass pozostaje poza tym zakresem.
- Sam wpis w JSON nie oznacza wdrożenia. `implementation_audit` zbiera również
  cechy wariantów, subclass i zagnieżdżonych wyborów klasowych. Każde ID musi
  być sklasyfikowane jako wykonywalne, data-driven, marker wyboru albo jawny
  wyjątek stołowy.
- Każda cecha klasy przyznawana na poziomie 1 ma polski tooltip z opisem reguły,
  sposobem obsługi w aplikacji i trybem użycia. Osobny audyt wymaga zarówno
  takiego opisu, jak i kontraktu w `implementation_audit`.
- Żaden z 127 czarów tego zakresu nie pozostaje surowym castem `assisted`.
  Czary bojowe używają resolverów ataku, leczenia, obszaru, wielopocisku,
  statusu, puli PW, okresowych obrażeń, ruchu, przywołania albo reakcji.
- Czar o otwartej konsekwencji fabularnej nadal przechodzi pełną walidację
  dostępu, przygotowania, komponentów, slotu, ekonomii akcji, koncentracji i
  zasobów, po czym zapisuje typowaną flagę `cast_<spell_id>` oraz — gdy ma to
  znaczenie — czasowy efekt eksploracyjny. Scenariusz może wymagać tej flagi
  przy konkretnej interakcji, np. `Animal Friendship` przy zwierzęciu.
- LLM widzi aktualne flagi i opis sceny, więc może sklasyfikować deklarację lub
  sparafrazować odpowiedź, ale nie tworzy skutku czaru poza listą efektów
  dopuszczoną przez content i walidator runtime.
- Świadome uproszczenia planszowe pozostają jawne: strefy są obecnie
  zakotwiczane na aktorze zamiast na pustym polu, `Command` ma deterministyczny
  wariant Halt, a wybrane utrzymywane czary nie mają jeszcze wszystkich
  specjalnych akcji przesuwania, uwolnienia albo zakończenia efektu.
- Jawne wyjątki cech to Druidic i Thieves' Cant (treść komunikacji), Tinker
  (fabularne drobne urządzenia) oraz specjalne formy i swobodne zachowanie
  chowańca Pact of the Chain. Uprawnienia, rytuał, koszt i czas nadal zapisuje
  aplikacja.
- Bardic Inspiration jest opcjonalnym dodatkiem do ataku, ability checku lub
  saving throwu i znika dopiero po podaniu wyniku kości. Cutting Words działa
  w deterministycznym oknie reakcji ataku; zastosowania przeciw fizycznym
  ability checkom i osobnym rzutom obrażeń pozostają rozstrzygane przy stole.
- Metamagia Sorcerera posiada wszystkie osiem wyborów z poziomu 3. Runtime
  pilnuje kosztów, nielegalnych kombinacji, Twinned targetingu,
  Careful/Heightened save'ów, Distant range, Quickened action economy,
  Subtle components, Extended duration i fizycznego rerollu Empowered.
- Favored Enemy typu humanoid nie jest skrótem oznaczającym wszystkie
  humanoidy. Kreator wymaga dokładnie dwóch ras humanoidów, a authored test
  śledzenia lub wiedzy musi podać zarówno `creature_type:humanoid`, jak i
  `humanoid_race:<id>`.
- Leczenie przez Cure Wounds i Healing Word jawnie wyklucza constructy oraz
  undead. Fire Bolt przekazuje do UI dodatkową regułę zapalenia
  nieprzymocowanego łatwopalnego obiektu; stan takiego fizycznego rekwizytu
  rozstrzyga stół.

## Formalny crafting w downtime

- Formalne rzemiosło nie korzysta z tymczasowych konstrukcji `/zbuduj`.
  Content receptury wskazuje strefę, warsztat, zwykły produkt oraz wymagany
  identyfikator narzędzi.
- Wykonawca musi być żywym sojusznikiem, mieć biegłość w wymaganych narzędziach
  i posiadać działający przedmiot o tym samym `tool_proficiency_id`.
- Zgodnie z bazową regułą 2014 materiały kosztują połowę wartości rynkowej
  produktu. Postęp wynosi 5 gp na ośmiogodzinny dzień; rozpoczęta część kolejnego
  dnia jest rozliczana jako pełny dzień pracy.
- Obecny vertical slice kończy recepturę atomowo. Koszt, rezultat i pełny czas są
  pokazane przed potwierdzeniem, po czym silnik pobiera monety, dodaje trwały
  mundane item i przesuwa wspólny zegar. Projekty wielodniowe przerywane w
  połowie oraz współpraca wielu rzemieślników pozostają poza tym zakresem.
- Referencyjna kuźnia w `village_square_mvp` tworzy sztylet za 1 gp materiałów
  w ciągu jednego dnia. Osiem godzin uruchamia istniejące konsekwencje zwłoki,
  co potwierdza, że downtime nie ma osobnego ani darmowego czasu.

## Granice warunków eksploracji i walki

- `ConditionState` jest wspólnym stanem aktora, a nie stanem konkretnego widoku.
  Warunki eksploracyjne dotyczące uczestników są przekazywane do `CombatState`.
- Po encounterze najpierw emitowany jest `ENCOUNTER_ENDED`. Warunki o duration
  lokalnym dla tury, rundy, pozycji, koncentracji albo encountera wygasają.
  Pozostałe warunki bohaterów wracają do `ExplorationState` z niezmienionym
  źródłem, duration i kontraktem save'a.
- `Grappled` nie może przetrwać, jeżeli jego źródłowy aktor nie należy do
  trwałej drużyny eksploracyjnej. Pozostałe `permanent` warunki mogą trwać dalej.
- `SHORT_REST_COMPLETED`, `LONG_REST_COMPLETED` i `SCENARIO_ENDED` rozstrzygają
  warunki tym samym eventowym kontraktem co aktywne efekty. Własny ponawiany
  save nie blokuje wygaśnięcia na nadrzędnej granicy.
- Hazard eksploracyjny może obecnie nałożyć `Prone`, `Poisoned` albo
  `Restrained` z duration właściwym poza walką. `Grappled` wymaga żywego źródła
  i pozostaje mechaniką rozstrzyganą w combat flow.
- Referencyjny upadek na zatrute kolce bramy nakłada `Prone` oraz `Poisoned`
  `until_short_rest`. Zatrucie wpływa na testy i ataki w encounterze, po czym
  pozostaje widoczne w eksploracji aż do odpoczynku.

Poza zakresem MVP:

- pełny UI point-and-click,
- losowe wydarzenia,
- czas/ryzyko za ponawianie działań,
- automatyczne przejście z eksploracji do encountera.
- pełny silnik wyzwań z wieloetapowymi konsekwencjami poza pierwszym challenge bramy,
- integracja pełnego ekwipunku i czarów z opcjami eksploracyjnymi,
- głosowy interfejs kreatywnych deklaracji przez LLM.

## Rozpraszanie efektów czarów

- Efekt jest rozpraszalny wyłącznie wtedy, gdy runtime zachowuje jego stabilne
  `spell_id` i rzeczywisty poziom rzucenia. Sama etykieta albo stan nie wystarcza.
- Czar rozpraszający na istocie kończy wszystkie efekty czarów na tym celu,
  których poziom nie przekracza użytego slotu.
- Dla każdego silniejszego efektu gracz wykonuje osobny fizyczny test d20 cechy
  rzucania czarów przeciw ST `10 + poziom efektu`. Proficiency nie jest dodawane.
- Efekty z akcji, przedmiotów, sceny i zwykłych warunków nie są usuwane. Zakończenie
  efektu utrzymującego summon usuwa powiązanego dynamicznego aktora.
- Obecny przepływ celuje w istoty podczas walki. Obiekty, samodzielne magiczne
  obszary i efekty eksploracyjne wymagają przyszłego wspólnego modelu celu magii.

## Fizyczne karty akcji: fazy i okna rozstrzygnięcia

- Każda nieuniwersalna karta ma jedną fazę: `combat`, `exploration` albo
  `removed`. Skaner odrzuca kartę zagraną w niewłaściwej fazie przed zużyciem
  akcji, zasobu lub slotu.
- Karty nie omijają mechaniki gry. Skan uruchamia ten sam resolver, wybór celu
  na planszy i walidację zasobów co odpowiadająca mu opcja ekranowa.
- Szał jest przełącznikiem: pierwszy skan go aktywuje, a ponowny skan podczas
  walki kończy. Frenzy można aktywować wyłącznie podczas Szału; ręczne
  zakończenie Frenzy dodaje poziom Wyczerpania.
- Bardic Inspiration i Guidance przechowują rozmiar opcjonalnej kości. Wartość
  `0` w oknie testu oznacza zachowanie efektu; dopiero wpisanie wyniku zużywa
  znacznik.
- Cutting Words ma dwa jawne okna: `attack_roll_revealed` i — jeśli gracz
  pominął pierwsze — `damage_roll_revealed`. W drugim oknie odejmowana jest
  wartość od obrażeń, nie od testu trafienia.
- Alarm można zagrać w podglądzie krótkiego odpoczynku. Zużywa legalny slot i
  kasuje karę zaskoczenia, jeżeli odpoczynek zakończy się napadem.
- Ogólna karta Ataku bronią wybiera aktualnie dobytą, legalną broń. Jeżeli
  postać nie ma aktywnej broni, ten sam skan przechodzi na Atak bez broni;
  ostatnio wybrany czar nigdy nie zastępuje w ten sposób broni.
- Zachowanie życia pozostawia spatial selection planszy: kolejne kliknięcia
  dodają albo usuwają cele, a panel przyjmuje osobną wartość leczenia dla
  każdej figurki. Resolver nadal sprawdza wspólną pulę oraz limit połowy PW.
- Odpowiedź skanera niesie jawny następny krok (`select_board_target`,
  `confirm_action`, `enter_reaction_roll` albo `resolved`) oraz komunikat z
  kosztem. Dzięki temu karta nie wygląda na zużytą, gdy dopiero otworzyła wybór.
- Pierwsza wspólna paczka czarów bojowych nie ma osobnych resolverów kart.
  `Magic Missile`, `Fire Bolt`, `Eldritch Blast`, `Sacred Flame`, `Guiding Bolt`,
  `Cure Wounds`, `Healing Word`, `Bless`, `Shield of Faith`, `Shield`,
  `Misty Step`, `Sleep`, `Hold Person`, `Thunderwave` i `Spiritual Weapon`
  wchodzą przez ten sam router źródeł ataku, leczenia, akcji czaru i reakcji,
  którego używa menu walki. Koszt jest nadal pobierany dopiero przez docelowy
  resolver zgodnie z jego istniejącym momentem zatwierdzenia.
- Karta `Shield` jest legalna wyłącznie w otwartym oknie reakcji obronnej po
  ujawnieniu trafienia. Skan od razu rozstrzyga istniejącą reakcję: zużywa
  reakcję i slot, dodaje +5 KP oraz ponownie ocenia trafienie przed obrażeniami.
- Druga paczka korzysta z tego samego routera dla `Acid Arrow`, `Acid Splash`,
  `Burning Hands`, `Chill Touch`, `Inflict Wounds`, `Poison Spray`,
  `Ray of Frost`, `Scorching Ray`, `Shatter`, `Shocking Grasp`, `Entangle`,
  `Grease`, `Web`, `Faerie Fire` i `Fog Cloud`. Skan nie upraszcza riderów:
  trwające obrażenia, blokada leczenia/reakcji, spowolnienie, osobne promienie,
  rzuty obronne, trudny teren, zasłonięcie i koncentracja pozostają domeną
  istniejących resolverów.
- Ukończony setup encountera nie jest już aktywnym źródłem pól planszy. Po
  rozpoczęciu walki kliknięcia są walidowane względem bieżącego celu lub obszaru
  czaru, dzięki czemu ostatnie pole ustawiania figurki nie może przejąć wyboru
  środka trwałej strefy.
- Trzecia paczka obejmuje `Aid`, `Barkskin`, `Blur`, `Darkness`, `Darkvision`,
  `False Life`, `Hellish Rebuke`, `Heroism`, `Lesser Restoration`, `Mage Armor`,
  `Mirror Image`, `Protection from Evil and Good`, `Protection from Poison`,
  `Sanctuary` i `See Invisibility`. Czary o celu `self` automatycznie wiążą
  aktywnego bohatera i przechodzą do potwierdzenia; nie wymagają klikania jego
  własnej figurki.
- `Hellish Rebuke` ma okno `after_damage_applied`. Karta jest odrzucana poza
  otwartą reakcją ofensywną; legalny skan zużywa reakcję oraz slot i rozstrzyga
  Dex save oraz obrażenia przeciw sprawcy przed wznowieniem tury przeciwnika.
- Zgodnie z uproszczeniem przyjętym dla fizycznej gry `See Invisibility`
  ujawnia rzucającemu zarówno aktywną niewidzialność, jak i przeciwników
  zapisanych jako ukryci przed nim. Usuwany jest tylko identyfikator tego
  obserwatora; ukrycie względem pozostałych bohaterów pozostaje bez zmian.
- Czwarta paczka obejmuje `Bane`, `Blindness/Deafness`, `Command`,
  `Color Spray`, `Hideous Laughter`, `Ray of Enfeeblement`, `Vicious Mockery`,
  `Heat Metal`, `Moonbeam`, `Flaming Sphere`, `Spike Growth`, `Silence`,
  `Gust of Wind`, `Flame Blade` i `Hunter's Mark`. Karta wyłącznie deklaruje
  źródło; rzuty ponawiane, opóźnione ridery, obrażenia przy ruchu lub początku
  tury i blokada komponentów werbalnych pozostają w istniejących resolverach.
- Ponowne zeskanowanie aktywnego `Moonbeam` albo `Flaming Sphere` nie rzuca
  drugiego czaru i nie zużywa slotu. Otwiera planszowy wybór nowego środka;
  docelowy resolver nadal wymusza odpowiednio akcję albo akcję dodatkową oraz
  maksymalny dystans przesunięcia.
- Celowanie leczeniem ma własny jawny stan, niezależny od celowania atakiem.
  Skan `Cure Wounds` lub `Healing Word` podświetla wyłącznie legalne cele i nie
  może korzystać z pozostawionego trybu poprzedniego ataku.
- Piąta paczka obejmuje `Divine Favor`, `Enlarge/Reduce`,
  `Expeditious Retreat`, `Levitate`, `Magic Weapon`, `Shillelagh`,
  `True Strike`, `Resistance`, `Warding Bond`, `Find Familiar`, `Find Traps`,
  `Goodberry`, `Prayer of Healing`, `Spare the Dying` i `Produce Flame`.
  Skan korzysta z tych samych efektów broni, ruchu, obron i stabilizacji co
  menu; `Magic Weapon` nadal wymaga wskazania konkretnej niemagicznej broni.
- `Find Familiar` nie tworzy aktora ani figurki. Wariant Kot daje +2 do obron
  Zręczności, Kruk daje przewagę atakom czarem, a Wąż dodaje dystansowe
  ukąszenie 1k6 trucizny jako akcję dodatkową. Ponowne rzucenie zastępuje
  poprzednią formę.
- Pierwsze potwierdzenie `Goodberry` tworzy zasób 10 jagód i zastępuje starą
  pulę. Kolejny skan tej samej karty otwiera planszowy wybór celu leczenia;
  potwierdzone użycie kosztuje akcję, leczy 1 PW i zmniejsza pulę o 1.
- `Find Traps` po potwierdzeniu ujawnia wszystkie ukryte pułapki bieżącego
  obszaru, ale nie zmienia ich stanu rozbrojenia. `Spare the Dying` otwiera
  istniejące celowanie stabilizacji i wymaga przyległego żywego sojusznika z
  0 PW.
- `Prayer of Healing` ma planszowy wybór maksymalnie sześciu legalnych celów
  i wspólny fizyczny rzut 2k8 (+1k8 za wyższy slot). Pierwsze potwierdzenie
  zapisuje cele i wynik oraz rozpoczyna wymagającą koncentracji modlitwę;
  kończy też wcześniejszą koncentrację rzucającego. Dopiero potwierdzenie
  10 nieprzerwanych minut przesuwa zegar, leczy każdy cel o rzut + modyfikator
  cechy czarowania i zużywa slot. Anulowanie lub utrata koncentracji przed
  ukończeniem nie leczy i nie zużywa slotu.
- Odpowiedź skanera karty zawiera aktualne liczniki zasobów aktywnego bohatera
  oraz komórek czarów. Dzięki temu po skanie w tym samym komunikacie widać m.in.
  Ki, Boską Moc, Inspirację, Punkty Magii, Wild Shape i pulę Goodberry, o ile
  postać posiada dany zasób.
- Pierwsza paczka fizycznych cech klas walczących obejmuje `Action Surge`,
  `Second Wind`, `Rage`, `Reckless Attack`, `Frenzy`, `Martial Arts`,
  `Flurry of Blows`, `Patient Defense`, `Step of the Wind`, `Deflect Missiles`,
  `Lay on Hands`, `Divine Smite`, `Sacred Weapon` oraz `Turn the Unholy`.
  Karta korzysta z tego samego resolvera i tej samej puli zasobów co przycisk
  ekranowy; skaner nie odejmuje Ki, Boskiej Mocy, slotu ani użycia przed
  właściwym potwierdzeniem.
- Karty wymagające wartości niefizycznej na planszy otwierają wspólny prompt:
  `Second Wind` i `Deflect Missiles` oczekują wyniku k10, `Sacred Weapon`
  konkretnej wyposażonej broni, `Turn the Unholy` osobnych rzutów obronnych
  Mądrości, a `Divine Smite` poziomu dostępnego slotu. Anulowanie promptu nie
  zużywa akcji ani zasobu.
- `Divine Smite` jest legalne dopiero po potwierdzonym trafieniu bronią w
  zwarciu i przed rzutem obrażeń. Otwarcie promptu nie usuwa oczekującego
  ataku. Analogicznie `Deflect Missiles` jest legalne tylko w aktywnym oknie
  ujawnionych obrażeń ataku dystansowego bronią i nie usuwa reakcji przeciwnika.
- `Rage` pozostaje ręcznym przełącznikiem, `Frenzy` wymaga aktywnego Rage, a
  `Reckless Attack` musi zostać zadeklarowane przed pierwszym atakiem.
  `Martial Arts` i `Flurry of Blows` wymagają wcześniejszego ataku w akcji
  Attack; odpowiednio ustawiają jeden albo dwa oczekujące ataki bez broni.
- Druga paczka fizycznych cech klasowych domyka planszowe cele Bardic
  Inspiration i Preserve Life, dwustopniowe okna Cutting Words oraz rzuty
  Turn Undead. Cunning Action po skanie wybiera Sprint, Odwrót albo Ukrycie,
  a Pact Weapon ogranicza kartę do trzech czytelnych form: longsword,
  greataxe i rapier.
- Wild Shape ma świadomie uproszczony profil planszowy trzech ról ze statystykami
  bestii SRD: brown bear (tank), wolf (mobilność/kontrola) i giant eagle
  (mobilny DPS). Dostęp do niedźwiedzia i latającej formy przed zwykłymi progami
  2014 jest regułą autorską tej gry. Giant eagle ignoruje koszt trudnego terenu,
  a ponowne zeskanowanie karty ręcznie kończy formę.
- Bojową Metamagię deklaruje się po przygotowaniu karty czaru. Skan modyfikatora
  dopina go do oczekującego źródła ataku, leczenia albo czaru obszarowego;
  cele, rzuty i koszt są rozliczane później przez istniejący resolver. Interfejs
  nie pokazuje już wariantów Metamagii przed wyborem czaru. Empowered Spell
  zachowuje własne okno po ujawnieniu rzutu obrażeń.
- Siedem planszowych archetypów celowo odchodzi od progów klas SRD, aby każda
  postać miała od 1. poziomu porównywalny budżet decyzji. Zryw akcji, Ratunek
  polowy, Lekkomyślny atak, Szał bojowy i Przebiegła akcja mogą więc pojawić się
  wcześniej albo u innego archetypu niż w stołowym D&D. Nadal używają tych
  samych kosztów akcji, efektów, koncentracji i zasad odpoczynku.
- Pozycja obronna i Unik instynktowny są osobistymi, limitowanymi wariantami
  Uniku: akcja dodatkowa, 1 użycie na krótki odpoczynek, utrudnienie ataków do
  początku następnej tury. Nie zużywają Ki.
- Zniknięcie w dymie oraz Wykrycie pułapek Miry zużywają wspólną pulę 2 Forteli
  na długi odpoczynek. Oznaczenie celu, Dobre jagody i Wykrycie pułapek Erynda
  zużywają Instynkt. Są kartami technik archetypu, więc ich bezkosztowe
  komponenty materialne nie są wymagane przez ekwipunek.
- Aktualne zestawy siedmiu grywalnych bohaterów nie drukują kart eksploracji.
  Inspiracja bardowska i Wykrycie pułapek są w tych taliach kartami walki;
  eksploracja korzysta z authored kafelków postaci i pasywów.
- Pełne pule poziomów 1–3 zawierają od 7 do 9 kart bojowych na bohatera. Każdy
  czar z wydrukowanej talii ma trasę runtime, a reakcje zachowują właściwe okno:
  Tarcza po ujawnieniu trafienia oraz Cięta riposta po ujawnieniu trafienia lub
  obrażeń.
- Taktyka Garrana (2/3), Dzikość Brakki (2), Fortele Miry (2/3) i Instynkt
  Erynda (2/3) odnawiają się po długim odpoczynku. Technika zużywa punkt dopiero
  przy potwierdzeniu efektu; anulowany prompt nie płaci kosztu.
- Kolorowy rewers karty bohatera i czarno-biały awers zawierają kompletną listę
  istotnych pasywów oraz mechaniczną skazę. Tonerowy zestaw bez rewersów zawiera
  również osobne białe dossier i aktualny arkusz statystyk.

## Start siedmiu bohaterów na poziomie 3

- Garran, Brakka, Mira, Dagna, Lorian, Nimra i Erynd zaczynają na poziomie 3.
  Każdy otrzymuje jednorazową, idempotentną premię `+2` do głównego atrybutu,
  maksymalnie do 20. Premia jest jawnym odstępstwem planszowego archetypu od
  standardowej progresji D&D 5e 2014.
- Każdy bohater ma od startu dostęp do wszystkich kart swojej osobistej talii.
  Drukowane karty mają plakietkę `OD STARTU`; dawne poziomy pochodzenia zostają
  tylko w manifeście technicznym. Awans i odblokowywanie kart są odłożone.
- Stała talia jest mechaniczną listą dostępnych czarów. Dodatkowe czary użyte
  przy budowaniu legalnej klasy mogą pozostać w danych opisowych aktora, ale nie
  tworzą akcji. Erynd płaci Instynktem i nie ma równoległych komórek łowcy.
- `Wykorzystanie słabości` Miry i `Strzelecka cierpliwość` Erynda kosztują akcję
  dodatkową oraz 1 punkt osobistego zasobu. Dają przewagę następnemu atakowi w
  tej samej turze i zastępują wcześniejsze, niegrywalne warianty True Strike.
- Karty `MANEWRY` i `EKWIPUNEK` otwierają odpowiednio legalne menu manewrów i
  menu wyposażenia aktywnego bohatera. Podpowiedź kart pokazuje tylko legalne w
  danym oknie karty oraz aktualny licznik ich skończonego zasobu.
- Dossier nie pokazuje pozornej progresji poziomów 1–3. Sekcja `Zasoby kart`
  podaje maksymalną pulę, sposób odnowienia i nazwy kart, które ją wydają.
  Klasy pełnoczarujące zaczynają z 4 komórkami 1. poziomu i 2 komórkami 2.
  poziomu. Arkusz postaci wymienia wyłącznie czary obecne w osobistej talii.

Testy:

- `tests/unit/test_exploration_setup.py`
- `tests/unit/test_exploration_checks.py`
- `tests/unit/test_exploration_led_feedback.py`
- `tests/unit/test_exploration_zones.py`
- `tests/unit/test_party_checks.py`
- `tests/unit/test_demo_exploration_scene.py`

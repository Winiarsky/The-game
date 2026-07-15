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
- TODO: zweryfikować względem SRD / zasad ruchu na siatce przed rozbudową o reakcje, rozmiary istot i ruch wymuszony.

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

- rozmiary istot,
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

Poza zakresem MVP:

- opóźnianie tury,
- gotowe akcje,
- reakcje,
- efekty dynamicznie zmieniające inicjatywę,
- skanowanie pól jako potwierdzenie setupu.

Odstępstwa / decyzje planszowe:

- Klikanie pionka nie jest wymagane do ustalenia, kto rzuca inicjatywę.
- Jawne elementy setupu są podświetlane LED-ami, ukryte i warunkowe elementy nie są zdradzane graczom.
- MVP rozstrzyga zaskoczenie dla całej drużyny albo całej strony przeciwników przez reguły scenariusza. Nie wykonuje osobnego porównania Stealth z passive Perception dla każdego stworzenia, a pełną karę D&D zastępuje utrudnieniem do inicjatywy; to świadome uproszczenie tempa gry przy stole.

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
- Legalny cel ataku musi mieścić się w `range_feet` źródła ataku.
- Dystans na siatce liczony jest w uproszczony sposób: `max(abs(dc), abs(dr)) * 5 feet`.
- Ranged line of sight / line of effect używa prostego algorytmu Bresenhama na siatce.
- Linia jest blokowana przez ściany/krawędzie, zamknięte drzwi i blokujący terrain na polach pośrednich.
- Atak porównuje wynik ataku z AC celu.
- Naturalne `20` przy ataku oznacza trafienie krytyczne.
- Naturalne `1` przy ataku oznacza automatyczne pudło.
- Przy trafieniu aplikacja prosi o wynik obrażeń.
- W MVP gracz może wpisać końcowy wynik obrażeń krytycznych samodzielnie.
- Obrażenia są wpisywane jako komponenty z typem obrażeń.
- `hp` aktora oznacza aktualne HP, a `max_hp` oznacza maksymalne HP z contentu/scenariusza.
- Obrażenia najpierw zmniejszają temporary HP, potem HP.
- HP nie spada poniżej `0`.
- Wynik aplikacji obrażeń zapisuje HP i temporary HP przed/po, ile obrażeń pochłonęło temporary HP, ile weszło w HP oraz czy cios pokonał cel.
- Komunikaty UI po trafieniu muszą pokazywać obrażenia oraz zmianę HP celu.
- Stan pokonania/śmierci jest uproszczony w MVP.
- `hp > 0` nie oznacza automatycznie, że obiekt jest legalnym celem ataku.
- Cel ataku musi być `attackable=True` i `visible`.
- `RollMode.ADVANTAGE` i `RollMode.DISADVANTAGE` rozstrzygają pełne `2d20`: zapisujemy oba wyniki, a wybrana kość to wyższa przy przewadze i niższa przy utrudnieniu.
- Przy ręcznych rzutach ataku UI wymaga wpisania obu wyników d20, jeśli rzut ma przewagę albo utrudnienie; przeciwnicy rzucają oba d20 automatycznie.
- Mini-pętla walki obsługuje start tury, zużycie akcji, koniec tury, przejście inicjatywy i zakończenie walki.
- Tura śledzi osobno akcję główną, akcję bonusową, reakcję i zużyty ruch.
- Reakcja jest śledzona per aktor, również poza jego własną turą, i odświeża się na początku jego następnej tury.
- `Dash` zużywa akcję główną i dodaje aktorowi dodatkową pulę ruchu równą jego `speed_feet` do końca bieżącej tury.
- `Dodge/Unik` zużywa akcję główną i daje efekt `Unik`: ataki przeciwko aktorowi mają utrudnienie; efekt wygasa na początku następnej tury tego aktora.
- `Disengage/Odwrót` zużywa akcję główną i w MVP daje efekt `Odwrót`: bezpieczne odejście do końca tury, blokujące ataki okazyjne.
- Atak okazyjny może zostać sprowokowany, gdy aktor dobrowolnie opuszcza zasięg wręcz żywego wroga z dostępną reakcją i zdefiniowanym atakiem wręcz/reach.
- W MVP zasięg okazyjnego bierze `range_feet` ataku do 10 feet, żeby obsłużyć zwykły zasięg 5 ft i broń z reach 10 ft, ale wykluczyć broń dystansową typu kusza.
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
- Cantripy nie wymagają przygotowania. Nieprzygotowany czar poziomu 1+ nie daje bonusu eksploracyjnego i nie może zostać użyty jako atak, leczenie ani akcja czarowa, nawet jeśli aktor ma wolny slot.
- Profil jest celowo niezależny od klasy. W tym MVP content podaje listę i limit; wyliczanie ich z poziomu klasy oraz cechy spellcasting zostaje na późniejszy etap.
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
- MVP testu koncentracji nie uwzględnia jeszcze proficiency, advantage/disadvantage, featów ani klasowych premii do concentration save.
- Aktor rzucający czary może mieć `spell_save_dc`; źródło czaru może nadpisać DC własnym `save_dc`.
- `AttackSource` może być save-spellem przez `save_ability`; wtedy przeciwnik wykonuje automatyczny rzut obronny, a UI pokazuje naturalny d20, modyfikator cechy, sumę, ST i sukces/porażkę.
- `AttackSource` może mieć obszar (`area`) typu `radius`, `line` albo `cone`; plansza wybiera środek obszaru albo sąsiednie pole kierunku, UI pokazuje preview LED i wymaga Entera/przycisku przed wykonaniem.
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
- Nie implementujemy jeszcze attunement, pełnych ładunków/odnawiania itemów, klasowo wyliczanych list czarów, profili casterów znanych czarów, zaawansowanych modyfikatorów testu koncentracji ani zaawansowanych efektów czarów poza obrażeniami/lekkim leczeniem i prostym buffem do ataku.
- Jawne obiekty sceny mogą oferować deterministyczne interakcje walki zużywające akcję główną.
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
- pełne death saving throws,
- destrukcja obiektów i przeszkód.
- pełne AI ruchu przeciwników,
- ruch w turze podczas multi-actor MVP,
- testy sporne, rzuty obronne i obrażenia obszarowe z interakcji sceny,
- przesuwanie obiektów sceny po planszy,
- konkretne bonus actions, konkretne reactions i multiattack.

Odstępstwa / decyzje planszowe:

- Szczegółowe zasady śmierci i umierania zostają odłożone, dopóki nie będą potrzebne w pierwszej scenie.
- Obiekty atakowalne są przewidziane w modelu targetowania, ale pełny flow niszczenia obiektów zostaje później.
- Komunikat aplikacji i LED-y muszą być zsynchronizowane: legalne cele, wybrany cel, wynik ataku.
- W board-first MVP gracz nie wybiera najpierw akcji z menu: klika pole na planszy, a aplikacja interpretuje intencję jako ruch albo atak.
- Pierwsze kliknięcie pola pokazuje podgląd intencji, drugie kliknięcie tego samego pola potwierdza.
- Kliknięcie innego legalnego pola przed potwierdzeniem zmienia podgląd.
- Kliknięcie pola aktywnego aktora pokazuje podstawowe opcje aktora; w MVP obsługiwana jest opcja zakończenia tury.
- Zakończenie tury przed wykorzystaniem całego ruchu jest legalne; niewykorzystany ruch przepada na końcu tury.
- Przeciwnicy w MVP mogą wykonać ruch w stronę najbliższego celu, a potem zaatakować, jeśli cel stał się legalny.
- Ruch przeciwnika jest wizualizowany jako czerwona ścieżka i pomarańczowe pole docelowe.
- Pole może mieć wiele dostępnych intencji, np. przeciwnik stojący na obiekcie interaktywnym.
- W takim przypadku plansza pokazuje kolor `multi-option`, kliknięcie tego samego pola przełącza opcję, a Enter potwierdza aktualną opcję.
- Obiekty sceny mogą deklarować `blocks_movement`, `allow_interaction_when_occupied_by_enemy` i `cover_bonus`.
- Jeśli cel ataku stoi na obiekcie z `cover_bonus`, runtime dodaje jawny modyfikator osłony do instrukcji rzutu ataku.
- W web UI walki efekty interakcji obiektu są przypięte do pozycji aktora: osłona wygasa po ruchu z pola, a premia z wozu wygasa po zejściu z pól wozu.
- UI walki nie rozpoznaje już efektów wozu po ID interakcji; wykonuje znane prymitywy efektów z contentu.
- Zielone LED-y oznaczają legalne pola interakcji sceny; jeśli pole jest jednocześnie ruchem i interakcją, kliknięcie z dostępną akcją otwiera wybór interakcji.
- Interakcja przy przeciwniku może wywołać uproszczony atak okazyjny jako decyzję planszowego MVP.
- Pierwsza scena grywalna może zakończyć się przez spełnienie celu sceny, a nie tylko przez pokonanie wszystkich przeciwników.
- Interakcja z jawnym obiektem jest akcją główną: kliknięcie obiektu pokazuje podgląd, drugie kliknięcie potwierdza i zużywa akcję.
- Interakcja może mieć test cechy `d20`; aplikacja pokazuje cechę, skill, ST, aktywne modyfikatory i końcowy modyfikator przed wpisaniem wyniku.
- Wynik eksploracyjnej interakcji może ustawić flagę sceny, np. `crate_secured` albo `crate_trap_missed`.
- Objective może używać warunku `flag_equals`, więc scena może zakończyć się dopiero po konkretnym skutku interakcji, a nie samym kliknięciu obiektu.
- Setup startowy pokazuje pola, na których gracze mogą ustawić figurki, ale MVP nie skanuje automatycznie poprawności ustawienia.
- Ranged MVP nie implementuje jeszcze cover bonus, half cover, three-quarters cover ani disadvantage za strzał w zwarciu.
- Uproszczony LOS traktuje blokujące pola pośrednie jako pełną blokadę, ale nie modeluje rogów, precyzyjnej geometrii miniaturek ani wysokości.

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
- Odrzucone lub niejasne deklaracje tworzą lokalny `declaration_thread` dla aktywnego challenge. Dzięki temu korekta gracza może odnosić się do poprzedniej deklaracji, ale nie tworzymy jeszcze globalnego czatu całej kampanii.
- `gm_classifier.py` zawiera mechanikę integracji, parsowania i walidacji. Content konkretnej przeszkody powinien pochodzić z `llm_policy` oraz `llm_context`; domyślna policy w kodzie jest celowo minimalna, żeby nie przemycać szczegółowego contentu poza scenariuszem.

Poza zakresem MVP:

- pełny UI point-and-click,
- losowe wydarzenia,
- czas/ryzyko za ponawianie działań,
- automatyczne przejście z eksploracji do encountera.
- pełny silnik wyzwań z wieloetapowymi konsekwencjami poza pierwszym challenge bramy,
- integracja pełnego ekwipunku i czarów z opcjami eksploracyjnymi,
- głosowy interfejs kreatywnych deklaracji przez LLM.

Testy:

- `tests/unit/test_exploration_setup.py`
- `tests/unit/test_exploration_checks.py`
- `tests/unit/test_exploration_led_feedback.py`
- `tests/unit/test_exploration_zones.py`
- `tests/unit/test_party_checks.py`
- `tests/unit/test_demo_exploration_scene.py`

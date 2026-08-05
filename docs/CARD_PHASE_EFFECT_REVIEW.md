# Karty — podział na fazy i docelowe efekty

Status: propozycja do przeglądu przed zmianami w mechanice i PDF-ach.

## Założenia

- Każda grywalna karta efektu należy dokładnie do jednej fazy: `COMBAT` albo
  `EXPLORATION`. Wartość `USUNĄĆ` oznacza kartę wycofaną z talii, menu rozwoju
  i puli skanowanych efektów do czasu zaprojektowania dla niej użytecznej
  mechaniki.
- Efekt `COMBAT` jest wykonywany od razu przez deterministyczny resolver walki.
- Efekt `EXPLORATION` wykonuje prostą zmianę stanu i/lub zapisuje flagę, na którą
  może zareagować scenariusz.
- Flaga ma zawsze: `scope` (cel, obiekt, obszar lub drużyna), `duration`,
  `source_id` i opcjonalne parametry.
- Jeżeli scena nie ma własnej reakcji na flagę, obowiązuje opisany w tabeli
  efekt domyślny. Karta nigdy nie kończy się wyłącznie komunikatem „MG rozstrzyga”.
- `Klasa / rasa` opisuje obecne źródło karty. W aktualnym zestawie nie ma
  osobnych aktywnych zdolności rasowych; `—` oznacza brak ograniczenia rasowego.
- Poziom, koszt, zasięg, legalność celu i koncentracja nadal są sprawdzane przed
  wykonaniem opisanego efektu.

### Skrócona składnia efektów

- `damage(cel, kości, typ)` — zadaj obrażenia.
- `heal(cel, wartość)` — przywróć PW.
- `status(cel, nazwa, czas)` — nałóż stan obsługiwany przez walkę.
- `move(cel, dystans)` — przesuń na legalne pole.
- `flag(scope, nazwa, parametry, czas)` — zapisz stan eksploracji.
- `reveal(typ, zasięg)` — zapytaj scenę o pasujące sekrety i pokaż obsługiwane
  wyniki; brak wyniku także jest poprawnym rezultatem.

## Karty sterujące — poza podziałem fazowym

Te cztery karty pozostają elementami interfejsu. Są dostępne w obu fazach, ale
nie są kartami efektu i nie nakładają flag.

| Karta / ID | Dostępność | Docelowe działanie |
|---|---|---|
| Akceptuj (`accept`) | wszyscy | Potwierdza aktualnie pokazany wybór po ponownym sprawdzeniu celu, kosztu i warunków. |
| Odrzuć (`decline`) | wszyscy | Anuluje niezatwierdzony wybór albo wraca o jeden poziom menu. |
| Ekwipunek (`equipment`) | wszyscy | Otwiera menu legalnych operacji na ekwipunku dla aktualnej fazy. |
| Manewry (`maneuvers`) | wszyscy | Otwiera menu manewrów dostępnych dla aktualnej fazy; samo zagranie nie wykonuje manewru. |

## Atak wspólny

| Karta / ID | Klasa / rasa | Faza | Docelowe działanie mechaniczne |
|---|---|---|---|
| Atak bronią (`basic_attack`) | wszystkie / — | WYCOFANA | Podstawowy atak nie używa karty: wskaż przeciwnika na planszy i wybierz legalny atak aktywną bronią; bez aktywnej broni dostępny jest atak bez broni. Karty pozostają dla czarów, cech i manewrów specjalnych. |

## Aktywne zdolności klasowe

| Karta / ID | Klasa / rasa | Faza | Docelowe działanie mechaniczne |
|---|---|---|---|
| Zryw akcji (`action_surge`) | wojownik / — | COMBAT | Zużyj 1 użycie; dodaj bohaterowi 1 dodatkową akcję w bieżącej turze. Odnowienie po krótkim lub długim odpoczynku. |
| Drugi oddech (`second_wind`) | wojownik / — | COMBAT | Zużyj 1 użycie i `heal(self, 1k10 + poziom wojownika)`. Odnowienie po krótkim lub długim odpoczynku. |
| Szał (`rage`) | barbarzyńca / — | COMBAT | Gdy Szał jest nieaktywny: zużyj 1 użycie i włącz go na maks. 10 rund — przewaga w testach i obronach Siły, +2 do obrażeń siłowych ataków wręcz oraz odporność na obrażenia kłute, cięte i obuchowe. Ponowne zeskanowanie tej samej karty ręcznie wyłącza Szał bez zużywania kolejnego użycia. Szał kończy się też po utracie przytomności albo zakończeniu walki. |
| Lekkomyślny atak (`reckless_attack`) | barbarzyńca / — | COMBAT | Pierwszy siłowy atak wręcz w tej turze ma przewagę; do początku następnej tury ataki przeciw bohaterowi także mają przewagę. |
| Szał bojowy (`frenzy`) | barbarzyńca / — | COMBAT | Wymaga aktywnego `rage`. Zeskanowanie włącza `frenzy` do końca bieżącego Szału; od następnej tury pozwala wykonać 1 atak wręcz akcją dodatkową. Nie można aktywować go przed Szałem ani utrzymać po jego zakończeniu. Gdy Szał się kończy, dodaj 1 poziom wyczerpania. |
| Inspiracja bardowska (`bardic_inspiration`) | bard / — | COMBAT | Zużyj 1 użycie; wybrany sojusznik otrzymuje `inspiration_die=1k6` na 10 minut. Przy każdym legalnym teście cechy, ataku lub rzucie obronnym UI pokazuje dodatkowe pole z wartością domyślną `0`. `0` zachowuje Inspirację; wpisanie wyniku 1–6 dodaje go do testu i zużywa efekt. Znacznik może zostać wykorzystany także po przejściu do eksploracji. |
| Cięta riposta (`cutting_words`) | bard / — | COMBAT | Reakcja i 1 użycie Inspiracji. Kartę można zeskanować w `ATTACK_ROLL_REVEALED`, aby odjąć wpisany wynik 1k6 od pokazanego rzutu ataku i ponownie porównać go z KP, albo w `DAMAGE_ROLL_REVEALED`, aby odjąć 1k6 od pokazanych obrażeń przed ich zastosowaniem. Jedna reakcja pozwala zmienić tylko jeden z tych etapów. |
| Zachowanie życia (`preserve_life`) | kleryk / — | COMBAT | Podświetl na planszy legalnych rannych bohaterów w 30 stopach. Gracz wybiera cele przez wskazanie ich pól i wpisuje przy każdym liczbę przydzielanych PW. Suma nie może przekroczyć `5 × poziom kleryka`, a żaden cel nie może zostać uleczony ponad połowę swojego maksimum PW. Zastosuj podział dopiero po zatwierdzeniu całej puli. |
| Odpędzenie nieumarłych (`turn_undead`) | kleryk / — | COMBAT | Nieumarli w obszarze wykonują obronę Mądrości; porażka nakłada `status(fleeing, 10 rund lub do obrażeń)`. |
| Dziki kształt (`wild_shape`) | druid / — | COMBAT | Gdy forma jest nieaktywna: zużyj 1 z 2 użyć, otwórz wybór Niedźwiedzia brunatnego, Wilka lub Wielkiego orła i podmień statystyki bojowe na profil SRD. Ponowne zeskanowanie ręcznie kończy formę. Forma kończy się też przy 0 PW formy albo końcu walki; nadmiar obrażeń przechodzi na PW druida. Latanie Wielkiego orła ignoruje trudny teren. |
| Naturalne odzyskiwanie (`natural_recovery`) | druid / — | EXPLORATION | Podczas krótkiego odpoczynku, raz na długi odpoczynek, odzyskaj wybrane komórki o łącznym poziomie do `ceil(poziom druida / 2)`. |
| Cios sztuk walki (`martial_arts_strike`) | mnich / — | COMBAT | Po legalnej akcji Ataku wykonaj 1 nieuzbrojony atak akcją dodatkową, jeśli bohater nie ma pancerza ani tarczy. |
| Nawałnica ciosów (`flurry_of_blows`) | mnich / — | COMBAT | Po akcji Ataku wydaj 1 Ki i wykonaj 2 osobne nieuzbrojone ataki akcją dodatkową. |
| Cierpliwa obrona (`patient_defense`) | mnich / — | COMBAT | Wydaj 1 Ki; do początku następnej tury włącz efekt Uniku. |
| Krok wiatru (`step_of_the_wind`) | mnich / — | COMBAT | Wydaj 1 Ki; wykonaj Sprint albo Odstąpienie akcją dodatkową i podwój dystans skoku do końca tury. |
| Odbijanie pocisków (`deflect_missiles`) | mnich / — | COMBAT | Reakcja na trafienie bronią dystansową: zmniejsz obrażenia o `1k10 + Zręczność + poziom mnicha`; przy redukcji do 0 pozwól wydać 1 Ki na natychmiastowy atak tym pociskiem. |
| Boski zmysł (`divine_sense`) | paladyn / — | EXPLORATION | Zużyj 1 użycie; `reveal(celestial_fiend_undead_or_sacred_place, 60 stóp)` i zapisz wykryte wyniki do końca następnej akcji eksploracji. |
| Nakładanie rąk (`lay_on_hands`) | paladyn / — | COMBAT | Wydaj wybraną liczbę punktów puli i `heal(cel, punkty)` albo wydaj 5 punktów, by usunąć `diseased` lub `poisoned`. |
| Boskie porażenie (`divine_smite`) | paladyn / — | COMBAT | Po trafieniu wręcz wydaj komórkę: dodaj `2k8 + 1k8/poziom komórki ponad 1.` obrażeń promienistych, dodatkowe 1k8 przeciw czartom i nieumarłym, maks. 5k8. |
| Święta broń (`channel_divinity_sacred_weapon`) | paladyn / — | COMBAT | Zużyj Boską Moc; przez 10 rund aktywna broń dodaje modyfikator Charyzmy (min. +1) do ataków i liczy się jako magiczna. |
| Odpędzenie plugawych (`channel_divinity_turn_the_unholy`) | paladyn / — | COMBAT | Czarty i nieumarli w obszarze wykonują obronę Mądrości; porażka nakłada `status(fleeing, 10 rund lub do obrażeń)`. |
| Pierwotna świadomość (`primeval_awareness`) | łowca / — | EXPLORATION | Otwórz wybór jednej z dostępnych komórek czarów łowcy i pokaż stan puli przed potwierdzeniem. Zużyj wybraną komórkę; `flag(scene, creature_presence_scan, wybrane typy, 1 min./poziom komórki)`. Scena zwraca tylko obecność albo brak w promieniu 1 mili, nigdy liczbę ani położenie. |
| Przebiegła akcja (`cunning_action`) | łotr / — | COMBAT | Wybierz Sprint, Odstąpienie albo Ukrycie i wykonaj je akcją dodatkową w bieżącej turze. |
| Fontanna magii (`font_of_magic`) | zaklinacz / — | EXPLORATION | Otwórz ekran wymiany dwóch zasobów i pokaż aktualne komórki oraz Punkty Magii. Gracz wybiera: zużyj komórkę i odzyskaj PM równe jej poziomowi albo wydaj 2/3/5 PM, aby utworzyć komórkę 1./2./3. poziomu. Maksymalna pula PM jest równa poziomowi zaklinacza. |
| Ostrożny czar (`metamagic_careful`) | zaklinacz / — | COMBAT | Przy czarze obszarowym wydaj 1 PM; do modyfikatora Charyzmy wybranych istot automatycznie zdaje pierwszy rzut obronny. |
| Odległy czar (`metamagic_distant`) | zaklinacz / — | COMBAT | Wydaj 1 PM; podwój liczbowy zasięg bieżącego czaru albo zmień Dotyk na 30 stóp. |
| Wzmocniony czar (`metamagic_empowered`) | zaklinacz / — | COMBAT | Wydaj 1 PM po rzucie obrażeń; przerzuć do modyfikatora Charyzmy kości obrażeń i zachowaj nowe wyniki. |
| Przedłużony czar (`metamagic_extended`) | zaklinacz / — | COMBAT | Wydaj 1 PM; podwój czas trwania bieżącego efektu bojowego, maks. do 24 godzin. |
| Potężny czar (`metamagic_heightened`) | zaklinacz / — | COMBAT | Wydaj 3 PM; wybrany cel ma utrudnienie w pierwszym rzucie obronnym przeciw bieżącemu czarowi. |
| Przyspieszony czar (`metamagic_quickened`) | zaklinacz / — | COMBAT | Wydaj 2 PM; czar o czasie 1 akcja staje się akcją dodatkową; system blokuje inne czary poza sztuczką rzucaną akcją. |
| Subtelny czar (`metamagic_subtle`) | zaklinacz / — | EXPLORATION | Wydaj 1 PM; `flag(current_cast, subtle_cast, no_verbal_no_somatic, natychmiast)`. Scena nie rejestruje gestu ani głosu, ale nadal może wykryć widoczny efekt czaru. |
| Podwojony czar (`metamagic_twinned`) | zaklinacz / — | COMBAT | Wydaj PM równe poziomowi czaru, min. 1; czar jednoosobowy obejmuje drugi legalny cel. |
| Broń paktu (`pact_of_the_blade`) | czarnoksiężnik / — | COMBAT | Otwórz wybór jednego z trzech profili: Rapier, Wielki miecz albo Glewia. System sprawdza wymagane wolne ręce, usuwa poprzednią Broń paktu i przywołuje wybraną do dłoni. Czarnoksiężnik jest w niej biegły, a broń liczy się jako magiczna; atak nadal używa normalnie Siły lub Zręczności. Ponowne zeskanowanie pozwala zmienić profil albo odwołać broń. |
| Odzyskiwanie magiczne (`arcane_recovery`) | czarodziej / — | EXPLORATION | Podczas krótkiego odpoczynku, raz na długi odpoczynek, odzyskaj wybrane komórki o łącznym poziomie do `ceil(poziom czarodzieja / 2)`. |

### Zasoby klasowe i określenia pokazywane graczowi

Każdy zasób jest przechowywany osobno na aktorze. UI pokazuje koszt karty,
wartość przed użyciem i przewidywaną wartość po użyciu. Koszt jest rezerwowany
w `ACTION_COMMITTED`, pobierany po zatwierdzeniu działania i zwracany, jeżeli
akcja zostanie anulowana przed rozstrzygnięciem. Licznik nie może spaść poniżej
zera ani przekroczyć swojego maksimum.

| Klasa | Zasób | Reguła na poziomach 1–3 i sposób prezentacji |
|---|---|---|
| Wojownik | Drugi oddech | Od 1. poziomu: 1 użycie, odnawiane po krótkim albo długim odpoczynku. Karta pokazuje `Użycia: 1/1`; po wykorzystaniu `0/1`. |
| Wojownik | Zryw akcji | Od 2. poziomu: osobne 1 użycie, odnawiane po krótkim albo długim odpoczynku. Nie korzysta z puli Drugiego oddechu. |
| Barbarzyńca | Szał | 2 użycia na poziomach 1–2 i 3 użycia na poziomie 3; odnawiane po długim odpoczynku. Aktywowanie pobiera użycie, ręczne wyłączenie przez ponowne skanowanie nie zwraca go. UI pokazuje `Szał: pozostało 2/2` oraz osobno `Aktywny: tak/nie`. |
| Barbarzyńca | Wyczerpanie | Osobny licznik poziomów wyczerpania. Zakończenie Szału z aktywnym Szałem bojowym dodaje 1 poziom. Nie jest to zasób do dobrowolnego wydawania, ale musi być widoczny obok Szału. |
| Bard | Inspiracja bardowska | Liczba użyć równa modyfikatorowi Charyzmy, minimum 1; na poziomach 1–3 odnawia się po długim odpoczynku. Nadany sojusznikowi znacznik przechowuje kość `1k6`, a nie wynik. Przy legalnym teście gracz wpisuje `0`, aby zachować Inspirację, albo 1–6, aby ją dodać i zużyć. |
| Bard | Komórki czarów | Korzysta ze zwykłej puli pełnego czarującego: poziom 1 — `2×1.`, poziom 2 — `3×1.`, poziom 3 — `4×1. + 2×2.`. Odnawia je po długim odpoczynku. |
| Kleryk | Boska Moc (`Channel Divinity`) | Od 2. poziomu: 1 wspólne użycie, odnawiane po krótkim albo długim odpoczynku. Odpędzenie nieumarłych i Zachowanie życia pobierają z tej samej puli. Karta pokazuje `Koszt: 1 Boska Moc · Pozostało: 1/1`. |
| Kleryk | Komórki czarów | Zwykła pula pełnego czarującego: poziom 1 — `2×1.`, poziom 2 — `3×1.`, poziom 3 — `4×1. + 2×2.`; odnowienie po długim odpoczynku. Przygotowane czary są wyborem dostępu, a nie dodatkowym zasobem. |
| Druid | Dziki kształt | Od 2. poziomu: 2 użycia, odnawiane po krótkim albo długim odpoczynku. Aktywowanie formy pobiera użycie; ręczne zakończenie przez ponowne skanowanie go nie zwraca. UI pokazuje użycia, aktywną formę i jej aktualne/maksymalne PW. |
| Druid | Naturalne odzyskiwanie | Od 2. poziomu: 1 użycie na długi odpoczynek, uruchamiane podczas krótkiego odpoczynku. Odzyskuje komórki o łącznym poziomie do `ceil(poziom druida / 2)`. |
| Druid | Komórki czarów | Zwykła pula pełnego czarującego: poziom 1 — `2×1.`, poziom 2 — `3×1.`, poziom 3 — `4×1. + 2×2.`; odnowienie po długim odpoczynku. |
| Mnich | Ki | Brak na poziomie 1. Od 2. poziomu maksymalna pula jest równa poziomowi mnicha: 2 Ki na poziomie 2 i 3 Ki na poziomie 3. Wszystkie punkty wracają po krótkim albo długim odpoczynku. Karta pokazuje np. `Koszt: 1 Ki · Pozostało: 2/3`. |
| Paladyn | Nakładanie rąk | Pula `5 × poziom paladyna`: 5/10/15 punktów na poziomach 1/2/3. Odnawia się po długim odpoczynku. Gracz wpisuje wydawaną wartość; leczenie pobiera dokładnie tyle punktów, ile przywraca PW, a usunięcie choroby lub trucizny kosztuje 5. |
| Paladyn | Boski zmysł | Liczba użyć `1 + modyfikator Charyzmy`, odnawiana po długim odpoczynku. Jest osobną pulą i nie pobiera Boskiej Mocy ani komórki. |
| Paladyn | Boska Moc (`Channel Divinity`) | Od 3. poziomu: 1 wspólne użycie, odnawiane po krótkim albo długim odpoczynku. Święta broń i Odpędzenie plugawych korzystają z tej samej puli. |
| Paladyn | Komórki czarów | Brak na poziomie 1; poziom 2 — `2×1.`, poziom 3 — `3×1.`. Odnawiane po długim odpoczynku. Z tej samej puli korzystają czary i Boskie porażenie. |
| Łowca | Komórki czarów | Brak na poziomie 1; poziom 2 — `2×1.`, poziom 3 — `3×1.`. Odnawiane po długim odpoczynku. Z tej samej puli korzystają czary i Pierwotna świadomość. |
| Łotr | Brak wydawanej puli klasowej | Na poziomach 1–3 nie ma punktów klasowych do wydawania. Atak ukradkowy jest automatycznym efektem pasywnym ograniczonym do jednego uruchomienia na turę, a Przebiegła akcja nie ma osobnego kosztu. |
| Zaklinacz | Punkty Magii | Brak na poziomie 1. Maksymalna pula jest równa poziomowi zaklinacza: 2 PM na poziomie 2 i 3 PM na poziomie 3; odnawiana po długim odpoczynku. Fontanna magii wymienia PM z komórkami, a Metamagia wydaje PM na właśnie przygotowany czar. |
| Zaklinacz | Komórki czarów | Zwykła pula pełnego czarującego: poziom 1 — `2×1.`, poziom 2 — `3×1.`, poziom 3 — `4×1. + 2×2.`; odnowienie po długim odpoczynku. |
| Czarnoksiężnik | Komórki Magii Paktu | Oddzielna pula: poziom 1 — `1×1.`, poziom 2 — `2×1.`, poziom 3 — `2×2.`. Wszystkie komórki mają aktualnie ten sam poziom i wracają po krótkim albo długim odpoczynku. Karta pokazuje np. `Magia Paktu: 1/2 komórki 2. poziomu`. |
| Czarnoksiężnik | Broń paktu | Nie ma licznika użyć. System przechowuje tylko stan `nieaktywna` albo wybrany profil broni; ponowne skanowanie zmienia profil lub odwołuje broń. |
| Czarodziej | Odzyskiwanie magiczne | Od 1. poziomu: 1 użycie na długi odpoczynek, uruchamiane podczas krótkiego odpoczynku. Odzyskuje komórki o łącznym poziomie do `ceil(poziom czarodzieja / 2)`. |
| Czarodziej | Komórki czarów | Zwykła pula pełnego czarującego: poziom 1 — `2×1.`, poziom 2 — `3×1.`, poziom 3 — `4×1. + 2×2.`; odnowienie po długim odpoczynku. Księga i przygotowane czary określają dostępne opcje, ale nie są zużywaną pulą. |

Wspólna prezentacja komórek zawsze rozdziela ich poziomy, np.
`1. poziom: 2/4 · 2. poziom: 1/2`. Wybranie czaru albo cechy najpierw pokazuje
legalne poziomy komórki oraz wynik skalowania efektu, a dopiero potem pozwala
zatwierdzić koszt.

### Etapy walki wymagane przez zdolności reakcyjne

Każde rozstrzygnięcie zapisuje jednoznaczny etap. Etapy niepasujące do danej
akcji są pomijane, ale ich kolejność nie może się zmieniać:

| Etap | Znaczenie |
|---|---|
| `COMBAT_STARTED` | Utworzono walkę, uczestników i inicjatywę. |
| `ROUND_STARTED` | Rozpoczęła się nowa runda. |
| `TURN_STARTED` | Aktywowano zasoby i efekty początku tury bieżącego aktora. |
| `ACTION_SELECTION` | Gracz może zagrać kartę albo wybrać akcję z menu. |
| `TARGET_SELECTION` | Plansza podświetla legalne cele, pola albo obszary. |
| `ACTION_COMMITTED` | Cel, koszt i warunki zostały zatwierdzone; zasób jest rezerwowany. |
| `ATTACK_ROLL_REVEALED` | Pokazano kość, premie, sumę ataku i KP celu; otwarte są reakcje zmieniające atak. |
| `ATTACK_RESULT_CONFIRMED` | Po reakcjach ostatecznie potwierdzono trafienie albo pudło. |
| `SAVE_ROLL_REVEALED` | Pokazano kość, premie, sumę obrony i ST; otwarte są reakcje zmieniające obronę. |
| `SAVE_RESULT_CONFIRMED` | Po reakcjach potwierdzono sukces albo porażkę obrony. |
| `DAMAGE_ROLL_REVEALED` | Pokazano kości, premie i surowe obrażenia; otwarte są reakcje zmieniające obrażenia. |
| `DAMAGE_APPLIED` | Po reakcjach, odpornościach i redukcjach zmieniono PW. |
| `STATUS_APPLIED` | Nałożono albo odrzucono wynikające z akcji statusy. |
| `MOVEMENT_RESOLVED` | Zakończono ruch dobrowolny, wymuszony albo teleportację. |
| `ACTION_RESOLVED` | Wszystkie części działania są zamknięte i zwolniono rezerwację kosztu. |
| `TURN_ENDED` | Rozliczono efekty końca tury i przekazano turę dalej. |
| `ROUND_ENDED` | Rozliczono efekty końca rundy. |
| `COMBAT_ENDED` | Zakończono walkę i usunięto efekty ograniczone do walki. |

Dla zwykłego ataku najważniejsze okna przebiegają następująco:

1. `ATTACK_ROLL_REVEALED` — pokazany rzut kością, premie, suma i KP celu;
   przed zatwierdzeniem trafienia otwiera okno reakcji, m.in. Ciętej riposty.
2. `ATTACK_RESULT_CONFIRMED` — po reakcjach ponownie oblicz trafienie. Obniżony
   rzut nadal może trafić, jeżeli jest równy lub wyższy od KP.
3. `DAMAGE_ROLL_REVEALED` — po trafieniu pokazane kości, premie i surowa suma
   obrażeń; przed odjęciem PW otwiera drugie okno reakcji.
4. `DAMAGE_APPLIED` — po reakcjach, odpornościach i redukcjach zmień PW celu.

### Dziki kształt — zamknięte formy bojowe

To świadome uproszczenie i odstępstwo od zwykłego limitu latania druida na tym
poziomie. Wszystkie trzy formy korzystają z bazowych statystyk SRD.

| Forma | Rola | Najważniejsze statystyki i reguły |
|---|---|---|
| Niedźwiedź brunatny | tank | KP 11, 34 PW, szybkość 40 stóp, wspinanie 30 stóp; Wieloatak: ugryzienie `+5, 1k8+4` i pazury `+5, 2k6+4`. |
| Wilk | skradanie i współpraca | KP 13, 11 PW, szybkość 40 stóp, Skradanie +4; Taktyka stada daje przewagę przy sojuszniku obok celu; ugryzienie `+4, 2k4+2`, a cel po porażce obrony Siły ST 11 zostaje Powalony. |
| Wielki orzeł | mobilny DPS | KP 13, 26 PW, chód 10 stóp, lot 80 stóp; ignoruje trudny teren podczas lotu; Wieloatak: dziób `+5, 1k6+3` i szpony `+5, 2k6+3`. |

### Broń paktu — zamknięte profile

| Profil | Warunki | Statystyki |
|---|---|---|
| Rapier | 1 wolna ręka | `1k8` kłutych, finezyjna; może używać Zręczności albo Siły. |
| Wielki miecz | 2 wolne ręce | `2k6` ciętych, ciężki, dwuręczny; używa Siły. |
| Glewia | 2 wolne ręce | `1k10` ciętych, ciężka, dwuręczna, zasięg 10 stóp; używa Siły. |

Broń nie usuwa automatycznie tarczy ani zwykłego przedmiotu. Jeżeli wybrany
profil wymaga większej liczby wolnych rąk, gracz musi najpierw schować albo
upuścić wyposażenie; w przeciwnym razie przywołanie jest nielegalne i nie
zużywa akcji.

### Metamagia — kolejność obsługi

1. Gracz skanuje czar, wybiera cele i wariant.
2. Po walidacji system przechodzi do `SPELL_METAMAGIC_WINDOW` i pokazuje
   legalne dla tego czaru Metamagie oraz aktualne PM.
3. Gracz skanuje jedną Metamagię albo kontynuuje bez modyfikacji.
4. System pobiera PM i rozstrzyga zmodyfikowany czar.
5. `Wzmocniony czar` jest wyjątkiem: jego okno
   `SPELL_DAMAGE_ROLL_REVEALED` pojawia się dopiero po pokazaniu kości obrażeń.
6. Jeden czar może otrzymać jedną Metamagię; Wzmocniony czar może być połączony
   z jedną wcześniej wybraną Metamagią.

### Atak ukradkowy łotra

Atak ukradkowy pozostaje zdolnością pasywną na karcie bohatera, bez osobnej
karty do skanowania. Resolver dodaje jego obrażenia automatycznie najwyżej raz
na turę, gdy łotr trafia bronią finezyjną lub dystansową i:

- ma przewagę, albo
- aktywny sojusznik stoi obok celu,

oraz łotr nie ma utrudnienia. Premia wynosi 1k6 na poziomach 1–2 i 2k6 na
poziomie 3. UI pokazuje osobno, że Atak ukradkowy został uruchomiony.

## Czary

| Karta / ID | Klasa / rasa | Faza | Docelowe działanie mechaniczne |
|---|---|---|---|
| Kwasowa strzała (`acid_arrow`) | czarodziej / — | COMBAT | Dystansowy atak czarem: trafienie `damage(4k4, kwas)` i `damage(2k4, kwas)` na końcu następnej tury celu; pudło zadaje połowę pierwszych obrażeń. |
| Kwasowy rozprysk (`acid_splash`) | zaklinacz, czarodziej / — | COMBAT | Obrona Zręczności; porażka `damage(1k6, kwas)`, sukces bez obrażeń. |
| Wsparcie (`aid`) | kleryk / — | COMBAT | Maks. 3 cele otrzymują `max_hp_bonus=5` oraz 5 aktualnych PW na 8 godzin; +5 za każdy wyższy poziom komórki. |
| Alarm (`alarm`) | łowca, czarodziej / — | EXPLORATION | Można zagrać wyłącznie przy rozpoczynaniu krótkiego odpoczynku. Ustaw `flag(party, alarmed_rest, do końca odpoczynku)`. Jeżeli podczas odpoczynku nastąpi napad, drużyna nie otrzymuje stanu `surprised`; po uruchomieniu alarmu albo zakończeniu odpoczynku flaga znika. |
| Zmiana siebie (`alter_self`) | zaklinacz, czarodziej / — | EXPLORATION | Gracz wpisuje zamierzoną zmianę wyglądu. Gemini otrzymuje ograniczony prompt i tworzy krótki opis wizualny; zapisz `flag(self, alter_self, generated_description, koncentracja do 1 godz.)`. Flaga wpływa wyłącznie na opis i reakcje NPC — nie zmienia statystyk, ruchu, oddychania ani ataków. |
| Przyjaźń ze zwierzętami (`animal_friendship`) | bard, druid, łowca / — | EXPLORATION | Wybrana bestia wykonuje obronę Mądrości. Po porażce ustaw jej nastawienie na `friendly` wobec rzucającego przez 24 godziny; odblokuj przyjazne reakcje i dialogi. Udana obrona nie zmienia nastawienia. |
| Zwierzęcy posłaniec (`animal_messenger`) | bard, druid / — | USUNĄĆ | Na razie nie trafia do talii ani puli rozwoju; brak wystarczająco konkretnego zastosowania w obecnych scenach. |
| Magiczny zamek (`arcane_lock`) | czarodziej / — | USUNĄĆ | Na razie nie trafia do talii ani puli rozwoju; obecne sceny nie zapewniają użytecznego, powtarzalnego celu dla tego efektu. |
| Magiczna aura arkanisty (`arcanists_magic_aura`) | czarodziej / — | EXPLORATION | Wybierz siebie, istotę albo przedmiot i ustaw `flag(target, magic_detection_blocked, 24 godz.)`. Dopóki flaga jest aktywna, Wykrycie magii i inne systemowe skany magii zwracają dla celu wynik negatywny. |
| Wróżba (`augury`) | kleryk / — | EXPLORATION | Można zagrać tylko w `INTERACTION_TILE_CHOICE`, przed wybraniem opcji kafelka. Gracz wskazuje dokładnie jedną dostępną opcję, np. „wręcz łapówkę”. System kopiuje bieżący stan, symuluje wyłącznie tę jedną gałąź interakcji i pokazuje jej wynik, po czym wykonuje pełny rollback świata, relacji, przedmiotów, PW, zasobów i pozycji. Zużycie samej Wróżby pozostaje. Następnie gracz wraca do pierwotnego wyboru kafelka i może podjąć dowolną rzeczywistą decyzję. |
| Zguba (`bane`) | kleryk, bard / — | COMBAT | Maks. 3 cele wykonują obronę Charyzmy; porażka nakłada `status(bane, -1k4 do ataków i obron, koncentracja do 10 rund)`. |
| Kora (`barkskin`) | druid / — | COMBAT | `status(target, minimum_ac=16, koncentracja do 1 godz.)`. |
| Błogosławieństwo (`bless`) | kleryk, paladyn / — | COMBAT | Maks. 3 cele otrzymują `status(bless, +1k4 do ataków i obron, koncentracja do 10 rund)`; +1 cel za wyższy poziom komórki. |
| Ślepota / głuchota (`blindness_deafness`) | kleryk, bard, zaklinacz, czarodziej / — | COMBAT | Obrona Kondycji; porażka nakłada wybrany `blinded` albo `deafened` na maks. 10 rund, z ponowieniem obrony na końcu tury celu. |
| Rozmycie (`blur`) | zaklinacz, czarodziej / — | COMBAT | `status(self, blurred, koncentracja do 10 rund)`; widzące cele mają utrudnienie w atakach przeciw rzucającemu. |
| Płonące dłonie (`burning_hands`) | zaklinacz, czarodziej / — | COMBAT | Cele w stożku wykonują obronę Zręczności; `damage(3k6, ogień)`, połowa przy sukcesie. |
| Uspokojenie emocji (`calm_emotions`) | kleryk, bard / — | EXPLORATION | Karta jest legalna wyłącznie w oknie `CHARISMA_CHECK_FAILED` po porażce albo krytycznej porażce testu Charyzmy przeciw NPC. Zużyj czar i zmień wynik tego testu na zwykły sukces; anuluj konsekwencje porażki i kontynuuj interakcję od gałęzi sukcesu. |
| Zauroczenie osoby (`charm_person`) | bard, druid, zaklinacz, czarnoksiężnik, czarodziej / — | EXPLORATION | Obrona Mądrości humanoida; porażka daje `flag(target, charmed_by, caster_id, 1 godz.)`. Domyślnie nastawienie NPC rośnie do przyjaznego wobec rzucającego; po końcu NPC wie o czarze. |
| Dotyk chłodu (`chill_touch`) | zaklinacz, czarnoksiężnik, czarodziej / — | COMBAT | Dystansowy atak czarem; trafienie `damage(1k8, nekrotyczne)` i `status(no_healing, do początku następnej tury rzucającego)`. |
| Barwny rozprysk (`color_spray`) | zaklinacz, czarodziej / — | COMBAT | Rzuć pulę 6k10 PW; od celu z najmniejszym aktualnym PW nakładaj `blinded` do końca następnej tury, odejmując pełne PW celu od puli. |
| Rozkaz (`command`) | kleryk, paladyn / — | COMBAT | Obrona Mądrości; porażka nakłada jeden z zamkniętych wariantów na następną turę: `approach`, `drop`, `flee`, `grovel` albo `halt`. |
| Rozumienie języków (`comprehend_languages`) | bard, zaklinacz, czarnoksiężnik, czarodziej / — | EXPLORATION | `flag(self, comprehend_languages, literal_only, 1 godz.)`; odblokuj dosłowne tłumaczenie dialogów i tekstów, ale nie szyfrów ani ukrytych znaczeń. |
| Wieczny płomień (`continual_flame`) | kleryk, czarodziej / — | EXPLORATION | Po zużyciu komponentu `flag(object, permanent_light, bright=20 + dim=20 stóp, do rozproszenia)`; światło nie wytwarza ciepła. |
| Stwórz / zniszcz wodę (`create_or_destroy_water`) | kleryk, druid / — | EXPLORATION | Wybierz `flag(container_or_area, water_created, 10 galonów)` albo usuń do 10 galonów; wariant obszarowy dodaje/usuwa `rain_or_fog` w sześcianie 30 stóp. |
| Leczenie ran (`cure_wounds`) | kleryk, bard, druid, paladyn, łowca / — | COMBAT | Dotyk i `heal(living_target, 1k8 + modyfikator cechy czarowania)`; +1k8 za wyższy poziom komórki. |
| Tańczące światła (`dancing_lights`) | bard, zaklinacz, czarodziej / — | EXPLORATION | `flag(scene, movable_lights, maks. 4 pozycje, koncentracja do 1 min.)`; pozwól akcją przesuwać światła do 60 stóp przy zachowaniu odległości między nimi. |
| Ciemność (`darkness`) | zaklinacz, czarnoksiężnik, czarodziej / — | COMBAT | Utwórz obszar `magical_darkness` o promieniu 15 stóp; blokuje widzenie i linię widzenia zgodnie z regułami przez czas koncentracji. |
| Widzenie w ciemności (`darkvision`) | druid, zaklinacz, czarodziej / — | COMBAT | Nałóż na cel `status(darkvision, range=60 stóp, 8 godz.)` przez ten sam komponent widoczności, którego używają cechy rasowe. Cel ignoruje bojowe ograniczenia zwykłej ciemności w tym zasięgu, ale nie widzi przez magiczną ciemność. |
| Wykrycie dobra i zła (`detect_evil_and_good`) | kleryk, paladyn / — | EXPLORATION | `flag(self, supernatural_detection, typy + miejsca poświęcone/zbezczeszczone, koncentracja do 10 min.)`; `reveal` pasujące obiekty w 30 stopach. |
| Wykrycie magii (`detect_magic`) | kleryk, bard, druid, paladyn, łowca, zaklinacz, czarodziej / — | EXPLORATION | `flag(self, detect_magic, 30 stóp, koncentracja do 10 min.)`; `reveal(magic_source)` oraz akcją pokaż aurę i szkołę widocznego źródła. |
| Wykrycie trucizny i choroby (`detect_poison_and_disease`) | kleryk, druid, paladyn, łowca / — | EXPLORATION | `flag(self, detect_poison_disease, 30 stóp, koncentracja do 10 min.)`; `reveal` źródła i ich zapisany rodzaj. |
| Wykrycie myśli (`detect_thoughts`) | bard, zaklinacz, czarodziej / — | EXPLORATION | `flag(target, thoughts_readable, surface, koncentracja)` po wykryciu celu; głębokie sondowanie wymaga obrony Mądrości i może uruchomić `target_aware`. |
| Zmiana wyglądu (`disguise_self`) | bard, zaklinacz, czarodziej / — | EXPLORATION | `flag(self, disguised, appearance_profile, 1 godz.)`; NPC reagują na profil pozorny, a fizyczny kontakt lub udany test Śledztwa usuwa zaufanie do iluzji. |
| Boska przychylność (`divine_favor`) | paladyn / — | COMBAT | `status(self, weapon_damage_bonus=1k4 radiant, koncentracja do 10 rund)`. |
| Druidztwo (`druidcraft`) | druid / — | EXPLORATION | Wybierz jedną flagę drobnego efektu: `weather_forecast`, `plant_bloom`, `sensory_nature_sign` albo `small_flame_toggle`; scena może ją wykorzystać bez dodatkowych skutków bojowych. |
| Niesamowity podmuch (`eldritch_blast`) | czarnoksiężnik / — | COMBAT | Dystansowy atak czarem; trafienie `damage(1k10, moc)`. |
| Wzmocnienie cechy (`enhance_ability`) | kleryk, bard, druid, zaklinacz / — | EXPLORATION | `flag(target, ability_enhanced, wybrana_cecha, koncentracja do 1 godz.)`; przewaga w testach tej cechy oraz zamknięty dodatkowy bonus wariantu. |
| Powiększenie / pomniejszenie (`enlarge_reduce`) | zaklinacz, czarodziej / — | COMBAT | Niechętny cel: obrona Kondycji. Na koncentrację zmień kategorię rozmiaru, przewagę Siły i obrażenia broni o `+1k4` albo `-1k4`. |
| Oplątanie (`entangle`) | druid / — | COMBAT | Obszar 20 stóp staje się trudnym terenem; porażka obrony Siły nakłada `restrained`. Akcja i udany test Siły usuwa stan. |
| Urzekająca przemowa (`enthrall`) | bard, czarnoksiężnik / — | EXPLORATION | Obrona Mądrości; porażka daje `flag(target, attention_fixed_on, caster_id, 1 min.)`. Domyślnie testy Percepcji dotyczące innych osób mają utrudnienie. |
| Szybki odwrót (`expeditious_retreat`) | zaklinacz, czarnoksiężnik, czarodziej / — | COMBAT | Po rzuceniu i akcją dodatkową w kolejnych turach wykonaj Sprint; efekt wymaga koncentracji. |
| Baśniowy ogień (`faerie_fire`) | bard, druid / — | COMBAT | Cele w obszarze wykonują obronę Zręczności; porażka usuwa korzyści niewidzialności i daje przewagę atakom przeciw celowi na czas koncentracji. |
| Fałszywe życie (`false_life`) | zaklinacz, czarodziej / — | COMBAT | Rzucający otrzymuje `temporary_hp=1k4+4` na 1 godzinę; +5 za wyższy poziom komórki. |
| Powolne opadanie (`feather_fall`) | bard, zaklinacz, czarodziej / — | EXPLORATION | Reakcja: maks. 5 spadających istot otrzymuje `flag(target, safe_fall, speed=60 stóp/rundę, 1 min.)`; lądowanie przed końcem usuwa obrażenia od upadku. |
| Przywołanie chowańca (`find_familiar`) | czarodziej / — | COMBAT | Nie twórz fizycznego aktora ani figurki. Po zagraniu wybierz jeden status do końca walki: **Kot** — `+2 do rzutów obronnych na Zręczność`; **Kruk** — przewaga w rzutach ataku czarem; **Wąż** — odblokuj akcję dodatkową raz na turę: dystansowy rzut ataku czarem do 30 stóp, trafienie `damage(1k6, trucizna)`. Aktywny może być tylko jeden chowaniec; ponowne rzucenie zastępuje poprzedni status. |
| Wykrycie pułapek (`find_traps`) | kleryk, druid / — | COMBAT | Ujawnij wszystkie ukryte pułapki w obszarze działania karty i usuń im flagę `hidden`. Pokaż ich pola, obszary rażenia i znane wyzwalacze; czar nie rozbraja pułapek. |
| Ognisty pocisk (`fire_bolt`) | zaklinacz, czarodziej / — | COMBAT | Dystansowy atak czarem; trafienie `damage(1k10, ogień)`. |
| Ostrze płomieni (`flame_blade`) | druid / — | COMBAT | `status(self, flame_blade, koncentracja)`; odblokuj atak czarem w zwarciu za 3k6 ognia. |
| Płonąca kula (`flaming_sphere`) | druid, czarodziej / — | COMBAT | Utwórz sterowalny obiekt; cele kończące turę obok wykonują obronę Zręczności przeciw 2k6 ognia; akcją dodatkową przesuń kulę do 30 stóp. |
| Lewitujący dysk (`floating_disk`) | czarodziej / — | USUNĄĆ | Na razie nie trafia do talii ani puli rozwoju; transport ładunku nie ma użytecznej mechaniki w obecnym modelu gry. |
| Chmura mgły (`fog_cloud`) | druid, łowca, zaklinacz, czarodziej / — | COMBAT | Utwórz silnie zasłonięty obszar o promieniu 20 stóp na czas koncentracji; +20 stóp promienia za wyższy poziom komórki. |
| Łagodny spoczynek (`gentle_repose`) | kleryk, czarodziej / — | USUNĄĆ | Na razie nie trafia do talii ani puli rozwoju; obecna gra nie śledzi rozkładu zwłok ani terminów wskrzeszenia. |
| Dobre jagody (`goodberry`) | druid, łowca / — | COMBAT | Rzucenie tworzy wspólną pulę `goodberry_charges=10` ważną 24 godziny. Podczas walki zeskanowanie karty otwiera użycie: wybierz legalnego bohatera, wydaj jego akcję i 1 ładunek, aby `heal(target, 1 PW)`. Nowe rzucenie zastępuje niewykorzystaną starą pulę. |
| Śliskość (`grease`) | czarodziej / — | COMBAT | Kwadrat 10 stóp staje się trudnym terenem na 10 rund; wejście lub koniec tury wymaga obrony Zręczności, porażka nakłada `prone`. |
| Wskazówki (`guidance`) | kleryk, druid / — | EXPLORATION | Można zagrać wyłącznie w oknie przed rzutem k20 testu cechy. Ustaw `flag(target, guidance, bonus_die=1k4, na bieżący test)`; po wpisaniu wyniku k20 UI wymaga wyniku 1–4, dodaje go do sumy i usuwa flagę. |
| Pocisk przewodni (`guiding_bolt`) | kleryk / — | COMBAT | Dystansowy atak czarem; trafienie `damage(4k6, promieniste)` i przewaga dla następnego ataku przeciw celowi do końca następnej tury rzucającego. |
| Podmuch wiatru (`gust_of_wind`) | druid, zaklinacz, czarodziej / — | COMBAT | Linia 60×10 stóp; porażka obrony Siły `move(push, 15 stóp)`, ruch pod wiatr kosztuje podwójnie; obszar usuwa obsługiwane gazy. |
| Słowo leczenia (`healing_word`) | kleryk, bard, druid / — | COMBAT | Akcja dodatkowa; `heal(living_target, 1k4 + modyfikator cechy czarowania)`; +1k4 za wyższy poziom komórki. |
| Rozgrzanie metalu (`heat_metal`) | bard, druid / — | COMBAT | `damage(2k8, ogień)` noszącemu metal; obrona Kondycji albo upuszczenie. Podczas koncentracji powtarzaj obrażenia akcją dodatkową. |
| Piekielna reprymenda (`hellish_rebuke`) | czarnoksiężnik / — | COMBAT | Reakcja po otrzymaniu obrażeń; sprawca wykonuje obronę Zręczności i otrzymuje 2k10 ognia, połowę przy sukcesie. |
| Heroizm (`heroism`) | bard, paladyn / — | COMBAT | `status(target, immune_frightened + temp_hp_each_turn=casting_modifier, koncentracja do 10 rund)`. |
| Ohydny śmiech (`hideous_laughter`) | bard, czarodziej / — | COMBAT | Obrona Mądrości; porażka nakłada `prone` i `incapacitated` na czas koncentracji, z ponowieniem obrony po obrażeniach i na końcu tury. |
| Unieruchomienie osoby (`hold_person`) | kleryk, bard, druid, zaklinacz, czarnoksiężnik, czarodziej / — | COMBAT | Humanoid wykonuje obronę Mądrości; porażka nakłada `paralyzed` na czas koncentracji, z ponowieniem na końcu tury. |
| Znak łowcy (`hunters_mark`) | łowca / — | COMBAT | `status(target, hunters_mark, koncentracja)`; trafienia rzucającego bronią zadają +1k6, a po pokonaniu celu znacznik można przenieść akcją dodatkową. |
| Identyfikacja (`identify`) | bard, czarodziej / — | EXPLORATION | Otwórz wyłącznie listę niezidentyfikowanych przedmiotów znajdujących się w ekwipunku drużyny. Wybrany przedmiot otrzymuje trwałą flagę `identified`; pokaż jego właściwości, sposób użycia, wymagane dostrojenie i ładunki. Czar nie działa na obiekty sceny poza ekwipunkiem. |
| Iluzoryczne pismo (`illusory_script`) | bard, czarnoksiężnik, czarodziej / — | USUNĄĆ | Na razie nie trafia do talii ani puli rozwoju; brak powtarzalnego zastosowania w obecnych interakcjach. |
| Zadawanie ran (`inflict_wounds`) | kleryk / — | COMBAT | Atak czarem w zwarciu; trafienie `damage(3k10, nekrotyczne)`, +1k10 za wyższy poziom komórki. |
| Niewidzialność (`invisibility`) | bard, zaklinacz, czarnoksiężnik, czarodziej / — | COMBAT | Nałóż `status(invisible, koncentracja do 1 godz.)`. Cel nie może być normalnie wskazany przez wroga bez zdolności wykrywania, a jego pierwszy atak ma przewagę. Status kończy się natychmiast po ataku lub rzuceniu czaru. |
| Skok (`jump`) | druid, łowca, zaklinacz, czarodziej / — | USUNĄĆ | Na razie nie trafia do talii ani puli rozwoju; plansza nie ma jeszcze osobnej, wartościowej mechaniki skoku. |
| Kołatka (`knock`) | bard, zaklinacz, czarodziej / — | EXPLORATION | Usuń jedną obsługiwaną blokadę z obiektu; `arcane_locked` zostaje stłumione na 10 minut. Wyemituj `loud_noise(radius=300 stóp)`. |
| Pomniejsze przywrócenie (`lesser_restoration`) | kleryk, bard, druid / — | COMBAT | Usuń z celu jeden wybrany stan: `blinded`, `deafened`, `paralyzed`, `poisoned` albo `diseased`. |
| Lewitacja (`levitate`) | zaklinacz, czarodziej / — | COMBAT | Nałóż na wybrany przyjazny cel `status(levitating, koncentracja do 10 min.)`. Podczas ruchu cel ignoruje dodatkowy koszt i kary pochodzące z trudnego terenu; efekt nie zmienia wysokości, nie daje lotu i nie pozwala przekraczać niedostępnych pól. |
| Światło (`light`) | bard, zaklinacz, czarodziej / — | EXPLORATION | `flag(object, light, bright=20 + dim=20 stóp, 1 godz.)`; system widoczności aktualizuje oświetlenie sceny. |
| Odnalezienie zwierząt lub roślin (`locate_animals_or_plants`) | bard, druid / — | EXPLORATION | `reveal(nearest_species, gatunek + promień 5 mil)`; scena zwraca kierunek i dystans albo brak wyniku. |
| Odnalezienie przedmiotu (`locate_object`) | kleryk, bard, druid, czarodziej / — | EXPLORATION | `flag(self, find_item, opis_przedmiotu + promień=1000 stóp, koncentracja do 10 min.)`; scena zwraca kierunek, a przy ruchu także kierunek przemieszczania. |
| Długonogi (`longstrider`) | bard, druid, łowca, czarodziej / — | EXPLORATION | `flag(target, exploration_speed_bonus=10 stóp, 1 godz.)`; zmniejsza koszt obsługiwanych przejść i pościgów, nie modyfikuje inicjatywy bojowej. |
| Zbroja maga (`mage_armor`) | zaklinacz, czarodziej / — | COMBAT | Nieopancerzony cel otrzymuje bazowe `KP=13 + modyfikator Zręczności` na 8 godzin. |
| Dłoń maga (`mage_hand`) | bard, zaklinacz, czarnoksiężnik, czarodziej / — | EXPLORATION | `flag(scene, mage_hand, pozycja + udźwig=10 funtów, 1 min.)`; odblokuj zdalne, niemagiczne interakcje przedmiotowe bez atakowania i aktywowania magicznych przedmiotów. |
| Magiczny pocisk (`magic_missile`) | zaklinacz, czarodziej / — | COMBAT | Utwórz 3 pociski; każdy automatycznie `damage(1k4+1, moc)` wybranemu widocznemu celowi. |
| Magiczne usta (`magic_mouth`) | bard, czarodziej / — | USUNĄĆ | Na razie nie trafia do talii ani puli rozwoju; system nie obsługuje trwałych, konfigurowalnych wyzwalaczy wiadomości. |
| Magiczna broń (`magic_weapon`) | czarodziej / — | COMBAT | `status(weapon, magical + attack_bonus=1 + damage_bonus=1, koncentracja)` na niemagicznej broni. |
| Naprawa (`mending`) | bard, druid, zaklinacz, czarodziej / — | EXPLORATION | Usuń z obiektu jedną flagę `minor_break` lub `minor_tear` do 1 stopy; nie przywraca utraconych części ani magii. |
| Wiadomość (`message`) | bard, zaklinacz, czarodziej / — | USUNĄĆ | Na razie nie trafia do talii ani puli rozwoju; prywatna komunikacja nie daje obecnie odrębnej, użytecznej konsekwencji mechanicznej. |
| Pomniejsza iluzja (`minor_illusion`) | bard, zaklinacz, czarnoksiężnik, czarodziej / — | EXPLORATION | `flag(area, minor_illusion, image_or_sound_profile, 1 min.)`; scena może odwrócić uwagę NPC, a fizyczny kontakt lub udane Śledztwo oznacza iluzję jako rozpoznaną. |
| Lustrzane odbicia (`mirror_image`) | zaklinacz, czarnoksiężnik, czarodziej / — | COMBAT | Dodaj 3 duplikaty; przy każdym ataku przeciw rzucającemu wykonaj rzut przekierowania. Trafiony duplikat o KP `10 + Zręczność` znika. |
| Mglisty krok (`misty_step`) | zaklinacz, czarnoksiężnik, czarodziej / — | COMBAT | Akcja dodatkowa: teleportuj rzucającego do 30 stóp na widoczne legalne pole. |
| Księżycowy promień (`moonbeam`) | druid / — | COMBAT | Utwórz cylinder promienia 5 stóp; wejście lub start tury: obrona Kondycji przeciw 2k10 obrażeń promienistych, połowa przy sukcesie. Akcją przesuń obszar do 60 stóp. |
| Przejście bez śladu (`pass_without_trace`) | druid / — | EXPLORATION | `flag(party_in_aura, stealth_boost=10 + no_tracks, koncentracja do 1 godz.)`; modyfikuje testy skradania oraz reakcje patroli i tropicieli. |
| Trujący rozprysk (`poison_spray`) | druid, zaklinacz, czarnoksiężnik, czarodziej / — | COMBAT | Obrona Kondycji; porażka `damage(1k12, trucizna)`, sukces bez obrażeń. |
| Modlitwa leczenia (`prayer_of_healing`) | kleryk / — | COMBAT | Po czasie rzucania maks. 6 żywych celów otrzymuje `heal(2k8 + modyfikator cechy czarowania)`; +1k8 za wyższy poziom komórki. |
| Drobne czary (`prestidigitation`) | bard, zaklinacz, czarnoksiężnik, czarodziej / — | EXPLORATION | Wybierz jedną drobną flagę: `sensory_effect`, `ignite_or_snuff`, `clean_or_soil`, `flavor`, `mark` albo `trinket`; maks. 3 trwałe efekty jednocześnie. |
| Stworzenie płomienia (`produce_flame`) | druid / — | COMBAT | Dystansowy atak czarem; trafienie `damage(1k8, ogień)`. |
| Ochrona przed dobrem i złem (`protection_from_evil_and_good`) | kleryk, paladyn, czarnoksiężnik, czarodziej / — | COMBAT | `status(target, protected_from_supernatural, koncentracja)`: wskazane typy mają utrudnienie w atakach i nie mogą nałożyć zauroczenia, strachu ani opętania. |
| Ochrona przed trucizną (`protection_from_poison`) | kleryk, druid / — | COMBAT | Usuń jedną truciznę; przez 1 godzinę cel ma przewagę w obronach przeciw zatruciu i odporność na obrażenia od trucizny. |
| Oczyszczenie jadła i napoju (`purify_food_and_drink`) | kleryk, druid, paladyn / — | EXPLORATION | Usuń z żywności i napojów w obszarze flagi `poisoned_food` i `diseased_food`; oznacz je `safe_to_consume`. |
| Promień osłabienia (`ray_of_enfeeblement`) | czarnoksiężnik, czarodziej / — | COMBAT | Dystansowy atak czarem; trafienie nakłada `status(weakened_strength_damage=half, koncentracja)`, z obroną Kondycji na końcu tury. |
| Promień mrozu (`ray_of_frost`) | zaklinacz, czarodziej / — | COMBAT | Dystansowy atak czarem; trafienie `damage(1k8, zimno)` i `speed_penalty=10 stóp` do początku następnej tury rzucającego. |
| Odporność (`resistance`) | druid / — | COMBAT | `status(target, resistance_die=1k4, koncentracja do 10 rund)`; cel może zużyć kość przy jednym rzucie obronnym. |
| Sztuczka z liną (`rope_trick`) | czarodziej / — | EXPLORATION | `flag(area, extradimensional_shelter, capacity=8, 1 godz.)`; odblokuj wejście/wyjście i bezpieczne ukrycie po wciągnięciu liny. |
| Święty płomień (`sacred_flame`) | kleryk / — | COMBAT | Obrona Zręczności ignorująca premię osłony; porażka `damage(1k8, promieniste)`, sukces bez obrażeń. |
| Sanktuarium (`sanctuary`) | kleryk / — | COMBAT | Przez 10 rund napastnik przed atakiem lub wrogim czarem wykonuje obronę Mądrości; porażka wymusza inny cel albo utratę działania. Wrogi efekt podopiecznego kończy ochronę. |
| Palący promień (`scorching_ray`) | zaklinacz, czarodziej / — | COMBAT | Wykonaj 3 osobne dystansowe ataki czarem; każde trafienie `damage(2k6, ogień)`, +1 promień za wyższy poziom komórki. |
| Widzenie niewidzialnego (`see_invisibility`) | bard, zaklinacz, czarodziej / — | COMBAT | Nałóż na rzucającego `status(see_hidden_and_invisible, 1 godz.)`. Natychmiast ujawnij mu wszystkich przeciwników oznaczonych jako `hidden` albo `invisible` w obsługiwanym zasięgu widzenia; stają się legalnymi celami i są podświetlani na planszy dla tego gracza. |
| Roztrzaskanie (`shatter`) | bard, zaklinacz, czarnoksiężnik, czarodziej / — | COMBAT | Cele w obszarze wykonują obronę Kondycji; `damage(3k8, grzmot)`, połowa przy sukcesie. |
| Tarcza (`shield`) | zaklinacz, czarodziej / — | COMBAT | Reakcja po trafieniu: `AC_bonus=5` do początku następnej tury; ponownie oceń atak, który uruchomił reakcję. |
| Tarcza wiary (`shield_of_faith`) | kleryk, paladyn / — | COMBAT | `status(target, AC_bonus=2, koncentracja do 10 min.)`. |
| Kostur bojowy (`shillelagh`) | druid / — | COMBAT | `status(weapon, magical + use_casting_ability + damage_die=1k8, 1 min.)` dla trzymanej pałki lub kostura. |
| Porażający dotyk (`shocking_grasp`) | zaklinacz, czarodziej / — | COMBAT | Atak czarem w zwarciu; trafienie `damage(1k8, błyskawice)` i blokada reakcji celu do początku jego następnej tury. |
| Cisza (`silence`) | kleryk, bard / — | COMBAT | Utwórz sferę 20 stóp na czas koncentracji: blokuj dźwięk, efekty zależne od słuchu i rzucanie czarów z komponentem werbalnym. |
| Cichy obraz (`silent_image`) | bard, zaklinacz, czarodziej / — | EXPLORATION | `flag(area, visual_illusion, profile + pozycja, koncentracja do 10 min.)`; akcją przesuń iluzję, kontakt lub udane Śledztwo oznacza ją jako rozpoznaną. |
| Sen (`sleep`) | bard, zaklinacz, czarodziej / — | COMBAT | Rzuć pulę 5k8 PW; od celu z najmniejszym aktualnym PW nakładaj `unconscious` na 10 rund, odejmując pełne PW. Obrażenia lub akcja sojusznika budzą. |
| Oszczędź umierającego (`spare_the_dying`) | kleryk / — | COMBAT | Ustaw żywy cel z 0 PW jako `stable`; nie działa na konstrukty i nieumarłych. |
| Rozmowa ze zwierzętami (`speak_with_animals`) | bard, druid, łowca / — | EXPLORATION | `flag(self, animal_speech, 10 min.)`; bestie stają się legalnymi rozmówcami i mogą udostępnić zapisane informacje, bez automatycznej zmiany nastawienia. |
| Pajęcza wspinaczka (`spider_climb`) | zaklinacz, czarnoksiężnik, czarodziej / — | EXPLORATION | `flag(target, spider_climb, speed=base_speed, koncentracja do 1 godz.)`; odblokuj ruch po ścianach i suficie bez użycia rąk. |
| Kolczaste zarośla (`spike_growth`) | druid / — | COMBAT | Obszar o promieniu 20 stóp jest trudnym terenem; każde 5 stóp ruchu w nim zadaje 2k4 obrażeń kłutych. |
| Duchowa broń (`spiritual_weapon`) | kleryk / — | COMBAT | Utwórz broń na 10 rund; przy rzuceniu i później akcją dodatkową wykonaj atak czarem za `1k8 + modyfikator cechy` obrażeń od mocy, po przesunięciu do 20 stóp. |
| Sugestia (`suggestion`) | bard, zaklinacz, czarnoksiężnik, czarodziej / — | EXPLORATION | Obrona Mądrości; porażka daje `flag(target, compelled_suggestion, normalized_intent, koncentracja do 8 godz.)`. Scena wybiera obsługiwane wykonanie; jawnie samobójcza sugestia jest nielegalna. |
| Fala gromu (`thunderwave`) | bard, druid, zaklinacz, czarodziej / — | COMBAT | Cele w obszarze wykonują obronę Kondycji; porażka `damage(2k8, grzmot)` i `move(push, 10 stóp)`, sukces połowa bez przesunięcia. |
| Pewne trafienie (`true_strike`) | bard, zaklinacz, czarnoksiężnik, czarodziej / — | COMBAT | `status(self, true_strike_target=cel, koncentracja do następnej tury)`; pierwszy atak rzucającego przeciw celowi w następnej turze ma przewagę i zużywa efekt. |
| Niewidzialny sługa (`unseen_servant`) | bard, czarnoksiężnik, czarodziej / — | EXPLORATION | `flag(scene, unseen_servant, position + simple_task, 1 godz.)`; odblokuj zdalne proste interakcje fizyczne w 15 stopach od sługi. |
| Zjadliwa kpina (`vicious_mockery`) | bard / — | COMBAT | Obrona Mądrości; porażka `damage(1k4, psychiczne)` i utrudnienie w następnym ataku celu przed końcem jego następnej tury. |
| Więź ochronna (`warding_bond`) | kleryk / — | COMBAT | Przez 1 godzinę cel ma +1 KP, +1 do obron i odporność na obrażenia; po każdych obrażeniach celu rzucający otrzymuje tę samą wartość. Zerwij powyżej 60 stóp. |
| Sieć (`web`) | zaklinacz, czarodziej / — | COMBAT | Obszar 20 stóp jest lekkim zasłonięciem i trudnym terenem; porażka obrony Zręczności nakłada `restrained`, usuwane akcją i testem Siły przeciw ST czaru. |
| Strefa prawdy (`zone_of_truth`) | kleryk, bard / — | EXPLORATION | Istoty w obszarze wykonują obronę Charyzmy; porażka daje `flag(target, cannot_knowingly_lie, caster_knows_result, 10 min.)`. Dialog blokuje świadomie fałszywe odpowiedzi, ale pozwala milczeć. |

## Otwarte decyzje do przeglądu przy czarach

1. Czy leczenie i usuwanie stanów zawsze zostawiamy w `COMBAT`, nawet jeśli
   technicznie można ich użyć poza walką? W tabeli przyjęto jedną kartę i jedną
   fazę, bez duplikatów.
2. Czy `Przedłużony czar` ma pozostać wyłącznie bojowy? Obecna propozycja nie
   pozwala nim przedłużać flag eksploracyjnych.
3. Czy `Subtelny czar` ma być wyłącznie eksploracyjny? W tej wersji służy do
   ukrywania aktu rzucania, a nie do omijania bojowego `silence`.
4. Czy nieobsługiwana przez konkretną scenę flaga ma zawsze używać efektu
   domyślnego z tej tabeli, czy gra ma odmówić zużycia karty przed
   zatwierdzeniem?

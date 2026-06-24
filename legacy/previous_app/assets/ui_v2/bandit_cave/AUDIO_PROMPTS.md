# Player UI Bandit Cave - lista elementow do audio

Plik zbiera elementy graficzne i tekstowe z `player_ui` oraz `assets/ui_v2/bandit_cave`, ktore warto przerobic na audio dla scenariusza `bandit_cave`.

Zalozenia dla wszystkich promptow:
- docelowy format w projekcie: `.mp3`,
- nazwy plikow ponizej pasuja do katalogu `assets/ui_v2/bandit_cave/audio/`,
- jezyk voiceoverow: polski,
- klimat: fantasy PF2e, bandycka jaskinia, kontrabanda, podziemne doki,
- Player UI ma byc czytelne przy stole, wiec audio powinno byc krotkie i funkcjonalne,
- bez muzyki z rozpoznawalnych utworow i bez nazw marek poza nazwami z gry,
- exportuj normalizowany plik bez dlugiej ciszy na poczatku i koncu.

Workflow ElevenLabs:
- `audio/voiceover/*`: uzyj ElevenLabs Text to Speech z juz przygotowanymi glosami. Nie wklejaj opisow glosu do pola tekstu. Wklej sam `Tekst do TTS`, a `Wykonanie` potraktuj jako wskazowke przy iteracji, tempie, pauzach i ewentualnym montazu.
- `audio/sfx/*`: uzyj ElevenLabs Sound Effects. Prompt wklej jako opis efektu. Generuj pojedynczy, krotki wariant bez narracji, chyba ze prompt wyraznie prosi o glos.
- `audio/music/*`: uzyj ElevenLabs Sound Effects / ambience generation. Traktuj je jako tlo lub petle. Jesli narzedzie nie gwarantuje idealnej petli, wygeneruj spokojny wariant z rownym poczatkiem i koncem, bez mocnego wejscia.
- Elementy typu `voiceover + subtelny SFX`: najpierw wygeneruj czysty TTS, potem osobno delikatny SFX/ambience i zmiksuj cicho pod spodem.
- Zalecany poziom glosnosci: voiceover na pierwszym planie, ambience wyraznie ciszej, SFX UI krotkie i nieagresywne.

## Priorytet MVP - pliki juz wskazane przez manifest

### 1. Lektor: intro scenariusza
- Zrodlo tekstu: `player_ui/content/bandit_cave.json` -> `briefing_intro`
- Docelowy plik: `audio/voiceover/intro_001.mp3`
- Typ: voiceover
- Wykonanie: spokojne tempo, wyrazne pauzy po stawce misji i po opisie ukrytych przejsc. Narastajace napiecie bez patosu.
- Tekst do TTS:

```text
Drużyna schodzi do bandyckiej jaskini, żeby przeciąć szlak kontrabandy, zanim ostatni transport zniknie w podziemnych dokach.

Wejściowa grota jest tylko pierwszą warstwą kryjówki. Dalej czekają ukryte przejścia, skarbiec z dowodami i nabrzeże, przy którym przemytnicy trzymają łódź gotową do odpłynięcia.

Wasz cel jest prosty: przeżyć zejście, oczyścić doki i przejąć statek, zanim bandyci odzyskają kontrolę nad szlakiem.
```

### 2. Lektor: szczekanie psa jako podpowiedz
- Zrodlo tekstu: `scenario_flows/bandit_cave.json` -> event `cave_intro`
- Docelowy plik: `audio/voiceover/hint_dog_barking_001.mp3`
- Typ: voiceover + subtelny SFX
- Wykonanie: krotka, praktyczna wskazowka. Pauza przed ostatnim zdaniem.
- Tekst do TTS:

```text
Z głębi jaskini dochodzi szuranie butów po kamieniu. Po chwili słychać krótkie, urwane szczeknięcie.

Ktoś albo coś pilnuje dalszego przejścia.
```

- SFX do zmiksowania cicho pod spodem:

```text
Odlegle szczekniecie psa w kamiennym tunelu, bardzo cichy poglos jaskini, bez jumpscare i bez dominowania nad narracja.
```

### 3. Muzyka: petla napiecia jaskini
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `music.default`
- Docelowy plik: `audio/music/cave_tension_loop.mp3`
- Typ: loop muzyczny
- Prompt do ElevenLabs:

```text
Stworz petle muzyczna do Player UI, scenariusz Bandit Cave. Dlugosc 45-60 sekund, seamless loop. Klimat: skradanie w jaskini bandytow, kontrabanda, niepewnosc przed walka. Instrumentarium: niskie drony, pojedyncze uderzenia bebna ramowego, szorstkie smyczki lub lira korbowa bardzo subtelnie. Tempo wolne, bez melodii wpadajacej w ucho, bez epickiego refrenu. Mix ma zostawiac miejsce na dialog lektora i dzwieki UI.
```

### 4. Ambience: wejscie do jaskini
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `music.cave_entrance`
- Docelowy plik: `audio/music/cave_entrance_ambience.mp3`
- Typ: ambience loop
- Prompt do ElevenLabs:

```text
Stworz ambientowa petle tla dla Player UI, mapa Cave Entrance w scenariuszu Bandit Cave. Dlugosc 45-60 sekund, seamless loop. Brzmienie: krople wody, cichy przeciag w kamiennym tunelu, odlegle skrzypniecia drewna, pojedyncze stlumione odglosy bandytow daleko w glebi. Bez wyraznej muzyki, bez glosnych jumpscare, bez rozpoznawalnych slow. Ma dzialac pod narracja i kliknieciami UI.
```

### 5. SFX UI: potwierdzenie wyboru
- Zrodlo graficzne/UI: `images/placeholders/default_choice.svg`, przyciski wyboru w `player_ui/static/app.js`
- Docelowy plik: `audio/sfx/choice_confirm.mp3`
- Typ: SFX UI
- Prompt do ElevenLabs:

```text
Wygeneruj krotki dzwiek UI dla Player UI, scenariusz Bandit Cave: potwierdzenie wyboru opcji. Czas: 0.25-0.5 sekundy. Brzmienie: cichy klik drewnianego znacznika na stole plus lekki metaliczny akcent, jak moneta lub nit przy skorzanym pasku. Ma byc czytelny, ale nie agresywny. Bez melodii.
```

### 6. SFX UI: aktywny aktor
- Zrodlo graficzne/UI: panel `Aktywna inicjatywa`, assety aktorow i przeciwnikow
- Docelowy plik: `audio/sfx/active_actor.mp3`
- Typ: SFX UI
- Prompt do ElevenLabs:

```text
Wygeneruj krotki dzwiek UI dla Player UI oznaczajacy zmiane aktywnego aktora w inicjatywie. Czas: 0.35-0.7 sekundy. Klimat Bandit Cave: szybki niski puls, przesuniecie pionka po drewnie, delikatny poglos jaskini. Dzwiek ma informowac, ze teraz czyjas tura jest aktywna. Bez alarmu i bez triumfalnej melodii.
```

## Teksty scenariusza do voiceoverow

### 7. Start: wejscie do jaskini
- Zrodlo tekstu: `scenario_flows/bandit_cave.json` -> `cave_intro`
- Proponowany plik: `audio/voiceover/cave_intro_001.mp3`
- Wykonanie: opis lokacji, cicho i napiecie. Pierwsze zdanie wolniej, ostatnie bardziej informacyjnie.
- Tekst do TTS:

```text
Stoisz przed wejściem do jaskini bandytów. Kamień przy progu jest wilgotny, a ślady prowadzą głębiej, w stronę nierównego tunelu.

Z ciemności dochodzi ruch, jakby ktoś przesuwał skrzynie albo broń po ziemi. Po chwili ciszę przecina szczekanie psa.

Przejście nie jest puste. Drużyna ma kilka oddechów, zanim kryjówka zorientuje się, że ktoś nadchodzi.
```

### 8. Odkrycie sekretnego przejscia
- Zrodlo tekstu: `scenario_flows/bandit_cave.json` -> `secret_discovered`
- Proponowany plik: `audio/voiceover/secret_passage_found_001.mp3`
- Wykonanie: ostrozna satysfakcja, ale bez triumfu. Dobra pauza przed wzmianka o skarbcu.
- Tekst do TTS:

```text
Kamienna szczelina okazuje się czymś więcej niż pęknięciem w ścianie. Po odsunięciu luźnego fragmentu widać wąskie przejście, ukryte przed każdym, kto idzie głównym tunelem.

To musi prowadzić do skarbca. Bandyci nie zostawiliby takiego przejścia bez powodu, a to znaczy, że po drugiej stronie może czekać coś cennego albo coś dobrze zabezpieczonego.
```

### 9. Jaskinia oczyszczona
- Zrodlo tekstu: `scenario_flows/bandit_cave.json` -> `cave_cleared`
- Proponowany plik: `audio/voiceover/cave_cleared_001.mp3`
- Wykonanie: po walce, lekka ulga, tempo rzeczowe.
- Tekst do TTS:

```text
Główna sala jaskini cichnie. Ostatnie echo walki odpływa między kamiennymi ścianami, a przy wejściu zostają tylko porzucone ślady bandyckiej warty.

Teraz możecie bezpieczniej przeszukać zakamarki, sprawdzić ukryte przejście albo zejść głównym tunelem do doków. Szlak kontrabandy jeszcze się nie kończy.
```

### 10. Wejscie do skarbca
- Zrodlo tekstu: `scenario_flows/bandit_cave.json` -> `treasure_intro`
- Proponowany plik: `audio/voiceover/treasure_intro_001.mp3`
- Wykonanie: skupiony opis pomieszczenia, ostrzegawcza pauza przed pulapka.
- Tekst do TTS:

```text
W skarbcu stoją ciężkie skrzynie, mokre beczki i pakunki owinięte płótnem. Między nimi leżą księgi rachunkowe, listy przewozowe i drobne znaki, które łączą tę kryjówkę z większym szlakiem kontrabandy.

Nie wszystko wygląda jednak na porzucone w pośpiechu. Jedna ze skrytek jest ustawiona zbyt równo, a przy podłodze widać ślad ukrytego mechanizmu.

Kto ruszy łup bez ostrożności, może uruchomić pułapkę.
```

### 11. Wejscie do dokow
- Zrodlo tekstu: `scenario_flows/bandit_cave.json` -> `docks_intro`
- Proponowany plik: `audio/voiceover/docks_intro_001.mp3`
- Wykonanie: final scenariusza coraz blizej, ale nadal opisowo.
- Tekst do TTS:

```text
Tunel opada niżej i otwiera się na podziemne doki. Woda odbija słabe światło, a przy nabrzeżu kołysze się łódź przygotowana do odpłynięcia.

Na deskach leżą liny, skrzynie i resztki załadunku. Jeśli przemytnicy utrzymają ten pomost, kontrabanda zniknie razem z dowodami.

To tutaj trzeba przerwać szlak.
```

### 12. Doki oczyszczone
- Zrodlo tekstu: `scenario_flows/bandit_cave.json` -> `docks_cleared`
- Proponowany plik: `audio/voiceover/docks_cleared_001.mp3`
- Wykonanie: finalna ulga, bez fanfar. Ostatnie zdanie wyraznie domyka cel.
- Tekst do TTS:

```text
Ostatni strażnicy doków padli, a nabrzeże wreszcie przestaje odpowiadać krzykiem i stalą. Zostaje chlupot wody, skrzypienie pomostu i statek przemytników przywiązany do pala.

Załoga nie zdążyła odpłynąć. Łódź jest bez nadzoru, kontrabanda nadal na miejscu, a drużyna może przejąć wyjście z jaskini.
```

### 13. Final: ucieczka statkiem
- Zrodlo tekstu: `scenario_flows/bandit_cave.json` -> `escape_by_ship`, `player_ui/content/bandit_cave.json` -> `result_summary`
- Proponowany plik: `audio/voiceover/escape_ship_ending_001.mp3`
- Wykonanie: zamkniecie przygody, spokojna satysfakcja. Pauza przed podsumowaniem skutkow.
- Tekst do TTS:

```text
Liny spadają z pala, a przejęty statek powoli odbija od podziemnego nabrzeża. Za rufą zostają ciemne doki, rozbite posterunki i szlak, który jeszcze chwilę temu miał wynieść kontrabandę poza zasięg prawa.

Drużyna przejęła łódź przemytników, zatrzymała transport i zabezpieczyła dowody ukryte w jaskini.

Scenariusz zakończony. Szlak kontrabandy został przerwany.
```

## Teksty ekranu Player UI do krotkich komunikatow

### 14. Start Hall
- Zrodlo tekstu: `player_ui/templates/index.html`
- Proponowany plik: `audio/voiceover/ui_start_hall_001.mp3`
- Wykonanie: jasny komunikat startowy, bez teatralnego przeciagania.
- Tekst do TTS:

```text
Szlak kontrabandy zaczyna się tutaj. Gdy drużyna jest gotowa, rozpocznij nową grę i przejdź do odprawy.
```

### 15. Party Assembly
- Zrodlo tekstu: `player_ui/templates/index.html` -> `Zbierz drużynę`
- Proponowany plik: `audio/voiceover/ui_party_assembly_001.mp3`
- Wykonanie: funkcjonalne tempo, wyrazny zakres liczby bohaterow.
- Tekst do TTS:

```text
Zbierz drużynę. Wybierz od jednego do czterech bohaterów, zanim rozpocznie się briefing i zejście do jaskini.
```

### 16. Mission Briefing
- Zrodlo tekstu: `player_ui/content/bandit_cave.json` -> `briefing_title`, `stakes`
- Proponowany plik: `audio/voiceover/ui_mission_briefing_001.mp3`
- Wykonanie: konkretnie, z naciskiem na stawke.
- Tekst do TTS:

```text
Misja: Szlak Kontrabandy.

Wejście prowadzi przez jaskinię bandytów, ale prawdziwy cel znajduje się niżej, w podziemnych dokach. Jeśli załoga odpłynie, kontrabanda zniknie wraz z dowodami i łupem.

Oczyść trasę, znajdź to, co ukryte, i przejmij łódź zanim przemytnicy uciekną.
```

### 17. Czekam na wydarzenia
- Zrodlo tekstu: `player_ui/templates/index.html` i `player_ui/static/app.js`
- Proponowany plik: `audio/voiceover/ui_waiting_for_events_001.mp3`
- Wykonanie: neutralnie, bez napiecia.
- Tekst do TTS:

```text
Czekam na wydarzenia.
```

### 18. Runtime error
- Zrodlo tekstu: `player_ui/templates/index.html` -> `Błąd połączenia`
- Proponowany plik: `audio/voiceover/ui_runtime_error_001.mp3`
- Wykonanie: spokojny komunikat techniczny, bez paniki.
- Tekst do TTS:

```text
Błąd połączenia. Sprawdź runtime i spróbuj ponownie.
```

- SFX do zmiksowania przed komunikatem:

```text
Bardzo krotki, niski i nienachalny dzwiek ostrzegawczy UI, bez alarmu i bez melodii.
```

### 19. Scenariusz zakonczony
- Zrodlo tekstu: `player_ui/static/app.js` -> fallback result
- Proponowany plik: `audio/voiceover/ui_scenario_finished_001.mp3`
- Wykonanie: finalnie, spokojnie.
- Tekst do TTS:

```text
Scenariusz zakończony.
```

## Elementy graficzne jako SFX lub earcony

### 20. Akcja: Ruch / Stride
- Zrodlo grafiki: `images/actions/stride.svg`
- Proponowany plik: `audio/sfx/action_stride.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX dla ikony akcji "Ruch / Stride" w Player UI, Bandit Cave. Czas: 0.4-0.8 sekundy. Brzmienie: dwa szybkie kroki po wilgotnym kamieniu, lekki poglos jaskini. Dzwiek ma byc subtelny i pasowac do klikniecia akcji, bez glosu.
```

### 21. Akcja: Strike / Attack
- Zrodlo grafiki: `images/actions/strike.svg`
- Proponowany plik: `audio/sfx/action_strike.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX dla ikony akcji "Strike / Attack" w Player UI, Bandit Cave. Czas: 0.35-0.7 sekundy. Brzmienie: krotkie swisniecie ostrza i stlumione uderzenie w skore lub drewno, bez krzyku i bez gore. Ma byc czytelny jako akcja bojowa.
```

### 22. Akcja: Interact
- Zrodlo grafiki: `images/actions/interact.svg`
- Proponowany plik: `audio/sfx/action_interact.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX dla ikony "Interact" w Player UI, Bandit Cave. Czas: 0.35-0.7 sekundy. Brzmienie: dlon dotykajaca starej skrzyni, drobne skrzypniecie zawiasu, lekki metaliczny detal. Bez glosu.
```

### 23. Akcja: Seek
- Zrodlo grafiki: `images/actions/seek.svg`
- Proponowany plik: `audio/sfx/action_seek.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX dla ikony "Seek" w Player UI, Bandit Cave. Czas: 0.5-0.9 sekundy. Brzmienie: ciche przesuniecie kamyka, skupiony niski ton, delikatne odkrycie szczegolu. Ma sugerowac przeszukiwanie jaskini, nie magie.
```

### 24. Akcja: End Turn
- Zrodlo grafiki: `images/actions/end_turn.svg`
- Proponowany plik: `audio/sfx/action_end_turn.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX dla ikony "End Turn" w Player UI. Czas: 0.35-0.6 sekundy. Brzmienie: pionek odstawiany na plansze i krotki niski klik. Neutralne, bez poczucia porazki ani sukcesu.
```

### 25. Akcja: Raise Shield / Defend
- Zrodlo grafiki: `images/actions/defend.svg`
- Proponowany plik: `audio/sfx/action_raise_shield.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX dla ikony "Raise Shield / Defend" w Player UI, Bandit Cave. Czas: 0.45-0.8 sekundy. Brzmienie: tarcza podnoszona na przedramieniu, skora napieta na pasku, delikatny metaliczny rezonans. Ma byc obronne, zwarte, bez dlugiego wybrzmienia.
```

### 26. Przeciwnik: Bandit
- Zrodlo grafiki: `images/enemies/bandit.svg`
- Proponowany plik: `audio/sfx/enemy_bandit_turn.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj krotki earcon dla pojawienia sie lub tury przeciwnika "Bandit" w Player UI, Bandit Cave. Czas: 0.8-1.2 sekundy. Brzmienie: krok po kamieniu, skorzany pas, krotki nieartykulowany pomruk daleko w poglosie. Bez slow, bez przesady.
```

### 27. Przeciwnik: Bandit Sharpshot
- Zrodlo grafiki: `images/enemies/bandit_sharpshot.svg`
- Proponowany plik: `audio/sfx/enemy_bandit_sharpshot_turn.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj earcon dla przeciwnika "Bandit Sharpshot" w Player UI, Bandit Cave. Czas: 0.8-1.3 sekundy. Brzmienie: napinana cieciwa lub kusza, delikatny klik mechanizmu, cichy oddech w jaskini. Bez wystrzalu jako glosnego efektu, bo to tylko identyfikacja przeciwnika.
```

### 28. Przeciwnik: Guard Dog / Cave Hound / Dock Hound
- Zrodlo grafiki: `images/enemies/guard_dog.svg`
- Proponowany plik: `audio/sfx/enemy_guard_dog_turn.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj earcon dla psa strazniczego w Player UI, Bandit Cave. Czas: 0.8-1.2 sekundy. Brzmienie: niski warkot i szybkie pazury na kamieniu, z poglosem jaskini. Bez glosnego szczekania, aby nie meczylo przy powtarzaniu tur.
```

### 29. Narrator / Mistrz gry
- Zrodlo grafiki: `images/characters/narrator.svg`
- Proponowany plik: `audio/sfx/narrator_notice.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj krotki earcon dla komunikatu narratora w Player UI, Bandit Cave. Czas: 0.5-0.9 sekundy. Brzmienie: niski, cieply ton jak otwarcie ksiegi plus delikatny poglos kamiennej sali. Ma sygnalizowac, ze zaraz pojawi sie tekst mistrza gry.
```

## Czary jako krotkie SFX

### 30. Acid Splash
- Zrodlo grafiki: `images/spells/acid_splash.svg`
- Proponowany plik: `audio/sfx/spell_acid_splash.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX dla czaru "Acid Splash" w Player UI, Bandit Cave. Czas: 0.8-1.4 sekundy. Brzmienie: kwas syczy na kamieniu, lepki rozprysk, lekki magiczny impuls na poczatku. Bez krzyku, bez dlugiego ogona.
```

### 31. Electric Arc
- Zrodlo grafiki: `images/spells/electric_arc.svg`
- Proponowany plik: `audio/sfx/spell_electric_arc.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX dla czaru "Electric Arc" w Player UI, Bandit Cave. Czas: 0.7-1.2 sekundy. Brzmienie: krotki luk elektryczny odbijajacy sie od wilgotnego kamienia, ostre trzaski, ale bez bardzo wysokiej glosnosci. Ma byc dynamiczne i czytelne.
```

### 32. Heal
- Zrodlo grafiki: `images/spells/heal.svg`
- Proponowany plik: `audio/sfx/spell_heal.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX dla czaru "Heal" w Player UI, Bandit Cave. Czas: 0.9-1.5 sekundy. Brzmienie: cieple swiatlo, delikatny choralny oddech bez slow, subtelny blysk. Ma odrozniac sie od ciemnego ambience jaskini, ale nie byc cukierkowe.
```

### 33. Magic Missile
- Zrodlo grafiki: `images/spells/magic_missile.svg`
- Proponowany plik: `audio/sfx/spell_magic_missile.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX dla czaru "Magic Missile" w Player UI, Bandit Cave. Czas: 0.8-1.3 sekundy. Brzmienie: trzy szybkie magiczne pociski, kazdy z krotkim swistem i lekkim uderzeniem energii. Bez eksplozji, bez sci-fi laserow.
```

### 34. Cantrip / Focus / Rank 1 fallback
- Zrodlo grafiki: `images/spells/cantrip.svg`, `images/spells/focus.svg`, `images/spells/rank_1.svg`
- Proponowany plik: `audio/sfx/spell_generic_ready.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj neutralny SFX dla ogolnej ikony czaru w Player UI, Bandit Cave. Czas: 0.45-0.8 sekundy. Brzmienie: delikatne magiczne rozswietlenie, krotki niski ton i lekki szelest pergaminu. Ma pasowac do cantrip, focus i czaru rangi 1, bez sugerowania konkretnego zywiolu.
```

## Mapy, obiekty i interakcje jako ambience/SFX

### 35. Treasure Room ambience
- Zrodlo: `scenarios/bandit_cave_treasure_room.json`
- Proponowany plik: `audio/music/treasure_room_ambience.mp3`
- Prompt do ElevenLabs:

```text
Stworz seamless loop ambience dla mapy Treasure Room w Player UI, Bandit Cave. Dlugosc 35-50 sekund. Brzmienie: mniejsza kamienna komora, skrzynie, stary papier, delikatne pobrzmiewanie monet, prawie nieslyszalny mechanizm pulapki. Bez muzyki, bez glosow, tlo pod narracje.
```

### 36. Smuggler Docks ambience
- Zrodlo: `scenarios/bandit_cave_smuggler_docks.json`
- Proponowany plik: `audio/music/smuggler_docks_ambience.mp3`
- Prompt do ElevenLabs:

```text
Stworz seamless loop ambience dla mapy Smuggler Docks w Player UI, Bandit Cave. Dlugosc 45-60 sekund. Brzmienie: podziemna przystan, woda o pale, skrzypiace deski, liny, odlegly przeciag w duzej grocie. Niski poziom glosnosci, bez melodii i bez rozpoznawalnych slow.
```

### 37. Pulapka: plyta naciskowa
- Zrodlo: `scenarios/bandit_cave_treasure_room.json` -> `Skarbcowa płyta naciskowa`
- Proponowany plik: `audio/sfx/trap_pressure_plate.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX pulapki do Player UI, Bandit Cave: skarbcowa plyta naciskowa. Czas: 1.0-1.6 sekundy. Brzmienie: kamienna plyta opada o kilka milimetrow, ukryta igla wyskakuje, metaliczny alarmowy trzask. Bez krzyku postaci, bez gore.
```

### 38. Pulapka: iglowa skrytka
- Zrodlo: `scenarios/bandit_cave_treasure_room.json` -> `Igłowa pułapka skrytki`
- Proponowany plik: `audio/sfx/trap_needle_cache.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX dla ukrytej iglowej pulapki w skrytce, Player UI, Bandit Cave. Czas: 0.8-1.3 sekundy. Brzmienie: szybki sprzeg mechanizmu, syk malej igly, krotki metaliczny trzask alarmu w kamiennej komorze. Bez glosu i bez krwi.
```

### 39. Ukryta skrytka odkryta
- Zrodlo: `scenarios/bandit_cave_treasure_room.json` -> `description_on_reveal`
- Proponowany plik: `audio/sfx/hidden_cache_reveal.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX odkrycia ukrytej skrytki w Player UI, Bandit Cave. Czas: 0.8-1.4 sekundy. Brzmienie: falszywa deska odsuwa sie, cichy szelest papierow i monet, delikatny ton odkrycia. Bez fanfary, bardziej skradankowo niz zwyciesko.
```

### 40. Statek przemytnikow
- Zrodlo: `scenarios/bandit_cave_smuggler_docks.json` -> exit `Smuggler Ship`
- Proponowany plik: `audio/sfx/smuggler_ship_interact.mp3`
- Prompt do ElevenLabs:

```text
Wygeneruj SFX interakcji ze statkiem przemytnikow w Player UI, Bandit Cave. Czas: 1.0-1.8 sekundy. Brzmienie: lina odpinana od pala, drewno lodzi skrzypi, woda chlupie przy burcie. Ma sugerowac gotowosc do ucieczki z podziemnych dokow.
```

### 41. Marek "Lina" Voss - NPC zwiazany przemytnik
- Zrodlo: `scenarios/bandit_cave_smuggler_docks.json`, `src/GameObjects/NPC/bound_smuggler_npc.py`
- Proponowany plik: `audio/voiceover/npc_marek_notice_001.mp3`
- Wykonanie: szybka zaczepka z dokow. Pierwsze slowo ciszej, potem konkretny haczyk.
- Tekst do TTS:

```text
Hej... wy tam.

Jeśli mnie rozwiążecie, powiem wam, gdzie chowali lepszy towar. Nie te skrzynie na pokaz. Prawdziwy zapas, ten z księgami i zabezpieczeniem.

Tylko szybko, zanim ktoś z góry usłyszy, że jeszcze gadam.
```

### 42. Marek "Lina" Voss - pakiet dialogow NPC
- Zrodlo: `src/GameObjects/NPC/bound_smuggler_npc.py`
- Typ: voiceover NPC
- Wspolne wykonanie: wszystkie kwestie nagrywaj tym samym zapisanym glosem Marka. TTS powinien byc czysty; ambience dokow dodawaj osobno tylko tam, gdzie jest potrzebne.

#### 42.1 Marek - pierwsze spotkanie
- Proponowany plik: `audio/voiceover/npc_marek_bound_intro_001.mp3`
- Wykonanie: prosi o pomoc, ale probuje od razu negocjowac.
- Tekst do TTS:

```text
Rozwiążcie mnie, a powiem wam, gdzie trzymają prawdziwy łup.

Nie ten, który leży na wierzchu dla strażników. Mówię o skrytce w górnym skarbcu, przy księgach. Bez mojej wskazówki możecie znaleźć ją dopiero wtedy, kiedy pułapka już zadziała.
```

#### 42.2 Marek - kim jestes?
- Proponowany plik: `audio/voiceover/npc_marek_identity_001.mp3`
- Wykonanie: zaczyna ostroznie, potem na moment pojawia sie zawodowa duma.
- Tekst do TTS:

```text
Marek Voss. Pilot.

Oni mówią na mnie Lina, bo znam każdy węzeł, każdą mieliznę i każdy prąd, który prowadzi z tych doków na otwartą wodę.

Nie jestem strażnikiem. Nie jestem też przypadkowym więźniem. Po prostu wybrałem zły moment, żeby pokłócić się z kapitanem.
```

#### 42.3 Marek - odmawia zdradzenia skrytki przed uwolnieniem
- Proponowany plik: `audio/voiceover/npc_marek_cache_bargain_001.mp3`
- Wykonanie: krotko, targuje sie i testuje reakcje druzyny.
- Tekst do TTS:

```text
Najpierw liny. Potem sekret.

Nie obraźcie się, ale w tych dokach informacja jest jedyną rzeczą, która jeszcze trzyma mnie przy życiu.
```

#### 42.4 Marek - wskazuje skrytke
- Proponowany plik: `audio/voiceover/npc_marek_reveals_cache_001.mp3`
- Wykonanie: szybciej, praktycznie, jak instrukcja przekazana pod presja.
- Tekst do TTS:

```text
Skrytka jest w górnym skarbcu, przy kontrabandowych księgach.

Nie ciągnijcie za uchwyt od frontu. Otwórzcie panel od strony zawiasu, powoli, dwa palce pod dolną listwę. Mechanizm igłowy zostanie napięty, ale nie puści.

W środku znajdziecie lepszy towar i dokumenty, których kapitan nie chciał trzymać przy łodzi.
```

#### 42.5 Marek - nie wierzy w obietnice
- Proponowany plik: `audio/voiceover/npc_marek_diplomacy_fail_001.mp3`
- Wykonanie: podejrzliwie, bez podnoszenia glosu.
- Tekst do TTS:

```text
Nie kupuję obietnic.

W tych dokach każdy obiecuje uczciwe traktowanie, dopóki ma nóż przy gardle albo potrzebuje cudzej ręki przy linach.

Chcecie informacji? Najpierw pokażcie, że nie jestem dla was tylko kolejną skrzynią do otwarcia.
```

#### 42.6 Marek - odporny na zastraszenie
- Proponowany plik: `audio/voiceover/npc_marek_intimidation_fail_001.mp3`
- Wykonanie: spiete, nerwowa odwaga, szybka pauza przed ostatnim zdaniem.
- Tekst do TTS:

```text
Groźby zostaw kapitanowi.

Słyszałem gorsze, kiedy cumy pękały w sztormie, a połowa załogi modliła się do desek pod stopami.

Ja patrzę, gdzie stoi łódź. I wiem, że dopóki ona tam jest, wszyscy czegoś ode mnie chcecie.
```

#### 42.7 Marek - rozpoznaje blef
- Proponowany plik: `audio/voiceover/npc_marek_deception_fail_001.mp3`
- Wykonanie: ciszej i ostrzej, jak ktos sklada fakty.
- Tekst do TTS:

```text
Nie jesteś od naszych.

Znam hasła, znam twarze i wiem, kto miał dziś zejść po odbiór ładunku. Ty nie pasujesz do żadnej z tych rzeczy.

Teraz chyba obaj gramy na czas. Pytanie tylko, kto pierwszy zrobi ruch.
```

#### 42.8 Marek - zlapany na klamstwie
- Proponowany plik: `audio/voiceover/npc_marek_motive_read_001.mp3`
- Wykonanie: niechetnie przyznaje prawde, natychmiast szuka nowego ukladu.
- Tekst do TTS:

```text
Dobra. Nie jestem ofiarą.

Jestem pilotem. Prowadziłem ich łódź przez mielizny i znałem skrytki, zanim połowa tej bandy nauczyła się wiązać własne buty.

Ale nadal mogę wam oszczędzić kłopotów. Jeśli chcecie łupu, dokumentów i wyjścia z doków, lepiej mieć mnie po swojej stronie niż przywiązane milczenie przy pomoście.
```

#### 42.9 Marek - uwolniony i wspolpracuje
- Proponowany plik: `audio/voiceover/npc_marek_untied_cooperative_001.mp3`
- Wykonanie: ostroznie, kontroluje kazde slowo.
- Tekst do TTS:

```text
Spokojnie. Ręce widoczne.

Do cum nie podchodzę, do łodzi nie biegnę, żadnych nagłych ruchów. Chcecie skrytkę, pokażę skrytkę.

Tylko nie każcie mi stać między wami a kapitanem, jeśli jeszcze oddycha.
```

#### 42.10 Marek - probuje rzucic sie do lodzi
- Proponowany plik: `audio/voiceover/npc_marek_escape_attempt_001.mp3`
- Wykonanie: bardzo krotko, nagly ruch. SFX osobno po slowach.
- Tekst do TTS:

```text
Za późno.
```

- SFX do zmiksowania po kwestii:

```text
Szarpniecie luzowanej liny, szybki krok po mokrym drewnie, chlupot wody przy burcie, bez krzyku.
```

#### 42.11 Marek - zatrzymany grozba
- Proponowany plik: `audio/voiceover/npc_marek_escape_stopped_intimidation_001.mp3`
- Wykonanie: szybko, przestraszony, ale stara sie nie stracic twarzy.
- Tekst do TTS:

```text
Dobra. Dobra.

Odsuwam się od łodzi. Widzicie? Ręce z dala od cum. Nie trzeba robić z tego przedstawienia.
```

#### 42.12 Marek - zatrzymany zmylka
- Proponowany plik: `audio/voiceover/npc_marek_escape_stopped_deception_001.mp3`
- Wykonanie: urwane tempo, zaskoczenie i zawahanie.
- Tekst do TTS:

```text
Co?

Nie, czekaj... Kto jest przy drugim pomoście?

Cholera. Dobrze, dobrze, już stoję.
```

#### 42.13 Marek - luzem przy lodzi
- Proponowany plik: `audio/voiceover/npc_marek_loose_at_boat_001.mp3`
- Wykonanie: zdyszany, odzyskuje przewage, ale jeszcze nie triumfuje.
- Tekst do TTS:

```text
Nie odpływam. Jeszcze.

Ale teraz rozmawiamy inaczej. Ja stoję przy łodzi, wy stoicie na pomoście, a każdy z nas wie, że jedno szarpnięcie liny może zmienić całą rozmowę.

Więc spokojnie. Możemy nadal dogadać się jak rozsądni ludzie.
```

#### 42.14 Marek - skrytka juz wskazana
- Proponowany plik: `audio/voiceover/npc_marek_cache_already_revealed_001.mp3`
- Wykonanie: krotkie przypomnienie po ponownym pytaniu o skrytke.
- Tekst do TTS:

```text
Już wam powiedziałem.

Górny skarbiec, przy kontrabandowych księgach. Panel od strony zawiasu, powoli, bez szarpania za front.

Jeśli zrobicie to inaczej, nie miejcie do mnie pretensji, kiedy mechanizm się odezwie.
```

#### 42.15 Marek - po uwolnieniu, ponowny opis rozmowy
- Proponowany plik: `audio/voiceover/npc_marek_after_untied_notice_001.mp3`
- Wykonanie: krotki stan NPC po odwiązaniu; bardziej narrator/komunikat sytuacyjny niz nowa kwestia.
- Tekst do TTS:

```text
Marek rozciera nadgarstki i próbuje brzmieć spokojnie.

Wzrok ciągle ucieka mu w stronę łodzi, jakby liczył odległość do cum i sprawdzał, kto naprawdę pilnuje pomostu.
```

#### 42.16 Marek - proba ponownego odwiązania
- Proponowany plik: `audio/voiceover/npc_marek_already_untied_001.mp3`
- Wykonanie: bardzo krotki komunikat stanu, bez dramatyzowania.
- Tekst do TTS:

```text
Marek jest już odwiązany.
```

#### 42.17 Marek - nieudane rozczytanie intencji
- Proponowany plik: `audio/voiceover/npc_marek_motive_read_fail_001.mp3`
- Wykonanie: narrator sytuacyjny; nie sugeruj jednoznacznie, czy Marek klamie.
- Tekst do TTS:

```text
Nie łapiesz pełnego obrazu.

Marek mówi szybko, zerka na łódź i co chwilę zmienia ciężar ciała. Może blefuje, może po prostu boi się doków bardziej niż was.
```

#### 42.18 Marek - koniec rozmowy
- Proponowany plik: `audio/voiceover/npc_marek_conversation_end_001.mp3`
- Wykonanie: opcjonalny, krotki komunikat UI po wybraniu zakonczenia rozmowy.
- Tekst do TTS:

```text
Kończysz rozmowę z Markiem.
```

## Elementy tekstowe z topbaru i paneli - opcjonalne accessibility audio

Te nagrania sa przydatne, jesli Player UI ma miec tryb bardziej dostepny lub prowadzic graczy bez patrzenia w ekran.

### 43. Status: audio wlaczone/wylaczone
- Zrodlo UI: `Audio on`, `Audio off`, `Muted`
- Proponowany plik: `audio/voiceover/ui_audio_toggle_001.mp3`
- Wykonanie: neutralnie, maksymalnie krotko.
- Tekst do TTS:

```text
Audio włączone.

Audio wyłączone.
```

### 44. Panel: cele
- Zrodlo UI: `Cele`, `Cele pojawią się po starcie scenariusza`
- Proponowany plik: `audio/voiceover/ui_objectives_empty_001.mp3`
- Wykonanie: neutralny komunikat pomocniczy.
- Tekst do TTS:

```text
Cele pojawią się po starcie scenariusza.
```

### 45. Panel: inicjatywa pusta
- Zrodlo UI: `Brak aktywnej inicjatywy`
- Proponowany plik: `audio/voiceover/ui_initiative_empty_001.mp3`
- Wykonanie: neutralnie, bez efektow.
- Tekst do TTS:

```text
Brak aktywnej inicjatywy.
```

### 46. Panel: przejscia map
- Zrodlo UI: `Przejścia map`, `Brak jawnych przejść dla tej mapy`
- Proponowany plik: `audio/voiceover/ui_transitions_empty_001.mp3`
- Wykonanie: neutralnie, czytelnie.
- Tekst do TTS:

```text
Brak jawnych przejść dla tej mapy.
```

## Nazewnictwo i wdrozenie

Proponowana struktura po wygenerowaniu audio:

```text
assets/ui_v2/bandit_cave/audio/
  music/
    cave_tension_loop.mp3
    cave_entrance_ambience.mp3
    treasure_room_ambience.mp3
    smuggler_docks_ambience.mp3
  sfx/
    active_actor.mp3
    choice_confirm.mp3
    action_stride.mp3
    action_strike.mp3
    action_interact.mp3
    action_seek.mp3
    action_end_turn.mp3
    action_raise_shield.mp3
    enemy_bandit_turn.mp3
    enemy_bandit_sharpshot_turn.mp3
    enemy_guard_dog_turn.mp3
    narrator_notice.mp3
    spell_acid_splash.mp3
    spell_electric_arc.mp3
    spell_heal.mp3
    spell_magic_missile.mp3
    spell_generic_ready.mp3
    trap_pressure_plate.mp3
    trap_needle_cache.mp3
    hidden_cache_reveal.mp3
    smuggler_ship_interact.mp3
  voiceover/
    intro_001.mp3
    hint_dog_barking_001.mp3
    cave_intro_001.mp3
    secret_passage_found_001.mp3
    cave_cleared_001.mp3
    treasure_intro_001.mp3
    docks_intro_001.mp3
    docks_cleared_001.mp3
    escape_ship_ending_001.mp3
    ui_start_hall_001.mp3
    ui_party_assembly_001.mp3
    ui_mission_briefing_001.mp3
    ui_waiting_for_events_001.mp3
    ui_runtime_error_001.mp3
    ui_scenario_finished_001.mp3
    npc_marek_notice_001.mp3
    npc_marek_bound_intro_001.mp3
    npc_marek_identity_001.mp3
    npc_marek_cache_bargain_001.mp3
    npc_marek_reveals_cache_001.mp3
    npc_marek_diplomacy_fail_001.mp3
    npc_marek_intimidation_fail_001.mp3
    npc_marek_deception_fail_001.mp3
    npc_marek_motive_read_001.mp3
    npc_marek_untied_cooperative_001.mp3
    npc_marek_escape_attempt_001.mp3
    npc_marek_escape_stopped_intimidation_001.mp3
    npc_marek_escape_stopped_deception_001.mp3
    npc_marek_loose_at_boat_001.mp3
    npc_marek_cache_already_revealed_001.mp3
    npc_marek_after_untied_notice_001.mp3
    npc_marek_already_untied_001.mp3
    npc_marek_motive_read_fail_001.mp3
    npc_marek_conversation_end_001.mp3
```

Po dodaniu plikow audio warto rozszerzyc `assets/ui_v2/bandit_cave/manifest.json` o brakujace wpisy `sfx`, `music` i `narration`, a potem podpiac je w `player_ui/static/app.js` tylko tam, gdzie nie beda odtwarzane zbyt czesto.

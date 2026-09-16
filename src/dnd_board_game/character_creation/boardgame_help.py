"""Shared player-facing rules for the seven curated heroes.

Rule decisions stay in combat/rules; these notes feed UI and printed dossiers.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuleNote:
    name: str
    body: str


FLAW_HELP: dict[str, RuleNote] = {
    'flaw_remorse': RuleNote('Wyrzuty sumienia', 'gdy Garran otrzymał najmniej obrażeń w drużynie, a ktoś otrzymał więcej, ma -2 do ataków, obron i testów. Leczenie nie cofa licznika.'),
    'flaw_chains': RuleNote('Bitewny amok', 'podczas Szału Brakka nie może używać mikstur, zwojów ani aktywnych właściwości przedmiotów. Może nadal atakować trzymaną bronią.'),
    'flaw_exposed_panic': RuleNote('Panika po zdemaskowaniu', 'podczas tej sesji skradania widzący Mirę wróg ma +2 do testów ataku przeciw niej. Gdy widzą ją wszyscy, skradanie się kończy i premia znika.'),
    'flaw_leave_no_one': RuleNote('Nikogo nie zostawiam', 'Żywy sojusznik z 0 PW w 30 stopach: utrudnienie ataków i testów poza ratunkiem; cele wrogich czarów Dagny mają przewagę w obronach.'),
    'flaw_needs_audience': RuleNote('Potrzeba publiczności', 'Zdolności specjalne wymagają żywego, przytomnego i nieobezwładnionego sojusznika w 10 stopach. Zwykłe ataki i czary pozostają dostępne.'),
    'flaw_arcane_echo': RuleNote('Echo magicznego wycieku', 'W danej rundzie nie możesz powtórzyć czaru ani opcji Metamagii użytych w poprzedniej rundzie. Anulowanie podglądu nie wywołuje Echa.'),
    'flaw_friendly_fire_trauma': RuleNote('Trauma bratobójczego strzału', '-1 do ataku długim łukiem za przytomnego bohatera drużyny w 5 stopach od celu. Pomija Erynda, pokonanych, przywołania i NPC; nie działa na nóż.'),
}

HERO_FLAW_IDS: dict[str, str] = {'garran': 'flaw_remorse', 'brakka': 'flaw_chains', 'mira': 'flaw_exposed_panic', 'dagna': 'flaw_leave_no_one', 'lorian': 'flaw_needs_audience', 'nimra': 'flaw_arcane_echo', 'erynd': 'flaw_friendly_fire_trauma'}

HERO_FLAWS = {actor_id: FLAW_HELP[feature_id] for actor_id, feature_id in HERO_FLAW_IDS.items()}

PASSIVE_HELP: dict[str, RuleNote] = {
    'fighting_style_defense': RuleNote('Styl walki: Obrona', '+1 KP podczas noszenia pancerza.'),
    'improved_critical': RuleNote('Ulepszony krytyk', 'ataki bronią trafiają krytycznie przy naturalnym 19 albo 20.'),
    'iron_line': RuleNote('Żelazna linia', 'sojusznik flankujący z Garranem tego samego przeciwnika ma +1 KP przeciw jego atakom.'),
    'darkvision': RuleNote('Widzenie w ciemności', 'W niemagicznej ciemności do 60 stóp widzi jak w półmroku. Nie przenika magicznej ciemności ani mgły.'),
    'unarmored_defense_constitution': RuleNote('Obrona bez pancerza', 'KP 10 + Zręczność + Kondycja; tarcza jest dozwolona.'),
    'relentless_endurance': RuleNote('Nieustępliwość półorka', 'automatycznie przy pierwszym zejściu do 0 PW pozostawia Brakkę z 1 PW, o ile obrażenia nie zabijają jej natychmiast; 1 użycie na długi odpoczynek.'),
    'savage_attacks': RuleNote('Dzikie ataki', 'krytyczny atak bronią wręcz dodaje jedną kość broni.'),
    'mira_shadow_stealth': RuleNote('Mistrzyni ukrycia', 'Ukryj się: akcja, bez osłony; blokuje je wróg w 5 stopach lub stan. Jeden test Zręczności przeciw osobnym testom wykrycia wrogów; remis wykrywa Mirę.'),
    'mira_stealth_movement': RuleNote('Skradanie', 'limit ruchu 20 stóp. Dobrowolne wyjście przywraca limit 25 stóp, ale nie zwraca wykonanego ruchu ani akcji.'),
    'mira_shadow_killer': RuleNote('Atak z cienia', 'Raz na turę rapier lub nóż daje +2k6 i przewagę przeciw celowi, który nie widzi Miry; własna flanka daje +1k6, oba warunki +3k6. Atak kończy ukrycie.'),
    'mira_flanking': RuleNote('Flanka zabójczyni', 'osobista flanka daje +1k6; razem z ukryciem daje +3k6.'),
    'lucky': RuleNote('Szczęście niziołka', 'ponów naturalną 1 w ataku, teście albo obronie.'),
    'mira_ranged_evasion': RuleNote('Ruchomy cel', 'Mira ma +2 KP przeciw dystansowym testom ataku bronią i czarem; nie działa przeciw obszarom ani rzutom obronnym.'),
    'dwarven_speed': RuleNote('Krasnoludzki ruch', 'Ciężki pancerz nie zmniejsza szybkości Dagny z powodu niewystarczającej Siły.'),
    'disciple_of_life': RuleNote('Uczeń Życia', 'Czar leczenia poziomu 1 lub wyższego przywraca dodatkowo 2 + poziom użytej komórki PW.'),
    'field_medic_step': RuleNote('Krok ratowniczki', 'Raz na turę Dagny, po leczeniu lub zdjęciu negatywnego stanu innego sojusznika w 10 stopach: ruch 5 stóp bez kosztu ruchu, reakcji i ataków okazyjnych.'),
    'dwarven_toughness': RuleNote('Krasnoludzka wytrzymałość', '+1 maksymalnego PW na każdy poziom.'),
    'dwarven_resilience': RuleNote('Krasnoludzka odporność', 'przewaga przeciw truciźnie i odporność na obrażenia od trucizny.'),
    'fey_ancestry': RuleNote('Fey Ancestry', 'przewaga przeciw zauroczeniu i odporność na magiczny sen.'),
    'crossbowman': RuleNote('Kusznik', 'zwykła akcja Ataku kuszą ręczną daje dwa osobne strzały; każdy może mieć inny legalny cel. Ostrzały specjalne określają własną liczbę celów.'),
    'social_grace_bargaining': RuleNote('Obycie i targowanie', '+2 do każdego pozabojowego testu Charyzmy. Nie tworzy nowych nagród ani możliwości fabularnych.'),
    'improvisation': RuleNote('Improwizacja', 'raz na NPC przerzuć nieudany pozabojowy test Charyzmy przed konsekwencjami; drugi wynik jest ostateczny. Zużycie jest zapisywane.'),
    'gnome_cunning': RuleNote('Gnomia przebiegłość', 'przewaga w obronach INT, MĄD i CHA przeciw magii.'),
    'nimra_catalogue': RuleNote('Katalog niemożliwego', 'wszystkie czary z talii są stale dostępne; Nimra nie przygotowuje ich po odpoczynku.'),
    'arcane_recovery': RuleNote('Odzyskiwanie magiczne', 'Raz na długi odpoczynek, podczas krótkiego odzyskaj komórki o sumie poziomów do połowy poziomu czarodziejki, w górę (obecnie 2).'),
    'fighting_style_archery': RuleNote('Styl walki: Łucznictwo', '+2 do dystansowych ataków bronią; premia jest już wliczona w atak na arkuszu.'),
    'erynd_expertise': RuleNote('Ekspertyza zwiadowcy', 'podwójna biegłość w Skradaniu i Sztuce przetrwania.'),
    'first_blood': RuleNote('Pierwsza krew', 'Raz na turę trafienie długim łukiem w cel z pełnymi PW zadaje dodatkowe 1k8. Inne bronie nie otrzymują tej premii.'),
    'scouts_vigilance': RuleNote('Czujność zwiadowcy', '+2 do inicjatywy i testów wykrywania ukrytych przeciwników; premia nie dotyczy pułapek.'),
    'expertise': RuleNote('Ekspertyza', 'Podwójna premia z biegłości w wybranych umiejętnościach; jest już wliczona w ich modyfikatory.'),
}

HERO_PASSIVE_IDS: dict[str, tuple[str, ...]] = {
    'garran': ('fighting_style_defense', 'improved_critical', 'iron_line'),
    'brakka': ('darkvision', 'unarmored_defense_constitution', 'relentless_endurance', 'savage_attacks'),
    'mira': ('mira_shadow_stealth', 'mira_stealth_movement', 'mira_shadow_killer', 'lucky', 'mira_ranged_evasion', 'expertise'),
    'dagna': ('darkvision', 'dwarven_speed', 'disciple_of_life', 'field_medic_step', 'dwarven_toughness', 'dwarven_resilience'),
    'lorian': ('darkvision', 'fey_ancestry', 'crossbowman', 'social_grace_bargaining', 'improvisation'),
    'nimra': ('darkvision', 'gnome_cunning', 'nimra_catalogue', 'arcane_recovery'),
    'erynd': ('darkvision', 'fighting_style_archery', 'erynd_expertise', 'first_blood', 'scouts_vigilance', 'fey_ancestry'),
}

HERO_PASSIVES = {
    actor_id: tuple(PASSIVE_HELP[feature_id] for feature_id in feature_ids)
    for actor_id, feature_ids in HERO_PASSIVE_IDS.items()
}


ACTIVE_FEATURE_HELP: dict[str, RuleNote] = {
    'second_wind': RuleNote('Drugi oddech', 'AKCJA DOD. · WŁASNY. Rzuć k10. Odzyskaj wynik + poziom Garrana PW. 1 użycie; odnawia krótki lub długi odpoczynek.'),
    'action_surge': RuleNote('Zryw akcji', 'AKCJA DOD. · PO AKCJI. Po zużyciu akcji głównej wydaj akcję dodatkową, aby natychmiast ją odzyskać. 1 użycie na krótki odpoczynek.'),
    'shield_bash': RuleNote('Uderzenie tarczą', 'AKCJA DODATKOWA · 5 STÓP. Wykonaj sporny test Siły; aplikacja rzuca za przeciwnika. Wygrana zadaje 1k6 + modyfikator Siły obrażeń obuchowych i odpycha cel o jedno wolne pole od Garrana; remis wygrywa obrońca.'),
    'defensive_stance': RuleNote('Pozycja obronna', 'AKCJA RUCHU · WŁASNY. Zamiast ruchu zyskaj +2 KP do początku następnej tury. Efekt kończy się wcześniej po każdej zmianie pola.'),
    'garran_command_halt': RuleNote('Rozkaz: Stać', 'AKCJA · 60 STÓP · 1 TAKTYKA. Mądrość ST 14. Sukces: połowa ruchu w następnej turze. Porażka: brak dobrowolnego ruchu. Naturalne 1 daje też -2 do ataków; naturalne 20 neguje efekt.'),
    'garran_shield_wall': RuleNote('Osłona tarczą', 'AKCJA DOD. · 1 TAKTYKA. Do początku następnej tury Garrana wszyscy sąsiadujący sojusznicy otrzymują +2 KP. Premia porusza się z Garranem; Garran jej nie otrzymuje.'),
    'garran_rally': RuleNote('Mowa dowódcy', 'AKCJA · 30 STÓP · 1 TAKTYKA. Garran i słyszący sojusznicy usuwają Strach i zyskują przewagę na pierwszy atak, test albo rzut obronny do końca swojej następnej tury.'),
    'garran_guard_companion': RuleNote('Osłona towarzysza', 'AKCJA · 5 STÓP · 1 TAKTYKA. Wybierz sąsiadującego sojusznika. Pierwszy pojedynczy wrogi atak, czar lub efekt przeciw niemu zostaje w całości przekierowany na Garrana i zużywa osłonę.'),
    'rage': RuleNote('Szał', 'AKCJA DOD. · 3/DŁUGI ODPOCZYNEK. Włącz Szał: odnów Dzikość do modyfikatora Kondycji (3), zyskaj przewagę w testach i obronach Siły, +2 do obrażeń ataków wręcz opartych na Sile oraz odporność na kłute, cięte i obuchowe. Niewydana Dzikość znika wraz ze Szałem.'),
    'reckless_attack': RuleNote('Lekkomyślny atak', 'AKCJA · ATAK WRĘCZ. Natychmiast wykonaj jeden atak bronią wręcz oparty na Sile z przewagą. Do początku następnej tury Brakki ataki przeciw niej mają przewagę. Nie wymaga Szału ani Dzikości.'),
    'powerful_strike': RuleNote('Potężne uderzenie', 'AKCJA · SZAŁ · 2 DZIKOŚCI. Wykonaj jeden atak bronią wręcz oparty na Sile z premią +10 do testu ataku. Obrażenia pozostają normalne.'),
    'shoulder_check': RuleNote('Z bara', 'AKCJA · 5 STÓP. Wybierz sąsiadującego przeciwnika najwyżej o jeden rozmiar większego. Sporny test Atletyki; remis wygrywa obrońca. Odepchnij o 5 stóp i dalsze 5 za każde pełne 5 punktów przewagi, maksymalnie 30 stóp.'),
    'hard_as_rock': RuleNote('Twarda jak skała', 'REAKCJA · SZAŁ · 1 DZIKOŚĆ. Po obliczeniu obrażeń i odporności zmniejsz pozostałe obrażenia o 1k12 + modyfikator Kondycji. Przy braku Szału albo Dzikości system nie proponuje reakcji.'),
    'acceleration': RuleNote('Przyspieszenie', 'AKCJA DOD. · SZAŁ · 1 DZIKOŚĆ. Do końca bieżącej tury podwój bazowy limit ruchu. Wykonany już ruch pozostaje wydany, trudny teren działa normalnie, a Sprint nie jest ponownie podwajany.'),
    'deafening_roar': RuleNote('Ogłuszający ryk', 'AKCJA · STOŻEK 15 STÓP · 2 DZIKOŚCI. Wrogowie wykonują obronę Kondycji przeciw ST 15. Porażka: 2k6 i brak dobrowolnego ruchu do końca najbliższej tury celu; sukces: połowa obrażeń. Naturalne 1 daje też utrudnienie ataków, naturalne 20 neguje obrażenia.'),
    'instinctive_dodge': RuleNote('Unik instynktowny', 'REAKCJA · 1 FORTEL. Gdy widzący Mirę wróg wybiera ją jako cel ataku podczas jej skradania, przed rzutem nadaj temu jednemu atakowi utrudnienie. Reakcja nie znosi premii +2 ze skazy.'),
    'smoke_screen': RuleNote('Zasłona dymna', 'AKCJA · RUCH 15 STÓP · 1 FORTEL. Przemieść Mirę bez ataków okazyjnych, po czym wykonaj nowy test Ukrycia nawet obok wroga. Wrogowie testują Percepcję z karą równą połowie modyfikatora Zręczności Miry, w dół.'),
    'guard_vault': RuleNote('Przeskok przez gardę', 'AKCJA · ATAK WRĘCZ. Jeśli dokładnie za sąsiadującym celem jest wolne legalne pole, zaatakuj z +2 do testu i obrażeń, po czym przenieś Mirę na to pole. Skok nie prowokuje; późniejszy atak okazyjny tego celu ma przeciw Mirze -2 do trafienia.'),
    'combat_trap_detection': RuleNote('Wykrycie pułapek', 'AKCJA · PROMIEŃ 45 STÓP. W walce przeskanuj obszar wokół Miry i wykonaj fizyczny test Spostrzegawczości. Wykryte pułapki zostają ujawnione oraz zaznaczone na planszy. Bez kosztu Fortelu.'),
    'hamstring_cut': RuleNote('Cięcie ścięgna', 'AKCJA · FLANKA · 1 FORTEL. Atak wręcz. Jeśli trafi i zada co najmniej 1 obrażenie, cel porusza się z połową szybkości do chwili otrzymania leczenia albo oczyszczenia statusu.'),
    'piercing_attack': RuleNote('Przeszywający atak', 'AKCJA · FLANKA · 1 FORTEL. Sojusznik angażujący pierwszy cel z sąsiedniego pola tworzy otwarcie. Po raniącym trafieniu zaatakuj osobno wroga dokładnie za pierwszym; drugi atak zachowuje premie i nie tworzy łańcucha.'),
    'blade_mistress': RuleNote('Mistrzyni ostrzy', 'ULEPSZENIE ATAKU · 1 FORTEL. Po raniącym trafieniu nożem z ukrycia w cel, który nie widzi Miry, nałóż Krwawienie: 1k4 na początku jego tur do otrzymania leczenia albo oczyszczenia. Nie kumuluje się.'),
    'preserve_life': RuleNote('Zachowanie życia', 'AKCJA · CELE NA PLANSZY. Rozdziel 5 × poziom Dagny PW pomiędzy wskazane cele, ale nie lecz żadnego powyżej połowy maksymalnych PW. 1 Boska Moc.'),
    'bardic_inspiration': RuleNote('Inspiracja bardowska', 'AKCJA DOD. · 60 STÓP. Sojusznik otrzymuje k6 do jednego wybranego testu, ataku lub obrony. Puste pole zachowuje efekt; wpisanie 1–6 zużywa kość. Użycia: modyfikator Charyzmy na krótki odpoczynek.'),
    'optical_scope': RuleNote('Luneta optyczna', 'AKCJA · KUSZA · 60 STÓP · CAŁY RUCH. Tylko przed ruchem. Wykonaj dwa strzały w jeden cel; oba traktują jego KP jako niższe o 2. Użycie zużywa cały ruch Loriana, także gdy strzały chybią.'),
    'mocking_shot': RuleNote('Ostrzał destabilizujący', 'AKCJA · KUSZA · 45 STÓP. Zamiast dwóch strzałów wykonaj jeden. Trafienie: utrudnienie pierwszego ataku celu oraz obron na Mądrość do początku następnej tury Loriana.'),
    'provoking_shot': RuleNote('Prowokujący ostrzał', 'AKCJA · KUSZA · 45 STÓP. Zamiast dwóch strzałów wykonaj jeden. Trafienie: do początku następnej tury Loriana premia celu do ataków przeciw niemu i kara przeciw pozostałym są równe zadanym obrażeniom.'),
    'entangling_shot': RuleNote('Oplatający ostrzał', 'AKCJA · OBSZAR 3×3 · 45 STÓP. Wszyscy w obszarze, także sojusznicy, wykonują obronę na Zręczność. Sukces: połowa ruchu; porażka: brak ruchu do początku następnej tury Loriana. Bez obrażeń.'),
    'counterpoint': RuleNote('Kontrapunkt', 'REAKCJA · 45 STÓP. Gdy zainspirowany sojusznik bezpośrednio zrani wroga, Lorian może zaatakować tego samego, nadal żywego i legalnego celu kuszą. Raz między turami Loriana; nie zużywa Inspiracji.'),
    'distracting_shout': RuleNote('Rozpraszający okrzyk', 'REAKCJA · PO RZUCIE OBRAŻEŃ. Gdy atak trafia zainspirowanego sojusznika, przed odjęciem PW zmniejsz obrażenia o 1k6+2, minimum do 0. Nie zużywa Inspiracji.'),
    'cutting_words': RuleNote('Cięta riposta', 'REAKCJA PO UJAWNIENIU RZUTU. Odejmij k6 od ujawnionego testu ataku albo od ujawnionych obrażeń przeciwnika. Nie zużywa Inspiracji, ale konkuruje z pozostałymi reakcjami.'),
    'nimra_sculpt_field': RuleNote('Rzeźbienie pola', 'METAMAGIA · 1 PUNKT. Wyłącz do 4 pól z obszaru czaru. Wycięcia pozostają w efektach trwających.'),
    'nimra_distant_spell': RuleNote('Odległy czar', 'METAMAGIA · 1 PUNKT. Zwiększ planszowy zasięg czaru o 15 stóp, maksymalnie do 75 stóp.'),
    'nimra_overcharged_spell': RuleNote('Przeciążony czar', 'METAMAGIA · 1 PUNKT. Dodaj jedną kość tego samego typu do podstawowych obrażeń czaru.'),
    'nimra_forced_weave': RuleNote('Wymuszony splot', 'METAMAGIA · 2 PUNKTY. Jeden wybrany cel ma utrudnienie pierwszego rzutu obronnego przeciw czarowi.'),
    'nimra_energy_transmutation': RuleNote('Transmutacja energii', 'METAMAGIA · 1 PUNKT. Zmień kwas, zimno, ogień, błyskawice albo grzmot na jeden z tych typów. Nie zmienia mocy ani obrażeń psychicznych.'),
    'cunning_action': RuleNote('Zwiadowcza mobilność', 'AKCJA DOD. · WŁASNA TURA. Wybierz Sprint albo Odstąpienie jako akcję dodatkową. Bojowe Ukrycie jest unikalną akcją Miry.'),
    'aim': RuleNote('Celowanie', 'CAŁY RUCH · PRZED RUCHEM. Poświęć cały niewykorzystany ruch. Następny atak z długiego łuku w tej turze ma przewagę.'),
    'anchoring_arrow': RuleNote('Strzała kotwicząca', 'AKCJA · 1 INSTYNKT. Rzuć k4 i podaj wynik. Trafienie: Siła ST 14; porażka blokuje ruch, sukces zmniejsza go o połowę przez tyle rund.'),
    'exposing_arrow': RuleNote('Strzała odsłaniająca', 'AKCJA · 1 INSTYNKT. Rzuć k8 i podaj wynik. Trafienie obniża KP celu o wynik do początku następnej tury Erynda.'),
    'disrupting_arrow': RuleNote('Strzała zakłócająca', 'AKCJA · 1 INSTYNKT. Trafienie odbiera reakcje i daje utrudnienie do następnego ataku celu, najpóźniej do końca jego następnej tury.'),
    'double_shot': RuleNote('Podwójny strzał', 'AKCJA · 2 INSTYNKT. Wykonaj jeden test przeciw jednemu celowi. Trafienie: 2k8 + 2×DEX; Znak łowcy i Pierwsza krew dodają kość tylko raz. Amunicja nie jest liczona.'),
}

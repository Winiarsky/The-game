"""Presentation-only physical costs. No deck, hand or payment state belongs here."""
from dataclasses import dataclass

# Internal F now denotes black; preserve codes for saved games and ability costs.
COLORS = {"C": "czerwona", "N": "niebieska", "Z": "zielona", "B": "biała", "F": "czarna", "*": "dowolna"}

@dataclass(frozen=True, slots=True)
class ManaAbility:
    hero_id: str
    id: str
    name: str
    timing: str
    cost: tuple[str, ...]
    description: str
    category: str = "basic"
    duration: str = ""
    boosts: tuple[object, ...] = ()

    @property
    def cost_label(self) -> str:
        return " + ".join(COLORS[color] for color in self.cost)

    def as_payload(self) -> dict[str, object]:
        return {"id": self.id, "name": self.name, "timing": self.timing,
                "cost": list(self.cost), "cost_label": self.cost_label,
                "description": self.description, "category": self.category,
                "duration": self.duration,
                "boosts": [{"id": b.id, "color": b.color, "maximum": b.maximum, "label": b.label} for b in self.boosts]}

_ROWS = (('garran',
  'second_wind',
  'Drugi oddech',
  'A',
  ('B', '*'),
  'Odzyskaj 1k10+3 PW. Zmiana z akcji dodatkowej na główną: leczenie konkuruje z ofensywą.'),
 ('garran',
  'action_surge',
  'Zryw akcji',
  'D',
  ('C',),
  'Następny zwykły atak w tej turze otrzymuje +2 do trafienia. Atak nadal '
  'kosztuje *. Nie odnawia akcji, nie dodaje ataków ani premii do technik specjalnych.'),
 ('garran',
  'shield_bash',
  'Uderzenie tarczą',
  'D',
  ('C', 'N'),
  'Akcja dodatkowa: sporny test Siły. Wygrana: 1k6 + modyfikator Siły obrażeń i odepchnięcie o jedno pole.'),
 ('garran',
  'defensive_stance',
  'Pozycja obronna',
  'D',
  ('B',),
  '+2 KP do początku następnej tury; każda zmiana pola kończy efekt. Zastępuje dawny koszt całego '
  'ruchu.'),
 ('garran',
  'garran_command_halt',
  'Rozkaz: Stać',
  'A',
  ('N', '*'),
  'Obecny rozkaz, w tym naturalne 1/20.'),
 ('garran',
  'garran_shield_wall',
  'Osłona tarczą',
  'D',
  ('B', 'N'),
  'Sąsiadujący sojusznicy mają +2 KP do początku następnej tury Garrana; bez premii dla niego.'),
 ('garran',
  'garran_rally',
  'Mowa dowódcy',
  'A',
  ('B', '*'),
  'Usuń Strach u słyszących sojuszników w 30 stopach i siebie; przewaga na ich pierwszy '
  'atak/test/obronę jak obecnie.'),
 ('garran',
  'garran_guard_companion',
  'Osłona towarzysza',
  'A',
  ('B', 'N'),
  'Przekieruj pierwszy pojedynczy wrogi efekt z sąsiadującego sojusznika na Garrana jak obecnie.'),
 ('brakka',
  'rage',
  'Szał',
  'D',
  ('C',),
  'Szał trwa modyfikator KON + modyfikator SIŁ rund (minimum 1), licząc rundę uruchomienia. '
  '+2 obrażeń wręcz z SIŁ, odporność na obuchowe, kłute i cięte oraz przewaga testów i obron SIŁ. '
  'Płacisz raz; nie odnawiaj co turę. Utrata przytomności kończy Szał.'),
 ('brakka',
  'reckless_attack',
  'Lekkomyślny atak',
  'MOD',
  ('C',),
  'Następny zwykły atak wręcz oparty na SIŁ w tej turze ma przewagę. Atak jest opłacany '
  'dodatkowo przez *. Ataki przeciw Brakce mają przewagę do początku jej następnej tury. Raz we własnej turze; '
  'nie jest osobną akcją ani kolejnym atakiem.'),
 ('brakka',
  'powerful_strike',
  'Potężne uderzenie',
  'A',
  ('C', 'C'),
  'W Szale: jeden atak z +2 do trafienia i +1k12 obrażeń przy trafieniu. Zastępuje dawne +10 do '
  'trafienia.'),
 ('brakka', 'shoulder_check', 'Z bara', 'A', ('C', 'N'), 'Obecne odpychanie Atletyką.'),
 ('brakka',
  'acceleration',
  'Przyspieszenie',
  'D',
  ('Z',),
  'W Szale: uruchamia zwykły ruch bez dodatkowej opłaty i podwaja jego bazowy limit w tej turze. '
  'Wykonany wcześniej ruch liczy się do nowego limitu.'),
 ('brakka',
  'deafening_roar',
  'Ogłuszający ryk',
  'A',
  ('C', 'N', '*'),
  'W Szale: obecny stożek, 2k6, ograniczenie ruchu i naturalne wyniki.'),
 ('brakka',
  'hard_as_rock',
  'Twarda jak skała',
  'R',
  ('B',),
  'W Szale: redukcja 1k12+KON po odporności jak obecnie.'),
 ('brakka', 'grapple', 'Chwyt', 'A', ('*',), 'Obecny chwyt, wolna ręka i limit wielkości celu.'),
 ('mira',
  'hide',
  'Ukryj się',
  'A',
  ('*',),
  'Obecny test ukrycia i osobni obserwatorzy. Dobrowolne zakończenie ukrycia bez many/akcji.'),
 ('mira',
  'smoke_screen',
  'Zasłona dymna',
  'A',
  ('Z', 'F'),
  'Ruch do 15 stóp bez ataków okazyjnych i próba ukrycia nawet przy wrogu; cały ruch w cenie.'),
 ('mira',
  'guard_vault',
  'Przeskok przez gardę',
  'A',
  ('Z', '*'),
  'Obecny atak +2/+2 i przejście na wolne pole za celem; to przesunięcie w cenie.'),
 ('mira', 'combat_trap_detection', 'Wykrycie pułapek', 'A', ('*',), 'Obecny test Percepcji w walce.'),
 ('mira',
  'hamstring_cut',
  'Cięcie ścięgna',
  'A',
  ('Z', 'N'),
  'Atak z własnej flanki; trafienie połowi ruch do początku następnej tury Miry, zamiast do leczenia.'),
 ('mira',
  'piercing_attack',
  'Przeszywający atak',
  'A',
  ('Z', 'C'),
  'Atak rapierem w przeciwnika stojącego przy sojuszniku. Po raniącym trafieniu osobny atak z +2 do '
  'trafienia w drugiego wroga dokładnie jedno pole za pierwszym, na tej samej linii od Miry. Drugie '
  'trafienie dosięga tego pola mimo zwykłego zasięgu rapiera; ściana je blokuje. Bez łańcucha dalszych '
  'celów. Oba ataki w cenie.'),
 ('mira',
  'blade_mistress',
  'Mistrzyni ostrzy',
  'A',
  ('Z', 'F'),
  'Trafienie nożem z ukrycia powoduje krwawienie 1k4 przez najwyżej dwie tury celu; leczenie kończy '
  'wcześniej. Bez kumulowania.'),
 ('mira',
  'instinctive_dodge',
  'Unik instynktowny',
  'R',
  ('Z',),
  'Obecna reakcja z utrudnieniem ataku przeciw ukrytej Mirze.'),
 ('dagna',
  'sacred_flame',
  'Święty płomień',
  'A',
  ('B',),
  'Obecny stożek 15 stóp, 1k8 blasku przy porażce ZRC.'),
 ('dagna',
  'healing_word',
  'Słowo leczenia',
  'A',
  ('B', '*'),
  '1k4+7 PW w 60 stopach. Zmiana z akcji dodatkowej na główną.'),
 ('dagna',
  'bless',
  'Błogosławieństwo',
  'A',
  ('B', 'N'),
  'Obecna aura +1k4, koncentracja; maksymalnie trzy rundy zamiast pięciu.'),
 ('dagna',
  'preserve_life',
  'Zachowanie życia',
  'A',
  ('B', 'B', '*'),
  'Rozdziel 15 PW, najwyżej do połowy maksymalnych PW celu, jak obecnie.'),
 ('dagna',
  'divine_care_aura',
  'Aura Boskiej Opieki',
  'A',
  ('B', 'N'),
  'Obecna aura -2 do ataków/obrażeń wrogów; koncentracja, maksymalnie trzy rundy.'),
 ('dagna',
  'guiding_bolt',
  'Naprowadzający pocisk',
  'A',
  ('B', 'C'),
  'Obecne 2k6 i przewaga kolejnego ataku przeciw trafionemu celowi.'),
 ('dagna',
  'healing_grace_aura',
  'Aura Uzdrawiającej Łaski',
  'A',
  ('B', 'Z', '*'),
  'Przez trzy rundy, z koncentracją: dwa pierwsze leczenia w aurze dodają po 1k8 PW. Zastępuje cztery '
  'wzmocnienia +1k8+MDR.'),
 ('dagna',
  'lesser_restoration',
  'Pomniejsze przywrócenie',
  'A',
  ('B', 'Z'),
  'Usuń jedną obecnie obsługiwaną negatywną kondycję przez dotyk.'),
 ('dagna',
  'turn_undead',
  'Odpędzanie nieumarłych',
  'A',
  ('B', 'N'),
  'Obecny obszar i rzut MDR; odpędzenie najwyżej do końca następnej tury Dagny, obrażenia kończą '
  'wcześniej.'),
 ('dagna',
  'spiritual_weapon',
  'Duchowa broń',
  'A',
  ('B', 'C', '*'),
  'Przywołanie i jeden atak w cenie. Trwa trzy rundy, najwyżej jedna broń; dalsze aktywacje kosztują akcję dodatkową i jedną białą manę, '
  'każda zawiera ruch broni do 20 stóp i jeden atak. Brak osobnej darmowej tury przywołania.'),
 ('lorian',
  'mana_inspiration',
  'Inspiracja barw',
  'D',
  ('B',),
  'Jeden inny bohater w 30 stopach może przy opłaceniu jednego działania do początku następnej tury '
  'Loriana potraktować jedną posiadaną kartę jako dowolny kolor. Jedna niewykorzystana Inspiracja na '
  'odbiorcę; bez k6 i bez tworzenia karty.'),
 ('lorian',
  'mana_tuning',
  'Strojenie talii',
  'D',
  ('N',),
  'Wymień do dwóch własnych kart z taką samą liczbą wybranych kart rynku. Jeden jednoczesny zestaw '
  'wymian 1:1, bez dobierania.'),
 ('lorian',
  'mana_transmutation',
  'Transmutacja',
  'D',
  ('F',),
  'Do końca tej tury dwie wskazane posiadane karty możesz opłacić jako dowolne kolory. Każda nadal jest '
  'wydawana i nie może opłacić dwóch symboli. Nie działa na kartę zużytą do uruchomienia Transmutacji.'),
 ('lorian',
  'mana_transfer',
  'Przerzut energii',
  'D',
  ('Z',),
  'Przekaż do dwóch własnych kart jednemu innemu bohaterowi w 30 stopach. Nie dobiera on nowych. '
  'Obowiązuje pojemność odbiorcy.'),
 ('lorian',
  'mana_reservation',
  'Rezerwacja',
  'D',
  ('N',),
  'Zabierz jedną kartę rynku do swojego depozytu, wliczanego do rezerwy i pojemności. Nie można jej '
  'wydać, oddać ani wymienić przed początkiem następnej własnej tury; wolno ją odrzucić. Maksymalnie '
  'jeden depozyt, na następnej turze staje się zwykłą kartą. Rynek uzupełnia się na końcu obecnej '
  'tury.'),
 ('lorian',
  'mana_recovery',
  'Odzysk energii',
  'A',
  ('B', 'N'),
  'Wybierz do trzech kart obecnych na odrzuconych przed opłaceniem zdolności i rozdaj je sobie lub '
  'bohaterom w 30 stopach, najwyżej dwie jednemu odbiorcy. Nie wolno odzyskać właśnie wydanych kart białej i niebieskiej many; '
  'nie zwiększa pojemności. Brak odpowiednich kart oznacza mniejszy odzysk.'),
 ('lorian',
  'mana_refresh',
  'Nowe rozdanie',
  'A',
  ('N', '*'),
  'Odrzuć do trzech kart rynku, uzupełnij go z talii. Następnie każdy przytomny bohater w 30 stopach, w '
  'tym Lorian, może raz wymienić własną kartę z rynkiem, w kolejności inicjatywy. Nie ma kolejnego '
  'doboru pomiędzy wymianami.'),
 ('lorian',
  'mana_loan',
  'Awaryjna pożyczka',
  'R',
  ('B',),
  'Gdy inny bohater w 30 stopach deklaruje działanie, przed jego opłaceniem przekaż mu jedną dodatkową '
  'własną kartę. Biała mana za reakcję jest osobnym kosztem; łącznie Lorian traci dwie karty. Bez zwrotu/długu '
  'mimo nazwy. Nie otwiera dodatkowej akcji ani nie zwiększa już zadeklarowanej serii ataków.'),
 ('lorian',
  'optical_scope',
  'Luneta optyczna',
  'A',
  ('Z', 'N', '*'),
  'Przed ruchem wykonaj dwa osobne strzały w jeden cel, każdy z +2 do trafienia i ignorowaniem '
  'częściowej osłony; całkowita osłona blokuje. Zużywa cały ruch. Dwa strzały są już opłacone.'),
 ('lorian',
  'mocking_shot',
  'Ostrzał destabilizujący',
  'A',
  ('Z', 'F'),
  'Jeden strzał w 45 stopach. Trafienie: utrudnienie pierwszego ataku i obron MDR celu do początku '
  'następnej tury Loriana.'),
 ('lorian',
  'entangling_shot',
  'Oplatający ostrzał',
  'A',
  ('Z', 'N'),
  'Obszar 3×3 w 45 stopach, także sojusznicy. ZRC ST 14: porażka blokuje ruch, sukces połowi do '
  'początku następnej tury Loriana. Bez obrażeń.'),
 ('lorian',
  'panic_whisper',
  'Podszept paniki',
  'A',
  ('F', 'N'),
  'Cel w 45 stopach, MDR ST 14: 2k6 psychicznych i ruch do 15 stóp od Loriana; sukces połowa bez '
  'ruchu.'),
 ('lorian',
  'thunderwave',
  'Fala gromu',
  'A',
  ('C', 'N'),
  'Sześcian 15 stóp, także sojusznicy. KON ST 14: 2k8 grzmotu i odepchnięcie o 10 stóp; sukces połowa '
  'bez odepchnięcia.'),
 ('lorian',
  'distracting_shout',
  'Rozpraszający okrzyk',
  'R',
  ('B',),
  'Gdy bohater w 30 stopach otrzymuje obrażenia od pojedynczego ataku, zmniejsz je o 1k6+2, minimum 0.'),
 ('nimra',
  'nimra_frost_pulse',
  'Lodowy impuls',
  'A',
  ('N',),
  'Obecne 1k8 zimna i -10 stóp ruchu przy porażce.'),
 ('nimra', 'nimra_acid_splash', 'Kwasowy rozprysk', 'A', ('C',), 'Obecne 1k6 kwasu w małym obszarze.'),
 ('nimra',
  'nimra_mind_spike',
  'Szpilka umysłu',
  'A',
  ('F',),
  'Obecne 1k6 psychicznych i odebranie reakcji.'),
 ('nimra', 'nimra_flame_fan', 'Wachlarz płomieni', 'A', ('C', '*'), 'Obecny stożek, 2k6/połowa.'),
 ('nimra', 'nimra_force_wave', 'Fala odrzutu', 'A', ('N', 'C'), 'Obecna linia, 2k6 i przesunięcie.'),
 ('nimra',
  'nimra_sticky_matrix',
  'Lepka matryca',
  'A',
  ('Z', 'N'),
  'Obecny teren i przewracanie, trzy rundy.'),
 ('nimra',
  'misty_step',
  'Mglisty krok',
  'D',
  ('N', 'Z'),
  'Teleport 30 stóp, bez dodatkowej opłaty ruchu.'),
 ('nimra',
  'nimra_sleep',
  'Sen',
  'A',
  ('F', 'N', '*'),
  'Pula 5k8 jak obecnie, sen najwyżej do końca następnej tury Nimry; pozostałe sposoby obudzenia '
  'pozostają.'),
 ('nimra', 'nimra_fog', 'Mgła', 'A', ('N', '*'), 'Obecny zasłonięty obszar; koncentracja, trzy rundy.'),
 ('nimra',
  'nimra_web',
  'Sieć',
  'A',
  ('Z', 'N', '*'),
  'Obecne unieruchamianie i trudny teren; koncentracja, trzy rundy.'),
 ('nimra',
  'nimra_lightning_path',
  'Piorunowy szlak',
  'A',
  ('C', 'N', '*'),
  'Obecne 3k6 i pojedynczy przeskok, również w sojusznika.'),
 ('nimra',
  'nimra_mind_break',
  'Załamanie woli',
  'A',
  ('F', 'N'),
  'Obecny obszar 2k6, brak reakcji i utrudnienie ataku.'),
 ('nimra',
  'nimra_stasis',
  'Staza istoty',
  'A',
  ('N', 'F', '*'),
  'Obecna blokada ruchu, ponawiane obrony, koncentracja do trzech rund.'),
 ('nimra', 'shatter', 'Roztrzaskanie', 'A', ('C', 'C', '*'), 'Obecne 3k8/połowa w obszarze.'),
 ('nimra',
  'shield',
  'Tarcza',
  'R',
  ('B',),
  '+3 KP wyłącznie przeciw jednemu atakowi; ponowna ocena trafienia. Zastępuje +5 KP do następnej '
  'tury.'),
 ('nimra',
  'nimra_sculpt_field',
  'Rzeźbienie pola',
  'MOD',
  ('N',),
  'Wyłącz do czterech pól jak obecnie.'),
 ('nimra', 'nimra_distant_spell', 'Odległy czar', 'MOD', ('Z',), '+15 stóp, maksymalnie 75.'),
 ('nimra',
  'nimra_overcharged_spell',
  'Przeciążony czar',
  'MOD',
  ('C',),
  'Jedna dodatkowa bazowa kość obrażeń. To inna zdolność niż ogólne przeciążenie koloru.'),
 ('nimra',
  'nimra_forced_weave',
  'Wymuszony splot',
  'MOD',
  ('F', 'F'),
  'Jeden cel ma utrudnienie pierwszej obrony; przez limit czar bazowy może kosztować najwyżej dwie '
  'karty.'),
 ('nimra',
  'nimra_energy_transmutation',
  'Transmutacja energii',
  'MOD',
  ('F',),
  'Zmień typ obrażeń w obecnym katalogu.'),
 ('erynd',
  'hunters_mark',
  'Znak łowcy',
  'D',
  ('Z',),
  '+1k6 raz na własną turę przy trafieniu oznaczonego celu bronią; koncentracja, trzy rundy. '
  'Przeniesienie po pokonaniu celu bez many i akcji. Ograniczenie raz na turę zastępuje dodawanie do '
  'każdego trafienia.'),
 ('erynd',
  'cunning_action',
  'Zwiadowcza mobilność',
  'D',
  ('Z',),
  'Sprint albo Odstąpienie; obejmuje opłatę za zwykły ruch w tej turze. Sprint zwiększa limit, '
  'Odstąpienie znosi ataki okazyjne. Wcześniejszy ruch liczy się do limitu.'),
 ('erynd',
  'aim',
  'Celowanie',
  'D',
  ('Z',),
  'Przed ruchem oddaj cały ruch, aby następny atak łukiem w tej turze miał przewagę. Osobny atak ma '
  'swój koszt many.'),
 ('erynd',
  'anchoring_arrow',
  'Strzała kotwicząca',
  'A',
  ('Z', 'N'),
  'Obecne trafienie i obrona SIŁ; ograniczenie ruchu do początku następnej tury Erynda, bez losowania '
  '1k4 rund.'),
 ('erynd',
  'exposing_arrow',
  'Strzała odsłaniająca',
  'A',
  ('Z', 'F'),
  'Trafienie: -2 KP do początku następnej tury Erynda. Zastępuje obniżenie o 1k8. Nie kumuluje się.'),
 ('erynd',
  'disrupting_arrow',
  'Strzała zakłócająca',
  'A',
  ('Z', 'N'),
  'Obecne odebranie reakcji i utrudnienie następnego ataku.'),
 ('erynd',
  'double_shot',
  'Podwójny strzał',
  'A',
  ('Z', 'C', '*'),
  'Dwa osobne strzały długim łukiem, każdy z +2 do trafienia, z możliwością różnych celów. Jedno '
  'wybrane trafienie dodaje +1k6 obrażeń tej techniki. Znak i Pierwsza krew również najwyżej raz w '
  'całej turze. Oba ataki są w cenie; obrażenia, krytyki i reakcje rozstrzygane osobno.'),
 ('erynd',
  'misty_step',
  'Mglisty krok',
  'D',
  ('N', 'Z'),
  'Teleport 30 stóp bez dodatkowej opłaty ruchu.'),
 ('erynd',
  'spike_growth',
  'Kolczaste zarośla',
  'A',
  ('Z', 'Z', '*'),
  'Obecny niebezpieczny trudny teren; koncentracja, najwyżej trzy rundy.'))

ABILITIES = tuple(ManaAbility(*row) for row in _ROWS)
HERO_NOTES: dict[str, str] = {'garran': 'Obrona daje +1 KP w pancerzu; Ulepszony krytyk daje krytyki bronią przy naturalnym 19–20; '
           'Żelazna linia daje sojusznikowi flankującemu z Garranem +1 KP przeciw wspólnemu '
           'przeciwnikowi. Nowy „Za tarczą”: raz we własnej turze, gdy przytomny bohater jest w 5 '
           'stopach, Garran może potraktować jedną N jako B w swojej zdolności ochronnej: Pozycji, '
           'Osłonie tarczą lub Osłonie towarzysza. Nie działa na samoleczenie.\n'
           '\n'
           'Nieustępliwość: jeśli Garran rozpoczyna zwykły Ruch obok przeciwnika (także po skosie), '
           'płaci 2 dowolne many zamiast 1. Koszt ustal raz na turę przy pierwszym rozpoczęciu '
           'ruchu; podział ruchu i późniejsze sąsiedztwo nie zmieniają tej ceny. Odepchnięcia '
           'i przemieszczenia ze zdolności nie uruchamiają skazy. Działa również solo.',
 'brakka': 'Widzenie w ciemności 60 stóp; Obrona bez pancerza daje KP 10 + modyfikator ZRC + '
           'modyfikator KON i pozwala na tarczę; Dzikie ataki dodają jedną kość broni do krytyka wręcz. '
           'Nieustępliwość półorka zostaje raz na długi odpoczynek, jako wyjątek ratunkowy — mana nie '
           'pozwala jej ponawiać. Nowy „Bitewny rozpęd”: raz we własnej turze, po trafieniu zwykłym '
           'atakiem opłaconym C, odzyskaj tę C z odrzuconych. Dotyczy podstawowego ataku, także '
           'objętego Lekkomyślnym, ale nie Potężnego ani innej techniki. Zwrot następuje dopiero po '
           'rozstrzygnięciu tego ataku, nie daje kolejnego ataku i podlega limitowi '
           'pięciu kart. Dopłata C za Lekkomyślny nie jest kartą opłacającą podstawowe uderzenie.\n'
           '\n'
           'Bitewny amok: jeśli Brakka jest w Szale, lecz w swojej turze nie zadeklarowała '
           'żadnego ataku ani szkodliwej techniki przeciw wrogowi, przed porządkowaniem rezerwy odrzuca '
           'jedną posiadaną kartę. Pudło nie uruchamia kary. Ta wersja zastępuje zakaz używania '
           'przedmiotów.',
 'mira': 'Mistrzyni ukrycia zachowuje test przeciw osobnym obserwatorom, limit ruchu 20 stóp podczas '
         'ukrycia i 25 po jego dobrowolnym zakończeniu, bez zwrotu wykonanego ruchu. Szczęście pozwala '
         'przerzucić naturalną 1 w ataku, teście i obronie. Ruchomy cel daje +2 KP przeciw dystansowym '
         'atakom bronią/czarem, nie obszarom. Ekspertyza podwaja biegłość w wybranych umiejętnościach. '
         'Atak z cienia ma +1k6 za ukrycie przed celem lub własną flankę, +2k6 za oba; raz na własną '
         'turę. Zmniejszamy dotychczasowe +2k6/+3k6, aby pojedynczy bonus nie mnożył się przez serię '
         'zwykłych ataków. Właściciel wybiera jedno kwalifikujące się trafienie przed rzutem jego '
         'obrażeń. Atak kończy ukrycie; kolejne uderzenia nie dziedziczą ukrycia z początku serii.\n'
         '\n'
         'Nowe „Zwinne dłonie”: raz we własnej turze po zakończeniu dowolnego odcinka legalnego ruchu o '
         'co najmniej 5 stóp zamień jedną posiadaną kartę z jedną kartą rynku. Zamiana 1:1, bez '
         'dobierania. Nie uruchamia się od przymusowego przesunięcia.\n'
         '\n'
         'Nowa Panika po zdemaskowaniu: raz między początkami własnych tur odrzuć jedną kartę, gdy test '
         'przeciwnika wykryje Mirę podczas aktywnej sesji ukrycia. Własny atak i dobrowolne wyjście nie '
         'uruchamiają kary. Zastępuje premię +2 dla obserwatorów; zasady widoczności pozostają.',
 'dagna': 'Widzenie w ciemności 60 stóp; Krasnoludzki ruch ignoruje karę szybkości z niewystarczającej '
          'Siły do pancerza; Krasnoludzka wytrzymałość daje +1 maksymalnego PW na poziom, już wliczone; '
          'Krasnoludzka odporność daje przewagę przeciw truciźnie i odporność na obrażenia od niej. '
          'Krok ratowniczki — po pomocy innemu sojusznikowi ruch 5 stóp bez many, raz we własnej turze. '
          'Nowy Uczeń Życia: raz we własnej turze można zastąpić jedną B przez Z w zdolności, która '
          'faktycznie przywraca PW innemu bohaterowi. Nie dotyczy przygotowania aury ani własnego '
          'leczenia. Stara premia zależna od poziomu komórki znika; +7 Słowa leczenia to już pełna '
          'premia, bez dodatkowego doliczania.\n'
          '\n'
          'Nowe Nikogo nie zostawiam: jeśli żywy bohater z 0 PW jest w 30 stopach, pierwsze ofensywne '
          'działanie Dagny we własnej turze kosztuje dodatkowo *. Leczenie, ratowanie, osłony i ruch '
          'nie dostają dopłaty. Zastępuje dotychczasowe utrudnienia/przewagę obron wrogów.',
 'lorian': '- **Rezerwuar:** pojemność sześciu kart i zachowanie trzech starych przed końcowym doborem. '
           'Dobór nadal trzy, start nadal trzy.\n'
           '- **Zgranie:** raz we własnej turze, przed końcowym doborem, zamień jedną swoją kartę z '
           'jedną kartą innego bohatera w 30 stopach. Zamiana 1:1. W grze solo zamiana z rynkiem.\n'
           '- **Obycie i targowanie:** +2 do pozabojowych testów Charyzmy.\n'
           '- **Improwizacja:** raz na NPC przerzut nieudanego pozabojowego testu Charyzmy przed '
           'konsekwencjami, drugi wynik ostateczny.\n'
           '- **Widzenie w ciemności:** 60 stóp w niemagicznej ciemności, bez widzenia przez mgłę.\n'
           '- **Dziedzictwo elfów:** przewaga przeciw zauroczeniu i odporność na magiczny sen.\n'
           '\n'
           'Stary Kusznik dający dwa darmowe strzały znika. Każdy zwykły strzał Loriana kosztuje * tak '
           'samo jak u innych. Inspiracja barw zastępuje Inspirację bardowską. Prowokujący ostrzał, '
           'Baśniowy ogień, Ohydny śmiech, Rozkaz sceniczny, Przyspieszony refren, Kontrapunkt i Cięte '
           'słowa ustępują siedmiu nowym zdolnościom zarządzania maną. To świadoma wymiana pozycji '
           'talii, nie dodatkowe ukryte czary.\n'
           '\n'
           '**Skaza — Potrzeba publiczności:** bez innego przytomnego bohatera w 10 stopach pierwsza '
           'zdolność specjalna użyta między początkami własnych tur kosztuje dodatkowo *. Dotyczy także '
           'reakcji, nie pasywów, zwykłego Ataku, ruchu i przedmiotów. W grze solo skaza jest '
           'nieaktywna. Nie wraca stara blokada zdolności.',
 'nimra': 'Widzenie w ciemności 60 stóp; Gnomia przebiegłość daje przewagę w obronach INT/MDR/CHA '
          'przeciw magii; Katalog niemożliwego daje dostęp do wszystkich piętnastu czarów bez '
          'przygotowania. Odzyskiwanie magiczne zastępujemy „Alchemią barw”: raz we własnej turze '
          'potraktuj jedną N jako dowolny kolor przy opłacaniu czaru lub Metamagii. Karta zostaje '
          'normalnie wydana; nie tworzy dodatkowej many.\n'
          '\n'
          'Nowe Echo magicznego wycieku: powtórzenie czaru lub Metamagii użytych w poprzedniej własnej '
          'turze powoduje dopłatę * do pierwszego takiego rzucenia w bieżącej własnej turze. Łączna '
          'dopłata najwyżej jedna, nawet gdy powtarzasz oba. Usuwamy zakaz powtarzania. Reakcje poza '
          'własną turą nie budują Echa. Pominięta tura czyści listę poprzednich wyborów. Maksymalny '
          'koszt po tej dopłacie wynosi pięć kart i mieści się w pojemności.',
 'erynd': 'Łucznictwo daje +2 do dystansowych ataków bronią, już wliczone w +8 łuku; Ekspertyza podwaja '
          'biegłość Skradania i Sztuki przetrwania; Widzenie w ciemności 60 stóp; Dziedzictwo elfów '
          'daje przewagę przeciw zauroczeniu i odporność na magiczny sen; Czujność daje +2 do '
          'inicjatywy i wykrywania ukrytych przeciwników, nie pułapek. Pierwsza krew zmniejszona do '
          '+1k6 raz na własną turę, wyłącznie łukiem w cel z pełnymi PW. Nowe „Czytanie prądów”: raz na '
          'końcu własnej tury, po własnym doborze z rynku, ale przed jego uzupełnieniem, obejrzyj dwie '
          'wierzchnie karty talii i odłóż je w wybranej kolejności. Jeśli pozostała jedna, widzisz '
          'jedną; oglądanie samo nie przewija talii. Przygotowuje uzupełnienie rynku dla kolejnych '
          'osób.\n'
          '\n'
          'Nowa Trauma bratobójczego strzału: pierwszy w swojej turze atak łukiem w cel mający '
          'przytomnego innego bohatera drużyny w 5 stopach kosztuje dodatkowo *. Jedna dopłata '
          'niezależnie od liczby bohaterów, bez starej kary do trafienia. Nóż, przywołania i NPC nie '
          'powodują dopłaty.'}

def hero_abilities(hero_id: str) -> tuple[ManaAbility, ...]:
    return tuple(ability for ability in ABILITIES if ability.hero_id == hero_id)


def mana_ability(hero_id: str, ability_id: str) -> ManaAbility | None:
    return next((a for a in (*ABILITIES, HOLY_SYMBOL_ABILITY) if a.hero_id == hero_id and a.id == ability_id), None)


def turn_supply(hero_id: str, *, green_surge: bool = False) -> dict[str, int]:
    return {"start": 5, "keep": 5, "draw": 5, "capacity": 5}

FLAWS = {
    'garran': ('flaw_remorse', 'Nieustępliwość',
        'Gdy po raz pierwszy w swojej turze zaczynasz zwykły ruch, sprawdź sąsiednie pola, także po skosie. Jeśli stoi tam przeciwnik, wydaj 2 dowolne many (*) zamiast 1. To cena całego ruchu w tej turze; kolejne odcinki nie wymagają dopłaty. Odepchnięcia i przemieszczenia ze zdolności nie uruchamiają skazy. Przykład: odpychasz jedynego sąsiadującego wroga tarczą, a potem ruszasz — płacisz 1 manę.'),
    'brakka': ('flaw_chains', 'Bitewny amok',
        'Na końcu swojej tury, jeśli nadal jesteś w Szale i nie zaatakowałaś wroga ani nie użyłaś przeciw niemu szkodliwej techniki, odrzuć 1 kartę many. Zrób to przed zachowaniem kart na kolejną turę. Nawet nieudany atak pozwala uniknąć tej kary. Jeśli nie masz kart, nic nie tracisz.'),
    'mira': ('flaw_exposed_panic', 'Panika po zdemaskowaniu',
        'Gdy przeciwnik wykryje cię testem podczas ukrycia, odrzuć 1 kartę many. Karę ponosisz najwyżej raz do początku swojej następnej tury. Ujawnienie się przez własny atak lub dobrowolne zakończenie ukrycia nie powoduje kary. Jeśli nie masz kart, nic nie tracisz.'),
    'dagna': ('flaw_leave_no_one', 'Nikogo nie zostawiam',
        'Jeśli w odległości do 30 ft leży żywy bohater z 0 PW, pierwsze działanie ofensywne w twojej turze kosztuje o 1 dowolną manę (*) więcej. Sprawdź ten warunek przy deklaracji działania. Leczenie, ratowanie, osłony i ruch nie wymagają dopłaty.'),
    'lorian': ('flaw_needs_audience', 'Potrzeba publiczności',
        'Jeśli nie ma innego przytomnego bohatera w odległości do 10 ft, pierwsza zdolność specjalna kosztuje o 1 dowolną manę (*) więcej. Dopłata może dotyczyć też reakcji; ponosisz ją najwyżej raz do początku swojej następnej tury. Zwykły atak, ruch, przedmioty i pasywy nie wymagają dopłaty. W grze solo skaza nie działa.'),
    'nimra': ('flaw_arcane_echo', 'Echo magicznego wycieku',
        'Zapamiętaj czary i Metamagię użyte we własnej turze. Jeśli w następnej turze powtórzysz któryś z nich, przy pierwszym powtórzeniu dopłać 1 dowolną manę (*). Łącznie płacisz najwyżej raz w turze, nawet jeśli powtórzysz i czar, i Metamagię. Reakcje poza własną turą nie liczą się do Echa. Pominięta tura usuwa zapamiętane wybory.'),
    'erynd': ('flaw_friendly_fire_trauma', 'Trauma bratobójczego strzału',
        'Pierwszy w twojej turze atak łukiem w cel sąsiadujący z innym przytomnym bohaterem kosztuje o 1 dowolną manę (*) więcej. Sąsiedztwo obejmuje też pola po skosie. Ataki nożem nie wymagają dopłaty. NPC i przywołane istoty stojące przy celu nie uruchamiają skazy.'),
}

MANA_PASSIVES = {
    'garran': ('mana_behind_shield', 'Za tarczą',
        'Raz w swojej turze, gdy na sąsiednim polu (także po skosie) stoi inny przytomny bohater, możesz zapłacić niebieską maną (N) zamiast jednej wymaganej białej (B). Dotyczy tylko Pozycji obronnej, Osłony tarczą i Osłony towarzysza. Kartę normalnie wydajesz; pozostały koszt się nie zmienia. Przykład: Osłonę tarczą opłacisz dwiema niebieskimi kartami zamiast białej i niebieskiej.'),
    'brakka': ('mana_momentum', 'Bitewny rozpęd',
        'Raz w swojej turze po trafieniu zwykłym atakiem opłaconym czerwoną maną (C) odzyskaj tę kartę z odrzuconych (limit 5 kart). Zwrot nie daje kolejnego ataku. Nie dotyczy dopłaty za Lekkomyślny atak ani kosztów technik.'),
    'mira': ('mana_nimble_hands', 'Zwinne dłonie',
        'Raz w swojej turze, po dobrowolnym przemieszczeniu się o co najmniej jedno pole (5 ft), możesz wymienić 1 kartę z ręki na 1 wybraną kartę rynku. Własną kartę połóż w miejsce zabranej. Nie dobierasz dodatkowych kart. Przymusowe przesunięcie nie uruchamia tej zdolności.'),
    'dagna': ('disciple_of_life', 'Uczeń Życia',
        'Raz w swojej turze, gdy zdolność przywraca PW innemu bohaterowi, możesz zapłacić zieloną maną (Z) zamiast jednej wymaganej białej (B). Kartę normalnie wydajesz. Własne leczenie i samo uruchomienie aury nie pozwalają na tę zamianę.'),
    'lorian': ('mana_reservoir', 'Rezerwuar i Zgranie',
        'Pojemność 6 kart. Na koniec tury zachowaj do 3 niewydanych kart i dobierz do 3 nowych; walkę zaczynasz z 3. Raz w swojej turze, przed doborem, możesz wymienić 1 kartę z ręki na 1 kartę innego bohatera w odległości do 30 ft. W grze solo wymieniasz ją z rynkiem. Wymiana nie daje dodatkowej karty.'),
    'nimra': ('mana_alchemy', 'Alchemia barw',
        'Raz w swojej turze, płacąc za czar lub Metamagię, możesz użyć jednej niebieskiej many (N) jako dowolnego koloru. Kartę normalnie wydajesz; opłaca tylko jeden symbol kosztu.'),
    'erynd': ('mana_read_currents', 'Czytanie prądów',
        'Na końcu swojej tury, po doborze many i przed uzupełnieniem rynku, możesz obejrzeć 2 wierzchnie karty talii i odłożyć je na wierzch w wybranej kolejności. Jeśli została tylko 1 karta, oglądasz tylko ją. Nie tasuj odrzuconych na potrzeby tego podglądu.'),
}

# Self-contained wording for cards; development notes stay in the design document.
_CARD_TEXT = {
 'second_wind': 'Odzyskaj 1k10+3 PW. Leczenie zajmuje akcję główną.',
 'shield_bash': 'Akcja dodatkowa; wymaga tarczy. Wybierz wroga na sąsiednim polu (5 ft). Rzuć k20 + modyfikator Siły; aplikacja rzuci za cel. Wygrana: 1k6 + modyfikator Siły obrażeń obuchowych i odepchnięcie o jedno wolne pole od Garrana. Zablokowane pole zatrzymuje tylko odepchnięcie. Remis lub przegrana: brak efektu.',
 'defensive_stance': '+2 KP do początku następnej własnej tury. Każda zmiana pola kończy efekt.',
 'garran_command_halt': 'Cel w 60 ft wykonuje obronę Mądrości ST 14. Porażka: brak dobrowolnego ruchu w następnej turze; sukces: połowa ruchu. Naturalne 1 daje również −2 do ataków; naturalne 20 neguje efekt.',
 'garran_guard_companion': 'Wybierz sąsiadującego sojusznika w 5 ft. Pierwszy pojedynczy wrogi atak, czar lub efekt przeciw niemu zostaje w całości przekierowany na Garrana i zużywa osłonę.',
 'garran_rally': 'Garran i słyszący sojusznicy w 30 ft usuwają Strach i zyskują przewagę na pierwszy atak, test albo rzut obronny do końca swojej następnej tury.',
 'shoulder_check': 'Przeciwnik w 5 ft, najwyżej o jeden rozmiar większy. Sporny test Atletyki; remis wygrywa obrońca. Odepchnij o 5 ft i dodatkowe 5 ft za każde pełne 5 punktów przewagi, maksymalnie 30 ft. Przeszkody zatrzymują przesunięcie.',
 'powerful_strike': 'Wymaga Szału. Jeden atak wręcz oparty na SIŁ: +2 do trafienia i +1k12 obrażeń przy trafieniu. Cały atak jest w cenie.',
 'hard_as_rock': 'Wymaga Szału. Po ujawnieniu obrażeń ataku i uwzględnieniu odporności zmniejsz je o 1k12+KON, minimum 0.',
 'grapple': 'Chwyt przeciwnika w 5 ft wymaga wolnej ręki i celu najwyżej o jeden rozmiar większego. Atletyka przeciw Atletyce/Akrobatyce celu; remis wygrywa obrońca. Sukces blokuje ruch celu do uwolnienia.',
 'hide': 'Wykonaj test Skradania przeciw osobnym obserwatorom. Wymagana legalna pozycja ukrycia; aplikacja pokazuje, kto nadal cię wykrywa. Dobrowolne zakończenie ukrycia nie kosztuje many ani akcji.',
 'smoke_screen': 'Przemieść Mirę do 15 ft bez ataków okazyjnych i wykonaj nowy test Ukrycia nawet obok wroga. Obserwatorzy mają karę do Percepcji równą połowie modyfikatora ZRC Miry, w dół. Ruch zawarty w cenie.',
 'combat_trap_detection': 'Wykonaj bojowy test Percepcji, aby wykryć ukryte pułapki w zasięgu obserwacji. Aplikacja podświetla pola wykrytych pułapek; samo wykrycie ich nie rozbraja.',
 'instinctive_dodge': 'Reakcja proponowana przed atakiem przeciw ukrytej Mirze. Nadaj temu jednemu atakowi utrudnienie.',
 'sacred_flame': 'Stożek 15 ft. Cele w obszarze wykonują obronę Zręczności; porażka: 1k8 obrażeń od blasku, sukces: brak obrażeń.',
 'healing_word': 'Przywróć 1k4+7 PW celowi w 60 ft. To pełna premia leczenia; nie doliczaj osobno Ucznia Życia.',
 'bless': 'Ruchoma aura Błogosławieństwa: sojusznicy w aurze dodają 1k4 do ataków i rzutów obronnych. Koncentracja, maksymalnie 3 rundy.',
 'preserve_life': 'Rozdziel 15 PW między wskazane cele, najwyżej do połowy maksymalnych PW każdego. Aplikacja podświetla legalnych odbiorców i kontroluje rozdział leczenia.',
 'divine_care_aura': 'Ruchoma aura: wrogowie w jej zasięgu mają −2 do ataków i obrażeń. Koncentracja, maksymalnie 3 rundy.',
 'guiding_bolt': 'Jeden atak czarem; trafienie zadaje 2k6 obrażeń od blasku i daje przewagę następnego ataku przeciw trafionemu celowi.',
 'healing_grace_aura': 'Aura 10 ft, koncentracja do 3 rund. Dwa pierwsze leczenia w aurze dodają po 1k8 PW.',
 'lesser_restoration': 'Dotknij celu w 5 ft i usuń jeden negatywny stan z listy dostępnej dla tej zdolności. Aplikacja pokazuje legalne stany i cele.',
 'turn_undead': 'Nieumarli w obszarze odpędzenia wykonują obronę Mądrości. Porażka: odpędzenie do końca następnej tury Dagny. Obrażenia kończą efekt wcześniej.',
 'aim': 'Przed ruchem poświęć cały jego limit: następny atak łukiem w tej turze ma przewagę. Atak opłacasz osobno.',
 'anchoring_arrow': 'Atak długim łukiem. Trafiony cel wykonuje obronę Siły ST 14: porażka blokuje ruch, sukces połowi ruch do początku następnej tury Erynda.',
 'exposing_arrow': 'Atak długim łukiem. Trafienie obniża KP celu o 2 do początku następnej tury Erynda. Efekt nie kumuluje się.',
}
_CARD_TEXT.update({'rage': 'Szał trwa modyfikator KON + modyfikator SIŁ rund (minimum 1), licząc rundę uruchomienia. '
         '+2 obrażeń ataków wręcz opartych na SIŁ, przewaga testów i obron SIŁ oraz odporność '
         'na obrażenia kłute, cięte i obuchowe. Płacisz raz; nie odnawiaj co turę. '
         'Utrata przytomności kończy Szał.',
 'deafening_roar': 'W Szale: stożek 15 ft, tylko wrogowie. Obrona KON, ST 12+KON Brakki. Porażka: 2k6 '
                   'grzmotu i brak dobrowolnego ruchu do końca najbliższej tury celu; sukces: połowa '
                   'obrażeń. Naturalne 1 daje też utrudnienie ataków, naturalne 20 neguje obrażenia.',
 'guard_vault': 'Atak wręcz z +2 do trafienia i +2 obrażeń wymaga wolnego pola dokładnie za celem. Po ataku '
                'przejdź na to pole; przesunięcie jest w cenie techniki.',
 'bless': 'Aura 10 ft wokół Dagny obejmuje ją i sojuszników: +1k4 do ataków i rzutów obronnych. '
          'Koncentracja, do 3 rund.',
 'divine_care_aura': 'Aura 5 ft wokół Dagny: wrogowie w zasięgu mają −2 do ataków i obrażeń. Koncentracja, '
                     'do 3 rund.',
 'guiding_bolt': 'Cel w 75 ft. Atak czarem; trafienie: 2k6 blasku i przewaga następnego ataku przeciw temu '
                 'celowi.',
 'preserve_life': 'Rozdziel 15 PW między siebie i sojuszników w 30 ft. Każdy cel może odzyskać PW najwyżej '
                  'do połowy swojego maksimum; niewykorzystane leczenie przepada.',
 'nimra_frost_pulse': 'Cel w 50 ft, obrona KON przeciw ST czarów Nimry. Porażka: 1k8 zimna i −10 ft '
                      'szybkości do początku następnej tury Nimry; sukces: brak efektu.',
 'nimra_acid_splash': 'Wskaż środek w 40 ft, promień 5 ft, także sojusznicy. Obrona ZRC przeciw ST Nimry: '
                      'porażka 1k6 kwasu, sukces bez obrażeń.',
 'nimra_mind_spike': 'Cel w 45 ft, obrona MDR przeciw ST Nimry. Porażka: 1k6 psychicznych i brak reakcji do '
                     'początku następnej tury Nimry; sukces: brak efektu.',
 'nimra_flame_fan': 'Stożek 15 ft, także sojusznicy. Obrona ZRC przeciw ST Nimry: porażka 2k6 ognia, sukces '
                    'połowa obrażeń.',
 'nimra_force_wave': 'Linia 30×5 ft, także sojusznicy. Obrona SIŁ przeciw ST Nimry: porażka 2k6 mocy i '
                     'odepchnięcie o 5 ft; sukces połowa obrażeń bez odepchnięcia.',
 'nimra_sticky_matrix': 'Środek w 50 ft, kwadrat 10×10 ft. Trudny teren przez 3 rundy, bez koncentracji. '
                        'Przy rzuceniu, wejściu lub początku tury istota wykonuje obronę ZRC przeciw ST '
                        'Nimry; porażka powala.',
 'nimra_sleep': 'Środek w 50 ft, promień 15 ft. Rzuć 5k8; pula usypia cele od najniższych aktualnych PW. Bez '
                'obrony; nie działa na nieumarłych i odpornych na zauroczenie. Sen do końca następnej tury '
                'Nimry, obrażeń lub obudzenia akcją. Bez koncentracji.',
 'nimra_fog': 'Środek w 50 ft, promień 15 ft. Mgła silnie przesłania obszar i ogranicza widoczność wszystkim '
              'istotom. Koncentracja, do 3 rund.',
 'nimra_web': 'Środek w 50 ft, kwadrat 20×20 ft. Trudny teren; obrona ZRC przeciw ST Nimry może '
              'unieruchomić. Uwolnienie: akcja i test SIŁ przeciw ST czaru. Koncentracja, do 3 rund.',
 'nimra_lightning_path': 'Cel w 60 ft: obrona ZRC przeciw ST Nimry, 3k6 błyskawic przy porażce, połowa przy '
                         'sukcesie. Następnie przeskok na jedną istotę w 15 ft od celu; aplikacja wskazuje '
                         'najbliższą istotę, także sojusznika; przy remisie wybiera wroga. Przeskok ma osobną obronę i te same obrażenia.',
 'nimra_mind_break': 'Środek w 50 ft, promień 10 ft, także sojusznicy. Obrona MDR przeciw ST Nimry: porażka '
                     '2k6 psychicznych i brak reakcji do początku następnej tury Nimry; sukces połowa '
                     'obrażeń.',
 'nimra_stasis': 'Wróg w 50 ft wykonuje obronę MDR przeciw ST Nimry. Porażka blokuje ruch i akcję ruchu; '
                 'powtarza obronę na końcu swoich tur. Koncentracja, do 3 rund.',
 'shatter': 'Środek w 60 ft, promień 10 ft, także sojusznicy. Obrona KON przeciw ST Nimry: porażka 3k8 '
            'grzmotu, sukces połowa obrażeń. Konstrukty mają utrudnienie obrony.',
 'shield': 'Reakcja na atak przeciw Nimrze: +3 KP wyłącznie przeciw temu atakowi i ponowna ocena trafienia.',
 'nimra_sculpt_field': 'Wyłącz do 4 wskazanych pól z obszaru następnego czaru. Modyfikuje obszar, nie czar '
                       'pojedynczego celu; koszt czaru płacisz osobno.',
 'nimra_distant_spell': 'Zwiększ zasięg następnego zgodnego czaru o 15 ft, najwyżej do 75 ft. Nie działa na '
                        'Tarczę ani Mglisty krok. Koszt czaru płacisz osobno.',
 'nimra_energy_transmutation': 'Zmień kwas, zimno, ogień, błyskawice lub grzmot następnego czaru na inny typ '
                               'z tej listy. Nie zmienia obrażeń psychicznych ani mocy. Koszt czaru płacisz '
                               'osobno.',
 'hamstring_cut': 'Atak wręcz z własnej flanki. Trafienie zadaje obrażenia broni i połowi szybkość celu do '
                  'początku następnej tury Miry.',
 'disrupting_arrow': 'Atak długim łukiem. Trafienie zadaje obrażenia broni, odbiera reakcje i daje '
                     'utrudnienie następnego ataku celu, najpóźniej do końca jego następnej tury.',
 'spike_growth': 'Środek w 50 ft, promień 20 ft. Trudny teren: każde 5 ft ruchu w obszarze zadaje 2k4 '
                 'obrażeń kłutych. Dotyczy również sojuszników. Koncentracja, do 3 rund.'})

from dataclasses import replace as _replace
ABILITIES = tuple(_replace(a, description=_CARD_TEXT.get(a.id, a.description.replace('Obecne ', '').replace('Obecny ', '').replace('Obecna ', '').replace(' jak obecnie', ''))) for a in ABILITIES)

# Version 0.3 is the single current catalogue; legacy rows above document the
# former profile and are not exposed to new-game menus or printers.
from .shared_mana_catalog import CATALOG as _SHARED_CATALOG, HOLY_SYMBOL as _HOLY_SYMBOL, SharedAbility

def _shared_presentation(a: SharedAbility) -> ManaAbility:
    return ManaAbility(a.hero_id, a.id, a.name, a.timing, tuple(a.cost),
                       a.full_description, a.category, a.duration, a.boosts)

ABILITIES = tuple(_shared_presentation(a) for a in _SHARED_CATALOG)
HOLY_SYMBOL_ABILITY = _shared_presentation(_HOLY_SYMBOL)
FLAWS.update({
    'garran': ('flaw_remorse', 'Nieustępliwość', 'Rozpoczęcie własnej tury przy wrogu, także po skosie, zmniejsza limit zwykłego ruchu o połowę do końca tej tury. Późniejsze usunięcie wroga nie znosi kary.'),
    'brakka': ('flaw_chains', 'Bitewny amok', 'Tura bez ataku lub szkodliwej techniki przeciw wrogowi kończy Szał. Nieudany atak wystarcza, by utrzymać Szał.'),
    'mira': ('flaw_exposed_panic', 'Ostrożność w ukryciu', 'Podczas ukrycia masz utrudnienie wszystkich rzutów obronnych oraz testów wykonywanych w ramach reakcji. Efekty bez rzutu, w tym Unik instynktowny, nie otrzymują kary.'),
    'dagna': ('flaw_leave_no_one', 'Nikogo nie zostawiam', 'Gdy przy deklaracji sąsiadujesz z żywym sojusznikiem mającym mniej niż połowę maksymalnych PW (również 0 PW), każde działanie ofensywne kosztuje dodatkową dowolną manę. Także zwykły atak; raz za działanie, nie za cel. UI przypomina przed płatnością.'),
    'nimra': ('flaw_arcane_echo', 'Echo magicznego wycieku', 'Kolejne użycia tego samego czaru z rzędu: dopłata 0, 1, 2, 3… dowolnych kart. Inny czar przerywa serię. Ruch, zwykły atak, pusta tura i odświeżenie talii nie zerują serii; reakcje jej nie zmieniają. Podbicie nie zmienia tożsamości czaru. Cały koszt maksymalnie 5.'),
})
MANA_PASSIVES.update({
    'garran': ('mana_behind_shield', 'Za tarczą', 'Raz we własnej turze przy przytomnym sąsiadującym bohaterze użyj niebieskiej zamiast jednej białej w koszcie bazowym Pozycji obronnej, Osłony tarczą lub Osłony towarzysza. Nie zastępuje podbić ani ultów.'),
    'brakka': ('mana_momentum', 'Bitewny rozpęd', 'Raz we własnej turze trafienie zwykłym atakiem w Szale daje 2 tymczasowe PW do początku następnej własnej tury.'),
    'mira': ('mana_nimble_hands', 'Zwinne dłonie', 'Raz we własnej turze po trafieniu nożem możesz przemieścić się o pole bez ataków okazyjnych i bez kosztu zwykłego ruchu.'),
    'lorian': ('mana_reservoir', 'Zgranie', 'Przygotowuj wspólny rynek Strojeniem i Odzyskiem. Karty kosztu trafiają na odrzucone przed efektem i również mogą być odzyskane. Brak prywatnej ręki lub rezerwy.'),
    'nimra': ('mana_alchemy', 'Alchemia barw', 'Raz we własnej turze użyj jednej niebieskiej jako dowolnego koloru bazowego kosztu czaru. Nie dotyczy wymaganych kolorów podbić ani ultów; kartę normalnie wydajesz.'),
    'erynd': ('mana_read_currents', 'Czytanie prądów', 'Przed końcowym uzupełnieniem rynku obejrzyj do dwóch wierzchnich kart talii i odłóż je w wybranej kolejności. Nie tasuj w tym celu stosu odrzuconych.'),
})
HERO_NOTES = {hero: MANA_PASSIVES[hero][2] + '\n\n' + FLAWS[hero][2] for hero in FLAWS}

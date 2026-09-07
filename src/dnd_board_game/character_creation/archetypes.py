"""Player-facing identity and play guidance for the curated starter heroes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HeroArchetype:
    actor_id: str
    class_id: str
    role: str
    tagline: str
    history: str
    motivation: str
    personal_goal: str
    turn_plan: tuple[str, ...]
    resources: tuple[str, ...]
    strengths: tuple[str, ...]
    pitfalls: tuple[str, ...]
    helper_code: str

    @property
    def qr_payload(self) -> str:
        return f"dndbg:v1:actor:{self.actor_id}"


HERO_ARCHETYPES = (
    HeroArchetype(
        "brakka",
        "barbarian",
        "Niszczycielka — obrażenia i wytrzymałość",
        "Nie chcę być bogata. Chcę móc odmówić.",
        (
            "Brakka przeżyła więcej wojen, oblężeń i źle opłaconych kontraktów, "
            "niż chce pamiętać. Dziś jest najemniczką Gildii Poszukiwaczy Przygód: "
            "walczy toporem, mówi wprost i każdą umowę traktuje śmiertelnie poważnie."
        ),
        (
            "Bierze zlecenia, aby uczciwie zarobić, przeżyć i odłożyć kolejną monetę "
            "na własny zajazd. Pomaga praktycznie, lecz każdą otrzymaną przysługę "
            "traktuje jak dług o nieznanej cenie."
        ),
        "Uzbierać na własny zajazd i zakończyć życie najemniczki.",
        (
            'Podejdź do przeciwnika i włącz Szał akcją dodatkową.',
            'Lekkomyślny atak ułatwia trafienie, lecz wystawia cię na łatwiejszy odwet.',
            'Dzikość wydawaj na Potężne uderzenie, Przyspieszenie, ryk albo reakcję Twarda jak skała.',
        ),
        (
            'Szał: 3 użycia; długi odpoczynek.',
            'Dzikość: każdy Szał odnawia 3 punkty (modyfikator Kondycji); koniec Szału usuwa resztę.',
            'Nieustępliwość półorka: 1 użycie; długi odpoczynek.',
        ),
        ("dużo PW", "wysokie obrażenia wręcz", "odporność podczas Szału"),
        (
            'słaby atak dystansowy',
            'podczas Szału nie używa mikstur, zwojów ani aktywnych mocy przedmiotów',
            'Lekkomyślny atak daje przewagę także atakującym Brakkę',
        ),
        "BR-01",
    ),
    HeroArchetype(
        "lorian",
        "bard",
        "Bard-wynalazca — kusza, kontrola i improwizacja",
        "Oczywiście, że sytuacja jest beznadziejna. Inaczej nie potrzebowalibyście barda.",
        (
            "Podczas oblężenia przeciętny muzyk Lorian zapragnął dotrzeć do ludzi, którzy "
            "nie czuli już nic poza strachem. Gość Ostatniego Rzędu odpowiedział, dając mu "
            "głos, charyzmę i magię w zamian za emocje wzbudzane w publiczności."
        ),
        (
            "Podróżuje, aby nieść ludziom prawdziwą nadzieję, badać naturę paktu i znaleźć "
            "własny głos. Drużyna daje mu też przynależność, lecz Lorian nie wie, czy jej "
            "przywiązanie dotyczy jego samego, czy magicznego daru."
        ),
        "Zrozumieć Gościa Ostatniego Rzędu i stworzyć pieśń poruszającą ludzi bez pomocy paktu.",
        (
            'Stań w 10 stopach od przytomnego sojusznika, aby móc używać zdolności specjalnych.',
            'Wybierz dwa zwykłe strzały, Lunetę optyczną albo ostrzał odpowiadający sytuacji.',
            'Inspiruj sojusznika przed ważnym rzutem; reakcje Kontrapunktu i Rozpraszającego okrzyku gra proponuje sama.',
        ),
        (
            'Inspiracja bardowska: 4 użycia (modyfikator Charyzmy), kość k6; krótki odpoczynek.',
            'Komórki czarów: 4 pierwszego i 2 drugiego poziomu; długi odpoczynek.',
            'Techniki kuszy, Kontrapunkt i Rozpraszający okrzyk nie zużywają Inspiracji. Improwizacja: raz na NPC.',
        ),
        ("dwa ataki kuszą", "testy Charyzmy", "kontrola obszaru"),
        (
            'niska Klasa Pancerza',
            'bez pobliskiego przytomnego sojusznika traci zdolności specjalne',
            'Oplatający ostrzał może ograniczyć ruch również sojusznikom',
        ),
        "LO-01",
    ),
    HeroArchetype(
        "dagna",
        "cleric",
        "Uzdrowicielka — leczenie i wzmocnienia",
        "Przestań krzyczeć. Jeszcze nawet nie zaczęłam.",
        (
            "Rodzina Dagny spłaciła dług wobec świątyni, oddając ją pod opiekę zakonu. "
            "Jej talent do magii leczniczej nazwano boskim przeznaczeniem, zanim nauczyła "
            "się pytać, czy sama chce takiego życia."
        ),
        (
            "Podejmuje kolejne wyprawy, bo zawsze istnieje ktoś, kto bez niej może umrzeć. "
            "Jednocześnie szuka doświadczeń, dzięki którym odkryje własne pragnienia i "
            "nauczy się odróżniać wiarę od oczekiwań innych ludzi."
        ),
        "Odkryć, kim jest poza rolą kapłanki i uzdrowicielki, oraz wybrać własne życie.",
        (
            'Utrzymuj sojuszników w zasięgu wybranej aury i pilnuj koncentracji.',
            'Słowo leczenia podnosi rannych na odległość; Boską Moc zachowaj na ciężkie obrażenia lub nieumarłych.',
            'Po pomocy pobliskiemu sojusznikowi skorzystaj z Kroku ratowniczki, gdy gra go zaproponuje.',
        ),
        (
            'Komórki czarów: 4 pierwszego i 2 drugiego poziomu; długi odpoczynek.',
            'Boska Moc: 1 użycie wspólne dla Zachowania życia i Odpędzania nieumarłych; krótki odpoczynek.',
            'Koncentracja: jedna aura lub inny efekt naraz; Krok ratowniczki najwyżej raz na turę Dagny.',
        ),
        ("wysoki pancerz", "leczenie", "obrażenia radiant i wsparcie"),
        (
            'gdy sojusznik w 30 stopach ma 0 PW, skaza utrudnia działania inne niż ratunek',
            'aury wymagają koncentracji i właściwej pozycji',
            'Słowo leczenia i Duchowa broń konkurują o akcję dodatkową',
        ),
        "DA-01",
    ),
    HeroArchetype(
        "sylwen",
        "druid",
        "Kontrola terenu i przetrwanie",
        "Słucha ziemi, ale nauczyła się, że czasem trzeba przemówić ogniem.",
        "Armie wycięły skraj lasu Sylwen. Od tej pory prowadzi ludzi i zwierzęta bezpiecznymi trasami przez zniszczone ziemie.",
        "Każda wyprawa odsłania nowy szlak i przynosi środki na ochronę ocalałych ostępów.",
        "Stworzyć mapę korytarzy, którymi uchodźcy ominą wojska i łowców niewolników.",
        (
            "Zmieniaj pole walki Entangle lub Faerie Fire, zanim przeciwnicy się rozproszą.",
            "Produce Flame służy jako bezkosztowy atak; komórki zostaw na ważne zwroty.",
            "Poza walką prowadź przez dzicz, badaj naturę i zabezpieczaj odpoczynek.",
        ),
        ("Komórki czarów: wracają po długim odpoczynku.", "Przygotowane czary: wybór po długim odpoczynku."),
        ("kontrola obszaru", "leczenie", "eksploracja"),
        ("wiele czarów wymaga koncentracji", "średnia obrona", "uważaj na sojuszników w obszarze"),
        "SY-01",
    ),
    HeroArchetype(
        "garran",
        "fighter",
        "Żelazna Straż — obrona pierwszej linii",
        "Nie obiecuję, że to dobry plan. Obiecuję, że pierwszy sprawdzę, gdzie się kończy.",
        (
            "Garran był dobrym dowódcą, dopóki wojna nie zmusiła go do wyboru między "
            "krzywdą niewinnych a ryzykiem dla własnych ludzi. Odmówił bezpodstawnych "
            "aresztowań; później dwóch wypuszczonych uczestniczyło w ataku na jego dawnych podwładnych."
        ),
        (
            "W Gildii przyjmuje małe, konkretne zlecenia: chroni człowieka, karawanę albo "
            "drogę odwrotu zamiast abstrakcyjnego interesu państwa. Szuka sposobu, by nadal "
            "osłaniać innych, nie oddając własnego sumienia żadnej instytucji."
        ),
        "Znaleźć własne zasady przyzwoitego działania bez obietnicy pewnego, dobrego rezultatu.",
        (
            'Zajmij przejście i osłoń sojuszników; ustawienie tarczy jest twoją główną decyzją.',
            'Uderzenie tarczą zużywa akcję dodatkową: możesz połączyć je ze zwykłym atakiem. Pozycję obronną wybierz przed ruchem.',
            'Taktykę wydawaj na rozkazy i osłonę. Po wykonaniu akcji możesz użyć Zrywu akcji akcją dodatkową.',
        ),
        (
            'Taktyka: 4 punkty (modyfikator Siły); długi odpoczynek.',
            'Drugi oddech i Zryw akcji: po 1 użyciu; krótki lub długi odpoczynek.',
            'Pozycja obronna: cały ruch. Uderzenie tarczą: akcja dodatkowa, bez puli użyć.',
        ),
        ("wysoki KP", "niezawodny atak", "kontrola pozycji"),
        (
            'mało opcji dystansowych',
            'leczenie nie cofa sumy ran śledzonej przez Wyrzuty sumienia',
            'Pozycja obronna wymaga niewydanego ruchu; Uderzenie tarczą wymaga wolnej akcji dodatkowej',
        ),
        "GA-01",
    ),
    HeroArchetype(
        "pim",
        "monk",
        "Mobilny napastnik",
        "Tam, gdzie inni widzą mur, Pim widzi drogę, poręcz i dwa dobre punkty odbicia.",
        "Pim dorastał wśród ulicznych posłańców. Dyscypliny nauczył go wędrowny mistrz, który pewnej nocy zniknął.",
        "Wyprawy pozwalają mu ćwiczyć, zarabiać i podążać za śladami nauczyciela.",
        "Dowiedzieć się, dlaczego tajna policja ścigała jego mistrza.",
        (
            "Uderzaj cele, do których ciężsi bohaterowie nie mogą bezpiecznie dotrzeć.",
            "Po ataku używaj dodatkowego ciosu Martial Arts, jeśli spełniasz warunki.",
            "Nie kończ tury otoczony; mobilność jest twoją prawdziwą obroną.",
        ),
        ("Na poziomie 1 nie masz jeszcze Ki; pojawi się jako wybór rozwoju na poziomie 2.",),
        ("mobilność", "wiele lekkich ataków", "Akrobatyka i Wnikliwość"),
        ("mało PW", "słaby ostrzał", "pancerz wyłącza kluczowe cechy"),
        "PI-01",
    ),
    HeroArchetype(
        "rhogar",
        "paladin",
        "Obrońca i awaryjne leczenie",
        "Odciął herb z tabardu, bo zaufanie chce odzyskać czynami, nie nazwiskiem.",
        "Rhogar pochodził z małego rodu, który dorobił się na wojennych dostawach. Sprzeciwił się rodzinie i został wygnany.",
        "Chroni podróżnych i przyjmuje uczciwe kontrakty, budując reputację od zera.",
        "Udowodnić udział rodu w sprzedaży wadliwego wyposażenia obu stronom konfliktu.",
        (
            "Stań między zagrożeniem a rannymi; miecz i tarcza utrzymują wysoką obronę.",
            "Lay on Hands dziel na tyle punktów, ile naprawdę potrzeba do powrotu do walki.",
            "Na poziomie 2 sam wybierzesz styl walki i przygotowane czary.",
        ),
        ("Lay on Hands: 5 punktów, wracają po długim odpoczynku."),
        ("wysoki KP", "leczenie bez czaru", "silne testy społeczne"),
        ("na poziomie 1 brak komórek czarów", "niewielki dystans", "nie wydawaj całego leczenia bez potrzeby"),
        "RH-01",
    ),
    HeroArchetype(
        "erynd",
        "ranger",
        "Zwiadowca — tropienie i ostrzał",
        "Nie jestem przewrażliwiony. Po prostu pamiętam, że rzeczy naprawdę się zdarzają.",
        (
            "Erynd ostrzegał rodzinną osadę przed znakami magicznego przesilenia, lecz nikt "
            "go nie słuchał. Przeżył falę wypaczenia dzięki przygotowanemu schronieniu; wielu "
            "mieszkańców zaginęło, wśród nich jego ojciec."
        ),
        (
            "Podróżuje, aby badać narastający chaos oraz tworzyć bezpieczne szlaki, schronienia "
            "i ukryte magazyny. Drużynę traktuje jak ludzi, których musi przygotować na wszystko, "
            "nawet jeśli jego troska zaczyna przypominać kontrolę."
        ),
        "Odnaleźć ojca i zbudować sieć miejsc, w których ludzie przetrwają kolejną katastrofę.",
        (
            'Wybierz linię strzału i cel, obok którego stoi jak najmniej sojuszników.',
            'Przed ruchem zdecyduj, czy zużyć go na Celowanie; Zwiadowcza mobilność pomaga utrzymać dystans.',
            'Instynkt wydawaj na Znak łowcy, strzały kontroli lub teren. Po pokonaniu celu przenieś Znak bez kosztu.',
        ),
        (
            'Instynkt: 4 punkty (modyfikator Zręczności); długi odpoczynek.',
            'Podwójny strzał: 2 Instynktu; pozostałe strzały i czary talii po 1.',
            'Celowanie zużywa cały ruch; Zwiadowcza mobilność akcję dodatkową. Nie mają puli użyć.',
        ),
        ("atak dystansowy", "zwiad", "tropienie i skradanie"),
        (
            'walka w zwarciu utrudnia strzelanie',
            'sojusznicy przy celu powodują karę do ataku długim łukiem',
            'Celowanie i zmiana pozycji konkurują o ruch',
        ),
        "ER-01",
    ),
    HeroArchetype(
        "mira",
        "rogue",
        "Specjalistka — infiltracja i precyzyjne obrażenia",
        "Nie uciekam. Po prostu wybieram lepsze miejsce do dalszej rozmowy.",
        (
            "Mira spłacała rodzinny dług w przestępczej Rodzinie Jedwabnego Sznura. "
            "Gdy zrozumiała, że dług jest tylko smyczą, uciekła z łupem i fałszywymi "
            "dokumentami — ale bez starszego brata."
        ),
        (
            "Zlecenia dają jej pieniądze, sojuszników i doświadczenie potrzebne do "
            "bezpiecznego powrotu. Chce żyć pod własnym nazwiskiem, lecz znaki Rodziny "
            "wciąż potrafią uciszyć najbardziej bezczelną osobę w drużynie."
        ),
        "Dowiedzieć się, co stało się z bratem, i uwolnić go od Rodziny Jedwabnego Sznura.",
        (
            'Szukaj własnej flanki lub celu, który cię nie widzi; razem dają +3k6 raz na turę.',
            'Ukryj się wykonuje nowy test Skradania przeciw osobnym testom Percepcji wrogów. Atak kończy ukrycie.',
            'Oszczędzaj Fortele na specjalne ataki, Zasłonę dymną i Unik instynktowny.',
        ),
        (
            'Fortele: 4 punkty (modyfikator Zręczności); długi odpoczynek.',
            'Unik instynktowny: reakcja i 1 Fortel; nie ma osobnej puli.',
            'Atak z cienia: raz na turę; +1k6 flanka, +2k6 ukrycie, +3k6 razem.',
        ),
        (
            'precyzyjne obrażenia',
            'ukrycie i flankowanie',
            'ekspertyza i wykrywanie pułapek',
        ),
        (
            'widzący ją wróg ma +2 do ataków podczas sesji skradania',
            'ukrycie ogranicza ruch do 20 stóp i kończy się po ataku',
            'większość Forteli wymaga odpowiedniego ustawienia i broni',
        ),
        "MI-01",
    ),
    HeroArchetype(
        "veyra",
        "sorcerer",
        "Artyleria magiczna",
        "Kiedy kłamstwo przestało wystarczać, odpowiedziała ogniem, którego sama się przestraszyła.",
        "Veyra żyła z przekrętów. Niekontrolowany wybuch magii ujawnił korupcję urzędnika i uczynił z niej niewygodnego świadka.",
        "W grupie łatwiej przetrwać pościg i nauczyć się panować nad mocą.",
        "Zdobyć dowody oczyszczające jej imię, zanim łowcy nagród znajdą ją pierwsi.",
        (
            "Fire Bolt jest podstawowym atakiem bez kosztu; Magic Missile zostaw na pewne trafienie.",
            "Shield to reakcja ratująca przed trafieniem — zachowaj na nią komórkę, gdy grozi ci ostrzał.",
            "Trzymaj dystans i linię widzenia, ale korzystaj z osłon.",
        ),
        ("Komórki czarów: wracają po długim odpoczynku.",),
        ("pewne obrażenia", "silny atak dystansowy", "Charyzma"),
        ("mało PW", "niewiele poznanych czarów", "Shield konkuruje o tę samą pulę komórek"),
        "VE-01",
    ),
    HeroArchetype(
        "kael",
        "warlock",
        "Stały ostrzał i ryzykowna magia",
        "Przeżył dzięki umowie, której treść rozumie coraz mniej — i właśnie dlatego czyta każdy przypis.",
        "Kael badał zakazane archiwum. Gdy je podpalono, przyjął głos z płomieni i wyszedł żywy, ale nie sam.",
        "Wyprawy dają dostęp do ruin, rytuałów i ludzi znających sposób na zerwanie paktu.",
        "Poznać prawdziwe imię patrona i znaleźć lukę, która zakończy umowę.",
        (
            "Eldritch Blast jest twoim niezawodnym atakiem; szukaj czystej linii strzału.",
            "Komórki paktu są nieliczne, ale wracają po krótkim odpoczynku.",
            "Hellish Rebuke zachowaj jako reakcję; Burning Hands stosuj, gdy trafisz kilka celów bez sojuszników.",
        ),
        ("Magia paktu: 1 komórka, wraca po krótkim lub długim odpoczynku."),
        ("dobry atak dystansowy", "krótki odpoczynek odnawia magię", "silna Charyzma"),
        ("tylko jedna komórka na początku", "mało wytrzymały", "obszar ognia może objąć sojuszników"),
        "KA-01",
    ),
    HeroArchetype(
        "nimra",
        "wizard",
        "Kontrolerka magiczna — teren i wiedza",
        "Nie pomyliłam się. Otrzymaliśmy po prostu wyjątkowo nieoczekiwany wynik.",
        (
            "Nimra była błyskotliwą badaczką teorii magii. Podczas eksperymentu "
            "z niestabilnym źródłem mocy zignorowała ostrzeżenia: laboratorium zostało "
            "zniszczone, a jej najbliższy współpracownik zaginął w anomalii."
        ),
        (
            "Wyprawy zapewniają ochronę, dostęp do anomalii oraz materiał do badań. "
            "Nimra wierzy, że większa wiedza pozwoli jej przewidzieć wszystkie konsekwencje "
            "i naprawić błąd, którego nadal nie potrafi nazwać własną winą."
        ),
        "Zrozumieć magiczne przesilenie i odkryć los współpracownika zaginionego w laboratorium.",
        (
            'Wybierz czar i jego obszar; opcjonalną Metamagię wybierz przed czarem.',
            'Sprawdź pola sojuszników: obszary i Piorunowy szlak mogą ich objąć.',
            'Zmieniaj czary i Metamagię między rundami; Echo blokuje powtórzenie wyboru z poprzedniej rundy.',
        ),
        (
            'Komórki czarów: 4 pierwszego i 2 drugiego poziomu; długi odpoczynek.',
            'Punkty Metamagii: 4 (modyfikator Inteligencji); długi odpoczynek.',
            'Odzyskiwanie magiczne: raz na długi odpoczynek, podczas krótkiego odzyskaj łącznie 2 poziomy komórek.',
        ),
        ("najszerszy wybór magii", "wiedza", "kontrola grup"),
        (
            'niska Klasa Pancerza i mało PW',
            'obszary i przeskok pioruna mogą trafić sojuszników',
            'Echo blokuje w kolejnej rundzie użyte czary i Metamagię',
        ),
        "NI-01",
    ),
)

HERO_ARCHETYPES_BY_ID = {hero.actor_id: hero for hero in HERO_ARCHETYPES}

PLAYABLE_HERO_IDS = (
    "garran",
    "brakka",
    "mira",
    "dagna",
    "lorian",
    "nimra",
    "erynd",
)
PLAYABLE_HERO_ARCHETYPES = tuple(
    HERO_ARCHETYPES_BY_ID[actor_id] for actor_id in PLAYABLE_HERO_IDS
)


def hero_archetype(actor_id: str) -> HeroArchetype | None:
    return HERO_ARCHETYPES_BY_ID.get(actor_id)


__all__ = [
    "HERO_ARCHETYPES",
    "HERO_ARCHETYPES_BY_ID",
    "PLAYABLE_HERO_ARCHETYPES",
    "PLAYABLE_HERO_IDS",
    "HeroArchetype",
    "hero_archetype",
]

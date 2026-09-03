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
            "Podejdź do najgroźniejszego przeciwnika i odetnij go od słabszych sojuszników.",
            "Włącz Szał przed serią wymian ciosów, nie na końcu walki.",
            "Łącz Lekkomyślny atak z impetem, gdy szybkie pokonanie celu jest warte ryzyka.",
        ),
        (
            "Szał: 2 użycia, wracają po długim odpoczynku.",
            "Niepowstrzymany impet: 1 użycie na krótki odpoczynek.",
            "Dzikość: 2 użycia na długi odpoczynek.",
        ),
        ("dużo PW", "wysokie obrażenia wręcz", "odporność podczas Szału"),
        (
            "słaby atak dystansowy",
            "podczas Szału nie może używać mikstur, zwojów ani mocy przedmiotów",
            "każdą przysługę traktuje jak zobowiązanie, a Szał bojowy kończy Wyczerpaniem",
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
            "Ustaw się blisko sojusznika i wybierz techniczny ostrzał pasujący do sytuacji.",
            "Luneta nagradza pozostanie w miejscu, a Oplatający ostrzał zamyka obszar także kosztem sojuszników.",
            "Inspiruj bohatera, którego kolejny ważny test uruchomi też reakcje Loriena.",
        ),
        ("Inspiracja: użycia zależne od Charyzmy i wracają po krótkim odpoczynku.", "Komórki czarów: wracają po długim odpoczynku."),
        ("dwa ataki kuszą", "testy Charyzmy", "kontrola obszaru"),
        (
            "mało wytrzymały",
            "nie potrafi przestać występować ani pozostawić ciszy w spokoju",
            "bez przytomnego sojusznika w pobliżu traci dostęp do zdolności specjalnych",
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
            "Stań blisko pierwszej linii, ale nie musisz prowadzić każdego natarcia.",
            "Lecz, gdy zapobiega to utracie tury lub śmierci; wcześniej wzmacniaj i atakuj.",
            "Masz stałą osobistą talię czarów; komórki zachowaj na najważniejsze chwile.",
        ),
        ("Komórki czarów: wracają po długim odpoczynku.", "Magia domeny i leczenie korzystają z Mądrości."),
        ("wysoki pancerz", "leczenie", "obrażenia radiant i wsparcie"),
        (
            "nie potrafi odmówić rannemu, którego może uratować",
            "tłumi własne potrzeby, a potem obwinia innych za swoje poświęcenie",
            "pilnuj koncentracji i zachowaj drogę do rannych",
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
            "Zajmij przejście, osłoń słabszych i zmuszaj wrogów do walki z tobą.",
            "Drugi oddech i Pozycję obronną zachowaj na moment, gdy utrzymają linię.",
            "Miecz i tarcza dają niezawodność; Rozkaz i Osłona tarczą zmieniają układ walki.",
        ),
        (
            "Drugi oddech, Zryw akcji i Pozycja obronna: wracają po krótkim odpoczynku.",
            "Ratunek polowy: 5 × poziom punktów na długi odpoczynek.",
            "Taktyka: 3 użycia; wraca po długim odpoczynku.",
        ),
        ("wysoki KP", "niezawodny atak", "kontrola pozycji"),
        (
            "mało opcji dystansowych",
            "lęk przed błędną decyzją może odebrać mu jasność przywództwa",
            "czasem traktuje towarzyszy jak podwładnych, choć sam nie ufa dowódcom",
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
            "Zacznij z bezpiecznego dystansu i wybierz linię strzału bez osłony celu.",
            "Oznaczenie celu wzmacnia serię strzałów, a Zwiadowcza mobilność pomaga utrzymać dystans.",
            "Instynkt wydawaj na kontrolę terenu, mobilność albo wykrycie ukrytego zagrożenia.",
        ),
        ("Instynkt: 3 użycia na długi odpoczynek.",),
        ("atak dystansowy", "zwiad", "tropienie i skradanie"),
        (
            "walka w zwarciu utrudnia strzelanie",
            "zużywa czas i zasoby na mało prawdopodobne zagrożenia",
            "im bardziej zależy mu na innych, tym mniej ufa ich decyzjom",
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
            "Szukaj celu, przy którym sojusznik stoi w zwarciu, aby uruchomić Atak ukradkowy.",
            "Atakuj z ukrycia lub korzystnej pozycji, a potem zmieniaj miejsce.",
            "Fortele wydawaj na uniknięcie skupionego ostrzału albo przygotowanie pewnego trafienia.",
        ),
        (
            "Atak ukradkowy: raz na turę po spełnieniu warunków, bez osobnej puli.",
            "Fortele: 3 użycia na długi odpoczynek.",
            "Unik instynktowny: 1 użycie na krótki odpoczynek.",
        ),
        ("wysokie obrażenia jednego trafienia", "ekspertyza", "pułapki i zamki"),
        (
            "krucha pod ostrzałem",
            "Atak ukradkowy wymaga właściwej sytuacji",
            "strach, wstyd i utratę kontroli maskuje prowokacją albo agresją",
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
            "Korzystasz ze stałej osobistej talii; nowe karty wybierasz podczas awansu.",
            "Promień mrozu spowalnia, Sen kontroluje grupę, a Tarcza chroni po ujawnieniu trafienia.",
            "Nie stój na pierwszej linii; planuj zasięg, osłonę i koncentrację.",
        ),
        ("Komórki czarów: wracają po długim odpoczynku.", "Odzyskiwanie magiczne: część komórek odzyskasz podczas dozwolonego krótkiego odpoczynku."),
        ("najszerszy wybór magii", "wiedza", "kontrola grup"),
        (
            "najmniej wytrzymała",
            "nie potrafi przyznać, że czegoś nie wie, i brnie dalej mimo ostrzeżeń",
            "utrata koncentracji uruchamia Echo magicznego wycieku",
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

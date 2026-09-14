"""Approved arena ability catalogue shared by rules, UI and printed cards."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Boost:
    id: str
    color: str
    maximum: int
    label: str


@dataclass(frozen=True, slots=True)
class SharedAbility:
    hero_id: str
    id: str
    name: str
    timing: str
    category: str
    cost: str
    description: str
    duration: str = ""
    boosts: tuple[Boost, ...] = ()
    boost_limit: int = 3

    def payment(self, boosts: Mapping[str, int], surcharge: int = 0) -> tuple[str, ...]:
        known = {b.id: b for b in self.boosts}
        if set(boosts)-known.keys():
            raise ValueError("Nieznane podbicie zdolności.")
        if type(surcharge) is not int or surcharge < 0:
            raise ValueError("Nieprawidłowa dopłata.")
        for key, count in boosts.items():
            if type(count) is not int or not 0 <= count <= known[key].maximum:
                raise ValueError("Przekroczony limit podbicia.")
        if sum(boosts.values()) > self.boost_limit:
            raise ValueError("Przekroczony łączny limit podbić.")
        result = tuple(self.cost) + tuple(b.color for b in self.boosts for _ in range(boosts.get(b.id, 0))) + ("*",)*surcharge
        if len(result) > 5:
            raise ValueError("Cały koszt, razem ze skazą, nie może przekroczyć pięciu kart.")
        return result

    @property
    def full_description(self) -> str:
        suffix = {"T": "Do początku następnej tury źródła (T).", "O": "Do odświeżenia talii (O)."}.get(self.duration, "")
        boosts = " ".join(f"{b.label} (maks. {b.maximum})." for b in self.boosts)
        return " ".join(part for part in (self.description, suffix, boosts) if part)


def _b(id: str, color: str, maximum: int, label: str) -> Boost:
    return Boost(id, color, maximum, label)


def _a(hero: str, id: str, name: str, timing: str, category: str, cost: str,
       text: str, duration: str = "", *boosts: Boost, limit: int = 3) -> SharedAbility:
    return SharedAbility(hero, id, name, timing, category, cost, text, duration, boosts, limit)


CATALOG = (
    _a("garran", "second_wind", "Drugi oddech", "A", "basic", "*", "Odzyskaj 1k10 + KON PW."),
    _a("garran", "defensive_stance", "Pozycja obronna", "D", "basic", "B", "+2 KP; każda zmiana pola kończy postawę.", "O"),
    _a("garran", "garran_command_halt", "Rozkaz: Stać!", "A", "basic", "N", "Wróg w 60 ft: obrona MDR. Porażka połowi ruch i odbiera reakcje.", "T"),
    _a("garran", "garran_guard_companion", "Osłona towarzysza", "R", "basic", "B", "Przed rozstrzygnięciem pojedynczego ataku na sąsiadującego sojusznika przejmij go na siebie. Nie obejmuje obszarów."),
    _a("garran", "shield_bash", "Uderzenie tarczą", "D", "boost", "NC", "Sporny test SIŁ: twój fizyczny k20 + SIŁ, automatyczny rzut wroga. Remis wygrywa obrońca. Wygrana: 1k6 + SIŁ i odepchnięcie o pole.", "", _b("damage", "C", 2, "Czerwona: +1k6 obrażeń")),
    _a("garran", "garran_shield_wall", "Osłona tarczą", "D", "boost", "B*", "Sąsiadujący sojusznicy otrzymują +2 KP; bez premii dla Garrana.", "T", _b("ward", "B", 2, "Biała: 5 tymczasowych PW jednemu sojusznikowi; różne cele")),
    _a("garran", "garran_rally", "Mowa dowódcy", "A", "boost", "B*", "Garran i sojusznicy w 15 ft usuwają Strach i mają przewagę pierwszego ataku.", "T", _b("heal", "B", 2, "Biała: wybrany uczestnik odzyskuje 1k6 PW")),
    _a("garran", "iron_bastion", "Żelazny bastion", "A", "ultimate", "BBBN", "Aura 10 ft: Garran i sojusznicy w niej mają premię do KP równą modyfikatorowi Siły Garrana oraz ochronę przed przymusowym przesunięciem.", "O"),
    _a("garran", "counterattack_command", "Rozkaz: Kontratak!", "A", "ultimate", "BBCC", "Garran i jeden sojusznik w 15 ft przemieszczają się do 10 ft bez ataków okazyjnych i wykonują po jednym ataku bronią. Sojusznik zużywa reakcję."),
    _a("brakka", "rage", "Szał", "D", "basic", "C", "+2 obrażeń ataków wręcz opartych na SIŁ, przewaga testów i obron SIŁ, odporność na kłute, cięte i obuchowe. Nieprzytomność albo tura bez ofensywy kończy Szał.", "O"),
    _a("brakka", "reckless_attack", "Lekkomyślny atak", "MOD", "basic", "C", "Przewaga następnego zwykłego ataku wręcz opartego na SIŁ w tej turze. Wrogowie mają przewagę ataków przeciw Brakce.", "T"),
    _a("brakka", "acceleration", "Przyspieszenie", "D", "basic", "Z", "W Szale podwaja limit ruchu bieżącej tury. Wcześniejszy ruch wlicza się do limitu."),
    _a("brakka", "hard_as_rock", "Twarda jak skała", "R", "basic", "*", "W Szale: po odporności zmniejsz otrzymane obrażenia o 1k12 + KON, minimum zero."),
    _a("brakka", "powerful_strike", "Potężne uderzenie", "A", "boost", "C*", "W Szale wykonaj jeden atak bronią z dodatkowym 1k12 obrażeń.", "", _b("damage", "C", 2, "Czerwona: +1k12 obrażeń")),
    _a("brakka", "shoulder_check", "Z bara", "A", "boost", "C*", "Sporny test Atletyki przeciw sąsiadującemu wrogowi, maksymalnie o rozmiar większemu. Wygrana odpycha o pole; remis broni cel.", "", _b("push", "N", 2, "Niebieska: dodatkowe pole odepchnięcia"), _b("damage", "C", 2, "Czerwona: 1k6 obrażeń"), limit=2),
    _a("brakka", "deafening_roar", "Ogłuszający ryk", "A", "boost", "CN", "W Szale: wrogowie w stożku 15 ft, obrona KON; 1k6 grzmotu, sukces daje połowę.", "", _b("damage", "C", 2, "Czerwona: +1k6 obrażeń"), _b("root", "N", 1, "Niebieska: przy porażce brak ruchu (T)")),
    _a("brakka", "reaper", "Siekator", "A", "ultimate", "CCCC", "W Szale wykonaj trzy osobne ataki wręcz, rozdzielane między dostępnych wrogów."),
    _a("brakka", "unstoppable", "Niepowstrzymana", "A", "ultimate", "CCCZ", "W Szale: ruch do 20 ft bez ataków okazyjnych i trudnego terenu, potem ataki w dwóch różnych wrogów. Trafieni bronią się SIŁ przed powaleniem (T lub do wstania)."),
    _a("mira", "hide", "Ukryj się", "D", "basic", "*", "Test Skradania w legalnej pozycji. Wykrycie, atak lub dobrowolne ujawnienie kończy ukrycie.", "O"),
    _a("mira", "instinctive_dodge", "Unik instynktowny", "R", "basic", "Z", "Nadaj utrudnienie jednemu atakowi przeciw Mirze. Nie wymaga rzutu Miry."),
    _a("mira", "feint", "Zwód", "D", "basic", "F", "Sąsiadujący wróg nie może wykonywać ataków okazyjnych przeciw Mirze.", "T"),
    _a("mira", "hamstring_cut", "Cięcie ścięgna", "A", "basic", "Z*", "Atak wręcz z własnej flanki. Trafienie zadaje obrażenia broni i połowi ruch celu.", "T"),
    _a("mira", "smoke_screen", "Zasłona dymna", "D", "boost", "Z*", "Ruch do 10 ft bez ataków okazyjnych i próba ukrycia, także po rozpoczęciu obok wroga. Ukrycie kończą atak lub wykrycie.", "O", _b("move", "Z", 2, "Zielona: +5 ft ruchu"), _b("stealth", "F", 1, "Czarna: przewaga testu ukrycia")),
    _a("mira", "guard_vault", "Przeskok przez gardę", "A", "boost", "Z*", "Atak wręcz i przejście na wolne pole dokładnie za celem.", "", _b("damage", "C", 2, "Czerwona: +1k6 obrażeń")),
    _a("mira", "blade_mistress", "Mistrzyni ostrzy", "A", "boost", "ZF", "Atak nożem z ukrycia albo własnej flanki, dodatkowe 1k6 obrażeń.", "", _b("damage", "C", 2, "Czerwona: +1k6 obrażeń"), _b("bleed", "F", 1, "Czarna: krwawienie 1k4 na początku tury celu (O); leczenie kończy, bez kumulowania")),
    _a("mira", "shadow_verdict", "Wyrok z cienia", "A", "ultimate", "FFFF", "Wymaga ukrycia przed celem i własnej flanki. Jeden atak z przewagą i dodatkowym 5k6 obrażeń."),
    _a("mira", "blade_dance", "Taniec ostrzy", "A", "ultimate", "ZZFF", "Ruch do 15 ft bez ataków okazyjnych i dwa ataki w różnych wrogów po drodze. Atak z cienia najwyżej raz."),
    _a("dagna", "sacred_flame", "Święty płomień", "A", "basic", "B", "Stożek 15 ft, także sojusznicy. Obrona ZRC: porażka 1k8 blasku, sukces bez obrażeń."),
    _a("dagna", "bless", "Błogosławieństwo", "A", "basic", "BN", "Aura 10 ft: Dagna i sojusznicy mają +1k4 do ataków i obron. Koncentracja.", "O"),
    _a("dagna", "lesser_restoration", "Pomniejsze przywrócenie", "A", "basic", "B*", "Dotykiem usuń jeden dostępny stan: zatrucie, oślepienie lub głuchotę."),
    _a("dagna", "caring_gesture", "Opiekuńczy gest", "D", "basic", "*", "Sąsiadujący sojusznik otrzymuje 1k4 + MDR tymczasowych PW. Nie leczy ran; tymczasowe PW nie kumulują się.", "T"),
    _a("dagna", "healing_word", "Słowo leczenia", "A", "boost", "B*", "Cel w 60 ft odzyskuje 1k4 + 7 PW.", "", _b("heal", "B", 3, "Biała: +1k6 leczenia")),
    _a("dagna", "divine_care_aura", "Aura Boskiej Opieki", "A", "boost", "B*", "Wrogowie w 5 ft mają −2 do ataków. Koncentracja.", "O", _b("radius", "N", 1, "Niebieska: promień 10 ft"), _b("reduction", "B", 1, "Biała: również −2 do zadawanych obrażeń")),
    _a("dagna", "guiding_bolt", "Naprowadzający pocisk", "A", "boost", "B*", "Atak czarem w 75 ft: 2k6 blasku; przewaga następnego ataku przeciw celowi (T lub do wykorzystania).", "", _b("damage", "C", 3, "Czerwona: +1k6 obrażeń")),
    _a("dagna", "preserve_life", "Zachowanie życia", "A", "ultimate", "BBBB", "Rozdziel 40 PW leczenia między Dagnę i sojuszników w 30 ft, do ich maksymalnych PW."),
    _a("dagna", "spiritual_weapon", "Duchowy oręż", "A", "ultimate", "BBCC", "Przywołaj broń i wykonaj nią atak za 2k8 + MDR. Kolejne aktywacje: D + biała, ruch broni do 20 ft i jeden atak. Najwyżej jedna broń; bez koncentracji.", "O"),
    _a("lorian", "mana_inspiration", "Inspiracja", "D", "basic", "*", "Inny bohater w 30 ft otrzymuje 1k4 do jednego ataku albo obrony, do wcześniejszego wykorzystania.", "T"),
    _a("lorian", "mana_tuning", "Strojenie rynku", "D", "basic", "N", "Po zapłacie odrzuć dodatkową kartę rynku. Dobierz dwie: jedną na rynek, drugą na spód talii. Wymaga dwóch kart talii i dodatkowej karty rynku poza kosztem."),
    _a("lorian", "mocking_shot", "Ostrzał destabilizujący", "A", "basic", "Z*", "Strzał z kuszy. Trafiony wróg ma utrudnienie następnego ataku, do wcześniejszego wykorzystania.", "T"),
    _a("lorian", "cutting_words", "Rozpraszający okrzyk", "R", "basic", "B", "Zmniejsz obrażenia pojedynczego ataku przeciw bohaterowi w 30 ft o 1k6 + CHA, minimum zero."),
    _a("lorian", "mana_recovery", "Odzysk energii", "A", "boost", "B*", "Po zapłacie połóż dwie wybrane karty odrzucone na wierzchu talii, w dowolnej kolejności. Możesz odzyskać właśnie wydany koszt.", "", _b("recover", "N", 3, "Niebieska: kolejna karta na wierzch talii")),
    _a("lorian", "optical_scope", "Luneta optyczna", "A", "boost", "Z*", "Przed ruchem poświęć cały jego limit. Strzał z +2 do trafienia, ignorujący częściową osłonę. Całkowita osłona blokuje.", "", _b("shot", "Z", 1, "Zielona: drugi taki strzał w ten sam cel")),
    _a("lorian", "entangling_shot", "Oplatający ostrzał", "A", "boost", "Z*", "Obszar 3×3, także sojusznicy. Obrona ZRC: porażka połowi ruch, bez obrażeń.", "T", _b("root", "N", 1, "Niebieska: zamiast połowienia blokuje ruch"), _b("area", "Z", 1, "Zielona: obszar 4×4")),
    _a("lorian", "mana_great_tuning", "Wielkie strojenie", "A", "ultimate", "NNNN", "Po zapłacie przenieś trzy wybrane karty z odrzuconych do pustych miejsc rynku. Możesz odzyskać właśnie wydane karty."),
    _a("lorian", "victory_hymn", "Hymn zwycięstwa", "A", "ultimate", "BBNN", "Aura 30 ft, koncentracja. Lorian i sojusznicy mogą wykorzystać jedną dodatkową akcję dodatkową we własnej turze, będąc w aurze. Płać normalnie; wejście i wyjście nie odnawia użycia.", "O"),
    _a("nimra", "nimra_frost_pulse", "Lodowy impuls", "A", "basic", "N", "Cel w 50 ft: obrona KON; porażka 1k8 zimna i −10 ft ruchu, sukces bez efektu.", "T"),
    _a("nimra", "nimra_mind_spike", "Szpilka umysłu", "A", "basic", "F", "Cel w 45 ft: obrona MDR; porażka 1k6 psychicznych i brak reakcji, sukces bez efektu.", "T"),
    _a("nimra", "nimra_sticky_matrix", "Lepka matryca", "A", "basic", "Z*", "Obszar 2×2 w 50 ft: trudny teren. Wejście lub początek tury: obrona ZRC przed powaleniem, najwyżej raz na turę istoty. Najwyżej jedna matryca. Powalenie T lub do wstania.", "O"),
    _a("nimra", "misty_step", "Mglisty krok", "D", "basic", "NZ", "Teleport do 30 ft na legalne, widoczne pole."),
    _a("nimra", "shield", "Tarcza", "R", "basic", "*", "+3 KP przeciw jednemu atakowi i ponowna ocena trafienia."),
    _a("nimra", "nimra_flame_fan", "Wachlarz płomieni", "A", "boost", "C*", "Stożek 15 ft, także sojusznicy. Obrona ZRC: 2k6 ognia, sukces daje połowę.", "", _b("damage", "C", 2, "Czerwona: +1k6 obrażeń"), _b("exclude", "N", 1, "Niebieska: wyłącz dwa wskazane pola")),
    _a("nimra", "nimra_force_wave", "Fala odrzutu", "A", "boost", "N*", "Linia 30×5 ft, także sojusznicy. Obrona SIŁ: 2k6 mocy i odepchnięcie o pole; sukces połowa bez przesunięcia.", "", _b("damage", "C", 2, "Czerwona: +1k6 obrażeń"), _b("push", "N", 1, "Niebieska: dodatkowe pole odepchnięcia")),
    _a("nimra", "nimra_web", "Sieć", "A", "boost", "ZN", "Obszar 2×2 w 50 ft, także sojusznicy: trudny teren i obrona ZRC przed unieruchomieniem. Koncentracja. Uwolnienie: akcja i test SIŁ.", "O", _b("area", "Z", 2, "Zielona: bok większy o jedno pole"), _b("exclude", "N", 1, "Niebieska: wyłącz dwa wskazane pola")),
    _a("nimra", "nimra_mind_break", "Załamanie woli", "A", "boost", "F*", "Cel w 50 ft: obrona MDR, 1k6 psychicznych i brak reakcji (T); sukces połowa bez osłabienia.", "", _b("target", "F", 2, "Czarna: dodatkowy cel w 10 ft od pierwszego"), _b("damage", "C", 1, "Czerwona: +1k6 obrażeń wszystkim celom")),
    _a("nimra", "nimra_lightning_path", "Piorunowy szlak", "A", "ultimate", "CCCN", "Cel w 60 ft, potem do dwóch przeskoków po 15 ft do najbliższej nieporażonej istoty, także sojusznika. 4k6 błyskawic, osobne obrony ZRC, sukces połowa."),
    _a("nimra", "shatter", "Roztrzaskanie", "A", "ultimate", "CCNN", "Środek w 60 ft, promień 10 ft, także sojusznicy. 4k8 grzmotu, obrona KON daje połowę. Konstrukty mają utrudnienie obrony."),
    _a("nimra", "nimra_stasis", "Staza istoty", "A", "ultimate", "NNNF", "Wróg w 50 ft: obrona MDR. Porażka odbiera ruch, akcję główną, dodatkową i reakcję. Koncentracja.", "T"),
    _a("erynd", "hunters_mark", "Znak łowcy", "D", "basic", "Z", "Koncentracja. Raz we własnej turze trafienie oznaczonego celu bronią dodaje 1k6. Przeniesienie po pokonaniu celu bez many i akcji.", "O"),
    _a("erynd", "cunning_action", "Zwiadowcza mobilność", "D", "basic", "Z", "Sprint albo Odstąpienie w bieżącej turze."),
    _a("erynd", "aim", "Celowanie", "D", "basic", "*", "Przed ruchem poświęć cały jego limit: przewaga następnego ataku łukiem w bieżącej turze."),
    _a("erynd", "disrupting_arrow", "Strzała zakłócająca", "A", "basic", "Z*", "Trafienie bronią odbiera reakcje i daje utrudnienie następnego ataku celu.", "T"),
    _a("erynd", "anchoring_arrow", "Strzała kotwicząca", "A", "boost", "Z*", "Trafiony wróg: obrona SIŁ, porażka blokuje ruch, sukces połowi.", "T", _b("shot", "Z", 1, "Zielona: osobny strzał kotwiczący w drugiego wroga sąsiadującego z pierwszym")),
    _a("erynd", "exposing_arrow", "Strzała odsłaniająca", "A", "boost", "Z*", "Trafienie bronią obniża KP celu o 2, bez kumulowania.", "T", _b("damage", "C", 2, "Czerwona: +1k6 obrażeń")),
    _a("erynd", "double_shot", "Podwójny strzał", "A", "boost", "ZC*", "Dwa osobne ataki łukiem, z możliwością różnych celów.", "", _b("damage", "C", 2, "Czerwona: +1k6 do jednego wybranego trafienia")),
    _a("erynd", "arrow_rain", "Deszcz strzał", "A", "ultimate", "ZZZZ", "Wskaż środek obszaru 3×3. Jeden wspólny test łuku przeciw KP każdego legalnego wroga, wspólne 1k8 + 1k6 + ZRC obrażeń. Osłona liczona osobno. Znak i Pierwsza krew najwyżej raz."),
    _a("erynd", "spike_growth", "Kolczaste zarośla", "A", "ultimate", "ZZNN", "Środek w 50 ft, promień 20 ft: trudny teren, koncentracja. 1k4 za przebyte pole, maks. 4k4 na turę istoty; także wymuszony ruch i sojusznicy.", "O"),
)

HOLY_SYMBOL = _a("dagna", "turn_undead", "Święty symbol: Odpędzenie", "A", "item", "BN", "Nieumarli w 15 ft: obrona MDR. Porażka odpędza; obrażenia kończą efekt wcześniej. Osobisty przedmiot Dagny, poza dziewięcioma runami.", "T")


def shared_ability(hero_id: str, ability_id: str) -> SharedAbility | None:
    return next((a for a in (*CATALOG, HOLY_SYMBOL) if a.hero_id == hero_id and a.id == ability_id), None)

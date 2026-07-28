#!/usr/bin/env python3
"""Replace temporary manual spell placeholders with table-assisted contracts.

The assisted path is a real cast: runtime validates access and components,
spends action/slot, tracks concentration and records the result.  These concise
instructions describe only the consequence that still needs physical-table
adjudication.  Straightforward spells can later move to an automatic resolver
without changing character content or spell ids.
"""

from __future__ import annotations

import json
from pathlib import Path


SPELL_DIR = Path("content/spells")

# Polish table instructions, deliberately concise enough for the combat panel.
INSTRUCTIONS: dict[str, str] = {
    "acid_arrow": "Wykonaj dystansowy atak czarem. Trafienie: 4k4 obrażeń od kwasu i 2k4 na końcu następnej tury celu; pudło zadaje połowę początkowych obrażeń.",
    "aid": "Wybierz do 3 istot w zasięgu. Na 8 godzin zwiększ ich aktualne i maksymalne PW o 5; +5 za każdy slot powyżej 2.",
    "alarm": "Wyznacz obszar do 20 stóp. Przez 8 godzin alarm ostrzega mentalnie lub dźwiękiem, gdy nieuprawniona istota wejdzie do obszaru.",
    "alter_self": "Na czas koncentracji wybierz: oddychanie wodą, naturalną broń albo zmianę wyglądu. Zapisz aktywny wariant.",
    "animal_friendship": "Bestia o Inteligencji poniżej 4 wykonuje rzut obronny na Mądrość; porażka oznacza zauroczenie na 24 godziny.",
    "animal_messenger": "Wybierz Tiny beast i miejsce/odbiorcę. Zwierzę podróżuje i przekazuje wiadomość do 25 słów.",
    "arcane_lock": "Dotknięte drzwi, okno, brama lub pojemnik zostają magicznie zamknięte; ustal hasło i zwiększ ST ich sforsowania o 10.",
    "arcanists_magic_aura": "Na 24 godziny ustaw fałszywą aurę szkoły magii lub fałszywy typ istoty dla efektów wykrywania.",
    "augury": "MG losuje omen dla planu z najbliższych 30 minut: dobro, zło, dobro i zło albo nic.",
    "bane": "Do 3 celów wykonuje rzut na Charyzmę. Przy porażce odejmuje k4 od ataków i rzutów obronnych podczas koncentracji.",
    "barkskin": "Podczas koncentracji KP dobrowolnego celu nie może spaść poniżej 16.",
    "bless": "Do 3 sojuszników dodaje k4 do ataków i rzutów obronnych podczas koncentracji; +1 cel za wyższy poziom slotu.",
    "blindness_deafness": "Cel wykonuje rzut na Kondycję. Przy porażce jest Blinded albo Deafened; ponawia rzut na końcu każdej swojej tury.",
    "blur": "Podczas koncentracji ataki przeciw rzucającemu mają utrudnienie, z wyjątkami dla istot niewidzących i truesight.",
    "branding_smite": "Przy następnym trafieniu podczas koncentracji dodaj 2k6 radiant; cel świeci i nie może być niewidzialny. +1k6 za wyższy slot.",
    "calm_emotions": "Humanoidy w kuli 20 stóp wykonują rzut na Charyzmę; stłum emocje albo czasowo usuń zauroczenie/przerażenie.",
    "charm_person": "Humanoid wykonuje rzut na Mądrość (z przewagą podczas walki). Porażka: zauroczenie na godzinę, potem zna fakt zauroczenia.",
    "color_spray": "Rzuć 6k10. Kolejno od celu z najmniejszymi aktualnymi PW istoty w stożku 15 stóp zostają Blinded do końca następnej tury.",
    "command": "Cel rozumiejący język wykonuje rzut na Mądrość. Porażka: w następnej turze wykonuje jednowyrazowy rozkaz; +1 cel za wyższy slot.",
    "continual_flame": "Dotknięty obiekt emituje światło jak pochodnia, bez ciepła i zużycia paliwa, dopóki efekt nie zostanie rozproszony.",
    "create_or_destroy_water": "Stwórz albo zniszcz do 10 galonów wody; alternatywnie utwórz deszcz lub usuń mgłę w sześcianie 30 stóp.",
    "darkness": "Kula magicznej ciemności o promieniu 15 stóp blokuje zwykłe darkvision podczas koncentracji; zasłoń odpowiedni obszar planszy.",
    "darkvision": "Dotknięta istota otrzymuje darkvision 60 stóp na 8 godzin.",
    "detect_evil_and_good": "Podczas koncentracji wykrywaj aberracje, celestial, elemental, fey, fiend i undead oraz poświęcone/sprofanowane miejsca w 30 stopach.",
    "detect_magic": "Podczas koncentracji wykrywaj magię w 30 stopach; akcja ujawnia aurę i szkołę widocznego źródła.",
    "detect_poison_and_disease": "Podczas koncentracji wykrywaj i identyfikuj trucizny, jadowite istoty oraz choroby w 30 stopach.",
    "detect_thoughts": "Podczas koncentracji czytaj powierzchowne myśli albo sonduj głębiej; cel broni się rzutem na Mądrość i może wykonać contest Inteligencji.",
    "disguise_self": "Na godzinę zmień pozorny wygląd i wyposażenie. Fizyczna inspekcja ujawnia iluzję; Investigation przeciw ST czaru rozpoznaje ją.",
    "divine_favor": "Podczas koncentracji twoje trafienia bronią zadają dodatkowe 1k4 radiant.",
    "enhance_ability": "Wybierz cechę celu: przewaga w jej testach i właściwy efekt dodatkowy; trwa podczas koncentracji.",
    "enlarge_reduce": "Cel wykonuje rzut na Kondycję, jeśli niechętny. Zmień rozmiar o kategorię oraz obrażenia broni o 1k4 podczas koncentracji.",
    "entangle": "Obszar 20 stóp staje się trudnym terenem. Istoty wykonują rzut na Siłę; porażka daje Restrained, uwolnienie wymaga akcji i testu Siły.",
    "enthrall": "Wybrane istoty wykonują rzut na Mądrość; porażka daje utrudnienie Perception dotyczącego innych niż rzucający przez minutę.",
    "expeditious_retreat": "Po rzuceniu i w każdej swojej turze podczas koncentracji możesz użyć Dash jako bonus action.",
    "faerie_fire": "Istoty w sześcianie 20 stóp wykonują rzut na Zręczność; porażka: świecą, nie korzystają z niewidzialności, ataki na nie mają przewagę.",
    "false_life": "Otrzymujesz 1k4+4 tymczasowych PW na godzinę; +5 za każdy wyższy poziom slotu.",
    "feather_fall": "Reakcja na upadek: do 5 spadających istot opada 60 stóp na rundę i nie otrzymuje obrażeń, jeśli wyląduje przed końcem minuty.",
    "find_familiar": "Po godzinie przywołaj ducha w formie wybranej Tiny beast. Zapisz formę, statblock, więź telepatyczną i możliwość dostarczania czarów dotykowych.",
    "find_steed": "Po 10 minutach przywołaj inteligentnego lojalnego wierzchowca; wybierz formę i ustaw jego osobny statblock.",
    "find_traps": "MG potwierdza obecność pułapki w linii widzenia do 120 stóp i ogólny rodzaj zagrożenia, ale nie wskazuje miejsca.",
    "flame_blade": "Podczas koncentracji tworzysz ogniste ostrze; melee spell attack zadaje 3k6 fire. +1k6 za każde dwa poziomy slotu powyżej 2.",
    "flaming_sphere": "Ustaw kulę na wolnym polu. Istoty kończące turę obok niej bronią się Dex przed 2k6 fire; bonus action przesuwa kulę do 30 stóp.",
    "floating_disk": "Na godzinę utwórz dysk podążający 20 stóp za tobą i przenoszący do 500 funtów; znika po oddaleniu ponad 100 stóp.",
    "fog_cloud": "Utwórz silnie zasłoniętą kulę mgły o promieniu 20 stóp podczas koncentracji; promień +20 stóp za wyższy slot.",
    "gentle_repose": "Dotknięte zwłoki przez 10 dni nie rozkładają się i nie mogą stać się undead; czas nie liczy się do limitu wskrzeszenia.",
    "goodberry": "Powstaje 10 jagód na 24 godziny. Akcja zjedzenia leczy 1 PW i zapewnia dzienne wyżywienie.",
    "grease": "Kwadrat 10 stóp staje się trudnym terenem na minutę. Istoty wchodzące lub kończące tam turę wykonują Dex save albo padają Prone.",
    "guiding_bolt": "Wykonaj dystansowy atak czarem: 4k6 radiant; następny atak przeciw celowi przed końcem twojej następnej tury ma przewagę.",
    "gust_of_wind": "Linia 60×10 stóp podczas koncentracji odpycha o 15 stóp po nieudanym Str save, kosztuje podwójny ruch pod wiatr i rozprasza gazy.",
    "heat_metal": "Metalowy obiekt zadaje 2k8 fire; noszący wykonuje Con save albo go upuszcza. Bonus action powtarza obrażenia podczas koncentracji.",
    "hellish_rebuke": "Reakcja po otrzymaniu obrażeń: sprawca wykonuje Dex save; otrzymuje 2k10 fire, połowę przy sukcesie. +1k10 za wyższy slot.",
    "heroism": "Dobrowolny cel jest odporny na Frightened i na początku każdej tury dostaje tymczasowe PW równe modyfikatorowi cechy rzucania.",
    "hideous_laughter": "Cel Int 4+ wykonuje Wis save; porażka: Prone i Incapacitated podczas koncentracji, ponawia save po obrażeniach i na końcu tury.",
    "hold_person": "Humanoid wykonuje Wis save; porażka: Paralyzed podczas koncentracji, ponawia save na końcu tury. +1 cel za wyższy slot.",
    "hunters_mark": "Oznacz cel podczas koncentracji: +1k6 do twoich trafień bronią i przewaga w Perception/Survival do odnalezienia go; przenieś znak po jego pokonaniu.",
    "identify": "Po minucie dotykania obiektu poznaj jego właściwości magiczne, użycie, attunement, ładunki i działające na nim czary.",
    "illusory_script": "Zapis wygląda przez 10 dni jak inna wiadomość lub nieznany magiczny tekst dla osób niewskazanych podczas rzucania.",
    "invisibility": "Cel i noszone przez niego przedmioty są Invisible podczas koncentracji do godziny; efekt kończy się po ataku lub rzuceniu czaru.",
    "jump": "Przez minutę potrój dystans skoku dotkniętej istoty, nadal ograniczony dostępnym ruchem.",
    "knock": "Wybrany zamek, rygiel albo blokada w 60 stopach otwiera się; Arcane Lock jest tłumiony na 10 minut, a dźwięk słychać z 300 stóp.",
    "lesser_restoration": "Dotknięta istota kończy jedną chorobę albo jeden stan: Blinded, Deafened, Paralyzed lub Poisoned.",
    "levitate": "Cel do 500 funtów wykonuje Con save, jeśli niechętny. Podczas koncentracji unosi się do 20 stóp i porusza tylko przez odpychanie.",
    "locate_animals_or_plants": "Opisz znany gatunek; poznaj kierunek i dystans do najbliższego okazu w promieniu 5 mil, jeśli istnieje.",
    "locate_object": "Podczas koncentracji poznawaj kierunek do znanego obiektu w promieniu 1000 stóp, o ile nie blokuje go ołów.",
    "longstrider": "Przez godzinę szybkość dotkniętego celu rośnie o 10 stóp; +1 cel za wyższy slot.",
    "mage_armor": "Nieopancerzony, chętny cel ma bazowe KP 13 + modyfikator Zręczności przez 8 godzin.",
    "magic_missile": "Trzy pociski automatycznie trafiają widoczne cele w 120 stopach; każdy zadaje 1k4+1 force. +1 pocisk za wyższy slot.",
    "magic_mouth": "Ustal wyzwalacz i wiadomość do 25 słów; zaczarowany obiekt odtwarza ją po spełnieniu warunku.",
    "magic_weapon": "Niemagiczna broń podczas koncentracji staje się magiczna i otrzymuje +1 do ataku i obrażeń.",
    "mirror_image": "Powstają 3 duplikaty. Przy ataku na ciebie rzuć k20, by ustalić trafienie duplikatu; duplikat ma KP 10 + Dex i znika po trafieniu.",
    "misty_step": "Teleportuj się jako bonus action na widoczne wolne pole w zasięgu 30 stóp.",
    "moonbeam": "Ustaw cylinder 5 stóp promienia. Wejście/start tury: Con save przeciw 2k10 radiant, połowa przy sukcesie; akcja przesuwa wiązkę 60 stóp.",
    "pass_without_trace": "Podczas koncentracji wybrane istoty w 30 stopach mają +10 do Stealth, nie zostawiają śladów i nie można ich śledzić niemagicznie.",
    "prayer_of_healing": "Po 10 minutach do 6 istot w 30 stopach odzyskuje 2k8 + modyfikator cechy rzucania PW; +1k8 za wyższy slot.",
    "protection_from_evil_and_good": "Podczas koncentracji aberracje, celestial, elemental, fey, fiend i undead mają utrudnienie ataków na cel i nie mogą go zauroczyć, przerazić ani opętać.",
    "protection_from_poison": "Zneutralizuj jedną truciznę; przez godzinę cel ma przewagę save przeciw poison i odporność na obrażenia poison.",
    "purify_food_and_drink": "Niemagiczne jedzenie i napoje w promieniu 5 stóp zostają oczyszczone z trucizn i chorób.",
    "ray_of_enfeeblement": "Ranged spell attack; podczas koncentracji cel zadaje połowę obrażeń atakami broni opartymi na Sile i ponawia Con save na końcu tury.",
    "rope_trick": "Lina do 60 stóp prowadzi przez godzinę do extradimensional space dla maksymalnie 8 Medium istot; wejście staje się niewidoczne po wciągnięciu liny.",
    "sanctuary": "Do minuty napastnik atakujący lub celujący szkodliwym czarem wykonuje Wis save albo wybiera inny cel; efekt kończy ofensywna akcja chronionego.",
    "scorching_ray": "Wykonaj 3 osobne dystansowe ataki czarem; każdy trafiony promień zadaje 2k6 fire. +1 promień za wyższy slot.",
    "see_invisibility": "Przez godzinę widzisz niewidzialne istoty i obiekty oraz obszary Ethereal Plane w zasięgu wzroku.",
    "shatter": "Istoty w promieniu 10 stóp wykonują Con save; 3k8 thunder, połowa przy sukcesie. Constructy mają utrudnienie, niemagiczne obiekty też otrzymują obrażenia.",
    "shield_of_faith": "Wybrana istota otrzymuje +2 KP podczas koncentracji do 10 minut.",
    "silence": "Podczas koncentracji kula 20 stóp nie przepuszcza dźwięku; istoty są Deafened i nie można rzucać czarów z komponentem werbalnym.",
    "silent_image": "Utwórz wizualną iluzję w sześcianie 15 stóp; akcja ją przesuwa. Fizyczna interakcja lub Investigation przeciw ST ujawnia iluzję.",
    "sleep": "Rzuć 5k8 PW. Od istoty z najmniejszą liczbą aktualnych PW usypiaj cele w promieniu 20 stóp do wyczerpania puli.",
    "speak_with_animals": "Przez 10 minut możesz komunikować się werbalnie z bestiami i uzyskiwać proste informacje.",
    "spider_climb": "Podczas koncentracji cel zyskuje climb speed równą szybkości i może chodzić po ścianach oraz suficie bez użycia rąk.",
    "spike_growth": "Obszar promienia 20 stóp jest trudnym terenem; każde 5 stóp ruchu zadaje 2k4 piercing. Nierozpoznany efekt jest zakamuflowany.",
    "spiritual_weapon": "Utwórz broń w 60 stopach i wykonaj melee spell attack za 1k8 + modyfikator cechy force; bonus action przesuwa ją 20 stóp i atakuje ponownie.",
    "suggestion": "Cel rozumiejący język wykonuje Wis save. Porażka: realizuje rozsądnie brzmiącą sugestię podczas koncentracji do 8 godzin.",
    "thunderwave": "Istoty w sześcianie 15 stóp wykonują Con save; 2k8 thunder i odepchnięcie 10 stóp, połowa bez odepchnięcia przy sukcesie.",
    "unseen_servant": "Na godzinę powstaje niewidzialny sługa o KP 10 i 1 PW; bonus action wydaje mu polecenie prostego zadania w 15 stopach.",
    "warding_bond": "Przez godzinę, gdy cel jest w 60 stopach, ma +1 KP i save oraz odporność na wszystkie obrażenia; rzucający otrzymuje tyle samo obrażeń.",
    "web": "Sześcian 20 stóp jest lekkim zasłonięciem i trudnym terenem. Wchodzący/startujący wykonują Dex save albo Restrained; akcja Str uwalnia.",
    "zone_of_truth": "Istoty w promieniu 15 stóp wykonują Cha save. Przy porażce przez 10 minut nie mogą świadomie kłamać; rzucający zna wyniki save.",
}


def main() -> None:
    updated = 0
    unresolved: list[str] = []
    for path in sorted(SPELL_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        effect = data.get("effect", {})
        if effect.get("kind") != "manual":
            continue
        spell_id = str(data["id"])
        instructions = INSTRUCTIONS.get(spell_id)
        if instructions is None:
            unresolved.append(spell_id)
            continue
        data["effect"] = {
            "kind": "assisted",
            "action_type": "assisted_spell",
            "instructions": instructions,
            "resolution_mode": (
                "narrative"
                if spell_id in {
                    "animal_messenger",
                    "arcanists_magic_aura",
                    "augury",
                    "detect_thoughts",
                    "identify",
                    "illusory_script",
                    "locate_animals_or_plants",
                    "locate_object",
                    "magic_mouth",
                    "speak_with_animals",
                    "suggestion",
                }
                else "tabletop"
            ),
            "board_relevance": (
                "indirect"
                if spell_id in {
                    "alarm",
                    "animal_friendship",
                    "animal_messenger",
                    "arcane_lock",
                    "arcanists_magic_aura",
                    "augury",
                    "continual_flame",
                    "detect_evil_and_good",
                    "detect_magic",
                    "detect_poison_and_disease",
                    "detect_thoughts",
                    "disguise_self",
                    "find_traps",
                    "gentle_repose",
                    "identify",
                    "illusory_script",
                    "locate_animals_or_plants",
                    "locate_object",
                    "magic_mouth",
                    "purify_food_and_drink",
                    "speak_with_animals",
                }
                else "direct"
            ),
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        updated += 1
    if unresolved:
        raise SystemExit(f"Missing assisted instructions: {', '.join(unresolved)}")
    print(f"Materialized {updated} assisted spell contracts.")


if __name__ == "__main__":
    main()

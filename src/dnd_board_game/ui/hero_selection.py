"""Editorial guidance for choosing the current seven board-game heroes.

These summaries describe play style, not rules or a ranking of hero strength.
Keep them aligned with boardgame_profiles and the keyboard character sheets.
"""

from dataclasses import dataclass

from dnd_board_game.character_creation.boardgame_help import HERO_FLAWS


@dataclass(frozen=True, slots=True)
class HeroSelectionGuide:
    role: str
    complexity: str
    complexity_reason: str
    play_style: str
    abilities: tuple[str, ...]
    flaw: str


HERO_SELECTION_GUIDES: dict[str, HeroSelectionGuide] = {
    "garran": HeroSelectionGuide(
        role="Obrona i dowodzenie",
        complexity="Przystępna",
        complexity_reason="Czytelny plan: utrzymaj pozycję i wybierz, kogo osłonić.",
        play_style="Stań na pierwszej linii. Mieczem i tarczą zatrzymuj wrogów, a rozkazami wspieraj drużynę.",
        abilities=(
            "Pozycja obronna — poświęć ruch, aby zwiększyć swoją obronę.",
            "Osłona towarzysza — przejmij pierwszy pojedynczy atak lub efekt wymierzony w wybranego sojusznika.",
            "Drugi oddech i Zryw akcji — odzyskaj siły albo wykonaj dodatkową akcję w ważnym momencie.",
        ),
        flaw=HERO_FLAWS['garran'].body,
    ),
    "brakka": HeroSelectionGuide(
        role="Natarcie i wytrzymałość",
        complexity="Przystępna",
        complexity_reason="Prosty cel w zwarciu; pilnuj Szału, Dzikości i ryzyka odwetu.",
        play_style="Wejdź w zwarcie i naciskaj toporem. Szał pomaga przetrwać, a Dzikość wzmacnia najważniejsze zagrania.",
        abilities=(
            "Szał — zwiększ obrażenia wręcz, zyskaj odporności i pulę Dzikości.",
            "Lekkomyślny atak — łatwiej trafisz, ale przeciwnikom też będzie łatwiej trafić ciebie.",
            "Twarda jak skała — wydaj Dzikość na reakcję zmniejszającą otrzymane obrażenia.",
        ),
        flaw=HERO_FLAWS['brakka'].body,
    ),
    "mira": HeroSelectionGuide(
        role="Ukrycie i precyzyjne ataki",
        complexity="Wymagająca",
        complexity_reason="Planuj flankowanie, drogę odwrotu i to, którzy wrogowie cię widzą.",
        play_style="Obchodź wrogów i uderzaj z ukrycia. Dobra pozycja daje mocny atak, lecz zdemaskowanie zwiększa ryzyko.",
        abilities=(
            "Ukrycie — wykorzystaj obserwację przeciwników i pozycję, aby przygotować silniejszy atak.",
            "Zasłona dymna — przemieść się bez ataków okazyjnych i spróbuj się ukryć nawet obok wroga.",
            "Cięcie ścięgna — wydaj Fortel podczas flankowania, by po trafieniu spowolnić przeciwnika.",
        ),
        flaw=HERO_FLAWS['mira'].body,
    ),
    "dagna": HeroSelectionGuide(
        role="Leczenie i ochrona drużyny",
        complexity="Umiarkowana",
        complexity_reason="Wybieraj między leczeniem a wsparciem i pilnuj zasięgu aury oraz koncentracji.",
        play_style="Poruszaj się blisko drużyny. Wzmacniaj sojuszników aurami i docieraj do rannych, zanim stracą kolejną turę.",
        abilities=(
            "Słowo leczenia — przywróć sojusznikowi punkty wytrzymałości na odległość.",
            "Błogosławieństwo — ruchoma aura wspiera ataki i rzuty obronne pobliskich sojuszników.",
            "Duchowa broń — przywołaj osobną broń na planszy, aby atakować i pomagać we flankowaniu.",
        ),
        flaw=HERO_FLAWS['dagna'].body,
    ),
    "lorian": HeroSelectionGuide(
        role="Ostrzał i wsparcie taktyczne",
        complexity="Wymagająca",
        complexity_reason="Łącz techniki kuszy, Inspirację i reakcje; pilnuj bliskości sojusznika.",
        play_style="Strzelaj z kuszy i utrudniaj wrogom działanie. Inspiruj drużynę, a poza walką wykorzystuj talent do rozmów.",
        abilities=(
            "Luneta optyczna — poświęć ruch na dwa precyzyjne strzały w jeden cel.",
            "Inspiracja bardowska — daj sojusznikowi dodatkową kość do ważnego rzutu.",
            "Oplatający ostrzał — ogranicz ruch w wybranym obszarze; uważaj też na sojuszników.",
        ),
        flaw=HERO_FLAWS['lorian'].body,
    ),
    "nimra": HeroSelectionGuide(
        role="Magia i kontrola obszaru",
        complexity="Wymagająca",
        complexity_reason="Wybieraj czar, Metamagię i obszar; pamiętaj o poprzedniej rundzie oraz sojusznikach.",
        play_style="Spowalniaj grupy wrogów i zmieniaj pole walki. Dopasowuj czary Metamagią, dbając o bezpieczeństwo drużyny.",
        abilities=(
            "Metamagia — zmień zasięg, obrażenia lub inne właściwości wybranego czaru.",
            "Rzeźbienie pola — wyklucz wybrane pola z obszaru czaru, aby oszczędzić sojuszników.",
            "Piorunowy szlak — łańcuch błyskawic przeskakuje do najbliższych istot, również sojuszników.",
        ),
        flaw=HERO_FLAWS['nimra'].body,
    ),
    "erynd": HeroSelectionGuide(
        role="Mobilny ostrzał i kontrola",
        complexity="Umiarkowana",
        complexity_reason="Wybieraj między ruchem a celowaniem i oszczędzaj Instynkt na ważne strzały.",
        play_style="Utrzymuj dystans długim łukiem. Oznaczaj cele, odbieraj im swobodę ruchu i zmieniaj pozycję, gdy wróg się zbliża.",
        abilities=(
            "Znak łowcy — zwiększ obrażenia przeciw wybranemu wrogowi; po jego pokonaniu przenieś oznaczenie.",
            "Celowanie — poświęć ruch, aby ułatwić następny atak długim łukiem.",
            "Strzała kotwicząca i Zwiadowcza mobilność — ogranicz ruch wroga albo oddal się od zagrożenia.",
        ),
        flaw=HERO_FLAWS['erynd'].body,
    ),
}

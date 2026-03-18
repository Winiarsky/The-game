from __future__ import annotations

from dataclasses import dataclass

from localization import localize_term_pl
from statuses.base import Status
from statuses.backgrounds.skill_feats import SKILL_FEAT_STATUS_BY_ID
from statuses.general.assurance import ASSURANCE_STATUS
from statuses.general.dubious_knowledge import DUBIOUS_KNOWLEDGE_STATUS

BACKGROUND_CORE_RULES_UI = (
    "Na 1. poziomie wybierasz jeden background i tej decyzji nie zmieniasz później. "
    "Każdy background daje dwa boosty cech (jeden ograniczony, jeden dowolny), "
    "trained w jednym skillu i jednym Lore oraz jeden skill feat. "
    "W tym silniku boosty cech i szkolenia skill/Lore są informacją UI, "
    "a feat z backgroundu jest dodawany do bohatera jako realny status."
)


@dataclass(frozen=True)
class BackgroundDefinition:
    key: str
    label: str
    description: str
    ability_boosts_ui: str
    skill_training_ui: str
    feat_id: str | None
    choice_kind: str | None = None
    extra_data: dict[str, object] | None = None


_FEAT_BY_ID: dict[str, Status] = dict(SKILL_FEAT_STATUS_BY_ID)
_FEAT_BY_ID.update(
    {
        "assurance": ASSURANCE_STATUS,
        "dubious_knowledge": DUBIOUS_KNOWLEDGE_STATUS,
    }
)

_BACKGROUND_DESCRIPTION_PL: dict[str, str] = {
    "acolyte": "Dorastales w klasztorze lub przybytku wiary i niesiesz te nauki w swiat.",
    "acrobat": "Zarabiales wystepami cyrkowymi lub ulicznymi, uczac sie zwinnego ruchu.",
    "animal_whisperer": "Masz naturalna wiez ze zwierzetami i potrafisz je szkolic.",
    "artisan": "Byles czeladnikiem rzemiosla i rozwineles praktyczna specjalizacje.",
    "artist": "Sztuka to twoja pasja, a przygoda stala sie droga do inspiracji lub utrzymania.",
    "barkeep": "Pracowales w karczmie, uczac sie kontaktu z ludzmi i trudnymi klientami.",
    "barrister": "Szkolenie prawnicze i praktyka w sali sadowej nauczyly cie argumentacji.",
    "bounty_hunter": "Scigales przestepcow dla sprawiedliwosci, zlota lub obu tych rzeczy.",
    "charlatan": "Zylas z oszustw i falszywych tozsamosci, az staly sie druga natura.",
    "criminal": "Przetrwales dzieki przestepczemu fachowi, samotnie lub w organizacji.",
    "detective": "Rozwiazywales sprawy i wypracowales oko do ukrytych powiazan.",
    "emissary": "Byles poslem lub dyplomata, podrozujac i budujac sojusze.",
    "entertainer": "Trenowales wystepy sceniczne i umiesz skupic na sobie uwage tlumu.",
    "farmhand": "Ciezka praca na roli zahartowala cialo i nauczyla dyscypliny.",
    "field_medic": "Nauczyles sie ratowac rannych pod presja pola walki.",
    "fortune_teller": "Praktykowales sztuke wrozenia i otarles sie o tajemnice okultyzmu.",
    "gambler": "Hazard wyrobil w tobie instynkt ryzyka i czytania ludzi.",
    "gladiator": "Arena nauczyla cie walczyc i jednoczesnie grac pod publike.",
    "guard": "Sluzba straznicza nauczyla cie porzadku i praktycznego nacisku.",
    "herbalist": "Poznales ziola, lekarstwa i naturalne metody leczenia.",
    "hermit": "Zyles w odosobnieniu i rozwineles nietypowa, praktyczna wiedze.",
    "hunter": "Tropienie i pozyskiwanie zwierzyny przygotowalo cie do wypraw.",
    "laborer": "Lata ciezkiej pracy fizycznej zbudowaly wytrzymalosc i sile.",
    "martial_disciple": "Przeszedles rygorystyczne szkolenie bojowe w formalnej szkole walki.",
    "merchant": "Handel i negocjacje nauczyly cie oceny wartosci pod presja czasu.",
    "miner": "Pracowales pod ziemia w trudnych warunkach i poznales realia podziemi.",
    "noble": "Dworskie zycie nauczylo cie etykiety, wplywow i ostroznosci politycznej.",
    "nomad": "Ciagle podroze nauczyly cie przetrwania przy ograniczonych zasobach.",
    "prisoner": "Niewola zahartowala cie i nauczyla skrytosci oraz przetrwania.",
    "sailor": "Morze wytrenowalo twoje cialo i odruchy do ciezkich warunkow.",
    "scholar": "Poswieciles sie nauce i wyruszyles sprawdzic wiedze w prawdziwym swiecie.",
    "scout": "Prowadziles innych przez dzicz i opanowales terenowa praktyke.",
    "street_urchin": "Przetrwales na ulicy dzieki ostroznosci, szybkosci i sprytowi.",
    "tinker": "Tworzyles i naprawiales urzadzenia, stale szukajac praktycznych rozwiazan.",
    "warrior": "Walczyles w milicji, armii albo kompanii najemnej przed zyciem awanturnika.",
}

_BACKGROUND_UI_TRANSLATIONS: dict[str, str] = {
    "One boost to Constitution or Charisma, and one free boost.": "Jeden boost do Kondycji lub Charyzmy oraz jeden dowolny boost.",
    "One boost to Constitution or Intelligence, and one free boost.": "Jeden boost do Kondycji lub Inteligencji oraz jeden dowolny boost.",
    "One boost to Constitution or Wisdom, and one free boost.": "Jeden boost do Kondycji lub Madrosci oraz jeden dowolny boost.",
    "One boost to Dexterity or Charisma, and one free boost.": "Jeden boost do Zrecznosci lub Charyzmy oraz jeden dowolny boost.",
    "One boost to Dexterity or Constitution, and one free boost.": "Jeden boost do Zrecznosci lub Kondycji oraz jeden dowolny boost.",
    "One boost to Dexterity or Intelligence, and one free boost.": "Jeden boost do Zrecznosci lub Inteligencji oraz jeden dowolny boost.",
    "One boost to Dexterity or Wisdom, and one free boost.": "Jeden boost do Zrecznosci lub Madrosci oraz jeden dowolny boost.",
    "One boost to Intelligence or Charisma, and one free boost.": "Jeden boost do Inteligencji lub Charyzmy oraz jeden dowolny boost.",
    "One boost to Intelligence or Wisdom, and one free boost.": "Jeden boost do Inteligencji lub Madrosci oraz jeden dowolny boost.",
    "One boost to Strength or Charisma, and one free boost.": "Jeden boost do Sily lub Charyzmy oraz jeden dowolny boost.",
    "One boost to Strength or Constitution, and one free boost.": "Jeden boost do Sily lub Kondycji oraz jeden dowolny boost.",
    "One boost to Strength or Dexterity, and one free boost.": "Jeden boost do Sily lub Zrecznosci oraz jeden dowolny boost.",
    "One boost to Strength or Intelligence, and one free boost.": "Jeden boost do Sily lub Inteligencji oraz jeden dowolny boost.",
    "One boost to Strength or Wisdom, and one free boost.": "Jeden boost do Sily lub Madrosci oraz jeden dowolny boost.",
    "One boost to Wisdom or Charisma, and one free boost.": "Jeden boost do Madrosci lub Charyzmy oraz jeden dowolny boost.",
    "Acrobatics and Circus Lore.": "Akrobatyka oraz Wiedza: Cyrk.",
    "Athletics and Farming Lore.": "Atletyka oraz Wiedza: Rolnictwo.",
    "Athletics and Labor Lore.": "Atletyka oraz Wiedza: Praca fizyczna.",
    "Athletics and Sailing Lore.": "Atletyka oraz Wiedza: Zeglarstwo.",
    "Choose Acrobatics or Athletics, plus Warfare Lore.": "Wybierz Akrobatyke albo Atletyke oraz Wiedza: Wojna.",
    "Choose Arcana, Nature, Occultism, or Religion; plus Academia Lore.": "Wybierz Arkana, Nature, Okultyzm albo Religie; dodatkowo Wiedza: Akademia.",
    "Crafting and Art Lore.": "Rzemioslo oraz Wiedza: Sztuka.",
    "Crafting and Engineering Lore.": "Rzemioslo oraz Wiedza: Inzynieria.",
    "Crafting and Guild Lore.": "Rzemioslo oraz Wiedza: Gildia.",
    "Deception and Games Lore.": "Oszustwo oraz Wiedza: Gry.",
    "Deception and Underworld Lore.": "Oszustwo oraz Wiedza: Podziemie.",
    "Diplomacy and Alcohol Lore.": "Dyplomacja oraz Wiedza: Alkohol.",
    "Diplomacy and Legal Lore.": "Dyplomacja oraz Wiedza: Prawo.",
    "Diplomacy and Mercantile Lore.": "Dyplomacja oraz Wiedza: Handel.",
    "Intimidation and Legal Lore or Warfare Lore.": "Zastraszanie oraz Wiedza: Prawo lub Wiedza: Wojna.",
    "Intimidation and Warfare Lore.": "Zastraszanie oraz Wiedza: Wojna.",
    "Medicine and Warfare Lore.": "Medycyna oraz Wiedza: Wojna.",
    "Nature and Herbalism Lore.": "Natura oraz Wiedza: Zielarstwo.",
    "Nature and one terrain Lore connected to animals you favor.": "Natura oraz jeden terenowy Lore zwiazany z ulubionymi zwierzetami.",
    "Nature or Occultism, plus one terrain Lore tied to your refuge.": "Natura albo Okultyzm oraz jeden terenowy Lore zwiazany z twoim schronieniem.",
    "Occultism and Fortune-Telling Lore.": "Okultyzm oraz Wiedza: Wrozenie.",
    "Performance and Gladiatorial Lore.": "Wystepy oraz Wiedza: Gladiatorstwo.",
    "Performance and Theater Lore.": "Wystepy oraz Wiedza: Teatr.",
    "Religion and Scribing Lore.": "Religia oraz Wiedza: Skryba.",
    "Society and Genealogy Lore or Heraldry Lore.": "Spoleczenstwo oraz Wiedza: Genealogia lub Wiedza: Heraldyka.",
    "Society and Underworld Lore.": "Spoleczenstwo oraz Wiedza: Podziemie.",
    "Society and one city Lore you know well.": "Spoleczenstwo oraz jeden miejski Lore, ktory dobrze znasz.",
    "Stealth and Underworld Lore.": "Skradanie oraz Wiedza: Podziemie.",
    "Survival and Legal Lore.": "Przetrwanie oraz Wiedza: Prawo.",
    "Survival and Mining Lore.": "Przetrwanie oraz Wiedza: Gornictwo.",
    "Survival and Tanning Lore.": "Przetrwanie oraz Wiedza: Garbarstwo.",
    "Survival and one terrain Lore from your journeys.": "Przetrwanie oraz jeden terenowy Lore z twoich podrozy.",
    "Survival and one terrain Lore from your scouting work.": "Przetrwanie oraz jeden terenowy Lore ze zwiadu.",
    "Thievery and one city Lore from your home city.": "Zlodziejstwo oraz jeden miejski Lore z rodzinnego miasta.",
}


BACKGROUND_DEFINITIONS: list[BackgroundDefinition] = [
    BackgroundDefinition(
        key="acolyte",
        label="Acolyte",
        description=(
            "You spent your early days in a monastery or cloister and carry those teachings with you."
        ),
        ability_boosts_ui="One boost to Intelligence or Wisdom, and one free boost.",
        skill_training_ui="Religion and Scribing Lore.",
        feat_id="student_of_the_canon",
    ),
    BackgroundDefinition(
        key="acrobat",
        label="Acrobat",
        description=(
            "You performed in a circus or on the streets and learned to survive through agility."
        ),
        ability_boosts_ui="One boost to Strength or Dexterity, and one free boost.",
        skill_training_ui="Acrobatics and Circus Lore.",
        feat_id="steady_balance",
    ),
    BackgroundDefinition(
        key="animal_whisperer",
        label="Animal Whisperer",
        description=(
            "You have a deep connection with animals and learned to communicate and train them."
        ),
        ability_boosts_ui="One boost to Wisdom or Charisma, and one free boost.",
        skill_training_ui="Nature and one terrain Lore connected to animals you favor.",
        feat_id="train_animal",
    ),
    BackgroundDefinition(
        key="artisan",
        label="Artisan",
        description=(
            "You trained as a craft apprentice and developed practical expertise."
        ),
        ability_boosts_ui="One boost to Strength or Intelligence, and one free boost.",
        skill_training_ui="Crafting and Guild Lore.",
        feat_id="specialty_crafting",
    ),
    BackgroundDefinition(
        key="artist",
        label="Artist",
        description=(
            "Your art is your calling, and adventuring became your path to inspiration or survival."
        ),
        ability_boosts_ui="One boost to Dexterity or Charisma, and one free boost.",
        skill_training_ui="Crafting and Art Lore.",
        feat_id="specialty_crafting",
    ),
    BackgroundDefinition(
        key="barkeep",
        label="Barkeep",
        description=(
            "You worked in taverns, learned hard social lessons, and can handle rowdy crowds."
        ),
        ability_boosts_ui="One boost to Constitution or Charisma, and one free boost.",
        skill_training_ui="Diplomacy and Alcohol Lore.",
        feat_id="hobnobber",
    ),
    BackgroundDefinition(
        key="barrister",
        label="Barrister",
        description=(
            "Legal studies and courtroom practice taught you how to argue and navigate law."
        ),
        ability_boosts_ui="One boost to Intelligence or Charisma, and one free boost.",
        skill_training_ui="Diplomacy and Legal Lore.",
        feat_id="group_impression",
    ),
    BackgroundDefinition(
        key="bounty_hunter",
        label="Bounty Hunter",
        description=(
            "You tracked fugitives for justice, coin, or both, and learned to read criminal trails."
        ),
        ability_boosts_ui="One boost to Strength or Wisdom, and one free boost.",
        skill_training_ui="Survival and Legal Lore.",
        feat_id="experienced_tracker",
    ),
    BackgroundDefinition(
        key="charlatan",
        label="Charlatan",
        description=(
            "You traveled with fake identities and confidence tricks until the mask became second nature."
        ),
        ability_boosts_ui="One boost to Intelligence or Charisma, and one free boost.",
        skill_training_ui="Deception and Underworld Lore.",
        feat_id="charming_liar",
    ),
    BackgroundDefinition(
        key="criminal",
        label="Criminal",
        description=(
            "You survived through crime, either alone or in an organization."
        ),
        ability_boosts_ui="One boost to Dexterity or Intelligence, and one free boost.",
        skill_training_ui="Stealth and Underworld Lore.",
        feat_id="experienced_smuggler",
    ),
    BackgroundDefinition(
        key="detective",
        label="Detective",
        description=(
            "You solved cases as an investigator and developed an eye for hidden links."
        ),
        ability_boosts_ui="One boost to Intelligence or Wisdom, and one free boost.",
        skill_training_ui="Society and Underworld Lore.",
        feat_id="streetwise",
    ),
    BackgroundDefinition(
        key="emissary",
        label="Emissary",
        description=(
            "You served as diplomat or messenger, traveling and building connections."
        ),
        ability_boosts_ui="One boost to Intelligence or Charisma, and one free boost.",
        skill_training_ui="Society and one city Lore you know well.",
        feat_id="multilingual",
    ),
    BackgroundDefinition(
        key="entertainer",
        label="Entertainer",
        description=(
            "You trained to perform for crowds and learned how to command attention."
        ),
        ability_boosts_ui="One boost to Dexterity or Charisma, and one free boost.",
        skill_training_ui="Performance and Theater Lore.",
        feat_id="fascinating_performance",
    ),
    BackgroundDefinition(
        key="farmhand",
        label="Farmhand",
        description=(
            "Long days of agricultural labor built endurance and practical discipline."
        ),
        ability_boosts_ui="One boost to Constitution or Wisdom, and one free boost.",
        skill_training_ui="Athletics and Farming Lore.",
        feat_id="assurance",
    ),
    BackgroundDefinition(
        key="field_medic",
        label="Field Medic",
        description=(
            "You learned emergency treatment under battlefield pressure."
        ),
        ability_boosts_ui="One boost to Constitution or Wisdom, and one free boost.",
        skill_training_ui="Medicine and Warfare Lore.",
        feat_id="battle_medicine",
    ),
    BackgroundDefinition(
        key="fortune_teller",
        label="Fortune Teller",
        description=(
            "You practiced divination traditions and brushed against occult mysteries."
        ),
        ability_boosts_ui="One boost to Intelligence or Charisma, and one free boost.",
        skill_training_ui="Occultism and Fortune-Telling Lore.",
        feat_id="oddity_identification",
    ),
    BackgroundDefinition(
        key="gambler",
        label="Gambler",
        description=(
            "Games of chance shaped your instincts for risk and reading people."
        ),
        ability_boosts_ui="One boost to Dexterity or Charisma, and one free boost.",
        skill_training_ui="Deception and Games Lore.",
        feat_id="lie_to_me",
    ),
    BackgroundDefinition(
        key="gladiator",
        label="Gladiator",
        description=(
            "Arena combat taught you to fight while keeping the crowd focused on you."
        ),
        ability_boosts_ui="One boost to Strength or Charisma, and one free boost.",
        skill_training_ui="Performance and Gladiatorial Lore.",
        feat_id="impressive_performance",
    ),
    BackgroundDefinition(
        key="guard",
        label="Guard",
        description=(
            "You served in guard duty and learned practical intimidation and orderkeeping."
        ),
        ability_boosts_ui="One boost to Strength or Charisma, and one free boost.",
        skill_training_ui="Intimidation and Legal Lore or Warfare Lore.",
        feat_id="quick_coercion",
    ),
    BackgroundDefinition(
        key="herbalist",
        label="Herbalist",
        description=(
            "You trained in medicinal herbs and natural remedies."
        ),
        ability_boosts_ui="One boost to Constitution or Wisdom, and one free boost.",
        skill_training_ui="Nature and Herbalism Lore.",
        feat_id="natural_medicine",
    ),
    BackgroundDefinition(
        key="hermit",
        label="Hermit",
        description=(
            "You lived in solitude and developed unusual practical knowledge."
        ),
        ability_boosts_ui="One boost to Constitution or Intelligence, and one free boost.",
        skill_training_ui="Nature or Occultism, plus one terrain Lore tied to your refuge.",
        feat_id="dubious_knowledge",
    ),
    BackgroundDefinition(
        key="hunter",
        label="Hunter",
        description=(
            "Tracking and harvesting wild game prepared you for long expeditions."
        ),
        ability_boosts_ui="One boost to Dexterity or Wisdom, and one free boost.",
        skill_training_ui="Survival and Tanning Lore.",
        feat_id="survey_wildlife",
    ),
    BackgroundDefinition(
        key="laborer",
        label="Laborer",
        description=(
            "Years of hard physical work made you resilient and strong."
        ),
        ability_boosts_ui="One boost to Strength or Constitution, and one free boost.",
        skill_training_ui="Athletics and Labor Lore.",
        feat_id="hefty_hauler",
    ),
    BackgroundDefinition(
        key="martial_disciple",
        label="Martial Disciple",
        description=(
            "You underwent strict combat training in a formal martial institution."
        ),
        ability_boosts_ui="One boost to Strength or Dexterity, and one free boost.",
        skill_training_ui="Choose Acrobatics or Athletics, plus Warfare Lore.",
        feat_id=None,
        choice_kind="background_martial_disciple",
        extra_data={
            "martial_disciple_skill_choices": ["acrobatics", "athletics"],
            "martial_disciple_feat_by_skill": {
                "acrobatics": "cat_fall",
                "athletics": "quick_jump",
            },
        },
    ),
    BackgroundDefinition(
        key="merchant",
        label="Merchant",
        description=(
            "Trade and bargaining taught you to evaluate value under pressure."
        ),
        ability_boosts_ui="One boost to Intelligence or Charisma, and one free boost.",
        skill_training_ui="Diplomacy and Mercantile Lore.",
        feat_id="bargain_hunter",
    ),
    BackgroundDefinition(
        key="miner",
        label="Miner",
        description=(
            "You worked in dangerous underground conditions and learned cave survival."
        ),
        ability_boosts_ui="One boost to Strength or Wisdom, and one free boost.",
        skill_training_ui="Survival and Mining Lore.",
        feat_id="terrain_expertise",
    ),
    BackgroundDefinition(
        key="noble",
        label="Noble",
        description=(
            "Court life taught you etiquette, influence, and political caution."
        ),
        ability_boosts_ui="One boost to Intelligence or Charisma, and one free boost.",
        skill_training_ui="Society and Genealogy Lore or Heraldry Lore.",
        feat_id="courtly_graces",
    ),
    BackgroundDefinition(
        key="nomad",
        label="Nomad",
        description=(
            "Constant travel taught you survival with limited resources."
        ),
        ability_boosts_ui="One boost to Constitution or Wisdom, and one free boost.",
        skill_training_ui="Survival and one terrain Lore from your journeys.",
        feat_id="assurance",
    ),
    BackgroundDefinition(
        key="prisoner",
        label="Prisoner",
        description=(
            "Captivity hardened you and taught stealthy ways to endure and escape."
        ),
        ability_boosts_ui="One boost to Strength or Constitution, and one free boost.",
        skill_training_ui="Stealth and Underworld Lore.",
        feat_id="experienced_smuggler",
    ),
    BackgroundDefinition(
        key="sailor",
        label="Sailor",
        description=(
            "A life at sea trained your body and instincts for harsh conditions."
        ),
        ability_boosts_ui="One boost to Strength or Dexterity, and one free boost.",
        skill_training_ui="Athletics and Sailing Lore.",
        feat_id="underwater_marauder",
    ),
    BackgroundDefinition(
        key="scholar",
        label="Scholar",
        description=(
            "You devoted yourself to study and set out to test your learning in the world."
        ),
        ability_boosts_ui="One boost to Intelligence or Wisdom, and one free boost.",
        skill_training_ui=(
            "Choose Arcana, Nature, Occultism, or Religion; plus Academia Lore."
        ),
        feat_id="assurance",
    ),
    BackgroundDefinition(
        key="scout",
        label="Scout",
        description=(
            "You guided others through wild terrain and became adept at field travel."
        ),
        ability_boosts_ui="One boost to Dexterity or Wisdom, and one free boost.",
        skill_training_ui="Survival and one terrain Lore from your scouting work.",
        feat_id="forager",
    ),
    BackgroundDefinition(
        key="street_urchin",
        label="Street Urchin",
        description=(
            "You survived city streets through theft, caution, and fast reflexes."
        ),
        ability_boosts_ui="One boost to Dexterity or Constitution, and one free boost.",
        skill_training_ui="Thievery and one city Lore from your home city.",
        feat_id="pickpocket",
    ),
    BackgroundDefinition(
        key="tinker",
        label="Tinker",
        description=(
            "You built and repaired odd devices, always chasing practical invention."
        ),
        ability_boosts_ui="One boost to Dexterity or Intelligence, and one free boost.",
        skill_training_ui="Crafting and Engineering Lore.",
        feat_id="specialty_crafting",
    ),
    BackgroundDefinition(
        key="warrior",
        label="Warrior",
        description=(
            "You fought in militias, armies, or mercenary companies before adventuring."
        ),
        ability_boosts_ui="One boost to Strength or Constitution, and one free boost.",
        skill_training_ui="Intimidation and Warfare Lore.",
        feat_id="intimidating_glare",
    ),
]


def _status_id_for_key(background_key: str) -> str:
    return f"background_{background_key}"


def _translate_background_ui(text: str) -> str:
    out = str(text or "").strip()
    if not out:
        return ""
    mapped = _BACKGROUND_UI_TRANSLATIONS.get(out)
    if mapped:
        return mapped
    replacements = {
        "One boost to": "Jeden boost do",
        "and one free boost.": "oraz jeden dowolny boost.",
        " and ": " i ",
        " or ": " lub ",
    }
    for source, target in replacements.items():
        out = out.replace(source, target)
    return out


def _localized_background_label(definition: BackgroundDefinition) -> str:
    key = str(definition.key or "").strip().lower()
    if not key:
        return str(definition.label or "")
    return (
        localize_term_pl(f"background_{key}")
        or localize_term_pl(key)
        or str(definition.label or key)
    )


def _localized_background_description(definition: BackgroundDefinition) -> str:
    key = str(definition.key or "").strip().lower()
    if not key:
        return str(definition.description or "")
    return _BACKGROUND_DESCRIPTION_PL.get(key, str(definition.description or ""))


def _build_prompt_long(definition: BackgroundDefinition, feat_status: Status | None) -> str:
    def _feat_short_mechanics(status: Status | None) -> str:
        if status is None:
            return ""
        data = getattr(status, "data", None) or {}
        raw = str(data.get("ui_description") or data.get("ui_prompt_long") or "").strip()
        if not raw:
            return ""
        lines = [str(line).strip() for line in raw.splitlines() if str(line).strip()]
        if not lines:
            return ""
        for line in lines:
            low = line.lower()
            if "mechanika:" not in low:
                continue
            _, _, rest = line.partition(":")
            trimmed = rest.strip()
            if trimmed:
                return trimmed
            return line.strip()
        return lines[0]

    description_pl = _localized_background_description(definition)
    feat_mechanics = _feat_short_mechanics(feat_status)
    feat_line = (
        f"{feat_status.display_label} (dodawany do bohatera jako status)."
        if feat_status is not None
        else "Feat zależny od wyboru w trakcie setupu."
    )
    feat_mechanics_line = (
        f"- Mechanika featu (krotko): {feat_mechanics}"
        if feat_mechanics
        else "- Mechanika featu (krotko): opis zalezny od wyboru/featu."
    )
    return "\n".join(
        [
            description_pl,
            "",
            "Mechanika (w tym silniku):",
            f"- Boosty cech (informacyjnie w UI): {_translate_background_ui(definition.ability_boosts_ui)}",
            f"- Szkolenie Skill/Lore (informacyjnie w UI): {_translate_background_ui(definition.skill_training_ui)}",
            f"- Feat z backgroundu: {feat_line}",
            feat_mechanics_line,
            "",
            f"Przypomnienie reguły bazowej: {BACKGROUND_CORE_RULES_UI}",
        ]
    )


def _build_background_status(definition: BackgroundDefinition) -> Status:
    feat_status = _FEAT_BY_ID.get(str(definition.feat_id or "").strip().lower())
    localized_label = _localized_background_label(definition)
    localized_description = _localized_background_description(definition)
    data: dict[str, object] = {
        "ui_description": localized_description,
        "ui_prompt": f"Tlo: {localized_label}",
        "ui_prompt_long": _build_prompt_long(definition, feat_status),
        "is_background": True,
        "background_key": definition.key,
        "background_label": localized_label,
        "background_ability_boosts_ui": _translate_background_ui(definition.ability_boosts_ui),
        "background_skill_training_ui": _translate_background_ui(definition.skill_training_ui),
        "background_skill_training_ui_only": True,
        "background_feat_id": definition.feat_id,
        "background_core_rules_ui": BACKGROUND_CORE_RULES_UI,
    }
    if definition.choice_kind:
        data["ui_choice_kind"] = definition.choice_kind
    if definition.extra_data:
        data.update(dict(definition.extra_data))
    if feat_status is not None:
        data["grants_statuses"] = [feat_status]
    return Status(
        id=_status_id_for_key(definition.key),
        label=f"{localized_label} (Tlo)",
        data=data,
    )


BACKGROUND_STATUS_BY_KEY: dict[str, Status] = {}
BACKGROUND_STATUS_BY_ID: dict[str, Status] = {}

for _definition in BACKGROUND_DEFINITIONS:
    _status = _build_background_status(_definition)
    BACKGROUND_STATUS_BY_KEY[_definition.key] = _status
    BACKGROUND_STATUS_BY_ID[_status.id] = _status
    globals()[f"{_definition.key.upper()}_BACKGROUND_STATUS"] = _status


BACKGROUND_CHOICES: list[str] = [item.key for item in BACKGROUND_DEFINITIONS]


def get_background_status(key_or_id: str) -> Status | None:
    raw = str(key_or_id or "").strip().lower().replace(" ", "_")
    if not raw:
        return None
    by_key = BACKGROUND_STATUS_BY_KEY.get(raw)
    if by_key is not None:
        return by_key
    if raw.startswith("background_"):
        return BACKGROUND_STATUS_BY_ID.get(raw)
    return BACKGROUND_STATUS_BY_ID.get(f"background_{raw}")


__all__ = [
    "BACKGROUND_CORE_RULES_UI",
    "BackgroundDefinition",
    "BACKGROUND_DEFINITIONS",
    "BACKGROUND_STATUS_BY_KEY",
    "BACKGROUND_STATUS_BY_ID",
    "BACKGROUND_CHOICES",
    "get_background_status",
] + [f"{item.key.upper()}_BACKGROUND_STATUS" for item in BACKGROUND_DEFINITIONS]

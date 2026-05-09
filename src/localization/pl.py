from __future__ import annotations

import re


def _normalize(value: str | None) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


_LABELS_PL: dict[str, str] = {
    # abilities
    "strength": "Siła",
    "dexterity": "Zręczność",
    "constitution": "Kondycja",
    "intelligence": "Inteligencja",
    "wisdom": "Mądrość",
    "charisma": "Charyzma",
    "free": "Dowolna",
    # core skills
    "acrobatics": "Akrobatyka",
    "arcana": "Arkana",
    "athletics": "Atletyka",
    "crafting": "Rzemiosło",
    "deception": "Oszustwo",
    "diplomacy": "Dyplomacja",
    "intimidation": "Zastraszanie",
    "medicine": "Medycyna",
    "nature": "Natura",
    "occultism": "Okultyzm",
    "performance": "Występy",
    "religion": "Religia",
    "society": "Społeczeństwo",
    "stealth": "Skradanie",
    "survival": "Przetrwanie",
    "thievery": "Złodziejstwo",
    "perception": "Percepcja",
    "fortitude": "Wytrzymałość",
    "reflex": "Refleks",
    "will": "Wola",
    "untrained": "Niewyszkolony",
    "trained": "Wyszkolony",
    "expert": "Ekspert",
    "master": "Mistrz",
    "legendary": "Legendarny",
    # ancestries / classes
    "human": "Człowiek",
    "elf": "Elf",
    "dwarf": "Krasnolud",
    "gnome": "Gnom",
    "goblin": "Goblin",
    "halfling": "Niziołek",
    "fighter": "Wojownik",
    "rogue": "Łotrzyk",
    "wizard": "Czarodziej",
    "cleric": "Kapłan",
    "barbarian": "Barbarzyńca",
    "ranger": "Łowca",
    "bard": "Bard",
    "alchemist": "Alchemik",
    "alchemist_research_field": "Pole badań alchemika",
    "bomber": "Bombardier",
    "chirurgeon": "Chirurgion",
    "mutagenist": "Mutagenista",
    "champion": "Czempion",
    "paladin": "Paladyn",
    "redeemer": "Odkupiciel",
    "liberator": "Wyzwoliciel",
    "iomedae": "Iomedae",
    "sarenrae": "Sarenrae",
    "torag": "Torag",
    "shelyn": "Shelyn",
    "desna": "Desna",
    "abadar": "Abadar",
    "custom": "Własne",
    "druid": "Druid",
    "monk": "Mnich",
    "sorcerer": "Czarownik",
    # backgrounds
    "acolyte": "Akolita",
    "acrobat": "Akrobata",
    "animal_whisperer": "Szeptacz zwierząt",
    "artisan": "Rzemieślnik",
    "artist": "Artysta",
    "barkeep": "Karczmarz",
    "barrister": "Prawnik",
    "bounty_hunter": "Łowca nagród",
    "charlatan": "Szarlatan",
    "criminal": "Przestępca",
    "detective": "Detektyw",
    "emissary": "Emisariusz",
    "entertainer": "Artysta sceniczny",
    "farmhand": "Pomocnik rolnika",
    "field_medic": "Medyk polowy",
    "fortune_teller": "Wróżbita",
    "gambler": "Hazardzista",
    "gladiator": "Gladiator",
    "guard": "Strażnik",
    "herbalist": "Zielarz",
    "hermit": "Pustelnik",
    "hunter": "Łowca",
    "laborer": "Robotnik",
    "martial_disciple": "Uczeń sztuk walki",
    "merchant": "Kupiec",
    "miner": "Górnik",
    "noble": "Szlachcic",
    "nomad": "Nomada",
    "prisoner": "Więzień",
    "sailor": "Żeglarz",
    "scholar": "Uczony",
    "scout": "Zwiadowca",
    "street_urchin": "Ulicznik",
    "tinker": "Majsterkowicz",
    "warrior": "Wojownik",
    "background_acolyte": "Akolita",
    "background_acrobat": "Akrobata",
    "background_animal_whisperer": "Szeptacz zwierząt",
    "background_artisan": "Rzemieślnik",
    "background_artist": "Artysta",
    "background_barkeep": "Karczmarz",
    "background_barrister": "Prawnik",
    "background_bounty_hunter": "Łowca nagród",
    "background_charlatan": "Szarlatan",
    "background_criminal": "Przestępca",
    "background_detective": "Detektyw",
    "background_emissary": "Emisariusz",
    "background_entertainer": "Artysta sceniczny",
    "background_farmhand": "Pomocnik rolnika",
    "background_field_medic": "Medyk polowy",
    "background_fortune_teller": "Wróżbita",
    "background_gambler": "Hazardzista",
    "background_gladiator": "Gladiator",
    "background_guard": "Strażnik",
    "background_herbalist": "Zielarz",
    "background_hermit": "Pustelnik",
    "background_hunter": "Łowca",
    "background_laborer": "Robotnik",
    "background_martial_disciple": "Uczeń sztuk walki",
    "background_merchant": "Kupiec",
    "background_miner": "Górnik",
    "background_noble": "Szlachcic",
    "background_nomad": "Nomada",
    "background_prisoner": "Więzień",
    "background_sailor": "Żeglarz",
    "background_scholar": "Uczony",
    "background_scout": "Zwiadowca",
    "background_street_urchin": "Ulicznik",
    "background_tinker": "Majsterkowicz",
    "background_warrior": "Wojownik",
    # general feats
    "additional_lore": "Dodatkowa wiedza",
    "adopted_ancestry": "Przysposobiona ancestry",
    "alchemical_crafting": "Alchemiczne rzemiosło",
    "arcane_sense": "Arcane Sense",
    "armor_proficiency": "Biegłość w pancerzu",
    "assurance": "Pewność",
    "bargain_hunter": "Łowca okazji",
    "battle_medicine": "Medycyna polowa",
    "breath_control": "Kontrola oddechu",
    "canny_acumen": "Bystry umysł",
    "cat_fall": "Koci upadek",
    "charming_liar": "Uroczysty kłamca",
    "combat_climber": "Bojowy wspinacz",
    "courtly_graces": "Dworska ogłada",
    "diehard": "Twardziel",
    "dubious_knowledge": "Wątpliwa wiedza",
    "experienced_professional": "Doświadczony fachowiec",
    "experienced_smuggler": "Doświadczony przemytnik",
    "experienced_tracker": "Doświadczony tropiciel",
    "fascinating_performance": "Fascynujący występ",
    "fast_recovery": "Szybka regeneracja",
    "feather_step": "Lekki krok",
    "fleet": "Szybki krok",
    "forager": "Zbieracz",
    "group_coercion": "Grupowy przymus",
    "group_impression": "Grupowe wrażenie",
    "hefty_hauler": "Silny tragarz",
    "hobnobber": "Bywalec salonów",
    "impressive_performance": "Imponujący występ",
    "incredible_initiative": "Niezwykła inicjatywa",
    "intimidating_glare": "Groźne spojrzenie",
    "lengthy_diversion": "Długa dywersja",
    "multilingual": "Poliglota",
    "natural_medicine": "Naturalna medycyna",
    "oddity_identification": "Identyfikacja osobliwości",
    "pickpocket": "Kieszonkowiec",
    "quick_coercion": "Szybki przymus",
    "quick_identification": "Szybka identyfikacja",
    "quick_jump": "Szybki skok",
    "quick_repair": "Szybka naprawa",
    "quick_squeeze": "Szybkie przeciskanie",
    "read_lips": "Czytanie z ust",
    "recognize_spell": "Rozpoznanie czaru",
    "ride": "Jazda konna",
    "shield_block": "Blok tarczą",
    "sign_language": "Język migowy",
    "skill_training": "Trening umiejętności",
    "snare_crafting": "Rzemiosło sideł",
    "specialty_crafting": "Specjalistyczne rzemiosło",
    "subtle_theft": "Subtelna kradzież",
    "survey_wildlife": "Obserwacja dzikiej przyrody",
    "terrain_expertise": "Znawca terenu",
    "terrain_stalker": "Łowca terenu",
    "titan_wrestler": "Pogromca olbrzymów",
    "toughness": "Wytrzymałość",
    "train_animal": "Tresura zwierząt",
    "trick_magic_item": "Sztuczka z magicznym przedmiotem",
    "underwater_marauder": "Podwodny grabieżca",
    "virtuosic_performer": "Wirtuoz sceny",
    "weapon_proficiency": "Biegłość w broni",
    # common action/event labels
    "move": "Ruch",
    "move_start": "przygotowanie ruchu",
    "interaction": "Interakcja",
    "interaction_end": "koniec interakcji",
    "interact": "Interakcja",
    "talk": "Rozmowa",
    "leave": "Zakończenie rozmowy",
    "attempt": "Próba",
    "seek": "Szukaj",
    "stealth": "Skradanie",
    "attack": "Atak",
    "equip": "Ekwipunek",
    "end": "Koniec tury",
    "delay": "Opóźnij",
    "swap_weapon": "Zmiana broni",
    "unarmed": "Walka bez broni",
    "club": "Maczuga",
    "crossbow": "Kusza",
    "dagger": "Sztylet",
    "glaive": "Glewia",
    "greataxe": "Wielki topór",
    "halberd": "Halabarda",
    "javelin": "Oszczep",
    "light_crossbow": "Lekka kusza",
    "longbow": "Długi łuk",
    "longsword": "Długi miecz",
    "mace": "Buzdygan",
    "rapier": "Rapier",
    "shortbow": "Krótki łuk",
    "shortsword": "Krótki miecz",
    "spear": "Włócznia",
    "sword": "Miecz",
    "warhammer": "Młot wojenny",
    "gauntlet": "Rękawica bojowa",
    "spiked_gauntlet": "Kolczasta rękawica",
    "sickle": "Sierp",
    "staff": "Kostur",
    "bo_staff": "Kij bo",
    "dart": "Rzutka",
    "blowgun": "Dmuchawka",
    "sling": "Proca",
    "halfling_sling_staff": "Niziołecka proca-kostur",
    "battle_axe": "Topór bitewny",
    "bastard_sword": "Miecz bastardowy",
    "clan_dagger": "Sztylet klanowy",
    "katar": "Katar",
    "light_mace": "Lekki buzdygan",
    "longspear": "Długa włócznia",
    "flail": "Korbacz",
    "war_flail": "Korbacz wojenny",
    "morningstar": "Gwiazda poranna",
    "pick": "Kilof bojowy",
    "light_pick": "Lekki kilof",
    "greatpick": "Wielki kilof",
    "scimitar": "Sejmitar",
    "falchion": "Falchion",
    "greatclub": "Wielka maczuga",
    "guisarme": "Gisarma",
    "hatchet": "Toporek",
    "lance": "Lanca",
    "light_hammer": "Lekki młot",
    "main_gauche": "Main-gauche",
    "ranseur": "Ranseur",
    "sap": "Pałka",
    "scythe": "Kosa bojowa",
    "starknife": "Starknife",
    "shield_bash": "Uderzenie tarczą",
    "shield_boss": "Umbo tarczy",
    "shield_spikes": "Kolce tarczy",
    "trident": "Trójząb",
    "whip": "Bicz",
    "greatsword": "Wielki miecz",
    "maul": "Wielki młot",
    "hand_crossbow": "Ręczna kusza",
    "heavy_crossbow": "Ciężka kusza",
    "composite_shortbow": "Kompozytowy krótki łuk",
    "composite_longbow": "Kompozytowy długi łuk",
    "shuriken": "Shuriken",
    "dogslicer": "Psie ostrze",
    "elven_curve_blade": "Elfickie zakrzywione ostrze",
    "filchers_fork": "Widelec złodzieja",
    "gnome_hooked_hammer": "Gnomi hakowy młot",
    "horsechopper": "Koniorab",
    "kama": "Kama",
    "katana": "Katana",
    "kukri": "Kukri",
    "nunchaku": "Nunchaku",
    "orc_knuckle_dagger": "Orczy pięściowy sztylet",
    "sai": "Sai",
    "spiked_chain": "Kolczasty łańcuch",
    "temple_sword": "Miecz świątynny",
    "dwarven_waraxe": "Krasnoludzki topór wojenny",
    "gnome_flickmace": "Gnomi młot cepowy",
    "orc_necksplitter": "Orczy przecinak karku",
    "sawtooth_saber": "Piła-szabla",
    "padded_armor": "Pikowany pancerz",
    "leather_armor": "Skórzana zbroja",
    "studded_leather": "Skórzana nabijana",
    "chain_shirt": "Koszula kolcza",
    "hide_armor": "Zbroja ze skór",
    "scale_mail": "Pancerz łuskowy",
    "chain_mail": "Kolczuga",
    "breastplate": "Napierśnik",
    "splint_mail": "Pancerz lamelkowy",
    "half_plate": "Półzbroja płytowa",
    "full_plate": "Pełna zbroja płytowa",
    "buckler": "Puklerz",
    "wooden_shield": "Tarcza drewniana",
    "steel_shield": "Tarcza stalowa",
    "standard_shield": "Tarcza stalowa",
    "tower_shield": "Tarcza wieżowa",
    "arrows": "Strzały (10)",
    "bolts": "Bełty (10)",
    "sling_bullets": "Pociski do procy (10)",
    "backpack": "Plecak",
    "bedroll": "Posłanie",
    "belt_pouch": "Sakiewka na pas",
    "climbing_kit": "Zestaw wspinaczkowy",
    "chalk": "Kreda (10)",
    "crowbar": "Łom",
    "flint_and_steel": "Krzesiwo",
    "grappling_hook": "Hak zadziorny",
    "healer_tools": "Narzędzia medyka",
    "thieves_tools": "Narzędzia złodziejskie",
    "repair_kit": "Zestaw naprawczy",
    "rope_hemp_50ft": "Lina konopna (50 ft)",
    "rope_silk_50ft": "Lina jedwabna (50 ft)",
    "rations_week": "Racje (1 tydzień)",
    "sack": "Worek",
    "torch": "Pochodnia",
    "waterskin": "Bukłak",
    "lantern_hooded": "Latarnia kapturowa",
    "lantern_bullseye": "Latarnia reflektorowa",
    "oil_flask": "Olej (1 flaszka)",
    "spellbook": "Księga zaklęć",
    "formula_book": "Księga formuł",
    "caltrops": "Kolce",
    "chain_10ft": "Łańcuch (10 ft)",
    "hammer": "Młotek",
    "mirror_steel": "Lusterko stalowe",
    "soap": "Mydło",
    "shovel": "Łopata",
    "signal_whistle": "Gwizdek sygnałowy",
    "spike_iron_10": "Żelazne kołki (10)",
    "lock_simple": "Zamek prosty",
    "lock_good": "Zamek dobry",
    "holy_symbol_wooden": "Święty symbol (drewniany)",
    "holy_symbol_silver": "Święty symbol (srebrny)",
    "writing_set": "Zestaw pisarski",
    "tent": "Namiot",
    "disarm": "Rozbrojenie",
    "parry": "Parowanie",
    "trip": "Podcięcie",
    "shove": "Odepchnięcie",
    "grapple": "Chwyt",
    "feint": "Zwód",
    "demoralize": "Demoralizacja",
    "aid": "Pomoc",
    "stand": "Wstań",
    "prone": "Padnij",
    "step": "Krok",
    "leap": "Skok",
    "take_cover": "Osłona",
    "cover": "Osłona",
    "raise_shield": "Podnieś tarczę",
    "disable_device": "Rozbrój urządzenie",
    "identify_trap": "Zidentyfikuj pułapkę",
    "quick_alchemy": "Szybka alchemia",
    "mutagenic_flashback": "Mutageniczny flashback",
    "thunderstone": "Kamień gromu",
    "silvertongue_mutagen": "Mutagen srebrnego języka",
    "flurry_of_blows": "Grad ciosów",
    "rage": "Szał",
    "refocus": "Refokus",
    "skill_check": "Test umiejętności",
    "ancientblood": "Pradawna krew",
    "enemy_attack_melee": "Atak przeciwnika",
    "enemy_move": "Ruch przeciwnika",
    "phase_start_exploration": "Start eksploracji",
    "phase_end_exploration": "Koniec eksploracji",
    "phase_start_combat": "Start walki",
    "phase_end_combat": "Koniec walki",
    "lay_on_hands": "Nałożenie rąk",
    "command_animal_companion": "Komenda: Zwierzęcy towarzysz",
    "commandfamilair": "Komenda: Chowaniec",
    "hunt_prey": "Wyznacz ofiarę",
    "drain_bonded_item": "Wyczerp bonded item",
    "drain_familiar": "Wyczerp chowańca",
    "wizard_spell_substitution": "Podmiana zaklęcia",
    "retrain_sorcerer_spell": "Retrain Sorcerer Spell",
    "cancel": "Anuluj",
    # bombs / elixirs / poisons
    "acidflask": "Fiolka kwasu",
    "acid_flask": "Fiolka kwasu",
    "alchemists_fire": "Ognista mikstura alchemika",
    "bottled_lightning": "Butelkowana błyskawica",
    "frost_vial": "Mroźna fiolka",
    "tanglefoot_bag": "Worek lepikuli",
    "smokestick": "Dymna fiolka",
    "elixir_of_life": "Eliksir życia",
    "holy_water": "Woda święcona",
    "unholy_water": "Woda plugawa",
    "minor_healing_potion": "Mikstura leczenia (słaba)",
    "scroll_common_rank1": "Zwój czaru 1. rangi",
    "potency_crystal": "Kryształ potencji",
    "cheetahs_elixir": "Eliksir geparda",
    "eagle_eye_elixir": "Eliksir sokolego oka",
    "juggernaut_mutagen": "Mutagen juggernauta",
    "quicksilver_mutagen": "Mutagen żywoksieci",
    "serene_mutagen": "Mutagen spokoju",
    "cognitive_mutagen": "Mutagen poznawczy",
    "antidote": "Antidotum",
    "antiplague": "Antyplaga",
    "arsenic": "Arsen",
    "giant_centipede_venom": "Jad wielkiej skolopendry",
    # human feats / heritages
    "half_elf": "Półelf",
    "half_orc": "Półork",
    "skilled_heritage": "Utalentowane dziedzictwo",
    "versatile_heritage": "Wszechstronne dziedzictwo",
    "general_training": "Trening ogólny",
    "natural_ambition": "Naturalna ambicja",
    "natural_skill": "Naturalny talent",
    "adapted_cantrip": "Adaptowany cantrip",
    "elf_atavism": "Elficki atawizm",
    "unconventional_weaponry": "Niekonwencjonalna broń",
    # common class feats (creation choices)
    "double_slice": "Podwójne cięcie",
    "exacting_strike": "Precyzyjny cios",
    "point_blank_shot": "Strzał z bliska",
    "power_attack": "Potężny atak",
    "reactive_shield": "Reaktywna tarcza",
    "snagging_strike": "Zaczepny cios",
    "sudden_charge": "Nagła szarża",
    "nimble_dodge": "Zwrotny unik",
    "trap_finder": "Tropiciel pułapek",
    "twin_feint": "Podwójna zwoda",
    "youre_next": "Ty jesteś następny",
    "counterspell": "Kontrczar",
    "dangerous_sorcery": "Niebezpieczna czaroksięstwo",
    "familiar": "Chowaniec",
    "reach_spell": "Wydłużony czar",
    "widen_spell": "Poszerzony czar",
    "eschew_materials": "Rzucanie bez komponentów",
    "hand_of_the_apprentice": "Dłoń adepta",
    "animal_companion": "Zwierzęcy towarzysz",
    "crossbow_ace": "Mistrz kuszy",
    "hunted_shot": "Strzał na cel",
    "monster_hunter": "Łowca potworów",
    "twin_takedown": "Podwójne obalenie",
    "crane_stance": "Postawa żurawia",
    "dragon_stance": "Postawa smoka",
    "ki_rush": "Poryw ki",
    "ki_strike": "Uderzenie ki",
    "monastic_weaponry": "Broń klasztorna",
    "mountain_stance": "Postawa góry",
    "tiger_stance": "Postawa tygrysa",
    "wolf_stance": "Postawa wilka",
    "bardic_lore": "Bardyczna wiedza",
    "lingering_composition": "Trwała kompozycja",
    "versatile_performance": "Wszechstronny występ",
    "deific_weapon": "Boska broń",
    "deitys_domain": "Domena bóstwa",
    "ranged_reprisal": "Dystansowa reprymenda",
    "raise_shield_allow": "Podniesienie tarczy",
    "unimpeded_step": "Nieskrępowany krok",
    "weight_of_guilt": "Ciężar winy",
    "deadly_simplicity": "Śmiercionośna prostota",
    "domain_initiate": "Inicjacja domeny",
    "harming_hands": "Dłonie krzywdy",
    "healing_hands": "Dłonie uzdrowienia",
    "holy_castigation": "Święte zgromienie",
    "leshy_familiar": "Leshy chowaniec",
    "storm_born": "Zrodzony z burzy",
    "advanced_alchemy": "Zaawansowana alchemia",
    "alchemical_savant": "Alchemiczny wirtuoz",
    "alchemist_familiar_guidance": "Wsparcie chowańca alchemika",
    "far_lobber": "Daleki rzut",
    "quick_alchemy_allow": "Szybka alchemia",
    "quick_bomber": "Szybki bombardier",
    "cute_vision": "Czujne spojrzenie",
    "moment_of_clarity": "Moment jasności",
    "raging_intimidation": "Zastraszanie w szale",
    "raging_thrower": "Miotacz w szale",
    # ancestry feats (core set used in creation)
    "ancestral_longevity": "Pradawna długowieczność",
    "elven_lore": "Elficka wiedza",
    "elven_weapon_familiarity": "Elficka znajomość broni",
    "forlorn": "Osamotniony",
    "nimble_elf": "Zwrotny elf",
    "otherworldly_magic": "Nadziemska magia",
    "unwavering_mien": "Niezachwiane oblicze",
    "dwarven_lore": "Krasnoludzka wiedza",
    "dwarven_weapon_familiarity": "Krasnoludzka znajomość broni",
    "rock_runner": "Skalny biegacz",
    "stonecunning": "Kamienna bystrość",
    "unburdened_iron": "Nieskrępowane żelazo",
    "vengeful_hatred": "Mściwa nienawiść",
    "burn_it": "Podpal to",
    "city_scavenger": "Miejski padlinożerca",
    "goblin_lore": "Goblińska wiedza",
    "goblin_scuttle": "Gobliński przemyk",
    "goblin_song": "Goblińska pieśń",
    "goblin_weapon_familiarity": "Goblińska znajomość broni",
    "junk_tinker": "Majsterkowicz złomu",
    "rough_rider": "Szorstki jeździec",
    "very_sneaky": "Bardzo skryty",
    "distracting_shadows": "Rozpraszające cienie",
    "halfling_lore": "Niziołecka wiedza",
    "halfling_luck": "Szczęście niziołka",
    "halfling_weapon_familiarity": "Niziołecka znajomość broni",
    "sure_feet": "Pewny krok",
    "titan_slinger": "Pogromca olbrzymów",
    "unfettered_halfling": "Nieskrępowany niziołek",
    "watchful_halfling": "Czujny niziołek",
    "animal_accomplice": "Zwierzęcy pomocnik",
    "burrow_elocutionist": "Mówca nor",
    "fey_fellowship": "Więź z fey",
    "first_world_magic": "Magia Pierwszego Świata",
    "gnome_obsession": "Gnomia obsesja",
    "gnome_weapon_familiarity": "Gnomia znajomość broni",
    "illusion_sense": "Zmysł iluzji",
    "orc_ferocity": "Orcza zajadłość",
    "orc_sight": "Orczy wzrok",
    "orc_superstition": "Orczy przesąd",
    "orc_weapon_familiarity": "Orcza znajomość broni",
    "cooperative_nature": "Współpracująca natura",
    "haughty_obstinacy": "Wyniosły upór",
    "monstrous_peacemaker": "Potworny rozjemca",
    # heritages
    "arctic_elf": "Arktyczny elf",
    "cavern_elf": "Jaskiniowy elf",
    "seer_elf": "Wizjonerski elf",
    "whisper_elf": "Szeptany elf",
    "woodland_elf": "Leśny elf",
    "ancient_blooded_dwarf": "Krasnolud pradawnej krwi",
    "forge_dwarf": "Kuźniany krasnolud",
    "rock_dwarf": "Skalny krasnolud",
    "strong_blooded_dwarf": "Krasnolud silnej krwi",
    "chameleon_gnome": "Kameleonowy gnom",
    "fey_touched_gnome": "Gnom dotknięty fey",
    "sensate_gnome": "Zmysłowy gnom",
    "umbral_gnome": "Mroczny gnom",
    "wellspring_gnome": "Gnom źródła magii",
    "charhide_goblin": "Goblin o węglowej skórze",
    "irongut_goblin": "Goblin żelaznego żołądka",
    "razortooth_goblin": "Goblin o brzytwowych kłach",
    "snow_goblin": "Śnieżny goblin",
    "unbreakable_goblin": "Niezłomny goblin",
    "gutsy_halfling": "Niezwykle odważny niziołek",
    "hillock_halfling": "Wzgórzowy niziołek",
    "nomadic_halfling": "Nomadyczny niziołek",
    "twilight_halfling": "Zmierzchowy niziołek",
    "wildwood_halfling": "Leśny niziołek",
    # magic traditions / schools / domains
    "arcane": "Arkana",
    "divine": "Boska",
    "occult": "Okultystyczna",
    "primal": "Pierwotna",
    "abjuration": "Abjuracja",
    "conjuration": "Konjuracja",
    "divination": "Dywinacja",
    "enchantment": "Zaklinanie",
    "evocation": "Ewokacja",
    "illusion": "Iluzja",
    "necromancy": "Nekromancja",
    "transmutation": "Transmutacja",
    "air": "Powietrze",
    "ambition": "Ambicja",
    "cities": "Miasta",
    "confidence": "Pewność",
    "creation": "Tworzenie",
    "darkness": "Ciemność",
    "death": "Śmierć",
    "destruction": "Zniszczenie",
    "dreams": "Sny",
    "earth": "Ziemia",
    "family": "Rodzina",
    "fate": "Los",
    "fire": "Ogień",
    "freedom": "Wolność",
    "healing": "Leczenie",
    "indulgence": "Folga",
    "knowledge": "Wiedza",
    "luck": "Szczęście",
    "magic": "Magia",
    "might": "Moc",
    "moon": "Księżyc",
    "nature": "Natura",
    "nightmares": "Koszmary",
    "pain": "Ból",
    "passion": "Pasja",
    "perfection": "Perfekcja",
    "protection": "Ochrona",
    "secrecy": "Sekretność",
    "sun": "Słońce",
    "travel": "Podróż",
    "trickery": "Podstęp",
    "truth": "Prawda",
    "tyranny": "Tyrania",
    "undeath": "Nieśmierć",
    "water": "Woda",
    "wealth": "Bogactwo",
    "zeal": "Gorliwość",
    "custom_domain_a": "Domena niestandardowa A",
    "custom_domain_b": "Domena niestandardowa B",
    "custom_domain_c": "Domena niestandardowa C",
    # cantrips/spells
    "acid_splash": "Kwasowy rozprysk",
    "acidsplash": "Kwasowy rozprysk",
    "chill_touch": "Lodowy dotyk",
    "dancing_lights": "Tańczące światła",
    "daze": "Otumanienie",
    "detect_magic": "Wykrycie magii",
    "detectmagic": "Wykrycie magii",
    "disrupt_undead": "Zakłócenie nieumarłego",
    "divine_lance": "Boska lanca",
    "electric_arc": "Łuk elektryczny",
    "forbidding_ward": "Zakazująca osłona",
    "ghost_sound": "Widmowy dźwięk",
    "guidance": "Wskazówka",
    "know_direction": "Znajdź kierunek",
    "light": "Światło",
    "mage_hand": "Magiczna dłoń",
    "message": "Wiadomość",
    "prestidigitation": "Sztuczki magiczne",
    "produce_flame": "Stwórz płomień",
    "ray_of_frost": "Promień mrozu",
    "read_aura": "Odczyt aury",
    "shield": "Tarcza",
    "shield_cantrip": "Tarcza (cantrip)",
    "sigil": "Symbol",
    "stabilize": "Stabilizacja",
    "tanglefoot": "Lepliwe pnącza",
    "telekinetic_projectile": "Telekinetyczny pocisk",
    "air_bubble": "Bąbel powietrza",
    "alarm": "Alarm",
    "ant_haul": "Mrówi trud",
    "bane": "Nieszczęście",
    "bless": "Błogosławieństwo",
    "burning_hands": "Płonące dłonie",
    "charm": "Urok",
    "color_spray": "Barwny rozbłysk",
    "command": "Rozkaz",
    "create_water": "Stwórz wodę",
    "detect_alignment": "Wykrycie etosu",
    "detect_poison": "Wykrycie trucizny",
    "fear": "Strach",
    "feather_fall": "Łagodny upadek",
    "fleet_step": "Szybki krok",
    "floating_disk": "Latający dysk",
    "grease": "Smar",
    "grim_tendrils": "Ponure macki",
    "goblin_pox": "Goblinia zaraza",
    "gust_of_wind": "Podmuch wiatru",
    "harm": "Zranienie",
    "heal": "Uleczenie",
    "hydraulic_push": "Hydrauliczne pchnięcie",
    "illusory_disguise": "Iluzoryczne przebranie",
    "illusory_object": "Iluzoryczny obiekt",
    "item_facade": "Fasada przedmiotu",
    "jump": "Skok",
    "lock": "Zaklucie",
    "longstrider": "Długi krok",
    "mage_armor": "Pancerz maga",
    "magic_aura": "Magiczna aura",
    "magic_fang": "Magiczny kieł",
    "magic_missile": "Magiczny pocisk",
    "magic_weapon": "Magiczna broń",
    "mending": "Naprawa",
    "mindlink": "Więź umysłów",
    "negate_aroma": "Zneutralizuj zapach",
    "pass_without_trace": "Przejście bez śladu",
    "pest_form": "Postać szkodnika",
    "phantom_pain": "Fantomowy ból",
    "purify_food_and_drink": "Oczyść jedzenie i napój",
    "ray_of_enfeeblement": "Promień osłabienia",
    "shillelagh": "Shillelagh",
    "shocking_grasp": "Piorunujący chwyt",
    "sleep": "Sen",
    "soothe": "Ukojenie",
    "spider_sting": "Pająkowe użądlenie",
    "spirit_link": "Więź duchowa",
    "summon_animal": "Przywołaj zwierzę",
    "summon_construct": "Przywołaj konstrukt",
    "summon_fey": "Przywołaj fey",
    "summon_plant": "Przywołaj roślinę",
    "summon_plant_or_fungus": "Przywołaj roślinę lub grzyb",
    "true_strike": "Prawdziwy cios",
    "unseen_servant": "Niewidzialny sługa",
    "ventriloquism": "Brzuchomówstwo",
    # focus/domain spells
    "agile_feet": "Zwinne stopy",
    "ancestral_memories": "Pamięć przodków",
    "angelic_halo": "Anielska aureola",
    "appearance_of_wealth": "Pozór bogactwa",
    "athletic_rush": "Atletyczny zryw",
    "augment_summoning": "Wzmocnione przywoływanie",
    "bit_of_luck": "Okruch szczęścia",
    "blind_ambition": "Ślepa ambicja",
    "call_of_the_grave": "Wezwanie grobu",
    "charming_touch": "Czarujący dotyk",
    "charming_words": "Urzekające słowa",
    "cloak_of_shadow": "Płaszcz cienia",
    "counter_performance": "Kontrwystęp",
    "cry_of_destruction": "Krzyk zniszczenia",
    "custom_domain_spell_a": "Niestandardowy czar domeny A",
    "custom_domain_spell_b": "Niestandardowy czar domeny B",
    "custom_domain_spell_c": "Niestandardowy czar domeny C",
    "dazzling_flash": "Oślepiający błysk",
    "deaths_call": "Zew śmierci",
    "diabolic_edict": "Diabelski edykt",
    "diviners_sight": "Wzrok wróżbity",
    "domain_focus_spell": "Czar skupienia domeny",
    "dragon_claws": "Smocze szpony",
    "elemental_toss": "Żywiołowy rzut",
    "face_in_the_crowd": "Twarz w tłumie",
    "faerie_dust": "Pył fey",
    "fire_ray": "Promień ognia",
    "forced_quiet": "Wymuszona cisza",
    "force_bolt": "Pocisk mocy",
    "gluttons_jaws": "Szczęki obżarstwa",
    "goodberry": "Dobra jagoda",
    "heal_animal": "Ulecz zwierzę",
    "healers_blessing": "Błogosławieństwo uzdrowiciela",
    "hurtling_stone": "Pędzący głaz",
    "inspire_competence": "Inspirująca kompetencja",
    "inspire_courage": "Inspiracja odwagi",
    "jealous_hex": "Zaklęcie zazdrości",
    "ki_rush": "Poryw ki",
    "ki_strike": "Uderzenie ki",
    "loremaster_etude": "Etiuda loremastera",
    "magics_vessel": "Naczynie magii",
    "moonbeam": "Księżycowy promień",
    "overstuff": "Przejedzenie",
    "perfected_mind": "Udoskonalony umysł",
    "physical_boost": "Wzmocnienie fizyczne",
    "protective_ward": "Ochronna aura",
    "protectors_sacrifice": "Poświęcenie obrońcy",
    "pushing_gust": "Pchający podmuch",
    "read_fate": "Odczyt losu",
    "savor_the_sting": "Delektuj się użądleniem",
    "scholarly_recollection": "Naukowe wspomnienie",
    "soothing_words": "Kojące słowa",
    "splash_of_art": "Rozprysk sztuki",
    "sudden_shift": "Nagła zmiana",
    "sweet_dream": "Słodki sen",
    "tempest_surge": "Poryw burzy",
    "tentacular_limbs": "Mackowate kończyny",
    "tidal_surge": "Przypływowy zryw",
    "touch_of_obedience": "Dotyk posłuszeństwa",
    "touch_of_undeath": "Dotyk nieśmierci",
    "undeaths_blessing": "Błogosławieństwo nieśmierci",
    "unimpeded_stride": "Nieskrępowany krok",
    "veil_of_confidence": "Zasłona pewności",
    "vibrant_thorns": "Witalne ciernie",
    "waking_nightmare": "Przebudzony koszmar",
    "warped_terrain": "Wypaczony teren",
    "weapon_surge": "Zryw broni",
    "wild_morph": "Dzika mutacja",
    "wild_shape": "Dziki kształt",
    "word_of_truth": "Słowo prawdy",
    # additional bloodline granted spells (setup/localization)
    "abyssal_plague": "Otchłanna zaraza",
    "baleful_polymorph": "Złowroga polimorfia",
    "bind_undead": "Zwiąż nieumarłego",
    "black_tentacles": "Czarne macki",
    "blindness": "Ślepota",
    "blade_barrier": "Bariera ostrzy",
    "chromatic_wall": "Chromatyczna ściana",
    "cloak_of_colors": "Płaszcz kolorów",
    "cloudkill": "Trująca chmura",
    "confusion": "Splątanie",
    "crushing_despair": "Przygniatająca rozpacz",
    "dimension_door": "Wrota wymiaru",
    "disintegrate": "Dezintegracja",
    "dispel_magic": "Rozproszenie magii",
    "divine_aura": "Boska aura",
    "divine_decree": "Boski dekret",
    "divine_wrath": "Boski gniew",
    "dragon_form": "Smocza forma",
    "elemental_form": "Forma żywiołu",
    "energy_aegis": "Egida energii",
    "enlarge": "Powiększenie",
    "enthrall": "Odurzenie",
    "false_life": "Fałszywe życie",
    "feeblemind": "Otumanienie umysłu",
    "finger_of_death": "Palec śmierci",
    "fireball": "Kula ognia",
    "flame_strike": "Płomienny cios",
    "flaming_sphere": "Płomienna sfera",
    "foresight": "Przewidywanie",
    "freedom_of_movement": "Swoboda ruchu",
    "haste": "Przyspieszenie",
    "hideous_laughter": "Upiorny śmiech",
    "horrid_wilting": "Potworne wysuszenie",
    "implosion": "Implozja",
    "mariners_curse": "Klątwa marynarza",
    "mask_of_terror": "Maska grozy",
    "maze": "Labirynt",
    "meteor_swarm": "Rój meteorów",
    "mislead": "Zwiedzenie",
    "natures_enmity": "Wrogość natury",
    "outcasts_curse": "Klątwa wygnańca",
    "overwhelming_presence": "Przytłaczająca obecność",
    "prismatic_sphere": "Pryzmatyczna sfera",
    "prismatic_spray": "Pryzmatyczny rozbłysk",
    "prismatic_wall": "Pryzmatyczna ściana",
    "prying_eye": "Wścibskie oko",
    "repulsion": "Odepchnięcie",
    "resist_energy": "Odporność na energię",
    "resplendent_mansion": "Olśniewająca posiadłość",
    "searing_light": "Palące światło",
    "slow": "Spowolnienie",
    "spell_immunity": "Odporność na czar",
    "spiritual_epidemic": "Duchowa epidemia",
    "spiritual_weapon": "Duchowa broń",
    "storm_of_vengeance": "Burza zemsty",
    "suggestion": "Sugestia",
    "talking_corpse": "Mówiące zwłoki",
    "touch_of_idiocy": "Dotyk idiotyzmu",
    "true_seeing": "Prawdziwe widzenie",
    "uncontrollable_dance": "Niekontrolowany taniec",
    "unfathomable_song": "Niezgłębiona pieśń",
    "vampiric_exsanguination": "Wampiryczne wykrwawienie",
    "vampiric_touch": "Wampiryczny dotyk",
    "visions_of_danger": "Wizje zagrożenia",
    "wail_of_the_banshee": "Lament banshee",
    "warp_mind": "Wypaczenie umysłu",
    # specialties / terrain picks
    "rubble": "Gruz",
    "snow": "Śnieg",
    "underbrush": "Poszycie",
    "acting": "Aktorstwo",
    "comedy": "Komedia",
    "dance": "Taniec",
    "keyboards": "Instrumenty klawiszowe",
    "oratory": "Oratorstwo",
    "percussion": "Perkusja",
    "singing": "Śpiew",
    "strings": "Instrumenty strunowe",
    "winds": "Instrumenty dęte",
    "academia": "Akademia",
    "engineering": "Inżynieria",
    "legal": "Prawo",
    "mercantile": "Handel",
    "military": "Wojskowość",
    "sailing": "Żeglarstwo",
    "underworld": "Podziemie",
    "warfare": "Wojna",
}


_HINTS_PL: dict[str, str] = {
    "move": "Przemieść postać po planszy w zasięgu jej prędkości.",
    "attack": "Wykonaj Strike aktywną bronią; gra dolicza biegłość, atrybut, MAP i premie.",
    "equip": "Zarządzaj aktywną bronią, pancerzem i tarczą.",
    "interaction": "Wejdź w interakcję z obiektem na planszy.",
    "seek": "Wypatruj ukrytych celów lub obiektów.",
    "stealth": "Ukryj się / skradanie z modyfikatorami.",
    "delay": "Opóźnij swoją turę w kolejności inicjatywy.",
    "end": "Zakończ aktualną turę aktora.",
    "shield": "Podnieś tarczę: +AC (circumstance) do początku kolejnej tury.",
    "raise_shield": "Podnieś tarczę: +AC (circumstance) do początku kolejnej tury.",
    "disarm": "Próbujesz rozbroić cel testem Athletics przeciwko jego obronie.",
    "trip": "Próbujesz przewrócić cel testem Athletics.",
    "shove": "Próbujesz odepchnąć cel testem Athletics.",
    "grapple": "Próbujesz pochwycić i unieruchomić cel.",
    "feint": "Zwodzisz cel, by ułatwić kolejny atak.",
    "demoralize": "Zastraszasz cel, by nałożyć Frightened.",
    "take_cover": "Przyjmij osłonę i zwiększ obronę.",
    "parry": "Akcja obronna: +1 circumstance do AC do początku następnej tury.",
    "power_attack": "Dwa ataki w cenie 2 akcji: Strike z dodatkowymi kośćmi obrażeń.",
    "exacting_strike": "Press: po nieudanym trafieniu lżej karze kolejne ataki (MAP).",
    "snagging_strike": "Strike melee z efektem off-guard na cel (wymaga wolnej ręki).",
    "double_slice": "Dwa strike'i melee 1H na jednym celu; łączysz obrażenia przy 2 trafieniach.",
    "point_blank_shot": "Stance wojownika: premie dla ataków dystansowych na bliskim zasięgu.",
    "hunt_prey": "Oznacz cel łowów i aktywuj premie łowcy (Hunter's Edge).",
    "hunted_shot": "Dwa szybkie strzaly do oznaczonej ofiary (Wyznacz ofiare).",
    "twin_takedown": "Dwa strike'i melee 1H przeciw oznaczonej ofierze.",
    "twin_feint": "2 akcje: dwa strike'i melee 1H; drugi atak korzysta z feint/off-guard.",
    "sudden_charge": "2x ruch + strike melee w jednej akcji specjalnej (2 akcje).",
    "raging_intimidation": "Podczas Rage możesz używać Demoralize; dodatkowo otrzymujesz Intimidating Glare.",
    "enigma": "Muza barda: otrzymujesz Bardyczna wiedza i dopisujesz czar Prawdziwy cios.",
    "maestro": "Muza barda: otrzymujesz Trwała kompozycja i dopisujesz czar Ukojenie.",
    "polymath": "Muza barda: otrzymujesz Wszechstronny występ i dopisujesz czar Niewidzialny sługa.",
    "flurry_of_blows": "Mnich: dwa uderzenia unarmed za 1 akcję (Flourish).",
    "rage": "Wejdź w Szał: premie ofensywne kosztem ograniczeń i/lub obrony.",
    "refocus": "Odzyskaj punkt Focus poza presją walki.",
    "wizard_spell_substitution": (
        "Wizard (Spell Substitution): 10 minut poza walką, aby podmienić 1 nieużytą kopię przygotowanego czaru "
        "na inny znany czar tej samej rangi. Limit: 1 raz na scenariusz."
    ),
    "retrain_sorcerer_spell": (
        "Sorcerer: podmienia 1 znany czar repertuaru na inny czar tej samej rangi z tej samej tradycji. "
        "Nie obejmuje bloodline granted spell."
    ),
    "skill_check": "Wykonaj test wybranej umiejętności z automatycznym doliczeniem premii.",
    "strength": "Siła: premia do ataków melee, Athletics i udźwigu.",
    "dexterity": "Zręczność: premia do ataków dystansowych, Reflex, AC i skradania.",
    "constitution": "Kondycja: więcej HP i lepsze rzuty Fortitude.",
    "intelligence": "Inteligencja: więcej trained skillów i lepsze testy wiedzy.",
    "wisdom": "Mądrość: lepsza Percepcja, Will i testy intuicyjne/medyczne.",
    "charisma": "Charyzma: silniejsze działania społeczne i części magii.",
    "thunderstone": "Bomba: obrażenia sonic, splash i potencjalne ogłuszenie.",
    "silvertongue_mutagen": "Mutagen: premie społeczne kosztem parametrów fizycznych.",
    "quick_alchemy": "Tworzysz alchemiczny przedmiot w locie (wymaga feata i zasobów).",
    "bomber": (
        "Specjalizacja alchemika skupiona na bombach i precyzyjnym rozprysku. "
        "Mechanika: Signature items = acidflask i alchemists_fire; "
        "dla signature w Advanced Alchemy tworzysz 3 sztuki zamiast 2; "
        "rzucane bomby dostają tryb wyboru splash ON/OFF (obszar albo tylko cel główny)."
    ),
    "chirurgeon": (
        "Specjalizacja alchemika skupiona na leczeniu i medycynie polowej. "
        "Mechanika: Signature items = antidote i antiplague; "
        "w kanonie pozwala używać Crafting zamiast Medicine dla akcji medycznych; "
        "w silniku zapisujemy to jako znacznik research field (część zastosowań może być opisowa)."
    ),
    "mutagenist": (
        "Specjalizacja alchemika skupiona na mutagenach i ich ponownym wykorzystaniu. "
        "Mechanika: Signature items = quicksilver_mutagen i juggernaut_mutagen; "
        "dla signature w Advanced Alchemy tworzysz 3 sztuki zamiast 2; "
        "odblokowuje akcję Mutagenic Flashback (1 raz na dzień)."
    ),
    "mutagenic_flashback": "Raz dziennie odtworzenie efektu wypitego mutagenu (Mutagenist).",
    "command_animal_companion": "Wydajesz komendę zwierzęcemu towarzyszowi na jego 2 akcje.",
    "commandfamilair": "Wydajesz komendę chowańcowi zgodnie z jego trybem.",
    "command_familiar": "Wydajesz komendę chowańcowi zgodnie z jego trybem.",
    "lay_on_hands": "Focus spell czempiona: leczenie i tymczasowy bonus do AC.",
    "heal": (
        "Czar 1. rangi: wybierasz liczbę akcji przy rzucaniu.\n"
        "Mechanika:\n"
        "- 1 akcja (dotyk 5 ft): leczy żywych albo rani undead za 1d8 + modyfikator spellcasting.\n"
        "- 2 akcje (30 ft): leczy żywych albo rani undead za stałe 8 HP.\n"
        "- 3 akcje (fala 30 ft): efekt obszarowy; żywi są leczeni, undead otrzymują positive damage."
    ),
    "paladin": (
        "Cause czempiona nastawiony na kontruderzenie. "
        "Mechanika: reakcja czempiona redukuje obrażenia sojusznika o 2 + level czempiona, "
        "a jeśli napastnik jest w zasięgu, wykonujesz przeciw niemu Retributive Strike."
    ),
    "redeemer": (
        "Cause czempiona nastawiony na odkupienie i osłabianie agresji. "
        "Mechanika: reakcja czempiona redukuje obrażenia sojusznika o 2 + level czempiona; "
        "napastnik wybiera: zadaje 0 obrażeń albo otrzymuje Enfeebled 2 do końca swojej następnej tury."
    ),
    "liberator": (
        "Cause czempiona nastawiony na wyzwolenie i mobilność sojuszników. "
        "Mechanika: reakcja czempiona redukuje obrażenia sojusznika o 2 + level czempiona; "
        "sojusznik może Step i usuwa Grabbed/Restrained."
    ),
    "iomedae": (
        "Bogini honoru, prawa i sprawiedliwej walki. "
        "Mechanika: wybór bóstwa zapisuje champion_deity=iomedae i ustawia divine skill: Intimidation."
    ),
    "sarenrae": (
        "Bogini słońca, uzdrowienia i odkupienia. "
        "Mechanika: wybór bóstwa zapisuje champion_deity=sarenrae i ustawia divine skill: Medicine."
    ),
    "torag": (
        "Bóg krasnoludów, kuźnictwa i ochrony klanu. "
        "Mechanika: wybór bóstwa zapisuje champion_deity=torag i ustawia divine skill: Crafting."
    ),
    "shelyn": (
        "Bogini sztuki, miłości i piękna. "
        "Mechanika: wybór bóstwa zapisuje champion_deity=shelyn i pozwala wybrać divine skill: Crafting lub Performance."
    ),
    "desna": (
        "Bogini podróży, gwiazd i marzeń. "
        "Mechanika: wybór bóstwa zapisuje champion_deity=desna i ustawia divine skill: Acrobatics."
    ),
    "abadar": (
        "Bóg miast, handlu i porządku społecznego. "
        "Mechanika: wybór bóstwa zapisuje champion_deity=abadar i ustawia divine skill: Society."
    ),
    "custom": (
        "Własny patron czempiona ustalony przez gracza i MG. "
        "Mechanika: wybór bóstwa zapisuje champion_deity=custom i odblokowuje rozszerzoną listę skillów od bóstwa "
        "(Religion, Diplomacy, Intimidation, Medicine, Society, Athletics, Crafting)."
    ),
    "acidflask": "Bomba: obrażenia od kwasu + splash.",
    "alchemists_fire": "Bomba: obrażenia od ognia + splash/persistent.",
    "bottled_lightning": "Bomba: elektryczne obrażenia i efekt pomocniczy.",
    "frost_vial": "Bomba: zimno + spowolnienie celu.",
    "tanglefoot_bag": "Bomba: utrudnia ruch celu.",
    "smokestick": "Narzędzie alchemiczne: zasłona dymna i concealed w pobliżu.",
    "elixir_of_life": "Eliksir: leczenie celu.",
    "holy_water": "Consumable magic: rzut jak bomba, 1k6 good przeciw fiendom/nieumarłym.",
    "unholy_water": "Consumable magic: rzut jak bomba, 1k6 evil przeciw celestials.",
    "minor_healing_potion": "Mikstura: leczenie 1k8 HP po wypiciu.",
    "scroll_common_rank1": "Zwój: jednorazowe rzucenie wybranego czaru 1. rangi.",
    "potency_crystal": "Talizman: +1 item do ataku bronią do końca tury.",
    "cheetahs_elixir": "Eliksir: zwiększa prędkość.",
    "eagle_eye_elixir": "Eliksir: wspiera percepcję/zasięg wzroku.",
    "juggernaut_mutagen": "Mutagen: premie obronne kosztem innych statystyk.",
    "quicksilver_mutagen": "Mutagen: premie do ataku/zasięgu kosztem wytrzymałości.",
    "serene_mutagen": "Mutagen: premie mentalne kosztem fizycznych.",
    "cognitive_mutagen": "Mutagen: premie do testów wiedzy i intelektu.",
    "antidote": "Eliksir: premia przeciwko truciznom.",
    "antiplague": "Eliksir: premia przeciwko chorobom.",
    "arsenic": "Trucizna: nakłada stan poisoned przy porażce save.",
    "giant_centipede_venom": "Trucizna: stopniowe obrażenia i pogorszenie stanu celu.",
    "acrobatics": "Akrobatyka: balans, przeciskanie i ruchy wymagające zręczności.",
    "arcana": "Arkana: wiedza o magii arcane i zjawiskach magicznych.",
    "athletics": "Atletyka: wspinaczka, skoki, pływanie i siłowe testy ruchu.",
    "crafting": "Rzemiosło: tworzenie i naprawa przedmiotów.",
    "deception": "Oszustwo: blef, zmylenie i kamuflowanie intencji.",
    "diplomacy": "Dyplomacja: negocjacje, wywieranie dobrego wrażenia i mediacja.",
    "intimidation": "Zastraszanie: presja, groźby i wymuszanie reakcji.",
    "medicine": "Medycyna: leczenie, diagnoza i pierwsza pomoc.",
    "nature": "Natura: wiedza o przyrodzie, zwierzętach i terenie.",
    "occultism": "Okultyzm: wiedza o zjawiskach occult i tajemnych tradycjach.",
    "performance": "Występy: muzyka, taniec, aktorstwo i prezentacja sceniczna.",
    "religion": "Religia: wiedza o bogach, wierzeniach i rytuałach.",
    "society": "Społeczeństwo: wiedza o kulturze, prawie i strukturach społecznych.",
    "stealth": "Skradanie: ukrywanie się i ciche poruszanie.",
    "survival": "Przetrwanie: orientacja w terenie, tropienie i bytowanie poza cywilizacją.",
    "thievery": "Złodziejstwo: zamki, pułapki i zręczne manipulacje.",
    "acid_splash": (
        "Cantrip: 2 akcje, spell attack na 30 ft. "
        "Przy trafieniu zadajesz obrażenia acid; na krytyku dodatkowo nakładasz persistent acid "
        "(wartość podawana w promptcie)."
    ),
    "acidsplash": (
        "Cantrip: 2 akcje, spell attack na 30 ft. "
        "Przy trafieniu zadajesz obrażenia acid; na krytyku dodatkowo nakładasz persistent acid "
        "(wartość podawana w promptcie)."
    ),
    "chill_touch": (
        "Cantrip: 2 akcje, zasięg dotyk (5 ft). Cel robi Fortitude save vs Spell DC. "
        "Krytyczny sukces: 0 obrażeń. Sukces: połowa obrażeń negative. "
        "Porażka: pełne obrażenia i Enfeebled 1. Krytyczna porażka: podwójne obrażenia i Enfeebled 2."
    ),
    "dancing_lights": (
        "Cantrip: 2 akcje, wybierasz do 4 pól darkness/dim light w zasięgu 30 ft. "
        "Pola są rozjaśniane do końca walki."
    ),
    "daze": (
        "Cantrip: 2 akcje, cel w 60 ft robi Will save vs Spell DC. "
        "Krytyczny sukces: cel otrzymuje 1 mental damage. Sukces: połowa obrażeń mental. "
        "Porażka: pełne obrażenia mental. Krytyczna porażka: pełne obrażenia mental i Stunned 1."
    ),
    "detect_magic": (
        "Cantrip: 2 akcje, skanujesz magiczne aury w pomieszczeniu. "
        "Pokazuje wykryte obiekty w zasięgu (zależnie od poziomu), może ujawnić ukryte magiczne obiekty."
    ),
    "detectmagic": (
        "Cantrip: 2 akcje, skanujesz magiczne aury w pomieszczeniu. "
        "Pokazuje wykryte obiekty w zasięgu (zależnie od poziomu), może ujawnić ukryte magiczne obiekty."
    ),
    "disrupt_undead": (
        "Cantrip: 2 akcje, tylko przeciw undead w 30 ft. Cel robi Fortitude save vs Spell DC "
        "(basic save), a ty zadajesz positive damage."
    ),
    "divine_lance": (
        "Cantrip: 2 akcje, spell attack na 30 ft. Zadaje obrażenia alignmentu bóstwa castera "
        "tylko celom o przeciwnej aurze; przy krytyku obrażenia są podwajane."
    ),
    "electric_arc": (
        "Cantrip: 2 akcje, 1 lub 2 cele. Każdy cel robi Reflex save vs Spell DC (basic save) "
        "przeciw obrażeniom electric."
    ),
    "forbidding_ward": (
        "Cantrip: 2 akcje, wybierasz sojusznika i przeciwnika (30 ft). "
        "Sojusznik dostaje +1 status do AC i wszystkich save przeciw temu przeciwnikowi; "
        "ten przeciwnik dostaje -1 status do ataków przeciw wskazanemu sojusznikowi (1 tura)."
    ),
    "ghost_sound": (
        "Cantrip: 2 akcje, tworzysz fałszywy dźwięk na wybranym polu w 30 ft "
        "(np. szept, kroki, krzyk, stukot)."
    ),
    "guidance": (
        "Cantrip: 1 akcja, sojusznik w 30 ft dostaje +1 status do ataków i testów umiejętności "
        "na 1 turę."
    ),
    "know_direction": "Cantrip: 1 akcja, wskazuje kierunek prawdziwej północy.",
    "light": "Cantrip: 2 akcje, tworzysz aurę światła 30 ft wokół castera do końca walki.",
    "mage_hand": (
        "Cantrip: 2 akcje, interakcja z obiektem interactable (bez NPC) w zasięgu 30 ft."
    ),
    "message": (
        "Cantrip: 1 akcja, zdalna interakcja/rozmowa z celem typu NPC/interactable w zasięgu 120 ft."
    ),
    "prestidigitation": "Cantrip: 2 akcje, drobny efekt magiczny o charakterze opisowym.",
    "produce_flame": (
        "Cantrip: 2 akcje, spell attack ogniem (tryb melee 5 ft albo ranged 30 ft). "
        "Przy krytyku obrażenia są podwajane i nakładasz persistent fire (wartość z promptu)."
    ),
    "ray_of_frost": (
        "Cantrip: 2 akcje, spell attack na 120 ft. Zadajesz cold damage; "
        "na krytyku dodatkowo -10 ft Speed na 1 turę."
    ),
    "read_aura": (
        "Cantrip: 2 akcje, cel w 30 ft. Pokazuje aktualne statusy celu (odczyt aury)."
    ),
    "shield": (
        "Cantrip: 1 akcja, +1 circumstance do AC i absorpcja 5 obrażeń do początku następnej tury."
    ),
    "shield_cantrip": (
        "Cantrip: 1 akcja, +1 circumstance do AC i absorpcja 5 obrażeń do początku następnej tury."
    ),
    # --- Rank 1 spells (combat-relevant) ---
    "magic_missile": (
        "Ranga 1: 1 akcja, zasięg 120 ft. Automatyczne trafienie — 1 pocisk force 1d4+1. "
        "Za każdą kolejną akcję (do 3) — dodatkowy pocisk. Bez rzutu na atak, bez save."
    ),
    "burning_hands": (
        "Ranga 1: 2 akcje, stożek 15 ft. Fala ognia — Reflex save (basic). Trafieni otrzymują fire damage."
    ),
    "fear": (
        "Ranga 1: 2 akcje, zasięg 30 ft. Will save: sukces = brak; porażka = Frightened 1; "
        "krit. porażka = Frightened 2."
    ),
    "charm": (
        "Ranga 1: 2 akcje, zasięg 30 ft. Enchantment/mental. Will save: porażka = cel traktuje cię "
        "jako sojusznika przez 1 minutę."
    ),
    "sleep": (
        "Ranga 1: 2 akcje, zasięg 30 ft, obszar 5 ft burst. Will save: porażka = Slowed 1 (runda); "
        "krit. porażka = Unconscious."
    ),
    "mage_armor": (
        "Ranga 1: 2 akcje. Wzmacnia AC celu: ubrany w lekki/brak pancerza otrzymuje AC = 16 + Dex "
        "(lub więcej jeśli ma już lepszy). Czas trwania: do następnego przygotowania czarów."
    ),
    "color_spray": (
        "Ranga 1: 2 akcje, stożek 15 ft. Blask iluzji — Will save: porażka = Stunned 1 + Blinded 1 runda; "
        "krit. porażka = Stunned 2 + Blinded 1 minuta."
    ),
    "command": (
        "Ranga 1: 2 akcje, zasięg 30 ft. Will save: porażka = cel wykonuje jedną z wybranych akcji "
        "(Approach, Drop, Release, Run, Halt) w swojej turze."
    ),
    "ray_of_enfeeblement": (
        "Ranga 1: 2 akcje, zasięg 30 ft. Spell attack lub Fort save: trafienie = Enfeebled 2 (1 runda); "
        "Fort krit. sukces = brak efektu."
    ),
    "grease": (
        "Ranga 1: 2 akcje, zasięg 30 ft. Tworzy śliską powierzchnię 10 ft burst — wchodzący muszą zdać "
        "Reflex save lub Upadają. Czas trwania: 1 minuta."
    ),
    "shocking_grasp": (
        "Ranga 1: 2 akcje, zasięg dotyk (5 ft). Spell attack elektrycznym: basic Reflex save. "
        "Metalowa zbroja: +1d6 do obrażeń i target jest Flat-footed."
    ),
    "hydraulic_push": (
        "Ranga 1: 2 akcje, zasięg 60 ft. Atak wodą — Reflex save (basic). Krit. porażka: odpychany 10 ft."
    ),
    "goblin_pox": (
        "Ranga 1: 2 akcje, zasięg 30 ft. Fort save: porażka = Sickened 1 + persistent poison 1d4; "
        "krit. porażka = Sickened 2 + persistent poison 1d6."
    ),
    "bane": (
        "Ranga 1: 2 akcje. Aura 10 ft. Wrogowie w zasięgu muszą zdać Will save lub dostają "
        "-1 status do ataków. Czas trwania: do 1 minuty (wymaga Sustain)."
    ),
    "bless": (
        "Ranga 1: 2 akcje. Aura 10 ft. Sojusznicy w zasięgu otrzymują +1 status do ataków. "
        "Czas trwania: do 1 minuty (wymaga Sustain)."
    ),
    "longstrider": (
        "Ranga 1: 2 akcje, zasięg dotyk. Cel otrzymuje +10 ft Status do Speed. "
        "Czas trwania: 1 godzina."
    ),
    "mage_hand": (
        "Ranga 1 (też Cantrip): 2 akcje, zasięg 30 ft. Telekinetycznie manipulujesz przedmiotem "
        "do Bulk 1 (opisowe)."
    ),
    "harm": (
        "Ranga 1: 1–3 akcje, zasięg 30 ft. Negative damage: rani żywych, leczy undead. "
        "Za więcej akcji — większy zasięg lub obszar (burst)."
    ),
    "heal": (
        "Ranga 1: 1–3 akcje, zasięg 30 ft. Positive energy: leczy żywych, szkodzi undead. "
        "1 akcja = dotyk (1d8+modifier); 2 akcje = 30 ft; 3 akcje = burst 30 ft."
    ),
    "magic_weapon": (
        "Ranga 1: 2 akcje, zasięg dotyk. Broń celu staje się +1 striking do końca starcia (1 minuta)."
    ),
    "true_strike": (
        "Ranga 1: 1 akcja. Następny atak przed końcem tury traktuj jako dwa rzuty — wybierz lepszy "
        "(ignore MAP for first attack after this)."
    ),
    "spider_sting": (
        "Ranga 1: 2 akcje, zasięg dotyk. Fort save: porażka = 1d4 poison + Enfeebled 1 (1 minuta); "
        "krit. porażka = 1d4 poison + Enfeebled 2."
    ),
    "pass_without_trace": (
        "Ranga 1: 2 akcje, zasięg 30 ft. Cel otrzymuje +4 circumstance do Stealth i nie zostawia śladów. "
        "Czas trwania: 10 minut."
    ),
    "phantom_pain": (
        "Ranga 1: 2 akcje, zasięg 30 ft. Will save: porażka = mental illusory damage + Sickened 1."
    ),
    "summon_animal": (
        "Ranga 1: 3 akcje, zasięg 30 ft. Przywołujesz zwierze (opisowe, DM zarządza stworzeniem)."
    ),
    # --- Focus spells ---
    "inspire_courage": (
        "Focus cantrip: 1 akcja, zasięg 60 ft (emanacja). Sojusznicy w zasięgu: +1 do ataków, "
        "+1 do obrażeń i damage rolls, +1 do save vs fear. Czas trwania: do początku następnej tury."
    ),
    "inspire_competence": (
        "Focus cantrip: 1 akcja, zasięg 30 ft. 1 sojusznik: +1 status do testów umiejętności. "
        "Czas trwania: do początku następnej tury."
    ),
    "tempest_surge": (
        "Focus: 2 akcje, zasięg 30 ft. Fala burzy — Reflex save (basic). "
        "Porażka = electricity damage + Clumsy 2 + persistent electricity."
    ),
    "wild_shape": (
        "Focus: 2 akcje. Druid: przemiana w zwierze (lista dostępnych form zależy od feats). "
        "Czas trwania: 1 minuta."
    ),
    "goodberry": (
        "Focus: 2 akcje. Tworzysz do 4 magicznych jagód. Każda w ciągu dnia leczy 1d6+4 HP "
        "i usuwa efekty chorób (opisowe)."
    ),
    "heal_animal": (
        "Focus: 1–3 akcje. Leczy zwierze (jak heal ale tylko zwierzęta). "
        "1 akcja = dotyk 1d8; 2 akcje = 30 ft 1d8; 3 akcje = burst."
    ),
    "sigil": (
        "Cantrip: 2 akcje, oznaczasz cel (hero/enemy/interactable) w 30 ft magicznym znakiem."
    ),
    "stabilize": (
        "Cantrip: 2 akcje, cel w 30 ft. Jeśli cel ma status dying, usuwa dying i stabilizuje cel."
    ),
    "tanglefoot": (
        "Cantrip: 2 akcje, spell attack na 30 ft. Trafiony cel dostaje -10 ft Speed na 1 turę; "
        "na krytyku dodatkowo Immobilized 1."
    ),
    "telekinetic_projectile": (
        "Cantrip: 2 akcje, spell attack na 30 ft. Zadajesz obrażenia wybranego typu "
        "(bludgeoning, piercing albo slashing)."
    ),
    "additional_lore": "General feat: dodatkowe trained w wybranej specjalizacji Lore.",
    "alchemical_crafting": "General feat: pozwala tworzyć przedmioty alchemiczne.",
    "arcane_sense": "General feat: Detect Magic jako arcane innate cantrip.",
    "combat_climber": "General feat: wsparcie walki podczas wspinaczki (częściowo opisowe).",
    "experienced_professional": "General feat: bezpieczniejszy Earn Income na Lore (opisowe).",
    "fast_recovery": "General feat: szybsze leczenie i lepsza walka z poison/disease.",
    "feather_step": "General feat: Step w difficult terrain (opisowe).",
    "fleet": "General feat: zwiększa bazową prędkość o 5 stóp.",
    "group_coercion": "General feat: Coerce wielu celów (opisowe).",
    "toughness": "General feat: zwiększa wytrzymałość i poprawia przeżywalność.",
    "bardic_lore": "Feat barda: Bardic Lore daje trained, uniwersalne Recall Knowledge; gra może automatycznie użyć lepszego modyfikatora.",
    "lingering_composition": "Feat barda: akcja za 1 Focus Point, która wydłuża następny composition cantrip; zwiększa też Focus Pool o 1.",
    "versatile_performance": "Feat barda: wybrane akcje społeczne możesz wykonywać przez Performance.",
    "true_strike": "Czar 1 rangi: przy następnym ataku rzucasz 2k20 i wybierasz lepszy wynik.",
    "soothe": "Czar 1 rangi: leczy cel i wzmacnia obronę przed efektami mentalnymi.",
    "unseen_servant": "Czar 1 rangi: przyzywa niewidzialnego sługę do prostych interakcji.",
    "assurance": "General feat: zapewnia stały wynik dla wybranej umiejętności.",
    "skill_training": "General feat: daje trained w dodatkowej umiejętności.",
    "quick_identification": "General feat: szybsze Identify Magic (opisowe).",
    "quick_repair": "General feat: szybsza akcja Repair (opisowe).",
    "quick_squeeze": "General feat: szybsze Squeeze (opisowe).",
    "read_lips": "General feat: czytanie z ruchu warg (opisowe).",
    "ride": "General feat: sprawniejsze dowodzenie wierzchowcem (opisowe).",
    "sign_language": "General feat: znajomość języków migowych.",
    "snare_crafting": "General feat: tworzenie sideł.",
    "subtle_theft": "General feat: trudniej zauważyć twoją kradzież (opisowe).",
    "terrain_stalker": "General feat: skradanie w wybranym trudnym terenie (opisowe).",
    "titan_wrestler": "General feat: manewry przeciw dużym celom.",
    "virtuosic_performer": "General feat: bonus do wybranego typu Performance.",
}


def localize_term_pl(value: str | None) -> str:
    raw = _normalize(value)
    if not raw:
        return ""
    direct = _LABELS_PL.get(raw)
    if direct:
        return direct
    if raw.endswith("_lore"):
        prefix = raw[: -len("_lore")]
        if prefix:
            return f"{localize_term_pl(prefix)} (Wiedza)"
    text = str(value or "").replace("_", " ").replace("-", " ").strip()
    if not text:
        return ""
    return text.title()


def _normalize_hint_format(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    parts = [part.strip() for part in re.split(r"\s*\|\s*", text) if part.strip()]
    if len(parts) <= 1:
        return text
    return "\n".join([parts[0]] + [f"- {part}" for part in parts[1:]])


def localized_hint_pl(value: str | None) -> str:
    raw = _normalize(value)
    if not raw:
        return ""
    return _normalize_hint_format(_HINTS_PL.get(raw, ""))

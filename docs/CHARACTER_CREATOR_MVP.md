# Character Creator MVP

## Product goal

The milestone ends with a complete playable loop using custom level-1 characters:

```text
Main menu
  -> New game
  -> Scenario selection
  -> Party selection (1-5 saved characters)
  -> Existing scenario setup
  -> Play the MVP scenario with the selected party

Main menu
  -> Create character
  -> Character creator
  -> Save character
  -> Saved-character roster
```

The character creator is a separate application module. It produces the same
actor model consumed by exploration, combat, inventory, spellcasting, rest and
scenario handoff. Scenario content must not need a custom copy of a player actor.

Multiclassing is outside this milestone. A character has exactly one class.

## Runtime surfaces

### Main menu

- `New game` starts scenario selection.
- `Load game` lists compatible session saves.
- `Create character` opens the character module.
- `Settings` and `Exit` may initially remain thin platform actions.

### New game

1. Select a scenario. The current MVP route starts with the village scenario and
   continues to the abandoned watchtower through the existing handoff.
2. Select between one and five saved characters.
3. Validate scenario level/party requirements without prescribing party
   composition.
4. Start the existing board and paper-map setup with the selected actors.

### Character creator

The level-1, single-class flow contains:

1. identity: name and player-facing description,
2. species,
3. class,
4. background,
5. ability scores,
6. proficiencies and other allowed choices,
7. equipment and spells when applicable,
8. appearance/portrait and final review.

Choices and grants must be data-driven. The UI does not calculate D&D rules;
the character-creation domain validates choices and derives the final actor.

## Architecture boundary

New deterministic code belongs under:

```text
src/dnd_board_game/character_creation/
```

It owns drafts, available choices, grants, validation and actor construction.
It must not depend on Flask, the board, Gemini, files or real time.

Content belongs in versioned catalogues under `content/`, with stable IDs for:

- species and their grants,
- classes and level-1 grants,
- backgrounds and their grants,
- starting-equipment choice groups,
- spellcasting choices,
- portrait metadata.

The launcher/menu, roster and creator presentation belong under
`src/dnd_board_game/ui/`. Saved characters use an explicit versioned document
separate from scenario/session saves.

## Implementation status

The K1 domain foundation is implemented:

- versioned character catalogue v1,
- four initial species, classes and backgrounds,
- level-1 standard-array validation,
- class skill, equipment and spell choice validation,
- deterministic HP, base AC, proficiency, senses, inventory, currency, spell
  slots, spell DC and preparation construction,
- saved-character schema v4 which persists source choices, XP and flexible
  species ability bonuses, and migrates v2/v3,
  and rebuilds `Actor`,
- repository content-audit coverage.

The first executable grant slice is implemented:

- Fighter chooses Defense, Archery, Dueling or Two-Weapon Fighting,
- Second Wind uses the shared bonus-action, healing and short-rest resource rules,
- Rogue chooses two owned skill proficiencies for Expertise,
- Sneak Attack validates its weapon, roll mode, adjacent ally and once-per-turn use,
- human ability bonuses, elf Perception/darkvision, and dwarf darkvision, poison
  resistance and heavy-armor speed exception are active,
- cantrip access, cleric class-list access, wizard spellbook membership and
  prepared spells are separate choices,
- Life Domain grants heavy-armor proficiency, always-prepared domain spells and
  executable Disciple of Life healing,
- Arcane Recovery is a long-rest resource that restores a legal depleted slot
  after a short rest,
- Halfling Lucky uses an explicit physical reroll contract for every natural
  one on an attack, check or save,
- Brave, Fey Ancestry and Dwarven Resilience grant tagged save advantage, while
  Fey Ancestry also exposes magical-sleep immunity,
- Halfling Nimbleness participates in shared occupied-tile pathfinding,
- Trance exposes a four-hour individual long-rest requirement,
- Stonecunning applies double proficiency only to authored `stonework` checks,
- background features expose stable permissions which require both the actor
  grant and an authored scene opportunity.

The dedicated player-facing follow-up form for physical Lucky rerolls remains
part of the character-creator UI integration. The transport and deterministic
runtime contracts already accept and validate those rerolls.

The launcher shell is also implemented:

- `/` opens a keyboard- and mouse-friendly main menu,
- `/new-game` shows the active scenario and starts it from a clean state,
- `/load-game` exposes only the compatible snapshot for the active scenario and
  validates it through the existing snapshot loader before entering play,
- `/characters` is a separate catalogue-backed character-module entry screen,
- the board-first exploration/combat runtime now lives at `/play`,
- the normal runtime defaults to the village scenario so the existing
  village-to-watchtower continuation remains the reference campaign path.

The persistent roster flow is implemented:

- a generic form exposes the choices authored by every catalogue class instead
  of branching on hard-coded class names,
- submission constructs a `CharacterDraft`, returns field-oriented domain
  validation messages, and writes only a fully built character,
- `/characters` lists compatible records rebuilt from their source choices,
- a saved character can be reopened and used to prefill an independent copy,
- duplicate ids and path traversal are rejected,
- deletion moves a record to `data/characters/.trash/` rather than destroying it,
- malformed or incompatible records are isolated and reported without blocking
  the rest of the roster.

New Game zawiera działający wybór od jednej do pięciu zapisanych postaci.
Wybrana drużyna zastępuje wyłącznie scenariuszowe szablony bohaterów; NPC,
przeciwnicy, setup mapy i content scenariusza pozostają własnością scenariusza.
Tożsamość, portrety, statystyki, zasoby, czary, ekwipunek i XP własnych postaci
przechodzą przez walkę, snapshot oraz handoff village-to-watchtower.

## MVP content slice

Zakres implementacji obejmuje:

- dziewięć głównych species SRD wraz z wariantami/ancestry występującymi w SRD,
- wszystkie dwanaście klas i po jednej subclassie SRD do poziomu 3,
- soldier, criminal, acolyte and sage,
- standard-array ability scores,
- authored starting equipment choices,
- wybór cantripów, czarów poziomu 1–2, przygotowania, spellbook i Pact Magic,
- XP, osobny awans 1→2→3 oraz wymagane wybory level-up,
- local portrait selection.

Katalogi pozostają rozszerzalne bez dodawania klasowych gałęzi do formularza.
Jawny audyt implementacji odrzuca każdą nową cechę bez przypisanego kontraktu
wykonawczego albo udokumentowanego wyjątku stołowego.

## Definition of Done

The milestone is complete when:

- the application opens on the main menu;
- `New game`, `Load game` and `Create character` lead to separate working flows;
- a player can create, validate, save, reopen, edit-as-copy and delete a level-1
  single-class character;
- invalid or incomplete choices cannot produce a playable actor and are
  explained in player-facing language;
- derived HP, AC, proficiency bonus, saves, skills, attacks, inventory, currency,
  spellcasting and resource pools match the deterministic rules;
- new-game setup allows one to five saved characters and rejects duplicates;
- the chosen party replaces scenario-authored player templates while NPCs and
  enemies remain scenario-owned;
- custom portraits and names appear in party, exploration, combat, rest, loot,
  save/load and scenario-handoff screens;
- a custom party can complete the village-to-watchtower MVP route from beginning
  to end;
- character and session save schemas are versioned and covered by round-trip and
  compatibility tests;
- content audit and focused unit/integration tests pass;
- no multiclass controls, data model or rules are required for this milestone.

## UI references

The generated screens are direction references, not pixel-perfect implementation
specifications. `KRONIKI POGRANICZA` is a working mockup title, not a final
product-name decision.

- `assets/ui_reference/character_creator_mvp/01_main_menu.png`
- `assets/ui_reference/character_creator_mvp/02_scenario_selection.png`
- `assets/ui_reference/character_creator_mvp/03_party_selection.png`
- `assets/ui_reference/character_creator_mvp/04_character_creator_class.png`
- `assets/ui_reference/character_creator_mvp/05_character_creator_summary.png`

Visual direction:

- original classic party-RPG atmosphere rather than a copy of another game,
- dark iron, aged wood, leather and parchment,
- antique-gold focus and selection states,
- cinematic backgrounds kept secondary to readable controls,
- explicit progress, validation and primary actions,
- full keyboard and mouse usability with a responsive fallback.

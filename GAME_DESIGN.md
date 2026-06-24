# Game Design

The new game is a board-assisted Dungeons & Dragons 5e tactical encounter app.

This is not a full virtual tabletop at first. The first version should focus on a tight encounter loop that works well with the physical board and LEDs.

## Core Loop

1. Load or create an encounter.
2. Place player characters, monsters, and interactables on the board.
3. Roll or assign initiative.
4. On each turn:
   - show active actor,
   - choose movement/action/bonus action/reaction where relevant,
   - use board scan or UI input for target/position choices,
   - resolve the rule outcome,
   - update board LEDs and game state.
5. End encounter and save summary/state.

## D&D 5e Baseline

Initial mechanics should be intentionally small:

- ability scores and modifiers,
- proficiency bonus,
- armor class,
- hit points and temporary hit points,
- speed in feet,
- initiative,
- attack rolls,
- saving throws,
- ability checks,
- damage and healing,
- advantage/disadvantage,
- conditions placeholder.

Do not implement all D&D 5e rules at once.

## Actor Model

Player characters:

- name,
- level,
- class placeholder,
- ability scores,
- proficiency bonus,
- armor class,
- hit points,
- speed,
- position,
- actions known or available.

Monsters:

- name,
- stat block id,
- armor class,
- hit points,
- speed,
- ability modifiers or scores,
- attacks/actions,
- position,
- behavior placeholder.

NPCs:

- TODO.

## Board Model

- Physical board size: 20 columns x 30 rows.
- Coordinates are `(col, row)`.
- Movement uses 5 ft squares.
- Terrain, walls, blockers, doors, and interactables should be modeled separately from actors.
- Pathfinding should be pure and tested before being connected to hardware.

## LED Design

Use LEDs for fast table feedback:

- active actor,
- valid movement area,
- selected path,
- attack target options,
- area-of-effect templates,
- hit/miss/damage/healing feedback,
- setup markers.

LED effects should be generated as frame data first, then played through a hardware adapter.

## Non-Goals For First Version

- Full D&D character builder.
- Complete spell catalog.
- Complete monster catalog.
- Networked multiplayer.
- Complex campaign management.
- Rebuilding the old Pathfinder UI unchanged.

# Player UI Bandit Cave - lista elementow do grafik

Plik zbiera elementy graficzne z `player_ui` oraz `assets/ui_v2/bandit_cave`, ktore warto przerobic z roboczych assetow na finalniejsze grafiki dla scenariusza `bandit_cave`.

Zalozenia dla wszystkich promptow:
- docelowy format dla grafik AI: `.png`,
- dla ikon, portretow i tokenow eksportuj przezroczyste tlo, jesli prompt nie mowi inaczej,
- nazwy plikow ponizej pasuja do katalogu `assets/ui_v2/bandit_cave/images/`,
- klimat: fantasy PF2e, bandycka jaskinia, kontrabanda, podziemne doki,
- styl: czytelna ilustracja tabletop fantasy, malarska, ale bez przesadnego realizmu i bez komiksowej karykatury,
- Player UI ma byc czytelne przy stole, wiec sylwetki, kontrast i gest musza byc jasne juz w malym rozmiarze,
- bez tekstu, liter, logo, znakow wodnych i UI w samej grafice,
- bez gore, horroru i nadmiernej brutalnosci,
- trzymaj spojny kierunek artystyczny: mokry kamien, chlodne swiatlo jaskini, cieple lampy/pochodnie, zuzyta skora, drewno, zelazo i lina.

Workflow generowania:
- `images/enemies/*`: generuj jako portret/token postaci na przezroczystym tle, najlepiej kwadrat 1024x1024. Postac ma zajmowac 80-90% kadru.
- `images/characters/*`: generuj jako portret narracyjny lub symbol postaci na przezroczystym tle, kwadrat 1024x1024.
- `images/actions/*` i `images/spells/*`: generuj jako ikony na przezroczystym tle, kwadrat 512x512 lub 1024x1024. Ikona musi byc czytelna po zmniejszeniu.
- `images/placeholders/*`: generuj neutralne fallbacki bez konkretnej postaci, kwadrat 512x512 lub 1024x1024.
- `images/scenes/*`: jesli dodamy ilustracje rozdzialow albo tlo briefingu, generuj 16:9, najlepiej 1920x1080. Bez tekstu i bez ramki.
- Obecny manifest wskazuje glownie pliki `.svg`. Ten dokument zaklada przygotowanie finalnych `.png`; po akceptacji mozna podmienic sciezki w `assets/ui_v2/bandit_cave/manifest.json`.

## Priorytet MVP - sceny rozdzialow

### 1. Scena: wejscie do jaskini
- Zrodlo tekstu: `player_ui/content/bandit_cave.json` -> rozdzial `Cave Entrance`
- Proponowany plik: `images/scenes/cave_entrance.png`
- Typ: scene background
- Format: 16:9, 1920x1080, bez tekstu
- Prompt:

```text
Fantasy tabletop RPG scene, entrance to a bandit cave hidden in a wet rocky hillside, muddy tracks leading into a dark tunnel, crates and old rope near the mouth of the cave, faint warm torchlight deeper inside, cold blue-grey daylight outside, tense but not horror. Painterly semi-realistic style, clear readable composition for a player UI background, no characters in the foreground, no text, no logo, no border.
```

### 2. Scena: ukryty skarbiec
- Zrodlo tekstu: `player_ui/content/bandit_cave.json` -> rozdzial `Treasure Room`
- Proponowany plik: `images/scenes/treasure_room.png`
- Typ: scene background
- Format: 16:9, 1920x1080, bez tekstu
- Prompt:

```text
Hidden bandit treasure room inside a cave, stacked wooden crates, sealed smuggler bundles, damp barrels, scattered ledgers and transport papers, one suspiciously neat chest suggesting a trap, rough stone walls with moisture and torchlight. Fantasy tabletop RPG illustration, painterly semi-realistic, readable for a player UI chapter image, warm amber light against cool stone shadows, no people, no text, no logo, no border.
```

### 3. Scena: podziemne doki przemytnikow
- Zrodlo tekstu: `player_ui/content/bandit_cave.json` -> rozdzial `Smuggler Docks`
- Proponowany plik: `images/scenes/smuggler_docks.png`
- Typ: scene background
- Format: 16:9, 1920x1080, bez tekstu
- Prompt:

```text
Underground smuggler docks inside a large cave, dark water reflecting lantern light, a small smuggler boat tied to a wooden pier, ropes, crates and cargo bundles on wet planks, stone tunnel in the background. Fantasy tabletop RPG scene, tense finale mood, painterly semi-realistic, strong readable shapes for player UI, cool water shadows with warm lantern accents, no text, no logo, no border.
```

## Priorytet MVP - przeciwnicy i postacie

### 4. Przeciwnik: Bandit
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `enemies.bandit`
- Obecny plik: `images/enemies/bandit.svg`
- Proponowany plik: `images/enemies/bandit.png`
- Typ: enemy token / portrait
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Full body fantasy bandit token on transparent background, rugged cave smuggler with leather armor, short sword, worn cloak, belt pouches and practical boots, cautious aggressive stance. Grounded tabletop RPG style, painterly semi-realistic, readable silhouette, muted browns and greys with small warm torch highlights, no blood, no text, no logo.
```

### 5. Przeciwnik: Bandit Sharpshot
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `enemies.bandit_sharpshot`
- Obecny plik: `images/enemies/bandit_sharpshot.svg`
- Proponowany plik: `images/enemies/bandit_sharpshot.png`
- Typ: enemy token / portrait
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Full body fantasy bandit sharpshooter token on transparent background, lean cave smuggler with a crossbow held ready, hooded leather armor, wrapped forearms, quiver of bolts, alert watchman posture. Painterly semi-realistic tabletop RPG style, sharp readable silhouette, cool cave shadows and subtle warm lantern rim light, no blood, no text, no logo.
```

### 6. Przeciwnik: Guard Dog / Cave Hound
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `enemies.guard_dog`
- Obecny plik: `images/enemies/guard_dog.svg`
- Proponowany plik: `images/enemies/guard_dog.png`
- Typ: enemy token / portrait
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Full body cave guard dog token on transparent background, muscular trained hound with rough dark fur, leather collar, alert stance, ears forward, guarding a smuggler cave. Fantasy tabletop RPG style, painterly semi-realistic, readable silhouette, tense but natural animal pose, no gore, no text, no logo.
```

### 7. Postac: Narrator / Mistrz gry
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `characters.narrator`
- Obecny plik: `images/characters/narrator.svg`
- Proponowany plik: `images/characters/narrator.png`
- Typ: character portrait
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Symbolic fantasy game master narrator portrait on transparent background, hooded figure holding an open travel journal and a small lantern, face mostly in soft shadow, calm guiding presence, cave-smuggler adventure mood. Painterly tabletop RPG style, readable at small size, warm lantern light against cool stone tones, no text, no logo.
```

### 8. NPC: Marek "Lina" Voss
- Zrodlo tekstu: `scenarios/bandit_cave_smuggler_docks.json` -> NPC `bound_smuggler_npc`
- Proponowany plik: `images/characters/marek_voss.png`
- Typ: NPC portrait / token
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Fantasy smuggler NPC token on transparent background, wiry man named Marek Voss, bound hands with rope, damp patched coat, nervous clever expression, dockworker-smuggler look, standing near imaginary cave docks. Painterly semi-realistic tabletop RPG style, readable silhouette, restrained palette of wet browns, greys and lantern gold, no text, no logo.
```

## Akcje UI

### 9. Akcja: Stride / Ruch
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `actions.stride`
- Obecny plik: `images/actions/stride.svg`
- Proponowany plik: `images/actions/stride.png`
- Typ: action icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Clean fantasy RPG action icon on transparent background, bootprint stepping across damp cave stone, subtle motion direction, simple bold silhouette, painterly texture, readable at small size, cool grey stone with warm tan highlight, no text, no logo.
```

### 10. Akcja: Strike / Attack
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `actions.strike`, `actions.attack`
- Obecny plik: `images/actions/strike.svg`
- Proponowany plik: `images/actions/strike.png`
- Typ: action icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Clean fantasy RPG combat action icon on transparent background, diagonal sword slash with a small spark on rough steel, bold readable shape, painterly but simple, cave-smuggler palette of iron grey and muted amber, no blood, no text, no logo.
```

### 11. Akcja: Interact
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `actions.interact`
- Obecny plik: `images/actions/interact.svg`
- Proponowany plik: `images/actions/interact.png`
- Typ: action icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Clean fantasy RPG interaction icon on transparent background, gloved hand reaching toward a small lever or crate latch, simple readable silhouette, subtle cave light, painterly texture, practical smuggler equipment mood, no text, no logo.
```

### 12. Akcja: Seek
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `actions.seek`
- Obecny plik: `images/actions/seek.svg`
- Proponowany plik: `images/actions/seek.png`
- Typ: action icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Clean fantasy RPG search action icon on transparent background, vigilant eye combined with a small lantern beam revealing a crack in cave stone, simple strong silhouette, painterly texture, cool shadows and warm lantern accent, readable at small size, no text, no logo.
```

### 13. Akcja: End Turn
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `actions.end`
- Obecny plik: `images/actions/end_turn.svg`
- Proponowany plik: `images/actions/end_turn.png`
- Typ: action icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Clean fantasy RPG end turn icon on transparent background, small wooden game marker resting beside a simple hourglass shape, calm completed-action feeling, bold readable silhouette, painterly tabletop texture, muted cave palette, no text, no logo.
```

### 14. Akcja: Raise Shield / Defend
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `actions.raise_shield`
- Obecny plik: `images/actions/defend.svg`
- Proponowany plik: `images/actions/defend.png`
- Typ: action icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Clean fantasy RPG defense action icon on transparent background, raised battered wooden shield with iron rim catching a faint torch highlight, simple bold silhouette, painterly texture, readable at small size, no text, no logo.
```

### 15. Akcja fallback: Default Action
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `fallbacks.action`
- Obecny plik: `images/actions/default_action.svg`
- Proponowany plik: `images/actions/default_action.png`
- Typ: fallback action icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Neutral fantasy RPG action icon on transparent background, small bronze action marker with three subtle notches, tabletop token feel, simple readable silhouette, painterly texture, muted metal and cave-shadow palette, no text, no logo.
```

## Czary

### 16. Czar: Acid Splash
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `spells.acid_splash`
- Obecny plik: `images/spells/acid_splash.svg`
- Proponowany plik: `images/spells/acid_splash.png`
- Typ: spell icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Clean fantasy spell icon on transparent background, splash of glowing green acid striking dark cave stone, small droplets and vapor, bold readable silhouette, painterly texture, no gore, no text, no logo.
```

### 17. Czar: Electric Arc
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `spells.electric_arc`
- Obecny plik: `images/spells/electric_arc.svg`
- Proponowany plik: `images/spells/electric_arc.png`
- Typ: spell icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Clean fantasy spell icon on transparent background, bright blue-white electric arc jumping between two small stone points, bold readable lightning shape, painterly energy, cave shadow contrast, no text, no logo.
```

### 18. Czar: Heal
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `spells.heal`
- Obecny plik: `images/spells/heal.svg`
- Proponowany plik: `images/spells/heal.png`
- Typ: spell icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Clean fantasy healing spell icon on transparent background, warm golden light wrapping around a simple open hand and small leaf-like glow, calm restorative feeling, bold readable silhouette, painterly texture, no medical symbol, no text, no logo.
```

### 19. Czar: Magic Missile
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `spells.magic_missile`
- Obecny plik: `images/spells/magic_missile.svg`
- Proponowany plik: `images/spells/magic_missile.png`
- Typ: spell icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Clean fantasy spell icon on transparent background, three violet-blue arcane darts streaking forward with subtle trails, bold readable composition, painterly magical light, cave shadow contrast, no text, no logo.
```

### 20. Czar fallback: Cantrip
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `spells.cantrip`
- Obecny plik: `images/spells/cantrip.svg`
- Proponowany plik: `images/spells/cantrip.png`
- Typ: fallback spell icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Neutral fantasy cantrip icon on transparent background, small simple spark above a stone rune chip, low-level magic feeling, bold readable silhouette, painterly texture, muted blue and amber light, no text, no logo.
```

### 21. Czar fallback: Focus Spell
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `spells.focus`
- Obecny plik: `images/spells/focus.svg`
- Proponowany plik: `images/spells/focus.png`
- Typ: fallback spell icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Neutral fantasy focus spell icon on transparent background, concentrated glowing point inside a small circular charm, subtle energy rings, bold readable silhouette, painterly texture, cave palette with one bright magical accent, no text, no logo.
```

### 22. Czar fallback: Rank 1 Spell
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `spells.rank_1`
- Obecny plik: `images/spells/rank_1.svg`
- Proponowany plik: `images/spells/rank_1.png`
- Typ: fallback spell icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Neutral fantasy first-rank spell icon on transparent background, one polished rune stone emitting a modest magical glow, simple readable silhouette, painterly texture, restrained tabletop RPG style, no number, no text, no logo.
```

### 23. Czar fallback: Default Spell
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `fallbacks.spell`
- Obecny plik: `images/spells/default_spell.svg`
- Proponowany plik: `images/spells/default_spell.png`
- Typ: fallback spell icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Neutral fantasy spell icon on transparent background, small arcane sigil painted on a stone shard with faint glow, generic magic symbol, bold readable silhouette, painterly texture, muted cave colors, no text, no logo.
```

## Fallbacki i elementy ogolne

### 24. Fallback: Default Actor
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `fallbacks.actor`
- Obecny plik: `images/placeholders/default_actor.svg`
- Proponowany plik: `images/placeholders/default_actor.png`
- Typ: placeholder icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Neutral fantasy tabletop actor placeholder on transparent background, simple hooded adventurer silhouette with no specific identity, soft cave rim light, painterly texture, readable at small size, no facial detail, no text, no logo.
```

### 25. Fallback: Default Choice
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `fallbacks.choice`
- Obecny plik: `images/placeholders/default_choice.svg`
- Proponowany plik: `images/placeholders/default_choice.png`
- Typ: placeholder choice icon
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Neutral fantasy tabletop choice icon on transparent background, forked path marker made from two small wooden arrows on cave stone, simple readable silhouette, painterly texture, muted browns and greys, no text, no logo.
```

### 26. Fallback: Default Enemy
- Zrodlo: `assets/ui_v2/bandit_cave/manifest.json` -> `fallbacks.enemy`
- Obecny plik: `images/enemies/default_enemy.svg`
- Proponowany plik: `images/enemies/default_enemy.png`
- Typ: placeholder enemy token
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Neutral fantasy enemy placeholder token on transparent background, anonymous hostile silhouette holding a simple weapon, cave shadow rim light, painterly semi-realistic tabletop style, strong readable shape, no gore, no text, no logo.
```

## Interactable / lokacyjne assety do dodania

### 27. Sekretne przejscie
- Zrodlo tekstu: `scenarios/bandit_cave_cave_entrance.json` -> exit `secret_treasure`
- Proponowany plik: `images/interactables/secret_passage.png`
- Typ: interactable icon / object
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Fantasy cave interactable icon on transparent background, loose stone slab shifted aside to reveal a narrow dark passage, subtle lantern light catching the edge, clear readable object silhouette, painterly texture, no characters, no text, no logo.
```

### 28. Skryta kontrabanda
- Zrodlo tekstu: `scenarios/bandit_cave_treasure_room.json` -> `hidden_cache`
- Proponowany plik: `images/interactables/hidden_cache.png`
- Typ: interactable icon / object
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Fantasy smuggler cache icon on transparent background, false wooden panel opened to reveal sealed packets, ledger, small coin pouch and contraband bundles, cave treasure room mood, painterly tabletop style, readable at small size, no text, no logo.
```

### 29. Pulapka skarbca
- Zrodlo tekstu: `scenarios/bandit_cave_treasure_room.json` -> `trap_tile`
- Proponowany plik: `images/interactables/trap_tile.png`
- Typ: interactable icon / object
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Fantasy cave trap icon on transparent background, suspicious stone pressure plate with tiny needle slot and faint metal glint, subtle warning mood, painterly texture, clear readable top-down object shape, no blood, no text, no logo.
```

### 30. Statek przemytnikow
- Zrodlo tekstu: `scenarios/bandit_cave_smuggler_docks.json` -> exit `escape_ship`
- Proponowany plik: `images/interactables/smuggler_ship.png`
- Typ: interactable icon / object
- Format: kwadrat, przezroczyste tlo
- Prompt:

```text
Fantasy smuggler boat icon on transparent background, small wooden boat tied with rope, crates and tarp-covered cargo inside, wet planks and lantern glow implied, painterly tabletop style, strong readable silhouette, no people, no text, no logo.
```

## Negatywny prompt wspolny

Uzywaj tego jako dodatkowego negatywnego promptu, jesli narzedzie go obsluguje:

```text
text, letters, logo, watermark, UI frame, modern clothing, firearms, sci-fi elements, cartoon mascot, chibi, excessive gore, horror monster, blurry composition, low contrast, tiny unreadable subject, extra limbs, duplicated weapon, cropped head, decorative border
```

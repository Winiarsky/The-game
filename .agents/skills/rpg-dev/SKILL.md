---
name: rpg-dev
description: Collaboratively develop tabletop RPG adventures — premise, NPCs, and scenes — and capture them as a durable Markdown file. Use when the user wants to design an adventure, module, one-shot, or session; develop a premise, scene, or NPC; or mentions running/prepping a game.
---

# RPG Dev — Adventure Creation

Build an adventure *with* the user, one layer at a time, and persist it to a single
Markdown file. Never dump a finished adventure from one prompt — interview, propose,
and confirm at each layer.

## Start with the context stack

An adventure inherits from the directories above it — a campaign's continuity, a system's
lore and rules — and how many layers there are varies by project. Before authoring, walk it:

```
~/work/bin/python <skill>/scripts/context_stack.py <adventure-dir-or-.md>
```

It reports every ancestor's Markdown with line counts and resolves the named assets
(`art_style.md`, `draw-tables.md`). Read broad → narrow; where layers disagree the narrower
wins. Grep the long files for the entities this adventure names rather than reading them
top-down. Full rules, including where to write a fact back: [CONTEXT-STACK.md](CONTEXT-STACK.md).

If the user names reference files in the prompt, those are authoritative — the walk finds
what they didn't think to mention.

## Workflow

Work top-down. Do not advance a layer until the user is satisfied with the current one.

1. **Premise** — establish the spine before anything else:
   - The situation (what is happening, and why now)
   - The stakes (what goes wrong if no one intervenes)
   - The hook (why *these* characters get pulled in)
   - Tone & scale (gritty vs. heroic; one-shot vs. multi-session)
   Propose 2–3 premise options as short pitches; let the user pick or remix.

2. **Arc** — the dramatic spine the session runs along. An adventure is too short to be
   fully player-generated, so commit to a shape before authoring scenes.
   - **Opening pressure** — the situation as players first meet it; what forces them to act
   - **Escalation** — how the stakes ratchet as they engage; a clock the GM can tick to keep
     pressure on even when players stall
   - **Turn** — the midpoint reversal or revelation that recontextualizes the goal
   - **Climax** — the confrontation the session drives toward; the choice that resolves the stakes
   - **Resolution** — what a win, a loss, and a costly win each look like
   Plot the *beats* (these turning points should land); improvise the connective tissue (how
   players get between them). Set the arc before scenes — it's the spine they hang on. A
   multi-session **campaign** is the opposite case — too long to pre-plot, so drive it with
   escalating **fronts**, player momentum, and NPC reactions rather than one fixed arc.

3. **Scenes** — the units of play that carry the arc's beats. For each, develop:
   - Purpose (which arc beat this scene carries)
   - Setting and who's present
   - What's at stake / what can change here
   - **Advances** — what each outcome unlocks or closes off, so branches are real, not decorative
   - Ways in and ways out (how players arrive, how it resolves or escalates)
   - Complications the GM can drop in
   - Sensory details: What does this place look like, sound like, smell like — draw these
     too (`rolodex.py --from <adventure-dir> location <section>`, or `street`, or `threats`)
     rather than reaching for the first image that fits the prose you just wrote
   Beats are fixed; the routes between them branch — give players several ways to reach each
   beat, not a single corridor.

4. **NPCs** — the people who drive the situation. For each, develop:
   - Role in the premise, and what they **want**
   - Their **stance** toward the players — sympathetic, antagonistic, or ambiguous
   - A **secret** or complication the players can uncover
   - Voice/manner (one line the GM can improvise from)
   - A **Visual.** line — hair, face, build, style and key items of dress — ending in an
     explicit **Cast:** field naming 1–2 actors who'd play them. Keep both labels literal
     so [rpg-npc-cast](../rpg-npc-cast/SKILL.md) can parse them and generate portraits.
   - A **Register** — the one emotion they wear at introduction (Tilda: braced fear;
     Anselm: patient menace), *when it's fixed*. This is the default portrait expression; a
     scene can call for another. Omit for NPCs with no characteristic mood.
   - Be creative with names no Elara, Kael, Thorne, Voss, no -ae-, no noun-surnames. Name the linguistic origin of each name proposed.
   - **Draw, don't invent.** If the stack has draw tables, source names, looks, professions
     and traits from them — `rolodex.py --from <adventure-dir> npc` — and write past what
     comes back. Picking "randomly" from a table you can read returns the attractor, which
     is the same failure the no-Elara rule is aimed at. If the project ships its own
     generator (a `scripts/gen-names.py` documented in its `CLAUDE.md`), prefer that.
   Start with the 2–4 NPCs the premise can't exist without; add minor ones later.
   Portraits are a separate skill: [rpg-npc-cast](../rpg-npc-cast/SKILL.md) reads the
   Visual/Cast/Register fields above. Run it in a **fresh session** — don't cast here — so
   image work doesn't bloat this adventure's context.

5. **Persist** — write everything to the adventure file after each layer, not just at
   the end. See [TEMPLATE.md](TEMPLATE.md) for the file structure.

## Pressure-test the arc

Before calling the adventure done, walk the spine once as a skeptic — plot deserves the same
scrutiny as the cast:

- **Causality** — does each scene's outcome feed the next beat, or are scenes just adjacent?
- **Agency** — can player choices change the route or the *cost*, not only the flavor? If every
  path reaches the climax identically, the branches are decorative.
- **Climax** — does it actually resolve the Premise's stakes, and can it end more than one way?
- **Momentum** — if players stall, does the escalation clock give the GM something to tick?

## Artifact rules

- **One adventure = one file**, inside the campaign directory — either directly
  (`<campaign>/<adventure-slug>.md`) or in its own folder when it has portraits and
  published forms to keep together (`<campaign>/<NN-slug>/<slug>.md`). Match whatever the
  stack already does; confirm the path with the user on first write, and pass it absolute.
- Sections follow [TEMPLATE.md](TEMPLATE.md): Premise, Arc, NPCs, Scenes, plus optional
  GM Notes and Open Threads.
- Adventures are **standalone with respect to their siblings** — never cross-link another
  adventure. They *do* inherit from their ancestors: the system's lore and the campaign doc
  are context, not things to copy in. Write each fact at the layer it belongs to
  (see [CONTEXT-STACK.md](CONTEXT-STACK.md)) — a running clock or a recurring NPC belongs in
  the campaign doc, not duplicated into every adventure that touches it.
- Update the file incrementally as each layer is confirmed; a fresh session should be able
  to pick the adventure up from this file plus its stack.

## Interaction style

- Ask focused questions; offer concrete options rather than open-ended prompts.
- Prefer the user's ideas over your own — you are a collaborator, not the author.
- Track loose ends in the **Open Threads** section so nothing gets dropped between
  sessions.
- Be efficient and direct with scene description and NPC dialog. Write direct examples to the document.

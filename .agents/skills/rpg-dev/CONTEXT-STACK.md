# The context stack

Shared by every `rpg-*` skill. An adventure inherits from the directories above it, and
this file fixes how far up to look, what to do with what's found, and which filenames
carry a defined meaning.

```
rpg-adventure-support/              project root — the walk stops here (.git)
  blades_68/                        System: rules + setting, art_style.md, draw-tables.md
    unnamed-campaign/               Campaign: campaign.md, characters.md, the-crew.md
      01-recall/                    Adventure: recall.md, its critique, its published form
```

**Depth is not fixed.** Some adventures have no campaign layer and sit directly in the
system directory; some projects add a session layer below the adventure; the project root
differs per user. Never hardcode a depth or a level's name — walk.

## The walk

```
~/work/bin/python scripts/context_stack.py <adventure-file-or-dir>
```

From the adventure directory, out to the first ancestor holding a `.git` (else `$HOME`),
listing the Markdown at each level with line counts and resolving the named assets below.
**Pass an absolute path** — relative paths resolve against a working directory that is
often no longer the repo root part-way through a session.

Run it once when you learn which adventure you're working on, before reading anything else.

## Two resolution rules

**Accumulate** — prose reference: lore, rules, campaign notes, PC sheets. Every layer
counts. Read broad → narrow, so the System's fiction frames the Campaign's continuity
which frames this Adventure. Where two layers disagree the **narrower wins** — a campaign
that has moved a faction's leadership on overrides the system book.

**Nearest-wins** — the named assets. Exactly one answer is wanted and it is the copy
closest to the adventure, so a campaign or a single adventure can override its system's.

| Asset | Nearest-wins | What it is |
|---|---|---|
| `art_style.md` | ✅ | The visual house look: a master style block to paste into an image model, palette regimes, compositional devices, negative prompt. Owned by [rpg-npc-cast](../rpg-npc-cast/SKILL.md). |
| `draw-tables.md` | ✅ | **Draw tables** — setting-owned lists sampled at random to dress a scene: locations, names, professions, threats, sounds, details. Human-readable grids. |
| `draw-tables-flat.md` | ✅ | The same tables as numbered lists, one per heading. The machine-readable source `scripts/rolodex.py` samples. |

Filenames match case-insensitively with `-` and `_` interchangeable. The legacy
`*rolodex*.md` names still resolve as draw tables.

## Reading what the walk finds

Reference files are long. **Do not read them top-down.** List the entities your adventure
names — factions, NPCs, districts, tech, named rules — and grep each layer for them, then
read those sections. The line counts in the report tell you which files are small enough to
just read (`clocks_summary.md (7)`) and which are not (`blades_68.md (328)`).

## Writing back

Each layer owns its own scope, and the walk is what joins them — so **write each fact at
the layer it belongs to and do not copy it downward.**

- A fact about the world → the System layer.
- What happened last session, a running clock, a recurring NPC → the Campaign doc.
- Everything specific to this session of play → the adventure file.

An adventure must be runnable from its own file plus its stack. It must **not** depend on a
*sibling* adventure — that's the standalone rule, and it is about siblings, not ancestors.

When you produce something reusable that no layer holds yet — a house look you and the
author agreed, a table you built — offer to save it at the **broadest layer it's true for**,
so the next adventure inherits it rather than re-deriving it.

## Draw tables vs. what the model reaches for

A model asked to invent a detail returns the attractor: the name that rhymes with names it
has written before, the cobbled alley, the smoky jazz club. Draw tables exist to beat that,
but only if the sampling happens **outside** the model — asked to "pick randomly" from a
table it can see, it drifts to whatever matches the prose it just wrote.

```
~/work/bin/python scripts/rolodex.py --from <adventure-dir> npc
~/work/bin/python scripts/rolodex.py --from <adventure-dir> location casino
~/work/bin/python scripts/rolodex.py --from <adventure-dir> list    # every list name
```

Each slot comes back with three candidates and sometimes a WILDCARD. Take the one that
could belong in the adventure already in play, then **write past it** — change the period
detail, the scale, whose it is, why it's there. A drawn entry is an angle of attack, never
a line to reproduce. Drop any slot where nothing earns a place.

If the project ships its own generator (a `scripts/gen-names.py` or similar, usually
documented in its `CLAUDE.md`), prefer it over inventing unaided, the same way.

---
name: rpg-critic
description: Give a tabletop RPG module a serious, table-focused critical read — pacing, internal contradictions, off-the-rails risks, shaky NPC motives, unanswered player questions, missing prep, and descriptive polish — and capture it as a durable critique-and-response log. Use when the user wants an adventure, module, one-shot, or scene stress-tested, red-teamed, or reviewed before running it; NOT for co-writing (that's rpg-dev).
---

# RPG Critic — Adversarial Read of a Module

Read an adventure the way a sharp GM reads it at 11pm the night before running it: hunting
for the things that break at the table. Deliver serious opinions and concrete fixes, **not a
gloss about how good it is**. Note strengths only where they're load-bearing to a finding.

System-agnostic: critique the module against **its own** rules and source material.

## Workflow

1. **Gather inputs.** The module to critique, plus the **reference files** it is canon
   against: setting / world lore, campaign-level notes (what's happened, PC ties, established
   facts), and system rules. The module must not contradict them, and the system lens is only
   as sharp as the rules file you have.

   Files the user passes are authoritative. To find the ones they didn't mention, walk the
   module's context stack — the directories above it hold exactly these files:
   ```
   ~/work/bin/python ../rpg-dev/scripts/context_stack.py <module-path>
   ```
   Confirm the shortlist with the user before starting rather than asking them to name files
   blind, and note which layer each came from — a campaign doc overrides the system book where
   they disagree. See [CONTEXT-STACK.md](../rpg-dev/CONTEXT-STACK.md).
2. **Read the whole module first**, twice. Reference files are often long — don't read them
   top-down. Instead, list the entities the module names (factions, NPCs, tech, districts,
   named rules) and **grep the reference files for each** to pull the canon it leans on; read
   those sections. Hold it all in mind before writing — contradictions and orphaned setups
   only show up across scenes.
3. **Run every lens** below over it. These are the default checklist; drop a lens that yields
   nothing, add a module-specific category if the module needs one.
4. **Write findings** to the critique file as you go (see [CRITIQUE_TEMPLATE.md](CRITIQUE_TEMPLATE.md)).
   Each finding gets a stable ID, a severity, a one-line diagnosis, and a concrete fix — often
   drawn from the module's own material ("your own source has the cure; apply it").
5. **Triage last.** Close with the 5-ish fixes to make before running, and flag any finding
   that might be a deliberate choice rather than a bug.

## The lenses

- **Breaks mid-session** — internal contradictions, geography/timeline that can't both be true,
  undefined-but-load-bearing rules, a scripted beat that only fits one branch. These are 🔴.
- **Off the rails** — the genre-savvy or chaotic play the module isn't armored against: the crew
  ignores/kills the exposition NPC, just leaves, settles early, interrogates the plot open.
  Every reveal or item routed through a single point of failure is a finding.
- **NPC motivation cracks** — a villain who reads as incompetent not sinister, a want that
  contradicts the setup, a performance the GM can't actually play as written.
- **Pacing / boring-risk** — the "wizard explains the plot" scene, an encounter that's a mood
  board with no spine, one theme hit five times, scripted tragedy that reads as railroad, and
  real runtime vs. billed length.
- **Unanswered player questions** — the obvious questions a table asks in the first ten minutes
  that the text can't answer (who are we, how big is the map, can we hack/talk to X).
- **Missing prep** — stat blocks, clocks, scales, or worked examples the GM is left to improvise
  under a heavy handoff burden.
- **Canon & rules consistency** — *only when reference files are provided.* Contradictions with
  the setting/lore, campaign continuity breaks (retconned facts, ignored PC ties, timeline
  clashes), and system rules the module misuses or violates. Cite the reference file + section,
  not just the module.
- **Descriptive polish** — 🔵 enrichments: a fixed sensory signature, a recurring motif, a
  physical tell — details that make players *feel* the situation. Keep these clearly optional.

## Severity

Each finding is a GitHub admonition block whose type carries its severity, plus the matching
emoji in the heading for scanning:

🔴 `[!CAUTION]` will break at the table · 🟠 `[!WARNING]` design/pacing weakness ·
🟡 `[!IMPORTANT]` unanswered question or canon/rules clash · 🔵 `[!TIP]` enhancement

## Output

- **One critique = one file**, written alongside the module: `<module-slug>-critiques.md` in the
  module's own folder.
- Follow [CRITIQUE_TEMPLATE.md](CRITIQUE_TEMPLATE.md): metadata header (source module, any
  reference files checked against, date, stance), a "how to read this" note, severity legend,
  categorized findings with stable IDs, and empty `→ Response:` / `→ Status:` lines for the
  author to fill, then Triage. Each finding's body is a GitHub admonition block.
- The file is a **dialogue log**: leave the response/status lines blank so the author replies
  inline and marks each `accepted` / `rejected` / `deferred` / `discuss`.

## Stance

- Be specific. "Vesna can't be where she needs to die (said twice she never went higher, then
  dies at the penthouse)" beats "some geography is unclear." Cite scene/section.
- Every finding carries a fix, and the fix should be buildable — a number, a branch, a named
  clock, a cut — not "consider tightening this."
- Distinguish bugs from choices. If a weakness might be intentional, say so and let the author
  reject it with a note rather than pretending it's broken.

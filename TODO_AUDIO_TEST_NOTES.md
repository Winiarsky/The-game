# Audio test notes

## Ashen Oath playtest

- [ ] `scenario.opening_scene` / prompt `#28` / title `Rynek Brindleford`: no voiceover played at this prompt during playtest.
  - Context: the next prompt shortly after this one did play a correct voiceover.
  - Initial decision: do not fix during the current test run.
  - Follow-up: decide after testing whether this prompt is redundant text-only, should reuse `audio/voiceover/square_intro_001.mp3`, or needs its own generated voiceover.

- [ ] `dialog.nila_ashwick.start` / prompt `#43` / title `Nila Ashwick`: NPC image is missing or using the generic hooded placeholder.
  - Follow-up: add or wire a proper portrait/image for Nila Ashwick after the playtest.

- [ ] `dialog.nila_ashwick.start` / prompt `#43` / title `Nila Ashwick`: voiceover did not play, but this prompt should be read by the narrator.
  - Expected: narrator reads the visible Nila Ashwick prompt text before/while the player chooses an option.
  - Follow-up: verify whether the prompt has an `audio` field, whether the referenced file exists, and whether choice prompts are allowed to autoplay voiceover.

- [ ] Choice-only/dialog prompts: remove the extra bottom control bar with `Nat 20`, `Nat 1`, and `Potwierdź wybór (Enter)`.
  - Context: for prompts where players only choose an option, the option buttons plus Enter guidance are enough.
  - Goal: save vertical space and reduce duplicated controls in dialogue/choice prompts.

- [ ] Choice-only/dialog prompts: remove the upper instruction panel with `Dalej: Po wyborze zobaczysz wynik albo kolejny krok.` and `Wybierz opcję i potwierdź wybór.`
  - Context: leave only the main text frame and the option buttons.
  - Goal: reduce clutter and keep attention on the prompt text plus choices.

- [ ] Roll/test prompts: simplify the visible prompt layout and move generic instructions to voiceover.
  - Example observed: `ui.roll.game` / prompt `#44` / title `Test Diplomacy (DC 14).`
  - Visible UI goal: keep only the prompt title plus the actual roll input/modifier UI; remove the top `Rzut` instruction panel.
  - Voiceover goal: generate/reuse a generalized narration for this prompt type, e.g. `Wykonaj test Dyplomacji i podaj wynik rzutu.`
  - Generalize for all prompts shaped like `Wykonaj test ... i podaj wynik rzutu.`

- [ ] Roll/test prompts: replace the long modifier summary sentence with structured modifier tiles.
  - Example text currently shown: `Podaj wynik rzutu d20 (bez premii). Premie/kary (najwyższe per typ): +2 status (group_impression +2) Modyfikator bazowy: +7 Uwagi: Group Impression: +2 status. Łączny modyfikator: +9 (doliczany automatycznie).`
  - Goal: each modifier tile should show the concrete source/name, value, and type instead of generic labels only.
  - Example: the `Status +2` tile should name the source `Group Impression` or the localized equivalent, not only `Premie/kary status.`
  - Follow-up: trace where `group_impression +2` is coming from and decide whether the UI should explain when/why that status bonus was applied.

- [ ] Result/continue prompts: remove the duplicated summary panel directly under the title.
  - Example observed: `dialog.nila_ashwick.gentle_questions` / prompt `#46` / title `Nila Ashwick, dziecko-świadek`.
  - Context: the upper panel repeats result/continue text already present in the main text frame.
  - Goal: keep the title, main text frame, and a simple continue affordance only.

- [ ] Roll input controls: remove separate `Nat 20` and `Nat 1` buttons when the UI asks for the raw d20 roll.
  - Context: if the player enters `1`, it is naturally a nat 1; if they enter `20`, it is naturally a nat 20.
  - Goal: avoid redundant buttons and save horizontal/vertical space.

- [ ] `dialog.nila_ashwick.gentle_questions` / prompt `#46`: highlight the clue location on the LED board.
  - Context: the text says Nila points to the place where the party should search for a clue.
  - Expected LED behavior: highlight the well while this prompt is visible.
  - Expected cleanup: turn that highlight off after the player confirms/continues with Enter.

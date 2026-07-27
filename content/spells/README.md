# Spell content schema

Each `dnd_board_game.spell` file owns the rules metadata and one executable
`effect`. Actors reference spells through `spell_refs`; the scenario loader
adapts `attack`, `healing`, and `combat_action` effects to the existing combat
pipeline.

Components support `verbal`, `somatic`, and material entries with `item_id`,
`label`, optional `minimum_value_cp`, `quantity`, and `consumed`. A focus may
replace only a material that has no minimum value and is not consumed.

Optional `scaling` adds damage, healing, or targets for every slot level above
the spell's base level. A targeted `combat_action` declares its base
`target_count`; `targets_per_slot_level` increases that limit for the selected
higher slot while all selected effects still belong to one cast and, when
applicable, one concentration. Ritual spells set `ritual: true`; exploration rituals
may use the generic `set_flag` effect, take their normal casting time plus ten
minutes, validate components, and do not consume a spell slot. Their declared
duration is converted to the shared exploration clock: recasting replaces the
same flag effect, and time spent crafting, resting or changing armor can expire it.

Combat spells with `minute`, `ten_minutes`, or `hour` casting times use persisted
`LongCastState`: one action per caster turn and concentration until completion.
Slots and consumed components are charged only when the final action completes.

The `summon` combat-action family embeds one reusable creature definition.
It selects a free visible tile in range, joins initiative immediately after
its owner, exposes its own attack source, and disappears when the owner's
concentration ends. Project-original fixtures remain separate from SRD content.

The `spell_movement` family embeds a `movement` object with `teleport`, `push`
or `pull` and a grid-aligned distance. Teleports select a visible free tile;
forced movement selects an enemy, resolves its save, then stops at the last
legal tile before terrain, an edge, a scene object or another living actor.

The `spell_debuff` family uses `effect_kind: apply_condition`, an authored
condition, save ability/DC/timing and hostile ranged targeting. The initial
enemy save is automatic; failure creates the shared condition state and its
later save uses the normal turn lifecycle. Project-original fixtures avoid
concentration so the condition remains until a successful save or dispel.

The `spell_dispel` family uses `effect_kind: dispel_magic` and `target_faction:
any`. It selects a visible creature carrying spell-authored active effects or
conditions. Effects at or below the selected cast level end automatically;
stronger effects require one physical spellcasting-ability check each against
DC `10 + effect level`.

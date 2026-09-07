# Grafika mapy Głodnych Cieni v6

Tryb: wbudowany `imagegen`, sketch-to-render, jedna generacja.
Referencja: schemat pól wygenerowany z runtime scenariusza (plik roboczy
`/tmp/shadows-v6/guide.png`). Ilustracja nie definiuje zasad pól; definiuje je
nakładka SVG generowana przez `scripts/build_hungry_shadows_map.py`.

Wynik: `assets/maps/ostatni_transport_01/glodne_cienie_illustration_v6.png`.
Gotowa plansza: `assets/maps/ostatni_transport_01/glodne_cienie_battlemap_v6.svg`.

## Prompt

```text
Use case: sketch-to-render. Asset type: printable tactical battlemap for a physical 20 by 30 board, portrait 2:3. Input image is the exact geometry reference, not the desired rendering style. Render this layout as a restrained dark fantasy comic-book illustration, strict orthographic top-down view, readable broad shapes and quiet walkable ground. Preserve the location and footprint of every colored area in the reference. Tan = dry open traversable road/clearing, do not add obstacles anywhere in tan. Green = dense impassable forest confined to the thin edge strips. Blue = shallow stream in upper left only. Gray vertical rectangle at x75–85%, y33–47% = SHORT isolated rock ridge, with open paths BOTH above and below it and to its right. Central dark brown stepped shape x40–60%, y43–53% = ONE overturned merchant wagon, slightly diagonal with visible wooden bed/wheels, the only large central obstacle. Ochre patches touching it = low wooden edges and TWO small cargo crate groups. Separate ochre strip x20–30%, y53–57% = ONE fallen tree trunk. Dark desaturated brown patches below wagon x40–60%, y53–63%, and just above it = small muddy wheel ruts and puddle, never a broad mud belt. All other tan remains walkable dry dirt, wide connected approaches on both sides of wreck. Low texture density, muted moss greens, ochre dirt, slate rock, teal water, bold readable contours. No grid, text, labels, characters, monsters, arrows, markers, border, buildings, towers, extra cargo, extra logs or extra rock walls. Keep exact 2:3 portrait framing; the many open tan areas must remain open. Match layout precisely so an exact square-cell rules overlay can align to this painting.
```

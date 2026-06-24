# Ashen Oath print maps

Printable battle maps for the `ashen_oath` campaign.

Scale:

- 1 tactical field = 2.5 x 2.5 cm
- Full maps use the physical board size: 20 columns x 30 rows, 50 x 75 cm.
- A4 PDFs are landscape and tiled for home printing.
- Full-size PDFs keep one map per 50 x 75 cm page for large-format printing.
- Print at 100% / actual size. Do not use "fit to page".

Files:

- `pdf/ashen_oath_print_maps_grid_a4_tiled.pdf` - tactical grid version.
- `pdf/ashen_oath_print_maps_no_grid_a4_tiled.pdf` - atmospheric version without grid.
- `pdf/ashen_oath_print_maps_grid_full_20x30_fields.pdf` - one full-size 20x30 board page per map.
- `pdf/ashen_oath_print_maps_no_grid_full_20x30_fields.pdf` - full-size atmospheric version.
- `png/grid/*.png` - full map PNGs with tactical grid.
- `png/no_grid/*.png` - full map PNGs without tactical grid.
- `images/*_bg.png` - generated atmospheric backgrounds used by the PDF generator.

Regenerate:

```bash
python scripts/generate_ashen_oath_print_maps.py
```

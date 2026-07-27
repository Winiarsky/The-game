# Papierowe mapy: wioska i strażnica

Każda mapa odpowiada całej fizycznej planszy:

- 20 kolumn × 30 rzędów,
- jedno pole fizyczne: 2,5 × 2,5 cm,
- rozmiar końcowy: 50 × 75 cm,
- grafika bez nadrukowanej siatki, w skali szarości.

Pliki w `pdf/a4/` są podzielone na poziome kartki A4 z zakładką 3 mm. Należy
drukować je w skali 100% / „rozmiar rzeczywisty”, bez opcji „dopasuj do strony”.
`pdf/full_size/` zawiera wersje 50 × 75 cm do druku wielkoformatowego, a `png/`
pełne obrazy rastrowe 300 DPI.

Znaczniki orientacji znajdują się w trzech rogach: jeden w lewym górnym, dwa w
prawym górnym i trzy w lewym dolnym. Nie są polami ani elementami sceny.

Regeneracja:

```bash
python scripts/generate_print_maps.py
```

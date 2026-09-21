# Portrety przeciwników w makiecie UI

Plik: `enemies-atlas.png`, 1774 × 887 px, PNG RGBA. Pojedynczy atlas 4 × 2, bez ramek i odstępów. Został wygenerowany wbudowanym narzędziem `image_gen` (bez CLI) i zapisany do repozytorium bez kadrowania ani edycji. Są to ilustracje do propozycji UI; nie zmieniają zasobów ani danych scenariusza w aplikacji.

Styl sprawdzono na istniejącym `content/scenarios/misja_0_dzwon/assets/images/comic_v2/garran.png`; obraz opisano słownie w prompcie, bez przekazywania go jako celu edycji.

Do prezentacji pojedynczego portretu użyj kwadratowego elementu z `background-size: 400% 200%`. Pozycje tła:

| Postać | Kolumna / wiersz (od 0) | `background-position` |
| --- | --- | --- |
| `borut` | 0 / 0 | `0% 0%` |
| `drwal` | 1 / 0 | `33.3333% 0%` |
| `parobek` | 2 / 0 | `66.6667% 0%` |
| `procarz` | 3 / 0 | `100% 0%` |
| `woznica` | 0 / 1 | `0% 100%` |
| `pomocnik` | 1 / 1 | `33.3333% 100%` |
| `procarz_drugi` | 2 / 1 | `66.6667% 100%` |
| `drwal_drugi` | 3 / 1 | `100% 100%` |

Kontrola wizualna: osiem odrębnych twarzy, poprawna kolejność, równa siatka, brak tekstu i nakładających się portretów. Przy powtórzonych profesjach zastosowano różne twarze, fryzury i kolory ubrań.

## Prompt

```text
Use case: stylized-concept.
Asset type: one game-UI portrait texture atlas, landscape 2:1 aspect ratio, exactly four columns and two rows of eight equally sized square cells, all cells flush without gutters or borders. This is a single sprite-atlas image to be consumed directly by CSS background positions.
Primary request: eight distinctive head-and-shoulders portraits of human opponents from a grounded medieval Slavic-fantasy village. Bold detailed black comic-book ink, crisp expressive faces, textured painterly flat colors, warm worn cloth, subdued dark olive and brown backgrounds; match the look of a gritty European fantasy graphic novel. Each face centered within its own square cell, eyes around 40% height of the cell, head fully inside cell, close and recognizable at tiny UI size. Strong silhouette and different face, hair, headwear and garment color per character. Neutral to stern expressions, no gore.
Exact cell order from left to right:
TOP ROW cell 1: Borut, authoritative broad-faced village leader age 50, short charcoal hair with gray temples, heavy gray mustache and short beard, deep burgundy wool collar and plain bronze brooch.
TOP ROW cell 2: woodcutter, large stocky man age 40 with bright red full beard, bald forehead, forest-green coarse tunic, a small axe handle behind shoulder.
TOP ROW cell 3: farmhand, lean young adult age 22, shaggy blond hair, clean-shaven narrow face, ochre linen shirt.
TOP ROW cell 4: slinger, wiry adult age 30, short dark hair, dark narrow mustache, reddish-brown cap and faded blue wool vest, sling leather crossing shoulder.
BOTTOM ROW cell 1: wagon driver, older weathered man age 60, long gray mustache, dark brown broad-brimmed felt hat, tan scarf and russet jacket.
BOTTOM ROW cell 2: helper, round-faced adult age 35 with short curly brown hair and a modest brown beard, simple light cream work shirt with dark apron straps.
BOTTOM ROW cell 3: second slinger, adult age 28, distinct sharp cheekbones, black braided hair at sides, no beard, dark teal hood pulled up, leather sling visible at shoulder.
BOTTOM ROW cell 4: second woodcutter, muscular man age 45, long dark hair tied back, squared black beard, red plaid work shirt, a small axe haft at shoulder.
Constraints: exactly eight portraits, one person per square cell, equal-sized 4x2 grid mathematically aligned edge to edge. No text, no letters, no numbers, no symbols, no labels, no watermarks, no frames, no margins. Distinct faces should remain recognizable within circular UI crops. Not photorealistic. No interface surrounding the atlas.
```

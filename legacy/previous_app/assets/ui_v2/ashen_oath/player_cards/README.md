# Ashen Oath - printable player cards

Folder zawiera osobne karty postaci do druku dla kampanii `ashen_oath`.

## PDF do druku

- `pdf/cedric.pdf`
- `pdf/freya.pdf`
- `pdf/kord.pdf`
- `pdf/christopher.pdf`
- `pdf/lorielen.pdf`
- `pdf/jimi.pdf`

Kazdy PDF ma 1 strone A4.

## Zrodla

- `md/*.md` - wersje tekstowe, najlatwiejsze do edycji.
- `html/*.html` - wersje z layoutem i grafikami.
- `card.css` - wspolny styl kart.
- `images/ashen_oath_party_header_6p.png` - grafika realnej szescioosobowej druzyny wygenerowana przez imagegen.
- `images/*_portrait.jpg` - portrety postaci skopiowane z `portrait_image` w lokalnych `data/heroes/*.json`.

## Regeneracja PDF

Przyklad:

```bash
google-chrome --headless --disable-gpu --no-sandbox \
  --print-to-pdf=assets/ui_v2/ashen_oath/player_cards/pdf/cedric.pdf \
  --print-to-pdf-no-header \
  file:///home/winiar/Desktop/projects/boardgame/The%20game/The-game/assets/ui_v2/ashen_oath/player_cards/html/cedric.html
```

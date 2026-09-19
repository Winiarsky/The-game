# Kafle Misji 0 — oprawa tuszem v3

14 ilustracji PNG obsługuje 18 kafli. Wóz pochodzi z zaakceptowanej próbki,
pozostałe 13 wygenerowano osobno wbudowanym image_gen z wozem jako referencją
stylu. `prompts.json` zawiera dokładne prompty i pochodzenie każdego pliku.

Przypisania `artwork` i nazwy `print_name` edytuje się w `../../cutouts.json`.
Ilustracje zawierają tylko przedmiot lub miejsce. Generator dokłada ramkę,
pogrubioną nazwę, myślnik, zwykły tekst działania, ID i punkt interakcji.
Całość mieści się w niezmienionych rozmiarach kafla. Nie dokładaj tekstów
ani siatki do samej ilustracji. Meble są dekoracyjne.

Styl: czarny tusz na białym tle, wyraźny kontur, realistyczna konstrukcja,
oszczędne kreskowanie. Gruz ma przezroczyste tło, które w wydruku jest białe.
Ilustracje są rastrowe; typografia i ramki w PDF pozostają wektorowe.

Eksport z katalogu projektu:

```sh
PYTHONPATH=src:. .venv/bin/python scripts/build_mission_zero_cutouts.py
```

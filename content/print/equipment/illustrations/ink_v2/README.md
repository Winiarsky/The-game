# Ilustracje wyposażenia

Czarno-białe ilustracje tuszem wygenerowane wbudowanym narzędziem imagegen.
Wzorzec stylistyczny: kafel wozu `content/scenarios/misja_0_dzwon/maps/illustrations/ink_v3/cart.png`.
Wyraźny obrys, faktura materiałów, oszczędne kreskowanie, białe tło.
Pełne prompty i pochodzenie plików zapisano w `prompts.json`.

Wspólne wyposażenie jest w tym folderze. Pierścień, medalik, mikstura,
klucz i dokumenty misji 0 są w jej folderze `assets/items/ink_v2`.
Mapowanie ilustracji do przedmiotów: `src/dnd_board_game/physical_cards/equipment_art.py`.
Powtarzające się rodzaje wyposażenia korzystają z tego samego obrazu.

UI i generator kart używają tych samych plików PNG. Po podmianie obrazka
odśwież UI i wykonaj `python scripts/build_equipment_cards.py`, aby odbudować PDF-y.
Format karty: 63 × 88 mm, po 9 miejsc na A4. Drukuj w skali 100%.

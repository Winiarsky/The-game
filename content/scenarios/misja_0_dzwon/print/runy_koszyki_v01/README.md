# Koszyki run v0.2 — siedmiu bohaterów

[Materiały do druku](index.html). A4, jednostronnie, 100%, bez dopasowania.

7 zestawów, 42 stron łącznie. Postać i pola na żetony, koszyki, mata zdolności, wyposażenie, wycinanki zdolności i sprzętu.

Zdolności: 60 × 54 mm. Wyposażenie: 60 × 42 mm. Koszyki mają osobne miejsca na naładowane i rozładowane znaczniki. Połóż po jednym znaczniku dla każdego punktu pojemności i przemieszczaj go pomiędzy tymi miejscami. Małe runy sugerują przygotowanie przed walką; możesz wybrać inne symbole z tej samej kategorii. Przy ładowaniu rzut k4 określa nowy symbol.

Każda moc kosztuje jedną własną runę kategorii; najwyżej jeden rezonans z innej kategorii. Wsparcie: do 3 pól, własna runa wspierającego i jego Reakcja. Skupienie: specjalna, do dwóch ładowań k4. Indywidualne wyzwalacze mają limit raz na rundę.

Źródło mechaniki: `content/print/rune_baskets_v01/catalog.json`. Statystyki, historie i wyposażenie: bieżące profile siedmiu bohaterów. Model działa w nowych walkach Misji 0 i swobodnym treningu areny. Stare zapisy zachowują poprzedni model. Warunki odnowienia zgłasza się Mostem; limit i żetony rozlicza aplikacja.

Odbudowa: `PYTHONPATH=src .venv/bin/python scripts/build_rune_baskets.py`. `--data-only`: tylko dane makiety, `--html-only`: dane i HTML bez przeglądarki/PDF. Pełne generowanie sprawdza układ i wymiary w jednej przeglądarce naraz, a następnie drukuje PDF.

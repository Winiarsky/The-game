# Wersjonowanie Contentu I Źródła

## Przyjęty zakres

Bazowym rulesetem projektu jest `dnd_5e_2014`. Docelowy katalog zgodny z tym
rulesetem może wykorzystywać materiał z SRD 5.1 udostępnionego przez Wizards of
the Coast na licencji CC BY 4.0. SRD 5.2/5.2.1 dotyczy rewizji zasad z 2024 roku
i nie jest automatycznie mieszany z obecnym rulesetem.

Oficjalne źródła tej decyzji:

- SRD 5.1 wraz z wymaganą treścią attribution:
  https://media.wizards.com/2023/downloads/dnd/SRD_CC_v5.1.pdf
- komunikat Wizards potwierdzający udostępnienie całego SRD 5.1 na CC BY 4.0:
  https://www.dndbeyond.com/posts/1439-ogl-1-0a-creative-commons
- informacja o SRD 5.2.1 i rozdzieleniu SRD od D&D Beyond Basic Rules:
  https://www.dndbeyond.com/posts/1949-you-can-now-publish-your-own-creations-using-the

Ten dokument opisuje techniczną politykę pochodzenia danych, a nie poradę prawną.

## Source packi

Rejestr `content/source_packs.json` jest jedynym miejscem definiującym source pack,
jego licencję, URL oraz wymagane attribution. Definicja contentu wskazuje wyłącznie
stabilne `source_pack_ids`.

Aktualne pakiety:

- `project_original` — lokalny content testowy projektu. Repozytorium nie ma
  obecnie zadeklarowanej licencji, dlatego pack ma `NOASSERTION` i nie wolno
  traktować go automatycznie jako otwartego ani redystrybuowalnego katalogu;
- `srd_5_1_cc_by_4_0` — materiał świadomie pochodzący z SRD 5.1. Publikacja
  wykorzystująca taki wpis musi zachować attribution zapisane w rejestrze.

Nie wolno jako źródła katalogu używać tekstów z Player's Handbook, Dungeon
Master's Guide, Monster Manual, D&D Beyond Basic Rules ani innych stron tylko
dlatego, że są dostępne do przeczytania. Definicja korzystająca z materiału
spoza zarejestrowanych packów nie przechodzi audytu.

## Nagłówek definicji

Każdy samodzielny scenariusz, item, monster, feature i katalog zawiera:

```json
{
  "schema": "dnd_board_game.item",
  "schema_version": 1,
  "ruleset_id": "dnd_5e_2014",
  "source_pack_ids": ["project_original"],
  "id": "longsword"
}
```

Fragmenty scenariusza z folderu `parts` dziedziczą nagłówek głównego
`scenario.json`; nie są osobnymi pakietami contentu.

## Stabilne identyfikatory

Lokalne ID definicji używają `snake_case` i po publikacji nie mogą zmienić
znaczenia. Audyt buduje globalny klucz `kind:local_id`, np.:

- `scenario:abandoned_watchtower`,
- `monster:goblin`,
- `item:longsword`,
- `feature:heroic_strike`.

Zmiana lokalnego ID wymaga migracji wszystkich referencji i zapisów, które je
przechowują. Nie wolno używać nazwy wyświetlanej ani ścieżki pliku jako
zastępczego ID.

## Wersjonowanie i migracje

- Runtime zapisuje wyłącznie bieżącą wersję schematu.
- Loader normalizuje starszy, beznagłówkowy scenariusz do content v1, aby
  zachować kompatybilność lokalnych fixture'ów.
- Każda kolejna wersja wymaga czystej migracji `vN -> vN+1` zarejestrowanej w
  `MigrationRegistry`.
- Migracje są wykonywane bez pomijania wersji i nie mogą używać losowości,
  plików zewnętrznych, Flask, hardware ani LLM.
- Nieznany schemat, przyszła wersja lub brak kroku migracji powodują błąd.

Snapshot sesji używa obecnie v12. Sekwencyjne migracje v1→v12 zachowują starsze
zapisy, a kolejne wersje dodały kontrakt contentu, ekonomię, amunicję, łup pola
walki, kupców, pancerze, stan ładunków, attunement oraz kontrakt zwykłego
ekwipunku.

## Audyt

Polecenie:

```bash
PYTHONPATH=src python scripts/audit_content.py content
```

Opcja `--json` zwraca maszynowy raport. Audyt sprawdza:

- nagłówki i wersje schematów,
- format oraz unikalność stabilnych ID,
- istnienie source packów,
- ładowalność scenariuszy,
- referencje i obsługiwane prymitywy sprawdzane przez właściwy loader.

Warning `source_license_unasserted` jest oczekiwany, dopóki repozytorium lub pack
`project_original` nie otrzyma jawnej licencji. Błędy audytu blokują uznanie
katalogu za gotowy.

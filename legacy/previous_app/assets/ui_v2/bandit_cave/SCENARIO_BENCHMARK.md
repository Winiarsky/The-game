# Bandit Cave - benchmark scenariusza

`bandit_cave` jest scenariuszem referencyjnym dla kolejnych przygod. Nowy scenariusz powinien kopiowac nie fabule, tylko zakres integracji: runtime flow, Player UI, assety, audio i testy kontraktowe.

## Minimalny pakiet

- `scenario_flows/<scenario_id>.json` z `format: scenario_flow_v1`.
- Co najmniej dwie mapy i przejscie miedzy nimi.
- `player_ui/content/<scenario_id>.json` z briefingiem, celami, rozdzialami, wynikiem i `asset_manifest`.
- `assets/ui_v2/<scenario_id>/manifest.json`.
- Grafiki w `assets/ui_v2/<scenario_id>/images/`.
- Audio w `assets/ui_v2/<scenario_id>/audio/`.
- Pliki promptow produkcyjnych: `IMAGE_PROMPTS.md` i `AUDIO_PROMPTS.md`.

## Zakres mechanik

Benchmarkowy scenariusz powinien pokazywac:

- start mapy z narracja,
- warunkowe przejscie,
- przejscie bezwarunkowe,
- ukryty obiekt albo sekret,
- opcjonalny cel,
- cel glowny zakonczony eventem,
- walke i reakcje na `combat_end`,
- NPC z wyborem dialogowym albo testem spolecznym,
- pulapke albo inny interaktywny obiekt z konsekwencja,
- finalny event `finish_scenario`,
- checkpoint po waznych zmianach stanu.

## Asset manifest

Manifest powinien zawierac:

- `fallbacks`: `actor`, `choice`, `spell`, `action`, `enemy`,
- `characters` dla narratora i istotnych NPC,
- `enemies`,
- `actions`,
- `spells`,
- `scenes` dla rozdzialow/map,
- `interactables` dla waznych obiektow lokacyjnych,
- `music`, `sfx`, `narration`.

Wszystkie sciezki w manifeście musza byc relatywne wobec `base_path`, chyba ze asset jest wspoldzielony i celowo ma sciezke absolutna.

## Audio

Story eventy w `scenario_flow` powinny deklarowac audio bezposrednio przy akcji:

```json
{
  "type": "show_prompt",
  "audio": "audio/voiceover/example_001.mp3",
  "message": "Tekst narracji."
}
```

Hardcoded mapowanie w runtime jest tylko fallbackiem kompatybilnosci. Nowe scenariusze nie powinny go wymagac.

## Grafiki

- Tokeny, ikony i interactables: `.png` z kanalem alfa.
- Sceny: `.png` 16:9 bez tekstu, uzywane w briefingu i widoku aktualnej mapy.
- Styl powinien byc spojny w ramach scenariusza.
- Robocze SVG moga zostac jako historia, ale manifest powinien wskazywac finalne PNG.

## Testy wymagane

Minimum dla nowego scenariusza:

- flow laduje sie i przechodzi `validate_scenario_flow`,
- przejscia odwolują sie do istniejacych `exit_id` i `entry_anchor_id`,
- story eventy maja `audio`,
- manifest assetow wskazuje istniejace pliki,
- obrazy z manifestu serwuja sie przez `/assets/...`,
- audio cue z contentu serwuja sie przez `/assets/...`,
- golden path: start -> przejscia -> cel glowny -> `finish_scenario`,
- negatywna sciezka dla co najmniej jednego zablokowanego przejscia albo warunku.

## Kryterium gotowosci

Scenariusz jest gotowy jako benchmarkowy, gdy mozna:

- uruchomic go przez Player UI,
- zobaczyc briefing z grafika sceny,
- przejsc przez glowna petle wydarzen,
- uslyszec voiceovery eventow,
- zobaczyc tokeny/ikony z manifestu w UI,
- zakonczyc scenariusz finalnym wynikiem,
- przejsc celowane testy kontraktowe i flow.

# Ashen Oath - walkthrough and verification guide

Ten dokument sluzy jako solucja dla prowadzacego oraz jako checklista testowa kampanii `ashen_oath`.

## Pliki kampanii

- Runtime flow: `scenario_flows/ashen_oath.json`
- Mapy: `scenarios/ashen_oath_*.json`
- Player UI content: `player_ui/content/ashen_oath.json`
- Asset manifest: `assets/ui_v2/ashen_oath/manifest.json`
- Prompty grafik: `assets/ui_v2/ashen_oath/IMAGE_PROMPTS.md`
- Prompty audio: `assets/ui_v2/ashen_oath/AUDIO_PROMPTS.md`
- Test kontraktowy: `tests/test_ashen_oath_campaign.py`

## Cel kampanii

Druzyna ma odkryc, ze kasztelan Odran Vale falszywie oskarza Mire Ashwane. Prawdziwy problem to kradziez relikwiarza z kaplicy i zlamanie Popielnej Przysiegi. Final rozstrzyga sie w `oath_crypt`.

## Golden path

Ta sciezka powinna przeprowadzic kampanie od startu do dobrego zakonczenia.

### 1. Start: `brindleford_square`

Oczekiwane:

- Event `square_intro` pokazuje narracje startowa.
- Gracze widza Odrana i Elne jako NPC.
- Dostepne sa przejscia:
  - `to_burned_chapel`
  - `to_old_mill`
  - `to_hill_ruins`

Zalecane dzialania:

1. Porozmawiaj z Odranem.
2. Porozmawiaj z Elna.
3. Zbadaj studnie i ukryty obiekt `ashen_oath_mark`.

Po odkryciu `ashen_oath_mark`:

- Event `ashen_mark_revealed` powinien ustawic `castellan_doubted=true`.
- Powinien pojawic sie prompt narratora o znaku przysiegi.

Minimalny stan po rynku:

```text
castellan_doubted=true
```

### 2. Sledztwo: `burned_chapel`

Wejscie:

- Uzyj przejscia `to_burned_chapel`.
- Mapa laduje anchor `from_square`.
- Event `chapel_intro` pokazuje narracje.

Zalecane dzialania:

1. Pokonaj lub omin 2x `ashen_watcher` - slabe popielne zjawy, raczej scena ostrzegawcza niz pelna walka.
2. Zbadaj ukryty obiekt `broken_oath_seal`.

Po odkryciu `broken_oath_seal`:

- Event `chapel_seal_found` powinien ustawic:
  - `chapel_investigated=true`
  - `relic_theft_discovered=true`
  - `warden_medallion_recovered=true`
- Objective `recover_warden_medallion` powinien zostac ukonczony.
- Powinien pojawic sie prompt o medalionie Serai i pieczeci Vale'a.

Minimalny stan po kaplicy:

```text
chapel_investigated=true
relic_theft_discovered=true
warden_medallion_recovered=true
completed: recover_warden_medallion
```

### 3. Opcjonalny, ale zalecany etap: `old_mill`

Wejscie:

- Wroc na rynek przez `return_to_square_from_chapel`.
- Uzyj `to_old_mill`.
- Event `mill_intro` pokazuje narracje.

Zalecane dzialania:

1. Rozpocznij walke ze straznikami Odrana: 2x `vale_guard` trzyma linie, `mill_enforcer` probuje zastraszyc i przewracac bohaterow.
2. Wyczysc przeciwnikow na mapie.
3. Zbadaj `mill_hidden_route`.

Po `combat_end` i wyczyszczeniu mapy:

- Event `mill_cleared_tovin_rescued` powinien ustawic:
  - `tovin_rescued=true`
  - `false_ash_found=true`
- Objective `free_the_acolyte` powinien zostac ukonczony.

Po odkryciu `mill_hidden_route`:

- Event `mill_hidden_route_revealed` powinien ustawic `hidden_mill_route_found=true`.
- Przejscie `mill_hidden_track` do ruin powinno byc dostepne.

Minimalny stan po mlynie:

```text
tovin_rescued=true
false_ash_found=true
hidden_mill_route_found=true
completed: free_the_acolyte
```

### 4. Plot twist: `hill_ruins`

Wejscie:

- Z rynku: `to_hill_ruins`, albo z mlyna: `mill_hidden_track` po odkryciu sekretu.
- Event `ruins_intro` pokazuje narracje.

Zalecane dzialania:

1. Nie traktuj Miry jako automatycznego wroga.
2. Pokonaj lub obejdz `ashen_knight` oraz 2x `ashen_watcher`, ktore pilnuja zejscia do krypty.
3. Zbadaj `ash_memory_circle`.

Po odkryciu `ash_memory_circle`:

- Event `ash_memory_revealed` powinien ustawic:
  - `mira_truth_learned=true`
  - `mira_allied=true`
- Objective `clear_miras_name` powinien zostac ukonczony.
- Powinien pojawic sie twist: Odran przy oltarzu z relikwiarzem i krwia.
- Przejscie `to_oath_crypt` powinno byc dostepne, bo wymaga `mira_truth_learned=true`.

Minimalny stan po ruinach:

```text
mira_truth_learned=true
mira_allied=true
completed: clear_miras_name
```

### 5. Final: `oath_crypt`

Wejscie:

- Uzyj przejscia `to_oath_crypt`.
- Event `crypt_intro` pokazuje narracje.
- Walka finalowa to `odrans_champion` wspierany przez `ashen_knight` i 2x `ashen_watcher`; to mocniejsze starcie pod druzyne 6 postaci 1. poziomu.

Dobre zakonczenie:

1. Wejdz w interakcje z `restore_oath`.
2. Event `restore_oath_ending` powinien ustawic:
   - `castellan_exposed=true`
   - `relic_restored=true`
   - `village_saved=true`
3. Objective `uncover_ashen_oath` powinien zostac ukonczony.
4. `finish_scenario` powinno zakonczyc scenariusz.

Stan dobrego finalu:

```text
castellan_exposed=true
relic_restored=true
village_saved=true
completed: uncover_ashen_oath
scenario_finished=true
```

## Alternatywna sciezka: kosztowne zakonczenie

W `oath_crypt` gracz moze wejsc w interakcje z `bargain_with_odran`.

Oczekiwane:

- Event `bargain_ending` ustawia:
  - `castellan_escaped=true`
  - `relic_lost=true`
  - `village_condemned=true`
- Objective `uncover_ashen_oath` zostaje ukonczony.
- Scenariusz konczy sie przez `finish_scenario`.

Ten final jest celowo dostepny nawet bez pelnego sledztwa, jako negatywna lub cyniczna sciezka.

## Negatywne testy przejsc

### `mill_hidden_track` zablokowany przed sekretem

Przejscie:

```text
old_mill -> hill_ruins
exit_id: mill_hidden_track
condition: hidden_mill_route_found=true
```

Przed odkryciem `mill_hidden_route` przejscie powinno byc niedostepne.

### `to_oath_crypt` zablokowany przed plot twistem

Przejscie:

```text
hill_ruins -> oath_crypt
exit_id: to_oath_crypt
condition: mira_truth_learned=true
```

Przed odkryciem `ash_memory_circle` przejscie powinno byc niedostepne.

## Checklist runtime

Uzyj tej listy po zmianach w flow albo mapach.

```text
[ ] `load_scenario_flow("ashen_oath")` przechodzi.
[ ] Player UI pokazuje `Ashen Oath` w katalogu scenariuszy.
[ ] Briefing ma tytul, stakes, rozdzialy i objectives.
[ ] `brindleford_square` laduje sie jako mapa startowa.
[ ] Wszystkie przejscia wskazuja istniejace `exit_id`.
[ ] Wszystkie przejscia wskazuja istniejace `entry_anchor_id`.
[ ] Story eventy maja `audio/voiceover/...`.
[ ] Odkrycie `broken_oath_seal` konczy `recover_warden_medallion`.
[ ] Combat end w `old_mill` konczy `free_the_acolyte`.
[ ] Odkrycie `ash_memory_circle` konczy `clear_miras_name`.
[ ] `restore_oath` konczy kampanie dobrym finalem.
[ ] `bargain_with_odran` konczy kampanie kosztownym finalem.
```

## Komendy weryfikacyjne

Walidacja flow:

```bash
PYTHONPATH=src python -c "from scenario_flow import load_scenario_flow; p=load_scenario_flow('ashen_oath'); print(p['scenario_id'], len(p['maps']), len(p['transitions']), len(p['events']))"
```

Test kontraktowy:

```bash
scripts/safe_pytest.sh --timeout 60 tests/test_ashen_oath_campaign.py
scripts/safe_pytest.sh --timeout 60 tests/test_ashen_oath_enemies.py
```

## Known limitations v1

- Dialogi sa opisane w `player_ui/content/ashen_oath.json` i materialach `.md`, ale nie sa jeszcze pelnym runtime drzewem dialogowym.
- NPC uzywaja istniejacych klas (`guard_npc`, `mage_npc`, `priest_npc`, `bound_smuggler_npc`) jako technicznego nosnika na mapie.
- Asset manifest wskazuje docelowe PNG/MP3, ale same pliki trzeba wygenerowac z `IMAGE_PROMPTS.md` i `AUDIO_PROMPTS.md`.
- Mapy sa proste i techniczne. Sa dobre do walidacji flow, ale pozniej mozna je dopracowac jako lepsze layouty taktyczne.

## Kolejnosc produkcji po tej wersji

1. Wygeneruj sceny i portrety z `IMAGE_PROMPTS.md`.
2. Wygeneruj voiceovery i ambience z `AUDIO_PROMPTS.md`.
3. Dodaj brakujace PNG/MP3 do folderow pod `assets/ui_v2/ashen_oath/`.
4. Uruchom Player UI i sprawdz briefing oraz asset manifest.
5. Rozegraj golden path.
6. Dopiero potem rozbuduj prawdziwe runtime dialogi, jesli UI ma je obslugiwac jako klikalne drzewa.

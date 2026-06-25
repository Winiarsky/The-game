# Obserwacja Sesji I Metadane

Projekt powinien od początku mieć prosty mechanizm obserwacji sesji. Celem nie jest rozbudowana telemetria, tylko wspólny punkt odniesienia do debugowania.

Gdy użytkownik zgłasza problem, powinniśmy móc spojrzeć na ostatnią sesję i zobaczyć:

- jaka była konfiguracja planszy,
- kto był aktywnym aktorem,
- jakie akcje wykonano,
- jakie pola wskazano,
- jakie rzuty wpisano,
- jakie decyzje podjął silnik,
- jakie dane wysłano do warstwy LED,
- gdzie wystąpił błąd.

## Założenia

- Mechanizm działa lokalnie.
- Pliki obserwacji nie trafiają domyślnie do git.
- Format powinien być prosty do czytania przez człowieka i Codexa.
- Preferowany format: JSON Lines (`.jsonl`).
- Każde zdarzenie jest osobną linią JSON.
- Mechanizm nie może być wymagany do działania czystych testów jednostkowych.

## Lokalizacja Plików

Docelowo:

```text
data/session_observations/
```

Przykład:

```text
data/session_observations/2026-06-24_134500_test_movement.jsonl
```

Katalog powinien być ignorowany przez git.

## Minimalny Format Zdarzenia

Każde zdarzenie powinno zawierać:

```json
{
  "ts": "2026-06-24T13:45:00.000Z",
  "session_id": "2026-06-24_134500_test_movement",
  "seq": 1,
  "event_type": "movement_range_calculated",
  "payload": {}
}
```

## Zalecane Typy Zdarzeń

### Sesja

- `session_started`
- `session_finished`
- `session_error`

### Plansza

- `board_backend_selected`
- `board_scan_requested`
- `board_scan_received`
- `board_scan_cancelled`
- `led_feedback_requested`
- `led_feedback_sent`

### Ruch

- `movement_range_requested`
- `movement_range_calculated`
- `movement_path_selected`
- `movement_committed`
- `movement_rejected`

### Rzuty

- `roll_requested`
- `roll_entered`
- `roll_resolved`

### Walka

- `setup_step_started`
- `setup_step_finished`
- `enemy_initiative_rolled`
- `initiative_set`
- `turn_started`
- `attack_declared`
- `attack_resolved`
- `damage_applied`
- `turn_finished`

## Przykład Zdarzeń Ruchu

```jsonl
{"ts":"2026-06-24T13:45:00.000Z","session_id":"demo","seq":1,"event_type":"turn_started","payload":{"actor_id":"hero_1","position":[4,5]}}
{"ts":"2026-06-24T13:45:01.000Z","session_id":"demo","seq":2,"event_type":"movement_range_calculated","payload":{"actor_id":"hero_1","origin":[4,5],"speed_feet":30,"reachable_count":41}}
{"ts":"2026-06-24T13:45:10.000Z","session_id":"demo","seq":3,"event_type":"movement_path_selected","payload":{"actor_id":"hero_1","origin":[4,5],"destination":[8,7],"path":[[4,5],[5,6],[6,6],[7,7],[8,7]],"cost_feet":25}}
```

## Przykład Zdarzeń Rzutu

```jsonl
{"ts":"2026-06-24T13:46:00.000Z","session_id":"demo","seq":4,"event_type":"roll_entered","payload":{"roll_type":"attack_roll","actor_id":"hero_1","natural_roll":14,"modifier":5}}
{"ts":"2026-06-24T13:46:00.100Z","session_id":"demo","seq":5,"event_type":"roll_resolved","payload":{"roll_type":"attack_roll","natural_roll":14,"total_result":19,"target_number":16,"success":true,"critical_hit":false,"critical_miss":false}}
```

## Wymagania Implementacyjne

- Obserwator powinien być małą klasą lub funkcją adaptera, nie globalnym loggerem.
- Czysta logika gry powinna zwracać wyniki, które runtime może zapisać jako zdarzenia.
- Testy jednostkowe nie powinny wymagać zapisu na dysk.
- Testy integracyjne mogą używać obserwatora zapisującego do katalogu tymczasowego.
- Każdy event powinien mieć stabilne `event_type`.

## Jak Codex Ma Korzystać Z Obserwacji

Przy zgłoszeniu problemu użytkownik może podać:

- plik `.jsonl`,
- krótki opis co zrobił,
- oczekiwany wynik,
- rzeczywisty wynik.

Codex powinien wtedy:

1. Odczytać ostatnie zdarzenia.
2. Ustalić, czy problem jest w logice, UI, adapterze LED czy hardware.
3. Zaproponować małą poprawkę i test.

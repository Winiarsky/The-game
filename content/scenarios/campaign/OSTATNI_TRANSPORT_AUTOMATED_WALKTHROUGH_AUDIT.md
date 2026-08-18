# Ostatni transport — automatyczny walkthrough kampanii

Data audytu: 2026-08-10  
Zakres: uruchomienie gry → Nessa → kontrakt → podróż → Głodne Cienie → zwycięstwo  
Test wykonywalny: `tests/integration/test_ostatni_transport_campaign_walkthrough.py`

## Wynik

Ścieżka kampanii do zakończenia pierwszego encountera jest spójna i nie ma
wykrytego błędu blokującego. Nowy test przechodzi cały golden path na jednej
instancji `ExplorationUiSession`, dzięki czemu sprawdza również zachowanie flag,
drużyny i klienta NPC po zmianie scenariusza.

Pakiet regresji kampanii: **74/74 testów zaliczonych**. Osobny audyt snapshotu
AI oraz Game Over/Retry również przechodzi.

## Automatycznie przechodzone etapy

| Etap | Sprawdzane zachowanie | Wynik |
|---|---|---|
| Launcher | menu Nowa gra; tylko kampania `ostatni_transport_00_gildia` | OK |
| Wybór drużyny | skany kart Garrana i Erynda; ACCEPT drużyny i scenariusza | OK |
| Start Gildii | wymagany backend planszy, mapa papierowa, preview lokacji, ustawienie Nessy | OK |
| Odprawa | zaginięcie, ładunek i ludzie rozwiązują się bez testu | OK |
| Intuicja | Garran wykonuje fizyczny test i odkrywa priorytet szarego pyłu | OK |
| Dokumenty | tylko Erynd wykonuje test i ustawia flagę podejrzenia magii | OK |
| Negocjacje | opis argumentu, klasyfikacja, przewaga 2d20, wynik i dynamiczna odpowiedź Nessy | OK |
| Przyjęcie zadania | aktywacja questa i odblokowanie bramy wyjściowej | OK |
| Podróż | normalne tempo, propagacja czasu, wiedzy i warunków kontraktu | OK |
| Handoff | ta sama sesja ładuje `ostatni_transport_01_zawalona_droga` | OK |
| Otwarcie walki | natychmiastowa zasadzka; eksploracja pozostaje ukryta | OK |
| Setup | mapa v4, dwa pola bohaterów, wariant dwóch Cieni i elementy terenu | OK |
| Inicjatywa | premia wynikająca z wiedzy Erynda wymaga i przyjmuje dwa wyniki d20 | OK |
| Encounter | aktywny stan walki, checkpoint Retry, ataki Cieni `+5/+6` | OK |
| Zwycięstwo | wszystkie wrogie figurki usunięte; flaga zwycięstwa i `road_aftermath` odblokowane | OK |

## Osłony przed regresją

Istniejące testy dołączone do audytu potwierdzają dodatkowo:

- brama wyjściowa jest zablokowana przed przyjęciem zadania;
- Eryndowy kafelek nie pojawia się bez Erynda w drużynie;
- absurdalna, niebezpieczna i off-topic deklaracja negocjacyjna nie może zmienić
  autorskiego wyniku mechanicznego;
- brak lub błędna odpowiedź modelu korzysta z bezpiecznego fallbacku;
- porażka encountera nie odsłania eksploracji i prowadzi do Game Over;
- Retry odtwarza skład, pozycje, inicjatywę, morale i setup;
- warianty przeciwników 1–5, passive defensive spots, utility AI i ucieczka
  pozostają deterministyczne;
- 64 symulowane walki kończą się bez timeoutu i deadlocku.

## Znane ograniczenia

Automat nie zastępuje następujących testów:

1. Prawdziwego sprzętu: czujników pól, WLED, drukowanej mapy i fizycznych kart.
2. Sieciowego wywołania Gemini. Walkthrough używa deterministycznego klienta
   Nessy; osobne testy obejmują walidację i fallback odpowiedzi modelu.
3. Ręcznego rozegrania wszystkich tur encountera przez UI. Golden path wymusza
   wynik zwycięstwa po prawidłowym uruchomieniu walki; rzeczywiste AI jest
   rozgrywane oddzielnie w macierzy 64 playtestów.
4. Dalszej eksploracji Mapy 1, ponieważ `road_aftermath` pozostaje obecnie
   świadomym placeholderem następnego etapu produkcji.

## Naprawione znalezisko poza kampanią

Globalny `test_repository_content_audit_has_no_errors` wykrył, że pole `(12,18)`
było jednocześnie przyciskiem `social_lab` oraz pozycją punktu
`training_compass`, mimo że kompas należy do `exploration_course`. Kompas został
przeniesiony na wolne pole `(6,18)` wewnątrz właściwej lokacji. Globalny audyt
contentu przechodzi po poprawce.

## Jak uruchomić ponownie

```bash
scripts/safe_pytest.sh --timeout 60 \
  tests/integration/test_ostatni_transport_campaign_walkthrough.py \
  tests/unit/test_launcher_ui.py \
  tests/unit/test_ostatni_transport_map0.py \
  tests/unit/test_nessa_dynamic_negotiation.py \
  tests/unit/test_scenario_continuation_flow.py \
  tests/unit/test_glodne_cienie_playtest.py \
  tests/unit/test_utility_enemy_ai.py
```

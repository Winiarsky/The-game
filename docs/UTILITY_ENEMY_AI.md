# Parametryczne AI przeciwników — kontrakt `weighted_utility_v1`

Status: działający pionowy przekrój; cechy pozycyjne czekają na pełne strojenie  
Pierwszy profil: `content/ai_profiles/hungry_shadow_pack.json`

## 1. Cel

AI ma podejmować rozsądne, ale nie całkowicie identyczne decyzje bez używania LLM i bez scenariuszowych instrukcji zapisanych w kodzie. Konfiguracja określa styl przeciwnika przez wagi; silnik odpowiada za zasady D&D, legalność ruchu i wykonanie akcji.

Model celowo nie planuje kilku tur naprzód. W każdej turze wybiera jeden plan spośród legalnych kandydatów.

Runtime obsługuje już profil i role z contentu, odtwarzalny szum, pamięć celu,
morale, wymuszone `flee`/`cornered`, pola ucieczki oraz osobne wyniki `dead` i
`escaped`. Pierwszy przekrój używa uproszczonych wartości części cech
pozycyjnych; pełne obliczenia osłony, izolacji, OA, hazardu i zagrożenia strefy
pozostają następnym etapem strojenia, a nie deklarowanym ukończonym systemem.

## 2. Granice odpowiedzialności

Silnik:

- generuje legalne cele, pola końcowe, ścieżki i akcje;
- wylicza cechy kandydatów w ujednoliconym zakresie;
- stosuje wagi z profilu;
- dodaje kontrolowany szum;
- zwraca jeden kompletny plan: intencję, cel, pole, ścieżkę i akcję;
- wykonuje zatwierdzony plan przez istniejące mechaniki ruchu i ataku.

JSON:

- wskazuje rolę przeciwnika;
- ustawia progi, wagi i wielkość szumu;
- wskazuje tagi stref ważnych dla profilu;
- definiuje morale stada;
- nie zawiera kodu, wyrażeń Python ani dowolnych warunków logicznych.

LLM nie bierze udziału w wyborze. Może później opisać gotowy plan, ale brak lub błąd modelu nie może zmieniać mechaniki.

## 3. Dane wejściowe decyzji

`UtilityDecisionContext` zawiera wyłącznie jawny stan:

- aktualnego aktora, jego rolę i współczynnik `hp_ratio`;
- widocznych przeciwników i sojuszników;
- planszę, teren, obiekty sceny oraz strefy otagowane w scenariuszu;
- pozostały ruch i ekonomię akcji;
- stan morale grupy;
- `encounter_seed`, numer rundy, `actor_id` i licznik decyzji aktora.

Profil nie otrzymuje klasy bohatera, kart na ręce, niewydanych zasobów, ukrytych aktorów ani przyszłych wyników kości.

## 4. Kandydaci

Generator tworzy kandydatów jako:

```text
UtilityCandidate(
    intent,
    target_id | null,
    destination,
    path,
    action,
    features,
)
```

Pierwsza wersja obsługuje sześć intencji:

| Intencja | Znaczenie |
|---|---|
| `engage` | pozostań albo przemieść się i wykonaj legalny atak |
| `advance` | zbliż się do wybranego celu, gdy atak nie jest jeszcze możliwy |
| `regroup` | zakończ ruch bliżej sojusznika, przewodnicy lub osłony; użyj Disengage, jeśli droga prowokuje OA, w innym przypadku Dodge |
| `guard` | utrzymaj albo zajmij pole kontrolujące oznaczoną strefę |
| `flee` | przemieść się ku wyjściu, preferując Disengage przy zagrożeniu OA, w innym przypadku Dash |
| `cornered` | Dodge albo zaatakuj aktora blokującego najkrótszą drogę ucieczki |

`flee` uczestniczy również w zwykłej punktacji, dlatego ciężko ranny albo przestraszony osobnik może wycofać się przed złamaniem całego stada. Morale równe zero wymusza `flee` albo `cornered`. `Search` jest fallbackiem, a nie wymuszeniem: pojawia się dopiero wtedy, gdy nie ma widocznego celu i AI nie wybrało ucieczki.

Generator nie powinien punktować każdego pola planszy. Z osiągalnych pól buduje mały, zróżnicowany zbiór:

- `engage`: dla każdego celu najwyżej trzy pola — najtańsze pole ataku, najlepsza osłona i najlepsze wsparcie sojusznika;
- `advance`: dla każdego celu jedno pole dające największy postęp, z kosztem ścieżki jako tie-breakerem;
- `regroup`: najwyżej po jednym najlepszym polu przy przewodnicy, najbliższym sojuszniku, osłonie i strefie ochrony;
- `guard`: najwyżej cztery pola o najlepszym `guard_position_quality`;
- `flee`: najwyżej dwa wyjścia — najbliższe według kosztu ścieżki i najbezpieczniejsze według ryzyka OA oraz hazardu;
- duplikaty `(intent, target, destination, action)` są usuwane.

Po tej redukcji dla każdej intencji pozostaje najwyżej `candidate_limits.per_intent`, a łącznie `candidate_limits.total` kandydatów. Dla `engage` i `advance` zachowujemy najpierw po jednym wariancie na każdy widoczny cel, dopiero potem dodatkowe warianty pozycyjne. Limit końcowy odrzuca najpierw duplikujące się warianty o najdroższej ścieżce, ale pozostawia co najmniej jednego kandydata każdej legalnej intencji. Zapobiega to kombinatoryce na planszy 20 × 30 bez sprowadzania wyboru znowu do „najbliższego pola”.

## 5. Cechy

Wszystkie cechy mają zakres `0.0–1.0`. Brak zastosowania oznacza `0.0`.

| Id cechy | Obliczenie |
|---|---|
| `can_attack` | `1`, jeśli kandydat kończy się legalnym atakiem |
| `distance_progress` | zmniejszenie odległości do celu podzielone przez maksymalny ruch, ograniczone do zakresu |
| `target_isolation` | `0` przy sojuszniku celu do 5 ft, `0.5` przy 10 ft, `1` od 15 ft |
| `target_injury` | `1 - target.hp / target.max_hp` |
| `ally_support` | `1` przy sojuszniku AI do 5 ft od celu, `0.5` przy 10 ft |
| `threat_to_guard_zone` | `1` w strefie chronionej, `0.5` do 10 ft od niej |
| `end_in_cover` | wartość osłony pola: brak `0`, half cover `0.5`, three-quarters `1` |
| `end_near_leader` | `1` do 10 ft od żywej przewodnicy, `0.5` do 20 ft |
| `pack_separation` | odległość pola końcowego od najbliższego żywego sojusznika: `0` do 5 ft, `0.5` przy 15 ft, `1` od 30 ft |
| `cohesion_gain` | zmniejszenie oddalenia od stada względem pola początkowego, znormalizowane do maksymalnego ruchu |
| `guard_position_quality` | `1` na polu kontrolującym wejście do chronionej strefy, `0.5` na sąsiednim polu osłaniającym |
| `self_injury` | `1 - self.hp / self.max_hp` |
| `opportunity_risk` | liczba możliwych opportunity attacks podzielona przez 2, maksymalnie `1` |
| `hazard_exposure` | udział kosztu ścieżki prowadzący przez ogień lub scenariuszowy hazard |
| `escape_progress` | zmniejszenie odległości do najbliższego pola ucieczki podzielone przez maksymalny ruch |
| `morale_pressure` | `1 - current_morale / starting_morale`; przy braku grupowego morale wynosi `0` |
| `repeats_target` | `1`, jeśli cel był celem poprzedniej decyzji aktora |

Cechy ciągłe stanowią „logikę rozmytą”. Przykładowo Cień nie przełącza się nagle na osobny skrypt przy 50% PW — rosnące `self_injury` stopniowo zwiększa atrakcyjność `regroup` i `flee`, a zmniejsza atrakcyjność ryzykownego `engage`.

## 6. Punktacja

Dla każdego kandydata:

```text
raw_score = base_score[intent]
          + suma(feature_value * weight[role][intent][feature])

final_score = raw_score + seeded_uniform(noise.min, noise.max)
```

Następnie wynik jest ograniczany do `score_bounds`. Wygrywa najwyższy `final_score`. Remis po zaokrągleniu rozstrzygają kolejno:

1. wyższy `raw_score`;
2. niższy koszt ścieżki;
3. stabilne `target_id`;
4. kolumna i rząd pola końcowego.

Szum jest mały względem najważniejszych wag. Ma czasami zmienić wybór między dwiema podobnie dobrymi flankami, ale nigdy przekonać rannego zwierzęcia do wejścia w ogień albo zignorowania młodego.

## 7. Losowość odtwarzalna

Każdy kandydat otrzymuje osobny seed z:

```text
encounter_seed + round + actor_id + decision_index + candidate_stable_key
```

Nie używamy czasu systemowego ani globalnego `random`. Ten sam snapshot daje tę samą decyzję. Nowy encounter seed może dać inny przebieg, a Retry odtwarza warunki zapisane w checkpointcie.

W logu zapisujemy `raw_score`, szum, wynik końcowy i trzy składniki o największej wartości bezwzględnej. UI pokazuje tylko krótką intencję, np. „ranny Cień cofa się ku przewodnicy”.

## 8. Twarde reguły

Przed utility scoringiem obowiązuje krótka lista reguł, których nie stroimy wagami:

1. martwy lub niezdolny do działania aktor nie planuje tury;
2. warunki D&D ograniczają legalne akcje zgodnie z istniejącym silnikiem;
3. `pack_morale <= 0` i legalna ścieżka ucieczki wymusza `flee`;
4. `pack_morale <= 0` bez legalnej ścieżki wymusza `cornered`;
5. przy morale większym od zera `flee` konkuruje z innymi legalnymi intencjami według wag roli;
6. brak widocznego przeciwnika uruchamia istniejące `Search`, chyba że wybrano albo wymuszono `flee`;
7. AI nigdy nie wybiera nielegalnego celu lub pola tylko dlatego, że otrzymało wysoki wynik.

Morale może wynosić zero przy zablokowanym wyjściu. Nie potrzeba osobnego `break_pending`: po otwarciu drogi następna decyzja automatycznie wybiera `flee`.

## 9. Morale grupy

Morale jest prostym licznikiem należącym do encountera, nie do aktora. Konfiguracja podaje wartość początkową dla liczby bohaterów oraz jednorazowe zdarzenia `delta`.

Resolver morale:

1. odrzuca zdarzenie już użyte, jeśli ma `once: true`;
2. dodaje `delta` i ogranicza wynik do `0..maximum`;
3. zapisuje id wykorzystanego zdarzenia;
4. ustawia wynikowe flagi scenariusza;
5. nie porusza aktorów i nie kończy ich aktualnej tury.

Po osiągnięciu zera każdy członek stada wybiera ucieczkę dopiero w swojej turze. Jeśli żadna postać nie blokuje wyjścia i nie deklaruje pościgu, runtime może zakończyć pozostałą sekwencję jako zbiorowy odwrót.

## 10. Ucieczka, śmierć i zwycięstwo

Scenariusz oznacza co najmniej jedno pole tagiem `pack_escape`. Gdy przeciwnik realizujący `flee` wejdzie na takie pole:

1. kończy ruch;
2. otrzymuje stan encountera `escaped`;
3. znika z aktywnej planszy, inicjatywy, blokowania ruchu i listy legalnych celów;
4. pozostaje wyłącznie w outcome ledgerze jako żywy zbiegły przeciwnik;
5. system prosi o zdjęcie figurki z fizycznej planszy.

Przeciwnicy nie korzystają z modelu nieprzytomności. Gdy ich PW spadną do zera:

1. natychmiast otrzymują wynik `dead`;
2. nie wykonują death saves i nie mogą zostać ustabilizowani;
3. znikają z inicjatywy, blokowania ruchu i listy legalnych celów;
4. system prosi o zdjęcie figurki;
5. outcome ledger zapisuje śmierć osobno od ucieczki.

Warunek zwycięstwa jest jeden:

```text
active_hostile_count == 0
```

Aktywny przeciwnik to aktor z `hp > 0`, który nie otrzymał wyniku `escaped`. Drużyna może więc wygrać przez zabicie wszystkich, ucieczkę wszystkich albo dowolną kombinację. Sposób rozstrzygnięcia zapisujemy do późniejszego naliczania PD i konsekwencji, ale na tym etapie nie przypisujemy mu nagrody.

## 11. Integracja z obecnym kodem

Pierwsza implementacja powinna rozszerzyć, a nie zastąpić obecny fallback:

- `combat/enemy_ai.py` zachowuje aktualny `plan_enemy_turn` dla aktorów bez profilu;
- nowy czysty moduł `combat/utility_ai.py` ładuje już zwalidowane dataclasses, generuje i punktuje kandydatów;
- `application/enemy_turn_flow.py` przekazuje profil oraz encounter context do planera;
- loader scenariusza rozwiązuje `ai_profile_ref` i `ai_role`, tak jak dziś rozwiązuje `source_ref` potwora;
- snapshot przechowuje `encounter_seed`, morale, wykorzystane zdarzenia oraz poprzedni cel każdego aktora;
- UI nadal pokazuje zamiar przed fizycznym przesunięciem figurki.

Nie należy umieszczać odczytu pliku JSON w `combat/utility_ai.py`. Loader zamienia content na niemutowalne dataclasses przed rozpoczęciem walki.

Docelowe powiązanie w scenariuszu:

```json
{
  "encounter_ai": {
    "profile_ref": "hungry_shadow_pack"
  },
  "actors": [
    {
      "id": "hungry_shadow_a",
      "source_ref": "hungry_shadow",
      "ai_role": "skirmisher"
    },
    {
      "id": "hungry_shadow_leader",
      "source_ref": "hungry_shadow_leader",
      "ai_role": "leader"
    }
  ],
  "environment": [
    {
      "id": "western_culvert",
      "tags": ["pack_den"]
    },
    {
      "id": "stream_escape",
      "tags": ["pack_escape"]
    }
  ]
}
```

`profile_ref` jest rozwiązywany względem `content/ai_profiles/`. Rola aktora musi istnieć w profilu. Brak `encounter_ai` zachowuje obecne AI, natomiast nieznany profil, rola lub tag wymagany przez `zone_tags` jest błędem preflightu.

## 12. Minimalny zakres pierwszej implementacji

W pierwszym przebiegu wystarczą:

- intencje `engage`, `advance`, `regroup`, `guard`, `flee`, `cornered`;
- siedemnaście cech wymienionych w tym dokumencie;
- jeden profil stada i dwie role;
- morale oraz jedna strefa ochrony i jedna grupa pól ucieczki;
- seeded noise;
- diagnostyczny log punktacji.

Nie implementujemy drzewa zachowań, uczenia maszynowego, planowania wieloturowego, dowolnego języka warunków w JSON ani decyzji LLM.

## 13. Kryteria testowe

- wyższa izolacja zwiększa wynik ataku harcownika;
- wzrost `self_injury` płynnie przesuwa preferencję z `engage` do `regroup`;
- odpowiednio wysokie `self_injury` i `morale_pressure` pozwalają wybrać `flee` przed złamaniem całego stada;
- zagrożenie strefy młodego ma większy wpływ na przewodnicę niż na harcownika;
- hazard i opportunity attacks obniżają wynik ryzykownej ścieżki;
- ten sam seed i stan zawsze zwracają ten sam plan;
- różne seedy mogą zmienić wybór tylko między kandydatami o zbliżonym `raw_score`;
- morale zero wymusza `flee` albo `cornered`, niezależnie od wag;
- wejście na `pack_escape` usuwa żywego aktora z aktywnego encountera i zapisuje `escaped`;
- przeciwnik przy 0 PW otrzymuje `dead`, nigdy `unconscious`;
- zwycięstwo następuje po usunięciu ostatniego aktywnego przeciwnika niezależnie od liczby śmierci i ucieczek;
- aktor bez profilu zachowuje aktualne AI najbliższego legalnego celu.

### Roboczy smoke test wag Głodnych Cieni

Wartości nie uwzględniają szumu `−3..+3`:

| Sytuacja | Kandydat | Raw score |
|---|---|---:|
| Zdrowy harcownik, odizolowany cel i wsparcie stada | `engage` | 71.8 |
| Ten sam harcownik, bez presji na odwrót | `regroup` | 38.2 |
| Ciężko ranny harcownik, droga przez hazard i jedno OA | `engage` | 34.2 |
| Ten sam ranny harcownik, ruch do osłony i przewodnicy | `regroup` | 62.0 |
| Ten sam ranny harcownik, morale w połowie i czysta droga do wyjścia | `flee` | 74.5 |
| Przewodnica może zająć dobre pole przy zagrożonym przepuście | `guard` | 85.0 |
| Przewodnica może zamiast tego od razu zaatakować intruza | `engage` | 65.2 |

Te przykłady pokazują oczekiwany kierunek, nie gwarantowany scenariusz każdej tury. Właściwy test korzysta ze wszystkich legalnych kandydatów wygenerowanych z planszy.

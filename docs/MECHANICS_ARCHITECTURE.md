# Mechanics Architecture

Ten dokument opisuje aktualną siatkę klas mechanik oraz zasady dodawania nowych funkcjonalności.

Cel tej warstwy: nowe akcje, czary, reakcje i interakcje mają trafiać do przewidywalnej hierarchii, zamiast rozrastać się jako warunki porozrzucane po UI.

## Zasada Główna

Mechanika ma trzy warstwy:

1. **Deklaracja mechaniki** w `src/dnd_board_game/actions/`.
2. **Czyste rozstrzyganie zasad** w `src/dnd_board_game/rules/`, `world/`, `actors/`, `combat/`.
3. **Transport i prezentacja** w `src/dnd_board_game/ui/` oraz `hardware/`.

Warstwa `actions/` opisuje czym jest akcja i jakiego rodzaju zasobów/targetowania używa. Nie powinna znać Flask, WLED, seriala, sesji webowej ani lokalnego czasu.

## Aktualna Hierarchia

```text
ActionMechanic
├── CombatActionMechanic
│   ├── AttackMechanic
│   │   ├── BasicAttack
│   │   │   ├── MeleeAttack
│   │   │   │   └── OpportunityAttack
│   │   │   └── RangedAttack
│   │   ├── SpellAttack
│   │   │   ├── SpellAttackRoll
│   │   │   └── SpellSaveAttack
│   │   │       └── AreaSpellAttack
│   │   └── ReadyAttack
│   ├── MovementMechanic
│   │   ├── BasicMove
│   │   └── DashAction
│   ├── DefensiveAction
│   │   ├── DodgeAction
│   │   └── DisengageAction
│   ├── SupportAction
│   │   ├── HelpAction
│   │   ├── ConcentrationAction
│   │   └── ReadyAction
│   ├── HealingMechanic
│   │   ├── SpellHealing
│   │   ├── ItemHealing
│   │   └── CustomHealing
│   ├── ItemAction
│   │   └── StrengthPotionAction
│   └── SceneInteractionMechanic
│       └── ObjectInteraction
└── ExplorationActionMechanic
```

`ExplorationActionMechanic` jest miejscem na kolejne uporządkowanie wyzwań, NPC i eksploracji. Obecny etap porządkuje przede wszystkim combat.

## Pliki

- `actions/base.py`: wspólne enumy i `ActionMechanic`.
- `actions/attacks.py`: ataki bronią, czary ofensywne, area spell, opportunity/ready attack.
- `actions/movement.py`: ruch i Dash.
- `actions/turn_actions.py`: Dodge, Disengage, Help, koncentracyjne akcje wsparcia, Ready, item actions.
- `actions/healing.py`: leczenie czarem, itemem albo customowe.
- `actions/interactions.py`: interakcje z obiektami sceny.
- `actions/catalog.py`: fabryki mapujące obecny content/runtime na klasy mechanik.
- `actions/resolution.py`: małe serwisy aplikacyjne rozstrzygające akcję + zasób + efekt domenowy.

## Serwisy Rozstrzygania

`actions/resolution.py` jest warstwą pośrednią między UI a czystym combatem. UI może wybrać cel, zebrać Enter/kliknięcie i wpisać wynik rzutu gracza, ale nie powinno samo składać pełnego efektu typu "zużyj akcję, zużyj slot, rzuć save, policz obrażenia, podmień aktora".

Aktualne serwisy:

- `ActionResourceResolver`: zużywa akcję główną i opcjonalny slot czaru.
- `AttackActionResolver`: aplikuje obrażenia do pojedynczego celu, także po rzucie obronnym.
- `SpellSaveAttackResolver`: potwierdza czar przeciw pojedynczemu celowi i wykonuje rzut obronny celu.
- `AreaSpellResolver`: potwierdza czar obszarowy, wykonuje save'y celów i aplikuje obrażenia w obszarze.
- `HealingActionResolver`: zużywa akcję/slot i aplikuje leczenie.

Kolejne refaktory powinny przenosić podobne orkiestracje do tej warstwy, jeśli zaczynają łączyć więcej niż jeden element zasad. Przykłady: flankowanie z modyfikatorem ataku, koncentracja po rzuceniu czaru, efekty warunków po trafieniu.

## Reguły Dodawania Feature'a

1. **Najpierw nazwać mechanikę.**
   Dodaj klasę w `actions/`, jeśli feature jest nowym typem akcji, reakcji, ruchu, czaru albo interakcji.

2. **Dziedziczyć tylko po relacji "jest rodzajem".**
   Przykład: `AreaSpellAttack` jest rodzajem `SpellSaveAttack`, więc dziedziczy.
   Parametry typu DC, zasięg, kształt obszaru, koszt slotu albo typ obrażeń są danymi, nie osobnymi klasami.

3. **Rozstrzyganie zasad zostaje poza UI.**
   Rzut obronny, obrażenia, zasięg, ścieżka, line of sight i ekonomia akcji muszą być w `rules/`, `world/`, `combat/` albo w serwisie `actions/resolution.py`, jeśli chodzi o połączenie kilku czystych reguł w jedną akcję.

4. **UI tylko wybiera, pokazuje i transportuje.**
   `exploration_app.py` może pokazać `mechanic.as_payload()`, ale nie powinien decydować, czy czar jest melee, ranged, save-spell albo area-spell.

5. **Content jest mapowany przez fabrykę.**
   Jeśli `AttackSource`, `HealingSource` albo `ScenarioCombatActionDefinition` dostają nowe pole, dodaj mapowanie w `actions/catalog.py` albo module konkretnej mechaniki.

6. **Każda nowa mechanika ma test hierarchii.**
   Test powinien sprawdzać klasę, `inheritance_path()`, `resource`, `targeting` i tagi.

7. **Każda nowa mechanika ma test rozstrzygania.**
   Klasa mechaniki nie wystarcza. Drugi test musi sprawdzić realny efekt w czystej domenie albo sesji UI.

8. **Dokumenty są częścią implementacji.**
   Przy nowej mechanice aktualizuj `docs/RULES_DECISIONS.md`, `TODO.md` i w razie nowej gałęzi klas ten plik.

## Jak Dodać Flankowanie

1. Dodać klasę, np. `FlankingModifier` albo `PositionalAttackModifier`, jeśli flankowanie będzie modyfikatorem ataku, a nie akcją.
2. Dodać czystą funkcję w `combat/` albo `world/`, która wykrywa pozycję względem celu.
3. Podpiąć wynik do istniejącego `AttackSource` przez modyfikatory rzutu, bez zmian w UI poza komunikatem.
4. Dodać test: dwóch sojuszników po przeciwnych stronach celu daje premię/przewagę zgodnie z przyjętą decyzją.
5. Zapisać decyzję w `docs/RULES_DECISIONS.md`, bo flankowanie w 5e jest regułą opcjonalną.

## Jak Dodać Nowy Czar

1. Użyć istniejącej gałęzi:
   - attack roll: `SpellAttackRoll`,
   - save przeciw celowi: `SpellSaveAttack`,
   - obszar: `AreaSpellAttack`.
2. Dodać dane do contentu: zasięg, damage, `spell_level`, opcjonalnie `area`, `save_ability`, `save_damage_on_success`.
3. Jeśli czar wymaga nowej geometrii, rozszerzyć `combat/spells.py` i dodać test geometrii.
4. Jeśli czar wymaga nowego efektu stanu, dodać czystą strukturę efektu i test wygasania.

## Aktualny Stan Refaktoru

Ten etap ma dwie części:

1. Klasowa warstwa deklaracji mechanik jest podpięta do payloadu UI.
2. Pierwsza część orkiestracji walki została przeniesiona z `exploration_app.py` do `actions/resolution.py`: akcja + slot, czary na save, czary obszarowe, obrażenia po save i leczenie.

Nie cała walka została jeszcze rozbita na małe serwisy. Ruch, reakcje, Ready/Help/Dodge/Disengage i interakcje sceny nadal mają część orkiestracji w UI/session, ale nowe funkcjonalności powinny być dodawane już według powyższego wzorca.

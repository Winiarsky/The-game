"""Seeded smoke/balance report using the production confrontation rules."""
from __future__ import annotations
import argparse
from dataclasses import replace
from pathlib import Path
import random
from statistics import mean, median
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dnd_board_game.application.confrontation import build
from dnd_board_game.rules import confrontation as rules
from dnd_board_game.rules.pooled_mana import COLORS
from dnd_board_game.rules.exploration_mana_catalog import HEROES
from dnd_board_game.scenarios.confrontation import scene_by_id
from dnd_board_game.ui.training_arena import training_hero


def simulate(template: rules.Confrontation, seed: int, *, cooperation: bool) -> tuple[bool,int,int]:
    rng=random.Random(seed)
    state=rules.begin_preparation(template)
    while state.stage=='approach':
        options=rules.available_approaches(state)
        selected=max(options,key=lambda p:max(0,min(1,(21-p.dc+p.test_modifier)/20))*((p.die+1)/2+p.impact_modifier))
        state=rules.select_approach(state,selected.approach_id)
    state=rules.shuffle(state)
    deck=[c for c in COLORS for _ in range(state.mana.copies)]
    rng.shuffle(deck)
    state=replace(state,mana=replace(state.mana,deck=tuple(deck)))
    tests=0
    for _ in range(1000):
        if state.stage=='result':return state.outcome=='success',state.round,tests
        if state.mana.phase in {'reveal','burn'}:
            state=rules.report_color(state,state.mana.deck[0])
        elif state.mana.phase=='choose':
            def card_priority(index: int) -> tuple[int, ...]:
                candidate = rules.take(state, index)
                return tuple(candidate.passive(state.actor.id, kind) - state.passive(state.actor.id, kind)
                             for kind in ('test', 'impact', 'recover', 'support', 'guard'))
            state=rules.take(state,max(range(len(state.mana.offer)),key=card_priority))
        elif state.stage=='turn':
            bonus=rules.available_tiers(state)[-1][1]
            chance=max(0,min(1,(21-state.actor.dc+state.actor.test_modifier+bonus+state.passive(state.actor.id,'test')+dict(state.aids).get(state.actor.id,0))/20))
            targets=list(rules.support_targets(state))
            if cooperation and targets and chance<0.35:
                target=min(targets,key=lambda p:p.dc-p.test_modifier)
                state=rules.support(state,target.id)
            else:
                state=rules.declare(state,bonus);tests+=1
        elif state.stage=='check':state=rules.roll_check(state,rng.randint(1,20))
        elif state.stage=='impact':state=rules.roll_impact(state,rng.randint(1,state.actor.die))
        elif state.stage=='recovery':state=rules.confirm_recovery(state)
        elif state.stage=='reaction':state=rules.react(state,rng.randint(1,4))
        else:state=rules.advance(state)
    raise RuntimeError('Konfrontacja nie zakończyła się w limicie operacji.')


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials',type=int,default=50)
    parser.add_argument('--output',type=Path,default=Path('docs/reports/PARTY_CONFRONTATIONS_V01.md'))
    args=parser.parse_args()
    if not 1<=args.trials<=10000:parser.error('trials: 1–10000')
    actors={h:training_hero(h) for h in HEROES}
    rows=[]
    for count in (3,4,5,6):
        for scene in ('nessa_raise','sealed_cache'):
            for cooperation in (False,True):
                results=[]
                for offset in range(7):
                    party=tuple(actors[HEROES[(offset+i)%7]] for i in range(count))
                    template=build(party,scene_by_id(scene))
                    results.extend(simulate(template,100000*offset+i,cooperation=cooperation) for i in range(args.trials))
                rows.append(f'| {count} | {scene} | {"Pomoc przy szansie <35%" if cooperation else "Zawsze test"} | {100*mean(r[0] for r in results):.1f}% | {median(r[1] for r in results):g} | {mean(r[1] for r in results):.2f} | {mean(r[2] for r in results):.1f} |')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text('# Konfrontacje drużynowe — raport startowy\n\n'
        f'Po {args.trials} prób na każdy z 7 rotowanych składów w każdym wierszu; stałe ziarna. Silnik produkcyjny, pełna talia i fizyczna oferta.\n\n'
        'Obie strategie dobierają do sześciu kart i wykorzystują premię +1 za fizyczną kartę. Preferują przyrost pasywów: test, efekt, odzysk, wsparcie, ochrona; jedna dodatkowo wspiera przy niskiej szansie. To proste punkty odniesienia, bez pełnej optymalizacji kolorów i kosztów. Atut nie podwaja testów eksploracji. Nie jest to model zachowania ludzi ani pomiar czasu przy stole.\n\n'
        '| Osób | Scena | Strategia | Sukces | Mediana rund | Średnia rund | Testów |\n|---|---|---|---|---|---|---|\n'+'\n'.join(rows)+'\n\n'
        'Podatność celowo wpływa na ST i kość wpływu. Solo nie ma wsparcia. Wyniki wymagają ręcznego ogrania: szczególnie udział odpornych metod, czytelność rozliczania kart i czas dwóch rzutów.\n')
    print(args.output)

if __name__=='__main__':main()

"""Pure party confrontations. Physical card economy is shared with combat."""
from __future__ import annotations
from dataclasses import dataclass, replace, asdict
from typing import Mapping
from . import pooled_mana as cards

TIERS = tuple((minimum, bonus, 1) for minimum, bonus in cards.CHARGE_BONUS_TIERS)
PASSIVE_KINDS = frozenset({'test', 'impact', 'support', 'guard', 'recover'})


@dataclass(frozen=True, slots=True)
class Participant:
    id: str
    name: str
    method: str
    test_modifier: int
    impact_modifier: int
    dc: int
    die: int
    passives: tuple[tuple[str, str], ...]
    ability: str = ""
    test_components: tuple[tuple[str, int], ...] = ()
    approach_id: str = ''
    description: str = ''
    supports: tuple[str, ...] = ('*',)
    repeatable: bool = False

    def __post_init__(self) -> None:
        if self.dc < 1 or self.die not in (4, 6, 8, 10, 12) or set(dict(self.passives)) != set(cards.COLORS):
            raise ValueError('Nieprawidłowy profil uczestnika.')
        if any(k not in PASSIVE_KINDS for _, k in self.passives):
            raise ValueError('Nieznany pasyw konfrontacji.')


@dataclass(frozen=True, slots=True)
class Confrontation:
    participants: tuple[Participant, ...]
    mana: cards.PooledMana
    resistance: int
    maximum: int
    pressure: int
    reactions: tuple[str, ...] = ('burn', 'strip', 'heal')
    stage: str = 'introduction'
    round: int = 1
    turn: int = 0
    bonus: int = 0
    cost: int = 0
    aids: tuple[tuple[str, int], ...] = ()
    outcome: str = ''
    condition: str = 'none'
    sensitive: bool = False
    obligation: bool = False
    goal: bool = False
    used_support: bool = False
    reached_charge: bool = False
    reacted: bool = False
    last: str = ''
    last_roll: int | None = None
    last_total: int | None = None
    last_impact: int = 0
    recovery_color: str = ''
    check_modifier: int = 0
    impact_modifier: int = 0
    first_test_bonus: int = 0
    first_test_label: str = ''
    applied_first_test_bonus: int = 0
    natural_one_seen: bool = False
    approach_options: tuple[tuple[Participant, ...], ...] = ()
    approach_selection_version: int = 1

    def __post_init__(self) -> None:
        if tuple(p.id for p in self.participants) != self.mana.heroes or not 0 <= self.turn < len(self.participants):
            raise ValueError('Nieprawidłowa kolejność uczestników.')
        if not 0 <= self.resistance <= self.maximum or self.maximum < 1 or self.pressure < 1:
            raise ValueError('Nieprawidłowy opór lub presja.')
        if self.stage not in {'introduction', 'approach', 'setup', 'turn', 'peek_choice', 'check', 'impact', 'recovery', 'after_action', 'reaction', 'after_reaction', 'result'}:
            raise ValueError('Nieznany etap konfrontacji.')
        if self.approach_options:
            if len(self.approach_options) != len(self.participants):
                raise ValueError('Brak podejść dla uczestnika.')
            for participant, options in zip(self.participants, self.approach_options):
                if not options or any(p.id != participant.id or not p.approach_id for p in options) or len({p.approach_id for p in options}) != len(options):
                    raise ValueError('Nieprawidłowe podejścia uczestnika.')
        if not self.reactions or any(r not in {'burn', 'strip', 'heal'} for r in self.reactions):
            raise ValueError('Nieznana reakcja.')

    @property
    def actor(self) -> Participant:
        return self.participants[self.turn]

    def passive(self, hero: str, kind: str) -> int:
        if self.mana.phase in {'setup', 'drain'} or self.stage == 'result':
            return 0
        participant = next(p for p in self.participants if p.id == hero)
        kinds = dict(participant.passives)
        count = sum(kinds[c] == kind for c in self.mana.hand(hero))
        return min(2 if kind in {'test', 'impact'} else 1, count)

    def to_data(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_data(cls, data: Mapping[str, object]) -> Confrontation:
        values = dict(data)
        if values.get('stage') in {'peek_color', 'peek_choice'}:
            values['stage'] = 'peek_choice'
            values['last'] = 'Podejrzyj dolną kartę. Wybierz: zostaw na spodzie albo przenieś na wierzch.'
        def participant(p: dict) -> Participant:
            return Participant(**{**p, 'passives': tuple(tuple(x) for x in p['passives']), 'test_components': tuple(tuple(x) for x in p.get('test_components', ())), 'supports': tuple(p.get('supports', ('*',)))})
        values['participants'] = tuple(participant(p) for p in values['participants'])
        values['approach_options'] = tuple(tuple(participant(p) for p in options) for options in values.get('approach_options', ()))
        values['mana'] = cards.PooledMana.from_payload(values['mana'])
        values['aids'] = tuple(tuple(a) for a in values.get('aids', ()))
        values['reactions'] = tuple(values.get('reactions', ('burn', 'strip', 'heal')))
        return cls(**values)


def available_tiers(state: Confrontation) -> tuple[tuple[int, int, int], ...]:
    return tuple(t for t in TIERS if state.mana.points(state.actor.id) >= t[0])


def _acting(state: Confrontation) -> None:
    if state.stage != 'turn' or state.mana.phase != 'ready' or state.outcome:
        raise ValueError('Najpierw dokończ dobór lub poprzednie działanie.')


def finish(state: Confrontation) -> Confrontation:
    """Do not lose a winning effect when its subsequent cost drains the deck."""
    if state.mana.phase == 'drain':
        won = state.resistance == 0
        return replace(state, stage='result', outcome='success' if won else 'failure',
                       goal=won and sum(hand.count('N') for _, hand in state.mana.pools) >= 2)
    if state.resistance == 0 and state.mana.phase == 'ready':
        return replace(state, stage='result', outcome='success',
                       goal=sum(hand.count('N') for _, hand in state.mana.pools) >= 2)
    return state


def shuffle(state: Confrontation) -> Confrontation:
    if state.stage != 'setup' or state.mana.phase != 'setup':
        raise ValueError('Nie ma tasowania do potwierdzenia.')
    if state.approach_options and any(not p.approach_id for p in state.participants):
        raise ValueError('Najpierw każdy bohater wybiera podejście.')
    return replace(state, mana=cards.confirm_shuffle(state.mana), stage='turn')


def begin_preparation(state: Confrontation) -> Confrontation:
    if state.stage != 'introduction':
        raise ValueError('Przygotowanie już rozpoczęto.')
    return replace(state, stage='approach' if state.approach_options else 'setup', turn=0)


def available_approaches(state: Confrontation) -> tuple[Participant, ...]:
    """Keep authored order; only exclusive approaches are consumed by selection."""
    taken = {p.approach_id for p in state.participants if p.approach_id}
    return tuple(p for p in state.approach_options[state.turn] if p.repeatable or p.approach_id not in taken) if state.approach_options else ()


def select_approach(state: Confrontation, approach_id: str) -> Confrontation:
    """Assign an authored approach, in turn order, before touching the deck."""
    if state.stage != 'approach' or state.mana.phase != 'setup' or not state.approach_options:
        raise ValueError('Podejścia wybiera się tylko przed konfrontacją.')
    selected = next((p for p in available_approaches(state) if p.approach_id == approach_id), None)
    if selected is None:
        raise ValueError('To podejście nie jest dostępne w tej scenie.')
    participants = tuple(selected if i == state.turn else p for i, p in enumerate(state.participants))
    last = state.turn == len(participants) - 1
    return replace(state, participants=participants, stage='setup' if last else 'approach',
                   turn=0 if last else state.turn + 1,
                   last=f'{selected.name}: {selected.method}. Wybór obowiązuje do końca konfrontacji.')


def report_color(state: Confrontation, color: str) -> Confrontation:
    if state.stage not in {'turn', 'after_action', 'after_reaction'}:
        raise ValueError('Nie ma operacji kart.')
    pool = cards.reveal(state.mana, color) if state.mana.phase == 'reveal' else cards.report_removed(state.mana, color)
    return finish(replace(state, mana=pool))


def take(state: Confrontation, index: int) -> Confrontation:
    if state.stage != 'turn':
        raise ValueError('Dobór nie jest teraz dostępny.')
    pool = cards.take(state.mana, index)
    color = pool.hand(state.actor.id)[-1]
    message = f'{state.actor.name}: dobrana karta {color}.'
    return replace(state, mana=pool, last=message,
                   sensitive=state.sensitive or (state.condition == 'sensitive' and color == 'C'),
                   reached_charge=state.reached_charge or pool.points(state.actor.id) >= 21)


def declare(state: Confrontation, bonus: int) -> Confrontation:
    _acting(state)
    tier = next((t for t in available_tiers(state) if type(bonus) is int and t[1] == bonus), None)
    if tier is None:
        raise ValueError('Ta siła próby nie jest dostępna.')
    aids = dict(state.aids)
    modifier = state.actor.test_modifier + bonus + state.passive(state.actor.id, 'test') + aids.get(state.actor.id, 0)
    return replace(state, stage='check', bonus=bonus, cost=tier[2], aids=tuple(aids.items()),
                   check_modifier=modifier + state.first_test_bonus,
                   applied_first_test_bonus=state.first_test_bonus, first_test_bonus=0, impact_modifier=state.actor.impact_modifier + state.passive(state.actor.id, 'impact'),
                   last_roll=None, last_total=None, last_impact=0)


def _cost(state: Confrontation) -> Confrontation:
    return finish(replace(state, stage='after_action', mana=cards.attack_mana(state.mana, 'deck', state.cost)))


def roll_check(state: Confrontation, natural: int) -> Confrontation:
    if state.stage != 'check' or type(natural) is not int or not 1 <= natural <= 20:
        raise ValueError('Wpisz naturalny wynik k20 od 1 do 20.')
    total = natural + state.check_modifier
    aids = tuple((hero, value) for hero, value in state.aids if hero != state.actor.id)
    updated = replace(state, aids=aids, last_roll=natural, last_total=total,
                      natural_one_seen=state.natural_one_seen or natural == 1,
                      last=f'{state.actor.name}: {natural} + ({state.check_modifier}) = {total}, ST {state.actor.dc}.')
    if total >= state.actor.dc:
        return replace(updated, stage='impact', last=updated.last + ' Udana próba — rzuć na wpływ.')
    return _cost(replace(updated, last=updated.last + ' Niepowodzenie. Koszt próby nadal obowiązuje.'))


def roll_impact(state: Confrontation, natural: int) -> Confrontation:
    if state.stage != 'impact' or type(natural) is not int or not 1 <= natural <= state.actor.die:
        raise ValueError('Wpisz naturalny wynik kości wpływu.')
    impact = max(0, natural + state.impact_modifier)
    updated = replace(state, resistance=max(0, state.resistance - impact), last_impact=impact,
                      last=state.last + f' Wpływ: {natural} + ({state.impact_modifier}) = {impact}.')
    if state.passive(state.actor.id, 'recover') and state.mana.burned:
        return replace(updated, stage='recovery', recovery_color=state.mana.burned[0])
    return _cost(updated)


def confirm_recovery(state: Confrontation) -> Confrontation:
    """Move the physical card only after acknowledgement, then charge the test."""
    if state.stage != 'recovery' or not state.recovery_color:
        raise ValueError('Nie ma odzyskania karty do potwierdzenia.')
    color = state.recovery_color
    pool = cards.recover(state.mana, (color,))
    return _cost(replace(state, mana=pool, recovery_color='',
                        last=state.last + f' Oddech: odzyskano kartę ({color}) na spód talii.'))


def support_bonus(state: Confrontation) -> int:
    return 1 + state.passive(state.actor.id, 'support')


def support_targets(state: Confrontation) -> tuple[Participant, ...]:
    return tuple(p for p in state.participants if p.id != state.actor.id
                 and ('*' in state.actor.supports or p.approach_id in state.actor.supports))


def support(state: Confrontation, target: str) -> Confrontation:
    _acting(state)
    if target not in {p.id for p in support_targets(state)}:
        raise ValueError('Wybrane podejście nie pozwala wesprzeć tego sojusznika.')
    aids = dict(state.aids)
    value = support_bonus(state)
    aids[target] = aids.get(target, 0) + value
    name = next(p.name for p in state.participants if p.id == target)
    return _cost(replace(state, aids=tuple(aids.items()), cost=1, used_support=True,
                   last=f'{state.actor.name}: pomoc +{value} dla {name}; razem +{aids[target]} do najbliższej próby testu. Spal 1 kartę. Cała pomoc znika po tej próbie, także po porażce.',
                   last_roll=None, last_total=None, last_impact=0))


def start_peek(state: Confrontation) -> Confrontation:
    _acting(state)
    return replace(state, stage='peek_choice' if state.mana.deck else 'after_action', cost=0,
                   last='Podejrzyj dolną kartę. Wybierz: zostaw na spodzie albo przenieś na wierzch.' if state.mana.deck else 'Talia jest pusta. Czekasz; kończysz działanie bez spalania.',
                   last_roll=None, last_total=None, last_impact=0)


def finish_peek(state: Confrontation, move_top: bool) -> Confrontation:
    if state.stage != 'peek_choice' or type(move_top) is not bool:
        raise ValueError('Najpierw podejrzyj kartę, potem wybierz jej położenie.')
    return replace(state, mana=cards.bottom_to_top(state.mana) if move_top else state.mana,
                   stage='after_action', last='Przenieś podejrzaną kartę na wierzch talii. Koniec działania, bez spalania.' if move_top else 'Zostaw podejrzaną kartę na spodzie talii. Koniec działania, bez spalania.')


def favor(state: Confrontation) -> Confrontation:
    _acting(state)
    if state.condition != 'favor' or state.obligation or not state.mana.burned:
        raise ValueError('Przysługa nie jest teraz dostępna.')
    color = state.mana.burned[0]
    return replace(state, mana=cards.recover(state.mana, (color,)), obligation=True,
                   last=f'Przyjęto zobowiązanie dostarczenia listu, także po porażce. Oddaj kartę {color} na spód talii.')


def compromise_available(state: Confrontation) -> bool:
    return (state.stage in {'turn', 'after_action'} and state.mana.phase == 'ready'
            and not state.outcome and state.condition == 'compromise'
            and 0 < state.resistance * 2 <= state.maximum)


def compromise(state: Confrontation) -> Confrontation:
    if not compromise_available(state):
        raise ValueError('Kompromis nie jest teraz dostępny.')
    return replace(state, stage='result', outcome='compromise', last='Drużyna przyjmuje częściowe porozumienie.')


def advance(state: Confrontation) -> Confrontation:
    if state.stage not in {'after_action', 'after_reaction'} or state.mana.phase != 'ready':
        raise ValueError('Dokończ działanie i rozliczenie kart.')
    if state.stage == 'after_action' and state.turn + 1 == len(state.participants):
        return replace(state, stage='reaction')
    new_round = state.round + int(state.stage == 'after_reaction')
    index = 0 if state.stage == 'after_reaction' else state.turn + 1
    pool = cards.start_turn(state.mana, state.participants[index].id)
    return finish(replace(state, turn=index, round=new_round, mana=pool, stage='turn'))


def react(state: Confrontation, heal_roll: int = 1) -> Confrontation:
    if state.stage != 'reaction' or state.mana.phase != 'ready':
        raise ValueError('Nie trwa reakcja sytuacji.')
    kind = state.reactions[(state.round - 1) % len(state.reactions)]
    if type(heal_roll) is not int or not 1 <= heal_roll <= 4:
        raise ValueError('Reakcja wymaga wyniku k4.')
    message = f'Presja sytuacji: spal {state.pressure} kart z wierzchu.'
    pool, resistance = state.mana, state.resistance
    if kind == 'strip':
        target = max(state.participants, key=lambda p: pool.points(p.id))
        count = max(0, 1 - state.passive(target.id, 'guard'))
        if count and pool.hand(target.id):
            hand = pool.hand(target.id)
            hands = dict(pool.pools)
            hands[target.id] = hand[:-1]
            pool = replace(pool, pools=tuple(hands.items()), burned=(*pool.burned, hand[-1]), revision=pool.revision + 1)
            message += f' {target.name}: odłóż ostatnią kartę puli ({hand[-1]}) do spalonych.'
        else:
            message += f' {target.name}: Opanowanie chroni pulę lub pula jest pusta.'
    elif kind == 'heal':
        resistance = min(state.maximum, resistance + heal_roll)
        message += f' Odzysk oporu: k4 = {heal_roll}; przywrócono {resistance - state.resistance}.'
    pool = cards.attack_mana(pool, 'deck', state.pressure)
    return finish(replace(state, mana=pool, resistance=resistance, stage='after_reaction', last=message, reacted=True))

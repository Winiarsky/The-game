"""Descriptions shared by the party indicator and physical deck preparation."""
from __future__ import annotations

from dnd_board_game.application.party_ethos import read
from dnd_board_game.combat.scene import SceneFlags
from dnd_board_game.rules.pooled_mana import PooledMana, new_mana

NAMES = {'C': 'czerwone', 'B': 'białe', 'Z': 'zielone', 'F': 'czarne', 'N': 'niebieskie'}


def composition_text(pool: PooledMana) -> str:
    return ', '.join(f'{NAMES[c]}: {n}' for c, n in pool.composition.items())


def deck_instruction(pool: PooledMana) -> str:
    text = f'Przygotuj talię many: {pool.total} kart ({composition_text(pool)}).'
    if pool.excluded:
        removed = ', '.join(f'{NAMES[c]}: {pool.excluded.count(c)}' for c in NAMES if c in pool.excluded)
        text += f' Poza talią odłóż {removed}. Te karty nie wracają przy mana drainie ani przez odzysk.'
    return text + ' Przetasuj.'


def deck_preparation(pool: PooledMana) -> dict[str, object] | None:
    """Describe this encounter's deck, including after loading an older save."""
    if not pool.excluded:
        return None
    from dnd_board_game.rules.party_ethos import PartyEthos
    ethos = PartyEthos(3 + pool.excluded.count('B') - pool.excluded.count('C'))
    return dict(label=ethos.label, steps=abs(ethos.position - 3), total=pool.total,
                composition=pool.composition,
                removed={c: pool.excluded.count(c) for c in NAMES if c in pool.excluded})


def payload(flags: SceneFlags, heroes: tuple[str, ...]) -> dict[str, object] | None:
    if not heroes:
        return None
    ethos = read(flags)
    pool = new_mana(heroes, excluded=ethos.excluded)
    return dict(position=ethos.position, label=ethos.label, steps=abs(ethos.position-3),
                composition=pool.composition, total=pool.total,
                instruction=deck_instruction(pool),
                explanation='Postawa drużyny: trzy pola ku Solidarności i trzy ku Bezwzględności. '
                'Każdy krok ku Solidarności wyłącza po jednej czerwonej i czarnej karcie; '
                'ku Bezwzględności — po jednej białej i niebieskiej. Zielona pozostaje bez zmian. '
                'Nowy skład obowiązuje od następnej walki lub konfrontacji; powrót ku środkowi przywraca karty.')

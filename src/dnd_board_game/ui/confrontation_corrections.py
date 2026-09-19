"""Bounded input corrections; never rewind dice or an NPC reaction."""
from __future__ import annotations

from typing import Any

from dnd_board_game.rules.confrontation import Confrontation


def remember(current: dict[str, Any], before: Confrontation, after: Confrontation, action: str) -> None:
    reversible = action in {'approach', 'take', 'color'} and not after.outcome
    if not reversible:
        current.pop('corrections', None)
    else:
        notice = {
            'approach': 'Cofnięto wybór podejścia. Wybierz właściwą runę.',
            'take': 'Odłóż ostatnio wybraną kartę z osobistej puli z powrotem do oferty. Wybierz właściwą kartę.',
            'color': ('Przywróć ostatnio odłożoną kartę na wierzch talii i zgłoś jej właściwy kolor.'
                      if before.mana.phase == 'burn' else
                      'Nie dobieraj kolejnej karty. Zgłoś ponownie właściwy kolor tej samej odkrytej karty.'),
        }[action]
        current['corrections'] = [*current.get('corrections', []),
                                  dict(state=before.to_data(), notice=notice)][-8:]
    current.pop('correction_notice', None)


def available(current: dict[str, Any]) -> bool:
    return bool(current.get('corrections')) and not current['state'].get('outcome')


def undo(current: dict[str, Any]) -> None:
    if not available(current):
        raise ValueError('Nie ma wyboru do cofnięcia. Rzutów i zakończonych działań nie cofamy.')
    entry = current['corrections'].pop()
    current['state'] = Confrontation.from_data(entry['state']).to_data()
    current['correction_notice'] = entry['notice']

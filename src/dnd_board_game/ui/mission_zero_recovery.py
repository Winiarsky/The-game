"""Recovery-contract chapter: authored choices, cargo, discoveries and follow-ups."""
from __future__ import annotations

from dataclasses import replace
import json
from typing import Any, TYPE_CHECKING

from dnd_board_game.inventory import MagicItemEffect, MagicItemEffectKind
from dnd_board_game.inventory.economy import currency_wallet_from_cp
from dnd_board_game.inventory.magic_items import effective_ability_modifier
from dnd_board_game.scenarios.mission_pack import read_json
from .exploration_mana_board import choice

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession

ROOMS = ('armory', 'quarters', 'store')


def has_hero(s: ExplorationUiSession, hero: str) -> bool:
    return any(str(a.id) == hero for a in s.exploration.actors)


def complete_cargo(m: dict[str, Any]) -> bool:
    return all(room in m['cargo'] for room in ROOMS)


def choices(s: ExplorationUiSession, m: dict[str, Any]) -> list[dict[str, Any]] | None:
    from . import mission_zero as mission
    stage = m['stage']
    result: list[dict[str, Any]] = []
    def add(slot: int, action: str, key: str | None = None, **extra: Any) -> None:
        result.append(choice(slot, action, mission.label(s, key or action), **extra))
    if stage == 'brief':
        add(6, 'why'); add(7, 'road_info')
        if 'negotiated' not in m['flags']: add(8, 'negotiate')
        if has_hero(s, 'lorian') and not m['compliment'] and not negotiation_started(s): add(9, 'compliments')
        if not negotiation_started(s) or 'negotiated' in m['flags']: add(28, 'depart')
    elif stage == 'compliments':
        for i, option in enumerate(read_json(mission.root(s), 'mechanics/compliments.json')['options']):
            result.append(choice(6+i, 'compliment', option['label'], option=option['id']))
    elif stage.startswith('compliment_'):
        add(28, 'brief_back', 'next')
    elif stage == 'explore':
        # Locations are selected by moving the party marker, not duplicate rune buttons.
        if 'leader' in m['flags'] and complete_cargo(m): add(28, 'dilemma')
        if owns_ring(s): add(23, 'ring')
    elif stage in ('armory', 'quarters'):
        if stage not in m['cargo']:
            add(6, 'search', room=stage); add(7, 'collect', room=stage)
        add(29, 'back')
    elif stage.startswith('search_') and stage != 'search_result':
        add(28, 'resume_search', 'resume_confrontation')
    elif stage == 'search_result' or stage == 'store':
        if m.get('search_result')=='quarters_success' and stage=='search_result' and has_hero(s,'nimra') and not m['identify_attempted'] and not m['ring_identified']:
            add(6,'identify_nimra')
        add(28, 'back')
    elif stage == 'leader':
        if not m['debt']:
            add(6, 'debt_help')
            if has_hero(s, 'garran'): add(7, 'debt_garran')
            add(8, 'debt_decline')
        if 'rumor_known' not in m['flags']: add(9, 'rumor')
        add(29, 'back')
    elif stage in ('debt_help', 'debt_garran', 'debt_decline'):
        add(28, 'back')
    elif stage == 'dilemma':
        if m['outcome'] != 'defeated': add(6, 'bell_guild')
        add(7, 'bell_village')
        if m['outcome'] != 'defeated' and has_hero(s, 'mira'): add(8, 'bell_fence')
        add(29, 'back')
    elif stage == 'guild_return':
        if owns_ring(s): add(6, 'ring')
        add(7,'equipment_open')
        add(28, 'summary', 'next')
    elif stage in ('ring', 'ring_identified'):
        if m['ring_identified']:
            if m['ring_home']=='guild_return': add(6,'equipment_open')
        elif m['ring_home'] == 'guild_return':
            price=read_json(mission.root(s),'mechanics/rewards.json')['identification_gp']
            result.append(choice(6,'identify_guild',f'Identyfikacja w Gildii — {price} sz'))
        elif has_hero(s, 'nimra') and not m['identify_attempted']: add(6, 'identify_nimra')
        add(29, 'ring_back')
    elif stage == 'identify_roll':
        pass
    elif stage == 'identify_failure':
        add(28, 'ring_view', 'next')
    else:
        return None
    return result



def owns_ring(s: ExplorationUiSession) -> bool:
    return any(i.id=='mission_ring' for i in s.state.party_loot.items) or any(i.id=='mission_ring' for a in s.exploration.actors for i in a.inventory)

def negotiation_started(s: ExplorationUiSession) -> bool:
    from .confrontation import read_store
    current = read_store(s).get('current') or {}
    return current.get('mode') == 'mission' and current.get('mission_scene') == 'nessa'


def presentation(s: ExplorationUiSession, m: dict[str, Any], key: str | None) -> str | None:
    if m['stage'] == 'return': return 'return_' + (m['bell'] or 'village')
    if m['stage'] == 'search_result': return m['search_result']
    if m['stage'] in ('armory', 'quarters') and m['stage'] in m['cargo']: return m['stage'] + '_done'
    if m['stage'] == 'ring' and m['ring_identified']: return 'ring_identified'
    return key


def search_outcome(m: dict[str, Any], state: dict[str, Any]) -> str:
    if state['outcome'] == 'success': return 'success'
    if state.get('natural_one_seen'):
        return 'repaired' if m['outcome'] == 'accepted' and not m['repair_used'] else 'critical'
    return 'failure'


def confrontation_result(s: ExplorationUiSession, current: dict[str, Any], default: str) -> str:
    from . import mission_zero as mission
    name = current['mission_scene']
    if name not in ('armory', 'quarters') or not current['state'].get('outcome'): return default
    outcome = search_outcome(mission.read(s), current['state'])
    return mission.narrative(s, name + '_' + outcome)['body']


def finish_search(s: ExplorationUiSession, m: dict[str, Any], current: dict[str, Any]) -> None:
    from . import mission_zero as mission
    room = current['mission_scene']
    if room in m['cargo']: raise ValueError('To pomieszczenie już rozstrzygnięto.')
    outcome = search_outcome(m, current['state'])
    m['cargo'][room] = 'damaged' if outcome == 'critical' else 'repaired' if outcome == 'repaired' else 'safe'
    m['searches'][room] = outcome
    if outcome == 'repaired': m['repair_used'] = True
    if outcome == 'success': mission.grant(s, m, 'medallion' if room == 'armory' else 'ring')
    m.update(stage='search_result', search_result=room + '_' + outcome)


def identify(s: ExplorationUiSession, m: dict[str, Any]) -> None:
    from . import mission_zero as mission
    if m['ring_identified']: return
    spec = read_json(mission.root(s), 'mechanics/items.json')['ring_identified']
    def known(ring):
        return replace(ring, name=spec['name'], description=spec['description'], value_cp=spec['value_cp'],
            equipped=False, magic_effects=(MagicItemEffect('strength', MagicItemEffectKind.STRENGTH_SCORE_BONUS, spec['strength_score_bonus']),))
    found=False
    if any(i.id=='mission_ring' for i in s.state.party_loot.items):
        s.state=replace(s.state,party_loot=replace(s.state.party_loot,items=tuple(known(i) if i.id=='mission_ring' else i for i in s.state.party_loot.items)))
        found=True
    for actor in s.exploration.actors:  # compatibility with earlier saves
        if any(i.id=='mission_ring' for i in actor.inventory):
            mission._set_actor(s,replace(actor,inventory=tuple(known(i) if i.id=='mission_ring' else i for i in actor.inventory)))
            found=True
    if not found: raise ValueError('Drużyna nie ma pierścienia.')
    m['ring_identified']=True
    for entry in m['ledger']:
        if entry['kind']=='item' and entry['id']=='ring':entry['name']=spec['name']


def identify_paid(s: ExplorationUiSession, m: dict[str, Any]) -> None:
    from . import mission_zero as mission
    if m['ring_identified']: raise ValueError('Pierścień jest już rozpoznany.')
    price=read_json(mission.root(s),'mechanics/rewards.json')['identification_gp']
    owner=s.exploration.actors[0]
    if owner.currency.total_cp < price*100: raise ValueError('Brakuje złota na identyfikację.')
    identify(s,m)
    mission._set_actor(s,replace(s.exploration.actors[0],currency=currency_wallet_from_cp(owner.currency.total_cp-price*100)))
    m['ledger'].append(dict(kind='money',id='identification',name='Identyfikacja pierścienia',amount=-price))


def identification_dc(s: ExplorationUiSession) -> int:
    from . import mission_zero as mission
    return read_json(mission.root(s), 'mechanics/items.json')['ring']['identification_dc']


def identification_modifier(s: ExplorationUiSession) -> int:
    from dnd_board_game.inventory.magic_items import magic_item_effect_total
    nimra = next(a for a in s.exploration.actors if str(a.id) == 'nimra')
    return effective_ability_modifier(nimra, 'intelligence') + magic_item_effect_total(nimra, MagicItemEffectKind.ABILITY_CHECK_BONUS)


def take_documents(s: ExplorationUiSession, m: dict[str, Any], garran: bool) -> None:
    from . import mission_zero as mission
    mission.grant(s, m, 'documents')
    # The physical custodian can be Garran; the papers remain shared quest inventory.
    for entry in m['ledger']:
        if entry.get('id')=='documents': entry['custodian']='garran' if garran else 'party'


def record_campaign(s: ExplorationUiSession, m: dict[str, Any]) -> None:
    from dnd_board_game.combat.scene import set_scene_flag
    case = dict(debt=m['debt'], bell=m['bell'], truce=m['outcome']=='accepted',
                documents='item:documents' in m['flags'], resolved=False)
    s.state = replace(s.state, flags=set_scene_flag(s.state.flags, 'campaign_mission_zero_case', json.dumps(case)))


def settle(s: ExplorationUiSession, m: dict[str, Any]) -> None:
    from . import mission_zero as mission
    if not complete_cargo(m): raise ValueError('Najpierw odbierzcie wszystkie trzy części ładunku.')
    if 'settled' in m['flags']: return
    rewards = read_json(mission.root(s), 'mechanics/rewards.json')
    mission.money(s, m, 'base', rewards['base_gp_per_hero'] * len(s.exploration.actors))
    penalty = rewards['cargo_damage_gp'] * sum(v == 'damaged' for v in m['cargo'].values())
    if penalty:
        owner = s.exploration.actors[0]
        mission._set_actor(s, replace(owner, currency=currency_wallet_from_cp(owner.currency.total_cp - penalty * 100)))
        m['ledger'].append(dict(kind='money', id='cargo_penalty', name=mission.label(s,'cargo_penalty'), amount=-penalty))
    if m['bell'] == 'guild': mission.money(s, m, 'bell_bonus', rewards['bell_guild_gp'])
    if m['bell'] == 'fence':
        from dnd_board_game.application.campaign_rewards import defer_reward
        s.state = replace(s.state, flags=defer_reward(s.state.flags, 'mission_zero_bell',
            rewards['fence_after_mission'], rewards['bell_fence_gp'], 'mission_zero_bell_payment'))
    had_key = any(i.id=='mission_key' for a in s.exploration.actors for i in a.inventory) or any(i.id=='mission_key' for i in s.state.party_loot.items)
    s.state=replace(s.state,party_loot=replace(s.state.party_loot,items=tuple(i for i in s.state.party_loot.items if i.id!='mission_key')))
    for actor in s.exploration.actors:
        mission._set_actor(s, replace(actor, inventory=tuple(i for i in actor.inventory if i.id != 'mission_key')))
    if had_key: m['ledger'].append(dict(kind='item', id='key_return', name=mission.label(s, 'key_return'), amount=-1))
    record_campaign(s, m)
    m['flags'].append('settled')


def handle(s: ExplorationUiSession, m: dict[str, Any], action: str, data: dict[str, Any]) -> bool:
    """Handle chapter actions after the mission transport validates availability."""
    from . import mission_zero as mission
    stage = m['stage']
    if action == 'compliments': m['stage'] = 'compliments'
    elif action == 'compliment':
        spec = read_json(mission.root(s), 'mechanics/compliments.json')
        option = data.get('option')
        if option not in {c['id'] for c in spec['options']} or m['compliment']: raise ValueError('Nieprawidłowy komplement.')
        m.update(compliment=option, stage='compliment_' + option)
    elif action == 'brief_back': m['stage'] = 'brief'
    elif action in ('armory', 'quarters', 'leader', 'store'):
        m['stage'] = action
        if action == 'leader' and 'leader' not in m['flags']: m['flags'].append('leader')
        if action == 'store': m['cargo'].setdefault('store', 'safe')
    elif action == 'collect':
        room = str(data.get('room', ''))
        if room != stage or room not in ('armory', 'quarters') or room in m['cargo']: raise ValueError('Ładunek niedostępny.')
        m['cargo'][room] = 'safe'; m['searches'][room] = 'skipped'
        m.update(stage='search_result', search_result=room + '_safe')
    elif action in ('search', 'resume_search'):
        room = str(data.get('room', '')) if action == 'search' else stage.removeprefix('search_')
        if room not in ('armory', 'quarters') or room in m['cargo']: raise ValueError('Przeszukanie niedostępne.')
        if action == 'search' and room != stage: raise ValueError('Niewłaściwe pomieszczenie.')
        m['stage'] = 'search_' + room
        mission.write(s, m); mission.launch_confrontation(s, room)
    elif action in ('debt_help', 'debt_garran', 'debt_decline'):
        m.update(debt=action.removeprefix('debt_'), stage=action)
        if action != 'debt_decline': take_documents(s, m, action == 'debt_garran')
        record_campaign(s, m)
    elif action == 'rumor':
        if m['outcome'] != 'accepted' and 'rumor_known' not in m['flags']:
            owner = s.exploration.actors[0]
            cost = read_json(mission.root(s), 'mechanics/rewards.json')['rumor_gp']
            if owner.currency.total_cp < cost * 100: raise ValueError(mission.label(s, 'no_money'))
            mission._set_actor(s, replace(owner, currency=currency_wallet_from_cp(owner.currency.total_cp - cost * 100)))
            m['ledger'].append(dict(kind='money', id='rumor', name=mission.label(s, 'rumor'), amount=-cost))
        if 'rumor_known' not in m['flags']: m['flags'].append('rumor_known')
        m['stage'] = 'rumor'
    elif action in ('bell_guild', 'bell_village', 'bell_fence'):
        if not complete_cargo(m): raise ValueError('Najpierw odbierzcie ładunek ze spisu.')
        m.update(bell=action.removeprefix('bell_'), stage=action)
        record_campaign(s, m)
    elif action == 'next' and stage == 'return':
        settle(s, m); m['stage'] = 'guild_return'; m['equipment_locked']=False
    elif action == 'summary': m['stage'] = 'summary'
    elif action == 'ring':
        m.update(ring_home=stage, stage='ring_identified' if m['ring_identified'] else 'ring')
    elif action == 'identify_nimra':
        if stage=='search_result': m['ring_home']='search_result'
        m.update(identify_attempted=True, stage='identify_roll')
    elif action == 'roll' and stage == 'identify_roll':
        natural = data.get('roll')
        if type(natural) is not int or not 1 <= natural <= 20: raise ValueError('Podaj naturalny wynik k20 od 1 do 20.')
        m['identify_total'] = natural + identification_modifier(s)
        if m['identify_total'] >= identification_dc(s):
            identify(s, m); m['stage'] = 'ring_identified'
        else: m['stage'] = 'identify_failure'
    elif action == 'identify_guild':
        identify_paid(s, m); m['stage'] = 'ring_identified'
    elif action in ('ring_view', 'ring_back'):
        m['stage'] = m['ring_home'] if action == 'ring_back' else 'ring_identified' if m['ring_identified'] else 'ring'
    else: return False
    return True


def status_payload(s: ExplorationUiSession, m: dict[str, Any]) -> dict[str, Any]:
    from . import mission_zero as mission
    ui = read_json(mission.root(s), 'text/ui.json')
    return dict(cargo=[dict(id=room, name=ui['cargo_'+room], status=ui['cargo_'+m['cargo'].get(room,'pending')]) for room in ROOMS],
        bell=ui.get('bell_'+m['bell'], ''),
        open_threads=([ui['journal_'+m['debt']]] if m['debt'] in ('help','garran') else []) + ([ui['journal_fence']] if m['bell']=='fence' else []))

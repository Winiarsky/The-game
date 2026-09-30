"""Board-only preparation and deferred, atomic payment for personal rune baskets."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING
from dnd_board_game.rules.rune_baskets import (RuneBaskets, CATEGORIES, SYMBOLS, NAMES,
    category_of, declare_token, undo_token, confirm_category, confirm_recharge)
from dnd_board_game.rules.shared_mana import sync_runes
from dnd_board_game.scenarios.rune_catalog import rune_card
from .board_panel_symbols import panel_icon, rune_slot

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession, BoardScanTarget
    from .shared_mana import ManaDeclaration
    from dnd_board_game.combat.session import CombatState
    from dnd_board_game.actors import Actor
    from dnd_board_game.world import Coordinate


def active(session: ExplorationUiSession) -> bool:
    state = session.combat_state
    return bool(state and state.shared_mana and isinstance(state.shared_mana.runes, RuneBaskets))


def _choice(slot: int, label: str, command: str, **values: object) -> dict[str, object]:
    return dict(slot=slot, label=label, command=command, icon=panel_icon(slot), **values)


def _context(session: ExplorationUiSession) -> tuple[CombatState, RuneBaskets, ManaDeclaration | None, Actor]:
    state = session.combat_state
    d = session.shared_mana_declaration
    actor = next(a for a in state.actors if str(a.id) == (d.actor_id if d else state.shared_mana.runes.actor))
    return state, state.shared_mana.runes, d, actor


def view(session: ExplorationUiSession) -> dict[str, object]:
    state, pool, d, actor = _context(session)
    names = {str(a.id):a.name for a in state.actors}
    choices, targets = [], []
    instruction, title, phase = '', '', 'ready'
    selected = []
    if state.shared_mana.rune_upkeep_actor:
        owner=state.shared_mana.rune_upkeep_actor
        phase='basket';title='Podtrzymanie Żelaznego bastionu'
        chosen=state.shared_mana.rune_upkeep_selected
        instruction=f'Wybrano {chosen}. ✓ wydaje żeton; ↩ cofa.' if chosen else 'Wybierz własny żeton, aby podtrzymać podstawową aurę (+1 KP, 2 pola). ↩ kończy aurę.'
        choices=[_choice(28,'Podtrzymaj','basket_upkeep_pay')] if chosen else [_choice(rune_slot(r),r,'basket_upkeep_take',rune=r) for r in dict.fromkeys(pool.hand(owner))]
        choices.append(_choice(29,'Wróć' if chosen else 'Zakończ aurę','basket_upkeep_back'))
    elif pool.phase == 'allocation':
        phase = 'basket'
        title = f"{names[pool.actor]} · {NAMES[pool.category]}"
        n = len(pool.charged(pool.actor,pool.category)); limit=pool.capacity(pool.actor,pool.category)
        instruction = f"Zadeklaruj żetony: {n}/{limit}. Naciśnięcie symbolu dodaje jedną sztukę; symbole mogą się powtarzać. ↩ cofa ostatni wybór w tej kategorii."
        if n < limit:
            choices = [_choice(rune_slot(r), r, 'basket_take', rune=r) for r in SYMBOLS[pool.category_index]]
        else:
            choices.append(_choice(28,'Zatwierdź kategorię','basket_confirm'))
        if pool.picks: choices.append(_choice(29,'Cofnij żeton','basket_back'))
        selected = list(pool.charged(pool.actor,pool.category))
    elif pool.phase.startswith('recharge'):
        phase='basket';title=f"Ładowanie · {names[pool.actor]}"
        if pool.phase=='recharge_category':
            instruction=f"Pozostało {pool.recharge_remaining}. Wybierz kategorię z wolnym miejscem, a potem rzuć k4."
            choices=[_choice(rune_slot(SYMBOLS[i][0]), NAMES[c], 'basket_recharge_category', category=c)
                for i,c in enumerate(CATEGORIES) if pool.missing(pool.actor,c)]
        else:
            rune=SYMBOLS[CATEGORIES.index(pool.recharge_category)][pool.recharge_roll-1]
            instruction=f"{NAMES[pool.recharge_category]} · k4: {pool.recharge_roll} → {rune}. " + ('✓ zatwierdza nowy żeton; ↩ poprawia wynik.' if pool.phase=='recharge_review' else 'Rzuć fizyczną k4. Ustaw wynik przez +/− i przejdź do podsumowania.')
            if pool.phase=='recharge_roll':
                if pool.recharge_roll<4: choices.append(_choice(26,'+','basket_plus'))
                if pool.recharge_roll>1: choices.append(_choice(27,'−','basket_minus'))
            choices.append(_choice(28,'Potwierdź','basket_confirm'))
            if pool.phase=='recharge_review' or not pool.recharge_fixed_category:choices.append(_choice(29,'Wróć','basket_back'))
    elif pool.phase in {'focus_confirm','regeneration'}:
        phase='basket'
        title='Skupienie' if pool.phase=='focus_confirm' else 'Zgłoś odnowienie po zdarzeniu'
        if pool.phase=='focus_confirm':
            instruction='Zużyj akcję specjalną, aby naładować do 2 własnych miejsc. Każde wymaga osobnego k4. Zwykły ruch i atak pozostają dostępne.'
            choices=[_choice(28,'Wykonaj Skupienie','basket_focus_confirm')]
        else:
            from dnd_board_game.scenarios.rune_basket_catalog import load_rune_basket_catalog
            instruction='Potwierdź tylko zdarzenie, które już nastąpiło. Aplikacja pilnuje limitu raz na rundę, pojemności oraz nowego symbolu. Pełny koszyk też zużywa limit.'
            for i,r in enumerate(load_rune_basket_catalog()['heroes'][pool.actor]['regeneration']):
                if (pool.actor,r['id'],state.initiative_order.round_number) not in pool.regeneration_used:
                    choices.append(_choice(5+i,r['label'],'basket_regen:'+r['id']))
        choices.append(_choice(29,'Wróć','basket_utility_back'))
    elif d and d.stage=='basket':
        phase='basket';card=rune_card(d.actor_id,d.ability_id,pool=pool)
        title=card.name
        step=d.basket_step
        own=list(pool.hand(d.actor_id))
        for r in d.rune_choices.get('payment',()): own.remove(r)
        selected=list(d.rune_choices.get('payment',()))
        if step=='review' and not d.basket_helper and not d.rune_flaw_only: selected.extend(card.payment(d.boosts)[1:])
        if step in {'base','surcharge'}:
            from dnd_board_game.combat.rune_flaws import rune_flaw_cost
            from .rune_payment import declaration_targets
            extra=rune_flaw_cost(state,actor,d.ability_id,declaration_targets(session,d)).count
            allowed=[r for r in own if step=='surcharge' or category_of(r)==card.category]
            instruction=(f"Koszt podstawowy: wybierz 1 własny żeton kategorii {NAMES[card.category]}." if step=='base'
                else f"Dopłata skazy: wybierz własne dowolne żetony ({len(selected)-(0 if d.rune_flaw_only else 1)}/{extra}).")
            choices=[_choice(rune_slot(r),f"{r} ×{n}",'basket_take',rune=r) for r,n in Counter(allowed).items()]
        elif step=='resonance':
            from dnd_board_game.combat.rune_baskets import helpers
            from dnd_board_game.combat.runes import require_budget
            instruction='Opcjonalnie wybierz konkretną runę Rezonansu. ✓ przechodzi dalej bez ulepszenia.'
            for b in card.boosts:
                eligible=helpers(state,actor,b.color)
                try: require_budget(state,actor,card,{b.id:1})
                except ValueError: continue
                if b.color in own or eligible:
                    choices.append(_choice(rune_slot(b.color),f"{b.color}: {b.label}" + ('' if b.color in own else ' · pomoc sojusznika'), 'basket_boost', boost_id=b.id))
            choices.append(_choice(28,'Bez Rezonansu','basket_confirm'))
        elif step=='helper':
            from dnd_board_game.combat.rune_baskets import helpers
            boost=next(b for b in card.boosts if d.boosts.get(b.id))
            instruction=f"Brakuje {boost.color}. Wskaż podświetlonego sojusznika w promieniu 3 pól. Odda ten żeton i zużyje reakcję po końcowym potwierdzeniu."
            targets=[dict(id=str(a.id),name=a.name,position=list(a.position.as_tuple())) for a in helpers(state,actor,boost.color)]
        elif step=='helper_confirm':
            helper=next(a for a in state.actors if str(a.id)==d.basket_helper)
            instruction=f"{helper.name}: czy zgadzasz się wydać swój żeton Rezonansu i reakcję? ✓ potwierdza udział, ↩ wraca do wyboru pomocnika."
            choices.append(_choice(28,'Potwierdź pomoc','basket_confirm'))
        elif step=='review':
            from .rune_payment import declaration_targets
            target_names=', '.join(a.name for a in declaration_targets(session,d)) or 'zgodnie z podglądem mocy'
            boost=next((b for b in card.boosts if d.boosts.get(b.id)),None)
            instruction=f"Cel: {target_names}. {card.description} Koszt: {', '.join(selected)}. Budżet: {card.budget_for(d.boosts)}. "
            instruction += f"Rezonans: {boost.label} " if boost else 'Bez Rezonansu. '
            if d.basket_helper: instruction += f"{names[d.basket_helper]} wydaje {boost.color} i reakcję. "
            instruction+='✓ opłaca i rozpoczyna rozstrzygnięcie; ↩ wraca bez kosztu.'
            choices.append(_choice(28,'Wykonaj moc','basket_confirm'))
        choices.append(_choice(29,'Wróć bez kosztu','basket_back'))
    hands=[dict(hero=h,name=names[h],cards=list(pool.hand(h)),count=len(pool.hand(h)),limit=sum(dict(pool.capacities)[h]),
        baskets=[dict(category=c,name=NAMES[c],count=len(pool.charged(h,c)),capacity=pool.capacity(h,c),
            tokens=[dict(rune=r,count=n,icon=panel_icon(rune_slot(r))) for r,n in Counter(pool.charged(h,c)).items()]) for c in CATEGORIES],
        counts=[dict(rune=r,name=r,count=n,slot=rune_slot(r),icon=panel_icon(rune_slot(r))) for r,n in Counter(pool.hand(h)).items()]) for h in pool.heroes]
    return dict(model=pool.model,phase=phase,actor=str(actor.id),actor_name=actor.name,title=title,instruction=instruction,
        hands=hands,choices=choices,targets=targets,selected=selected,selected_slots=[rune_slot(r) for r in selected],
        utilities=[_choice(slot,'Skupienie · naładuj do 2 miejsc' if slot==19 else 'Zgłoś odnowienie po zdarzeniu', 'basket_focus' if slot==19 else 'basket_regeneration') for slot in utility_slots(session)],
        offer=[],deck_count=0,discard_count=0,opening_count=0,special_used=state.turn_action.rune_special_used)


def begin(session: ExplorationUiSession) -> dict[str, object]:
    from .shared_mana import _preflight
    d=session.shared_mana_declaration
    _preflight(session,d)
    if d.basket_step=='parameters':
        d.stage='basket';d.basket_step='review'
    else:
        d.stage='basket';d.basket_step='surcharge' if d.rune_flaw_only else 'base';d.boosts={} if not d.rune_flaw_only else d.boosts;d.rune_choices={};d.basket_helper=''
    return _updated(session)


def _updated(session: ExplorationUiSession) -> dict[str, object]:
    state=session.combat_state
    session.combat_state=replace(state,shared_mana=replace(state.shared_mana,revision=state.shared_mana.revision+1))
    session.board_panel_context=None
    session._sync_board_leds()
    return session.state_payload()


def _parameters(session: ExplorationUiSession) -> None:
    d=session.shared_mana_declaration
    # Existing target/area flows also validate extra targets chosen by a resonance.
    d.stage='payment';d.basket_step='parameters'
    from .shared_mana import _refresh_preview
    _refresh_preview(session,d)


def command(session: ExplorationUiSession, data: dict[str, object]) -> dict[str, object]:
    state,pool,d,actor=_context(session)
    if type(data.get('revision')) is not int or data['revision'] != state.shared_mana.revision:
        raise ValueError('Nieaktualny wybór koszyków.')
    action=str(data.get('command',''))
    if action.startswith('basket_upkeep_'):
        from dnd_board_game.rules.rune_baskets import spend_tokens
        mana=state.shared_mana;owner=mana.rune_upkeep_actor
        if not owner:raise ValueError('Brak aury do podtrzymania.')
        if action=='basket_upkeep_take':
            rune=str(data.get('rune',''))
            if rune not in pool.hand(owner):raise ValueError('Brak takiego żetonu.')
            mana=replace(mana,rune_upkeep_selected=rune)
        elif action=='basket_upkeep_back' and mana.rune_upkeep_selected:
            mana=replace(mana,rune_upkeep_selected='')
        else:
            if action=='basket_upkeep_pay':
                if not mana.rune_upkeep_selected:raise ValueError('Wybierz żeton podtrzymania.')
                pool=spend_tokens(pool,{owner:(mana.rune_upkeep_selected,)})
                from dnd_board_game.combat.shared_mana_features import synchronize_bastion
                session.active_combat_effects=synchronize_bastion(state.actors,tuple(replace(e,value=1,radius_feet=10) if e.kind=='iron_bastion' and e.source_actor_id==owner else e for e in session.active_combat_effects))
            elif action=='basket_upkeep_back':
                session.active_combat_effects=tuple(e for e in session.active_combat_effects if not(e.kind in {'iron_bastion','iron_bastion_member'} and e.source_actor_id==owner))
            else:raise ValueError('Nieznana operacja aury.')
            mana=sync_runes(replace(mana,rune_upkeep_actor='',rune_upkeep_selected=''),pool)
        session.combat_state=replace(state,shared_mana=mana)
        return _updated(session)
    if action in {'basket_focus','basket_regeneration','basket_focus_confirm','basket_utility_back'} or action.startswith('basket_regen:'):
        return utility_command(session,action)
    if pool.phase=='allocation':
        if action=='basket_take': pool=declare_token(pool,str(data.get('rune','')))
        elif action=='basket_back': pool=undo_token(pool)
        elif action=='basket_confirm': pool=confirm_category(pool)
        else: raise ValueError('Wybierz żeton bieżącej kategorii.')
        session.combat_state=replace(state,shared_mana=sync_runes(state.shared_mana,pool))
    elif pool.phase.startswith('recharge'):
        if action=='basket_recharge_category' and pool.phase=='recharge_category':
            c=str(data.get('category',''))
            if not pool.missing(pool.actor,c): raise ValueError('Ten koszyk jest pełny.')
            pool=replace(pool,phase='recharge_roll',recharge_category=c)
        elif action in {'basket_plus','basket_minus'} and pool.phase=='recharge_roll':
            pool=replace(pool,recharge_roll=pool.recharge_roll+(1 if action=='basket_plus' else -1))
        elif action=='basket_confirm':
            pool=confirm_recharge(pool) if pool.phase=='recharge_review' else replace(pool,phase='recharge_review')
        elif action=='basket_back' and pool.phase in {'recharge_roll','recharge_review'}:
            if pool.phase=='recharge_roll' and pool.recharge_fixed_category:raise ValueError('To odnowienie ładuje tylko wskazaną kategorię.')
            pool=replace(pool,phase='recharge_roll' if pool.phase=='recharge_review' else 'recharge_category')
        else: raise ValueError('Dokończ ładowanie wskazanego koszyka.')
        session.combat_state=replace(state,shared_mana=sync_runes(state.shared_mana,pool))
    elif d and d.stage=='basket':
        card=rune_card(d.actor_id,d.ability_id,pool=pool)
        step=d.basket_step
        legal=view(session)
        if action=='basket_helper' and step=='helper':
            if str(data.get('target_id')) not in {a['id'] for a in legal['targets']}:raise ValueError('Wybierz dostępnego pomocnika.')
            d.basket_helper=str(data['target_id']);d.basket_step='helper_confirm'
        elif not any(c['command']==action and all(data.get(k)==c[k] for k in ('rune','boost_id') if k in c) for c in legal['choices']):
            raise ValueError('Ten wybór nie jest teraz dostępny.')
        elif action=='basket_back':
            if d.rune_flaw_only:
                d.rune_choices={}
                if step=='review':d.basket_step='surcharge'
                else:d.stage='payment';d.basket_step=''
            elif step=='helper_confirm': d.basket_helper='';d.basket_step='helper'
            elif step in {'helper','review'}: d.basket_helper='';d.boosts={};d.basket_step='resonance'
            elif step=='resonance': d.rune_choices={};d.basket_step='base'
            elif step=='surcharge': d.rune_choices={};d.basket_step='base'
            else: d.stage='payment';d.basket_step='';d.rune_choices={}
        elif action=='basket_take':
            selected=(*d.rune_choices.get('payment',()),str(data['rune']))
            d.rune_choices['payment']=selected
            from dnd_board_game.combat.rune_flaws import rune_flaw_cost
            from .rune_payment import declaration_targets
            extra=rune_flaw_cost(state,actor,d.ability_id,declaration_targets(session,d)).count
            d.basket_step='surcharge' if len(selected)<(0 if d.rune_flaw_only else 1)+extra else 'review' if d.rune_flaw_only else 'resonance'
        elif action=='basket_boost':
            b=next(b for b in card.boosts if b.id==data['boost_id']);d.boosts={b.id:1}
            remaining=Counter(pool.hand(d.actor_id))-Counter(d.rune_choices.get('payment',()))
            if remaining[b.color]:
                _parameters(session)
            else: d.basket_step='helper'
        elif action=='basket_confirm':
            if step in {'resonance','helper_confirm'}: _parameters(session)
            elif step=='review':
                d.stage='payment';d.basket_step='final'
                from .shared_mana import command as mana_command
                try: return mana_command(session,dict(command='pay',revision=state.shared_mana.revision))
                except Exception:
                    d.stage='basket';d.basket_step='review'
                    raise
            else: raise ValueError('Najpierw wybierz koszt.')
    else: raise ValueError('Brak operacji koszyków do obsłużenia.')
    return _updated(session)


def scan_target(session: ExplorationUiSession) -> BoardScanTarget | None:
    from .exploration_app import BoardScanTarget
    from dnd_board_game.hardware.board_panel import panel_feedback, panel_position
    from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole
    from dnd_board_game.hardware.led_palette import LedColor
    from dnd_board_game.world import Coordinate
    v=view(session)
    if v['phase']!='basket':return None
    slots=tuple(c['slot'] for c in v['choices'])
    positions=tuple(Coordinate(*a['position']) for a in v['targets'])
    feedback=panel_feedback(tuple(s for s in slots if s<26), control_slots=tuple(s for s in slots if s>=26))
    frames=(LedFrame(positions,LedColor.LEGAL_ABILITY_TARGET,LedRole.MARKER),) if positions else ()
    declaration=session.shared_mana_declaration
    if declaration:
        from .rune_payment import declaration_targets
        marked=tuple(a.position for a in declaration_targets(session,declaration))
        if declaration.basket_helper:
            marked+=tuple(a.position for a in session.combat_state.actors if str(a.id)==declaration.basket_helper)
        if marked:frames+=(LedFrame(marked,LedColor.SELECTED_ABILITY_TARGET,LedRole.MARKER),)
    selected=tuple(panel_position(s) for s in set(v['selected_slots']))
    if selected:frames+=(LedFrame(selected,LedColor.SELECTED_ABILITY_TARGET,LedRole.MARKER),)
    return BoardScanTarget(positions=(*positions,*(panel_position(s) for s in slots)),feedback=LedFeedback((*feedback.frames,*frames)),empty_message=v['instruction'])


def select_position(session: ExplorationUiSession, position: Coordinate) -> dict[str, object]:
    from dnd_board_game.hardware.board_panel import panel_position
    v=view(session)
    c=next((c for c in v['choices'] if panel_position(c['slot'])==position),None)
    target=next((a for a in v['targets'] if a['position']==list(position.as_tuple())),None)
    if target:c=dict(command='basket_helper',target_id=target['id'])
    if not c:raise ValueError('Wybierz podświetlone pole.')
    return command(session,dict(c,revision=session.combat_state.shared_mana.revision))


def utility_slots(session: ExplorationUiSession) -> tuple[int, ...]:
    """Utility controls coexist with normal action buttons only at turn selection."""
    if not active(session):return ()
    state=session.combat_state
    from dnd_board_game.combat import current_actor
    actor=current_actor(state)
    if (state.status.value!='active' or str(actor.id) not in state.shared_mana.runes.heroes
        or state.shared_mana.phase.value!='ready' or session.shared_mana_declaration
        or session._combat_has_pending_resolution() or session.combat_turn_preview_option_id
        or session.combat_targeting_attack_source_id or session.combat_targeting_class_feature_action_id
        or session.selected_combat_movement_path or (session.board_panel_context and session.board_panel_context[2])):
        return ()
    slots=[]
    from dnd_board_game.combat.runes import require_budget
    from dnd_board_game.scenarios.rune_catalog import RuneCard
    try:
        require_budget(state,actor,RuneCard(str(actor.id),'basket_focus','',19,'S','Skupienie',''))
        if any(state.shared_mana.runes.missing(str(actor.id),c) for c in CATEGORIES):slots.append(19)
    except ValueError:
        pass
    slots.append(21)
    return tuple(slots)


def utility_command(session: ExplorationUiSession, action: str) -> dict[str, object]:
    from dnd_board_game.combat import current_actor
    from dnd_board_game.combat.runes import require_budget, commit_budget
    from dnd_board_game.scenarios.rune_catalog import RuneCard
    from dnd_board_game.rules.rune_baskets import start_recharge
    from dnd_board_game.scenarios.rune_basket_catalog import load_rune_basket_catalog
    state=session.combat_state;pool=state.shared_mana.runes
    actor=current_actor(state)
    focus=RuneCard(str(actor.id),'basket_focus','',19,'S','Skupienie','Naładuj do 2 własnych miejsc przez k4.')
    if action in {'basket_focus','basket_regeneration'}:
        if not utility_slots(session):raise ValueError('Najpierw zakończ bieżącą akcję.')
        if action=='basket_focus':
            require_budget(state,actor,focus)
            if not any(pool.missing(str(actor.id),c) for c in CATEGORIES):raise ValueError('Wszystkie koszyki są pełne.')
        pool=replace(pool,phase='focus_confirm' if action=='basket_focus' else 'regeneration',recharge_actor=str(actor.id))
    elif action=='basket_utility_back':
        pool=replace(pool,phase='ready',recharge_actor='')
    elif action=='basket_focus_confirm' and pool.phase=='focus_confirm':
        require_budget(state,actor,focus)
        pool=start_recharge(replace(pool,phase='ready',recharge_actor=''),str(actor.id),2)
        state=commit_budget(state,actor,focus,{})
    elif action.startswith('basket_regen:') and pool.phase=='regeneration':
        key=action.split(':',1)[1]
        rule=next((r for r in load_rune_basket_catalog()['heroes'][str(actor.id)]['regeneration'] if r['id']==key),None)
        round_number=state.initiative_order.round_number
        marker=(str(actor.id),key,round_number)
        if rule is None or marker in pool.regeneration_used:raise ValueError('Odnowienie zostało już zgłoszone w tej rundzie.')
        pool=replace(pool,phase='ready',recharge_actor='',regeneration_used=(*pool.regeneration_used,marker))
        if pool.missing(str(actor.id),rule['category']):pool=start_recharge(pool,str(actor.id),rule['count'],rule['category'])
        else:session._add_message('Odnowienie', 'Koszyk jest pełny. Warunek został wykorzystany w tej rundzie.')
    else:raise ValueError('Nieaktualna operacja ładowania.')
    session.combat_state=replace(state,shared_mana=sync_runes(state.shared_mana,pool))
    return _updated(session)

"""Rendered clue feedback and the authored finale in the running application."""
from __future__ import annotations

from collections.abc import Callable

from tests.integration.test_player_ui_browser import PlayerSession, player_session, pw
from tests.unit.test_mission_zero import send, stage


def test_borut_clue_is_visible_in_actual_confrontation(
    player_session: Callable[..., PlayerSession],
) -> None:
    session = player_session("mission")
    page = session.page
    stage(session.game, "leader", outcome="accepted")
    page.reload(wait_until="networkidle")
    session.idle()
    page.locator('[data-mission-slot="8"]').click()
    session.idle()
    pw.expect(page.locator(".mission-prose")).to_contain_text("niższe o 2")
    page.locator('[data-mission-slot="28"]').click()
    session.idle()
    send(session.game, "quarters")
    page.reload(wait_until="networkidle")
    session.idle()
    page.locator('[data-mission-slot="5"]').click()
    session.idle()
    page.locator('[data-mana-slot="28"]').click()
    session.idle()
    options = page.locator(".progress-confrontation-options article")
    pw.expect(options).to_have_count(6)
    for option in options.all():
        pw.expect(option).to_contain_text("ST 12")
    session.capture("borut-clue-dc12")
    page.locator('[data-mana-slot="5"]').click()
    session.idle()
    assert page.evaluate("state.exploration_mana.dc") == 12
    assert page.evaluate("state.exploration_mana.phase") == "check"
    assert not session.errors


def test_defeat_finale_describes_only_available_resolution(
    player_session: Callable[..., PlayerSession],
) -> None:
    session = player_session("mission")
    stage(session.game, "dilemma", outcome="defeated", cargo=dict(armory="safe", quarters="safe", store="safe"))
    session.page.reload(wait_until="networkidle")
    session.idle()
    pw.expect(session.page.locator(".mission-prose")).to_contain_text("warunek zakończenia starcia")
    assert session.page.locator('[data-mission-slot="5"]').count() == 0
    assert session.page.locator('[data-mission-slot="7"]').count() == 0
    session.capture("defeat-bell-resolution")
    session.page.locator('[data-mission-slot="6"]').click()
    session.idle()
    assert session.page.evaluate("state.mission.stage") == "bell_village"
    assert not session.errors

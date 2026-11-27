"""Real keyboard and rendered-layout checks for the shared player interface.

Install the optional ui-test dependencies and run through safe_pytest.sh.
All games, rosters and screenshots are isolated from the user's campaign.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
from threading import Thread
from typing import TYPE_CHECKING

import pytest
from werkzeug.serving import BaseWSGIServer, make_server, WSGIRequestHandler

from dnd_board_game.ui import mission_zero, party_preparation
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.routes import create_app
from scripts.install_default_roster import install_default_roster
from scripts.keyboard_playtest import prepare_session

if TYPE_CHECKING:
    from playwright.sync_api import Page

pw = pytest.importorskip("playwright.sync_api", reason="Install the ui-test extra for browser QA")


class QuietHandler(WSGIRequestHandler):
    def log(self, *args: object, **kwargs: object) -> None:
        pass


@dataclass
class PlayerSession:
    page: Page
    game: ExplorationUiSession
    artifacts: Path
    errors: list[str]

    def idle(self) -> None:
        self.page.wait_for_function(
            "typeof state!=='undefined' && state?.input?.mode==='keyboard' "
            "&& !busy && !boardPanelSyncPromise && document.querySelector('[data-keyboard-sync]')?.hidden"
        )

    def press(self, key: str) -> None:
        self.page.keyboard.press(key)
        self.idle()

    def capture(self, name: str) -> None:
        viewport = self.page.viewport_size
        assert viewport is not None
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(self.artifacts / f"{name}-{viewport['width']}x{viewport['height']}.png"))


@pytest.fixture
def player_session(tmp_path: Path) -> Iterator[Callable[..., PlayerSession]]:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if chrome is None:
        pytest.skip("Chrome or Chromium required")
    resources: list[tuple[BaseWSGIServer, Thread, ExplorationUiSession]] = []
    contexts = []
    with pw.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=chrome, headless=True,
                                         args=["--no-sandbox", "--disable-dev-shm-usage"])

        def start(mode: str = "combat", size: tuple[int, int] = (1221, 656)) -> PlayerSession:
            folder = tmp_path / f"{mode}-{len(resources)}"
            if mode == "conversation":
                from tests.unit.test_confrontation_presentation import start as confrontation_session
                game = confrontation_session(folder, count=3, scene_name="nessa")
                game.configure_input_mode("keyboard")
                game.configured_board_backend = "none"
            else:
                game = prepare_session(folder, ("erynd", "nimra", "brakka"),
                                       arena=mode == "combat", skip_setup=mode == "combat")
            if mode == "equipment":
                preparation = mission_zero.read(game)
                party_preparation.begin(preparation, "guild")
                mission_zero.write(game, preparation)
            if mode == "launcher":
                install_default_roster(folder / "characters")
            app = create_app(game, character_dir=folder / "characters")
            server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=QuietHandler)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            resources.append((server, thread, game))
            context = browser.new_context(viewport={"width": size[0], "height": size[1]})
            contexts.append(context)
            page = context.new_page()
            page.set_default_timeout(12_000)
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/{'new-game' if mode=='launcher' else 'play'}",
                      wait_until="networkidle")
            session = PlayerSession(page, game, Path(os.environ.get("DND_UI_ARTIFACTS", tmp_path / "screenshots")), errors)
            if mode == "launcher":
                pw.expect(page.locator("[data-board-status]")).to_contain_text("Klawiatura")
            else:
                session.idle()
            return session

        try:
            yield start
        finally:
            for context in contexts:
                context.close()
            browser.close()
            for server, thread, game in resources:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
                game.shutdown_board()


@pytest.mark.parametrize("size", [(1221, 656), (883, 687), (1221, 569)])
def test_combat_panels_focus_and_movement(player_session: Callable[..., PlayerSession], size: tuple[int, int]) -> None:
    session = player_session(size=size)
    page = session.page
    before = repr(session.game.combat_state)
    pw.expect(page.locator(".app-shell-context")).to_be_visible()
    assert page.locator("#side-panel").evaluate("panel=>panel.inert")
    session.capture("combat")

    session.press("Numpad5")
    session.press("Numpad2")
    assert page.evaluate("getComputedStyle(document.activeElement).outlineColor") == "rgb(145, 200, 228)"
    assert page.evaluate("""(()=>{const selected=document.activeElement,rect=selected.getBoundingClientRect(),
        container=selected.closest('.rc-decision-content').getBoundingClientRect();
        return rect.top>=container.top-1&&rect.bottom<=container.bottom+1})()""")
    original = page.evaluate("document.activeElement.dataset.rcSlot")
    session.press("Numpad1")
    panel = page.get_by_role("dialog", name="Informacje", exact=True)
    pw.expect(panel).to_be_visible()
    assert page.locator("#game-content").evaluate("element=>element.inert")
    page.get_by_role("button", name="Zamknij panel", exact=True).focus()
    page.keyboard.press("Shift+Tab")
    assert page.evaluate("document.activeElement.closest('#side-panel')!==null")
    page.keyboard.press("Tab")
    pw.expect(page.get_by_role("button", name="Zamknij panel", exact=True)).to_be_focused()
    session.press("Numpad3")
    pw.expect(page.get_by_role("tab", name="Ekwipunek", exact=True)).to_have_attribute("aria-selected", "true")
    page.locator(".inventory-metadata").evaluate_all("items=>items.forEach(item=>item.open=true)")
    assert panel.evaluate("element=>element.scrollWidth<=element.clientWidth+1")
    session.capture("inventory")
    session.press("Numpad1")
    session.press("Numpad1")
    assert page.locator("#side-panel").evaluate("element=>element.inert")
    assert page.evaluate("document.activeElement.dataset.rcSlot") == original
    assert repr(session.game.combat_state) == before

    session.press("Numpad7")
    preview_before = repr(session.game.combat_state)
    session.press("Numpad8")
    pw.expect(page.locator("#keyboard-decision-hint")).to_contain_text("Koszt ruchu:")
    pw.expect(page.locator("[data-keyboard-accept]")).to_be_enabled()
    destination = page.evaluate("state.input.cursor")
    assert repr(session.game.combat_state) == preview_before
    session.capture("movement-preview")
    page.locator("[data-keyboard-accept]").click()
    session.idle()
    assert page.evaluate("state.combat.resonance.actors.find(actor=>actor.id===state.combat.resonance.active).position") == destination
    assert page.evaluate("state.combat.resonance.phase") == "result"
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth && document.documentElement.scrollHeight<=innerHeight+1")
    assert not session.errors


@pytest.mark.parametrize("mode", ["combat", "mission", "equipment", "conversation"])
def test_api_error_preserves_game_and_allows_next_action(
    player_session: Callable[..., PlayerSession], mode: str,
) -> None:
    session = player_session(mode)
    page = session.page
    before = page.evaluate("JSON.stringify(state)")
    domain = repr(session.game.combat_state)
    scene_before = page.locator(".confrontation-scroll").bounding_box() if mode == "conversation" else None
    page.route("**/api/input/command", lambda route: route.fulfill(status=400, json={"error": "Cel poza zasięgiem. Wybierz bliższy cel."}))
    page.evaluate("api('/api/input/command',{command:'accept'},'Sprawdzam wybór…')")
    pw.expect(page.get_by_role("alert")).to_contain_text("Cel poza zasięgiem")
    pw.expect(page.get_by_role("alert")).to_be_visible()
    assert page.get_by_role("alert").evaluate("element=>{const rect=element.getBoundingClientRect();return rect.height>=40&&rect.top>=0&&rect.bottom<=innerHeight;}")
    assert page.evaluate("JSON.stringify(state)") == before
    assert repr(session.game.combat_state) == domain
    if scene_before is not None:
        assert page.locator(".confrontation-scroll").bounding_box() == scene_before
    session.capture(f"{mode}-inline-error")
    page.get_by_role("button", name="Zamknij komunikat").click()
    pw.expect(page.get_by_role("alert")).to_have_count(0)
    page.unroute("**/api/input/command")
    if mode == "combat":
        session.press("Numpad7")
        assert page.evaluate("state.input.kind") == "map"
    else:
        session.press("Numpad1")
        pw.expect(page.get_by_role("dialog", name="Informacje", exact=True)).to_be_visible()
        session.press("Numpad1")
        assert page.locator("#side-panel").evaluate("element=>element.inert")
    assert not session.errors


def test_rejected_revision_refreshes_server_projection_before_retry(
    player_session: Callable[..., PlayerSession],
) -> None:
    session = player_session()
    before = repr(session.game.combat_state)
    revision = session.page.evaluate("state.input.revision")
    session.game.board_selection_revision += 1
    session.page.evaluate("api('/api/input/command',{command:'accept',context:state.input.context,revision:state.input.revision},'')")
    pw.expect(session.page.get_by_role("alert")).to_contain_text("nieaktualny")
    assert session.page.evaluate("state.input.revision") != revision
    assert repr(session.game.combat_state) == before
    session.press("Numpad7")
    assert session.page.evaluate("state.input.kind") == "map"
    pw.expect(session.page.get_by_role("alert")).to_have_count(0)
    assert not session.errors


def test_character_tabs_use_current_rune_powers_and_combat_states(player_session: Callable[..., PlayerSession]) -> None:
    from dnd_board_game.ui import resonance

    session = player_session()
    engine = resonance.engine(session.game)
    engine.add_status("erynd", "arcane", value=2, until_start="erynd")
    session.game.combat_state = engine.combat_state()
    session.page.reload(wait_until="networkidle")
    session.idle()
    before = repr(session.game.combat_state)
    session.press("Numpad1")
    page = session.page
    page.get_by_role("tab", name="Stany", exact=True).click()
    pw.expect(page.locator("#actor-states")).to_contain_text("Tarcza arkanów")
    page.get_by_role("tab", name="Moce", exact=True).click()
    pw.expect(page.locator("#actor-spells")).to_contain_text("Strzała wichru")
    hero = page.locator('[data-panel-actor="nimra"]')
    hero.focus()
    page.keyboard.press("Enter")
    pw.expect(page.locator('[data-panel-actor="nimra"]')).to_be_focused()
    pw.expect(page.locator("#actor-spells")).to_contain_text("Strefa ognia")
    session.capture("rune-powers")
    assert repr(session.game.combat_state) == before
    assert not session.errors


def test_launcher_uses_spatial_navigation_without_changing_selection(player_session: Callable[..., PlayerSession]) -> None:
    session = player_session("launcher")
    page = session.page
    page.goto(page.url.rsplit("/", 1)[0] + "/", wait_until="networkidle")
    menu = page.locator(".main-menu")
    pw.expect(menu).to_be_visible()
    assert menu.locator("button.menu-action").evaluate("element=>getComputedStyle(element).color") == "rgb(240, 234, 223)"
    session.capture("main-menu")
    menu.locator('a[href="/new-game"]').click()
    pw.expect(page.locator("[data-board-status]")).to_contain_text("Klawiatura")
    page.keyboard.press("Enter")
    pw.expect(page.locator('input[name="character_ids"]:checked')).to_have_count(1)
    first = page.locator(".hero-choice").first
    first.focus()
    page.keyboard.press("Numpad6")
    page.wait_for_function("document.activeElement.matches('.hero-choice')")
    selected = page.locator(".hero-choice:focus")
    initial_rect, next_rect = first.bounding_box(), selected.bounding_box()
    assert next_rect["x"] > initial_rect["x"]
    assert abs(next_rect["y"]-initial_rect["y"]) < 5
    pw.expect(page.locator('input[name="character_ids"]:checked')).to_have_count(1)
    session.capture("party-selection")
    page.locator("#continue-to-scenario").click()
    pw.expect(page.locator("#scenario-selection-step")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    assert not session.errors


@pytest.mark.parametrize("mode", ["mission", "equipment", "conversation"])
def test_narrative_equipment_and_conversation_fit_the_laptop(player_session: Callable[..., PlayerSession], mode: str) -> None:
    session = player_session(mode, (1221, 656))
    page = session.page
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth && document.documentElement.scrollHeight<=innerHeight+1")
    session.capture(mode)
    if mode == "equipment":
        session.press("Numpad6")
        assert page.evaluate("document.activeElement.dataset.equipmentSlot") == "pack_1"
    elif mode == "mission":
        stage = page.evaluate("state.mission.stage")
        session.press("Enter")
        assert page.evaluate("state.mission.stage") != stage
    else:
        session.press("Numpad1")
        pw.expect(page.get_by_role("dialog", name="Informacje", exact=True)).to_be_visible()
        session.press("Backspace")
    assert not session.errors


def test_reduced_motion_and_session_dialog_focus(player_session: Callable[..., PlayerSession]) -> None:
    session = player_session()
    page = session.page
    page.emulate_media(reduced_motion="reduce")
    session.press("NumpadDivide")
    dialog = page.locator("#session-navigation")
    pw.expect(dialog).to_be_visible()
    pw.expect(dialog.locator("[data-session-choice]").first).to_be_focused()
    page.keyboard.press("Shift+Tab")
    pw.expect(dialog.locator("header button")).to_be_focused()
    session.press("Enter")
    pw.expect(dialog).not_to_be_visible()
    assert page.locator("#side-panel").evaluate("element=>getComputedStyle(element).transitionDuration") == "0s"
    assert not session.errors

import json
from io import BytesIO

from dnd_board_game.ui.exploration_app import (
    ExplorationUiSession,
    UiFlowStage,
    create_app,
)


def _session(tmp_path) -> ExplorationUiSession:
    return ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        save_dir=tmp_path / "saves",
        observation_dir=tmp_path / "observations",
    )


def test_main_menu_exposes_separate_application_flows(tmp_path) -> None:
    client = create_app(_session(tmp_path)).test_client()

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'href="/new-game"' in html
    assert 'href="/load-game"' in html
    assert 'href="/characters"' in html
    assert "Nowa gra" in html
    assert "Wczytaj grę" in html
    assert "Stwórz postać" in html


def test_new_game_requires_a_roster_party(tmp_path) -> None:
    session = _session(tmp_path)
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    client = create_app(session).test_client()

    response = client.post(
        "/new-game/start",
        data={"scenario_id": session.exploration.scenario_id},
    )

    assert response.status_code == 400
    assert "Wybierz od 1 do 5" in response.get_data(as_text=True)


def test_load_game_empty_state_is_player_facing(tmp_path) -> None:
    client = create_app(_session(tmp_path)).test_client()

    response = client.get("/load-game")

    assert response.status_code == 200
    assert "Nie ma jeszcze zapisanej przygody" in response.get_data(as_text=True)


def test_load_game_restores_snapshot_before_entering_play(tmp_path) -> None:
    session = _session(tmp_path)
    session.save_snapshot()
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    client = create_app(session).test_client()

    response = client.post("/load-game/current")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/play")
    assert session.state_payload()["flow"]["stage"] == "waiting_for_board"


def test_character_module_reads_versioned_catalog(tmp_path) -> None:
    client = create_app(
        _session(tmp_path),
        character_dir=tmp_path / "characters",
    ).test_client()

    response = client.get("/characters/new")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Człowiek" in html
    assert "Niziołek" in html
    assert "Wojownik" in html
    assert "Czarodziej" in html
    assert "Żołnierz" in html
    assert "Mędrzec" in html
    assert "Szarlatan" in html
    assert "Urwis" in html
    assert 'data-creator-step-button="0"' in html
    assert 'data-creator-step="7"' in html
    assert "1. Rasa" in html
    assert "2. Profity rasy" in html
    assert "3. Background" in html
    assert "4. Profity tła" in html
    assert "Siła +1" in html
    assert "Charyzma +1" in html
    assert "Pula point buy" in html
    assert "Wynik:" in html
    assert "Zdolności 1. poziomu:" in html
    assert "Drugi oddech" in html
    assert "Przycisk Szał zużywa jedno użycie" in html
    assert 'class="feature-help"' in html
    assert 'role="tooltip"' in html
    assert 'tabindex="0"' in html
    assert "Fałszywa tożsamość" in html
    assert "W naszej grze:" in html
    assert "Scenariusz nadal może wymagać testu" in html
    assert "Dostępne w pasującej scenie" in html
    assert "nie istnieje jeszcze uniwersalny kreator takich gadżetów" in html
    assert "Zestaw do gry — wybierz 1" in html
    assert "Wybierasz biegłość w jednej grze oraz jej fizyczny zestaw" in html
    assert "Zestaw kości" in html
    assert "Talia kart" in html
    assert "Zestaw smoczych szachów" in html
    assert "Zestaw Trzy Smoki" in html
    assert "Biegłość oznacza, że do pasującego testu dodasz premię z biegłości" in html
    assert "Przykłady: wspinaczka, skok, pływanie, chwyt i odepchnięcie" in html
    assert "Styl walki — wybierz 1" in html
    assert "Kiedy nosisz pancerz, otrzymujesz +1 do Klasy Pancerza" in html
    assert "Gotowy zestaw startowy" in html
    assert "Obecna wersja nie zamienia wyposażenia klasowego na osobną pulę zakupową" in html
    assert "20× Bełt" in html
    assert "Zawartość pakietu" in html
    assert "Podgląd karty" in html
    assert "Akceptuj i utwórz postać" in html
    assert 'data-edit-step="6"' in html
    assert "Magiczny pocisk" in html
    assert "Dłoń maga" in html
    assert "Dice Set" not in html
    assert "Playing Card Set" not in html
    assert "Magic Missile" not in html
    assert "function showCreatorStep" in html
    assert "Następny etap" in html
    assert 'name="id"' not in html
    assert 'type="file" name="portrait_file"' in html
    assert 'enctype="multipart/form-data"' in html
    assert "Gra skopiuje go do rosteru" in html


def test_character_creator_saves_opens_copies_and_deletes_character(tmp_path) -> None:
    character_dir = tmp_path / "characters"
    client = create_app(
        _session(tmp_path),
        character_dir=character_dir,
    ).test_client()
    form = {
        "id": "aldren",
        "name": "Aldren",
        "species_id": "human",
        "class_id": "fighter",
        "background_id": "soldier",
        "strength": "15",
        "dexterity": "14",
        "constitution": "13",
        "intelligence": "12",
        "wisdom": "10",
        "charisma": "8",
        "selected_skill_ids": ["perception", "survival"],
        "selected_fighting_style_id": "defense",
        "equipment_package_id": "fighter_sword_and_board",
        "portrait": "portraits/custom/aldren.webp",
        "selected_species_language_ids": ["elvish"],
        "selected_background_tool_ids": ["dice_set"],
    }

    created = client.post("/characters", data=form)

    assert created.status_code == 302
    assert created.headers["Location"].endswith("/characters/aldren")
    assert (character_dir / "aldren.character.json").is_file()
    detail = client.get("/characters/aldren").get_data(as_text=True)
    assert "Aldren" in detail
    assert "PW" in detail
    assert "Drugi oddech" in detail
    assert "Akcją dodatkową" in detail
    assert "Edytuj jako kopię" in detail
    copied_form = client.get("/characters/aldren/copy").get_data(as_text=True)
    assert 'name="id"' not in copied_form
    assert "Aldren — kopia" in copied_form

    deleted = client.post("/characters/aldren/delete")

    assert deleted.status_code == 302
    assert not (character_dir / "aldren.character.json").exists()
    assert len(tuple((character_dir / ".trash").glob("aldren.*.character.json"))) == 1


def test_character_creator_generates_unique_internal_ids_and_uploads_portrait(
    tmp_path,
) -> None:
    character_dir = tmp_path / "characters"
    session = _session(tmp_path)
    client = create_app(
        session,
        character_dir=character_dir,
    ).test_client()
    form = {
        "id": "gracz_nie_powinien_ustalac_id",
        "name": "Żaneta Łowczyni",
        "species_id": "human",
        "class_id": "fighter",
        "background_id": "soldier",
        "strength": "15",
        "dexterity": "14",
        "constitution": "13",
        "intelligence": "12",
        "wisdom": "10",
        "charisma": "8",
        "selected_skill_ids": ["perception", "survival"],
        "selected_fighting_style_id": "defense",
        "equipment_package_id": "fighter_sword_and_board",
        "selected_species_language_ids": ["elvish"],
        "selected_background_tool_ids": ["dice_set"],
    }
    png = b"\x89PNG\r\n\x1a\n" + b"test-image"

    first = client.post(
        "/characters",
        data={**form, "portrait_file": (BytesIO(png), "zaneta.png")},
    )
    second = client.post("/characters", data=form)

    assert first.status_code == 302
    assert first.headers["Location"].endswith("/characters/zaneta_lowczyni")
    assert second.status_code == 302
    assert second.headers["Location"].endswith("/characters/zaneta_lowczyni_2")
    portrait_path = character_dir / "portraits" / "zaneta_lowczyni.png"
    assert portrait_path.read_bytes() == png
    saved = json.loads(
        (character_dir / "zaneta_lowczyni.character.json").read_text(
            encoding="utf-8"
        )
    )
    assert saved["portrait"] == "character_uploads/zaneta_lowczyni.png"
    served = client.get("/character-portraits/zaneta_lowczyni.png")
    assert served.status_code == 200
    assert served.data == png
    roster = client.get("/characters").get_data(as_text=True)
    assert 'src="/character-portraits/zaneta_lowczyni.png"' in roster
    assert "Portret: Żaneta Łowczyni" in roster


def test_character_creator_rejects_invalid_portrait_file(tmp_path) -> None:
    character_dir = tmp_path / "characters"
    client = create_app(
        _session(tmp_path),
        character_dir=character_dir,
    ).test_client()
    form = {
        "name": "Fałszywy Obraz",
        "species_id": "human",
        "class_id": "fighter",
        "background_id": "soldier",
        "strength": "15",
        "dexterity": "14",
        "constitution": "13",
        "intelligence": "12",
        "wisdom": "10",
        "charisma": "8",
        "selected_skill_ids": ["perception", "survival"],
        "selected_fighting_style_id": "defense",
        "equipment_package_id": "fighter_sword_and_board",
        "selected_species_language_ids": ["elvish"],
        "selected_background_tool_ids": ["dice_set"],
        "portrait_file": (BytesIO(b"not-an-image"), "portrait.png"),
    }

    response = client.post("/characters", data=form)

    assert response.status_code == 400
    assert "PNG, JPEG albo WEBP" in response.get_data(as_text=True)
    assert not tuple(character_dir.glob("*.character.json"))


def test_new_game_replaces_fixture_party_with_selected_character(tmp_path) -> None:
    character_dir = tmp_path / "characters"
    session = _session(tmp_path)
    client = create_app(session, character_dir=character_dir).test_client()
    created = client.post(
        "/characters",
        data={
            "id": "aldren",
            "name": "Aldren",
            "species_id": "human",
            "class_id": "fighter",
            "background_id": "soldier",
            "strength": "15",
            "dexterity": "14",
            "constitution": "13",
            "intelligence": "12",
            "wisdom": "10",
            "charisma": "8",
            "selected_skill_ids": ["perception", "survival"],
            "selected_fighting_style_id": "defense",
            "equipment_package_id": "fighter_sword_and_board",
            "selected_species_language_ids": ["elvish"],
            "selected_background_tool_ids": ["dice_set"],
        },
    )
    assert created.status_code == 302

    response = client.post(
        "/new-game/start",
        data={
            "scenario_id": session.exploration.scenario_id,
            "character_ids": ["aldren"],
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/play")
    allies = [
        actor
        for actor in session.exploration.actors
        if actor.faction.value == "ally"
    ]
    assert [str(actor.id) for actor in allies] == ["aldren"]

    session.save_snapshot()
    restored = _session(tmp_path)
    restored.load_snapshot()
    restored_allies = [
        actor
        for actor in restored.exploration.actors
        if actor.faction.value == "ally"
    ]
    assert [str(actor.id) for actor in restored_allies] == ["aldren"]


def test_character_creator_returns_domain_validation_messages(tmp_path) -> None:
    client = create_app(
        _session(tmp_path),
        character_dir=tmp_path / "characters",
    ).test_client()

    response = client.post(
        "/characters",
        data={
            "id": "broken",
            "name": "Niepełna",
            "species_id": "human",
            "class_id": "fighter",
            "background_id": "soldier",
            "strength": "15",
            "dexterity": "15",
            "constitution": "13",
            "intelligence": "12",
            "wisdom": "10",
            "charisma": "8",
        },
    )

    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "Rozdaj pełną pulę 27 punktów point buy" in html
    assert "przekroczono pulę o 2" in html
    assert "Wybierz dokładnie 2 umiejętności klasowe" in html


def test_character_level_up_page_persists_level_two_without_free_rest(
    tmp_path,
) -> None:
    character_dir = tmp_path / "characters"
    client = create_app(
        _session(tmp_path),
        character_dir=character_dir,
    ).test_client()
    form = {
        "id": "aldren",
        "name": "Aldren",
        "species_id": "human",
        "class_id": "fighter",
        "background_id": "soldier",
        "strength": "15",
        "dexterity": "14",
        "constitution": "13",
        "intelligence": "12",
        "wisdom": "10",
        "charisma": "8",
        "selected_skill_ids": ["perception", "survival"],
        "selected_fighting_style_id": "defense",
        "equipment_package_id": "fighter_sword_and_board",
        "selected_species_language_ids": ["elvish"],
        "selected_background_tool_ids": ["dice_set"],
    }
    assert client.post("/characters", data=form).status_code == 302
    path = character_dir / "aldren.character.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["experience_points"] = 300
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    page = client.get("/characters/aldren/level-up")
    advanced = client.post(
        "/characters/aldren/level-up",
        data={"selected_fighting_style_id": "defense"},
    )

    assert page.status_code == 200
    assert "poziom 1 → 2" in page.get_data(as_text=True)
    assert advanced.status_code == 302
    detail = client.get("/characters/aldren").get_data(as_text=True)
    assert "poziom 2" in detail
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["level"] == 2
    assert saved["experience_points"] == 300

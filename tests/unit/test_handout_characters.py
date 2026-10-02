"""Current character handouts render live rules and editable narrative sources."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Iterator, Any

import pytest

from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.physical_cards.mana_print import build_print_hero
from dnd_board_game.rules.resonance import cards_for
from dnd_board_game.scenarios import character_text
from dnd_board_game.scenarios.rune_relation_catalog import load_rune_relation_catalog

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Element:
    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    children: list[Element | str] = field(default_factory=list)

    @property
    def text(self) -> str:
        if self.tag in {"style", "script"}:
            return ""
        return "".join(child.text if isinstance(child, Element) else child for child in self.children)

    def walk(self) -> Iterator[Element]:
        for child in self.children:
            if isinstance(child, Element):
                yield child
                yield from child.walk()

    def find(self, *, tag: str = "", class_name: str = "") -> list[Element]:
        return [node for node in self.walk() if (not tag or node.tag == tag)
                and (not class_name or class_name in str(node.attrs.get("class", "")).split())]


class SheetParser(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]
        self.feed(html)
        self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Element(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in {"meta", "link", "img", "br", "hr", "input"}:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


@pytest.fixture(scope="module")
def generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("handout_character_generator", ROOT / "scripts/build_rune_relations.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def catalog() -> dict[str, Any]:
    return load_rune_relation_catalog()


@pytest.fixture(scope="module")
def sheets(generator: ModuleType, catalog: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> dict[str, Element]:
    output = tmp_path_factory.mktemp("character-html")
    return {hero: SheetParser(generator.render_hero(hero, catalog, output)).root for hero in PLAYABLE_HERO_IDS}


def resonance_symbols(node: Element) -> tuple[str, ...]:
    return tuple(str(symbol.attrs["aria-label"]).removeprefix("Rezonans: ")
                 for symbol in node.find(class_name="resonance-rune"))


@pytest.mark.parametrize("hero_id", PLAYABLE_HERO_IDS)
def test_five_page_sheet_preserves_stats_and_runtime_power_cards(
    hero_id: str, sheets: dict[str, Element], catalog: dict[str, Any],
) -> None:
    sheet = sheets[hero_id]
    pages = sheet.find(tag="article", class_name="page")
    assert len(pages) == 5
    printed = build_print_hero(hero_id, rune_profile=True)
    vitals = {node.find(tag="label")[0].text: node.find(tag="b")[0].text
              for node in pages[0].find(class_name="vital")}
    assert vitals == {"Punkty wytrzymałości": str(printed.hp), "Klasa pancerza": str(printed.ac),
                      "Ruch": f"{printed.speed} ft", "Inicjatywa": f"{printed.initiative:+d}"}
    stats = [(node.find(tag="label")[0].text, int(node.find(tag="b")[0].text), int(node.find(tag="span")[0].text))
             for node in pages[0].find(class_name="stat")]
    assert tuple(stats) == printed.abilities
    cards = {str(node.attrs["data-card-id"]): node for node in pages[3].find(class_name="relation-card")}
    rules = cards_for(catalog, hero_id)
    assert set(cards) == {"focus", *(card.id for card in rules)}
    for rule in rules:
        card = cards[rule.id]
        assert card.attrs["data-rune"] == rule.rune
        assert card.find(tag="h2")[0].text == rule.name
        assert [node.text for node in card.find(class_name="charge-cost")[0].find(tag="span")] == [
            f"{rule.cost} ładunków", rule.budget,
        ]
        assert card.find(class_name="charge-target")[0].text == rule.target
        assert rule.effect in card.text
        if rule.requirements != "Brak dodatkowych wymagań.":
            assert card.find(class_name="requirement")[0].text == rule.requirements
        gates = card.find(class_name="relation-gate")
        assert bool(gates) == bool(rule.requires_resonance)
        if gates:
            assert resonance_symbols(gates[0]) == rule.requires_resonance
        assert bool(card.find(class_name="relation-finish")) == rule.ends_resonance
        bonuses = card.find(class_name="charge-bonus")
        paragraphs = bonuses[0].find(tag="p") if bonuses else []
        assert len(paragraphs) == len(rule.resonance_bonuses)
        for paragraph, bonus in zip(paragraphs, rule.resonance_bonuses, strict=True):
            assert resonance_symbols(paragraph) == tuple(bonus["requires"])
            assert bonus["text"] in paragraph.text
    equipment = {node.attrs["data-id"] for node in pages[4].find(class_name="item")}
    from dnd_board_game.character_creation.runes import apply_rune_profile
    from dnd_board_game.ui.training_arena import training_hero
    assert equipment == {item.id for item in apply_rune_profile(training_hero(hero_id)).inventory}


@pytest.mark.parametrize("hero_id", PLAYABLE_HERO_IDS)
def test_identity_story_and_recovery_use_current_editable_sources(
    hero_id: str, sheets: dict[str, Element], catalog: dict[str, Any],
) -> None:
    pages = sheets[hero_id].find(tag="article", class_name="page")
    source = character_text.hero_text(hero_id)
    hero = catalog["heroes"][hero_id]
    for text in (source["history"], source["motivation"], source["character_line"],
                 hero["vignette"]["title"], hero["vignette"]["text"], hero["flaw"]["name"],
                 hero["flaw"]["description"], hero["passive"]["name"], hero["passive"]["description"],
                 *hero["regeneration"]):
        assert text in pages[0].text
    assert pages[0].find(class_name="recovery-die")[0].text == "1k4"
    assert pages[1].find(class_name="goal-slot")
    assert [step.attrs["aria-label"] for step in pages[1].find(class_name="goal-step")] == [
        f"Postęp {step} z 5" for step in range(1, 6)
    ]


def test_editing_narrative_sources_refreshes_render_without_generated_assets(
    generator: ModuleType, catalog: dict[str, Any], sheets: dict[str, Element],
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = character_text.SOURCE_PATH
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if "player_aid_file" in source:
        aid = source["player_aid_file"]
        (tmp_path / aid).write_bytes((source_path.parent / aid).read_bytes())
    source["heroes"]["garran"]["history"] = "Nowa historia <Garran & drużyna> z edytowalnego JSON."
    source["heroes"]["garran"]["character_line"] = "Nowe słowa Garrana & jego drużyny."
    path = tmp_path / "karty_postaci.json"
    path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(character_text, "SOURCE_PATH", path)

    relations = deepcopy(catalog)
    relations["heroes"]["garran"]["vignette"]["text"] = "Nowa scenka z katalogu relacji <Wieża & Grot>."
    relation_path = tmp_path / "relations.json"
    relation_path.write_text(json.dumps(relations, ensure_ascii=False), encoding="utf-8")
    edited = load_rune_relation_catalog(relation_path)
    first_html = generator.render_hero("garran", edited, tmp_path)
    first = SheetParser(first_html).root.find(tag="article", class_name="page")[0]
    assert source["heroes"]["garran"]["history"] in first.text
    assert source["heroes"]["garran"]["character_line"] in first.text
    assert relations["heroes"]["garran"]["vignette"]["text"] in first.text
    assert "&lt;Garran &amp; drużyna&gt;" in first_html
    original = sheets["garran"].find(tag="article", class_name="page")[0]
    assert [node.text for node in first.find(class_name="stat")] == [node.text for node in original.find(class_name="stat")]

    source["heroes"]["garran"]["motivation"] = "Drugie zapisanie tego samego JSON zmienia powód podróży."
    path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    second = SheetParser(generator.render_hero("garran", edited, tmp_path)).root
    assert source["heroes"]["garran"]["motivation"] in second.text
    assert not list(tmp_path.glob("*.pdf")) and not list(tmp_path.glob("*.png"))

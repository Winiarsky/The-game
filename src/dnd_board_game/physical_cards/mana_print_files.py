"""Sequential HTML/PDF export using installed Chrome and Poppler, no new packages."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from .mana_print import COLORS, PROFILE, COMMON_KEYS, MANA_PASSIVE_REMINDER, build_print_hero
from dnd_board_game.scenarios.confrontation import REMINDER
from dnd_board_game.scenarios.confrontation_terms import effect_name
from dnd_board_game.ui.board_panel_symbols import SYMBOLS, PANEL_CONTROLS
from .mana_print_html import FORMATS, render_hero_html

ROOT = Path(__file__).resolve().parents[3]
ASSET_ROOT = ROOT / "assets/physical_cards/character_sets"
DEFAULT_OUTPUT = ASSET_ROOT / "physical_mana_v02"  # Stable published location; manifest identifies the current profile.


def render_pdf(html: Path, pdf: Path) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        raise RuntimeError(
            "Brak Chrome/Chromium. HTML można wydrukować ręcznie albo użyć --html-only."
        )
    with TemporaryDirectory(prefix="mana-print-") as temporary:
        result = subprocess.run(
            [
                chrome,
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-background-networking",
                "--disable-extensions",
                "--disable-sync",
                "--no-first-run",
                "--no-default-browser-check",
                "--no-pdf-header-footer",
                f"--user-data-dir={temporary}",
                f"--print-to-pdf={pdf.resolve()}",
                html.resolve().as_uri(),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode or not pdf.is_file():
            raise RuntimeError(f"Nie udało się wydrukować {html.name}: {result.stderr[-700:]}")


def merge_pdfs(paths: list[Path], destination: Path) -> None:
    binary = shutil.which("pdfunite")
    if not binary:
        raise RuntimeError("Brak pdfunite; osobne pliki postaci są gotowe.")
    temporary = destination.with_suffix(".tmp.pdf")
    subprocess.run([binary, *(str(path) for path in paths), str(temporary)], check=True, timeout=60)
    temporary.replace(destination)


def legacy_aliases(output: Path, formats: tuple[str, ...], actor_ids: tuple[str, ...]) -> None:
    """Keep familiar print links current; canonical files carry the profile version."""
    aliases: list[tuple[Path, Path]] = []
    for format_id in formats:
        combined = output / format_id / "all_heroes.pdf"
        if format_id == "color":
            old_root = ASSET_ROOT / "keyboard_v1/pdf"
            aliases.append((combined, old_root / "keyboard_character_sheets_v1.pdf"))
            aliases.extend(
                (output / format_id / f"{hero}.pdf", old_root / f"{hero}_keyboard_sheet_v1.pdf")
                for hero in actor_ids
            )
        elif format_id == "minimal":
            old_root = ASSET_ROOT / "keyboard_v1/minimal_bw/pdf"
            aliases.append((combined, old_root / "minimal_bw_character_sheets_v1.pdf"))
            aliases.extend(
                (output / format_id / f"{hero}.pdf", old_root / f"{hero}_minimal_bw_v1.pdf")
                for hero in actor_ids
            )
            aliases.append((combined, ASSET_ROOT / "character_sheets_bw/character_sheets_bw.pdf"))
            aliases.extend(
                (
                    output / format_id / f"{hero}.pdf",
                    ASSET_ROOT / f"character_sheets_bw/character_sheet_{hero}_bw.pdf",
                )
                for hero in actor_ids
            )
        elif format_id == "bw_test":
            aliases.append((combined, ASSET_ROOT / "bw_test/card_sets_bw_test.pdf"))
            aliases.extend(
                (
                    output / format_id / f"{hero}.pdf",
                    ASSET_ROOT / f"bw_test/card_set_{hero}_bw_test.pdf",
                )
                for hero in actor_ids
            )
        elif format_id == "cards":
            aliases.append((combined, ASSET_ROOT / "card_sets.pdf"))
            aliases.extend(
                (output / format_id / f"{hero}.pdf", ASSET_ROOT / f"card_set_{hero}.pdf")
                for hero in actor_ids
            )
    for source, target in aliases:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        # A matching sidecar prevents an old PDF manifest describing the new file.
        manifest = source.parent / (source.stem + ".json")
        if manifest.exists():
            shutil.copyfile(manifest, Path(str(target) + ".json"))


def write_reference(output: Path, actor_ids: tuple[str, ...]) -> None:
    heroes = [build_print_hero(hero_id) for hero_id in actor_ids]
    manifest = {
        "rules_profile": PROFILE,
        "exploration_rules_version": 3,
        "version": 13,
        "mana_passive_revision": 2,
        "mana_catalog_version": 2,
        "roll_rules": "charge_replaces_proficiency_v1",
        "panel_symbols_version": 1,
        "panel_controls": PANEL_CONTROLS,
        "common_keys": COMMON_KEYS,
        "heroes": [hero.as_payload() for hero in heroes],
    }
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    (output / "manifest.json").write_text(text, encoding="utf-8")
    if output == DEFAULT_OUTPUT and set(actor_ids) == set(PLAYABLE_HERO_IDS):
        legacy = ASSET_ROOT / "keyboard_v1/keyboard_character_cards_v1.json"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(text, encoding="utf-8")
        lines = [
            "# Siedem archetypów — ładowanie many 2.0",
            "",
            "Źródło: katalog `content/balance/pooled_mana/catalog.json`, profile postaci i stałe oznaczenia panelu areny.",
            "Wygenerowano przez `scripts/generate_mana_character_prints.py`.",
            "",
            "Każdy symbol oznacza osobną kartę. Biała: słońce (Plains); niebieska: kropla (Island); czarna: czaszka (Swamp); czerwona: płomień (Mountain); zielona: drzewo (Forest). Cyfra 1 w kółku: dowolny kolor.",
            "A = akcja główna, D = dodatkowa, R = reakcja, MOD = modyfikacja. Koszt obejmuje opisane ataki. T = początek następnej tury źródła; O = mana drain. Dolny pasek mapy wyłączony; symbole pozostają wydrukowane.",
            "",
            "PDF-y: `assets/physical_cards/character_sets/physical_mana_v02/` — color, minimal, cards i bw_test.",
            "",
        ]
        for hero in heroes:
            lines += [
                f"## {hero.name} — {hero.role}",
                "",
                f"PW {hero.hp}; KP {hero.ac}; ruch {hero.speed} ft.",
                "Wspólna talia: po max(5, 2 × liczba bohaterów) kart każdego koloru. Oferta dwóch kart, dobór jednej na początku własnej tury poniżej 21 pkt. Ładunek pozostaje do draina; bazowa akcja spala 1 kartę z wierzchu, podbicie dodatkowe 2.",
                "",
            ]
            for card in hero.cards:
                symbol = SYMBOLS[card.panel_slot][0] if card.panel_slot is not None else "Reakcja"
                lines += [f"### {card.name} · {symbol}", ""]
                lines += [f"- **{label}:** {text}" for label, text in card.sections]
                lines.append("")
            lines += ["", "### Eksploracja — NPC i obiekty", ""]
            for method in hero.exploration:
                lines.append(f"- **{method.name} ({'NPC' if method.kind == 'npc' else 'obiekt'}):** {method.ability}, bazowy test {method.modifier:+d}; {effect_name(method.kind).lower()}: kość podatności {method.influence_modifier:+d}. {method.description}")
            lines += ["", REMINDER, ""]
            lines += [f"- **{COLORS[color]}:** {label}" for color, label in hero.exploration_passives]
            lines += ["", "### Pasywy i skaza", ""]
            lines += [f"- **{name}:** {body}" for name, body in hero.passives[:-1]]
            lines += ["", "#### Nasycenie maną", ""]
            lines += [f"- **{COLORS[color]}:** {label}" for color, label in hero.mana_passives]
            lines += ["", MANA_PASSIVE_REMINDER]
            lines += ["", f"**Skaza — {hero.flaw[0]}:** {hero.flaw[1]}", ""]
        (ROOT / "docs/BOARDGAME_ARCHETYPES_LEVELS_1_3.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )


def main(default_formats: tuple[str, ...] = FORMATS) -> int:
    parser = argparse.ArgumentParser(
        description="Aktualne karty siedmiu postaci: osobiste pule many."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--actor", action="append", choices=PLAYABLE_HERO_IDS)
    parser.add_argument("--format", action="append", choices=FORMATS)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--html-only", action="store_true")
    parser.add_argument("--bw-test-only", action="store_true")
    args = parser.parse_args()
    formats = tuple(args.format or (("bw_test",) if args.bw_test_only else default_formats))
    actor_ids = tuple(args.actor or PLAYABLE_HERO_IDS)
    output = args.output_dir.resolve()
    # Preflight before replacing any files.
    if not args.overwrite:
        for format_id in formats:
            for hero_id in actor_ids:
                target = output / format_id / f"{hero_id}.html"
                if target.exists():
                    parser.error(f"Plik już istnieje: {target}; użyj --overwrite.")
    output.mkdir(parents=True, exist_ok=True)
    for format_id in formats:
        directory = output / format_id
        directory.mkdir(parents=True, exist_ok=True)
        pdfs: list[Path] = []
        manifests: list[dict[str, object]] = []
        for hero_id in actor_ids:
            hero = build_print_hero(hero_id)
            html = directory / f"{hero_id}.html"
            portrait = ROOT / f"assets/character_portraits/default_roster_v2/{hero_id}.png"
            html.write_text(
                render_hero_html(
                    hero, format_id, portrait_path=portrait if portrait.exists() else None
                ),
                encoding="utf-8",
            )
            payload = hero.as_payload()
            (directory / f"{hero_id}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            manifests.append(payload)
            if not args.html_only:
                pdf = directory / f"{hero_id}.pdf"
                render_pdf(html, pdf)
                pdfs.append(pdf)
            print(f"{format_id}: {hero.name}, {len(hero.cards)} zdolności — gotowe", flush=True)
        (directory / "all_heroes.json").write_text(
            json.dumps(
                {"rules_profile": PROFILE, "heroes": manifests}, ensure_ascii=False, indent=2
            )
            + "\n",
            encoding="utf-8",
        )
        if pdfs:
            merge_pdfs(pdfs, directory / "all_heroes.pdf")
    write_reference(output, actor_ids)
    if output == DEFAULT_OUTPUT and not args.html_only:
        legacy_aliases(output, formats, actor_ids)
    (output / "README.md").write_text(
        "# Aktualne wydruki — fizyczna mana 0.2\n\n"
        "color: kolorowe arkusze; minimal: oszczędne arkusze; cards: kolorowe karty do wycięcia; bw_test: czarno-białe karty bez rewersów.\n\n"
        "Każdy katalog: osobny HTML/PDF/JSON na bohatera i zbiorczy all_heroes.pdf. A4, skala 100%. "
        "AUTO/REAKCJA oznacza wybór w oknie aplikacji, nie literę skrótu. "
        "Statystyki, pasywy, skaza i dossier są dołączone do każdego zestawu.\n\n"
        "Wygeneruj ponownie: PYTHONPATH=src python scripts/generate_mana_character_prints.py --overwrite\n",
        encoding="utf-8",
    )
    return 0

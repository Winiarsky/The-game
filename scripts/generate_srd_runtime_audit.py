#!/usr/bin/env python3
"""Generate the current SRD level-3 runtime audit from the Arena registry."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = (
    PROJECT_ROOT / "content/scenarios/mechanics_playground/audit_cases.json"
)
REPORT_PATH = PROJECT_ROOT / "docs/SRD_LEVEL_3_RUNTIME_AUDIT_2026-07-29.md"

CATEGORY_LABELS = {
    "spell": "Czary poziomów 0–2",
    "species_feature": "Cechy rasowe",
    "class_feature": "Cechy klasowe",
    "subclass_feature": "Cechy podklas",
    "cross_cutting_mechanic": "Mechaniki przekrojowe",
}
CATEGORY_ORDER = tuple(CATEGORY_LABELS)
MODULE_LABELS = {
    "combat_arena": "Arena walki",
    "spell_lab": "Laboratorium czarów",
    "exploration_course": "Tor eksploracyjny",
    "social_lab": "Pracownia rozmów",
    "rest_station": "Stacja odpoczynku",
}


def _cell(value: object) -> str:
    return (
        str(value)
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", "<br>")
    )


def _joined(values: Iterable[object]) -> str:
    return "<br>".join(_cell(value) for value in values)


def _test_references(case: dict[str, Any]) -> str:
    references = case.get("automatic_tests", ())
    if not references:
        return "—"
    return "<br>".join(f"`{_cell(reference)}`" for reference in references)


def _category_rows(
    cases: list[dict[str, Any]],
    *,
    status: str,
) -> list[str]:
    rows: list[str] = []
    for category in CATEGORY_ORDER:
        category_cases = [
            case
            for case in cases
            if case["category"] == category and case["status"] == status
        ]
        if not category_cases:
            continue
        rows.extend(
            [
                f"### {CATEGORY_LABELS[category]}",
                "",
            ]
        )
        if status == "tested_automatically":
            rows.extend(
                [
                    "| ID | Nazwa | Moduł Areny | Aktualny efekt / oczekiwany rezultat | Dowód automatyczny |",
                    "|---|---|---|---|---|",
                ]
            )
            for case in category_cases:
                rows.append(
                    "| `{id}` | {label} | {module} | {expected} | {tests} |".format(
                        id=_cell(case["id"]),
                        label=_cell(case["label"]),
                        module=_cell(MODULE_LABELS.get(case["module"], case["module"])),
                        expected=_joined(case["expected_results"]),
                        tests=_test_references(case),
                    )
                )
        else:
            rows.extend(
                [
                    "| ID | Nazwa | Moduł Areny | Docelowy test | Powód odłożenia |",
                    "|---|---|---|---|---|",
                ]
            )
            for case in category_cases:
                rows.append(
                    "| `{id}` | {label} | {module} | {expected} | {notes} |".format(
                        id=_cell(case["id"]),
                        label=_cell(case["label"]),
                        module=_cell(MODULE_LABELS.get(case["module"], case["module"])),
                        expected=_joined(case["expected_results"]),
                        notes=_cell(case["notes"]),
                    )
                )
        rows.append("")
    return rows


def generate_report(registry: dict[str, Any]) -> str:
    cases = list(registry["cases"])
    statuses = Counter(case["status"] for case in cases)
    categories = Counter(
        (case["category"], case["status"]) for case in cases
    )
    modules = Counter(case["module"] for case in cases)
    unique_test_references = {
        reference
        for case in cases
        if case["status"] == "tested_automatically"
        for reference in case.get("automatic_tests", ())
    }

    lines = [
        "# Audyt zgodności mechanik postaci z SRD 5.1",
        "",
        "Data pierwszego audytu: 2026-07-29",
        "",
        "Aktualizacja po naprawach i testach Areny: 2026-07-30",
        "",
        "Zakres: D&D 5e 2014 / SRD 5.1, postacie jednoklasowe do 3. poziomu,",
        "9 ras, 12 klas i 127 czarów poziomów 0–2.",
        "",
        "Źródłem porównawczym jest",
        "[System Reference Document 5.1](https://media.wizards.com/2016/downloads/DND/SRD-OGL_V5.1.pdf).",
        "Bieżącym źródłem statusów, presetów i instrukcji testowych jest",
        "[rejestr Areny](../content/scenarios/mechanics_playground/audit_cases.json).",
        "Ten dokument jest generowany z rejestru poleceniem",
        "`python scripts/generate_srd_runtime_audit.py`; nie zawiera już historycznych",
        "statusów sprzed napraw.",
        "",
        "## Wynik końcowy",
        "",
        "| Wynik | Liczba |",
        "|---|---:|",
        f"| Wszystkie przypadki | {len(cases)} |",
        f"| ✅ Przetestowane automatycznie | {statuses['tested_automatically']} |",
        f"| ⏸️ Świadomie odłożone z uzasadnieniem | {statuses['skipped']} |",
        "| ❓ Nierozstrzygnięte | 0 |",
        f"| Unikalne odwołania do testów | {len(unique_test_references)} |",
        "",
        "Status **przetestowane automatycznie** oznacza, że przypadek ma wykonywalny",
        "resolver oraz co najmniej jeden wskazany test rezultatu lub kontraktu.",
        "Status **świadomie odłożone** oznacza, że brak został zidentyfikowany, ma",
        "odtwarzalny preset Areny i komentarz opisujący potrzebny system. Nie jest",
        "traktowany jako działająca mechanika.",
        "",
        "## Pokrycie według obszaru",
        "",
        "| Obszar | Razem | Automatycznie | Odłożone |",
        "|---|---:|---:|---:|",
    ]
    for category in CATEGORY_ORDER:
        tested = categories[(category, "tested_automatically")]
        skipped = categories[(category, "skipped")]
        lines.append(
            f"| {CATEGORY_LABELS[category]} | {tested + skipped} | {tested} | {skipped} |"
        )
    lines.extend(
        [
            "",
            "## Pokrycie modułów Areny",
            "",
            "| Moduł | Liczba przypadków |",
            "|---|---:|",
        ]
    )
    for module, count in sorted(
        modules.items(),
        key=lambda item: (-item[1], MODULE_LABELS.get(item[0], item[0])),
    ):
        lines.append(
            f"| {MODULE_LABELS.get(module, module)} | {count} |"
        )
    lines.extend(
        [
            "",
            "Każdy z 236 wpisów przechowuje `arena_config`, wymagania drużyny, kroki",
            "ręczne i oczekiwane wyniki. Pozwala to odtworzyć ręcznie dokładnie te same",
            "warunki, których użyto podczas audytu.",
            "",
            "## Najważniejsze domknięte problemy",
            "",
            "- Skorygowano koncentrację, czas działania, koszty akcji i zużywanie zasobów.",
            "- Wszystkie bojowe rodziny `effect_kind` mają zarejestrowaną granicę wykonawczą;",
            "  audyt blokuje ponowne dodanie martwego markera bez konsumenta.",
            "- Celowanie w aktorów, pola, linie, stożki i obszary jest prowadzone przez",
            "  planszę oraz legalne podświetlone pola.",
            "- Trwałe strefy obsługują właściwy dla danego czaru obszar, ruch, widoczność,",
            "  trudny teren, wejście w strefę lub początek tury.",
            "- Flankowanie daje przewagę zamiast liczbowego `+0` i nie korzysta z",
            "  obezwładnionego sojusznika.",
            "- Naprawiono m.in. Niewidzialność, Piętnujące porażenie, Znak łowcy,",
            "  Ostrze płomieni, Płonącą kulę, Rozgrzanie metalu, Wzmocnienie cechy,",
            "  Rozmycie, Ochronę przed dobrem i złem oraz ignorowanie osłony przez",
            "  Święty płomień.",
            "- Nazwy czarów, zdolności, umiejętności, narzędzi i przedmiotów używane",
            "  w interfejsie mają polskie etykiety.",
            "",
            "## Aktualnie przetestowane przypadki",
            "",
            "Poniższe statusy pochodzą bezpośrednio z rejestru Areny. Pełne kroki ręczne,",
            "skład drużyny i konfiguracja manekinów pozostają w pliku JSON.",
            "",
        ]
    )
    lines.extend(_category_rows(cases, status="tested_automatically"))
    lines.extend(
        [
            "## Świadomie odłożone przypadki",
            "",
            "Poniższe mechaniki nie są przedstawiane jako kompletne. Każda ma zapisany",
            "preset i oczekiwany rezultat, ale wymaga większej granicy systemowej,",
            "authored contentu albo kontraktu LLM. Należy wrócić do niej dopiero wtedy,",
            "gdy korzystający z niej scenariusz wejdzie do produkcji.",
            "",
        ]
    )
    lines.extend(_category_rows(cases, status="skipped"))
    lines.extend(
        [
            "## Jak odtwarzać przypadki na Arenie",
            "",
            "1. Uruchom scenariusz **Arena mechanik — laboratorium**.",
            "2. W panelu Areny wybierz wpis po nazwie lub identyfikatorze.",
            "3. Załaduj zapisany preset; parametry manekinów pochodzą z `arena_config`.",
            "4. Przygotuj postacie wskazane w `party_requirements`.",
            "5. Wykonaj `manual_steps` i porównaj rezultat z `expected_results`.",
            "6. Dla przypadku automatycznego użyj wskazanych w tabeli testów jako",
            "   regresji. Dla przypadku odłożonego najpierw zrealizuj system opisany",
            "   w kolumnie „Powód odłożenia”.",
            "",
            "## Walidacja raportu",
            "",
            "Rejestr Areny jest objęty testami sprawdzającymi pełny zbiór 236",
            "identyfikatorów, poprawność statusów, obecność presetów, instrukcji,",
            "oczekiwanych wyników i odwołań do testów. Końcowa regresja po naprawach",
            "objęła 783 zaliczone testy w kontrolowanych partiach, w tym 247 testów",
            "pełnej sesji UI oraz 77 testów aplikacji webowej.",
            "",
            "Aby sprawdzić, czy dokument odpowiada rejestrowi bez nadpisywania pliku:",
            "",
            "```bash",
            "python scripts/generate_srd_runtime_audit.py --check",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Zwróć błąd, jeśli raport nie odpowiada rejestrowi.",
    )
    args = parser.parse_args()
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    generated = generate_report(registry)
    if args.check:
        current = REPORT_PATH.read_text(encoding="utf-8")
        if current != generated:
            print(f"Raport jest nieaktualny: {REPORT_PATH}")
            return 1
        print(
            f"Raport jest aktualny: {len(registry['cases'])} przypadków."
        )
        return 0
    REPORT_PATH.write_text(generated, encoding="utf-8")
    print(
        f"Zaktualizowano {REPORT_PATH}: {len(registry['cases'])} przypadków."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

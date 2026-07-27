from __future__ import annotations

import argparse
import json
from pathlib import Path

from dnd_board_game.scenarios.content_audit import audit_content


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate versioned content headers, stable ids and scenario references."
    )
    parser.add_argument(
        "content_root",
        nargs="?",
        default="content",
        help="Content directory to audit (default: content).",
    )
    parser.add_argument("--json", action="store_true", help="Print the full JSON report.")
    args = parser.parse_args()
    report = audit_content(Path(args.content_root))
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        summary = report.as_dict()["summary"]
        print(
            f"content audit: entries={summary['entries']} "
            f"scenarios={summary['scenarios']} errors={summary['errors']} "
            f"warnings={summary['warnings']}"
        )
        for issue in report.issues:
            print(
                f"{issue.severity.value}: {issue.code}: "
                f"{issue.path}: {issue.message}"
            )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

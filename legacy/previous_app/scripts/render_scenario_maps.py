from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scenario_map_renderer import DEFAULT_OUTPUT_DIR, DEFAULT_SCENARIOS_DIR, render_all_scenarios, render_scenario_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render technical SVG maps for scenario files.")
    parser.add_argument(
        "scenarios",
        nargs="*",
        help="Optional scenario names or json filenames. If omitted, render all scenarios/*.json.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for generated SVG files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    if not args.scenarios:
        generated = render_all_scenarios(output_dir=output_dir)
    else:
        generated = []
        for item in args.scenarios:
            path = Path(item)
            if path.suffix != ".json":
                path = DEFAULT_SCENARIOS_DIR / f"{item}.json"
            elif not path.is_absolute():
                path = DEFAULT_SCENARIOS_DIR / path.name
            map_path, legend_path = render_scenario_files(path, output_dir=output_dir)
            generated.extend([map_path, legend_path])

    for path in generated:
        print(path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

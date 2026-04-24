#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/safe_pytest.sh [--timeout SECONDS] TEST_TARGET [PYTEST_ARGS...]

Runs one small pytest batch with a timeout and refuses to start if another
pytest process is already running.

Examples:
  scripts/safe_pytest.sh tests/test_trap_mechanics.py
  scripts/safe_pytest.sh --timeout 90 tests/test_trap_mechanics.py::test_seek_preview
EOF
}

timeout_seconds=60
args=()

while (($#)); do
    case "$1" in
        --timeout)
            if (($# < 2)); then
                echo "safe_pytest: --timeout requires seconds" >&2
                exit 2
            fi
            timeout_seconds="$2"
            shift 2
            ;;
        --timeout=*)
            timeout_seconds="${1#--timeout=}"
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            args+=("$1")
            shift
            ;;
    esac
done

if ! [[ "$timeout_seconds" =~ ^[0-9]+$ ]] || ((timeout_seconds < 1)); then
    echo "safe_pytest: timeout must be a positive integer" >&2
    exit 2
fi

if ((${#args[@]} == 0)); then
    usage >&2
    exit 2
fi

has_target=0
for arg in "${args[@]}"; do
    case "$arg" in
        -*)
            ;;
        .|./|tests|tests/)
            echo "safe_pytest: broad target '$arg' is not allowed; pass a specific test file or node id" >&2
            exit 2
            ;;
        *.py|*.py::*|tests/*)
            has_target=1
            ;;
    esac
done

if ((has_target == 0)); then
    echo "safe_pytest: pass at least one concrete test file or pytest node id" >&2
    exit 2
fi

running_pytest="$(pgrep -af '(^|[ /])pytest([[:space:]]|$)' || true)"
if [[ -n "$running_pytest" ]]; then
    echo "safe_pytest: refusing to start because pytest is already running:" >&2
    echo "$running_pytest" >&2
    exit 3
fi

exec timeout --preserve-status "${timeout_seconds}s" pytest -q --tb=short "${args[@]}"

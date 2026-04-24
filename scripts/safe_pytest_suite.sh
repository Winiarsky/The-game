#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/safe_pytest_suite.sh [--timeout SECONDS] [--continue-on-fail] [--start-at FILE] [--start-after FILE]

Runs the test suite one test file at a time through scripts/safe_pytest.sh.
This keeps pytest processes sequential, applies a per-file timeout, and writes
full per-file output to a capped log under /tmp.

Use --start-at to resume from a specific test file, or --start-after to continue
with the next file after a test that already passed locally.
EOF
}

timeout_seconds=60
continue_on_fail=0
start_at=""
start_after=""

while (($#)); do
    case "$1" in
        --timeout)
            timeout_seconds="${2:-}"
            shift 2
            ;;
        --timeout=*)
            timeout_seconds="${1#--timeout=}"
            shift
            ;;
        --continue-on-fail)
            continue_on_fail=1
            shift
            ;;
        --start-at)
            start_at="${2:-}"
            shift 2
            ;;
        --start-at=*)
            start_at="${1#--start-at=}"
            shift
            ;;
        --start-after)
            start_after="${2:-}"
            shift 2
            ;;
        --start-after=*)
            start_after="${1#--start-after=}"
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "safe_pytest_suite: unknown argument '$1'" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if ! [[ "$timeout_seconds" =~ ^[0-9]+$ ]] || ((timeout_seconds < 1)); then
    echo "safe_pytest_suite: timeout must be a positive integer" >&2
    exit 2
fi
if [[ -n "$start_at" && -n "$start_after" ]]; then
    echo "safe_pytest_suite: use only one of --start-at or --start-after" >&2
    exit 2
fi

if [[ ! -x scripts/safe_pytest.sh ]]; then
    echo "safe_pytest_suite: scripts/safe_pytest.sh is missing or not executable" >&2
    exit 1
fi

mapfile -t test_files < <(find tests -maxdepth 1 -type f -name 'test_*.py' | sort)
total=${#test_files[@]}
if ((total == 0)); then
    echo "safe_pytest_suite: no tests/test_*.py files found" >&2
    exit 1
fi

start_index=0
if [[ -n "$start_at" || -n "$start_after" ]]; then
    marker="${start_at:-$start_after}"
    found_index=-1
    for idx in "${!test_files[@]}"; do
        if [[ "${test_files[$idx]}" == "$marker" ]]; then
            found_index="$idx"
            break
        fi
    done
    if ((found_index < 0)); then
        echo "safe_pytest_suite: resume marker not found: $marker" >&2
        exit 2
    fi
    start_index="$found_index"
    if [[ -n "$start_after" ]]; then
        start_index=$((found_index + 1))
    fi
    if ((start_index >= total)); then
        echo "safe_pytest_suite: resume marker is at or beyond the last test file" >&2
        exit 2
    fi
fi

log_file="/tmp/safe_pytest_suite_$(date +%Y%m%d_%H%M%S).log"
failures=0
start_epoch=$(date +%s)

echo "safe_pytest_suite: running $total files, timeout=${timeout_seconds}s, log=$log_file"
if ((start_index > 0)); then
    echo "safe_pytest_suite: resuming at [$((start_index + 1))/$total] ${test_files[$start_index]}"
fi

for idx in "${!test_files[@]}"; do
    if ((idx < start_index)); then
        continue
    fi
    test_file="${test_files[$idx]}"
    printf '[%03d/%03d] %s ... ' "$((idx + 1))" "$total" "$test_file"
    tmp_out="$(mktemp /tmp/safe_pytest_one.XXXXXX)"
    file_start=$(date +%s)
    set +e
    scripts/safe_pytest.sh --timeout "$timeout_seconds" "$test_file" >"$tmp_out" 2>&1
    status=$?
    set -e
    file_end=$(date +%s)
    duration=$((file_end - file_start))
    {
        printf '===== %s status=%s duration=%ss =====\n' "$test_file" "$status" "$duration"
        cat "$tmp_out"
        printf '\n'
    } >>"$log_file"
    if ((status == 0)); then
        printf 'ok (%ss)\n' "$duration"
    elif ((status == 5)); then
        printf 'skip-no-tests (%ss)\n' "$duration"
    else
        failures=$((failures + 1))
        printf 'FAIL status=%s (%ss)\n' "$status" "$duration"
        tail -80 "$tmp_out"
        rm -f "$tmp_out"
        if ((continue_on_fail == 0)); then
            echo "safe_pytest_suite: stopped after first failure; full log: $log_file" >&2
            exit "$status"
        fi
    fi
    rm -f "$tmp_out"
done

end_epoch=$(date +%s)
duration=$((end_epoch - start_epoch))
if ((failures > 0)); then
    echo "safe_pytest_suite: completed with $failures failing files in ${duration}s; log: $log_file" >&2
    exit 1
fi

echo "safe_pytest_suite: all $total files passed in ${duration}s; log: $log_file"

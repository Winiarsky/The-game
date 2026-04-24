#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/read_recent_codex_logs.sh --since 'YYYY-MM-DD HH:MM:SS' [--until 'YYYY-MM-DD HH:MM:SS'] [--limit N] [--pattern TEXT]

Reads a narrow slice of ~/.codex/logs_2.sqlite. Output is intentionally capped
to avoid pulling large Codex sessions into the active context.
EOF
}

since=""
until=""
limit=80
pattern=""

while (($#)); do
    case "$1" in
        --since)
            since="${2:-}"
            shift 2
            ;;
        --until)
            until="${2:-}"
            shift 2
            ;;
        --limit)
            limit="${2:-}"
            shift 2
            ;;
        --pattern)
            pattern="${2:-}"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "read_recent_codex_logs: unknown argument '$1'" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -z "$since" ]]; then
    echo "read_recent_codex_logs: --since is required" >&2
    usage >&2
    exit 2
fi

if ! [[ "$limit" =~ ^[0-9]+$ ]] || ((limit < 1 || limit > 200)); then
    echo "read_recent_codex_logs: --limit must be between 1 and 200" >&2
    exit 2
fi

db="${CODEX_LOG_DB:-$HOME/.codex/logs_2.sqlite}"
if [[ ! -f "$db" ]]; then
    echo "read_recent_codex_logs: missing Codex log db: $db" >&2
    exit 1
fi

where="ts >= strftime('%s', '$since', 'utc')"
if [[ -n "$until" ]]; then
    where="$where and ts <= strftime('%s', '$until', 'utc')"
fi
if [[ -n "$pattern" ]]; then
    escaped_pattern="${pattern//\'/\'\'}"
    where="$where and feedback_log_body like '%$escaped_pattern%'"
fi

sqlite3 -line "$db" \
    "select datetime(ts,'unixepoch','localtime') as time,
            level,
            target,
            substr(feedback_log_body, 1, 1200) as body
       from logs
      where $where
      order by ts desc, ts_nanos desc
      limit $limit;"

# Codex Notes

## Test Safety

- Run pytest in small, targeted batches instead of broad or parallel runs.
- Run pytest through `scripts/safe_pytest.sh` by default, with a concrete test file or node id.
- Avoid launching multiple `pytest` processes at once in this workspace; the wrapper refuses to start if one is already active.
- Use a timeout for every pytest run. The wrapper defaults to 60 seconds and supports `--timeout SECONDS`.
- Keep command output capped when reading logs or test output.
- Be careful with broad searches through `data/debug_sessions`, `logs`, and Codex session logs; prefer narrow time windows and specific filenames.
- Use `scripts/read_recent_codex_logs.sh` for Codex logs instead of direct broad reads from `~/.codex/logs_2.sqlite`.
- Context: on 2026-04-24 around 13:20 local time, the VS Code/Codex scope reached about 13.9 GB memory and `systemd-oomd` killed the desktop session.

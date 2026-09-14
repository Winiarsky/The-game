"""Execute production firmware protocol and MCP driver with a simulated bus."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest


BOOT = 'a18b920000000001'
SESSION = 'b42c810000000001'
FIRMWARE = Path('future/board_20x30_usb_wled_test')


@pytest.fixture(scope='module')
def firmware(tmp_path_factory: pytest.TempPathFactory) -> Path:
    compiler = shutil.which('g++')
    if compiler is None:
        pytest.skip('g++ is required for the firmware simulator')
    binary = tmp_path_factory.mktemp('firmware') / 'scanner'
    compiled = subprocess.run(
        [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
         '-fsanitize=undefined', '-fno-sanitize-recover=all',
         '-I', str(FIRMWARE), 'tests/hardware/firmware_scan_harness.cpp', '-o', str(binary)],
        capture_output=True, text=True, timeout=25,
    )
    assert compiled.returncode == 0, compiled.stderr[-5000:]
    return binary


def command(kind: str, id: int | None = None, **fields: object) -> str:
    payload: dict[str, object] = dict(v=2, type=kind, boot=BOOT, session=SESSION)
    if id is not None:
        payload['id'] = id
    payload.update(fields)
    return json.dumps(payload, separators=(',', ':'))


def arm(id: int = 2, context: int = 1, **fields: object) -> str:
    params: dict[str, object] = dict(context=context, mode='stream', mask=[[19, '0000000e']], finish=[[19, '00000008']])
    params.update(fields)
    return command('SET_INPUT', id, **params)


def run(firmware: Path, *lines: str) -> list[dict[str, object]]:
    result = subprocess.run([str(firmware)], input='\n'.join(lines) + '\n',
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    frames = [json.loads(line) for line in result.stdout.splitlines()]
    assert all(len(line.encode()) <= 2048 for line in result.stdout.splitlines())
    return frames


def presses(frames: list[dict[str, object]]) -> list[dict[str, object]]:
    return [f for f in frames if f.get('type', f.get('event')) == 'press']


def click(row: int = 2) -> tuple[str, ...]:
    return (f'@contact 19 {row} 1', '@tick 30', f'@contact 19 {row} 0', '@tick 30')


def test_all_600_cells_masked_reads_and_checked_i2c(firmware: Path) -> None:
    result = subprocess.run([str(firmware), '--matrix'], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert '600 cells; masked bulk reads; checked I2C OK' in result.stdout


def test_stream_finish_and_hold_across_contexts(firmware: Path) -> None:
    frames = run(firmware, command('HELLO', 1), arm(), '@tick 30', *click(),
                 command('ACK', context=1, seq=1), *click(), command('ACK', context=1, seq=2),
                 '@contact 19 3 1', '@tick 30', command('ACK', context=1, seq=3),
                 *click(), arm(3, 2), '@tick 40', '@contact 19 3 0', '@tick 30', *click())
    assert [(f['context'], f['seq'], f['row'], f['final']) for f in presses(frames)] == [
        (1, 1, 2, False), (1, 2, 2, False), (1, 3, 3, True), (2, 1, 2, False)]


def test_single_empty_full_and_inactive_fields(firmware: Path) -> None:
    frames = run(firmware, command('HELLO', 1), '@contact 0 0 1', '@contact 19 7 1',
                 arm(mode='single', finish=[]), '@tick 30', *click(), *click(),
                 arm(3, 2, mask=[], finish=[]), '@tick 30', *click(),
                 arm(4, 3, mask=[[c, '3fffffff'] for c in range(20)], finish=[]),
                 '@contact 0 0 0', '@contact 19 7 0', '@tick 30', *click())
    assert [(f['context'], f['final']) for f in presses(frames)] == [(1, True), (3, False)]
    assert any(f.get('type') == 'input_set' and f.get('context') == 2 and f['state'] == 'idle' for f in frames)


def test_bounce_multitouch_and_held_input(firmware: Path) -> None:
    frames = run(firmware, command('HELLO', 1), '@contact 19 2 1', arm(), '@tick 40',
                 '@contact 19 2 0', '@tick 30', '@contact 19 2 1', '@tick 10',
                 '@contact 19 2 0', '@tick 30', '@contact 19 1 1', '@contact 19 2 1',
                 '@tick 40', '@contact 19 1 0', '@tick 40', '@contact 19 2 0', '@tick 30', *click())
    assert len(presses(frames)) == 1


def test_retries_deduplicate_and_stale_stop_cannot_stop_new_context(firmware: Path) -> None:
    first = arm()
    frames = run(firmware, command('HELLO', 1), first, '@tick 30', *click(),
                 '@tick 250', command('ACK', context=1, seq=1), command('ACK', context=1, seq=1),
                 first, *click(), command('ACK', context=1, seq=2), arm(3, 2), '@tick 30',
                 command('STOP', 4, context=1), command('STOP', 2, context=1),
                 command('ACK', context=1, seq=1), *click())
    observed = presses(frames)
    assert [(f['context'], f['seq']) for f in observed] == [(1, 1), (1, 1), (1, 2), (2, 1)]
    assert observed[0] == observed[1]
    assert any(f.get('code') == 'stale_context' for f in frames)
    assert any(f.get('code') == 'stale_request' for f in frames)


@pytest.mark.parametrize('bad', [
    {'mask': [[20, '00000001']]}, {'mask': [[19, '40000000']]},
    {'mask': [[19, '0000000e'], [19, '00000001']]},
    {'mask': [[19, '00000000']]}, {'finish': [[18, '00000001']]},
    {'mode': 'single', 'finish': [[19, '00000008']]}, {'mode': 'wrong'},
])
def test_bad_mask_stops_old_input(firmware: Path, bad: dict[str, object]) -> None:
    frames = run(firmware, command('HELLO', 1), arm(), '@tick 30', arm(3, 2, **bad), *click())
    assert not presses(frames)
    assert any(f.get('code') == 'invalid_mask' for f in frames)


@pytest.mark.parametrize('line', [
    'NOTPING', 'S C A N', '{"v":2,"v":2}', '{"v":true}', '{"v":2.0}',
    '{"v":4294967296}', '{"v":02}', '{"v":2}SCAN', '{"v":2,}',
    '{"v":2,"x":"\\u0053CAN"}', 'X' * 2049 + 'SCAN',
])
def test_strict_parser_and_overflow_tail(firmware: Path, line: str) -> None:
    frames = run(firmware, line, '@tick 30', *click())
    assert not presses(frames)
    assert any(f.get('type') == 'error' for f in frames)
    assert not any(f.get('event') in {'armed', 'pong'} for f in frames)


def test_incomplete_line_discards_tail_until_lf(firmware: Path) -> None:
    frames = run(firmware, '@bytes {"v":', '@tick 1001', command('HELLO', 1),
                 command('HELLO', 1), arm(), '@tick 30', *click())
    assert len(presses(frames)) == 1
    assert presses(frames)[0]['v'] == 2


def test_plain_legacy_commands_are_rejected(firmware: Path) -> None:
    frames = run(firmware, 'SCAN', 'ARM', 'STOP', 'CANCEL', 'STATUS', '@tick 30', *click(),
                 command('HELLO', 1), arm(), '@tick 30', 'STOP', *click())
    assert len(presses(frames)) == 1
    assert not any(f.get('protocol') == 'board_scan_usb_v1' for f in frames)


def test_heartbeat_player_silence_and_host_disconnect(firmware: Path) -> None:
    heartbeats = [line for i in range(3, 34) for line in ('@tick 1000', command('PING', i))]
    frames = run(firmware, command('HELLO', 1), arm(), *heartbeats, *click(),
                 command('ACK', context=1, seq=1), '@tick 5001', *click())
    assert len(presses(frames)) == 1
    assert any(f.get('code') == 'host_timeout' for f in frames)
    assert len([f for f in frames if f.get('type') == 'status']) >= 30


def test_ack_timeout_and_blocked_output_stop_input(firmware: Path) -> None:
    frames = run(firmware, command('HELLO', 1), arm(), '@tick 30', *click(), '@tick 2001',
                 command('PING', 3), *click())
    assert any(f.get('code') == 'ack_timeout' for f in frames)
    assert {f['seq'] for f in presses(frames)} == {1}
    blocked = run(firmware, command('HELLO', 1), arm(), '@tick 30', '@block', *click(),
                  '@tick 2001', '@unblock', command('PING', 3))
    assert blocked[-1]['fault'] == 'ack_timeout'
    assert not presses(blocked)


def test_i2c_fault_requires_reinitialization_and_new_session(firmware: Path) -> None:
    frames = run(firmware, command('HELLO', 1), arm(), '@tick 30', '@short_read', '@tick 1',
                 '@recover', arm(3, 2), *click(),
                 command('HELLO', 1, session='c000000000000001'),
                 arm(2, 1).replace(SESSION, 'c000000000000001'), '@tick 30', *click())
    assert any(f.get('code') == 'i2c_error' for f in frames)
    assert any(f.get('code') == 'not_ready' for f in frames)
    assert len(presses(frames)) == 1
    assert presses(frames)[0]['session'] == 'c000000000000001'


def test_millis_wrap_preserves_debounce(firmware: Path) -> None:
    frames = run(firmware, '@time 4294967270', command('HELLO', 1), arm(), '@tick 30', *click())
    assert len(presses(frames)) == 1


def test_command_conflict_wrong_boot_and_old_session_leave_input_armed(firmware: Path) -> None:
    frames = run(firmware, command('HELLO', 1), arm(), '@tick 30', arm(mode='single', finish=[]),
                 command('STOP', 3, context=1, boot='0000000000000000'),
                 command('STOP', 3, context=1, session='0000000000000000'), *click())
    assert len(presses(frames)) == 1
    assert presses(frames)[0]['final'] is False
    assert any(f.get('code') == 'id_conflict' for f in frames)


def test_event_queue_overflow_is_explicit(firmware: Path) -> None:
    clicks = [line for _ in range(33) for line in click()]
    frames = run(firmware, command('HELLO', 1), arm(), '@tick 30', *clicks, command('PING', 3))
    assert any(f.get('code') == 'event_overflow' for f in frames)
    assert frames[-1]['state'] == 'fault'
    assert {f['seq'] for f in presses(frames)} == set(range(1, 33))


def test_lost_input_confirmation_precedes_ready_and_press(firmware: Path) -> None:
    frames = run(firmware, command('HELLO', 1), '@block', arm(), '@tick 30', '@unblock',
                 '@tick 30', *click())
    types = [f.get('type') for f in frames]
    assert types.index('input_set') < types.index('input_ready') < types.index('press')


def test_stopped_context_and_session_takeover_discard_pending_events(firmware: Path) -> None:
    new_session = 'c000000000000001'
    frames = run(firmware, command('HELLO', 1), arm(), '@tick 30', *click(),
                 command('STOP', 3, context=1), command('STOP', 3, context=1), '@tick 300',
                 arm(4, 2), '@tick 30', *click(), command('HELLO', 1, session=new_session),
                 '@tick 300', *click())
    assert [(f['context'], f['seq']) for f in presses(frames)] == [(1, 1), (2, 1)]
    assert len([f for f in frames if f.get('type') == 'stopped']) == 2


def test_maximum_masks_and_bad_ack(firmware: Path) -> None:
    full = [[c, '3fffffff'] for c in range(20)]
    frames = run(firmware, command('HELLO', 1), arm(mask=full, finish=full), '@tick 30',
                 command('ACK', context=1, seq=1), *click())
    assert any(f.get('code') == 'invalid_ack' for f in frames)
    assert len(presses(frames)) == 1 and presses(frames)[0]['final'] is True


def test_frame_recovery_crlf_nul_and_token_depth(firmware: Path) -> None:
    frames = run(firmware, 'SCAN\x00SCAN', '{"a":[[[[0]]]]}', '@tick 30', *click(),
                 command('HELLO', 1) + '\r', arm() + '\r', '@tick 30', *click())
    assert len(presses(frames)) == 1
    assert presses(frames)[0].get('v') == 2


def test_probe_consumes_press_after_command_reply_and_deduplicates() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location('board_v2_probe', FIRMWARE / 'protocol_v2_probe.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Port:
        in_waiting = 0

        def __init__(self) -> None:
            self.sent: list[dict[str, object]] = []

        def write(self, data: bytes) -> int:
            self.sent.append(json.loads(data))
            return len(data)

        def read(self, size: int = 1) -> bytes:
            return b''

    port = Port()
    probe = module.Probe(port, full=False)
    probe.boot = BOOT
    probe.session = SESSION
    event = dict(v=2, type='press', boot=BOOT, session=SESSION, context=1,
                 seq=1, col=19, row=2, final=False)
    probe.read_frames = lambda: [dict(v=2, type='status', boot=BOOT, session=SESSION, id=1), event, event]
    probe.command('PING')
    assert probe.value == 11 and probe.seq == 1
    assert [f['type'] for f in port.sent] == ['PING', 'ACK', 'ACK']
    probe.event(dict(event, seq=3))
    assert probe.seq == 1  # Missing sequence 2 cannot be skipped.


def test_mutated_frames_do_not_crash_or_prevent_new_session(firmware: Path) -> None:
    import random

    randomizer = random.Random(42)
    base = arm(mask=[[c, '3fffffff'] for c in range(20)], finish=[])
    mutated = []
    for _ in range(400):
        text = base
        for _ in range(randomizer.randint(1, 4)):
            at = randomizer.randrange(len(text))
            text = text[:at] + randomizer.choice(['', '{', ']', '"', ',', ':', '\x00', '9', '\\']) + text[at + 1:]
        mutated.append(text)
    frames = run(firmware, command('HELLO', 1), *mutated,
                 command('HELLO', 1, session='c000000000000001'),
                 arm().replace(SESSION, 'c000000000000001'), '@tick 30', *click())
    assert len(presses(frames)) == 1


def test_exact_frame_limit_includes_optional_crlf(firmware: Path) -> None:
    line = arm()
    padded = line + ' ' * (2048 - len(line)) + '\r'
    frames = run(firmware, command('HELLO', 1), padded, '@tick 30', *click())
    assert len(presses(frames)) == 1
    assert not any(f.get('code') == 'frame_too_long' for f in frames)


def test_malformed_stale_context_cannot_cancel_current_input(firmware: Path) -> None:
    stale = json.loads(arm(4, 1))
    stale['extra'] = 1
    frames = run(firmware, command('HELLO', 1), arm(), arm(3, 2), '@tick 30',
                 json.dumps(stale), *click())
    assert len(presses(frames)) == 1 and presses(frames)[0]['context'] == 2

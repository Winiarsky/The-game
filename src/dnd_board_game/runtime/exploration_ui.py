from __future__ import annotations

import argparse
import os

from dnd_board_game.llm import GeminiGmClassifierClient, GeminiNpcInteractionClient, GroqGmClassifierClient, GroqNpcInteractionClient
from dnd_board_game.ui.exploration_app import ExplorationUiSession, create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lokalne GUI do testowania eksploracji i LLM.")
    parser.add_argument("--scenario", default="content/scenarios/abandoned_watchtower.json")
    parser.add_argument("--gm-classifier", choices=("none", "groq", "gemini"), default="gemini")
    parser.add_argument("--groq-model", default=None)
    parser.add_argument("--gemini-model", default=None)
    parser.add_argument("--board-backend", choices=("none", "simulator", "hardware"), default="none")
    parser.add_argument("--board-url", default="http://127.0.0.1:5000")
    parser.add_argument("--board-serial-port", default="")
    parser.add_argument("--wled-url", default="")
    parser.add_argument("--scan-timeout", type=float, default=30.0)
    debug_target = parser.add_mutually_exclusive_group()
    debug_target.add_argument("--debug-point", default="")
    debug_target.add_argument("--debug-challenge", default="")
    debug_target.add_argument("--debug-courtyard-entry", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5200)
    parser.add_argument("--debug", action="store_true", default=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    gm_client, npc_client = _create_clients(args)
    session = ExplorationUiSession(
        args.scenario,
        gm_client=gm_client,
        npc_client=npc_client,
        debug_point_id=args.debug_point or None,
        debug_challenge_id=args.debug_challenge or None,
        debug_courtyard_entry=args.debug_courtyard_entry,
    )
    if args.board_backend != "none":
        session.configure_board(
            backend=args.board_backend,
            board_url=args.board_url,
            board_serial_port=args.board_serial_port,
            wled_url=args.wled_url,
            scan_timeout_s=args.scan_timeout,
        )
    app = create_app(session)
    print(f"Exploration UI: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


def _create_clients(args: argparse.Namespace):
    if args.gm_classifier == "none":
        return None, None
    if args.gm_classifier == "groq":
        return GroqGmClassifierClient(model=args.groq_model), GroqNpcInteractionClient(model=args.groq_model)
    if args.gm_classifier == "gemini":
        return (
            GeminiGmClassifierClient(model=args.gemini_model or os.environ.get("GEMINI_MODEL")),
            GeminiNpcInteractionClient(model=args.gemini_model or os.environ.get("GEMINI_MODEL")),
        )
    raise ValueError(f"Unknown gm-classifier: {args.gm_classifier}")


if __name__ == "__main__":
    raise SystemExit(main())

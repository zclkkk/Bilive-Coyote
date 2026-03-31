from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from .client import DGLabAPIError, DGLabClient


DEFAULT_BASE_URL = "http://127.0.0.1:8920"
DEFAULT_CONFIG_PATH = Path("config.json")


def load_config() -> Dict[str, Any]:
    if not DEFAULT_CONFIG_PATH.exists():
        return {}
    return json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))


def build_client(args: argparse.Namespace) -> DGLabClient:
    config = load_config()
    return DGLabClient(
        base_url=args.base_url or config.get("base_url") or DEFAULT_BASE_URL,
        client_id=config.get("client_id") or None,
        token=args.token or config.get("token") or None,
        timeout=float(args.timeout if args.timeout is not None else config.get("timeout", 10)),
    )


def print_json(data: Dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DG-Lab Coyote Game Hub CLI")
    parser.add_argument("--base-url", help=f"API base URL, default: {DEFAULT_BASE_URL}")
    parser.add_argument("--token", help="Optional Bearer token")
    parser.add_argument("--timeout", type=float, help="HTTP timeout in seconds")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("server-info", help="Get server info")
    subparsers.add_parser("game-api-info", help="Get game API info")
    subparsers.add_parser("game-info", help="Get game info for the specified client")
    subparsers.add_parser("strength-info", help="Get strength config for the specified client")
    p_strength = subparsers.add_parser("strength", help="Change strength")
    p_strength.add_argument("--target", choices=["base", "random"], required=True, help="Strength target")
    p_strength.add_argument("--action", choices=["add", "sub", "set"], required=True, help="Strength action")
    p_strength.add_argument("--value", type=float, required=True, help="Strength value")

    p_fire = subparsers.add_parser("fire", help="Trigger fire action")
    p_fire.add_argument("--strength", type=int, required=True, help="Fire strength")
    p_fire.add_argument("--time-ms", type=int, help="Duration in milliseconds")
    p_fire.add_argument("--override", action="store_true", help="Override current fire action")
    p_fire.add_argument("--pulse-id", help="Optional pulse ID")

    return parser


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    client = build_client(args)

    try:
        if args.command == "server-info":
            print_json(client.get_server_info())
        elif args.command == "game-api-info":
            print_json(client.get_game_api_info())
        elif args.command == "game-info":
            print_json(client.get_game_info())
        elif args.command == "strength-info":
            print_json(client.get_strength_config())
        elif args.command == "strength":
            print_json(client.change_strength(target=args.target, action=args.action, value=args.value))
        elif args.command == "fire":
            print_json(
                client.fire(
                    strength=args.strength,
                    time_ms=args.time_ms,
                    override=args.override,
                    pulse_id=args.pulse_id,
                )
            )
        else:
            parser.error(f"Unknown command: {args.command}")
        return 0
    except (DGLabAPIError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

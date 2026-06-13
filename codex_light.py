from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from codex_notifier import notify_status


APP_DIR = Path(__file__).resolve().parent
STATE_FILE = APP_DIR / "codex_status.json"

STATE_MAP = {
    "working": ("working", "Codex 正在工作"),
    "waiting": ("decision", "Codex 正在等待你确认"),
    "done": ("done", "本轮任务已完成"),
    "idle": ("idle", "Codex 待命"),
    "quit": ("idle", "Codex 待命"),
}


def write_state(command: str) -> None:
    status, message = STATE_MAP[command]
    payload = {
        "status": status,
        "message": message,
        "updated_at": int(time.time()),
        "source": "command",
        "event": f"codex-light {command}",
    }
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    notify_status(payload)


def read_state() -> str:
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "idle"
    status = payload.get("status")
    if status == "decision":
        return "waiting"
    if status in {"working", "done", "idle"}:
        return str(status)
    return "idle"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Control the Codex dynamic island status")
    parser.add_argument("command", choices=[*STATE_MAP.keys(), "status"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "status":
        print(read_state())
        return 0
    write_state(args.command)
    print(args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

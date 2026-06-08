from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[2]
STATE_FILE = PROJECT_DIR / "codex_status.json"
LOG_FILE = PROJECT_DIR / "codex_status_hook.log"

STATUS_BY_EVENT = {
    "SessionStart": ("idle", "Codex 会话已启动"),
    "UserPromptSubmit": ("working", "Codex 已收到你的任务"),
    "PreToolUse": ("working", "Codex 正在调用工具"),
    "PermissionRequest": ("decision", "Codex 正在等待你确认"),
    "PostToolUse": ("working", "Codex 正在处理工具结果"),
    "SubagentStart": ("working", "Codex 子任务开始"),
    "SubagentStop": ("working", "Codex 子任务结束"),
    "Stop": ("done", "本轮任务已完成"),
    "SessionEnd": ("done", "Codex 会话已结束"),
}

WAITING_PATTERNS = [
    r"等你",
    r"需要你",
    r"需要.*?(回复|确认|授权|登录|验证码|文件|截图|选择|提供|补充)",
    r"请.*?(回复|确认|授权|登录|提供|发我|补充|选择)",
    r"你.*?(确认|选择|提供|发我|补充).*?吗",
    r"要不要|可以吗|行不行|是否",
    r"我需要.*?(你|确认|授权|文件|截图|验证码)",
    r"blocked|waiting for user|permission|approval",
    r"\?",
    r"？",
]


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    return payload if isinstance(payload, dict) else {"payload": payload}


def looks_waiting(message: str) -> bool:
    if not message:
        return False
    return any(re.search(pattern, message, re.IGNORECASE | re.DOTALL) for pattern in WAITING_PATTERNS)


def write_state(payload: dict[str, Any]) -> None:
    event_name = str(
        payload.get("hook_event_name")
        or payload.get("hookEventName")
        or (sys.argv[1] if len(sys.argv) > 1 else "")
    ).strip()
    status, message = STATUS_BY_EVENT.get(event_name, ("working", f"Codex 事件：{event_name or '未知'}"))
    last_message = str(payload.get("last_assistant_message") or "")

    # 如果停止事件后的最后回复明显在等用户，保持红灯。
    if event_name in {"Stop", "SubagentStop"} and looks_waiting(last_message):
        status = "decision"
        message = "Codex 正在等待你确认"

    state = {
        "status": status,
        "message": message,
        "updated_at": int(time.time()),
        "source": "hook",
        "event": event_name,
        "session_id": payload.get("session_id") or payload.get("sessionId"),
        "turn_id": payload.get("turn_id") or payload.get("turnId"),
        "tool_name": payload.get("tool_name") or payload.get("toolName"),
    }
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    write_log(f"{event_name or 'Unknown'} -> {status}")


def write_log(message: str) -> None:
    try:
        with LOG_FILE.open("a", encoding="utf-8") as file:
            file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except OSError:
        pass


def main() -> int:
    payload = read_payload()
    try:
        write_state(payload)
    except OSError:
        pass

    print(json.dumps({"continue": True, "suppressOutput": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import msvcrt
import subprocess
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parent
CONFIG_FILE = APP_DIR / "notification_config.json"
STATE_FILE = APP_DIR / "notification_state.json"
LOCK_FILE = APP_DIR / "notification_state.lock"
LOG_FILE = APP_DIR / "codex_notification.log"

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "provider": "kdeconnect",
    "kdeconnect": {
        "cli_path": "kdeconnect-cli",
        "device_id": "",
    },
    "pushplus": {
        "token": "",
        "endpoint": "https://www.pushplus.plus/send",
        "template": "markdown",
        "channel": "wechat",
    },
    "events": {
        "decision": True,
        "done": True,
        "working": False,
        "idle": False,
    },
    "min_interval_seconds": 20,
    "include_context": True,
}

STATUS_TITLES = {
    "working": "Codex 正在工作",
    "decision": "Codex 等待你确认",
    "done": "Codex 任务已完成",
    "idle": "Codex 待命",
}


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(default)
    if not isinstance(value, dict):
        return dict(default)
    return merge_dict(default, value)


def merge_dict(default: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    merged = dict(default)
    for key, item in value.items():
        if isinstance(item, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dict(merged[key], item)
        else:
            merged[key] = item
    return merged


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_log(message: str) -> None:
    try:
        with LOG_FILE.open("a", encoding="utf-8") as file:
            file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except OSError:
        pass


def notify_status(state: dict[str, Any]) -> None:
    config = load_json(CONFIG_FILE, DEFAULT_CONFIG)
    if not config.get("enabled"):
        return
    provider = str(config.get("provider", "kdeconnect")).lower()
    if provider not in {"kdeconnect", "pushplus"}:
        write_log("skip: unsupported provider")
        return

    status = str(state.get("status") or "idle")
    events = config.get("events") if isinstance(config.get("events"), dict) else {}
    if not events.get(status, False):
        return

    if provider == "pushplus":
        pushplus = config.get("pushplus") if isinstance(config.get("pushplus"), dict) else {}
        token = str(pushplus.get("token") or "").strip()
        if not token:
            write_log("skip: missing pushplus token")
            return

    with notification_lock():
        notify_state = load_json(STATE_FILE, {})
        event_key = build_event_key(state)
        now = int(time.time())
        last_sent_at = int(notify_state.get("last_sent_at") or 0)
        min_interval = max(0, int(config.get("min_interval_seconds") or 0))
        if notify_state.get("last_event_key") == event_key:
            return
        if min_interval and now - last_sent_at < min_interval:
            return

        try:
            if provider == "kdeconnect":
                send_kdeconnect(config, state)
            else:
                send_pushplus(config, state)
        except (OSError, subprocess.SubprocessError, urllib.error.URLError, TimeoutError) as exc:
            write_log(f"send failed: {exc}")
            return

        save_json(STATE_FILE, {"last_event_key": event_key, "last_sent_at": now, "last_status": status})
        write_log(f"sent: {status} {state.get('event') or ''}".strip())


@contextmanager
def notification_lock():
    LOCK_FILE.touch(exist_ok=True)
    with LOCK_FILE.open("r+b") as lock_file:
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)


def is_notification_enabled() -> bool:
    config = load_json(CONFIG_FILE, DEFAULT_CONFIG)
    return bool(config.get("enabled"))


def set_notification_enabled(enabled: bool) -> None:
    config = load_json(CONFIG_FILE, DEFAULT_CONFIG)
    config["enabled"] = bool(enabled)
    save_json(CONFIG_FILE, config)


def build_event_key(state: dict[str, Any]) -> str:
    parts = [
        state.get("session_id"),
        state.get("turn_id"),
        state.get("event"),
        state.get("status"),
        state.get("tool_name"),
        state.get("message"),
    ]
    return "|".join(str(part or "") for part in parts)


def send_pushplus(config: dict[str, Any], state: dict[str, Any]) -> None:
    pushplus = config.get("pushplus") if isinstance(config.get("pushplus"), dict) else {}
    endpoint = str(pushplus.get("endpoint") or DEFAULT_CONFIG["pushplus"]["endpoint"])
    payload = {
        "token": str(pushplus.get("token") or ""),
        "title": build_title(state),
        "content": build_content(state, bool(config.get("include_context", True))),
        "template": str(pushplus.get("template") or "markdown"),
        "channel": str(pushplus.get("channel") or "wechat"),
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        body = response.read().decode("utf-8", errors="replace")
    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        result = {}
    if isinstance(result, dict):
        code = result.get("code")
        if code not in (None, 200):
            raise OSError(f"PushPlus returned code={code}, message={result.get('msg') or result.get('message')}")


def send_kdeconnect(config: dict[str, Any], state: dict[str, Any]) -> None:
    kdeconnect = config.get("kdeconnect") if isinstance(config.get("kdeconnect"), dict) else {}
    cli_path = str(kdeconnect.get("cli_path") or "kdeconnect-cli")
    device_id = str(kdeconnect.get("device_id") or "").strip()
    message = f"{build_title(state)}\n{plain_text_content(state)}"
    command = [cli_path]
    if device_id:
        command.extend(["--device", device_id])
    command.extend(["--ping-msg", message])
    completed = subprocess.run(command, capture_output=True, text=True, timeout=8, check=False)
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "kdeconnect-cli failed").strip()
        raise OSError(error)


def build_title(state: dict[str, Any]) -> str:
    status = str(state.get("status") or "idle")
    return STATUS_TITLES.get(status, "Codex 状态更新")


def build_content(state: dict[str, Any], include_context: bool) -> str:
    status = str(state.get("status") or "idle")
    message = str(state.get("message") or STATUS_TITLES.get(status, "Codex 状态更新"))
    lines = [message]
    if include_context:
        event = str(state.get("event") or "").strip()
        tool_name = str(state.get("tool_name") or "").strip()
        source = str(state.get("source") or "").strip()
        if event:
            lines.append(f"- 事件：{event}")
        if tool_name:
            lines.append(f"- 工具：{tool_name}")
        if source:
            lines.append(f"- 来源：{source}")
    return "\n\n".join(lines)


def plain_text_content(state: dict[str, Any]) -> str:
    lines = build_content(state, include_context=True).replace("\n\n", "\n").splitlines()
    return "\n".join(line[2:] if line.startswith("- ") else line for line in lines)

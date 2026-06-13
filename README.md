# Codex Dynamic Island Status Bar

一个 Windows 桌面悬浮状态栏，用灵动岛样式显示 Codex/AI 助手的当前状态。

状态颜色：

- 黄灯：正在工作
- 红灯：等待用户决策
- 绿灯：任务已完成
- 灰灯：待命
<img width="474" height="130" alt="image" src="https://github.com/user-attachments/assets/988b7768-ce8d-4f80-905f-6218c6048b42" />
<img width="211" height="75" alt="image" src="https://github.com/user-attachments/assets/2304d597-903d-4b6a-92a6-9268e3ec6483" />

## 功能

- PyQt5 原生窗口，无边框、透明背景、可拖动
- 自绘抗锯齿胶囊和圆形呼吸灯
- 双击展开/折叠
- 右键切换置顶/普通
- 拖到屏幕边缘自动吸附
- 命令行更新状态，适合配合 Codex skill、bat、hook 或其它自动化脚本使用

## 环境要求

- Windows
- Python 3.10+
- PyQt5

安装依赖：

```powershell
pip install -r requirements.txt
```

如果你使用 conda：

```powershell
conda create -n codex-island python=3.10
conda activate codex-island
pip install -r requirements.txt
```

## 启动

双击：

```text
start_dynamic_island.bat
```

或命令行运行：

```powershell
python codex_dynamic_island.py
```

## 更新状态

双击或命令行运行：

```powershell
codex-light.bat working
codex-light.bat waiting
codex-light.bat done
codex-light.bat idle
```

也可以直接用 Python：

```powershell
python codex_light.py working
python codex_light.py waiting
python codex_light.py done
python codex_light.py idle
python codex_light.py status
```

状态会写入当前目录下的 `codex_status.json`，灵动岛每 250ms 自动读取并刷新。

## Codex Hook 自动更新

项目内包含 hook 示例：

```text
.codex/hooks/codex_status_hook.py
.codex/config.example.toml
```

配置步骤：

1. 打开 `.codex/config.example.toml`
2. 把 `<PYTHON_EXE>` 改成你的 Python 路径，例如 `C:\Users\you\miniconda3\envs\codex-island\python.exe`
3. 把 `<PROJECT_DIR>` 改成这个项目的绝对路径
4. 把这些 hook 配置复制到你的 Codex 配置里
5. 在 Codex 里运行 `/hooks`
6. trust 这些 hook

hook 会自动写入 `codex_status.json`：

- `UserPromptSubmit` / `PreToolUse`：黄灯
- `PermissionRequest`：红灯
- `Stop`：绿灯
- 如果 `Stop` 时最后回复像是在等用户确认，会保持红灯

hook 适合自动更新；如果 hook 没有生效，可以继续使用下面的 skill 或 `codex-light.bat` 手动兜底。

## 手机通知

安卓手机在同一 WiFi 局域网内建议使用 KDE Connect。它不需要公网、不走微信、不收费，Windows 和安卓配对后即可通过局域网给手机发通知。项目已经在手动命令和 Codex hook 写入状态后接入通知逻辑，默认只在下面两个状态推送：

- `decision`：Codex 正在等待你确认
- `done`：本轮任务已完成

### KDE Connect 局域网通知

配置步骤：

1. Windows 和安卓手机都安装 KDE Connect
2. 确保电脑和手机在同一个 WiFi
3. 打开两端 KDE Connect，完成配对
4. 复制 `notification_config.example.json` 为 `notification_config.json`
5. 确认 `enabled` 为 `true`，`provider` 为 `kdeconnect`
6. 如果只配对了一台手机，`device_id` 可以留空；如果配对了多台设备，用下面命令查看设备 ID 后填入 `device_id`

```powershell
kdeconnect-cli --list-devices
```

如果 Windows 找不到 `kdeconnect-cli`，把 `kdeconnect.cli_path` 改成 `kdeconnect-cli.exe` 的完整路径。

配置示例：

```json
{
  "enabled": true,
  "provider": "kdeconnect",
  "kdeconnect": {
    "cli_path": "kdeconnect-cli",
    "device_id": ""
  },
  "events": {
    "decision": true,
    "done": true,
    "working": false,
    "idle": false
  },
  "min_interval_seconds": 20,
  "include_context": true
}
```

测试命令：

```powershell
kdeconnect-cli --ping-msg "Codex 测试通知"
```

KDE Connect 必须在电脑端后台运行。如果只是关闭主窗口但托盘仍在，通常可以继续发送；如果从托盘彻底退出 KDE Connect，消息就发不出去。

### PushPlus 备用方案

如果后续需要公网或微信通知，可以把 `provider` 改成 `pushplus`，并配置 token：

```json
{
  "enabled": true,
  "provider": "pushplus",
  "pushplus": {
    "token": "替换成你的 PushPlus token",
    "endpoint": "https://www.pushplus.plus/send",
    "template": "markdown",
    "channel": "wechat"
  },
  "events": {
    "decision": true,
    "done": true,
    "working": false,
    "idle": false
  },
  "min_interval_seconds": 20,
  "include_context": true
}
```

`working` 默认关闭，避免 Codex 高频调用工具时刷屏。通知发送记录会写入 `codex_notification.log`，最近一次通知去重信息会写入 `notification_state.json`。

## Codex Skill 手动兜底

项目内包含 skill 模板：

```text
.codex/skills/codex-status-light/SKILL.md
```

安装方式：

1. 把 `.codex/skills/codex-status-light` 复制到你的 Codex skills 目录
2. 编辑 `SKILL.md`，把 `<PROJECT_DIR>` 改成这个项目的绝对路径
3. 在 Codex 后续对话中要求使用 `codex-status-light` skill

推荐约定：

- 开始工作：`working`
- 需要你决策：`waiting`
- 任务完成：`done`
- 清空/待命：`idle`

skill 和 hook 可以同时存在：hook 负责自动更新，skill/command 负责 hook 不稳定时手动更新。

## 交互

- 拖动：移动位置
- 松手：靠近屏幕边缘时自动吸附
- 双击：展开/折叠
- 右键：切换置顶/普通
- 托盘右键菜单：显示窗口、切换任务栏图标、切换手机通知、退出
- `T`：切换置顶/普通
- `Esc` 或 `×`：关闭

## 文件说明

- `codex_dynamic_island.py`：灵动岛 UI 主程序
- `codex_light.py`：状态控制命令
- `codex_notifier.py`：手机通知发送逻辑
- `notification_config.example.json`：手机通知配置模板
- `.codex/hooks/codex_status_hook.py`：Codex hook 自动状态更新
- `.codex/skills/codex-status-light/SKILL.md`：Codex skill 手动状态更新说明
- `.codex/config.example.toml`：hook 配置示例
- `start_dynamic_island.bat`：Windows 启动脚本
- `codex-light.bat`：Windows 状态控制脚本
- `requirements.txt`：Python 依赖



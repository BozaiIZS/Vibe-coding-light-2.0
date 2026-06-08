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
- `T`：切换置顶/普通
- `Esc` 或 `×`：关闭

## 文件说明

- `codex_dynamic_island.py`：灵动岛 UI 主程序
- `codex_light.py`：状态控制命令
- `.codex/hooks/codex_status_hook.py`：Codex hook 自动状态更新
- `.codex/skills/codex-status-light/SKILL.md`：Codex skill 手动状态更新说明
- `.codex/config.example.toml`：hook 配置示例
- `start_dynamic_island.bat`：Windows 启动脚本
- `codex-light.bat`：Windows 状态控制脚本
- `requirements.txt`：Python 依赖

运行后会自动生成：

- `codex_status.json`：当前状态
- `dynamic_island_config.json`：窗口位置、置顶、展开状态

这两个文件是本地运行状态。

## GitHub 建议

建议添加 `.gitignore`：

```gitignore
__pycache__/
*.pyc
codex_status.json
dynamic_island_config.json
*.log
```

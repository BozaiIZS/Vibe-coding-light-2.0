---
name: codex-status-light
description: Use when the user wants to manually update the local Codex Dynamic Island status indicator. Use this skill at the start/end of tasks when visible status updates are useful, including working, waiting/decision, done, and idle states.
---

# Codex Status Light

Use the project-local status command to update the visible Codex Dynamic Island.

## Setup

Edit the commands below so `<PROJECT_DIR>` points to the cloned `灵动岛2.0` folder.

Example:

```powershell
<PROJECT_DIR>\codex-light.bat working
<PROJECT_DIR>\codex-light.bat waiting
<PROJECT_DIR>\codex-light.bat done
<PROJECT_DIR>\codex-light.bat idle
```

## Workflow

- Before non-trivial work, run `working`.
- If user input, confirmation, credentials, approval, missing files, or a decision is needed, run `waiting` before asking.
- After the requested task is complete and ready for review, run `done`.
- If explicitly asked to clear the indicator, run `idle`.

Hooks can update the status automatically, but this skill remains useful when hooks are unavailable, untrusted, or inaccurate.

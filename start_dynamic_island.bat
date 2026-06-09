@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "QT_PLUGIN_PATH="
set "QT_QPA_PLATFORM_PLUGIN_PATH="
start "" "D:\Anaconda\envs\py310_5070ti\pythonw.exe" "%~dp0codex_dynamic_island.py"

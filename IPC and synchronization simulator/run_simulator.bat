@echo off
echo Starting IPC & Synchronization Arcade...
py ipc_simulator.py
if %ERRORLEVEL% NEQ 0 (
    python ipc_simulator.py
)
pause

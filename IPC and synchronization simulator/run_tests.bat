@echo off
echo Running Automated Test Suite...
py -m unittest test_ipc_simulator.py -v
if %ERRORLEVEL% NEQ 0 (
    python -m unittest test_ipc_simulator.py -v
)
pause

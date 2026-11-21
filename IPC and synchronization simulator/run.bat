@echo off
title IPC ^& Synchronization Arcade Launcher
cd /d "%~dp0"

echo ===================================================
echo     IPC ^& SYNCHRONIZATION ARCADE (PAC-MAN)
echo ===================================================
echo.

:: 1. Check Python 3.14 explicit path
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    echo [OK] Launching with Python 3.14...
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" ipc_simulator.py
    if %ERRORLEVEL% neq 0 goto onerror
    goto end
)

:: 2. Check standard python in PATH
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Launching with system Python...
    python ipc_simulator.py
    if %ERRORLEVEL% neq 0 goto onerror
    goto end
)

:: 3. Check py launcher
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Launching with py launcher...
    py ipc_simulator.py
    if %ERRORLEVEL% neq 0 goto onerror
    goto end
)

:onerror
echo.
echo ===================================================
echo [!] The application stopped with error code %ERRORLEVEL%.
if exist crash_log.txt (
    echo [!] Details from crash_log.txt:
    type crash_log.txt
)
echo ===================================================
echo.
pause
exit /b %ERRORLEVEL%

:end

@echo off
REM ============================================================================
REM BGR User Management — Offboarding Scheduled Task
REM ============================================================================
REM This script runs the offboarding process for departing employees.
REM Runs on the day AFTER the exit date (Letzter Arbeitstag).
REM
REM Setup Instructions:
REM 1. In Task Scheduler, create a new task
REM 2. Action: Start a program
REM 3. Program: C:\Tasks\User-Management\run-offboarding.bat
REM 4. Working directory: C:\Tasks\User-Management
REM 5. Run as: Service account with AD/Exchange permissions
REM 6. Trigger: Daily at 08:00 (or your preferred time, after onboarding)
REM ============================================================================

setlocal enabledelayedexpansion

REM Get the script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check if activation was successful
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment at %SCRIPT_DIR%.venv
    echo [ERROR] Ensure Python is installed and venv exists: %SCRIPT_DIR%.venv
    exit /b 1
)

REM Load environment from .env (Python will handle this, but it's good to verify)
if not exist .env (
    echo [ERROR] .env file not found at %SCRIPT_DIR%.env
    echo [ERROR] Please copy .env.example to .env and fill in the required values
    exit /b 1
)

REM Ensure logs directory exists
if not exist logs (
    mkdir logs
)

REM Run the offboarding process
echo.
echo [INFO] Starting BGR Offboarding Process...
echo [INFO] Timestamp: %date% %time%
echo [INFO] Working Directory: %SCRIPT_DIR%
echo.

python main.py offboarding

REM Capture exit code
set EXIT_CODE=%errorlevel%

REM Log completion
if %EXIT_CODE% equ 0 (
    echo.
    echo [SUCCESS] Offboarding process completed successfully
    echo.
) else (
    echo.
    echo [ERROR] Offboarding process failed with exit code %EXIT_CODE%
    echo.
    exit /b %EXIT_CODE%
)

endlocal
exit /b 0

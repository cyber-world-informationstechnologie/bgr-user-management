@echo off
REM ============================================================================
REM BGR User Management — Onboarding Scheduled Task
REM ============================================================================
REM This script runs the onboarding process for new employees.
REM
REM Setup Instructions:
REM 1. In Task Scheduler, create a new task
REM 2. Action: Start a program
REM 3. Program: C:\Tasks\User-Management\run-onboarding.bat
REM 4. Working directory: C:\Tasks\User-Management
REM 5. Run as: Service account with AD/Exchange permissions
REM 6. Trigger: Daily at 06:00 (or your preferred time)
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

REM Run the onboarding process
echo.
echo [INFO] Starting BGR Onboarding Process...
echo [INFO] Timestamp: %date% %time%
echo [INFO] Working Directory: %SCRIPT_DIR%
echo.

python main.py onboarding

REM Capture exit code
set EXIT_CODE=%errorlevel%

REM Log completion
if %EXIT_CODE% equ 0 (
    echo.
    echo [SUCCESS] Onboarding process completed successfully
    echo.
) else (
    echo.
    echo [ERROR] Onboarding process failed with exit code %EXIT_CODE%
    echo.
    exit /b %EXIT_CODE%
)

endlocal
exit /b 0

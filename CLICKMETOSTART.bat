@echo off
setlocal EnableExtensions
title Statement Markup Tool (FOR DAD)

cd /d "%~dp0"

set "APP_DIR=%~dp0"
set "VENV_DIR=%APP_DIR%.venv"
set "SHORTCUT_SCRIPT=%APP_DIR%tools\Create-BrandedShortcut.ps1"
set "PYTHON_CMD="

if exist "%SHORTCUT_SCRIPT%" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SHORTCUT_SCRIPT%" -AppDir "%APP_DIR%" >nul 2>nul
)

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    echo Python was not found. Trying to install Python automatically for this user...
    where winget >nul 2>nul
    if not %errorlevel%==0 (
        echo.
        echo Windows App Installer / winget was not found, so Python cannot be installed automatically.
        echo Please install Python from https://www.python.org/downloads/windows/ and run this file again.
        echo.
        pause
        exit /b 1
    )

    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    if not %errorlevel%==0 (
        echo.
        echo Python installation did not complete successfully.
        echo Please install Python from https://www.python.org/downloads/windows/ and run this file again.
        echo.
        pause
        exit /b 1
    )

    set "PYTHON_CMD=py -3"
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating the private app environment...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if not %errorlevel%==0 (
        echo.
        echo Could not create the private app environment.
        pause
        exit /b 1
    )
)

echo Installing or updating app dependencies...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV_DIR%\Scripts\python.exe" -m pip install -r "%APP_DIR%requirements.txt"
if not %errorlevel%==0 (
    echo.
    echo Dependency installation failed. Check your internet connection and try again.
    pause
    exit /b 1
)

echo Starting Statement Markup Tool (FOR DAD)...
if exist "%VENV_DIR%\Scripts\pythonw.exe" (
    start "" "%VENV_DIR%\Scripts\pythonw.exe" "%APP_DIR%app\cost_markup_tool.py"
) else (
    start "" "%VENV_DIR%\Scripts\python.exe" "%APP_DIR%app\cost_markup_tool.py"
)

endlocal

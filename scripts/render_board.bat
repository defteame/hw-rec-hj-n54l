@echo off
REM Render PCB board using KiCad Analyzer
REM Usage: render_board.bat [pcb_file] [width]

setlocal

REM Get project root (parent of scripts directory)
pushd "%~dp0.."
set "PROJECT_ROOT=%CD%"
popd

set "VENV_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"
set "DEFAULT_PCB=%PROJECT_ROOT%\layouts\main\main.kicad_pcb"
set "DEFAULT_WIDTH=3840"
set "SCRIPT_DIR=%~dp0"

if "%~1"=="" (set "PCB_FILE=%DEFAULT_PCB%") else (set "PCB_FILE=%~1")
if "%~2"=="" (set "WIDTH=%DEFAULT_WIDTH%") else (set "WIDTH=%~2")

echo ========================================
echo KiCad PCB Render Script
echo ========================================
echo.

REM Check for Inkscape
echo Checking for Inkscape...
where inkscape >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :inkscape_found
if exist "C:\Program Files\Inkscape\bin\inkscape.exe" goto :inkscape_found
if exist "%LOCALAPPDATA%\Programs\Inkscape\bin\inkscape.exe" goto :inkscape_found

echo ERROR: Inkscape not found!
echo Install with: winget install Inkscape.Inkscape
exit /b 1

:inkscape_found
echo Inkscape found.
echo.

REM Check for Python venv
echo Checking Python...
if not exist "%VENV_PYTHON%" (
    echo ERROR: Python venv not found: %VENV_PYTHON%
    exit /b 1
)
echo Python found.
echo.

REM Check for PCB file
echo Checking PCB file...
if not exist "%PCB_FILE%" (
    echo ERROR: PCB file not found: %PCB_FILE%
    exit /b 1
)
echo PCB file found.
echo.

echo Rendering: %PCB_FILE%
echo Resolution: %WIDTH%px
echo.

cd /d "%SCRIPT_DIR%"
"%VENV_PYTHON%" kicad-analyzer.py render all --pcb "%PCB_FILE%" --format png --width %WIDTH%

echo.
echo Done!
endlocal

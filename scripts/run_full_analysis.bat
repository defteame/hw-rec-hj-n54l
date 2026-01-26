@echo off
REM Full KiCad PCB Analysis Script (Windows)
REM Runs: DRC, 2D Renders, 3D Renders
REM Usage: run_full_analysis.bat [pcb_file] [width]

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
echo KiCad Full Analysis Script
echo ========================================
echo.

REM Check for KiCad CLI
echo Checking for KiCad CLI...
where kicad-cli >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :kicad_found
if exist "%LOCALAPPDATA%\Programs\KiCad\9.0\bin\kicad-cli.exe" goto :kicad_found
if exist "%LOCALAPPDATA%\Programs\KiCad\8.0\bin\kicad-cli.exe" goto :kicad_found
if exist "C:\Program Files\KiCad\9.0\bin\kicad-cli.exe" goto :kicad_found
if exist "C:\Program Files\KiCad\8.0\bin\kicad-cli.exe" goto :kicad_found

echo ERROR: KiCad CLI not found!
echo Install KiCad 8.0+ from https://www.kicad.org/
exit /b 1

:kicad_found
echo KiCad CLI found.
echo.

REM Check for Inkscape (for PNG conversion)
echo Checking for Inkscape...
where inkscape >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :inkscape_found
if exist "C:\Program Files\Inkscape\bin\inkscape.exe" goto :inkscape_found
if exist "%LOCALAPPDATA%\Programs\Inkscape\bin\inkscape.exe" goto :inkscape_found

echo WARNING: Inkscape not found - PNG conversion may fail
echo Install with: winget install Inkscape.Inkscape
echo.
goto :check_python

:inkscape_found
echo Inkscape found.
echo.

:check_python
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

echo Analysis Target: %PCB_FILE%
echo Render Resolution: %WIDTH%px
echo.

cd /d "%SCRIPT_DIR%"

echo Running full analysis (DRC + Renders)...
echo.
"%VENV_PYTHON%" kicad-analyzer.py full run --pcb "%PCB_FILE%" --format png --width %WIDTH%
set "EXIT_CODE=%ERRORLEVEL%"

if %EXIT_CODE% NEQ 0 (
    echo.
    echo WARNING: Analysis completed with DRC errors
)

echo.
echo ========================================
echo Analysis Complete!
echo ========================================
echo.
echo Output location: %PROJECT_ROOT%\build\kicad_analyzer\
echo.
echo Run 'kicad-analyzer latest' to see the latest results.
echo.

endlocal

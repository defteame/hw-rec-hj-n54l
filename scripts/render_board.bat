@echo off
REM Render PCB board using KiCad Analyzer
REM Usage: render_board.bat [pcb_file] [width]
REM   pcb_file: Path to .kicad_pcb file (default: layouts\main\main.kicad_pcb)
REM   width:    Image width in pixels (default: 3840 for 4K)
REM
REM Output structure:
REM   build\renders\<iso timestamp>\
REM     - 3d\   - 3D renders (PNG)
REM     - svg\  - SVG exports
REM     - png\  - PNGs converted from SVGs
REM
REM Requires: KiCad CLI (8.0+) and Inkscape for PNG conversion

setlocal enabledelayedexpansion

cd /d "%~dp0"

set VENV_PYTHON=%~dp0..\.venv\Scripts\python.exe
set DEFAULT_PCB=%~dp0..\layouts\main\main.kicad_pcb
set DEFAULT_WIDTH=3840

set PCB_FILE=%1
set WIDTH=%2

if "%PCB_FILE%"=="" (
    set PCB_FILE=%DEFAULT_PCB%
)

if "%WIDTH%"=="" (
    set WIDTH=%DEFAULT_WIDTH%
)

echo ========================================
echo KiCad PCB Render Script
echo ========================================
echo.

REM Check for Inkscape
echo Checking for Inkscape...
set INKSCAPE_FOUND=0

REM Check if inkscape is in PATH
where inkscape >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "delims=" %%i in ('where inkscape') do (
        echo Inkscape found: %%i
        set INKSCAPE_FOUND=1
        goto :inkscape_checked
    )
)

REM Check standard installation paths
if exist "C:\Program Files\Inkscape\bin\inkscape.exe" (
    echo Inkscape found: C:\Program Files\Inkscape\bin\inkscape.exe
    set INKSCAPE_FOUND=1
    goto :inkscape_checked
)

if exist "C:\Program Files (x86)\Inkscape\bin\inkscape.exe" (
    echo Inkscape found: C:\Program Files ^(x86^)\Inkscape\bin\inkscape.exe
    set INKSCAPE_FOUND=1
    goto :inkscape_checked
)

if exist "%LOCALAPPDATA%\Programs\Inkscape\bin\inkscape.exe" (
    echo Inkscape found: %LOCALAPPDATA%\Programs\Inkscape\bin\inkscape.exe
    set INKSCAPE_FOUND=1
    goto :inkscape_checked
)

:inkscape_checked
if %INKSCAPE_FOUND% EQU 0 (
    echo.
    echo ERROR: Inkscape not found!
    echo.
    echo Inkscape is required for converting SVG renders to PNG.
    echo.
    echo To install Inkscape:
    echo   winget install Inkscape.Inkscape
    echo.
    echo Or download from: https://inkscape.org/release/
    echo.
    echo After installation, re-run this script.
    exit /b 1
)
echo.

REM Check for Python venv
if not exist "%VENV_PYTHON%" (
    echo ERROR: Python virtual environment not found at: %VENV_PYTHON%
    echo Please create and activate the virtual environment first.
    exit /b 1
)

REM Check for PCB file
if not exist "%PCB_FILE%" (
    echo ERROR: PCB file not found: %PCB_FILE%
    echo.
    echo Usage: render_board.bat [pcb_file] [width]
    echo   pcb_file: Path to .kicad_pcb file
    echo   width:    Image width in pixels (default: 3840 for 4K)
    exit /b 1
)

echo Rendering board: %PCB_FILE%
echo Resolution: %WIDTH%px
echo.

REM Run the render command with PNG format
REM This will:
REM - Export SVGs to svg\ folder
REM - Convert SVGs to PNGs in png\ folder using Inkscape
REM - Render 3D views to 3d\ folder
"%VENV_PYTHON%" kicad-analyzer.py render all --pcb "%PCB_FILE%" --format png --width %WIDTH%

echo.
echo Render complete!

endlocal

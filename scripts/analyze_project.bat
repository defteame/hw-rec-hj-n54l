@echo off
REM Example script to analyze the hw-rec-hj-n54l project (Windows)
REM
REM Usage:
REM   analyze_project.bat          - Quick analysis
REM   analyze_project.bat full     - Full comprehensive analysis

setlocal

echo ======================================
echo KiCad Analyzer - Project Analysis
echo ======================================
echo.

REM Configuration
set PCB_FILE=..\layouts\main\main.kicad_pcb
set BOARD_RADIUS=9.3
set CLEARANCE=0.3

REM Check if files exist
if not exist "%PCB_FILE%" (
    echo ERROR: PCB file not found: %PCB_FILE%
    exit /b 1
)

echo Analyzing: %PCB_FILE%
echo.

REM Check if full analysis requested
if "%1"=="full" (
    echo Running comprehensive placement analysis...
    echo.
    python kicad-analyzer.py analyze placement "%PCB_FILE%"
    echo.
    echo ======== View Latest Results ========
    python kicad-analyzer.py latest
    goto :end
)

REM Quick analysis (default)
REM PCB Information
echo ======== PCB Information ========
python kicad-analyzer.py pcb info "%PCB_FILE%"
echo.

REM Check circular fit
echo ======== Circular Fit Check (R=%BOARD_RADIUS%mm) ========
python kicad-analyzer.py pcb circular-fit "%PCB_FILE%" --radius %BOARD_RADIUS%
echo.

REM Check collisions
echo ======== Collision Detection (Clearance=%CLEARANCE%mm) ========
python kicad-analyzer.py pcb collisions "%PCB_FILE%" --clearance %CLEARANCE%
echo.

REM List largest components
echo ======== Largest Components (Top 10) ========
python kicad-analyzer.py pcb list "%PCB_FILE%" --sort area | findstr /N "^" | findstr "^[1-9]:" | findstr "^[1-9]:\|^1[0-5]:"
echo.

:end
echo ======================================
echo Analysis complete!
echo ======================================
echo.
echo For comprehensive analysis with placement, run:
echo   analyze_project.bat full
echo.
pause

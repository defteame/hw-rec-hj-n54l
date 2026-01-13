@echo off
REM Example script to analyze the hw-rec-hj-n54l project (Windows)

echo ======================================
echo KiCad Analyzer - Project Analysis
echo ======================================
echo.

REM Configuration
set PCB_FILE=..\layouts\main\main.kicad_pcb
set PLACEMENT_FILE=..\planv7\placement_main_v1.csv
set BOARD_RADIUS=9.3
set CLEARANCE=0.3

REM Check if files exist
if not exist "%PCB_FILE%" (
    echo ERROR: PCB file not found: %PCB_FILE%
    exit /b 1
)

echo Analyzing: %PCB_FILE%
echo.

REM PCB Information
echo ======== PCB Information ========
python kicad-analyzer.py pcb info "%PCB_FILE%"
echo.

REM List components
echo ======== Component List ========
python kicad-analyzer.py pcb list "%PCB_FILE%" --sort area
echo.

REM Check circular fit
echo ======== Circular Fit Check (R=%BOARD_RADIUS%mm) ========
python kicad-analyzer.py pcb circular-fit "%PCB_FILE%" --radius %BOARD_RADIUS%
echo.

REM Check collisions
echo ======== Collision Detection (Clearance=%CLEARANCE%mm) ========
python kicad-analyzer.py pcb collisions "%PCB_FILE%" --clearance %CLEARANCE%
echo.

REM Layer distribution
echo ======== Layer Distribution ========
python kicad-analyzer.py pcb layers "%PCB_FILE%"
echo.

REM Validate placement if file exists
if exist "%PLACEMENT_FILE%" (
    echo ======== Placement Validation ========
    python kicad-analyzer.py placement validate "%PLACEMENT_FILE%" --circular --radius %BOARD_RADIUS%
    echo.
) else (
    echo Note: Placement file not found: %PLACEMENT_FILE%
    echo.
)

echo ======================================
echo Analysis complete!
echo ======================================
pause

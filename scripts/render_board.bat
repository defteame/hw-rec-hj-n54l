@echo off
REM Render PCB board using KiCad Analyzer
REM Usage: render_board.bat [optional: path to pcb file]
REM
REM Note: 2D renders use SVG format by default (PNG requires Inkscape/ImageMagick)
REM       3D renders are always PNG

setlocal enabledelayedexpansion

cd /d "%~dp0"

set VENV_PYTHON=%~dp0..\.venv\Scripts\python.exe
set DEFAULT_PCB=%~dp0..\layouts\main\main.kicad_pcb
set PCB_FILE=%1

if "%PCB_FILE%"=="" (
    set PCB_FILE=%DEFAULT_PCB%
)

echo Rendering board: %PCB_FILE%
"%VENV_PYTHON%" kicad-analyzer.py render all --pcb "%PCB_FILE%" --format svg

endlocal

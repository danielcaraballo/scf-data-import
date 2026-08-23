@echo off
chcp 65001 >nul
title SCF Data Import - ETL Flota Vehicular

:: Detectar entorno virtual
set "PYTHON_EXE=python"
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
)

:: Ejecutar el lanzador interactivo en Python
"%PYTHON_EXE%" run.py %*

if errorlevel 1 (
    echo.
    echo Ocurrió un error durante la ejecución.
    pause
)

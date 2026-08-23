#!/usr/bin/env bash
# SCF Data Import - Lanzador para Linux/macOS

# Detectar entorno virtual
if [ -f "venv/bin/python" ]; then
    PYTHON_EXE="venv/bin/python"
elif [ -f ".venv/bin/python" ]; then
    PYTHON_EXE=".venv/bin/python"
else
    PYTHON_EXE="python3"
fi

"$PYTHON_EXE" run.py "$@"

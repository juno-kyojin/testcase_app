#!/bin/bash
# Build .exe for Windows using Wine
wine python -m pip install -r requirements.txt
wine pyinstaller -F src/main.py --name=app --distpath dist/windows

@echo off
rem Builds GreenEverything.zip from your own Minecraft install (Windows).
rem Needs Python 3 from https://www.python.org/downloads/ (tick "Add to PATH").
cd /d "%~dp0"
py -3 -m pip install --user --quiet pillow numpy || python -m pip install --user --quiet pillow numpy
py -3 greenify.py %* || python greenify.py %*
pause

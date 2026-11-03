@echo off
cd /d "%~dp0"
set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYEXE%" goto :nopython
echo Starting frontend GUI ...
"%PYEXE%" "%~dp0frontend\main.py"
pause
goto :eof
:nopython
echo [ERROR] .venv not found. Run install_packages.bat first.
pause

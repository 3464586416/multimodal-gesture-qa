@echo off
cd /d "%~dp0"
set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYEXE%" goto :nopython
echo Starting backend: http://127.0.0.1:8000
"%PYEXE%" "%~dp0backend\app.py"
pause
goto :eof
:nopython
echo [ERROR] .venv not found. Run install_packages.bat first.
pause

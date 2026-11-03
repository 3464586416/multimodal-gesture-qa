@echo off
cd /d "%~dp0"
set "PYEXE=%~dp0.venv\Scripts\python.exe"
if exist "%PYEXE%" goto :pip
echo Creating virtualenv .venv ...
python -m venv .venv
if not exist "%PYEXE%" goto :nopython
:pip
echo Upgrading pip ...
"%PYEXE%" -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
echo Installing backend + frontend requirements (about 5-10 min) ...
"%PYEXE%" -m pip install -r "%~dp0backend\requirements.txt" -r "%~dp0frontend\requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 goto :fail
echo Installing dev/test requirements ...
"%PYEXE%" -m pip install -r "%~dp0requirements-dev.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.
echo ============ All dependencies installed ============
echo Next: 1) run schema.sql in Navicat  2) start_backend.bat  3) start_frontend.bat
pause
goto :eof
:nopython
echo [ERROR] python not found. Run setup_python.bat first.
pause
goto :eof
:fail
echo [ERROR] Dependency install failed. Check network / Python version (3.11-3.13).
pause

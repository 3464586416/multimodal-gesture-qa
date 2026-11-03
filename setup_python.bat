@echo off
cd /d "%~dp0"
set "PYVER=3.13.12"
if exist "C:\Python313\python.exe" goto :done
set "PYURL=https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-amd64.exe"
set "INSTALLER=%TEMP%\python-%PYVER%-amd64.exe"
echo Downloading Python %PYVER% ...
curl -L -o "%INSTALLER%" "%PYURL%"
if not exist "%INSTALLER%" goto :failed
echo Installing Python %PYVER% to C:\Python313 ...
"%INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 TargetDir=C:\Python313
:done
echo Done. Reopen a new terminal so PATH takes effect.
pause
goto :eof
:failed
echo [ERROR] Download failed. Try a CN mirror manually:
echo   https://mirrors.tuna.tsinghua.edu.cn/python/
echo   https://mirrors.huaweicloud.com/python/
pause

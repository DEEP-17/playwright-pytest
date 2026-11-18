@echo off
setlocal

where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 "%~dp0openAllureReport.py" %*
exit /b %errorlevel%

:use_python
where python >nul 2>nul
if errorlevel 1 goto no_python
python "%~dp0openAllureReport.py" %*
exit /b %errorlevel%

:no_python
echo Python 3 was not found. Install Python 3, then run this launcher again.
pause
exit /b 1

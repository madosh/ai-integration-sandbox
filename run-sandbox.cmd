@echo off
setlocal
cd /d "%~dp0"

echo.
echo Starting AI Integration Sandbox...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-sandbox.ps1" %*
set EXITCODE=%ERRORLEVEL%

if %EXITCODE% neq 0 (
    echo.
    echo Sandbox failed to start ^(exit %EXITCODE%^).
    pause
    exit /b %EXITCODE%
)

echo.
exit /b 0

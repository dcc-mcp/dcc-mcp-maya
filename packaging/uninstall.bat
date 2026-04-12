@echo off
setlocal

echo =========================================
echo  DCC-MCP-Maya Uninstaller
echo =========================================
echo.

set "MOD_DEST=%USERPROFILE%\Documents\maya\modules\dcc-mcp-maya"

if not exist "%MOD_DEST%" (
    echo Module directory not found at: %MOD_DEST%
    echo Nothing to uninstall.
    pause & exit /b 0
)

echo Removing module directory: %MOD_DEST%
rmdir /s /q "%MOD_DEST%"
if errorlevel 1 (
    echo ERROR: Failed to remove module directory.
    echo Please close Maya and try again.
    pause & exit /b 1
)

echo.
echo Module removed successfully.
echo.
echo NOTE: userSetup.py was not modified. If you want to remove the
echo auto-load snippet, edit this file manually:
echo   %USERPROFILE%\Documents\maya\scripts\userSetup.py
echo.
pause
endlocal

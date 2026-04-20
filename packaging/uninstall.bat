@echo off
setlocal

echo =========================================
echo  DCC-MCP-Maya Uninstaller
echo =========================================
echo.

set "MOD_FILE=%USERPROFILE%\Documents\maya\modules\dcc_mcp_maya.mod"

if not exist "%MOD_FILE%" (
    echo .mod file not found at: %MOD_FILE%
    echo Nothing to uninstall.
    pause & exit /b 0
)

echo Removing .mod file: %MOD_FILE%
del /f "%MOD_FILE%"
if errorlevel 1 (
    echo ERROR: Failed to remove .mod file.
    echo Please close Maya and try again.
    pause & exit /b 1
)

echo.
echo .mod file removed successfully. The plugin will no longer load at Maya startup.
echo.
echo NOTE: The module directory was not deleted (it remains where you extracted it).
echo NOTE: userSetup.py was not modified. If you want to remove the
echo auto-load snippet, edit this file manually:
echo   %USERPROFILE%\Documents\maya\scripts\userSetup.py
echo.
pause
endlocal

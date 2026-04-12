@echo off
setlocal enabledelayedexpansion

echo =========================================
echo  DCC-MCP-Maya Installer
echo =========================================
echo.

REM -- Resolve script directory (handles spaces) --
set "SCRIPT_DIR=%~dp0"
set "MODULE_DIR=%SCRIPT_DIR%dcc-mcp-maya"

if not exist "%MODULE_DIR%\dcc_mcp_maya.mod" (
    echo ERROR: Module directory not found at:
    echo   %MODULE_DIR%
    echo.
    echo Please ensure this script is in the same directory as the dcc-mcp-maya folder.
    pause & exit /b 1
)

REM -- Read version from .mod file --
set "VERSION=unknown"
for /f "tokens=4" %%v in ('findstr /r "^+ MAYAVERSION" "%MODULE_DIR%\dcc_mcp_maya.mod" 2^>nul') do (
    set "VERSION=%%v"
)
echo  Version: %VERSION%
echo.

REM -- Detect Maya installations --
set "FOUND_MAYA=0"
for %%Y in (2026 2025 2024 2023 2022) do (
    if exist "C:\Program Files\Autodesk\Maya%%Y\bin\mayapy.exe" (
        echo  Found Maya %%Y
        set "FOUND_MAYA=1"
    )
)
if "%FOUND_MAYA%"=="0" (
    echo  WARNING: No Maya installation detected.
    echo  The module will still be installed but Maya may not find it automatically.
    echo.
)

REM -- Deploy module directory --
set "MOD_DEST=%USERPROFILE%\Documents\maya\modules"
if not exist "%MOD_DEST%" mkdir "%MOD_DEST%"

REM -- Remove previous installation --
if exist "%MOD_DEST%\dcc-mcp-maya" (
    echo Removing previous installation...
    rmdir /s /q "%MOD_DEST%\dcc-mcp-maya"
)

echo.
echo Deploying module to: %MOD_DEST%\dcc-mcp-maya
xcopy /e /i /q /y "%MODULE_DIR%" "%MOD_DEST%\dcc-mcp-maya" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy module files.
    pause & exit /b 1
)

REM -- Deploy userSetup.py --
set "SCRIPTS_DEST=%USERPROFILE%\Documents\maya\scripts"
if not exist "%SCRIPTS_DEST%" mkdir "%SCRIPTS_DEST%"

set "USERSETUP_DEST=%SCRIPTS_DEST%\userSetup.py"
if not exist "%USERSETUP_DEST%" (
    copy /y "%MOD_DEST%\dcc-mcp-maya\scripts\userSetup.py" "%USERSETUP_DEST%" >nul
    echo Deployed userSetup.py to %SCRIPTS_DEST%
) else (
    REM Check if our snippet is already present
    findstr /c:"dcc_mcp_maya" "%USERSETUP_DEST%" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo Appending dcc-mcp-maya loader to existing userSetup.py...
        echo. >> "%USERSETUP_DEST%"
        echo # dcc-mcp-maya auto-load >> "%USERSETUP_DEST%"
        echo try: >> "%USERSETUP_DEST%"
        echo     import maya.utils >> "%USERSETUP_DEST%"
        echo     def _load_dcc_mcp_maya^^^(^^^): >> "%USERSETUP_DEST%"
        echo         try: >> "%USERSETUP_DEST%"
        echo             import maya.cmds as cmds >> "%USERSETUP_DEST%"
        echo             if not cmds.pluginInfo^^^("dcc_mcp_maya", query=True, loaded=True^^^): >> "%USERSETUP_DEST%"
        echo                 cmds.loadPlugin^^^("dcc_mcp_maya", quiet=True^^^) >> "%USERSETUP_DEST%"
        echo         except Exception: >> "%USERSETUP_DEST%"
        echo             pass >> "%USERSETUP_DEST%"
        echo     maya.utils.executeDeferred^^^(_load_dcc_mcp_maya^^^) >> "%USERSETUP_DEST%"
        echo except ImportError: >> "%USERSETUP_DEST%"
        echo     pass >> "%USERSETUP_DEST%"
    ) else (
        echo userSetup.py already contains dcc-mcp-maya loader, skipping.
    )
)

echo.
echo =========================================
echo  Installation complete!
echo.
echo  Module:   %MOD_DEST%\dcc-mcp-maya
echo  Plugin:   %MOD_DEST%\dcc-mcp-maya\plug-ins\dcc_mcp_maya.py
echo.
echo  The plugin will auto-load when Maya starts.
echo  Alternatively, load it via:
echo    Window ^> Settings/Preferences ^> Plug-in Manager
echo =========================================
pause
endlocal

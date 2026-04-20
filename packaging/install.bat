@echo off
setlocal

echo =========================================
echo  DCC-MCP-Maya Installer
echo =========================================
echo.

REM -- Resolve module directory (this script lives inside it) --
set "MODULE_DIR=%~dp0"
if "%MODULE_DIR:~-1%"=="\" set "MODULE_DIR=%MODULE_DIR:~0,-1%"

REM -- Read version from pre-generated .mod file --
set "VERSION=unknown"
for /f "tokens=4" %%v in ('findstr /r "^+ MAYAVERSION" "%MODULE_DIR%\dcc_mcp_maya.mod"') do (
    set "VERSION=%%v"
)
echo  Version: %VERSION%
echo  Module:  %MODULE_DIR%
echo.

REM -- Generate .mod with absolute path to Maya modules dir --
set "MOD_DEST=%USERPROFILE%\Documents\maya\modules"
if not exist "%MOD_DEST%" mkdir "%MOD_DEST%"

set "HAS_CP37=0"
if exist "%MODULE_DIR%\python37" set "HAS_CP37=1"

(
if "%HAS_CP37%"=="1" (
    echo + MAYAVERSION:2022 PLATFORM:win64 dcc_mcp_maya %VERSION% %MODULE_DIR%
    echo PYTHONPATH+:=python37
    echo PLUG_IN_PATH+:=plug-ins
)
for %%Y in (2023 2024 2025 2026) do (
    echo + MAYAVERSION:%%Y PLATFORM:win64 dcc_mcp_maya %VERSION% %MODULE_DIR%
    echo PYTHONPATH+:=python
    echo PLUG_IN_PATH+:=plug-ins
)
) > "%MOD_DEST%\dcc_mcp_maya.mod"

echo  Generated %MOD_DEST%\dcc_mcp_maya.mod

REM -- Deploy userSetup.py --
set "SCRIPTS_DEST=%USERPROFILE%\Documents\maya\scripts"
if not exist "%SCRIPTS_DEST%" mkdir "%SCRIPTS_DEST%"

if not exist "%SCRIPTS_DEST%\userSetup.py" (
    copy /y "%MODULE_DIR%\scripts\userSetup.py" "%SCRIPTS_DEST%\userSetup.py" >nul
    echo  Deployed userSetup.py
) else (
    findstr /c:"dcc_mcp_maya" "%SCRIPTS_DEST%\userSetup.py" >nul 2>&1
    if errorlevel 1 (
        echo. >> "%SCRIPTS_DEST%\userSetup.py"
        type "%MODULE_DIR%\scripts\userSetup.py" >> "%SCRIPTS_DEST%\userSetup.py"
        echo  Appended to existing userSetup.py
    ) else (
        echo  userSetup.py already configured, skipping.
    )
)

echo.
echo =========================================
echo  Installation complete!
echo.
echo  .mod file:  %MOD_DEST%\dcc_mcp_maya.mod
echo  Module:     %MODULE_DIR%
echo  Plugin:     %MODULE_DIR%\plug-ins\dcc_mcp_maya_plugin.py
echo.
echo  The plugin will auto-load when Maya starts.
echo =========================================
pause
endlocal

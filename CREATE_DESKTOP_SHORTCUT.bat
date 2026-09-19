@echo off
echo Creating desktop shortcut...

set SCRIPT_DIR=%~dp0
set SHORTCUT_NAME=Seismic Deliverable AI Checker
set TARGET=%SCRIPT_DIR%START_APP.bat
set ICON=%SystemRoot%\System32\shell32.dll,13

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\%SHORTCUT_NAME%.lnk'); $s.TargetPath = '%TARGET%'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.IconLocation = '%ICON%'; $s.Description = 'Launch Seismic Deliverable AI Checker'; $s.Save()"

echo.
echo  [OK] Desktop shortcut created: "%SHORTCUT_NAME%"
echo.
pause

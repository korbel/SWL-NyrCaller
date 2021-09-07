@echo off

where java >nul 2>nul
if errorlevel 1 (
    echo Java not found!
    pause
    exit /b 1
)

java -version 2>&1 | find "64-Bit" >nul:
if errorlevel 1 (
    start  /d ".\Discord Audio Stream Bot" "" ".\run win32.bat"
) else (
    start  /d ".\Discord Audio Stream Bot" "" ".\run win64.bat"
)

.\env\python.exe nyr_caller.py "redirectOutput" "voice=Microsoft Zira Desktop" "speed=1"
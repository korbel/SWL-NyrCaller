@echo off

if [%1]==[] goto fullrun

pipenv run python nyr_caller.py log=logs\%1 rewind > .\logs\debug\%1
pipenv run python nyr_caller.py log=logs\%1 rewind trace > .\logs\trace\%1
exit

:fullrun
del .\logs\debug\* /f /q
del .\logs\trace\* /f /q
for %%f in (.\logs\*) do (
    echo %%f
    pipenv run python nyr_caller.py log=%%f rewind > %%~pf\debug\%%~nxf
    pipenv run python nyr_caller.py log=%%f rewind trace > %%~pf\trace\%%~nxf
)
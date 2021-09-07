rd env /s /q
rd __pycache__ /s /q

if not exist "python.zip" (
    powershell Invoke-WebRequest https://www.python.org/ftp/python/3.9.7/python-3.9.7-embed-amd64.zip -OutFile python.zip
)

powershell Expand-Archive python.zip -DestinationPath env

if not exist "get-pip.py" (
    powershell Invoke-WebRequest https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py
)

.\env\python.exe get-pip.py

echo import site>> env\python39._pth

rem ###########################
rem ## Put dependencies here ##
rem ###########################
env\Scripts\pip.exe install pywin32
rem ###########################

env\Python.exe -m compileall nyr_caller.py

copy /y __pycache__\nyr_caller.cpython-39.pyc .\nyr_caller.pyc

pause

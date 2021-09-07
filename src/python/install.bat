rd env /s /q

if not exist "python.zip" (
    powershell Invoke-WebRequest https://www.python.org/ftp/python/3.9.7/python-3.9.7-embed-amd64.zip -OutFile python.zip
)

powershell Expand-Archive python.zip -DestinationPath env

cd env

powershell Invoke-WebRequest https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py

.\python.exe get-pip.py

del get-pip.py /q /f

echo import site>> python39._pth

rem ###########################
rem ## Put dependencies here ##
rem ###########################
Scripts\pip.exe install pywin32
rem ###########################

cd ..
rd __pycache__ /s /q
rd build /s /q
rd dist /s /q
py -3 -m PyInstaller -F nyr10ttl.spec
copy /Y ".\dist\New York Raid Elite 10 Bot.exe" "..\New York Raid Elite 10 Bot"
pause
rd build /s /q
rd dist /s /q
pipenv install
pipenv run pyinstaller -F nyr_caller.py
pause
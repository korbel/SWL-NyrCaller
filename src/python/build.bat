rd build /s /q
rd dist /s /q
py -3 -m pipenv install
py -3 -m pipenv run pyinstaller -F nyr_caller.py
pause
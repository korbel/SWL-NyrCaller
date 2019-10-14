@echo off
powershell -Command "1..%1 | %% { Invoke-Expression (\".\debug \" + \"$_\".PadLeft(2, \"0\")) }"
powershell -Command "1..%1 | %% { Invoke-Expression (\".\trace \" + \"$_\".PadLeft(2, \"0\")) }"
@echo off
powershell -Command "1..%1 | %% { Invoke-Expression (\".\debug \" + \"$_\".PadLeft(2, \"0\")) }"
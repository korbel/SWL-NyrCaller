rd ".\dist" /s /q

xcopy ".\src\as2\bin\NyrCaller.swf" ".\dist\Data\Gui\Custom\Flash\NyrCaller\" /y /q
xcopy ".\src\as2\src\mod\*" ".\dist\Data\Gui\Custom\Flash\NyrCaller\" /y /q

xcopy ".\src\batch\*" ".\dist\NyrCaller\" /y /q
xcopy ".\*.md" ".\dist\NyrCaller\" /y /q

xcopy ".\src\python\nyr_caller.py" ".\dist\NyrCaller\" /y /q
xcopy ".\src\python\env" ".\dist\NyrCaller\env\" /y /q /e
xcopy ".\external\Discord Audio Stream Bot" ".\dist\NyrCaller\Discord Audio Stream Bot\" /y /q /e
xcopy ".\external\VBCABLE_Driver_Pack43" ".\dist\NyrCaller\VBCABLE_Driver_Pack43\" /y /q /e

cd ".\dist"
tar -a -cf "NyrCaller.zip" "Data" "NyrCaller"

pause
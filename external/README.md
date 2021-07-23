This directory contains the required external tools to package and run the application.

It should contain the following files/directories:

- `VBCABLE_Driver_Pack43`: Download and extract the setup files from [here](https://vb-audio.com/Cable/).
- `Discord Audio Stream Bot`: The latest release at the time of writing (2021-07-23) is available [here](https://github.com/BinkanSalaryman/Discord-Audio-Stream-Bot).

Example directory structure:

```
external/
│-- Discord Audio Stream Bot
|   |-- Discord Audio Stream Bot.jar
|   |-- run win32.bat
|   `-- run win64.bat
│-- VBCABLE_Driver_Pack43
|   |-- VBCABLE_Setup.exe
|   |-- VBCABLE_Setup_x64.exe
|   |-- VBCABLE_ControlPanel.exe
|   `-- ...
│-- README.me
`-- .gitignore
```

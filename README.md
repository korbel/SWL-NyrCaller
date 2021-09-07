# New York Raid SWL caller bot

This bot analyses the NYR combat in real time and calls when it deems necessary using Windows TTS (Text to Speech) service.

Currently it only supports NYR E10.

The currently supported call types:
- **Pod target is/are [...]**: In P1 and P3 when someone gets targeted by *Inevitable Doom*
- **Third bird**: In phrase 2, when the 3rd *Eldritch Guardian* spawns
- **Hulk has spawned**: In P2 and P3 when *Zero-Point Titan* spawns
- **Stop DPS**:  When the next *Personal Space* is expected in 5-9 seconds based on the current DPS, and the next expected *Shadow Out of Time* is within -10 to +6 seconds to *Personal Space*
- **Personal space soon! / Final resort soon!**: When the next *Personal Space* or *Final Resort* is within 1 second based on out current DPS
- **Focus on hulk**: If there was a *Shadow Out of Time* cast recently (the past 14 seconds) or a Hulk has spawned in P3 and the next expected *Personal Space* is within 4 seconds with out average DPS
- **Stop DPS and wait for pod**: In P1 if *Shadow Out of Time* is expected in around 7 seconds and the next Pod is less than 9 seconds away
- **Push it**: In P1 if *Shadow Out of Time* is expected in around 7 seconds and the next Pod is 9-12 seconds away
- **Shadow out of time soon!**: In P1 when *Shadow Out of Time* is within 1 seconds away based on our average DPS 
- **Personal space will be early**: When the 3rd *Eldritch Guardian* dies and the *The Unutterable Lurker*'s HP is within 4 seconds away from the next *Personal Space* with an average DPS
- **Hulk is dead**: When a *Zero-Point Titan* dies in P3 (or at the end of P2).
- **Filth is out**: At the start of P1 and P3 when *Pure Filth* is cast
- **Shadow out of time**: In P3 when *Shadow Out of Time* is cast
- **Pod**: Anytime in game when *The Unutterable Lurker* casts *From Beneath You, It Devours*
- **Kill it**: In P2 when the 3rd *Eldritch Guardian* has already cast *Downfall* 3 times
- **1, 2, 3, 4 ...**: Number of *Downfall*s of the 3rd *Eldritch Guardian* in P2

## Installation instructions

Extract zip file into your SWL folder, check if have the following directories:

- `<SWL directory>\NyrCaller`
- `<SWL directory>\Data\Gui\Custom\Flash\NyrCaller`

`<SWL directory>` is where the `SecretWorldLegends.exe` and `SecretWorldLegendsDX11.exe` files are located.

Restart the game. 


## Usage

To run it locally without setting up a discord bot, navigate to the `<SWL directory>\NyrCaller` directory and start the `start.bat` executable. You should now see a console with the following message:

> Agnitio NYR Caller bot started

**IMPORTANT!** The bot must be running when you enter NYR E10. Upon entering NYR you should hear the bot saying "Welcome to New York raid E10!" indicating that everything is set up and working correctly.
If you forgot to start the bot then type `/reloadui` into the chat or press `Ctrl + Shift + F1` (which is equivalent to `/reloadui`) before starting the fight. It will re-register all the raid participants and should say "Welcome to New York raid E10!" if it hasn't already done so.
The bot is listening to in-game events so upon the unfortunate event of the game crashing, it may lose track of the fight and say weird things for the rest of the fight. Beware.


## Setting it up as a Discord bot

To broadcast the voice of the caller application on discord, other than running the caller app, you need to set up a discord bot and have some means to transfer the voice of the caller bot to the discord bot. Here are the steps how to do that:

- First you must install VBCable driver. It can be found in the `NyrCaller\VBCABLE_Driver_Pack43` directory, it will give you the ability to connect the voice of NYR caller bot a discord bot.
- Next you will have to register the bot on Discord's website and acquire a bot token. If you've already got a token and `SERVER MEMBERS INTENT` is enabled for the bot you can skip the following step.
- To acquire a bot token, you must create a bot user first. To do that, visit the [Discord Developer Portal](https://discordapp.com/developers/applications). After you created a bot user, make sure you enable `SERVER MEMBERS INTENT` in the bot settings.
- Now start the `Discord Audio Stream Bot\start_with_discord.bat` executable. You must have java installed on your system and it must be added the PATH environment variable. I recommend the [AdoptOpenJDK](https://adoptopenjdk.net/) LTS builds, but you can install Java from <https://java.com/> too.
- Go to the Settings tab of the Discord Audio Stream Bot application, and enter your bot token you received. Unmute the audio input and select "CABLE Output (VB-Audio Virtual Cable)".
- On the Home tab start the bot. After it started, you can invite you bot to your server on the Maintenance tab if it hasn't already invited. Make sure the bot has the correct permissions to be able to enter and talk in the voice channels.
- Send the "help" command by directly messaging the bot or by @mention to see how to use the bot. If you want the bot to follow you when you join a voice channel you can send a mention on your guild discord: @Bot_name follow-voice set @Your_name
- Further info and troubleshooting here: https://github.com/BinkanSalaryman/Discord-Audio-Stream-Bot

**IMPORTANT!** Don't distribute your "Discord Audio Stream Bot" directory with the `config.json` as it contains the secret key to control your bot! To change the secret key (the bot token) go to <https://discordapp.com/developers/applications/>


## Advanced settings and troubleshooting

The bot uses the Microsoft Speech API and by default it uses Microsoft Zira's voice. If it cannot be found it uses the default one.

To test different voices and settings press `Windows Key + R` and run the following command:

    rundll32.exe shell32.dll,Control_RunDLL C:\WINDOWS\system32\speech\speechux\sapi.cpl

You can also edit `start.bat` and `start_with_discord.bat` to change the default settings. The following arguments can be set:
- **voice**: Name of the voice to be used. Run the following command in powershell to find other voices:
    
        (New-Object -ComObject SAPI.SPVoice).GetVoices() | % {$_.GetAttribute("Name")}

- **speed**: Speed of the speech. Must be an integer number between -10 and 10 (default is 0)
- **log**: Path of the game log file to parse. It should point to a valid ClientLog.txt
- **redirectOutput**: Redirects the audio output to the "CABLE Input (VB-Audio Virtual Cable)" channel. Used together with the Discord bot.
- **trace**: Verbose output of in-game events
- **rewind**: Disable voice and re-parse the whole ClientLog.txt for debugging purposes

Example:

    ".\NyrCaller.exe" "redirectOutput" "voice=Microsoft David Desktop" "speed=8" "log=C:\Games\Secret World Legends\OldLogs\ClientLog20190412002700.txt" "trace" "rewind"


## Development guide

The caller consists of 2 individual parts. One is an SWL mod which sends the in-game events into the ClientLog, and the other one is a Python app which reads and analyses the ClientLog and calls using Microsoft's Text-to-Speech engine when it deems necessary.

The source code can be found at <https://github.com/korbel/SWL-NyrCaller>.

### The SWL mod

Set up a development environment by downloading FlashDevelop and setting it up by following [this guide](https://docs.google.com/document/d/17c5wV2a7Z--KpEWTobFtoWXO-oHSKT43h_94_TRrG-M/edit) or if you don't want to use FlashDevelop you can check out the [SWL-BuildScripts repository](https://github.com/korbel/SWL-BuildScripts) and follow its [README.md](https://github.com/korbel/SWL-BuildScripts/blob/main/README.md).

The .as2proj project file can be found in the `\src\as2` directory.

### The Python app

Run `src\python\install.bat` to download and set up a local installation of Python.
It should download python, extract it to the `env` directory, add `pip` to the installation and install the dependencies.

When packaging the application the `env` directory will be shipped alongside the script.

To add new dependencies, you must edit `install.bat`. You can manually install a dependency by running `env\Scripts\pip.exe install <module_name>`.

### Testing and debugging the Python app

To test changes or debug issues, you can put your ClientLog file into the `src\python\logs` directory and run the `test.bat` executable. It will generate the debug and trace logs into the `src\python\logs\debug` and `src\python\logs\trace` directories respectively to help you test, analyze and debug NYR runs.

By default it will (re)generate all the debug and trace files for all the logs it can find in the `logs` directory, however it can be slow at times. To only test a single log, you can pass in the name of the log as the first parameter of the `test.bat`, e.g.:

    .\test.bat ClientLog20190412002700.txt

### Packaging the app

To package the app, you must follow the instructions in the `external\README.md` file first and download the external tools required for deploying the final product.

After both the SWL mod and the Python app got built, run the `package.bat` executable, it will create the required directory structure in the `dist` folder, then it will copy the appropriate files in their corresponding directory, and finally create the `dist\NyrCaller.zip` archive which can be directly shipped and extracted into the user's game directory.

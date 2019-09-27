# ALAuto
Updated and semi-rewritten version of [azurlane-auto](https://github.com/perryhuynh/azurlane-auto).  
Automates Combat, Commissions, Missions, Enhancement and Retiring.

**This bot was made for EN server, other servers won't work with current assets.**

## Requirements on Windows
* Python 3.X installed and added to PATH.
* [ADB r23](https://dl.google.com/android/repository/platform-tools_r23.0.1-windows.zip) added to PATH.
* This [sed](http://unxutils.sourceforge.net/) port added to PATH.
* ADB debugging enabled emulator with **1920x1080 resolution**.

Tested and used on Windows 10 with Nox 6.3.0.2, Android 5.1 @ 60fps. If it does not work with your emulator please use Nox.

## Installation and Usage
1. Clone or download this repository.
2. Install the required packages via `pip3` with the command `pip3 install -r requirements.txt`.
3. Enable adb debugging on your emulator, on Nox you might also need to enable root.
4. Change config.ini's IP:PORT to 127.0.0.1 and your emulator's adb port, then change the rest to your likings.
5. Run `ALAuto` using the command `python ALAuto.py`.

Check the [Wiki](https://github.com/Egoistically/ALAuto/wiki/Config.ini-and-Modules-explanation) for more information. It's my first time making one, don't mind me.  

## Relevant information
* It does not support multiple fleets, it only works when **one** fleet is selected. 
* CPU usage might spike when searching for enemies, if it bothers you comment lines 118 to 126 in utils.py.

This was made for my own usage, it is far from good and I'm very aware of it. I am posting this because it might be useful to someone, that's all.  
If you'd like to contribute in any way make sure to open a [pull request](https://github.com/Egoistically/ALAuto/pulls) or an [issue](https://github.com/Egoistically/ALAuto/issues).
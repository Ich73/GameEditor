[![](https://img.shields.io/github/v/release/Ich73/GameEditor?include_prereleases&label=Release)](https://github.com/Ich73/GameEditor/releases/latest)
[![](https://img.shields.io/github/downloads/Ich73/GameEditor/total?label=Downloads)](https://github.com/Ich73/GameEditor/releases)
[![](https://img.shields.io/github/license/Ich73/GameEditor?label=License)](/LICENSE)
# Game Editor
Game Editor is a program to edit and randomize CIA and 3DS files.  

![Screenshot](https://user-images.githubusercontent.com/44297391/166115893-3151e2e6-aaa9-4d62-af85-1915dcbd3cf4.png)

It supports the following games:
  * [Dragon Quest Monsters 2: Cobi and Tara's Marvelous Mysterious Key](https://github.com/Ich73/GameEditor/wiki/DQM2)
  
It uses the following tools:
  * [xdelta](https://github.com/jmacd/xdelta-gpl) ([v3.1.0](https://github.com/jmacd/xdelta-gpl/releases/tag/v3.1.0))
  * [3dstool](https://github.com/dnasdw/3dstool) ([v1.1.0](https://github.com/dnasdw/3dstool/releases/tag/v1.1.0))
  * [ctrtool](https://github.com/3DSGuy/Project_CTR) ([v0.7](https://github.com/3DSGuy/Project_CTR/releases/tag/ctrtool-v0.7))
  * [makerom](https://github.com/3DSGuy/Project_CTR) ([v0.17](https://github.com/3DSGuy/Project_CTR/releases/tag/makerom-v0.17))


## Using Game Editor
You can download the newest version from the [Release Page](https://github.com/Ich73/GameEditor/releases/latest). There are two downloads:
  * `GameEditor-Standalone.zip`: Extract the archive to a directory of your choice and run `GameEditor.exe`.
  * `GameEditor-Installer.zip`: Extract the archive and run `GameEditor-Installer.exe` in order to install Game Editor on your PC. You can then start it from the start menu.
  
It supports CIA and 3DS files. The required tools are downloaded automatically.  

## For Developers
### Setup
This program is written using [Python 3.10.2](https://www.python.org/downloads/release/python-3102/). You can install the required packages with the following commands.
```
python -m pip install pyqt5>=5.15.6
```
Addionally you need `lrelease`, a Qt tool for converting `.ts` translation files to `.qm` files.  
  
You also need [`JTools.py`](https://github.com/Ich73/BinJEditor/blob/master/JTools.py) found in [BinJ Editor](https://github.com/Ich73/BinJEditor) as well as [`GameManager.py`](https://github.com/Ich73/TranslationToolkit/blob/master/GameManager.py) and [`ToolManager.py`](https://github.com/Ich73/TranslationToolkit/blob/master/ToolManager.py) found in [Translation Toolkit](https://github.com/Ich73/TranslationToolkit).

### Compiling Resources
To convert the translation files and pack them with the other resources into a single `Resources.py` file, you can run the following commands. This is needed whenever you change any resource file.
```
set "plugins=Plugins\CTR-P-BDMJ.py"

pylupdate5 GameEditor.pyw MessageBoxes.py Plugins\BasePlugin.py %plugins% Resources/Forms/main-window.ui -ts -noobsolete Resources/i18n/de.ts
lrelease Resources/i18n/de.ts

pylupdate5 GameEditor.pyw MessageBoxes.py Plugins\BasePlugin.py %plugins% Resources/Forms/main-window.ui -ts -noobsolete Resources/i18n/en.ts
lrelease Resources/i18n/en.ts

lrelease Resources/i18n/qtbase_de.ts
lrelease Resources/i18n/qtbase_en.ts

pyrcc5 Resources.qrc -o Resources.py
```

### Running
You can run the program by using the command `python GameEditor.pyw`.

### Distributing
To pack the program into a single executable file, [pyinstaller](http://www.pyinstaller.org/) is needed.  
Run the command `pyinstaller GameEditor-OneFile.spec --noconfirm` and the executable will be created in the `dist` folder.  
Run the command `pyinstaller GameEditor-OneFolder.spec --noconfirm` and the program files will be created in the `dist/bin` folder.

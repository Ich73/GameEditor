""" Author: Dominik Beese
>>> Game Editor
	A program to edit and randomize CIA and 3DS files.
<<<
"""

# pip install pyqt5
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QEvent
from PyQt5.uic import loadUi
import Resources

import sys
from os import remove, listdir, makedirs, getenv
from os.path import join, exists, basename, dirname, realpath, splitext, expanduser
from os.path import normpath, sep as normsep
from shutil import rmtree
from zipfile import ZipFile
import platform

import webbrowser
from urllib.request import urlopen

import uuid
import json
import re

import ToolManager
import GameManager

from MessageBoxes import MessageBoxes
from Plugins import CTR_P_BDMJ


CONFIG_FILENAME = 'config.json'
GAME_CONFIG_FILENAME = 'ge-config.json'

APPNAME = 'Game Editor'
VERSION = 'v0.1.0'
REPOSITORY = r'Ich73/GameEditor'
AUTHOR = 'Dominik Beese 2022'

TOOLS = {
	'xdelta': {
		'version': '3.1.0',
		'win64': {'url': r'https://github.com/jmacd/xdelta-gpl/releases/download/v3.1.0/xdelta3-3.1.0-x86_64.exe.zip', 'exe': 'xdelta.exe'},
		'win32': {'url': r'https://github.com/jmacd/xdelta-gpl/releases/download/v3.1.0/xdelta3-3.1.0-i686.exe.zip', 'exe': 'xdelta.exe'},
	},
	'3dstool': {
		'version': '1.1.0',
		'win64': {'url': r'https://github.com/dnasdw/3dstool/releases/download/v1.1.0/3dstool.zip', 'exe': '3dstool.exe'},
		'win32': {'url': r'https://github.com/dnasdw/3dstool/releases/download/v1.1.0/3dstool.zip', 'exe': '3dstool.exe'},
	},
	'ctrtool': {
		'version': '0.7',
		'win64': {'url': r'https://github.com/3DSGuy/Project_CTR/releases/download/ctrtool-v0.7/ctrtool-v0.7-win_x86_64.zip', 'exe': 'ctrtool.exe'},
		'win32': {'url': r'https://github.com/Ich73/Project-CTR-WindowsBuilds/releases/download/ctrtool-v0.7/ctrtool-v0.7-win_i686.zip', 'exe': 'ctrtool.exe'},
	},
	'makerom': {
		'version': '0.17',
		'win64': {'url': r'https://github.com/3DSGuy/Project_CTR/releases/download/makerom-v0.17/makerom-v0.17-win_x86_64.zip', 'exe': 'makerom.exe'},
		'win32': {'url': r'https://github.com/Ich73/Project-CTR-WindowsBuilds/releases/download/makerom-v0.17/makerom-v0.17-win_i686.zip', 'exe': 'makerom.exe'},
	}
}


###########
## Setup ##
###########

# check os
if 'windows' in platform.system().lower(): opSys = 'win'
else: opSys = 'linux'
if '64' in platform.machine(): opSys += '64'
else: opSys += '32'

# set paths
ROOT = dirname(realpath(sys.argv[0]))
USER = ROOT
CONFIG_FILE = join(ROOT, CONFIG_FILENAME)
try:
	# write and delete test file to check permissions
	temp = join(ROOT, 'temp')
	with open(temp, 'wb') as file: file.write(b'\x00')
	remove(temp)
except PermissionError:
	# use user path and appdata instead
	USER = expanduser('~') # user path
	ROOT = join(getenv('APPDATA'), APPNAME) # appdata
	CONFIG_FILE = join(ROOT, CONFIG_FILENAME)
	if not exists(dirname(CONFIG_FILE)): os.makedirs(dirname(CONFIG_FILE))

# set windows taskbar icon
try:
	from PyQt5.QtWinExtras import QtWin
	appid = APPNAME.replace(' ', '').lower() + '.' + VERSION
	QtWin.setCurrentProcessExplicitAppUserModelID(appid)
except: pass

# config
class Config:
	cfg = None
	
	def loadConfig():
		if Config.cfg is not None: return
		if not exists(CONFIG_FILE):
			Config.cfg = dict()
			return
		try:
			with open(CONFIG_FILE, 'r') as file:
				Config.cfg = json.load(file)
		except:
			Config.cfg = dict()
	
	def saveConfig():
		with open(CONFIG_FILE, 'w') as file:
			json.dump(Config.cfg, file)
	
	def get(key, default = None):
		Config.loadConfig()
		value = Config.cfg.get(key)
		if value is None:
			Config.set(key, default)
			return default
		return value
	
	def set(key, value):
		Config.cfg[key] = value
		Config.saveConfig()


#################
## Main Window ##
#################

class MainWindow(QtWidgets.QMainWindow, MessageBoxes):
	""" The Main Window of the editor. """
	
	def __init__(self):
		super(MainWindow, self).__init__()
		uiFile = QtCore.QFile(':/Resources/Forms/main-window.ui')
		uiFile.open(QtCore.QFile.ReadOnly)
		loadUi(uiFile, self)
		uiFile.close()
		
		# menu > language
		self.menuLanguageGroup = QtWidgets.QActionGroup(self.menuLanguage)
		self.menuLanguageGroup.addAction(self.actionGerman)
		self.menuLanguageGroup.addAction(self.actionEnglish)
		self.menuLanguageGroup.triggered.connect(self.retranslateUi)
		
		# menu > help
		self.actionAbout.triggered.connect(self.showAbout)
		self.actionAbout.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation))
		self.actionCheckForUpdates.triggered.connect(lambda: self.checkUpdates(True))
		self.actionCheckForUpdates.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
		
		# buttons
		self.buttonExtract.clicked.connect(self.extractGame)
		self.buttonRebuild.clicked.connect(self.rebuildGame)
		self.buttonLayeredFS.clicked.connect(self.exportLayeredFS)
		self.buttonEdit.clicked.connect(self.editGame)
		self.buttonImport.clicked.connect(self.importSettings)
		self.buttonExport.clicked.connect(self.exportSettings)
		
		# ui
		self.retranslateUi(None)
		self.appname = APPNAME
		self.game_config_filename = GAME_CONFIG_FILENAME
		self.tools = TOOLS
		self.opSys = opSys
		self.icon = QtGui.QPixmap(':/Resources/Images/icon.ico')
		self.setWindowIcon(QtGui.QIcon(self.icon))
		self.show()
		self.checkTools()
		self.checkUpdates()
	
	def retranslateUi(self, language):
		# change locale
		action2locale = {
			self.actionGerman: 'de',
			self.actionEnglish: 'en',
		}
		if language is None:
			locale = Config.get('language', QtCore.QLocale.system().name().split('_')[0])
			if not QtCore.QFile.exists(':/Resources/i18n/%s.qm' % locale): locale = 'en'
			next(k for k, v in action2locale.items() if v == locale).setChecked(True)
		else: locale = action2locale[language]
		Config.set('language', locale)
		translator.load(':/Resources/i18n/%s.qm' % locale)
		app.installTranslator(translator)
		baseTranslator.load(':/Resources/i18n/qtbase_%s.qm' % locale)
		app.installTranslator(baseTranslator)
		
		# update texts
		self.setWindowTitle(APPNAME)
		self.menuLanguage.setTitle(self.tr('Language'))
		self.menuHelp.setTitle(self.tr('Help'))
		self.actionAbout.setText(self.tr('About %s...') % APPNAME)
		self.actionCheckForUpdates.setText(self.tr('Check for Updates...'))
		self.groupLeft.setTitle(self.tr('CIA/3DS Tools'))
		self.groupRight.setTitle(self.tr('Editor Tools'))
		self.textHelp.setText('<html><body><p style="margin-left: 1em;">1. %s<br/>2. %s<br/>3. %s</body></html>' % (self.tr('Extract Game'), self.tr('Edit Game'), self.tr('Rebuild Game')))
		self.buttonExtract.setText(self.tr('Extract Game'))
		self.buttonRebuild.setText(self.tr('Rebuild Game'))
		self.buttonLayeredFS.setText(self.tr('Export LayeredFS'))
		self.buttonEdit.setText(self.tr('Edit Game'))
		self.buttonImport.setText(self.tr('Import Settings'))
		self.buttonExport.setText(self.tr('Export Settings'))
	
	def tr(self, sourceText):
		s = QtCore.QCoreApplication.translate('MainWindow', sourceText)
		if r'\n' not in s: return s
		return '<html><body><p>%s</p></body></html>' % s.replace(r'\n', '</p><p>')
	
	## UPDATES ##
	
	def checkUpdates(self, showFailure=False):
		""" Queries the github api for a new release. """
		try:
			# query api
			latest = r'https://api.github.com/repos/%s/releases/latest' % REPOSITORY
			with urlopen(latest) as url: data = json.loads(url.read().decode())
			tag = data['tag_name']
			info = data['body']
			link = data['html_url']
			
			# compare versions
			def ver2int(s):
				if s[0] == 'v': s = s[1:]
				v = s.split('.')
				return sum([int(k) * 100**(len(v)-i) for i, k in enumerate(v)])
			current_version = ver2int(VERSION)
			tag_version = ver2int(tag)
			
			if current_version == tag_version:
				if showFailure: self.showInfo(self.tr('update.newestVersion') % APPNAME)
				return
			
			if current_version > tag_version:
				if showFailure: self.showInfo(self.tr('update.newerVersion') % APPNAME)
				return
			
			# show message
			msg = QtWidgets.QMessageBox()
			msg.setWindowTitle(self.tr('Check for Updates...'))
			msg.setWindowIcon(QtGui.QIcon(self.icon))
			text = '<html><body><p>%s</p><p>%s: <code>%s</code><br/>%s: <code>%s</code></p><p>%s</p></body></html>'
			msg.setText(text % (self.tr('update.newVersionAvailable') % APPNAME, self.tr('update.currentVersion'), VERSION, self.tr('update.newVersion'), tag, self.tr('update.doWhat')))
			info = re.sub(r'!\[([^\]]*)\]\([^)]*\)', '', info) # remove images
			info = re.sub(r'\[([^\]]*)\]\([^)]*\)', '\\1', info) # remove links
			info = re.sub(r'__([^_\r\n]*)__|_([^_\r\n]*)_|\*\*([^\*\r\n]*)\*\*|\*([^\*\r\n]*)\*|`([^`\r\n]*)`', '\\1\\2\\3\\4\\5', info) # remove bold, italic and inline code
			msg.setDetailedText(info.strip())
			button_open_website = QtWidgets.QPushButton(self.tr('update.openWebsite'))
			msg.addButton(button_open_website, QtWidgets.QMessageBox.AcceptRole)
			msg.addButton(QtWidgets.QMessageBox.Cancel)
			msg.exec_()
			res = msg.clickedButton()
			
			# open website
			if msg.clickedButton() == button_open_website:
				webbrowser.open(link)
			
		except Exception as e:
			print('Warning: Checking for updates failed:', str(e))
			if showFailure: self.showError(self.tr('update.failed'), str(e))
	
	def checkTools(self):
		""" Checks and downloads the tools. """
		# get tool information
		tool_args_version_url = [
			(tool, args, *Config.get(tool, (TOOLS[tool]['version'], TOOLS[tool][opSys]['url'])))
			for tool, args in [('xdelta', '-V'), ('3dstool', ''), ('ctrtool', ''), ('makerom', '')]
		]
		# check tools
		download_tools = [
			(tool, url) for tool, args, version, url in tool_args_version_url
			if not ToolManager.checkTool(join(ROOT, TOOLS[tool][opSys]['exe']), version, args=args)
		]
		# download tools
		if download_tools:
			msg = self.showProgress('', maximum=len(download_tools))
			for tool, url in download_tools:
				msg.setText(self.tr('Downloading %s...') % tool)
				ToolManager.downloadTool(url, join(ROOT, TOOLS[tool][opSys]['exe']))
				msg.incValue()
	
	## ACTIONS ##
	
	def escapeName(self, name):
		""" Escapes a filename by replacing several characters with underscores. """
		return re.sub(r'[^\w]+', '_', name).strip('_')
	
	def extractGame(self):
		""" Extracts a cia or 3ds file. """
		# ask game file
		cia_dir = Config.get('game-dir', USER)
		game_file, _ = QtWidgets.QFileDialog.getOpenFileName(self, self.tr('extract.choose_file'), cia_dir, self.tr('type.cia_3ds'))
		if not game_file: return
		Config.set('game-dir', dirname(game_file))
		
		# ask game dir
		while True:
			dir_dir = Config.get('dir-dir', USER)
			game_dir = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr('extract.choose_dir'), dir_dir)
			if not game_dir: return
			Config.set('dir-dir', game_dir)
			if len(listdir(game_dir)) > 0:
				if self.askWarning(self.tr('extract.warning_non_empty_folder_ask_create')):
					game_dir = join(game_dir, self.escapeName(basename(game_file)))
					if exists(game_dir): game_dir = game_dir + '_' + str(uuid.uuid4())
					makedirs(game_dir, exist_ok=True)
					break
				else: continue
			else: break
		
		# extract game
		msg = self.showProgress(self.tr('extract.inprogress'), maximum=7+1)
		msg.setValue(1)
		for v in GameManager.extractGame(game_file, game_dir, join(ROOT, TOOLS['3dstool'][opSys]['exe']), join(ROOT, TOOLS['ctrtool'][opSys]['exe'])):
			if isinstance(v, str):
				self.showError(self.tr('extract.failed'), v)
				return
			msg.setValue(v+1)
		
		# create config
		config = dict()
		config['game-type'] = splitext(game_file)[1][1:]
		with open(join(game_dir, 'HeaderNCCH0.bin'), 'rb') as file:
			config['game-id'] = str(file.read()[0x150:0x15a].decode())
		config['editor-version'] = VERSION
		with open(join(game_dir, GAME_CONFIG_FILENAME), 'w', encoding='UTF-8') as file: json.dump(config, file)
		
		# show success
		self.showInfo(self.tr('extract.done'), game_dir)
	
	def rebuildGame(self):
		""" Rebuilds a cia or 3ds file. """
		# ask game dir
		dir_dir = Config.get('dir-dir', USER)
		game_dir = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr('rebuild.choose_dir'), dir_dir)
		if not game_dir: return
		Config.set('dir-dir', game_dir)
		if not exists(join(game_dir, GAME_CONFIG_FILENAME)):
			self.showError(self.tr('rebuild.error_bad_folder'), self.tr('msg.no_config_found'))
			return
		
		# read config
		with open(join(game_dir, GAME_CONFIG_FILENAME), 'r', encoding='UTF-8') as file: config = json.load(file)
		
		# ask game file
		cia_dir = Config.get('game-dir', USER)
		type = self.tr('type.3ds') if config.get('game-type', 'cia') == '3ds' else self.tr('type.cia')
		game_file, _ = QtWidgets.QFileDialog.getSaveFileName(self, self.tr('rebuild.choose_file'), cia_dir, type)
		if not game_file: return
		Config.set('game-dir', dirname(game_file))
		
		# rebuild game
		msg = self.showProgress(self.tr('rebuild.inprogress'), maximum=6+1)
		msg.setValue(1)
		for v in GameManager.rebuildGame(game_dir, game_file, 1024, join(ROOT, TOOLS['3dstool'][opSys]['exe']), join(ROOT, TOOLS['makerom'][opSys]['exe'])):
			if isinstance(v, str):
				self.showError(self.tr('rebuild.failed'), v)
				return
			msg.setValue(v+1)
		
		# show success and ask delete folder
		if self.askDlg(self.tr('rebuild.done_ask_delete')):
			while self.askDlg(self.tr('rebuild.ask_save_settings')):
				if self._exportSettings(game_dir): break
			rmtree(game_dir)
			self.showInfo(self.tr('rebuild.deleted'))
	
	def exportLayeredFS(self):
		""" Exports a LayeredFS zip file. """
		# ask 3ds or citra
		layeredfs_type = self.askCustomDlg(self.tr('layeredfs.choose_type'), '3DS', 'Citra').lower()
		
		# ask game dir
		dir_dir = Config.get('dir-dir', USER)
		game_dir = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr('layeredfs.choose_dir'), dir_dir)
		if not game_dir: return
		Config.set('dir-dir', game_dir)
		if not exists(join(game_dir, GAME_CONFIG_FILENAME)):
			self.showError(self.tr('layeredfs.error_bad_folder'), self.tr('msg.no_config_found'))
			return
		
		# read config
		with open(join(game_dir, GAME_CONFIG_FILENAME), 'r', encoding='UTF-8') as file: config = json.load(file)
		
		# check config
		if 'game-files' not in config:
			self.showError(self.tr('layeredfs.error_bad_folder'), self.tr('msg.config_without_game_files'))
			return
		
		# ask layeredfs file
		cia_dir = Config.get('layeredfs-dir', Config.get('game-dir', USER))
		layeredfs_file, _ = QtWidgets.QFileDialog.getSaveFileName(self, self.tr('layeredfs.choose_file'), cia_dir, self.tr('type.zip'))
		if not layeredfs_file: return
		Config.set('layeredfs-dir', dirname(layeredfs_file))
		
		# export layeredfs patch
		with ZipFile(layeredfs_file, 'w') as zip:
			for game_file in config['game-files']:
				parts = normpath(game_file).split(normsep)
				if parts[0] == 'ExtractedRomFS': parts[0] = 'romfs'
				elif parts[0] == 'ExtractedExeFS': parts[0] = 'exefs' if layeredfs_type == 'citra' else ''
				else: continue
				zip.write(filename=join(game_dir, game_file), arcname=join(*parts))
		
		# show success
		self.showInfo(self.tr('layeredfs.done'), layeredfs_file)
	
	def editGame(self):
		""" Starts the plugin suitable for the chosen game folder. """
		# ask game dir
		dir_dir = Config.get('dir-dir', USER)
		game_dir = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr('edit.choose_dir'), dir_dir)
		if not game_dir: return
		Config.set('dir-dir', game_dir)
		if not exists(join(game_dir, GAME_CONFIG_FILENAME)):
			self.showError(self.tr('edit.error_bad_folder'), self.tr('msg.no_config_found'))
			return
		
		# get game id
		with open(join(game_dir, GAME_CONFIG_FILENAME), 'r', encoding='UTF-8') as file: game_id = json.load(file)['game-id']
		
		# start plugin
		try:
			Editor = eval('%s.Editor' % game_id.replace('-', '_'))
			#Editor = getattr(__import__('Plugins.%s' % game_id, fromlist=['Editor']), 'Editor')
		except NameError:
			self.showError(self.tr('edit.error_no_plugin'), game_id)
			return
		dlg = Editor(self, game_dir, title=APPNAME, icon=QtGui.QIcon(self.icon))
		if dlg.run(): dlg.exec_()
	
	def importSettings(self):
		""" Import settings to a chosen game folder. """
		# ask settings file
		cia_dir = Config.get('settings-dir', USER)
		settings_file, _ = QtWidgets.QFileDialog.getOpenFileName(self, self.tr('import.choose_file'), cia_dir, self.tr('type.settings'))
		if not settings_file: return
		Config.set('settings-dir', dirname(settings_file))
		with open(settings_file, 'r', encoding='UTF-8') as file: config = json.load(file)
		
		# ask game dir
		while True:
			dir_dir = Config.get('dir-dir', USER)
			game_dir = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr('import.choose_dir'), dir_dir)
			if not game_dir: return
			Config.set('dir-dir', game_dir)
			if exists(join(game_dir, GAME_CONFIG_FILENAME)):
				with open(join(game_dir, GAME_CONFIG_FILENAME), 'r', encoding='UTF-8') as file: old_config = json.load(file)
				if config['game-id'] == old_config['game-id']: break
				self.showError(self.tr('import.error_bad_folder'), self.tr('import.different_games'))
			else: self.showError(self.tr('import.error_bad_folder'), self.tr('msg.no_config_found'))
		
		# import settings
		config['game-type'] = old_config['game-type']
		with open(join(game_dir, GAME_CONFIG_FILENAME), 'w', encoding='UTF-8') as file: json.dump(config, file)
		
		# show success
		self.showInfo(self.tr('import.done'))
	
	def exportSettings(self):
		""" Exports settings from a chosen game folder. """
		# ask game dir
		dir_dir = Config.get('dir-dir', USER)
		game_dir = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr('export.choose_dir'), dir_dir)
		if not game_dir: return
		Config.set('dir-dir', game_dir)
		if not exists(join(game_dir, GAME_CONFIG_FILENAME)):
			self.showError(self.tr('export.error_bad_folder'), self.tr('msg.no_config_found'))
			return
		
		# do the rest
		self._exportSettings(game_dir)
	
	def _exportSettings(self, game_dir):
		# ask settings file
		cia_dir = Config.get('settings-dir', USER)
		settings_file, _ = QtWidgets.QFileDialog.getSaveFileName(self, self.tr('export.choose_file'), cia_dir, self.tr('type.settings'))
		if not settings_file: return False
		Config.set('settings-dir', dirname(settings_file))
		
		# export settings
		with open(join(game_dir, GAME_CONFIG_FILENAME), 'r', encoding='UTF-8') as file: config = json.load(file)
		del config['game-type']
		with open(settings_file, 'w', encoding='UTF-8') as file: json.dump(config, file)
		
		# show success
		self.showInfo(self.tr('export.done'))
		return True
	
	## DIALOGS ##
	
	def showAbout(self):
		""" Displays the about window. """
		msg = QtWidgets.QMessageBox()
		msg.setIconPixmap(self.icon.scaledToWidth(76))
		msg.setWindowTitle(self.tr('about.title'))
		msg.setWindowIcon(QtGui.QIcon(self.icon))
		text = '''<html><body style="text-align: center; font-size: 10pt">
					<p><b style="font-size: 14pt">%s </b><b>%s</b>
					<br/>@ <a href="%s">%s</a></p>
					<p style="text-align: center;">%s</p>
				</body></html>'''
		msg.setText(text % (APPNAME, VERSION, 'https://github.com/%s' % REPOSITORY, 'GitHub', AUTHOR))
		msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
		msg.exec_()


##########
## Main ##
##########

if __name__ == '__main__':
	app = QtWidgets.QApplication(list())
	translator = QtCore.QTranslator()
	baseTranslator = QtCore.QTranslator()
	window = MainWindow()
	app.exec_()

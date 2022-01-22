""" Author: Dominik Beese
>>> Base Plugin
<<<
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from os.path import join, basename, abspath

from copy import deepcopy
import json

import sys
sys.path.append(abspath('..'))
from MessageBoxes import MessageBoxes

def translate(context, sourceText):
	s = QtCore.QCoreApplication.translate(context, sourceText)
	if r'\n' not in s: return s
	return '<html><body><p>%s</p></body></html>' % s.replace(r'\n', '</p><p>')


class Plugin(QtWidgets.QDialog, MessageBoxes):
	"""
		The base class for all plugins.
		self.PLUGINNAME : str - short name of the game the plugin is for
		self.VERSION : str - version of the plugin
		self.GAME_FILES: list of str - game files that may be altered by the plugin
		self.parent : GameEditor - parent element of the plugin
		self.initialConfig : dict - config based on the game files, do not modify this
		self.config : dict - current config to modify
		self.updateActions - list of (list of args, function) tuples to update the GUI
	"""
	
	PLUGINNAME = ''
	VERSION = 'v0.0.-1'
	GAME_FILES = list()
	
	def __init__(self, parent, game_dir, **kwargs):
		""" Creates a tab widget, an apply and a quit button. """
		super(Plugin, self).__init__()
		
		# variables
		self.parent = parent
		self.appname = self.parent.appname
		self.game_dir = game_dir
		self.game_config_filename = self.parent.game_config_filename
		
		# components
		self.layout = QtWidgets.QVBoxLayout()
		self.setLayout(self.layout)
		
		self.tabs = self.createTabWidget()
		self.layout.addWidget(self.tabs)
		
		horizontalLayout = QtWidgets.QHBoxLayout()
		self.buttonApply = QtWidgets.QPushButton(translate('Plugin', 'Apply'))
		self.buttonApply.setFocusPolicy(Qt.NoFocus)
		self.buttonApply.clicked.connect(self.apply)
		self.buttonQuit = QtWidgets.QPushButton(translate('Plugin', 'Quit'))
		self.buttonQuit.setFocusPolicy(Qt.NoFocus)
		self.buttonQuit.clicked.connect(self.close)
		horizontalLayout.addStretch()
		horizontalLayout.addWidget(self.buttonApply)
		horizontalLayout.addWidget(self.buttonQuit)
		self.layout.addLayout(horizontalLayout)
		
		# window
		self.setWindowFlags(Qt.WindowCloseButtonHint)
		self.setWindowModality(Qt.ApplicationModal)
		self.setWindowTitle('%s - %s [%s]' % (self.PLUGINNAME, kwargs.get('title', 'Plugin'), basename(self.game_dir)))
		self.icon = kwargs.get('icon', None)
		if self.icon: self.setWindowIcon(self.icon)
	
	def run(self):
		"""
			Called to start the plugin.
			Loads the config from the config file.
			Loads the files and creates the initial config.
			Performs standard actions.
		"""
		# load and check config
		if not self.loadConfig():
			self.close()
			return False
		
		# create progress dialog
		msg = self.showProgress(translate('Plugin', 'run.loadfiles.inprogress'), maximum=100+100)
		
		# load game files
		for v in self.loadFiles():
			if isinstance(v, str): msg.setText(v)
			else: msg.setValue(v)
		
		# add missing keys from initial config to config
		self.config = {**deepcopy(self.initialConfig), **self.config}
		
		# create GUI
		self.updateActions = list()
		msg.setText(translate('Plugin', 'run.creategui.inprogress'))
		for v in self.createGUI():
			if isinstance(v, str): msg.setText(v)
			else: msg.setValue(100+v)
		self.adjustSize()
		
		# show
		self.show()
		return True
	
	## GUI ##
	
	def createGUI(self):
		""" >> Overwrite this method <<
			Creates the GUI elements.
		"""
		yield 100
	
	def updateGUI(self):
		""" >> Overwrite this method <<
			Updates the GUI elements' colors based on the current and the initial config.
		"""
		for lst, fct in self.updateActions:
			for args in lst:
				fct(*args)
	
	def addTab(self, title, layout):
		""" Adds a new tab to the tab widget. """
		self.tabs.addTab(title, layout)
	
	## ELEMENTS ##
	
	def createWidget(self, layout):
		""" Creates an empty widget with the specified layout. """
		widget = QtWidgets.QWidget()
		widget.setLayout(layout)
		widget.setMinimumSize(0, 0)
		return widget
	
	def createHorizontalSpacer(self):
		""" Creates a horizontal QSpacerItem. """
		spacer = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
		return spacer
	
	def createVerticalSpacer(self):
		""" Creates a vertical QSpacerItem. """
		spacer = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
		return spacer
	
	def createHorizontalLayout(self, spacing=10, margins=None):
		""" Creates a QHBoxLayout with the specified parameters. """
		layout = QtWidgets.QHBoxLayout()
		if spacing is not None: layout.setSpacing(spacing)
		if margins is not None:
			if isinstance(margins, tuple): layout.setContentsMargins(*margins)
			else: layout.setContentsMargins(margins, margins, margins, margins)
		return layout
	
	def createVerticalLayout(self, spacing=None, margins=None):
		""" Creates a QVBoxLayout with the specified parameters. """
		layout = QtWidgets.QVBoxLayout()
		if spacing is not None: layout.setSpacing(spacing)
		if margins is not None:
			if isinstance(margins, tuple): layout.setContentsMargins(*margins)
			else: layout.setContentsMargins(margins, margins, margins, margins)
		return layout
	
	def createGridLayout(self, horizontalSpacing=10, verticalSpacing=None, margins=None):
		""" Creates a QGridLayout with the specified parameters. """
		layout = QtWidgets.QGridLayout()
		if horizontalSpacing is not None: layout.setHorizontalSpacing(horizontalSpacing)
		if verticalSpacing is not None: layout.setVerticalSpacing(verticalSpacing)
		if margins is not None:
			if isinstance(margins, tuple): layout.setContentsMargins(*margins)
			else: layout.setContentsMargins(margins, margins, margins, margins)
		return layout
	
	def createGroupBox(self, title=None, margins=None):
		""" Creates a QGroupBox with the specified parameters. """
		groupBox = QtWidgets.QGroupBox(title)
		if margins is not None:
			if isinstance(margins, tuple): groupBox.setContentsMargins(*margins)
			else: groupBox.setContentsMargins(margins, margins, margins, margins)
		return groupBox
	
	class MyTabWidget(QtWidgets.QTabWidget):
		def __init__(self, parent, horizontalScrollBarPolicy, verticalScrollBarPolicy):
			super().__init__()
			self.parent = parent
			self.horizontalScrollBarPolicy = horizontalScrollBarPolicy
			self.verticalScrollBarPolicy = verticalScrollBarPolicy
		def addTab(self, title, layout):
			""" Adds a new tab to the tab widget. """
			widget = self.parent.createWidget(layout)
			if self.horizontalScrollBarPolicy != Qt.ScrollBarAlwaysOff or self.verticalScrollBarPolicy != Qt.ScrollBarAlwaysOff:
				scrollArea = QtWidgets.QScrollArea()
				scrollArea.setHorizontalScrollBarPolicy(self.horizontalScrollBarPolicy)
				scrollArea.setVerticalScrollBarPolicy(self.verticalScrollBarPolicy)
				scrollArea.setSizePolicy(
					QtWidgets.QSizePolicy.Fixed if self.horizontalScrollBarPolicy == Qt.ScrollBarAlwaysOff else QtWidgets.QSizePolicy.Expanding,
					QtWidgets.QSizePolicy.Fixed if self.verticalScrollBarPolicy == Qt.ScrollBarAlwaysOff else QtWidgets.QSizePolicy.Expanding
				)
				scrollArea.setWidget(widget)
				super().addTab(scrollArea, title)
			else:
				super().addTab(widget, title)
	
	def createTabWidget(self, horizontalScrollBarPolicy=Qt.ScrollBarAlwaysOff, verticalScrollBarPolicy=Qt.ScrollBarAlwaysOn):
		""" Creates a QTabWidget with the specified parameters. """
		return self.MyTabWidget(self, horizontalScrollBarPolicy, verticalScrollBarPolicy)
	
	class MyStackedWidget(QtWidgets.QStackedWidget):
		def __init__(self, parent, frameShape):
			super().__init__()
			self.parent = parent
			self.setFrameShape(frameShape)
		def createSwitcher(self, text, items):
			horizontalLayout = self.parent.createHorizontalLayout()
			horizontalLayout.addWidget(self.parent.createLabel(text, bold=True))
			comboBox = self.parent.createComboBox(
				items=items,
				args=(self,),
				fct=lambda i, sw: sw.setCurrentIndex(i)
			)
			horizontalLayout.addWidget(comboBox)
			horizontalLayout.setStretch(1, 1)
			return horizontalLayout
		
	def createStackedWidget(self, frameShape=QtWidgets.QFrame.StyledPanel):
		""" Creates a QStackedWidget with the specified parameters. """
		return self.MyStackedWidget(self, frameShape)
	
	class MyLabel(QtWidgets.QLabel):
		def __init__(self, text, tooltip, bold, alignment):
			super().__init__()
			self.bold = bold
			self.setText(text)
			self.setAlignment(self.alignment() | alignment)
			if tooltip is not None: self.setToolTip(tooltip)
		def setText(self, text):
			text = text.replace('&', '&&')
			if self.bold: text = '<b>%s</b>' % text
			super().setText(text)
		
	def createLabel(self, text, tooltip=None, bold=False, alignment=Qt.AlignLeft):
		""" Creates a QLabel with the specified style. """
		return self.MyLabel(text, tooltip, bold, alignment)
	
	class MyCheckBox(QtWidgets.QCheckBox):
		def __init__(self, text, tooltip, checked, args, fct):
			super().__init__(text.replace('&', '&&'))
			self.setCheckState(Qt.Checked if checked else Qt.Unchecked)
			if tooltip is not None: self.setToolTip(tooltip)
			self.args = args
			self.fct = fct
			self.connect()
		def connect(self):
			try: self.stateChanged.disconnect()
			except: pass
			if self.args is not None and self.fct is not None:
				self.stateChanged.connect(lambda state: self.fct(state == Qt.Checked, *self.args))
		def setArgs(self, args): self.args = args; self.connect()
		def setFct(self, fct): self.fct = fct; self.connect()
	
	def createCheckBox(self, text, tooltip=None, checked=False, args=None, fct=None):
		""" Creates a QCheckBox with the specified parameters.
			The function fct takes the new state and the args as the input.
		"""
		return self.MyCheckBox(text, tooltip, checked, args, fct)
	
	class MySpinBox(QtWidgets.QSpinBox):
		def __init__(self, tooltip, minimum, maximum, value, alignment, args, fct):
			super().__init__()
			if tooltip is not None: self.setToolTip(tooltip)
			self.setRange(minimum, maximum)
			self.setValue(value)
			self.setAlignment(alignment)
			self.args = args
			self.fct = fct
			self.connect()
		def connect(self):
			try: self.valueChanged.disconnect()
			except: pass
			if self.args is not None and self.fct is not None:
				self.valueChanged.connect(lambda value: self.fct(value, *self.args))
		def setArgs(self, args): self.args = args; self.connect()
		def setFct(self, fct): self.fct = fct; self.connect()
		def setBlockedValue(self, value):
			self.blockSignals(True)
			self.setValue(value)
			self.blockSignals(False)
	
	def createSpinBox(self, tooltip=None, minimum=0, maximum=100, value=0, alignment=Qt.AlignRight, args=None, fct=None):
		""" Creates a QSpinBox with the specified parameters.
			The function fct takes the new value and the args as the input.
		"""
		return self.MySpinBox(tooltip, minimum, maximum, value, alignment, args, fct)
	
	class MyComboBox(QtWidgets.QComboBox):
		def __init__(self, items, length, index, args, fct):
			super().__init__()
			self.setModel(QtCore.QStringListModel(items))
			#if tooltips is not None:
			#	for i, tooltip in enumerate(tooltips):
			#		self.setItemData(i, tooltip, Qt.ToolTipRole)
			if length is not None:
				self.setMinimumContentsLength(length)
				self.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLength)
			if index is not None: self.setCurrentIndex(index)
			self.args = args
			self.fct = fct
			self.connect()
		def connect(self):
			try: self.currentIndexChanged.disconnect()
			except: pass
			if self.args is not None and self.fct is not None:
				self.currentIndexChanged.connect(lambda index: self.fct(index, *self.args))
		def setArgs(self, args): self.args = args; self.connect()
		def setFct(self, fct): self.fct = fct; self.connect()
		def setBlockedCurrentIndex(self, index):
			self.blockSignals(True)
			self.setCurrentIndex(index)
			self.blockSignals(False)
	
	def createComboBox(self, items, length=None, index=None, args=None, fct=None):
		""" Creates a QComboBox with the specified parameters.
			The function fct takes the new index and the args as the input.
		"""
		return self.MyComboBox(items, length, index, args, fct)
	
	class MySwitcher(MyComboBox):
		def connect(self):
			try: self.currentIndexChanged.disconnect()
			except: pass
			if self.args is not None and self.fct is not None:
				self.currentIndexChanged.connect(lambda _: self.fct(self, *self.args))
	
	def createSwitcher(self, text, items, args=None, fct=None):
		""" Creates a QComboBox and a QLabel with the specified parameters.
			The function fct takes the new index and the args as the input.
			Returns the layout and the QComboBox.
		"""
		horizontalLayout = self.createHorizontalLayout()
		horizontalLayout.addWidget(self.createLabel(text, bold=True))
		comboBox = self.MySwitcher(
			items=items,
			length=None,
			index=None,
			args=args,
			fct=fct
		)
		comboBox.currentIndexChanged.emit(0)
		horizontalLayout.addWidget(comboBox)
		horizontalLayout.setStretch(1, 1)
		return (horizontalLayout, comboBox)
	
	class MyCustomButton(QtWidgets.QToolButton):
		def __init__(self, args, fct, icon):
			super().__init__()
			self.setIcon(self.style().standardIcon(icon))
			self.setFocusPolicy(Qt.NoFocus)
			self.args = args
			self.fct = fct
			self.connect()
		def connect(self):
			try: self.clicked.disconnect()
			except: pass
			if self.args is not None and self.fct is not None:
				self.clicked.connect(lambda _: self.fct(*self.args))
		def setArgs(self, args): self.args = args; self.connect()
		def setFct(self, fct): self.fct = fct; self.connect()
	
	def createResetButton(self, args=None, fct=None):
		""" Creates a QToolButton with a reset icon.
			The function fct takes the args as the input.
		"""
		return self.MyCustomButton(args, fct, QtWidgets.QStyle.SP_DialogResetButton)
	
	def createRandomButton(self, args=None, fct=None):
		""" Creates a QToolButton with a random icon.
			The function fct takes the args as the input.
		"""
		return self.MyCustomButton(args, fct, QtWidgets.QStyle.SP_BrowserReload)
	
	def createDeleteButton(self, args=None, fct=None):
		""" Creates a QToolButton with a delete icon.
			The function fct takes the args as the input.
		"""
		return self.MyCustomButton(args, fct, QtWidgets.QStyle.SP_DialogCancelButton)
	
	class MyControlButtons(QtWidgets.QHBoxLayout):
		def __init__(self, parent, target, allArgs, showProgress, hideTarget, noIcon, topMargin, bottomMargin, fctNone, fctAll, fctReset, fctRandom, finishArgs, finishFct):
			super().__init__()
			self.parent = parent
			self.target = target
			self.allArgs = allArgs
			self.showProgress = showProgress
			self.finishArgs = finishArgs
			self.finishFct = finishFct
			self.setContentsMargins(0, 10 if topMargin else 0, 0, 10 if bottomMargin else 0)
			if fctNone is not None:
				self.buttonNone = QtWidgets.QPushButton(translate('Plugin', 'None'))
				self.buttonNone.setFocusPolicy(Qt.NoFocus)
				self.buttonNone.clicked.connect(lambda: self.run(translate('Plugin', 'Clearing %s...'), fctNone))
				self.addWidget(self.buttonNone)
			if fctAll is not None:
				self.buttonAll = QtWidgets.QPushButton(translate('Plugin', 'All'))
				self.buttonAll.setFocusPolicy(Qt.NoFocus)
				self.buttonAll.clicked.connect(lambda: self.run(translate('Plugin', 'Setting %s...'), fctAll))
				self.addWidget(self.buttonAll)
			if fctReset is not None:
				self.buttonReset = QtWidgets.QPushButton(translate('Plugin', 'Reset %s') % target if not hideTarget else translate('Plugin', 'Reset'))
				if not noIcon: self.buttonReset.setIcon(self.parent.style().standardIcon(QtWidgets.QStyle.SP_DialogResetButton))
				self.buttonReset.setFocusPolicy(Qt.NoFocus)
				self.buttonReset.clicked.connect(lambda: self.run(translate('Plugin', 'Resetting %s...'), fctReset))
				self.addWidget(self.buttonReset)
			if fctRandom is not None:
				self.buttonRandom = QtWidgets.QPushButton(translate('Plugin', 'Randomize %s') % target if not hideTarget else translate('Plugin', 'Randomize'))
				if not noIcon: self.buttonRandom.setIcon(self.parent.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
				self.buttonRandom.setFocusPolicy(Qt.NoFocus)
				self.buttonRandom.clicked.connect(lambda: self.run(translate('Plugin', 'Randomizing %s...'), fctRandom))
				self.addWidget(self.buttonRandom)
			self.addItem(self.parent.createHorizontalSpacer())
		def run(self, text, fct):
			if self.showProgress: msg = self.parent.showProgress(text % self.target, maximum=len(self.allArgs))
			for args in self.allArgs:
				fct(*args)
				if self.showProgress: msg.incValue()
			if self.finishFct is not None:
				self.finishFct(*self.finishArgs)
		def setTarget(self, target): self.target = target
		def setAllArgs(self, allArgs): self.allArgs = allArgs
		def setFinishArgs(self, finishArgs): self.finishArgs = finishArgs
	
	def createControlButtons(self, target, allArgs, showProgress=True, hideTarget=False, noIcon=False, topMargin=True, bottomMargin=False, fctNone=None, fctAll=None, fctReset=None, fctRandom=None, finishArgs=None, finishFct=None):
		""" Creates a none, all, reset, and random button if specified.
			When clicked, the buttons apply fctReset (or fctRandom) to all elements of allArgs.
		"""
		return self.MyControlButtons(self, target, allArgs, showProgress, hideTarget, noIcon, topMargin, bottomMargin, fctNone, fctAll, fctReset, fctRandom, finishArgs, finishFct)
	
	## ACTIONS ##
	
	def closeEvent(self, event):
		""" Calls quit. """
		self.quit()
		event.accept()
	
	def apply(self):
		""" Applies the modifications to the config and the game files. """
		# ask to proceed
		if not self.askWarning(translate('Plugin', 'apply.warning')): return
		
		# update game files
		self.doStandardActions()
		msg = self.showProgress(translate('Plugin', 'apply.inprogress'), maximum=100)
		for v in self.saveFiles(): msg.setValue(v)
		
		# update config
		self.initialConfig.update(deepcopy(self.config))
		with open(join(self.game_dir, self.game_config_filename), 'w', encoding='UTF-8') as file:
			json.dump(self.config, file)
		
		# update GUI
		self.updateGUI()
		
		# show success
		self.showInfo(translate('Plugin', 'apply.done'))
	
	def quit(self):
		""" Closes the plugin. Asks whether to apply the changes if neccessary. """
		if not hasattr(self, 'initialConfig'): return
		# check modifications
		IGNORE_KEYS = ['game-type', 'game-id', 'editor-version', 'plugin-version', 'game-files']
		cmp_current = {k: v for k, v in self.config.items() if k not in IGNORE_KEYS}
		cmp_initial = {k: v for k, v in self.initialConfig.items() if k not in IGNORE_KEYS}
		if cmp_current != cmp_initial:
			if self.askWarning(translate('Plugin', 'quit.warning_unsaved_changes_ask_apply')):
				self.apply()
	
	## CONFIG ##
	
	def loadConfig(self):
		""" Loads the config. Updates the version or shows an error if neccessary. """
		def ver2int(s):
			if s[0] == 'v': s = s[1:]
			v = s.split('.')
			return sum([int(k) * 100**(len(v)-i) for i, k in enumerate(v)])
		
		# read config
		with open(join(self.game_dir, self.game_config_filename), 'r', encoding='UTF-8') as file: config = json.load(file)
		
		# check and set version
		if 'plugin-version' not in config: config['plugin-version'] = '0.0.-1'
		config_version = ver2int(config['plugin-version'])
		current_version = ver2int(self.VERSION)
		if config_version > current_version:
			self.showError(translate('Plugin', 'error.version_too_old'))
			return False
		if config_version < current_version:
			config = self.updateConfig(config)
		config['plugin-version'] = self.VERSION
		
		# set game files
		config['game-files'] = self.GAME_FILES
		
		# set config
		self.config = config
		return True
	
	def updateConfig(self, config):
		""" >> Overwrite this method <<
			Updates the config from an old version to the current version.
		"""
		return config
	
	## FILES ##
	
	def doStandardActions(self):
		""" >> Overwrite this method (optional) <<
			Performs standard actions such as modifying a file to add a watermark.
		"""
		pass
	
	def loadFiles(self):
		""" >> Overwrite this method <<
			Loads the game files and creates the initial config.
		"""
		self.initialConfig = dict()
		yield 100
	
	def saveFiles(self):
		""" >> Overwrite this method <<
			Writes the game files based on the current config.
			Yields progress values from 0 to 100 percent.
		"""
		yield 100

if __name__ == '__main__':
	app = QtWidgets.QApplication(list())
	translator = QtCore.QTranslator()
	baseTranslator = QtCore.QTranslator()
	class Parent:
		appname = 'Game Editor'
		game_config_filename = 'ge-config.json'
	window = Plugin(Parent(), 'C:\Test-Game')
	window.run()
	app.exec_()

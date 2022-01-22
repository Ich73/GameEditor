""" Author: Dominik Beese
>>> DQM2 Plugin
<<<
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QEvent

from os import rename, remove
from os.path import join, abspath, dirname
from hashlib import md5
from subprocess import run
from base64 import b85decode
import random

try:
	from Plugins.BasePlugin import Plugin
	from JTools import *
except:
	import sys
	sys.path.append(abspath('..'))
	from BasePlugin import Plugin
	from JTools import *


class Editor(Plugin):
	
	PLUGINNAME = 'DQM2'
	VERSION = 'v0.1.0'
	GAME_FILES = [
		join('ExtractedRomFS', 'data', 'Layout', 'picture', 'title_lower_bg.arc'),
		*[join('ExtractedRomFS', 'data', 'Param', f) for f in [
			'FixItemTbl.bin',
			*['StoreTbl_%s_MAA.bin'    % n for n in 'BOOK|GENERAL|HIGH_BOOK|HIGH_ITEM|HIGH_MEAT|HIGH_WEAPON|KEY'.split('|')],
			*['StoreTbl_ITEM_%s.bin'   % n for n in 'ATA|ATB|BTA|BTB|BTC|CTA|CTB|CTD|CTE|DTA|DTB|DTC|FTA|MAA|W'.split('|')],
			*['StoreTbl_WEAPON_%s.bin' % n for n in 'ATB|BTB|BTC|CTA|CTD|CTE|DTC|FTA|MAA'.split('|')],
			*['StoreTbl_%s.bin'        % n for n in 'MASTER|MATERIAL_ATB|MEAT_MAA|WIFI'.split('|')],
			'SkillTbl.bin',
			'SkillEvoTbl.bin',
			'SkillSpEvoTbl.bin'
		]]
	]
	
	def __init__(self, *args, **kwargs):
		""" Plugin for DQM2.
			self.data_folder - path to the ExtractedRomFS\data folder
			self.SEP - separator token for binJ files
			self.TABLE - decoding table for binJ files
		"""
		super(Editor, self).__init__(*args, **kwargs)
		self.setMinimumSize(516, 540)
		self.data_folder = join(self.game_dir, 'ExtractedRomFS', 'data')
		self.update_actions = list()
		self.SEP = b'\xe3\x1b'
		tempfile = join(self.game_dir, 'decoding-table.txt')
		with open(tempfile, 'w', encoding='UTF-8') as file: file.write(DECODING_TABLE)
		self.TABLE = parseDecodingTable(tempfile)
		remove(tempfile)
	
	def tr(self, sourceText):
		s = QtCore.QCoreApplication.translate('Editor', sourceText)
		if r'\n' not in s: return s
		return '<html><body><p>%s</p></body></html>' % s.replace(r'\n', '</p><p>')
	
	## GUI ##
	
	def createGUI(self):
		""" Creates the GUI elements for the tabs. """
		N = 3
		
		### TAB: Skills ###
		
		def skills(tabName):
			# skill names
			skills = [(id, skill) for id, skill in enumerate(self.skillname) if skill is not None]
			
			# action names and descriptions
			valid_ids = list(range(3, 202+1)) + list(range(209, 311+1)) + list(range(322, 345+1)) + [350, 351, 352, 357, 358, 359, 360]
			actions = [
				(('a', id), action + ('', '*')[help is None], help or self.tr('(Unused)')) # add * to name of unused actions
				for id, (action, help) in enumerate(zip(self.actionname, self.actionhelp))
				if action is not None and id in valid_ids
			]
			
			# trait names and descriptions
			traits = [
				(('t', id), trait + ('', '*')[help is None], help or self.tr('(Unused)')) # add * to name of unused traits
				for id, (trait, help) in enumerate(zip(self.traitname, self.traithelp))
				if trait is not None
			]
			
			# combined actions and traits
			actionTraits = [((None, None), '-----', None)] + actions + traits
			actionTraitsName = [name for _, name, _ in actionTraits]
			actionTraitsHelp = [help for _, _, help in actionTraits]
			actionTraitsLength = max(len(name) for _, name, _ in actionTraits)
			actionTraitsLookup = {(t, id): i for i, ((t, id), _, _) in enumerate(actionTraits)}
			
			# tab widget
			tabWidget = self.createTabWidget(verticalScrollBarPolicy=Qt.ScrollBarAlwaysOff)
			
			
			## SUB-TAB: Skill Sets ##
			
			def skillSets(subTabName):
				# vertical layout and group box
				layout = self.createVerticalLayout()
				groupBox = self.createGroupBox()
				layout.addWidget(groupBox)
				
				# gui actions
				def spinAction(value, i, j, pageArgs):
					spinBox = pageArgs[j][2]
					set = self.config['skills']['sets'][i]
					# verify valid action
					if j >= len(set): return # no action
					if j > 0 and j-1 < len(set) and value <= set[j-1]['sp']: spinBox.setBlockedValue(set[j-1]['sp']+1); return # too less
					if j+1 < len(set) and value >= set[j+1]['sp']: spinBox.setBlockedValue(set[j+1]['sp']-1); return # too much
					# change config
					set[j]['sp'] = value
					# update
					if j == len(set)-1:
						for k in range(j, 10):
							pageArgs[k][2].setBlockedValue(set[-1]['sp'])
					update(*pageArgs)
				def comboAction(index, i, j, pageArgs):
					comboBox = pageArgs[j][3]
					set = self.config['skills']['sets'][i]
					# verify valid action
					if index == 0 and j == 0: comboBox.setBlockedCurrentIndex(actionTraitsLookup[(set[j]['t'], set[j]['id'])]); return
					# change config and update
					newT, newId = actionTraits[index][0]
					if j < len(set):
						if index != 0: # normal -> update
							set[j]['id'] = newId
							set[j]['t'] = newT
						else: # none -> remove current and higher
							for _ in range(len(set)-j): set.pop()
							for k in range(j, 10):
								pageArgs[k][2].setBlockedValue(set[-1]['sp'])
								pageArgs[k][3].setBlockedCurrentIndex(0)
					else: # add action(s)
						for k in range(len(set), j+1):
							newSp = set[-1]['sp']+1
							set += [{'sp': newSp, 'id': newId, 't': newT}]
							pageArgs[k][2].setBlockedValue(newSp)
							pageArgs[k][3].setBlockedCurrentIndex(index)
					update(*pageArgs)
				
				# update and switch
				def update(*pageArgs):
					for i, j, spinBox, comboBox, resetButton, _, deleteButton, _ in pageArgs:
						set = self.config['skills']['sets'][i]
						initialSet = self.initialConfig['skills']['sets'][i]
						bSp = (set[j]['sp'] if j < len(set) else None) != (initialSet[j]['sp'] if j < len(initialSet) else None)
						bT  = (set[j]['t']  if j < len(set) else None) != (initialSet[j]['t']  if j < len(initialSet) else None)
						bId = (set[j]['id'] if j < len(set) else None) != (initialSet[j]['id'] if j < len(initialSet) else None)
						spinStyleSheet = 'QSpinBox { color: %s; }' % ('red' if bSp else 'inherit')
						comboStyleSheet = 'QComboBox { color: %s; }' % ('red' if bT or bId else 'inherit')
						if spinBox.styleSheet() != spinStyleSheet: spinBox.setStyleSheet(spinStyleSheet)
						if comboBox.styleSheet() != comboStyleSheet: comboBox.setStyleSheet(comboStyleSheet)
						spinBox.setEnabled(j < len(set))
						resetButton.setEnabled(bSp or bT or bId)
						deleteButton.setEnabled(j > 0 and j < len(set))
				def switch(switcher, *allArgs):
					pageArgs = allArgs[switcher.currentIndex()] # get current page
					set = self.config['skills']['sets'][pageArgs[0][0]] # get current set
					for i, j, spinBox, comboBox, resetButton, randomButton, deleteButton, controlButtons in pageArgs:
						# update args
						args = (i, j, pageArgs)
						spinBox.setArgs(args)
						comboBox.setArgs(args)
						resetButton.setArgs(args)
						randomButton.setArgs(args)
						deleteButton.setArgs(args)
						controlButtons.setAllArgs([pageArgs])
						# update values
						spinBox.setBlockedValue(set[j if j < len(set) else -1]['sp'])
						comboBox.setBlockedCurrentIndex(actionTraitsLookup[(set[j]['t'], set[j]['id'])] if j < len(set) else 0)
						update(*pageArgs)
				
				# single actions
				def resetSingleAction(i, j, pageArgs):
					set = self.config['skills']['sets'][i]
					initialSet = self.initialConfig['skills']['sets'][i]
					# update config
					if j < len(set):
						if j < len(initialSet): set[j] = dict(initialSet[j]) # normal -> replace by initial
						else: # more than initial set -> remove current and higher
							for _ in range(len(set)-j): set.pop()
					else: # restore all unrestored
						for k in range(len(set), min(j+1, len(initialSet))): set += [dict(initialSet[k])]
					# fix sp
					for k in range(min(len(set)-1, j)-1, -1, -1):
						if set[k]['sp'] >= set[min(j, len(set)-1)]['sp']: set[k]['sp'] = set[min(j, len(set)-1)]['sp']-j+k
						else: break
					for k in range(j+1, len(set)):
						if set[k]['sp'] <= set[j]['sp']: set[k]['sp'] = set[j]['sp']-j+k
						else: break
					# update gui
					for j in range(10):
						pageArgs[j][2].setBlockedValue(set[j if j < len(set) else -1]['sp'])
						pageArgs[j][3].setBlockedCurrentIndex(actionTraitsLookup[(set[j]['t'], set[j]['id'])] if j < len(set) else 0)
					update(*pageArgs)
				def randomSingleAction(i, j, pageArgs):
					set = self.config['skills']['sets'][i]
					# add action
					for k in range(min(j, len(set)), j+1):
						# add action
						if k >= len(set): set += [dict()]
						# create random values
						newSp = random.randint(set[max(k-1, 0)]['sp']+1, set[k+1]['sp']-1 if k+1 < len(set) else 0xFF-9+k)
						newT, newId = random.choice(actionTraits[1:])[0]
						# update config
						set[k]['sp'] = newSp
						set[k]['id'] = newId
						set[k]['t']  = newT
					# update gui
					for j in range(10):
						pageArgs[j][2].setBlockedValue(set[j if j < len(set) else -1]['sp'])
						pageArgs[j][3].setBlockedCurrentIndex(actionTraitsLookup[(set[j]['t'], set[j]['id'])] if j < len(set) else 0)
					update(*pageArgs)
				def deleteSingleAction(i, j, pageArgs):
					set = self.config['skills']['sets'][i]
					# add action
					for _ in range(len(set)-j): set.pop()
					for k in range(j, 10):
						pageArgs[k][2].setBlockedValue(set[-1]['sp'])
						pageArgs[k][3].setBlockedCurrentIndex(0)
					update(*pageArgs)
				
				# page actions
				def resetPageAction(*pageArgs):
					i = pageArgs[0][0]
					self.config['skills']['sets'][i] = [dict(d) for d in self.initialConfig['skills']['sets'][i]]
					# do not update (page may not be visible)
				def randomPageAction(*pageArgs):
					# create random size and max sp
					newSize = random.choices([3, 4, 5, 6, 7, 8, 9, 10], [1, 2, 4, 8, 20, 50, 150, 150])[0]
					maxSp = random.randint(newSize*5, 0xFF)
					# create sp based on ^1.8 function and randomize with gaussian distribution between mids
					newSp = [int((maxSp**(1/1.8)*(k+1)/newSize)**1.8) for k in range(newSize)]
					midSp = [(p+c)//2 for p, c in zip([0]+newSp[:-1], newSp)]
					newSp = [
						random.choices(
							range(lo+1, hi+1),
							[1/(2*random._pi)**0.5 * random._e**(-0.5*((k-(hi-lo-1)/2)/(hi-lo)*5)**2) for k in range(hi-lo)]
						)[0] for lo, sp, hi in zip(midSp, newSp, midSp[1:]+[0xFF])
					]
					# create random actions
					newTId = [random.choice(actionTraits[1:])[0] for _ in range(newSize)]
					# update config
					self.config['skills']['sets'][pageArgs[0][0]] = [
						{'sp': sp, 'id': id, 't': t}
						for sp, (t, id) in zip(newSp, newTId)
					]
					# do not update (page may not be visible)
				
				# inner layout
				innerLayout = self.createVerticalLayout()
				groupBox.setLayout(innerLayout)
				
				# grid layout
				gridLayout = self.createGridLayout(margins=0)
				innerLayout.addWidget(self.createWidget(gridLayout))
				
				# header
				gridLayout.addWidget(self.createLabel(self.tr('SP'), bold=True, alignment=Qt.AlignCenter), 0, 1)
				gridLayout.addWidget(self.createLabel(self.tr('Action/Trait'), bold=True), 0, 2)
				
				# actions/traits
				rawArgs = list()
				for j in range(10):
					# number
					label = self.createLabel('%d.' % (j+1), alignment=Qt.AlignRight)
					gridLayout.addWidget(label, j+1, 0)
					
					# quantity
					spinBox = self.createSpinBox(
						minimum=1,
						maximum=0xFF,
						fct=spinAction
					)
					gridLayout.addWidget(spinBox, j+1, 1)
					
					# action/trait
					comboBox = self.createComboBox(
						items=actionTraitsName,
						#tooltips=actionTraitsHelp,
						length=actionTraitsLength,
						fct=comboAction
					)
					gridLayout.addWidget(comboBox, j+1, 2)
					
					# reset
					resetButton = self.createResetButton(fct=resetSingleAction)
					gridLayout.addWidget(resetButton, j+1, 3)
					
					# random
					randomButton = self.createRandomButton(fct=randomSingleAction)
					gridLayout.addWidget(randomButton, j+1, 4)
					
					# delete
					deleteButton = self.createDeleteButton(fct=deleteSingleAction)
					gridLayout.addWidget(deleteButton, j+1, 5)
					
					# args
					rawArgs.append((j, spinBox, comboBox, resetButton, randomButton, deleteButton))
				
				# (inner) control buttons
				controlButtons = self.createControlButtons(
					target=None,
					allArgs=None,
					showProgress=False,
					hideTarget=True,
					noIcon=True,
					topMargin=False,
					fctReset=resetPageAction,
					fctRandom=randomPageAction,
					finishArgs=None,
					finishFct=switch
				)
				innerLayout.addWidget(self.createWidget(controlButtons))
				
				# args
				allArgs = list()
				for i, set in enumerate(self.config['skills']['sets']):
					if set is None: continue # skip undefined sets
					pageArgs = [(i, *args, controlButtons) for args in rawArgs]
					allArgs.append(pageArgs)
				self.updateActions.append((allArgs, update))
				
				# switcher
				switcherLayout, switcher = self.createSwitcher(
					text=self.tr('Skill'),
					items=[name for name, set in zip(self.skillname, self.config['skills']['sets']) if set is not None],
					args=allArgs,
					fct=switch
				)
				layout.insertLayout(0, switcherLayout)
				self.updateActions.append(([(switcher, *allArgs)], switch))
				controlButtons.setFinishArgs((switcher, *allArgs))
				
				# (outer) control buttons
				controlButtons = self.createControlButtons(
					target=self.tr('Skill Sets'),
					allArgs=allArgs,
					topMargin=False,
					fctReset=resetPageAction,
					fctRandom=randomPageAction,
					finishArgs=(switcher, *allArgs),
					finishFct=switch
				)
				layout.addWidget(self.createWidget(controlButtons))
				return subTabName, layout
			
			# add tab
			tabWidget.addTab(*skillSets(self.tr('Skill Sets')))
			
			# main layout
			mainLayout = self.createVerticalLayout(spacing=0)
			mainLayout.addWidget(tabWidget)
			return tabName, mainLayout
		
		# skills
		self.addTab(*skills(self.tr('Skills')))
		yield int(1/N*100)
		
		
		### TAB: Shops ###
		
		def shops(tabName):
			# item names
			valid_ids = list(range(0, 511+1)) # items that can be bought in shops
			unused_ids = [92, 261, 268, 329, 330, 331, 575, 576, 577, 578] # add * to name of unused items
			items = [
				(
					id,
					item + ('', '*')[id in unused_ids],
					help or (self.tr('(Unused)') if id in unused_ids else self.tr('(No description available)'))
				)
				for id, (item, help) in enumerate(zip(self.itemname, self.itemhelp))
				if item is not None and id in valid_ids
			]
			
			# actions
			def checkAction(checked, i, id, checkBox, label):
				if id in self.config['shops'][i]['ids']:
					self.config['shops'][i]['ids'].remove(id)
				else: self.config['shops'][i]['ids'].append(id)
				update(i, id, checkBox, label)
			def update(i, id, checkBox, label):
				bId = (id in self.config['shops'][i]['ids']) != (id in self.initialConfig['shops'][i]['ids'])
				styleSheet = 'color: %s;' % ('red' if bId else 'inherit')
				if checkBox.styleSheet() != styleSheet: checkBox.setStyleSheet(styleSheet)
				bAll = sorted(self.config['shops'][i]['ids']) != sorted(self.initialConfig['shops'][i]['ids'])
				label.setText(str(len(self.config['shops'][i]['ids'])))
				styleSheet = 'color: %s;' % ('red' if bAll else 'inherit')
				if label.styleSheet() != styleSheet: label.setStyleSheet(styleSheet)
			def noneAction(*pageArgs):
				for i, id, checkBox, label in pageArgs:
					checkBox.setChecked(False)
					update(i, id, checkBox, label)
				self.config['shops'][i]['ids'] = list()
			def allAction(*pageArgs):
				for i, id, checkBox, label in pageArgs:
					checkBox.setChecked(True)
					update(i, id, checkBox, label)
				self.config['shops'][i]['ids'] = [id for id, _, _ in items]
			def resetAction(*pageArgs):
				newIds = list()
				for i, id, checkBox, label in pageArgs:
					newFlag = id in self.initialConfig['shops'][i]['ids']
					checkBox.setChecked(newFlag)
					if newFlag: newIds.append(id)
					update(i, id, checkBox, label)
				self.config['shops'][i]['ids'] = newIds
			def randomAction(*pageArgs):
				k = random.randint(1, len(items)//10)
				newIds = sorted([id for id, _, _ in random.sample(items, k=k)])
				for i, id, checkBox, label in pageArgs:
					checkBox.setChecked(id in newIds)
					update(i, id, checkBox, label)
				self.config['shops'][i]['ids'] = newIds
			
			# vertical layout and stacked widget
			layout = self.createVerticalLayout(margins=0)
			stackedWidget = self.createStackedWidget()
			layout.addWidget(stackedWidget)
			
			# shops
			allArgs = list()
			for i, shop in enumerate(self.config['shops']):
				# inner layout
				innerLayout = self.createVerticalLayout()
				stackedWidget.addWidget(self.createWidget(innerLayout))
				
				# info
				infoLayout = self.createHorizontalLayout(spacing=4, margins=0)
				infoLayout.addWidget(self.createLabel(self.tr('Number of Items:'), bold=True))
				label = self.createLabel(str(len(shop['ids'])))
				infoLayout.addWidget(label)
				infoLayout.addItem(self.createHorizontalSpacer())
				innerLayout.addWidget(self.createWidget(infoLayout))
				
				# grid layout
				gridLayout = self.createGridLayout(margins=0)
				innerLayout.addWidget(self.createWidget(gridLayout))
				
				# items
				pageArgs = list()
				for j, (id, item, help) in enumerate(items):
					# item flag
					checkBox = self.createCheckBox(
						text=item,
						tooltip=help,
						checked=id in shop['ids'],
						fct=checkAction
					)
					gridLayout.addWidget(checkBox, j // 2, j % 2)
					
					# args
					args = (i, id, checkBox, label)
					checkBox.setArgs(args)
					update(*args)
					pageArgs.append(args)
				
				# control buttons
				controlButtons = self.createControlButtons(
					target=shop['loc'],
					allArgs=[pageArgs],
					showProgress=False,
					hideTarget=True,
					noIcon=True,
					topMargin=False,
					fctNone=noneAction,
					fctAll=allAction,
					fctReset=resetAction,
					fctRandom=randomAction
				)
				innerLayout.insertWidget(0, self.createWidget(controlButtons))
				
				allArgs.append(pageArgs)
			self.updateActions.append(([x for y in allArgs for x in y], update))
			
			# widget switcher
			widgetSwitcher = stackedWidget.createSwitcher(
				text=self.tr('Location'),
				items=[shop['loc'] for shop in self.config['shops']]
			)
			layout.insertLayout(0, widgetSwitcher)
			
			# controls
			controlButtons = self.createControlButtons(
				target=tabName,
				allArgs=allArgs,
				fctReset=resetAction,
				fctRandom=randomAction
			)
			
			# main layout
			mainLayout = self.createVerticalLayout(spacing=0)
			mainLayout.addWidget(self.createWidget(layout))
			mainLayout.addWidget(self.createWidget(controlButtons))
			return tabName, mainLayout
		
		# shops
		self.addTab(*shops(self.tr('Shops')))
		yield int(2/N*100)
		
		
		### TAB: Chests ###
		
		def chests(tabName):
			# item names
			valid_ids = list(range(0, 491+1)) + [0x1FF] # items that can be found in treasure chests
			unused_ids = [92, 261, 268, 329, 330, 331, 575, 576, 577, 578] # add * to name of unused items
			mod_limits = {k: 3 for k in list(range(112, 233+1)) + list(range(485, 491+1))} # limit mod of weapons to 3
			mod_limit = 0x7FFF
			items = [(0, self.tr('(Empty Chest)'), None), (0x1FF, self.tr('Money (G)'), None)]
			items += [
				(
					id,
					item + ('', '*')[id in unused_ids],
					help or (self.tr('(Unused)') if id in unused_ids else self.tr('(No description available)'))
				)
				for id, (item, help) in enumerate(zip(self.itemname, self.itemhelp))
				if item is not None and id in valid_ids
			]
			itemsName = [name for _, name, _ in items]
			itemsHelp = [help for _, _, help in items]
			itemsLength = max(len(name) for _, name, _ in items)
			itemsLookup = {id: i for i, (id, _, _) in enumerate(items)}
			
			# actions
			def comboAction(index, i, comboBox, spinBox, resetButton, randomButton):
				self.config['chests'][i]['id'] = items[index][0]
				spinBox.setMaximum(mod_limits.get(items[index][0], mod_limit))
				update(i, comboBox, spinBox, resetButton, randomButton)
			def spinAction(value, i, comboBox, spinBox, resetButton, randomButton):
				self.config['chests'][i]['mod'] = value
				update(i, comboBox, spinBox, resetButton, randomButton)
			def update(i, comboBox, spinBox, resetButton, randomButton):
				bId = self.config['chests'][i]['id'] != self.initialConfig['chests'][i]['id']
				bMod = self.config['chests'][i]['mod'] != self.initialConfig['chests'][i]['mod']
				comboStyleSheet = 'QComboBox { color: %s; }' % ('red' if bId else 'inherit')
				if comboBox.styleSheet() != comboStyleSheet: comboBox.setStyleSheet(comboStyleSheet)
				spinStyleSheet = 'QSpinBox { color: %s; }' % ('red' if bMod else 'inherit')
				if spinBox.styleSheet() != spinStyleSheet: spinBox.setStyleSheet(spinStyleSheet)
				resetButton.setEnabled(bId or bMod)
			def resetAction(i, comboBox, spinBox, resetButton, randomButton):
				newId = self.initialConfig['chests'][i]['id']
				newMod = self.initialConfig['chests'][i]['mod']
				comboBox.setCurrentIndex(itemsLookup[newId])
				spinBox.setValue(newMod)
				self.config['chests'][i]['id'] = newId
				self.config['chests'][i]['mod'] = spinBox.value()
				update(i, comboBox, spinBox, resetButton, randomButton)
			def randomAction(i, comboBox, spinBox, resetButton, randomButton):
				newId = random.choice(items)[0]
				if newId in mod_limits: newMod = random.choices(range(4), weights=[0.4, 0.3, 0.2, 0.1])[0] # weapons
				elif newId == 0x1FF: newMod = random.randint(0, mod_limit) # money
				else: newMod = int(1+1000-random.randint(0, 1000**100)**0.01) # other items
				comboBox.setCurrentIndex(itemsLookup[newId])
				spinBox.setValue(newMod)
				update(i, comboBox, spinBox, resetButton, randomButton)
			
			# grid layout
			layout = self.createGridLayout(margins=0)
			
			# header
			layout.addWidget(self.createLabel(self.tr('Location'), bold=True), 0, 0)
			layout.addWidget(self.createLabel(self.tr('Item'), bold=True), 0, 1)
			layout.addWidget(self.createLabel(self.tr('Qty/Stars'), bold=True, alignment=Qt.AlignCenter), 0, 2)
			
			# chests
			allArgs = list()
			for i, chest in enumerate(self.config['chests']):
				# location
				label = self.createLabel('%s #%d' % (chest['loc'][0], chest['loc'][1]))
				layout.addWidget(label, i+1, 0)
				
				# item
				comboBox = self.createComboBox(
					items=itemsName,
					#tooltips=itemsHelp,
					length=itemsLength,
					index=itemsLookup[chest['id']],
					fct=comboAction
				)
				layout.addWidget(comboBox, i+1, 1)
				
				# quantity
				spinBox = self.createSpinBox(
					minimum=0,
					maximum=mod_limits.get(chest['id'], mod_limit),
					value=chest['mod'],
					fct=spinAction
				)
				layout.addWidget(spinBox, i+1, 2)
				
				# reset
				resetButton = self.createResetButton(fct=resetAction)
				layout.addWidget(resetButton, i+1, 3)
				
				# random
				randomButton = self.createRandomButton(fct=randomAction)
				layout.addWidget(randomButton, i+1, 4)
				
				# args
				args = (i, comboBox, spinBox, resetButton, randomButton)
				comboBox.setArgs(args)
				spinBox.setArgs(args)
				resetButton.setArgs(args)
				randomButton.setArgs(args)
				update(*args)
				allArgs.append(args)
			self.updateActions.append((allArgs, update))
			
			# controls
			controlButtons = self.createControlButtons(
				target=tabName,
				allArgs=allArgs,
				fctReset=resetAction,
				fctRandom=randomAction
			)
			
			# main layout
			mainLayout = self.createVerticalLayout(spacing=0)
			mainLayout.addWidget(self.createWidget(layout))
			mainLayout.addWidget(self.createWidget(controlButtons))
			return tabName, mainLayout
		
		# chests
		self.addTab(*chests(self.tr('Chests')))
		yield int(3/N*100)
		
		# finished
		yield 100
	
	## CONFIG ##
	
	def updateConfig(self, config):
		""" Updates the config from an old version to the current version. """
		# no special changes at the moment
		return config
	
	## FILES ##
	
	def doStandardActions(self):
		""" Modifies title_lower_bg.arc """
		# write copyright.bclim into title_lower_bg.arc
		filename = join(self.data_folder, 'Layout', 'picture', 'title_lower_bg.arc')
		with open(filename, 'rb') as file: bytes = file.read()
		bytes = bytes[:-len(COPYRIGHT_BCLIM)] + COPYRIGHT_BCLIM
		with open(filename, 'wb') as file: file.write(bytes)
	
	def loadFiles(self):
		""" Loads the game files and creates the initial config. """
		self.initialConfig = dict()
		N = 11
		
		# load translations from messages
		def nonify(l, lf=False): return [(x if not lf else x.replace('[LF]', '\n')) or None for x in l]
		self.monstername = nonify(self.readFromBinJ('msg_monstername', indices=(0, 901)))
		yield int(1/N*100)
		self.itemname = nonify(self.readFromBinJ('msg_itemname', indices=(0, 639)))
		yield int(2/N*100)
		self.itemhelp = nonify(self.readFromBinJ('msg_itemhelp', indices=(0, 639)), lf=True)
		yield int(3/N*100)
		self.skillname = nonify(self.readFromBinJ('msg_skillname', indices=(0, 384)))
		yield int(4/N*100)
		self.actionname = nonify(self.readFromBinJ('msg_actionname'))
		yield int(5/N*100)
		self.actionhelp = nonify(self.readFromBinJ('msg_actionhelp'), lf=True)
		yield int(6/N*100)
		self.traitname = [None] + nonify(self.readFromBinJ('msg_tokusei', indices=(1, 345)))
		yield int(7/N*100)
		self.traithelp = [None] + nonify(self.readFromBinJ('msg_library', indices=(100, 444)), lf=True)
		yield int(8/N*100)
		
		# load skills
		self.initialConfig['skills'] = dict()
		with open(join(self.data_folder, 'Param', 'SkillTbl.bin'), 'rb') as file: data = file.read()
		self.initialConfig['skills']['sets'] = [
			[ # list of actions/traits for one skill
				{
					'sp': data[0x08+n*0x84+k], # required skill points
					'id': int.from_bytes(data[0x08+n*0x84+0x0A+k*0x0A:0x08+n*0x84+0x0A+k*0x0A+2], 'little') # id of action or trait
						or int.from_bytes(data[0x08+n*0x84+0x6E+k*0x02:0x08+n*0x84+0x6E+k*0x02+2], 'little'),
					't': 'a' if data[0x08+n*0x84+0x0A+k*0x0A:0x08+n*0x84+0x0A+k*0x0A+2] != b'\x00\x00' else 't', # type: action or trait
				}
				for k in range(10)
				if k == 0 or data[0x08+n*0x84+k] != data[0x08+n*0x84+k-1]
			] if data[0x08+n*0x84] != 0 else None
			for n in range((len(data) - 0x08) // 0x84)
		]
		yield int(8.5/N*100)
		with open(join(self.data_folder, 'Param', 'SkillEvoTbl.bin'), 'rb') as file: data = file.read()
		self.initialConfig['skills']['evo'] = [
			int.from_bytes(data[0x08+n*0x06+0x04:0x08+n*0x06+0x04+2], 'little') # id of evolution skill
			if int.from_bytes(data[0x08+n*0x06+0x02:0x08+n*0x06+0x02+2], 'little') == 1 # flag is set
			else False # skill cannot evolve
			for n in range((len(data) - 0x08) // 0x06)
		]
		yield int(8.7/N*100)
		with open(join(self.data_folder, 'Param', 'SkillSpEvoTbl.bin'), 'rb') as file: data = file.read()
		self.initialConfig['skills']['spevo'] = [
			{
				'src': [ # ids of skills to combine
					int.from_bytes(data[0x08+n*0x1C+k*0x02:0x08+n*0x1C+k*0x02+2], 'little')
					for k in range(6)
				],
				'sp': [ # sp required on each skill
					int.from_bytes(data[0x08+n*0x1C+0x0C+k*0x02:0x08+n*0x1C+0x0C+k*0x02+2], 'little')
					for k in range(6)
				],
				'res': int.from_bytes(data[0x08+n*0x1C+0x18:0x08+n*0x1C+0x18+2], 'little'), # resulting skill
			}
			for n in range((len(data) - 0x08) // 0x1C)
		]
		yield int(9/N*100)
		
		# load chests
		with open(join(self.data_folder, 'Param', 'FixItemTbl.bin'), 'rb') as file: data = file.read()
		self.initialConfig['chests'] = [
			{
				'loc': [data[n*0x10+0x00:n*0x10+0x00+5].decode(), data[n*0x10+0x08]],
				'id': int.from_bytes(data[n*0x10+0x0C:n*0x10+0x0C+2], 'little'),
				'mod': int.from_bytes(data[n*0x10+0x0E:n*0x10+0x0E+2], 'little'),
			}
			for n in range(len(data) // 0x10)
		]
		yield int(10/N*100)
		
		# load shops
		allShops = ['BOOK_MAA', 'GENERAL_MAA', 'HIGH_BOOK_MAA', 'HIGH_ITEM_MAA', 'HIGH_MEAT_MAA', 'HIGH_WEAPON_MAA', 'ITEM_ATA', 'ITEM_ATB', 'ITEM_BTA', 'ITEM_BTB', 'ITEM_BTC', 'ITEM_CTA', 'ITEM_CTB', 'ITEM_CTD', 'ITEM_CTE', 'ITEM_DTA', 'ITEM_DTB', 'ITEM_DTC', 'ITEM_FTA', 'ITEM_MAA', 'ITEM_W', 'KEY_MAA', 'MASTER', 'MATERIAL_ATB', 'MEAT_MAA', 'WEAPON_ATB', 'WEAPON_BTB', 'WEAPON_BTC', 'WEAPON_CTA', 'WEAPON_CTD', 'WEAPON_CTE', 'WEAPON_DTC', 'WEAPON_FTA', 'WEAPON_MAA', 'WIFI']
		self.initialConfig['shops'] = list()
		for i, shop in enumerate(allShops):
			with open(join(self.data_folder, 'Param', 'StoreTbl_%s.bin' % shop), 'rb') as file: data = file.read()
			self.initialConfig['shops'].append({
				'loc': shop,
				'ids': [i for i, b in enumerate(data[0x08:]) if b & 1 == 1],
			})
			yield int((10+(i+1)/len(allShops))/N*100)
		# finish
		yield 100
	
	def saveFiles(self):
		""" Writes the game files based on the current config. """
		N = 4
		
		# save chests
		with open(join(self.data_folder, 'Param', 'FixItemTbl.bin'), 'rb') as file: data = file.read()
		for n, chest in enumerate(self.config['chests']):
			data = data[:n*0x10+0x00] + chest['loc'][0].encode() + data[n*0x10+0x00+5:]
			data = data[:n*0x10+0x08] + bytes([chest['loc'][1]]) + data[n*0x10+0x08+1:]
			data = data[:n*0x10+0x0C] + int.to_bytes(chest['id'], 2, 'little') + data[n*0x10+0x0C+2:]
			data = data[:n*0x10+0x0E] + int.to_bytes(chest['mod'], 2, 'little') + data[n*0x10+0x0E+2:]
		with open(join(self.data_folder, 'Param', 'FixItemTbl.bin'), 'wb') as file: file.write(data)
		yield int(1/N*100)
		
		# save shops
		for i, shop in enumerate(self.config['shops']):
			with open(join(self.data_folder, 'Param', 'StoreTbl_%s.bin' % shop['loc']), 'rb') as file: data = file.read()
			old_data = data
			for k in range(len(data)-0x08):
				data = data[:0x08+k] + bytes([data[0x08+k] >> 4 << 4 | (1 if k in shop['ids'] else 0)]) + data[0x08+k+1:]
			with open(join(self.data_folder, 'Param', 'StoreTbl_%s.bin' % shop['loc']), 'wb') as file: file.write(data)
			yield int((1+(i+1)/len(self.config['shops']))/N*100)
		
		# save skills
		with open(join(self.data_folder, 'Param', 'SkillTbl.bin'), 'wb') as file:
			file.write(b'SKIL')
			file.write(int.to_bytes(len(self.config['skills']['sets']), 4, 'little'))
			for id, set in enumerate(self.config['skills']['sets']):
				if set is None: file.write(b'\x00'*0x84); continue
				for i in range(10): file.write(int.to_bytes(set[i if i < len(set) else -1]['sp'], 1, 'little'))
				for i in range(10): file.write(int.to_bytes(set[i]['id'] if i < len(set) and set[i]['t'] == 'a' else 0, 0xA, 'little'))
				for i in range(10): file.write(int.to_bytes(set[i]['id'] if i < len(set) and set[i]['t'] == 't' else 0, 0x2, 'little'))
				file.write(b'\x00\x00')
		yield int(2.5/N*100)
		with open(join(self.data_folder, 'Param', 'SkillEvoTbl.bin'), 'wb') as file:
			file.write(b'SEVO')
			file.write(int.to_bytes(len(self.config['skills']['evo']), 4, 'little'))
			for src, res in enumerate(self.config['skills']['evo']):
				file.write(int.to_bytes(src, 2, 'little'))
				file.write(int.to_bytes(1 if res else 0, 2, 'little'))
				file.write(int.to_bytes(res or 0, 2, 'little'))
		yield int(2.7/N*100)
		with open(join(self.data_folder, 'Param', 'SkillSpEvoTbl.bin'), 'wb') as file:
			file.write(b'SESP')
			file.write(int.to_bytes(len(self.config['skills']['spevo']), 4, 'little'))
			for skill in self.config['skills']['spevo']:
				for i in range(6): file.write(int.to_bytes(skill['src'][i], 2, 'little'))
				for i in range(6): file.write(int.to_bytes(skill['sp'][i], 2, 'little'))
				file.write(int.to_bytes(skill['res'], 2, 'little'))
				file.write(b'\x00\x00')
		yield int(3/N*100)
		
		# finish
		yield 100
	
	## HELPER ##

	def readFromBinJ(self, file, folder = 'Message', indices = None):
		filename = join(self.data_folder, folder, file + '.binJ')
		with open(filename, 'rb') as file: bin = file.read()
		data, _ = parseBinJ(bin, self.SEP)
		data = [list2text(bytes2list(line, self.TABLE, self.SEP)) for line in data]
		if indices: return data[indices[0]:indices[1]+1]
		return data

COPYRIGHT_BCLIM = b85decode(b''
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'*10
  + b'0000000000000000000000000000000000000000000C4000C44*&)L4*(7T000C4000C44*(7T4*&)L000000000000000000C4'
  + b'1^@s64gdfE000aC1ON{J00000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'3;+%Q4*(7T00000000004gd}S2LKKL00000000F5000000000000000000002mlTM4*&%K4gdxK1^^EL00000000000000000000'
  + b'0000000000000000000000000000000000000000000000ss#H000000{{g800000000000000000000000000{{g82>=fO4*&%K'
  + b'0ss#H0ss#H0{{d70{{R33;+)R2LKNM0{{g80{{g800000000000000000000000004gdiF00000000O800000000000000000000'
  + b'000004gdfE000004gdxK3;+NC00000000jF0ss#H4*&oF4*&oF4FC@S0{{;I1^@s60{{R33jhQF000004*(AU1pop74*&)L4*&)L'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'000O81pp5K4gd`R1ONp9000000000000000000001ONa44*&oF000R91pp5K000000000000000000000000000062000004*&xI'
  + b'000000000000000000000000000000000000000000062000624*&xI4*&xI4*(1R1po&C4*&xI4*&xI00000000000000000000'
  + b'00000000004FCuL2mlNK0000000000000000000000000000000000000000000000000000000000000000000000000001pp2J'
  + b'00000000000000000000000R9000dD4FCWD4*&rG00000000001ON;G000001ON{J2mlKJ1pp5K1pp5K00000000000000000000'
  + b'000000RR9100000000000000000000000000000000000000F5000004*&oF00000000004FCfG4*&xI000dD000C44*(AU4*&%K'
  + b'000F5000F54*&oF4*&oF2ml2D0RRO64*&`P4*&)L000000000000000000000000000000000000000000000000000000000000'
  + b'00000000000000000000000000000000000000004*&`P1^^EL000000{{R30000000000000R90{{;I00000000002mlWN3IGoP'
  + b'00000000000000000000000002LKHK000004*(7T00000000000000000000000003IGBC00000000004*&`P2><{91^@>D00000'
  + b'0ssI20RR91000310RRsG4FCoJ0000000000000L70RR914*&}Q0RRjD000000000000000000000000000000000000000000000'
  + b'0000000000000000000000000000000000000000000004ge1T000003IG5A2LJ~E000004*&-M4FC%O000000{{;I000002mlTM'
  + b'0{{;I0{{;I4FCoJ1^@s600000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'000004gdoH000003IGoP4FC@S2LKNM3jhWH0ssI2000003;+TE00000000004*&`P3;+!P00031000L700000000000000000000'
  + b'000000000000000000000000000000000000000000000000000000000000000001ON>H000004*&}Q4*(1R4*&xI1^^8J0RRR7'
  + b'000000RR9100000000003IG5A4*&oF00000000000000000000000000000000000000C4000004*(AU00000000000000000000'
  + b'000004*(AU000004gdfE000C4000C44*&@O4*&)L000C4000C44*&-M4*(AU1poyA000001ONa4000000RRC24*(AU000310ssd9'
  + b'000000000000000000000000000000000I6000I6000000000000000000004*&xI4*&xI0{{*H1ON{J000001pp2J000I64gd@Q'
  + b'4*(1R4*&xI1^^8J000I64*&xI4*&xI000310{{;I4*&xI4*&xI0{{;I0{{;I000000000000000000001poj52LJ#7000002>=NI'
  + b'0000000000000000000000000000000000000000000001^^5I4FCxM4*(AU1^@&A1^@s64*&}Q4*&@O000004*&uH0000000093'
  + b'1poj5000000RRsG2LKNM00000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'000003;+)R000003;+WF3;+fI0{{R33;+)R0{{;I00000000C4000004*&-M0RRL52LJ>B4*(4S4*&%K00000000000000000000'
  + b'000000000000000000000000000000000000000000000000000000000000000004gduJ00000000001pom6000000000000000'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'*22
  + b'00000000000000000000000000000000000000000000000000000000000000000000000000000000000C4000C44*&oF4*&oF'
  + b'000C4000C44*&oF4*&oF4gd!L1^^EL3;+lK4*&rG000dD000002mk;8000000000000000000000000000000000000000000000'
  + b'00000000000000000000000000000000000000001^^BK1^^BK000R9000R91^^BK1^^BK000F5000003;+NC3;+NC000gE000gE'
  + b'4*&%K2mlTM1^^EL4gd!L00000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'2mlEH2mlEH3;+NC3;+NC0{{j9000004*&!J3jhuP0ss#H0ss#H0{{g80{{g82LKNM2mlWN0{{g80{{g800000000000000000000'
  + b'0000000000000000000000000000000000000000000000000000000000004*&oF4*&oF0ss#H0ss#H4*&oF4*&oF0ss#H0ss#H'
  + b'0{{R30{{R34*&)L4*&)L0{{R30{{R34*&)L4*&)L000000000000000000000000000000000000000000000000000000000000'
  + b'000000000000000000002>=fO2>=WL4*(AU0ssO41ON{J000L71pos84gd}S4*&uH0ssI22>=WL2>=WL2mk;82><{91^^EL000XB'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000062000624*&xI4*&xI'
  + b'1ONvB4gd%M4*&xI4*&xI00000000001ON{J000jF0000000000000XB000L70000000000000000000000000000000000000000'
  + b'00000000000000000000000000000000000000000ssyG2>=QJ3jhTG2LK8H4*&)L4*&rG0ss#H000gE3;+iJ4*&xI1pp5K1pp5K'
  + b'4gdfE3IG5A1pp5K1pp5K00000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'00062000624*&xI4*&xI00062000004*&)L3jhxQ000F5000F54*&oF4*&oF000F51poyA4*&oF4*&oF00000000000000000000'
  + b'000000000000000000000000000000000000000000000000000000000000000jF000jF1poj51poj5000jF000jF1poj51poj5'
  + b'00000000002mlWN0{{;I0000000000000R900000000000000000000000000000000000000000000000000000000000000000'
  + b'000000000000000000000{{R33IG5A000C4000004*&}Q1po{H1^@>D4*(7T4FC%O3;+uN000L71pp5K4*&}Q3jhNE2LKNM0RRjD'
  + b'000000000000000000000000000000000000000000000000000000000000000000000000000000004ge1T2ml2D4*(1R4gd@Q'
  + b'2LK2F4*&`P4*(1R2mlNK0{{;I0{{;I1^@s61^@s60{{;I0{{;I1^@s61^@s60000000000000000000000000000000000000000'
  + b'00000000000000000000000000000000000000002LKNM2LKNM0ssI20ssI22LKNM2LKNM0ssI20ssI23jhuP3jhuP000O8000I6'
  + b'3jhuP3jhuP000310000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'4*(AU4*&%K4*(AU1ONm84*&}Q0{{#F1^@^E4*(4S4*&uH1ONa400000000002><{91^@s6000000000000000000000000000000'
  + b'000000000000000000000000000000000000000000000000000000000000000C4000C44*&@O4*&)L000C4000C44*&@O4*(AU'
  + b'1ONm800000000R9000L71poyA4*(AU1ONj74gdfE000000000000000000000000000000000000000000000000000000000000'
  + b'000000000000000000004*&rG4*&uH000I6000I64*&}Q2mlWN1^^8J4FCoJ4*&xI4*&xI0{{;I0{{;I4*&xI4*&xI0{{;I0{{;I'
  + b'000000000000000000000000000000000000000000000000000000000000000000000000000000001^@s61^@s64*&@O4*&@O'
  + b'1^@s61^@s64*(4S2LKNM00000000002>=fO2LKNM1poj54FCZE0RRsG000930000000000000000000000000000000000000000'
  + b'00000000000000000000000000000000000000000RR910{{R30RRsG0{{;I3;+fI3;+)R3;+)R3;+WF2mk~C2LJ>B4*&%K4*&%K'
  + b'0RRL5000C44*&%K4*&%K00000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'*16
  + b'000000000000000000000000000000000000000000000000000000000000008j+008j+@c;1t@c#e+00000000000000000000'
  + b'00000000000000000000008j+008j+000XB2>=fO00062000R94*(AU4*(AU00000000000000000000@c#k;2>=fO2>=ZM4*(AU'
  + b'000000000000000000004*(AU4*(AU4FCxM4*(AU4*(AU9}!<w4*(AU9}y1#KQsUTKQsUT@9w|5|NsC04*(AU4*(AU4*(AU4*(w#'
  + b'|NsC0|NsC0zq{Yv|NsC0000000000000000000000s!#;4*&@O@c;1t008j+00000000000000000000@c#e+@c#e+0000000000'
  + b'4*(AUUsWFw3jhEB4*&@O|NlQT|NlQT4*(AU4*(AU@c#e+@c#e+00000000000ssI22mk;8000000000000000000000000000000'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'000001ON{J000000{{R31ON{J1ON{J0{{R30{{R3000000000000000000000000000000000000000000000000000000000000'
  + b'00000000000000000000000000000000000000000000000000000XB000gE000000000000000000002LJ#72LJ#7000jF0{{;I'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'0RR910RR91000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'*2
  + b'000000000000000000620000000000000R90RRsG000004gdiF00000000002><{90RR91000000003100000000000000000000'
  + b'000000000000000000000000000000000000000000000000000000000000000000ssyG000000RR912>=NI4*&rG0000000000'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'00000000000000000000000001ON^I000000{{R30{{&G000000ssI200000000000000000000000C43jhWH4gdxK000C4000C4'
  + b'00000000000000000000000000000000000000000000000000000000000000000000000000000000000004*&xI0000000000'
  + b'4*&xI4*&xI000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'0000000000000000000000000000000000000000000000000000000000C40000000000000C4000C4000004*&xI0000000000'
  + b'4*&xI4*&xI000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'*5
  + b'00000000000000000031000000ssyG000000RR912>=NI4*&rG0ss#H0ss#H0000000000000000000000000000000000000000'
  + b'0000000000000000000000000000000000000000000000000000000000001^@s61^@s600000000000000000000000001ON{J'
  + b'00000000001ON{J1ON{J00000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'000000{{R300000000000{{R30{{R30000000000000000000000000000002mlWN000624*(AU0ssR500000000000000000000'
  + b'000000000000000000000000000000000000000000000000000000000000000000000000000000004*(1R4gd%M000F50ss#H'
  + b'000000000000000000004FC@S2LJ>B3jhHC4gd%M000000000000000000000000000000000000000000000000000000000000'
  + b'00000000000000000000000000000000000000620000000000000R90RRsG000004gdiF00000000002><{90RR91000R94FC=R'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'4ge1T1pop74FCrK1^@{F00000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'*3
  + b'000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000F5000F5'
  + b'000000000000000000004*(AU4*&%K4*(AU0ssO4000000000000000000000000000000000000000000000000000000000000'
  + b'00000000000000000000000000000000000000002LJ#70RR91000000000000000000aC000003jhQF000aC000aC3jhNE3jhEB'
  + b'00000000000000000000000000000000000000000000000000000000000000000000000000000000000004gdoH0000000000'
  + b'4FCcF00000000XB000gE000000000000000000001^@s61^@s600000000000000000000000000000000000000000000000000'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'*9
  + b'000000000000000000000000000000000000000000000000000000000000000dD000jF4*(AU4*(AU000jF000dD4*(AU4*(AU'
  + b'0000000000000000000000000000000000000000000R9000624*(AU4**X@008j+008j+2>=fO000XBpPB#v|NsC0|NsC0|NsC0'
  + b'-`)TJZ)X4h|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC09}$m;FCq^B|NsC0FCveKkBC1r4FGRuFCwq1e|P`?'
  + b'|NsC0|NsC0|NsC0kBBcK|NsC0|NsC0zq=0r|NjpF|NpP5|NsC04*(AU4*(AU|Nrmq|Nnn?4*(AU4*(AU4FCWD4*&oF0000000000'
  + b'4*&oF4FCWD0000000000pP3&K4*(AU4*(AU4*(AU4*(AU4*(AU4*&@O3jhEB2><{90ssI20000000000@c#e+@c#e+0000000000'
  + b'00000000000000000000000000000000000000001ON{J1ON{J3IGlO2>=5C1ON{J1ON{J0{{R30{{R300000000000000000000'
  + b'000000000000000000001ON{J1ON{J0{{R30{{R3000000000000000000004FCfG4gd-O3;+)R0ss#H3IGfM3IGiN0RRsG0RRsG'
  + b'4*(AU2mk^A4*(AU2LKNM2LJ#72LJ#71^^EL1^^EL3IGiN3IGiN000jF000R9000000000000000000002><~A4*&`P1^^EL0RRmE'
  + b'000000000000000000004*&=N0{{U41ON{J1ON{J0RR910RR911ON{J1ON{J2mlTM2>=5C4FCfG4FC)P0{{R30{{R32mlWN2mlWN'
  + b'1poj54*&)L1ON{J1ON{J00000000001ON{J1ON{J2LJ;A3;+)R4gd=P3;+QD0{{R30{{R300000000000RRgC2LKNM4*(1R0{{j9'
  + b'1pp5K000933IGHE3IGoP0ssL30RRC24gduJ3;+ZG000001poj500000000000{{j91pp2J0{{;I4*&`P00000000000000000000'
  + b'1^@s6000310RR914*&)L0000000000000000000000000000002mlHI4gdlG000L7000gE3jhEB0{{R30000000000000O8000gE'
  + b'00000000002LKBI4gdoH1^^5I4FCfG000000000000000000000000000000000I6000dD3;+NC0{{R300000000000000000000'
  + b'3IG5A0ssI2000UA1^^EL00000000001^^BK000gE4*(AU1ON*F4*&=N4gdiF0RRaA4*(4S3;+NC0{{R300000000000{{;I2LKBI'
  + b'00000000003IGfM0sspD4*(AU0ssU63jhHC4*&)L0{{g84*(7T4*&xI1^@s61ON{J1ON{J0{{&G0{{X51ON{J1ON{J0{{U40{{U4'
  + b'4*(AU4*&-M4FCiH0ssU64*&)L4*&)L000C4000C41ON{J1ON{J0{{R30{{R3000000000000000000004*&@O2>=fO0RRL53IGHE'
  + b'000000000000000000004*&`P4*&@O4gd`R0{{*H4*&xI4*&xI000UA000UA0{{j93IGNG4*&rG4*&rG3;+fI4FClI4*&rG4*&rG'
  + b'4*&xI4*&xI000UA000UA000000000000000000004FCiH4FCWD4*&-M3IGoP00000000000000000000000aC000aC3jhQF3jhQF'
  + b'000aC000aC3jhQF3jhQF4*&`P4*&@O4gd`R0{{&G4*&xI4*&xI000O8000O81ON^I3;+uN3jhQF3jhQF00000000000000000000'
  + b'4*&=N4*&`P0{{*H4*(1R000000000000000000000{{R34FCWD00000000004*&oF4*&oF0000000000000O81pp5K4gd}S1^@&A'
  + b'2>=cN2>=cN00000000003jhEB0RRF30RR914*&%K000000000000000000001pp5K000O81^@*B4*(7T00000000000000000000'
  + b'1^@s61ONm81^^8J4*&-M000O8000O84*&oF4*&oF4*&`P0{{&G0RRL53jhQF000O8000O84*&!J4*&!J1^@&A1^@s64*&-M1^^8J'
  + b'000000000000000000000{{&G4*&`P3jhQF0RRL5000000000000000000004*&@O4*&=N4*&}Q1ON{J4*&xI4*&xI000dD000dD'
  + b'1pp2J4gdoH4gdxK3IGoP3IG5A3IG5A1^^EL1^^EL4*&xI4*&xI000dD000dD000000000000000000003IG5A3IG5A1^^EL1^^EL'
  + b'000000000000000000000000000000000O8000gE0RR910RR912LKBI4gdoH3IG5A0ssI20ss#H0ss#H00000000000ss#H0ss#H'
  + b'0RRR70RRmE3;+NC0{{R30000000000000000000000000000000ss#H0ss#H000000000000000000001^@s61^@*B2mlTM4*&)L'
  + b'1^@{F1^@{F4gdfE4gdfE4gdxK1ONm81ON{J1ON{J00000000001ON{J1ON{J1^@*B1^@s64*&)L2mlWN00000000000000000000'
  + b'1po#B4gdxK1ON{J1ON{J000000000000000000003IGlO2>=5C4FCfG4gd-O0{{R30{{R33IGfM3IGiN0000000000000I6000dD'
  + b'00000000001pp5K4FC%O0{{R30{{R33IGiN3IGiN00000000000000000000000C4000aC4*&!J3jhEB00000000000000000000'
  + b'4*&rG2><{900062000000ssI200000000000ssX7000311pp5K4gd!L4FCWD0RRL5000004gd%M3jhlM00000000001ON{J000L7'
  + b'000000000000000000001^@&A4ge1T4gd!L2><{90000000000000000000000000000002mlHI4gdlG000L7000gE3jhEB0{{R3'
  + b'000I6000UA4*&xI4*&oF000UA000I64*&oF4*&xI1^^5I4FCfG00000000000000000000000000000000000000003;+%Q000O8'
  + b'0000000000000000000000000000000000000000000L7000004*(AU1^^EL00000000002>=cN1^@#90RR910ssa81^^8J4*&)L'
  + b'1pos84ge1T2mlWN4FCuL000000000000000000000ssgA000624*&xI4FC@S000000000000000000004gd!L2LKNM000C40ssU6'
  + b'4*(AU1pp5K1ONm81ONm84*&@O4*&=N4*&}Q1ON{J4*&xI4*&xI000dD000dD2mlWN2mlQL1ONm81ONm800000000000000000000'
  + b'4*&xI4*&xI000dD000dD000000000000000000001pp2J4gdoH4gdxK3IGoP3IG5A3IG5A1^^EL1^^EL00000000C41^^8J4*&)L'
  + b'0RRX90RRX94*(AU4*&uH3IG5A3IG5A1^^EL1^^EL000000000000000000000RRI40RR914*&-M1^^8J00000000000000000000'
  + b'4gd)N0{{&G000F51^@*B4*(AU0ssO43IGKF0RRO64*&xI4*(AU000004*&}Q4*&%K4*&xI0ssO4000000{{mA4*(1R0{{g80{{g8'
  + b'000000000000000000004*&%K4*(AU0ssO44*(AU0000000000000000000000000000C42LKKL4*&-M000O8000R94*&oF4*&oF'
  + b'4FC=R1ON^I3jhQF3jhQF000aC000aC3jhQF3jhQF0RRO62LJ#74*&)L3IGoP000000000000000000001ON^I3jhiL3jhQF3jhQF'
  + b'000000000000000000004*&xI4*&xI4FC@S0ss#H4*&xI4*&xI0RRsG0RRsG4*(4S2LJ*9000I61ON{J1^@s61^@s62mlWN2mlWN'
  + b'4*&xI4*&xI000jF000R9000000000000000000002><~A4*&`P1ON{J000I6000000000000000000004FC@S2LJ;A3IG8B4FC%O'
  + b'00000000002mlWN2mlWN1pp5K1pp5K2>=fO2mk^A1^^EL1^^EL0ssI20ssI22LJ;A4FC@S4FC%O3IG8B00000000000000000000'
  + b'1pp5K1pp5K0ssI20ssI200000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'*7
  + b'00000000000000000000000000000000000000000000000000000000000000000000000000000000008j+008j+@c#e+@c;1t'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'2>=fO@c#k;4*=iY2mt^800000000000000000000|NsC0|NsC0|NjpF|NjU80000000000000000000000000000000000000000'
  + b'0000000000000000000000000000000000000000000000000000000000004*&@O0s!#;008j+@c;1t00000000000000000000'
  + b'@c#e+@c#e+000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
  + b'0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'*198
  + b'000000000000000000000000000000000000000000000000000000000000Lrh6c|NayJ00064D1ZO}0RR91X>DO=5C8xG>;NMG'
  + b'2mk;80Du4h'
)

DECODING_TABLE = '\n'.join('%02X;%s' % (i+1, chr(i+48)) for i in range(10)) + '\n' \
  + '0B; \n0C;　\n' \
  + '\n'.join('%02X;%s' % (i+0x0D, chr(i+65)) for i in range(26)) + '\n' \
  + '\n'.join('%02X;%s' % (i+0x27, chr(i+97)) for i in range(26)) + '\n' \
  + '41;À\n42;Á\n43;Â\n44;Ä\n45;Ç\n46;È\n47;É\n48;Ê\n49;Ë\n4A;Ì\n4B;Í\n4C;Î\n4D;Ï\n4E;Ñ\n4F;Ò\n50;Ó\n' \
  + '51;Ô\n52;Ö\n53;Œ\n54;Ù\n55;Ú\n56;Û\n57;Ü\n58;à\n59;á\n5A;â\n5B;ä\n5C;ç\n5D;è\n5E;é\n5F;ê\n60;ë\n' \
  + '61;ì\n62;í\n63;î\n64;ï\n65;ñ\n66;ò\n67;ó\n68;ô\n69;ö\n6A;œ\n6B;ù\n6C;ú\n6D;û\n6E;ü\n' \
  + '6F;あ\n70;ぁ\n71;い\n72;ぃ\n73;う\n74;ぅ\n75;え\n76;ぇ\n77;お\n78;ぉ\n79;か\n7A;き\n7B;く\n7C;け\n7D;こ\n7E;さ\n' \
  + '7F;し\n80;す\n81;せ\n82;そ\n83;た\n84;ち\n85;つ\n86;っ\n87;て\n88;と\n89;な\n8A;に\n8B;ぬ\n8C;ね\n8D;の\n8E;は\n' \
  + '8F;ひ\n90;ふ\n91;へ\n92;ほ\n93;ま\n94;み\n95;む\n96;め\n97;も\n98;や\n99;ゃ\n9A;ゆ\n9B;ゅ\n9C;よ\n9D;ょ\n9E;ら\n' \
  + '9F;り\nA0;る\nA1;れ\nA2;ろ\nA3;わ\nA4;を\nA5;ん\nA6;ア\nA7;ァ\nA8;イ\nA9;ィ\nAA;ウ\nAB;ゥ\nAC;エ\nAD;ェ\nAE;オ\n' \
  + 'AF;ォ\nB0;カ\nB1;キ\nB2;ク\nB3;ケ\nB4;コ\nB5;サ\nB6;シ\nB7;ス\nB8;セ\nB9;ソ\nBA;タ\nBB;チ\nBC;ツ\nBD;ッ\nBE;テ\n' \
  + 'BF;ト\nC0;ナ\nC1;ニ\nC2;ヌ\nC3;ネ\nC4;ノ\nC5;ハ\nC6;ヒ\nC7;フ\nC8;ヘ\nC9;ホ\nCA;マ\nCB;ミ\nCC;ム\nCD;メ\nCE;モ\n' \
  + 'CF;ヤ\nD0;ャ\nD1;ユ\nD2;ュ\nD3;ヨ\nD4;ョ\nD5;ラ\nD6;リ\nD7;ル\nD8;レ\nD9;ロ\nDA;ワ\nDB;ヲ\nDC;ン\nDD;ヴ\nDE;(1)\n' \
  + 'DF;(2)\nE000;(9)\n' \
  + 'E001;が\nE002;ぎ\nE003;ぐ\nE004;げ\nE005;ご\nE006;ざ\nE007;じ\nE008;ず\nE009;ぜ\nE00A;ぞ\nE00B;だ\nE00C;ぢ\n' \
  + 'E00D;づ\nE00E;で\nE00F;ど\nE010;ば\nE011;び\nE012;ぶ\nE013;べ\nE014;ぼ\nE015;ガ\nE016;ギ\nE017;グ\nE018;ゲ\n' \
  + 'E019;ゴ\nE01A;ザ\nE01B;ジ\nE01C;ズ\nE01D;ゼ\nE01E;ゾ\nE01F;ダ\nE020;ヂ\nE021;ヅ\nE022;デ\nE023;ド\nE024;バ\n' \
  + 'E025;ビ\nE026;ブ\nE027;ベ\nE028;ボ\nE029;ぱ\nE02A;ぴ\nE02B;ぷ\nE02C;ぺ\nE02D;ぽ\nE02E;パ\nE02F;ピ\nE030;プ\n' \
  + 'E031;ペ\nE032;ポ\nE033;(ß)\nE034;(¿)\nE035;(¡)\nE036;(ß)\nE037;(¿)\nE038;(¡)\nE039;(!)\nE03A;(?)\nE03B;(_)\nE03C;(←)\n' \
  + 'E03D;(↑)\nE03E;(→)\nE03F;(↓)\nE040;(☆)\nE041;(★)\nE042;(※)\nE043;(△)\nE044;(▲)\nE045;(▽)\nE046;(▼)\nE047;(□)\nE048;(■)\n' \
  + 'E049;(○)\nE04A;(●)\nE04E;(=)\nE04F;(/)\nE050;(/)\nE051;(↔)\nE052;(→)\nE053;(Ⅰ)\nE054;(Ⅱ)\nE055;(Ⅲ)\nE056;(Ⅴ)\nE057;(Ⅹ)\n' \
  + 'E058;(;)\nE059;(°)\nE05A;(_)\nE05B;(”)\nE05C;(”)\nE05D;(”)\nE05E;(”)\nE05F;(’)\nE060;(‘)\nE061;(’)\nE062;(‘)\nE063;(’)\n' \
  + 'E064;(~)\nE065;(♪)\nE066;(*)\nE067;(・)\nE068;(*)\nE100;(ポ)\nE101;(ß)\nE102;(¿)\nE103;(¡)\nE104;ß\nE105;¿\nE106;¡\n' \
  + 'E107;!\nE108;?\nE109;_\nE10A;←\nE10B;↑\nE10C;→\nE10D;↓\nE10E;[EmptyStar]\nE10F;[YellowStar]\nE110;※\nE111;△\nE112;▲\n' \
  + 'E113;▽\nE114;▼\nE115;□\nE116;■\nE117;○\nE118;●\nE119;°\nE11A;+\nE11B;＋\nE11C;=\nE11D;/\nE11E;／\n' \
  + 'E11F;⇒\nE120;Ⅰ\nE121;Ⅱ\nE122;Ⅲ\nE123;Ⅴ\nE124;Ⅹ\nE125;;\nE126;(°)\nE127;(-)\nE128;(-)\nE129;"\nE12A;(")\n' \
  + 'E12B;(")\nE12C;(")\nE12D;\'\nE12E;(\')\nE12F;`\nE130;(\')\nE131;(\')\nE132;(~)\nE133;♪\nE134;(*)\nE135;(・)\nE136;*\n' \
  + 'E137;(\nE138;)\nE139;(”)\nE13A;%\nE13B;.\nE13C;&\nE13D;×\nE13E;:\nE13F;(„)\nE140;(!)\nE141;》\nE142;《\n' \
  + 'E143;-\nE144;(,)\nE145;,\nE146;(?)\nE147;｡\nE148;「\nE149;」\nE14A;『\nE14B;』\nE14C;”\nE14D;“\nE14E;(?)\n' \
  + 'E14F;(!)\nE150;(,)\nE151;・\nE152;ー\nE153;(-)\nE154;~\nE155;(/)\nE156;(*)\nE157;(()\nE158;())\nE159;(+)\nE15A;(:)\n' \
  + 'E15B;[...]\nE15C;(→)\nE15D;(¡)\nE15E;(%)\nE15F;(.)\nE160;(&)\nE161;(`)\nE162;(°)\nE163;(:)\nE164;(%)\nE165;♂\nE166;♀\n' \
  + 'E167;々\nE168;(‘)\nE169;(’)\nE16A;【\nE16B;】\nE16C;(-)\nE16D;(♪)\nE16E;☆\nE16F;★\n'   \
  + 'E201;[0]\nE202;[1]\nE203;[2]\nE204;[3]\nE205;[4]\nE206;[5]\nE207;[6]\nE208;[7]\nE209;[8]\nE20A;[9]\n' \
  + 'E20B;[WhiteRightArrow]\nE20C;[BlackRightArrow]\nE20D;[SlimeSymbol]\nE20E;[DragonSymbol]\nE20F;[NatureSymbol]\n' \
  + 'E210;[BeastSymbol]\nE211;[MaterialSymbol]\nE212;[DevilSymbol]\nE213;[ZombieSymbol]\nE214;[???Symbol]\n' \
  + 'E215;[BrownFist]\nE216;[Lightning]\nE217;[GreenPlus]\nE218;[ThreePlus]\nE219;[SwordSymbol]\n' \
  + 'E21A;[SpearSymbol]\nE21B;[WhipSymbol]\nE21C;[ClawSymbol]\nE21D;[StaffSymbol]\nE21E;[AxeSymbol]\n' \
  + 'E21F;[HammerSymbol]\nE220;[YellowItem]\nE221;[BrownChest]\nE222;[GreenUpArrow]\nE223;[RedDownArrow]\n' \
  + 'E224;[MoneySymbol]\nE225;[WhiteDownArrow]\nE226;[BlackDownArrow]\nE227;(♂)\nE228;(♀)\n' \
  + 'E229;[MaleAndFemaleSymbol]\nE22A;[PartySymbol]\nE22B;[StandbyPartySymbol]\nE22C;[MonsterFarmSymbol]\nE22D;[SmallPartySymbol]\n' \
  + 'E22E;[SmallStandbyPartySymbol]\nE22F;[SmallMonsterFarmSymbol]\nE230;[NeverAI]\nE231;[OftenAI]\nE232;[BigStar]\n' \
  + 'E233;[FlippedBigStar]\nE234;[H]\nE235;[P]\nE236;[M]\nE237;[Lv]\n' \
  + 'E238;[TopToRightArrow]\nE239;[StarSymbol]\nE23A;[UncheckedCheckbox]\nE23B;[CheckedCheckbox]\nE23C;[BluePlus]\n' \
  + 'E23D;[QuestionMark]\nE23E;[GoldenBlock]\nE23F;[SilverBlock]\nE240;[BronzeBlock]\nE241;[GoldenKey]\n' \
  + 'E242;[SilverKey]\nE243;[BronzeKey]\nE244;[GoldenBadge]\nE245;[SilverBadge]\nE246;[BronzeBadge]\n' \
  + 'E247;[AsNeededAI]\nE248;[WhiteKey]\nE249;[GrayStar]\n# E24A;堯\nE24B;[StandardSizeSymbol]\n' \
  + 'E24C;[PowerfulSizeSymbol]\nE24D;[HugeSizeSymbol]\nE24E;[GiganticSizeSymbol]\nE24F;[1/4-Star]\nE250;[2/4-Star]\n' \
  + 'E251;[4/4-Star]\nE252;[YellowRightArrow]\nE253;[GreenKey]\nE254;[BlueKey]\nE255;[RedKey]\n' \
  + 'E256;[PurpleBlock]\nE257;[RankF]\nE258;[RankE]\nE259;[RankD]\nE25A;[RankC]\nE25B;[RankB]\n' \
  + 'E25C;[RankA]\nE25D;[RankS]\nE25E;[RankSS]\nE25F;[PurpleKey]\n' \
  + 'E301;[#01]\nE302;[#02]\nE303;[MSG3]\nE304;[#04]\nE305;[#05]\nE306;[#06]\nE307;[MSG7]\nE308;[MSG8]\n' \
  + 'E309;[YesNoOption]\nE30A;[#0A]\nE30B;[#0B]\nE30B00;[#0B0]\nE30B10;[#0B1]\nE30B20;[#0B2]\nE30B30;[#0B3]\nE30B40;[#0B4]\n' \
  + 'E30B50;[#0B5]\nE30B60;[#0B6]\nE30B70;[#0B7]\nE30B80;[#0B8]\nE30B90;[#0B9]\nE30BA0;[#0BA]\nE30BB0;[#0BB]\nE30BC0;[#0BC]\n' \
  + 'E30BD0;[#0BD]\nE30BE0;[#0BE]\nE30BF0;[#0BF]\nE30C;[CONT]\nE30D;[#0D]\nE30E;[#0E]\nE30F;[#0F]\nE310;[#10]\n' \
  + 'E311;[#11]\nE312;[#12]\nE313;[#13]\nE314;[#14]\nE315;[LF]\nE316;[#16]\nE317;[#17]\nE318;[#18]\n' \
  + 'E319;[#19]\nE31A;[#1A]\nE31C;[#1C]\nE31C00;[Color]\nE31C01;[Grey]\nE31C02;[Yellow]\nE31C03;[Red]\nE31C04;[Green]\n' \
  + 'E31C05;[Brown]\nE31C06;[Blue]\nE31C07;[Pink]\nE31C08;[#1C8]\nE31C09;[#1C9]\nE31C0A;[#1CA]\nE31C0B;[#1CB]\nE31C0C;[#1CC]\n' \
  + 'E31C0D;[#1CD]\nE31C0E;[#1CE]\nE31C0F;[#1CF]\nE31D;[#1D]\nE31D00;[#1D0]\nE31D01;[#1D1]\nE31D02;[#1D2]\nE31D03;[#1D3]\n' \
  + 'E31D04;[#1D4]\nE31D05;[#1D5]\nE31D06;[#1D6]\nE31D07;[#1D7]\nE31D08;[#1D8]\nE31D09;[#1D9]\nE31D0A;[#1DA]\nE31D0B;[#1DB]\n' \
  + 'E31D0C;[#1DC]\nE31D0D;[#1DD]\nE31D0E;[#1DE]\nE31D0F;[#1DF]\nE31E;​\nE31F;[CENTERED]\n' \
  + '\n'.join('%02X;[#%02X]' % (i+0xe320, i+0x20) for i in range(213)) + '\n' \
  + 'E3F400;[#F40]\nE3F420;[#F42]\nE3F440;[#F44]\nE3F5;[GIRL]\nE3F6;[BOY]\nE3F7;[#F7]\nE3F8;[#F8]\nE3F9;[#F9]\n' \
  + 'E3FA;[#FA]\nE3FB;[#FB]\nE3FC;[#FC]\nE3FD;[#FD]\nE3FE;[#FE]\nE3FF;[#FF]\n' \
  + '\n'.join('%03X;%s' % (i+0xe40000, chr(i)) for i in range(0x4e00, 0x9fbb)) + '\n'

if __name__ == '__main__':
	app = QtWidgets.QApplication(list())
	translator = QtCore.QTranslator()
	baseTranslator = QtCore.QTranslator()
	class Parent:
		appname = 'Game Editor'
		game_config_filename = 'ge-config.json'
	window = Editor(Parent(), 'C:\Test-Game')
	window.run()
	app.exec_()

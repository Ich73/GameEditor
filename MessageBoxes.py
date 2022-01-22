""" Author: Dominik Beese
>>> Message Boxes
<<<
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
translate = QtCore.QCoreApplication.translate

class MessageBoxes:
	
	def showDlg(self, text, detailedText = None, icon = None, title = None):
		""" Displays a message dialog. """
		msg = QtWidgets.QMessageBox()
		if icon: msg.setIcon(icon)
		msg.setWindowTitle(title or self.appname)
		msg.setWindowIcon(QtGui.QIcon(self.icon))
		msg.setText(text)
		if detailedText: msg.setDetailedText(detailedText)
		msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
		msg.exec_()
	
	def showError(self, text, detailedText = None):
		""" Displays an error message. """
		self.showDlg(text, detailedText, QtWidgets.QMessageBox.Critical, translate('MessageBoxes', 'error'))
	
	def showWarning(self, text, detailedText = None):
		""" Displays a warning message. """
		self.showDlg(text, detailedText, QtWidgets.QMessageBox.Warning, translate('MessageBoxes', 'warning'))
	
	def showInfo(self, text, detailedText = None):
		""" Displays an information message. """
		self.showDlg(text, detailedText, None, translate('MessageBoxes', 'information'))
	
	def askDlg(self, text, detailedText = None, icon = None, title = None):
		""" Displays a message and asks yes or no. Returns True if yes was selected. """
		msg = QtWidgets.QMessageBox()
		if icon: msg.setIcon(icon)
		msg.setWindowTitle(title or self.appname)
		msg.setWindowIcon(QtGui.QIcon(self.icon))
		msg.setText(text)
		if detailedText: msg.setDetailedText(detailedText)
		msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
		return msg.exec_() == QtWidgets.QMessageBox.Yes
	
	def askCustomDlg(self, text, *buttons, detailedText = None, icon = None, title = None):
		""" Displays a message dialog with custom buttons. """
		msg = QtWidgets.QMessageBox()
		if icon: msg.setIcon(icon)
		msg.setWindowTitle(title or self.appname)
		msg.setWindowIcon(QtGui.QIcon(self.icon))
		msg.setText(text)
		if detailedText: msg.setDetailedText(detailedText)
		for i, button in enumerate(buttons): msg.addButton(button, i)
		return buttons[msg.exec_()]
	
	def askWarning(self, text, detailedText = None):
		""" Displays a warning message and asks yes or no. Returns True if yes was selected. """
		return self.askDlg(text, detailedText, QtWidgets.QMessageBox.Warning, translate('MessageBoxes', 'warning'))
	
	def showProgress(self, text, minimum = 0, maximum = 100):
		class CustomProgressDialog(QtWidgets.QProgressDialog):
			def __init__(self):
				super().__init__(text, None, minimum, maximum)
			def incValue(self):
				self.setValue(self.value() + 1)
			def setValue(self, value):
				super().setValue(value)
				QtWidgets.QApplication.processEvents()
			def setText(self, text):
				super().setLabelText(text)
				QtWidgets.QApplication.processEvents()
		msg = CustomProgressDialog()
		msg.setWindowTitle(self.appname)
		msg.setWindowIcon(QtGui.QIcon(self.icon))
		msg.setWindowFlags(Qt.WindowTitleHint)
		msg.setWindowModality(Qt.ApplicationModal)
		msg.setCancelButton(None)
		msg.setAutoClose(True)
		msg.show()
		QtWidgets.QApplication.processEvents()
		return msg

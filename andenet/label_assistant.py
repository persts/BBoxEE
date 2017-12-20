import os
from PyQt5 import QtCore, QtWidgets, uic

LABEL, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'label_assistant.ui'))


class LabelAssistant(QtWidgets.QWidget, LABEL):
    submitted = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self)
        self.setupUi(self)
        self.setWindowTitle('Annotation Assitant')
        file = open('labels.txt')
        for line in file:
            self.comboBoxLabels.addItem(line.rstrip())
        file.close()
        self.pushButtonSubmit.clicked.connect(self.submit)

    def submit(self):
        metadata = {}
        metadata['label'] = self.comboBoxLabels.currentText()
        metadata['truncated'] = self.checkBoxTruncated.isChecked() and 'Y' or 'N'
        metadata['occluded'] = self.checkBoxOccluded.isChecked() and 'Y' or 'N'
        metadata['difficult'] = self.checkBoxDifficult.isChecked() and 'Y' or 'N'
        self.submitted.emit(metadata)
        self.hide()

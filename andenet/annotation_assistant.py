# -*- coding: utf-8 -*-
#
# Animal Detection Network (Andenet)
# Copyright (C) 2017 Peter Ersts
# ersts@amnh.org
#
# --------------------------------------------------------------------------
#
# This file is part of Animal Detection Network (Andenet).
#
# Andenet is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Andenet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Point Class Assigner.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------
import os
from PyQt5 import QtCore, QtWidgets, uic

LABEL, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'annotation_assistant.ui'))


class AnnotationAssistant(QtWidgets.QWidget, LABEL):
    """Helper widget that displays label and metadata choices after creating a bounding box."""

    submitted = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        """Class init function."""
        QtWidgets.QWidget.__init__(self)
        self.setupUi(self)
        self.setWindowTitle('Annotation Assitant')
        file = open('labels.txt')
        for line in file:
            self.comboBoxLabels.addItem(line.rstrip())
        file.close()
        self.pushButtonSubmit.clicked.connect(self.submit)

    def submit(self):
        """(Slot) Emit bounding box label data."""
        metadata = {}
        metadata['label'] = self.comboBoxLabels.currentText()
        metadata['truncated'] = self.checkBoxTruncated.isChecked() and 'Y' or 'N'
        metadata['occluded'] = self.checkBoxOccluded.isChecked() and 'Y' or 'N'
        metadata['difficult'] = self.checkBoxDifficult.isChecked() and 'Y' or 'N'
        self.submitted.emit(metadata)
        self.hide()

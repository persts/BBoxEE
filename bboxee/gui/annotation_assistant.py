# -*- coding: utf-8 -*-
#
# Bounding Box Editor and Exporter (BBoxEE)
# Author: Peter Ersts (ersts@amnh.org)
#
# --------------------------------------------------------------------------
#
# This file is part of Animal Detection Network's (Andenet)
# Bounding Box Editor and Exporter (BBoxEE)
#
# BBoxEE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BBoxEE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------
import os
import sys
from PyQt5 import QtCore, QtWidgets, uic

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(__file__)
LABEL, _ = uic.loadUiType(os.path.join(bundle_dir, 'annotation_assistant.ui'))


class AnnotationAssistant(QtWidgets.QDialog, LABEL):
    """Helper widget that displays label and metadata choices
    after creating a bounding box."""

    submitted = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        """Class init function."""
        QtWidgets.QDialog.__init__(self, parent)
        self.setupUi(self)
        self.setWindowTitle('Annotation Assitant')
        self.setModal(True)
        self.set_labels(['N/A'])
        self.pb_submit.clicked.connect(self.submit)

    def set_label(self, label):
        """Set current lable in the combobox."""
        index = self.cbb_labels.findText(label)
        if index == -1:
            self.cbb_labels.addItem(label)
            index = self.cbb_labels.count() - 1
        self.cbb_labels.setCurrentIndex(index)

    def set_labels(self, labels):
        """Populate base lables."""
        self.cbb_labels.clear()
        self.cbb_labels.addItems(labels)

    def submit(self):
        """(Slot) Emit bounding box label data."""
        metadata = {}
        metadata['label'] = self.cbb_labels.currentText()
        metadata['truncated'] = self.cb_truncated.isChecked() and 'Y' or 'N'
        metadata['occluded'] = self.cb_occluded.isChecked() and 'Y' or 'N'
        metadata['difficult'] = self.cb_difficult.isChecked() and 'Y' or 'N'
        self.submitted.emit(metadata)
        self.hide()

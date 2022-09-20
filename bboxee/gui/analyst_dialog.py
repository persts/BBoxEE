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
from PyQt6 import QtWidgets, QtCore


class AnalystDialog(QtWidgets.QDialog):
    name = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(AnalystDialog, self).__init__(parent)
        self.setModal(True)
        message = 'By adding an analyst\'s name, you are asserting that ' \
                  'this analyst has created or reviewed all of the current ' \
                  'bounding boxes in this bbx file.'
        self.label = QtWidgets.QLabel(message)
        self.label.setWordWrap(True)
        self.analyst = QtWidgets.QLineEdit()
        self.add_button = QtWidgets.QPushButton('Save')
        self.add_button.clicked.connect(self.save)
        self.setWindowTitle('Add Analyst')
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.label)
        self.layout().addWidget(self.analyst)
        self.layout().addWidget(self.add_button)

    def save(self):
        self.name.emit(self.analyst.text())
        self.close()

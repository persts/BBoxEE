# -*- coding: utf-8 -*-
#
# Animal Detection Network (Andenet)
# Author: Peter Ersts (ersts@amnh.org)
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
# along with this software.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------
import os
from PyQt5 import QtCore, QtWidgets, uic

DIALOG, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'annotator_dialog.ui'))


class AnnotatorDialog(QtWidgets.QDialog, DIALOG):
    """Helper widget to select and build Annotator."""

    selected = QtCore.pyqtSignal(QtCore.QThread)

    def __init__(self, parent=None):
        """Class init function."""
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)
        self.setWindowTitle('Select Model')

        self.pushButtonTensorflow.clicked.connect(self.tensorflow_selected)

    def tensorflow_selected(self):
        """Load a frozen inference graph and label map."""
        try:
            from andenet.annotator.tensorflow import Annotator
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Model Directory')
            if directory != '':
                self.annotator = Annotator(directory)
                self.selected.emit(self.annotator)
                self.hide()
        except ModuleNotFoundError:
            QtWidgets.QMessageBox.critical(self, 'Export', 'Required Tensorflow modules not found.\n\nPlease review install requirements.')

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
        self.last_dir = '.'

        # TODO: Split this up into smaller components to avoid future name collison
        self.pushButtonTensorflow.clicked.connect(self.tensorflow_selected)
        self.pushButtonYolo.clicked.connect(self.yolo_selected)

        self.data_config = None
        self.pushButtonDataConfig.clicked.connect(self.get_data_config)
        self.network_config = None
        self.pushButtonNetworkConfig.clicked.connect(self.get_network_config)
        self.weights = None
        self.pushButtonWeights.clicked.connect(self.get_weights)

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

    def yolo_selected(self):
        try:
            from andenet.annotator.yolo import Annotator
            data_config = self.lineEditDataConfig.text()
            net_config = self.lineEditNetworkConfig.text()
            weights = self.lineEditWeights.text()
            image_size = self.spinBoxImageSize.value()
            self.annotator = Annotator(data_config, net_config, weights, image_size)
            self.selected.emit(self.annotator)
            self.hide()
        except ModuleNotFoundError:
            QtWidgets.QMessageBox.critical(self, 'Export', 'Required Torch or YOLOv3 modules not found.\n\nPlease review install requirements.')


    # Helper functions
    def get_data_config(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Load Data Config', self.last_dir, 'Data (*.data)')
        if file_name[0] != '':
            self.lineEditDataConfig.setText(file_name[0])
            self.last_dir = os.path.split(file_name[0])[0]
            self.pushButtonNetworkConfig.setDisabled(False)
    
    def get_network_config(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Load Network Config', self.last_dir, 'Config (*.cfg)')
        if file_name[0] != '':
            self.lineEditNetworkConfig.setText(file_name[0])
            self.last_dir = os.path.split(file_name[0])[0]
            self.pushButtonWeights.setDisabled(False)

    def get_weights(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Load weights', self.last_dir, 'PyTorch (*.pt)')
        if file_name[0] != '':
            self.lineEditWeights.setText(file_name[0])
            self.last_dir = os.path.split(file_name[0])[0]
            self.pushButtonYolo.setDisabled(False)

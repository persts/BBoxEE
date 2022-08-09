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
from PyQt5 import QtCore, QtWidgets, QtGui, uic

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(__file__)
DIALOG, _ = uic.loadUiType(os.path.join(bundle_dir, 'select_model_dialog.ui'))


class SelectModelDialog(QtWidgets.QDialog, DIALOG):
    """Helper widget to select and load model."""

    selected = QtCore.pyqtSignal(QtCore.QThread)

    def __init__(self, parent=None):
        """Class init function."""
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)
        self.setWindowTitle('Select Model')
        self.last_dir = '.'

        self.pushButtonTFGraph.clicked.connect(self.get_inference_graph)
        self.interence_graph = None

        self.pushButtonLabelMapV1.clicked.connect(self.get_label_map)
        self.pushButtonLabelMapV2.clicked.connect(self.get_label_map_2)
        self.label_map = None

        self.pushButtonTFModel.clicked.connect(self.get_saved_model)
        self.pushButtonYoloModelFile.clicked.connect(self.get_yolo_model)
        self.model = None

        self.pushButtonTFV1.clicked.connect(self.tensorflow_v1_frozen_selected)
        self.pushButtonTFV2.clicked.connect(self.tensorflow_v2_saved_model)
        self.pushButtonYolo.clicked.connect(self.yolo_model)

    def set_label(self, label, text):
        qfm = QtGui.QFontMetrics(label.font())
        width = label.width() - 2
        clipped = qfm.elidedText(text, QtCore.Qt.ElideMiddle, width)
        label.setText(clipped)
        label.raw_text = text

    def tensorflow_v1_frozen_selected(self):
        """Load a frozen inference graph and label map."""
        self.pushButtonTFV1.setDisabled(True)
        self.pushButtonLabelMapV1.setDisabled(True)
        self.pushButtonTFGraph.setDisabled(True)
        try:
            from bboxee.annotator.tensorflow_v1_frozen import Annotator
            graph = self.labelTFGraph.raw_text
            label_map = self.labelLabelMapV1.raw_text
            self.annotator = Annotator(graph, label_map)
            self.selected.emit(self.annotator)
            self.hide()
        except ModuleNotFoundError:
            message = 'Required TensorFlow modules not found.'
            QtWidgets.QMessageBox.critical(self, 'Export', message)
        self.pushButtonTFV1.setDisabled(False)
        self.pushButtonLabelMapV1.setDisabled(False)
        self.pushButtonTFGraph.setDisabled(False)

    def tensorflow_v2_saved_model(self):
        """Load a saved model and label map."""
        self.pushButtonTFV2.setDisabled(True)
        self.pushButtonLabelMapV2.setDisabled(True)
        self.pushButtonTFModel.setDisabled(True)
        try:
            import tensorflow as tf
            if tf.__version__[0] == '1':
                raise ModuleNotFoundError('')
            from bboxee.annotator.tensorflow_v2_saved import Annotator
            model = self.labelTFModel.raw_text
            label_map = self.labelLabelMapV2.raw_text
            self.annotator = Annotator(model, label_map)
            self.selected.emit(self.annotator)
            self.hide()
        except ModuleNotFoundError:
            message = 'Required TensorFlow modules not found.'
            QtWidgets.QMessageBox.critical(self, 'Export', message)
        self.pushButtonTFV2.setDisabled(False)
        self.pushButtonLabelMapV2.setDisabled(False)
        self.pushButtonTFModel.setDisabled(False)

    def yolo_model(self):
        """Load YOLO5 Model"""
        self.pushButtonYoloModelFile.setDisabled(True)
        try:
            from bboxee.annotator.yolo import Annotator
            model = self.labelYoloModelFile.raw_text
            self.annotator = Annotator(model, self.spinBoxImageSize.value(), self.spinBoxStride.value())
            self.selected.emit(self.annotator)
            self.hide()
        except ModuleNotFoundError:
            message = 'Required Torch or YOLO5 modules not found.'
            QtWidgets.QMessageBox.critical(self, 'Export', message)
        self.pushButtonYoloModelFile.setEnabled(True)

    # Helper functions
    def get_inference_graph(self):
        file_name = (QtWidgets.
                     QFileDialog.
                     getOpenFileName(self,
                                     'Select Frozen Inference Graph',
                                     self.last_dir, 'TF Graph (*.pb)'))
        if file_name[0] != '':
            self.set_label(self.labelTFGraph, file_name[0])
            self.last_dir = os.path.split(file_name[0])[0]
            self.pushButtonTFV1.setDisabled(False)

    def get_label_map(self):
        file_name = (QtWidgets.
                     QFileDialog.
                     getOpenFileName(self,
                                     'Select Label Map',
                                     self.last_dir, 'Label Map (*.pbtxt *.txt)'))
        if file_name[0] != '':
            self.set_label(self.labelLabelMapV1, file_name[0])
            self.last_dir = os.path.split(file_name[0])[0]
            self.pushButtonTFGraph.setDisabled(False)

    def get_label_map_2(self):
        file_name = (QtWidgets.
                     QFileDialog.
                     getOpenFileName(self,
                                     'Select Label Map',
                                     self.last_dir, 'Label Map (*.pbtxt *.txt)'))
        if file_name[0] != '':
            self.set_label(self.labelLabelMapV2, file_name[0])
            self.last_dir = os.path.split(file_name[0])[0]
            self.pushButtonTFModel.setDisabled(False)

    def get_saved_model(self):
        directory = (QtWidgets.
                     QFileDialog.
                     getExistingDirectory(self,
                                          'Select Saved Model Directory',
                                          self.last_dir))
        if directory != '':
            self.set_label(self.labelTFModel, directory)
            self.last_dir = directory
            self.pushButtonTFV2.setDisabled(False)

    def get_yolo_model(self):
        file_name = (QtWidgets.
                     QFileDialog.
                     getOpenFileName(self,
                                     'Select YOLO5 Model',
                                     self.last_dir, '(*.pt)'))
        if file_name[0] != '':
            self.set_label(self.labelYoloModelFile, file_name[0])
            self.last_dir = os.path.split(file_name[0])[0]
